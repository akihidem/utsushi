"""作業しながら見る頁（/toy/<印>/kasane と /toy/<印>/kasane/hmd）。聞くための経路。

始まりの決め（grove の state/standing-decisions.md）:
- 本人 11-08 539「3D 重ねずに、質問もできるだけにしよう。質問した時のその瞬間の写真を何枚か撮って、音声を文字にして認識して、クロードが考えて
  答えを音声で出すようにする。iPhone のカメラと HMD で使えるようにする。記録はここでは取らず、質問のための経路と割り切る。」
- 本人 11-07「HMD か iPhone カメラでオーバーレイする形での作業を前提に、作業ページを作ろう。」（道はこの時から）
- 本人 11-08「4 つとも推しのとおり。」: 合言葉のある場だけで使い、公開のデモは「この場では聞けません」・手帖の印の字は「カメラで聞く」・
  新しい字「聞く」「聞いています」「考えています」「こたえ」「この場では聞けません」・3D は出さない
- 本人 11-08「字の替え 11 か所も、カメラの区切りを外す事も、推しのとおり。」（設計の 3 版の表・「ここで止まった」を外す）
設計は grove の state/kasane-ask-20261108.md（1〜3 版）と、別の目の確かめ state/kasane-ask-review-20261108.md。

判断の芯:
- 頁は 3 つだけを持つ: 今の手順の字 1 行（← → で選ぶ。問いの文脈になる手順を、見る人が選べるように）・大きな「聞く」・こたえ。
  前の 3D・重ねる（指の合わせ）・中を見る・声で送る（はじめる・つぎ・もどる・もう一回）・ここで止まった は外した。戻す時は 11-08 の main
  （ad6d67f9）の hmd.py から（試験は tests/test_hmd.py の前の版）
- 「聞く」を押している間だけ声を録る（MediaRecorder・音だけ・12 秒まで）。押したまま話して離す形でも、1 回押して始め、もう 1 回で止める形でも
  使える（短く押した時は 2 回目か 12 秒で止まる）。手帖の「声を録る」（押す・もう一度押すと止める）と同じ使い方でも動き、押し方の字を足さない
- 手元の写真は、押した時と、その後 1 秒ごとに、3 枚まで（canvas に描いた JPEG・長い辺 960px）。撮るのはカメラの道で、映像の向き
  （track の getSettings().facingMode）が後ろのカメラ（environment）と分かる時だけ。前のカメラ・分からない時・HMD の道は撮らず、字の問いだけ
  （後ろのカメラが無い機械では ideal の指定が前のカメラ＝顔に落ちるため。visionOS の Safari は人の姿の写しを返しうるため）
- 送るのは押し終えた時の 1 回だけ（POST /toy/<印>/kasane/ask・play_server._kasane_ask）。声はこのサーバの中で字にし（omochae.asr_serve）、
  字と写真を Claude に渡して（api.kasane）、答えの字だけが返る。頁は声も写真も答えも端末に置かない（IndexedDB・localStorage を使わない）。
  答えは画面に出して、端末の読み上げ（speechSynthesis・ja-JP・外へ送らない）で読む。次に聞くまで画面に残し、頁を離れたら消える
- 頁を隠すか離れたら、カメラと録りを止め、録りかけの声は送らずに捨てる
- iPhone の Safari は、押した時の手当ての中で 1 度読み上げを呼ばないと、後の読み上げが鳴らない（音を出す許しの決まり）。押した時に空の読み上げを呼ぶ
- 長押しで字の選びや呼び出しの窓が出ないよう、「聞く」は user-select と -webkit-touch-callout を止め、指で画面が動かないよう touch-action も止める
- 暗い地にする。透けて見える HMD の画面では、明るい地が目に強いため（試作の読みで、機械では確かめていない）
- 作っている間、画面が消えないように頼む（断られても動く）
- 声とカメラの区切りの回（web.clips）: 作業の頁は録らないが、開いた時の回の判定は残す（clips.start_assets・同じ出所から 3 時間の内なら
  引き継ぎ、直に開いた時と戻る釦で読み直さずに戻った時は作り始め。#655 の守り。前の頁で録った声が、次の人の のこす に並ばないため）
"""
import json

