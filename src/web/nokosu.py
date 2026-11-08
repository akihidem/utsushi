"""のこすの頁の記入の節と、内容の確かめ（本人 11-08 402「のこすページ、記入、アップロード欄がない。記入後、のこすを押すと、内容確認になり、
承認すると、もちよるに飛ぶ、という形にしよう。承認の時に自己改善ループの話を出そう。」・405「記録欄の下に配置する指示さっきしたので
それに従ってください。」）。設計は grove の state/nokosu-flow-20261108.md の 3 版（別の目の検品 3 回）。

判断の芯:
- **記入の節は頁のいちばん上、「のこす」の釦は記入の欄のすぐ下**（400・405）。釦は帯の駅の道しるべ（p.road の中）で、頁の道しるべはこの 1 つ。
- **「のこす」では何も送らない。** 同じ頁の中で確かめの画面に替え、入れた字・結果・選んだ写真の小さい絵（その画面の中だけ）と、
  自己改善の輪の話（学びの輪の文と図と、naoru の 1 行）を見せる。utsushi のサーバへ送るのは「承認」の後だけ。
- **承認の時に叩く順は 1 つ**（別の目の止め 1）: 工夫の字があれば /talk（scene craft・step は手順の数）→ 断られたら記録を作らず理由を見せて
  記入へ戻す → /record-json（結果・感想）→ その場限りの印を作り直す（utsushiNewWho）→ 写真と動画を 1 つずつ /record/<番号>/media →
  もちよる（/gallery#ageta）。工夫の字は記録を作る時に talk_log.bind が同じ印で結ぶので、記録より先に送る。
- **「写真あり」の合図（attach）は使わない**（別の目の止め 3）。承認の時は結果が必ず入り、足すと書いた感想と結果が残らないため。いつも新しい記録。
- **記入の中身を端末に残さない**（localStorage・sessionStorage・IndexedDB に書かない）。utsushi-who（sessionStorage）は読むだけ（止め 2・B2）。
- **写真と動画は 3 つまで・1 つ 20MB まで**（今の MAX_PER_RECORD・MAX_MEDIA）。4 つ以上は手帖と同じ字で、残りを上げないと言う（止め 5）。
  選んだら約束の印（手帖と同じ字）を押さないと確かめへ進まない（気づき 7）。
- **台本が動かない画面**: 確かめの画面は台本のある画面だけ。noscript の中に、写真なしで記録を残す素のフォーム（POST /toy/<印>/record・
  結果と感想・隠した欄に紙と back=techo）を置く。台本が無いので who は付かず、話した字は記録に結ばれない（統括の決め・ここに断る）（止め 4・B3）。
- **声とカメラの区切り**（本人 11-08 330・412・415・「公開デモでも声も録る。」・設計 voice-camera-send の 3 版）: 工夫の欄に話す口の録る釦
  （hanasu.rec_button の「声を録る」・押してから「止める」までの声を録る）と、字の欄の下の 1 行（hanasu.keyboard_line）を置く。前は hanasu の「話す」
  （ブラウザの音声認識で字にしながら録る）だったが、本人 11-08 の答え (A) で音声認識を外した（grove の state/no-speech-recognition-20261108.md の 2 版）。
  「のこす」と「承認」は、録っている声を先に止め、置き終えてから並べる・送る（止めた区切りが並びに入るように）。確かめの画面に、この画面へ渡された区切り（web.clips の list）とこの頁で録った区切りを並べ、
  1 つずつ「外す」。承認で記録ができた後、写真の前に、区切りを 1 つずつ /record/<番号>/media へ送る（見出し X-Utsushi-Clip に t か k。
  カメラの区切りは、どの手順で押したかを X-Utsushi-Step、どの釦かを X-Utsushi-Button に添える。サーバが区切りの読みの手がかりにする）。
  送れた物から端末の置き場で消し、承認の終わりに置き場と渡す印を消す。
- **手帖の「のこす」の後の「区切りだけ」の確かめ**（#659 の取り消しの後の作り直し・統括の決め 11-08 (a)）: 手帖は記録と写真を送った後、
  今の回に区切りがある時だけ、この頁へ #to=<記録の番号>&msg=<返事> で移る。その時は記入の欄を出さず、確かめの画面を区切りの並びと「外す」と
  輪の話と「承認」だけで出す（記録の行と「直す」は隠す・新しい字なし）。承認で、区切りを手帖が作った記録へ送り、その玩具の区切りと印を消し、
  もちよるへ（返事の字は手帖の物。送れない物があれば CLIP_FAIL）。記録は作らない。サーバは記録の鍵で見るので、ほかの記録の番号では送れない。
  並びを手元に持った直後に、その場限りの印を作り直す（手帖が作り直さずに渡したため）。並びが空・置き場が開かない時は、そのまま もちよるへ。
  作り直すのは、この画面のどの出口よりも前（置き場の台本が無い・開かない・並びが空・承認、のどれでも。同じタブの次の人が前の人の印のまま
  作らないように・別の目の設計の確かめ 1）。読み直しても並ぶように、作り直す前の印を 1 回分だけ控える（web.clips の keepWho）。
  記録の鍵は作ってから 15 分なので、手帖の「残した記録に足す」から来た時や、この画面で長く止まった時は、送りが断られて CLIP_FAIL になる。
- **戻る釦で読み直さずに戻った時は読み直す**（pageshow の persisted・別の目の設計の確かめ 3）。手元の並びや記入が残ったまま、もう一度「承認」で
  同じ区切りを送り直したり、2 つ目の記録を作ったりしないように。区切りだけの確かめは、承認の後なら並びが空なので もちよるへ移る。
- **開いた時の渡し**は web.clips の openedAs(印, 'nokosu') に任せる（前の頁が作る頁の時だけ渡す・直に開いたら作り始め・別の目の #659 の止め 2）。
- 新しい字（本人の確かめ待ち）: RESULT_HEAD・CHECK_HEAD・APPROVE・FIX・PICK・NOSCRIPT。見出しは前からある のこすへの道の字（toy.KIROKU_TO_NOKOSU）。
"""
from omochae import talk_log

