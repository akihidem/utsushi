"""雛形 popup_jar: 箱に載せた壺（角筒）の口から、下から押す帯で人形を飛び出させる。『江都二色』22 コマ左の玩具の仮説を試す。

【解釈】絵は、黒い釉の垂れた壺が箱に載り、袖を広げて棒と丸い物を持つ人形が口に立つ所と、脇に置いた切り込みのある板を描く。
動き方は絵の文からは読み切れない。この雛形は「箱の底から帯を押し上げると、壺に隠れていた人形が口から飛び出す」と読んだ
1 つの仮説で、昔の作り方の復元ではない（脇の板が押す棒か、梃子か、ただの添え物かは分からない。梃子の読みは試していない）。

しくみ（この雛形の決め事）:
- 壺は面の数の違う角筒（FORM の jar: square は 4 面、hex は 6 面）。jar_width は型紙の折り線の間で測った向かい合う面の間で、
  どちらの形も同じ値にする（展開図の 1 面の幅はこの値から出す）。内の幅は紙 2 枚分狭く（inner_half）、外の差し渡しは 2 枚分広い（footprint）
  下の端の糊代を内へ折って箱の上に貼る（外へ折ると足が箱からはみ出すため）
- 押す帯は紙を縦に半分に折って貼った 2 枚重ね。箱の上の面と底の面の同じ位置の四角い穴に通す。2 つの穴が離れているので
  帯が傾きにくい（箱の高さが案内の長さ）
- 人形の足は帯より広く、静かな時は箱の上の面に乗って止まる（隠れた形）。帯の下の端は箱の底から押す量だけ出ていて、
  底とそろうまで押し上げると人形が口の上へ出る（押し切った形は机に立つ）

動きの見込みの式（check_physics）の前提:
- 高さは箱の底から測る。口の高さ R = 箱の高さ + 壺の高さ。人形の体の下の端は静かな時 z0 = 箱の高さ + 足の高さ
- 隠れる: z0 + 人形の高さ ≦ R − HIDE_MARGIN。口から出る: z0 + 押す量 ≧ R（体の下の端が口の高さに届く）
- 傾き: 帯は 2 つの穴の遊び（幅の向き SLIDE_GAP、厚みの向き HOLE_DEPTH − 2×紙の厚さ）の分だけ、上の穴の中で丸ごと寄り（遊びの半分）、
  案内の長さ（箱の高さ）に対して傾く。高さ h での横ずれ = 遊び ÷ 2 ＋ h × 遊び ÷ 案内の長さ。壺の中にいる間（h ≦ 壺の高さ）に、
  袖の先と足の端が内の壁に当たらない事を見る（足は人形より広くなりうるので別に見る）。厚みの向きの遊びは MIN_DEPTH_GAP 以上を要る
- 引っかかり: 引き出しの決まり（ずれた所を押すと、案内の 2 点に生じる摩擦で止まる）。帯の端を押す（ずれ = 帯の幅の半分）時に
  ずれ ≦ 案内の長さ ÷ (2 × 摩擦の係数) なら滑る。摩擦の係数 MU は紙と紙の見込みで、実物では測っていない
- 紙の厚さ・摩擦・遊びの値はどれも実物では未確認。帯の座屈（長い帯が押す力で曲がる）は式にしていない
Claude が変えてよいのは RANGES にある名前の値だけ。
"""
import math

from shapely.geometry import LineString, Polygon

from ..paper_words import paper_name  # 紙の書き方は 4 つの名前だけ（制作者の指示 2026-11-05）
from ..model import Failure, Part

