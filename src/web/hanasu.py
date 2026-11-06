"""話す口（一周の声の部分。本人の決定 2026-11-05、Issue #279）。

本人の描く一周の 3 つの場面に、同じ部品を置く: 1 仮説を見て考えを話す（玩具の頁）・2 作りながら工夫を話す（作りながら見る頁）・
3 できた物を上げた後に工夫と考えを残す（手帖の記録の札）。残す先は omochae.talk_log（字だけ）。

判断の芯:
- **声そのものは残さない（本人の決定）。** この頁は、マイクを開く code・録る code・声を送る code を持たない（tests/test_hanasu.py が固定する）。
  声を字にするのはブラウザの音声認識で、頁が受け取るのは字だけ。受け口は字のフォームしか受けない（play_server の _form）。
- **声を字にする所（本人の決定 11-05: iPhone・iPad でも話す釦を出す）。** ブラウザの音声認識は、既定では声を認識のサービスへ送って字にする
  （MDN の Web Speech API の頁で確かめた）。端末の中だけで字にする指定（processLocally）を持つ画面では、その指定で聞く。日本語で使えるかは、
  釦を押した時にブラウザへ聞く（available）。持たない画面（調べた時点で iPhone と iPad の Safari など）と、使えなかった画面では、ブラウザの既定の
  音声認識で聞き、本人の決めた断り（「声はブラウザの音声認識で字になります。この頁は声を受け取りません」）を出す。声がブラウザの会社の仕組みへ
  送られる事がある事も、続けて書く。音声認識の口が無い画面では釦を出さず、字の欄だけにする（キーボードの音声入力は使える。頁は声に触らない）。
  切り替え（OMOCHAE_VOICE）: browser（既定）・local（端末の中だけで字にできる画面でだけ釦を出す）・off（釦を出さない）。
- ブラウザの既定の口では、1 回話すごとに止まる形で聞き、途中の字も欄に出す。話し続ける形は、機種によって同じ字が重なったり、終わりの字が来なかったり
  するため（実機では確かめていない。広く使われている聞き方に合わせた）。端末の中で字にする時は、話し続けられる。
- **字は本人が見てから残す。** 聞き取った字は欄に足すだけで、送らない。「残す」を押した時に送る。なぜ: 名前は機械で見分けられない
  （talk_log の床の限り）ので、人の目を入口に置く。聞き違いも直せる。話し終えたら自動で残す形は、手は空くが、この目が無くなるので採らない。
- 床に落ちた時は、欄の字を消さずに理由を返す（直して残せる）。JS が無い時は、理由の頁を返す。
- JS が無くても字で残せる（フォームの送信）。JS がある時は頁を読み直さない（作りながら見る頁の鏡と手順が切れないように）。
- 釦と断りの出し分けは CSS で持つ（html に付く印）。手帖は記録の一覧を頁の中で入れ替えるので、後から来た部品にも同じ出し分けが効くように。
  釦に hidden 属性を付けない: 指で触る機器の床（skin.TAP_FLOOR の [hidden]{display:none!important}）が勝って、幅 1100 以下で釦が消える（tests/test_mic_seen.py が測る）。
  同じ理由で、釦の動きは頁に 1 回だけ置く script が、頁全体で受ける。
- 聞く口の声（手帖・作りながら見る頁の #mic）と同時には聞かない。片方を押したら、もう片方を止める。読み上げの間に入った字は捨てる
  （端末が自分の答えを聞いた物なので）。
- **作りながら話した工夫は、そのまま記録の「工夫した所（直した所）」に入る（本人の設計）。** 記録を残した時に、同じ画面（その場限りの印）で、
  同じ紙について話した工夫を、その記録に結ぶ（talk_log.bind。play_server の記録を残す口が呼ぶ）。上げた後に書き直さなくてよい。
  手帖の記録の札は「工夫した所（直した所）」を出し、その下の口で足せる。
- **記録に入った工夫の字は、記録の感想と同じに、ほかの人の頁に文で出す（本人の決定 11-05）。** 選び肢と、既定で出さない形は置かない。
  名前は機械で落とせないので、名前などを書かないお願いを、口の断りに出す（採られた文のまま）。入口の床（連絡先・名乗り・学年と組・学校の名前）は
  そのままで、出す時にもう一度当てる。合言葉なしで開いた場では、文を出さない（J-028 の線は変えない。節ごと出さない）。
  記録に入る前の字は、学ぶ人の頁に出さない（作る側の頁だけ）。作る側が読んで名前などに気づいた時は、その記録の字を隠せる（talk_log.set_share。画面からは呼ばない）。
  仮説を見て話した考えも記録に結ぶが、記録の札にはまだ出さない（札で工夫と見分ける見出しの文が要り、文面は本人の確認が要るため）。作る側の頁には出す。
- 利用者向けの文は、本人が採ったやさしい言葉の文を、一字も変えずに置く（本人の方針と決定 11-05、Issue #318）。新しい文は、ここで足さない
  （文面は本人の確認が要る。足したい文は、統括の担当へ知らせる）。採られた文で言えない場合は、一番近い採られた文で答える（仕組みと文を分けるため）。
  節の名「工夫した所（直した所）」だけは、本人の言葉のまま置く。
"""
import json
import os
import urllib.parse

