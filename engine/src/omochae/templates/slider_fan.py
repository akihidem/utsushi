"""雛形 slider_fan: 角筒の中で動く台に蛇腹の扇と像を載せ、押し上げると開く。

押し方の読みを描き分ける（どれが昔の作り方かは分からない）。ただし玩具の型紙は 1 枚で、rise（内筒を下から押し上げる形）がたたき台
（制作者の決定 2026-11-06「筒を外す形（lift）はやめる。下から押し上げるバージョンを作る。側面のつまみのバージョンは廃止。内筒を付ける。」）。
tab・tube・stick・lift は試行錯誤のヒントとして残す読み（制作者の決定 2026-11-05「玩具 1 つに型紙 1 枚」・omochae.sheets）。
既定の形は tab のまま（tab を既定で刷る凍結の場面の紙を変えないため）。寸法の初期値は行程の計算から出した。
どの値も実物では未確認。Claude が変えてよいのは RANGES にある名前の値だけで、座標には触れない。
"""
from shapely.geometry import LineString, Polygon

from ..fan_model import clearance_limit_deg, opening_bound_deg, shortest_free_thread
from ..model import Failure, Part
from ..ops3d import ops as assembly_ops

ID = "slider_fan"
# 寸法の共通の出発点。手元の複写の図の比と紙面の制約から出した。
# 押し方と中心の置き方の値は答えではない。型紙の 1 枚（たたき台）は omochae.sheets が決め、ほかの組は試行錯誤のヒント。
DEFAULTS = {
    "push_part": "tab",
    # 扇の中心の置き方も仮説の違い。axle は口より上の軸、rim は口の高さの台。
    "hub": "axle", "pivot_above_rim": 21,
    "tube_side": 30, "tube_height": 84, "tube_glue": 8,
    "pusher_side": 26, "pusher_height": 15, "pusher_glue": 8,
    "push_amount": 69,
    "fold_height": 48, "fold_width": 8.5, "fold_count": 28,
    "base_side": 26, "base_glue": 6,
    # 割り箸の柄で押す形にも、内筒を短く切った土台を載せる（v8）。紙で組んで試した時、つまみの形にある土台が柄の形にもある方が作りやすかったため。
    "stage_height": 15,
    "figure_w": 12, "figure_h": 32,
    "knob_width": 4,
    # 0.15mm はふつうの厚めの紙の見込み。実物の紙を測ったら置き換える。
    "paper_thickness": 0.15,
}
RANGES = {
    "tube_side": (20, 50), "tube_height": (50, 130), "tube_glue": (5, 12),
    # 内筒の高さの上限も筒の高さと同じ 130 にした。内筒を下から押す形と柄の形は内筒が筒より短いと落とす（L < H）ので、
    # 筒の上限だけを上げると、その形では 111〜130 の筒が書けなかった（見直しの指摘）
    "pusher_side": (15, 48), "pusher_height": (10, 130), "pusher_glue": (5, 12),
    "push_amount": (10, 90),
    "pivot_above_rim": (0, 40),
    # 折り数の上限 60 と筒の高さの上限 130 は、実物の写真（制作者の決定 2026-11-06「実物の写真と照らした直しは…全部入れる」）の
    # 扇の折り目 44〜52 枚・筒の長さ 一辺の約 4 倍（一辺 30 で 120）を、寸法で書けるようにするため。その寸法で刷れるかは、
    # 配置（F5.print_area）と扇の床（F5.fan_clearance）が決める。既定値は変えない（凍結の場面が既定の寸法で動くので、
    # 既定を替えると凍結の期待が崩れる）
    # 折り幅の下限 4 は、内筒を下から押し上げる形（rise）の次の組の、細かい扇の板の幅（実物の写真の扇は約 3.7mm）。前は 5
    "fold_height": (20, 60), "fold_width": (4, 15), "fold_count": (6, 60),
    "base_side": (10, 48), "base_glue": (4, 10),
    "stage_height": (8, 40),
    "figure_w": (8, 30), "figure_h": (15, 60),
    "knob_width": (2, 8),
    # 上限を広く取るのは、厚さの検査が範囲の検査より先に落ちないようにするため。
    "paper_thickness": (0.05, 1.5),
    # 扇の長さ（書く時は折り数×折り幅と合う事を F5.fan_length で見る）の上限は、折り数と折り幅の上限の積（60 × 15）。
    # 折り数の上限を上げた時に 300 のままだと、合っている長さ（52 枚 × 8.5mm＝442 など）を範囲の検査が先に落とした（見直しの指摘）
    "fan_length": (50, 900),
}
PUSH_PARTS = ("tab", "tube", "stick", "lift", "rise")
# lift（筒を外す形）: 制作者のレビュー（2026-11-06）から採った案 EP-0017 の、御来迎の次の版（goraigo-v11）。扇は糸を一切使わず（制作者「糸なしでやります」）、
# 扇の下の端を 2 受け（小さい U の字の部品）に貼って束ね、両端の板も受けに貼る。蛇腹の折り目のばねで扇は「基本は開いている」形になり、
# 1 外筒をかぶせると扇は畳まれ、筒を上へ外すと開く（制作者「この形で開くなら、内筒を下から押す仕組みも竹串も要らない」）。
# 内筒・竹串・糸・穴は無い。今の組 goraigo-v10 の形（tab・tube・stick）は変えない（凍結の場面はそのまま）
LIFT = "lift"
# rise（内筒を下から押し上げる形）: 制作者の決定（2026-11-06）「筒を外す形（lift）はやめる。下から押し上げるバージョンを作る。
# 側面のつまみのバージョンは廃止。内筒を付ける。」と、前の決定「糸なしでやります」による、御来迎の次の組の形。
# lift の糸の無い扇と受けを、内筒の上の口に差し込んで蓋をした台に載せる。外筒を持ち、内筒の内に貼って外筒の下へ出した割り箸で
# 押し上げると（v13 から。下の注）、台の上の面が外筒の口の高さまで上がり、扇が口から出て開く。引き下げると扇は口の縁で畳まれて
# 筒に入る（紙で確かめていない）。糸・竹串・溝・つまみ・穴は無い。
# 扇の要を像の首の高さに上げる事（実物の写真の案 B）は、要を支える柱の部品が要るので、この形を紙で確かめた後に入れる
RISE = "rise"
# 次の組 goraigo-v13 の直し（制作者の指示 2026-11-06「御来迎の形の直し: ① 外筒の紫色の部分は不用（外す）。② 内筒は半分の長さにする。
# ③ 押し上げは、内筒の内側に割り箸を貼り付ける形にする。」）: 押す所は割り箸。割り箸を 2 内筒の刷った面（谷折りで筒の内になる面）の
# 印に沿って貼り、外筒の下へ出た割り箸を持って押し上げ・引き下げる。内筒は外筒の下へ出さなくてよいので、v12 の半分の長さにした。
# 位置の言葉: 「開いた位置」は、静かな時から押し上げる量 s だけ押して、台の上の面が口の高さに来た所（扇が開く）。止めは無く、
# 静かな時の位置は外筒と割り箸を一緒に持って保つ（手を離すと内筒は下へ抜ける。組み方の最後の段に書く）。
CHOPSTICK_LEN = 200  # 割り箸の長さ mm の見込み。よく売っている割り箸は約 20〜21cm で、その短い方。切らずに使う
CHOPSTICK_W = 5  # 割った割り箸 1 本の太さ mm の見込み。内筒に刷る、割り箸を貼る位置の印の幅
CHOPSTICK_GRIP = 30  # 開いた位置でも、割り箸を外筒の下へ残す長さの下限 mm。指で持って押し引きする所（見込み。未確認）
CHOPSTICK_GLUE = 20  # 割り箸を内筒に貼る長さの下限 mm。短いと押した時に外れる見込み（未確認）
CHOPSTICK_GAP = 1  # 台の糊代（内筒の上の口の内に貼る）の下の端と、割り箸の上の端の間 mm
# 割り箸は内筒の 1 つの壁に沿って貼るので、押す力は内筒の軸から約（一辺の半分 − 割り箸の太さの半分）ずれ、内筒を傾ける力になる
# （見直しの指摘）。引き出しの引っかかりの見込み（押す力のずれ e、支える長さ L、紙どうしの摩擦の係数 μ で、μ > L / (2e) なら
# 引っかかる）では、v13 の一番短い支え（静かな時に外筒に入る長さの下限＝内筒の一辺 22）と e ≈ 8.5 で L / (2e) ≈ 1.3。紙どうしの
# μ の見込み（0.3〜0.6）より大きいので、今の「内筒の一辺以上入る」決まりで引っかからない見込み（紙で確かめていない）
# 次の組の寸法の見本は examples/goraigo_v13.json。v12 の寸法のまま、内筒の長さを半分（115 → 57.5）にした（v12 の見本の場面は、v13 の形
# では割り箸の行と両側の像の分だけ A4 の刷る域から出るので外した）。
# v12 で選んだ事（実物の写真の比に、A4 の 1 枚と床が許す所まで寄せた）はそのまま:
# - 筒は一辺 26・高さ 100（3.85 倍。写真は約 4 倍）。台・像・受けの段が筒の網と横に並ぶのは一辺 26 まで。
# - 扇の要は台の上にあるので、扇は台の縁と口の角までのほぼ 180° しか開けない。開く角の見込みがそこに収まる折りは 22 枚 × 4mm（高さ 28.6）。
#   写真の 300° は要が首の高さにある時の角で、180° に入る折り目の細かさ（板の幅 4mm）は写真の扇（約 3.7mm）に近い。
#   折り幅の下限を 5 から 4 に下げたのは、この細かさにするため。要を上げる柱（案 B）を入れたら、折り数を増やせる
# 次の組 goraigo-v14 の見本は examples/goraigo_v14.json。制作者の言葉（2026-11-06）「御来迎、4扇は今の倍の長さにして欲しい。」と
# 「内筒が外筒よりもふた回りくらい小さいのでスカスカ。抵抗があった方がいい。」による。v13 から 6 つの寸法を変えた:
# - 扇はまるごと倍: 折り 22 → 44 枚（板の幅 4mm のまま。帯 88 → 176mm）・高さ 28.6 → 57.2。開く角の見込み（帯の長さ ÷ 高さ）は
#   176° のまま（台の縁と口の角までの 181° に収まる）。帯の長さだけを倍にする読みは、要が台の上にある今の形では 353° 開こうとして
#   口の角に当たり、高さだけを倍にする読みは 88° しか開かない（今の半円の形を保てない）。折り 44 枚は写真の扇（44〜52 枚）に近い。
# - 押し上げる量 31 → 60。静かな時に扇（受けの底＋扇の高さ＋2）が口の下に隠れるため。
# - 外筒の高さ 100 → 130（範囲の上限）。内筒 57.5 が静かな時に外筒の下から出ないため（台の上の面は静かな時 70・開いた時 130）。
# - 内筒の一辺 22 → 24.5（外筒 26 との隙間は片側 2 → 0.75mm）・台 21.5 → 24（内筒の口に差し込める大きさ）。凍結の床（F5.slide_clearance:
#   内筒は外筒 − 1 より小さい）が許すのは 24.9 まで。紙で試して、まだ緩ければ 24.9 にする。
# 筒は一辺の 5 倍で写真の約 4 倍より長く、扇の半径は筒の一辺の約 2.2 倍（写真は約 1.1 倍）。どちらも制作者の言葉を写真の比より先にした。
# 帯が長いので、扇の右の列が左の列より下まで来る。文字は左の列の内筒の下から、右の段の左までの幅で刷る（place）
CRADLE_FLAP = 8  # 受けの左右の面の高さ mm。扇の両端の板の下の端からこの高さまでを貼る
CRADLE_ROOM = 0.8  # 受けの底の奥行きの、畳んだ扇の厚さに足す余り mm
# 刷る形を決める寸法（押し方）。寸法を直に渡す入口（python -m omochae --params）では既定に頼らず必ず書かせる（刷った形を JSON に残すため）。
FORM = "push_part"
FORMS = PUSH_PARTS  # 刷る形の値の一覧（作りうる部品を数える時に使う）
# 既定の出典（data/sources/ の名前）。--source を書かない時に、雛形と合わない出典の印を刷らないため。
SOURCE = "NDL-1187053-R0000005-L"
HUBS = ("axle", "rim")
# 開く糸を扇の中心からこの距離につなぐ。途中で突っ張らない糸が一番短く、よく開く位置。糸の長さはこの距離から fan_model.shortest_free_thread で出す。
THREAD_RADIUS = 35
# 開く糸を結ぶ筒の穴の、口からの深さ。糸の長さの式（thread_mm）も同じ値から測る。
THREAD_DEPTH = 3
# 溝が筒の端に近いと紙が裂けやすい。実物で確かめるまでの安全側の見込み。
SLOT_MARGIN = 5


