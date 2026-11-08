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
- **回の印と作り始め**（統括の決め 11-08・別の目の止め 3 と、その後の残る道と逆向きの気づき）: 作り始めは「玩具の頁を開いた時
  （のこす から戻った時を除く）」。その時に回の印（sessionStorage の utsushi-run:<印>）を新しく作り、その玩具の印の無い区切りを消し、
  次に渡す時は新しい渡す印にする。作業の頁と手帖の「はじめる」は、同じ玩具の回の印が 3 時間の内なら引き継ぐ（玩具の頁で話す → 作業の頁 →
  のこす と同じタブで続けて移った時は同じ回として消さない）。回の印が無い時だけ、そこで作り始める。区切りには回の印を付け、渡す時は
  今の回の印の付いた物だけに渡す印を付ける。前の人が録っただけで去っても、次の人が玩具の頁を開いた時に消え、次の人の承認で送られない。
  戻る釦で頁が読み直されずに作業の頁へ戻った時（pageshow の persisted）は、前の頁が分からないので作り始めとする（実機でまだ確かめていない）。
  作業の頁と手帖を、前の頁がこのサイトの頁でない所（referrer が空か外）から開いた時も作り始めとする（URL を直に打って入った時・統括の決め）。
  開いたまま次の人へ渡した時は見分けようがないので、進め役の手引き（workshop-guide）に、渡す前の 1 手を書いた。
- **印は玩具ごと**（sessionStorage の utsushi-pass:<印>）。のこす へ移るたびに、3 時間の内の今の印を使い直す（戻って録り足した後に渡しても、
  前に渡した区切りが消えない・別の目の気づき）。承認の終わりの消しは、その玩具の区切りと印だけ（ほかの玩具の区切りを消さない）。
