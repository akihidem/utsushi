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

from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import polygonize, unary_union

from . import hypotheses, instructions
from .compose import TEMPLATES, compose
from .model import Failure, Part, ToolMissing
from .fan_model import clearance_limit_deg, opening_bound_deg
from .templates import pivot_counterweight
from .templates.pivot_counterweight import NECK_BACK

ROOT = pathlib.Path(hypotheses.__file__).resolve().parents[2]
EPS = 1e-6
CLOSE_TOL = 1.0  # mm。糊代が相手の面に届いたと読む離れ。紙の厚みと手の誤差を見込む
LINE_TOL = 5.0  # 度。穴が一直線に並ぶと読む傾き
THREAD_TOL = 1.5  # mm。糸の穴どうしがそろったと読む離れ
RULER_ZERO = 4.0  # mm。定規の端から 0 の目盛りまで
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


ROUND_SEGS = 32  # 丸い穴を近づける多角形の辺の数。はさみの道も面の穴も同じ点を使い、切る線と穴の縁をそろえる


def round_ring(x, y, r):
    """丸い穴の縁の点（部品の座標）。最初の点で閉じない。"""
    return [(x + r * math.cos(2 * math.pi * i / ROUND_SEGS), y + r * math.sin(2 * math.pi * i / ROUND_SEGS)) for i in range(ROUND_SEGS)]


def round_hole(x, y, r):
    return Polygon(round_ring(x, y, r))


@dataclass
class Sheet:
    """部品 1 つを、折り線で分けた面の集まりにした物。"""
    part: object
    extra: list = field(default_factory=list)  # 紙に刷っていないが、貼る時に折る線 [(線の 2 点, 種類)]
    slits: list = field(default_factory=list)  # 紙に切る線が無いが、折るには切り離す所 [線の 2 点]
    root_at: tuple = None  # 動かさない面の中の点。無ければ左端の面
    panels: list = field(default_factory=list)  # shapely の多角形（部品の座標、mm）
    tree: dict = field(default_factory=dict)  # 面 → (親の面, 折り線の番号)
    lines: list = field(default_factory=list)  # [(線の 2 点, "valley"|"mountain")]
    root: int = 0

    def __post_init__(self):
        self.lines = [(tuple(s), "valley") for s in self.part.valley] + [(tuple(s), "mountain") for s in self.part.mountain] + list(self.extra)
        whole = Polygon(self.part.outline).buffer(0)
        ring = list(self.part.outline) + [self.part.outline[0]]
        net = unary_union([LineString(ring)] + [LineString(seg) for seg, _ in self.lines] + [LineString(seg) for seg in self.slits])
        faces = [g for g in polygonize(net) if whole.buffer(1e-6).contains(g.representative_point())]
        for x, y, w, h in self.part.cuts:  # 中を切る四角は面の穴にする
            faces = [g.difference(box(x, y, x + w, y + h)) for g in faces]
        # 中を切る丸い穴も面の穴にする（虎の今の組の首の穴）。前の組と御来迎の部品には無いので、形は変わらない。
        # 丸い穴の欄が無い部品の型もある（虎の今の組の欄が入る前の型）ので、無ければ空と読む
        for x, y, r in getattr(self.part, "round_cuts", ()):
            faces = [g.difference(round_hole(x, y, r)) for g in faces]
        self.panels = sorted(faces, key=lambda s: (round(s.bounds[1], 3), round(s.bounds[0], 3)))
        if self.root_at is not None:
            self.root = self.at(*self.root_at)
        else:
            self.root = max(range(len(self.panels)), key=lambda i: self.panels[i].area) if self.part.key == "base" else self._first_panel()
        self._grow()

    def at(self, x, y):
        """部品の座標の点を含む面の番号。"""
        p = Point(x, y)
        for i, s in enumerate(self.panels):
            if s.buffer(1e-3).contains(p):
                return i
        raise ValueError(f"{self.part.key}: ({x}, {y}) を含む面が無い")

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

    def __init__(self, parts, extra=None, slits=None, roots=None):
        self.sheets = {q.key: Sheet(q, (extra or {}).get(q.key, []), (slits or {}).get(q.key, []), (roots or {}).get(q.key)) for q in parts}
        self.place = {q.key: identity() for q in parts}
        self.angles = {q.key: {} for q in parts}
        self.custom = {q.key: {} for q in parts}  # 面ごとの行列を直に置く物（硬い面の折りでは表せない形。扇を開いた形）
        self.nudge = {q.key: {} for q in parts}  # 面を自分の表の向きへずらす mm（貼って重なる面の前後を決める。形の検査には使わない）
        self.visible = set()
        self.paper_on = False  # 刷った紙が机にあるか
        self.scrap = True  # 溝の切り落とす所が、まだ紙についているか
        self.plug = True  # 面の中を切る四角が、まだ切られていないか
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
        return self.sheets[key].at(x, y)

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
                           "paper": self.paper_on, "scrap": self.scrap, "plug": self.plug, **tool})

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


