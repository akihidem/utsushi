"""雛形 spin_toy: 回る芯（つまようじ・竹ひご）に、羽の車か円盤を通して回す。『江都二色』の風車・独楽・手車の線（11-04）。

形の考え: 線の玩具 6 件を 1 本に乗せ、形の違いは shape（羽の車・平たい円盤・円錐の胴・手車）、絵の違いは look で出す。
どう回すかの読みが仮説の違いなので、HYP_KEY は drive（回し方）にした。形は図で見えるが、回し方は図に描かれていないため。
どの寸法も実物では未確認の見込み。Claude が変えてよいのは ALLOWED の名前の値だけで、座標には触れない。
"""
import math

from shapely.affinity import rotate, translate
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

from ._paper import paper_name
from ..model import Failure, Part

ID = "spin_toy"
SHEET_SET = "spin-v1"
# 手順の紙の図の説明（instructions.compose_sheet）。御来迎の筒の言葉を刷らないため。
DIAGRAM_CAPTION = "回る芯と羽・円盤（破線は芯）"
# 結果の欄の見出し。この形の玩具に合う問いにする。
RESULT_HEAD = "おもちゃとして回りましたか（1 つに丸）"
HYP_KEY = "drive"
DEFAULTS = {
    "shape": "pinwheel", "look": "kazaguruma", "drive": "pitch",
    # 羽の車。図の風車は 8 本の細い棒の先に四角い紙（コマ 20）。紙 1 枚で棒と羽を一続きに切る形に置き換えた。
    "wheels": 1, "blade_count": 8, "hub_r": 7, "arm_len": 26, "arm_w": 4, "blade": 18, "blade_angle": 25,
    "wheel_offset": 20, "drum_d": 40, "drum_w": 12, "drum_gap": 14, "striker_len": 18, "rooster_w": 34,
    # 独楽。円盤は紙を重ねて厚くする。つまようじ 1 本（60mm 前後）を芯にする見込み。
    "disc_d": 50, "disc_layers": 4, "axis_len": 60, "axis_below": 8,
    "cone_r": 25, "cone_h": 22, "cone_pieces": 2, "lid_layers": 3, "knob_h": 0,
    # 紐。太さは手縫い糸を 2 本どりにした見込み。
    "string_d": 1.0, "string_turns": 8, "string_len": 600,
    # 手車。2 枚の円盤の間に巻いた紙の芯を挟む。
    "hub_w": 6, "hub_strip": 40,
    # 紙の面密度は見込み。実物の紙を量ったら置き換える。
    "paper_gsm": 150,
}
RANGES = {
    "wheels": (1, 2), "blade_count": (4, 12), "hub_r": (4, 12), "arm_len": (8, 40), "arm_w": (2, 8), "blade": (8, 30),
    # 範囲は広く取り、回るかどうかの床（check_physics）を範囲の検査より先に落とさないようにする。
    "blade_angle": (0, 80),
    "wheel_offset": (5, 40), "drum_d": (25, 60), "drum_w": (6, 20), "drum_gap": (6, 30), "striker_len": (6, 40), "rooster_w": (20, 50),
    "disc_d": (25, 90), "disc_layers": (1, 8), "axis_len": (30, 150), "axis_below": (1, 30),
    "cone_r": (12, 40), "cone_h": (8, 40), "cone_pieces": (1, 2), "lid_layers": (1, 6), "knob_h": (0, 20),
    "string_d": (0.3, 3), "string_turns": (1, 30), "string_len": (100, 1500),
    "hub_w": (2, 20), "hub_strip": (10, 120),
    "paper_gsm": (40, 400),
}
SHAPES = ("pinwheel", "disc", "cone", "yoyo")
LOOKS = ("kazaguruma", "kanko", "koma", "oyama", "tetsudo", "teguruma")
# 形ごとに読める回し方。形に合わない回し方は、刷っても遊び方が書けないので範囲の検査で落とす。
DRIVES = {"pinwheel": ("pitch", "cup", "beat"), "disc": ("twist", "palm", "string"), "cone": ("twist", "string"), "yoyo": ("yoyo", "handle")}
ALLOWED = {"blade_count", "arm_len", "blade", "blade_angle", "hub_r", "striker_len", "drum_gap",
           "disc_d", "disc_layers", "axis_len", "axis_below", "cone_r", "cone_h", "cone_pieces", "lid_layers",
           "string_turns", "string_len", "hub_w", "hub_strip", "paper_gsm"}
PARAM_NAMES = {"blade_count": "羽の数", "arm_len": "羽の柄の長さ（mm）", "blade": "羽の一辺（mm）", "blade_angle": "羽のひねり（度）",
               "hub_r": "車の中心の半径（mm）", "striker_len": "打ち木の長さ（mm）", "drum_gap": "軸から太鼓の下まで（mm）",
               "disc_d": "円盤の径（mm）", "disc_layers": "円盤の重ねる枚数", "axis_len": "芯の長さ（mm）", "axis_below": "円盤の下に出す芯（mm）",
               "cone_r": "胴の半径（mm）", "cone_h": "胴の高さ（mm）", "cone_pieces": "胴を分ける枚数", "lid_layers": "ふたの重ねる枚数",
               "string_turns": "紐を巻く回数", "string_len": "紐の長さ（mm）", "hub_w": "手車の芯の幅（mm）", "hub_strip": "芯に巻く帯の長さ（mm）",
               "paper_gsm": "紙の重さ（g/m²）"}

