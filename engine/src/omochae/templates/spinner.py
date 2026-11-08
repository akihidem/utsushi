"""雛形 spinner: 軸のまわりに回る部品。『江都二色』の風車と独楽を試す。

刷る形（kind）は 5 つ。形が違えば部品も回り方の見込みも違うので、FORM の値で描き分ける。
- pinwheel: 正方形の紙を角から中心へ切り、1 つおきの角を軸へ寄せる紙の風車（コマ 14 左の風車を、家で作れる 1 枚の風車にした翻案）
- square: 中心から 8 本の腕が出て、先に四角い羽が付く風車（コマ 20 右）
- top: 紙の円盤を何枚か重ね、竹串か爪楊枝を通した独楽（コマ 26 左）
- cone: 重ねた円盤の下に紙の円錐を貼り、帯の模様を描いた独楽（コマ 29 右の銭独楽（推定）。図の胴は上が広く下へすぼむ）
- screen: 屏風の 3 枚の面をコの字に折り、向かい合う 2 枚の穴に軸を渡す。軸に巻いた糸を引くと、前の面の外の車が回る
  （コマ 25 左の車屏風。図の屏風の穴の車と、糸を巻いた棒の読みは【解釈】。屏風は車の台として使う）

寸法は図の比を目測して出した。どの値も実物では未確認。Claude が変えてよいのは RANGES の名前の値だけ。

回り方の見込み（式の前提。どれも実物で確かめていない）:
- 風車の羽と柄（ストロー）の間: 羽は軸の 2 か所（風車は中心の紙と 4 つの角の束、四角の羽は 1 の中心と 2 の座金）で軸に載る。
  穴と軸の隙間 s、2 か所の間 b なら、羽は軸に対して atan(s/b) まで傾く。羽の先（半径 R）は柄の側へ R・sin(傾き) 寄る。
  四角の羽は風を受けるよう腕をねじる（TWIST_DEG）ので、羽の半分の幅 × sin(ねじれ) だけ後ろへ出る。
  柄との間（spacer）がこの和に MIN_CLEAR を足した長さより短いと、羽が柄に当たる。紙のたわみは入れていない。
- 穴の余白: 穴の縁から紙の端（切り込みの終わり・羽の角の辺）まで HOLE_MARGIN（虎の雛形と同じ 4mm）。狭いと回すうちに裂ける見込み。
- 穴の隙間: 穴の径 − 軸の径 が MIN_SLACK より小さいと、紙が軸を締めて回らない見込み。
- 柄を持つ手: 柄の長さから軸の位置と羽の半径を引いた残りが GRIP より短いと、羽が手に当たる。
- 独楽は速く回る対称な独楽が倒れない条件（Klein–Sommerfeld の「眠る独楽」）を使う: ω² > 4·M·g·l·I1 / I3²。
  M は全質量、l は先から重心までの高さ、I1 は先を通る横の軸のまわり、I3 は回る軸のまわりの慣性モーメント。
  円盤は一様な紙（面密度 paper_gsm、厚さ paper_gsm/800 mm＝密度 0.8g/cm³ の見込み）、軸は一様な木の棒（WOOD_DENSITY）。
  指でひねって回す速さを OMEGA_HAND と見込み、その SLEEP_RATIO 倍で倒れない事を求める（回り続ける時間の余裕）。
  円盤が軽いと軸の重さで重心が上がり、I3 も小さいので倒れやすい。1 枚で足りなければ layers 枚を重ねて貼る（部品表に枚数を書く）。
  軸が重心を通る事: 刷った円盤の輪郭と穴から重心を数え、穴の中心から COM_TOL より離れれば落とす（ぶれて跳ねる見込み）。
  先が短いと、少し傾いただけで円盤の縁が床に付く。MIN_TILT_DEG 傾くまで縁が床に付かない事を求める。持つ所は MIN_GRIP_TOP。
- 円錐の独楽: 円錐は一様な紙の殻（側面の質量 σ·π·R·s、s は母線。重心は頂点から高さの 2/3、
  重心を通る横の軸のまわりの慣性モーメントは m(R²/4 + h²/18)）として、円盤と軸と同じ式に足す。
  円錐は扇形を丸めて作るので、扇形の角 2πR/s に糊代の角を足しても一回り（2π）に届かない事を求める（平らすぎると糊代が取れない）。
  縁が床に付く角は、先から円錐の縁を見た角 atan((先＋円錐の高さ)/R)。
- 車屏風: 軸は屏風の向かい合う 2 枚の面の穴に載る。2 か所の間は屏風の奥行き（box_depth）なので、風車と同じ式で車の傾きを見て、
  車と前の面の間（wheel_gap）を求める。車は軸の高さ（面の高さの半分）より小さくないと机に当たる。
  車は前の面より外に出るので、屏風が前へ倒れない事を、前の面の下の縁のまわりのモーメントで見る（屏風の紙の重さ ≧ 車の重さ × 張り出し）。
  糸を引く力は手で屏風を押さえて受ける前提で、式に入れていない。
- 空気の抵抗・先の摩擦・紙の反りは入れていない。どれも回る時間を縮める側に効く。
"""
import math

from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

from ..paper_words import paper_name  # 紙の書き方は 4 つの名前だけ（制作者の指示 2026-11-05）
from ..model import Failure, Part

