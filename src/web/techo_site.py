"""手帖を入口のサイトの中に置く（本人の方向転換、2026-11-04 午後）。

本人の言葉: 「最初のサイトと、いまアーティファクトで作った手帖は地続きの方が良いのでは。アーティファクトで作ってと言ったのが良くなかったね」。
本人の指定（同じ日）: 生徒向けの画面は机に置いて声で操作する。両手は工作で塞がっている。写真や動画を上げられる。文字は最小。
判断の芯:
- 入口（A・A′・C の展示）→ 玩具の頁 → 手帖 → 試した記録、を同じサーバの頁で一続きにする。見た目は A′ の白い展示の世界に合わせる
- 聞く口は src/api/ask.py をそのまま使う（仕組みは答えない、よくある言葉は刷った説明から、ほかは鍵がある時だけ Claude）
- 声: ブラウザの音声認識で、1 回押したら話し続けられる形（続けて聞く）と、答えの読み上げ。使えない画面では字の操作だけが残る
- 上げた写真と動画は、その場で作った試した記録（R-番号）に添える。置き場は記録と同じ git の外（data/records/media）
- 写真と動画の撮影情報（位置など）は保存の時に外す。記録は公開の repo に入り得るし、ギャラリーは合言葉を知る人の全員に見えるため（#156）
- 中身が写真・動画として読める物だけを置く。送られた Content-Type は信じない。動画は観察の ffmpeg に渡るので、なおさら
"""
import html
import io
import pathlib
import re
import shutil
import subprocess
import tempfile

from PIL import Image

from api import ask, config
from omochae import contrib, hypotheses, making_log, records
from omochae.compose import TEMPLATES
from omochae.form_import import FORM_URL

MEDIA_TYPES = {"image/jpeg": "jpg", "image/png": "png", "video/mp4": "mp4", "video/quicktime": "mov"}
MAX_MEDIA = 20 * 1024 * 1024
MAX_PER_RECORD = 3
MISMATCH = "中身を写真か動画として読めません（JPEG・PNG・MP4・MOV だけ）"
ICONS = {
    "動いた": '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M10 34c8 0 14-6 18-18M20 14l8 2 2 8"/></svg>',
    "動かない": '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M10 24h28"/></svg>',
    "わからない": '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M18 18a6 6 0 1 1 8 6c-2 1-2 2-2 5"/><circle cx="24" cy="35" r="1"/></svg>',
    "揺れた": '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M6 24c4-8 8-8 12 0s8 8 12 0 8-8 12 0"/></svg>',
    "揺れない": '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M6 24h36"/></svg>',
}


def esc(s):
    return html.escape(str(s or ""), quote=True)


def media_dir(rid):
    return records.folder() / "media" / rid


def strip_jpeg_meta(data):
    """JPEG の撮影情報を外す。画素は変えない。読めない形なら None（情報が残るかもしれない物を置かないため）。

    残す区画を決めて、ほかは全部外す（JFIF・ICC の色・Adobe の色の変換）。外す物を並べる形だと、機種ごとの区画（位置や顔の情報）が抜けるため。
    最後の EOI の後ろも捨てる。スマホの写真はそこに 2 枚目の画像（MPF）を持ち、それ自身の EXIF が付く事がある。
    """
    if data[:2] != b"\xff\xd8":
        return None
    out, p = bytearray(data[:2]), 2
    while p + 1 < len(data):
        if data[p] != 0xFF:
            return None
        m = data[p + 1]
        if m == 0xFF:  # 区画の前の詰め物
            p += 1
            continue
        if m == 0xD9:
            return bytes(out) + b"\xff\xd9"
        n = int.from_bytes(data[p + 2:p + 4], "big")
        seg = data[p:p + 2 + n]
        extra = 0xE0 <= m <= 0xEF or m == 0xFE
        if not extra or m in (0xE0, 0xEE) or (m == 0xE2 and seg[4:16] == b"ICC_PROFILE\x00"):
            out += seg
        p += 2 + n
        if m == 0xDA:  # 画素の本体。次の区画まで（FF00 と RST は本体の中の印）そのまま写す
            q = p
            while True:
                q = data.find(b"\xff", q)
                if q < 0 or q + 1 >= len(data):
                    return None
                if data[q + 1] != 0 and not 0xD0 <= data[q + 1] <= 0xD7:
                    break
                q += 2
            out += data[p:q]
            p = q
    return None


