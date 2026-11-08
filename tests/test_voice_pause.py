"""「声を録る」の止まる所を、頭なしの Chrome で 1 つずつ歩いて確かめる（本人の答え 11-08「(A) 声を録る釦を置いて残す。」・音声認識を外す設計の 2 版の止め 2）。

前は、聞く口の声（ブラウザの音声認識）が、頁が隠れたら止まり、見えたら戻り、頁を離れたら止まるかを歩いていた（#87 の点検で見つけた事）。
11-08 に音声認識を外した（本人「クロードの音声認識をはずして、ユーザーの端末の音声入力に頼るのでいいのではないか。」）ので、同じ「周りの声を
録り続けない」を、録る釦で歩く形に替えた。歩く所: 作りながら見る頁の工夫の口と、手帖の記録の頁（のこすの頁）の記録の札の足す口。
見る事:
- もう一度押すと止まり、置き場に置き終える。録っている間は釦の字が「止める」、止めると「声を録る」に戻る
- 見えなくなった時・頁を離れる時（pagehide）・手順を移る時（次の手順へ）に止まる。区切りは録り始めた手順の番号
- 60 秒で止まる。1 秒ごとにたまった大きさが受け口の上限の手前に来たら止まり、上限の内で置く
- 欄の「残す」は、録りを止めて置き終えてから字を送る
- 5 ついっぱいの時は録らず（マイクを開かない）、前からの字（web.clips.FULL）で 1 行知らせる
- 記録の札の足す口には録る釦が無く、字を残してもマイクを開かない
- 音声認識は作られない
./run.sh はブラウザなしで動く決まりで、ブラウザを操る道具も入れない決まり（tests/test_mic_seen.py と同じ）。入っている Chrome で頁を iframe に開いて歩く。
IndexedDB とマイクと録りは見本にする（tests/voice_stub.py の注。時間を進める形の頭なしの Chrome では、本物の IndexedDB が返ってこない）。
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
from omochae import hypotheses, records  # noqa: E402
from voice_stub import FAKE_IDB, inject  # noqa: E402
from web import clips, play_server  # noqa: E402

G = "NDL-1187053-R0000005-L"
GS = hypotheses.sheet_of(G)["id"]
KEY = "c" * 24  # この画面が記録を残した時の鍵（記録の札の足す口は、その画面にだけ開く）
PAGES = {"tsukuru": f"/toy/{G}/tsukuru?h={GS}&n=1", "kiroku": f"/toy/{G}/techo/kiroku"}
WALK = {
    "tsukuru": r"""<script>addEventListener('load',()=>setTimeout(async()=>{
const wait=(ms=50)=>new Promise(r=>setTimeout(r,ms)),R={},$=s=>document.querySelector(s),D=parent.__idb.data;
const b=$('[data-scene=craft] .hanasu-rec'),ts=()=>[...D.values()].filter(c=>c.kind==='t'),on=()=>b.getAttribute('aria-pressed'),label=()=>b.innerText.trim();
const until=async(f,n=400)=>{for(let i=0;i<n&&!f();i++)await wait()};
let hidden=false;Object.defineProperty(document,'hidden',{configurable:true,get:()=>hidden});
const vis=async(h)=>{hidden=h;document.dispatchEvent(new Event('visibilitychange'));await wait()};
const startRec=async()=>{b.click();await until(()=>window.__mr&&__mr.state==='recording')};
try{
R.before=[on(),label(),__log.filter(x=>x.startsWith('gum')).length];
await startRec();R.on=[on(),label(),__log.filter(x=>x.startsWith('gum')||x.startsWith('rec:start'))];
await wait(1500);b.click();await until(()=>ts().length===1);R.second=[on(),label(),ts().length,__mr.state];
D.clear();await startRec();await vis(true);await until(()=>ts().length===1);R.hidden=[on(),__mr.state,ts().length];await vis(false);
D.clear();await startRec();dispatchEvent(new Event('pagehide'));await until(()=>ts().length===1);R.pagehide=[on(),__mr.state,ts().length];
D.clear();await startRec();const n0=$('#step').value;$('#tiles [value=next]').click();await until(()=>ts().length===1);
R.next=[on(),__mr.state,ts().length,String(ts()[0].step),n0,$('#step').value];
D.clear();await startRec();await until(()=>__mr.state!=='recording',1400);await until(()=>ts().length===1);R.minute=[on(),__recMs,ts().length];
D.clear();window.__chunk=95*1024;await startRec();await until(()=>__mr.state!=='recording',1400);await until(()=>ts().length===1);
R.size=[on(),__recMs,ts().length,ts()[0].size];window.__chunk=1000;
D.clear();__log.length=0;parent.__fetches.length=0;await startRec();
$('[data-scene=craft] textarea').value='紙を二重にした';$('[data-scene=craft] .hanasu-go').click();
await until(()=>parent.__fetches.some(f=>f.url.endsWith('/talk')));const tf=parent.__fetches.find(f=>f.url.endsWith('/talk'));
R.keep=[__log.indexOf('rec:stop'),__log.indexOf('fetch:talk'),tf?tf.clips:-1,on()];
D.clear();const w=sessionStorage.getItem('utsushi-who'),sid=$('.stage').dataset.sid;
for(let i=0;i<5;i++)D.set('x'+i,{id:'x'+i,sid,kind:'t',pass:null,who:w,at:Date.now(),run:null});
__log.length=0;b.click();await wait(400);R.full=[on(),$('[data-scene=craft] .hanasu-note').textContent,__log.filter(x=>x.startsWith('gum')).length];
R.sr=window.__sr;
}catch(e){R.error=String(e&&e.stack||e)}
parent.postMessage(JSON.stringify({page:'tsukuru',R}),'*')},300))</script>""",
    "kiroku": r"""<script>addEventListener('load',()=>setTimeout(async()=>{
const wait=(ms=50)=>new Promise(r=>setTimeout(r,ms)),R={},$=s=>document.querySelector(s);
try{const keep=$('[data-scene=keep]');R.keep=[!!keep,keep?keep.querySelectorAll('.hanasu-rec').length:-1,!!$('#nk .hanasu-rec')];
if(keep){__log.length=0;keep.querySelector('textarea').value='あとで足した工夫';keep.querySelector('.hanasu-go').click();
 for(let i=0;i<200&&!parent.__fetches.some(f=>f.url.endsWith('/talk'));i++)await wait();await wait(200);
 R.after=[__log.filter(x=>x.startsWith('gum')||x.startsWith('rec:')).length,keep.querySelector('.hanasu-note').textContent]}
R.sr=window.__sr}catch(e){R.error=String(e&&e.stack||e)}
parent.postMessage(JSON.stringify({page:'kiroku',R}),'*')},300))</script>""",
}
# 外の頁: IndexedDB の見本を置き、頁を 1 つずつ開く（2 つの頁が同じ置き場の見本を取り合わないように）
WRAP = """<!doctype html><body>%s<iframe id="f" width="390" height="844" style="border:0"></iframe><pre id="measured"></pre><script>
const order=%s,f=document.getElementById('f');let i=0;const next=()=>{if(i<order.length){parent.__fetches.length=0;f.src=order[i++]}};
addEventListener('message',e=>{document.getElementById('measured').textContent+=e.data+'\\n';next()});next();</script>"""

send, get = play_server.Handler._send, play_server.Handler.do_GET


def wrapped(self, code, body, ctype="text/html; charset=utf-8", headers=()):
    m = re.search(r"[?&]walk=(\w+)", self.path)
    if m and isinstance(body, str) and ctype.startswith("text/html"):
        body = inject(body, WALK[m.group(1)])
    return send(self, code, body, ctype, headers)


def do_get(self):
    if self.path == "/__wrap":
        order = [p + ("&" if "?" in p else "?") + f"walk={name}" for name, p in PAGES.items()]
        return send(self, 200, WRAP % (FAKE_IDB, json.dumps(order)))
    return get(self)


exe = chrome()
if not exe:
    print("測れない: Chrome が無い（止まる所の字の並びは tests/test_clips_client.py と tests/test_hanasu.py が見る）")
    raise SystemExit(0)
play_server.Handler._send, play_server.Handler.do_GET = wrapped, do_get
play_server.Handler._rec_key = lambda self: KEY
server = play_server.serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"
for path, data in ((f"/toy/{G}/print", {"hypothesis": GS}), (f"/toy/{G}/record", {"hypothesis": GS, "result": "動いた"})):
    urllib.request.urlopen(urllib.request.Request(base + path, data=urllib.parse.urlencode(data).encode(), headers={"Origin": base}), timeout=120).read()
records.claim(records.all_records(G)[-1]["id"], KEY)
try:
    with tempfile.TemporaryDirectory() as profile:
        out = subprocess.run([exe, "--headless=new", "--no-sandbox", "--disable-gpu", f"--user-data-dir={profile}", "--window-size=900,900",
                              "--virtual-time-budget=240000", "--dump-dom", f"{base}/__wrap"], capture_output=True, text=True, timeout=200).stdout
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
R = got["tsukuru"]
print(json.dumps(got, ensure_ascii=False))
assert "error" not in R, R
assert R["before"] == ["false", "声を録る", 0], ("押すまでマイクを開かない", R["before"])
assert R["on"] == ["true", "止める", ["gum:audio", "rec:start:1000"]], ("押すと録り始め、字が「止める」になる（1 秒ごとに受ける）", R["on"])
assert R["second"] == ["false", "声を録る", 1, "inactive"], ("もう一度押すと止まり、置き終える", R["second"])
assert R["hidden"] == ["false", "inactive", 1], ("見えなくなったら止める", R["hidden"])
assert R["pagehide"] == ["false", "inactive", 1], ("頁を離れる時は止める", R["pagehide"])
assert R["next"][:3] == ["false", "inactive", 1] and R["next"][3] == R["next"][4] != R["next"][5], ("手順を移ると止める。区切りは録り始めた手順の番号", R["next"])
assert R["minute"][0] == "false" and clips.VOICE_SECONDS * 1000 <= R["minute"][1] < clips.VOICE_SECONDS * 1000 + 1500 and R["minute"][2] == 1, ("60 秒で止まる", R["minute"])
assert R["size"][0] == "false" and R["size"][1] < clips.VOICE_SECONDS * 1000 and R["size"][2] == 1 and clips.VOICE_NEAR <= R["size"][3] <= clips.VOICE_CLIP_BYTES, \
    ("上限の手前で止まり、上限の内で置く", R["size"])
assert 0 <= R["keep"][0] < R["keep"][1] and R["keep"][2] == 1 and R["keep"][3] == "false", ("「残す」は録りを止めて置き終えてから字を送る", R["keep"])
assert R["full"] == ["false", clips.FULL, 0], ("5 ついっぱいの時は録らず、マイクも開かず、前からの字で知らせる", R["full"])
assert R["sr"] == 0, "音声認識は作られない"
K = got["kiroku"]
assert "error" not in K, K
assert K["keep"] == [True, 0, True], ("記録の札の足す口には録る釦が無い（のこすの記入の欄にはある）", K["keep"])
assert K["after"][0] == 0, ("足す口で字を残してもマイクを開かない", K["after"])
assert K["sr"] == 0, "音声認識は作られない"
print("ok 声を録る: もう一度押す・見えなくなる・頁を離れる・手順を移る・60 秒・上限の手前・残す で止まり、5 つで止まり、足す口では録らない")