def _ruler_step(b, paper, text, view, parts=None):
    """手順 1。刷った紙を机に置き、定規を外から刷った物差しへ持ってくる。"""
    b.visible = set(parts or b.sheets)
    b.paper_on = bool(paper)
    if paper:
        rx0, ry0 = paper["ruler"]
        at = (rx0 - paper["page"].w / 2 - RULER_ZERO, ry0 + 3.2 - paper["page"].h / 2)
        b.beat(view, 500, ruler=(paper["page"].w / 2 + 8, at[1] + 30))
        b.snapshot(text, view, 1400, ruler=at)
    else:
        b.snapshot(text, view)


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
    flat = {"rx": -8, "ry": 0}
    _ruler_step(b, paper, step(1), flat)

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

    # 8 扇を端から蛇腹に畳む。真ん中の板は正面を向いたまま、ほかの板が前後に重なる。畳んだ厚みは紙の厚さの数のとおりにする
    text = step(8)
    b.visible = {"fan"}
    flat_fan = mul(rotate_z(-90), translate(-hub[0], -hub[1]))
    b.place["fan"] = flat_fan
    b.beat({"rx": -14, "ry": -16}, 900)
    pleats = [k for k, (seg, _) in enumerate(fan.lines) if abs(seg[0][1] - seg[1][1]) < EPS]
    leg_fold = next(k for k, (seg, _) in enumerate(fan.lines) if abs(seg[0][0] - seg[1][0]) < EPS)
    fold_x = fan.lines[leg_fold][0][0][0]
    pleat = 180 - 2 * math.degrees(math.asin(min(1.0, p["paper_thickness"] / w)))
    b.fold("fan", deg=pleat, only=pleats)
    strip = b.panel_at("fan", hub[0], hub[1])
    ends = list(range(m)) + list(range(n - 1, m, -1))  # 片方の端から真ん中へ、次に反対の端から真ん中へ
    order = {"fan": {b.panel_at("fan", 20, (k + 0.5) * w): i for i, k in enumerate(ends)}}
    b.snapshot(text, {"rx": -12, "ry": -30}, 4800, cam=1.0, order=order)

    # 9 像を扇の前に持ってきて、穴の列に糸を通し、像の穴へ結ぶ
    text = step(9)
    b.visible = {"fan", "figure"}
    view = {"rx": -14, "ry": -24}
    if len(fan.part.holes) < n:
        b.fail(fan.part.name, "糸を通す穴の列が折りの数より少ない")
    mark = by_key["base"].art[0]["pts"]
    mark_z = min(y for _, y in mark) - (g + bs / 2)  # 扇の足を貼る印の奥の端（台の中心から）。真ん中の板はここに立つ
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
    stand = [[0, 1, 0, 0], [0, 0, -1, 0], [-1, 0, 0, 0], [0, 0, 0, 1.0]]  # 糊代の面を上に、真ん中の板は立てて正面を向く。扇は外筒の 1 面目に平行に開く
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
        b.fail(by_key["base"].name, "足の糊代が台の印から外れる")
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
    b.snapshot(text, {"rx": -12, "ry": -16}, 1700, cam=1.0)

    # 組み立ての最後の動き（本人の追加 11-06「上にスライドさせて蛇腹が開く所まで」）: 竹串のつまみを上へ動かすと、内筒が上がり、扇が口から出て開く。
    # 開いた形は硬い面の折りでは表せないので、面を要のまわりに並べる（紙の形はそのまま）。
    b.step = len(words) + 1
    rise = translate(0, -p["push_amount"])
    hub0 = apply(b.world("fan", strip), hub)
    for key in ("pusher", "base", "figure"):
        b.place[key] = mul(rise, b.place[key])
    _carry(b, "axle", rise)
    opening = _open_fan(b, p, hub0, apply(rise, hub0), hub[0], fold_x, pleat, -tall / 2)
    del b.extras["row"]  # 開くと穴の列は要に集まる
    _thread(b, strip, hub, hole)
    b.snapshot("", {"rx": -10, "ry": -10}, 3000, open=opening)
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

    真ん中の板は足で台に貼ってあるので正面を向いたまま。ほかの板は要の糸（前後の向き）のまわりに開き、外筒の 1 面目に平行な面に広がる。
    要が筒の口より下の間は、口の幅が許す分だけ開く（11-04 の動画: 扇の先が口の幅いっぱいに出てきて、上がるほど広がる）。
    紙はばねのように開くので、筒の中でも口の幅まで広がる。最初の少しの間（筒に隠れている間）に、その形になる。
    """
    y = o["hub0"][1] + (o["hub1"][1] - o["hub0"][1]) * rise
    half = o["spread"] / 2
    below = y - o["rim"]
    now = min(half, math.degrees(math.atan2(o["mouth"], below))) if below > 0 else half
    settle = min(1.0, rise / 0.08)
    t = max(0.0, min(1.0, now / half)) * settle * settle * (3 - 2 * settle)
    out = {}
    for i, k in o["strips"].items():
        off = k - o["m"]
        goal = 0.0 if k == o["m"] else (o["tilt"] if k % 2 else -o["tilt"])
        lean = (o["closed"] if off % 2 else 0.0) * (1 - t) + goal * t
        hub = (o["hub0"][0], y, o["hub0"][2] + off * o["pitch"] * (1 - t))
        out[i] = mul(translate(*hub), mul(rotate_z(-90 + off * o["each"] * t), mul(rotate_x(lean), translate(-o["hole_x"], -(k + 0.5) * o["w"]))))
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
         "tilt": math.degrees(math.acos(min(1.0, (h - hole_x) * math.radians(each) / w))), "pitch": p["paper_thickness"], "w": w, "hole_x": hole_x, "fold_x": fold_x,
         "m": m, "strips": strips, "tab": next(i for i in range(len(sheet.panels)) if i not in strips), "mid": next(i for i, k in strips.items() if k == m)}
    b.custom["fan"] = fan_pose(o, 1.0)
    b.place["fan"] = identity()
    return o


def _pivot_counterweight(p, parts, paper=None):
    """張子の首振り虎（pivot_counterweight）の組み立て。手順の文の順に、紙が実際に動く形を並べる。首を穴に入れる形だけ書いた。Returns Bench か None。"""
    if p["mount"] != "neck":
        return None
    # 虎の次の組（tora-v6 から）は 3D で組まない。この組み立ては前の組の胴（四角い首の穴・角のある箱・丸めた尾・片面の頭）の形で書いてあり、
    # v6 の丸い穴・角を落とした胴・立体の脚・両面の頭・上の面に立てる尾を組めない。組み立ての頁は文と絵だけを出す（御来迎の次の組と同じ扱い）。
    # 型紙エンジンには v6 を 3D で折る確かめ（fold3d）があるが、サイトの組み立ての頁に写すのは別の仕事
    if pivot_counterweight.set_no() >= pivot_counterweight.V6:
        return None
    by_key = {q.key: q for q in parts}
    body = by_key["body"]
    L, W, H, g = p["body_length"], p["body_width"], p["body_height"], p["glue"]
    top0, top1 = g, g + W
    b0, b1 = top1 + H, top1 + H + W
    cx, cy = H + L / 2, (b0 + b1) / 2
    words = instructions.steps(p, "pivot_counterweight")
    sw, ax = p["strip_width"], p["axle_height"]
    hw, hh = p["head_w"], p["head_h"]

    # 紙に切る線が無いが、箱に折るには切り離す所。糊代の根元が側面につながっている
    seams = [((H, b0 - g), (H, b0)), ((H + L, b0 - g), (H + L, b0)), ((H, b1), (H, b1 + g)), ((H + L, b1), (H + L, b1 + g))]
    plain = Sheet(body, root_at=(cx, cy))
    joined = plain.at(H - 1, b0 - 1) == plain.at(H + 1, b0 - 1)
    # 粘土は紙に無いので、丸い形で足す。尾は折り線の無い帯を丸めるので、短い面に分けて曲げる
    r = max(3.0, 5.0 * (p["weight_g"] / 3.0) ** (1 / 3))
    circle = [(r * math.cos(i * math.pi / 8), r * math.sin(i * math.pi / 8)) for i in range(16)]
    clay = Part(9, "clay", "粘土", circle, label="", art=[{"kind": "poly", "pts": circle, "fill": "#8d6b4a"}])
    tail_len = by_key["tail"].height
    each = tail_len / 8
    curl = [(((0, each * i), (by_key["tail"].width, each * i)), "valley") for i in range(1, 8)]
    b = Bench([*parts, clay], {"tail": curl}, {"body": seams}, {"body": (cx, cy)})
    if paper:
        pw, ph_page = paper["page"].w, paper["page"].h
        laid = {q.key: translate(q.x - pw / 2, q.y - ph_page / 2) for q in parts}
    else:
        laid, x = {}, -120.0
        for q in parts:
            laid[q.key] = translate(x, -q.height / 2)
            x += q.width + 6
    b.place.update(laid)

    def step(k):
        b.step = k
        return words[k - 1]

    # 1 刷った紙を机に置き、定規を物差しに当てる
    flat = {"rx": -8, "ry": 0}
    _ruler_step(b, paper, step(1), flat, parts=by_key)

    # 2 部品を切る。切った部品は紙から持ち上げ、胴の穴は竹串の先であける
    text = step(2)
    b.beat(flat, 300)
    for key in ("body", "head", "strip", "drop", "tail"):
        path = _outline(b, key)
        b.beat(flat, _cut_ms(path), cut=path)
        b.place[key] = mul(translate(0, 0, 8), laid[key])
        b.beat(flat, 350)
    for x, y, _ in body.holes:
        tip = apply(b.world("body", b.panel_at("body", x, y)), (x, y))
        b.extras["poke"] = (tip, (tip[0] + 8, tip[1] - 14, tip[2] + 34), "body")
        b.beat(flat, 450)
    del b.extras["poke"]
    b.snapshot(text, flat, 300)

    # 3 前の壁の四角い穴をカッターで切る。切った所が落ちる
    text = step(3)
    b.visible = {"body"}
    b.paper_on = False
    b.place["body"] = translate(-cx, -cy)
    view = {"rx": -8, "ry": 0}
    b.beat(view, 800)
    x, y, w, h = body.cuts[0]
    square = [apply(b.place["body"], pt)[:2] for pt in ((x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y))]
    b.beat(view, 1500, cut=square, knife=True)
    b.plug = False
    b.snapshot(text, view, 600)

    # 4 胴を箱に折る。まず文のとおり（谷折り）に組んで確かめ、図は絵を外にした形で折る。上の面はまだ閉じない
    text = step(4)
    if joined:
        b.fail(body.name, "糊代の根元 4 か所に切る線が無く、側面につながっている（切り込まないと箱に折れない）")
    side1, side2 = b.panel_at("body", cx, top1 + H / 2), b.panel_at("body", cx, b1 + H / 2)
    wall = {b.panel_at("body", H / 2, cy), b.panel_at("body", H + L + H / 2, cy)}
    flaps = [b.panel_at("body", H / 2, b0 - g / 2), b.panel_at("body", H / 2, b1 + g / 2), b.panel_at("body", H + L + H / 2, b0 - g / 2), b.panel_at("body", H + L + H / 2, b1 + g / 2)]
    top_lines = [k for k, (seg, _) in enumerate(b.sheets["body"].lines) if seg[0][1] == seg[1][1] and seg[0][1] in (top0, top1)]
    box_lines = [k for k in range(len(b.sheets["body"].lines)) if k not in top_lines]
    b.fold("body", deg=90, only=box_lines)
    lo, hi = b.bounds("body")
    middle = tuple((x + y) / 2 for x, y in zip(lo, hi))
    if b.faces_out("body", [side1, side2], middle):
        b.fail(body.name, "文のとおりに谷折りすると、絵のある面が箱の内側に入る")
    b.angles["body"] = {}
    home = mul(translate(0, H / 2, 0), mul(rotate_x(-90), translate(-cx, -cy)))
    b.place["body"] = home
    view = {"rx": -30, "ry": 30}
    b.beat(view, 1100)
    b.fold_back("body")
    for k in top_lines:
        del b.angles["body"][k]
    order = {"body": {**{i: 0 for i in flaps}, **{i: 1 for i in wall}, side1: 2, side2: 2}}
    fronts = {flaps[0]: side1, flaps[1]: side2, flaps[2]: side1, flaps[3]: side2}
    for flap, onto in fronts.items():
        b.closes("body", flap, onto)
        b.nudge["body"][flap] = -0.3
    b.snapshot(text, {"rx": -24, "ry": 32}, cam=1.0, order=order)

    # 5 首の帯を半分に折って貼る。穴が重なるか見る
    text = step(5)
    b.visible = {"strip"}
    strip = by_key["strip"]
    b.place["strip"] = translate(-strip.width / 2, -strip.height / 2)
    b.beat({"rx": -10, "ry": -16}, 800)
    b.fold("strip", deg=178)
    first, second = [apply(b.world("strip", b.panel_at("strip", hx, hy)), (hx, hy)) for hx, hy, _ in strip.holes]
    if math.dist(first, second) > THREAD_TOL:
        b.fail(strip.name, "半分に折っても、帯の 2 つの穴が重ならない")
    b.snapshot(text, {"rx": -14, "ry": -28}, 1300)

    # 6 帯の前の端に頭を貼る。帯は胴の中で軸の高さに来る向きで持つ
    text = step(6)
    b.visible = {"strip", "head"}
    hole_y = strip.holes[0][1]
    ax_x, ax_y = -L / 2 + NECK_BACK, H / 2 - ax
    strip_home = mul(translate(ax_x, ax_y, 0), mul(rotate_z(90), translate(-sw / 2, -hole_y)))
    head_home = mul(translate(ax_x - (strip.height - hole_y), ax_y, 0), mul(rotate_y(-90), translate(-hw / 2, -hh / 2)))
    away = translate(-60, 0, 0)
    b.place["strip"] = mul(away, strip_home)
    b.place["head"] = mul(translate(-30, 0, 0), mul(away, head_home))
    view = {"rx": -14, "ry": 34}
    b.beat(view, 1000)
    b.place["head"] = mul(away, head_home)
    b.snapshot(text, view, 900)

    # 7 帯を前の壁の穴に入れ、竹串を外から胴の穴と帯の穴に通す
    text = step(7)
    b.visible = {"body", "strip", "head"}
    view = {"rx": -16, "ry": 36}
    b.beat(view, 900)
    b.place["strip"], b.place["head"] = strip_home, head_home
    b.beat(view, 1300)
    line = b.holes_in_line("body", 0, 1)
    if line:
        if abs(line[0][1] - ax_y) > THREAD_TOL or abs(line[0][0] - ax_x) > THREAD_TOL:
            b.fail(body.name, "胴の穴と帯の穴がそろわない（竹串が通らない）")
        d = _unit(_sub(line[0], line[1]))
        out = tuple(x + y * 10 for x, y in zip(line[0], d))
        length = W + 20  # 用意する物の表と同じ長さ
        start = tuple(x - y * length for x, y in zip(out, d))
        b.extras["axle"] = (tuple(x + y * (length + 8) for x, y in zip(start, d)), tuple(x + y * (2 * length + 8) for x, y in zip(start, d)), "body")
        b.beat(view, 500)
        b.extras["axle"] = (start, out, "body")
    b.snapshot(text, view, 1300)

    # 8 重りの腕を上から入れて竹串に掛け、下の端に粘土を付ける。上の面が開いているので、上から見る
    text = step(8)
    b.visible = {"body", "strip", "head", "drop"}
    drop = by_key["drop"]
    hx, hy, _ = drop.holes[0]
    arm_home = translate(ax_x - hx, ax_y - hy, 5)
    if ax_y - hy + drop.height > H / 2:
        b.fail(drop.name, "重りの腕が胴の底に当たる")
    view = {"rx": -48, "ry": 22}
    b.place["drop"] = mul(translate(0, -90, 0), arm_home)
    b.beat(view, 900)
    b.place["drop"] = arm_home
    b.beat(view, 1100)
    b.visible = {"body", "strip", "head", "drop", "clay"}
    clay_home = translate(ax_x, ax_y + p["weight_below_axle"], 5.4)
    b.place["clay"] = mul(translate(0, -90, 0), clay_home)
    b.beat(view, 200)
    b.place["clay"] = clay_home
    b.snapshot(text, view, 1000)

    # 9 頭の傾きを見る。軸のまわりに少し動かして止める
    text = step(9)
    moving = ("strip", "head", "drop", "clay")
    homes = {key: b.place[key] for key in moving}

    def nod(deg):
        turn = mul(translate(ax_x, ax_y, 0), mul(rotate_z(deg), translate(-ax_x, -ax_y, 0)))
        for key in moving:
            b.place[key] = mul(turn, homes[key])

    view = {"rx": -30, "ry": 34}
    nod(7)
    b.beat(view, 900)
    nod(-4)
    b.beat(view, 700)
    nod(0)
    b.snapshot(text, view, 600)

    # 10 上の面を閉じる
    text = step(10)
    b.fold_back("body")
    top_flap = b.panel_at("body", cx, g / 2)
    b.closes("body", top_flap, side2)
    b.nudge["body"][top_flap] = -0.3
    b.snapshot(text, {"rx": -24, "ry": 32}, 1800)

    # 11 尾を丸くして、後ろに貼る。絵を外にして丸める
    text = step(11)
    b.visible = {"body", "strip", "head", "drop", "clay", "tail"}
    view = {"rx": -14, "ry": -38}
    width = by_key["tail"].width
    upward = [[0, 0, -1, 0], [0, -1, 0, 0], [-1, 0, 0, 0], [0, 0, 0, 1.0]]  # 帯の長い辺を上へ、絵の面を胴の側へ
    tail_home = mul(translate(L / 2 + 0.3, -H / 2 + 12, 0), mul(upward, translate(-width / 2, -each / 2)))
    b.place["tail"] = mul(translate(36, 0, 0), tail_home)
    b.beat(view, 900)
    b.fold_back("tail", deg=45)
    b.beat(view, 1300)
    b.place["tail"] = tail_home
    b.snapshot(text, view, 900)

    # できあがり: 頭に触れると、軸のまわりに揺れて止まる。組み立ての最後の動き
    b.step = len(words) + 1
    view = {"rx": -12, "ry": 42}
    nod(0)
    b.beat(view, 1100)
    for deg in (10, -8, 5, -3):
        nod(deg)
        b.beat(view, 620)
    nod(0)
    b.snapshot("", view, 500)
    return b


RECIPES = {"slider_fan": _slider_fan, "pivot_counterweight": _pivot_counterweight}


def _paper(template, p, source_id, title=None):
    """刷った紙の配置（compose の layout）。読めない時は None。組み立ての書き方があるかは呼ぶ側が見る（JSON で描く雛形は書き方が無くてもよい）。
    title は机の上の紙に刷られる題（_sheet_title）。前は compose の既定の題のままで、玩具の頁の 3D の紙に「版 1」が残った
    （窓口の決定 (a)「紙の題と窓の札も組の番号に」・#513）。"""
    try:
        source = json.loads((ROOT / "data/sources" / f"{source_id}.json").read_text(encoding="utf-8"))
        return compose(template, p, source, title=title)[1]
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _same(a, b):
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool) and not isinstance(b, bool):
        return abs(a - b) < 1e-9
    return a == b


