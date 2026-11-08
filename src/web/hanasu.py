"""話す口（一周の声の部分。本人の決定 2026-11-05、Issue #279）。

本人の描く一周の 3 つの場面に、同じ部品を置く: 1 仮説を見て考えを話す（玩具の頁）・2 作りながら工夫を話す（作りながら見る頁）・
3 できた物を上げた後に工夫と考えを残す（手帖の記録の札）。残す先は omochae.talk_log（字だけ）。

判断の芯:
- **声を字にするのは、その機械のキーボード（端末の音声入力）。この頁は声を聞いて字にしない。** 本人 11-08「サイトの中の「はなす」がうまく動かない。
  クロードの音声認識をはずして、ユーザーの端末の音声入力に頼るのでいいのではないか。」で、ブラウザの音声認識（Web Speech API）と、
  端末の中だけで字にする指定と、切り替え OMOCHAE_VOICE（browser・local・off）を外した（設計は grove の state/no-speech-recognition-20261108.md の 2 版）。
  前の本人の決定 11-05「iPhone・iPad でも話す釦を出す」は、音声認識の上の決めなので、ここで替わった。
  字の欄の下に「キーボードのマイクで話して入れられます。」の 1 行（KEYBOARD・本人の OK 11-08）を置く。iPhone・iPad・Android の画面のキーボードの
  マイクの釦の事で、パソコンや作業の頁の画面には無い事がある（統括から本人へ添えた）。
- **声の区切りは「声を録る」を押した間だけ録る（本人の答え 11-08「(A) 声を録る釦を置いて残す。新しい字 3 つもよい。」・415「声も送って解析に使う形にする。」）。**
  録る code はこの台本に置かず、置き場（web.clips）の voiceStart・voiceStop を呼ぶだけ（tests/test_hanasu.py が固定する）。録った声はこの端末に置き、
  のこすで承認した時に送り、サーバの中で字にしてから消す（omochae.voice_text）。欄の字と録った声は別の物で、片方だけでもよい。
  釦の字は「声を録る」、録っている間は「止める」（本人の OK）。2 つの字は両方とも頁に置き、押した印（aria-pressed）で CSS が片方を見せる:
  台本の中の字は英語の頁で訳されない（web.i18n）ので、台本で釦の字を書き替えない。止まる所は web.clips の注の 7 つで、この台本は「残す」の前に止めて
  置き終えるのを待つ。
  **記録の札の足す口（keep）には置かない**（設計の 2 版の止め 1）: 前の記録に足す口で録った声は、その記録に結べず、次の のこす の承認で別の記録と
  一緒に送られ、回が無い時は印の無い区切りを消すため。足す口は字の欄と端末のマイクだけにする。
- **字は本人が見てから残す。** 欄の字は「残す」を押した時に送る。なぜ: 名前は機械で見分けられない（talk_log の床の限り）ので、人の目を入口に置く。
- 床に落ちた時は、欄の字を消さずに理由を返す（直して残せる）。JS が無い時は、理由の頁を返す。
- JS が無くても字で残せる（フォームの送信）。JS がある時は頁を読み直さない（作りながら見る頁の鏡と手順が切れないように）。
- 釦の字の出し分けは CSS で持つ。釦に hidden 属性を付けない: 指で触る機器の床（skin.TAP_FLOOR の [hidden]{display:none!important}）が勝って、
  幅 1100 以下で釦が消えた事がある（tests/test_mic_seen.py が測る）。釦の動きは頁に 1 回だけ置く script が、頁全体で受ける
  （手帖の記録の頁は、記録の一覧を頁の中で入れ替えるので、後から来た部品にも同じ動きが効くように）。
- **作りながら話した工夫は、記録を残した時に、その記録に結ぶ（本人の設計）。** 同じ画面（その場限りの印）で、同じ紙について話した工夫を、
  その記録に結ぶ（talk_log.bind。play_server の記録を残す口が呼ぶ）。上げた後に書き直さなくてよい。結んだ字は、輪と束と作る側の頁が読む。
- **話した字は、学ぶ人の頁に出さない（本人の決定 11-06、J-034。11-05 の「記録の感想と同じに出す」を変えた）。** 頁に出す字は、AI が整理した字だけ。
  話した字そのものは作る側だけが読む（/loop/<印> の節と /loop/ayumi）。なぜ: 名前は機械で落とせず、話した字は書いた字より名前や癖が混ざりやすい。
  整理した字の置き場はまだ無いので、今は記録の札に話した字の行を出さない（置き場ができたら、その字を出す形で作り直す）。
  記録の札の「工夫した所（直した所）」には、記録の欄に書いた直した点（部品・変えた事・結果）だけを出す。手で欄に書いた字は、書いた字として出してきた物なので変えない。
  その下の口で足せる（足した字は輪の材料に入り、札には出ない）。合言葉なしで開いた場では、節ごと出さない（J-028）。
  作る側が読んで名前などに気づいた時は、その記録の字を、輪と束からも外せる（talk_log.set_share。画面からは呼ばない）。
- 「残す」の後に、残した字を口の下に並べるのは、話した本人がその画面で確かめるため（頁を開き直すと消え、ほかの人の頁には出ない）。この決定でも残す。
- 利用者向けの文は、本人が採ったやさしい言葉の文を、一字も変えずに置く（本人の方針と決定 11-05、Issue #318）。新しい文は、ここで足さない
  （文面は本人の確認が要る。足したい文は、統括の担当へ知らせる）。採られた文で言えない場合は、一番近い採られた文で答える（仕組みと文を分けるため）。
  節の名「工夫した所（直した所）」だけは、本人の言葉のまま置く。
"""
import json
import urllib.parse

