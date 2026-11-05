"""雛形 balance_toy: 重りを支点より下に置いて、傾けても戻る形。釣り合い人形と起き上がり小法師の仮説を試す（線 cart、11-04）。

1 本に 2 つの形を乗せる（線の契約）。どちらも「重心が支える所より下にあれば戻る」で読めるので同じ床で落とせる。
HYP_KEY の hold（支え方と重りの付け方）が、形と仮説の両方を決める。
- "arm": 着物の形の板を竹串の先の一点に載せ、袖の下の角から斜め下へ伸ばした腕の先の錘で釣り合う（弥次郎兵衛の読み）
- "spin": 着物の板を竹串の先に貼って止め、錘は糸で吊る。柄を手で回すと錘が外へ振れる（回して遊ぶ読み）
- "round": 円錐の胴の下に、粘土で丸い底を作る。倒しても起き上がる（起き上がりの読み）
- "flat": 同じ胴に平らな底を貼る。立つだけの頭巾人形（飾りの読み）
寸法は図の比からの見込みで、どの値も実物では未確認。Claude が変えてよいのは ALLOWED の名前の値だけ。
"""
import math

from shapely.geometry import LineString, Polygon, box

from ..model import Failure, Part
from ..pivot_model import center, paper_mass, rest_tilt_deg

ID = "balance_toy"
SHEET_SET = "balance_toy-v1"
# 手順の紙の図の説明（instructions.compose_sheet）。御来迎の筒の言葉を刷らないため。
DIAGRAM_CAPTION = "支点と重り（破線は重さの線）"
HYP_KEY = "hold"
HOLDS = ("arm", "spin", "round", "flat")
DEFAULTS = {
    "hold": "arm",
    # 釣り合い人形。図の着物の幅を 64mm と置き、ほかは図の比で出した（腕 103mm・60°、錘の玉の半径 6.5mm ≒ 粘土 2g）。
    "kimono_w": 64, "v_height": 19, "arm_len": 100, "arm_deg": 60, "thread_len": 36, "weight_g": 2.0,
    "doll_h": 32, "stand": 34, "spin_deg": 30,
    # 起き上がり。底の粘土は半径 base_r の半球、胴は高さ body_h の円錐。
    "base_r": 14, "body_h": 64,
    "glue": 6, "paper_gsm": 150,
}
RANGES = {
    "kimono_w": (40, 80), "v_height": (10, 30), "arm_len": (40, 140), "arm_deg": (-30, 80), "thread_len": (10, 80), "weight_g": (0.3, 8),
    "doll_h": (20, 45), "stand": (24, 44), "spin_deg": (10, 60),
    "base_r": (8, 20), "body_h": (30, 90),
    "glue": (4, 10), "paper_gsm": (40, 400),
}
ALLOWED = ("kimono_w", "v_height", "arm_len", "arm_deg", "thread_len", "weight_g", "doll_h", "stand", "spin_deg", "base_r", "body_h", "paper_gsm")
POCKET = 5  # V の先から、竹串の先が入る袋の奥まで。袋の奥が支点
BAMBOO_G_PER_MM = 0.002  # 竹ひご（太さ 2mm）1mm の重さの見込み。手元の物を量ったら置き換える
CLAY_G_PER_MM3 = 1.7e-3  # 油粘土の密度の見込み
MIN_DROP = 3  # 重心が支点より下にある量。これより小さいと、紙のゆがみと擦れで戻りきらない（見込み）
MAX_TILT = 8  # 静かな時の傾き。着物の板は笠が片寄っているので、少しは傾く
MAX_REV = 3.0  # 掌で柄をこすって回せる回数（1 秒あたり）の見込み
STAND_RIM = 5  # 台の縁の高さ
MARGIN = 1.0  # 起き上がり: 重心が丸い底の中心より下にある量
MIN_TIP = 20  # 平らな底: 倒れ始める傾き。これより小さいと、置いただけで倒れやすい（見込み）
G = 9800.0

SHU, AI, OCHRE, SUMI, GOFUN = "#c8553d", "#2e4a6b", "#c9a35a", "#2a2622", "#f3eee2"
KIMONO, KIMONO_DARK, HAT, SKIN, BODY = "#d6bb7f", "#b8975a", "#c9a35a", "#ecc4ac", "#d8bf78"
WOOD, WOOD_DARK, BENGARA = "#d8bd84", "#b08a45", "#7a4a2a"

