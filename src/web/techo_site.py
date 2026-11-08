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
from omochae import contrib, hypotheses, media_review, records, words_review
from omochae.form_import import FORM_URL

from . import wording

MEDIA_TYPES = {"image/jpeg": "jpg", "image/png": "png", "video/mp4": "mp4", "video/quicktime": "mov"}
MAX_MEDIA = 20 * 1024 * 1024
MAX_PER_RECORD = 3
# 合言葉なしで開いた場の写真と動画の置き場の合計（本人の決定 11-06「公開のデモでも写真と動画を上げられるようにしてください」）。
# 誰でも上げられる場なので、機械の空き（11-06 に 102G）を埋めさせない。2GB は空きの 2% で、20MB の動画なら 100 本・写真なら数百枚。
# 記録を作る口は書き込みの数の上限が絞り、1 つの記録には MAX_PER_RECORD までなので、1 人で一気に埋める形にはなりにくい
PUBLIC_MEDIA_TOTAL = 2 * 1024 * 1024 * 1024
MISMATCH = "中身を写真か動画として読めません（JPEG・PNG・MP4・MOV だけ）"
# 動画を写す時に、元より増えてよい量（セキュリティの点検 U1）。絵の流れを写すだけで音と撮影情報を外すので、ふつうは元より小さい。
# 同じコマを何度も指す小さな動画は、写すと何倍にも膨らみ、合言葉なしの場でも一時の置き場とメモリを埋められた。動画の受け口（trial_video.ROOM）と同じ考えで、
# 1 つ 20MB までのこの口に合わせて小さく取る。
VIDEO_ROOM = 4 * 1024 * 1024
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


def media_bytes():
    """置き場の写真と動画と、字にする前の声の大きさの合計（確かめの控えの json と字は数えない）。公開の場の合計の上限を見る時に、受ける前に数える。
    声（voice/*.mka・本人の言葉 11-08「全部残していいことにしたい。」）も数える。数えないと、公開の場で声の分だけ上限を越えて機械を埋められるため。
    声の区切り（voice/t<n>.mka）は *.mka に入る。カメラの区切り（voice/k<n>.webm・k<n>.mp4・本人の言葉 11-08「カメラの映像は、押した時の短い区切りだけ。」）も同じわけで数える。"""
    root = records.folder() / "media"
    pats = ("R-*/m*.*", "R-*/voice/*.mka", "R-*/voice/k*.webm", "R-*/voice/k*.mp4")
    return sum(p.stat().st_size for pat in pats for p in root.glob(pat)) if root.exists() else 0


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
    頁に出す動画からは音を落とす（頁の muted だけでは、ファイルに声が残る）。声は save_media が別に写し、この機械の中で字にしてから消す
    （本人の言葉 11-08「全部残していいことにしたい。」・omochae.voice_text）。前は本人の決定（11-05「声は字にして、声そのものは残しません」、#314）で、字にせずに捨てていた。
    読み手を mov に決める（-f mov）。中身の形で読み手を選ばせると、ほかのファイルや URL を指す一覧（HLS など）を読みに行くため。
    """
    if data[4:8] not in (b"ftyp", b"moov", b"mdat", b"wide", b"free", b"skip"):
        return None, MISMATCH
    if not shutil.which("ffmpeg"):
        return None, "この機械では動画を受けられません（撮影情報を外す ffmpeg が無い）"
    with tempfile.TemporaryDirectory() as tmp:
        src, dst = pathlib.Path(tmp) / "in", pathlib.Path(tmp) / f"out.{ext}"
        src.write_bytes(data)
        # -protocol_whitelist file: 読むのは置いたファイルだけ（ほかの道を開かない）。-fs: 書き出しの大きさの上限。-fs は超えても 0 で終わるので、後で比べる。
        limit = len(data) + VIDEO_ROOM
        try:
            r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-protocol_whitelist", "file", "-f", "mov", "-i", str(src),
                                "-map", "0:V", "-an", "-map_metadata", "-1", "-map_metadata:s", "-1", "-map_chapters", "-1",
                                "-c", "copy", "-fs", str(limit), "-f", ext, str(dst)], capture_output=True, timeout=config.VIDEO_TIMEOUT)
        except (OSError, subprocess.TimeoutExpired):
            return None, MISMATCH
        if r.returncode != 0 or not dst.exists() or dst.stat().st_size >= limit:
            return None, MISMATCH
        return dst.read_bytes(), ""


def save_media(rid, ctype, data, keep_voice=False):
    """Returns (ファイル名 or None, 失敗の文)。記録が実在し、型と大きさと数の上限を守り、中身が読める物だけを、撮影情報を外して置く。

    keep_voice: 動画の声を、字にするために非公開で写すか（voice/m<n>.mka）。字にする道具がある時だけ、サーバが True で呼ぶ
    （道具が無い機械では字にできず、72 時間置いて消すだけになるので、今までどおり受ける時に落とす）。字にするのはサーバの作業列（web.play_server）。"""
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
    if keep_voice and ext in ("mp4", "mov"):
        from omochae import voice_text

        with tempfile.TemporaryDirectory() as tmp:
            src = pathlib.Path(tmp) / "in"
            src.write_bytes(data)
            # 声を写せない形（音の無い動画など）でも、動画は受け取る
            voice_text.copy_voice(src, voice_text.voice_dir(rid) / f"m{len(have) + 1}.mka", len(data) + VIDEO_ROOM)
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
    取り下げで説明の字が空になった記録は、人の説明が先（J-013）を満たさないので、どちらの口も出さない。
    """
    from omochae import loop

    if not loop.explained(rid):
        return False, False, ""
    if not ask._key_present():
        return False, False, "AI の返事は、この場では使えません。"
    # 人や声が入ると確かめた動画は AI にも渡さない（#314）。確認の前の動画は、上げた本人の画面からだけ渡す。
    has_video = any(f.endswith(("mp4", "mov")) for f in media_review.shown_to(rid, media_of(rid), up_key))
    return True, has_video, "" if has_video else "動画を上げると、Claude が見えた事を返します。"


