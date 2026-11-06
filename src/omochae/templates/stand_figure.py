"""雛形 stand_figure: 描き直した絵を表と裏の 2 枚の紙にして貼り合わせ、台か支えで立てる。動かない玩具（人形・張子・ままごと道具・建物）の線。

なぜ 1 本に 40 件近くを乗せるか: 動かない玩具の違いは「何の絵か」と「どう置いて遊ぶか」に尽きる。絵は motif の値で選び、
置き方（台に立てる・立てかける・水に浮かべる・器の前に立てる）を仮説の違い（HYP_KEY＝form）にした。仕組みを 1 つに決めない（J-002）。
絵は原図を見て手で起こした多角形で、画素は使っていない（J-007）。寸法はどれも実物で未確認の見込み。
"""
import math

from shapely.geometry import Polygon, box
from shapely.ops import unary_union

from ._paper import paper_name
from ..model import Failure, Part

ID = "stand_figure"
SHEET_SET = "stand_figure-v1"
# 手順の紙の図の説明（instructions.compose_sheet）。御来迎の筒の言葉を刷らないため。
DIAGRAM_CAPTION = "台に立てた姿（前と横）"
# 結果の欄の見出し。この形の玩具に合う問いにする。
RESULT_HEAD = "おもちゃとして立ちましたか（1 つに丸）"
HYP_KEY = "form"
DEFAULTS = {
    "form": "base", "motif": "doll_mino_net",
    "fig_h": 80, "glue": 10,
    "base_w": 60, "base_d": 45, "base_h": 12,
    "strut_len": 44,
    # 紙の面密度は見込み。実物の紙を量ったら置き換える（虎の雛形と同じ値）。
    "paper_gsm": 150,
}
RANGES = {
    "fig_h": (25, 120), "glue": (6, 14),
    "base_w": (20, 150), "base_d": (20, 100), "base_h": (5, 40),
    "strut_len": (20, 110), "paper_gsm": (40, 400),
}
FORMS = ("base", "easel", "float", "box")
# 次の版で変えてよい寸法。絵（motif）と糊代は仮説の違いでも結果の違いでもないので開けない。
ALLOWED = {"fig_h", "base_w", "base_d", "base_h", "strut_len", "paper_gsm"}
PARAM_NAMES = {"fig_h": "絵の高さ", "base_w": "台の幅", "base_d": "台の奥行き", "base_h": "台の高さ", "strut_len": "支えの長さ", "paper_gsm": "紙の重さ"}
TITLES = {"base": "台に立てて飾る", "easel": "支えで立てかける", "float": "器に立てて水に浮かべる", "box": "器の前に立てて物を入れる"}

MARGIN = 1.5  # 絵の外の白い縁。絵の際で切らずに済むようにし、少しずれて切っても絵が欠けない
OUTLINE_SW = 0.2  # 絵の面の輪郭線の太さ（mm）。縮尺で細らない
STRUT_W = 14
STRUT_ANGLE = 30  # 支えを開く角度（度）の見込み。手順に刷る高さと倒れの式が同じ角度を使う
FLAP_TAPER = 1.5
MIN_TIP = 10  # 傾けて戻る余裕（度）。机を揺らした程度で倒れない見込み
MIN_TIP_BOX = 5  # 器の前に立てる形は、器の重さだけで後ろへ引く。物を入れると増えるので低めに置く
FREEBOARD = 5  # 水面から器の縁までの余裕。波で水が入らない見込み
TAPE_GSM = 50  # 梱包テープの面密度の見込み

# 江戸の色: 朱・藍・黄土・墨・胡粉の白に、絵に多い緑青・柿・茶を足した。原図の退色した地の色は写さない。
SHU, BENI, AI, ASAGI, MIDORI = "#c0452f", "#d9705f", "#35516d", "#7aa0a8", "#5d8767"
OUDO, KI, CHA, SUMI, GOFUN = "#c49a55", "#e3c565", "#8a5a34", "#2b2622", "#f5f0e4"
HADA, NEZU, KIN, KAKI, AKACHA = "#f0dcc2", "#9b9c95", "#d6b45a", "#d98a4c", "#a9503a"


# ---- 絵の部品（高さ 100 の単位。地面は 94、94〜99.7 は台板の帯を足す） ----

def E(cx, cy, rx, ry, fill, n=28):
    return {"kind": "poly", "fill": fill, "pts": [(cx + rx * math.cos(2 * math.pi * i / n), cy + ry * math.sin(2 * math.pi * i / n)) for i in range(n)]}


def R(x, y, w, h, fill):
    return {"kind": "poly", "fill": fill, "pts": [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]}


def P(pts, fill):
    return {"kind": "poly", "fill": fill, "pts": list(pts)}


def L(pts, sw=0.35, stroke=SUMI):
    return {"kind": "line", "pts": list(pts), "stroke": stroke, "sw": sw}


def _mirror(items, cx):
    return [{**it, "pts": [(2 * cx - x, y) for x, y in it["pts"]]} for it in items]


