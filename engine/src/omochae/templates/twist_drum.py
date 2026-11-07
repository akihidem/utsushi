"""雛形 twist_drum: 柄を指で回すと、鼓の左右に下げた玉が振れて面を打つ（でんでん太鼓・振り鼓）。

紙の部品は、面 2 枚・胴の帯（糊代の歯つき。丸めて胴にする）・柄の巻き紙。竹串・糸・玉は部品表に載せる。
面の絵は出典ごとに違うので、刷る形（face）で描き分ける。鳥の面（コマ 29）は図に幣（紙の房）が付くので、房の部品が 1 つ増える。
諫鼓（コマ 10、face=kanko）は柄の無い形で、台の上の柱に長い鼓を載せ、台の花車を回して玉を振る。仕組みは【解釈】（下の KANKO の注）。
寸法は手元の複写の図の比から出した見込みで、どの値も実物では未確認。Claude が変えてよいのは RANGES の名前の値だけ。

動きの見込み（F5.drum）の前提:
- 鼓の軸は横、柄（竹串）は胴を縦に貫く。糸は胴の帯の左右（柄から 90° の所）の帯の幅の真ん中に結ぶ。
- 柄を速く回すと、玉は結び目の高さの水平面をほぼ回ると見る（重力と糸のたるみは入れない）。
  糸は胴の中を通れない。結び目（帯の幅の真ん中）から面へ向かう糸は、帯の表に沿って帯の縁（面の縁）まで行き、縁で曲がって面の上へ出る。
  だから面の上の玉は、帯の縁を中心に、糸の長さから奥行きの半分を引いた残りを半径にして回る。
  前は、結び目を中心に糸の全長で回ると見ていた（糸が胴の角を突き抜ける形）。その式は打つ点を面の中心の側へ 5mm ほど寄せて出し、
  縁の近くを打つ短い糸（既定の寸法で 18.4〜22.6mm）を通していた。
  玉は点でない。糸は玉の中心までの長さなので、玉の表が面に触れる時、中心は面より玉の半径だけ外にある。
  打つ点が面の中心から半径の半分の内に入る糸の長さを求める。縁に近いと胴の帯が硬く、鳴りが鈍いと見込む（実物で確かめていない）。
- 玉が胴の下へ回り込んで、胴の下に出た柄に届くと糸が柄に絡む。結び目から柄の一番近い点（胴の下の縁の柄）までは、まっすぐ測って √2 × 半径。
  柄の太さの半分を引いた長さより、糸の長さ＋玉の半径が短ければ（等しいと届くので落とす）絡まない（たるみ・玉の跳ね返りは入れない）。
  この「まっすぐ」は胴の中を通る線で、上の「糸は胴の中を通れない」と形がそろっていない。帯の表に沿って測ると道のりはもっと長い
  （既定の寸法で 37mm ほど。手で数えた見込み）ので、まっすぐの距離は厳しい側の下限になる。検査を緩める直しは決まりで人が決めるので、
  ここでは下限のまま残す。そのため小さい面（半径 15〜16mm）では、打つ点の下限と合わせると通る糸が無い（検査が落とす）。
"""
import math

from shapely.geometry import Polygon

from ..paper_words import paper_name  # 紙の書き方は 4 つの名前だけ（制作者の指示 2026-11-05）
from ..model import Failure, Part

ID = "twist_drum"
DEFAULTS = {
    "face": "kiku",
    # 面の半径と胴の奥行き。コマ 7 の図で、奥行きは面の直径の 3 割強に見える（斜めの図を目測）。
    "radius": 26, "depth": 18, "tab": 6, "seam_glue": 8,
    # 柄は竹串。太さ 3mm・長さ 180mm は家にある竹串の見込み。
    "stick_d": 3, "handle_length": 90, "wrap_glue": 3,
    # 糸 27 は、既定の寸法の糸の窓（22.6〜31.3mm）の真ん中。前の 24 は、帯の縁で曲がる分を入れると下限まで 1.4mm しか無かった。
    "cord_length": 27, "bead_d": 8,
    # 0.15mm はふつうの厚めの紙の見込み。実物の紙を測ったら置き換える。
    "paper_thickness": 0.15,
    # 諫鼓（face=kanko）だけが使う寸法。鼓の形が違う（長い胴を横に寝かせる）ので、でんでん太鼓の寸法と名を分ける。
    # 比はコマ 10 の図の目測: 胴の長さは面の直径の 1.2 倍ほど、柱は面の半径ほど、花車は面の半径の半分ほど。
    "k_radius": 18, "k_length": 44, "k_cord": 9.5,
    "post_side": 8, "post_height": 20, "post_pos": 18,
    # 台の幅と壁の高さは図の比（34・15）より広く高い。7mm の旗が棒の上に立ち、棒が穴の中で浮いても天井の下に収まる（壁 17.8mm 以上）、
    # 旗が東の壁の側へ倒れても当たらない（幅 35.6mm 以上）最小の値を切り上げた（壁は 1mm 余らせて 19。check_kanko の留め具の 2 つの検査が決める）。
    # 台の長さ 90 は、棒を引き切った時に軸が回る数（pull_turns）が、少ない側の見込みで 1.3 回・多い側で 2.1 回になる値。
    # 図の比に近い 80 では、少ない側で 1 回に届かない（0.5〜1.1 回）。これより長いと引く棒が竹串に収まらなくなる（92 で先を落とした 164mm ちょうど）。
    "base_length": 90, "base_width": 36, "base_height": 19,
    "wheel_r": 9, "peg_height": 38, "face_gap": 20,
}
RANGES = {
    # 半径の上限 28 は、胴の帯（円周＋糊代）が A4 の印字域の幅 190mm に 1 本で入るため。
    "radius": (15, 28), "depth": (8, 30), "tab": (3, 10), "seam_glue": (5, 12),
    "stick_d": (2, 5), "handle_length": (40, 130), "wrap_glue": (2, 6),
    "cord_length": (5, 60), "bead_d": (4, 14),
    "paper_thickness": (0.05, 0.5),
    "k_radius": (12, 24), "k_length": (20, 60), "k_cord": (3, 40),
    "post_side": (5, 14), "post_height": (8, 50), "post_pos": (5, 70),
    "base_length": (50, 100), "base_width": (24, 50), "base_height": (8, 25),
    "wheel_r": (8, 16), "peg_height": (10, 80), "face_gap": (8, 50),
}
FACES = ("kiku", "tori", "kanko")
# 刷る形を決める寸法（面の絵と、幣の房があるか）。どの面が「正しい」かは無いので、寸法を直に渡す入口では必ず書かせる。
FORM = "face"
FORMS = FACES
# 既定の出典（data/sources/ の名前）。--source を書かない時に、雛形と合わない出典の印を刷らないため。
SOURCE = "NDL-1187053-R0000007-R-twist_drum"
# 刷る形ごとの出典。面の絵はコマごとに違うので、形と合わない出典の印を刷らない（compose が F1.source で落とす）。
SOURCES = {"kiku": SOURCE, "tori": "NDL-1187053-R0000029-L-twist_drum", "kanko": "NDL-1187053-R0000010-R-twist_drum"}
HOLE_MARGIN = 3  # 穴から紙の端（帯の縁・継ぎ目の糊代）までの見込み。これより狭いと串を回した時に裂けやすい
SKEWER_LEN = 180  # 家にある竹串の長さの見込み（実物を測ったら置き換える）
# 竹串のとがった先は、危ないので両端とも切り落とす。でんでん太鼓は帯の穴を先であけてから落とす（穴をあける道具を増やさない）。
# 諫鼓は、丸い穴を竹串の先であけた後、軸と棒の長さに切る前に 3 本とも落とす。1 つの先を落とす長さは見込み（実物で確かめていない）。
SKEWER_POINT = 8
SKEWER_USABLE = SKEWER_LEN - 2 * SKEWER_POINT
# 利用者に見せる文（用意する物・組み方・見取り図の言葉）は、小学生にも分かるやさしい言葉で書く（2026-11-06 の制作者の決定で、
# twist_drum の文を書き直した。ほかの雛形はまだ「〜する」の形）。書き方の決め:
# - 組み方は「です・ます」で、1 文を短くする。小学校で習わない字はかなにする（糊→のり・貼る→はる・竹串→竹ぐし・菱形→ひし形・端→はし・縁→ふち）
# - 折る線は、紙の凡例の言葉（切る・山折り・谷折り）で言う。凡例に無い線の名（実線・一点鎖線・破線）は使わない
# - 部品の名（胴・柄・軸・幣の房・花車など）は紙に刷ってあるので変えない。【解釈】の印も変えない
# - 行数は書き直す前の上限（下の STEP_LINES_*）に収める。寸法を乱数で動かして確かめた（11-06）: でんでん太鼓は前の文より長くなる寸法が無い。
#   諫鼓は 1 割ほどの寸法で前より 1 行長いが、一番長い時は 41 行で、前の文の一番長い時（42 行）より短い
CUT_POINTS = "、とがった先を両はしともニッパーかカッターで切り落とします（大人がします）"
CUT_TOOL = "ニッパーかカッター（竹ぐしを切る道具。大人が使います）"
TOP_OUT = 5  # 柄の先を胴の上へ出す長さ。抜け止めに糸を巻くため（幣の房の無い形）
CORD_SPARE = 30  # 玉の糸を切る時に、糸の長さ（結び目から玉の中心）へ足す余り
# 組み方の文の行数の上限。手順の紙は廃止し（制作者の決まり 2026-11-06「文章のプリントは廃止。組み立て用のページだけでいい。」）、文はサイトの組み立ての頁に出す。画面でも短い方が読みやすいので上限は残す。
# 上限を決めた時の理由: 前のサイトの手順の紙（A4）は、左の列 144mm に字 3.6mm で「番号. 文」を刷り、その下に予想・試した事・問いの欄が続いた。
# でんでん太鼓は 16 行までなら紙に収まる（2026-11-05 にサイトの手順の紙の組み立てに載せて測った。16 行で 2.8mm 余り、1 行は 4.5mm）。
# 糸を留める手順と直しの幅を足した時に 22〜23 行になり、紙の下へ 14〜19mm はみ出したので、言い回しを詰めた（今は菊の面 14 行・鳥の面 15 行。
# やさしい言葉に書き直した後も同じ。「です・ます」で長くなる分は、線の名を凡例の言葉にし、1 行に収まらない文を言い直して詰めた）。
# 諫鼓は部品が 12 あり、前から 1 枚に収まっていない（27 行で 37mm はみ出していた。糸を軸に留める・軸受け・巻く向きを足した今は 41 行で 100mm）。
# 1 枚に収めるには組み方を別の紙に分ける要があり、それはサイトの側の決め事。ここでは行数が黙って増えないよう、今の行数を上限にする。
STEP_COL_W, STEP_SIZE, STEP_LINES_MAX, STEP_LINES_KANKO = 144.0, 3.6, 16, 41