# 色は皮の変数から取る（skin.py の SKINS。本人の指示 11-05: A′ 白の展示と C 黒のジンを一気通貫に）。
# 手帖の字を大きくするのは、机に置いて離れて読むため（本人の指定 11-04「文字は最小」）。書体は他の頁と同じ明朝にした（本人のサイトの見直し 11-07 22:16
# 「のこす、手帖、のフォントが違う。」。前は手帖だけゴシック）。骨（頭の帯・余白）は skin.shell が持つ。
STYLE = """
body.techo{font-family:"Noto Serif CJK JP","Noto Serif JP","Hiragino Mincho ProN","Yu Mincho",serif;font-size:18px}
.techo main{max-width:640px;margin:0 auto;padding:20px max(16px,env(safe-area-inset-left,0px)) 64px;display:grid;gap:22px}
.techo h1{font-family:"Noto Serif CJK JP","Hiragino Mincho ProN",serif;font-weight:400;font-size:26px;letter-spacing:.3em;margin:0}
.techo .top{display:flex;align-items:center;gap:14px}.techo .top img{width:56px;height:84px;object-fit:cover;border:1px solid var(--frame)}
.techo .top a{margin-left:auto;font-size:14px;color:var(--accent)}
.techo .row{display:flex;gap:12px;flex-wrap:wrap}
.techo .manabi .loop-fig{margin:0 auto}
.techo .panel{border:1px solid var(--frame);border-radius:18px;padding:18px;display:grid;gap:14px;background:var(--paper)}
.techo .mark{display:flex;align-items:center;gap:12px;font-family:"Noto Serif CJK JP",serif;font-size:22px;letter-spacing:.15em;margin:0}
.techo .mark svg{width:40px;height:40px;stroke:var(--accent);fill:none;stroke-width:3;stroke-linecap:round;stroke-linejoin:round}
.techo input[type=text],.techo input[type=number]{font:inherit;font-size:22px;border:2px solid var(--frame);border-radius:12px;padding:14px 16px;width:100%;box-sizing:border-box;background:var(--field);color:var(--fg)}
.techo .go{font:inherit;font-size:20px;letter-spacing:.05em;background:var(--accent);color:var(--onaccent);border:0;padding:16px 28px;border-radius:12px;cursor:pointer;margin:0}
.techo a.go{display:inline-block;text-decoration:none;min-height:64px;box-sizing:border-box;letter-spacing:.3em}
.techo .meta{font-size:12px;color:var(--mute)}
.techo .item{border-top:1px solid var(--rule);padding-top:10px;display:grid;gap:6px}
.techo .item img,.techo .item video{height:110px;max-width:100%;border:1px solid var(--frame);border-radius:8px}
.techo .sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
.techo :focus-visible{outline:3px solid var(--accent);outline-offset:2px}
"""

