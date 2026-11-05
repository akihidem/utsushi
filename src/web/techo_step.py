"""工作の手帖の 1 手 1 画面（本人の決定 11-05「案 A で進める。手順の絵は段 1 から」、Issue #87）。

本人の感想: 「子供が手元で触る前提。文字情報がおおい。声で操作できなさそう。AIの考えたUiって感じ」。
前の頁は最初の画面に字が約 11 個あり、絵が 0 で、次に押す所が 1 つに決まらなかった（390px の幅で数えた）。

判断の芯:
- **今の手順の絵と 1 文だけ。** 一番大きい物は絵で、画面の高さの半分以上。押す所は 1 画面に 3 つまで（閉じる印とマイクを除く）。字を読まずに絵と形で進める。
- **押す所の名前は本人が決めた 6 つ（NAMES）。** 一字も変えない（tests/test_techo_step.py が文字列で見る）。結果の札だけは別で、記録の値（凍結の床 F3 の語）の字を絵に添える:
  「よく動いた」と「少し動いた」のように、絵だけでは取り違えて記録が濁るため。既定の選びは置かない。
- **頁の帯を置かない。** 帯の字だけで字のかたまりが 6 個増えるため。閉じる印で玩具の頁へ戻る（作りながら見る頁と同じ形）。
- **紙を選ぶ札は作らない。** 型紙は玩具ごとに 1 枚で、たたき台は記録の先頭（#332）。作る紙を頁が決める。
- **絵は手順の紙と同じ形から描く（instructions.step_pictures）。** 字を入れず、紙と食い違わず、刷った PNG を切らないので小さなコマを大きくしても粗くならない。
- **記録の札（試した後の紙 → 説明 → AI）はこの頁に置かない。** 頁の字に版の名・記録の番号・「の紙」を出さないため。のこした後に手帖の記録の頁（techo_site.records_page）へ移る。順（J-013・S-03）は変えない。
- **声は全部が一致した時だけ操作にする。** 「次の手順ってどうやるの」で進まないように、部分一致を使わない。操作の字は送らず残さない。ほかの字は質問として扱い、最後の画面では工夫の欄に入れる。
- **声を字にする所は話す口（hanasu）の切り替えのまま。** OMOCHAE_VOICE の browser（既定）・local・off を読み、どちらにも切り替えられる形を保つ（本人の決定待ち）。local と browser の見分けは hanasu.SCRIPT と同じ式。
  hanasu の部品は置かない: 話す釦と残す釦が増え、マイクが 1 頁に 2 つになるため。声そのものは録らず、受け取らない（マイクを開く code と録る code を持たない）。
- **工夫の字は「のこす」で送る。** 話す口の決まり「字は本人が見てから残す」を、この頁でも守る。先に床（talk_log）に通し、落ちたら記録を作らず、字を残して理由を見せる（押し直しで記録を増やさない。#143）。
- **「もう一回」は今の手順の文を読み上げる。** 手順ごとに自動で読まない: 教室で 30 台が同時に読むと、紙の返事を聞く場が濁るため。
- **「とって」は外のカメラを求める（capture="environment"）。** 顔を写さない線のため。写真を選んだ時は前と同じ確かめ（大人の手元だけ・顔なし・声なし）を通す。
- 手順の文は雛形の steps のまま（tsukuru.step_texts。紙と画面で言う事を変えない）。札を押した事は作りながら見る頁と同じ口（/toy/<印>/step）に残す。
- 祝う演出と順位の言葉は入れない（J-025）。JS が無い時は、つぎ・もどるがリンクとして手順を送る。
"""
import json
import re

from omochae import hypotheses, instructions, loop, making_log, render, talk_log
from omochae.compose import TEMPLATES

from . import hanasu, skin, tsukuru
from .play_server import esc, printed_versions
from .techo_site import ICONS, MAX_MEDIA, MAX_PER_RECORD

# 本人の決定 11-05: 押す所の名前。字を変える時は本人の確認が要る。
NAMES = ("つぎ", "もどる", "こまった", "とって", "のこす", "はじめる")
NEXT, BACK, STUCK, SHOOT, KEEP, START = NAMES

# 声の操作。全部が一致した時だけ操作にする（CLEAN で空白と句読点を除いた後の字）。認識は漢字で返す事が多いので両方を持つ。
WORDS = {"つぎ": "next", "次": "next", "つぎへ": "next", "次へ": "next", "できた": "next", "出来た": "next",
         "もどる": "back", "戻る": "back", "もう一回": "again", "もういっかい": "again", "もう1回": "again", "もう１回": "again",
         "こまった": "stuck", "困った": "stuck", "とって": "photo", "撮って": "photo", "取って": "photo", "のこす": "keep", "残す": "keep"}
