"""虎の次の組 tora-v6 の作り（型紙エンジン paper-to-toy の main e7cf5f7 の雛形 pivot_counterweight の写し。#115）。

名前が `_` で始まるので、雛形としては読まれない。pivot_counterweight が、刷る組が tora-v6 より後の時だけ、この関数に渡す
（set_no）。前の組（tora-v3・tora-v4）の作りは pivot_counterweight に残し、1 バイトも変えない（凍結の床）。

なぜ別の 1 本か: エンジンは v4 の後に、写真と照らした直し（#119）・立体の脚と角を落とした胴・端の壁の糊代の根元・両面の頭（#129）を
入れ、胴の網と絵をほぼ全部描き直した。前の組の作りに 1 行ずつ「組で分ける」を足すと、v4 の紙に直しが漏れても見つけにくい。
エンジンの雛形をそのまま写して、組の境で関数ごと替えれば、漏れる所が無い（雛形の正はエンジン）。

エンジンと違う所は 2 つだけ（次にエンジンから写し直す時に、この 2 つを残す）:
- 手順 4 の「破線で山折り」を「線のとおり山折り」にする。山折りの線は凡例では一点鎖線で、「破線で山折り」だと字と線が合わない
  （窓口が本人の委任 2026-11-06 でカード 002247 の推しを選んだ字。tora-v4 から同じ）
- 紙の行を、本人が確かめた 4 つの名前（_paper.paper_name。#295）にする（統括の指示「虎の紙の行の 4 つの字は次の組の写しの時に」）

以下はエンジンの雛形の注のまま:
頭の支え方の読みを描き分ける。玩具の型紙は 1 枚で、neck（首を胴の穴に入れる・元の repo の H-A）がたたき台、hang は試行錯誤のヒント
（制作者の決定 2026-11-05「玩具 1 つに型紙 1 枚」「虎のたたき台は H-A」・omochae.sheets）。寸法は手元の複写の図の比から出した。
どの値も実物では未確認。Claude が変えてよいのは RANGES の名前の値だけ。
"""
import math

from ..model import Failure, Part
from ..textfit import text_width
from ..pivot_model import center, paper_mass, period_s, rest_tilt_deg
from ._paper import paper_name

ID = "pivot_counterweight"
DEFAULTS = {
    "mount": "neck",
    "body_length": 64, "body_width": 28, "body_height": 54, "glue": 8,
    "ear_length": 12, "ear_height": 8, "axle_height": 42,
    "opening": 18, "neck_length": 14, "strip_width": 10,
    "head_w": 26, "head_h": 24,
    "weight_g": 3.0, "weight_below_axle": 28, "weight_behind": 1,
    # 立体の脚の高さと、胴の上の角を落とす幅（制作者の追加の指示 2026-11-06「虎の足と胴体を立体的にして、さらにリアリティを追求する」）。
    # 既定は 0（脚なし・箱）。凍結の場面は既定の寸法で動くので、次の組の見本（examples/tora_v5.json）だけが使う
    "leg_height": 0, "body_round": 0,
    # 頭の顔の数（制作者の指示 2026-11-06「顔は、両側に貼れるように首から立体的にするか、両側から見た物を用意して。」の後の方）。
    # 2 は、今の顔と、頭の上で折り返した鏡写しの顔を 1 つの部品にする（_head_part）。既定は 1（今の頭）で、凍結の場面の紙は変えない。
    # 次の組の見本（examples/tora_v6.json）だけが 2 を使う
    "head_sides": 1,
    # 紙の面密度は見込み。実物の紙を量ったら置き換える。
    "paper_gsm": 150,
}
RANGES = {
    "body_length": (40, 90), "body_width": (20, 40), "body_height": (30, 70), "glue": (5, 12),
    "ear_length": (6, 25), "ear_height": (5, 15), "axle_height": (15, 65),
    "opening": (10, 30), "neck_length": (5, 30), "strip_width": (5, 20),
    "head_w": (15, 45), "head_h": (15, 45),
    "weight_g": (0.2, 15), "weight_below_axle": (-20, 60), "weight_behind": (-10, 40),
    "leg_height": (0, 15), "body_round": (0, 10),
    "head_sides": (1, 2),
    "paper_gsm": (40, 400),
}
MOUNTS = ("neck", "hang")
# 刷る形を決める寸法（頭の支え方）。仮説の違いそのものなので、寸法を直に渡す入口（python -m omochae --params）では既定に頼らず必ず書かせる。
FORM = "mount"
FORMS = MOUNTS  # 刷る形の値の一覧（作りうる部品を数える時に使う）
# 既定の出典（data/sources/ の名前）。--source を書かない時に、雛形と合わない出典の印を刷らないため。
SOURCE = "NDL-1187053-R0000014-R"
HOLE_MARGIN = 4  # 穴から紙の端までの見込み。これより狭いと裂けやすい
NECK_BACK = 6  # 首の形で、軸を前の壁の後ろに通す距離。部品の穴と揺れの検査が同じ値を使う
# 吊る形の帯: 帯の上の端から穴まで STRIP_HOLE、頭の上の端と帯の下の端を HEAD_OVERLAP 重ねて貼る。
# 帯の長さ＝STRIP_HOLE＋軸から頭の上の端まで＋HEAD_OVERLAP。式（axle_to_head_top）と刷る帯・組み方の文が同じ数を指すように名前を付けた。
STRIP_HOLE = 6
HEAD_OVERLAP = 4
MIN_SWING = 10
MAX_TILT = 15
# 色は実物の張子の虎の写真（制作者が送った 2026-11-06。制作者の決定「実物の写真と照らした直しは、全部入れる」）に寄せた:
# 明るい黄の地・紺の縞・白い下と脚・赤の差し色（首の穴の縁・頭の斑・口）。前はくすんだ黄土と焦げ茶で、元の図の色の見込みだった
TIGER, STRIPE, RIM, MOUTH, EYE = "#f2c230", "#1f2d5c", "#cc3326", "#cc3326", "#fbf8ee"
WHITE, INK = "#fbf8ee", "#1d1d1d"
RIM_W = 1.5  # 首の穴の赤い縁の幅 mm（穴の切り口から外へ）
# 胴の絵の割合（写真の目測。斜めから撮ってあるので 1〜2 割はずれる）: 下の白い帯の高さと、脚の上の端の高さは胴の高さの割合、
# 脚の幅は胴の長さの割合、脚は前と後ろの端からこの割合だけ内に置く
FOOT_BAND, LEG_TOP, LEG_W, LEG_IN = 0.22, 0.36, 0.16, 0.07
STRIPE_STEP = 8  # 縞の間 mm
# 尾（4）: 幅・長さと、根元の糊代の長さ。尾は胴の上の面の後ろの端に糊代を貼って立て、上へ反らせる（実物の写真の直し E。前は後ろの壁に貼った）
TAIL_W, TAIL_LEN, TAIL_TAB = 8, 56, 8
TAIL_BACK = 3  # 尾の糊代を貼る四角の、上の面の後ろの端からの間 mm
# 立体の脚（leg_height > 0）: 白い角筒の一辺・上の糊代の長さ・横の糊代の幅 mm（描いた脚の LEG_IN は胴の長さの割合で、別の物）。
# 一辺は、胴の幅の下限（20mm）でも底に 2 本が並ぶ太さ（2·(7＋2)＋2 = 20）
# 上の 2 つの糊代は、角筒の内へ山折りして（刷った面＝斜線が上を向く）胴の底に貼る。外へ谷折りすると、刷った面が下を向いて貼れない
# （3D で折って見つけた）。2 つの糊代は向かい合う面から内へ折るので、重ならない長さ（2·LEG_TAB ≦ LEG_SIDE）にする
LEG_SIDE, LEG_TAB, LEG_GLUE = 7, 3, 5
# 脚を貼る四角（位置の印）は脚の上の面（一辺 LEG_SIDE）。胴の底の端から LEG_INSET 内に置く（胴の長さと幅の範囲の下限 40・20mm でも
# 2 本ずつ並ぶ）。糊代は角筒の内に入るので、四角の外へは出ない
LEG_INSET = 2
LEG_MIN = 5  # 脚の高さの下限 mm。これより低いと、角筒の横の糊代と指の線が脚の面に収まらない
TITLES = {"neck": "首を胴の穴に入れる", "hang": "頭を前に吊る"}


