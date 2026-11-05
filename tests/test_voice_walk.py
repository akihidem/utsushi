"""声の操作の約束を、音声認識の見本で 1 つずつ歩いて確かめる（#87）。字を見る試験だけでは、約束を破る書き換えが通ってしまったため。

約束: 操作の字は送らない。言葉の全部が一致した時だけ操作にする。ほかは質問。結果の画面の話し声は質問にしない。読み上げの前に聞くのを止める。
マイクを押すと止まる。頁を離れたら止める。隠れたら止め、見えたら聞いていた時だけ戻す。

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
os.environ.pop("OMOCHAE_VOICE", None)
os.environ.pop("ANTHROPIC_API_KEY", None)

from measure_tap import chrome  # noqa: E402
from web import play_server  # noqa: E402

G = "NDL-1187053-R0000005-L"
PAGES = {"techo": f"/toy/{G}/techo?n=1", "tsukuru": f"/toy/{G}/tsukuru?h=H-A&n=2", "kiroku": f"/toy/{G}/techo/kiroku?x=1"}
# ブラウザの既定の字（Arial など）のままの入力の部品を集める（#87 の要件。頁の字を継いでいれば空）。
FONTS = "[...document.querySelectorAll('button,input:not([type=hidden]):not([type=file]):not([type=checkbox]):not([type=radio]),textarea,select')].filter(e=>getComputedStyle(e).fontFamily!==getComputedStyle(document.body).fontFamily).map(e=>e.tagName+(e.id?'#'+e.id:''))"
# 見本は頁の script より先に置く。音声認識・読み上げ・送信を差し替えて、起きた順を window.__log に書く（本物のサーバに記録を残さない）。
STUB = r"""<script>
window.__log=[];window.__posts=[];
class S{constructor(){window.__rec=this;this.running=false}
 start(){this.running=true;__log.push('start')}
 stop(){this.running=false;__log.push('stop');const t=this;setTimeout(()=>t.onend&&t.onend(),0)}};
window.SpeechRecognition=undefined;window.webkitSpeechRecognition=S;
window.__fetch=window.fetch;
window.fetch=(url,o)=>{const q=new URLSearchParams(o&&o.body&&o.body.toString?o.body.toString():''),st=Number(q.get('step')||1),ev=q.get('event');window.__posts.push({url:String(url).split('/').pop(),question:q.get('question'),event:ev,sheet_version:q.get('sheet_version')});
 return Promise.resolve(new Response(JSON.stringify({ok:true,step:ev==='next'?st+1:ev==='back'?Math.max(st-1,1):st,text:'こたえ'}),{status:200,headers:{'Content-Type':'application/json'}}))};
