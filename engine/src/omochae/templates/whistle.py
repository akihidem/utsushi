"""雛形 whistle: 息を吹くと鳴る・振ると鳴る、紙の鳴り物 3 つ（『江都二色』のコマ 9 左・24 右・27 左）。

刷る形（kind）で描き分ける。どれも、音が出る見込みのしくみ（紙の舌・閉じた管・中の玉。栓や玉に粘土、糸と竹串も使う。実物で鳴らしてはいない）に置き換えた翻案で、元の玩具の鳴らし方は図からは分からない。
- horn（コマ 9 左、既定の出典）: 継ぎのある柄の先に漏斗の形のラッパ。【解釈】柄を息の管、柄の端の円盤を口当て、継ぎの巻きを
  鳴りの所と読み、管の先に紙の舌（自由リード）を 2 枚の枠で挟み、その先に扇形から丸めたラッパを付ける。
- tube（コマ 24 右）: 角と羽の付いた黒い鬼の面を、切り欠きのある竹筒と曲がった柄に付けた物。【解釈】竹筒の口の切り欠きを
  尺八の歌口のような縁と読み、底を粘土で塞いだ閉管の笛にする。面の絵は別の部品（面）に刷る。
- rattle（コマ 27 左）: 2 本の竹筒を角度を付けて継ぎ、糸で鈴を下げた物。鈴は紙では鳴らないので、丸めた筒の両端を
  向きを変えてつまんで閉じた四面体の袋に粘土の玉を入れ、振ると玉が当たって鳴る物に置き換える。
寸法は手元の複写の図の比から出した見込みで、どの値も実物では未確認。Claude が変えてよいのは RANGES の名前の値だけ。

鳴るかの見込み（F5.sound）の前提。どれも実物の紙で確かめていない:
- 舌（horn）: 根元を挟んだ片持ちの薄い紙の帯とみて、1 次の固有振動数
  f = (1.875² / 2π) · (t / L²) · √(E / 12ρ) を自由リードの鳴る高さとする（空気の重さと減衰は入れない）。
  紙の E = 3 GPa・ρ = 750 kg/m³ は、ふつうのコピー用紙の文献の幅（E 2〜6 GPa）の中の見込み。
  鳴る窓は 150〜3000Hz（低いと紙が重く揺れ始めない・高いと短すぎて手で切れない、の見込み）。
  板でなく梁として曲がるよう、自由長は幅の 1.5 倍以上。舌のまわりの窓は管の内に収まり、根元を 2mm 以上挟む。
- ラッパ（horn）: 扇形の外の弧の長さ ＝ 口の円周 π·D（D は紙の厚みの真ん中で測った口の径）。弧に糊代の帯を足して丸める。
  半頂角が 8° より細いと筒、45° より開くと皿で、ラッパの形にならないと見る（音を大きくする効きは測っていない）。
- 筒の笛（tube）: 底を塞いだ閉管は f ≈ c / 4(L + 0.3d)（c = 343 m/s、開いた口の端の補正を 0.3d とする）。
  鳴る窓は 200〜4000Hz。管として鳴るよう、塞いだ後の長さは径の 4 倍以上。歌口の切り欠きは、幅が径の 0.25〜0.6・
  深さが径の 0.1〜0.4（縦笛の歌口の比の見込み）。
- 鈴（rattle）: 周 C・高さ H の筒の両端を糊代 e で向きを変えてつまむと、向かい合う 2 辺が a = C/2・その間 h = H − 2e の四面体になる。
  内接球の半径 r = a·h / (4·√(a²/4 + h²))。玉の径が 2r の 0.7 倍までなら中で転がって当たると見る。
"""
import math

from shapely.geometry import Polygon, box
from shapely.ops import unary_union

from ..paper_words import paper_name  # 紙の書き方は 4 つの名前だけ（制作者の指示 2026-11-05）
from ..model import Failure, Part

ID = "whistle"
DEFAULTS = {
    "kind": "horn",
    # 0.15mm はふつうの厚めの紙の見込み。舌だけは薄い紙（0.09mm はコピー用紙の見込み）に写して切る。
    "paper_thickness": 0.15, "glue": 5,
    # ラッパ（コマ 9 左）。口の径に対して長さ 0.75 倍・柄は口の径の 2 倍弱に見える（斜めの図を目測）。
    "horn_mouth_d": 60, "horn_length": 45, "pipe_d": 12, "pipe_length": 110, "lip_d": 22, "collar_w": 8,
    "reed_length": 8, "reed_width": 4, "reed_gap": 0.5, "reed_thickness": 0.09,
    # 筒の笛（コマ 24 右）。面の幅は筒の径の 4 倍強にした（図ではもっと大きいが、A4 に筒と並べるため縮めた）。
    "tube_d": 16, "tube_length": 150, "notch_width": 6, "notch_depth": 4, "plug_depth": 8, "mask_w": 70, "handle_length": 90,
    # 鳴り物（コマ 27 左）。竹筒 2 本の長さの比は図の目測。
    "bone_d": 10, "bone_a": 110, "bone_b": 90, "bell_d": 18, "bell_height": 30, "bead_d": 6, "cord_length": 120,
}
RANGES = {
    "paper_thickness": (0.05, 0.5), "glue": (3, 10),
    "horn_mouth_d": (30, 90), "horn_length": (20, 80), "pipe_d": (6, 20), "pipe_length": (40, 185), "lip_d": (10, 40), "collar_w": (4, 15),
    "reed_length": (3, 30), "reed_width": (2, 15), "reed_gap": (0.2, 1.5), "reed_thickness": (0.03, 0.3),
    # 長さの上限 185 は、筒を横に 1 本で A4 の印字域の幅 190mm に入れるため。
    "tube_d": (8, 30), "tube_length": (40, 185), "notch_width": (1, 15), "notch_depth": (1, 15), "plug_depth": (3, 20),
    "mask_w": (40, 120), "handle_length": (40, 150),
    "bone_d": (6, 20), "bone_a": (40, 185), "bone_b": (40, 185), "bell_d": (10, 30), "bell_height": (12, 50), "bead_d": (3, 14),
    "cord_length": (60, 300),
}
KINDS = ("horn", "tube", "rattle")
# 刷る形を決める寸法（どの鳴り物か）。どれが「正しい」かは無いので、寸法を直に渡す入口では必ず書かせる。
FORM = "kind"
FORMS = KINDS
# 既定の出典（data/sources/ の名前）。--source を書かない時に、雛形と合わない出典の印を刷らないため。
SOURCE = "NDL-1187053-R0000009-L-whistle"
SOURCES = {"horn": SOURCE, "tube": "NDL-1187053-R0000024-R-whistle", "rattle": "NDL-1187053-R0000027-L-whistle"}
TITLES = {"horn": "紙の舌で鳴るラッパ", "tube": "鬼の面の竹笛", "rattle": "竹の鳴り物と玉の鈴"}