def feedback(sid, r, photos=True, up_key=None, can_tell=False, filled=None, note=""):
    """手帖で受けるフィードバック（本人「フィードバックも手帖」、11-04）。順は J-013 のまま: 紙の返事（試した後の紙）→ 人の説明 → 次の版。
    Claude の解釈は、鍵がある時に作り手の道具で作る段で、ここでは出さない（人の説明が先）。
    photos=False は合言葉なしで開いた場。手帖の札は人ごとに分かれていないので、玩具の頁と同じく説明の文も次の版の欄も出さない（J-028、#336）。
    can_tell は、この画面がこの記録を残した時に真。説明の欄はその画面にだけ出す（受け口も断る。records.mine）。
    filled は通らなかった欄の (名前, 書いた中身)（"explain" か "next"）。書いた字を欄に戻し、次の版の欄は開いた形にする（#121 と同じ線。つくるの頁から
    記録の札を外した 11-08 から、説明と次の版の 422 はこの頁で返す）。note は次の版の欄の頭に出す理由の文（錨 next-記録の番号 のすぐ後）"""
    from web.toy import refill

    filled = filled or (None, {})
    from omochae import loop

    told = loop.explanation(r["id"])
    if told and not photos:
        body = ('<p class="meta">説明を残しました。</p>' if told.get("text") else "") + ai_part(r, up_key, photos=False)
    elif told:
        from web.play_server import next_form

        # 取り下げた説明は字が空になるので、空の欄を並べない。
        said = (f'<p>{esc(told["text"])}</p>' if told.get("text") else "") + (f'<p class="meta">次の思いつき: {esc(told["next_idea"])}</p>' if told.get("next_idea") else "")
        nxt = next_form(r).replace('</form>', '<input type="hidden" name="back" value="techo"></form>')
        if filled[0] == "next" and nxt:
            nxt = refill(nxt, filled[1]).replace("<details>", "<details open>", 1)
        # 次の版の欄に錨（next-記録の番号）を付ける: 送り先の #next-… と、通らなかった時の理由の文の置き場（前の玩具の頁の記録の札と同じ形）
        nxt = f'<div id="next-{esc(r["id"])}">{note}{nxt}</div>' if nxt else ""
        body = said + ai_part(r, up_key) + nxt
    elif not can_tell:
        body = ""
    else:
        # 欄の name を type のすぐ後に置く: 通らなかった時に字を戻す toy.refill は <input type="text" name=… の形で欄を探すため（422 をこの頁で返す 11-08 から）
        body = refill(f'<form method="post" action="/record/{esc(r["id"])}/explain#{esc(r["id"])}"><input type="hidden" name="back" value="techo">'
                '<label class="sr" for="t-' + esc(r["id"]) + '">何が起きたと思う</label><input type="text" name="text" id="t-' + esc(r["id"]) + '" placeholder="何が起きたと思う（わからない、でも）" required>'
                '<input type="text" name="next_idea" placeholder="次に試したい事" required><input type="text" name="by" placeholder="書いた人" autocomplete="off">'
                '<p><button class="go">残す</button></p></form>', filled[1] if filled[0] == "explain" else {})
    # 試した後の紙は刷らなくなった（本人の決まり 11-06・6 点の 1）ので、札に紙への道を出さない。紙の返事は、作った紙の玩具そのもの
    return body


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
        out += f'<div class="item"><p class="meta">Claude の読み（案）</p><ul>{lines}</ul></div>' if lines else ""  # 取り下げで中身が消えた読みは、見出しも出さない
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
.gallery .go{display:inline-block;background:var(--accent);color:var(--onaccent);border:0;padding:12px 22px;letter-spacing:.05em}
.gallery .day{font-size:17px;letter-spacing:.1em;margin:4px 0 0}
.gallery .sakurei-row,.gallery .workshop-row{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:12px}
.gallery .sakurei-row figure,.gallery .workshop-row figure{margin:0;display:grid;gap:6px;align-content:start}
.gallery .sakurei-row img,.gallery .workshop-row img{width:100%;height:auto;display:block;border:1px solid var(--frame)}
.gallery .sakurei-row figcaption,.gallery .workshop-row figcaption{font-size:14px}
.gallery .tiles figure:has(details[open]){grid-column:1/-1}
.gallery .workshop-top{margin:0}
.gallery .workshop-top img{width:100%;height:auto;display:block;border:1px solid var(--frame)}
.gallery .voices-fold summary{cursor:pointer;color:var(--accent);font-size:14px}
.gallery .voices-fold .item{display:grid;gap:4px;border-top:1px solid var(--frame);padding-top:8px;margin-top:8px}
.gallery .voices-fold p{margin:0}
.gallery .sakurei-row .ban{white-space:nowrap;margin-left:.6em}
.gallery .sakurei-faces{margin:0;display:grid;gap:6px}.gallery .sakurei-faces>div{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:8px}
.gallery .sakurei-faces img,.gallery .sakurei-kufu img{width:100%;height:auto;display:block;border:1px solid var(--frame)}
.gallery .sakurei-report{margin:0;padding-left:1.2em;display:grid;gap:4px}.gallery .sakurei-report .meta{display:block}
.gallery .sakurei-kufu figure{margin:0;display:grid;gap:6px;max-width:360px}
"""


# 記録の札の畳みの見出し（前からある字・のこすの頁の言い方）。中は、玩具の頁の記録の札にだけあった型紙の版と 4 つの欄
# （本人の言葉 11-08 477「復元の記録などはすべてもちよるに統合する。」・統括の決め: 玩具の頁から記録の札を外すとサイトのどこにも出なくなるので、ここへ）
DETAILS_HEAD = "のこした記録"


def record_details(data, r, say=True):
    """記録の札の畳み「のこした記録」の中身: 型紙の版の札と、最初に動いた所・引っかかった所・変えると違いが出そうな所・思いついた事。
    字と並びは玩具の頁の記録の札（toy.records_list）と同じ。say=False（公開の場で人が確かめていない記録）は 4 つの欄の字を出さず、版の札だけ。
    ひとこと（玩具の頁の「メモ」）は、もちよる（みんなが見る所）に出さない（11-05 の別の目の決まり・統括の答え 11-08 の C）。
    代わりに、手帖の記録の頁の自分の記録の札（records_page・その人の画面）に出す。Returns (畳みの html, 欄の字があるか)。"""
    ans = r.get("answers") or {}
    written = [("最初に動いた所", ans.get("first_moved")), ("引っかかった所", ans.get("stuck")), ("変えると違いが出そうな所", ans.get("what_if")),
               ("思いついた事", "、".join(str(x) for x in r.get("ideas") or []))] if say else []
    lines = "".join(f"<p>{label}: {esc(text)}</p>" for label, text in written if text)
    ban = hypotheses.label_of(r.get("sheet_set") or hypotheses.current_set(data), r.get("sheet_version", 1))
    return f'<details class="record-more"><summary>{esc(DETAILS_HEAD)}</summary><p class="meta">{esc(ban)}</p>{lines}</details>', bool(lines)


def made_item(sid, data, r, photos=True, public=False):
    """作った物の 1 件。ギャラリーの札。写真か言葉（感想・工夫）の無い記録は、見せる物が無いので空を返す。
    public=True は合言葉なしで開いた場。人が「物だけ」と確かめた写真と動画は出す（本人の決定 11-06「公開の場で上げた写真は、公開の場の
    ギャラリーにも出します」）。人の書いた文（感想と工夫の行）は、人が確かめた字だけを出す（窓口の決め A・11-08。前は出さなかった:
    文の中の名前は機械で落とせず、/loop を閉じたのと同じ理由・J-028。確かめが人の目になる）。記録の番号は前と同じく出さない。
    photos=False は写真も文も出さない前の開いた場の形（今は呼ぶ所が無い）。
    畳み「のこした記録」（record_details）に、型紙の版と 4 つの欄（最初に動いた所…思いついた事）を出す。前は玩具の頁の記録の札にだけあった欄で、
    本人の言葉 11-08 477 でもちよるへ移した。公開の場は感想と同じく、人が確かめた字だけ（words_review が欄の字も確かめる）。
    ひとこと（note）はギャラリーに出さない（前からの決まりのまま。自分の記録は手帖の記録の頁で見える）。
    動きの札（result）を残しても評価はしない。並びと同じく上下を付けない（J-025）。"""
    if not photos:
        return ""
    # 物だけと人が確かめた写真と動画だけを出す。ほかは字だけになる（本人の決定 11-05、#314）。
    # 写真は小さい写し（/small）を出し、押すと元の写真を開く（玩具の頁の記録の札と同じ。元の写真は 1 枚 3.7MB ほどで、並ぶと重い・#521）
    files = media_review.public(r["id"], media_of(r["id"]))
    pics = "".join((f'<video src="/record/{esc(r["id"])}/media/{esc(f)}" controls muted playsinline preload="metadata"></video>' if f.endswith(("mp4", "mov"))
                    else f'<a href="/record/{esc(r["id"])}/media/{esc(f)}"><img src="/record/{esc(r["id"])}/media/{esc(f)}/small" alt="作った物の写真" loading="lazy" decoding="async"></a>') for f in files)
    # 人の書いた文（感想と工夫の行）は、公開の場では人が確かめた字だけを出す（窓口の決め A・11-08。omochae.words_review）。
    # 確かめていない・確かめた後に字が替わった・連絡先の床に当たる物は、前と同じく出さない。合言葉付きの場は今までどおり出す
    say = not public or words_review.checked(r["id"])
    words = f'<p>{esc(r["impression"])}</p>' if r.get("impression") and say else ""
    words += "".join(f'<p class="meta">工夫: {esc(f.get("part", ""))} / {esc(f.get("change", ""))} / {esc(f.get("outcome", ""))}</p>' for f in r.get("fixes", []) if isinstance(f, dict) and say)
    more, has_more = record_details(data, r, say)
    # 欄だけの記録（写真も感想も工夫も無い）も札を出す（玩具の頁から記録の札を外しても、欄の字が消えないように）
    if not pics and not words and not has_more:
        return ""
    h = next((x for x in data["hypotheses"] if x["id"] == r["hypothesis_id"]), None)
    # 玩具の名前から、もちよるの中のその玩具の札（錨 toy-<印>・gallery_page が今の札に 1 つ付ける）へ行く。前は玩具の頁の同じ記録（#R-…）へ
    # 行ったが（本人の指摘 11-05: 制作した記録と玩具の頁をつなぐ）、本人の言葉 11-08 477「復元の記録などはすべてもちよるに統合する。」で
    # 玩具の頁から記録の札が無くなるので、向け直した（統括の決め 11-08）。この札が出る時は、その玩具の錨も頁にある（無ければこの札が錨を持つ）。
    # 錨は玩具の印で、記録の番号を道に入れない（開いた場で番号を出さない線・別の目の確かめで見つかった）
    to = f"#toy-{esc(sid)}"
    return (f'<div class="item"><p class="meta"><a href="{to}">{esc(data["toy"])}</a>　{esc(hypotheses.SHOWN + "の紙" if h else "自分の仮説の紙")}　{esc(records.result_word(r))}{"" if public else "　" + esc(wording.record_no(r["id"]))}</p>'
            + (f'<div class="row">{pics}</div>' if pics else "") + f'{words}{more}</div>')


def own_item(sid, data, r):
    """今残した 1 つの札（持ち寄る駅の頭。窓口の決定 11-06 夜・案 A）。記録を残した画面にだけ出す。
    ほかの札と違い、写真か言葉が無い記録も出す（今残した物が並んだ事を見せるため）。写真と動画は、ほかの札と同じく人が確かめた物だけ
    （ギャラリーは確認の後だけ、#314。確認の前の物は、上げた本人が手帖の記録の頁で見る）。
    記録の頁（説明と AI の札）へは記録の番号から、玩具の頁の同じ記録へは玩具の名前から行く（ほかの札と同じ。地図の 4。新しい字は足さない）。"""
    files = media_review.public(r["id"], media_of(r["id"]))
    pics = "".join((f'<video src="/record/{esc(r["id"])}/media/{esc(f)}" controls muted playsinline preload="metadata"></video>' if f.endswith(("mp4", "mov"))
                    else f'<a href="/record/{esc(r["id"])}/media/{esc(f)}"><img src="/record/{esc(r["id"])}/media/{esc(f)}/small" alt="作った物の写真" loading="lazy" decoding="async"></a>') for f in files)
    words = f'<p>{esc(r["impression"])}</p>' if r.get("impression") else ""
    # ほかの札と同じ畳み「のこした記録」（型紙の版と 4 つの欄）。今残した札は記録を残した画面にだけ出る（合言葉付きの場だけ）ので、欄の字はそのまま出す。
    # 付けないと、残した人の画面では その記録が 他の人が作った物 の並びに出ず（ここに出る）、4 つの欄がどこにも出ない（修正の担当 d の気づき 11-08）
    more, _ = record_details(data, r)
    h = next((x for x in data["hypotheses"] if x["id"] == r["hypothesis_id"]), None)
    return (f'<div class="item mine" id="own"><p class="meta"><a href="/toy/{esc(sid)}/techo/kiroku#mine">{esc(wording.record_no(r["id"]))}</a>　'
            # 玩具の名前は、手帖の記録の頁の自分の記録へ（記録の番号の道と同じ行き先）。前の玩具の頁の同じ記録（#R-…）は、本人の言葉 11-08 477 で
            # 玩具の頁から記録の札が無くなるので向け直した（統括の決め 11-08・修正の担当 d と合わせた）
            f'<a href="/toy/{esc(sid)}/techo/kiroku#mine">{esc(data["toy"])}</a>　'
            f'{esc(hypotheses.SHOWN + "の紙" if h else "自分の仮説の紙")}　{esc(records.result_word(r))}</p>'
            + (f'<div class="row">{pics}</div>' if pics else "") + f'{words}{more}</div>')


# ワークショップで作られた物（作例）の節の字（本人の言葉 11-07「サイトにワークショップで作られたおもちゃを掲載したい」。字は 11-07 に決まった案から）。
# 1 行は決めた字から「日の順に並べます。」だけを外した（本人の言葉 11-07「全部一緒にしてしまったので日毎にはしない」で、札を玩具ごとにしたため）
SAKUREI_TITLE = "ワークショップで作られた物"
# 「上下はありません」は外した（本人のサイトの見直し 11-07 22:16「もちよる、の上下はありません、は要らない。」。もちよる の頁＝作った物の頁の字）
SAKUREI_LEAD = "11 月 4・5・6・7 日のワークショップで作られた物です。"
# 報告の顔の写真（web.sakurei.faces）の札。本人の言葉のまま（窓口を通して 11-07「札は本人の言葉『4 日間のワークショップで作ったおもちゃたち』のままで」）
SAKUREI_FACES = "4 日間のワークショップで作ったおもちゃたち"
# 参加者の工夫の事例（web.sakurei.cases("kufu")）。題も文も本人の言葉から取り、言い換えない（統括 11-07「字は本人の説明のまま（本人の言葉として引用）」）。
# この工夫が型紙の次の版に入ったとは書かない（記録に無い。UX の担当の設計の「言わない事」）
SAKUREI_KUFU = "参加者の型紙の改善例"
SAKUREI_KUFU_WORDS = "参加者の型紙の改善例その1。手前が型紙通り。しかし、奥の工作のように、からくりがあると推測した参加者が蓋の開閉でネズミが箱の中に仕舞われるようにした。"
# 報告の段の道の字（UX の担当の案・窓口の確かめ待ち）。回の一覧が main に無い間は段ごと出ないので、この字も出ない
SAKUREI_REPORT_GO = "ワークショップの様子と、うつしの輪"  # 11-08 呼び名を 1 本の輪の名にそろえた（前は「改善の輪」）


def toy_place(sid, public=False):
    """玩具の頁から、もちよる（/gallery）のその玩具の置き場への道（つくるの作り直しの枝 1 が玩具の頁の のこす の段に置く 1 行の道の行き先）。
    もちよるにその玩具の札（みんながつくったおもちゃ・作例・他の人が作った物のどれか）があれば /gallery#toy-<印>（錨は gallery_page が今の札に 1 つ付ける）、
    どれも無ければ None（道を置かない。行き止まりを作らない）。public は合言葉なしで開いた場（記録の札は人が確かめた字か写真がある時だけ出るので、同じ線で見る）。"""
    from . import workshop

    data = hypotheses.load(sid)
    if workshop.has_card(sid) or any(made_item(sid, data, r, True, public) for r in records.all_records(sid)):
        return f"/gallery#toy-{sid}"
    return None


def _ban(sheet_set):
    """作例の札の型紙の版（刷った組の番号。例 goraigo-v10 は 10）。組の分かる作例だけ。分からない時は空（推して書かない）。
    字は「型紙の版」と数だけ（型紙の版は組の番号で言いそろえる決め 11-07。玩具の頁の型紙の札の脇に出す #513 と同じ形）。"""
    m = re.fullmatch(r"[a-z_]+-v(\d+)", sheet_set or "")
    # 名との間は全角の空白の字でなく余白で空ける（空白だけの字の塊は、英語の頁の訳の表で引けない日本語として残るため）
    return f' <span class="ban">型紙の版 {int(m.group(1))}</span>' if m else ""


