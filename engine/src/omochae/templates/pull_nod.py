"""雛形 pull_nod: 糸を引くと部品が軸で振れ、離すと粘土の重りで元に戻る。

形（kind）は玩具の違いなので描き分ける。
- bow: 米搗き人形（推定）。台の上の 2 本の柱に腰の軸を通し、体の前を糸で下へ引くと礼をして臼をつく。尾の粘土で起き上がる。
- jaw: 振り獅子（獅子頭）。棒の上の頭に下顎を軸で留め、顎の後ろの舌を糸で引くと口が閉じる。顎の先の粘土で口が開く。
- peck: 藁苞の鶏（推定）。図は藁苞に鶏が 2 羽載り、苞の先から細い糸が上へ伸びる。動く仕掛けは図に描かれていない。
  【解釈】ここでは、2 羽の脚を苞の上の面の溝に差して苞の中の竹串で留め、胸に結んだ糸を苞の中から下へ出し、引くと 2 羽が前へ傾いて
  苞をついばむ、と読む。尾の粘土で起き上がり、尾の先が苞に載って止まる。図の上へ伸びる糸は吊るす糸と見て、型紙には作らない。
どれも図から読んだ仕掛けで【解釈】。寸法は手元の複写の図の比と A4 の紙面から出し、どの値も実物では未確認。
Claude が変えてよいのは RANGES の名前の値だけ。

動きの見込み（check_physics の式）の前提:
- 振れる部品は軸のまわりの天秤として見る。紙の曲がり・糸の伸び・空気は入れない。
- 戻る向きの力のモーメント（g·mm）は、重りと紙の質量 × 軸からの水平の距離。静かな時は止め（bow は尾の下の柱、jaw は舌の上のこぶ）に
  押し付けられている前提で、戻る向きのモーメントが軸の摩擦の SAFETY 倍を超える事を見る。振り切った所では cos(角度) 倍に減るので、そこでも見る。
- 軸の摩擦のモーメントは 摩擦係数 MU × 全質量 × 軸の半径。竹串と紙の MU は見込み（量っていない）。
- 振れる角度は、止めに当たるまでの幾何だけで出す（bow は体を横から見た四角を軸のまわりに回して臼の四角に交わるまで、jaw は舌がこぶに当たるまで、
  peck は鶏の輪郭の頂点のどれかが苞の上の面に届くまで。辺の途中が先に当たる事は見ていない＝頂点で近似）。
- peck の鶏の紙は 1 枚（裏は無地）。手前の鶏は奥の鶏の輪郭（幅・高さ・腹の高さ）をそのまま HEN 倍にした形。脚の帯の幅と長さ・軸の深さは、
  苞の溝と穴の余白で決まるので縮めない。重り（weight_g）は 1 羽ずつに付ける。
- peck の 2 羽は、苞の幅の向きに bird_gap だけ離した 2 本の溝に差す（別の面で振れる）。bird_gap が PLANE_GAP より狭い時は同じ面と見て、
  2 羽の横から見た輪郭を 0〜振り切りの間で回し、交わるかを見る。溝が脚の帯を幅の向きに押さえるので、串の中に位置決めは要らない。
- 粘土は密度 CLAY_RHO の球と見る（半径は質量から出す）。peck の玉は鶏の外側の面に付け、玉の下が苞の上の面から 1mm 浮く高さに置く。
- 傾いた後の戻るモーメントは、質量の点 (質量, 戻る向きの水平の距離 x, 軸からの高さ z) を軸のまわりに回して測る:
  θ 引いた時の腕は x cosθ − z sinθ（引く向きに傾くと、軸より上の点は引く側へ出る）。0〜振り切りの間を 1° ごとに見て最小を取る。
  bow と jaw は質量の点を軸の高さ（z = 0）に置く（体・顎の紙の中心線の上に軸と粘土がある）ので、cos 倍と同じになる。
  peck の鶏は粘土と紙の重心が軸より上にあるので、この項が効く（前は cos 倍だけで見ていて、振り切った所で前へ倒れる既定を通していた）。
"""
import math

from shapely import affinity
from shapely.geometry import LineString, Point, Polygon, box

from ..paper_words import paper_name  # 紙の書き方は 4 つの名前だけ（制作者の指示 2026-11-05）
from ..model import Failure, Part

ID = "pull_nod"
DEFAULTS = {
    "kind": "bow",
    # bow（米搗き人形）の寸法。torso_len は腰の軸から頭の先まで、tail_len は軸から尾の端まで。
    "plank_length": 110, "plank_width": 36, "post_height": 50, "post_width": 12,
    "torso_len": 50, "torso_w": 22, "tail_len": 20, "string_arm": 14,
    "stop_height": 18, "mortar_round": 56,
    # jaw（振り獅子）の寸法。jaw_len は軸から顎の先まで、tab_len は軸から舌の端まで。
    "head_w": 50, "head_h": 46, "jaw_len": 34, "jaw_h": 14, "tab_len": 14, "stop_gap": 6,
    "stick_len": 120, "stick_w": 10,
    # peck（藁苞の鶏）の寸法。cock_h は苞の上の面から鶏の頭の上まで、leg_h は苞の上の面から腹まで、axle_depth は上の面から軸まで。
    "straw_len": 120, "straw_w": 24, "straw_h": 26, "cock_w": 50, "cock_h": 44, "leg_h": 6, "axle_depth": 6, "peck_arm": 6, "bird_gap": 12,
    "weight_g": 2.0, "glue": 8,
    # 紙の面密度は見込み。実物の紙を量ったら置き換える。
    "paper_gsm": 150,
}
RANGES = {
    "plank_length": (80, 180), "plank_width": (25, 60), "post_height": (30, 80), "post_width": (6, 20),
    "torso_len": (30, 80), "torso_w": (14, 36), "tail_len": (10, 40), "string_arm": (6, 40),
    "stop_height": (5, 60), "mortar_round": (40, 70),
    "head_w": (30, 70), "head_h": (30, 70), "jaw_len": (20, 60), "jaw_h": (8, 24), "tab_len": (6, 30), "stop_gap": (1, 20),
    "stick_len": (60, 160), "stick_w": (6, 16),
    "straw_len": (80, 160), "straw_w": (14, 40), "straw_h": (14, 40), "cock_w": (30, 60), "cock_h": (30, 56), "leg_h": (1, 20),
    "axle_depth": (4, 20), "peck_arm": (4, 20), "bird_gap": (0, 30),
    "weight_g": (0.1, 15), "glue": (5, 12), "paper_gsm": (40, 400),
}
KINDS = ("bow", "jaw", "peck")
# 刷る形を決める寸法（玩具の形）。--params では既定に頼らず必ず書かせる（compose の決まり）。
FORM = "kind"
FORMS = KINDS
# 既定の出典（既定の形 bow の物）。米搗き人形を既定にする（族の先頭の玩具）。
SOURCE = "NDL-1187053-R0000006-L-pull_nod"
# 形ごとの出典。3 つの形は別の玩具（別の図）なので、形と合わない出典を刷らない（compose が F1.source で落とす・--params の既定もここから選ぶ）。
SOURCES = {"bow": SOURCE, "jaw": "NDL-1187053-R0000030-L-pull_nod", "peck": "NDL-1187053-R0000016-R-pull_nod"}
HOLE_MARGIN = 4  # 穴の縁から紙の端・隣の穴の縁までの見込み。虎の雛形と同じ値（これより狭いと裂けやすい）
AXLE_R, STRING_R = 1.2, 1.0  # 竹串の穴と糸の穴の半径（mm）
MIN_SWING = 15  # 引いて動いたと目で分かる角度の見込み。虎の 10° より大きくするのは、礼・噛む動きが「振れ」より大きく見えないと遊びにならないため
MU = 0.4  # 竹串と紙の摩擦係数の見込み（量っていない）
SAFETY = 3  # 戻る力が摩擦の何倍あれば戻ると見るか。紙のたわみ・糸の擦れを入れていないので余裕を取る
POST_GAP = 6  # 2 本の柱の間。体の紙（2 枚重ね）が擦れずに入る幅の見込み
CLAY_IN = 3  # 粘土の中心を紙の端からこれだけ内側に付ける
CLAY_MARK_R = 2.0  # 振り獅子の顎の先に刷る、重りの位置の点の丸の半径（顎の高さの下限 8mm でも、紙の縁と先の角の落としから離れる）
# 竹串の抜け止め・鶏の位置決めに串へ付ける粘土（1 本の串あたり、見込み）。重り（weight_g）とは別に用意する。
# 同じ粘土から取ると、振れる部品に付く量が式の weight_g より減るため（部品表でも別の行にする）。軸の上に付くので戻るモーメントは 0、摩擦の質量にだけ入れる。
STOP_CLAY_G = 0.3
# 竹串の長さの見込み: 串が通る紙の厚さと、両端に抜け止めの粘土を付ける分。
PAPER_T, STOP_END = 0.15, 5
BUMP_FACE, BUMP_GLUE = 8, 5  # こぶの三角の柱の 1 面の幅と、柱を閉じる糊代の幅
WOOD, LINE, SKIN, CLOTH, ROUGE = "#c9b48a", "#3c3424", "#d9c2a0", "#6b4a2e", "#c9826b"
GOLD, FACE, MOUTH, STICK = "#c8a845", "#d4b49a", "#9a4a3a", "#cdb066"
TITLES = {"bow": "糸を引くと腰で礼をする", "jaw": "糸を引くと顎が閉じる", "peck": "糸を引くと鶏がついばむ"}
COCK, COMB, STRAW, BAND = "#a0482c", "#f2efe6", "#d8c08a", "#5a4630"
HEN = 0.8  # 手前の鶏の縮み。図で手前の鶏が奥の鶏の約 0.8 の大きさに描かれているため
PLANE_GAP = 3  # 2 羽の紙の面がこれより近いと、紙のたわみで触れるので同じ面と見る（見込み）
CLAY_RHO = 1.8e-3  # 油粘土の密度 g/mm³（見込み。量っていない）
CLAY_LIFT = 1  # 鶏の粘土の玉の下を苞の上の面から浮かせる量（mm）。玉が尾の先より先に苞に載らないように
MAX_SWING = 80  # これを超えて振れる（礼をする）と、腕の cos が小さく、90° を越えると戻らない。止めがこれより手前に要る
SWEEP_STEP = 0.25  # bow の当たりを探す角度の刻み（°）
TAB_W = 12  # 鶏の脚の帯の幅。軸の穴の縁に HOLE_MARGIN を取れる幅
TAB_BELOW = 6  # 脚の帯が軸の穴の下に伸びる長さ


