"""雛形 stick_prop: 平らな形（1 枚か 2 枚）を竹串に付け、手で持って振る・かざす・かぶる。『江都二色』の持ち物の玩具の線。

1 本の雛形に、線の玩具を全部乗せる（本人「なるべく並列ですべて作ろう」、11-04、docs/process/template-contract.md）。
玩具ごとの違いは形の選び（shape）と寸法で出し、仮説の違い（どう持つ・何が動くか）は付け方（hold）で描き分ける。
形の点は原図を見て手で取った箱の中の座標で、絵の画素は使っていない（J-007）。どの値も実物では未確認。
Claude が変えてよいのは ALLOWED の名前の値だけで、座標には触れない。

設計の勘所:
- 形は「箱の単位」で持ち、size（箱の長い辺の mm）で一度に縮める。玩具を足す時は SHAPES に 1 つ足し、HOLDS に付け方を書く。
- 絵は描いた後に外形・折り線・糊代で切り抜く（_clip）。手で取った点が少しはみ出しても、check_art に落ちる絵を刷らないため。
- 動く仕組みの床（check_physics）は、付け方ごとに「組めない・持てない・動かない」の式だけを置く。動き方の良し悪しは紙が返事をする。
"""
import math

from shapely.geometry import LineString, Point, Polygon, box as _box
from shapely.ops import unary_union

from ..model import Failure, Part
from ..textfit import text_width

ID = "stick_prop"
SHEET_SET = "stick-prop-v1"
# 仮説を分ける寸法の名前。持ち物の玩具の読みは「どう付けて、何が動くか」で割れるので、付け方で分ける。
# 手順の紙の図の説明（instructions.compose_sheet）。御来迎の筒の言葉を刷らないため。
DIAGRAM_CAPTION = "持った時の姿（棒と貼る所）"
# 結果の欄の見出し。この形の玩具に合う問いにする。
RESULT_HEAD = "おもちゃとして遊べましたか（1 つに丸）"
HYP_KEY = "hold"
DEFAULTS = {
    "shape": "uchiwa_l", "hold": "glue",
    # size は形の箱の長い辺。stick_len は竹串の長さ（台所の竹串の 18cm を既定に見込む）。
    "size": 100, "stick_len": 180, "stick_d": 3,
    # 重りは首振り（nod）で重心を軸より下げるための油粘土。0 は付けない。
    "weight_g": 0.0,
    "slide_gap": 3.0, "travel": 12,
    "pocket_depth": 35, "arrows": 3,
    "loops": 3, "loop_len": 22,
    "thread_len": 30, "wheel_d": 32,
    # 紙の面密度は見込み。実物の紙を量ったら置き換える。
    "paper_gsm": 150,
}
RANGES = {
    "size": (30, 180), "stick_len": (100, 300), "stick_d": (2, 5),
    "weight_g": (0, 10),
    "slide_gap": (0, 10), "travel": (4, 30),
    "pocket_depth": (10, 80), "arrows": (1, 6),
    "loops": (1, 6), "loop_len": (8, 40),
    "thread_len": (5, 80), "wheel_d": (15, 60),
    "paper_gsm": (40, 400),
}
ALLOWED = {"size", "stick_len", "weight_g", "slide_gap", "travel", "pocket_depth", "arrows", "loop_len", "thread_len", "wheel_d", "paper_gsm"}
PARAM_NAMES = {"size": "大きさ（長い辺の mm）", "stick_len": "竹串の長さ（mm）", "weight_g": "重りの重さ（g）", "slide_gap": "すき間（mm）",
               "travel": "動く長さ（mm）", "pocket_depth": "袋の深さ（mm）", "arrows": "矢の数", "loop_len": "輪の帯の長さ（mm）",
               "thread_len": "吊る糸の長さ（mm）", "wheel_d": "車の直径（mm）", "paper_gsm": "紙の重さ（g/m²）"}

# 床の見込み。どれも実物で確かめるまでの安全側の値。
STICK_IN = 20  # 竹串を紙に貼る長さ。これより短いと振った時にテープごと抜けると見込む
HAND = 50  # 手で握る長さ（大人の手の幅の見込み）
HOLE_MARGIN = 4  # 穴から紙の端まで。これより狭いと裂けやすい（pivot_counterweight と同じ見込み）
MIN_DROP = 2.0  # 首振りで、重心が軸より下にある距離。これより小さいと揺れて戻らない
SLIDE_MIN, SLIDE_MAX = 1.5, 6.0  # 差し込む物のすき間。狭いと紙がこすれて動かず、広いと抜け落ちる
TOOTHPICK = 60  # つまようじの長さ
ARROW_OUT = 15  # 矢羽を袋の口から出す長さ
LOOP_GLUE = 5
AXLE_UP = 5  # 車の軸を竹串の下の端から上げる距離
GLUE = 6
JAW_OFFSET = 5  # 顎の重心が軸より前にある距離。これより小さいと顎が垂れずに口が開かない
HOLE_R = 1.2

# 江戸の色（本人の方針: 朱・藍・黄土・墨・胡粉の白で描き直す）。
SHU, AI, OCHRE, SUMI, GOFUN = "#c8553d", "#3a5a7a", "#c9a24a", "#2b2b2b", "#f4efe2"
ROKUSHO, HADA, MOMO, CHA, PALE = "#6f9a8a", "#ecd3b0", "#e3a69a", "#7a4a2a", "#e6d6a8"


def _circle(cx, cy, r, n=24):
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def _poly(pts, fill, stroke=None, sw=0.2):
    d = {"kind": "poly", "pts": pts, "fill": fill}
    if stroke:
        d.update(stroke=stroke, sw=sw)
    return d


def _line(pts, stroke=SUMI, sw=0.35):
    return {"kind": "line", "pts": pts, "stroke": stroke, "sw": sw}


def _pts(g):
    return [tuple(c) for c in list(g.exterior.coords)[:-1]]


def _outer(g):
    """和の形の外側。穴ができても切る線は外側の 1 本にする（はさみで切れる形にするため）。"""
    if g.geom_type == "MultiPolygon":
        g = max(g.geoms, key=lambda q: q.area)
    return Polygon(g.exterior)


# ---- 形の箱。点は箱の単位（x は右、y は下）。原図を見て手で取った --------------------------------
# foot: 竹串が紙から出る所、top: 紙の中で竹串が届く所、pivot: 首振りの軸、weight: 重りを付ける所。
def _ame_tori():
    body = [(3, 36), (16, 28), (30, 27), (44, 31), (58, 30), (74, 18), (97, 3), (90, 20), (80, 34), (66, 46), (48, 54), (30, 53), (16, 46)]
    art = [_poly(body, GOFUN, SUMI, 0.3), _poly([(3, 36), (14, 31), (14, 40)], OCHRE),
           _poly(_circle(24, 34, 2.2, 12), SUMI), _line([(40, 41), (58, 39), (72, 30)]), _line([(76, 24), (92, 8)], SUMI, 0.25)]
    return {"box": (100, 56), "outline": body, "art": art, "foot": (48, 54), "top": (48, 33), "pivot": (46, 42), "weight": (48, 51)}


def _tori_ki():
    body = [(6, 0), (12, 2), (22, 32), (36, 44), (56, 52), (72, 58), (64, 62), (46, 62), (30, 68), (18, 74), (8, 73), (2, 68), (6, 60), (14, 52), (16, 40)]
    art = [_poly(body, "#d9b25a", SUMI, 0.3), _poly(_circle(12, 64, 1.8, 12), SUMI), _line([(20, 50), (34, 56), (50, 58)], CHA, 0.4),
           _line([(9, 4), (16, 36)], CHA, 0.3)]
    return {"box": (72, 74), "outline": body, "art": art, "foot": (60, 60), "top": (25, 40), "pivot": (34, 54), "weight": (50, 60)}