def title(p):
    return TITLES[p["mount"]]


def spec():
    return {"template_id": ID, "defaults": DEFAULTS, "ranges": RANGES, "mount": MOUNTS}


def check_range(p):
    out = []
    for k, v in p.items():
        if k == "mount":
            if v not in MOUNTS:
                out.append(Failure("F5.range", k, f"{v} は {MOUNTS} のどれでもない"))
        elif k not in RANGES:
            out.append(Failure("F5.range", k, "知らない寸法の名前"))
        elif not isinstance(v, (int, float)) or isinstance(v, bool) or not RANGES[k][0] <= v <= RANGES[k][1]:
            out.append(Failure("F5.range", k, f"{v} は範囲 {RANGES[k]} の外"))
        elif k == "head_sides" and not float(v).is_integer():
            # 範囲 (1, 2) の間の 1.5 などは、刷る頭の形が無い（顔は 1 つか 2 つ）
            out.append(Failure("F5.range", k, f"{v} は 1 か 2 でない（顔の数は整数）"))
    return out


def mass_points(p):
    """揺れる部分の質量の点。紙の頭は重りより桁で軽い。両面の頭（head_sides 2）は紙が 2 枚なので、頭の紙の重さも 2 倍にする
    （頭の上の尖りを外した分は小さいので引かない。頭の紙は外形の箱で見込む）。"""
    head_m = paper_mass(p["head_w"] * p["head_h"], p["paper_gsm"]) * p["head_sides"]
    if p["mount"] == "neck":
        head = (head_m, p["neck_length"] + 6, 0)
        strip = (paper_mass(2 * p["strip_width"] * (p["neck_length"] + 12), p["paper_gsm"]), p["neck_length"] / 2, 0)
    else:
        arm = axle_to_head_top(p)
        head = (head_m, 0, arm + p["head_h"] / 2)
        strip = (paper_mass(2 * p["strip_width"] * arm, p["paper_gsm"]), 0, arm / 2)
    return [head, strip, (p["weight_g"], -p["weight_behind"], p["weight_below_axle"])]


def axle_to_head_top(p):
    return 8


# 5 重りの腕の下の穴（EP-0011、作成動画の札から採った案。2026-11-06）。穴は軸の穴から weight_below_axle 下（釣り合いの式の重りの位置）で、
# 粘土はこの穴の所に付けるか、穴に糸を通して玉を下げる。糸で下げた玉の重さは、糸を通した穴にかかる（糸は引く力しか伝えないので、
# 玉が穴の真下に下がっても、頭を傾ける力の腕は穴までの深さ）。なので釣り合いの式は変えず、糸の長さは玉が胴の底に当たるかだけに効く。
# 案の「穴＋糸＋玉の半径を weight_below_axle にする」は、戻る力を大きく見すぎるので採らなかった
# 揺れの周期の見込み（period_s）は、玉を穴に固めた形のまま。糸で下げた玉は腕と別に揺れるので、その組み方では周期が合わない事がある（見直しの指摘）
THREAD_R = 0.6  # 糸の穴の半径（御来迎の開く糸の穴と同じ）
CLAY_DENSITY = 1.8e-3  # 油粘土の密度 g/mm³（弥次郎兵衛と同じ見込み）
HANG_MIN = 5  # 糸で下げる時の、穴から玉の上までの長さの下限 mm。これより短いと糸を結ぶ間が無いので、下げる形を出さない
LOWER_HOLE_MIN = 1.0 + THREAD_R + 2  # 下の穴を開ける weight_below_axle の下限（軸の穴との間に紙を 2mm 残す）
# 粘土の玉の上の端から軸の中心までに残す余り（軸の穴の半径 1.0 を引くと、穴の縁まで 1mm）。玉の真ん中は軸の下 clay_r + AXLE_CLEAR 以上（見直しの指摘: 浅い重りの寸法で、
# 重い玉が軸の竹串にかかるのに検査が通っていた）。この決まりで、検査に通る寸法では下の穴がいつもある（玉の半径は 0.2g でも 3mm）
AXLE_CLEAR = 2.0


def clay_r(g):
    """粘土の玉の半径 mm。"""
    return (3 * g / (4 * math.pi * CLAY_DENSITY)) ** (1 / 3)


def hang_thread_mm(p):
    """首の形で、下の穴から粘土の玉を糸で下げる時の、穴から玉の上までの長さの上限（整数 mm。糸そのものの長さではない。
    穴に通して結ぶ分と玉に結ぶ分は別に要る）。玉の下が胴の底から 3mm 以上離れる長さ。

    下げられない（上限が HANG_MIN より短い・下の穴が無い・吊る形）時は None。既定の寸法（重り 3g・穴は軸の 28mm 下・軸の高さ 42mm）では、
    直径約 15mm の玉が底に当たるので None になる。
    """
    if p["mount"] != "neck" or p["weight_below_axle"] < LOWER_HOLE_MIN:
        return None
    room = axle_z(p) - 3 - p["weight_below_axle"] - 2 * clay_r(p["weight_g"])
    return math.floor(room) if room >= HANG_MIN else None


def axle_z(p):
    """刷る穴の高さ（胴の底から）。吊る形では耳の穴が胴の上の縁から HOLE_MARGIN 下に決まり、axle_height は部品に効かない。"""
    return p["body_height"] - HOLE_MARGIN if p["mount"] == "hang" else p["axle_height"]


