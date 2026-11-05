"""作りながら見る（観察 A の試作）。本人の案の具体化（2026-11-05 朝、窓口を通して届いた）:
「生徒の一人一台端末や iPhone を机の端に置いて、端末のカメラで生徒の上半身を写す形に。間に手と動画と紙があり、作成の様子を見れるようにする」。

何をする頁か: 端末を机の端に立て、画面に手本（今の手順の文と、手順の紙の絵）と返事（聞いた事の答え）を出す。隅の小さな鏡に、
自分と机の上（手と紙）が映る。進み方は大きな札（次の手順へ・止まった・できた）で残す。設計は docs/process/research/30 の「観察の置き方」。

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
- 「できた」を祝う演出は入れない（紙で動くかはこの後に確かめる事で、組み上がりは成績ではない。J-025）。
- JS が無くても札は働く（フォームの送信で手順が進む）。JS がある時は、頁を読み直さずに進める（読み直すと鏡が止まるため）。
"""
from omochae import hypotheses, instructions, loop
from omochae.compose import TEMPLATES

from . import skin
from .kazasu import PRIVACY
from .play_server import esc, out_dir, printed_versions

NOTICE = "聞いた言葉は字にして、案内を良くするために残します。声と映像は残しません。名前は言わないでください。"

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
/* 札は手が紙でふさがっていても押せる大きさ。並びは進む順（次へ・止まった・できた）。色で良し悪しを付けない。 */
.tiles{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:0}
.tiles button{font:inherit;font-size:22px;min-height:72px;border:2px solid var(--accent);background:var(--paper);color:var(--fg);cursor:pointer;padding:8px 10px}
.tiles .go{grid-column:1/-1;background:var(--accent);color:var(--onaccent);font-size:26px;min-height:84px}
.tiles .small{grid-column:1/-1;min-height:44px;font-size:15px;border:1px solid var(--frame);color:var(--mute)}
.msg{margin:0;padding:10px 12px;border:1px solid var(--accent);font-size:17px}
.henji form{display:flex;gap:8px}
.henji input{flex:1;min-width:0;font:inherit;font-size:18px;padding:10px;border:1px solid var(--frame);background:var(--field);color:var(--fg)}
.henji form button{font:inherit;font-size:18px;padding:10px 18px;border:1px solid var(--accent);background:transparent;color:var(--accent);cursor:pointer}
.answer{min-height:2.2em;font-size:20px;margin-top:8px}
.meta{margin:6px 0 0;font-size:13px;color:var(--mute)}
.meta button{font:inherit;font-size:13px;color:var(--accent);background:transparent;border:1px solid var(--accent);padding:6px 12px;margin-right:8px;cursor:pointer}
.sr{position:absolute;left:-9999px}
/* 鏡は小さく。左右を返して鏡の向きにする。横線は、机の上（手と紙）がその下に入る目安。カメラを使うまでは出さない。 */
.mirror{position:relative;width:min(100%,260px);aspect-ratio:4/3;background:var(--soft);border:1px solid var(--frame);overflow:hidden;display:none}
.live .mirror{display:block}
#cam{display:block;width:100%;height:100%;object-fit:cover;transform:scaleX(-1)}
.mirror .line{position:absolute;left:0;right:0;top:55%;border-top:2px dashed var(--accent)}
.mirror .cap{position:absolute;left:0;right:0;bottom:0;margin:0;padding:2px 6px;font-size:11px;color:var(--fg);background:color-mix(in srgb,var(--bg) 82%,transparent)}
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
const st=document.querySelector('.stage'),sid=st.dataset.sid,hid=st.dataset.hid;
const items=[...document.querySelectorAll('#steps li')],num=document.getElementById('n'),stepIn=document.getElementById('step');
const mStuck=document.getElementById('msg-stuck'),mDone=document.getElementById('msg-done');
let n=+stepIn.value;
const show=()=>{items.forEach((li,i)=>li.classList.toggle('on',i+1===n));num.textContent=n;stepIn.value=n;
 try{history.replaceState(null,'',`?h=${encodeURIComponent(hid)}&n=${n}`)}catch(e){}};
