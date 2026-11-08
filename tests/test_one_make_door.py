"""玩具の頁の作る口は 1 本の道: 頭の「つくる」で型紙の窓へ、窓の「つくる」で手帖へ。ほかに手帖へ行く口と「作る」の節と、作りながら見る頁への口を置かない。

なぜ: 本人のサイト体験レビュー（11-07）の 3 で、同じ所へ行く口が頁に何回も出ると言われた。前は型紙の窓の「つくる」と、
頁の下の「作る」の節の「手帖をひらく（作りながら聞く・上げる）」の 2 つが手帖へ行き、作る節も「すぐ作る」と「作る」の 2 つあった。
地図の道しるべ「作る口は手帖 1 つ」に寄せる。作りながら見る頁は手帖へ寄せた（窓口の決め 11-07 の 4）ので、頁からその頁への口も無い事を見る。
頭の帯（道しるべ）は入口の担当の物なので数えない。
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


def main_part(page):
    """頭の帯を除いた頁。"""
    return re.sub(r'<nav class="nav">.*?</nav>', "", page, count=1, flags=re.S)


def section(page, sid):
    """節の id ごとの中身（次の節の頭まで）。"""
    starts = [(m.start(), m.group(1)) for m in re.finditer(r'<section [^>]*id="([^"]+)"', page)]
    return {name: page[a:(starts[i + 1][0] if i + 1 < len(starts) else len(page))] for i, (a, name) in enumerate(starts)}


for sid in TOYS:
    before = main_part(toy_page(sid))
    techo = f'href="/toy/{sid}/techo"'
    # 刷る前: 手帖へ行く口は無い（手順は紙と一緒に使う物なので、紙を作る道だけ）。紙を作るのは型紙の窓の中の「つくる」1 つ。
    # 頭の「つくる」は仮説の段の頭へ行く道（本人の言葉 11-08「原図をみて、狂歌を読んで、仮説、たとえ、3D をみたあとに型紙の印刷にすすむ。」・設計の問い 2 の答え）
    assert before.count(techo) == 0, (sid, "刷る前に手帖への口がある")
    assert before.count(">つくる<") == 2, (sid, "刷る前の頁の「つくる」が 頭と窓の 2 つでない")
    assert before.count(f'action="/toy/{sid}/print#win"') == 1 and before[before.index('id="win"'):before.index('id="kiroku"')].count(f'action="/toy/{sid}/print#win"') == 1, (sid, "刷る口が型紙の窓の 1 つでない")
    assert 'id="tsukuru"' not in before and '<section class="sec" id="tsukuru"></section>' not in before, (sid, "前の作る節の錨が残った")

    assert print_latest(sid, hypotheses.sheet_of(sid)["id"]) is not None, (sid, "紙を作れない")
    page = main_part(toy_page(sid))
    secs = section(page, sid)
    # 型紙の窓の中に版の歩みの節（畳み）が入るので、窓は次の段（のこそう・#kiroku）の頭まで
    secs["win"] = page[page.index('id="win"'):page.index('id="kiroku"')]
    # 刷った後: 手帖へ行く口は型紙の窓の「つくる」1 つだけ
    assert page.count(techo) == 1 and techo in secs["win"], (sid, page.count(techo))
    assert f'<a class="btn" {techo}>つくる</a>' in secs["win"], (sid, "窓の「つくる」が手帖へ行かない")
    # 頭の「つくる」は仮説の段の頭へ（本人の言葉 477・設計の問い 2 の答え）。頁の「つくる」は頭と窓の 2 つで、行き先は 仮説の段 → 手帖 の順
    assert page.count(">つくる<") == 2, (sid, page.count(">つくる<"))
    hero = page[:page.index('</section>', page.index('<section class="hero">'))]
    assert '<a class="btn" href="#kasetsu-fuda">つくる</a>' in hero, (sid, "頭の「つくる」が仮説の段へ行かない")
    # 前の「作る」の節の見出し・説明・手帖への釦は無い（外した字）
    for gone in ("<h2>作る</h2>", "手帖をひらく（作りながら聞く・上げる）", "刷った紙を切って、折って、組みます。机に置いた手帖で"):
        assert gone not in page, (sid, gone)
    # 作りながら見る頁は手帖へ寄せた（窓口の決め 11-07 の 4）ので、頁から作りながら見る頁への口は無い。困った時に聞く口は今の節に残る
    assert "/tsukuru" not in page and "作りながら見る（机の端に置く・試作）" not in page, (sid, "作りながら見る頁への口")
    # 困った時に聞く口は玩具の頁から外した: 手帖の手順の画面に「こまった」と聞く口がある（設計の問い 4 の答え「推しのとおり。」）
    assert 'id="ask"' not in page and 'id="tsukuru"' not in page, sid
print(f"ok 玩具の頁の作る口: {len(TOYS)} 種で、手帖へ行く口は型紙の窓の「つくる」1 つ（刷る前は 0）、刷る口は型紙の窓の 1 つ、頭の「つくる」は仮説の段へ")
