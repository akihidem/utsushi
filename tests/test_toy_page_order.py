"""玩具の頁（つくる）の節の並び。

前は本人の言葉 11-08（394）「つくるのページ、これまでの復元、仮説、組み立てを立体で見る、たとえと関連する事柄、型紙の順で。考えを話す、作ってる途中で
困ったら、は同じ窓で。」の並びを見ていた（#625）。その後の本人の言葉 11-08（477）「つくるは読む情報が多すぎて整理する必要を感じる。復元の記録などは
すべてもちよるに統合する。原図をみて、狂歌を読んで、仮説、たとえ、3D をみたあとに型紙の印刷にすすむ。…」と設計の 9 つの問いの答え「推しのとおり。」で
替わり（#657）、さらに本人の言葉 11-08「つくるは、仮説の前に「組み立てを立体で見る」を置く。」「つくるの「考えを話す」は無くす。」
「つくるの仮説にある図は、のこすのうつしの輪の図にする。」「型紙の窓を「型紙を印刷する」からにして、その直下に PDF を開いて印刷するボタンを置く。
型紙の窓のところにある仮説・型紙のボタンは要らない。」で替わったので、今の並びを見る（作り直しの細かい線は test_tsukuru_rebuild）。

見る線:
1. 頭の後の段は 組み立てを立体で見る（#kasetsu）→ 仮説（#kasetsu-fuda）→ たとえ（#tatoe）→ 型紙を印刷する（#win）→ できたら、のこそう（#kiroku）の順。
   立体の無い玩具は、立体の段が抜けるだけ（錨 #kasetsu の空の div が頭のすぐ後に残る）
2. 仮説の段は 見出し「仮説」→ 前提の断り → うつしの輪の図（#wa）→ 札。断りが札より前（本人の言葉 11-05）。考えを話す（#hanasu）は無い
3. 型紙の窓の中は 見出し「型紙を印刷する」→ PDF を開いて印刷する → 型紙（紙の絵と札）→ 版の歩み（#ban-ayumi・閉じた畳み）→ つくる → 本人の字 → のこす。
   仮説・型紙の切り替えの札（.tabs）は無い
4. これまでの復元（#minna）・組み方（#kumikata）・困ったら（#tsukuru・#ask）・考えを話す（#hanasu）は頁に無い
5. 刷る前も刷った後も同じ並び
"""
import os
import re
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ.pop("ANTHROPIC_API_KEY", None)

from omochae import hypotheses  # noqa: E402
from web import naoru  # noqa: E402
from web.play_server import print_latest  # noqa: E402
from web.toy import toy_page  # noqa: E402

TOYS = ("NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R")
PLAIN = "NDL-1187053-R0000009-L-2"  # 立体の無い玩具（試作）
STEPS = ("kasetsu", "kasetsu-fuda", "tatoe", "win", "kiroku")

for printed in (False, True):
    for sid in TOYS + (PLAIN,):
        if printed:
            assert print_latest(sid, hypotheses.sheet_of(sid)["id"]) is not None, (sid, "紙を作れない")
        page = toy_page(sid)
        where = (sid, "刷った後" if printed else "刷る前")
        # 1
        at = [page.index(f'id="{x}"') for x in STEPS]
        assert at == sorted(at) and page.index('<section class="hero">') < at[0], (where, dict(zip(STEPS, at)))
        if sid == PLAIN:
            assert '<div id="kasetsu"></div>' in page and "組み立てを立体で見る" not in page, (where, "立体の無い玩具に立体の段が出た")
        else:
            assert re.search(r'<section class="sec" id="kasetsu">(<[^>]+>)*<h2>組み立てを立体で見る</h2>', page), (where, "立体の段が頭のすぐ後に無い")
        # 2
        fuda = page[page.index('id="kasetsu-fuda"'):page.index('id="tatoe"')]
        marks = [fuda.index(x) for x in ("<h2>仮説</h2>", 'id="premise"', 'id="wa"', 'class="plates"')]
        assert marks == sorted(marks), (where, "仮説の段の中の順", marks)
        # 3
        win = page[page.index('id="win"'):page.index('id="kiroku"')]
        assert win.index("<h2>") == win.index("<h2>型紙を印刷する</h2>"), (where, "窓の頭の見出しが 型紙を印刷する でない")
        assert '<div class="tabs">' not in win and "<h2>型紙の窓</h2>" not in page, (where, "窓の切り替えの札か前の見出しが残った")
        if printed:
            # 版の歩みは版のある玩具だけ（試作の玩具には無い）
            inner = [win.index(x) for x in ("<h2>型紙を印刷する</h2>", "PDF を開いて印刷する", '<figure class="sheet">', *(('id="ban-ayumi"',) if sid != PLAIN else ()),
                                            f'href="/toy/{sid}/techo">つくる</a>', naoru.ROUTE_ASK, f'href="/toy/{sid}/techo/kiroku">のこす</a>')]
            assert inner == sorted(inner), (where, "型紙の窓の中の順", inner)
            # 見出しの直下が PDF を開いて印刷する（間に段の字を挟まない）
            assert re.search(r'<h2>型紙を印刷する</h2><div class="print-top"><p><a class="btn" href="[^"]+\.pdf"[^>]*>PDF を開いて印刷する</a>', win), (where, "見出しの直下が PDF でない")
        else:
            # 刷る前は、見出しの直下が紙を刷る つくる（PDF はまだ無い）
            assert re.search(r'<h2>型紙を印刷する</h2><form method="post" action="/toy/[^"]+/print#win"', win) and "PDF を開いて印刷する" not in win, (where, "刷る前の見出しの直下")
        # 4
        for gone in ('id="minna"', 'id="kumikata"', 'id="tsukuru"', 'id="ask"', 'id="hanasu"'):
            assert gone not in page, (where, gone)
print("ok 玩具の頁の節の並び: 立体 → 仮説（断り・うつしの輪・札）→ たとえ → 型紙を印刷する（PDF → 型紙 → 版の歩み → つくる・本人の字・のこす）→ のこそう。"
      "立体の無い玩具は立体が抜ける。復元・組み方・困ったら・考えを話す・窓の切り替えの札は無い")