def title(p):
    return TITLES[p["kind"]]


def spec():
    return {"template_id": ID, "defaults": DEFAULTS, "ranges": RANGES, "kind": KINDS}


def check_range(p):
    out = []
    for k, v in p.items():
        if k == "kind":
            if v not in KINDS:
                out.append(Failure("F5.range", k, f"{v} は {KINDS} のどれでもない"))
        elif k not in RANGES:
            out.append(Failure("F5.range", k, "知らない寸法の名前"))
        elif not isinstance(v, (int, float)) or isinstance(v, bool) or not RANGES[k][0] <= v <= RANGES[k][1]:
            out.append(Failure("F5.range", k, f"{v} は範囲 {RANGES[k]} の外"))
    return out


def paper_mass(area_mm2, gsm):
    return area_mm2 * 1e-6 * gsm


def moment_at(pts, deg):
    """質量の点 [(質量 g, x, z)] を軸のまわりに deg 度回した時の戻る向きのモーメント（g·mm）。腕は x cosθ − z sinθ。"""
    t = math.radians(deg)
    return sum(m * (x * math.cos(t) - z * math.sin(t)) for m, x, z in pts)


def min_moment(pts, sw):
    """0° から振り切り（sw）までの戻るモーメントの最小。1° ごとと振り切りの所で見る（腕は角度の sin・cos の和なので、端か途中で最小）。"""
    angles = [a for a in range(0, int(sw) + 1)] + [sw]
    return min(moment_at(pts, a) for a in angles)


def lever(p):
    """振れる部品の質量の点 [(質量 g, 戻る向きに正の水平の距離 mm, 軸からの高さ mm)] と、糸の腕（mm）。高さは bow・jaw とも 0。

    bow は体の紙（2 枚重ね）と尾の粘土。紙の重心は体の中央で、軸より前（礼の向き）に (torso_len - tail_len)/2。
    jaw は顎の紙（1 枚）と顎の先の粘土。戻る向き（口が開く向き）は前。
    """
    g = p["paper_gsm"]
    if p["kind"] == "bow":
        card = paper_mass(2 * p["torso_w"] * (p["torso_len"] + p["tail_len"]), g)
        pts = [(card, -(p["torso_len"] - p["tail_len"]) / 2, 0), (p["weight_g"], p["tail_len"] - CLAY_IN, 0)]
        return pts, p["string_arm"]
    card = paper_mass(p["jaw_h"] * (p["jaw_len"] + p["tab_len"]), g)
    pts = [(card, (p["jaw_len"] - p["tab_len"]) / 2, 0), (p["weight_g"], p["jaw_len"] - CLAY_IN, 0)]
    return pts, jaw_string_arm(p)


def jaw_string_arm(p):
    # 糸の穴は舌の端から HOLE_MARGIN + 糸の穴の半径 + 0.5 の所。端に寄せるほど腕が長く軽く引けるが、端が裂ける。
    return p["tab_len"] - (HOLE_MARGIN + STRING_R + 0.5)


def return_moment(p):
    """静かな時の戻る向きのモーメント（g·mm）と、軸の摩擦のモーメント（g·mm）。"""
    pts, _ = lever(p)
    m = moment_at(pts, 0)
    # 抜け止めの粘土は軸の上に付くので、腕は 0 で摩擦の質量にだけ入る。
    friction = MU * (sum(w for w, _, _ in pts) + STOP_CLAY_G) * AXLE_R
    return m, friction


def swing_deg(p):
    """引いて止めに当たるまでに振れる角度。

    bow: bow_contact の、体が臼に当たる角度。臼でなく台に当たる・90° まで何にも当たらない時は None。
    jaw: 静かな時は舌がこぶに当たって口が開いている。引くと口が閉じるまで（顎が水平まで）振れる。
    こぶに当たるのは舌の端の上の角で、軸から (tab_len, jaw_h/2) にある。この角は半径 ρ = hypot(tab_len, jaw_h/2) の円を回るので、
    θ 開いた時の高さは ρ sin(φ + θ)（φ = atan2(jaw_h/2, tab_len)）。こぶの下の面（軸から jaw_h/2 + stop_gap の高さ）に届く θ は
    asin((jaw_h/2 + stop_gap)/ρ) − φ。こぶが ρ より高いと角は届かず、止めが無いのと同じなので None を返す。
    （前は atan2(stop_gap, tab_len) で、上がる高さが角度に比例すると見ていた。高さは sin で頭打ちになるので、届かない寸法も通していた。）
    """
    if p["kind"] == "bow":
        deg, what = bow_contact(p)
        return deg if what == "mortar" else None
    h2 = p["jaw_h"] / 2
    rho = math.hypot(p["tab_len"], h2)
    reach = (h2 + p["stop_gap"]) / rho
    if reach >= 1:
        return None
    return math.degrees(math.asin(reach) - math.atan2(h2, p["tab_len"]))


def bow_side(p):
    """bow を横から見た体と臼と台の形。座標は前を正の f、上を正の z、台の上の面を z = 0、軸を (0, post_height)。"""
    T, t, TW, ph = p["torso_len"], p["tail_len"], p["torso_w"], p["post_height"]
    torso = box(-t, ph - TW / 2, T, ph + TW / 2)
    r = p["mortar_round"] / (2 * math.pi)
    mx = mortar_ahead(p)
    mortar = box(mx - r, 0, mx + r, p["stop_height"])
    plank = box(-p["plank_length"], -50, 2 * p["plank_length"], 0)
    return torso, mortar, plank, (0, ph)


def mortar_ahead(p):
    """臼の中心の軸からの前への距離。頭の先から 5mm 内側の下に置く（台の目印も同じ値）。"""
    return p["torso_len"] - 5


def bow_contact(p):
    """体を軸のまわりに前へ回し（時計回り）、最初に当たる物と角度を返す。("mortar"|"plank"|"none", 角度)。
    前は「頭の下の縁が臼の高さまで下がる角度」だけを見ていて、頭が臼の上にあるかを見ていなかった。角度が大きいと頭の先は
    軸の前 T·cosθ まで引っ込み、臼を外れて台に当たるか、90° を越えて戻らない。横から見た四角を回して交わりで見る。"""
    torso, mortar, plank, origin = bow_side(p)
    a = 0.0
    while a <= 90 + 1e-9:
        r = affinity.rotate(torso, -a, origin=origin)
        if r.intersection(mortar).area > 1e-6:
            return a, "mortar"
        if r.intersection(plank).area > 1e-6:
            return a, "plank"
        a += SWEEP_STEP
    return 90.0, "none"


