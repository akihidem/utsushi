"""雛形 slider_fan: 角筒の中で動く台に蛇腹の扇と像を載せ、押し上げると開く。

押し方は仮説の違いなので描き分ける（docs/process/decisions/J002）。寸法の初期値の根拠は research/03。
どの値も実物では未確認。Claude が変えてよいのは RANGES にある名前の値だけで、座標には触れない。
"""
from shapely.geometry import LineString, Polygon

from ..fan_model import clearance_limit_deg, opening_bound_deg, shortest_free_thread
from ..model import Failure, Part

ID = "slider_fan"
# 刷った組の版。紙の題の「版」は仮説の版なので、組の版を別に小さく刷る（本人の決定 U-31、11-04）。組を刷り直したら上げる。
SHEET_SET = "goraigo-v9"
# 寸法の共通の出発点。手元の複写の図の比と紙面の制約から出した（docs/process/research/06・07）。
# 押し方と中心の置き方の値は答えではない。使い手に見せる組は data/hypotheses の仮説が決める（J-002）。
DEFAULTS = {
    "push_part": "tab",
    # 扇の中心の置き方も仮説の違い（J-005）。axle は口より上の軸、rim は口の高さの台。
    "hub": "axle", "pivot_above_rim": 21,
    "tube_side": 30, "tube_height": 84, "tube_glue": 8,
    "pusher_side": 26, "pusher_height": 15, "pusher_glue": 8,
    "push_amount": 69,
    "fold_height": 48, "fold_width": 8.5, "fold_count": 28,
    "base_side": 26, "base_glue": 6,
    # 割り箸の柄で押す形にも、内筒を短く切った土台を載せる。試行で「仮説Aにある土台が仮説Cにもあると、作りやすい」（本人、11-04、goraigo-v8）。
    "stage_height": 15,
    "figure_w": 12, "figure_h": 32,
    "knob_width": 4,
    # 0.15mm はふつうの厚めの紙の見込み。実物の紙を測ったら置き換える。
    "paper_thickness": 0.15,
}
RANGES = {
    "tube_side": (20, 50), "tube_height": (50, 110), "tube_glue": (5, 12),
    "pusher_side": (15, 48), "pusher_height": (10, 110), "pusher_glue": (5, 12),
    "push_amount": (10, 90),
    "pivot_above_rim": (0, 40),
    "fold_height": (20, 60), "fold_width": (5, 15), "fold_count": (6, 40),
    "base_side": (10, 48), "base_glue": (4, 10),
    "stage_height": (8, 40),
    "figure_w": (8, 30), "figure_h": (15, 60),
    "knob_width": (2, 8),
    # 上限を広く取るのは、厚さの検査が範囲の検査より先に落ちないようにするため。
    "paper_thickness": (0.05, 1.5),
    "fan_length": (50, 300),
}
PUSH_PARTS = ("tab", "tube", "stick")
HUBS = ("axle", "rim")
# 開く糸を扇の中心からこの距離につなぐ。途中で突っ張らない糸が一番短く、よく開く位置（research/08）。
THREAD_RADIUS = 35
# 溝が筒の端に近いと紙が裂けやすい。実物で確かめるまでの安全側の見込み。
SLOT_MARGIN = 5


def spec():
    """Claude に渡す道具 get_template_spec の中身。"""
    return {"template_id": ID, "defaults": DEFAULTS, "ranges": RANGES, "push_part": PUSH_PARTS, "hub": HUBS}


def check_range(p):
    out = []
    if isinstance(p.get("fold_count"), float) and not p["fold_count"].is_integer():
        out.append(Failure("F5.range", "fold_count", "折り数は整数"))
    for k, v in p.items():
        if k == "push_part":
            if v not in PUSH_PARTS:
                out.append(Failure("F5.range", k, f"{v} は {PUSH_PARTS} のどれでもない"))
        elif k == "hub":
            if v not in HUBS:
                out.append(Failure("F5.range", k, f"{v} は {HUBS} のどれでもない"))
        elif k not in RANGES:
            out.append(Failure("F5.range", k, "知らない寸法の名前"))
        elif not isinstance(v, (int, float)) or isinstance(v, bool) or not RANGES[k][0] <= v <= RANGES[k][1]:
            out.append(Failure("F5.range", k, f"{v} は範囲 {RANGES[k]} の外"))
    return out


