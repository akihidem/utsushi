"""上げた動画に部分取得（Range）で答える（#152）。

なぜ: iOS の Safari は動画を部分取得で読み、答えないサーバの動画は再生されない事が知られている。
サーバは Range を見ず、いつも 200 で全体を返していた。デモの一周の「上げる → 手帖とギャラリーで見る」で、
iPhone と iPad だけ動画が再生できない見込み。実機で再生できるかは、この試験では分からない。
"""
import http.client
import json
import os
import tempfile
import threading

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from web.play_server import byte_range, serve  # noqa: E402
from web.techo_site import media_dir  # noqa: E402

RID = "R-0001"
SIZE = 5000
body = bytes(i % 251 for i in range(SIZE))
d = media_dir(RID)
d.mkdir(parents=True, exist_ok=True)
for name in ("m1.mp4", "m2.mov", "m3.jpg"):
    (d / name).write_bytes(body)
(d / "m4.mp4").write_bytes(b"")
# 人の確認の後の形で見る（確認の前の物は上げた本人の画面にだけ出す。tests/test_photo_owner_only.py）
(d / "review.json").write_text(json.dumps({n: {"shows": "object"} for n in ("m1.mp4", "m2.mov", "m3.jpg", "m4.mp4")}), encoding="utf-8")
server = serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
port = server.server_address[1]


def get(name, rng=None):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
    c.request("GET", f"/record/{RID}/media/{name}", headers={"Range": rng} if rng else {})
    r = c.getresponse()
    data = r.read()
    c.close()
    return r.status, data, r.headers


# Range の無い要求は今までどおり全体を返し、部分取得できる事を知らせる。
code, data, h = get("m1.mp4")
assert code == 200 and data == body and h["Accept-Ranges"] == "bytes" and h["Content-Type"] == "video/mp4", (code, dict(h))
# 答える形: (送る Range, 始め, 終わり)。最初の 2 つは iOS が最初に送る形と、続きを読む形。
for rng, a, b in (("bytes=0-1", 0, 1), ("bytes=20-29", 20, 29), (f"bytes={SIZE - 5}-", SIZE - 5, SIZE - 1), ("bytes=-5", SIZE - 5, SIZE - 1),
                  (f"bytes=20-{SIZE * 9}", 20, SIZE - 1), (f"bytes=-{SIZE * 9}", 0, SIZE - 1), ("bytes=0-", 0, SIZE - 1)):
    code, data, h = get("m1.mp4", rng)
    assert code == 206, (rng, code)
    assert data == body[a:b + 1], (rng, len(data), "範囲の中身が違う")
    assert h["Content-Range"] == f"bytes {a}-{b}/{SIZE}", (rng, h["Content-Range"])
    assert h["Content-Length"] == str(b - a + 1) and h["Accept-Ranges"] == "bytes", (rng, dict(h))
    assert h["Content-Type"] == "video/mp4" and h["X-Content-Type-Options"] == "nosniff", (rng, dict(h))
code, data, h = get("m2.mov", "bytes=0-1")
assert code == 206 and h["Content-Type"] == "video/quicktime" and data == body[:2], (code, dict(h))
# 範囲の外は 416 で、全体の大きさを言う。
for name, size, rng in (("m1.mp4", SIZE, f"bytes={SIZE}-"), ("m1.mp4", SIZE, f"bytes={SIZE + 7}-{SIZE + 9}"), ("m1.mp4", SIZE, "bytes=-0"), ("m4.mp4", 0, "bytes=0-"), ("m4.mp4", 0, "bytes=-5")):
    code, data, h = get(name, rng)
    assert code == 416 and data == b"" and h["Content-Range"] == f"bytes */{size}", (name, rng, code, h["Content-Range"])
# 読めない形と複数の範囲は、Range が無いものとして全体を返す（決まりの内で、再生も止めない）。
for rng in ("bytes=abc", "chars=0-1", "bytes=", "bytes=-", "bytes=5-2", "bytes=0-1,3-4"):
    code, data, _ = get("m1.mp4", rng)
    assert code == 200 and data == body, (rng, code, len(data))
assert byte_range("bytes=٠-١", SIZE) is None, "半角の数字だけを読む（この形はヘッダに載せられないので、関数で見る）"
# 写真は同じ道で出すので、同じ形で答える。無いファイルは今までどおり 404 のまま。
code, data, h = get("m3.jpg", "bytes=0-1")
assert code == 206 and h["Content-Type"] == "image/jpeg" and data == body[:2], (code, dict(h))
assert get("m9.mp4", "bytes=0-1")[0] == 404
server.shutdown()
print("ok 部分取得の答え 7 通り・範囲の外 5 通り・読めない形 7 通り")
