"""雛形 den_den: 紙の太鼓の胴（2 枚の皮と帯）を竹ひごの柄に通し、音を出す仕組みを仮説で描き分ける。

『江都二色』の音の玩具（でんでん太鼓・小槌・振り鼓・諫鼓・振り太鼓）を 1 本に乗せる（並列の線 drum、11-04）。
玩具ごとの違いは寸法（皮の径・帯の幅・胴の数・台の有無）と絵の選び（紋・帯の色）で出し、
仮説の違いは鳴らし方（play）だけで分ける。鳴らし方を寸法と混ぜると、どちらの違いで鳴ったのかが読めなくなるため。
どの値も実物では未確認。Claude が変えてよいのは ALLOWED の名前の値だけ。

笛（ぴいぴい・鳩笛・竹の笛）・琴・みみずくの止まり木は、この胴と皮の形に乗らないので作らない（理由は線の返事に書いた）。
"""
import math

from shapely import affinity
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

from ..model import Failure, Part

ID = "den_den"
# 刷った組の版（U-31）。組を刷り直したら上げる。
SHEET_SET = "den_den-v1"
# 仮説を分ける寸法の名前。twist＝柄を手のひらで回して糸の玉で打つ、shake＝胴の中の玉を振って鳴らす、tap＝皮を指で打つ。
HYP_KEY = "play"
DEFAULTS = {
    "play": "twist",
    # 形の選び。stick は柄で持つ形、stand は台に立てる形（諫鼓の絵が台に載るため）。
    "form": "stick",
    "motif": "kiku", "band_color": "shu", "band_stripe": 0,
    "drums": 1,
    # でんでん太鼓の絵の比（皮の径と柄の長さ）から出した見込み。帯の長さが A4 の印字域に入る径を上限にした。
    "head_d": 50, "band_w": 22, "tab": 6, "glue": 8,
    "thread_len": 34, "bead_d": 8, "beads_inside": 3,
    "handle_len": 180, "handle_d": 3,
    "streamers": 0,
    "base_l": 70, "base_w": 50, "base_h": 15,
}
RANGES = {
    "drums": (1, 2), "band_stripe": (0, 1),
    # 皮の径の下限は、玉が当たる面が指先より小さくならない所。上限は帯（πD＋糊代）が A4 の印字域（190mm）に入る所。
    "head_d": (30, 56), "band_w": (10, 70), "tab": (4, 8), "glue": (5, 12),
    "thread_len": (10, 80), "bead_d": (4, 14), "beads_inside": (1, 8),
    # 竹串のふつうの長さを上限にした。長い柄は割り箸を継ぐ物で、この型紙の手順の外。
    "handle_len": (80, 300), "handle_d": (2, 5),
    "streamers": (0, 4),
    "base_l": (40, 120), "base_w": (30, 90), "base_h": (8, 30),
}
CHOICES = {
    "play": ("twist", "shake", "tap"),
    "form": ("stick", "stand"),
    "motif": ("kiku", "tomoe", "tori", "none"),
    "band_color": ("shu", "ochre", "ai"),
}
INTS = ("drums", "band_stripe", "beads_inside", "streamers")
# 次の版で変えてよい寸法。鳴り方に効く寸法だけに絞る。紋や色は見た目の選びで、鳴ったかどうかの比べに混ぜないため。
ALLOWED = {"head_d", "band_w", "thread_len", "bead_d", "beads_inside", "handle_len"}
PARAM_NAMES = {"head_d": "皮の径（mm）", "band_w": "胴の幅（mm）", "thread_len": "糸の長さ（mm）", "bead_d": "玉の径（mm）",
               "beads_inside": "中の玉の数", "handle_len": "柄の長さ（mm）"}

