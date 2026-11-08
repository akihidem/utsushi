"""サイト全体の資源の上限（安全の事項 4 への対応・web.load_guard）。

見る事:
1. 写真と動画の変換の入口（Gate）: 同時に回す数（2）を越えた分は待ち、待てる数（4）を越えた分はすぐ断る。待つ長さを越えたら断る。空けば次が入る
2. 置き場の合計の予約（Reserve）: 書き終わる前の分も数えるので、同時に送られた分の合計で上限を越えない。書き終えたら（失敗でも）外す
   予約は札で外す。台帳のファイルを渡すと、同じ台帳を使う別のプロセスの予約も数え、落ちたプロセスの予約は外れる（安全の事項 2 への対応）
3. 本物の口: 写真と動画の口は、変換の入口が溢れた時だけ 503 で本文を空にして断る（手帖は前からの字を出す）。ふつうの量では前のまま（422・201）。
   合言葉付きの場にも合計の止めがあり、予約中の分も数えて越えたら 507（前は公開の場だけ・今の合計＋今回の長さだけ）。
   予約の台帳は記録の置き場の中の共有のファイル。受け取り中の本文の合計（RECV_TOTAL）を越えた時だけ 503（安全の事項 2 への対応）
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
a = r.take(0, 30, 50)
assert a and not r.take(0, 30, 50), "書き終わる前の分も数える（前は数え合わず、2 本とも通った）"
r.give(a)
b = r.take(0, 30, 50)
assert b and r.reserved == 30
r.give(b)
assert r.reserved == 0
# 共有の台帳: 別に立てたサーバ（白と暗いなど）が同じ置き場を使う時、互いの予約を数える。前はサーバごとのメモリの中だけで、2 つが同時に
# 受けると上限を越えうった。別のプロセスの予約は、本物の別のプロセスで取って見る（落ちて外さなかった予約は、pid が居なくなると外れる）
import subprocess  # noqa: E402

book = pathlib.Path(tempfile.mkdtemp()) / ".reserve" / "media.json"
one, two = load_guard.Reserve(book), load_guard.Reserve(book)
c = one.take(0, 30, 50)
assert c and not two.take(0, 30, 50) and two.reserved == 30, "同じ台帳の予約を、別の入れ物からも数える"
one.give(c)
assert two.take(0, 30, 50) and one.reserved == 30
code = f"import sys; sys.path.insert(0, {str(ROOT / 'src')!r}); from web import load_guard; r = load_guard.Reserve({str(book)!r}); print(r.reserved, bool(r.take(0, 10, 50)), bool(r.take(0, 20, 50)))"
out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=60)
assert out.stdout.split() == ["30", "True", "False"], ("別のプロセスも同じ予約を数える", out.stdout, out.stderr)
assert one.reserved == 30, "外さずに終わったプロセスの予約は、pid が居ないので外れる"
for broken in ("[1, 2]", '{"a": 5, "b": [1], "c": {"x": 1}, "d": ["p", 3, 0]}', "null"):  # 形の違う台帳は、落ちずに空の台帳として扱う（別の目の気づき）
    book.write_text(broken, encoding="utf-8")
    d = one.take(0, 10, 50)
    assert d and one.reserved == 10, ("形の違う台帳で落ちない", broken)
    one.give(d)

# 3. 本物の口
assert techo_site.MEDIA_TOTAL == techo_site.PUBLIC_MEDIA_TOTAL == 2 * 1024 ** 3
server = play_server.serve(0)
assert isinstance(server, load_guard.LimitedServer) and isinstance(server.media_gate, load_guard.Gate) and isinstance(server.media_reserve, load_guard.Reserve)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"
jar = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def call(path, body, ctype, ip="203.0.113.9"):
    req = urllib.request.Request(base + path, data=body, headers={"Origin": base, "Content-Type": ctype, "Cf-Connecting-Ip": ip})
    try:
        with op.open(req) as x:
            return x.status, x.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def settle(ok, what):
    """口は返事を送った後に予約を外す（finally）ので、返事を受けた直後はまだ外れていない事がある。少し待って見る
    （試験の揺れ・11-08 の別の目の 8 回のうち 1 回目と、新しい木 4 つを同時に回した 1 つで、受け取りで断った後の予約の 0 の確かめが落ちた）"""
    for _ in range(100):
        if ok():
            return
        time.sleep(0.05)
    raise AssertionError(what)


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
# 遅い送り（会場の遅い Wi-Fi で本文を送っている途中）が 2 本あっても、3 本目の小さな写真は待たずに通る。写し直しの枠は本文を読み終えてから
# 取るので、受け取りの間は持たない（別の目の気づき 11-08。前の形では 3 本目が枠を待ち、待つ長さを越えて 503 になった）
import socket  # noqa: E402

server.media_gate = load_guard.Gate(slots=2, wait_max=4, wait_s=3.0)
cookie = "; ".join(f"{c.name}={c.value}" for c in jar)
slow = []
for ip in ("203.0.113.21", "203.0.113.22"):
    so = socket.create_connection(("127.0.0.1", server.server_address[1]), timeout=10)
    so.sendall((f"POST /record/{rid}/media HTTP/1.1\r\nHost: 127.0.0.1:{server.server_address[1]}\r\nOrigin: {base}\r\nCookie: {cookie}\r\nContent-Type: image/png\r\n"
                f"Cf-Connecting-Ip: {ip}\r\nContent-Length: {1024 * 1024}\r\n\r\n").encode() + b"x" * 1000)
    slow.append(so)
time.sleep(0.5)  # 2 本とも本文の途中で止まっている
assert server.media_reserve.reserved == 2 * 1024 * 1024, ("遅い送りが 2 本とも照らしを通って受け取りの途中にいる", server.media_reserve.reserved)
t0 = time.time()
code, _ = call(f"/record/{rid}/media", b"x", "image/png", ip="203.0.113.23")
took = time.time() - t0
assert code == 422 and took < 2.0, ("遅い送りが 2 本ある時に、3 本目の小さな写真が待たされた", code, round(took, 1))
for so in slow:
    so.close()
time.sleep(0.5)
server.media_gate = real_gate
# 合言葉付きの場の合計の止め（予約中の分も数える）。上限の手前まで予約を埋めて、今回の分で越える形
assert not getattr(server, "public_open", False)
used = techo_site.media_bytes()
# 予約の台帳は記録の置き場の中の共有のファイル（同じ置き場を使う別のプロセスと数え合う。安全の事項 2 への対応）
from omochae import records  # noqa: E402

assert server.media_reserve.path == records.folder() / ".reserve" / "media.json"
settle(lambda: server.media_reserve.reserved == 0, "前の上げの予約が外れる")
tag = load_guard.Reserve(server.media_reserve.path).take(used, techo_site.MEDIA_TOTAL - used - 1, techo_site.MEDIA_TOTAL)
assert tag, "別の入れ物（別のプロセスの形）で予約を埋める"
code, body = call(f"/record/{rid}/media", b"xx", "image/png")
assert code == 507 and body == b"", ("別のプロセスの予約も数えて、上限を越える分を断る", code, body)
server.media_reserve.give(tag)
assert server.media_reserve.reserved == 0, "断った分と書き終えた分の予約は外れる"
assert call(f"/record/{rid}/media", b"x", "image/png")[0] == 422
# 受け取り中の本文の合計（このプロセスのメモリ）の上限。合計が越えた時だけ、変換の入口が溢れた時と同じ 503・本文は空。空けば前のまま
assert load_guard.RECV_TOTAL == 8 * techo_site.MAX_MEDIA and isinstance(server.recv_reserve, load_guard.Reserve) and server.recv_reserve.path is None
held = server.recv_reserve.take(0, load_guard.RECV_TOTAL - 1, load_guard.RECV_TOTAL)
code, body = call(f"/record/{rid}/media", b"xx", "image/png")
assert code == 503 and body == b"", ("受け取り中の合計が上限を越える分を断る", code, body)
settle(lambda: server.media_reserve.reserved == 0, "受け取りで断った分の、置き場の予約も外れる")
server.recv_reserve.give(held)
assert call(f"/record/{rid}/media", b"x", "image/png")[0] == 422
settle(lambda: server.recv_reserve.reserved == 0 and server.media_reserve.reserved == 0, "書き終えた分の受け取りの予約も外れる")

# 4. 同時に処理する要求の数
assert load_guard.HTTP_MAX == server.http_max == 64
# 前の要求の処理（返事の後の閉じ）がまだ枠を持っている事があるので、枠を取る時は少し待つ（試験の揺れ・11-08 の Green の 1 回目で当たった）
for _ in range(server.http_max):
    assert server._slots.acquire(timeout=5)
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
print("ok 全体の資源の上限: 変換の入口（同時 2・待ち 4・待つ長さ）・合計の予約（合言葉付きの場にも・プロセスをまたいで共有の台帳）・受け取り中の本文の合計・同時の処理の数・声の待ち行列の長さ。ふつうの量では前のまま")
