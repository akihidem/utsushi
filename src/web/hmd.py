"""作業しながら見る頁の試作（HMD を想定。本人の指示 11-06「実装やってみて。作業する場面で使えるといいよね」）。

半年後に向けた試作で、main には入れない（試作の枝 try/hmd。凍結の中なので、試しのリンクでだけ見せる）。
狙い: 両手を作る事に空けたまま、手順の字と組み立ての 3D を目の前に出し、声で送る。

判断の芯:
- 組み立ては kumitate の部品をそのまま使う。送るのも kumitate の釦を押す形にして、絵と動きの作りを 2 つにしない。
- 手順の字は目線の高さ（画面の上）に大きく出す。3D はその下で、画面の高さに合わせて大きくする。押す所は大きく、間を空ける。
- 声で送る言葉は、手帖の声の操作と同じ「つぎ・もどる・もう一回」。聞くのは「はじめる」を押した後だけ。
  字は残さず、送る言葉を探すだけ（頁から外へ何も送らない）。頁を隠したら聞くのを止める。
- 声を字にできないブラウザでは、ボタンとキーボード（→ ← スペース。足の踏み板や指輪の送りは PageDown・PageUp を送る）で送る。
- 開いたら手順 1 の字を出し、刷った紙のまま止める（最初の「つぎ」で 1 手目が動く）。できあがりの「つぎ」では戻さない（下の 1 手ずつの節）。
- 暗い地にする。透けて見える HMD の画面では、明るい地が目に強いため（試作の読みで、機械では確かめていない）。
- 文は全部、試作の文（本人の確認の前）。採られた字（つぎ・もどる・もう一回・はじめる）だけは手帖と同じ。
- 本人の感想（11-06）「折る操作などが早く再生されどうしたらいいかわからない」: 1 つの手順の動きを「手」に分け、「つぎ」1 回で
  1 手だけ動かして止まる。手は、切る・折る・通す・置く・開く の 1 つ。折りは折り目 1 本ずつ（多い時は数本ずつ、1 つの動きで 6 回まで）。
  見る向きが変わるだけの動きは前後の手に付ける（「つぎ」を言ったのに何も起きない、を作らない）。折りは 1 本 2.2 秒から、切るは 2.2 倍。
  手順が替わった時は、字を読む間を置いてから動かす。「もどる」は 1 手もどり、「もう一回」は今の手をもう一度動かす。
  手順の中の手の数と済んだ数は、字でなく点で示す（新しい字を足さない）。最後の「つぎ」では、はじめに戻さない
  （言い間違いで組み上がった形が消えないように。はじめに戻すのは「はじめから」）。
  この進め方は、同じ感想から別の窓が作った枝 proto/hmd-work-view の物を移した（統括の決め 11-06: 枝は try/hmd に 1 つにする）。
- 声の約束（本人の決定 11-06・手帖の作り直しの案 2 と同じ）: 認識の字の全部が操作の言葉と一致した時だけ動く。
  「次の手順ってどうやるの」のような話し声では動かない。認識が付ける空白と句読点は除いてから比べる。読みの候補は 3 つまで見る。
- 作っている間、画面が消えないように頼む（断られても動く）。
- 本人の追加（11-06）「普通にiPhoneのカメラのオーバーレイでもできるようにしたら」: /toy/<玩具>/kasane で、後ろのカメラの映像の上に
  手順の字と 3D を重ねる。映像は機械の中だけで、送りも残しもしない（作りながら見る頁の約束と同じ字）。
- 映像の中の紙に 3D を合わせる（本人の言葉 11-07「自分が作った実物がオーバーレイする」）: カメラが付いたら、紙の 4 隅に置く印を 4 つ出す。
  印を指で紙の角へ動かすと、3D の舞台を 4 隅の囲みの中へ動かして縮める（映像の中の紙の上に 3D が来る）。印は数字だけで、新しい字を足さない。
  合わせ方は囲みに入れるだけで、紙の傾きに合わせて 3D を歪めない（歪めると、立った部品の形が崩れて見えるため。紙の座標の行列は
  エンジンの JSON の paper.place が来た後に使う）。合わせた位置は頁の中だけに持ち、残さない（頁は送らず、残さない決まり）。
  合わせた後は、頁の幅に合わせる縮尺（舞台に直に書く --hmd-zoom の zoom）を 1 に固定する。zoom は位置にも掛かり、囲みからずれるため。大きさは scale だけで決める。
"""
import json

