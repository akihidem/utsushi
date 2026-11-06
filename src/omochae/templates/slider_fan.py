"""雛形 slider_fan: 角筒の中で動く台に蛇腹の扇と像を載せ、押し上げると開く。

押し方は仮説の違いなので描き分ける（docs/process/decisions/J002）。寸法の初期値の根拠は research/03。
どの値も実物では未確認。Claude が変えてよいのは RANGES にある名前の値だけで、座標には触れない。
"""
from shapely.geometry import LineString, Polygon

from ..fan_model import clearance_limit_deg, opening_bound_deg, shortest_free_thread
from ..model import Failure, Part

ID = "slider_fan"
# 刷った組の版。紙の題の「版」は仮説の版なので、組の版を別に小さく刷る（本人の決定 U-31、11-04）。組を刷り直したら上げる。
# 仮説を分ける寸法の名前（words・generate が、仮説の寸法にこれがあるかを見る）。
HYP_KEY = "push_part"
SHEET_SET = "goraigo-v11"
# 控えを残す前の組（凍結の床。本人の指示「今の版の紙と指紋は変えない」）。SHEET_SET をこの名に置くと、前の組の紙を組む（tests/test_floor_pin.py）。
FROZEN_SET = "goraigo-v10"


def frozen():
    return SHEET_SET == FROZEN_SET