# 江戸の色（朱・藍・黄土・墨・胡粉）。原図の画素は使わず、色の名で塗り直す（J-007）。
SHU, AI, OCHRE, SUMI, GOFUN = "#c4553a", "#34507a", "#c9a25a", "#2e2a24", "#f1e9d6"
BAND_COLORS = {"shu": SHU, "ochre": OCHRE, "ai": AI}
HOLE_MARGIN = 4  # 穴から紙の端までの見込み。これより狭いと裂けやすい（pivot_counterweight と同じ値）
GRIP = 60  # 柄の握る所。手のひらで挟んで回すのに要る長さの見込み
HIT_MARGIN = 2  # 玉が皮の縁ぎりぎりに当たると、帯の角を打って鳴りが鈍いと見込む余裕
STAND_POST = 20  # 台の上に出る柄の最小の長さ。これより短いと胴が台に触れて打てない
TITLES = {"twist": "柄を回して糸の玉で打つ", "shake": "胴の中の玉を振って鳴らす", "tap": "皮を指で打つ"}


def title(p):
    return TITLES[p["play"]] + ("・台に立てる" if p["form"] == "stand" else "")


def spec():
    return {"template_id": ID, "defaults": DEFAULTS, "ranges": RANGES, **CHOICES}


def check_range(p):
    out = []
    for k, v in p.items():
        if k in CHOICES:
            if v not in CHOICES[k]:
                out.append(Failure("F5.range", k, f"{v} は {CHOICES[k]} のどれでもない"))
        elif k not in RANGES:
            out.append(Failure("F5.range", k, "知らない寸法の名前"))
        elif not isinstance(v, (int, float)) or isinstance(v, bool) or not RANGES[k][0] <= v <= RANGES[k][1]:
            out.append(Failure("F5.range", k, f"{v} は範囲 {RANGES[k]} の外"))
        elif k in INTS and not float(v).is_integer():
            out.append(Failure("F5.range", k, "数は整数"))
    return out


def circumference(p):
    return math.pi * p["head_d"]


def hit_offset(p):
    """玉が皮を打つ点の、皮の中心からの距離（mm）。届かなければ None。

    柄を回すと玉は糸の付け根（帯の真ん中、柄から 90° の所）を中心に、胴の軸を含む面で振れる。
    玉の面が皮に触れる時、玉の中心は皮の面から玉の半径だけ外にある。付け根から皮の面までは帯の幅の半分。
    糸の長さを l、そこまでの軸の向きの距離を a とすると、付け根から皮の面に沿って √(l²−a²) 内に入った所を打つ。
    """
    a = p["band_w"] / 2 + p["bead_d"] / 2
    if p["thread_len"] <= a:
        return None
    return p["head_d"] / 2 - math.sqrt(p["thread_len"] ** 2 - a ** 2)


def check_physics(p):
    out = []
    R, r = p["head_d"] / 2, p["bead_d"] / 2
    stand = p["form"] == "stand"
    if p["play"] == "twist":
        if stand:
            out.append(Failure("F5.drum", "柄", "台に立てた胴は柄を回せないので、糸の玉で打てない"))
        h = hit_offset(p)
        if h is None:
            out.append(Failure("F5.drum", "糸", f"糸 {p['thread_len']}mm では玉が皮に届かない（帯の幅の半分＋玉の半径＝{p['band_w'] / 2 + r:g}mm より長く）"))
        elif h > R - r - HIT_MARGIN:
            out.append(Failure("F5.drum", "糸", f"玉が皮の縁（中心から {h:.1f}mm）を打ち、帯の角に当たる"))
        elif h < -(R - r - HIT_MARGIN):
            out.append(Failure("F5.drum", "糸", f"糸が長く、玉が皮を越えて向こうの縁の外へ振れる（中心から {-h:.1f}mm 先）"))
    if p["play"] == "shake":
        # 玉が胴の中で転がる余地。帯の幅と柄の両方で狭まるので、柄の太さも引く。
        room = min(p["band_w"], p["head_d"] / 2 - p["handle_d"]) - p["bead_d"]
        if room < 3:
            out.append(Failure("F5.drum", "中の玉", f"玉（{p['bead_d']}mm）が胴の中で動く余地が {room:.1f}mm しかなく、鳴らない"))
    need = (p["drums"] * p["head_d"] + GRIP) if not stand else (p["base_h"] + STAND_POST + R)
    if p["handle_len"] < need:
        out.append(Failure("F5.drum", "柄", f"柄 {p['handle_len']}mm が胴を通ると握る所（台では立てる所）が残らない（{need:g}mm 要る）"))
    if p["band_w"] < p["handle_d"] + 2 * HOLE_MARGIN:
        out.append(Failure("F5.drum", "帯", f"帯の幅 {p['band_w']}mm では柄の穴の前後に {HOLE_MARGIN}mm 取れず、裂けやすい"))
    if stand:
        if p["drums"] != 1:
            out.append(Failure("F5.drum", "台", "台に立てる形は胴 1 つだけ"))
        if p["streamers"]:
            out.append(Failure("F5.drum", "紙垂", "紙垂は柄の先に結ぶ物で、台の形には付けない"))
        # 胴の重さが台の外に出ると倒れる。胴の軸は台の長い向きに置くので、帯の幅と皮の径が台に収まるかを見る。
        if p["band_w"] > p["base_l"] or p["head_d"] > 2 * p["base_w"]:
            out.append(Failure("F5.drum", "台", "胴が台より大きく、立てると倒れる"))
    return out


