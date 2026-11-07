"""審査用の頁（/kaizen）のワークショップの節（本人の言葉 11-07 昼「ワークショップは今日も合わせて 4 回実施した。
ワークショップの様子や回数、位置付け、それにより改善ループがまわる、はウリなので、デモと審査用サイトには写真をたくさん使って載せていきたい」）。

判断の芯（設計は grove の state/judge-page-20261107.md の末の節・案 A）:
- 回の一覧（日付・何をしたか・刷った型紙の組・その回から直った所・下の一周への道・写真の置き場）は repo の中の字だけの JSON（data/kaizen-judge/workshops.json）。
  窓口が確かめた物だけを置く。無い間は節を出さない（回数を作り話にしない）。
- 札の名は日付で言う（「何回目」と言わない）。前の記録は 11-06 を「ワークショップ 2 回目」と呼ぶが、本人の答え（11-07）で 4 回は 11-04・05・06・07 になり、数え方が食い違うため。
- 写真は、試行の記録にもう入っている写し（docs/process/trials/photos/<日付>/。撮影の情報を外した物）だけを使う。新しい写真を repo に入れない（統括の知らせ 11-07: 写真の元は repo へ入れない）。
  本人の答え（11-07）「いま渡している写真は使っていい。全部使っていい。4 と 6 の渡している写真を中心に使って」。
- 出す写真は、その置き場の確かめ表（review.md）の「本人の判断」の欄に「公開してよい」とある物だけ（今までの確かめの道。統括の知らせ 11-07: 公開の場へ出す物は人が確かめた物）。
  欄が空の物・外すとある物・表に無い物は出さない。動画は出さない（最初の画面で重く、音の扱いも別）。
- 写真の道は /kaizen/photo/<回>/<名> の 1 本。出さない物はどれも 404。置き場の外は、名の形とたどった先（symlink の先）の両方で見る（別の目の気づき 11-07）。
  小さい写しにして出す（作り直しで撮影の情報は入らない。向きだけ直す）。
- 新しい字は定数にまとめた（本人の確かめ・窓口へ）。
"""
import functools
import io
import json
import re

from omochae.hypotheses import ROOT

from .skin import esc

LIST = ROOT / "data/kaizen-judge/workshops.json"
PHOTOS = ROOT / "docs/process/trials/photos"
IMAGE = (".jpg", ".jpeg", ".png")
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,80}")
OK = "公開してよい"   # 確かめ表の「本人の判断」の欄の字
MOSAIC = 12   # 頭の敷き詰めの枚数（幅 390 で 3 列 × 4 段）。回をまたいで順に取る（4 日と 6 日の両方が頭に出る）
SHOWN = 9     # 札に開いて出す枚数。残りは畳む（11-06 は 34 枚あり、全部を開くと幅 390 で 1400px を越えるため）
SMALL_W = 480  # 写しの幅（札と敷き詰めの 1 枚は幅 390 で約 110px・広い幅の 4 列で約 230px。2 倍の画面でも粗くならない幅）

# 新しい字（本人の確かめ・窓口へ）
TITLE = "ワークショップ {n} 回"
LEAD = "ワークショップは、改善の輪の入口です。作った人の記録と感想から型紙とエンジンが直り、次のワークショップで新しい版を刷ります。"
PRINTED = "刷った型紙"
FROM = "この回から直った所"
TO_LOOP = "この一周を見る"
MORE = "ほかの写真（{n} 枚）"

STYLE = """
.ws-mosaic{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin:16px 0 0}
@media (min-width:768px){.ws-mosaic{grid-template-columns:repeat(4,1fr)}}
.ws-mosaic img,.ws-photos img{width:100%;aspect-ratio:1/1;object-fit:cover;display:block}
.ws-n{font-size:40px;letter-spacing:.08em}
.ws-row{list-style:none;margin:24px 0 0;padding:0;display:grid;gap:24px}
@media (min-width:768px){.ws-row{grid-template-columns:repeat(2,1fr)}}
.ws-card{border-top:2px solid var(--ink);padding:10px 0 0}
.ws-card h3{font-size:16px;margin:0}
.ws-photos{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:10px 0 0}
.ws-card details{margin:8px 0 0}
.ws-ver{letter-spacing:.06em}
"""


def _load(p):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def workshops():
    """窓口が確かめた回の一覧（回の番号の順＝行った順）。無ければ空。回の番号が整数でない行は外す（行 1 つの書き損じで頁ごと止めない。別の目の気づき 11-07）。
    日付は「11 月 4 日」の形の字なので、並べ替えには使わない（10 日を越えると字の順と日の順が食い違う）。"""
    d = _load(LIST) or {}
    rows = [w for w in d.get("workshops", []) if isinstance(w, dict) and isinstance(w.get("n"), int) and not isinstance(w.get("n"), bool)]
    return sorted(rows, key=lambda w: w["n"])