from omochae import hypotheses, making_log, records, talk_log
from omochae.model import Failure

from . import skin
from .play_server import esc, printed_versions, sheet_version_of

MODES = ("browser", "local", "off")
DEFAULT_MODE = "browser"  # 本人の決定 11-05: iPhone・iPad でも話す釦を出す

# 利用者向けの文は、本人が採ったやさしい言葉の文（11-05、Issue #318）。小学生・中学生にも分かる言葉で、一字も変えずに置く（tests/test_hanasu.py が文字列で見る）。
# 断りの文。どの場面でも同じ物を出す。名前は床で落とせない（落とせるのは形だけ）ので、入れないお願いを添える。
# 頭の 3 つの文は、本人が決め直した文（11-05）: 前の「声は録音しないし、どこにも送りません」は、ブラウザの音声認識で聞く画面では本当でなかった
# （声がブラウザの会社に送られる事がある）。どの画面でも本当の文にした。
# 最後の文も本人が採った字（話した字を輪の Claude へ渡す事を、残す前に知らせる）。一字も変えない。
NOTICE = "残るのは字だけです。声は録音しません。このサイトは声を受け取りません。残す前に、字を読んで直せます。名前・学校の名前・住所・電話番号・メールは書かないでください。残した字は、AI（Claude）が型紙をよくする案を考えるのにも使います。"
HOW_LOCAL = "「話す」を押すと、声はこの機械（タブレットやパソコン）の中で字になります。"
# ブラウザの既定の音声認識で聞く時の断り（本人の決定 11-05: iPhone・iPad でも話す釦を出し、頁に断りを出す。文は、採られたやさしい言葉の文）。
HOW_BROWSER = "「話す」を押すと、ブラウザ（ネットを見るアプリ）が声を字にします。そのとき、声がブラウザの会社に送られることがあります。このサイトは声を受け取りません。"
# 釦を出さない時（切り替えが local か off の時と、音声認識の口が無い画面）。
HOW_NONE = "この機械では、声を機械の中だけで字にできません。だから「話す」のボタンを出していません。キーボードのマイクのマークを押すと、話した事が字で入ります（声がどう使われるかは、機械の設定によってちがいます）。"
# ③ で上げる時の説明文（本人の決定 11-05、Issue #275 の決める点 3。採られたやさしい言葉の文）。文を変える時は、ここだけを変える。
UPLOAD_NOTICE = "声は字にかえて、声は残しません。のせた写真と動画は、いつ・どこでとったかなどの情報を消してから残します。"