def _katana():
    full = [(6, 0), (14, 0), (14, 25), (19, 25), (19, 30), (15, 30), (15, 96), (10, 100), (5, 96), (5, 30), (1, 30), (1, 25), (6, 25)]
    art = [_poly([(6, 0), (14, 0), (14, 25), (6, 25)], CHA)]
    art += [_poly([(10, 1 + 6 * k), (13, 3.5 + 6 * k), (10, 6 + 6 * k), (7, 3.5 + 6 * k)], GOFUN) for k in range(4)]
    art += [_poly([(1, 25), (19, 25), (19, 30), (1, 30)], ROKUSHO, SUMI, 0.2), _poly([(5, 30), (15, 30), (15, 96), (10, 100), (5, 96)], SUMI)]
    art += [_poly(_circle(8 if k % 2 else 12, 34 + 5 * k, 0.9, 8), GOFUN) for k in range(13)]
    return {"box": (20, 100), "outline": full, "art": art, "foot": (10, 0), "top": (10, 96), "core": True}


def _shitadashi():
    out = [(10, 4), (90, 4), (96, 28), (92, 55), (85, 80), (70, 95), (50, 101), (30, 95), (15, 80), (8, 55), (4, 28)]
    art = [_poly(out, HADA, SUMI, 0.3), _poly([(10, 4), (90, 4), (96, 28), (4, 28)], OCHRE, SUMI, 0.3),
           _line([(8, 13), (92, 13)], CHA, 0.4), _line([(6, 21), (94, 21)], CHA, 0.4)]
    for cx in (32, 68):
        art += [_poly(_circle(cx, 50, 9), GOFUN, SUMI, 0.4), _poly(_circle(cx + (1 if cx < 50 else -1), 51, 3.5, 12), SUMI)]
    art += [_line([(20, 37), (40, 35)], SUMI, 1.2), _line([(60, 35), (80, 37)], SUMI, 1.2), _line([(50, 56), (46, 66), (53, 67)], SUMI, 0.5)]
    for y in (42, 50, 58, 66):
        art += [_line([(9, y), (16, y + 3)], SUMI, 0.6), _line([(91, y), (84, y + 3)], SUMI, 0.6)]
    art.append(_poly([(38, 73), (62, 73), (57, 79), (43, 79)], "#5a2a20"))
    return {"box": (100, 101), "outline": out, "art": art, "foot": (50, 101), "top": (50, 55), "mouth": (50, 76), "chin": 101,
            "tongue": _poly([(44, 77), (56, 77), (55, 90), (50, 93), (45, 90)], SHU, SUMI, 0.2)}


def _uchiwa(notched):
    leaf = Polygon(_circle(50, 48, 47, 48))
    if notched:  # 小さい団扇は上の真ん中が少しくぼむ（コマ 8 の図）
        leaf = unary_union([Polygon(_circle(33, 40, 33, 32)), Polygon(_circle(67, 40, 33, 32)), Polygon(_circle(50, 55, 42, 40))])
    shape = _outer(unary_union([leaf, _box(44, 88, 56, 100)]))
    art = [_poly(_pts(shape), GOFUN, SUMI, 0.3), _poly(_circle(50, 92, 17, 24), OCHRE, SUMI, 0.25)]
    for k in range(23):
        t = math.radians(160 + 10 * k)
        art.append(_line([(50, 86), (50 + 46 * math.cos(t), 48 + 46 * math.sin(t))], SUMI, 0.25))
    return {"box": (100, 100), "outline": _pts(shape), "art": art, "foot": (50, 100), "top": (50, 45)}


def _genji():
    face = [(10, 30), (20, 22), (50, 20), (70, 28), (72, 55), (62, 72), (45, 78), (28, 74), (14, 62), (8, 45)]
    hood = [(5, 28), (15, 10), (40, 2), (70, 5), (92, 15), (98, 35), (90, 50), (74, 48), (70, 28), (50, 22), (20, 24), (8, 34)]
    neck = [(38, 74), (52, 74), (52, 80), (38, 80)]
    out = _pts(_outer(unary_union([Polygon(face), Polygon(hood), Polygon(neck)])))
    art = [_poly(out, HADA, SUMI, 0.3), _poly(hood, ROKUSHO, SUMI, 0.3), _line([(22, 40), (34, 38)], SUMI, 0.8), _line([(44, 38), (56, 40)], SUMI, 0.8),
           _poly([(24, 46), (32, 44), (33, 47), (25, 48)], SUMI), _poly([(46, 45), (54, 46), (53, 49), (45, 48)], SUMI),
           _line([(38, 50), (36, 58), (41, 59)], SUMI, 0.4), _line([(30, 66), (40, 64), (50, 66)], SUMI, 0.5), _line([(30, 12), (60, 10), (85, 22)], "#4f7a6a", 0.6)]
    return {"box": (98, 80), "outline": out, "art": art, "foot": (45, 80), "top": (45, 50), "pivot": (45, 40), "weight": (45, 77)}


def _heike():
    hat = [(15, 40), (18, 10), (30, 0), (55, 2), (62, 15), (60, 40)]
    face = [(12, 40), (62, 40), (64, 65), (58, 88), (45, 98), (28, 98), (16, 88), (10, 65)]
    neck = [(32, 96), (44, 96), (44, 110), (32, 110)]
    out = _pts(_outer(unary_union([Polygon(hat), Polygon(face), Polygon(neck)])))
    art = [_poly(out, HADA, SUMI, 0.3), _poly(hat, SUMI), _line([(22, 30), (52, 26)], "#555", 0.4),
           _line([(18, 54), (32, 52)], SUMI, 1.3), _line([(42, 52), (56, 54)], SUMI, 1.3),
           _poly(_circle(25, 60, 2, 10), SUMI), _poly(_circle(49, 60, 2, 10), SUMI),
           _line([(37, 62), (34, 72), (39, 73)], SUMI, 0.4), _line([(28, 84), (37, 81), (47, 84)], SUMI, 0.6), _line([(12, 66), (16, 80)], SUMI, 0.5)]
    return {"box": (66, 110), "outline": out, "art": art, "foot": (38, 110), "top": (38, 70), "pivot": (37, 50), "weight": (38, 106)}


def _utsubo():
    out = [(8, 8), (20, 2), (35, 6), (50, 2), (62, 8), (64, 30), (58, 50), (64, 75), (62, 100), (50, 108), (35, 104), (20, 108), (8, 100), (6, 75), (12, 50), (6, 30)]
    P = Polygon(out)
    art = [_poly(_pts(P.intersection(_box(0, 0, 70, 52))), SUMI), _poly(_pts(P.intersection(_box(0, 52, 70, 110))), OCHRE)]
    for k in range(4):
        art.append(_line([(8, 62 + 11 * k), (20, 65 + 11 * k), (30, 60 + 11 * k)], SUMI, 0.9))
        art.append(_line([(40, 60 + 11 * k), (50, 65 + 11 * k), (62, 61 + 11 * k)], SUMI, 0.9))
    for cx in (21, 49):
        for i in range(8):
            t = 2 * math.pi * i / 8
            art.append(_poly(_circle(cx + 6 * math.cos(t), 26 + 6 * math.sin(t), 2.6, 10), GOFUN))
        art.append(_poly(_circle(cx, 26, 2.2, 10), OCHRE))
    art.append(_line([(35, 6), (35, 104)], CHA, 0.5))
    return {"box": (70, 110), "outline": out, "art": art, "foot": (35, 104), "top": (35, 20), "pocket": (35, 0.36)}