ID = "spinner"
DEFAULTS = {
    "kind": "pinwheel",
    # 軸と柄（風車の 2 つの形で同じ）。竹串 3mm・ストローはふつうの物の見込み。
    "axle_d": 3.0, "hole_d": 3.6, "spacer": 24, "bearing": 10, "stick_length": 200,
    # 紙の風車
    "square": 120, "uncut": 12,
    # 四角の羽の風車。コマ 20 右の図で、中心から羽の中心まで ≈ 羽の一辺 × 2.6
    "vane": 24, "vane_radius": 62, "spoke_w": 4, "hub_r": 12,
    # 独楽。コマ 26 左の図で、円盤の径に対して下の軸は短く、上の軸は径の 4 割ほど
    "disc_r": 30, "layers": 3, "tip": 8, "grip": 25, "hole_offset": 0,
    # 円錐の独楽。コマ 29 右の図で、胴の高さは径の 1/3〜1/2。紙の殻は軽いので、倒れにくいよう低めにした
    # 円盤の半径と下の軸は、平らな独楽と別に持つ（円錐で重心が上がる分、円盤を大きく・先を短くしないと倒れる。式で確かめた）
    "cone_h": 10, "cone_r": 35, "cone_tip": 3,
    # 車屏風。コマ 25 左の図で、面は縦が横の 1.4 倍ほど。奥行きは軸を 2 か所で支える間
    "panel_w": 50, "panel_h": 70, "box_depth": 30, "wheel_gap": 6,
    # 紙の面密度は見込み（厚めの紙）。実物の紙を量ったら置き換える。
    "paper_gsm": 180,
}
RANGES = {
    "axle_d": (1.8, 4.0), "hole_d": (1.0, 8.0), "spacer": (0, 40), "bearing": (2, 30), "stick_length": (100, 210),
    "square": (60, 180), "uncut": (4, 40),
    "vane": (10, 40), "vane_radius": (25, 80), "spoke_w": (2, 10), "hub_r": (5, 25),
    "disc_r": (10, 40), "layers": (1, 6), "tip": (1, 40), "grip": (5, 60), "hole_offset": (0, 10),
    "cone_h": (4, 40), "cone_r": (10, 40), "cone_tip": (1, 40), "panel_w": (25, 60), "panel_h": (40, 120), "box_depth": (15, 60), "wheel_gap": (0, 40),
    "paper_gsm": (40, 400),
}
KINDS = ("pinwheel", "square", "top", "cone", "screen")
# 刷る形を決める寸法。形が違えば部品が違うので、寸法を直に渡す入口では既定に頼らず必ず書かせる。
FORM = "kind"
FORMS = KINDS
# 既定の出典。紙の風車（既定の形）の元にしたコマ 14 左。四角の羽と独楽は場面の --source で出典を替える。
SOURCE = "NDL-1187053-R0000014-L-spinner"
# 刷る形ごとの出典。形ごとに別の玩具の図なので、形と合わない出典の印を刷らない（compose が F1.source で落とす）。
SOURCES = {"pinwheel": SOURCE, "square": "NDL-1187053-R0000020-R-spinner", "top": "NDL-1187053-R0000026-L-spinner",
           "cone": "NDL-1187053-R0000029-R-spinner", "screen": "NDL-1187053-R0000025-L-spinner"}

HOLE_MARGIN = 4
MIN_SLACK = 0.3
MIN_CLEAR = 3
TWIST_DEG = 45
# 腕を 45° ねじっても折れ目が付かない長さの見込み（腕の幅の倍数）。
TWIST_LEN = 3
VANE_GAP = 2
GRIP = 60
# 柄の上の端から軸までの長さ。ストローの端に近いと串の穴が裂ける。
AXLE_FROM_TOP = 10
# 柄のストローの径と、軸の前の止め（テープを巻く分）。軸の長さを部品表に書くため。
STRAW_D = 6
FRONT_STOP = 8
G = 9800.0  # mm/s²
WOOD_DENSITY = 0.65e-3  # g/mm³。竹・木の串の見込み
OMEGA_HAND = 60.0  # rad/s（約 10 回/秒）。指でひねって回す速さの見込み
SLEEP_RATIO = 0.5
MIN_TILT_DEG = 8
MIN_GRIP_TOP = 15
COM_TOL = 0.5
SIN_HALF = math.sin(math.radians(22.5))  # 風車の角の尖り（45°）の半分
NOTCH = 0.5  # 切り込みの口の幅。幅 0 の線は輪郭にできないので、細い V にして刷る
GOLD, CREAM, ORANGE, INK = "#cdb57e", "#e9dfc3", "#c8724e", "#4a3f2c"
# コマ 29 右の銭独楽の茶と、明るい帯
BROWN, TAN = "#8a6a4a", "#c9a77c"
CONE_GLUE = 6  # 円錐の糊代の、外の縁での幅（mm）
LAYER_KEYS = "abcdef"
TITLES = {"pinwheel": "橙の角を表へ曲げて軸に寄せる", "square": "八枚の四角い羽", "top": "円盤に串を通す",
          "cone": "円錐に円盤を載せる", "screen": "屏風の車を糸で回す"}


def title(p):
    return TITLES[p["kind"]]


def spec():
    return {"template_id": ID, "defaults": DEFAULTS, "ranges": RANGES, "kind": KINDS}


def check_range(p):
    out = []
    if isinstance(p.get("layers"), float) and not p["layers"].is_integer():
        out.append(Failure("F5.range", "layers", "重ねる枚数は整数"))
    for k, v in p.items():
        if k == "kind":
            if v not in KINDS:
                out.append(Failure("F5.range", k, f"{v} は {KINDS} のどれでもない"))
        elif k not in RANGES:
            out.append(Failure("F5.range", k, "知らない寸法の名前"))
        elif not isinstance(v, (int, float)) or isinstance(v, bool) or not RANGES[k][0] <= v <= RANGES[k][1]:
            out.append(Failure("F5.range", k, f"{v} は範囲 {RANGES[k]} の外"))
    return out


# ---- 回り方の見込みの式 ----

def _r(p):
    """円盤の半径。円錐の独楽は cone_r、ほかは disc_r。"""
    return p["cone_r"] if p["kind"] == "cone" else p["disc_r"]


def _tip(p):
    """先（円盤か円錐の下に出る軸）の長さ。円錐の独楽は cone_tip、平らな独楽は tip。"""
    return p["cone_tip"] if p["kind"] == "cone" else p["tip"]


def thickness(p):
    return p["paper_gsm"] / 800


def wheel_radius(p):
    if p["kind"] == "pinwheel":
        return p["square"] / math.sqrt(2)
    return p["vane_radius"] + p["vane"] / math.sqrt(2)


def wobble_deg(p):
    """羽が軸に対して傾ける角度。2 か所の穴の隙間と間の長さから。"""
    return math.degrees(math.atan2(max(p["hole_d"] - p["axle_d"], 0), p["bearing"]))


def need_spacer(p):
    """羽が柄に当たらないのに要る、羽の面と柄の間の長さ。"""
    back = wheel_radius(p) * math.sin(math.radians(wobble_deg(p)))
    if p["kind"] == "square":
        back += p["vane"] / math.sqrt(2) * math.sin(math.radians(TWIST_DEG))
    return back + MIN_CLEAR


def tip_hole_dist(p):
    """風車の角の穴を、角の先から尖りの二等分線に沿ってどれだけ入れるか。両側の辺まで穴の縁から HOLE_MARGIN 取れる所。"""
    return (HOLE_MARGIN + p["hole_d"] / 2) / SIN_HALF


def axle_length(p):
    if p["kind"] == "screen":
        # 2 枚の壁の間（奥行き）＋車との間＋車の厚さ＋両端の止め
        return p["box_depth"] + p["wheel_gap"] + p["layers"] * thickness(p) + 2 * FRONT_STOP
    stack = 5 * thickness(p) if p["kind"] == "pinwheel" else 2 * thickness(p)
    return STRAW_D + p["spacer"] + p["bearing"] + stack + FRONT_STOP


def top_stick_length(p):
    cone = p["cone_h"] if p["kind"] == "cone" else 0
    return _tip(p) + cone + p["layers"] * thickness(p) + p["grip"]


def cone_slant(p):
    return math.hypot(_r(p), p["cone_h"])