def slot_span(p):
    """溝の範囲を筒の底からの高さで返す。つまみは内筒の高さの中ほどに通す。

    v8 から溝は筒の下の端まで切り込む（くり抜かない）。試行で「くり抜く側面の穴を切るのが大変で、下から切り取ることになった」
    （本人、11-04）。下の端は開くので、使うのは上の端 high だけ。low は内筒が静止する高さの目安として残す。
    """
    rest_bottom = p["tube_height"] - p["push_amount"] - p["pusher_height"]
    low = rest_bottom + p["pusher_height"] / 2 - p["knob_width"] / 2
    return low, low + p["push_amount"] + p["knob_width"]


def check_physics(p):
    out = []
    H, s, h = p["tube_height"], p["push_amount"], p["fold_height"]
    A, a, L = p["tube_side"], p["pusher_side"], p["pusher_height"]
    length = p["fold_count"] * p["fold_width"]
    if "fan_length" in p and abs(p["fan_length"] - length) > 1e-6:
        out.append(Failure("F5.fan_length", "蛇腹の扇", f"折り数×折り幅={length} と扇の長さ {p['fan_length']} が違う"))
    d = p["pivot_above_rim"] if p["hub"] == "axle" else 0
    if p["hub"] == "axle":
        # 中心が上がる分だけ、隠すための行程が要る。
        if d + h > s:
            out.append(Failure("F5.fan_height", "蛇腹の扇", f"中心の高さ {d}＋折りの高さ {h} が押し上げる量 {s} を超え、扇が隠れない"))
    elif h > H - s:
        out.append(Failure("F5.fan_height", "蛇腹の扇", f"畳んだ高さ {h} が筒の空き {H - s} を超える"))
    bound, limit = opening_bound_deg(p["fold_count"], p["fold_width"], h), clearance_limit_deg(A, d)
    if bound > limit:
        out.append(Failure("F5.fan_clearance", "蛇腹の扇", f"帯の長さでは {bound:.0f}° 開くが、筒の口の角に当たって {limit:.0f}° までしか開けない"))
    thick = p["fold_count"] * p["paper_thickness"]
    if thick > a - 2:
        out.append(Failure("F5.fan_thickness", "蛇腹の扇", f"畳んだ厚さ {thick:.1f} が内筒の一辺−2={a - 2} を超える"))
    if not a < A - 1:
        out.append(Failure("F5.slide_clearance", "内筒", f"内筒 {a} は外筒 {A} − 1 より小さくない"))
    if p["figure_h"] > h + 6:
        out.append(Failure("F5.figure_height", "像", f"像の高さ {p['figure_h']} が折りの高さ＋6={h + 6} を超える"))
    if p["base_side"] > a:
        out.append(Failure("F5.base_size", "扇の台", f"扇の台 {p['base_side']} が内筒 {a} を超える"))
    if p["push_part"] == "tab":
        if L > H - s:
            out.append(Failure("F5.stroke", "内筒", f"内筒の長さ {L} が静止時の筒の空き {H - s} に収まらない"))
        low, high = slot_span(p)
        # 下の端は開いた切り込みなので、上の端だけが筒の口から離れていればよい。
        if H - high < SLOT_MARGIN:
            out.append(Failure("F5.stroke", "溝", f"溝が筒の口から {SLOT_MARGIN}mm 離れない（底から 0〜{high:.1f}）"))
    elif p["push_part"] == "stick" and p["stage_height"] > H - s:
        out.append(Failure("F5.stroke", "土台", f"土台の高さ {p['stage_height']} が静止時の筒の空き {H - s} に収まらない"))
    if p["push_part"] != "tab" and L < H:
        # research/03: L < H だと指が筒の外にある間に押し切れない。
        out.append(Failure("F5.stroke", "押す部品", f"長さ {L} が筒の高さ {H} より短く、押し切れない"))
    return out


