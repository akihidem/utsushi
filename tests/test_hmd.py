"""作業の頁に重ねる形（web.hmd。下地は試作の枝 try/hmd。本人の指示 11-07「HMD か iPhone カメラでオーバーレイする形での作業を前提に、作業ページを作ろう。」）の試験。
本物の API・マイク・カメラは使わない。

見る事:
1. 組み立ての 3D（kumitate）を中に持ち、送る釦・鍵・声の言葉がつながっている。字を外へ送らない。組み立ての書き方が無い玩具は出さない
2. 道: /toy/<玩具>/kasane（カメラに重ねる）と /toy/<玩具>/kasane/hmd（HMD）で開く。玩具を選ぶ頁は持たない（作る口は手帖 1 つ）。
   道は手帖の最初の画面からの 1 つだけ（口の名は本人の決定「カメラに重ねる」）。組み立ての書き方が無い玩具の手帖には出さない
3. 1 手ごとに止まる（本人の感想 11-06）: 「つぎ」1 回で動くのは 1 手だけ。折り目 1 本の動きは 2 秒以上。「もどる」は 1 手もどる。
   声の約束（本人の決定 11-06・手帖の作り直しの案 2 と同じ）: 聞くのは「はじめる」の後だけ。操作の言葉の全部が一致した時だけ動く。
   教室の話し声の見本では動かない。最後の「つぎ」で、はじめに戻さない。隠れたら止め、見えたら戻し、離れたら止める
4. 声が使えない画面でも、釦とキーボードで通れる
5. 大きさと置き場: 手順の字は大きく、釦に掛からない。釦は 64px 以上、「つぎ」は 96px 以上。横にはみ出さない
6. カメラに重ねる頁: 偽のカメラで映像が付き、画面いっぱいに敷かれる
7. 重ねる（本人の言葉 11-08「A → B → C の順。」の A・統括の決め ①〜③）: カメラが付くと、今の手順の 3D を半透明で映像の上に重ね、
   層の順は下から 映像 → 3D → 字と押す所。1 本指で動かし、2 本指の長さの比で大きさ、角の差で向き、真ん中で位置が替わる。鍵 + ] 0 も効く。
   重ねている間は 3D の見る向き（kumitate の 1 本指の回し）は替わらない。「元に戻す」で重ね始めた所へ戻る。カメラを止めると重ねをやめる。
   HMD の道は最初から重ねる（映像は無い）。カメラが使えない機械でも 3D は見える大きさで出て、断りの字が出る。重ねている間、頁は網に何も送らない
   （前の 4 隅の印は外した）
8. 中を見る（本人の言葉 11-07「中身をそこで分解できる構造表示」・字は本人の決定「中を見る」「とじる」）: 組み立ての節が分解した形
   （window.kumitateSplit）を持つ時だけ釦が出て、押すと「とじる」に替わり、もう一度押すと戻る。開いたまま手順を送ると、先にとじる。
   分解した形の無い組では釦を出さない（分解した形は 3D の担当が kumitate に足す口。ここでは見本の形で歩く）

./run.sh はブラウザなしで動く決まりで、ブラウザを操る道具も入れない決まり（tests/test_mic_seen.py と同じ）。入っている Chrome で頁を開いて歩く。
Chrome が無い機械と、Chrome が何も答えなかった時は、測れないと出して通す。落ちるのは、歩けて結果が違う時と、歩き始めたのに終わらなかった時。
1 手ずつの進め方と歩く試験は、別の試作の枝（proto/hmd-work-view）の物を、この枝の頁の作りに合わせて移した（統括の決め 11-06）。
"""
import html
import json
import math
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
from omochae import assembly, hypotheses  # noqa: E402
from web import hmd, kumitate, naoru, play_server  # noqa: E402

# 原画の写し（out/sources・git の外）がある時は、手帖の上の帯に原画の小さな絵（#genga-thumb）が出る。写しの無い木では出ないので、
# 帯の印どうしの重なり（重ねる頁への印と原画の小さな絵）を見ない試験になり、今の main で写しのある木でだけ落ちた所を拾えなかった（11-08）。
# 写しの有り無しの両方で測る: "pic" は写しが無い木でも同じ形の絵の包みを置く形（tests/test_landscape_fit.py と同じ）、"nopic" は絵を出さない形
from web import genga  # noqa: E402

_real_pic = genga._pic
PIC = {"m": "pic"}


def _pic(sid, src, alt, lazy=False, href=None, **kw):
    if PIC["m"] == "nopic":
        return "", False
    got = _real_pic(sid, src, alt, lazy=lazy, href=href, **kw)
    return got if got[0] else (f'<span class="genga-pic" style="--genga-r:0.7000"><img src="data:," width="700" height="1000" alt="{html.escape(alt)}"></span>', True)


genga._pic = _pic

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
assert '<video id="hmd-cam" playsinline muted autoplay></video>' in cam and 'id="hmd-camera"' in cam and hmd.CAM_NOTE in cam
# カメラの区切り（本人 11-08 415・窓口の決め A2・web.clips）: 「ここで止まった」はカメラの頁だけで、カメラを出している間だけ見える。
# 録るのは置き場の camClip で、呼ぶのはその釦を押した所の 1 か所だけ（カメラを出しただけでは録らない）。録る code（MediaRecorder）は置き場の台本だけが持つ
from web import clips  # noqa: E402

