"""サイトの北斎漫画の節（本人の決定 2026-11-05、#262: 案 1・2・3 を全部入れる）を試験で見る。

見る事（網につながず、偽の頁の画像で見る）:
- 絵の出所は国立国会図書館の PDM だけ。記録にある名前だけを道で出す。
- 切り出しは記録の枠のとおりで、足りない分だけ作る。
- 案 1 は白の序の頁、案 2 は黒の入口、案 3 は両方の序の頁。札が絵のそばに出る。玩具の頁と一覧には出さない。
- 動きは操作でだけ起きる。動きを減らす設定を見る。絵が無い時は壊れた絵を出さず、国立国会図書館への道を出す。
"""
import os
import pathlib
import sys
import tempfile
import threading
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
tmp = tempfile.TemporaryDirectory()
os.environ["OMOCHAE_DATA"] = f"{tmp.name}/data"

from PIL import Image  # noqa: E402

from omochae import hokusai as hk  # noqa: E402
from web import about, looks, toy, toys  # noqa: E402
from web import hokusai as site  # noqa: E402
from web.play_server import serve  # noqa: E402

hk.DIR = pathlib.Path(tmp.name) / "hokusai"
G = "NDL-1187053-R0000005-L"

# 権利: どの頁も国立国会図書館の PDM。札に同じ事を出す
for name, rec in hk.pages().items():
    assert rec["rights"] == "PDM" and rec["iiif"].startswith("https://dl.ndl.go.jp/") and "国立国会図書館" in rec["attribution"], name
    assert "（PDM）" in site.credit(rec) and "1878" in site.credit(rec) and rec["modification_note"] in site.credit(rec)
assert len(hk.figure_ids()) == 18

# 絵が無い時: 壊れた絵を出さず道を出す。黒の章は節ごと出さない
page = about.page("tenji")
assert "/hokusai/" not in page and "dl.ndl.go.jp/pid/851651" in page and "dl.ndl.go.jp/pid/851653" in page
assert site.scroll_section() == "" and 'id="hk-stack"' not in page

# 偽の頁で切り出す。網は使わない（頁の画像を先に置く）
hk.DIR.mkdir(parents=True)
for name in hk.pages():
    Image.new("RGB", (1000, 800), (200, 180, 140)).save(hk.path_of(name), "JPEG")
assert hk.fetch() == []
c = hk.pages()[hk.WHEEL_PAGE]["crops"][0]
with Image.open(hk.path_of(f"{hk.WHEEL_PAGE}-{c['id']}")) as im:
    assert im.size == (round(1000 * (c["box_pct"][0] + c["box_pct"][2]) / 100) - round(1000 * c["box_pct"][0] / 100), round(800 * (c["box_pct"][1] + c["box_pct"][3]) / 100) - round(800 * c["box_pct"][1] / 100)), im.size
# 取り直さない（足りない分だけ）
stamp = hk.path_of(hk.FLIP_PAGE).stat().st_mtime_ns
assert hk.fetch() == [] and hk.path_of(hk.FLIP_PAGE).stat().st_mtime_ns == stamp

# 案 1: 白の序の頁だけ。押すと動き、開いただけでは動かない
white, black = about.page("tenji"), about.page("zine")
assert 'id="hk-stack"' in white and 'id="hk-stack"' not in black
assert white.count(f"/hokusai/{hk.FLIP_PAGE}-") == 18 and "18 人を順に重ねる" in white
assert "addEventListener('click'" in site.FLIP_SCRIPT and "prefers-reduced-motion" in site.FLIP_SCRIPT
assert "setInterval" not in site.FLIP_SCRIPT.split("addEventListener('click'")[0], "開いただけで動かさない"
# 本人が採った文（11-05、#318）。一字でも変わったら落ちるように、ここに決定の文を書く
assert "絵は、動いているとちゅうを止めてかいています。どう動いたかは、紙で作ってたしかめます。" in white
assert "江戸の人は、糸車のしくみも、平らな紙に奥ゆきを見せる線のかき方も、絵で残しました。うつしの型紙は、その絵から線をおこして、紙で作ってたしかめます。" in white
# 案 3: 両方の序の頁
for page in (white, black):
    assert 'id="hokusai-mech"' in page and f"/hokusai/{hk.WHEEL_PAGE}-wheel.jpg" in page and f"/hokusai/{hk.LINES_PAGE}-left.jpg" in page and f"/hokusai/{hk.LINES_PAGE}-right.jpg" in page
    assert "糸車" in page and "（PDM）" in page
# 案 2: 入口の章の頭。玩具の章より前。前は黒の入口にだけあった。本人の決定（11-06）「ページは白案で統一します。黒案にだけある要素は白案に入れてください」で、
# 白の入口にも同じ節を白の色で置く（字と動きは同じ）
zine, tenji = looks.PAGES["zine"](), looks.PAGES["tenji"]()
for page in (zine, tenji):
    assert 'id="zn-hokusai"' in page and page.index('id="zn-hokusai"') < page.index('id="look-1"') and "（PDM）" in page
assert 'class="zn-hk tj-hk"' in tenji and 'class="zn-hk"' in zine and site.WHITE_SCROLL_STYLE in tenji and site.WHITE_SCROLL_STYLE not in zine
assert tenji.index('class="tj-hall"') < tenji.index('id="zn-hokusai"'), "白の入口の最初の画面（題の間と えらぶ）の後"

assert "prefers-reduced-motion" in site.SCROLL_SCRIPT and "IntersectionObserver" not in site.SCROLL_SCRIPT and "prefers-reduced-motion" in site.SCROLL_STYLE

# 玩具の頁と一覧には置かない
for page in (toy.toy_page(G), toys.page("tenji"), toys.page("zine")):
    assert "/hokusai/" not in page and "北斎" not in page

# 道: 記録にある名前だけ
server = serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"
assert urllib.request.urlopen(f"{base}/hokusai/{hk.FLIP_PAGE}-L1a.jpg", timeout=30).headers["Content-Type"] == "image/jpeg"
for bad in ("nothing", "..%2f..%2fsecret", f"{hk.FLIP_PAGE}-L1a.jpg.part"):
    try:
        urllib.request.urlopen(f"{base}/hokusai/{bad}.jpg", timeout=30)
        raise AssertionError(bad)
    except urllib.error.HTTPError as e:
        assert e.code == 404, bad
print("ok")
