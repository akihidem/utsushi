"""型紙の窓の「つくる」のすぐ下に大きな「のこす」を置く（本人の答え 11-08: のこすへの道は案 B「印刷 → つくる の直後に大きな のこす」。
本人の言葉 476「…つくるからのこすの誘導が全体的に弱いので、のこすに行かない可能性が高い。」・477「…できたらのこすことも念頭につくり…」）。

見る事:
1. 紙を刷った後の型紙の窓に、「PDF を開いて印刷する」→「つくる」（手帖へ）→「のこす」（記録の頁へ・枠の釦）の順で並ぶ
2. 「のこす」のすぐ下に、今の 1 行「つくるところを、写真と声でのこせます。」→ 本人の字「どう工夫したかあとで教えてください。写真や動画でもいいです。」→ 意義の 1 行 の順
3. 「のこす」の釦は「つくる」と同じ大きさ（高さ 64px・幅 10em 以上）で、押せる所は 44px 以上
4. 刷る前（窓に紙が無い時）は のこす の釦を出さない（作る前に のこす を押す人を作らない）
5. 本人の字は英語とやさしい日本語の表にある
"""
import json
import os
import pathlib
import re
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ.pop("ANTHROPIC_API_KEY", None)

from omochae import hypotheses  # noqa: E402
from web import naoru, toy  # noqa: E402
from web.play_server import print_latest  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
ASK = "どう工夫したかあとで教えてください。写真や動画でもいいです。"
TOYS = ("NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R")


def win(page):
    a = page.index('<section class="sec" id="win">')
    return page[a:page.index("</section>", a)]


for sid in TOYS:
    before = win(toy.toy_page(sid))
    # 4
    assert f'href="/toy/{sid}/techo/kiroku"' not in before and "nokosu-go" not in before, (sid, "刷る前に のこす の釦が出た")
    assert print_latest(sid, hypotheses.sheet_of(sid)["id"]) is not None, (sid, "紙を作れない")
    w = win(toy.toy_page(sid))
    # 1
    pdf = w.index("PDF を開いて印刷する")
    make = w.index(f'<a class="btn" href="/toy/{sid}/techo">つくる</a>')
    go = re.search(rf'<p class="nokosu-go"><a class="btn quiet" href="/toy/{sid}/techo/kiroku">のこす</a></p>', w)
    assert go and pdf < make < go.start(), (sid, "印刷 → つくる → のこす の順でない")
    # 2
    lines = [w.index(t, go.end()) for t in (naoru.ROUTE_MAKING, ASK, naoru.purpose())]
    assert lines == sorted(lines), (sid, "のこす の下の行の順が違う")
    assert w.count(ASK) == 1 and w.count(naoru.ROUTE_MAKING) == 1, (sid, "同じ行を 2 度出した")
# 3
css = toy.FOLD_STYLE
assert re.search(r"\.nokosu-go \.btn\{[^}]*min-height:64px[^}]*min-width:10em", css), "のこす の釦が つくる と同じ大きさでない"
# 5
en = json.loads((ROOT / "data/i18n/en.json").read_text(encoding="utf-8"))["strings"]
assert en.get(ASK) == "Tell us later what you changed. Photos or videos are fine too.", en.get(ASK)
easy = {}
for f in sorted((ROOT / "data/i18n/yasashii.d").glob("*.json")):
    easy.update(json.loads(f.read_text(encoding="utf-8"))["strings"])
assert ASK in easy and "｜工夫《くふう》" in easy[ASK], "やさしい日本語の表に本人の字が無い"
print("ok 型紙の窓: 印刷 → つくる → のこす（大きな枠の釦）・下に のこせる・本人の字・意義の 3 行・刷る前は出さない・英語とやさしい日本語の表にある")
