"""雛形 wheel_cart: 竹串の軸に厚紙を重ねた車輪を付け、押すと転がる。『江都二色』の車の付く玩具を試す。

乗り物の形は玩具ごとに違うので、FORM（ride）の値で描き分ける。
- rat: 大黒の鼠車（推定・19 コマ左）。鼠を箱の胴にし、前と後ろの 2 本の軸に車輪を 4 つ。人形は平らな切り抜きを上に立てる。
  絵では鼠は車の付いた板に乗るが、板と胴を 1 つの箱にまとめた（紙で作る部品を減らすため。箱の側面の下の帯を板の色にした）。
- stick: 春駒（31 コマ右）。馬の頭の切り抜きを割り箸の上に貼り、下の端の紙の二股に車輪を 1 つ。手で持って押す。
- mallet: ぶりぶり（推定・9 コマ左）。八角の槌の頭の両端に小さな車輪を付け、割り箸の柄で引くか転がす。
  9 コマの絵は、菊の模様の丸い面を両端に持つ筒の頭に柄が付いた槌の形で、絵だけでは丸い面が車輪か飾りかは決まらない。
  江戸の振々毬杖（ぶりぶりぎっちょう）は槌の頭に小さな車輪を付けて引いた、という一般の説明に拠って車輪と読んだ（推定。原典は未確認）。
  頭は絵では丸い筒だが、紙で折りやすい八角柱にした（振々毬杖の頭を八角に作る例があるという説明にも合う。これも未確認）。

寸法は手元の複写の図の比と、A4 に収まる事から出した。どの値も実物では未確認。Claude が変えてよいのは RANGES の名前の値だけ。
"""
import math

from shapely.geometry import LineString, Polygon, box

from ..paper_words import paper_name  # 紙の書き方は 4 つの名前だけ（制作者の指示 2026-11-05）
from ..model import Failure, Part
from ..pivot_model import paper_mass

ID = "wheel_cart"
DEFAULTS = {
    "ride": "rat",
    # 車輪と軸（両方の形で使う）
    "wheel_r": 12, "wheel_layers": 3, "axle_height": 7,
    # 鼠車の胴（箱）。軸の高さ axle_height は胴の底から測る
    "body_length": 70, "body_width": 30, "body_height": 30, "glue": 8,
    "inset_front": 12, "inset_rear": 12, "wheel_gap": 2,
    "figure_w": 30, "figure_h": 42, "rider_at": 0.5,
    # 春駒。軸の高さ axle_height は二股の腕の先から測る
    "head_w": 56, "head_h": 31, "cloth_w": 44, "cloth_h": 28,
    "fork_width": 12, "fork_inner": 8, "fork_arm": 34, "stick_t": 4.5, "stick_in": 4,
    # ぶりぶり。head_r は八角の頭の外接円の半径（角まで）、handle_in は柄を頭に差し込む深さ。車輪と頭のすき間は wheel_gap
    "head_r": 9, "head_len": 36, "handle_len": 180, "handle_in": 3,
    # 紙と厚紙の見込み。実物の紙を量ったら置き換える。厚紙は空き箱の板紙を見込む。
    "paper_gsm": 150, "paper_thickness": 0.15, "card_gsm": 350, "card_thickness": 0.4,
}
RANGES = {
    "wheel_r": (6, 28), "wheel_layers": (1, 6), "axle_height": (2, 30),
    "body_length": (40, 100), "body_width": (20, 45), "body_height": (20, 45), "glue": (5, 12),
    "inset_front": (2, 50), "inset_rear": (2, 50), "wheel_gap": (0, 8),
    "figure_w": (15, 40), "figure_h": (20, 60), "rider_at": (0, 1),
    "head_w": (40, 64), "head_h": (20, 40), "cloth_w": (30, 50), "cloth_h": (20, 36),
    "fork_width": (6, 20), "fork_inner": (3, 20), "fork_arm": (15, 50), "stick_t": (3, 7), "stick_in": (0, 20),
    # handle_in の下限 2mm: 0 だと組み方が「0mm 差し込む」と言い、柄が糊だけで穴に付かず抜ける（実物では未確認の見込み）
    "head_r": (6, 20), "head_len": (20, 60), "handle_len": (80, 220), "handle_in": (2, 10),
    "paper_gsm": (40, 400), "paper_thickness": (0.05, 0.6), "card_gsm": (150, 800), "card_thickness": (0.2, 1.5),
}
RIDES = ("rat", "stick", "mallet")
# 刷る形を決める寸法（乗り物の形）。玩具の違いそのものなので、寸法を直に渡す入口（python -m omochae --params）では必ず書かせる。
FORM = "ride"
FORMS = RIDES  # 刷る形の値の一覧（作りうる部品を数える時に使う）
# 既定の出典（data/sources/ の名前）。--source を書かない時に、雛形と合わない出典の印を刷らないため。
SOURCE = "NDL-1187053-R0000019-L-wheel_cart"
# 形ごとの出典。3 つの形は別々のコマの別の玩具なので、形と出典を組にする（合わない組は compose が F1.source で落とす）。
SOURCES = {"rat": SOURCE, "stick": "NDL-1187053-R0000031-R-wheel_cart", "mallet": "NDL-1187053-R0000009-L-wheel_cart"}
TITLES = {"rat": "鼠に車を付けて転がす", "stick": "棒の先の車で転がす", "mallet": "槌の頭の車で転がす"}

HOLE_MARGIN = 4  # 穴の中心から紙の端・折り目までの見込み（虎と同じ値）。これより狭いと裂けやすい
MIN_GROUND = 2  # 胴の底（二股の腕の先）と床のすき間。紙の胴は撓むので 0 では擦る見込み
MIN_SIDE_GAP = 1.5  # 車輪と胴の側面（二股の内側・割り箸の先）のすき間。重ねた厚紙の車輪は少し首を振るので余裕を取る
TIP_MARGIN = 2  # 重心が前後の車輪の接地点から内側にある幅。押した時の傾きで越えないための余裕
STOP_MARK_MIN = 0.5  # 春駒の割り箸を止める印を刷る下限（差し込む深さ）。これ以下は印が頭の折り目と重なるので刷らず、折り目で止める
AXLE_HOLE_R = 2.0  # 回る軸の穴。竹串（太さ約 3mm）が回るように緩くする
WHEEL_HOLE_R = 1.3  # 車輪の穴。竹串の先であけ、軸に貼って留める
SKEWER_D = 3.0  # 竹串の太さの見込み
BAMBOO_DENSITY = 0.7e-3  # g/mm³。竹串の密度の見込み（量っていない）
PAPER, LINE, BOARD, WOOD, DARK = "#efe9dc", "#6b6458", "#c8a46a", "#d9bf86", "#4a3a2a"
WHEEL, WHEEL_RIM, PINK, ROBE, CAP, SKIN, RED = "#a7703f", "#5a3a22", "#c98a7a", "#d8c78c", "#c9b88a", "#e3b9a0", "#9a4a3a"


