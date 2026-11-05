"""話す口（一周の声の部分。本人の決定 2026-11-05、Issue #279）。

本人の描く一周の 3 つの場面に、同じ部品を置く: 1 仮説を見て考えを話す（玩具の頁）・2 作りながら工夫を話す（作りながら見る頁）・
3 できた物を上げた後に工夫と考えを残す（手帖の記録の札）。残す先は omochae.talk_log（字だけ）。

判断の芯:
- **声そのものは残さない（本人の決定）。** この頁は、マイクを開く code・録る code・声を送る code を持たない（tests/test_hanasu.py が固定する）。
  声を字にするのはブラウザの音声認識で、頁が受け取るのは字だけ。受け口は字のフォームしか受けない（play_server の _form）。
- **端末の中だけで字にする（既定）。** ブラウザの音声認識は、既定では声を認識のサービスへ送って字にする（MDN の Web Speech API の頁で確かめた）。
  端末の中だけで字にする指定（processLocally）を持つ画面でだけ、話す釦を出す。日本語で使えるかは、釦を押した時にブラウザへ聞き
  （available）、使えなければ釦をしまう。無い画面では釦を出さず、字の欄だけにする（キーボードの音声入力は使える。頁は声に触らない）。対応は、調べた時点でパソコンの Chrome と Edge、Firefox の新しい版。
  iPhone と iPad の Safari には無い。そこで声の釦を出すかは本人が決める事なので、切り替え（OMOCHAE_VOICE）にした。
  local（既定）・browser（端末の中でできない画面では、ブラウザの既定の音声認識を使う。断りの文が変わる）・off（釦を出さない）。
- **字は本人が見てから残す。** 聞き取った字は欄に足すだけで、送らない。「残す」を押した時に送る。なぜ: 名前は機械で見分けられない
  （talk_log の床の限り）ので、人の目を入口に置く。聞き違いも直せる。話し終えたら自動で残す形は、手は空くが、この目が無くなるので採らない。
- 床に落ちた時は、欄の字を消さずに理由を返す（直して残せる）。JS が無い時は、理由の頁を返す。
- JS が無くても字で残せる（フォームの送信）。JS がある時は頁を読み直さない（作りながら見る頁の鏡と手順が切れないように）。
- 釦と断りの出し分けは CSS で持つ（html に付く印）。手帖は記録の一覧を頁の中で入れ替えるので、後から来た部品にも同じ出し分けが効くように。
  同じ理由で、釦の動きは頁に 1 回だけ置く script が、頁全体で受ける。
- 聞く口の声（手帖・作りながら見る頁の #mic）と同時には聞かない。片方を押したら、もう片方を止める。読み上げの間に入った字は捨てる
  （端末が自分の答えを聞いた物なので）。
- **作りながら話した工夫は、そのまま記録の「工夫した所（直した所）」に入る（本人の設計）。** 記録を残した時に、同じ画面（その場限りの印）で、
  同じ紙について話した工夫を、その記録に結ぶ（talk_log.bind。play_server の記録を残す口が呼ぶ）。上げた後に書き直さなくてよい。
  手帖の記録の札は「工夫した所（直した所）」を出し、その下の口で足せる。
- 1 の字は学ぶ人の頁に出さない（作る側の頁だけ）。2 と 3 の字は、本人が「ほかの人に見せてよい」を選んだ物だけを記録の札に出す。
  選んでいない物は、件数だけを出す（記録に入った事は分かるが、文は作る側だけが読む）。
  合言葉なしで開いたデモでは、文は出さない（文の中の名前は機械で落とせないため。J-028 と同じ線）。
"""
import json
import os
import urllib.parse

from omochae import hypotheses, making_log, talk_log
from omochae.model import Failure

from . import skin
from .play_server import esc, printed_versions, sheet_version_of

MODES = ("local", "browser", "off")