def stick_cut(p):
    """柄の竹串を切る長さ ＝ 胴の下の柄 ＋ 胴の直径 ＋ 胴の上へ出す長さ。部品表と組み方の文はこの 1 つの式から書く。
    切らずに 180mm のまま通すと、上を決めた分だけ下が余り、柄の巻き紙（柄より 2mm 短い）と合わなかった。"""
    return p["handle_length"] + 2 * p["radius"] + top_out(p)


def top_out(p):
    """竹串を胴の上へ出す長さ。鳥の面は幣の房の上の帯（STREAMER_TOP）をこの出た所に巻いて貼るので、帯の幅＋2mm 出す。
    5mm のままだと 8mm の帯を巻く所が無く、組めなかった。"""
    return STREAMER_TOP + 2 if p["face"] == "tori" else TOP_OUT
TAB_PITCH = 8  # 糊代の歯の目安の幅。細かいほど丸く貼れるが、切るのが手間になる
STRIKE_ZONE = 0.5  # 打つ点が面の中心から半径のこの割合の内に入れば、鳴ると見込む（縁は鳴りが鈍い）
FACE, INK, BAND, BAND_DARK, BAMBOO, CORD_MARK, PAPER = "#ddd0aa", "#3b3a34", "#9a5a35", "#6e4128", "#cdb98a", "#e8dfc6", "#ece6d6"
TITLES = {"kiku": "菊の面", "tori": "鳥の面と幣", "kanko": "諫鼓と花車【解釈】"}
# サイトが見取り図（diagram）の下に出す言葉（前は手順の紙に刷った。手順の紙は廃止し、組み立ての頁に出す）。雛形が持たないと、御来迎の言葉（閉じた時の中の様子・破線は筒の中）が鼓の図に刷られる。
# どの形の図でも、破線は振れた時の玉の糸。利用者に見せる言葉なので「破線・振れた」を「点線・ふれた」と言う。
DIAGRAM_CAPTION = "組み上がりの様子（点線は、ふれた玉の糸）"


def title(p):
    return TITLES[p["face"]]


def spec():
    return {"template_id": ID, "defaults": DEFAULTS, "ranges": RANGES, "face": FACES}


def check_range(p):
    out = []
    for k, v in p.items():
        if k == "face":
            if v not in FACES:
                out.append(Failure("F5.range", k, f"{v} は {FACES} のどれでもない"))
        elif k not in RANGES:
            out.append(Failure("F5.range", k, "知らない寸法の名前"))
        elif not isinstance(v, (int, float)) or isinstance(v, bool) or not RANGES[k][0] <= v <= RANGES[k][1]:
            out.append(Failure("F5.range", k, f"{v} は範囲 {RANGES[k]} の外"))
    return out


def drum_rd(p):
    """鼓の面の半径と胴の奥行き（帯の幅）。諫鼓は長い胴なので別の寸法の名から取る。"""
    if p["face"] == "kanko":
        return p["k_radius"], p["k_length"]
    return p["radius"], p["depth"]


def circumference(p):
    """胴の帯の長さ（糊代を除く）。面は内へ折った歯に外から貼り、面の縁と帯の外の面をそろえる見込み。
    帯の厚みの真ん中は面の縁から紙の厚みの半分だけ内にあるので、半径から厚みの半分を引いた円周にする。"""
    return 2 * math.pi * (drum_rd(p)[0] - p["paper_thickness"] / 2)


def band_length(p):
    """胴の帯の全長 ＝ 円周 ＋ 継ぎ目の糊代。帯を切り出す長さはこの 1 つの式から出す（型紙と試験が同じ値を使う）。"""
    return circumference(p) + p["seam_glue"]


def tab_teeth(p):
    """糊代の歯の数・間隔・肩の削り。歯を内へ折ると先は半径 (R − tab) の円に乗り、長さが (R − tab)/R に縮む。
    隣の歯と重ならないよう、先の幅を同じ割合に詰め、さらに両肩を 0.3mm ずつ空ける。"""
    n = max(1, round(circumference(p) / TAB_PITCH))
    pitch = circumference(p) / n
    inset = pitch * p["tab"] / (2 * drum_rd(p)[0]) + 0.3
    return n, pitch, inset


def stick_hole_r(p):
    return p["stick_d"] / 2 + 0.1  # 串が回らずに締まるよう、穴は串よりわずかに大きいだけにする


def hole_positions(p):
    """帯の上の穴の位置（継ぎ目から測った長さ）。柄の穴は向かい合う 2 つ、糸の穴はそこから 90° の 2 つ。
    継ぎ目の糊代（帯の頭の 0〜seam_glue）に穴が来ないよう、円周の 1/8 ずらして置く。"""
    c = circumference(p)
    return {"stick": (c / 8, 5 * c / 8), "cord": (3 * c / 8, 7 * c / 8)}


def cord_window(p):
    """糸の長さ（結び目から玉の中心まで）の下限と上限。前提は module の docstring。

    帯の縁から先の糸を f = L − D/2（free_cord）、玉の半径を b とする。面に触れた玉の中心は、帯の縁から面に沿って √(f² − b²) 内にある。
    下限: 打つ点 x = R − √(f² − b²) が面の中心から STRIKE_ZONE·R の内 → L ≧ D/2 + √(((1 − k)R)² + b²)。
    上限: 反対側へ行き過ぎない L ≦ D/2 + √(((1 + k)R)² + b²) と、柄に絡まない L + b < √2·R − 柄の半径 の小さい方。
    返す上限は 2 つの小さい方の値。柄の側は等号も落とす（check の側で厳密に見る）。
    """
    R, b, k = p["radius"], p["bead_d"] / 2, STRIKE_ZONE
    low = p["depth"] / 2 + math.hypot((1 - k) * R, b)
    high = min(far_limit(p), tangle_limit(p))
    return low, high


def free_cord(p):
    """帯の縁から先の糸の長さ（玉の中心まで）。糸は結び目から縁まで、帯の表に沿って奥行きの半分を使う。"""
    return p["cord_length"] - p["depth"] / 2


def far_limit(p):
    """面の中心を越えて、反対の縁の近くを打つ手前の糸の長さ（この長さまでは通す）。
    今の柄の側の上限（tangle_limit）は、範囲のどの寸法でもこれより短いので、この上限が先に効く事は無い（上限を帯に沿う道のりへ替えた時に効く）。"""
    return p["depth"] / 2 + math.hypot((1 + STRIKE_ZONE) * p["radius"], p["bead_d"] / 2)


def tangle_limit(p):
    """垂れた玉が柄に届く糸の長さ（この長さちょうどでも届くので、これより短い糸だけ通す）。
    柄は太さがあるので、結び目から柄の表までの距離の下限 √2·R − 柄の半径 を使う（本当の距離は √((R − r)² + R²)、r は柄の半径で、
    これより少し長い）。下限で見るので、絡まない側に厳しく倒れる。そこから玉の半径を引く。"""
    return math.sqrt(2) * p["radius"] - p["stick_d"] / 2 - p["bead_d"] / 2


def strike_offset(p):
    """玉が面を打つ点の、面の中心からの距離（正は結び目の側）。帯の縁から先の糸が玉の半径に届かなければ None（玉が面の上へ出ない）。"""
    f, b = free_cord(p), p["bead_d"] / 2
    if f <= b:
        return None
    return p["radius"] - math.sqrt(f * f - b * b)


def check_physics(p):
    if p["face"] == "kanko":
        return check_kanko(p)
    return _check_hand(p)


def _check_hand(p):
    """F5.drum: 玉が面を打つ・柄に絡まない・串の穴が裂けない・帯の歯が貼れる・竹串が足りる、を見る。"""
    out = []
    low, high = cord_window(p)
    L = p["cord_length"]
    if L < low:
        x = strike_offset(p)
        where = "面に届かない" if x is None else f"面の中心から {x:.1f}mm の縁の近くを打つ"
        out.append(Failure("F5.drum", "糸", f"糸 {L:g}mm は短く、{where}（{low:.1f}mm 以上）"))
    if L >= tangle_limit(p):
        out.append(Failure("F5.drum", "糸", f"糸 {L:g}mm は長く、垂れた玉が柄に届いて絡む（{tangle_limit(p):.1f}mm より短く）"))
    elif L > far_limit(p):
        out.append(Failure("F5.drum", "糸", f"糸 {L:g}mm は長く、玉が面の中心を越えて反対の縁の近くを打つ（{far_limit(p):.1f}mm まで）"))
    r = stick_hole_r(p)
    edge = p["depth"] / 2 - r
    if edge < HOLE_MARGIN:
        out.append(Failure("F5.drum", "柄の穴", f"柄の穴から帯の縁まで {edge:.1f}mm で、回すと裂けやすい（{HOLE_MARGIN}mm 以上）"))
    seam = hole_positions(p)["stick"][0] - r - p["seam_glue"]
    if seam < HOLE_MARGIN:
        out.append(Failure("F5.drum", "柄の穴", f"柄の穴から継ぎ目の糊代まで {seam:.1f}mm で、継ぎ目が剥がれやすい（{HOLE_MARGIN}mm 以上）"))
    _, pitch, inset = tab_teeth(p)
    if pitch - 2 * inset < 1:
        out.append(Failure("F5.drum", "糊代の歯", f"歯の先が {pitch - 2 * inset:.1f}mm で、面を貼る所が無い（歯が深すぎる）"))
    need = stick_cut(p)
    if need > SKEWER_USABLE:
        out.append(Failure("F5.drum", "柄", f"柄に竹串が {need:.0f}mm 要り、先を落とした {SKEWER_USABLE}mm の竹串で足りない"))
    return out


def _circle(cx, cy, r, n=72, a0=0.0):
    return [(cx + r * math.cos(a0 + 2 * math.pi * i / n), cy + r * math.sin(a0 + 2 * math.pi * i / n)) for i in range(n)]


def _ring(cx, cy, r, sw):
    """細い輪は閉じた線で描く（絵の面は穴の無い多角形だけなので、輪を面にすると形が壊れる）。"""
    pts = _circle(cx, cy, r)
    return {"kind": "line", "pts": pts + [pts[0]], "stroke": INK, "sw": sw}


def _petal(cx, cy, r0, r1, a, w):
    """菊の花弁 1 枚。根元 r0 から先 r1 へ、幅 w の細い葉形。コマ 7 の図の 16 弁の形を手で取った。"""
    ca, sa = math.cos(a), math.sin(a)
    rm = r0 + (r1 - r0) * 0.7
    pts = [(r0, 0), (rm, w / 2), (r1, w * 0.18), (r1 + w * 0.15, 0), (r1, -w * 0.18), (rm, -w / 2)]
    return [(cx + x * ca - y * sa, cy + x * sa + y * ca) for x, y in pts]