ID = "popup_jar"
# 寸法の出発点。絵の比（壺の高さに対し箱が低い）と A4 の印字域に収まる事から出した。どの値も実物では未確認。
DEFAULTS = {
    "jar": "square",
    "jar_width": 40, "jar_height": 60, "jar_glue": 8, "jar_tab": 5,
    "box_side": 48, "box_height": 18, "box_glue": 7,
    "strip_width": 12,
    # 押す量は、体の下の端が口に届く最小（壺の高さ − 足の高さ = 54）に 2mm の余り。
    "push_amount": 56,
    "figure_w": 30, "figure_h": 26,
    # 0.15mm はふつうの厚めの紙の見込み。実物の紙を測ったら置き換える。
    "paper_thickness": 0.15,
}
RANGES = {
    "jar_width": (30, 60), "jar_height": (40, 90), "jar_glue": (5, 12), "jar_tab": (3, 8),
    "box_side": (30, 70), "box_height": (8, 40), "box_glue": (5, 10),
    "strip_width": (6, 20), "push_amount": (20, 90),
    "figure_w": (15, 50), "figure_h": (15, 60),
    "paper_thickness": (0.05, 1.5),
}
JARS = ("square", "hex")
SIDES = {"square": 4, "hex": 6}
# 刷る形を決める寸法（壺の面の数）。絵の壺は丸いので、紙で折れる角筒のどちらが近いかは作り手の試行錯誤。既定に頼らず必ず書かせる。
# 玩具の型紙は 1 枚で、square がたたき台、hex はヒント（制作者の決定 2026-11-05「玩具 1 つに型紙 1 枚」・omochae.sheets）。
FORM = "jar"
FORMS = JARS
# 既定の出典（data/sources/ の名前）。
SOURCE = "NDL-1187053-R0000022-L-popup_jar"
# 形ごとの出典。4 面と 6 面は同じ玩具の作り分けなので、どちらも 22 コマ左。合わない出典（ほかの玩具）を渡すと compose が F1.source で落とす。
SOURCES = {jar: SOURCE for jar in JARS}

# 帯と穴の幅の遊び（片側 0.5mm ずつ）。狭いと紙の毛羽で擦れ、広いと傾く。見込みの値。
SLIDE_GAP = 1.0
# 穴の厚みの向きの大きさ。帯（0.3mm 前後）に合わせて細く切るのは難しいので、カッターで切れる 3mm にする。
HOLE_DEPTH = 3.0
# 人形の足の、穴の縁から外へ出る長さ（片側）。これより狭いと足が穴に落ちて止まらない。
STOP_LIP = 3.0
# 人形の足の高さ。帯の上の端に貼り、箱の上の面に乗る。
FOOT_TAB = 6.0
# 隠れた時に、人形の上の端（棒の先）を口からこれだけ下げる。上から覗いて見えにくくするための見込み。
HIDE_MARGIN = 2.0
# 袖の先と壺の内の壁の間に残す余り。紙の反りの見込み。
FIT_MARGIN = 1.0
# 紙と紙の摩擦の係数の見込み（0.3〜0.6 と言われる範囲の上の方を取り、安全側にした）。実物では測っていない。
MU = 0.5
# 壺の足が箱の上の面に乗る時の余り（全体で）。
SEAT_MARGIN = 1.0
# 厚みの向きの最小の遊び。0 だと紙の毛羽と糊の膨らみで帯が穴に詰まる（見込み。実物では測っていない）。
MIN_DEPTH_GAP = 0.5


def spec():
    return {"template_id": ID, "defaults": DEFAULTS, "ranges": RANGES, "jar": JARS}


def check_range(p):
    out = []
    for k, v in p.items():
        if k == "jar":
            if v not in JARS:
                out.append(Failure("F5.range", k, f"{v} は {JARS} のどれでもない"))
        elif k not in RANGES:
            out.append(Failure("F5.range", k, "知らない寸法の名前"))
        elif not isinstance(v, (int, float)) or isinstance(v, bool) or not RANGES[k][0] <= v <= RANGES[k][1]:
            out.append(Failure("F5.range", k, f"{v} は範囲 {RANGES[k]} の外"))
    return out


def face_width(p):
    """展開図の 1 面の幅（折り線の間）。jar_width は折り線の間で測った向かい合う面の間なので、6 面なら 1 面は W/√3。"""
    return p["jar_width"] if p["jar"] == "square" else p["jar_width"] / math.sqrt(3)


def inner_half(p):
    """壺の中心から内の壁までの距離。折り線の間の半分から、壁の紙 1 枚の厚さを引く（紙は折り線の外へは出ないと見る安全側）。"""
    return p["jar_width"] / 2 - p["paper_thickness"]


def footprint(p):
    """壺の足の一番広い差し渡し（外の寸法）。6 面は角から角（2 × 1 面の幅）。向きを決めずに安全側で見る。両側に紙 1 枚ずつを足す。"""
    span = p["jar_width"] if p["jar"] == "square" else 2 * face_width(p)
    return span + 2 * p["paper_thickness"]


# 人形の体の中心の、輪郭の幅に対する位置（絵から取った）。棒が左へ長く出るので、体は輪郭の中ほどより右にある。
# 帯はこの位置に貼るので、輪郭を壺の真ん中に置くには、帯（と穴）を真ん中から右へずらす。
FIG_AXIS = (440 - 206) / 367