# 江戸の色（本人の方針: 朱・藍・黄土・墨・胡粉の白）。原図の画素は使わず、色の名前で塗り直す。
SHU, AI, OUDO, SUMI, GOFUN, TAISHA, USUCHA = "#c8553d", "#3b5a7a", "#c9a24e", "#3a3631", "#f1ece0", "#8b5a3c", "#d9b98a"
PAPER_T = 0.2  # 紙 1 枚の厚さの見込み（mm）。重ねた円盤の厚さに使う
AXIS_D = 2.0  # つまようじの太さの見込み
HOLE_R = 1.1
# 指でひねるのに要る芯の長さ。指先 2 本でつまむ幅の見込み。
GRIP = 12
PALM = 35  # 両手の平でもむのに要る長さ。手の平 2 枚の幅の見込み
# 芯が円盤の径に比べて長すぎると、回る前に倒れる。紙の独楽を試す前の安全側の見込み。
AXIS_RATIO = 1.6
# 重心が芯からこれより外れると、回すと首を振って早く倒れると見込む（実物で確かめるまでの値）。
BALANCE_TOL = 0.15
PITCH_MIN, PITCH_MAX = 10, 45  # 浅いと風を受けず、深いと受け流す。紙の風車の作例の幅の見込み
BLADE_GAP = 2  # ひねった羽どうしが当たらない隙間
SEAM_TAB = 5  # 胴の継ぎ目の糊代
RIM_TAB = 4  # 胴の上の縁の糊代（ふたの裏に貼る）
STRIKE_MIN, STRIKE_MAX = 2, 8  # 打ち木が太鼓の縁にかかる長さ。浅いと当たらず、深いと引っかかって止まる
FORK = 3  # 手車の柄の、円盤との隙間と紙の厚さと、外に出す芯の見込み
HANDLE_W, HANDLE_L = 12, 80  # 柄の幅と長さ。手で握れる長さの見込み

TITLES = {"pitch": "羽をひねり正面の風で回す", "cup": "羽を折って横の風で回す", "beat": "風で回し太鼓を打つ",
          "twist": "芯を指でひねって回す", "palm": "芯を両手でもんで回す", "string": "紐を巻いて引いて回す",
          "yoyo": "紐を巻いて上下させる", "handle": "柄に通して紐を引いて回す"}


def title(p):
    return TITLES[p["drive"]]


def spec():
    return {"template_id": ID, "defaults": DEFAULTS, "ranges": RANGES, "shape": SHAPES, "look": LOOKS, "drive": DRIVES}


def check_range(p):
    out = []
    for k, v in p.items():
        if k == "shape":
            if v not in SHAPES:
                out.append(Failure("F5.range", k, f"{v} は {SHAPES} のどれでもない"))
        elif k == "look":
            if v not in LOOKS:
                out.append(Failure("F5.range", k, f"{v} は {LOOKS} のどれでもない"))
        elif k == "drive":
            allowed = DRIVES.get(p.get("shape"), ())
            if v not in allowed:
                out.append(Failure("F5.range", k, f"{v} は形 {p.get('shape')} の回し方 {allowed} のどれでもない"))
        elif k not in RANGES:
            out.append(Failure("F5.range", k, "知らない寸法の名前"))
        elif not isinstance(v, (int, float)) or isinstance(v, bool) or not RANGES[k][0] <= v <= RANGES[k][1]:
            out.append(Failure("F5.range", k, f"{v} は範囲 {RANGES[k]} の外"))
    for k in ("wheels", "blade_count", "disc_layers", "cone_pieces", "lid_layers", "string_turns"):
        if isinstance(p.get(k), float) and not p[k].is_integer():
            out.append(Failure("F5.range", k, f"{p[k]} は枚数・本数なので整数"))
    return out


# --- 式（床と台帳が同じ数を見るように、ここに集める） ---

def wheel_radius(p):
    return p["hub_r"] + p["arm_len"] - 1 + p["blade"] * math.sqrt(2)


def blade_gap(p):
    """隣り合う羽の、羽の中心の高さでの隙間。羽は菱形に置くので、幅は対角線 blade·√2。"""
    d = p["blade"] * math.sqrt(2)
    rc = p["hub_r"] + p["arm_len"] - 1 + d / 2
    return 2 * rc * math.sin(math.pi / int(p["blade_count"])) - d


def stack(p):
    """芯に通す紙の厚さ。円盤の形は重ねた円盤、胴の形はふたの重ね。"""
    return (p["disc_layers"] if p["shape"] in ("disc", "yoyo") else p["lid_layers"]) * PAPER_T


def axis_above(p):
    """円盤（胴の形はふた）の上に出る芯の長さ。指や紐が掛かるのはここだけ。"""
    body = p["cone_h"] if p["shape"] == "cone" else 0
    return p["axis_len"] - p["axis_below"] - body - stack(p)


def slant(p):
    return math.hypot(p["cone_r"], p["cone_h"])


def balance_offset(p):
    """組んだ時の重心の、芯からのずれ（mm）。胴の継ぎ目の糊代だけが芯の周りで偏る。

    胴を 1 枚で巻くと糊代が片側に 1 つ寄る。2 枚に分けて糊代を向かい合わせにすると打ち消す（この雛形の形の工夫）。
    紙の面密度は同じと見て、面積で重さを数える。継ぎ目は胴の斜面の中ほど（芯から半径の半分）にあると見る。
    """
    if p["shape"] != "cone":
        return 0.0  # 円盤も手車も、穴を中心に置いた丸い紙だけなので偏りが無い
    s = slant(p)
    tab = SEAM_TAB * (s - 3)
    total = math.pi * p["cone_r"] * s + math.pi * p["cone_r"] ** 2 * p["lid_layers"] + tab * p["cone_pieces"]
    if int(p["cone_pieces"]) % 2 == 0:
        return 0.0
    return tab * (p["cone_r"] / 2) / total


def hub_d(p):
    """手車の芯。紙の帯をつまようじに巻いた太さ。巻いた紙の断面積は帯の長さ×厚さ。"""
    return math.sqrt(AXIS_D ** 2 + 4 * p["hub_strip"] * 2 * PAPER_T / math.pi)  # 帯は半分に折って 2 枚重ね