# コマ 29 の鳥。面の図を 800 四方に拡大し、面の中心 (395, 385)・半径 295 の座標で手で取った点。画素は使っていない。
_BIRD = [(165, 365), (205, 325), (230, 290), (280, 275), (330, 290), (352, 300), (350, 240), (380, 200), (440, 178), (530, 170), (505, 195), (520, 212),
         (470, 228), (440, 290), (500, 298), (560, 265), (612, 245), (615, 275), (648, 285), (655, 322), (600, 332), (532, 362), (515, 405), (548, 462),
         (528, 478), (505, 452), (495, 495), (480, 545), (462, 568), (452, 520), (420, 560), (350, 612), (380, 565), (300, 562), (250, 532), (225, 482),
         (248, 445), (300, 420), (322, 405), (268, 392), (232, 362), (205, 385), (192, 378)]
_BIRD_EYE = (232, 318, 14)


def _bird(cx, cy, s):
    return [(cx + (x - 395) * s, cy + (y - 385) * s) for x, y in _BIRD]


def _face_art(p):
    R = drum_rd(p)[0]
    art = [{"kind": "poly", "pts": _circle(R, R, R - 0.3), "fill": FACE}]
    if p["face"] == "kanko":
        art += _tomoe_art(R)
    elif p["face"] == "kiku":
        # コマ 7: 面の中に 2 重の輪（半径の 0.66・0.60）、その内に 16 弁の菊と小さな芯。
        art += [_ring(R, R, 0.66 * R, 0.025 * R), _ring(R, R, 0.60 * R, 0.025 * R)]
        for i in range(16):
            art.append({"kind": "poly", "pts": _petal(R, R, 0.09 * R, 0.46 * R, 2 * math.pi * i / 16 - math.pi / 2, 0.11 * R), "fill": INK})
        art.append({"kind": "poly", "pts": _circle(R, R, 0.06 * R, 24), "fill": INK})
    else:
        # コマ 29: 面いっぱいの鳥。図では面の輪の内の半径 295 に描かれているので、面の半径の 0.9 に縮める。
        s = 0.9 * R / 295
        art.append({"kind": "poly", "pts": _bird(R, R, s), "fill": INK})
        ex, ey, er = _BIRD_EYE
        art.append({"kind": "poly", "pts": _circle(R + (ex - 395) * s, R + (ey - 385) * s, er * s, 16), "fill": FACE})
    return art


def _disc(number, key, name, p):
    R = drum_rd(p)[0]
    return Part(number, key, name, _circle(R, R, R), label_xy=(R - 1.5, 2 * R - 5), label=str(number), art=_face_art(p))


def _band(p):
    C, g, t, D = circumference(p), p["seam_glue"], p["tab"], drum_rd(p)[1]
    n, pitch, inset = tab_teeth(p)
    top, bot, H = t, t + D, D + 2 * t
    pts = [(0, top)]
    teeth = []
    for i in range(n):
        a, b = i * pitch, (i + 1) * pitch
        pts += [(a + inset, 0), (b - inset, 0), (b, top)]
        teeth.append([(a, top), (a + inset, 0), (b - inset, 0), (b, top)])
    pts += [(C + g, top), (C + g, bot), (C, bot)]
    for i in reversed(range(n)):
        a, b = i * pitch, (i + 1) * pitch
        pts += [(b - inset, H), (a + inset, H), (a, bot)]
        teeth.append([(b, bot), (b - inset, H), (a + inset, H), (a, bot)])
    band = Part(3, "band", "胴の帯", pts, label_xy=(2, top + 1.5), label="3 胴")
    # 歯は、絵（刷った面）を外にして胴の内へ折る。刷った面から見ると折り目が手前に出るので山折り（凡例）。
    # 前は谷折りの線で刷っていて、同じ紙の留め具の旗（谷折り＝刷った面が内）と線の意味が食い違っていた。
    band.mountain = [((0, top), (C, top)), ((0, bot), (C, bot))]
    # 継ぎ目の糊代は帯の終わりに置き、帯の頭の下に入れて貼る（頭の側の絵が外に見える）。
    band.glue = teeth + [[(C, top), (C + g, top), (C + g, bot), (C, bot)]]
    band.art = [{"kind": "poly", "pts": [(0.2, top + 0.2), (C - 0.2, top + 0.2), (C - 0.2, bot - 0.2), (0.2, bot - 0.2)], "fill": KANKO_BODY if p["face"] == "kanko" else BAND}]
    # 帯の上下の縁の濃い筋（コマ 7 の胴の縁の影）。
    for y0 in (top + 0.2, bot - 1.4):
        band.art.append({"kind": "poly", "pts": [(0.2, y0), (C - 0.2, y0), (C - 0.2, y0 + 1.2), (0.2, y0 + 1.2)], "fill": BAND_DARK})
    mid = top + D / 2
    if p["face"] == "kanko":
        # 諫鼓は柄を通さず、柱の頭を帯の四角い穴に差す。穴は継ぎ目の向かい（円周の半分）に置き、糊代から一番遠くする。
        cs = p["post_side"] + POST_FIT
        band.cuts = [(C / 2 - cs / 2, mid - cs / 2, cs, cs)]
        return band
    pos = hole_positions(p)
    # コマ 7 の胴の白い菱形（糸の留め）を、糸の穴のまわりに描く。
    for s in pos["cord"]:
        d = min(3.0, D / 2 - 1.6)
        band.art.append({"kind": "poly", "pts": [(s, mid - d), (s + d, mid), (s, mid + d), (s - d, mid)], "fill": CORD_MARK})
    band.holes = [(s, mid, stick_hole_r(p)) for s in pos["stick"]] + [(s, mid, 0.6) for s in pos["cord"]]
    return band


def wrap_size(p):
    """柄の巻き紙の幅と長さ。幅は串の周りを紙の厚みの真ん中で 1 周＋糊代、長さは胴の下の柄から 2mm 短く（胴に当てない）。"""
    return math.pi * (p["stick_d"] + p["paper_thickness"]) + p["wrap_glue"], p["handle_length"] - 2


def _wrap(p):
    w, L = wrap_size(p)
    g = p["wrap_glue"]
    part = Part(4, "wrap", "柄の巻き紙", [(0, 0), (w, 0), (w, L), (0, L)], label_xy=(0.6, 1.5), label="4")
    part.glue = [[(w - g, 0), (w, 0), (w, L), (w - g, L)]]
    part.art = [{"kind": "poly", "pts": [(0.2, 0.2), (w - g - 0.2, 0.2), (w - g - 0.2, L - 0.2), (0.2, L - 0.2)], "fill": BAMBOO}]
    return part


# 幣の房（コマ 29）。上の帯を柄の先に巻いて貼り、下の 3 本の房を垂らす。房の幅と長さは図の比の目測。
# 房は 50mm あり、止まっている時は胴の上から面の前へ垂れる（玉が打つ所にかかる）。回している間は外へ広がると見て、長さは図の比のままにした。
# 元の図（コマ 29）では、房は胴の上へ長く出た柄の先から、胴の横へ下がっている。面の邪魔になるかは実物で確かめていない。
STREAMER_TEETH, STREAMER_W, STREAMER_GAP, STREAMER_TOP, STREAMER_LEN = 3, 5, 2.5, 8, 50


def _streamer():
    W = STREAMER_TEETH * STREAMER_W + (STREAMER_TEETH - 1) * STREAMER_GAP
    pts = [(0, 0), (W, 0)]
    # 右の房から左へ、房の外形と房の間の切り込みを順に回る。
    for i in reversed(range(STREAMER_TEETH)):
        a = i * (STREAMER_W + STREAMER_GAP)
        pts += [(a + STREAMER_W, STREAMER_TOP + STREAMER_LEN), (a, STREAMER_TOP + STREAMER_LEN)]
        if i:
            pts += [(a, STREAMER_TOP), (a - STREAMER_GAP, STREAMER_TOP)]
    part = Part(5, "streamer", "幣の房", pts, label_xy=(0.6, STREAMER_TOP + 1.5), label="5")
    part.glue = [[(0, 0), (W, 0), (W, STREAMER_TOP), (0, STREAMER_TOP)]]
    part.art = [{"kind": "poly", "pts": [(a + 0.2, STREAMER_TOP + 0.2), (a + STREAMER_W - 0.2, STREAMER_TOP + 0.2),
                                         (a + STREAMER_W - 0.2, STREAMER_TOP + STREAMER_LEN - 0.2), (a + 0.2, STREAMER_TOP + STREAMER_LEN - 0.2)], "fill": PAPER}
                for a in (i * (STREAMER_W + STREAMER_GAP) for i in range(STREAMER_TEETH))]
    return part


def parts(p):
    if p["face"] == "kanko":
        return [_disc(1, "front", "表の面", p), _disc(2, "back", "裏の面", p), _band(p), _post(p), _base(p), _wheel(p), _rodtab(p), _gauge(p), _bearing(p)]
    out = [_disc(1, "front", "表の面", p), _disc(2, "back", "裏の面", p), _band(p), _wrap(p)]
    if p["face"] == "tori":
        out.append(_streamer())
    return out


def place(by_key, page, top, gap):
    """1 段目に胴の帯（長い）、2 段目の左に面 2 枚を縦に、その右に巻き紙と房。
    説明の列は房の右から。物差し（100mm）が印字域に入るよう、列の左は 100mm より左に来るように並べる。"""
    band = by_key["band"]
    band.x, band.y = page.x0, top
    y = top + band.height + gap
    if "base" in by_key:
        return _place_kanko(by_key, page, y, gap)
    front, back, wrap = by_key["front"], by_key["back"], by_key["wrap"]
    front.x, front.y = page.x0, y
    back.x, back.y = page.x0, y + front.height + gap
    x = page.x0 + front.width + gap
    wrap.x, wrap.y = x, y
    right = x + wrap.width
    if "streamer" in by_key:
        st = by_key["streamer"]
        st.x, st.y = x, y + wrap.height + gap
        right = max(right, x + st.width)
    x = right + gap
    return y, page.x1 - x, x