def strip_offset(p):
    """帯の中心の、壺の中心から右（前から見て）へのずれ。人形の輪郭を壺の真ん中に置くため。"""
    return (FIG_AXIS - 0.5) * p["figure_w"]


def foot_width(p):
    """人形の足の幅。穴より片側 STOP_LIP 広くして、静かな時に箱の上で止める。"""
    return p["strip_width"] + SLIDE_GAP + 2 * STOP_LIP


def rest_bottom(p):
    """静かな時の人形の体の下の端の高さ（箱の底から）。足が箱の上の面に乗る。"""
    return p["box_height"] + FOOT_TAB


def strip_length(p):
    """帯の長さ。上の端は体の下の端（足を貼る所）、下の端は箱の底から押す量だけ出る。"""
    return rest_bottom(p) + p["push_amount"]


def sway(p, h):
    """高さ h（箱の上の面から）での帯の横ずれ（幅の向き, 厚みの向き）。案内は箱の上と底の穴で、その間が箱の高さ。

    上の穴の中で帯が丸ごと寄る分（遊びの半分）に、2 つの穴の遊びで傾く分を足す。寄る分を落とすと、h が小さい所のずれを少なく見た。
    """
    lg = p["box_height"]
    depth_gap = max(0.0, depth_gap_mm(p))
    return SLIDE_GAP / 2 + h * SLIDE_GAP / lg, depth_gap / 2 + h * depth_gap / lg


def depth_gap_mm(p):
    """厚みの向きの遊び。穴の大きさから、2 枚重ねの帯の厚さを引く。"""
    return HOLE_DEPTH - 2 * p["paper_thickness"]


def check_physics(p):
    out = []
    H, Hb, s = p["jar_height"], p["box_height"], p["push_amount"]
    R, z0, fh, fw = Hb + H, rest_bottom(p), p["figure_h"], p["figure_w"]
    room = inner_half(p)
    # 1. 隠れる。人形の上の端（棒の先）が口より HIDE_MARGIN 下。
    if z0 + fh > R - HIDE_MARGIN:
        out.append(Failure("F5.popup", "人形", f"静かな時の人形の上の端 {z0 + fh:.1f} が口の高さ {R}−{HIDE_MARGIN} を超え、隠れない"))
    # 2. 口から出る。押し切った時に体の下の端が口の高さに届く。
    if z0 + s < R:
        out.append(Failure("F5.popup", "押し帯", f"押し切った時の体の下の端 {z0 + s:.1f} が口の高さ {R} に届かず、人形が出きらない"))
    # 3. 壺の中で袖の先が壁に当たらない。輪郭は壺の真ん中に置くので、片側は幅の半分。傾きは壺の口の高さで一番大きい。
    dx, dy = sway(p, H)
    if fw / 2 + dx + FIT_MARGIN > room:
        out.append(Failure("F5.popup", "人形", f"袖の先（半分の幅 {fw / 2:.1f}＋傾き {dx:.1f}＋余り {FIT_MARGIN}）が壺の内の半分 {room:.1f} を超え、壁に擦れる"))
    if dy + FIT_MARGIN > room:
        out.append(Failure("F5.popup", "押し帯", f"厚みの向きの傾き {dy:.1f} が壺の内の半分 {room:.1f} を超え、前後の壁に当たる"))
    # 4. 静かな時、足が壺の中に収まる（内へ折った糊代の上には乗らない）。
    reach = abs(strip_offset(p)) + foot_width(p) / 2
    free = room - p["jar_tab"] - FIT_MARGIN
    if reach > free:
        out.append(Failure("F5.popup", "人形の足", f"足の端が壺の中心から {reach:.1f} で、内へ折った糊代の内側 {free:.1f} を超える"))
    # 4b. 押し上げる途中も、足の端が内の壁に当たらない。足は帯に合わせて広くなり人形より広くなりうるので、袖とは別に、
    #     足が壺の中にいる一番高い所（足の上の端が口の高さ＝箱の上から壺の高さ）の傾きで見る。
    if reach + dx + FIT_MARGIN > room:
        out.append(Failure("F5.popup", "人形の足", f"押し上げる途中の足の端（{reach:.1f}＋傾き {dx:.1f}＋余り {FIT_MARGIN}）が壺の内の半分 {room:.1f} を超え、壁に擦れる"))
    # 4c. 厚みの向きの遊び。0 以下だと帯が穴に詰まって滑らない。
    if depth_gap_mm(p) < MIN_DEPTH_GAP:
        out.append(Failure("F5.popup", "押し帯", f"厚みの向きの遊び {depth_gap_mm(p):.2f}（穴 {HOLE_DEPTH}−帯 2 枚）が {MIN_DEPTH_GAP} に足りず、帯が穴に詰まる"))
    # 5. 引っかからない。帯の端を押した時のずれ（帯の幅の半分）が、案内の長さ ÷ (2μ) 以下。
    e, limit = p["strip_width"] / 2, Hb / (2 * MU)
    if e > limit:
        out.append(Failure("F5.popup", "押し帯", f"帯の端を押すずれ {e:.1f} が 案内の長さ {Hb}÷(2×摩擦 {MU})={limit:.1f} を超え、穴で引っかかる"))
    # 壺が箱に乗る（F5.jar_seat）。足の差し渡しが箱の一辺に収まり、穴が内へ折った糊代に隠れない。
    B = p["box_side"]
    if footprint(p) > B - SEAT_MARGIN:
        out.append(Failure("F5.jar_seat", "壺", f"壺の足の差し渡し {footprint(p):.1f} が箱の一辺 {B}−{SEAT_MARGIN} を超え、箱に乗らない"))
    hx, hy = abs(strip_offset(p)) + (p["strip_width"] + SLIDE_GAP) / 2, HOLE_DEPTH / 2
    if math.hypot(hx, hy) > free:
        out.append(Failure("F5.jar_seat", "箱の穴", f"穴の角が壺の中心から {math.hypot(hx, hy):.1f} で、内へ折った糊代の内側 {free:.1f} を超え、糊代で塞がる"))
    return out