def tube_fold():
    """外筒の折り方の語。本人の答え（11-05）「色がついている所が外を向くよう折った」。色の面を外へ向けるには、刷った面から見て山折りにする。"""
    return "谷折り" if frozen() else "山折り"


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
PUSH_PARTS = ("tab", "tube", "stick", "lift")
# lift（筒を外す形）: 本人のレビュー（2026-11-06）から採った案 EP-0017 の、御来迎の次の組（goraigo-v11）の形。型紙エンジン（paper-to-toy の
# issue/goraigo-v11 5325586）と同じ形と字。扇は糸を一切使わず（本人「糸なしでやります」）、扇の下の端を 2 受け（小さい U の字の部品）に貼って束ね、
# 両端の板も受けに貼る。蛇腹の折り目のばねで扇は「基本は開いている」形になり、1 外筒をかぶせると扇は畳まれ、筒を上へ外すと開く
# （本人「この形で開くなら、内筒を下から押す仕組みも竹串も要らない」）。内筒・竹串・糸・穴は無い。
# 前の組（goraigo-v10）には無い形（check_range が落とす）。今の仮説の記録（H-A〜H-E）はこの形を使わず、型紙の 1 枚は tab のまま。
# 1 枚を lift に替えるかは本人が決める（エンジンも同じ扱い）
LIFT = "lift"
CRADLE_FLAP = 8  # 受けの左右の面の高さ mm。扇の両端の板の下の端からこの高さまでを貼る
CRADLE_ROOM = 0.8  # 受けの底の奥行きの、畳んだ扇の厚さに足す余り mm
HUBS = ("axle", "rim")
# 開く糸を扇の中心からこの距離につなぐ。途中で突っ張らない糸が一番短く、よく開く位置（research/08）。
# 低い扇では穴が紙の外に出る（F5.hole で落とす）が、半径を折りの高さに合わせて縮めない。黙って変えると糸の長さの計算と食い違うため。
THREAD_RADIUS = 35
# 開く糸を結ぶ筒の穴の、口からの深さ。糸の長さの式（thread_mm）も同じ値から測る。
THREAD_DEPTH = 3
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
            elif v == LIFT and frozen():
                out.append(Failure("F5.range", k, f"{v} は次の組の形で、前の組 {SHEET_SET} には無い"))
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
    if p["push_part"] == LIFT:
        return out + _check_lift(p)
    d = p["pivot_above_rim"] if p["hub"] == "axle" else 0
    if p["hub"] == "axle":
        # 中心が上がる分だけ、隠すための行程が要る。
        if d + h > s:
            out.append(Failure("F5.fan_height", "蛇腹の扇", f"中心の高さ {d}＋折りの高さ {h} が押し上げる量 {s} を超え、扇が隠れない"))
        # 足の糊代が扇の本体に食い込むと、糊代の折り線が要の穴の列を横切る。
        # 範囲の検査は pivot_above_rim を 0 まで許すので、足の長さが糊代に足りない組はここで落とす。
        if leg_length(p) < LEG_GLUE:
            out.append(Failure("F5.fan_leg", "蛇腹の扇", f"足の長さ {leg_length(p)} が糊代 {LEG_GLUE} に足りず、糊代が扇に食い込む（中心の高さ {d} が 2 未満）"))
    elif h > s:
        # 口の台の形も、静かな時の台から口までは押し上げる量 s（軸の形と同じ見方）。H − s は台の下の空きで、
        # これと比べていたので、扇が口から出る寸法が通っていた（paper-to-toy の直しに合わせた。#163）。
        out.append(Failure("F5.fan_height", "蛇腹の扇", f"畳んだ高さ {h} が押し上げる量 {s} を超え、静かな時に扇が口から出る"))
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
    # 像の足の糊代は像の幅の 0.3〜0.7（parts の cx0・cx1）。台より広いと貼れない。像の高さだけを見ていたので通っていた。
    foot = p["figure_w"] * (FOOT[1] - FOOT[0])
    if foot > p["base_side"]:
        out.append(Failure("F5.figure_base", "像", f"像の足の糊代 {foot:.1f} が扇の台 {p['base_side']} より広く、台に貼れない"))
    if p["push_part"] == "tab":
        if L > H - s:
            out.append(Failure("F5.stroke", "内筒", f"内筒の長さ {L} が静止時の筒の空き {H - s} に収まらない"))
        low, high = slot_span(p)
        # 下の端は開いた切り込みなので、上の端だけが筒の口から離れていればよい。
        if H - high < SLOT_MARGIN:
            out.append(Failure("F5.stroke", "溝", f"溝が筒の口から {SLOT_MARGIN}mm 離れない（底から 0〜{high:.1f}）"))
    elif p["push_part"] == "stick" and p["stage_height"] > H - s:
        out.append(Failure("F5.stroke", "土台", f"土台の高さ {p['stage_height']} が静止時の筒の空き {H - s} に収まらない"))
    elif p["push_part"] == "tube" and s > H:
        # 静止時の内筒の上の端は外筒の底から H − s。量が高さを超えると、扇の台が外筒の下へ出て扇が筒に入らない（レビュー指摘）。
        # つまみと柄の形は上の 2 つの検査が同じ事を含むので、内筒を下から押す形だけに足す。
        out.append(Failure("F5.stroke", "内筒", f"押し上げる量 {s} が筒の高さ {H} を超え、静止時に内筒の上の端が筒の下に出る"))
    if p["push_part"] != "tab" and L < H:
        # research/03: L < H だと指が筒の外にある間に押し切れない。
        out.append(Failure("F5.stroke", "押す部品", f"長さ {L} が筒の高さ {H} より短く、押し切れない"))
    return out


def cradle_depth(p):
    """2 受けの底の奥行き。畳んだ扇の厚さ（板の数 × 紙の厚さ）に余りを足す。"""
    return p["fold_count"] * p["paper_thickness"] + CRADLE_ROOM


def cradle_width(p):
    """2 受けの幅。扇の板の幅に 2mm 足し、札「2 受け」が入る 10mm を下限にする（札は部品の枠の内に置く決まり）。"""
    return max(p["fold_width"] + 2, 10)


