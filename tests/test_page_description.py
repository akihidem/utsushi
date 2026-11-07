"""頁の description（本人の言葉 11-08「まずはAIフレンドリーに。…AIにも選んでもらいたい」）。本物の API は呼ばない。

統括の決め（11-08）: description には、今ある字で合う物だけを入れ、合う物が無い頁は空ける（新しい字を作らない）。
見る事:
1. 入れた頁の description は、決めた今ある字と一字も同じで、その字は頁（入口は序の頁）にもう出ている。og:title は <title> と同じ
2. 空けた頁には description を出さない（空けた頁の一覧は、PR の本文の一覧と同じ物をここに置く）
3. 英語の頁では、同じ鍵で英語に訳される（日本語の字が残らない）
4. 読み手の AI への頼みの字が無い（J-015）
"""
import html
import os
import re
import tempfile
import threading
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from api import ask  # noqa: E402
from web import about, en, kaizen_judge, kumitate, otona, techo_site  # noqa: E402
from web.play_server import serve, sources  # noqa: E402

ask._key_present = lambda: False  # 合言葉なしの場は鍵のある所で立たない。鍵のある機械でも同じに動かす
G = "NDL-1187053-R0000005-L"
PLAIN = next(s for s in sources() if not kumitate.available(s))  # 立体の無い玩具（組み立ての頁は組み方の節だけ）
DESCRIBED = {  # 道 → (description の字, その字がもう出ている頁)
    "/": (about.PREMISE[0], "/about"),
    "/about": (about.PREMISE[0], "/about"),
    "/otona": (otona.SECTIONS[0][2][0], "/otona"),
    "/gallery": (techo_site.GALLERY_LEAD, "/gallery"),
    "/kaizen": (kaizen_judge.LEAD, "/kaizen"),
    f"/toy/{G}/kumitate": (kumitate.LEAD, f"/toy/{G}/kumitate"),
    f"/toy/{PLAIN}/kumitate": (kumitate.STEPS_LEAD, f"/toy/{PLAIN}/kumitate"),  # 頁に無い「指で回して見られます」を言わない
    "/en": (en.POSITION, "/en"),
}
EMPTY = [f"/toy/{G}", f"/toy/{G}/techo", f"/toy/{G}/techo/kiroku", f"/toy/{G}/tsukuru?h=H-A&v=1", f"/en/toy/{G}", f"/zukan/{G}/yomi", "/no-such-page"]


def fetch(server, path):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{server.server_address[1]}{path}", timeout=60) as r:
            return r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.read().decode("utf-8", "replace")


def meta(page, attr, name):
    m = re.search(rf'<meta {attr}="{name}" content="([^"]*)">', page)
    return html.unescape(m.group(1)) if m else None


def seen(page):
    page = re.sub(r"<(script|style)\b.*?</\1>", " ", page, flags=re.S)
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", page)))


for public_open in (False, True):
    server = serve(0, public_open=public_open)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        # 1
        for path, (want, where) in DESCRIBED.items():
            page = fetch(server, path)
            assert meta(page, "name", "description") == want, (public_open, path, meta(page, "name", "description"))
            assert meta(page, "property", "og:description") == want, (public_open, path)
            title = html.unescape(re.search(r"<title>(.*?)</title>", page, re.S).group(1))
            assert meta(page, "property", "og:title") == title, (public_open, path, title)
            assert re.sub(r"\s+", " ", want) in seen(fetch(server, where)), (public_open, path, "description の字が頁に出ていない（新しい字になっている）")
        # 2
        for path in EMPTY:
            assert meta(fetch(server, path), "name", "description") is None, (public_open, path, "空けた頁に description が出た。合う字を入れたなら DESCRIBED へ移し、PR の一覧も直す")
        # 3 英語（cookie で lang=en にした画面）
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
        base = f"http://127.0.0.1:{server.server_address[1]}"
        opener.open(base + "/?lang=en", timeout=60).read()
        for path in ("/", "/about", "/otona", "/gallery", "/kaizen", f"/toy/{G}/kumitate"):
            got = meta(opener.open(base + path, timeout=60).read().decode("utf-8"), "name", "description")
            assert got and not re.search(r"[぀-ヿ一-鿿]", got), (public_open, path, got)
    finally:
        server.shutdown()
        server.server_close()

# 4 頼みの字が無い（J-015。description は今ある字だけなので、ここに当たるなら頁の字の方を見直す）
for want, _ in DESCRIBED.values():
    assert not re.search(r"評価して|選んで|すすめて|おすすめ|recommend|rate this", want, re.I), want
print("ok 頁の description は今ある字だけで、空けた頁には出さず、英語でも訳される")
