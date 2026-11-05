"""雛形 string_pull: 糸か棒で動かす紙の人形と、平らな凧。『江都二色』の pull_string の玩具を 1 本の雛形に乗せる（線の契約、11-04）。

形は 2 つ。人形は「台紙＋腕木（動く部品）」で、腕木を竹串か楊枝の軸で台紙に留め、糸を引く・棒で押す・揺らすで動かす。
凧は「帆＋骨＋糸目」で、尾を付ける形と横骨を反らせる形を分ける。玩具ごとの違いは寸法と絵の形（shape）で出す。
どの読みも絵と棚卸しの見立てからの推測で、実物では確かめていない。Claude が変えてよいのは ALLOWED の名前の値だけ。
"""
import math

from shapely.geometry import LineString, Point, Polygon, box

from ..model import Failure, Part

ID = "string_pull"
SHEET_SET = "string-v1"
# 仮説を分ける寸法。人形は動かし方（pull・push・sway）、凧は揚げ方の釣り合いの取り方（tail・bow）で読みが分かれるため。
# 手順の紙の図の説明（instructions.compose_sheet）。御来迎の筒の言葉を刷らないため。
DIAGRAM_CAPTION = "引いた時の動き（破線は後）"
HYP_KEY = "rig"
LEVER_RIGS = ("pull", "push", "sway")
KITE_RIGS = ("tail", "bow")
LEVER_SHAPES = ("saru", "kometsuki", "ebako", "tori", "sumo", "yamaneko", "noborizaru", "odori", "shishi")
KITE_SHAPES = ("raijin", "sode", "mimizuku")
DEFAULTS = {
    "rig": "pull", "shape": "kometsuki",
    # 人形: 台紙の大きさ、台紙の軸の位置、腕木の長さと幅、腕木の左の端から軸まで、軸から糸の穴まで、引く（押す）量、糸の通し穴の下がり
    "board_w": 90, "board_h": 110, "pivot_x": 40, "pivot_y": 50,
    "arm_len": 80, "arm_w": 30, "pivot_at": 20, "pull_arm": 12, "stroke": 10, "guide_drop": 40,
    # 凧: 帆の幅と高さ、横骨の位置（上から）、糸目の上と下（上から）、結び目の位置（上から）と帆からの高さ、尾の長さ、横骨の反り
    "sail_w": 120, "sail_h": 160, "spar_y": 40, "bridle_top": 25, "bridle_bottom": 120, "tow_at": 55, "bridle_h": 90,
    "tail_len": 520, "bow_depth": 12,
    # 紙の面密度は見込み。凧は軽い紙ほど揚がりやすいので、刷る紙を量ったら置き換える。
    "paper_gsm": 80,
}
RANGES = {
    "board_w": (40, 150), "board_h": (50, 150), "pivot_x": (5, 145), "pivot_y": (5, 145),
    "arm_len": (25, 150), "arm_w": (10, 60), "pivot_at": (3, 100), "pull_arm": (2, 60), "stroke": (2, 60), "guide_drop": (5, 140),
    "sail_w": (60, 150), "sail_h": (80, 185), "spar_y": (5, 180), "bridle_top": (3, 180), "bridle_bottom": (3, 185), "tow_at": (3, 180),
    "bridle_h": (30, 250), "tail_len": (0, 900), "bow_depth": (0, 40), "paper_gsm": (30, 250),
}
ALLOWED = ("pivot_at", "pull_arm", "stroke", "guide_drop", "arm_len", "arm_w", "spar_y", "bridle_top", "bridle_bottom", "tow_at", "bridle_h", "tail_len", "bow_depth", "paper_gsm")
PARAM_NAMES = {"pivot_at": "腕木の端から軸まで", "pull_arm": "軸から糸の穴まで", "stroke": "引く量", "tow_at": "糸目の結び目の位置", "tail_len": "尾の長さ", "bow_depth": "横骨の反り"}

HOLE_R = 1.2  # 楊枝が通る穴。軸と糸の穴で同じ大きさにして、道具を 1 本で済ませる
HOLE_MARGIN = 3  # 穴から紙の端まで。これより狭いと、引いた時に紙が裂けやすい（pivot_counterweight の 4 は厚い胴の値で、腕木は台紙に裏打ちする前提）
MIN_ARM = 6  # 軸から糸の穴まで。これより短いと、指の引きの細かさで角度を決められない
MIN_SWING, MAX_SWING = 15, 100  # 動いたと見える角度と、裏返らずに戻れる角度
MIN_OFFSET = 3  # 腕木の重心が軸からずれる量。これより小さいと、離しても重さで戻らない（揺れない）
TAIL_SEG = 150  # 尾の 1 本の長さ。A4 の縦に並べられる長さ
TAIL_W, TAIL_OVER = 10, 10  # 尾の幅と、つなぐ時の重ね
MIN_TAIL = 3  # 尾は帆の高さの何倍か。凧の作り方の目安で、確かめるのは揚げた時
BOW_MIN, BOW_MAX = 0.05, 0.2  # 反りは横骨の長さの割合。浅いと尾のない凧が回り、深いと帆が風を受けない（目安）
SPAR_MIN = 0.5  # 横骨が帆の幅のどれだけを渡るか。狭い所に通すと帆の端がはためく

# 江戸の色（朱・藍・黄土・墨・胡粉）と、絵に要る茶・鼠・肌・金。
SHU, AI, OUDO, SUMI, GOFUN = "#c8442b", "#34507a", "#c9a05a", "#2b2622", "#f3ecdc"
CHA, NEZU, HADA, KIN, USUKI, KOGE = "#8a5a3a", "#9a958c", "#ecd3b0", "#d8b04a", "#e3cf9c", "#a8783e"

TITLES = {"pull": "糸を引いて動かす", "push": "棒で押して動かす", "sway": "揺らして動かす", "tail": "尾を付けて揚げる", "bow": "横骨を反らせて揚げる"}


def is_kite(p):
    return p["rig"] in KITE_RIGS


def title(p):
    return TITLES[p["rig"]]


def spec():
    return {"template_id": ID, "defaults": DEFAULTS, "ranges": RANGES, "rig": LEVER_RIGS + KITE_RIGS, "shape": LEVER_SHAPES + KITE_SHAPES}


def check_range(p):
    out = []
    for k, v in p.items():
        if k == "rig":
            if v not in LEVER_RIGS + KITE_RIGS:
                out.append(Failure("F5.range", k, f"{v} は {LEVER_RIGS + KITE_RIGS} のどれでもない"))
        elif k == "shape":
            if v not in LEVER_SHAPES + KITE_SHAPES:
                out.append(Failure("F5.range", k, f"{v} は知らない絵の形"))
        elif k not in RANGES:
            out.append(Failure("F5.range", k, "知らない寸法の名前"))
        elif not isinstance(v, (int, float)) or isinstance(v, bool) or not RANGES[k][0] <= v <= RANGES[k][1]:
            out.append(Failure("F5.range", k, f"{v} は範囲 {RANGES[k]} の外"))
    if not out:
        # 凧の絵に人形の動かし方を付けると、刷る部品と手順が食い違う。組み合わせも範囲の一部として落とす。
        kite_shape = p["shape"] in KITE_SHAPES
        if kite_shape != is_kite(p):
            out.append(Failure("F5.range", "rig", f"絵 {p['shape']} に動かし方 {p['rig']} は組めない"))
    return out


