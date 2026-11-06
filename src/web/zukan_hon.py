"""図鑑の本の頁（/zukan/hon/<コマ>）。玩具の絵がある頁を、1 コマずつ本の順に見る（本人の決定 11-06）。

本人の決定: 図鑑に、玩具の絵がある頁を置く（「玩具の絵だけ。」。35 コマ全部ではない）。同じ取り込みの道（ingest・git の外）で取り、
図鑑から 1 コマずつ順に見られる形に。サイトに型紙の無い玩具（棚卸しの 26 種と、玩具の無い 7 頁）も原画として見える。
新しい字は「原画と歌」「大きく見る」のほかは足さない（コマの番号は今ある「本の n コマ目」の字で）。

判断の芯:
- 置く頁は棚卸しの玩具が載る頁（ingest.book_faces。54 頁）。奥付と玩具の無いコマは入らない。
- 1 つの画面に 1 コマ（見開き）。広い幅は本と同じに右の面を右へ、狭い幅は本の順（右の面が先）に縦に並べる。
- 頁の上の枠は棚卸しの玩具の所。サイトに玩具の頁がある玩具は、枠と名前から玩具の頁へ行ける。無い玩具は枠だけ
  （名前は作る側の見立てで人が確かめていないので、字にしない）。
- 歌の字は、人が確かめた読みだけを、その頁の下に出す（玩具の頁の頭と同じ genga.songs）。歌は絵の中に書かれている。
- 送る字は組み立ての頁と同じ「前へ」「次へ」。
"""
import json

from omochae import ingest
from omochae.hypotheses import ROOT

from . import genga, wording
from .genga_words import BIG, HEAD
from .skin import esc

PREV, NEXT = "前へ", "次へ"  # 組み立ての頁（kumitate.PREV・NEXT）と同じ字

STYLE = """
.zukan-hon .pages{display:flex;flex-direction:row-reverse;gap:6px;justify-content:center;align-items:flex-start}
.zukan-hon .face{flex:1 1 0;min-width:0;max-width:460px;margin:0}
.zukan-hon .face .genga-pic{width:100%}
.zukan-hon .face figcaption{font-size:13px;line-height:1.9;margin-top:8px}
.zukan-hon .face figcaption p{margin:0}
.zukan-hon .walk{display:flex;gap:18px;justify-content:space-between;margin:14px 0}
.zukan-hon a.genga-box:focus-visible{outline:3px solid var(--accent)}
@media (max-width:640px){.zukan-hon .pages{flex-direction:column}.zukan-hon .face{max-width:none}}
"""


def koma(frame):
    """今ある字「本の n コマ目」（wording.frame）で、コマの番号を言う。"""
    return wording.frame(f"NDL-1187053-R{frame:07d}-L")


def frames():
    """図鑑に置くコマ（本の順）。"""
    return sorted({c for c, _ in ingest.book_faces()})


def _site():
    """サイトの玩具（出典の記録がある物）。{印: 記録}"""
    out = {}
    for p in sorted((ROOT / "data/sources").glob("NDL-*.json")):
        out[p.stem] = json.loads(p.read_text(encoding="utf-8"))
    return out


def _inventory():
    return json.loads((ROOT / "data/inventory/edo-nishiki.json").read_text(encoding="utf-8"))["toys"]


def face_file(frame, side):
    return ingest.PAGES / f"{ingest.face_name(frame, side)}.jpg"


def _face(frame, side, toys, site):
    """1 つの頁。頁の全体の絵と玩具の所の枠、その下にサイトの玩具の名前と確かめた歌。"""
    name = ingest.face_name(frame, side)
    path = face_file(frame, side)
    mine = [t for t in toys if (int(t["frame"]), t["side"]) == (frame, side)]
    if path.exists():
        w, h = genga.size(path)
        boxes = ""
        for t in mine:
            b = genga.box({"crop_region": t["region"], "side": side})
            if not b:
                continue
            style = f"left:{b[0]:.2f}%;top:{b[1]:.2f}%;width:{b[2]:.2f}%;height:{b[3]:.2f}%"
            src = site.get(t["id"])
            boxes += (f'<a class="genga-box" href="/toy/{esc(t["id"])}" aria-label="{esc(src["toy"])}" style="{style};pointer-events:auto"></a>' if src
                      else f'<span class="genga-box" style="{style}" aria-hidden="true"></span>')
        pic = (f'<span class="genga-pic" style="--genga-r:{w / h:.4f}"><img src="/zukan/hon/{name}.jpg" width="{w}" height="{h}" '
               f'alt="{esc(koma(frame))}" loading="lazy">{boxes}</span>')
        big = f'<a href="/zukan/hon/{name}.jpg">{esc(BIG)}</a>'
    else:
        pic, big = "", f'<a href="{esc(ingest.face_url(frame, side))}">{esc(genga.NDL)}</a>'
    words = ""
    for t in mine:
        src = site.get(t["id"])
        if not src:
            continue
        songs = "".join(f"<p>{esc(e['text'])}</p>" for e in genga.songs(src))
        words += f'<p><a href="/toy/{esc(t["id"])}">{esc(src["toy"])}</a></p>' + (f'<div class="genga-songs">{songs}</div>' if songs else "")
    return f'<figure class="face" id="{name}">{pic}<figcaption>{words}<p>{big}</p></figcaption></figure>'


def page(frame, look=None, path=None):
    """1 コマの頁。前後のコマへ送る道と、その見開きの頁（玩具の絵がある面だけ）。"""
    from .zukan import NAV, _page

    order = frames()
    i = order.index(frame)
    toys, site = _inventory(), _site()
    faces = [f for f in ingest.book_faces() if f[0] == frame]
    title = koma(frame)
    walk = ('<p class="walk">'
            + (f'<a href="/zukan/hon/{order[i - 1]}">{esc(PREV)}</a>' if i > 0 else "<span></span>")
            + (f'<a href="/zukan/hon/{order[i + 1]}">{esc(NEXT)}</a>' if i + 1 < len(order) else "<span></span>") + "</p>")
    holding = next(iter(site.values()), {}).get("holding", "")
    body = (f'<style>{genga.STYLE}{STYLE}</style><div class="zukan-hon"><h1>{esc(HEAD)}</h1>{NAV}<h2>{esc(title)}</h2>{walk}'
            f'<div class="pages">{"".join(_face(c, s, toys, site) for c, s in faces)}</div>{walk}'
            f'<p class="meta">{esc(holding)}</p></div>')
    return _page(f"うつし · 図鑑 · {title}", body, look, path or f"/zukan/hon/{frame}")
