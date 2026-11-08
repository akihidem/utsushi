"""玩具の頁（つくる）の頭を #595 の前の形に戻す（本人の言葉 11-08「iPhone Airだとこの表示。原図を横幅いっぱいにする。縦書きは失敗なので前の形に戻す。」・
答え「広い画面も戻す」）。

本人の写真（御来迎の頁・幅 420 ほど）では、原図が左の半分ほどの幅しかなく、つくる の下の題の塊と狂歌の縦書きが右へはみ出して切れていた。
前の決め「絵の左横に縦で狂歌、その左横に御来迎 江都二色よりーの部分を置く」（11-08）は、この言葉で替わった。
同じ日の決め（確かめた人の行なし・出典の字は頁の一番下・図を見る は国立国会図書館へ 1 つ・図鑑の頁とほかのおもちゃの道なし）は残す。

見る線:
1. 頭の原画の部品は 絵（と 図を見る）→ 歌 の順。題の塊の縦の段は無い
2. 題の塊は、前の作品の札の所（玩具の名と つくる の後）に、札の形（class="label"）で横書き。出典の字（所蔵・権利）は札に入れず、頁の一番下のまま
3. 広い幅: 歌は絵の右に縦書き（#595 の前の形）。頭の 2 列は前の比（1.9 : 1 の上書きが無い）
4. 狭い幅: 原図は横幅いっぱい（高さの上限で細らせない）。脇の切り抜きは出さない（置く空きが無い）。歌は絵の真下に横書きで、高さの上限なし
5. 狭い幅の並び: 絵（と 図を見る）→ 歌 → 玩具の名 → つくる → 名の下の 1 行 → ほか（作品の札・くずし字を読む・これまでの記録の順）
6. 英語の頁の絵（plain）と作る時の畳み（fold）の高さの上限は今のまま（本人の言葉は玩具の頁の原図の話）
"""
import json
import os
import pathlib
import re
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from web import genga, toy  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
# 原画の写し（out/ の頁の絵）は git の外なので、まっさらな木には無い。写しが無い時だけ部品の絵を差し替え、絵のある形で並びを見る（test_toy_page_tate と同じ形）
_real_pic = genga._pic


def _pic(sid, src, alt, lazy=False, href=None, **kw):
    got = _real_pic(sid, src, alt, lazy=lazy, href=href, **kw)
    if got[0]:
        return got
    tag, link = ("a", f' href="{href}"') if href else ("span", "")
    return (f'<{tag} class="genga-pic"{link} style="--genga-r:0.7000"><img src="/picture/{sid}/page" width="700" height="1000" alt="{alt}"></{tag}>', True)


genga._pic = _pic
G, T = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"
QUIET = "NDL-1187053-R0000013-L-5"  # 歌の読みが無い玩具（亀）

# 1・2. 頭の並びと作品の札
for sid in (G, T, QUIET):
    src = json.loads((ROOT / "data/sources" / f"{sid}.json").read_text(encoding="utf-8"))
    page = toy.toy_page(sid)
    hero = re.search(r'<section class="hero">.*?</section>', page, re.S).group(0)
    # 歌のある頭は横書き（genga-flat）で出て、台本が測って縦書きにする（genga.FIT_SCRIPT・別の目の検品 11-08）ので、組の名の後ろに印が付きうる
    fig = re.search(r'<figure class="genga genga-head(?: genga-flat)?".*?</figure>', hero, re.S).group(0)
    assert 'class="genga-tate"' not in fig and 'class="genga-title"' not in fig, (sid, "題の塊の縦の段が残った")
    assert fig.index('class="genga-main"') < fig.index('class="genga-uta"'), (sid, "絵 → 歌 の順でない")
    if sid != QUIET:
        assert fig.index('class="genga-pic"') < fig.index('class="genga-songs"'), sid
    label = re.search(r'<p class="label">(.*?)</p>', hero, re.S)
    assert label and f"<b>{src['toy']}</b>" in label.group(1) and f"『{src['title']}』より" in label.group(1), (sid, "作品の札（題の塊）が無い")
    assert hero.index("<h1>") < hero.index('class="road"') < hero.index('class="label"') < hero.index('class="links"'), (sid, "札は つくる の後・くずし字の前")
    assert src["holding"] not in label.group(1) and "パブリック・ドメイン" not in label.group(1), (sid, "出典の字が札に戻った")
    assert src["holding"] in page[page.index('class="sec ndl-credit"'):], (sid, "出典の字は頁の一番下のまま")
    assert "確かめた人" not in hero and "ほかのおもちゃ" not in hero and f'href="/zukan/{sid}"' not in hero, (sid, "同じ日の残す決めが崩れた")
    assert 'class="genga-crop"' not in hero, (sid, "脇の切り抜きを出した")

css = genga.STYLE
wide, narrow = css[:css.index("@media (max-width:820px)")], css[css.index("@media (max-width:820px)"):]
rule = lambda sel, text: [b for s, b in re.findall(r"([^{}]+)\{([^{}]*)\}", text) if sel in [x.strip() for x in s.split(",")]]  # noqa: E731
# 3. 広い幅
assert ".genga-head{display:grid;grid-template-columns:minmax(0,1fr) auto" in wide, "広い幅は 絵 | 歌 の 2 列（前の形）"
assert ".genga-head .genga-songs{writing-mode:vertical-rl" in wide, "広い幅の歌は絵の右に縦書き（前の形）"
assert "genga-title" not in css and "genga-tate" not in css and "genga-crop" not in css
assert "1.9fr" not in toy.FOLD_STYLE, "頭の 2 列の上書きが残った"
# 4. 狭い幅
pic = rule(".genga-head .genga-pic", narrow)
assert pic and all("calc(var(--genga-h)" not in b for b in pic) and any("width:100%" in b for b in pic), ("狭い幅の原図が横幅いっぱいでない", pic)
songs = rule(".genga-head .genga-songs", narrow)
assert any("writing-mode:horizontal-tb" in b for b in songs) and not any(re.search(r"max-height:(?!none)", b) for b in songs), songs
# 5. 狭い幅の並び
fold_narrow = toy.FOLD_STYLE[toy.FOLD_STYLE.index("@media (max-width:820px){.hero{"):]
orders = {sel.strip(): int(n) for sel, n in re.findall(r"([^{}]+)\{[^{}]*?order:(\d+)", fold_narrow.split("{", 1)[1])}
want = [".hero>.genga-head>.genga-main", ".hero>.genga-head>.genga-uta", ".hero h1", ".hero .road", ".hero h1+.meta", ".hero>*>*"]
got = [orders.get(s) for s in want]
assert None not in got and got == sorted(got) and len(set(got)) == len(got), ("狭い幅の並びが 絵 → 歌 → 名 → つくる → 1 行 → ほか でない", dict(zip(want, got)))
# 6. 英語の頁と畳み
assert any("calc(var(--genga-h) * var(--genga-r))" in b for b in rule(".genga-plain .genga-pic", narrow)), "英語の頁の絵の上限が消えた"
assert ".genga-fold .genga-pic{width:min(100%,calc(var(--genga-h) * var(--genga-r)))}" in wide
print("ok 玩具の頭は #595 の前の形: 絵 → 歌（広い幅は縦・狭い幅は横）・題の塊は つくる の後の札・狭い幅の原図は横幅いっぱい")