# ---- 形（絵を見て手で取った点。0〜1 の割合で持ち、寸法で伸ばす。原図の画素は使っていない） ----

def _u(pts, w, h, ox=0.0, oy=0.0):
    return [(ox + x * w, oy + y * h) for x, y in pts]


def _ellipse(cx, cy, rx, ry, n=16):
    return [(cx + rx * math.cos(2 * math.pi * i / n), cy + ry * math.sin(2 * math.pi * i / n)) for i in range(n)]


# 腕木の外形。左の端が軸の後ろ（糸を付ける短い方）、右が動いて見える長い方。どれも軸の通る帯（縦の真ん中）を太く取る。
MOVER = {
    "saru": [(0, 0.3), (0.55, 0.28), (0.62, 0.1), (0.78, 0.0), (0.92, 0.08), (1.0, 0.3), (0.96, 0.55), (0.86, 0.7), (0.7, 0.72), (0.55, 0.7), (0, 0.7)],
    "kometsuki": [(0, 0.2), (0.35, 0.18), (0.7, 0.22), (0.8, 0.04), (0.96, 0.06), (1.0, 0.36), (0.94, 0.62), (0.8, 0.66), (0.72, 0.62), (0.66, 1.0), (0.58, 1.0), (0.58, 0.72), (0.3, 0.8), (0, 0.8)],
    "ebako": [(0, 0.25), (0.4, 0.22), (0.75, 0.15), (1.0, 0.25), (1.0, 0.85), (0.8, 0.95), (0.55, 0.8), (0.4, 0.78), (0, 0.75)],
    "tori": [(0, 0.35), (0.3, 0.32), (0.55, 0.3), (0.7, 0.1), (0.8, 0.0), (0.88, 0.08), (0.92, 0.2), (1.0, 0.32), (0.92, 0.42), (0.84, 0.6), (0.7, 0.8), (0.45, 0.85), (0.3, 0.7), (0, 0.68)],
    "sumo": [(0, 0.28), (0.3, 0.25), (0.55, 0.2), (0.62, 0.05), (0.75, 0.0), (0.85, 0.08), (0.88, 0.22), (1.0, 0.3), (1.0, 0.62), (0.88, 0.72), (0.62, 0.8), (0.3, 0.76), (0, 0.72)],
    "yamaneko": [(0, 0.25), (0.3, 0.2), (0.5, 0.05), (0.62, 0.15), (0.75, 0.3), (1.0, 0.55), (0.75, 0.72), (0.5, 0.8), (0.3, 0.78), (0, 0.75)],
    "noborizaru": [(0, 0.3), (0.35, 0.28), (0.42, 0.05), (0.55, 0.0), (0.72, 0.12), (0.7, 0.3), (0.85, 0.35), (1.0, 0.6), (0.92, 0.95), (0.7, 1.0), (0.5, 0.85), (0.35, 0.72), (0, 0.7)],
    "odori": [(0, 0.3), (0.45, 0.25), (0.8, 0.2), (0.86, 0.0), (1.0, 0.0), (1.0, 0.45), (0.86, 0.45), (0.8, 0.75), (0.45, 0.75), (0, 0.7)],
    "shishi": [(0, 0.25), (0.25, 0.2), (0.4, 0.3), (0.95, 0.15), (1.0, 0.3), (0.98, 0.6), (0.6, 0.85), (0.35, 0.8), (0.25, 0.75), (0, 0.75)],
}


def _mover_art(shape, w, h):
    """腕木の絵。外形を塗り、その上に色の面と墨の線を重ねる。はみ出しは _clip が外形で切る。"""
    s = lambda pts: _u(pts, w, h)
    if shape == "saru":  # 腕と、腕に付いた棒（帯金具の所が軸）
        return [("poly", s(MOVER[shape]), NEZU), ("poly", s([(0, 0.3), (0.58, 0.3), (0.58, 0.7), (0, 0.7)]), OUDO),
                ("poly", s([(0.62, 0.1), (0.78, 0.0), (0.92, 0.08), (1.0, 0.3), (0.96, 0.55), (0.78, 0.5), (0.66, 0.35)]), CHA),
                ("line", s([(0.1, 0.3), (0.1, 0.7)]), SUMI), ("line", s([(0.45, 0.3), (0.45, 0.7)]), SUMI),
                ("line", s([(0.62, 0.65), (0.8, 0.58)]), SUMI), ("line", s([(0.7, 0.68), (0.9, 0.6)]), SUMI)]
    if shape == "kometsuki":  # 前かがみの上半身。腰に茶の帯、右の端が頭
        return [("poly", s(MOVER[shape]), HADA), ("poly", s([(0, 0.2), (0.22, 0.19), (0.22, 0.8), (0, 0.8)]), CHA),
                ("poly", s([(0.22, 0.19), (0.3, 0.19), (0.3, 0.8), (0.22, 0.8)]), SHU),
                ("poly", s([(0.8, 0.04), (0.96, 0.06), (1.0, 0.3), (0.86, 0.24)]), SUMI), ("line", s([(0.62, 0.72), (0.62, 0.98)]), KOGE)]
    if shape == "ebako":  # 口元へ上げる袖。藍の地に朱の模様
        return [("poly", s(MOVER[shape]), AI), ("poly", s([(0.75, 0.15), (1.0, 0.25), (1.0, 0.45), (0.8, 0.4)]), HADA)]\
            + [("poly", s([(x, 0.4), (x + 0.08, 0.4), (x + 0.08, 0.5), (x, 0.5)]), SHU) for x in (0.15, 0.4, 0.6)]
    if shape == "tori":  # ついばむ雄鶏。赤茶の体、朱の鶏冠
        return [("poly", s(MOVER[shape]), "#a4472c"), ("poly", s([(0.72, 0.08), (0.8, 0.0), (0.88, 0.08), (0.84, 0.15)]), SHU),
                ("poly", s([(0.92, 0.2), (1.0, 0.32), (0.92, 0.34)]), KIN), ("poly", s(_ellipse(0.86, 0.22, 0.02, 0.04, 8)), SUMI)]\
            + [("line", s([(x, 0.4), (x + 0.15, 0.72)]), "#6e2a18") for x in (0.35, 0.45, 0.55)]
    if shape == "sumo":  # 組み付く力士。肌に朱の褌
        return [("poly", s(MOVER[shape]), HADA), ("poly", s([(0.0, 0.28), (0.3, 0.25), (0.3, 0.76), (0.0, 0.72)]), OUDO),
                ("poly", s([(0.55, 0.45), (0.75, 0.45), (0.75, 0.62), (0.55, 0.62)]), SHU),
                ("poly", s([(0.62, 0.05), (0.75, 0.0), (0.85, 0.08), (0.8, 0.12)]), SUMI)]
    if shape == "yamaneko":  # 細い鼻先の頭
        return [("poly", s(MOVER[shape]), USUKI), ("poly", s([(0.5, 0.05), (0.62, 0.15), (0.55, 0.25)]), CHA),
                ("poly", s(_ellipse(0.6, 0.42, 0.025, 0.06, 8)), SUMI), ("poly", s(_ellipse(0.97, 0.55, 0.02, 0.05, 8)), SUMI),
                ("line", s([(0.3, 0.3), (0.45, 0.5)]), KOGE), ("line", s([(0.2, 0.3), (0.3, 0.6)]), KOGE)]
    if shape == "noborizaru":  # 笠をかぶった猿。茶の毛と蓑
        return [("poly", s(MOVER[shape]), CHA), ("poly", s([(0.42, 0.05), (0.55, 0.0), (0.72, 0.12), (0.7, 0.3), (0.4, 0.3)]), OUDO),
                ("poly", s([(0.72, 0.3), (0.85, 0.35), (0.8, 0.55), (0.7, 0.5)]), HADA)]\
            + [("line", s([(x, 0.55), (x - 0.05, 0.95)]), SUMI) for x in (0.6, 0.7, 0.8)]
    if shape == "odori":  # 広げた両の袖。右の端に玉
        return [("poly", s(MOVER[shape]), SHU), ("poly", s([(0, 0.3), (0.45, 0.25), (0.45, 0.75), (0, 0.7)]), AI),
                ("poly", s([(0.86, 0.0), (1.0, 0.0), (1.0, 0.45), (0.86, 0.45)]), GOFUN), ("line", s([(0.45, 0.3), (0.45, 0.7)]), SUMI)]
    if shape == "shishi":  # 下あご。朱の口と胡粉の歯
        return [("poly", s(MOVER[shape]), KIN), ("poly", s([(0.4, 0.3), (0.95, 0.15), (0.95, 0.4), (0.45, 0.5)]), SHU)]\
            + [("poly", s([(x, 0.3 - (x - 0.4) * 0.27), (x + 0.07, 0.29 - (x - 0.4) * 0.27), (x + 0.035, 0.42 - (x - 0.4) * 0.27)]), GOFUN) for x in (0.5, 0.62, 0.74, 0.84)]
    raise KeyError(shape)