def check_physics(p):
    out = []
    H, ax = p["body_height"], axle_z(p)
    pts = mass_points(p)
    _, z, _ = center(pts)
    if z <= 0:
        out.append(Failure("F5.pivot", "重り", f"重心が軸より {-z:.1f}mm 上にあり、揺れて戻らない"))
    tilt = rest_tilt_deg(pts)
    if z > 0 and abs(tilt) > MAX_TILT:
        out.append(Failure("F5.pivot", "重り", f"静かな時に {tilt:.0f}° 傾く（{MAX_TILT}° まで）"))
    if H - ax < HOLE_MARGIN and p["mount"] == "neck":
        out.append(Failure("F5.pivot", "軸の穴", f"軸の穴から胴の上の縁まで {H - ax}mm で、裂けやすい"))
    if p["mount"] == "hang":
        # 式と刷る物を同じにする。吊る形の軸は耳の穴で決まるので、axle_height が違えば式が別の物を計算している。
        if abs(p["axle_height"] - ax) > 0.5:
            out.append(Failure("F5.pivot", "軸の高さ", f"axle_height {p['axle_height']} が、刷る耳の穴の高さ（胴の高さ−{HOLE_MARGIN}＝{ax}）と違う"))
        # 重りは頭の裏に貼る（組み方の文）。両面の頭は裏どうしを貼り合わせるので、粘土を貼る裏が無い
        if p["head_sides"] == 2:
            out.append(Failure("F5.pivot", "頭", "吊る形は頭の裏に粘土を貼るので、頭を両面（head_sides 2）にできない"))
        # 重りは頭の裏に貼る（組み方の文）。式の位置が頭の外なら、その文では作れない。
        arm = axle_to_head_top(p)
        if not arm <= p["weight_below_axle"] <= arm + p["head_h"]:
            out.append(Failure("F5.pivot", "重り", f"軸の下 {p['weight_below_axle']}mm は頭（軸の下 {arm}〜{arm + p['head_h']}mm）の外で、頭の裏に貼れない"))
        if p["ear_length"] < 2 * HOLE_MARGIN:
            out.append(Failure("F5.pivot", "耳", f"耳が短く、穴の前後に {HOLE_MARGIN}mm 取れない"))
        reach = axle_to_head_top(p) + p["head_h"]
        room = p["ear_length"] - HOLE_MARGIN
        if room < reach and math.degrees(math.asin(room / reach)) < MIN_SWING:
            out.append(Failure("F5.pivot", "頭", f"頭が胴に当たるまで {MIN_SWING}° 揺れない"))
        # 吊る形は、脚がある時も、床までは胴の底で見る（脚の分を足さない。保守側）。頭の裏の粘土の玉（3g で直径 約 15mm）が、
        # 揺れや静止の傾き（MAX_TILT まで）で前の脚に当たるかは、玉の大きさ・位置・傾きで変わり、頭の紙の位置だけでは決まらない。
        # 吊る形は型紙の 1 枚でない読みなので、当たりの式は入れず、頭の下の端を胴の底から 3mm 以上離す形だけを通す
        # （玉が脚に当たらない低い頭の寸法も落とす。限りとして README に書いた）
        if H - HOLE_MARGIN - reach < 3:
            # 脚の分を足せば床に届かない寸法は、床の近さでなく「脚に当たらないかを確かめられない」と言う（物の決めつけでない文にする）
            if p["leg_height"] > 0 and H + p["leg_height"] - HOLE_MARGIN - reach >= 3:
                out.append(Failure("F5.pivot", "頭", "頭の下の端が胴の底から 3mm 未満で、前の脚に当たらないかを確かめられない（吊る形は、脚がある時も頭の下の端を胴の底から 3mm 以上離す）"))
            else:
                out.append(Failure("F5.pivot", "頭", "頭の下端が床に近すぎる"))
    else:
        # 首の帯が穴の縁に当たらずに MIN_SWING まで揺れるか。帯の面は軸に直交する（軸は帯の面の穴を貫く）ので、
        # 帯の幅は穴の中で縦に並ぶ。軸は前の壁の NECK_BACK 後ろ。θ 傾くと、壁の所で帯の中心は NECK_BACK·tanθ 動き、
        # 帯の縦の幅は sw/cosθ に広がる。前は帯の幅の 2 割しか引いておらず、穴より広い帯も通していた（穴 10・帯 20）。
        t = math.radians(MIN_SWING)
        need = NECK_BACK * math.tan(t) + p["strip_width"] / (2 * math.cos(t))
        if need > p["opening"] / 2:
            out.append(Failure("F5.pivot", "首", f"首の帯（幅 {p['strip_width']}）が穴（{p['opening']}）の縁に当たるまで {MIN_SWING}° 揺れない"))
        # 首の形の頭は前の壁より前にあり、胴の下の脚には当たらないので、脚がある時は床までが脚の高さだけ遠い
        if p["head_h"] / 2 > ax + p["leg_height"] - 3:
            out.append(Failure("F5.pivot", "頭", "頭の下端が床に近すぎる"))
    # 粘土の玉の 2 つの決まり（軸の竹串・底）は、重りの別の落ち（重心が軸より上・傾き）が無い時だけ言う。1 つの崩れに別の行が続くと
    # 狙いが読めなくなり、凍結の負の場面（neg_pivot_tilt・neg_pivot_weight_above）が 1 行で落ちる決まりも崩れた（run.sh で見つけた）
    ball_ok = not any(f.where == "重り" for f in out)
    if ball_ok and p["mount"] == "neck":
        r = clay_r(p["weight_g"])
        # 2 つは 1 つの寸法で両方起きうる（軸の高さ 15・重り 5mm 下・15g）ので、先の 1 つだけを言う（見直しの指摘）
        if p["weight_below_axle"] < r + AXLE_CLEAR:
            out.append(Failure("F5.pivot", "重り", f"粘土の玉（半径 {r:.1f}mm）が軸の竹串にかかる（玉の真ん中は軸の下 {p['weight_below_axle']}mm。{r + AXLE_CLEAR:.1f}mm 以上下に）"))
        elif p["weight_below_axle"] <= ax - 3 < p["weight_below_axle"] + r:
            # 首の形の粘土の玉は腕に付くので、静かな時（一番低い）の玉の下の端で見る（見直しの指摘: 真ん中だけ見ると、重い玉の下が底に当たっても通った）。
            # 真ん中が底に近すぎる時は、下の今の決まりが落とすので、ここでは重ねて言わない
            out.append(Failure("F5.pivot", "重り", f"粘土の玉の下が底に当たる（玉の下は軸の下 {p['weight_below_axle'] + r:.1f}mm、軸の高さ {ax}mm）"))
    if p["weight_below_axle"] > ax - 3:
        out.append(Failure("F5.pivot", "重り", f"重りが底に当たる（軸の下 {p['weight_below_axle']}mm、軸の高さ {ax}mm）"))
    if p["strip_width"] > p["body_width"] - 6:
        out.append(Failure("F5.pivot", "帯", "帯が胴の内幅に入らない"))
    # 角を落とした胴（body_round）: 吊る形は耳が角の面に来るので落とせない。首の形は、軸の穴が側面の縦の所に要る。
    # 上の面は角の分だけ細くなるので、尾を貼る四角（TAIL_W）が入る幅が要る
    if 0 < p["leg_height"] < LEG_MIN:
        out.append(Failure("F5.pivot", "脚", f"脚が低すぎて角筒に折れない（{p['leg_height']}mm。{LEG_MIN}mm 以上）"))
    c = p["body_round"]
    if c:
        d = c / math.sqrt(2)
        if p["mount"] == "hang":
            out.append(Failure("F5.pivot", "胴", "吊る形の胴は角を落とせない（耳が角の面に来る）"))
        elif ax + HOLE_MARGIN > p["body_height"] - d:
            out.append(Failure("F5.pivot", "軸の高さ", f"軸の穴が胴の角の面に来る（軸の高さ {ax}mm、側面の縦の所は {p['body_height'] - d:.1f}mm まで）"))
        if p["body_width"] - 2 * d < TAIL_W + 1.2:
            out.append(Failure("F5.pivot", "胴", f"胴の上の面（幅 {p['body_width'] - 2 * d:.1f}mm）に尾の糊代の四角（幅 {TAIL_W}mm）が入らない"))
    return out


# 絵を見て手で取った点。絵の画素は使っていない。
_HEAD = [(40, 345), (60, 300), (95, 265), (135, 245), (150, 232), (172, 250), (195, 265), (235, 320), (245, 385), (215, 415), (150, 420), (100, 445), (70, 425), (58, 390)]
_MOUTH = [(62, 385), (130, 382), (150, 405), (100, 438), (72, 422)]
_EYES = [[(72, 295), (92, 295), (96, 315), (76, 318)], [(115, 325), (140, 325), (142, 345), (118, 348)]]
_HEAD_LINES = [[(100, 275), (120, 300)], [(125, 262), (140, 285)], [(155, 285), (205, 310)], [(165, 355), (195, 380)], [(205, 350), (220, 372)]]
# 両面の頭（head_sides 2）の外形。頭の上の尖り（y 232〜250。頭の高さの約 8%）を外して、頭の上を y 250 の平らな線にし、そこを折り線にする。
# 最初の点 (172, 250) は輪郭の点、最後の点 (125, 250) は輪郭の辺 (95, 265)〜(135, 245) の上で、最後と最初を結ぶ辺が平らな頭の上。
# 顔の絵（縞・斑・目・口）は y 262 より下にあり、外す所にかからない
_HEAD_FLAT = [(172, 250), (195, 265), (235, 320), (245, 385), (215, 415), (150, 420), (100, 445), (70, 425), (58, 390), (40, 345), (60, 300), (95, 265), (125, 250)]
# 実物の頭の差し色（写真）: 赤い斑・白目の黒い瞳・口の先の白い歯。頭の絵と同じ点の座標で置く
_HEAD_SPOTS = [(185, 300, 9), (212, 348, 7)]
_PUPILS = [(85, 307), (129, 337)]
_TEETH = [[(66, 387), (77, 386), (72, 395)], [(81, 386), (92, 385), (87, 394)]]


