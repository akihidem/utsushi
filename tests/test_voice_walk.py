"""声の約束を、音声認識の見本で 1 つずつ歩いて確かめる（#87。本人の決定 11-06・案 2）。字を見る試験だけでは、約束を破る書き換えが通ってしまったため。

約束: 聞き続けるのは操作の言葉だけ。言葉の全部が一致した時だけ操作にし、操作の字は送らない。問いは「こまった」を押した（言った）後の 1 つだけ受ける。
工夫は、最後の画面でマイクを押した後に話した事だけを欄に入れる。教室の話し声の見本を流しても、問いにも工夫にも記録にもならず、答えの口にも渡らない。
読み上げの前に聞くのを止める。マイクを押すと止まる。頁を離れたら止める。隠れたら止め、見えたら聞いていた時だけ戻す。入力の部品は頁の字を継ぐ。

./run.sh はブラウザなしで動く決まりで、ブラウザを操る道具も入れない決まり（tests/test_mic_seen.py と同じ）。入っている Chrome で頁を iframe に開いて歩く。
Chrome が無い機械と、1 つも答えなかった時は、測れないと出して通す。落ちるのは、歩けて、結果が違う時と、一部の頁だけ答えない時。マイクは使わない。
"""
import http.cookiejar
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
# chatter は、送信を差し替えずに本物の受け口へ送る頁（話し声だけを流して、何も残らない事をサーバの側で見る）。
PAGES = {"techo": f"/toy/{G}/techo?n=1", "tsukuru": f"/toy/{G}/tsukuru?h=H-A&n=2", "kiroku": f"/toy/{G}/techo/kiroku?x=1", "chatter": f"/toy/{G}/techo?n=1&real=1"}
# 教室の話し声の見本。操作の言葉に似た文・名乗りの形・連絡先の形を混ぜる。
CHATTER = ["ねえ きょうの給食なんだっけ", "田中くん それ取って", "3年2組の田中です", "次の手順ってどうやるの", "電話は090-1234-5678"]
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
if(!/[?&]real=1/.test(location.search))window.fetch=(url,o)=>{const q=new URLSearchParams(o&&o.body&&o.body.toString?o.body.toString():''),st=Number(q.get('step')||1),ev=q.get('event');window.__posts.push({url:String(url).split('/').pop(),question:q.get('question'),event:ev,sheet_version:q.get('sheet_version')});
 return Promise.resolve(new Response(JSON.stringify({ok:true,step:ev==='next'?st+1:ev==='back'?Math.max(st-1,1):st,text:'こたえ'}),{status:200,headers:{'Content-Type':'application/json'}}))};