def jaw_contact_back(p):
    """舌の端の角がこぶに当たる所の、軸からの後ろへの水平の距離。角は半径 ρ の円の上で、高さ jaw_h/2 + stop_gap の所。"""
    h2 = p["jaw_h"] / 2
    rho = math.hypot(p["tab_len"], h2)
    return math.sqrt(max(0.0, rho * rho - (h2 + p["stop_gap"]) ** 2))


def bump_box(p):
    """頭の紙の上の、こぶを貼る所（こぶの 1 面の四角）。下の辺が軸から jaw_h/2 + stop_gap 上、当たる所を真ん中にする。"""
    px, py = jaw_pivot(p)
    xc = px + jaw_contact_back(p)
    yb = py - (p["jaw_h"] / 2 + p["stop_gap"])
    return xc - BUMP_FACE / 2, yb - BUMP_FACE, xc + BUMP_FACE / 2, yb


def pull_gf(p):
    """引き切る時に糸に要る力（gf）。戻るモーメントと摩擦を糸の腕で割る。組み方の文に見当として書くだけで、床にはしない。
    peck は 2 羽を 1 本の糸で引くので、2 羽の分を足す。"""
    if p["kind"] == "peck":
        total = 0.0
        for which in ("cock", "hen"):
            m, friction = bird_moment(p, which)
            b = bird(p, which)
            total += (m + friction) / (b["pivot"][0] - b["string"][0])
        return total
    m, friction = return_moment(p)
    _, arm = lever(p)
    return (m + friction) / arm if arm > 0 else math.inf


def hole_margins(parts):
    """穴ごとに、紙の端までと隣の穴までの縁の余白の最小（mm）。F5.hole は穴が紙の中にあるかだけを見るので、裂けにくさはここで見る。"""
    out = []
    for q in parts:
        edge = Polygon(q.outline).exterior
        for i, (x, y, r) in enumerate(q.holes):
            gaps = [edge.distance(Point(x, y)) - r]
            gaps += [math.hypot(x - x2, y - y2) - r - r2 for x2, y2, r2 in q.holes[i + 1:]]
            out.append((q.name, (x, y), min(gaps)))
    return out


def check_physics(p):
    if p["kind"] == "peck":
        return _check_peck(p)
    out = []
    m, friction = return_moment(p)
    sw = swing_deg(p)
    what = "尾の粘土" if p["kind"] == "bow" else "顎の先の粘土"
    if sw is None and p["kind"] == "jaw":
        # 止めに届かない時は角度が決まらない。顎は止まらずに垂れ下がるので、ここで落とす。
        # 振り切った所の戻りと振れの量はこの時は決まらないので見ない（同じ原因で別の文を重ねて出さない）。
        h2 = p["jaw_h"] / 2
        out.append(Failure("F5.pull_nod", "こぶ", f"こぶが軸から {h2 + p['stop_gap']:.1f}mm 上で、舌の端の角（軸から {math.hypot(p['tab_len'], h2):.1f}mm）が届かない"))
    elif sw is None:
        deg, what = bow_contact(p)
        hit = {"plank": f"{deg:.0f}° で台に当たる", "none": "90° まで何にも当たらない"}[what]
        out.append(Failure("F5.pull_nod", "臼", f"頭が臼を外れ、{hit}（臼は軸の前 {mortar_ahead(p):.0f}mm）"))
    elif sw >= MAX_SWING:
        out.append(Failure("F5.pull_nod", "臼", f"臼に当たるまで {sw:.0f}° 振れ、{MAX_SWING}° を超える（起き上がる腕が小さすぎる）"))
    # 1. 戻る力が静かな時に勝つ。負なら止めから離れて倒れたまま、摩擦より小さければ引いた後に戻らない。
    if m <= SAFETY * friction:
        out.append(Failure("F5.pull_nod", what, f"戻るモーメント {m:.1f}g·mm が摩擦 {friction:.1f}g·mm の {SAFETY} 倍以下で、離しても戻らない"))
    elif sw is not None and min_moment(lever(p)[0], sw) <= SAFETY * friction:
        out.append(Failure("F5.pull_nod", what, f"{sw:.0f}° 振り切った所で戻るモーメントが摩擦の {SAFETY} 倍以下になる"))
    # 2. 引いた時に止めに当たるまで MIN_SWING 以上振れる。
    if sw is not None and sw < MIN_SWING:
        stop = "臼" if p["kind"] == "bow" else "こぶ"
        out.append(Failure("F5.pull_nod", stop, f"{stop}に当たるまで {sw:.1f}° しか振れない（{MIN_SWING}° 要る）"))
    # 3. 穴の縁の余白。
    for name, (x, y), gap in hole_margins(parts(p)):
        if gap < HOLE_MARGIN:
            out.append(Failure("F5.pull_nod", name, f"穴 ({x:.1f}, {y:.1f}) の縁から端か隣の穴まで {gap:.1f}mm で、{HOLE_MARGIN}mm 取れない"))
    if p["kind"] == "bow":
        # 軸の前に臼（の前の縁まで）、後ろに尾と止めの柱が載らないと、台からはみ出す。軸は台の後ろの端から tail_len + 5 の所。
        # 前は体と尾の長さ + 10 で見ていて、臼が大きいと臼の目印が台の前の端から出た。
        need = math.ceil(p["tail_len"] + 5 + mortar_ahead(p) + p["mortar_round"] / (2 * math.pi) + 2)
        if p["plank_length"] < need:
            out.append(Failure("F5.pull_nod", "台", f"台が {p['plank_length']}mm で、臼から尾までの載る {need}mm に足りない"))
    else:
        # こぶを貼る所（当たる所の上の四角）が頭の紙の中に無いと、貼れない。
        if sw is not None and not Polygon(_head_outline(p)).buffer(1e-6).contains(box(*bump_box(p))):
            out.append(Failure("F5.pull_nod", "こぶ", "こぶを貼る所が頭の紙の外に出る"))
    return out


# ---- peck（藁苞の鶏） ----
# 鶏の輪郭。R0000016 右頁（表示の 1205 幅の座標）の奥の鶏を見て手で取った点を、外接の箱で 0〜1 に直した物。原図の画素は使っていない。
# u は左（くちばし）から右（尾）、v は上（とさか）から下。v = 0.74 が腹、v = 1 が尾の先（苞の上の面に載る所）。
_BIRD = [(0.0, 0.12), (0.05, 0.09), (0.06, 0.0), (0.2, 0.0), (0.24, 0.06), (0.2, 0.12), (0.17, 0.2), (0.3, 0.36), (0.6, 0.42),
         (0.78, 0.3), (0.95, 0.32), (1.0, 0.42), (0.9, 0.48), (0.98, 0.68), (0.9, 0.82), (0.82, 1.0), (0.74, 0.86), (0.6, 0.74),
         (0.4, 0.74), (0.22, 0.62), (0.12, 0.42), (0.06, 0.24), (0.02, 0.18)]
_COMB = [(0.06, 0.0), (0.2, 0.0), (0.24, 0.06), (0.2, 0.1), (0.07, 0.08)]
_FEATHERS = [[(0.5, 0.5), (0.7, 0.62)], [(0.62, 0.48), (0.85, 0.7)], [(0.8, 0.4), (0.92, 0.62)], [(0.78, 0.56), (0.86, 0.9)], [(0.3, 0.45), (0.45, 0.6)]]
# 粘土は尾の先の近く（苞の上の面のすぐ上）に付ける。軸より高い所に付けると、ついばんで前へ傾いた時に腕が縮んで負になり、前へ倒れる。
BELLY_V, CLAY_UV = 0.74, (0.82, 0.92)


def _bird_y(v, H, leg):
    """v を紙の y へ写す。腹より上は鶏の体の高さ（H − 脚の高さ）に、腹から尾の先までは脚の高さに縮める。
    腹の高さ（leg_h）を寸法で動かしても、尾の先が苞の上の面に載る形を保つため。"""
    if v <= BELLY_V:
        return v / BELLY_V * (H - leg)
    return (H - leg) + (v - BELLY_V) / (1 - BELLY_V) * leg


