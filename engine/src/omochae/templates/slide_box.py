"""雛形 slide_box: 長い箱と、滑る板（蓋か外箱）で、猫と鼠を会わせたり離したりする（猫と鼠の箱・鼠取り、推定）。

コマ 25 の右頁の図: 長い口の開いた箱の上に、箱より長い板が載り、後ろへずれて箱の後ろからはみ出している。板の前の縁に猫が
うずくまり、板がどいた箱の前の所に鼠が立って、上を見上げている。板の前の縁の下の箱の中に、仕切りらしい線がある。
【解釈】板は箱の上を前後に滑る。板を前へ戻すと鼠が隠れ（猫に捕まる）、後ろへ引くと鼠が出る。どれが昔の作り方かは
図から決まらないので、刷る形（form）で 2 つを描き分ける。玩具の型紙は 1 枚で、lid がたたき台、sleeve は試行錯誤のヒント
（制作者の決定 2026-11-05「玩具 1 つに型紙 1 枚」・omochae.sheets）。
- lid（既定・図にいちばん近い読み）: 箱の上の蓋の板が滑る。蓋の左右の縁を下へ折った袴が、箱の側の壁の外を挟んで道になる。
  蓋の裏の前に貼った止め（舌）が、前では箱の前の壁に、後ろでは仕切りに当たり、蓋は落ちない。猫は蓋に載って一緒に動く。
- sleeve（2 つ目の読み・推定）: マッチ箱の形。猫を載せた外箱（筒）は止まったまま、中箱を前へ引き出すと鼠が出る。
  外箱の上の面の前の端を内へ折った縁（止め）が中箱の仕切りに当たり、中箱は抜けない。中箱の前の壁は縁の下を通れるよう低い。

紙の部品は、箱（中箱）・蓋か外箱・止め（lid だけ）・仕切り・猫・鼠。竹串や糸は使わない。
寸法は手元の複写の図の比から出した見込みで、どの値も実物では未確認。Claude が変えてよいのは RANGES の名前の値だけ。

動きの見込み（F5.slide）の前提:
- 紙の部品の寸法は折り線で測る。折ると紙の厚み t の半分が折り線の外に、半分が内に出ると見る（箱の外の幅 ＝ W + t、
  筒の内の幅 ＝ 面の幅 − t）。重ねて貼った糊代は、重なった所の道を t だけ狭める。
- 滑る所の隙間 ＝ slide_gap − （紙の厚み × 層の数）。MIN_CLEAR より狭いと擦れて動かず、MAX_CLEAR より広いとがたついて
  止めが外れる、と見込む（どちらの値も実物で確かめていない）。
- 動く長さ（行程）は、止めが仕切りに当たるまで。鼠の像の全部が板の外に出るだけ動き、閉じた時は全部が板の下に隠れる事を見る。
- 板（蓋・中箱）は、動いた後も長さの半分以上が支えの上に残る事を見る（蓋は重心が箱の後ろの端を越えると傾く。猫の重みは
  前の縁にあるので、見込みは安全側）。摩擦・紙の反りは入れない。
- 止めは仕切りに CATCH だけ掛かり、鼠と前の壁の上は PASS 空けて通る事を見る。
- 糊代は滑る道の外に置く: 箱の角の糊代は側の壁の内側、仕切りの糊代は後ろ向き、外箱の継ぎ目の糊代は底の内側（層に数える）。
  蓋の止めは、箱の前の角の糊代で狭まった所を擦らずに通る幅でなければならない。
"""
from shapely.geometry import LineString, Polygon, box as rect

from ..paper_words import paper_name  # 紙の書き方は 4 つの名前だけ（制作者の指示 2026-11-05）
from ..model import Failure, Part