def _yumiya():
    quiver = Polygon([(20, 40), (44, 40), (48, 92), (40, 98), (24, 98), (16, 92)])
    shafts = _box(18, 4, 46, 40)
    bow = LineString([(8, 0), (3, 30), (3, 70), (10, 100)]).buffer(2.5)
    straps = [_box(4, 46, 20, 52), _box(5, 84, 18, 89)]
    shape = _outer(unary_union([quiver, shafts, bow, *straps]))
    art = [_poly(_pts(shape), PALE), _poly(_pts(bow), OCHRE, SUMI, 0.25), _poly(_pts(quiver), OCHRE, SUMI, 0.3)]
    art += [_poly(_pts(s), CHA) for s in straps]
    art += [_line([(16 + 4 * i, 60), (48 - 4 * i, 92)], CHA, 0.4) for i in range(0, 3)]
    for i in range(5):
        x = 22 + 5.5 * i
        art += [_line([(x, 40), (x, 12)], SUMI, 0.5), _poly([(x - 2, 6), (x + 2, 6), (x + 2, 16), (x, 13), (x - 2, 16)], GOFUN, SUMI, 0.2)]
    art.append(_line([(9, 1), (11, 99)], SUMI, 0.2))
    return {"box": (50, 100), "outline": _pts(shape), "art": art, "foot": (32, 98), "top": (32, 45), "pocket": (32, 0.5)}


def _nobori():
    out = [(0, 0), (34, 0), (34, 92), (26, 100), (17, 94), (8, 100), (0, 92)]
    art = [_poly([(0, 0), (34, 0), (34, 10), (0, 10)], GOFUN), _poly([(0, 10), (34, 10), (34, 92), (26, 100), (17, 94), (8, 100), (0, 92)], MOMO),
           _line([(31, 12), (31, 90)], SHU, 0.8), _line([(4, 30), (30, 30)], GOFUN, 0.6), _line([(4, 60), (30, 60)], GOFUN, 0.6)]
    return {"box": (34, 100), "outline": out, "art": art}


def _hagoita():
    out = [(2, 0), (48, 0), (46, 75), (40, 82), (32, 84), (32, 120), (18, 120), (18, 84), (10, 82), (4, 75)]
    P = Polygon(out)
    cloud = [(6, 6), (44, 6), (43, 60), (38, 64), (32, 60), (25, 66), (18, 60), (12, 64), (7, 60)]
    art = [_poly(_pts(P.intersection(_box(0, 0, 50, 84))), PALE, SUMI, 0.3), _poly(_pts(P.intersection(_box(0, 84, 50, 120))), "#cf9f62", SUMI, 0.3),
           _poly(cloud, GOFUN, SUMI, 0.2), _poly([(14, 46), (25, 24), (36, 46), (34, 56), (16, 56)], OCHRE, SUMI, 0.3)]
    art += [_line([(17 + 3 * i, 50), (25, 28)], CHA, 0.3) for i in range(7)]
    for cx, cy in ((14, 14), (25, 11), (36, 14)):
        art += [_line([(cx, cy), (cx + 6 * math.cos(math.radians(a)), cy + 6 * math.sin(math.radians(a)))], ROKUSHO, 0.5) for a in range(200, 341, 28)]
    art += [_line([(10, 58), (10, 30)], ROKUSHO, 0.6), _line([(40, 58), (40, 32)], ROKUSHO, 0.6), _poly([(20, 70), (30, 70), (25, 78)], SHU)]
    return {"box": (50, 120), "outline": out, "art": art, "foot": (25, 120), "top": (25, 15), "core": True}


SHISHI_HEAD = [(2, 40), (10, 26), (24, 18), (30, 16), (22, 0), (38, 8), (44, 12), (48, 14), (56, 0), (60, 12), (66, 8), (78, 0), (76, 12), (88, 10),
               (98, 26), (95, 44), (92, 64), (66, 64), (60, 54), (40, 52), (20, 50), (5, 50)]
SHISHI_JAW = [(8, 54), (40, 56), (66, 50), (82, 50), (84, 60), (70, 68), (50, 72), (25, 70), (10, 62)]


def _shishi_art(head=True, jaw=True):
    art = []
    if head:
        art += [_poly(SHISHI_HEAD, SUMI), _poly([(44, 14), (56, 0), (60, 14)], OCHRE, SUMI, 0.2),
                _poly([(26, 17), (22, 1), (37, 9)], "#9a9a8a"), _poly([(64, 10), (78, 1), (76, 13)], "#9a9a8a"),
                _poly(_circle(62, 30, 6), GOFUN), _poly(_circle(60, 31, 2.6, 12), SUMI), _poly([(6, 44), (60, 48), (60, 53), (6, 50)], GOFUN)]
        art += [_line([(12 + 8 * i, 45), (12 + 8 * i, 51)], SUMI, 0.4) for i in range(6)]
        art += [_line([(50, 22), (70, 20), (84, 26)], OCHRE, 0.6), _line([(12, 34), (26, 30)], OCHRE, 0.6), _poly(_circle(8, 38, 2, 10), SHU)]
    if jaw:
        art += [_poly(SHISHI_JAW, SUMI), _poly([(10, 55), (60, 54), (60, 59), (12, 60)], GOFUN)]
        art += [_line([(16 + 8 * i, 54.5), (16 + 8 * i, 59.5)], SUMI, 0.4) for i in range(6)]
        art.append(_line([(20, 66), (50, 68)], OCHRE, 0.5))
    return art


def _shishi():
    out = _pts(_outer(unary_union([Polygon(SHISHI_HEAD), Polygon(SHISHI_JAW)])))
    return {"box": (100, 72), "outline": out, "art": _shishi_art(), "foot": (80, 66), "top": (80, 30), "jaw_pivot": (74, 56), "jaw_hole": (24, 62)}


def _harukoma():
    out = [(2, 34), (6, 24), (18, 14), (30, 6), (36, 0), (42, 6), (52, 6), (66, 12), (80, 22), (92, 38), (98, 60), (96, 80), (70, 80), (66, 62), (56, 48),
           (44, 44), (30, 46), (16, 48), (6, 46)]
    art = [_poly(out, GOFUN, SUMI, 0.3), _poly([(36, 2), (44, 6), (50, 2), (56, 9), (64, 7), (68, 15), (76, 15), (82, 26), (74, 21), (60, 15), (46, 11)], SUMI),
           _poly([(56, 20), (64, 18), (66, 26), (58, 28)], SUMI), _poly([(74, 36), (82, 34), (84, 44), (76, 44)], SUMI), _poly([(84, 54), (92, 52), (93, 60), (86, 62)], SUMI),
           _poly(_circle(28, 22, 2.2, 12), SUMI), _poly(_circle(8, 38, 1.5, 10), SUMI),
           _line([(10, 42), (30, 30), (42, 18)], SHU, 0.8), _line([(30, 30), (44, 42)], SHU, 0.8), _poly([(68, 64), (96, 66), (96, 80), (71, 80)], MOMO)]
    return {"box": (98, 80), "outline": out, "art": art, "foot": (84, 80), "top": (84, 45), "pivot": (72, 34), "weight": (84, 76)}


