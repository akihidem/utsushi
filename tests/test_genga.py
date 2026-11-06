"""原画と歌（web.genga）の試験。本人の指示 11-06: 原画はページ全体で、狂歌は必ず原画と一緒に。本物の網は使わない。

見る事（設計メモの試験の節と、統括の決め）:
1. 頁の全体の目当ては 47 枚で、左右の箱が正しい。必須 2 種の頁は今の切り抜きと同じ箱。取る道は今の写しと同じ入口
2. 玩具の頁の頭: 頁の全体の絵が歌より先、確かめた歌がその後。玩具の所は細い枠（頁の片側の全体の記録には出さない）。比は絵のまま
3. 作る時の畳み: 1 回押すと開き、絵は開くまで取らない。「大きく見る」は頁を離れない（リンクでなく、頁の中に重ねる）
4. 英語の頁は絵だけ。くずし字は箱の無い玩具に頁の全体。額（skin.frame）は縦横を別々に伸ばさない
5. 頁の写しが無くても頁は止まらない。一覧の小さい絵は今の切り抜きのまま。合言葉なしの場でも頁の全体を出す
"""
import inspect
import io
import json
import os
import pathlib
import re
import tempfile
import threading
import urllib.error
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ.pop("ANTHROPIC_API_KEY", None)

from PIL import Image  # noqa: E402

from omochae import ingest  # noqa: E402
from omochae.hypotheses import ROOT  # noqa: E402
from web import en, genga, genga_words, kuzushi, skin, techo_site, toys, tsukuru  # noqa: E402
from web.play_server import serve  # noqa: E402
from web.toy import toy_page  # noqa: E402

G, T = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"
PLAIN = "NDL-1187053-R0000009-L-2"  # 歌の読みの無い試作の玩具。箱は頁の一部


def src(sid):
    return json.loads((ROOT / "data/sources" / f"{sid}.json").read_text(encoding="utf-8"))


# 1. 目当て
targets = ingest.page_targets()
assert len(targets) == 47, len(targets)
assert targets["R0000005-L"].endswith("/R0000005/pct:0,0,50,100/1000,/0/default.jpg")
assert targets["R0000014-R"].endswith("/R0000014/pct:50,0,50,100/1000,/0/default.jpg")
for sid in (G, T):  # 必須 2 種の頁は、今の切り抜きと同じ箱（幅だけが違う）
    s = src(sid)
    assert targets[ingest.page_name(s)].replace("/1000,/", "/1600,/") == s["image_url"], sid
assert "fetch_images(pages, PAGES)" in inspect.getsource(ingest.images), "今の写しと同じ入口で取る"
got = pathlib.Path(tempfile.mkdtemp())
keep = ingest._get
ingest._get = lambda url: b"\xff\xd8page\xff\xd9"
try:
    assert ingest.fetch_images({"R0000005-L": targets["R0000005-L"]}, got) == []
    assert (got / "R0000005-L.jpg").read_bytes() == b"\xff\xd8page\xff\xd9" and (got / "R0000005-L.url").read_text(encoding="utf-8") == targets["R0000005-L"]
finally:
    ingest._get = keep

# 写しの置き場を一時の場所にする（本物の out/sources/pages には触らない）
pages = pathlib.Path(tempfile.mkdtemp())
ingest.PAGES = pages


def jpeg(path, size=(100, 166)):
    buf = io.BytesIO()
    Image.new("RGB", size, (230, 220, 200)).save(buf, "JPEG")
    path.write_bytes(buf.getvalue())


for sid in (G, PLAIN):
    jpeg(genga.page_file(src(sid)))

# 2. 玩具の頁の頭
for look in ("tenji", "zine"):
    page = toy_page(G, look)
    hero = page[page.index('class="hero"'):page.index('id="kasetsu"')]
    assert hero.index(f'<img src="/picture/{G}/page" width="100" height="166"') < hero.index('class="genga-songs"') < hero.index("<h1>"), look
    assert all(e["text"] in hero for e in genga.songs(src(G))) and genga.QUOTE in hero, "確かめた歌が絵の後に"
    assert 'class="genga-box"' not in hero, "頁の片側の全体の記録には枠を出さない"
    assert f'<a href="/picture/{G}/page">{genga_words.BIG}</a>' in hero, "玩具の頁は絵そのものへ"
    assert f'<a class="genga-pic" href="/picture/{G}/page"' in hero, "絵そのものも押せる（UX の見直し）"
    assert 'class="genga-crop"' not in hero, "枠の無い玩具（頁の片側の全体）には切り抜きを置かない"
    assert "background-image:url(/picture/" not in hero, "頭に切り抜きを敷かない"
    assert f'alt="{src(G)["toy"]} {genga_words.HEAD}"' in hero and "の載る頁" not in hero, "絵の読み上げは玩具の名と本人が採った見出し（新しい字を足さない）"
