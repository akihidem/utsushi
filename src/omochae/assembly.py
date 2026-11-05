"""手順どおりに 3D で組み立てる（本人の考え 2026-11-05、#331）。

本人の言葉: 「3Dで作ることでユーザーフレンドリーだし、AIの自己検証にもなる。手順をAIが3Dで組み立てて、その過程を手順書にする」

部品の平らな形と折り線から始めて、手順ごとに折る・貼る・通す。最後の形が完成図で、途中の形が手順の図になる。組み上がらなければ、それが自己検証の結果になる。

判断の芯:
- 紙の形は雛形の parts から読む。完成図を別に描かない。紙か寸法を直すと図も一緒に変わる。
- 紙は折り線で分けた硬い面として動かす。たわみ・折り目なしの曲げ・糸の張り・摩擦は入らない。形の確かめで、動くかは確かめない（紙の返事が本線）。
- 手順の文は雛形の steps をそのまま使う。組み立ての段は文と 1 対 1 に並べ、数が合わなければ落とす（文と図がずれないため）。
- 検査は形の事実を数えるだけで、合否を学ぶ人の頁に出さない。「AI が確かめたから正しい」とは言わない。

exit code: 0 = 通る / 3 = 落ちる（どの手順で何が合わないか）/ 4 = 検査できない。
"""
import argparse
import json
import math
import pathlib
import sys
from dataclasses import dataclass, field

from shapely.geometry import LineString, Polygon
from shapely.ops import split

from . import hypotheses, instructions
from .compose import TEMPLATES, compose
from .model import Failure, ToolMissing
from .fan_model import clearance_limit_deg, opening_bound_deg

ROOT = pathlib.Path(hypotheses.__file__).resolve().parents[2]
EPS = 1e-6
CLOSE_TOL = 1.0  # mm。糊代が相手の面に届いたと読む離れ。紙の厚みと手の誤差を見込む
LINE_TOL = 5.0  # 度。穴が一直線に並ぶと読む傾き
THREAD_TOL = 1.5  # mm。糸の穴どうしがそろったと読む離れ
RULER_ZERO = 4.0  # mm。定規の端から 0 の目盛りまで
FOLD_PITCH = 1.0  # mm。畳んだ蛇腹の 1 枚あたりの広がり。11-04 の動画と写真 p02 で、28 折りが筒の幅いっぱいに並ぶ
FAN_SHOWN = 180.0  # 度。できあがりの図で開く角。どこまで開くかは紙で確かめる物なので、図は半円までにする


def identity():
    return [[1.0 if i == j else 0.0 for j in range(4)] for i in range(4)]


def mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def translate(x=0.0, y=0.0, z=0.0):
    m = identity()
    m[0][3], m[1][3], m[2][3] = x, y, z
    return m


def rotate_axis(point, direction, deg):
    """点 point を通る向き direction の軸のまわりの回転。"""
    n = math.sqrt(sum(c * c for c in direction))
    ux, uy, uz = (c / n for c in direction)
    a = math.radians(deg)
    c, s, t = math.cos(a), math.sin(a), 1 - math.cos(a)
    r = [[t * ux * ux + c, t * ux * uy - s * uz, t * ux * uz + s * uy, 0],
         [t * ux * uy + s * uz, t * uy * uy + c, t * uy * uz - s * ux, 0],
         [t * ux * uz - s * uy, t * uy * uz + s * ux, t * uz * uz + c, 0],
         [0, 0, 0, 1.0]]
    return mul(mul(translate(*point), r), translate(*(-c_ for c_ in point)))


def rotate_x(deg):
    return rotate_axis((0, 0, 0), (1, 0, 0), deg)


def rotate_y(deg):
    return rotate_axis((0, 0, 0), (0, 1, 0), deg)


def rotate_z(deg):
    return rotate_axis((0, 0, 0), (0, 0, 1), deg)


def apply(m, p):
    x, y, z = (p[0], p[1], p[2] if len(p) > 2 else 0.0)
    return tuple(m[i][0] * x + m[i][1] * y + m[i][2] * z + m[i][3] for i in range(3))


def _sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _unit(a):
    n = math.sqrt(_dot(a, a)) or 1.0
    return tuple(x / n for x in a)


def normal_of(m):
    """面の表（刷った面）の向き。"""
    return _unit((m[0][2], m[1][2], m[2][2]))