def cone_angles(p):
    """円錐の扇形の角（rad）と糊代の角。糊代は外の縁で CONE_GLUE mm の幅。"""
    s = cone_slant(p)
    return 2 * math.pi * _r(p) / s, CONE_GLUE / s


def top_masses(p):
    """独楽の質量（g）: 円盤 1 枚・円盤全部・軸。"""
    r = _r(p)
    layer = (math.pi * r * r - math.pi * (p["axle_d"] / 2) ** 2) * 1e-6 * p["paper_gsm"]
    stick = WOOD_DENSITY * math.pi * (p["axle_d"] / 2) ** 2 * top_stick_length(p)
    return layer, layer * p["layers"], stick


def top_parts_mass(p):
    """独楽の成分ごとの (質量 g, 先からの重心の高さ mm, 回る軸のまわりの I3, 重心を通る横の軸のまわりの I1)。"""
    r, d = _r(p), p["axle_d"]
    h = p["layers"] * thickness(p)
    L = top_stick_length(p)
    _, md, ms = top_masses(p)
    hc = p["cone_h"] if p["kind"] == "cone" else 0
    out = [(md, _tip(p) + hc + h / 2, md * r * r / 2, md * (r * r / 4 + h * h / 12)),
           (ms, L / 2, ms * d * d / 8, ms * L * L / 12)]
    if p["kind"] == "cone":
        mc = math.pi * r * cone_slant(p) * 1e-6 * p["paper_gsm"]
        out.append((mc, _tip(p) + 2 * hc / 3, mc * r * r / 2, mc * (r * r / 4 + hc * hc / 18)))
    return out


def top_omega_min(p):
    """眠る独楽の下限の角速度（rad/s）と、先から重心までの高さ l（mm）。座標は軸の先を原点に上を正にする。"""
    comps = top_parts_mass(p)
    M = sum(m for m, _, _, _ in comps)
    l = sum(m * z for m, z, _, _ in comps) / M
    i3 = sum(c[2] for c in comps)
    i1 = sum(i + m * z * z for m, z, _, i in comps)  # 先を通る横の軸へ平行軸の定理で移す
    return 2 * math.sqrt(M * G * l * i1) / i3, l


def screen_moment(p):
    """車屏風が前の面の下の縁のまわりに受けるモーメント（g·mm）: (屏風が後ろへ戻す側, 車が前へ倒す側)。
    奥へ向かって x を測り、前の面を x = 0 にする。屏風の 1・2 の面は奥の x = box_depth、3 の面は真ん中。"""
    sigma = 1e-6 * p["paper_gsm"]
    w, H, b = p["panel_w"], p["panel_h"], p["box_depth"]
    back = 2 * w * H * sigma * b + b * H * sigma * b / 2
    _, md, _ = top_masses(p)
    front = md * (p["wheel_gap"] + p["layers"] * thickness(p) / 2)
    return back, front


def disc_com_offset(p):
    """刷る円盤（輪郭と穴）の重心と、穴の中心の距離（mm）。穴が中心からずれると重心が軸から外れる。"""
    q = _disc_part(p, 0)
    x, y, r = q.holes[0]
    shape = Polygon(q.outline, [Point(x, y).buffer(r, 32).exterior.coords])
    c = shape.centroid
    return math.hypot(c.x - x, c.y - y)


def _wheel_floors(p):
    out = []
    R = wheel_radius(p)
    slack = p["hole_d"] - p["axle_d"]
    if slack < MIN_SLACK:
        out.append(Failure("F5.spin", "軸の穴", f"穴 {p['hole_d']}mm と軸 {p['axle_d']}mm の隙間が {MIN_SLACK}mm 無く、紙が軸を締めて回らない"))
    need = need_spacer(p)
    if p["spacer"] < need:
        out.append(Failure("F5.spin", "羽", f"羽と柄の間 {p['spacer']}mm が、羽の傾き {wobble_deg(p):.1f}° で柄に寄る分を見た {need:.1f}mm に足りず、羽が柄に当たる"))
    if p["stick_length"] - AXLE_FROM_TOP - R < GRIP:
        out.append(Failure("F5.spin", "柄", f"軸から下の柄 {p['stick_length'] - AXLE_FROM_TOP}mm が羽の半径 {R:.0f}＋持つ所 {GRIP} に足りず、羽が手に当たる"))
    if p["kind"] == "pinwheel":
        if p["uncut"] - p["hole_d"] / 2 < HOLE_MARGIN:
            out.append(Failure("F5.spin", "中心の穴", f"切り込みの終わりから中心の穴まで {p['uncut'] - p['hole_d'] / 2:.1f}mm で、{HOLE_MARGIN}mm 無く裂けやすい"))
        flap = R - p["uncut"]
        if flap < tip_hole_dist(p) + p["hole_d"] / 2 + HOLE_MARGIN:
            out.append(Failure("F5.spin", "角の穴", f"切り込み {flap:.1f}mm が短く、角の穴を辺から {HOLE_MARGIN}mm 離して置けない"))
    else:
        if p["hub_r"] - p["hole_d"] / 2 < HOLE_MARGIN:
            out.append(Failure("F5.spin", "中心の穴", f"中心の円の縁まで {p['hub_r'] - p['hole_d'] / 2:.1f}mm で、{HOLE_MARGIN}mm 無く裂けやすい"))
        half = p["vane"] / math.sqrt(2)
        # 隣の羽との間は、刷る菱形どうしの実際の距離で見る。対角線の幅（2·half）を中心の間と比べると、菱形は隣へ向けて
        # half·cos22.5° しか張り出さないので、重ならない寸法まで落としていた。
        _, vanes, _ = _star_outline(p)
        gap = vanes[0].distance(vanes[1])
        if gap < VANE_GAP:
            out.append(Failure("F5.spin", "羽", f"隣の羽との間が {gap:.1f}mm で {VANE_GAP}mm 無く、羽が重なるか、ねじると当たる"))
        free = p["vane_radius"] - half - p["hub_r"]
        if free < TWIST_LEN * p["spoke_w"]:
            out.append(Failure("F5.spin", "腕", f"腕の長さ {free:.1f}mm が幅の {TWIST_LEN} 倍に足りず、羽をねじると折れ目が付く"))
    return out


