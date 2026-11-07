"""雛形 float: 紙の舟（四隅を糊で留めた浅い箱）に葉と人形を立て、水に浮かべる（浮き人形・水からくり、推定）。

出典はコマ 28 の右頁。大きな鉢の水に渦の線があり、槍（か薙刀。先の下に白い刃か旗のような物）を持ち、烏帽子をかぶった
小さな人形が、水に浮いた丸い葉（放射の葉脈が見えるので蓮の葉と読む・【解釈】）の上に立つ。
【解釈】水の上で浮く、または渦に乗って回る玩具と読む。昔の物が何で浮いていたか（木・葉・紙）は図から分からない。
この型紙では、紙の舟を浮きにし、その底に葉を貼って人形を立てる。刷る形（vane）で、息を吹くと回る風受け 2 つを足せる。

寸法は図の比と家庭の紙で作れる大きさから出した見込みで、どの値も実物では未確認。寸法として変えてよいのは RANGES の名前の値だけで、範囲の外と知らない名前は F5.range で落ちる。

動きの見込み（F5.float）の前提:
- 水の密度は 1g/cm³（1g が 1000mm³ を押しのける）。舟は箱のまま平らに沈み、喫水 d ＝ 押しのける体積 ÷ 底の面積。
- 質量は刷る部品の面積 × 紙の面密度、外側に貼るテープの面積 × テープの面密度、油粘土の重り。糊の重さは入れない。
  テープは底と壁の外側に、ふちから内へ折り返す帯（幅 TAPE_FOLD・壁の上端にあるので G を上げる）を足して数える。
- 紙は水を吸うと重くなり柔らかくなるが、この式は吸水を入れない（乾いた紙の重さと形のまま見る）。
  テープで外側をふさぐのはそのため。濡れた後の浮き方は実物で確かめていない。
  水よけは必ず貼る物として、その面密度（tape_gsm）を下限つきで持つ。ろうを塗る時は、塗ったろうの g/m² をここに入れる。
- 粘土の重りは、底の四隅の四角（辺 clay_side）に同じ重さずつ平たく押し付ける。厚み ＝ 体積 ÷ 実の面積
  （四角 4 つを合わせて底の内に切った面。下の箇条）、重心の高さはその半分（密度 CLAY_DENSITY は油粘土の見込み・未確認）。厚く積むと崩れやすく、重心も上がる。
- 余裕（乾舷）＝ 壁の高さ − 喫水。これが FREEBOARD_MIN より小さいと、波や息でふちから水が入ると見込む。
  さらに、傾いた時にふちが水に着く角 atan(2·乾舷 ÷ 幅) が MIN_HEEL より小さいと、少し傾いただけで水が入る。
- 安定は横揺れ（狭い向き）で見る。浮心の高さ KB ＝ d/2、BM ＝ I/V（長方形の水線面 I ＝ 長さ × 幅³ ÷ 12）、
  重心の高さ KG は各部品の重さをその重心の高さで平均する（人形が高いほど G が上がる）。GM ＝ KB + BM − KG が GM_MIN より大きければ戻る。
  小さな傾きの式なので、大きく傾いた時の戻りは見ない。
- 風受け（vane=cups）は半円に丸めた紙 2 つを、底の長さ（tray_length・展開図の左右）の向きの両端に、口を逆の向きにして立てる。
  横から吹くと、口の側の風受けは平らな側より強く押される（お椀形の抗力の差。値は見込み）ので、舟が回ると見込む。
  回る速さ・水の抵抗は式にせず、風受けが壁より上に出て息を受けられる事、底に収まる事、息で傾いてもふちが水に着かない事（下の箇条）を見る。
  底に収まるかは、外へ折って貼る足の歯の先まで（半径 ρ + CUP_TAB の半円）で見る。人形の足の糊代も、葉に寝かせた台形の角まで見る。
- 人形は底の幅（tray_width・展開図の上下）の向きに立てる。葉の矢印を底の刻み（長さの向き）に向け、足の印（矢印と直角）に立てる。
  組み方の文は「長い向き」と言わず、刷った矢印と刻みで言う（幅が長さより長い舟でも食い違わない）。
  長さの向きに立てると、槍の下の刃が端の風受けに当たる（既定の寸法で 1.4mm）。幅の向きでは、壁の上端より下の人形の外形の
  半幅が、底の半幅（壁の紙の分 WALL_GAP を引く）に入るかを見る。紙を裏返して貼っても入るよう、足の真ん中から左右の遠い方で見る。
  壁の上端より上は、壁の外へ出てもよい。人形はまっすぐ立つと見る。風受けの足跡は葉の外にあるので、人形が矢印の向きへ傾いても、
  傾きが atan(葉の半径 ÷ 風受けの高さ) より小さい間は風受けに届かない（既定で約 30°。式には入れない）。
  向きは刷った刻みで決まるので、刻みを NOTCH_MIN 刷る所が無い寸法は落とす。風受けとの当たりは床にしない: 風受けの足跡は葉に重ならないので（F5.float 風受け）、
  葉の真ん中に立つ人形の紙の面と、葉の上に寝かせる糊代には届かない（試験でこの前提を見る）。
- 折る向きと糊の面: 糊代の斜線は刷った面にある。斜線の面が貼る相手に当たり、組み上がった物の見える側に斜線が残らない向きに折る。
  舟は全部を谷折りにして刷った面を内にする（底の貼る所の印が内に要るため）。それで壁の内側に雷文が出て、外側は紙の白のまま。
  角の糊代は谷折りで内を向くので、となりの壁（糊代の無い壁）の外側（裏）に貼る。人形の足と風受けの歯は山折りにして、斜線の面を
  葉と底に当てる（谷折りだと糊代の斜線が上を向き、葉の上と底に残る）。風受けは刷った面を丸い口の側にして丸める。
- 風受けの無い形（vane=none）は、水をかき回して作った渦に舟を乗せて回す（図の渦の線の【解釈】）。渦の速さと舟の回り方は式にしていない。
- 組み方の文は、決まった行数に詰める（STEP_LINES_MAX。前はサイトの手順の紙（A4・左の列 144mm・字 3.6mm）に収めるため。手順の紙は廃止し、文はサイトの組み立ての頁に出す）。手順の数は形だけで決まり、
  重りの有無で変わらない（作った人の報告は手順の番号で来るので、同じ形の報告を番号で数えられるように）。
- 粘土の厚みは、四隅の四角を合わせて底の内に切った実の面積から出す（狭い舟で四角が重なると 4 × 辺² より狭い）。
  粘土は G を下げるが、重さで V が増えて BM ＝ I/V も下がるので、狭い舟では GM が上がらない事がある。
- 息で倒れないか（風受けつき・blow_arm と righting_max）: 口から 10〜20cm の息を速さ BREATH_V の風と見て、壁より上に出た風受けの面
  （幅 2ρ × 壁より上の高さ）に動圧 ½·ρ空気·v² × 抗力係数が掛かると見る。口の側 CD_CUP_OPEN・丸い側 CD_CUP_BACK。2 つの力の和に、
  その面の真ん中の高さと喫水の半分（水が押し返す高さ）の差を掛けた物が傾ける力で、それを舟の重さで割った長さを「傾ける腕」と呼ぶ。
  風受けの口は幅の向きを向くので、息は幅の向きに当たり、舟は幅の向きに傾く。
  戻す側は、小さな傾きの式（GM·sinθ）を使わない。紙の舟は軽く、喫水が浅い（既定で 1.3mm）ので、2° ほど傾くと底の高い側の角が水から出て、
  そこから先は戻す腕が幅の半分より手前で頭打ちになる。箱の断面（幅 W・喫水 d）で、押しのける水の断面積 W·d を保って傾けた時の
  戻す腕 GZ(θ) を出し（righting_arm）、ふちが水に着く角までの最大（righting_max）と比べる。
  傾ける腕に余裕 BLOW_SAFETY を掛けた長さが、戻す腕の最大に届く寸法は落とす（つり合う傾きが無く、倒れるかふちから水が入る）。
  乾舷・ふちの角・GM の検査が落ちた舟と、息を受けない風受けには重ねない。2 つの力の差が舟を回す力になるが、回る速さは式にしない。
  入れていない物: 舟の壁が受ける息（息は風受けを狙う細い流れと見る）、人形が受ける息（紙の面が息と平行。舟が回って息が長さの向きに
  当たる間は、人形が面で息を受ける）、傾いた後の力の変わり方。
  落ちるのは、狭い舟に高い風受けを立てた時（負の場面 float_neg_blow）。
  見込みの値（BREATH_V・抗力係数・余裕）は 1 か所に置く。作った人の報告「息で水が入った・回らない」（Issue #21）が集まった時に直す所。
"""
import math

