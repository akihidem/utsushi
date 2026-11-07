"""ページを白案に統一する（本人の決定 11-06「ページは白案で統一します。黒案にだけある要素は白案に入れてください」）の床。

見る事: 黒の表紙にだけあった、最初の玩具の額の絵と 1 行が、白の入口の「まずはここから」の 2 枚に字のまま出る（入口は えらぶ。本人のサイト体験レビュー 11-07）／
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
# 白の入口は えらぶ（本人のサイト体験レビュー 11-07 の 4・5）。題の間は題と副題（と表紙の 2 行）だけで、えらぶ の釦は無い。
# 黒の表紙にだけあった額の絵（最初の玩具を額の敷き方で）と 1 行は、前は次の扉に掛けた。扉を外した今は、「まずはここから」の 1 枚目が
# 同じ額の敷き方の最初の玩具で、1 行はその 2 枚の下に出る（本人の決定 11-06「黒案にだけある要素は白案に入れて」を保つ）
body = white.split("</style>")[-1]
hall = body.index('class="tj-hall')
hall_end = body.index("</section>", hall)
inner = body[hall:hall_end]
assert "tj-work" not in inner and "role=\"img\"" not in inner and 'class="road-go"' not in inner, "最初の節に額と えらぶ の釦を入れない"
assert 'class="tj-door"' not in body, "扉の 1 室は外した"
mazu = body[body.index('<section class="tj-mazu"'):body.index("</section>", body.index('<section class="tj-mazu"'))]
assert hall_end < body.index('<section class="tj-mazu"'), "題の間の後"
first = looks.toys()[0]
# 額の絵は、図の写し（out/sources、git の外）がある時だけ /picture/<印> を敷く（looks._bg）。写しの無い木では地の色だけになる
# 1 枚目は最初の玩具の図。絵は中くらいの写しを先に読む img（最初の画面で元の大きい写しを読まない。本人の答え 11-07 の (a)）。
# 写しの無い木では地の色の札になる。敷き方は黒の表紙と同じく綴じの反対側へ寄せる（framed_pos の横の位置）
if (looks.ROOT / "out/sources" / f"{first['sid']}.jpg").exists():
    x = looks.framed_pos(first["sid"]).split()[0]
    assert f'<img src="/picture/{first["sid"]}/mid" alt="{first["toy"]}の図" fetchpriority="high"' in mazu and f"object-position:{x} 50%" in mazu, "1 枚目は最初の玩具の図"
else:
    assert f'role="img" aria-label="{first["toy"]}の図"' in mazu, "写しの無い木では地の色の札に読み上げの名"
assert f"url(/picture/{first['sid']})" not in body and f'src="/picture/{first["sid"]}"' not in body, "最初の画面で元の大きい写しを読まない"
assert f'<p class="meta">{looks.DOOR_LINE}</p>' in mazu, "黒の表紙の 1 行は 2 枚の下"
# 入口の絵は小さい写しだけ（統括の合格の線 11-07: 1 枚 100KB 以下・83 の並びは遅れて読む。本人の答え「言葉だけに見えたのは一番最初の画面、
# iPhone で」の元は、入口の絵の大きい写し 1 枚 750KB を一度に読む形だった）
import re  # noqa: E402
from web import toys  # noqa: E402
urls = re.findall(r'(?:url\(|src="|data-src=")(/picture/[^)"]+)', body)
have = any((looks.ROOT / "out/sources" / f"{t['sid']}.jpg").exists() for t in looks.toys())
assert (urls or not have) and all(re.fullmatch(r"/picture/NDL-[^/]+/(small|mid)", u) for u in urls), [u for u in urls if not u.endswith(("/small", "/mid"))][:3]
grid = body[body.index('<section class="tj-erabu"'):]
assert ' src="/picture/' not in grid and grid.count(' data-src="/picture/') >= (1 if have else 0), "並びは 2 枚の後に読む"
for u in set(urls):
    sid, size = u.split("/")[2:4]
    got = toys.small_picture(sid, size)
    assert got is None or len(got) <= 100_000, (u, len(got))
assert 'id="zn-hokusai"' not in white, "白の入口に北斎漫画の縦読みを置かない（序の頁へ。統括の決め 11-06）"
# 公開デモは白の 1 つだけ
sh = (ROOT / "run-demo.sh").read_text(encoding="utf-8")
assert re.search(r'^LOOKS="tenji"', sh, re.M) and 'LOOKS="tenji zine"' not in sh
print("ok 白の入口は えらぶ で、黒にだけあった額の絵と 1 行は まずはここから の 2 枚に入り、公開デモは白の 1 つだけ")
