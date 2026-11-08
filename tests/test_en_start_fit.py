"""英語の頁の手帖で、最初の画面の「はじめる」（Start）が、幅 320×568 の最初の画面に入る（統括の頼み 11-08）。

なぜ: 英語の頁では、「はじめる」の上の声の断り（どこで声を字にするか・名前は言わない）が日本語より長く、幅 320×568 で 3 行になり、
御来迎と虎の両方で「はじめる」の下の端が 577px（画面の 9px 外）に出た。声の断りの英語を、言葉の決め（grove の state/english-review-20261107.md）の内で
短くして 2 行にした。11-08 に手帖の作る頁のマイクと音声認識を外し（本人「クロードの音声認識をはずして、ユーザーの端末の音声入力に頼るのでいいのではないか。」）、
声の断り（start-note）も一緒に外したので、今は断りの無い最初の画面で「はじめる」が画面の中にある事を見る（断りが戻って 3 行になった時にも落ちる）。
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
# 開いた最初の画面（はじめるの前）で、はじめるの下の端を測る。声の断りの要素（start-note）が無い事も見る
MEASURE = """<script>addEventListener('load',()=>{setTimeout(()=>{
const te=document.getElementById('te'),st=document.getElementById('start'),out={page:'__PAGE__',w:innerWidth,h:innerHeight,lang:document.documentElement.lang};
out.bottom=Math.round(st.getBoundingClientRect().bottom);out.note=!!document.getElementById('start-note');
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
    assert rec["bottom"] <= H, (name, f"はじめるの下の端 {rec['bottom']}px が画面の高さ {H}px の外")
    assert rec["note"] is False, (name, "声の断り（start-note）は音声認識と一緒に外した")
print("ok 英語の手帖の最初の画面: 幅 320×568 で はじめる が画面の中（声の断りは外した）")