CLEAN = r"[\s。、．，！？!?…・]"
# 結果の札を声で選ぶ言い方。値は雛形の RESULTS のまま（凍結の床 F3 の語）。
RESULT_WORDS = {r: r for tpl in TEMPLATES.values() for r in tpl.RESULTS} | {
    "うごいた": "動いた", "うごかない": "動かない", "分からない": "わからない", "ゆれた": "揺れた", "ゆれない": "揺れない", "もどった": "戻った", "もどらない": "戻らない",
    "なった": "鳴った", "ならない": "鳴らない", "まわった": "回った", "まわらない": "回らない", "たった": "立った", "たおれた": "倒れた", "あそべた": "遊べた",
    "すこしあそべた": "少し遊べた", "あそべない": "遊べない", "よくうごいた": "よく動いた", "すこしうごいた": "少し動いた", "ころがった": "転がった", "ころがらない": "転がらない"}

# hanasu.SCRIPT の M と同じ文。声を字にするしくみを機械に入れている間の知らせ。
INSTALL = "声を字にするしくみを、この機械に入れています（はじめの 1 回だけ）…"

_ICON = '<svg viewBox="0 0 48 48" aria-hidden="true">{}</svg>'
KEY_ICONS = {
    START: _ICON.format('<path d="M15 9l24 15-24 15z"/>'),
    BACK: _ICON.format('<path d="M30 9L13 24l17 15"/>'),
    NEXT: _ICON.format('<path d="M18 9l17 15-17 15"/>'),
    STUCK: _ICON.format('<path d="M16 17a8 8 0 1 1 11 8c-2 1-3 2-3 6"/><circle cx="24" cy="39" r="1.5"/>'),
    SHOOT: _ICON.format('<path d="M6 16h8l4-6h12l4 6h8v24H6z"/><circle cx="24" cy="27" r="8"/>'),
    KEEP: _ICON.format('<path d="M24 7v22M14 20l10 10 10-10M8 40h32"/>'),
}
MIC = _ICON.format('<rect x="17" y="6" width="14" height="24" rx="7"/><path d="M10 22a14 14 0 0 0 28 0M24 36v6"/>')
CLOSE = _ICON.format('<path d="M12 12l24 24M36 12L12 36"/>')
SEND = _ICON.format('<path d="M10 24h26M26 12l12 12-12 12"/>')
_SMALL = _ICON.format('<path d="M14 30c5 0 9-3 12-9M20 19l6 2 1 6"/>')


def result_icon(r):
    """結果の札の絵。良し悪しに見えない線だけで、色を付けない。手順の紙の値は雛形ごとに違うので、手帖の絵（techo_site.ICONS）に無い値は形で寄せる。"""
    if r in ICONS:
        return ICONS[r]
    if r.endswith("ない") or r == "倒れた":
        return ICONS["動かない"]
    return _SMALL if r.startswith("少し") else ICONS["動いた"]


