"""入口の題の間（tj-hall）の縦の組み（本人の決め 11-07 夜「縦の組みに戻す」。11-06 夜の main 5d1358dd の最初の画面）。

見る線:
1. 題字「うつし」・英字・副題は縦書き（TENJI の .tj-hall の形）で、横書きで短くする上書き（#hall.tj-hall の horizontal-tb）が無い
2. 幅 480 以下の形（英字は題の上に横・副題は下に縦）は TENJI のまま
3. 字は 1 字も替えない（英字・題・副題 3 行・このサイトについて）。まずはここから の 2 枚と帯は今のまま
   題字の下の読み（looks.YOMI）は字の形に残るが、出すのは英語の頁だけ（本人の言葉 11-08「英語は英語モードの時のみ横書きで、他はかえない」。tests/test_entrance_yomi.py が測る）
"""
import os
import re
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from web import looks  # noqa: E402

page = looks.tenji()
css = "".join(re.findall(r"<style>(.*?)</style>", page, re.S))
# 1. 縦書き・横書きの上書きが無い
assert ".tj-hall h1{grid-column:2;writing-mode:vertical-rl" in css and ".tj-hall .sub{grid-column:3;justify-self:start;writing-mode:vertical-rl" in css
assert ".tj-hall .en{grid-column:1;justify-self:end;margin-right:5vw;font-size:12px;letter-spacing:.35em;color:#7a7164;text-transform:uppercase;writing-mode:vertical-rl}" in css
assert not re.search(r"#hall\.tj-hall[^{]*\{[^}]*horizontal-tb", css), "題の間を横書きにする上書きが残った"
assert not re.search(r"#hall\.tj-hall\{[^}]*min-height:auto", css), "題の間の高さを詰める上書きが残った"
# 2. 幅 480 以下の形
assert ".tj-hall .en{writing-mode:horizontal-tb}" in css
# 3. 字
hall = re.search(r'<section class="tj-hall" id="hall">.*?</section>', page, re.S).group(0)
# 副題の 3 行目は本人の答え 11-08「紙でよみがえらせる。」（字は looks.SUB の 1 か所）
assert looks.SUB == ("江都二色より", "うしなわれた玩具の動きを", "紙でよみがえらせる")
assert f'<p class="en">Lost toys of Edo · 1773</p><h1><span class="kana" lang="ja">うつし</span><span class="yomi">{looks.YOMI}</span></h1><p class="sub">江都二色より<br>うしなわれた玩具の動きを<br>紙でよみがえらせる</p>' in hall
assert "このサイトについて" in hall and "<h2>まずはここから</h2>" in page and page.index('id="hall"') < page.index("<h2>まずはここから</h2>")
print("ok 入口の題の間は縦の組み（11-06 夜の形）。字と下の札は今のまま")