def clean_photo(data, ext):
    """写真を置ける形にする。Returns 中身 or None（型と合わない・読めない）。PNG は画素だけを書き直す。JPEG は描き直すと画質が落ちるので区画だけを外す。"""
    clean, kind = contrib._clean_image(data)
    if clean is None or kind != f".{ext}":
        return None
    if ext == "png":
        return clean
    # 向きの欄は EXIF の中にある。外すと縦に撮った写真が横倒しになるので、向きのある写真だけは描き直して画素へ移す
    with Image.open(io.BytesIO(data)) as im:
        return clean if im.getexif().get(0x0112, 1) != 1 else strip_jpeg_meta(data)


def clean_video(data, ext):
    """動画の撮影情報を落として入れ物を作り直す。絵と音は再符号化しない。Returns (中身 or None, 失敗の文)。

    絵と音の流れだけを写す（-map）。全体の欄だけを消しても、字幕や時刻つきの情報の流れと流れごとの欄に位置が残るため。
    読み手を mov に決める（-f mov）。中身の形で読み手を選ばせると、ほかのファイルや URL を指す一覧（HLS など）を読みに行くため。
    """
    if data[4:8] not in (b"ftyp", b"moov", b"mdat", b"wide", b"free", b"skip"):
        return None, MISMATCH
    if not shutil.which("ffmpeg"):
        return None, "この機械では動画を受けられません（撮影情報を外す ffmpeg が無い）"
    with tempfile.TemporaryDirectory() as tmp:
        src, dst = pathlib.Path(tmp) / "in", pathlib.Path(tmp) / f"out.{ext}"
        src.write_bytes(data)
        try:
            r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "mov", "-i", str(src),
                                "-map", "0:V", "-map", "0:a?", "-map_metadata", "-1", "-map_metadata:s", "-1", "-map_chapters", "-1",
                                "-c", "copy", "-f", ext, str(dst)], capture_output=True, timeout=config.VIDEO_TIMEOUT)
        except (OSError, subprocess.TimeoutExpired):
            return None, MISMATCH
        if r.returncode != 0 or not dst.exists():
            return None, MISMATCH
        return dst.read_bytes(), ""


def save_media(rid, ctype, data):
    """Returns (ファイル名 or None, 失敗の文)。記録が実在し、型と大きさと数の上限を守り、中身が読める物だけを、撮影情報を外して置く。"""
    if not re.fullmatch(r"R-\d{4,}", rid) or not (records.folder() / f"{rid}.json").exists():
        return None, "記録が無い"
    ext = MEDIA_TYPES.get(ctype)
    if not ext:
        return None, "写真（JPEG・PNG）か動画（MP4・MOV）だけ"
    if not 0 < len(data) <= MAX_MEDIA:
        return None, "1 つ 20MB まで"
    d = media_dir(rid)
    have = sorted(d.glob("m*.*")) if d.exists() else []
    if len(have) >= MAX_PER_RECORD:
        return None, "1 つの記録に 3 つまで"
    if ext in ("mp4", "mov"):
        clean, why = clean_video(data, ext)
    else:
        clean, why = clean_photo(data, ext), MISMATCH
    if clean is None:
        return None, why
    d.mkdir(parents=True, exist_ok=True)
    name = f"m{len(have) + 1}.{ext}"
    (d / name).write_bytes(clean)
    return name, ""


def media_of(rid):
    d = media_dir(rid)
    return [p.name for p in sorted(d.glob("m*.*"))] if d.exists() else []


def ai_offer(rid):
    """AI の 2 つの口のうち、今押して進める物と、進めない時に出す 1 行を返す（#130）。

    押しても断りの文が返るだけの釦を出さないため。play_server の受け口の断りは、古い頁から押された時のために残す。
    """
    if not ask._key_present():
        return False, False, "AI の返事は、この場では使えません。"
    has_video = any(f.endswith(("mp4", "mov")) for f in media_of(rid))
    return True, has_video, "" if has_video else "動画を上げると、Claude が見えた事を返します。"