@dataclass
class Sheet:
    """部品 1 つを、折り線で分けた面の集まりにした物。"""
    part: object
    extra: list = field(default_factory=list)  # 紙に刷っていないが、貼る時に折る線 [(線の 2 点, 種類)]
    panels: list = field(default_factory=list)  # shapely の多角形（部品の座標、mm）
    tree: dict = field(default_factory=dict)  # 面 → (親の面, 折り線の番号)
    lines: list = field(default_factory=list)  # [(線の 2 点, "valley"|"mountain")]
    root: int = 0

    def __post_init__(self):
        self.lines = [(tuple(s), "valley") for s in self.part.valley] + [(tuple(s), "mountain") for s in self.part.mountain] + list(self.extra)
        shapes = [Polygon(self.part.outline).buffer(0)]
        for (a, b), _ in self.lines:
            d = _unit((b[0] - a[0], b[1] - a[1], 0))
            cut = LineString([(a[0] - d[0], a[1] - d[1]), (b[0] + d[0], b[1] + d[1])])
            shapes = [g for s in shapes for g in (split(s, cut).geoms if s.crosses(cut) else [s])]
        self.panels = sorted(shapes, key=lambda s: (round(s.bounds[1], 3), round(s.bounds[0], 3)))
        self.root = max(range(len(self.panels)), key=lambda i: self.panels[i].area) if self.part.key == "base" else self._first_panel()
        self._grow()

    def _first_panel(self):
        return min(range(len(self.panels)), key=lambda i: (round(self.panels[i].bounds[0], 3), round(self.panels[i].bounds[1], 3)))

    def _grow(self):
        """面のつながりの木を、根の面から作る。折り線の上で辺を共有する面どうしをつなぐ。"""
        seen, stack = {self.root}, [self.root]
        while stack:
            i = stack.pop()
            for j, other in enumerate(self.panels):
                if j in seen:
                    continue
                for k, ((a, b), _) in enumerate(self.lines):
                    line = LineString([a, b]).buffer(1e-3)
                    if self.panels[i].intersection(line).area > 1e-3 and other.intersection(line).area > 1e-3:
                        self.tree[j] = (i, k)
                        seen.add(j)
                        stack.append(j)
                        break
        loose = set(range(len(self.panels))) - seen
        if loose:
            raise ValueError(f"{self.part.key}: 折り線でつながらない面がある {sorted(loose)}")

    def hinge(self, i):
        """面 i を親につなぐ折り線。Returns (線の始めの点, 線の向き)。"""
        (a, b), _ = self.lines[self.tree[i][1]]
        return (a[0], a[1], 0.0), (b[0] - a[0], b[1] - a[1], 0.0)

    def turn(self, i, angles):
        """面 i を折り線のまわりに回す角（線の向きのまわりの度）。angles は {折り線の番号: 度}。負の角は、線の種類と逆の向きに折る。"""
        k = self.tree[i][1]
        deg = angles.get(k, 0.0)
        point, axis = self.hinge(i)
        c = self.panels[i].centroid
        # 向きは、子の面の重心がどちらへ動くかで決める。谷は +z、山は -z。
        lifted = apply(rotate_axis(point, axis, abs(deg)), (c.x, c.y, 0.0))[2]
        want = (1 if self.lines[k][1] == "valley" else -1) * (1 if deg >= 0 else -1)
        return -abs(deg) if deg and lifted * want < 0 else abs(deg)

    def depth(self, i):
        """根の面から何枚目か。"""
        return 0 if i == self.root else 1 + self.depth(self.tree[i][0])

    def matrices(self, angles):
        """面ごとの行列（部品の座標 → 部品の組の座標）。angles は {折り線の番号: 度}。谷は刷った面の側（+z）へ起こす。"""
        out = {self.root: identity()}

        def of(i):
            if i not in out:
                point, axis = self.hinge(i)
                out[i] = mul(of(self.tree[i][0]), rotate_axis(point, axis, self.turn(i, angles)))
            return out[i]

        for i in range(len(self.panels)):
            of(i)
        return out