assert f'<button type="button" id="hmd-stuck">{hmd.STUCK}</button>' in cam and "body:not(.cam-on) #hmd-stuck{display:none}" in hmd.STYLE
assert 'id="hmd-stuck"' not in hmd.page(G), "HMD の頁（カメラなし）には出さない"
assert hmd.SCRIPT.count("utsushiClips.camClip(") == 1
stuck = hmd.SCRIPT[hmd.SCRIPT.index("if(stuck)stuck.addEventListener('click'"):]
assert stuck.index("if(!tracks||!window.utsushiClips") < stuck.index("utsushiClips.camClip(cam.srcObject,"), "カメラを出していない時は録らない"
on_part = hmd.SCRIPT[hmd.SCRIPT.index("camBtn.addEventListener('click'"):]
assert "camClip" not in on_part.split("addEventListener('pagehide',off)")[0], "カメラを出しただけでは録らない"
assert cam.count(clips.assets()) == 1 and clips.assets() not in hmd.page(G)
assert cam.replace(clips.assets(), "").count("MediaRecorder") == 0, "録る code は置き場の台本だけ"
# 手順の画面には長い断りを置かず、カメラの断りの 1 行と、くわしい説明の頁（保護者の方へ）と のこす への道だけ（統括の決め 11-08・別の目の止め 2）
assert hmd.CAM_NOTE in cam and clips.FIRST not in cam and clips.STORE not in cam, "作業の頁の手順の画面に長い断りを置かない"
assert f'<a href="/otona">{hmd.OTONA_LINK}</a>' in cam and f'href="/toy/{G}/techo/kiroku"' in cam, "くわしい説明の頁への道と、渡す のこす の道"
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
# 道は手帖の最初の画面から 1 つだけ（作る口は手帖 1 つの決まり。口の名は本人の決定 11-07「カメラに重ねる」）。組み立ての書き方が無い玩具の手帖には出さない
assert hmd.CAM_LINK == "カメラに重ねる"
for sid in (G, T):  # 手帖は刷った紙がある時に手順の画面を出すので、先に刷る
    # 刷るのは、その玩具のたたき台（sheet_of）。御来迎の今の組 goraigo-v14 のたたき台は H-C で、必須 2 種の今の組はたたき台の紙だけを刷る
    # （H-A と決め打ちすると 422 で断られる）
    sheet = hypotheses.sheet_of(sid)["id"]
    urllib.request.urlopen(urllib.request.Request(f"{base}/toy/{sid}/print", data=f"hypothesis={sheet}".encode(), headers={"Origin": base}), timeout=120).read()
# 手帖の最初の画面の重ねる頁への道「カメラに重ねる」は、のこすへの道の 1 行「つくるところを、写真と声でのこせます。」と入れ替えた
# （本人の答え 11-08「「のこせる」の 1 行は、今の行と入れ替える。」・窓口の決め: 入れ替えるのは（イ）「カメラに重ねる」）。
# その後の本人の答え 11-08「どこかに道を戻す。」で、道を手順の画面（作りながら使う所）の上の帯の字の無い印に戻した。辿れる頁は 0 → 1（手帖）
for sid in (G, T):
    techo = get(f"/toy/{sid}/techo")[1]
    assert f'<p class="meta nokosu-route" data-on="start">{naoru.ROUTE_MAKING}</p>' in techo, sid
    assert techo.count('href="/toy/' + sid + '/kasane"') == 1 and f'<a class="kasane-go" id="kasane-go" href="/toy/{sid}/kasane" title="カメラに重ねる" data-on="step">' in techo and '<span>カメラに重ねる</span></a>' in techo, sid
assert "/kasane" not in get("/toy/NDL-1187053-R0000004-L/techo")[1], "組み立ての書き方が無い玩具の手帖には道を出さない"
for path in ("/", "/toys", f"/toy/{G}", f"/toy/{G}/kumitate", "/gallery"):
    assert "/kasane" not in get(path)[1], ("道は手帖の手順の画面からの 1 つだけ", path)

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
R.total=Number(b.dataset.moves);R.plan=(b.dataset.plan||'').split(',').filter(x=>x!=='').map(Number);
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
// 大きさと置き場（字が一番長い手順で測る。組が替わると手順の字も替わるので、段の字 F[i].t から選ぶ）
for(let i=0;i<80&&mv()>0;i++)await tap('prev');
const FF=window.kumitateParts.F,PL=(b.dataset.plan||'').split(',').map(Number);let LG=0;for(let i=0;i<FF.length-1;i++)if((FF[i].t||'').length>(FF[LG].t||'').length)LG=i;
R.longest=LG;for(let i=0,n=PL.indexOf(LG)+1;i<n;i++)await tap('next');
// 手順の字の行の数が替わると、頁は次の描画（requestAnimationFrame）で 3D の大きさを測り直す（fit）。時間を進める形の headless の Chrome では
// 次の描画の合図が来ない事があるので、測り直しを聞いている resize を送ってから測る（本物のブラウザでは描画の合図で走る。11-07 に手で確かめた）
dispatchEvent(new Event('resize'));await wait(200);
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