from shapely.geometry import LineString, Polygon, box
from shapely.ops import unary_union

from ..paper_words import paper_name  # 紙の書き方は 4 つの名前だけ（制作者の指示 2026-11-05）
from ..model import Failure, Part

ID = "float"
DEFAULTS = {
    "vane": "none",
    # 舟の底の長さ・幅と壁の高さ。底が広いほど浅く浮き、横に倒れにくい（BM が幅の 2 乗で効く）。
    "tray_length": 90, "tray_width": 60, "wall_height": 22, "glue": 8,
    # 人形の高さはコマ 28 の図で葉の直径の 1.2 倍ほどに見える（斜めの図の目測）。
    # 葉の半径 20 は、風受けの足跡（半円 ＋ 外へ折る歯）を葉の両側の底に置けるため（90mm の舟で 40 + 2 × 23 = 86mm）。
    "figure_height": 60, "leaf_radius": 20,
    # 風受けの紙の幅（丸めると半円の周になる）と高さ。壁より上に出す。
    "cup_width": 22, "cup_height": 34,
    "ballast_g": 4.0, "clay_side": 12,
    # 紙とテープの面密度は見込み。実物を量ったら置き換える。OPP の梱包テープは 1m² で 60g 前後と見込んだ（未確認）。
    "paper_gsm": 150, "tape_gsm": 60,
}
RANGES = {
    # 舟の型紙（長さ＋壁 2 枚）が A4 の印字域の幅 190mm に入る上限。
    "tray_length": (40, 110), "tray_width": (20, 80), "wall_height": (8, 35), "glue": (5, 12),
    "figure_height": (30, 90), "leaf_radius": (8, 35),
    "cup_width": (12, 40), "cup_height": (15, 60),
    "ballast_g": (0, 100), "clay_side": (6, 20),
    "paper_gsm": (40, 400), "tape_gsm": (20, 150),
}
VANES = ("none", "cups")
# 刷る形を決める寸法（風受けがあるか）。回るかは図の解釈の違いなので、寸法を直に渡す入口では必ず書かせる。
FORM = "vane"
FORMS = VANES
# 既定の出典（data/sources/ の名前）。--source を書かない時に、雛形と合わない出典の印を刷らないため。
SOURCE = "NDL-1187053-R0000028-R-float"
# 2 つの形は同じ玩具（コマ 28 右）の作り分けなので、どちらも同じ出典。形ごとに書くのは、別の玩具の出典を渡した時に F1.source で落とすため。
SOURCES = {v: SOURCE for v in VANES}
WATER = 1000.0  # 水 1g が押しのける体積（mm³）
FREEBOARD_MIN = 5  # 乾舷の下限（mm）。見込み
MIN_HEEL = 12  # ふちが水に着くまでに傾ける角の下限（°）。波と、置く時の傾きの余裕の見込み。息で倒れないかは blow_arm と righting_max で別に見る
GM_MIN = 3  # 戻る力の余裕（mm）。紙の歪み・人形の貼り位置のずれを見込む
CLAY_DENSITY = 1.7  # 油粘土の密度（g/cm³）の見込み。実物を量ったら置き換える
CLAY_T_MAX = 8  # 粘土の厚みの上限（mm）。これより厚く小さな四角に積むと、押し付けても崩れて片寄ると見込む
CLAY_INSET = 3  # 粘土の四角を底の四隅の折り線から離す長さ（mm）
CUP_INSET = 1  # 風受けの足跡（外へ折った歯の先）を底の両端の折り線から離す長さ（mm）
CUP_TAB = 4  # 風受けの足の歯の長さ（mm）。歯は外へ折って底に貼るので、足跡は半円の外へこの長さだけ広がる
TAB = 7  # 人形と風受けの足の糊代の高さ（mm）
NOTCH_MIN = 1.0  # 葉の向きの刻みの長さの下限（mm）。これより短いと刷っても見えず、葉を 90° 回して貼る（人形が風受けに当たる）と見込む
WALL_GAP = 0.5  # 人形の外形を壁の内の面から離す長さ（mm）。壁の紙の厚みとテープの折り返しの見込み
TAPE_FOLD = 5  # 水よけのテープをふちから内へ折り返す幅（mm）。組み方の文と質量の式で同じ値を使う
# 舟のラベル「1 舟」の幅と高さの見込み（compose の字の大きさ 2.8mm・行送り 1.25。幅は Noto Serif CJK JP で 4.8mm と測り、1mm の空きを足した）。
# 粘土の印の右に置けるかの判定と、雷文を始める所にだけ使う。
LABEL_W, LABEL_H = 6, 3.5
CUP_ABOVE = 5  # 風受けが壁の上に出る長さの下限（mm）。壁の陰では息を受けない
STIR_TURNS = 5  # 風受けの無い形で、渦を作るために水をかき回す回数の見込み。少ないと舟が回らず、速いと波でふちから水が入る（未確認）
# 組み方の文の行数の上限。手順の紙は廃止し（制作者の決まり 2026-11-06「文章のプリントは廃止。組み立て用のページだけでいい。」）、文はサイトの組み立ての頁に出す。
# 画面でも短い方が読みやすいので、上限は残す。上限を決めた時の理由（前のサイトの手順の紙（A4）は、左の列 144mm に字 3.6mm で組み方を刷り、
# その下に予想・試した事・問いの欄が続いた）:
# 前の版は、風受けつきの既定で 20 行あり、紙の印字域の下へ 5.2mm はみ出していた。16 行で 2.8mm 余り、今の 15 行で 7.2mm 余る
# （2026-11-05 にサイトの手順の紙の組み立てに float を載せて測った。題と遊び方の文は仮の 1 行ずつ）。
STEP_LINES_MAX, STEP_COL_W, STEP_SIZE = 16, 144.0, 3.6
# 息で倒れないかの検査の、見込みの値（風受けつき）。どれも実物で量っていない。作った人の報告（Issue #21）で「息で水が入った・回らない」が集まったら、ここを直す。
# BREATH_V: 口から 10〜20cm の所の息の速さ（m/s）。
# CD_CUP_OPEN・CD_CUP_BACK: 風受けの口の側と丸い側の抗力係数。長い半円筒の値（口の側 2.3・丸い側 1.2）に、壁より上に出る面が
#   高さと幅の同じほどの短い面である分の割引（正方形の板 1.17 ÷ 長い板 1.98 ≈ 0.6）を掛けた。
# BLOW_SAFETY: 息が舟を傾ける腕に掛ける余裕。力は速さの 2 乗に比例するので、2 は息が見込みの 1.4 倍強い時に当たる。
BREATH_V, CD_CUP_OPEN, CD_CUP_BACK, BLOW_SAFETY = 4.0, 1.4, 0.7, 2.0
AIR_DENSITY, GRAVITY = 1.2, 9.81  # 空気の密度（kg/m³）と重力の加速度（m/s²）。物理の定数で、見込みの値ではない
# 貼る所の印の色と太さ。破線は谷折り、黒の実線は切る線と読まれるので、印は茶の細い実線にする。
MARK, MARK_SW = "#8a4f2e", 0.35
TITLES = {"none": "浮かべる", "cups": "息で回す風受けつき"}
HULL, HULL_DARK, LEAF, VEIN, ROBE, HAKAMA, INK, SKIN, CUP = "#b9c2a4", "#8d9878", "#7d8a5a", "#4d5638", "#c9b46a", "#e6e0cf", "#2f2c27", "#ece6d6", "#d9cfae"


