"""作ってみた実物を、原画の隣に見せる部品（本人のサイト体験レビュー 11-07 の 2「作ってみた実物（御来迎など）を見せる」。UX の割り方の B）。

判断の芯:
- 出すのは、人が「物だけ」と確かめた写真だけ（media_review.public。ギャラリーと玩具の頁と同じ線。#314・J-028）。その玩具の記録の中で一番新しい物を 1 枚。
  動画は出さない（最初の画面で重く、音の扱いも別。写真だけで足りる）。
- 写真が無い玩具には何も置かない（窓口の決め 125731・(b)）。前は組み立ての止まった形（kumitate.still）を代わりに置いていたが、
  組み立ての 3D がある玩具（御来迎と虎）では C3（#529）が頭の後へ上げた動く 3D と同じ物が 2 回出た（幅 390 で 467px と 1558px）。
  3D の無い玩具（81 種）には前から何も置かない（作っていない物を作ったように見せない）。
- 写真がいつ届いても作りは替えない: 写真の有無で切り替わる（写真は repo に入れない決まり。公開の場のサーバの記録の置き場に、人が確かめて入る）。
- 字は今ある字だけ: 写真の札は「作った物」（ギャラリーの「他の人が作った物」と同じ言い方）。
"""
import functools
import io

from omochae import media_review, records

from .skin import esc

PHOTO = "作った物"
IMAGE = (".jpg", ".jpeg", ".png")


SMALL_W = 480   # 写真の小さい写しの幅（px）。入口の札（幅 390 で 71px）と玩具の頁の頭（240px）を 2 倍の画面で見ても粗くならない


@functools.lru_cache(maxsize=64)
def _small(path, mtime):
    from PIL import Image, ImageOps
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")  # 上げた写真の向き（撮影の情報は上げる時に外してある。向きだけ直す）
        im.thumbnail((SMALL_W, SMALL_W * 2))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=78, optimize=True)
    return buf.getvalue()


def small_photo(path):
    """作った物の写真の小さい写し（JPEG のバイト）。読めない写真は None（壊れた写真で頁を止めない）。"""
    try:
        return _small(str(path), path.stat().st_mtime)
    except OSError:
        return None


def photo(sid):
    """その玩具の、人が物だけと確かめた写真のうち一番新しい物の小さい写しの道（/record/<記録>/media/<名前>/small）。無ければ None。"""
    from .techo_site import media_of

    # 作例（ワークショップで作られたおもちゃ・via=workshop の記録。#531）の写真も読む。入口の棚の札の角と玩具の頁の頭に、
    # 作例の人が確かめた写真が出るように（窓口の決め 163132「入口の棚の札のうち実物の写真がある玩具だけ…made.photo」）
    for r in reversed(records.all_records(sid, workshop=True)):
        files = [f for f in media_review.public(r["id"], media_of(r["id"])) if f.lower().endswith(IMAGE)]
        if files:
            return f"/record/{r['id']}/media/{files[-1]}/small"
    return None


def figure(sid, cls="made", photos=True):
    """原画の隣に置く 1 枚。人が確かめた写真があればその 1 枚、無ければ空（窓口の決め 125731・(b)）。
    photos=False は合言葉なしで開いた場の玩具の頁。そこでは記録の写真を出さない前の決まり（test_public_open: 人が確かめた写真は
    開いた場のギャラリーにだけ出し、玩具の頁と図鑑は出さないまま）を守り、何も置かない。"""
    url = photo(sid) if photos else None
    if url:
        return (f'<figure class="{cls}"><img src="{esc(url)}" alt="{esc(PHOTO)}の写真" loading="lazy" decoding="async">'
                f'<figcaption>{esc(PHOTO)}</figcaption></figure>')
    return ""