ID = "slide_box"
DEFAULTS = {
    "form": "lid",
    # 箱の内の寸法（折り線で測る）。コマ 25 の図で、箱の長さは幅の 3.5 倍ほど、高さは幅よりわずかに低く見える（斜めの図を目測）。
    "box_l": 110, "box_w": 30, "box_h": 26, "glue": 7,
    # 中箱の前の壁の高さ（sleeve だけで使う。lid の前の壁は止めを受けるので箱の高さと同じ）。
    "front_h": 10,
    # 仕切りの位置（箱の前の壁の内から）。図で板の前の縁の下に見える線を仕切りと読んだ。
    "partition_at": 50,
    "mouse_at": 8, "mouse_w": 14, "mouse_h": 16,
    "cat_w": 28, "cat_h": 28,
    "stop_depth": 6, "stop_w": 27, "skirt": 6,
    # 道の隙間の見込み（板の幅に足す）。0.15mm はふつうの厚めの紙の見込み。実物の紙を測ったら置き換える。
    "slide_gap": 1.0, "paper_thickness": 0.15,
}
RANGES = {
    "box_l": (60, 130), "box_w": (15, 45), "box_h": (12, 40), "glue": (5, 12),
    "front_h": (4, 30), "partition_at": (20, 100),
    "mouse_at": (2, 40), "mouse_w": (10, 40), "mouse_h": (8, 35),
    "cat_w": (12, 45), "cat_h": (10, 40),
    "stop_depth": (2, 15), "stop_w": (8, 44), "skirt": (3, 12),
    "slide_gap": (0.2, 4), "paper_thickness": (0.05, 0.5),
}
FORMS = ("lid", "sleeve")
# 刷る形を決める寸法（何が滑るか）。仮説の違いそのものなので、寸法を直に渡す入口では既定に頼らず必ず書かせる。
FORM = "form"
# 既定の出典（data/sources/ の名前）。--source を書かない時に、雛形と合わない出典の印を刷らないため。
SOURCE = "NDL-1187053-R0000025-R-slide_box"
# 2 つの形は同じ玩具（コマ 25 右）の読みの違いなので、どちらも同じ出典にする。形と合わない出典は compose が F1.source で落とす。
SOURCES = {"lid": SOURCE, "sleeve": SOURCE}
MIN_CLEAR, MAX_CLEAR = 0.4, 2.0  # 滑る隙間の下限と上限の見込み（mm・実物では未確認）
SHOW_MARGIN = 2  # 鼠の像の後ろの端から板の縁までに残す余り。ぎりぎりだと像の端が板に隠れて見える
CATCH = 1.5  # 止めが仕切りに掛かる深さの下限。浅いと紙がたわんで乗り越える
PASS = 1.0  # 止めの下を通る物（鼠・前の壁）の上に空ける余り
STOP_AT = 2  # lid: 止めを貼る所（蓋の前の縁から）。前の壁の厚みより後ろに置き、閉じた時に前の壁に当てる
STOP_GLUE = 6  # lid: 止めの足（蓋の裏に貼る糊代）の長さ
PART_TAB = 6  # 仕切りの糊代の幅
FIG_TAB = 5  # 像の足の糊代。図には無いが、立てるのに要る
WOOD, WOOD_DARK, CAT, INK, MOUSE = "#d6b96e", "#b8964d", "#ece6d6", "#3b3a34", "#b5ad9c"
TITLES = {"lid": "蓋が滑る箱", "sleeve": "中箱を引き出す箱"}


def title(p):
    return TITLES[p["form"]]


def spec():
    return {"template_id": ID, "defaults": DEFAULTS, "ranges": RANGES, "form": FORMS}


def check_range(p):
    out = []
    for k, v in p.items():
        if k == "form":
            if v not in FORMS:
                out.append(Failure("F5.range", k, f"{v} は {FORMS} のどれでもない"))
        elif k not in RANGES:
            out.append(Failure("F5.range", k, "知らない寸法の名前"))
        elif not isinstance(v, (int, float)) or isinstance(v, bool) or not RANGES[k][0] <= v <= RANGES[k][1]:
            out.append(Failure("F5.range", k, f"{v} は範囲 {RANGES[k]} の外"))
    return out


def board_width(p):
    """蓋の板（lid）と外箱の上下の面（sleeve）の幅（折り線で測る）＝ 箱の内の幅 ＋ 道の隙間の見込み。"""
    return p["box_w"] + p["slide_gap"]


def sleeve_height(p):
    """外箱の側の面の高さ（折り線で測る）＝ 箱の高さ ＋ 道の隙間の見込み。"""
    return p["box_h"] + p["slide_gap"]


def clearances(p):
    """滑る所の隙間（mm）と、数えた紙の層。前提は module の docstring。

    lid の左右: 袴の内 (B − t) − 箱の外 (W + t) ＝ gap − 2t（層 2）。
    sleeve の左右: 同じく gap − 2t。上下: 外箱の内の高さ (Hs − t) から、底の内に貼った継ぎ目の糊代 t と、中箱の外の高さ
    (H + t) を引いて gap − 3t（層 3）。
    """
    t = p["paper_thickness"]
    side = board_width(p) - t - (p["box_w"] + t)
    if p["form"] == "lid":
        return {"左右": (side, 2)}
    up = sleeve_height(p) - t - t - (p["box_h"] + t)
    return {"左右": (side, 2), "上下": (up, 3)}