from omochae import hypotheses, making_log, records, talk_log
from omochae.model import Failure

from . import clips, skin
from .play_server import esc, printed_versions, sheet_version_of

# 利用者向けの文は、本人が採ったやさしい言葉の文（11-05、Issue #318）。小学生・中学生にも分かる言葉で、一字も変えずに置く（tests/test_hanasu.py が文字列で見る）。
# 断りの文。どの場面でも同じ物を出す。名前は床で落とせない（落とせるのは形だけ）ので、入れないお願いを添える。
# 頭の 3 つの文は、本人が決め直した文（11-05）: 前の「声は録音しないし、どこにも送りません」は、ブラウザの音声認識で聞く画面では本当でなかった
# （声がブラウザの会社に送られる事がある）。どの画面でも本当の文にした。
# 最後の文も本人が採った字（話した字を輪の Claude へ渡す事を、残す前に知らせる）。一字も変えない。
# 11-08: 2・3 文目（「声は録音しません。話した声は、このサイトに送りません。」）は、本人の決め 415「声も送って解析に使う形にする。」と
# 「公開デモでも声も録る。」で本当でなくなったので、設計の 6 節の字に替えた（押して話した間の声を録り、のこすで承認した時に送る・字にしてから消す）。
# 同じ日の後で、「話す」の釦を外して「声を録る」の釦にした（本人の答え (A)）ので、2 文目の「押して話した間」を「「声を録る」を押した間」にした
# （音声認識を外す設計の 4 節の (A) の字。本人の確かめ待ち）
NOTICE = "残るのは字だけです。「声を録る」を押した間の声を録り、のこすで承認した時に受け取ります。声は字にしてから消します。残す前に、字を読んで直せます。名前・学校の名前・住所・電話番号・メールは書かないでください。残した字は、AI（Claude）が型紙をよくする案を考えるのにも使います。"
# 字の欄の下の 1 行と、録る釦の字（本人の答え 11-08「新しい字 3 つもよい。」）。前の HOW_LOCAL・HOW_BROWSER・HOW_NONE（どこで声を字にするかの断り）は、
# この頁が声を字にしなくなったので外した。HOW_NONE の後半（キーボードのマイクのマーク）は、この 1 行に寄せた（同じ意味の字を 2 つにしない）
KEYBOARD = "キーボードのマイクで話して入れられます。"
REC_START, REC_STOP = "声を録る", "止める"
# ③ で上げる時の説明文（本人の決定 11-05、Issue #275 の決める点 3。採られたやさしい言葉の文）。文を変える時は、ここだけを変える。
# 11-08: 動画の声を字にしてから消す形（本人の言葉「全部残していいことにしたい。」・omochae.voice_text）に合わせた案。本人の確かめ待ち。
# 子どもの声は入れないでくださいは、決まり（今週は成人のみ・子どもの写真と声は扱わない。J-013 の 6・J-021・J-022）と字を合わせるため。
UPLOAD_NOTICE = "のせた写真と動画は、いつ・どこでとったかなどの情報を消してから残します。動画の声は、この機械の中で字にしてから消します。字にできない時も、3 日で消します。子どもの声は入れないでください。"

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
# 入口の床に当たって残せなかった時の文。talk_log の理由（「名乗りの形がある」など）は作る人向けの言葉なので、そのまま出さない。
# 連絡先の形の時も、この文を出す（採られた文は 1 つ。連絡先の時の言い分けは、文面の確認が要るので足していない）。
BLOCKED = "名前・学校の名前・住所・電話番号・メールのような言葉が入っていたので、残しませんでした。その言葉を消して、もう一度「残す」を押してください。"

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
/* 録る釦は、録っている間（押した印）だけ地と字を入れ替え、字を「止める」にする。字は 2 つとも頁にあり、片方だけを見せる */
.hanasu .hanasu-rec{border:2px solid var(--accent);background:var(--paper);color:var(--fg)}
.hanasu-rec[aria-pressed=true]{background:var(--accent);color:var(--onaccent)}
.hanasu-rec .rec-stop,.hanasu-rec[aria-pressed=true] .rec-go{display:none}
.hanasu-rec[aria-pressed=true] .rec-stop{display:inline}
.hanasu .hanasu-go{border:0;background:var(--accent);color:var(--onaccent)}
.hanasu .hanasu-go:disabled{opacity:.6}
.hanasu .hanasu-note{margin:0;font-size:15px}
.hanasu .hanasu-note:empty,.hanasu .hanasu-said:empty{display:none}
.hanasu .hanasu-said{margin:0;padding-left:1.2em;font-size:14px}
.hanasu .meta{margin:0;font-size:12px;color:var(--mute);line-height:1.8}
.hanasu-kb{margin:0;font-size:14px}
.hanasu-kufu{margin:8px 0}
.hanasu-kufu .hanasu-kufu-head{margin:0;font-size:15px;font-weight:600;letter-spacing:.06em}
.hanasu-kufu ul{margin:4px 0;padding-left:1.2em;font-size:15px}
.hanasu-kufu .meta{margin:0;font-size:12px;color:var(--mute)}
"""

# 録る釦と「残す」の動き（頁に 1 回）。録る code は置き場（web.clips）にだけあり、ここは voiceStart・voiceStop を呼ぶだけ。
# 録れない画面（置き場の台本が無い・マイクを開けない）と、5 ついっぱいの時は、1 行で知らせる。録っている口は頁に 1 つだけ（置き場の録りが 1 つなので）。
# 欄の字は「残す」を押した時に送る（submit）。送る前に録りを止め、置き終えるのを待つ（止めた区切りが、のこすの並びに入るように）。
SCRIPT = """<script>(()=>{
const M={norec:'__NOREC__',full:'__FULL__',failed:'__FAILED__'};
const note=(root,t)=>{const n=root.querySelector('.hanasu-note');if(n)n.textContent=t};
const press=(b,v)=>b.setAttribute('aria-pressed',v?'true':'false');
const stopRec=()=>window.utsushiClips?utsushiClips.voiceStop():Promise.resolve('none');
// 区切りに添える付帯情報: 玩具の印・場面・手順の番号（作りながら見る頁は手順が頁の中で進むので、その頁の欄 #step から読む）
const meta=(root)=>{const sc=root.querySelector('input[name=scene]'),st=root.querySelector('input[name=step]')||document.getElementById('step');
 return {sid:root.dataset.sid,scene:sc?sc.value:(root.dataset.scene||''),step:st?st.value:''}};
document.addEventListener('click',async(e)=>{
 const b=e.target.closest&&e.target.closest('.hanasu-rec');if(!b)return;
 const root=b.closest('[data-hanasu]');if(!root)return;
 if(b.getAttribute('aria-pressed')==='true'){await stopRec();press(b,false);return}
 await stopRec();
 if(!window.utsushiClips||!root.dataset.sid){note(root,M.norec);return}
 press(b,true);note(root,'');
 // 録り終えた時（もう一度押した・60 秒・大きさの手前・頁が隠れた・残す など）に釦を戻す。5 ついっぱいで置けなかった時だけ知らせる。
 // 録れた事を見せるのは釦の字が戻る事だけで、並びは のこす の確かめの画面にある（数や並びをここに足すと新しい字になる・web.clips の注）
 const ended=(got)=>{press(b,false);if(got==='full')note(root,M.full)};
 let r='none';try{r=await utsushiClips.voiceStart(meta(root),ended)}catch(e2){}
 if(r!=='rec'){press(b,false);note(root,r==='full'?M.full:M.norec)}});
document.addEventListener('submit',async(e)=>{
 const form=e.target,root=form.closest?form.closest('[data-hanasu]'):null;if(!root)return;
 e.preventDefault();await stopRec();
 const box=form.querySelector('textarea'),go=form.querySelector('.hanasu-go'),text=box.value.trim();
 if(!text||go.disabled)return;
 const b=new URLSearchParams(new FormData(form));b.set('via','text');b.set('json','1');
 // 作りながら見る頁は、頁を読み直さずに手順が進む。今の手順の番号は、その頁の欄（#step）から読む。
 const st=document.getElementById('step');if(b.get('scene')==='craft'&&st)b.set('step',st.value);
 try{const w=sessionStorage.getItem('utsushi-who');if(w)b.set('who',w)}catch(e2){}
 go.disabled=true;let j={};
 try{const r=await fetch(form.action,{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:b});j=await r.json()}catch(e3){j={}}
 go.disabled=false;
 if(j.kept){const li=document.createElement('li');li.textContent=text;root.querySelector('.hanasu-said').append(li);box.value='';note(root,j.note)}
 else note(root,j.why||M.failed)});
// 「残す」の前に #think の釦を押すと、頁を読み直して欄の字が消える。字はこのタブの中にだけ持ち、読み直したら消す（サーバへ送るのは「残す」の時だけ）。
const said=document.querySelector('#hanasu textarea');
if(said){
 const keep='utsushi-said '+said.form.getAttribute('action');
 try{const d=JSON.parse(sessionStorage.getItem(keep)||'null');sessionStorage.removeItem(keep);
  if(d&&!said.value)said.value=d.text}catch(e){}
 document.addEventListener('submit',(e)=>{
  if(!e.target.closest||!e.target.closest('#think')||!said.value.trim())return;
  try{sessionStorage.setItem(keep,JSON.stringify({text:said.value}))}catch(e2){}});
}
})()</script>""".replace("__NOREC__", clips.NO_VOICE).replace("__FULL__", clips.FULL).replace("__FAILED__", FAILED)


def rec_button():
    """録る釦（作りながら見る頁の工夫の口・のこすの頁の工夫の欄）。字は 2 つとも置き、押した印で CSS が片方を見せる（英語の頁でも両方が訳される）。"""
    return (f'<button type="button" class="hanasu-rec" aria-pressed="false"><span class="rec-go">{esc(REC_START)}</span>'
            f'<span class="rec-stop">{esc(REC_STOP)}</span></button>')


def keyboard_line():
    """字の欄の下の 1 行（端末のキーボードのマイク）。話す口の 3 つの場面と、のこすの頁の工夫の欄に、同じ字を 1 か所から出す。"""
    return f'<p class="meta hanasu-kb">{esc(KEYBOARD)}</p>'


def assets():
    """頁に 1 回だけ置く物（見た目と動き）。部品を何個置いても 1 つでよい（手帖は記録の一覧を後から入れ替えるので、後から来た部品にも同じ動きが効く）。"""
    # 声の区切りの置き場（web.clips）も頁に 1 回だけ置く。話す口の台本は録る code を持たず、置き場の voiceStart・voiceStop を呼ぶだけ
    return f"<style>{STYLE}</style>" + SCRIPT + clips.assets()


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
    # 玩具の頁の口は、JS が無い時に同じ節へ着く（返事の文もそこに出る。#121 と同じ形）。ほかの 2 つは、戻る道の付いた頁で答える。
    land = "#hanasu" if scene == "think" else ""
    hint = f' placeholder="{esc(s["hint"])}"' if s.get("hint") else ""
    # 取り下げの説明文（本人の決定）。記録ごとの口は手帖の上げる節の中に並ぶので、そこでは節の 1 回に任せて、同じ文を重ねない。
    withdraw = "" if scene == "keep" else f'<p class="meta">{esc(records.WITHDRAW_NOTICE)}</p>'
    # 玩具の頁の考えの箱は、節の見出し「考えを話す」と同じ字が並ぶので、箱の見出しを出さない（本人の決定 11-06。読み上げの名前の label は残す）。
    shown = "" if scene == "think" else f'<p class="hanasu-head">{esc(s["head"])}</p>'
    # 録る釦は記録の札の足す口（keep）には置かない（設計の 2 版の止め 1・上の注）。字の欄の下の 1 行は 3 つの場面の全部に出す
    rec = "" if scene == "keep" else rec_button()
    return (f'<div class="hanasu" data-hanasu data-sid="{esc(sid)}" data-scene="{esc(scene)}">{shown}'
            f'<form method="post" action="/toy/{esc(sid)}/talk{land}">{hidden}'
            f'<label class="sr" for="{key}">{esc(s["head"])}</label><textarea id="{key}" name="text" maxlength="{talk_log.MAX_TEXT}" {hint} required></textarea>'
            f'{keyboard_line()}<div class="hanasu-row">{rec}<button class="hanasu-go">残す</button></div></form>'
            '<p class="hanasu-note" aria-live="polite"></p><ul class="hanasu-said"></ul>'
            f'<p class="meta">{esc(NOTICE)}</p>{withdraw}</div>' + (assets() if with_assets else ""))


def think_section(sid, data, note=""):
    """玩具の頁の節（1 仮説を見て、考えを話す）。仮説の札のすぐ後に置く。note は、JS が無い時に送った後の返事の文（着いたこの節の頭に出す）。"""
    return (f'<section class="sec" id="hanasu">{note}<h2>考えを話す</h2>'
            '<p class="lead">仮説は、AI が考えたためしの案です。見て思った事を、話すか書いて残してください。合っているかどうかは見ません。思ったとおりに話してください。</p>'
            f'{box(sid, "think", hid=hypotheses.sheet_of(sid)["id"])}'
            # 玩具の頁を開いた時は作り始め（声とカメラの区切りの回の印・統括の決め 11-08・web.clips の openedAs の toy）。のこす から戻った時は引き継ぐ
            f'<script>addEventListener("DOMContentLoaded",()=>{{if(window.utsushiClips)setTimeout(()=>utsushiClips.openedAs({json.dumps(sid)},"toy").catch(()=>{{}}))}})</script></section>')


def craft_box(sid, hid, version, step):
    """作りながら見る頁の口（2 作りながら、工夫を話す）。今の手順の番号に結ぶ。"""
    return box(sid, "craft", hid=hid, version=version, step=step)


def kufu_block(sid, r, show_shared=True):
    """記録の札に出す「工夫した所（直した所）」。記録の欄に書いた直した点（部品・変えた事・結果）だけを並べる。
    話した字（作りながら話した工夫・上げた後に足した字・仮説を見て話した考え）は、記録に結んでいても出さない（本人の決定 11-06、J-034:
    頁に出す字は AI が整理した字だけ。話した字は作る側だけが読む）。整理した字の置き場ができたら、ここにその字を足す。
    show_shared=False は合言葉なしで開いた場で、節ごと出さない（人の書いた文を出さない。J-028 の線）。1 件も無い記録にも、何も出さない。
    学ぶ人の頁とギャラリーが記録の札を作る時も、この関数を呼べる。"""
    typed = [f'{f["part"]} / {f["change"]} / {f["outcome"]}' for f in r.get("fixes") or []
             if isinstance(f, dict) and all(str(f.get(k, "")).strip() for k in ("part", "change", "outcome"))]
    # talk_log.kufu をここで読まない。読むと、作る側が隠していない字が全部、学ぶ人の頁に出る（11-05 の形）。
    texts = typed
    if not (texts and show_shared):
        return ""
    lines = "".join(f"<li>{esc(x)}</li>" for x in texts)
    return f'<div class="hanasu-kufu" data-kufu="{esc(r["id"])}"><p class="hanasu-kufu-head">{esc(KUFU_HEAD)}</p><ul>{lines}</ul></div>'


def keep_box(sid, r, show_shared=True, can_add=False):
    """手帖の記録の札に置く物（3 できた物を上げた後に、工夫した所と考えを残す）。上に、その記録の「工夫した所（直した所）」
    （記録の欄に書いた直した点。話した字は出さない。J-034）。下に、足す口（足した字は記録に結び、輪の材料になる）。show_shared=False は合言葉なしで開いた場。
    can_add は、この画面がこの記録を残した時に真。足す口はその画面にだけ出す（受け口の post も断る）。"""
    return kufu_block(sid, r, show_shared) + (box(sid, "keep", rid=r["id"], with_assets=False) if can_add else "")


def reason(failures):
    """残せなかった理由を、学ぶ人の言葉にする。言うのは採られた文だけ（記録が消えた時などの文は、本人の確認の後に足す）。
    字が空の時は、前は「聞き取れませんでした。…」（NOHEARD）だった。この頁が声を聞かなくなって本当でないので、受け口の断りの字（REFUSED）にする
    （台本のある画面は空の字を送らず、ここに来るのは台本の無い画面で空白だけを送った時だけ）。"""
    f = failures[0]
    if f.floor == "F10.pii":
        return BLOCKED
    return REFUSED if f.message == talk_log.EMPTY else FAILED


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
        back = (f"/toy/{sid}/techo/kiroku#mine", "手帖をひらく（作りながら聞く・上げる）")
    return handler._send(200 if kept else 403 if refused else 422, skin.notice("残しました" if kept else "残せませんでした", KEPT if kept else REFUSED if refused else reason(failures), handler._look, links=(back,)))


def maker_section(sid, data):
    """作る側の頁（/loop/<印>）の節。話した事を場面ごとに並べる。字だけで、多い順や点にしない（J-025）。学ぶ人の頁には出さない。"""
    sm = talk_log.summary(sid)
    letter = {h["id"]: hypotheses.letter(h) for h in data["hypotheses"]}
    # 仮説の印（A・C）は出さない（本人の答え 11-08「そろえる。」（つくるの外も印なし）・hypotheses.SHOWN）
    paper = lambda hid: f"{hypotheses.SHOWN}の紙" if hid in letter else (f"自分の仮説 {hid} の紙" if hid else "紙を選ばず")
    none = '<p class="meta">残した言葉はまだありません。</p>'
    lines = lambda items: "<ul>" + "".join(f"<li>{esc(x)}</li>" for x in items) + "</ul>" if items else none
    think = lines([f'{hypotheses.SHOWN if t["hypothesis_id"] in letter else "仮説を選ばず"}: {t["text"]}' for t in sm["think"]])
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
            # 前の「声から字にした物 n 件・字で書いた物 n 件」は外した（この頁が声を字にしなくなり、どの字も欄に打った字になったため。前の記録の via は talk_log に残る）
            f'<p class="meta">床で落とした物（文は残していません）: 連絡先の形 {d["pii"]} 件・名乗りや学校の形 {d["name"]} 件。</p></section>')