SHAPES = {
    "ame_tori": _ame_tori, "tori_ki": _tori_ki, "katana": _katana, "shitadashi": _shitadashi,
    "uchiwa_s": lambda: _uchiwa(True), "uchiwa_l": lambda: _uchiwa(False), "genji": _genji, "heike": _heike,
    "utsubo": _utsubo, "yumiya": _yumiya, "nobori": _nobori, "hagoita": _hagoita, "shishi": _shishi, "harukoma": _harukoma,
    "andon": None, "tokin": None,  # 筒と六角は箱の形でなく寸法から描く（_andon_parts・_tokin_parts）
}
# 形ごとに試せる付け方。棚卸しの見立てから、動き方の読みが割れる所を選んだ（仮説の記録が根拠と弱い所を持つ）。
HOLDS = {
    "ame_tori": ("glue", "nod"), "tori_ki": ("glue", "nod"), "genji": ("glue", "nod"), "heike": ("glue", "nod"),
    "harukoma": ("glue", "nod", "wheel"), "katana": ("sandwich", "slide"), "shitadashi": ("glue", "slide"),
    "uchiwa_s": ("glue", "sandwich"), "uchiwa_l": ("glue", "sandwich"), "hagoita": ("glue", "sandwich"),
    "yumiya": ("sandwich", "pocket"), "utsubo": ("sandwich", "pocket"), "nobori": ("glue", "turn"),
    "andon": ("glue", "hang"), "tokin": ("tie", "cone"), "shishi": ("glue", "jaw"),
}
TITLES = {"glue": "竹串を裏に貼る", "sandwich": "2 枚で竹串を挟む", "nod": "軸に掛けて揺らす", "slide": "差し込んで出し入れする",
          "pocket": "袋に矢を差す", "turn": "輪で竿に通す", "hang": "糸で吊る", "jaw": "顎を軸で開け閉めする", "wheel": "柄の先に車を付ける",
          "tie": "糸で額に結ぶ", "cone": "六角の笠に折る"}


def title(p):
    return TITLES[p["hold"]]


def spec():
    return {"template_id": ID, "defaults": DEFAULTS, "ranges": RANGES, "shape": tuple(SHAPES), "hold": HOLDS}


def check_range(p):
    out = []
    for k, v in p.items():
        if k == "shape":
            if v not in SHAPES:
                out.append(Failure("F5.range", k, f"{v} は知らない形"))
        elif k == "hold":
            # 付け方は形ごとに決まる。形に無い付け方は部品を作れないので、範囲の外として落とす。
            if v not in HOLDS.get(p.get("shape"), ()):
                out.append(Failure("F5.range", k, f"{v} は形 {p.get('shape')} の付け方 {HOLDS.get(p.get('shape'), ())} のどれでもない"))
        elif k not in RANGES:
            out.append(Failure("F5.range", k, "知らない寸法の名前"))
        elif not isinstance(v, (int, float)) or isinstance(v, bool) or not RANGES[k][0] <= v <= RANGES[k][1]:
            out.append(Failure("F5.range", k, f"{v} は範囲 {RANGES[k]} の外"))
    return out


# ---- 寸法に縮めた形 -----------------------------------------------------------------------------
def _scaled(p):
    """箱の単位の形を mm にする。式と刷る部品が同じ数を使うように、ここを 1 か所にする。"""
    d = SHAPES[p["shape"]]()
    W, H = d["box"]
    s = p["size"] / max(W, H)
    sc = lambda pts: [(x * s, y * s) for x, y in pts]
    out = {"s": s, "W": W * s, "H": H * s, "outline": sc(d["outline"]), "art": [{**a, "pts": sc(a["pts"])} for a in d["art"]]}
    for k in ("foot", "top", "pivot", "weight", "mouth", "jaw_pivot", "jaw_hole"):
        if k in d:
            out[k] = (d[k][0] * s, d[k][1] * s)
    for k in ("core", "pocket", "chin", "tongue"):
        if k in d:
            out[k] = d[k]
    if "tongue" in d:
        out["tongue"] = {**d["tongue"], "pts": sc(d["tongue"]["pts"])}
    if "chin" in d:
        out["chin"] = d["chin"] * s
    return out


def _paper_g(area_mm2, p, layers=1):
    return area_mm2 * p["paper_gsm"] / 1e6 * layers


def _drop(p):
    """首振りの重心が軸より下にある距離（mm、下が正）。紙は面の重心、重りは付ける所の点で数える。"""
    d = _scaled(p)
    poly = Polygon(d["outline"])
    m = _paper_g(poly.area, p)
    cy = (m * poly.centroid.y + p["weight_g"] * d["weight"][1]) / (m + p["weight_g"])
    return cy - d["pivot"][1]


def _jaw_offset(p):
    d = _scaled(p)
    jaw = Polygon([(x * d["s"], y * d["s"]) for x, y in SHISHI_JAW])
    return d["jaw_pivot"][0] - jaw.centroid.x


def _hole_room(outline, pt):
    return Polygon(outline).exterior.distance(Point(pt)) if Polygon(outline).contains(Point(pt)) else -1.0


def _andon_dims(p):
    ph = p["size"]
    return ph, ph * 0.5  # 行灯の縦と 1 面の幅。コマ 14 の図の比（幅は縦のほぼ半分）


def _stick_in(p):
    """竹串が紙に貼られる長さ（mm）。持つ所の長さを出すのにも使う。"""
    h = p["hold"]
    if p["shape"] == "andon":
        return _andon_dims(p)[0]
    if p["shape"] == "tokin":
        return 0.0
    d = _scaled(p)
    if p["shape"] == "nobori":
        return d["H"] * 0.92 if h == "glue" else _loop_span(p)
    if h in ("nod",):
        return 0.0
    # 斜めに貼る形（鳥の棒）もあるので、縦の差でなく 2 点の距離で数える。
    return math.dist(d["foot"], d["top"])


def _loop_ys(p):
    d = _scaled(p)
    n, L = int(p["loops"]), d["H"] * 0.9
    return [0.0] if n == 1 else [i * (L - 8) / (n - 1) for i in range(n)]


def _loop_span(p):
    ys = _loop_ys(p)
    return ys[-1] - ys[0] + 8


def _grip(p):
    """手で握れる竹串の長さ。芯にする形（刀・羽子板）は紙の柄を握るので、紙の柄の長さを返す。"""
    if p["shape"] == "tokin":
        return HAND
    d = None if p["shape"] == "andon" else _scaled(p)
    if d and d.get("core"):
        return HAND
    used = _stick_in(p)
    if p["shape"] == "andon" and p["hold"] == "hang":
        used = p["thread_len"] + _andon_dims(p)[0]
    if p["hold"] == "nod":
        used = d["H"] - d["pivot"][1] + 5  # 揺れる形の下の端まで、竹串の上を空ける
    return p["stick_len"] - used