def _sheet_title(data, tpl, p, h=None):
    """3D の机の上の紙の題。刷る紙の題（hypotheses.print_sheet「玩具の名 型紙 仮説「…」版 N」）から、「…」の仮説の名を外した形
    （玩具の名 型紙 仮説 版 N。11-08 から仮説の印 A・C は出さない）。版の字は hypotheses.paper_label（今の組は組の番号・前の組は前の題「版 1」）。
    なぜ: 前は compose の既定の題「玩具の名 型紙（雛形の呼び名）版 N」で、雛形の呼び名（御来迎は「内筒を下から押し上げる」）が
    今のたたき台（H-C「柄を下から押し上げる」）と違う仮説の名に読め、しかも括弧の中が動き方の答えを言っていた（学ぶ人に動き方を先に見せない
    決まり J-013 に当たる。別の系統の検品の気づき 11-07 夕）。仮説の名（「…」）も動き方を言うので外す。
    題を長くすると部品の配置が動き、型紙エンジンの 3D の JSON と寸法が合わなくなる（tests/test_tora_v7_3d が部品の位置で見る）。
    この形は前の題より短く、1 行のまま収まる"""
    # 仮説の印（A・C）は出さない（本人の言葉 11-08・hypotheses.SHOWN）。刷る紙の題と同じ呼び名
    named = f" {hypotheses.SHOWN}" if h else ""
    return f"{data['toy']} 型紙{named} {hypotheses.paper_label(data, 1)}"