from omochae import hypotheses

from . import kumitate, skin
from .skin import esc
from .tsukuru import PRIVACY

CAMERA, CAMERA_OFF = "カメラを出す", "カメラを止める"
NO_CAMERA = "この機械ではカメラを使えません。"
CAM_LINK = "カメラに重ねる（iPhone 向け）"

TOYS = ("NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R")  # 組み立ての書き方がある玩具（御来迎・虎）
TITLE = "作業しながら見る（試作）"
LISTEN, STOP = "はじめる", "止める"
NEXT, PREV, AGAIN = "つぎ", "もどる", "もう一回"
MIC_OFF = "声で送る: 止まっています"
MIC_ON = "聞いています: 「つぎ」「もどる」「もう一回」"
NO_VOICE = "このブラウザでは声で送れません。ボタンか、キーボードの → ← で送れます。"
BLOCKED = "マイクの許しがありません。ボタンか、キーボードの → ← で送れます。"
HOW = ("「はじめる」を押すと、ブラウザ（ネットを見るアプリ）が声を字にします。そのとき、声がブラウザの会社に送られることがあります。"
       "この頁は、送る言葉を探すだけです。声も字も残しません。")
TRIAL = "試作です。HMD（頭に付ける画面）で、両手を空けたまま見る形を試しています。"
# 声の言葉（言った字 → 操作）。認識は漢字で返す事が多いので、同じ意味の書き方を並べる。全部が一致した時だけ操作にする。
# つぎ・もどる・もう一回 は手帖の作り直しで採られた言葉（web/voice_words の表と同じ字。まだ main に無い）。はじめから・止める はこの試作の足し
WORDS = {**dict.fromkeys(("つぎ", "次", "つぎへ", "次へ", "すすむ", "進む", "できた", "出来た"), "next"),
         **dict.fromkeys(("もどる", "戻る", "まえに", "前に"), "prev"),
         **dict.fromkeys(("もう一回", "もういっかい", "もう1回", "もう１回", "もう一度", "もういちど"), "again"),
         **dict.fromkeys(("はじめから", "初めから", "最初から"), "top"),
         **dict.fromkeys(("とめて", "止めて", "とめる", "止める", "おわり", "終わり"), "stop")}
CLEAN = r"[\s。、．，！？!?…・]"  # 認識が付ける空白と句読点を除いてから比べる

