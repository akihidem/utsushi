"""ループ1（Issue #335）: 話した考えから作った紙（OWN-n）と、話した字が刷られた手順の紙は、作った本人の画面からしか開かない。合言葉なしの場では開かない（J-028 の線）。

見る線:
- その場限りの印（who）を確かめて頼んだ人にだけ、紙の鍵を cookie で渡す。URL に載せないので、URL を渡されても開かない。
- 鍵の無い人・別の案の鍵の人には、絵も PDF も SVG も手順の紙も開かない（在るかどうかも言わない）。頼んだ後の頁も、採る釦も同じ。
- 同じ印の人が押し直すと、鍵を受け取り直せる。書いて立てた仮説の紙は今までどおり。
- 合言葉なしの場: 書いた物も含めて OWN-n の紙は開かない。紙を作る節も受け口も閉じる。
"""
import os
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

DATA = tempfile.mkdtemp()
os.environ["OMOCHAE_DATA"] = DATA
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(DATA, "api-usage.jsonl")  # 本物の台帳に書かない（#151）

from api import words  # noqa: E402
from omochae import hypotheses, talk_log  # noqa: E402
from web import think_sheet  # noqa: E402
from web.play_server import out_dir, serve  # noqa: E402

G = "NDL-1187053-R0000005-L"
WHO, OTHER = "abcdefgh12", "zyxwvuts98"
SAID, SAID2 = "割り箸の柄で押したら大きく開くと思う", "柄を長くしたい"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


opener = urllib.request.build_opener(NoRedirect)


def start(**kw):
    server = serve(0, **kw)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


def send(base, path, data=None, cookie=""):
    headers = {"Content-Type": "application/x-www-form-urlencoded", "Origin": base}
    if cookie:
        headers["Cookie"] = cookie
    req = urllib.request.Request(base + path, data=urllib.parse.urlencode(data).encode() if data is not None else None, method="POST" if data is not None else "GET", headers=headers)
    try:
        r = opener.open(req)
        return r.status, r.read(), r.headers
    except urllib.error.HTTPError as e:
        return e.code, e.read(), e.headers


def ask(base, who, text):
    """考えを残して頼む。Returns (Location, cookie の「名=値」)。"""
    talk_log.add(G, "think", text, who=who)
    code, _, h = send(base, f"/toy/{G}/think-sheet", {"who": who})
    assert code == 303, code
    return h["Location"], h["Set-Cookie"].split(";")[0]


server, base = start()
loc, key = ask(base, WHO, SAID)
token = urllib.parse.parse_qs(urllib.parse.urlsplit(loc).query)["at"][0][len("think-"):]
attrs = send(base, f"/toy/{G}/think-sheet", {"who": WHO})[2]["Set-Cookie"]
assert "HttpOnly" in attrs and "SameSite=Lax" in attrs and "Max-Age" not in attrs, attrs  # 画面の JS から読まない。ブラウザを閉じれば消える
assert "Path=/;" in attrs or attrs.endswith("Path=/"), attrs
assert key.split("=", 1)[1] == token and token not in key.split("=", 1)[0], "鍵の名前に値を入れない"

# 頼んだ後の頁は、鍵のある人だけに字を見せる（URL だけでは開かない）
path = loc.split("#")[0]
w = words.by_token(G, token)
assert not words.fill_think(w["id"], words.think_result(w["base_params"], {"push_part": "stick", "pusher_height": 84}), "作る側")[1]
assert SAID in send(base, path, cookie=key)[1].decode(), "本人には見える"
for c in ("", "utsushi_own_W-9999=nothing"):
    assert SAID not in send(base, path, cookie=c)[1].decode(), "URL を渡されても、話した字は見えない"

# 採る釦も、鍵のある人だけ
assert send(base, f"/toy/{G}/think-ok", {"t": token})[0] == 422, "印を知っていても、鍵が無いと採れない"
assert hypotheses.own_hypotheses(G) == [] and not out_dir(G).exists()
assert send(base, f"/toy/{G}/think-ok", {"t": token}, cookie=key)[0] == 303
oid = words.by_token(G, token)["own_id"]
names = sorted(p.name for p in out_dir(G).glob(f"{oid}_v*"))
assert {f"{oid}_v1.pdf", f"{oid}_v1.png", f"{oid}_v1_tejun.pdf", f"{oid}_v1_tejun.png"} <= set(names), names

# 紙は、作った本人にだけ開く
_, other_key = ask(base, OTHER, SAID2)
for name in names:
    if name.endswith((".pdf", ".png", ".svg")) and "_after" not in name:
        code, body, _ = send(base, f"/sheet/{G}/{name}", cookie=key)
        assert code == 200 and body, (name, code)
        for c in ("", other_key, "utsushi_own_W-0001=nothing"):
            code, body, _ = send(base, f"/sheet/{G}/{name}", cookie=c)
            assert code == 404 and SAID.encode() not in body, (name, c, code)
        assert send(base, f"/sheet/{G}/{name}?t={token}")[0] == 404, "URL に印を付けても開かない"
# 本人の頁のリンクと絵が開く（鍵で）
page = send(base, path, cookie=key)[1].decode()
assert f"/sheet/{G}/{oid}_v1.pdf" in page and f"/sheet/{G}/{oid}_v1.png" in page
assert SAID not in send(base, f"/toy/{G}", cookie=other_key)[1].decode(), "ほかの人の頁に出ない"

# 同じ印の人が押し直すと、鍵を受け取り直せる（ブラウザを閉じた後でも、同じ画面の印があれば）
code, _, h = send(base, f"/toy/{G}/think-sheet", {"who": WHO})
assert code == 303 and h["Set-Cookie"].split(";")[0] == key
code, _, h = send(base, f"/toy/{G}/think-sheet", {"who": "nobody0001"})
assert code == 422 and not h.get("Set-Cookie"), "ほかの印には渡さない"

# 書いて立てた仮説の紙は今までどおり（鍵なしで開く）
typed, _ = hypotheses.save_own(G, "書いた案", "書いて立てた動かし方", "右の図")
assert send(base, f"/toy/{G}/print-own", {"id": typed["id"]})[0] == 303
assert send(base, f"/sheet/{G}/{typed['id']}_v1_free.pdf")[0] == 200
server.shutdown()

# ── 合言葉なしの場 ──
server, base = start(public_open=True)
for name in (f"{oid}_v1.pdf", f"{oid}_v1.png", f"{oid}_v1_tejun.pdf", f"{typed['id']}_v1_free.pdf"):
    assert send(base, f"/sheet/{G}/{name}", cookie=key)[0] == 404, name
assert send(base, f"/sheet/{G}/H-A_v1.pdf")[0] in (200, 404), "元の仮説の道は変えない"
code, body, _ = send(base, f"/toy/{G}")
assert code == 200 and think_sheet.GO not in body.decode() and f"{typed['id']}_v1_free.pdf" not in body.decode(), "開かない紙の入口を出さない"
talk_log.add(G, "think", "公開の場で話した考え", who="pubwho0001")
before = len(words.waiting())
assert send(base, f"/toy/{G}/think-sheet", {"who": "pubwho0001"})[0] == 403
assert send(base, f"/toy/{G}/think-ok", {"t": token}, cookie=key)[0] == 403
assert len(words.waiting()) == before, "合言葉なしの場では案を作らない"
assert SAID not in send(base, path, cookie=key)[1].decode(), "鍵があっても字を出さない"
server.shutdown()
print("ok")