# 重ねる（A）: カメラの口を差し替えた見本（空の映像を返す）で押し、指（PointerEvent）と鍵で合わせる。この機械の偽のカメラは映像が付かないので、口を差し替える
QUADSTUB = "<script>if(navigator.mediaDevices)navigator.mediaDevices.getUserMedia=async()=>new MediaStream();</script>"
# カメラが使えない機械の見本（口が無い）
NOCAMSTUB = "<script>Object.defineProperty(navigator,'mediaDevices',{get:()=>undefined,configurable:true});</script>"
FITWALK = r"""<script>(async()=>{
const wait=(ms=80)=>new Promise(r=>setTimeout(r,ms)),R={},$=s=>document.querySelector(s),b=document.body,stage=document.getElementById('rt-stage');
// 頁が網に何かを送ったら数える（映像は機械の中だけ）
const net=[];const of=window.fetch;window.fetch=(...a)=>{net.push('fetch');return of(...a)};
const ox=XMLHttpRequest.prototype.open;XMLHttpRequest.prototype.open=function(...a){net.push('xhr');return ox.apply(this,a)};
if(navigator.sendBeacon){const sb=navigator.sendBeacon.bind(navigator);navigator.sendBeacon=(...a)=>{net.push('beacon');return sb(...a)}}
const OW=window.WebSocket;window.WebSocket=function(...a){net.push('ws');return new OW(...a)};
const fv=()=>(stage.dataset.fit||'').split(',').filter(x=>x!=='').map(Number);
const ev=(t,id,x,y)=>stage.dispatchEvent(new PointerEvent(t,{bubbles:true,cancelable:true,pointerId:id,clientX:x,clientY:y,isPrimary:id===1}));
const key=async k=>{document.body.dispatchEvent(new KeyboardEvent('keydown',{key:k,bubbles:true,cancelable:true}));await wait()};
const shown=e=>!!e&&getComputedStyle(e).display!=='none';
try{const cam=$('#hmd-camera'),v=$('#hmd-cam');
R.before=[b.classList.contains('fit-on'),shown($('#hmd-reset'))];
if(cam){cam.click();await wait(300)}
R.on=[b.classList.contains('fit-on'),shown($('#hmd-reset')),Number(getComputedStyle(stage).opacity),shown($('#hmd-fit-hint'))];
const r=stage.getBoundingClientRect(),cx=Math.round(r.left+r.width/2),cy=Math.round(r.top+r.height/2);
const stack=document.elementsFromPoint(cx,cy);R.layer=[stack.findIndex(e=>e===stage||stage.contains(e)),v?stack.indexOf(v):-1];
const z=e=>Number(getComputedStyle(e).zIndex)||0;R.z=[z(stage),z($('.hmd-acts')),z($('#rt-text')),z($('.hmd-top')),v?z(v):null];
R.home=fv();const ry0=stage.dataset.ry;
ev('pointerdown',1,cx,cy);ev('pointermove',1,cx+30,cy+20);ev('pointerup',1,cx+30,cy+20);await wait();R.move=fv();
ev('pointerdown',1,cx-50,cy);ev('pointerdown',2,cx+50,cy);ev('pointermove',2,cx+150,cy);await wait();R.pinch=fv();
ev('pointermove',2,Math.round(cx-50+200*Math.cos(Math.PI/6)),Math.round(cy+200*Math.sin(Math.PI/6)));await wait();R.twist=fv();
ev('pointerup',2,0,0);ev('pointerup',1,0,0);await wait();R.ry=[ry0,stage.dataset.ry];
await key('+');R.plus=fv();await key(']');R.turn=fv();await key('0');R.zero=fv();
ev('pointerdown',1,cx,cy);ev('pointermove',1,cx+40,cy);ev('pointerup',1,cx+40,cy);await wait();$('#hmd-reset').click();await wait();R.reset=fv();
// 重ねている間の押す所（カメラの頁は「元に戻す」で 7 つ）が、頁を動かさずに全部見える（横 1024×600 で 1 列だと外へ出た・別の目の測り 11-08）
R.reach=[...document.querySelectorAll('.hmd-acts button')].filter(e=>!e.hidden&&getComputedStyle(e).display!=='none').map(e=>[e.id,Math.round(e.getBoundingClientRect().bottom),Math.round(e.getBoundingClientRect().height)]);R.vh=innerHeight;
R.wide=document.documentElement.scrollWidth<=document.documentElement.clientWidth;
if(cam){cam.click();await wait();R.off=[b.classList.contains('fit-on'),stage.style.transform,!!stage.dataset.fit]}
R.net=net;
}catch(e){R.error=String(e&&e.stack||e)}
const pre=document.createElement('pre');pre.id='measured';pre.textContent=JSON.stringify(R);document.body.appendChild(pre);
})();</script>"""
NOCAMWALK = r"""<script>(async()=>{
const wait=(ms=200)=>new Promise(r=>setTimeout(r,ms)),R={},$=s=>document.querySelector(s),stage=document.getElementById('rt-stage');
try{await wait();const r=stage.getBoundingClientRect();R.stage=[Math.round(r.width),Math.round(r.height),getComputedStyle(stage).visibility,Number(getComputedStyle(stage).opacity)];
R.note=$('#hmd-cam-note').textContent;R.btn=$('#hmd-camera').hidden;R.fit=document.body.classList.contains('fit-on');
R.panels=document.querySelectorAll('#rt-stage svg').length}catch(e){R.error=String(e&&e.stack||e)}
const pre=document.createElement('pre');pre.id='measured';pre.textContent=JSON.stringify(R);document.body.appendChild(pre);
})();</script>"""