# 色は皮の変数から取る（skin.py）。絵の地だけ白に決める: 手順の紙の形は黒い線と紙の色で描いてあり、黒の皮でもそのまま読めるように（作りながら見る頁の紙の絵と同じ）。
# 字の大きさは机の端に置いて少し離れて読むため。角丸の箱を並べない（本人の感想「AIの考えたUiって感じ」）。
STYLE = """
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--fg);font-family:"Noto Sans CJK JP","Noto Sans JP","Hiragino Sans","Yu Gothic",sans-serif;font-size:18px;line-height:1.5}
a{color:inherit;text-decoration:none}
.sr{position:absolute;left:-9999px}
/* 指で触る機器の床（skin.TAP_FLOOR）が button を横並びの箱にするので、hidden を効かせる。 */
[hidden]{display:none!important}
/* 余りの高さは絵に回す。押す所は画面の下に寄る（親指が届く所。作っている手を離さず押せるように）。 */
.te{position:relative;min-height:100vh;min-height:100svh;max-width:820px;margin:0 auto;display:flex;flex-direction:column}
/* 場面ごとに出す物を data-on で決める。JS は場面の名前を替えるだけ。 */
.te[data-scene=start] [data-on]:not([data-on~=start]),.te[data-scene=step] [data-on]:not([data-on~=step]),.te[data-scene=henji] [data-on]:not([data-on~=henji]),
.te[data-scene=end] [data-on]:not([data-on~=end]),.te[data-scene=kekka] [data-on]:not([data-on~=kekka]){display:none!important}
.bar{position:absolute;top:0;left:0;right:0;height:6px;background:var(--rule);z-index:2}
.bar span{display:block;height:100%;background:var(--accent)}
.koma{flex:1 0 auto;position:relative;min-height:50vh;min-height:50svh;margin:0;background:#fff}
.koma svg{display:none}
.koma svg.on{display:block;position:absolute;left:12px;top:84px;width:calc(100% - 24px);height:calc(100% - 94px)}
#steps{list-style:none;margin:0;padding:12px 16px 6px;font-size:clamp(22px,5.6vw,32px);line-height:1.4;font-weight:600}
.meta{margin:0;font-size:13px;color:var(--mute);line-height:1.7}
#start-note{padding:6px 16px}
#note{padding:0 16px}
#note:empty{display:none}
.how{display:none}
.te-local .how.is-local,.te-browser .how.is-browser{display:inline}
.keys{display:grid;grid-template-columns:1fr 1.5fr 1fr;gap:8px;padding:8px 12px calc(12px + env(safe-area-inset-bottom,0px))}
.key{min-height:64px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2px;margin:0;padding:6px;font:inherit;font-size:18px;font-weight:600;text-align:center;border:2px solid var(--accent);border-radius:0;background:var(--paper);color:var(--fg);cursor:pointer;position:relative}
.key.go{min-height:96px;background:var(--accent);color:var(--onaccent);font-size:26px}
.key[aria-disabled=true]{opacity:.45}
.key svg,.send svg,.mic svg,.close svg,.tile svg{stroke:currentColor;fill:none;stroke-width:3.5;stroke-linecap:round;stroke-linejoin:round}
.key svg{width:32px;height:32px}
.key.go svg{width:36px;height:36px}
#start{grid-column:1/-1}
.mic{position:absolute;top:12px;left:12px;width:72px;height:72px;display:grid;place-items:center;padding:0;margin:0;border:2px solid var(--accent);border-radius:50%;background:var(--paper);color:var(--accent);cursor:pointer;z-index:3}
.mic svg{width:40px;height:40px}
/* 聞いている間は地と字を入れ替える。別の色を足さず、どちらの皮でも「今は違う状態」と読めるようにする。 */
.mic[aria-pressed=true]{background:var(--accent);color:var(--onaccent)}
.close{position:absolute;top:12px;right:12px;width:64px;height:64px;display:grid;place-items:center;border:2px solid var(--frame);background:var(--paper);color:var(--fg);z-index:3}
.close svg{width:32px;height:32px}
.henji{padding:10px 12px 16px;display:grid;gap:10px}
#ask-form{display:flex;gap:8px;margin:0}
#q{flex:1;min-width:0;min-height:64px;margin:0;padding:10px 12px;font:inherit;font-size:20px;border:2px solid var(--frame);border-radius:0;background:var(--field);color:var(--fg)}
.send{width:76px;min-height:64px;display:grid;place-items:center;padding:0;margin:0;border:0;border-radius:0;background:var(--accent);color:var(--onaccent);cursor:pointer}
.send svg{width:34px;height:34px}
.answer{font-size:24px;line-height:1.5;white-space:pre-wrap;min-height:1.5em}
.answer:empty::before{content:"ここに答えが出ます";font-size:14px;color:var(--mute)}
.end{padding:92px 12px 16px;display:grid;gap:10px}
.end form{display:grid;gap:10px;margin:0}
.key.shot{min-height:38vh;min-height:38svh;border:3px dashed var(--accent);background:transparent;font-size:24px}
.key.shot svg{width:72px;height:72px}
.shot input{position:absolute;opacity:0;width:1px;height:1px;pointer-events:none}
.thumbs{display:flex;flex-wrap:wrap;justify-content:center;gap:8px}
.thumbs:empty,.picked:empty{display:none}
.thumbs img,.thumbs video{width:30vw;max-width:180px;height:30vw;max-height:180px;object-fit:cover}
.picked{font-size:15px;font-weight:400}
#kufu{display:block;width:100%;min-height:76px;margin:0;padding:10px 12px;font:inherit;font-size:18px;border:1px solid var(--frame);border-radius:0;background:var(--field);color:var(--fg)}
.te .check{display:flex;align-items:center;gap:12px;min-height:64px;padding:8px 12px;margin:0;font-size:16px;border:1px solid var(--frame)}
.check input{width:32px;height:32px;flex:none;margin:0}
.te:not(.picked) .check,.te.picked #endback{display:none}
.end .keys{grid-template-columns:1fr 2fr;padding:0}
.te.picked .end .keys{grid-template-columns:1fr}
.call{outline:4px solid var(--accent);outline-offset:2px}
#up-status{font-size:16px;margin:0}
#up-status:empty{display:none}
.kekka{padding:92px 12px 16px;display:grid;gap:12px;align-content:start}
/* 結果の札は同じ大きさ（小さくすると、選ぶのをためらわせるため。手順の紙の欄と同じ考え）。色で良し悪しを付けない。 */
.tile{min-height:96px;display:flex;align-items:center;justify-content:center;gap:14px;margin:0;padding:10px;font:inherit;font-size:24px;border:2px solid var(--frame);border-radius:0;background:var(--paper);color:var(--fg);cursor:pointer}
.tile svg{width:56px;height:56px}
/* 横置き（机の端に立てたタブレット）: 左に絵、右に文と押す所。 */
@media (min-width:860px) and (orientation:landscape){
 .te{display:grid;max-width:none;grid-template-columns:minmax(0,1.4fr) minmax(340px,1fr);grid-auto-rows:min-content;align-content:start}
 .koma{grid-row:1/span 8;min-height:100vh;min-height:100svh}
 .end,.kekka{grid-column:1/-1;max-width:820px;width:100%;margin:0 auto}
}
"""