# 鳴るかの見込みの数（前提は module の docstring）。
E_PAPER, RHO_PAPER = 3.0e9, 750.0
BEAM_K = 1.875104 ** 2 / (2 * math.pi)
REED_HZ = (150, 3000)
REED_ASPECT = 1.5
ROOT_MIN = 2.0  # 舌の根元を枠で挟む長さの下限。これより短いと根元ごと揺れて鳴らない見込み
BORE_MARGIN = 0.5  # 窓の角から管の内の縁まで。糊がはみ出しても窓を塞がない余裕
REED_RIM = 1.0  # 枠の円盤を管の外より大きくする幅。管の端を貼る所
HORN_ALPHA = (8, 45)
C_AIR = 343.0
END_CORR = 0.3
PIPE_HZ = (200, 4000)
PIPE_LD = 4
NOTCH_W, NOTCH_D = (0.25, 0.6), (0.1, 0.4)
RATTLE_FREE = 0.7
BELL_SEAL = 5  # 鈴の上下をつまんで貼る糊代の幅
HANDLE_W, HANDLE_GLUE = 6, 10  # 曲がった柄の帯の幅と、両端を筒に貼る長さ
JOINT_W, JOINT_TAIL = 8, 12  # 継ぎの帯の幅と、竹筒 B に貼る尾の長さ

IVORY, INK, BAMBOO, BAMBOO_DARK, HORN, HORN_RIM, MASK, TEETH, FEATHER, BELL, CORD = (
    "#e8dcb8", "#2f2d29", "#d8c48e", "#8f7440", "#dcc387", "#a88a4f", "#34312c", "#e6dcc0", "#6d675c", "#c4a96a", "#5b4a33")
# 床の式が頼る位置（粘土を詰める深さ・舌の根元を挟む境）の印の色。節の筋と見分けられるよう、絵の色に無い赤茶にする。
MARK = "#9b3b2a"


def title(p):
    return TITLES[p["kind"]]


def spec():
    return {"template_id": ID, "defaults": DEFAULTS, "ranges": RANGES, "kind": KINDS, "sources": SOURCES}


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
    return out


# ---- 式（型紙と試験が同じ式を使う） ----

def wrap_circ(d, t):
    """芯（径 d）に 1 周巻いた紙の、厚みの真ん中の周。帯の幅はこれに糊代を足す。"""
    return math.pi * (d + t)


def reed_hz(p):
    """舌の 1 次の固有振動数（Hz）。片持ちの梁の式。mm を m に直して計算する。"""
    t, L = p["reed_thickness"] / 1000, p["reed_length"] / 1000
    return BEAM_K * t / (L * L) * math.sqrt(E_PAPER / (12 * RHO_PAPER))


def reed_disc_r(p):
    """枠の円盤の半径。管（芯の径 pipe_d・紙 1 枚）の外より REED_RIM だけ大きくし、管の端を貼る縁を残す。"""
    return p["pipe_d"] / 2 + p["paper_thickness"] + REED_RIM


def reed_window(p):
    """枠の窓の大きさ（舌の向きの長さ, 幅）。舌の先と両脇に reed_gap の隙間を空ける。"""
    return p["reed_length"] + p["reed_gap"], p["reed_width"] + 2 * p["reed_gap"]


def reed_root(p):
    """舌の根元を挟む長さ。窓を円盤の真ん中に置くので、窓の端から円盤の縁まで。"""
    return reed_disc_r(p) - reed_window(p)[0] / 2


def horn_cone(p):
    """ラッパの半頂角（度）と扇形の内外の半径・角度（ラジアン）。小さい口は枠の円盤の径に合わせる（継ぎの巻きで束ねる）。"""
    D, d, h = p["horn_mouth_d"], 2 * reed_disc_r(p), p["horn_length"]
    a = math.atan2((D - d) / 2, h)
    s1, s0 = D / 2 / math.sin(a), d / 2 / math.sin(a)
    return math.degrees(a), s0, s1, 2 * math.pi * math.sin(a)