const sp=window.speechSynthesis;if(sp){sp.speak=(u)=>{__log.push('speak:'+(window.__rec&&window.__rec.running?'running':'stopped'));setTimeout(()=>u.onend&&u.onend(),1)};sp.cancel=()=>{}}
</script>"""
# 頁の終わりに足す。順に話して、起きた事を親へ送る。
WALK = {
    "techo": r"""<script>(async()=>{
const wait=(ms=30)=>new Promise(r=>setTimeout(r,ms)),te=document.getElementById('te'),mic=document.getElementById('mic'),R={},CH=__CHATTER__;
const hear=async(t)=>{__rec.onresult({results:[[{transcript:t}]]});await wait()};
const asks=()=>__posts.filter(p=>p.url==='ask-json').map(p=>p.question);
const n=()=>+new URLSearchParams(location.search).get('n'),q=document.getElementById('q'),kufu=document.getElementById('kufu'),fold=document.getElementById('fold');
let hidden=false;Object.defineProperty(document,'hidden',{configurable:true,get:()=>hidden});
const vis=async(h)=>{hidden=h;document.dispatchEvent(new Event('visibilitychange'));await wait()};
document.getElementById('start').click();await wait();
R.started=[__log.filter(x=>x==='start').length>0,mic.getAttribute('aria-pressed'),te.dataset.scene];
await hear('つぎ');await hear('次。');R.next=[n(),te.dataset.scene];
await hear('もどる');R.back=n();
for(const c of CH)await hear(c);R.chatterStep=[n(),te.dataset.scene,asks().length,q.value];
await hear('こまった');R.stuck=te.dataset.scene;
await hear('次の手順ってどうやるの');R.asked=[n(),te.dataset.scene,asks().slice()];
await wait(60);R.speakAsk=__log.filter(x=>x.startsWith('speak')).slice();
await hear(CH[0]);await hear(CH[1]);R.afterOne=asks().length;
await hear('こまった');await hear('谷折りって？');await wait(60);R.again2=asks().slice();
await hear('もどる');R.closed=te.dataset.scene;
await hear(CH[0]);R.closedChatter=[asks().length,te.dataset.scene];
__log.length=0;await hear('もう一回');await wait(60);R.again=__log.filter(x=>x.startsWith('speak'));
__log.length=0;await vis(true);R.hidden=[__log.slice(),mic.getAttribute('aria-pressed'),__rec.running];
__log.length=0;await vis(false);R.shown=[__log.slice(),mic.getAttribute('aria-pressed'),__rec.running];
__log.length=0;mic.click();await wait();R.micoff=[__log.slice(),mic.getAttribute('aria-pressed'),__rec.running];
__log.length=0;await vis(true);await vis(false);R.offstays=[__log.slice(),mic.getAttribute('aria-pressed')];
mic.click();await wait(60);R.micon=[mic.getAttribute('aria-pressed'),__rec.running];
for(let i=0;i<20&&te.dataset.scene!=='end';i++){await hear('できた')}
R.end=[te.dataset.scene,__posts.filter(p=>p.event==='done').length];
for(const c of CH)await hear(c);await hear('紙を二重に貼った');R.kufuBefore=[kufu.value,fold.open,mic.getAttribute('aria-pressed'),asks().length];
mic.click();await wait();R.talkOn=mic.getAttribute('aria-pressed');
await hear('紙を二重に貼った');R.kufu=[kufu.value,fold.open];
mic.click();await wait();R.talkOff=mic.getAttribute('aria-pressed');
await hear(CH[1]);R.kufuAfter=kufu.value;
// 写真を選んだ後は、約束の印が無いと先へ進まない（押した時に見る。選んだ知らせの有無に頼らない）
const dt=new DataTransfer();dt.items.add(new File([new Uint8Array([255,216,255,217])],'a.jpg',{type:'image/jpeg'}));
const picker=document.getElementById('files');picker.files=dt.files;picker.dispatchEvent(new Event('change'));await wait();
await hear('のこす');R.noPromise=[te.dataset.scene,document.querySelector('.check').classList.contains('call'),picker.files.length];
document.getElementById('ok').checked=true;
await hear('のこす');R.kekka=te.dataset.scene;
await hear(CH[0]);R.chatter=[te.dataset.scene,asks().length];
await hear('もどる');R.fromkekka=[te.dataset.scene,mic.getAttribute('aria-pressed')];
R.ops=asks().filter(q=>/^(つぎ|次。|もどる|もう一回|できた|のこす|こまった)$/.test(q));
R.talkPosts=__posts.filter(p=>p.url==='talk'||p.url==='record-json').length;
R.versions=[...new Set(__posts.map(p=>p.sheet_version))];
__log.length=0;window.dispatchEvent(new Event('pagehide'));await wait();R.left=[__log.slice(),__rec.running];
R.fonts=__FONTS__;
parent.postMessage(JSON.stringify({page:'techo',R}),'*');
})()</script>""",
    "chatter": r"""<script>(async()=>{
const wait=(ms=40)=>new Promise(r=>setTimeout(r,ms)),te=document.getElementById('te'),CH=__CHATTER__;
const hear=async(t)=>{__rec.onresult({results:[[{transcript:t}]]});await wait()};
document.getElementById('start').click();await wait();
for(const c of CH)await hear(c);
await hear('つぎ');for(const c of CH)await hear(c);
for(let i=0;i<20&&te.dataset.scene!=='end';i++){await hear('できた')}
for(const c of CH)await hear(c);
await hear('のこす');for(const c of CH)await hear(c);
await wait(300);
parent.postMessage(JSON.stringify({page:'chatter',R:{scene:te.dataset.scene,kufu:document.getElementById('kufu').value,q:document.getElementById('q').value}}),'*');
})()</script>""",
    "kiroku": r"""<script>(()=>{parent.postMessage(JSON.stringify({page:'kiroku',R:{fonts:__FONTS__,controls:document.querySelectorAll('select,textarea,input[type=text]').length}}),'*')})()</script>""",
    "tsukuru": r"""<script>(async()=>{
const wait=(ms=30)=>new Promise(r=>setTimeout(r,ms)),mic=document.getElementById('mic'),R={},CH=__CHATTER__;
const hear=async(t)=>{__rec.onresult({results:[[{transcript:t}]]});await wait(60)};
const asks=()=>__posts.filter(p=>p.url==='ask-json').map(p=>p.question);
const n=()=>document.getElementById('n').textContent;
let hidden=false;Object.defineProperty(document,'hidden',{configurable:true,get:()=>hidden});
const vis=async(h)=>{hidden=h;document.dispatchEvent(new Event('visibilitychange'));await wait()};
mic.click();await wait();R.started=[__log.filter(x=>x==='start').length>0,mic.getAttribute('aria-pressed')];
await hear('次の手順ってどうやるの');R.first=[n(),asks().slice()];
await wait(60);R.speak=__log.filter(x=>x.startsWith('speak')).slice();
for(const c of CH)await hear(c);R.afterOne=asks().length;
await hear('つぎ');R.next=n();
await hear('もどる');R.back=n();
await hear(CH[0]);R.afterMove=asks().length;
await hear('こまった');await wait(120);await hear('谷折りって？');await wait(60);R.second=asks().slice();
await hear(CH[0]);R.afterTwo=asks().length;
__log.length=0;await hear('もう一回');await wait(60);R.again=__log.filter(x=>x.startsWith('speak'));
const before=asks().length;await hear('とって');await hear('のこす');R.noop=[asks().length-before,n()];
__log.length=0;await vis(true);R.hidden=[__log.slice(),mic.getAttribute('aria-pressed'),__rec.running];
__log.length=0;await vis(false);R.shown=[__log.slice(),mic.getAttribute('aria-pressed'),__rec.running];
await hear(CH[0]);R.afterShown=asks().length;
__log.length=0;mic.click();await wait();R.micoff=[__log.slice(),mic.getAttribute('aria-pressed'),__rec.running];
mic.click();await wait();
R.ops=asks().filter(q=>/^(つぎ|もどる|もう一回|とって|のこす|こまった)$/.test(q));
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
        body = re.sub(r"<html[^>]*>", lambda h: h.group(0) + STUB, body, count=1) + WALK[m.group(1)].replace("__FONTS__", FONTS).replace("__CHATTER__", json.dumps(CHATTER, ensure_ascii=False))
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


# 記録の鍵（main の #441）: 説明を送れるのは、その記録を残した画面だけ。同じ Cookie を持つ 1 つの画面として送る
screen = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))