def bird(p, which):
    """鶏 1 羽の紙の形と、軸・糸・粘土の位置（紙の座標。苞の上の面は y = H）。"""
    k = 1.0 if which == "cock" else HEN
    w, H, leg, d = p["cock_w"] * k, p["cock_h"] * k, p["leg_h"] * k, p["axle_depth"]
    uv = lambda ps: [(u * w, _bird_y(v, H, leg)) for u, v in ps]
    body = Polygon(uv(_BIRD))
    xp = 0.5 * w
    tab = Polygon([(xp - TAB_W / 2, H - leg - 1), (xp + TAB_W / 2, H - leg - 1), (xp + TAB_W / 2, H + d + TAB_BELOW), (xp - TAB_W / 2, H + d + TAB_BELOW)])
    shape = body.union(tab)
    outline = [(round(x, 4), round(y, 4)) for x, y in list(shape.exterior.coords)[:-1]]
    sx = xp - p["peck_arm"] * k
    # 糸の穴は、その x での体の下の縁から HOLE_MARGIN + 半径 + 1.5 だけ上。下の縁は縦の線と体の交わりの下の端。
    # 胸の下の縁は斜めなので、縦に測った余白より縁までの距離が短い。その分 1.5mm（0.5 では斜めの縁まで 4mm に届かなかった）。
    cut = LineString([(sx, -1), (sx, H + 1)]).intersection(body)
    ys = [y for g in getattr(cut, "geoms", [cut]) for _, y in g.coords] or [H / 2]
    sy = max(ys) - (HOLE_MARGIN + STRING_R + 1.5)
    # 粘土の玉は、玉の下が苞の上の面から CLAY_LIFT 浮く高さに中心を置き、その高さの体の後ろの縁から 2mm 内側に付ける。
    rad = clay_radius(p["weight_g"])
    cy = H - CLAY_LIFT - rad
    row = LineString([(-1, cy), (w + 1, cy)]).intersection(body)
    xs = [x for g in getattr(row, "geoms", [row]) for x, _ in g.coords]
    clay = (max(xs) - 2, cy) if xs else (CLAY_UV[0] * w, cy)
    return {"w": w, "H": H, "d": d, "body": body, "outline": outline, "pivot": (xp, H + d), "string": (sx, sy), "clay": clay, "k": k}


def clay_radius(g):
    """質量 g の油粘土の玉の半径（mm）。"""
    return (3 * g / (4 * math.pi * CLAY_RHO)) ** (1 / 3)


def bird_side(p, which):
    """鶏を苞に沿って横から見た輪郭と軸。X は苞の左の端から、Z は苞の上の面から上が正。"""
    b = bird(p, which)
    xp, _ = b["pivot"]
    X = slot(p, which)["cx"]
    return Polygon([(X + x - xp, b["H"] - y) for x, y in b["outline"]]), (X, -b["d"])


def birds_collide(p):
    """2 羽が同じ面にいる時、0〜振り切りの間の傾きの組で、横から見た輪郭が交わる最初の組 (手前, 奥) の角度。交わらなければ None。
    鶏は前（左）へ傾くので、横から見て反時計回りに回す。2 羽は 1 本の糸で引くが、紙の硬さで傾きがずれうるので、組を全部見る。"""
    if p["bird_gap"] >= PLANE_GAP:
        return None
    hen, oh = bird_side(p, "hen")
    cock, oc = bird_side(p, "cock")
    sh, sc = bird_swing(p, "hen"), bird_swing(p, "cock")
    steps = lambda sw: [sw * i / 20 for i in range(21)]
    hens = [(a, affinity.rotate(hen, a, origin=oh)) for a in steps(sh)]
    for b_ in steps(sc):
        c = affinity.rotate(cock, b_, origin=oc)
        for a, h in hens:
            if h.intersection(c).area > 1e-6:
                return a, b_
    return None


def string_ahead(p, which):
    """胸の糸の穴が、0〜振り切りの間で軸の前へ出る最大（mm）。前へ傾くと、軸より上の穴は前へ出る（f cosθ + z sinθ）。"""
    b = bird(p, which)
    xp, zp = b["pivot"]
    f, z = xp - b["string"][0], zp - b["string"][1]
    sw = bird_swing(p, which)
    return max(f * math.cos(math.radians(a)) + z * math.sin(math.radians(a)) for a in [sw * i / 20 for i in range(21)])


def bird_points(p, which):
    """鶏 1 羽の質量の点 [(質量 g, 後ろ向きに正の水平の距離 x, 軸からの高さ z)]。粘土と紙（重心は輪郭の重心）。"""
    b = bird(p, which)
    shape = Polygon(b["outline"])
    xp, zp = b["pivot"]
    card = paper_mass(shape.area, p["paper_gsm"])
    return [(p["weight_g"], b["clay"][0] - xp, zp - b["clay"][1]), (card, shape.centroid.x - xp, zp - shape.centroid.y)]


def bird_moment(p, which):
    """鶏 1 羽の静かな時の戻るモーメント（g·mm）と軸の摩擦（g·mm）。"""
    pts = bird_points(p, which)
    return moment_at(pts, 0), MU * (sum(m for m, _, _ in pts) + STOP_CLAY_G) * AXLE_R


def bird_swing(p, which):
    """前へ傾けて、輪郭の頂点のどれかが苞の上の面（軸の d 上）に届くまでの角度。
    頂点を軸のまわりの極座標 (ρ, φ)（φ は前向きから上へ）に置くと、前へ θ 傾けた高さは ρ sin(φ − θ)。d に届く θ = φ − asin(d/ρ)。
    静かな時に上の面より上にある頂点だけを見る（上の面より下は溝の中を通る脚の帯）。尾の先は静かな時に面の上にあり、θ = 0 で後ろの止めになる。"""
    b = bird(p, which)
    xp, zp = b["pivot"]
    d = b["d"]
    best = 90.0
    for x, y in b["outline"]:
        f, z = xp - x, zp - y
        if z < d - 1e-9 or f <= 0:
            continue
        rho, phi = math.hypot(f, z), math.atan2(z, f)
        best = min(best, math.degrees(phi - math.asin(min(1.0, d / rho))))
    return best


def _check_peck(p):
    out = []
    for which, name in (("cock", "奥の鶏"), ("hen", "手前の鶏")):
        m, friction = bird_moment(p, which)
        sw = bird_swing(p, which)
        if m <= SAFETY * friction:
            out.append(Failure("F5.pull_nod", f"{name}の尾の粘土", f"戻るモーメント {m:.1f}g·mm が摩擦 {friction:.1f}g·mm の {SAFETY} 倍以下で、離しても戻らない"))
        elif min_moment(bird_points(p, which), sw) <= SAFETY * friction:
            low = min_moment(bird_points(p, which), sw)
            out.append(Failure("F5.pull_nod", f"{name}の尾の粘土", f"{sw:.0f}° 傾くまでに戻るモーメントが {low:.1f}g·mm になり、摩擦の {SAFETY} 倍以下（前へ倒れる）"))
        if sw < MIN_SWING:
            out.append(Failure("F5.pull_nod", name, f"苞に当たるまで {sw:.1f}° しか傾かない（{MIN_SWING}° 要る）"))
    for name, (x, y), gap in hole_margins(parts(p)):
        if gap < HOLE_MARGIN:
            out.append(Failure("F5.pull_nod", name, f"穴 ({x:.1f}, {y:.1f}) の縁から端か隣の穴まで {gap:.1f}mm で、{HOLE_MARGIN}mm 取れない"))
    # 脚の帯の下の端が苞の底に当たると、傾けない。
    if p["axle_depth"] + TAB_BELOW + 3 > p["straw_h"]:
        out.append(Failure("F5.pull_nod", "藁苞", f"苞の高さ {p['straw_h']}mm に、軸の深さと脚の帯の下の端が収まらない"))
    # 2 本の溝は苞の上の面に収まる（縁まで HOLE_MARGIN）。同じ面なら苞に沿う向きにも重ならない。
    if p["bird_gap"] / 2 + 1 + HOLE_MARGIN > p["straw_w"] / 2:
        out.append(Failure("F5.pull_nod", "藁苞", f"2 本の溝の間 {p['bird_gap']}mm が苞の幅に収まらない"))
    a, b = slot(p, "hen"), slot(p, "cock")
    if p["bird_gap"] < 2 + HOLE_MARGIN and a["x0"] + a["len"] + 3 > b["x0"]:
        out.append(Failure("F5.pull_nod", "藁苞", "2 羽の溝が近すぎる"))
    if a["x0"] < 2 or b["x0"] + b["len"] > p["straw_len"] - 2:
        out.append(Failure("F5.pull_nod", "藁苞", "溝が苞の端から出る"))
    # 2 羽が同じ面で振れると、傾いた時にぶつかる。
    hit = birds_collide(p)
    if hit:
        out.append(Failure("F5.pull_nod", "鶏", f"2 羽が同じ面で振れ、手前の鶏 {hit[0]:.0f}°・奥の鶏 {hit[1]:.0f}° でぶつかる"))
    return out