const send=(event)=>fetch(`/toy/${sid}/step`,{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},
 body:new URLSearchParams({hypothesis:hid,step:n,event,json:'1'})}).then(r=>r.json()).catch(()=>({}));
document.body.classList.add('js');show();
try{const k=`tsukuru-start-${sid}-${hid}`;if(!sessionStorage.getItem(k)){sessionStorage.setItem(k,'1');send('start')}}catch(e){}
document.querySelectorAll('#tiles button').forEach(b=>b.addEventListener('click',async(e)=>{e.preventDefault();const ev=b.value;
 const j=await send(ev);mStuck.hidden=true;mDone.hidden=true;
 if(ev==='next'||ev==='back'){if(j.step)n=j.step;show()}
 else if(ev==='stuck'){mStuck.querySelector('.sn').textContent=n;mStuck.hidden=false;document.getElementById('q').focus()}
 else if(ev==='done'){mDone.hidden=false}}));
const ans=document.getElementById('answer');
document.getElementById('ask-form').addEventListener('submit',async(e)=>{e.preventDefault();const q=document.getElementById('q').value.trim();if(!q)return;
 ans.textContent='…';
 const r=await fetch(`/toy/${sid}/ask-json`,{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:new URLSearchParams({hypothesis:hid,question:q})}).catch(()=>null);
 const j=r?await r.json().catch(()=>({})):{};ans.textContent=j.text||j.error||'今は答えられません'});
const v=document.getElementById('cam'),on=document.getElementById('on'),note=document.getElementById('mirror-note');
const off='鏡は出さなくても全部できます。';
if(!navigator.mediaDevices||!navigator.mediaDevices.getUserMedia){on.hidden=true;note.textContent='この機器ではカメラを使えません。'+off}
else{const start=async()=>{try{const s=await navigator.mediaDevices.getUserMedia({video:{facingMode:'user'},audio:false});
 v.srcObject=s;document.body.classList.add('live');on.hidden=true;note.textContent='%s'}catch(e){note.textContent='カメラを使えませんでした。'+off}};
 on.addEventListener('click',start);
 if(new URLSearchParams(location.search).get('cam')==='1')start()}