def tube_hz(p):
    """閉管の笛の高さ。底を塞いだ粘土の分だけ管は短くなる。"""
    L = (p["tube_length"] - p["plug_depth"]) / 1000
    return C_AIR / (4 * (L + END_CORR * p["tube_d"] / 1000))


def bell_inradius(p):
    """鈴の四面体の内接球の半径（mm）。式は module の docstring。"""
    a = wrap_circ(p["bell_d"], p["paper_thickness"]) / 2
    h = p["bell_height"] - 2 * BELL_SEAL
    if h <= 0:
        return 0.0
    return a * h / (4 * math.sqrt(a * a / 4 + h * h))


def check_physics(p):
    """F5.sound: 刷る形ごとに、鳴るしくみが成り立つ寸法かを見る。式の前提は module の docstring。"""
    out = []
    k = p["kind"]
    if k == "horn":
        f = reed_hz(p)
        if not REED_HZ[0] <= f <= REED_HZ[1]:
            out.append(Failure("F5.sound", "舌", f"舌の固有振動数 {f:.0f}Hz は鳴る窓 {REED_HZ[0]}〜{REED_HZ[1]}Hz の外（長さ・厚みを変える）"))
        if p["reed_length"] < REED_ASPECT * p["reed_width"]:
            out.append(Failure("F5.sound", "舌", f"舌の自由長 {p['reed_length']:g}mm が幅の {REED_ASPECT} 倍に足りず、板のように揺れて鳴りにくい"))
        wl, ww = reed_window(p)
        corner = math.hypot(wl / 2, ww / 2)
        if corner > p["pipe_d"] / 2 - BORE_MARGIN:
            out.append(Failure("F5.sound", "舌", f"窓の角が管の中心から {corner:.1f}mm で、管の内（{p['pipe_d'] / 2 - BORE_MARGIN:.1f}mm まで）に収まらない"))
        if reed_root(p) < ROOT_MIN:
            out.append(Failure("F5.sound", "舌", f"舌の根元を挟む長さが {reed_root(p):.1f}mm で、{ROOT_MIN:g}mm に足りない"))
        a = horn_cone(p)[0]
        if not HORN_ALPHA[0] <= a <= HORN_ALPHA[1]:
            out.append(Failure("F5.sound", "ラッパ", f"ラッパの半頂角 {a:.0f}° は {HORN_ALPHA[0]}〜{HORN_ALPHA[1]}° の外で、ラッパの形にならない"))
        if p["lip_d"] < p["pipe_d"] + 2 * p["paper_thickness"] + 4:
            out.append(Failure("F5.sound", "口当て", "口当ての円盤が管より 4mm 以上大きくなく、唇が当たらない"))
    elif k == "tube":
        d, L = p["tube_d"], p["tube_length"] - p["plug_depth"]
        f = tube_hz(p)
        if not PIPE_HZ[0] <= f <= PIPE_HZ[1]:
            out.append(Failure("F5.sound", "筒", f"閉管の高さ {f:.0f}Hz は {PIPE_HZ[0]}〜{PIPE_HZ[1]}Hz の外"))
        if L < PIPE_LD * d:
            out.append(Failure("F5.sound", "筒", f"塞いだ後の長さ {L:g}mm が径の {PIPE_LD} 倍（{PIPE_LD * d:g}mm）に足りず、管として鳴らない"))
        if not NOTCH_W[0] * d <= p["notch_width"] <= NOTCH_W[1] * d:
            out.append(Failure("F5.sound", "歌口", f"切り欠きの幅 {p['notch_width']:g}mm は径の {NOTCH_W[0]}〜{NOTCH_W[1]} 倍（{NOTCH_W[0] * d:.1f}〜{NOTCH_W[1] * d:.1f}mm）の外"))
        if not NOTCH_D[0] * d <= p["notch_depth"] <= NOTCH_D[1] * d:
            out.append(Failure("F5.sound", "歌口", f"切り欠きの深さ {p['notch_depth']:g}mm は径の {NOTCH_D[0]}〜{NOTCH_D[1]} 倍（{NOTCH_D[0] * d:.1f}〜{NOTCH_D[1] * d:.1f}mm）の外"))
    else:
        r = bell_inradius(p)
        free = RATTLE_FREE * 2 * r
        if p["bead_d"] > free:
            out.append(Failure("F5.sound", "鈴", f"玉 {p['bead_d']:g}mm は鈴の中（内接球の径 {2 * r:.1f}mm の {RATTLE_FREE} 倍 = {free:.1f}mm まで）で転がらない"))
    return out


# ---- 部品 ----

def _arc(r, a0, a1, n):
    """扇形の弧。角度は下向き（+y）から測る。ラッパの口が下、要（かなめ）が上に来る。"""
    return [(r * math.sin(a0 + (a1 - a0) * i / n), r * math.cos(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]


def _norm(part):
    """部品の外形の左上を原点に寄せる（place と検査が部品の左上を原点にした座標を前提にするため）。"""
    xs = [x for x, _ in part.outline]
    ys = [y for _, y in part.outline]
    dx, dy = -min(xs), -min(ys)
    mv = lambda ps: [(x + dx, y + dy) for x, y in ps]
    part.outline = mv(part.outline)
    part.glue = [mv(g) for g in part.glue]
    part.valley = [tuple(mv(list(ln))) for ln in part.valley]
    part.art = [dict(a, pts=mv(a["pts"])) for a in part.art]
    part.holes = [(x + dx, y + dy, r) for x, y, r in part.holes]
    part.cuts = [(x + dx, y + dy, w, h) for x, y, w, h in part.cuts]
    part.label_xy = (part.label_xy[0] + dx, part.label_xy[1] + dy)
    return part


def horn_outer_arc(part):
    """刷ったラッパの外の弧（糊代の帯を除く）の長さ。試験が式（π·D）と比べる。"""
    pts = part.outline[:ARC_N + 1]
    return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))