def _top_floors(p):
    out = []
    off = disc_com_offset(p)
    if off > COM_TOL:
        out.append(Failure("F5.spin", "円盤", f"円盤の重心が軸から {off:.1f}mm 外れ（{COM_TOL}mm まで）、ぶれて跳ねる"))
    w, l = top_omega_min(p)
    if w > OMEGA_HAND * SLEEP_RATIO:
        _, md, ms = top_masses(p)
        out.append(Failure("F5.spin", "独楽", f"倒れずに回るのに {w:.0f}rad/s 要り、指で回す見込み {OMEGA_HAND:.0f} の {SLEEP_RATIO} 倍を超える"
                                          f"（重心の高さ {l:.1f}mm・円盤 {md:.2f}g・軸 {ms:.2f}g）"))
    tilt = math.degrees(math.atan2(_tip(p), _r(p)))
    if tilt < MIN_TILT_DEG:
        out.append(Failure("F5.spin", "下の軸", f"下の軸 {_tip(p)}mm では {tilt:.1f}° 傾くと円盤の縁が床に付く（{MIN_TILT_DEG}° まで要る）"))
    if p["grip"] < MIN_GRIP_TOP:
        out.append(Failure("F5.spin", "上の軸", f"上の軸 {p['grip']}mm が {MIN_GRIP_TOP}mm 無く、指でひねれない"))
    if _r(p) - p["hole_offset"] - p["axle_d"] / 2 < HOLE_MARGIN:
        out.append(Failure("F5.spin", "円盤の穴", "穴が円盤の縁に近すぎる"))
    return out


def _cone_floors(p):
    out = [f for f in _top_floors(p) if f.where != "下の軸"]
    a, g = cone_angles(p)
    if a + g > 2 * math.pi - 0.05:
        out.append(Failure("F5.spin", "円錐", f"円錐が平らすぎ、扇形 {math.degrees(a):.0f}° に糊代 {math.degrees(g):.0f}° を足すと一回りを超える"))
    tilt = math.degrees(math.atan2(_tip(p) + p["cone_h"], _r(p)))
    if tilt < MIN_TILT_DEG:
        out.append(Failure("F5.spin", "下の軸", f"{tilt:.1f}° 傾くと円盤の縁が床に付く（{MIN_TILT_DEG}° まで要る）"))
    return out


def _screen_floors(p):
    out = []
    R, b = _r(p), p["box_depth"]
    slack = p["hole_d"] - p["axle_d"]
    if slack < MIN_SLACK:
        out.append(Failure("F5.spin", "軸の穴", f"穴 {p['hole_d']}mm と軸 {p['axle_d']}mm の隙間が {MIN_SLACK}mm 無く、紙が軸を締めて回らない"))
    tilt = math.degrees(math.atan2(max(slack, 0), b))
    need = R * math.sin(math.radians(tilt)) + MIN_CLEAR
    if p["wheel_gap"] < need:
        out.append(Failure("F5.spin", "車", f"車と前の面の間 {p['wheel_gap']}mm が、車の傾き {tilt:.1f}° を見た {need:.1f}mm に足りず、車が面に当たる"))
    if R + MIN_CLEAR > p["panel_h"] / 2:
        out.append(Failure("F5.spin", "車", f"車の半径 {R}＋{MIN_CLEAR} が軸の高さ {p['panel_h'] / 2:g}mm を超え、車が机に当たる"))
    back, front = screen_moment(p)
    if front > back:
        out.append(Failure("F5.spin", "屏風", f"車の重さで前へ倒す {front:.0f}g·mm が、屏風の戻す {back:.0f}g·mm を超え、屏風が前へ倒れる"))
    out += [f for f in _top_floors(p) if f.where == "円盤"]
    return out


def check_physics(p):
    k = p["kind"]
    if k == "top":
        return _top_floors(p)
    if k == "cone":
        return _cone_floors(p)
    if k == "screen":
        return _screen_floors(p)
    return _wheel_floors(p)


# ---- 部品 ----

def _circle(cx, cy, r, n=64):
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def _poly_art(geom, fill, stroke=None, sw=0):
    """shapely の面を絵の面にする。切れて 2 つ以上になった時は全部描く。"""
    out = []
    for g in getattr(geom, "geoms", [geom]):
        if g.is_empty or g.geom_type != "Polygon":
            continue
        item = {"kind": "poly", "pts": [(round(x, 3), round(y, 3)) for x, y in g.exterior.coords[:-1]], "fill": fill}
        if stroke:
            item.update(stroke=stroke, sw=sw)
        out.append(item)
    return out


def _pinwheel_part(p):
    S, u = p["square"], p["uncut"]
    c = S / 2
    k = u / math.sqrt(2)
    # 角ごとに、辺から切り込みの終わりへ入って戻る細い V。角の順は (0,0)→(S,0)→(S,S)→(0,S)。
    ends = {(0, 0): (c - k, c - k), (S, 0): (c + k, c - k), (S, S): (c + k, c + k), (0, S): (c - k, c + k)}
    w = NOTCH
    pts = [(0, w), ends[(0, 0)], (w, 0),
           (S - w, 0), ends[(S, 0)], (S, w),
           (S, S - w), ends[(S, S)], (S - w, S),
           (w, S), ends[(0, S)], (0, S - w)]
    body = Polygon(pts)
    # 1 つおきの角に穴。どの三角も同じ回りの向きの角を選ぶ（向きがそろわないと風を受けても打ち消し合う）。
    a = tip_hole_dist(p)
    tips = [((S, 0), (-1, 0)), ((S, S), (0, -1)), ((0, S), (1, 0)), ((0, 0), (0, 1))]
    holes = [(c, c, p["hole_d"] / 2)]
    for (x, y), (ex, ey) in tips:
        dx, dy = (c - x) / math.hypot(c - x, c - y), (c - y) / math.hypot(c - x, c - y)
        bx, by = ex + dx, ey + dy
        n = math.hypot(bx, by)
        holes.append((x + a * bx / n, y + a * by / n, p["hole_d"] / 2))
    # 絵: 4 つの三角を辺の真ん中で 2 つに分けた 8 枚を、金と白で交互に塗る。コマ 14 左の 8 枚の羽の先が橙なので、外の辺の帯を橙にする。
    inner = body.buffer(-0.4, join_style=2)
    corners = [(0, 0), (S, 0), (S, S), (0, S)]
    art = []
    for i in range(4):
        (x0, y0), (x1, y1) = corners[i], corners[(i + 1) % 4]
        mid = ((x0 + x1) / 2, (y0 + y1) / 2)
        for j, half in enumerate(([(x0, y0), mid, (c, c)], [mid, (x1, y1), (c, c)])):
            tri = Polygon(half).intersection(inner)
            art += _poly_art(tri, GOLD if j == 0 else CREAM)
            if j == 0:
                continue
            # 橙は軸へ寄せる角（穴のある半分）の外の帯だけ。図の羽の先の橙は羽の長さの 3 割ほど（目測）。
            # 寄せる角が色で分かるので、組む時に 1 つおきを数え間違えにくい。
            band = Polygon([(x0, y0), (x1, y1), (x1 + (c - x1) * 0.24, y1 + (c - y1) * 0.24), (x0 + (c - x0) * 0.24, y0 + (c - y0) * 0.24)])
            art += _poly_art(tri.intersection(band), ORANGE)
    # 中心の飾りの丸。図の羽の中心の点を写した。穴より外。
    ring = p["hole_d"] / 2 + 2.2
    art += _poly_art(Point(c, c).buffer(ring, 24).difference(Point(c, c).buffer(p["hole_d"] / 2 + 1.2, 24)).intersection(inner), INK)
    art += _bend_marks(holes[1:], tips, c, ring)
    return Part(1, "vanes", "羽", pts, label_xy=(c - 3, 3), label="1 羽", holes=holes, art=art)


