"""雛形 pivot_counterweight: 箱の胴に軸を通し、重りで頭を揺らす。張子の首振り虎の仮説を試す。

頭の支え方は仮説の違いなので描き分ける（docs/process/research/12）。寸法は手元の複写の図の比から出した。
どの値も実物では未確認。Claude が変えてよいのは RANGES の名前の値だけ。
"""
import math

from shapely.geometry import LineString, Polygon

from ..model import Failure, Part
from ..textfit import text_width
from ..pivot_model import center, paper_mass, period_s, rest_tilt_deg

ID = "pivot_counterweight"
# 刷った組の版（U-31）。slider_fan.SHEET_SET と同じ意味。
# 仮説を分ける寸法の名前（words・generate が、仮説の寸法にこれがあるかを見る）。
HYP_KEY = "mount"
SHEET_SET = "tora-v4"
# 控えを残す前の組（凍結の床）。slider_fan.FROZEN_SET と同じ意味。
FROZEN_SET = "tora-v3"


def frozen():
    return SHEET_SET == FROZEN_SET


DEFAULTS = {
    "mount": "neck",
    "body_length": 64, "body_width": 28, "body_height": 54, "glue": 8,
    "ear_length": 12, "ear_height": 8, "axle_height": 42,
    "opening": 18, "neck_length": 14, "strip_width": 10,
    "head_w": 26, "head_h": 24,
    "weight_g": 3.0, "weight_below_axle": 28, "weight_behind": 1,
    # 紙の面密度は見込み。実物の紙を量ったら置き換える。
    "paper_gsm": 150,
}
RANGES = {
    "body_length": (40, 90), "body_width": (20, 40), "body_height": (30, 70), "glue": (5, 12),
    "ear_length": (6, 25), "ear_height": (5, 15), "axle_height": (15, 65),
    "opening": (10, 30), "neck_length": (5, 30), "strip_width": (5, 20),
    "head_w": (15, 45), "head_h": (15, 45),
    "weight_g": (0.2, 15), "weight_below_axle": (-20, 60), "weight_behind": (-10, 40),
    "paper_gsm": (40, 400),
}
MOUNTS = ("neck", "hang")
HOLE_MARGIN = 4  # 穴から紙の端までの見込み。これより狭いと裂けやすい
NECK_BACK = 6  # 首の形で、軸を前の壁の後ろに通す距離。部品の穴と揺れの検査が同じ値を使う
# 吊る形の帯: 帯の上の端から穴まで STRIP_HOLE、頭の上の端と帯の下の端を HEAD_OVERLAP 重ねて貼る。
# 帯の長さ＝STRIP_HOLE＋軸から頭の上の端まで＋HEAD_OVERLAP。式（axle_to_head_top）と刷る帯・手順が同じ数を指すように名前を付けた。
STRIP_HOLE = 6
HEAD_OVERLAP = 4
MIN_SWING = 10
MAX_TILT = 15
TIGER, STRIPE, RIM, MOUTH, EYE = "#b1a37a", "#3c3424", "#8d7745", "#553c24", "#666c53"
TITLES = {"neck": "首を胴の穴に入れる", "hang": "頭を前に吊る"}


def title(p):
    return TITLES[p["mount"]]


def spec():
    return {"template_id": ID, "defaults": DEFAULTS, "ranges": RANGES, "mount": MOUNTS}


def check_range(p):
    out = []
    for k, v in p.items():
        if k == "mount":
            if v not in MOUNTS:
                out.append(Failure("F5.range", k, f"{v} は {MOUNTS} のどれでもない"))
        elif k not in RANGES:
            out.append(Failure("F5.range", k, "知らない寸法の名前"))
        elif not isinstance(v, (int, float)) or isinstance(v, bool) or not RANGES[k][0] <= v <= RANGES[k][1]:
            out.append(Failure("F5.range", k, f"{v} は範囲 {RANGES[k]} の外"))
    return out


def mass_points(p):
    """揺れる部分の質量の点。紙の頭は重りより桁で軽い（research/12）。"""
    head_m = paper_mass(p["head_w"] * p["head_h"], p["paper_gsm"])
    if p["mount"] == "neck":
        head = (head_m, p["neck_length"] + 6, 0)
        strip = (paper_mass(2 * p["strip_width"] * (p["neck_length"] + 12), p["paper_gsm"]), p["neck_length"] / 2, 0)
    else:
        arm = axle_to_head_top(p)
        head = (head_m, 0, arm + p["head_h"] / 2)
        strip = (paper_mass(2 * p["strip_width"] * arm, p["paper_gsm"]), 0, arm / 2)
    return [head, strip, (p["weight_g"], -p["weight_behind"], p["weight_below_axle"])]


def axle_to_head_top(p):
    return 8


