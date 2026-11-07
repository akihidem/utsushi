"""写真と動画の口は、写した動画の大きさと、同じ相手からの数に上限がある（セキュリティの点検 U1）。

なぜ: 動画を ffmpeg で写す時に書き出しの大きさの上限が無く、写すと何倍にも膨らむ小さな動画で、合言葉なしの場でも一時の置き場と
メモリを埋められた。この口はフォームを読む前に本体のまま受けるので、書き込みの数（WRITE_PATHS）も届いていなかった。
1 は ffmpeg を偽物に替えて、上限の引数と、上限に届いた書き出しを断る事を見る（膨らむ動画そのものは作らない）。2 は本物の口で数を見る。
"""
import http.cookiejar
import json
import os
import pathlib
import tempfile
import threading
import types
import urllib.error
import urllib.parse
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(os.environ["OMOCHAE_DATA"], "api-usage.jsonl")

from omochae import hypotheses  # noqa: E402
from web import play_server, techo_site  # noqa: E402

# 1. 写す時の上限（偽の ffmpeg が、言われた大きさのファイルを書く）
data = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 1000
seen = []


def fake_run(write):
    def run(args, **kw):
        seen.append(args)
        pathlib.Path(args[-1]).write_bytes(b"\x00" * write)
        return types.SimpleNamespace(returncode=0, stdout=b"", stderr=b"")
    return run


real_run, real_which = techo_site.subprocess.run, techo_site.shutil.which
techo_site.shutil.which = lambda name: "/usr/bin/" + name
# 先に振る舞い: 写すと元より 8MB も膨らむ書き出しは受けない（上限の前の形では、そのまま受けてメモリに読んだ）
techo_site.subprocess.run = fake_run(len(data) + 8 * 1024 * 1024)
assert techo_site.clean_video(data, "mp4") == (None, techo_site.MISMATCH), "写すと大きく膨らむ動画は断る"
limit = len(data) + techo_site.VIDEO_ROOM
techo_site.subprocess.run = fake_run(len(data) - 100)
clean, why = techo_site.clean_video(data, "mp4")
assert clean is not None and why == "", why
args = seen[-1]
assert args[args.index("-protocol_whitelist") + 1] == "file" and args.index("-protocol_whitelist") < args.index("-i"), args
assert args[args.index("-fs") + 1] == str(limit) and args.index("-fs") > args.index("-i"), args
techo_site.subprocess.run = fake_run(limit)
assert techo_site.clean_video(data, "mp4") == (None, techo_site.MISMATCH), "写すと上限に届く動画は断る"
techo_site.subprocess.run, techo_site.shutil.which = real_run, real_which

# 2. 同じ相手からの数（MEDIA_LIMIT）。中身は読めない物を送り、断り（422）と数の断り（429）を見分ける
server = play_server.serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))


def call(path, body, ctype, ip="203.0.113.7"):
    r = urllib.request.Request(base + path, data=body, headers={"Origin": base, "Content-Type": ctype, "Cf-Connecting-Ip": ip})
    try:
        with op.open(r) as x:
            return x.status, x.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


G = "NDL-1187053-R0000005-L"
H = hypotheses.sheet_of(G)["id"]
form = lambda d: urllib.parse.urlencode(d).encode()
assert call(f"/toy/{G}/print", form({"hypothesis": H}), "application/x-www-form-urlencoded")[0] == 200
code, body = call(f"/toy/{G}/record-json", form({"hypothesis": H, "result": "動いた"}), "application/x-www-form-urlencoded")
rid = json.loads(body)["id"]
for n in range(play_server.MEDIA_LIMIT):
    code, _ = call(f"/record/{rid}/media", b"x", "image/png")
    assert code == 422, (n, code)
code, _ = call(f"/record/{rid}/media", b"x", "image/png")
assert code == 429, code
assert call(f"/record/{rid}/media", b"x", "image/png", ip="203.0.113.8")[0] == 422, "別の相手は数えない"
server.shutdown()
print("ok: 写真と動画の口は、写した動画の大きさと、同じ相手からの数に上限がある")
