"""玩具 1 つに型紙 1 枚（たたき台）の決まり。

制作者の決定（2026-11-05 17:26）「型紙は説を羅列せず、おもちゃ一個につき一個にする。理由はその型紙が完璧ではないから。
その型紙をたたき台に色々試行錯誤する」による。
判断の芯:
- 玩具は「出典（source_id）と、描かれた物」で数える。同じ出典で動き方の読みだけが違う形は、同じ玩具の別の読みと見て、
  1 つだけを型紙（sheet）にし、ほかは試行錯誤のヒント（reading_of で型紙の形を指す）に回す。
  同じ出典でも描かれた物が違う形（stand_figure の凧 2 つ・土人形 3 つ）は、別の玩具なので、どれも型紙のまま。
- 型紙の 1 枚は、制作者が決めた物（御来迎は内筒を下から押し上げる形 rise（2026-11-06）、首振り虎は元の repo の先頭の仮説 H-A）、
  無ければ雛形の今の既定の形。必須 2 種の紙も、この型紙の 1 枚で刷る（御来迎 examples/goraigo_v14.json・首振り虎 pos_tiger_neck）。
  どれも「答え」ではなく、たたき台。
- 御来迎は、型紙の 1 枚（rise）が雛形の既定の形（tab）と違う。既定を替えると、tab を既定で刷る凍結の場面（pos_tab ほか）の紙が
  変わるので、既定は tab のままにし、型紙の 1 枚はこの表だけで決める。rise には凍結の場面が無い（凍結の置き場は足さない）ので、
  必須の紙は examples の場面（次の組 goraigo-v14 の寸法）で刷る。rise は寸法ごと書く形で、既定の寸法（つまみの形の物）に形だけ rise を
  入れると床に落ちる。一覧（omochae.ways）は形の名だけを出すので、サイトは型紙の 1 枚を刷る時、この場面の寸法を使う（次の組の記録に写す）。
- 別の読みの形は消さない（凍結の場面と試験が使い、作る人が試行錯誤する時のヒントになる）。一覧（omochae.ways）で印を付け、
  サイトは型紙の 1 枚だけを出す。
- 表をここ 1 か所に置くのは、雛形の決まり（tests/test_template_contract.py）を増やさず、1 枚の選び直しを 1 行で済ませるため。
"""
from .compose import TEMPLATES

# 必須 2 種の紙を刷る場面（repo の根からの道）。どちらも、その玩具の型紙の 1 枚で刷る。試験（tests/test_sheets.py の 3・
# tests/test_pdf_repeatable.py）は、この表を 1 か所の正として使う（2 つの試験に同じ表を書くと、片方だけ直し忘れたため。見直しの指摘）
REQUIRED = {"slider_fan": "examples/goraigo_v14.json", "pivot_counterweight": "tests/frozen/scenarios/pos_tiger_neck.json"}

# 雛形 → {別の読みの形: 型紙の形}。ここに無い形は、どれも型紙（その玩具の 1 枚）。
READINGS = {
    # 御来迎（R5-L・必須の 1 つ）: 押し方の読み。たたき台は rise（内筒を下から押し上げる。扇は糸を使わず受けで束ねる）。
    # 制作者の決定（2026-11-06）「筒を外す形（lift）はやめる。下から押し上げるバージョンを作る。側面のつまみのバージョンは廃止。内筒を付ける。」と、前の決定「糸なしでやります」による。
    # 前のたたき台 tab（側面のつまみ。元の repo の H-A。制作者の決定 2026-11-05）と、tube・stick・lift（筒を外す形。やめた）は
    # 試行錯誤のヒント。凍結の場面 pos_tab と 3D の確かめ（fold3d。凍結の基準で tab の形だけを組む）は tab のまま残る
    "slider_fan": {"tab": "rise", "tube": "rise", "stick": "rise", "lift": "rise"},
    # 首振り虎（R14-R・必須の 1 つ）: 頭の支え方の読み。たたき台は neck（首を胴の穴に入れる。元の repo の H-A）。
    # 制作者の決定（2026-11-05）で H-A に決まった。必須の紙もこの形（pos_tiger_neck）で刷る。hang（頭を前に吊る）はヒント
    "pivot_counterweight": {"hang": "neck"},
    # 猫と鼠の箱: 何が滑るかの読み。既定の lid（図にいちばん近い読み）を型紙に
    "slide_box": {"sleeve": "lid"},
    # 壺から飛び出す人形: 壺の面の数の読み。既定の square を型紙に
    "popup_jar": {"hex": "square"},
    # 浮き人形: 風受けを足すかの読み。既定の none を型紙に
    "float": {"cups": "none"},
}


def source_of(template_id, form):
    """形の出典の ID。刷る形ごとに出典が違う雛形（SOURCES）は形から、ほかは雛形の SOURCE。"""
    tpl = TEMPLATES[template_id]
    return getattr(tpl, "SOURCES", {}).get(form, tpl.SOURCE)


def reading_of(template_id, form):
    """別の読みの形なら、型紙の形。型紙なら None。"""
    return READINGS.get(template_id, {}).get(str(form))


def is_sheet(template_id, form):
    return reading_of(template_id, form) is None
