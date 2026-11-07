"""作り方の 3D の組み立てを、エンジンが自分で検品する（制作者の言葉 2026-11-07「エンジンは3D組み立て検品を自分でする（エンジンの性質として）」
「組み立ての様子も作る」）。決める側の決定（同日）で、入口は 3D の JSON を出す道（python -m omochae.assembly3d）だけ。型紙の道へはつながない。

omochae.assembly3d.build が作る段ごとの形（JSON と同じ物）を読み、次を床として見る:
- 3D.hit（当たり）: 部品の紙の面が、ほかの面を刺さない。粘土の玉が紙に食い込まない。棒（竹串・割り箸）は穴の所でだけ紙を通る。
- 3D.out（はみ出し）: レシピが言う「静かな時に口の下に隠れる部品」が口から出ない。机に置く形（虎）は、どの部品も机の下へ出ない。
- 3D.face（色の面の向き）: 組み終わりの形で、レシピが言う部品の刷った面が、外・内・上の決めた向き（fold3d の 3D.face と同じ床の名。
  fold3d は御来迎のつまみの形の外筒を、ここは作り方の 3D の組を見る）。

判断の芯（どれも、作り方の 3D で決めて置いた形のどこが「当たり」かの決め）:
- 紙は折り線で分けた硬い面（fold3d と同じ）。厚み・糊・たわみは入れない。見るのは JSON に出す姿と、レシピが足す検品だけの姿で、
  姿と姿の間（サイトが補う動きの途中）は見ない。
- 面と面は「辺が相手の面を刺す」で見る。辺の両端が相手の面の平らな所の両側へ EPS 超離れ、刺す点が相手の面の中（外形の縁と穴から EPS 超内）
  なら当たり。辺が面に乗るだけ（折り線・糊代の縁・T の字に突き当たる所）は、両側に出ないので当たりにしない。折り線でつながる隣の面も
  この決まりで刺さないので、別に外さない（折りすぎて相手を突き抜けた面は当たりになる。虎 v7・御来迎 v14・虎 v6 で外す時と同じ結果を確かめた）。
- ほぼ平ら（PARALLEL_DEG 未満）の 2 面は、貼る・重ねる・筒の中に入れる所（糊代と相手の面、両面の頭、内筒と外筒の壁）と見て、
  刺す深さの決まりを EPS_PAR にする（糊代は相手の面から 0.6mm 内に寝る。見直しの指摘: 前は一律に外していて、関わりの無い部品が
  浅い角で深く刺さっても見なかった）。
- 見ない組（理由つき）:
  - 隠した部品（hidden）と、中身の分解の形（structure。わざと離した形）。
  - レシピが言う「動きを見せるための近い形」（custom。御来迎の扇の開く途中）の板どうし: 隣の折り線が合わない近い形で、
    板どうしの交わりは本当の形でない（#136 の限り）。扇とほかの部品の交わりは、落ちにせず所見（NOTE）として記録に残す
    （硬い板の近い形では、要の所で紙が縮む形を表せず、台・受けに刺さって見える。扇が口の縁に当たらない事は、型紙の F5.fan_clearance と
    fold3d の 3D.fan が見る）。
- 玉は球。レシピが言う付く部品（虎の粘土は 5 重りの腕）の面は見ない（玉は腕の穴に付く）。
- 棒は太さの無い線分で見る（穴の縁から棒の半径の分は見ない）。穴は部品の holes・round_cuts と面の inner。
"""
import math

EPS = 0.1  # 刺すと見る深さ mm（行列は 5 桁に丸めるので、点は 0.01mm まで合う。紙の厚み 0.15mm より小さく取る）
PARALLEL_DEG = 10.0  # これより平らな 2 面は、貼る・重ねる所と見る
EPS_PAR = 1.0  # ほぼ平らな 2 面で刺すと見る深さ mm（糊代が相手の面から寝る 0.6mm の外）
DESK_TOL = 0.5  # 机の下へ出たと見る深さ mm


