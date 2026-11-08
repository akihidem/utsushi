"""サイト全体の資源の上限（安全の事項 4 への対応・web.load_guard）。

見る事:
1. 写真と動画の変換の入口（Gate）: 同時に回す数（2）を越えた分は待ち、待てる数（4）を越えた分はすぐ断る。待つ長さを越えたら断る。空けば次が入る
2. 置き場の合計の予約（Reserve）: 書き終わる前の分も数えるので、同時に送られた分の合計で上限を越えない。書き終えたら（失敗でも）外す
3. 本物の口: 写真と動画の口は、変換の入口が溢れた時だけ 503 で本文を空にして断る（手帖は前からの字を出す）。ふつうの量では前のまま（422・201）。
   合言葉付きの場にも合計の止めがあり、予約中の分も数えて越えたら 507（前は公開の場だけ・今の合計＋今回の長さだけ）
4. 同時に処理する要求の数（LimitedServer）: 上限を越えた要求は読まずに 503。空けば前のまま開く
5. 字にする前の声の待ち行列に長さの上限があり、満ちたら入れない（落ちない）
"""
import http.client
import http.cookiejar
import json
import os
import pathlib
import queue
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
import sys  # noqa: E402

sys.path.insert(0, str(ROOT / "src"))
os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(os.environ["OMOCHAE_DATA"], "api-usage.jsonl")

from omochae import hypotheses, voice_text  # noqa: E402
from web import load_guard, play_server, techo_site  # noqa: E402

# 1. 変換の入口
assert (load_guard.MEDIA_SLOTS, load_guard.MEDIA_WAIT) == (2, 4)
g = load_guard.Gate(slots=2, wait_max=1, wait_s=5.0)
assert g.enter() and g.enter(), "同時に 2 本までは待たずに入る"
got = []
t = threading.Thread(target=lambda: got.append(g.enter()))
t.start()
time.sleep(0.2)
assert g.waiting == 1, "3 本目は待つ"
assert g.enter() is False, "待てる数を越えた分はすぐ断る"
g.leave()  # 1 本空く → 待っていた分が入る
t.join(5)
assert got == [True] and g.waiting == 0
short = load_guard.Gate(slots=1, wait_max=1, wait_s=0.2)
assert short.enter() and short.enter() is False, "待つ長さを越えたら断る"
short.leave()
assert short.enter(), "空けば次が入る"

# 2. 置き場の合計の予約
r = load_guard.Reserve()
assert r.take(0, 30, 50) and not r.take(0, 30, 50), "書き終わる前の分も数える（前は数え合わず、2 本とも通った）"
r.give(30)
assert r.take(0, 30, 50) and r.reserved == 30
r.give(30)
assert r.reserved == 0

# 3. 本物の口
assert techo_site.MEDIA_TOTAL == techo_site.PUBLIC_MEDIA_TOTAL == 2 * 1024 ** 3
server = play_server.serve(0)
assert isinstance(server, load_guard.LimitedServer) and isinstance(server.media_gate, load_guard.Gate) and isinstance(server.media_reserve, load_guard.Reserve)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))


def call(path, body, ctype, ip="203.0.113.9"):
    req = urllib.request.Request(base + path, data=body, headers={"Origin": base, "Content-Type": ctype, "Cf-Connecting-Ip": ip})
    try:
        with op.open(req) as x:
            return x.status, x.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


G = "NDL-1187053-R0000005-L"
H = hypotheses.sheet_of(G)["id"]
form = lambda d: urllib.parse.urlencode(d).encode()  # noqa: E731
assert call(f"/toy/{G}/print", form({"hypothesis": H}), "application/x-www-form-urlencoded")[0] == 200
rid = json.loads(call(f"/toy/{G}/record-json", form({"hypothesis": H, "result": "動いた"}), "application/x-www-form-urlencoded")[1])["id"]
assert call(f"/record/{rid}/media", b"x", "image/png")[0] == 422, "ふつうの量では前のまま（読めない中身は 422）"
# 変換の入口が溢れた時だけ 503・本文は空
real_gate = server.media_gate
server.media_gate = load_guard.Gate(slots=1, wait_max=0, wait_s=0.1)
assert server.media_gate.enter()
code, body = call(f"/record/{rid}/media", b"x", "image/png")
assert code == 503 and body == b"", (code, body)
server.media_gate.leave()
assert call(f"/record/{rid}/media", b"x", "image/png")[0] == 422, "空けば前のまま"
server.media_gate = real_gate
# 合言葉付きの場の合計の止め（予約中の分も数える）。上限の手前まで予約を埋めて、今回の分で越える形
assert not getattr(server, "public_open", False)
used = techo_site.media_bytes()
assert server.media_reserve.take(used, techo_site.MEDIA_TOTAL - used - 1, techo_site.MEDIA_TOTAL)
code, body = call(f"/record/{rid}/media", b"xx", "image/png")
assert code == 507 and body == b"", (code, body)
server.media_reserve.give(techo_site.MEDIA_TOTAL - used - 1)
assert server.media_reserve.reserved == 0, "断った分と書き終えた分の予約は外れる"
assert call(f"/record/{rid}/media", b"x", "image/png")[0] == 422

# 4. 同時に処理する要求の数
assert load_guard.HTTP_MAX == server.http_max == 64
for _ in range(server.http_max):
    assert server._slots.acquire(blocking=False)
c = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=10)
c.request("GET", "/")
resp = c.getresponse()
assert resp.status == 503 and resp.getheader("Retry-After") == "30", resp.status
c.close()
for _ in range(server.http_max):
    server._slots.release()
with urllib.request.urlopen(base + "/", timeout=60) as x:
    assert x.status == 200, "空けば前のまま開く"
server.shutdown()

# 5. 声の待ち行列の長さ
assert voice_text.QUEUE_MAX == load_guard.VOICE_QUEUE_MAX
w = voice_text.Worker(tool=False)
assert w.jobs.maxsize == voice_text.QUEUE_MAX
assert all(voice_text.enqueue(w, f"v{n}") for n in range(voice_text.QUEUE_MAX))
assert voice_text.enqueue(w, "over") is False and w.jobs.qsize() == voice_text.QUEUE_MAX, "満ちたら入れない（落ちない）"
assert isinstance(w.jobs, queue.Queue)
print("ok 全体の資源の上限: 変換の入口（同時 2・待ち 4・待つ長さ）・合計の予約（合言葉付きの場にも）・同時の処理の数・声の待ち行列の長さ。ふつうの量では前のまま")