def _tube(number, key, name, side, height, glue, label, notch=None):
    """notch=(x0, x1, top) は下の端から top まで切り込む溝（v8）。はさみで下から切れるよう、輪郭の一部にする。"""
    w = side * 4
    # 糊代の角を落とすのは、貼る時に隣の面へはみ出さないようにするため。
    outline = [(0, 0), (w, 0), (w + glue, 2), (w + glue, height - 2), (w, height)]
    if notch:
        x0, x1, top = notch
        outline += [(x1, height), (x1, top), (x0, top), (x0, height)]
    outline.append((0, height))
    return Part(number, key, name, outline, label_xy=(1.5, 1.5), label=label,
                valley=[((side * i, 0), (side * i, height)) for i in range(1, 5)],
                glue=[[(w, 0), (w + glue, 2), (w + glue, height - 2), (w, height)]])


# 色は NDL の図から測った値（research/10）。図を貼らず、色と線を描き直す（J-007）。
PAPER, ORANGE, BROWN, LINE, FACE = "#a89365", "#a5632c", "#7a5e3b", "#55492c", "#b9a677"
# 色の境で折る（v9）。ワークショップを見ていたデザイナーの「見た目のクオリティが低く見えるのは、谷折り線とか入ってるからじゃない？」
# を受け、本人が d「絵の色の境で折り、線を引かない」を選んだ（11-04）。隣り合う面と板の色を変え、その境を折り目にする。
# 筒は 1 面おきに少し明るい地、扇は 2 色の板を交互にする。色は原図の地の色の近くから選んだ（作る側の選び）。
PAPER_ALT = "#bba982"
FAN_A, FAN_B = "#f1e9d6", "#d9caa6"


def _tube_art(A, H, notch=None):
    """筒の 4 面の描き直し。絵の手前の角の 2 本線は、折り線の両側に 1 本ずつ引くと組んだ時に細い面に見える。

    溝の切り込みがある面は、切り込みの左右に分けて塗る（絵を切る線の外に出さないため）。
    """
    art = []
    for i in range(4):
        x0, x1 = A * i, A * (i + 1)
        cols = [(x0, x1)]
        if notch and x0 < notch[0] and notch[1] < x1:
            cols = [(x0, notch[0]), (notch[1], x1)]
        art.append({"kind": "poly", "pts": [(x0, 0), (x1, 0), (x1, 4.5), (x0, 4.5)], "fill": ORANGE})
        ground = PAPER if i % 2 == 0 else PAPER_ALT
        for c0, c1 in cols:
            art.append({"kind": "poly", "pts": [(c0, 4.5), (c1, 4.5), (c1, H - 5), (c0, H - 5)], "fill": ground})
            art.append({"kind": "poly", "pts": [(c0, H - 5), (c1, H - 5), (c1, H), (c0, H)], "fill": BROWN})
        if len(cols) == 2:
            # 溝の上の端より上は 1 枚の面のまま塗る。
            art.append({"kind": "poly", "pts": [(notch[0], 4.5), (notch[1], 4.5), (notch[1], notch[2]), (notch[0], notch[2])], "fill": ground})
    art.append({"kind": "line", "pts": [(A - 1.2, 0), (A - 1.2, H)], "stroke": LINE, "sw": 0.5})
    art.append({"kind": "line", "pts": [(A + 1.2, 0), (A + 1.2, H)], "stroke": LINE, "sw": 0.5})
    return art


# 像の線。絵を見て手で点を取り直した物で、絵の画素は使っていない。座標は輪郭と同じ 0〜1 に直す。
_FIGURE_LINES = [
    [(72, 155), (85, 195)], [(170, 150), (155, 200)],
    [(110, 218), (115, 180), (125, 168), (138, 185), (145, 205), (130, 225), (120, 235), (110, 218)],
    [(40, 240), (60, 265), (110, 240)], [(195, 272), (150, 235)],
    [(65, 270), (100, 310)], [(90, 285), (140, 245)], [(125, 280), (130, 340)],
    [(72, 340), (95, 340), (105, 355), (130, 360), (170, 340)],
    [(105, 360), (110, 410), (122, 425), (158, 385), (140, 470)], [(185, 385), (165, 470)], [(72, 345), (85, 500)],
]
_FACE = [(118, 60), (140, 68), (153, 90), (150, 118), (135, 140), (118, 146), (100, 140), (85, 118), (82, 90), (95, 68)]


