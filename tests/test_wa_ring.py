"""型紙がよくなっていく輪の図（web.wa）の床。本人の言葉 11-06「サイトにその仕組みがわかりやすくあるといいよね」。

見る事:
1. 輪の字は、頁に既にある字から取った物（新しい言い方を増やさない）。順は 案 → 作る → 工夫を記録に書く → 次の型紙をよくする
2. 玩具の頁の「すぐ作る」の札のすぐ後に 1 つだけ出る（白の展示と黒のジン、必須 2 種と試作）。真ん中から頁の下の「型紙の改善の輪」へ飛べる
3. 真ん中の数は今の型紙の版だけ（人が採った一番新しい版。無ければ版 1）。報告や動いた数は出さない（J-025）
4. 図の札は図の中に収まる（幅 390 の画面で左右の札の端が切れたのを直した）。読み上げの title に輪の順が 1 文で入る
"""
import os
import re
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ.pop("ANTHROPIC_API_KEY", None)

from omochae.marks import PREMISE_PAGE  # noqa: E402
from web import kaizen, toy, wa  # noqa: E402

G, T, PLAIN = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R", "NDL-1187053-R0000009-L-2"

# 1. 字は頁に既にある字から
assert wa.STEPS == ("ためしの案（仮説）", "切って、折って、組む", "どう工夫したかを記録に書く", "次の型紙をよくする")
assert "ためしの案（仮説）" in PREMISE_PAGE and "どう工夫したかを記録に書" in PREMISE_PAGE and "次の型紙をよくする" in PREMISE_PAGE
for label, lines in wa.LINES.items():
    assert "".join(lines) == label, "2 行に分けるのは置き方だけで、字は変えない"

# 2. 置き場: 札のすぐ後に 1 つだけ。真ん中から改善の輪の節へ
for sid in (G, T, PLAIN):
    for look in ("tenji", "zine"):
        page = toy.toy_page(sid, look)
        assert "切って、折って、組みます" in page, "「切って、折って、組む」は「すぐ作る」の頭の文の字"
        assert page.count('id="wa"') == 1, (sid, look)
        at, premise = page.index('id="wa"'), page.index('id="premise"')
        assert premise < at and page.index("</p>", premise) < at < page.index('class="plates"'), "札のすぐ後"
        assert 'href="#kaizen"' in page[at:page.index("</figure>", at)] and 'id="kaizen"' in page, "真ん中から改善の輪の節へ飛べる"

# 3. 真ん中の数は今の型紙の版だけ
assert wa.current_version(G, None) == 1
keep = kaizen.versions
kaizen.versions = lambda sid, hid: [{"version": 2}, {"version": 3}]
try:
    assert wa.current_version(G, None) == 3
    assert "版 3" in toy.toy_page(G, "tenji")
finally:
    kaizen.versions = keep
fig = wa.ring(1)
shown = re.findall(r"<text[^>]*>([^<]*)</text>", fig)
assert shown == [s for label in wa.STEPS for s in wa.LINES.get(label, (label,))] + [wa.NOW, "版 1"], shown
assert not re.search(r"[0-9]", "".join(shown).replace("版 1", "")), "版のほかに数を出さない"

# 4. 札は図の中に収まる。読み上げの title に輪の順
for x, y in wa.SPOTS:
    assert 0 <= x - wa.BOX_W / 2 and x + wa.BOX_W / 2 <= wa.W and 0 <= y - wa.BOX_H / 2 and y + wa.BOX_H / 2 <= wa.H, (x, y)
title = re.search(r"<title[^>]*>([^<]*)</title>", fig).group(1)
assert title == " → ".join((*wa.STEPS, wa.STEPS[0])) and 'role="img"' in fig
print("ok 輪の図は札のすぐ後に 1 つ出て、字は頁の字のまま、真ん中は今の型紙の版")
