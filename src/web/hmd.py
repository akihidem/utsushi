"""作業しながら見る頁の試作（HMD を想定。本人の指示 11-06「実装やってみて。作業する場面で使えるといいよね」）。

半年後に向けた試作で、main には入れない（試作の枝 try/hmd。凍結の中なので、試しのリンクでだけ見せる）。
狙い: 両手を作る事に空けたまま、手順の字と組み立ての 3D を目の前に出し、声で送る。

判断の芯:
- 組み立ては kumitate の部品をそのまま使う。送るのも kumitate の釦を押す形にして、絵と動きの作りを 2 つにしない。
- 手順の字は目線の高さ（画面の上）に大きく出す。3D はその下で、画面の高さに合わせて大きくする。押す所は大きく、間を空ける。
- 声で送る言葉は、手帖の声の操作と同じ「つぎ・もどる・もう一回」。聞くのは「はじめる」を押した後だけ。
  字は残さず、送る言葉を探すだけ（頁から外へ何も送らない）。頁を隠したら聞くのを止める。
- 声を字にできないブラウザでは、ボタンとキーボード（→ ← スペース。足の踏み板や指輪の送りは PageDown・PageUp を送る）で送る。
- 開いたら手順 1 から始める。できあがりで「つぎ」を言うと、はじめから組み立て直す。
- 暗い地にする。透けて見える HMD の画面では、明るい地が目に強いため（試作の読みで、機械では確かめていない）。
- 文は全部、試作の文（本人の確認の前）。採られた字（つぎ・もどる・もう一回・はじめる）だけは手帖と同じ。
"""
import json

from omochae import hypotheses