def _from_engine(template, tpl, p, source_id, title=None):
    """今の組の作り方の 3D を、型紙エンジンが出した JSON（data/kumitate/<組の名>.json）から読む（決定 2026-11-07。assembly_json の注）。
    Returns 組み立て（assembly_json.Shown）・None（JSON はあるが、刷る紙と寸法か形が違う）・False（今の組の JSON が無い。前の組の書き方で組む）。

    寸法か形が違う JSON は使わない（違う紙の立体を見せない）。その時は組み立てを出さず、頁は文と絵だけにする。違いは試験が見つける。"""
    from . import assembly_json  # assembly_json が assembly を読むので、読み込みの輪にしないためにここで読む

    doc = assembly_json.load(getattr(tpl, "SHEET_SET", ""))
    if doc is None:
        return False
    if any(not _same(p.get(k), v) for k, v in (doc.get("params") or {}).items()):
        return None
    paper = _paper(template, p, source_id, title)
    parts = paper["parts"] if paper else tpl.parts(p)
    if assembly_json.part_gaps(doc, parts):
        return None
    return assembly_json.bench_of(doc, parts, instructions.steps(p, template), paper)


def assemble(source_id, hypothesis_id=None):
    """玩具のたたき台を組み立てる。Returns Bench（今の組の JSON がある時は、それを読んだ assembly_json.Shown）。組み立ての書き方も JSON も無い雛形は None。"""
    data = hypotheses.load(source_id)
    h = hypotheses.sheet_of(source_id) if hypothesis_id is None else next(x for x in data["hypotheses"] if x["id"] == hypothesis_id)
    template = h.get("template") or data.get("template", "slider_fan")
    if template not in TEMPLATES:
        return None
    tpl = TEMPLATES[template]
    p = {**tpl.DEFAULTS, **(h.get("params") or {})}
    title = _sheet_title(data, tpl, p, h)
    shown = _from_engine(template, tpl, p, source_id, title)
    if shown is not False:
        return shown
    if template not in RECIPES:
        return None
    paper = _paper(template, p, source_id, title)
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