def _board_art(shape, w, h, pu, pv):
    """台紙の絵。pu, pv は軸の位置の割合で、軸の座（柱・帯）は軸に合わせて描く。地は胡粉。"""
    s = lambda pts: _u(pts, w, h)
    ground = [("poly", s([(0, 0), (1, 0), (1, 1), (0, 1)]), GOFUN)]
    if shape in ("saru", "noborizaru"):  # 斜めの竹。節は墨の線
        pole = [(0.0, 0.88), (0.12, 1.0), (1.0, 0.12), (0.88, 0.0)]
        art = ground + [("poly", s(pole), USUKI if shape == "saru" else OUDO)]
        art += [("line", s([(0.06 + t, 0.94 - t - 0.06), (0.06 + t + 0.06, 0.94 - t)]), KOGE) for t in (0.2, 0.45, 0.7)]
        if shape == "saru":  # 竹に取り付く猿の胴と、留めの帯
            art += [("poly", s(_ellipse(pu + 0.05, pv + 0.12, 0.16, 0.14)), NEZU), ("poly", s([(pu - 0.12, pv - 0.04), (pu + 0.12, pv - 0.04), (pu + 0.12, pv + 0.04), (pu - 0.12, pv + 0.04)]), NEZU)]
            art += [("poly", s(_ellipse(pu + 0.2, pv - 0.02, 0.07, 0.06)), CHA)]
        else:
            art += [("poly", s([(pu - 0.1, pv - 0.04), (pu + 0.1, pv - 0.04), (pu + 0.1, pv + 0.04), (pu - 0.1, pv + 0.04)]), CHA)]
        return art
    if shape == "kometsuki":  # 台の板、臼、腰を受ける 2 本の柱と脚
        return ground + [("poly", s([(0.02, 0.86), (0.98, 0.86), (0.98, 0.97), (0.02, 0.97)]), OUDO), ("line", s([(0.02, 0.86), (0.98, 0.86)]), KOGE),
                         ("poly", s([(0.66, 0.58), (0.92, 0.58), (0.92, 0.86), (0.66, 0.86)]), KOGE), ("poly", s([(0.68, 0.58), (0.9, 0.58), (0.9, 0.63), (0.68, 0.63)]), USUKI),
                         ("poly", s([(0.74, 0.3), (0.84, 0.3), (0.84, 0.6), (0.74, 0.6)]), OUDO),
                         ("poly", s([(pu - 0.14, pv + 0.08), (pu - 0.05, pv + 0.08), (pu - 0.05, 0.86), (pu - 0.14, 0.86)]), HADA),
                         ("poly", s([(pu - 0.06, pv + 0.06), (pu + 0.06, pv + 0.06), (pu + 0.04, 0.86), (pu - 0.04, 0.86)]), HADA)]\
            + [("poly", s([(pu + d - 0.015, pv - 0.06), (pu + d + 0.015, pv - 0.06), (pu + d + 0.015, 0.86), (pu + d - 0.015, 0.86)]), CHA) for d in (-0.07, 0.07)]
    if shape == "ebako":  # 木の枠、胡粉の中の板、朱の雲の帯、袖を当てる人物
        art = [("poly", s([(0, 0), (1, 0), (1, 1), (0, 1)]), OUDO), ("poly", s([(0.12, 0.08), (0.88, 0.08), (0.88, 0.92), (0.12, 0.92)]), GOFUN)]
        art += [("line", s([(0.16, y), (0.84, y)]), SHU) for y in (0.14, 0.17, 0.83, 0.86)]
        art += [("poly", s([(pu - 0.12, pv - 0.05), (pu + 0.14, pv - 0.05), (pu + 0.2, 0.8), (pu - 0.16, 0.8)]), AI),
                ("poly", s(_ellipse(pu + 0.02, pv - 0.14, 0.08, 0.08)), HADA), ("poly", s([(pu - 0.06, pv - 0.26), (pu + 0.1, pv - 0.26), (pu + 0.08, pv - 0.2), (pu - 0.04, pv - 0.2)]), SUMI)]
        return art
    if shape == "tori":  # 藁苞と雌鶏
        art = ground + [("poly", s([(0.0, 0.72), (1.0, 0.68), (1.0, 0.92), (0.0, 0.95)]), USUKI)]
        art += [("line", s([(0.02, y), (0.98, y - 0.03)]), KOGE) for y in (0.77, 0.82, 0.87, 0.92)]
        art += [("poly", s([(0.05, 0.7), (0.1, 0.45), (0.22, 0.4), (0.3, 0.5), (0.4, 0.55), (0.42, 0.7)]), "#a4472c"),
                ("poly", s([(0.08, 0.42), (0.12, 0.38), (0.16, 0.42)]), SHU), ("poly", s([(pu - 0.03, pv), (pu + 0.03, pv), (pu + 0.03, 0.7), (pu - 0.03, 0.7)]), KIN)]
        return art
    if shape == "sumo":  # 立つ力士と、2 人をつなぐ板の根元
        return ground + [("poly", s([(0.1, 0.12), (0.3, 0.12), (0.34, 0.6), (0.3, 0.95), (0.22, 0.95), (0.2, 0.7), (0.16, 0.95), (0.08, 0.95), (0.06, 0.6)]), HADA),
                         ("poly", s(_ellipse(0.2, 0.1, 0.08, 0.07)), HADA), ("poly", s([(0.12, 0.05), (0.28, 0.05), (0.26, 0.09), (0.14, 0.09)]), SUMI),
                         ("poly", s([(0.07, 0.52), (0.33, 0.52), (0.33, 0.62), (0.07, 0.62)]), SHU),
                         ("poly", s([(0.28, pv - 0.04), (pu + 0.05, pv - 0.04), (pu + 0.05, pv + 0.04), (0.28, pv + 0.04)]), OUDO)]
    if shape == "yamaneko":  # 逆立つ毛の胴と、輪の尾
        art = ground + [("poly", s([(0.05, 0.6), (0.2, 0.3), (0.5, 0.15), (0.85, 0.05), (0.95, 0.3), (0.8, 0.55), (0.5, 0.7), (0.2, 0.72)]), USUKI)]
        art += [("line", s([(0.25 + 0.1 * i, 0.5 - 0.05 * i), (0.3 + 0.12 * i, 0.25 - 0.06 * i)]), KOGE) for i in range(6)]
        ring = _ellipse(0.55, 0.85, 0.3, 0.1, 20)
        art += [("line", s(ring + ring[:1]), SUMI)]
        return art
    if shape == "odori":  # 流し釉の壺と台。人形の胴は台紙に描く
        art = ground + [("poly", s([(0.05, 0.86), (0.95, 0.86), (0.95, 0.98), (0.05, 0.98)]), OUDO),
                        ("poly", s([(0.25, 0.4), (0.75, 0.4), (0.85, 0.6), (0.72, 0.86), (0.28, 0.86), (0.15, 0.6)]), USUKI),
                        ("poly", s([(0.25, 0.4), (0.75, 0.4), (0.8, 0.5), (0.2, 0.5)]), SUMI)]
        art += [("poly", s([(x, 0.5), (x + 0.06, 0.5), (x + 0.03, 0.62)]), SUMI) for x in (0.24, 0.36, 0.48, 0.6, 0.7)]
        art += [("poly", s([(pu - 0.08, pv - 0.02), (pu + 0.08, pv - 0.02), (pu + 0.1, 0.4), (pu - 0.1, 0.4)]), SHU),
                ("poly", s(_ellipse(pu, pv - 0.08, 0.06, 0.05)), HADA)]
        return art
    if shape == "shishi":  # 金のたてがみ、朱の顔、下へ伸びる棒
        art = ground + [("poly", s([(0.42, 0.45), (0.58, 0.45), (0.58, 1.0), (0.42, 1.0)]), OUDO),
                        ("poly", s([(0.1, 0.1), (0.5, 0.02), (0.9, 0.12), (0.95, 0.35), (0.6, pv + 0.02), (0.1, pv + 0.02)]), KIN),
                        ("poly", s([(0.05, pv - 0.16), (0.55, pv - 0.2), (0.6, pv + 0.02), (0.05, pv + 0.02)]), SHU),
                        ("poly", s(_ellipse(0.32, pv - 0.2, 0.06, 0.04)), GOFUN), ("poly", s(_ellipse(0.32, pv - 0.2, 0.02, 0.02, 8)), SUMI)]
        art += [("line", s([(0.2 + 0.12 * i, 0.04), (0.25 + 0.12 * i, 0.15)]), KOGE) for i in range(6)]
        return art
    raise KeyError(shape)


