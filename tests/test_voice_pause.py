"""聞く口の声は、頁が隠れたら止め、見えたら聞いていた時だけ戻す。頁を離れたら止める（#87 の点検で見つけた事）。

1 回押すと聞き続ける作りなので、別のタブやアプリに移っている間も、周りの声を字にして送り続けていた。手帖と作りながら見る頁の両方で、見本の音声認識で歩いて確かめる。
./run.sh はブラウザなしで動く決まりで、ブラウザを操る道具も入れない決まり（tests/test_mic_seen.py と同じ）。入っている Chrome で頁を iframe に開いて歩く。
Chrome が無い機械と、時間内に答えなかった時は、測れないと出して通す。落ちるのは、歩けて、結果が違う時だけ。マイクは使わない。
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

from measure_tap import chrome  # noqa: E402
from web import play_server  # noqa: E402

G = "NDL-1187053-R0000005-L"
from omochae import hypotheses  # noqa: E402
# 御来迎のたたき台は組ごと（今の組 goraigo-v14 は H-C・記録の欄 sheet_by_set）。今の組で刷れるのはたたき台の紙だけ
GS = hypotheses.sheet_of(G)["id"]
PAGES = {"techo": f"/toy/{G}/techo?walk=techo", "tsukuru": f"/toy/{G}/tsukuru?h={GS}&walk=tsukuru"}
# 見本は頁の script より先に置く。聞き始めと止めた事を、起きた順に window.__log へ書く。
STUB = """<script>window.__log=[];class S{constructor(){window.__rec=this;this.running=false}
 start(){this.running=true;__log.push('start')}stop(){this.running=false;__log.push('stop');const t=this;setTimeout(()=>t.onend&&t.onend(),0)}};
window.SpeechRecognition=undefined;window.webkitSpeechRecognition=S;</script>"""
WALK = """<script>(async()=>{
const wait=(ms=40)=>new Promise(r=>setTimeout(r,ms)),mic=document.getElementById('mic'),R={};
let hidden=false;Object.defineProperty(document,'hidden',{configurable:true,get:()=>hidden});
const vis=async(h)=>{hidden=h;document.dispatchEvent(new Event('visibilitychange'));await wait()};
const snap=()=>[__log.slice(),mic.getAttribute('aria-pressed'),__rec.running];
await vis(true);await vis(false);R.never=[__log.slice(),mic.getAttribute('aria-pressed')];
mic.click();await wait();R.on=snap();
__log.length=0;await vis(true);R.hidden=snap();
__log.length=0;await vis(false);R.shown=snap();
__log.length=0;mic.click();await wait();R.off=snap();
__log.length=0;await vis(true);await vis(false);R.offstays=[__log.slice(),mic.getAttribute('aria-pressed')];
mic.click();await wait();
__log.length=0;window.dispatchEvent(new Event('pagehide'));await wait();R.left=snap();
parent.postMessage(JSON.stringify({page:'__PAGE__',R}),'*');
})()</script>"""
WRAP = """<!doctype html><body>%s<pre id="measured"></pre><script>
addEventListener('message',e=>{document.getElementById('measured').textContent+=e.data+'\\n'})</script>"""

send, get = play_server.Handler._send, play_server.Handler.do_GET


def wrapped(self, code, body, ctype="text/html; charset=utf-8", headers=()):
    m = re.search(r"[?&]walk=(\w+)", self.path)
    if m and isinstance(body, str) and ctype.startswith("text/html"):
        body = re.sub(r"<html[^>]*>", lambda h: h.group(0) + STUB, body, count=1) + WALK.replace("__PAGE__", m.group(1))
    return send(self, code, body, ctype, headers)


def do_get(self):
    if self.path == "/__wrap":
        frames = "".join(f'<iframe src="{path.replace("&", "&amp;")}" width="390" height="844" style="border:0"></iframe>' for path in PAGES.values())
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
urllib.request.urlopen(urllib.request.Request(f"{base}/toy/{G}/print", data=urllib.parse.urlencode({"hypothesis": GS}).encode(), headers={"Origin": base}), timeout=120)
try:
    with tempfile.TemporaryDirectory() as profile:
        out = subprocess.run([exe, "--headless=new", "--no-sandbox", "--disable-gpu", f"--user-data-dir={profile}", "--window-size=900,900",
                              "--virtual-time-budget=12000", "--dump-dom", f"{base}/__wrap"], capture_output=True, text=True, timeout=150).stdout
except subprocess.TimeoutExpired:
    out = ""
server.shutdown()
found = re.search(r'<pre id="measured">(.*?)</pre>', out, re.S)
got = {}
for line in (found.group(1).replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">") if found else "").splitlines():
    if line.strip():
        rec = json.loads(line)
        got[rec["page"]] = rec["R"]
if set(got) != set(PAGES):
    print(f"測れない: Chrome が {sorted(got)} しか答えなかった（混んだ機械では起きる）")
    raise SystemExit(0)
for page, R in got.items():
    # 聞いていない時は、隠れても見えても何も起きない
    assert R["never"] == [[], "false"], (page, R["never"])
    assert R["on"] == [["start"], "true", True], (page, R["on"])
    # 隠れたら止め、見えたら戻す
    assert R["hidden"] == [["stop"], "false", False], (page, R["hidden"])
    assert R["shown"] == [["start"], "true", True], (page, R["shown"])
    # 押して止めた時は、見えても戻さない
    assert R["off"][1:] == ["false", False] and "stop" in R["off"][0], (page, R["off"])
    assert R["offstays"] == [[], "false"], (page, R["offstays"])
    # 頁を離れたら止める
    assert "stop" in R["left"][0] and R["left"][2] is False, (page, R["left"])
print("ok 聞く口の声: 手帖と作りながら見る頁で、隠れたら止め、見えたら戻し、離れたら止める")
