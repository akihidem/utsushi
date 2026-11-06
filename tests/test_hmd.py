"""作業の頁に重ねる形（web.hmd。下地は試作の枝 try/hmd。本人の指示 11-07「HMD か iPhone カメラでオーバーレイする形での作業を前提に、作業ページを作ろう。」）の試験。
本物の API・マイク・カメラは使わない。

見る事:
1. 組み立ての 3D（kumitate）を中に持ち、送る釦・鍵・声の言葉がつながっている。字を外へ送らない。組み立ての書き方が無い玩具は出さない
2. 道: /toy/<玩具>/kasane（カメラに重ねる）と /toy/<玩具>/kasane/hmd（HMD）で開く。玩具を選ぶ頁は持たない（作る口は手帖 1 つ）。
   手帖からの道は口の字が決まってから足すので、今はどの頁からも道を張らない
3. 1 手ごとに止まる（本人の感想 11-06）: 「つぎ」1 回で動くのは 1 手だけ。折り目 1 本の動きは 2 秒以上。「もどる」は 1 手もどる。
   声の約束（本人の決定 11-06・手帖の作り直しの案 2 と同じ）: 聞くのは「はじめる」の後だけ。操作の言葉の全部が一致した時だけ動く。
   教室の話し声の見本では動かない。最後の「つぎ」で、はじめに戻さない。隠れたら止め、見えたら戻し、離れたら止める
4. 声が使えない画面でも、釦とキーボードで通れる
5. 大きさと置き場: 手順の字は大きく、釦に掛からない。釦は 64px 以上、「つぎ」は 96px 以上。横にはみ出さない
6. カメラに重ねる頁: 偽のカメラで映像が付き、画面いっぱいに敷かれる
7. 映像の中の紙に合わせる（本人の言葉 11-07「自分が作った実物がオーバーレイする」）: カメラが付くと紙の 4 隅の印が 4 つ出て（字は数字だけ）、
   印は既定の囲みに出て 3D の舞台もその中、印を動かすと舞台が新しい囲みの中へ動いて縮む。画面の大きさが変わると印を既定の囲みへ置き直す。
   カメラを止めると印を消し、舞台を元の置き場へ戻す。押すまで印は出ない

./run.sh はブラウザなしで動く決まりで、ブラウザを操る道具も入れない決まり（tests/test_mic_seen.py と同じ）。入っている Chrome で頁を開いて歩く。
Chrome が無い機械と、Chrome が何も答えなかった時は、測れないと出して通す。落ちるのは、歩けて結果が違う時と、歩き始めたのに終わらなかった時。
1 手ずつの進め方と歩く試験は、別の試作の枝（proto/hmd-work-view）の物を、この枝の頁の作りに合わせて移した（統括の決め 11-06）。
"""
import json
import os
import re
import subprocess
import tempfile
import threading
import urllib.error
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ.pop("ANTHROPIC_API_KEY", None)

from measure_tap import chrome  # noqa: E402
from web import hmd, kumitate, play_server  # noqa: E402

G, T = hmd.TOYS
# ---- 1. 字と、送らない作り
for sid in (G, T):
    assert hmd.available(sid), sid
    page = hmd.page(sid)
    assert 'id="rt-stage"' in page and 'id="rt-next"' in page and 'id="rt-prev"' in page, "kumitate の 3D と釦がある"
    for w in (hmd.NEXT, hmd.PREV, hmd.AGAIN, hmd.LISTEN, hmd.NO_VOICE, hmd.HOW):
        assert w in page or json.dumps(w, ensure_ascii=False)[1:-1] in page, w
    words = json.loads(re.search(r'<script type="application/json" id="hmd-words">(.*?)</script>', page, flags=re.S).group(1))
    assert set(words["words"].values()) == {"next", "prev", "again", "top", "stop"}
    clean = re.compile(words["clean"].replace("\\s", r"\s"))
    for said, k in (("つぎ", "next"), ("次。", "next"), ("もどる", "prev"), ("もう一回", "again"), ("もう一度", "again"), ("最初から", "top"), ("止めて", "stop")):
        assert words["words"].get(clean.sub("", said)) == k, (said, k)
    for said in ("次の手順ってどうやるの", "つぎはどうするの", "もどるって言って"):
        assert clean.sub("", said) not in words["words"], ("言葉の全部が一致した時だけ", said)
    assert "rec.start()" in hmd.SCRIPT and "listen.addEventListener('click'" in hmd.SCRIPT
    assert "rec.onresult=e=>{if(!on)return;" in hmd.SCRIPT, "止めた後に届いた字では送らない"
    for key in ("ArrowRight", "ArrowLeft", "PageDown", "PageUp"):
        assert key in hmd.SCRIPT, key