def travel(p):
    """動く長さ。lid は止め（蓋の前から STOP_AT・厚み t）が仕切り（厚み t）に当たるまで、sleeve は仕切りが外箱の縁に当たるまで。"""
    t = p["paper_thickness"]
    if p["form"] == "lid":
        return p["partition_at"] - STOP_AT - 2 * t
    return p["partition_at"] - t


# sleeve: 縁の切る端の角を落とす幅。縁の本当の深さ（切る端から折り線まで）は stop_depth からこれだけ浅い。
LIP_INSET = 0.5


def lip_depth(p):
    """sleeve の外箱の縁の本当の深さ。刷る外形（_sleeve）と掛かりの式（check_physics）が同じこの値を使う。
    名目の stop_depth で掛かりを見ていた時は、0.5mm 深く見込み、掛からない縁を通していた。"""
    return p["stop_depth"] - LIP_INSET


def sleeve_inner_h(p):
    """外箱の内の高さ（底の継ぎ目の糊代の上から上の面の内まで）。縁の下の端はここから lip_depth 下がる。"""
    t = p["paper_thickness"]
    return sleeve_height(p) - 2 * t


def stop_side_room(p):
    """lid: 止めの左右に残る隙間。箱の前の角の糊代（側の壁の内に貼る）が、前から glue の長さだけ内の幅を 2t 狭める。
    止めは前から STOP_AT の所にあり、閉じた時はちょうどこの狭い所にいる。"""
    t = p["paper_thickness"]
    inner = p["box_w"] - t - 2 * t
    return (inner - p["stop_w"]) / 2


def check_physics(p):
    """F5.slide: 道の隙間・行程（鼠が出て隠れる）・止め（落ちない）・糊代が道をふさがない、を見る。"""
    out = []
    t, H, L = p["paper_thickness"], p["box_h"], p["box_l"]
    for where, (c, layers) in clearances(p).items():
        if not MIN_CLEAR <= c <= MAX_CLEAR:
            out.append(Failure("F5.slide", f"道の隙間（{where}）", f"隙間 {c:.2f}mm（隙間の見込み {p['slide_gap']:g} − 厚み {t:g} × {layers} 層）が {MIN_CLEAR}〜{MAX_CLEAR}mm の外"))
    s = travel(p)
    show = p["mouse_at"] + p["mouse_w"] + SHOW_MARGIN
    if s < show:
        out.append(Failure("F5.slide", "行程", f"動く長さ {s:.1f}mm では鼠（前から {p['mouse_at']:g}〜{p['mouse_at'] + p['mouse_w']:g}mm）が出きらない（{show:g}mm 要る）"))
    if s > L / 2:
        who = "蓋の重心が箱の後ろの端を越えて傾く" if p["form"] == "lid" else "中箱が外箱に半分も残らず垂れる"
        out.append(Failure("F5.slide", "行程", f"動く長さ {s:.1f}mm が箱の長さの半分 {L / 2:g}mm を超え、{who}"))
    if p["partition_at"] > L - 10:
        out.append(Failure("F5.slide", "仕切り", f"仕切りが箱の後ろの壁から 10mm 離れない（前から {p['partition_at']:g}mm）"))
    if p["form"] == "lid":
        if p["mouse_at"] < STOP_AT + t + PASS:
            out.append(Failure("F5.slide", "鼠", f"閉じた時に鼠が止めより前にあり、隠れない（前から {STOP_AT + t + PASS:.1f}mm 以上）"))
        if p["stop_depth"] < CATCH:
            out.append(Failure("F5.slide", "止め", f"止めの深さ {p['stop_depth']:g}mm が仕切りに {CATCH}mm 掛からず、蓋が抜ける"))
        if p["mouse_h"] > H - p["stop_depth"] - PASS:
            out.append(Failure("F5.slide", "止め", f"鼠の高さ {p['mouse_h']:g}mm が止めの下（{H - p['stop_depth'] - PASS:g}mm まで）を通れない"))
        room = stop_side_room(p)
        if room < MIN_CLEAR:
            out.append(Failure("F5.slide", "糊代", f"止めの左右の隙間 {room:.2f}mm が、箱の前の角の糊代で {MIN_CLEAR}mm を割り、止めが糊代に擦れる"))
    else:
        inner = sleeve_inner_h(p)
        lip = inner - lip_depth(p)
        if (H + t) - lip < CATCH:
            out.append(Failure("F5.slide", "止め", f"外箱の縁が仕切りに {(H + t) - lip:.1f}mm しか掛からず（{CATCH}mm 以上）、中箱が抜ける"))
        if p["front_h"] > H:
            out.append(Failure("F5.slide", "前の壁", f"前の壁 {p['front_h']:g}mm が箱の高さ {H:g}mm を超える"))
        if p["front_h"] + t > lip - PASS:
            out.append(Failure("F5.slide", "前の壁", f"中箱の前の壁 {p['front_h']:g}mm が外箱の縁の下（{lip - PASS - t:.1f}mm まで）を通れない"))
        if p["mouse_h"] + t > lip - PASS:
            out.append(Failure("F5.slide", "止め", f"鼠の高さ {p['mouse_h']:g}mm が外箱の縁の下（{lip - PASS - t:.1f}mm まで）を通れない"))
        # 継ぎ目の糊代が底の面より広いと、角を越えて側の面へ上がり、中箱の角に擦れる。
        if p["glue"] > board_width(p) - 2:
            out.append(Failure("F5.slide", "糊代", f"外箱の継ぎ目の糊代 {p['glue']:g}mm が底の面に収まらず、道に出る"))
    return out