TITLES = {"arm": "腕の先の錘で、竹串の先に釣り合う", "spin": "糸の錘を、柄を回して振る", "round": "粘土の丸い底で起き上がる", "flat": "平らな底で立つ"}
PARAM_NAMES = {"hold": "支え方", "kimono_w": "着物の板の幅", "v_height": "着物の下の V の高さ", "arm_len": "腕の長さ", "arm_deg": "腕の下がる角度",
               "thread_len": "糸の長さ", "weight_g": "錘 1 つの粘土", "doll_h": "人形の高さ", "stand": "台の幅", "spin_deg": "回して振れる角度",
               "base_r": "底の半径", "body_h": "胴の高さ"}


def _yaji(p):
    return p["hold"] in ("arm", "spin")


def title(p):
    return TITLES[p["hold"]]


def spec():
    return {"template_id": ID, "defaults": DEFAULTS, "ranges": RANGES, "hold": HOLDS}


def check_range(p):
    out = []
    for k, v in p.items():
        if k == "hold":
            if v not in HOLDS:
                out.append(Failure("F5.range", k, f"{v} は {HOLDS} のどれでもない"))
        elif k not in RANGES:
            out.append(Failure("F5.range", k, "知らない寸法の名前"))
        elif not isinstance(v, (int, float)) or isinstance(v, bool) or not RANGES[k][0] <= v <= RANGES[k][1]:
            out.append(Failure("F5.range", k, f"{v} は範囲 {RANGES[k]} の外"))
    return out


# --- 釣り合い人形の形（NDL コマ 7 左頁を、横 1000px に切り出した座標で手で取った点。絵の画素は使っていない） ---
# 笠は絵より 14px 下げて袖と重ねる。絵のままだと袖との継ぎ目が細く、切ると取れやすいため。
_HAT = [(358, 307), (528, 199), (537, 224), (528, 259), (505, 289), (470, 312), (420, 319)]
_SLEEVE = [(270, 300), (665, 300), (665, 415), (270, 415)]
_BODY = [(408, 412), (545, 408), (610, 528), (365, 528)]
_COLLAR = [(425, 300), (500, 300), (470, 372)]
HEM_Y, HEM_L, HEM_R = 528, 365, 610
V_TOP_W = 50  # V の上の幅（px）。絵の V は細い
PX_W = 665 - 270  # 着物の幅の px。kimono_w をこれに当てる


def _sc(p):
    return p["kimono_w"] / PX_W


def _board_geom(p):
    """片面の着物の形（笠・袖・身頃・V）を mm で返す。原点は V の先（下の頂点）で、y は下が正。"""
    s = _sc(p)
    cx = (HEM_L + HEM_R) / 2  # V は裾の真ん中に置く。腕を左右同じ所に付けて、傾きを笠の片寄りだけにするため
    vh = p["v_height"]
    conv = lambda ps: [((x - cx) * s, (y - HEM_Y) * s - vh) for x, y in ps]
    vw = V_TOP_W * s / 2
    v = [(-vw, -vh - 0.01), (vw, -vh - 0.01), (0, 0)]
    shape = Polygon(conv(_HAT)).union(Polygon(conv(_SLEEVE))).union(Polygon(conv(_BODY))).union(Polygon(v)).buffer(0)
    return shape, conv, v


def mass_points(p):
    """揺れる部分の質量の点 (質量 g, 横 mm, 支点から下 mm)。pivot_model と同じ向き（下が正）。

    糸で吊った錘は、静かな釣り合いでは吊った所に重さが掛かる（振り子が吊り元に重さを渡すため）。
    なので spin の形の錘は、糸の先でなく裾の角に置く。柄に貼って止めるので、spin では揺れの式に使わない。"""
    shape, _, _ = _board_geom(p)
    c = shape.centroid
    pts = [(paper_mass(2 * shape.area, p["paper_gsm"]), c.x, c.y + POCKET)]
    hx, hz = hem_corner(p)
    if p["hold"] == "arm":
        a = math.radians(p["arm_deg"])
        L = p["arm_len"]
        for sgn in (-1, 1):
            pts.append((BAMBOO_G_PER_MM * L, sgn * (hx + L / 2 * math.cos(a)), hz + L / 2 * math.sin(a)))
            pts.append((p["weight_g"], sgn * (hx + L * math.cos(a)), hz + L * math.sin(a)))
    else:
        pts += [(p["weight_g"], -hx, hz), (p["weight_g"], hx, hz)]
    return pts