def title(p):
    return TITLES[p["vane"]]


def spec():
    return {"template_id": ID, "defaults": DEFAULTS, "ranges": RANGES, "vane": VANES}


def check_range(p):
    out = []
    for k, v in p.items():
        if k == "vane":
            if v not in VANES:
                out.append(Failure("F5.range", k, f"{v} は {VANES} のどれでもない"))
        elif k not in RANGES:
            out.append(Failure("F5.range", k, "知らない寸法の名前"))
        elif not isinstance(v, (int, float)) or isinstance(v, bool) or not RANGES[k][0] <= v <= RANGES[k][1]:
            out.append(Failure("F5.range", k, f"{v} は範囲 {RANGES[k]} の外"))
    return out


# コマ 28 の人形。図を 800×994 に拡大した切り抜き（pct:66,58,8,12）の座標で手で取った点。画素は使っていない。足の線は y=890。
_FEET, _TOP, _LEFT, _RIGHT = 890, 112, 95, 662
_SPEAR = [(330, 125), (215, 560), (168, 860)]  # 柄の中心線
_TIP = [(312, 112), (338, 116), (350, 150), (332, 200), (318, 160)]
_BLADE = [(140, 655), (186, 662), (168, 880), (98, 830)]  # 下の白い刃か旗（【解釈】）
_HAT = [(352, 295), (385, 282), (415, 295), (420, 360), (452, 420), (405, 440), (385, 480), (360, 470), (350, 400)]
_FACE = [(372, 402), (414, 396), (424, 448), (388, 476), (366, 452)]
_SLEEVE_L = [(195, 560), (345, 495), (380, 600), (250, 672)]
_TORSO = [(345, 470), (460, 440), (482, 622), (360, 642)]
_SLEEVE_R = [(455, 450), (600, 490), (662, 505), (632, 522), (626, 692), (530, 692), (480, 622)]
# 袴の裾は足の線（y=890）まで平らに取る。元の点は右の裾が 872 まで上がっていて、糊代の右 4 割の上に紙が無かった。
_HAKAMA = [(290, 690), (360, 640), (482, 622), (530, 692), (632, 822), (622, 890), (260, 890)]
_FOOT = (262, 628)  # 足の台（糊代）を付ける幅（x の範囲）。袴の裾の幅に収める


def _fig_scale(p):
    return p["figure_height"] / (_FEET - _TOP)


# 外形は絵を 0.6mm 太らせて取るので、その分だけ絵を右下へずらし、部品の左上を原点 (0, 0) にそろえる。
_OFF = 0.6


def _fig_pts(pts, s):
    return [((x - _LEFT) * s + _OFF, (y - _TOP) * s + _OFF) for x, y in pts]


def _feet(p):
    """人形の足の線（山折り）の y。"""
    return (_FEET - _TOP) * _fig_scale(p) + _OFF


def foot_width(p):
    return (_FOOT[1] - _FOOT[0]) * _fig_scale(p)


def _figure(p):
    """人形 1 枚。足の線で山折りした糊代を葉に貼って立てる（糊代は絵の裏へ回り、斜線の面が葉に当たる）。
    外形は絵の形を合わせた物を少し太らせて取る（絵を外形の内に置くため）。"""
    s = _fig_scale(p)
    feet = _feet(p)
    spear = Polygon(LineString(_fig_pts(_SPEAR, s)).buffer(max(0.9, 12 * s), cap_style=2))
    # 顔も外形に入れる。帽子と胴の間の顔の点は、高い人形（70mm から）で 0.6mm の太らせでは隠れず、外形の外に出た
    shapes = [Polygon(_fig_pts(q, s)) for q in (_TIP, _BLADE, _HAT, _FACE, _SLEEVE_L, _TORSO, _SLEEVE_R, _HAKAMA)] + [spear]
    upper = unary_union(shapes).buffer(_OFF, join_style=2).intersection(box(-5, -5, 1000, feet))
    x0, x1 = (_FOOT[0] - _LEFT) * s + _OFF, (_FOOT[1] - _LEFT) * s + _OFF
    tab = Polygon([(x0, feet), (x1, feet), (x1 - 1.5, feet + TAB), (x0 + 1.5, feet + TAB)])
    whole = unary_union([upper, tab]).simplify(0.05)
    if whole.geom_type != "Polygon":  # 部品が離れると 1 枚の紙にならない。形を作る手で取った点の誤りなので、すぐ分かるように止める
        raise ValueError("人形の外形が 1 つにつながらない")
    outline = [(round(x, 3), round(y, 3)) for x, y in list(whole.exterior.coords)[:-1]]
    clip = box(-5, -5, 1000, feet - 0.4)  # 絵は折り線と糊代にかけない

    def fill(q, color, sw=0.25):
        g = Polygon(_fig_pts(q, s)).intersection(clip)
        return {"kind": "poly", "pts": list(g.exterior.coords)[:-1], "fill": color, "stroke": INK, "sw": sw}
    art = [fill(_BLADE, SKIN), fill(_HAKAMA, HAKAMA), fill(_SLEEVE_L, ROBE), fill(_SLEEVE_R, ROBE), fill(_TORSO, ROBE), fill(_HAT, INK), fill(_FACE, SKIN, 0.15)]
    spear_ink = Polygon(LineString(_fig_pts(_SPEAR, s)).buffer(max(0.45, 6 * s), cap_style=2)).intersection(clip)
    art.insert(0, {"kind": "poly", "pts": list(spear_ink.exterior.coords)[:-1], "fill": INK})
    art.insert(1, fill(_TIP, INK, 0))
    part = Part(3, "figure", "人形", outline, label_xy=((x0 + x1) / 2 - 1, feet + 1.5), label="3", art=art)
    # 山折り。谷折りだと糊代の斜線の面が上を向き、葉の上（人形の前）に斜線が見えたまま残る
    part.mountain = [((x0, feet), (x1, feet))]
    part.glue = [[(x0, feet), (x1, feet), (x1 - 1.5, feet + TAB), (x0 + 1.5, feet + TAB)]]
    return part


