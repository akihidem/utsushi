"""作りながら見る（観察 A の試作）。本人の案の具体化（2026-11-05 朝、窓口を通して届いた）:
「生徒の一人一台端末や iPhone を机の端に置いて、端末のカメラで生徒の上半身を写す形に。間に手と動画と紙があり、作成の様子を見れるようにする」。

何をする頁か: 端末を机の端に立て、画面に手本（今の手順の文と、手順の紙の絵）と返事（聞いた事の答え）を出す。隅の小さな鏡に、
自分と机の上（手と紙）が映る。進み方は大きな札（次の手順へ・止まった。最後の手順はできた）で残す。設計は docs/process/research/30 の「観察の置き方」。

判断の芯:
- **一番浅い段（観察 A）だけを作る。映像は端末の中だけ。** 鏡は <video> に流すだけで、画素を取り出さない・録らない・送らない。
  子どもの顔や部屋が映る物を扱わない線（CLAUDE.md）を変えずにできる範囲がここまで。机の上だけの 1 枚を残す段（B）や続けて撮る段（C）は、
  本人が線を決めてからの物で、この頁には入れない。試験（tests/test_tsukuru.py）で、その種の JS が頁に無い事を固定する。
- 残るのは字と数だけ: 札を押した事（手順の番号と、進んだ・戻った・止まった・できた。omochae.making_log.add_step）と、聞く口の質問の文（既にある口）。
  どの手順で止まるかを数えて、手順の紙と案内を直す材料にする（research/29 の 1）。数は作る側の頁（/loop/<印>）にだけ出す。
- 手順の文は、手順の紙が刷る文と同じ物（雛形の steps）をそのまま出す。ここで文を作らない（紙と画面で言う事が違うと、どちらを信じるか迷うため）。
  仮説の名前と動かし方は出さない（字と版だけ。手帖と同じ範囲）。
- 鏡は「鏡を出す」を押した時だけカメラを求め、頁を離れる時に止める。使わなくても全部できる。
- 机の端に置いて少し離れて読むので、字と札は大きく、書体はゴシック（手帖と同じ理由）。縦置きは 1 列、横置きは手本と札を左右に分ける。
- 組み上がりの札を祝う演出は入れない（紙で動くかはこの後に確かめる事で、組み上がりは成績ではない。J-025）。押すと記録の欄へ送る。
- 組み上がりの札は最後の手順だけに出し、一番大きい札にする（#321）。前は小さい札が全部の手順にあり、「この手順ができた」と読めて、手順 1 で押した人も
  組み上がりに数えられ、作る様子の集計がずれた。最後の手順の一番大きい札は「次の手順へ」のままで、押しても何も起きなかった。
- JS が無くても札は働く（フォームの送信で手順が進む）。JS がある時は、頁を読み直さずに進める（読み直すと鏡が止まるため）。
  組み上がりの札は頁を移るので読み直しを避ける理由が無く、JS がある時もフォームのまま送る（JS の有無で道を分けない）。
- 「ここで止まった」から、その段のまま聞ける（Issue #118・U-44 の「聞く」）。札を押すと止まった段が残り、同じ画面の聞く口が
  「手順 N で止まった所を聞く」に変わって、字の欄に手が届き、声の釦が出る。聞く口には今の手順の番号（step）を添えて送る。
  なぜ添えるか: どの段でどんな問いが出るかを束ねて、手順の紙の直しと先回りの答えの材料にするため（U-45）。
- 声で聞く口は手帖と同じ作り（ブラウザの音声認識。使えない画面では釦を隠す）。**声そのものは録らず、送らない。** 送るのは字になった問いだけ。
  マイクを getUserMedia で開く code と録る code は書かない（鏡は audio:false のまま）。試験で固定する。
- 出来事（札と問い）には、その場限りの無作為の印（who）を添える。sessionStorage に持つ英数字 10 桁で、タブを閉じると消える。
  なぜ持つか: 「同じ段で 3 人以上止まった」を数えるには、同じ人の押し直しを 1 人と数える印が要る（Issue #119 の「人は、その場限りの
  無作為の印で数える」）。cookie にしない・名前や機器と結び付けない・次に開いた時は別の印になる、で人を追える物にしない。
"""
from omochae import hypotheses, instructions, loop, making_log
from omochae.compose import TEMPLATES

from . import skin