def title(p):
    return TITLES[p["ride"]]


def spec():
    return {"template_id": ID, "defaults": DEFAULTS, "ranges": RANGES, "ride": RIDES}


def check_range(p):
    out = []
    for k, v in p.items():
        if k == "ride":
            if v not in RIDES:
                out.append(Failure("F5.range", k, f"{v} は {RIDES} のどれでもない"))
        elif k not in RANGES:
            out.append(Failure("F5.range", k, "知らない寸法の名前"))
        elif not isinstance(v, (int, float)) or isinstance(v, bool) or not RANGES[k][0] <= v <= RANGES[k][1]:
            out.append(Failure("F5.range", k, f"{v} は範囲 {RANGES[k]} の外"))
        elif k == "wheel_layers" and not isinstance(v, int):
            # 2.0 のような小数の形も落とす。通すと部品表と組み方に「4.0 枚」と刷る
            out.append(Failure("F5.range", k, f"{v} は枚数なので整数（小数点を付けない）"))
    return out


def wheel_thickness(p):
    """車輪 1 つの厚み（mm）。刷った面 1 枚と、空き箱の厚紙の芯（枚数 - 1 枚）を重ねる。糊の厚みは入れない。"""
    return p["paper_thickness"] + (p["wheel_layers"] - 1) * p["card_thickness"]


def wheel_mass(p):
    """車輪 1 つの質量（g）。面積 × 面密度の見込み。穴の分は引かない（桁を見るため）。"""
    area = math.pi * p["wheel_r"] ** 2
    return paper_mass(area, p["paper_gsm"]) + (p["wheel_layers"] - 1) * paper_mass(area, p["card_gsm"])


def axle_length(p):
    """鼠車の軸の竹串 1 本の長さ（mm）。胴の幅 + 両側の すき間・車輪 + 先に 5mm ずつ残す。"""
    return p["body_width"] + 2 * (p["wheel_gap"] + wheel_thickness(p)) + 10


def body_area(p):
    L, W, H, g = p["body_length"], p["body_width"], p["body_height"], p["glue"]
    return 2 * L * W + 2 * L * H + 2 * W * H + g * (L + 4 * H)


def cart_com_x(p):
    """鼠車の前後の重心（胴の前の端から mm）。

    前提: 胴（紙の箱）は前後の真ん中、人形は rider_at の位置、車輪 2 つと竹串 1 本は各軸の上に質量があるとする。
    糊・尾・紙の撓みは入れない。質量は面積 × 面密度の見込みで、実物では量っていない。
    """
    L = p["body_length"]
    skewer = BAMBOO_DENSITY * math.pi * (SKEWER_D / 2) ** 2 * axle_length(p)
    per_axle = 2 * wheel_mass(p) + skewer
    pts = [(paper_mass(body_area(p), p["paper_gsm"]), L / 2),
           (paper_mass(p["figure_w"] * p["figure_h"], p["paper_gsm"]), p["rider_at"] * L),
           (per_axle, p["inset_front"]), (per_axle, L - p["inset_rear"])]
    total = sum(m for m, _ in pts)
    return sum(m * x for m, x in pts) / total


def octagon(p):
    """八角の頭の寸法: (面の幅, 内接円の半径)。head_r は外接円の半径。"""
    r = p["head_r"]
    return 2 * r * math.sin(math.pi / 8), r * math.cos(math.pi / 8)


def mallet_axle_length(p):
    """ぶりぶりの軸の竹串の長さ（mm）。頭の長さ + 両側の すき間・車輪 + 先に 5mm ずつ残す。"""
    return p["head_len"] + 2 * (p["wheel_gap"] + wheel_thickness(p)) + 10


def _check_mallet(p, fail):
    """ぶりぶりの F5.wheel。軸は頭の芯を通るので、軸の高さは車輪の半径そのもので、axle_height は使わない。

    1. 床: 頭は柄に付いて回らないが、柄を持ち上げる角度で八角のどの角も下に来うるので、外接円の半径 head_r で見る。
    2. 側面: 車輪と頭の端の蓋のすき間 wheel_gap。柄の先は軸（竹串）と MIN_SIDE_GAP 離す（当たると軸が回らない）。
    3. 穴: 蓋の軸の穴から蓋の縁まで（内接円の半径）HOLE_MARGIN 以上。柄の穴は面の幅の中に、折り目から 1mm 以上離す。
    4. 重心: 回る物は車輪と軸だけで、回らない頭と柄の重心は、軸を通る真ん中の頭に対して必ず柄の側に来る。
       置くと柄の先が床に付き、車輪の接地点と柄の先の間に重心が入るので、寸法で倒れる事は無い（式にしない理由）。
    """
    R, r = p["wheel_r"], p["head_r"]
    side, apo = octagon(p)
    if R - r < MIN_GROUND:
        fail("車輪", f"車輪の半径 {R}mm が頭の角まで {r}mm より {MIN_GROUND}mm 以上大きくなく、頭が床を擦る")
    if p["wheel_gap"] < MIN_SIDE_GAP:
        fail("車輪", f"車輪と頭の蓋のすき間 {p['wheel_gap']}mm が {MIN_SIDE_GAP}mm より狭く、擦る")
    room = apo - p["handle_in"] - SKEWER_D / 2
    if room < MIN_SIDE_GAP:
        fail("柄", f"柄の先と軸のすき間 {room:.1f}mm が {MIN_SIDE_GAP}mm より狭く、軸が回らない")
    if apo < HOLE_MARGIN:
        fail("軸の穴", f"蓋の軸の穴から蓋の縁まで {apo:.1f}mm で、裂けやすい")
    if side < p["stick_t"] + 2:
        fail("柄", f"割り箸（太さ {p['stick_t']}mm）を通す穴が頭の面（幅 {side:.1f}mm）に収まらない")


