"""原画と歌（本人の指示 11-06）。玩具が載る頁の全体の絵と、人が確かめた歌の読みを、1 つの組にして出す部品。

本人の言葉: 「サイトに掲載されていない原画が多数あるのでチェックをお願いしたい。また、原画はアップでなくて、ページ全体を
掲載して欲しい。また、狂歌は制作の際参考になるので必ず原画と一緒に見れるようにしてください。」
作りは原画の載せ方の設計メモ（11-06。統括が OK）と、その見直し（UX の目と統括の決め）のとおり。

判断の芯:
- 絵は頁の全体を、拡大せず、縦横の比も絵のままで出す。玩具の所は、頁の絵の上に細い枠で示す（切り抜きは別に置かない）。
  枠の箱は出典の記録の crop_region。頁の片側の全体が玩具の記録の物（必須 2 種）は枠を出さない。
- 歌は絵と組にする。広い幅は絵の横に縦書き、狭い幅は絵の真下に横書き。字にするのは人が確かめた読みだけ（J-016）。
  読みが無い玩具は、歌は絵の中に書かれているので、字は出さない（断りも足さない。本人の決定 11-06）。
- 狭い幅の絵の高さの上限は CSS の変数 1 つ（--genga-h、44svh から）。段 0 の「最初の画面にボタン 1 つ」の余地を残すため。
- 出し方は 3 つ。head（玩具の頁の頭。「大きく見る」は絵そのものへ行く）、fold（作る時の畳み。「大きく見る」は頁の中で重ねて出す。
  作りながら見る頁は、頁を離れると声の聞き取りと鏡が止まるため）、plain（英語の頁。絵だけで、字は足さない）。
- 頁の写しが無い所（取れなかった・取る前の木）は、玩具の写しを比を保って出す。頁は止めない。
"""
import functools
import json

from omochae import ingest, labels
from omochae.hypotheses import ROOT

from . import wording
from .genga_words import BIG, HEAD
from .skin import esc

QUOTE = "原文の引用。確かめた人: "  # 今の玩具の頁の頭と同じ字
NDL = "図を見る（国立国会図書館）"  # 今の字
WHOLE = 95.0  # 頁の片側をこれだけ覆う箱は「頁の全体の記録」と見て、枠を出さない（%）

STYLE = """
.genga{margin:0;--genga-h:44vh;--genga-h:44svh}
.genga-pic{position:relative;display:block;width:100%;line-height:0}
.genga-pic img{display:block;width:100%;height:auto;background:var(--soft)}
.genga-box{position:absolute;border:2px solid var(--accent);outline:1px solid rgba(255,255,255,.75);pointer-events:none}
.genga-head{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:10px 22px;align-items:start}
.genga-songs p{margin:0 .3em}
.genga-head .genga-songs{writing-mode:vertical-rl;max-height:min(70vh,620px);font-size:clamp(16px,1.6vw,21px);line-height:2.3;letter-spacing:.14em}
.genga-cap{grid-column:1/-1;font-size:12px;color:var(--mute);letter-spacing:.1em;line-height:1.9;margin:0}
.genga-cap p{margin:0 0 4px}
.genga-cap a{display:inline-flex;align-items:center;min-height:44px;margin-right:1.2em}
a.genga-pic{cursor:zoom-in}
.genga-row{display:flex;gap:10px;align-items:flex-start;min-width:0}
.genga-crop{display:none;flex:1 1 0;min-width:0;line-height:0}
.genga-crop img{display:block;width:100%;height:auto;max-height:var(--genga-h);object-fit:contain;object-position:left top}
.genga-made{margin:14px 0 0;width:min(240px,60%);line-height:0}
.genga-made img{display:block;width:100%;height:auto;border:1px solid var(--frame);background:var(--soft)}
.genga-made figcaption{line-height:1.6;font-size:12px;letter-spacing:.2em;color:var(--mute);margin-top:6px}
.genga-fold{margin:10px 0}
.genga-fold summary{cursor:pointer;min-height:44px;display:flex;align-items:center;letter-spacing:.12em}
.stage .genga-fold{padding:0 16px}
.genga-fold .genga-pic{cursor:zoom-in}
.genga-fold [data-big]{font:inherit;font-size:15px;letter-spacing:.08em;min-height:44px;padding:0 18px;margin:8px 0;border:1px solid var(--accent);border-radius:4px;background:transparent;color:var(--fg);cursor:pointer}
.genga-fold .genga-pic{width:min(100%,calc(var(--genga-h) * var(--genga-r)))}
.genga-fold .genga-songs{font-size:15px;line-height:2;margin:8px 0}
.genga-dlg{border:0;padding:0;background:transparent;max-width:98vw;max-height:98vh}
.genga-dlg::backdrop{background:rgba(0,0,0,.82)}
.genga-dlg img{display:block;max-width:98vw;max-height:98vh;width:auto;height:auto}
@media (max-width:820px){
.genga-head{grid-template-columns:minmax(0,1fr)}
.genga-head .genga-pic,.genga-plain .genga-pic{width:min(100%,calc(var(--genga-h) * var(--genga-r)));flex:0 0 auto}
.genga-head .genga-crop{display:block}
.genga-head .genga-songs{writing-mode:horizontal-tb;max-height:none;font-size:16px;line-height:2}
}
"""