def spec():
    """Claude に渡す道具 get_template_spec の中身。"""
    return {"template_id": ID, "defaults": DEFAULTS, "ranges": RANGES, "push_part": PUSH_PARTS, "hub": HUBS}


def check_range(p):
    out = []
    if isinstance(p.get("fold_count"), float) and not p["fold_count"].is_integer():
        out.append(Failure("F5.range", "fold_count", "折り数は整数"))
    for k, v in p.items():
        if k == "push_part":
            if v not in PUSH_PARTS:
                out.append(Failure("F5.range", k, f"{v} は {PUSH_PARTS} のどれでもない"))
        elif k == "hub":
            if v not in HUBS:
                out.append(Failure("F5.range", k, f"{v} は {HUBS} のどれでもない"))
        elif k not in RANGES:
            out.append(Failure("F5.range", k, "知らない寸法の名前"))
        elif not isinstance(v, (int, float)) or isinstance(v, bool) or not RANGES[k][0] <= v <= RANGES[k][1]:
            out.append(Failure("F5.range", k, f"{v} は範囲 {RANGES[k]} の外"))
    return out


def slot_span(p):
    """溝の範囲を筒の底からの高さで返す。つまみは内筒の高さの中ほどに通す。

    v8 から溝は筒の下の端まで切り込む（くり抜かない）。紙で組んで試した時、側面の穴をくり抜くのが大変で、下から切り取る方が
    作りやすかったため。下の端は開くので、使うのは上の端 high だけ。low は内筒が静止する高さの目安として残す。
    """
    rest_bottom = p["tube_height"] - p["push_amount"] - p["pusher_height"]
    low = rest_bottom + p["pusher_height"] / 2 - p["knob_width"] / 2
    return low, low + p["push_amount"] + p["knob_width"]


def check_physics(p):
    out = []
    H, s, h = p["tube_height"], p["push_amount"], p["fold_height"]
    A, a, L = p["tube_side"], p["pusher_side"], p["pusher_height"]
    length = p["fold_count"] * p["fold_width"]
    if "fan_length" in p and abs(p["fan_length"] - length) > 1e-6:
        out.append(Failure("F5.fan_length", "蛇腹の扇", f"折り数×折り幅={length} と扇の長さ {p['fan_length']} が違う"))
    if p["push_part"] == LIFT:
        return out + _check_lift(p)
    if p["push_part"] == RISE:
        return out + _check_rise(p)
    d = p["pivot_above_rim"] if p["hub"] == "axle" else 0
    if p["hub"] == "axle":
        # 中心が上がる分だけ、隠すための行程が要る。
        if d + h > s:
            out.append(Failure("F5.fan_height", "蛇腹の扇", f"中心の高さ {d}＋折りの高さ {h} が押し上げる量 {s} を超え、扇が隠れない"))
        # 足の糊代が扇の本体に食い込むと、糊代の折り線が要の穴の列を横切る（レビューの指摘）。
        # 範囲の検査は pivot_above_rim を 0 まで許すので、足の長さが糊代に足りない組はここで落とす。
        if leg_length(p) < LEG_GLUE:
            out.append(Failure("F5.fan_leg", "蛇腹の扇", f"足の長さ {leg_length(p)} が糊代 {LEG_GLUE} に足りず、糊代が扇に食い込む（中心の高さ {d} が 2 未満）"))
    elif h > s:
        # 口の台の形も、静かな時の台から口までは押し上げる量 s（軸の形と同じ見方）。H − s は台の下の空きで、
        # これと比べていたので、扇が口から出る寸法が通っていた（レビューの指摘で直した）。
        out.append(Failure("F5.fan_height", "蛇腹の扇", f"畳んだ高さ {h} が押し上げる量 {s} を超え、静かな時に扇が口から出る"))
    bound, limit = opening_bound_deg(p["fold_count"], p["fold_width"], h), clearance_limit_deg(A, d)
    if bound > limit:
        out.append(Failure("F5.fan_clearance", "蛇腹の扇", f"帯の長さでは {bound:.0f}° 開くが、筒の口の角に当たって {limit:.0f}° までしか開けない"))
    thick = p["fold_count"] * p["paper_thickness"]
    if thick > a - 2:
        out.append(Failure("F5.fan_thickness", "蛇腹の扇", f"畳んだ厚さ {thick:.1f} が内筒の一辺−2={a - 2} を超える"))
    if not a < A - 1:
        out.append(Failure("F5.slide_clearance", "内筒", f"内筒 {a} は外筒 {A} − 1 より小さくない"))
    if p["figure_h"] > h + 6:
        out.append(Failure("F5.figure_height", "像", f"像の高さ {p['figure_h']} が折りの高さ＋6={h + 6} を超える"))
    if p["base_side"] > a:
        out.append(Failure("F5.base_size", "扇の台", f"扇の台 {p['base_side']} が内筒 {a} を超える"))
    # 像の足の糊代は像の幅の 0.3〜0.7（parts の cx0・cx1）。台より広いと貼れない。像の高さだけを見ていたので通っていた。
    foot = p["figure_w"] * (FOOT[1] - FOOT[0])
    if foot > p["base_side"]:
        out.append(Failure("F5.figure_base", "像", f"像の足の糊代 {foot:.1f} が扇の台 {p['base_side']} より広く、台に貼れない"))
    if p["push_part"] == "tab":
        if L > H - s:
            out.append(Failure("F5.stroke", "内筒", f"内筒の長さ {L} が静止時の筒の空き {H - s} に収まらない"))
        low, high = slot_span(p)
        # 下の端は開いた切り込みなので、上の端だけが筒の口から離れていればよい。
        if H - high < SLOT_MARGIN:
            out.append(Failure("F5.stroke", "溝", f"溝が筒の口から {SLOT_MARGIN}mm 離れない（底から 0〜{high:.1f}）"))
    elif p["push_part"] == "stick" and p["stage_height"] > H - s:
        out.append(Failure("F5.stroke", "土台", f"土台の高さ {p['stage_height']} が静止時の筒の空き {H - s} に収まらない"))
    elif p["push_part"] == "tube" and s > H:
        # 静止時の内筒の上の端は外筒の底から H − s。量が高さを超えると、扇の台が外筒の下へ出て扇が筒に入らない。
        # つまみと柄の形は上の 2 つの検査が同じ事を含むので、内筒を下から押す形だけに足す。
        out.append(Failure("F5.stroke", "内筒", f"押し上げる量 {s} が筒の高さ {H} を超え、静止時に内筒の上の端が筒の下に出る"))
    if p["push_part"] != "tab" and L < H:
        # L < H だと指が筒の外にある間に押し切れない（行程の計算で見つかった不足）。
        out.append(Failure("F5.stroke", "押す部品", f"長さ {L} が筒の高さ {H} より短く、押し切れない"))
    return out