# 映像の約束。かざして選ぶ頁（U-44）を外した後も、作りながら見る頁の鏡に同じ約束を残す（決まり「子どもの写真・声は扱わない」）。
PRIVACY = "映像はこの端末の中だけで、送りも残しもしません。"
CAMERA_PURPOSE = "カメラで見るのは、不完全な型紙を人が工夫で乗り切る所です。人の出来を見るためではありません。"
from .play_server import esc, out_dir, printed_versions

NOTICE = making_log.ASK_NOTICE + making_log.ASK_NAME_VOICE  # 断りの文は making_log に 1 か所（本人の決定 11-05）
# 最後の手順の札と、押した後に記録の欄の頭で出す案内（#321）。案内は play_server が記録の欄へ渡す。
DONE_LABEL = "できた"
DONE_NOTE = "組み上がった事を残しました。動かしてみて、玩具の頁で記録を残します。"

STYLE = """
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--fg);font-family:"Noto Sans CJK JP","Noto Sans JP","Hiragino Sans","Yu Gothic",sans-serif;line-height:1.6;font-size:18px}
a{color:var(--accent)}
.stage{min-height:100svh;display:grid;grid-template-columns:minmax(0,1fr);grid-template-rows:auto;align-content:start}
.top{grid-column:1/-1;display:flex;justify-content:space-between;flex-wrap:wrap;gap:6px 12px;margin:0;padding:10px 16px;font-size:14px;border-bottom:1px solid var(--rule)}
.top a{text-decoration:none}
.tehon{padding:14px 16px;min-width:0}
.num{margin:0 0 6px;font-size:16px;color:var(--mute);letter-spacing:.1em}
.num b{font-size:30px;color:var(--fg);letter-spacing:0}
#steps{margin:0 0 12px;padding-left:1.6em;font-size:18px}
#steps li.on{font-weight:600}
/* JS がある時は今の手順だけを大きく出す（離れて読むため）。無い時は全部の手順を並べ、今の手順を太くする。 */
.js #steps{list-style:none;padding:0}
.js #steps li{display:none}
.js #steps li.on{display:block;font-size:clamp(24px,3.6vw,44px);line-height:1.45}
.sheet{display:block;width:100%;max-height:52svh;object-fit:contain;object-position:left top;background:#fff;border:1px solid var(--frame)}
.side{padding:14px 16px;display:grid;gap:14px;align-content:start;min-width:0;border-top:1px solid var(--rule)}
/* 札は手が紙でふさがっていても押せる大きさ。並びは進む順（次へか組み上がり・止まった・戻る）。色で良し悪しを付けない。 */
.tiles{display:grid;grid-template-columns:minmax(0,1fr);gap:10px;margin:0}
.tiles button{font:inherit;font-size:clamp(17px,4.8vw,22px);min-height:72px;border:2px solid var(--accent);background:var(--paper);color:var(--fg);cursor:pointer;padding:8px 10px}
.tiles .go{background:var(--accent);color:var(--onaccent);font-size:26px;min-height:84px}
.tiles .small{min-height:44px;font-size:15px;border:1px solid var(--frame);color:var(--mute)}
.msg{margin:0;padding:10px 12px;border:1px solid var(--accent);font-size:17px}
.henji form{display:flex;gap:8px}
.henji input{flex:1;min-width:0;font:inherit;font-size:18px;padding:10px;border:1px solid var(--frame);background:var(--field);color:var(--fg)}
.henji form button{font:inherit;font-size:18px;padding:10px 18px;border:1px solid var(--accent);background:transparent;color:var(--accent);cursor:pointer}
.answer{min-height:2.2em;font-size:20px;margin-top:8px}
/* 聞く口の見出し。「ここで止まった」を押すと「手順 N で止まった所を聞く」に変わり、枠で囲んで目が行くようにする。 */
.ask-head{margin:0 0 8px;font-size:17px}
.henji.open{border:2px solid var(--accent);padding:12px}
.henji.open .ask-head{font-size:20px;font-weight:600}
/* 声の釦は、手が紙でふさがっている時の入口なので札と同じ大きさ。押している間（続けて聞いている間）は地の色を変える。 */
.mic{font:inherit;font-size:20px;min-height:60px;width:100%;margin:0 0 8px;border:2px solid var(--accent);background:var(--paper);color:var(--fg);cursor:pointer}
.mic[aria-pressed=true]{background:var(--accent);color:var(--onaccent)}
.meta{margin:6px 0 0;font-size:13px;color:var(--mute)}
.meta button{font:inherit;font-size:13px;color:var(--accent);background:transparent;border:1px solid var(--accent);padding:6px 12px;margin-right:8px;cursor:pointer}
.sr{position:absolute;left:-9999px}
/* 鏡は小さく。左右を返して鏡の向きにする。横線は、机の上（手と紙）がその下に入る目安。カメラを使うまでは出さない。 */
.mirror{position:relative;width:min(100%,260px);aspect-ratio:4/3;background:var(--soft);border:1px solid var(--frame);overflow:hidden;display:none}
.live .mirror{display:block}
#cam{display:block;width:100%;height:100%;object-fit:cover;transform:scaleX(-1)}
.mirror .line{position:absolute;left:0;right:0;top:55%;border-top:2px dashed var(--accent)}
.mirror .cap{position:absolute;left:0;right:0;bottom:0;margin:0;padding:2px 6px;font-size:12px;color:var(--fg);background:color-mix(in srgb,var(--bg) 82%,transparent)}
/* 横置き（机の端に立てた端末やタブレット）: 左に手本、右に札・返事・鏡。 */
@media (min-width:860px) and (orientation:landscape){
 .stage{grid-template-columns:minmax(0,1.5fr) minmax(300px,1fr)}
 .side{border-top:0;border-left:1px solid var(--rule)}
 .sheet{max-height:58svh}
}
@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
"""

