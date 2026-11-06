"""雛形 wheel_cart: 紙の車輪を竹串の軸で付けて転がす。鼠車（大黒の鼠乗り）と俵ころがしの仮説を試す（線 cart、11-04）。

1 本に 2 つの形を乗せる（線の契約: 雛形は 1 本に線の玩具を全部乗せる）。玩具ごとの違いは body の値で出し、
仮説の違い（どう遊ぶか）は HYP_KEY の drive で出す。
- body "cart": 板の台（下に縁を折った浅い箱）に紙の車 4 つ。上に鼠と乗り手の絵の板を立てる（鼠車）
- body "bale": 紙の筒の俵。坂（樋の形の溝板）を転がすか、軸を通して糸で引く（俵）
樋の板（R0000004-L-3）は入れない。絵では竹筒（L-2）を貫いて描かれていて、単独の玩具でなく竹筒の玩具の部品と見たため。
寸法は図の比と手の大きさからの見込みで、どの値も実物では未確認。Claude が変えてよいのは ALLOWED の名前の値だけ。
"""
import math

from shapely.geometry import LineString, Polygon, box

from ._paper import paper_name
from ..model import Failure, Part

ID = "wheel_cart"
SHEET_SET = "wheel_cart-v1"
# 手順の紙の図の説明（instructions.compose_sheet）。御来迎の筒の言葉を刷らないため。
DIAGRAM_CAPTION = "車と軸と台（破線は軸）"
# 結果の欄の見出し。この形の玩具に合う問いにする。
RESULT_HEAD = "おもちゃとして転がりましたか（1 つに丸）"
HYP_KEY = "drive"
DRIVES = ("pull", "slope")
BODIES = ("cart", "bale")
DEFAULTS = {
    "drive": "pull", "body": "cart",
    # 台車。台の縁（skirt）は軸の穴を持つ壁。軸は台の板の下 axle_drop、端から axle_in の所に通す。
    "deck_length": 72, "deck_width": 40, "skirt": 12, "axle_drop": 6, "axle_in": 15, "wheel_d": 26,
    # 台の穴は軸（竹串）が回る大きさ。車の穴は軸を締める大きさ（AXLE_R より小さく、決まりの値）。
    "axle_hole": 2.0, "glue": 6,
    # 俵。筒の周りの長さは π·bale_d。坂は俵の長さに隙間を足した溝。
    "bale_d": 26, "bale_length": 46, "ramp_length": 180, "rail": 10,
    "paper_gsm": 150,
}
RANGES = {
    "deck_length": (50, 90), "deck_width": (28, 56), "skirt": (8, 22), "axle_drop": (3, 18), "axle_in": (6, 30),
    "wheel_d": (14, 40), "axle_hole": (1.4, 3.5), "glue": (4, 10),
    "bale_d": (16, 34), "bale_length": (24, 70), "ramp_length": (100, 186), "rail": (5, 16),
    "paper_gsm": (40, 400),
}
ALLOWED = ("deck_length", "deck_width", "skirt", "axle_drop", "axle_in", "wheel_d", "axle_hole", "bale_d", "bale_length", "ramp_length", "rail")
AXLE_R = 1.5  # 竹串（太さ 3mm 前後）の半径の見込み。手元の竹串を測ったら置き換える
WHEEL_HOLE = AXLE_R - 0.3  # 車は軸に締めて一緒に回す。台の穴で回るので、車の穴は緩くしない
HOLE_MARGIN = 3  # 穴の縁から紙の端までの見込み。これより狭いと 150g/m² の紙は裂けやすい
MIN_CLEAR = 2  # 台の縁の下端と床の隙間。0 だと縁が床をこすって止まる
MIN_PLAY, MAX_PLAY = 0.3, 1.2  # 台の穴と軸の隙間。狭いと回らず、広いと車が首を振る（見込み）
WHEEL_GAP = 2  # 前と後ろの車の間。0 だと擦れ合う
RAMP_CLEAR = 3  # 坂の溝の中で、俵の両端に空ける隙間
TAB = 5  # 俵の筒の両端の糊代の高さ
BALE_RATIO = 1.0  # 俵の長さ ÷ 太さ。これより短いと、坂で端を下に倒れやすい（見込み）
RAIL_RATIO = 0.3  # 坂の縁の高さ ÷ 俵の太さ。低いと俵が溝から跳ね出る（見込み）
MIN_TURNS = 2  # 坂の上で俵が回る数。1 回り足らずで止まると、転がったか滑ったかが見分けにくい