# 作る時の畳みの「大きく見る」。頁を離れずに重ねて出し、押すか Esc で閉じる。畳みの中の絵を押しても同じに開く
SCRIPT = """<script>(()=>{document.querySelectorAll('.genga-fold [data-big]').forEach(b=>{const d=b.parentElement.querySelector('dialog');
if(!d||!d.showModal){b.hidden=true;return}const open=()=>d.showModal();b.addEventListener('click',open);
const p=b.parentElement.querySelector('.genga-pic');if(p)p.addEventListener('click',open);d.addEventListener('click',()=>d.close())})})()</script>"""


def alt(src):
    """絵の読み上げの字。新しい字を足さず、玩具の名と本人が採った見出しにする（統括の決め 11-06）。"""
    return f'{src["toy"]} {HEAD}'


def _source(sid):
    return json.loads((ROOT / "data/sources" / f"{sid}.json").read_text(encoding="utf-8"))


def page_file(src):
    return ingest.PAGES / f"{ingest.page_name(src)}.jpg"


@functools.lru_cache(maxsize=512)
def _size(path, mtime):
    from PIL import Image

    with Image.open(path) as im:
        return im.size


def size(path):
    """絵の縦横（画素）。width と height を img に書いて、読み込みで頁が跳ねないようにする。"""
    return _size(str(path), path.stat().st_mtime)


def box(src):
    """玩具の所の枠。頁の片側に対する %（左・上・幅・高さ）。頁の片側の全体を覆う記録は None。"""
    try:
        x, y, w, h = (float(v) for v in src["crop_region"].removeprefix("pct:").split(","))
    except (KeyError, ValueError):
        return None
    left = (x if src["side"] == "L" else x - 50) * 2
    width = w * 2
    if width * h / 100 >= WHOLE:
        return None
    return max(0.0, left), max(0.0, y), min(width, 100.0), min(h, 100.0)


def songs(src):
    """人が確かめた歌の読み（採らなかった読みは labels.source_lines が外す）。"""
    return [e for e in labels.source_lines(src) if e.get("checked_by")]


def _pic(sid, src, alt, lazy=False, href=None):
    """頁の全体の絵と玩具の所の枠。頁の写しが無ければ玩具の写し（比は保つ）。どちらも無ければ空。
    href があれば絵そのものを、そのリンクにする（押せば大きく見られる。字のリンクと同じ所）。"""
    load = ' loading="lazy"' if lazy else ""
    tag, link = ("a", f' href="{esc(href)}"') if href else ("span", "")
    page = page_file(src)
    if page.exists():
        w, h = size(page)
        b = box(src)
        frame = (f'<span class="genga-box" style="left:{b[0]:.2f}%;top:{b[1]:.2f}%;width:{b[2]:.2f}%;height:{b[3]:.2f}%" aria-hidden="true"></span>'
                 if b else "")
        # 包みの幅を絵の比から決める（--genga-r）。高さの上限で絵が細くなっても、包みと絵の大きさが同じなので、枠の % がずれない
        return (f'<{tag} class="genga-pic"{link} style="--genga-r:{w / h:.4f}"><img src="/picture/{esc(sid)}/page" width="{w}" height="{h}" alt="{esc(alt)}"{load}>'
                f'{frame}</{tag}>'), True
    crop = ROOT / "out/sources" / f"{sid}.jpg"
    if crop.exists():
        w, h = size(crop)
        return f'<span class="genga-pic" style="--genga-r:{w / h:.4f}"><img src="/picture/{esc(sid)}" width="{w}" height="{h}" alt="{esc(alt)}"{load}></span>', False
    return "", False