SCENES = {
    "think": {"head": "考えを話す", "hint": "『こう動くと思う』『ここが気になる』など"},
    "craft": {"head": "工夫を話す", "hint": "『ここをこうしたら、うまくいった』など"},
    "keep": {"head": "工夫した所や、思った事を足す"},
}
# 記録の札の節の名前。本人の言葉「工夫した所（直した所）」のまま。
KUFU_HEAD = "工夫した所（直した所）"
KEPT = "残しました。型紙や説明をよくするのに使います。"
FAILED = "残せませんでした。インターネットにつながっているか見て、もう一度押してください。"
REFUSED = "受け付けられません"  # 記録を残した画面の外から足す字を断る時。つながりの案内は誤りになる（開いたままのタブ、15 分の後）。説明の受け口と同じ字
NOHEARD = "聞き取れませんでした。もう一度押すか、字で書いてください。"
# 入口の床に当たって残せなかった時の文。talk_log の理由（「名乗りの形がある」など）は作る人向けの言葉なので、そのまま出さない。
# 連絡先の形の時も、この文を出す（採られた文は 1 つ。連絡先の時の言い分けは、文面の確認が要るので足していない）。
BLOCKED = "名前や学校の名前のような言葉が入っていたので、残しませんでした。その言葉を消して、もう一度「残す」を押してください。"

STYLE = """
.hanasu{border:1px solid var(--frame);background:var(--paper);padding:14px 16px;margin:14px 0;display:grid;gap:8px}
.hanasu .hanasu-head{margin:0;font-size:17px;font-weight:600;letter-spacing:.06em}
.hanasu form{display:grid;gap:8px;margin:0}
.hanasu label{margin:0}
.hanasu textarea,.hanasu select{display:block;width:100%;margin:0;padding:10px 12px;font:inherit;font-size:17px;color:var(--fg);background:var(--field);border:1px solid var(--frame);border-radius:0}
.hanasu textarea{min-height:76px}
.hanasu .hanasu-row{display:flex;gap:10px;flex-wrap:wrap}
/* 釦は、手が紙でふさがっていても押せる大きさ（作りながら見る頁の札と同じ考え）。字は中央（指で触る機器の床が button を横並びの箱にして、字が左に寄るため）。 */
.hanasu .hanasu-row button{flex:1 1 140px;min-height:56px;margin:0;padding:8px 12px;font:inherit;font-size:18px;letter-spacing:.08em;border-radius:0;cursor:pointer;
 text-align:center;justify-content:center}
/* 話す釦は、端末の中で字にできると分かった時（html に印が付いた時）だけ出す。 */
.hanasu .hanasu-mic{display:none;border:2px solid var(--accent);background:var(--paper);color:var(--fg)}
.hanasu-local .hanasu .hanasu-mic,.hanasu-browser .hanasu .hanasu-mic{display:block}
.hanasu .hanasu-mic[aria-pressed=true]{background:var(--accent);color:var(--onaccent)}
.hanasu .hanasu-go{border:0;background:var(--accent);color:var(--onaccent)}
.hanasu .hanasu-go:disabled{opacity:.6}
.hanasu .hanasu-note{margin:0;font-size:15px}
.hanasu .hanasu-note:empty,.hanasu .hanasu-said:empty{display:none}
.hanasu .hanasu-said{margin:0;padding-left:1.2em;font-size:14px}
.hanasu .meta{margin:0;font-size:12px;color:var(--mute);line-height:1.8}
.hanasu .hanasu-how{display:none}
.hanasu-local .hanasu .hanasu-how.is-local,.hanasu-browser .hanasu .hanasu-how.is-browser,.hanasu-none .hanasu .hanasu-how.is-none{display:inline}
.hanasu-kufu{margin:8px 0}
.hanasu-kufu .hanasu-kufu-head{margin:0;font-size:15px;font-weight:600;letter-spacing:.06em}
.hanasu-kufu ul{margin:4px 0;padding-left:1.2em;font-size:15px}
.hanasu-kufu .meta{margin:0;font-size:12px;color:var(--mute)}
"""