STYLE = """
body.hmd-page{background:#14161a;color:#f3efe6}
.hmd-page .nav,.hmd-page .foot{display:none}
.hmd-page main{max-width:none;padding:0 max(16px,2vw)}
.hmd{display:flex;flex-direction:column;gap:14px;min-height:100vh;padding:14px 0 18px}
.hmd-top{display:flex;flex-wrap:wrap;gap:8px 22px;align-items:baseline;font-size:clamp(18px,1.6vw,28px);letter-spacing:.06em;color:#c9c2b4}
.hmd-top b{color:#f3efe6;font-weight:600}
#hmd-count{font-variant-numeric:tabular-nums}
.hmd-mic{margin-left:auto;padding:4px 14px;border:2px solid #5d6470;border-radius:999px}
.hmd-mic[data-state=on]{border-color:#7fd1a8;color:#bff0d6}
.hmd-mic[data-state=none],.hmd-mic[data-state=blocked]{border-color:#c98a6a;color:#f0c7b0}
#hmd-heard{min-width:6em;color:#ffe08a}
.hmd-k{display:grid;grid-template-columns:minmax(0,1fr) minmax(220px,300px);grid-template-areas:"text acts" "stage acts" "note acts";grid-template-rows:auto auto 1fr;gap:14px 26px;align-items:start}
.hmd-k .lead,.hmd-k .rt-acts{display:none}
.hmd-k #rt-text{grid-area:text;margin:0;min-height:2.6em;font-size:clamp(30px,3.6vw,64px);line-height:1.45;letter-spacing:.04em;color:#fffaf0}
.hmd-k .rt-stage{grid-area:stage;justify-self:center;margin:0;zoom:var(--hmd-zoom,1);border-color:#3a3f48;cursor:grab}
.hmd-k .meta{grid-area:note;color:#9a9385;font-size:14px}
.hmd-acts{grid-area:acts;display:flex;flex-direction:column;gap:12px}
/* 押す所は全部、頁を動かさずに見える所に置く（カメラの釦が画面の外に出て、iPhone で探せなかった。11-06 の撮った画面で見た） */
.hmd-acts button{margin:0;text-align:center;min-height:clamp(64px,8vh,100px);padding:0 .6em;font-size:clamp(22px,2.2vw,36px);letter-spacing:.12em;border-radius:14px;border:2px solid #6b7280;background:#22262d;color:#f3efe6;cursor:pointer}
.hmd-acts button:focus-visible{outline:4px solid #ffe08a;outline-offset:3px}
.hmd-acts #hmd-next{background:#2e5b46;border-color:#7fd1a8}
.hmd-acts #hmd-listen{background:#3b3550;border-color:#a99be0}
.hmd-acts #hmd-listen[aria-pressed=true]{background:#5a2f2f;border-color:#e09b9b}
.hmd-note{font-size:14px;line-height:1.8;color:#9a9385;max-width:60em}
.hmd-note a{color:#c9c2b4}
/* 縦に長い画面（iPhone を縦に持つ）: 手順の字・3D・押す所の順。字の欄は 3 行分の高さに決め、手順が替わっても 3D の大きさと置き場が
   動かないようにする。頭の帯は 1 行（聞き取った字の写しは、当たった釦が光るので縦では出さない）。押す所は「つぎ」を左の大きな 1 つ、
   ほかを右の 2 列 2 段にして、iPhone の見える高さ（390×664 ほど）でも 3D の下に全部入れる */
@media (max-aspect-ratio:1/1){.hmd{gap:8px;padding-top:8px}
.hmd-top{flex-wrap:nowrap;gap:10px;font-size:14px;letter-spacing:.02em}.hmd-top b,#hmd-count{white-space:nowrap}.hmd-mic{min-width:0;padding:2px 10px;border-width:1px;border-radius:12px;line-height:1.4}#hmd-heard{display:none}
.hmd-k{grid-template-columns:minmax(0,1fr);grid-template-areas:"text" "stage" "acts" "note";grid-template-rows:none;gap:8px}
.hmd-k #rt-text{font-size:clamp(19px,5.6vw,26px);min-height:4.35em}
.hmd-acts{display:grid;grid-template-columns:1.15fr 1fr 1fr;grid-template-rows:64px 64px;gap:10px}
.hmd-acts #hmd-next{grid-row:1/3;min-height:96px}
.hmd-acts button{min-height:64px;padding:0 .3em;font-size:clamp(16px,4.4vw,22px);letter-spacing:0;line-height:1.2}}
@media (prefers-reduced-motion:reduce){.hmd-acts button{transition:none}}
.hmd-list{display:flex;flex-wrap:wrap;gap:18px;margin:18px 0}
/* 手の印: 今の手順の中に手がいくつあり、いくつ済んだか（字にしない。1 手だけの手順では出さない） */
#hmd-dots{display:flex;gap:.55em;margin:0;min-height:.8em;font-size:clamp(16px,1.6vw,28px)}
#hmd-dots span{width:.8em;height:.8em;border-radius:50%;box-sizing:border-box;border:2px solid #6b7280}
#hmd-dots span.on{background:#ffe08a;border-color:#ffe08a}
/* 「つぎ」はいちばん押す所なので大きく。当たった言葉の札は少しの間光る */
.hmd-acts #hmd-next{min-height:96px}
.hmd-acts button[disabled]{opacity:.35;cursor:default}
.hmd-acts button.hit{background:#ffe08a;border-color:#ffe08a;color:#14161a}
body.hmd-cam{background:#000}
#hmd-cam{position:fixed;inset:0;width:100%;height:100%;object-fit:cover;z-index:-1;background:#000}
#hmd-quad{display:none;position:fixed;inset:0;z-index:3;pointer-events:none}body.quad-on #hmd-quad{display:block}
.hmd-corner{position:absolute;width:44px;height:44px;margin:-22px 0 0 -22px;border-radius:50%;border:2px solid #fffaf0;background:rgba(0,0,0,.35);color:#fffaf0;font-weight:600;font-size:16px;line-height:40px;font-family:inherit;text-align:center;pointer-events:auto;touch-action:none;cursor:grab;user-select:none}
body.quad-set .hmd-k .rt-stage{position:fixed;margin:0;z-index:2;transform-origin:0 0;zoom:1!important}
body.hmd-cam .hmd{position:relative}
body.hmd-cam .hmd-k #rt-text{background:rgba(0,0,0,.55);padding:8px 14px;border-radius:10px;text-shadow:0 1px 3px #000}
body.hmd-cam .hmd-top{background:rgba(0,0,0,.45);padding:6px 12px;border-radius:10px}
body.hmd-cam .hmd-k .rt-stage{--rt-table:transparent;background:rgba(20,22,26,.35);border-color:rgba(255,255,255,.25)}
body.hmd-cam .hmd-acts button{background:rgba(34,38,45,.8)}
body.hmd-cam .hmd-note{background:rgba(0,0,0,.55);padding:6px 10px;border-radius:8px}
.hmd-list a{display:inline-flex;align-items:center;min-height:96px;padding:0 34px;font-size:clamp(26px,2.6vw,42px);border:2px solid #7fd1a8;border-radius:14px;color:#f3efe6;text-decoration:none}
"""

