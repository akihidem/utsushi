"""玩具の頁（つくる）の節の並び。

前は本人の言葉 11-08（394）「つくるのページ、これまでの復元、仮説、組み立てを立体で見る、たとえと関連する事柄、型紙の順で。考えを話す、作ってる途中で
困ったら、は同じ窓で。」の並びを見ていた（#625）。その後の本人の言葉 11-08（477）「つくるは読む情報が多すぎて整理する必要を感じる。復元の記録などは
すべてもちよるに統合する。原図をみて、狂歌を読んで、仮説、たとえ、3D をみたあとに型紙の印刷にすすむ。…」と設計の 9 つの問いの答え「推しのとおり。」で
替わったので、今の並びを見る（作り直しの細かい線は test_tsukuru_rebuild）。

見る線:
1. 頭の後の段は 仮説（#kasetsu-fuda）→ たとえ（#tatoe）→ 組み立てを立体で見る（#kasetsu）→ 型紙の窓（#win）→ できたら、のこそう（#kiroku）の順
2. 仮説の段は 見出し「仮説」→ 前提の断り → 輪の図 → 札 → 考えを話す（#hanasu・段の中）。断りが札より前（本人の言葉 11-05）・輪の図が断りと札の間は前のまま
3. 型紙の窓の中は 型紙（紙の絵と札）→ 版の歩み（#ban-ayumi・閉じた畳み）→ 窓の口（印刷・つくる・のこす）（本人の言葉 469・統括の読み 11-08）
4. これまでの復元（#minna）・組み方（#kumikata）・困ったら（#tsukuru・#ask）は頁に無い
5. 刷る前も刷った後も同じ並び
"""
import os
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ.pop("ANTHROPIC_API_KEY", None)

from omochae import hypotheses  # noqa: E402
from web.play_server import print_latest  # noqa: E402
from web.toy import toy_page  # noqa: E402

TOYS = ("NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R")
STEPS = ("kasetsu-fuda", "tatoe", "kasetsu", "win", "kiroku")

for printed in (False, True):
    for sid in TOYS:
        if printed:
            assert print_latest(sid, hypotheses.sheet_of(sid)["id"]) is not None, (sid, "紙を作れない")
        page = toy_page(sid)
        where = (sid, "刷った後" if printed else "刷る前")
        # 1
        at = [page.index(f'id="{x}"') for x in STEPS]
        assert at == sorted(at) and page.index('<section class="hero">') < at[0], (where, dict(zip(STEPS, at)))
        # 2
        fuda = page[page.index('id="kasetsu-fuda"'):page.index('id="tatoe"')]
        marks = [fuda.index(x) for x in ("<h2>仮説</h2>", 'id="premise"', 'id="wa"', 'class="plates"', 'id="hanasu"')]
        assert marks == sorted(marks), (where, "仮説の段の中の順", marks)
        # 3
        win = page[page.index('id="win"'):page.index('id="kiroku"')]
        if printed:
            inner = [win.index(x) for x in ('<figure class="sheet">', 'id="ban-ayumi"', "PDF を開いて印刷する", f'href="/toy/{sid}/techo/kiroku">のこす</a>')]
            assert inner == sorted(inner), (where, "型紙の窓の中の順", inner)
        # 4
        for gone in ('id="minna"', 'id="kumikata"', 'id="tsukuru"', 'id="ask"'):
            assert gone not in page, (where, gone)
print("ok 玩具の頁の節の並び: 仮説（断り・輪の図・札・考えを話す）→ たとえ → 立体 → 型紙の窓（型紙 → 版の歩み → 口）→ のこそう。復元・組み方・困ったらは無い")