# 札: 頁を読み直さずに手順を進め、押した事だけを送る（手順の番号と出来事。欄は form と同じ）。聞く口は手帖と同じ口（ask-json）。
# 鏡: 押した時にだけカメラを求め、<video> に流すだけ（画素は取り出さない）。頁を離れる時に止める。
# ?cam=1 は確かめの写しを撮るための口（開いた時にカメラを求める。許しの窓はいつもどおり出る）。
SCRIPT = """<script>(()=>{
const st=document.querySelector('.stage'),sid=st.dataset.sid,hid=st.dataset.hid,ver=st.dataset.v;
const wantCam=new URLSearchParams(location.search).get('cam')==='1';
const items=[...document.querySelectorAll('#steps li')],num=document.getElementById('n'),stepIn=document.getElementById('step');
const tiles=document.getElementById('tiles'),mStuck=document.getElementById('msg-stuck');
const goNext=tiles.querySelector('[value=next]'),goDone=tiles.querySelector('[value=done]');
let n=+stepIn.value;
const show=()=>{items.forEach((li,i)=>li.classList.toggle('on',i+1===n));num.textContent=n;stepIn.value=n;goNext.hidden=n>=items.length;goDone.hidden=n<items.length;
 try{history.replaceState(null,'',`?h=${encodeURIComponent(hid)}&v=${ver}&n=${n}`)}catch(e){}};
// その場限りの無作為の印（who）。タブごとの sessionStorage に英数字 10 桁を 1 つ持つ。cookie にしない。持てない画面では添えない。
const who=(()=>{try{let w=sessionStorage.getItem('utsushi-who')||'';if(!/^[a-z0-9]{10}$/.test(w)){
 const a=new Uint8Array(10);if(window.crypto&&crypto.getRandomValues)crypto.getRandomValues(a);else for(let i=0;i<10;i++)a[i]=Math.floor(Math.random()*256);
 w=[...a].map(x=>'abcdefghijklmnopqrstuvwxyz0123456789'[x%%36]).join('');sessionStorage.setItem('utsushi-who',w)}return w}catch(e){return ''}})();
// 組み上がりの札はフォームのまま送るので、印も欄に足す。抜けると、作り終えた人が途中でやめた人に数えられる（making_log.summary）。
if(who){const w=document.createElement('input');w.type='hidden';w.name='who';w.value=who;tiles.append(w)}
const fields=(o)=>{const b=new URLSearchParams(o);b.set('sheet_version',ver);if(who)b.set('who',who);return b};
const send=(event)=>fetch(`/toy/${sid}/step`,{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},
 body:fields({hypothesis:hid,step:n,event,json:'1'})}).then(r=>r.json()).catch(()=>({}));
document.body.classList.add('js');show();
try{const k=`tsukuru-start-${sid}-${hid}`;if(!sessionStorage.getItem(k)){sessionStorage.setItem(k,'1');send('start')}}catch(e){}
// 聞く口。「ここで止まった」を押した段では、見出しを「手順 N で止まった所を聞く」に変えて囲み、字の欄へ手を届かせる。段を進めたら元に戻す。
const henji=document.getElementById('henji'),head=document.getElementById('ask-head'),qIn=document.getElementById('q');
const openAsk=(on)=>{henji.classList.toggle('open',on);head.textContent=on?`手順 ${n} で止まった所を聞く`:'聞く';
 if(on){try{henji.scrollIntoView({block:'nearest'})}catch(e){}qIn.focus()}};
document.querySelectorAll('#tiles button:not([value=done])').forEach(b=>b.addEventListener('click',async(e)=>{e.preventDefault();const ev=b.value;
 const j=await send(ev);mStuck.hidden=true;
 if(ev==='next'||ev==='back'){if(j.step)n=j.step;show();openAsk(false)}
 else if(ev==='stuck'){mStuck.querySelector('.sn').textContent=n;mStuck.hidden=false;openAsk(true)}}));
// 答えの読み上げ（手帖と同じ扱い。在る画面だけ）。手が紙でふさがっていても答えが届くようにする。
// 読み上げの間は音声認識を止める: 止めないと端末が自分の答えを聞き取り、問いとして送り、それがまた読み上げられる（答えの文が質問として残り、費用もかかる）。
// 読み上げの終わりの知らせが来ない機種があるので、長さから見た時間でも戻す。前の読み上げの取り消しの知らせで戻らないよう、番号で見分ける。
let sayStart=()=>{},sayEnd=()=>{},sayId=0;
const say=(t)=>{try{if(!('speechSynthesis' in window))return;speechSynthesis.cancel();const u=new SpeechSynthesisUtterance(t),id=++sayId;u.lang='ja-JP';
 const fin=()=>{if(id===sayId)sayEnd()};u.onend=fin;u.onerror=fin;setTimeout(fin,Math.min(60000,t.length*400+3000));sayStart();speechSynthesis.speak(u)}catch(e){sayEnd()}};
const ans=document.getElementById('answer');
// 問いには今の手順の番号（step）と、その場限りの印（who）を添える。サーバが受けない版では、余った欄は読まれないだけ。
const ask=async(q)=>{if(!q)return;ans.textContent='…';
 const r=await fetch(`/toy/${sid}/ask-json`,{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:fields({hypothesis:hid,question:q,step:n})}).catch(()=>null);
 const j=r?await r.json().catch(()=>({})):{};const t=j.text||j.error||'今は答えられません';ans.textContent=t;say(t)};
document.getElementById('ask-form').addEventListener('submit',(e)=>{e.preventDefault();ask(qIn.value.trim())});
// 声で聞く: ブラウザの音声認識で字にし、字になった問いだけを上の口へ送る（声は録らない・送らない）。1 回押すと話し続けられ、もう 1 回で止まる。
// 使えない画面では釦を隠し、字の欄だけにする（手帖と同じ作り）。
const SR=window.SpeechRecognition||window.webkitSpeechRecognition,mic=document.getElementById('mic');
if(SR){mic.hidden=false;let rec=null,listening=false,speaking=false;
 sayStart=()=>{speaking=true;if(listening&&rec){try{rec.stop()}catch(e){}}};
 sayEnd=()=>{if(!speaking)return;speaking=false;if(listening&&rec){try{rec.start()}catch(e){}}};
 mic.addEventListener('click',()=>{
  if(listening){listening=false;rec&&rec.stop();mic.setAttribute('aria-pressed','false');return}
  rec=new SR();rec.lang='ja-JP';rec.continuous=true;rec.interimResults=false;
  rec.onresult=(ev)=>{if(speaking)return;const t=ev.results[ev.results.length-1][0].transcript.trim();qIn.value=t;ask(t)};
  rec.onend=()=>{if(listening&&!speaking){try{rec.start()}catch(e){}}};
  rec.onerror=()=>{listening=false;mic.setAttribute('aria-pressed','false')};
  listening=true;mic.setAttribute('aria-pressed','true');try{rec.start()}catch(e){}})}
if(henji.classList.contains('open'))head.textContent=`手順 ${n} で止まった所を聞く`;
const v=document.getElementById('cam'),on=document.getElementById('on'),note=document.getElementById('mirror-note');
const off='鏡は出さなくても全部できます。';
if(!navigator.mediaDevices||!navigator.mediaDevices.getUserMedia){on.hidden=true;note.textContent='この機器ではカメラを使えません。'+off}
else{const start=async()=>{try{const s=await navigator.mediaDevices.getUserMedia({video:{facingMode:'user'},audio:false});
 v.srcObject=s;document.body.classList.add('live');on.hidden=true;note.textContent='%s'}catch(e){note.textContent='カメラを使えませんでした。'+off}};
 on.addEventListener('click',start);
 if(wantCam)start()}
addEventListener('pagehide',()=>{const s=v.srcObject;if(s)s.getTracks().forEach(t=>t.stop())});
})()</script>""" % PRIVACY


