"""紙を刷る口に数の上限がある（セキュリティの点検 U17）。

なぜ: 刷る口（刷る・刷り直す・英語の頁から刷る）は 1 回ごとに描画と PDF の別の処理が走る重い口なのに、前は数の上限が無く、
合言葉なしの場で玩具を変えながら送り続けると CPU が詰まった。相手ごとの数（PRINT_LIMIT）と、全体で同時に刷る数（PRINT_SLOTS）を見る。
相手はトンネルが付ける見出しの番地で見分ける（writer。手元から来た時だけ見出しを信じる）。
"""
import os
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(os.environ["OMOCHAE_DATA"], "api-usage.jsonl")

from omochae import hypotheses, loop  # noqa: E402
from web import play_server  # noqa: E402

server = play_server.serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"


def post(path, data, ip):
    r = urllib.request.Request(base + path, data=urllib.parse.urlencode(data).encode(), headers={"Origin": base, "Cf-Connecting-Ip": ip})
    try:
        with urllib.request.urlopen(r) as x:
            return x.status, dict(x.headers)
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers)


sids = [s for s in sorted(play_server.sources()) if hypotheses.load(s).get("hypotheses")][:3]
assert len(sids) == 3, sids
G = sids[0]
H = hypotheses.sheet_of(G)["id"]

# 1. 相手ごとの数。刷る中身は差し替えて速くし、数え方だけを見る（3 つの口が同じ数を分ける）
real_print_latest = play_server.print_latest
play_server.print_latest = lambda sid, hid: 1
real_print_version, real_confirm = loop.print_version, loop.confirm_sheet
loop.print_version = lambda *a, **k: 0
loop.confirm_sheet = lambda *a, **k: None
real_adopted = loop.adopted_versions
loop.adopted_versions = lambda sid, hid: [2]
paths = [(f"/toy/{G}/print", {"hypothesis": H})] * 4 + [(f"/en/toy/{G}/print", {"hypothesis": H})] * 3 + [(f"/toy/{G}/reprint", {"hypothesis": H, "version": "2"})] * 3
for path, data in paths:
    code, _ = post(path, data, "203.0.113.1")
    assert code != 429, (path, code)
code, headers = post(f"/toy/{G}/reprint", {"hypothesis": H, "version": "2"}, "203.0.113.1")
assert code == 429 and headers.get("Retry-After"), (code, headers)
code, _ = post(f"/toy/{G}/print", {"hypothesis": H}, "203.0.113.2")
assert code != 429, "別の相手は数えない"
play_server.print_latest = real_print_latest
loop.adopted_versions = real_adopted

# 2. 全体で同時に刷る数。遅い刷りを 3 つの玩具（同じ案はまとめられるので別の玩具）で同時に頼むと、空きを待てない 1 つだけが断られる
play_server.PRINT_WAIT = 0.3
loop.latest_version = lambda sid, hid: 1
loop.print_version = lambda *a, **k: (time.sleep(1.5), 0)[1]
codes = {}
threads = [threading.Thread(target=lambda s=s, n=n: codes.__setitem__(s, post(f"/toy/{s}/print", {"hypothesis": hypotheses.sheet_of(s)["id"]}, f"198.51.100.{n}")[0]))
           for n, s in enumerate(sids, 1)]
for t in threads:
    t.start()
    time.sleep(0.05)
for t in threads:
    t.join()
assert sorted(c == 429 for c in codes.values()) == [False, False, True], codes
assert all(c in (200, 303, 429) for c in codes.values()), codes
# 空きは返る: 刷り終えた後は、また刷れる
assert post(f"/toy/{G}/print", {"hypothesis": H}, "198.51.100.9")[0] in (200, 303)
loop.print_version, loop.confirm_sheet = real_print_version, real_confirm
server.shutdown()
print("ok: 紙を刷る口に、相手ごとの数と全体で同時に刷る数の上限がある")
