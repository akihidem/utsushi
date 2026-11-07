"""雛形 balance: 重りで重心を下げ、倒れずに戻る玩具（弥次郎兵衛・起き上がり小法師）。

刷る形（kind）で 2 つを描き分ける。
- yajirobe（コマ 7 の左頁）: 奴の形の紙の体（表と裏の 2 枚）に竹串の腕を 2 本挟み、腕の先に粘土の玉を付ける。
  床は腕の差し込みの深さ・向きと玉の位置に頼るので、裏の 1 枚の刷った面に竹串を置く線を刷り（その面を内にして表と貼る）、
  竹串に差し込みと玉の中心を写す「腕の物差し」を刷る。裏の 1 枚の外に見える面は刷らない面になる（無地）。
  体の下の V の先（【解釈】図では奴の下の細い V が、台の上の人形の頭に乗っている）を、立てた竹串の先か指先に乗せる。
  図の台（棒の上の板としゃがんだ人形）は刷らず、竹串を粘土の台に立てた物で置き換える（作る手間を減らすため）。
- okiagari（コマ 26 の左頁）: 頭巾の人形の、上がすぼまった縦長の胴。紙の円錐（上）と、舟形の切れ（ゴア）を
  つないだ半球（下）を貼り合わせ、半球の底に粘土を押し込む。【解釈】図の底は半球より平たく見えるが、
  起き上がる条件を半球の半径 1 つで数えられるよう半球にした。円錐の先は尖る（図の頭巾の丸い頭は描かない）。
寸法は手元の複写の図の比から出した見込みで、どの値も実物では未確認。Claude が変えてよいのは RANGES の名前の値だけ。

動きの見込み（F5.balance）の前提（質量は g、長さは mm。pivot_model と同じく下を z の正にする）:
- 弥次郎兵衛: 支点は V の先。質量の点は、紙の体 2 枚（外形の面積 × 坪量、外形の重心）、先の当て紙、
  竹串の腕 2 本（太さ 3mm の竹串の線密度の見込み × 長さ、腕の真ん中）、玉 2 つ。紙の曲がり・糊の重さ・摩擦は入れない。
  ・重心が支点より MIN_DROP 以上下にある（上にあれば倒れる。真下に近いと少しの風で回って落ちる）。
  ・玉の粘土を手で量る差（CLAY_TOL）だけ左右が違っても、静かな時の傾きが MAX_TILT 以下（重心が低いほど傾きは小さい）。
  ・傾けた時に玉が台の竹串に当たるまで MIN_SWING 以上振れる。玉の下が机に当たらない。
  ・腕の竹串の差し込みが体の中に収まり、左右の腕が体の中で交わらない。竹串 1 本の長さで足りる。
  ・支点の先は紙を重ねて厚くする（当て紙）。表裏 2 枚と当て紙の厚みの和が MIN_TIP_T 以上（薄い縁は串の先が滑るか刺さる）。
- 起き上がり小法師: 底の半球の曲がりの中心は、底から半径 R の高さにある。重心がそれより下なら、傾けた時に
  重心が上がるので戻る（半球の上で転がる限り。円錐の側が床に付くほど倒すと、ここの式は外れる）。
  質量の点は、円錐の紙（側面の重心は底から高さの 1/3）、半球の紙（重心は底の面から R/2）、帯の紙、底の粘土
  （半球の底を満たす球の欠けの形と見る。油粘土の密度の見込み CLAY_DENSITY）。
  ・重心が曲がりの中心より MIN_MARGIN × R 以上下にある（紙の継ぎ目の段や床の摩擦の分の余裕の見込み）。
  ・粘土が底の半分の高さに収まる（それより多いと赤道の継ぎ目を押し広げる見込み）。
  底の切れには、粘土を平らに詰める高さの線を刷る（重心の式は、粘土が底の真ん中に平らに詰まる形に頼るため）。
  ・円錐を開いた形が半円より開かない（開くと型紙の扇が重なり、上がすぼまった形にならない）。
"""
import math

from shapely.geometry import LineString, Point, Polygon

from ..paper_words import paper_name  # 紙の書き方は 4 つの名前だけ（制作者の指示 2026-11-05）
from ..model import Failure, Part
from ..pivot_model import center, paper_mass, rest_tilt_deg