def _tray(p):
    """舟の展開図。底（長さ × 幅）の 4 辺に壁を付け、長さの向きの壁の両端に糊代を付ける。
    谷折りで刷った面が内になるので、糊代の斜線の面は内を向く。糊代は、となりの壁（糊代の無い壁）の外側（裏）に貼って角を閉じる。"""
    L, W, h, g = p["tray_length"], p["tray_width"], p["wall_height"], p["glue"]
    c = min(2.0, h / 4)  # 糊代のふちの側を細める。となりの壁の外に重ねた時、ふちから上へ出さない（底の側は 45° に落としてある）
    pts = [(h, 0), (h + L, 0), (h + L + g, c), (h + L + g, h - g), (h + L, h), (2 * h + L, h), (2 * h + L, h + W), (h + L, h + W),
           (h + L + g, h + W + g), (h + L + g, 2 * h + W - c), (h + L, 2 * h + W), (h, 2 * h + W), (h - g, 2 * h + W - c), (h - g, h + W + g),
           (h, h + W), (0, h + W), (0, h), (h, h), (h - g, h - g), (h - g, c)]
    # ラベルは左上の粘土の印の右に置く（印と重ねると読めない）。短い舟で葉の丸の印がそこまで来る時は、上の壁の左端に置き、
    # 雷文をその右から始める（長さ 40〜60 の舟で、ラベルが葉の印に重なるため）。
    lx = h + CLAY_INSET + 2 + p["clay_side"]
    on_floor = lx + LABEL_W <= h + L / 2 - p["leaf_radius"]
    part = Part(1, "tray", "舟", pts, label_xy=(lx, h + 2) if on_floor else (h + 2, (h - LABEL_H) / 2), label="1 舟")
    part.valley = [((h, h), (h + L, h)), ((h, h + W), (h + L, h + W)), ((h, h), (h, h + W)), ((h + L, h), (h + L, h + W)),
                   ((h, 0), (h, h)), ((h + L, 0), (h + L, h)), ((h, h + W), (h, 2 * h + W)), ((h + L, h + W), (h + L, 2 * h + W))]
    part.glue = [[(h + L, 0), (h + L + g, c), (h + L + g, h - g), (h + L, h)], [(h + L, h + W), (h + L + g, h + W + g), (h + L + g, 2 * h + W - c), (h + L, 2 * h + W)],
                 [(h, 2 * h + W), (h - g, 2 * h + W - c), (h - g, h + W + g), (h, h + W)], [(h, h), (h - g, h - g), (h - g, c), (h, 0)]]
    e = 0.25

    def panel(x0, y0, x1, y1, color):
        return {"kind": "poly", "pts": [(x0 + e, y0 + e), (x1 - e, y0 + e), (x1 - e, y1 - e), (x0 + e, y1 - e)], "fill": color}
    part.art = [panel(h, h, h + L, h + W, HULL), panel(h, 0, h + L, h, HULL_DARK), panel(h, h + W, h + L, 2 * h + W, HULL_DARK),
                panel(0, h, h, h + W, HULL_DARK), panel(h + L, h, 2 * h + L, h + W, HULL_DARK)]
    # 雷文（コマ 28 の鉢の縁の模様）を、長さの向きの壁に細い線で写す。鉢の模様を舟に移した翻案。谷折りで刷った面が内になるので、
    # 組み上がると壁の内側に出る。下の壁の文様は 180° 回して描く（上下も左右も返す）。舟の内から見ると、2 枚の壁の文様が同じ形で、
    # 口が底の側を向く（回さないと、下の壁だけ口がふちの側を向く。上下だけ返すと、渦の巻く向きが 2 枚で逆になる）。
    hh = h * 0.3
    for y0, x, turn in ((h * 0.35, h + 3 + (0 if on_floor else LABEL_W), False), (2 * h + W - h * 0.65, h + 3, True)):
        a, b = (y0, y0 + hh) if turn else (y0 + hh, y0)  # a は口の側（底の折り線に近い方）、b は閉じた側（ふちに近い方）
        while x + 8 < h + L - 3:
            xs = [x + 6 - dx if turn else x + dx for dx in (0, 0, 6, 6, 2.5, 2.5)]
            ys = [a, b, b, a, a, a + (b - a) * 0.55]
            part.art.append({"kind": "line", "pts": list(zip(xs, ys)), "stroke": INK, "sw": 0.35, "mark": "fret"})
            x += 9
    # 貼る所の印。式（mass_points）は葉と人形が底の真ん中、粘土が四隅に同じだけ、と見るので、その所を刷って組み方の文で言う。
    # 印の形は floor_marks の 1 つの式から出す（刷る印と F5.float が見る置き場を食い違わせない）。
    # 底に収まらない印は刷らない。収まらない寸法は F5.float で落ちるので、絵の検査（折り線をまたぐ）を重ねて鳴らさない。
    # 折り線から 0.5mm 内で見る（折り線に触れる印も「またぐ」と読まれる。F5.float が許す葉は折り線から 1mm 内なので、通る寸法の印は刷る）。
    fm = floor_marks(p)
    floor = box(0.5, 0.5, L - 0.5, W - 0.5)
    if floor.contains(fm["leaf"]):
        ring = list(fm["leaf"].exterior.coords)
        part.art.append({"kind": "line", "pts": [(x + h, y + h) for x, y in ring], "stroke": MARK, "sw": MARK_SW, "mark": "leaf"})
        # 葉の向きの刻み（丸い印の右の外へ）。葉の矢印の先をここへ向ける。長さは notch_length の 1 つの式から出し、
        # NOTCH_MIN に届かない寸法は F5.float で落とす（刷らないまま組み方の文が刻みを言わないように）
        cx, cy, r = L / 2, W / 2, p["leaf_radius"]
        k = notch_length(p)
        if k >= NOTCH_MIN:
            part.art.append({"kind": "line", "pts": [(h + cx + r, h + cy), (h + cx + r + k, h + cy)], "stroke": MARK, "sw": 0.6, "mark": "leafdir"})
    for sq in fm["ballast"]:
        if floor.contains(sq):
            part.art.append({"kind": "poly", "pts": [(x + h, y + h) for x, y in list(sq.exterior.coords)[:-1]], "fill": "none", "stroke": MARK, "sw": MARK_SW, "mark": "ballast"})
    for arc in fm["cup_arcs"]:
        if floor.contains(LineString(arc)):
            part.art.append({"kind": "line", "pts": [(x + h, y + h) for x, y in arc], "stroke": MARK, "sw": MARK_SW, "mark": "cups"})
    return part


def floor_marks(p):
    """舟の底に置く物の足跡（底の左上を原点にした mm）。葉の丸・粘土の四角 4 つ・風受けの半円 2 つ（と、その弧の線）。"""
    L, W = p["tray_length"], p["tray_width"]
    cx, cy, cs = L / 2, W / 2, p["clay_side"]
    out = {"leaf": Polygon(_circle(cx, cy, p["leaf_radius"])), "ballast": [], "cups": [], "cup_arcs": []}
    if p["ballast_g"] > 0:
        for x0, y0 in ((CLAY_INSET, CLAY_INSET), (L - CLAY_INSET - cs, CLAY_INSET), (CLAY_INSET, W - CLAY_INSET - cs), (L - CLAY_INSET - cs, W - CLAY_INSET - cs)):
            out["ballast"].append(box(x0, y0, x0 + cs, y0 + cs))
    if p["vane"] == "cups":
        # 風受けは長い向きの両端に、丸い口を逆の向きにして立てる。
        rho = cup_radius(p)
        R = rho + CUP_TAB
        for ex, sign in ((CUP_INSET + R, -1), (L - CUP_INSET - R, 1)):
            arc = [(ex + rho * math.cos(math.pi * i / 24), cy + sign * rho * math.sin(math.pi * i / 24)) for i in range(25)]
            out["cup_arcs"].append(arc)  # 刷る印は丸めた紙が立つ線（半径 ρ）
            # 足跡は外へ折った歯の先まで（半径 ρ + 歯）。半円だけで見ると、歯が壁を上がるか葉に乗っても通っていた
            out["cups"].append(Polygon([(ex + R * math.cos(math.pi * i / 24), cy + sign * R * math.sin(math.pi * i / 24)) for i in range(25)]))
    return out