def _arc(cx, cy, r0, r1, a0, a1, fill, n=16):
    """太い弧（土瓶のつる・数珠の輪の代わり）。線でなく面にするのは、外形の縁が線を囲めるように。"""
    outer = [(cx + r1 * math.cos(math.radians(a0 + (a1 - a0) * i / n)), cy + r1 * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]
    inner = [(cx + r0 * math.cos(math.radians(a0 + (a1 - a0) * i / n)), cy + r0 * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n, -1, -1)]
    return P(outer + inner, fill)


def _face(cx, cy, s=1.0):
    return [L([(cx - 4 * s, cy - 0.5 * s), (cx - 1.8 * s, cy - 0.5 * s)], 0.3), L([(cx + 1.8 * s, cy - 0.5 * s), (cx + 4 * s, cy - 0.5 * s)], 0.3),
            E(cx, cy + 4 * s, 1.1 * s, 0.6 * s, SHU, 10)]


def _doll(cx=25, s=1.0, robe=KI, sleeve=None, collar=GOFUN, sash=MIDORI, dot=None, head="mage", prop=None, mino=False, top=0.0):
    """立ち姿の人形。台板の上に裾を広げて立つ形で、蓑・笠・頭巾・烏帽子などを選んで描き分ける。"""
    sleeve = sleeve or robe
    y = lambda v: top + v * s
    X = lambda v: cx + v * s
    it = []
    if prop == "pole":
        it.append(R(X(15), y(2), 1.8 * s, 92 * s, CHA))
        it.append(E(X(15.9), y(4), 5 * s, 2.4 * s, SUMI))
    it += [P([(X(-10), y(32)), (X(10), y(32)), (X(17), y(94)), (X(-17), y(94))], robe),
           P([(X(-10), y(33)), (X(-21), y(40)), (X(-22), y(63)), (X(-12), y(65))], sleeve),
           P([(X(10), y(33)), (X(21), y(40)), (X(22), y(63)), (X(12), y(65))], sleeve),
           P([(X(-5), y(31)), (X(5), y(31)), (X(0), y(46))], collar),
           R(X(-11.5), y(52), 23 * s, 5 * s, sash)]
    if dot:
        for dx, dy in ((-8, 70), (5, 66), (-3, 82), (9, 84), (-12, 88), (0, 74), (-16, 50), (16, 50)):
            it.append(E(X(dx), y(dy), 2.2 * s, 2.2 * s, dot, 12))
    if mino:
        # 蓑は朱の房を重ねて描く（10 の 2 体）。房の 1 つ 1 つを丸で置き、外形の縁で 1 枚につながる。
        for row, yy in enumerate((34, 42, 50, 58)):
            for k in range(-2 - (row > 1), 3 + (row > 1)):
                it.append(E(X(k * 6.5), y(yy), 4.6 * s, 4.6 * s, SHU if (k + row) % 2 else AKACHA, 12))
    it.append(E(X(0), y(20), 8 * s, 9.5 * s, HADA))
    if head == "mage":
        it += [P([(X(-8), y(17)), (X(-6), y(11)), (X(0), y(9)), (X(6), y(11)), (X(8), y(17)), (X(5), y(13)), (X(-5), y(13))], SUMI), R(X(-1.5), y(5.5), 3 * s, 4 * s, SUMI)]
    elif head == "bald":
        it.append(L([(X(-5), y(13)), (X(-2), y(12))], 0.3))
    elif head == "long":
        it += [P([(X(-8), y(16)), (X(-6), y(10)), (X(0), y(8.5)), (X(6), y(10)), (X(8), y(16)), (X(9), y(46)), (X(6), y(46)), (X(5), y(16)), (X(-5), y(16)), (X(-6), y(46)), (X(-9), y(46))], SUMI)]
    elif head == "hood":
        it += [P([(X(-8.5), y(22)), (X(-7), y(10)), (X(0), y(8)), (X(7), y(10)), (X(8.5), y(22)), (X(5), y(16)), (X(-5), y(16))], SUMI),
               P([(X(-8), y(22)), (X(8), y(22)), (X(6), y(29)), (X(-6), y(29))], SUMI)]
    elif head == "eboshi":
        it += [P([(X(-6), y(13)), (X(-2), y(-1)), (X(1), y(-6)), (X(3), y(1)), (X(6), y(13))], SUMI)]
    elif head == "kasa":
        it += [P([(X(-17), y(15)), (X(0), y(3)), (X(17), y(15))], KI), L([(X(-12), y(13.5)), (X(12), y(13.5))], 0.3)]
    elif head == "kasa_black":
        it += [P([(X(-13), y(14)), (X(-5), y(8)), (X(5), y(8)), (X(13), y(14))], SUMI)]
    if head not in ("hood",):
        it += _face(X(0), y(21), s)
    if prop == "net":
        it += [R(X(-20), y(14), 42 * s, 1.6 * s, CHA), E(X(-21), y(17), 7 * s, 5 * s, GOFUN, 16)]
        it += [L([(X(-26), y(16)), (X(-16), y(16))], 0.25), L([(X(-25), y(19)), (X(-17), y(19))], 0.25)]
    return it


def m_doll_mino_net():
    return 56, (8, 48), _doll(cx=29, robe=HADA, sleeve=SHU, sash=MIDORI, head="kasa", prop="net", mino=True)


def m_doll_mino_pole():
    return 52, (6, 44), _doll(cx=24, robe=HADA, sleeve=SHU, sash=MIDORI, head="bald", prop="pole", mino=True)


def m_doll_hood():
    return 50, (6, 44), _doll(cx=25, robe=OUDO, sleeve=OUDO, collar=MIDORI, sash=SUMI, dot=MIDORI, head="hood")


def m_hina_f():
    return 48, (6, 42), _doll(cx=24, robe=GOFUN, sleeve=BENI, collar=SHU, sash=ASAGI, dot=MIDORI, head="long")


def m_hina_m():
    return 50, (5, 45), _doll(cx=25, robe=KI, sleeve=KI, collar=GOFUN, sash=ASAGI, dot=MIDORI, head="eboshi", top=4)


def m_noroma():
    return 50, (6, 44), _doll(cx=25, robe=GOFUN, sleeve=MIDORI, collar=SUMI, sash=SUMI, dot=AI, head="mage")


def m_child():
    cx = 25
    it = [R(cx - 8, 66, 6, 28, HADA), R(cx + 2, 66, 6, 28, HADA),
          E(cx, 50, 12, 19, HADA),
          P([(cx - 11, 38), (cx - 18, 56), (cx - 15, 58), (cx - 8, 44)], HADA),
          P([(cx + 11, 38), (cx + 18, 56), (cx + 15, 58), (cx + 8, 44)], HADA),
          E(cx, 20, 10, 11, HADA),
          E(cx - 3, 12, 3, 2, SUMI, 10), E(cx + 4, 12, 3, 2, SUMI, 10)]
    it += _face(cx, 21) + [L([(cx - 4, 50), (cx + 4, 50)], 0.3)]
    return 50, (10, 40), it


def m_seated():
    cx = 30
    it = [P([(cx - 8, 36), (cx + 8, 36), (cx + 22, 76), (cx + 26, 94), (cx - 26, 94), (cx - 22, 76)], KAKI),
          P([(cx - 24, 86), (cx + 24, 86), (cx + 26, 94), (cx - 26, 94)], GOFUN),
          E(cx, 24, 10, 12, HADA),
          P([(cx - 10, 22), (cx - 9, 14), (cx - 2, 10), (cx + 7, 12), (cx + 11, 20), (cx + 11, 34), (cx + 6, 36), (cx + 4, 20), (cx - 6, 18)], SUMI)]
    it += [E(cx + dx, dy, 1.6, 1.6, GOFUN, 10) for dx, dy in ((-10, 60), (0, 54), (10, 62), (-4, 72), (8, 74), (-14, 78), (16, 80))]
    it += _face(cx - 3, 26)
    return 60, (4, 56), it


def m_fushimi():
    # 笠の女と、手を引かれる小さな子。子は 1 枚の絵の中に入れ、別の部品にしない（棚卸しで 1 体と数えた）。
    it = _doll(cx=36, robe=KAKI, sleeve=KAKI, collar=GOFUN, sash=SUMI, dot=GOFUN, head="kasa_black")
    it += _doll(cx=12, s=0.52, robe=KAKI, sleeve=AKACHA, collar=GOFUN, sash=MIDORI, head="bald", top=94 - 94 * 0.52)
    return 58, (2, 56), it


def m_dog(spots=True, apron=KAKI):
    it = [R(18, 58, 7, 36, GOFUN), R(30, 60, 7, 34, GOFUN), R(58, 60, 7, 34, GOFUN), R(70, 58, 7, 36, GOFUN),
          E(48, 52, 32, 15, GOFUN),
          P([(78, 44), (90, 22), (96, 30), (88, 40), (84, 52)], GOFUN),
          E(20, 34, 13, 12, GOFUN),
          P([(10, 36), (0, 39), (2, 46), (14, 44)], GOFUN),
          P([(12, 26), (14, 12), (21, 22)], SUMI if spots else GOFUN), P([(22, 22), (28, 11), (31, 24)], GOFUN),
          E(1.5, 40, 1.8, 1.5, SUMI, 10), L([(15, 31), (19, 31)], 0.3),
          P([(26, 44), (46, 46), (44, 64), (30, 60)], apron),
          L([(24, 42), (34, 46), (46, 45)], 0.5, SHU)]
    if spots:
        it += [E(60, 46, 6, 4, SUMI, 14), E(72, 56, 4, 3, CHA, 12), E(24, 30, 4, 3, CHA, 12), E(40, 52, 1.5, 1.5, SHU, 8), E(36, 55, 1.5, 1.5, SHU, 8)]
    return 98, (14, 81), it


def m_dog_white():
    return m_dog(spots=False, apron=SHU)


def m_horse():
    body = AKACHA
    it = [R(24, 58, 6, 36, body), R(34, 60, 6, 34, body), R(70, 60, 6, 34, body), R(80, 58, 6, 36, body),
          E(56, 50, 34, 14, body),
          P([(28, 46), (14, 18), (24, 14), (40, 44)], body),
          P([(14, 18), (2, 30), (6, 35), (20, 26)], body),
          P([(24, 14), (40, 44), (35, 46), (20, 18)], SUMI),
          P([(88, 44), (98, 52), (100, 76), (94, 76), (90, 54)], OUDO),
          P([(44, 36), (64, 36), (66, 52), (42, 52)], SUMI), R(48, 52, 12, 12, KI),
          L([(50, 56), (58, 56)], 0.3), L([(50, 60), (58, 60)], 0.3),
          E(13, 22, 1.2, 1.2, GOFUN, 8)]
    return 102, (20, 90), it


def m_owl():
    cx = 35
    it = [E(cx, 56, 26, 34, KI),
          P([(cx - 22, 30), (cx - 20, 8), (cx - 10, 22)], KI), P([(cx + 22, 30), (cx + 20, 8), (cx + 10, 22)], KI),
          E(cx - 9, 34, 8, 8, GOFUN), E(cx + 9, 34, 8, 8, GOFUN), E(cx - 9, 34, 3.5, 3.5, SUMI, 14), E(cx + 9, 34, 3.5, 3.5, SUMI, 14),
          P([(cx - 2.5, 40), (cx + 2.5, 40), (cx, 46)], KAKI),
          E(cx, 70, 15, 18, GOFUN),
          P([(cx - 30, 50), (cx - 22, 40), (cx - 18, 84), (cx - 26, 82)], OUDO), P([(cx + 30, 50), (cx + 22, 40), (cx + 18, 84), (cx + 26, 82)], OUDO),
          R(cx - 14, 88, 9, 6, KAKI), R(cx + 5, 88, 9, 6, KAKI)]
    for yy in range(58, 84, 6):
        for dx in (-8, 0, 8):
            it.append(L([(cx + dx - 2, yy), (cx + dx, yy + 2), (cx + dx + 2, yy)], 0.3))
    return 70, (8, 62), it


def m_monkey():
    cx = 34
    it = [E(cx, 66, 24, 26, AKACHA),
          E(cx - 4, 28, 14, 14, AKACHA), E(cx - 6, 30, 9, 9, HADA),
          E(cx - 9, 28, 1.3, 1.3, SUMI, 8), E(cx - 3, 28, 1.3, 1.3, SUMI, 8), L([(cx - 8, 34), (cx - 4, 34)], 0.3),
          E(cx - 6, 62, 11, 10, KI), L([(cx - 10, 58), (cx - 2, 66)], 0.3),
          P([(cx + 10, 40), (cx + 30, 56), (cx + 26, 90), (cx + 14, 80)], CHA),
          R(cx - 22, 86, 40, 8, AKACHA)]
    return 66, (10, 54), it


def m_sparrows():
    it = [P([(12, 94), (20, 78), (70, 78), (78, 94)], OUDO)]
    for cx, cy, flip in ((30, 64, False), (58, 48, True)):
        bird = [E(cx, cy, 16, 11, GOFUN), E(cx - 13, cy - 6, 7, 7, CHA), E(cx - 15, cy - 5, 1.2, 1.2, SUMI, 8),
                P([(cx - 20, cy - 6), (cx - 24, cy - 4), (cx - 19, cy - 3)], SUMI),
                P([(cx - 4, cy - 6), (cx + 20, cy - 20), (cx + 26, cy - 8), (cx + 8, cy + 2)], CHA),
                E(cx - 12, cy - 1, 2.5, 2, SUMI, 10)]
        it += _mirror(bird, cx) if flip else bird
    it.append(R(44, 56, 6, 24, OUDO))
    return 90, (12, 78), it


def m_rabbit():
    cx = 40
    it = [E(cx, 66, 30, 26, GOFUN),
          E(cx - 14, 30, 7, 18, GOFUN), E(cx + 14, 30, 7, 18, GOFUN), E(cx - 14, 32, 3.5, 12, BENI, 18), E(cx + 14, 32, 3.5, 12, BENI, 18),
          E(cx - 8, 62, 2, 2, SHU, 10), E(cx + 8, 62, 2, 2, SHU, 10), E(cx, 70, 2, 1.4, SHU, 10),
          L([(cx - 20, 74), (cx - 10, 72)], 0.3), L([(cx + 20, 74), (cx + 10, 72)], 0.3),
          R(cx - 24, 88, 48, 6, GOFUN)]
    return 80, (12, 68), it


def m_fish():
    it = [R(100, 60, 8, 34, CHA), P([(80, 94), (104, 84), (128, 94)], CHA),
          E(100, 42, 76, 20, KI),
          P([(170, 42), (196, 18), (190, 42), (196, 66)], KI),
          E(44, 36, 3, 3, GOFUN, 12), E(44, 36, 1.4, 1.4, SUMI, 8), L([(52, 28), (56, 42), (52, 56)], 0.4)]
    for x in range(66, 146, 10):
        for yy in (32, 44):
            it.append(L([(x, yy), (x + 4, yy + 4), (x + 8, yy)], 0.3))
    return 200, (78, 130), it


def m_turtle_top():
    cx = 50
    it = [E(cx, 22, 9, 9, MIDORI), E(cx - 34, 40, 9, 6, MIDORI), E(cx + 34, 40, 9, 6, MIDORI), E(cx - 32, 80, 9, 6, MIDORI), E(cx + 32, 80, 9, 6, MIDORI),
          E(cx, 60, 34, 32, MIDORI), E(cx, 60, 30, 28, "#7da27f"),
          R(cx - 40, 88, 80, 6, MIDORI)]
    for dx, dy in ((0, 48), (-14, 56), (14, 56), (0, 66), (-14, 72), (14, 72), (0, 82), (-22, 64), (22, 64)):
        it.append(P([(cx + dx - 5, 60 + (dy - 60) - 4), (cx + dx + 5, 60 + (dy - 60) - 4), (cx + dx + 7, dy), (cx + dx + 5, dy + 4), (cx + dx - 5, dy + 4), (cx + dx - 7, dy)], MIDORI))
    it.append(E(cx, 18, 1.2, 1.2, SUMI, 8))
    return 100, (10, 90), it


def m_turtle_side():
    it = [E(26, 36, 10, 8, MIDORI), P([(30, 40), (48, 54), (40, 62), (26, 44)], MIDORI),
          R(46, 70, 10, 24, MIDORI), R(100, 70, 10, 24, MIDORI),
          P([(40, 76), (52, 50), (78, 40), (104, 50), (122, 76)], MIDORI),
          P([(118, 70), (138, 80), (120, 82)], MIDORI),
          R(36, 74, 90, 6, "#7da27f"), E(20, 34, 1.3, 1.3, SUMI, 8),
          L([(62, 50), (66, 72)], 0.35), L([(80, 44), (82, 72)], 0.35), L([(98, 50), (96, 72)], 0.35), L([(54, 62), (112, 62)], 0.35)]
    return 140, (40, 116), it


def _bottle(cx, pts_half, fill, band=None):
    right = [(cx + x, y) for x, y in pts_half]
    left = [(cx - x, y) for x, y in reversed(pts_half)]
    it = [P(right + left, fill)]
    if band:
        y0, y1, color = band
        half = lambda yy: next(x for (x, y), (x2, y2) in zip(pts_half, pts_half[1:]) if y <= yy <= y2)
        w0, w1 = half(y0), half(y1)
        it.append(P([(cx - w0 + 0.3, y0), (cx + w0 - 0.3, y0), (cx + w1 - 0.3, y1), (cx - w1 + 0.3, y1)], color))
    return it


def m_tokkuri():
    half = [(7, 6), (5, 10), (5, 24), (9, 34), (20, 52), (26, 68), (25, 84), (20, 94)]
    it = _bottle(30, half, KAKI, band=(26, 32, MIDORI)) + [E(30, 7, 7, 2, OUDO, 16), L([(22, 60), (24, 80)], 0.3)]
    return 60, (8, 52), it


def m_longneck():
    half = [(5, 4), (3.5, 8), (3.5, 46), (8, 58), (16, 72), (17, 84), (14, 94)]
    return 40, (5, 35), _bottle(20, half, KI) + [E(20, 5, 5, 1.6, OUDO, 14)]


def m_pot():
    half = [(9, 10), (9, 22), (28, 34), (34, 56), (32, 80), (24, 94)]
    return 74, (10, 64), _bottle(37, half, OUDO, band=(22, 26, CHA)) + [L([(24, 50), (26, 76)], 0.3)]


def m_cup_stand():
    cx = 42
    it = [P([(cx - 14, 94), (cx - 10, 62), (cx + 10, 62), (cx + 14, 94)], KAKI),
          E(cx, 62, 34, 7, KAKI), E(cx, 62, 28, 4.5, MIDORI),
          P([(cx - 10, 56), (cx + 10, 56), (cx + 7, 44), (cx - 7, 44)], KAKI),
          P([(cx - 26, 30), (cx + 26, 30), (cx + 14, 46), (cx - 14, 46)], MIDORI), E(cx, 30, 26, 5, KAKI)]
    return 84, (26, 58), it


def m_dobin():
    cx = 50
    it = [_arc(cx, 52, 26, 31, 200, 340, CHA),
          P([(cx + 30, 64), (cx + 48, 50), (cx + 50, 56), (cx + 32, 76)], KAKI),
          E(cx, 70, 32, 22, KAKI), P([(cx - 32, 70), (cx + 32, 70), (cx + 26, 84), (cx - 26, 84)], MIDORI),
          E(cx, 50, 18, 4, OUDO), E(cx, 46, 3, 3, CHA, 12),
          R(cx - 22, 88, 44, 6, KAKI)]
    return 100, (22, 78), it


def m_nabe():
    it = [E(60, 66, 46, 20, KAKI), E(60, 60, 40, 12, OUDO), E(60, 62, 34, 8, GOFUN),
          P([(100, 56), (148, 34), (152, 42), (104, 66)], OUDO), E(128, 46, 5, 5, KIN, 16),
          P([(14, 62), (4, 58), (4, 66), (14, 70)], KAKI), R(26, 84, 68, 10, KAKI)]
    it += [L([(128 + 4 * math.cos(a), 46 + 4 * math.sin(a)), (128, 46)], 0.25) for a in [i * math.pi / 4 for i in range(8)]]
    return 154, (24, 96), it


def m_kama_furo():
    cx = 46
    it = [E(cx, 66, 42, 28, NEZU), E(cx, 74, 18, 14, KI),
          E(cx, 40, 30, 6, NEZU), E(cx, 30, 18, 10, "#7f807a"), E(cx, 20, 4, 3, CHA, 12),
          R(cx - 30, 88, 60, 6, NEZU)]
    for fx, fy in ((cx - 28, 60), (cx + 28, 62)):
        it += [E(fx + 4 * math.cos(a), fy + 4 * math.sin(a), 3, 3, BENI, 10) for a in [i * 2 * math.pi / 5 for i in range(5)]] + [E(fx, fy, 1.5, 1.5, KI, 8)]
    return 92, (16, 76), it


def m_chigibako():
    cx = 60
    it = [P([(cx - 56, 40), (cx + 56, 40), (cx + 56, 80), (cx - 56, 80)], OUDO), E(cx, 80, 56, 14, OUDO),
          E(cx, 40, 56, 22, GOFUN), E(cx, 40, 50, 18, OUDO),
          R(cx - 40, 88, 80, 6, OUDO)]
    for k in range(-5, 6):
        x = cx + k * 9
        it.append(L([(x - 3, 30 + abs(k)), (x, 34 + abs(k)), (x + 3, 30 + abs(k))], 0.6, KAKI if k % 2 else CHA))
        it.append(L([(x - 3, 58), (x, 62), (x + 3, 58)], 0.6, KAKI if k % 2 else CHA))
    it += [P([(cx + 20, 22), (cx + 30, 16), (cx + 28, 28)], MIDORI), P([(cx + 30, 26), (cx + 40, 22), (cx + 34, 32)], MIDORI)]
    return 120, (18, 102), it


def m_gourd():
    cx = 30
    it = [E(cx, 72, 22, 22, KI), E(cx, 34, 13, 14, KI), R(cx - 5, 46, 10, 8, KAKI),
          R(cx - 2, 10, 4, 12, CHA), L([(cx - 4, 50), (cx + 4, 50)], 0.4)]
    return 60, (12, 48), it


def m_kinchaku():
    cx = 38
    it = [P([(cx - 30, 94), (cx - 26, 60), (cx - 10, 36), (cx + 10, 36), (cx + 26, 60), (cx + 30, 94)], CHA),
          P([(cx - 10, 36), (cx - 14, 26), (cx - 4, 30), (cx, 22), (cx + 4, 30), (cx + 14, 26), (cx + 10, 36)], CHA),
          R(cx - 11, 34, 22, 4, SHU), L([(cx - 16, 70), (cx - 10, 50)], 0.4), L([(cx + 16, 70), (cx + 10, 50)], 0.4)]
    return 76, (8, 68), it


def m_juzu():
    cx, cy, r = 44, 52, 34
    it = [E(cx + r * math.cos(2 * math.pi * i / 22), cy + r * 0.9 * math.sin(2 * math.pi * i / 22), 4.4, 4.4, GOFUN, 12) for i in range(22)]
    it += [P([(cx - 6, 84), (cx + 6, 84), (cx + 8, 94), (cx - 8, 94)], SUMI), R(cx - 10, 88, 20, 6, SUMI)]
    return 88, (30, 58), it


def m_inro():
    cx = 26
    it = [R(cx - 2, 2, 4, 14, OUDO), E(cx, 6, 5, 5, OUDO),
          P([(cx - 18, 20), (cx + 18, 20), (cx + 20, 94), (cx - 20, 94)], SUMI),
          L([(cx - 19, 40), (cx + 19, 40)], 0.4, NEZU), L([(cx - 19.5, 62), (cx + 19.5, 62)], 0.4, NEZU),
          P([(cx, 60), (cx + 8, 68), (cx, 76), (cx - 8, 68)], GOFUN)]
    return 52, (6, 46), it


def m_katsuo_dish():
    it = [E(76, 78, 72, 14, ASAGI), E(76, 50, 60, 22, KAKI), R(30, 86, 92, 8, ASAGI)]
    for x in range(32, 124, 12):
        it.append(P([(x, 36), (x + 5, 34), (x + 4, 58), (x - 1, 60)], CHA))
    return 152, (28, 124), it


def m_katsuo():
    it = [E(80, 60, 76, 26, GOFUN), R(36, 82, 88, 12, GOFUN)]
    for x in range(30, 134, 14):
        it.append(P([(x, 44), (x + 6, 42), (x + 5, 72), (x - 1, 74)], KAKI))
    return 160, (34, 126), it


def m_shrine():
    it = [R(10, 18, 4, 76, SHU), R(84, 18, 4, 76, SHU), P([(2, 12), (96, 12), (98, 18), (0, 18)], SUMI), R(6, 26, 86, 4, SHU),
          R(24, 52, 50, 34, SHU), R(30, 58, 14, 20, AKACHA), R(52, 58, 16, 20, AKACHA),
          P([(16, 52), (40, 34), (58, 34), (82, 52)], NEZU),
          P([(34, 86), (64, 86), (70, 94), (28, 94)], NEZU), L([(32, 90), (66, 90)], 0.3),
          R(18, 86, 62, 3, GOFUN)]
    return 98, (2, 96), it


def m_teahouse():
    it = [P([(2, 40), (28, 18), (62, 18), (88, 40)], CHA), P([(36, 18), (45, 6), (54, 18)], NEZU),
          R(14, 40, 5, 54, SHU), R(70, 40, 5, 54, SHU), R(19, 44, 51, 30, KI), R(19, 74, 51, 6, NEZU),
          R(48, 80, 3, 14, CHA), R(60, 80, 3, 14, CHA)]
    it += [L([(50, yy), (61, yy)], 0.5, CHA) for yy in (84, 88, 92)]
    return 90, (10, 80), it


def m_byobu():
    it = []
    for k in range(4):
        x = 4 + k * 38
        it += [R(x, 14 + (k % 2) * 4, 36, 80 - (k % 2) * 4, SUMI), R(x + 2.5, 17 + (k % 2) * 4, 31, 74 - (k % 2) * 4, KIN if k % 2 else "#e3c873")]
        it += [P([(x + 10, 40), (x + 26, 40), (x + 26, 56), (x + 10, 56)], OUDO), P([(x + 14, 44), (x + 22, 44), (x + 22, 52), (x + 14, 52)], KIN)]
    return 160, (4, 156), it


def m_kabuto():
    cx = 45
    it = [P([(cx - 34, 70), (cx - 44, 60), (cx - 20, 58), (cx - 8, 72)], OUDO), P([(cx + 34, 70), (cx + 44, 60), (cx + 20, 58), (cx + 8, 72)], OUDO),
          E(cx, 58, 22, 18, NEZU), P([(cx - 6, 44), (cx - 16, 6), (cx - 10, 4), (cx, 40)], KIN), P([(cx + 6, 44), (cx + 16, 6), (cx + 10, 4), (cx, 40)], KIN),
          P([(cx - 30, 76), (cx + 30, 76), (cx + 34, 94), (cx - 34, 94)], AI)]
    it += [L([(cx + dx, 78), (cx + dx, 92)], 0.4, GOFUN) for dx in range(-24, 28, 8)]
    return 90, (12, 78), it


def m_nobori_box():
    it = [P([(4, 8), (30, 2), (36, 8), (36, 94), (4, 94)], KI), R(8, 12, 24, 80, "#ecd58a"),
          E(20, 50, 6, 18, AI), P([(20, 66), (14, 76), (26, 76)], AI), E(18, 38, 1.4, 1.4, GOFUN, 8),
          E(20, 18, 4, 4, SUMI, 14), E(20, 18, 2, 2, KI, 10)]
    return 40, (4, 36), it


# 絵の名前→描く関数と、原の素材の見込み（部品表の original_guess）。素材は棚卸しの見立てで確かめ待ち。
MOTIFS = {
    "doll_mino_net": (m_doll_mino_net, "土か張子の人形（見立て）"), "doll_mino_pole": (m_doll_mino_pole, "土か張子の人形（見立て）"),
    "doll_hood": (m_doll_hood, "人形（素材は不明）"), "hina_f": (m_hina_f, "紙（本文に「紙」らしき字、確かめ待ち）"),
    "hina_m": (m_hina_m, "紙（同じ）"), "child": (m_child, "人形（素材は不明）"), "noroma": (m_noroma, "人形（素材は不明）"),
    "seated": (m_seated, "土人形か（見立て）"), "fushimi": (m_fushimi, "土人形（伏見の見立て）"),
    "dog": (m_dog, "張子（見立て）"), "dog_white": (m_dog_white, "張子（見立て）"), "horse": (m_horse, "張子か木（見立て）"),
    "owl": (m_owl, "張子（見立て）"), "monkey": (m_monkey, "土人形か（見立て）"), "sparrows": (m_sparrows, "張子か木（見立て）"),
    "rabbit": (m_rabbit, "張子か土（見立て）"), "fish": (m_fish, "張子か木（見立て）"), "turtle_top": (m_turtle_top, "張子か土（見立て）"),
    "turtle_side": (m_turtle_side, "張子か土（見立て）"), "tokkuri": (m_tokkuri, "土器（見立て）"), "longneck": (m_longneck, "土器（見立て）"),
    "pot": (m_pot, "土器（見立て）"), "cup_stand": (m_cup_stand, "土器（見立て）"), "dobin": (m_dobin, "土器（見立て）"),
    "nabe": (m_nabe, "土器（見立て）"), "kama_furo": (m_kama_furo, "土器か金物（見立て）"), "chigibako": (m_chigibako, "曲物の木（見立て）"),
    "gourd": (m_gourd, "瓢箪（見立て）"), "kinchaku": (m_kinchaku, "布（見立て）"), "juzu": (m_juzu, "木か土の玉（見立て）"),
    "inro": (m_inro, "塗りの木か紙（見立て）"), "katsuo_dish": (m_katsuo_dish, "不明"), "katsuo": (m_katsuo, "不明"),
    "shrine": (m_shrine, "木（見立て）"), "teahouse": (m_teahouse, "木（見立て）"), "byobu": (m_byobu, "紙と木（見立て）"),
    "kabuto": (m_kabuto, "紙か張子（見立て）"), "nobori_box": (m_nobori_box, "紙と木（見立て）"),
}


def title(p):
    return TITLES[p["form"]]


def spec():
    return {"template_id": ID, "defaults": DEFAULTS, "ranges": RANGES, "form": FORMS, "motif": tuple(MOTIFS)}


def check_range(p):
    out = []
    for k, v in p.items():
        if k == "form":
            if v not in FORMS:
                out.append(Failure("F5.range", k, f"{v} は {FORMS} のどれでもない"))
        elif k == "motif":
            if v not in MOTIFS:
                out.append(Failure("F5.range", k, f"{v} という絵は無い"))
        elif k not in RANGES:
            out.append(Failure("F5.range", k, "知らない寸法の名前"))
        elif not isinstance(v, (int, float)) or isinstance(v, bool) or not RANGES[k][0] <= v <= RANGES[k][1]:
            out.append(Failure("F5.range", k, f"{v} は範囲 {RANGES[k]} の外"))
    return out


# ---- 絵から表の部品の形を作る ----

_CACHE = {}


def figure(p):
    """表の部品の (外形, 絵, 糊代, 折り線, 台板の帯の幅)。外形は絵の面を縁の分だけ太らせた輪郭で、手で輪郭を描かずに済む。
    折り線は台板の帯の下の端に置き、色の境（帯の色と白い糊代）で折る（本人の決定 d）。"""
    key = (p["motif"], p["fig_h"], p["glue"])
    if key in _CACHE:
        return _CACHE[key]
    fn, _ = MOTIFS[p["motif"]]
    w_u, (f0, f1), items = fn()
    s = p["fig_h"] / 100
    H, g = p["fig_h"], p["glue"]
    # 台板の帯を必ず足す。人形の絵には台板があり、器や動物にも置く面が要る。帯の下の端が真っ直ぐだから折り線が引ける。
    # 帯の下の端は折り線より少し上に止める。絵が折り線に触れると check_art が「またぐ」と見る。
    items = items + [R(f0, 94, f1 - f0, 5.4, OUDO)]
    art = [{**it, "pts": [(x * s, y * s) for x, y in it["pts"]]} for it in items]
    for it in art:
        if it["kind"] == "poly":
            it.setdefault("stroke", SUMI)
            it.setdefault("sw", OUTLINE_SW)
    polys = [Polygon(it["pts"]).buffer(0) for it in art if it["kind"] == "poly"]
    body = unary_union(polys)
    margin = MARGIN
    shape = body.buffer(margin)
    # 離れた絵の面（数珠の玉・子の人形）が縁でつながらない時は、縁を太らせて 1 枚にする。切り離れた紙にしないため。
    while shape.geom_type != "Polygon" and margin < 8:
        margin += 0.5
        shape = body.buffer(margin)
    x0, x1 = f0 * s - margin, f1 * s + margin
    # 帯の下の端（99.4）と折り線の隙間は縮尺で狭まるが、輪郭線の太さは狭まらない。小さい絵でも線が折り線に届かない所まで下げる。
    fold_y = max(99.7 * s, 99.4 * s + OUTLINE_SW / 2 + 0.001)
    shape = shape.intersection(box(-1e3, -1e3, 1e3, fold_y))
    tab = Polygon([(x0, fold_y), (x1, fold_y), (x1 - 1.5, fold_y + g), (x0 + 1.5, fold_y + g)])
    shape = unary_union([shape, tab])
    if shape.geom_type != "Polygon":
        shape = max(shape.geoms, key=lambda q: q.area)
    shape = Polygon(shape.exterior).simplify(0.2)
    mx, my = shape.bounds[0], shape.bounds[1]
    move = lambda pts: [(x - mx, y - my) for x, y in pts]
    out = (move(list(shape.exterior.coords)[:-1]), [{**it, "pts": move(it["pts"])} for it in art],
           [move(list(tab.exterior.coords)[:-1])], [tuple(move([(x0, fold_y), (x1, fold_y)]))], x1 - x0, shape.area, shape.centroid.y - my, fold_y - my)
    _CACHE[key] = out
    return out


def tab_width(p):
    return figure(p)[4]


def _mass(area, gsm):
    return area * gsm * 1e-6


def masses(p):
    """立てた時の質量の点 (g, 床からの高さ mm, 前後の位置 mm)。前後は台の真ん中が 0、絵の向く側が負。"""
    _, _, _, _, _, area, cy, fold = figure(p)
    fig_m = 2 * _mass(area, p["paper_gsm"])  # 表と裏の 2 枚
    W, D, Hb, gsm = p["base_w"], p["base_d"], p["base_h"], p["paper_gsm"]
    tray_m = _mass(W * D + 2 * Hb * (W + D), gsm)
    lift = fold - cy  # 折り線から絵の重心まで
    form = p["form"]
    if form == "easel":
        strut_m = _mass(STRUT_W * (p["strut_len"] + p["glue"]), gsm)
        zh = p["strut_len"] * math.cos(math.radians(STRUT_ANGLE))
        return [(fig_m, lift, 0), (strut_m, zh / 2, p["strut_len"] * math.sin(math.radians(STRUT_ANGLE)) / 2)]
    if form == "base":
        return [(fig_m, Hb + lift, 0), (tray_m, Hb / 2, 0)]
    if form == "float":
        tape = _mass(W * D + 2 * Hb * (W + D), TAPE_GSM)
        return [(fig_m, lift, 0), (tray_m + tape, Hb / 2, 0)]
    # box: 絵は器の前の壁の外に立つ。器の重さが後ろに引く。
    return [(fig_m, lift, -D / 2), (tray_m, Hb / 2, 0)]


def _center(pts):
    m = sum(q[0] for q in pts)
    return m, sum(q[0] * q[1] for q in pts) / m, sum(q[0] * q[2] for q in pts) / m


def tip_deg(p):
    """倒れるまでに傾けられる角度の小さい方（前と後ろ）。支える面の端から重心までの水平の距離と高さで決まる。"""
    m, z, y = _center(masses(p))
    form = p["form"]
    if form == "easel":
        # 前は糊代を前へ折った足、後ろは支えの足先が支える。
        front, back = p["glue"], p["strut_len"] * math.sin(math.radians(STRUT_ANGLE))
    elif form == "box":
        front, back = p["base_d"] / 2, p["base_d"] / 2
    else:
        front, back = p["base_d"] / 2, p["base_d"] / 2
    lo = min(front + y, back - y)
    return math.degrees(math.atan2(lo, z)) if z > 0 else 90.0


def draft_mm(p):
    """浮かべた時の沈み（水の密度 1g/cm³）。器の底の面で割る。"""
    m, _, _ = _center(masses(p))
    return m / (p["base_w"] * p["base_d"] * 1e-3)


def metrics(p):
    m, z, _ = _center(masses(p))
    return {"tip_deg": round(tip_deg(p), 2), "draft_mm": round(draft_mm(p), 2) if p["form"] == "float" else 0.0,
            "center_height_mm": round(z, 1), "mass_g": round(m, 2)}


def strut_hinge(p):
    """支えの折り目を貼る高さ（絵の下の端から）。支えを STRUT_ANGLE 開いた時に足先が床に着く高さ。"""
    return p["strut_len"] * math.cos(math.radians(STRUT_ANGLE))


def check_physics(p):
    out = []
    form, tw = p["form"], tab_width(p)
    width = max(x for x, _ in figure(p)[0])
    if width > 2 * 92 + 4 or p["fig_h"] + p["glue"] > 130:
        out.append(Failure("F5.stand", "絵", f"絵（幅 {width:.0f}mm）が大きく、表と裏が A4 に入らない"))
    if form in ("base", "float") and tw > p["base_w"] - 4:
        out.append(Failure("F5.stand", "糊代", f"糊代（幅 {tw:.0f}mm）が台（幅 {p['base_w']}mm）の上に収まらない"))
    if form == "box" and tw > p["base_w"] + 2 * p["base_h"]:
        out.append(Failure("F5.stand", "糊代", f"糊代（幅 {tw:.0f}mm）が器の底の下に収まらない"))
    if form == "box" and p["base_h"] > p["fig_h"] - 5:
        out.append(Failure("F5.stand", "器", "器の壁が絵より高く、絵の上に壁が見える"))
    if form == "easel":
        zh = strut_hinge(p)
        if zh + p["glue"] > p["fig_h"] - 2:
            out.append(Failure("F5.stand", "支え", f"支えの糊代（折り目 {zh:.0f}mm＋{p['glue']}mm）が絵の背からはみ出す"))
    tip = tip_deg(p)
    need = MIN_TIP_BOX if form == "box" else MIN_TIP
    if tip < need:
        out.append(Failure("F5.stand", "重心", f"{tip:.1f}° 傾けると倒れる（{need}° 以上ほしい）"))
    if form == "float":
        d = draft_mm(p)
        if d > p["base_h"] - FREEBOARD:
            out.append(Failure("F5.float", "器", f"{d:.1f}mm 沈み、縁まで {p['base_h'] - d:.1f}mm（{FREEBOARD}mm ほしい）で水が入る"))
        m, z, _ = _center(masses(p))
        # 浮いた箱の傾きの戻り（メタセンタ）: 浮心の高さ＋B²/(12·沈み)−重心の高さ。負なら水の上で倒れる。
        gm = d / 2 + min(p["base_w"], p["base_d"]) ** 2 / (12 * max(d, 1e-6)) - z
        if gm <= 0:
            out.append(Failure("F5.float", "重心", "水の上で傾いて戻らない（重心が高すぎる）"))
    return out


# ---- 部品 ----

def _front(p, mirror=False):
    outline, art, glue, fold, *_ = figure(p)
    w = max(x for x, _ in outline)
    if mirror:
        # 裏は表の鏡の絵。背中合わせに貼ると、後ろから見た姿になる。
        f = lambda pts: [(w - x, y) for x, y in pts]
        outline, art, glue = f(outline), [{**it, "pts": f(it["pts"])} for it in art], [f(g) for g in glue]
        fold = [tuple(f(list(seg))) for seg in fold]
    lx = min(fold[0][0][0], fold[0][1][0]) + 2
    num, key, name = (2, "back", "裏") if mirror else (1, "front", "表")
    return Part(num, key, name, outline, label_xy=(lx, fold[0][0][1] + 1.5), label=str(num), valley=list(fold), glue=glue, art=art, hide_folds=True)


def _tray(p):
    W, D, T, g = p["base_w"], p["base_d"], p["base_h"], p["glue"]
    f = min(g, T - 1)
    t = FLAP_TAPER
    pts = [(T, 0), (T + W, 0), (T + W + f, t), (T + W + f, T - t), (T + W, T), (2 * T + W, T), (2 * T + W, T + D), (T + W, T + D),
           (T + W + f, T + D + t), (T + W + f, 2 * T + D - t), (T + W, 2 * T + D), (T, 2 * T + D), (T - f, 2 * T + D - t), (T - f, T + D + t),
           (T, T + D), (0, T + D), (0, T), (T, T), (T - f, T - t), (T - f, t)]
    folds = [((T, T), (T + W, T)), ((T, T + D), (T + W, T + D)), ((T, T), (T, T + D)), ((T + W, T), (T + W, T + D)),
             ((T, 0), (T, T)), ((T + W, 0), (T + W, T)), ((T, T + D), (T, 2 * T + D)), ((T + W, T + D), (T + W, 2 * T + D))]
    glue = [[(T + W, 0), (T + W + f, t), (T + W + f, T - t), (T + W, T)], [(T + W, T + D), (T + W + f, T + D + t), (T + W + f, 2 * T + D - t), (T + W, 2 * T + D)],
            [(T, T + D), (T, 2 * T + D), (T - f, 2 * T + D - t), (T - f, T + D + t)], [(T, 0), (T, T), (T - f, T - t), (T - f, t)]]
    i = 0.25

    def panel(x0, y0, x1, y1, fill, trim=None):
        return {"kind": "poly", "fill": fill, "pts": [(x0 + i, y0 + i), (x1 - i, y0 + i), (x1 - i, y1 - i), (x0 + i, y1 - i)]}

    # 台の上の面（伏せた時の天板・浮かべた時の器の底）は黄土、壁は朱。面ごとに色を変え、色の境で折る（本人の決定 d）。
    art = [panel(T, T, T + W, T + D, OUDO), panel(T, 0, T + W, T, SHU), panel(T, T + D, T + W, 2 * T + D, SHU), panel(0, T, T, T + D, SHU), panel(T + W, T, 2 * T + W, T + D, SHU)]
    if T >= 8:
        # 壁に墨の細い縁を引く。塗りの台に見せるため。
        art += [L([(T + 1.5, T - 1.6), (T + W - 1.5, T - 1.6)], 0.4), L([(T + 1.5, T + D + 1.6), (T + W - 1.5, T + D + 1.6)], 0.4),
                L([(T - 1.6, T + 1.5), (T - 1.6, T + D - 1.5)], 0.4), L([(T + W + 1.6, T + 1.5), (T + W + 1.6, T + D - 1.5)], 0.4)]
    # 台は伏せて天板と外の壁を見せるので、刷った面を外に出す山折り。器は上が開いた形で、中の底と壁を上から見るので谷折り
    # （谷は刷った面がへこむ向き。前は形によらず谷で、伏せた台の色が全部内に隠れた）。
    kind = "mountain" if p["form"] == "base" else "valley"
    return Part(3, "tray", "台" if p["form"] == "base" else "器", pts, label_xy=(T + 2, T + 2), label="3 台" if p["form"] == "base" else "3 器",
                glue=glue, art=art, hide_folds=True, **{kind: folds})


def _strut(p):
    g, Ls = p["glue"], p["strut_len"]
    return Part(4, "strut", "支え", [(0, 0), (STRUT_W, 0), (STRUT_W, g + Ls), (0, g + Ls)], label_xy=(2, g + 2), label="4",
                valley=[((0, g), (STRUT_W, g))], glue=[[(0, 0), (STRUT_W, 0), (STRUT_W, g), (0, g)]],
                art=[{"kind": "poly", "fill": OUDO, "pts": [(0.25, g + 0.25), (STRUT_W - 0.25, g + 0.25), (STRUT_W - 0.25, g + Ls - 0.25), (0.25, g + Ls - 0.25)]}])


def parts(p):
    out = [_front(p), _front(p, mirror=True)]
    if p["form"] == "easel":
        out.append(_strut(p))
    else:
        out.append(_tray(p))
    return out


def place(by_key, page, top, gap):
    """表と裏を上の段に並べ（入らなければ縦に積む）、台か支えを下の段に置く。文字はその右か下。"""
    front, back = by_key["front"], by_key["back"]
    front.x, front.y = page.x0, top
    if front.width * 2 + gap <= page.x1 - page.x0:
        back.x, back.y = page.x0 + front.width + gap, top
        y = top + front.height + gap
    else:
        back.x, back.y = page.x0, top + front.height + gap
        y = back.y + back.height + gap
    low = by_key.get("tray") or by_key["strut"]
    low.x, low.y = page.x0, y
    right = page.x0 + low.width + gap
    if page.x1 - right >= 104:
        return y, page.x1 - right, right
    return y + low.height + gap, page.x1 - page.x0, page.x0


def bom(p):
    paper = paper_name(p["paper_gsm"])
    why = "家庭のプリンタで刷って作るため"
    orig = MOTIFS[p["motif"]][1]
    rows = [
        {"number": 1, "key": "front", "name": "表", "qty": 1, "material": paper, "substituted": True, "original_guess": orig, "reason": why},
        {"number": 2, "key": "back", "name": "裏", "qty": 1, "material": paper, "substituted": True, "original_guess": orig, "reason": why},
    ]
    if p["form"] == "easel":
        rows.append({"number": 4, "key": "strut", "name": "支え", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明（絵に支えは見えない）", "reason": why})
    else:
        name = "台" if p["form"] == "base" else "器"
        rows.append({"number": 3, "key": "tray", "name": name, "qty": 1, "material": paper, "substituted": True, "original_guess": "不明（台板は木かと見込む）", "reason": why})
    if p["form"] == "float":
        rows.append({"number": 5, "key": "tape", "name": "水よけ", "qty": 1, "material": "透明な梱包テープ", "substituted": True, "original_guess": "不明", "reason": "紙の器に水を通さないため"})
    return rows


def materials(p):
    out = [f"{paper_name(p['paper_gsm'])}を 1 枚", "のり、はさみ、定規"]
    if p["form"] == "float":
        out += ["透明な梱包テープ", "水を張った盆か洗面器"]
    if p["form"] == "box":
        out.append("豆か、小さく丸めた紙（器に入れる）")
    return out


def steps(p):
    out = ["刷った物差しに定規を当て、10cm か確かめる",
           "1 表と 2 裏を、外の線で切る。白い縁は絵の際まで切らずに残す",
           "1 と 2 を、絵を外にして背中合わせに貼る。下の白い糊代は貼らずに残す",
           "糊代を色の境で折る。1 は前へ、2 は後ろへ"]
    form = p["form"]
    if form == "easel":
        out += ["4 支えを切り、色の境で谷折りする",
                f"4 の糊代を 2 の背中に貼る。折り目が絵の下の端から {strut_hinge(p):.0f}mm の高さに来るように",
                f"支えを {STRUT_ANGLE}° くらい開き、机に立てる"]
        return out
    out += [f"3 {'台' if form == 'base' else '器'}を切り、色の境で{'山' if form == 'base' else '谷'}折りして箱にする。角の糊代は内側に貼る"]
    if form == "base":
        out += ["台を伏せて置き、上の面の真ん中に 1・2 の糊代を貼る"]
    elif form == "float":
        out += ["器の外の底と壁に、透明なテープを隙間なく貼る（水を通さないため）", "器の底の真ん中に 1・2 の糊代を貼る",
                "水を張った盆にそっと浮かべる。遊んだら取り出して乾かす"]
    else:
        out += ["1・2 の糊代を両方とも後ろへ折り直し、器の底の下に差し込んで貼る。絵が器の前の壁を隠すように", "器に豆や丸めた紙を入れて遊ぶ"]
    return out


# 動かない玩具の物差しは、立つか（浮くか）と、倒れたかで足りる。どれが昔の作り方かは紙では決めない。
RESULTS = ("立った", "倒れた", "わからない")


def measures(p):
    where = "置いた所（机・畳・水）" if p["form"] == "float" else "置いた所（机・畳・棚）"
    return {"predict": "置いた時（浮かべた時）、どうなると思いますか（言葉か絵で）", "rows": [[(where, 40)]]}


def diagram(x, y, w, h, p):
    """横から見た姿。台・器・支えと絵の板の位置の関係だけを描く。"""
    form = p["form"]
    D, Hb, H = p["base_d"], p["base_h"], p["fig_h"]
    depth = D + 20 if form != "easel" else p["strut_len"] + 20
    s = min(w / depth, h / (H + Hb + 6))
    floor = y + h - 2
    shapes = [{"kind": "line", "x1": x, "y1": floor, "x2": x + w, "y2": floor}]
    cx = x + w / 2
    if form == "easel":
        top = floor - H * s
        shapes.append({"kind": "rect", "x": cx - 0.6, "y": top, "w": 1.2, "h": H * s})
        zh = strut_hinge(p) * s
        foot = cx + p["strut_len"] * math.sin(math.radians(STRUT_ANGLE)) * s
        shapes.append({"kind": "line", "x1": cx + 0.6, "y1": floor - zh, "x2": foot, "y2": floor})
        return shapes
    bx = cx - D * s / 2
    shapes.append({"kind": "rect", "x": bx, "y": floor - Hb * s, "w": D * s, "h": Hb * s, **({"dash": "1,0.6"} if form != "base" else {})})
    if form == "base":
        shapes.append({"kind": "rect", "x": cx - 0.6, "y": floor - (Hb + H) * s, "w": 1.2, "h": H * s})
    elif form == "float":
        shapes.append({"kind": "rect", "x": cx - 0.6, "y": floor - H * s, "w": 1.2, "h": H * s})
        wl = floor - draft_mm(p) * s
        shapes.append({"kind": "line", "x1": x, "y1": wl, "x2": x + w, "y2": wl, "dash": "2,1"})
    else:
        shapes.append({"kind": "rect", "x": bx - 1.2, "y": floor - H * s, "w": 1.2, "h": H * s})
    return shapes