def slot(p, which):
    """苞の上の面の溝。cx は軸の x、x0 と len は溝の始めと長さ、y は苞の幅の向きの真ん中。手前の鶏が前（左）。
    前へ傾くと、脚の帯が上の面を通る所は前へ d·tanθ ずれ、幅は 1/cosθ 倍になる。胸の糸も溝を通るので、傾いて前へ出た糸の穴（string_ahead）
    より 1.5mm 前まで開ける（前は脚の帯の分だけで、43° で糸の穴が溝の前の端より 5mm 前に出た）。
    2 本の溝は苞の幅の向きに bird_gap だけ離す（前は 2 本とも真ん中で、2 羽が同じ面で振れてぶつかった）。"""
    at, side = (0.3, -1) if which == "hen" else (0.64, 1)
    sw = math.radians(bird_swing(p, which))
    front = max(TAB_W / 2 / math.cos(sw) + p["axle_depth"] * math.tan(sw) + 1, string_ahead(p, which) + 1.5)
    cx = p["straw_len"] * at
    return {"cx": cx, "x0": cx - front, "len": front + TAB_W / 2 + 1, "y": p["straw_w"] / 2 + side * p["bird_gap"] / 2}


def _bird_part(p, which, number, key, name):
    b = bird(p, which)
    w, H, leg = b["w"], b["H"], p["leg_h"] * b["k"]
    uv = lambda ps: [(u * w, _bird_y(v, H, leg)) for u, v in ps]
    body = list(b["body"].exterior.coords)[:-1]
    inner = b["body"].buffer(-0.15)
    art = [{"kind": "poly", "pts": body, "fill": COCK, "stroke": LINE, "sw": 0.2}]
    comb = Polygon(uv(_COMB)).intersection(inner)
    art.append({"kind": "poly", "pts": list(comb.exterior.coords)[:-1], "fill": COMB})
    art += _clip_lines([uv(ln) for ln in _FEATHERS], inner, LINE, 0.3)
    ex, ey = 0.12 * w, _bird_y(0.13, H, leg)
    art.append({"kind": "poly", "pts": [(ex - 0.6, ey), (ex, ey - 0.6), (ex + 0.6, ey), (ex, ey + 0.6)], "fill": LINE})
    (px, py), (sx, sy) = b["pivot"], b["string"]
    return Part(number, key, name, b["outline"], label_xy=(px - 2, py - 1.7 - 3.5 - 1.5), label=str(number), art=art,
                holes=[(px, py, AXLE_R), (sx, sy, STRING_R)])


def _peck_parts(p):
    L, W, Hs, g, d = p["straw_len"], p["straw_w"], p["straw_h"], p["glue"], p["axle_depth"]
    # 1 藁苞: 上の面・横・底・横・糊代の順に並べた箱。両端は開けたまま（藁の束の切り口に見立てる）。
    rows = [0, W, W + Hs, 2 * W + Hs, 2 * W + 2 * Hs, 2 * W + 2 * Hs + g]
    # 苞は色の面（藁の色）を外にして角の筒にするので、刷った面から見て山折り。谷折り（凡例の、刷った面がへこむ向き）のままだと
    # 色の面が筒の内に入った。制作者の決定（2026-11-06「今のうちに4つ直す」）で、御来迎の外筒・虎の胴と同じ線で直した。
    # 線は破線で刷るので、刷る線の形が山折りの形に変わる。穴と溝の高さは筒の向きに依らない（2 つの横の穴はどちらも上の面から d）
    straw = Part(1, "straw", "藁苞", [(0, 0), (L, 0), (L, rows[5]), (0, rows[5])], label_xy=(2, 1), label="1",
                 mountain=[((0, y), (L, y)) for y in rows[1:5]], glue=[[(0, rows[4]), (L, rows[4]), (L, rows[5]), (0, rows[5])]])
    holes, cuts = [], []
    for which in ("hen", "cock"):
        sl = slot(p, which)
        cx = sl["cx"]
        cuts.append((sl["x0"], sl["y"] - 1, sl["len"], 2))
        holes += [(cx, W + d, AXLE_R), (cx, rows[4] - d, AXLE_R)]
        # 糸は溝を通って苞の中へ入り、底の穴から出す。底の穴は胸の糸の穴の真下で、溝と同じ幅の向きの位置。
        # 底の面は上の面と幅の向きが同じ（展開図で上の面と同じ向きに並ぶ）。
        holes.append((cx - p["peck_arm"] * (1.0 if which == "cock" else HEN), W + Hs + sl["y"], STRING_R))
    straw.holes, straw.cuts = holes, cuts
    straw.art = []
    for y0, y1 in zip(rows[:4], rows[1:5]):
        straw.art.append(_panel(6, y0 + 0.3, L - 0.3, y1 - 0.3, STRAW))
        straw.art += [{"kind": "line", "pts": [(8, y), (L - 2, y)], "stroke": BAND, "sw": 0.2} for y in [y0 + (y1 - y0) * f for f in (0.25, 0.5, 0.75)]]
        # 苞の左の端を縛った帯（図の結び目）。
        straw.art.append(_panel(10, y0 + 0.3, 14, y1 - 0.3, BAND))
    return [straw, _bird_part(p, "cock", 2, "cock", "奥の鶏"), _bird_part(p, "hen", 3, "hen", "手前の鶏")]


def _panel(x0, y0, x1, y1, fill):
    return {"kind": "poly", "pts": [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], "fill": fill}


def _box(x0, y0, x1, y1):
    """貼る所の目印の四角（線）。"""
    return {"kind": "line", "pts": [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)], "stroke": LINE, "sw": 0.25}


def _fit(pts, x0, y0, w0, h0, ox, oy, w, h):
    """図の上で取った点（図の画素の座標）を、部品の中の箱へ写す。縦横の比は箱に合わせて変わる。"""
    return [(ox + (x - x0) / w0 * w, oy + (y - y0) / h0 * h) for x, y in pts]


def _clip_lines(lines, shape, stroke, sw):
    out = []
    for line in lines:
        piece = LineString(line).intersection(shape)
        for g in getattr(piece, "geoms", [piece]):
            if not g.is_empty and g.geom_type == "LineString":
                out.append({"kind": "line", "pts": list(g.coords), "stroke": stroke, "sw": sw})
    return out


# 米搗き人形の体。R0000006 左頁を 1600 幅で見た図（表示の 1205 幅の座標）から手で取った点。原図の画素は使っていない。
# 図は前かがみの姿なので、型紙では水平に伸ばして写す（頭が左＝前、腰が右）。
_FIG = [(505, 1080), (520, 1050), (550, 1035), (580, 1040), (605, 1062), (650, 1048), (800, 1075), (880, 1110), (950, 1150), (960, 1185),
        (940, 1240), (900, 1260), (860, 1240), (760, 1200), (650, 1165), (600, 1172), (560, 1180), (520, 1160), (505, 1130)]
_CLOTH = [(865, 1100), (945, 1135), (962, 1200), (935, 1255), (905, 1258), (895, 1175), (860, 1150)]
_CHEEK = [(530, 1120), (548, 1112), (562, 1125), (550, 1142), (532, 1138)]
_FIG_LINES = [[(600, 1172), (612, 1100)]]  # 首の線だけ。腰の線は帯の絵と重なって読めなかった
FIG_BOX = (500, 1030, 460, 230)


def _figure_art(ox, oy, w, h, flip):
    """体の紙の半分 1 枚の絵。flip は折って裏になる半分（折り線で上下に写す）。"""
    fit = lambda ps: _fit(ps, *FIG_BOX, ox, oy, w, h)
    fix = (lambda ps: [(x, 2 * oy + h - y) for x, y in ps]) if flip else (lambda ps: ps)
    body = fix(fit(_FIG))
    shape = Polygon(body)
    art = [{"kind": "poly", "pts": body, "fill": SKIN, "stroke": LINE, "sw": 0.2}]
    for piece, fill in ((_CLOTH, CLOTH), (_CHEEK, ROUGE)):
        g = Polygon(fix(fit(piece))).intersection(shape.buffer(-0.15))
        for q in getattr(g, "geoms", [g]):
            if not q.is_empty and q.geom_type == "Polygon":
                art.append({"kind": "poly", "pts": list(q.exterior.coords)[:-1], "fill": fill})
    art += _clip_lines([fix(fit(ln)) for ln in _FIG_LINES], shape.buffer(-0.1), LINE, 0.35)
    return art