def post(path, data):
    r = urllib.request.Request(base + path, data=urllib.parse.urlencode(data).encode(), headers={"Origin": base})
    with screen.open(r, timeout=120) as x:
        return x.read().decode()


# 答えの口へ渡った問いを集める（本物の API は呼ばない）。話し声だけの頁からは、1 つも渡らないはず。
from api import ask  # noqa: E402
from omochae import making_log, records, talk_log  # noqa: E402

asked = []
ask.answer = lambda sid, hid, question: (asked.append(question), ("こたえ", "claude"))[1]
post(f"/toy/{G}/print", {"hypothesis": "H-A"})
# 記録の頁に、説明の後の欄（選ぶ欄と字の欄）まで出しておく
rid = json.loads(post(f"/toy/{G}/record-json", {"hypothesis": "H-A", "result": "動いた", "sheet_version": "1"}))["id"]
post(f"/record/{rid}/explain", {"text": "開いた", "next_idea": "速く押す", "by": "本人", "back": "techo"})
post(f"/toy/{G}/record-json", {"hypothesis": "H-A", "result": "わからない", "sheet_version": "1"})


def walk():
    try:
        with tempfile.TemporaryDirectory() as profile:
            out = subprocess.run([exe, "--headless=new", "--no-sandbox", "--disable-gpu", f"--user-data-dir={profile}", "--window-size=1700,900",
                                  "--virtual-time-budget=40000", "--dump-dom", f"{base}/__wrap"], capture_output=True, text=True, timeout=150).stdout
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
# 話し声は、手順の画面では何も起こさない（問いにしない・画面を移さない・欄に入れない）
assert R["chatterStep"] == [2, "step", 0, ""], R["chatterStep"]
# 「こまった」の後の 1 つだけが問いになる。受けたら閉じる。もう一度「こまった」と言えば、また 1 つ受ける
assert R["stuck"] == "henji" and R["asked"] == [2, "henji", [QUESTION]], (R["stuck"], R["asked"])
assert R["afterOne"] == 1, R["afterOne"]
assert R["again2"] == [QUESTION, "谷折りって？"], R["again2"]
assert R["closed"] == "step" and R["closedChatter"] == [2, "step"], (R["closed"], R["closedChatter"])
# 読み上げの前に聞くのを止める（端末が自分の声を聞いて問いにしないように）
assert R["speakAsk"] == ["speak:stopped"] and R["again"] == ["speak:stopped"], (R["speakAsk"], R["again"])
# 隠れたら止め、見えたら戻す。押して止めた時は、見えても戻さない
assert R["hidden"] == [["stop"], "false", False], R["hidden"]
assert R["shown"] == [["start"], "true", True], R["shown"]
assert R["micoff"] == [["stop"], "false", False], R["micoff"]
assert R["offstays"] == [[], "false"], R["offstays"]
assert R["micon"] == ["true", True], R["micon"]
# 最後の手順の「できた」は組み上がりの知らせ
assert R["end"] == ["end", 1], R["end"]
# 最後の画面: マイクを押す前に聞こえた事は、欄に入れない。押した後に話した事だけが入り、畳みが開く。もう一度押すと閉じる
assert R["kufuBefore"] == ["", False, "false", 2], R["kufuBefore"]
assert R["talkOn"] == "true" and R["kufu"] == ["紙を二重に貼った", True], (R["talkOn"], R["kufu"])
assert R["talkOff"] == "false" and R["kufuAfter"] == "紙を二重に貼った", (R["talkOff"], R["kufuAfter"])
# 写真を選んだ後は、約束の印が無いと「のこす」で先へ進まない。選んだ写真は頁の中に持ち、選ぶ欄は空に戻す（戻った時にブラウザが欄を戻しても、印なしでは上がらない）
assert R["noPromise"] == ["end", True, 0], R["noPromise"]
# 結果の画面の話し声は捨てる。「もどる」で最後の画面へ戻ると、話す切り替えは閉じている
assert R["kekka"] == "kekka" and R["chatter"] == ["kekka", 2] and R["fromkekka"] == ["end", "false"], (R["kekka"], R["chatter"], R["fromkekka"])
# 操作の字は 1 つも送っていない。残す前は、工夫も記録も送っていない。出来事は開いた時の版のまま
assert R["ops"] == [] and R["talkPosts"] == 0, (R["ops"], R["talkPosts"])
assert R["versions"] == ["1"], R["versions"]
# 頁を離れたら止める
assert "stop" in R["left"][0] and R["left"][1] is False, R["left"]
# 入力の部品は頁の字を継ぐ（ブラウザの既定の字にしない）。手帖と、手帖の記録の頁
assert R["fonts"] == [], ("既定の字のままの部品", R["fonts"])
assert got["kiroku"]["fonts"] == [] and got["kiroku"]["controls"] >= 3, got["kiroku"]