const sp=window.speechSynthesis;if(sp){sp.speak=(u)=>{__log.push('speak:'+(window.__rec&&window.__rec.running?'running':'stopped'));setTimeout(()=>u.onend&&u.onend(),1)};sp.cancel=()=>{}}
</script>"""
# 頁の終わりに足す。順に話して、起きた事を親へ送る。
WALK = {
    "techo": r"""<script>(async()=>{
const wait=(ms=30)=>new Promise(r=>setTimeout(r,ms)),te=document.getElementById('te'),mic=document.getElementById('mic'),R={};
const hear=async(t)=>{__rec.onresult({results:[[{transcript:t}]]});await wait()};
const asks=()=>__posts.filter(p=>p.url==='ask-json').map(p=>p.question);
const n=()=>+new URLSearchParams(location.search).get('n');
let hidden=false;Object.defineProperty(document,'hidden',{configurable:true,get:()=>hidden});
const vis=async(h)=>{hidden=h;document.dispatchEvent(new Event('visibilitychange'));await wait()};
document.getElementById('start').click();await wait();
R.started=[__log.filter(x=>x==='start').length>0,mic.getAttribute('aria-pressed'),te.dataset.scene];
await hear('つぎ');await hear('次。');R.next=[n(),te.dataset.scene];
await hear('もどる');R.back=n();
await hear('次の手順ってどうやるの');R.partial=[n(),te.dataset.scene,asks().slice()];
await wait(60);R.speakAsk=__log.filter(x=>x.startsWith('speak')).slice();
await hear('もどる');R.closed=te.dataset.scene;
__log.length=0;await hear('もう一回');await wait(60);R.again=__log.filter(x=>x.startsWith('speak'));
__log.length=0;await vis(true);R.hidden=[__log.slice(),mic.getAttribute('aria-pressed'),__rec.running];
__log.length=0;await vis(false);R.shown=[__log.slice(),mic.getAttribute('aria-pressed'),__rec.running];
__log.length=0;mic.click();await wait();R.micoff=[__log.slice(),mic.getAttribute('aria-pressed'),__rec.running];
__log.length=0;await vis(true);await vis(false);R.offstays=[__log.slice(),mic.getAttribute('aria-pressed')];
mic.click();await wait(60);R.micon=[mic.getAttribute('aria-pressed'),__rec.running];
for(let i=0;i<20&&te.dataset.scene!=='end';i++){await hear('できた')}
R.end=[te.dataset.scene,__posts.filter(p=>p.event==='done').length];
const before=asks().length;await hear('紙を二重に貼った');R.kufu=[document.getElementById('kufu').value,document.getElementById('fold').open,asks().length-before];
await hear('のこす');R.kekka=te.dataset.scene;
await hear('ねえ きょうの給食なんだっけ');R.chatter=[te.dataset.scene,asks().length-before];
await hear('もどる');R.fromkekka=te.dataset.scene;
R.ops=asks().filter(q=>/^(つぎ|次。|もどる|もう一回|できた|のこす)$/.test(q));
R.versions=[...new Set(__posts.map(p=>p.sheet_version))];
__log.length=0;window.dispatchEvent(new Event('pagehide'));await wait();R.left=[__log.slice(),__rec.running];
R.fonts=__FONTS__;
parent.postMessage(JSON.stringify({page:'techo',R}),'*');
})()</script>""",
    "kiroku": r"""<script>(()=>{parent.postMessage(JSON.stringify({page:'kiroku',R:{fonts:__FONTS__,controls:document.querySelectorAll('select,textarea,input[type=text]').length}}),'*')})()</script>""",
    "tsukuru": r"""<script>(async()=>{
const wait=(ms=30)=>new Promise(r=>setTimeout(r,ms)),mic=document.getElementById('mic'),R={};
const hear=async(t)=>{__rec.onresult({results:[[{transcript:t}]]});await wait(60)};
const asks=()=>__posts.filter(p=>p.url==='ask-json').map(p=>p.question);
const n=()=>document.getElementById('n').textContent;
let hidden=false;Object.defineProperty(document,'hidden',{configurable:true,get:()=>hidden});
const vis=async(h)=>{hidden=h;document.dispatchEvent(new Event('visibilitychange'));await wait()};
mic.click();await wait();R.started=[__log.filter(x=>x==='start').length>0,mic.getAttribute('aria-pressed')];
await hear('つぎ');R.next=n();
await hear('もどる');R.back=n();
await hear('次の手順ってどうやるの');R.partial=[n(),asks().slice()];
await wait(60);R.speak=__log.filter(x=>x.startsWith('speak')).slice();
__log.length=0;await hear('もう一回');await wait(60);R.again=__log.filter(x=>x.startsWith('speak'));
const before=asks().length;await hear('とって');await hear('のこす');R.noop=[asks().length-before,n()];
__log.length=0;await vis(true);R.hidden=[__log.slice(),mic.getAttribute('aria-pressed'),__rec.running];
__log.length=0;await vis(false);R.shown=[__log.slice(),mic.getAttribute('aria-pressed'),__rec.running];
__log.length=0;mic.click();await wait();R.micoff=[__log.slice(),mic.getAttribute('aria-pressed'),__rec.running];
mic.click();await wait();
R.ops=asks().filter(q=>/^(つぎ|もどる|もう一回|とって|のこす)$/.test(q));
__log.length=0;window.dispatchEvent(new Event('pagehide'));await wait();R.left=[__log.slice(),__rec.running];
parent.postMessage(JSON.stringify({page:'tsukuru',R}),'*');
})()</script>""",
}
WRAP = """<!doctype html><body>%s<pre id="measured"></pre><script>
addEventListener('message',e=>{document.getElementById('measured').textContent+=e.data+'\\n'})</script>"""

send, get = play_server.Handler._send, play_server.Handler.do_GET


def wrapped(self, code, body, ctype="text/html; charset=utf-8", headers=()):
    m = re.search(r"[?&]walk=(\w+)", self.path)
    if m and isinstance(body, str) and ctype.startswith("text/html"):
        body = re.sub(r"<html[^>]*>", lambda h: h.group(0) + STUB, body, count=1) + WALK[m.group(1)].replace("__FONTS__", FONTS)
    return send(self, code, body, ctype, headers)


def do_get(self):
    if self.path == "/__wrap":
        frames = "".join(f'<iframe src="{path.replace("&", "&amp;")}&amp;walk={name}" width="390" height="844" style="border:0"></iframe>' for name, path in PAGES.items())
        return send(self, 200, WRAP % frames)
    return get(self)


exe = chrome()
if not exe:
    print("測れない: Chrome が無い（声の約束の字は tests/test_techo_step.py と tests/test_tsukuru.py が見る）")
    raise SystemExit(0)
play_server.Handler._send, play_server.Handler.do_GET = wrapped, do_get
server = play_server.serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"


def post(path, data):
    r = urllib.request.Request(base + path, data=urllib.parse.urlencode(data).encode(), headers={"Origin": base})
    with urllib.request.urlopen(r, timeout=120) as x:
        return x.read().decode()


post(f"/toy/{G}/print", {"hypothesis": "H-A"})
# 記録の頁に、説明の後の欄（選ぶ欄と字の欄）まで出しておく
rid = json.loads(post(f"/toy/{G}/record-json", {"hypothesis": "H-A", "result": "動いた", "sheet_version": "1"}))["id"]
post(f"/record/{rid}/explain", {"text": "開いた", "next_idea": "速く押す", "by": "本人", "back": "techo"})
post(f"/toy/{G}/record-json", {"hypothesis": "H-A", "result": "わからない", "sheet_version": "1"})


def walk():
    try:
        with tempfile.TemporaryDirectory() as profile:
            out = subprocess.run([exe, "--headless=new", "--no-sandbox", "--disable-gpu", f"--user-data-dir={profile}", "--window-size=1300,900",
                                  "--virtual-time-budget=20000", "--dump-dom", f"{base}/__wrap"], capture_output=True, text=True, timeout=150).stdout
    except subprocess.TimeoutExpired:
        out = ""
    found = re.search(r'<pre id="measured">(.*?)</pre>', out, re.S)
    got = {}
    for line in (found.group(1).replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">") if found else "").splitlines():
        if line.strip():
            rec = json.loads(line)
            got[rec["page"]] = rec["R"]
    return got


got = walk()
if got and set(got) != set(PAGES):
    got = walk()  # 一部の頁だけ答えた時は、1 度だけ回し直す（混んだ機械のため）
server.shutdown()
# 1 つも答えない時だけ「測れない」にする。一部だけ答えない時は落とす: 頁の JS が壊れて答えなくなった時を、混んだ機械と取り違えないため。
if not got:
    print("測れない: Chrome が答えなかった（混んだ機械では起きる）")
    raise SystemExit(0)
assert set(got) == set(PAGES), ("答えない頁がある（頁の JS が壊れた時もこうなる）", sorted(set(PAGES) - set(got)))

QUESTION = "次の手順ってどうやるの"
R = got["techo"]
# はじめるの後は聞き続ける。全部が一致した時だけ操作になる
assert R["started"] == [True, "true", "step"], R["started"]
assert R["next"] == [3, "step"] and R["back"] == 2, (R["next"], R["back"])
# ほかの言葉は質問。手順は進まない。質問の字だけが送られる
assert R["partial"] == [2, "henji", [QUESTION]], R["partial"]
# 読み上げの前に聞くのを止める（端末が自分の声を聞いて問いにしないように）
assert R["speakAsk"] == ["speak:stopped"], R["speakAsk"]
assert R["closed"] == "step" and R["again"] == ["speak:stopped"], (R["closed"], R["again"])
# 隠れたら止め、見えたら戻す。押して止めた時は、見えても戻さない
assert R["hidden"] == [["stop"], "false", False], R["hidden"]
assert R["shown"] == [["start"], "true", True], R["shown"]
assert R["micoff"] == [["stop"], "false", False], R["micoff"]
assert R["offstays"] == [[], "false"], R["offstays"]
assert R["micon"] == ["true", True], R["micon"]
# 最後の手順の「できた」は組み上がりの知らせ。最後の画面の話し声は工夫の欄に入り、畳みが開く。質問にしない
assert R["end"] == ["end", 1], R["end"]
assert R["kufu"] == ["紙を二重に貼った", True, 0], R["kufu"]
# 結果の画面の話し声は捨てる（質問にしない・送らない）。「もどる」で最後の画面へ
assert R["kekka"] == "kekka" and R["chatter"] == ["kekka", 0] and R["fromkekka"] == "end", (R["kekka"], R["chatter"], R["fromkekka"])
# 操作の字は 1 つも送っていない。出来事は開いた時の版のまま
assert R["ops"] == [], R["ops"]
assert R["versions"] == ["1"], R["versions"]
# 頁を離れたら止める
assert "stop" in R["left"][0] and R["left"][1] is False, R["left"]
# 入力の部品は頁の字を継ぐ（ブラウザの既定の字にしない）。手帖と、手帖の記録の頁
assert R["fonts"] == [], ("既定の字のままの部品", R["fonts"])
assert got["kiroku"]["fonts"] == [] and got["kiroku"]["controls"] >= 3, got["kiroku"]

R = got["tsukuru"]
assert R["started"] == [True, "true"], R["started"]
assert R["next"] == "3" and R["back"] == "2", (R["next"], R["back"])
assert R["partial"] == ["2", [QUESTION]], R["partial"]
assert R["speak"] == ["speak:stopped"] and R["again"] == ["speak:stopped"], (R["speak"], R["again"])
# この頁に無い操作（とって・のこす）は何もしない。質問にも送らない
assert R["noop"] == [0, "2"], R["noop"]
assert R["hidden"] == [["stop"], "false", False] and R["shown"] == [["start"], "true", True], (R["hidden"], R["shown"])
assert R["micoff"][1:] == ["false", False] and "stop" in R["micoff"][0], R["micoff"]
assert R["ops"] == [], R["ops"]
assert "stop" in R["left"][0] and R["left"][1] is False, R["left"]
print("ok 声の約束: 手帖と作りながら見る頁で、操作の字を送らず、止めるべき時に止める")