def _figure_art(fw, fh, pts):
    scale = lambda ps: [(fw * (x - 36) / 177, fh * (y - 33) / 472) for x, y in ps]
    art = [{"kind": "poly", "pts": pts, "fill": PAPER}, {"kind": "poly", "pts": scale(_FACE), "fill": FACE, "stroke": LINE, "sw": 0.25}]
    # 手で取った線の端が輪郭を越えた時は切る。切る線の外に絵を残さないため。
    body = Polygon(pts).buffer(-0.15)
    for line in _FIGURE_LINES:
        clipped = LineString(scale(line)).intersection(body)
        for piece in getattr(clipped, "geoms", [clipped]):
            if not piece.is_empty and piece.geom_type == "LineString":
                art.append({"kind": "line", "pts": list(piece.coords), "stroke": LINE, "sw": 0.25})
    return art


# 像の輪郭（絵を見て手で取った点を 0〜1 にした物）。
_RAW = [(113, 33), (135, 45), (150, 62), (158, 85), (157, 120), (153, 135), (172, 152), (195, 175), (210, 205), (213, 250),
        (200, 272), (193, 280), (190, 330), (180, 410), (170, 475), (165, 505), (90, 505), (85, 470), (72, 400), (65, 350),
        (62, 330), (68, 290), (50, 265), (40, 240), (36, 210), (45, 175), (65, 155), (78, 130), (80, 100), (78, 80), (90, 62), (100, 45)]
FIGURE_OUTLINE = [((x - 36) / 177, (y - 33) / 472) for x, y in _RAW]


def _insert_tab(pts, x0, x1, bottom, tab):
    """輪郭の底辺（右下→左下の順）の間に足を入れる。"""
    i = max(range(len(pts)), key=lambda k: (pts[k][1], pts[k][0]))
    return pts[: i + 1] + [(x1, bottom), (x1, bottom + tab), (x0, bottom + tab), (x0, bottom)] + pts[i + 1:]