from omochae import hypotheses

from . import clips, kumitate, skin
from .skin import esc

CAMERA, CAMERA_OFF = "カメラを出す", "カメラを止める"
# 断りの 1 行（本人 11-08「字の替え 11 か所も、…推しのとおり。」の 5 と 6）。カメラの道と HMD の道で、送る物が違う（HMD の道は写真を撮らない）
CAM_NOTE = "聞くと、声をこのサイトの中で字にし、その字と手元の写真（3 枚まで）を Claude に送って答えます。答えたら、このサイトの側では消します。手元だけを写してください。"
HMD_NOTE = "聞くと、声をこのサイトの中で字にし、その字だけを Claude に送って答えます。この頁では写真を撮りません。答えたら、このサイトの側では消します。"
OTONA_LINK = "保護者の方へ、ファシリテーターの方へ"  # 前からある頁の名（くわしい説明の道）
KEEP_LINK = "のこす"  # 帯の駅の字（前からの道）
NO_CAMERA = "この機械ではカメラを使えません。"
# 手帖の手順の画面から作業の頁へ行く印の字（本人 11-08「4 つとも推しのとおり。」の ②。前は「カメラに重ねる」）
CAM_LINK = "カメラで聞く"
# 聞く口の字（本人 11-08 の ③ の 5 つと、字の替えの 7）
ASK, LISTENING, THINKING, ANSWER = "聞く", "聞いています", "考えています", "こたえ"
ASK_PUBLIC = "この場では聞けません"
ASK_NOHEARD = "聞き取れませんでした。もう一度「聞く」を押して話してください。"
ASK_DOWN = "今は答えられません"  # 手帖の「こまった」の口が答えを出せない時と同じ字（web.techo_step）。声を字にする道具が無い・時間切れの時
PREV, NEXT = "もどる", "つぎ"  # ← → の読み上げの名（前からの字）
ASK_SECONDS = 12  # 1 回に録る長さの上限（設計の 2 版の止め 4。問いは短い方が字にするのも答えるのも速い）
FRAMES, FRAME_EDGE = 3, 960  # 手元の写真の数と長い辺（px）。受け口の上限（play_server.ASK_FRAME_BYTES）に収まる大きさ
HOLD_MS = 600  # これより長く押して離したら「押している間」の形、短ければ「1 回押して始める」形と読む

TOYS = ("NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R")  # 作業の頁を開く玩具（御来迎・虎。手帖からの印もこの 2 つだけ）
TITLE = "作業しながら見る（試作）"
TRIAL = "試作です。HMD（頭に付ける画面）で、両手を空けたまま見る形を試しています。"

