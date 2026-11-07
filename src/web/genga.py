"""原画と歌（本人の指示 11-06）。玩具が載る頁の全体の絵と、人が確かめた歌の読みを、1 つの組にして出す部品。

本人の言葉: 「サイトに掲載されていない原画が多数あるのでチェックをお願いしたい。また、原画はアップでなくて、ページ全体を
掲載して欲しい。また、狂歌は制作の際参考になるので必ず原画と一緒に見れるようにしてください。」
作りは原画の載せ方の設計メモ（11-06。統括が OK）と、その見直し（UX の目と統括の決め）のとおり。

判断の芯:
- 絵は頁の全体を、拡大せず、縦横の比も絵のままで出す。玩具の所は、頁の絵の上に細い枠で示す（切り抜きは別に置かない）。
  枠の箱は出典の記録の crop_region。頁の片側の全体が玩具の記録の物（必須 2 種）は枠を出さない。
- 歌は絵と組にする。玩具の頁の頭は、左から 題の塊 → 歌 → 絵 で、題の塊と歌は縦書き（本人の言葉 11-08。狭い幅も縦のまま、高さに上限）。
  字にするのは人が確かめた読みだけ（J-016）。
  読みが無い玩具は、歌は絵の中に書かれているので、字は出さない（断りも足さない。本人の決定 11-06）。
- 狭い幅の絵の高さの上限は CSS の変数 1 つ（--genga-h、44svh から）。段 0 の「最初の画面にボタン 1 つ」の余地を残すため。
- 出し方は 3 つ。head（玩具の頁の頭。絵そのものと「図を見る（国立国会図書館）」の 1 つの道は、国立国会図書館のその絵の頁へ行く・本人の言葉 11-08）、
  fold（作る時の畳み。道は head と同じ 1 つで国立国会図書館へ・本人の答え 11-08「作りながら見る頁の大きく見るも国会図書館への道にそろえる」。
  作りながら見る頁は、頁を離れると声の聞き取りと鏡が止まるので、別のタブで開く）、plain（英語の頁。絵だけで、字は足さない）。
- 頁の写しが無い所（取れなかった・取る前の木）は、玩具の写しを比を保って出す。頁は止めない。
"""
import functools
import json

from omochae import ingest, labels
from omochae.hypotheses import ROOT

from . import wording
from .genga_words import HEAD
from .skin import esc

QUOTE = "原文の引用。確かめた人: "  # 今の玩具の頁の頭と同じ字
NDL = "図を見る（国立国会図書館）"  # 今の字
WHOLE = 95.0  # 頁の片側をこれだけ覆う箱は「頁の全体の記録」と見て、枠を出さない（%）

STYLE = """
.genga{margin:0;--genga-h:44vh;--genga-h:44svh}
.genga-pic{position:relative;display:block;width:100%;line-height:0}
.genga-pic img{display:block;width:100%;height:auto;background:var(--soft)}
.genga-box{position:absolute;border:2px solid var(--accent);outline:1px solid rgba(255,255,255,.75);pointer-events:none}
.genga-head{display:grid;grid-template-columns:auto minmax(0,1fr);gap:10px 22px;align-items:start}
.genga-songs p{margin:0 .3em}
.genga-head .genga-tate{display:flex;flex-direction:row;gap:18px;align-items:flex-start}
.genga-head .genga-title{writing-mode:vertical-rl;max-height:min(70vh,620px);font-size:13px;line-height:2;letter-spacing:.14em;color:var(--mute)}
.genga-head .genga-title p{margin:0 .2em}.genga-head .genga-title b{font-size:clamp(17px,1.7vw,22px);font-weight:400;color:var(--fg);letter-spacing:.3em}
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
.genga-fold .genga-go{display:inline-flex;align-items:center;font-size:15px;letter-spacing:.08em;min-height:44px;padding:0 18px;margin:8px 0;border:1px solid var(--accent);border-radius:4px;color:var(--fg);text-decoration:none}
.genga-fold .genga-pic{width:min(100%,calc(var(--genga-h) * var(--genga-r)))}
.genga-fold .genga-songs{font-size:15px;line-height:2;margin:8px 0}
@media (max-width:820px){
.genga-head{grid-template-columns:minmax(0,1fr)}
.genga-head .genga-pic,.genga-plain .genga-pic{width:min(100%,calc(var(--genga-h) * var(--genga-r)));flex:0 0 auto}
.genga-head .genga-crop{display:block}
.genga-head .genga-tate{justify-content:flex-end;gap:12px}
.genga-head .genga-songs,.genga-head .genga-title{max-height:min(52vh,420px)}
.genga-head .genga-songs{font-size:16px;line-height:2.1}
}
"""

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