# 江戸の色（朱・藍・黄土・墨・胡粉）と、絵の木と藁の色。原図の画素は使わず、目で見て選んだ。
SHU, AI, OCHRE, SUMI, GOFUN = "#c8553d", "#2e4a6b", "#c9a35a", "#2a2622", "#f3eee2"
WOOD, WOOD_DARK, BENGARA, SKIN, PANTS = "#d8bd84", "#b08a45", "#7a4a2a", "#ecc4ac", "#d9a08a"
STRAW, STRAW_LINE, ROPE = "#c69356", "#7a4a2a", "#e0bf7e"

TITLES = {("cart", "pull"): "板の台に車を付け、糸で引く", ("cart", "slope"): "板の台に車を付け、坂に置いて離す",
          ("bale", "pull"): "俵に軸を通し、糸で引く", ("bale", "slope"): "俵を溝の坂で転がす"}
PARAM_NAMES = {"drive": "遊び方", "body": "形", "deck_length": "台の長さ", "deck_width": "台の幅", "skirt": "台の縁の高さ",
               "axle_drop": "台の板から軸まで", "axle_in": "台の端から軸まで", "wheel_d": "車の直径", "axle_hole": "台の穴の半径",
               "bale_d": "俵の太さ", "bale_length": "俵の長さ", "ramp_length": "坂の長さ", "rail": "坂の縁の高さ"}


def title(p):
    return TITLES[(p["body"], p["drive"])]


def spec():
    return {"template_id": ID, "defaults": DEFAULTS, "ranges": RANGES, "drive": DRIVES, "body": BODIES}


def check_range(p):
    out = []
    for k, v in p.items():
        if k in ("drive", "body"):
            allowed = DRIVES if k == "drive" else BODIES
            if v not in allowed:
                out.append(Failure("F5.range", k, f"{v} は {allowed} のどれでもない"))
        elif k not in RANGES:
            out.append(Failure("F5.range", k, "知らない寸法の名前"))
        elif not isinstance(v, (int, float)) or isinstance(v, bool) or not RANGES[k][0] <= v <= RANGES[k][1]:
            out.append(Failure("F5.range", k, f"{v} は範囲 {RANGES[k]} の外"))
    return out


def ground_clear(p):
    """台の縁の下端と床の隙間。車の半径から、軸より下に出る縁の分を引く。"""
    return p["wheel_d"] / 2 - (p["skirt"] - p["axle_drop"])


def ramp_inner(p):
    return p["bale_length"] + 2 * RAMP_CLEAR


def check_physics(p):
    out = []
    play = p["axle_hole"] - AXLE_R
    if p["body"] == "cart":
        if ground_clear(p) < MIN_CLEAR:
            out.append(Failure("F5.wheel", "車", f"台の縁の下端が床から {ground_clear(p):.1f}mm で、床をこする（{MIN_CLEAR}mm から）。車を大きくするか、軸を下げる"))
        # 穴は縁の壁の中にある。上は台の板の折り目、下は縁の下端、横は縁の端（端の壁と貼る角）。
        for where, room in (("台の板の折り目", p["axle_drop"]), ("縁の下端", p["skirt"] - p["axle_drop"]), ("縁の端", p["axle_in"])):
            if room - p["axle_hole"] < HOLE_MARGIN:
                out.append(Failure("F5.axle", "軸の穴", f"穴から{where}まで {room - p['axle_hole']:.1f}mm で、裂けやすい（{HOLE_MARGIN}mm から）"))
        if p["deck_length"] - 2 * p["axle_in"] < p["wheel_d"] + WHEEL_GAP:
            out.append(Failure("F5.wheel", "車", f"前と後ろの車が {p['deck_length'] - 2 * p['axle_in']:.0f}mm 離れているだけで、直径 {p['wheel_d']} の車が擦れ合う"))
        if p["glue"] > p["skirt"] - 3:
            out.append(Failure("F5.glue", "糊代", f"糊代 {p['glue']} が縁の高さ {p['skirt']} に収まらない"))
    else:
        if p["bale_length"] < BALE_RATIO * p["bale_d"]:
            out.append(Failure("F5.roll", "俵", f"俵の長さ {p['bale_length']} が太さ {p['bale_d']} より短く、端を下に倒れやすい"))
        if p["drive"] == "slope":
            if p["rail"] < RAIL_RATIO * p["bale_d"]:
                out.append(Failure("F5.roll", "坂", f"坂の縁 {p['rail']}mm が低く、太さ {p['bale_d']} の俵が溝から出やすい（{RAIL_RATIO * p['bale_d']:.1f}mm から）"))
            if p["ramp_length"] < MIN_TURNS * math.pi * p["bale_d"]:
                out.append(Failure("F5.roll", "坂", f"坂 {p['ramp_length']}mm の上で俵が {MIN_TURNS} 回りしない"))
        elif p["bale_d"] / 2 - p["axle_hole"] < HOLE_MARGIN:
            out.append(Failure("F5.axle", "軸の穴", "俵の蓋の穴から縁までが狭く、裂けやすい"))
    # 軸の隙間は両方の形で同じ（台の穴でも俵の蓋の穴でも、軸が回る所）。坂だけの俵は軸を通さないので見ない。
    if not (p["body"] == "bale" and p["drive"] == "slope"):
        if play < MIN_PLAY:
            out.append(Failure("F5.axle", "軸の穴", f"穴と軸の隙間 {play:.1f}mm で、軸が回らない（{MIN_PLAY}mm から）"))
        elif play > MAX_PLAY:
            out.append(Failure("F5.axle", "軸の穴", f"穴と軸の隙間 {play:.1f}mm で、車が首を振る（{MAX_PLAY}mm まで）"))
    return out