# 地図: 下から 映像（カメラの道だけ・指を受けない）→ 字と押す所。押す所は「聞く」を大きく 1 つ、← → とカメラは小さく
STYLE = """
body.hmd-page{background:#14161a;color:#f3efe6}
.hmd-page .nav,.hmd-page .foot{display:none}
.hmd-page main{max-width:none;padding:0 max(16px,2vw)}
.hmd{display:flex;flex-direction:column;gap:12px;min-height:100vh;min-height:100dvh;box-sizing:border-box;padding:12px 0 16px}
.hmd-top{display:flex;gap:8px 18px;align-items:baseline;font-size:clamp(15px,1.5vw,24px);letter-spacing:.04em;color:#c9c2b4}
.hmd-top b{color:#f3efe6;font-weight:600}
#hmd-count{font-variant-numeric:tabular-nums;white-space:nowrap}
.hmd-step{display:grid;grid-template-columns:64px minmax(0,1fr) 64px;gap:10px;align-items:center}
#hmd-text{margin:0;font-size:clamp(17px,2.4vw,34px);line-height:1.5;letter-spacing:.03em;color:#fffaf0;max-height:4.5em;overflow:auto}
.hmd button{margin:0;min-height:64px;border-radius:14px;border:2px solid #6b7280;background:#22262d;color:#f3efe6;cursor:pointer;font-size:clamp(17px,2vw,28px);letter-spacing:.06em;text-align:center;justify-content:center}
.hmd button:focus-visible{outline:4px solid #ffe08a;outline-offset:3px}
.hmd button[disabled]{opacity:.35;cursor:default}
.hmd-step button{width:64px;padding:0;font-size:28px;letter-spacing:0}
#hmd-answer{margin:0;padding:10px 14px;border-left:4px solid #7fd1a8;max-height:40vh;overflow:auto}
#hmd-answer h2{margin:0 0 4px;font-size:15px;letter-spacing:.12em;color:#bff0d6;font-weight:600}
#hmd-reply{margin:0;font-size:clamp(18px,2.2vw,30px);line-height:1.6}
#hmd-state{margin:0;min-height:1.4em;font-size:clamp(16px,1.8vw,26px);color:#ffe08a;text-align:center}
.hmd-acts{margin-top:auto;display:flex;gap:12px;justify-content:center;align-items:stretch}
.hmd-acts #hmd-ask{flex:0 1 420px;min-height:96px;font-size:clamp(26px,3vw,44px);letter-spacing:.2em;background:#2e5b46;border-color:#7fd1a8;
 -webkit-user-select:none;user-select:none;-webkit-touch-callout:none;touch-action:none}
.hmd-acts #hmd-ask[aria-pressed=true]{background:#5a2f2f;border-color:#e09b9b}
.hmd-acts #hmd-ask[data-state=wait]{background:#3b3550;border-color:#a99be0}
.hmd-acts #hmd-camera{flex:0 0 auto;padding:0 .7em;font-size:clamp(15px,1.6vw,22px);letter-spacing:.02em}
.hmd-note{margin:0;font-size:13px;line-height:1.7;color:#9a9385;max-width:60em}
.hmd-note a{color:#c9c2b4}
.hmd-list{display:flex;flex-wrap:wrap;gap:18px;margin:18px 0}
.hmd-list a{display:inline-flex;align-items:center;min-height:96px;padding:0 34px;font-size:clamp(26px,2.6vw,42px);border:2px solid #7fd1a8;border-radius:14px;color:#f3efe6;text-decoration:none}
body.hmd-cam{background:#000}
#hmd-cam{position:fixed;inset:0;width:100%;height:100%;object-fit:cover;z-index:-1;background:#000;pointer-events:none}
body.hmd-cam .hmd-top,body.hmd-cam .hmd-step,body.hmd-cam #hmd-answer,body.hmd-cam .hmd-note{background:rgba(0,0,0,.55);border-radius:10px;padding:6px 10px}
body.hmd-cam #hmd-text,body.hmd-cam #hmd-reply{text-shadow:0 1px 3px #000}
body.hmd-cam .hmd button{background:rgba(34,38,45,.85)}
body.hmd-cam .hmd-acts #hmd-ask{background:rgba(46,91,70,.92)}
@media (max-aspect-ratio:1/1){.hmd{gap:8px;padding-top:8px}.hmd-note{font-size:12px}}
@media (prefers-reduced-motion:reduce){.hmd button{transition:none}}
"""