def _panel(x0, y0, x1, y1, fill, inset=0.25):
    return {"kind": "poly", "pts": [(x0 + inset, y0 + inset), (x1 - inset, y0 + inset), (x1 - inset, y1 - inset), (x0 + inset, y1 - inset)], "fill": fill}


def _box(p):
    """箱（中箱）の展開図。x は箱の長さ（左が前）、y は幅。床の四方に壁、端の壁の両脇に角の糊代（側の壁の内に貼る）。"""
    L, W, H, g = p["box_l"], p["box_w"], p["box_h"], p["glue"]
    hf = H if p["form"] == "lid" else p["front_h"]
    # 前の壁の置き場。外形の左上を原点にする（ほかの部品と同じ）ので、前の壁の高さだけ右へずらす。
    # 箱の高さで固定していた時は、sleeve の低い前の壁で外形の左の端が 0 でなかった。
    ox = hf
    gf, gr = min(g, H - 0.5), min(g, H - 0.5)  # 糊代は角の正方形からはみ出さない
    pts = [(ox, 0), (ox + L, 0), (ox + L, H),
           (ox + L + 1, H - gr), (ox + L + H - 1.5, H - gr), (ox + L + H, H), (ox + L + H, H + W),
           (ox + L + H - 1.5, H + W + gr), (ox + L + 1, H + W + gr), (ox + L, H + W),
           (ox + L, 2 * H + W), (ox, 2 * H + W), (ox, H + W),
           (ox - 1, H + W + gf), (ox - hf + 1.5, H + W + gf), (ox - hf, H + W), (ox - hf, H),
           (ox - hf + 1.5, H - gf), (ox - 1, H - gf), (ox, H)]
    name = "箱" if p["form"] == "lid" else "中箱"
    part = Part(1, "box", name, pts, label_xy=(ox + 2, H + 2), label=f"1 {name}")
    part.valley = [((ox, H), (ox + L, H)), ((ox, H + W), (ox + L, H + W)), ((ox, H), (ox, H + W)), ((ox + L, H), (ox + L, H + W)),
                   ((ox + L, H), (ox + L + H, H)), ((ox + L, H + W), (ox + L + H, H + W)), ((ox - hf, H), (ox, H)), ((ox - hf, H + W), (ox, H + W))]
    part.glue = [[(ox + L, H), (ox + L + 1, H - gr), (ox + L + H - 1.5, H - gr), (ox + L + H, H)],
                 [(ox + L, H + W), (ox + L + H, H + W), (ox + L + H - 1.5, H + W + gr), (ox + L + 1, H + W + gr)],
                 [(ox - hf, H + W), (ox, H + W), (ox - 1, H + W + gf), (ox - hf + 1.5, H + W + gf)],
                 [(ox - hf, H), (ox - hf + 1.5, H - gf), (ox - 1, H - gf), (ox, H)]]
    part.art = [_panel(ox, 0, ox + L, H, WOOD), _panel(ox, H + W, ox + L, 2 * H + W, WOOD), _panel(ox, H, ox + L, H + W, WOOD_DARK),
                _panel(ox + L, H, ox + L + H, H + W, WOOD), _panel(ox - hf, H, ox, H + W, WOOD)]
    # 仕切りと鼠を貼る所の印（床の上）。前の壁から partition_at・mouse_at の所。線は床の面の中だけに引く。
    xp, xm = ox + p["partition_at"], ox + p["mouse_at"]
    part.art.append({"kind": "line", "pts": [(xp, H + 1), (xp, H + W - 1)], "stroke": INK, "sw": 0.3})
    part.art.append({"kind": "line", "pts": [(xm, H + W / 2), (xm + p["mouse_w"], H + W / 2)], "stroke": INK, "sw": 0.3})
    return part