ID = "balance"
DEFAULTS = {
    "kind": "yajirobe",
    # --- 弥次郎兵衛。体の幅と高さはコマ 7 の図の奴の比（幅 258 : 帽子の上から V の先まで 325）。
    "body_w": 60, "body_h": 76,
    # 腕は肩（体の下の角）から玉の中心まで。図では水平から約 60° 下へ、体の高さの 1.4 倍ほど伸びる。
    "arm_length": 108, "arm_angle": 60, "arm_insert": 15,
    "ball_g": 3.0, "tip_layers": 6,
    # 台の竹串を粘土の台に立てた時の、机から先までの高さ（180mm の竹串の 40mm を台に差す見込み）。
    "stand_h": 140,
    # --- 起き上がり小法師。コマ 26 の図の胴は幅 290 : 高さ 430 なので、半径 25 に円錐の高さ 49。
    "base_r": 25, "cone_h": 49, "gores": 8, "band": 6, "seam_glue": 6,
    "bottom_g": 3.0,
    # --- 共通。坪量と厚みはふつうの厚めの紙の見込み。実物の紙を量ったら置き換える。
    "paper_gsm": 150, "paper_thickness": 0.15,
}
RANGES = {
    "body_w": (40, 90), "body_h": (50, 110),
    # 腕の上限 150 は、腕の物差し（差し込み＋腕）が A4 の印字域の幅 190mm に 1 本で入るため。
    "arm_length": (40, 150), "arm_angle": (-10, 85), "arm_insert": (5, 40),
    # 玉 1 つの粘土。0.5g より軽いと指でつまんで丸められず、20g を超えると竹串の腕がしなう見込み。
    "ball_g": (0.5, 20), "tip_layers": (1, 12), "stand_h": (60, 170),
    # 半径の上限 28 は、半球の切れの帯（円周＋糊代）が A4 の印字域の幅 190mm に 1 本で入るため。
    "base_r": (15, 28), "cone_h": (20, 100), "gores": (6, 12), "band": (4, 10), "seam_glue": (4, 10),
    # 底の粘土。1g より軽いと紙の重さに負け、30g を超えると底に収まらない見込み（どちらも床でも数える）。
    "bottom_g": (1, 30),
    "paper_gsm": (40, 400), "paper_thickness": (0.05, 0.5),
}
KINDS = ("yajirobe", "okiagari")
# 刷る形を決める寸法（どの玩具か）。形ごとに部品が違うので、寸法を直に渡す入口では必ず書かせる。
FORM = "kind"
FORMS = KINDS
# 既定の出典（data/sources/ の名前）。--source を書かない時に、雛形と合わない出典の印を刷らないため。
SOURCE = "NDL-1187053-R0000007-L-balance"
# 形ごとの出典。形と合わない出典を渡すと compose が F1.source で落とす（別の玩具の出典を刷らないため）。
SOURCES = {"yajirobe": SOURCE, "okiagari": "NDL-1187053-R0000026-L-balance"}

# どれも見込み。実物で確かめていない。
SKEWER_LEN = 180  # 家にある竹串の長さ
SKEWER_G_PER_MM = 0.0042  # 太さ 3mm の竹串（比重 0.6 の見込み）の 1mm あたりの重さ
SKEWER_R = 1.5
CLAY_DENSITY = 1.8e-3  # 油粘土の密度 g/mm³
CLAY_TOL = 0.3  # 手で丸めた粘土の玉の、左右の差の見込み g
MIN_DROP = 10  # 重心が支点の下にあるべき深さ mm
MAX_TILT = 10  # 左右の差で静かな時に傾いてよい角度
MIN_SWING = 20  # 玉が台の竹串に当たるまでに振れてよい角度
TABLE_CLEAR = 10  # 玉の下と机の間の余裕 mm
MIN_TIP_T = 1.0  # 支点の先の紙の厚みの下限 mm（串の先が座る見込みの厚み）
PAD = 8  # 当て紙の 1 枚の大きさ mm（貼ってから V の線で切りそろえる）
MIN_MARGIN = 0.25  # 起き上がりの重心が曲がりの中心より下にあるべき量（半径の割合）
MAX_CLAY_FILL = 0.5  # 粘土の高さの上限（半径の割合）

KIMONO, HAT, INK = "#c8a96e", "#e2d2a4", "#3b3a34"
ROBE, HOOD, FACE, DOME = "#cfae62", "#e3cd8e", "#d9a58c", "#c09a50"
TITLES = {"yajirobe": "弥次郎兵衛", "okiagari": "起き上がり小法師"}


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
    if isinstance(p.get("gores"), float) and not p["gores"].is_integer():
        out.append(Failure("F5.range", "gores", "切れの数は整数"))
    if isinstance(p.get("tip_layers"), float) and not p["tip_layers"].is_integer():
        out.append(Failure("F5.range", "tip_layers", "当て紙の枚数は整数"))
    return out


# ---------------------------------------------------------------- 弥次郎兵衛

# コマ 7 の奴を 1205 幅に縮めた図で手で取った点（画素は使っていない）。帽子 → 袖の横棒 → 胴 → V の先。
_YAKKO = [(410, 828), (486, 828), (480, 806), (592, 735), (607, 748), (601, 800), (590, 828), (668, 828), (668, 890), (632, 890),
          (655, 978), (582, 978), (565, 1060), (549, 985), (480, 985), (503, 890), (410, 890)]