class Hit:
    """検品の落ち 1 つ。floor・所（where）・文と、絵に赤で描く物（面・点・玉）。"""

    def __init__(self, floor, where, msg, pose_label, panels=(), points=(), balls=(), note=False, depth=0.0, rods=()):
        self.floor, self.where, self.msg, self.pose_label, self.depth = floor, where, msg, pose_label, depth
        self.panels, self.points, self.balls, self.rods = list(panels), list(points), list(balls), list(rods)
        self.note = note  # 所見（落ちにしない。近い形の部品の当たり）
        self.pose = None  # 当たった姿（記録の絵に使う）

    def line(self):
        return f"{'NOTE' if self.note else 'FAIL'} {self.floor} [{self.where}] {self.pose_label}: {self.msg}"


def M(c):
    """列優先の 16 個 → 行の並びの 4×4。"""
    return [[c[col * 4 + row] for col in range(4)] for row in range(4)]


def ap(m, p):
    x, y = p[0], p[1]
    return (m[0][0] * x + m[0][1] * y + m[0][3], m[1][0] * x + m[1][1] * y + m[1][3], m[2][0] * x + m[2][1] * y + m[2][3])


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _inside(poly, q):
    """点 q（2D）が多角形の中か（偶奇）。"""
    x, y = q
    n, c = len(poly), False
    for i in range(n):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < x1 + (x2 - x1) * (y - y1) / (y2 - y1):
            c = not c
    return c


def _edge_dist(poly, q):
    """点 q（2D）から多角形の縁までの長さ。"""
    best = math.inf
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % len(poly)]
        dx, dy = x2 - x1, y2 - y1
        L2 = dx * dx + dy * dy
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((q[0] - x1) * dx + (q[1] - y1) * dy) / L2))
        best = min(best, math.hypot(q[0] - x1 - t * dx, q[1] - y1 - t * dy))
    return best


class Panel:
    """1 つの姿の、部品の 1 面（世界の形）。面の座標（部品の座標の 2D）との行き来は、面の行列 m（z = 0 の面を世界へ）で。"""

    def __init__(self, key, name, pid, poly, inner, holes, m):
        self.key, self.name, self.pid, self.m = key, name, pid, m
        self.poly, self.inner, self.holes = poly, inner, holes  # 部品の座標の 2D（holes は (x, y, r) で、この面に入る物だけ）
        self.pts = [ap(m, q) for q in poly]
        self.o = ap(m, (0.0, 0.0))
        self.u = _sub(ap(m, (1.0, 0.0)), self.o)
        self.v = _sub(ap(m, (0.0, 1.0)), self.o)
        self.n = (m[0][2], m[1][2], m[2][2])  # 刷った面の向き（面の z）
        xs, ys, zs = zip(*self.pts)
        self.lo, self.hi = (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))

    def dist(self, p):
        """点 p の、面の平らな所からの向きの付いた距離（刷った面の側が正）。"""
        return _dot(_sub(p, self.o), self.n)

    def local(self, p):
        """世界の点 p を面の座標（2D）へ。面の平らな所へ落とした所。"""
        d = _sub(p, self.o)
        return (_dot(d, self.u), _dot(d, self.v))

    def solid_depth(self, q):
        """面の座標の点 q が、紙のある所（外形の中で、穴の外）にどれだけ深く入るか mm。紙の外は負。"""
        if not _inside(self.poly, q):
            return -_edge_dist(self.poly, q)
        depth = _edge_dist(self.poly, q)
        for ring in self.inner:
            if _inside(ring, q):
                return -_edge_dist(ring, q)
            depth = min(depth, _edge_dist(ring, q))
        for hx, hy, hr in self.holes:
            dd = math.hypot(q[0] - hx, q[1] - hy) - hr
            if dd < 0:
                return dd
            depth = min(depth, dd)
        return depth

    def edges(self):
        rings = [self.poly] + list(self.inner)
        for ring in rings:
            w = [ap(self.m, q) for q in ring]
            for i in range(len(w)):
                yield w[i], w[(i + 1) % len(w)]


def panels_of(data, pose):
    """姿 1 つの、見える部品の面（Panel）の並び。部品の holes・round_cuts は、その点を含む面に入れる。"""
    out = []
    for part in data["parts"]:
        key = part["key"]
        st = pose["parts"].get(key)
        if st is None or key in pose.get("hidden", ()):
            continue
        holes = [tuple(h) for h in part.get("holes", [])] + [tuple(c) for c in part.get("round_cuts", [])]
        for pn in part["panels"]:
            poly = [tuple(q) for q in pn["poly"]]
            mine = [h for h in holes if _inside(poly, h[:2])]
            out.append(Panel(key, part["name"], pn["id"], poly, [[tuple(q) for q in r] for r in pn.get("inner", [])], mine,
                             M(st["panels"][str(pn["id"])])))
    return out


