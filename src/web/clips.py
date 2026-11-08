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
- **手帖の「のこす」の後**（#659 の取り消しの後の作り直し・統括の決め 11-08 (a)）: 手帖の頁は送らず、IndexedDB も開かない。区切りを置いた時に
  sessionStorage の utsushi-clips-made:<印> に今の回の印を書き、手帖はそれが今の回と同じ時だけ、記録の後に のこすの頁の「区切りだけ」の確かめ
  （#to=<記録の番号>）へ移る。送るのは、そこでの「承認」の後だけ（窓口の決め「承認の時にまとめて」・本人の OK の字 STORE のまま）。
- **のこすの頁を開いた時**（openedAs の 'nokosu'・別の目の #659 の止め 2）: 前の頁が同じ出所の作る頁（玩具の頁・作業の頁・作りながら見る頁・手帖）の
  時だけ渡す（handOver。その玩具の頁と、その下の頁で、のこすの頁そのものは除く）。直に開いた時（前の頁が外か空）は作り始めで、渡す印も外す（前の人の物は、渡した物も含めて並ばずに消える）。
  ほかの頁（もちよるなど）から来た時は渡さずに並べるだけ。作りながら見る頁と手帖の頁も、開いた時に作り始めかを見る（start_assets(sid)）。
- **区切りだけの確かめの読み直し**（別の目の設計の確かめ 2）: その画面は並べた後に who を作り直すので、読み直すと自分の区切りが開いた時の消しで
  黙って消えていた。並べる前の who を 1 回分だけ控え（sessionStorage の utsushi-clips-keep・玩具と記録の番号つき）、同じ確かめの画面
  （/toy/<印>/techo/kiroku#to=<その番号>&…）でだけ、その who の区切りを消さずに並べる。ほかの頁では控えを見ないので、前の人の区切りは消える。
  出口（承認・もちよるへ移る時）で控えを消す。
- **待つのは置き場が開くまでだけ**（別の目の #659 の気づき）: 開かない時は、待つ秒（OPEN_WAIT）を過ぎたら断る。
  送る側は、それを送れなかった事として扱う（CLIP_FAIL）。送り（fetch）には切りを掛けない（遅い網で、送っている途中の区切りを捨てて頁を移らないように）。
- **印は玩具ごと**（sessionStorage の utsushi-pass:<印>）。のこす へ移るたびに、3 時間の内の今の印を使い直す（戻って録り足した後に渡しても、
  前に渡した区切りが消えない・別の目の気づき）。承認の終わりの消しは、その玩具の区切りと印だけ（ほかの玩具の区切りを消さない）。
