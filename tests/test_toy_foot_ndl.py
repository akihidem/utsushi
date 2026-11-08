"""玩具の頁（つくる）の残りの直し（本人の答え 11-08。最初の言葉は「サイト、つくる、のところ。…大きく見る、図を見る、は統一して国会図書館へのリンクへ。
…ほかのおもちゃ、のリンク要らない。」）。

本人の答え（11-08）:
- つくるの頁の一番下の前と次のおもちゃと一覧への道は「外す」
- 作りながら見る頁の「大きく見る」も「国会図書館への道にそろえる」

見る線:
1. 玩具の頁の足に、前と次の玩具への道（「← 名」「名 →」）と「おもちゃの一覧」（/toys）が無い。作った物と入口への道は残る（答えに無いので替えない）
2. （外した）狭い幅の頭の並びは、本人の答え「スマホは…この形でよい」の後に、本人の言葉「縦書きは失敗なので前の形に戻す」で替わった。
   並びは頭を戻す PR の試験（test_toy_head_back）が見るので、ここでは見ない
3. 作りながら見る頁の原画と歌の畳みに「大きく見る」も頁の中に重ねる窓も無い。道は玩具の頁の頭と同じ 1 つ（図を見る（国立国会図書館））で、
   行き先は国立国会図書館のその絵の頁。絵そのものも同じ所へ。どちらも別のタブで開く（作りながら見る頁は、頁を離れると声の聞き取りと鏡が止まる）
4. 畳みにも「原文の引用。確かめた人」の行が無い（11-08 の最初の言葉「原文の引用確かめた人要らない」を、作りながら見る頁にもそろえる）
"""
import json
import os
import pathlib
import re
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from web import genga, genga_words, toy  # noqa: E402
from web.play_server import sources  # noqa: E402
from web.skin import ndl_page  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]

# 原画の写し（out/ の頁の絵）は git の外なので、まっさらな木には無い。写しが無い時だけ部品の絵を差し替え、絵のある形で道を見る（test_toy_page_tate と同じ形）
_real_pic = genga._pic


def _pic(sid, src, alt, lazy=False, href=None, **kw):
    got = _real_pic(sid, src, alt, lazy=lazy, href=href, **kw)
    if got[0]:
        return got
    tag, link = ("a", f' href="{href}"') if href else ("span", "")
    if href and kw.get("new_tab"):
        link += ' target="_blank" rel="noopener"'
    return (f'<{tag} class="genga-pic"{link} style="--genga-r:0.7000"><img src="/picture/{sid}/page" width="700" height="1000" alt="{alt}"></{tag}>', True)


genga._pic = _pic
G, T = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"
QUIET = "NDL-1187053-R0000013-L-5"  # 歌の読みが無い玩具（亀）
SIDS = sources()

# 1. 足の道
for sid in (G, T, QUIET, SIDS[0], SIDS[-1]):
    page = toy.toy_page(sid)
    i = SIDS.index(sid)
    others = [SIDS[j] for j in (i - 1, i + 1) if 0 <= j < len(SIDS)]
    for o in others:
        assert f'href="/toy/{o}"' not in page, (sid, o, "前か次の玩具への道が残った")
    assert not re.search(r"<a [^>]*>← |→</a>", page), (sid, "前か次の矢印の道が残った")
    assert 'href="/toys"' not in page and "おもちゃの一覧" not in page, (sid, "おもちゃの一覧への道が残った")
    tail = page[page.rindex('<section class="sec">'):]
    assert '<a href="/gallery">作った物</a>' in tail and '<a href="/">入口へ</a>' in tail, (sid, "作った物と入口への道は残す")
    assert page.rindex('class="sec ndl-credit"') > page.rindex('<a href="/">入口へ</a>'), (sid, "出典の字は頁の一番下のまま")

# 3・4. 作りながら見る頁の畳み
for sid in (G, T, QUIET):
    src = json.loads((ROOT / "data/sources" / f"{sid}.json").read_text(encoding="utf-8"))
    ndl = ndl_page(src)
    assert ndl.startswith("https://dl.ndl.go.jp/pid/1187053/1/"), (sid, ndl)
    fold = genga.fold(sid)
    assert fold and f'<details class="genga genga-fold"><summary>{genga_words.HEAD}</summary>' in fold, sid
    assert genga_words.BIG not in fold and "data-big" not in fold and "<dialog" not in fold and "<script" not in fold, (sid, "大きく見る か重ねる窓が残った")
    links = re.findall(r'<a ([^>]*)>', fold)
    assert links and all(f'href="{ndl}"' in a and 'target="_blank"' in a and 'rel="noopener"' in a for a in links), (sid, links)
    assert re.search(rf'<a href="{re.escape(ndl)}" target="_blank" rel="noopener"[^>]*>{re.escape(genga.NDL)}</a>', fold), (sid, "図を見る（国立国会図書館）の道が無い")
    assert re.search(r'<a class="genga-pic" href="[^"]+" target="_blank" rel="noopener"', fold), (sid, "絵そのものが同じ所へ行かない")
    assert "確かめた人" not in fold and "原文の引用" not in fold, (sid, "畳みに確かめた人の行が残った")
assert ("<ul" in genga.fold(G) or 'class="genga-songs"' in genga.fold(G)) and 'class="genga-songs"' not in genga.fold(QUIET), "歌の字は読みのある玩具だけ（前のまま）"
assert ".genga-fold [data-big]" not in genga.STYLE and not hasattr(genga, "SCRIPT"), "重ねる窓の CSS と JS が残った"
print("ok 玩具の頁の足に前と次と一覧の道が無い・作りながら見る頁の畳みは国立国会図書館への道 1 つ（別のタブ）")