- 字（本人の OK 11-08）: FIRST・STORE・FULL・NO_VOICE・REMOVE・HEAD・CLIP_FAIL。STORE の最後の 1 句は本人の答えの字（11-08「このサイトをほかの画面で開くと、前に録った声と映像は消えます。」）
"""
from .skin import esc

CLIP_HOURS = 3   # 端末の中に置く長さ（統括の決め）。サーバの側の 72 時間の掃除とは別
CLIP_MAX = 5     # 声とカメラ、それぞれの数（窓口の決め）
CAM_SECONDS = 10  # 押した後に録る長さ（A2・窓口の決め）

FIRST = "押した間の声と、押した後の 10 秒の映像を、のこすで承認した時に送り、字にしてから消します。"
STORE = "録った区切りは、のこすで承認するまで、この端末の中だけに置きます。ブラウザを閉じても、次にこのサイトを開くまで残ります（3 時間を過ぎた物と、別の画面の物は、開いた時に消します）。このサイトをほかの画面で開くと、前に録った声と映像は消えます。"
FULL = "区切りは 5 つまでです。のこすで送ってから、また録れます。"
NO_VOICE = "この画面では声を録れません。"
REMOVE = "外す"
HEAD = "録った区切り"
CLIP_FAIL = "記録は残しました。声かカメラの区切りを送れませんでした"  # 区切りを送れなかった時の 1 行（サーバの断りの字はそのまま出さない）

SCRIPT = """<script>(()=>{
if(window.utsushiClips||!window.indexedDB)return;
const HOURS=__HOURS__,MAX=__MAX__,CAM=__CAM__*1000,DB='utsushi-clips',ST='clips',AGE=HOURS*3600000;
const who=()=>{try{return sessionStorage.getItem('utsushi-who')||''}catch(e){return ''}};
const PK=(sid)=>'utsushi-pass:'+sid,NK=(sid)=>'utsushi-pass-new:'+sid,RK=(sid)=>'utsushi-run:'+sid;
const runNow=(sid)=>{try{const r=JSON.parse(sessionStorage.getItem(RK(sid))||'null');return r&&Date.now()-r.at<AGE?r:null}catch(e){return null}};
const passNow=(sid)=>{try{const p=JSON.parse(sessionStorage.getItem(PK(sid))||'null');return p&&Date.now()-p.at<AGE?p:null}catch(e){return null}};
const passMake=(sid)=>{const p={id:newId(),at:Date.now()};try{sessionStorage.setItem(PK(sid),JSON.stringify(p));sessionStorage.removeItem(NK(sid))}catch(e){return null}return p};
// 渡す印は、今の回の印の付いた、まだ印の無い区切りにだけ付ける（前の回の物には付けない）
const mark=async(sid,p)=>{const w=who(),r=runNow(sid);await run('readwrite',s=>{const q=s.openCursor();q.onsuccess=()=>{const cur=q.result;if(!cur)return;const c=cur.value;
  if(c.sid===sid&&c.who===w&&!c.pass&&r&&c.run===r.id){c.pass=p.id;cur.update(c)}cur.continue()};return q})};
// 新しい回: 回の印を作り、その玩具の印の無い区切りを消し、次に渡す時は新しい渡す印にする
const runNew=async(sid)=>{const r={id:newId(),at:Date.now()};try{sessionStorage.setItem(RK(sid),JSON.stringify(r));sessionStorage.setItem(NK(sid),'1')}catch(e){return null}
 for(const c of await all())if(c.sid===sid&&!c.pass)await remove(c.id);return r};
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
 const r=runNow(c.sid)||await runNew(c.sid);
 await run('readwrite',s=>s.put({...c,id:newId(),who:who(),at:Date.now(),pass:null,run:r?r.id:null}));return true};
// 作り始め（玩具の頁を開いた時・戻る釦で読み直さずに戻った時）: 新しい回。のこす の頁から戻って開いた時（fromNokosu）は作り始めとしない
const startMaking=async(sid,fromNokosu)=>{if(fromNokosu&&runNow(sid))return;await runNew(sid)};
// 続き（作業の頁を開いた時・手帖の「はじめる」）: 同じ玩具の回の印が 3 時間の内なら引き継ぐ。無い時だけ作り始める
const goOn=async(sid)=>{if(!runNow(sid))await runNew(sid)};
// 渡す: 3 時間の内の今の印を使い直す（作り始めの後は新しい印）。その玩具の、まだ印の無い区切りにだけ付ける（印の有る物は替えない）
const handOver=async(sid)=>{let p=null;try{p=sessionStorage.getItem(NK(sid))?null:passNow(sid)}catch(e){}p=p||passMake(sid);if(!p)return;await mark(sid,p)};
// のこすの頁: 同じ画面・今の印（3 時間の内）の物だけを返し、その玩具の、印の違う物（印の無い物も）は消す
const handed=async(sid)=>{const p=passNow(sid),w=who(),out=[];for(const c of await all()){if(c.sid!==sid)continue;
 if(p&&c.who===w&&c.pass===p.id)out.push(c);else await remove(c.id)}return out.sort((a,b)=>a.at-b.at)};
// のこすの頁で録った区切り（工夫の欄の話す口）も、承認で送る並びに入れる: 今の印（無ければ作る）を、その玩具の、まだ印の無い区切りに付ける
const adopt=async(sid)=>{const p=passNow(sid)||passMake(sid);if(p)await mark(sid,p)};
// 承認の終わり: その玩具の区切りと印だけを消す（ほかの玩具の区切りは消さない・別の目の気づき）
const clear=async(sid)=>{for(const c of await all())if(c.sid===sid)await remove(c.id);try{sessionStorage.removeItem(PK(sid));sessionStorage.removeItem(NK(sid));sessionStorage.removeItem(RK(sid))}catch(e){}};
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
// 開いた時の振り分け（統括の決め）: 玩具の頁は作り始め（toy）、作業の頁は続き（work）。前の頁が その玩具の のこす なら、どちらも引き継ぐ。
// 呼ぶのは頁の側（玩具の頁と作業の頁が、開いた時に自分の種類を言う）。消し（purge）を済ませてから振り分ける
let purged=null;
// 作業の頁を、前の頁がこのサイトの頁でない所（URL を直に打った・外のリンク）から開いた時は、続きでなく作り始めにする
// （玩具の頁を通らずに直に入った前の人の区切りを、3 時間の内に直に入った次の人に渡さない・別の目の確かめ 11-08・統括の決め）
const fromOutside=()=>{try{return !document.referrer||new URL(document.referrer).origin!==location.origin}catch(e){return true}};
const openedAs=async(sid,kind)=>{await purged;let back=false;try{back=new URL(document.referrer).pathname==='/toy/'+sid+'/techo/kiroku'}catch(e){}
 if(kind==='work')return back||(fromOutside()?startMaking(sid,false):goOn(sid));return startMaking(sid,back)};
addEventListener('DOMContentLoaded',()=>{purged=purge().catch(()=>{})});
window.utsushiClips={put,list:handed,adopt,remove,clear,handOver,startMaking,goOn,openedAs,voiceStart,voiceStop,camClip};
// その場限りの印は頁の終わりの台本（skin.WHO_SCRIPT）が作るので、消しは頁を読み終えた後に回す
})()</script>"""


# 手帖の作る頁に置く小さな台本: 「はじめる」の作り始めの消しだけ（その頁は録らない決まりで、録る code を持たない・test_techo_step）。
# 置き場の台本（SCRIPT）と同じ db・同じ印の名を使う。外へ送る口も持たない
START_SCRIPT = """<script>(()=>{if(!window.indexedDB)return;
window.utsushiClipsStart=(sid)=>{try{const r=JSON.parse(sessionStorage.getItem('utsushi-run:'+sid)||'null');
  // 手帖を、前の頁がこのサイトの頁でない所から開いた時は、回を引き継がずに作り始める（作業の頁と同じ・直に入った前の人の区切りを渡さない）
  let out=true;try{out=!document.referrer||new URL(document.referrer).origin!==location.origin}catch(e){}
  if(r&&!out&&Date.now()-r.at<__HOURS__*3600000)return;sessionStorage.setItem('utsushi-run:'+sid,JSON.stringify({id:Math.random().toString(36).slice(2)+Date.now().toString(36),at:Date.now()}));
  sessionStorage.setItem('utsushi-pass-new:'+sid,'1')}catch(e){return}
 const q=indexedDB.open('utsushi-clips',1);q.onupgradeneeded=()=>q.result.createObjectStore('clips',{keyPath:'id'});
 q.onsuccess=()=>{const db=q.result,t=db.transaction('clips','readwrite'),c=t.objectStore('clips').openCursor();
  c.onsuccess=()=>{const cur=c.result;if(!cur)return;if(cur.value.sid===sid&&!cur.value.pass)cur.delete();cur.continue()};t.oncomplete=()=>db.close()}};
})()</script>"""


def start_assets():
    """手帖の作る頁に置く小さな台本（数は 1 か所の値から入れる）。"""
    return START_SCRIPT.replace("__HOURS__", str(CLIP_HOURS))


def assets():
    """頁に 1 回だけ置く台本。数は 1 か所の値から入れる。"""
    return SCRIPT.replace("__HOURS__", str(CLIP_HOURS)).replace("__MAX__", str(CLIP_MAX)).replace("__CAM__", str(CAM_SECONDS))


def notes():
    """録る所に添える 2 行（初めて録る時の 1 行と、端末の置き場の 1 行）。"""
    return f'<span class="clip-note">{esc(FIRST)}</span> <span class="clip-note">{esc(STORE)}</span>'