class Bench:
    """作業の机。手順ごとの形を frames に残し、合わない所を failures に残す。"""

    def __init__(self, parts, extra=None):
        self.sheets = {q.key: Sheet(q, (extra or {}).get(q.key, [])) for q in parts}
        self.place = {q.key: identity() for q in parts}
        self.angles = {q.key: {} for q in parts}
        self.custom = {q.key: {} for q in parts}  # 面ごとの行列を直に置く物（硬い面の折りでは表せない形。扇を開いた形）
        self.nudge = {q.key: {} for q in parts}  # 面を自分の表の向きへずらす mm（貼って重なる面の前後を決める。形の検査には使わない）
        self.visible = set()
        self.paper_on = False  # 刷った紙が机にあるか
        self.scrap = True  # 溝の切り落とす所が、まだ紙についているか
        self.paper = None  # 刷った紙の配置（compose の layout）
        self.poses = []  # 今の手順の途中の形
        self.frames = []
        self.failures = []
        self.step = 0
        self.extras = {}  # 竹串と糸。名前 → (始め, 終わり, 持ち主の部品)

    def world(self, key, i):
        c = self.custom[key].get(i)
        m = mul(self.place[key], c if c is not None else self.sheets[key].matrices(self.angles[key])[i])
        d = self.nudge[key].get(i)
        return mul(m, translate(0, 0, d)) if d else m

    def fold(self, key, kinds=("valley", "mountain"), deg=90.0, only=None):
        for k, (_, kind) in enumerate(self.sheets[key].lines):
            if kind in kinds and (only is None or k in only):
                self.angles[key][k] = deg

    def fold_back(self, key, deg=90.0):
        """線の種類によらず、刷った面を外にして折る（紙の言葉と違う向きで組む時）。"""
        for k, (_, kind) in enumerate(self.sheets[key].lines):
            self.angles[key][k] = -deg if kind == "valley" else deg

    def panel_at(self, key, x, y):
        """部品の座標の点を含む面の番号。"""
        from shapely.geometry import Point

        p = Point(x, y)
        for i, s in enumerate(self.sheets[key].panels):
            if s.buffer(1e-3).contains(p):
                return i
        raise ValueError(f"{key}: ({x}, {y}) を含む面が無い")

    def fail(self, where, message):
        self.failures.append(Failure("F13.assembly", f"手順 {self.step} {where}", message))

    def closes(self, key, tab, onto):
        """糊代の面が、相手の面に重なるか。筒や箱が閉じるかの確かめ。tab と onto は面の番号。"""
        name = self.sheets[key].part.name
        wt, wo = self.world(key, tab), self.world(key, onto)
        n, o = normal_of(wo), apply(wo, (0, 0, 0))
        pts = [apply(wt, p) for p in self.sheets[key].panels[tab].exterior.coords]
        far = max(abs(_dot(_sub(p, o), n)) for p in pts)
        if far > CLOSE_TOL:
            self.fail(name, f"糊代が相手の面に届かない（{far:.1f}mm 離れる）")
            return False
        inv = _invert_rigid(wo)
        flat = Polygon([apply(inv, p)[:2] for p in pts]).buffer(0)
        target = self.sheets[key].panels[onto]
        if flat.intersection(target).area < 0.8 * flat.area:
            self.fail(name, "糊代が相手の面の外に出る")
            return False
        return True

    def faces_out(self, key, panels, center):
        """絵のある面の表が外を向くか。Returns 内を向いた面の番号の一覧。"""
        inner = []
        for i in panels:
            w = self.world(key, i)
            c = self.sheets[key].panels[i].centroid
            if _dot(_sub(apply(w, (c.x, c.y)), center), normal_of(w)) < 0:
                inner.append(i)
        return inner

    def holes_in_line(self, key, a, b):
        """2 つの穴に棒をまっすぐ通せるか。Returns (棒の始め, 終わり) か None。"""
        name = self.sheets[key].part.name
        pa, pb = self.sheets[key].part.holes[a], self.sheets[key].part.holes[b]
        wa, wb = self.world(key, self.panel_at(key, pa[0], pa[1])), self.world(key, self.panel_at(key, pb[0], pb[1]))
        ca, cb = apply(wa, pa[:2]), apply(wb, pb[:2])
        d = _unit(_sub(cb, ca))
        for w in (wa, wb):
            if abs(_dot(d, normal_of(w))) < math.cos(math.radians(LINE_TOL)):
                self.fail(name, "2 つの穴が向かい合わない（棒をまっすぐ通せない）")
                return None
        return ca, cb

    def bounds(self, key):
        """部品の今の形の広がり（世界の座標）。"""
        lo, hi = [math.inf] * 3, [-math.inf] * 3
        for i, s in enumerate(self.sheets[key].panels):
            w = self.world(key, i)
            for p in s.exterior.coords:
                q = apply(w, p)
                for k in range(3):
                    lo[k], hi[k] = min(lo[k], q[k]), max(hi[k], q[k])
        return lo, hi

    def fits_inside(self, inner, outer):
        """内の部品が外の部品の中に入るか（筒の断面で見る）。"""
        li, hi = self.bounds(inner)
        lo, ho = self.bounds(outer)
        for k in (0, 2):
            if li[k] < lo[k] - EPS or hi[k] > ho[k] + EPS:
                self.fail(self.sheets[inner].part.name, f"{self.sheets[outer].part.name}の中に入らない")
                return False
        return True

    def _worlds(self, key):
        sheet = self.sheets[key]
        ms = sheet.matrices(self.angles[key])
        out = {}
        for i in range(len(sheet.panels)):
            c = self.custom[key].get(i)
            m = mul(self.place[key], c if c is not None else ms[i])
            d = self.nudge[key].get(i)
            out[i] = mul(m, translate(0, 0, d)) if d else m
        return out

    def beat(self, view=None, dur=None, **tool):
        """手順の途中の形を 1 つ残す。頁はこの形を順に動かして見せる。
        tool: focus（寄って見る部品）・cut（はさみの道）・ruler（定規の左上）・cam（見る向きを変えるのに使う割合）・order（折る順）。"""
        panels = {}
        for key, sheet in self.sheets.items():
            shown = self._worlds(key) if key in self.visible else {}
            for i in range(len(sheet.panels)):
                panels[f"{key}:{i}"] = shown.get(i)
        # 折りの途中を描けるように、部品の置き方と折り線の角も残す（面を直に置いた部品は、途中を描かない）
        state = {key: {"place": self.place[key], "turns": {i: sheet.turn(i, self.angles[key]) for i in sheet.tree}, "nudge": dict(self.nudge[key])}
                 for key, sheet in self.sheets.items() if key in self.visible and not self.custom[key]}
        self.poses.append({"panels": panels, "view": view or {}, "extras": dict(self.extras), "state": state, "dur": dur,
                           "paper": self.paper_on, "scrap": self.scrap, **tool})

    def snapshot(self, text, view=None, dur=None, **tool):
        """手順の終わりの形を残し、手順を閉じる。"""
        self.beat(view, dur, **tool)
        last = self.poses[-1]
        self.frames.append({"step": self.step, "text": text, "poses": self.poses, "panels": last["panels"], "view": last["view"],
                            "extras": last["extras"], "state": last["state"]})
        self.poses = []


def _invert_rigid(m):
    """回転と平行移動だけの行列の逆。"""
    r = [[m[j][i] for j in range(3)] for i in range(3)]
    t = [-sum(r[i][j] * m[j][3] for j in range(3)) for i in range(3)]
    return [r[0] + [t[0]], r[1] + [t[1]], r[2] + [t[2]], [0, 0, 0, 1.0]]


