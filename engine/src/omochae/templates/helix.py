"""雛形 helix: DNA の二重らせん（B 形・右巻き）の紙の模型。江戸の玩具でない、内部構造を持つ機構の模型の試作（制作者の指示 2026-11-07
「何個かつくってみてよ。」）。

形の比は、B 形 DNA の値に合わせる（出典の記録 data/sources/SCI-DNA-B.json）:
- 1 回りの塩基対 10.5（測った値 10.4 と 10.6 の間）。1 つ上の塩基対は、上から見て左回り（反時計回り）に 360° / 10.5 ≈ 34.3° 回る（右巻き）。
- 1 段の高さ 0.34nm、らせんの直径 約 2nm。紙の模型では、背骨の半径 R に合わせて 1 段の高さを 2R × 0.34 / 2.0 にする。
- 2 本の背骨は逆向き（5' → 3' が逆）。

仕組み（紙の作り）:
- 塩基対の板（V の字）: 竹串を通す穴を要に、2 本の腕が 140° 開く（小さい溝の側。見せるための見込みで、原子の位置から測った値ではない）。
  腕の先の糊代を立て、背骨の帯を貼る。腕の色は塩基（A と T、G と C が向かい合う）。
- 間の筒: 竹串に巻いて作る紙の筒で、板と板の間の高さ（1 段）を決める。
- 背骨の帯 2 本: 印の間の長さを、らせんの上の隣の塩基対の間の長さ（弦 2R·sin(34.3°/2) と 1 段の高さの斜めの長さ）にする。
  板は竹串のまわりに自由に回るので、帯を印のとおりに貼ると、1 段に 34.3° のねじれが決まる（巻く向きは手順で左回りと言う）。
どれも紙で組んで確かめていない。らせんの比を見るための模型で、原子の形や動きそのものではない。
"""
import math

from shapely.geometry import Point, Polygon, box
from shapely.affinity import rotate
from shapely.ops import unary_union

from ..model import Failure, Part
from ..paper_words import paper_name
from ..textfit import text_width

ID = "helix"
DEFAULTS = {
    "kind": "bdna",
    "n_bp": 11,           # 塩基対の板の数（1 回り 10.5 を少し越える）
    "radius": 25,         # 背骨の半径 mm（要から腕の先の折り線まで）
    "skewer_d": 3.0,      # 竹串の太さ mm
    "skewer_len": 180,    # 竹串の長さ mm
    "clay_g": 20,         # 台の油粘土 g
    "paper_gsm": 150,
}
RANGES = {
    "n_bp": (6, 12), "radius": (18, 30), "skewer_d": (2.0, 4.0), "skewer_len": (120, 250),
    "clay_g": (10, 60), "paper_gsm": (110, 220),
}
KINDS = ("bdna",)
FORM = "kind"
FORMS = KINDS
SOURCE = "SCI-DNA-B"
TITLES = {"bdna": "二重らせん・B 形・右巻き"}

# B 形 DNA の値（出典の記録）。比だけを使い、模型の大きさは背骨の半径で決める
BP_PER_TURN = 10.5
RISE_NM, DIAMETER_NM = 0.34, 2.0
TWIST = 360.0 / BP_PER_TURN  # 1 段のねじれ（度）。上から見て左回りが正（右巻き）
MINOR_DEG = 140.0  # 2 本の腕の間の角（小さい溝の側）。見せるための見込み
ARM_W = 7.0      # 腕の幅 mm
TAB = 5.0        # 腕の先の糊代（立てて背骨の帯を貼る）mm
HUB_R = 5.0      # 要のまわりの丸の半径 mm（穴のまわりの紙）
HOLE_CLEAR = 0.3  # 竹串と穴のすき間 mm
PLATE_T = 0.2    # 板の紙の厚さの見込み mm（間の筒の長さから引く）
WRAPS = 3        # 間の筒を竹串に巻く回数（外の太さが板の穴より太くなり、板が筒に乗る）
SPACER_GLUE = 6.0
STRAND_W = 8.0   # 背骨の帯の幅 mm
STRAND_END = 10.0  # 背骨の帯の両端の余り mm（端の 5'・3' の字と、いちばん端の印の番号が重ならない長さ）
CLAY_DEPTH = 15.0  # 竹串を台の粘土に刺す深さの見込み mm
TOP_MARGIN = 5.0
SEQUENCE = "ATGCGTACGATC"  # 板の塩基（1 の板から）。向かいは相補（A–T・G–C）
PAIR = {"A": "T", "T": "A", "G": "C", "C": "G"}
NAMES = {"A": "アデニン", "T": "チミン", "G": "グアニン", "C": "シトシン"}
COLORS = {"A": "#f08a8a", "T": "#8ab4f0", "G": "#8fd18f", "C": "#f5cf7a"}
STRAND_FILL = "#e3e0ec"
LABEL_SIZE = 2.8  # 札の字の大きさ（compose.LABEL_SIZE と同じ。雛形から compose を読むと読み込みの輪になるので、値を写す）
LABEL_LINE = 1.25