# 読み上げの間は音声認識を止める: 止めないと端末が自分の声を聞き取り、問いとして送る（前の手帖と作りながら見る頁と同じ決まり）。
# 手順の番号は頁の中で持ち、札の送信の返事を待たない: 手がふさがっている時に画面の変わりを待たせないため。送れなくても手順は進む。
# 端末の中で字にする時は話し続け、ブラウザの既定の口は 1 回話すごとに止まる形で聞いて、止まったらまた聞く（話す口と同じ聞き方）。
SCRIPT = """<script>
(() => {
const te = document.getElementById('te'), sid = te.dataset.sid, hid = te.dataset.hid, ver = te.dataset.v, total = +te.dataset.total, want = te.dataset.voice;
const WORDS = __WORDS__, RESULT_WORDS = __RESULT_WORDS__;
const clean = (t) => t.replace(/__CLEAN__/g, '');
const $ = (id) => document.getElementById(id);
const items = [...document.querySelectorAll('#steps li')], koma = [...document.querySelectorAll('#koma svg')];
const mic = $('mic'), note = $('note'), ans = $('answer'), q = $('q'), kufu = $('kufu'), bar = $('bar');
let n = +te.dataset.n;
const scene = () => te.dataset.scene;
const to = (s) => { te.dataset.scene = s; };
// 版（開いた時に刷ってあった一番新しい版）と、その場限りの印（skin.WHO_SCRIPT が持つ）を、出来事に添える。
const extra = (o) => { const b = new URLSearchParams(o); b.set('sheet_version', ver); try { const w = sessionStorage.getItem('utsushi-who'); if (w) b.set('who', w); } catch (e) {} return b; };
const post = (path, o) => fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: extra(o) });
const send = (event) => { post(`/toy/${sid}/step`, { hypothesis: hid, step: Math.min(n, total), event, json: '1' }).catch(() => {}); };
const paint = () => {
  items.forEach((li, i) => { const on = i + 1 === n; li.hidden = !on; li.classList.toggle('on', on); });
  const k = n > total ? -1 : +items[n - 1].dataset.k;
  koma.forEach((s, i) => s.classList.toggle('on', i === k));
  bar.firstElementChild.style.width = `${Math.round(Math.min(n, total) / total * 100)}%`;
  bar.setAttribute('aria-valuenow', Math.min(n, total));
  $('back').href = `?v=${ver}&n=${Math.max(n - 1, 1)}`; $('next').href = `?v=${ver}&n=${n + 1}`;
  $('back').setAttribute('aria-disabled', n <= 1 ? 'true' : 'false');
  try { history.replaceState(null, '', `?v=${ver}&n=${n}`); } catch (e) {}
};
const goNext = () => {
  if (n > total) return;
  // 最後の手順の「つぎ」は組み上がりの知らせ。途中の手順では残さない。
  if (n === total) { send('done'); n = total + 1; paint(); to('end'); return; }
  send('next'); n += 1; paint(); to('step');
};
const goBack = () => {
  if (n > total) { n = total; paint(); to('step'); return; }
  if (n > 1) { send('back'); n -= 1; paint(); }
  to('step');
};
// 読み上げ。始まりと終わりで聞くのを止めて戻す。終わりの知らせが来ない機種があるので、長さから見た時間でも戻す。前の読み上げの取り消しの知らせで戻らないよう、番号で見分ける。
let sayStart = () => {}, sayEnd = () => {}, sayId = 0;
const say = (t) => { try { if (!('speechSynthesis' in window)) return; speechSynthesis.cancel(); const u = new SpeechSynthesisUtterance(t), id = ++sayId; u.lang = 'ja-JP';
  const fin = () => { if (id === sayId) sayEnd(); }; u.onend = fin; u.onerror = fin; setTimeout(fin, Math.min(60000, t.length * 400 + 3000)); sayStart(); speechSynthesis.speak(u); } catch (e) { sayEnd(); } };
const ask = async (t) => {
  if (!t) return;
  ans.textContent = '…';
  const r = await post(`/toy/${sid}/ask-json`, { hypothesis: hid, question: t, step: Math.min(n, total) }).catch(() => null);
  const j = r ? await r.json().catch(() => ({})) : {};
  const text = j.text || j.error || '今は答えられません';
  ans.textContent = text; say(text);
};
const openAsk = () => { send('stuck'); to('henji'); if (!listening) q.focus(); };
const act = (op) => {
  const s = scene();
  if (op === 'again') { if (n <= total) say(items[n - 1].textContent); return; }
  if (op === 'next') { if (s === 'step' || s === 'henji') goNext(); return; }
  if (op === 'back') { if (s === 'kekka') to('end'); else if (s === 'henji') to('step'); else goBack(); return; }
  if (op === 'stuck') { if (s === 'step') openAsk(); return; }
  if (op === 'photo') { if (s === 'end') shoot(); return; }
  if (op === 'keep') { if (s === 'end') keepPress(); }
};
// 聞いた字。全部が一致した時だけ操作にする。操作の字は送らず残さない。
const heard = (t) => {
  const s = scene();
  if (s === 'kekka') { const r = RESULT_WORDS[clean(t)]; if (r) { save(r); return; } }
  const op = WORDS[clean(t)];
  if (op) { act(op); return; }
  if (s === 'kekka') return;
  if (s === 'end') { kufu.value = (kufu.value ? `${kufu.value} ` : '') + t; kufu.dataset.via = 'voice'; return; }
  if (s === 'step') to('henji');
  q.value = t; ask(t);
};
// 声を字にする所。切り替えと見分けは話す口（hanasu.SCRIPT）と同じ。頁を開いた時にはブラウザへ聞かない（聞くだけで頁ごと落ちる画面があった）。人が押した時だけ聞く。
const REC = window.SpeechRecognition || window.webkitSpeechRecognition, LANG = 'ja-JP';
const feat = !!(REC&&typeof REC.available==='function'&&'processLocally' in REC.prototype);
let how = want === 'off' ? 'none' : feat ? 'local' : (want === 'browser' && REC) ? 'browser' : 'none';
let rec = null, listening = false, speaking = false, onDevice = false;
// 端末の中で字にできるかを聞くと、頁ごと落ちる画面がある（Chromium 156 の headless で確かめた。例外でなく頁が落ちるので受けられない）。
// 「はじめる」は全員が押す唯一の釦なので、開き直しても同じ所で止まらないよう、聞く前に印を置き、無事に済んだら消す。印が残っていれば端末の中の口を使えない物として扱う。
// 印は機器の事だけで、人を指さない（英数字の印とは別物）。残せない画面では、印なしで今までどおり。
const CHECKING = 'utsushi-voice-local-check';
const mem = (v) => { try { if (v === undefined) return localStorage.getItem(CHECKING) === '1'; if (v) localStorage.setItem(CHECKING, '1'); else localStorage.removeItem(CHECKING); } catch (e) {} return false; };
if (how === 'local' && mem()) how = want === 'browser' ? 'browser' : 'none';
const press = () => mic.setAttribute('aria-pressed', listening ? 'true' : 'false');
const mark = () => { te.classList.remove('te-local', 'te-browser', 'te-none'); te.classList.add(`te-${how}`); if (how === 'none') { mic.hidden = true; } else { mic.hidden = false; } };
const begin = () => {
  rec = new REC(); rec.lang = LANG; rec.continuous = onDevice; rec.interimResults = false; if (onDevice) rec.processLocally = true;
  rec.onresult = (ev) => { if (speaking) return; const t = ev.results[ev.results.length - 1][0].transcript.trim(); if (t) heard(t); };
  // 許されなかった時と使えない時は聞くのをやめる。ボタンだけで最後まで通る。聞き取れなかっただけの時は聞き続ける。
  rec.onerror = (ev) => { if (['not-allowed', 'service-not-allowed', 'language-not-supported'].indexOf(ev.error) >= 0) { listening = false; press(); } };
  rec.onend = () => { if (listening && !speaking) { try { rec.start(); } catch (e) {} } };
  listening = true; press(); try { rec.start(); } catch (e) {}
};
const wake = async () => {
  if (how === 'none') return;
  if (how === 'local') {
    // 印が書かれるのを待ってから聞く（すぐ落ちると、書く前に頁が消える事があるため）。
    mem(true); await new Promise((r) => setTimeout(r, 80));
    let a = 'no'; try { a = await REC.available({ langs: [LANG], processLocally: true }); } catch (e) {}
    if (a === 'downloadable' || a === 'downloading') { note.textContent = '__INSTALL__'; let ok = false; try { ok = await REC.install({ langs: [LANG], processLocally: true }); } catch (e) {} note.textContent = ''; if (ok) a = 'available'; }
    if (a !== 'available') {
      // 端末の中では字にできないと分かった。切り替えが browser の時は、断りの文を替えて、もう一度押した時から既定の口を使う（黙って外へ送らない）。ほかはマイクをしまう。
      mem(false);
      if (want === 'browser' && REC) { how = 'browser'; note.textContent = '__HOW_BROWSER__'; } else { how = 'none'; }
      mark(); return;
    }
    onDevice = true;
  }
  begin();
  // 端末の中の指定で聞き始めても落ちる画面がある（同じ headless）ので、始まった後に印を消す。
  if (onDevice) setTimeout(() => mem(false), 1500);
};
sayStart = () => { speaking = true; if (listening && rec) { try { rec.stop(); } catch (e) {} } };
sayEnd = () => { if (!speaking) return; speaking = false; if (listening && rec) { try { rec.start(); } catch (e) {} } };
mic.onclick = () => { if (listening) { listening = false; if (rec) rec.stop(); press(); return; } note.textContent = ''; wake(); };
addEventListener('pagehide', () => { listening = false; if (rec) { try { rec.stop(); } catch (e) {} } });
$('start').onclick = () => {
  try { const k = `tsukuru-start-${sid}-${hid}`; if (!sessionStorage.getItem(k)) { sessionStorage.setItem(k, '1'); send('start'); } } catch (e) {}
  to(n > total ? 'end' : 'step'); wake();
};
$('next').onclick = (e) => { e.preventDefault(); goNext(); };
$('back').onclick = (e) => { e.preventDefault(); goBack(); };
$('endback').onclick = (e) => { e.preventDefault(); goBack(); };
$('stuck').onclick = (e) => { e.preventDefault(); openAsk(); };
// 閉じる印: 開いている札を閉じる。何も開いていない時は玩具の頁へ戻る。
$('close').onclick = (e) => { const s = scene(); if (s === 'henji') { e.preventDefault(); to('step'); } else if (s === 'kekka') { e.preventDefault(); to('end'); } };
$('ask-form').onsubmit = (e) => { e.preventDefault(); ask(q.value.trim()); };
// 写真: 撮った物を足していく（1 つ撮るごとに選びが入れ替わる画面でも、前の 1 枚を落とさない）。写しはこの端末の中だけで作り、のこすまで送らない。
const form = $('up-form'), picker = $('files'), thumbs = $('thumbs'), go = $('keep'), ok = $('ok'), st = $('up-status'), max = Number(form.dataset.maxN);
let chosen = [];
function showPicked() {
  thumbs.querySelectorAll('[src]').forEach((el) => URL.revokeObjectURL(el.src));
  thumbs.textContent = '';
  const kept = chosen.slice(0, max);
  const movies = kept.filter((f) => f.type.startsWith('video/')).length, stills = kept.length - movies;
  for (const f of kept) {
    const el = document.createElement(f.type.startsWith('video/') ? 'video' : 'img');
    el.src = URL.createObjectURL(f); el.alt = '';
    if (el.tagName === 'VIDEO') { el.muted = true; el.playsInline = true; el.preload = 'metadata'; }
    thumbs.append(el);
  }
  let text = [[stills, '写真'], [movies, '動画']].filter(([c]) => c).map(([c, w]) => `${w} ${c}`).join('・');
  if (chosen.length > kept.length) text += `（${max} つまでなので、残りの ${chosen.length - kept.length} つは上げません）`;
  if (kept.some((f) => f.size > Number(form.dataset.maxBytes))) text += '（大きすぎて上げられない物があります）';
  $('picked').textContent = text;
  te.classList.toggle('picked', kept.length > 0);
}
picker.onchange = () => { chosen = chosen.concat([...picker.files]); picker.value = ''; showPicked(); };
// 声の「とって」: 画面によっては人が押さないとカメラを開けないので、開けない時は「とって」を目立たせて手を呼ぶ。
const shoot = () => { const shot = $('shot'); if (!shot) return; shot.classList.add('call'); setTimeout(() => shot.classList.remove('call'), 2000); try { picker.click(); } catch (e) {} };
// 「のこす」: 写真があれば手元だけの確かめを通してから、見た事の札を出す。既定の選びは置かない。
const keepPress = () => {
  if (go.disabled) return;
  if (chosen.length && !ok.checked) { ok.closest('label').classList.add('call'); return; }
  to('kekka');
};
form.onsubmit = (e) => { e.preventDefault(); keepPress(); };
document.querySelectorAll('.tile').forEach((b) => { b.onclick = () => save(b.value); });
// 残す順: 工夫の字を床に通す → 記録を作る → 欄を空にする → 写真を送る。工夫の字が床に落ちたら記録を作らず、字を残して理由を見せる。記録ができたら欄を空にする（写真で止まっても、押し直しで記録を増やさない）。
const save = async (result) => {
  if (go.disabled) return;
  go.disabled = true; to('end'); st.textContent = '送っています…';
  const files = chosen.slice(0, max), said = kufu.value.trim();
  let done = '', saved = false;
  try {
    if (said) {
      const t = await post(`/toy/${sid}/talk`, { scene: 'craft', hypothesis: hid, step: total, text: said, via: kufu.dataset.via === 'voice' ? 'voice' : 'text', json: '1' });
      const tj = await t.json().catch(() => ({}));
      if (!tj.kept) { st.textContent = tj.why || '残せませんでした'; return; }
      kufu.value = ''; kufu.dataset.via = '';
    }
    const r = await post(`/toy/${sid}/record-json`, { hypothesis: hid, result });
    const j = await r.json().catch(() => ({}));
    if (!j.id) { st.textContent = j.error || '残せませんでした'; return; }
    saved = true;
    form.reset(); chosen = []; showPicked();
    done = '上げました';
    for (const f of files) {
      const m = await fetch(`/record/${j.id}/media`, { method: 'POST', headers: { 'Content-Type': f.type || 'application/octet-stream' }, body: f });
      if (!m.ok) { done = '記録は残しました。' + ((await m.text()) || '写真か動画を上げられませんでした'); break; }
    }
  } catch (err) {
    if (!saved) { st.textContent = '送れませんでした。つながりを見て、もう一度押してください'; return; }
    done = '記録は残しました。写真か動画を送れませんでした';
  } finally { go.disabled = false; }
  location.assign(`/toy/${sid}/techo/kiroku?msg=${encodeURIComponent(done)}#mine`);
};
mark(); paint(); to('start');
})();
</script>"""