SAIL = {
    "raijin": [(0, 0), (1, 0), (1, 1), (0, 1)],
    # 袖凧: 上が左右に張った袖、下が身頃
    "sode": [(0, 0), (1, 0), (1, 0.45), (0.78, 0.45), (0.78, 1), (0.22, 1), (0.22, 0.45), (0, 0.45)],
    # 木菟の凧: 羽を広げた形
    "mimizuku": [(0.5, 0), (0.64, 0.04), (0.72, 0.13), (1.0, 0.2), (0.95, 0.46), (0.76, 0.55), (0.7, 0.86), (0.58, 1.0), (0.42, 1.0), (0.3, 0.86), (0.24, 0.55), (0.05, 0.46), (0, 0.2), (0.28, 0.13), (0.36, 0.04)],
}


def _sail_art(shape, w, h):
    s = lambda pts: _u(pts, w, h)
    if shape == "raijin":  # 太鼓の輪を背負う雷神と雲
        art = [("poly", s(SAIL[shape]), GOFUN)]
        art += [("poly", s(_ellipse(0.5 + 0.3 * math.cos(a), 0.36 + 0.24 * math.sin(a), 0.055, 0.042)), SHU if i % 2 else OUDO)
                for i, a in enumerate(2 * math.pi * k / 8 + math.pi / 8 for k in range(8))]
        art += [("poly", s([(0.38, 0.28), (0.62, 0.28), (0.68, 0.5), (0.6, 0.66), (0.4, 0.66), (0.32, 0.5)]), OUDO),
                ("poly", s(_ellipse(0.5, 0.25, 0.1, 0.07)), OUDO), ("poly", s([(0.42, 0.16), (0.47, 0.1), (0.5, 0.17), (0.55, 0.1), (0.58, 0.16)]), SUMI),
                ("poly", s([(0.05, 0.75), (0.2, 0.66), (0.4, 0.7), (0.6, 0.64), (0.85, 0.7), (0.95, 0.82), (0.7, 0.9), (0.3, 0.9), (0.08, 0.86)]), USUKI)]
        art += [("line", s([(0.44, 0.24), (0.48, 0.24)]), SUMI), ("line", s([(0.52, 0.24), (0.56, 0.24)]), SUMI)]
        return art
    if shape == "sode":  # 袖に藍の鋸の紋、身頃に丸に十字
        art = [("poly", s(SAIL[shape]), GOFUN), ("poly", s([(0, 0), (0.22, 0), (0.22, 0.45), (0, 0.45)]), USUKI), ("poly", s([(0.78, 0), (1, 0), (1, 0.45), (0.78, 0.45)]), USUKI)]
        for x0 in (0.0, 0.78):
            art += [("poly", s([(x0, 0.08 + 0.1 * i), (x0 + 0.11, 0.13 + 0.1 * i), (x0, 0.18 + 0.1 * i)]), AI) for i in range(3)]
            art += [("poly", s([(x0 + 0.22, 0.08 + 0.1 * i), (x0 + 0.11, 0.13 + 0.1 * i), (x0 + 0.22, 0.18 + 0.1 * i)]), AI) for i in range(3)]
        art += [("poly", s(_ellipse(0.5, 0.42, 0.2, 0.15, 24)), OUDO), ("poly", s(_ellipse(0.5, 0.42, 0.15, 0.11, 24)), GOFUN),
                ("poly", s([(0.48, 0.3), (0.52, 0.3), (0.52, 0.54), (0.48, 0.54)]), OUDO), ("poly", s([(0.36, 0.405), (0.64, 0.405), (0.64, 0.435), (0.36, 0.435)]), OUDO),
                ("poly", s([(0.22, 0.7), (0.78, 0.66), (0.78, 0.8), (0.22, 0.84)]), USUKI)]
        return art
    if shape == "mimizuku":  # 灰の羽、丸い目、耳の羽
        art = [("poly", s(SAIL[shape]), "#bdb8ad"), ("poly", s([(0.3, 0.14), (0.7, 0.14), (0.74, 0.5), (0.5, 0.6), (0.26, 0.5)]), NEZU)]
        art += [("poly", s(_ellipse(cx, 0.22, 0.07, 0.05)), GOFUN) for cx in (0.42, 0.58)]
        art += [("poly", s(_ellipse(cx, 0.22, 0.03, 0.025, 8)), SUMI) for cx in (0.42, 0.58)]
        art += [("poly", s([(0.48, 0.28), (0.52, 0.28), (0.5, 0.33)]), OUDO), ("poly", s([(0.36, 0.04), (0.42, 0.1), (0.34, 0.12)]), SUMI), ("poly", s([(0.64, 0.04), (0.66, 0.12), (0.58, 0.1)]), SUMI)]
        art += [("line", s([(0.05 + 0.08 * i, 0.25 + 0.02 * i), (0.12 + 0.08 * i, 0.42)]), "#6c6860") for i in range(3)]
        art += [("line", s([(0.95 - 0.08 * i, 0.25 + 0.02 * i), (0.88 - 0.08 * i, 0.42)]), "#6c6860") for i in range(3)]
        art += [("line", s([(0.4 + 0.05 * i, 0.65), (0.42 + 0.05 * i, 0.9)]), "#6c6860") for i in range(4)]
        return art
    raise KeyError(shape)