def title(p):
    return TITLES[p["kind"]]


def spec():
    return {"template_id": ID, "defaults": DEFAULTS, "ranges": RANGES, "kind": KINDS}


def check_range(p):
    out = []
    for k, v in p.items():
        if k == "kind":
            if v not in KINDS:
                out.append(Failure("F5.range", k, f"{v} は {KINDS} のどれでもない"))
        elif k not in RANGES:
            out.append(Failure("F5.range", k, "知らない寸法の名前"))
        elif not isinstance(v, (int, float)) or isinstance(v, bool) or not RANGES[k][0] <= v <= RANGES[k][1]:
            out.append(Failure("F5.range", k, f"{v} は範囲 {RANGES[k]} の外"))
    if isinstance(p.get("n_bp"), float) and not p["n_bp"].is_integer():
        out.append(Failure("F5.range", "n_bp", "塩基対の数は整数"))
    return out


def rise(p):
    """1 段の高さ mm（背骨の直径に、B 形の 1 段 ÷ 直径の比を掛ける）。"""
    return 2 * p["radius"] * RISE_NM / DIAMETER_NM


def segment(p):
    """背骨の帯の、隣の塩基対の間の長さ mm（弦と 1 段の高さの斜め）。"""
    chord = 2 * p["radius"] * math.sin(math.radians(TWIST) / 2)
    return math.hypot(chord, rise(p))


def stack_height(p):
    """竹串に要る長さ mm（板と筒を積んだ高さ・粘土に刺す深さ・上の余り）。
    積むのは板 n 枚と間の筒 n − 1 本で、筒の長さは 1 段から板の厚さを引いた物なので、積んだ高さは (n − 1)·1 段 ＋ 板の厚さ
    （見直しの指摘: 前は n·1 段と 1 段分多く数え、収まる竹串を断っていた）。"""
    return (int(p["n_bp"]) - 1) * rise(p) + PLATE_T + CLAY_DEPTH + TOP_MARGIN


def check_physics(p):
    out = []
    need = stack_height(p)
    if need > p["skewer_len"]:
        # 寸法の組み合わせの範囲の外（竹串の長さに、板と筒が積めない）。新しい床は作らず、範囲の床で言う
        out.append(Failure("F5.range", "竹串", f"板 {int(p['n_bp'])} 枚と間の筒を積むと {need:.0f}mm で、竹串 {p['skewer_len']}mm に入らない"))
    return out


def _letter(i):
    """部品の key の通し番号の字（a, b, c…）。key は英小文字だけ（折れる様子の書き出しが、前の回の SVG を key の名で選ぶため）。"""
    return chr(ord("a") + i)


def _arm_dir(deg):
    return (math.cos(math.radians(deg)), math.sin(math.radians(deg)))


# 板の腕の向き（頁の座標。y は下）。V の字は上へ開き、腕の間は MINOR_DEG
ARM_A_DEG = -(90.0 - MINOR_DEG / 2)
ARM_B_DEG = -(90.0 + MINOR_DEG / 2)


def _arm_rect(deg, length):
    """要から deg の向きへ length 伸びる幅 ARM_W の腕（要の後ろにも ARM_W/2 だけ出す）。"""
    r = box(-ARM_W / 2, -ARM_W / 2, length, ARM_W / 2)
    return rotate(r, deg, origin=(0, 0), use_radians=False)