def _check_lift(p):
    """筒を外す形の床（エンジンと同じ）。押し上げる仕組みが無いので、行程（F5.stroke）・内筒の遊び（F5.slide_clearance）・足（F5.fan_leg）・
    筒の口の角（F5.fan_clearance。扇は筒を外してから開く）は見ない。見るのは、筒が台と扇と像にかぶさる事と、受けが台に乗る事。
    床の名は今の物を使う（凍結の基準の一覧にある名だけを使う）。
    """
    out = []
    H, A, h, g, b = p["tube_height"], p["tube_side"], p["fold_height"], p["base_glue"], p["base_side"]
    thick = p["fold_count"] * p["paper_thickness"]
    # 台は糊代を下へ折った浅い箱で、高さは糊代の長さ。その上に、受けの底（紙 1 枚）と畳んだ扇が立つ
    if g + h > H - 2:
        out.append(Failure("F5.fan_height", "蛇腹の扇", f"台の高さ {g}＋扇の高さ {h} が筒の高さ {H}−2 を超え、筒をかぶせられない"))
    if thick > A - 2 - 2 * CRADLE_ROOM:
        out.append(Failure("F5.fan_thickness", "蛇腹の扇", f"畳んだ厚さ {thick:.1f} が筒の一辺 {A} に収まらず、受けごと筒に入らない"))
    if b > A - 1:
        out.append(Failure("F5.base_size", "扇の台", f"扇の台 {b} が外筒 {A} − 1 より大きく、筒をかぶせられない"))
    if cradle_width(p) > b - 2 or cradle_depth(p) + 2 > b / 2:
        out.append(Failure("F5.base_size", "受け", f"受け（幅 {cradle_width(p):g}・奥行き {cradle_depth(p):.1f}）が台の奥の半分（{b / 2:g}）に乗らない"))
    if p["figure_h"] > h + 6:
        out.append(Failure("F5.figure_height", "像", f"像の高さ {p['figure_h']} が折りの高さ＋6={h + 6} を超える"))
    if g + p["figure_h"] > H - 2:
        out.append(Failure("F5.figure_height", "像", f"台の高さ {g}＋像の高さ {p['figure_h']} が筒の高さ {H}−2 を超え、筒をかぶせられない"))
    foot = p["figure_w"] * (FOOT[1] - FOOT[0])
    if foot > b:
        out.append(Failure("F5.figure_base", "像", f"像の足の糊代 {foot:.1f} が扇の台 {b} より広く、台に貼れない"))
    return out


def _axle(p):
    """軸の形（扇を糸で束ね、足と穴がある）か。筒を外す形（lift）は糸も穴も無いので、hub に関わらず軸の形にしない。"""
    return p["hub"] == "axle" and p["push_part"] != LIFT