def knob_length(p):
    """竹串の長さ。用意する物の表（slider_fan の materials）と同じ式。"""
    return p["tube_side"] + 20


def _print_side_out(b, key, side, height):
    """紙を角筒にして、原点に立てる。絵のある面を外に、糊代を内へ。"""
    b.fold_back(key)
    b.place[key] = translate(-side / 2, -height / 2, side / 2)


def _cap(b, key, center, y, c):
    """台の中央の面を水平に置く。糊代が下へ向く置き方を選ぶ。c は部品の座標での面の中心。"""
    tab = next(i for i in range(len(b.sheets[key].panels)) if i != center)
    p = b.sheets[key].panels[tab].centroid
    for deg in (90, -90):
        b.place[key] = mul(translate(0, y, 0), mul(rotate_x(deg), translate(-c, -c)))
        if apply(b.world(key, tab), (p.x, p.y))[1] > y:
            return


def _thread(b, strip, hub, hole):
    """糸。扇の要から像の穴の先まで。Returns (要, 像の穴)。"""
    s = apply(b.world("fan", strip), hub)
    e = apply(b.world("figure", b.panel_at("figure", *hole)), hole)
    d = _unit(_sub(e, s))
    b.extras["thread"] = (s, tuple(x + y * 2 for x, y in zip(e, d)), "fan")
    return s, e


def _row(b):
    """畳んだ扇の中心側の穴の列を通る糸。列の端から端まで。"""
    fan = b.sheets["fan"]
    holes = [h for h in fan.part.holes if h[0] == fan.part.holes[0][0]]
    ends = [apply(b.world("fan", b.panel_at("fan", h[0], h[1])), h[:2]) for h in (holes[0], holes[-1])]
    b.extras["row"] = (ends[0], ends[1], "fan")


def _outline(b, key):
    """はさみの道。平らな部品の切る線を一周する（世界の座標）。"""
    q = b.sheets[key].part
    pts = [apply(b.place[key], pt)[:2] for pt in q.outline]
    return pts + pts[:1]


def _cut_ms(path):
    """はさみが一周する時間（ミリ秒）。長い部品でも待たせすぎない。"""
    return min(2400, 500 + 4 * sum(math.dist(a, b) for a, b in zip(path, path[1:])))