# 色は皮の変数から取る（skin.py の SKINS。本人の指示 11-05: A′ 白の展示と C 黒のジンを一気通貫に）。
# 手帖だけ書体をゴシックにし字を大きくするのは、机に置いて離れて読むため（本人の指定 11-04「文字は最小」）。骨（頭の帯・余白）は skin.shell が持つ。
STYLE = """
#up-status{scroll-margin-top:16px}
body.techo{font-family:"Noto Sans JP","Hiragino Sans",system-ui,sans-serif;font-size:18px}
.techo main{max-width:640px;margin:0 auto;padding:20px max(16px,env(safe-area-inset-left,0px)) 64px;display:grid;gap:22px}
.techo main:has(.gallery){max-width:960px}
.techo .gallery h1{font-size:clamp(19px,5vw,26px);letter-spacing:.2em}.techo .gallery .top a{white-space:nowrap}
.techo .jump{display:flex;gap:6px 18px;flex-wrap:wrap;margin:8px 0 14px;font-size:14px;letter-spacing:.1em}.techo .jump a{color:var(--accent)}
.techo h1{font-family:"Noto Serif CJK JP","Hiragino Mincho ProN",serif;font-weight:400;font-size:26px;letter-spacing:.3em;margin:0}
.techo .top{display:flex;align-items:center;gap:14px}.techo .top img{width:56px;height:84px;object-fit:cover;border:1px solid var(--frame)}
.techo .top a{margin-left:auto;font-size:14px;color:var(--accent)}
.techo .row{display:flex;gap:12px;flex-wrap:wrap}
.techo .tile{display:grid;justify-items:center;gap:6px;border:2px solid var(--frame);background:var(--paper);color:var(--fg);font:inherit;font-size:15px;padding:10px 14px;border-radius:14px;cursor:pointer;min-width:84px;text-decoration:none;position:relative}
.techo .tile[aria-pressed="true"],.techo .tile:has(input:checked){border-color:var(--accent);box-shadow:0 0 0 2px var(--accent) inset}
.techo .tile .big{font-family:"Noto Serif CJK JP",serif;font-size:34px;line-height:1}
.techo .tile svg{width:44px;height:44px;stroke:var(--fg);fill:none;stroke-width:3;stroke-linecap:round;stroke-linejoin:round}
.techo .tile input{position:absolute;opacity:0;pointer-events:none}
.techo .panel{border:1px solid var(--frame);border-radius:18px;padding:18px;display:grid;gap:14px;background:var(--paper)}
.techo .mark{display:flex;align-items:center;gap:12px;font-family:"Noto Serif CJK JP",serif;font-size:22px;letter-spacing:.15em;margin:0}
.techo .mark svg{width:40px;height:40px;stroke:var(--accent);fill:none;stroke-width:3;stroke-linecap:round;stroke-linejoin:round}
.techo input[type=text]{font:inherit;font-size:22px;border:2px solid var(--frame);border-radius:12px;padding:14px 16px;width:100%;box-sizing:border-box;background:var(--field);color:var(--fg)}
.techo #ask-form{display:flex;gap:10px;align-items:stretch}.techo #ask-form input{flex:1;min-width:0;margin:0}.techo #ask-form .go{white-space:nowrap}
.techo .mic{width:96px;height:96px;border-radius:50%;border:0;background:var(--accent);color:var(--onaccent);display:grid;place-items:center;cursor:pointer;justify-self:center;margin:0}
.techo .mic svg{width:48px;height:48px;stroke:var(--onaccent);fill:none;stroke-width:3;stroke-linecap:round}
/* 聞いている間は地と字を入れ替える。緑などの別の色を足さず、どちらの皮でも「今は違う状態」と読めるようにするため。 */
.techo .mic[aria-pressed="true"]{background:var(--fg);color:var(--bg)}.techo .mic[aria-pressed="true"] svg{stroke:var(--bg)}
.techo .answer{font-size:26px;line-height:1.6;white-space:pre-wrap;min-height:1.6em;border-top:1px solid var(--frame);padding-top:12px}
.techo .answer:empty::before{content:"ここに答えが出ます";font-size:14px;color:var(--mute)}
.techo .shot{display:grid;place-items:center;gap:6px;border:2px dashed var(--accent);border-radius:16px;padding:22px;cursor:pointer;color:var(--accent);position:relative;margin:0}
.techo .shot svg{width:56px;height:56px;stroke:var(--accent);fill:none;stroke-width:2.5}
.techo .shot input{position:absolute;opacity:0;width:1px;height:1px}
.techo .picked{font-size:16px}.techo .picked:empty,.techo .thumbs:empty{display:none}
.techo .thumbs{display:flex;flex-wrap:wrap;justify-content:center;gap:8px}.techo .thumbs img,.techo .thumbs video{width:72px;height:72px;object-fit:cover;border-radius:8px}
.techo .go{font:inherit;font-size:20px;letter-spacing:.05em;background:var(--accent);color:var(--onaccent);border:0;padding:16px 28px;border-radius:12px;cursor:pointer;margin:0}
.techo .check{display:flex;gap:10px;align-items:center;font-size:15px;margin:0}.techo .check input{width:26px;height:26px}
.techo .meta{font-size:12px;color:var(--mute)}
.techo .item{border-top:1px solid var(--rule);padding-top:10px;display:grid;gap:6px}
.techo .item img,.techo .item video{height:110px;max-width:100%;border:1px solid var(--frame);border-radius:8px}
.techo .sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
.techo :focus-visible{outline:3px solid var(--accent);outline-offset:2px}
"""

