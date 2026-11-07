"""うつしの位置づけと想定する相手の字（本人の言葉 11-07 昼「想定する相手は教育分野から、みんなが使える公開のサービスへ広げる。
utsushi は paper to toy の具体例、という説明をサイトに」。作り直しの設計 0.8）の試験。

見る事:
1. 序の頁: 位置づけの字が、題の下の一言のすぐ後・本の段の前に 1 回。相手の字が、なぜ の節の玩具の定義の後に 1 回（合言葉なしの場でも）
2. English の頁: 同じ中身が頭（紹介の文の前）に 1 回。紹介の文（J-030 と同じ文）は変えない
3. 入口の最初の画面は『江都二色』の話だけのまま（#517 の本人の決め）で、位置づけの字を足さない
"""
import os
import re
import tempfile
import threading
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ.pop("ANTHROPIC_API_KEY", None)

from web import about, en  # noqa: E402
from web.play_server import serve  # noqa: E402
from web.skin import esc  # noqa: E402

for opened in (False, True):
    server = serve(0, public_open=opened)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    get = lambda path: urllib.request.urlopen(base + path, timeout=120).read().decode()  # noqa: E731

    # ---- 1 序の頁
    page = get("/about")
    pos, aud = esc(about.POSITION), esc(about.AUDIENCE)
    assert page.count(pos) == 1 and page.count(aud) == 1, ("序の頁に 1 回ずつ", opened)
    concept = page.index(esc(about.CONCEPT))
    assert concept < page.index(pos) < page.index("江都二色", page.index(pos) + len(pos)), "位置づけは題の下の一言のすぐ後、本の段の前"
    why = page.index("<h2>なぜ</h2>")
    assert why < page.index(esc(about.DEFINITION)) < page.index(aud) < page.index("</section>", why), "相手の字は なぜ の節の、玩具の定義の後"
    assert "paper to toy" in about.POSITION and "公開のサービス" in about.AUDIENCE

    # ---- 2 English
    page = get("/en")
    assert page.count(en.POSITION) == 1 and page.index(en.POSITION) < page.index(en.INTRO[0]), ("English の頭に 1 回", opened)
    assert all(page.count(x) == 1 for x in en.INTRO), "紹介の文は今のまま"

    # ---- 3 入口
    top = get("/")
    assert "paper to toy" not in top and pos not in top and aud not in top, ("入口の最初の画面に足さない", opened)
    server.shutdown()

print("ok うつしの位置づけ（paper to toy の 1 つの例）と相手の字: 序の頁の頭と なぜ の末、English の頭に 1 回ずつ。入口には足さない")