def check_physics(p):
    """F5.wheel: 転がる形が成り立たない寸法を落とす。見る事は 4 つで、どれも紙の厚み・すき間・重心の量だけの式。

    1. 床: 車輪の半径が、軸から胴の底（春駒は二股の腕の先）までの高さより MIN_GROUND 以上大きい。小さいと胴が床を擦る。
       春駒は棒を傾けて押すが、腕の先が一番低くなる真っ直ぐ立てた時で見る（安全側）。
    2. 側面: 車輪が胴の側面（二股の内側、割り箸の先）と MIN_SIDE_GAP 以上離れる。鼠車は前と後ろの車輪どうしも離れる。
       車輪の厚みは wheel_thickness（紙と厚紙を重ねた厚み、糊は入れない）。
    3. 穴: 軸の穴の中心から紙の端・折り目まで HOLE_MARGIN 以上。狭いと押した力で裂ける。
    4. 重心: 鼠車は前後の重心（cart_com_x）が、前と後ろの車輪の接地点（軸の真下）の間に TIP_MARGIN 以上入る。外だと前か後ろへ倒れる。
       春駒は手で持って押す物で、手が支えの点になるので、置いて倒れるかは見ない。
    どの見込みも実物の紙では確かめていない。
    """
    out = []
    R, a = p["wheel_r"], p["axle_height"]
    fail = lambda where, msg: out.append(Failure("F5.wheel", where, msg))
    if p["ride"] == "mallet":
        _check_mallet(p, fail)
        return out
    t = wheel_thickness(p)
    if R - a < MIN_GROUND:
        under = "胴の底" if p["ride"] == "rat" else "二股の腕の先"
        fail("車輪", f"車輪の半径 {R}mm が軸の高さ {a}mm より {MIN_GROUND}mm 以上大きくなく、{under}が床を擦る")
    if a < HOLE_MARGIN:
        fail("軸の穴", f"軸の穴から{'胴の底の折り目' if p['ride'] == 'rat' else '腕の先'}まで {a}mm で、裂けやすい")
    if p["ride"] == "rat":
        L, H = p["body_length"], p["body_height"]
        if p["wheel_gap"] < MIN_SIDE_GAP:
            fail("車輪", f"車輪と胴の側面のすき間 {p['wheel_gap']}mm が {MIN_SIDE_GAP}mm より狭く、擦る")
        between = L - p["inset_front"] - p["inset_rear"]
        if between < 2 * R + MIN_SIDE_GAP:
            fail("車輪", f"前と後ろの軸の間 {between}mm に、車輪 2 つ（{2 * R}mm）とすき間が入らない")
        if H - a < HOLE_MARGIN:
            fail("軸の穴", f"軸の穴から胴の上の縁まで {H - a}mm で、裂けやすい")
        for name in ("inset_front", "inset_rear"):
            if p[name] < HOLE_MARGIN:
                fail("軸の穴", f"軸の穴から{'前' if name == 'inset_front' else '後ろ'}の壁の折り目まで {p[name]}mm で、裂けやすい")
        x = cart_com_x(p)
        lo, hi = p["inset_front"] + TIP_MARGIN, L - p["inset_rear"] - TIP_MARGIN
        if not lo <= x <= hi:
            fail("重心", f"重心（前から {x:.1f}mm）が車輪の接地点の間（{lo:g}〜{hi:g}mm）に無く、倒れる")
        # 人形の台は胴の上の面に貼るので、上の面の前後から出ると貼れない。
        half = p["figure_w"] * 0.3
        if not half <= p["rider_at"] * L <= L - half:
            fail("人形", "人形の台が胴の上の面から前か後ろへ出る")
    else:
        fi, A = p["fork_inner"], p["fork_arm"]
        if fi < t + 2 * MIN_SIDE_GAP:
            fail("車輪", f"二股の内の幅 {fi}mm に、車輪（厚み {t:.2f}mm）と両側のすき間 {MIN_SIDE_GAP}mm が入らない")
        if fi < p["stick_t"] + 1 or p["fork_width"] < p["stick_t"] + 2:
            fail("二股", f"割り箸（太さ {p['stick_t']}mm）を通す穴が二股の頭に収まらない")
        room = A - p["stick_in"] - a - R
        if room < MIN_SIDE_GAP:
            fail("車輪", f"車輪の上の端と割り箸の先のすき間 {room:.1f}mm が {MIN_SIDE_GAP}mm より狭く、擦る")
        if p["fork_width"] / 2 < HOLE_MARGIN:
            fail("軸の穴", f"軸の穴から二股の腕の縁まで {p['fork_width'] / 2}mm で、裂けやすい")
    return out


# ---- 絵。出典の図（19 コマ左・31 コマ右、横 800px に縮めた物）を見て手で取った点。絵の画素は使っていない。----
# 鼠（横から、左が鼻）。19 コマの白い鼠の輪郭。
_RAT = [(118, 1022), (135, 995), (170, 960), (205, 930), (245, 915), (300, 895), (380, 880), (470, 875), (560, 880), (615, 905), (640, 950),
        (640, 1000), (610, 1040), (540, 1065), (420, 1070), (300, 1075), (230, 1070), (180, 1050), (140, 1040)]
_RAT_EAR = [(238, 925), (282, 922), (290, 958), (256, 966)]
_RAT_EYE = [(165, 978), (177, 978), (180, 988), (170, 994), (162, 988)]
_RAT_LINES = [[(126, 1030), (162, 1032)], [(225, 1045), (238, 1072)], [(300, 1052), (312, 1074)], [(520, 1030), (560, 1062)]]
# 大黒の人形（座った形、頭巾）。下の端は台に貼るので平らにした。
_RIDER = [(312, 628), (318, 600), (360, 585), (420, 590), (455, 612), (460, 640), (432, 662), (470, 690), (505, 720), (502, 800), (472, 832),
          (495, 868), (496, 920), (490, 960), (250, 960), (240, 880), (245, 830), (238, 760), (236, 720), (258, 672), (300, 660), (322, 655)]
_RIDER_TAB_AT = 14  # _RIDER の 13 番目（右下）と 14 番目（左下）の間に台に貼る耳を入れる
_CAP = [(312, 628), (318, 600), (360, 585), (420, 590), (455, 612), (460, 640), (430, 642), (380, 634), (340, 632)]
_FACE = [(330, 634), (428, 642), (432, 662), (415, 690), (380, 700), (345, 690), (330, 665)]
_ROBE = [(258, 690), (330, 690), (380, 702), (432, 690), (500, 722), (500, 800), (470, 830), (440, 840), (330, 845), (250, 850), (240, 770)]
_LEGS = [(250, 852), (330, 847), (440, 842), (472, 834), (494, 868), (494, 920), (488, 958), (252, 958), (242, 880)]
_FOOT = [(420, 936), (480, 930), (486, 956), (424, 956)]
_RIDER_LINES = [[(358, 664), (372, 667)], [(394, 667), (408, 664)], [(348, 694), (412, 692)], [(300, 760), (310, 840)], [(420, 740), (430, 830)]]
# 春駒の頭（左が鼻）。31 コマの白い斑の馬。
_HEAD = [(28, 795), (40, 760), (60, 735), (85, 700), (100, 682), (112, 700), (125, 685), (135, 700), (150, 710), (200, 715), (260, 740),
         (320, 790), (330, 820), (250, 840), (200, 850), (150, 835), (110, 830), (70, 830), (40, 828), (25, 815)]