def bom(p):
    if p["face"] == "kanko":
        return bom_kanko(p)
    paper = paper_name(thickness=p['paper_thickness'])
    why = "家庭のプリンタで刷って作るため"
    # 帯の裏で 2 回重ねて結ぶ分と、玉を付ける所をずらして長さを直す分の余り。15mm では短い糸を指で結べなかった（余りは最後に切る）。
    cord = p["cord_length"] + CORD_SPARE
    rows = [
        {"number": 1, "key": "front", "name": "表の面", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明（紙張りか革張りかは図から分からない）", "reason": why},
        {"number": 2, "key": "back", "name": "裏の面", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明（同じ）", "reason": why},
        {"number": 3, "key": "band", "name": "胴の帯", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明（図では塗った胴）", "reason": why},
        {"number": 4, "key": "wrap", "name": "柄の巻き紙", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明", "reason": "竹串の柄を持ちやすく、図の柄の色に近づけるため"},
        {"number": 7, "key": "stick", "name": "柄", "qty": 1, "material": f"竹ぐし（太さ {p['stick_d']:g}mm・{SKEWER_LEN}mm の物を {stick_cut(p):g}mm に切る）", "substituted": True, "original_guess": "竹か木（図の柄の形からの推定）", "reason": "家にあり、胴に通しやすいため"},
        {"number": 8, "key": "cord", "name": "糸", "qty": 2, "material": f"もめんの糸（1 本 {cord:g}mm に切る）", "substituted": True, "original_guess": "糸か紐（図の線による）", "reason": "家にあるため"},
        {"number": 9, "key": "bead", "name": "玉", "qty": 2, "material": f"油ねんどの玉（直径 {p['bead_d']:g}mm）かビーズ", "substituted": True, "original_guess": "不明", "reason": "大きさを変えて試しやすいため"},
    ]
    if p["face"] == "tori":
        rows.insert(4, {"number": 5, "key": "streamer", "name": "幣の房", "qty": 1, "material": paper, "substituted": True, "original_guess": "紙（図の形からの推定）", "reason": why})
    return rows


def materials(p):
    # 行の位置でなく key で引く。形によって部品表の行が増えるので、位置で引くと別の行を刷る。
    by = {r["key"]: r for r in bom(p)}
    if p["face"] == "kanko":
        # カッターは穴と竹串の両方に使うので 1 行にまとめる（2 行に分けると、同じ道具が 2 つ要るように読める）
        return [f"{by['band']['material']}を 1 枚", "のり、はさみ、定規、セロハンテープ、まち針、えんぴつ", "カッター（台と帯の四角い穴と、竹ぐしを切る道具。大人が使います。竹ぐしはニッパーでも切れます）",
                by["peg"]["material"], by["rod"]["material"], f"{by['cord']['material']}と{by['pull']['material']}", by["bead"]["material"]]
    return [f"{by['band']['material']}を 1 枚", "のり、はさみ、定規、まち針", CUT_TOOL, by["stick"]["material"], f"{by['cord']['material']}を 2 本", f"{by['bead']['material']}を 2 つ"]


def steps(p):
    """組み方の文。でんでん太鼓は、決まった行数（STEP_LINES_MAX。前はサイトの手順の紙に収めるため）に詰める。"""
    if p["face"] == "kanko":
        return steps_kanko(p)
    # 糸は、帯を丸める前に帯の裏で結んで留める。面を貼った後は胴の中に手が入らず、1 つの小さい穴に外から糸を留める手が無い
    # （前は面を 2 枚貼ってから「穴に結ぶ」と書いていて、その順では組めなかった）。糸の長さは、後で玉を付ける所で決める（直せる）。
    # 糸と絵が外に出る事は、帯を丸める手順で一緒に言う（前は「絵が外。糸は外へ垂らす」と添えていた。行に収めるため）。
    out = ["印刷した物差しに定規を当てて、10cm あるか確かめます",
           "部品を、切る線で切ります。3 胴の帯は、歯の間にも切りこみを入れます",
           "帯の穴は大人があけます（下に厚い紙をしきます）。太い 2 つの穴は竹ぐしの先で、ひし形の小さい穴はまち針であけます",
           "丸める前に、糸をひし形の穴に 1 本ずつ通し、帯の裏で 2 回結んでのりでとめます",
           "3 胴の帯を、絵と糸を外にして丸め、終わりののりしろを始めのはしの下にはります",
           "上下の歯を内へ山折りし、1 表の面と 2 裏の面を、歯の外からはります",
           f"帯の穴をあけた竹ぐしは{CUT_POINTS}。その竹ぐしを {stick_cut(p):g}mm に切ります",
           f"竹ぐしを太い 2 つの穴に通して、上へ {top_out(p):g}mm 出します。穴の所をのりでとめます",
           f"糸 2 本に玉を付けます（帯の表から玉の中心まで {p['cord_length']:g}mm）。あまりは切ります",
           "4 柄の巻き紙を、のりをうすく付けた胴の下の竹ぐしに巻いてはります（絵が外）"]
    if p["face"] == "tori":
        out.append("5 幣の房の上の帯を、胴の上に出た竹ぐしに巻いてはります")
    rng = tune_range(p)
    span = f"（帯の表から玉の中心まで {rng[0]:g}〜{rng[1]:g}mm の間）" if rng else ""
    out.append(f"柄を両手ではさんで左右に回し、玉が面に当たるか見ます。当たらなければ糸を長く、柄にからめば短くします{span}")
    return out


def _half_in(low, high, low_open=False):
    """窓 (low, high) の内で、0.5mm きざみの一番短い値と一番長い値。刷る数が窓の外へ丸まらないよう、下は切り上げ、上は切り捨てる。
    上の端はどの窓でも 0.01mm 内へ寄せる（柄に絡む長さちょうどは落ちるので、端の値を刷らない）。low_open は下の端も落ちる窓。"""
    lo = math.ceil((low + (0.01 if low_open else 0)) * 2 - 1e-9) / 2
    hi = math.floor((high - 0.01) * 2 + 1e-9) / 2
    return lo, hi


def tune_range(p):
    """作った人が糸の長さを直してよい範囲（刷る数）。検査の窓と同じ式から出すので、この間のどの長さも糸の検査を通る。
    作った人の報告（動かない・少し動く）を待たずに、手元で直せる所を型紙に書いておくための数。
    窓が無い寸法（検査で落ちる寸法）では None を返し、組み方の文は数を刷らない（組み方の文は、落ちる寸法でも読めるようにしておく）。"""
    if p["face"] == "kanko":
        low, high, _ = kanko_window(p)
        if high is None:
            return None
        clear = p["bead_d"] / 2 + (p["wheel_r"] - wheel_anchor(p))  # check_kanko の「玉が花車に重なる」と同じ長さ（ちょうども落ちる）
        lo, hi = _half_in(max(low, clear), high, low_open=clear >= low)
    else:
        lo, hi = _half_in(*cord_window(p))
    return (lo, hi) if lo <= hi else None


RESULTS = ("鳴った", "鳴らない")


def measures(p):
    """鳴るかの二択でなく、回し方と玉の動きを言葉か絵で予想する（ほかの雛形と同じ形）。回し方は数でないので欄に残す。"""
    if p["face"] == "kanko":
        return {"predict": "棒をどう引くと、花車と玉はどう動くと思いますか（言葉か絵で）", "rows": [[("引き方（速さ・長さ）", 40)]]}
    return {"predict": "柄をどう回すと、玉はどう動くと思いますか（言葉か絵で）", "rows": [[("回し方（速さ・向き）", 40)]]}


def diagram(x, y, w, h, p):
    """組み上がりを正面から見た絵。寸法の図ではなく、面・柄・糸と玉の並びを見せるだけ。"""
    if p["face"] == "kanko":
        return _diagram_kanko(x, y, w, h, p)
    R, L = p["radius"], p["cord_length"]
    up = top_out(p)
    s = min(w / (2 * R + 2 * L + p["bead_d"]), h / (2 * R + p["handle_length"] + up))
    cx, cy = x + w / 2, y + (up + R) * s
    shapes = [{"kind": "poly", "pts": _circle(cx, cy, R * s, 48), "fill": "none", "sw": 0.25}]
    shapes.append({"kind": "line", "x1": cx, "y1": cy - (R + up) * s, "x2": cx, "y2": cy - R * s})
    shapes.append({"kind": "line", "x1": cx, "y1": cy + R * s, "x2": cx, "y2": cy + (R + p["handle_length"]) * s})
    br = p["bead_d"] / 2 * s
    for side in (-1, 1):
        ax = cx + side * R * s
        bx = ax + side * L * s  # 回して振れた時の玉。糸はほぼ水平に張る
        shapes.append({"kind": "line", "x1": ax, "y1": cy, "x2": bx, "y2": cy, "dash": "1,0.6"})
        shapes.append({"kind": "rect", "x": bx - br, "y": cy - br, "w": 2 * br, "h": 2 * br})
    return shapes


# ---- 諫鼓（コマ 10 右、face=kanko）----
# 図に見える物: 横に寝かせた長い鼓（面に三つ巴）、鼓を支える 1 本の柱、平たい台、台に立つ軸の上の花車（花弁 10 枚・先に糸と玉）、
# 台の端から差し込んだ 2 本並びの竹の棒（途中に切り欠き）。
# 【解釈】図に動かし方の説明は無い。この雛形では、棒を引くと台の中で軸に巻いた糸がほどけて軸が回り（独楽の紐と同じ）、
# 花車の先の玉が振れて、花車の側を向いた鼓の面を打つ、と読む。棒の切り欠きは糸を掛ける所と読む。どちらも図からの推定で、確かめていない。
# 鼓の軸の向き（面が花車を向く）も【解釈】。図では鼓が斜め奥を向き、花車は面の手前の下にある。
KANKO_BODY, WOOD, WOOD_DARK, PETAL = "#d8c58c", "#d6c38e", "#b49d62", "#e2cf95"
POST_FIT = 0.4  # 柱の頭を差す帯の四角い穴の遊び。きついと帯が裂け、緩いと鼓が回る
POST_INSERT, POST_TAB, POST_GLUE = 5, 5, 5  # 柱の頭を胴に差す長さ・足の糊代・継ぎ目の糊代
BASE_TAB = 6  # 台の角の糊代の幅（壁の高さより狭くする）
WHEEL_PETALS = 10  # 図の花車の花弁の数
PEG_TOP = 3  # 花車の軸の竹串を、花車の上へ出す長さ
ROD_GRIP = 40  # 引く棒の、南の壁から出して手で持つ長さ
# 棒の留め具: 帯の幅（棒の向き）と、帯の両端を貼り合わせて棒の上に立てる旗の高さ。
# 旗は棒の真上に立てる。旗は南の壁の棒の穴より上に出るので、引くと壁に当たって止まる（止め具も兼ねる）。
# 旗の穴（半径 TAB_HOLE_R）から旗の先・折り目・帯の縁まで HOLE_MARGIN を取るので、旗の高さと帯の幅は 2 × (3 + 0.5) = 7mm。
# 3.5mm の旗では穴から先と折り目まで 1.25mm しか無く、結んだ糸で裂ける。
TAB_HOLE_R = 0.5
TAB_W = TAB_FLAG = 2 * (HOLE_MARGIN + TAB_HOLE_R)
ROD_GAP = 1  # 旗が軸の側へ倒れた時に、旗の先から軸に巻いた糸の表まで空ける長さ
WIND_D = 0.5  # 軸に巻く木綿の糸の太さの見込み。巻いた分だけ軸の表が太る（糸は軸に沿って並んで巻かれると見て 1 本分。重ねて巻くと越える）


def wheel_anchor(p):
    """花車で玉の糸を結ぶ穴の、軸からの距離。花弁の先から 1.5mm 内に穴をあける（先に寄せると裂ける）。"""
    return p["wheel_r"] - 1.5


def peg_cut(p):
    """花車の軸の竹串の長さ。下の端を床に着けて台の穴に立てるので、台の高さ＋花車の高さ（台の上の面から）＋上へ出す分。"""
    return p["base_height"] + p["peg_height"] + PEG_TOP


def rodtab_pos(p):
    """棒の北の端から、棒の留め具の北の縁までの長さ。押し込んだ時に、留め具の真ん中（旗の穴）が軸の真横に来る所にする。
    図の棒の切り欠きの代わり【解釈】。合わせる縁を北の縁と決めて刷るので、結ぶ所が作る人ごとにずれない。"""
    return rod_north_out(p) + peg_pos(p) - TAB_W / 2


def rod_north_out(p):
    """棒を押し込んだ時に北の壁から出しておく長さ。引き切っても北の壁の穴に HOLE_MARGIN 残るよう、引ける長さに合わせる。
    決まった 10mm にしていた時は、既定で 17mm 引くと棒の先が北の穴から抜け、棒が台の中で倒れた。
    刷る数はこの値から足して出すので、ここで 1 度だけ mm の整数に切り上げる（切り捨てると余白が 3mm を割る）。
    留め具の位置（rodtab_pos）と棒の長さ（rod_length）は、この丸めた値に足すので、刷った 3 つの数が食い違わない。"""
    return math.ceil(pull_travel(p) + HOLE_MARGIN - 1e-9)


def rod_length(p):
    """引く棒（竹串 2 本）の長さ ＝ 北に出す分 ＋ 台の中 ＋ 手で持つ分。竹串の長さ（SKEWER_LEN）を越えると作れない。"""
    return rod_north_out(p) + p["base_length"] + ROD_GRIP


def pull_travel(p):
    """棒を南へ引ける長さ。押し込んだ時の留め具の南の縁（軸の位置＋帯の幅の半分）から、旗が南の壁に当たるまで。
    前は壁の 3mm 手前で止まると見ていたが、旗は壁に当たって止まるので、当たるまでを引ける長さにする。"""
    return p["base_length"] - peg_pos(p) - TAB_W / 2


def pull_unwind(p, favorable=False):
    """棒を引き切った時に、軸から解ける糸の長さ。
    糸は軸の表（半径 r）から旗の穴までまっすぐ張る。旗の穴は、押し込んだ時は軸の真横（軸から rod_off）にあり、引き切ると南へ pull_travel 動く。
    解けるのは「旗の穴が軸から遠ざかった分」で、棒の動いた長さではない（真横から動き始めるので、始めは糸がほとんど引かれない）。
    前は棒の動いた長さがそのまま解けると見て、台 80mm で約 1.8 回と刷っていたが、この形で数えると 0.8〜1.1 回だった。
    糸が軸のどちらの側を回って棒へ向かうかで、軸に沿う分 r·(糸の向きが変わる角度) が足されるか引かれる。
    鼓の側（北＝引く向きの反対）を回ると、引くほど糸が軸に巻き付く向きに動くので足される（favorable=True）。
    多い側の見込み（favorable=True）: 鼓の側を回る巻き方・旗は立ったまま・糸の太さは入れない。
    少ない側の見込み（既定。検査はこちら）: 反対の巻き方・引き切る頃に旗が軸の側へ倒れて穴が旗の高さの半分だけ軸に近づく
    （巻く時は立っていて引くと倒れる、が一番少ない）・糸の中心が軸の表から糸の太さの半分だけ外を回る（_wind_r）。糸の伸びは入れない。"""
    r, off, T = _wind_r(p, favorable), rod_off(p), pull_travel(p)
    if T <= 0:
        return 0.0
    off1 = off if favorable else off - TAB_FLAG / 2  # 引き切った時の、棒の通り道から見た穴の位置
    d1 = math.hypot(off1, T)
    free = math.sqrt(d1 * d1 - r * r) - math.sqrt(off * off - r * r)
    turn = math.atan2(T, off1)  # 軸から見た旗の穴の向きが変わる角度
    lift = math.acos(r / d1) - math.acos(r / off)  # 糸が軸を離れる点の、その向きからのずれが変わる分
    return free + r * (turn - lift) if favorable else free - r * (turn + lift)


def _wind_r(p, favorable):
    """糸が軸を回る半径。少ない側では糸の太さの半分を足す（rod_off が軸に巻いた糸の分を見ているのと同じ WIND_D）。"""
    return p["stick_d"] / 2 + (0 if favorable else WIND_D / 2)


def pull_turns(p, favorable=False):
    """引き切った時に軸が回る数 ＝ 解ける糸の長さ ÷ 糸が軸を回る 1 周。既定（favorable=False）は少ない側の見込み。"""
    return pull_unwind(p, favorable) / (2 * math.pi * _wind_r(p, favorable))


def wind_wraps(p):
    """棒を押し込んだ時に、軸に巻いておく糸の回数。多い側で解ける回数を切り上げ、1 回余らせる
    （引き切った時に結び目まで解け切ると、結び目が引かれて軸が止まる）。"""
    return math.ceil(pull_turns(p, favorable=True)) + 1


def pull_cord(p):
    """巻く糸の、旗の穴から軸の結び目までの長さ（mm の整数に丸めて刷る）。押し込んだ時の張った所 ＋ 軸に巻いておく分。
    前は 200mm の糸を「2 回巻く」とだけ書き、残りの糸の行き先が無かった（余りが軸に絡む）。結ぶ所を長さで決める。"""
    r = _wind_r(p, False)  # 糸の太さを入れた 1 周で数える（細く見ると、巻いておく回数に糸が足りなくなる）
    return round(math.sqrt(rod_off(p) ** 2 - r * r) + wind_wraps(p) * 2 * math.pi * r)


def rod_perimeter(p):
    """竹串 2 本を縦に重ねて束ねた棒の周りの長さ（半円 2 つ＋まっすぐな所 2 つ）。"""
    return math.pi * p["stick_d"] + 2 * p["stick_d"]


def peg_pos(p):
    """台の北の端から軸（花車）までの長さ。柱の真上に鼓の真ん中を置き、鼓の前の面から face_gap 先に軸を立てる。"""
    return p["post_pos"] + p["k_length"] / 2 + p["face_gap"]


def rod_off(p):
    """棒の通り道（中心）を軸の線から横へずらす量。留め具が軸に一番近づくのは、旗が軸の側へ倒れた時
    （旗は棒の真上の付け根から、横へ旗の高さ＋紙の厚みだけ出る。巻く糸は旗を軸の側へ引くので、倒れるならこちら側）。
    その時も旗の先が、軸に巻いた糸の表（軸の半径＋糸の太さ WIND_D）から ROD_GAP 離れるように決める。
    前は棒の幅だけを見て 1.5·d ＋ 1（d = 3 で 5.5mm）にしていて、倒れた旗が軸に当たりえた。軸に巻いた糸の分は 6 回目の直しで落ちていたので戻した。"""
    return p["stick_d"] / 2 + WIND_D + ROD_GAP + TAB_FLAG + p["paper_thickness"]


def rod_cut_top(p):
    """棒の穴の上の縁の、床からの高さ。穴は床から HOLE_MARGIN の所から開け、棒（竹串 2 本の縦重ね）を低く通して、上に旗の立つ所を空ける。
    棒は穴の中で上へ浮きうる（穴は棒より 1mm 高い）ので、旗の高さは棒が穴の上の縁まで浮いた時で見る。"""
    return HOLE_MARGIN + rod_cut(p)[1]


def flag_tip_z(p):
    """棒が一番浮いた時の旗の先の、床からの高さ ＝ 穴の上の縁 ＋ 巻いた帯の厚み ＋ 旗の高さ。"""
    return rod_cut_top(p) + p["paper_thickness"] + TAB_FLAG


def ceiling_z(p):
    """台の天井の下の面の、床からの高さ ＝ 壁の高さ − 天井の紙の厚み。"""
    return p["base_height"] - p["paper_thickness"]


def rod_cut(p):
    """台の端の壁にあける棒の穴（幅・高さ）。竹串 2 本を縦に重ねて通す。"""
    return p["stick_d"] + 1, 2 * p["stick_d"] + 1


def kanko_window(p):
    """諫鼓の糸の長さ（花車の穴から玉の中心まで）の下限と上限。

    前提: 花車を速く回すと、玉は軸を中心に半径 ρ = 穴の距離 + 糸 の水平な円を、花車の高さで回る（重力・たるみは入れない）。
    面は軸から face_gap 先の縦の面で、玉の表が面に触れる時、玉の中心は面から玉の半径だけ手前（g = face_gap − 玉の半径）。
    打つ点の面の中心からのずれは、横 √(ρ² − g²) と縦 dz（花車の高さ − 鼓の中心の高さ）を合わせた長さ。
    でんでん太鼓と同じく、これが STRIKE_ZONE·R の内なら鳴ると見込む。
    下限: ρ ≧ g（面に届く）。上限: ρ² ≦ g² + (kR)² − dz²。dz が kR を越えると窓が無い（上限は None）。
    """
    R, k = p["k_radius"], STRIKE_ZONE
    g = p["face_gap"] - p["bead_d"] / 2
    dz = p["peg_height"] - (p["post_height"] + R)
    a = wheel_anchor(p)
    low = g - a
    room = g * g + (k * R) ** 2 - dz * dz
    # 窓は両端を含む（L ≦ high）ので、境（room == g²、下限＝上限の 1 点）も窓に入れる。
    high = math.sqrt(room) - a if room >= g * g else None
    return low, high, dz


def check_kanko(p):
    """F5.drum（諫鼓）: 玉が面を打つ・花車が面に当たらない・柱の穴と台の穴が裂けない・柱と軸が台に載る、を見る。"""
    out = []
    low, high, dz = kanko_window(p)
    L, kR = p["k_cord"], STRIKE_ZONE * p["k_radius"]
    if high is None:
        out.append(Failure("F5.drum", "花車", f"花車の高さが鼓の中心から {dz:+.1f}mm ずれ、玉が面の真ん中（±{kR:.1f}mm）を通らない"))
    else:
        if L < low:
            out.append(Failure("F5.drum", "糸", f"糸 {L:g}mm は短く、玉が面に届かない（{low:.1f}mm 以上）"))
        if L > high:
            out.append(Failure("F5.drum", "糸", f"糸 {L:g}mm は長く、面の縁の近くを打つ（{high:.1f}mm まで）"))
    # 玉は糸の先に下がるので、糸が玉の半径＋穴から花弁の先までより短いと、玉が花車に重なって振れない。
    clear = p["bead_d"] / 2 + (p["wheel_r"] - wheel_anchor(p))
    # 柄に絡む側と同じく、ちょうど触れる長さも落とす（触れると玉が花車に当たって振れが止まる）。
    if L <= clear:
        out.append(Failure("F5.drum", "糸", f"糸 {L:g}mm は玉の半径と花弁の先までより短く、玉が花車に重なる（{clear:.1f}mm 以上）"))
    if p["wheel_r"] > p["face_gap"] - 2:
        out.append(Failure("F5.drum", "花車", f"花車の半径 {p['wheel_r']:g}mm が面までの {p['face_gap']:g}mm に近く、回すと面に当たる"))
    edge = (p["k_length"] - p["post_side"] - POST_FIT) / 2
    if edge < HOLE_MARGIN:
        out.append(Failure("F5.drum", "柱の穴", f"柱の穴から帯の縁まで {edge:.1f}mm で、裂けやすい（{HOLE_MARGIN}mm 以上）"))
    if p["post_pos"] - p["post_side"] / 2 < HOLE_MARGIN or p["post_side"] > p["base_width"] - 2 * HOLE_MARGIN:
        out.append(Failure("F5.drum", "柱", "柱の足が台の上に収まらない"))
    if peg_pos(p) > p["base_length"] - HOLE_MARGIN:
        out.append(Failure("F5.drum", "軸", f"花車の軸が台の端から {peg_pos(p):.0f}mm で、台（{p['base_length']:g}mm）の上に立たない"))
    # 棒の穴の余白。穴の下の余白は HOLE_MARGIN で開ける（_base）ので、見るのは上の余白（壁の高さ − 穴の上の縁）と、穴から東の壁の端まで。
    # どちらも下の留め具の 2 つの検査（天井・東の壁）がどの寸法でも一緒に落とす（旗 7mm ＋ 0.5mm は HOLE_MARGIN より大きく、
    # 旗 7mm ＋ 紙 ＋ 0.5mm は穴の幅の半分 ＋ HOLE_MARGIN より大きい）ので単独では落ちないが、壁が低すぎる時の素直な理由として残す（試験で範囲の端を見る）。
    cw, ch = rod_cut(p)
    if p["base_height"] - rod_cut_top(p) < HOLE_MARGIN:
        out.append(Failure("F5.drum", "棒の穴", f"台の壁 {p['base_height']:g}mm に棒の穴（高さ {ch:g}mm・床から {HOLE_MARGIN}mm）の上の余白が {HOLE_MARGIN}mm 取れない"))
    if p["base_width"] / 2 + rod_off(p) + cw / 2 > p["base_width"] - HOLE_MARGIN:
        out.append(Failure("F5.drum", "棒の穴", "棒の穴が台の壁の端に近すぎる"))
    _, pitch, inset = tab_teeth(p)
    if pitch - 2 * inset < 1:
        out.append(Failure("F5.drum", "糊代の歯", f"歯の先が {pitch - 2 * inset:.1f}mm で、面を貼る所が無い（歯が深すぎる）"))
    # 結ぶ所（留め具）を決めたので、引ける長さで軸が回る数も数えられる。1 回も回らないと玉が振れない。
    # 北に出す分を引ける長さに合わせたので、台が長いと棒が伸びる。でんでん太鼓の柄と同じく竹串の長さで落とす。
    if rod_length(p) > SKEWER_USABLE:
        out.append(Failure("F5.drum", "棒", f"引く棒に竹串が {rod_length(p):g}mm 要り、先を落とした {SKEWER_USABLE}mm の竹串で足りない"))
    # 留め具の旗は棒の上に立つ。棒が穴の中で一番浮いた時も、旗の先が天井の下の面から 0.5mm 空かないと棒が引けない。
    # 帯の厚み・天井の紙の厚み・穴の中の浮きを入れる（前は穴の中心で数え、天井の紙の厚みも入れず、壁 14mm・紙 0.5mm で当たる寸法を通した）。
    room = ceiling_z(p) - flag_tip_z(p)
    if room < 0.5:
        out.append(Failure("F5.drum", "留め具", f"留め具の旗の先が台の天井まで {room:.1f}mm で、0.5mm 空かない（台の壁を高く）"))
    # 一番悪いのは旗が横へ倒れた時。軸の側へ倒れても当たらないよう rod_off を決めてあるので、反対の東の壁の側へ倒れた時を見る。
    east = p["base_width"] / 2 - rod_off(p) - (TAB_FLAG + p["paper_thickness"])
    if east < 0.5:
        out.append(Failure("F5.drum", "留め具", f"留め具の旗が東の壁の側へ倒れると、壁まで {east:.1f}mm で当たる（台を広く）"))
    if pull_turns(p) < 1:
        out.append(Failure("F5.drum", "棒", f"棒を引ける長さ {pull_travel(p):.0f}mm では、軸が 1 回も回らない（{pull_turns(p):.1f} 回）"))
    return out


TOMOE_SWEEP = 110  # 巴の尾が外の円に沿う角度。3 つで 1 周を越えると尾が隣の頭に重なり、輪に見えるので 1/3 周より短くする


def _tomoe_art(R):
    """三つ巴。頭の丸と、外の円に沿って細くなる尾を 1 つの面にする。コマ 10 の面の巴の大きさ（面の半径の 0.75 の円の内）を目測した。"""
    ro, rh = 0.66 * R, 0.21 * R
    out = []
    for i in range(3):
        f0 = math.pi / 2 + 2 * math.pi * i / 3
        pts = []
        n = 24
        for j in range(n + 1):  # 外の縁: 頭から尾の先へ、外の円に沿って TOMOE_SWEEP° 戻る
            a = f0 - math.radians(TOMOE_SWEEP) * j / n
            pts.append((R + ro * math.cos(a), R + ro * math.sin(a)))
        for j in range(n, -1, -1):  # 内の縁: 尾の先から頭へ、半径を頭の幅だけ詰めていく
            a = f0 - math.radians(TOMOE_SWEEP) * j / n
            r = ro - 2 * rh * (1 - j / n) ** 2  # 2 乗で細らせ、尾を頭の近くで急に細くする（図の巴の尾は細い）
            pts.append((R + r * math.cos(a), R + r * math.sin(a)))
        hc = ro - rh
        for j in range(1, n):  # 頭の丸: 内の点（中心から見て内向き）から、進む向きの側を回って外の点へ
            a = math.pi - math.pi * j / n
            pts.append((R + hc * math.cos(f0) + rh * math.cos(f0 + a), R + hc * math.sin(f0) + rh * math.sin(f0 + a)))
        poly = Polygon(pts).buffer(0)
        if poly.geom_type == "MultiPolygon":
            poly = max(poly.geoms, key=lambda g: g.area)
        out.append({"kind": "poly", "pts": list(poly.exterior.coords)[:-1], "fill": INK})
    return out


def _post(p):
    """柱は四角い筒。面 4 つ＋継ぎ目の糊代、下に外へ折る足の糊代。上の POST_INSERT は胴の穴に差す分。"""
    s, L = p["post_side"], p["post_height"] + POST_INSERT
    W = 4 * s
    pts = [(0, 0), (W + POST_GLUE, 0), (W + POST_GLUE, L), (W, L)]
    for i in reversed(range(4)):
        a, b = i * s, (i + 1) * s
        pts += [(b - 0.5, L + POST_TAB), (a + 0.5, L + POST_TAB), (a, L)]
    part = Part(10, "post", "柱", pts, label_xy=(0.8, 1.5), label="10")
    # 筒の 4 本は絵を外にして向こうへ折るので山折り。足は外（手前）へ開くので谷折り。
    part.mountain = [((i * s, 0), (i * s, L)) for i in range(1, 5)]
    part.valley = [((0, L), (W, L))]
    # 糊の印（斜線）は、刷った面に糊を付ける所にだけ刷る。足は外へ開いて裏を台に貼るので、刷った面に印を刷らない
    # （印があると、足の上の面に糊を付けるように読める）。貼る所は台の上のかぎの印が示す。
    part.glue = [[(W, 0), (W + POST_GLUE, 0), (W + POST_GLUE, L), (W, L)]]
    part.art = [{"kind": "poly", "pts": [(i * s + 0.2, POST_INSERT + 0.2), ((i + 1) * s - 0.2, POST_INSERT + 0.2), ((i + 1) * s - 0.2, L - 0.2), (i * s + 0.2, L - 0.2)],
                 "fill": WOOD if i % 2 == 0 else WOOD_DARK} for i in range(4)]
    return part


def _base(p):
    """台は底の無い箱（上の面と 4 つの壁）。北と南の壁の端に角の糊代。長さの向きは紙の縦（北が上）。
    北と南の壁に棒の穴、上の面に花車の軸の穴、柱の足を貼る所の印。"""
    W, L, H = p["base_width"], p["base_length"], p["base_height"]
    g = min(BASE_TAB, H - 1)
    pts = [(H, 0), (H + W, 0), (H + W + g, 1.5), (H + W + g, H - 0.5), (H + W, H), (2 * H + W, H), (2 * H + W, H + L), (H + W, H + L),
           (H + W + g, H + L + 0.5), (H + W + g, 2 * H + L - 1.5), (H + W, 2 * H + L), (H, 2 * H + L), (H - g, 2 * H + L - 1.5), (H - g, H + L + 0.5),
           (H, H + L), (0, H + L), (0, H), (H, H), (H - g, H - 0.5), (H - g, 1.5)]
    part = Part(11, "base", "台", pts, label_xy=(H + 1.5, H + 1.5), label="11 台")
    # 壁も角の糊代も、絵を外にして向こう（下・内）へ折るので山折り。
    part.mountain = [((H, H), (H + W, H)), ((H, H + L), (H + W, H + L)), ((H, H), (H, H + L)), ((H + W, H), (H + W, H + L)),
                     ((H, 0), (H, H)), ((H + W, 0), (H + W, H)), ((H, H + L), (H, 2 * H + L)), ((H + W, H + L), (H + W, 2 * H + L))]
    part.glue = [[(H, 0), (H, H), (H - g, H - 0.5), (H - g, 1.5)], [(H + W, 0), (H + W + g, 1.5), (H + W + g, H - 0.5), (H + W, H)],
                 [(H, H + L), (H, 2 * H + L), (H - g, 2 * H + L - 1.5), (H - g, H + L + 0.5)], [(H + W, H + L), (H + W + g, H + L + 0.5), (H + W + g, 2 * H + L - 1.5), (H + W, 2 * H + L)]]
    faces = [(H, H, H + W, H + L), (H, 0, H + W, H), (H, H + L, H + W, 2 * H + L), (0, H, H, H + L), (H + W, H, 2 * H + W, H + L)]
    part.art = [{"kind": "poly", "pts": [(a + 0.2, b + 0.2), (c - 0.2, b + 0.2), (c - 0.2, d - 0.2), (a + 0.2, d - 0.2)], "fill": WOOD if i == 0 else WOOD_DARK}
                for i, (a, b, c, d) in enumerate(faces)]
    cx = H + W / 2
    s = p["post_side"]
    py = H + p["post_pos"]
    sq = [(cx - s / 2, py - s / 2), (cx + s / 2, py - s / 2), (cx + s / 2, py + s / 2), (cx - s / 2, py + s / 2)]
    # 柱の足を貼る所は、四隅のかぎの印（茶色）で示す。黒い閉じた四角は切る線に見え、穴に切られた。
    k = s / 4
    for (x0, y0), (ux, uy) in zip(sq, ((1, 1), (-1, 1), (-1, -1), (1, -1))):
        part.art.append({"kind": "line", "pts": [(x0 + ux * k, y0), (x0, y0), (x0, y0 + uy * k)], "stroke": BAND, "sw": 0.5})
    part.holes = [(cx, H + peg_pos(p), p["stick_d"] / 2 + 0.4)]  # 軸が回るよう、穴は串より 0.8mm 太い
    cw, ch = rod_cut(p)
    rx = cx + rod_off(p) - cw / 2
    # 北の壁は y=0 が床の縁、南の壁は y=2H+L が床の縁。棒は床から HOLE_MARGIN の所に低く通し、上に旗の立つ所を空ける。
    # 穴の上の縁は検査（flag_tip_z）と同じ rod_cut_top から出す。ここで別に数えると、片方を変えた時に刷る穴と検査が黙って食い違う。
    part.cuts = [(rx, rod_cut_top(p) - ch, cw, ch), (rx, 2 * H + L - rod_cut_top(p), cw, ch)]
    return part


def _wheel(p):
    """花車（花弁 10 枚）。真ん中に軸の穴、1 枚の花弁の先に玉の糸の穴。花弁の形はコマ 10 の図の目測。"""
    r, n = p["wheel_r"], WHEEL_PETALS
    ri = 0.6 * r  # 花弁の根元。番号の字を軸の穴の横に置けるだけの広さを残す
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        da = math.pi / n
        pts += [(r + ri * math.cos(a - da * 0.9), r + ri * math.sin(a - da * 0.9)),
                (r + r * math.cos(a - da * 0.45), r + r * math.sin(a - da * 0.45)),
                (r + r * math.cos(a + da * 0.45), r + r * math.sin(a + da * 0.45))]
    part = Part(12, "wheel", "花車", pts, label_xy=(r - 4.6, r - 1.75), label="12")
    a = wheel_anchor(p)
    part.holes = [(r, r, p["stick_d"] / 2 + 0.1), (r + a, r, 0.5)]
    part.art = [{"kind": "poly", "pts": _circle(r, r, ri * 0.9, 30), "fill": PETAL}]
    return part


def _rodtab(p):
    """棒の留め具。帯（長さ＝棒の周り＋旗 2 枚分、幅 TAB_W は棒の向き）を棒に巻き、両端を棒の上で貼り合わせて旗にする。
    刷った面を内にして（真ん中の糊の印を棒に当てて）巻き、両端を棒の真上で立てると、2 枚の旗は刷った面どうしが向き合うので、
    端の旗の糊の印が相手の旗に当たる（帯が棒の上を右へ来て上へ曲がると、下を向いていた刷った面は右＝相手の旗の側を向く）。
    この曲げは、刷った面が外まわりになるので山折り（凡例: 山折りは手前に出る）。
    前は「刷った面を外にして」と書いていたが、それだと立てた 2 枚の旗の刷った面は外を向き、真ん中の印も棒の反対を向いて、どの印にも糊を付けられない。
    旗の 2 枚の穴は重なる所（旗の真ん中）に置き、巻く糸を通して結ぶ。穴は糊の印の中にあるので、組み方は糸を通して結んでから貼る順にする。"""
    F = TAB_FLAG
    W = rod_perimeter(p) + 2 * F
    part = Part(16, "rodtab", "棒の留め具", [(0, 0), (W, 0), (W, TAB_W), (0, TAB_W)], label_xy=(F + 0.4, 0.4), label="16")
    # 帯の真ん中（棒に当たる所）にも糊の印を置き、棒に貼る。旗どうしだけを貼ると、旗が壁に当たった時と糸に引かれた時に
    # 輪が棒の上を滑って棒だけが進み、棒の北の端が穴から抜けた。
    # 番号（箱 2.9 × 3.5mm）の分だけ、真ん中の印の左上を空ける（印の線の上に刷ると読めない。旗は 7mm 四方の真ん中に穴があり、番号の入る所が無い）。
    # 糊は空けた分（1 割ほど）だけ減る。
    px, py = F + 3.5, 4.1
    part.glue = [[(px, 0), (W - F, 0), (W - F, TAB_W), (px, TAB_W)], [(F, py), (px, py), (px, TAB_W), (F, TAB_W)],
                 [(W - F, 0), (W, 0), (W, TAB_W), (W - F, TAB_W)]]
    # 旗の付け根は山折り。刷った面を棒に当てて巻くと、旗は棒から離れる向き＝刷った面の反対の側へ曲げて立てるので、
    # 刷った面から見ると折り目が手前に出る。前は谷折りの線で刷っていて、線のとおりに折り癖を付けると旗が棒の側へ倒れた。
    part.mountain = [((F, 0), (F, TAB_W)), ((W - F, 0), (W - F, TAB_W))]
    part.holes = [(F / 2, TAB_W / 2, TAB_HOLE_R), (W - F / 2, TAB_W / 2, TAB_HOLE_R)]
    return part


# 軸受けの腕を机から浮かせる高さ（＝西の壁に貼る糊代の高さ）。軸の下の端が、この長さだけ腕の穴を通る。
# 6mm にしていた時は、細い竹串（2mm）で、軸の側へ倒れた旗（棒の上の面の高さ）と腕の間が 1mm しか無かった。4mm ならどの太さでも 2mm 以上空く。
BEARING_LIFT = 4


def flag_hole_z(p):
    """旗の穴の、机からの高さ（棒が穴の底に乗っている時）。巻く糸はこの高さで軸に結ぶ（糸が水平に張る）。"""
    return HOLE_MARGIN + 2 * p["stick_d"] + p["paper_thickness"] + TAB_FLAG / 2


def bearing_arm(p):
    """軸受けの腕の長さ（西の壁の内の面から、穴の先の余白まで）と、壁から穴の中心までの長さ。"""
    to_hole = p["base_width"] / 2 - p["paper_thickness"]
    return to_hole + p["stick_d"] / 2 + 0.4 + HOLE_MARGIN, to_hole


def _bearing(p):
    """軸受け。西の壁（棒と反対の側）の内に糊代で貼り、腕を机から BEARING_LIFT 浮かせて、軸の下を穴で受ける。
    台は底が無く、軸は上の面の穴 1 つと机だけで支えていた。巻く糸は軸を棒の側へ横に引くので、軸の下の端が机の上を滑って軸が傾き、
    花車と玉の高さが狂う（玉が面の真ん中を打つという見込みが外れる）。穴を上下 2 つにすると、軸は立ったまま回る。
    腕は西の壁から出す。糸が軸を引く向きは、引き始めは東（腕を引っ張る向き）、引き切る頃は南東（腕を面の中で横に曲げる向き。幅のある紙は面の中では曲がりにくい）。
    台の幅いっぱいの帯にしないのは、東の側に棒と旗の通り道があるため
    （腕の先は棒の手前で止まる）。腕を机に着けないのは、紙 1 枚の厚みの穴では軸の下の端がすぐ乗り越えるため。
    糊代は腕の西の端から下へ山折りする（腕の上の面が刷った面。糊の印は刷った面にあるので、山折りで壁の側を向く）。"""
    arm, to_hole = bearing_arm(p)
    T, D, r = BEARING_LIFT, 2 * (HOLE_MARGIN + p["stick_d"] / 2 + 0.4), p["stick_d"] / 2 + 0.4  # 穴は上の面の穴と同じ太さ（軸が回る）
    part = Part(18, "bearing", "軸受け", [(0, 0), (T + arm, 0), (T + arm, D), (0, D)], label_xy=(T + 1, 0.6), label="18")
    part.mountain = [((T, 0), (T, D))]
    part.glue = [[(0, 0), (T, 0), (T, D), (0, D)]]
    part.holes = [(T + to_hole, D / 2, r)]
    return part


def _gauge(p):
    """花車の高さの物差しの紙。台の上の面に立て、上の端に花車の下の面を合わせる。長さは peg_height そのもの。"""
    h = p["peg_height"]
    part = Part(17, "gauge", "花車の高さの紙", [(0, 0), (6, 0), (6, h), (0, h)], label_xy=(1.4, 1.5), label="17")
    part.art = [{"kind": "poly", "pts": [(0.2, 0.2), (5.8, 0.2), (5.8, 1.0), (0.2, 1.0)], "fill": INK}]  # 上の端の印
    return part


def _place_kanko(by_key, page, y, gap):
    """2 段目に台・面 2 枚（縦）・柱・花車を並べ、説明は 2 段目の下に全幅で置く（台が広く、右に説明の列を取ると物差しが入らない）。"""
    x = page.x0
    base = by_key["base"]
    base.x, base.y = x, y
    x += base.width + gap
    front, back = by_key["front"], by_key["back"]
    front.x, front.y = x, y
    back.x, back.y = x, y + front.height + gap
    x += front.width + gap
    post, wheel = by_key["post"], by_key["wheel"]
    post.x, post.y = x, y
    wheel.x, wheel.y = x, y + post.height + gap
    tab, gauge = by_key["rodtab"], by_key["gauge"]
    tab.x, tab.y = x + wheel.width + gap, wheel.y
    gauge.x, gauge.y = tab.x + tab.width + gap, wheel.y
    # 軸受けは花車の下（留め具の下に置くと、右の物差しの紙と重なる）。
    bearing = by_key["bearing"]
    bearing.x, bearing.y = x, wheel.y + wheel.height + gap
    bottom = max(base.y + base.height, back.y + back.height, bearing.y + bearing.height, tab.y + tab.height, gauge.y + gauge.height)
    return bottom + gap, page.x1 - page.x0, page.x0


def bom_kanko(p):
    paper = paper_name(thickness=p['paper_thickness'])
    why = "家庭のプリンタで刷って作るため"
    peg = peg_cut(p)
    rod = rod_length(p)
    return [
        {"number": 1, "key": "front", "name": "表の面", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明（紙張りか革張りかは図から分からない）", "reason": why},
        {"number": 2, "key": "back", "name": "裏の面", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明（同じ）", "reason": why},
        {"number": 3, "key": "band", "name": "胴の帯", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明", "reason": why},
        {"number": 8, "key": "cord", "name": "糸", "qty": 1, "material": f"もめんの糸（{p['k_cord'] + CORD_SPARE:g}mm）", "substituted": True, "original_guess": "糸（図の線による）", "reason": "家にあるため"},
        {"number": 9, "key": "bead", "name": "玉", "qty": 1, "material": f"油ねんどの玉（直径 {p['bead_d']:g}mm）かビーズを 1 つ", "substituted": True, "original_guess": "不明", "reason": "大きさを変えて試しやすいため"},
        {"number": 10, "key": "post", "name": "柱", "qty": 1, "material": paper, "substituted": True, "original_guess": "木か竹（図の形からの推定）", "reason": why},
        {"number": 11, "key": "base", "name": "台", "qty": 1, "material": paper, "substituted": True, "original_guess": "木の板（図の形からの推定）", "reason": why},
        {"number": 12, "key": "wheel", "name": "花車", "qty": 1, "material": paper, "substituted": True, "original_guess": "紙（図の形からの推定）", "reason": why},
        {"number": 13, "key": "peg", "name": "花車の軸", "qty": 1, "material": f"竹ぐし（長さ {peg:g}mm に切る）", "substituted": True, "original_guess": "竹か木（図の形からの推定）", "reason": "家にあり、台の穴で回しやすいため"},
        {"number": 14, "key": "rod", "name": "引く棒", "qty": 1, "material": f"竹ぐし 2 本（長さ {rod:g}mm、テープでまとめる）", "substituted": True, "original_guess": "竹 2 本（図の形による。図の切り欠きは 16 棒の留め具に置き換えた）【解釈】", "reason": "図の 2 本並びの竹に近く、家にあるため"},
        {"number": 15, "key": "pull", "name": "巻く糸", "qty": 1, "material": f"もめんの糸（{math.ceil((pull_cord(p) + 2 * CORD_SPARE) / 10) * 10:g}mm）", "substituted": True, "original_guess": "不明（図に見えない）【解釈】", "reason": "棒を引いて軸を回すため"},
        {"number": 16, "key": "rodtab", "name": "棒の留め具", "qty": 1, "material": paper, "substituted": True, "original_guess": "棒の切り欠き（図による）【解釈】", "reason": "竹串に切り欠きを彫るのは難しく、結ぶ所を刷って決めるため"},
        {"number": 17, "key": "gauge", "name": "花車の高さの紙", "qty": 1, "material": paper, "substituted": True, "original_guess": "無し（作るための道具）", "reason": "花車を台の上の面から決まった高さに貼るため"},
        {"number": 18, "key": "bearing", "name": "軸受け", "qty": 1, "material": paper, "substituted": True, "original_guess": "無し（図の台は木の板で、軸は板の穴に立つと見た）【解釈】", "reason": "紙の台は底が無く、糸に引かれた軸の下の端が横へ逃げて傾くのを止めるため"},
    ]


def steps_kanko(p):
    """諫鼓の組み方の文。部品が多く、前のサイトの手順の紙 1 枚には収まらなかった（STEP_LINES_KANKO。手順の紙は廃止）。理由を短く添え、言い回しは詰める。"""
    rng = tune_range(p)
    span = "（花車の小さい穴から玉の中心まで {:g}〜{:g}mm の間）".format(*rng) if rng else ""
    return ["印刷した物差しに定規を当てて、10cm あるか確かめます",
            "部品を、切る線で切ります。胴の帯の歯の間・帯の四角い穴・台の壁の四角い穴も切ります（カッターは大人が使います）",
            "穴は大人があけます（下に厚い紙をしきます）。台の丸い穴・18 軸受けの穴・花車の真ん中の穴は目打ちか竹ぐしの先で、旗の穴と花車の小さい穴はまち針であけます",
            "3 胴の帯を丸めてはります。歯を内へ山折りし、1 表の面（巴）と 2 裏の面をはります",
            "10 柱を山折りし、絵を外にして四角い筒にはります。足は外へ谷折りします。柱の頭を胴の四角い穴にさして、はります",
            # 方角の言い方（北・南・東・西）は紙に刷っていないので、台の上の印と穴で決める（前は説明なしに「南の壁」「北の壁」と書いていた）。
            "11 台を山折りし（絵が外）、角ののりしろを壁の内にはります（底はありません）。柱の印のはしを北、丸い穴のはしを南、壁の四角い穴が寄る側を東と呼びます",
            "柱の足の裏（印刷していない側）にのりを付けて、印の四角にはります。表の面を南（花車の側）に向けます",
            f"13・14 に使う竹ぐし 3 本とも{CUT_POINTS}",
            f"竹ぐし 13 を {peg_cut(p):g}mm に切ります。台の丸い穴に通して、下のはしを机につけます",
            f"17 を軸の横に立て、12 花車を台の上の面から {p['peg_height']:g}mm（17 の上のはしの印）にはります。軸の上のはしからは {PEG_TOP}mm 下です。はれたら 17 は外します",
            f"花車の小さい穴に糸を通して、花びらの先に結びます。穴から玉の中心まで {p['k_cord']:g}mm の所に玉を付け、あまりは切ります",
            f"竹ぐし 2 本を {rod_length(p):g}mm に切ります。縦に重ねてセロハンテープで 3 か所まとめ、14 引く棒にします（真ん中は留め具を巻く所なので、よけます）",
            f"【解釈】14 を南の壁の穴から北の壁の穴へ通し、北の壁から {rod_north_out(p):g}mm 出します。南の壁の所で、棒にえんぴつで印を付けます（押しこむ時の目印）",
            # 1 文に「どこに・どの向きで・どう巻く」を詰めていたので、文を分けた（どこに合わせるかの数は、前と同じ北のふちの位置）。
            f"【解釈】台の下から、16 棒の留め具を棒に巻いてはります。留め具の北のふちは、棒の北のはしから {rodtab_pos(p):g}mm の所です。"
            "印刷した面を内にして、真ん中ののりの印を棒に当てます。両はしを山折りして棒の真上に立て、2 枚の穴を合わせます",
            "【解釈】巻く糸のはしを、合わせた 2 枚の穴に通して結びます。結んでから 2 枚をはり合わせて、旗にします（穴はのりの印の中にあります）",
            # 巻く糸は軸に結んで糊で留める。巻くだけでは、引いた時に糸が軸の上を滑って軸が回らない（前は「軸に 2 回巻く」としか書いていなかった）。
            f"【解釈】糸のもう一方のはしを、台の下から軸（竹ぐし 13）に結びます。結ぶ所は旗の穴から {pull_cord(p):g}mm で、"
            f"高さは旗の穴と同じです（机から約 {flag_hole_z(p):.0f}mm）。結び目にのりを付けてとめ（とめないとすべります）、あまりは切ります",
            # 軸受けは、軸に糸を結んだ後で付ける（先に付けると、腕が邪魔で台の下から軸に手が届かない）。
            "18 軸受けののりしろを山折りします。台を横にたおし、軸の下のはしを 18 の穴に通して、のりしろを西の壁（棒の反対の側）の内にはります。のりしろの下のふちを、壁の下のふちにそろえます",
            # 巻く向きは、台の中の糸を見ずに確かめられる言い方にする（糸は上の面の下にあり、下からは軸受けの腕に隠れる）。
            # 上から見て時計と反対回りに巻くと、糸は軸の鼓の側（北）を通る（pull_unwind の多い側）。
            f"【解釈】棒を印まで押しこみます。鼓を奥・棒を右にして上から見て、花車を時計と反対回りに回し、糸が張るまで巻き取ります（約 {wind_wraps(p)} 回）",
            f"旗が南の壁に当たるまで（{pull_travel(p):g}mm）、棒をすばやく引きます。軸が約 {pull_turns(p):.1f}〜{pull_turns(p, favorable=True):.1f} 回まわり、玉が面に当たるか見ます。"
            "もう一度する時は、棒を印まで押しこみ、同じ向きに巻き直します",
            f"玉が面に届かない時は糸を長く、ふちを打つ時は短くします{span}。軸が回らない時は、結び目と留め具ののりを見ます"]


def _diagram_kanko(x, y, w, h, p):
    """横から見た絵。台・柱・鼓・軸・花車の並びと、振れた玉。"""
    R, Lk = p["k_radius"], p["k_length"]
    span = p["base_length"] + 10
    tall = p["base_height"] + max(p["post_height"] + 2 * R, p["peg_height"]) + 4
    s = min(w / span, h / tall)
    floor = y + h - 2
    top = floor - p["base_height"] * s
    shapes = [{"kind": "rect", "x": x, "y": top, "w": p["base_length"] * s, "h": p["base_height"] * s}]
    px = x + p["post_pos"] * s
    shapes.append({"kind": "rect", "x": px - p["post_side"] / 2 * s, "y": top - p["post_height"] * s, "w": p["post_side"] * s, "h": p["post_height"] * s})
    shapes.append({"kind": "rect", "x": px - Lk / 2 * s, "y": top - (p["post_height"] + 2 * R) * s, "w": Lk * s, "h": 2 * R * s})
    gx = x + peg_pos(p) * s
    wy = top - p["peg_height"] * s
    shapes.append({"kind": "line", "x1": gx, "y1": floor, "x2": gx, "y2": wy})
    shapes.append({"kind": "line", "x1": gx - p["wheel_r"] * s, "y1": wy, "x2": gx + p["wheel_r"] * s, "y2": wy})
    bx = gx - (wheel_anchor(p) + p["k_cord"]) * s
    shapes.append({"kind": "line", "x1": gx - wheel_anchor(p) * s, "y1": wy, "x2": bx, "y2": wy, "dash": "1,0.6"})
    br = p["bead_d"] / 2 * s
    shapes.append({"kind": "rect", "x": bx - br, "y": wy - br, "w": 2 * br, "h": 2 * br})
    return shapes