from . import clips, hanasu, naoru
from .skin import esc

# 型紙と一緒に刷ったしおりに、この記録を入れる 1 行（新しい字・本人の確かめ待ち・設計 grove の state/shiori-in-sheet-20261108.md の 6 節 7″）
SHIORI_LINE = "この記録を、さっき刷ったしおりに入れます。"
RESULT_HEAD = "どうだった？"
IMPRESSION_HEAD = "感想"
MEDIA_HEAD = "写真と動画"
CHECK_HEAD = "これで のこしますか"
APPROVE = "承認"
FIX = "直す"
PICK = "どうだったかを 1 つ えらんでください"
NOSCRIPT = "この画面では写真と動画は上げられません。"
# 手帖の約束の印と同じ字（techo_step）。前の「・声なし」は、声を録って送る作り（本人 11-08 415）と食い違うので外した。声の断りは話す口の 1 行で。本人の確かめ待ち
PROMISE = "大人の手元だけ・顔なし"

STYLE = """
.nokosu .nk-results{display:flex;flex-wrap:wrap;gap:8px;margin:4px 0 12px}
.nokosu .nk-results label{border:1px solid var(--frame);padding:8px 12px;cursor:pointer}
.nokosu .nk-results input{margin-right:6px}
.nokosu textarea{display:block;width:100%;min-height:64px;margin:4px 0 12px;font:inherit}
.nokosu .nk-thumbs img{width:72px;height:72px;object-fit:cover;margin:4px 4px 0 0}
.nokosu .nk-check .call{outline:2px solid var(--accent, #b33)}
/* 工夫の欄の録る釦（hanasu の台本が動かす）。指で押せる大きさ。録っている間の字と地の入れ替えは hanasu の .hanasu-rec の決まり */
.nokosu .hanasu-rec{min-height:44px;padding:6px 16px;margin:0 0 8px;border:2px solid var(--accent);background:var(--paper);color:var(--fg)}
.nokosu .hanasu-kb{margin:-8px 0 8px}
.nokosu .nk-clips li{margin:4px 0}
.nokosu .nk-clips video{width:96px;height:72px;object-fit:cover;vertical-align:middle;margin-right:6px}
"""