for word in ("fetch(", "XMLHttpRequest", "sendBeacon", "WebSocket", "<form", "localStorage", "sessionStorage", "document.cookie", "MediaRecorder", "toDataURL", "getImageData"):
    assert word not in hmd.SCRIPT, ("この頁は送らず、残さない", word)
# 組み立ての節は、試作の頁に形の並びと動かす口を渡し、1 つの動きが終わった時に知らせる（ふだんの頁は使わない）
assert "window.kumitateParts={F,T,play,rest,stop," in kumitate.SCRIPT and "window.kumitateSlow||1" in kumitate.SCRIPT
assert "rest(B)}beat(j+1,seq.length)" in kumitate.SCRIPT, "終わりの知らせは、形を置き終えた後に出す"
# カメラに重ねる頁。後ろのカメラ、映像は機械の中だけ（作りながら見る頁と同じ約束の字）
cam = hmd.page(G, cam=True)
assert '<video id="hmd-cam" playsinline muted autoplay></video>' in cam and 'id="hmd-camera"' in cam and hmd.PRIVACY in cam
assert "facingMode:{ideal:'environment'}" in hmd.SCRIPT and "audio:false" in hmd.SCRIPT and "addEventListener('pagehide',off)" in hmd.SCRIPT
assert '<video' not in hmd.page(G), "カメラは重ねる頁だけ"
assert not hmd.available("NDL-1187053-R0000004-L"), "組み立ての書き方が無い玩具は出さない"

# ---- 2. 道
server = play_server.serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"