def _report():
    """ワークショップの報告の段（4 回の 1 行ずつと、審査用の頁への道）。字の元は審査用の頁の回の一覧（web.kaizen_ws.workshops()）1 か所で、
    同じ物を読む（UX の担当の設計「字の元を 1 つにする」）。その口が無い・読めない時は空（段を出さない。回の一覧は #518 の作り直しで main に入る）。"""
    try:
        from . import kaizen_ws

        rows = kaizen_ws.workshops()
    except (ImportError, AttributeError, OSError, ValueError, TypeError):
        return ""
    lines = "".join(f'<li>{esc(str(w.get("date", "")))}　{esc(str(w.get("did", "")))}'
                    + (f'<span class="meta">{esc(str(w["line"]))}</span>' if w.get("line") else "") + "</li>"
                    for w in rows if isinstance(w, dict) and w.get("date") and w.get("did"))
    if not lines:
        return ""
    return f'<ul class="sakurei-report">{lines}</ul><p class="meta"><a href="/kaizen#ws">{esc(SAKUREI_REPORT_GO)}</a></p>'


def sakurei_section(sids, photos=True):
    """ワークショップで作られた物（作例）の節。持ち寄る駅（/gallery）の頭、「他の人が作った物」の上に置く（地図の工程 5）。

    判断の芯:
    - 並び（UX の担当の設計 11-07・state の workshop-link）: 題と 1 行 → 報告の顔の写真（sakurei.faces）と札 → 報告の 4 回の段（回の一覧がある時だけ）
      → 参加者の型紙の改善例（sakurei.cases("kufu")・本人の言葉の引用）→ 玩具ごとの作例の札。
    - anchored は、みんながつくったおもちゃ の札（workshop.made）で錨 toy-<印> を持つ玩具。それ以外の 83 の玩具の最初の札が錨を持つ
      （玩具の頁の「この玩具の作った物を もちよる で見る」の道の行き先。本人の言葉 11-08 477。1 つの玩具に錨は頁に 1 つ）。
    - 札は玩具ごと（日ごとにしない。本人の言葉 11-07「全部一緒にしてしまったので日毎にはしない」。写真の撮影の日は作った日と限らない）。
      玩具の並びは頁の玩具の並び（sids の順）、同じ玩具の中は記録の順。83 の外の玩具（猫と鼠の箱など）は後ろに、棚卸しの名で、道を付けずに置く
      （窓口の決め 11-07 144403）。上下は付けない（J-025）。
    - 出すのは人が「物だけ」と確かめた写真だけ（examples・faces・cases が確かめた物だけを返す）。どれも無い時は節ごと出さない（写真が来る前の形）。
    - 札は 1 つの記録に 1 枚: 写真の小さい写し（/small。元の写真を並べて読まない）と玩具の名（玩具の頁へ行く。他の人が作った物の札と同じ）と、
      刷った組が分かる時だけ型紙の版（_ban）。作った人の名と感想は記録に持たない。記録の番号は字にしない。
    - 合言葉なしで開いた場も同じ物を出す（人が確かめた写真は開いた場のギャラリーにも出す、本人の決定 11-06）。
      photos=False（写真を出さない前の開いた場の形）は出さない。"""
    if not photos:
        return ""
    from . import sakurei  # sakurei は techo_site を読むので、ここで読む

    # 玩具ごとの作例の札は「みんながつくったおもちゃ」の節（workshop.made）へ移した（本人の言葉 11-08「…ワークショップで作られたものの方は写真と名前が
    # 一致しているので、こちらの組み合わせと表示を採用して、みんなが作ったおもちゃの方に置く。」。同じ物を 2 度出さない）。ここには顔の写真・報告の段・工夫が残る
    faces, kufu = sakurei.faces(), sakurei.cases("kufu")
    # 報告の段だけでは節を出さない（前と同じ: 確かめた写真が来る前の形）
    if not (faces or kufu):
        return ""
    report = _report()
    img = lambda url, alt="作った物の写真": f'<img src="{esc(url)}" alt="{esc(alt)}" loading="lazy" decoding="async">'  # noqa: E731
    head = (f'<figure class="sakurei-faces"><div>{"".join(img(u, SAKUREI_FACES) for u in faces)}</div>'
            f'<figcaption>{esc(SAKUREI_FACES)}</figcaption></figure>') if faces else ""
    case = (f'<div class="sakurei-kufu"><h3 class="day">{esc(SAKUREI_KUFU)}</h3><figure>{"".join(img(c["url"]) for c in kufu)}'
            f'<figcaption>「{esc(SAKUREI_KUFU_WORDS)}」</figcaption></figure></div>') if kufu else ""
    return (f'<section class="panel" id="sakurei"><h2 class="mark">{esc(SAKUREI_TITLE)}</h2>'
            f'<p class="meta">{esc(SAKUREI_LEAD)}</p>{head}{report}{case}</section>')