def _clip(items, outline, holes=()):
    """絵を外形の少し内側で切る。手で取った点が縁を越えても、検査（絵が部品の外）に落ちないように。穴の周りは絵を抜かない（穴は線で刷る）。"""
    inner = Polygon(outline).buffer(-0.25)
    out = []
    for kind, pts, color in items:
        if kind == "poly":
            g = Polygon(pts).buffer(0).intersection(inner)
            for piece in getattr(g, "geoms", [g]):
                if not piece.is_empty and piece.geom_type == "Polygon" and piece.area > 0.05:
                    out.append({"kind": "poly", "pts": list(piece.exterior.coords)[:-1], "fill": color})
        else:
            g = LineString(pts).intersection(inner)
            for piece in getattr(g, "geoms", [g]):
                if not piece.is_empty and piece.geom_type == "LineString":
                    out.append({"kind": "line", "pts": list(piece.coords), "stroke": color, "sw": 0.5})
    return out


# ---- 人形の形の式 ----

def mover_outline(p):
    return _u(MOVER[p["shape"]], p["arm_len"], p["arm_w"])


def mover_holes(p):
    """腕木の軸の穴と糸の穴。軸は左の端から pivot_at、糸の穴は軸から pull_arm 左。どちらも縦の真ん中。"""
    cy = p["arm_w"] / 2
    holes = [(p["pivot_at"], cy, HOLE_R)]
    if p["rig"] != "sway":
        holes.append((p["pivot_at"] - p["pull_arm"], cy, HOLE_R))
    return holes


def guide_hole(p):
    """台紙の糸の通し穴。休んだ時の糸の穴の真下に置き、糸を下へ引けるようにする。"""
    return (p["pivot_x"] - p["pull_arm"], p["pivot_y"] + p["guide_drop"])


def swing_deg(p):
    """糸（棒）を stroke 動かした時に腕木が回る角度。糸の穴は軸から pull_arm の円の上を動くので、弦の長さとして数える。"""
    r = p["stroke"] / (2 * p["pull_arm"])
    return math.degrees(2 * math.asin(r)) if r <= 1 else float("inf")


def offset_mm(p):
    """腕木の重心（外形の面の重心）が軸から右へずれる量。正なら長い方が下がり、離すと戻る（揺れる）。"""
    return Polygon(mover_outline(p)).centroid.x - p["pivot_at"]


# ---- 凧の形の式 ----

def sail_outline(p):
    return _u(SAIL[p["shape"]], p["sail_w"], p["sail_h"])


def bridle_points(p):
    cx = p["sail_w"] / 2
    return [(cx, p["bridle_top"]), (cx, p["bridle_bottom"])]


def centroid_y(p):
    return Polygon(sail_outline(p)).centroid.y


def spar_len(p):
    seg = LineString([(-1, p["spar_y"]), (p["sail_w"] + 1, p["spar_y"])]).intersection(Polygon(sail_outline(p)))
    return seg.length


def legs(p):
    """糸目の 2 本の長さ。結び目は帆から bridle_h 離れ、帆の上では tow_at の所に来る。"""
    return [math.hypot(p["bridle_h"], p["tow_at"] - y) for _, y in bridle_points(p)]


def tail_count(p):
    if p["rig"] != "tail" or p["tail_len"] <= 0:
        return 0
    return max(1, math.ceil((p["tail_len"] - TAIL_OVER) / (TAIL_SEG - TAIL_OVER)))


def kite_mass_g(p):
    """帆の紙と竹ひご 2 本（径 2mm の見込み、0.0022g/mm）。尾の紙は帆より後ろで別に効くので、ここには入れない。"""
    paper = Polygon(sail_outline(p)).area * 1e-6 * p["paper_gsm"]
    return paper + 0.0022 * (p["sail_h"] + spar_len(p))


def metrics(p):
    """台帳の式（F7）。人形は回る角度と戻る力のずれ、凧は面積・翼の荷重・結び目の余裕を数える。"""
    if is_kite(p):
        area = Polygon(sail_outline(p)).area
        return {"area_cm2": area / 100, "loading_gsm": kite_mass_g(p) / (area * 1e-6), "tow_margin_mm": centroid_y(p) - p["tow_at"],
                "tail_ratio": p["tail_len"] / p["sail_h"] if p["rig"] == "tail" else 0.0}
    sw = swing_deg(p)
    return {"swing_deg": sw if math.isfinite(sw) else 999.0, "offset_mm": offset_mm(p)}


