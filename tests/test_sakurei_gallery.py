"""作った物の頁（/gallery）の、ワークショップで作られた物（作例）の節（本人の言葉 11-07「サイトにワークショップで作られたおもちゃを掲載したい」）。

見る線:
1. 空の時: 作例が無い時と、人が確かめる前は、節ごと出ない（字も id も無い）。頁の前の形（他の人が作った物・まだ…の 1 行・見本）は変わらない
2. 出す物: 人が「物だけ」と確かめた写真だけ。「人が入る」と確かめた写真は出ない。写真は小さい写し（/small）で、元の写真の道は並べない
3. 並び: 札は玩具ごと（日ごとの見出しを置かない。本人の言葉 11-07「日毎にはしない」）。頁の玩具の並びの順、同じ玩具の中は記録の順、
   83 の外の玩具は後ろに棚卸しの名で道なし。頭に報告の顔の写真と本人の言葉の札、その後に参加者の型紙の改善例（本人の言葉の引用）。
   報告の 4 回の段は、回の一覧（web.kaizen_ws）が無い時は出ない
4. 札: 玩具の名から玩具の頁へ行く。刷った組が分かる時だけ型紙の版（組の番号）。記録の番号の字は出さない。作例は「他の人が作った物」の並びに混ざらない
5. 場: 小さい写しの道は確かめた写真だけを返す。合言葉なしで開いた場も同じ物を出す。写真を出さない形（photos=False）は出さない。作例だけがある時も見本は畳む
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
# ワークショップの試行の写真（web.workshop・repo に在る）は、ここが見る「本物の記録が無い時」の形を変えるので、この試験では表を空にする
# （写真が出る形は tests/test_workshop_gallery.py が見る。本人の見直し 11-07 夜の ②⑦）
from web import workshop as _workshop  # noqa: E402

_workshop.TABLE = _workshop.TABLE.with_name("no-such-workshop-photos.json")

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
from omochae import records  # noqa: E402
OUT, ALL = "NDL-1187053-R0000025-R", records.WORKSHOP_ALL
(o1, on1, _), = sakurei.add([photo("o.jpg", (120, 60, 0))], OUT, "2026-11-07")[0]
(f1, fn1, _), = sakurei.add([photo("f.jpg", (0, 60, 120))], ALL, "2026-11-07")[0]
(k1, kn1, _), = sakurei.add([photo("k.jpg", (60, 0, 120))], OUT, "2026-11-07", kind="kufu")[0]
assert techo_site.sakurei_section(SIDS) == "" and 'id="sakurei"' not in techo_site.gallery_page(SIDS), "人が確かめる前に出た"

# 2. 出す物: 物だけと確かめた写真だけ（g2 は人が入る・g3 は確かめ待ちのまま）
for rid, name in ((g1, gn1), (t1, tn1), (t2, tn2), (o1, on1), (f1, fn1), (k1, kn1)):
    assert media_review.record(rid, name, "object", "確認者") == []
assert media_review.record(g2, gn2, "people", "確認者") == []
html = techo_site.gallery_page(SIDS)
sec = section(html)
assert sec, "確かめた作例があるのに節が無い"
for rid, name in ((g1, gn1), (t1, tn1), (t2, tn2)):
    assert f'src="/record/{rid}/media/{name}/small"' in sec, (rid, "小さい写しで出ない")
    assert f'/record/{rid}/media/{name}"' not in html, (rid, "元の写真の道を並べた")
assert g2 not in html and g3 not in html, "人が入る写真か、確かめ待ちの写真が出た"
assert sec.count("<img") == 6 and 'alt="作った物の写真"' in sec

# 3. 並び: 頭に顔の写真と本人の言葉の札 → 参加者の型紙の改善例 → 玩具ごとの札（日の見出しは無い）
assert not re.search(r'id="sakurei-\d{4}"', sec) and "11 月 4 日" not in sec and "11 月 6 日" not in sec, "日ごとの見出しが残った"
faces = sec.index('class="sakurei-faces"')
assert f'src="/record/{f1}/media/{fn1}/small"' in sec[faces:sec.index("</figure>", faces)] and techo_site.SAKUREI_FACES in sec, "顔の写真か札が無い"
assert sec.index("sakurei-faces") < sec.index("sakurei-kufu") < sec.index("sakurei-row"), "並びが違う"
kufu = sec[sec.index("sakurei-kufu"):sec.index("sakurei-row")]
assert f"/record/{k1}/media/{kn1}/small" in kufu and f"「{techo_site.SAKUREI_KUFU_WORDS}」" in kufu and techo_site.SAKUREI_KUFU in kufu
row = sec[sec.index("sakurei-row"):]
assert f1 not in row and k1 not in row, "顔の写真か事例の写真が玩具の札に重なった"
assert SIDS.index(G) < SIDS.index(T) and t1 < g1, "試験の前提（玩具の並びと記録の順が逆）"
assert row.index(g1) < row.index(t1) < row.index(t2) < row.index(o1), "玩具ごとの並び（頁の玩具の順・記録の順・83 の外は後ろ）でない"
assert "sakurei-report" not in sec and techo_site.SAKUREI_REPORT_GO not in sec, "回の一覧が無いのに報告の段が出た"

# 4. 札: 玩具の名から玩具の頁へ・記録の番号の字は出さない・他の人が作った物に混ざらない
names = {sid: techo_site.hypotheses.load(sid)["toy"] for sid in (G, T)}
assert f'<a href="/toy/{G}">{techo_site.esc(names[G])}</a>' in sec and f'<a href="/toy/{T}">{techo_site.esc(names[T])}</a>' in sec
text = re.sub(r"<[^>]+>", " ", sec)
assert not re.search(r"R-\d{4}", text), "記録の番号を字で出した"
assert "記録の番号" not in text and "goraigo-v10" not in sec
# 型紙の版は、刷った組が分かる作例の札にだけ、組の番号で出す（玩具の頁の型紙の札の脇と同じ「型紙の版 10」の形）
card = lambda rid: re.search(rf'<figure>(?:(?!</figure>).)*{rid}(?:(?!</figure>).)*</figure>', row, re.S).group(0)  # noqa: E731
assert "猫と鼠の箱（鼠捕りからくり）" in card(o1) and "<a " not in card(o1), "83 の外の玩具の札に名が無いか、無い頁への道を張った"
assert "型紙の版 10" in card(g1), card(g1)
assert "型紙の版" not in card(t1) and "型紙の版" not in card(t2), "組の分からない作例に版を出した"
assert sec.count("型紙の版") == 1
ageta = html.split('id="ageta"')[1]
assert not any(r in ageta for r in (g1, t1, t2, o1, f1, k1)), "作例が他の人が作った物に混ざった"
# 報告の段: 回の一覧の口がある時は、その字で 4 回の行と審査用の頁への道が出る（字の元を 1 つに）
import sys  # noqa: E402
import types  # noqa: E402
fake = types.ModuleType("web.kaizen_ws")
fake.workshops = lambda: [{"n": 1, "date": "11 月 4 日", "did": "紙で作って試した", "line": "外筒を山折りに直した"}, {"n": 2, "date": "11 月 5 日", "did": "動画を受けた"}, {"n": 3}]
sys.modules["web.kaizen_ws"] = fake
import web  # noqa: E402
web.kaizen_ws = fake
rep = section(techo_site.gallery_page(SIDS))
assert rep.count("<li>") == 2 and "11 月 4 日　紙で作って試した" in rep and "外筒を山折りに直した" in rep and f'href="/kaizen#ws">{techo_site.SAKUREI_REPORT_GO}' in rep, rep
assert rep.index("sakurei-faces") < rep.index("sakurei-report") < rep.index("sakurei-kufu"), "報告の段が顔の写真の後・事例の前に無い"
fake.workshops = lambda: (_ for _ in ()).throw(ValueError("読めない"))
assert "sakurei-report" not in section(techo_site.gallery_page(SIDS)), "回の一覧が読めない時に段が出た"
del sys.modules["web.kaizen_ws"], web.kaizen_ws
assert html.index('id="sakurei"') < html.index('id="ageta"'), "作例の節が頁の頭でない"
assert "まだ作った物の記録はありません" not in html, "作例が並んでいるのに「まだ…ありません」"

# 原画の隣の作ってみた実物（web.made）が作例を読む形は、入口の棚の札の角の PR（サイトの担当）が持つ（同じ行の衝突を避けた）
# 小さい写しの道が、作例の写真を返す（人が入る写真と確かめ待ちの写真は返さない）
import threading  # noqa: E402
import urllib.error  # noqa: E402
import urllib.request  # noqa: E402

from web.play_server import serve  # noqa: E402


def get(server, path):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{server.server_address[1]}{path}", timeout=30) as r:
            return r.status, r.headers.get("Content-Type"), r.read()
    except urllib.error.HTTPError as e:
        return e.code, None, b""


for opened in (False, True):
    srv = serve(0, public_open=opened)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        st, kind, body = get(srv, f"/record/{g1}/media/{gn1}/small")
        assert st == 200 and kind == "image/jpeg" and body[:3] == b"\xff\xd8\xff", (opened, st, kind)
        assert get(srv, f"/record/{g2}/media/{gn2}/small")[0] == 404 and get(srv, f"/record/{g3}/media/{gn3}/small")[0] == 404, opened
        st, _, page = get(srv, "/gallery")
        assert st == 200 and 'id="sakurei"' in page.decode() and f"/record/{g1}/media/{gn1}/small" in page.decode(), opened
    finally:
        srv.shutdown()
        srv.server_close()

# 英語の頁: 作例の節の字は全頁の英語の表にある（表に無い日本語が残らない。83 の外の玩具の名も）
from web import i18n  # noqa: E402
miss = []
i18n.to_en(sec, miss)
assert miss == [], miss
# 本人の言葉の引用（顔の写真の札・参加者の型紙の改善例）は、英語の頁でも原文を残して英訳を添える（web.i18n の頭の決まり・#538 の形）
en_sec = i18n.to_en(sec, [])
for words in (techo_site.SAKUREI_FACES, techo_site.SAKUREI_KUFU_WORDS):
    assert words in en_sec, (words, "英語の頁で本人の言葉の原文が消えた")
assert "(“The toys made over the 4 days of workshops”)" in en_sec and "(“A participant's improvement to the template, example 1." in en_sec

# 5. 場
pub = techo_site.gallery_page(SIDS, public=True)
assert section(pub) == sec, "合言葉なしで開いた場で、作例の節が違う"
closed = techo_site.gallery_page(SIDS, photos=False)
assert 'id="sakurei"' not in closed and "/small" not in closed
# 上げた物の見本（作り物）は外した（本人の言葉 11-08「見本の記録をワークショップのデータで作成して欲しい。」）。畳みも出ない
assert '<details class="samples-fold">' not in html and '<details class="samples-fold">' not in before, "ギャラリーに見本の畳みを出さない"
print("ok 作った物の頁の作例の節: 空の時・確かめた物だけ・小さい写し・顔の写真と事例・玩具ごと・報告の段・札・場")