- 字（本人の OK 11-08）: FIRST・STORE・FULL・NO_VOICE・REMOVE・HEAD・CLIP_FAIL。STORE の最後の 1 句は本人の答えの字（11-08「このサイトをほかの画面で開くと、前に録った声と映像は消えます。」）
"""
import json

from .skin import esc

CLIP_HOURS = 3   # 端末の中に置く長さ（統括の決め）。サーバの側の 72 時間の掃除とは別
CLIP_MAX = 5     # 声とカメラ、それぞれの数（窓口の決め）
CAM_SECONDS = 10  # 押した後に録る長さ（A2・窓口の決め）
OPEN_WAIT = 6     # 置き場（IndexedDB）が開くのを待つ秒。頭なしの試験の仮の時計や止まった置き場で、承認や移りが止まったままにならないように

FIRST = "押した間の声と、押した後の 10 秒の映像を、のこすで承認した時に送り、字にしてから消します。"
STORE = "録った区切りは、のこすで承認するまで、この端末の中だけに置きます。ブラウザを閉じても、次にこのサイトを開くまで残ります（3 時間を過ぎた物と、別の画面の物は、開いた時に消します）。このサイトをほかの画面で開くと、前に録った声と映像は消えます。"
FULL = "区切りは 5 つまでです。のこすで送ってから、また録れます。"
NO_VOICE = "この画面では声を録れません。"
REMOVE = "外す"
HEAD = "録った区切り"
CLIP_FAIL = "記録は残しました。声かカメラの区切りを送れませんでした"  # 区切りを送れなかった時の 1 行（サーバの断りの字はそのまま出さない）

SCRIPT = """<script>(()=>{
if(window.utsushiClips||!window.indexedDB)return;
const HOURS=__HOURS__,MAX=__MAX__,CAM=__CAM__*1000,WAIT=__WAIT__*1000,DB='utsushi-clips',ST='clips',AGE=HOURS*3600000;
const who=()=>{try{return sessionStorage.getItem('utsushi-who')||''}catch(e){return ''}};
const PK=(sid)=>'utsushi-pass:'+sid,NK=(sid)=>'utsushi-pass-new:'+sid,RK=(sid)=>'utsushi-run:'+sid,MK=(sid)=>'utsushi-clips-made:'+sid;
// 区切りだけの確かめの画面で控えた、並べる前の who（その画面でだけ使う）
const KEEP='utsushi-clips-keep';
const kept=()=>{try{const k=JSON.parse(sessionStorage.getItem(KEEP)||'null');if(!k||Date.now()-k.at>=AGE)return null;
 return location.pathname==='/toy/'+k.sid+'/techo/kiroku'&&location.hash.startsWith('#to='+k.rec+'&')?k:null}catch(e){return null}};
const keepWho=(sid,rec)=>{try{const k=kept();if(k&&k.sid===sid&&k.rec===rec)return;sessionStorage.setItem(KEEP,JSON.stringify({sid,rec,who:who(),at:Date.now()}))}catch(e){}};
const dropKeep=()=>{try{sessionStorage.removeItem(KEEP)}catch(e){}};
const runNow=(sid)=>{try{const r=JSON.parse(sessionStorage.getItem(RK(sid))||'null');return r&&Date.now()-r.at<AGE?r:null}catch(e){return null}};
const passNow=(sid)=>{try{const p=JSON.parse(sessionStorage.getItem(PK(sid))||'null');return p&&Date.now()-p.at<AGE?p:null}catch(e){return null}};
const passMake=(sid)=>{const p={id:newId(),at:Date.now()};try{sessionStorage.setItem(PK(sid),JSON.stringify(p));sessionStorage.removeItem(NK(sid))}catch(e){return null}return p};
// 渡す印は、今の回の印の付いた、まだ印の無い区切りにだけ付ける（前の回の物には付けない）
const mark=async(sid,p)=>{const w=who(),r=runNow(sid);await run('readwrite',s=>{const q=s.openCursor();q.onsuccess=()=>{const cur=q.result;if(!cur)return;const c=cur.value;
  if(c.sid===sid&&c.who===w&&!c.pass&&r&&c.run===r.id){c.pass=p.id;cur.update(c)}cur.continue()};return q})};
// 新しい回: 回の印を作り、その玩具の印の無い区切りを消し、次に渡す時は新しい渡す印にする
const runNew=async(sid)=>{const r={id:newId(),at:Date.now()};try{sessionStorage.setItem(RK(sid),JSON.stringify(r));sessionStorage.setItem(NK(sid),'1')}catch(e){return null}
 for(const c of await all())if(c.sid===sid&&!c.pass)await remove(c.id);return r};
// 待つのは開くまでだけ。開かなければ断る（遅れて開いたら閉じる）。一度開かなかった頁では、次からは待たずに断る（待ちを重ねない）
let dead=false;
const open=()=>new Promise((ok,ng)=>{if(dead)return ng(new Error('wait'));let late=false;const t=setTimeout(()=>{late=true;dead=true;ng(new Error('wait'))},WAIT);const q=indexedDB.open(DB,1);
 q.onupgradeneeded=()=>q.result.createObjectStore(ST,{keyPath:'id'});q.onsuccess=()=>{clearTimeout(t);if(late)q.result.close();else ok(q.result)};q.onerror=()=>{clearTimeout(t);ng(q.error)}});
const run=async(mode,fn)=>{const db=await open();return new Promise((ok,ng)=>{const t=db.transaction(ST,mode),q=fn(t.objectStore(ST));
 t.oncomplete=()=>{db.close();ok(q&&'result' in q?q.result:undefined)};t.onerror=()=>{db.close();ng(t.error)}})};
const all=()=>run('readonly',s=>s.getAll());
const remove=(id)=>run('readwrite',s=>s.delete(id));
const newId=()=>Math.random().toString(36).slice(2)+Date.now().toString(36);
// 開いた時の消し: 別の画面（who が違う）の物と、録ってから 3 時間を過ぎた物
const purge=async()=>{const w=who(),k=kept(),now=Date.now();for(const c of await all())if(!w||(c.who!==w&&!(k&&c.sid===k.sid&&c.who===k.who))||now-c.at>AGE)await remove(c.id)};
const waiting=async(sid,kind)=>(await all()).filter(c=>c.sid===sid&&c.kind===kind&&!c.pass&&c.who===who()).length;
const put=async(c)=>{if(!who()||await waiting(c.sid,c.kind)>=MAX)return false;
 const r=runNow(c.sid)||await runNew(c.sid);
 await run('readwrite',s=>s.put({...c,id:newId(),who:who(),at:Date.now(),pass:null,run:r?r.id:null}));
 // 手帖の「のこす」が、のこすの頁の確かめへ移るかを IndexedDB を開かずに見る印（今の回に区切りを置いた）
 if(r)try{sessionStorage.setItem(MK(c.sid),r.id)}catch(e){}return true};
// 作り始め（玩具の頁を開いた時・戻る釦で読み直さずに戻った時）: 新しい回。のこす の頁から戻って開いた時（fromNokosu）は作り始めとしない
const startMaking=async(sid,fromNokosu)=>{if(fromNokosu&&runNow(sid))return;await runNew(sid)};
// 続き（作業の頁を開いた時・手帖の「はじめる」）: 同じ玩具の回の印が 3 時間の内なら引き継ぐ。無い時だけ作り始める
const goOn=async(sid)=>{if(!runNow(sid))await runNew(sid)};
// 渡す: 3 時間の内の今の印を使い直す（作り始めの後は新しい印）。その玩具の、まだ印の無い区切りにだけ付ける（印の有る物は替えない）
const handOver=async(sid)=>{let p=null;try{p=sessionStorage.getItem(NK(sid))?null:passNow(sid)}catch(e){}p=p||passMake(sid);if(!p)return;await mark(sid,p)};
// のこすの頁: 同じ画面・今の印（3 時間の内）の物だけを返し、その玩具の、印の違う物（印の無い物も）は消す
const handed=async(sid)=>{const p=passNow(sid),w=who(),k=kept(),out=[];for(const c of await all()){if(c.sid!==sid)continue;
 if(p&&(c.who===w||(k&&k.sid===sid&&c.who===k.who))&&c.pass===p.id)out.push(c);else await remove(c.id)}return out.sort((a,b)=>a.at-b.at)};
// のこすの頁で録った区切り（工夫の欄の話す口）も、承認で送る並びに入れる: 今の印（無ければ作る）を、その玩具の、まだ印の無い区切りに付ける
const adopt=async(sid)=>{const p=passNow(sid)||passMake(sid);if(p)await mark(sid,p)};
// 承認の終わり: その玩具の区切りと印だけを消す（ほかの玩具の区切りは消さない・別の目の気づき）
const clear=async(sid)=>{for(const c of await all())if(c.sid===sid)await remove(c.id);try{[PK,NK,RK,MK].forEach(k=>sessionStorage.removeItem(k(sid)))}catch(e){}};
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
const purgeOnce=()=>purged||(purged=purge().catch(()=>{}));
// 作業の頁を、前の頁がこのサイトの頁でない所（URL を直に打った・外のリンク）から開いた時は、続きでなく作り始めにする
// （玩具の頁を通らずに直に入った前の人の区切りを、3 時間の内に直に入った次の人に渡さない・別の目の確かめ 11-08・統括の決め）
const fromOutside=()=>{try{return !document.referrer||new URL(document.referrer).origin!==location.origin}catch(e){return true}};
// 前の頁が、その玩具の作る頁か: 同じ出所の、その玩具の頁と、その下の頁（作業の頁・作りながら見る頁・手帖）。のこすの頁そのもの（読み直し）は除く。
// 道の名を並べて書かない（台本は玩具の頁にも載り、頁の中の道の字を数える試験に当たるため）
const fromMaking=(sid)=>{try{const u=new URL(document.referrer),t='/toy/'+sid;return u.origin===location.origin&&(u.pathname===t||u.pathname.startsWith(t+'/'))&&u.pathname!==t+'/techo/kiroku'}catch(e){return false}};
// のこすの頁（'nokosu'）は並びを返す: 直に開いたら作り始めで渡す印も外す・作る頁から来たら渡す・ほかは並べるだけ（並べる時に印の違う物は消える）
const openedAs=async(sid,kind)=>{await purgeOnce();let back=false;try{back=new URL(document.referrer).pathname==='/toy/'+sid+'/techo/kiroku'}catch(e){}
 if(kind==='nokosu'){if(fromOutside()){await runNew(sid);try{sessionStorage.removeItem(PK(sid))}catch(e){}}else if(fromMaking(sid))await handOver(sid);return handed(sid)}
 if(kind==='work')return back||(fromOutside()?startMaking(sid,false):goOn(sid));return startMaking(sid,back)};
addEventListener('DOMContentLoaded',purgeOnce);
window.utsushiClips={put,list:handed,adopt,remove,clear,handOver,startMaking,goOn,openedAs,keepWho,dropKeep,voiceStart,voiceStop,camClip};
// その場限りの印は頁の終わりの台本（skin.WHO_SCRIPT）が作るので、消しは頁を読み終えた後に回す
})()</script>"""


# 手帖の作る頁に置く小さな台本: 「はじめる」の作り始めの消しだけ（その頁は録らない決まりで、録る code を持たない・test_techo_step）。
# 置き場の台本（SCRIPT）と同じ db・同じ印の名を使う。外へ送る口も持たない
START_SCRIPT = """<script>(()=>{if(!window.indexedDB)return;
// 作り始め: 新しい回の印を作り、次は新しい渡す印にし、その玩具の印の無い区切りを消す
const fresh=(sid)=>{try{sessionStorage.setItem('utsushi-run:'+sid,JSON.stringify({id:Math.random().toString(36).slice(2)+Date.now().toString(36),at:Date.now()}));
  sessionStorage.setItem('utsushi-pass-new:'+sid,'1')}catch(e){return}
 const q=indexedDB.open('utsushi-clips',1);q.onupgradeneeded=()=>q.result.createObjectStore('clips',{keyPath:'id'});
 q.onsuccess=()=>{const db=q.result,t=db.transaction('clips','readwrite'),c=t.objectStore('clips').openCursor();
  c.onsuccess=()=>{const cur=c.result;if(!cur)return;if(cur.value.sid===sid&&!cur.value.pass)cur.delete();cur.continue()};t.oncomplete=()=>db.close()}};
// 開いた時の判定（録らない頁の 1 つの入口。作業の頁の「続き」と同じ決まり）: 同じ出所から 3 時間の内の回なら引き継ぐ（のこす から戻った時も
// 同じ出所なので引き継ぐ）。前の頁がこのサイトの頁でない所（直に開いた・外のリンク）か、回が無い時は作り始め（直に入った前の人の区切りを渡さない）
window.utsushiClipsStart=(sid)=>{let r=null,out=true;try{r=JSON.parse(sessionStorage.getItem('utsushi-run:'+sid)||'null')}catch(e){return}
  try{out=!document.referrer||new URL(document.referrer).origin!==location.origin}catch(e){}
  if(r&&!out&&Date.now()-r.at<__HOURS__*3600000)return;fresh(sid)};
// 戻る釦で読み直さずに戻った時（pageshow の persisted）は、前の頁が分からないので作り始め（録る頁の台本の作業の頁と同じ決まり）
window.utsushiClipsFresh=fresh;
// 今の回に区切りが置かれたか（置き場の台本の put が書く印）。手帖の「のこす」が、のこすの頁の確かめへ移るかを決める。IndexedDB は開かない
window.utsushiClipsMade=(sid)=>{try{const r=JSON.parse(sessionStorage.getItem('utsushi-run:'+sid)||'null');
  return !!r&&Date.now()-r.at<__HOURS__*3600000&&sessionStorage.getItem('utsushi-clips-made:'+sid)===r.id}catch(e){return false}};
})()</script>"""


def start_assets(sid=None):
    """録らない頁（手帖の作る頁・作りながら見る頁・録らない形の作業の頁）に置く小さな台本（数は 1 か所の値から入れる）。sid を渡すと、開いた時と
    戻る釦で読み直さずに戻った時に、作り始めかを見る
    （同じ出所から 3 時間の内なら引き継ぎ、直に開いた時は作り始め・統括の決め 11-08。手帖の手順の頁や作りながら見る頁を直に開いて
    のこす へ進んだ時に、前の人の回を引き継がないように）。"""
    on_open = (f"<script>(()=>{{const s={json.dumps(sid)};window.utsushiClipsStart&&utsushiClipsStart(s);"
               "addEventListener('pageshow',(e)=>{if(e.persisted&&window.utsushiClipsFresh)utsushiClipsFresh(s)})})()</script>")
    return START_SCRIPT.replace("__HOURS__", str(CLIP_HOURS)) + (on_open if sid else "")


def assets():
    """頁に 1 回だけ置く台本。数は 1 か所の値から入れる。"""
    return SCRIPT.replace("__HOURS__", str(CLIP_HOURS)).replace("__MAX__", str(CLIP_MAX)).replace("__CAM__", str(CAM_SECONDS)).replace("__WAIT__", str(OPEN_WAIT))


def notes():
    """録る所に添える 2 行（初めて録る時の 1 行と、端末の置き場の 1 行）。"""
    return f'<span class="clip-note">{esc(FIRST)}</span> <span class="clip-note">{esc(STORE)}</span>'