def metrics(p):
    """台帳の式（F7）。次の版の寸法の向きを、雛形の側で数え直すため。"""
    h = hit_offset(p) if p["play"] == "twist" else None
    return {
        "hit_from_center_mm": abs(h) if h is not None else 0.0,
        "rattle_room_mm": float(min(p["band_w"], p["head_d"] / 2 - p["handle_d"]) - p["bead_d"]),
        "grip_mm": float(p["handle_len"] - p["drums"] * p["head_d"]),
    }


# --- 絵（原図を見て形を描き直した物。画素は使っていない） ---

def _circle(cx, cy, r, n=72):
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def _poly_coords(geom):
    g = max(getattr(geom, "geoms", [geom]), key=lambda x: x.area)
    return list(g.exterior.coords)[:-1]


def _kiku(cx, cy, R):
    """菊の紋。でんでん太鼓の皮の絵の、細い花びらが 16 枚放射に並ぶ形。"""
    art, n = [], 16
    for i in range(n):
        a = 2 * math.pi * i / n
        w = math.pi / n * 0.55
        pts = [(0.14, -w * 0.4), (0.4, -w), (0.6, -w * 0.5), (0.64, 0), (0.6, w * 0.5), (0.4, w), (0.14, w * 0.4)]
        art.append({"kind": "poly", "pts": [(cx + R * d * math.cos(a + t), cy + R * d * math.sin(a + t)) for d, t in pts], "fill": SUMI})
    art.append({"kind": "poly", "pts": _circle(cx, cy, R * 0.07, 24), "fill": SUMI})
    return art


def _tomoe(cx, cy, R):
    """三つ巴。諫鼓の絵の胴の端の紋。頭の丸から尾を細くして、次の巴の外を回す。"""
    art = []
    for k in range(3):
        a0 = 2 * math.pi * k / 3
        blobs = []
        for j in range(14):
            t = j / 13
            ang, rad = a0 + t * 2.0, R * (0.3 + 0.22 * t)
            blobs.append(Point(cx + rad * math.cos(ang), cy + rad * math.sin(ang)).buffer(R * (0.2 - 0.18 * t), 12))
        art.append({"kind": "poly", "pts": _poly_coords(unary_union(blobs).simplify(0.05)), "fill": SUMI})
    return art


def _tori(cx, cy, R):
    """振り太鼓の皮の、羽を上げて口を開けた鳥。胴・頭・嘴・羽・尾を形で組む（絵を見て手で取った比。画素は使っていない）。"""
    s = R * 0.72
    P = lambda pts: Polygon([(cx + x * s, cy + y * s) for x, y in pts])
    body = affinity.scale(Point(cx + 0.02 * s, cy + 0.12 * s).buffer(1, 32), 0.36 * s, 0.22 * s).buffer(0)
    body = affinity.rotate(body, -20, origin=(cx, cy))
    head = Point(cx - 0.42 * s, cy - 0.08 * s).buffer(0.15 * s, 24)
    beak = P([(-0.52, -0.16), (-0.82, -0.24), (-0.6, -0.08), (-0.8, 0.02), (-0.52, 0.0)])
    wing = P([(-0.12, -0.02), (-0.05, -0.55), (0.12, -0.78), (0.2, -0.62), (0.32, -0.7), (0.34, -0.42), (0.22, 0.02)])
    tail = P([(0.3, 0.05), (0.88, -0.32), (0.84, -0.12), (0.9, 0.02), (0.4, 0.3)])
    neck = P([(-0.42, -0.2), (-0.08, -0.06), (-0.08, 0.16), (-0.42, 0.05)])
    legs = P([(0.02, 0.3), (0.12, 0.3), (0.2, 0.62), (0.08, 0.5), (-0.02, 0.62)])
    bird = unary_union([body, neck, head, beak, wing, tail, legs]).simplify(0.05)
    # 嘴や足が胴から離れて別の形になっても落とさないよう、形ごとに塗る。
    art = [{"kind": "poly", "pts": list(g.exterior.coords)[:-1], "fill": SUMI} for g in getattr(bird, "geoms", [bird])]
    return art + [{"kind": "poly", "pts": _circle(cx - 0.44 * s, cy - 0.1 * s, 0.05 * s, 16), "fill": GOFUN}]