# 合言葉なしの場で上げた直後の返事に続ける 1 行（窓口の決定 11-06 夜・案 A。字はその決定の字のまま）。上げた物は、確かめる前は上げた画面にだけ出て
# ギャラリーには出ないので、並ばない理由を上げた時に言う。合言葉付きの場も同じ線だが、決定は合言葉なしの場の分なので、そこだけに出す
PUBLIC_UPLOADED = "写真は、人が確かめてから、みんなの所に出ます。"
UPLOADED = "上げました"  # 手帖の script（techo_step）が上げた後に渡す返事の字
# のこした後の「この画面をとじる」（のこすの流れの設計の別の目の気づき 9・統括の決め 11-08。設計は grove の state/screen-close-20261108.md）。
# 1 台を順に使う場では、前の人の写真の鍵（確かめる前の写真を 2 時間見せる）と記録の鍵（今残した 1 つの札と字を足す口）が、次の人が記録を
# 残すまでその画面に残る。のこした直後（返事のある時）にだけ釦を出し、POST /close で 2 つの鍵を消す。字は新しい字で、本人の確かめ待ち
CLOSE = "この画面をとじる"
CLOSED = "とじました。次の人が使えます。"
# 公開の場だけの断り（とじると、その画面からは取り下げられない）は置かない（本人 11-08「公開デモだけのものはいらない。なにかあれば僕が対応するので。」）。
# 公開の場の取り下げは写真の鍵で見分けるので、とじた後に取り下げたい人は、本人が受ける


def close_form():
    """「この画面をとじる」の素のフォーム（台本なしでも動く）。道しるべの釦（.go）にしない: 帯の駅の道しるべは 1 つの決まり（test_ux_stage0）"""
    return f'<form method="post" action="/close" class="close-screen"><button type="submit">{esc(CLOSE)}</button></form>'


# ギャラリーの頭の説明の文。頁と、頁の description（skin.meta_head）が同じ字を引く（description に新しい字を作らないため・11-08）
GALLERY_LEAD = "記録の順に並べます。型紙は正解ではなく AI が考えた仮説で、作った人の工夫も一緒に残ります。紙で動いても、昔の作り方の証明にはなりません。"