from . import kumitate, skin
from .skin import esc

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
# 声の言葉。聞き取りの字は漢字にもなるので、同じ意味の書き方を並べる。
WORDS = (("next", "つぎ|次|すすむ|進む"), ("prev", "もどる|戻る|まえに|前に"), ("again", "もう一回|もういっかい|もう1回|もう一度|もういちど"),
         ("top", "はじめから|初めから|最初から"), ("stop", "とめて|止めて|とめる|止める|おわり|終わり"))

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
.hmd-k{display:grid;grid-template-columns:minmax(0,1fr) minmax(220px,300px);grid-template-areas:"text text" "stage acts" "note acts";gap:14px 26px;align-items:start}
.hmd-k .lead,.hmd-k .rt-acts{display:none}
.hmd-k #rt-text{grid-area:text;margin:0;min-height:2.6em;font-size:clamp(30px,3.6vw,64px);line-height:1.45;letter-spacing:.04em;color:#fffaf0}
.hmd-k .rt-stage{grid-area:stage;justify-self:center;margin:0;zoom:var(--hmd-zoom,1);border-color:#3a3f48;cursor:grab}
.hmd-k .meta{grid-area:note;color:#9a9385;font-size:14px}
.hmd-acts{grid-area:acts;display:flex;flex-direction:column;gap:16px}
.hmd-acts button{min-height:clamp(64px,9vh,110px);font-size:clamp(24px,2.4vw,40px);letter-spacing:.12em;border-radius:14px;border:2px solid #6b7280;background:#22262d;color:#f3efe6;cursor:pointer}
.hmd-acts button:focus-visible{outline:4px solid #ffe08a;outline-offset:3px}
.hmd-acts #hmd-next{background:#2e5b46;border-color:#7fd1a8}
.hmd-acts #hmd-listen{background:#3b3550;border-color:#a99be0}
.hmd-acts #hmd-listen[aria-pressed=true]{background:#5a2f2f;border-color:#e09b9b}
.hmd-note{font-size:14px;line-height:1.8;color:#9a9385;max-width:60em}
.hmd-note a{color:#c9c2b4}
@media (max-aspect-ratio:1/1){.hmd-k{grid-template-columns:minmax(0,1fr);grid-template-areas:"text" "stage" "acts" "note"}.hmd-acts{flex-direction:row;flex-wrap:wrap}.hmd-acts button{flex:1 1 40%}}
@media (prefers-reduced-motion:reduce){.hmd-acts button{transition:none}}
.hmd-list{display:flex;flex-wrap:wrap;gap:18px;margin:18px 0}
.hmd-list a{display:inline-flex;align-items:center;min-height:96px;padding:0 34px;font-size:clamp(26px,2.6vw,42px);border:2px solid #7fd1a8;border-radius:14px;color:#f3efe6;text-decoration:none}
"""

SCRIPT = r"""<script>(()=>{
const $=id=>document.getElementById(id);
const next=$('rt-next'),prev=$('rt-prev'),text=$('rt-text'),count=$('rt-count'),stage=$('rt-stage');
const mic=$('hmd-mic'),heard=$('hmd-heard'),listen=$('hmd-listen'),shown=$('hmd-count');
const T=JSON.parse($('hmd-words').textContent);
if(!next||!prev)return;
const at=()=>Number(stage.dataset.at||0),done=()=>!count.textContent;
const act={
 next:()=>next.click(),
 prev:()=>{if(!prev.disabled)prev.click()},
 again:()=>{if(done())return;if(prev.disabled){next.click();prev.click()}else{prev.click();next.click()}},
 top:()=>{if(done()){next.click();return}let n=0;while(!prev.disabled&&n++<99)prev.click()},
 stop:()=>stopListen()};
// 釦と鍵（足の踏み板・指輪の送りは PageDown・PageUp を送る）
$('hmd-next').addEventListener('click',()=>act.next());
$('hmd-prev').addEventListener('click',()=>act.prev());
$('hmd-again').addEventListener('click',()=>act.again());
document.addEventListener('keydown',e=>{const el=e.target.closest?e.target:document.body;if(el.closest('input,textarea'))return;
 if(el.closest('button')&&(e.key===' '||e.key==='Enter'))return;
 const k={ArrowRight:'next',PageDown:'next',' ':'next',ArrowLeft:'prev',PageUp:'prev',r:'again',R:'again',Home:'top'}[e.key];
 if(k){e.preventDefault();act[k]()}});
// 作業は手順 1 から始める（kumitate の頁は、開くとできあがりの形を見せる作り）
if(done())next.click();
// 数を頭の帯へ写す（kumitate の数をそのまま使う）
const copy=()=>{shown.textContent=count.textContent||T.done};copy();
new MutationObserver(copy).observe(count,{childList:true,characterData:true,subtree:true});
// 3D を画面の高さに合わせて大きくする
const fit=()=>{const r=stage.getBoundingClientRect(),z=parseFloat(getComputedStyle(stage).zoom)||1;
 const w=r.width/z,h=r.height/z,avail=innerHeight-stage.parentElement.getBoundingClientRect().top-text.offsetHeight-60;
 const col=stage.parentElement.clientWidth-(innerWidth>innerHeight?340:0);
 stage.style.setProperty('--hmd-zoom',Math.max(.6,Math.min(2.4,avail/h,col/w)).toFixed(2))};
addEventListener('resize',fit);fit();
// 声。聞くのは「はじめる」の後だけ。字は残さない。
const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
const RE=T.words.map(([k,p])=>[k,new RegExp(p)]);
let rec=null,on=false,last=0,firedAt=-1;
const say=(s,state)=>{mic.textContent=s;mic.dataset.state=state};
const hit=t=>{for(const [k,re] of RE)if(re.test(t))return k;return null};
function stopListen(){on=false;if(rec)try{rec.stop()}catch(_){}say(T.off,'off');listen.textContent=T.listen;listen.setAttribute('aria-pressed','false')}
function startListen(){
 if(!SR){say(T.none,'none');return}
 rec=new SR();rec.lang='ja-JP';rec.continuous=true;rec.interimResults=true;firedAt=-1;
 rec.onresult=e=>{if(!on)return;for(let i=e.resultIndex;i<e.results.length;i++){if(i<=firedAt)continue;const t=e.results[i][0].transcript,k=hit(t);
  if(!k)continue;const now=Date.now();firedAt=i;if(now-last<900)return;last=now;heard.textContent='「'+t.trim().slice(-10)+'」';act[k]();return}};
 rec.onerror=e=>{if(e.error==='not-allowed'||e.error==='service-not-allowed'){on=false;say(T.blocked,'blocked');listen.textContent=T.listen;listen.setAttribute('aria-pressed','false')}};
 rec.onend=()=>{if(on){firedAt=-1;try{rec.start()}catch(_){}}};
 try{rec.start()}catch(_){return}
 on=true;say(T.on,'on');listen.textContent=T.stop;listen.setAttribute('aria-pressed','true')}
listen.addEventListener('click',()=>on?stopListen():startListen());
if(!SR)say(T.none,'none');
document.addEventListener('visibilitychange',()=>{if(document.hidden&&on)stopListen()});
})()</script>"""


def available(sid):
    return sid in TOYS and kumitate.available(sid)


def page(sid, look="tenji", base="/hmd"):
    """1 つの玩具の、作業しながら見る頁。帯と足は出さない（見る所を手順と 3D だけにする）。"""
    toy = hypotheses.load(sid)["toy"]
    words = {"words": WORDS, "on": MIC_ON, "off": MIC_OFF, "none": NO_VOICE, "blocked": BLOCKED, "listen": LISTEN, "stop": STOP, "done": kumitate.DONE}
    params = json.dumps(hypotheses.sheet_of(sid).get("params") or {}, sort_keys=True, ensure_ascii=False)
    body = (f'<div class="hmd"><div class="hmd-top"><b>{esc(toy)}</b><span id="hmd-count"></span><span id="hmd-heard" aria-live="polite"></span>'
            f'<span class="hmd-mic" id="hmd-mic" data-state="off" aria-live="polite">{esc(MIC_OFF)}</span></div>'
            f'<div class="hmd-k">{kumitate._block_html(sid, params)}'
            f'<div class="hmd-acts"><button type="button" id="hmd-next">{esc(NEXT)}</button><button type="button" id="hmd-prev">{esc(PREV)}</button>'
            f'<button type="button" id="hmd-again">{esc(AGAIN)}</button><button type="button" id="hmd-listen" aria-pressed="false">{esc(LISTEN)}</button></div></div>'
            f'<p class="hmd-note">{esc(HOW)} {esc(TRIAL)} <a href="{esc(base)}">玩具を選びなおす</a></p></div>'
            f'<script type="application/json" id="hmd-words">{json.dumps(words, ensure_ascii=False)}</script>{SCRIPT}')
    return skin.shell(f"{toy}: {TITLE}", body, look, path=f"{base}/{sid}", extra_style=STYLE, body_class="hmd-page")


def index(look="tenji", base="/hmd"):
    links = "".join(f'<a href="{esc(base)}/{esc(sid)}">{esc(hypotheses.load(sid)["toy"])}</a>' for sid in TOYS if available(sid))
    body = (f'<div class="hmd"><h1>{esc(TITLE)}</h1><p class="hmd-note">{esc(TRIAL)}</p><div class="hmd-list">{links}</div>'
            f'<p class="hmd-note">{esc(HOW)}</p></div>')
    return skin.shell(TITLE, body, look, path=base, extra_style=STYLE, body_class="hmd-page")