_MANE = [(88, 702), (100, 686), (112, 702), (125, 689), (134, 702), (140, 730), (120, 745), (100, 730)]
_SPOTS = [[(155, 725), (190, 730), (205, 760), (180, 775), (160, 760)], [(235, 775), (265, 780), (270, 805), (245, 815), (230, 800)]]
_HEAD_LINES = [[(68, 748), (90, 742)], [(45, 790), (80, 772), (112, 786)], [(42, 810), (100, 820), (150, 836)]]
_CLOTH = [(240, 820), (330, 810), (480, 905), (500, 945), (420, 960), (330, 975), (265, 950)]
_CLOTH_LINES = [[(300, 862), (318, 945)], [(360, 880), (382, 955)], [(420, 905), (440, 945)]]


def _fit(pts, bbox, x, y, w, h, flip_x=False, flip_y=False):
    """手で取った点を、箱 (x, y, w, h) に収める。bbox は点を取った範囲 (x0, y0, x1, y1)。"""
    x0, y0, x1, y1 = bbox
    out = []
    for a, b in pts:
        u, v = (a - x0) / (x1 - x0), (b - y0) / (y1 - y0)
        out.append((x + (1 - u if flip_x else u) * w, y + (1 - v if flip_y else v) * h))
    return out


def _clip(item, region):
    """絵を region（shapely の面）の中に切り詰める。折り線・糊代・外形をまたがないため。切り詰めて消えた物は返さない。"""
    if item["kind"] == "poly":
        g = Polygon(item["pts"]).buffer(0).intersection(region)
        geoms = [x for x in getattr(g, "geoms", [g]) if x.geom_type == "Polygon" and x.area > 0.05]
        return [dict(item, pts=list(x.exterior.coords)[:-1]) for x in geoms]
    g = LineString(item["pts"]).intersection(region)
    geoms = [x for x in getattr(g, "geoms", [g]) if x.geom_type == "LineString" and x.length > 0.2]
    return [dict(item, pts=list(x.coords)) for x in geoms]


def _art(items, region):
    out = []
    for it in items:
        out += _clip(it, region)
    return out


def _poly(pts, fill, stroke=None, sw=0.0):
    d = {"kind": "poly", "pts": pts, "fill": fill}
    if stroke:
        d.update(stroke=stroke, sw=sw)
    return d


def _line(pts, stroke, sw):
    return {"kind": "line", "pts": pts, "stroke": stroke, "sw": sw}


def _mark(pts, tag, closed=False):
    """組み立ての位置の印。色と線の形は描く所（render）が決める（赤茶の点の線）。雛形が濃い実線で描くと切る線と、破線で描くと谷折りと
    取り違えるので、ここでは色も太さも持たない。tag は試験が印を見分けるための名。"""
    return {"kind": "mark", "pts": pts, "closed": closed, "mark": tag}


def _rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def _circle(cx, cy, r, n=40):
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def _wheel(number, key, p):
    """車輪の刷る面 1 枚。芯の厚紙はこの面を型にして切る。絵の車は茶色の円に濃い縁と点の芯。"""
    R = p["wheel_r"]
    outline = _circle(R, R, R)
    inner = Polygon(outline).buffer(-0.3)
    art = [_poly(list(inner.exterior.coords)[:-1], WHEEL),
           _line(_circle(R, R, R - 1.2) + [_circle(R, R, R - 1.2)[0]], WHEEL_RIM, 0.6),
           _poly(_circle(R, R, max(2.0, R * 0.28), 16), WHEEL_RIM)]
    return Part(number, key, "車輪", outline, label_xy=(R - 0.8, 1.5), label=str(number), holes=[(R, R, WHEEL_HOLE_R)], art=art)


def _rat_body(p):
    """鼠の胴の箱。展開図は虎の胴（pivot_counterweight）と同じ十字形: 上の面・側面・底・側面を縦に並べ、底の左右に前と後ろの壁。
    前は左（x = H の側）。軸の穴は 2 つの側面の同じ x に、底から axle_height の高さにあける。
    """
    L, W, H, g = p["body_length"], p["body_width"], p["body_height"], p["glue"]
    top0, top1 = g, g + W
    b0, b1 = top1 + H, top1 + H + W
    bottom = b1 + H
    pts = [(H + 2, 0), (H + L - 2, 0), (H + L, g), (H + L, b0 - g), (H + L + H - 2, b0 - g), (H + L + H, b0), (H + L + H, b1),
           (H + L + H - 2, b1 + g), (H + L, b1 + g), (H + L, bottom), (H, bottom), (H, b1 + g), (2, b1 + g), (0, b1), (0, b0),
           (2, b0 - g), (H, b0 - g), (H, g)]
    body = Part(1, "body", "胴（鼠）", pts, label_xy=(H + 2, top0 + 2), label="1 胴")
    # 胴は色の面（鼠の絵・板の色・顔・人形を貼る印）を外にして箱にするので、刷った面から見て山折り（下の側面の絵も「外から見て」描いてある）。
    # 谷折り（凡例の、刷った面がへこむ向き）のままだと色の面が箱の内に入った。制作者の決定（2026-11-06「今のうちに4つ直す」）で、
    # 同じ十字形の虎の胴と同じ線で直した。線は破線で刷るので、刷る線の形が山折りの形に変わる
    body.mountain = [((H, top0), (H + L, top0)), ((H, top1), (H + L, top1)), ((H, b0), (H + L, b0)), ((H, b1), (H + L, b1)), ((H, b0), (H, b1)),
                     ((H + L, b0), (H + L, b1)), ((0, b0), (H, b0)), ((0, b1), (H, b1)), ((H + L, b0), (H + L + H, b0)), ((H + L, b1), (H + L + H, b1))]
    body.glue = [[(H + 2, 0), (H + L - 2, 0), (H + L, g), (H, g)], [(2, b0 - g), (H, b0 - g), (H, b0), (0, b0)], [(0, b1), (H, b1), (H, b1 + g), (2, b1 + g)],
                 [(H + L, b0 - g), (H + L + H - 2, b0 - g), (H + L + H, b0), (H + L, b0)], [(H + L, b1), (H + L + H, b1), (H + L + H - 2, b1 + g), (H + L, b1 + g)]]
    e = 0.25  # 絵を折り線から離す幅。check_art は線の太さまで見るので、面の縁を少し内へ
    # 人形の耳を貼る位置の印。重心の式（cart_com_x）は人形が rider_at * L にあるとして数えるので、その位置を紙に刷る。
    # 耳は人形の幅の 0.2〜0.8（幅 0.6 倍）、奥行き 7mm。上の面の幅の真ん中に置く。
    rx, half, my = H + p["rider_at"] * L, p["figure_w"] * 0.3, (top0 + top1) / 2
    art = [_poly(_rect(H + e, top0 + e, H + L - e, top1 - e), PAPER),  # 上の面（人形を貼る）
           _mark(_rect(rx - half, my - 3.5, rx + half, my + 3.5), "rider", closed=True),
           _poly(_rect(H + e, b0 + e, H + L - e, b1 - e), BOARD),  # 底は板の色
           _poly(_rect(H + L + e, b0 + e, H + L + H - e, b1 - e), PAPER)]  # 後ろの壁（尾を貼る）
    # 前の壁は鼠の顔を正面から。壁は x = H の折り目で底から立つので、x の小さい方が上。
    front = box(e, b0 + e, H - e, b1 - e)
    cy = (b0 + b1) / 2
    face = [_poly(_rect(e, b0 + e, H - e, b1 - e), PAPER),
            _poly(_circle(H * 0.22, cy - W * 0.3, min(H, W) * 0.12, 16), PINK),
            _poly(_circle(H * 0.22, cy + W * 0.3, min(H, W) * 0.12, 16), PINK),
            _poly(_circle(H * 0.45, cy - W * 0.15, 1.0, 10), DARK), _poly(_circle(H * 0.45, cy + W * 0.15, 1.0, 10), DARK),
            _poly(_circle(H * 0.72, cy, 1.4, 10), PINK)]
    art += _art(face, front)
    # 側面: 下の帯を板の色にし（絵の板）、その上に鼠を横から描く。2 つ目の側面は上下だけ裏返す（外から見て鼻が前に来る）。
    bh = max(3.0, H * 0.22)
    for wall_top, wall_bottom, flip in ((top1, b0, False), (b1, bottom, True)):
        region = box(H + e, wall_top + e, H + L - e, wall_bottom - e)
        if flip:
            band = _rect(H + e, wall_top + e, H + L - e, wall_top + bh)
            rat_box = (H + 1, wall_top + bh, L - 2, wall_bottom - 1 - wall_top - bh)
        else:
            band = _rect(H + e, wall_bottom - bh, H + L - e, wall_bottom - e)
            rat_box = (H + 1, wall_top + 1, L - 2, wall_bottom - bh - wall_top - 1)
        fit = lambda ps: _fit(ps, (118, 875, 640, 1075), *rat_box, flip_y=flip)
        side = [_poly(band, BOARD), _poly(fit(_RAT), PAPER, LINE, 0.3), _poly(fit(_RAT_EAR), PINK), _poly(fit(_RAT_EYE), DARK)]
        side += [_line(fit(x), LINE, 0.35) for x in _RAT_LINES]
        art += _art(side, region)
    body.art = art
    a = p["axle_height"]
    xf, xr = H + p["inset_front"], H + L - p["inset_rear"]
    body.holes = [(xf, b0 - a, AXLE_HOLE_R), (xr, b0 - a, AXLE_HOLE_R), (xf, b1 + a, AXLE_HOLE_R), (xr, b1 + a, AXLE_HOLE_R)]
    return body