def _box(n):
    """その回の写真の置き場（試行の写真の置き場の中の 1 つの箱）。無い・外を指す時は None。"""
    w = next((w for w in workshops() if w["n"] == n), None)
    name = str((w or {}).get("photos", ""))
    if not NAME.fullmatch(name):
        return None
    root = PHOTOS.resolve()
    box = (PHOTOS / name).resolve()
    return box if box.parent == root and box.is_dir() else None


def _judged(box):
    """確かめ表（review.md）の行のうち、本人の判断の欄（行の最後の欄）が「公開してよい」の名。"""
    try:
        lines = (box / "review.md").read_text(encoding="utf-8").splitlines()
    except OSError:
        return set()
    out = set()
    for line in lines:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and NAME.fullmatch(cells[0]) and cells[-1].startswith(OK):
            out.add(cells[0])
    return out


def _inside(box, path):
    """たどった先が箱の中の、ふつうのファイルか。"""
    try:
        real = path.resolve(strict=True)
    except OSError:
        return False
    return real.parent == box and real.is_file()


def photos(n):
    """その回の、出してよい写真の名（名の順）。確かめ表で本人が公開してよいとした写真で、箱の中に在る物だけ。"""
    box = _box(n)
    if not box:
        return []
    return sorted(x for x in _judged(box) if x.lower().endswith(IMAGE) and _inside(box, box / x))


@functools.lru_cache(maxsize=128)
def _small(path, mtime):
    from PIL import Image, ImageOps
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        im.thumbnail((SMALL_W, SMALL_W * 2))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=80, optimize=True)  # 作り直すので撮影の情報は入らない
    return buf.getvalue()


def photo_bytes(n, name):
    """/kaizen/photo/<回>/<名> の中身。出してよくない物と読めない写真は None（呼ぶ側が 404 にする）。"""
    if name not in photos(n):
        return None
    p = _box(n) / name
    try:
        return _small(str(p), p.stat().st_mtime)
    except OSError:
        return None


def _img(n, name, alt):
    return f'<img src="/kaizen/photo/{int(n)}/{esc(name)}" alt="{esc(alt)}" loading="lazy">'


def _mosaic(each):
    """回をまたいで 1 枚ずつ順に取る（写真の多い回だけで頭が埋まらないように）。"""
    out, i = [], 0
    while len(out) < MOSAIC and any(i < len(names) for _, names in each):
        out += [(w["n"], names[i], w.get("date", "")) for w, names in each if i < len(names)]
        i += 1
    return out[:MOSAIC]


def section(sheet):
    """節の HTML。sheet は組の名を「型紙の版 vN」で言う関数（kaizen_judge._sheet と同じ言い方にそろえる）。一覧が無ければ空。"""
    ws = workshops()
    if not ws:
        return ""
    each = [(w, photos(w["n"])) for w in ws]
    cards = ""
    for w, names in each:
        alt = w.get("date", "")
        printed = "・".join(f'{esc(toy)} {esc(sheet(s))}' for toy, s in w.get("printed", []))
        shown = "".join(_img(w["n"], x, alt) for x in names[:SHOWN])
        more = "".join(_img(w["n"], x, alt) for x in names[SHOWN:])
        cards += (f'<li class="ws-card" id="ws-{int(w["n"])}"><h3>{esc(w.get("date", ""))}</h3>'
                  + (f'<p>{esc(w["did"])}</p>' if w.get("did") else "")
                  + (f'<div class="ws-photos">{shown}</div>' if shown else "")
                  + (f'<details><summary>{esc(MORE.format(n=len(names) - SHOWN))}</summary><div class="ws-photos">{more}</div></details>' if more else "")
                  + (f'<p class="ws-ver">{esc(PRINTED)}: {printed}</p>' if printed else "")
                  + (f'<p>{esc(FROM)}: {esc(w["line"])}</p>' if w.get("line") else "")
                  + (f'<p><a href="#{esc(w["loop"])}">{esc(TO_LOOP)}</a></p>' if w.get("loop") else "")
                  + "</li>")
    mosaic = _mosaic(each)
    return (f'<section class="sec ws" id="ws"><h2 class="ws-n">{esc(TITLE.format(n=len(ws)))}</h2><p class="lead">{esc(LEAD)}</p>'
            + (f'<div class="ws-mosaic">{"".join(_img(n, x, alt) for n, x, alt in mosaic)}</div>' if mosaic else "")
            + f'<ol class="ws-row">{cards}</ol></section>')