MOTIFS = {"kiku": _kiku, "tomoe": _tomoe, "tori": _tori, "none": lambda cx, cy, R: []}


def _panel(x0, y0, x1, y1, fill):
    return {"kind": "poly", "pts": [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], "fill": fill}


def _head(n, key, p, label):
    R = p["head_d"] / 2
    art = [{"kind": "poly", "pts": _circle(R, R, R - 0.6), "fill": GOFUN}]
    # 皮の縁の内側の二重の輪（でんでん太鼓と小槌の絵にある）。
    art += [{"kind": "line", "pts": _circle(R, R, R * f) + [_circle(R, R, R * f)[0]], "stroke": SUMI, "sw": 0.3} for f in (0.78, 0.84)]
    art += MOTIFS[p["motif"]](R, R, R)
    return Part(n, key, "皮", _circle(R, R, R), label_xy=(R * 0.1 + 2, R - 1.7), label=label, art=art)


def _band(n, key, p, label):
    """胴の帯。両の縁の歯を内へ山折りして皮を貼る。端の糊代に反対の端を重ねて輪にする。"""
    C, B, t, g = circumference(p), p["band_w"], p["tab"], p["glue"]
    x_end = g + C
    teeth = max(6, math.ceil(C / 9))
    w = C / teeth
    top = [(0, t)]
    bottom = []
    glue = [[(0, t), (g, t), (g, t + B), (0, t + B)]]
    for i in range(teeth):
        xa, xb = g + i * w, g + (i + 1) * w
        # 歯は台形にする。輪にすると歯の先が内へ寄って重なるので、先を細める。
        top += [(xa, t), (xa + 1.2, 0), (xb - 1.2, 0), (xb, t)]
        bottom += [(xb, t + B), (xb - 1.2, t + B + t), (xa + 1.2, t + B + t), (xa, t + B)]
        glue += [[(xa + 0.3, t), (xa + 1.4, 0.3), (xb - 1.4, 0.3), (xb - 0.3, t)], [(xb - 0.3, t + B), (xb - 1.4, t + B + t - 0.3), (xa + 1.4, t + B + t - 0.3), (xa + 0.3, t + B)]]
    outline = top + [(x_end, t), (x_end, t + B)] + bottom + [(0, t + B)]
    # 同じ点の重なり（歯と歯の継ぎ目）を落とす。多角形の検査が自己交差と読まないため。
    clean = [outline[0]]
    for q in outline[1:]:
        if abs(q[0] - clean[-1][0]) > 1e-9 or abs(q[1] - clean[-1][1]) > 1e-9:
            clean.append(q)
    color = BAND_COLORS[p["band_color"]]
    art = [_panel(g + 0.2, t + 0.2, x_end - 0.2, t + B - 0.2, color)]
    if p["band_stripe"]:
        # 小槌の絵の、胴の端に寄った墨の帯。
        art.append(_panel(g + 0.2, t + B * 0.62, x_end - 0.2, t + B * 0.8, SUMI))
    else:
        # でんでん太鼓の絵の、帯の上の白い菱形の鋲。柄の穴と糸の穴を避けた 45° ずつの所に置く。
        for k in (1, 3, 5, 7):
            cx, cy, s = g + C * k / 8 + C / 16, t + B / 2, min(B / 4, 3.0)
            art.append({"kind": "poly", "pts": [(cx, cy - s), (cx + s * 0.7, cy), (cx, cy + s), (cx - s * 0.7, cy)], "fill": GOFUN})
    holes = []
    hr = p["handle_d"] / 2 + 0.3
    # 柄の穴は継ぎ目から 45° ずらした向かい合う 2 か所。継ぎ目の糊代に穴が来ると貼った所が裂けるため。
    holes.append((g + C / 8, t + B / 2, hr))
    if p["form"] == "stick":
        holes.append((g + 5 * C / 8, t + B / 2, hr))
    if p["play"] == "twist":
        # 糸の穴は柄から 90°。玉が皮の真ん中寄りを打つ向き。
        holes += [(g + 3 * C / 8, t + B / 2, 0.8), (g + 7 * C / 8, t + B / 2, 0.8)]
    part = Part(n, key, "胴の帯", clean, label_xy=(g + 1.5, t + 1), label=label, art=art, glue=glue, holes=holes,
                mountain=[((g, t), (x_end, t)), ((g, t + B), (x_end, t + B))])
    # 折り線は帯の色の縁（歯との境）に置き、見える面には刷らない（本人の決定 d）。
    part.hide_folds = True
    return part


