"""作った物の頁（/gallery）の、ワークショップで作られた物（作例）の節（本人の言葉 11-07「サイトにワークショップで作られたおもちゃを掲載したい」）。

見る線:
1. 空の時: 作例が無い時と、人が確かめる前は、節ごと出ない（字も id も無い）。頁の前の形（他の人が作った物・まだ…の 1 行・見本）は変わらない
2. 出す物: 人が「物だけ」と確かめた写真だけ。「人が入る」と確かめた写真は出ない。写真は小さい写し（/small）で、元の写真の道は並べない
3. 並び: 日の順の小見出し（id は sakurei-MMDD・web.sakurei.days() と同じ日だけ）。日の中は玩具ごとに寄せる。作った日は札に重ねない
4. 札: 玩具の名から玩具の頁へ行く。記録の番号の字は出さない。作例は「他の人が作った物」の並びに混ざらない
5. 場: 合言葉なしで開いた場も同じ物を出す。写真を出さない形（photos=False）は出さない。作例だけがある時も見本は畳む
"""
import io
import os
import re
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from PIL import Image  # noqa: E402

from omochae import media_review  # noqa: E402
from web import sakurei, techo_site  # noqa: E402
from web.play_server import sources  # noqa: E402

G, T = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"
SIDS = sources()
tmp = tempfile.mkdtemp()


def photo(name, color):
    path = os.path.join(tmp, name)
    buf = io.BytesIO()
    Image.new("RGB", (64, 48), color).save(buf, "JPEG")
    with open(path, "wb") as f:
        f.write(buf.getvalue())
    return path


def section(html):
    m = re.search(r'<section class="panel" id="sakurei">.*?</section>', html, re.S)
    return m.group(0) if m else ""


# 1. 空の時
before = techo_site.gallery_page(SIDS)
assert 'id="sakurei' not in before and techo_site.SAKUREI_TITLE not in before and "sakurei-row" not in before
assert "まだ作った物の記録はありません" in before, "作例が無い時の前の形"
assert techo_site.sakurei_section(SIDS) == ""

# 11-06 は虎（頁の並びで後の玩具）を先に取り込む: 記録の順と玩具の並びが逆になり、玩具ごとに寄せたかが見える
(t1, tn1, _), = sakurei.add([photo("c.jpg", (10, 10, 200))], T, "2026-11-06")[0]
done, refused, cannot = sakurei.add([photo("a.jpg", (200, 10, 10)), photo("b.jpg", (10, 200, 10))], G, "2026-11-06", sheet_set="goraigo-v10")
assert not refused and not cannot and len(done) == 2, (refused, cannot)
(g1, gn1, _), (g2, gn2, _) = done
(t2, tn2, _), = sakurei.add([photo("d.jpg", (90, 90, 90))], T, "2026-11-04")[0]
(g3, gn3, _), = sakurei.add([photo("e.jpg", (50, 150, 50))], G, "2026-11-07")[0]
assert techo_site.sakurei_section(SIDS) == "" and 'id="sakurei"' not in techo_site.gallery_page(SIDS), "人が確かめる前に出た"

# 2. 出す物: 物だけと確かめた写真だけ（g2 は人が入る・g3 は確かめ待ちのまま）
for rid, name in ((g1, gn1), (t1, tn1), (t2, tn2)):
    assert media_review.record(rid, name, "object", "確認者") == []
assert media_review.record(g2, gn2, "people", "確認者") == []
html = techo_site.gallery_page(SIDS)
sec = section(html)
assert sec, "確かめた作例があるのに節が無い"
for rid, name in ((g1, gn1), (t1, tn1), (t2, tn2)):
    assert f'src="/record/{rid}/media/{name}/small"' in sec, (rid, "小さい写しで出ない")
    assert f'/record/{rid}/media/{name}"' not in html, (rid, "元の写真の道を並べた")
assert g2 not in html and g3 not in html, "人が入る写真か、確かめ待ちの写真が出た"
assert sec.count("<img") == 3 and 'alt="作った物の写真"' in sec

# 3. 並び: 日の順の小見出し・days() と同じ日だけ・日の中は玩具ごと（頁の玩具の並び）
heads = re.findall(r'<h3 class="day" id="sakurei-(\d{4})">([^<]+)</h3>', sec)
assert heads == [("1104", "11 月 4 日"), ("1106", "11 月 6 日")], heads
assert {d for d, _ in heads} == sakurei.days(), "審査用の頁が道を張る日と、節の小見出しの日が違う"
assert "11 月 7 日" not in sec, "確かめた写真の無い日の小見出しが出た"
six = sec.split('id="sakurei-1106"')[1]
assert SIDS.index(G) < SIDS.index(T) and t1 < g1, "試験の前提（玩具の並びと記録の順が逆）"
assert six.index(g1) < six.index(t1), "日の中が頁の玩具の並びでない"
for _, label in heads:
    assert sec.count(label) == 1, (label, "作った日を札に重ねた")

# 4. 札: 玩具の名から玩具の頁へ・記録の番号の字は出さない・他の人が作った物に混ざらない
names = {sid: techo_site.hypotheses.load(sid)["toy"] for sid in (G, T)}
assert f'<a href="/toy/{G}">{techo_site.esc(names[G])}</a>' in sec and f'<a href="/toy/{T}">{techo_site.esc(names[T])}</a>' in sec
text = re.sub(r"<[^>]+>", " ", sec)
assert not re.search(r"R-\d{4}", text), "記録の番号を字で出した"
assert "記録の番号" not in text and "goraigo-v10" not in sec
ageta = html.split('id="ageta"')[1]
assert not any(r in ageta for r in (g1, t1, t2)), "作例が他の人が作った物に混ざった"
assert html.index('id="sakurei"') < html.index('id="ageta"'), "作例の節が頁の頭でない"
assert "まだ作った物の記録はありません" not in html, "作例が並んでいるのに「まだ…ありません」"

# 5. 場
pub = techo_site.gallery_page(SIDS, public=True)
assert section(pub) == sec, "合言葉なしで開いた場で、作例の節が違う"
closed = techo_site.gallery_page(SIDS, photos=False)
assert 'id="sakurei"' not in closed and "/small" not in closed
from web.demo_samples import uploads_html  # noqa: E402
if uploads_html():
    assert '<details class="samples-fold"><summary>見本</summary>' in html, "作例だけがある時に見本を畳まない"
    assert '<details class="samples-fold">' not in before, "作例が無い時に見本を畳んだ（前の形が変わった）"
print("ok 作った物の頁の作例の節: 空の時・確かめた物だけ・小さい写し・日の順と玩具ごと・札・場")