# 声を字にする所。REC はブラウザの音声認識の口（前置きの付いた名前でしか出していない版もあるので、両方の名前を見る）。
# 端末の中で字にできるかは、名前でなく、口の形で見分ける（使えるかを聞く口 available と、端末の中だけの指定 processLocally を持つか）。
# 端末の中だけの指定を付けない聞き方（ブラウザの既定。声が外へ送られる事がある）は、切り替えが browser（既定）の時だけ使い、断りの文を替える。
# 聞き取った字は欄に足すだけ。送るのは「残す」を押した時（submit）。
SCRIPT = """<script>(()=>{
const REC=window.SpeechRecognition||window.webkitSpeechRecognition,LANG='ja-JP',html=document.documentElement;
const M={listening:'聞いています。話した事が、欄に字で出ます。',heard:'字にしました。読んで、よければ「残す」を押してください。',
 failed:'__FAILED__',nolang:'この機械では字にできませんでした。字で書いてください。',
 noheard:'__NOHEARD__',install:'声を字にするしくみを、この機械に入れています（はじめの 1 回だけ）…',
 tobrowser:'__HOW_BROWSER__'};
const want='__VOICE__';
// 釦を出すかは、口の形だけで決める（端末の中で字にする指定を持つ実装か）。頁を開いた時には、使えるかをブラウザに聞かない:
// 聞くだけで頁ごと落ちる画面があった（操作する人のいない headless の Chromium で確かめた）。聞くのは、人が釦を押した時だけ。
const feat=!!(REC&&typeof REC.available==='function'&&'processLocally' in REC.prototype);
let how=want==='off'?'none':feat?'local':(want==='browser'&&REC)?'browser':'none',rec=null;
const mark=()=>{html.classList.remove('hanasu-local','hanasu-browser','hanasu-none');html.classList.add('hanasu-'+how)};mark();
const local=async()=>{try{return await REC.available({langs:[LANG],processLocally:true})}catch(e){return 'no'}};
const note=(root,t)=>{root.querySelector('.hanasu-note').textContent=t};
// 釦の字は短く保つ（狭い画面で折れない）。聞いている間は「止める」に替える。
const press=(mic,on)=>{mic.setAttribute('aria-pressed',on?'true':'false');mic.textContent=on?'止める':'話す'};
const stop=()=>{if(rec){try{rec.stop()}catch(e){}}};
const listen=(root,onDevice)=>{
 const box=root.querySelector('textarea'),mic=root.querySelector('.hanasu-mic'),r=new REC(),base=box.value.trim();
 // 端末の中で字にする時は、話し続けられる。ブラウザの既定の口は、1 回話すごとに止まる形で聞き、途中の字も出す
 // （話し続ける形は、機種によって同じ字が重なったり、終わりの字が来なかったりする）。
 r.lang=LANG;r.continuous=onDevice;r.interimResults=!onDevice;if(onDevice)r.processLocally=true;
 r.onresult=(ev)=>{
  // 読み上げの間に入った字は、端末が自分の答えを聞いた物なので入れない。
  if(window.speechSynthesis&&speechSynthesis.speaking)return;
  // 聞き始めた時の欄の字の後ろに、この回に聞いた字を置き直す（途中の字が来るたびに足すと、同じ字が重なる）。
  let said='',n=ev.results.length;for(let i=0;i<n;i++)said+=ev.results[i][0].transcript;said=said.trim();
  // 欄の長さで切る（script が入れた字には maxlength が効かない。見せた字と残る字を同じにする）。
  if(said){box.value=((base?base+' ':'')+said).slice(0,box.maxLength);root.dataset.via='voice';note(root,ev.results[n-1].isFinal?M.heard:M.listening)}};
 r.onerror=(ev)=>{note(root,ev.error==='language-not-supported'?M.nolang:M.noheard)};
 // 終わりの字が来ないまま止まる機種がある。止まった後に「聞いています」を残さない（途中の字が欄にあれば、読んで残せる）。
 r.onend=()=>{press(mic,false);if(rec===r)rec=null;const n=root.querySelector('.hanasu-note');if(n.textContent===M.listening)n.textContent=box.value.trim()!==base?M.heard:''};
 rec=r;press(mic,true);note(root,M.listening);
 try{r.start()}catch(e){press(mic,false);rec=null;note(root,M.noheard)}};
document.addEventListener('click',async(e)=>{
 if(!e.target.closest)return;
 // 聞く口の声（#mic）を押したら、こちらは止める。同時に 2 つは聞けない。
 if(e.target.closest('#mic')){stop();return}
 const mic=e.target.closest('.hanasu-mic');if(!mic)return;
 const root=mic.closest('[data-hanasu]');
 if(mic.getAttribute('aria-pressed')==='true'){stop();return}
 stop();const ask=document.querySelector('#mic[aria-pressed="true"]');if(ask)ask.click();
 if(how==='browser'){listen(root,false);return}
 if(how!=='local')return;
 const a=await local();
 if(a==='available'){listen(root,true);return}
 if(a==='downloadable'||a==='downloading'){note(root,M.install);let ok=false;try{ok=await REC.install({langs:[LANG],processLocally:true})}catch(e2){}
  if(ok){listen(root,true);return}}
 // 端末の中では字にできないと分かった。切り替えが browser の時は、断りの文を替えて、もう一度押した時から既定の口を使う。ほかは釦をしまう。
 if(want==='browser'&&REC){how='browser';mark();note(root,M.tobrowser);return}
 how='none';mark();note(root,M.nolang)});
document.addEventListener('submit',async(e)=>{
 const form=e.target,root=form.closest?form.closest('[data-hanasu]'):null;if(!root)return;
 e.preventDefault();stop();
 const box=form.querySelector('textarea'),go=form.querySelector('.hanasu-go'),text=box.value.trim();
 if(!text||go.disabled)return;
 const b=new URLSearchParams(new FormData(form));b.set('via',root.dataset.via==='voice'?'voice':'text');b.set('json','1');
 // 作りながら見る頁は、頁を読み直さずに手順が進む。今の手順の番号は、その頁の欄（#step）から読む。
 const st=document.getElementById('step');if(b.get('scene')==='craft'&&st)b.set('step',st.value);
 try{const w=sessionStorage.getItem('utsushi-who');if(w)b.set('who',w)}catch(e2){}
 go.disabled=true;let j={};
 try{const r=await fetch(form.action,{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:b});j=await r.json()}catch(e3){j={}}
 go.disabled=false;
 if(j.kept){const li=document.createElement('li');li.textContent=text;root.querySelector('.hanasu-said').append(li);box.value='';root.dataset.via='';note(root,j.note)}
 else note(root,j.why||M.failed)});
// 「残す」の前に #think の釦を押すと、頁を読み直して欄の字が消える。字はこのタブの中にだけ持ち、読み直したら消す（サーバへ送るのは「残す」の時だけ）。
const said=document.querySelector('#hanasu textarea');
if(said){
 const keep='utsushi-said '+said.form.getAttribute('action'),box=said.closest('[data-hanasu]');
 try{const d=JSON.parse(sessionStorage.getItem(keep)||'null');sessionStorage.removeItem(keep);
  if(d&&!said.value){said.value=d.text;box.dataset.via=d.via}}catch(e){}
 document.addEventListener('submit',(e)=>{
  if(!e.target.closest||!e.target.closest('#think')||!said.value.trim())return;
  try{sessionStorage.setItem(keep,JSON.stringify({text:said.value,via:box.dataset.via||''}))}catch(e2){}});
}
addEventListener('pagehide',stop);
})()</script>""".replace("__FAILED__", FAILED).replace("__NOHEARD__", NOHEARD).replace("__HOW_BROWSER__", HOW_BROWSER)