def check_physics(p):
    out = []
    h, shape = p["hold"], p["shape"]
    if shape != "tokin":
        if h not in ("nod", "wheel", "jaw") and shape != "andon" and _stick_in(p) < STICK_IN:
            out.append(Failure("F5.prop", "竹串", f"紙に貼る長さが {_stick_in(p):.0f}mm で、振ると抜ける（{STICK_IN}mm 以上）"))
        if _grip(p) < HAND:
            out.append(Failure("F5.prop", "持つ所", f"竹串の握る所が {_grip(p):.0f}mm しかない（{HAND}mm 以上）"))
    if h == "nod":
        d = _scaled(p)
        drop = _drop(p)
        if drop < MIN_DROP:
            out.append(Failure("F5.prop", "重心", f"重心が軸より {drop:.1f}mm 下で、揺れて戻らない（{MIN_DROP}mm 以上）"))
        if _hole_room(d["outline"], d["pivot"]) < HOLE_MARGIN:
            out.append(Failure("F5.prop", "軸の穴", f"軸の穴から紙の端が近く、裂けやすい（{HOLE_MARGIN}mm 以上）"))
    if h == "slide":
        g = p["slide_gap"]
        if g < SLIDE_MIN:
            out.append(Failure("F5.prop", "すき間", f"すき間 {g}mm では紙がこすれて動かない（{SLIDE_MIN}mm 以上）"))
        if g > SLIDE_MAX:
            out.append(Failure("F5.prop", "すき間", f"すき間 {g}mm では抜け落ちる（{SLIDE_MAX}mm まで）"))
        if shape == "shitadashi":
            d = _scaled(p)
            x, y, w, hh = _slit(p)
            if not Polygon(d["outline"]).buffer(-3).contains(_box(x, y, x + w, y + hh)):
                out.append(Failure("F5.prop", "口の切れ目", "切れ目が顔の端に近すぎる"))
    if h == "pocket":
        d = _scaled(p)
        pw = d["W"] * d["pocket"][1]
        if TOOTHPICK - p["pocket_depth"] < ARROW_OUT:
            out.append(Failure("F5.prop", "袋", f"袋が深く、つまようじの矢が {TOOTHPICK - p['pocket_depth']:.0f}mm しか出ない（{ARROW_OUT}mm 以上）"))
        if pw < p["arrows"] * 4 + 4:
            out.append(Failure("F5.prop", "袋の口", f"袋の口 {pw:.0f}mm に矢 {p['arrows']:g} 本が入らない"))
        if p["pocket_depth"] > d["H"] - 10:
            out.append(Failure("F5.prop", "袋", "袋が形の下の端まで届く"))
    if h == "turn":
        need = math.pi * (p["stick_d"] + 1) + LOOP_GLUE
        if p["loop_len"] < need:
            out.append(Failure("F5.prop", "輪の帯", f"帯 {p['loop_len']}mm では竹串に巻いて貼れない（{need:.0f}mm 以上）"))
        if p["loops"] < 2:
            out.append(Failure("F5.prop", "輪の帯", "輪が 1 つでは、幟が竿の周りで傾く"))
    if h == "jaw" and _jaw_offset(p) < JAW_OFFSET:
        out.append(Failure("F5.prop", "顎", f"顎の重心が軸の前 {_jaw_offset(p):.1f}mm で、垂れて口が開かない（{JAW_OFFSET}mm 以上）"))
    if h == "jaw":
        d = _scaled(p)
        jaw = [(x * d["s"], y * d["s"]) for x, y in SHISHI_JAW]
        head = [(x * d["s"], y * d["s"]) for x, y in SHISHI_HEAD]
        if min(_hole_room(jaw, d["jaw_pivot"]), _hole_room(head, d["jaw_pivot"]), _hole_room(jaw, d["jaw_hole"])) < HOLE_MARGIN:
            out.append(Failure("F5.prop", "軸の穴", f"顎の穴から紙の端が近く、裂けやすい（{HOLE_MARGIN}mm 以上）"))
    if h == "wheel" and p["wheel_d"] / 2 < AXLE_UP + 3:
        out.append(Failure("F5.prop", "車", f"車が小さく、竹串の先が先に床に当たる（直径 {2 * (AXLE_UP + 3)}mm 以上）"))
    if h == "tie" or h == "cone":
        R = p["size"] / 2
        if R * math.sin(math.radians(60)) < 2 * HOLE_MARGIN + 6:
            out.append(Failure("F5.prop", "兜巾", "六角が小さく、糸の穴を開ける所が無い"))
    return out


def metrics(p):
    """台帳の式（F7）。版の間の変更の向きを、刷る部品と同じ式で数え直す。"""
    out = {"stick_in_mm": _stick_in(p), "grip_mm": _grip(p), "pivot_drop_mm": 0.0, "slide_gap_mm": 0.0, "jaw_offset_mm": 0.0}
    if p["hold"] == "nod":
        out["pivot_drop_mm"] = _drop(p)
    if p["hold"] == "slide":
        out["slide_gap_mm"] = p["slide_gap"]
    if p["hold"] == "jaw":
        out["jaw_offset_mm"] = _jaw_offset(p)
    return out


# ---- 部品 ---------------------------------------------------------------------------------------
def _clip(items, region):
    """絵を、刷ってよい所（外形の内・折り線と糊代の外）で切り抜く。手で取った点のはみ出しを刷る前に落とすため。"""
    out = []
    for it in items:
        if it["kind"] == "poly":
            g = Polygon(it["pts"]).buffer(0).intersection(region)
            for q in getattr(g, "geoms", [g]):
                if q.geom_type == "Polygon" and q.area > 0.05:
                    out.append({**it, "pts": _pts(q)})
        else:
            g = LineString(it["pts"]).intersection(region)
            for q in getattr(g, "geoms", [g]):
                if q.geom_type == "LineString" and q.length > 0.2:
                    out.append({**it, "pts": list(q.coords)})
    return out


def _region(outline, folds=(), glue=()):
    r = Polygon(outline).buffer(-0.25)
    for a, b in folds:
        r = r.difference(LineString([a, b]).buffer(0.25))
    for g in glue:
        r = r.difference(Polygon(g).buffer(0.1))
    return r


DARK = {SUMI, CHA, "#4a3a2e", "#5a2a20"}


def _label_xy(outline, label, art=()):
    """部品の番号を部品の中に置く。番号の箱が枠をまたぐと F5.text_overlap に落ちるので、入る所を探す。
    黒い字なので、墨や茶の絵の上は避ける（獅子頭の試し刷りで番号が墨に隠れた）。避けられない時だけ絵の上に置く。"""
    w, h = text_width(label, 2.8) + 0.4, 2.8 * 1.25 + 0.4
    P = Polygon(outline).buffer(-0.3)
    dark = unary_union([Polygon(a["pts"]).buffer(0) for a in art if a["kind"] == "poly" and a["fill"] in DARK] or [Point(-1e6, -1e6)])
    x0, y0, x1, y1 = P.bounds
    first = None
    y = y0
    while y + h <= y1:
        x = x0
        while x + w <= x1:
            b = _box(x, y, x + w, y + h)
            if P.contains(b):
                if not b.intersects(dark):
                    return (x + 0.2, y + 0.2)
                first = first or (x + 0.2, y + 0.2)
            x += 1
        y += 1
    return first or (x0, y0)


def _part(number, key, name, outline, art=(), valley=(), glue=(), holes=(), cuts=(), hide=False, label=None):
    """部品を作り、外形の左上を原点にそろえる。place が幅と高さだけで並べられるようにするため。"""
    mx, my = min(x for x, _ in outline), min(y for _, y in outline)
    sh = lambda pts: [(x - mx, y - my) for x, y in pts]
    region = _region(outline, valley, glue)
    art = _clip(list(art), region)
    label = label or str(number)
    o = sh(outline)
    sart = [{**a, "pts": sh(a["pts"])} for a in art]
    return Part(number, key, name, o, label_xy=_label_xy(o, label, sart), label=label,
                valley=[tuple(sh([a, b])) for a, b in valley], glue=[sh(g) for g in glue],
                holes=[(x - mx, y - my, r) for x, y, r in holes], cuts=[(x - mx, y - my, w, h) for x, y, w, h in cuts],
                art=sart, hide_folds=hide)


def _mirror(pts, W):
    return [(W - x, y) for x, y in pts]


def _flat_parts(p, d):
    """平らな形の表（と裏）。glue・sandwich・nod・wheel が使う。"""
    h = p["hold"]
    art = list(d["art"])
    holes = [(*d["pivot"], 1.5)] if h == "nod" else []
    if d.get("tongue") and h == "glue":
        art.append(d["tongue"])
    out = [_part(1, "front", "表", d["outline"], art, holes=holes)]
    if h == "sandwich":
        # 裏も絵にする。2 枚で挟む形は両面が見えるので、裏が白いと振った時に見た目が落ちる（本人の方針: 見た目で質を上げる）。
        W = d["W"]
        back = [{**a, "pts": _mirror(a["pts"], W)} for a in art]
        out.append(_part(2, "back", "裏", _mirror(d["outline"], W), back))
    return out


def _slit(p):
    d = _scaled(p)
    tw = 12 * d["s"]
    w = tw + p["slide_gap"]
    return (d["mouth"][0] - w / 2, d["mouth"][1] - 1.25, w, 2.5)