def sheet_of(data, printed_ids):
    """手帖で作る紙。型紙は玩具ごとに 1 枚で、たたき台は記録の先頭（本人の決定 11-05、#332）。
    #332 が入るまでは玩具の頁でほかの案を刷れるので、先頭が刷られていない時は、刷ってある紙の手順を出す（持っている紙と手順が食い違わないように）。"""
    ids = [h["id"] for h in data["hypotheses"] if h["id"] in printed_ids]
    head = data["hypotheses"][0]["id"]
    return head if head in ids else (ids[0] if ids else "")


def clean(t):
    return re.sub(CLEAN, "", t)


def _params(sid, data, h, v):
    template = h.get("template") or data.get("template", "slider_fan")
    params, _ = loop.version_params(sid, h["id"], v)
    return template, {**TEMPLATES[template].DEFAULTS, **(params or h.get("params") or {})}


def _doc(title, look, body):
    s = skin.SKINS.get(look, skin.SKINS[skin.DEFAULT])
    root = ";".join(f"--{k}:{v}" for k, v in s.items() if k != "name")
    return ('<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
            f'<title>{esc(title)}</title><style>:root{{{root}}}{STYLE}{skin.TAP_FLOOR}</style>'
            f'<body class="skin-{esc(look)}">{body}</body></html>')