ARC_N = 96


def _horn(p):
    _, s0, s1, th = horn_cone(p)
    g = p["glue"]
    a0, a1 = -th / 2, th / 2
    outer, inner = _arc(s1, a0, a1, ARC_N), _arc(s0, a1, a0, ARC_N)
    p1, p0 = outer[-1], inner[0]
    # 糊代は右の直線の辺に平行な帯にする。要に向かって細る帯だと、要の近くで糊代が 1mm を切って貼れない。
    n = (math.cos(a1), -math.sin(a1))
    tab = [(p1[0] + g * n[0], p1[1] + g * n[1]), (p0[0] + g * n[0], p0[1] + g * n[1])]
    part = Part(1, "horn", "ラッパ", outer + tab + inner, label_xy=(-4, s0 + 4), label="1 ラッパ")
    part.glue = [[p1, tab[0], tab[1], p0]]
    part.valley = [(p0, p1)]
    # 絵は扇（糊代を除く）を 0.4mm 内へ縮めた形。角で縮めると外の方ほど白い隙間が広がったので、幅で縮める。
    fan = Polygon(outer + inner).buffer(-0.4, join_style=2)
    rim = fan.difference(Polygon([(0, 0)] + _arc(s1 - 2.5, a0 - 0.1, a1 + 0.1, ARC_N)))
    part.art = [{"kind": "poly", "pts": list(fan.exterior.coords)[:-1], "fill": HORN}]
    # 口の縁の濃い帯（コマ 9 の漏斗の口の輪）。
    if rim.geom_type == "Polygon" and not rim.is_empty:
        part.art.append({"kind": "poly", "pts": list(rim.exterior.coords)[:-1], "fill": HORN_RIM})
    return _norm(part)


def _wrap(number, key, name, length, circ, p, label, rings=(), notch=None, fill=BAMBOO, mark=None):
    """芯に巻いて筒にする帯。横が筒の長さ、縦が周。下の端に継ぎ目の糊代。notch は (幅, 深さ) で、左の端（口）の真ん中に切り欠く。
    切り欠きを継ぎ目の反対（周の半分）に置くのは、糊代の重なりで縁が厚くならない所に歌口を作るため。"""
    g = p["glue"]
    H = circ + g
    pts = [(0, 0), (length, 0), (length, H), (0, H)]
    if notch:
        w, dpt = notch
        yc = circ / 2
        pts += [(0, yc + w / 2), (dpt, yc + w / 2), (dpt, yc - w / 2), (0, yc - w / 2)]
    part = Part(number, key, name, pts, label_xy=(5, 1.5), label=label)
    part.glue = [[(0, circ), (length, circ), (length, H), (0, H)]]
    body = Polygon(pts).intersection(box(0, 0, length, circ)).buffer(-0.25, join_style=2)
    part.art = [{"kind": "poly", "pts": list(body.exterior.coords)[:-1], "fill": fill}]
    # 竹の節の筋（コマ 9・27 の柄と竹筒の端の輪）。
    for x in rings:
        part.art.append({"kind": "line", "pts": [(x, 0.6), (x, circ - 0.6)], "stroke": BAMBOO_DARK, "sw": 0.5})
    # mark は床の式が頼る位置の印（閉管の粘土の栓の深さ）。印が無いと詰める量で管の長さ、つまり鳴る高さが式とずれる。
    if mark is not None:
        part.art.append({"kind": "line", "pts": [(mark, 0.6), (mark, circ - 0.6)], "stroke": MARK, "sw": 0.6})
    return part


def _disc(number, key, name, r, label, hole=None, fill=HORN):
    pts = [(r + r * math.cos(2 * math.pi * i / 60), r + r * math.sin(2 * math.pi * i / 60)) for i in range(60)]
    part = Part(number, key, name, pts, label_xy=(r - 1.5, 0.8), label=label)
    art = [(r + (r - 0.3) * math.cos(2 * math.pi * i / 60), r + (r - 0.3) * math.sin(2 * math.pi * i / 60)) for i in range(60)]
    part.art = [{"kind": "poly", "pts": art, "fill": fill}]
    if hole:
        part.holes = [(r, r, hole)]
    return part


def _reed_frame(p):
    """舌を挟む枠。円盤 2 つを細い橋でつなぎ、橋の真ん中で谷折りして重ねる。窓は円盤の真ん中で、折ると重なる。"""
    r = reed_disc_r(p)
    bridge = 4
    wl, ww = reed_window(p)
    circle = lambda cx: [(cx + r * math.cos(2 * math.pi * i / 60), r + r * math.sin(2 * math.pi * i / 60)) for i in range(60)]
    shape = unary_union([Polygon(circle(r)), Polygon(circle(3 * r + bridge)), box(r, r - 2, 3 * r + bridge, r + 2)])
    pts = list(shape.exterior.coords)[:-1]
    part = Part(3, "reed", "舌の枠", pts, label_xy=(r - 1, 2 * r - 3.6), label="3")
    xf = 2 * r + bridge / 2
    part.valley = [((xf, r - 2), (xf, r + 2))]
    # 窓は舌の向き（横）に長い。根元は円盤の縁の側（左の円盤なら左）で挟む。
    part.cuts = [(r - wl / 2, r - ww / 2, wl, ww), (3 * r + bridge - wl / 2, r - ww / 2, wl, ww)]
    return part