SCRIPT = """
<script>
(() => {
const sid = document.querySelector('[data-sid]').dataset.sid;
// 読み上げの間は音声認識を止める: 止めないと端末が自分の答えを聞き取り、問いとして送り、それがまた読み上げられる（答えの文が質問として残り、費用もかかる）。
// 読み上げの終わりの知らせが来ない機種があるので、長さから見た時間でも戻す。前の読み上げの取り消しの知らせで戻らないよう、番号で見分ける。
let sayStart = () => {}, sayEnd = () => {}, sayId = 0;
const say = (t) => { try { if (!('speechSynthesis' in window)) return; speechSynthesis.cancel(); const u = new SpeechSynthesisUtterance(t), id = ++sayId; u.lang = 'ja-JP';
  const fin = () => { if (id === sayId) sayEnd(); }; u.onend = fin; u.onerror = fin; setTimeout(fin, Math.min(60000, t.length * 400 + 3000)); sayStart(); speechSynthesis.speak(u); } catch (e) { sayEnd(); } };
// 版（開いた時に刷ってあった一番新しい版）と、その場限りの印（skin.WHO_SCRIPT が持つ）を、出来事に添える。
const paper = () => document.querySelector('[name=hypothesis]:checked') || {};
const extra = (o) => { const b = new URLSearchParams(o); const el = paper(); if (el.dataset && el.dataset.v) b.set('sheet_version', el.dataset.v); try { const w = sessionStorage.getItem('utsushi-who'); if (w) b.set('who', w); } catch (e) {} return b; };
const ans = document.getElementById('answer');
async function ask(q) {
  const hid = (document.querySelector('[name=hypothesis]:checked') || {}).value;
  if (!q || !hid) return;
  ans.textContent = '…';
  const r = await fetch(`/toy/${sid}/ask-json`, { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: extra({ hypothesis: hid, question: q }) });
  const j = await r.json().catch(() => ({ text: '今は答えられません' }));
  ans.textContent = j.text; say(j.text);
}
document.getElementById('ask-form').onsubmit = (e) => { e.preventDefault(); ask(document.getElementById('q').value.trim()); };
// 音声認識: 1 回押すと話し続けられる（続けて聞く）。もう 1 回押すと止まる。使えない画面ではボタンを隠し、字の操作だけにする。
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
const mic = document.getElementById('mic');
if (!SR) { mic.hidden = true; } else {
  let rec = null, on = false, speaking = false;
  sayStart = () => { speaking = true; if (on && rec) { try { rec.stop(); } catch (e) {} } };
  sayEnd = () => { if (!speaking) return; speaking = false; if (on && rec) { try { rec.start(); } catch (e) {} } };
  mic.onclick = () => {
    if (on) { on = false; rec && rec.stop(); mic.setAttribute('aria-pressed', 'false'); return; }
    rec = new SR(); rec.lang = 'ja-JP'; rec.continuous = true; rec.interimResults = false;
    rec.onresult = (ev) => { if (speaking) return; const t = ev.results[ev.results.length - 1][0].transcript.trim(); document.getElementById('q').value = t; ask(t); };
    rec.onend = () => { if (on && !speaking) { try { rec.start(); } catch (e) {} } };
    on = true; mic.setAttribute('aria-pressed', 'true'); rec.start();
  };
}
// 上げる: 先に記録を作り（見た事）、その R-番号に写真と動画を 1 つずつ送る。
// 送った後は頁の中で一覧を入れ替える。同じ道へ移っても読み込まれず、「…」のまま残って押し直すと記録が 2 件になるため（#143）。読み込み直さないので、話している手順も切れない。
const showMine = async () => {
  const doc = new DOMParser().parseFromString(await (await fetch(location.pathname)).text(), 'text/html');
  document.getElementById('mine').innerHTML = doc.getElementById('mine').innerHTML;
};
// 選んだ物を押す前に見せる。写しはこの端末の中だけで作り、送らない。
const upForm = document.getElementById('up-form'), picker = document.getElementById('files');
const thumbs = document.getElementById('thumbs');
function showPicked() {
  thumbs.querySelectorAll('[src]').forEach((el) => URL.revokeObjectURL(el.src));
  thumbs.textContent = '';
  const all = [...picker.files], kept = all.slice(0, Number(upForm.dataset.maxN));
  const movies = kept.filter((f) => f.type.startsWith('video/')).length, stills = kept.length - movies;
  for (const f of kept) {
    const el = document.createElement(f.type.startsWith('video/') ? 'video' : 'img');
    el.src = URL.createObjectURL(f); el.alt = '';
    if (el.tagName === 'VIDEO') { el.muted = true; el.playsInline = true; el.preload = 'metadata'; }
    thumbs.append(el);
  }
  const notes = [[stills, '写真'], [movies, '動画']].filter(([n]) => n).map(([n, w]) => `${w} ${n}`);
  let text = notes.join('・');
  if (all.length > kept.length) text += `（${upForm.dataset.maxN} つまでなので、残りの ${all.length - kept.length} つは上げません）`;
  if (kept.some((f) => f.size > Number(upForm.dataset.maxBytes))) text += '（大きすぎて上げられない物があります）';
  document.getElementById('picked').textContent = text;
  upForm.querySelector('button.go').textContent = kept.length ? '上げる' : '記録だけ残す';
}
picker.onchange = showPicked;
document.getElementById('up-form').onsubmit = async (e) => {
  e.preventDefault();
  const form = e.target, go = form.querySelector('button.go');
  if (go.disabled) return;
  const st = document.getElementById('up-status');
  const hid = (document.querySelector('[name=hypothesis]:checked') || {}).value;
  const result = (document.querySelector('[name=result]:checked') || {}).value;
  const files = [...picker.files].slice(0, Number(form.dataset.maxN));
  if (!hid || !result) { st.textContent = '紙と見た事をえらぶ'; return; }
  go.disabled = true; st.textContent = '送っています…';
  let done = '';
  try {
    const r = await fetch(`/toy/${sid}/record-json`, { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: extra({ hypothesis: hid, result, note: document.getElementById('note').value, fix_part: document.getElementById('fix-part').value, fix_change: document.getElementById('fix-change').value, fix_outcome: document.getElementById('fix-outcome').value }) });
    const j = await r.json().catch(() => ({}));
    if (!j.id) { st.textContent = j.error || '残せませんでした'; return; }
    // 記録はできたので欄を空にする。この先の写真で止まっても、押し直しで記録を増やさない。
    form.reset(); showPicked();
    done = '上げました';
    for (const f of files) {
      const m = await fetch(`/record/${j.id}/media`, { method: 'POST', headers: { 'Content-Type': f.type || 'application/octet-stream' }, body: f });
      if (!m.ok) { done = '記録は残しました。' + ((await m.text()) || '写真か動画を上げられませんでした'); break; }
    }
  } catch (err) {
    done = done ? '記録は残しました。写真か動画を送れませんでした' : '送れませんでした。つながりを見て、もう一度押してください';
  } finally { go.disabled = false; }
  st.textContent = done;
  try { await showMine(); } catch (err) { st.textContent = done + '（一覧は、読み込み直すと出ます）'; }
  st.scrollIntoView({ block: 'start' });
};
})();
</script>
"""