def _streamer(n, key):
    """紙垂。振り太鼓の絵の、柄の先に束ねた白い紙。上の糊代を柄に巻いて貼る。"""
    pts = [(0, 0), (8, 0), (8, 14), (14, 14), (14, 28), (20, 28), (20, 42), (12, 42), (12, 28), (6, 28), (6, 14), (0, 14)]
    return Part(n, key, "紙垂", pts, label_xy=(1, 5), label=str(n), glue=[[(0, 0), (8, 0), (8, 4), (0, 4)]])


def _base(n, p):
    """台の箱。上の面の真ん中の穴に柄を立てる。4 つの壁を山折りし、糊代を壁の内に貼る。"""
    L, W, h = p["base_l"], p["base_w"], p["base_h"]
    gt = min(p["glue"], h - 2)
    pts = [(h, 0), (h + L, 0), (h + L + gt, 1), (h + L + gt, h - 1), (h + L, h), (2 * h + L, h), (2 * h + L, h + W), (h + L, h + W),
           (h + L + gt, h + W + 1), (h + L + gt, 2 * h + W - 1), (h + L, 2 * h + W), (h, 2 * h + W), (h - gt, 2 * h + W - 1), (h - gt, h + W + 1),
           (h, h + W), (0, h + W), (0, h), (h, h), (h - gt, h - 1), (h - gt, 1)]
    glue = [[(h + L, 0.3), (h + L + gt - 0.3, 1.2), (h + L + gt - 0.3, h - 1.2), (h + L, h - 0.3)],
            [(h + L, h + W + 0.3), (h + L + gt - 0.3, h + W + 1.2), (h + L + gt - 0.3, 2 * h + W - 1.2), (h + L, 2 * h + W - 0.3)],
            [(h, h + W + 0.3), (h - gt + 0.3, h + W + 1.2), (h - gt + 0.3, 2 * h + W - 1.2), (h, 2 * h + W - 0.3)],
            [(h, 0.3), (h - gt + 0.3, 1.2), (h - gt + 0.3, h - 1.2), (h, h - 0.3)]]
    folds = [((h, h), (h + L, h)), ((h, h + W), (h + L, h + W)), ((h, h), (h, h + W)), ((h + L, h), (h + L, h + W)),
             ((h, 0), (h, h)), ((h + L, 0), (h + L, h)), ((h, h + W), (h, 2 * h + W)), ((h + L, h + W), (h + L, 2 * h + W))]
    art = [_panel(h + 0.2, h + 0.2, h + L - 0.2, h + W - 0.2, OCHRE), _panel(h + 0.2, 0.2, h + L - 0.2, h - 0.2, OCHRE),
           _panel(h + 0.2, h + W + 0.2, h + L - 0.2, 2 * h + W - 0.2, OCHRE), _panel(0.2, h + 0.2, h - 0.2, h + W - 0.2, OCHRE),
           _panel(h + L + 0.2, h + 0.2, 2 * h + L - 0.2, h + W - 0.2, OCHRE)]
    part = Part(n, "base", "台", pts, label_xy=(h + 2, h + 2), label=f"{n} 台", art=art, glue=glue, mountain=folds,
                holes=[(h + L / 2, h + W / 2, p["handle_d"] / 2 + 0.3)])
    part.hide_folds = True
    return part


