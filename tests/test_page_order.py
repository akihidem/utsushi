"""玩具の頁の本体の並びと、読み物と作る側の節を見出しのまま畳む事（並びは本人の言葉 11-08 で替わった。下の注）。

なぜ: 本人のサイト体験レビュー（11-07）の 3「作るの頁がごちゃごちゃして、同じ物が何回も出る。まとめる」。前は「すぐ作る」の節
（見出し・説明・断り・輪の図・立体・仮説の札）と「型紙の窓」が別にあり、作る節と型紙の置き場が 2 つに見え、組み方も 頁の立体・組み方の節・手帖
と重なっていた。立体は頭の原画のすぐ後、説明の文と断りと輪の図と仮説の札は型紙の窓の頭（「すぐ作る」の見出しは外す）、組み方の節は畳む。輪の図は版の印と並ぶ所なので本体に残す。
11-08 の本人の言葉 477 で並びを替えた: 仮説 → たとえ → 立体 → 型紙の窓（型紙 → 版の歩み → 窓の口）→ のこそう。これまでの復元（#minna）は もちよる へ移し、
組み方と困ったらは外した（作る時は手帖が 3D と文で 1 手ずつ出す）。
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
# 並びは本人の言葉 11-08（477）「原図をみて、狂歌を読んで、仮説、たとえ、3D をみたあとに型紙の印刷にすすむ。…できたら完成形を記録するために、のこすにいく。」と、
# 設計の 9 つの問いの答え「推しのとおり。」: 仮説（中に考えを話す）→ たとえ → 立体 → 型紙の窓（中に 型紙 → 版の歩み → 窓の口）→ のこそう → 英語。
# これまでの復元（#minna）は もちよる へ・組み方（#kumikata）と困ったら（#tsukuru）は外した。前の並び（394・469）はこの言葉で替わった。
# 頁の足の「型紙の改善の輪」（#kaizen）は外したまま（本人の答え 11-07 夕の Q5。作る側の様子の頁へ移した）
ORDER = ("kasetsu-fuda", "hanasu", "tatoe", "kasetsu", "win", "ban-ayumi", "kiroku", "english")
GONE_IDS = ("minna", "kumikata", "tsukuru", "kaizen")
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
        # 並び: 頭（題と つくる）→ 仮説（考えを話す）→ たとえ → 立体 → 型紙の窓（版の歩み）→ のこそう → 英語
        at = [page.index(f'id="{name}"') for name in ORDER]
        assert page.index("<h1>") < at[0] and at == sorted(at), (where, dict(zip(ORDER, at)))
        for gone in GONE:
            assert gone not in page, (where, gone)
        assert not [x for x in GONE_IDS if f'id="{x}"' in page], (where, "外した節が残った", [x for x in GONE_IDS if f'id="{x}"' in page])
        # 立体は たとえ の後の節に。型紙の窓より前
        if kumitate.available(sid):
            assert 'id="kumitate"' in section(page, "kasetsu"), (where, "立体が頭の後に無い")
        # 仮説の節に、断り → 輪の図 → 仮説の札。型紙の窓は見出しと頭の文と紙（本人の言葉 11-08 の並びで、札は窓の前の仮説の節へ移った。
        # 断りが札より前・輪の図が断りと札の間、は前の決めのまま）
        fuda, win = page[page.index('id="kasetsu-fuda"'):page.index('id="tatoe"')], page[page.index('id="win"'):page.index('id="kiroku"')]  # 段の中に節が入るので、次の段の頭まで
        heads = [fuda.index(x) for x in ('id="premise"', 'id="wa"', 'class="plates"')]
        assert heads == sorted(heads), (where, heads)
        assert hypotheses.sheet_of(sid)["name"] in fuda and '<h2>型紙の窓</h2>' in win and '型紙を刷ります。切って、折って、組みます。' in win, where
        if printed:
            assert page.index('class="plates"') < page.index('<figure class="sheet">') and '<figure class="sheet">' in win, (where, "紙が札より前か、窓の外")
        assert page.count('id="wa"') == 1 and page.count('id="premise"') == 1, where
        # 版の歩みは型紙の窓の中の閉じた畳み（設計の問い 3 の答え）。たとえは畳まずに出す（本人の答え Q4 の「開いて出す」は前のまま）。改善の輪の節は無い（Q5）
        assert re.search(r'id="ban-ayumi"[^>]*><details class="fold-sec"><summary><h2>型紙の版の歩み</h2></summary>', win), (where, "版の歩みが窓の中の閉じた畳みでない")
        assert 'id="kaizen"' not in page, (where, "改善の輪の節は玩具の頁に無い")
        assert '<section class="sec" id="tatoe"><h2>たとえと、関連する事柄</h2>' in page, (where, "たとえは開いて出す")
    # 頁の足のギャラリーへの口は、ギャラリーの今の題「作った物」（職人の言葉は序の頁へ移った。#519・本人のサイト体験レビュー 11-07 の 6）
    assert '<a href="/gallery">作った物</a>' in page and "作った物と職人の言葉" not in page, sid
print(f"ok 玩具の頁の並び: {len(TOYS)} 種の刷る前と後で、原画 → 仮説（断り・輪の図・札・考えを話す）→ たとえ（開いて）→ 立体 → 型紙の窓（紙・版の歩みの畳み・口）→ のこそう。復元・組み方・困ったら・改善の輪の節は無い")
