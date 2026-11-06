"""ページを白案に統一する（本人の決定 11-06「ページは白案で統一します。黒案にだけある要素は白案に入れてください」）の床。

見る事: 黒の表紙にだけあった、最初の玩具の額の絵と 1 行が、白の入口の扉に字のまま出る（題の間の後、北斎漫画の縦読みの前）／
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
assert white.count('class="tj-door"') == 1 and f'<p class="meta">{looks.DOOR_LINE}</p>' in white
door = white.index('class="tj-door"')
assert white.index('class="tj-hall"') < door, "題の間の後"
assert door < white.index('class="tj-work"', door) < white.index("</section>", door), "扉に額の絵"
first = looks.toys()[0]["sid"]
# 額の絵は、図の写し（out/sources、git の外）がある時だけ /picture/<印> を敷く（looks._bg）。写しの無い木では地の色だけになる
inner = white[door:white.index("</section>", door)]
assert looks._bg(first, looks.framed_pos(first), looks.FRAMED) in inner, "額は最初の玩具の図（黒の表紙と同じ敷き方）"
if 'id="zn-hokusai"' in white:
    assert door < white.index('id="zn-hokusai"'), "扉の後に北斎漫画の縦読み"
# 公開デモは白の 1 つだけ
sh = (ROOT / "run-demo.sh").read_text(encoding="utf-8")
assert re.search(r'^LOOKS="tenji"', sh, re.M) and 'LOOKS="tenji zine"' not in sh
print("ok 白の入口に黒にだけあった額の絵と 1 行が入り、公開デモは白の 1 つだけ")