def notch_length(p):
    """葉の向きの刻みの長さ（mm）。丸い葉の印の右から外へ 3mm まで。底の折り線から 0.5mm 内、右の風受けの足跡（外へ折る歯を含む）の
    手前 0.3mm で止める（止めないと、既定の寸法で歯の下に 1mm 入った）。"""
    L, r = p["tray_length"], p["leaf_radius"]
    cx = L / 2
    k = min(3.0, L - 0.5 - (cx + r))
    for c in floor_marks(p)["cups"]:
        if c.bounds[0] > cx:
            k = min(k, c.bounds[0] - (cx + r) - 0.3)
    return k


def clay_area(p):
    """粘土を載せる実の面積（mm²）。四角を合わせ、底の内に切った面。狭い舟では四角が重なるか底から出るので、4 × 辺² では広すぎる。"""
    sq = floor_marks(p)["ballast"]
    if not sq:
        return 0.0
    return unary_union(sq).intersection(box(0, 0, p["tray_length"], p["tray_width"])).area


def clay_thickness(p):
    """粘土の厚み（mm）＝ 体積（mm³）÷ 実の面積。"""
    a = clay_area(p)
    return p["ballast_g"] * 1000 / CLAY_DENSITY / a if a > 0 else 0.0


def _circle(cx, cy, r, n=72):
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def _leaf(p):
    """蓮の葉（【解釈】）。コマ 28 の図の、中心から出る 7 本ほどの葉脈を写す。"""
    r = p["leaf_radius"]
    art = [{"kind": "poly", "pts": _circle(r, r, r - 0.3), "fill": LEAF}]
    for i, k in enumerate((0.8, 0.55, 0.75, 0.6, 0.8, 0.5, 0.7)):
        a = 2 * math.pi * i / 7 + 0.3
        art.append({"kind": "line", "pts": [(r + 0.08 * r * math.cos(a), r + 0.08 * r * math.sin(a)), (r + k * r * math.cos(a), r + k * r * math.sin(a))], "stroke": VEIN, "sw": 0.4})
    # 人形の足の印。式は人形が葉の真ん中（＝舟の真ん中）に立つと見る。
    # 葉より広い足は F5.float（人形）で落ちる。印は葉の内に留め、絵の検査（F5.image_box）を重ねて鳴らさない
    # 足の印は葉の y の向き（矢印と直角）。人形を底の幅の向きに立てるため
    fw = min(foot_width(p), 2 * r - 1)
    art.append({"kind": "line", "pts": [(r, r - fw / 2), (r, r + fw / 2)], "stroke": MARK, "sw": 0.6, "mark": "figure"})
    # 数字の「2」は足の印（真ん中の縦の線）をよけて左下に置く（label_xy）。
    # 向きの矢印（葉の +x）。舟の底の丸い印の右の刻みに向けて貼る。人形の糊代もこの向きへ寝かせる
    a0, a1, hd = r + 0.15 * r, r + 0.85 * r, min(1.5, 0.12 * r)
    art.append({"kind": "line", "pts": [(a0, r), (a1, r), (a1 - hd, r - hd), (a1, r), (a1 - hd, r + hd)], "stroke": MARK, "sw": 0.5, "mark": "arrow"})
    return Part(2, "leaf", "葉", _circle(r, r, r), label_xy=(0.5 * r, 1.3 * r), label="2", art=art)


def foot_footprint(p):
    """人形の足の糊代を葉の上に寝かせた足跡（葉の中心を原点にした mm）。足の線は葉の y の向きに中心を通り、糊代は矢印の向き（+x）へ倒す。"""
    fw = foot_width(p)
    return Polygon([(0, -fw / 2), (0, fw / 2), (TAB, fw / 2 - 1.5), (TAB, -fw / 2 + 1.5)])


def figure_half_width(p, zmax):
    """人形の外形のうち、足の線から高さ zmax までの所の半幅（足の真ん中から左右の遠い方、mm）。
    裏返して貼っても同じに見るため、左右の遠い方を両側に取る。"""
    fig = _figure(p)
    feet = _feet(p)
    low = Polygon(fig.outline).intersection(box(-5, feet - zmax, 1000, feet))
    if low.is_empty:
        return 0.0
    xc = ((_FOOT[0] + _FOOT[1]) / 2 - _LEFT) * _fig_scale(p) + _OFF
    x0, _, x1, _ = low.bounds
    return max(xc - x0, x1 - xc)


def cup_radius(p):
    """風受けの紙を半円に丸めた時の半径。紙の幅が半円の周（π × 半径）になる。"""
    return p["cup_width"] / math.pi


FRINGE_PITCH, FRINGE_GAP = 4, 0.8  # 足の糊代の歯の目安の幅と、歯の間の切り込みの幅（mm）


def _cup(number, key, name, p):
    """風受け 1 枚。足の糊代は切り込みで歯に分ける。半円に丸めると縁が曲がるので、1 枚の帯のままでは底に平らに貼れない。
    刷った面を丸い口の側にして丸め、歯は外へ山折りにする（斜線の面が底に当たる）。"""
    w, H = p["cup_width"], p["cup_height"]
    n = max(3, round(w / FRINGE_PITCH))
    pitch = w / n
    teeth = [(i * pitch + (FRINGE_GAP / 2 if i else 0), (i + 1) * pitch - (FRINGE_GAP / 2 if i < n - 1 else 0)) for i in range(n)]
    pts = [(0, 0), (w, 0)]
    for a, b in reversed(teeth):
        pts += [(b, H), (b, H + CUP_TAB), (a, H + CUP_TAB), (a, H)]
    part = Part(number, key, name, pts[:-1], label_xy=(1, 1.5), label=str(number))
    # 山折りの線は歯ごとに切らず、幅いっぱいの 1 本で刷る。歯は 3mm ほどで、山折りの線の刻み（3mm の線で始まる 5.6mm の繰り返し）
    # より短く、歯ごとに刷ると切れ目の無い実線に見えて、切る線と読まれる
    part.mountain = [((0, H), (w, H))]
    part.glue = [[(a, H), (b, H), (b, H + CUP_TAB), (a, H + CUP_TAB)] for a, b in teeth]
    part.art = [{"kind": "poly", "pts": [(0.2, 0.2), (w - 0.2, 0.2), (w - 0.2, H - 0.4), (0.2, H - 0.4)], "fill": CUP}]
    return part


def parts(p):
    out = [_tray(p), _leaf(p), _figure(p)]
    if p["vane"] == "cups":
        out += [_cup(4, "cupa", "風受け（右）", p), _cup(5, "cupb", "風受け（左）", p)]
    return out


def _area(q):
    return Polygon(q.outline).area