# 獅子頭。R0000030 左頁（表示の 1205 幅の座標）から手で取った点。鼻先が左、頭の後ろが右。顎は別の部品にする。
_HEAD = [(505, 1035), (540, 1005), (590, 975), (575, 935), (610, 900), (680, 885), (760, 900), (800, 940), (800, 1010), (790, 1080),
         (790, 1170), (640, 1170), (620, 1090), (530, 1075), (505, 1060)]
_MANE = [(575, 935), (610, 900), (680, 885), (760, 900), (800, 940), (790, 975), (700, 960), (620, 975)]
_EYES = [[(600, 1022), (622, 1015), (632, 1032), (610, 1040)], [(648, 1030), (670, 1024), (678, 1042), (655, 1048)]]
_HEAD_LINES = [[(590, 1000), (640, 990)], [(645, 1005), (690, 1000)], [(510, 1050), (600, 1062)], [(700, 990), (760, 1060)], [(730, 980), (780, 1040)]]
HEAD_BOX = (505, 885, 295, 285)
MANE_HUB = (690, 1000)


def _head_outline(p):
    return _fit(_HEAD, *HEAD_BOX, 0, 0, p["head_w"], p["head_h"])


def _head_part(p):
    w, h = p["head_w"], p["head_h"]
    fit = lambda ps: _fit(ps, *HEAD_BOX, 0, 0, w, h)
    outline = _head_outline(p)
    shape = Polygon(outline).buffer(-0.15)
    art = [{"kind": "poly", "pts": outline, "fill": FACE, "stroke": LINE, "sw": 0.2}]
    mane = Polygon(fit(_MANE)).intersection(shape)
    art.append({"kind": "poly", "pts": list(mane.exterior.coords)[:-1], "fill": GOLD})
    # たてがみの毛は、図の放射の線を中心から外へ引いて、たてがみの中だけ残す（図の金の毛の数を写すのでなく、向きを写す）。
    hub = fit([MANE_HUB])[0]
    rays = [[hub, (hub[0] + 60 * math.cos(math.radians(a)), hub[1] - 60 * math.sin(math.radians(a)))] for a in range(20, 165, 12)]
    art += _clip_lines(rays, mane.buffer(-0.2), LINE, 0.25)
    art += [{"kind": "poly", "pts": fit(e), "fill": "#ffffff", "stroke": LINE, "sw": 0.25} for e in _EYES]
    art += _clip_lines([fit(ln) for ln in _HEAD_LINES], shape, LINE, 0.35)
    if swing_deg(p) is not None and Polygon(outline).contains(box(*bump_box(p))):
        # こぶを貼る所の目印。舌の角が当たる所（軸から jaw_contact_back 後ろ）の真上に、組み方の文と同じ式で置く。
        # 頭の外に出る寸法は check_physics が F5.pull_nod で落とすので、ここでは描かない（同じ原因で F5.image_box を重ねない）。
        art.append(_box(*bump_box(p)))
    px, py = jaw_pivot(p)
    return Part(1, "head", "頭", outline, label_xy=(w * 0.55, h * 0.58), label="1", art=art, holes=[(px, py, AXLE_R)])


def jaw_pivot(p):
    """頭の紙の上の顎の軸の穴。舌が頭の右の縁の 2mm 内側で終わり、閉じた顎が頭の下の縁に揃う所。"""
    return p["head_w"] - p["tab_len"] - 2, p["head_h"] - p["jaw_h"] / 2


def _bow_parts(p):
    L, W = p["plank_length"], p["plank_width"]
    T, t, TW = p["torso_len"], p["tail_len"], p["torso_w"]
    g, ph, pw = p["glue"], p["post_height"], p["post_width"]
    # 1 台: 2 枚重ねにして反らないようにする。糸の穴は軸の真下から string_arm だけ前。
    pivot_x = L - t - 5
    sx = pivot_x - p["string_arm"]
    plank = Part(1, "plank", "台", [(0, 0), (L, 0), (L, 2 * W), (0, 2 * W)], label_xy=(2, 2), label="1 台",
                 valley=[((0, W), (L, W))], holes=[(sx, W / 2, STRING_R), (sx, 1.5 * W, STRING_R)])
    plank.art = [_panel(0.3, 0.3, L - 0.3, W - 0.3, WOOD), _panel(0.3, W + 0.3, L - 0.3, 2 * W - 0.3, WOOD)]
    # 上の面に、柱・止めの柱・臼を貼る所の目印を描く。軸の位置と糸の穴の距離が式の前提なので、貼る所を目で合わせられるようにする。
    fx = pivot_x + t - CLAY_IN
    mx = pivot_x - (T - 5)
    r = p["mortar_round"] / (2 * math.pi)
    plank.art += [_box(pivot_x - pw / 2, W / 2 - POST_GAP / 2, pivot_x + pw / 2, W / 2 + POST_GAP / 2),
                  _box(fx - g / 2, W / 2 - pw / 2, fx + g / 2, W / 2 + pw / 2),
                  _box(mx - r, W / 2 - r, mx + r, W / 2 + r)]
    # 2 柱: 1 本の帯を U の字に折り、底を台に貼る。穴の中心が台から post_height の高さに来るよう、柱の長さは post_height + 幅の半分。
    side = ph + pw / 2
    posts = Part(2, "posts", "柱", [(0, 0), (2 * side + POST_GAP, 0), (2 * side + POST_GAP, pw), (0, pw)], label_xy=(pw, 1.5), label="2",
                 valley=[((side, 0), (side, pw)), ((side + POST_GAP, 0), (side + POST_GAP, pw))],
                 glue=[[(side, 0), (side + POST_GAP, 0), (side + POST_GAP, pw), (side, pw)]],
                 holes=[(pw / 2, pw / 2, AXLE_R), (2 * side + POST_GAP - pw / 2, pw / 2, AXLE_R)])
    posts.art = [_panel(pw + 6, 0.3, side - 0.3, pw - 0.3, WOOD), _panel(side + POST_GAP + 0.3, 0.3, 2 * side + POST_GAP - pw, pw - 0.3, WOOD)]
    # 3 体: 2 枚重ね。左が頭（前）、軸は前から torso_len、糸の穴は軸から string_arm 前。
    n = T + t
    torso = Part(3, "torso", "体", [(0, 0), (n, 0), (n, 2 * TW), (0, 2 * TW)], label_xy=(n - 6, 1), label="3",
                 valley=[((0, TW), (n, TW))],
                 holes=[(T, TW / 2, AXLE_R), (T, 1.5 * TW, AXLE_R), (T - p["string_arm"], TW / 2, STRING_R), (T - p["string_arm"], 1.5 * TW, STRING_R)])
    torso.art = _figure_art(0.6, 0.6, n * 0.92, TW - 1.2, False) + _figure_art(0.6, TW + 0.6, n * 0.92, TW - 1.2, True)
    # 4 止めの柱: 尾の下の縁が載る高さ（軸の高さ − 体の幅の半分）。下を糊代で折って台に貼る。
    sh = ph - TW / 2
    stop = Part(4, "stop", "止めの柱", [(0, 0), (sh + g, 0), (sh + g, pw), (0, pw)], label_xy=(1, 1.5), label="4",
                valley=[((sh, 0), (sh, pw))], glue=[[(sh, 0), (sh + g, 0), (sh + g, pw), (sh, pw)]])
    stop.art = [_panel(6, 0.3, sh - 0.3, pw - 0.3, WOOD)]
    # 5 臼: 丸めて筒にする。高さが頭の止め（stop_height）。杵は描かない（臼に当たって止まる所だけを作る）。
    c, hh = p["mortar_round"], p["stop_height"]
    mortar = Part(5, "mortar", "臼", [(0, 0), (c + g, 0), (c + g, hh), (0, hh)], label_xy=(1, 1), label="5",
                  valley=[((c, 0), (c, hh))], glue=[[(c, 0), (c + g, 0), (c + g, hh), (c, hh)]])
    mortar.art = [_panel(6, 0.3, c - 0.3, hh - 0.3, WOOD)] + [{"kind": "line", "pts": [(6.5, y), (c - 0.8, y)], "stroke": LINE, "sw": 0.3} for y in (2.5, hh - 2.5)]
    return [plank, posts, torso, stop, mortar]


