"""玩具の頁の型紙は 1 か所（型紙の窓）にだけ出し、紙を作る口は頭の「つくる」1 つにする。

なぜ: 本人のサイト体験レビュー（11-07）の 3「作るの頁がごちゃごちゃして、同じ物が何回も出る。まとめる」。前は型紙の絵が
「すぐ作る」の札（小さな絵）と型紙の窓の 2 か所に出て、紙を作る口も 頭の「つくる」・札の「型紙を見る」・窓の中の札 の 3 つあった。
札は仮説の字だけを持つ（札は型紙の窓の頭にある）。紙が無い時は窓に紙の絵を出さない。作れなかった時の文は、今までどおり窓の錨の所で読める。
"""
import os
import re
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ.pop("ANTHROPIC_API_KEY", None)

from omochae import hypotheses  # noqa: E402
from web.play_server import print_latest  # noqa: E402
from web.toy import toy_page  # noqa: E402

TOYS = ("NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R")
GONE = ("型紙を見る", "仮説の札を押すと、紙を作ってここに出します。", "仮説の点線の札は、押すと紙を作ってここに出します。")


def main_part(page):
    """頭の帯を除いた頁。"""
    return re.sub(r'<nav class="nav">.*?</nav>', "", page, count=1, flags=re.S)


def win(page):
    """型紙の窓の段（次の段 できたら、のこそう の頭まで）。窓の中に版の歩みの節（畳み）が入るので、次の <section では切らない。"""
    a = page.index('id="win"')
    return page[a:page.index('id="kiroku"', a)]


for sid in TOYS:
    prints = rf'<form method="post" action="/toy/{re.escape(sid)}/print#\w+"'
    before = main_part(toy_page(sid))
    # 紙が無い時: 紙を作る口は型紙の窓の中の「つくる」1 つだけ。頭の「つくる」は仮説の段へ行く道で刷らない（本人の言葉 11-08「原図をみて、狂歌を読んで、
    # 仮説、たとえ、3D をみたあとに型紙の印刷にすすむ。」・設計の問い 2 の答え）。型紙の絵は無い
    hero = before[:before.index("</section>", before.index('<section class="hero">'))]
    win_before = before[before.index('id="win"'):before.index('id="kiroku"')]
    assert len(re.findall(prints, before)) == 1 and len(re.findall(prints, win_before)) == 1 and not re.findall(prints, hero), (sid, re.findall(prints, before))
    assert f'<img src="/sheet/{sid}/' not in before, (sid, "紙が無いのに型紙の絵")
    # 窓の節は、紙が無い時も、説明・断り・輪の図・仮説の札を出す（「すぐ作る」の節を窓へ寄せた。C3）。紙の絵と紙の種類の札は無い
    # 見出しは「型紙を印刷する」（本人の言葉 11-08「型紙の窓を「型紙を印刷する」からにして…」。前は「型紙の窓」）
    assert "<h2>型紙を印刷する</h2>" in before and '<figure class="sheet">' not in win(before), (sid, "紙が無いのに紙の窓")
    for gone in GONE:
        assert gone not in before, (sid, gone)

    assert print_latest(sid, hypotheses.sheet_of(sid)["id"]) is not None, (sid, "紙を作れない")
    page = main_part(toy_page(sid))
    w = win(page)
    # 紙がある時: 型紙の絵は窓の中だけ。札（すぐ作る）に絵は無い。紙を作り直す口も無い（頭の「つくる」は窓の紙へ行く）
    pics = re.findall(rf'<img src="/sheet/{re.escape(sid)}/[^"]+"', page)
    assert pics and all(p in w for p in pics) and len(re.findall(rf'<img src="/sheet/{re.escape(sid)}/[^"]+"', page.replace(w, ""))) == 0, (sid, pics)
    assert "<h2>型紙を印刷する</h2>" in w and "PDF を開いて印刷する" in w and "<h2>型紙の窓</h2>" not in page, sid
    assert not re.findall(prints, page), (sid, re.findall(prints, page))
    for gone in GONE:
        assert gone not in page, (sid, gone)
    # 札は仮説の字を持ったまま（字は変えない）。札は型紙の窓の頭
    assert hypotheses.sheet_of(sid)["name"] in w, sid
print(f"ok 玩具の頁の型紙: {len(TOYS)} 種で、型紙の絵は窓の 1 か所、紙を作る口は頭の「つくる」1 つ（紙が無い時は窓の節を出さない）")
