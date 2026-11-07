"""English の頭の、paper to toy の短い説明（英語 3 文）の試験。本人の言葉（11-07 昼「utsushi は paper to toy の具体例、という説明をサイトに」）の English の側。
窓口の決め（11-07）: 序の頁の位置づけは序の頁と README の担当の作りでそろえ、English の頭には英語 3 文を入れる。

見る事:
1. English の頁の頭（紹介の文の前）に 3 文が 1 回（合言葉なしの場でも）。紹介の文（J-030 と同じ文）は変えない
2. 3 文は材料の字のまま（文の数が 3）
3. 入口と序の頁には、この英語の段を足さない（序の頁の位置づけは別の作り）
"""
import os
import re
import tempfile
import threading
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ.pop("ANTHROPIC_API_KEY", None)

from web import en  # noqa: E402
from web.play_server import serve  # noqa: E402
from web.skin import esc  # noqa: E402

pos = esc(en.POSITION)
assert len(re.findall(r"[.!?](?:\s|$)", en.POSITION)) == 3 and en.POSITION.startswith("Paper to toy is an engine"), "材料の英語 3 文"

for opened in (False, True):
    server = serve(0, public_open=opened)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    get = lambda path: urllib.request.urlopen(base + path, timeout=120).read().decode()  # noqa: E731

    # ---- 1 English の頭
    page = get("/en")
    assert page.count(pos) == 1 and page.index(pos) < page.index(en.INTRO[0]), ("English の頭に 1 回", opened)
    assert all(page.count(x) == 1 for x in en.INTRO), "紹介の文は今のまま"

    # ---- 3 入口と序の頁には足さない
    for path in ("/", "/about"):
        assert pos not in get(path), ("足さない", path, opened)
    server.shutdown()

print("ok English の頭に paper to toy の短い説明（英語 3 文）を 1 回。紹介の文は今のまま、入口と序の頁には足さない")