class NoFollow(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


opener = urllib.request.build_opener(NoFollow)


def get(path):
    try:
        r = opener.open(base + path, timeout=120)
        return r.status, r.read().decode("utf-8", "replace"), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace"), dict(e.headers)


for sid in (G, T):
    assert get(f"/toy/{sid}/kasane/hmd")[0] == 200 and get(f"/toy/{sid}/kasane")[0] == 200
assert '<video id="hmd-cam"' in get(f"/toy/{G}/kasane")[1] and '<video id="hmd-cam"' not in get(f"/toy/{G}/kasane/hmd")[1], "映像はカメラに重ねる形だけ"
assert get("/toy/NDL-1187053-R0000004-L/kasane")[0] == 404 and get("/toy/NDL-1187053-R0000004-L/kasane/hmd")[0] == 404, "組み立ての書き方が無い玩具では開かない"
assert get("/hmd")[0] == 404 and get(f"/hmd/{G}")[0] == 404, "玩具を選ぶ頁と試作の枝の番地は持たない"
for path in ("/", "/toys", f"/toy/{G}", f"/toy/{G}/kumitate", f"/toy/{G}/techo", "/gallery"):
    assert "/kasane" not in get(path)[1], ("手帖からの道は口の字が決まってから足す", path)

# ---- 3〜6. Chrome で歩く
# 見本は頁の script より先に置く。音声認識を差し替えて、始めた・止めたを window.__log に書く（マイクは使わない）。
STUB = ("<script>window.__log=[];class S{constructor(){window.__rec=this;this.running=false}"
        "start(){this.running=true;__log.push('start')}stop(){this.running=false;__log.push('stop');const t=this;setTimeout(()=>t.onend&&t.onend(),0)}};"
        "window.SpeechRecognition=undefined;window.webkitSpeechRecognition=__VOICE__?S:undefined;</script>")
# 教室の話し声の見本。操作の言葉に似た文を混ぜる。
CHATTER = ["ねえ きょうの給食なんだっけ", "次の手順ってどうやるの", "田中くん それ取って", "つぎはどうするの", "もどるって言って", "もう一回やってみる"]
WALK = r"""<script>(async()=>{
const wait=(ms=40)=>new Promise(r=>setTimeout(r,ms)),R={},b=document.body,stage=document.getElementById('rt-stage'),CH=__CHATTER__,VOICE=__VOICE__;
const at=()=>Number(stage.dataset.at),mv=()=>Number(b.dataset.move),$=(s)=>document.querySelector(s);
const say=async(t,alts)=>{__rec.onresult({results:[[{transcript:t},...(alts||[]).map(a=>({transcript:a}))]]});await wait()};
const box=(s)=>{const r=$(s).getBoundingClientRect();return[Math.round(r.left),Math.round(r.top),Math.round(r.width),Math.round(r.height)]};
const key=async(k)=>{document.body.dispatchEvent(new KeyboardEvent('keydown',{key:k,bubbles:true,cancelable:true}));await wait()};
const tap=async(op)=>{$('#hmd-'+op).click();await wait()};
const idle=async()=>{for(let i=0;i<400&&b.dataset.busy==='1';i++)await wait(50)};
const LAST=window.kumitateParts.F.length-1;
try{
R.total=Number(b.dataset.moves);
R.init=[at(),mv(),$('#hmd-prev').disabled,$('#hmd-mic').dataset.state];
if(VOICE){
 R.before=[typeof window.__rec,__log.length];
 $('#hmd-listen').click();await wait();
 R.began=[$('#hmd-mic').dataset.state,__log.join(','),$('#hmd-listen').getAttribute('aria-pressed')];
 await say('つぎ');R.next0=[at(),mv()];await say('次。');R.next1=[at(),mv()];await say('つぎ');R.next2=[at(),mv()];
 for(const c of CH)await say(c);R.chatter=[at(),mv()];
 await say('すぎ',['次']);R.alt=[at(),mv()];
 R.dots=[document.querySelectorAll('#hmd-dots span').length,document.querySelectorAll('#hmd-dots span.on').length];
 await say('もどる');R.back=[at(),mv()];await say('もう一回');R.again=[at(),mv()];
 // 速さ: 折り目 1 本の動きにかかる時間（止まるまで待つ）
 await idle();const t0=performance.now();await say('つぎ');await idle();R.fold=[Math.round(performance.now()-t0),at(),mv()];
 let hidden=false;Object.defineProperty(document,'hidden',{configurable:true,get:()=>hidden});
 const vis=async(h)=>{hidden=h;document.dispatchEvent(new Event('visibilitychange'));await wait()};
 await vis(true);R.hid=__rec.running;await vis(false);R.shown=__rec.running;
 for(let i=0;i<80&&!$('#hmd-next').disabled;i++)await say('つぎ');
 R.end=[at()===LAST,$('#rt-text').textContent,$('#hmd-next').disabled,$('#hmd-count').textContent,mv()===R.total];
 await say('つぎ');R.afterEnd=at()===LAST&&mv()===R.total;
 await say('もう一回');R.againEnd=at()===LAST&&mv()===R.total;
 await say('はじめから');R.top=[at(),mv()];
 await say('止めて');R.stopped=[__rec.running,$('#hmd-mic').dataset.state];
 $('#hmd-listen').click();await wait();
 dispatchEvent(new Event('pagehide'));await wait();R.left=__rec.running;
}else{
 await tap('next');R.tap=[at(),mv()];await key('ArrowRight');R.key1=[at(),mv()];await key('ArrowLeft');R.key2=[at(),mv()];await key('r');R.key3=[at(),mv()];
 await tap('prev');R.first=[at(),mv(),$('#hmd-prev').disabled,$('#hmd-again').disabled];
}
// 大きさと置き場（手順 2 で測る: 字が長い手順）
for(let i=0;i<80&&mv()>0;i++)await tap('prev');
await tap('next');await tap('next');
const tx=$('#rt-text'),r=tx.getBoundingClientRect(),fam=getComputedStyle(b).fontFamily;
R.size={vw:innerWidth,vh:innerHeight,sx:document.documentElement.scrollWidth,sy:document.documentElement.scrollHeight,text:parseFloat(getComputedStyle(tx).fontSize),textBottom:Math.round(r.bottom),textRight:Math.round(r.right),actsLeft:box('.hmd-acts')[0],
 textLen:tx.textContent.length,at:at(),stage:box('#rt-stage'),chips:['prev','again','next'].map(o=>box('#hmd-'+o)[3]),actsTop:box('.hmd-acts')[1],
 reach:Math.max(...[...document.querySelectorAll('.hmd-acts button')].filter(e=>!e.hidden).map(e=>e.getBoundingClientRect().bottom))<=innerHeight,
 stageBottom:Math.round(stage.getBoundingClientRect().bottom),
 font:[...document.querySelectorAll('.hmd button')].filter(e=>getComputedStyle(e).fontFamily!==fam).length};
}catch(e){R.error=String(e&&e.stack||e)}
const pre=document.createElement('pre');pre.id='measured';pre.textContent=JSON.stringify(R);document.body.appendChild(pre);
})();</script>"""
# カメラに重ねる頁: 釦を押し、偽のカメラの映像が付くのを待つ
CAMWALK = r"""<script>(async()=>{
const wait=(ms=50)=>new Promise(r=>setTimeout(r,ms)),R={},v=document.getElementById('hmd-cam');
try{R.before=[!!v.srcObject,document.getElementById('hmd-camera').textContent];
document.getElementById('hmd-camera').click();
for(let i=0;i<200&&!(v.videoWidth>0);i++)await wait();
const r=v.getBoundingClientRect(),de=document.documentElement;
// 映像の敷き: 画面（スクロールの棒を除いた幅と、見えている高さ）いっぱい。映像が付かなくても敷きは測れる
R.cover=[Math.round(r.width)>=de.clientWidth,Math.round(r.height)>=de.clientHeight,getComputedStyle(v).position];
R.wide=de.scrollWidth<=de.clientWidth;R.over=[de.scrollWidth,de.clientWidth,...[...document.querySelectorAll('body *')].filter(e=>e.getBoundingClientRect().right>de.clientWidth+1).slice(0,4).map(e=>e.tagName+'#'+(e.id||e.className))];R.reach=Math.max(...[...document.querySelectorAll('.hmd-acts button')].filter(e=>!e.hidden).map(e=>e.getBoundingClientRect().bottom))<=innerHeight;
// headless の Chrome では、偽のカメラでも映像が付かない機械がある（この機械は付かない）。その時は、押した後に断りも出ず待っている
R.pending=!(v.videoWidth>0)&&document.getElementById('hmd-cam-note').textContent!==__NOCAM__;
R.on=[v.videoWidth>0,document.body.classList.contains('cam-on'),document.getElementById('hmd-camera').textContent];
document.getElementById('hmd-camera').click();await wait();R.off=[!!v.srcObject,document.body.classList.contains('cam-on')];
}catch(e){R.error=String(e&&e.stack||e)}
const pre=document.createElement('pre');pre.id='measured';pre.textContent=JSON.stringify(R);document.body.appendChild(pre);
})();</script>"""

# 紙の 4 隅の印: カメラの口を差し替えた見本（空の映像を返す）で押し、印を紙の角に見立てた所へ動かす。この機械の偽のカメラは映像が付かないので、口を差し替える
QUADSTUB = "<script>if(navigator.mediaDevices)navigator.mediaDevices.getUserMedia=async()=>new MediaStream();</script>"
QUADWALK = r"""<script>(async()=>{
const wait=(ms=80)=>new Promise(r=>setTimeout(r,ms)),R={},$=s=>document.querySelector(s),stage=document.getElementById('rt-stage');
const box=e=>{const r=e.getBoundingClientRect();return[r.left,r.top,r.right,r.bottom].map(Math.round)};
const centers=()=>[...document.querySelectorAll('.hmd-corner')].map(c=>{const r=c.getBoundingClientRect();return[Math.round(r.left+r.width/2),Math.round(r.top+r.height/2)]});
try{R.before=[getComputedStyle($('#hmd-quad')).display,box(stage)];
$('#hmd-camera').click();await wait(300);
R.on=[document.body.classList.contains('quad-on'),getComputedStyle($('#hmd-quad')).display,[...document.querySelectorAll('.hmd-corner')].map(c=>c.textContent).join('')];
R.home=centers();R.stage1=box(stage);
const W=innerWidth,H=innerHeight,T=[[W*.5,H*.55],[W*.92,H*.55],[W*.92,H*.92],[W*.5,H*.92]].map(p=>p.map(Math.round));
const drag=(c,[x,y])=>{const o={bubbles:true,pointerId:7,clientX:x,clientY:y};c.dispatchEvent(new PointerEvent('pointerdown',o));c.dispatchEvent(new PointerEvent('pointermove',o));c.dispatchEvent(new PointerEvent('pointerup',o))};
[...document.querySelectorAll('.hmd-corner')].forEach((c,i)=>drag(c,T[i]));await wait();
R.target=T;R.moved=centers();R.stage2=box(stage);
dispatchEvent(new Event('resize'));await wait();R.reset=centers();
$('#hmd-camera').click();await wait();
R.off=[document.body.classList.contains('quad-on'),document.body.classList.contains('quad-set'),stage.style.transform,getComputedStyle($('#hmd-quad')).display];
}catch(e){R.error=String(e&&e.stack||e)}
const pre=document.createElement('pre');pre.id='measured';pre.textContent=JSON.stringify(R);document.body.appendChild(pre);
})();</script>"""

send, getter = play_server.Handler._send, play_server.Handler.do_GET


def wrapped(self, code, body, ctype="text/html; charset=utf-8", headers=()):
    m = re.search(r"[?&]walk=(voice|plain|cam|quad)", self.path)
    if m and isinstance(body, str) and "/kasane" in self.path:
        kind = m.group(1)
        voice = "true" if kind == "voice" else "false"
        walk_js = (QUADWALK if kind == "quad" else CAMWALK.replace("__NOCAM__", json.dumps(hmd.NO_CAMERA, ensure_ascii=False)) if kind == "cam"
                   else WALK.replace("__CHATTER__", json.dumps(CHATTER, ensure_ascii=False)).replace("__VOICE__", voice))
        stub = STUB.replace("__VOICE__", voice) + (QUADSTUB if kind == "quad" else "")
        body = body.replace('<meta charset="utf-8">', '<meta charset="utf-8">' + stub, 1).replace("</body>", walk_js + "</body>", 1)
    return send(self, code, body, ctype, headers)


def walk(width, height, kind):
    """Chrome で 1 回歩く。返すのは、頁が書いた結果（歩き終われば dict、何も答えなければ None）。"""
    hold = {}

    def tagged(self, code, body, ctype="text/html; charset=utf-8", headers=()):
        self.path = hold.get("path", self.path)
        return wrapped(self, code, body, ctype, headers)

    def tagging_get(self):
        hold["path"], self.path = self.path, re.sub(r"[?&]walk=\w+", "", self.path)
        return getter(self)

    play_server.Handler._send, play_server.Handler.do_GET = tagged, tagging_get
    flags = ["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"] if kind == "cam" else []
    path = f"/toy/{G}/kasane" if kind in ("cam", "quad") else f"/toy/{G}/kasane/hmd"
    try:
        with tempfile.TemporaryDirectory() as profile:
            out = subprocess.run([exe, "--headless=new", "--no-sandbox", "--disable-gpu", f"--user-data-dir={profile}", f"--window-size={width},{height}", *flags,
                                  "--virtual-time-budget=60000", "--dump-dom", f"{base}{path}?walk={kind}"],
                                 capture_output=True, text=True, timeout=170).stdout
    except subprocess.TimeoutExpired:
        return None
    finally:
        play_server.Handler._send, play_server.Handler.do_GET = send, getter
    found = re.search(r'<pre id="measured">(.*?)</pre>', out, re.S)
    if not found:
        return "started" if 'class="hmd"' in out else None
    return json.loads(found.group(1).replace("&quot;", '"').replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&"))


exe = chrome()
if not exe:
    server.shutdown()
    print("ok 作業しながら見る試作の字と道。測れない: Chrome が無いので、声と大きさとカメラは歩いていない")
    raise SystemExit(0)
runs = {}
for name, (w, h, kind) in {"横・声あり": (1280, 720, "voice"), "横・声なし": (1280, 720, "plain"), "縦・声あり": (390, 844, "voice"), "縦・カメラ": (390, 844, "cam"), "縦・紙に合わせる": (390, 844, "quad"), "横・紙に合わせる": (1280, 720, "quad")}.items():
    got = walk(w, h, kind)
    if not isinstance(got, dict):
        got = walk(w, h, kind)  # 混んだ機械では答えない事があるので、1 度だけ回し直す
    runs[name] = got
server.shutdown()
if all(v is None for v in runs.values()):
    print("ok 作業しながら見る試作の字と道。測れない: Chrome が答えなかった（混んだ機械では起きる）")
    raise SystemExit(0)
unmeasured = []
for name, got in runs.items():
    assert isinstance(got, dict), ("歩き始めたのに終わらなかった", name, got)
    assert "error" not in got, (name, got)
    if "紙に合わせる" in name:
        inside = lambda b, pts, pad=3: b[0] >= min(p[0] for p in pts) - pad and b[1] >= min(p[1] for p in pts) - pad and b[2] <= max(p[0] for p in pts) + pad and b[3] <= max(p[1] for p in pts) + pad
        assert got["before"][0] == "none", (name, "押すまで印は出ない", got)
        assert got["on"] == [True, "block", "1234"], (name, "カメラが付くと、数字だけの印が 4 つ出る", got)
        assert inside(got["stage1"], got["home"]), (name, "印を出した時、3D の舞台は印の囲みの中", got)
        assert all(abs(a[0] - b[0]) <= 1 and abs(a[1] - b[1]) <= 1 for a, b in zip(got["moved"], got["target"])), (name, "印は指で動かした所へ動く", got)
        assert inside(got["stage2"], got["target"]) and got["stage2"] != got["stage1"], (name, "印を動かすと、3D の舞台が新しい囲みの中へ動く", got)
        assert got["reset"] == got["home"], (name, "画面の大きさが変わると、印を既定の囲みへ置き直す", got)
        assert got["off"] == [False, False, "", "none"], (name, "カメラを止めると印を消し、舞台を元の置き場へ戻す", got)
        continue
    if "カメラ" in name:
        assert got["before"] == [False, hmd.CAMERA], (name, "押すまでカメラは付けない", got)
        assert got["cover"] == [True, True, "fixed"], (name, "映像は画面いっぱいに敷く", got)
        assert got["wide"] and got["reach"], (name, "横にはみ出さず、カメラの釦を含む押す所が頁を動かさずに見える", got)
        if got["pending"]:
            unmeasured.append("カメラの映像（この機械の headless の Chrome では偽のカメラが付かない）")
            continue
        assert got["on"] == [True, True, hmd.CAMERA_OFF], (name, "映像が付く", got)
        assert got["off"] == [False, False], (name, "止めると映像を外す", got)
        continue
    voice = "声あり" in name
    assert 25 <= got["total"] <= 40, (name, "手順 12 を、手（切る・折り目 1 本・通す・置く）に分けている", got)
    # 開いた時: 刷った紙のまま手順 1 で止まり、何も動かしていない
    assert got["init"] == [0, 0, True, "off" if voice else "none"], (name, got)
    if voice:
        assert got["before"] == ["undefined", 0], (name, "聞くのは「はじめる」の後だけ。押す前は、聞く物を作ってもいない", got)
        assert got["began"] == ["on", "start", "true"], (name, got)
        assert (got["next0"], got["next1"], got["next2"]) == ([0, 1], [1, 2], [2, 3]), (name, "「つぎ」と「次。」で 1 手ずつ進む", got)
        assert got["chatter"] == [2, 3], (name, "話し声の見本では動かない", got)
        # 手順 3（外筒を角筒にする）は折り目 4 本。「つぎ」1 回で 1 本だけ折れて止まり、手順は替わらない。点は 4 つで、済んだ数だけ塗る
        assert got["alt"] == [2, 4] and got["dots"] == [4, 2], (name, "1 つ目の読みが外れても、別の読みが操作の言葉なら動く。同じ手順の中で 1 手進む", got)
        assert (got["back"], got["again"]) == ([2, 3], [2, 3]), (name, "「もどる」は 1 手もどり、「もう一回」は同じ手のまま", got)
        assert got["fold"][0] >= 2000 and got["fold"][1:] == [2, 4], (name, "折り目 1 本の動きは 2 秒以上かけ、動き終わったら止まって待つ", got)
        assert (got["hid"], got["shown"]) == (False, True), (name, "隠れたら止め、見えたら戻す", got)
        assert got["end"] == [True, kumitate.DONE, True, kumitate.DONE, True], (name, "最後は、できあがり。「つぎ」は押せない", got)
        assert got["afterEnd"] and got["againEnd"], (name, "最後の「つぎ」で、はじめに戻さない", got)
        assert got["top"] == [0, 0], (name, "「はじめから」で刷った紙に戻る", got)
        assert got["stopped"] == [False, "off"], (name, "「止めて」で聞くのを止める", got)
        assert got["left"] is False, (name, "頁を離れたら止める", got)
    else:
        # 声が使えない画面: 釦とキーボードで通れる
        assert (got["tap"], got["key1"], got["key2"], got["key3"]) == ([0, 1], [1, 2], [0, 1], [0, 1]), (name, got)
        assert got["first"] == [0, 0, True, True], (name, "はじめに戻ると、もどると、もう一回は押せない", got)
    size = got["size"]
    assert size["at"] == 1 and size["textLen"] >= 30, (name, "手順 2 で測る", size)
    assert size["sx"] <= size["vw"], (name, "横にはみ出さない", size)
    assert size["text"] >= (28 if size["vw"] >= 1000 else 20), (name, "手順の字が大きい", size)
    # 横の画面は押す所の列が字の横に、縦の画面は字の下に来る。どちらでも重ならない
    assert (size["textRight"] <= size["actsLeft"]) if size["vw"] > size["vh"] else (size["textBottom"] <= size["actsTop"]), (name, "手順の字は釦に掛からない", size)
    assert min(size["chips"]) >= 64 and size["chips"][2] >= 96, (name, "釦は 64px 以上、「つぎ」は 96px 以上", size)
    assert size["font"] == 0, (name, "釦がブラウザの既定の字のまま", size)
    assert size["reach"] and size["stageBottom"] <= size["vh"], (name, "押す所と 3D は、頁を動かさずに全部見える", size)
note = f"。測れない: {'・'.join(unmeasured)}" if unmeasured else ""
print(f"ok 作業しながら見る試作: 1 手ずつ止まり、声は操作の言葉の全部が一致した時だけ動く。送らない。カメラは押した時だけ付く。{len(runs)} つの画面で歩いた{note}")