SCRIPT = r"""<script>(()=>{
const $=id=>document.getElementById(id),body=document.body;
const T=JSON.parse($('hmd-words').textContent);
const text=$('hmd-text'),count=$('hmd-count'),prev=$('hmd-prev'),next=$('hmd-next');
const askBtn=$('hmd-ask'),stateLine=$('hmd-state'),answer=$('hmd-answer'),reply=$('hmd-reply'),note=$('hmd-cam-note');
// ---- 今の手順（頁の中だけ。番号だけを聞く時に送り、字は送らない。サーバは同じ文から字を引く）
let at=0;const N=T.steps.length;
const paint=()=>{text.textContent=T.steps[at]||'';count.textContent=N?(at+1)+' / '+N:'';prev.disabled=at===0;next.disabled=at>=N-1;body.dataset.at=at};
const go=d=>{const k=Math.max(0,Math.min(N-1,at+d));if(k!==at){at=k;paint()}};
prev.addEventListener('click',()=>go(-1));next.addEventListener('click',()=>go(1));
// 鍵（足の踏み板・指輪の送りは PageDown・PageUp を送る）。字の欄は無いが、釦の上の Enter とスペースは釦に任せる
document.addEventListener('keydown',e=>{if(e.altKey||e.ctrlKey||e.metaKey)return;const el=e.target;if(el&&el.closest&&el.closest('button')&&(e.key===' '||e.key==='Enter'))return;
 const k={ArrowRight:1,PageDown:1,ArrowLeft:-1,PageUp:-1}[e.key];if(k){e.preventDefault();go(k)}});
paint();
// 作っている間、画面が消えないように頼む（断られても動く）
const wake=()=>{try{if(navigator.wakeLock&&!document.hidden)navigator.wakeLock.request('screen').catch(()=>{})}catch(_){}};
wake();
// ---- カメラ（カメラの道だけ）。映像は頁の下に敷くだけ。写真は「聞く」の間だけ、後ろのカメラと分かる時だけ撮る
const cam=$('hmd-cam'),camBtn=$('hmd-camera');let tracks=null;
const back=()=>{if(!tracks)return false;const v=tracks.find(x=>x.kind==='video');if(!v||v.readyState!=='live')return false;
 try{return (v.getSettings().facingMode||'')==='environment'}catch(_){return false}};
const camOff=()=>{if(tracks)tracks.forEach(x=>x.stop());tracks=null;if(cam)cam.srcObject=null;body.classList.remove('cam-on');if(camBtn)camBtn.textContent=T.camera};
if(cam&&camBtn){
 if(!navigator.mediaDevices||!navigator.mediaDevices.getUserMedia){camBtn.hidden=true;note.textContent=T.nocamera}
 camBtn.addEventListener('click',async()=>{if(tracks){camOff();return}
  try{const s=await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'}},audio:false});tracks=s.getTracks();cam.srcObject=s;
   body.classList.add('cam-on');body.dataset.back=back()?'1':'0';camBtn.textContent=T.cameraoff}catch(_){note.textContent=T.nocamera}})}
const shot=()=>new Promise(res=>{try{if(T.hmd||!cam||!back()||!cam.videoWidth)return res(null);
 const w=cam.videoWidth,h=cam.videoHeight,k=Math.min(1,T.edge/Math.max(w,h)),c=document.createElement('canvas');c.width=Math.round(w*k);c.height=Math.round(h*k);
 c.getContext('2d').drawImage(cam,0,0,c.width,c.height);
 const fit=q=>c.toBlob(b=>{if(b&&b.size>T.frameMax&&q>.45)return fit(q-.15);res(b&&b.size<=T.frameMax?b:null)},'image/jpeg',q);fit(.8)}catch(_){res(null)}});
const b64=blob=>new Promise(res=>{const r=new FileReader();r.onload=()=>res(String(r.result).split(',')[1]||'');r.onerror=()=>res('');r.readAsDataURL(blob)});
// ---- 聞く。録るのは押している間だけ（押したまま離す形と、1 回押して始め 2 回目で止める形のどちらでも）。送るのは止めた時の 1 回だけ
let rec=null,mic=null,chunks=[],shots=[],timer=null,ticks=[],downAt=0,busy=false,drop=false;
const say=s=>{stateLine.textContent=s||''};
const speak=s=>{try{if(!window.speechSynthesis||!s)return;speechSynthesis.cancel();const u=new SpeechSynthesisUtterance(s);u.lang='ja-JP';speechSynthesis.speak(u)}catch(_){}};
const unlock=()=>{try{if(window.speechSynthesis){speechSynthesis.cancel();speechSynthesis.speak(new SpeechSynthesisUtterance(''))}}catch(_){}};
const show=s=>{reply.textContent=s;answer.hidden=!s;speak(s)};
const idle=()=>{busy=false;askBtn.textContent=T.ask;askBtn.setAttribute('aria-pressed','false');delete askBtn.dataset.state;say('')};
const clear=()=>{ticks.forEach(clearTimeout);ticks=[];clearTimeout(timer);timer=null;if(mic)mic.getTracks().forEach(x=>x.stop());mic=null};
const kind=()=>{const M=window.MediaRecorder;if(!M)return '';if(M.isTypeSupported&&M.isTypeSupported('audio/webm;codecs=opus'))return 'audio/webm;codecs=opus';
 if(M.isTypeSupported&&M.isTypeSupported('audio/mp4'))return 'audio/mp4';return ''};
async function begin(){
 if(busy||rec)return;busy=true;unlock();if(window.speechSynthesis)try{speechSynthesis.cancel()}catch(_){}
 const type=kind();if(!type||!navigator.mediaDevices||!navigator.mediaDevices.getUserMedia){busy=false;say(T.novoice);return}
 try{mic=await navigator.mediaDevices.getUserMedia({audio:true,video:false})}catch(_){busy=false;say(T.novoice);return}
 if(document.hidden){clear();busy=false;return}
 chunks=[];shots=[];drop=false;
 try{rec=new MediaRecorder(mic,{mimeType:type})}catch(_){clear();busy=false;say(T.novoice);return}
 rec.ondataavailable=e=>{if(e.data&&e.data.size)chunks.push(e.data)};
 rec.onstop=()=>finish(type.split(';')[0]);
 rec.start();askBtn.textContent=T.listening;askBtn.setAttribute('aria-pressed','true');say(T.listening);
 for(let i=0;i<T.frames;i++)ticks.push(setTimeout(()=>{if(rec)shots.push(shot())},i*1000));
 timer=setTimeout(end,T.seconds*1000)}
function end(){if(rec&&rec.state!=='inactive')rec.stop()}
async function finish(type){
 const parts=chunks;chunks=[];rec=null;const pending=shots;shots=[];clear();
 if(drop){idle();return}
 const blob=new Blob(parts,{type});if(!blob.size){idle();show(T.noheard);return}
 askBtn.dataset.state='wait';askBtn.textContent=T.thinking;askBtn.setAttribute('aria-pressed','false');say(T.thinking);
 const frames=[];for(const p of pending){const b=await p;if(b)frames.push(await b64(b))}
 let text=T.down;
 try{const r=await fetch(`/toy/${T.sid}/kasane/ask`,{method:'POST',headers:{'Content-Type':'application/json'},
   body:JSON.stringify({step:at+1,type,voice:await b64(blob),frames:T.hmd?[]:frames.filter(Boolean)})});
  const j=await r.json().catch(()=>null);if(j&&j.text)text=j.text}catch(_){}
 idle();show(text)}
// 押した時に始め、長く押して離したら止める。短く押した時は録り続け、次に押した時か上限の秒で止める
askBtn.addEventListener('pointerdown',e=>{if(e.button)return;e.preventDefault();if(rec){end();return}downAt=performance.now();begin()});
// 読み上げの許しは、指では離した時に付く（指の pointerdown は押した手当てに数えない機械がある）ので、離した時にも呼ぶ
const up=()=>{unlock();if(rec&&downAt&&performance.now()-downAt>=T.hold)end();downAt=0};
askBtn.addEventListener('pointerup',up);askBtn.addEventListener('pointercancel',up);
// 鍵で押した時（Enter・スペース）は 1 回押して始め、もう 1 回で止める形
askBtn.addEventListener('click',e=>{if(e.detail!==0)return;unlock();if(rec)end();else begin()});
askBtn.addEventListener('contextmenu',e=>e.preventDefault());
// 頁を隠すか離れたら、カメラと録りを止める。録りかけの声は送らない
const away=()=>{if(rec){drop=true;end()}else clear();camOff()};
document.addEventListener('visibilitychange',()=>{if(document.hidden)away();else wake()});
addEventListener('pagehide',away);
})()</script>"""