def _paper(sid, hid):
    """その紙の仮説。話した考えから作った本人の案（OWN-n）も同じ道で開く（呼ぶ側が、本人の画面である事を確かめる）。無ければ None。"""
    return next((x for x in hypotheses.load(sid)["hypotheses"] + hypotheses.own_hypotheses(sid) if x["id"] == hid), None)


def _label(h):
    """紙の呼び名。案は名前で呼ぶ（OWN-n の番号は学ぶ人に見せない）。話した字（how_it_moves）は出さない。"""
    return h["name"] if h["id"].startswith("OWN-") else hypotheses.letter(h)


def step_texts(sid, hid, version=None):
    """その紙（刷ってある一番新しい版）の組み方の文。手順の紙が刷る文と同じ物（instructions.steps ＝ 雛形の steps）。
    版 2 以降は採った寸法で文が変わる事があるので、手順の紙と同じく、その版の寸法で作る。作れない時は空（頁は手順の紙の絵だけで動く）。"""
    data = hypotheses.load(sid)
    h = _paper(sid, hid)
    if h is None or (hid.startswith("OWN-") and not h.get("params")):  # 型紙なしの紙に、雛形の手順は無い
        return []
    vs = printed_versions(sid, hid)
    try:
        params, _ = loop.version_params(sid, hid, version if version in vs else (vs[-1] if vs else 1))
        template = h.get("template") or data.get("template", "slider_fan")
        return [str(s) for s in instructions.steps({**TEMPLATES[template].DEFAULTS, **(params or h.get("params") or {})}, template)]
    except Exception:
        return []