def _lid(p):
    """蓋の板（lid）。板の左右の袴を下へ山折りし、箱の側の壁の外を挟む。左が前（猫を貼る側）。"""
    L, B, k = p["box_l"], board_width(p), p["skirt"]
    pts = [(0, 0), (L, 0), (L, 2 * k + B), (0, 2 * k + B)]
    part = Part(2, "lid", "蓋", pts, label_xy=(L - 12, k + 2), label="2 蓋")
    part.mountain = [((0, k), (L, k)), ((0, k + B), (L, k + B))]
    part.art = [_panel(0, k, L, k + B, WOOD), _panel(0, 0, L, k, WOOD_DARK), _panel(0, k + B, L, 2 * k + B, WOOD_DARK)]
    # 止めを貼る所の印（前から STOP_AT）。行程の式（travel）がこの位置に頼るので、印が無いと式どおりに貼れない。
    # 止めは裏に貼るので、表の板の印に加え、左右の袴にも刷る。蓋を裏返すと袴の印が止めの横に見え、足の前の端を合わせられる。
    part.art += [{"kind": "line", "pts": [(STOP_AT, y0), (STOP_AT, y1)], "stroke": INK, "sw": 0.25}
                 for y0, y1 in ((k + 1.5, k + B - 1.5), (0.8, k - 0.8), (k + B + 0.8, 2 * k + B - 0.8))]
    return part


def _stop(p):
    """蓋の止め（lid）。足を蓋の裏の前に貼り、舌を下へ垂らす。舌が前の壁と仕切りに当たる。"""
    w, s = p["stop_w"], p["stop_depth"]
    part = Part(3, "stop", "止め", [(0, 0), (w, 0), (w, STOP_GLUE + s), (0, STOP_GLUE + s)], label_xy=(1, STOP_GLUE + 0.3), label="3")
    part.valley = [((0, STOP_GLUE), (w, STOP_GLUE))]
    part.glue = [[(0, 0), (w, 0), (w, STOP_GLUE), (0, STOP_GLUE)]]
    return part


def _sleeve(p):
    """外箱（sleeve）。y の順に 底・側・上・側・継ぎ目の糊代。上の面の前（左）の端に、内へ折る縁（止め）。表が外。
    糊代を底の内に貼るのは、上の面の縁の折りに糊代を重ねないため（底の内に重ねた分は clearances の層に数える）。"""
    L, B, Hs, g, s = p["box_l"], board_width(p), sleeve_height(p), p["glue"], lip_depth(p)
    y1, y2, y3, y4 = B, B + Hs, 2 * B + Hs, 2 * B + 2 * Hs
    # 縁の切る端を x = 0 に置き（ほかの部品と同じく外形の左上が原点）、折り線を x = lip_depth に置く。
    # 切る端の角は LIP_INSET の幅で y に 0.5 ずつ落とす（折り線の端より縁を細くし、上の面の角の折りに掛けない）。
    pts = [(s, 0), (s + L, 0), (s + L, y4), (s + L - 1.5, y4 + g), (s + 1.5, y4 + g), (s, y4), (s, y3 - 1),
           (0, y3 - 1 - LIP_INSET), (0, y2 + 1 + LIP_INSET), (s, y2 + 1)]
    part = Part(2, "sleeve", "外箱", pts, label_xy=(s + L - 14, y2 + 2), label="2 外箱")
    part.mountain = [((s, y), (s + L, y)) for y in (y1, y2, y3, y4)] + [((s, y2 + 1), (s, y3 - 1))]
    part.glue = [[(s, y4), (s + L, y4), (s + L - 1.5, y4 + g), (s + 1.5, y4 + g)]]
    part.art = [_panel(s, 0, s + L, y1, WOOD_DARK), _panel(s, y1, s + L, y2, WOOD), _panel(s, y2, s + L, y3, WOOD), _panel(s, y3, s + L, y4, WOOD)]
    # 猫を貼る所の印（上の面の前の寄り）。
    part.art.append({"kind": "line", "pts": [(s + 3, y2 + B / 2), (s + 3 + p["cat_w"] * 0.4, y2 + B / 2)], "stroke": INK, "sw": 0.25})
    part.label_xy = (s + L - 14, y2 + 2)
    return part