def _bend_marks(tip_holes, tips, c, ring):
    """軸へ寄せる角ごとの曲げる印。角の穴のすぐ外から中心の穴へ向かう点の線（位置の印の形）と、矢じりの片側。

    ワークショップの型紙レビューの指摘から採った案（EP-0010、2026-11-06）: 切った後にどこをどう曲げるのかが紙から読めなかった。
    角は曲げるだけで折り目を付けないので、折り線は刷らない（刷ると折る所と読まれる）。線は中心の飾りの輪の手前で止める
    （塗りに重ねると読めない）。線は角の切り込み（V）に沿って中心へ向かうので、矢じりは切り込みと反対の側にだけ付ける
    （両側に付けると、切り残しの小さい寸法で切り込みにかかる）。矢じりは 3.5mm（点の線なので、2.5mm では刷った絵を 400dpi で見ても読みにくかった）。
    """
    out = []
    for (hx, hy, r), ((x, y), _) in zip(tip_holes, tips):
        d = math.hypot(c - hx, c - hy)
        ux, uy = (c - hx) / d, (c - hy) / d
        start = (hx + ux * (r + 1.2), hy + uy * (r + 1.2))
        end = (c - ux * (ring + 1.5), c - uy * (ring + 1.5))
        # 切り込みは中心から角への線の上にある。矢じりの先の 2 つの向き（線の左右）のうち、その線から遠い方へ開く。
        # 前は外積の符号で向きを決めていて、符号を取り違えて切り込みの側へ開いていた（別の系統の検品の指摘）。距離で選べば取り違えない
        cut = LineString([(c, c), (x, y)])
        cs, sn = math.cos(math.radians(30)), math.sin(math.radians(30))
        tips_ = [(end[0] + 3.5 * (-ux * cs - k * uy * sn), end[1] + 3.5 * (-uy * cs + k * ux * sn)) for k in (1, -1)]
        head = max(tips_, key=lambda pt: cut.distance(Point(pt)))
        out += [{"kind": "mark", "pts": [start, end], "mark": "bend"},
                {"kind": "mark", "pts": [end, head], "mark": "bend_head"}]
    return out


def _star_outline(p):
    R = wheel_radius(p)
    a, rv, sw, hr = p["vane"], p["vane_radius"], p["spoke_w"], p["hub_r"]
    half = a / math.sqrt(2)
    shapes = [Point(R, R).buffer(hr, 32)]
    vanes = []
    for i in range(8):
        t = 2 * math.pi * i / 8 - math.pi / 2
        ux, uy, vx, vy = math.cos(t), math.sin(t), -math.sin(t), math.cos(t)
        cx, cy = R + rv * ux, R + rv * uy
        # 図の羽は菱形（対角線が腕の向き）。
        dia = Polygon([(cx + half * ux, cy + half * uy), (cx + half * vx, cy + half * vy), (cx - half * ux, cy - half * uy), (cx - half * vx, cy - half * vy)])
        r0 = hr - 1
        spoke = Polygon([(R + r0 * ux + sw / 2 * vx, R + r0 * uy + sw / 2 * vy), (cx + sw / 2 * vx, cy + sw / 2 * vy),
                         (cx - sw / 2 * vx, cy - sw / 2 * vy), (R + r0 * ux - sw / 2 * vx, R + r0 * uy - sw / 2 * vy)])
        shapes += [dia, spoke]
        vanes.append(dia)
    return unary_union(shapes), vanes, R


def _square_part(p):
    shape, vanes, R = _star_outline(p)
    if shape.geom_type != "Polygon":
        # 羽が重なると 1 つの輪郭にならない。床（F5.spin）が羽の重なりで落とすので、ここでは外の殻で描くだけにする。
        shape = shape.convex_hull
    pts = [(round(x, 3), round(y, 3)) for x, y in shape.exterior.coords[:-1]]
    inner = Polygon(pts).buffer(-0.35, join_style=2)
    art = _poly_art(Point(R, R).buffer(p["hub_r"] - 0.4, 32).intersection(inner), GOLD)
    for i, v in enumerate(vanes):
        # 図の羽は薄茶と薄紅が混じる。交互に塗る。
        art += _poly_art(v.buffer(-0.4, join_style=2).intersection(inner), GOLD if i % 2 else "#d9a58c", INK, 0.25)
    top = vanes[0].centroid
    return Part(1, "star", "羽", pts, label_xy=(top.x - 1, top.y - 1.7), label="1", holes=[(R, R, p["hole_d"] / 2)], art=art)


HUB_DISC = 8  # 四角の羽の前の座金の半径。穴の余白 HOLE_MARGIN を取れる大きさ


def _washer_part(p):
    r = HUB_DISC
    return Part(2, "washer", "座金", _circle(r, r, r, 32), label_xy=(r - 1, 0.8), label="2", holes=[(r, r, p["hole_d"] / 2)],
                art=_poly_art(Polygon(_circle(r, r, r - 0.4, 32)), GOLD))


# 円盤の絵の輪（半径に対する比と色）。独楽はコマ 26 左の黄土の地に橙の輪（目測で 0.72〜0.62 と 0.4〜0.3）、
# 円錐の独楽はコマ 29 右の茶の胴に明るい帯、車屏風はコマ 25 左の車の黄土に中心の白い輪。
RINGS = {"top": ((1, GOLD), (0.72, ORANGE), (0.62, GOLD), (0.40, ORANGE), (0.30, GOLD)),
         "cone": ((1, BROWN), (0.85, TAN), (0.75, BROWN), (0.45, TAN), (0.35, BROWN)),
         "screen": ((1, GOLD), (0.45, CREAM), (0.30, GOLD))}


def _disc_first(p):
    """円盤の 1 枚目の部品番号。車屏風は 1 が屏風なので 2 から。"""
    return 2 if p["kind"] == "screen" else 1


def _disc_part(p, i):
    r = _r(p)
    hole = (r + p["hole_offset"], r, p["axle_d"] / 2)
    art = []
    if i in (0, p["layers"] - 1):
        # 表と裏に見える 1 枚目と最後の 1 枚だけ塗る。
        for k, col in RINGS.get(p["kind"], RINGS["top"]):
            art += _poly_art(Polygon(_circle(r, r, r - 0.4 if k == 1 else k * r, 64)), col)
    n = i + _disc_first(p)
    name = "車" if p["kind"] == "screen" else "円盤"
    return Part(n, f"disc{LAYER_KEYS[i]}", f"{name} {i + 1} 枚目", _circle(r, r, r, 96), label_xy=(r - 1.2, 1.5), label=str(n), holes=[hole], art=art)


