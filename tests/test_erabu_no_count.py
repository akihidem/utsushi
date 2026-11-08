"""入口の えらぶ の畳みの札から、棚ごとの数の字を外す（本人の言葉 11-08「最初の「（うごく 38・かざる 45）」は消す。」）。

見る事:
1. 入口（白と暗い版）の畳みの札は「2 回目からは、{全部の数} のおもちゃから えらぶ」で、棚ごとの数（うごく N・かざる N）の字が頁のどこにも無い
2. 棚の名（うごく・かざる）は畳みの中の見出しに残る（字はそのまま）
3. 英語の表に、棚ごとの数の付いた札の鍵が無く、数を外した札の鍵がある。英語で開いた入口にも棚ごとの数の字が無い
"""
import json
import os
import pathlib
import re
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from web import genre, i18n, looks  # noqa: E402
from web.play_server import sources  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
ALL = list(sources())
n = len(ALL)
COUNT = re.compile(r"(うごく|かざる)\s*\d+|（うごく|Move \d+|Display \d+")

# 1・2
for page in (looks.tenji(), looks.yoru()):
    fold = page[page.index('<details class="tj-fold" id="erabu">'):page.index("</details>", page.index('id="erabu"'))]
    assert f"<summary>2 回目からは、{n} のおもちゃから えらぶ</summary>" in fold, "札は全部の数だけ"
    assert not COUNT.search(re.sub(r"<[^>]+>", " ", page)), ("棚ごとの数の字が頁に残った", COUNT.search(re.sub(r"<[^>]+>", " ", page)))
    for big, _ in genre.groups(ALL):
        assert f"<h3>{big}</h3>" in fold, (big, "棚の名が無い")
assert looks.fold_label(ALL) == f"2 回目からは、{n} のおもちゃから えらぶ"

# 3
en = json.loads((ROOT / "data/i18n/en.json").read_text(encoding="utf-8"))["strings"]
assert not [k for k in en if "回目からは" in k and "うごく" in k], "棚ごとの数の付いた札の鍵が英語の表に残った"
assert en.get("{0} 回目からは、{1} のおもちゃから えらぶ") == "From your second time on, choose from {1} toys"
html = i18n.page_en(looks.tenji())
assert "From your second time on, choose from" in html and not COUNT.search(re.sub(r"<[^>]+>", " ", html)), "英語の入口に棚ごとの数の字が残った"
print(f"ok 入口の えらぶ の札は全部の数だけ（{n}）・棚ごとの数の字は無い・棚の名は残る・英語の表も同じ")