# 5 重りの腕の下の穴（EP-0011、作成動画 R-0004 の札から採った案。2026-11-06）。型紙エンジン（paper-to-toy の issue/tora-v4 1f4f0b1）と同じ形で、
# 必須 2 種の次の組（tora-v4）だけに入れる（前の組は紙を変えない）。穴は軸の穴から weight_below_axle 下（釣り合いの式の重りの位置）で、
# 粘土はこの穴の所に付けるか、穴に糸を通して玉を下げる。糸で下げた玉の重さは、糸を通した穴にかかる（糸は引く力しか伝えないので、
# 頭を傾ける力の腕は穴までの深さ）。なので釣り合いの式は変えず、糸の長さは玉が胴の底に当たるかだけに効く。
# 揺れの周期の見込み（period_s）は、玉を穴に固めた形のまま。糸で下げた玉は腕と別に揺れるので、その組み方では周期が合わない事がある
THREAD_R = 0.6  # 糸の穴の半径（御来迎の開く糸の穴と同じ）
CLAY_DENSITY = 1.8e-3  # 油粘土の密度 g/mm³（エンジンの弥次郎兵衛と同じ見込み）
HANG_MIN = 5  # 糸で下げる時の、穴から玉の上までの長さの下限 mm。これより短いと糸を結ぶ間が無いので、下げる形を出さない
LOWER_HOLE_MIN = 1.0 + THREAD_R + 2  # 下の穴を開ける weight_below_axle の下限（軸の穴との間に紙を 2mm 残す）
# 粘土の玉の上の端から軸の中心までに残す余り。玉の真ん中は軸の下 clay_r + AXLE_CLEAR 以上（浅い重りで、重い玉が軸の竹串にかかる寸法を落とす）
AXLE_CLEAR = 2.0


def clay_r(g):
    """粘土の玉の半径 mm。"""
    return (3 * g / (4 * math.pi * CLAY_DENSITY)) ** (1 / 3)


def hang_thread_mm(p):
    """次の組の首の形で、下の穴から粘土の玉を糸で下げる時の、穴から玉の上までの長さの上限（整数 mm。糸そのものの長さではない。
    穴に通して結ぶ分と玉に結ぶ分は別に要る）。玉の下が胴の底から 3mm 以上離れる長さ。

    下げられない（上限が HANG_MIN より短い・下の穴が無い・吊る形・前の組）時は None。既定の寸法（重り 3g・穴は軸の 28mm 下・軸の高さ 42mm）では、
    直径約 15mm の玉が底に当たるので None になる。
    """
    if frozen() or p["mount"] != "neck" or p["weight_below_axle"] < LOWER_HOLE_MIN:
        return None
    room = axle_z(p) - 3 - p["weight_below_axle"] - 2 * clay_r(p["weight_g"])
    return math.floor(room) if room >= HANG_MIN else None


def axle_z(p):
    """刷る穴の高さ（胴の底から）。吊る形では耳の穴が胴の上の縁から HOLE_MARGIN 下に決まり、axle_height は部品に効かない。"""
    return p["body_height"] - HOLE_MARGIN if p["mount"] == "hang" else p["axle_height"]