def cradle_depth(p):
    """2 受けの底の奥行き。畳んだ扇の厚さ（板の数 × 紙の厚さ）に余りを足す。"""
    return p["fold_count"] * p["paper_thickness"] + CRADLE_ROOM


def cradle_width(p):
    """2 受けの幅。扇の板の幅に 2mm 足し、札「2 受け」が入る 10mm を下限にする（札は部品の枠の内に置く決まり）。"""
    return max(p["fold_width"] + 2, 10)


def cradle_number(p):
    """受けの部品の番号。lift は 2、rise は 2 番が内筒なので 6（部品表と型紙の札が同じ番号を指す）。"""
    return 6 if p["push_part"] == RISE else 2


def _check_lift(p):
    """筒を外す形の床。押し上げる仕組みが無いので、行程（F5.stroke）・内筒の遊び（F5.slide_clearance）・足（F5.fan_leg）・
    筒の口の角（F5.fan_clearance。扇は筒を外してから開く）は見ない。見るのは、筒が台と扇と像にかぶさる事と、受けが台に乗る事。
    床の名は今の物を使う（凍結の基準の一覧にある名だけを使う）。
    """
    out = []
    H, A, h, g, b = p["tube_height"], p["tube_side"], p["fold_height"], p["base_glue"], p["base_side"]
    thick = p["fold_count"] * p["paper_thickness"]
    # 台は糊代を下へ折った浅い箱で、高さは糊代の長さ。その上に、受けの底（紙 1 枚）と畳んだ扇が立つ（紙の厚さも足す。見直しの指摘）
    t = p["paper_thickness"]
    if g + t + h > H - 2:
        out.append(Failure("F5.fan_height", "蛇腹の扇", f"台の高さ {g}＋受けの底の紙 {t:g}＋扇の高さ {h} が筒の高さ {H}−2 を超え、筒をかぶせられない"))
    if thick > A - 2 - 2 * CRADLE_ROOM:
        out.append(Failure("F5.fan_thickness", "蛇腹の扇", f"畳んだ厚さ {thick:.1f} が筒の一辺 {A} に収まらず、受けごと筒に入らない"))
    if b > A - 1:
        out.append(Failure("F5.base_size", "扇の台", f"扇の台 {b} が外筒 {A} − 1 より大きく、筒をかぶせられない"))
    if cradle_width(p) > b - 2 or cradle_depth(p) + 2 > b / 2:
        out.append(Failure("F5.base_size", "受け", f"受け（幅 {cradle_width(p):g}・奥行き {cradle_depth(p):.1f}）が台の奥の半分（{b / 2:g}）に乗らない"))
    if p["figure_h"] > h + 6:
        out.append(Failure("F5.figure_height", "像", f"像の高さ {p['figure_h']} が折りの高さ＋6={h + 6} を超える"))
    if g + p["figure_h"] > H - 2:
        out.append(Failure("F5.figure_height", "像", f"台の高さ {g}＋像の高さ {p['figure_h']} が筒の高さ {H}−2 を超え、筒をかぶせられない"))
    foot = p["figure_w"] * (FOOT[1] - FOOT[0])
    if foot > b:
        out.append(Failure("F5.figure_base", "像", f"像の足の糊代 {foot:.1f} が扇の台 {b} より広く、台に貼れない"))
    # 筒をかぶせるので、像の幅と畳んだ扇の幅も筒の内に入る（見直しの指摘: 足の糊代だけ見ていて、幅 30 の像が一辺 20 の筒を通った）
    if p["figure_w"] > A - 2:
        out.append(Failure("F5.figure_base", "像", f"像の幅 {p['figure_w']} が筒の一辺 {A}−2 を超え、筒をかぶせられない"))
    if p["fold_width"] > A - 2:
        out.append(Failure("F5.fan_thickness", "蛇腹の扇", f"畳んだ扇の幅 {p['fold_width']} が筒の一辺 {A}−2 を超え、筒をかぶせられない"))
    return out


def _tube(number, key, name, side, height, glue, label, notch=None):
    """notch=(x0, x1, top) は下の端から top まで切り込む溝（v8）。はさみで下から切れるよう、輪郭の一部にする。"""
    w = side * 4
    # 糊代の角を落とすのは、貼る時に隣の面へはみ出さないようにするため。
    outline = [(0, 0), (w, 0), (w + glue, 2), (w + glue, height - 2), (w, height)]
    if notch:
        x0, x1, top = notch
        outline += [(x1, height), (x1, top), (x0, top), (x0, height)]
    outline.append((0, height))
    return Part(number, key, name, outline, label_xy=(1.5, 1.5), label=label,
                valley=[((side * i, 0), (side * i, height)) for i in range(1, 5)],
                glue=[[(w, 0), (w + glue, 2), (w + glue, height - 2), (w, height)]])


# 像の色は NDL の図から測った値。図を貼らず、色と線を描き直す（拡大した図の粗さを避け、作る線を読みやすくするため）。
PAPER, LINE, FACE = "#a89365", "#55492c", "#b9a677"
# 色の境で折る（v9）。見える面に谷折り・山折りの線があると見た目が安っぽく見えるので、絵の色の境で折り、線を引かない
# （作り手の判断）。隣り合う面と板の色を変え、その境を折り目にする。1 色に塗ると折る所の目印が消えるので、近い 2 色を交互にする。
# 筒と扇の色は、実物の写真に寄せた（制作者の決定 2026-11-06。次の組 goraigo-v12）: 筒は白木の角柱で、扇は金の箔の紙。
# 刷った紙では木目も箔の光も出ないので、白木と金に近い色にした。筒の上と下の帯は、角柱の端に見せる少し濃い木の色
# （前は原図の橙と茶の帯）。筒は 1 面おきに少し濃い地、扇は 2 色の板を交互にする。
WOOD, WOOD_ALT, WOOD_TOP, WOOD_BOTTOM = "#ece1c6", "#dfd1ae", "#cbb68b", "#bba476"
FAN_A, FAN_B = "#e8c766", "#d4aa44"
# 筒の紫の枠の札（v12 で足した）は、制作者の指示（2026-11-06「① 外筒の紫色の部分は不用（外す）」）で外した（どの形も）


def _tube_art(A, H, notch=None):
    """筒の 4 面の描き直し。絵の手前の角の 2 本線は、折り線の両側に 1 本ずつ引くと組んだ時に細い面に見える。

    溝の切り込みがある面は、切り込みの左右に分けて塗る（絵を切る線の外に出さないため）。
    """
    art = []
    for i in range(4):
        x0, x1 = A * i, A * (i + 1)
        cols = [(x0, x1)]
        if notch and x0 < notch[0] and notch[1] < x1:
            cols = [(x0, notch[0]), (notch[1], x1)]
        art.append({"kind": "poly", "pts": [(x0, 0), (x1, 0), (x1, 4.5), (x0, 4.5)], "fill": WOOD_TOP})
        ground = WOOD if i % 2 == 0 else WOOD_ALT
        for c0, c1 in cols:
            art.append({"kind": "poly", "pts": [(c0, 4.5), (c1, 4.5), (c1, H - 5), (c0, H - 5)], "fill": ground})
            art.append({"kind": "poly", "pts": [(c0, H - 5), (c1, H - 5), (c1, H), (c0, H)], "fill": WOOD_BOTTOM})
        if len(cols) == 2:
            # 溝の上の端より上は 1 枚の面のまま塗る。
            art.append({"kind": "poly", "pts": [(notch[0], 4.5), (notch[1], 4.5), (notch[1], notch[2]), (notch[0], notch[2])], "fill": ground})
    art.append({"kind": "line", "pts": [(A - 1.2, 0), (A - 1.2, H)], "stroke": LINE, "sw": 0.5})
    art.append({"kind": "line", "pts": [(A + 1.2, 0), (A + 1.2, H)], "stroke": LINE, "sw": 0.5})
    return art


