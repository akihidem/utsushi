"""デモの一周を外の機器から開く合言葉の門（本人の決定 A、11-04）。合言葉の無い人は入れず、トンネルの https の頁からの送信は受ける。
合言葉を付けない時は今までどおり（トンネルの名前も断る）。"""
import os
import tempfile
import threading
import urllib.error
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from web.play_server import TUNNEL_HOST, serve  # noqa: E402

KEY = "k" * 24
TUN = "demo-abc" + TUNNEL_HOST.split("+", 1)[1].replace("\\", "")  # サーバが受ける形から作る見本の名前（実在のトンネルではない）

try:
    serve(0, public_key="short")
    raise SystemExit("短い合言葉を受けてしまった")
except ValueError:
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


opener = urllib.request.build_opener(NoRedirect)


def call(port, path, host, cookie=None, form=None, origin=None):
    headers = {"Host": host}
    if cookie:
        headers["Cookie"] = cookie
    data = None
    if form is not None:
        data = form.encode()
        headers |= {"Content-Type": "application/x-www-form-urlencoded", "Origin": origin or f"https://{host}"}
    try:
        r = opener.open(urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data, headers=headers))
        return r.status, dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers)


plain = serve(0)
pp = plain.server_address[1]
threading.Thread(target=plain.serve_forever, daemon=True).start()
assert call(pp, "/", f"127.0.0.1:{pp}")[0] == 200, "合言葉なしの時は今までどおり"
assert call(pp, "/", TUN)[0] == 403, "合言葉なしの時はトンネルの名前を断る"
plain.shutdown()

pub = serve(0, public_key=KEY)
port = pub.server_address[1]
assert pub.server_address[0] == "127.0.0.1", "口は手元のまま（外からはトンネルだけ）"
threading.Thread(target=pub.serve_forever, daemon=True).start()
assert call(port, "/", TUN)[0] == 403, "合言葉の無い人は入れない"
assert call(port, "/?k=wrong", TUN)[0] == 403
code, h = call(port, f"/gallery?k={KEY}", TUN)
assert code == 303 and h["Location"] == "/gallery" and f"utsushi_k={KEY}" in h["Set-Cookie"] and "Secure" in h["Set-Cookie"], (code, h)
jar = f"utsushi_k={KEY}"
assert call(port, "/gallery", TUN, jar)[0] == 200, "Cookie で入れる"
assert call(port, "/", "evil.example", jar)[0] == 403, "ほかの名前は合言葉があっても断る"
SID = "NDL-1187053-R0000005-L"
code, _ = call(port, f"/toy/{SID}/own", TUN, jar, "name=x")
assert code in (200, 303, 422), "トンネルの https の頁からの送信は受ける"
assert call(port, f"/toy/{SID}/own", TUN, jar, "name=x", origin="https://evil.example")[0] == 403, "別のサイトからは断る"
assert call(port, f"/toy/{SID}/own", TUN, None, "name=x")[0] == 403, "合言葉の無い送信は断る"
pub.shutdown()
print("ok")