def _hole_ok(outline, x, y, margin=HOLE_MARGIN):
    return Polygon(outline).contains(Point(x, y).buffer(HOLE_R + margin))


def check_physics(p):
    return _kite_physics(p) if is_kite(p) else _lever_physics(p)


def _lever_physics(p):
    out = []
    mo = mover_outline(p)
    pivot, *rest = mover_holes(p)
    if not _hole_ok(mo, pivot[0], pivot[1]):
        out.append(Failure("F5.lever", "腕木の軸の穴", f"軸の穴から腕木の縁まで {HOLE_MARGIN}mm 取れず、回すと裂けやすい"))
    if rest and not _hole_ok(mo, rest[0][0], rest[0][1]):
        out.append(Failure("F5.lever", "糸の穴", f"糸の穴から腕木の縁まで {HOLE_MARGIN}mm 取れない（腕木の左の端か縁に寄りすぎ）"))
    board = [(0, 0), (p["board_w"], 0), (p["board_w"], p["board_h"]), (0, p["board_h"])]
    if not _hole_ok(board, p["pivot_x"], p["pivot_y"]):
        out.append(Failure("F5.lever", "台紙の軸の穴", f"軸の穴から台紙の縁まで {HOLE_MARGIN}mm 取れない"))
    if p["rig"] != "sway":
        # 腕の短すぎる腕木は、指の引きのぶれがそのまま大きな角度になり、狙った動きにならない。
        if p["pull_arm"] < MIN_ARM:
            out.append(Failure("F5.lever", "腕", f"軸から糸の穴まで {p['pull_arm']}mm で、{MIN_ARM}mm より短い"))
        sw = swing_deg(p)
        if not math.isfinite(sw):
            out.append(Failure("F5.lever", "引く量", f"引く量 {p['stroke']}mm が腕の 2 倍（{2 * p['pull_arm']}mm）を超え、腕木が裏返る"))
        elif sw < MIN_SWING:
            out.append(Failure("F5.lever", "引く量", f"引いて {sw:.0f}° しか回らず、動いたと見えない（{MIN_SWING}° から）"))
        elif sw > MAX_SWING:
            out.append(Failure("F5.lever", "引く量", f"引いて {sw:.0f}° 回り、{MAX_SWING}° を超えて戻れない"))
    if p["rig"] in ("pull", "sway"):
        # 糸を離した後と揺らす時は、紙の重さだけが腕木を戻す。重心が軸の真下に来ないと止まったままになる。
        off = offset_mm(p)
        if off < MIN_OFFSET:
            what = "離しても重さで戻らない" if p["rig"] == "pull" else "重心が軸の下に来ず、揺れない"
            out.append(Failure("F5.lever", "重心", f"腕木の重心が軸から {off:.1f}mm で、{what}（{MIN_OFFSET}mm から）"))
    if p["rig"] == "pull":
        gx, gy = guide_hole(p)
        if not _hole_ok(board, gx, gy):
            out.append(Failure("F5.lever", "糸の通し穴", f"糸の通し穴（{gx:g}, {gy:g}）が台紙の縁から {HOLE_MARGIN}mm 内に入らない"))
    if p["pivot_at"] >= p["arm_len"]:
        out.append(Failure("F5.lever", "腕木", "軸が腕木の外にある"))
    return out


def _kite_physics(p):
    out = []
    so = sail_outline(p)
    top, bottom = bridle_points(p)
    for name, (x, y) in (("上の糸目", top), ("下の糸目", bottom)):
        if not _hole_ok(so, x, y):
            out.append(Failure("F5.kite", name, f"糸目の穴（上から {y:g}mm）が帆の中に {HOLE_MARGIN}mm の余裕で入らない"))
    if top[1] >= bottom[1]:
        out.append(Failure("F5.kite", "糸目", "上の糸目が下の糸目より下にある"))
    # 結び目が受ける力の中心（平らな帆では面の重心と見込む）より上にないと、凧は頭を下げて落ちる。上の糸目より上なら立たない。
    cy = centroid_y(p)
    if not top[1] < p["tow_at"] < cy:
        out.append(Failure("F5.kite", "結び目", f"結び目（上から {p['tow_at']:g}mm）が上の糸目 {top[1]:g} と帆の重心 {cy:.0f} の間にない"))
    if not HOLE_MARGIN < p["spar_y"] < p["sail_h"] - HOLE_MARGIN or spar_len(p) < SPAR_MIN * p["sail_w"]:
        out.append(Failure("F5.kite", "横骨", f"横骨（上から {p['spar_y']:g}mm）が帆の幅の {SPAR_MIN:.0%} を渡らない"))
    if p["rig"] == "tail":
        if p["tail_len"] < MIN_TAIL * p["sail_h"]:
            out.append(Failure("F5.kite", "尾", f"尾 {p['tail_len']:g}mm が帆の高さの {MIN_TAIL} 倍（{MIN_TAIL * p['sail_h']:g}mm）より短く、凧が回りやすい"))
    else:
        ratio = p["bow_depth"] / max(spar_len(p), 1)
        if not BOW_MIN <= ratio <= BOW_MAX:
            out.append(Failure("F5.kite", "反り", f"横骨の反り {p['bow_depth']:g}mm が横骨の長さの {BOW_MIN:.0%}〜{BOW_MAX:.0%} の外"))
    return out


# ---- 部品 ----

def _disc(n, key):
    pts = _ellipse(5, 5, 5, 5, 12)
    return Part(n, key, "留め", pts, label_xy=(3.6, 0.6), label=str(n), holes=[(5, 5, HOLE_R)],
                art=[{"kind": "poly", "pts": _ellipse(5, 5, 4.3, 4.3, 12), "fill": SHU}])


def parts(p):
    if is_kite(p):
        return _kite_parts(p)
    bw, bh = p["board_w"], p["board_h"]
    board_pts = [(0, 0), (bw, 0), (bw, bh), (0, bh)]
    holes = [(p["pivot_x"], p["pivot_y"], HOLE_R)]
    if p["rig"] == "pull":
        holes.append((*guide_hole(p), HOLE_R))
    board = Part(1, "board", "台紙", board_pts, label_xy=(1.5, 1.2), label="1",
                 art=_clip(_board_art(p["shape"], bw, bh, p["pivot_x"] / bw, p["pivot_y"] / bh), board_pts), holes=holes)
    mo = mover_outline(p)
    mover = Part(2, "mover", "腕木", mo, label_xy=(1.2, p["arm_w"] / 2 - 1.8), label="2",
                 art=_clip(_mover_art(p["shape"], p["arm_len"], p["arm_w"]), mo), holes=mover_holes(p))
    # 番号のラベルが軸の穴に掛からないよう、軸が左の端に近い時は穴より右の帯に置く。
    if p["pivot_at"] < 8:
        mover.label_xy = (p["pivot_at"] + 3, p["arm_w"] / 2 - 1.8)
    return [board, mover, _disc(3, "disc1"), _disc(4, "disc2")]