def _slide_parts(p, d):
    s = d["s"]
    if p["shape"] == "katana":
        # 刀身を鞘から抜く読み。刀身は 1 枚に竹串を裏から貼り、鞘は平たい筒にする。
        blade = [(6, 0), (14, 0), (14, 25), (19, 25), (19, 30), (14, 30), (14, 94), (10, 100), (6, 94), (6, 30), (1, 30), (1, 25), (6, 25)]
        blade = [(x * s, y * s) for x, y in blade]
        art = [a for a in d["art"][:6]] + [_poly([(6 * s, 30 * s), (14 * s, 30 * s), (14 * s, 94 * s), (10 * s, 100 * s), (6 * s, 94 * s)], GOFUN, SUMI, 0.25),
                                           _line([(10 * s, 31 * s), (10 * s, 95 * s)], "#9a9a8a", 0.3)]
        bw, L = 8 * s, 70 * s + 2
        sw = bw + p["slide_gap"]
        o = [(0, 0), (2 * sw, 0), (2 * sw + GLUE, 2), (2 * sw + GLUE, L - 2), (2 * sw, L), (0, L)]
        folds = [((sw, 0), (sw, L)), ((2 * sw, 0), (2 * sw, L))]
        glue = [[(2 * sw, 0), (2 * sw + GLUE, 2), (2 * sw + GLUE, L - 2), (2 * sw, L)]]
        sl_art = [_poly([(0, 0), (sw, 0), (sw, L), (0, L)], SUMI), _poly([(sw, 0), (2 * sw, 0), (2 * sw, L), (sw, L)], "#4a3a2e")]
        sl_art += [_poly(_circle(sw * (0.3 if k % 2 else 0.7), 4 + 5 * k, 0.9, 8), GOFUN) for k in range(int((L - 6) / 5))]
        return [_part(1, "blade", "刀身", blade, art), _part(2, "sleeve", "鞘", o, sl_art, valley=folds, glue=glue, hide=True)]
    # 舌出し: 口の切れ目から舌の帯を出し入れする読み。帯は顔の裏の輪で押さえる。
    x, y, w, hh = _slit(p)
    face = _part(1, "front", "顔", d["outline"], d["art"], cuts=[(x, y, w, hh)])
    tw = 12 * s
    L = (d["chin"] - d["mouth"][1]) + p["travel"] + 20
    tl = 14 * s
    strip = [(0, 0), (tw, 0), (tw, L), (0, L)]
    tongue = _poly([(0, 0), (tw, 0), (tw, tl - tw / 2)] + [(tw / 2 + tw / 2 * math.cos(math.radians(a)), tl - tw / 2 + tw / 2 * math.sin(math.radians(a))) for a in range(0, 181, 20)] + [(0, tl - tw / 2)], SHU, SUMI, 0.2)
    lw = w + 2 * GLUE
    loop = [(0, 0), (lw, 0), (lw, 8), (0, 8)]
    lglue = [[(0, 0), (GLUE, 0), (GLUE, 8), (0, 8)], [(lw - GLUE, 0), (lw, 0), (lw, 8), (lw - GLUE, 8)]]
    return [face, _part(2, "tongue", "舌の帯", strip, [tongue]), _part(3, "loop", "輪", loop, glue=lglue)]


def _pocket_parts(p, d):
    W = d["W"]
    cx = d["pocket"][0] * d["s"]
    pw = W * d["pocket"][1]
    P = Polygon(_mirror(d["outline"], W))
    top = min(y for _, y in d["outline"])
    hole = _box(W - cx - pw / 2, top - 1, W - cx + pw / 2, top + p["pocket_depth"])
    g = P.buffer(-0.3).difference(hole)
    glue = [_pts(q) for q in getattr(g, "geoms", [g]) if q.area > 1]
    out = [_part(1, "front", "表", d["outline"], d["art"]), _part(2, "back", "裏", _mirror(d["outline"], W), glue=glue)]
    for i in range(int(p["arrows"])):
        # 矢羽は帯を半分に折ってつまようじを挟む。折り目は白と墨の色の境に置く（本人の決定 d）。
        o = [(0, 0), (16, 0), (16, 12), (8, 9), (0, 12)]
        art = [_poly([(0, 0), (8, 0), (8, 9), (0, 12)], GOFUN), _poly([(8, 0), (16, 0), (16, 12), (8, 9)], SUMI)]
        out.append(_part(3 + i, f"fletch{i + 1}", f"矢羽 {i + 1}", o, art, valley=[((8, 0), (8, 9))], hide=True))
    return out


def _nobori_parts(p, d):
    art = d["art"]
    if p["hold"] == "glue":
        L = d["outline"][-1][1]
        o = [(-GLUE, 0)] + list(d["outline"]) + [(-GLUE, L)]
        glue = [[(-GLUE, 0), (0, 0), (0, L), (-GLUE, L)]]
        main = _part(1, "banner", "幟", o, art, valley=[((0, 0), (0, L))], glue=glue, hide=True)
    else:
        shape = Polygon(d["outline"])
        glue, tabs = [], []
        for y in _loop_ys(p):
            tabs.append(_box(-p["loop_len"], y, 0.01, y + 8))
            glue.append([(-p["loop_len"], y), (-p["loop_len"] + LOOP_GLUE, y), (-p["loop_len"] + LOOP_GLUE, y + 8), (-p["loop_len"], y + 8)])
        o = _pts(_outer(unary_union([shape, *tabs])))
        main = _part(1, "banner", "幟", o, art, glue=glue)
    # 竿の先の房。コマ 20 の図の竿の先に房がある。
    tassel = [(0, 0), (14, 0), (14, 6)] + [(14 - k, 14 if k % 2 == 0 else 8) for k in range(0, 15)] + [(0, 6)]
    tart = [_poly([(0, 0), (14, 0), (14, 6), (0, 6)], SHU), _poly([(0, 6), (14, 6), (14, 13)] + [(14 - k, 14 if k % 2 == 0 else 8) for k in range(1, 14)] + [(0, 13)], OCHRE)]
    return [main, _part(2, "tassel", "房", tassel, tart)]


def _andon_parts(p):
    ph, pw = _andon_dims(p)
    o = [(0, 0), (4 * pw, 0), (4 * pw + GLUE, 2), (4 * pw + GLUE, ph - 2), (4 * pw, ph), (0, ph)]
    folds = [((pw * i, 0), (pw * i, ph)) for i in range(1, 5)]
    glue = [[(4 * pw, 0), (4 * pw + GLUE, 2), (4 * pw + GLUE, ph - 2), (4 * pw, ph)]]
    art = []
    for i in range(4):
        x = pw * i
        # 面ごとに枠の色を朱と黄土で替える。折り線を刷らず、色の境で折るため（本人の決定 d）。
        art += [_poly([(x, 0), (x + pw, 0), (x + pw, ph), (x, ph)], SHU if i % 2 == 0 else OCHRE),
                _poly([(x + 3, 3), (x + pw - 3, 3), (x + pw - 3, ph - 3), (x + 3, ph - 3)], GOFUN)]
        if i % 2 == 0:
            art += [_line([(x + pw * 0.6, ph * 0.18), (x + pw * 0.45, ph * 0.4), (x + pw * 0.6, ph * 0.55), (x + pw * 0.4, ph * 0.8)], SUMI, 0.9)]
        else:
            art += [_line([(x + pw * 0.5, ph * 0.85), (x + pw * 0.5 + 6 * math.cos(math.radians(a)), ph * 0.85 - 14 * math.sin(math.radians(a)) * 0.9)], CHA, 0.4) for a in range(55, 130, 15)]
    r = ph * 0.18
    moon_g = Polygon(_circle(r, r, r, 32)).difference(Polygon(_circle(r * 1.45, r * 0.8, r * 0.9, 32)))
    moon = _outer(unary_union([moon_g, _box(r - 2.5, r * 1.6, r + 2.5, 2 * r + 12)]))
    out = [_part(1, "lantern", "行灯", o, art, valley=folds, glue=glue, hide=True),
           _part(2, "moon", "月", _pts(moon), [_poly(_pts(moon_g), OCHRE, SUMI, 0.3)])]
    if p["hold"] == "hang":
        bl = pw + 2 * GLUE
        bglue = [[(0, 0), (GLUE, 0), (GLUE, 8), (0, 8)], [(bl - GLUE, 0), (bl, 0), (bl, 8), (bl - GLUE, 8)]]
        out.append(_part(3, "bridge", "吊り橋", [(0, 0), (bl, 0), (bl, 8), (0, 8)], valley=[((GLUE, 0), (GLUE, 8)), ((bl - GLUE, 0), (bl - GLUE, 8))],
                         glue=bglue, holes=[(bl / 2, 4, HOLE_R)]))
    return out