def parts(p):
    A, H, a, L = p["tube_side"], p["tube_height"], p["pusher_side"], p["pusher_height"]
    out = []
    notch = None
    if p["push_part"] == "tab":
        low, high = slot_span(p)
        # 溝は 2 面目の中央。ラベルの面と離し、糊の継ぎ目からも離す。y は頁の下向きなので高さから引く。
        notch = (A * 1.5 - (p["knob_width"] + 1) / 2, A * 1.5 + (p["knob_width"] + 1) / 2, H - high)
    tube = _tube(1, "tube", "外筒", A, H, p["tube_glue"], "1 外筒", notch)
    tube.art = _tube_art(A, H, notch)
    tube.hide_folds = True
    if p["hub"] == "axle":
        # 開く糸を試す穴。扇は 1 面目に平行に開くので、その両脇の面につなぐ。
        tube.holes += [(A * 1.5, 3, 0.6), (A * 3.5, 3, 0.6)]
    out.append(tube)
    if p["push_part"] in ("tab", "tube", "stick"):
        # 柄の形の内筒は短い土台（v8）。柄の先を下から差し込んで貼り、台を載せる面にする。
        height, name = (p["stage_height"], "土台") if p["push_part"] == "stick" else (L, "内筒")
        inner = _tube(2, "pusher", name, a, height, p["pusher_glue"], f"2 {name}")
        if p["push_part"] == "tab":
            # 向かい合う 2 面に串を通す穴。1 面だけだと串が傾いて溝の中で引っかかりやすい。
            inner.holes += [(a * 1.5, L / 2, 1.2), (a * 3.5, L / 2, 1.2)]
        out.append(inner)
    b, g = p["base_side"], p["base_glue"]
    out.append(Part(3, "base", "扇の台", [
        (g, g), (g + 1, 0), (g + b - 1, 0), (g + b, g), (g + b + g, g + 1), (g + b + g, g + b - 1),
        (g + b, g + b), (g + b - 1, g + b + g), (g + 1, g + b + g), (g, g + b), (0, g + b - 1), (0, g + 1),
    ], label_xy=(g + 1, g + 1), label="3 台",
        valley=[((g, g), (g + b, g)), ((g + b, g), (g + b, g + b)), ((g + b, g + b), (g, g + b)), ((g, g + b), (g, g))],
        glue=[[(g, g), (g + 1, 0), (g + b - 1, 0), (g + b, g)],
              [(g + b, g), (g + b + g, g + 1), (g + b + g, g + b - 1), (g + b, g + b)],
              [(g + b, g + b), (g + b - 1, g + b + g), (g + 1, g + b + g), (g, g + b)],
              [(g, g + b), (0, g + b - 1), (0, g + 1), (g, g)]],
        art=_base_mark(p)))
    n, w, h = int(p["fold_count"]), p["fold_width"], p["fold_height"]
    outline = [(0, 0), (h, 0), (h, n * w), (0, n * w)]
    glue, leg_valley = [], []
    if p["hub"] == "axle":
        # ジャバラの固定（v8）。試行で「ジャバラの固定に苦慮していた」（本人、11-04）。本人の決定で、糊代と貼る位置の印まで型紙で決める。
        # 真ん中の 1 枚を要から下へ伸ばした足にし、先の糊代を 3 台の印に貼る。真ん中が立ったまま、両側の板が開く。
        m, leg = n // 2, leg_length(p)
        outline += [(0, (m + 1) * w), (-leg, (m + 1) * w), (-leg, m * w), (0, m * w)]
        glue.append([(-leg, m * w), (-leg + LEG_GLUE, m * w), (-leg + LEG_GLUE, (m + 1) * w), (-leg, (m + 1) * w)])
        leg_valley.append(((-leg + LEG_GLUE, m * w), (-leg + LEG_GLUE, (m + 1) * w)))
    fan = Part(4, "fan", "蛇腹の扇", outline, label_xy=(5, 1.5), label="4 扇", glue=glue, valley=leg_valley)
    for i in range(1, n):
        line = ((0, i * w), (h, i * w))
        # 山と谷を交互にするのが蛇腹の形そのもの。
        (fan.valley if i % 2 else fan.mountain).append(line)
    # 板ごとに 2 色を交互に塗り、色の境で折る（v9）。足は真ん中の板と同じ色にし、糊代は塗らない。
    fan.art = [{"kind": "poly", "pts": [(0, i * w), (h, i * w), (h, (i + 1) * w), (0, (i + 1) * w)], "fill": FAN_A if i % 2 == 0 else FAN_B} for i in range(n)]
    if p["hub"] == "axle":
        m, leg = n // 2, leg_length(p)
        fan.art.append({"kind": "poly", "pts": [(-leg + LEG_GLUE, m * w), (0, m * w), (0, (m + 1) * w), (-leg + LEG_GLUE, (m + 1) * w)], "fill": FAN_A if m % 2 == 0 else FAN_B})
    fan.hide_folds = True
    if p["hub"] == "axle":
        # 中心の穴に糸を通して束ねる。扇の要と同じ形。端の 2 枚の穴は開く糸を試すため。
        r_hole = 2
        fan.holes += [(r_hole, (i + 0.5) * w, 0.6) for i in range(n)]
        fan.holes += [(r_hole + THREAD_RADIUS, 0.5 * w, 0.6), (r_hole + THREAD_RADIUS, (n - 0.5) * w, 0.6)]
    out.append(fan)
    fw, fh = p["figure_w"], p["figure_h"]
    pts = [(fw * x, fh * y) for x, y in FIGURE_OUTLINE]
    tab = 5  # 台に貼る足。絵には無いが、立てるのに要る。
    cx0, cx1 = fw * 0.3, fw * 0.7
    figure = Part(5, "figure", "像", _insert_tab(pts, cx0, cx1, fh, tab), label_xy=(fw * 0.4, fh * 0.6), label="5",
                  glue=[[(cx0, fh), (cx1, fh), (cx1, fh + tab), (cx0, fh + tab)]],
                  art=_figure_art(fw, fh, pts))
    if p["hub"] == "axle":
        figure.holes.append((fw / 2, fh - p["pivot_above_rim"], 0.6))
    out.append(figure)
    return out


# 扇の足の先の糊代の長さ。台に貼る面。
LEG_GLUE = 6


def leg_length(p):
    """扇の足の長さ。要（糸の穴）は像の足元から pivot_above_rim の高さにあり、そこから台まで届かせ、糊代を足す。"""
    return p["pivot_above_rim"] - 2 + LEG_GLUE