def _near(a, b, pad):
    return all(a.lo[k] - pad <= b.hi[k] and b.lo[k] - pad <= a.hi[k] for k in range(3))


def _pierce(a, b, eps=EPS):
    """面 a の辺が面 b を刺す所（世界の点）と深さ（辺が b の両側へ出る短い方）。両側へ eps 超出る辺だけを見る。無ければ None。"""
    best = None
    for p, q in a.edges():
        dp, dq = b.dist(p), b.dist(q)
        if not ((dp > eps and dq < -eps) or (dp < -eps and dq > eps)):
            continue
        t = dp / (dp - dq)
        x = (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t, p[2] + (q[2] - p[2]) * t)
        depth = b.solid_depth(b.local(x))
        if depth > EPS:
            reach = min(abs(dp), abs(dq))
            if best is None or reach > best[1]:
                best = (x, reach)
    return best


def _deepest(a, b, eps):
    """a の辺が b を刺す所と、b の辺が a を刺す所のうち、深い方（見直しの指摘: 前は先に見つけた向きだけで、深さを小さく言う事があった）。"""
    got = [g for g in (_pierce(a, b, eps), _pierce(b, a, eps)) if g is not None]
    return max(got, key=lambda g: g[1]) if got else None


def check_pose(data, pose, label, rules):
    """姿 1 つの 3D.hit と 3D.out。rules はレシピの決め（attach・desk）。"""
    pans = panels_of(data, pose)
    hits, seen = [], set()
    custom = {k for k, st in pose["parts"].items() if st.get("custom")}
    cos_par = math.cos(math.radians(PARALLEL_DEG))
    for i, a in enumerate(pans):
        for b in pans[i + 1:]:
            if a.key == b.key and a.key in custom:
                continue  # 動きを見せる近い形（扇の開く途中）の板どうし
            if not _near(a, b, EPS):
                continue
            eps = EPS_PAR if abs(_dot(a.n, b.n)) > cos_par else EPS
            got = _deepest(a, b, eps)
            if got is None:
                continue
            where = "と".join(sorted((a.key, b.key))) if a.key != b.key else a.key
            if where in seen:
                # 同じ部品の組の 2 つ目からの交わりは、前の落ちに面と点を足す（記録の絵で全部を赤にする。見直しの指摘: 同じ部品の中の
                # 交わりは名の作り方が違い、足せていなかった）
                for h in hits:
                    if h.floor == "3D.hit" and h.where == where:
                        h.panels += [(a.key, a.pid), (b.key, b.pid)]
                        h.points.append(got[0])
                        if got[1] > h.depth:
                            h.depth, h.msg = got[1], f"{h.msg.split('の紙が交わる')[0]}の紙が交わる（深さ {got[1]:.1f}mm）"
                continue
            seen.add(where)
            what = a.name if a.key == b.key else f"{a.name}と{b.name}"
            hits.append(Hit("3D.hit", where, f"{what}の紙が交わる（深さ {got[1]:.1f}mm）", label,
                            panels=[(a.key, a.pid), (b.key, b.pid)], points=[got[0]], note=bool(custom & {a.key, b.key}), depth=got[1]))
    radius = {k: v["r"] for k, v in data.get("balls", {}).items()}
    for name, ball in pose.get("balls", {}).items():
        c, r = tuple(ball["at"]), radius.get(name, 0.0)
        own = rules.get("attach", {}).get(name)
        for pn in pans:
            if pn.key == own or not _near(pn, type("B", (), {"lo": tuple(x - r for x in c), "hi": tuple(x + r for x in c)})(), 0.0):
                continue
            q = pn.local(c)
            d = abs(pn.dist(c))
            depth = pn.solid_depth(q)
            gap = d if depth >= 0 else math.hypot(d, depth)
            if gap < r - EPS:
                hits.append(Hit("3D.hit", f"{name}と{pn.key}", f"玉（半径 {r:.1f}mm）が{pn.name}の紙に {r - gap:.1f}mm 食い込む", label,
                                panels=[(pn.key, pn.pid)], balls=[name], note=pn.key in custom, depth=r - gap))
                break
    for name, rod in pose.get("rods", {}).items():
        p0, p1 = tuple(rod["from"]), tuple(rod["to"])
        mine = {}  # 部品ごとの落ち（同じ姿で同じ部品の面をいくつ通っても 1 つ。見直しの指摘: 姿の数を多く数えた）
        for pn in pans:
            d0, d1 = pn.dist(p0), pn.dist(p1)
            if not ((d0 > EPS and d1 < -EPS) or (d0 < -EPS and d1 > EPS)):
                continue
            t = d0 / (d0 - d1)
            x = tuple(p0[k] + (p1[k] - p0[k]) * t for k in range(3))
            depth = pn.solid_depth(pn.local(x))
            if depth > EPS:
                h = mine.get(pn.key)
                if h is None:
                    mine[pn.key] = Hit("3D.hit", f"{name}と{pn.key}", f"棒が{pn.name}の紙を穴の無い所で通る（穴の縁から {depth:.1f}mm 内）", label,
                                       panels=[(pn.key, pn.pid)], points=[x], note=pn.key in custom, depth=depth, rods=[name])
                    hits.append(mine[pn.key])
                else:
                    h.panels.append((pn.key, pn.pid))
                    h.points.append(x)
                    if depth > h.depth:
                        h.depth, h.msg = depth, f"棒が{pn.name}の紙を穴の無い所で通る（穴の縁から {depth:.1f}mm 内）"
    if rules.get("desk"):
        low = max((q[1] for pn in pans for q in pn.pts), default=-math.inf)
        for name, ball in pose.get("balls", {}).items():
            low = max(low, ball["at"][1] + radius.get(name, 0.0))
        rod_low = max((max(rod["from"][1], rod["to"][1]) for rod in pose.get("rods", {}).values()), default=-math.inf)
        if max(low, rod_low) > DESK_TOL:
            if rod_low >= low:  # 棒の端が一番下（見直しの指摘: 前は棒を見ず、竹串が机の下へ出ても通った）
                name = max(pose["rods"], key=lambda k: max(pose["rods"][k]["from"][1], pose["rods"][k]["to"][1]))
                end = max((pose["rods"][name]["from"], pose["rods"][name]["to"]), key=lambda q: q[1])
                hits.append(Hit("3D.out", name, f"棒の端が机の下へ {rod_low:.1f}mm 出る", label, depth=rod_low, rods=[name], points=[tuple(end)]))
            else:
                worst = max(pans, key=lambda pn: max(q[1] for q in pn.pts))
                hits.append(Hit("3D.out", worst.key, f"{worst.name}が机の下へ {low:.1f}mm 出る", label, panels=[(worst.key, worst.pid)], depth=low))
    return hits