def gallery_page(sids, photos=True, public=False, msg="", rec_key=None):
    """他の人が作った物のギャラリー（本人の決定 11-05「他の人の作ったものギャラリーは作る」。予想のギャラリーではない）。
    前は「職人の言葉」と「寄せられた声」の枠もここにあったが、序の頁へ移した（voices_sections。本人のサイト体験レビュー 11-07 の言葉 6）。
    作った物は手元の記録から読む（git の外の物なので、手元のサーバでだけ出す）。並びは記録の順で、上下を付けない（J-025）。
    """
    from . import workshop

    # 玩具ごとの錨 toy-<印>（本人の言葉 11-08 477「復元の記録などはすべてもちよるに統合する。」・玩具の頁の 1 行の道の行き先）は、今の札に 1 つだけ付ける:
    # みんながつくったおもちゃ のその玩具の最初の札（作例の札・事例の札・名と感想だけの札）→ 無ければ 他の人が作った物 のその玩具の最初の札。
    # 作例の節の玩具ごとの札は、みんながつくったおもちゃ へ移した（本人の言葉 11-08）ので、作例の節は錨を持たない。
    # 錨の名は玩具の印で、記録の番号は入れない（開いた場で記録の番号を画面にも道にも出さない線・J-028）
    with_sak = {sid for sid in sids if workshop.has_card(sid, photos)}
    cards, own = "", ""
    for sid in sids:
        data = hypotheses.load(sid)
        for r in records.all_records(sid):
            # 今残した 1 つ（記録を残した画面の鍵が合う記録）は頭に出し、並びの中には重ねて出さない。合言葉なしの場（public・photos=False）は鍵を見ない。
            # 札に記録の番号と感想の字が出るので（J-028）。呼ぶ側（play_server）も合言葉なしの場では鍵を渡さず、二重に閉じる
            if photos and not public and rec_key and not own and records.mine(r["id"], rec_key):
                own = own_item(sid, data, r)
                continue
            item = made_item(sid, data, r, photos, public)
            if item and sid not in with_sak:
                with_sak.add(sid)
                item = item.replace('<div class="item">', f'<div class="item" id="toy-{esc(sid)}">', 1)
            cards += item
    sak = sakurei_section(sids, photos)
    # ワークショップの試行の写真（web.workshop。本人の見直し 11-07 夜の ⑦）。他の人が作った物なので、この節の記録の札の前に置く。
    # repo の公開の決めが済んだ写真なので、合言葉なしの場（photos=False）でも出す（本人の直の指示）
    # ワークショップの様子（作っている途中の写真）と、できたおもちゃの敷き詰め（押すと感想）（本人の言葉 11-08「もちよる、ワークショップの様子、として
    # 作っている様子をあげるのと、できたおもちゃはギャラリーの形で並べる。感想も見れるように」）。前は「他の人が作った物」の中に、玩具ごとの写真の札
    # （workshop.gallery）を置いていたが、できたおもちゃの節が同じ写真を玩具ごとに出すので、2 回出さないよう外した。
    # repo の公開の決めが済んだ写真なので、合言葉なしの場（photos=False）でも出す（本人の直の指示・前と同じ）
    ws = workshop.made(sids, photos) + workshop.scene()
    narabe = workshop.top()
    after = f'<p class="meta">{esc(PUBLIC_UPLOADED)}</p>' if public and msg == UPLOADED else ""
    # とじた後の返事（CLOSED）には釦を出さない（押した後に同じ釦がまた出ると、とじていないように見えるため）
    shut = close_form() if msg and msg != CLOSED else ""
    note = f'<div role="status"><p id="msg">{esc(msg)}</p>{after}</div>{shut}' if msg else ""
    # 今残した 1 つだけがある時と、ワークショップで作られた物だけがある時は「まだ…ありません」を出さない（すぐ上に並んだ札と食い違うため）。
    # 開いた場で札が無い時は、断りの字を出さない。前の「公開のデモでは、人が書いた文と写真は出しません。」は、確かめた写真を出す形にしたので
    # 事実と違う。「記録を残すと、ここに並びます」も、開いた場では字の記録が並ばないので合わない。新しい字は本人の確かめが要るので、足さない
    if not cards and not own and not sak and not ws:
        cards = ('<p class="meta">公開のデモでは、人が書いた文と写真は出しません。</p>' if not photos else
                 "" if public else '<p class="meta">まだ作った物の記録はありません。玩具の頁か手帖で記録を残すと、ここに並びます。</p>')
    # 上げた物の見本（作り物）は外した（本人の言葉 11-08「見本の記録をワークショップのデータで作成して欲しい。」。ここには作例とワークショップの写真が本物として出る）

    # .gallery で包むのは、手帖の幅（640px）より広く並べるため（GALLERY_STYLE の main:has(.gallery)）。
    # 次の型紙へ（段 1、本人の決定 11-06「「次の型紙へ」の口は「もう 1 つ つくる」の 1 つだけ。次の玩具は勧めない」）。持ち寄る駅の頭に 1 つ。行き先は えらぶ（/toys）
    # 頭の「入口へ」は外した（窓口の決め 11-07）。入口へ直した「もう 1 つ つくる」と同じ所へ行く対になったため（本人のサイト体験レビュー 11-07 の 3）
    return ('<div class="gallery"><div class="top"><h1>作った物</h1></div>'
            # 選ぶ所は入口（えらぶ）。/toys は入口へ送るので、直に入口へ向ける（本人のサイト体験レビュー 11-07 の 3）
            '<p class="road"><a class="go" href="/">もう 1 つ つくる</a></p>'
            # 頭のおもちゃが並べてある写真 1 枚 → みんながつくったおもちゃ → つくっている様子（本人の言葉 11-08「冒頭におもちゃが並べてある写真一枚。…」）
            f'{narabe}{ws}'
            f'{sak}'
            # 寄せられた声と職人の言葉の節は、序の頁（よむ）へ移した（voices_sections。本人のサイト体験レビュー 11-07 の言葉 6、直しの設計の D）。
            # この頁は作った記録の並び（のこす の続き）だけになったので、節へ飛ぶ口（jump）は外した（1 つの節へ飛ぶ口は要らない）。題も「と職人の言葉」を外した
            f'<section class="panel" id="ageta"><h2 class="mark">他の人が作った物</h2><p class="meta">{esc(GALLERY_LEAD)}</p>'
            f'{note}{own}{cards}</section>'
            # 職人の言葉の節は、もちよるの頁の足（本人の言葉 11-08「職人の言葉、はもちよるに移動」。前は序の頁の足）
            f'{shokunin_section()}</div>')


VOICES_STYLE = """
.voices{display:grid;gap:22px}
.voices .panel{border:1px solid var(--frame);border-radius:0;padding:18px;display:grid;gap:14px;background:var(--paper)}
.voices .mark{font-size:22px;letter-spacing:.15em;margin:0}
.voices p{margin:0}
.voices .samples{display:grid;gap:10px;margin:0}
.voices .go{display:inline-block;background:var(--accent);color:var(--onaccent);border:0;padding:12px 22px;letter-spacing:.05em}
"""


def voices_sections():
    """寄せられた声の節（序の頁・よむ。about.page の足に置く）。本人のサイト体験レビュー（11-07）の言葉 6 で、ギャラリーから序の頁へ移した節。
    前は職人の言葉の節も並べていたが、本人の言葉（11-08）「職人の言葉、はもちよるに移動」で、職人の言葉の節は箱ごと もちよるの頁（gallery_page）へ
    移した（shokunin_section）。寄せられた声はここに残す。字と id（yose）は前のまま。見た目は VOICES_STYLE（序の頁の幅を変えないため、この節だけを包む）。"""
    from .demo_samples import voices_html

    return ('<div class="voices">'
            f'<section class="panel" id="yose"><h2 class="mark">寄せられた声</h2><p class="meta">{esc(wording.plain("持ち寄りの入口（フォーム）から寄せられた物を、同意・権利・確認・個人情報の床を通してから載せる所です。"))}</p>'
            f'{voices_html()}</section></div>')