def _partition(p):
    """仕切り。左右の糊代を後ろへ折り、側の壁の内に貼る（糊代を前に向けると、鼠の側の道に出る）。"""
    t, H, g = p["paper_thickness"], p["box_h"], PART_TAB
    w = p["box_w"] - t - 2 * t - 0.5  # 側の壁の内（角の糊代が来ない中ほど）より、自分の糊代の 2 層と遊びだけ細く
    pts = [(1, 0), (g, 0), (g + w, 0), (2 * g + w - 1, 0), (2 * g + w, H), (0, H)]
    part = Part(4, "partition", "仕切り", pts, label_xy=(g + 1, 1), label="4")
    part.valley = [((g, 0), (g, H)), ((g + w, 0), (g + w, H))]
    part.glue = [[(1, 0), (g, 0), (g, H), (0, H)], [(g + w, 0), (2 * g + w - 1, 0), (2 * g + w, H), (g + w, H)]]
    part.art = [_panel(g, 0, g + w, H, WOOD)]
    return part


# コマ 25 の猫と鼠。図を拡大し、手で取った点（猫は 720×760、鼠は 660×870 の拡大の座標）。画素は使っていない。
_CAT = [(130, 345), (190, 265), (260, 225), (350, 210), (440, 225), (500, 250), (470, 190), (440, 130), (438, 70), (455, 38), (478, 40),
        (490, 100), (530, 160), (600, 220), (632, 280), (628, 340), (585, 385), (565, 450), (578, 510), (555, 540), (470, 560), (400, 590),
        (340, 615), (320, 665), (300, 690), (250, 690), (235, 655), (160, 660), (120, 690), (60, 690), (48, 660), (45, 600), (30, 520),
        (35, 440), (40, 398), (80, 393)]
_CAT_SPOTS = [[(180, 285), (250, 238), (320, 240), (300, 285), (240, 300)], [(390, 255), (430, 245), (425, 290), (400, 295)],
              [(90, 435), (160, 398), (240, 420), (250, 462), (180, 435), (105, 448)], [(441, 70), (455, 40), (476, 42), (482, 78), (448, 88)]]
_CAT_LINES = [[(80, 580), (120, 575), (150, 590)], [(380, 380), (450, 360), (520, 400)],
              # 頭の輪郭と右の耳。頭は胴の前にうずくまって重なるので、外形でなく線で分ける。
              [(80, 395), (150, 400), (235, 392), (270, 400), (295, 470), (300, 560), (270, 640)], [(230, 393), (262, 372), (272, 402)]]
_CAT_EYES = [[(55, 495), (92, 490), (96, 506), (60, 512)], [(135, 515), (176, 500), (181, 513), (140, 526)]]
_MOUSE = [(480, 85), (500, 140), (470, 160), (440, 230), (470, 290), (580, 270), (595, 295), (540, 315), (460, 330), (400, 375),
          (345, 430), (330, 500), (350, 570), (345, 630), (300, 650), (140, 630), (60, 600), (40, 520), (50, 420), (90, 320),
          (150, 240), (190, 190), (220, 100), (265, 88), (300, 100), (340, 80), (430, 70)]
_MOUSE_EYE = [(380, 125), (405, 122), (412, 145), (388, 152)]
_MOUSE_LINES = [[(120, 400), (140, 460)], [(170, 380), (190, 450)], [(220, 300), (240, 360)], [(90, 500), (110, 560)], [(260, 420), (280, 480)]]


def _fit(raw, w, h):
    """手で取った点を、幅 w・高さ h の箱に入れる（下の端は h − 0.4。足の折り線に絵を掛けないため）。"""
    xs, ys = [x for x, _ in raw], [y for _, y in raw]
    x0, y0, sx, sy = min(xs), min(ys), w / (max(xs) - min(xs)), (h - 0.4) / (max(ys) - min(ys))
    return lambda pts: [((x - x0) * sx, (y - y0) * sy) for x, y in pts]