def _base_mark(p):
    """3 台の上の面に、扇の足を貼る位置の印（v8）。像の足を貼る真ん中を空けて、奥の縁に寄せる。"""
    if p["hub"] != "axle":
        return []
    g, b, w = p["base_glue"], p["base_side"], p["fold_width"]
    x0, x1, y0, y1 = g + b / 2 - w / 2, g + b / 2 + w / 2, g + 1, g + 1 + LEG_GLUE
    return [{"kind": "line", "pts": [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)], "stroke": LINE, "sw": 0.3},
            {"kind": "line", "pts": [(x0, y0), (x1, y1)], "stroke": LINE, "sw": 0.2}]


def bom(p):
    """部品表。元の素材は絵から読めないので、分からない物は「不明」と書き、歴史の事実として断定しない。"""
    paper = f"紙（厚さ {p['paper_thickness']}mm 前後）"
    why = "家庭のプリンタで刷って作るため"
    rows = [
        {"number": 1, "key": "tube", "name": "外筒", "qty": 1, "material": paper, "substituted": True, "original_guess": "竹（『還魂紙料』を引く解説による。原典は未確認）", "reason": why},
        {"number": 3, "key": "base", "name": "扇の台", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明", "reason": why},
        {"number": 4, "key": "fan", "name": "蛇腹の扇", "qty": 1, "material": paper, "substituted": True, "original_guess": "紙（同じ解説による）", "reason": why},
        {"number": 5, "key": "figure", "name": "像", "qty": 1, "material": paper, "substituted": True, "original_guess": "紙の張貫か木（同じ解説による）", "reason": why},
    ]
    if p["push_part"] == "stick":
        rows.insert(1, {"number": 2, "key": "pusher", "name": "土台", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明", "reason": "柄の先に台を載せて作りやすくするため（11-04 の試行）"})
    if p["push_part"] in ("tab", "tube"):
        rows.insert(1, {"number": 2, "key": "pusher", "name": "内筒", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明", "reason": why})
    if p["push_part"] == "tab":
        rows.append({"number": 6, "key": "knob", "name": "つまみ", "qty": 1, "material": f"竹串（長さ約 {p['tube_side'] + 20}mm に切り、先を落とす）", "substituted": True, "original_guess": "不明（絵の細い棒の素材は読めない）", "reason": "家にあり、細くて溝を通るため"})
    if p["push_part"] == "stick":
        rows.append({"number": 6, "key": "stick", "name": "柄", "qty": 1, "material": f"割り箸（長さ約 {p['pusher_height']}mm）", "substituted": True, "original_guess": "不明", "reason": "家にあり、押す力に耐えるため"})
    if p["hub"] == "axle":
        rows.append({"number": 7, "key": "thread", "name": "糸", "qty": 3, "material": f"たこ糸（軸に 1 本。開く糸を試す時は、さらに 2 本 各約 {thread_mm(p):.0f}mm ＋結ぶ分）", "substituted": True, "original_guess": "不明", "reason": "家にあり、細い穴を通るため"})
    return rows


def thread_mm(p):
    return shortest_free_thread(p["tube_side"], THREAD_RADIUS, p["pivot_above_rim"] - p["push_amount"], p["pivot_above_rim"])


RESULTS = ("動いた", "動かない", "わからない")


def materials(p):
    """型紙の「用意する物」。素材は部品表だけから刷り、2 か所に手で書かない。"""
    rows = bom(p)
    lines = [f"{rows[0]['material']}を 1 枚（全部品を同じ紙に刷る）", "のり、はさみ、定規"]
    lines += [f"{r['material']} {r['qty']} 本" for r in rows if r["number"] == 6]
    lines += [r["material"] for r in rows if r["number"] == 7]
    return lines


TITLES = {"tab": "つまみで動かす", "tube": "内筒を下から押す", "stick": "割り箸の柄で動かす"}


def title(p):
    return TITLES[p["push_part"]]


def place(by_key, page, top, gap):
    """扇は長いので右の列に縦に置き、残りを左の列に積む。返り値は (文字の開始 y, 文字の幅, 文字の開始 x)。"""
    fan = by_key["fan"]
    # 扇の足（v8）は部品の原点より左に出るので、右端をそろえて置く。
    minx = min(x for x, _ in fan.outline)
    fan.x, fan.y = page.x1 - fan.width - minx, top
    left_y = top
    for key in ("tube", "pusher"):
        if key in by_key:
            q = by_key[key]
            q.x, q.y = page.x0, left_y
            left_y += q.height + gap
    base, fig = by_key["base"], by_key["figure"]
    base.x, base.y = page.x0, left_y
    fig.x, fig.y = page.x0 + base.width + gap * 2, left_y
    left_y += max(base.height, fig.height) + gap
    # 文字の列の幅は扇の本体まで取る。足は真ん中の 1 枚の高さにしか無く、文字と重なれば配置の検査（F5.overlap）が落とす。
    return left_y, fan.x - page.x0 - gap, page.x0


def steps(p):
    """組み方。部品番号は型紙と同じ。押し方と中心の置き方で変わる所だけを分ける。"""
    # まず筒を 1 つ作る（v8）。試行で、手が止まったのは平面から立体への最初の一歩で、「筒ができただけで目の色が変わって」
    # 取り組み始めた（本人の補足所見、11-04）。最初に形が 1 つできる順にする。
    out = ["刷った物差しに定規を当て、10cm か確かめる"]
    if p["push_part"] == "tab":
        out.append("まず 1 外筒だけを実線で切る。溝は下の端からはさみで切り込む（くり抜かない）")
    else:
        out.append("まず 1 外筒だけを実線で切る")
    out.append("1 外筒を色の境で谷折りし、糊代で貼って角筒にする")
    out.append("残りの部品を実線で切る。穴は竹串の先であける")
    if p["push_part"] in ("tab", "tube"):
        out.append("2 内筒も同じように角筒にする")
    if p["push_part"] == "tab":
        out.append("竹串を 2 内筒の 2 つの穴に通す")
    if p["push_part"] == "stick":
        out.append("2 土台も同じように角筒にし、割り箸の先を下から差し込んで貼る")
    out.append("3 台で 2 の上に蓋をする")
    out.append("4 扇を色の境で、端から谷折り・山折りを交互にして蛇腹に畳む")
    if p["hub"] == "axle":
        out.append("糸を 5 像の穴と 4 扇の中心側の穴の列に通し、ゆるく結ぶ")
        out.append("4 扇の真ん中の足を、糊代の境の破線で折り、足の糊代を 3 台の印に貼る")
        out.append("5 像の足を 3 台に貼る")
    else:
        out.append("4 扇の端を 3 台に貼り、5 像の足も台に貼る")
    if p["push_part"] == "tab":
        out.append("内筒を 1 外筒に入れ、竹串の端を溝から出す")
    else:
        out.append("押す部品を 1 外筒に下から入れる")
    return out


def measures(p):
    first = [("開いた角度（度）紙の力だけ", 20)]
    if p["hub"] == "axle":
        first.append(("糸あり", 20))
    return {"predict": "どこまで開くと思いますか（度）", "rows": [first, [("試した回数", 15), ("開いた回数", 15)]]}


def diagram(x, y, w, h, p):
    """組み上がりの断面の見取り図。寸法の図ではなく、部品の並びを見せるだけの絵。"""
    s = (h - 8) / (p["tube_height"] + p["fold_height"])
    cx, base = x + w / 2, y + h - 4
    tw, th = p["tube_side"] * s, p["tube_height"] * s
    shapes = [{"kind": "rect", "x": cx - tw / 2, "y": base - th, "w": tw, "h": th}]
    inner = p["pusher_side"] * s
    rest_top = base - (p["tube_height"] - p["push_amount"]) * s
    length = p["pusher_height"] * s
    if p["push_part"] == "stick":
        stage = p["stage_height"] * s
        shapes.append({"kind": "rect", "x": cx - inner / 2, "y": rest_top, "w": inner, "h": stage, "dash": "1,0.6"})
        shapes.append({"kind": "rect", "x": cx - 0.6, "y": rest_top + stage, "w": 1.2, "h": length - stage, "dash": "1,0.6"})
    else:
        shapes.append({"kind": "rect", "x": cx - inner / 2, "y": rest_top, "w": inner, "h": length, "dash": "1,0.6"})
    if p["push_part"] == "tab":
        shapes.append({"kind": "line", "x1": cx - tw / 2 - 5, "y1": rest_top + length / 2, "x2": cx, "y2": rest_top + length / 2})
    shapes.append({"kind": "rect", "x": cx - 1.2, "y": rest_top - p["fold_height"] * s, "w": 2.4, "h": p["fold_height"] * s, "dash": "1,0.6"})
    return shapes