def hem_corner(p):
    """裾の右の角（腕か糸を付ける所）。支点から右へ、下へ（mm）。"""
    s = _sc(p)
    return (HEM_R - HEM_L) / 2 * s, POCKET - p["v_height"]


def weight_pos(p):
    """右の錘の中心。arm は腕の先、spin は静かに吊った時の糸の先。"""
    hx, hz = hem_corner(p)
    if p["hold"] == "arm":
        a = math.radians(p["arm_deg"])
        return hx + p["arm_len"] * math.cos(a), hz + p["arm_len"] * math.sin(a)
    return hx, hz + p["thread_len"]


def weight_r(p):
    return (3 * p["weight_g"] / CLAY_G_PER_MM3 / (4 * math.pi)) ** (1 / 3)


def doll_top(p):
    """人形の頭の上。V の先の 2mm 下に置く（V が頭に触れて擦らないため）。"""
    return POCKET + 2


def spin_rev(p):
    """糸が鉛直から spin_deg 開くのに要る、1 秒あたりの回数。tanφ = ω²·r / g（円すい振り子）。"""
    phi = math.radians(p["spin_deg"])
    hx, _ = hem_corner(p)
    r = hx + p["thread_len"] * math.sin(phi)
    return math.sqrt(G * math.tan(phi) / r) / (2 * math.pi)


# --- 起き上がりの形 ---

def cone(p):
    """円錐の胴の展開。斜辺 s と、扇の開き Θ（rad）。"""
    s = math.hypot(p["body_h"], p["base_r"])
    return s, 2 * math.pi * p["base_r"] / s


def kobo_cg(p):
    """床からの重心の高さ（立てた時）。紙の胴の側面の重心は底から高さの 1/3。粘土の半球の重心は平らな面から 3R/8。"""
    R, H = p["base_r"], p["body_h"]
    s, _ = cone(p)
    paper = [(paper_mass(math.pi * R * s, p["paper_gsm"]), H / 3), (paper_mass(math.pi * (R + 0.5) ** 2, p["paper_gsm"]), 0)]
    if p["hold"] == "round":
        clay = CLAY_G_PER_MM3 * 2 / 3 * math.pi * R ** 3
        pts = [(m, z + R) for m, z in paper] + [(clay, R - 3 * R / 8)]
    else:
        pts = paper
    total = sum(m for m, _ in pts)
    return sum(m * z for m, z in pts) / total


def check_physics(p):
    out = []
    if _yaji(p):
        wx, wz = weight_pos(p)
        r = weight_r(p)
        if p["hold"] == "arm":
            pts = mass_points(p)
            _, z, _ = center(pts)
            if z < MIN_DROP:
                state = f"{-z:.1f}mm 上にあり" if z < 0 else f"{z:.1f}mm 下にしかなく"
                out.append(Failure("F5.balance", "錘", f"重心が支点より {state}、傾けると戻らない（下へ {MIN_DROP}mm から）。腕を下げるか長くする"))
            elif abs(rest_tilt_deg(pts)) > MAX_TILT:
                out.append(Failure("F5.balance", "着物の板", f"静かな時に {rest_tilt_deg(pts):.0f}° 傾く（{MAX_TILT}° まで）"))
        else:
            if spin_rev(p) > MAX_REV:
                out.append(Failure("F5.balance", "糸", f"錘を {p['spin_deg']}° 振るのに 1 秒に {spin_rev(p):.1f} 回まわす要りがあり、掌では回しきれない（{MAX_REV} 回まで）"))
        # 静かに下がった錘が、人形・台・柄に当たらないか。腕も糸も同じ式で見る。高さの帯が重なる物とだけ横の隙間を比べる。
        top, stand_top = doll_top(p), doll_top(p) + p["doll_h"]
        bands = ((top, stand_top, doll_w(p) / 2 + 1, "人形"), (stand_top, stand_top + STAND_RIM, p["stand"] / 2 + 1, "台"), (stand_top + STAND_RIM, 1e9, 2.5, "柄"))
        for z0, z1, need, name in bands:
            if wz + r > z0 and wz - r < z1 and wx - r < need:
                out.append(Failure("F5.balance", "錘", f"静かに下がった錘が{name}に当たる（錘の内の端が柄から {wx - r:.1f}mm、要るのは {need:.1f}mm から）"))
        if p["v_height"] < POCKET + 4:
            out.append(Failure("F5.balance", "V", f"V が低く、竹串の先を入れる袋（{POCKET}mm）の上に糊しろが残らない"))
    else:
        R = p["base_r"]
        h = kobo_cg(p)
        if p["hold"] == "round":
            if h > R - MARGIN:
                out.append(Failure("F5.balance", "底", f"重心が床から {h:.1f}mm で、丸い底の中心（{R}mm）より {MARGIN}mm 以上下にない。倒すと起き上がらない"))
        else:
            tip = math.degrees(math.atan2(R, h))
            if tip < MIN_TIP:
                out.append(Failure("F5.balance", "底", f"{tip:.0f}° 傾くと倒れる（{MIN_TIP}° から）"))
        s, th = cone(p)
        if th > math.pi * 1.15:
            out.append(Failure("F5.balance", "胴", "胴が低く太すぎ、扇が半円を大きく超えて丸めにくい"))
    return out


