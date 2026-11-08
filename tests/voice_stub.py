"""頭なしの Chrome で「声を録る」を歩く試験（tests/test_voice_pause.py・tests/test_voice_walk.py）の見本。試験ではない（名が test_ で始まらない）。

なぜ見本が要るか: 頭なしの Chrome は時間を進める形（--virtual-time-budget）で回すと、IndexedDB の開く・置くが返ってこない（11-08 に手元で確かめた:
indexedDB.open の onsuccess が来ないまま頁が書き出された）。録りの置き場（web.clips）は IndexedDB に置くので、そのままでは置いた後の動き
（voiceStop が置き終えてから返る・のこすの頁に並ぶ・承認で送る）を歩けない。そこで、置き場の台本が使う形だけを持つ IndexedDB の見本を、
頁を入れる外の頁（WRAP）に 1 つ置き、iframe の頁から借りる。外の頁に置くのは、iframe が頁を移っても（作りながら見る頁 → のこすの頁）中身が残るため
（本物の IndexedDB が出所ごとに残るのと同じ）。マイク（getUserMedia）と録り（MediaRecorder）も見本にする（マイクは使わない）。
見本が持つのは、置き場の台本が呼ぶ形だけ: open・transaction・objectStore・put・delete・getAll・openCursor（update・delete・continue）。
音声認識（SpeechRecognition）は、作られたら __sr を数える見本にする（作られないはず）。
"""
import re

# 外の頁に置く IndexedDB の見本。区切りの blob は外の頁の Blob に写す（iframe の頁が移っても読めるように）
FAKE_IDB = r"""<script>
window.__idb=(()=>{const data=new Map(),later=f=>setTimeout(f,0);let made=false;
 const req=()=>({result:undefined,error:null,onsuccess:null,onerror:null});
 const ok=q=>q.onsuccess&&q.onsuccess({target:q});
 const copy=v=>{const c={...v};if(c.blob)c.blob=new Blob([c.blob],{type:c.blob.type});return c};
 const tx=()=>{const t={oncomplete:null,onerror:null,n:0,done:false};
  t.track=fn=>{t.n++;later(()=>{fn();t.n--;later(()=>{if(!t.n&&!t.done){t.done=true;t.oncomplete&&t.oncomplete()}})})};
  t.objectStore=()=>({
   put(v){const q=req();t.track(()=>{data.set(v.id,copy(v));q.result=v.id;ok(q)});return q},
   delete(k){const q=req();t.track(()=>{data.delete(k);ok(q)});return q},
   getAll(){const q=req();t.track(()=>{q.result=[...data.values()].map(v=>({...v}));ok(q)});return q},
   openCursor(){const q=req(),keys=[...data.keys()];let i=0;
    const step=()=>{while(i<keys.length&&!data.has(keys[i]))i++;if(i>=keys.length){q.result=null;ok(q);return}
     const k=keys[i++];q.result={value:{...data.get(k)},update(v){data.set(k,copy(v))},delete(){data.delete(k)},continue(){t.track(step)}};ok(q)};
    t.track(step);return q}});
  return t};
 return {open(){const q=req();later(()=>{q.result={transaction:()=>tx(),createObjectStore(){},close(){}};
   if(!made){made=true;q.onupgradeneeded&&q.onupgradeneeded({target:q})}ok(q)});return q},data}})();
window.__media=[];window.__fetches=[];
</script>"""

# 頁の頭（頁の台本より先）に置く見本。__chunk は 1 秒ごとの録りの大きさ（大きさの止めを歩く時に替える）
PAGE_STUB = r"""<script>
window.__log=[];window.__chunk=1000;window.__sr=0;
if(parent!==window&&parent.__idb)Object.defineProperty(window,'indexedDB',{value:parent.__idb,configurable:true});
window.SpeechRecognition=window.webkitSpeechRecognition=function(){window.__sr++;this.start=()=>{};this.stop=()=>{}};
// 読み上げは残す（音声認識とは別の物）。読み上げたかだけを控える
if(window.speechSynthesis){speechSynthesis.speak=(u)=>{__log.push('speak');setTimeout(()=>u.onend&&u.onend(),1)};speechSynthesis.cancel=()=>{}}
Object.defineProperty(navigator,'mediaDevices',{configurable:true,value:{getUserMedia:async(c)=>{__log.push('gum:'+(c&&c.audio?'audio':'video'));return {getTracks:()=>[{stop(){}}]}}}});
window.MediaRecorder=class{constructor(s,o){this.state='inactive';this.mimeType='audio/webm';window.__mr=this}
 start(ts){this.state='recording';__log.push('rec:start:'+ts);this.t0=performance.now();this.iv=setInterval(()=>{this.ondataavailable&&this.ondataavailable({data:new Blob([new Uint8Array(window.__chunk)])})},ts||1000)}
 stop(){if(this.state==='inactive')return;this.state='inactive';clearInterval(this.iv);__log.push('rec:stop');window.__recMs=Math.round(performance.now()-this.t0);
  setTimeout(()=>{this.ondataavailable&&this.ondataavailable({data:new Blob([new Uint8Array(10)])});this.onstop&&this.onstop()},0)}};
// 区切りの送り（/record/<番号>/media に X-Utsushi-Clip の見出し）だけを外の頁に控えて、本物のサーバへは送らない（声を字にする道具を回さないため）。
// ほかの送りは本物のサーバへ通し、何をいつ送ったかと、その時の置き場の数を控える
const real=window.fetch.bind(window);
window.fetch=(url,o)=>{const u=String(url),h=(o&&o.headers)||{},n=parent.__idb?parent.__idb.data.size:-1;
 (parent.__fetches||[]).push({url:u.split('?')[0],clips:n});__log.push('fetch:'+u.split('?')[0].split('/').pop());
 if(/\/record\/[^/]+\/media$/.test(u)&&h['X-Utsushi-Clip']){parent.__media.push({clip:h['X-Utsushi-Clip'],size:o.body&&o.body.size,step:h['X-Utsushi-Step']||null});
  return Promise.resolve(new Response('t1.mka',{status:201}))}
 return real(url,o)};
</script>"""


def inject(body, script):
    """頁の頭（<html> の直後。<head> の無い頁があるため）に見本を置き、頁の終わりに歩く台本を足す。"""
    return re.sub(r"<html[^>]*>", lambda h: h.group(0) + PAGE_STUB, body, count=1) + script