SCRIPT = r"""<script>(()=>{
const $=id=>document.getElementById(id),body=document.body;
const next=$('rt-next'),prev=$('rt-prev'),text=$('rt-text'),count=$('rt-count'),stage=$('rt-stage');
const mic=$('hmd-mic'),heard=$('hmd-heard'),listen=$('hmd-listen'),shown=$('hmd-count'),dots=$('hmd-dots');
const T=JSON.parse($('hmd-words').textContent),P=window.kumitateParts;
if(!next||!prev)return;
const at=()=>Number(stage.dataset.at||0),done0=()=>!count.textContent;
const still=window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches;
const chip={next:$('hmd-next'),prev:$('hmd-prev'),again:$('hmd-again')};
const flash=op=>{const b=chip[op];if(!b)return;b.classList.add('hit');setTimeout(()=>b.classList.remove('hit'),500)};

// ---- 1 手ごとに止まる進め方（本人の感想 11-06「折る操作などが早く再生されどうしたらいいかわからない」）
// 1 つの手順の動きを「手」に分け、「つぎ」1 回で 1 手だけ動かして止まる。手は、切る・折る・通す・置く・開く の 1 つ。
// 折りは折り目 1 本ずつ止まる（多い時は数本ずつ、1 つの動きで 6 回まで）。見る向きが変わるだけの動きは、前後の手に付ける。
// 速さも遅くする（折りは 1 本 2.2 秒から。切る動きは 2.2 倍の長さ）。手順が替わった時は、字を読む間を置いてから動かす。
const moves=[];let done=0,token=0,onDone=null;
// 1 つの動きが終わった知らせ（kumitate が形を置き終えた後に出す）で、手の中の次の動きへつなぐ
document.addEventListener('kumitate-beat',e=>{const d=e.detail;if(d.beat===d.beats&&onDone){const f=onDone;onDone=null;f()}});
if(P){const F=P.F,TR=P.T;
const kind=(A,B)=>{const k={cut:!!B.cut,open:!!B.open,fold:[],scene:false,moved:false,dur:B.dur||0};
 for(const key in B.s){const a=A.s[key],b=B.s[key];if(!a){k.scene=true;continue}
  const rows=TR[key].rows;
  for(const i in rows)if(Math.abs((a.a[i]||0)-(b.a[i]||0))>.01)k.fold.push([key,i,B.o&&B.o[key]&&B.o[key][i]!==undefined?B.o[key][i]:-rows[i][5]]);
  if(a.m.join()!==b.m.join())k.moved=true}
 for(const key in A.s)if(!B.s[key])k.scene=true;
 if((A.paper||0)!==(B.paper||0))k.scene=true;
 k.rod=Object.keys(B.r).some(n=>!A.r[n]);
 k.tool=!!B.ruler&&String(A.ruler||'')!==String(B.ruler);
 k.act=k.cut||k.open||k.fold.length>0||k.rod||k.tool||(k.moved&&!k.scene&&k.dur>500);
 return k};
const slow=k=>k.cut?2.2:k.open?1.6:k.fold.length?Math.max(1.6,1800/(k.dur||1100)):k.rod?1.8:1.5;
// 途中の形: 折り目のうち、順の早い物（upto まで）だけを折った形。置き場と見る向きは、折り始めのまま
const mix=(A,B,upto,folds)=>{const Q={...A,s:{},o:B.o,dur:undefined,cut:undefined,open:undefined,cam:undefined};
 for(const key in A.s){const a=A.s[key];Q.s[key]={m:a.m,n:a.n,a:{...a.a}}}
 for(const f of folds)if(f[2]<=upto&&Q.s[f[0]])Q.s[f[0]].a[f[1]]=B.s[f[0]].a[f[1]];
 return Q};
let pose=F[0].q[0];
F.forEach((f,i)=>{const list=[];
 for(let j=i===0?1:0;j<f.q.length;j++){const A=pose,B=f.q[j];list.push({A,B,k:kind(A,B)});pose=B}
 if(!list.length)return;
 // 見る向きだけの動きなどは、前の手に付ける（短い動きと、後ろに手が無い時）か、次の手に付ける
 const groups=[];let pend=[];
 list.forEach((t,n)=>{if(t.k.act){groups.push({pre:pend,act:t,post:[]});pend=[]}
  else if(groups.length&&(t.k.dur<=500||!list.slice(n+1).some(x=>x.k.act)))groups[groups.length-1].post.push(t);
  else pend.push(t)});
 if(!groups.length)groups.push({pre:[],act:null,post:pend});else if(pend.length)groups[groups.length-1].post.push(...pend);
 for(const g of groups){const pre=g.pre.map(t=>[t.A,t.B,1.3]),post=g.post.map(t=>[t.A,t.B,1.3]);
  const ords=g.act?[...new Set(g.act.k.fold.map(x=>x[2]))].sort((x,y)=>x-y):[];
  const parts=[];
  if(ords.length>1){const size=Math.ceil(ords.length/6);let A=g.act.A,lo=-Infinity;
   for(let s=0;s<ords.length;s+=size){const lastOne=s+size>=ords.length,upto=ords[Math.min(s+size,ords.length)-1];
    const n=g.act.k.fold.filter(x=>x[2]>lo&&x[2]<=upto).length,B=lastOne?{...g.act.B}:mix(g.act.A,g.act.B,upto,g.act.k.fold);
    B.dur=Math.max(2200,1100*n);parts.push([A,B,1]);A=B;lo=upto}}
  else if(g.act)parts.push([g.act.A,g.act.B,slow(g.act.k)]);
  if(!parts.length){moves.push({i,chain:post,end:post[post.length-1][1]});continue}
  parts.forEach((part,x)=>{const chain=[...(x===0?pre:[]),part,...(x===parts.length-1?post:[])];moves.push({i,chain,end:chain[chain.length-1][1]})})}});
body.dataset.moves=moves.length}
const ok=P&&moves.length>0;
const halt=()=>{token++;onDone=null;P.stop()};
const endOf=k=>k<0?P.F[0].q[0]:moves[k].end;
// 1 手を動かす。動きの途中で次の言葉が来たら、その手の終わりの形にしてから次へ進む
const run=(k,read)=>{halt();const me=token,chain=moves[k].chain;P.rest(endOf(k-1));
 if(still){P.rest(moves[k].end);return}
 let n=0;const step=()=>{if(me!==token)return;if(n===chain.length){body.dataset.busy='';return}
  const c=chain[n++];window.kumitateSlow=c[2];onDone=step;P.play(c[0],[c[1]],0)};
 body.dataset.busy='1';setTimeout(step,read?900:250)};
// 今の手順の字と数と、手の印（点）を出す。手順は、最後に動かした手の手順（まだ動かしていない時は手順 1）
const paint=()=>{const i=moves[Math.max(done-1,0)].i;P.go(i);
 const n=moves.filter(m=>m.i===i).length,k=moves.slice(0,done).filter(m=>m.i===i).length;
 dots.textContent='';if(n>1)for(let x=0;x<n;x++){const d=document.createElement('span');if(x<k)d.className='on';dots.append(d)}
 chip.prev.disabled=done===0;chip.again.disabled=done===0;chip.next.disabled=done===moves.length;body.dataset.at=i;body.dataset.move=done;
 // 手順の字の行の数が替わると 3D の置き場が動くので、描いた後に大きさを測り直す
 requestAnimationFrame(()=>fit())};
const back=k=>{halt();done=k;P.rest(endOf(done-1));body.dataset.busy='';paint()};
// 操作。kumitate の口が無い時（節の作りが変わった時）は、前の進め方（kumitate の釦を押す・手順ごと）で動く
const act={
 next:()=>{if(!ok){next.click();return}
  if(done>=moves.length)return false;const was=done?moves[done-1].i:-1;done++;paint();run(done-1,moves[done-1].i!==was)},
 prev:()=>{if(!ok){if(!prev.disabled)prev.click();return}if(done===0)return false;back(done-1)},
 again:()=>{if(!ok){if(done0())return;if(prev.disabled){next.click();prev.click()}else{prev.click();next.click()}return}
  if(done===0)return false;run(done-1)},
 top:()=>{if(!ok){if(done0()){next.click();return}let n=0;while(!prev.disabled&&n++<99)prev.click();return}
  if(done===0)return false;back(0)},
 stop:()=>{stopListen();return false}};
const go=op=>{if(act[op]()!==false)flash(op)};
// 釦と鍵（足の踏み板・指輪の送りは PageDown・PageUp を送る）
for(const op in chip)chip[op].addEventListener('click',()=>go(op));
document.addEventListener('keydown',e=>{const el=e.target.closest?e.target:document.body;if(el.closest('input,textarea'))return;
 if(el.closest('button')&&(e.key===' '||e.key==='Enter'))return;if(e.altKey||e.ctrlKey||e.metaKey)return;
 const k={ArrowRight:'next',PageDown:'next',' ':'next',ArrowLeft:'prev',PageUp:'prev',r:'again',R:'again',Home:'top'}[e.key];
 if(k){e.preventDefault();go(k)}});
// 作業は手順 1 から始める。開いた時は刷った紙のまま止め、手順 1 の字を出す（kumitate の頁は、開くとできあがりの形を見せる作り）
if(ok){done=0;P.rest(endOf(-1));paint()}else if(done0())next.click();
// 数を頭の帯へ写す（kumitate の数をそのまま使う）
const copy=()=>{shown.textContent=count.textContent||T.done};copy();
new MutationObserver(copy).observe(count,{childList:true,characterData:true,subtree:true});
// 3D を、頁を動かさずに見える所いっぱいに大きくする。縦の画面では、3D の下に押す所が来るので、その高さを引く
const acts=document.querySelector('.hmd-acts');
const fit=()=>{const r=stage.getBoundingClientRect(),z=parseFloat(getComputedStyle(stage).zoom)||1,wide=innerWidth>innerHeight;
 const w=r.width/z,h=r.height/z,top=r.top+scrollY,avail=innerHeight-top-(wide?16:acts.offsetHeight+24);
 const col=stage.parentElement.clientWidth-(wide?340:0);
 stage.style.setProperty('--hmd-zoom',Math.max(.35,Math.min(2.4,avail/h,col/w)).toFixed(2));if(P)P.view()};
addEventListener('resize',fit);fit();
// 声。聞くのは「はじめる」の後だけ。認識の字の全部が操作の言葉と一致した時だけ動かし、ほかの字は捨てる（送らない・残さない）
const SR=window.SpeechRecognition||window.webkitSpeechRecognition,CLEAN=new RegExp(T.clean,'g');
let rec=null,on=false;
// 声の様子の字が替わると頭の帯の高さが変わるので、3D の大きさを測り直す
const say=(s,state)=>{mic.textContent=s;mic.dataset.state=state;fit()};
const hit=t=>T.words[t.replace(CLEAN,'')]||null;
function stopListen(){on=false;if(rec)try{rec.stop()}catch(_){}say(T.off,'off');listen.textContent=T.listen;listen.setAttribute('aria-pressed','false')}
function startListen(){
 if(!SR){say(T.none,'none');return}
 try{rec=new SR()}catch(_){say(T.none,'none');return}
 rec.lang='ja-JP';rec.continuous=false;rec.interimResults=false;rec.maxAlternatives=3;
 rec.onresult=e=>{if(!on)return;const r=e.results[e.results.length-1];
  for(let i=0;i<r.length;i++){const k=hit(r[i].transcript);if(k){heard.textContent='「'+r[i].transcript.trim().slice(-10)+'」';go(k);return}}};
 rec.onerror=e=>{if(['not-allowed','service-not-allowed','audio-capture'].includes(e.error)){on=false;say(T.blocked,'blocked');listen.textContent=T.listen;listen.setAttribute('aria-pressed','false')}};
 // 1 回の聞き取りが終わるたびに聞き直す（聞いている間と、頁が見えている間だけ）
 rec.onend=()=>{if(on&&!document.hidden){try{rec.start()}catch(_){}}};
 try{rec.start()}catch(_){return}
 on=true;say(T.on,'on');listen.textContent=T.stop;listen.setAttribute('aria-pressed','true')}
listen.addEventListener('click',()=>{on?stopListen():startListen();wake()});
if(!SR)say(T.none,'none');
// 作っている間、画面が消えないように頼む（断られても動く）
const wake=()=>{try{if(navigator.wakeLock&&!document.hidden)navigator.wakeLock.request('screen').catch(()=>{})}catch(_){}};
wake();
const cam=$('hmd-cam'),camBtn=$('hmd-camera'),camNote=$('hmd-cam-note');
if(cam&&camBtn){let tracks=null;
 // 紙の 4 隅の印（左上・右上・右下・左下の順）。動かしたら、3D の舞台を 4 隅の囲みの中へ動かして縮める。位置は頁の中だけに持つ
 const quad=$('hmd-quad'),C=quad?[...quad.querySelectorAll('.hmd-corner')]:[],Q=[];
 const fit=()=>{if(Q.length<4)return;const xs=Q.map(q=>q[0]),ys=Q.map(q=>q[1]),x0=Math.min(...xs),y0=Math.min(...ys),bw=Math.max(...xs)-x0,bh=Math.max(...ys)-y0;
  body.classList.add('quad-set');stage.style.transform='';const sw=stage.offsetWidth||1,sh=stage.offsetHeight||1,z=Math.max(.2,Math.min(bw/sw,bh/sh));
  stage.style.left=(x0+(bw-sw*z)/2)+'px';stage.style.top=(y0+(bh-sh*z)/2)+'px';stage.style.transform='scale('+z+')'};
 const put=()=>{C.forEach((c,i)=>{c.style.left=Q[i][0]+'px';c.style.top=Q[i][1]+'px'});fit()};
 const home=()=>{const w=innerWidth,h=innerHeight,bw=Math.min(w*.7,h*.45),bh=bw*1.414,x=(w-bw)/2,y=Math.max(30,(h-bh)/2);Q.length=0;Q.push([x,y],[x+bw,y],[x+bw,y+bh],[x,y+bh]);put()};
 C.forEach((c,i)=>{c.addEventListener('pointerdown',e=>{e.preventDefault();try{c.setPointerCapture(e.pointerId)}catch(_){}c.dataset.drag='1'});
  c.addEventListener('pointermove',e=>{if(!c.dataset.drag)return;Q[i]=[Math.max(0,Math.min(innerWidth,e.clientX)),Math.max(0,Math.min(innerHeight,e.clientY))];put()});
  const up=()=>{delete c.dataset.drag};c.addEventListener('pointerup',up);c.addEventListener('pointercancel',up)});
 const quadOn=()=>{if(!quad)return;body.classList.add('quad-on');home()};
 const quadOff=()=>{body.classList.remove('quad-on','quad-set');stage.style.left=stage.style.top=stage.style.transform=''};
 const off=()=>{if(tracks)tracks.forEach(x=>x.stop());tracks=null;cam.srcObject=null;document.body.classList.remove('cam-on');camBtn.textContent=T.camera;quadOff()};
 if(!navigator.mediaDevices||!navigator.mediaDevices.getUserMedia){camBtn.hidden=true;camNote.textContent=T.nocamera}
 camBtn.addEventListener('click',async()=>{if(tracks){off();return}
  try{const s=await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'}},audio:false});tracks=s.getTracks();cam.srcObject=s;
   document.body.classList.add('cam-on');camBtn.textContent=T.cameraoff;quadOn()}catch(_){camNote.textContent=T.nocamera}});
 addEventListener('pagehide',off);document.addEventListener('visibilitychange',()=>{if(document.hidden)off()})}
// 隠れたら聞くのを止め、見えたら聞いていた時だけ戻す。頁を離れたら止める（手帖の作り直しと同じ）
document.addEventListener('visibilitychange',()=>{if(document.hidden){if(rec)try{rec.stop()}catch(_){}}else{if(on&&rec)try{rec.start()}catch(_){}wake()}});
addEventListener('pagehide',()=>{if(on)stopListen()});
})()</script>"""