def check_below(data, pose, label, below):
    """静かな時に口の下に隠れる部品（レシピの below: 部品・口のある部品 of・空き clear）が、口から出ない。口は of の一番上（y が一番小さい所）。"""
    hits = []
    pans = panels_of(data, pose)
    names = {q["key"]: q["name"] for q in data["parts"]}
    # 決めた部品が姿に無い（隠した・入れ忘れた）時は落とす（見直しの指摘: 前は黙って通した）
    for key in [below["of"]] + list(below["parts"]):
        if not any(pn.key == key for pn in pans):
            hits.append(Hit("3D.out", key, f"静かな時の姿に{names.get(key, key)}が無く、口の下に隠れるかを確かめられない", label))
    if hits:
        return hits
    below = dict(below, mouth=min(q[1] for pn in pans if pn.key == below["of"] for q in pn.pts))
    for key in below["parts"]:
        mine = [pn for pn in pans if pn.key == key]
        top = min(q[1] for pn in mine for q in pn.pts)  # y は下が正なので、一番上は一番小さい y
        if top < below["mouth"] + below["clear"] - 0.01:
            hits.append(Hit("3D.out", key, f"静かな時に{mine[0].name}の上の端が口の {below['clear']:g}mm 下より上に出る（口から {below['mouth'] - top:+.1f}mm）",
                            label, panels=[(pn.key, pn.pid) for pn in mine]))
    return hits