def _slider_fan(p, parts, paper=None):
    """御来迎（slider_fan）の組み立て。手順の文の順に、紙が実際に動く形を並べる。Returns Bench。押し方と中心の置き方が別の形は、まだ書いていないので None。

    本人の感想（11-05）「実際の手順に沿って、見え方や動きを再現する」。刷った紙の上の置き場から始め、切る・穴をあける・折る・通す・貼る・入れるを順に動かす。
    paper は compose の layout。無い時（部品を直して検査する時）は、部品を机に並べて同じ順に組む。
    """
    if p["push_part"] != "tab" or p["hub"] != "axle":
        return None
    by_key = {q.key: q for q in parts}
    # 像の足は紙に折り線が無いが、台に貼る時に折る
    foot_line = tuple(by_key["figure"].glue[0][:2])
    b = Bench(parts, {"figure": [(foot_line, "mountain")]})
    words = instructions.steps(p, "slider_fan")
    side, tall = p["tube_side"], p["tube_height"]
    ps, ph = p["pusher_side"], p["pusher_height"]
    bs, g = p["base_side"], p["base_glue"]
    n, w = int(p["fold_count"]), p["fold_width"]
    m = n // 2
    fw, fh = p["figure_w"], p["figure_h"]
    top = -ph / 2  # 内筒の中心を原点に置いた時の、内筒の上の端（台の上の面）
    fan = b.sheets["fan"]
    hub = fan.part.holes[m][:2]  # 扇の要。真ん中の板の中心側の穴
    hole = by_key["figure"].holes[0][:2]
    tw = 4 * side + p["tube_glue"]
    leg = max(0.0, -min(x for x, _ in fan.part.outline))
    if paper:
        pw, ph_page = paper["page"].w, paper["page"].h
        laid = {q.key: translate(q.x - pw / 2, q.y - ph_page / 2) for q in parts}
        left = -pw / 2
    else:
        laid = {"tube": translate(-tw / 2 - 6, -tall / 2), "pusher": translate(-(4 * ps + p["pusher_glue"]) / 2, tall / 2 + 18),
                "base": translate(-(bs + 2 * g) / 2, tall / 2 + ph + 26), "figure": translate(bs / 2 + g + 10, tall / 2 + ph + 26),
                "fan": translate(tw / 2 + 2 + leg, -n * w / 2)}
        left = -tw / 2 - 6
    b.place.update(laid)

    def step(k):
        b.step = k
        return words[k - 1]

    # 1 刷った紙を机に置き、定規を物差しに当てる
    text = step(1)
    b.visible = set(b.sheets)
    b.paper_on = bool(paper)
    flat = {"rx": -8, "ry": 0}
    if paper:
        rx0, ry0 = paper["ruler"]
        at = (rx0 - pw / 2 - RULER_ZERO, ry0 + 3.2 - ph_page / 2)
        b.beat(flat, 500, ruler=(pw / 2 + 8, at[1] + 30))
        b.snapshot(text, flat, 1400, ruler=at)
    else:
        b.snapshot(text, flat)

    # 2 外筒だけを切る。はさみは切る線を一周し、溝は下の端から切り込む。切った部品を紙から持ち上げる
    text = step(2)
    b.beat(flat, 800, focus=("tube",))
    path = _outline(b, "tube")
    b.beat(flat, _cut_ms(path), focus=("tube",), cut=path)
    b.scrap = False
    b.place["tube"] = mul(translate(0, 0, 8), laid["tube"])
    b.beat(flat, 500, focus=("tube",))
    b.visible = {"tube"}
    b.paper_on = False
    b.place["tube"] = translate(-tw / 2, -tall / 2, 6)
    b.snapshot(text, {"rx": -6, "ry": 0}, 800)

    # 3 外筒を折って角筒にする。まず文のとおり（谷折り）に組んで確かめ、図は絵を外にした形で折る
    text = step(3)
    tube = b.sheets["tube"]
    b.beat({"rx": -16, "ry": -26}, 800)
    tab, onto = b.panel_at("tube", 4 * side + 4, tall / 2), b.panel_at("tube", 4, tall / 2)
    arts = [b.panel_at("tube", side * k + side / 2, 2) for k in range(4)]
    b.fold("tube", deg=90)
    lo, hi = b.bounds("tube")
    inner = b.faces_out("tube", arts, tuple((x + y) / 2 for x, y in zip(lo, hi)))
    if inner:
        b.fail(tube.part.name, f"文のとおりに谷折りすると、絵のある面（{len(inner)} 面）が筒の内側に入る")
    _print_side_out(b, "tube", side, tall)
    b.closes("tube", tab, onto)
    b.nudge["tube"][tab] = -0.3
    b.snapshot(text, {"rx": -14, "ry": -28}, cam=1.0)

    # 4 残りの部品を切る。作った外筒は紙の横に立てる。切った部品は紙から持ち上げ、穴は竹串の先であける
    text = step(4)
    b.visible = set(b.sheets)
    b.paper_on = bool(paper)
    for key in ("pusher", "base", "fan", "figure"):
        b.place[key] = laid[key]
    b.place["tube"] = translate(left - 22 - side, -tall / 2, side / 2)
    look = {"rx": -8, "ry": -4}
    b.beat(look, 1000)
    for key in ("pusher", "base", "fan", "figure"):
        path = _outline(b, key)
        b.beat(look, _cut_ms(path), cut=path)
        b.place[key] = mul(translate(0, 0, 8), laid[key])
        b.beat(look, 350)
    for key in ("pusher", "figure"):
        for x, y, _ in by_key[key].holes:
            tip = apply(b.world(key, b.panel_at(key, x, y)), (x, y))
            b.extras["poke"] = (tip, (tip[0] + 8, tip[1] - 14, tip[2] + 34), key)
            b.beat(look, 450)
    del b.extras["poke"]
    b.snapshot(text, look, 300)

    # 5 内筒も同じように角筒にする
    text = step(5)
    b.visible = {"pusher"}
    b.paper_on = False
    b.place["pusher"] = translate(-(4 * ps + p["pusher_glue"]) / 2, -ph / 2)
    b.beat({"rx": -16, "ry": -24}, 900)
    _print_side_out(b, "pusher", ps, ph)
    tab = b.panel_at("pusher", 4 * ps + 4, ph / 2)
    b.closes("pusher", tab, b.panel_at("pusher", 4, ph / 2))
    b.nudge["pusher"][tab] = -0.3
    b.snapshot(text, {"rx": -18, "ry": -30}, cam=1.0)

    # 6 竹串を外から 2 つの穴に通す。竹串の内の端は反対の穴から少し出るだけにする（反対の面に溝は無い）
    text = step(6)
    view = {"rx": -18, "ry": -30}
    line = b.holes_in_line("pusher", 0, 1)
    if line:
        d = _unit(_sub(line[0], line[1]))
        out = tuple(x + y * 6 for x, y in zip(line[0], d))
        length = knob_length(p)
        b.extras["axle"] = (out, tuple(x + y * length for x, y in zip(out, d)), "pusher")
        b.beat(view, 500)
        start = tuple(x - y for x, y in zip(line[1], d))
        b.extras["axle"] = (start, tuple(x + y * length for x, y in zip(start, d)), "pusher")
    b.snapshot(text, view, 1500)

    # 7 台の糊代を下へ折り、内筒の上から蓋をする。まず文のとおり（谷折り）に組み、糊代が下へ向く時に印の面がどちらを向くかを見る
    text = step(7)
    b.visible = {"pusher", "base"}
    if abs(bs - ps) > 0.5:
        b.fail(b.sheets["base"].part.name, f"台の面（{bs}mm）と内筒の断面（{ps}mm）が合わない")
    c = g + bs / 2
    center = b.panel_at("base", c, c)
    b.fold("base", deg=90)
    _cap(b, "base", center, top, c)
    if normal_of(b.world("base", center))[1] > 0:
        b.fail(b.sheets["base"].part.name, "型紙の線のとおりに谷折りすると、扇と像を貼る印のある面が下を向く")
    # 図は印の面を上にした形で出す
    view = {"rx": -24, "ry": -30}
    b.angles["base"] = {}
    b.place["base"] = mul(translate(0, top - 26, 0), mul(rotate_x(90), translate(-c, -c)))
    b.beat(view, 900)
    b.fold_back("base")
    b.beat(view, 1000)
    _cap(b, "base", center, top, c)
    b.nudge["base"] = {i: 0.3 for i in range(len(b.sheets["base"].panels)) if i != center}
    b.snapshot(text, view, 900)

    # 8 扇を端から蛇腹に畳み、折り山が前に並ぶ向きに立てる（11-04 の動画と写真の向き。板の面は横を向き、折り山が幅いっぱいに並ぶ）
    text = step(8)
    b.visible = {"fan"}
    flat_fan = mul(rotate_z(-90), translate(-hub[0], -hub[1]))
    b.place["fan"] = flat_fan
    b.beat({"rx": -14, "ry": -16}, 900)
    pleats = [k for k, (seg, _) in enumerate(fan.lines) if abs(seg[0][1] - seg[1][1]) < EPS]
    leg_fold = next(k for k, (seg, _) in enumerate(fan.lines) if abs(seg[0][0] - seg[1][0]) < EPS)
    fold_x = fan.lines[leg_fold][0][0][0]
    lean = math.degrees(math.acos(min(1.0, FOLD_PITCH / w)))
    b.fold("fan", deg=2 * lean, only=pleats)
    strip = b.panel_at("fan", hub[0], hub[1])
    ends = list(range(m)) + list(range(n - 1, m, -1))  # 片方の端から真ん中へ、次に反対の端から真ん中へ
    order = {"fan": {b.panel_at("fan", 20, (k + 0.5) * w): i for i, k in enumerate(ends)}}
    b.beat({"rx": -14, "ry": -16}, 4800, cam=1.0, order=order)
    b.place["fan"] = mul(rotate_y(lean), flat_fan)
    b.snapshot(text, {"rx": -14, "ry": -20}, 1100)

    # 9 像を扇の前に持ってきて、穴の列に糸を通し、像の穴へ結ぶ
    text = step(9)
    b.visible = {"fan", "figure"}
    view = {"rx": -14, "ry": -24}
    if len(fan.part.holes) < n:
        b.fail(fan.part.name, "糸を通す穴の列が折りの数より少ない")
    mark = by_key["base"].art[0]["pts"]
    mark_z = (min(y for _, y in mark) + max(y for _, y in mark)) / 2 - (g + bs / 2)  # 扇の足を貼る印の中心（台の中心から）
    b.place["figure"] = translate(-hole[0], -hole[1], -mark_z)
    b.beat(view, 800)
    _row(b)
    whole = b.extras["row"]
    b.extras["row"] = (whole[0], tuple(x + 0.1 for x in whole[0]), "fan")
    b.beat(view, 200)
    b.extras["row"] = whole
    b.beat(view, 1000)
    start = apply(b.world("fan", strip), hub)
    b.extras["thread"] = (start, tuple(x + 0.1 for x in start), "fan")
    b.beat(view, 200)
    _thread(b, strip, hub, hole)
    b.snapshot(text, view, 800)

    # 10 足を破線で折り、台の上から下ろして、足の糊代を台に貼る。像はまだ糸で下がっている
    text = step(10)
    b.visible = {"pusher", "base", "fan", "figure"}
    view = {"rx": -18, "ry": -32}
    foot_h = by_key["figure"].height - fh
    b.fold("fan", deg=90, only=[leg_fold])
    sn, cs = FOLD_PITCH / w, math.sqrt(1 - (FOLD_PITCH / w) ** 2)
    stand = [[-cs, sn, 0, 0], [0, 0, -1, 0], [-sn, -cs, 0, 0], [0, 0, 0, 1.0]]  # 糊代の面を上に、板は立てたまま横を向く
    settle = mul(stand, translate(-fold_x, -hub[1]))
    b.place["fan"] = mul(translate(0, top - 24, mark_z), settle)
    b.place["figure"] = translate(-hole[0], top - 24 - fh - foot_h - 0.5, 0)
    _thread(b, strip, hub, hole)
    _row(b)
    b.beat(view, 1100)
    b.place["fan"] = mul(translate(0, top, mark_z), settle)
    b.place["figure"] = translate(-hole[0], top - fh - foot_h - 0.5, 0)
    leg_tab = b.panel_at("fan", fold_x - 1, hub[1])
    b.nudge["fan"][leg_tab] = 0.2
    _thread(b, strip, hub, hole)
    _row(b)
    # 足の糊代は台の印に入るか（上から見た広さで比べる）
    seen = [apply(b.world("fan", leg_tab), pt) for pt in fan.panels[leg_tab].exterior.coords]
    onto_mark = [apply(b.world("base", center), pt) for pt in mark]
    glued = Polygon([(x, z) for x, _, z in seen]).buffer(0)
    if glued.intersection(Polygon([(x, z) for x, _, z in onto_mark]).buffer(0)).area < 0.8 * glued.area:
        b.fail(by_key["base"].name, "蛇腹の開く向きに立てると、足の糊代が台の印から外れる（印の向きが 90 度ちがう）")
    b.snapshot(text, view, 900)

    # 11 像の足を後ろへ折り、台の上に下ろして貼る
    text = step(11)
    b.fold("figure", deg=90)
    b.beat(view, 800)
    b.place["figure"] = translate(-hole[0], top - fh, 0)
    b.nudge["figure"][b.panel_at("figure", hole[0], fh + foot_h / 2)] = -0.2
    made, tied = _thread(b, strip, hub, hole)
    if math.hypot(made[0] - tied[0], made[1] - tied[1]) > THREAD_TOL:
        b.fail(b.sheets["figure"].part.name, "像の穴と扇の要の穴の高さが合わない（糸がまっすぐ通らない）")
    b.snapshot(text, view, 700)

    # 12 内筒を外筒の下から入れる。溝は下の端が開いているので、竹串は下から溝に入る
    text = step(12)
    b.visible = set(b.sheets)
    b.place["tube"] = translate(-side / 2, -tall / 2, side / 2)
    fixed = {key: b.place[key] for key in ("pusher", "base", "fan", "figure")}
    rod = b.extras["axle"] if "axle" in b.extras else None
    below = translate(0, tall / 2 - ph / 2 + tall + 10)
    for key, value in fixed.items():
        b.place[key] = mul(below, value)
    _carry(b, "axle", below)
    _thread(b, strip, hub, hole)
    _row(b)
    b.beat({"rx": -10, "ry": -30}, 900)
    # 内筒が外筒の底にある時まで上げる（内筒の中心は y=0 にある）
    move = translate(0, tall / 2 - ph / 2)
    for key, value in fixed.items():
        b.place[key] = mul(move, value)
    if rod:
        b.extras["axle"] = rod
    _carry(b, "axle", move)
    _thread(b, strip, hub, hole)
    _row(b)
    b.fits_inside("pusher", "tube")
    b.fits_inside("fan", "tube")
    above = -tall / 2 - b.bounds("fan")[0][1]
    if above > EPS:
        b.fail(fan.part.name, f"畳んだ扇が外筒の口から {above:.1f}mm 出る")
    _slot_check(b, p)
    b.snapshot(text, {"rx": -12, "ry": -30}, 1700, cam=1.0)

    # 組み立ての最後の動き（本人の追加 11-06「上にスライドさせて蛇腹が開く所まで」）: 竹串のつまみを上へ動かすと、内筒が上がり、扇が口から出て開く。
    # 開いた形は硬い面の折りでは表せないので、面を要のまわりに並べる（紙の形はそのまま）。
    b.step = len(words) + 1
    rise = translate(0, -p["push_amount"])
    hub0 = apply(b.world("fan", strip), hub)
    for key in ("pusher", "base", "figure"):
        b.place[key] = mul(rise, b.place[key])
    _carry(b, "axle", rise)
    opening = _open_fan(b, p, hub0, apply(rise, hub0), hub[0], fold_x, lean, -tall / 2)
    del b.extras["row"]  # 開くと穴の列は要に集まる
    _thread(b, strip, hub, hole)
    b.snapshot("", {"rx": -8, "ry": -24}, 3000, open=opening)
    return b