# 断りの文。どの場面でも同じ物を出す。名前は床で落とせない（落とせるのは形だけ）ので、入れないお願いを添える。
NOTICE = "残すのは字だけです。声は録らず、送りません。字は、残す前に見て直せます。名前、学校の名前、連絡先は入れないでください。"
HOW_LOCAL = "話す釦を押すと、声はこの端末の中で字になります。"
HOW_BROWSER = "話す釦を押すと、声はブラウザの音声認識で字になります（ブラウザの会社の仕組みへ送られる事があります）。この頁は声を受け取りません。"
HOW_NONE = "この画面は、声を端末の中だけで字にできないので、話す釦を出していません。キーボードの音声入力を使うと、欄に字が入ります（声の扱いは機器の設定によります）。"

SCENES = {
    "think": {"head": "考えを話す", "hint": "こう動くと思う、ここが気になる、など"},
    "craft": {"head": "工夫を話す", "hint": "ここをこう工夫した、など"},
    "keep": {"head": "工夫した所や考えを足す", "hint": "工夫した所、考えた事"},
}
# 記録の札の節の名前。本人の言葉「工夫した所（直した所）」のまま。
KUFU_HEAD = "工夫した所（直した所）"
SHARE = {"craft": "記録に入った時に、ほかの人に見せてよい（選ばなければ、作る側だけが読みます）",
         "keep": "ほかの人に見せてよい（選ばなければ、作る側だけが読みます）"}
KEPT = "残しました。型紙と案内を直す材料にします。"
# 作りながら話した工夫は、記録を残した時にその記録に入る。入るのは、画面がその場限りの印を持つ時だけなので、印が無い時はこの文を出さない。
KEPT_CRAFT = f"残しました。記録を残すと、その記録の「{KUFU_HEAD}」に入ります。"
KEPT_SHARED = "残しました。ほかの人にも見せます。"
KEPT_PRIVATE = "残しました。ほかの人には見せません。"

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
/* 選ぶ欄は、字の行ごと押せる高さにする。四角は、字が折り返す幅でも縮めない。 */
.hanasu .hanasu-share{display:flex;gap:8px;align-items:center;min-height:44px;font-size:14px;line-height:1.5}
.hanasu .hanasu-share input{flex:0 0 22px;width:22px;height:22px;margin:0}
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
# 端末の中だけの指定を付けない聞き方（ブラウザの既定。声が外へ送られる事がある）は、切り替えが browser の時だけ使う。
# 聞き取った字は欄に足すだけ。送るのは「残す」を押した時（submit）。
SCRIPT = """<script>(()=>{
const REC=window.SpeechRecognition||window.webkitSpeechRecognition,LANG='ja-JP',html=document.documentElement;
const M={listening:'聞いています。話した事が、欄に字で出ます。',heard:'字にしました。見て、よければ「残す」を押します。',sending:'残しています…',kept:'残しました。',
 failed:'残せませんでした。つながりを見て、もう一度押してください。',nolang:'この端末の中では字にできませんでした。字で書けます。',
 noheard:'聞き取れませんでした。もう一度押すか、字で書けます。',install:'この端末の中で字にする仕組みを入れています（初めの 1 回だけ）…',
 tobrowser:'この端末の中では字にできません。もう一度押すと、ブラウザの音声認識で字にします（声がブラウザの会社の仕組みへ送られる事があります）。'};
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
 const box=root.querySelector('textarea'),mic=root.querySelector('.hanasu-mic'),r=new REC();
 r.lang=LANG;r.continuous=true;r.interimResults=false;if(onDevice)r.processLocally=true;
 r.onresult=(ev)=>{
  // 読み上げの間に入った字は、端末が自分の答えを聞いた物なので入れない。
  if(window.speechSynthesis&&speechSynthesis.speaking)return;
  for(let i=ev.resultIndex;i<ev.results.length;i++){if(!ev.results[i].isFinal)continue;const t=ev.results[i][0].transcript.trim();
   if(t){box.value=(box.value?box.value+' ':'')+t;root.dataset.via='voice';note(root,M.heard)}}};
 r.onerror=(ev)=>{note(root,ev.error==='language-not-supported'?M.nolang:M.noheard)};
 r.onend=()=>{press(mic,false);if(rec===r)rec=null};
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
 go.disabled=true;note(root,M.sending);let j={};
 try{const r=await fetch(form.action,{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:b});j=await r.json()}catch(e3){j={}}
 go.disabled=false;
 if(j.kept){const li=document.createElement('li');li.textContent=text;root.querySelector('.hanasu-said').append(li);box.value='';root.dataset.via='';note(root,j.note||M.kept)}
 else note(root,j.why||M.failed)});
addEventListener('pagehide',stop);
})()</script>"""