def mass_points(p):
    """(質量 g, 重心の高さ mm) の点。高さは舟の底の外から測る。紙の厚みは高さに入れない（0.2mm ほどで、壁の高さより桁で小さい）。"""
    L, W, h = p["tray_length"], p["tray_width"], p["wall_height"]
    gsm, tape = p["paper_gsm"] / 1e6, p["tape_gsm"] / 1e6
    by = {q.key: q for q in parts(p)}
    floor = L * W
    pts = [(floor * gsm, 0), ((_area(by["tray"]) - floor) * gsm, h / 2),
           # テープは底と 4 枚の壁の外側を覆う（角の糊代はとなりの壁の外に重なり、テープはその上から覆うので、面積は変わらない）。
           # ふちから内へ折り返す帯は壁の上端にある
           (floor * tape, 0), (2 * (L + W) * h * tape, h / 2), (2 * (L + W) * TAPE_FOLD * tape, h - TAPE_FOLD / 2),
           (_area(by["leaf"]) * gsm, 0)]
    fig = by["figure"]
    feet = _feet(p)
    poly = Polygon(fig.outline)
    upper = poly.intersection(box(-5, -5, 1000, feet))
    # 人形は葉の上に立つ。葉の厚みは入れない。重心の高さは足の線からの距離（画面の y は下向きなので引く）
    pts.append((upper.area * gsm, feet - upper.centroid.y))
    pts.append(((poly.area - upper.area) * gsm, 0))
    for k in ("cupa", "cupb"):
        if k in by:
            pts.append((p["cup_width"] * p["cup_height"] * gsm, p["cup_height"] / 2))
            pts.append(((_area(by[k]) - p["cup_width"] * p["cup_height"]) * gsm, 0))
    pts.append((p["ballast_g"], clay_thickness(p) / 2))
    return pts


def hydro(p):
    """浮き方の数。戻り値は辞書: 質量 m（g）・体積 V（mm³）・喫水 d・乾舷 f・KB・BM・KG・GM（mm）・ふちが着く角 heel（°）。"""
    L, W = p["tray_length"], p["tray_width"]
    pts = mass_points(p)
    m = sum(w for w, _ in pts)
    V = m * WATER
    d = V / (L * W)
    f = p["wall_height"] - d
    long, short = max(L, W), min(L, W)
    BM = long * short ** 3 / 12 / V  # 狭い向きの横揺れ（長い辺を軸に傾く）が倒れやすい
    KG = sum(w * z for w, z in pts) / m
    KB = d / 2
    heel = math.degrees(math.atan2(2 * f, short)) if f > 0 else 0.0
    return {"m": m, "V": V, "d": d, "f": f, "KB": KB, "BM": BM, "KG": KG, "GM": KB + BM - KG, "heel": heel}


def blow_forces(p):
    """風受け 2 つが息から受ける力（N）: (口の側, 丸い側)。壁より上に出た面（幅 2ρ × 壁より上の高さ）に動圧 × 抗力係数。風受けの無い形は (0, 0)。"""
    if p["vane"] != "cups":
        return 0.0, 0.0
    area = 2 * cup_radius(p) * max(0.0, p["cup_height"] - p["wall_height"]) * 1e-6  # m²
    q = 0.5 * AIR_DENSITY * BREATH_V ** 2  # 動圧（Pa）
    return q * area * CD_CUP_OPEN, q * area * CD_CUP_BACK


def blow_arm(p, hy=None):
    """息が舟を傾ける腕（mm）＝ 傾ける力のモーメント ÷ 舟の重さ。風受け 2 つの力の和 ×（壁より上の風受けの面の真ん中の高さ − 喫水の半分）
    ÷ (m·g)。風受けの無い形は 0。hy は hydro(p) の結果を持っている時に渡す（人形の外形を作り直すのを省くだけ。値は同じ）。"""
    fo, fb = blow_forces(p)
    if fo + fb == 0:
        return 0.0
    hy = hy or hydro(p)
    lever = (p["wall_height"] + p["cup_height"]) / 2 - hy["d"] / 2  # mm
    return (fo + fb) * lever / (hy["m"] / 1000 * GRAVITY)  # N·mm ÷ N


def rim_angle(p, hy):
    """幅の向きに傾けて、低い側のふちが水に着く角（°）。底の高い側の角が水から出た後は、舟が浮き上がりながら傾くので、
    喫水の浅い舟では atan(2·乾舷 ÷ 幅)（舟が浮き上がらないと見た控えめな値。ふちの角の検査はこちらを使う）より大きい。"""
    W, h, d = p["tray_width"], p["wall_height"], hy["d"]
    if d >= h:
        return 0.0
    if h - d <= d:  # 深く沈んだ舟は、底の角が出る前にふちが着く
        return math.degrees(math.atan(2 * (h - d) / W))
    return math.degrees(math.atan(h * h / (2 * W * d)))  # 低い側の壁の濡れた高さ √(2·W·d·tanθ) が壁の高さになる角


def righting_arm(p, hy, deg):
    """幅の向きに deg° 傾けた時に、舟を戻す腕 GZ（mm）。箱の断面（幅 W・喫水 d）で、押しのける水の断面積 W·d を保って傾ける。
    底の高い側の角が水から出るまで（tanθ ≦ 2d/W）は、壁の立った箱の式 sinθ·(GM + BM·tan²θ/2)。出た後は、低い側の角に残る三角形の
    浮心から出す: GZ ＝ (W/2 − b/3)·cosθ − (KG − s/3)·sinθ。b ＝ √(2·W·d ÷ tanθ) は底の濡れた幅、s ＝ b·tanθ は低い側の壁の濡れた高さ。"""
    W, d, KG = p["tray_width"], hy["d"], hy["KG"]
    th = math.radians(deg)
    tan = math.tan(th)
    if tan <= 2 * d / W:
        BM = W * W / (12 * d)
        return math.sin(th) * (d / 2 + BM - KG + BM * tan * tan / 2)
    b = math.sqrt(2 * W * d / tan)
    return (W / 2 - b / 3) * math.cos(th) - (KG - b * tan / 3) * math.sin(th)


def righting_max(p, hy):
    """(戻す腕の最大 mm, その時の傾き °)。0.25° 刻みで、ふちが水に着く角（rim_angle）まで探す。ふちが着いた先は水が入るので見ない。"""
    top = min(rim_angle(p, hy), 89.0)
    best, at, deg = 0.0, 0.0, 0.25
    while deg <= top:
        gz = righting_arm(p, hy, deg)
        if gz > best:
            best, at = gz, deg
        deg += 0.25
    return best, at