def _tongue(p):
    """舌。窓の端から円盤の縁までの根元と、窓の中で揺れる自由長。薄い紙に写して切る。"""
    L = reed_root(p) + p["reed_length"]
    w = p["reed_width"]
    part = Part(4, "tongue", "舌", [(0, 0), (L, 0), (L, w), (0, w)], label_xy=(0.4, 0.3), label="4")
    # 根元と自由長の境の印（窓の端に合わせる）。折り線ではないので絵の線で描く。
    x = reed_root(p)
    # 印の線を窓の端に合わせると、根元を挟む長さが式（reed_root）どおりになり、自由長が reed_length になる。
    part.art = [{"kind": "line", "pts": [(x, 0.3), (x, w - 0.3)], "stroke": MARK, "sw": 0.3}]
    return part


def _collar(p):
    """継ぎの巻き。管の端・枠・ラッパの小さい口を 1 つに束ねる帯（コマ 9 の継ぎの巻きの筋）。息が漏れないよう糊で巻く。"""
    t = p["paper_thickness"]
    circ = wrap_circ(2 * reed_disc_r(p) + 2 * t, t)
    w, g = p["collar_w"], p["glue"]
    part = Part(6, "collar", "継ぎの巻き", [(0, 0), (w, 0), (w, circ + g), (0, circ + g)], label_xy=(0.5, 1), label="6")
    part.glue = [[(0, circ), (w, circ), (w, circ + g), (0, circ + g)]]
    part.art = [{"kind": "poly", "pts": [(0.25, 0.25), (w - 0.25, 0.25), (w - 0.25, circ - 0.25), (0.25, circ - 0.25)], "fill": BAMBOO}]
    part.art += [{"kind": "line", "pts": [(x, 0.6), (x, circ - 0.6)], "stroke": BAMBOO_DARK, "sw": 0.4} for x in (w / 3, 2 * w / 3)]
    return part


# コマ 24 右の鬼の面。面と筒の図を 1000 幅に拡大した座標で手で取った点。画素は使っていない。
_FACE = [(160, 555), (185, 520), (170, 470), (165, 420), (230, 395), (300, 380), (300, 345), (290, 300), (255, 280), (265, 250), (330, 235),
         (360, 250), (420, 225), (480, 230), (560, 225), (620, 250), (680, 245), (740, 280), (770, 350), (720, 370), (690, 440), (650, 500),
         (590, 530), (520, 580), (430, 610), (330, 600), (230, 580)]
_HORN = [(478, 232), (540, 140), (580, 105), (576, 170), (558, 232)]
_FEATHER_L = [(472, 222), (440, 150), (400, 80), (370, 25), (430, 60), (480, 120), (500, 205)]
_FEATHER_R = [(602, 245), (660, 150), (740, 100), (830, 115), (760, 160), (680, 215), (632, 252)]
_EYES = [[(305, 340), (330, 335), (340, 360), (310, 368)], [(440, 375), (500, 345), (560, 355), (520, 390), (460, 395)]]
_TEETH = [(188, 482), (280, 470), (400, 480), (520, 470), (570, 482), (560, 518), (420, 552), (300, 544), (192, 520)]
_MASK_BOX = (155, 25, 830, 610)


def _mask(p):
    """鬼の面。外形は面・角・羽の形を 1.5mm 太らせた輪郭で切る（羽の細かい毛を切り出すのは手で無理なので、葉の形にまとめた）。"""
    x0, y0, x1, _ = _MASK_BOX
    s = p["mask_w"] / (x1 - x0)
    sc = lambda ps: [((x - x0) * s, (y - y0) * s) for x, y in ps]
    shapes = [Polygon(sc(q)) for q in (_FACE, _HORN, _FEATHER_L, _FEATHER_R)]
    outline = unary_union(shapes).buffer(1.5, join_style=1).simplify(0.2)
    part = Part(2, "mask", "鬼の面", list(outline.exterior.coords)[:-1], label_xy=sc([(200, 486)])[0], label="2")
    part.art = [{"kind": "poly", "pts": sc(_FEATHER_L), "fill": FEATHER}, {"kind": "poly", "pts": sc(_FEATHER_R), "fill": FEATHER},
                {"kind": "poly", "pts": sc(_HORN), "fill": IVORY}, {"kind": "poly", "pts": sc(_FACE), "fill": MASK},
                {"kind": "poly", "pts": sc(_TEETH), "fill": TEETH}]
    part.art += [{"kind": "poly", "pts": sc(e), "fill": IVORY} for e in _EYES]
    # 歯の境の筋。
    for x in (235, 285, 335, 385, 435, 485, 530):
        part.art.append({"kind": "line", "pts": sc([(x, 478), (x, 530)]), "stroke": INK, "sw": 0.25})
    # 羽の軸。
    part.art.append({"kind": "line", "pts": sc([(485, 200), (430, 110), (375, 32)]), "stroke": INK, "sw": 0.25})
    part.art.append({"kind": "line", "pts": sc([(620, 245), (700, 160), (820, 118)]), "stroke": INK, "sw": 0.25})
    return _norm(part)