# 色は NDL の図を見て選んだ落ち着いた数色。図を貼らず、色と線を描き直す。隣り合う面の色を少し変え、色の境で折る（slider_fan の v9 と同じ）。
GLAZE, GLAZE_ALT = "#3b3226", "#4a3f30"
CLAY, CLAY_ALT = "#d6bba5", "#ccae97"
RIM_LINE = "#8a7a60"
BOX_TOP, BOX_WALL, BOX_BOTTOM = "#e2d5b6", "#cdbd98", "#d8c9a6"
SLAT, SLAT_ALT = "#cbb27c", "#bfa36b"
ROBE, HAIR, FACE, INK, PALE = "#c9ab9b", "#c9a25a", "#efe5d0", "#3b3328", "#e9dfc6"

# 釉の垂れの長さ（口からの、壺の高さに対する比）。絵の 5 本の垂れの先を測った比を順に使う。
_DRIPS = (0.48, 0.40, 0.53, 0.44, 0.50)
# 釉の塗りの下の端（垂れの根元）。絵では口から壺の高さの 3 割ほど。
GLAZE_DOWN = 0.30


def _drip(cx, w, y0, y1):
    """垂れ 1 本。先を丸くするため、下の端を 5 点で折れ線にする。"""
    r = w / 2
    pts = [(cx - r, y0), (cx + r, y0), (cx + r, y1 - r)]
    for k in range(1, 4):
        a = math.pi * k / 4
        pts.append((cx + r * math.cos(a), y1 - r + r * math.sin(a)))
    pts.append((cx - r, y1 - r))
    return pts