# 中を見る: 分解した形の見本（今の手の終わりの形と同じ形を返す）を、組み立ての節の口と同じ名で置く。kumitateParts が出来た後に読まれる
SPLITSTUB = "<script>window.kumitateSplit={get X(){const P=window.kumitateParts;return P&&P.F.at(-1).q.at(-1)}};</script>"
# 分解した形の無い組の見本: 組み立ての節が分解した形を置いても入らない口を先に作る（御来迎 v14・虎 v6 のように、どちらの組にも分解した形が在るため）
NOSPLITSTUB = "<script>Object.defineProperty(window,'kumitateSplit',{get:()=>undefined,set:()=>{},configurable:true});</script>"
SPLITWALK = r"""<script>(async()=>{
const wait=(ms=300)=>new Promise(r=>setTimeout(r,ms)),R={},$=s=>document.querySelector(s),b=document.body,s=$('#hmd-split');
try{R.shown=[!s.hidden,s.textContent,s.getAttribute('aria-pressed')];
if(!s.hidden){s.click();await wait();R.open=[s.textContent,s.getAttribute('aria-pressed'),b.classList.contains('split-on')];
s.click();await wait();R.closed=[s.textContent,s.getAttribute('aria-pressed'),b.classList.contains('split-on')];
s.click();await wait();$('#hmd-next').click();await wait();R.sent=[s.textContent,b.classList.contains('split-on'),Number(b.dataset.move)];
R.size=Math.round(s.getBoundingClientRect().height)}
}catch(e){R.error=String(e&&e.stack||e)}
const pre=document.createElement('pre');pre.id='measured';pre.textContent=JSON.stringify(R);document.body.appendChild(pre);
})();</script>"""

send, getter = play_server.Handler._send, play_server.Handler.do_GET


def wrapped(self, code, body, ctype="text/html; charset=utf-8", headers=()):
    m = re.search(r"[?&]walk=(voice|plain|cam|fit|hfit|nocam|split|nosplit)", self.path)
    if m and isinstance(body, str) and "/kasane" in self.path:
        kind = m.group(1)
        voice = "true" if kind == "voice" else "false"
        walk_js = (SPLITWALK if kind in ("split", "nosplit") else FITWALK if kind in ("fit", "hfit") else NOCAMWALK if kind == "nocam" else CAMWALK.replace("__NOCAM__", json.dumps(hmd.NO_CAMERA, ensure_ascii=False)) if kind == "cam"
                   else WALK.replace("__CHATTER__", json.dumps(CHATTER, ensure_ascii=False)).replace("__VOICE__", voice))
        stub = STUB.replace("__VOICE__", voice) + (QUADSTUB if kind == "fit" else "") + (NOCAMSTUB if kind == "nocam" else "") + (SPLITSTUB if kind == "split" else "") + (NOSPLITSTUB if kind == "nosplit" else "")
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
    path = f"/toy/{G}/kasane" if kind in ("cam", "fit", "nocam") else f"/toy/{G}/kasane/hmd"
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
# 手帖の最初の画面: のこすへの道の 1 行（前は重ねる頁への道）を置いても、大きいボタン「はじめる」が狭い画面の最初の画面に入る
# （別の目の確かめ 11-07: 道を上に置くと 320×568 で 22px 出た）。
# headless の Chrome は窓を 500px より狭くできないので、その大きさの iframe に開いて測る（tests/test_landscape_fit.py と同じ測り方）
FIT_SIZES, FIT_TOYS = ((320, 568), (375, 667)), (G, T, "NDL-1187053-R0000004-L")
FIT_WRAP = """<!doctype html><meta charset="utf-8"><body>__FRAMES__<pre id="measured"></pre><script>
addEventListener('load',()=>setTimeout(()=>{const out=[];for(const f of document.querySelectorAll('iframe')){const d=f.contentDocument,w=f.contentWindow;
const st=d.getElementById('start'),go=d.querySelector('.nokosu-route');const r=st.getBoundingClientRect(),g=go&&go.getBoundingClientRect();
out.push({sid:f.dataset.sid,w:w.innerWidth,h:w.innerHeight,start:Math.round(r.bottom),go:g?[Math.round(g.top),Math.round(g.bottom)]:null,sx:d.documentElement.scrollWidth});st.click();d.documentElement.style.overflowY='scroll'}
setTimeout(()=>{let i=0;for(const f of document.querySelectorAll('iframe')){const d=f.contentDocument,w=f.contentWindow,o=out[i++];
const seen=(e)=>e&&!e.hidden&&getComputedStyle(e).display!=='none'&&e.getBoundingClientRect().width>0,box=(e)=>{const b=e.getBoundingClientRect();return [Math.round(b.left),Math.round(b.top),Math.round(b.right),Math.round(b.bottom)]};
const kg=d.getElementById('kasane-go'),kl=kg&&kg.querySelector('span'),li=d.querySelector('#steps li.on'),keys=[...d.querySelectorAll('.keys a,.keys button')].filter(seen);
const others=['mic','close','genga-thumb'].map(id=>d.getElementById(id)).filter(seen);
o.step={kasane:seen(kg)?box(kg):null,label:kl&&seen(kl)?{box:box(kl),px:parseFloat(getComputedStyle(kl).fontSize),lines:Math.round(kl.getBoundingClientRect().height/parseFloat(getComputedStyle(kl).lineHeight)),cut:kl.scrollWidth>kl.clientWidth+1||kl.getBoundingClientRect().right>kg.getBoundingClientRect().right+1||kl.getBoundingClientRect().left<kg.getBoundingClientRect().left-1||kl.getBoundingClientRect().bottom>kg.getBoundingClientRect().bottom+1||kl.getBoundingClientRect().top<kg.getBoundingClientRect().top-1,iconOut:(()=>{const sv=kg.querySelector('svg');if(!sv)return true;const a=sv.getBoundingClientRect(),b=kg.getBoundingClientRect();return a.top<b.top-1||a.bottom>b.bottom+1})()}:null,bar:['mic','close','genga-thumb','kasane-go'].map(id=>d.getElementById(id)).filter(seen).map(e=>[Math.round(e.getBoundingClientRect().top),Math.round(e.getBoundingClientRect().bottom)]),text:li?box(li):null,others:others.map(box),keysBottom:Math.max(0,...keys.map(k=>Math.round(k.getBoundingClientRect().bottom)))}}
document.getElementById('measured').textContent=JSON.stringify(out)},700)},800))</script>"""