def metrics(p):
    """台帳の式（F7）。どの形でも同じ名前で返す（版の間で比べるため）。当てはまらない値は 0。"""
    if p["hold"] == "arm":
        pts = mass_points(p)
        return {"cg_margin_mm": center(pts)[1], "rest_tilt_deg": abs(rest_tilt_deg(pts)), "spin_rev_s": 0.0}
    if p["hold"] == "spin":
        return {"cg_margin_mm": 0.0, "rest_tilt_deg": 0.0, "spin_rev_s": spin_rev(p)}
    if p["hold"] == "round":
        return {"cg_margin_mm": p["base_r"] - kobo_cg(p), "rest_tilt_deg": 0.0, "spin_rev_s": 0.0}
    return {"cg_margin_mm": 0.0, "rest_tilt_deg": math.degrees(math.atan2(p["base_r"], kobo_cg(p))), "spin_rev_s": 0.0}


# --- 部品 ---

def _circle(cx, cy, r, n=48):
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def _panel(x0, y0, x1, y1, fill):
    return {"kind": "poly", "pts": [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], "fill": fill}


def _clip(pts, shape, fill, stroke=None, sw=0.2):
    """絵を部品の内側で切る。外に出た絵は F5.image_box で落ちるので、描く側で収める。"""
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


def _board(p):
    """着物の板。表と裏を袖の端でつなぎ、そこで山折りして背中合わせに貼る（2 枚にして反りを抑える）。
    V の先の袋（POCKET）には糊を付けず、竹串の先を差し込む。"""
    shape, conv, v = _board_geom(p)
    s = _sc(p)
    fold_x = (665 - (HEM_L + HEM_R) / 2) * s  # 袖の右端。原点からの x
    minx, miny, _, _ = shape.bounds
    dx, dy = -minx, -miny
    move = lambda ps: [(x + dx, y + dy) for x, y in ps]
    mirror = lambda ps: [(2 * (fold_x + dx) - x, y) for x, y in ps]
    front = Polygon(move(list(shape.exterior.coords)[:-1]))
    back = Polygon(mirror(list(front.exterior.coords)[:-1]))
    whole = front.union(back).buffer(0)
    part = Part(1, "board", "着物の板", list(whole.exterior.coords)[:-1], label_xy=(fold_x + dx - 8, (300 - HEM_Y) * s - p["v_height"] + dy + 3), label="1")
    sl_top, sl_bot = (300 - HEM_Y) * s - p["v_height"] + dy, (415 - HEM_Y) * s - p["v_height"] + dy
    fx = fold_x + dx
    part.mountain = [((fx, sl_top), (fx, sl_bot))]
    art = []
    for half, f in ((front, lambda ps: ps), (back, mirror)):
        inner = half.buffer(-0.3).intersection(box(-1e3, -1e3, fx - 0.3, 1e3) if f is not mirror else box(fx + 0.3, -1e3, 1e3, 1e3))
        art += _clip(list(half.exterior.coords)[:-1], inner, KIMONO, SUMI, 0.3)
        art += _clip(f(move(conv(_HAT))), inner, HAT, SUMI, 0.3)
        art += _clip(f(move(conv(_COLLAR))), inner, GOFUN, SUMI, 0.25)
        art += _clip(f(move(v)), inner, GOFUN)
        # V は絵では 2 本の細い線。白の上に墨の線で描く。
        art += _clip_line(f(move([v[0], v[2]])), inner, SUMI, 0.35) + _clip_line(f(move([v[1], v[2]])), inner, SUMI, 0.35)
        art += _clip_line(f(move(conv([(408, 412), (545, 410)]))), inner, SUMI, 0.3)
    part.art = art
    part.hide_folds = True
    return part