def check_physics(p):
    out = []
    H, ax = p["body_height"], axle_z(p)
    pts = mass_points(p)
    _, z, _ = center(pts)
    if z <= 0:
        out.append(Failure("F5.pivot", "重り", f"重心が軸より {-z:.1f}mm 上にあり、揺れて戻らない"))
    tilt = rest_tilt_deg(pts)
    if z > 0 and abs(tilt) > MAX_TILT:
        out.append(Failure("F5.pivot", "重り", f"静かな時に {tilt:.0f}° 傾く（{MAX_TILT}° まで）"))
    if H - ax < HOLE_MARGIN and p["mount"] == "neck":
        out.append(Failure("F5.pivot", "軸の穴", f"軸の穴から胴の上の縁まで {H - ax}mm で、裂けやすい"))
    if p["mount"] == "hang":
        # 式と刷る物を同じにする（レビュー指摘）。吊る形の軸は耳の穴で決まるので、axle_height が違えば式が別の物を計算している。
        if abs(p["axle_height"] - ax) > 0.5:
            out.append(Failure("F5.pivot", "軸の高さ", f"axle_height {p['axle_height']} が、刷る耳の穴の高さ（胴の高さ−{HOLE_MARGIN}＝{ax}）と違う"))
        # 重りは頭の裏に貼る（手順）。式の位置が頭の外なら、刷った手順では作れない。
        arm = axle_to_head_top(p)
        if not arm <= p["weight_below_axle"] <= arm + p["head_h"]:
            out.append(Failure("F5.pivot", "重り", f"軸の下 {p['weight_below_axle']}mm は頭（軸の下 {arm}〜{arm + p['head_h']}mm）の外で、頭の裏に貼れない"))
        if p["ear_length"] < 2 * HOLE_MARGIN:
            out.append(Failure("F5.pivot", "耳", f"耳が短く、穴の前後に {HOLE_MARGIN}mm 取れない"))
        reach = axle_to_head_top(p) + p["head_h"]
        room = p["ear_length"] - HOLE_MARGIN
        if room < reach and math.degrees(math.asin(room / reach)) < MIN_SWING:
            out.append(Failure("F5.pivot", "頭", f"頭が胴に当たるまで {MIN_SWING}° 揺れない"))
        if H - HOLE_MARGIN - reach < 3:
            out.append(Failure("F5.pivot", "頭", "頭の下端が床に近すぎる"))
    else:
        # 首の帯が穴の縁に当たらずに MIN_SWING まで揺れるか。帯の面は軸に直交する（軸は帯の面の穴を貫く）ので、
        # 帯の幅は穴の中で縦に並ぶ。軸は前の壁の NECK_BACK 後ろ。θ 傾くと、壁の所で帯の中心は NECK_BACK·tanθ 動き、
        # 帯の縦の幅は sw/cosθ に広がる。前は帯の幅の 2 割しか引いておらず、穴より広い帯も通していた（レビュー指摘: 穴 10・帯 20）。
        t = math.radians(MIN_SWING)
        need = NECK_BACK * math.tan(t) + p["strip_width"] / (2 * math.cos(t))
        if need > p["opening"] / 2:
            out.append(Failure("F5.pivot", "首", f"首の帯（幅 {p['strip_width']}）が穴（{p['opening']}）の縁に当たるまで {MIN_SWING}° 揺れない"))
        if p["head_h"] / 2 > ax - 3:
            out.append(Failure("F5.pivot", "頭", "頭の下端が床に近すぎる"))
    # 粘土の玉の大きさで見る床（エンジン issue/tora-v4 8d2f667 と同じ）。前の組でも同じ玉なので、組で分けない（刷る紙は変わらない）。
    # 2 つの決まり（軸の竹串・底）は、重りの別の落ち（重心が軸より上・傾き）が無い時だけ言う。1 つの崩れに別の行が続くと狙いが読めなくなり、
    # 凍結の負の場面が 1 行で落ちる決まりも崩れる
    ball_ok = not any(f.where == "重り" for f in out)
    if ball_ok and p["mount"] == "neck":
        r = clay_r(p["weight_g"])
        # 2 つは 1 つの寸法で両方起きうる（軸の高さ 15・重り 5mm 下・15g）ので、先の 1 つだけを言う
        if p["weight_below_axle"] < r + AXLE_CLEAR:
            out.append(Failure("F5.pivot", "重り", f"粘土の玉（半径 {r:.1f}mm）が軸の竹串にかかる（玉の真ん中は軸の下 {p['weight_below_axle']}mm。{r + AXLE_CLEAR:.1f}mm 以上下に）"))
        elif p["weight_below_axle"] <= ax - 3 < p["weight_below_axle"] + r:
            # 首の形の粘土の玉は腕に付くので、静かな時（一番低い）の玉の下の端で見る。真ん中が底に近すぎる時は、下の今の決まりが落とすので重ねて言わない
            out.append(Failure("F5.pivot", "重り", f"粘土の玉の下が底に当たる（玉の下は軸の下 {p['weight_below_axle'] + r:.1f}mm、軸の高さ {ax}mm）"))
    if p["weight_below_axle"] > ax - 3:
        out.append(Failure("F5.pivot", "重り", f"重りが底に当たる（軸の下 {p['weight_below_axle']}mm、軸の高さ {ax}mm）"))
    if p["strip_width"] > p["body_width"] - 6:
        out.append(Failure("F5.pivot", "帯", "帯が胴の内幅に入らない"))
    return out


# 絵を見て手で取った点。絵の画素は使っていない。
_BODY = [(300, 240), (340, 205), (400, 180), (500, 180), (600, 180), (700, 140), (780, 150), (840, 190), (862, 270), (845, 360), (855, 400), (875, 440), (878, 560), (865, 610), (830, 625), (785, 595),
         (810, 550), (805, 470), (770, 400), (745, 420), (735, 500), (725, 540), (680, 555), (640, 525), (660, 490), (672, 440), (670, 390), (600, 430), (525, 455), (515, 500), (490, 640), (440, 668),
         (385, 640), (420, 600), (420, 500), (400, 460), (375, 520), (345, 600), (300, 625), (262, 600), (290, 560), (318, 480), (320, 425), (345, 370), (360, 320), (345, 270)]
_BODY_LINES = [[(345, 235), (385, 275)], [(370, 215), (415, 255)], [(410, 195), (470, 240), (480, 310)], [(450, 190), (510, 250), (540, 360)], [(515, 205), (550, 270), (620, 350)], [(555, 195), (590, 260), (650, 320)],
               [(595, 190), (630, 260)], [(640, 185), (660, 230)], [(665, 175), (690, 220)], [(690, 160), (725, 205)], [(740, 155), (765, 225)], [(790, 185), (800, 255)], [(705, 315), (780, 345)], [(715, 345), (800, 355)],
               [(430, 420), (485, 412)], [(440, 445), (480, 440)], [(340, 455), (375, 468)], [(335, 485), (365, 490)], [(680, 405), (715, 440)], [(770, 410), (840, 425)]]
