"""手帖の記録の頁（上げた物とフィードバック）と、上げた物の受け口・上げた物の頁（本人の方向転換、2026-11-04 午後）。作る頁は techo_step（1 手 1 画面、#87）。

本人の言葉: 「最初のサイトと、いまアーティファクトで作った手帖は地続きの方が良いのでは。アーティファクトで作ってと言ったのが良くなかったね」。
本人の指定（同じ日）: 生徒向けの画面は机に置いて声で操作する。両手は工作で塞がっている。写真や動画を上げられる。文字は最小。
判断の芯:
- 入口（A・A′・C の展示）→ 玩具の頁 → 手帖 → 試した記録、を同じサーバの頁で一続きにする。見た目は A′ の白い展示の世界に合わせる
- 聞く口は src/api/ask.py をそのまま使う（仕組みは答えない、語そのものを尋ねる短い問いは刷った説明から、ほかは鍵がある時だけ Claude）
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
from omochae import contrib, hypotheses, media_review, records
from omochae.form_import import FORM_URL

from . import wording

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


def result_icon(word, words):
    """札の絵。言葉の絵が無い札は、札の並びで決める。「わからない」を除いた最後が動かない側で、ほかは動いた側（engine_bundle と同じ読み）。
    全部を「?」にすると、「転がった」まで分からない札に見える（#146）。"""
    if word in ICONS:
        return ICONS[word]
    sure = [w for w in words if w != "わからない"]
    return ICONS["動かない" if len(sure) > 1 and word == sure[-1] else "動いた"]


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
    """動画の撮影情報と音を落として入れ物を作り直す。絵は再符号化しない。Returns (中身 or None, 失敗の文)。

    絵の流れだけを写す（-map）。全体の欄だけを消しても、字幕や時刻つきの情報の流れと流れごとの欄に位置が残るため。
    音を落とすのは本人の決定（11-05「声は字にして、声そのものは残しません」、#314）。頁の muted だけでは、ファイルに声が残る。
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
                                "-map", "0:V", "-an", "-map_metadata", "-1", "-map_metadata:s", "-1", "-map_chapters", "-1",
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


def seen_observation(rid, up_key=None):
    """その画面に出してよい観察の文。確認の前の動画を読んだ文は、その動画と同じに、上げた本人の画面にだけ出す（media_review.shown_to）。
    どの動画を読んだかの控えが無い前の文は、その記録の動画を見られる画面にだけ出す。"""
    from api import observe

    o = observe.observation(rid)
    if not o:
        return None
    read = [o["video"]] if o.get("video") else [f for f in media_of(rid) if f.endswith(("mp4", "mov"))]
    return o if media_review.shown_to(rid, read, up_key) else None


def ai_offer(rid, up_key=None):
    """AI の 2 つの口のうち、今押して進める物と、進めない時に出す 1 行を返す（#130）。

    押しても断りの文が返るだけの釦を出さないため。play_server の受け口の断りは、古い頁から押された時のために残す。
    """
    if not ask._key_present():
        return False, False, "AI の返事は、この場では使えません。"
    # 人や声が入ると確かめた動画は AI にも渡さない（#314）。確認の前の動画は、上げた本人の画面からだけ渡す。
    has_video = any(f.endswith(("mp4", "mov")) for f in media_review.shown_to(rid, media_of(rid), up_key))
    return True, has_video, "" if has_video else "動画を上げると、Claude が見えた事を返します。"


# 色は皮の変数から取る（skin.py の SKINS。本人の指示 11-05: A′ 白の展示と C 黒のジンを一気通貫に）。
# 手帖だけ書体をゴシックにし字を大きくするのは、机に置いて離れて読むため（本人の指定 11-04「文字は最小」）。骨（頭の帯・余白）は skin.shell が持つ。
STYLE = """
body.techo{font-family:"Noto Sans JP","Hiragino Sans",system-ui,sans-serif;font-size:18px}
.techo main{max-width:640px;margin:0 auto;padding:20px max(16px,env(safe-area-inset-left,0px)) 64px;display:grid;gap:22px}
.techo h1{font-family:"Noto Serif CJK JP","Hiragino Mincho ProN",serif;font-weight:400;font-size:26px;letter-spacing:.3em;margin:0}
.techo .top{display:flex;align-items:center;gap:14px}.techo .top img{width:56px;height:84px;object-fit:cover;border:1px solid var(--frame)}
.techo .top a{margin-left:auto;font-size:14px;color:var(--accent)}
.techo .row{display:flex;gap:12px;flex-wrap:wrap}
.techo .panel{border:1px solid var(--frame);border-radius:18px;padding:18px;display:grid;gap:14px;background:var(--paper)}
.techo .mark{display:flex;align-items:center;gap:12px;font-family:"Noto Serif CJK JP",serif;font-size:22px;letter-spacing:.15em;margin:0}
.techo .mark svg{width:40px;height:40px;stroke:var(--accent);fill:none;stroke-width:3;stroke-linecap:round;stroke-linejoin:round}
.techo input[type=text],.techo input[type=number]{font:inherit;font-size:22px;border:2px solid var(--frame);border-radius:12px;padding:14px 16px;width:100%;box-sizing:border-box;background:var(--field);color:var(--fg)}
.techo .go{font:inherit;font-size:20px;letter-spacing:.05em;background:var(--accent);color:var(--onaccent);border:0;padding:16px 28px;border-radius:12px;cursor:pointer;margin:0}
.techo .meta{font-size:12px;color:var(--mute)}
.techo .item{border-top:1px solid var(--rule);padding-top:10px;display:grid;gap:6px}
.techo .item img,.techo .item video{height:110px;max-width:100%;border:1px solid var(--frame);border-radius:8px}
.techo .sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
.techo :focus-visible{outline:3px solid var(--accent);outline-offset:2px}
"""

def feedback(sid, r, photos=True, up_key=None, can_tell=False):
    """手帖で受けるフィードバック（本人「フィードバックも手帖」、11-04）。順は J-013 のまま: 紙の返事（試した後の紙）→ 人の説明 → 次の版。
    Claude の解釈は、鍵がある時に作り手の道具で作る段で、ここでは出さない（人の説明が先）。
    photos=False は合言葉なしで開いた場。手帖の札は人ごとに分かれていないので、玩具の頁と同じく説明の文も次の版の欄も出さない（J-028、#336）。
    can_tell は、この画面がこの記録を残した時に真。説明の欄はその画面にだけ出す（受け口も断る。records.mine）。"""
    from omochae import loop

    after = f"/sheet/{esc(sid)}/{esc(r['hypothesis_id'])}_v{esc(r.get('sheet_version', 1))}_after.pdf"
    told = loop.explanation(r["id"])
    if told and not photos:
        body = '<p class="meta">説明を残しました。</p>' + ai_part(r, up_key, photos=False)
    elif told:
        from web.play_server import next_form

        body = f'<p>{esc(told["text"])}</p><p class="meta">次の思いつき: {esc(told["next_idea"])}</p>' + ai_part(r, up_key) + next_form(r).replace('</form>', '<input type="hidden" name="back" value="techo"></form>')
    elif not can_tell:
        body = ""
    else:
        body = (f'<form method="post" action="/record/{esc(r["id"])}/explain#{esc(r["id"])}"><input type="hidden" name="back" value="techo">'
                '<label class="sr" for="t-' + esc(r["id"]) + '">何が起きたと思う</label><input type="text" id="t-' + esc(r["id"]) + '" name="text" placeholder="何が起きたと思う（わからない、でも）" required>'
                '<input type="text" name="next_idea" placeholder="次に試したい事" required><input type="text" name="by" placeholder="書いた人" required>'
                '<p><button class="go">残す</button></p></form>')
    # 合言葉なしの場では OWN-n の紙を開かない（think_sheet.opens）。行き止まりになるので、札に紙への道を出さない。
    if not photos and str(r["hypothesis_id"]).startswith("OWN-"):
        return body
    return f'<p><a href="{after}">試した後の紙</a></p>{body}'


def ai_part(r, up_key=None, photos=True):
    """人の説明の後に出す AI の返事（J-013 の順の最後）。Claude の読みと、動画を見た観察の補助。どちらも案で、採点しない。
    photos=False は合言葉なしで開いた場で、読みと観察の文を出さない（J-028）。"""
    from omochae import loop
    from api import observe

    rid = esc(r["id"])
    out = ""
    i = loop.interpretation(r["id"]) if photos else None
    if i and isinstance(i.get("content"), dict):
        c = i["content"]
        lines = "".join(f"<li>{esc(x)}</li>" for x in c.get("observed", []))
        lines += "".join(f'<li>{esc(x.get("text", ""))}（確からしさ: {esc(x.get("confidence", ""))}）</li>' for x in c.get("causes", []) if isinstance(x, dict))
        lines += "".join(f"<li>分からない事: {esc(x)}</li>" for x in c.get("unknown", []))
        out += f'<div class="item"><p class="meta">Claude の読み（案）</p><ul>{lines}</ul></div>'
    o = seen_observation(r["id"], up_key) if photos else None
    if o:
        lines = "".join(f"<li>{esc(x)}</li>" for x in o.get("observed", [])) + "".join(f"<li>見えなかった事: {esc(x)}</li>" for x in o.get("unclear", []))
        out += f'<div class="item"><p class="meta">観察（Claude の補助）</p><ul>{lines}</ul></div>'
    can_ask, can_watch, why = ai_offer(r["id"], up_key)
    buttons = (f'<form method="post" action="/record/{rid}/ai-interpret#{rid}"><input type="hidden" name="back" value="techo"><button class="go">Claude に聞く（何が起きたか）</button></form>' if can_ask else "") + (
               f'<form method="post" action="/record/{rid}/ai-observe#{rid}"><input type="hidden" name="back" value="techo"><button class="go">動画を見てもらう</button></form>' if can_watch else "")
    return out + (f'<div class="row">{buttons}</div>' if buttons else "") + (f'<p class="meta">{why}</p>' if why else "")


# /gallery は机に置く道具でなく読む頁なので、手帖の STYLE を使わず、骨の書体と皮の角 0 で組む（#126）。
GALLERY_STYLE = """
main:has(.gallery){max-width:960px;padding-top:20px}
.gallery{display:grid;gap:22px}
.gallery .top{display:flex;align-items:center;gap:14px}.gallery .top a{margin-left:auto;font-size:14px;white-space:nowrap}
.gallery h1{font-size:clamp(19px,5vw,26px);letter-spacing:.2em}
.gallery .jump{display:flex;gap:6px 18px;flex-wrap:wrap;margin:-8px 0 0;font-size:14px;letter-spacing:.1em}
.gallery .panel{border:1px solid var(--frame);border-radius:0;padding:18px;display:grid;gap:14px;background:var(--paper)}
.gallery .mark{font-size:22px;letter-spacing:.15em;margin:0}
.gallery p{margin:0}
.gallery .samples{display:grid;gap:10px;margin:0}
.gallery .is-sample{border:1px dashed var(--frame);padding:10px}
.gallery .go{display:inline-block;background:var(--accent);color:var(--onaccent);border:0;padding:12px 22px;letter-spacing:.05em}
"""


def made_item(sid, data, r, photos=True):
    """作った物の 1 件。ギャラリーの札。写真か言葉（感想・工夫）の無い記録は、見せる物が無いので空を返す。
    photos=False は合言葉なしで開いた場。写真も人の書いた文も出さない: 文の中の名前は機械で落とせず、/loop を閉じたのと同じ理由（J-028）。
    ひとこと（note）は学ぶ人の頁に出してこなかった欄なので、ギャラリーにも出さない。
    動きの札（result）を残しても評価はしない。並びと同じく上下を付けない（J-025）。"""
    if not photos:
        return ""
    # 物だけと人が確かめた写真と動画だけを出す。ほかは字だけになる（本人の決定 11-05、#314）。
    files = media_review.public(r["id"], media_of(r["id"]))
    pics = "".join((f'<video src="/record/{esc(r["id"])}/media/{esc(f)}" controls muted playsinline preload="metadata"></video>' if f.endswith(("mp4", "mov"))
                    else f'<img src="/record/{esc(r["id"])}/media/{esc(f)}" alt="作った物の写真" loading="lazy">') for f in files)
    words = f'<p>{esc(r["impression"])}</p>' if r.get("impression") else ""
    words += "".join(f'<p class="meta">工夫: {esc(f.get("part", ""))} / {esc(f.get("change", ""))} / {esc(f.get("outcome", ""))}</p>' for f in r.get("fixes", []) if isinstance(f, dict))
    if not pics and not words:
        return ""
    h = next((x for x in data["hypotheses"] if x["id"] == r["hypothesis_id"]), None)
    # 玩具の名前から、その玩具の頁の同じ記録へ行ける（本人の指摘 11-05: 制作した記録と玩具の頁をつなぐ）。
    return (f'<div class="item"><p class="meta"><a href="/toy/{esc(sid)}#{esc(r["id"])}">{esc(data["toy"])}</a>　{esc(hypotheses.letter(h) + " の紙" if h else "")}　{esc(records.result_word(r))}　{esc(wording.record_no(r["id"]))}</p>'
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

    # .gallery で包むのは、手帖の幅（640px）より広く並べるため（GALLERY_STYLE の main:has(.gallery)）。
    return ('<div class="gallery"><div class="top"><h1>作った物と職人の言葉</h1><a href="/">入口へ</a></div>'
            '<nav class="jump" aria-label="この頁の節"><a href="#ageta">他の人が作った物</a><a href="#yose">寄せられた声</a><a href="#shokunin">職人の言葉</a></nav>'
            '<section class="panel" id="ageta"><h2 class="mark">他の人が作った物</h2><p class="meta">記録の順に並べます。上下はありません。型紙は正解ではなく AI が考えた仮説で、作った人の工夫も一緒に残ります。紙で動いても、昔の作り方の証明にはなりません。</p>'
            f'{cards}</section>'
            f'<section class="panel" id="yose"><h2 class="mark">寄せられた声</h2><p class="meta">{esc(wording.plain("持ち寄りの入口（フォーム）から寄せられた物を、同意・権利・確認・個人情報の床を通してから載せる所です。"))}</p>'
            f'{voices_html()}</section>'
            f'<section class="panel" id="shokunin"><h2 class="mark">職人の言葉</h2><p class="meta">{esc(wording.plain("紙や玩具を作る人の言葉を、確かめてから載せる所です（持ち寄りの場、J-021）。"))}</p>'
            f'<p><a class="go" href="{esc(FORM_URL)}" rel="noopener" target="_blank">持ち寄りの入口（フォーム）で寄せる</a></p>'
            '<p class="meta">フォームは Google のフォームです。写真や動画を添える時は Google に入る必要があり、添えた人の名前とメールがフォームの持ち主に記録されます。送られた物は確かめてから載せます。</p>'
            f'{voices}</section></div>')


def records_page(sid, uploads=True, msg="", up_key=None, rec_key=None):
    """手帖の記録の頁。作る頁（techo_step）から外した札を置く: 上げた物・工夫・試した後の紙 → 説明 → AI の順（J-013）。
    作る頁の字に記録の番号と「の紙」を出さない決定（本人の決定 11-05、#87）のために分けた。のこした後と、説明を送った後にここへ着く。"""
    data = hypotheses.load(sid)
    from . import hanasu  # 循環を避けて、ここで読む

    # 手帖から送った後の返事の文（#121）。着く #mine の頭に出す。
    note = f'<div role="status"><p id="msg">{esc(msg)}</p></div>' if msg else ""
    mine = ""
    for r in reversed(records.all_records(sid)):
        # 開いた場は受け口が画像を出さないので、壊れた絵にしない（J-028）。確認の前の物は、上げた本人の画面にだけ、受け取りを確かめられるように出す（#314）。
        files = media_review.shown_to(r["id"], media_of(r["id"]), up_key) if uploads else []
        pics = "".join((f'<video src="/record/{esc(r["id"])}/media/{esc(f)}" controls muted playsinline preload="metadata"></video>' if f.endswith(("mp4", "mov"))
                        else f'<img src="/record/{esc(r["id"])}/media/{esc(f)}" alt="上げた写真" loading="lazy">') for f in files)
        h = next((x for x in data["hypotheses"] if x["id"] == r["hypothesis_id"]), None)
        who = f"{hypotheses.letter(h)} の紙" if h else ""
        mine += (f'<div class="item"><p class="meta">{esc(wording.record_no(r["id"])) + "　" if uploads else ""}{esc(who)}　{esc(records.result_word(r))}</p>{f"<div class=row>{pics}</div>" if pics else ""}'
                 # 記録の「工夫した所（直した所）」と、上げた後に足す口（一周の 2 と 3、Issue #279）。開いた場では、人の言葉を出さない。
                 f'{hanasu.keep_box(sid, r, show_shared=uploads, can_add=records.mine(r["id"], rec_key))}'
                 f'{feedback(sid, r, photos=uploads, up_key=up_key, can_tell=records.mine(r["id"], rec_key))}</div>')
    # 話す口の見た目と動きは、頁に 1 回だけ置く。
    return (f'<div class="top"><h1>手帖</h1><a href="/toy/{esc(sid)}">{esc(data["toy"])}</a></div>'
            f'<p class="links"><a href="/toy/{esc(sid)}/techo">手帖をひらく（作りながら聞く・上げる）</a></p>'
            f'<section class="panel" aria-label="上げる"><div id="mine">{note}{mine}</div></section>') + hanasu.assets()
