"""応答の守りの頭を見る（公開の前の点検 U18・U20。本人の決め 11-07「(a) を出す」）。

なぜ要るか: 公開のデモはトンネル（Cloudflare）の先にあり、写真や PDF の拡張子は途中で溜め置かれうる。溜め置かれると、上げた人にだけ
出す確かめる前の写真や、その人だけの紙が、同じ URL を開いた別の人に返る。また、頭が無いと別のサイトの枠に入れて押させる形
（クリックジャッキング）を防げない。

見る事:
1. 頁（入口・玩具の頁・断りの頁）の応答に、共有の溜め置きを止める頭（private, no-store）・ほかのサイトの枠に入れさせない頭（X-Frame-Options:
   SAMEORIGIN と CSP の frame-ancestors 'self'。同じ origin の枠は開く。試験が手帖を同じ origin の枠で開くため）・Referrer-Policy・nosniff が付く
2. 絵と紙は、同じ人の端末では溜めてよい（private だけ。no-store にしない）。JSON は頁と同じく no-store
3. Referrer-Policy は same-origin（no-referrer にすると、ブラウザは同じ頁からのフォームの POST に Origin: null を付け、書き込みの口の
   Origin の照らしが全部断るため）
"""
import os
import tempfile
import threading
import urllib.error
import urllib.request

_data = tempfile.TemporaryDirectory()
os.environ["OMOCHAE_DATA"] = _data.name
os.environ.pop("ANTHROPIC_API_KEY", None)

from web import play_server  # noqa: E402

G = "NDL-1187053-R0000005-L"
server = play_server.serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"


def head_of(path):
    try:
        r = urllib.request.urlopen(base + path, timeout=60)
    except urllib.error.HTTPError as e:
        r = e
    r.read()
    return r.status, {k.lower(): v for k, v in r.headers.items()}


try:
    # 1. 頁の応答
    for path, want in (("/", 200), (f"/toy/{G}", 200), ("/no-such-page", 404)):
        code, h = head_of(path)
        assert code == want, (path, code)
        assert h.get("cache-control") == "private, no-store", (path, h.get("cache-control"))
        assert h.get("x-frame-options") == "SAMEORIGIN" and "frame-ancestors 'self'" in h.get("content-security-policy", ""), (path, h)
        assert h.get("referrer-policy") == "same-origin" and h.get("x-content-type-options") == "nosniff", (path, h)
finally:
    server.shutdown()

# 2. 絵と紙は private だけ・JSON は no-store
g = dict(play_server.guard_headers("image/jpeg"))
assert g["Cache-Control"] == "private", g
assert dict(play_server.guard_headers("application/pdf"))["Cache-Control"] == "private"
assert dict(play_server.guard_headers("application/json; charset=utf-8"))["Cache-Control"] == "private, no-store"
# 3. 書き込みの口の Origin の照らしを壊さない
assert all(v != "no-referrer" for k, v in play_server.guard_headers("text/html; charset=utf-8") if k == "Referrer-Policy")
print("ok 応答の守りの頭（頁は private, no-store・枠に入れさせない・Referrer-Policy は same-origin・絵と紙は private だけ・JSON は no-store）")