def _scale(pts, x0, y0, sx, sy, ox, oy):
    return [(ox + (x - x0) * sx, oy + (y - y0) * sy) for x, y in pts]


LABEL_SIZE = 2.8  # 札の字の大きさ（compose.LABEL_SIZE と同じ。雛形から compose を読むと読み込みの輪になるので、値を写す）


def _strip_label(sw):
    """3 首の帯の札の字と x。帯の真ん中の谷折りの線（x = sw）が、字の「3」と「首」の間の空きを通る所に置く（作る途中の気づき 2026-11-06:
    札の字が折り線にかかっていた）。「3 首の帯」は 10.7mm で、帯の片側（既定 10mm）には入らないので、番号と名の間で折る。
    名が片側に入らない細い帯（sw が約 9mm より細い）は「3 帯」にする（「3 首の帯」は帯の枠に収まらず、配置の検査で落ちた。見直しの指摘）。
    限り: その時も、用意する物と組み方の文は「3 首の帯」と呼ぶ（番号の 3 で同じ部品と分かる）。
    """
    num, pre = text_width("3", LABEL_SIZE), text_width("3 ", LABEL_SIZE)
    x0 = sw - (num + pre) / 2
    for text in ("3 首の帯", "3 帯"):
        if x0 + text_width(text, LABEL_SIZE) <= 2 * sw - 0.3:
            return text, x0
    return "3", 1


def _circle(cx, cy, r, n=24):
    """円を近づける多角形の点（絵の poly で塗るため。絵に円の種類は無い）。"""
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def _stripe(a, b, w0, w1):
    """a から b へ細くなる縞（a の所の幅 w0、b の所の幅 w1）。実物の縞は背から下りるほど細い。"""
    (ax, ay), (bx, by) = a, b
    n = math.hypot(bx - ax, by - ay)
    nx, ny = -(by - ay) / n, (bx - ax) / n
    return {"kind": "poly", "pts": [(ax + nx * w0 / 2, ay + ny * w0 / 2), (bx + nx * w1 / 2, by + ny * w1 / 2),
                                    (bx - nx * w1 / 2, by - ny * w1 / 2), (ax - nx * w0 / 2, ay - ny * w0 / 2)], "fill": STRIPE}


def _side_art(x, y, L, H, foot_at_top, legs=True):
    """側面の絵: 黄の地に、背（上の辺）から下りる紺の縞と、下の白い帯と白い脚 2 本（実物の写真の直し C・F。前は横向きの虎 1 匹の絵で、
    実物は胴そのものが虎で、側面は縞と白い脚だった）。

    u は前の端（x。前の壁の側＝軸の穴の側）からの長さ、v は床の辺からの高さで描き、頁の座標に移す。2 枚目の側面は箱の中で上が頁の下に
    なるので、床の辺が頁の上に来る（foot_at_top）。x は裏返さない（制作者のレビューから採った案 EP-0016: 前は 180° 回していて、2 枚目の
    側面の向きが逆になっていた）。どちらの側面も、外から見て脚が下、前の脚が前の端に来る。
    立体の脚（leg_height > 0）がある時は、描いた脚を描かず、下の白い帯だけを残す（legs=False）。
    """
    def at(u, v):
        return (x + u, y + v) if foot_at_top else (x + u, y + H - v)

    def poly(pts, fill, **line):
        return {"kind": "poly", "pts": [at(u, v) for u, v in pts], "fill": fill, **line}
    m, band = 0.3, FOOT_BAND * H
    art = [poly([(m, 0), (L - m, 0), (L - m, H), (m, H)], TIGER)]
    # 縞は背から下りる。長い縞（白い帯の上まで）と短い縞（半ばまで）を交互にする（実物の縞の長さはそろっていない）。
    # 前の端から NECK_BACK＋5mm までは描かない: 首の形の軸の穴（前の端から NECK_BACK）が紺の縞に乗ると、黒い穴の丸が見えなくなる
    for i, u in enumerate(range(NECK_BACK + 5, int(L) - 5, STRIPE_STEP)):
        low = band + 2 if i % 2 == 0 else H * 0.55
        art.append(_stripe(at(u, H - 1.6), at(u + 2.5, low), 2.6, 0.6))
    art.append(poly([(m, 0), (L - m, 0), (L - m, band), (m, band)], WHITE))
    leg_w, leg_h = LEG_W * L, LEG_TOP * H
    for u0 in ((LEG_IN * L, L - LEG_IN * L - leg_w) if legs else ()):
        art.append(poly([(u0, 0.3), (u0 + leg_w, 0.3), (u0 + leg_w, leg_h), (u0, leg_h)], WHITE, stroke=STRIPE, sw=0.3))
        # 指の線（脚に見せるため）
        art += [{"kind": "line", "pts": [at(u0 + leg_w * k / 3, 0.6), at(u0 + leg_w * k / 3, 3.0)], "stroke": STRIPE, "sw": 0.3} for k in (1, 2)]
    return art


def _top_art(x, y, L, W):
    """上の面の絵: 黄の地に、幅をまたぐ紺の縞と、首の後ろの黒い斑（実物の写真）。前の端は x（前の壁の側）。
    前の端の近く（軸の竹串の線と黒い斑）と後ろの端（尾を貼る四角）には縞を描かない（印と斑が縞に紛れないように）。"""
    art = [_panel(x + 0.2, y, x + L - 0.2, y + W, TIGER)]
    art += [_stripe((x + u, y + 1.6), (x + u + 2.5, y + W - 1.6), 2.4, 1.2) for u in range(18, int(L) - TAIL_BACK - TAIL_TAB - 6, STRIPE_STEP)]
    art.append({"kind": "poly", "pts": _circle(x + NECK_BACK + 6, y + W / 2, min(3.0, W / 4)), "fill": INK})
    return art


def _bevel_art(x, y, L, C):
    """角の面（body_round）の絵: 上の面と側面の間の細い面。縞は側面の縞と同じ所から、面の幅をまたぐ。"""
    art = [_panel(x + 0.2, y, x + L - 0.2, y + C, TIGER)]
    art += [_stripe((x + u, y + 0.6), (x + u + 1.2, y + C - 0.6), 2.6, 2.4) for u in range(NECK_BACK + 5, int(L) - 5, STRIPE_STEP)]
    return art


def _leg_part(n, h):
    """立体の脚 1 本（n は部品の番号 6〜9）: 白い角筒。刷った面を外にして角筒にする（山折り）。上の 2 つの糊代を角筒の内へ折り
    （山折り）、刷った面（斜線）を上に向けて胴の底の四角に貼る。前は脚を側面に描いていた（実物の写真の直し F の繋ぎ）。"""
    a, t, gl = LEG_SIDE, LEG_TAB, LEG_GLUE
    k = min(1.0, h / 4)  # 横の糊代の角を落とす長さ。低い脚でも頂点の順が入れ替わらない（検査で落ちる低さでも、形は壊さない）
    outline = [(0, t), (0.5, 0), (a - 0.5, 0), (a, t), (2 * a, t), (2 * a + 0.5, 0), (3 * a - 0.5, 0), (3 * a, t), (4 * a, t),
               (4 * a + gl, t + k), (4 * a + gl, t + h - k), (4 * a, t + h), (0, t + h)]
    leg = Part(n, f"leg{n - 5}", "脚", outline, label_xy=(0.6, t + 0.6), label=f"{n} 脚",
               mountain=[((k * a, t), (k * a, t + h)) for k in (1, 2, 3, 4)] + [((0, t), (a, t)), ((2 * a, t), (3 * a, t))],
               glue=[[(4 * a, t), (4 * a + gl, t + k), (4 * a + gl, t + h - k), (4 * a, t + h)],
                     [(0.5, 0), (a - 0.5, 0), (a, t), (0, t)], [(2 * a + 0.5, 0), (3 * a - 0.5, 0), (3 * a, t), (2 * a, t)]])
    leg.art = [_panel(k * a + 0.2, t + 0.2, (k + 1) * a - 0.2, t + h - 0.2, WHITE) for k in range(4)]
    # 指の線（前の面の下の端）。脚の面に収まる長さだけ描く
    toe = min(2.0, h - 1.2)
    if toe > 0.3:
        leg.art += [{"kind": "line", "pts": [(a * j / 3, t + h - 0.6), (a * j / 3, t + h - 0.6 - toe)], "stroke": STRIPE, "sw": 0.3} for j in (1, 2)]
    return leg