def mode():
    """声の釦の出し方。既定は local（端末の中だけで字にできる画面でだけ出す）。決まりの外の値は local に戻す。"""
    m = os.environ.get("OMOCHAE_VOICE", "local")
    return m if m in MODES else "local"


def assets():
    """頁に 1 回だけ置く物（見た目と動き）。部品を何個置いても 1 つでよい。声の釦の出し方（mode）は、ここで script に渡す:
    手帖は記録の一覧を後から入れ替えるので、頁を開いた時に部品が 1 つも無くても、後から来た部品が同じ出し方になるように。"""
    return f"<style>{STYLE}</style>" + SCRIPT.replace("__VOICE__", mode())


def box(sid, scene, hid="", version=None, step=None, rid="", hyps=(), with_assets=True):
    """話す口 1 つ。hyps は 1（考え）で選べる仮説の (id, 字) の並び。with_assets=False は、同じ頁に何個も置く時（手帖）に、頁の側が assets() を 1 回置く形。"""
    s = SCENES[scene]
    key = esc(f"hn-{scene}-{rid}" if rid else f"hn-{scene}")
    hidden = f'<input type="hidden" name="scene" value="{esc(scene)}">'
    if scene == "think":
        opts = '<option value="">どの仮説についてか（選ばなくてもよい）</option>' + "".join(f'<option value="{esc(i)}">仮説 {esc(n)}</option>' for i, n in hyps)
        hidden += f'<label class="sr" for="{key}-h">どの仮説についてか</label><select id="{key}-h" name="hypothesis">{opts}</select>'
    elif scene == "craft":
        hidden += (f'<input type="hidden" name="hypothesis" value="{esc(hid)}"><input type="hidden" name="sheet_version" value="{esc(version)}">'
                   f'<input type="hidden" name="step" value="{esc(step)}">')
    else:
        hidden += f'<input type="hidden" name="record" value="{esc(rid)}">'
    # 見せてよいかは、話した本人がその場で選ぶ（既定は見せない）。1 の考えは記録に入らないので、選ぶ欄を出さない。
    share = f'<label class="hanasu-share"><input type="checkbox" name="share" value="1"> {esc(SHARE[scene])}</label>' if scene in SHARE else ""
    how = (f'<span class="hanasu-how is-local">{esc(HOW_LOCAL)}</span><span class="hanasu-how is-browser">{esc(HOW_BROWSER)}</span>'
           f'<span class="hanasu-how is-none">{esc(HOW_NONE)}</span>')
    # 玩具の頁の口は、JS が無い時に同じ節へ着く（返事の文もそこに出る。#121 と同じ形）。ほかの 2 つは、戻る道の付いた頁で答える。
    land = "#hanasu" if scene == "think" else ""
    return (f'<div class="hanasu" data-hanasu data-voice="{mode()}"><p class="hanasu-head">{esc(s["head"])}</p>'
            f'<form method="post" action="/toy/{esc(sid)}/talk{land}">{hidden}'
            f'<label class="sr" for="{key}">{esc(s["head"])}</label><textarea id="{key}" name="text" maxlength="{talk_log.MAX_TEXT}" placeholder="{esc(s["hint"])}" required></textarea>'
            f'{share}<div class="hanasu-row"><button type="button" class="hanasu-mic" aria-pressed="false" aria-label="話す（もう一度押すと止まる）" hidden>話す</button>'
            '<button class="hanasu-go">残す</button></div></form>'
            '<p class="hanasu-note" aria-live="polite"></p><ul class="hanasu-said" aria-label="この頁で残した言葉"></ul>'
            f'<p class="meta">{esc(NOTICE)}{how}</p></div>' + (assets() if with_assets else ""))