_HAT = [(486, 828), (480, 806), (592, 735), (607, 748), (601, 800), (590, 828)]
_COLLAR = [[(548, 830), (562, 902), (578, 842)]]
_HEM = [[(492, 940), (642, 935)]]
_X0, _Y0, _PX_W, _PX_H = 410, 735, 668 - 410, 1060 - 735
_TIP, _SHOULDERS = (565, 1060), ((480, 985), (655, 978))
_V_TOP = ((549, 985), (582, 978))


def _yk(p, pts):
    """図の点を mm にする。"""
    sx, sy = p["body_w"] / _PX_W, p["body_h"] / _PX_H
    return [((x - _X0) * sx, (y - _Y0) * sy) for x, y in pts]


def _rel(p, pt):
    """表の 1 枚の上の点を、支点（V の先）を原点・下を正にした (x, z) にする。"""
    (tx, ty), (x, y) = _yk(p, [_TIP])[0], _yk(p, [pt])[0]
    return x - tx, y - ty


def arm_geometry(p):
    """左右の腕の (差し込みの奥の端, 肩, 玉の中心)。どれも支点を原点・下を正。左が先。"""
    a = math.radians(p["arm_angle"])
    out = []
    for side, sh in zip((-1, 1), _SHOULDERS):
        sx, sz = _rel(p, sh)
        dx, dz = side * math.cos(a), math.sin(a)
        ball = (sx + dx * p["arm_length"], sz + dz * p["arm_length"])
        inner = (sx - dx * p["arm_insert"], sz - dz * p["arm_insert"])
        out.append((inner, (sx, sz), ball))
    return out


def ball_r(g):
    return (3 * g / (4 * math.pi * CLAY_DENSITY)) ** (1 / 3)


def yajirobe_points(p, extra_left=0.0):
    """支点のまわりの質量の点。extra_left は左の玉に足す重さ（左右の差を見るため）。"""
    body = Polygon(_yk(p, _YAKKO))
    tx, ty = _yk(p, [_TIP])[0]
    c = body.centroid
    pts = [(2 * paper_mass(body.area, p["paper_gsm"]), c.x - tx, c.y - ty)]
    # 当て紙は V の先の PAD 四方に重なる。切りそろえる前の重さで見る（重い側に見て安全）。
    pts.append((paper_mass(PAD * PAD * p["tip_layers"], p["paper_gsm"]), 0, -PAD / 2))
    for i, (inner, _, ball) in enumerate(arm_geometry(p)):
        stick = SKEWER_G_PER_MM * (p["arm_length"] + p["arm_insert"])
        pts.append((stick, (inner[0] + ball[0]) / 2, (inner[1] + ball[1]) / 2))
        pts.append((p["ball_g"] + (extra_left if i == 0 else 0), ball[0], ball[1]))
    return pts


def tip_thickness(p):
    return (2 + p["tip_layers"]) * p["paper_thickness"]


def _check_yajirobe(p):
    out = []
    pts = yajirobe_points(p)
    _, z, _ = center(pts)
    if z < MIN_DROP:
        where = f"支点より {-z:.1f}mm 上にあり、倒れる" if z <= 0 else f"支点の下 {z:.1f}mm で浅く、回って落ちやすい"
        out.append(Failure("F5.balance", "重心", f"重心が{where}（{MIN_DROP}mm 以上下に）"))
    else:
        tilt = abs(rest_tilt_deg(yajirobe_points(p, CLAY_TOL)))
        if tilt > MAX_TILT:
            out.append(Failure("F5.balance", "玉", f"玉の左右が {CLAY_TOL}g 違うだけで {tilt:.0f}° 傾く（{MAX_TILT}° まで）"))
    arms = arm_geometry(p)
    r = ball_r(p["ball_g"])
    low = 0.0
    # 肩は左右で少し非対称（図の奴の形）なので、玉ごとに見る。
    for (_, _, (bx, bz)), side in zip(arms, ("左", "右")):
        d = math.hypot(bx, bz)
        if d <= r + SKEWER_R:
            out.append(Failure("F5.balance", f"{side}の玉", "玉が支点の串に重なる"))
            continue
        # 台の竹串は支点の真下へ伸びる。玉の中心の、真下からの角度から、玉と串の半径の分を引く。
        reach = math.asin((r + SKEWER_R) / d)
        swing = math.degrees(math.atan2(abs(bx), bz) - reach)
        if bz > 0 and swing < MIN_SWING:
            out.append(Failure("F5.balance", f"{side}の玉", f"玉が台の竹串に当たるまで {swing:.1f}° しか振れない（{MIN_SWING}° 以上）"))
        # 机に当たるか。振れる間に玉の中心は支点のまわりの半径 d の円を回り、串に当たる所（真下から reach の角）が一番低い。
        # 串に届く前に振れが止まる事は見込まない（強く押した時を見る）。休む時の高さより低ければ、そちらを使う。
        low = max(low, max(bz, d * math.cos(reach)) + r)
    if low > p["stand_h"] - TABLE_CLEAR:
        out.append(Failure("F5.balance", "台", f"振れた時の玉の下が支点の {low:.0f}mm 下まで来て、高さ {p['stand_h']}mm の台では机に当たる（余裕 {TABLE_CLEAR}mm）"))
    body = Polygon([_rel(p, q) for q in _YAKKO])
    for (inner, _, _), side in zip(arms, ("左", "右")):
        if not body.contains(Point(inner)) or body.exterior.distance(Point(inner)) < SKEWER_R:
            out.append(Failure("F5.balance", f"{side}の腕", f"竹串の差し込みの奥 {p['arm_insert']}mm が体の外に出る"))
    if LineString(arms[0][:2]).intersects(LineString(arms[1][:2])):
        out.append(Failure("F5.balance", "腕", "左右の竹串が体の中で交わる"))
    if p["arm_length"] + p["arm_insert"] > SKEWER_LEN:
        out.append(Failure("F5.balance", "腕", f"腕に竹串が {p['arm_length'] + p['arm_insert']}mm 要り、{SKEWER_LEN}mm の竹串で足りない"))
    if tip_thickness(p) < MIN_TIP_T:
        out.append(Failure("F5.balance", "支点", f"V の先の紙が {tip_thickness(p):.2f}mm で薄く、串の先が座らない（{MIN_TIP_T}mm 以上。当て紙を増やす）"))
    return out


