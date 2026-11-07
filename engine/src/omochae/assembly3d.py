"""作り方の 3D を、組み方の文と 1 対 1 の段ごとの形にして JSON で出す。

窓口の決定（2026-11-07 カード 020154）「サイトの3Dの作り直しは推し(a)、エンジンが JSON で出す形で進めてください。」による。
サイトの「組み立てを立体で見る」は、この JSON を読んで描く（形の決めは ~/work/hackathon-grove/state/3d-json/FORMAT-v1.md と同じ）。

判断の芯:
- 紙の形は刷る部品（雛形の parts）から読み、折り線で分けた面を omochae.fold3d.fold で硬いまま折る。完成図を別に描かない。
  紙か寸法を直すと 3D も一緒に変わる。たわみ・紙の厚み・糊は入れない（形の確かめで、動くかは確かめない）。
- 段は組み方の文（steps）と 1 対 1。段ごとに、部品ごとの置き場（根の面の行列）と、折り線ごとの角と、面ごとの行列を出す。
  描く側は面ごとの行列だけで描いてもよく、折る途中を動かすなら面のつながり（tree）と角（angles）を使う。
- 座標はサイトの組み立ての頁と同じ: 長さは mm、x が右・y が下・z が見る人の方。部品の座標は刷った紙の上の座標（y は下）で、刷った面は +z。
  行列は CSS の matrix3d と同じ列優先の 16 個で、部品の座標の点 (x, y, 0, 1) を世界の点へ写す。
- 部品を置く所は、刷った位置の印（脚の四角・尾の四角・軸の穴）から決める（印と貼った物の所がずれないため）。
"""
import json
import math
import pathlib
import sys

from .compose import TEMPLATES
from .fold3d import FoldError, fold

FORMAT = "omochae-assembly-3d/1"
TAIL_HOLD = 30.0  # 尾を貼る前に、貼る四角の上に持つ高さ mm
ROOT = pathlib.Path(__file__).resolve().parents[2]

# 4×4 の行列は行の並び（[[...], ...]）で持ち、JSON に出す時だけ列優先の 16 個にする
I4 = [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]]
# fold3d は頁の点を (x, -y, 0) に持ち上げ、y が上の 3D で折る。サイトの座標（y が下）へは y を裏返す。持ち上げと戻しは同じ行列
FLIP = [[1.0, 0.0, 0.0, 0.0], [0.0, -1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]]


def mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def apply(m, p):
    x, y, z = p
    return tuple(m[i][0] * x + m[i][1] * y + m[i][2] * z + m[i][3] for i in range(3))


def css(m):
    """列優先の 16 個（CSS の matrix3d と同じ順）。"""
    return [round(m[r][c], 5) for c in range(4) for r in range(4)]


def _sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def _unit(a):
    n = math.sqrt(sum(x * x for x in a))
    return tuple(x / n for x in a)


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _frame(p0, p1, p2):
    """3 点の正規直交の向き（列が e1・e2・e3）。e1 は p0→p1、e3 は 3 点の面の向き。"""
    e1 = _unit(_sub(p1, p0))
    e3 = _unit(_cross(e1, _sub(p2, p0)))
    e2 = _cross(e3, e1)
    return (e1, e2, e3)


