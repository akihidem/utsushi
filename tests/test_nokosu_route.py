"""のこすへの 2 つの道の字（本人の言葉 11-07 夜「つくるところからのこせます、できたはのこそう、の二つの経路を用意してのこすに行くようにしたい。
リンクが埋もれててわかりにくい…簡単な意義も話しながら誘導する」。UX の担当の案の「今夜の形」）。

なぜ: のこすへの道は頁の下の方の #kiroku に 1 本だけで、組み方の畳みの後に埋もれていた。並び・道・錨は替えず、字を足して道を見つけやすくする。
見る線:
- 道 1 の 1 行と意義は、型紙の窓の「つくる」（手帖へ行く釦）のすぐ下に 1 回ずつ。釦の行き先は今の手帖のまま。
- 道 2 の見出しと意義は、#kiroku の節の、のこすへの道の上に 1 回ずつ。道の字と行き先（記録の頁）は替えない。
- 手帖の最初の画面には今夜は足さない。最初の画面は手順の文のほかの字のかたまりが 3 つまで（test_techo_step）で、重ねる頁への道のある御来迎と虎は
  もう 3 つ（声の断り・「はじめる」・カメラに重ねる）あり、1 行足すと 4 つになった（UX の担当の案の「入らなければ外す」の当てはめ）。
- 意義は新しい字にせず、のこす の画面の枠の 1 行目（naoru.LINES[0]）と同じ字。字を空にすると、その道の字は出ず、頁は前と同じ。
（狭い画面で「はじめる」が最初の画面に入る事は test_hmd が測る。英語は test_en_all が見る）
"""
import os
import re
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ.pop("ANTHROPIC_API_KEY", None)

from omochae import hypotheses  # noqa: E402
from web import naoru, techo_step, toy  # noqa: E402
from web.play_server import print_latest  # noqa: E402

TOYS = ("NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R", "NDL-1187053-R0000004-L")
MAKING, DONE, WHY = naoru.ROUTE_MAKING, naoru.ROUTE_DONE, naoru.LINES[0]
assert naoru.purpose() == WHY, "意義は のこす の画面の枠と同じ字"


def section(page, name):
    """その id の節（次の節の頭まで）。"""
    a = page.index(f'id="{name}"')
    b = page.find("<section", a + 1)
    return page[a:b if b > 0 else len(page)]


for sid in TOYS:
    hid = hypotheses.sheet_of(sid)["id"]
    assert print_latest(sid, hid) is not None, (sid, "紙を作れない")
    page = toy.toy_page(sid)
    # 道 1: 型紙の窓の「つくる」のすぐ下に、1 行と意義
    win = section(page, "win")
    go = f'<p class="road"><a class="btn" href="/toy/{sid}/techo">つくる</a></p>'
    after = f'<p class="meta nokosu-route">{MAKING}</p><p class="meta nokosu-route">{WHY}</p>'
    assert win.count(go + after) == 1, (sid, "道 1 は窓の「つくる」のすぐ下")
    assert page.count(MAKING) == 1, (sid, "道 1 の字は玩具の頁に 1 回")
    # 道 2: #kiroku の節の、今の道の上に見出しと意義。道の字と行き先は替えない
    kiroku = section(page, "kiroku")
    road = f'<p class="links"><a href="/toy/{sid}/techo/kiroku">{toy.KIROKU_TO_NOKOSU}</a></p>'
    assert f"<h2>{DONE}</h2><p class=\"meta\">{WHY}</p>{road}" in kiroku, (sid, "道 2 は のこすへの道の上")
    assert page.count(DONE) == 1 and page.count(toy.KIROKU_TO_NOKOSU) == 1, sid
    # 手帖の最初の画面には足さない（字のかたまりが 3 つまでの決まりを崩さない）
    assert MAKING not in techo_step.page(sid, [hid]), (sid, "手帖の最初の画面には今夜は足さない")

# 字を空にすると、その道の字は出ず、頁は前と同じ（本人の確かめで字を外す時の形）
sid = TOYS[0]
hid = hypotheses.sheet_of(sid)["id"]
with_route = toy.toy_page(sid)
keep = naoru.ROUTE_MAKING, naoru.ROUTE_DONE
naoru.ROUTE_MAKING = naoru.ROUTE_DONE = ""
try:
    bare = toy.toy_page(sid)
finally:
    naoru.ROUTE_MAKING, naoru.ROUTE_DONE = keep
assert "nokosu-route" not in bare and f"<h2>{DONE}</h2>" not in bare
assert re.sub(r'<p class="meta nokosu-route"[^>]*>[^<]*</p>|<h2>' + DONE + r'</h2><p class="meta">' + re.escape(WHY) + "</p>", "", with_route) == bare, "字を外すと頁は前と同じ"
print("ok")