def _yakko_part(p):
    outline = _yk(p, _YAKKO)
    art = [{"kind": "poly", "pts": outline, "fill": KIMONO, "stroke": INK, "sw": 0.2},
           {"kind": "poly", "pts": _yk(p, _HAT), "fill": HAT, "stroke": INK, "sw": 0.2}]
    art += [{"kind": "line", "pts": _yk(p, ln), "stroke": INK, "sw": 0.3} for ln in _COLLAR + _HEM]
    # 番号は袖の端に置く（帽子の横は外形の外）。
    return Part(1, "front", "体（表）", outline, label_xy=(p["body_w"] * 0.93, p["body_h"] * 0.33), label="1", art=art)


ARM_MARK = "#9a3b2a"


def _back_part(p):
    """裏の 1 枚。刷った面を内にして表と貼るので、外形は表と同じ向き（鏡にしない）。刷った面に竹串を置く線を刷る。
    重ね方: 裏を刷った面を上に置き、竹串を載せ、表を刷った面を上にしたまま重ねる。どちらの紙も上から見えるのは刷った面なので、
    同じ向きの外形がそのまま重なる。鏡にすると、左右が非対称の奴では外形がずれる（表を裏返すと奴の絵が内に隠れる）。
    線は差し込みの奥の端から肩の角の 1mm 手前まで（角まで引くと線の太さが外形の外に出る）。奥の端に四角い印。"""
    outline = _yk(p, _YAKKO)
    tx, ty = _yk(p, [_TIP])[0]
    art = []
    for inner, sh, _ in arm_geometry(p):
        x0, y0 = inner[0] + tx, inner[1] + ty
        x1, y1 = sh[0] + tx, sh[1] + ty
        k = 1 - 1 / math.hypot(x1 - x0, y1 - y0)
        art.append({"kind": "line", "pts": [(x0, y0), (x0 + (x1 - x0) * k, y0 + (y1 - y0) * k)], "stroke": ARM_MARK, "sw": 0.6, "role": "arm"})
        art.append({"kind": "poly", "pts": [(x0 - 0.8, y0 - 0.8), (x0 + 0.8, y0 - 0.8), (x0 + 0.8, y0 + 0.8), (x0 - 0.8, y0 + 0.8)], "fill": ARM_MARK})
    return Part(2, "back", "体（裏）", outline, label_xy=(p["body_w"] * 0.93, p["body_h"] * 0.33), label="2", art=art)


GAUGE_W = 8


def _gauge_part(p):
    """腕の物差し。左の端に竹串の端を合わせ、差し込みの深さ（肩の印）と玉の中心の印をペンで写す。
    印の位置は art の "at"（左の端からの mm）にも持たせ、試験が式と比べられるようにする。"""
    a, L = p["arm_insert"], p["arm_length"]
    part = Part(4, "gauge", "腕の物差し", [(0, 0), (a + L, 0), (a + L, GAUGE_W), (0, GAUGE_W)], label_xy=(0.8, 1.2), label="4")
    part.art = [{"kind": "line", "pts": [(a, 0.3), (a, GAUGE_W - 0.3)], "stroke": ARM_MARK, "sw": 0.5, "at": a}]
    r = min(GAUGE_W / 2 - 0.6, ball_r(p["ball_g"]))
    cx, cy = a + L - r - 0.4, GAUGE_W / 2
    # 玉の中心は竹串の先（物差しの右の端）。玉の丸は端の内に描き、中心の印は端の線に重ねない縦の線で示す。
    part.art.append({"kind": "poly", "pts": [(cx + r * math.cos(2 * math.pi * i / 24), cy + r * math.sin(2 * math.pi * i / 24)) for i in range(24)], "fill": "#e8dfc6", "stroke": INK, "sw": 0.2})
    part.art.append({"kind": "line", "pts": [(a + L - 0.4, 0.3), (a + L - 0.4, GAUGE_W - 0.3)], "stroke": ARM_MARK, "sw": 0.5, "at": a + L})
    return part