_DOLL = [(440, 410), (420, 440), (415, 480), (440, 540), (470, 555), (520, 555), (555, 520), (550, 470), (525, 430), (495, 410)]
_DOLL_HEAD = (468, 385, 30)
_DOLL_LINES = [[(430, 470), (480, 455), (525, 472)], [(455, 520), (490, 500), (530, 515)], [(470, 555), (470, 525)]]


def doll_w(p):
    return p["doll_h"] * (555 - 415) / (555 - 355)


def _doll(p):
    """座った人形。1 枚で、背を竹串に貼る。下の糊代は台に貼る。"""
    s = p["doll_h"] / (555 - 355)
    conv = lambda ps: [((x - 415) * s, (y - 355) * s) for x, y in ps]
    hx, hy, hr = _DOLL_HEAD
    sil = Polygon(conv(_DOLL)).union(Polygon(conv(_circle(hx, hy, hr, 24)))).buffer(0)
    w, h = doll_w(p), p["doll_h"]
    tab = 5
    whole = sil.union(box(w * 0.25, h - 0.01, w * 0.75, h + tab)).buffer(0)
    part = Part(2, "doll", "人形", list(whole.exterior.coords)[:-1], label_xy=(w * 0.4, h * 0.55), label="2")
    part.valley = [((w * 0.25, h), (w * 0.75, h))]
    part.glue = [[(w * 0.25, h), (w * 0.75, h), (w * 0.75, h + tab), (w * 0.25, h + tab)]]
    inner = sil.buffer(-0.3)
    part.art = _clip(list(sil.exterior.coords)[:-1], inner, KIMONO, SUMI, 0.3)
    for line in _DOLL_LINES:
        part.art += _clip_line(conv(line), inner, SUMI, 0.3)
    part.hide_folds = True
    return part


def _stand(p):
    """台。真ん中の穴に竹串を通す。縁を下に折る浅い箱（台車の台と同じ作り）。"""
    S, h, g = p["stand"], STAND_RIM, 3
    pts = [(h, 0), (h + S, 0), (h + S, h), (h + S + 1, h - g), (2 * h + S - 1, h - g), (2 * h + S, h), (2 * h + S, h + S),
           (2 * h + S - 1, h + S + g), (h + S + 1, h + S + g), (h + S, h + S), (h + S, 2 * h + S), (h, 2 * h + S), (h, h + S),
           (h - 1, h + S + g), (1, h + S + g), (0, h + S), (0, h), (1, h - g), (h - 1, h - g), (h, h)]
    part = Part(3, "stand", "台", pts, label_xy=(h + 2, h + 2), label="3")
    part.mountain = [((h, h), (h + S, h)), ((h, h + S), (h + S, h + S)), ((h, h), (h, h + S)), ((h + S, h), (h + S, h + S)),
                     ((0, h), (h, h)), ((0, h + S), (h, h + S)), ((h + S, h), (2 * h + S, h)), ((h + S, h + S), (2 * h + S, h + S))]
    part.glue = [[(h + S, h), (h + S + 1, h - g), (2 * h + S - 1, h - g), (2 * h + S, h)], [(h + S, h + S), (2 * h + S, h + S), (2 * h + S - 1, h + S + g), (h + S + 1, h + S + g)],
                 [(0, h), (1, h - g), (h - 1, h - g), (h, h)], [(0, h + S), (h, h + S), (h - 1, h + S + g), (1, h + S + g)]]
    e = 0.3
    part.art = [_panel(h + e, h + e, h + S - e, h + S - e, WOOD), _panel(h + e, e, h + S - e, h - e, WOOD_DARK), _panel(h + e, h + S + e, h + S - e, 2 * h + S - e, WOOD_DARK),
                _panel(e, h + e, h - e, h + S - e, WOOD_DARK), _panel(h + S + e, h + e, 2 * h + S - e, h + S - e, WOOD_DARK)]
    part.holes = [(h + S / 2, h + S / 2, 1.6)]
    part.hide_folds = True
    return part


def _gauge(p):
    """腕の角度の型。直角三角形の斜めの辺を袖の下の角に当て、竹ひごを沿わせる。分度器を使わずに図の角度を出すため。"""
    a = math.radians(max(p["arm_deg"], 20))  # 落ちる値の時も型の形が崩れないように、描く角度の下限を置く
    base = 28
    hgt = min(base * math.tan(a), 50)
    base = hgt / math.tan(a)
    pts = [(0, 0), (base, hgt), (0, hgt)]
    return Part(4, "gauge", "腕の角度の型", pts, label_xy=(1, hgt - 5), label="4")