def _wall_art(x_floor, y, H, W, up, cut=0):
    """前と後ろの壁の絵: 黄の地と、床の側の白い帯。壁は胴の底の面に x の向きでつながるので、x_floor が床の辺で、up（+1 か −1）の
    向きに高くなる。後ろの壁には、幅をまたぐ紺の縞も描く（前の壁は首の穴と赤い縁を見せるので縞を描かない）。
    cut は胴の角を落とした長さ（body_round の d）。壁の上の 2 つの角も同じだけ切った形なので、地の色も角を切る
    （絵の枠は外形から 0.2 内なので、切る長さに 0.3 足して外形の外に出さない）。"""
    def at(h, w):
        return (x_floor + up * h, y + w)
    k = cut + 0.3 if cut else 0
    shape = [at(0, 0), at(H - k, 0), at(H, k), at(H, W - k), at(H - k, W), at(0, W)] if k else [at(0, 0), at(H, 0), at(H, W), at(0, W)]
    art = [{"kind": "poly", "pts": shape, "fill": TIGER},
           {"kind": "poly", "pts": [at(0, 0), at(FOOT_BAND * H, 0), at(FOOT_BAND * H, W), at(0, W)], "fill": WHITE}]
    if up > 0:
        art += [_stripe(at(f * H, 1.6), at(f * H + 2, W - 1.6), 2.2, 0.8) for f in (0.45, 0.62, 0.79)]
    return art


def _panel(x0, y0, x1, y1, fill):
    return {"kind": "poly", "pts": [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], "fill": fill}


def _head_part(p):
    """2 頭。head_sides 2 の時は、今の顔と、頭の上で折り返した鏡写しの顔を 1 つの部品にする（両面の頭）。

    制作者の指示（2026-11-06「顔は、両側に貼れるように首から立体的にするか、両側から見た物を用意して。」）の後の方（両側から見た物）。
    今の頭は 1 枚の横顔で、3 首の帯の横の面に貼るので、反対の側からは頭の白い裏が見えた。
    - 頭の上の山折りの線で後ろの半分を後ろへ折り、3 首の帯の先を 2 枚の間に挟んで、裏どうしを貼る。山折り（刷った面の裏へ折る）なので、
      刷った面（顔）が両側の外を向く。糊は裏に付けるので糊代の斜線は刷らない（御来迎の両面の像と同じ作り）。
    - 後ろの半分は前と同じ絵の上下を返した物で、折ると反対の側からも、口が前を向いた顔が見える（左右は鏡写し）。
    - 頭の上の尖りを外して平らにし、そこを折り線にする（_HEAD_FLAT）。外すのは頭の高さの約 8% で、顔の絵より上。
    頭を首から立体にする形（指示の前の方）は作っていない。吊る形は頭の裏に粘土を貼るので、両面にしない（check_physics が落とす）。
    """
    w, h = p["head_w"], p["head_h"]
    sx, sy = w / (245 - 40), h / (445 - 232)
    scale = lambda ps: _scale(ps, 40, 232, sx, sy, 0, 0)
    two = p["head_sides"] == 2
    outline = scale(_HEAD_FLAT if two else _HEAD)
    # 両面の頭の地は、輪郭に紺の線を引かない。線は平らな頭の上（折り線）にも乗り、絵が折り線をまたぐ（F5.image_box）。外形は切る線で刷られる
    art = [{"kind": "poly", "pts": outline, "fill": TIGER} if two else {"kind": "poly", "pts": outline, "fill": TIGER, "stroke": STRIPE, "sw": 0.2}]
    # 実物の頭（写真）: 赤い斑・紺の縞・黒い大きな口の線で口の中は赤・口の先に白い歯・白目に黒い瞳
    art += [{"kind": "poly", "pts": scale(_circle(cx, cy, r)), "fill": RIM} for cx, cy, r in _HEAD_SPOTS]
    art += [{"kind": "line", "pts": scale(line), "stroke": STRIPE, "sw": 0.45} for line in _HEAD_LINES]
    art.append({"kind": "poly", "pts": scale(_MOUTH), "fill": MOUTH, "stroke": INK, "sw": 0.35})
    art += [{"kind": "poly", "pts": scale(t), "fill": WHITE} for t in _TEETH]
    art += [{"kind": "poly", "pts": scale(e), "fill": EYE, "stroke": INK, "sw": 0.2} for e in _EYES]
    art += [{"kind": "poly", "pts": scale(_circle(cx, cy, 4.5)), "fill": INK} for cx, cy in _PUPILS]
    # 2〜5 番にも部品の名を刷る（EP-0016: 1 番だけ名があり、ほかは番号だけだった）
    if not two:
        return Part(2, "head", "頭", outline, label_xy=(w * 0.5, h * 0.6), label="2 頭", art=art)
    yf = outline[0][1]
    assert abs(outline[-1][1] - yf) < 1e-9  # 頭の上の平らな辺は水平（_HEAD_FLAT の点を変えた時に見落とさないため）
    mirror = lambda q: (q[0], 2 * yf - q[1])
    back = [mirror(q) for q in reversed(outline[1:-1])]  # 前の輪郭を逆にたどった鏡写し。折り線の両端は前と同じ点なので入れない
    dy = h - 2 * yf  # 後ろの半分の上の端（鏡写しのあご）を 0 にする
    shift = lambda q: (q[0], q[1] + dy)
    art_back = [{**item, "pts": [mirror(q) for q in item["pts"]]} for item in art]
    # 札は前の半分の、今の頭と同じ所（後ろの半分には刷らない）
    return Part(2, "head", "頭", [shift(q) for q in outline + back], label_xy=(w * 0.5, h * 0.6 + dy), label="2 頭",
                mountain=[(shift(outline[-1]), shift(outline[0]))],
                art=[{**item, "pts": [shift(q) for q in item["pts"]]} for item in art + art_back])