def check_faces(data, pose, label, faces):
    """組み終わりの形で、決めた部品の刷った面の向き。faces は {部品: "out" | "in" | "up" | "both"}。
    out・in は部品の面の真ん中の重心から見た向き（筒・箱）、up は上（y が小さい向き）、both は 0 番と 1 番の面が逆（両面の頭）。"""
    hits = []
    pans = panels_of(data, pose)
    names = {q["key"]: q["name"] for q in data["parts"]}
    for key, want in faces.items():
        mine = [pn for pn in pans if pn.key == key]
        if not mine:
            # 決めた部品が組み終わりの姿に無い時は落とす（見直しの指摘: 前は黙って通した）
            hits.append(Hit("3D.face", key, f"組み終わりの姿に{names.get(key, key)}が無く、刷った面の向きを確かめられない", label))
            continue
        cen = tuple(sum(c) / len(c) for c in zip(*[q for pn in mine for q in pn.pts]))
        bad = []
        for pn in mine:
            mid = tuple(sum(c) / len(c) for c in zip(*pn.pts))
            if want in ("out", "in"):
                s = _dot(pn.n, _sub(mid, cen))
                ok = s > 0 if want == "out" else s < 0
                if abs(s) < 1e-6:
                    ok = True  # 真ん中を通る面（向きが決まらない）は見ない
            elif want == "up":
                ok = pn.n[1] < -0.5
            else:
                ok = True
            if not ok:
                bad.append(pn)
        if want == "both":
            by = {pn.pid: pn for pn in mine}
            if 0 in by and 1 in by and _dot(by[0].n, by[1].n) > -0.99:
                bad = [by[0], by[1]]
        if bad:
            said = {"out": "外", "in": "内", "up": "上", "both": "両側"}[want]
            hits.append(Hit("3D.face", key, f"{bad[0].name}の刷った面が{said}を向かない（面 {', '.join(str(pn.pid) for pn in bad)}）", label,
                            panels=[(pn.key, pn.pid) for pn in bad]))
    return hits


def inspect(data, rules):
    """作り方の 3D（build の dict）を検品する。rules はレシピの決め:
    - attach: {玉の名: 付く部品}、desk: 机に置く形か、below: {"parts", "mouth", "clear", "pose": (段, 姿)}、faces: {部品: 向き}
    - extra: 検品だけの姿の並び（虎の揺れの間）。JSON には出さない。
    Returns [Hit]。見る姿は、全部の段の全部の姿・できあがりの動き・extra。"""
    hits = []
    poses = [(f"手順 {s['n']}", q) for s in data["steps"] for q in s["poses"]]
    poses += [("できあがりの動き", q) for q in data["finale"]["poses"]]
    poses += [(label, q) for label, q in rules.get("extra", [])]
    for label, q in poses:
        got = check_pose(data, q, label, rules)
        for h in got:
            h.pose = q
        hits += got
    below = rules.get("below")
    if below:
        n, i = below["pose"]
        q = data["steps"][n - 1]["poses"][i]
        for h in check_below(data, q, f"手順 {n}", below):
            h.pose = q
            hits.append(h)
    if rules.get("faces"):
        last = data["steps"][-1]["poses"][-1]
        for h in check_faces(data, last, f"手順 {data['steps'][-1]['n']}", rules["faces"]):
            h.pose = last
            hits.append(h)
    return hits


def summary(hits):
    """落ちと所見を、床・所・落ちか所見かごとに 1 行にまとめる（同じ当たりが続く姿で何度も出るので）。一番深い姿の文に、ほかの姿の数を添える
    （前は最初の姿の文で、浅い当たりの数だけが出て、深さが読めなかった）。"""
    groups = {}
    for h in hits:
        groups.setdefault((h.note, h.floor, h.where), []).append(h)
    out = []
    for (note, floor, where), hs in groups.items():
        deep = max(hs, key=lambda h: h.depth)
        n = len({id(h.pose) if h.pose is not None else h.pose_label for h in hs})  # 違う姿の数（落ちの数でない）
        more = f"（ほか {n - 1} の姿）" if n > 1 else ""
        out.append(f"{'NOTE' if note else 'FAIL'} {floor} [{where}] {deep.pose_label}{more}: {deep.msg}")
    return out