def _rider(p):
    """人形。下に台へ貼る耳を付け、耳の付け根で山折りして胴の上の面に立てる。

    山折り（刷った面の裏へ折る）なので、耳は人形の後ろへ折れ、耳に刷った糊の印が胴の上の面を向く。前の谷折りでは、耳が絵の面の前へ
    出て、糊の印が上を向いた。制作者の決定（2026-11-06「今のうちに4つ直す」）で、ほかの色の面の部品と一緒に直した。
    """
    fw, fh, tab = p["figure_w"], p["figure_h"], 7
    bb = (236, 585, 505, 960)
    fit = lambda ps: _fit(ps, bb, 0, 0, fw, fh)
    sil = fit(_RIDER)
    t0, t1 = fw * 0.2, fw * 0.8
    tab_pts = [(t1, fh), (t1 - 1, fh + tab), (t0 + 1, fh + tab), (t0, fh)]
    outline = sil[:_RIDER_TAB_AT] + tab_pts + sil[_RIDER_TAB_AT:]
    region = Polygon(sil).buffer(-0.15).intersection(box(-1, -1, fw + 1, fh - 0.35))
    art = [_poly(fit(_LEGS), PINK), _poly(fit(_ROBE), ROBE), _poly(fit(_CAP), CAP), _poly(fit(_FACE), SKIN), _poly(fit(_FOOT), DARK)]
    art += [_line(fit(x), DARK, 0.3) for x in _RIDER_LINES]
    return Part(2, "rider", "人形", outline, label_xy=(fw * 0.42, fh * 0.42), label="2", mountain=[((t0, fh), (t1, fh))],
                glue=[tab_pts], art=_art(art, region))


def _head(number, key, name, p, flip):
    w, h = p["head_w"], p["head_h"]
    fit = lambda ps: _fit(ps, (25, 682, 330, 850), 0, 0, w, h, flip_x=flip)
    outline = fit(_HEAD)
    # 線は太さの半分だけ外へ出て刷られるので、線の太さより深く内へ切り詰める
    region = Polygon(outline).buffer(-0.3)
    art = [_poly(outline, PAPER, LINE, 0.25), _poly(fit(_MANE), DARK)] + [_poly(fit(s), DARK) for s in _SPOTS]
    art += [_line(fit(x), RED if i else DARK, 0.4) for i, x in enumerate(_HEAD_LINES)]
    # 輪郭線の付いた面は外形の上に乗るので切り詰めない（外へ出た半分は切り落とす。虎の頭と同じ）
    art = art[:1] + _art(art[1:], region)
    return Part(number, key, name, outline, label_xy=(w * 0.55, h * 0.55), label=str(number), art=art)


def _cloth(p):
    w, h = p["cloth_w"], p["cloth_h"]
    fit = lambda ps: _fit(ps, (240, 810, 500, 975), 0, 0, w, h)
    outline = fit(_CLOTH)
    region = Polygon(outline).buffer(-0.2)
    art = _art([_poly(outline, PINK)] + [_line(fit(x), RED, 0.35) for x in _CLOTH_LINES], region)
    return Part(3, "cloth", "布の胴", outline, label_xy=(w * 0.45, h * 0.45), label="3", art=art)


def _fork(p):
    """車輪を挟む紙の二股。縦に 腕・頭・腕 と並べ、2 本の折り目で コ の字に折る。頭の四角い穴に割り箸を通して貼る。
    腕の先（y = 0 と y = 最下）から axle_height の所に軸の穴。
    """
    fw, fi, A, st = p["fork_width"], p["fork_inner"], p["fork_arm"], p["stick_t"]
    total = 2 * A + fi
    a = p["axle_height"]
    e = 0.25
    art = [_poly(_rect(e, e, fw - e, A - e), WOOD), _poly(_rect(e, A + fi + e, fw - e, total - e), WOOD)]
    # 割り箸の先を止める印。車輪と割り箸の先のすき間の式は差し込む深さ stick_in で数えるので、両方の腕の、頭の折り目から
    # stick_in の所に位置の印を刷る。0 に近いと折り目と重なるので刷らない（折り目そのものが印になる）。
    d = p["stick_in"]
    if d > STOP_MARK_MIN:
        art += [_mark([(0.3, A - d), (fw - 0.3, A - d)], "stop"), _mark([(0.3, A + fi + d), (fw - 0.3, A + fi + d)], "stop")]
    return Part(4, "fork", "二股", _rect(0, 0, fw, total), label_xy=(1, A * 0.4), label="4",
                valley=[((0, A), (fw, A)), ((0, A + fi), (fw, A + fi))],
                holes=[(fw / 2, a, AXLE_HOLE_R), (fw / 2, total - a, AXLE_HOLE_R)],
                cuts=[((fw - st) / 2, A + (fi - st) / 2, st, st)], art=art)


