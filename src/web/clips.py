"""声とカメラの区切りの、端末の中の置き場（本人 11-08 330・412・415・「公開デモでも声も録る。」、窓口の決め A2・承認の時にまとめて・それぞれ 5 つまで）。
設計は grove の state/voice-camera-send-20261108.md の 3 版（別の目の検品 3 回）と、作る時の統括の直し。

判断の芯:
- **録るのは押した時だけ。** 声は話す口の「話す」を押して話した間（hanasu が voiceStart・voiceStop を呼ぶ）、カメラは作業の頁の
  「ここで止まった」を押した後の 10 秒（hmd が camClip を呼ぶ）。押す前は何も録らず、何も覚えない（A2）。カメラを出しただけでは録らない。
- **承認まで、utsushi のサーバへは送らない。** 録った区切りは、この端末の IndexedDB に置くだけ。この台本は外へ送る口（fetch など）を持たない。
  送るのは、のこすの頁の「承認」の後の 1 か所（web.nokosu）だけ。
- **開いた時に消す。** IndexedDB は出所ごとにタブをまたいで残り、ブラウザを閉じても消えない。だから、この台本のある頁を開くたびに、
  別の画面（その場限りの印 utsushi-who が違う）の物と、録ってから 3 時間（CLIP_HOURS）を過ぎた物を消す。3 時間は統括の決め
  （工作は 30 分を越える事が多く、始めの方の区切りが のこす の前に消えないように・ワークショップの 1 コマ約 2 時間より長く）。
- **pagehide では消さない。** pagehide は、同じタブで のこす へ移る時にも起き、渡す前に消える。加えて、pagehide の中の IndexedDB の消しは
  終わる前に頁が止まりうる（iPhone の Safari）ので、どのみち頼れない。開いた時に消すのを主にする。
- **「渡す」の印。** のこす へ移る道を押した時に、その玩具の、まだ印の無い区切りにだけ今の印を付ける（統括の直し: 前の人が承認しないで
  去った区切りに、次の人の印が付かないように）。のこすの頁を開いた時は、今の印と違う印（印の無い物も）のその玩具の区切りを消す。
  区切りは「録った頁 → のこす」の 1 回の移りでだけ渡る。
- 数は、その玩具の、まだ渡していない区切りが、声とカメラそれぞれ 5 つ（CLIP_MAX）まで。いっぱいの時は録らず、1 行で知らせる。
- 字（本人の確かめ待ち）: FIRST・STORE・FULL・NO_VOICE・REMOVE・HEAD・CLIP_FAIL。
"""
from .skin import esc

CLIP_HOURS = 3   # 端末の中に置く長さ（統括の決め）。サーバの側の 72 時間の掃除とは別
CLIP_MAX = 5     # 声とカメラ、それぞれの数（窓口の決め）
CAM_SECONDS = 10  # 押した後に録る長さ（A2・窓口の決め）

FIRST = "押した間の声と、押した後の 10 秒の映像を、のこすで承認した時に送り、字にしてから消します。"
STORE = "録った区切りは、のこすで承認するまで、この端末の中だけに置きます。ブラウザを閉じても、次にこのサイトを開くまで残ります（3 時間を過ぎた物と、別の画面の物は、開いた時に消します）。"
FULL = "区切りは 5 つまでです。のこすで送ってから、また録れます。"
NO_VOICE = "この画面では声を録れません。"
REMOVE = "外す"
HEAD = "録った区切り"
CLIP_FAIL = "記録は残しました。声かカメラの区切りを送れませんでした"  # 区切りを送れなかった時の 1 行（サーバの断りの字はそのまま出さない）