def check_physics(p):
    """F5.float: 浮く（乾舷）・少し傾いても水が入らない・戻る（GM）・息で倒れない（風受けつき）・部品が舟の底に収まる・糊代が壁に収まる、を見る。"""
    out = []
    L, W, h = p["tray_length"], p["tray_width"], p["wall_height"]
    hy = hydro(p)
    if hy["f"] < FREEBOARD_MIN:
        out.append(Failure("F5.float", "舟の壁", f"{hy['m']:.1f}g で {hy['d']:.1f}mm 沈み、壁 {h:g}mm の余裕が {hy['f']:.1f}mm（{FREEBOARD_MIN}mm 以上）"))
    elif hy["heel"] < MIN_HEEL:
        out.append(Failure("F5.float", "舟の壁", f"{hy['heel']:.0f}° 傾くとふちが水に着く（{MIN_HEEL}° 以上。壁を高くするか重りを減らす）"))
    elif hy["GM"] >= GM_MIN and p["vane"] == "cups" and p["cup_height"] >= h + CUP_ABOVE:
        # 息で倒れないか。乾舷・ふちの角・GM の検査が落ちた舟と、息を受けない風受けには重ねない（同じ舟に、別の直し方を 2 つ言わない）
        arm = blow_arm(p, hy)
        gz, at = righting_max(p, hy)
        if arm * BLOW_SAFETY >= gz:
            out.append(Failure("F5.float", "風受け", f"息（{BREATH_V:g}m/s の見込み）が舟を傾ける腕 {arm:.1f}mm の {BLOW_SAFETY:g} 倍が、幅の向きに舟が戻す腕の最大 {gz:.1f}mm（{at:.0f}° 傾いた時）に届き、倒れるかふちから水が入る（風受けを低くするか、舟の幅を広くする）"))
    if hy["GM"] < GM_MIN:
        out.append(Failure("F5.float", "重心", f"GM が {hy['GM']:.1f}mm で、傾いて戻らない（{GM_MIN}mm 以上。KB {hy['KB']:.1f} + BM {hy['BM']:.1f} − KG {hy['KG']:.1f}）"))
    if p["glue"] > h - 2:
        out.append(Failure("F5.float", "舟の糊代", f"糊代 {p['glue']:g}mm が壁 {h:g}mm より広く、角が閉じない"))
    r = p["leaf_radius"]
    if 2 * r > min(L, W) - 2:
        out.append(Failure("F5.float", "葉", f"葉の直径 {2 * r:g}mm が舟の底に入らない"))
    if not foot_footprint(p).within(Polygon(_circle(0, 0, r))):
        out.append(Failure("F5.float", "人形", f"人形の足の糊代（幅 {foot_width(p):.0f}mm・奥行き {TAB}mm）が葉からはみ出す"))
    t = clay_thickness(p)
    if t > CLAY_T_MAX:
        out.append(Failure("F5.float", "重り", f"粘土 {p['ballast_g']:g}g は四隅の {p['clay_side']:g}mm の四角で厚さ {t:.1f}mm になり、崩れて片寄る（{CLAY_T_MAX}mm まで。四角を広げるか減らす）"))
    fm = floor_marks(p)
    floor = box(0, 0, L, W)
    if p["vane"] == "cups":
        rho = cup_radius(p)
        if any(not floor.contains(c) or c.intersects(fm["leaf"]) for c in fm["cups"]):
            out.append(Failure("F5.float", "風受け", f"半径 {rho:.1f}mm の風受け 2 つ（外へ折る歯 {CUP_TAB}mm を含む）が葉の両側の底（端から {CUP_INSET}mm 内）に入らない"))
    # 粘土の四角は、葉と風受けの足跡に重ねない（重ねると葉が浮くか、風受けが立たない）
    others = [fm["leaf"]] + fm["cups"]
    if any(sq.intersects(o) for sq in fm["ballast"] for o in others):
        out.append(Failure("F5.float", "粘土の印", "四隅の粘土の四角が、葉か風受けの置き場に重なる"))
    # 葉の向きの刻みが刷れないと、葉の向き（＝人形の向き）が決まらない。風受けつきで葉を 90° 回すと、人形が風受けに 12mm ほど入る
    if notch_length(p) < NOTCH_MIN:
        out.append(Failure("F5.float", "葉の向きの刻み", f"丸い葉の印の右に、向きの刻みを {NOTCH_MIN:g}mm 刷る所が無い（{max(notch_length(p), 0):.1f}mm。葉を小さくするか舟を長くする）"))
    # 人形は底の幅の向きに立つ。壁の上端より下の外形は壁の内に（風受けとの当たりは、風受けを葉の外に置くので起きない。docstring）
    e = figure_half_width(p, h)
    if e > W / 2 - WALL_GAP:
        out.append(Failure("F5.float", "人形", f"壁の上端より下の人形の半幅 {e:.1f}mm が、底の半幅 {W / 2 - WALL_GAP:.1f}mm に入らず、壁に当たる"))
    sq = fm["ballast"]
    if any(not floor.contains(q) for q in sq) or any(a.intersection(b).area > 1e-9 for i, a in enumerate(sq) for b in sq[i + 1:]):
        out.append(Failure("F5.float", "粘土の印", "四隅の粘土の四角が、互いに重なるか底から出る（四角を小さくする）"))
    if p["vane"] == "cups" and p["cup_height"] < h + CUP_ABOVE:
        out.append(Failure("F5.float", "風受け", f"風受けが壁の上に {p['cup_height'] - h:g}mm しか出ず、息を受けない（{CUP_ABOVE}mm 以上）"))
    return out


def _flow(items, x0, y0, x1, gap):
    """部品を x0 から右へ並べ、x1 に入らなければ次の行の x0 へ送る。並べた物の下端の y を返す。"""
    x, y, row_h = x0, y0, 0
    for q in items:
        if x > x0 and x + q.width > x1:
            x, y, row_h = x0, y + row_h + gap, 0
        q.x, q.y = x, y
        x += q.width + gap
        row_h = max(row_h, q.height)
    return y + row_h


def place(by_key, page, top, gap):
    """1 段目の左に舟、その右の帯に葉と風受け 2 つを並べる（帯に入らなければ次の行へ、帯に入らない物は舟の下へ）。
    2 段目は、1 段目に置いた物の一番下の次の行で、左に人形、その右から説明の列。
    理由: 葉を必ず舟の右、風受けを葉の下に置くと、広い舟で葉が印字域を出て、高い風受けが説明の文に重なった。"""
    tray, leaf, fig = by_key["tray"], by_key["leaf"], by_key["figure"]
    tray.x, tray.y = page.x0, top
    items = [leaf] + [by_key[k] for k in ("cupa", "cupb") if k in by_key]
    side_x = tray.x + tray.width + gap
    n = 0  # 舟の右の帯に（1 つずつなら）入る物の数。入らない物から先は舟の下へ
    while n < len(items) and side_x + items[n].width <= page.x1:
        n += 1
    bottom = tray.y + tray.height
    if n:
        bottom = max(bottom, _flow(items[:n], side_x, top, page.x1, gap))
    if n < len(items):
        bottom = _flow(items[n:], page.x0, bottom + gap, page.x1, gap)
    y = bottom + gap
    fig.x, fig.y = page.x0, y
    x = page.x0 + fig.width + gap
    return y, page.x1 - x, x