def _tail(p):
    art = [_poly(_rect(0.2, 0.2, 5.8, 49.8), PINK)]
    return Part(3, "tail", "尾", _rect(0, 0, 6, 50), label_xy=(1, 1.5), label="3", art=art)


def _drum(p):
    """ぶりぶりの頭の胴。八角柱の 8 面を横に並べ、右の端に糊代。真ん中の面（4 面目）に柄を通す四角い穴。
    絵の頭は木の色に黒い帯が 2 本なので、各面の端寄りに黒い帯を描く（折り目をまたがないよう面ごとに分ける）。
    """
    s, _ = octagon(p)
    L, g, e = p["head_len"], 6, 0.25
    W = 8 * s
    outline = [(0, 0), (W, 0), (W + g, 1), (W + g, L - 1), (W, L), (0, L)]
    art = []
    for i in range(8):
        x0, x1 = i * s + e, (i + 1) * s - e
        art.append(_poly(_rect(x0, e, x1, L - e), WOOD))
        for y0, y1 in ((0.12, 0.17), (0.21, 0.26)):
            art.append(_poly(_rect(x0, L * y0, x1, L * y1), DARK))
    st = p["stick_t"]
    # 頭は色の面（木の色と黒い帯）を外にして八角の筒にするので、刷った面から見て山折り。谷折り（凡例の、刷った面がへこむ向き）のままだと
    # 色の面が筒の内に入った。制作者の決定（2026-11-06「今のうちに4つ直す」）で、御来迎の外筒・虎の胴と同じ線で直した。
    # 線は破線で刷るので、刷る線の形が山折りの形に変わる
    return Part(1, "drum", "頭", outline, label_xy=(1, L * 0.4), label="1",
                mountain=[((i * s, 0), (i * s, L)) for i in range(1, 9)], glue=[[(W, 0), (W + g, 1), (W + g, L - 1), (W, L)]],
                cuts=[(3.5 * s - st / 2, L / 2 - st / 2, st, st)], art=art)


def _cap(number, key, p):
    """頭の端の蓋。八角の各辺に糊代を付け、山折りして頭の内側に貼る。中心に軸の穴。絵の端の面の菊の模様を描く。

    山折り（刷った面の裏へ折る）なので、糊代は頭の内へ入り、菊の絵の面が頭の外を向く。前の谷折りでは、絵の面が頭の内を向いた。
    制作者の決定（2026-11-06「今のうちに4つ直す」）で、頭の筒と一緒に直した。線は破線で刷るので、刷る線の形が山折りの形に変わる。
    """
    r = p["head_r"]
    side, apo = octagon(p)
    tab = min(5.0, side * 0.6)
    c = r + tab
    v = [(c + r * math.cos(math.pi / 8 + k * math.pi / 4), c + r * math.sin(math.pi / 8 + k * math.pi / 4)) for k in range(8)]
    outline, folds, glue = [], [], []
    for k in range(8):
        a, b = v[k], v[(k + 1) % 8]
        dx, dy = (b[0] - a[0]) / side, (b[1] - a[1]) / side
        # 外向きの法線。正八角形なので、中心から辺の中点へ向かう向きがそのまま法線になる
        nx, ny = ((a[0] + b[0]) / 2 - c) / apo, ((a[1] + b[1]) / 2 - c) / apo
        # 隣の糊代と重ならないよう、外の辺を両側から縮める（八角の外角 45° の半分の tan より大きく）
        k_in = tab * 0.6
        ta = (a[0] + nx * tab + dx * k_in, a[1] + ny * tab + dy * k_in)
        tb = (b[0] + nx * tab - dx * k_in, b[1] + ny * tab - dy * k_in)
        outline += [a, ta, tb]
        folds.append((a, b))
        glue.append([a, ta, tb, b])
    region = Polygon(v).buffer(-0.3)
    art = [_poly(list(region.exterior.coords)[:-1], WOOD)]
    art += [_line([(c + apo * 0.3 * math.cos(t), c + apo * 0.3 * math.sin(t)), (c + apo * 0.85 * math.cos(t), c + apo * 0.85 * math.sin(t))], PAPER, 0.5)
            for t in (2 * math.pi * i / 16 for i in range(16))]
    art.append(_poly(_circle(c, c, apo * 0.25, 16), CAP))
    return Part(number, key, "頭の蓋", outline, label_xy=(c - 0.8, c - apo * 0.95), label=str(number), mountain=folds, glue=glue,
                holes=[(c, c, AXLE_HOLE_R)], art=_art(art, region))


WHEEL_KEYS = ("wheela", "wheelb", "wheelc", "wheeld")


def parts(p):
    if p["ride"] == "rat":
        return [_rat_body(p), _rider(p), _tail(p)] + [_wheel(4 + i, k, p) for i, k in enumerate(WHEEL_KEYS)]
    if p["ride"] == "mallet":
        return [_drum(p), _cap(2, "capa", p), _cap(3, "capb", p), _wheel(4, "wheela", p), _wheel(5, "wheelb", p)]
    return [_head(1, "head", "頭", p, False), _head(2, "headback", "頭の裏", p, True), _cloth(p), _fork(p), _wheel(5, "wheela", p)]


def _row(items, x, y, gap):
    for q in items:
        q.x, q.y = x, y
        x += q.width + gap
    return x