def _cradle(p):
    """2 受け（筒を外す形、EP-0017）。U の字に折り、底の面に畳んだ扇の下の端を、左右の面に扇の両端の板の下の所を貼る
    （本人「扇の底面・側面にのり付けで固定・扇の両端をそれで付けて基本は開いている形」）。底の面の裏は 3 台の印に貼る。
    刷った面が U の内（扇の側）になるので谷折りで、刷った面の全部が糊代。蛇腹の折り目がばねになって扇の上が開き、受けは扇の下を束ねる。
    """
    w, d, f = cradle_width(p), cradle_depth(p), CRADLE_FLAP
    total = 2 * f + d
    return Part(2, "cradle", "扇の受け", [(0, 0), (w, 0), (w, total), (0, total)], label_xy=(0.3, 1.5), label="2 受け",
                valley=[((0, f), (w, f)), ((0, f + d), (w, f + d))],
                glue=[[(0, 0), (w, 0), (w, f), (0, f)], [(0, f), (w, f), (w, f + d), (0, f + d)], [(0, f + d), (w, f + d), (w, total), (0, total)]])


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
# 色の境で折る（v9）。ワークショップに来た広告代理店の見学者の「見た目のクオリティが低く見えるのは、谷折り線とか入ってるからじゃない？」
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
    if not frozen():
        # エンジン（paper-to-toy の c4ade80）と同じ形。線は刷らず色の境で折るので、型紙の線は変わらない。組む向き（3D の確かめと foldsim）がこの種類を読む。
        tube.mountain, tube.valley = tube.valley, []
    if _axle(p):
        # 開く糸を試す穴。扇は 1 面目に平行に開くので、その両脇の面につなぐ。
        tube.holes += [(A * 1.5, THREAD_DEPTH, 0.6), (A * 3.5, THREAD_DEPTH, 0.6)]
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
    if not frozen():
        # 扇の台は、真ん中の面（扇の足を貼る印のある面）を上にして内筒に蓋をするので、刷った面から見て山折り。谷折りのままだと
        # 印が下を向いた（3D の組み立てで見つかった。11-04 の写真 p09 も印が上）。手順の文に折り方の語は無いので、文は変わらない。
        base = out[-1]
        base.mountain, base.valley = base.valley, []
    n, w, h = int(p["fold_count"]), p["fold_width"], p["fold_height"]
    outline = [(0, 0), (h, 0), (h, n * w), (0, n * w)]
    glue, leg_valley = [], []
    if _axle(p):
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
    if _axle(p) and leg_length(p) > LEG_GLUE:
        # 足が糊代より短い寸法は F5.fan_leg で落とす。その時に足の絵を描くと形が裏返る（糊代より左から右へ逆に塗る）ので描かない。
        m, leg = n // 2, leg_length(p)
        fan.art.append({"kind": "poly", "pts": [(-leg + LEG_GLUE, m * w), (0, m * w), (0, (m + 1) * w), (-leg + LEG_GLUE, (m + 1) * w)], "fill": FAN_A if m % 2 == 0 else FAN_B})
    fan.hide_folds = True
    if _axle(p):
        # 中心の穴に糸を通して束ねる。扇の要と同じ形。端の 2 枚の穴は開く糸を試すため。
        r_hole = 2
        fan.holes += [(r_hole, (i + 0.5) * w, 0.6) for i in range(n)]
        fan.holes += [(r_hole + THREAD_RADIUS, 0.5 * w, 0.6), (r_hole + THREAD_RADIUS, (n - 0.5) * w, 0.6)]
    out.append(fan)
    if p["push_part"] == LIFT:
        out.append(_cradle(p))
    fw, fh = p["figure_w"], p["figure_h"]
    pts = [(fw * x, fh * y) for x, y in FIGURE_OUTLINE]
    tab = 5  # 台に貼る足。絵には無いが、立てるのに要る。
    cx0, cx1 = fw * FOOT[0], fw * FOOT[1]
    figure = Part(5, "figure", "像", _insert_tab(pts, cx0, cx1, fh, tab), label_xy=(fw * 0.4, fh * 0.6), label="5",
                  glue=[[(cx0, fh), (cx1, fh), (cx1, fh + tab), (cx0, fh + tab)]],
                  art=_figure_art(fw, fh, pts))
    if _axle(p):
        figure.holes.append((fw / 2, fh - p["pivot_above_rim"], 0.6))
    out.append(figure)
    return out


# 扇の足の先の糊代の長さ。台に貼る面。
LEG_GLUE = 6
# 像の足の糊代を、像の幅のどこからどこまでに取るか。台に貼る幅の検査（F5.figure_base）と同じ値を使う。
FOOT = (0.3, 0.7)


def leg_length(p):
    """扇の足の長さ。要（糸の穴）は像の足元から pivot_above_rim の高さにあり、そこから台まで届かせ、糊代を足す。"""
    return p["pivot_above_rim"] - 2 + LEG_GLUE