def feedback(sid, r):
    """手帖で受けるフィードバック（本人「フィードバックも手帖」、11-04）。順は J-013 のまま: 紙の返事（試した後の紙）→ 人の説明 → 次の版。
    Claude の解釈は、鍵がある時に作り手の道具で作る段で、ここでは出さない（人の説明が先）。"""
    from omochae import loop

    after = f"/sheet/{esc(sid)}/{esc(r['hypothesis_id'])}_v{esc(r.get('sheet_version', 1))}_after.pdf"
    told = loop.explanation(r["id"])
    if told:
        from web.play_server import next_form

        body = f'<p>{esc(told["text"])}</p><p class="meta">次の思いつき: {esc(told["next_idea"])}</p>' + ai_part(r) + next_form(r).replace('</form>', '<input type="hidden" name="back" value="techo"></form>')
    else:
        body = (f'<form method="post" action="/record/{esc(r["id"])}/explain#{esc(r["id"])}"><input type="hidden" name="back" value="techo">'
                '<label class="sr" for="t-' + esc(r["id"]) + '">何が起きたと思う</label><input type="text" id="t-' + esc(r["id"]) + '" name="text" placeholder="何が起きたと思う（わからない、でも）" required>'
                '<input type="text" name="next_idea" placeholder="次に試したい事" required><input type="text" name="by" placeholder="書いた人" required>'
                '<p><button class="go">残す</button></p></form>')
    return f'<p><a href="{after}">試した後の紙</a></p>{body}'