def place(by_key, page, top, gap):
    """鼠車: 胴を左上、車輪を胴の右に 2 列で積み、人形と尾を下の段。春駒: 頭 2 枚と布を上の段、二股と車輪を下の段。
    文字の列は下の段の右（物差しが 100mm あるので、下の段の部品は細い物だけにする）。返り値は (文字の開始 y, 文字の幅, 文字の開始 x)。
    """
    if "body" in by_key:
        body = by_key["body"]
        body.x, body.y = page.x0, top
        wheels = [by_key[k] for k in WHEEL_KEYS]
        d = wheels[0].width
        x = page.x0 + body.width + gap
        cols = min(2, int((page.x1 - x + gap) // (d + gap)))
        low = [by_key["rider"], by_key["tail"]]
        right_h = 0
        if cols >= 1:
            for i, q in enumerate(wheels):
                q.x, q.y = x + (i % cols) * (d + gap), top + (i // cols) * (d + gap)
            right_h = math.ceil(len(wheels) / cols) * (d + gap) - gap
        else:
            low += wheels  # 胴の右に入らない時は下の段へ
        y = top + max(body.height, right_h) + gap
        x = _row(low, page.x0, y, gap)
        return y, page.x1 - x, x
    if "drum" in by_key:
        # ぶりぶり: 頭と蓋 2 枚を上の段、車輪 2 つを下の段。物差し（100mm）の幅が残らない時は 2 つ目の車輪を 1 つ目の下へ。
        drum, ca, cb, wa, wb = (by_key[k] for k in ("drum", "capa", "capb", "wheela", "wheelb"))
        _row([drum, ca, cb], page.x0, top, gap)
        y = top + max(drum.height, ca.height) + gap
        x = _row([wa, wb], page.x0, y, gap)
        if page.x1 - x < 102:
            wb.x, wb.y = page.x0, y + wa.height + gap
            x = page.x0 + wa.width + gap
        return y, page.x1 - x, x
    head, back, cloth = by_key["head"], by_key["headback"], by_key["cloth"]
    _row([head, back, cloth], page.x0, top, gap)
    y = top + max(head.height, cloth.height) + gap
    x = _row([by_key["fork"], by_key["wheela"]], page.x0, y, gap)
    return y, page.x1 - x, x


def bom(p):
    paper = paper_name(gsm=p['paper_gsm'])
    why = "家庭のプリンタで刷って作るため"
    n = p["wheel_layers"] - 1
    # 芯の紙の名前は、計算に使う厚さ（card_thickness）から選ぶ。名前を決め打ちにすると、薄い値にした時に計算と名前が食い違う
    core = f"{paper_name(thickness=p['card_thickness'])}。刷った車輪を型にして切る"
    if p["ride"] == "rat":
        rows = [
            {"number": 1, "key": "body", "name": "胴（鼠）", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明（絵の鼠は白く塗った物で、素材は読めない）", "reason": why},
            {"number": 2, "key": "rider", "name": "人形", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明", "reason": why},
            {"number": 3, "key": "tail", "name": "尾", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明", "reason": why},
        ]
        rows += [{"number": 4 + i, "key": k, "name": "車輪", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明（絵の車は茶色の円で、木か土かは読めない）", "reason": why}
                 for i, k in enumerate(WHEEL_KEYS)]
        rows.append({"number": 8, "key": "axle", "name": "軸", "qty": 2, "material": f"竹串（長さ約 {axle_length(p):.0f}mm に切り、先を落とす）", "substituted": True, "original_guess": "不明", "reason": "家にあり、まっすぐで穴の中で回るため"})
        if n:
            rows.append({"number": 9, "key": "core", "name": "車輪の芯", "qty": 4 * n, "material": core, "substituted": True, "original_guess": "不明", "reason": "紙 1 枚では車輪が柔らかく、首を振るため"})
        return rows
    if p["ride"] == "mallet":
        rows = [
            {"number": 1, "key": "drum", "name": "頭", "qty": 1, "material": paper, "substituted": True, "original_guess": "木（推定。絵の頭は木の色に塗った筒に見える）", "reason": why},
            {"number": 2, "key": "capa", "name": "頭の蓋", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明", "reason": why},
            {"number": 3, "key": "capb", "name": "頭の蓋", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明", "reason": why},
            {"number": 4, "key": "wheela", "name": "車輪", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明（絵の端の丸い面が車輪かどうかも推定）", "reason": why},
            {"number": 5, "key": "wheelb", "name": "車輪", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明（同じ）", "reason": why},
            {"number": 6, "key": "handle", "name": "柄", "qty": 1, "material": f"割り箸（割った 1 本、長さ約 {p['handle_len']}mm）", "substituted": True, "original_guess": "竹か木の柄（推定。絵の柄は黄色い）", "reason": "家にあり、引く力に耐えるため"},
            {"number": 7, "key": "axle", "name": "軸", "qty": 1, "material": f"竹串（長さ約 {mallet_axle_length(p):.0f}mm に切り、先を落とす）", "substituted": True, "original_guess": "不明", "reason": "家にあり、穴の中で回るため"},
        ]
        if n:
            rows.append({"number": 8, "key": "core", "name": "車輪の芯", "qty": 2 * n, "material": core, "substituted": True, "original_guess": "不明", "reason": "紙 1 枚では車輪が柔らかく、首を振るため"})
        return rows
    rows = [
        {"number": 1, "key": "head", "name": "頭", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明（張子か木か、絵から読めない）", "reason": why},
        {"number": 2, "key": "headback", "name": "頭の裏", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明", "reason": "割り箸を 2 枚の頭で挟んで貼るため"},
        {"number": 3, "key": "cloth", "name": "布の胴", "qty": 1, "material": paper, "substituted": True, "original_guess": "布（絵の胴は布の襞に見える）", "reason": why},
        {"number": 4, "key": "fork", "name": "二股", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明（絵では棒の先に車が直に付いて見える）", "reason": "紙で車輪を挟んで軸を通すため"},
        {"number": 5, "key": "wheela", "name": "車輪", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明", "reason": why},
        {"number": 6, "key": "stick", "name": "棒", "qty": 1, "material": "割り箸（割った 1 本）", "substituted": True, "original_guess": "竹か木の棒（推定。絵の棒は黄色い）", "reason": "家にあり、押す力に耐えるため"},
        {"number": 7, "key": "axle", "name": "軸", "qty": 1, "material": f"竹串（長さ約 {p['fork_inner'] + 10:.0f}mm に切り、先を落とす）", "substituted": True, "original_guess": "不明", "reason": "家にあり、穴の中で回るため"},
    ]
    if n:
        rows.append({"number": 8, "key": "core", "name": "車輪の芯", "qty": n, "material": core, "substituted": True, "original_guess": "不明", "reason": "紙 1 枚では車輪が柔らかく、首を振るため"})
    return rows


def materials(p):
    # 行の位置でなく key で引く（形で行が変わるため。虎と同じ）。
    by = {r["key"]: r for r in bom(p)}
    out = [f"{by['wheela']['material']}を 1 枚", "のり、はさみ、定規"]
    if p["ride"] in ("stick", "mallet"):
        # 春駒の二股とぶりぶりの頭には、紙の中を切る四角い穴がある（はさみでは切れない）
        out.append("カッター（四角い穴を切る。カッターは大人がする）")
    if p["ride"] == "stick":
        out.append(by["stick"]["material"])
    if p["ride"] == "mallet":
        out.append(by["handle"]["material"])
    out.append(f"{by['axle']['material']} {by['axle']['qty']} 本")
    if "core" in by:
        out.append(f"{paper_name(thickness=p['card_thickness'])}（車輪の芯 {by['core']['qty']} 枚分）")
    return out


def steps(p):
    n = p["wheel_layers"] - 1
    # 中の四角い穴（春駒の二股・ぶりぶりの頭）は外形と同じ実線で刷るので、最初の切る行で除く。除かないと、後の
    # 「カッターは大人がする」の行より先に、子どもがはさみで切り込む。穴を切る行は各形の折る行の前に置く。
    cut = "部品を実線で切る。" + ("中の四角い穴はまだ切らない。" if p["ride"] in ("stick", "mallet") else "")
    out = ["刷った物差しに定規を当て、10cm か確かめる", cut + "穴は竹串の先であけ、軸の穴は竹串が回るまで広げる"]
    if n:
        # 芯の紙の名前は、用意する物と同じく計算の厚さから選ぶ（決め打ちだと、薄い芯で用意する物と手順の名前が食い違った）
        out.append(f"車輪を型にして、{paper_name(thickness=p['card_thickness'])}から車輪 1 つに {n} 枚ずつ芯を切り、刷った車輪の裏に重ねて貼る。芯の真ん中にも穴をあける")
    if p["ride"] == "rat":
        out += ["1 胴を破線で山折りし、糊代で貼って箱にする",
                "竹串を 1 胴の前の 2 つの穴に通し、後ろの 2 つの穴にもう 1 本通す",
                f"車輪を竹串の両端に差し、胴との間を {p['wheel_gap']}mm あけて貼る（厚紙を挟んで測る）。軸ごと回る事を確かめる",
                f"2 人形の耳を山折りし、1 胴の上の面の四角い印（赤茶の点の線。切らない）に貼る（印の真ん中は前の端から {p['rider_at'] * p['body_length']:g}mm）", "3 尾を丸くして、後ろの壁に貼る",
                "机の上で押して、まっすぐ転がるか見る"]
    elif p["ride"] == "mallet":
        out += ["1 頭の真ん中の面の四角い穴を切る（カッターは大人がする）",
                "1 頭を破線で山折りして八角の筒にし、糊代で貼る",
                "2・3 頭の蓋の糊代を山折りし、頭の両端の内側に貼って蓋をする",
                f"割り箸の先から {p['handle_in']:g}mm に鉛筆で印を付け、1 頭の四角い穴に印まで差し込んで貼る（深く入れると奥の軸に当たる）",
                "竹串を 2 つの蓋の穴に通し、両端に 4・5 車輪を差す",
                f"車輪と蓋の間を {p['wheel_gap']}mm あけて貼る（厚紙を挟んで測る）。軸ごと回る事を確かめる",
                "柄を持って、車輪を床に付けて引くか押す"]
    else:
        # 割り箸を止める所は、刷った印の見た目で言う。印を刷らない深さ（_fork と同じ下限）では、折り目で止めると言う。
        # 折り目は「四角い穴のわき」と言う。春駒で「頭」と言うと馬の頭（部品 1・2）と取り違える（二股の真ん中の面に名前は刷っていない）。
        stop = (f"割り箸の先は、両方の腕の位置の印（赤茶の点の線。切らない。四角い穴のわきの折り目から {p['stick_in']:g}mm）で止めて貼る"
                if p["stick_in"] > STOP_MARK_MIN else "割り箸の先は、四角い穴の両わきの折り目（破線）で止めて貼る")
        out += ["1 頭と 2 頭の裏で割り箸の上の端を挟んで貼る", "3 布の胴を割り箸に巻き、頭の下に貼る",
                "4 二股の真ん中の四角い穴を切る（カッターは大人がする）",
                "4 二股を破線で谷折りして コ の字にし、真ん中の四角い穴に割り箸の下の端を通す。" + stop + "（深く入れると車輪に当たる）",
                "竹串を二股の穴と車輪の穴に通し、車輪を二股の真ん中に貼る。軸ごと回る事を確かめる",
                "割り箸を持ち、車輪を床に付けて押す"]
    return out


def measures(p):
    """転がるかの二択でなく、どう転がるかを言葉か絵で予想する（虎と同じ）。押した物と長さは手で書く欄を置く。"""
    return {"predict": "押すと、どう転がると思いますか（言葉か絵で）", "rows": [[("押した強さ（そっと・強く）", 40), ("転がった長さ", 30)]]}


def diagram(x, y, w, h, p):
    """組み上がりを横から見た図。寸法の図ではなく、部品の並びを見せるだけの絵。車輪は四角で示す。"""
    R, a = p["wheel_r"], p["axle_height"]
    if p["ride"] == "rat":
        L, H = p["body_length"], p["body_height"]
        s = min(w / (L + 2 * R), h / (H + p["figure_h"] + R))
        floor = y + h
        bx = x + R * s
        by = floor - (R - a + H) * s
        shapes = [{"kind": "rect", "x": bx, "y": by, "w": L * s, "h": H * s}]
        for ax in (p["inset_front"], L - p["inset_rear"]):
            cx, cy = bx + ax * s, floor - R * s
            shapes.append({"kind": "rect", "x": cx - R * s, "y": cy - R * s, "w": 2 * R * s, "h": 2 * R * s, "dash": "1,0.6"})
        fx = bx + p["rider_at"] * L * s
        shapes.append({"kind": "rect", "x": fx - p["figure_w"] * s / 2, "y": by - p["figure_h"] * s, "w": p["figure_w"] * s, "h": p["figure_h"] * s})
        shapes.append({"kind": "line", "x1": x, "y1": floor, "x2": x + w, "y2": floor})
        return shapes
    if p["ride"] == "mallet":
        r, L = p["head_r"], p["head_len"]
        s = min(w / (L + 2 * R + 60), h / (2 * R + 4))
        floor = y + h
        cx, cy = x + R * s, floor - R * s
        return [{"kind": "rect", "x": cx - R * s, "y": cy - R * s, "w": 2 * R * s, "h": 2 * R * s, "dash": "1,0.6"},
                {"kind": "rect", "x": cx - r * s, "y": cy - r * s, "w": 2 * r * s, "h": 2 * r * s},
                {"kind": "line", "x1": cx + r * s, "y1": cy, "x2": x + w, "y2": floor},
                {"kind": "line", "x1": x, "y1": floor, "x2": x + w, "y2": floor}]
    A = p["fork_arm"]
    s = h / (A + R + 60)
    cx, floor = x + w / 2, y + h
    cy = floor - R * s
    return [{"kind": "rect", "x": cx - R * s, "y": cy - R * s, "w": 2 * R * s, "h": 2 * R * s, "dash": "1,0.6"},
            # 二股の腕は軸から上へ A - a、下へ a（腕の先は軸の下 a で、床より上に止まる）
            {"kind": "rect", "x": cx - 1, "y": cy - (A - a) * s, "w": 2, "h": A * s},
            {"kind": "line", "x1": cx, "y1": cy - (A - a) * s, "x2": cx + 30 * s, "y2": y},
            {"kind": "line", "x1": x, "y1": floor, "x2": x + w, "y2": floor}]