SCRIPT = """<script>(()=>{
const f = document.getElementById('nk'), chk = document.getElementById('nk-check'); if (!f || !chk) return;
f.hidden = false;
const sid = f.dataset.sid, hid = f.dataset.hid, total = f.dataset.total, max = +f.dataset.maxN, maxBytes = +f.dataset.maxBytes;
const $ = (id) => document.getElementById(id), st = $('nk-status'), go = $('nk-go'), files = $('nk-files'), ok = $('nk-ok');
let chosen = [], big = false;
// 手帖の「のこす」の後（#to=R-…&msg=…）。形の違う印は無い物とする（ふつうの のこすの頁のまま）
let toRec = '', toMsg = '';
try { const hm = location.hash.match(/^#to=(R-[0-9]{4,})&msg=(.*)$/); if (hm) { toRec = hm[1]; toMsg = decodeURIComponent(hm[2]); } } catch (e) { toRec = ''; }
const toGallery = (msg) => `/gallery?msg=${encodeURIComponent(msg)}#ageta`;
if (toRec) f.hidden = true;
const showPicked = () => {
  const kept = chosen.slice(0, max);
  let t = kept.map((x) => x.name).join('、');
  if (chosen.length > kept.length) t += `（${max} つまでなので、残りの ${chosen.length - kept.length} つは上げません）`;
  // 20MB を越えて選びから落とした物があれば、手帖と同じ字で言う（何も言わずに落とさない・別の目の気づき）
  if (big) t += '（大きすぎて上げられない物があります）';
  $('nk-picked').textContent = t;
  $('nk-promise').hidden = !chosen.length;
};
files.onchange = () => { const all = [...files.files]; chosen = all.filter((x) => x.size <= maxBytes); big = chosen.length < all.length; showPicked(); };
const result = () => (f.querySelector('input[name=result]:checked') || {}).value || '';
// 型紙と一緒に刷ったしおり（設計 2.1 版の 2 節）: サーバが待ちを見つけた時だけ 1 行が頁にあり、さらに、この画面の今の回の印が、刷った時の控え
// （utsushi-shiori-wait）と同じ時だけ出す（1 台を順に使う形で、次の人が玩具の頁から作り始めたら回が替わって出ない）。外したら結ばない
const runOf = () => { try { const r = JSON.parse(sessionStorage.getItem('utsushi-run:' + sid) || 'null'); return r && r.id ? r.id : ''; } catch (e) { return ''; } };
let shioriOn = false;
const sw = $('nk-c-shiori');
if (sw) {
  try { shioriOn = !!runOf() && sessionStorage.getItem('utsushi-shiori-wait:' + sid) === runOf(); } catch (e) { shioriOn = false; }
  sw.hidden = !shioriOn;
  $('nk-shiori-x').onclick = () => { shioriOn = false; sw.hidden = true; };
}
const post = (url, data) => fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  body: new URLSearchParams({ ...data, who: sessionStorage.getItem('utsushi-who') || '' }) });
// 「のこす」: 何も送らず、確かめの画面に替える（402）
// 区切りの並び（web.clips）。頁を開いた時に、渡す印の違う物を消す（list が消す）。確かめの画面を出す時に、この頁で録った物も入れる
let clipsNow = [];
// 並びを描くのは手元の clipsNow から（区切りだけの確かめでは、印を作り直した後に置き場から並べ直すと、前の印の物が消えるため）
const drawClips = () => {
  const box = $('nk-c-clips'); if (!box) return;
  const ul = box.querySelector('ul'); ul.textContent = ''; box.hidden = !clipsNow.length;
  clipsNow.forEach((c) => {
    const li = document.createElement('li');
    if (c.kind === 'k') { const v = document.createElement('video'); v.muted = true; v.playsInline = true; v.preload = 'metadata'; v.src = URL.createObjectURL(c.blob); li.appendChild(v); }
    li.appendChild(document.createTextNode(`${c.kind === 'k' ? 'カメラ' : '声'} ${Math.max(1, Math.round((c.ms || 0) / 1000))} 秒 `));
    const b = document.createElement('button'); b.type = 'button'; b.textContent = '__REMOVE__';
    b.onclick = async () => { await utsushiClips.remove(c.id); clipsNow = clipsNow.filter((x) => x.id !== c.id); drawClips(); };
    li.appendChild(b); ul.appendChild(li);
  });
};
const showClips = async () => {
  if (!window.utsushiClips || !$('nk-c-clips')) return;
  await utsushiClips.adopt(sid); clipsNow = await utsushiClips.list(sid); drawClips();
};
// 区切りだけの確かめ: 記入の欄と記録の行と「直す」を隠し、並びと輪の話と「承認」だけ
const onlyClips = () => { $('nk-c-rec').hidden = true; $('nk-fix').hidden = true; chk.hidden = false; drawClips(); chk.scrollIntoView(); };
// 開いた時: 渡すかどうかと並べる事は web.clips の openedAs に任せる（作る頁から来た時だけ渡す・直に開いたら作り始め）
addEventListener('DOMContentLoaded', () => {
  const newWho = () => { if (window.utsushiNewWho) window.utsushiNewWho(); };
  if (!window.utsushiClips) { if (toRec) { newWho(); location.replace(toGallery(toMsg)); } return; }
  utsushiClips.openedAs(sid, 'nokosu').then((list) => {
    if (!toRec) return;
    clipsNow = list; utsushiClips.keepWho(sid, toRec); newWho();
    if (!clipsNow.length) { utsushiClips.dropKeep(); location.replace(toGallery(toMsg)); return; }
    onlyClips();
  }).catch(() => { if (toRec) { newWho(); utsushiClips.dropKeep(); location.replace(toGallery('__CLIP_FAIL__')); } });
});
addEventListener('pageshow', (e) => { if (e.persisted) location.reload(); });
// 区切りを 1 つずつ送る（記録ができた後・写真の前）。見出しで、声（t）かカメラ（k）かと、カメラの区切りの手順と釦を添える。送れた物から置き場で消す
const sendClips = async (id) => {
  let bad = false;
  for (const c of clipsNow) {
    const h = { 'Content-Type': c.type || 'application/octet-stream', 'X-Utsushi-Clip': c.kind };
    if (c.kind === 'k') { if (/^[0-9]+$/.test(String(c.step))) h['X-Utsushi-Step'] = String(c.step); if (c.button) h['X-Utsushi-Button'] = c.button; }
    // 1 つずつ受ける（送りが落ちたら送れなかった事にして次へ・CLIP_FAIL）。送れた後に置き場で消せなかった時は送れた事のまま（承認の終わりの消しが、もう一度消す）
    try { const m = await fetch(`/record/${id}/media`, { method: 'POST', headers: h, body: c.blob }); if (m.ok) await utsushiClips.remove(c.id).catch(() => {}); else bad = true; } catch (e) { bad = true; }
  }
  return bad;
};
f.onsubmit = async (e) => {
  e.preventDefault();
  if (!result()) { st.textContent = '__PICK__'; return; }
  if (chosen.length && !ok.checked) { ok.closest('label').classList.add('call'); return; }
  // 録っている声は止めて、置き終えてから確かめの画面に並べる（止めた区切りが並びに入るように・音声認識を外す設計の 2 版の止め 2）
  if (window.utsushiClips) await utsushiClips.voiceStop();
  $('nk-c-result').textContent = result();
  $('nk-c-kufu').textContent = $('nk-kufu').value.trim();
  $('nk-c-impression').textContent = $('nk-impression').value.trim();
  const th = $('nk-c-thumbs'); th.textContent = '';
  chosen.slice(0, max).forEach((x) => {
    if (x.type.startsWith('image/')) { const i = document.createElement('img'); i.src = URL.createObjectURL(x); i.alt = x.name; th.appendChild(i); }
    else { const s = document.createElement('span'); s.textContent = x.name; th.appendChild(s); }
  });
  st.textContent = ''; f.hidden = true; chk.hidden = false; chk.scrollIntoView(); showClips();
};
$('nk-fix').onclick = () => { chk.hidden = true; f.hidden = false; };
const sendFiles = async (id, list) => {
  for (const x of list) {
    const m = await fetch(`/record/${id}/media`, { method: 'POST', headers: { 'Content-Type': x.type || 'application/octet-stream' }, body: x });
    if (!m.ok) return '記録は残しました。' + ((await m.text()) || '写真か動画を上げられませんでした');
  }
  return '上げました';
};
// 「承認」: 工夫の字 → 記録 → 印の作り直し → 写真と動画 → もちよる（止め 1）。押している間は押せない
go.onclick = async () => {
  if (go.disabled) return;
  go.disabled = true; const cs = $('nk-c-status'); cs.textContent = '送っています…';
  // 送る前にも止める（確かめの画面で録る釦は見えないが、録りの止まりを送りの前に必ず通す）
  if (window.utsushiClips) await utsushiClips.voiceStop();
  // 区切りだけの確かめ: 手帖が作った記録へ区切りを送り、その玩具の区切りと印を消して もちよるへ（記録は作らない）
  if (toRec) {
    const bad = clipsNow.length ? await sendClips(toRec) : false;
    try { await utsushiClips.clear(sid); } catch (e) {}
    utsushiClips.dropKeep();
    location.assign(toGallery(bad ? '__CLIP_FAIL__' : toMsg)); return;
  }
  const said = $('nk-kufu').value.trim(), list = chosen.slice(0, max);
  let done = '', saved = false;
  try {
    if (said) {
      const t = await post(`/toy/${sid}/talk`, { scene: 'craft', hypothesis: hid, step: total, text: said, via: 'text', json: '1' });
      const tj = await t.json().catch(() => ({}));
      if (!tj.kept) { chk.hidden = true; f.hidden = false; st.textContent = tj.why || '残せませんでした'; return; }
    }
    // しおりの 1 行を外さなかった時だけ、結ぶ印と今の回の印を添える（サーバが待ちの cookie・who・回・3 時間を照らしてから結ぶ）
    const r = await post(`/toy/${sid}/record-json`, { hypothesis: hid, result: result(), impression: $('nk-impression').value.trim(), ...(shioriOn ? { shiori: '1', run: runOf() } : {}) });
    try { sessionStorage.removeItem('utsushi-shiori-wait:' + sid); } catch (e) {}
    const j = await r.json().catch(() => ({}));
    if (!j.id) { cs.textContent = j.error || '残せませんでした'; return; }
    saved = true;
    if (window.utsushiNewWho) window.utsushiNewWho();
    f.reset(); chosen = []; showPicked();
    const clipBad = window.utsushiClips && clipsNow.length ? await sendClips(j.id) : false;
    done = list.length ? await sendFiles(j.id, list) : '記録を残しました';
    // 区切りを送れなかった時は、サーバの断りの字を出さず（本人の確かめていない字のため）、決めた 1 行だけを出す。写真は送り続ける
    if (clipBad) done = '__CLIP_FAIL__';
    if (window.utsushiClips) await utsushiClips.clear(sid);  // その玩具の区切りと印だけ（ほかの玩具の物は消さない）
  } catch (err) {
    if (!saved) { cs.textContent = '送れませんでした。つながりを見て、もう一度押してください'; return; }
    done = '記録は残しました。写真か動画を送れませんでした';
  } finally { go.disabled = false; }
  location.assign(`/gallery?msg=${encodeURIComponent(done)}#ageta`);
};
})()</script>"""