def _tip_part(p):
    n = int(p["tip_layers"])
    part = Part(3, "tip", "先の当て紙", [(0, 0), (PAD, 0), (PAD, PAD * n), (0, PAD * n)], label_xy=(0.8, 1.2), label="3")
    # 蛇腹に折って n 枚に重ねる。谷と山を交互にすると、重ねた時に端がそろう。
    for i in range(1, n):
        (part.valley if i % 2 else part.mountain).append(((0, PAD * i), (PAD, PAD * i)))
    return part


# ---------------------------------------------------------------- 起き上がり小法師

def slant(p):
    return math.hypot(p["base_r"], p["cone_h"])


def cone_angles(p):
    """円錐を開いた扇の角（本体 θ と、継ぎ目の糊代 δ）。扇の弧の長さが底の円周と同じになる。"""
    s = slant(p)
    return 2 * math.pi * p["base_r"] / s, p["seam_glue"] / s


def clay_cap(p):
    """底の粘土を、半球の底を満たす球の欠けと見る。(欠けの高さ, 底から重心までの高さ)。"""
    R, v = p["base_r"], p["bottom_g"] / CLAY_DENSITY
    lo, hi = 0.0, R
    for _ in range(60):  # 欠けの体積 π h²(3R − h)/3 は h について増えるので、二分法で解く
        h = (lo + hi) / 2
        lo, hi = (h, hi) if math.pi * h * h * (3 * R - h) / 3 < v else (lo, h)
    h = (lo + hi) / 2
    return h, R - 3 * (2 * R - h) ** 2 / (4 * (3 * R - h))


def okiagari_points(p):
    """(質量, 0, 底からの高さ) の点。左右は対称なので x は 0。"""
    R, H, g = p["base_r"], p["cone_h"], p["paper_gsm"]
    cone = (paper_mass(math.pi * R * slant(p), g), 0, R + H / 3)
    dome = (paper_mass(2 * math.pi * R * R, g), 0, R / 2)
    band = (paper_mass(2 * math.pi * R * p["band"], g), 0, R + p["band"] / 2)
    return [cone, dome, band, (p["bottom_g"], 0, clay_cap(p)[1])]


def com_height(p):
    return center(okiagari_points(p))[1]


def _check_okiagari(p):
    out = []
    R, h = p["base_r"], com_height(p)
    if R - h < MIN_MARGIN * R:
        out.append(Failure("F5.balance", "重心", f"重心が底から {h:.1f}mm で、底の丸みの中心（{R}mm）より {MIN_MARGIN * R:.1f}mm 以上下に無く、起き上がらない"))
    cap, _ = clay_cap(p)
    if cap > MAX_CLAY_FILL * R:
        out.append(Failure("F5.balance", "粘土", f"粘土が底から {cap:.1f}mm まで来て、底の半分（{MAX_CLAY_FILL * R:.1f}mm）に収まらない"))
    th, dl = cone_angles(p)
    if th + dl > math.pi:
        out.append(Failure("F5.balance", "円錐", f"円錐を開くと {math.degrees(th + dl):.0f}° で半円を超える（円錐を高くする）"))
    return out


def check_physics(p):
    return _check_yajirobe(p) if p["kind"] == "yajirobe" else _check_okiagari(p)


# コマ 26 の小法師を 1205 幅に縮めた図で取った値。円錐の先 y=880、底の円の継ぎ目 y=1165、軸 x=545、半径 145。
_APEX_Y, _EQ_Y, _AXIS_X, _PX_R = 880, 1165, 545, 145
_HOOD_Y, _FACE_Y, _FACE_R = 945, 985, 42
_MARKS = [(515, 1045), (548, 1075), (525, 1100), (470, 1125), (562, 1100), (600, 1140), (520, 1158)]