def think_section(sid, data, note=""):
    """玩具の頁の節（1 仮説を見て、考えを話す）。仮説の札のすぐ後に置く。note は、JS が無い時に送った後の返事の文（着いたこの節の頭に出す）。"""
    hyps = [(h["id"], hypotheses.letter(h)) for h in data["hypotheses"]]
    return (f'<section class="sec" id="hanasu">{note}<h2>考えを話す</h2>'
            '<p class="lead">仮説は AI が考えた案です。見て思った事を、話すか書いて残します。合っているかは見ません。</p>'
            f'{box(sid, "think", hyps=hyps)}</section>')


def craft_box(sid, hid, version, step):
    """作りながら見る頁の口（2 作りながら、工夫を話す）。今の手順の番号に結ぶ。"""
    return box(sid, "craft", hid=hid, version=version, step=step)


def kufu_block(sid, r, show_shared=True):
    """記録の札に出す「工夫した所（直した所）」。1 つの節に並べる: 記録の欄に書いた直した点（部品・変えた事・結果）、
    作りながら話した工夫（手順の番号つき）、上げた後に残した字。
    話した字は、本人が見せてよいと選んだ物だけを文で出し、ほかは件数だけ。記録の欄の直した点は、記録の中身なので文で出す。
    show_shared=False は合言葉なしで開いた場（人の書いた文を出さず、件数だけ）。1 件も無い記録には、何も出さない。
    学ぶ人の頁とギャラリーが記録の札を作る時も、この関数を呼べる。"""
    typed = [f'{f["part"]} / {f["change"]} / {f["outcome"]}' for f in r.get("fixes") or []
             if isinstance(f, dict) and all(str(f.get(k, "")).strip() for k in ("part", "change", "outcome"))]
    items = talk_log.kufu(sid, r["id"])
    if not (typed or items):
        return ""
    step = lambda k: f"手順 {k['step']}: " if k["step"] else ""
    shown = typed + [step(k) + k["text"] for k in items if k["share"]] if show_shared else []
    lines = "".join(f"<li>{esc(x)}</li>" for x in shown)
    rest = len(typed) + len(items) - len(shown)
    why = "作る側だけが読みます" if show_shared else "公開のデモでは、文を出しません"
    more = f'<p class="meta">{"ほかに " if shown else ""}{rest} 件（{why}）</p>' if rest else ""
    return f'<div class="hanasu-kufu"><p class="hanasu-kufu-head">{esc(KUFU_HEAD)}</p>{f"<ul>{lines}</ul>" if lines else ""}{more}</div>'


def keep_box(sid, r, show_shared=True):
    """手帖の記録の札に置く物（3 できた物を上げた後に、工夫した所と考えを残す）。上に、その記録の「工夫した所（直した所）」
    （作りながら話した工夫が、記録を残した時にここへ入る）。下に、足す口。"""
    return kufu_block(sid, r, show_shared) + box(sid, "keep", rid=r["id"], with_assets=False)


def reason(failures):
    """残せなかった理由を、学ぶ人の言葉にする。床に落ちた時は、何の形かと、直せば残せる事を言う。"""
    f = failures[0]
    if f.floor == "F10.pii":
        return f"{f.message}ので、残しませんでした。その所を消すと残せます。"
    if f.message == talk_log.EMPTY:
        return "話した事を、話すか書いてください。"
    if f.where == "record_id":
        return "記録が見つかりません。頁を開き直してください。"
    if f.where == "hypothesis_id":
        return "紙が見つかりません。頁を開き直してください。"
    return "残せませんでした。もう一度押してください。"