def parts(p):
    L, W, H, g = p["body_length"], p["body_width"], p["body_height"], p["glue"]
    e, eh = p["ear_length"], p["ear_height"]
    hang = p["mount"] == "hang"
    # 胴の上の 2 つの角を、幅 c の面で 45° に落とす（制作者の追加の指示「胴体を立体的に」。c = body_round）。d は角の面の横と縦の長さ
    # （c·cos45°）。上の面は 2d 細く、側面の縦の所は d 低くなり、壁も上の 2 つの角を d 切る。帯は上・角の面・側面・底・側面・角の面の順。
    # c = 0 の時は d も 0（int）にし、前と同じ数と並びにする（既定の寸法で刷る凍結の場面の紙を、1 バイトも変えない）
    c = p["body_round"]
    d = c / math.sqrt(2) if c else 0
    Wt, Hs = W - 2 * d, H - d
    top0, top1 = g, g + Wt
    ch1 = top1 + c
    b0 = ch1 + Hs
    b1 = b0 + W
    ch2 = b1 + Hs
    bottom = ch2 + c
    far = H + L + H
    if d:
        back_wall = [(far - d - 2, b0 - g), (far - d, b0), (far, b0 + d), (far, b1 - d), (far - d, b1), (far - d - 2, b1 + g)]
        front_wall = [(d + 2, b1 + g), (d, b1), (0, b1 - d), (0, b0 + d), (d, b0), (d + 2, b0 - g)]
    else:
        back_wall = [(far - 2, b0 - g), (far, b0), (far, b1), (far - 2, b1 + g)]
        front_wall = [(2, b1 + g), (0, b1), (0, b0), (2, b0 - g)]
    # 端の壁の上下の糊代 4 枚は、根元の角も外の端と同じく 2mm 落とす（制作者の決定 2026-11-06）。落とさないと、糊代の横の縁が隣の側面と
    # 糊代の幅だけつながったまま（切る線も折り線も無い縁）で、切り込まないと壁を立てて箱に折れなかった（3D で折ると、糊代と側面が 1 枚の
    # 面になって折れない）。斜めに落とすと、糊代と側面は 1 点でしか触れず、外形をはさみで切るだけで離れる
    pts = [(H + 2, 0), (H + L - 2, 0), (H + L, g), (H + L, b0), (H + L + 2, b0 - g)] + back_wall + [(H + L + 2, b1 + g), (H + L, b1), (H + L, bottom), (H, bottom)]
    if hang:
        pts += [(H - e, bottom), (H - e, bottom - eh), (H, bottom - eh)]
    pts += [(H, b1), (H - 2, b1 + g)] + front_wall + [(H - 2, b0 - g), (H, b0)]
    if hang:
        pts += [(H, top1 + eh), (H - e, top1 + eh), (H - e, top1), (H, top1)]
    pts += [(H, g)]
    # 札「1 胴」は、後ろの壁の床の側の白い帯に置く（制作者の決定 2026-11-06「札を縞の上から外す」）。上の面は縞・首の後ろの黒い斑・
    # 軸の竹串の点の線があり、細い上の面（角を落とした胴）では札がどれかにかかる。後ろの壁の白い帯には、縞も印も無い
    body = Part(1, "body", "胴", pts, label_xy=(H + L + 0.8, b0 + W / 2 - 1.4), label="1 胴")
    # 胴は色の面（虎の地・縞・横の絵）を外にして箱にするので、刷った面から見て山折り。谷折り（凡例の、刷った面がへこむ向き）のままだと
    # 色の面が箱の内に入った。御来迎の外筒への制作者の答え（2026-11-06「色がついている所が外を向くよう折った」）と同じ線で直した（次の版）。
    # 胴の線は破線で刷るので、刷る線の形が山折りの形に変わる
    body.mountain = [((H, top0), (H + L, top0)), ((H, top1), (H + L, top1))] + ([((H, ch1), (H + L, ch1))] if c else [])
    body.mountain += [((H, b0), (H + L, b0)), ((H, b1), (H + L, b1))] + ([((H, ch2), (H + L, ch2))] if c else [])
    body.mountain += [((H, b0), (H, b1)), ((H + L, b0), (H + L, b1)),
                      ((d, b0), (H, b0)), ((d, b1), (H, b1)), ((H + L, b0), (far - d, b0)), ((H + L, b1), (far - d, b1))]
    body.glue = [[(H + 2, 0), (H + L - 2, 0), (H + L, g), (H, g)], [(d + 2, b0 - g), (H - 2, b0 - g), (H, b0), (d, b0)], [(d, b1), (H, b1), (H - 2, b1 + g), (d + 2, b1 + g)],
                 [(H + L + 2, b0 - g), (far - d - 2, b0 - g), (far - d, b0), (H + L, b0)], [(H + L, b1), (far - d, b1), (far - d - 2, b1 + g), (H + L + 2, b1 + g)]]
    legs = p["leg_height"] > 0
    # 胴の絵（実物の写真の直し B・C・F）: 上の面は縞と黒い斑、側面は縞と白い帯と脚、前と後ろの壁は白い帯、底の面は白（実物は下が白い）。
    # 角の面にも縞を続ける。立体の脚がある時は、側面に脚を描かない
    body.art = _top_art(H, top0 + 0.2, L, Wt - 0.4)
    if c:
        body.art += _bevel_art(H, top1 + 0.2, L, c - 0.4) + _bevel_art(H, ch2 + 0.2, L, c - 0.4)
    body.art += [_panel(H + 0.2, b0 + 0.2, H + L - 0.2, b1 - 0.2, WHITE)]
    body.art += _wall_art(H - 0.2, b0 + 0.2, H - 0.4, W - 0.4, -1, d) + _wall_art(H + L + 0.2, b0 + 0.2, H - 0.4, W - 0.4, +1, d)
    body.art += _side_art(H, ch1 + 0.2, L, Hs - 0.4, False, not legs) + _side_art(H, b1 + 0.2, L, Hs - 0.4, True, not legs)
    if legs:
        # 脚を貼る四角（位置の印）: 胴の底の面（x が H〜H＋L・y が b0〜b1）の四隅から LEG_INSET 内。前の 2 本は前の壁の側（x = H）
        a = LEG_SIDE
        for x0, y0 in ((H + LEG_INSET, b0 + LEG_INSET), (H + LEG_INSET, b1 - LEG_INSET - a), (H + L - LEG_INSET - a, b0 + LEG_INSET), (H + L - LEG_INSET - a, b1 - LEG_INSET - a)):
            body.art.append({"kind": "mark", "pts": [(x0, y0), (x0 + a, y0), (x0 + a, y0 + a), (x0, y0 + a)], "closed": True, "mark": "leg"})
    # 尾の糊代を貼る四角（位置の印）。上の面の後ろの端の近く、幅の真ん中（実物の尾は上の面の後ろ寄りから上へ反る。直し E）
    ty = (top0 + top1) / 2
    tx1 = H + L - TAIL_BACK
    body.art.append({"kind": "mark", "pts": [(tx1 - TAIL_TAB, ty - TAIL_W / 2), (tx1, ty - TAIL_W / 2), (tx1, ty + TAIL_W / 2), (tx1 - TAIL_TAB, ty + TAIL_W / 2)],
                     "closed": True, "mark": "tail"})
    ax = p["axle_height"]
    if hang:
        body.holes = [(H - e + HOLE_MARGIN, top1 + HOLE_MARGIN, 1.2), (H - e + HOLE_MARGIN, bottom - HOLE_MARGIN, 1.2)]
    else:
        back = NECK_BACK  # 前の壁の少し後ろに軸を通す。首の帯が壁に当たらないように
        # 軸の穴は側面の縦の所（床から Hs まで）。c = 0 の時は前と同じ式（top1 + H − ax・bottom − (H − ax)）になる
        body.holes = [(H + back, ch1 + Hs - ax, 1.2), (H + back, ch2 - (Hs - ax), 1.2)]
        # 軸の竹串が胴を横切る所の線（EP-0016: 竹串を通す位置の線）。上の面の、2 つの穴と同じ x に横切る点の線（位置の印）
        body.art.append({"kind": "mark", "pts": [(H + back, top0 + 0.6), (H + back, top1 - 0.6)], "mark": "axle"})
        op = p["opening"]
        cy = (b0 + b1) / 2
        # 首の穴は丸く、縁を赤く塗る（実物の写真の直し A。前は四角で、縁は橙）。穴の真ん中は軸の高さ（前の壁は x = H が床の辺で、
        # x が小さいほど高い）。揺れの式（check_physics の首）は、穴の真ん中の縦の列で帯と縁の間を見るので、丸い穴でも同じ式のまま
        body.round_cuts = [(H - ax, cy, op / 2)]
        body.art.append({"kind": "poly", "pts": _circle(H - ax, cy, op / 2 + RIM_W), "fill": RIM})
    head = _head_part(p)
    sw = p["strip_width"]
    length = (p["neck_length"] + 12) if not hang else STRIP_HOLE + axle_to_head_top(p) + HEAD_OVERLAP
    # 帯は半分に折って 2 枚にする。1 枚では頭を支えるには柔らかいと見込むため。
    # 札は軸の穴の下に置き（穴の上の 1.5mm からだと、名の札が穴にかかる）、真ん中の谷折りの線が字の間の空きを通る x にする
    tag, tag_x = _strip_label(sw)
    strip = Part(3, "strip", "首の帯", [(0, 0), (2 * sw, 0), (2 * sw, length), (0, length)], label_xy=(tag_x, STRIP_HOLE + 2.5), label=tag,
                 valley=[((sw, 0), (sw, length))], holes=[(sw / 2, STRIP_HOLE, 1.0), (1.5 * sw, STRIP_HOLE, 1.0)])
    # 尾は根元に糊代（TAIL_TAB）があり、山折りして糊代の刷った面を胴の上の面の四角に貼って立てる（実物の写真の直し E）。
    # 山折りは、糊代の刷った面（斜線）が下を向いて上の面に付く向き（凡例の、刷った面が外がわになる折り）
    n = TAIL_LEN + TAIL_TAB
    tail = Part(4, "tail", "尾", [(0, 0), (TAIL_W, 0), (TAIL_W, n), (0, n)], label_xy=(1, 1.5), label="4 尾",
                mountain=[((0, TAIL_LEN), (TAIL_W, TAIL_LEN))], glue=[[(0, TAIL_LEN), (TAIL_W, TAIL_LEN), (TAIL_W, n), (0, n)]],
                art=[_panel(0.1, 0.1, TAIL_W - 0.1, TAIL_LEN - 0.3, TIGER)]
                + [_stripe((0.4, y), (TAIL_W - 0.4, y + 1.5), 1.6, 0.8) for y in range(10, TAIL_LEN - 4, 8)])
    out = [body, head, strip, tail]
    # 立体の脚 4 本は、部品の最後に足す（脚が無い形の部品の並びと番号は変えない）
    legs_parts = [_leg_part(6 + i, p["leg_height"]) for i in range(4)] if legs else []
    if not hang:
        # 紙の頭は軽いので、重りは軸の真下に下げる。下げる腕が無いと寸法どおりに作れない。
        drop_len = max(p["weight_below_axle"] + 8, 20)
        # 札は「5 腕」（幅 8mm に「5 重りの腕」は入らない。札は部品の枠の内に置く決まり）
        drop = Part(5, "drop", "重りの腕", [(0, 0), (8, 0), (8, drop_len), (0, drop_len)], label_xy=(1, 8), label="5 腕", holes=[(4, 4, 1.0)])
        if p["weight_below_axle"] >= LOWER_HOLE_MIN:
            # 下の穴（重りの位置。EP-0011）と、粘土を付ける高さの点の線（EP-0016）。
            # 前は「下の端に粘土を付ける」だけで、腕が 20mm の下限で長い寸法では、式の位置（軸から weight_below_axle）より下に付いた
            wy = 4 + p["weight_below_axle"]
            drop.holes.append((4, wy, THREAD_R))
            # 粘土を付ける高さの線（EP-0016: 点の丸は「赤い斑点」に見え、何の印か分からなかった）。起き上がり小法師の粘土の線と同じ
            # 位置の印の点の線で、腕を横切る。穴の左右で切る（印が穴にかかると切った時に消える）
            gap = THREAD_R + 1.0
            drop.art += [{"kind": "mark", "pts": [(0.6, wy), (4 - gap, wy)], "mark": "weight"},
                         {"kind": "mark", "pts": [(4 + gap, wy), (7.4, wy)], "mark": "weight"}]
        out.append(drop)
    return out + legs_parts