def parts(p):
    out, n = [], 1
    for d in range(1, p["drums"] + 1):
        tag = "" if p["drums"] == 1 else f"の{d}"
        out.append(_band(n, f"band{d}", p, f"{n} 帯{tag}"))
        out.append(_head(n + 1, f"head{d}a", p, f"{n + 1}"))
        out.append(_head(n + 2, f"head{d}b", p, f"{n + 2}"))
        n += 3
    if p["form"] == "stand":
        out.append(_base(n, p))
        n += 1
    for k in range(p["streamers"]):
        out.append(_streamer(n, f"shide{k + 1}"))
        n += 1
    return out


def place(by_key, page, top, gap):
    """棚に詰める順に置く。帯は長いので 1 段に 1 本、皮と紙垂は横に並べる。文字は全部の部品の下に全幅で置く（物差しの 100mm を取るため）。"""
    x, y, row_h = page.x0, top, 0.0
    for q in by_key.values():
        if x > page.x0 and x + q.width > page.x1:
            x, y, row_h = page.x0, y + row_h + gap, 0.0
        q.x, q.y = x, y
        x += q.width + gap
        row_h = max(row_h, q.height)
    return y + row_h + gap, page.x1 - page.x0, page.x0


def bom(p):
    paper = "紙（厚さ 0.15mm 前後の見込み）"
    why = "家庭のプリンタで刷って作るため"
    rows = []
    for q in parts(p):
        orig = {"band": "木か張子の胴（不明）", "head": "皮か紙（不明）", "base": "木の台（不明）", "shide": "紙"}[q.key.rstrip("0123456789ab")]
        rows.append({"number": q.number, "key": q.key, "name": q.name, "qty": 1, "material": paper, "substituted": True, "original_guess": orig, "reason": why})
    n = len(rows) + 1
    rows.append({"number": n, "key": "handle", "name": "柄", "qty": 1, "material": f"竹串か竹ひご（太さ約 {p['handle_d']:g}mm・長さ {p['handle_len']:g}mm）",
                 "substituted": True, "original_guess": "竹か木の棒（不明）", "reason": "家にあり、穴に通しやすいため"})
    if p["play"] == "twist":
        rows.append({"number": n + 1, "key": "bead", "name": "糸の玉", "qty": 2 * p["drums"], "material": f"ビーズ（径 約 {p['bead_d']:g}mm）を {2 * p['drums']} 個と糸（{p['thread_len'] + 15:g}mm を {2 * p['drums']} 本）",
                     "substituted": True, "original_guess": "不明", "reason": "重さと長さを変えて試しやすいため"})
    if p["play"] == "shake":
        rows.append({"number": n + 1, "key": "rattle", "name": "中の玉", "qty": p["beads_inside"], "material": f"ビーズ（径 約 {p['bead_d']:g}mm）を {p['beads_inside']} 個",
                     "substituted": True, "original_guess": "不明（小石か豆の見込み）", "reason": "数を変えて試しやすいため"})
    return rows


def materials(p):
    out = [f"紙（厚さ 0.15mm 前後）を 1 枚", "のり、はさみ、定規、テープ"]
    out += [r["material"] for r in bom(p) if r["key"] in ("handle", "bead", "rattle")]
    return out


