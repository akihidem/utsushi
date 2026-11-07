"""審査用の頁（/kaizen）のワークショップの節（本人の言葉 11-07 昼「ワークショップは今日も合わせて 4 回実施した。
ワークショップの様子や回数、位置付け、それにより改善ループがまわる、はウリなので、デモと審査用サイトには写真をたくさん使って載せていきたい」）。

判断の芯（設計は grove の state/judge-page-20261107.md の末の節・案 A）:
- 回の一覧（日付・場・作った玩具・刷った型紙の組・その回から直った所・下の一周への道）は repo の中の字だけの JSON（data/kaizen-judge/workshops.json）。
  一覧は窓口が確かめた物だけを置く。無い間は節を出さない（回数を作り話にしない。表の workshops は 2 回分しか無い）。
- 写真は repo に入れない（repo の画像は NDL と東京学芸大学の PDM の物だけの決まり）。サーバの記録の置き場（OMOCHAE_DATA/kaizen-ws/）に、
  人が確かめた印つきの一覧（photos.json）と一緒に置く。審査する人が repo だけを clone した時は、写真の無い札（字と版だけ）で開く。
- 出す写真は、人が確かめた物で、写っている物の種類が SHOWS_OK に入る物だけ。今は「物だけ」（object）。
  前からの本人の決め（omochae.media_review の頭）「人や声が入る物は、字だけにする」があるため。審査用の頁で人の写る写真を出すかは窓口の決め待ちで、
  決まったら SHOWS_OK に people を足す（写真ごとの印は前から持たせておく）。
- 写真の道は /kaizen/photo/<回>/<名> の 1 本。一覧に無い名・確かめていない物・出さない種類・置き場の外を指す名は、どれも 404（中身を推させない）。
  小さい写しにして出す（撮影の情報は、写しを作り直す時に落ちる。向きだけ直す）。
- 新しい字は定数にまとめた（本人の確かめ・窓口へ）。
"""
import functools
import io
import json
import os
import pathlib
import re

from omochae.hypotheses import ROOT

from .skin import esc

LIST = ROOT / "data/kaizen-judge/workshops.json"
SHOWS_OK = ("object",)
IMAGE = (".jpg", ".jpeg", ".png")
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,80}")
MOSAIC = 12   # 頭の敷き詰めの枚数（幅 390 で 3 列 × 4 段）
SMALL_W = 800  # 写しの幅（札の写真は幅 390 で 1 枚 約 110px、頭の敷き詰めも同じ。2 倍の画面と、広い幅の 4 列で粗くならない幅）

# 新しい字（本人の確かめ・窓口へ）
TITLE = "ワークショップ {n} 回"
LEAD = "ワークショップは、改善の輪の入口です。作った人の記録と感想から型紙とエンジンが直り、次のワークショップで新しい版を刷ります。"
PRINTED = "刷った型紙"
FROM = "この回から直った所"
TO_LOOP = "この一周を見る"

STYLE = """
.ws-mosaic{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin:16px 0 0}
@media (min-width:768px){.ws-mosaic{grid-template-columns:repeat(4,1fr)}}
.ws-mosaic img,.ws-photos img{width:100%;aspect-ratio:1/1;object-fit:cover;display:block}
.ws-n{font-size:40px;letter-spacing:.08em}
.ws-row{list-style:none;margin:24px 0 0;padding:0;display:grid;gap:24px}
@media (min-width:768px){.ws-row{grid-template-columns:repeat(4,1fr)}}
.ws-card{border-top:2px solid var(--ink);padding:10px 0 0}
.ws-card h3{font-size:16px;margin:0}
.ws-photos{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:10px 0 0}
.ws-ver{letter-spacing:.06em}
"""


def _base():
    return pathlib.Path(os.environ.get("OMOCHAE_DATA", ROOT / "data")) / "kaizen-ws"


def _load(p):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def workshops():
    """窓口が確かめた回の一覧（日付の順）。無ければ空。"""
    d = _load(LIST) or {}
    return sorted(d.get("workshops", []), key=lambda w: (w.get("date", ""), w.get("n", 0)))


def photos(n):
    """その回の、出してよい写真の名（一覧の順）。人が確かめた印があり、種類が SHOWS_OK に入り、名が安全で、置き場に在る物だけ。"""
    d = _load(_base() / "photos.json") or {}
    out = []
    for p in d.get("photos", []):
        name = str(p.get("name", ""))
        if (p.get("ws") == n and p.get("checked_by") and p.get("shows") in SHOWS_OK
                and NAME.fullmatch(name) and name.lower().endswith(IMAGE) and (_base() / str(n) / name).is_file()):
            out.append(name)
    return out


@functools.lru_cache(maxsize=128)
def _small(path, mtime):
    from PIL import Image, ImageOps
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        im.thumbnail((SMALL_W, SMALL_W * 2))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=80, optimize=True)  # 作り直すので撮影の情報（位置など）は入らない
    return buf.getvalue()


def photo_bytes(n, name):
    """/kaizen/photo/<回>/<名> の中身。出してよくない物と読めない写真は None（呼ぶ側が 404 にする）。"""
    if name not in photos(n):
        return None
    p = _base() / str(n) / name
    try:
        return _small(str(p), p.stat().st_mtime)
    except OSError:
        return None


def _img(n, name, alt):
    return f'<img src="/kaizen/photo/{int(n)}/{esc(name)}" alt="{esc(alt)}" loading="lazy">'


def section(sheet):
    """節の HTML。sheet は組の名を「型紙の版 vN」で言う関数（kaizen_judge._sheet と同じ言い方にそろえる）。一覧が無ければ空。"""
    ws = workshops()
    if not ws:
        return ""
    each = [(w, photos(w.get("n"))) for w in ws]
    mosaic = [(w["n"], name, w.get("name", "")) for w, names in each for name in names][:MOSAIC]
    cards = ""
    for w, names in each:
        printed = "・".join(f'{esc(toy)} {esc(sheet(s))}' for toy, s in w.get("printed", []))
        cards += (f'<li class="ws-card" id="ws-{int(w["n"])}"><p class="meta">{esc(w.get("date", ""))}</p><h3>{esc(w.get("name", ""))}</h3>'
                  + (f'<div class="ws-photos">{"".join(_img(w["n"], x, w.get("name", "")) for x in names[:6])}</div>' if names else "")
                  + (f'<p class="ws-ver">{esc(PRINTED)}: {printed}</p>' if printed else "")
                  + (f'<p>{esc(FROM)}: {esc(w["line"])}</p>' if w.get("line") else "")
                  + (f'<p><a href="#{esc(w["loop"])}">{esc(TO_LOOP)}</a></p>' if w.get("loop") else "")
                  + "</li>")
    return (f'<section class="sec ws" id="ws"><h2 class="ws-n">{esc(TITLE.format(n=len(ws)))}</h2><p class="lead">{esc(LEAD)}</p>'
            + (f'<div class="ws-mosaic">{"".join(_img(n, x, alt) for n, x, alt in mosaic)}</div>' if mosaic else "")
            + f'<ol class="ws-row">{cards}</ol></section>')
