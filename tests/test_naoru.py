"""のこすと型紙が直る事の枠（本人のサイト体験レビュー 11-07 の言葉 7「残すの頁に、記録を上げるとどう改善が進むか（型紙と AI の仮説が良くなる事）を、
はっきり書く。ただで情報を上げる人はいない。」。直しの設計の E。src/web/naoru.py）。

見る事:
1. 説明は 2〜3 行で、どの行も空でない（のこす の画面は 1 手 1 画面なので長くしない）
2. 山場の 1 行は data/kaizen/highlight.json の表の字のまま（字を作り替えない）。出どころの欄があり、個人のパスを持たない
3. 手帖の最後の画面（のこす の画面）は作る頁の決まり（記録の番号・「の紙」・版の名を出さない。本人の決定 11-05、#87）に従う:
   字がその決まりに当たる今の案 1 では、手帖に枠を出さない。当たらない字なら、枠が end の節の中の「のこす」の釦のすぐ後に 1 回だけ出て
   （釦の上に置くと小さい画面で釦が最初の画面の外へ出たため）、山場の 1 行（版の名を持つ）は添えない。公開の場（public）でも同じ
4. 手帖の記録の頁では、枠が頁の頭（題の後・手帖をひらくの口の前）に 1 回だけ出る。公開の場でも出る
5. 説明の字を空にすると、枠はどちらの頁にも出ない（字を外して作りだけを残す形）
"""
import json
import os
import tempfile

os.environ.setdefault("OMOCHAE_DATA", tempfile.mkdtemp())

from omochae import hypotheses  # noqa: E402
from web import naoru, techo_site, techo_step  # noqa: E402

TORA = "NDL-1187053-R0000014-R"
GORAIGO = "NDL-1187053-R0000005-L"

# 1. 説明の行
assert 2 <= len(naoru.LINES) <= 3 and all(t.strip() for t in naoru.LINES), naoru.LINES

# 2. 山場の 1 行は表の字のまま
data = json.loads(naoru.HIGHLIGHT.read_text(encoding="utf-8"))
# 表の字（改善の歴史の表の、張子の首振り虎の型紙の版 v7 の行）。表は repo の外にあるので、写した字をここで留める（写し違い・作り替えを拾う）
assert (data["line"], data["toy"], data["sheet_version"]) == ("3D で組んで見つかった当たりを直し、頭が揺れても前の壁に当たらない", "張子の首振り虎", 7), data
assert data["source"] and data["why_this_one"], data
assert naoru.highlight() == f"{data['line']}（{data['toy']} 型紙の版 v{data['sheet_version']}）", naoru.highlight()
raw = naoru.HIGHLIGHT.read_text(encoding="utf-8")
assert "/home/" not in raw and "~/" not in raw, "data に個人のパスが入っている"
box = naoru.box()
assert box.count('class="naoru"') == 1 and all(t in box for t in naoru.LINES) and naoru.highlight() in box, box


def end_section(html):
    a = html.index('<section class="end" data-on="end">')
    return html[a:html.index("</section>", a)]


# 3. のこす の画面: 作る頁の決まりに当たる字（今の案 1）なら出さない。当たらない字なら、end の節の中の「のこす」の釦のすぐ後に 1 回
assert not naoru.techo_ok(naoru.LINES) and naoru.box(techo=True) == "", "案 1 の字は「の紙」を持つので、手帖には出さない"
for sid in (TORA, GORAIGO):
    sheet = hypotheses.sheet_of(sid)["id"]
    assert 'class="naoru"' not in techo_step.page(sid, [sheet], "tenji", step=99), (sid, "手帖に決まりに当たる字の枠が出た")
keep_lines = naoru.LINES
naoru.LINES = ("試しの 1 行目", "試しの 2 行目")  # 決まりに当たらない字（試験だけの字。頁の字ではない）
try:
    assert naoru.techo_ok(naoru.LINES)
    for sid in (TORA, GORAIGO):
        sheet = hypotheses.sheet_of(sid)["id"]
        for public in (False, True):
            page = techo_step.page(sid, [sheet], "tenji", step=99, public=public)
            assert page.count('class="naoru"') == 1, (sid, public, "枠が 1 回でない")
            end = end_section(page)
            keys_end = end.index('id="keep"')
            at = end.index('class="naoru"')
            assert keys_end < at, (sid, public, "枠が「のこす」の釦の前にある")
            between = end[end.index("</div>", keys_end) + len("</div>"):at]
            assert between.strip() == '<aside', (sid, public, "釦と枠の間に別の物がある", between[:80])
            assert naoru.highlight() not in page, (sid, public, "手帖に版の名を持つ山場の 1 行が出た")
    for bad in (("次に作る人の紙", "x"), ("型紙の版 v7", "x"), ("R-0001", "x")):
        naoru.LINES = bad
        assert naoru.box(techo=True) == "" and naoru.box() != "", bad
finally:
    naoru.LINES = keep_lines

# 4. 記録の頁: 頭（題の後・手帖をひらくの口の前）に 1 回
for sid in (TORA, GORAIGO):
    for public in (False, True):
        page = techo_site.records_page(sid, public=public)
        assert page.count('class="naoru"') == 1, (sid, public)
        assert page.index("<h1>手帖</h1>") < page.index('class="naoru"') < page.index('<p class="links">'), (sid, public, "枠が頁の頭に無い")

# 5. 字を空にすると、どちらの頁にも出ない
keep = naoru.LINES
naoru.LINES = ()
try:
    assert naoru.box() == ""
    sheet = hypotheses.sheet_of(TORA)["id"]
    assert 'class="naoru"' not in techo_step.page(TORA, [sheet], "tenji", step=99)
    assert 'class="naoru"' not in techo_site.records_page(TORA)
finally:
    naoru.LINES = keep
print("ok のこすと型紙が直る事の枠（2〜3 行・山場の 1 行は表の字・のこすの釦のすぐ下と記録の頁の頭に 1 回・公開の場でも・字が空なら出ない）")
