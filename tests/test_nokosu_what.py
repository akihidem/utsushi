"""のこす の「何をのこすか」の 1 行と、字の欄の手引き（夕方のサイトのレビュー 11-07 の 14「のこす は何をのこすのか分からない」・
15「『感想をおくる』など、ハードルを低くして書いてもらう工夫」。UX の担当の仕分けの PR-C。src/web/naoru.py の WHAT と KEEP_HINT）。

見る事:
1. 何をのこすかの 1 行は、手帖の最後の画面（のこす の画面）と手帖の記録の頁の、のこすの枠の頭（説明の字の前）に 1 回ずつ。公開の場でも同じ
2. のこす の画面では、その 1 行も作る頁の決まり（記録の番号・「の紙」・版の名を出さない）に当たらない。枠は「のこす」の釦の後のまま
3. 手帖の字で書く欄の手引きは KEEP_HINT。作りながら見る頁の工夫の欄（hanasu の craft）の手引きは替えない
4. 字を空にすると前の形に戻る（WHAT が空なら枠は説明の字から始まる・KEEP_HINT が空なら手帖の欄も hanasu の手引き）
"""
import html
import os
import tempfile

os.environ.setdefault("OMOCHAE_DATA", tempfile.mkdtemp())

from omochae import hypotheses  # noqa: E402
from web import hanasu, naoru, techo_site, techo_step  # noqa: E402

TORA = "NDL-1187053-R0000014-R"
GORAIGO = "NDL-1187053-R0000005-L"


def esc(t):
    return html.escape(t, quote=True)


def first_lines(page):
    """のこすの枠の中の行（<p> の字）を順に返す。"""
    a = page.index('<aside class="naoru"')
    inner = page[a:page.index("</aside>", a)]
    return [seg.split(">", 1)[1].split("</p>", 1)[0] for seg in inner.split("<p ")[1:]]


def end_section(page):
    a = page.index('<section class="end" data-on="end">')
    return page[a:page.index("</section>", a)]


assert naoru.WHAT.strip() and naoru.KEEP_HINT.strip()
assert naoru.techo_ok((naoru.WHAT,)), "何をのこすかの 1 行が作る頁の決まりに当たる"

for sid in (TORA, GORAIGO):
    sheet = hypotheses.sheet_of(sid)["id"]
    for public in (False, True):
        # 1・2. のこす の画面: 枠の頭が WHAT、続けて窓口の決めた 2 行。枠は「のこす」の釦の後
        page = techo_step.page(sid, [sheet], "tenji", step=99, public=public)
        lines = first_lines(page)
        assert lines[0] == html.escape(naoru.WHAT, quote=False) and lines[1:] == [html.escape(t, quote=False) for t in naoru.TECHO_LINES], (sid, public, lines)
        end = end_section(page)
        assert end.index('id="keep"') < end.index('class="naoru"'), (sid, public, "枠が「のこす」の釦の前にある")
        # 3. 手帖の欄の手引き
        assert f'placeholder="{esc(naoru.KEEP_HINT)}"' in end, (sid, public, "手帖の欄の手引き")
        assert f'placeholder="{esc(hanasu.SCENES["craft"]["hint"])}"' not in end, (sid, public)
        # 1. 記録の頁: 枠の頭が WHAT、続けて説明の 2 行
        rec = techo_site.records_page(sid, public=public)
        lines = first_lines(rec)
        assert lines[0] == html.escape(naoru.WHAT, quote=False) and lines[1:3] == [html.escape(t, quote=False) for t in naoru.LINES], (sid, public, lines)
        assert rec.count(html.escape(naoru.WHAT, quote=False)) == 1, (sid, public)

# 3. 作りながら見る頁の工夫の欄は前の手引きのまま
sheet = hypotheses.sheet_of(TORA)["id"]
# （作りながら見る頁は刷った版が要るので、その頁が置く工夫の口 hanasu.craft_box を直に見る）
tsu = hanasu.craft_box(TORA, sheet, 1, 1)
assert f'placeholder="{esc(hanasu.SCENES["craft"]["hint"])}"' in tsu and naoru.KEEP_HINT not in tsu, "作りながら見る頁の手引きが替わった"

# 4. 字を空にした時は前の形
keep_what, keep_hint = naoru.WHAT, naoru.KEEP_HINT
naoru.WHAT, naoru.KEEP_HINT = "", ""
try:
    page = techo_step.page(TORA, [sheet], "tenji", step=99)
    assert first_lines(page) == [html.escape(t, quote=False) for t in naoru.TECHO_LINES], first_lines(page)
    assert f'placeholder="{esc(hanasu.SCENES["craft"]["hint"])}"' in end_section(page), "手引きが hanasu に戻らない"
    assert first_lines(techo_site.records_page(TORA))[:2] == [html.escape(t, quote=False) for t in naoru.LINES]
finally:
    naoru.WHAT, naoru.KEEP_HINT = keep_what, keep_hint
print("ok のこすの何をのこすかの 1 行と欄の手引き（2 つの頁の枠の頭・作る頁の決まり・手帖の欄だけ替える・空なら前の形）")