# ---- 検品の記録（決める側の決定 (b): 段ごとの絵か短い動画、当たった所は赤）----
# 記録はサイトの頁の代わりではない（頁は JSON から組み立ての動きを描く）。エンジンが検品した姿をそのまま描き、落ちた所を赤、
# 所見を橙で示す。紙の面は刷った面が見える時は部品の色、裏は紙の白。見る向きはどの姿も同じ。重なりの順は面の真ん中の奥行きで決めるので、
# 入れ子の筒（御来迎の内筒）は外筒から透けて見える事がある（中を見る記録としてはそのままにした）。粘土の玉と棒は紙の上に重ねて描く
# （胴の中の玉と竹串も見えるように。当たった玉は赤い縁）。
VIEW = (-20.0, -35.0)  # 見る向き（x のまわりに rx・y のまわりに ry 度）。前の左の上から見る（虎の頭と前の壁、御来迎の口が見える）
TILE = 300  # 一覧の 1 枚の大きさ px
BACK = (243, 239, 230)  # 紙の裏
RED, ORANGE = (220, 30, 30), (240, 140, 0)
# 記録の字（日本語）。機械にある物を順に探し、無ければ PIL の字（日本語は出ない。絵と検品の結果は同じ）
_FONTS = ("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
          "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc", "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf")


def _font(size):
    from PIL import ImageFont
    for path in _FONTS:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _rot(p):
    """見る向きへ回す（y のまわりに ry、x のまわりに rx）。返りの z は見る人の方が大きい。"""
    rx, ry = (math.radians(a) for a in VIEW)
    x, y, z = p
    x, z = x * math.cos(ry) + z * math.sin(ry), -x * math.sin(ry) + z * math.cos(ry)
    y, z = y * math.cos(rx) - z * math.sin(rx), y * math.sin(rx) + z * math.cos(rx)
    return x, y, z


def _color(part):
    """部品の色: 絵の最初の塗りの色（無ければ灰）。"""
    for a in part.get("art", []):
        fill = a.get("fill")
        if isinstance(fill, str) and fill.startswith("#") and len(fill) == 7:
            return tuple(int(fill[i:i + 2], 16) for i in (1, 3, 5))
    return (190, 190, 190)


def _frame(data, pose, hits, fit):
    """姿 1 つの絵（PIL の Image）。fit は (x0, y0, scale)。"""
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (TILE, TILE), (255, 255, 255))
    d = ImageDraw.Draw(img)
    x0, y0, k = fit
    to = lambda p: (TILE / 2 + (p[0] - x0) * k, TILE / 2 + (p[1] - y0) * k)
    colors = {q["key"]: _color(q) for q in data["parts"]}
    red = {pk for h in hits if not h.note for pk in h.panels}
    org = {pk for h in hits if h.note for pk in h.panels}
    faces = []
    for pn in panels_of(data, pose):
        pts = [_rot(q) for q in pn.pts]
        nz = _rot(tuple(pn.n))[2] - _rot((0.0, 0.0, 0.0))[2]
        faces.append((sum(p[2] for p in pts) / len(pts), pts, colors[pn.key] if nz > 0 else BACK, (pn.key, pn.pid)))
    for _, pts, col, pk in sorted(faces, key=lambda f: f[0]):
        line = RED if pk in red else ORANGE if pk in org else (90, 90, 90)
        d.polygon([to(p) for p in pts], fill=col, outline=line, width=3 if line != (90, 90, 90) else 1)
    radius = {k_: v["r"] for k_, v in data.get("balls", {}).items()}
    hit_balls = {b for h in hits for b in h.balls}
    red_rods = {r for h in hits if not h.note for r in h.rods}
    org_rods = {r for h in hits if h.note for r in h.rods}
    for name, rod in pose.get("rods", {}).items():
        a, b = _rot(rod["from"]), _rot(rod["to"])
        w = max(2, int(2 * data["rods"].get(name, {}).get("r", 1.0) * k))
        col = RED if name in red_rods else ORANGE if name in org_rods else (170, 130, 70)
        d.line([to(a), to(b)], fill=col, width=w + (2 if col != (170, 130, 70) else 0))
    for name, ball in pose.get("balls", {}).items():
        c, r = to(_rot(ball["at"])), radius.get(name, 1.0) * k
        d.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], fill=(138, 111, 85), outline=RED if name in hit_balls else (60, 60, 60),
                  width=3 if name in hit_balls else 1)
    for h in hits:
        for p in h.points:
            c = to(_rot(p))
            d.ellipse([c[0] - 4, c[1] - 4, c[0] + 4, c[1] + 4], fill=ORANGE if h.note else RED)
    return img