def _carry(b, name, m):
    if name in b.extras:
        s, e, owner = b.extras[name]
        b.extras[name] = (apply(m, s), apply(m, e), owner)


def _slot_check(b, p):
    """竹串が外筒の溝を通るか。底の時と、押し上げた時の両方で見る。溝は部品の座標で読む。"""
    tube = b.sheets["tube"]
    outline = tube.part.outline
    slot = [pt for pt in outline if 0 < pt[1] < p["tube_height"]]
    xs = sorted({pt[0] for pt in outline if pt[1] == p["tube_height"]})
    if "axle" not in b.extras or len(xs) < 3:
        return
    left, right = xs[1], xs[2]
    top = min(pt[1] for pt in slot if left <= pt[0] <= right)
    i = b.panel_at("tube", left - 1, p["tube_height"] / 2)
    inv = _invert_rigid(b.world("tube", i))
    s, e, _ = b.extras["axle"]
    for rise in (0.0, p["push_amount"]):
        a, c = apply(inv, _shift(s, -rise)), apply(inv, _shift(e, -rise))
        if abs(a[2] - c[2]) < EPS:
            b.fail(tube.part.name, "竹串が溝のある面を通らない")
            return
        t = a[2] / (a[2] - c[2])
        x, y = a[0] + (c[0] - a[0]) * t, a[1] + (c[1] - a[1]) * t
        if not (0 <= t <= 1):
            b.fail(tube.part.name, "竹串が短くて、溝から外へ出ない")
            return
        if not (left <= x <= right):
            b.fail(tube.part.name, f"竹串が溝から外れる（溝の幅 {left}〜{right}mm、竹串 {x:.1f}mm）")
            return
        if y < top:
            b.fail(tube.part.name, f"押し上げると竹串が溝の上の端に当たる（溝の端 {top}mm、竹串 {y:.1f}mm）")
            return