_HEAD = [(40, 345), (60, 300), (95, 265), (135, 245), (150, 232), (172, 250), (195, 265), (235, 320), (245, 385), (215, 415), (150, 420), (100, 445), (70, 425), (58, 390)]
_MOUTH = [(62, 385), (130, 382), (150, 405), (100, 438), (72, 422)]
_EYES = [[(72, 295), (92, 295), (96, 315), (76, 318)], [(115, 325), (140, 325), (142, 345), (118, 348)]]
_HEAD_LINES = [[(100, 275), (120, 300)], [(125, 262), (140, 285)], [(155, 285), (205, 310)], [(165, 355), (195, 380)], [(205, 350), (220, 372)]]


def _scale(pts, x0, y0, sx, sy, ox, oy):
    return [(ox + (x - x0) * sx, oy + (y - y0) * sy) for x, y in pts]


def _flip(pts, x, y, w, h):
    """2 枚目の側面の絵。次の組は y だけを裏返す（本人のレビューから採った案 EP-0016、2026-11-06。前にも言われて直っていなかった所。
    型紙エンジン issue/tora-v4 1f4f0b1 と同じ）。

    前の組は x も裏返し（180° 回していた）、組むとその側の虎は後ろを向き、軸の穴が尾の側に来た。2 枚目の側面は箱の中で上が頁の下に
    なるので、y だけ裏返すと外から見て立ち、頭が 1 枚目と同じ前の端（軸の穴の側）に来る。前の組は紙を変えないので 180° のまま。
    """
    if frozen():
        return [(2 * x + w - a, 2 * y + h - b) for a, b in pts]
    return [(a, 2 * y + h - b) for a, b in pts]


LABEL_SIZE = 2.8  # 札の字の大きさ（compose.LABEL_SIZE と同じ。雛形から compose を読むと読み込みの輪になるので、値を写す）


def _strip_label(sw):
    """次の組の 3 首の帯の札の字と x（型紙エンジン issue/tora-v4 1f4f0b1 と同じ）。帯の真ん中の谷折りの線（x = sw）が、字の「3」と「首」の
    間の空きを通る所に置く（札の字が折り線にかかっていた）。「3 首の帯」は 10.7mm で、帯の片側（既定 10mm）には入らないので、番号と名の間で折る。
    名が片側に入らない細い帯（sw が約 9mm より細い）は「3 帯」にする（「3 首の帯」は帯の枠に収まらず、配置の検査で落ちる）。
    限り: その時も、用意する物と組み方の文は「3 首の帯」と呼ぶ（番号の 3 で同じ部品と分かる）。
    """
    num, pre = text_width("3", LABEL_SIZE), text_width("3 ", LABEL_SIZE)
    x0 = sw - (num + pre) / 2
    for text in ("3 首の帯", "3 帯"):
        if x0 + text_width(text, LABEL_SIZE) <= 2 * sw - 0.3:
            return text, x0
    return "3", 1


def _side_art(x, y, L, H, flip):
    sx, sy = (L - 1) / (878 - 262), (H - 1) / (668 - 140)
    fix = (lambda ps: _flip(ps, x, y, L, H)) if flip else (lambda ps: ps)
    body = fix(_scale(_BODY, 262, 140, sx, sy, x + 0.5, y + 0.5))
    art = [{"kind": "poly", "pts": body, "fill": TIGER, "stroke": STRIPE, "sw": 0.2}]
    shape = Polygon(body).buffer(-0.1)
    for line in _BODY_LINES:
        piece = LineString(fix(_scale(line, 262, 140, sx, sy, x + 0.5, y + 0.5))).intersection(shape)
        for g in getattr(piece, "geoms", [piece]):
            if not g.is_empty and g.geom_type == "LineString":
                art.append({"kind": "line", "pts": list(g.coords), "stroke": STRIPE, "sw": 0.5})
    return art


def _panel(x0, y0, x1, y1, fill):
    return {"kind": "poly", "pts": [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], "fill": fill}


def _head_part(p):
    w, h = p["head_w"], p["head_h"]
    sx, sy = w / (245 - 40), h / (445 - 232)
    scale = lambda ps: _scale(ps, 40, 232, sx, sy, 0, 0)
    outline = scale(_HEAD)
    art = [{"kind": "poly", "pts": outline, "fill": TIGER, "stroke": STRIPE, "sw": 0.2}, {"kind": "poly", "pts": scale(_MOUTH), "fill": MOUTH}]
    art += [{"kind": "poly", "pts": scale(e), "fill": EYE, "stroke": STRIPE, "sw": 0.2} for e in _EYES]
    art += [{"kind": "line", "pts": scale(line), "stroke": STRIPE, "sw": 0.35} for line in _HEAD_LINES]
    # 次の組は 2〜5 番にも部品の名を刷る（EP-0016: 1 番だけ名があり、ほかは番号だけだった）。前の組は番号だけのまま
    return Part(2, "head", "頭", outline, label_xy=(w * 0.5, h * 0.6), label="2" if frozen() else "2 頭", art=art)