def _pic(sid, src, alt, lazy=False, href=None, new_tab=False):
    """頁の全体の絵と玩具の所の枠。頁の写しが無ければ玩具の写し（比は保つ）。どちらも無ければ空。
    href があれば絵そのものを、そのリンクにする（押せば大きく見られる。字のリンクと同じ所）。new_tab は別のタブで開く（頁を離れない所の畳み）。"""
    load = ' loading="lazy"' if lazy else ""
    tag, link = ("a", f' href="{esc(href)}"' + (' target="_blank" rel="noopener"' if new_tab else "")) if href else ("span", "")
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
    """玩具の頁の頭。左から 題の塊 → 狂歌 → 絵（本人の言葉 11-08「絵の左横に縦で狂歌、その左横に御来迎 江都二色よりーの部分を置く」）。
    題の塊と狂歌は縦書き（入口の縦の組みと同じ考え）。狭い幅は絵が上で、題の塊と狂歌は縦のまま並べて「つくる」の釦の後ろへ（toy.FOLD_STYLE）。
    「大きく見る」と「図を見る」は 1 つにし、絵そのものも同じ所（国立国会図書館のその絵の頁）へ行く（本人の言葉「統一して国会図書館へのリンクへ」）。
    原文の引用の「確かめた人」の行と、国立国会図書館の出典の字は頭に置かない（本人の言葉「確かめた人要らない」「文言はページの一番下に」。
    出典の字は toy の頁の一番下の段 ndl_credit）。"""
    from .skin import artwork_title, ndl_page

    src = src or _source(sid)
    ndl = ndl_page(src)
    pic, whole = _pic(sid, src, alt(src), href=ndl or None)
    pic = f'<div class="genga-row">{pic}{crop(sid, src) if whole else ""}</div>' if pic else ""
    # 原画のすぐ後に、作ってみた実物（人が確かめた写真。無ければ何も置かない。窓口の決め 125731・(b)）を 1 枚（本人のサイト体験レビュー 11-07 の 2。web.made）
    from . import made

    pic += made.figure(sid, "made genga-made", photos=photos)
    lines, _ = _songs(src)
    tate = f'<div class="genga-tate"><div class="genga-title">{artwork_title(src["toy"], src)}</div>{lines}</div>'
    cap = f'<div class="genga-cap"><p><a href="{esc(ndl)}">{esc(NDL)}</a></p></div>'
    return (f'<style>{STYLE}</style><figure class="genga genga-head" id="genga" aria-label="{esc(HEAD)}">{tate}'
            f'<div class="genga-main">{pic}{cap}</div></figure>')


def ndl_credit(sid, src=None):
    """玩具の頁の一番下の出典の段（国立国会図書館デジタルコレクションの所蔵・コマ・権利）。字は前の頭の札と出所の字のまま（替えない）。"""
    from .skin import artwork_credit

    src = src or _source(sid)
    return f'<section class="sec ndl-credit"><p class="meta">{artwork_credit(src)}<br>{esc(wording.frame(sid))}</p></section>'


def fold(sid, src=None):
    """作る時の畳み。1 回押すと開く。絵は開くまで取らない。道は玩具の頁の頭と同じ 1 つ（図を見る（国立国会図書館））で、絵そのものも同じ所へ。

    前は「大きく見る」で頁の中に重ねて出した。本人の答え（11-08）「作りながら見る頁の大きく見るも国会図書館への道にそろえる」で、頭と同じ道にした。
    作りながら見る頁は、頁を離れると声の聞き取りと鏡が止まるので、道は別のタブで開く（前の「頁を離れない」の理由は、この形で残す）。
    原文の引用の「確かめた人」の行も出さない（11-08 の最初の言葉「原文の引用確かめた人要らない」を頭とそろえる）。"""
    from .skin import ndl_page

    src = src or _source(sid)
    ndl = ndl_page(src)
    pic, _ = _pic(sid, src, alt(src), lazy=True, href=ndl or None, new_tab=True)
    if not pic:
        return ""
    lines, _ = _songs(src)
    go = f'<p><a href="{esc(ndl)}" target="_blank" rel="noopener" class="genga-go">{esc(NDL)}</a></p>' if ndl else ""
    return f'<style>{STYLE}</style><details class="genga genga-fold"><summary>{esc(HEAD)}</summary>{pic}{lines}{go}</details>'


def plain(sid, alt):
    """絵だけ（英語の頁）。歌の字も新しい字も出さない。"""
    pic, _ = _pic(sid, _source(sid), alt)
    return f'<style>{STYLE}</style><figure class="genga genga-plain">{pic}</figure>' if pic else ""
