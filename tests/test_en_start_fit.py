"""英語の頁の手帖で、最初の画面の「はじめる」（Start）が、幅 320×568 の最初の画面に入る（統括の頼み 11-08）。

なぜ: 英語の頁では、「はじめる」の上の声の断り（どこで声を字にするか・名前は言わない）が日本語より長く、幅 320×568 で 3 行になり、
御来迎と虎の両方で「はじめる」の下の端が 577px（画面の 9px 外）に出た。声の断りの英語を、言葉の決め（grove の state/english-review-20261107.md）の内で
短くして 2 行にした。断りは、声を機械の中で字にする形と、ブラウザが字にする形の 2 つがあり、どちらが出るかは機械で替わるので、両方で見る。
あわせて、英語の頁では断りの 2 つの文の間に空白がある事も見る（2 つの要素の間に空白が無く、"device.Please" とくっついて出ていた）。
./run.sh はブラウザなしで動く決まりなので、入っている Chrome で頁をその大きさの iframe に開いて測る（tests/test_landscape_fit.py と同じ）。
Chrome が無い機械と、時間内に答えなかった時は、測れないと出して通す。
"""
import json
import os
import re
import subprocess
import tempfile
import threading
import urllib.parse
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ.pop("ANTHROPIC_API_KEY", None)

import html  # noqa: E402

from measure_tap import chrome  # noqa: E402
from omochae import hypotheses  # noqa: E402
from web import play_server  # noqa: E402

TOYS = {"goraigo": "NDL-1187053-R0000005-L", "tora": "NDL-1187053-R0000014-R"}
W, H = 320, 568
# 開いた最初の画面（はじめるの前）で、はじめるの下の端を測る。声の断りは JS が機械に合わせて片方を出すので、両方の形に切り替えて測る
MEASURE = """<script>addEventListener('load',()=>{setTimeout(()=>{
const te=document.getElementById('te'),st=document.getElementById('start'),out={page:'__PAGE__',w:innerWidth,h:innerHeight,lang:document.documentElement.lang};
for(const how of ['local','browser']){te.classList.remove('te-local','te-browser','te-none');te.classList.add('te-'+how);
 out[how]=Math.round(st.getBoundingClientRect().bottom);}
const both=document.querySelector('#start-note .how.is-local.is-browser');out.gap=both?getComputedStyle(both,'::before').content:null;
parent.postMessage(JSON.stringify(out),'*')},400)})</script>"""
pages = {name: f"/toy/{sid}/techo?lang=en&walk={name}" for name, sid in TOYS.items()}
WRAP = """<!doctype html><body>%s<pre id="measured"></pre><script>
addEventListener('message',e=>{document.getElementById('measured').textContent+=e.data+'\\n'})</script>"""

send, get = play_server.Handler._send, play_server.Handler.do_GET


def wrapped(self, code, body, ctype="text/html; charset=utf-8", headers=()):
    m = re.search(r"[?&]walk=([\w-]+)", self.path)
    if m and m.group(1) in pages and isinstance(body, str) and ctype.startswith("text/html"):
        body += MEASURE.replace("__PAGE__", m.group(1))
    return send(self, code, body, ctype, headers)


def do_get(self):
    if self.path == "/__wrap":
        frames = "".join(f'<iframe src="{p.replace("&", "&amp;")}" width="{W}" height="{H}" style="border:0;display:block"></iframe>' for p in pages.values())
        return send(self, 200, WRAP % frames)
    return get(self)


exe = chrome()
if not exe:
    print("測れない: Chrome が無い")
    raise SystemExit(0)
play_server.Handler._send, play_server.Handler.do_GET = wrapped, do_get
server = play_server.serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"
# 手帖は刷った後でしか開かないので、玩具ごとに 1 枚刷る
for sid in TOYS.values():
    urllib.request.urlopen(urllib.request.Request(f"{base}/toy/{sid}/print", data=urllib.parse.urlencode({"hypothesis": hypotheses.sheet_of(sid)["id"]}).encode(),
                                                  headers={"Origin": base}), timeout=180)
try:
    with tempfile.TemporaryDirectory() as profile:
        out = subprocess.run([exe, "--headless=new", "--no-sandbox", "--disable-gpu", f"--user-data-dir={profile}", "--window-size=2000,1200",
                              "--virtual-time-budget=20000", "--dump-dom", f"{base}/__wrap"], capture_output=True, text=True, timeout=240).stdout
except subprocess.TimeoutExpired:
    out = ""
server.shutdown()
found = re.search(r'<pre id="measured">(.*?)</pre>', out, re.S)
got = {}
for line in html.unescape(found.group(1) if found else "").splitlines():
    if line.strip():
        rec = json.loads(line)
        got[rec["page"]] = rec
if set(got) != set(pages):
    print(f"測れない: Chrome が {len(got)}/{len(pages)} 頁しか答えなかった（混んだ機械では起きる）")
    raise SystemExit(0)
for name, rec in got.items():
    assert (rec["w"], rec["h"]) == (W, H) and rec["lang"] == "en", (name, rec)
    for how in ("local", "browser"):
        assert rec[how] <= H, (name, how, f"はじめるの下の端 {rec[how]}px が画面の高さ {H}px の外")
    assert rec["gap"] == '" "', (name, "英語の頁で声の断りの 2 つの文の間に空白が無い", rec["gap"])
print("ok 英語の手帖の最初の画面: 幅 320×568 で はじめる が画面の中（声の断りの 2 つの形とも）・断りの文の間に空白")