def count(sid, hid, version=None):
    """手順の数。札の送信（step の番号）が手順の数の中かを、サーバが確かめる時に使う。"""
    return len(step_texts(sid, hid, version))


def page(sid, hid, look=skin.DEFAULT, step=1, event="", version=None):
    """作りながら見る頁。呼ぶ側（play_server）が、その仮説の紙が刷ってある事を確かめてから呼ぶ。"""
    from . import hanasu  # 話す口（Issue #279）。循環を避けて、ここで読む

    data = hypotheses.load(sid)
    h = _paper(sid, hid)
    s = skin.SKINS.get(look, skin.SKINS[skin.DEFAULT])
    root = ";".join(f"--{k}:{v}" for k, v in s.items() if k != "name")
    vs = printed_versions(sid, hid)
    v = version if version in vs else vs[-1]  # 開いた時の版のまま作り続ける（別の人の報告で版が上がっても、手順の文を変えない）
    steps = step_texts(sid, hid, v)
    total = max(len(steps), 1)
    n = min(max(step, 1), total)
    on = ' class="on"'
    items = "".join(f'<li{on if i == n else ""}>{esc(t)}</li>' for i, t in enumerate(steps, 1))
    if not steps:
        items = '<li class="on">手順の紙の絵を見て、番号の順に進めます。</li>'
    name = f"{hid}_v{v}_tejun.png"
    if not (out_dir(sid) / name).exists():  # 型紙なしの紙には手順の紙が無い。その紙そのものを出す
        name = f"{hid}_v{v}_free.png"
    img = (f'<img class="sheet" src="/sheet/{esc(sid)}/{esc(name)}" alt="手順の紙（{esc(_label(h))} の紙・版 {v}）">'
           if (out_dir(sid) / name).exists() else "")
    # 止まったの文は先に置いておき、押した時に出す（JS が無い時は ?ev= で出す）。
    stuck = (f'<p id="msg-stuck" class="msg"{"" if event == "stuck" else " hidden"}>止まった所を残しました（手順 <span class="sn">{n}</span>）。'
             'このまま下で、声か字で聞けます。</p>')
    # 聞く口の見出し。止まった段（?ev=stuck。JS が無い時の戻り先）では、その段を名指しして囲む。JS がある時は札を押した時に同じ形に変える。
    asking = event == "stuck"
    ask_head = f"手順 {n} で止まった所を聞く" if asking else "聞く"
    body = (f'<main class="stage" data-sid="{esc(sid)}" data-hid="{esc(hid)}" data-v="{v}">'
            f'<p class="top"><a href="/toy/{esc(sid)}#tsukuru">← {esc(data["toy"])}</a>'
            f'<span>作りながら見る（試作）　{esc(_label(h))} の紙・版 {v}</span></p>'
            f'<section class="tehon" aria-label="手本"><p class="num">手順 <b id="n">{n}</b> / {total}</p>'
            f'<ol id="steps">{items}</ol>{img}</section>'
            f'<section class="side">{stuck}'
            f'<form class="tiles" id="tiles" method="post" action="/toy/{esc(sid)}/step">'
            f'<input type="hidden" name="hypothesis" value="{esc(hid)}"><input type="hidden" name="step" id="step" value="{n}"><input type="hidden" name="sheet_version" value="{v}">'
            # 一番大きい札は 1 つだけ。最後の手順で替わる（JS で進む時は show が同じ 2 つを切り替える）。
            f'<button name="event" value="next" class="go"{" hidden" if n >= total else ""}>次の手順へ</button>'
            f'<button name="event" value="done" class="go"{"" if n >= total else " hidden"}>{esc(DONE_LABEL)}</button>'
            '<button name="event" value="stuck">ここで止まった</button>'
            '<button name="event" value="back" class="small">戻る</button></form>'
            # 作りながら、工夫を話す（一周の 2、Issue #279）。札のすぐ下に置き、今の手順の番号に結ぶ。声は字にして、字だけを残す（hanasu.py）。
            f'{hanasu.craft_box(sid, hid, v, n)}'
            # 聞く口: JS がある時は手帖と同じ口（ask-json）で答えをここに出す。無い時は玩具の頁の聞く口へ送る。
            # 声の釦は、音声認識が在る画面でだけ JS が出す（hidden を外す）。声は字にして送るだけで、録らない。
            f'<div class="henji{" open" if asking else ""}" id="henji" aria-label="返事"><p class="ask-head" id="ask-head">{esc(ask_head)}</p>'
            '<button type="button" class="mic" id="mic" aria-pressed="false" hidden>声で聞く（もう一度押すと止まる）</button>'
            f'<form id="ask-form" method="post" action="/toy/{esc(sid)}/ask">'
            f'<input type="hidden" name="hypothesis" value="{esc(hid)}"><input type="hidden" name="sheet_version" value="{v}"><label class="sr" for="q">聞きたい事</label>'
            '<input type="text" id="q" name="question" maxlength="300" placeholder="谷折りって？" enterkeyhint="send" required><button>聞く</button></form>'
            f'<div class="answer" id="answer" aria-live="polite"></div><p class="meta">{esc(NOTICE)}</p>'
            f'<p class="meta"><a href="/toy/{esc(sid)}/techo">声で聞く・写真を上げる（手帖）</a></p></div>'
            # カメラの目的（本人の言葉 11-05「カメラで見るのはそういうとこだよ」）。人の出来を測らない事を、カメラのそばに書く。
            f'<p class="meta">{esc(CAMERA_PURPOSE)}</p>'
            '<div class="mirror" id="mirror"><video id="cam" autoplay playsinline muted aria-hidden="true"></video>'
            '<span class="line" aria-hidden="true"></span><p class="cap">紙がこの線より下に入るように置く</p></div>'
            f'<p class="meta"><button type="button" id="on">鏡を出す</button><span id="mirror-note">自分と机の上が小さく映ります。{esc(PRIVACY)}鏡は出さなくても全部できます。</span></p>'
            '</section></main>')
    return (f'<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
            f'<title>{esc(data["toy"])} · 作りながら見る</title><style>:root{{{root}}}{STYLE}{skin.TAP_FLOOR}</style>'
            f'<body class="tsukuru skin-{esc(look)}">{body}{SCRIPT}</body></html>')