def mode():
    """声の釦の出し方。既定は browser（端末の中だけで字にできない画面では、ブラウザの既定の音声認識で聞く。本人の決定 11-05）。決まりの外の値は既定に戻す。"""
    m = os.environ.get("OMOCHAE_VOICE", DEFAULT_MODE)
    return m if m in MODES else DEFAULT_MODE


def assets():
    """頁に 1 回だけ置く物（見た目と動き）。部品を何個置いても 1 つでよい。声の釦の出し方（mode）は、ここで script に渡す:
    手帖は記録の一覧を後から入れ替えるので、頁を開いた時に部品が 1 つも無くても、後から来た部品が同じ出し方になるように。"""
    return f"<style>{STYLE}</style>" + SCRIPT.replace("__VOICE__", mode())


def box(sid, scene, hid="", version=None, step=None, rid="", with_assets=True):
    """話す口 1 つ。with_assets=False は、同じ頁に何個も置く時（手帖）に、頁の側が assets() を 1 回置く形。"""
    s = SCENES[scene]
    key = esc(f"hn-{scene}-{rid}" if rid else f"hn-{scene}")
    hidden = f'<input type="hidden" name="scene" value="{esc(scene)}">'
    if scene == "think":
        # 考えは、頁に出ているたたき台に結ぶ（型紙は玩具ごとに 1 枚。本人の決定 11-05、J-032）。仮説を選ぶ欄は置かない。
        hidden += f'<input type="hidden" name="hypothesis" value="{esc(hid)}">'
    elif scene == "craft":
        hidden += (f'<input type="hidden" name="hypothesis" value="{esc(hid)}"><input type="hidden" name="sheet_version" value="{esc(version)}">'
                   f'<input type="hidden" name="step" value="{esc(step)}">')
    else:
        hidden += f'<input type="hidden" name="record" value="{esc(rid)}">'
    how = (f'<span class="hanasu-how is-local">{esc(HOW_LOCAL)}</span><span class="hanasu-how is-browser">{esc(HOW_BROWSER)}</span>'
           f'<span class="hanasu-how is-none">{esc(HOW_NONE)}</span>')
    # 玩具の頁の口は、JS が無い時に同じ節へ着く（返事の文もそこに出る。#121 と同じ形）。ほかの 2 つは、戻る道の付いた頁で答える。
    land = "#hanasu" if scene == "think" else ""
    hint = f' placeholder="{esc(s["hint"])}"' if s.get("hint") else ""
    # 取り下げの説明文（本人の決定）。記録ごとの口は手帖の上げる節の中に並ぶので、そこでは節の 1 回に任せて、同じ文を重ねない。
    withdraw = "" if scene == "keep" else f'<p class="meta">{esc(records.WITHDRAW_NOTICE)}</p>'
    return (f'<div class="hanasu" data-hanasu data-voice="{mode()}"><p class="hanasu-head">{esc(s["head"])}</p>'
            f'<form method="post" action="/toy/{esc(sid)}/talk{land}">{hidden}'
            f'<label class="sr" for="{key}">{esc(s["head"])}</label><textarea id="{key}" name="text" maxlength="{talk_log.MAX_TEXT}" {hint} required></textarea>'
            '<div class="hanasu-row"><button type="button" class="hanasu-mic" aria-pressed="false">話す</button>'
            '<button class="hanasu-go">残す</button></div></form>'
            '<p class="hanasu-note" aria-live="polite"></p><ul class="hanasu-said"></ul>'
            f'<p class="meta">{esc(NOTICE)}{how}</p>{withdraw}</div>' + (assets() if with_assets else ""))