def string_capacity(p):
    """手車の芯の溝に巻ける紐の長さ（mm）。溝の幅に並ぶ巻き数×段の数で、段ごとに径が増える。"""
    per_row = max(0, int(p["hub_w"] // p["string_d"]))
    rows = max(0, int((p["disc_d"] / 2 - hub_d(p) / 2 - 3) // p["string_d"]))
    return sum(math.pi * (hub_d(p) + (2 * k + 1) * p["string_d"]) * per_row for k in range(rows))


def yoyo_axle_need(p):
    """手車の芯（つまようじ）に要る長さ。柄に通す形は、両側に柄の分を足す。"""
    core = p["hub_w"] + 2 * stack(p)
    # 柄に通す形は、柄の 2 枚の紙と隙間、反対の端の玉の分を足す。
    return core + (4 * FORK if p["drive"] == "handle" else 2)


def metrics(p):
    """台帳の式（F7）。形によらず同じ名前を返し、版の前後を同じ物差しで比べられるようにする。"""
    return {
        "blade_gap_mm": round(blade_gap(p), 2) if p["shape"] == "pinwheel" else 0.0,
        "wheel_radius_mm": round(wheel_radius(p), 2) if p["shape"] == "pinwheel" else 0.0,
        "axis_above_mm": round(axis_above(p), 2) if p["shape"] in ("disc", "cone") else 0.0,
        "balance_offset_mm": round(balance_offset(p), 3),
        "string_capacity_mm": round(string_capacity(p), 1) if p["shape"] == "yoyo" else 0.0,
    }


def check_physics(p):
    out = []
    shape, drive = p["shape"], p["drive"]
    if shape == "pinwheel":
        if blade_gap(p) < BLADE_GAP:
            out.append(Failure("F5.spin", "羽", f"隣の羽との隙間 {blade_gap(p):.1f}mm（{BLADE_GAP}mm まで）で、ひねると羽どうしが当たる"))
        if drive in ("pitch", "beat") and not PITCH_MIN <= p["blade_angle"] <= PITCH_MAX:
            out.append(Failure("F5.spin", "羽のひねり", f"{p['blade_angle']}° は {PITCH_MIN}〜{PITCH_MAX}° の外で、風を受けないか受け流す"))
        if int(p["blade_count"]) * p["arm_w"] > 2 * math.pi * p["hub_r"] * 0.8:
            out.append(Failure("F5.spin", "羽の柄", "羽の柄が中心で重なり、切り分けられない"))
        if drive == "beat":
            reach = p["striker_len"] - p["drum_gap"]
            if not STRIKE_MIN <= reach <= STRIKE_MAX:
                out.append(Failure("F5.spin", "打ち木", f"打ち木が太鼓の縁に {reach:g}mm かかる（{STRIKE_MIN}〜{STRIKE_MAX}mm）。浅いと当たらず、深いと引っかかる"))
        if int(p["wheels"]) == 2:
            # 2 つの車は太鼓の真下の軸の両端に付く。太鼓の幅の内に入ると、羽が太鼓の胴に当たる。
            if p["wheel_offset"] < p["drum_w"] / 2 + 3 and wheel_radius(p) > p["drum_gap"]:
                out.append(Failure("F5.spin", "羽の車", "羽の車が太鼓の胴に当たる"))
            if drive == "beat" and p["striker_len"] >= wheel_radius(p):
                out.append(Failure("F5.spin", "打ち木", "打ち木が羽より長く、軸の回りで竹ひごに当たる"))
    elif shape in ("disc", "cone"):
        diameter = p["disc_d"] if shape == "disc" else 2 * p["cone_r"]
        up = axis_above(p)
        need = {"twist": GRIP, "palm": PALM, "string": p["string_turns"] * p["string_d"] + 8}[drive]
        if up < need:
            out.append(Failure("F5.spin", "芯", f"上に出る芯が {up:.1f}mm で、{TITLES[drive]}のに {need:g}mm 要る"))
        if p["axis_len"] > AXIS_RATIO * diameter:
            out.append(Failure("F5.spin", "芯", f"芯 {p['axis_len']}mm が径 {diameter:g}mm の {AXIS_RATIO} 倍より長く、回る前に倒れる"))
        if not 3 <= p["axis_below"] <= 0.3 * diameter:
            out.append(Failure("F5.spin", "芯の先", f"下に出す芯 {p['axis_below']}mm は 3〜{0.3 * diameter:.0f}mm の外で、床に着かないか首を振る"))
        off = balance_offset(p)
        if off > BALANCE_TOL:
            out.append(Failure("F5.balance", "胴", f"重心が芯から {off:.2f}mm ずれる（{BALANCE_TOL}mm まで）。胴を 2 枚に分けて糊代を向かい合わせる"))
        if shape == "cone" and 0 < p["knob_h"] < 5:
            out.append(Failure("F5.spin", "つまみ", f"つまみの帯 {p['knob_h']}mm が細く、芯に巻いても指で持てない"))
        if shape == "cone" and math.tau * p["cone_r"] / slant(p) / int(p["cone_pieces"]) > math.radians(300):
            out.append(Failure("F5.spin", "胴", "胴の扇形が開きすぎて 1 枚から切れない"))
    else:
        if p["string_len"] > string_capacity(p):
            out.append(Failure("F5.spin", "紐", f"紐 {p['string_len']}mm が芯の溝に巻ける {string_capacity(p):.0f}mm より長い"))
        if p["hub_w"] < 2 * p["string_d"]:
            out.append(Failure("F5.spin", "芯", "芯の幅が紐 2 本分より狭く、紐が溝から外れる"))
        if yoyo_axle_need(p) > p["axis_len"]:
            out.append(Failure("F5.spin", "芯", f"芯 {p['axis_len']}mm が、円盤と柄を通すのに要る {yoyo_axle_need(p):.0f}mm より短い"))
        if hub_d(p) > p["disc_d"] / 2:
            out.append(Failure("F5.spin", "芯", "巻いた芯が太く、紐を巻く溝が残らない"))
    return out


# --- 部品 ---

def _circle(r, cx=0.0, cy=0.0):
    return Point(cx, cy).buffer(r, quad_segs=24)


def _coords(g):
    return [(round(x, 3), round(y, 3)) for x, y in list(g.exterior.coords)[:-1]]


def _fill(g, color, sw=None, stroke=SUMI):
    item = {"kind": "poly", "pts": _coords(g), "fill": color}
    if sw:
        item.update(stroke=stroke, sw=sw)
    return item


def _normalize(part):
    """部品の座標を左上が (0,0) になるように寄せる。配置（place）は部品の左上を原点として置くため。"""
    mx, my = min(x for x, _ in part.outline), min(y for _, y in part.outline)
    sh = lambda ps: [(x - mx, y - my) for x, y in ps]
    part.outline = sh(part.outline)
    for item in part.art:
        item["pts"] = sh(item["pts"])
    part.valley = [tuple(sh(list(seg))) for seg in part.valley]
    part.mountain = [tuple(sh(list(seg))) for seg in part.mountain]
    part.glue = [sh(g) for g in part.glue]
    part.holes = [(x - mx, y - my, r) for x, y, r in part.holes]
    part.cuts = [(x - mx, y - my, w, h) for x, y, w, h in part.cuts]
    part.label_xy = (part.label_xy[0] - mx, part.label_xy[1] - my)
    return part


def _wheel(number, key, p, hub_color):
    """羽の車 1 枚。中心の丸・柄・菱形の羽を一続きに切る。羽は柄の先に角を付けて菱形に置く（コマ 20 の図の向き）。"""
    n, hr, L, aw, b = int(p["blade_count"]), p["hub_r"], p["arm_len"], p["arm_w"], p["blade"]
    d = b * math.sqrt(2)
    r0 = hr + L - 1  # 柄と羽を 1mm 重ねて、切った時に細く切れないようにする
    pieces, art, valley = [_circle(hr)], [], []
    halves = []
    for i in range(n):
        a = 360 * i / n
        arm = rotate(box(hr - 1, -aw / 2, r0 + 1, aw / 2), a, origin=(0, 0))
        dia = rotate(Polygon([(r0, 0), (r0 + d / 2, -d / 2), (r0 + d, 0), (r0 + d / 2, d / 2)]), a, origin=(0, 0))
        lead = rotate(Polygon([(r0, 0), (r0 + d / 2, -d / 2), (r0 + d, 0)]), a, origin=(0, 0))
        trail = rotate(Polygon([(r0, 0), (r0 + d, 0), (r0 + d / 2, d / 2)]), a, origin=(0, 0))
        pieces += [arm, dia]
        # 柄の塗りは羽の手前で止める。柄の紙は羽に 1mm 重なるので、そのまま塗ると受け皿の折り線をまたぐ。
        halves.append((rotate(box(hr, -aw / 2, r0 - 0.3, aw / 2), a, origin=(0, 0)), lead, trail))
        if p["drive"] == "cup":
            # 受け皿に折る線は羽の対角線で、朱と黄土の境に置く（本人の決定 d: 折り線は色の境、見える面に刷らない）。
            seg = rotate(LineString([(r0, 0), (r0 + d, 0)]), a, origin=(0, 0))
            valley.append(tuple(seg.coords))
    outline = unary_union(pieces)
    for arm, lead, trail in halves:
        art.append(_fill(arm.difference(_circle(hr)).buffer(-0.3), GOFUN))
        art.append(_fill(lead.buffer(-0.25), SHU))
        art.append(_fill(trail.buffer(-0.25), OUDO))
    art.append(_fill(_circle(hr - 0.6), hub_color))
    art.append(_fill(_circle(hr * 0.45), GOFUN))
    # 番号は角度 0 の羽の真ん中に置く。中心の丸は小さく、穴とも重なるため。
    part = Part(number, key, "羽の車", _coords(outline), label_xy=(r0 + d / 2 - 1.2, -1.8), label=str(number),
                art=art, valley=valley, holes=[(0, 0, HOLE_R)], hide_folds=True)
    return _normalize(part)


def _disc(number, key, name, r, art=None, label_dy=0.25):
    """丸い紙 1 枚。芯の穴は中心。ラベルは穴を避けて少し下に置く。"""
    return _normalize(Part(number, key, name, _coords(_circle(r)), label_xy=(-r * 0.15, r * label_dy), label=str(number),
                           art=art or [], holes=[(0, 0, HOLE_R)]))


def _rings(r, colors):
    """木目の年輪のような同心の輪（コマ 21・26 の円盤の塗り）。外から順に色を置く。"""
    out = []
    for i, c in enumerate(colors):
        rr = r * (1 - i / len(colors)) - 0.4
        if rr > 1.5:
            out.append(_fill(_circle(rr), c))
    return out


def _strip(number, key, name, w, h, fill=None, glue_at_end=0, holes=(), stripes=None):
    """細長い帯。glue_at_end は端の糊代の長さ。帯の絵は糊代を避ける。"""
    pts = [(0, 0), (w, 0), (w, h), (0, h)]
    art, glue = [], []
    if glue_at_end:
        glue = [[(w - glue_at_end, 0), (w, 0), (w, h), (w - glue_at_end, h)]]
    if fill:
        art.append(_fill(box(0.2, 0.2, w - glue_at_end - 0.2, h - 0.2), fill))
    if stripes:
        for x in range(4, int(w - glue_at_end) - 2, 8):
            art.append({"kind": "line", "pts": [(x, 0.6), (x, h - 0.6)], "stroke": stripes, "sw": 0.6})
    return Part(number, key, name, pts, label_xy=(1, 1), label=str(number), art=art, glue=glue, holes=list(holes))


# 鶏の輪郭は、コマ 14 の絵を見て手で取った点（左向き、幅 100 の箱）。絵の画素は使っていない。
_ROOSTER = [(6, 20), (14, 14), (18, 5), (26, 3), (30, 11), (33, 20), (48, 25), (58, 20), (62, 6), (75, 0), (90, 6), (98, 22),
            (96, 40), (88, 52), (76, 58), (60, 64), (40, 66), (26, 60), (18, 48), (16, 32), (10, 25)]
_COMB = [(16, 6), (19, 2), (26, 1), (29, 8), (24, 12), (18, 12)]
_CHEST = [(18, 40), (30, 44), (46, 54), (60, 62), (40, 65), (26, 59), (19, 49)]
_TAIL = [[(66, 8), (82, 6), (92, 18)], [(64, 16), (82, 16), (90, 32)], [(62, 26), (78, 28), (84, 46)], [(60, 36), (72, 40), (74, 54)]]


def _rooster(number, p):
    """太鼓の上の鶏。下に糊代を付け、谷折りで太鼓の帯に貼る。折る線は糊代と鶏の色の境（決定 d）。"""
    s = p["rooster_w"] / 100
    sc = lambda ps: [(x * s, y * s) for x, y in ps]
    # とさかは頭の輪郭の外へ出るので、切る形に含める。
    body = unary_union([Polygon(sc(_ROOSTER)), Polygon(sc(_COMB))])
    base_y = 64 * s
    tab = box(30 * s, base_y - 0.5, 70 * s, base_y + 6)
    outline = unary_union([body, tab]).simplify(0.05)
    above = box(-1, -1, 101 * s, base_y - 0.3)
    art = [_fill(body.intersection(above).buffer(-0.2), OUDO, sw=0.2), _fill(Polygon(sc(_COMB)).intersection(above), SHU),
           _fill(Polygon(sc(_CHEST)).intersection(above).buffer(-0.3), SUMI)]
    clip = body.buffer(-0.4).intersection(above)
    for line in _TAIL:
        piece = LineString(sc(line)).intersection(clip)
        for g in getattr(piece, "geoms", [piece]):
            if not g.is_empty and g.geom_type == "LineString":
                art.append({"kind": "line", "pts": list(g.coords), "stroke": SUMI, "sw": 0.9})
    glue = [[(30 * s, base_y), (70 * s, base_y), (70 * s, base_y + 6), (30 * s, base_y + 6)]]
    part = Part(number, "rooster", "鶏", _coords(outline), label_xy=(50 * s, 36 * s), label=str(number), art=art,
                valley=[((30 * s, base_y), (70 * s, base_y))], glue=glue, hide_folds=True)
    return _normalize(part)


def _drum_face(number, key, p):
    r = p["drum_d"] / 2
    # 図の太鼓の面の朱と黄土の印（コマ 14）。形は描き直した。
    art = [_fill(_circle(r - 0.3), GOFUN, sw=0.3), _fill(box(-r * 0.45, r * 0.25, r * 0.45, r * 0.4), SHU),
           _fill(box(-r * 0.45, -r * 0.4, r * 0.45, -r * 0.25), OUDO)]
    return _normalize(Part(number, key, "太鼓の面", _coords(_circle(r)), label_xy=(-1.5, -1.6), label=str(number), art=art))


def _cone_piece(number, key, p, look):
    """胴の扇形 1 枚。芯を通すため先を 3mm 切り落とした扇形で、上の縁に糊代の歯、片方の直線の縁に継ぎ目の糊代。"""
    s, n = slant(p), int(p["cone_pieces"])
    theta = math.tau * p["cone_r"] / s / n
    r_in, k = 3.0, max(4, int(math.degrees(theta) // 20))
    arc = [(s * math.cos(theta * i / k), s * math.sin(theta * i / k)) for i in range(k + 1)]
    inner = [(r_in * math.cos(theta * i / k), r_in * math.sin(theta * i / k)) for i in range(k, -1, -1)]
    body = Polygon(arc + inner)
    pieces, glue, valley = [body], [], []
    for (x1, y1), (x2, y2) in zip(arc, arc[1:]):
        # 歯は弦の外へ RIM_TAB。両端を少し絞ってふたの裏で歯どうしが重ならないようにする。
        nx, ny = (x1 + x2) / 2, (y1 + y2) / 2
        L = math.hypot(nx, ny)
        ux, uy = nx / L * RIM_TAB, ny / L * RIM_TAB
        tx, ty = (x2 - x1) * 0.15, (y2 - y1) * 0.15
        tooth = [(x1, y1), (x2, y2), (x2 + ux - tx, y2 + uy - ty), (x1 + ux + tx, y1 + uy + ty)]
        pieces.append(Polygon(tooth))
        glue.append(tooth)
        valley.append(((x1, y1), (x2, y2)))
    # 継ぎ目の糊代は角度 0 の縁の外（下側）。
    seam = [(r_in, 0), (s, 0), (s - 2, -SEAM_TAB), (r_in + 1, -SEAM_TAB)]
    pieces.append(Polygon(seam))
    glue.append(seam)
    valley.append(((r_in, 0), (s, 0)))
    outline = unary_union(pieces).simplify(0.01)
    inside = body.buffer(-0.3)
    art = []
    if look == "tetsudo":
        # 鉄胴ごまの胴は、上が代赭、下が墨に胡粉の縞（コマ 29）。扇形の同心の弧が、組むと胴を巻く縞になる。
        art.append(_fill(inside.difference(_circle(s * 0.62)), TAISHA))
        art.append(_fill(inside.intersection(_circle(s * 0.62 - 0.3)), SUMI))
        for f in (0.28, 0.36, 0.44, 0.52):
            ring = LineString([(s * f * math.cos(theta * i / 24), s * f * math.sin(theta * i / 24)) for i in range(25)]).intersection(inside.buffer(-0.5))
            for g in getattr(ring, "geoms", [ring]):
                if not g.is_empty and g.geom_type == "LineString":
                    art.append({"kind": "line", "pts": list(g.coords), "stroke": GOFUN, "sw": 0.9})
    else:
        # 大山独楽の胴は代赭のまだら（コマ 21）。まだらは点の塗りで描き直す。
        art.append(_fill(inside, TAISHA))
        for i in range(6):
            a = theta * (i + 0.5) / 6
            spot = _circle(1.6, s * 0.6 * math.cos(a), s * 0.6 * math.sin(a))
            if inside.buffer(-0.2).contains(spot):
                art.append(_fill(spot, SHU))
    mid = theta / 2
    # 番号は縁に近い明るい塗りの所に置く。先の近くは墨で、番号が読めない。
    part = Part(number, key, "胴", _coords(outline), label_xy=(s * 0.8 * math.cos(mid) - 1, s * 0.8 * math.sin(mid) - 1.5),
                label=str(number), art=art, glue=glue, valley=valley, hide_folds=True)
    return _normalize(part)


def parts(p):
    shape, look = p["shape"], p["look"]
    out = []
    if shape == "pinwheel":
        hub_color = AI if look == "kazaguruma" else SHU
        for i in range(int(p["wheels"])):
            out.append(_wheel(i + 1, f"wheel{i + 1}", p, hub_color))
        n = len(out)
        # 中心の補強の丸。紙 1 枚の中心は芯の回りで裂けやすいので、両面から 1 枚ずつ貼る見込み。
        for i in range(2 * int(p["wheels"])):
            out.append(_disc(n + 1 + i, f"hub{i + 1}", "中心の補強", p["hub_r"], [_fill(_circle(p["hub_r"] - 0.4), hub_color)], label_dy=0.1))
        n = len(out)
        if look == "kanko":
            out.append(_drum_face(n + 1, "drum_a", p))
            out.append(_drum_face(n + 2, "drum_b", p))
            band = math.pi * p["drum_d"] + 6
            out.append(_strip(n + 3, "drum_band", "太鼓の胴", band, p["drum_w"], fill=SHU, glue_at_end=6, holes=[(band / 4, p["drum_w"] / 2, HOLE_R + 0.6)]))
            out.append(_rooster(n + 4, p))
            n = len(out)
        if p["drive"] == "beat":
            sl = p["striker_len"] + 6
            # 芯の穴は下の端。上の端は番号の置き場にする。
            out.append(_strip(n + 1, "striker", "打ち木", 6, sl, fill=OUDO, holes=[(3, sl - 3, HOLE_R)]))
    elif shape == "disc":
        r = p["disc_d"] / 2
        top = _rings(r, [OUDO, USUCHA, OUDO, USUCHA, OUDO]) if look == "koma" else _rings(r, [SHU, GOFUN, AI])
        for i in range(int(p["disc_layers"])):
            # 見える面は上と下の 2 枚だけなので、間の紙には塗らない（刷る墨を減らし、のりで貼りやすくする）。
            art = top if i == 0 else ([_fill(_circle(r - 0.4), OUDO)] if i == int(p["disc_layers"]) - 1 else [])
            out.append(_disc(i + 1, f"disc{i + 1}", "円盤", r, [dict(a, pts=list(a["pts"])) for a in art]))
    elif shape == "cone":
        r = p["cone_r"]
        lid_top = _rings(r, [GOFUN, USUCHA, GOFUN, USUCHA]) if look == "oyama" else _rings(r, [TAISHA, SHU, TAISHA])
        for i in range(int(p["lid_layers"])):
            out.append(_disc(i + 1, f"lid{i + 1}", "ふた", r, [dict(a, pts=list(a["pts"])) for a in lid_top] if i == 0 else []))
        n = len(out)
        for i in range(int(p["cone_pieces"])):
            out.append(_cone_piece(n + 1 + i, f"cone{i + 1}", p, look))
        if p["knob_h"]:
            out.append(_strip(len(out) + 1, "knob", "つまみ", 60, p["knob_h"], fill=TAISHA, glue_at_end=8))
    else:
        r = p["disc_d"] / 2
        face = [_fill(_circle(r - 0.3), OUDO, sw=0.4), _fill(_circle(r * 0.35), USUCHA)]
        for i in range(2 * int(p["disc_layers"])):
            # 外に見える 2 枚だけに絵を置く（1 枚目と最後）。
            art = [dict(a, pts=list(a["pts"])) for a in face] if i in (0, 2 * int(p["disc_layers"]) - 1) else []
            out.append(_disc(i + 1, f"disc{i + 1}", "円盤", r, art))
        # 芯の帯は幅を 2 倍に刷り、長い辺で半分に折る。細い帯は 1 枚では巻く時によれ、番号も入らないため。
        # 折る線は 2 色の境に置く（決定 d）。
        w, hw, g = p["hub_strip"], p["hub_w"], 6
        hub = Part(len(out) + 1, "hub", "芯の帯", [(0, 0), (w, 0), (w, 2 * hw), (0, 2 * hw)], label_xy=(1, hw - 1.75), label=str(len(out) + 1),
                   art=[_fill(box(0.2, 0.2, w - g - 0.2, hw - 0.2), USUCHA), _fill(box(0.2, hw + 0.2, w - g - 0.2, 2 * hw - 0.2), OUDO)],
                   glue=[[(w - g, 0), (w, 0), (w, 2 * hw), (w - g, 2 * hw)]], valley=[((0, hw), (w, hw))], hide_folds=True)
        out.append(hub)
        if p["drive"] == "handle":
            # 柄はコマ 25 のへら形の板に倣い、上の端の穴に芯を通す片持ちにした。2 つ折りにして硬くし、折る線は 2 色の境に置く（決定 d）。
            hw, L = HANDLE_W, HANDLE_L
            out.append(Part(len(out) + 1, "handle", "柄", [(0, 0), (2 * hw, 0), (2 * hw, L), (0, L)], label_xy=(1, 12), label=str(len(out) + 1),
                            art=[_fill(box(0.2, 0.2, hw - 0.2, L - 0.2), OUDO), _fill(box(hw + 0.2, 0.2, 2 * hw - 0.2, L - 0.2), USUCHA)],
                            valley=[((hw, 0), (hw, L))], holes=[(hw / 2, 6, HOLE_R + 0.3), (1.5 * hw, 6, HOLE_R + 0.3)], hide_folds=True))
    return out


def place(by_key, page, top, gap):
    """部品を左から並べ、入らなければ次の段へ送る（棚の詰め方）。文字は部品の段の下に頁の幅で置く。

    雛形によって部品の数と大きさが大きく違う（羽の車 1 枚から円盤 8 枚まで）ので、決め打ちの配置にしない。
    """
    x, y, row_h = page.x0, top, 0.0
    for q in by_key.values():
        if x > page.x0 and x + q.width > page.x1:
            x, y, row_h = page.x0, y + row_h + gap, 0.0
        q.x, q.y = x, y
        x += q.width + gap
        row_h = max(row_h, q.height)
    return y + row_h + gap, page.x1 - page.x0, page.x0


def bom(p):
    paper = paper_name(p["paper_gsm"])
    why = "家庭のプリンタで刷って作るため"
    shape = p["shape"]
    rows = []
    if shape == "pinwheel":
        rows.append({"number": 1, "key": "wheel", "name": "羽の車", "qty": int(p["wheels"]), "material": paper, "substituted": True,
                     "original_guess": "細い竹の棒の先に紙を貼った物（図の見た目による）", "reason": why})
        rows.append({"number": 7, "key": "axle", "name": "車の芯", "qty": 1, "material": "つまようじか竹ひご（短く切る）", "substituted": True, "original_guess": "不明", "reason": "家にあり、穴に通しやすいため"})
        rows.append({"number": 8, "key": "stick", "name": "柄", "qty": 1, "material": "竹ひごか割り箸（長さ 25cm 前後）", "substituted": True, "original_guess": "竹の棒（図の見た目による）", "reason": "家にあるため"})
        rows.append({"number": 9, "key": "bead", "name": "車の間に挟む玉", "qty": 2, "material": "ビーズ（穴に芯が通る物）", "substituted": True, "original_guess": "不明", "reason": "車が柄にこすれて止まらないため"})
        if p["look"] == "kanko":
            rows.append({"number": 2, "key": "drum", "name": "太鼓と鶏", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明", "reason": why})
    elif shape in ("disc", "cone"):
        rows.append({"number": 1, "key": "body", "name": "円盤" if shape == "disc" else "ふたと胴", "qty": 1, "material": paper, "substituted": True,
                     "original_guess": "木（図の木目と色による）", "reason": why})
        rows.append({"number": 7, "key": "axis", "name": "芯", "qty": 1, "material": f"{'つまようじ' if p['axis_len'] <= 65 else '竹ひご'}（長さ約 {p['axis_len']:g}mm）", "substituted": True,
                     "original_guess": "木か竹の心棒（図の見た目による）", "reason": "家にあるため"})
    else:
        rows.append({"number": 1, "key": "disc", "name": "円盤と芯の帯", "qty": 1, "material": paper, "substituted": True, "original_guess": "木（図の見た目による）", "reason": why})
        rows.append({"number": 7, "key": "axis", "name": "芯", "qty": 1, "material": f"つまようじ（長さ約 {p['axis_len']:g}mm）", "substituted": True, "original_guess": "不明", "reason": "家にあるため"})
        if p["drive"] == "handle":
            rows.append({"number": 9, "key": "bead", "name": "芯の止めの玉", "qty": 1, "material": "ビーズ（穴に芯が通る物）", "substituted": True, "original_guess": "不明", "reason": "芯が柄から抜けないため"})
    if p["drive"] in ("string", "yoyo", "handle"):
        length = p["string_len"] if shape == "yoyo" else round(p["string_turns"] * math.pi * AXIS_D + 250)
        rows.append({"number": 10, "key": "string", "name": "紐", "qty": 1, "material": f"糸（長さ約 {length / 10:.0f}cm）", "substituted": True, "original_guess": "紐（図の見た目による）", "reason": "家にあるため"})
    return rows


def materials(p):
    rows = bom(p)
    return [f"{rows[0]['material']}を 1 枚", "のり、はさみ、テープ、定規"] + [r["material"] for r in rows[1:] if r["material"] != rows[0]["material"]]


def steps(p):
    shape, drive = p["shape"], p["drive"]
    out = ["刷った物差しに定規を当て、10cm か確かめる", "部品を実線で切る。芯の穴はつまようじの先であける"]
    if shape == "pinwheel":
        out.append("中心の補強の丸を、羽の車の中心の両面に穴を合わせて貼る")
        if drive == "cup":
            out.append("羽を朱と黄土の境で、全部同じ向きに谷折りし、受け皿の形にする")
        else:
            out.append(f"羽の柄を指でつまみ、全部の羽を同じ向きに約 {p['blade_angle']:g}° ひねる")
        if p["look"] == "kanko":
            out += ["太鼓の胴を丸めて輪にし、糊代で貼る。2 枚の面で挟み、縁をテープで止める",
                    "鶏の糊代を谷折りし、太鼓の上に貼る。胴の穴に柄の上の端を差し込む",
                    f"柄の、太鼓の下から {p['drum_gap']:g}mm の所に穴をあけ、竹ひごの芯を通す",
                    "芯の両端に玉を通し、羽の車を貼る。2 つの車のひねりは同じ向きにそろえる"]
            if drive == "beat":
                out.append(f"打ち木の穴を芯に通して貼る。柄から玉 1 つ分離し、先が太鼓の縁に {p['striker_len'] - p['drum_gap']:g}mm かかるか見る")
        else:
            out.append("芯を羽の車の穴に通し、玉を挟んで柄の先に刺す。車が軽く回るか見る")
    elif shape == "disc":
        out += ["円盤を穴をそろえて重ね、のりで貼る。絵の面を上と下にする",
                f"つまようじを穴に通し、下に {p['axis_below']:g}mm 出してのりで止める"]
    elif shape == "cone":
        if int(p["cone_pieces"]) == 2:
            out.append("胴の 2 枚を、継ぎ目の糊代で互いに貼って円錐にする（糊代が向かい合う）")
        else:
            out.append("胴を丸め、継ぎ目の糊代で貼って円錐にする")
        out += ["ふたを穴をそろえて重ねて貼る", "胴の上の縁の歯を谷折りし、ふたの裏に貼る",
                f"つまようじをふたの穴から胴の先まで通し、先を {p['axis_below']:g}mm 出してのりで止める"]
        if p["knob_h"]:
            out.append("つまみの帯を、ふたの上の芯に巻いて貼る")
    else:
        out += ["円盤を半分ずつ、穴をそろえて重ねて貼る（2 組）", "芯の帯を色の境で半分に折り、つまようじに固く巻いて糊代で止める",
                "芯の両端に円盤の組を通し、芯の帯を挟んで貼る", "紐の端を芯の帯に結び、溝に巻く"]
        if drive == "handle":
            out.append("柄を色の境で半分に折って貼る。穴に芯の端を通し、反対の端に玉を付けて抜けないようにする")
    if drive == "string":
        out.append(f"紐を上の芯に {int(p['string_turns'])} 回巻き、端を持つ")
    return out


RESULTS = ("回った", "回らない", "わからない")


def measures(p):
    """回るかどうかの二択でなく、回り方を言葉か絵で予想する（U-25 の案 1 に倣う）。回した物は数でないので欄に残す。"""
    return {"predict": "どう回ると思いますか。どこから力が来ますか（言葉か絵で）",
            "rows": [[("回し方（息・走る・指・紐）", 40), ("回った長さ（秒）", 20)]]}


def diagram(x, y, w, h, p):
    """組んだ時の横からの姿。線と四角だけで、仕組みの答え（なぜ回るか）は描かない。"""
    shape, cx = p["shape"], x + w / 2
    if shape == "pinwheel":
        R = wheel_radius(p)
        s = min(w / (2.4 * R if int(p["wheels"]) == 1 else 2 * (p["wheel_offset"] + 10) + 10), h / (R + 70))
        ay = y + 8 + (p["drum_d"] if p["look"] == "kanko" else R) * s
        shapes = [{"kind": "line", "x1": cx, "y1": ay - 2, "x2": cx, "y2": y + h}]
        if p["look"] == "kanko":
            dt = ay - p["drum_gap"] * s
            shapes.append({"kind": "rect", "x": cx - p["drum_w"] * s / 2, "y": dt - p["drum_d"] * s, "w": p["drum_w"] * s, "h": p["drum_d"] * s})
            off = p["wheel_offset"] * s
            shapes.append({"kind": "line", "x1": cx - off, "y1": ay, "x2": cx + off, "y2": ay})
            for sx in (-off, off):
                shapes.append({"kind": "line", "x1": cx + sx, "y1": ay - min(R * s, ay - y - 1), "x2": cx + sx, "y2": ay + R * s})
            if p["drive"] == "beat":
                shapes.append({"kind": "line", "x1": cx + 1.5, "y1": ay, "x2": cx + 1.5, "y2": ay - p["striker_len"] * s, "dash": "1,0.6"})
        else:
            shapes.append({"kind": "line", "x1": cx, "y1": ay, "x2": cx + 6, "y2": ay})
            shapes.append({"kind": "line", "x1": cx + 6, "y1": ay - R * s, "x2": cx + 6, "y2": ay + R * s})
        return shapes
    if shape in ("disc", "cone"):
        r = p["disc_d"] / 2 if shape == "disc" else p["cone_r"]
        s = min(w / (2 * r + 6), h / (p["axis_len"] + 6))
        base = y + 3 + p["axis_len"] * s
        tip = base - p["axis_below"] * s
        shapes = [{"kind": "line", "x1": cx, "y1": y + 3, "x2": cx, "y2": base}]
        if shape == "disc":
            th = max(stack(p) * s, 0.8)
            shapes.append({"kind": "rect", "x": cx - r * s, "y": tip - th, "w": 2 * r * s, "h": th})
        else:
            top = tip - p["cone_h"] * s
            shapes += [{"kind": "line", "x1": cx - r * s, "y1": top, "x2": cx, "y2": tip}, {"kind": "line", "x1": cx + r * s, "y1": top, "x2": cx, "y2": tip},
                       {"kind": "rect", "x": cx - r * s, "y": top - max(stack(p) * s, 0.8), "w": 2 * r * s, "h": max(stack(p) * s, 0.8)}]
        return shapes
    r = p["disc_d"] / 2
    s = min(w / (2 * r + 10), h / (2 * r + 30))
    cy = y + h - r * s - 3
    shapes = [{"kind": "rect", "x": cx - (p["hub_w"] / 2 + 1) * s - 1, "y": cy - r * s, "w": 1, "h": 2 * r * s},
              {"kind": "rect", "x": cx + (p["hub_w"] / 2 + 1) * s, "y": cy - r * s, "w": 1, "h": 2 * r * s},
              {"kind": "line", "x1": cx, "y1": cy - hub_d(p) / 2 * s, "x2": cx, "y2": y + 2, "dash": "1,0.6"}]
    if p["drive"] == "handle":
        shapes.append({"kind": "rect", "x": cx - (p["hub_w"] / 2 + 4) * s - 1, "y": cy - 3, "w": 1, "h": h - (cy - y) + 2 - 3})
    return shapes