def post(handler, sid, form):
    """話す口の受け口（/toy/<印>/talk）。字のフォームだけがここに届く（play_server の _form が、ほかの形・別の出所・大きすぎる本体を断る）。
    JS からは JSON で答え、JS が無い時は頁で答える。戻り先は場面から作る（送られた値を戻り先にしない）。"""
    scene, hid = form.get("scene", ""), form.get("hypothesis", "")
    version = step = None
    failures = []
    if scene == "craft":
        if not printed_versions(sid, hid):
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
    share = form.get("share") == "1"
    who = form.get("who", "")
    path = None
    if not failures:
        path, failures = talk_log.add(sid, scene, form.get("text", ""), hypothesis_id=hid or None, sheet_version=version, step=step,
                                      record_id=form.get("record") or None, via=form.get("via", "text"), share=share, who=who)
    kept = path is not None
    said = (KEPT_SHARED if share else KEPT_PRIVATE) if scene == "keep" else KEPT_CRAFT if scene == "craft" and making_log.clean_who(who) else KEPT
    if form.get("json") == "1":
        body = {"kept": True, "note": said} if kept else {"kept": False, "why": reason(failures)}
        return handler._send(200 if kept else 422, json.dumps(body, ensure_ascii=False), "application/json; charset=utf-8")
    if scene == "think":
        if kept:
            return handler._send(303, "", headers=[("Location", f"/toy/{sid}?msg={urllib.parse.quote(said)}&at=hanasu#hanasu")])
        return handler._send(422, handler._toy(sid, errors=[reason(failures)], at="hanasu"))
    if scene == "craft" and version:
        back = (f"/toy/{sid}/tsukuru?h={urllib.parse.quote(hid)}&v={version}&n={step or 1}", "作りながら見る頁へ戻る")
    elif scene == "keep":
        back = (f"/toy/{sid}/techo#mine", "手帖へ戻る")
    else:
        back = (f"/toy/{sid}", "玩具の頁へ戻る")
    return handler._send(200 if kept else 422, skin.notice("残しました" if kept else "残せませんでした", said if kept else reason(failures), handler._look, links=(back,)))


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
    when = lambda k: (f"手順 {k['step']}" if k["step"] else "作りながら") if k["when"] == "making" else "上げた後"
    keep = "".join(f'<h4>{esc(r["record_id"])}（{esc(paper(r["hypothesis_id"]))}・版 {esc(r["sheet_version"])}）</h4>'
                   + lines([f'{when(k)}: {k["text"]}{"［見せてよい］" if k["share"] else ""}' for k in r["kufu"]]) for r in sm["records"]) or none
    d = sm["dropped"]
    return ('<section class="sec" id="k7"><h2>7 話した事</h2>'
            '<p class="meta">話すか書いて残した言葉を、場面ごとに並べます。残っているのは字だけで、声は残していません。'
            '名前は機械では見分けられないので、読む時に気づいたら消します。</p>'
            f'<h3>仮説を見て話した考え</h3>{think}<h3>作りながら話した工夫（手順ごと）</h3>{craft}<h3>記録の「{esc(KUFU_HEAD)}」</h3>'
            '<p class="meta">作りながら話した工夫は、記録を残した時にその記録に入ります。上げた後に足した言葉も、ここに並びます。</p>'
            f'{keep}'
            f'<p class="meta">声から字にした物 {sm["via"]["voice"]} 件・字で書いた物 {sm["via"]["text"]} 件。'
            f'床で落とした物（文は残していません）: 連絡先の形 {d["pii"]} 件・名乗りや学校の形 {d["name"]} 件。</p></section>')