def _kite_parts(p):
    so = sail_outline(p)
    sail = Part(1, "sail", "帆", so, label_xy=(p["sail_w"] / 2 + 3, p["sail_h"] * 0.5), label="1",
                art=_clip(_sail_art(p["shape"], p["sail_w"], p["sail_h"]), so), holes=[(x, y, HOLE_R) for x, y in bridle_points(p)])
    # 骨の位置は縁の小さな三角で示す。帆の面に骨の線を刷ると、見える面に線が出る（本人の決定 d の考えに合わせる）。
    cx, sy = p["sail_w"] / 2, p["spar_y"]
    xs = [x for x in _spar_ends(p)]
    marks = [[(cx - 1.5, 0.3), (cx + 1.5, 0.3), (cx, 2.5)]]
    if xs:
        marks += [[(xs[0] + 0.3, sy - 1.5), (xs[0] + 0.3, sy + 1.5), (xs[0] + 2.5, sy)], [(xs[1] - 0.3, sy - 1.5), (xs[1] - 0.3, sy + 1.5), (xs[1] - 2.5, sy)]]
    sail.art += [{"kind": "poly", "pts": m, "fill": SUMI} for m in marks if Polygon(so).buffer(0.05).contains(Polygon(m))]
    out = [sail]
    out += [Part(2 + i, f"patch{i + 1}", "当て紙", [(0, 0), (12, 0), (12, 12), (0, 12)], label_xy=(0.8, 0.6), label=str(2 + i), holes=[(6, 7, HOLE_R)])
            for i in range(2)]
    for i in range(tail_count(p)):
        n = 4 + i
        out.append(Part(n, f"tail{i + 1}", "尾", [(0, 0), (TAIL_W, 0), (TAIL_W, TAIL_SEG), (0, TAIL_SEG)], label_xy=(1.2, 1.5), label=str(n),
                        glue=[[(0, TAIL_SEG - TAIL_OVER), (TAIL_W, TAIL_SEG - TAIL_OVER), (TAIL_W, TAIL_SEG), (0, TAIL_SEG)]] if i < tail_count(p) - 1 else [],
                        art=[{"kind": "poly", "pts": [(0.3, 8), (TAIL_W - 0.3, 8), (TAIL_W - 0.3, TAIL_SEG - TAIL_OVER - 0.3), (0.3, TAIL_SEG - TAIL_OVER - 0.3)], "fill": SHU if i % 2 == 0 else AI}]))
    return out


def _spar_ends(p):
    seg = LineString([(-1, p["spar_y"]), (p["sail_w"] + 1, p["spar_y"])]).intersection(Polygon(sail_outline(p)))
    if seg.is_empty:
        return []
    xs = [c[0] for g in getattr(seg, "geoms", [seg]) for c in g.coords]
    return [min(xs), max(xs)]


def place(by_key, page, top, gap):
    x0 = page.x0
    if "sail" in by_key:
        sail = by_key["sail"]
        sail.x, sail.y = x0, top
        x = x0 + sail.width + gap
        bottom = top + sail.height
        for k in ("patch1", "patch2"):
            q = by_key[k]
            q.x, q.y = x, top
            x += q.width + gap
        x = x0 + sail.width + gap
        y = top + 12 + gap
        tails = sorted((k for k in by_key if k.startswith("tail")), key=lambda k: int(k[4:]))
        for k in tails:
            q = by_key[k]
            q.x, q.y = x, y
            x += q.width + gap
            bottom = max(bottom, y + q.height)
        return bottom + gap, page.x1 - x0, x0
    board, mover = by_key["board"], by_key["mover"]
    board.x, board.y = x0, top
    mover.x, mover.y = x0 + board.width + gap, top
    dy = top + mover.height + gap
    for k in ("disc1", "disc2"):
        q = by_key[k]
        q.x, q.y = mover.x + (0 if k == "disc1" else q.width + gap), dy
    bottom = max(board.y + board.height, dy + 10)
    return bottom + gap, page.x1 - x0, x0


def bom(p):
    paper = f"紙（{p['paper_gsm']}g/m² 前後の見込み）"
    why = "家庭のプリンタで刷って作るため"
    if is_kite(p):
        top, bottom = legs(p)
        rows = [
            {"number": 1, "key": "sail", "name": "帆", "qty": 1, "material": paper, "substituted": True, "original_guess": "和紙（凧の通例から。この図では確かめていない）", "reason": why},
            {"number": 2, "key": "patch", "name": "当て紙", "qty": 2, "material": paper, "substituted": False},
            {"number": 7, "key": "spine", "name": "縦骨", "qty": 1, "material": f"竹ひご（長さ約 {p['sail_h']:g}mm）", "substituted": True, "original_guess": "割り竹（不明）", "reason": "家にあり、まっすぐなため"},
            {"number": 8, "key": "spar", "name": "横骨", "qty": 1, "material": f"竹ひご（長さ約 {spar_len(p):.0f}mm）", "substituted": True, "original_guess": "割り竹（不明）", "reason": "同じ"},
            {"number": 9, "key": "bridle", "name": "糸目と揚げ糸", "qty": 1, "material": f"木綿の糸（糸目 {top + bottom + 20:.0f}mm と、揚げ糸 数 m）", "substituted": True, "original_guess": "麻糸（不明）", "reason": "家にあるため"},
        ]
        if p["rig"] == "tail":
            rows.append({"number": 4, "key": "tail", "name": "尾", "qty": tail_count(p), "material": paper, "substituted": True, "original_guess": "不明（図に尾は見えない）", "reason": why})
        return rows
    rows = [
        {"number": 1, "key": "board", "name": "台紙", "qty": 1, "material": f"{paper}を空き箱の厚紙に貼る", "substituted": True, "original_guess": "木か竹（棚卸しの見立てによる。確かめていない）", "reason": why},
        {"number": 2, "key": "mover", "name": "腕木", "qty": 1, "material": f"{paper}を厚紙に貼る", "substituted": True, "original_guess": "木（同じ）", "reason": why},
        {"number": 3, "key": "disc", "name": "留め", "qty": 2, "material": paper, "substituted": False},
        {"number": 7, "key": "axle", "name": "軸", "qty": 1, "material": "楊枝（両端を少し残して切る）", "substituted": True, "original_guess": "竹釘（不明）", "reason": "家にあり、穴に通しやすいため"},
    ]
    if p["rig"] == "pull":
        rows.append({"number": 8, "key": "string", "name": "糸", "qty": 1, "material": f"木綿の糸 約 {p['guide_drop'] + 150:g}mm と、先に付けるビーズ 1 個", "substituted": True, "original_guess": "糸（図に見える）", "reason": "家にあるため"})
    elif p["rig"] == "push":
        rows.append({"number": 8, "key": "rod", "name": "押し棒", "qty": 1, "material": "竹串 1 本とテープ", "substituted": True, "original_guess": "竹の棒（不明）", "reason": "家にあるため"})
    return rows