def _cone_part(p):
    """胴の扇。真ん中（Θ=0 の向き）が顔の前。右の辺の帯で丸めて貼り、弧の歯を中へ折って底を貼る。"""
    s, th = cone(p)
    g = p["glue"]
    n = 10
    arc = lambda r, a: (r * math.sin(a), r * math.cos(a))
    a0, a1 = -th / 2, th / 2
    # 弧は歯の付け根で直線（弦）にする。折る線をまっすぐにするため。弦と弧の差は 1mm 未満
    edges = [a0 + (a1 - a0) * i / n for i in range(n + 1)]
    pts = [(0.0, 0.0)]
    glue = []
    folds = []
    for i in range(n):
        b0, b1 = edges[i], edges[i + 1]
        q0, q1 = arc(s, b0), arc(s, b1)
        t0, t1 = arc(s + 4, b0 + (b1 - b0) * 0.18), arc(s + 4, b1 - (b1 - b0) * 0.18)
        pts += [q0, t0, t1]
        glue.append([q0, t0, t1, q1])
        folds.append((q0, q1))
    end = arc(s, a1)
    pts.append(end)
    # 丸めて貼る帯（右の辺の外）。頂点の近くは細くなりすぎるので付けない。
    ux, uy = math.sin(a1), math.cos(a1)
    nx, ny = uy, -ux  # 右の辺の外向き
    p_in, p_out = (ux * s * 0.15, uy * s * 0.15), end
    strip = [p_out, (p_out[0] + nx * g - ux * 2, p_out[1] + ny * g - uy * 2), (p_in[0] + nx * g + ux * 2, p_in[1] + ny * g + uy * 2), p_in]
    pts += strip[1:3] + [p_in]
    glue.append(strip)
    sector = [(0.0, 0.0)] + [arc(s, a) for a in edges]
    xs = [x for x, _ in pts]
    ys = [y for _, y in pts]
    dx, dy = -min(xs), -min(ys)
    mv = lambda ps: [(x + dx, y + dy) for x, y in ps]
    part = Part(1, "cone", "胴", mv(pts), label_xy=(dx - 3, dy + s * 0.75), label="1 胴")
    part.glue = [mv(gl) for gl in glue]
    part.mountain = [tuple(mv(list(f))) for f in folds]
    sec = Polygon(mv(sector)).buffer(-0.6)
    hood_d = 0.3 * s
    art = _clip(mv(sector), sec, BODY, SUMI, 0.3)
    hood = [(0.0, 0.0)] + [arc(hood_d, a0 + (a1 - a0) * i / 24) for i in range(25)]
    art += _clip(mv(hood), sec, HAT, SUMI, 0.35)
    # 顔は前の真ん中。円錐に巻くと横に縮むので、扇の上では少し横に広い楕円にする。
    fr = 0.11 * s
    fc = hood_d + fr * 0.85
    face = [(fr * 1.15 * math.cos(t), fc + fr * math.sin(t)) for t in [2 * math.pi * i / 32 for i in range(32)]]
    art += _clip(mv(face), sec, SKIN, SUMI, 0.35)
    for ex in (-0.45, 0.45):
        art += _clip_line(mv([(ex * fr - 0.35 * fr, fc - 0.15 * fr), (ex * fr, fc - 0.02 * fr), (ex * fr + 0.35 * fr, fc - 0.15 * fr)]), sec, SUMI, 0.45)
    # 胴の墨の点々。絵の配置をまねた決まった位置（乱数にしないのは、刷るたびに絵が変わらないため）。
    for fd, fa in ((0.52, -0.08), (0.55, 0.12), (0.6, -0.3), (0.64, 0.02), (0.68, 0.26), (0.74, -0.18), (0.78, 0.1),
                   (0.82, -0.38), (0.85, 0.32), (0.9, -0.05), (0.62, -0.5), (0.72, 0.5), (0.88, 0.2), (0.8, -0.6), (0.7, 0.75), (0.86, -0.82)):
        d, a = fd * s, fa * th / 2
        cx, cy = arc(d, a)
        tri = [(cx - 1.6, cy - 0.6), (cx + 1.6, cy - 0.6), (cx, cy + 0.9)]
        art += _clip(mv(tri), sec, SUMI)
    part.art = art
    part.hide_folds = True
    return part