def techo_fit(lang=""):
    # lang="en" は英語の頁（訳の表の字で印の字の塊の大きさが替わる。#628 の別の目: 前の訳は 4 行に折れて印から上下に出た）。
    # 言葉の切り替えは cookie なので、日本語の頁と同じ回に混ぜず、英語だけの回にする
    q = f"&amp;lang={lang}" if lang else ""

    def do_wrap(self):
        if self.path == "/__fit":
            frames = "".join(f'<iframe data-sid="{sid}" src="/toy/{sid}/techo?v=1&amp;n=1{q}" width="{w}" height="{h}" style="border:0;display:block"></iframe>'
                             for w, h in FIT_SIZES for sid in FIT_TOYS)
            return send(self, 200, FIT_WRAP.replace("__FRAMES__", frames))
        return getter(self)

    play_server.Handler.do_GET = do_wrap
    try:
        with tempfile.TemporaryDirectory() as profile:
            out = subprocess.run([exe, "--headless=new", "--no-sandbox", "--disable-gpu", f"--user-data-dir={profile}", "--window-size=1600,1200",
                                  "--virtual-time-budget=20000", "--dump-dom", f"{base}/__fit"], capture_output=True, text=True, timeout=170).stdout
    except subprocess.TimeoutExpired:
        return None
    finally:
        play_server.Handler.do_GET = getter
    found = re.search(r'<pre id="measured">(.*?)</pre>', out, re.S)
    return json.loads(found.group(1).replace("&quot;", '"')) if found and found.group(1).strip() else None


from omochae import hypotheses  # noqa: E402

for sid in FIT_TOYS:  # 手帖は刷った紙がある時だけ「はじめる」を出すので、測る玩具は全部刷る
    urllib.request.urlopen(urllib.request.Request(f"{base}/toy/{sid}/print", data=f"hypothesis={hypotheses.sheet_of(sid)['id']}".encode(),
                                                  headers={"Origin": base}), timeout=120).read()
fits, fits_en = [], []
for mode in ("pic", "nopic"):
    PIC["m"] = mode
    got_ja = techo_fit() or techo_fit()
    got_en = techo_fit("en") or techo_fit("en")
    if got_ja is None or got_en is None:
        fits = fits_en = None
        break
    for f in got_ja + got_en:
        f["pic"] = mode
    fits += got_ja
    fits_en += got_en
PIC["m"] = "pic"
if fits is not None and fits_en is not None:
    # 英語の頁は印の字の塊（字が印の高さに収まり、写真機の形が印の外へ押し出されない・帯が 1 行）だけを同じ線で見る（統括の決め 11-08）。
    # 英語の最初の画面の「はじめる」の位置は、断りの字の長さで替わる別の事なので、ここでは数だけを出す（en_start）
    for f in fits_en:
        f["lang"] = "en"
    fits = fits + fits_en
