"""玩具の頁の頭で、題と歌の間に歌の高さぶんの空きを作らない（#134）。

なぜ試験にするか: 歌の箱を右へ寄せただけの形では、題の下の左側（幅 1440 で 417×360）が空いたまま札が歌の下へ送られていた。
./run.sh はブラウザなしで動くので、ここでは空きを消す組み方の印と字の順を見る（座標はブラウザで測って帳面に書いた）。
"""
import json
import os
import re
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ.pop("ANTHROPIC_API_KEY", None)

from web import skin, zukan  # noqa: E402
from web.toy import toy_page  # noqa: E402
from omochae.hypotheses import ROOT  # noqa: E402

# 原画の写し（out/ の頁の絵と切り抜き）は git の外なので、まっさらな木（clone しただけの木・./run.sh の場面）には無い（#450 と同じ）。
# 写しが無い時だけ、部品の絵を差し替えて絵のある形を作る（test_landscape_fit と同じ形。絵の有る無しに関わらず、並びと道を見る）
from web import genga as _genga  # noqa: E402

_real_pic = _genga._pic


def _pic(sid, src, alt, lazy=False, href=None, **kw):
    got = _real_pic(sid, src, alt, lazy=lazy, href=href, **kw)  # 増えた引数（new_tab）も本物へ渡す
    if got[0]:
        return got
    tag, link = ("a", f' href="{href}"') if href else ("span", "")
    return (f'<{tag} class="genga-pic"{link} style="--genga-r:0.7000"><img src="/picture/{sid}/page" width="700" height="1000" alt="{alt}"></{tag}>', True)


_genga._pic = _pic


GORAIGO, TORA = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"
def _no_reading():
    """歌の読みの無い試作の玩具を 1 つ選ぶ（箱は頁の一部）。くずし字の歌の読みを 10 歌ずつ足していくので（11-08）、名指しの印にすると、
    読みが入るたびに例の玩具を替えないといけない。並びの頭から、出典の記録に読みの無い玩具を選ぶ"""
    from omochae import hypotheses as _h
    for p in sorted((ROOT / "data/sources").glob("NDL-*.json")):
        s = json.loads(p.read_text(encoding="utf-8"))
        if s.get("transcription", {}).get("entries") or not (ROOT / "data/hypotheses" / p.name).exists():
            continue
        # 御来迎と虎と同じ頁を分け合う玩具は外す（この試験は例の玩具の頁の写しを消して見る所があり、同じ頁の御来迎と虎の写しまで消えるため）
        if p.stem.rsplit("-", 1)[0] in {"NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"} or p.stem in {"NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"}:
            continue
        if _genga.box(s) and _h.stage(p.stem) != "必須":
            return p.stem
    raise AssertionError("読みの無い試作の玩具が無い")


PLAIN = _no_reading()  # 歌の読みの無い試作の玩具

for look in ("tenji", "zine"):
    for sid in (GORAIGO, TORA):
        page = toy_page(sid, look)
        hero = page[page.index('class="hero"'):page.index('id="kasetsu"')]
        # 原画と歌（本人の指示 11-06）: 歌は頁の全体の絵と組にして左の欄に置く。絵 → 歌 の順で、作品の札（class="label"）は題と つくる の後
        # （#595 の前の形。本人の言葉 11-08「縦書きは失敗なので前の形に戻す」・答え「広い画面も戻す」）。札は題の塊だけで、出典の字は頁の一番下（同じ日の決めのまま）
        assert (hero.index('class="genga genga-head"') < hero.index('class="genga-pic"') < hero.index('class="genga-songs"')
                < hero.index("<h1>") < hero.index('class="label"') < hero.index('class="links"')), (look, sid)
        assert 'class="genga-title"' not in hero and 'class="sec ndl-credit"' in page, (look, sid)
        assert 'class="songs"' not in hero, (look, sid)
    # 歌の読みの無い玩具は字の歌を出さない（断りの 1 行だけ）。札は題のすぐ下のまま
    page = toy_page(PLAIN, look)
    hero = page[page.index('class="hero"'):page.index('id="kasetsu"')]
    assert 'class="songs"' not in hero and 'class="genga-songs"' not in hero and hero.index("<h1>") < hero.index('class="label"'), look

css = skin.BASE
wide = css[:css.index("@media (max-width:820px)")]
assert re.search(r"\.hero \.songs\{[^}]*float:right", wide), "机の幅では歌を右に浮かせる"
narrow = css[css.index("@media (max-width:820px)"):]
assert re.search(r"\.hero \.songs\{[^}]*float:none", narrow), "スマホの幅は今の縦の並びのまま"

# 図鑑の札も同じ形で、題と歌の間に同じ空きがあった
wide = zukan.STYLE[:zukan.STYLE.index("@media (max-width:760px)")]
assert re.search(r"\.zukan \.song\{[^}]*float:right", wide), "図鑑も机の幅では歌を右に浮かせる"
narrow = zukan.STYLE[zukan.STYLE.index("@media (max-width:760px)"):]
assert re.search(r"\.zukan \.song\{[^}]*float:none", narrow), "図鑑もスマホの幅は今の縦の並びのまま"
# 前は図鑑の玩具の段（zukan.toy_section）の並びも見ていた。図鑑の頁は外した（本人の言葉 11-08「図鑑のページ要らない」）。図鑑の CSS は くずし字を読む の頁が使うので上で見る
print("ok")