def _ring(cx, cy, r, n=24):
    """位置の印の丸（閉じた点の線）の頂点。"""
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def _jaw_parts(p):
    head = _head_part(p)
    jl, jh, tl = p["jaw_len"], p["jaw_h"], p["tab_len"]
    n = jl + tl
    # 2 顎: 左が顎の先、軸は先から jaw_len、舌の端に糸の穴。
    jaw = Part(2, "jaw", "下顎", [(3, 0), (n, 0), (n, jh), (0, jh), (0, 3)], label_xy=(jl + 1.5, jh - 4.5), label="2",
               holes=[(jl, jh / 2, AXLE_R), (n - (HOLE_MARGIN + STRING_R + 0.5), jh / 2, STRING_R)])
    jaw.art = [{"kind": "poly", "pts": [(3.3, 0.4), (jl - 2, 0.4), (jl - 2, jh * 0.45), (0.6, jh * 0.45), (0.6, 3.2)], "fill": MOUTH},
               {"kind": "poly", "pts": [(0.6, jh * 0.55), (jl - 2, jh * 0.55), (jl - 2, jh - 0.4), (0.6, jh - 0.4)], "fill": FACE}]
    jaw.art += [{"kind": "line", "pts": [(x, 0.8), (x + 1.2, jh * 0.4), (x + 2.4, 0.8)], "stroke": "#ffffff", "sw": 0.3} for x in range(4, int(jl) - 5, 3)]
    # 位置の印（作る前のレビューの指摘から採った案 EP-0008、2026-11-06: 下顎に、糸を付ける所と重りを付ける所を示してほしい）。
    # 重りは顎の先の点の丸。真ん中は戻る力の式（lever）が粘土を置く所（軸から jaw_len − CLAY_IN 前・軸の高さ）と同じで、粘土は丸の裏に付ける。
    # 糸は舌の端の穴を点の丸で囲む（軸の穴と見分けるため）。丸は穴の縁から 1.2mm 離す（印が穴にかかると、切った時に消える）
    sx, sy, sr = jaw.holes[1]
    jaw.art += [{"kind": "mark", "pts": _ring(CLAY_IN, jh / 2, CLAY_MARK_R), "closed": True, "mark": "clay"},
                {"kind": "mark", "pts": _ring(sx, sy, sr + 1.2), "closed": True, "mark": "string"}]
    # 3 棒: 2 枚重ね。頭を上の端に貼り、糸は裏に沿わせて下の端から出す。
    sl, s = p["stick_len"], p["stick_w"]
    stick = Part(3, "stick", "棒", [(0, 0), (sl, 0), (sl, 2 * s), (0, 2 * s)], label_xy=(2, 1), label="3",
                 valley=[((0, s), (sl, s))], art=[_panel(6, 0.3, sl - 0.3, s - 0.3, STICK), _panel(0.3, s + 0.3, sl - 0.3, 2 * s - 0.3, STICK)])
    # 4 こぶ: 3 面を三角の柱に折り、端の糊代で閉じる。閉じた柱の 1 面（左の面）を頭に貼る。舌がここに当たって口の開きが止まる。
    # 前は 3 面だけで、最後の面を頭に貼る糊代にしていたので、柱の残りの辺を留める所が無く、柱にならなかった。
    f, gb = BUMP_FACE, BUMP_GLUE
    bump = Part(4, "bump", "こぶ", [(0, 0), (3 * f + gb, 0), (3 * f + gb, f), (0, f)], label_xy=(1, 1), label="4",
                valley=[((f, 0), (f, f)), ((2 * f, 0), (2 * f, f)), ((3 * f, 0), (3 * f, f))], glue=[[(3 * f, 0), (3 * f + gb, 0), (3 * f + gb, f), (3 * f, f)]])
    return [head, jaw, stick, bump]


def parts(p):
    return {"bow": _bow_parts, "jaw": _jaw_parts, "peck": _peck_parts}[p["kind"]](p)


def place(by_key, page, top, gap):
    x0 = page.x0
    if "plank" in by_key:
        plank, torso, mortar, posts, stop = (by_key[k] for k in ("plank", "torso", "mortar", "posts", "stop"))
        plank.x, plank.y = x0, top
        torso.x, torso.y = x0 + plank.width + gap, top
        mortar.x, mortar.y = torso.x, top + torso.height + gap
        y = top + max(plank.height, torso.height + gap + mortar.height) + gap
        posts.x, posts.y = x0, y
        stop.x, stop.y = x0 + posts.width + gap, y
        y += max(posts.height, stop.height) + gap
        # 文字の列は部品の下に頁の幅いっぱいで置く（10cm の物差しが入る幅が要る）。
        return y, page.x1 - x0, x0
    if "straw" in by_key:
        straw, cock, hen = by_key["straw"], by_key["cock"], by_key["hen"]
        straw.x, straw.y = x0, top
        cock.x, cock.y = x0 + straw.width + gap, top
        hen.x, hen.y = cock.x, top + cock.height + gap
        y = top + max(straw.height, cock.height + gap + hen.height) + gap
        return y, page.x1 - x0, x0
    stick, jaw, head, bump = (by_key[k] for k in ("stick", "jaw", "head", "bump"))
    stick.x, stick.y = x0, top
    jaw.x, jaw.y = x0 + stick.width + gap, top
    y = top + max(stick.height, jaw.height) + gap
    head.x, head.y = x0, y
    bump.x, bump.y = x0 + head.width + gap, y
    x = bump.x + bump.width + gap
    return y, page.x1 - x, x