def _strip(number, key, name, length, width, tail, label, fill):
    """両端に糊代のある帯（曲がった柄・継ぎの帯）。糊代の境で谷折りして貼る。"""
    part = Part(number, key, name, [(0, 0), (length, 0), (length, width), (0, width)], label_xy=(tail + 1, 0.8), label=label)
    part.glue = [[(0, 0), (tail, 0), (tail, width), (0, width)], [(length - tail, 0), (length, 0), (length, width), (length - tail, width)]]
    part.valley = [((tail, 0), (tail, width)), ((length - tail, 0), (length - tail, width))]
    part.art = [{"kind": "poly", "pts": [(tail + 0.5, 0.25), (length - tail - 0.5, 0.25), (length - tail - 0.5, width - 0.25), (tail + 0.5, width - 0.25)], "fill": fill}]
    return part


def _bell(p):
    """鈴の袋。丸めて継ぎ目を貼り、上の糊代をつまんで貼り、玉を入れ、下の糊代を上と直角の向きにつまんで貼る（四面体になる）。"""
    t, g, e = p["paper_thickness"], p["glue"], BELL_SEAL
    C, H = wrap_circ(p["bell_d"], t), p["bell_height"]
    part = Part(4, "bell", "鈴", [(0, 0), (C + g, 0), (C + g, H), (0, H)], label_xy=(1, e + 1), label="4 鈴")
    part.glue = [[(0, 0), (C + g, 0), (C + g, e), (0, e)], [(0, H - e), (C + g, H - e), (C + g, H), (0, H)], [(C, e), (C + g, e), (C + g, H - e), (C, H - e)]]
    part.art = [{"kind": "poly", "pts": [(0.25, e + 0.25), (C - 0.25, e + 0.25), (C - 0.25, H - e - 0.25), (0.25, H - e - 0.25)], "fill": BELL}]
    # コマ 27 の鈴の口の筋を胴の真ん中に描く。
    part.art.append({"kind": "line", "pts": [(C * 0.2, H / 2), (C * 0.8, H / 2)], "stroke": INK, "sw": 0.5})
    # 糸の穴は上の糊代の真ん中。つまんで貼った 2 枚を一緒に通す。
    part.holes = [(C / 4, e / 2, 0.6)]
    return part


def parts(p):
    t = p["paper_thickness"]
    k = p["kind"]
    if k == "horn":
        L = p["pipe_length"]
        return [_horn(p), _wrap(2, "pipe", "息の管", L, wrap_circ(p["pipe_d"], t), p, "2 息の管", rings=(L * 0.2, L - 4, L - 2.5)),
                _reed_frame(p), _tongue(p), _disc(5, "lip", "口当て", p["lip_d"] / 2, "5", hole=p["pipe_d"] / 2 + t + 0.1), _collar(p)]
    if k == "tube":
        L = p["tube_length"]
        return [_wrap(1, "tube", "竹筒", L, wrap_circ(p["tube_d"], t), p, "1 竹筒", rings=(L * 0.45, L * 0.8), notch=(p["notch_width"], p["notch_depth"]), mark=L - p["plug_depth"]),
                _mask(p), _strip(3, "handle", "曲がった柄", p["handle_length"], HANDLE_W, HANDLE_GLUE, "3", BAMBOO)]
    a, b = p["bone_a"], p["bone_b"]
    circ = wrap_circ(p["bone_d"], t)
    joint = wrap_circ(p["bone_d"] + 2 * t, t) + 2 * JOINT_TAIL
    return [_wrap(1, "bonea", "竹筒 A", a, circ, p, "1 竹筒 A", rings=(2.5, a - 2.5)), _wrap(2, "boneb", "竹筒 B", b, circ, p, "2 竹筒 B", rings=(2.5, b - 2.5)),
            _strip(3, "joint", "継ぎの帯", joint, JOINT_W, JOINT_TAIL, "3", BAMBOO), _bell(p)]


def place(by_key, page, top, gap):
    """番号の順に、左から棚に並べる（入らなければ次の段）。説明の列は全部の部品の下に全幅で置く。
    刷る形ごとに部品の数と大きさが大きく違うので、決め打ちの配置より棚の方が形を足しても崩れにくい。"""
    x, y, row = page.x0, top, 0.0
    for q in sorted(by_key.values(), key=lambda q: q.number):
        if x > page.x0 and x + q.width > page.x1:
            x, y, row = page.x0, y + row + gap, 0.0
        q.x, q.y = x, y
        x += q.width + gap
        row = max(row, q.height)
    return y + row + gap, page.x1 - page.x0, page.x0


PAPER_WHY = "家庭のプリンタで刷って作るため"