def think_section(sid, data, note=""):
    """玩具の頁の節（1 仮説を見て、考えを話す）。仮説の札のすぐ後に置く。note は、JS が無い時に送った後の返事の文（着いたこの節の頭に出す）。"""
    return (f'<section class="sec" id="hanasu">{note}<h2>考えを話す</h2>'
            '<p class="lead">仮説は、AI が考えたためしの案です。見て思った事を、話すか書いて残してください。合っているかどうかは見ません。思ったとおりに話してください。</p>'
            f'{box(sid, "think", hid=hypotheses.sheet_of(sid)["id"])}</section>')


def craft_box(sid, hid, version, step):
    """作りながら見る頁の口（2 作りながら、工夫を話す）。今の手順の番号に結ぶ。"""
    return box(sid, "craft", hid=hid, version=version, step=step)


def kufu_block(sid, r, show_shared=True):
    """記録の札に出す「工夫した所（直した所）」。1 つの節に並べる: 記録の欄に書いた直した点（部品・変えた事・結果）、
    作りながら話した工夫（手順の番号つき）、上げた後に残した字。
    記録に入った字は、記録の感想と同じに、文で出す（本人の決定 11-05）。作る側が隠した字と、床に当たる字は出さない（talk_log.kufu の shared_only）。
    show_shared=False は合言葉なしで開いた場で、節ごと出さない（人の書いた文を出さない。J-028 の線）。1 件も無い記録にも、何も出さない。
    仮説を見て話した考えは、ここにはまだ出さない（工夫と見分ける見出しの文が要り、文面は本人の確認が要るため）。
    学ぶ人の頁とギャラリーが記録の札を作る時も、この関数を呼べる。"""
    typed = [f'{f["part"]} / {f["change"]} / {f["outcome"]}' for f in r.get("fixes") or []
             if isinstance(f, dict) and all(str(f.get(k, "")).strip() for k in ("part", "change", "outcome"))]
    step = lambda k: f"手順 {k['step']}: " if k["step"] else ""
    texts = typed + [step(k) + k["text"] for k in talk_log.kufu(sid, r["id"], shared_only=True) if k["when"] != "idea"]
    if not (texts and show_shared):
        return ""
    lines = "".join(f"<li>{esc(x)}</li>" for x in texts)
    return f'<div class="hanasu-kufu" data-kufu="{esc(r["id"])}"><p class="hanasu-kufu-head">{esc(KUFU_HEAD)}</p><ul>{lines}</ul></div>'