def shokunin_section():
    """職人の言葉の節（持ち寄りの入口のフォームを含む）。本人の言葉（11-08）「職人の言葉、はもちよるに移動」で、序の頁から もちよるの頁へ箱ごと移した。
    箱・見出し・入口の字と id（shokunin）は前のまま（前の #shokunin への道は、もちよるの頁の同じ節に着く。英語とやさしい日本語の表の鍵も替えない）。
    箱の中身（札の並び）は声の担当の demo_samples.craft_html を呼ぶ（中身を型紙レビュー 10 本の言葉に替える直しと、ぶつからない分担・11-08）。
    見た目は GALLERY_STYLE の .gallery .panel・.mark・.go（ギャラリーの頁の中に置くので、VOICES_STYLE は要らない）。"""
    from .demo_samples import craft_html

    return (f'<section class="panel" id="shokunin"><h2 class="mark">職人の言葉</h2><p class="meta">{esc(wording.plain("紙や玩具を作る人の言葉を、確かめてから載せる所です（持ち寄りの場、J-021）。"))}</p>'
            f'<p><a class="go" href="{esc(FORM_URL)}" rel="noopener" target="_blank">持ち寄りの入口（フォーム）で寄せる</a></p>'
            '<p class="meta">フォームは Google のフォームです。写真や動画を添える時は Google に入る必要があり、添えた人の名前とメールがフォームの持ち主に記録されます。送られた物は確かめてから載せます。</p>'
            f'{craft_html()}</section>')


NEXT_ERABU = "次は、{n} のおもちゃから えらぶ"


def next_erabu():
    """のこすの後の道の字（数は入口の畳みの札と同じ数え方）。"""
    from .looks import erabu_counts
    from .play_server import sources
    return NEXT_ERABU.format(n=erabu_counts(list(sources()))[0])


def manabi_box():
    """学びの輪の文と図の節。のこす の頁（手帖の記録の頁）の頭の「のこすと型紙が直る事の枠」（naoru.box）の後に置く。
    本人のサイトの見直し（11-07 22:16）の ⑤「ここに輪の説明ある方がいいよね。」と、本人の決め「輪の説明は のこす の頁に置く」による。
    字は本人が採った輪の節の文（loop_figure.ADOPTED）をそのまま使う。11-08 から本人の答え「字 1 と絵 A。」の字（前は 11-07 夕「学びの輪の文は案 1 の字でよい」の字）。
    説明の頁（このサイトについて）の学びの輪の段と同じ形（文の後に同じ部品 loop_figure.svg() の図）にして、2 つの頁で字と絵が食い違わないようにする。
    のこす の頁に置くのは、文の「のこした記録が、次に作る時の入り口になります。」が、この頁でする事（作った記録をのこす）の意味を言っているため。
    のこした後は #mine に着くので、頭のこの節は上げる手の邪魔にならない。公開の場でも出す（人の言葉も記録の番号も入らない説明の字と図だけなので）"""
    from . import loop_figure  # 循環を避けて、ここで読む（naoru と同じ）

    # 11-08 の組み直し（本人の決め「この案で組み直す」）: 見出しは 1 本の輪の名、図は 1 本の輪。説明の頁の学びの輪の段と同じ形
    return (f'<section class="panel manabi" id="manabi"><h2>{esc(loop_figure.NAME)}</h2><p>{esc(loop_figure.ADOPTED)}</p>'
            f'{loop_figure.svg()}</section>')