def metrics(p):
    """台帳の式（F7）。床との差を数で持つ。版を変えた時に、余裕が増えたか減ったかを数で比べるため。"""
    if p["body"] == "cart":
        return {"ground_clear_mm": ground_clear(p), "axle_play_mm": p["axle_hole"] - AXLE_R, "roll_per_turn_mm": math.pi * p["wheel_d"]}
    turns = p["ramp_length"] / (math.pi * p["bale_d"]) if p["drive"] == "slope" else 0.0
    return {"ground_clear_mm": 0.0, "axle_play_mm": p["axle_hole"] - AXLE_R if p["drive"] == "pull" else 0.0, "roll_per_turn_mm": math.pi * p["bale_d"], "ramp_turns": turns}


# --- 形の部品 ---

def _circle(cx, cy, r, n=48):
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def _panel(x0, y0, x1, y1, fill):
    return {"kind": "poly", "pts": [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], "fill": fill}


def _clip(pts, shape, fill, stroke=None, sw=0.2):
    """絵の多角形を部品の形の内側で切る。部品の外に出た絵は F5.image_box で落ちるので、描く側で収める。"""
    g = Polygon(pts).buffer(0).intersection(shape)
    out = []
    for q in getattr(g, "geoms", [g]):
        if q.geom_type == "Polygon" and q.area > 0.05:
            item = {"kind": "poly", "pts": list(q.exterior.coords)[:-1], "fill": fill}
            if stroke:
                item.update(stroke=stroke, sw=sw)
            out.append(item)
    return out


def _clip_line(pts, shape, stroke, sw):
    g = LineString(pts).intersection(shape)
    return [{"kind": "line", "pts": list(q.coords), "stroke": stroke, "sw": sw} for q in getattr(g, "geoms", [g]) if not q.is_empty and q.geom_type == "LineString"]


