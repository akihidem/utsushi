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
# 合言葉なしで開いた場の写真と動画の置き場の合計（本人の決定 11-06「公開のデモでも写真と動画を上げられるようにしてください」）。
# 誰でも上げられる場なので、機械の空き（11-06 に 102G）を埋めさせない。2GB は空きの 2% で、20MB の動画なら 100 本・写真なら数百枚。
# 記録を作る口は書き込みの数の上限が絞り、1 つの記録には MAX_PER_RECORD までなので、1 人で一気に埋める形にはなりにくい
PUBLIC_MEDIA_TOTAL = 2 * 1024 * 1024 * 1024
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


def media_bytes():
    """置き場の写真と動画の大きさの合計（確かめの控えの json は数えない）。公開の場の合計の上限を見る時に、受ける前に数える。"""
    root = records.folder() / "media"
    return sum(p.stat().st_size for p in root.glob("R-*/m*.*")) if root.exists() else 0


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
.techo a.go{display:inline-block;text-decoration:none;min-height:64px;box-sizing:border-box;letter-spacing:.3em}
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

    told = loop.explanation(r["id"])
    if told and not photos:
        body = ('<p class="meta">説明を残しました。</p>' if told.get("text") else "") + ai_part(r, up_key, photos=False)
    elif told:
        from web.play_server import next_form

        # 取り下げた説明は字が空になるので、空の欄を並べない。
        said = (f'<p>{esc(told["text"])}</p>' if told.get("text") else "") + (f'<p class="meta">次の思いつき: {esc(told["next_idea"])}</p>' if told.get("next_idea") else "")
        body = said + ai_part(r, up_key) + next_form(r).replace('</form>', '<input type="hidden" name="back" value="techo"></form>')
    elif not can_tell:
        body = ""
    else:
        body = (f'<form method="post" action="/record/{esc(r["id"])}/explain#{esc(r["id"])}"><input type="hidden" name="back" value="techo">'
                '<label class="sr" for="t-' + esc(r["id"]) + '">何が起きたと思う</label><input type="text" id="t-' + esc(r["id"]) + '" name="text" placeholder="何が起きたと思う（わからない、でも）" required>'
                '<input type="text" name="next_idea" placeholder="次に試したい事" required><input type="text" name="by" placeholder="書いた人" autocomplete="off">'
                '<p><button class="go">残す</button></p></form>')
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
.gallery .is-sample{border:1px dashed var(--frame);padding:10px}
.gallery .go{display:inline-block;background:var(--accent);color:var(--onaccent);border:0;padding:12px 22px;letter-spacing:.05em}
"""


def made_item(sid, data, r, photos=True, public=False):
    """作った物の 1 件。ギャラリーの札。写真か言葉（感想・工夫）の無い記録は、見せる物が無いので空を返す。
    public=True は合言葉なしで開いた場。人が「物だけ」と確かめた写真と動画は出す（本人の決定 11-06「公開の場で上げた写真は、公開の場の
    ギャラリーにも出します」）。人の書いた文と記録の番号は前と同じく出さない: 文の中の名前は機械で落とせず、/loop を閉じたのと同じ理由（J-028）。
    photos=False は写真も文も出さない前の開いた場の形（今は呼ぶ所が無い）。
    ひとこと（note）は学ぶ人の頁に出してこなかった欄なので、ギャラリーにも出さない。
    動きの札（result）を残しても評価はしない。並びと同じく上下を付けない（J-025）。"""
    if not photos:
        return ""
    # 物だけと人が確かめた写真と動画だけを出す。ほかは字だけになる（本人の決定 11-05、#314）。
    files = media_review.public(r["id"], media_of(r["id"]))
    pics = "".join((f'<video src="/record/{esc(r["id"])}/media/{esc(f)}" controls muted playsinline preload="metadata"></video>' if f.endswith(("mp4", "mov"))
                    else f'<img src="/record/{esc(r["id"])}/media/{esc(f)}" alt="作った物の写真" loading="lazy">') for f in files)
    words = f'<p>{esc(r["impression"])}</p>' if r.get("impression") and not public else ""
    words += "".join(f'<p class="meta">工夫: {esc(f.get("part", ""))} / {esc(f.get("change", ""))} / {esc(f.get("outcome", ""))}</p>' for f in r.get("fixes", []) if isinstance(f, dict) and not public)
    if not pics and not words:
        return ""
    h = next((x for x in data["hypotheses"] if x["id"] == r["hypothesis_id"]), None)
    # 玩具の名前から、その玩具の頁の同じ記録へ行ける（本人の指摘 11-05: 制作した記録と玩具の頁をつなぐ）。
    # 開いた場では記録の番号を画面に出さないので、道（#R-…）にも入れず、玩具の頁の頭へ行く（別の目の確かめで見つかった）
    to = f"/toy/{esc(sid)}" + ("" if public else f"#{esc(r['id'])}")
    return (f'<div class="item"><p class="meta"><a href="{to}">{esc(data["toy"])}</a>　{esc(hypotheses.letter(h) + " の紙" if h else "自分の仮説の紙")}　{esc(records.result_word(r))}{"" if public else "　" + esc(wording.record_no(r["id"]))}</p>'
            + (f'<div class="row">{pics}</div>' if pics else "") + f'{words}</div>')


def own_item(sid, data, r):
    """今残した 1 つの札（持ち寄る駅の頭。窓口の決定 11-06 夜・案 A）。記録を残した画面にだけ出す。
    ほかの札と違い、写真か言葉が無い記録も出す（今残した物が並んだ事を見せるため）。写真と動画は、ほかの札と同じく人が確かめた物だけ
    （ギャラリーは確認の後だけ、#314。確認の前の物は、上げた本人が手帖の記録の頁で見る）。
    記録の頁（説明と AI の札）へは記録の番号から、玩具の頁の同じ記録へは玩具の名前から行く（ほかの札と同じ。地図の 4。新しい字は足さない）。"""
    files = media_review.public(r["id"], media_of(r["id"]))
    pics = "".join((f'<video src="/record/{esc(r["id"])}/media/{esc(f)}" controls muted playsinline preload="metadata"></video>' if f.endswith(("mp4", "mov"))
                    else f'<img src="/record/{esc(r["id"])}/media/{esc(f)}" alt="作った物の写真" loading="lazy">') for f in files)
    words = f'<p>{esc(r["impression"])}</p>' if r.get("impression") else ""
    h = next((x for x in data["hypotheses"] if x["id"] == r["hypothesis_id"]), None)
    return (f'<div class="item mine" id="own"><p class="meta"><a href="/toy/{esc(sid)}/techo/kiroku#mine">{esc(wording.record_no(r["id"]))}</a>　'
            f'<a href="/toy/{esc(sid)}#{esc(r["id"])}">{esc(data["toy"])}</a>　'
            f'{esc(hypotheses.letter(h) + " の紙" if h else "自分の仮説の紙")}　{esc(records.result_word(r))}</p>'
            + (f'<div class="row">{pics}</div>' if pics else "") + f'{words}</div>')


# 合言葉なしの場で上げた直後の返事に続ける 1 行（窓口の決定 11-06 夜・案 A。字はその決定の字のまま）。上げた物は、確かめる前は上げた画面にだけ出て
# ギャラリーには出ないので、並ばない理由を上げた時に言う。合言葉付きの場も同じ線だが、決定は合言葉なしの場の分なので、そこだけに出す
PUBLIC_UPLOADED = "写真は、人が確かめてから、みんなの所に出ます。"
UPLOADED = "上げました"  # 手帖の script（techo_step）が上げた後に渡す返事の字


def gallery_page(sids, photos=True, public=False, msg="", rec_key=None):
    """他の人が作った物のギャラリー（本人の決定 11-05「他の人の作ったものギャラリーは作る」。予想のギャラリーではない）。
    前は「職人の言葉」と「寄せられた声」の枠もここにあったが、序の頁へ移した（voices_sections。本人のサイト体験レビュー 11-07 の言葉 6）。
    作った物は手元の記録から読む（git の外の物なので、手元のサーバでだけ出す）。並びは記録の順で、上下を付けない（J-025）。
    """
    cards, own = "", ""
    for sid in sids:
        data = hypotheses.load(sid)
        for r in records.all_records(sid):
            # 今残した 1 つ（記録を残した画面の鍵が合う記録）は頭に出し、並びの中には重ねて出さない。合言葉なしの場（public・photos=False）は鍵を見ない。
            # 札に記録の番号と感想の字が出るので（J-028）。呼ぶ側（play_server）も合言葉なしの場では鍵を渡さず、二重に閉じる
            if photos and not public and rec_key and not own and records.mine(r["id"], rec_key):
                own = own_item(sid, data, r)
                continue
            cards += made_item(sid, data, r, photos, public)
    real = bool(cards or own)
    after = f'<p class="meta">{esc(PUBLIC_UPLOADED)}</p>' if public and msg == UPLOADED else ""
    note = f'<div role="status"><p id="msg">{esc(msg)}</p>{after}</div>' if msg else ""  # 本物の作った物の札が 1 つでもあるか（見本を畳むかを決める）
    # 今残した 1 つだけがある時は「まだ…ありません」を出さない（並んだ札と食い違うため）。
    # 開いた場で札が無い時は、断りの字を出さない。前の「公開のデモでは、人が書いた文と写真は出しません。」は、確かめた写真を出す形にしたので
    # 事実と違う。「記録を残すと、ここに並びます」も、開いた場では字の記録が並ばないので合わない。新しい字は本人の確かめが要るので、足さない
    if not cards and not own:
        cards = ('<p class="meta">公開のデモでは、人が書いた文と写真は出しません。</p>' if not photos else
                 "" if public else '<p class="meta">まだ作った物の記録はありません。玩具の頁か手帖で記録を残すと、ここに並びます。</p>')
    # 見本（本人の指示、11-04）は本物の後ろに、札を付けて置く。本物が増えても見本と混ざらない。
    from .demo_samples import uploads_html
    # 本物の作った物が 1 つでもあれば、見本は「見本」の畳みに入れる（段 0。research/36「本物が 1 つでもあれば、見本は畳む」）。畳みの見出しは見本の札と同じ字
    sample = uploads_html()
    cards += f'<details class="samples-fold"><summary>見本</summary>{sample}</details>' if (real and sample) else sample

    # .gallery で包むのは、手帖の幅（640px）より広く並べるため（GALLERY_STYLE の main:has(.gallery)）。
    # 次の型紙へ（段 1、本人の決定 11-06「「次の型紙へ」の口は「もう 1 つ つくる」の 1 つだけ。次の玩具は勧めない」）。持ち寄る駅の頭に 1 つ。行き先は えらぶ（/toys）
    return ('<div class="gallery"><div class="top"><h1>作った物</h1><a href="/">入口へ</a></div>'
            '<p class="road"><a class="go" href="/toys">もう 1 つ つくる</a></p>'
            # 寄せられた声と職人の言葉の節は、序の頁（よむ）へ移した（voices_sections。本人のサイト体験レビュー 11-07 の言葉 6、直しの設計の D）。
            # この頁は作った記録の並び（のこす の続き）だけになったので、節へ飛ぶ口（jump）は外した（1 つの節へ飛ぶ口は要らない）。題も「と職人の言葉」を外した
            '<section class="panel" id="ageta"><h2 class="mark">他の人が作った物</h2><p class="meta">記録の順に並べます。上下はありません。型紙は正解ではなく AI が考えた仮説で、作った人の工夫も一緒に残ります。紙で動いても、昔の作り方の証明にはなりません。</p>'
            f'{note}{own}{cards}</section></div>')


VOICES_STYLE = """
.voices{display:grid;gap:22px}
.voices .panel{border:1px solid var(--frame);border-radius:0;padding:18px;display:grid;gap:14px;background:var(--paper)}
.voices .mark{font-size:22px;letter-spacing:.15em;margin:0}
.voices p{margin:0}
.voices .samples{display:grid;gap:10px;margin:0}
.voices .is-sample{border:1px dashed var(--frame);padding:10px}
.voices .go{display:inline-block;background:var(--accent);color:var(--onaccent);border:0;padding:12px 22px;letter-spacing:.05em}
"""


def voices_sections():
    """寄せられた声と職人の言葉の 2 つの節（持ち寄りの入口のフォームを含む）。序の頁（よむ。about.page）の足に置く。
    本人のサイト体験レビュー（11-07）の言葉 6「残すと持ち寄るが同じに聞こえて分かりにくい。残す＝作った記録を残す事、に寄せる。
    職人の言葉や、昔遊んだ人の寄せる話の入口は、作る側へ合体してもよい。」と、本人の答え「反映してください。…要点の通りで進めてください。」による
    （直しの設計の D。UX の担当の読み ②: のこす は作った記録を残す事に寄せ、職人の言葉と寄せる話の入口を作る側へ。帯の駅は替えない）。
    移し先を序の頁にしたのは、直しの設計の「玩具の頁の足の畳みか よむ」のうち、玩具の頁は別の直しの担当が持つため（統括の分担 11-07）。
    字は前のギャラリーの節のまま（id も yose・shokunin のまま。前のギャラリーの #yose と #shokunin への道は、序の頁で同じ節に着く）。
    見た目はギャラリーと同じ。ギャラリーの CSS は .gallery の下と頁の幅（main:has(.gallery)）を持つので、序の頁の幅を変えないよう、
    この 2 つの節だけを包む VOICES_STYLE を別に持つ。"""
    from .demo_samples import voice_html, voices_html

    voices = "".join(voice_html(k) for k in ("紙と折りの職人", "からくりの職人", "郷土玩具の作り手"))
    return ('<div class="voices">'
            f'<section class="panel" id="yose"><h2 class="mark">寄せられた声</h2><p class="meta">{esc(wording.plain("持ち寄りの入口（フォーム）から寄せられた物を、同意・権利・確認・個人情報の床を通してから載せる所です。"))}</p>'
            f'{voices_html()}</section>'
            f'<section class="panel" id="shokunin"><h2 class="mark">職人の言葉</h2><p class="meta">{esc(wording.plain("紙や玩具を作る人の言葉を、確かめてから載せる所です（持ち寄りの場、J-021）。"))}</p>'
            f'<p><a class="go" href="{esc(FORM_URL)}" rel="noopener" target="_blank">持ち寄りの入口（フォーム）で寄せる</a></p>'
            '<p class="meta">フォームは Google のフォームです。写真や動画を添える時は Google に入る必要があり、添えた人の名前とメールがフォームの持ち主に記録されます。送られた物は確かめてから載せます。</p>'
            f'{voices}</section></div>')


def records_page(sid, uploads=True, msg="", up_key=None, rec_key=None, public=False):
    """手帖の記録の頁。作る頁（techo_step）から外した札を置く: 上げた物・工夫・試した後の紙 → 説明 → AI の順（J-013）。
    作る頁の字に記録の番号と「の紙」を出さない決定（本人の決定 11-05、#87）のために分けた。のこした後と、説明を送った後にここへ着く。
    public=True は合言葉なしで開いた場（本人の決定 11-06 で写真と動画を受け、確かめた物はギャラリーにも出す形）。写真と動画は合言葉付きの場と
    同じ線（確かめる前は上げた本人の画面だけ・物だけの後は誰にでも・人や声は誰にも）。記録の番号・人の言葉・説明の文は前と同じく出さない。
    uploads=False は写真の口ごと閉じた形（前の開いた場の形。今は呼ぶ所が無いが、試験が使う）。"""
    closed = public or not uploads
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
        who = f"{hypotheses.letter(h)} の紙" if h else "自分の仮説の紙"
        # 合言葉なしの場には進行者がいないので、上げた画面にだけ「取り下げる」を置く（窓口の決定 11-06 夜・案 A）。押すと、この記録の写真と動画が
        # 置き場ごと消え、ギャラリーからも消える。合言葉付きの場は、今までどおり進行者に記録の番号を伝える形（釦は出さない）
        drop = (f'<form method="post" action="/record/{esc(r["id"])}/media/withdraw"><button type="submit" class="btn quiet">取り下げる</button></form>'
                if public and media_review.uploaded_here(r["id"], media_of(r["id"]), up_key) else "")
        mine += (f'<div class="item"><p class="meta">{esc(wording.record_no(r["id"])) + "　" if not closed else ""}{esc(who)}　{esc(records.result_word(r))}</p>{f"<div class=row>{pics}</div>" if pics else ""}{drop}'
                 # 記録の「工夫した所（直した所）」と、上げた後に足す口（一周の 2 と 3、Issue #279）。開いた場では、人の言葉を出さない。
                 f'{hanasu.keep_box(sid, r, show_shared=not closed, can_add=records.mine(r["id"], rec_key))}'
                 f'{feedback(sid, r, photos=not closed, up_key=up_key, can_tell=records.mine(r["id"], rec_key))}</div>')
    # 話す口の見た目と動きは、頁に 1 回だけ置く。
    return (f'<div class="top"><h1>手帖</h1><a href="/toy/{esc(sid)}">{esc(data["toy"])}</a></div>'
            f'<p class="links"><a href="/toy/{esc(sid)}/techo">手帖をひらく（作りながら聞く・上げる）</a></p>'
            # 取り下げの説明文（#438 で本人が決めた字）。記録ごとに「足す」口が並ぶ頁なので、節の頭に 1 回だけ置く（main の手帖の上げる節と同じ）
            # 残した後に次へ進む口（段 0、本人の決定 11-06「もちよる は、残した物がみんなの作った物に並ぶ所」。research/36）。
            # 「のこす」の後はこの頁の #mine に着くので、返事の文のすぐ下に 1 つだけ置く。行き先はギャラリーの「他の人が作った物」
            f'<section class="panel" aria-label="上げる"><p class="meta">{esc(records.WITHDRAW_NOTICE)}</p><div id="mine">{note}'
            '<p class="road"><a class="go" href="/gallery#ageta">もちよる</a></p>'
            f'{mine}</div></section>') + hanasu.assets()