def records_page(sid, uploads=True, msg="", up_key=None, rec_key=None, public=False, paper=None, at="", errors=(), err_at="", filled=None):
    """手帖の記録の頁。作る頁（techo_step）から外した札を置く: 上げた物・工夫・試した後の紙 → 説明 → AI の順（J-013）。
    作る頁の字に記録の番号と「の紙」を出さない決定（本人の決定 11-05、#87）のために分けた。のこした後と、説明を送った後にここへ着く。
    public=True は合言葉なしで開いた場（本人の決定 11-06 で写真と動画を受け、確かめた物はギャラリーにも出す形）。写真と動画は合言葉付きの場と
    同じ線（確かめる前は上げた本人の画面だけ・物だけの後は誰にでも・人や声は誰にも）。記録の番号・人の言葉・説明の文は前と同じく出さない。
    uploads=False は写真の口ごと閉じた形（前の開いた場の形。今は呼ぶ所が無いが、試験が使う）。
    paper は記入の節で記録を残す紙（techo_step.paper_of の (紙の印, 手順の数)）。None は刷った紙が無い時で、記入の節の代わりに紙を作る道を出す。
    並び（本人 11-08 400・402・405・設計 nokosu-flow 3 版）: 題 → 記入の節（その最後が「のこす」の釦）→ のこした記録から直った所（naoru.box）→
    学びの輪 → 手帖をひらく → 上げる の節（今までの記録）。前の道しるべの「のこす」（/gallery#ageta）は外した（記入の節の「のこす」と字が
    同じで行き先が違う物が並ぶため・承認の後は自分でもちよるへ飛ぶので要らない。別の目の気づき 6）
    errors・err_at・filled は、記録の札の説明と次の版が通らなかった時（422）: 理由の文を、その記録の札（錨 id=記録の番号）か次の版の欄（next-記録の番号）の頭に出し、
    書いた字を欄に戻す。前は玩具の頁の記録の札で返していたが、つくるの頁から記録の札を外した（本人の言葉 11-08「復元の記録などはすべてもちよるに統合する。」）"""
    closed = public or not uploads
    data = hypotheses.load(sid)
    from . import hanasu  # 循環を避けて、ここで読む
    from . import zukan  # 試した日の字（前のつくるの頁の記録の札と同じ部品）

    # 手帖から送った後の返事の文（#121）。着く #mine の頭に出す。通らなかった時の理由は、その記録の札の頭に出す（返事の文は頁に 1 つ・id を重ねない）
    from web.toy import reply_note

    note = "" if errors else reply_note((), msg)
    from api.words import spoken_own_ids
    from web.toy import own_papers as toy_own_papers

    spoken = spoken_own_ids(sid)
    alert = reply_note(errors, "") if errors else ""
    mine = ""
    for r in reversed(records.all_records(sid)):
        # 開いた場は受け口が画像を出さないので、壊れた絵にしない（J-028）。確認の前の物は、上げた本人の画面にだけ、受け取りを確かめられるように出す（#314）。
        files = media_review.shown_to(r["id"], media_of(r["id"]), up_key) if uploads else []
        pics = "".join((f'<video src="/record/{esc(r["id"])}/media/{esc(f)}" controls muted playsinline preload="metadata"></video>' if f.endswith(("mp4", "mov"))
                        else f'<a href="/record/{esc(r["id"])}/media/{esc(f)}"><img src="/record/{esc(r["id"])}/media/{esc(f)}/small" alt="上げた写真" loading="lazy" decoding="async"></a>') for f in files)
        h = next((x for x in data["hypotheses"] if x["id"] == r["hypothesis_id"]), None)
        who = f"{hypotheses.SHOWN}の紙" if h else "自分の仮説の紙"  # 仮説の印（A・C）は出さない（本人の答え 11-08「そろえる。」（つくるの外も印なし）・hypotheses.SHOWN）
        # 合言葉なしの場には進行者がいないので、上げた画面にだけ「取り下げる」を置く（窓口の決定 11-06 夜・案 A）。押すと、この記録の写真と動画が
        # 置き場ごと消え、ギャラリーからも消える。合言葉付きの場は、今までどおり進行者に記録の番号を伝える形（釦は出さない）
        drop = (f'<form method="post" action="/record/{esc(r["id"])}/media/withdraw"><button type="submit" class="btn quiet">取り下げる</button></form>'
                if public and media_review.uploaded_here(r["id"], media_of(r["id"]), up_key) else "")
        # ひとこと（玩具の頁の「メモ」）は、その画面が残した自分の記録の札にだけ出す（統括の答え 11-08 の C: もちよる＝みんなが見る所には出さず、
        # 玩具の頁から記録の札を外してもサイトから消えないように、その人の画面のここへ）。開いた場では人の言葉を出さない（前と同じ線）
        memo = wording.record_note(r.get("note")) if not closed and records.mine(r["id"], rec_key) else ""
        rid = r["id"]
        here = alert if err_at == rid else ""
        # 前に書かれた自分の仮説で刷った紙（型紙）への道は、前はつくるの頁の記録の札にだけあった（toy.own_papers）。つくるの頁から記録の札を外した
        # （本人の言葉 11-08）ので、ここ（その記録の札）に置く。合言葉なしの場と、話した案の紙（作った本人の画面からだけ開く）には出さない（前と同じ線）
        own = toy_own_papers(sid, r["hypothesis_id"], r.get("sheet_version", 1)) if (not closed and h is None and r["hypothesis_id"] not in spoken) else ""
        # 開いた角度（測った数）は、前はつくるの頁の記録の札の題（「…・40°」）にだけあった。記録の札を外したので、同じ形でここの 1 行に付ける（11-08）
        deg = f'・{r["opened_deg"]:g}°' if r.get("opened_deg") is not None else ""
        # 試した日と型紙の版は、前はつくるの頁の記録の札の頭（「11 月 4 日・版 7」）にだけあった。#657 で記録の札を外した後、写真も感想も無い記録は
        # どこにも出なくなった（統括の確かめ 11-08）ので、同じ部品と同じ字でここの頭の 1 行に付ける。人の言葉でないので合言葉なしの場でも出す
        when = f'　{zukan.record_date(r)}・{hypotheses.label_of(r.get("sheet_set") or hypotheses.current_set(data), r.get("sheet_version", 1))}'
        mine += (f'<div class="item" id="{esc(rid)}">{here}<p class="meta">{esc(wording.record_no(r["id"])) + "　" if not closed else ""}{esc(who)}　{esc(records.result_word(r))}{esc(deg)}{esc(when)}</p>{f"<div class=row>{pics}</div>" if pics else ""}{drop}'
                 + (f'<p>メモ: {esc(memo)}</p>' if memo else "") + own +
                 # 記録の「工夫した所（直した所）」と、上げた後に足す口（一周の 2 と 3、Issue #279）。開いた場では、人の言葉を出さない。
                 f'{hanasu.keep_box(sid, r, show_shared=not closed, can_add=records.mine(r["id"], rec_key))}'
                 f'{feedback(sid, r, photos=not closed, up_key=up_key, can_tell=records.mine(rid, rec_key), filled=filled if err_at in (rid, "next-" + rid) else None, note=alert if err_at == "next-" + rid else "")}</div>')
    # 話す口の見た目と動きは、頁に 1 回だけ置く。
    from . import naoru, nokosu  # 循環を避けて、ここで読む（hanasu と同じ）
    kinyu = nokosu.entry(sid, paper, records.results_for(sid)) if paper and uploads else nokosu.no_paper(sid)
    return (f'<div class="top"><h1>手帖</h1><a href="/toy/{esc(sid)}">{esc(data["toy"])}</a></div>'
            # 記入の節（いちばん上・その最後が「のこす」の釦。本人 11-08 400・405）
            # 作りながら見る頁の組み上がりから着いた時（at=kinyu）は、返事の字を記入の節のすぐ上に出す（上げる節の #mine には出さない）
            + (note if at == "kinyu" else "") + kinyu +
            # うつしの輪の文と図（本人の見直し 11-07 22:16 の ⑤・manabi_box）。記入の節のすぐ下（本人の言葉 11-08「のこすのうつしの輪は、
            # 記入欄の下にする。」決めの記録 530。前は直った例の集の後）
            manabi_box() +
            # のこすと型紙が直る事の枠と、のこした記録から直った所（本人 11-08 403）。うつしの輪の下に 1 回、手帖をひらく道の前
            naoru.box() +
            f'<p class="links"><a href="/toy/{esc(sid)}/techo">手帖をひらく（作りながら聞く・上げる）</a></p>'
            # 取り下げの説明文（#438 で本人が決めた字）。記録ごとに「足す」口が並ぶ頁なので、節の頭に 1 回だけ置く（main の手帖の上げる節と同じ）
            # 前はここに道しるべの「のこす」（/gallery#ageta）があった。記入の節の「のこす」の釦（承認の後にもちよるへ飛ぶ）に替えた
            f'<section class="panel" aria-label="上げる"><p class="meta">{esc(records.WITHDRAW_NOTICE)}</p><div id="mine">{"" if at == "kinyu" else note}'
            # 2 回目の入口（本人の決め 11-08「A＋Cでよい」の C）。のこした人（返事の文が出た時）にだけ、入口の畳みが開いた形 /#erabu への道を出す。
            # 印は持たない（道を見せるだけ）。数は入口の畳みの札と同じく、棚の分けから数える。道しるべの釦（class road）にはしない:
            # のこすの後の道しるべは 1 つの決まり（段 0・research/36・test_ux_stage0）なので、その下のふつうの道として置く
            + (f'<p class="links next-erabu"><a href="/#erabu">{esc(next_erabu())}</a></p>' if msg else '') +
            f'{mine}</div></section>') + hanasu.assets()