def _jar(p):
    n, a, H = SIDES[p["jar"]], face_width(p), p["jar_height"]
    g, tb = p["jar_glue"], p["jar_tab"]
    w = n * a
    outline = [(0, 0), (w, 0), (w + g, 2), (w + g, H - 2), (w, H)]
    glue = [[(w, 0), (w + g, 2), (w + g, H - 2), (w, H)]]
    # 壺は色の面（土の色・釉・口の輪）を外にして筒にするので、刷った面から見て全部山折り。谷折り（凡例の、刷った面がへこむ向き）のままだと
    # 色の面が筒の内に入った。制作者の決定（2026-11-06「今のうちに4つ直す」）で、御来迎の外筒・虎の胴と同じ線で直した。下の糊代も、
    # 筒の内へ折る（手順の「内へ折り」）のは刷った面の裏へ折る向きなので山折り。線は刷らず色の境で折るので、型紙の PDF は変わらない
    folds = [((a * i, 0), (a * i, H)) for i in range(1, n + 1)]
    for i in reversed(range(n)):
        x0, x1 = a * i, a * (i + 1)
        # 足の糊代の角は糊代の長さだけ落とす。内へ折ると隣の糊代と角で重なるので（4 面は 45°、6 面は 30° 必要）、両方に足りる量にした。
        outline += [(x1 - tb, H + tb), (x0 + tb, H + tb), (x0, H)]
        glue.append([(x0, H), (x1, H), (x1 - tb, H + tb), (x0 + tb, H + tb)])
        folds.append(((x0, H), (x1, H)))
    jar = Part(1, "jar", "壺", outline, label_xy=(1.5, H - 6), label="1 壺", mountain=folds, glue=glue)
    art = []
    gz = H * GLAZE_DOWN
    per = max(1, round(a / 16))
    k = 0
    for i in range(n):
        x0, x1 = a * i, a * (i + 1)
        alt = i % 2
        art.append({"kind": "poly", "pts": [(x0, 0), (x1, 0), (x1, H), (x0, H)], "fill": CLAY_ALT if alt else CLAY})
        glaze = GLAZE_ALT if alt else GLAZE
        art.append({"kind": "poly", "pts": [(x0, 0), (x1, 0), (x1, gz), (x0, gz)], "fill": glaze})
        for j in range(per):
            cx = x0 + a * (j + 0.5) / per
            art.append({"kind": "poly", "pts": _drip(cx, a * (0.30 if per == 1 else 0.18), gz - 0.5, H * _DRIPS[k % len(_DRIPS)]), "fill": glaze})
            k += 1
        # 口の縁の輪の線（絵の口の 2 本の輪）。
        art.append({"kind": "line", "pts": [(x0 + 0.4, 3.5), (x1 - 0.4, 3.5)], "stroke": RIM_LINE, "sw": 0.4})
    jar.art = art
    jar.hide_folds = True
    return jar


def _rect(x0, y0, x1, y1, fill):
    return {"kind": "poly", "pts": [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], "fill": fill}