def available(sid):
    return sid in TOYS and kumitate.available(sid)


def page(sid, look="tenji", cam=False):
    """1 つの玩具の、作業しながら見る頁。帯と足は出さない（見る所を手順と 3D だけにする）。
    cam=True はカメラに重ねる頁（後ろのカメラの映像の上に手順と 3D。/toy/<印>/kasane）。cam=False は HMD 向け（/toy/<印>/kasane/hmd）。
    道は玩具ごとに置く: 作る口は手帖 1 つの決まり（地図の 1）なので、玩具を選ぶ頁は持たず、選びなおす時は えらぶ（/toys）へ戻す。"""
    toy = hypotheses.load(sid)["toy"]
    words = {"words": WORDS, "on": MIC_ON, "off": MIC_OFF, "none": NO_VOICE, "blocked": BLOCKED, "listen": LISTEN, "stop": STOP, "done": kumitate.DONE,
             "clean": CLEAN, "camera": CAMERA, "cameraoff": CAMERA_OFF, "nocamera": NO_CAMERA}
    # 紙の 4 隅の印は数字だけ（新しい字を足さない）。読み上げには出さない（指で動かす印で、押す所ではない）
    corners = "".join(f'<span class="hmd-corner" data-i="{i}">{i + 1}</span>' for i in range(4))
    camera = (f'<video id="hmd-cam" playsinline muted autoplay></video><div id="hmd-quad" aria-hidden="true">{corners}</div>' if cam else "")
    camera_btn = (f'<button type="button" id="hmd-camera">{esc(CAMERA)}</button>' if cam else "")
    camera_note = (f'<span id="hmd-cam-note">{esc(PRIVACY)}</span> ' if cam else "")
    params = json.dumps(hypotheses.sheet_of(sid).get("params") or {}, sort_keys=True, ensure_ascii=False)
    body = (f'<div class="hmd"><div class="hmd-top"><b>{esc(toy)}</b><span id="hmd-count"></span><span id="hmd-heard" aria-live="polite"></span>'
            f'<span class="hmd-mic" id="hmd-mic" data-state="off" aria-live="polite">{esc(MIC_OFF)}</span></div>'
            f'<p id="hmd-dots" aria-hidden="true"></p>'
            f'<div class="hmd-k">{kumitate._block_html(sid, params)}'
            f'<div class="hmd-acts"><button type="button" id="hmd-next">{esc(NEXT)}</button><button type="button" id="hmd-prev">{esc(PREV)}</button>'
            f'<button type="button" id="hmd-again">{esc(AGAIN)}</button><button type="button" id="hmd-listen" aria-pressed="false">{esc(LISTEN)}</button>{camera_btn}</div></div>'
            f'<p class="hmd-note">{camera_note}{esc(HOW)} {esc(TRIAL)} <a href="/toys">玩具を選びなおす</a></p></div>{camera}'
            f'<script type="application/json" id="hmd-words">{json.dumps(words, ensure_ascii=False)}</script>{SCRIPT}')
    return skin.shell(f"{toy}: {TITLE}", body, look, path=f"/toy/{sid}/kasane" + ("" if cam else "/hmd"), extra_style=STYLE,
                      body_class="hmd-page hmd-cam" if cam else "hmd-page")