def parts(p):
    L, W, H, g = p["body_length"], p["body_width"], p["body_height"], p["glue"]
    e, eh = p["ear_length"], p["ear_height"]
    hang = p["mount"] == "hang"
    top0, top1 = g, g + W
    b0, b1 = top1 + H, top1 + H + W
    bottom = b1 + H
    pts = [(H + 2, 0), (H + L - 2, 0), (H + L, g), (H + L, b0 - g), (H + L + H - 2, b0 - g), (H + L + H, b0), (H + L + H, b1), (H + L + H - 2, b1 + g), (H + L, b1 + g), (H + L, bottom), (H, bottom)]
    if hang:
        pts += [(H - e, bottom), (H - e, bottom - eh), (H, bottom - eh)]
    pts += [(H, b1 + g), (2, b1 + g), (0, b1), (0, b0), (2, b0 - g), (H, b0 - g)]
    if hang:
        pts += [(H, top1 + eh), (H - e, top1 + eh), (H - e, top1), (H, top1)]
    pts += [(H, g)]
    # 札の字は、上の面の左下に置く。左上だと 1 本目の縞が字にかかる（読めるが、次の組で直す）。前の組は紙を変えないので左上のまま。
    body = Part(1, "body", "胴", pts, label_xy=(H + 2, top0 + 2) if frozen() else (H + 2, top1 - 5.5), label="1 胴")
    body.valley = [((H, top0), (H + L, top0)), ((H, top1), (H + L, top1)), ((H, b0), (H + L, b0)), ((H, b1), (H + L, b1)), ((H, b0), (H, b1)), ((H + L, b0), (H + L, b1)),
                   ((0, b0), (H, b0)), ((0, b1), (H, b1)), ((H + L, b0), (H + L + H, b0)), ((H + L, b1), (H + L + H, b1))]
    if not frozen():
        # 絵は箱の 6 面とも刷った面の側にある。色の面を外へ向けるには、刷った面から見て山折りにする（本人の答えは御来迎の外筒。虎も同じ形。エンジンの c4ade80 と同じ）。
        body.mountain, body.valley = body.valley, []
    body.glue = [[(H + 2, 0), (H + L - 2, 0), (H + L, g), (H, g)], [(2, b0 - g), (H, b0 - g), (H, b0), (0, b0)], [(0, b1), (H, b1), (H, b1 + g), (2, b1 + g)],
                 [(H + L, b0 - g), (H + L + H - 2, b0 - g), (H + L + H, b0), (H + L, b0)], [(H + L, b1), (H + L + H, b1), (H + L + H - 2, b1 + g), (H + L, b1 + g)]]
    body.art = [_panel(H + 0.2, top0 + 0.2, H + L - 0.2, top1 - 0.2, TIGER), _panel(H + 0.2, b0 + 0.2, H + L - 0.2, b1 - 0.2, TIGER),
                _panel(0.2, b0 + 0.2, H - 0.2, b1 - 0.2, TIGER), _panel(H + L + 0.2, b0 + 0.2, H + L + H - 0.2, b1 - 0.2, TIGER)]
    body.art += [{"kind": "line", "pts": [(H + x, top0 + 3), (H + x + 4, top1 - 3)], "stroke": STRIPE, "sw": 0.5} for x in range(6, int(L) - 6, 9)]
    body.art += _side_art(H, top1 + 0.2, L, H - 0.4, False) + _side_art(H, b1 + 0.2, L, H - 0.4, True)
    ax = p["axle_height"]
    if hang:
        body.holes = [(H - e + HOLE_MARGIN, top1 + HOLE_MARGIN, 1.2), (H - e + HOLE_MARGIN, bottom - HOLE_MARGIN, 1.2)]
    else:
        back = NECK_BACK  # 前の壁の少し後ろに軸を通す。首の帯が壁に当たらないように
        body.holes = [(H + back, top1 + H - ax, 1.2), (H + back, bottom - (H - ax), 1.2)]
        if not frozen():
            # 軸の竹串が胴を横切る所の線（EP-0016: 竹串を通す位置の線）。上の面の、2 つの穴と同じ x に横切る点の線（位置の印）
            body.art.append({"kind": "mark", "pts": [(H + back, top0 + 0.6), (H + back, top1 - 0.6)], "mark": "axle"})
        op = p["opening"]
        cy = (b0 + b1) / 2
        body.cuts = [(H - ax - op / 2, cy - op / 2, op, op)]
        # 穴の縁の橙。絵の首の穴の色を前の壁に描く
        body.art.append(_panel(H - ax - op / 2 - 1.5, cy - op / 2 - 1.5, H - ax + op / 2 + 1.5, cy + op / 2 + 1.5, RIM))
    head = _head_part(p)
    sw = p["strip_width"]
    length = (p["neck_length"] + 12) if not hang else STRIP_HOLE + axle_to_head_top(p) + HEAD_OVERLAP
    # 帯は半分に折って 2 枚にする。1 枚では頭を支えるには柔らかいと見込むため。
    # 次の組の札は名つきで、軸の穴の下に置き（穴の上の 1.5mm からだと、名の札が穴にかかる）、真ん中の谷折りの線が字の間の空きを通る x にする
    tag, tag_x = ("3", 1) if frozen() else _strip_label(sw)
    strip = Part(3, "strip", "首の帯", [(0, 0), (2 * sw, 0), (2 * sw, length), (0, length)], label_xy=(tag_x, 1.5) if frozen() else (tag_x, STRIP_HOLE + 2.5),
                 label=tag, valley=[((sw, 0), (sw, length))], holes=[(sw / 2, STRIP_HOLE, 1.0), (1.5 * sw, STRIP_HOLE, 1.0)])
    tail = Part(4, "tail", "尾", [(0, 0), (8, 0), (8, 56), (0, 56)], label_xy=(1, 1.5), label="4" if frozen() else "4 尾",
                art=[_panel(0.1, 0.1, 7.9, 55.9, TIGER)] + [{"kind": "line", "pts": [(0.3, y), (7.7, y)], "stroke": STRIPE, "sw": 0.5} for y in range(10, 54, 8)])
    out = [body, head, strip, tail]
    if not hang:
        # 紙の頭は軽いので、重りは軸の真下に下げる（research/12）。下げる腕が無いと寸法どおりに作れない。
        drop_len = max(p["weight_below_axle"] + 8, 20)
        # 次の組の札は「5 腕」（幅 8mm に「5 重りの腕」は入らない。札は部品の枠の内に置く決まり）
        drop = Part(5, "drop", "重りの腕", [(0, 0), (8, 0), (8, drop_len), (0, drop_len)], label_xy=(1, 8), label="5" if frozen() else "5 腕", holes=[(4, 4, 1.0)])
        if not frozen() and p["weight_below_axle"] >= LOWER_HOLE_MIN:
            # 下の穴（重りの位置。EP-0011）と、粘土を付ける高さの点の線（EP-0016）。
            # 前は「下の端に粘土を付ける」だけで、腕が 20mm の下限で長い寸法では、式の位置（軸から weight_below_axle）より下に付いた
            wy = 4 + p["weight_below_axle"]
            drop.holes.append((4, wy, THREAD_R))
            # 粘土を付ける高さの線（EP-0016: 点の丸は「赤い斑点」に見え、何の印か分からなかった）。腕を横切る位置の印の点の線で、
            # 穴の左右で切る（印が穴にかかると切った時に消える）
            gap = THREAD_R + 1.0
            drop.art += [{"kind": "mark", "pts": [(0.6, wy), (4 - gap, wy)], "mark": "weight"},
                         {"kind": "mark", "pts": [(4 + gap, wy), (7.4, wy)], "mark": "weight"}]
        out.append(drop)
    return out


