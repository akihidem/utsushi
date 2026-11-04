"""雛形 pivot_counterweight: 箱の胴に軸を通し、重りで頭を揺らす。張子の首振り虎の仮説を試す。

頭の支え方は仮説の違いなので描き分ける（docs/process/research/12）。寸法は手元の複写の図の比から出した。
どの値も実物では未確認。Claude が変えてよいのは RANGES の名前の値だけ。
"""
import math

from shapely.geometry import LineString, Polygon

from ..model import Failure, Part
from ..pivot_model import center, paper_mass, period_s, rest_tilt_deg

ID = "pivot_counterweight"
# 刷った組の版（U-31）。slider_fan.SHEET_SET と同じ意味。
SHEET_SET = "tora-v2"
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


def check_physics(p):
    out = []
    H, ax = p["body_height"], p["axle_height"]
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
        if p["ear_length"] < 2 * HOLE_MARGIN:
            out.append(Failure("F5.pivot", "耳", f"耳が短く、穴の前後に {HOLE_MARGIN}mm 取れない"))
        reach = axle_to_head_top(p) + p["head_h"]
        room = p["ear_length"] - HOLE_MARGIN
        if room < reach and math.degrees(math.asin(room / reach)) < MIN_SWING:
            out.append(Failure("F5.pivot", "頭", f"頭が胴に当たるまで {MIN_SWING}° 揺れない"))
        if H - HOLE_MARGIN - reach < 3:
            out.append(Failure("F5.pivot", "頭", "頭の下端が床に近すぎる"))
    else:
        # 首の帯が穴の縁に当たらずに揺れる余裕。穴の中で上下に動ける量を、軸からの距離で角度に直す。
        room = (p["opening"] - p["strip_width"] * 0.2) / 2
        if room <= 0 or math.degrees(math.atan2(room, 6)) < MIN_SWING:
            out.append(Failure("F5.pivot", "首", f"首が穴の縁に当たるまで {MIN_SWING}° 揺れない"))
        if p["head_h"] / 2 > ax - 3:
            out.append(Failure("F5.pivot", "頭", "頭の下端が床に近すぎる"))
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
    return [(2 * x + w - a, 2 * y + h - b) for a, b in pts]


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
    return Part(2, "head", "頭", outline, label_xy=(w * 0.5, h * 0.6), label="2", art=art)


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
    body = Part(1, "body", "胴", pts, label_xy=(H + 2, top0 + 2), label="1 胴")
    body.valley = [((H, top0), (H + L, top0)), ((H, top1), (H + L, top1)), ((H, b0), (H + L, b0)), ((H, b1), (H + L, b1)), ((H, b0), (H, b1)), ((H + L, b0), (H + L, b1)),
                   ((0, b0), (H, b0)), ((0, b1), (H, b1)), ((H + L, b0), (H + L + H, b0)), ((H + L, b1), (H + L + H, b1))]
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
        back = 6  # 前の壁の少し後ろに軸を通す。首の帯が壁に当たらないように
        body.holes = [(H + back, top1 + H - ax, 1.2), (H + back, bottom - (H - ax), 1.2)]
        op = p["opening"]
        cy = (b0 + b1) / 2
        body.cuts = [(H - ax - op / 2, cy - op / 2, op, op)]
        # 穴の縁の橙。絵の首の穴の色を前の壁に描く
        body.art.append(_panel(H - ax - op / 2 - 1.5, cy - op / 2 - 1.5, H - ax + op / 2 + 1.5, cy + op / 2 + 1.5, RIM))
    head = _head_part(p)
    sw = p["strip_width"]
    length = (p["neck_length"] + 12) if not hang else axle_to_head_top(p) + 10
    # 帯は半分に折って 2 枚にする。1 枚では頭を支えるには柔らかいと見込むため。
    strip = Part(3, "strip", "首の帯", [(0, 0), (2 * sw, 0), (2 * sw, length), (0, length)], label_xy=(1, 1.5), label="3",
                 valley=[((sw, 0), (sw, length))], holes=[(sw / 2, 6, 1.0), (1.5 * sw, 6, 1.0)])
    tail = Part(4, "tail", "尾", [(0, 0), (8, 0), (8, 56), (0, 56)], label_xy=(1, 1.5), label="4",
                art=[_panel(0.1, 0.1, 7.9, 55.9, TIGER)] + [{"kind": "line", "pts": [(0.3, y), (7.7, y)], "stroke": STRIPE, "sw": 0.5} for y in range(10, 54, 8)])
    out = [body, head, strip, tail]
    if not hang:
        # 紙の頭は軽いので、重りは軸の真下に下げる（research/12）。下げる腕が無いと寸法どおりに作れない。
        drop_len = max(p["weight_below_axle"] + 8, 20)
        out.append(Part(5, "drop", "重りの腕", [(0, 0), (8, 0), (8, drop_len), (0, drop_len)], label_xy=(1, 8), label="5", holes=[(4, 4, 1.0)]))
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
    return [
        {"number": 1, "key": "body", "name": "胴", "qty": 1, "material": paper, "substituted": True, "original_guess": "張子（手元の解説の呼び名による）", "reason": why},
        {"number": 2, "key": "head", "name": "頭", "qty": 1, "material": paper, "substituted": True, "original_guess": "張子（同じ）", "reason": why},
        {"number": 3, "key": "strip", "name": "首の帯", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明", "reason": why},
        {"number": 4, "key": "tail", "name": "尾", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明", "reason": why},
        {"number": 7, "key": "axle", "name": "軸", "qty": 1, "material": f"竹串（長さ約 {p['body_width'] + 20}mm に切り、先を落とす）", "substituted": True, "original_guess": "不明", "reason": "家にあり、穴に通しやすいため"},
        {"number": 8, "key": "weight", "name": "重り", "qty": 1, "material": f"油粘土 {p['weight_g']:g}g", "substituted": True, "original_guess": "不明", "reason": "量を変えて試しやすいため"},
    ]


def materials(p):
    rows = bom(p)
    return [f"{rows[0]['material']}を 1 枚", "のり、はさみ、定規", rows[4]["material"], rows[5]["material"]]


def steps(p):
    out = ["刷った物差しに定規を当て、10cm か確かめる", "部品を実線で切る。胴の穴は竹串の先であける"]
    if p["mount"] == "neck":
        out.append("1 胴の前の壁の四角い穴を切る（カッターは大人がする）")
    out += ["1 胴を破線で谷折りし、糊代で貼って箱にする。上の面は後で閉じる", "3 首の帯を半分に折って貼る。穴は重ねたまま通す"]
    if p["mount"] == "neck":
        out += ["3 首の帯の前の端に 2 頭を貼る", "帯を前の壁の穴に入れ、竹串を胴の穴と帯の穴に通す", "5 重りの腕の穴にも竹串を通し、下の端に粘土を付ける。腕は 3 首の帯に貼る", "頭の傾きを見て、腕を貼る位置を決める"]
    else:
        out += ["3 首の帯の下の端に 2 頭を貼る", "竹串を耳の穴と帯の穴に通す", "粘土を頭の裏のあごの近くに貼る"]
    out += ["1 胴の上の面を閉じる", "4 尾を丸くして、後ろに貼る"]
    return out


# 虎の物差しは頭が揺れるかどうかで足りる（本人の判断、research/15）。周期の差で仮説を見分ける設計にしない。
RESULTS = ("揺れた", "揺れない")


def measures(p):
    """揺れるかの二択でなく、動き方を言葉か絵で予想する（U-25 の案 1）。動かした物は数でないので残す。"""
    return {"predict": "頭はどう動くと思いますか（言葉か絵で）", "rows": [[("動かした物（手・息・団扇）", 40)]]}


def diagram(x, y, w, h, p):
    s = min(w / (p["body_length"] + p["head_w"]), h / (p["body_height"] + 6))
    bx, by = x + p["head_w"] * s, y + 3
    shapes = [{"kind": "rect", "x": bx, "y": by, "w": p["body_length"] * s, "h": p["body_height"] * s}]
    ax_y = by + (p["body_height"] - p["axle_height"]) * s
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