def steps(p):
    D, two = p["head_d"], p["drums"] == 2
    out = ["刷った物差しに定規を当て、10cm か確かめる", "部品を実線で切る。帯の小さな穴は竹串の先であける"]
    out.append("1 帯の歯を色の縁で山折りし（歯が輪の内へ倒れる向き）、帯を丸めて端を糊代に重ねて貼り、輪にする")
    if p["play"] == "twist":
        out.append(f"糸の片方の端を帯の小さな穴に内から通して結び、もう片方にビーズを結ぶ。結び目から玉の真ん中まで {p['thread_len']:g}mm")
    out.append("片側の歯の糊代に糊を付け、皮を 1 枚貼る")
    if p["play"] == "shake":
        out.append(f"輪の中にビーズを {p['beads_inside']} 個入れる")
    out.append("もう 1 枚の皮を貼って閉じる")
    if two:
        out.append("部品 4〜6 で、2 つ目の胴も同じに作る")
    if p["form"] == "stand":
        out += ["台を色の縁で山折りして箱にし、糊代を壁の内に貼る", f"柄を台の穴に差してテープで止め、上の端を胴の帯の穴に差して貼る（胴の真ん中が台の上 {p['base_h'] + 20 + D / 2:g}mm より高く）"]
    else:
        out.append("柄を帯の大きな穴に通し、反対の穴から出す。胴が柄の上で回らないよう、穴の所をテープで止める" + ("。2 つ目の胴は 1 つ目と直角に向けて通す" if two else ""))
    if p["streamers"]:
        out.append("紙垂の上の糊代を柄の先に巻いて貼る")
    return out


RESULTS = ("鳴った", "鳴らない", "わからない")


def measures(p):
    """鳴ったかどうかの二択だけでなく、どうすると鳴るかを先に言葉で予想する（U-25 の案 1 に倣う）。"""
    return {"predict": "どう動かすと、どこが鳴ると思いますか（言葉か絵で）", "rows": [[("動かし方（回す・振る・打つ）", 50), ("鳴った所", 40)]]}


def diagram(x, y, w, h, p):
    """横から見た図。胴は軸を横に寝かせた形で、柄は縦。破線は糸と中の玉。"""
    D, B = p["head_d"], p["band_w"]
    stand = p["form"] == "stand"
    reach = (p["thread_len"] + p["bead_d"]) if p["play"] == "twist" else 0
    total_w = max(B + 2 * reach, p["base_l"] if stand else 0, B) + 4
    total_h = (D + (p["base_h"] + STAND_POST) if stand else p["drums"] * D + GRIP * 0.5) + 4
    s = min(w / total_w, h / total_h)
    cx = x + w / 2
    top = y + 2
    shapes = []
    for d in range(p["drums"]):
        dy = top + d * D * s
        shapes.append({"kind": "rect", "x": cx - B * s / 2, "y": dy, "w": B * s, "h": D * s})
    drum_bottom = top + p["drums"] * D * s
    if stand:
        by = drum_bottom + STAND_POST * s
        shapes.append({"kind": "line", "x1": cx, "y1": drum_bottom, "x2": cx, "y2": by})
        shapes.append({"kind": "rect", "x": cx - p["base_l"] * s / 2, "y": by, "w": p["base_l"] * s, "h": p["base_h"] * s})
    else:
        shapes.append({"kind": "line", "x1": cx, "y1": top - 1, "x2": cx, "y2": min(y + h - 1, drum_bottom + GRIP * 0.5 * s)})
    if p["play"] == "twist":
        # 回した時に玉が振れて皮を打つ所まで、糸を破線で引く。
        # 糸の付け根は柄から 90° の向き（見る人の手前と奥）なので、横から見ると胴の真ん中の高さに重なる。
        by_ = top + D * s / 2
        for side in (-1, 1):
            bx = cx + side * (B / 2 + p["bead_d"] / 2) * s
            shapes.append({"kind": "line", "x1": cx, "y1": by_, "x2": bx, "y2": by_, "dash": "1,0.6"})
            shapes.append({"kind": "rect", "x": bx - p["bead_d"] * s / 2, "y": by_ - p["bead_d"] * s / 2, "w": p["bead_d"] * s, "h": p["bead_d"] * s})
    elif p["play"] == "shake":
        for k in range(p["beads_inside"]):
            bx = cx - B * s / 2 + (k + 1) * B * s / (p["beads_inside"] + 1)
            shapes.append({"kind": "rect", "x": bx - p["bead_d"] * s / 4, "y": top + D * s * 0.8, "w": p["bead_d"] * s / 2, "h": p["bead_d"] * s / 2, "dash": "1,0.6"})
    return shapes