def entry(sid, paper, results, shiori_wait=False):
    """記入の節と確かめの画面（台本で動く形）と、台本の無い画面の素のフォーム。paper は (紙の印, 手順の数)。
    results は結果の札の字（records.results_for）。頁に 1 回だけ置く。"""
    from . import loop_figure, toy  # 循環を避けて、ここで読む（techo_site と同じ）
    from .techo_site import MAX_MEDIA, MAX_PER_RECORD

    hid, total = paper
    # 台本の形は required を付けない（付けると、えらばずに押した時にブラウザの吹き出しが出て、PICK の字が出ない）。素のフォームには付ける
    radios = "".join(f'<label><input type="radio" name="result" value="{esc(r)}">{esc(r)}</label>' for r in results)
    plain_radios = "".join(f'<label><input type="radio" name="result" value="{esc(r)}" required>{esc(r)}</label>' for r in results)
    kufu = hanasu.SCENES["craft"]
    limits = f"{MAX_PER_RECORD} つまで・1 つ {MAX_MEDIA // (1024 * 1024)}MB まで"
    form = (f'<form id="nk" hidden data-sid="{esc(sid)}" data-hid="{esc(hid)}" data-total="{total}" data-max-n="{MAX_PER_RECORD}" data-max-bytes="{MAX_MEDIA}">'
            f'<fieldset style="border:0;padding:0;margin:0"><legend>{esc(RESULT_HEAD)}</legend><div class="nk-results">{radios}</div></fieldset>'
            # 工夫の欄は話す口の形（data-hanasu の中の textarea と .hanasu-rec と .hanasu-note。hanasu の台本が、押してから止めるまでの声を録る）。
            # 字は端末のキーボードのマイクでも入る（欄の下の 1 行）。送るのは承認の時だけ（hanasu の「残す」のフォームは置かないので、hanasu の submit は動かない）
            f'<div data-hanasu data-sid="{esc(sid)}" data-scene="craft"><label for="nk-kufu">{esc(hanasu.KUFU_HEAD)}</label>'
            f'<textarea id="nk-kufu" maxlength="{talk_log.MAX_TEXT}" placeholder="{esc(kufu["hint"])}"></textarea>'
            f'{hanasu.keyboard_line()}{hanasu.rec_button()}<p class="meta hanasu-note" aria-live="polite"></p>'
            f'<p class="meta">{clips.notes()}</p></div>'
            f'<label for="nk-impression">{esc(IMPRESSION_HEAD)}</label><textarea id="nk-impression" maxlength="{talk_log.MAX_TEXT}" placeholder="{esc(naoru.KEEP_HINT)}"></textarea>'
            f'<label for="nk-files">{esc(MEDIA_HEAD)}（{esc(limits)}）</label>'
            '<input type="file" id="nk-files" accept="image/jpeg,image/png,video/mp4,video/quicktime" multiple>'
            '<p class="meta" id="nk-picked" aria-live="polite"></p>'
            f'<p id="nk-promise" hidden><label class="check" for="nk-ok"><input type="checkbox" id="nk-ok"> {esc(PROMISE)}</label></p>'
            f'<p class="meta">{esc(hanasu.UPLOAD_NOTICE)}</p>'
            '<p class="meta" id="nk-status" aria-live="polite"></p>'
            # 「のこす」は記入の欄のすぐ下（405）。帯の駅の道しるべの釦（p.road の .go）で、頁の道しるべはこの 1 つ（test_ux_stage0）
            '<p class="road"><button type="submit" class="go" id="nk-keep">のこす</button></p></form>')
    # 確かめの画面。自己改善の輪の話は、学びの輪の文と図（輪の部品の字のまま・401）と naoru の 1 行（402「承認の時に自己改善ループの話を出そう」）
    # 記録の行は 1 つの囲み（nk-c-rec）にまとめる。手帖の のこす の後の区切りだけの確かめでは、囲みごと隠す
    check = (f'<div class="nk-check" id="nk-check" hidden><h3>{esc(CHECK_HEAD)}</h3><div id="nk-c-rec">'
             f'<p class="meta">{esc(RESULT_HEAD)}</p><p id="nk-c-result"></p>'
             f'<p class="meta">{esc(hanasu.KUFU_HEAD)}</p><p id="nk-c-kufu"></p>'
             f'<p class="meta">{esc(IMPRESSION_HEAD)}</p><p id="nk-c-impression"></p>'
             '<div class="nk-thumbs" id="nk-c-thumbs"></div></div>'
             f'<div class="nk-clips" id="nk-c-clips" hidden><p class="meta">{esc(clips.HEAD)}</p><ul></ul><p class="meta">{esc(clips.STORE)}</p></div>'
             # しおりの 1 行は待ちがある時だけ頁に置く（台本が今の回と照らしてから見せる）。横の釦は今の字「外す」
             + (f'<p id="nk-c-shiori" hidden>{esc(SHIORI_LINE)} <button type="button" id="nk-shiori-x">{esc(clips.REMOVE)}</button></p>' if shiori_wait else '') +
             f'<p>{esc(loop_figure.ADOPTED)}</p>{loop_figure.svg()}'
             + (f'<p>{esc(naoru.LINES[0])}</p>' if naoru.LINES else "") +
             f'<p><button type="button" class="go" id="nk-go">{esc(APPROVE)}</button> <button type="button" id="nk-fix">{esc(FIX)}</button></p>'
             '<p class="meta" id="nk-c-status" aria-live="polite"></p></div>')
    # 台本の無い画面: 写真なしで記録だけを残す素のフォーム。戻り先は記録の頁の #mine（back=techo）
    plain = ('<noscript><form method="post" action="/toy/' + esc(sid) + '/record">'
             f'<input type="hidden" name="hypothesis" value="{esc(hid)}"><input type="hidden" name="back" value="techo">'
             f'<fieldset style="border:0;padding:0;margin:0"><legend>{esc(RESULT_HEAD)}</legend><div class="nk-results">{plain_radios}</div></fieldset>'
             f'<label>{esc(IMPRESSION_HEAD)}<textarea name="impression" maxlength="{talk_log.MAX_TEXT}"></textarea></label>'
             f'<p class="meta">{esc(NOSCRIPT)}</p><p><button type="submit">のこす</button></p></form></noscript>')
    return (f'<section class="panel nokosu" id="kinyu" aria-label="のこす"><h2>{esc(toy.KIROKU_TO_NOKOSU)}</h2>{form}{check}{plain}</section>'
            + SCRIPT.replace("__PICK__", PICK.replace("'", "\\'")).replace("__REMOVE__", clips.REMOVE).replace("__CLIP_FAIL__", clips.CLIP_FAIL))


def no_paper(sid):
    """刷った紙が無い時の記入の節の代わり: 紙を作る道（手帖の、紙の無い時の字と同じ「紙を作る」）。"""
    return f'<section class="panel nokosu" id="kinyu" aria-label="のこす"><p class="road"><a class="go" href="/toy/{esc(sid)}">紙を作る</a></p></section>'