def _deck(p):
    """台: 中の板と、四方に折り下げる縁。前後の縁の両端の糊代を、長い縁の内側に貼って箱にする。"""
    L, W, h, g = p["deck_length"], p["deck_width"], p["skirt"], p["glue"]
    pts = [(h, 0), (h + L, 0), (h + L, h), (h + L + 2, h - g), (2 * h + L - 1.5, h - g), (2 * h + L, h), (2 * h + L, h + W),
           (2 * h + L - 1.5, h + W + g), (h + L + 2, h + W + g), (h + L, h + W), (h + L, 2 * h + W), (h, 2 * h + W), (h, h + W),
           (h - 2, h + W + g), (1.5, h + W + g), (0, h + W), (0, h), (1.5, h - g), (h - 2, h - g), (h, h)]
    part = Part(1, "deck", "台", pts, label_xy=(h + 2, h + 2), label="1 台")
    # 縁は台の板の下へ折る。刷った面を外に出すので山折り。
    part.mountain = [((h, h), (h + L, h)), ((h, h + W), (h + L, h + W)), ((h, h), (h, h + W)), ((h + L, h), (h + L, h + W)),
                     ((0, h), (h, h)), ((0, h + W), (h, h + W)), ((h + L, h), (2 * h + L, h)), ((h + L, h + W), (2 * h + L, h + W))]
    part.glue = [[(h + L, h), (h + L + 2, h - g), (2 * h + L - 1.5, h - g), (2 * h + L, h)], [(h + L, h + W), (2 * h + L, h + W), (2 * h + L - 1.5, h + W + g), (h + L + 2, h + W + g)],
                 [(0, h), (1.5, h - g), (h - 2, h - g), (h, h)], [(0, h + W), (h, h + W), (h - 2, h + W + g), (1.5, h + W + g)]]
    e = 0.3  # 折り目の上に色を置かない。色の切れ目の細い白が、折る所の目印になる（本人の決定 d）
    part.art = [_panel(h + e, h + e, h + L - e, h + W - e, WOOD), _panel(h + e, e, h + L - e, h - e, WOOD_DARK), _panel(h + e, h + W + e, h + L - e, 2 * h + W - e, WOOD_DARK),
                _panel(e, h + e, h - e, h + W - e, WOOD_DARK), _panel(h + L + e, h + e, 2 * h + L - e, h + W - e, WOOD_DARK)]
    # 板の木目。絵の板の縁の濃い茶を、縁の折り目の手前の帯で描く。
    part.art += [{"kind": "line", "pts": [(h + 3, h + y), (h + L - 3, h + y + 0.6)], "stroke": WOOD_DARK, "sw": 0.3} for y in (W * 0.3, W * 0.55, W * 0.8)]
    part.art += [_panel(h + e, h + e, h + L - e, h + 1.6, BENGARA), _panel(h + e, h + W - 1.6, h + L - e, h + W - e, BENGARA)]
    r, ai, ad = p["axle_hole"], p["axle_in"], p["axle_drop"]
    part.holes = [(h + ai, h - ad, r), (h + L - ai, h - ad, r), (h + ai, h + W + ad, r), (h + L - ai, h + W + ad, r)]
    if p["drive"] == "pull":
        part.holes.append((h + L + h / 2, h + W / 2, 1.0))  # 前の壁に糸を通す
    part.hide_folds = True
    return part


def _wheel(n, p):
    """車 1 つ。2 枚の円を細い橋でつなぎ、橋で山折りして貼り合わせる。1 枚では軸に締めた所が柔らかく、首を振ると見込むため。"""
    R = p["wheel_d"] / 2
    b = min(6, R)
    shape = Polygon(_circle(R, R, R)).union(Polygon(_circle(3 * R, R, R))).union(box(2 * R - 3, R - b / 2, 2 * R + 3, R + b / 2))
    pts = list(shape.exterior.coords)[:-1]
    part = Part(n, f"wheel{n - 3}", f"車 {n - 3}", pts, label_xy=(R - 1.2, R + 2.2), label=str(n))
    part.mountain = [((2 * R, R - b / 2), (2 * R, R + b / 2))]
    part.holes = [(R, R, WHEEL_HOLE), (3 * R, R, WHEEL_HOLE)]
    for cx in (R, 3 * R):
        # 絵の車は茶の円に濃い縁と中の点。車の色を朱にしないのは、原図が茶で塗っているため。
        part.art += [{"kind": "poly", "pts": _circle(cx, R, R - 0.6), "fill": BENGARA, "stroke": SUMI, "sw": 0.3},
                     {"kind": "poly", "pts": _circle(cx, R, R * 0.72), "fill": "#9a6440"}]
    part.hide_folds = True
    return part


# 鼠と乗り手の絵を見て手で取った点（NDL コマ 19 左頁の切り出しを 1000px 幅にした座標）。絵の画素は使っていない。
_SIL = [(15, 795), (40, 745), (95, 680), (110, 640), (150, 578), (185, 628), (215, 605), (270, 590), (318, 618), (322, 650), (300, 600),
        (240, 540), (234, 450), (252, 412), (222, 396), (218, 240), (250, 172), (300, 140), (358, 135), (356, 88), (352, 22), (420, 5),
        (560, 12), (612, 60), (602, 92), (640, 90), (720, 112), (770, 182), (795, 300), (790, 420), (765, 478), (830, 520), (870, 580),
        (882, 680), (872, 760), (862, 880), (60, 880), (62, 840), (110, 832), (50, 815)]