def _fit(data, poses):
    """絵の真ん中と倍率。紙の面の点に、棒の端と玉の上下左右も入れる（見直しの指摘: 紙の外へ出た棒が絵から切れる事があった）。"""
    pts = [_rot(q) for pose in poses for pn in panels_of(data, pose) for q in pn.pts]
    pts += [_rot(rod[k]) for pose in poses for rod in pose.get("rods", {}).values() for k in ("from", "to")]
    radius = {k: v["r"] for k, v in data.get("balls", {}).items()}
    for pose in poses:
        for name, ball in pose.get("balls", {}).items():
            c, r = _rot(ball["at"]), radius.get(name, 0.0)
            pts += [(c[0] - r, c[1] - r, c[2]), (c[0] + r, c[1] + r, c[2])]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    span = max(max(xs) - min(xs), max(ys) - min(ys), 1.0)
    return ((max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2, (TILE - 40) / span)


def render(data, hits, stem):
    """検品の記録を書く: <stem>.png（段ごとの終わりの姿の一覧。落ちた段は落ちた姿）、<stem>.gif（全部の段とできあがりの動きの短い動画）、
    <stem>.txt（落ちと所見の行）。Returns 書いた path の並び。"""
    from PIL import Image, ImageDraw
    stem.parent.mkdir(parents=True, exist_ok=True)
    by_pose = {}
    for h in hits:
        by_pose.setdefault(id(h.pose), []).append(h)
    steps = [(f"手順 {s['n']}", s["poses"]) for s in data["steps"]] + [("できあがりの動き", data["finale"]["poses"])]
    extra = {}
    for h in hits:
        if h.pose is not None and not any(h.pose is q for _, qs in steps for q in qs):
            extra.setdefault(h.pose_label, h.pose)
    tiles = []
    for label, qs in steps:
        bad = [q for q in qs if id(q) in by_pose]
        tiles.append((label, bad[0] if bad else qs[-1]))
    tiles += list(extra.items())[:3]  # 検品だけの姿（揺れの間）は、落ちた姿を 3 つまで
    cols = 6
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * TILE, rows * (TILE + 24) + 40), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    fails = [h for h in hits if not h.note]
    head = f"{data['toy']} の 3D 組み立て検品: 落ち {len(fails)}・所見 {len(hits) - len(fails)}（赤＝落ち、橙＝所見）  engine {data['engine'].get('commit')}"
    d.text((10, 8), head, fill=(0, 0, 0), font=_font(20))
    for i, (label, q) in enumerate(tiles):
        hs = by_pose.get(id(q), [])
        x, y = (i % cols) * TILE, 40 + (i // cols) * (TILE + 24)
        sheet.paste(_frame(data, q, hs, _fit(data, [q])), (x, y + 24))  # 一覧は 1 枚ずつ大きく
        mark = "  落ち" if any(not h.note for h in hs) else "  所見" if hs else ""
        d.text((x + 6, y + 2), label + mark, fill=RED if any(not h.note for h in hs) else ORANGE if hs else (0, 0, 0), font=_font(16))
    png = stem.with_suffix(".png")
    sheet.save(png)
    fit = _fit(data, [q for _, qs in steps for q in qs])  # 動画はどの姿も同じ大きさ
    frames = [_frame(data, q, by_pose.get(id(q), []), fit) for _, qs in steps for q in qs]
    gif = stem.with_suffix(".gif")
    frames[0].save(gif, save_all=True, append_images=frames[1:], duration=350, loop=0)
    txt = stem.with_suffix(".txt")
    txt.write_text("\n".join([head] + summary(hits)) + "\n", encoding="utf-8")
    return [png, gif, txt]