def _base_mark(p):
    """3 台の上の面に、扇の足を貼る位置の印（v8）。像の足を貼る真ん中を空けて、奥の縁に寄せる。

    筒を外す形（EP-0017）は、2 受けの底の面を貼る位置の印（受けの幅 × 底の奥行き）を、同じく奥の縁に寄せて刷る（エンジンと同じ）。
    """
    if p["push_part"] == LIFT:
        g, b = p["base_glue"], p["base_side"]
        cw, cd = cradle_width(p), cradle_depth(p)
        x0, x1, y0, y1 = g + b / 2 - cw / 2, g + b / 2 + cw / 2, g + 1, g + 1 + cd
        return [{"kind": "line", "pts": [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)], "stroke": LINE, "sw": 0.3},
                {"kind": "line", "pts": [(x0, y0), (x1, y1)], "stroke": LINE, "sw": 0.2}]
    if not _axle(p):
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
    if p["push_part"] == LIFT:
        # 筒を外す形（EP-0017）: 内筒・つまみ・糸は無く、2 受けがある
        rows.insert(1, {"number": 2, "key": "cradle", "name": "扇の受け", "qty": 1, "material": paper, "substituted": True,
                        "original_guess": "無し（本人のレビューで足した。糸の代わりに扇を束ねて開いておく小さい部品）", "reason": why})
    if p["push_part"] == "tab":
        rows.append({"number": 6, "key": "knob", "name": "つまみ", "qty": 1, "material": f"竹串（長さ約 {p['tube_side'] + 20}mm に切り、先を落とす）", "substituted": True, "original_guess": "不明（絵の細い棒の素材は読めない）", "reason": "家にあり、細くて溝を通るため"})
    if p["push_part"] == "stick":
        rows.append({"number": 6, "key": "stick", "name": "柄", "qty": 1, "material": f"割り箸（長さ約 {p['pusher_height']}mm）", "substituted": True, "original_guess": "不明", "reason": "家にあり、押す力に耐えるため"})
    if _axle(p):
        rows.append({"number": 7, "key": "thread", "name": "糸", "qty": 3, "material": f"たこ糸（軸に 1 本。開く糸を試す時は、さらに 2 本 各約 {thread_mm(p):.0f}mm ＋結ぶ分）", "substituted": True, "original_guess": "不明", "reason": "家にあり、細い穴を通るため"})
    return rows


def thread_mm(p):
    # 高さは筒の穴から測る。穴は口から THREAD_DEPTH 下にあるので、口から測ると糸の長さが最大で約 3mm ずれた。
    z0 = p["pivot_above_rim"] + THREAD_DEPTH
    return shortest_free_thread(p["tube_side"], THREAD_RADIUS, z0 - p["push_amount"], z0)


RESULTS = ("動いた", "動かない", "わからない")


def materials(p):
    """型紙の「用意する物」。素材は部品表だけから刷り、2 か所に手で書かない。"""
    rows = bom(p)
    # 穴があるのに竹串の行が無い形（内筒を下から押す形・柄の形）は、穴をあける竹串を道具に書く（手順に「穴は竹串の先であける」。#294、本人の確認 11-06）。
    # つまみの形は竹串の行がもう有る。エンジン（paper-to-toy の e189dc6）と同じ結果になる事を tests/test_next_sheets.py が見る。
    # 部品を組まずに形の値で決める。作り方の印の一覧が全部の記録で読むので、字の寸法が混ざった記録で落とさないため。
    tools = "のり、はさみ、定規"
    if not frozen() and _axle(p) and not any("竹串" in r["material"] for r in rows):
        tools += "、竹串（穴あけ）"
    lines = [f"{rows[0]['material']}を 1 枚（全部品を同じ紙に刷る）", tools]
    lines += [f"{r['material']} {r['qty']} 本" for r in rows if r["number"] == 6]
    lines += [r["material"] for r in rows if r["number"] == 7]
    return lines