def _arc(r, a0, a1, cx, cy, n=48):
    return [(cx + r * math.cos(a0 + (a1 - a0) * j / n), cy + r * math.sin(a0 + (a1 - a0) * j / n)) for j in range(n + 1)]


def _cone_part(p):
    """円錐の扇形。内の弧は丸めた時に軸が通る口（半径が軸の半分）になる長さ。糊代は扇形の終わりに続けて取り、丸めて重ねる。"""
    s, R = cone_slant(p), _r(p)
    a, g = cone_angles(p)
    # 平らすぎて一回りを超える寸法は床（F5.spin の「円錐」）が落とす。その時も絵の検査が別の理由で連鎖して落ちないよう、
    # 描く扇形は一回りの手前で止める（羽が重なる四角の羽を外の殻で描くのと同じ考え）。
    tot = min(a + g, 2 * math.pi - 0.05)
    a = min(a, tot - 0.02)
    g = tot - a
    ri = p["axle_d"] / 2 * s / R
    # 扇形の向き: 開いた所が上に来るよう、真上（−90°）を挟んで置く。
    a0 = -math.pi / 2 + (2 * math.pi - a - g) / 2
    a1, a2 = a0 + a, a0 + a + g
    pts = _arc(s, a0, a2, 0, 0, 96) + _arc(ri, a2, a0, 0, 0, 12)
    pts = [(x + s, y + s) for x, y in pts]
    glue = [(x + s, y + s) for x, y in _arc(s, a1, a2, 0, 0, 8) + _arc(ri, a2, a1, 0, 0, 4)]
    body = Polygon(pts)
    inner = body.buffer(-0.4, join_style=2).difference(Polygon(glue).buffer(0.5, join_style=2))
    art = _poly_art(inner, BROWN)
    # 帯: 丸めると円錐の横の輪になる弧。図の胴の帯は 4 本ほど（目測）。
    for k in (0.45, 0.62, 0.79, 0.93):
        r = ri + (s - ri) * k
        m = 1.0 / r  # 弧の端を糊代と輪郭から 1mm 離す
        arc = [(x + s, y + s) for x, y in _arc(r, a0 + m, a1 - m, 0, 0, 64)]
        art.append({"kind": "line", "pts": arc, "stroke": TAN, "sw": 0.9})
    lx, ly = s + (ri + (s - ri) * 0.3) * math.cos(a0 + a / 2), s + (ri + (s - ri) * 0.3) * math.sin(a0 + a / 2)
    n = int(p["layers"]) + 1
    return Part(n, "cone", "胴（円錐）", pts, label_xy=(lx - 1, ly - 1.7), label=str(n), glue=[glue], art=art)


def _screen_part(p):
    """屏風。左から 1 の面（翼）・2 の面（奥の壁）・3 の面（横の壁、幅は奥行き）・4 の面（前の壁）。
    2 と 4 を向かい合わせにコの字に折ると、2 つの穴が同じ高さで、3 の面からの距離も同じになる。"""
    w, H, b = p["panel_w"], p["panel_h"], p["box_depth"]
    xs = [0, w, 2 * w, 2 * w + b, 3 * w + b]
    pts = [(0, 0), (xs[4], 0), (xs[4], H), (0, H)]
    hy = H / 2
    holes = [(xs[2] - w / 2, hy, p["hole_d"] / 2), (xs[3] + w / 2, hy, p["hole_d"] / 2)]
    valley = [((xs[2], 0), (xs[2], H)), ((xs[3], 0), (xs[3], H))]
    mountain = [((xs[1], 0), (xs[1], H))]
    art = []
    for i in range(4):
        art.append({"kind": "poly", "pts": [(xs[i] + 0.6, 0.6), (xs[i + 1] - 0.6, 0.6), (xs[i + 1] - 0.6, H - 0.6), (xs[i] + 0.6, H - 0.6)], "fill": GOLD})
    # 1 の面の四角の重ね模様（図の左の面）。
    cx, cy = w / 2, H / 2
    for k, col in ((0.36, INK), (0.33, GOLD), (0.24, CREAM), (0.16, GOLD), (0.08, CREAM)):
        e = w * k
        art.append({"kind": "poly", "pts": [(cx - e, cy - e), (cx + e, cy - e), (cx + e, cy + e), (cx - e, cy + e)], "fill": col})
    # 4 の面の穴のまわりの輪（図の前の面の丸い窓）。車の位置の目印。
    hx = holes[1][0]
    # 絵の面は外の輪郭しか持たないので、輪は墨の円の上に地の色の円を重ねて描く。
    rr = min(w / 2, H / 2) - 3
    art += [{"kind": "poly", "pts": _circle(hx, hy, rr, 48), "fill": INK}, {"kind": "poly", "pts": _circle(hx, hy, rr - 1, 48), "fill": GOLD}]
    return Part(1, "screen", "屏風", pts, label_xy=(2, 2), label="1 屏風", valley=valley, mountain=mountain, holes=holes, art=art)


def _clear_holes(q):
    """絵の面から穴の円（と縁の 0.5mm）を抜く。穴の線は絵の上に墨で刷るので、穴の上に濃い塗りがあると穴が見えなくなる。
    絵の面は外の輪郭しか持てないので、抜いて輪になった面は穴の中心を通る縦の線で 2 つに分けて描く。"""
    if not q.holes:
        return q
    cut = unary_union([Point(x, y).buffer(r + 0.5, 32) for x, y, r in q.holes])
    art = []
    for item in q.art:
        if item["kind"] != "poly":
            art.append(item)
            continue
        geom = Polygon(item["pts"]).buffer(0).difference(cut)
        pieces, todo = [], [g for g in getattr(geom, "geoms", [geom]) if g.geom_type == "Polygon" and not g.is_empty]
        while todo:
            g = todo.pop()
            if not g.interiors:
                pieces.append(g)
                continue
            # 抜いた穴の 1 つの中心を通る縦の線で分ける。1 つの面に穴が 2 つ以上あれば、分けた片をまた見る。
            x = Polygon(g.interiors[0]).centroid.x
            x0, y0, x1, y1 = g.bounds
            for half in (box(x0 - 1, y0 - 1, x, y1 + 1), box(x, y0 - 1, x1 + 1, y1 + 1)):
                part = g.intersection(half)
                todo += [h for h in getattr(part, "geoms", [part]) if h.geom_type == "Polygon" and not h.is_empty]
        for g in pieces:
            new = {k: v for k, v in item.items() if k != "pts"}
            new["pts"] = [(round(x, 3), round(y, 3)) for x, y in g.exterior.coords[:-1]]
            art.append(new)
    q.art = art
    return q