def _plate(i, p):
    R = p["radius"]
    hole_r = p["skewer_d"] / 2 + HOLE_CLEAR
    shape = unary_union([_arm_rect(ARM_A_DEG, R + TAB), _arm_rect(ARM_B_DEG, R + TAB), Point(0, 0).buffer(HUB_R, 48)])
    outline = [(round(x, 4), round(y, 4)) for x, y in shape.exterior.coords[:-1]]
    valley, glue, art, lines = [], [], [], []
    base = SEQUENCE[i]
    for deg, b in ((ARM_A_DEG, base), (ARM_B_DEG, PAIR[base])):
        (dx, dy), (nx, ny) = _arm_dir(deg), _arm_dir(deg + 90)
        h = ARM_W / 2
        f0 = (R * dx + h * nx, R * dy + h * ny)
        f1 = (R * dx - h * nx, R * dy - h * ny)
        # 腕の先の糊代は、刷った面の側へ立てる（谷折り）。立てた面に背骨の帯を貼る
        valley.append((tuple(round(v, 4) for v in f0), tuple(round(v, 4) for v in f1)))
        e0 = ((R + TAB) * dx + h * nx, (R + TAB) * dy + h * ny)
        e1 = ((R + TAB) * dx - h * nx, (R + TAB) * dy - h * ny)
        glue.append([tuple(round(v, 4) for v in q) for q in (f0, e0, e1, f1)])
        # 腕の色（塩基）。要の穴と折り線にかからないよう、内と外を空ける
        r0, r1, hh = hole_r + 1.5, R - 0.4, h - 0.2
        art.append({"kind": "poly", "fill": COLORS[b],
                    "pts": [(round(r * dx + s * hh * nx, 4), round(r * dy + s * hh * ny, 4)) for r, s in ((r0, 1), (r1, 1), (r1, -1), (r0, -1))]})
        # 札: 腕の真ん中に塩基の字。A の腕には板の番号も
        text = f"{i + 1} {b}" if deg == ARM_A_DEG else b
        c = (R * 0.55 * dx, R * 0.55 * dy)
        tw = text_width(text, LABEL_SIZE)
        lines.append((text, round(c[0] - tw / 2, 4), round(c[1] - LABEL_SIZE * LABEL_LINE / 2, 4)))
    return Part(i + 1, f"plate{_letter(i)}", "塩基対の板", outline, label_xy=lines[0][1:], label=f"{i + 1} {base}", label_lines=lines,
                valley=valley, glue=glue, holes=[(0.0, 0.0, round(hole_r, 4))], art=art)


def _strand(k, p, number):
    """背骨の帯。印は塩基対の板の腕の先に貼る所で、印の間は segment。上の端が 5'（2 本とも同じに刷り、貼る向きを手順で言う）。"""
    n = int(p["n_bp"])
    seg = segment(p)
    length = (n - 1) * seg + 2 * STRAND_END
    outline = [(0.0, 0.0), (STRAND_W, 0.0), (STRAND_W, round(length, 4)), (0.0, round(length, 4))]
    art = [{"kind": "poly", "fill": STRAND_FILL, "pts": [(0.2, 0.2), (STRAND_W - 0.2, 0.2), (STRAND_W - 0.2, length - 0.2), (0.2, length - 0.2)]}]
    # 上の端に部品の番号（手順の文が番号で呼ぶ）と 5'、下の端に 3'。帯は幅 8mm で名が入らないので、番号だけを刷る
    lines = [(str(number), 1.0, 0.6), ("5'", 1.0, 0.6 + LABEL_SIZE * LABEL_LINE + 0.4), ("3'", 1.0, round(length - LABEL_SIZE * LABEL_LINE - 0.6, 4))]
    for j in range(n):
        y = STRAND_END + j * seg
        art.append({"kind": "mark", "pts": [(0.6, round(y, 4)), (STRAND_W - 0.6, round(y, 4))], "mark": "attach"})
        plate = j + 1 if k == 1 else n - j  # 背骨 1 は下の板から、背骨 2 は上の板から
        lines.append((str(plate), 1.0, round(y + 0.6, 4)))
    return Part(number, f"back{_letter(k - 1)}", f"背骨 {k}", outline, label_xy=(1.0, 0.6), label=f"{number} 背骨 {k}", label_lines=lines, art=art)


def _spacer(j, p, number):
    h = rise(p) - PLATE_T
    w = math.pi * (p["skewer_d"] + 2 * HOLE_CLEAR) * WRAPS + SPACER_GLUE
    outline = [(0.0, 0.0), (round(w, 4), 0.0), (round(w, 4), round(h, 4)), (0.0, round(h, 4))]
    glue = [[(round(w - SPACER_GLUE, 4), 0.0), (round(w, 4), 0.0), (round(w, 4), round(h, 4)), (round(w - SPACER_GLUE, 4), round(h, 4))]]
    return Part(number, f"spacer{_letter(j)}", "間の筒", outline, label_xy=(1.0, round((h - LABEL_SIZE * LABEL_LINE) / 2, 4)), label=str(number), glue=glue)


def parts(p):
    n = int(p["n_bp"])
    out = [_plate(i, p) for i in range(n)]
    out += [_strand(1, p, n + 1), _strand(2, p, n + 2)]
    out += [_spacer(j, p, n + 3 + j) for j in range(n - 1)]
    return out