def _tokin_parts(p):
    R = p["size"] / 2
    v = [(R + R * math.cos(math.radians(-90 + 60 * i)), R + R * math.sin(math.radians(-90 + 60 * i))) for i in range(6)]
    c = (R, R)
    inset = lambda pt, k: (c[0] + (pt[0] - c[0]) * k, c[1] + (pt[1] - c[1]) * k)
    hole_k = 1 - (HOLE_MARGIN + 3) / R
    rays = []
    for i in range(12):
        t = math.radians(-75 + 30 * i)
        rays.append(_line([(R + R * 0.22 * math.cos(t), R + R * 0.22 * math.sin(t)), (R + R * 0.7 * math.cos(t), R + R * 0.7 * math.sin(t))], SUMI, 0.9))
    dot = _poly(_circle(R, R, R * 0.08, 12), SHU)
    if p["hold"] == "tie":
        art = [_poly(v, PALE, SUMI, 0.3)] + rays + [dot]
        return [_part(1, "tokin", "兜巾", v, art, holes=[(*inset(v[1], hole_k), HOLE_R), (*inset(v[4], hole_k), HOLE_R)])]
    # 笠に折る読み: 上の 1 区切りを切り落とし、隣の区切りの糊代に重ねて浅い六角の笠にする。
    tab_tip = (v[0][0] + (v[5][0] - v[0][0]) * 0.35, v[0][1] + (v[5][1] - v[0][1]) * 0.35)
    o = [c, v[0], v[1], v[2], v[3], v[4], v[5], tab_tip]
    glue = [[c, tab_tip, v[0]]]
    folds = [(c, v[0])] + [(c, v[i]) for i in range(1, 5)]
    art = []
    for i in range(5):
        a, b = v[i], v[i + 1]
        art.append(_poly([c, a, b], PALE if i % 2 == 0 else "#d8c48e"))
        t = math.atan2((a[1] + b[1]) / 2 - R, (a[0] + b[0]) / 2 - R)
        for dt in (-0.2, 0.2):
            art.append(_line([(R + R * 0.25 * math.cos(t + dt), R + R * 0.25 * math.sin(t + dt)), (R + R * 0.7 * math.cos(t + dt), R + R * 0.7 * math.sin(t + dt))], SUMI, 0.9))
    art.append(dot)
    holes = [(*inset(v[2], hole_k), HOLE_R), (*inset(v[4], hole_k), HOLE_R)]
    return [_part(1, "tokin", "兜巾", o, art, valley=folds, glue=glue, holes=holes, hide=True)]


def parts(p):
    shape, h = p["shape"], p["hold"]
    if shape == "andon":
        return _andon_parts(p)
    if shape == "tokin":
        return _tokin_parts(p)
    d = _scaled(p)
    if shape == "nobori":
        return _nobori_parts(p, d)
    if h == "slide":
        return _slide_parts(p, d)
    if h == "pocket":
        return _pocket_parts(p, d)
    if h == "jaw":
        s = d["s"]
        sc = lambda pts: [(x * s, y * s) for x, y in pts]
        sca = lambda items: [{**a, "pts": sc(a["pts"])} for a in items]
        jp = d["jaw_pivot"]
        return [_part(1, "head", "頭", sc(SHISHI_HEAD), sca(_shishi_art(jaw=False)), holes=[(*jp, 1.5)]),
                _part(2, "jaw", "顎", sc(SHISHI_JAW), sca(_shishi_art(head=False)), holes=[(*jp, 1.5), (*d["jaw_hole"], HOLE_R)])]
    out = _flat_parts(p, d)
    if h == "wheel":
        r = p["wheel_d"] / 2
        for i in (0, 1):
            art = [_poly(_circle(r, r, r, 32), OCHRE, SUMI, 0.3), _poly(_circle(r, r, r * 0.62, 28), GOFUN)]
            art += [_line([(r + r * 0.15 * math.cos(math.radians(a)), r + r * 0.15 * math.sin(math.radians(a))),
                           (r + r * 0.6 * math.cos(math.radians(a)), r + r * 0.6 * math.sin(math.radians(a)))], CHA, 0.4) for a in range(0, 360, 60)]
            out.append(_part(2 + i, f"wheel{i + 1}", f"車 {i + 1}", _circle(r, r, r, 32), art, holes=[(r, r, 1.5)]))
    return out


def place(by_key, page, top, gap):
    """部品を左から並べ、入らなければ次の段へ送る。用意する物の文は、部品の下に頁の幅で置く。"""
    x, y, row_h = page.x0, top, 0.0
    for q in by_key.values():
        if x > page.x0 and x + q.width > page.x1:
            x, y, row_h = page.x0, y + row_h + gap, 0.0
        q.x, q.y = x - min(a for a, _ in q.outline), y - min(b for _, b in q.outline)
        x += q.width + gap
        row_h = max(row_h, q.height)
    return y + row_h + gap, page.x1 - page.x0, page.x0


# ---- 部品表・手順 -------------------------------------------------------------------------------
def _paper(p):
    return f"紙（厚さ 0.15mm 前後・{p['paper_gsm']}g/m² の見込み）"


def bom(p):
    paper, why = _paper(p), "家庭のプリンタで刷って作るため"
    rows = [{"number": q.number, "key": q.key, "name": q.name, "qty": 1, "material": paper, "substituted": True,
             "original_guess": "紙か木（絵からは読めない）", "reason": why} for q in parts(p)]
    h, shape = p["hold"], p["shape"]
    extra = []
    if shape != "tokin":
        extra.append(("stick", "柄", f"竹串（長さ {p['stick_len']}mm・太さ {p['stick_d']}mm）", "竹か木の柄（絵の棒から）", "家にあり、切らずに使えるため"))
    extra.append(("tape", "留め", "セロハンテープ", "不明", "のりより早く乾き、貼り直せるため"))
    if h in ("nod", "wheel", "jaw"):
        extra.append(("axle", "軸", "つまようじ 1 本とビーズ 1 個", "不明", "穴に通しやすく、抜け止めになるため"))
    if h == "nod" and p["weight_g"] > 0:
        extra.append(("weight", "重り", f"油粘土 {p['weight_g']:g}g", "不明", "量を変えて試しやすいため"))
    if h == "pocket":
        extra.append(("arrows", "矢", f"つまようじ {int(p['arrows'])} 本", "竹の矢", "家にあり、先が細いため"))
    if h in ("hang", "jaw", "tie", "cone"):
        extra.append(("thread", "糸", "木綿の糸（30cm ほど）" if h in ("hang", "jaw") else "木綿の糸か細い紐（80cm ほど）", "紐（絵からは読めない）", "家にあるため"))
    for i, (key, name, mat, orig, reason) in enumerate(extra):
        rows.append({"number": 20 + i, "key": key, "name": name, "qty": 1, "material": mat, "substituted": True, "original_guess": orig, "reason": reason})
    return rows


def materials(p):
    rows = bom(p)
    out = [f"{rows[0]['material']}を 1 枚", "のり、はさみ、定規"]
    out += [r["material"] for r in rows if r["number"] >= 20]
    if p["shape"] == "tokin":  # 柄の竹串が無い形で、糸を通す穴を竹串の先であける（#294）
        out.append("竹串（穴あけ）")
    if p["shape"] == "shitadashi" and p["hold"] == "slide":
        out.append("カッター（口の切れ目だけ。大人が切る）")
    return out