def steps(sid):
    """頁に出す手順の字（組み方の節と同じ文。聞く口も同じ文から今の手順の字を引く・play_server.kumitate_steps）。"""
    return kumitate.steps(sid, pictures=False)[0]


def available(sid):
    return sid in TOYS and bool(steps(sid))


def page(sid, look="tenji", cam=False):
    """1 つの玩具の、作業しながら見る頁。帯と足は出さない（見る所を手順の字と「聞く」とこたえだけにする）。
    cam=True はカメラの道（後ろのカメラの映像を頁の下に敷く。/toy/<印>/kasane）。cam=False は HMD の道（/toy/<印>/kasane/hmd・写真を撮らない）。
    道は玩具ごとに置く: 作る口は手帖 1 つの決まり（地図の 1）なので、玩具を選ぶ頁は持たず、選びなおす時は入口へ戻す。"""
    toy = hypotheses.load(sid)["toy"]
    texts = steps(sid)
    words = {"steps": texts, "sid": sid, "hmd": not cam, "ask": ASK, "listening": LISTENING, "thinking": THINKING, "noheard": ASK_NOHEARD, "down": ASK_DOWN,
             "novoice": clips.NO_VOICE, "camera": CAMERA, "cameraoff": CAMERA_OFF, "nocamera": NO_CAMERA,
             "seconds": ASK_SECONDS, "frames": FRAMES if cam else 0, "edge": FRAME_EDGE, "hold": HOLD_MS, "frameMax": 300 * 1024}
    # 字の中の < は \u003c にして、手順の字が script の終わりの印にならないようにする（f 文字列の中に \ を書かない: 3.11 で読めない・test_min_python）
    data = json.dumps(words, ensure_ascii=False).replace("<", "\\u003c")
    camera = '<video id="hmd-cam" playsinline muted autoplay></video>' if cam else ""
    camera_btn = f'<button type="button" id="hmd-camera">{esc(CAMERA)}</button>' if cam else ""
    body = (f'<div class="hmd"><div class="hmd-top"><b>{esc(toy)}</b><span id="hmd-count">{f"1 / {len(texts)}" if texts else ""}</span></div>'
            f'<div class="hmd-step"><button type="button" id="hmd-prev" aria-label="{esc(PREV)}" disabled>←</button>'
            f'<p id="hmd-text" aria-live="polite">{esc(texts[0]) if texts else ""}</p>'
            f'<button type="button" id="hmd-next" aria-label="{esc(NEXT)}">→</button></div>'
            f'<section id="hmd-answer" hidden><h2>{esc(ANSWER)}</h2><p id="hmd-reply" aria-live="polite"></p></section>'
            f'<p id="hmd-state" aria-live="polite"></p>'
            f'<div class="hmd-acts"><button type="button" id="hmd-ask" aria-pressed="false">{esc(ASK)}</button>{camera_btn}</div>'
            f'<p class="hmd-note"><span id="hmd-cam-note">{esc(CAM_NOTE if cam else HMD_NOTE)}</span> <a href="/otona">{esc(OTONA_LINK)}</a> '
            f'<a href="/toy/{esc(sid)}/techo/kiroku">{esc(KEEP_LINK)}</a> {esc(TRIAL)} <a href="/">玩具を選びなおす</a></p></div>{camera}'
            f'<script type="application/json" id="hmd-words">{data}</script>{SCRIPT}{clips.start_assets(sid)}')
    return skin.shell(f"{toy}: {TITLE}", body, look, path=f"/toy/{sid}/kasane" + ("" if cam else "/hmd"), extra_style=STYLE,
                      body_class="hmd-page hmd-cam" if cam else "hmd-page")