def parts(p):
    return [_clear_holes(q) for q in _parts(p)]


def _parts(p):
    k = p["kind"]
    if k == "pinwheel":
        return [_pinwheel_part(p)]
    if k == "square":
        return [_square_part(p), _washer_part(p)]
    discs = [_disc_part(p, i) for i in range(int(p["layers"]))]
    if k == "cone":
        return discs + [_cone_part(p)]
    if k == "screen":
        return [_screen_part(p)] + discs
    return discs


def place(by_key, page, top, gap):
    """部品を左から並べ、入らなければ次の行へ送る。文字は部品の下に全幅で置く。"""
    x, y, row = page.x0, top, 0.0
    for q in by_key.values():
        if x > page.x0 and x + q.width > page.x1:
            x, y, row = page.x0, y + row + gap, 0.0
        q.x, q.y = x, y
        x += q.width + gap
        row = max(row, q.height)
    return y + row + gap, page.x1 - page.x0, page.x0


# ---- 部品表・組み方 ----

def bom(p):
    paper = paper_name(gsm=p['paper_gsm'])
    why = "家庭のプリンタで刷って作るため"
    k = p["kind"]
    if k in ("top", "cone", "screen"):
        n = int(p["layers"])
        first = _disc_first(p)
        name = "車" if k == "screen" else "円盤"
        guess = {"top": "木（推定。図の円盤の輪は木地の塗りに見える）", "cone": "銭か木（推定。銭独楽の名と、図の茶の胴から）",
                 "screen": "木（推定。図の車の黄土の色から）"}[k]
        rows = [{"number": first + i, "key": f"disc{LAYER_KEYS[i]}", "name": f"{name} {i + 1} 枚目（{n} 枚重ねる）", "qty": 1, "material": paper,
                 "substituted": True, "original_guess": guess, "reason": f"{why}。1 枚では軽いので {n} 枚を重ねて貼る"}
                for i in range(n)]
        if k == "cone":
            rows.append({"number": n + 1, "key": "cone", "name": "胴（円錐）", "qty": 1, "material": paper, "substituted": True,
                         "original_guess": "不明（図の胴の帯は塗りか、重ねた物の境か読めない）", "reason": why})
        if k == "screen":
            rows.insert(0, {"number": 1, "key": "screen", "name": "屏風", "qty": 1, "material": paper, "substituted": True,
                            "original_guess": "紙を貼った木の枠（推定。屏風の作りから）", "reason": why})
            L = axle_length(p)
            rows.append({"number": 20, "key": "axle", "name": "軸", "qty": 1, "material": f"竹串（太さ {p['axle_d']:g}mm・長さ約 {L:.0f}mm に切り、先を落とす）",
                         "substituted": True, "original_guess": "木の棒（推定。図の糸を巻いた棒）", "reason": "家にあり、まっすぐで穴に通しやすいため"})
            rows.append({"number": 21, "key": "string", "name": "糸", "qty": 1, "material": "たこ糸（約 400mm）", "substituted": True,
                         "original_guess": "糸（図の通り。素材は読めない）", "reason": "家にあり、軸に巻きやすいため"})
            rows.append({"number": 22, "key": "stop", "name": "止め", "qty": 1, "material": "セロハンテープ（軸の両端に巻く）", "substituted": True,
                         "original_guess": "不明", "reason": "軸が屏風から抜けないようにするため"})
            return rows
        L = top_stick_length(p)
        stick = f"爪楊枝（長さ約 {L:.0f}mm）" if p["axle_d"] <= 2.2 and L <= 60 else f"竹串（太さ {p['axle_d']:g}mm・長さ約 {L:.0f}mm に切る）"
        rows.append({"number": 20, "key": "axle", "name": "軸", "qty": 1, "material": stick, "substituted": True,
                     "original_guess": "不明（図の細い棒の素材は読めない）", "reason": "家にあり、まっすぐで円盤の穴に固く通るため"})
        return rows
    if k == "pinwheel":
        rows = [{"number": 1, "key": "vanes", "name": "羽", "qty": 1, "material": paper, "substituted": True,
                 "original_guess": "紙（推定。図の羽の色は紙の色に見える）", "reason": why}]
    else:
        rows = [{"number": 1, "key": "star", "name": "羽", "qty": 1, "material": paper, "substituted": True, "original_guess": "紙（推定。同じ）", "reason": why},
                {"number": 2, "key": "washer", "name": "座金", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明（図の中心の筒）",
                 "reason": "羽が軸に対して傾かないよう、2 か所で軸に載せるため"}]
    rows += [
        {"number": 20, "key": "axle", "name": "軸", "qty": 1, "material": f"竹串（太さ {p['axle_d']:g}mm・長さ約 {axle_length(p):.0f}mm に切り、先を落とす）",
         "substituted": True, "original_guess": "不明（図の細い棒の素材は読めない）", "reason": "家にあり、まっすぐで穴に通しやすいため"},
        {"number": 21, "key": "stick", "name": "柄", "qty": 1, "material": f"ストロー（長さ約 {p['stick_length']}mm）", "substituted": True,
         "original_guess": "竹（推定。図の長い棒の節の無い色から）", "reason": "竹串を横に刺して通せるため"},
        {"number": 22, "key": "spacer", "name": "間の筒", "qty": 2, "material": f"ストローの切れ端（{p['spacer']}mm と {p['bearing']}mm）", "substituted": True,
         "original_guess": "不明", "reason": "羽を柄から離し、2 か所の穴の間を保つため"},
        {"number": 23, "key": "stop", "name": "止め", "qty": 1, "material": "セロハンテープ（軸の先に巻く）", "substituted": True, "original_guess": "不明", "reason": "家にあり、羽が抜けないようにするため"},
    ]
    return rows


def materials(p):
    by = {r["key"]: r for r in bom(p)}
    first = by.get("vanes") or by.get("star") or by.get("screen") or by["disca"]
    out = [f"{first['material']}を 1 枚", "のり、はさみ、定規", by["axle"]["material"]]
    if p["kind"] in ("pinwheel", "square"):
        out += [by["stick"]["material"], by["spacer"]["material"], by["stop"]["material"]]
    if p["kind"] == "screen":
        out += [by["string"]["material"], by["stop"]["material"]]
    return out