def _sector(cx, r, a0, a1, n=48, apex=True):
    pts = [(cx + r * math.sin(a0 + (a1 - a0) * i / n), r * math.cos(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]
    return ([(cx, 0)] if apex else []) + pts


def _on_cone(p, px, py):
    """図の正面の点を、開いた扇の上の (先からの長さ, 扇の真ん中からの角) にする。"""
    frac = (py - _APEX_Y) / (_EQ_Y - _APEX_Y)
    ring = _PX_R * frac  # その高さの胴の半径（図の画素）
    phi = math.asin(max(-1, min(1, (px - _AXIS_X) / ring)))
    return frac * slant(p), phi * p["base_r"] / slant(p)


def _shell_part(p):
    s = slant(p)
    th, dl = cone_angles(p)
    a0, a1 = -(th + dl) / 2, (th + dl) / 2
    half = max(s * math.sin(min(a1, math.pi / 2)), 0)
    cx = half
    outline = _sector(cx, s, a0, a1)
    part = Part(1, "shell", "胴（円錐）", outline, label_xy=(cx - 1, s * 0.82), label="1")
    part.glue = [_sector(cx, s, a1 - dl, a1, 8)]
    ea = 0.4 / s  # 糊代と切る線から絵を少し離す
    mid = a0 + th / 2  # 本体の扇の真ん中が正面（継ぎ目は背中）
    art = [{"kind": "poly", "pts": _sector(cx, s - 0.3, a0 + ea, a1 - dl - ea), "fill": ROBE}]
    hood = s * (_HOOD_Y - _APEX_Y) / (_EQ_Y - _APEX_Y)
    art.append({"kind": "poly", "pts": _sector(cx, hood, a0 + ea, a1 - dl - ea), "fill": HOOD})
    art.append({"kind": "line", "pts": _sector(cx, hood, a0 + ea, a1 - dl - ea, apex=False), "stroke": INK, "sw": 0.3})
    fd = s * (_FACE_Y - _APEX_Y) / (_EQ_Y - _APEX_Y)
    fr = _FACE_R / _PX_R * p["base_r"]
    fcx, fcy = cx + fd * math.sin(mid), fd * math.cos(mid)
    art.append({"kind": "poly", "pts": [(fcx + fr * math.cos(2 * math.pi * i / 32), fcy + fr * math.sin(2 * math.pi * i / 32)) for i in range(32)],
                "fill": FACE, "stroke": INK, "sw": 0.2})
    for e in (-1, 1):  # 図の細い目（横の短い線）
        art.append({"kind": "line", "pts": [(fcx + e * fr * 0.55, fcy - fr * 0.15), (fcx + e * fr * 0.15, fcy - fr * 0.1)], "stroke": INK, "sw": 0.3})
    m = 0.09 * p["base_r"]
    for px, py in _MARKS:  # 図の黒い三日月の模様
        d, a = _on_cone(p, px, py)
        a += mid
        mx, my = cx + d * math.sin(a), d * math.cos(a)
        art.append({"kind": "poly", "pts": [(mx - m, my - m * 0.3), (mx, my + m * 0.5), (mx + m, my - m * 0.3), (mx, my + m * 0.1)], "fill": INK})
    part.art = art
    return part


def gore_half_width(p, t):
    """赤道から t mm 下った所の切れの幅の半分。緯度 t/R の円周を切れの数で割る。"""
    return math.pi * p["base_r"] / p["gores"] * math.cos(t / p["base_r"])


def _gore(p, x, top, inset=0.0, n=16):
    L = math.pi * p["base_r"] / 2
    ts = [L * i / n for i in range(n + 1)]
    right = [(x + max(gore_half_width(p, t) - inset, 0), top + t) for t in ts[:-1]]
    left = [(x - max(gore_half_width(p, t) - inset, 0), top + t) for t in reversed(ts[:-1])]
    return right + [(x, top + L - inset * 2)] + left


def _dome_part(p):
    R, n, b, g = p["base_r"], int(p["gores"]), p["band"], p["seam_glue"]
    C = 2 * math.pi * R
    w = C / n
    pts = [(0, 0), (C + g, 0), (C + g, b)]
    for i in reversed(range(n)):
        pts += _gore(p, (i + 0.5) * w, b)[:-1] if i else _gore(p, (i + 0.5) * w, b)
    part = Part(2, "dome", "底（半球の切れ）", pts, label_xy=(1, b + 1.5), label="2")
    # 帯は円錐の底の内側に貼る。円錐の側が内へ傾く分だけ、赤道の線で軽く谷に折る。
    part.valley = [((0, b), (C, b))]
    part.glue = [[(0, 0), (C, 0), (C, b), (0, b)], [(C, 0), (C + g, 0), (C + g, b), (C, b)]]
    part.art = [{"kind": "poly", "pts": _gore(p, (i + 0.5) * w, b + 0.3, 0.3), "fill": DOME} for i in range(n)]
    # 粘土を詰める高さの線。底の極から切れの上を arc だけ戻った所（高さ h の緯度）。全部の切れに引くと、詰めた粘土が真ん中に平らか見える。
    h, _ = clay_cap(p)
    t = math.pi * R / 2 - R * math.acos(1 - h / R)
    hw = gore_half_width(p, t) - 0.6
    if hw > 0.3:
        part.art += [{"kind": "line", "pts": [((i + 0.5) * w - hw, b + t), ((i + 0.5) * w + hw, b + t)], "stroke": INK, "sw": 0.3, "role": "clay"} for i in range(n)]
    return part


# ---------------------------------------------------------------- 共通の口

def parts(p):
    if p["kind"] == "yajirobe":
        return [_yakko_part(p), _back_part(p), _tip_part(p), _gauge_part(p)]
    return [_shell_part(p), _dome_part(p)]


def place(by_key, page, top, gap):
    """部品を上の段から並べ、説明の列は部品の下に左から置く（物差しの 100mm が印字域に入るように）。"""
    x, y, row = page.x0, top, 0
    order = ("front", "back", "tip", "gauge") if "front" in by_key else ("dome", "shell")
    for key in order:
        q = by_key[key]
        if x > page.x0 and x + q.width > page.x1:
            x, y, row = page.x0, y + row + gap, 0
        q.x, q.y = x - min(a for a, _ in q.outline), y - min(b for _, b in q.outline)
        x += q.width + gap
        row = max(row, q.height)
        if key == "dome":  # 半球の切れは横に長いので、1 段を使い切る
            x, y, row = page.x0, y + row + gap, 0
    left = y + row + gap
    return left, page.x1 - page.x0, page.x0


def bom(p):
    paper = paper_name(gsm=p['paper_gsm'])
    why = "家庭のプリンタで刷って作るため"
    if p["kind"] == "yajirobe":
        return [
            {"number": 1, "key": "front", "name": "体（表）", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明（図では塗った奴の形）", "reason": why},
            {"number": 2, "key": "back", "name": "体（裏）", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明", "reason": "腕の竹串を表と裏で挟んで留めるため"},
            {"number": 3, "key": "tip", "name": "先の当て紙", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明", "reason": "支点の先を厚くして、串の先に座らせるため"},
            {"number": 4, "key": "gauge", "name": "腕の物差し", "qty": 1, "material": paper, "substituted": False, "original_guess": "無し（組むための物差し）", "reason": "竹串に差し込みと玉の位置を写すため"},
            {"number": 7, "key": "arm", "name": "腕", "qty": 2, "material": f"竹串（1 本 {p['arm_length'] + p['arm_insert']}mm に切る）", "substituted": True, "original_guess": "竹か針金（図の細い線による推定）", "reason": "家にあり、まっすぐで切りやすいため"},
            {"number": 8, "key": "ball", "name": "玉", "qty": 2, "material": f"油粘土 {p['ball_g']:g}g（直径 約 {2 * ball_r(p['ball_g']):.0f}mm）", "substituted": True, "original_guess": "不明（図では白い玉）", "reason": "量を変えて試しやすいため"},
            {"number": 9, "key": "stand", "name": "台の柱", "qty": 1, "material": f"竹串（{SKEWER_LEN}mm の見込み）", "substituted": True, "original_guess": "棒の上の板と人形（図による）", "reason": "台の人形を作る手間を省き、先の尖った支えにするため"},
            {"number": 10, "key": "base", "name": "台の土台", "qty": 1, "material": "油粘土 30g ほどか消しゴム", "substituted": True, "original_guess": "不明", "reason": "竹串をまっすぐ立てるため"},
        ]
    return [
        {"number": 1, "key": "shell", "name": "胴（円錐）", "qty": 1, "material": paper, "substituted": True, "original_guess": "張子か土（推定）", "reason": why},
        {"number": 2, "key": "dome", "name": "底（半球の切れ）", "qty": 1, "material": paper, "substituted": True, "original_guess": "張子か土（推定）", "reason": why},
        {"number": 8, "key": "weight", "name": "底の重り", "qty": 1, "material": f"油粘土 {p['bottom_g']:g}g", "substituted": True, "original_guess": "土か粘土（起き上がりの作りからの推定）", "reason": "量を変えて試しやすいため"},
        {"number": 9, "key": "tape", "name": "切れを留めるテープ", "qty": 1, "material": "セロハンテープ", "substituted": True, "original_guess": "不明", "reason": "切れの縁どうしを突き合わせて留めるため"},
    ]


def materials(p):
    # 行の位置でなく key で引く。形によって部品表の行が違うので、位置で引くと別の行を刷る。
    by = {r["key"]: r for r in bom(p)}
    if p["kind"] == "yajirobe":
        return [f"{by['front']['material']}を 1 枚", "のり、はさみ、定規", f"{by['arm']['material']}を 2 本", f"{by['ball']['material']}を 2 つ",
                f"台: {by['stand']['material']}と{by['base']['material']}"]
    return [f"{by['shell']['material']}を 1 枚", "のり、はさみ、定規", by["tape"]["material"], by["weight"]["material"]]


def steps(p):
    out = ["刷った物差しに定規を当て、10cm か確かめる", "部品を実線で切る"]
    if p["kind"] == "yajirobe":
        out += [f"3 先の当て紙を蛇腹に折って {int(p['tip_layers'])} 枚に重ね、糊で貼る",
                f"竹串 2 本を {p['arm_length'] + p['arm_insert']}mm に切る。4 腕の物差しの左の端に竹串の端を合わせ、"
                f"肩の印（端から {p['arm_insert']}mm）と玉の印（端から {p['arm_insert'] + p['arm_length']}mm＝竹串の先）をペンで写す",
                f"2 体（裏）の刷った面を上にし、竹串を赤い線に沿って置く。竹串の端を四角い印に、肩の印を肩の角に合わせる"
                f"（差し込み {p['arm_insert']}mm、水平から {p['arm_angle']}° 下）",
                "3 当て紙を V の先に置き、糊を塗って 1 体（表）を、刷った面を上にしたまま（裏返さない）重ねて外形をそろえて貼る。乾いたら当て紙を V の線で切りそろえる",
                f"竹串の先に油粘土を {p['ball_g']:g}g ずつ丸め、玉の中心が竹串の先（肩から {p['arm_length']}mm）に来るように付ける",
                "竹串を土台に立て、V の先を竹串の先か指先に乗せる。傾いたら軽い側の粘土を足す"]
    else:
        out += ["1 胴を丸め、糊代を反対の縁の内に入れて貼り、円錐にする",
                "2 底の切れを帯の所で輪にして貼り、切れの縁どうしを突き合わせてテープで留め、お椀にする",
                f"お椀の底（切れの先が集まる所）に油粘土 {p['bottom_g']:g}g を押し込み、切れの線（底から高さ約 {clay_cap(p)[0]:.0f}mm）まで平らに詰める",
                "帯を赤道の破線で軽く内へ折り、円錐の底の内に差し込んで貼る",
                "倒して手を離し、起き上がるか見る"]
    return out


RESULTS = ("戻った", "戻らない")


def measures(p):
    """戻るかの二択でなく、傾け方と戻り方を言葉か絵で予想する（ほかの雛形と同じ形）。"""
    if p["kind"] == "yajirobe":
        return {"predict": "指で押して傾けると、どう戻ると思いますか（言葉か絵で）", "rows": [[("傾け方（押す所・強さ）", 40)]]}
    return {"predict": "倒して手を離すと、どう動くと思いますか（言葉か絵で）", "rows": [[("倒し方（向き・角度）", 40)]]}


def diagram(x, y, w, h, p):
    """組み上がりを正面から見た絵。寸法の図ではなく、支点・重心の位置・重りの並びを見せるだけ。"""
    if p["kind"] == "yajirobe":
        arms = arm_geometry(p)
        r = ball_r(p["ball_g"])
        span = 2 * max(abs(b[0]) for _, _, b in arms) + 2 * r
        top = p["body_h"]
        s = min(w / span, h / (top + p["stand_h"]))
        ox, oy = x + w / 2, y + top * s
        body = [(ox + a * s, oy + b * s) for a, b in (_rel(p, q) for q in _YAKKO)]
        shapes = [{"kind": "poly", "pts": body, "fill": "none", "sw": 0.25}]
        for inner, sh, b in arms:
            shapes.append({"kind": "line", "x1": ox + sh[0] * s, "y1": oy + sh[1] * s, "x2": ox + b[0] * s, "y2": oy + b[1] * s})
            shapes.append({"kind": "rect", "x": ox + (b[0] - r) * s, "y": oy + (b[1] - r) * s, "w": 2 * r * s, "h": 2 * r * s})
        shapes.append({"kind": "line", "x1": ox, "y1": oy, "x2": ox, "y2": oy + p["stand_h"] * s, "dash": "1,0.6"})
        return shapes
    R, H = p["base_r"], p["cone_h"]
    s = min(w / (2 * R), h / (R + H))
    cx, base = x + w / 2, y + (R + H) * s
    dome = [(cx + R * s * math.cos(math.pi * i / 24), base - R * s + R * s * math.sin(math.pi * i / 24)) for i in range(25)]
    # 左の赤道 → 先 → 右の赤道 → 底の半円（右から左へ）の 1 本の道。半円を逆に並べると、右から左へ赤道の横の線が余分に入る。
    shapes = [{"kind": "poly", "pts": [(cx - R * s, base - R * s), (cx, y)] + dome[:-1], "fill": "none", "sw": 0.25}]
    hc = com_height(p)
    shapes.append({"kind": "rect", "x": cx - 1, "y": base - hc * s - 1, "w": 2, "h": 2})
    shapes.append({"kind": "line", "x1": cx - R * s, "y1": base - R * s, "x2": cx + R * s, "y2": base - R * s, "dash": "1,0.6"})
    return shapes
