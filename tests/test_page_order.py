"""玩具の頁の本体は 原画と立体 → つくる → 型紙 の順だけにし、読み物と作る側の節は見出しのまま畳む。

なぜ: 本人のサイト体験レビュー（11-07）の 3「作るの頁がごちゃごちゃして、同じ物が何回も出る。まとめる」。前は「すぐ作る」の節
（見出し・説明・断り・輪の図・立体・仮説の札）と「型紙の窓」が別にあり、作る節と型紙の置き場が 2 つに見え、組み方も 頁の立体・組み方の節・手帖
と重なっていた。立体は頭の原画のすぐ後、説明の文と断りと輪の図と仮説の札は型紙の窓の頭（「すぐ作る」の見出しは外す）、組み方の節は畳む。輪の図は版の印と並ぶ所なので本体に残す。
他の人が作った物の節（#minna）は、自分の記録の口と同じ節なので、残す口の形が決まるまで動かさない（今の場所のまま見る）。
"""
import os
import re
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ.pop("ANTHROPIC_API_KEY", None)

from omochae import hypotheses  # noqa: E402
from web import kumitate  # noqa: E402
from web.play_server import print_latest  # noqa: E402
from web.toy import toy_page  # noqa: E402

TOYS = ("NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R")
ORDER = ("kasetsu", "win", "hanasu", "tsukuru", "kumikata", "kiroku", "minna", "tatoe", "kaizen", "english")
GONE = ("<h2>すぐ作る</h2>",)


def section(page, name):
    """その id の節（次の節の頭まで）。"""
    a = page.index(f'id="{name}"')
    b = page.find("<section", a + 1)
    return page[a:b if b > 0 else len(page)]


for sid in TOYS:
    for printed in (False, True):
        if printed:
            assert print_latest(sid, hypotheses.sheet_of(sid)["id"]) is not None, (sid, "紙を作れない")
        page = toy_page(sid)
        where = f"{sid} {'刷った後' if printed else '刷る前'}"
        # 並び: 頭（題と つくる）→ 立体 → 型紙の窓 → 考えを話す → 困った時 → 組み方 → 記録 → 他の人が作った物 → たとえ → 改善の輪 → 英語
        at = [page.index(f'id="{name}"') for name in ORDER]
        assert page.index("<h1>") < at[0] and at == sorted(at), (where, dict(zip(ORDER, at)))
        for gone in GONE:
            assert gone not in page, (where, gone)
        # 立体は頭のすぐ後の節に。型紙の窓より前
        if kumitate.available(sid):
            assert 'id="kumitate"' in section(page, "kasetsu"), (where, "立体が頭の後に無い")
        # 型紙の窓の頭に、断り → 輪の図 → 仮説の札（紙は札の後）
        win = section(page, "win")
        heads = [win.index(x) for x in ('<h2>型紙の窓</h2>', '型紙を刷ります。切って、折って、組みます。', 'id="premise"', 'id="wa"', 'class="plates"')]
        assert heads == sorted(heads), (where, heads)
        assert hypotheses.sheet_of(sid)["name"] in win, where
        if printed:
            assert win.index('class="plates"') < win.index('<figure class="sheet">'), (where, "紙が札より前")
        assert page.count('id="wa"') == 1 and page.count('id="premise"') == 1, where
        # 読み物と作る側の節は見出しのまま畳む（組み方・たとえ・改善の輪）
        for name, head in (("kumikata", "組み方"), ("tatoe", "たとえと、関連する事柄"), ("kaizen", "型紙の改善の輪")):
            assert re.search(rf'<details class="fold-sec"><summary><h2>{head}</h2></summary>', section(page, name)), (where, name)
print(f"ok 玩具の頁の並び: {len(TOYS)} 種の刷る前と後で、原画 → 立体 → 型紙の窓（断り・輪の図・札・紙）→ 考えを話す、組み方・たとえ・改善の輪は畳む")