_ROBE = [(222, 240), (260, 170), (370, 200), (540, 215), (700, 290), (712, 445), (590, 462), (520, 432), (252, 412), (222, 396)]
_PANTS = [(236, 448), (252, 420), (520, 432), (600, 462), (662, 520), (652, 690), (540, 700), (480, 562), (330, 532), (240, 525)]
_FACE = [(366, 86), (420, 70), (510, 80), (560, 102), (556, 170), (520, 200), (430, 206), (380, 182), (362, 130)]
_HAT = [(354, 24), (420, 6), (560, 13), (611, 60), (601, 93), (560, 102), (510, 80), (420, 70), (364, 86)]
_COLLAR = [(380, 205), (520, 212), (500, 238), (400, 242)]
_CUFFS = [[(256, 262), (300, 252), (305, 390), (266, 396)], [(545, 322), (590, 316), (596, 430), (556, 436)]]
_FEET = [[(540, 700), (652, 698), (662, 742), (546, 746)]]
_EAR = [(240, 622), (285, 606), (302, 640), (256, 668)]
_MOUTH = [(22, 796), (95, 790), (100, 805), (42, 810)]
_LINES = [[(330, 860), (360, 820), (400, 862)], [(620, 870), (660, 838)], [(470, 470), (560, 560)], [(430, 120), (445, 128)], [(480, 122), (500, 128)]]
_EYE = (112, 722, 18)


def _rider(n, p, mirror):
    """鼠と乗り手の板。2 枚を背中合わせに貼り、下の糊代を左右へ開いて台に貼る。2 枚にするのは、紙 1 枚では立たせた時に反るため。"""
    w = p["deck_length"] - 6
    s = w / 870
    hgt = 880 * s
    tab = 6
    f = (lambda x: w - (x - 12) * s) if mirror else (lambda x: (x - 12) * s)
    conv = lambda ps: [(f(x), y * s) for x, y in ps]
    sil = conv(_SIL)
    t0, t1 = w * 0.2, w * 0.8
    outline = Polygon(sil).buffer(0).union(box(t0, hgt - 0.01, t1, hgt + tab))
    pts = list(outline.exterior.coords)[:-1]
    key = "rider_b" if mirror else "rider"
    part = Part(n, key, "乗り手（裏）" if mirror else "乗り手", pts, label_xy=(w * 0.45, hgt - 9), label=str(n))
    part.mountain = [((t0, hgt), (t1, hgt))] if mirror else []
    part.valley = [] if mirror else [((t0, hgt), (t1, hgt))]
    part.glue = [[(t0, hgt), (t1, hgt), (t1, hgt + tab), (t0, hgt + tab)]]
    shape = Polygon(sil).buffer(0).intersection(box(-1, -1, w + 1, hgt - 0.4)).buffer(-0.25)
    art = _clip(sil, shape, GOFUN, SUMI, 0.3)
    for pts_, fill in ((_ROBE, OCHRE), (_PANTS, PANTS), (_FACE, SKIN), (_HAT, OCHRE), (_COLLAR, BENGARA), (_EAR, SHU), (_MOUTH, SHU)):
        art += _clip(conv(pts_), shape, fill, SUMI, 0.2)
    for c in _CUFFS:
        art += _clip(conv(c), shape, BENGARA)
    for c in _FEET:
        art += _clip(conv(c), shape, SUMI)
    ex, ey, er = _EYE
    art += _clip(conv(_circle(ex, ey, er, 16)), shape, SUMI)
    for line in _LINES:
        art += _clip_line(conv(line), shape, SUMI, 0.3)
    part.art = art
    part.hide_folds = True
    return part