# 像の線。絵を見て手で点を取り直した物で、絵の画素は使っていない。座標は輪郭と同じ 0〜1 に直す。
_FIGURE_LINES = [
    [(72, 155), (85, 195)], [(170, 150), (155, 200)],
    [(110, 218), (115, 180), (125, 168), (138, 185), (145, 205), (130, 225), (120, 235), (110, 218)],
    [(40, 240), (60, 265), (110, 240)], [(195, 272), (150, 235)],
    [(65, 270), (100, 310)], [(90, 285), (140, 245)], [(125, 280), (130, 340)],
    [(72, 340), (95, 340), (105, 355), (130, 360), (170, 340)],
    [(105, 360), (110, 410), (122, 425), (158, 385), (140, 470)], [(185, 385), (165, 470)], [(72, 345), (85, 500)],
]
_FACE = [(118, 60), (140, 68), (153, 90), (150, 118), (135, 140), (118, 146), (100, 140), (85, 118), (82, 90), (95, 68)]


def _figure_art(fw, fh, pts):
    scale = lambda ps: [(fw * (x - 36) / 177, fh * (y - 33) / 472) for x, y in ps]
    art = [{"kind": "poly", "pts": pts, "fill": PAPER}, {"kind": "poly", "pts": scale(_FACE), "fill": FACE, "stroke": LINE, "sw": 0.25}]
    # 手で取った線の端が輪郭を越えた時は切る。切る線の外に絵を残さないため。
    body = Polygon(pts).buffer(-0.15)
    for line in _FIGURE_LINES:
        clipped = LineString(scale(line)).intersection(body)
        for piece in getattr(clipped, "geoms", [clipped]):
            if not piece.is_empty and piece.geom_type == "LineString":
                art.append({"kind": "line", "pts": list(piece.coords), "stroke": LINE, "sw": 0.25})
    return art


# 像の輪郭（絵を見て手で取った点を 0〜1 にした物）。
_RAW = [(113, 33), (135, 45), (150, 62), (158, 85), (157, 120), (153, 135), (172, 152), (195, 175), (210, 205), (213, 250),
        (200, 272), (193, 280), (190, 330), (180, 410), (170, 475), (165, 505), (90, 505), (85, 470), (72, 400), (65, 350),
        (62, 330), (68, 290), (50, 265), (40, 240), (36, 210), (45, 175), (65, 155), (78, 130), (80, 100), (78, 80), (90, 62), (100, 45)]
FIGURE_OUTLINE = [((x - 36) / 177, (y - 33) / 472) for x, y in _RAW]


def _insert_tab(pts, x0, x1, bottom, tab):
    """輪郭の底辺（右下→左下の順）の間に足を入れる。"""
    i = max(range(len(pts)), key=lambda k: (pts[k][1], pts[k][0]))
    return pts[: i + 1] + [(x1, bottom), (x1, bottom + tab), (x0, bottom + tab), (x0, bottom)] + pts[i + 1:]


def _two_sided_figure(p):
    """内筒を下から押し上げる形（rise）の 5 像。前の像と、頭の上で折り返した鏡写しの像を 1 つの部品にする。

    制作者の指示（2026-11-06「顔は、両側に貼れるように首から立体的にするか、両側から見た物を用意して。」）の後の方（両側から見た物）。
    - 頭の上の山折りの線で後ろの半分を後ろへ折り、裏どうしを貼り合わせる。山折り（刷った面の裏へ折る）なので、刷った面（顔）が
      前と後ろの外を向き、裏どうしが合わさる。糊は裏に付けるので糊代の斜線は刷らない（斜線は刷った面に付ける糊の印で、裏の糊は
      組み方の文で言う）。
    - 後ろの半分は前と同じ絵（上下を返した物）で、折ると後ろから見ても顔が出る（左右は鏡写し）。
    - 頭の上の尖り（輪郭の最初の 1 点）を外して頭の上を平らな線にし、そこを折り線にする。外す尖りは像の高さの約 2.5% で、顔の絵より上。
      平らな線の幅は像の幅の約 0.2 倍（短い蝶番だが、裏どうしを全部貼るので、折り線は 2 つの半分の向きを合わせるだけ）。
    - 足の糊代（台に貼る）は前の半分にだけ付け、後ろへ折って台に貼る（前と同じ）。
    頭を首から立体にする形（指示の前の方）は作っていない。
    """
    fw, fh = p["figure_w"], p["figure_h"]
    flat = [(fw * x, fh * y) for x, y in FIGURE_OUTLINE[1:]]  # 頭の上の尖りを外す。最後の点と最初の点を結ぶ辺が、平らな頭の上
    yf = flat[0][1]
    assert abs(flat[-1][1] - yf) < 1e-9  # 頭の上の平らな辺は水平（輪郭の点がそうなっている事を、形を変えた時に見落とさないため）
    tab = 5  # 台に貼る足（前の半分だけ）
    cx0, cx1 = fw * FOOT[0], fw * FOOT[1]
    front = _insert_tab(flat, cx0, cx1, fh, tab)
    mirror = lambda q: (q[0], 2 * yf - q[1])
    back = [mirror(q) for q in reversed(flat[1:-1])]  # 前の輪郭を逆にたどった鏡写し。折り線の両端は前と同じ点なので入れない
    dy = fh - 2 * yf  # 後ろの半分の上の端（鏡写しの足）を 0 にする
    shift = lambda q: (q[0], q[1] + dy)
    art_front = _figure_art(fw, fh, flat)
    art_back = [{**item, "pts": [mirror(q) for q in item["pts"]]} for item in art_front]
    return Part(5, "figure", "像", [shift(q) for q in front + back], label_xy=(fw * 0.4, fh * 0.6 + dy), label="5",
                mountain=[(shift(flat[-1]), shift(flat[0]))],
                glue=[[shift(q) for q in ((cx0, fh), (cx1, fh), (cx1, fh + tab), (cx0, fh + tab))]],
                art=[{**item, "pts": [shift(q) for q in item["pts"]]} for item in art_front + art_back])


def _axle(p):
    """軸の形（扇を糸で束ね、足と穴がある）か。筒を外す形（lift）と内筒を下から押し上げる形（rise）は糸も穴も無いので、
    hub に関わらず軸の形にしない。"""
    return p["hub"] == "axle" and p["push_part"] not in (LIFT, RISE)


def _cradled(p):
    """扇を受け（U の字の部品）で束ねる形か（lift と rise）。扇は穴と足の無い長方形で、受けの底の面を台の印に貼る。"""
    return p["push_part"] in (LIFT, RISE)


def _cradle(p):
    """2 受け（筒を外す形、EP-0017）。U の字に折り、底の面に畳んだ扇の下の端を、左右の面に扇の両端の板の下の所を貼る
    （制作者「扇の底面・側面にのり付けで固定・扇の両端をそれで付けて基本は開いている形」）。底の面の裏は 3 台の印に貼る。
    刷った面が U の内（扇の側）になるので谷折りで、刷った面の全部が糊代。蛇腹の折り目がばねになって扇の上が開き、受けは扇の下を束ねる。
    """
    w, d, f = cradle_width(p), cradle_depth(p), CRADLE_FLAP
    total = 2 * f + d
    # rise は 2 番が内筒なので、受けは 6 番（部品表と同じ番号）
    k = cradle_number(p)
    return Part(k, "cradle", "扇の受け", [(0, 0), (w, 0), (w, total), (0, total)], label_xy=(0.3, 1.5), label=f"{k} 受け",
                valley=[((0, f), (w, f)), ((0, f + d), (w, f + d))],
                glue=[[(0, 0), (w, 0), (w, f), (0, f)], [(0, f), (w, f), (w, f + d), (0, f + d)], [(0, f + d), (w, f + d), (w, total), (0, total)]])