def steps(p):
    out = ["刷った物差しに定規を当て、10cm か確かめる"]
    k = p["kind"]
    if k == "screen":
        n = int(p["layers"])
        # 面は左から数えて呼ぶ。部品番号（車は 2 から）と取り違えないよう、番号だけでは書かない。
        out += ["1 屏風を実線で切り、2 つの穴を竹串の先であける", "屏風の 2 本の谷折りの線を直角に折り、穴のある 2 枚の面を向かい合わせ（コの字）にする",
                "左の端の面との境を山折りし、左の端の面を翼にして立てる",
                f"車を {n} 枚切り、穴をそろえて重ねて貼る", "竹串を奥の面の穴から前の面（丸い輪の面）の穴へ通す",
                f"前の面の外に {p['wheel_gap']}mm 空けて車を竹串に通し、のりで止める。両端にテープを巻く",
                "コの字の中で糸の端を竹串に結び、10 回ほど巻く", "屏風を手で押さえ、糸をまっすぐ引いて車を回す"]
        return out
    if k == "cone":
        n = int(p["layers"])
        out += [f"円盤を {n} 枚とも切り、穴をそろえて重ねて貼る", f"{n + 1} 胴を切り、糊代に重ねて貼って円錐にする（先の小さな口は残す）",
                "円錐の縁に円盤を貼る", f"竹串を円盤の穴から円錐の口へ通し、口から {_tip(p)}mm 出してのりで止める",
                "横から見て、軸がまっすぐか確かめる", "上の軸を指でひねって回す"]
        return out
    if k == "top":
        n = int(p["layers"])
        out += [f"円盤を {n} 枚とも実線で切る", "1 枚目の穴に竹串の先で穴をあけ、残りの円盤も穴を重ねてあける",
                f"{n} 枚を穴をそろえて重ねて貼り、乾くまで本などで押さえる（反ると回らない）",
                f"軸を通し、円盤の下に {_tip(p)}mm、上に {p['grip']}mm 出して、穴の所をのりで止める",
                "円盤が軸に直角か、横から見て確かめる", "上の軸を指でひねって回す"]
        return out
    if k == "pinwheel":
        out += ["1 羽を外の線で切る。角の切り込みは V の線を中心の手前まで切る", "穴を 5 つ竹串の先であける"]
    else:
        out += ["1 羽と 2 座金を切る。腕は細いので、はさみをゆっくり進める", "穴を竹串の先であける",
                f"8 本の腕を、根元から同じ向きに約 {TWIST_DEG}° ねじる"]
    out += [f"柄のストローの上の端から {AXLE_FROM_TOP}mm の所に竹串を横に刺し通す", f"竹串に {p['spacer']}mm のストローを通す"]
    if k == "pinwheel":
        out += ["羽の表（色を刷った面）を竹串の先の側に向けて、羽の中心の穴を竹串に通す", f"{p['bearing']}mm のストローを通す",
                "橙の帯のある 4 つの角を、刷った点の線の矢じりの向きに表の側へ順に曲げて中心に寄せ、角の穴を竹串に通す（折り目を付けない）"]
    else:
        out += ["1 羽の中心の穴を竹串に通す", f"{p['bearing']}mm のストローを通し、2 座金を通す"]
    out += ["竹串の先にテープを巻いて止める。羽が軽く回るか確かめる", "息を吹きかけるか、持って走る"]
    return out


RESULTS = ("回った", "回らない")


def measures(p):
    """回るかの二択でなく、回り方を言葉か絵で予想する（ほかの雛形と同じ）。"""
    if p["kind"] in ("top", "cone"):
        return {"predict": "独楽はどう回ると思いますか（言葉か絵で）", "rows": [[("回した手（指・両手）", 40)]]}
    if p["kind"] == "screen":
        return {"predict": "糸を引くと車はどう回ると思いますか（言葉か絵で）", "rows": [[("引いた速さ（ゆっくり・速く）", 40)]]}
    return {"predict": "羽はどう回ると思いますか（言葉か絵で）", "rows": [[("風にした物（息・団扇・走る）", 40)]]}


def diagram(x, y, w, h, p):
    """横から見た組み上がりの並び。寸法の図ではなく、部品の並びを見せるだけの絵。"""
    if p["kind"] == "screen":
        b, H, R = p["box_depth"], p["panel_h"], _r(p)
        s = min(w / (b + p["wheel_gap"] + 6), h / (H + 2))
        x0, base = x + 2, y + h - 1
        front = x0 + b * s
        wheel = front + p["wheel_gap"] * s
        return [{"kind": "rect", "x": x0, "y": base - H * s, "w": b * s, "h": H * s},
                {"kind": "line", "x1": x0 - 1, "y1": base - H * s / 2, "x2": wheel + 3, "y2": base - H * s / 2},
                {"kind": "line", "x1": wheel, "y1": base - H * s / 2 - R * s, "x2": wheel, "y2": base - H * s / 2 + R * s}]
    if p["kind"] == "cone":
        r, tip, hc, grip = _r(p), _tip(p), p["cone_h"], p["grip"]
        s = min(w / (2 * r + 4), h / (tip + hc + grip + 4))
        cx, base = x + w / 2, y + h - 2
        rim = base - (tip + hc) * s
        return [{"kind": "line", "x1": cx, "y1": base, "x2": cx, "y2": rim - grip * s},
                {"kind": "line", "x1": cx, "y1": base - tip * s, "x2": cx - r * s, "y2": rim},
                {"kind": "line", "x1": cx, "y1": base - tip * s, "x2": cx + r * s, "y2": rim},
                {"kind": "rect", "x": cx - r * s, "y": rim - 1, "w": 2 * r * s, "h": 1}]
    if p["kind"] == "top":
        r, tip, grip = _r(p), _tip(p), p["grip"]
        s = min(w / (2 * r + 4), h / (tip + grip + 4))
        cx, base = x + w / 2, y + h - 2
        dh = max(p["layers"] * thickness(p) * s, 0.6)
        disc_y = base - tip * s - dh
        return [{"kind": "line", "x1": cx, "y1": base, "x2": cx, "y2": disc_y - grip * s},
                {"kind": "rect", "x": cx - r * s, "y": disc_y, "w": 2 * r * s, "h": dh}]
    R = wheel_radius(p)
    s = min(w / (STRAW_D + p["spacer"] + p["bearing"] + 12), h / (2 * R + 4))
    stick_x, cy = x + 4 * s, y + h / 2
    face = stick_x + (STRAW_D + p["spacer"]) * s
    return [{"kind": "rect", "x": stick_x, "y": cy - AXLE_FROM_TOP * s, "w": STRAW_D * s, "h": y + h - (cy - AXLE_FROM_TOP * s)},
            {"kind": "line", "x1": stick_x, "y1": cy, "x2": face + (p["bearing"] + FRONT_STOP) * s, "y2": cy},
            {"kind": "line", "x1": face, "y1": cy - R * s, "x2": face, "y2": cy + R * s},
            {"kind": "line", "x1": face + p["bearing"] * s, "y1": cy - 2, "x2": face + p["bearing"] * s, "y2": cy + 2, "dash": "1,0.6"}]