def _songs(src):
    """歌の字と、その印の 1 行（原文の引用・確かめた人）。読みが無ければ両方とも空。"""
    lines = songs(src)
    if not lines:
        return "", ""
    who = "・".join(sorted({wording.plain(e["checked_by"]) for e in lines}))
    body = "".join(f"<p>{esc(e['text'])}</p>" for e in lines)
    return f'<div class="genga-songs">{body}</div>', f'<p class="meta">{esc(QUOTE + who)}</p>'


def crop(sid, src):
    """頁を分け合う玩具（枠がある玩具）の今の切り抜き。狭い幅で、頁の絵の右の空きに小さく置く（UX の見直し・統括の決め 11-06）。
    頁の絵の中では玩具がとても小さくなるため。字は足さない（読み上げは隣の頁の絵と同じ玩具なので空）。"""
    path = ROOT / "out/sources" / f"{sid}.jpg"
    if not box(src) or not path.exists():
        return ""
    w, h = size(path)
    return f'<span class="genga-crop"><img src="/picture/{esc(sid)}" width="{w}" height="{h}" alt="" loading="lazy"></span>'


def head(sid, src=None, photos=True):
    """玩具の頁の頭。絵 → 歌の順（広い幅は横に並ぶ）。「大きく見る」と絵そのものは、頁の全体の絵へ。"""
    src = src or _source(sid)
    pic, whole = _pic(sid, src, alt(src), href=f"/picture/{sid}/page" if page_file(src).exists() else None)
    pic = f'<div class="genga-row">{pic}{crop(sid, src) if whole else ""}</div>' if pic else ""
    # 原画のすぐ後に、作ってみた実物（人が確かめた写真。無ければ組み立ての止まった形）を 1 枚（本人のサイト体験レビュー 11-07 の 2。web.made）
    from . import made

    pic += made.figure(sid, "made genga-made", photos=photos)
    big = f'<a href="/picture/{esc(sid)}/page">{esc(BIG)}</a>' if whole else ""
    lines, mark = _songs(src)
    # 印の 1 行は絵の下の行に置く。歌の横の欄に置くと、横書きの字の幅で欄が広がり、広い幅で絵が細くなった
    cap = (f'<div class="genga-cap">{mark}<p>{esc(src.get("holding", ""))}　{esc(wording.frame(sid))}<br>{big}'
           f'<a href="{esc(src.get("image_url", ""))}">{esc(NDL)}</a></p></div>')
    return (f'<style>{STYLE}</style><figure class="genga genga-head" id="genga" aria-label="{esc(HEAD)}">{pic}'
            f'<div>{lines}</div>{cap}</figure>')


def fold(sid, src=None):
    """作る時の畳み。1 回押すと開く。絵は開くまで取らない。「大きく見る」は頁の中で重ねて出す（頁を離れない）。"""
    src = src or _source(sid)
    pic, whole = _pic(sid, src, alt(src), lazy=True)
    if not pic:
        return ""
    big = (f'<button type="button" class="quiet" data-big>{esc(BIG)}</button>'
           f'<dialog class="genga-dlg" aria-label="{esc(HEAD)}"><img src="/picture/{esc(sid)}/page" alt="{esc(alt(src))}" loading="lazy"></dialog>'
           if whole else "")
    lines, mark = _songs(src)
    return (f'<style>{STYLE}</style><details class="genga genga-fold"><summary>{esc(HEAD)}</summary>{pic}{lines}{mark}{big}</details>'
            + (SCRIPT if whole else ""))


def plain(sid, alt):
    """絵だけ（英語の頁）。歌の字も新しい字も出さない。"""
    pic, _ = _pic(sid, _source(sid), alt)
    return f'<style>{STYLE}</style><figure class="genga genga-plain">{pic}</figure>' if pic else ""