def place(by_key, page, top, gap):
    body = by_key["body"]
    body.x, body.y = page.x0, top
    y = top + body.height + gap
    x = page.x0
    head, strip, tail = by_key["head"], by_key["strip"], by_key["tail"]
    head.x, head.y = x, y
    x += head.width + gap
    strip.x, strip.y = x, y
    x += strip.width + gap
    if "drop" in by_key:
        drop = by_key["drop"]
        drop.x, drop.y = x, y
        x += drop.width + gap
    tail.x, tail.y = x, y
    x += tail.width + gap
    # 立体の脚は、胴の網の外形の外の空き（前の壁と後ろの壁の上、上の面の帯の左右）に 2 本ずつ縦に置く。下の段に足すと、
    # 用意する物の字の幅が減り、紙の下へはみ出す。重なりの検査（F5.overlap）は外形の多角形で見るので、網の空きに置ける
    legs = [by_key[k] for k in ("leg1", "leg2", "leg3", "leg4") if k in by_key]
    if legs:
        left = page.x0
        right = page.x0 + body.width - legs[0].width
        for i, leg in enumerate(legs):
            leg.x = left if i < 2 else right
            leg.y = top + (i % 2) * (leg.height + gap)
    return y, page.x1 - x, x


def bom(p):
    # 紙の行は本人が確かめた 4 つの名前（#295。エンジンと違う所）。寸法と重さの計算は paper_gsm の数のまま
    paper = paper_name(p["paper_gsm"])
    why = "家庭のプリンタで刷って作るため"
    rows = [
        {"number": 1, "key": "body", "name": "胴", "qty": 1, "material": paper, "substituted": True, "original_guess": "張子（手元の解説の呼び名による）", "reason": why},
        {"number": 2, "key": "head", "name": "頭", "qty": 1, "material": paper, "substituted": True, "original_guess": "張子（同じ）", "reason": why},
        {"number": 3, "key": "strip", "name": "首の帯", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明", "reason": why},
        {"number": 4, "key": "tail", "name": "尾", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明", "reason": why},
        {"number": 7, "key": "axle", "name": "軸", "qty": 1, "material": f"竹串（長さ約 {p['body_width'] + 20}mm に切り、先を落とす）", "substituted": True, "original_guess": "不明", "reason": "家にあり、穴に通しやすいため"},
        {"number": 8, "key": "weight", "name": "重り", "qty": 1, "material": _weight_material(p), "substituted": True, "original_guess": "不明", "reason": "量を変えて試しやすいため"},
    ]
    if p["leg_height"] > 0:
        # 立体の脚 4 本は刷る部品 6〜9。刷る部品の番号は部品表の行と 1 対 1 で結ぶ（F2.bom）ので、刷らない竹串と粘土の番号を 10・11 に送る
        rows[-2]["number"], rows[-1]["number"] = 10, 11
        rows[4:4] = [{"number": 6 + i, "key": f"leg{i + 1}", "name": "脚", "qty": 1, "material": paper, "substituted": True,
                      "original_guess": "張子（実物の写真の短い白い脚）", "reason": why} for i in range(4)]
    if p["mount"] == "neck":
        # 首の形だけが刷る部品 5。部品表に無いと、型紙と部品表が食い違ったまま検査を通った。
        rows.insert(4, {"number": 5, "key": "drop", "name": "重りの腕", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明", "reason": "紙の頭は軽いので、重りを軸の真下に下げる腕が要るため"})
    return rows


def _weight_material(p):
    """重りの素材。糸で下げられる寸法の時だけ、穴から玉の上までの長さの幅（HANG_MIN〜上限）を添える（EP-0011）。"""
    L = hang_thread_mm(p)
    # L は穴から玉の上までの長さで、糸そのものの長さではない（穴に通して結ぶ分と玉に結ぶ分は別に要る。見直しの指摘）
    return f"油粘土 {p['weight_g']:g}g" + (f"（糸で下げる時は、たこ糸も。玉の上は穴から {HANG_MIN}〜{L}mm）" if L is not None else "")


def materials(p):
    # 行の位置でなく key で引く。形によって部品表の行が増えるので、位置で引くと別の行を刷る。
    by = {r["key"]: r for r in bom(p)}
    # 胴に中を切り抜く所がある形（首の形の前の壁の丸い穴）は、カッターを道具に書く（手順に「カッターは大人がする」。制作者の確認 2026-11-06）。
    # 部品を組まずに形の値で決める（切り抜きは首の形にだけある。部品から決めた答えと同じ事は試験で見る。理由は slider_fan.materials と同じ）
    # 首の形は、重りの腕をテープで仮に留めて試してから貼る（EP-0011）ので、セロハンテープも書く（見直しの指摘: 手順にあって用意する物に無かった）
    # カッターは行の終わりに置く（中を切り抜く所がある形の行は「、カッター」で終わる、と試験が見る）
    tools = "のり、はさみ、定規" + ("、セロハンテープ、カッター" if p["mount"] == "neck" else "")
    if p["mount"] != "neck":
        return [f"{by['body']['material']}を 1 枚", tools, by["axle"]["material"], by["weight"]["material"]]
    # 首の形: 紙でない材料の置き所と、丸い印・色の意味を字で書く（EP-0016: 制作者に分からなかった）。手順は刷らないので、刷る紙の字で言う
    L = hang_thread_mm(p)
    hang = f"。糸で下げる時は、たこ糸も。玉の上は穴から {HANG_MIN}〜{L}mm" if L is not None else ""
    return [f"{by['body']['material']}を 1 枚", tools,
            f"{by['axle']['material']}（胴の 2 つの穴・3 首の帯の穴・5 腕の上の穴に通す。胴の上の面の点の線の下を通る）",
            f"油粘土 {p['weight_g']:g}g（" + (f"5 腕の下の穴の、点の線の所に付ける{hang}" if p["weight_below_axle"] >= LOWER_HOLE_MIN
                                          else f"5 腕の上の穴の {p['weight_below_axle']:g}mm 下に付ける") + "）",
            "小さい丸い印は穴（竹串の先であける）。赤い縁の大きな丸は切り抜く。4 尾は外に見えるので色を刷り、3 首の帯と 5 腕は胴の中に入るので白"]


def steps(p):
    out = ["刷った物差しに定規を当て、10cm か確かめる", "部品を実線で切る。胴の小さい穴は竹串の先であける"]
    if p["mount"] == "neck":
        out.append("1 胴の前の壁の丸い穴を切る（カッターは大人がする）")
    # 「線のとおり」は窓口が本人の委任で選んだ字（エンジンは「破線で」。エンジンと違う所。tora-v4 から同じ）
    out += ["1 胴を線のとおり山折りし、糊代で貼って箱にする。上の面は後で閉じる", "3 首の帯を半分に折って貼る。穴は重ねたまま通す"]
    if p["mount"] == "neck":
        # 腕は仮に留めて、頭の傾きを見てから貼る（EP-0011: 作った人が帯と頭を胴の穴から何度も出し入れしていた）。手順の数と番号は変えない
        L = hang_thread_mm(p)
        # 下限も書く（見直しの指摘: 上限だけだと、結ぶ間の無い短さに下げても文に合ってしまう）
        hang = f"か、下の穴に糸を通して粘土の玉を下げる（玉の上は穴から {HANG_MIN}〜{L}mm）" if L is not None else ""
        # 下の穴は weight_below_axle が LOWER_HOLE_MIN 以上の時だけある（軸の穴と近すぎる時は開けない）。無い時は、粘土の位置を軸の穴からの深さで言う
        # （見直しの指摘: 穴の無い寸法でも「下の穴」と言っていた）
        clay = (f"下の穴（点の線）の所に粘土を付ける{hang}" if p["weight_below_axle"] >= LOWER_HOLE_MIN
                else f"粘土の真ん中を、上の穴の {p['weight_below_axle']:g}mm 下に付ける")
        # 両面の頭（head_sides 2）は、折って帯の先を 2 枚の間に挟む。帯の先は頭の真ん中まで（揺れの式は頭の真ん中を帯の先に置く）。
        # 帯は胴から来るので、口と反対の側（頭の後ろ）から入れる。手順の数と番号は変えない
        head = ("2 頭を頭の上の山折りの線で後ろへ折る。3 首の帯の先を、口と反対の側から 2 枚の間の真ん中まで挟み、裏どうしを貼る"
                if p["head_sides"] == 2 else "3 首の帯の前の端に 2 頭を貼る")
        out += [head, "帯を前の壁の穴に入れ、竹串を胴の穴と帯の穴に通す",
                f"5 重りの腕の上の穴にも竹串を通す。{clay}。腕は 3 首の帯に添えて、テープで仮に留める（まだ貼らない）",
                "頭の傾きを見て腕の位置を決めてから、腕を 3 首の帯に貼る"]
    else:
        # 式の「軸から頭の上の端まで」と重りの位置を文に書く。「下の端に貼る」「あごの近く」だけでは、式の寸法を実現できない。
        arm = axle_to_head_top(p)
        out += [f"3 首の帯の下の端を、2 頭の上の端に {HEAD_OVERLAP}mm 重ねて貼る", "竹串を耳の穴と帯の穴に通す",
                f"粘土を頭の裏の真ん中、頭の上の端から {p['weight_below_axle'] - arm:g}mm 下に貼る"]
    if p["leg_height"] > 0:
        # 立体の脚（制作者の追加の指示）。上の面を閉じる前に貼る（底を内から押さえて貼れる）。脚が無い形の手順の数と番号は変えない
        out.append("6〜9 脚を山折りの線で角筒にして糊代で貼り、上の 2 つの糊代を内へ山折りして、1 胴の底の点の線の四角に 1 本ずつ貼る")
    # 尾は上の面の後ろの四角に立てて貼る（実物の写真の直し E。前は「丸くして、後ろに貼る」で、後ろの壁に貼っていた）
    out += ["1 胴の上の面を閉じる", "4 尾の糊代を山折りし、1 胴の上の面の後ろの点の線の四角に貼る。尾は上へ反らせる"]
    return out


# 虎の物差しは頭が揺れるかどうかで足りる（作り手の判断）。周期の差で仮説を見分ける設計にしない。
RESULTS = ("揺れた", "揺れない")


def measures(p):
    """揺れるかの二択でなく、動き方を言葉か絵で予想する（元の repo の手順の紙に合わせた。手順の紙は廃止し、サイトの組み立ての頁で使う）。動かした物は数でないので残す。"""
    return {"predict": "頭はどう動くと思いますか（言葉か絵で）", "rows": [[("動かした物（手・息・団扇）", 40)]]}


def diagram(x, y, w, h, p):
    s = min(w / (p["body_length"] + p["head_w"]), h / (p["body_height"] + 6))
    bx, by = x + p["head_w"] * s, y + 3
    shapes = [{"kind": "rect", "x": bx, "y": by, "w": p["body_length"] * s, "h": p["body_height"] * s}]
    ax_y = by + (p["body_height"] - axle_z(p)) * s
    if p["mount"] == "neck":
        ax_x = bx + 6 * s
        head_x = ax_x - (p["neck_length"] + 6 + p["head_w"]) * s
        shapes.append({"kind": "line", "x1": head_x + p["head_w"] * s, "y1": ax_y, "x2": ax_x, "y2": ax_y})
        shapes.append({"kind": "rect", "x": head_x, "y": ax_y - p["head_h"] * s / 2, "w": p["head_w"] * s, "h": p["head_h"] * s})
    else:
        ax_x = bx - (p["ear_length"] - HOLE_MARGIN) * s
        top = ax_y + axle_to_head_top(p) * s
        shapes.append({"kind": "line", "x1": ax_x, "y1": ax_y, "x2": ax_x, "y2": top})
        shapes.append({"kind": "rect", "x": ax_x - p["head_w"] * s / 2, "y": top, "w": p["head_w"] * s, "h": p["head_h"] * s})
    wz = ax_y + p["weight_below_axle"] * s
    shapes.append({"kind": "line", "x1": ax_x, "y1": ax_y, "x2": ax_x, "y2": wz, "dash": "1,0.6"})
    shapes.append({"kind": "rect", "x": ax_x - 1.2, "y": wz - 1.2, "w": 2.4, "h": 2.4})
    return shapes