def rigid(src, dst):
    """src の 3 点を dst の 3 点へ写す剛体の変換（4×4）。3 点の形が同じ（距離が同じ）時に正しい。"""
    a, b = _frame(*src), _frame(*dst)
    # R = B · Aᵀ（A・B は列が向きの行列）
    R = [[sum(b[k][i] * a[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
    t = _sub(dst[0], tuple(sum(R[i][j] * src[0][j] for j in range(3)) for i in range(3)))
    return [R[0] + [t[0]], R[1] + [t[1]], R[2] + [t[2]], [0.0, 0.0, 0.0, 1.0]]


def translate(x=0.0, y=0.0, z=0.0):
    return [[1.0, 0.0, 0.0, x], [0.0, 1.0, 0.0, y], [0.0, 0.0, 1.0, z], [0.0, 0.0, 0.0, 1.0]]


def _from_fold(T):
    R, t = T
    return [list(R[0]) + [t[0]], list(R[1]) + [t[1]], list(R[2]) + [t[2]], [0.0, 0.0, 0.0, 1.0]]


class Sheet:
    """刷る部品 1 つを、折り線で分けた面にした物。面の番号は fold3d.fold の並び（根の面が 0）で、角を変えても同じ。"""

    def __init__(self, part):
        self.part = part
        self.kind = {tuple(map(tuple, ln)): "valley" for ln in part.valley}
        self.kind.update({tuple(map(tuple, ln)): "mountain" for ln in part.mountain})
        flat = fold(part, deg=0)
        self.panels = [[(round(x, 4), round(y, 4)) for x, y in f.poly.exterior.coords[:-1]] for f in flat]
        self.rows = {i: {"parent": f.parent, "hinge": [list(f.hinge[0]), list(f.hinge[1])], "kind": self.kind[tuple(map(tuple, f.hinge))]}
                     for i, f in enumerate(flat) if f.parent is not None}

    def local(self, angles):
        """折り線ごとの角（度。無い線は 0）で折った時の、面ごとの行列（部品の座標 → 根の面を動かさない 3D、サイトの向き）。"""
        faces = fold(self.part, deg=0, angles=angles)
        return [mul(FLIP, mul(_from_fold(f.T), FLIP)) for f in faces], faces

    def panel_of(self, x, y):
        """部品の座標の点を含む面の番号。"""
        from shapely.geometry import Point, Polygon
        pt = Point(x, y)
        return min(range(len(self.panels)), key=lambda i: Polygon(self.panels[i]).distance(pt))


def pose(sheet, angles, place):
    """1 つの部品の、置き場・角・面ごとの行列。place は根の面を動かさない 3D から世界への行列。"""
    local, faces = sheet.local(angles)
    world = [mul(place, m) for m in local]
    by_face = {}
    for i, f in enumerate(faces):
        if f.hinge is not None:
            by_face[str(i)] = round(abs(angles.get(f.hinge, 0.0)), 4)
    return {"place": css(world[0]), "angles": by_face, "panels": {str(i): css(m) for i, m in enumerate(world)}}, world


def place_by(sheet, angles, pts_local, pts_world):
    """部品の座標の 3 点 pts_local が、折った後に世界の pts_world に来る置き場。"""
    local, _ = sheet.local(angles)
    idx = [sheet.panel_of(x, y) for x, y in pts_local]
    pre = [apply(local[i], (x, y, 0.0)) for i, (x, y) in zip(idx, pts_local)]
    return rigid(pre, pts_world)


def part_json(q):
    """刷る部品の形と絵（部品の座標）。"""
    s = Sheet(q)
    labels = [{"text": t, "x": x, "y": y, "size": 2.8} for t, x, y in (q.label_lines or [(q.label, *q.label_xy)]) if t]
    return {"key": q.key, "number": q.number, "name": q.name, "outline": [list(p) for p in q.outline],
            "panels": [{"id": i, "poly": [list(p) for p in poly]} for i, poly in enumerate(s.panels)],
            "tree": {"root": 0, "rows": {str(i): r for i, r in s.rows.items()}},
            "art": q.art, "glue": q.glue, "holes": [list(h) for h in q.holes], "round_cuts": [list(c) for c in q.round_cuts],
            "labels": labels}, s


def _signed_turn(parent, child, hinge):
    """子の面が親の面に対して、折り線の 1 点目から 2 点目の向きのまわりに回った角（度・右ねじで正）。サイトの頁の turn と同じ向き。"""
    rel = mul(_invert(parent), child)
    (x1, y1), (x2, y2) = hinge
    u = _unit((x2 - x1, y2 - y1, 0.0))
    R = [row[:3] for row in rel[:3]]
    vee = (R[2][1] - R[1][2], R[0][2] - R[2][0], R[1][0] - R[0][1])
    s = sum(a * b for a, b in zip(u, vee)) / 2
    c = (R[0][0] + R[1][1] + R[2][2] - 1) / 2
    return math.degrees(math.atan2(s, c))


def _invert(m):
    """剛体の変換の逆。"""
    R = [row[:3] for row in m[:3]]
    t = [m[0][3], m[1][3], m[2][3]]
    Rt = [[R[j][i] for j in range(3)] for i in range(3)]
    ti = [-sum(Rt[i][k] * t[k] for k in range(3)) for i in range(3)]
    return [Rt[0] + [ti[0]], Rt[1] + [ti[1]], Rt[2] + [ti[2]], [0.0, 0.0, 0.0, 1.0]]


def _circle(cx, cy, r, n=48):
    return [[round(cx + r * math.cos(2 * math.pi * k / n), 4), round(cy + r * math.sin(2 * math.pi * k / n), 4)] for k in range(n)]


class Scene:
    """部品の面と、刷った紙の上の置き場。段ごとの形（POSE）を作る。"""

    def __init__(self, layout, paper_gap=30.0):
        self.page = layout["page"]
        self.parts = {q.key: q for q in layout["parts"]}
        self.sheets = {k: Sheet(q) for k, q in self.parts.items()}
        # 刷った紙は机の上（y = 0）の、組み立てる所の奥（z が負）に置く。頁の x はそのまま x、頁の y は z
        self.paper_z0 = -(self.page.h + paper_gap)

    def on_paper(self, key, lift=0.0):
        """部品が、刷った紙の上の刷った所に、刷った面を上にして寝ている置き場。"""
        q = self.parts[key]
        flat = {}
        src = [(0.0, 0.0), (10.0, 0.0), (0.0, 10.0)]
        dst = [(q.x + x - self.page.w / 2, -lift, self.paper_z0 + q.y + y) for x, y in src]
        return place_by(self.sheets[key], flat, src, dst)

    def state(self, key, angles, place):
        sheet = self.sheets[key]
        local, faces = sheet.local(angles)
        world = [mul(place, m) for m in local]
        turns, ang = {}, {}
        for i, f in enumerate(faces):
            if f.parent is not None:
                turns[str(i)] = round(_signed_turn(local[f.parent], local[i], f.hinge), 4)
                ang[str(i)] = round(abs(angles.get(f.hinge, 0.0)), 4)
        return {"place": css(world[0]), "turns": turns, "angles": ang, "panels": {str(i): css(m) for i, m in enumerate(world)}}, world

    def pose(self, states, hidden=(), rods=None, balls=None, view=None, on_paper=False, tool=None, custom=(), act=None, moving=None):
        """POSE 1 枚。act（手の種類: cut・fold・thread・place・open・move）と moving（動く部品）は、書き方が言わなければ、
        前の POSE との違いから決める（切る道具 → cut、custom → open、折る角が変わる → fold、棒が出る → thread、置き場が変わる → move）。"""
        out = {"parts": {}, "hidden": sorted(hidden), "rods": rods or {}, "balls": balls or {},
               "view": view or {"rx": -20, "ry": 30}, "on_paper": bool(on_paper)}
        for key, (angles, place) in states.items():
            if key in hidden:
                continue
            st, _ = self.state(key, angles, place)
            if key in custom:
                st["custom"] = True
            out["parts"][key] = st
        if tool:
            out["tool"] = tool
        prev = getattr(self, "_prev", None)
        changed_place = sorted(k for k, st in out["parts"].items() if prev and k in prev["parts"] and st["place"] != prev["parts"][k]["place"])
        changed_fold = sorted(k for k, st in out["parts"].items() if prev and k in prev["parts"] and st["turns"] != prev["parts"][k]["turns"])
        new_rods = sorted(k for k in out["rods"] if not prev or k not in prev["rods"])
        # 動く物には、部品のほかに、出た・動いた棒と、動いた粘土の玉も入れる（竹串を通す手・揺れる時の粘土を、サイトが名で引けるように）
        moved = {k for k, r in out["rods"].items() if prev and k in prev["rods"] and r != prev["rods"][k]}
        moved |= {k for k, b in out["balls"].items() if not prev or prev["balls"].get(k) != b}
        # 消えた棒・玉と、出た・隠れた部品も動く物（取り外す手・出す手を、空の moving と place に読み違えないため。見直しの指摘）
        gone = {k for k in (prev["rods"] if prev else {}) if k not in out["rods"]} | {k for k in (prev["balls"] if prev else {}) if k not in out["balls"]}
        shown = {k for k in out["parts"] if prev and k not in prev["parts"]} | {k for k in (prev["parts"] if prev else {}) if k not in out["parts"]}
        if moving is None:
            moving = sorted(set(changed_place) | set(changed_fold) | set(custom) | set(new_rods) | moved | gone | shown)
        if act is None:
            act = ("cut" if tool and tool.get("kind") in ("scissors", "knife") else "open" if custom else "fold" if changed_fold
                   else "thread" if new_rods else "move" if (changed_place or gone or shown) else "place")
        out["act"], out["moving"] = act, sorted(moving)
        self._prev = out
        return out

    def paper_place(self):
        """刷った紙の行列（紙の座標 → 世界）。紙は机の面（y = 0）に、刷った面を上にして、組み立てる所の奥に寝ている。"""
        return css([[1.0, 0.0, 0.0, -self.page.w / 2], [0.0, 0.0, -1.0, 0.0], [0.0, 1.0, 0.0, self.paper_z0], [0.0, 0.0, 0.0, 1.0]])

    def part_list(self):
        out = []
        for key, q in self.parts.items():
            data, sheet = part_json(q)
            from shapely.geometry import Point, Polygon
            for panel in data["panels"]:
                poly = Polygon(panel["poly"])
                inner = [_circle(cx, cy, r) for cx, cy, r in q.round_cuts if poly.contains(Point(cx, cy))]
                inner += [[[x, y], [x + w, y], [x + w, y + h], [x, y + h]] for x, y, w, h in q.cuts if poly.contains(Point(x + w / 2, y + h / 2))]
                if inner:
                    panel["inner"] = inner
            out.append(data)
        return out


def _world_pt(world, sheet, x, y):
    """部品の座標の点の、世界の点（その点を含む面の行列で写す）。"""
    return apply(world[sheet.panel_of(x, y)], (x, y, 0.0))


def rot_x(deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return [[1.0, 0.0, 0.0, 0.0], [0.0, c, -s, 0.0], [0.0, s, c, 0.0], [0.0, 0.0, 0.0, 1.0]]


def rot_z(deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return [[c, -s, 0.0, 0.0], [s, c, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]]


def _all_lines(part, deg):
    return {tuple(map(tuple, ln)): float(deg) for ln in list(part.valley) + list(part.mountain)}


def _tiger(scene, p):
    """張子の首振り虎（首の形）の段ごとの形。手順の文（pivot_counterweight.steps）と 1 対 1。

    判断の芯:
    - 胴は箱に折る角を tests/test_pivot_fold3d.py と同じにする（角の面の 4 本は 45°、ほかは 90°）。上の面は手順 11 まで開けておく
      （上の面の 2 本の線を 0°）。胴の底の面を机に置く（脚を貼るまでは机の上、貼った後は脚の高さだけ上）。
    - 軸は胴の 2 つの穴の真ん中を通る（刷った穴の所から読む）。首の帯・頭・重りの腕・粘土は軸に対して置き、揺れる時は軸のまわりに回す。
    - 帯は穴の側の端が軸、反対の端（前）が頭の真ん中（揺れの式が頭の真ん中を帯の先に置くのと同じ）。頭は両面なら 180° 折る。
    - 脚の角筒の上の口は、胴の底の四角（位置の印）に、尾の糊代は上の面の後ろの四角に合わせる（印と貼った物がずれないため）。
    - できあがりの動きは、静かな時の傾きのまわりに ±MIN_SWING の中で揺れて、静かな時の傾きで止まる。型紙の当たりの検査
      （pivot_counterweight.swing_range・fit_gaps）が見る角と同じにする（見直しの指摘: 前は水平のまわりに 12° まで揺らし、
      検査が見ない角で、粘土の玉と腕が前の壁に入って見えた）。
    """
    from .templates import pivot_counterweight as pc
    if p["mount"] != "neck":
        return None
    parts, S = scene.parts, scene.sheets
    H, L, W, c = p["body_height"], p["body_length"], p["body_width"], p["body_round"]
    d = c / math.sqrt(2) if c else 0
    Wt, Hs, g = W - 2 * d, H - d, p["glue"]
    top0, top1 = g, g + Wt
    b0 = top1 + c + Hs
    b1 = b0 + W
    legh = p["leg_height"]
    legs = [k for k in ("leg1", "leg2", "leg3", "leg4") if k in parts]

    # 胴の折る角（閉じた箱）と、上の面を開けた角
    closed = _all_lines(parts["body"], 90)
    rows = sorted((ln for ln in closed if ln[0][1] == ln[1][1] and ln[0][0] == H and ln[1][0] == H + L), key=lambda ln: ln[0][1])
    if c:
        for i in (0, 1, 2, len(rows) - 1):
            closed[rows[i]] = 45.0
    opened = dict(closed)
    for ln in rows:
        if abs(ln[0][1] - top0) < 1e-9 or abs(ln[0][1] - top1) < 1e-9:
            opened[ln] = 0.0

    def body_place(angles, ybot):
        src = [(H, b0), (H + L, b0), (H, b1)]
        dst = [(0.0, ybot, W / 2), (L, ybot, W / 2), (0.0, ybot, -W / 2)]
        return place_by(S["body"], angles, src, dst)

    def axle_of(angles, place):
        local, _ = S["body"].local(angles)
        world = [mul(place, m) for m in local]
        (x1, y1, _), (x2, y2, _) = (_world_pt(world, S["body"], hx, hy) for hx, hy, _ in parts["body"].holes)
        return (x1 + x2) / 2, (y1 + y2) / 2, world

    # 首の帯・頭・腕を、軸を原点にした「立てた」置き場で決める（後で机に寝かせる・軸へ動かす・揺らす）
    sw = p["strip_width"]
    strip_len = p["neck_length"] + 12
    band = {ln: 180.0 for ln in _all_lines(parts["strip"], 0)}
    head_ang = {ln: 180.0 for ln in _all_lines(parts["head"], 0)}
    hd = parts["head"]
    fy = hd.mountain[0][0][1] if hd.mountain else None
    w, h = p["head_w"], p["head_h"]
    head_mid = (w / 2, 1.5 * fy) if fy is not None else (w / 2, h / 2)
    tip = -(strip_len - pc.STRIP_HOLE)  # 帯の先（頭の真ん中）の、軸からの x
    za = 0.6  # 腕は帯の横（重ならないように少しずらす。見せる時だけ）

    def neck_places(G):
        """軸を原点にした立てた置き場に、G（4×4）を掛けた置き場。"""
        strip = place_by(S["strip"], band, [(sw / 2, pc.STRIP_HOLE), (sw / 2, pc.STRIP_HOLE + 10), (sw, pc.STRIP_HOLE)],
                         [apply(G, (0.0, 0.0, 0.0)), apply(G, (-10.0, 0.0, 0.0)), apply(G, (0.0, sw / 2, 0.0))])
        hx, hy = head_mid
        head = place_by(S["head"], head_ang, [(hx, hy), (hx + 10, hy), (hx, hy + 10)],
                        [apply(G, (tip, 0.0, 0.0)), apply(G, (tip + 10, 0.0, 0.0)), apply(G, (tip, 10.0, 0.0))])
        drop = place_by(S["drop"], {}, [(4.0, 4.0), (4.0, 14.0), (14.0, 4.0)],
                        [apply(G, (0.0, 0.0, za)), apply(G, (0.0, 10.0, za)), apply(G, (10.0, 0.0, za))]) if "drop" in parts else None
        clay = apply(G, (p["clay_back"], p["weight_below_axle"], za))  # 粘土は 5 重りの腕の下の穴（v7 から軸の clay_back 後ろ）
        return strip, head, drop, clay

    cur = {k: ({}, scene.on_paper(k)) for k in parts}
    steps_text = pc.steps(p)
    steps = []
    view_side = {"rx": -15, "ry": 25}

    def snap(**kw):
        return scene.pose({k: v for k, v in cur.items()}, **kw)

    page_w = scene.page.w
    # 1. 物差し
    ruler = None
    steps.append([snap(on_paper=True, view={"rx": -70, "ry": 0}, tool=ruler, act="place", moving=[])])
    # 2. 切る・小さい穴（紙から部品を切り離す）
    steps.append([snap(on_paper=True, view={"rx": -70, "ry": 0}, tool={"kind": "scissors"}), snap(view={"rx": -70, "ry": 0}, act="cut", moving=sorted(parts))])
    # 3. 前の壁の丸い穴を切る
    steps.append([snap(view={"rx": -70, "ry": 0, "focus": ["body"]}, tool={"kind": "knife"}, moving=["body"])])
    # 4. 胴を箱に（上の面は開ける）
    cur["body"] = ({}, body_place({}, 0.0))
    a = snap(view={"rx": -35, "ry": 30, "focus": ["body"]})
    cur["body"] = (opened, body_place(opened, 0.0))
    steps.append([a, snap(view={"rx": -20, "ry": 30, "focus": ["body"]})])
    xa, ya, _ = axle_of(opened, cur["body"][1])
    # 首の組を机に寝かせる置き場（胴の前の机の上。立てた置き場を x の軸のまわりに 90° 倒す）
    lay = mul(translate(-70.0, 0.0, 0.0), rot_x(90))
    # 5. 帯を半分に折る
    s_lay, h_lay, d_lay, _ = neck_places(lay)
    cur["strip"] = ({}, place_by(S["strip"], {}, [(sw / 2, pc.STRIP_HOLE), (sw / 2, pc.STRIP_HOLE + 10), (sw, pc.STRIP_HOLE)],
                                [apply(lay, (0.0, 0.0, 0.0)), apply(lay, (-10.0, 0.0, 0.0)), apply(lay, (0.0, sw / 2, 0.0))]))
    a = snap(view={"rx": -50, "ry": 10, "focus": ["strip"]})
    cur["strip"] = (band, s_lay)
    steps.append([a, snap(view={"rx": -50, "ry": 10, "focus": ["strip"]})])
    # 6. 頭を折って帯の先を挟む
    hx, hy = head_mid
    cur["head"] = ({}, place_by(S["head"], {}, [(hx, hy), (hx + 10, hy), (hx, hy + 10)],
                                [apply(lay, (tip - 30, 0.0, 0.0)), apply(lay, (tip - 20, 0.0, 0.0)), apply(lay, (tip - 30, 10.0, 0.0))]))
    a = snap(view={"rx": -50, "ry": 10, "focus": ["strip", "head"]})
    cur["head"] = (head_ang, h_lay)
    steps.append([a, snap(view={"rx": -50, "ry": 10, "focus": ["strip", "head"]})])
    # 7. 帯を前の壁の穴に入れ、竹串を通す（立てて穴の前へ → 軸の所へ → 竹串）
    front = mul(translate(xa - 40.0, ya, 0.0), I4)
    s7, h7, _, _ = neck_places(front)
    cur["strip"], cur["head"] = (band, s7), (head_ang, h7)
    a = snap(view=view_side)
    at = translate(xa, ya, 0.0)
    s7, h7, d7, clay7 = neck_places(at)
    cur["strip"], cur["head"] = (band, s7), (head_ang, h7)
    b = snap(view=view_side, act="thread", moving=["strip", "head"])
    skewer = {"skewer": {"from": [xa, ya, (W + 20) / 2], "to": [xa, ya, -(W + 20) / 2]}}
    steps.append([a, b, snap(view=view_side, rods=skewer)])
    # 8. 腕に竹串・粘土・仮留め
    cur["drop"] = ({}, d7)
    a = snap(view=view_side, rods=skewer, act="thread", moving=["drop"])
    clay = {"clay": {"at": list(clay7)}}
    steps.append([a, snap(view=view_side, rods=skewer, balls=clay, act="place", moving=["clay"])])
    # 9. 腕を帯に貼る
    steps.append([snap(view=view_side, rods=skewer, balls=clay, act="place", moving=["drop"])])
    # 10. 脚を角筒にして底の四角へ（胴の組を脚の高さだけ上げる）
    leg_ang = {k: _all_lines(parts[k], 90) for k in legs}
    if legs:
        for i, k in enumerate(legs):
            cur[k] = (leg_ang[k], mul(translate(L + 20 + 12 * i, 0.0, -30.0), place_by(S[k], leg_ang[k], [(0.0, 3.0), (7.0, 3.0), (14.0, 3.0)],
                                                                                              [(0.0, -legh, 0.0), (7.0, -legh, 0.0), (7.0, -legh, -7.0)])))
        a = snap(view=view_side, rods=skewer, balls=clay)
        up = translate(0.0, -legh, 0.0)
        cur["body"] = (opened, mul(up, cur["body"][1]))
        for k in ("strip", "head", "drop"):
            cur[k] = (cur[k][0], mul(up, cur[k][1]))
        xa, ya = xa, ya - legh
        clay7 = (clay7[0], clay7[1] - legh, clay7[2])
        skewer = {"skewer": {"from": [xa, ya, (W + 20) / 2], "to": [xa, ya, -(W + 20) / 2]}}
        clay = {"clay": {"at": list(clay7)}}
        _, _, bworld = axle_of(opened, cur["body"][1])
        marks = [a_ for a_ in parts["body"].art if a_["kind"] == "mark" and a_.get("mark") == "leg"]
        for k, mk in zip(legs, marks):
            m = [_world_pt(bworld, S["body"], x, y) for x, y in mk["pts"]]
            src = [(0.0, 3.0), (7.0, 3.0), (14.0, 3.0)]
            for order in ((0, 1, 2), (1, 0, 3), (0, 3, 2), (3, 0, 1), (1, 2, 3), (2, 1, 0), (2, 3, 0), (3, 2, 1)):
                pl = place_by(S[k], leg_ang[k], src, [m[j] for j in order])
                local, _ = S[k].local(leg_ang[k])
                bottom = apply(mul(pl, local[S[k].panel_of(3.5, 3.0 + legh)]), (3.5, 3.0 + legh, 0.0))
                if bottom[1] > m[0][1] + legh - 0.5:
                    break
            cur[k] = (leg_ang[k], pl)
        steps.append([a, snap(view=view_side, rods=skewer, balls=clay, act="place", moving=sorted(legs + ["body", "strip", "head", "drop"]))])
    # 11. 上の面を閉じる
    ybot = -legh if legs else 0.0
    cur["body"] = (closed, body_place(closed, ybot))
    steps.append([snap(view={"rx": -30, "ry": 30}, rods=skewer, balls=clay)])
    # 12. 尾の糊代を折って、上の面の後ろの四角に貼る
    tail_ang = _all_lines(parts["tail"], 90)
    _, _, bworld = axle_of(closed, cur["body"][1])
    mk = next(a_ for a_ in parts["body"].art if a_["kind"] == "mark" and a_.get("mark") == "tail")
    xs, ys = [x for x, _ in mk["pts"]], [y for _, y in mk["pts"]]
    sq = {"f0": (min(xs), min(ys)), "f1": (min(xs), max(ys)), "b0": (max(xs), min(ys))}
    tl = pc.TAIL_LEN
    for f0, f1, b0_ in ((sq["f0"], sq["f1"], sq["b0"]), (sq["f1"], sq["f0"], (sq["b0"][0], max(ys)))):
        pl = place_by(S["tail"], tail_ang, [(0.0, tl), (pc.TAIL_W, tl), (0.0, tl + pc.TAIL_TAB)],
                      [_world_pt(bworld, S["body"], *f0), _world_pt(bworld, S["body"], *f1), _world_pt(bworld, S["body"], *b0_)])
        local, _ = S["tail"].local(tail_ang)
        tipw = apply(mul(pl, local[0]), (pc.TAIL_W / 2, 0.0, 0.0))
        if tipw[1] < _world_pt(bworld, S["body"], *f0)[1] - 10:
            break
    # 糊代を折った尾を、貼る四角の TAIL_HOLD 上に持ってから貼る。前は机の右に尾の先を下にして立てていて、尾が机の下へ 16mm 出た
    # （エンジンの 3D の検品 omochae.check3d の 3D.out で見つけた）
    cur["tail"] = (tail_ang, mul(translate(0.0, -TAIL_HOLD, 0.0), pl))
    a = snap(view={"rx": -30, "ry": 30}, rods=skewer, balls=clay)
    cur["tail"] = (tail_ang, pl)
    steps.append([a, snap(view={"rx": -25, "ry": 35}, rods=skewer, balls=clay, act="place", moving=["tail"])])
    # できあがりの動き: 頭が揺れて、静かな時の傾きで止まる（軸のまわりに回す。頭が上がる向きが正で、rot_z の正と同じ向き）。
    # 揺れは静かな時の傾きのまわりに ±MIN_SWING の中（当たりの検査が見る角の中）
    finale = []
    base = {k: cur[k] for k in ("strip", "head", "drop")}
    rest = math.degrees(sum(pc.swing_range(p)) / 2)
    for deg in (rest + pc.MIN_SWING, rest - 8.0, rest + 4.0, rest):
        swing = mul(translate(xa, ya, 0.0), mul(rot_z(deg), translate(-xa, -ya, 0.0)))
        for k, (ang, pl) in base.items():
            cur[k] = (ang, mul(swing, pl))
        cpos = apply(swing, tuple(clay7))
        finale.append(snap(view={"rx": -10, "ry": 20}, rods=skewer, balls={"clay": {"at": list(cpos)}}))
    # 検品だけの姿（JSON に出さない）: できあがりを、静かな時の傾きから ±MIN_SWING まで 0.5° ずつ回す。できあがりの動きの 4 つの姿の
    # 間も、玉・腕・頭が前の壁に当たらない事を 3D の形で見る（型紙の当たりの検査 fit_gaps と同じ角）
    sweep = []
    n_sw = int(round(2 * pc.MIN_SWING / 0.5))
    for i in range(n_sw + 1):
        deg = rest - pc.MIN_SWING + i * 0.5
        swing = mul(translate(xa, ya, 0.0), mul(rot_z(deg), translate(-xa, -ya, 0.0)))
        for k, (ang, pl) in base.items():
            cur[k] = (ang, mul(swing, pl))
        sweep.append((f"揺れ {deg - rest:+.1f}°", snap(view={"rx": -10, "ry": 20}, rods=skewer, balls={"clay": {"at": list(apply(swing, tuple(clay7)))}})))
    for k, v in base.items():
        cur[k] = v
    if len(steps) != len(steps_text):
        raise ValueError(f"段の数 {len(steps)} が手順の文の数 {len(steps_text)} と合わない")
    # 中身を分解して見せる（制作者の言葉「AI が 3D で表示して中身をそこで分解できる構造表示と、自分が作った実物がオーバーレイする。」）。
    # できあがりから、部品を入れた道の逆へ離す: 帯と頭は穴から前へ、腕と粘土は上へ、脚は下へ、尾は上へ、竹串は横へ
    away = {"strip": (-45.0, 0.0, 0.0), "head": (-45.0, 0.0, 0.0), "drop": (0.0, -35.0, 0.0), "tail": (0.0, -25.0, 0.0)}
    away.update({k: (0.0, 15.0, 0.0) for k in legs})
    exploded_states = {k: (ang, mul(translate(*away[k]), pl)) if k in away else (ang, pl) for k, (ang, pl) in cur.items()}
    sk = skewer["skewer"]
    exploded = scene.pose(exploded_states, view={"rx": -20, "ry": 35}, act="move", moving=sorted(away),
                          rods={"skewer": {"from": [sk["from"][0], sk["from"][1], sk["from"][2] + 35], "to": [sk["to"][0], sk["to"][1], sk["to"][2] + 35]}},
                          balls={"clay": {"at": [clay7[0], clay7[1] - 35, clay7[2]]}})
    # 内側を見る時に外す面: 胴の面のうち、見る人の方（+z）を向く面
    _, bw = scene.state("body", *cur["body"])
    glue_ids = {i for i, poly in enumerate(S["body"].panels) for gl in parts["body"].glue
                if __import__("shapely.geometry", fromlist=["Polygon"]).Polygon(gl).intersection(__import__("shapely.geometry", fromlist=["Polygon"]).Polygon(poly)).area > 0.99 * __import__("shapely.geometry", fromlist=["Polygon"]).Polygon(poly).area}
    front_side = max((i for i in range(len(bw)) if i not in glue_ids), key=lambda i: bw[i][2][2])
    structure = {"inside": {"strip": "body", "drop": "body", "clay": "body", "skewer": "body"}, "exploded": exploded,
                 "cutaway": {"body": [str(front_side)]}}
    rods = {"skewer": {"r": 1.0, "color": "#c8a46a", "kind": "rod", "owner": "body"}}
    balls = {"clay": {"r": round(pc.clay_r(p["weight_g"]), 3), "color": "#8a6f55"}}
    # 検品の決め（omochae.check3d）: 粘土の玉は 5 重りの腕に付く。机に置く形。刷った面は、胴と脚は外、両面の頭は両側
    faces = {"body": "out", **{k: "out" for k in legs}}
    if p["head_sides"] == 2:
        faces["head"] = "both"
    rules = {"attach": {"clay": "drop"}, "desk": True, "faces": faces, "extra": sweep}
    return steps_text, steps, finale, rods, balls, structure, rules


def _axis_angle(R):
    """回転の行列（3×3）の軸と角（ラジアン）。角が π の近くは、対称の部分（R + I）/ 2 = u uᵀ から軸を読む。"""
    c = max(-1.0, min(1.0, (R[0][0] + R[1][1] + R[2][2] - 1) / 2))
    th = math.acos(c)
    vee = (R[2][1] - R[1][2], R[0][2] - R[2][0], R[1][0] - R[0][1])
    sn = math.sin(th)
    if sn > 1e-6:
        return tuple(v / (2 * sn) for v in vee), th
    if th < 1e-6:
        return (0.0, 0.0, 1.0), 0.0
    B = [[(R[i][j] + (1.0 if i == j else 0.0)) / 2 for j in range(3)] for i in range(3)]
    i = max(range(3), key=lambda k: B[k][k])
    return tuple(B[i][j] / math.sqrt(B[i][i]) for j in range(3)), th


def _rot_axis(u, th):
    x, y, z = u
    c, sn = math.cos(th), math.sin(th)
    C = 1 - c
    return [[c + x * x * C, x * y * C - z * sn, x * z * C + y * sn], [y * x * C + z * sn, c + y * y * C, y * z * C - x * sn],
            [z * x * C - y * sn, z * y * C + x * sn, c + z * z * C]]


def _fan_open(scene, fan_key, stack, pivot, opening_deg, spread):
    """扇（蛇腹の帯）が、受けの所を要に開く途中の、面ごとの行列（custom）。

    紙の扇は、要の所で紙が縮んで開くので、折り線で分けた硬い面のつながり（tree と turns）では正しく表せない。そこで両方の端を合わせる:
    - spread 0 は、折りの形の畳んだ束（stack。面ごとの世界の行列）と同じ（谷と山で 1 枚ごとに裏返った束。畳んだ扇からつながる）。
    - spread 1 は、開いた半円。板 k（帯の y が k·w〜(k+1)·w、x が高さ）を、真ん中の線が要からの向き φ_k になるように立てる。
      φ_k は開く角（帯の長さ ÷ 高さ）を板の数で等分した所なので、上の端の弧の長さは板の幅と同じになり、隣の板の上の端の角が合う。
      刷った面は見る人の方。
    - 途中は、板ごとに、束の向きから開いた向きへ同じ軸のまわりに spread の割合だけ回し、上の端の真ん中を要のまわりの弧に沿って動かす。
      途中の形では、隣の板の折り線は合わない（見せるための近い形。サイトは custom の面を行列の間で補わない）。
    """
    q = scene.parts[fan_key]
    n = len(scene.sheets[fan_key].panels)
    w = (max(y for _, y in q.outline) - min(y for _, y in q.outline)) / n
    h = max(x for x, _ in q.outline) - min(x for x, _ in q.outline)
    out = {}
    for k in range(n):
        phi = -opening_deg / 2 + (k + 0.5) * opening_deg / n
        A = [[0.0, 1.0, 0.0, -(k * w + w / 2)], [-1.0, 0.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]]
        M1 = mul(translate(*pivot), mul(rot_z(phi), A))
        M0 = stack[k]
        R0 = [row[:3] for row in M0[:3]]
        R1 = [row[:3] for row in M1[:3]]
        Rrel = [[sum(R1[i][m] * R0[j][m] for m in range(3)) for j in range(3)] for i in range(3)]  # R1 · R0ᵀ
        u, th = _axis_angle(Rrel)
        Rs = _rot_axis(u, spread * th)
        Rs = [[sum(Rs[i][m] * R0[m][j] for m in range(3)) for j in range(3)] for i in range(3)]
        top = (h, k * w + w / 2, 0.0)  # 板の上の端の真ん中（部品の座標）
        p0 = apply(M0, top)
        rz = rot_z(spread * phi)
        rel = _sub(p0, pivot)
        ps = tuple(pivot[i] + sum(rz[i][j] * rel[j] for j in range(3)) for i in range(3))
        t = _sub(ps, tuple(sum(Rs[i][j] * top[j] for j in range(3)) for i in range(3)))
        out[str(k)] = css([Rs[0] + [t[0]], Rs[1] + [t[1]], Rs[2] + [t[2]], [0.0, 0.0, 0.0, 1.0]])
    return out


def _goraigo_rise(scene, p):
    """御来迎（内筒を下から押し上げる形 rise）の段ごとの形。手順の文（slider_fan.steps）と 1 対 1。

    判断の芯:
    - 外筒は色の境で山折りして角筒にし（刷った面が外）、内筒は谷折りで角筒にする（刷った面が内。割り箸を貼る長方形は 1 面目の内）。
    - 内筒・台・受け・扇・像・割り箸は 1 つの組にし、台の上の面の真ん中を組の原点にする。組は外筒の脇で組み、下から外筒に入れて、
      静かな時の高さ（台の上の面が外筒の底から 筒の高さ − 押し上げる量 − 内筒の長さ ＋ 内筒の長さ）と、押し上げた高さ（口の高さ）に置く。
      高さは omochae.fold3d.check_rise と同じ式。
    - 受けは台の印（台の奥の半分）に、像は台の前の半分に立てる。扇は受けの U の中に畳んで立て、口から出たら要（扇の下の端の真ん中）の
      まわりに開く（custom）。開く角は雛形の開く角の見込み（帯の長さ ÷ 高さ）。
    - 割り箸は、内筒の 1 面目の内の点の線の長方形の真ん中に沿わせ、上の端を長方形の上の端にそろえ、長さ CHOPSTICK_LEN で下へ出す。
    """
    from .templates import slider_fan as sf
    if p["push_part"] != sf.RISE:
        return None
    parts, S = scene.parts, scene.sheets
    A, Ht, a, Lp, s_up = p["tube_side"], p["tube_height"], p["pusher_side"], p["pusher_height"], p["push_amount"]
    b = p["base_side"]
    g = p["base_glue"]
    fw, fh = p["figure_w"], p["figure_h"]
    n_fold, fold_w, fold_h = int(p["fold_count"]), p["fold_width"], p["fold_height"]
    opening = sf.opening_bound_deg(n_fold, fold_w, fold_h)
    # 角
    tube_closed = _all_lines(parts["tube"], 90)
    tube_crease = _all_lines(parts["tube"], 60)
    inner_closed = _all_lines(parts["pusher"], 90)
    base_folded = _all_lines(parts["base"], 90)
    cradle_u = _all_lines(parts["cradle"], 90)
    fan_stack = _all_lines(parts["fan"], 180)
    fig_folded = _all_lines(parts["figure"], 180)
    # 組の中の置き場（組の原点 = 台の上の面の真ん中。x 右・y 下・z 見る人の方）
    def inner_rel(angles):
        return place_by(S["pusher"], angles, [(0.0, 0.0), (a, 0.0), (0.0, Lp)], [(-a / 2, 0.0, -a / 2), (a / 2, 0.0, -a / 2), (-a / 2, Lp, -a / 2)])
    base_rel = lambda angles: place_by(S["base"], angles, [(g, g), (g + b, g), (g, g + b)], [(-b / 2, 0.0, -b / 2), (b / 2, 0.0, -b / 2), (-b / 2, 0.0, b / 2)])
    # 受けの底の面は台の印（台の座標の線の外接の四角）に合わせる
    mark = [pt for it in parts["base"].art if it["kind"] == "line" for pt in it["pts"]]
    mx0, mx1 = min(x for x, _ in mark), max(x for x, _ in mark)
    my0, my1 = min(y for _, y in mark), max(y for _, y in mark)
    to_group = lambda x, y: (x - g - b / 2, 0.0, y - g - b / 2)
    cq = parts["cradle"]
    c_y0 = min(r["hinge"][0][1] for r in S["cradle"].rows.values())
    c_y1 = max(r["hinge"][0][1] for r in S["cradle"].rows.values())
    c_w = max(x for x, _ in cq.outline)
    cradle_rel = lambda angles: place_by(S["cradle"], angles, [(0.0, c_y0), (c_w, c_y0), (0.0, c_y1)], [to_group(mx0, my0), to_group(mx1, my0), to_group(mx0, my1)])
    zc = (to_group(0, my0)[2] + to_group(0, my1)[2]) / 2  # 受けの U の真ん中（扇の束の z）
    fan_rel = lambda angles: place_by(S["fan"], angles, [(0.0, 0.0), (0.0, fold_w), (10.0, 0.0)], [(-fold_w / 2, 0.0, zc), (fold_w / 2, 0.0, zc), (-fold_w / 2, -10.0, zc)])
    fy = max(y for _, y in parts["figure"].outline)
    zf = b / 4  # 台の前の半分の真ん中
    fig_rel = lambda angles: place_by(S["figure"], angles, [(fw / 2, fy), (fw / 2 + 10, fy), (fw / 2, fy - 10)], [(0.0, 0.0, zf), (10.0, 0.0, zf), (0.0, -10.0, zf)])
    stick = next(it for it in parts["pusher"].art if it["kind"] == "mark" and it.get("mark") == "stick")
    sx = (min(x for x, _ in stick["pts"]) + max(x for x, _ in stick["pts"])) / 2
    sy = min(y for _, y in stick["pts"])
    stick_top = (sx - a / 2, sy, -a / 2 + sf.CHOPSTICK_W / 2)  # 1 面目（奥）の内に沿う
    # 外筒の置き場: 作る所（机の上に立てる）と、手に持つ所
    def tube_at(angles, x0, ybottom):
        return place_by(S["tube"], angles, [(0.0, 0.0), (A, 0.0), (0.0, Ht)], [(x0 - A / 2, ybottom - Ht, A / 2), (x0 + A / 2, ybottom - Ht, A / 2), (x0 - A / 2, ybottom, A / 2)])
    work_x, y_bottom = -60.0, -150.0
    rest_top = y_bottom - (Ht - s_up - Lp + Lp)  # 台の上の面（静かな時）
    open_top = rest_top - s_up
    G_build = translate(60.0, -Lp, 0.0)  # 内筒を机に立てた所
    group_keys = ["pusher", "base", "cradle", "fan", "figure"]

    def lie(key, x, z, lift=0.0):
        """部品を机の上に、刷った面を上にして寝かせる（作る所）。"""
        q = parts[key]
        bx0, by0 = min(x_ for x_, _ in q.outline), min(y_ for _, y_ in q.outline)
        return place_by(S[key], {}, [(bx0, by0), (bx0 + 10, by0), (bx0, by0 + 10)], [(x, -lift, z), (x + 10, -lift, z), (x, -lift, z + 10)])

    cur = {k: ({}, scene.on_paper(k)) for k in parts}
    steps_text = sf.steps(p)
    steps = []
    snap = lambda **kw: scene.pose(dict(cur), **kw)
    rods = {}

    def chop(G):
        top = apply(G, stick_top)
        return {"chopstick": {"from": list(top), "to": list(apply(G, (stick_top[0], stick_top[1] + sf.CHOPSTICK_LEN, stick_top[2])))}}
    # 1・2. 物差し・切る
    steps.append([snap(on_paper=True, view={"rx": -70, "ry": 0}, tool={"kind": "ruler"}, act="place", moving=[])])
    steps.append([snap(on_paper=True, view={"rx": -70, "ry": 0}, tool={"kind": "scissors"}), snap(view={"rx": -70, "ry": 0}, act="cut", moving=sorted(parts))])
    # 3・4. 外筒を山折りして角筒に（作る所に立てる）
    cur["tube"] = ({}, tube_at({}, work_x, 0.0))
    a3 = snap(view={"rx": -15, "ry": 30, "focus": ["tube"]})
    cur["tube"] = (tube_crease, tube_at(tube_crease, work_x, 0.0))
    steps.append([a3, snap(view={"rx": -15, "ry": 30, "focus": ["tube"]})])
    cur["tube"] = (tube_closed, tube_at(tube_closed, work_x, 0.0))
    steps.append([snap(view={"rx": -15, "ry": 30, "focus": ["tube"]})])
    # 5. 内筒を谷折りして戻す（作る所に立てる）
    cur["pusher"] = (inner_closed, mul(G_build, inner_rel(inner_closed)))
    a5 = snap(view={"rx": -15, "ry": 30, "focus": ["pusher"]})
    cur["pusher"] = ({}, mul(G_build, inner_rel({})))
    steps.append([a5, snap(view={"rx": -15, "ry": 30, "focus": ["pusher"]})])
    # 6. 割り箸を内筒の点の線の長方形に沿わせて留める（平らな内筒の上）
    rods = chop(G_build)
    steps.append([snap(view={"rx": -15, "ry": 30, "focus": ["pusher"]}, rods=rods, act="place", moving=["chopstick"])])
    # 7. 内筒を角筒に（割り箸は内）
    cur["pusher"] = (inner_closed, mul(G_build, inner_rel(inner_closed)))
    steps.append([snap(view={"rx": -15, "ry": 30, "focus": ["pusher"]}, rods=rods)])
    # 8. 台の糊代を下へ山折り（机の少し上で）
    cur["base"] = ({}, lie("base", 110.0, 0.0, lift=10.0))
    a8 = snap(view={"rx": -40, "ry": 20, "focus": ["base"]}, rods=rods)
    cur["base"] = (base_folded, mul(translate(0.0, 0.0, 0.0), place_by(S["base"], base_folded, [(g, g), (g + b, g), (g, g + b)],
                                                                         [(110.0, -10.0, 0.0), (110.0 + b, -10.0, 0.0), (110.0, -10.0, b)])))
    steps.append([a8, snap(view={"rx": -40, "ry": 20, "focus": ["base"]}, rods=rods)])
    # 9. 台を内筒の上の口に差し込む
    cur["base"] = (base_folded, mul(G_build, base_rel(base_folded)))
    steps.append([snap(view={"rx": -30, "ry": 30, "focus": ["pusher", "base"]}, rods=rods, act="place", moving=["base"])])
    # 10. 扇を蛇腹に畳む（机の上）
    cur["fan"] = ({}, lie("fan", -40.0, 40.0, lift=1.0))
    a10 = snap(view={"rx": -60, "ry": 10, "focus": ["fan"]}, rods=rods)
    cur["fan"] = (fan_stack, place_by(S["fan"], fan_stack, [(0.0, 0.0), (0.0, fold_w), (10.0, 0.0)], [(-40.0, -1.0, 40.0), (-40.0, -1.0, 40.0 + fold_w), (-30.0, -1.0, 40.0)]))
    steps.append([a10, snap(view={"rx": -60, "ry": 10, "focus": ["fan"]}, rods=rods)])
    # 11. 受けを U の字に（机の上）
    cur["cradle"] = ({}, lie("cradle", 100.0, 40.0, lift=0.5))
    a11 = snap(view={"rx": -40, "ry": 20, "focus": ["cradle"]}, rods=rods)
    cur["cradle"] = (cradle_u, place_by(S["cradle"], cradle_u, [(0.0, c_y0), (c_w, c_y0), (0.0, c_y1)], [(100.0, -0.5, 40.0), (100.0 + c_w, -0.5, 40.0), (100.0, -0.5, 40.0 + (c_y1 - c_y0))]))
    steps.append([a11, snap(view={"rx": -40, "ry": 20, "focus": ["cradle"]}, rods=rods)])
    # 12. 受けを台の印に貼る
    cur["cradle"] = (cradle_u, mul(G_build, cradle_rel(cradle_u)))
    steps.append([snap(view={"rx": -35, "ry": 30, "focus": ["base", "cradle"]}, rods=rods, act="place", moving=["cradle"])])
    # 13. 畳んだ扇を受けに立てて貼る
    cur["fan"] = (fan_stack, mul(G_build, fan_rel(fan_stack)))
    steps.append([snap(view={"rx": -20, "ry": 30, "focus": ["base", "cradle", "fan"]}, rods=rods, act="place", moving=["fan"])])
    # 14. 像を山折りで裏どうし（机の上）
    cur["figure"] = ({}, lie("figure", -20.0, 80.0, lift=2.0))
    a14 = snap(view={"rx": -50, "ry": 10, "focus": ["figure"]}, rods=rods)
    fx0 = min(x for x, _ in parts["figure"].outline)
    cur["figure"] = (fig_folded, place_by(S["figure"], fig_folded, [(fw / 2, fy), (fw / 2 + 10, fy), (fw / 2, fy - 10)],
                                          [(-20.0 + fw / 2 - fx0, -2.0, 80.0 + fy), (-10.0 + fw / 2 - fx0, -2.0, 80.0 + fy), (-20.0 + fw / 2 - fx0, -2.0, 80.0 + fy - 10)]))
    steps.append([a14, snap(view={"rx": -50, "ry": 10, "focus": ["figure"]}, rods=rods)])
    # 15. 像を台の受けの前に立てて貼る
    cur["figure"] = (fig_folded, mul(G_build, fig_rel(fig_folded)))
    steps.append([snap(view={"rx": -15, "ry": 30, "focus": ["base", "cradle", "fan", "figure"]}, rods=rods, act="place", moving=["figure"])])

    def group_at(G):
        for k, rel in (("pusher", inner_rel(inner_closed)), ("base", base_rel(base_folded)), ("cradle", cradle_rel(cradle_u)),
                       ("fan", fan_rel(fan_stack)), ("figure", fig_rel(fig_folded))):
            cur[k] = (cur[k][0], mul(G, rel))
        return chop(G)
    # 16. 外筒を手に持つ所へ、組を外筒の下から入れる
    cur["tube"] = (tube_closed, tube_at(tube_closed, 0.0, y_bottom))
    G_below = translate(0.0, y_bottom + fold_h + 20.0, 0.0)
    r16a = group_at(G_below)
    a16 = snap(view={"rx": -10, "ry": 25}, rods=r16a)
    G_rest = translate(0.0, rest_top, 0.0)
    r16 = group_at(G_rest)
    steps.append([a16, snap(view={"rx": -10, "ry": 25}, rods=r16, act="thread", moving=sorted(group_keys + ["chopstick"]))])
    # 17. 押し上げると扇が口から出て開く（開く所は custom）
    G_open = translate(0.0, open_top, 0.0)
    pivot = apply(G_open, (0.0, 0.0, zc))
    r17 = group_at(G_open)
    rise = snap(view={"rx": -10, "ry": 25}, rods=r17)
    stack = scene.state("fan", *cur["fan"])[1]  # 押し上げた所の、畳んだ束の面ごとの世界の行列（開く所はここから始まる）
    opening_poses = []
    for i in range(1, 11):
        pose_ = snap(view={"rx": -5, "ry": 15}, rods=r17, custom=("fan",))
        pose_["parts"]["fan"]["panels"] = _fan_open(scene, "fan", stack, pivot, opening, i / 10)
        opening_poses.append(pose_)
    steps.append([rise] + opening_poses)
    # 18. 引き下げると畳まれて筒に入る
    closing = []
    for i in range(9, -1, -1):
        pose_ = snap(view={"rx": -5, "ry": 15}, rods=r17, custom=("fan",))
        pose_["parts"]["fan"]["panels"] = _fan_open(scene, "fan", stack, pivot, opening, i / 10)
        closing.append(pose_)
    r18 = group_at(G_rest)
    steps.append(closing + [snap(view={"rx": -10, "ry": 25}, rods=r18)])
    # できあがりの動き: 押し上げて扇が開く
    finale = [rise] + opening_poses
    if len(steps) != len(steps_text):
        raise ValueError(f"段の数 {len(steps)} が手順の文の数 {len(steps_text)} と合わない")
    # 中身を分解して見せる: 静かな時の形から、組を外筒の下へ抜き、組の中は入れた道の逆へ離す（台は内筒の上へ、受けと扇は台の上へ、
    # 像は前へ）。割り箸は内筒と一緒
    group_at(G_rest)
    down = 150.0
    away = {"pusher": (0.0, down, 0.0), "base": (0.0, down - 30.0, 0.0), "cradle": (0.0, down - 50.0, 0.0), "fan": (0.0, down - 70.0, 0.0),
            "figure": (0.0, down - 40.0, 30.0)}
    exploded_states = {k: (ang, mul(translate(*away[k]), pl)) if k in away else (ang, pl) for k, (ang, pl) in cur.items()}
    exploded = scene.pose(exploded_states, view={"rx": -15, "ry": 30}, act="move", moving=sorted(away),
                          rods=chop(mul(translate(0.0, down, 0.0), G_rest)))
    # 内側を見る時に外す面: 外筒と内筒の、見る人の方（z が一番大きい所）にある面
    def front_face(key):
        _, wm = scene.state(key, *cur[key])
        from shapely.geometry import Polygon
        def zc(i):
            c = Polygon(S[key].panels[i]).centroid
            return apply(wm[i], (c.x, c.y, 0.0))[2]
        body = [i for i in range(len(wm)) if not any(Polygon(gl).intersection(Polygon(S[key].panels[i])).area > 0.99 * Polygon(S[key].panels[i]).area for gl in parts[key].glue)]
        return str(max(body, key=zc))
    structure = {"inside": {"pusher": "tube", "base": "pusher", "cradle": "tube", "fan": "tube", "figure": "tube", "chopstick": "pusher"},
                 "exploded": exploded, "cutaway": {"tube": [front_face("tube")], "pusher": [front_face("pusher")]}}
    rod_kinds = {"chopstick": {"r": sf.CHOPSTICK_W / 2, "color": "#d9c49a", "kind": "rod", "owner": "pusher"}}
    # 検品の決め（omochae.check3d）: 静かな時（手順 16 の終わり）に扇と像は外筒の口の 2mm 以上下（隠れる）。刷った面は、外筒は外、
    # 内筒は内（破線を刷る隠れる部品で、色の面を内にする）、台は外（上の面が上・横の面が外）。手に持つ玩具なので机は見ない
    rules = {"below": {"parts": ["fan", "figure"], "of": "tube", "clear": 2.0, "pose": (16, -1)},
             "faces": {"tube": "out", "pusher": "in", "base": "out"}, "desk": False}
    return steps_text, steps, finale, rod_kinds, {}, structure, rules


def _slider_fan(scene, p):
    from .templates import slider_fan as sf
    return _goraigo_rise(scene, p) if p["push_part"] == sf.RISE else None


RECIPES = {"pivot_counterweight": _tiger, "slider_fan": _slider_fan}


def build(scenario_path, commit=None):
    """場面の JSON（examples/ の形）から、作り方の 3D の JSON を作る。Returns dict。組み立ての書き方が無い雛形は None。"""
    return assemble(scenario_path, commit)[0]


def assemble(scenario_path, commit=None):
    """build と同じ dict と、レシピの検品の決め（omochae.check3d.inspect の rules）。組み立ての書き方が無い雛形は (None, None)。
    検品は入口（main）だけで回す。build は今までどおり形だけを返す（試験や読む側が、検品の落ちる形も作れるように）。"""
    from .__main__ import load_source
    from .compose import compose
    path = pathlib.Path(scenario_path)
    sc = json.loads(path.read_text(encoding="utf-8"))
    tid = sc["template"]
    if tid not in RECIPES:
        return None, None
    tpl = TEMPLATES[tid]
    p = {**tpl.DEFAULTS, **sc["params"]}
    _, layout, fails = compose(tid, p, load_source(sc["source_id"]))
    if fails:
        raise ValueError("型紙の検査に落ちる寸法では 3D を作らない: " + "; ".join(f.line() for f in fails))
    scene = Scene(layout)
    made = RECIPES[tid](scene, p)
    if made is None:
        return None, None
    texts, steps, finale, rods, balls, structure, rules = made
    toy = path.stem.replace("_", "-")
    return {
        "format": FORMAT, "toy": toy, "template": tid, "source_id": sc["source_id"], "params": sc["params"],
        "paper": {"w": scene.page.w, "h": scene.page.h, "place": scene.paper_place(),
                  "at": {q.key: [round(q.x, 4), round(q.y, 4)] for q in layout["parts"]}},
        "parts": scene.part_list(),
        "steps": [{"n": i + 1, "text": t, "poses": poses} for i, (t, poses) in enumerate(zip(texts, steps))],
        "finale": {"poses": finale},
        "structure": structure,
        "rods": rods, "balls": balls,
        "engine": {"commit": commit, "command": f"python -m omochae.assembly3d --scenario {path.as_posix()}"},
    }, rules


def _ours(path):
    """この入口が書いた形の JSON か（format が FORMAT）。読めない・JSON でない・形が違う物は False。"""
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("format") == FORMAT
    except (OSError, UnicodeDecodeError, ValueError, AttributeError):
        return False


def main(argv=None):
    from .__main__ import Parser  # 呼び方の誤りは 4（ほかの入口と同じ。README の命令の試験が見る）
    ap = Parser(prog="python -m omochae.assembly3d", description="作り方の 3D を、手順と 1 対 1 の段ごとの形にして JSON で出す")
    ap.add_argument("--scenario", required=True, help="場面の JSON（examples/tora_v6.json など）")
    ap.add_argument("--out", help="書き出す JSON（無ければ標準出力）")
    ap.add_argument("--commit", help="出所に書く commit（無ければ git の HEAD）")
    ap.add_argument("--record", help="検品の記録（段ごとの絵の一覧 PNG・短い動画 GIF・文 TXT）を書く所。落ちても書く")
    args = ap.parse_args(argv)
    commit = args.commit
    if commit is None:
        import subprocess
        r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True)
        commit = r.stdout.strip() or None
    try:
        data, rules = assemble(args.scenario, commit)
    except (FoldError, ValueError) as e:
        print(f"作れない: {e}", file=sys.stderr)
        return 3
    if data is None:
        print("この雛形の組み立ての書き方はまだ無い", file=sys.stderr)
        return 4
    # エンジンが自分で組んだ形を検品する（制作者の言葉「エンジンは3D組み立て検品を自分でする」）。落ちたら JSON を書かない
    # （サイトが当たる形を描かないため）。終わりの値は、型紙の検査に落ちた時と同じ 3。所見（NOTE）は落ちにしない
    from .check3d import inspect, render, summary
    hits = inspect(data, rules)
    for line in summary(hits):
        print(line, file=sys.stderr)
    if args.record:
        for path in render(data, hits, pathlib.Path(args.record) / f"{data['toy']}-check"):
            print(path, file=sys.stderr)
    if any(not h.note for h in hits):
        print("3D の組み立て検品に落ちた。JSON は書かない", file=sys.stderr)
        if args.out and pathlib.Path(args.out).exists():
            # 前に書いた JSON を残すと、落ちた後も古い形が読まれる（見直しの指摘）。同じ置き場の前の JSON は消す。
            # 消すのは、この入口が書く形の JSON（format が FORMAT）の時だけ。--out を別のファイルに向けた時に、そのファイルを
            # 消さないため（セキュリティの点検 2026-11-07）
            if _ours(pathlib.Path(args.out)):
                pathlib.Path(args.out).unlink()
                print(f"前の JSON を消した（古い形を読ませない）: {args.out}", file=sys.stderr)
            else:
                print(f"--out の所の物は作り方の 3D の JSON でないので、消さない: {args.out}", file=sys.stderr)
        return 3
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    if args.out:
        pathlib.Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(args.out).write_text(text, encoding="utf-8")
        print(args.out)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