def _box(p):
    """箱の展開図（十字）。真ん中の列に 上の面・前の壁・底の面・後ろの壁、上の面の左右に横の壁。

    横の壁の前後の端の糊代を前と後ろの壁の内に貼り、後ろの壁の端の糊代を上の面の内に貼る。底の面の左右は貼らない
    （前と後ろの壁が支える）。上の面と底の面の同じ位置に帯の穴を切る。
    """
    B, Hb, g = p["box_side"], p["box_height"], p["box_glue"]
    c0, c1 = Hb, Hb + B  # 真ん中の列の x
    top0, top1 = g, g + B
    front1 = top1 + Hb
    bot1 = front1 + B
    back1 = bot1 + Hb
    W = 2 * Hb + B
    outline = [
        (c0, top0), (c1, top0),
        # 右の横の壁と、その前後の端の糊代
        (c1, top0), (c1 + 1.5, 0), (W - 1.5, 0), (W, top0), (W, top1), (W - 1.5, top1 + g), (c1 + 1.5, top1 + g), (c1, top1),
        (c1, front1), (c1, bot1), (c1, back1),
        (c1 - 1.5, back1 + g), (c0 + 1.5, back1 + g), (c0, back1),
        (c0, bot1), (c0, front1), (c0, top1),
        (c0 - 1.5, top1 + g), (1.5, top1 + g), (0, top1), (0, top0), (1.5, 0), (c0 - 1.5, 0), (c0, top0),
    ]
    # 同じ点が続く所を除く（多角形を正しくするため）。
    clean = [outline[0]]
    for q in outline[1:]:
        if q != clean[-1]:
            clean.append(q)
    if clean[-1] == clean[0]:
        clean.pop()
    # 箱は色の面と「2 箱」の字を外にして閉じるので、刷った面から見て全部山折り。谷折り（凡例の、刷った面がへこむ向き）のままだと、
    # 色の面も前の壁の字も箱の内に入り、外から見ると上の面の穴のずれ（真ん中より右）が左に出た。制作者の決定（2026-11-06「今のうちに
    # 4つ直す」）で、御来迎の外筒・虎の胴と同じ線で直した。糊代は山折りでも箱の内へ折れる（手順どおり）。線は刷らないので PDF は変わらない
    folds = [((c0, top0), (c1, top0)), ((c0, top1), (c1, top1)), ((c0, front1), (c1, front1)), ((c0, bot1), (c1, bot1)), ((c0, back1), (c1, back1)),
             ((c0, top0), (c0, top1)), ((c1, top0), (c1, top1)),
             ((0, top0), (c0, top0)), ((0, top1), (c0, top1)), ((c1, top0), (W, top0)), ((c1, top1), (W, top1))]
    glue = [[(c1, top0), (c1 + 1.5, 0), (W - 1.5, 0), (W, top0)], [(c1, top1), (W, top1), (W - 1.5, top1 + g), (c1 + 1.5, top1 + g)],
            [(0, top0), (1.5, 0), (c0 - 1.5, 0), (c0, top0)], [(0, top1), (c0, top1), (c0 - 1.5, top1 + g), (1.5, top1 + g)],
            [(c0, back1), (c1, back1), (c1 - 1.5, back1 + g), (c0 + 1.5, back1 + g)]]
    # top0 の線は、上の面の縁が後ろの壁の糊代に貼られる所。折り線ではないので折り線から外す。
    folds = [v for v in folds if v != ((c0, top0), (c1, top0))]
    hw, cx = p["strip_width"] + SLIDE_GAP, c0 + B / 2 + strip_offset(p)
    cuts = [(cx - hw / 2, top0 + B / 2 - HOLE_DEPTH / 2, hw, HOLE_DEPTH), (cx - hw / 2, front1 + B / 2 - HOLE_DEPTH / 2, hw, HOLE_DEPTH)]
    art = [_rect(c0, top0, c1, top1, BOX_TOP), _rect(c0, top1, c1, front1, BOX_WALL), _rect(c0, front1, c1, bot1, BOX_BOTTOM),
           _rect(c0, bot1, c1, back1, BOX_WALL), _rect(0, top0, c0, top1, BOX_WALL), _rect(c1, top0, W, top1, BOX_WALL)]
    # 壺を貼る位置の印（上の面の真ん中）。足の差し渡しの四角で示す。
    # 箱に乗らない寸法（F5.jar_seat で落ちる）でも印が上の面の外へ出ないよう、面の内で止める。
    f = min(footprint(p), B - 1) / 2
    mx, my = c0 + B / 2, top0 + B / 2
    art.append({"kind": "line", "pts": [(mx - f, my - f), (mx + f, my - f), (mx + f, my + f), (mx - f, my + f), (mx - f, my - f)], "stroke": RIM_LINE, "sw": 0.25})
    box = Part(2, "box", "箱", clean, label_xy=(c0 + 2, top1 + 2), label="2 箱", mountain=folds, glue=glue, cuts=cuts, art=art)
    box.hide_folds = True
    return box


def _strip(p):
    sw, L = p["strip_width"], strip_length(p)
    strip = Part(3, "strip", "押し帯", [(0, 0), (2 * sw, 0), (2 * sw, L), (0, L)], label_xy=(1, 8), label="3",
                 valley=[((sw, 0), (sw, L))], art=[_rect(0, 0, sw, L, SLAT), _rect(sw, 0, 2 * sw, L, SLAT_ALT),
                                                   # 人形の足の下の端を合わせる線（前の半分だけ）。隠れる・出る高さの式（rest_bottom・strip_length）は、
                                                   # 足が帯の上の端から FOOT_TAB だけ重なって貼られる事を前提にするので、その位置を刷る。
                                                   {"kind": "line", "pts": [(0.4, FOOT_TAB), (sw - 0.4, FOOT_TAB)], "stroke": INK, "sw": 0.3}])
    strip.hide_folds = True
    return strip


# 人形の輪郭。絵（1600 幅の図を 1205 幅で見た画素）を見て手で取った点で、絵の画素は使っていない。
# 左上の板の付いた棒・頭・広げた袖・右手の丸い物・裾の順に、時計回り。棒は絵より太くした（紙で切れる太さにするため）。
_RAW = [(206, 828), (232, 814), (248, 836), (244, 840), (340, 912), (385, 925), (400, 915),
        (398, 880), (402, 858), (418, 845), (440, 848), (452, 865), (452, 895), (446, 912),
        (470, 922), (522, 930), (528, 904), (527, 886), (536, 872), (550, 866), (565, 872), (573, 888), (567, 904), (554, 912),
        (556, 935), (562, 990), (508, 990), (498, 1000), (512, 1078), (492, 1092), (388, 1092), (368, 1078), (384, 1000),
        (384, 990), (328, 980), (326, 930), (330, 921), (238, 853), (222, 850)]