def _figure(number, key, name, raw, w, h, foot, fill, spots, lines, eye=None):
    """平たい像に、床（板）に貼る足を付ける。足の幅は像の幅の foot の範囲。足と絵の間に 2mm の台を挟み、絵を折り線から離す。"""
    fit = _fit(raw, w, h)
    body = Polygon(fit(raw))
    if not body.is_valid:
        body = body.buffer(0)
    a, b = w * foot[0], w * foot[1]
    shape = body.union(rect(a, h - 2.5, b, h + FIG_TAB)).simplify(0.05)
    outline = list(shape.exterior.coords)[:-1]
    part = Part(number, key, name, outline, label_xy=(a + 0.5, h + 0.8), label=str(number))
    part.valley = [((a, h), (b, h))]
    part.glue = [[(a, h), (b, h), (b, h + FIG_TAB), (a, h + FIG_TAB)]]
    inner = body.buffer(-0.2)
    part.art = [{"kind": "poly", "pts": fit(raw), "fill": fill, "stroke": INK, "sw": 0.25}]
    part.art += [{"kind": "poly", "pts": list(Polygon(fit(sp)).intersection(inner).exterior.coords)[:-1], "fill": INK} for sp in spots]
    if eye:
        part.art.append({"kind": "poly", "pts": fit(eye), "fill": INK})
    for ln in lines:
        piece = LineString(fit(ln)).intersection(inner)
        for g in getattr(piece, "geoms", [piece]):
            if not g.is_empty and g.geom_type == "LineString":
                part.art.append({"kind": "line", "pts": list(g.coords), "stroke": INK, "sw": 0.3})
    return part


def parts(p):
    out = [_box(p)]
    if p["form"] == "lid":
        out += [_lid(p), _stop(p)]
    else:
        out.append(_sleeve(p))
    out.append(_partition(p))
    out.append(_figure(5, "cat", "猫", _CAT, p["cat_w"], p["cat_h"], (0.2, 0.65), CAT, _CAT_SPOTS + _CAT_EYES, _CAT_LINES))
    out.append(_figure(6, "mouse", "鼠", _MOUSE, p["mouse_w"], p["mouse_h"], (0.15, 0.55), MOUSE, [], _MOUSE_LINES, _MOUSE_EYE))
    return out


def place(by_key, page, top, gap):
    """1 段目に箱の展開図。lid は 2 段目に蓋と、その右に仕切りと止め、3 段目に猫と鼠、説明の列はその右。
    sleeve は 2 段目に外箱、その右に仕切り・猫・鼠を縦に、説明の列は外箱の下。物差し（100mm）が入るよう、列の左は 100mm より左。"""
    bx = by_key["box"]
    bx.x, bx.y = page.x0, top
    y = top + bx.height + gap
    part, cat, mouse = by_key["partition"], by_key["cat"], by_key["mouse"]
    if "lid" in by_key:
        lid, stop = by_key["lid"], by_key["stop"]
        lid.x, lid.y = page.x0, y
        x = page.x0 + lid.width + gap
        part.x, part.y = x, y
        stop.x, stop.y = x, y + part.height + gap
        y = y + max(lid.height, part.height + gap + stop.height) + gap
        cat.x, cat.y = page.x0, y
        mouse.x, mouse.y = page.x0 + cat.width + gap, y + cat.height - mouse.height
        x = mouse.x + mouse.width + gap
        return y, page.x1 - x, x
    sl = by_key["sleeve"]
    sl.x, sl.y = page.x0, y
    x = page.x0 + sl.width + gap
    part.x, part.y = x, y
    cat.x, cat.y = x, y + part.height + gap
    mouse.x, mouse.y = x, cat.y + cat.height + gap
    y = y + max(sl.height, mouse.y + mouse.height - y) + gap
    return y, page.x1 - page.x0, page.x0