addEventListener('pagehide',()=>{const s=v.srcObject;if(s)s.getTracks().forEach(t=>t.stop())});
})()</script>""" % PRIVACY


def step_texts(sid, hid):
    """その紙（刷ってある一番新しい版）の組み方の文。手順の紙が刷る文と同じ物（instructions.steps ＝ 雛形の steps）。
    版 2 以降は採った寸法で文が変わる事があるので、手順の紙と同じく、その版の寸法で作る。作れない時は空（頁は手順の紙の絵だけで動く）。"""
    data = hypotheses.load(sid)
    h = next((x for x in data["hypotheses"] if x["id"] == hid), None)
    if h is None:
        return []
    vs = printed_versions(sid, hid)
    try:
        params, _ = loop.version_params(sid, hid, vs[-1] if vs else 1)
        template = h.get("template") or data.get("template", "slider_fan")
        return [str(s) for s in instructions.steps({**TEMPLATES[template].DEFAULTS, **(params or h.get("params") or {})}, template)]
    except Exception:
        return []


def count(sid, hid):
    """手順の数。札の送信（step の番号）が手順の数の中かを、サーバが確かめる時に使う。"""
    return len(step_texts(sid, hid))


def page(sid, hid, look=skin.DEFAULT, step=1, event=""):
    """作りながら見る頁。呼ぶ側（play_server）が、予想の後である事と、その仮説の紙が刷ってある事を確かめてから呼ぶ。"""
    data = hypotheses.load(sid)
    h = next(x for x in data["hypotheses"] if x["id"] == hid)
    s = skin.SKINS.get(look, skin.SKINS[skin.DEFAULT])
    root = ";".join(f"--{k}:{v}" for k, v in s.items() if k != "name")
    v = printed_versions(sid, hid)[-1]
    steps = step_texts(sid, hid)
    total = max(len(steps), 1)
    n = min(max(step, 1), total)
    items = "".join(f'<li{" class=\"on\"" if i == n else ""}>{esc(t)}</li>' for i, t in enumerate(steps, 1))
    if not steps:
        items = '<li class="on">手順の紙の絵を見て、番号の順に進めます。</li>'
    name = f"{hid}_v{v}_tejun.png"
    img = (f'<img class="sheet" src="/sheet/{esc(sid)}/{esc(name)}" alt="手順の紙（{esc(hypotheses.letter(h))} の紙・版 {v}）">'
           if (out_dir(sid) / name).exists() else "")
    # 止まった・できたの文は先に置いておき、押した時に出す（JS が無い時は ?ev= で出す）。祝いの言葉にしない。
    stuck = (f'<p id="msg-stuck" class="msg"{"" if event == "stuck" else " hidden"}>止まった所を残しました（手順 <span class="sn">{n}</span>）。'
             '聞きたい事があれば、下で聞けます。</p>')
    done = (f'<p id="msg-done" class="msg"{"" if event == "done" else " hidden"}>組み上がった事を残しました。動かしてみて、'
            f'<a href="/toy/{esc(sid)}#kiroku">玩具の頁で記録を残します</a>。</p>')
    body = (f'<main class="stage" data-sid="{esc(sid)}" data-hid="{esc(hid)}">'
            f'<p class="top"><a href="/toy/{esc(sid)}#tsukuru">← {esc(data["toy"])}</a>'
            f'<span>作りながら見る（試作）　{esc(hypotheses.letter(h))} の紙・版 {v}</span></p>'
            f'<section class="tehon" aria-label="手本"><p class="num">手順 <b id="n">{n}</b> / {total}</p>'
            f'<ol id="steps">{items}</ol>{img}</section>'
            f'<section class="side">{stuck}{done}'
            f'<form class="tiles" id="tiles" method="post" action="/toy/{esc(sid)}/step">'
            f'<input type="hidden" name="hypothesis" value="{esc(hid)}"><input type="hidden" name="step" id="step" value="{n}">'
            '<button name="event" value="next" class="go">次の手順へ</button>'
            '<button name="event" value="stuck">止まった</button><button name="event" value="done">できた</button>'
            '<button name="event" value="back" class="small">戻る</button></form>'
            # 聞く口: JS がある時は手帖と同じ口（ask-json）で答えをここに出す。無い時は玩具の頁の聞く口へ送る。
            f'<div class="henji" aria-label="返事"><form id="ask-form" method="post" action="/toy/{esc(sid)}/ask">'
            f'<input type="hidden" name="hypothesis" value="{esc(hid)}"><label class="sr" for="q">聞きたい事</label>'
            '<input type="text" id="q" name="question" maxlength="300" placeholder="谷折りって？" enterkeyhint="send" required><button>聞く</button></form>'
            f'<div class="answer" id="answer" aria-live="polite"></div><p class="meta">{esc(NOTICE)}</p>'
            f'<p class="meta"><a href="/toy/{esc(sid)}/techo">声で聞く・写真を上げる（手帖）</a></p></div>'
            '<div class="mirror" id="mirror"><video id="cam" autoplay playsinline muted aria-hidden="true"></video>'
            '<span class="line" aria-hidden="true"></span><p class="cap">紙がこの線より下に入るように置く</p></div>'
            f'<p class="meta"><button type="button" id="on">鏡を出す</button><span id="mirror-note">自分と机の上が小さく映ります。{esc(PRIVACY)}鏡は出さなくても全部できます。</span></p>'
            '</section></main>')
    return (f'<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
            f'<title>{esc(data["toy"])} · 作りながら見る</title><style>:root{{{root}}}{STYLE}</style>'
            f'<body class="tsukuru skin-{esc(look)}">{body}{SCRIPT}</body></html>')
