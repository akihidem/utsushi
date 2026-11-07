"""玩具の頁の頭で、題と歌の間に歌の高さぶんの空きを作らない（#134）。

なぜ試験にするか: 歌の箱を右へ寄せただけの形では、題の下の左側（幅 1440 で 417×360）が空いたまま札が歌の下へ送られていた。
./run.sh はブラウザなしで動くので、ここでは空きを消す組み方の印と字の順を見る（座標はブラウザで測って帳面に書いた）。
"""
import os
import re
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ.pop("ANTHROPIC_API_KEY", None)

from web import skin, zukan  # noqa: E402
from web.toy import toy_page  # noqa: E402

GORAIGO, TORA = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"
PLAIN = "NDL-1187053-R0000009-L-2"

for look in ("tenji", "zine"):
    for sid in (GORAIGO, TORA):
        page = toy_page(sid, look)
        hero = page[page.index('class="hero"'):page.index('id="kasetsu"')]
        # 原画と歌（本人の指示 11-06）: 歌は頁の全体の絵と組にして左の欄に置く。11-08 の本人の言葉「絵の左横に縦で狂歌、その左横に御来迎 江都二色よりーの部分を置く」で、
        # 左から 題の塊 → 狂歌 → 絵。作品の札（class="label"）は、題の塊を原画の部品へ、出典の字を頁の一番下へ分けたので頭に無い
        assert (hero.index('class="genga genga-head"') < hero.index('class="genga-title"') < hero.index('class="genga-songs"')
                < hero.index('class="genga-pic"') < hero.index("<h1>") < hero.index('class="links"')), (look, sid)
        assert 'class="label"' not in hero and 'class="sec ndl-credit"' in page, (look, sid)
        assert 'class="songs"' not in hero, (look, sid)
    # 歌の読みの無い玩具は字の歌を出さない（断りの 1 行だけ）。札は題のすぐ下のまま
    page = toy_page(PLAIN, look)
    hero = page[page.index('class="hero"'):page.index('id="kasetsu"')]
    assert 'class="songs"' not in hero and 'class="genga-songs"' not in hero and hero.index('class="genga-title"') < hero.index("<h1>"), look

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
section = zukan.toy_section(GORAIGO)
assert section.index("<h2>") < section.index('class="song"') < section.index('class="links"')
print("ok")