elif fits is not None:
    fits = None  # 英語の回が答えなかった時は、測れないとして出す（日本語だけで通さない）
if fits is None:
    unmeasured_fit = "手帖の最初の画面の大きさ（Chrome が答えなかった）"
else:
    unmeasured_fit = ""
    en_start = []
    for f in fits:
        en = f.get("lang") == "en"
        if en:
            en_start.append(f"{f['sid'][-6:]} {f['w']}×{f['h']} はじめるの下の端 {f['start']}")
        else:
            assert f["start"] <= f["h"] and f["sx"] <= f["w"], ("「はじめる」が最初の画面に入り、横にはみ出さない", f)
            # のこすへの道の 1 行は、全部の玩具の最初の画面に「はじめる」の下で出て、重ならず、最初の画面から押し出さない
            assert f["go"] and f["go"][0] >= f["start"], ("のこすへの 1 行は「はじめる」の下に置き、重ならない", f)
        # 手順の画面の重ねる頁への印（本人の答え 11-08「どこかに道を戻す。」）: 組み立ての書き方がある玩具だけに出て、画面の中にあり、
        # 手順の字と上の帯の印（マイク・閉じる印・原画の小さな絵）と重ならず、押す所（もどる・つぎ・こまった）を最初の画面から押し出さない
        # 手順の画面は送りの棒を必ず出した形で測る（html の overflow-y:scroll）。頁が縦に送れる長さの時（原画の写しがある木・英語の頁）は、
        # 右寄せの印が送りの棒の幅（15px）だけ左へ寄り、幅 320 で重ねる頁への印と原画の小さな絵が重なった（今の main で落ちた・#635 の left:96px）。
        # 送りの棒の有り無しで替わる所を、写しの有り無しに左右されずに見るため
        st = f["step"]
        over = lambda a, b: not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])  # noqa: E731
        if f["sid"] == "NDL-1187053-R0000004-L":
            assert st["kasane"] is None, ("組み立ての書き方が無い玩具には印が無い", f)
        else:
            k = st["kasane"]
            assert k and k[0] >= 0 and k[2] <= f["w"] and k[3] <= f["h"], ("印が画面の中", f)
            assert not (st["text"] and over(k, st["text"])) and not any(over(k, o) for o in st["others"]), ("印が字や上の帯の印と重ならない", f)
            # 印に添えた字「カメラに重ねる」（本人の答え 11-08）は 12px 以上で、切れずに印の中に収まる（統括の決め 11-08）
            assert st["label"] and not st["label"]["cut"] and not st["label"]["iconOut"] and st["label"]["px"] >= 12, ("印の字が読める大きさで切れず、印の高さに収まる", f)
            # 帯は 1 行のまま: 上の帯の印（マイク・閉じる・原画の小さな絵・この印）の上の端がそろい、この印は帯の一番高い印（マイク 72px）より下へ出ない
            assert len({t for t, _ in st["bar"]}) == 1 and k[3] <= max(b for _, b in st["bar"]), ("帯が 2 行にならない", f)
            # マイクとの間は 8px 以上（統括の気づき 11-08: 4px は指で押し違えやすい）。マイクは帯の左の端の印
            assert k[0] - st["others"][0][2] >= 8, ("マイクと印の間が 8px 以上", f)
        if not en:
            assert st["keysBottom"] <= f["h"], ("手順の画面の押す所が最初の画面に入る", f)
    print("英語の頁の最初の画面（数だけ）:", "・".join(en_start))

runs = {}
for name, (w, h, kind) in {"横・声あり": (1280, 720, "voice"), "横・声なし": (1280, 720, "plain"), "縦・声あり": (390, 844, "voice"), "縦・カメラ": (390, 844, "cam"), "縦・重ねる": (390, 844, "fit"), "横・重ねる": (1280, 720, "fit"), "横・低い・重ねる": (1024, 600, "fit"), "横・HMD で重ねる": (1280, 720, "hfit"), "縦・カメラが使えない": (390, 844, "nocam"), "縦・中を見る": (390, 844, "split"), "横・分解の形が無い": (1280, 720, "nosplit")}.items():
    got = walk(w, h, kind)
    if not isinstance(got, dict):
        got = walk(w, h, kind)  # 混んだ機械では答えない事があるので、1 度だけ回し直す
    runs[name] = got
server.shutdown()
if all(v is None for v in runs.values()):
    print("ok 作業しながら見る試作の字と道。測れない: Chrome が答えなかった（混んだ機械では起きる）")
    raise SystemExit(0)
unmeasured = []


