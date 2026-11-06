"""ページを白案に統一する（本人の決定 11-06「ページは白案で統一します。黒案にだけある要素は白案に入れてください」）の床。

見る事: 黒の表紙にだけあった、最初の玩具の額の絵と 1 行が、白の入口の最初の画面（題の間）に、額と額の札として字のまま出る／
公開デモの命令（run-demo.sh）は白の 1 サイトだけを立てる。黒の皮の作り（--look zine）は消していない。
"""
import os
import pathlib
import re
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from web import looks  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
assert looks.DOOR_LINE == "江都二色　安永二年　うしなわれた玩具", "黒の表紙の字のまま"
white, black = looks.PAGES["tenji"](), looks.PAGES["zine"]()
assert f'<p class="meta">{looks.DOOR_LINE}</p>' in black, "黒の表紙の 1 行は前と同じ所に（黒の作りは残す）"
# 額の絵は入口の最初の画面（題の間）に掛け、黒の 1 行は額の札にする（ジャーニーマップの工程 1「絵 1 枚と 1 行とボタン 1 つ」。前は次の 1 室の扉だった）
assert 'class="tj-door"' not in white, "扉の節は無くした（額は題の間へ）"
hall = white.index('class="tj-hall')
hall_end = white.index("</section>", hall)
inner = white[hall:hall_end]
assert inner.count('class="tj-hallwork"') == 1 and f'<figcaption class="meta">{looks.DOOR_LINE}</figcaption>' in inner, "額と、黒の 1 行の札が題の間に"
assert inner.index('class="tj-hallwork"') < inner.index("<h1>うつし</h1>") < inner.index('class="road-go"'), "額・題・えらぶの順"
first = looks.toys()[0]
# 額の絵は、図の写し（out/sources、git の外）がある時だけ /picture/<印> を敷く（looks._bg）。写しの無い木では地の色だけになる
assert looks._bg(first["sid"], looks.framed_pos(first["sid"]), looks.FRAMED) in inner, "額は最初の玩具の図（黒の表紙と同じ敷き方）"
assert f'role="img" aria-label="{first["toy"]}の図"' in inner, "額に読み上げの名（全部の玩具の一覧の絵と同じ字の形）"
work = inner[inner.index('class="tj-hallwork"'):inner.index("</figure>")]
assert "<a " not in work and "<button" not in work, "額は押せる口にしない（大きいボタンは えらぶ 1 つ）"
assert inner.count('class="road-go"') == 1
assert 'id="zn-hokusai"' not in white, "白の入口に北斎漫画の縦読みを置かない（序の頁へ。統括の決め 11-06）"
# 狭い画面の札も 12px 以上
css = looks.TENJI
assert re.search(r"\.tj-hallwork \.meta\{writing-mode:vertical-rl;font-size:(\d+)px", css) and int(re.search(r"\.tj-hallwork \.meta\{writing-mode:vertical-rl;font-size:(\d+)px", css).group(1)) >= 12
# 公開デモは白の 1 つだけ
sh = (ROOT / "run-demo.sh").read_text(encoding="utf-8")
assert re.search(r'^LOOKS="tenji"', sh, re.M) and 'LOOKS="tenji zine"' not in sh
print("ok 白の入口に黒にだけあった額の絵と 1 行が入り、公開デモは白の 1 つだけ")
