"""ページを白案に統一する（本人の決定 11-06「ページは白案で統一します。黒案にだけある要素は白案に入れてください」）の床。

見る事: 黒の表紙にだけあった、最初の玩具の額の絵と 1 行が、白の入口の題の間のすぐ後の扉に字のまま出る（最初の画面は題と えらぶ と副題だけ。本人の決定 11-07）／
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
# 最初の画面（題の間）は題と「えらぶ」と副題だけ。額の絵と黒の 1 行は、すぐ後の 1 室（扉）に掛ける
# （本人の決定 11-07「前の白の案の間」は B＝入口の絵の前の間。11-06 夜に一度、額を題の間へ入れた形から戻した）
hall = white.index('class="tj-hall')
hall_end = white.index("</section>", hall)
inner = white[hall:hall_end]
assert "tj-work" not in inner and "role=\"img\"" not in inner, "最初の画面に額を入れない"
assert inner.index("<h1>うつし</h1>") < inner.index('class="road-go"') and inner.count('class="road-go"') == 1, "題・えらぶの順、えらぶは 1 つ"
assert white.count('class="tj-door"') == 1 and f'<p class="meta">{looks.DOOR_LINE}</p>' in white
door = white.index('class="tj-door"')
assert hall_end < door, "題の間の後"
door_html = white[door:white.index("</section>", door)]
first = looks.toys()[0]
# 額の絵は、図の写し（out/sources、git の外）がある時だけ /picture/<印> を敷く（looks._bg）。写しの無い木では地の色だけになる
assert looks._bg(first["sid"], looks.framed_pos(first["sid"]), looks.FRAMED) in door_html, "額は最初の玩具の図（黒の表紙と同じ敷き方）"
assert f'role="img" aria-label="{first["toy"]}の図"' in door_html, "額に読み上げの名（全部の玩具の一覧の絵と同じ字の形）"
assert "<a " not in door_html and "<button" not in door_html, "額は押せる口にしない（大きいボタンは えらぶ 1 つ）"
assert 'id="zn-hokusai"' not in white, "白の入口に北斎漫画の縦読みを置かない（序の頁へ。統括の決め 11-06）"
# 公開デモは白の 1 つだけ
sh = (ROOT / "run-demo.sh").read_text(encoding="utf-8")
assert re.search(r'^LOOKS="tenji"', sh, re.M) and 'LOOKS="tenji zine"' not in sh
print("ok 白の入口の最初の画面は題と えらぶ だけで、黒にだけあった額の絵と 1 行は次の扉に入り、公開デモは白の 1 つだけ")