def _tube(p):
    """俵の筒。横が周り（π·太さ）、縦が長さ。上下の歯の糊代を中へ折り、蓋を貼る。右の帯は筒を閉じる糊代。"""
    C, Lb, g = math.pi * p["bale_d"], p["bale_length"], p["glue"]
    n = max(6, round(C / 10))
    step = C / n
    top = [(0, TAB)]
    for i in range(n):
        x0, x1 = i * step, (i + 1) * step
        top += [(x0 + 1, 0), (x1 - 1, 0), (x1, TAB)]
    bottom = []
    for i in reversed(range(n)):
        x0, x1 = i * step, (i + 1) * step
        bottom += [(x1 - 1, TAB * 2 + Lb), (x0 + 1, TAB * 2 + Lb), (x0, TAB + Lb)]
    pts = top + [(C + g, TAB), (C + g, TAB + Lb)] + bottom
    part = Part(1, "tube", "俵の筒", pts, label_xy=(2, TAB + 2), label="1 俵")
    part.mountain = [((0, TAB), (C, TAB)), ((0, TAB + Lb), (C, TAB + Lb))]
    part.glue = [[(i * step, TAB), (i * step + 1, 0), ((i + 1) * step - 1, 0), ((i + 1) * step, TAB)] for i in range(n)]
    part.glue += [[((i + 1) * step, TAB + Lb), ((i + 1) * step - 1, 2 * TAB + Lb), (i * step + 1, 2 * TAB + Lb), (i * step, TAB + Lb)] for i in range(n)]
    part.glue.append([(C, TAB), (C + g, TAB), (C + g, TAB + Lb), (C, TAB + Lb)])
    e = 0.3
    y0, y1 = TAB + e, TAB + Lb - e
    art = [_panel(e, y0, C - e, y1, STRAW)]
    # 藁の筋は俵の長さの向き、縄の帯は周りの向き。絵の俵は帯が 4 本見える。
    bands = [y0 + (y1 - y0) * f for f in (0.12, 0.37, 0.63, 0.88)]
    for x in range(3, int(C) - 2, 4):
        for k in range(len(bands) - 1):
            a, b = bands[k] + 2.2, bands[k + 1] - 2.2
            off = 1.2 if (x // 4 + k) % 2 else 0
            yy = a + off
            while yy + 2 < b:
                art.append({"kind": "line", "pts": [(x, yy), (x + 0.4, yy + 2)], "stroke": STRAW_LINE, "sw": 0.3})
                yy += 3.4
    for yb in bands:
        art.append(_panel(e, yb - 1.4, C - e, yb + 1.4, ROPE))
        art += [{"kind": "line", "pts": [(e + 0.1, yb + d), (C - e - 0.1, yb + d)], "stroke": STRAW_LINE, "sw": 0.25} for d in (-1.4, 1.4)]
    part.art = art
    part.hide_folds = True
    return part


def _lid(n, p, key, name):
    """俵の蓋（桟俵）。絵の端の丸には、真ん中から放射の筋がある。"""
    R = p["bale_d"] / 2 + 1  # 筒の糊代に重ねるので、筒より少し大きく
    pts = _circle(R, R, R)
    part = Part(n, key, name, pts, label_xy=(R + 1.5, R + 1.5), label=str(n))
    art = [{"kind": "poly", "pts": _circle(R, R, R - 0.4), "fill": STRAW, "stroke": STRAW_LINE, "sw": 0.3}]
    for i in range(20):
        a = 2 * math.pi * i / 20
        art.append({"kind": "line", "pts": [(R + 2.5 * math.cos(a), R + 2.5 * math.sin(a)), (R + (R - 1.5) * math.cos(a), R + (R - 1.5) * math.sin(a))], "stroke": STRAW_LINE, "sw": 0.4})
    part.art = art
    if p["drive"] == "pull":
        part.holes = [(R, R, p["axle_hole"])]
    return part


def _ramp(p):
    """坂の溝。底の板の両側の縁を手前に起こす（谷折り）。刷った面が溝の内側になり、上から見える。"""
    Lr, inner, r = p["ramp_length"], ramp_inner(p), p["rail"]
    H = inner + 2 * r
    part = Part(4, "ramp", "坂の溝", [(0, 0), (Lr, 0), (Lr, H), (0, H)], label_xy=(3, r + 2), label="4 坂")
    part.valley = [((0, r), (Lr, r)), ((0, r + inner), (Lr, r + inner))]
    e = 0.3
    part.art = [_panel(e, e, Lr - e, r - e, WOOD_DARK), _panel(e, r + e, Lr - e, r + inner - e, WOOD), _panel(e, r + inner + e, Lr - e, H - e, WOOD_DARK)]
    part.art += [{"kind": "line", "pts": [(4, r + inner * f), (Lr - 4, r + inner * f + 0.5)], "stroke": WOOD_DARK, "sw": 0.3} for f in (0.3, 0.7)]
    part.hide_folds = True
    return part


def parts(p):
    if p["body"] == "cart":
        out = [_deck(p), _rider(2, p, False), _rider(3, p, True)]
        out += [_wheel(4 + i, p) for i in range(4)]
        return out
    out = [_tube(p), _lid(2, p, "lid", "蓋"), _lid(3, p, "lid_b", "蓋（2 枚目）")]
    if p["drive"] == "slope":
        out.append(_ramp(p))
    return out


def place(by_key, page, top, gap):
    """棚に並べるように左から詰め、入らなければ次の段へ。文字は部品の下に全幅で置く（物差しの 100mm を必ず入れるため）。"""
    x, y, row = page.x0, top, 0.0
    order = ["ramp", "deck", "tube", "rider", "rider_b", "lid", "lid_b"] + [f"wheel{i}" for i in range(1, 5)]
    for k in order:
        if k not in by_key:
            continue
        q = by_key[k]
        if x > page.x0 and x + q.width > page.x1:
            x, y, row = page.x0, y + row + gap, 0.0
        q.x, q.y = x, y
        x += q.width + gap
        row = max(row, q.height)
    return y + row + gap, page.x1 - page.x0, page.x0


def bom(p):
    paper = paper_name(p["paper_gsm"])
    why = "家庭のプリンタで刷って作るため"
    if p["body"] == "cart":
        rows = [
            {"number": 1, "key": "deck", "name": "台", "qty": 1, "material": paper, "substituted": True, "original_guess": "木の板（絵の色と木目による推測）", "reason": why},
            {"number": 2, "key": "rider", "name": "乗り手", "qty": 1, "material": paper, "substituted": True, "original_guess": "張子か土か木（不明）", "reason": why},
            {"number": 3, "key": "rider_b", "name": "乗り手（裏）", "qty": 1, "material": paper, "substituted": True, "original_guess": "張子か土か木（不明）", "reason": why},
            *[{"number": 4 + i, "key": f"wheel{i + 1}", "name": f"車 {i + 1}", "qty": 1, "material": paper, "substituted": True, "original_guess": "木の輪切り（推測）", "reason": why} for i in range(4)],
            {"number": 8, "key": "axle", "name": "軸", "qty": 2, "material": f"竹串（長さ約 {p['deck_width'] + 20}mm に切り、先を落とす）", "substituted": True, "original_guess": "不明", "reason": "家にあり、穴に通しやすいため"},
        ]
    else:
        rows = [
            {"number": 1, "key": "tube", "name": "俵の筒", "qty": 1, "material": paper, "substituted": True, "original_guess": "藁（俵の形による推測）", "reason": why},
            {"number": 2, "key": "lid", "name": "蓋", "qty": 1, "material": paper, "substituted": True, "original_guess": "藁の桟俵（推測）", "reason": why},
            {"number": 3, "key": "lid_b", "name": "蓋（2 枚目）", "qty": 1, "material": paper, "substituted": True, "original_guess": "藁の桟俵（推測）", "reason": why},
        ]
        if p["drive"] == "slope":
            rows.append({"number": 4, "key": "ramp", "name": "坂の溝", "qty": 1, "material": paper, "substituted": True, "original_guess": "絵に無い（試すための台）", "reason": why})
        else:
            rows.append({"number": 8, "key": "axle", "name": "軸", "qty": 1, "material": f"竹串（長さ約 {p['bale_length'] + 30}mm に切り、先を落とす）", "substituted": True, "original_guess": "絵に無い（不明）", "reason": "家にあり、穴に通しやすいため"})
    if p["drive"] == "pull":
        rows.append({"number": 9, "key": "string", "name": "引く糸", "qty": 1, "material": "糸 50cm", "substituted": True, "original_guess": "絵に無い（不明）", "reason": "引いて遊ぶ読みを試すため"})
    return rows


def materials(p):
    rows = bom(p)
    out = [f"{rows[0]['material']}を 1 枚", "のり、はさみ、定規、セロハンテープ"]
    out += [r["material"] for r in rows if r["key"] in ("axle", "string")]
    if p["drive"] == "slope":
        out.append("坂にする厚い本 2〜3 冊" if p["body"] == "cart" else "坂の端を載せる本 1〜2 冊")
    return out


def steps(p):
    # 坂で転がす俵は軸が無く、部品に穴が無い。穴あけの文を出すと、要らない竹串をそろえさせる（#294）。
    cut = "部品を外の線で切る。穴は竹串の先であける（色の切れ目の細い白で折る）" if any(q.holes for q in parts(p)) else "部品を外の線で切る（色の切れ目の細い白で折る）"
    out = ["刷った物差しに定規を当て、10cm か確かめる", cut]
    if p["body"] == "cart":
        out += ["1 台の縁を、絵を外にして下へ折る。前と後ろの壁の糊代を、横の縁の内側に貼る",
                "2 と 3 の乗り手を背中合わせに貼る。下の糊代は左右に開き、台の真ん中に貼る",
                "4〜7 の車を真ん中の橋で折り、2 枚を貼り合わせる",
                "竹串を台の穴に通し、両端に車を差してのりで止める。車が台に触れない隙間を 1mm 残す",
                "台を指で押して、車が 4 つとも回るか確かめる"]
        if p["drive"] == "pull":
            out.append(f"前の壁の小さな穴に糸を通し、内側で玉結びにする")
    else:
        out += ["1 俵の筒を、絵を外にして丸め、右の帯の糊代で貼る", "上と下の歯の糊代を中へ折り、2 と 3 の蓋を外から貼る"]
        if p["drive"] == "slope":
            out += [f"4 坂の両側の縁を手前に起こし、溝にする", "坂の片方の端を本に載せ、俵を上の端に置いて手を離す"]
        else:
            out += ["蓋の穴に竹串を通す。俵の両側に 10mm ずつ出す", "糸の両端を竹串の両側に結ぶ。糸の真ん中を持って引く"]
    return out


RESULTS = ("転がった", "転がらない", "わからない")


def measures(p):
    """数でなく、どう転がるかを言葉か絵で予想する（U-25 の案 1、虎と同じ形）。"""
    if p["drive"] == "pull":
        return {"predict": "引くと、どう動くと思いますか（言葉か絵で）", "rows": [[("引いた所（床・畳・机）", 40)]]}
    return {"predict": "坂に置いて手を離すと、どう動くと思いますか（言葉か絵で）", "rows": [[("坂の高さ（本の冊数）", 30)]]}


def diagram_caption(p):
    """図の札。俵の図には車も台も無いので、札を刷らない（#294）。"""
    return DIAGRAM_CAPTION if p["body"] == "cart" else ""


def diagram(x, y, w, h, p):
    """横から見た図。床の線、台か俵、軸の点。坂の形では坂を斜めに描く。"""
    shapes = []
    if p["body"] == "cart":
        L, R = p["deck_length"], p["wheel_d"] / 2
        tall = R + p["axle_drop"] + 6
        s = min(w / (L + 8), h / (tall * 2.2))
        base = y + h * 0.6
        ax_y = base - R * s
        deck_y = ax_y - p["axle_drop"] * s
        x0 = x + (w - L * s) / 2
        shapes.append({"kind": "rect", "x": x0, "y": deck_y - 1.2 * s, "w": L * s, "h": 1.2 * s})
        shapes.append({"kind": "rect", "x": x0, "y": deck_y, "w": L * s, "h": p["skirt"] * s, "dash": "1,0.6"})
        for cx in (x0 + p["axle_in"] * s, x0 + (L - p["axle_in"]) * s):
            shapes.append({"kind": "poly", "pts": _circle(cx, ax_y, R * s, 24), "fill": BENGARA, "sw": 0.25})
            shapes.append({"kind": "rect", "x": cx - 0.6, "y": ax_y - 0.6, "w": 1.2, "h": 1.2})
        shapes.append({"kind": "line", "x1": x, "y1": base, "x2": x + w, "y2": base})
        if p["drive"] == "pull":
            shapes.append({"kind": "line", "x1": x0 + L * s, "y1": deck_y + 2, "x2": x + w, "y2": deck_y - 4})
        return shapes
    d = p["bale_d"]
    if p["drive"] == "slope":
        s = min(w / 60, h / 60)
        x0, y0, x1, y1 = x + 1, y + h * 0.35, x + w - 1, y + h * 0.85
        shapes.append({"kind": "line", "x1": x0, "y1": y0, "x2": x1, "y2": y1})
        shapes.append({"kind": "line", "x1": x0, "y1": y1, "x2": x1, "y2": y1})
        ang = math.atan2(y1 - y0, x1 - x0)
        r = d / 2 * s
        cx, cy = x0 + 8 + r * math.sin(ang), y0 + 8 * math.tan(ang) - r * math.cos(ang)
        shapes.append({"kind": "poly", "pts": _circle(cx, cy, r, 24), "fill": STRAW, "sw": 0.25})
        return shapes
    s = min(w / (d * 2.5), h / (d * 2.5))
    cx, cy = x + w / 2, y + h * 0.55
    shapes.append({"kind": "poly", "pts": _circle(cx, cy, d / 2 * s, 24), "fill": STRAW, "sw": 0.25})
    shapes.append({"kind": "rect", "x": cx - 0.6, "y": cy - 0.6, "w": 1.2, "h": 1.2})
    shapes.append({"kind": "line", "x1": x, "y1": cy + d / 2 * s, "x2": x + w, "y2": cy + d / 2 * s})
    shapes.append({"kind": "line", "x1": cx, "y1": cy, "x2": x + w, "y2": cy - d * s, "dash": "1,0.6"})
    return shapes