_X0, _Y0, _W, _H = 206, 814, 367, 278
_HEAD = [(400, 914), (398, 880), (402, 858), (418, 845), (440, 848), (452, 865), (452, 895), (446, 912), (424, 918)]
_FACE = [(410, 868), (440, 866), (444, 890), (436, 906), (418, 906), (410, 890)]
_STICK = [(244, 840), (340, 912), (330, 921), (238, 853)]
_PADDLE = [(206, 828), (232, 814), (248, 836), (222, 850)]
_BALL = (550, 889, 21)
_LINES = [[(415, 918), (430, 945), (446, 915)], [(386, 935), (385, 988)], [(497, 935), (499, 988)], [(392, 1012), (490, 1012)], [(440, 1014), (440, 1090)]]


def _figure(p):
    fw, fh = p["figure_w"], p["figure_h"]
    sc = lambda ps: [(fw * (x - _X0) / _W, fh * (y - _Y0) / _H) for x, y in ps]
    body = sc(_RAW)
    # 裾の下の辺（右下→左下）の所に、帯より広い足を入れる。足の中心は体の中心（帯の中心）にそろえる。
    i = body.index(sc([(492, 1092)])[0])
    axis, half = FIG_AXIS * fw, foot_width(p) / 2
    foot = [(axis + half, fh), (axis + half, fh + FOOT_TAB), (axis - half, fh + FOOT_TAB), (axis - half, fh)]
    outline = body[: i + 1] + foot + body[i + 1:]
    # 糊代は帯の幅の所だけ（足の外の端は糊を付けず、箱に乗る止めになる）。
    sw = p["strip_width"]
    glue = [[(axis - sw / 2, fh), (axis + sw / 2, fh), (axis + sw / 2, fh + FOOT_TAB), (axis - sw / 2, fh + FOOT_TAB)]]
    shape = Polygon(body).buffer(-0.15)
    art = []

    def clip_poly(pts, fill, stroke=None):
        # 手で取った点が輪郭を少し越えても、切る線の外と足（糊代）に絵を残さないよう体の内で切る。
        g = Polygon(pts).buffer(0).intersection(shape)
        for piece in getattr(g, "geoms", [g]):
            if not piece.is_empty and piece.geom_type == "Polygon":
                item = {"kind": "poly", "pts": list(piece.exterior.coords)[:-1], "fill": fill}
                if stroke:
                    item.update(stroke=stroke, sw=0.2)
                art.append(item)

    clip_poly(body, ROBE)
    clip_poly(sc(_HEAD), HAIR)
    clip_poly(sc(_FACE), FACE)
    clip_poly(sc(_STICK), INK)
    clip_poly(sc(_PADDLE), PALE)
    bx, by, br = _BALL
    clip_poly(sc([(bx + br * math.cos(2 * math.pi * k / 12), by + br * math.sin(2 * math.pi * k / 12)) for k in range(12)]), PALE)
    for line in _LINES:
        piece = LineString(sc(line)).intersection(shape.buffer(-0.2))
        for seg in getattr(piece, "geoms", [piece]):
            if not seg.is_empty and seg.geom_type == "LineString":
                art.append({"kind": "line", "pts": list(seg.coords), "stroke": INK, "sw": 0.25})
    return Part(4, "figure", "人形", outline, label_xy=(axis - 1, fh * 0.62), label="4", glue=glue, art=art)


def parts(p):
    return [_jar(p), _box(p), _strip(p), _figure(p)]


def place(by_key, page, top, gap):
    """壺を上に横長に置き、その下の左に箱、箱の右に帯と人形、その下に文字。返り値は (文字の開始 y, 文字の幅, 文字の開始 x)。"""
    jar, box, strip, fig = by_key["jar"], by_key["box"], by_key["strip"], by_key["figure"]
    jar.x, jar.y = page.x0, top
    y = top + jar.height + gap
    box.x, box.y = page.x0, y
    x = page.x0 + box.width + gap
    strip.x, strip.y = x, y
    # 人形の足が輪郭の原点より左へ出る寸法もあるので、左端をそろえて置く。
    fig.x, fig.y = x + strip.width + gap - min(px for px, _ in fig.outline), y
    left_y = y + max(strip.height, fig.height) + gap
    return left_y, page.x1 - x, x


