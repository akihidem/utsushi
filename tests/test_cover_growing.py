"""表紙の題の下の 2 行（本人の決定 11-06）の床。

見る事: 字は本人が採った案 1 のまま／両方の表紙（白の展示と黒のジン）に 1 つずつ／表紙の節の中で、題の後に置く。
"""
import os
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from web import looks  # noqa: E402

assert looks.GROWING == ("このサイトは、まだ育っている途中です。", "型紙をよくしていくのは、作ってみるあなたです。")
for look, cover, title in (("tenji", 'class="tj-hall"', '<p class="sub">'), ("zine", 'class="zn-cover"', "<h1>うつし</h1>")):
    page = looks.PAGES[look]()
    line = f'<p class="grow">{looks.GROWING[0]}<br>{looks.GROWING[1]}</p>'
    assert page.count(line) == 1, look
    start = page.index(cover)
    end = page.index("</section>", start)
    at = page.index(line)
    assert start < page.index(title, start) < at < end, (look, "表紙の節の中で、題の後")
print("ok 表紙の題の下の 2 行は、両方の表紙に本人が採った字のまま 1 つずつある")