def keep_box(sid, r, show_shared=True, can_add=False):
    """手帖の記録の札に置く物（3 できた物を上げた後に、工夫した所と考えを残す）。上に、その記録の「工夫した所（直した所）」
    （作りながら話した工夫が、記録を残した時にここへ入る）。下に、足す口。show_shared=False は合言葉なしで開いた場。
    can_add は、この画面がこの記録を残した時に真。足す口はその画面にだけ出す（受け口の post も断る）。"""
    return kufu_block(sid, r, show_shared) + (box(sid, "keep", rid=r["id"], with_assets=False) if can_add else "")


def reason(failures):
    """残せなかった理由を、学ぶ人の言葉にする。言うのは採られた文だけ（記録が消えた時などの文は、本人の確認の後に足す）。"""
    f = failures[0]
    if f.floor == "F10.pii":
        return BLOCKED
    return NOHEARD if f.message == talk_log.EMPTY else FAILED


def post(handler, sid, form):
    """話す口の受け口（/toy/<印>/talk）。字のフォームだけがここに届く（play_server の _form が、ほかの形・別の出所・大きすぎる本体を断る）。
    JS からは JSON で答え、JS が無い時は頁で答える。戻り先は場面から作る（送られた値を戻り先にしない）。"""
    scene, hid = form.get("scene", ""), form.get("hypothesis", "")
    version = step = None
    failures = []
    if scene == "craft":
        from . import think_sheet

        # 話した考えから作った案に付く工夫は、作った本人の画面からだけ受ける（ループ1、#335）。
        if not printed_versions(sid, hid) or not think_sheet.usable(handler, sid, hid):
            failures = [Failure("F8.references", "hypothesis_id", "刷った紙が無い")]
        else:
            from . import tsukuru

            version = sheet_version_of(sid, hid, form)
            n = making_log._step_no(form.get("step"))
            # 手順の数の外の番号には結ばない（字は残す。無い手順に結ぶと、作る側が直す紙を取り違える）。
            step = n if n and n <= tsukuru.count(sid, hid, version) else None
    elif scene == "think" and hid:
        vs = printed_versions(sid, hid)
        version = vs[-1] if vs else None
    # 上げた後に足す字は、記録を残した画面からだけ受ける。別の人の字が前の人の記録に結ばれないように（字は残さない）。
    refused = scene == "keep" and not records.mine(form.get("record"), handler._rec_key())
    if refused:
        failures = [Failure("F8.references", "record_id", "記録を残した画面でない")]
    who = form.get("who", "")
    path = None
    if not failures:
        path, failures = talk_log.add(sid, scene, form.get("text", ""), hypothesis_id=hid or None, sheet_version=version, step=step,
                                      record_id=form.get("record") or None, via=form.get("via", "text"), who=who)
    kept = path is not None
    if form.get("json") == "1":
        body = {"kept": True, "note": KEPT} if kept else {"kept": False, "why": REFUSED if refused else reason(failures)}
        return handler._send(200 if kept else 403 if refused else 422, json.dumps(body, ensure_ascii=False), "application/json; charset=utf-8")
    if scene == "think":
        if kept:
            return handler._send(303, "", headers=[("Location", f"/toy/{sid}?msg={urllib.parse.quote(KEPT)}&at=hanasu#hanasu")])
        return handler._send(422, handler._toy(sid, errors=[reason(failures)], at="hanasu"))
    # 戻る道の字は、玩具の頁の入口と同じ字（新しい文を足さない）。
    if scene == "craft" and version:
        back = (f"/toy/{sid}/tsukuru?h={urllib.parse.quote(hid)}&v={version}&n={step or 1}", "作りながら見る（机の端に置く・試作）")
    else:
        back = (f"/toy/{sid}/techo#mine", "手帖をひらく（作りながら聞く・上げる）")
    return handler._send(200 if kept else 403 if refused else 422, skin.notice("残しました" if kept else "残せませんでした", KEPT if kept else REFUSED if refused else reason(failures), handler._look, links=(back,)))