def _shift(p, dy):
    return (p[0], p[1] + dy, p[2])


def fan_pose(o, rise):
    """押し上げた割合 rise（0〜1）の時の、扇の面ごとの行列。頁の動きも同じ計算をする（web.kumitate の openShape）。

    要が筒の口より下の間は、口の幅が許す分だけ開く（11-04 の動画: 扇の先が口の幅いっぱいに出てきて、上がるほど広がる）。
    板は要を通る向きに放射に並び、開くほど面が前を向く。畳んだ時は穴の列が横に並ぶ。真ん中の板は足で台に貼ってあるので向きを変えない。
    """
    y = o["hub0"][1] + (o["hub1"][1] - o["hub0"][1]) * rise
    half = o["spread"] / 2
    below = y - o["rim"]
    start = math.degrees(math.atan2(o["mouth"], o["hub0"][1] - o["rim"]))
    now = min(half, math.degrees(math.atan2(o["mouth"], below))) if below > 0 else half
    t = max(0.0, min(1.0, (now - start) / (half - start)))
    out = {}
    for i, k in o["strips"].items():
        lean = -o["closed"] if k == o["m"] else (1 if k % 2 else -1) * (o["closed"] + (o["tilt"] - o["closed"]) * t)
        hub = (o["hub0"][0] + (k - o["m"]) * o["pitch"] * (1 - t), y, o["hub0"][2])
        out[i] = mul(translate(*hub), mul(rotate_z(-90 + (k - o["m"]) * o["each"] * t), mul(rotate_x(lean), translate(-o["hole_x"], -(k + 0.5) * o["w"]))))
    out[o["tab"]] = mul(out[o["mid"]], rotate_axis((o["fold_x"], 0, 0), (0, 1, 0), 90))
    return out