# 教室の話し声だけを本物の受け口へ流した頁: 問いにも工夫にも記録にもならず、答えの口にも渡らない（本人の決定 11-06・案 2）
assert got["chatter"] == {"scene": "kekka", "kufu": "", "q": ""}, got["chatter"]
assert asked == [], ("話し声が答えの口へ渡った", asked)
assert making_log.asks(G) == [], making_log.asks(G)
assert talk_log.talks(G) == [], talk_log.talks(G)
assert len(records.all_records(G)) == 2, "話し声では記録が増えない（2 件は、この試験が先に置いた物）"
assert any(e["event"] == "done" for e in making_log.steps(G)), "操作の言葉は効いている（最後まで進んだ）"

R = got["tsukuru"]
assert R["started"] == [True, "true"], R["started"]
# 「声で聞く」を押した後の 1 つだけが問いになる。その後の話し声は問いにしない。「こまった」と言えば、また 1 つ受ける
assert R["first"] == ["2", [QUESTION]], R["first"]
assert R["afterOne"] == 1, R["afterOne"]
assert R["next"] == "3" and R["back"] == "2" and R["afterMove"] == 1, (R["next"], R["back"], R["afterMove"])
assert R["second"] == [QUESTION, "谷折りって？"] and R["afterTwo"] == 2, (R["second"], R["afterTwo"])
assert R["speak"] == ["speak:stopped"] and R["again"] == ["speak:stopped"], (R["speak"], R["again"])
# この頁に無い操作（とって・のこす）は何もしない。問いにも送らない
assert R["noop"] == [0, "2"], R["noop"]
# 隠れたら止め、見えたら戻す。戻っても、問いを受ける口は開かない
assert R["hidden"] == [["stop"], "false", False] and R["shown"] == [["start"], "true", True], (R["hidden"], R["shown"])
assert R["afterShown"] == 2, R["afterShown"]
assert R["micoff"][1:] == ["false", False] and "stop" in R["micoff"][0], R["micoff"]
assert R["ops"] == [], R["ops"]
assert "stop" in R["left"][0] and R["left"][1] is False, R["left"]
print("ok 声の約束: 聞き続けるのは操作の言葉だけ。話し声は、問いにも工夫にも記録にもならない")