def place(by_key, page, top, gap):
    body = by_key["body"]
    body.x, body.y = page.x0, top
    y = top + body.height + gap
    x = page.x0
    head, strip, tail = by_key["head"], by_key["strip"], by_key["tail"]
    head.x, head.y = x, y
    x += head.width + gap
    strip.x, strip.y = x, y
    x += strip.width + gap
    if "drop" in by_key:
        drop = by_key["drop"]
        drop.x, drop.y = x, y
        x += drop.width + gap
    tail.x, tail.y = x, y
    x += tail.width + gap
    return y, page.x1 - x, x


def bom(p):
    paper = f"紙（厚さ 0.15mm 前後・{p['paper_gsm']}g/m² の見込み）"
    why = "家庭のプリンタで刷って作るため"
    rows = [
        {"number": 1, "key": "body", "name": "胴", "qty": 1, "material": paper, "substituted": True, "original_guess": "張子（手元の解説の呼び名による）", "reason": why},
        {"number": 2, "key": "head", "name": "頭", "qty": 1, "material": paper, "substituted": True, "original_guess": "張子（同じ）", "reason": why},
        {"number": 3, "key": "strip", "name": "首の帯", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明", "reason": why},
        {"number": 4, "key": "tail", "name": "尾", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明", "reason": why},
        {"number": 7, "key": "axle", "name": "軸", "qty": 1, "material": f"竹串（長さ約 {p['body_width'] + 20}mm に切り、先を落とす）", "substituted": True, "original_guess": "不明", "reason": "家にあり、穴に通しやすいため"},
        {"number": 8, "key": "weight", "name": "重り", "qty": 1, "material": _weight_material(p), "substituted": True, "original_guess": "不明", "reason": "量を変えて試しやすいため"},
    ]
    if p["mount"] == "neck":
        # 首の形だけが刷る部品 5。部品表に無いと、型紙と部品表が食い違ったまま検査を通った。
        rows.insert(4, {"number": 5, "key": "drop", "name": "重りの腕", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明", "reason": "紙の頭は軽いので、重りを軸の真下に下げる腕が要るため"})
    return rows


def _weight_material(p):
    """重りの素材。糸で下げられる寸法の時だけ、穴から玉の上までの長さの幅（HANG_MIN〜上限）を添える（EP-0011・エンジンと同じ字）。"""
    L = hang_thread_mm(p)
    # L は穴から玉の上までの長さで、糸そのものの長さではない（穴に通して結ぶ分と玉に結ぶ分は別に要る）
    return f"油粘土 {p['weight_g']:g}g" + (f"（糸で下げる時は、たこ糸も。玉の上は穴から {HANG_MIN}〜{L}mm）" if L is not None else "")


def materials(p):
    # 行の位置でなく key で引く。形によって部品表の行が増えるので、位置で引くと別の行を刷る。
    by = {r["key"]: r for r in bom(p)}
    # 胴に中を切り抜く所がある形（首の形の前の壁の四角い穴）は、カッターを道具に書く（手順に「カッターは大人がする」。#294、本人の確認 11-06）。
    # 前の組は紙を変えないので足さない。エンジン（paper-to-toy の e189dc6）と同じ結果になる事を tests/test_next_sheets.py が見る。
    # 部品を組まずに形の値で決める（slider_fan と同じ理由）。
    # 次の組の首の形は、重りの腕をテープで仮に留めて試してから貼る（EP-0011）ので、セロハンテープも書く（エンジンと同じ並び。カッターを行の終わりに）
    tools = "のり、はさみ、定規" + ("、セロハンテープ、カッター" if not frozen() and p["mount"] == "neck" else "")
    if frozen() or p["mount"] != "neck":
        return [f"{by['body']['material']}を 1 枚", tools, by["axle"]["material"], by["weight"]["material"]]
    # 次の組の首の形: 紙でない材料の置き所と、丸い印・色の意味を字で書く（EP-0016: 本人に分からなかった）。型紙エンジンと同じ字
    L = hang_thread_mm(p)
    hang = f"。糸で下げる時は、たこ糸も。玉の上は穴から {HANG_MIN}〜{L}mm" if L is not None else ""
    return [f"{by['body']['material']}を 1 枚", tools,
            f"{by['axle']['material']}（胴の 2 つの穴・3 首の帯の穴・5 腕の上の穴に通す。胴の上の面の点の線の下を通る）",
            f"油粘土 {p['weight_g']:g}g（" + (f"5 腕の下の穴の、点の線の所に付ける{hang}" if p["weight_below_axle"] >= LOWER_HOLE_MIN
                                          else f"5 腕の上の穴の {p['weight_below_axle']:g}mm 下に付ける") + "）",
            "丸い印は穴（竹串の先であける）。4 尾は外に見えるので色を刷り、3 首の帯と 5 腕は胴の中に入るので白"]


def steps(p):
    out = ["刷った物差しに定規を当て、10cm か確かめる", "部品を実線で切る。胴の穴は竹串の先であける"]
    if p["mount"] == "neck":
        out.append("1 胴の前の壁の四角い穴を切る（カッターは大人がする）")
    # 次の組は「破線で」を「線のとおり」に。山折りの線は凡例では一点鎖線で、「破線で山折り」だと字と線が合わない
    # （窓口が本人の委任 2026-11-06 でカード 002247 の推しを選んだ。1 語の決まりを 2 語にした）。前の組は紙を変えないので前の字。
    fold = "破線で谷折り" if frozen() else "線のとおり山折り"
    out += [f"1 胴を{fold}し、糊代で貼って箱にする。上の面は後で閉じる", "3 首の帯を半分に折って貼る。穴は重ねたまま通す"]
    if p["mount"] == "neck":
        out += ["3 首の帯の前の端に 2 頭を貼る", "帯を前の壁の穴に入れ、竹串を胴の穴と帯の穴に通す"]
        if frozen():
            out += ["5 重りの腕の穴にも竹串を通し、下の端に粘土を付ける。腕は 3 首の帯に貼る", "頭の傾きを見て、腕を貼る位置を決める"]
        else:
            # 腕は仮に留めて、頭の傾きを見てから貼る（EP-0011: 作った人が帯と頭を胴の穴から何度も出し入れしていた）。手順の数と番号は変えない。
            # 文はエンジン（issue/tora-v4 1f4f0b1）と同じ字
            L = hang_thread_mm(p)
            hang = f"か、下の穴に糸を通して粘土の玉を下げる（玉の上は穴から {HANG_MIN}〜{L}mm）" if L is not None else ""
            # 下の穴は weight_below_axle が LOWER_HOLE_MIN 以上の時だけある。無い時は、粘土の位置を軸の穴からの深さで言う
            clay = (f"下の穴（点の線）の所に粘土を付ける{hang}" if p["weight_below_axle"] >= LOWER_HOLE_MIN
                    else f"粘土の真ん中を、上の穴の {p['weight_below_axle']:g}mm 下に付ける")
            out += [f"5 重りの腕の上の穴にも竹串を通す。{clay}。腕は 3 首の帯に添えて、テープで仮に留める（まだ貼らない）",
                    "頭の傾きを見て腕の位置を決めてから、腕を 3 首の帯に貼る"]
    else:
        # 式の「軸から頭の上の端まで」と重りの位置を手順に刷る。前は「下の端に貼る」「あごの近く」だけで、紙が式の寸法を実現しなかった（レビュー指摘）。
        arm = axle_to_head_top(p)
        out += [f"3 首の帯の下の端を、2 頭の上の端に {HEAD_OVERLAP}mm 重ねて貼る", "竹串を耳の穴と帯の穴に通す",
                f"粘土を頭の裏の真ん中、頭の上の端から {p['weight_below_axle'] - arm:g}mm 下に貼る"]
    out += ["1 胴の上の面を閉じる", "4 尾を丸くして、後ろに貼る"]
    return out


# 虎の物差しは頭が揺れるかどうかで足りる（本人の判断、research/15）。周期の差で仮説を見分ける設計にしない。
# 「わからない」は物差しでなく、決められない時の札。どの玩具でも選べるようにした（#146）。
RESULTS = ("揺れた", "揺れない", "わからない")
# 手順の紙に刷る札は、刷る組で決める。本人の決め（11-06、#373）は「次の組の紙から 3 つの欄」。
# 決めの前に紙の指紋を控えた組（tora-v3・tora-v4）は 2 つの欄のまま刷る。札は紙に刷るので、足すと控えた紙の指紋が変わり、
# 控えは書き換えない決まり（tests/test_floor_pin.py）。それより後の組（tora-v6 など）は RESULTS の 3 つで刷る。
# 1 つの値で持たないのは、控えた組と今の組を同じ雛形で刷り分けるため（前の組の紙は、雛形の SHEET_SET をその組に置いて組む）。
# 控えた組を足すのは、決めの前に 2 つの欄で控えた組がほかにあった時だけ（tests/test_result_words.py が控えの有る組だけかを見る）。
TWO_BOX_SETS = ("tora-v3", "tora-v4")
PAPER_RESULTS = ("揺れた", "揺れない")


def paper_results():
    """今組んでいる組（SHEET_SET）の手順の紙に刷る札。frozen() と同じく、組を前の組に置いて組む時もその組の札になる。"""
    return PAPER_RESULTS if SHEET_SET in TWO_BOX_SETS else RESULTS


def measures(p):
    """揺れるかの二択でなく、動き方を言葉か絵で予想する（U-25 の案 1）。動かした物は数でないので残す。"""
    return {"predict": "頭はどう動くと思いますか（言葉か絵で）", "rows": [[("動かした物（手・息・団扇）", 40)]]}


def diagram(x, y, w, h, p):
    s = min(w / (p["body_length"] + p["head_w"]), h / (p["body_height"] + 6))
    bx, by = x + p["head_w"] * s, y + 3
    shapes = [{"kind": "rect", "x": bx, "y": by, "w": p["body_length"] * s, "h": p["body_height"] * s}]
    ax_y = by + (p["body_height"] - axle_z(p)) * s
    if p["mount"] == "neck":
        ax_x = bx + 6 * s
        head_x = ax_x - (p["neck_length"] + 6 + p["head_w"]) * s
        shapes.append({"kind": "line", "x1": head_x + p["head_w"] * s, "y1": ax_y, "x2": ax_x, "y2": ax_y})
        shapes.append({"kind": "rect", "x": head_x, "y": ax_y - p["head_h"] * s / 2, "w": p["head_w"] * s, "h": p["head_h"] * s})
    else:
        ax_x = bx - (p["ear_length"] - HOLE_MARGIN) * s
        top = ax_y + axle_to_head_top(p) * s
        shapes.append({"kind": "line", "x1": ax_x, "y1": ax_y, "x2": ax_x, "y2": top})
        shapes.append({"kind": "rect", "x": ax_x - p["head_w"] * s / 2, "y": top, "w": p["head_w"] * s, "h": p["head_h"] * s})
    wz = ax_y + p["weight_below_axle"] * s
    shapes.append({"kind": "line", "x1": ax_x, "y1": ax_y, "x2": ax_x, "y2": wz, "dash": "1,0.6"})
    shapes.append({"kind": "rect", "x": ax_x - 1.2, "y": wz - 1.2, "w": 2.4, "h": 2.4})
    return shapes