def place(by_key, page, top, gap):
    """背骨の帯 2 本は右の端に縦に、板と間の筒は左の残りに上の段から並べ、文字は板と筒の下に置く。"""
    strands = [by_key["backa"], by_key["backb"]]
    x = page.x1
    for s in reversed(strands):
        x -= s.width
        s.x, s.y = x, top
        x -= gap
    right = x
    cx, cy, row = page.x0, top, 0.0
    keys = [k for k in by_key if k.startswith("plate")] + [k for k in by_key if k.startswith("spacer")]
    prev_kind = None
    for key in keys:
        q = by_key[key]
        kind = "plate" if key.startswith("plate") else "spacer"
        if prev_kind and kind != prev_kind:  # 板と筒の間で段を変える
            cx, cy, row = page.x0, cy + row + gap, 0.0
        prev_kind = kind
        if cx > page.x0 and cx + q.width > right:
            cx, cy, row = page.x0, cy + row + gap, 0.0
        q.x, q.y = cx - min(a for a, _ in q.outline), cy - min(b for _, b in q.outline)
        cx += q.width + gap
        row = max(row, q.height)
    return cy + row + gap, right - page.x0 - gap, page.x0


def bom(p):
    paper = paper_name(gsm=p["paper_gsm"])
    n = int(p["n_bp"])
    note = "無し（科学の模型。紙で形の比を見る）"
    rows = [{"number": i + 1, "key": f"plate{_letter(i)}", "name": "塩基対の板", "qty": 1, "material": paper, "substituted": False,
             "original_guess": note, "reason": "塩基の対を、腕の色と字で見せるため"} for i in range(n)]
    rows += [{"number": n + k, "key": f"back{_letter(k - 1)}", "name": f"背骨 {k}", "qty": 1, "material": paper, "substituted": False,
              "original_guess": note, "reason": "糖とリン酸の鎖を帯で見せ、印の間の長さでねじれを決めるため"} for k in (1, 2)]
    rows += [{"number": n + 3 + j, "key": f"spacer{_letter(j)}", "name": "間の筒", "qty": 1, "material": paper, "substituted": False,
              "original_guess": note, "reason": "板と板の間の高さ（1 段）を決めるため"} for j in range(n - 1)]
    rows += [{"number": 2 * n + 2, "key": "axis", "name": "軸", "qty": 1, "material": f"竹串（長さ約 {p['skewer_len']}mm・太さ約 {p['skewer_d']:g}mm）",
              "substituted": False, "original_guess": note, "reason": "らせんの真ん中の軸を見せ、板を通して積むため"},
             {"number": 2 * n + 3, "key": "stand", "name": "台", "qty": 1, "material": f"油粘土 {p['clay_g']:g}g",
              "substituted": False, "original_guess": note, "reason": "竹串を真っすぐ立てるため"}]
    return rows


def materials(p):
    by = {r["key"]: r for r in bom(p)}
    return [f"{by['platea']['material']}を 1 枚", "のり、はさみ、定規", f"{by['axis']['material']}を 1 本", f"台に{by['stand']['material']}",
            "板の腕の色と字は塩基: A（アデニン）と T（チミン）、G（グアニン）と C（シトシン）が向かい合う"]


def steps(p):
    n = int(p["n_bp"])
    return [
        "刷った物差しに定規を当て、10cm か確かめる",
        "部品を実線で切る。板の要の小さい穴は竹串の先であける",
        f"{n + 3}〜{2 * n + 1} の間の筒を、竹串に {WRAPS} 回巻いて端の糊代を貼り、竹串から抜く（{n - 1} 本）",
        f"1〜{n} の板の腕の先の糊代を、破線で谷折りして立てる",
        f"油粘土 {p['clay_g']:g}g を丸めて机に置き、竹串を真っすぐ立てて刺す",
        "竹串に、1 の板、間の筒、2 の板、間の筒…と番号の順に通して積む（刷った面を上に）",
        f"{n + 1} 背骨 1 の 5' の端の側の印 1 を、1 の板の右の腕の糊代に貼る。上から見て左回り（反時計回り）に巻きながら、"
        f"印 2・3…を、2・3…の板の右の腕の糊代に順に貼る（板は竹串のまわりに回して印に合わせる）",
        f"{n + 2} 背骨 2 の 5' の端の側の印 {n} を、{n} の板（いちばん上）の左の腕の糊代に貼り、下へ順に貼る（2 本の背骨は向きが逆）",
        "上から見ると、板は 1 段ごとに左回りに回って上がる（右巻き）。2 本の背骨の間に、広い溝と狭い溝が交互に見える",
    ]


RESULTS = ("らせんになった", "らせんにならない")