def bom(p):
    paper = paper_name(thickness=p['paper_thickness'])
    k = p["kind"]
    if k == "horn":
        return [
            {"number": 1, "key": "horn", "name": "ラッパ", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明（図では塗った漏斗の形。木か紙か分からない）", "reason": PAPER_WHY},
            {"number": 2, "key": "pipe", "name": "息の管", "qty": 1, "material": paper, "substituted": True, "original_guess": "竹か木の柄（図の色と節の形からの推定）", "reason": "丸めると息の通る管になるため"},
            {"number": 3, "key": "reed", "name": "舌の枠", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明（図の継ぎの巻きの中は見えない）", "reason": PAPER_WHY},
            {"number": 4, "key": "tongue", "name": "舌", "qty": 1, "material": f"{paper_name(thickness=p['reed_thickness'])}（型紙から写して切る）", "substituted": True,
             "original_guess": "不明（ぴいぴいと鳴る物の中身。葦か薄い竹の舌かは推定）", "reason": "舌の厚みで鳴る高さが決まり、刷る紙より薄い紙が要るため"},
            {"number": 5, "key": "lip", "name": "口当て", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明（図では柄の端の円盤）", "reason": PAPER_WHY},
            {"number": 6, "key": "collar", "name": "継ぎの巻き", "qty": 1, "material": paper, "substituted": True, "original_guess": "糸か紙の巻き（図の筋からの推定）", "reason": "継ぎから息が漏れないよう糊で巻くため"},
        ]
    if k == "tube":
        return [
            {"number": 1, "key": "tube", "name": "竹筒", "qty": 1, "material": paper, "substituted": True, "original_guess": "竹（図の色と切り口からの推定）", "reason": "丸めると管になり、長さで鳴る高さを変えやすいため"},
            {"number": 2, "key": "mask", "name": "鬼の面", "qty": 1, "material": paper, "substituted": True, "original_guess": "張子か木彫りの面（推定）と鳥の羽", "reason": PAPER_WHY},
            {"number": 3, "key": "handle", "name": "曲がった柄", "qty": 1, "material": paper, "substituted": True, "original_guess": "曲げた竹（図の形からの推定）", "reason": PAPER_WHY},
            {"number": 7, "key": "plug", "name": "底の栓", "qty": 1, "material": f"油粘土（筒の底に {p['plug_depth']:g}mm 詰める）", "substituted": True, "original_guess": "竹の節（推定）", "reason": "息が抜けないよう底を塞ぎ、詰める量で高さを変えられるため"},
        ]
    cord = p["cord_length"] + 20  # 結び目の余り
    return [
        {"number": 1, "key": "bonea", "name": "竹筒 A", "qty": 1, "material": paper, "substituted": True, "original_guess": "竹（図の節からの推定）", "reason": PAPER_WHY},
        {"number": 2, "key": "boneb", "name": "竹筒 B", "qty": 1, "material": paper, "substituted": True, "original_guess": "竹（同じ）", "reason": PAPER_WHY},
        {"number": 3, "key": "joint", "name": "継ぎの帯", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明（図では継ぎに輪が見える）", "reason": "2 本を角度を付けて留めるため"},
        {"number": 4, "key": "bell", "name": "鈴", "qty": 1, "material": paper, "substituted": True, "original_guess": "金属の鈴（図の丸い形と口からの推定）", "reason": "紙の鈴は鳴らないので、玉を入れた紙の袋で鳴らすため"},
        {"number": 7, "key": "cord", "name": "糸", "qty": 1, "material": f"木綿の糸（{cord:g}mm に切る）", "substituted": True, "original_guess": "紐（図の線による）", "reason": "家にあるため"},
        # 鈴の玉の代わりの物にビーズを書かない（材料の前提で樹脂の側。油粘土は使ってよい。設計の条件・2026-11-07）
        {"number": 8, "key": "bead", "name": "鈴の玉", "qty": 1, "material": f"油粘土の玉（直径 {p['bead_d']:g}mm）", "substituted": True, "original_guess": "鈴の中の玉（推定）", "reason": "大きさを変えて試しやすいため"},
        {"number": 9, "key": "toggle", "name": "吊りの横木", "qty": 1, "material": "竹串（長さ 30mm に切る）", "substituted": True, "original_guess": "竹か木の小片（図の吊りの横棒）", "reason": "家にあるため"},
    ]


def materials(p):
    # 行の位置でなく key で引く。形によって部品表の行が変わるので、位置で引くと別の行を刷る。
    by = {r["key"]: r for r in bom(p)}
    base = [f"{by[next(iter(by))]['material']}を 1 枚", "のり、はさみ、定規"]
    if p["kind"] == "horn":
        return base + [by["tongue"]["material"], f"巻く芯（径 {p['pipe_d']:g}mm の鉛筆やペン）"]
    if p["kind"] == "tube":
        return base + [by["plug"]["material"], f"巻く芯（径 {p['tube_d']:g}mm のペンなど）"]
    return base + [by["cord"]["material"], by["bead"]["material"], by["toggle"]["material"], f"巻く芯（径 {p['bone_d']:g}mm・{p['bell_d']:g}mm）"]


def steps(p):
    out = ["刷った物差しに定規を当て、10cm か確かめる", "部品を実線で切る。窓と穴も切り抜く"]
    k = p["kind"]
    if k == "horn":
        out += [f"2 息の管を径 {p['pipe_d']:g}mm の芯に巻き、糊代で貼って芯を抜く",
                f"4 舌を薄い紙に写して切る（長さ {reed_root(p) + p['reed_length']:.1f}mm・幅 {p['reed_width']:g}mm）",
                f"3 舌の枠の片方の円盤に、4 舌の根元を貼る。舌の赤茶の線を窓の端に合わせ（根元 {reed_root(p):.1f}mm を挟む）、舌の先は窓の中で浮かせ、まわりに隙間を残す",
                "3 舌の枠を橋で谷折りして重ね、根元を挟んで貼る（窓どうしを重ねる）",
                "2 息の管の端を 3 枠に貼る。1 ラッパを丸めて糊代で貼り、小さい口を枠の反対の面に当てる",
                "6 継ぎの巻きで、管の端・枠・ラッパの口をまとめて巻いて貼る（息が漏れないように）",
                "5 口当てを管の反対の端に通して貼る",
                f"口当てから強めに吹く。舌の見込みの高さは {reed_hz(p):.0f}Hz（実物で未確認）。鳴らなければ舌の先の隙間を指で整える"]
    elif k == "tube":
        out += [f"1 竹筒を径 {p['tube_d']:g}mm の芯に巻き、糊代で貼って芯を抜く（切り欠きが口の縁に来る）",
                f"筒の切り欠きの無い端から粘土を {p['plug_depth']:g}mm 詰めて塞ぐ（竹筒の赤茶の印まで。詰めすぎると高く、足りないと低くなる）",
                "2 鬼の面を筒の中ほどに貼る（切り欠きを塞がない）", "3 曲がった柄を弧に曲げ、両端の糊代を筒に貼る",
                f"切り欠きの縁に息を細く当てて吹く（瓶の口を吹くように）。見込みの高さは {tube_hz(p):.0f}Hz（実物で未確認）"]
    else:
        out += [f"1 竹筒 A と 2 竹筒 B を径 {p['bone_d']:g}mm の芯に巻いて貼る",
                "3 継ぎの帯を竹筒 A の端に巻き、両端の糊代を竹筒 B の端に貼って、2 本を角度を付けて留める",
                f"4 鈴を径 {p['bell_d']:g}mm の芯に巻いて継ぎ目を貼り、穴のある上の糊代をつまんで内側を貼る",
                "鈴の玉を入れ、下の糊代を上と直角の向きにつまんで貼る",
                "糸を竹筒 A の先と継ぎに結び、真ん中を鈴の穴に通して、上に吊りの横木を結ぶ",
                "横木を持って振り、玉が鳴るか聞く"]
    return out


RESULTS = ("鳴った", "鳴らない")


def measures(p):
    """鳴るかの二択でなく、どんな音かを言葉で予想する（ほかの雛形と同じ形）。吹き方・振り方は数でないので欄に残す。"""
    if p["kind"] == "rattle":
        return {"predict": "振るとどんな音がすると思いますか（言葉で）", "rows": [[("振り方（速さ・向き）", 40)]]}
    return {"predict": "吹くとどんな音がすると思いますか（高い・低い・言葉で）", "rows": [[("吹き方（強さ・向き）", 40)]]}


def diagram(x, y, w, h, p):
    """組み上がりを横から見た絵。寸法の図ではなく、部品の並びを見せるだけ。"""
    k = p["kind"]
    if k == "horn":
        total = p["pipe_length"] + p["horn_length"]
        s = min(w / total, h / p["horn_mouth_d"])
        cy = y + h / 2
        x1 = x + p["pipe_length"] * s
        r0, r1 = reed_disc_r(p) * s, p["horn_mouth_d"] / 2 * s
        return [{"kind": "rect", "x": x, "y": cy - p["pipe_d"] / 2 * s, "w": p["pipe_length"] * s, "h": p["pipe_d"] * s},
                {"kind": "line", "x1": x + 2 * s, "y1": cy - p["lip_d"] / 2 * s, "x2": x + 2 * s, "y2": cy + p["lip_d"] / 2 * s},
                {"kind": "line", "x1": x1, "y1": cy - r0, "x2": x1 + p["horn_length"] * s, "y2": cy - r1},
                {"kind": "line", "x1": x1, "y1": cy + r0, "x2": x1 + p["horn_length"] * s, "y2": cy + r1},
                {"kind": "line", "x1": x1 + p["horn_length"] * s, "y1": cy - r1, "x2": x1 + p["horn_length"] * s, "y2": cy + r1}]
    if k == "tube":
        s = min(w / p["tube_length"], h / (p["tube_d"] * 3))
        cy = y + h / 2
        d = p["tube_d"] * s
        return [{"kind": "rect", "x": x, "y": cy - d / 2, "w": p["tube_length"] * s, "h": d},
                {"kind": "rect", "x": x + (p["tube_length"] - p["plug_depth"]) * s, "y": cy - d / 2, "w": p["plug_depth"] * s, "h": d},
                {"kind": "rect", "x": x, "y": cy - d / 2, "w": p["notch_depth"] * s, "h": min(d, p["notch_width"] * s)}]
    s = min(w / (p["bone_a"] + 10), h / (p["bone_a"] * 0.8))
    ax, ay = x, y + h
    bx, by = x + p["bone_a"] * s * 0.85, y + h - p["bone_a"] * s * 0.5
    top = (x + p["bone_a"] * s * 0.3, y)
    bell = (top[0], y + h * 0.35)
    return [{"kind": "line", "x1": ax, "y1": ay, "x2": bx, "y2": by},
            {"kind": "line", "x1": bx, "y1": by, "x2": bx + p["bone_b"] * s * 0.5, "y2": by + p["bone_b"] * s * 0.1},
            {"kind": "line", "x1": ax, "y1": ay, "x2": bell[0], "y2": bell[1], "dash": "1,0.6"},
            {"kind": "line", "x1": bx, "y1": by, "x2": bell[0], "y2": bell[1], "dash": "1,0.6"},
            {"kind": "line", "x1": bell[0], "y1": bell[1], "x2": top[0], "y2": top[1], "dash": "1,0.6"},
            {"kind": "rect", "x": bell[0] - 3, "y": bell[1] - 3, "w": 6, "h": 6}]