def materials(p):
    rows = bom(p)
    extra = [r["material"] for r in rows if r["key"] not in ("sail", "patch", "board", "mover", "disc", "tail")]
    # 凧も人形も、手順で穴を竹串の先であける（#294。前は凧の時だけ書いていなかった）。
    return [f"{rows[0]['material']}を 1 枚", "のり、はさみ、テープ、定規、竹串（穴あけ）", *extra]


def steps(p):
    out = ["刷った物差しに定規を当て、10cm か確かめる"]
    if is_kite(p):
        top, bottom = legs(p)
        out += ["1 帆を実線で切る。2 当て紙を帆の裏の穴の所に貼り、穴を竹串の先であける",
                "縦骨を帆の裏の真ん中に、横骨を縁の三角の所にテープで貼る"]
        if p["rig"] == "bow":
            out.append(f"横骨の両端に糸を張り、真ん中が帆の裏へ {p['bow_depth']:g}mm 反るように結ぶ")
        else:
            out.append(f"4〜{3 + tail_count(p)} 尾を糊代でつなぎ（約 {p['tail_len']:g}mm）、帆の下の端に貼る")
        out += [f"糸目: 上の穴に {top:.0f}mm、下の穴に {bottom:.0f}mm の糸を表から通して骨に結ぶ",
                f"2 本の先を結ぶ。結び目は帆から {p['bridle_h']:g}mm、上から {p['tow_at']:g}mm の所の真上に来る",
                "結び目に揚げ糸を結ぶ。風のある広い所で、電線の無い所で揚げる"]
        return out
    out += ["1 台紙と 2 腕木を厚紙に貼ってから実線で切る。穴は竹串の先であける",
            "楊枝を 3 留め・2 腕木・1 台紙・4 留めの順に通し、留めを楊枝に貼る。腕木が軽く回るか見る"]
    if p["rig"] == "pull":
        out += [f"糸を腕木の糸の穴に結び、台紙の下の通し穴へ表から裏へ通す。先にビーズを付ける",
                f"台紙を持ち、糸を {p['stroke']:g}mm ほど引いて離す"]
    elif p["rig"] == "push":
        out += ["竹串の先を腕木の糸の穴の所にテープで留める", f"竹串を {p['stroke']:g}mm ほど押し上げ、引き下げる"]
    else:
        out += ["台紙の上の端を持ち、左右に小さく揺らす"]
    return out


# 動いたかを 3 つの同じ大きさの欄で問う（「少し」を入れるのは、紙のこすれで動きが小さい事が多いと見込むため）。
RESULTS = ("よく動いた", "少し動いた", "動かない")


def measures(p):
    """動き方を言葉か絵で予想する（U-25 の案 1 に倣う）。動かした物は数でないので残す。"""
    if is_kite(p):
        return {"predict": "凧は風の中でどう動くと思いますか（言葉か絵で）", "rows": [[("風の強さ（弱い・ふつう・強い）", 40)]]}
    return {"predict": "糸や棒を動かすと、どこがどう動くと思いますか（言葉か絵で）", "rows": [[("動かした物（糸・棒・手）", 40)]]}


def diagram(x, y, w, h, p):
    """手順の紙の横の図。人形は軸と腕と糸、凧は帆と骨と糸目。答え（どう動くか）は描かない。"""
    shapes = []
    if is_kite(p):
        s = min(w / (p["sail_w"] + p["bridle_h"] * 0.6), (h - 4) / p["sail_h"])
        ox, oy = x + 1, y + 2
        pts = [(ox + a * s, oy + b * s) for a, b in sail_outline(p)]
        for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
            shapes.append({"kind": "line", "x1": x1, "y1": y1, "x2": x2, "y2": y2})
        cx = ox + p["sail_w"] / 2 * s
        shapes.append({"kind": "line", "x1": cx, "y1": oy, "x2": cx, "y2": oy + p["sail_h"] * s, "dash": "1,0.6"})
        xs = _spar_ends(p)
        if xs:
            shapes.append({"kind": "line", "x1": ox + xs[0] * s, "y1": oy + p["spar_y"] * s, "x2": ox + xs[1] * s, "y2": oy + p["spar_y"] * s, "dash": "1,0.6"})
        # 糸目は帆の面から手前に出るので、横から見た形を右に添える（帆を縦の線で見る）。
        sx = ox + p["sail_w"] * s + 2
        shapes.append({"kind": "line", "x1": sx, "y1": oy, "x2": sx, "y2": oy + p["sail_h"] * s})
        kx, ky = sx + p["bridle_h"] * s * 0.5, oy + p["tow_at"] * s
        for _, by in bridle_points(p):
            shapes.append({"kind": "line", "x1": sx, "y1": oy + by * s, "x2": kx, "y2": ky})
        shapes.append({"kind": "rect", "x": kx - 0.8, "y": ky - 0.8, "w": 1.6, "h": 1.6})
        return shapes
    # 吊った腕木と下へ出る糸も図の枠に入れる。枠の外へ出ると、下の説明の字に線が掛かる。
    tall = max(p["board_h"], p["pivot_y"] + p["arm_len"] - p["pivot_at"], p["pivot_y"] + p["guide_drop"] + 6)
    s = min(w / max(p["board_w"], p["pivot_x"] + p["arm_len"] - p["pivot_at"]), h / (tall + 2))
    ox, oy = x + 1, y + 1
    shapes.append({"kind": "rect", "x": ox, "y": oy, "w": p["board_w"] * s, "h": p["board_h"] * s})
    px, py = ox + p["pivot_x"] * s, oy + p["pivot_y"] * s
    if p["rig"] == "sway":
        shapes.append({"kind": "line", "x1": px, "y1": py, "x2": px, "y2": py + (p["arm_len"] - p["pivot_at"]) * s})
    else:
        shapes.append({"kind": "line", "x1": px - p["pivot_at"] * s, "y1": py, "x2": px + (p["arm_len"] - p["pivot_at"]) * s, "y2": py})
        hx = px - p["pull_arm"] * s
        if p["rig"] == "pull":
            gy = oy + (p["pivot_y"] + p["guide_drop"]) * s
            shapes.append({"kind": "line", "x1": hx, "y1": py, "x2": hx, "y2": gy + 6, "dash": "1,0.6"})
        else:
            shapes.append({"kind": "line", "x1": hx, "y1": py, "x2": hx, "y2": oy + p["board_h"] * s + 0.5})
    shapes.append({"kind": "rect", "x": px - 1, "y": py - 1, "w": 2, "h": 2})
    return shapes
