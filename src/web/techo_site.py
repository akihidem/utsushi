"""手帖を入口のサイトの中に置く（本人の方向転換、2026-11-04 午後）。

本人の言葉: 「最初のサイトと、いまアーティファクトで作った手帖は地続きの方が良いのでは。アーティファクトで作ってと言ったのが良くなかったね」。
本人の指定（同じ日）: 生徒向けの画面は机に置いて声で操作する。両手は工作で塞がっている。写真や動画を上げられる。文字は最小。
判断の芯:
- 入口（A・A′・C の展示）→ 玩具の頁 → 手帖 → 試した記録、を同じサーバの頁で一続きにする。見た目は A′ の白い展示の世界に合わせる
- 聞く口は src/api/ask.py をそのまま使う（仕組みは答えない、よくある言葉は刷った説明から、ほかは鍵がある時だけ Claude）
- 声: ブラウザの音声認識で、1 回押したら話し続けられる形（続けて聞く）と、答えの読み上げ。使えない画面では字の操作だけが残る
- 上げた写真と動画は、その場で作った試した記録（R-番号）に添える。置き場は記録と同じ git の外（data/records/media）
- 写真の撮影情報（位置など）は保存の時に外す。試行の写真を repo に載せた時と同じ扱い（JPEG の APP1 の区画を外す）
"""
import html
import re

from omochae import hypotheses, records
from omochae.compose import TEMPLATES
from omochae.form_import import FORM_URL

MEDIA_TYPES = {"image/jpeg": "jpg", "image/png": "png", "video/mp4": "mp4", "video/quicktime": "mov"}
MAX_MEDIA = 20 * 1024 * 1024
MAX_PER_RECORD = 3
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
    """JPEG の撮影情報（EXIF・XMP の APP1）を外す。画素は変えない。形が読めない時はそのまま返す（画像として保存しない判断は呼ぶ側）。"""
    if data[:2] != b"\xff\xd8":
        return data
    out, p = bytearray(data[:2]), 2
    try:
        while p < len(data):
            if data[p] != 0xFF:
                return data
            m = data[p + 1]
            if m == 0xDA:
                out += data[p:]
                return bytes(out)
            n = int.from_bytes(data[p + 2:p + 4], "big")
            if m != 0xE1:
                out += data[p:p + 2 + n]
            p += 2 + n
    except IndexError:
        return data
    return bytes(out)


def save_media(rid, ctype, data):
    """Returns (ファイル名 or None, 失敗の文)。記録が実在し、型と大きさと数の上限を守る物だけを置く。"""
    if not re.fullmatch(r"R-\d{4,}", rid) or not (records.folder() / f"{rid}.json").exists():
        return None, "記録が無い"
    ext = MEDIA_TYPES.get(ctype)
    if not ext:
        return None, "写真（JPEG・PNG）か動画（MP4・MOV）だけ"
    if not 0 < len(data) <= MAX_MEDIA:
        return None, "1 つ 20MB まで"
    d = media_dir(rid)
    d.mkdir(parents=True, exist_ok=True)
    have = sorted(d.glob("m*.*"))
    if len(have) >= MAX_PER_RECORD:
        return None, "1 つの記録に 3 つまで"
    name = f"m{len(have) + 1}.{ext}"
    (d / name).write_bytes(strip_jpeg_meta(data) if ext == "jpg" else data)
    return name, ""


def media_of(rid):
    d = media_dir(rid)
    return [p.name for p in sorted(d.glob("m*.*"))] if d.exists() else []