TITLES = {"tab": "つまみで動かす", "tube": "内筒を下から押す", "stick": "割り箸の柄で動かす", "lift": "筒を外すと扇が開く"}


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
    row = max(base.height, fig.height)
    if "cradle" in by_key:
        # 2 受け（筒を外す形、EP-0017）は小さいので、像の右に置く（左の列の高さを増やさない。エンジンと同じ）
        c = by_key["cradle"]
        c.x, c.y = fig.x + fig.width + gap * 2, left_y
        row = max(row, c.height)
    left_y += row + gap
    # 文字の列の幅は扇の本体まで取る。足は真ん中の 1 枚の高さにしか無く、文字と重なれば配置の検査（F5.overlap）が落とす。
    return left_y, fan.x - page.x0 - gap, page.x0


def steps(p):
    """組み方。部品番号は型紙と同じ。押し方と中心の置き方で変わる所だけを分ける。"""
    if p["push_part"] == LIFT:
        # 筒を外す形（EP-0017）の組み方。エンジンと同じ字。新しい形なので手順の番号は新しく振る（この形の記録の鍵はまだ無い）。
        # 最後は本人の言い方の動き（筒を上へ外すと扇が開く）
        return ["刷った物差しに定規を当て、10cm か確かめる",
                "部品を実線で切る（穴はあけない）",
                "1 外筒を色の境で山折りし、糊代で貼って角筒にする",
                "3 台の 4 つの糊代を山折りの線で下へ折り、伏せて机に置く（印のある上の面が台になる）",
                "4 扇を色の境で、端から谷折り・山折りを交互にして蛇腹に畳む",
                "2 受けを 2 本の破線で谷折りして U の字にし、底の面の裏を 3 台の印に貼る",
                "畳んだ 4 扇の下の端を 2 受けに入れ、扇の下の端を受けの底に、扇の両端の板の下の所を受けの左右の面に貼る（受けの刷った面は全部が糊代）",
                "5 像の足を、3 台の受けの前に貼る",
                "4 扇を手で畳み、上から 1 外筒をかぶせる。筒を上へ外すと、扇が開く"]
    # まず筒を 1 つ作る（v8）。試行で、手が止まったのは平面から立体への最初の一歩で、「筒ができただけで目の色が変わって」
    # 取り組み始めた（本人の補足所見、11-04）。最初に形が 1 つできる順にする。
    out = ["刷った物差しに定規を当て、10cm か確かめる"]
    if p["push_part"] == "tab":
        out.append("まず 1 外筒だけを実線で切る。溝は下の端からはさみで切り込む（くり抜かない）")
    else:
        out.append("まず 1 外筒だけを実線で切る")
    out.append(f"1 外筒を色の境で{tube_fold()}し、糊代で貼って角筒にする")
    out.append("残りの部品を実線で切る。穴は竹串の先であける")
    if p["push_part"] in ("tab", "tube"):
        # 外筒を山折りに直すと、「同じように」は、破線を谷折りで刷る内筒と食い違う。本人の決定（11-06）の文で、一字も変えない。内筒は隠れる部品で谷のまま。
        out.append("2 内筒も同じように角筒にする" if frozen() else "2 内筒は破線で谷折りし、糊代で貼って角筒にする")
    if p["push_part"] == "tab":
        out.append("竹串を 2 内筒の 2 つの穴に通す")
    if p["push_part"] == "stick":
        # 内筒と同じ型の文（本人の確認 11-06）。「同じように」は山折りと読めて、破線を谷折りで刷る土台と食い違う。
        out.append("2 土台も同じように角筒にし、割り箸の先を下から差し込んで貼る" if frozen() else "2 土台は破線で谷折りし、糊代で貼って角筒にし、割り箸の先を下から差し込んで貼る")
    out.append("3 台で 2 の上に蓋をする")
    out.append("4 扇を色の境で、端から谷折り・山折りを交互にして蛇腹に畳む")
    if _axle(p):
        out.append("糸を 5 像の穴と 4 扇の中心側の穴の列に通し、ゆるく結ぶ")
        out.append("4 扇の真ん中の足を、糊代の境の破線で折り、足の糊代を 3 台の印に貼る")
        out.append("5 像の足を 3 台に貼る")
    else:
        out.append("4 扇の端を 3 台に貼り、5 像の足も台に貼る")
    if p["push_part"] == "tab":
        out.append("内筒を 1 外筒に入れ、竹串の端を溝から出す")
        if not frozen():
            # 組み立ての最後の動き（本人の追加 11-06「上にスライドさせて蛇腹が開く所まで」）。後ろに足すので、前の手順の番号はずれない（記録が手順の番号を鍵にしている）。
            # 文は本人の答えのとおり押し上げる量を言わない。エンジン（e189dc6）の 3D の操作から作った文と同じ。
            out.append("竹串の端を溝に沿って上に押し上げると、4 扇が 1 外筒の口から出て、蛇腹が開く")
    else:
        out.append("押す部品を 1 外筒に下から入れる")
    return out