def bom(p):
    paper = paper_name(thickness=p['paper_thickness'])
    why = "家庭のプリンタで刷って作るため"
    lid = p["form"] == "lid"
    rows = [
        {"number": 1, "key": "box", "name": "箱" if lid else "中箱", "qty": 1, "material": paper, "substituted": True, "original_guess": "木の箱（図の色と板の厚みからの推定）", "reason": why},
    ]
    if lid:
        rows += [
            {"number": 2, "key": "lid", "name": "蓋", "qty": 1, "material": paper, "substituted": True, "original_guess": "木の板（同じ）", "reason": why},
            {"number": 3, "key": "stop", "name": "止め", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明（図に見えない。紙で落ちないために足した）", "reason": "蓋が箱から抜けないため"},
        ]
    else:
        rows.append({"number": 2, "key": "sleeve", "name": "外箱", "qty": 1, "material": paper, "substituted": True, "original_guess": "木の板（同じ。外箱の形は推定）", "reason": why})
    rows += [
        {"number": 4, "key": "partition", "name": "仕切り", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明（図の線を仕切りと読んだ）", "reason": "止めを受け、動く長さを決めるため"},
        {"number": 5, "key": "cat", "name": "猫", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明（張子か木彫りか土か、図から分からない）", "reason": why},
        {"number": 6, "key": "mouse", "name": "鼠", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明（同じ）", "reason": why},
    ]
    return rows


def materials(p):
    by = {r["key"]: r for r in bom(p)}
    return [f"{by['box']['material']}を 1 枚", "のり、はさみ、定規"]


def steps(p):
    out = ["刷った物差しに定規を当て、10cm か確かめる", "部品を実線で切る"]
    name = "箱" if p["form"] == "lid" else "中箱"
    out += [f"1 {name}を破線で谷折りして立て、角の糊代を側の壁の内に貼る（糊代を外に出すと道に擦れる）",
            f"4 仕切りの糊代を後ろへ折り、床の印（前の壁から {p['partition_at']:g}mm）に立てて側の壁の内に貼る",
            f"6 鼠の足を折り、床の印（前の壁から {p['mouse_at']:g}mm）に貼る"]
    if p["form"] == "lid":
        out += [f"3 止めの足を 2 蓋の裏に貼る。足の前の端を、左右の袴の印（前の縁から {STOP_AT}mm）に合わせ、舌を下へ折る",
                "2 蓋の左右の袴を山折りし、箱の上に載せて袴で側の壁を挟む。止めは前の壁と仕切りの間に入れる",
                "5 猫の足を折り、蓋の表の前の縁に貼る", "蓋を後ろへ引くと鼠が出て、前へ戻すと隠れるか見る"]
    else:
        out += ["2 外箱を山折りして筒にし、継ぎ目の糊代を底の内に貼る（表が外）", "上の面の前の縁を内へ折る（止め）",
                "1 中箱を外箱の後ろから差し込む（前の壁の低い方を前へ）", "5 猫の足を折り、外箱の上の印に貼る",
                "中箱の前の壁をつまんで引くと鼠が出て、押すと隠れるか見る"]
    return out


RESULTS = ("鼠が出て隠れた", "動かない")


def measures(p):
    """出るかの二択でなく、引き方と鼠の出方を言葉か絵で予想する（ほかの雛形と同じ形）。"""
    return {"predict": "板を引くと、猫と鼠はどうなると思いますか（言葉か絵で）", "rows": [[("引き方（速さ・向き）", 40)]]}


def diagram(x, y, w, h, p):
    """横から見た絵。箱・仕切り・鼠と、動いた後の板（点線）を並べるだけで、寸法の図ではない。"""
    L, H = p["box_l"], p["box_h"]
    s = travel(p)
    sc = min(w / (L + s), h / (H + p["cat_h"] + 4))
    # 枠の幅は L + s で取る。lid は蓋が後ろ（右）へ s 動くので箱を枠の左に、sleeve は中箱が前（左）へ s 出るので
    # 箱（閉じた位置）を s だけ右に置く。sleeve でも箱を枠の左に置いていた時は、引き出した中箱が枠の左の外に出た。
    bx, by = (x if p["form"] == "lid" else x + s * sc), y + (p["cat_h"] + 2) * sc
    shapes = [{"kind": "rect", "x": bx, "y": by, "w": L * sc, "h": H * sc}]
    shapes.append({"kind": "line", "x1": bx + p["partition_at"] * sc, "y1": by, "x2": bx + p["partition_at"] * sc, "y2": by + H * sc})
    shapes.append({"kind": "rect", "x": bx + p["mouse_at"] * sc, "y": by + (H - p["mouse_h"]) * sc, "w": p["mouse_w"] * sc, "h": p["mouse_h"] * sc})
    if p["form"] == "lid":
        shapes.append({"kind": "line", "x1": bx + s * sc, "y1": by - 0.5, "x2": bx + (s + L) * sc, "y2": by - 0.5, "dash": "1,0.6"})
        shapes.append({"kind": "rect", "x": bx + s * sc, "y": by - p["cat_h"] * sc, "w": p["cat_w"] * sc, "h": p["cat_h"] * sc})
    else:
        shapes.append({"kind": "rect", "x": bx - s * sc, "y": by, "w": L * sc, "h": H * sc, "dash": "1,0.6"})
        shapes.append({"kind": "rect", "x": bx, "y": by - p["cat_h"] * sc, "w": p["cat_w"] * sc, "h": p["cat_h"] * sc})
    return shapes