def bom(p):
    paper = paper_name(gsm=p['paper_gsm'])
    why = "家庭のプリンタで刷って作るため"
    if p["kind"] == "bow":
        rows = [
            {"number": 1, "key": "plank", "name": "台", "qty": 1, "material": paper, "substituted": True, "original_guess": "木の板（図の色と形による推定）", "reason": why},
            {"number": 2, "key": "posts", "name": "柱", "qty": 1, "material": paper, "substituted": True, "original_guess": "木（同じ）", "reason": why},
            {"number": 3, "key": "torso", "name": "体", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明", "reason": why},
            {"number": 4, "key": "stop", "name": "止めの柱", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明（図に無い。戻りを止める所として足した）", "reason": why},
            {"number": 5, "key": "mortar", "name": "臼", "qty": 1, "material": paper, "substituted": True, "original_guess": "木（図の色と形による推定）", "reason": why},
        ]
        # 串は U の字の 2 本の柱を横切る。柱の間（POST_GAP）と柱の紙 2 枚と、両端の抜け止めの分。柱の幅は串の向きに関わらない
        # （前は柱の幅を 2 回足していて、串が 44mm と長すぎた）。
        axle_len = round(POST_GAP + 2 * PAPER_T + 2 * STOP_END)
        thread = p["post_height"] + 150
    elif p["kind"] == "peck":
        rows = [
            {"number": 1, "key": "straw", "name": "藁苞", "qty": 1, "material": paper, "substituted": True, "original_guess": "藁（図の形による推定）", "reason": why},
            {"number": 2, "key": "cock", "name": "奥の鶏", "qty": 1, "material": paper, "substituted": True, "original_guess": "張子か土（不明）", "reason": why},
            {"number": 3, "key": "hen", "name": "手前の鶏", "qty": 1, "material": paper, "substituted": True, "original_guess": "張子か土（不明）", "reason": why},
        ]
        axle_len = round(p["straw_w"] + 2 * PAPER_T + 2 * STOP_END)
        thread = p["straw_h"] + 150
    else:
        rows = [
            {"number": 1, "key": "head", "name": "頭", "qty": 1, "material": paper, "substituted": True, "original_guess": "張子か木（不明）", "reason": why},
            {"number": 2, "key": "jaw", "name": "下顎", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明", "reason": why},
            {"number": 3, "key": "stick", "name": "棒", "qty": 1, "material": paper, "substituted": True, "original_guess": "竹か木の棒（図の色による推定）", "reason": why},
            {"number": 4, "key": "bump", "name": "こぶ", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明（図に無い。口の開きを止める所として足した）", "reason": why},
        ]
        axle_len = round(2 * PAPER_T + 2 * STOP_END)  # 頭と顎の紙 2 枚と、両端の抜け止めの分
        thread = p["stick_len"] + 80
    rows += [
        {"number": 7, "key": "axle", "name": "軸", "qty": 2 if p["kind"] == "peck" else 1, "material": f"竹串（長さ約 {axle_len}mm に切り、先を落とす）", "substituted": True, "original_guess": "不明", "reason": "家にあり、穴に通しやすいため"},
        {"number": 8, "key": "weight", "name": "重り", "qty": 2 if p["kind"] == "peck" else 1, "material": f"油粘土 {p['weight_g']:g}g", "substituted": True, "original_guess": "不明", "reason": "量を変えて戻り方を試しやすいため"},
        {"number": 9, "key": "string", "name": "糸", "qty": 1, "material": f"木綿の糸（長さ約 {thread}mm）", "substituted": True, "original_guess": "糸（図に描かれている）", "reason": "家にあるため"},
    ]
    # 串の抜け止めの粘土。どの形も串の両端の外側にだけ付ける（peck の鶏は溝が幅の向きに押さえるので、苞の中に付けない）。重りと同じ粘土から取ると、振れる部品に付く量が式より減るので別の行にする。
    rows.append({"number": 10, "key": "stopclay", "name": "抜け止めの粘土", "qty": 2 if p["kind"] == "peck" else 1,
                 "material": f"油粘土 {STOP_CLAY_G:g}g（串の両端の外側に {STOP_CLAY_G / 2:g}g ずつ。重りとは別）",
                 "substituted": True, "original_guess": "不明", "reason": "串が抜けないようにするため"})
    return rows


def materials(p):
    by = {r["key"]: r for r in bom(p)}
    first = {"bow": "plank", "jaw": "head", "peck": "straw"}[p["kind"]]
    # 鶏は 2 羽なので、竹串と粘土は 2 つずつ（部品表の qty）。
    n = by["axle"]["qty"]
    if n > 1:
        out = [f"{by[first]['material']}を 1 枚", "のり、はさみ、定規", f"{by['axle']['material']}を {n} 本", f"{by['weight']['material']}を {n} つ（重り）", by["string"]["material"]]
    else:
        out = [f"{by[first]['material']}を 1 枚", "のり、はさみ、定規", by["axle"]["material"], f"{by['weight']['material']}（重り）", by["string"]["material"]]
    if "stopclay" in by:
        out.append(f"抜け止めに{by['stopclay']['material']}" + (f"を {by['stopclay']['qty']} 本分" if by["stopclay"]["qty"] > 1 else ""))
    return out


def steps(p):
    out = ["刷った物差しに定規を当て、10cm か確かめる", "部品を実線で切る。穴は竹串の先であける"]
    if p["kind"] == "bow":
        out += ["1 台を破線で谷折りして 2 枚に貼り合わせる。穴は重ねたまま通す",
                "3 体を破線で谷折りして貼り合わせる。軸の穴と糸の穴は重ねたまま通す",
                f"2 柱を U の字に折り、糊代を台の上の面の小さい四角（糸の穴から {p['string_arm']}mm 後ろ）に貼る",
                "体を柱の間に入れ、竹串を柱の穴と体の軸の穴に通す。串の両端の柱の外側に抜け止めの粘土を付ける（重りの粘土は使わない）",
                f"4 止めの柱の糊代を、台の後ろの細い四角（軸から {p['tail_len'] - CLAY_IN}mm 後ろ）に貼る",
                f"5 臼を丸めて筒にし、台の前の大きい四角（軸から {p['torso_len'] - 5}mm 前）に立てて貼る",
                f"尾の端に重りの粘土を {p['weight_g']:g}g 付ける。体が水平で止めの柱に載るか見る",
                f"糸を体の糸の穴に結び、台の穴から下へ通す。引くと約 {pull_gf(p):.0f}gf（見込み）で礼をして臼に当たる"]
    elif p["kind"] == "peck":
        out += ["1 藁苞の上の面の 2 本の溝を切る（カッターは大人がする）",
                "1 藁苞を破線で山折りし、糊代で貼って角の筒にする。両端は開けたまま",
                "2 奥の鶏と 3 手前の鶏の胸の小さい穴に糸を 1 本ずつ結ぶ",
                f"重りの粘土を {p['weight_g']:g}g ずつ丸め、鶏の外側の面（苞の縁に近い側）の尾に、玉の下が尾の先の高さより {CLAY_LIFT}mm 上になるように付ける",
                "鶏の脚の帯を溝に差し、糸は溝から苞の中へ入れて底の穴から出す",
                "苞の開いた端からのぞき、竹串を苞の横の穴・脚の帯の穴・反対の横の穴の順に通す。串の両端の苞の外側に抜け止めの粘土を付ける（重りの粘土は使わない。鶏は溝で横にずれない）",
                "尾の先が苞に載って鶏が起きているか見る",
                f"底から出た 2 本の糸を 1 本に結ぶ。引くと約 {pull_gf(p):.0f}gf（見込み）で 2 羽がついばむ"]
    else:
        out += ["3 棒を破線で谷折りして貼り合わせる",
                "1 頭の裏の下を 3 棒の上の端に貼る",
                "2 下顎を頭の口に重ね、短く切った竹串を両方の穴に通し、竹串の両端の外側（頭の裏と顎の表）に抜け止めの粘土を付ける（重りの粘土は使わない）",
                f"4 こぶを破線で三角に折り、糊代で閉じて柱にする。左の面を頭に刷った小さい四角（軸の穴から {p['jaw_h'] / 2 + p['stop_gap']:g}mm 上・{jaw_contact_back(p):.0f}mm 後ろ）に合わせて貼る",
                f"顎の先の点の丸（位置の印）の裏に、重りの粘土を {p['weight_g']:g}g 付ける。口が開いて舌がこぶに当たるか見る",
                f"糸を、舌の端の点の丸で囲んだ穴に結び、棒の裏に沿わせて下の端から出す。引くと約 {pull_gf(p):.0f}gf（見込み）で口が閉じる"]
    return out


RESULTS = ("動いた", "動かない")


def measures(p):
    """動くかの二択でなく、動き方を言葉か絵で予想する（虎の雛形と同じ形）。粘土の量は戻り方を分ける量なので書かせる。"""
    return {"predict": "糸を引いて離すと、どう動くと思いますか（言葉か絵で）", "rows": [[("付けた粘土の量", 40)]]}


def diagram(x, y, w, h, p):
    """横から見た仕組みの図。軸・振れる部品・止め・糸の向きを線で描く。"""
    if p["kind"] == "bow":
        span = p["plank_length"]
        s = min(w / span, h / (p["post_height"] + p["torso_w"] + 6))
        base = y + h - 2
        px = x + (span - p["tail_len"] - 5) * s
        py = base - p["post_height"] * s
        shapes = [{"kind": "line", "x1": x, "y1": base, "x2": x + span * s, "y2": base},
                  {"kind": "line", "x1": px, "y1": base, "x2": px, "y2": py},
                  {"kind": "rect", "x": px - p["torso_len"] * s, "y": py - p["torso_w"] * s / 2, "w": (p["torso_len"] + p["tail_len"]) * s, "h": p["torso_w"] * s},
                  {"kind": "rect", "x": px - p["torso_len"] * s, "y": base - p["stop_height"] * s, "w": 10 * s, "h": p["stop_height"] * s},
                  {"kind": "line", "x1": px - p["string_arm"] * s, "y1": py, "x2": px - p["string_arm"] * s, "y2": base + 2, "dash": "1,0.6"}]
        return shapes
    if p["kind"] == "peck":
        s = min(w / p["straw_len"], h / (p["straw_h"] + p["cock_h"] + 4))
        top = y + p["cock_h"] * s
        shapes = [{"kind": "rect", "x": x, "y": top, "w": p["straw_len"] * s, "h": p["straw_h"] * s}]
        for which in ("hen", "cock"):
            b = bird(p, which)
            cx = x + slot(p, which)["cx"] * s
            shapes.append({"kind": "rect", "x": cx - b["pivot"][0] * s, "y": top - b["H"] * s, "w": b["w"] * s, "h": b["H"] * s})
            sx = cx - p["peck_arm"] * b["k"] * s
            shapes.append({"kind": "line", "x1": sx, "y1": top - 4 * s, "x2": sx, "y2": y + h, "dash": "1,0.6"})
        return shapes
    s = min(w / (p["head_w"] + 4), h / (p["head_h"] + 20))
    px, py = x + jaw_pivot(p)[0] * s, y + jaw_pivot(p)[1] * s
    return [{"kind": "rect", "x": x, "y": y, "w": p["head_w"] * s, "h": p["head_h"] * s},
            {"kind": "line", "x1": px - p["jaw_len"] * s, "y1": py, "x2": px + p["tab_len"] * s, "y2": py},
            {"kind": "line", "x1": px + p["tab_len"] * s, "y1": py, "x2": px + p["tab_len"] * s, "y2": y + h, "dash": "1,0.6"}]