def _key(name, cls="key", attrs="", tag="button", extra=""):
    kind = ' type="button"' if tag == "button" else ""
    return f'<{tag}{kind} class="{cls}" {attrs}>{KEY_ICONS[name]}<span>{name}</span>{extra}</{tag}>'


def page(sid, printed_ids, look=skin.DEFAULT, step=1, version=None, uploads=True):
    """手帖の頁。呼ぶ側（play_server）が刷ってある紙の一覧を渡す。刷った紙が無い時は、紙を作る道だけを出す（手順は紙と一緒に使う物なので）。"""
    data = hypotheses.load(sid)
    title = f'{data["toy"]} · 手帖'
    hid = sheet_of(data, printed_ids)
    if not hid:
        return _doc(title, look, f'<main class="te" data-scene="step"><h1 class="sr">手帖</h1><div class="end"><a class="key go" href="/toy/{esc(sid)}">紙を作る</a></div></main>')
    h = next(x for x in data["hypotheses"] if x["id"] == hid)
    vs = printed_versions(sid, hid)
    v = version if version in vs else vs[-1]  # 開いた時の版のまま作り続ける（別の人の報告で版が上がっても、手順の文を変えない）
    template, p = _params(sid, data, h, v)
    texts = tsukuru.step_texts(sid, hid, v) or [""]
    total = len(texts)
    n = min(max(step, 1), total + 1)
    pictures, which = instructions.step_pictures(template, p, texts)
    now = which[n - 1] if n <= total else -1
    koma = "".join(render.shapes_svg(s, "on" if i == now else "") for i, s in enumerate(pictures))
    steps = "".join(f'<li data-k="{k}" class="on">{esc(t)}</li>' if i == n else f'<li data-k="{k}" hidden>{esc(t)}</li>'
                    for i, (t, k) in enumerate(zip(texts, which), 1))
    width = round(min(n, total) / total * 100)
    tiles = "".join(f'<button type="button" class="tile" value="{esc(r)}">{result_icon(r)}<span>{esc(r)}</span></button>' for r in TEMPLATES[template].RESULTS)
    # 声の断りは、声がどこへ行くかをマイクが起きる前に言う文。声が使える時だけ出す。どちらの文を出すかは画面ごとに違うので、JS の印で切り替える。
    # 文は採られた文のまま（hanasu）。「話す」を「はじめる」に合わせた文は本人の確認待ちで、確認が済むまで入れない（本人の指示 11-05「新しい文は確認までマージしない」）。
    how = (f'<span class="how is-local">{esc(hanasu.HOW_LOCAL)}</span><span class="how is-browser">{esc(hanasu.HOW_BROWSER)}</span>'
           f'<span class="how is-local is-browser">{esc(making_log.ASK_NAME_VOICE)}</span>')
    # 合言葉なしで開いたデモ（uploads=False）では、写真と動画の口を閉じる（play_server の受け口も断る）。見た事と工夫の字は残せる。
    shot = (_key(SHOOT, "key shot", 'id="shot" for="files"', "label",
                 '<input type="file" id="files" accept="image/jpeg,image/png,video/mp4,video/quicktime" capture="environment" multiple>'
                 '<span class="picked" id="picked" aria-live="polite"></span><span class="thumbs" id="thumbs"></span>') if uploads else
            '<input type="file" id="files" disabled hidden><span class="picked" id="picked" hidden></span><span class="thumbs" id="thumbs" hidden></span>')
    limits = (f'<p class="meta">{MAX_PER_RECORD} つまで・1 つ {MAX_MEDIA // (1024 * 1024)}MB まで</p>' if uploads else
              '<p class="meta">公開のデモでは、写真と動画は上げられません。見た事とひとことは残せます。</p>')
    craft = hanasu.SCENES["craft"]
    body = (f'<main class="te" id="te" data-scene="{"end" if n > total else "step"}" data-sid="{esc(sid)}" data-hid="{esc(hid)}" data-v="{v}" '
            f'data-total="{total}" data-n="{n}" data-voice="{hanasu.mode()}"><h1 class="sr">手帖</h1>'
            f'<div class="bar" id="bar" role="progressbar" aria-valuemin="1" aria-valuemax="{total}" aria-valuenow="{min(n, total)}"><span style="width:{width}%"></span></div>'
            f'<button type="button" class="mic" id="mic" aria-pressed="false" aria-label="話して聞く（もう一度押すと止まる）" data-on="step henji end kekka" hidden>{MIC}</button>'
            f'<a class="close" id="close" href="/toy/{esc(sid)}" aria-label="閉じる">{CLOSE}</a>'
            f'<figure class="koma" id="koma" data-on="start step henji">{koma}</figure>'
            f'<ol id="steps" data-on="start step henji">{steps}</ol>'
            '<p class="meta" id="note" aria-live="polite"></p>'
            f'<p class="meta" id="start-note" data-on="start">{how}</p>'
            '<div class="keys" data-on="start step">'
            + _key(START, "key go", 'id="start" data-on="start"')
            + _key(BACK, "key", f'id="back" data-on="step" href="?v={v}&amp;n={max(n - 1, 1)}"', "a")
            + _key(NEXT, "key go", f'id="next" data-on="step" href="?v={v}&amp;n={n + 1}"', "a")
            # JS が無い時は、玩具の頁の聞く口へ行く。
            + _key(STUCK, "key", f'id="stuck" data-on="step" href="/toy/{esc(sid)}#ask"', "a")
            + '</div>'
            '<section class="henji" data-on="henji">'
            f'<form id="ask-form"><label class="sr" for="q">聞きたい事</label><input type="text" id="q" maxlength="300" placeholder="谷折りって？" enterkeyhint="send"><button type="submit" class="send" aria-label="聞く">{SEND}</button></form>'
            f'<div class="answer" id="answer" aria-live="polite"></div><p class="meta">{esc(making_log.ASK_NAME_VOICE)}</p></section>'
            '<section class="end" data-on="end">'
            f'<form id="up-form" data-max-n="{MAX_PER_RECORD}" data-max-bytes="{MAX_MEDIA}">{shot}'
            f'<label class="sr" for="kufu">{esc(craft["head"])}</label><textarea id="kufu" maxlength="{talk_log.MAX_TEXT}" placeholder="{esc(craft["hint"])}"></textarea>'
            '<label class="check" for="ok"><input type="checkbox" id="ok"> 大人の手元だけ・顔なし・声なし</label>'
            '<div class="keys">' + _key(BACK, "key", f'id="endback" href="?v={v}&amp;n={total}"', "a")
            + f'<button class="key go" id="keep">{KEY_ICONS[KEEP]}<span>{KEEP}</span></button></div>'
            f'<p class="meta" id="up-status" aria-live="polite"></p>{limits}'
            f'<p class="meta" id="up-notice">{esc(hanasu.UPLOAD_NOTICE)}</p><p class="meta">{esc(hanasu.NOTICE)}</p></form></section>'
            f'<section class="kekka" data-on="kekka">{tiles}</section></main>')
    js = (SCRIPT.replace("__WORDS__", json.dumps(WORDS, ensure_ascii=False)).replace("__RESULT_WORDS__", json.dumps(RESULT_WORDS, ensure_ascii=False))
          .replace("__CLEAN__", CLEAN).replace("__HOW_BROWSER__", hanasu.HOW_BROWSER).replace("__INSTALL__", INSTALL))
    return _doc(title, look, body + skin.WHO_SCRIPT + js)