def ai_part(r):
    """人の説明の後に出す AI の返事（J-013 の順の最後）。Claude の読みと、動画を見た観察の補助。どちらも案で、採点しない。"""
    from omochae import loop
    from api import observe

    rid = esc(r["id"])
    out = ""
    i = loop.interpretation(r["id"])
    if i and isinstance(i.get("content"), dict):
        c = i["content"]
        lines = "".join(f"<li>{esc(x)}</li>" for x in c.get("observed", []))
        lines += "".join(f'<li>{esc(x.get("text", ""))}（確からしさ: {esc(x.get("confidence", ""))}）</li>' for x in c.get("causes", []) if isinstance(x, dict))
        lines += "".join(f"<li>分からない事: {esc(x)}</li>" for x in c.get("unknown", []))
        out += f'<div class="item"><p class="meta">Claude の読み（案）</p><ul>{lines}</ul></div>'
    o = observe.observation(r["id"])
    if o:
        lines = "".join(f"<li>{esc(x)}</li>" for x in o.get("observed", [])) + "".join(f"<li>見えなかった事: {esc(x)}</li>" for x in o.get("unclear", []))
        out += f'<div class="item"><p class="meta">観察（Claude の補助）</p><ul>{lines}</ul></div>'
    can_ask, can_watch, why = ai_offer(r["id"])
    buttons = (f'<form method="post" action="/record/{rid}/ai-interpret#{rid}"><input type="hidden" name="back" value="techo"><button class="go">Claude に聞く（何が起きたか）</button></form>' if can_ask else "") + (
               f'<form method="post" action="/record/{rid}/ai-observe#{rid}"><input type="hidden" name="back" value="techo"><button class="go">動画を見てもらう</button></form>' if can_watch else "")
    return out + (f'<div class="row">{buttons}</div>' if buttons else "") + (f'<p class="meta">{why}</p>' if why else "")


def made_item(sid, data, r, photos=True):
    """作った物の 1 件。ギャラリーの札。写真か言葉（感想・工夫）の無い記録は、見せる物が無いので空を返す。
    photos=False は合言葉なしで開いた場。写真も人の書いた文も出さない: 文の中の名前は機械で落とせず、/loop を閉じたのと同じ理由（J-028）。
    ひとこと（note）は学ぶ人の頁に出してこなかった欄なので、ギャラリーにも出さない。
    動きの札（result）を残しても評価はしない。並びと同じく上下を付けない（J-025）。"""
    if not photos:
        return ""
    files = media_of(r["id"])
    pics = "".join((f'<video src="/record/{esc(r["id"])}/media/{esc(f)}" controls muted playsinline preload="metadata"></video>' if f.endswith(("mp4", "mov"))
                    else f'<img src="/record/{esc(r["id"])}/media/{esc(f)}" alt="作った物の写真" loading="lazy">') for f in files)
    words = f'<p>{esc(r["impression"])}</p>' if r.get("impression") else ""
    words += "".join(f'<p class="meta">工夫: {esc(f.get("part", ""))} / {esc(f.get("change", ""))} / {esc(f.get("outcome", ""))}</p>' for f in r.get("fixes", []) if isinstance(f, dict))
    if not pics and not words:
        return ""
    h = next((x for x in data["hypotheses"] if x["id"] == r["hypothesis_id"]), None)
    # 玩具の名前から、その玩具の頁の同じ記録へ行ける（本人の指摘 11-05: 制作した記録と玩具の頁をつなぐ）。
    return (f'<div class="item"><p class="meta"><a href="/toy/{esc(sid)}#{esc(r["id"])}">{esc(data["toy"])}</a>　{esc(hypotheses.letter(h) + " の紙" if h else "")}　{esc(r["result"])}　{esc(r["id"])}</p>'
            + (f'<div class="row">{pics}</div>' if pics else "") + f'{words}</div>')