def parts(p):
    A, H, a, L = p["tube_side"], p["tube_height"], p["pusher_side"], p["pusher_height"]
    out = []
    notch = None
    if p["push_part"] == "tab":
        low, high = slot_span(p)
        # 溝は 2 面目の中央。ラベルの面と離し、糊の継ぎ目からも離す。y は頁の下向きなので高さから引く。
        notch = (A * 1.5 - (p["knob_width"] + 1) / 2, A * 1.5 + (p["knob_width"] + 1) / 2, H - high)
    tube = _tube(1, "tube", "外筒", A, H, p["tube_glue"], "1 外筒", notch)
    tube.art = _tube_art(A, H, notch)
    tube.hide_folds = True
    # 外筒は色の面を外にして角筒にするので、刷った面から見て山折り（制作者の答え 2026-11-06「色がついている所が外を向くよう折った」）。
    # 谷折り（凡例の、刷った面がへこむ向き）のままだと色の面が筒の内に入る事を、3D で組んで見つけた（omochae.fold3d の 3D.face）。
    # 線は刷らず色の境で折る部品なので、型紙の PDF は変わらない。内筒は隠れる部品で、破線を刷るので谷のまま（手順 2 の文は制作者の決定 2026-11-06）
    tube.mountain, tube.valley = tube.valley, []
    if _axle(p):
        # 開く糸を試す穴。扇は 1 面目に平行に開くので、その両脇の面につなぐ。
        tube.holes += [(A * 1.5, THREAD_DEPTH, 0.6), (A * 3.5, THREAD_DEPTH, 0.6)]
    out.append(tube)
    if p["push_part"] in ("tab", "tube", "stick", RISE):
        # 柄の形の内筒は短い土台（v8）。柄の先を下から差し込んで貼り、台を載せる面にする。
        height, name = (p["stage_height"], "土台") if p["push_part"] == "stick" else (L, "内筒")
        inner = _tube(2, "pusher", name, a, height, p["pusher_glue"], f"2 {name}")
        if p["push_part"] == "tab":
            # 向かい合う 2 面に串を通す穴。1 面だけだと串が傾いて溝の中で引っかかりやすい。
            inner.holes += [(a * 1.5, L / 2, 1.2), (a * 3.5, L / 2, 1.2)]
        if p["push_part"] == RISE:
            # 割り箸を貼る位置の印（制作者の指示 2026-11-06 ③「押し上げは、内筒の内側に割り箸を貼り付ける形にする」）。内筒は谷折りで
            # 刷った面が筒の内になるので、刷った面の 1 面目の真ん中に、割り箸の太さの点の線の長方形を刷る。上の端は台の糊代（内筒の
            # 上の口の内に貼る）の下 CHOPSTICK_GAP から、下の端は内筒の下の端の手前まで（割り箸はそのまま内筒の下へ出る）
            x0, x1 = a / 2 - CHOPSTICK_W / 2, a / 2 + CHOPSTICK_W / 2
            y0, y1 = p["base_glue"] + CHOPSTICK_GAP, L - 0.6
            inner.art.append({"kind": "mark", "pts": [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], "closed": True, "mark": "stick"})
        out.append(inner)
    b, g = p["base_side"], p["base_glue"]
    out.append(Part(3, "base", "扇の台", [
        (g, g), (g + 1, 0), (g + b - 1, 0), (g + b, g), (g + b + g, g + 1), (g + b + g, g + b - 1),
        (g + b, g + b), (g + b - 1, g + b + g), (g + 1, g + b + g), (g, g + b), (0, g + b - 1), (0, g + 1),
    ], label_xy=(g + 1, g + 1), label="3 台",
        valley=[((g, g), (g + b, g)), ((g + b, g), (g + b, g + b)), ((g + b, g + b), (g, g + b)), ((g, g + b), (g, g))],
        glue=[[(g, g), (g + 1, 0), (g + b - 1, 0), (g + b, g)],
              [(g + b, g), (g + b + g, g + 1), (g + b + g, g + b - 1), (g + b, g + b)],
              [(g + b, g + b), (g + b - 1, g + b + g), (g + 1, g + b + g), (g, g + b)],
              [(g, g + b), (0, g + b - 1), (0, g + 1), (g, g)]],
        art=_base_mark(p)))
    if _cradled(p):
        # 筒を外す形の台は、印のある上の面を上にし、糊代を下へ折って伏せて置く。下へ折るのは刷った面の裏へ折る向きなので山折り
        # （今の組の形の台は谷折りのまま。凍結の場面の紙を変えないため。今の形の向きは次の組で見る）。
        # 内筒を下から押し上げる形の台も、印のある上の面を上にして糊代を下へ折り、内筒の上の口に差し込んで蓋にするので同じ山折り
        # （山折りの糊代は斜線の面が外を向き、口に差し込むと斜線の面が内筒の壁に付く）
        out[-1].mountain, out[-1].valley = out[-1].valley, []
    n, w, h = int(p["fold_count"]), p["fold_width"], p["fold_height"]
    outline = [(0, 0), (h, 0), (h, n * w), (0, n * w)]
    glue, leg_valley = [], []
    if _axle(p):
        # ジャバラの固定（v8）。紙で組んで試した時、蛇腹をどこに留めるかで手が止まったので、糊代と貼る位置の印まで型紙で決める。
        # 真ん中の 1 枚を要から下へ伸ばした足にし、先の糊代を 3 台の印に貼る。真ん中が立ったまま、両側の板が開く。
        m, leg = n // 2, leg_length(p)
        outline += [(0, (m + 1) * w), (-leg, (m + 1) * w), (-leg, m * w), (0, m * w)]
        glue.append([(-leg, m * w), (-leg + LEG_GLUE, m * w), (-leg + LEG_GLUE, (m + 1) * w), (-leg, (m + 1) * w)])
        leg_valley.append(((-leg + LEG_GLUE, m * w), (-leg + LEG_GLUE, (m + 1) * w)))
    # 足の折り線は、後で板の折り線が足される valley とは別に取っておく（刷る線を位置で選ぶと、足の長さが糊代と同じ時に x = 0 になって漏れた）。
    leg_folds = list(leg_valley)
    fan = Part(4, "fan", "蛇腹の扇", outline, label_xy=(5, 1.5), label="4 扇", glue=glue, valley=leg_valley)
    for i in range(1, n):
        line = ((0, i * w), (h, i * w))
        # 山と谷を交互にするのが蛇腹の形そのもの。
        (fan.valley if i % 2 else fan.mountain).append(line)
    # 板ごとに 2 色を交互に塗り、色の境で折る（v9）。足は真ん中の板と同じ色にし、糊代は塗らない。
    fan.art = [{"kind": "poly", "pts": [(0, i * w), (h, i * w), (h, (i + 1) * w), (0, (i + 1) * w)], "fill": FAN_A if i % 2 == 0 else FAN_B} for i in range(n)]
    if _axle(p) and leg_length(p) > LEG_GLUE:
        # 足が糊代より短い寸法は F5.fan_leg で落とす。その時に足の絵を描くと形が裏返る（糊代より左から右へ逆に塗る）ので描かない。
        # なお、その寸法では糊代が扇の本体に食い込むので、本体の色の板と糊代が重なり F5.image_box も落ちる（neg_fan_leg が期待する）。
        m, leg = n // 2, leg_length(p)
        fan.art.append({"kind": "poly", "pts": [(-leg + LEG_GLUE, m * w), (0, m * w), (0, (m + 1) * w), (-leg + LEG_GLUE, (m + 1) * w)], "fill": FAN_A if m % 2 == 0 else FAN_B})
    fan.hide_folds = True
    # 足の糊代の境は台に貼る時に折る所で、隣も同じ色なので色の境が無い。組み方の文が「糊代の境の破線で折り」と言うので、
    # この線だけは刷る（作り手の判断。足は台に貼ると隠れるので見た目に効かない）。
    fan.print_folds = leg_folds
    if _axle(p):
        # 中心の穴に糸を通して束ねる。扇の要と同じ形。端の 2 枚の穴は開く糸を試すため。
        r_hole = 2
        fan.holes += [(r_hole, (i + 0.5) * w, 0.6) for i in range(n)]
        fan.holes += [(r_hole + THREAD_RADIUS, 0.5 * w, 0.6), (r_hole + THREAD_RADIUS, (n - 0.5) * w, 0.6)]
    out.append(fan)
    if _cradled(p):
        out.append(_cradle(p))
    if p["push_part"] == RISE:
        out.append(_two_sided_figure(p))
        return out
    fw, fh = p["figure_w"], p["figure_h"]
    pts = [(fw * x, fh * y) for x, y in FIGURE_OUTLINE]
    tab = 5  # 台に貼る足。絵には無いが、立てるのに要る。
    cx0, cx1 = fw * FOOT[0], fw * FOOT[1]
    figure = Part(5, "figure", "像", _insert_tab(pts, cx0, cx1, fh, tab), label_xy=(fw * 0.4, fh * 0.6), label="5",
                  glue=[[(cx0, fh), (cx1, fh), (cx1, fh + tab), (cx0, fh + tab)]],
                  art=_figure_art(fw, fh, pts))
    if _axle(p):
        figure.holes.append((fw / 2, fh - p["pivot_above_rim"], 0.6))
    out.append(figure)
    return out


# 扇の足の先の糊代の長さ。台に貼る面。
LEG_GLUE = 6
# 像の足の糊代を、像の幅のどこからどこまでに取るか。台に貼る幅の検査（F5.figure_base）と同じ値を使う。
FOOT = (0.3, 0.7)


def leg_length(p):
    """扇の足の長さ。要（糸の穴）は像の足元から pivot_above_rim の高さにあり、そこから台まで届かせ、糊代を足す。"""
    return p["pivot_above_rim"] - 2 + LEG_GLUE


def _base_mark(p):
    """3 台の上の面に、扇の足を貼る位置の印（v8）。像の足を貼る真ん中を空けて、奥の縁に寄せる。

    筒を外す形（EP-0017）は、2 受けの底の面を貼る位置の印（受けの幅 × 底の奥行き）を、同じく奥の縁に寄せて刷る。
    """
    if _cradled(p):
        g, b = p["base_glue"], p["base_side"]
        cw, cd = cradle_width(p), cradle_depth(p)
        x0, x1, y0, y1 = g + b / 2 - cw / 2, g + b / 2 + cw / 2, g + 1, g + 1 + cd
        return [{"kind": "line", "pts": [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)], "stroke": LINE, "sw": 0.3},
                {"kind": "line", "pts": [(x0, y0), (x1, y1)], "stroke": LINE, "sw": 0.2}]
    if not _axle(p):
        return []
    g, b, w = p["base_glue"], p["base_side"], p["fold_width"]
    x0, x1, y0, y1 = g + b / 2 - w / 2, g + b / 2 + w / 2, g + 1, g + 1 + LEG_GLUE
    return [{"kind": "line", "pts": [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)], "stroke": LINE, "sw": 0.3},
            {"kind": "line", "pts": [(x0, y0), (x1, y1)], "stroke": LINE, "sw": 0.2}]