def steps(p):
    h, shape = p["hold"], p["shape"]
    # 穴の無い形に穴あけの文を出さない（#294）。形の名前でなく部品を見るので、形が増えても食い違わない。
    cut = "部品を実線で切る。穴は竹串の先であける" if any(q.holes for q in parts(p)) else "部品を実線で切る"
    out = ["刷った物差しに定規を当て、10cm か確かめる", cut]
    if shape == "andon":
        out += ["1 行灯を色の境で谷折りし、糊代で貼って四角い筒にする", "2 月の下の足を竹串の先にテープで巻く"]
        if h == "glue":
            out += ["竹串を筒の中の 1 つの角に通し、上と下をテープで留める"]
        else:
            out += ["3 吊り橋の両端を折り、筒の上の口の内側に貼る", f"穴に糸を通して結び、糸を {p['thread_len']}mm 残して竹串の月の下に結ぶ"]
        return out
    if shape == "tokin":
        if h == "cone":
            out += ["色の境で谷折りし、切り落とした所を糊代に重ねて貼る。浅い笠になる"]
        out += ["2 つの穴に糸を通し、額に当てて頭の後ろで結ぶ（きつく締めない）"]
        return out
    if shape == "nobori":
        if h == "glue":
            out += ["竹串の先から 1cm 下に、1 幟の糊代を巻いて貼る"]
        else:
            out += ["1 幟の輪の帯を、竹串に巻いて先の糊代で帯どうしを貼る。竹串には貼らない"]
        return out + ["2 房を丸めて、竹串の先に貼る"]
    if h == "slide" and shape == "katana":
        return out + ["2 鞘を色の境で谷折りし、糊代で貼って平たい筒にする", "竹串を 1 刀身の裏の真ん中にテープで貼る（先は切る）", "刀身を鞘に差し、抜いたり差したりする"]
    if h == "slide":
        return out + ["1 顔の口の切れ目を切る（カッターは大人がする）", "2 舌の帯を裏から切れ目に通し、朱の先を前に出す",
                      "3 輪を顔の裏の口の下に、両端の糊代で貼る。帯を輪に通す", "竹串を顔の裏の真ん中にテープで貼る"]
    if h == "pocket":
        return out + ["2 裏の糊代に のりを付け、1 表を重ねて貼る。上の口は貼らない", "竹串を裏の真ん中にテープで貼る",
                      "矢羽を色の境で折り、つまようじの頭を挟んで貼る", "矢を袋の口から差す"]
    if h == "sandwich":
        core = "（先は切る）" if _scaled(p).get("core") else ""
        return out + [f"竹串を 2 裏の真ん中に置き、テープで仮に留める{core}", "2 裏の全面に のりを付け、1 表を重ねて貼る"]
    if h == "nod":
        d = _scaled(p)
        out += ["つまようじを竹串の先に十字にテープで巻き、前へ 2cm 出す", "1 表の穴をつまようじに通し、先にビーズを付けて抜けないようにする"]
        if p["weight_g"] > 0:
            out.append(f"粘土 {p['weight_g']:g}g を表の下の端の近く（穴の {d['weight'][1] - d['pivot'][1]:.0f}mm 下）に貼る")
        return out
    if h == "jaw":
        return out + ["竹串を 1 頭の裏の後ろの端にテープで貼る", "2 顎を頭の前に重ね、軸の穴につまようじを通し、両端をテープで留める",
                      "顎の前の穴に糸を結び、糸の端を竹串を持つ手に持つ"]
    out += ["竹串を 1 表の裏の真ん中にテープで貼る"]
    if h == "wheel":
        out += [f"つまようじを竹串の下の端から {AXLE_UP}mm 上に十字にテープで巻く", "車をつまようじの両側に通し、先にビーズかテープで抜け止めをする"]
    return out


# 持ち物の玩具は「遊べたか」を見る。動いた角度や回数は測らない（U-25 の方針に合わせる）。
# 「少し遊べた」は出来ばえの段に読めるので置かない（#146）。どのくらい遊べたかは感想の欄に言葉で書ける。
RESULTS = ("遊べた", "遊べない", "わからない")
# 前の札で残った記録の受け口。今の札のどれに当たるかだけを持ち、紙にも画面にも出さない。
OLD_RESULTS = {"少し遊べた": "遊べた"}


def measures(p):
    return {"predict": "振ったり動かしたりすると、どうなると思いますか（言葉か絵で）", "rows": [[("動かし方（振る・かざす・引く）", 40)]]}


def diagram(x, y, w, h, p):
    """横から見た組み上がりの略図。竹串と紙の形と、動く所の軸だけを描く。仕組みの答えは描かない（紙で確かめる所なので。J-013）。"""
    shape, hold = p["shape"], p["hold"]
    if shape == "andon":
        ph, pw = _andon_dims(p)
        W, Hp = pw, ph + (p["thread_len"] if hold == "hang" else 0) + ph * 0.4
    elif shape == "tokin":
        W = Hp = p["size"]
    else:
        d = _scaled(p)
        W, Hp = d["W"], d["H"]
    total = Hp + (0 if shape == "tokin" else p["stick_len"] * 0.5)
    s = min(w / max(W, 1), h / total)
    ox, oy = x + (w - W * s) / 2, y
    out = []
    if shape == "tokin":
        out.append({"kind": "rect", "x": ox, "y": oy, "w": W * s, "h": W * s * 0.866})
        return out
    if shape == "andon":
        top = oy + ph * 0.4 * s
        if hold == "hang":
            out.append({"kind": "line", "x1": ox + W * s / 2, "y1": top, "x2": ox + W * s / 2, "y2": top + p["thread_len"] * s, "dash": "1,0.6"})
            top += p["thread_len"] * s
            sx = ox + W * s / 2
        else:
            sx = ox + 1
        out.append({"kind": "rect", "x": ox, "y": top, "w": W * s, "h": ph * s})
        out.append({"kind": "line", "x1": sx, "y1": oy + ph * 0.3 * s, "x2": sx, "y2": y + h})
        return out
    pts = [(ox + a * s, oy + b * s) for a, b in d["outline"]]
    out.append({"kind": "poly", "pts": pts, "fill": "white", "sw": 0.25})
    if shape == "nobori":
        out.append({"kind": "line", "x1": ox, "y1": oy - 2, "x2": ox, "y2": y + h})
        return out
    if hold == "nod":
        px, py = ox + d["pivot"][0] * s, oy + d["pivot"][1] * s
        out.append({"kind": "line", "x1": px, "y1": py, "x2": px, "y2": y + h, "dash": "1,0.6"})
        out.append({"kind": "rect", "x": px - 1, "y": py - 1, "w": 2, "h": 2})
        return out
    fx, fy = ox + d["foot"][0] * s, oy + d["foot"][1] * s
    tx, ty = ox + d["top"][0] * s, oy + d["top"][1] * s
    out.append({"kind": "line", "x1": tx, "y1": ty, "x2": fx, "y2": fy, "dash": "1,0.6"})
    if not d.get("core"):
        out.append({"kind": "line", "x1": fx, "y1": fy, "x2": fx, "y2": y + h})
    if hold == "jaw":
        jx, jy = ox + d["jaw_pivot"][0] * s, oy + d["jaw_pivot"][1] * s
        out.append({"kind": "rect", "x": jx - 1, "y": jy - 1, "w": 2, "h": 2})
    if hold == "wheel":
        r = p["wheel_d"] / 2 * s
        out.append({"kind": "rect", "x": fx - r, "y": y + h - 2 * r, "w": 2 * r, "h": 2 * r})
    return out