def fold_groups(sid):
    """手順ごとの、1 つの動きで折る折り目の順の組の数の最大（頁の手の分け方と別に、組み立ての段ごとの形から数える）。
    折る順は、段の形の折る順（o）が無ければ、根の面から遠い順（頁と同じ）。"""
    bench = assembly.assemble(sid)
    frames, trees = kumitate.frames_of(bench), kumitate.trees_of(bench)
    pose, out = frames[0]["q"][0], []
    for i, f in enumerate(frames):
        most = 0
        for j, B in enumerate(f["q"]):
            if i == 0 and j == 0:
                continue
            A, pose = pose, B
            orders = set()
            for key, b in B["s"].items():
                a = A["s"].get(key)
                if not a:
                    continue
                for r, row in trees[key]["rows"].items():
                    if abs(a["a"].get(str(r), 0) - b["a"].get(str(r), 0)) > .01:
                        o = (B.get("o") or {}).get(key, {}).get(r)
                        orders.add(o if o is not None else -row[5])
            most = max(most, len(orders))
        out.append(most)
    return out


FOLD_GROUPS = fold_groups(G)
assert max(FOLD_GROUPS) >= 2, ("折り目の組が 2 つ以上ある手順が無く、手の数の照らしが何も見ない", FOLD_GROUPS)
for name, got in runs.items():
    assert isinstance(got, dict), ("歩き始めたのに終わらなかった", name, got)
    assert "error" not in got, (name, got)
    if "中を見る" in name:
        assert got["shown"] == [True, hmd.SPLIT_OPEN, "false"], (name, "分解した形がある時だけ「中を見る」が出る", got)
        assert got["open"] == [hmd.SPLIT_CLOSE, "true", True], (name, "押すと開いて「とじる」になる", got)
        assert got["closed"] == [hmd.SPLIT_OPEN, "false", False], (name, "もう一度押すと戻る", got)
        assert got["sent"] == [hmd.SPLIT_OPEN, False, 1], (name, "開いたまま手順を送ると、先にとじて 1 手進む", got)
        assert got["size"] >= 64, (name, "釦は 64px 以上", got)
        continue
    if "分解の形が無い" in name:
        assert got["shown"][0] is False, (name, "分解した形の無い組では釦を出さない", got)
        continue
    if "重ねる" in name:
        hmd_path = "HMD" in name
        close = lambda a, b, d: all(abs(x - y) <= d for x, y in zip(a, b))
        assert got["before"] == ([True, True] if hmd_path else [False, False]), (name, "カメラに重ねる頁は押すまで重ねない・HMD の道は最初から重ねる", got)
        assert got["on"][:2] == [True, True] and got["on"][2] < 1 and got["on"][3], (name, "重ねると 3D は半透明・元に戻す と指の使い方の 1 行が出る", got)
        assert got["layer"][0] >= 0 and (hmd_path or (got["layer"][1] == -1 or got["layer"][0] < got["layer"][1])), (name, "3D の真ん中では 3D が映像より上", got)
        assert got["z"][0] < min(got["z"][1:4]) and (hmd_path or got["z"][4] < got["z"][0]), (name, "層の順は 映像 → 3D → 字と押す所", got)
        h, m, pi, tw = got["home"], got["move"], got["pinch"], got["twist"]
        assert close(m, [h[0] + 30, h[1] + 20, h[2], h[3]], 1.01), (name, "1 本指で動かすと、指の動きだけ動く", got)
        assert close(pi[:2], [m[0] + 50, m[1]], 1.01) and abs(pi[2] - m[2] * 2) <= .02 and abs(pi[3] - m[3]) <= .5, (name, "2 本指を広げると、長さの比で大きく・真ん中で位置", got)
        assert abs(tw[3] - (m[3] + 30)) <= 1 and abs(tw[2] - pi[2]) <= .03, (name, "2 本指をねじると、角の差で向き", got)
        assert got["ry"][0] == got["ry"][1], (name, "重ねている間は 3D の見る向きが替わらない", got)
        assert abs(got["plus"][2] - tw[2] * 1.1) <= .01 and abs(got["turn"][3] - (tw[3] + 5)) <= .01 and got["zero"] == h, (name, "鍵 + ] 0", got)
        assert got["reset"] == h, (name, "元に戻す で重ね始めた所へ戻る", got)
        if not hmd_path:
            assert got["off"] == [False, "", False], (name, "カメラを止めると重ねをやめる", got)
        assert got["net"] == [], (name, "重ねている間、頁は網に何も送らない", got)
        assert got["wide"] and all(bottom <= got["vh"] for _, bottom, _ in got["reach"]), (name, "重ねている間の押す所が、頁を動かさずに全部見える", got)
        assert all(h >= 64 for _, _, h in got["reach"]) and (hmd_path or "hmd-reset" in [i for i, _, _ in got["reach"]]), (name, "押す所は 64px 以上・元に戻す が出る", got)
        continue
    if "カメラが使えない" in name:
        assert got["stage"][0] > 100 and got["stage"][1] > 100 and got["stage"][2] == "visible" and got["stage"][3] == 1 and got["panels"] > 0, (name, "カメラが無くても 3D は出る", got)
        assert got["note"] == hmd.NO_CAMERA and got["btn"] is True and got["fit"] is False, (name, "断りの字が出て、カメラの釦は隠れ、重ねない", got)
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
    # 期待は頁の手の並び（data-plan: 手ごとの手順の番号）から出す。組が替わると手順と手の数が変わるため（前は組 v10 の手順 12 で決め打ちしていた）
    plan = got["plan"]
    at_after = lambda n: plan[n - 1] if n else 0
    def dots_at(n):
        i = at_after(n)
        c = plan.count(i)
        return [c, plan[:n].count(i)] if c > 1 else [0, 0]
    assert len(plan) == got["total"] and got["total"] > len(set(plan)) >= 2, (name, "手順を、手（切る・折り目 1 本・通す・置く）に分けている", got)
    assert plan == sorted(plan), (name, "手は手順の順に並ぶ", got)
    # 頁の手の並びとは別の道で、手順ごとの手の数の下限を数えて照らす（data-plan から期待を作るだけだと、頁が分け方を崩しても気づかない。
    # 確かめの指摘: 折り目が 2 本以上ある手順のうち 1 つだけを分ける誤りが通った）。折り目は順の組ごとに 1 手で、6 手まで（hmd の決まり）
    for i, n in enumerate(FOLD_GROUPS):
        if n > 1:
            want = math.ceil(n / math.ceil(n / 6))
            assert plan.count(i) >= want, (name, f"手順 {i + 1} の折り目の組 {n} を {want} 手以上に分けていない", plan.count(i), plan)
    # 開いた時: 刷った紙のまま手順 1 で止まり、何も動かしていない
    assert got["init"] == [0, 0, True, "off" if voice else "none"], (name, got)
    if voice:
        assert got["before"] == ["undefined", 0], (name, "聞くのは「はじめる」の後だけ。押す前は、聞く物を作ってもいない", got)
        assert got["began"] == ["on", "start", "true"], (name, got)
        assert (got["next0"], got["next1"], got["next2"]) == ([at_after(1), 1], [at_after(2), 2], [at_after(3), 3]), (name, "「つぎ」と「次。」で 1 手ずつ進む", got)
        assert got["chatter"] == [at_after(3), 3], (name, "話し声の見本では動かない", got)
        # 「つぎ」1 回で 1 手だけ動いて止まる。点は今の手順の手の数で、済んだ数だけ塗る（手が 1 つの手順は点を出さない）
        assert got["alt"] == [at_after(4), 4] and got["dots"] == dots_at(4), (name, "1 つ目の読みが外れても、別の読みが操作の言葉なら動く。1 手進む", got)
        assert (got["back"], got["again"]) == ([at_after(3), 3], [at_after(3), 3]), (name, "「もどる」は 1 手もどり、「もう一回」は同じ手のまま", got)
        assert got["fold"][0] >= 2000 and got["fold"][1:] == [at_after(4), 4], (name, "1 手の動きは 2 秒以上かけ、動き終わったら止まって待つ", got)
        assert (got["hid"], got["shown"]) == (False, True), (name, "隠れたら止め、見えたら戻す", got)
        assert got["end"] == [True, kumitate.DONE, True, kumitate.DONE, True], (name, "最後は、できあがり。「つぎ」は押せない", got)
        assert got["afterEnd"] and got["againEnd"], (name, "最後の「つぎ」で、はじめに戻さない", got)
        assert got["top"] == [0, 0], (name, "「はじめから」で刷った紙に戻る", got)
        assert got["stopped"] == [False, "off"], (name, "「止めて」で聞くのを止める", got)
        assert got["left"] is False, (name, "頁を離れたら止める", got)
    else:
        # 声が使えない画面: 釦とキーボードで通れる
        assert (got["tap"], got["key1"], got["key2"], got["key3"]) == ([at_after(1), 1], [at_after(2), 2], [at_after(1), 1], [at_after(1), 1]), (name, got)
        assert got["first"] == [0, 0, True, True], (name, "はじめに戻ると、もどると、もう一回は押せない", got)
    size = got["size"]
    assert size["at"] == got["longest"] and size["textLen"] >= 30, (name, "字が一番長い手順で測る", size)
    assert size["sx"] <= size["vw"], (name, "横にはみ出さない", size)
    assert size["text"] >= (28 if size["vw"] >= 1000 else 20), (name, "手順の字が大きい", size)
    # 横の画面は押す所の列が字の横に、縦の画面は字の下に来る。どちらでも重ならない
    assert (size["textRight"] <= size["actsLeft"]) if size["vw"] > size["vh"] else (size["textBottom"] <= size["actsTop"]), (name, "手順の字は釦に掛からない", size)
    assert min(size["chips"]) >= 64 and size["chips"][2] >= 96, (name, "釦は 64px 以上、「つぎ」は 96px 以上", size)
    assert size["font"] == 0, (name, "釦がブラウザの既定の字のまま", size)
    assert size["reach"] and size["stageBottom"] <= size["vh"], (name, "押す所と 3D は、頁を動かさずに全部見える", size)
if unmeasured_fit:
    unmeasured.append(unmeasured_fit)
note = f"。測れない: {'・'.join(unmeasured)}" if unmeasured else ""
print(f"ok 作業しながら見る試作: 1 手ずつ止まり、声は操作の言葉の全部が一致した時だけ動く。送らない。カメラは押した時だけ付く。{len(runs)} つの画面で歩いた{note}")