def measures(p):
    """手順の紙の「作る前に」の問いと、試した事の欄（U-25 の案 1）。

    開き具合の角度と回数は今回の課題ではない（本人、11-04）ので欄を置かない。予想は数でなく、動き方を言葉か絵で書く。
    中身は凍結の後に utsushi 側へ移す（U-30）。それまではここに置く。
    """
    # 筒を外す形（EP-0017）は押す部品が無いので、問いの動きも筒を外す事にする（「押すと」のままだと組み方と合わない）
    act = "筒を外すと" if p["push_part"] == LIFT else "押すと"
    return {"predict": f"{act}、どこがどう動くと思いますか（言葉か絵で）", "rows": []}


def diagram(x, y, w, h, p):
    """組み上がりの断面の見取り図。寸法の図ではなく、部品の並びを見せるだけの絵。"""
    s = (h - 8) / (p["tube_height"] + p["fold_height"])
    cx, base = x + w / 2, y + h - 4
    tw, th = p["tube_side"] * s, p["tube_height"] * s
    shapes = [{"kind": "rect", "x": cx - tw / 2, "y": base - th, "w": tw, "h": th}]
    if p["push_part"] == LIFT:
        # 筒を外す形（EP-0017）: 伏せた台の上に、受けで束ねた畳んだ扇が立ち、筒がかぶさる。押す部品は無い
        g = p["base_glue"] * s
        shapes.append({"kind": "rect", "x": cx - p["base_side"] * s / 2, "y": base - g, "w": p["base_side"] * s, "h": g, "dash": "1,0.6"})
        shapes.append({"kind": "rect", "x": cx - 1.2, "y": base - g - p["fold_height"] * s, "w": 2.4, "h": p["fold_height"] * s, "dash": "1,0.6"})
        return shapes
    inner = p["pusher_side"] * s
    rest_top = base - (p["tube_height"] - p["push_amount"]) * s
    length = p["pusher_height"] * s
    if p["push_part"] == "stick":
        stage = p["stage_height"] * s
        shapes.append({"kind": "rect", "x": cx - inner / 2, "y": rest_top, "w": inner, "h": stage, "dash": "1,0.6"})
        # 割り箸は筒の下へ出るが、絵の枠（y+h）の中で止める。枠の外へ出ると下の説明と重なる（印刷の担当が見つけた）。
        shapes.append({"kind": "rect", "x": cx - 0.6, "y": rest_top + stage, "w": 1.2, "h": max(0.0, min(length - stage, y + h - rest_top - stage)), "dash": "1,0.6"})
    else:
        shapes.append({"kind": "rect", "x": cx - inner / 2, "y": rest_top, "w": inner, "h": length, "dash": "1,0.6"})
    if p["push_part"] == "tab":
        shapes.append({"kind": "line", "x1": cx - tw / 2 - 5, "y1": rest_top + length / 2, "x2": cx, "y2": rest_top + length / 2})
    shapes.append({"kind": "rect", "x": cx - 1.2, "y": rest_top - p["fold_height"] * s, "w": 2.4, "h": p["fold_height"] * s, "dash": "1,0.6"})
    return shapes