# 色は皮の変数から取る（skin.py の SKINS。本人の指示 11-05: A′ 白の展示と C 黒のジンを一気通貫に）。
# 手帖だけ書体をゴシックにし字を大きくするのは、机に置いて離れて読むため（本人の指定 11-04「文字は最小」）。骨（頭の帯・余白）は skin.shell が持つ。
STYLE = """
body.techo{font-family:"Noto Sans JP","Hiragino Sans",system-ui,sans-serif;font-size:18px}
.techo main{max-width:640px;margin:0 auto;padding:20px max(16px,env(safe-area-inset-left,0px)) 64px;display:grid;gap:22px}
.techo main:has(.gallery){max-width:960px}
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
.techo .mic{width:96px;height:96px;border-radius:50%;border:0;background:var(--accent);color:var(--onaccent);display:grid;place-items:center;cursor:pointer;justify-self:center;margin:0}
.techo .mic svg{width:48px;height:48px;stroke:var(--onaccent);fill:none;stroke-width:3;stroke-linecap:round}
/* 聞いている間は地と字を入れ替える。緑などの別の色を足さず、どちらの皮でも「今は違う状態」と読めるようにするため。 */
.techo .mic[aria-pressed="true"]{background:var(--fg);color:var(--bg)}.techo .mic[aria-pressed="true"] svg{stroke:var(--bg)}
.techo .answer{font-size:26px;line-height:1.6;white-space:pre-wrap;min-height:1.6em}
.techo .shot{display:grid;place-items:center;gap:6px;border:2px dashed var(--accent);border-radius:16px;padding:22px;cursor:pointer;color:var(--accent);position:relative;margin:0}
.techo .shot svg{width:56px;height:56px;stroke:var(--accent);fill:none;stroke-width:2.5}
.techo .shot input{position:absolute;opacity:0;width:1px;height:1px}
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
const say = (t) => { try { if (!('speechSynthesis' in window)) return; speechSynthesis.cancel(); const u = new SpeechSynthesisUtterance(t); u.lang = 'ja-JP'; speechSynthesis.speak(u); } catch (e) {} };
const ans = document.getElementById('answer');
async function ask(q) {
  const hid = (document.querySelector('[name=hypothesis]:checked') || {}).value;
  if (!q || !hid) return;
  ans.textContent = '…';
  const r = await fetch(`/toy/${sid}/ask-json`, { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: new URLSearchParams({ hypothesis: hid, question: q }) });
  const j = await r.json().catch(() => ({ text: '今は答えられません' }));
  ans.textContent = j.text; say(j.text);
}
document.getElementById('ask-form').onsubmit = (e) => { e.preventDefault(); ask(document.getElementById('q').value.trim()); };
// 音声認識: 1 回押すと話し続けられる（続けて聞く）。もう 1 回押すと止まる。使えない画面ではボタンを隠し、字の操作だけにする。
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
const mic = document.getElementById('mic');
if (!SR) { mic.hidden = true; } else {
  let rec = null, on = false;
  mic.onclick = () => {
    if (on) { on = false; rec && rec.stop(); mic.setAttribute('aria-pressed', 'false'); return; }
    rec = new SR(); rec.lang = 'ja-JP'; rec.continuous = true; rec.interimResults = false;
    rec.onresult = (ev) => { const t = ev.results[ev.results.length - 1][0].transcript.trim(); document.getElementById('q').value = t; ask(t); };
    rec.onend = () => { if (on) { try { rec.start(); } catch (e) {} } };
    on = true; mic.setAttribute('aria-pressed', 'true'); rec.start();
  };
}
// 上げる: 先に記録を作り（見た事）、その R-番号に写真と動画を 1 つずつ送る。
document.getElementById('up-form').onsubmit = async (e) => {
  e.preventDefault();
  const st = document.getElementById('up-status');
  const hid = (document.querySelector('[name=hypothesis]:checked') || {}).value;
  const result = (document.querySelector('[name=result]:checked') || {}).value;
  const files = [...document.getElementById('files').files].slice(0, 3);
  if (!hid || !result) { st.textContent = '紙と見た事をえらぶ'; return; }
  st.textContent = '…';
  const r = await fetch(`/toy/${sid}/record-json`, { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: new URLSearchParams({ hypothesis: hid, result, note: document.getElementById('note').value }) });
  const j = await r.json().catch(() => ({}));
  if (!j.id) { st.textContent = j.error || '残せませんでした'; return; }
  for (const f of files) {
    const m = await fetch(`/record/${j.id}/media`, { method: 'POST', headers: { 'Content-Type': f.type || 'application/octet-stream' }, body: f });
    if (!m.ok) { st.textContent = (await m.text()) || '上げられませんでした'; return; }
  }
  location.href = `/toy/${sid}/techo#mine`;
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
        body = (f'<form method="post" action="/record/{esc(r["id"])}/explain"><input type="hidden" name="back" value="techo">'
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
    buttons = (f'<form method="post" action="/record/{rid}/ai-interpret"><input type="hidden" name="back" value="techo"><button class="go">Claude に聞く（何が起きたか）</button></form>'
               f'<form method="post" action="/record/{rid}/ai-observe"><input type="hidden" name="back" value="techo"><button class="go">動画を見てもらう</button></form>')
    return out + f'<div class="row">{buttons}</div>'


def gallery_page(sids):
    """サイトの「上げた物のギャラリー」と「職人の言葉」の枠（本人の設計、11-04）。上げた物は手元の記録から読む（git の外の物なので、手元のサーバでだけ出す）。
    並びは記録の順で、上下を付けない（J-025）。職人の言葉は、持ち寄りの場（J-021）と有識者の声（U-02）が入る所として枠だけを置く。"""
    cards = ""
    for sid in sids:
        data = hypotheses.load(sid)
        for r in records.all_records(sid):
            files = media_of(r["id"])
            if not files:
                continue
            pics = "".join((f'<video src="/record/{esc(r["id"])}/media/{esc(f)}" controls muted playsinline preload="metadata"></video>' if f.endswith(("mp4", "mov"))
                            else f'<img src="/record/{esc(r["id"])}/media/{esc(f)}" alt="上げた写真" loading="lazy">') for f in files)
            h = next((x for x in data["hypotheses"] if x["id"] == r["hypothesis_id"]), None)
            cards += (f'<div class="item"><p class="meta">{esc(data["toy"])}　{esc(hypotheses.letter(h) + " の紙" if h else "")}　{esc(r["result"])}　{esc(r["id"])}</p>'
                      f'<div class="row">{pics}</div></div>')
    cards = cards or '<p class="meta">まだ上げた物はありません。手帖の「上げる」から上げると、ここに並びます。</p>'
    # 見本（本人の指示、11-04）は本物の後ろに、札を付けて置く。本物が増えても見本と混ざらない。
    from .demo_samples import uploads_html, voice_html
    cards += uploads_html()
    voices = "".join(voice_html(k) for k in ("紙と折りの職人", "からくりの職人", "郷土玩具の作り手"))
    # 寄せられた声（持ち寄りの入口から来た物）は、上げた物と職人の言葉の間に置く（本人の指示 11-05: デモなので想定の内容で）。見本は札と架空の一文つき。
    from .demo_samples import voices_html

    # .gallery で包むのは、手帖の幅（640px）より広く並べるため（STYLE の main:has(.gallery)）。
    return ('<div class="gallery"><div class="top"><h1>上げた物</h1><a href="/">入口へ</a></div>'
            '<section class="panel" aria-label="上げた物"><p class="mark">上げた物</p><p class="meta">記録の順に並べます。上下はありません。紙で動いても、昔の作り方の証明にはなりません。</p>'
            f'{cards}</section>'
            '<section class="panel" aria-label="寄せられた声"><p class="mark">寄せられた声</p><p class="meta">持ち寄りの入口（フォーム）から寄せられた物を、同意・権利・確認・個人情報の床を通してから載せる所です。</p>'
            f'{voices_html()}</section>'
            '<section class="panel" aria-label="職人の言葉"><p class="mark">職人の言葉</p><p class="meta">紙や玩具を作る人の言葉を、確かめてから載せる所です（持ち寄りの場、J-021）。</p>'
            f'<p><a class="go" href="{esc(FORM_URL)}" rel="noopener" target="_blank">持ち寄りの入口（フォーム）で寄せる</a></p>'
            '<p class="meta">フォームは Google のフォームです。写真や動画を添える時は Google に入る必要があり、添えた人の名前とメールがフォームの持ち主に記録されます。送られた物は確かめてから載せます。</p>'
            f'{voices}</section></div>')


def page(sid, printed_ids, picture_url):
    """手帖の頁。仮説の名前と動き方は出さない（字と組の版だけ）。予想の前は呼ばない（呼ぶ側が F9.prediction を見る）。"""
    data = hypotheses.load(sid)
    tpl = TEMPLATES[data.get("template", "slider_fan")]
    hyps = [h for h in data["hypotheses"] if h["id"] in printed_ids]
    sheets = "".join(f'<label class="tile"><input type="radio" name="hypothesis" value="{esc(h["id"])}"{" checked" if i == 0 else ""}>'
                     f'<span class="big">{esc(hypotheses.letter(h))}</span>の紙</label>' for i, h in enumerate(hyps))
    if not hyps:
        sheets = f'<a class="tile" href="/toy/{esc(sid)}">紙を刷る</a>'
    results = "".join(f'<label class="tile"><input type="radio" name="result" value="{esc(r)}">{ICONS.get(r, ICONS["わからない"])}{esc(r)}</label>' for r in tpl.RESULTS)
    mine = ""
    for r in reversed(records.all_records(sid)):
        files = media_of(r["id"])
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
            f'{mic}<form id="ask-form"><label class="sr" for="q">聞きたい事</label><input type="text" id="q" maxlength="300" placeholder="谷折りって？" enterkeyhint="send"></form>'
            '<div class="answer" id="answer" aria-live="polite"></div></section>'
            '<section class="panel" aria-label="上げる"><p class="mark"><svg viewBox="0 0 48 48" aria-hidden="true"><path d="M6 16h8l4-6h12l4 6h8v24H6z"/><circle cx="24" cy="27" r="8"/></svg>上げる</p>'
            '<form id="up-form"><label class="shot" for="files"><svg viewBox="0 0 56 56" aria-hidden="true"><path d="M8 18h10l5-7h10l5 7h10v28H8z"/><circle cx="28" cy="31" r="9"/></svg>写真・動画'
            '<input type="file" id="files" accept="image/jpeg,image/png,video/mp4,video/quicktime" multiple></label>'
            f'<div class="row" role="radiogroup" aria-label="見た事">{results}</div>'
            '<label class="sr" for="note">ひとこと</label><input type="text" id="note" maxlength="300" placeholder="ひとこと">'
            '<label class="check" for="ok"><input type="checkbox" id="ok" required> 大人の手元だけ・顔なし・声なし</label>'
            '<p><button class="go">上げる</button></p></form><p class="meta" id="up-status" aria-live="polite"></p>'
            f'<div id="mine">{mine}</div></section>')
    return body + SCRIPT