def maker_section(sid, data):
    """作る側の頁（/loop/<印>）の節。話した事を場面ごとに並べる。字だけで、多い順や点にしない（J-025）。学ぶ人の頁には出さない。"""
    sm = talk_log.summary(sid)
    letter = {h["id"]: hypotheses.letter(h) for h in data["hypotheses"]}
    paper = lambda hid: f"仮説 {letter[hid]} の紙" if hid in letter else (f"自分の仮説 {hid} の紙" if hid else "紙を選ばず")
    none = '<p class="meta">残した言葉はまだありません。</p>'
    lines = lambda items: "<ul>" + "".join(f"<li>{esc(x)}</li>" for x in items) + "</ul>" if items else none
    think = lines([f'{"仮説 " + letter[t["hypothesis_id"]] if t["hypothesis_id"] in letter else "仮説を選ばず"}: {t["text"]}' for t in sm["think"]])
    craft = "".join(f'<h4>{esc(paper(h))}・版 {esc(v)}・{"手順 " + str(n) if n is not None else "手順なし"}</h4>{lines(texts)}'
                    for h, vs in sm["craft"].items() for v, ss in vs.items() for n, texts in ss.items()) or none
    when = lambda k: "考え" if k["when"] == "idea" else (f"手順 {k['step']}" if k["step"] else "作りながら") if k["when"] == "making" else "上げた後"
    keep = "".join(f'<h4>{esc(r["record_id"])}（{esc(paper(r["hypothesis_id"]))}・版 {esc(r["sheet_version"])}）</h4>'
                   + lines([f'{when(k)}: {k["text"]}{"" if k["share"] else "［隠している］"}' for k in r["kufu"]]) for r in sm["records"]) or none
    d = sm["dropped"]
    return ('<section class="sec" id="k7"><h2>7 話した事</h2>'
            '<p class="meta">話すか書いて残した言葉を、場面ごとに並べます。残っているのは字だけで、声は残していません。'
            '名前は機械では見分けられないので、読む時に気づいたら消します。</p>'
            f'<h3>仮説を見て話した考え</h3>{think}<h3>作りながら話した工夫（手順ごと）</h3>{craft}<h3>記録の「{esc(KUFU_HEAD)}」</h3>'
            '<p class="meta">話した考えと、作りながら話した工夫は、記録を残した時にその記録に入ります。上げた後に足した言葉も、ここに並びます。'
            '記録に入った言葉は、ほかの人の頁にも出ます。［隠している］は、作る側が隠した言葉です。</p>'
            f'{keep}'
            f'<p class="meta">声から字にした物 {sm["via"]["voice"]} 件・字で書いた物 {sm["via"]["text"]} 件。'
            f'床で落とした物（文は残していません）: 連絡先の形 {d["pii"]} 件・名乗りや学校の形 {d["name"]} 件。</p></section>')