SCRIPT = """<script>(()=>{
if(window.utsushiClips||!window.indexedDB)return;
const HOURS=__HOURS__,MAX=__MAX__,CAM=__CAM__*1000,DB='utsushi-clips',ST='clips',AGE=HOURS*3600000;
const who=()=>{try{return sessionStorage.getItem('utsushi-who')||''}catch(e){return ''}};
const passNow=()=>{try{const p=JSON.parse(sessionStorage.getItem('utsushi-pass')||'null');return p&&Date.now()-p.at<AGE?p:null}catch(e){return null}};
const open=()=>new Promise((ok,ng)=>{const q=indexedDB.open(DB,1);q.onupgradeneeded=()=>q.result.createObjectStore(ST,{keyPath:'id'});q.onsuccess=()=>ok(q.result);q.onerror=()=>ng(q.error)});
const run=async(mode,fn)=>{const db=await open();return new Promise((ok,ng)=>{const t=db.transaction(ST,mode),q=fn(t.objectStore(ST));
 t.oncomplete=()=>{db.close();ok(q&&'result' in q?q.result:undefined)};t.onerror=()=>{db.close();ng(t.error)}})};
const all=()=>run('readonly',s=>s.getAll());
const remove=(id)=>run('readwrite',s=>s.delete(id));
const newId=()=>Math.random().toString(36).slice(2)+Date.now().toString(36);
// 開いた時の消し: 別の画面（who が違う）の物と、録ってから 3 時間を過ぎた物
const purge=async()=>{const w=who(),now=Date.now();for(const c of await all())if(!w||c.who!==w||now-c.at>AGE)await remove(c.id)};
const waiting=async(sid,kind)=>(await all()).filter(c=>c.sid===sid&&c.kind===kind&&!c.pass&&c.who===who()).length;
const put=async(c)=>{if(!who()||await waiting(c.sid,c.kind)>=MAX)return false;
 await run('readwrite',s=>s.put({...c,id:newId(),who:who(),at:Date.now(),pass:null}));return true};
// 渡す: 今の印を作り、その玩具の、まだ印の無い区切りにだけ付ける（前の人の、承認しないで去った区切りに付けないため、印の有る物は替えない）
const handOver=async(sid)=>{const p={id:newId(),at:Date.now()};try{sessionStorage.setItem('utsushi-pass',JSON.stringify(p))}catch(e){return}
 const w=who();await run('readwrite',s=>{const q=s.openCursor();q.onsuccess=()=>{const cur=q.result;if(!cur)return;const c=cur.value;
  if(c.sid===sid&&c.who===w&&!c.pass){c.pass=p.id;cur.update(c)}cur.continue()};return q})};
// のこすの頁: 同じ画面・今の印（3 時間の内）の物だけを返し、その玩具の、印の違う物（印の無い物も）は消す
const handed=async(sid)=>{const p=passNow(),w=who(),out=[];for(const c of await all()){if(c.sid!==sid)continue;
 if(p&&c.who===w&&c.pass===p.id)out.push(c);else await remove(c.id)}return out.sort((a,b)=>a.at-b.at)};
// のこすの頁で録った区切り（工夫の欄の話す口）も、承認で送る並びに入れる: 今の印（無ければ作る）を、その玩具の、まだ印の無い区切りに付ける
const adopt=async(sid)=>{let p=passNow();if(!p){p={id:newId(),at:Date.now()};try{sessionStorage.setItem('utsushi-pass',JSON.stringify(p))}catch(e){return}}
 const w=who();await run('readwrite',s=>{const q=s.openCursor();q.onsuccess=()=>{const cur=q.result;if(!cur)return;const c=cur.value;
  if(c.sid===sid&&c.who===w&&!c.pass){c.pass=p.id;cur.update(c)}cur.continue()};return q})};
const clear=async()=>{await run('readwrite',s=>s.clear());try{sessionStorage.removeItem('utsushi-pass')}catch(e){}};
// 声: 話す口の「話す」を押した時だけ始め、話し終わりで止める。開けない画面（iPhone の Safari で音声認識とマイクを取り合う時など）は録らない
let vr=null,vs=null;
const voiceStart=async(meta)=>{if(vr||!window.MediaRecorder||!navigator.mediaDevices||!navigator.mediaDevices.getUserMedia)return false;
 if(!who()||await waiting(meta.sid,'t')>=MAX)return false;
 try{vs=await navigator.mediaDevices.getUserMedia({audio:true});const r=new MediaRecorder(vs,{audioBitsPerSecond:32000}),parts=[],t0=Date.now();vr=r;
  r.ondataavailable=(e)=>{if(e.data&&e.data.size)parts.push(e.data)};
  r.onstop=async()=>{const b=new Blob(parts,{type:r.mimeType||'audio/webm'});if(vs)vs.getTracks().forEach(t=>t.stop());vs=null;vr=null;
   if(b.size)await put({...meta,kind:'t',type:b.type,size:b.size,ms:Date.now()-t0,blob:b})};
  r.start();return true}catch(e){if(vs)vs.getTracks().forEach(t=>t.stop());vs=null;vr=null;return false}};
const voiceStop=()=>{if(vr&&vr.state!=='inactive')vr.stop()};
// カメラ: 作業の頁の「ここで止まった」を押した後の 10 秒だけ。映像の流れ（音なし）は頁が持つ物を使い、ここで新しく開かない
let cr=null;
const camClip=async(stream,meta)=>{if(cr||!window.MediaRecorder||!stream)return 'none';if(!who())return 'none';
 if(await waiting(meta.sid,'k')>=MAX)return 'full';
 let r;try{r=new MediaRecorder(stream,{videoBitsPerSecond:1000000})}catch(e){return 'none'}
 const parts=[];cr=r;r.ondataavailable=(e)=>{if(e.data&&e.data.size)parts.push(e.data)};
 r.onstop=async()=>{cr=null;const b=new Blob(parts,{type:r.mimeType||'video/webm'});if(b.size)await put({...meta,kind:'k',type:b.type,size:b.size,ms:CAM,blob:b})};
 r.start();setTimeout(()=>{if(r.state!=='inactive')r.stop()},CAM);return 'rec'};
// のこす へ移る道（記録の頁 /toy/<印>/techo/kiroku）を押した時に渡す。台本の無い画面では、ふつうのリンクのまま動く
document.addEventListener('click',(e)=>{const a=e.target.closest&&e.target.closest('a[href]');if(!a)return;
 const m=new URL(a.href,location.href).pathname.match(/^\\/toy\\/([^/]+)\\/techo\\/kiroku$/);if(!m||e.defaultPrevented||e.metaKey||e.ctrlKey)return;
 e.preventDefault();handOver(decodeURIComponent(m[1])).finally(()=>{location.href=a.href})});
window.utsushiClips={put,list:handed,adopt,remove,clear,handOver,voiceStart,voiceStop,camClip};
// その場限りの印は頁の終わりの台本（skin.WHO_SCRIPT）が作るので、消しは頁を読み終えた後に回す
addEventListener('DOMContentLoaded',()=>{purge().catch(()=>{})});
})()</script>"""


def assets():
    """頁に 1 回だけ置く台本。数は 1 か所の値から入れる。"""
    return SCRIPT.replace("__HOURS__", str(CLIP_HOURS)).replace("__MAX__", str(CLIP_MAX)).replace("__CAM__", str(CAM_SECONDS))


def notes():
    """録る所に添える 2 行（初めて録る時の 1 行と、端末の置き場の 1 行）。"""
    return f'<span class="clip-note">{esc(FIRST)}</span> <span class="clip-note">{esc(STORE)}</span>'