def _base(p):
    R = p["base_r"] + 0.5  # 歯の糊代の外から貼るので、胴の底より少し大きく
    part = Part(2, "base", "底", _circle(R, R, R), label_xy=(R - 2, R - 1.5), label="2")
    part.art = [{"kind": "poly", "pts": _circle(R, R, R - 0.4), "fill": BODY if p["hold"] == "flat" else GOFUN, "stroke": SUMI, "sw": 0.2}]
    return part


def parts(p):
    if _yaji(p):
        out = [_board(p), _doll(p), _stand(p)]
        if p["hold"] == "arm":
            out.append(_gauge(p))
        return out
    return [_cone_part(p), _base(p)]


def place(by_key, page, top, gap):
    """棚に並べるように左から詰める。文字は部品の下に全幅で置く（物差しの 100mm を必ず入れるため）。"""
    x, y, row = page.x0, top, 0.0
    for k in ("board", "cone", "base", "doll", "stand", "gauge"):
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
    paper = f"紙（厚さ 0.15mm 前後・{p['paper_gsm']}g/m² の見込み）"
    why = "家庭のプリンタで刷って作るため"
    if _yaji(p):
        rows = [
            {"number": 1, "key": "board", "name": "着物の板", "qty": 1, "material": paper, "substituted": True, "original_guess": "紙か薄い板（不明）", "reason": why},
            {"number": 2, "key": "doll", "name": "人形", "qty": 1, "material": paper, "substituted": True, "original_guess": "土か張子（不明）", "reason": why},
            {"number": 3, "key": "stand", "name": "台", "qty": 1, "material": paper, "substituted": True, "original_guess": "木（絵の色による推測）", "reason": why},
            {"number": 7, "key": "pole", "name": "柄", "qty": 1, "material": "竹串 1 本（先の尖った方を上に）", "substituted": True, "original_guess": "竹か木の棒（絵の長い棒）", "reason": "尖った先を支点にできるため"},
            {"number": 8, "key": "weight", "name": "錘", "qty": 2, "material": f"油粘土 {p['weight_g']:g}g を 2 つ", "substituted": True, "original_guess": "不明（絵の丸い物）", "reason": "量を変えて試しやすいため"},
        ]
        if p["hold"] == "arm":
            rows.append({"number": 9, "key": "arm", "name": "腕", "qty": 2, "material": f"竹ひご {p['arm_len']:g}mm を 2 本", "substituted": True, "original_guess": "針金か竹（絵のまっすぐな線）", "reason": "まっすぐで軽いため"})
        else:
            rows.append({"number": 9, "key": "thread", "name": "糸", "qty": 2, "material": f"糸 {p['thread_len'] + 20:g}mm を 2 本", "substituted": True, "original_guess": "糸（絵の細い線の読み）", "reason": "錘を吊るため"})
        return rows
    rows = [
        {"number": 1, "key": "cone", "name": "胴", "qty": 1, "material": paper, "substituted": True, "original_guess": "張子（起き上がりの作りの一般による推測）", "reason": why},
        {"number": 2, "key": "base", "name": "底", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明", "reason": why},
    ]
    if p["hold"] == "round":
        clay = CLAY_G_PER_MM3 * 2 / 3 * math.pi * p["base_r"] ** 3
        rows.append({"number": 8, "key": "weight", "name": "丸い底の粘土", "qty": 1, "material": f"油粘土 約 {clay:.0f}g（半径 {p['base_r']:g}mm の半球）", "substituted": True, "original_guess": "土の重り（推測）", "reason": "丸い底と重りを 1 つで作れるため"})
    return rows


def materials(p):
    rows = bom(p)
    out = [f"{rows[0]['material']}を 1 枚", "のり、はさみ、定規、セロハンテープ"]
    out += [r["material"] for r in rows if r["key"] in ("pole", "weight", "arm", "thread")]
    return out


def steps(p):
    out = ["刷った物差しに定規を当て、10cm か確かめる", "部品を外の線で切る（色の切れ目の細い白で折る）"]
    if _yaji(p):
        out += ["3 台の縁を下へ折って箱にし、真ん中の穴に竹串を通す。竹串の先から " + f"{doll_top(p) + p['doll_h']:.0f}mm の所で止める",
                "2 人形の背を竹串に貼り、下の糊代を台に貼る"]
        if p["hold"] == "arm":
            out += ["1 着物の板を袖の端で山折りする。V の先から 5mm には糊を付けず、残りを貼り合わせる",
                    "4 角度の型の斜めの辺に沿わせて、竹ひごを裾の両方の角にテープで貼る。先に粘土を丸めて付ける",
                    "V の先の袋に竹串の先を入れて載せる。傾くなら粘土を少し足し引きする"]
        else:
            out += ["1 着物の板を袖の端で山折りして貼る。V の先に竹串の先を差し、のりで止める",
                    f"糸の端を裾の両方の角にテープで貼り、{p['thread_len']:g}mm 下に粘土を付ける",
                    "竹串を両手の掌にはさみ、こすって回す"]
    else:
        out += ["1 胴を、絵を外にして円錐に丸め、右の帯の糊代で貼る", "弧の歯を中へ折り、2 底を外から貼る"]
        if p["hold"] == "round":
            out += [f"粘土を半径 {p['base_r']:g}mm の半球に丸め、底に押し付けて付ける", "手で倒して、離す"]
        else:
            out.append("平らな所に立てて、指で少し押す")
    return out


RESULTS = ("戻った", "戻らない", "わからない")


def measures(p):
    """数でなく、どう動くかを言葉か絵で予想する（U-25 の案 1、虎と同じ形）。"""
    if p["hold"] == "spin":
        return {"predict": "柄を回すと、錘はどう動くと思いますか（言葉か絵で）", "rows": [[("回した速さ（ゆっくり・速く）", 40)]]}
    if _yaji(p):
        return {"predict": "片方の錘を指で下げて離すと、どう動くと思いますか（言葉か絵で）", "rows": [[("押した所（錘・袖・笠）", 40)]]}
    return {"predict": "倒して手を離すと、どう動くと思いますか（言葉か絵で）", "rows": [[("倒した向き（前・横・後ろ）", 40)]]}


def diagram(x, y, w, h, p):
    """正面の図。支点（竹串の先）、着物の板の外形、腕か糸、錘。起き上がりは横の図と丸い底。"""
    shapes = []
    if _yaji(p):
        shape, _, _ = _board_geom(p)
        wx, wz = weight_pos(p)
        hx, hz = hem_corner(p)
        r = weight_r(p)
        minx, miny, maxx, _ = shape.bounds
        span_x = max(maxx, wx + r) * 2
        bottom = max(wz + r, doll_top(p) + p["doll_h"] + 20)
        top_y = miny + POCKET
        s = min(w / span_x, h / (bottom - top_y))
        cx, cy = x + w / 2, y - top_y * s
        tr = lambda px, pz: (cx + px * s, cy + pz * s)
        outline = [tr(a, b + POCKET) for a, b in list(shape.exterior.coords)[:-1]]
        shapes.append({"kind": "poly", "pts": outline, "fill": KIMONO, "sw": 0.25})
        for sgn in (-1, 1):
            x1, y1 = tr(sgn * hx, hz)
            x2, y2 = tr(sgn * wx, wz)
            shapes.append({"kind": "line", "x1": x1, "y1": y1, "x2": x2, "y2": y2})
            shapes.append({"kind": "poly", "pts": _circle(x2, y2, r * s, 16), "fill": SHU, "sw": 0.2})
        px, py = tr(0, 0)
        shapes.append({"kind": "line", "x1": px, "y1": py, "x2": px, "y2": y + h, "dash": "1,0.6"})
        sx0, sy0 = tr(-p["stand"] / 2, doll_top(p) + p["doll_h"])
        shapes.append({"kind": "rect", "x": sx0, "y": sy0, "w": p["stand"] * s, "h": STAND_RIM * s})
        return shapes
    R, H = p["base_r"], p["body_h"]
    tall = H + R
    s = min(w / (2 * R + 6), h / (tall + 4))
    cx, base_y = x + w / 2, y + 2 + H * s
    shapes.append({"kind": "poly", "pts": [(cx, y + 2), (cx + R * s, base_y), (cx - R * s, base_y)], "fill": BODY, "sw": 0.25})
    if p["hold"] == "round":
        half = [(cx + R * s * math.cos(t), base_y + R * s * math.sin(t)) for t in [math.pi * i / 16 for i in range(17)]]
        shapes.append({"kind": "poly", "pts": half, "fill": SHU, "sw": 0.25})
        floor = base_y + R * s
    else:
        floor = base_y
    shapes.append({"kind": "line", "x1": x, "y1": floor, "x2": x + w, "y2": floor})
    gy = floor - kobo_cg(p) * s
    shapes.append({"kind": "rect", "x": cx - 0.8, "y": gy - 0.8, "w": 1.6, "h": 1.6})
    return shapes