def gallery_page(sids, photos=True):
    """他の人が作った物のギャラリーと「職人の言葉」の枠（本人の決定 11-05「他の人の作ったものギャラリーは作る」。予想のギャラリーではない）。
    作った物は手元の記録から読む（git の外の物なので、手元のサーバでだけ出す）。並びは記録の順で、上下を付けない（J-025）。
    職人の言葉は、持ち寄りの場（J-021）と有識者の声（U-02）が入る所として枠だけを置く。"""
    cards = ""
    for sid in sids:
        data = hypotheses.load(sid)
        for r in records.all_records(sid):
            cards += made_item(sid, data, r, photos)
    cards = cards or ('<p class="meta">まだ作った物の記録はありません。玩具の頁か手帖で記録を残すと、ここに並びます。</p>' if photos
                      else '<p class="meta">公開のデモでは、人が書いた文と写真は出しません。</p>')
    # 見本（本人の指示、11-04）は本物の後ろに、札を付けて置く。本物が増えても見本と混ざらない。
    from .demo_samples import uploads_html, voice_html
    cards += uploads_html()
    voices = "".join(voice_html(k) for k in ("紙と折りの職人", "からくりの職人", "郷土玩具の作り手"))
    # 寄せられた声（持ち寄りの入口から来た物）は、上げた物と職人の言葉の間に置く（本人の指示 11-05: デモなので想定の内容で）。見本は札と架空の一文つき。
    from .demo_samples import voices_html

    # .gallery で包むのは、手帖の幅（640px）より広く並べるため（STYLE の main:has(.gallery)）。
    return ('<div class="gallery"><div class="top"><h1>作った物と職人の言葉</h1><a href="/">入口へ</a></div>'
            '<nav class="jump" aria-label="この頁の節"><a href="#ageta">他の人が作った物</a><a href="#yose">寄せられた声</a><a href="#shokunin">職人の言葉</a></nav>'
            '<section class="panel" id="ageta"><h2 class="mark">他の人が作った物</h2><p class="meta">記録の順に並べます。上下はありません。型紙は正解ではなく AI が考えた仮説で、作った人の工夫も一緒に残ります。紙で動いても、昔の作り方の証明にはなりません。</p>'
            f'{cards}</section>'
            '<section class="panel" id="yose"><h2 class="mark">寄せられた声</h2><p class="meta">持ち寄りの入口（フォーム）から寄せられた物を、同意・権利・確認・個人情報の床を通してから載せる所です。</p>'
            f'{voices_html()}</section>'
            '<section class="panel" id="shokunin"><h2 class="mark">職人の言葉</h2><p class="meta">紙や玩具を作る人の言葉を、確かめてから載せる所です（持ち寄りの場、J-021）。</p>'
            f'<p><a class="go" href="{esc(FORM_URL)}" rel="noopener" target="_blank">持ち寄りの入口（フォーム）で寄せる</a></p>'
            '<p class="meta">フォームは Google のフォームです。写真や動画を添える時は Google に入る必要があり、添えた人の名前とメールがフォームの持ち主に記録されます。送られた物は確かめてから載せます。</p>'
            f'{voices}</section></div>')