def bom(p):
    paper = paper_name(gsm=p['paper_gsm'])
    why = "家庭のプリンタで刷って作るため"
    rows = [
        {"number": 1, "key": "tray", "name": "舟", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明（図では葉が直に浮く。木か葉の浮きと推定）", "reason": "紙で浮きを作るため、箱にして水をはじく"},
        {"number": 2, "key": "leaf", "name": "葉", "qty": 1, "material": paper, "substituted": True, "original_guess": "蓮の葉か葉の形の木（図の葉脈からの推定）", "reason": why},
        {"number": 3, "key": "figure", "name": "人形", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明（紙か木の人形と推定）", "reason": why},
        {"number": 7, "key": "tape", "name": "水よけ", "qty": 1, "material": f"透明の梱包テープ（{p['tape_gsm']:g}g/m² の見込み）で舟の外側の底と壁を覆う", "substituted": True, "original_guess": "なし（紙の舟は昔の物に無い翻案）", "reason": "紙は濡れると水を吸って弱るため"},
    ]
    if p["ballast_g"] > 0:
        rows.append({"number": 8, "key": "ballast", "name": "重り", "qty": 1, "material": f"油粘土 {p['ballast_g']:g}g", "substituted": True, "original_guess": "不明", "reason": "重心を下げて倒れにくくし、量を変えて試しやすいため"})
    if p["vane"] == "cups":
        rows.insert(3, {"number": 4, "key": "cupa", "name": "風受け（右）", "qty": 1, "material": paper, "substituted": True, "original_guess": "なし（回すための翻案）", "reason": "息で回すため"})
        rows.insert(4, {"number": 5, "key": "cupb", "name": "風受け（左）", "qty": 1, "material": paper, "substituted": True, "original_guess": "なし（同じ）", "reason": "息で回すため"})
    return rows


def materials(p):
    # 行の位置でなく key で引く。形によって部品表の行が増えるので、位置で引くと別の行を刷る。
    by = {r["key"]: r for r in bom(p)}
    clay = [by["ballast"]["material"]] if "ballast" in by else []
    return [f"{by['tray']['material']}を 1 枚", "のり、はさみ、定規", by["tape"]["material"], *clay, "水を張った洗面器か深い皿"]


def _steps(p):
    """(組み方の文, その手順の困り事が当たる直しの行き先) の並び。文と行き先を 1 つの並びで持つのは、手順を直した時に、
    作った人の報告の手順の番号（Issue #21 の報告の problems[].step）が別の寸法を指さないようにするため。
    手順の数は形（vane）だけで決まる。重りを使わない寸法でも、重りの手順は「使わない」と言う文で残す（番号をずらさない）。
    行き先は params（RANGES の寸法の名）・consts（この雛形の見込みの値の名）・floors（F5.float の所の名）。3 つとも空なら組み方の文だけ。
    文は STEP_LINES_MAX 行に収める（前はサイトの手順の紙に収めるため。今は組み立ての頁で読みやすくするため。docstring）。"""
    def to(params=(), consts=(), floors=()):
        return {"params": list(params), "consts": list(consts), "floors": list(floors)}
    cups = p["vane"] == "cups"
    out = [("水を使う時は大人と一緒に・紙は濡れると弱る", to()), ("水は床に敷いた新聞紙の上で使い、こぼした水はすぐ拭く", to()),
           ("刷った物差しに定規を当て、10cm か確かめる", to()),
           ("部品を実線で切る。舟の角の糊代の脇も切り込む", to(("glue", "figure_height"), ("FRINGE_PITCH", "FRINGE_GAP") if cups else ())),
           # 「短い壁」とは言わない。幅が長さより長い舟では、糊代の無い壁の方が長い
           ("1 舟を谷折りで箱にする。角の糊代は斜線に糊を塗り、となりの壁の外側に貼る", to(("glue", "wall_height"), (), ("舟の糊代",))),
           (f"舟の外側の底と壁を透明テープですき間なく覆い、ふちは内へ {TAPE_FOLD}mm 折り返す", to(("tape_gsm",), ("TAPE_FOLD",), ("舟の壁",))),
           ("2 葉を舟の底の丸い葉の印に合わせ、茶の矢印の先を印の右の刻みに向けて貼る", to(("leaf_radius", "tray_length"), ("NOTCH_MIN",), ("葉", "葉の向きの刻み"))),
           ("3 人形の足の糊代を山折りし、折り目を葉の茶の足の印に合わせ、糊代の斜線を葉に当てて矢印の向きへ寝かせて貼る（絵は矢印と逆を向く）",
            to(("figure_height", "leaf_radius", "tray_width"), ("TAB", "WALL_GAP"), ("人形",)))]
    if cups:
        out.append(("4・5 風受けの歯の間の切り込みを山折りの線まで切る。刷った面を内にして半円に丸め、歯を外へ山折りし、斜線を底に当てて風受けの印に沿わせて貼る",
                    to(("cup_width", "cup_height", "tray_length", "leaf_radius"), ("CUP_TAB", "CUP_INSET", "FRINGE_PITCH", "FRINGE_GAP"), ("風受け",))))
    clay = to(("ballast_g", "clay_side"), ("CLAY_DENSITY", "CLAY_T_MAX", "CLAY_INSET"), ("重り", "粘土の印"))
    if p["ballast_g"] > 0:
        out.append((f"油粘土 {p['ballast_g']:g}g を 4 等分し、底の四隅の印に平たく押し付ける（片寄ると傾く）", clay))
    else:
        out.append(("この型紙は重りを使わない（油粘土は載せない）", clay))
    out.append(("水に浮かべ、傾きと沈み方を見る（内側はテープが無く、水が入ると色がにじむ）",
                to(("paper_gsm", "tape_gsm", "wall_height", "tray_length", "tray_width", "ballast_g", "figure_height"), ("FREEBOARD_MIN", "MIN_HEEL", "GM_MIN"), ("舟の壁", "重心"))))
    if cups:
        out.append(("横から風受けに息を吹き、回るか見る",
                    to(("cup_width", "cup_height", "wall_height", "tray_width"), ("BREATH_V", "CD_CUP_OPEN", "CD_CUP_BACK", "BLOW_SAFETY", "CUP_ABOVE"), ("風受け",))))
    else:
        # 風受けの無い形にも、動かす手順を 1 つ持たせる。コマ 28 の鉢の水には渦の線があり、渦に乗って回る玩具とも読める（【解釈】）。
        # 前は浮かべて見るだけで、動きを試す手順が無かった。水の流れと舟の回り方は式にしていない
        out.append((f"舟を出し、水を指で同じ向きに {STIR_TURNS} 回かき回して渦を作り、舟を浮かべて回るか見る",
                    to(("tray_length", "tray_width", "wall_height"), ("STIR_TURNS", "FREEBOARD_MIN"), ("舟の壁",))))
    out.append(("終わったら舟を水から出し、布で拭いて広げて乾かす。使った水を捨てる", to()))
    return out


def steps(p):
    return [text for text, _ in _steps(p)]


def step_targets(p):
    """手順の番号（1 から）ごとの、直しの行き先。作った人の報告の困り事（手順の番号つき）を、当たる寸法・見込みの値・検査の所へ引くための表。
    値は直さない。直しは人が採る。報告の集計の側からは、まだ呼んでいない。"""
    return {i: target for i, (_, target) in enumerate(_steps(p), 1)}


RESULTS = ("浮いた", "沈んだ")


def measures(p):
    """浮くかの二択でなく、浮き方と動き方を言葉か絵で予想する（ほかの雛形と同じ形）。「試した事」の欄は 1 行で、数でなく言葉で書く。
    前のサイトの手順の紙は測る欄（角度・回数・物差し）を外していて、既定の舟の喫水 1.3mm は定規で読めない。欄を 2 行にすると紙からはみ出した
    （手順の紙は廃止。欄はサイトの組み立ての頁の物）。
    書いた言葉は、作った人の報告の動きの感想（motion_notes）にそのまま写せる。"""
    if p["vane"] == "cups":
        return {"predict": "水に浮かべて横から息を吹くと、舟と人形はどうなると思いますか（言葉か絵で）", "rows": [[("沈み方と傾き・水が入ったか・息での回り方", 110)]]}
    return {"predict": "水に浮かべて水をかき回すと、舟と人形はどうなると思いますか（言葉か絵で）", "rows": [[("沈み方と傾き・水が入ったか・渦での回り方", 110)]]}


def diagram(x, y, w, h, p):
    """浮かべた舟を横から見た絵。水の線を喫水の高さに引く。寸法の図ではなく、舟・葉・人形・水の並びを見せるだけ。"""
    L, H, fh = p["tray_length"], p["wall_height"], p["figure_height"]
    s = min(w / (L + 10), h / (H + fh + 8))
    bx, base = x + 5 * s, y + h - 4 * s
    shapes = [{"kind": "rect", "x": bx, "y": base - H * s, "w": L * s, "h": H * s}]
    d = min(hydro(p)["d"], H)
    shapes.append({"kind": "line", "x1": x, "y1": base - d * s, "x2": x + w, "y2": base - d * s, "dash": "1,0.6"})
    cx = bx + L * s / 2
    fw = foot_width(p) * s
    shapes.append({"kind": "rect", "x": cx - fw / 2, "y": base - fh * s, "w": fw, "h": fh * s})
    if p["vane"] == "cups":
        for side in (-1, 1):
            shapes.append({"kind": "rect", "x": cx + side * (L / 2 - 2) * s - (side > 0) * 2 * s, "y": base - p["cup_height"] * s, "w": 2 * s, "h": p["cup_height"] * s})
    return shapes