def _open_fan(b, p, hub0, hub1, hole_x, fold_x, closed, rim):
    """扇を開いた形を置く。開く角は雛形の計算のとおり。Returns 途中の形の計算に使う値。"""
    sheet = b.sheets["fan"]
    n, w, h = int(p["fold_count"]), p["fold_width"], p["fold_height"]
    m = n // 2
    spread = min(FAN_SHOWN, opening_bound_deg(n, w, h), clearance_limit_deg(p["tube_side"], p["pivot_above_rim"]))
    each = spread / (2 * max(m, n - 1 - m))  # 真ん中の板を立てたまま、両側が spread の半分の中に収まる刻み
    strips = {i: int(round(s.bounds[1] / w)) for i, s in enumerate(sheet.panels) if s.bounds[2] > fold_x + EPS}
    o = {"hub0": hub0, "hub1": hub1, "rim": rim, "mouth": p["tube_side"] / 2, "spread": spread, "each": each, "closed": closed,
         "tilt": math.degrees(math.acos(min(1.0, (h - hole_x) * math.radians(each) / w))), "pitch": FOLD_PITCH, "w": w, "hole_x": hole_x, "fold_x": fold_x,
         "m": m, "strips": strips, "tab": next(i for i in range(len(sheet.panels)) if i not in strips), "mid": next(i for i, k in strips.items() if k == m)}
    b.custom["fan"] = fan_pose(o, 1.0)
    b.place["fan"] = identity()
    return o


RECIPES = {"slider_fan": _slider_fan}


def _paper(template, p, source_id):
    """刷った紙の配置（compose の layout）。組み立ての書き方が無い時と読めない時は None。"""
    if template not in RECIPES:
        return None
    try:
        source = json.loads((ROOT / "data/sources" / f"{source_id}.json").read_text(encoding="utf-8"))
        return compose(template, p, source)[1]
    except (OSError, ValueError, KeyError, TypeError):
        return None


def assemble(source_id, hypothesis_id=None):
    """玩具のたたき台を組み立てる。Returns Bench。組み立ての書き方がまだ無い雛形は None。"""
    data = hypotheses.load(source_id)
    h = hypotheses.sheet_of(source_id) if hypothesis_id is None else next(x for x in data["hypotheses"] if x["id"] == hypothesis_id)
    template = h.get("template") or data.get("template", "slider_fan")
    if template not in RECIPES:
        return None
    tpl = TEMPLATES[template]
    p = {**tpl.DEFAULTS, **(h.get("params") or {})}
    paper = _paper(template, p, source_id)
    bench = RECIPES[template](p, paper["parts"] if paper else tpl.parts(p), paper)
    if bench is None:
        return None
    bench.paper = paper
    words = instructions.steps(p, template)
    made = [f for f in bench.frames if f["step"] <= len(words)]
    if [f["text"] for f in made] != words:
        bench.failures.append(Failure("F13.assembly", "手順", "組み立ての段と手順の文が 1 対 1 に並んでいない"))
    return bench


def main(argv=None):
    ap = argparse.ArgumentParser(prog="omochae.assembly", description="手順どおりに 3D で組み立てて、形の食い違いを数える")
    ap.add_argument("source")
    ap.add_argument("--hypothesis")
    ap.add_argument("--json", action="store_true", help="手順ごとの形を JSON で出す")
    try:
        args = ap.parse_args(argv)
    except SystemExit as e:
        return 0 if e.code in (0, None) else 4
    try:
        bench = assemble(args.source, args.hypothesis)
    except (KeyError, ValueError, OSError, StopIteration, ToolMissing) as e:
        print(f"検査できない: {type(e).__name__}: {e}", file=sys.stderr)
        return 4
    if bench is None:
        print("検査できない: この雛形の組み立てはまだ無い", file=sys.stderr)
        return 4
    if args.json:
        print(json.dumps(bench.frames, ensure_ascii=False))
    for f in bench.failures:
        print(f.line(), file=sys.stderr)
    print(f"手順 {max(f['step'] for f in bench.frames) - 1} 段を組み立てた。合わない所 {len(bench.failures)} 件")
    return 3 if bench.failures else 0


if __name__ == "__main__":
    sys.exit(main())