def bom(p):
    """部品表。元の素材は絵から読めないので、分からない物は「不明」と書き、歴史の事実として断定しない。紙のほかの材料は無い。"""
    paper = paper_name(thickness=p['paper_thickness'])
    why = "家庭のプリンタで刷って作るため"
    return [
        {"number": 1, "key": "jar", "name": "壺", "qty": 1, "material": paper, "substituted": True, "original_guess": "焼き物か張子に見える（黒い釉の垂れは絵から。素材は不明）", "reason": why},
        {"number": 2, "key": "box", "name": "箱", "qty": 1, "material": paper, "substituted": True, "original_guess": "木の箱か（絵から。不明）", "reason": why},
        {"number": 3, "key": "strip", "name": "押し帯", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明（絵の脇の切り込みのある板が押す物かもしれない。推定）", "reason": "紙を 2 枚重ねにすると押せる硬さになると見込んだため"},
        {"number": 4, "key": "figure", "name": "人形", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明", "reason": why},
    ]


def materials(p):
    rows = bom(p)
    return [f"{rows[0]['material']}を 1 枚（全部品を同じ紙に刷る）", "のり、はさみ、定規、カッター（箱の穴は大人が切る）"]


TITLES = {"square": "四角い壺で下から押す", "hex": "六角の壺で下から押す"}


def title(p):
    return TITLES[p["jar"]]


def steps(p):
    n = SIDES[p["jar"]]
    return [
        "刷った物差しに定規を当て、10cm か確かめる",
        "まず 1 壺だけを実線で切る。色の境で山折りし、横の糊代で貼って " + ("四角" if n == 4 else "六角") + "の筒にする",
        "残りの部品を実線で切る。2 箱の上の面と底の面の細い四角い穴はカッターで切る（大人がする）",
        "2 箱を色の境で山折りし、横の壁の糊代を前と後ろの壁の内に、後ろの壁の糊代を上の面の内に貼って箱にする",
        "1 壺の下の糊代を内へ折り、2 箱の上の面の印に合わせて貼る（壺の口から鉛筆で押さえる）",
        "「2 箱」の字のある壁を前にする。穴は真ん中より右にずらしてあるので、人形の顔を前に向けると壺の真ん中に立つ",
        "3 押し帯を縦に色の境で半分に折り、印の線が外に出るように貼り合わせる",
        "3 押し帯を箱の底の穴から入れ、上の面の穴を通して壺の中へ出す",
        "4 人形の足の上の端（体との境）を 3 押し帯の上の端にそろえ、足の下の端を帯の印の線に合わせて、線のある方の面に貼る（足の両端は貼らずに箱の上に乗せる）",
        f"箱を手で持ち、底から出た帯（約 {p['push_amount']}mm）を押し上げる。底とそろうまで押すと人形が口から出る",
    ]


RESULTS = ("飛び出した", "途中で止まった", "わからない")


def measures(p):
    """動き方を言葉か絵で予想する（元の repo の手順の紙に合わせた。手順の紙は廃止し、サイトの組み立ての頁で使う）。"""
    return {"predict": "帯を押し上げると、人形はどう動くと思いますか（言葉か絵で）", "rows": []}


def diagram(x, y, w, h, p):
    """組み上がりの断面の見取り図。寸法の図ではなく、部品の並びを見せるだけの絵（静かな時の形）。"""
    H, Hb, s = p["jar_height"], p["box_height"], p["push_amount"]
    k = (h - 4) / (Hb + H + s)
    cx, floor = x + w / 2, y + h - 2 - s * k
    B, W = p["box_side"] * k, p["jar_width"] * k
    shapes = [{"kind": "rect", "x": cx - B / 2, "y": floor - Hb * k, "w": B, "h": Hb * k},
              {"kind": "rect", "x": cx - W / 2, "y": floor - (Hb + H) * k, "w": W, "h": H * k}]
    sx = cx + strip_offset(p) * k
    z0 = rest_bottom(p)
    shapes.append({"kind": "rect", "x": sx - 0.6, "y": floor - z0 * k, "w": 1.2, "h": strip_length(p) * k, "dash": "1,0.6"})
    fw = p["figure_w"] * k
    shapes.append({"kind": "rect", "x": cx - fw / 2, "y": floor - (z0 + p["figure_h"]) * k, "w": fw, "h": p["figure_h"] * k, "dash": "1,0.6"})
    return shapes