plain = toy_page(PLAIN, "tenji")
hero = plain[plain.index('class="hero"'):plain.index('id="kasetsu"')]
if (ROOT / "out/sources" / f"{PLAIN}.jpg").exists():
    assert f'<span class="genga-crop"><img src="/picture/{PLAIN}"' in hero, "頁を分け合う玩具は、狭い幅で切り抜きを右に"
assert 'class="genga-box" style="left:' in hero and 'class="genga-songs"' not in hero and genga.QUOTE not in hero, "読みの無い玩具は字の歌も断りも出さない（本人の決定 11-06）"
b = genga.box(src(PLAIN))
assert b and all(0 <= v <= 100 for v in b) and b[2] * b[3] / 100 < genga.WHOLE
assert genga.box(src(G)) is None and genga.box(src(T)) is None
css = genga.STYLE
assert css.index("--genga-h:44vh") < css.index("--genga-h:44svh"), "svh を知らないブラウザのために vh を先に"
narrow = css[css.index("@media (max-width:820px)"):]
assert "calc(var(--genga-h) * var(--genga-r))" in narrow and "writing-mode:horizontal-tb" in narrow, "狭い幅は絵の高さに上限、歌は絵の真下に横書き"
assert 'style="--genga-r:0.6024"' in hero or "--genga-r:" in hero, "包みの幅を絵の比から決める（枠の % がずれない）"
assert "writing-mode:vertical-rl" in css[:css.index("@media")], "広い幅は絵の横に縦書き"
# UX の見直し（幅 390）: 押せる所は 44px 以上。作りながら見る頁の畳みに余白と頁の皮の釦。英語の頁にも高さの上限。狭い幅だけ切り抜きを右に
assert ".genga-cap a{display:inline-flex;align-items:center;min-height:44px" in css
assert ".stage .genga-fold{padding:0 16px}" in css and re.search(r"\.genga-fold \[data-big\]\{[^}]*min-height:44px[^}]*border:1px solid var\(--accent\)", css)
assert ".genga-plain .genga-pic" in narrow and ".genga-head .genga-crop{display:block}" in narrow and ".genga-crop{display:none" in css[:css.index("@media")]

# 3. 作る時の畳み
fold = genga.fold(G)
assert f'<details class="genga genga-fold"><summary>{genga_words.HEAD}</summary>' in fold
assert f'src="/picture/{G}/page"' in fold and 'loading="lazy"' in fold and "querySelector('.genga-pic')" in fold, "畳みの中の絵を押しても重ねて開く"
assert "data-big" in fold and "<dialog" in fold and f'<a href="/picture/{G}/page"' not in fold, "頁を離れずに重ねて出す"
assert "genga.fold(sid)" in inspect.getsource(tsukuru.page) and "genga.fold(sid)" in inspect.getsource(techo_site.page)

# 4. 英語の頁・くずし字・額
en_page = en.toy_page(G, "tenji") if "look" in inspect.signature(en.toy_page).parameters else en.toy_page(G)
assert f'src="/picture/{G}/page"' in en_page and 'alt="Picture from the book"' in en_page and genga_words.HEAD not in en_page and 'class="genga-songs"' not in en_page
assert "/page" not in en._picture(G), "英語の一覧の札は今の額のまま"
body = kuzushi.page(PLAIN)
assert f'src="/picture/{PLAIN}/page"' in body and '<div class="crop"' not in body, "歌の箱の無い玩具は、頁の全体を歌の箱で切らずに出す（くずし字の頁）"
crop = ROOT / "out/sources" / f"{PLAIN}.jpg"
if crop.exists():
    w, h = genga.size(crop)
    fr = skin.frame(PLAIN)
    assert f"aspect-ratio:{w}/{h};background-size:contain" in fr, "額は絵の比のまま（縦横を別々に伸ばさない）"
assert "background-size:112% 112%" not in skin.frame(PLAIN) and "background-size:112%" not in skin.frame(G)

# 5. 写しが無くても止まらない。一覧は切り抜きのまま
genga.page_file(src(PLAIN)).unlink()
plain = toy_page(PLAIN, "tenji")
assert "<h1>" in plain and f"/picture/{PLAIN}/page" not in plain
assert genga.fold(PLAIN) == "" or f"/picture/{PLAIN}/page" not in genga.fold(PLAIN)
listing = toys.page("tenji")
assert "url(/picture/" in listing and not re.search(r"/picture/[^)\"]*/page", listing), "一覧の小さい絵は今の切り抜きのまま"


def get(server, path):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{server.server_address[1]}{path}", timeout=30) as r:
            return r.status, r.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        return e.code, ""


for public_open in (False, True):
    server = serve(0, public_open=public_open)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        assert get(server, f"/picture/{G}/page") == (200, "image/jpeg"), public_open
        assert get(server, f"/picture/{PLAIN}/page")[0] == 404, "写しの無い頁は 404"
        assert get(server, "/picture/NDL-1187053-R0000099-L/page")[0] == 404
        assert get(server, f"/toy/{G}")[0] == 200
    finally:
        server.shutdown()
        server.server_close()
print("ok 原画は頁の全体で歌と組になり、作る時は頁を離れずに大きく見られる")
