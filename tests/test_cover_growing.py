"""表紙の題の下の床（前は本人の決定 11-06 の 2 行。本人のサイトレビュー 11-07 午後の 1 で、説明の頁への道 1 つに替えた）。

本人の言葉（11-07 午後）:「…サイトの目的や AI でやっていることや仕組みについて説明するページを作ってそのリンクを添えた方が良いかも？
そうするなら、トップページの『このサイトは、まだ育っている途中です。型紙をよくしていくのは、作ってみるあなたです。』もいらなそう」。
窓口の決め 132926 の ③④: 表紙の 2 行を外し、副題の下に説明の頁（/about）への道を 1 つ。字は「このサイトについて」。

見る事: 前の 2 行が両方の表紙に無い／道は両方の表紙（白の展示と黒のジン）に 1 つずつ、表紙の節の中で題（白の展示は副題）の後／
大きいボタンにしない（入口の大きいボタンは えらぶ 1 つ。class="go" を付けない）。
"""
import os
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from web import looks  # noqa: E402

assert not hasattr(looks, "GROWING") and looks.ABOUT == "このサイトについて"
# 暗い版（zine）の入口は白と同じ作り（本人の決め 11-08「もう1つ立てる」）なので、表紙の節も同じ tj-hall
for look, cover, title in (("tenji", 'class="tj-hall"', '<p class="sub">'), ("zine", 'class="tj-hall"', '<p class="sub">')):
    page = looks.PAGES[look]()
    assert "まだ育っている途中" not in page and "型紙をよくしていくのは、作ってみるあなたです" not in page, (look, "前の 2 行は外した")
    line = '<p class="about-go"><a href="/about">このサイトについて</a></p>'
    assert page.count(line) == 1, look
    start = page.index(cover)
    end = page.index("</section>", start)
    at = page.index(line)
    assert start < page.index(title, start) < at < end, (look, "表紙の節の中で、題の後")
    assert 'class="go" href="/about"' not in page, (look, "大きいボタンにしない")
print("ok 表紙の題の下は、説明の頁への道 1 つ（このサイトについて）。前の 2 行は無い")
