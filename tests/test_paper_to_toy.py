"""English の頭の、うつしの位置づけ（英語 2 文）の試験。本人の言葉（11-07 昼「utsushi は paper to toy の具体例、という説明をサイトに」
「これからというよりは、みんなが使えるサービスとして作った」）の English の側。字は本人が採った（11-07「この英文でよい」）。

その後に paper to toy の仕組みの英語 3 文（材料の字のまま）。窓口の決め（11-07 130735）「/en の英語 3 文は #526 の 1 本にまとめる」。

見る事:
1. English の頁の頭（紹介の文の前）に、位置づけの 2 文 → 仕組みの 3 文の順で 1 回ずつ（合言葉なしの場でも）。紹介の文（J-030 と同じ文）は変えない
2. 位置づけは本人が採った字のまま。「これから」の向きの字（will grow・hope）は無い。仕組みは材料の 3 文のまま
3. 入口と序の頁には、この英語の段を足さない（序の頁の位置づけは #527）
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
ADOPTED = ("Utsushi is one example of paper to toy, using the toys in an Edo picture book. "
           "We made it as a service everyone can use, from schools, research, and museums to homes.")
assert en.POSITION == ADOPTED and len(re.findall(r"[.!?](?:\s|$)", en.POSITION)) == 2, "本人が採った 2 文のまま"
assert not re.search(r"\bwill\b|\bhope\b|\bgrow", en.POSITION), "これからの向きの字は使わない（本人の言葉 11-07 昼）"
assert en.ENGINE.startswith("Paper to toy is an engine") and len(re.findall(r"[.!?](?:\s|$)", en.ENGINE)) == 3, "材料の英語 3 文"
eng = esc(en.ENGINE)

for opened in (False, True):
    server = serve(0, public_open=opened)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    get = lambda path: urllib.request.urlopen(base + path, timeout=120).read().decode()  # noqa: E731

    # ---- 1 English の頭
    page = get("/en")
    assert page.count(pos) == 1 and page.count(eng) == 1 and page.index(pos) < page.index(eng) < page.index(en.INTRO[0]), ("English の頭に 2 文 → 3 文の順で 1 回ずつ", opened)
    assert all(page.count(x) == 1 for x in en.INTRO), "紹介の文は今のまま"

    # ---- 3 入口と序の頁には足さない
    for path in ("/", "/about"):
        body = get(path)
        assert pos not in body and eng not in body, ("足さない", path, opened)
    server.shutdown()

print("ok English の頭に、本人が採ったうつしの位置づけ（英語 2 文）と paper to toy の仕組み（英語 3 文）を 1 回ずつ。紹介の文は今のまま、入口と序の頁には足さない")