def page(sid, printed_ids, picture_url, uploads=True, msg=""):
    """手帖の頁。仮説の名前と動き方は出さない（字と組の版だけ）。"""
    data = hypotheses.load(sid)
    tpl = TEMPLATES[data.get("template", "slider_fan")]
    hyps = [h for h in data["hypotheses"] if h["id"] in printed_ids]
    from .play_server import printed_versions  # 循環を避けて、ここで読む

    # data-v: 開いた時に刷ってあった一番新しい版。作っている途中で別の人の版が刷られても、報告はこの版への物として残る。
    sheets = "".join(f'<label class="tile"><input type="radio" name="hypothesis" value="{esc(h["id"])}" data-v="{(printed_versions(sid, h["id"]) or [1])[-1]}"{" checked" if i == 0 else ""}>'
                     f'<span class="big">{esc(hypotheses.letter(h))}</span>の紙</label>' for i, h in enumerate(hyps))
    if not hyps:
        sheets = f'<a class="tile" href="/toy/{esc(sid)}">紙を作る</a>'
    results = "".join(f'<label class="tile"><input type="radio" name="result" value="{esc(r)}">{ICONS.get(r, ICONS["わからない"])}{esc(r)}</label>' for r in tpl.RESULTS)
    # 手帖から送った後の返事の文（#121）。着く #mine の頭に出す。上げた後に一覧を入れ替えると一緒に消える。
    note = f'<div role="status"><p id="msg">{esc(msg)}</p></div>' if msg else ""
    mine = ""
    for r in reversed(records.all_records(sid)):
        files = media_of(r["id"]) if uploads else []  # 開いた場は受け口が画像を出さないので、壊れた絵にしない（J-028）
        pics = "".join((f'<video src="/record/{esc(r["id"])}/media/{esc(f)}" controls muted playsinline preload="metadata"></video>' if f.endswith(("mp4", "mov"))
                        else f'<img src="/record/{esc(r["id"])}/media/{esc(f)}" alt="上げた写真" loading="lazy">') for f in files)
        h = next((x for x in data["hypotheses"] if x["id"] == r["hypothesis_id"]), None)
        who = f"{hypotheses.letter(h)} の紙" if h else ""
        mine += (f'<div class="item"><p class="meta">{esc(r["id"])}　{esc(who)}　{esc(r["result"])}</p>{f"<div class=row>{pics}</div>" if pics else ""}'
                 f'{feedback(sid, r)}</div>')
    pic = f'<img src="{esc(picture_url)}" alt="">' if picture_url else ""
    mic = ('<button type="button" class="mic" id="mic" aria-pressed="false" aria-label="話して聞く（もう一度押すと止まる）">'
           '<svg viewBox="0 0 48 48" aria-hidden="true"><rect x="17" y="6" width="14" height="24" rx="7"/><path d="M10 22a14 14 0 0 0 28 0M24 36v6"/></svg></button>')
    body = (f'<div data-sid="{esc(sid)}" hidden></div><div class="top">{pic}<h1>手帖</h1><a href="/toy/{esc(sid)}">{esc(data["toy"])}</a></div>'
            f'<div class="row" role="radiogroup" aria-label="紙">{sheets}</div><p class="meta">{esc(tpl.SHEET_SET)}</p>'
            '<section class="panel" aria-label="聞く"><p class="mark"><svg viewBox="0 0 48 48" aria-hidden="true"><rect x="17" y="6" width="14" height="24" rx="7"/><path d="M10 22a14 14 0 0 0 28 0M24 36v6M17 42h14"/></svg>聞く</p>'
            f'{mic}<form id="ask-form"><label class="sr" for="q">聞きたい事</label><input type="text" id="q" maxlength="300" placeholder="谷折りって？" enterkeyhint="send"><button type="submit" class="go">聞く</button></form>'
            # 断り（本人の決定 11-05、様子の蓄積）: 声は残さず、字にした質問だけを残す。名前は言わないでほしい事も出す。
            '<div class="answer" id="answer" aria-live="polite"></div><p class="meta">' + esc(making_log.ASK_NOTICE) + esc(making_log.ASK_NAME_VOICE) + '</p></section>'
            '<section class="panel" aria-label="上げる"><p class="mark"><svg viewBox="0 0 48 48" aria-hidden="true"><path d="M6 16h8l4-6h12l4 6h8v24H6z"/><circle cx="24" cy="27" r="8"/></svg>上げる</p>'
            f'<form id="up-form" data-max-n="{MAX_PER_RECORD}" data-max-bytes="{MAX_MEDIA}"><label class="shot" for="files"><svg viewBox="0 0 56 56" aria-hidden="true"><path d="M8 18h10l5-7h10l5 7h10v28H8z"/><circle cx="28" cy="31" r="9"/></svg>写真・動画'
            # 合言葉なしで開いたデモ（uploads=False）では、写真と動画の口を閉じる（play_server の受け口も断る）。見た事とひとことは残せる。
            + ('<input type="file" id="files" accept="image/jpeg,image/png,video/mp4,video/quicktime" multiple>' if uploads else '<input type="file" id="files" disabled>')
            + '<span class="picked" id="picked" aria-live="polite"></span><span class="thumbs" id="thumbs"></span></label>'
            + (f'<p class="meta">{MAX_PER_RECORD} つまで・1 つ {MAX_MEDIA // (1024 * 1024)}MB まで</p>' if uploads else
               '<p class="meta">公開のデモでは、写真と動画は上げられません。見た事とひとことは残せます。</p>') +
            f'<div class="row" role="radiogroup" aria-label="見た事">{results}</div>'
            '<label class="sr" for="note">ひとこと</label><input type="text" id="note" maxlength="300" placeholder="ひとこと">'
            # 工夫の欄（本人の言葉 11-05「工夫で乗り切る過程」）。作りながらなので畳んでおく。一部だけ書いても記録は落とさない（play_server.fixes_of）。
            '<details><summary>工夫した所（あれば）</summary><p class="meta">ほかの人も読むので、名前や連絡先は書かないでください。</p><input type="text" id="fix-part" maxlength="100" placeholder="どの部品か"><input type="text" id="fix-change" maxlength="200" placeholder="どう工夫したか"><input type="text" id="fix-outcome" maxlength="200" placeholder="どうなったか"></details>'
            '<label class="check" for="ok"><input type="checkbox" id="ok" required> 大人の手元だけ・顔なし・声なし</label>'
            '<p><button class="go">記録だけ残す</button></p></form><p class="meta" id="up-status" aria-live="polite"></p>'
            f'<div id="mine">{note}{mine}</div></section>')
    return body + SCRIPT