def bom(p):
    """部品表。元の素材は絵から読めないので、分からない物は「不明」と書き、歴史の事実として断定しない。"""
    paper = f"紙（厚さ {p['paper_thickness']}mm 前後）"
    why = "家庭のプリンタで刷って作るため"
    rows = [
        {"number": 1, "key": "tube", "name": "外筒", "qty": 1, "material": paper, "substituted": True, "original_guess": "竹（『還魂紙料』を引く解説による。原典は未確認）", "reason": why},
        {"number": 3, "key": "base", "name": "扇の台", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明", "reason": why},
        {"number": 4, "key": "fan", "name": "蛇腹の扇", "qty": 1, "material": paper, "substituted": True, "original_guess": "紙（同じ解説による）", "reason": why},
        {"number": 5, "key": "figure", "name": "像", "qty": 1, "material": paper, "substituted": True, "original_guess": "紙の張貫か木（同じ解説による）", "reason": why},
    ]
    if p["push_part"] == "stick":
        rows.insert(1, {"number": 2, "key": "pusher", "name": "土台", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明", "reason": "柄の先に台を載せて作りやすくするため"})
    if p["push_part"] in ("tab", "tube", RISE):
        rows.insert(1, {"number": 2, "key": "pusher", "name": "内筒", "qty": 1, "material": paper, "substituted": True, "original_guess": "不明", "reason": why})
    if _cradled(p):
        # 筒を外す形（EP-0017）: 内筒・つまみ・糸は無く、2 受けがある。内筒を下から押し上げる形は、内筒（2）の後の 6 受け
        row = {"number": cradle_number(p), "key": "cradle", "name": "扇の受け", "qty": 1, "material": paper, "substituted": True,
               "original_guess": "無し（制作者のレビューで足した。糸の代わりに扇を束ねて開いておく小さい部品）", "reason": why}
        if p["push_part"] == LIFT:
            rows.insert(1, row)
        else:
            rows.append(row)
    if p["push_part"] == RISE:
        # 押す所の割り箸（制作者の指示 2026-11-06 ③）。刷る部品でないので 7 番（6 は受け）。切らずに使う長さで、床（F5.stroke）が
        # 外筒の下に残る長さを見る
        rows.append({"number": 7, "key": "stick", "name": "柄", "qty": 1, "material": f"割り箸 1 本（割った片方。長さ約 {CHOPSTICK_LEN}mm。切らずに使う）",
                     "substituted": True, "original_guess": "不明（実物は筒の下から丸い棒が出ている。素材は写真では読めない）",
                     "reason": "家にあり、内筒を押し上げ・引き下げる力に耐えるため"})
    if p["push_part"] == "tab":
        rows.append({"number": 6, "key": "knob", "name": "つまみ", "qty": 1, "material": f"竹串（長さ約 {p['tube_side'] + 20}mm に切り、先を落とす）", "substituted": True, "original_guess": "不明（絵の細い棒の素材は読めない）", "reason": "家にあり、細くて溝を通るため"})
    if p["push_part"] == "stick":
        rows.append({"number": 6, "key": "stick", "name": "柄", "qty": 1, "material": f"割り箸（長さ約 {p['pusher_height']}mm）", "substituted": True, "original_guess": "不明", "reason": "家にあり、押す力に耐えるため"})
    if _axle(p):
        rows.append({"number": 7, "key": "thread", "name": "糸", "qty": 3, "material": f"たこ糸（軸に 1 本。開く糸を試す時は、さらに 2 本 各約 {thread_mm(p):.0f}mm ＋結ぶ分）", "substituted": True, "original_guess": "不明", "reason": "家にあり、細い穴を通るため"})
    return rows


def thread_mm(p):
    # 高さは筒の穴から測る。穴は口から THREAD_DEPTH 下にあるので、口から測ると糸の長さが最大で約 3mm ずれた。
    z0 = p["pivot_above_rim"] + THREAD_DEPTH
    return shortest_free_thread(p["tube_side"], THREAD_RADIUS, z0 - p["push_amount"], z0)


RESULTS = ("動いた", "動かない", "わからない")


def chopstick_lengths(L, H, base_glue):
    """割り箸を内筒に貼れる長さと、開いた位置で外筒の下へ出る長さ（mm）。

    割り箸は台の糊代（深さ base_glue）の下 CHOPSTICK_GAP から貼る。開いた位置では台の上の面が口の高さなので、割り箸の上の端は
    口から base_glue + CHOPSTICK_GAP 下、下の端はそこから CHOPSTICK_LEN 下。型紙の床（_check_rise）と 3D の確かめ（fold3d.check_rise）が
    この 1 つの式を使う（2 つに書くと判定がずれるため。見直しの指摘）。
    """
    top_depth = base_glue + CHOPSTICK_GAP
    return L - top_depth, CHOPSTICK_LEN - (H - top_depth)


def chopstick_problem(L, H, base_glue):
    """割り箸の決まりの、先の 1 つの崩れの文（無ければ None）。貼れる長さを先に見る（貼れなければ、出る長さを言っても直らない）。"""
    glued, below = chopstick_lengths(L, H, base_glue)
    if glued < CHOPSTICK_GLUE:
        return f"割り箸を内筒に貼る長さ {glued:g}mm が {CHOPSTICK_GLUE}mm に足りず、押すと外れる"
    if below < CHOPSTICK_GRIP:
        return f"割り箸（長さ {CHOPSTICK_LEN}mm の見込み）が、開いた位置で外筒の下へ {below:g}mm しか出ず、{CHOPSTICK_GRIP}mm 残らないので押し引きできない"
    return None


def _check_rise(p):
    """内筒を下から押し上げる形の床。床の名は今の物を使う（凍結の基準の一覧にある名だけを使う）。

    形の見方（高さは外筒の底から。位置の言葉は RISE の注）: 押し上げる量 s は、静かな時の台の上の面から外筒の口までの距離で、
    開いた位置では台の上の面が口の高さに来る（内筒を下から押す形と同じ見方）。静かな時の台の上の面は H − s、内筒はその下へ長さ L だけ伸びる。
    - 静かな時に、受けの底の紙と畳んだ扇と像が、口から 2mm 下に隠れる（F5.fan_height・F5.figure_height）。
    - 内筒は、静かな時も開いた位置も、外筒に内筒の一辺以上入っている（傾かない）。静かな時に外筒に入っているのは min(L, H − s)、
      開いた位置では min(L, H) で、静かな時の方が短い（F5.stroke）。v13 から押す所は割り箸なので、内筒は外筒の下へ出さなくてよい。
    - 割り箸（長さ CHOPSTICK_LEN の見込み）は、台の糊代の下から内筒の内の面に沿って貼り、内筒の下を通って外筒の下へ出る。
      内筒に貼る長さが CHOPSTICK_GLUE 以上で、開いた位置でも外筒の下へ CHOPSTICK_GRIP 以上残る（F5.stroke。静かな時はさらに s 長く出る）。
    - 台は、印の面を上にして糊代を下へ山折りし、内筒の上の口に差し込んで、糊代を内筒の内の面に貼る（蓋をする）。山折りの糊代は
      刷った面（糊代の斜線）が外を向くので、口に差し込むと斜線の面が内筒の壁に付く（かぶせると斜線の裏が壁に付き、斜線に糊を付けると
      貼れない。見直しの指摘）。台の一辺は、内筒の一辺より糊代の紙 2 枚分以上小さく、1mm より小さくない（F5.base_size）。
    - 扇の下の端（要）は台の上の面にあり、開いた位置で口の高さに来る（押し過ぎると口より上）。扇は台の縁と口の角より下へは開けないので、開く角の見込みの
      上限（帯の長さ ÷ 板の高さ）が、要から台の縁・口の角を見た角（ほぼ 180°）に収まる（F5.fan_clearance）。
      実物の写真の扇（約 300° 開く）は、要が像の首の高さにある。要を上げる柱の部品（案 B）は、この形を紙で確かめた後に入れる。
    """
    out = []
    H, A, a, b = p["tube_height"], p["tube_side"], p["pusher_side"], p["base_side"]
    s, L, h, t = p["push_amount"], p["pusher_height"], p["fold_height"], p["paper_thickness"]
    if s < t + h + 2:
        out.append(Failure("F5.fan_height", "蛇腹の扇", f"受けの底の紙 {t:g}＋扇の高さ {h}＋2 が押し上げる量 {s} を超え、静かな時に扇が口から出る"))
    if p["figure_h"] > h + 6:
        out.append(Failure("F5.figure_height", "像", f"像の高さ {p['figure_h']} が折りの高さ＋6={h + 6} を超える"))
    if s < p["figure_h"] + 2:
        out.append(Failure("F5.figure_height", "像", f"像の高さ {p['figure_h']}＋2 が押し上げる量 {s} を超え、静かな時に像が口から出る"))
    if s > H:
        # 台が筒の下に出る寸法は、入る長さが負になるので、傾きの文でなく、この文で言う（見直しの指摘: 「-1mm しか差し込まれず」と言った）
        out.append(Failure("F5.stroke", "内筒", f"押し上げる量 {s} が筒の高さ {H} を超え、静かな時に台が筒の下に出る"))
    elif min(L, H - s) < a:
        out.append(Failure("F5.stroke", "内筒", f"静かな時に内筒が外筒に {min(L, H - s):g}mm しか入らず、一辺 {a} より短いので傾く"))
    problem = chopstick_problem(L, H, p["base_glue"])
    if problem:
        out.append(Failure("F5.stroke", "割り箸", problem))
    if not a < A - 1:
        out.append(Failure("F5.slide_clearance", "内筒", f"内筒 {a} は外筒 {A} − 1 より小さくない"))
    # 台は内筒の上の口に差し込み、糊代を内筒の内の面に貼る。口に入る（糊代の紙 2 枚の分だけ小さい）と、糊代が内筒の壁に届く（1mm より
    # 小さくない）の間。台は内筒の内に入るので、外筒の中を滑るかは内筒の遊び（F5.slide_clearance）だけで決まる
    if not a - 1 <= b <= a - 2 * t:
        out.append(Failure("F5.base_size", "扇の台", f"扇の台 {b} が、内筒 {a} の上の口に差し込めて糊代が内の面に届く大きさ（{a - 1:g}〜{a - 2 * t:g}）でない"))
    if cradle_width(p) > b - 2 or cradle_depth(p) + 2 > b / 2:
        out.append(Failure("F5.base_size", "受け", f"受け（幅 {cradle_width(p):g}・奥行き {cradle_depth(p):.1f}）が台の奥の半分（{b / 2:g}）に乗らない"))
    thick = p["fold_count"] * t
    if thick > A - 2 - 2 * CRADLE_ROOM:
        out.append(Failure("F5.fan_thickness", "蛇腹の扇", f"畳んだ厚さ {thick:.1f} が筒の一辺 {A} に収まらず、受けごと筒に入らない"))
    if p["fold_width"] > A - 2:
        out.append(Failure("F5.fan_thickness", "蛇腹の扇", f"畳んだ扇の幅 {p['fold_width']} が筒の一辺 {A}−2 を超え、筒に入らない"))
    foot = p["figure_w"] * (FOOT[1] - FOOT[0])
    if foot > b:
        out.append(Failure("F5.figure_base", "像", f"像の足の糊代 {foot:.1f} が扇の台 {b} より広く、台に貼れない"))
    if p["figure_w"] > A - 2:
        out.append(Failure("F5.figure_base", "像", f"像の幅 {p['figure_w']} が筒の一辺 {A}−2 を超え、筒に入らない"))
    # 要は台の上の面から受けの底の紙の厚さ t 上。開いた位置で台の上の面が口の高さに来るので、台の縁（一辺 b）も口の角（一辺 A）も要の t 下。
    # 止めが無いので押し過ぎると台は口より上へ出るが、その時は口の角が要よりさらに下になり、開ける角は台の縁で決まるので、開いた位置で見れば足りる
    bound = opening_bound_deg(p["fold_count"], p["fold_width"], h)
    limit = min(clearance_limit_deg(A, t), clearance_limit_deg(b, t))
    if bound > limit:
        out.append(Failure("F5.fan_clearance", "蛇腹の扇", f"帯の長さでは {bound:.0f}° 開くが、扇の下の端が台の上にあるので、台の縁と筒の口の角に当たって {limit:.0f}° までしか開けない"))
    return out


def materials(p):
    """型紙の「用意する物」。素材は部品表だけから刷り、2 か所に手で書かない。"""
    rows = bom(p)
    # 穴があるのに竹串の行が無い形（内筒を下から押す形・柄の形）は、穴をあける竹串を道具に書く（手順に「穴は竹串の先であける」。
    # 制作者の確認 2026-11-06）。つまみの形は竹串の行がもう有る。
    # 部品を組まずに形の値で決める（穴は、軸の形の開く糸・扇・像の穴と、竹串の行のあるつまみの形の穴だけなので、同じ答えになる。
    # 部品から決めた答えと同じ事は試験で見る）。用意する物は、記録の寸法（字の形の寸法が混ざりうる）で読む一覧からも呼ばれうるので、
    # 部品を組んで落ちないようにする（写し先の repo で、作り方の印の一覧が記録を読んで落ちたため）
    tools = "のり、はさみ、定規"
    if _axle(p) and not any("竹串" in r["material"] for r in rows):
        tools += "、竹串（穴あけ）"
    if p["push_part"] == RISE:
        # 割り箸は木で糊が付きにくいので、内筒にはセロハンテープで留める（組み方の文と同じ）
        tools += "、セロハンテープ（割り箸を留める）"
    lines = [f"{rows[0]['material']}を 1 枚（全部品を同じ紙に刷る）", tools]
    # 6 番は紙でない棒（竹串・割り箸）の行。内筒を下から押し上げる形の 6 受けは紙の部品で、1 枚目の紙の行に入るので書かない
    lines += [f"{r['material']} {r['qty']} 本" for r in rows if r["number"] == 6 and r["key"] != "cradle"]
    lines += [r["material"] for r in rows if r["number"] == 7]
    return lines


TITLES = {"tab": "つまみで動かす", "tube": "内筒を下から押す", "stick": "割り箸の柄で動かす", "lift": "筒を外すと扇が開く",
          "rise": "内筒を下から押し上げる"}


def title(p):
    return TITLES[p["push_part"]]


def place(by_key, page, top, gap):
    """扇は長いので右の列に縦に置き、残りを左の列に積む。返り値は (文字の開始 y, 文字の幅, 文字の開始 x)。"""
    fan = by_key["fan"]
    # 扇の足（v8）は部品の原点より左に出るので、右端をそろえて置く。
    minx = min(x for x, _ in fan.outline)
    fan.x, fan.y = page.x1 - fan.width - minx, top
    left_y = top
    for key in ("tube", "pusher"):
        if key in by_key:
            q = by_key[key]
            q.x, q.y = page.x0, left_y
            left_y += q.height + gap
    base, fig = by_key["base"], by_key["figure"]
    if "pusher" in by_key and "cradle" in by_key:
        # 内筒を下から押し上げる形（rise）は、外筒と内筒で左の列が長くなりやすい（v12 は内筒が外筒より長かった）。扇は短い（ほぼ
        # 180° に収まる枚数）ので、台・像・受けの段を右の列の扇の下に置く。左の列の筒の網と横に並ばない時は、前と同じく左の列に積む
        c = by_key["cradle"]
        row_w = base.width + gap * 2 + fig.width + gap * 2 + c.width
        row_x = page.x1 - row_w
        if row_x - gap >= max(by_key[k].x + by_key[k].width for k in ("tube", "pusher")):
            row_y = fan.y + fan.height + gap
            base.x, base.y = row_x, row_y
            fig.x, fig.y = row_x + base.width + gap * 2, row_y
            c.x, c.y = fig.x + fig.width + gap * 2, row_y
            # 文字は左の列の筒の下から刷るが、文字の列は右の段の下まで横に伸びるので、段の下の端より下から始める
            # （筒が短く扇が長い寸法で、文字が段に重なった。見直しの指摘）
            row_bottom = row_y + max(base.height, fig.height, c.height)
            if row_bottom + gap > left_y:
                # 扇が長くて右の段が左の列より下まで来る時（v14 の折り 44 枚）は、段の下から刷ると紙の下に出る。文字の列の幅を段の左までに
                # 狭めて、左の列の筒の下から刷る（狭めた幅で行が折り返して段の下より長くなれば、配置の検査が落とす）。段が左の列より
                # 上で終わる寸法（v13 まで）は、前と同じ所から刷る（刷った紙を変えない）
                return left_y, row_x - page.x0 - gap, page.x0
            return max(left_y, row_bottom + gap), fan.x - page.x0 - gap, page.x0
    base.x, base.y = page.x0, left_y
    fig.x, fig.y = page.x0 + base.width + gap * 2, left_y
    row = max(base.height, fig.height)
    if "cradle" in by_key:
        # 2 受け（筒を外す形、EP-0017）は小さいので、像の右に置く（左の列の高さを増やさない）
        c = by_key["cradle"]
        c.x, c.y = fig.x + fig.width + gap * 2, left_y
        row = max(row, c.height)
    left_y += row + gap
    # 文字の列の幅は扇の本体まで取る。足は真ん中の 1 枚の高さにしか無く、文字と重なれば配置の検査（F5.overlap）が落とす。
    return left_y, fan.x - page.x0 - gap, page.x0


def _steps(p):
    """組み方の (手順の文, 3D の操作の種類) の並び。種類は、3D の操作から作った手順だけに付く（ほかは None）。

    文と操作の種類を 1 つの並びで持つのは、omochae.fold3d が確かめた操作の手順の番号を、文を突き合わせずに引けるようにするため
    （浮き人形の _steps が、文と直しの行き先を 1 つの並びで持つのと同じ考え。文の突き合わせは、文の小さな直しで黙って外れる）。
    つまみの形は、3D で組める部品（外筒・内筒・竹串）の手順を、3D の操作から作る（制作者の決定 2026-11-06。omochae.ops3d）。
    文は型紙のデータから作るので、折り方のデータを直すと文も変わる。ほかの手順と、ほかの形の手順は文のまま。
    """
    if p["push_part"] == RISE:
        # 内筒を下から押し上げる形の組み方。新しい形なので手順の番号は新しく振る（この形の報告の鍵はまだ無い）。
        # 最後は、内筒を下から押し上げると扇が口から出て開き、引き下げると畳まれて筒に入る動き（制作者の決定 2026-11-06）
        # 作る順（切る → 部品ごとに折る → 貼る → 組む → 押し上げる）のとおりに並べ、1 つの段に 1 つの動きにする（作った人の報告で、
        # 折る順と貼る順が分かりにくかったため）。割り箸は、内筒を筒に貼る前に、平らなまま刷った面の印に貼る（筒にした後では手が
        # 入らない）。押す時は、外筒を片手で持ち、もう片方の手で割り箸をゆっくり押し上げる（持たずに動かすと扱いにくかったため。
        # 止めが無いので、手を離すと内筒は下へ抜ける）。像は頭の上で折って裏どうしを貼り、両側に顔を出す（_two_sided_figure）
        return [(s, None) for s in (
            "刷った物差しに定規を当て、10cm か確かめる",
            "部品を全部、実線で切る（穴はあけない）",
            "1 外筒を、色の境で 4 回山折りする",
            "1 外筒の糊代を、反対の端の面の裏に貼って角筒にする",
            "2 内筒を、破線で 4 回谷折りして、平らに戻す（まだ貼らない）",
            "割り箸を、2 内筒の刷った面の点の線の長方形に沿って置き、上の端を長方形の上の端にそろえて、セロハンテープで 2〜3 か所留める（下の端は内筒の下へ出す）",
            "2 内筒の糊代を、反対の端の面に貼って角筒にする（割り箸は筒の内に入る）",
            "3 台の 4 つの糊代を、山折りの線で下へ折る",
            "3 台を、印のある上の面を上にして 2 内筒の上の口に差し込み、糊代を内筒の内の面に貼る（蓋をする）",
            "4 扇を色の境で、端から谷折り・山折りを交互にして蛇腹に畳む",
            "6 受けを、2 本の破線で谷折りして U の字にする",
            "6 受けの底の面の裏を、3 台の印に貼る",
            "畳んだ 4 扇の下の端を 6 受けに入れ、扇の下の端を受けの底に、扇の両端の板の下の所を受けの左右の面に貼る（受けの刷った面は全部が糊代）",
            "5 像を、頭の上の山折りの線で後ろへ折り、裏どうしを糊で貼り合わせる（前と後ろの両方に顔が出る）",
            "5 像の足の糊代を後ろへ折り、3 台の受けの前に貼る",
            "4 扇を手で畳み、2 内筒を台の側から 1 外筒の下の口に入れ、扇と像が筒に隠れる所まで差し込む（割り箸は外筒の下に出る）",
            "1 外筒を片手で持ち、もう片方の手で割り箸をゆっくり押し上げると、扇が筒の口から出て開く",
            "割り箸をゆっくり引き下げると、扇は口の縁で畳まれて筒に入る（手を離すと内筒が下へ抜けるので、外筒と割り箸を一緒に持つ）",
        )]
    if p["push_part"] == LIFT:
        # 筒を外す形（EP-0017）の組み方。新しい形なので手順の番号は新しく振る（この形の報告の鍵はまだ無い）。
        # 最後は制作者の言い方の動き（筒を上へ外すと扇が開く）
        return [(s, None) for s in (
            "刷った物差しに定規を当て、10cm か確かめる",
            "部品を実線で切る（穴はあけない）",
            "1 外筒を色の境で山折りし、糊代で貼って角筒にする",
            "3 台の 4 つの糊代を山折りの線で下へ折り、伏せて机に置く（印のある上の面が台になる）",
            "4 扇を色の境で、端から谷折り・山折りを交互にして蛇腹に畳む",
            "2 受けを 2 本の破線で谷折りして U の字にし、底の面の裏を 3 台の印に貼る",
            "畳んだ 4 扇の下の端を 2 受けに入れ、扇の下の端を受けの底に、扇の両端の板の下の所を受けの左右の面に貼る（受けの刷った面は全部が糊代）",
            "5 像の足を、3 台の受けの前に貼る",
            "4 扇を手で畳み、上から 1 外筒をかぶせる。筒を上へ外すと、扇が開く",
        )]
    # 3D の操作から作った文。つまみの形だけ（手順の文を 3D の操作から作るのは、まだこの形だけ。rise は 3D で確かめるが、文は手で書く）
    made = dict(assembly_ops(parts(p), p)) if p["push_part"] == "tab" else {}

    def op(kind, text):
        return (made[kind], kind) if kind in made else (text, None)
    # まず筒を 1 つ作る（v8）。紙で組んで試した時、手が止まりやすいのは平面から立体への最初の一歩だったので、
    # 最初に形が 1 つできる順にする。
    out = [("刷った物差しに定規を当て、10cm か確かめる", None)]
    if p["push_part"] == "tab":
        out.append(("まず 1 外筒だけを実線で切る。溝は下の端からはさみで切り込む（くり抜かない）", None))
    else:
        out.append(("まず 1 外筒だけを実線で切る", None))
    out.append(op("fold_outer", "1 外筒を色の境で山折りし、糊代で貼って角筒にする"))
    out.append(("残りの部品を実線で切る。穴は竹串の先であける", None))
    if p["push_part"] in ("tab", "tube"):
        # 外筒を山折りに直した時、「同じように」だと、破線を谷折りで刷る内筒と食い違うので、制作者の決定（2026-11-06）の文にした
        out.append(op("fold_inner", "2 内筒は破線で谷折りし、糊代で貼って角筒にする"))
    if p["push_part"] == "tab":
        out.append(op("thread", None))
    if p["push_part"] == "stick":
        # 外筒を山折りに直した後は「同じように」が山折りと読めて、破線を谷折りで刷る土台と食い違うので、手順 2 と同じ型の文にした（制作者の確認 2026-11-06）
        out.append(("2 土台は破線で谷折りし、糊代で貼って角筒にし、割り箸の先を下から差し込んで貼る", None))
    out.append(("3 台で 2 の上に蓋をする", None))
    out.append(("4 扇を色の境で、端から谷折り・山折りを交互にして蛇腹に畳む", None))
    if _axle(p):
        out.append(("糸を 5 像の穴と 4 扇の中心側の穴の列に通し、ゆるく結ぶ", None))
        out.append(("4 扇の真ん中の足を、糊代の境の破線で折り、足の糊代を 3 台の印に貼る", None))
        out.append(("5 像の足を 3 台に貼る", None))
    else:
        out.append(("4 扇の端を 3 台に貼り、5 像の足も台に貼る", None))
    if p["push_part"] == "tab":
        out.append(op("insert", None))
        # 組み立ての最後の動き（制作者の追加 2026-11-06「上にスライドさせて蛇腹が開く所まで」）。今の手順の後ろに足すので、
        # 前の手順の番号はずれない（作った人の報告は手順の番号を鍵にしている）
        out.append(op("push", None))
    else:
        out.append(("押す部品を 1 外筒に下から入れる", None))
    return out


def steps(p):
    """組み方。部品番号は型紙と同じ。押し方と中心の置き方で変わる所だけを分ける（作り方は _steps）。"""
    return [text for text, _ in _steps(p)]


def step_ops(p):
    """3D の操作の種類ごとの、手順の番号（1 から）。omochae.fold3d が、確かめた操作の手順の番号を所見に添えるのに使う。"""
    return {kind: i for i, (_, kind) in enumerate(_steps(p), 1) if kind}


def measures(p):
    """「作る前に」の問いと、試した事の欄（元の repo の手順の紙が使っていた。手順の紙は廃止し（制作者の決まり 2026-11-06「文章のプリントは廃止。組み立て用のページだけでいい。」）、サイトの組み立ての頁で使う。この repo に手順の紙は無い）。

    開き具合の角度と回数は欄を置かない。予想は数でなく、動き方を言葉か絵で書く（元の repo に合わせた）。
    """
    return {"predict": "押すと、どこがどう動くと思いますか（言葉か絵で）", "rows": []}


def diagram(x, y, w, h, p):
    """組み上がりの断面の見取り図。寸法の図ではなく、部品の並びを見せるだけの絵。"""
    s = (h - 8) / (p["tube_height"] + p["fold_height"])
    cx, base = x + w / 2, y + h - 4
    tw, th = p["tube_side"] * s, p["tube_height"] * s
    shapes = [{"kind": "rect", "x": cx - tw / 2, "y": base - th, "w": tw, "h": th}]
    inner = p["pusher_side"] * s
    rest_top = base - (p["tube_height"] - p["push_amount"]) * s
    length = p["pusher_height"] * s
    if p["push_part"] == "stick":
        stage = p["stage_height"] * s
        shapes.append({"kind": "rect", "x": cx - inner / 2, "y": rest_top, "w": inner, "h": stage, "dash": "1,0.6"})
        # 割り箸は筒の下へ出るが、絵の枠（y+h）の中で止める。枠の外へ出ると下の説明と重なる。
        shapes.append({"kind": "rect", "x": cx - 0.6, "y": rest_top + stage, "w": 1.2, "h": max(0.0, min(length - stage, y + h - rest_top - stage)), "dash": "1,0.6"})
    else:
        shapes.append({"kind": "rect", "x": cx - inner / 2, "y": rest_top, "w": inner, "h": length, "dash": "1,0.6"})
    if p["push_part"] == "tab":
        shapes.append({"kind": "line", "x1": cx - tw / 2 - 5, "y1": rest_top + length / 2, "x2": cx, "y2": rest_top + length / 2})
    shapes.append({"kind": "rect", "x": cx - 1.2, "y": rest_top - p["fold_height"] * s, "w": 2.4, "h": p["fold_height"] * s, "dash": "1,0.6"})
    return shapes
