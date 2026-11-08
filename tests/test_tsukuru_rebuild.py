"""つくるの頁（玩具の頁 /toy/<印>）の作り直し（本人の言葉 11-08「つくるは読む情報が多すぎて整理する必要を感じる。復元の記録などはすべてもちよるに統合する。
原図をみて、狂歌を読んで、仮説、たとえ、3D をみたあとに型紙の印刷にすすむ。そして作成を 3D の手順の解説に従って行い、その過程も記録、できたらのこすことも
念頭につくり、できたら完成形を記録するために、のこすにいく。」・設計 grove の state/tsukuru-redesign-20261108.md の 9 つの問いに本人の答え「推しのとおり。」）。

見る事:
1. 頭: 原図と狂歌（くずし字を読む の道）と題と作品の札。頭に「これまでの記録」の畳みと、原図の横の作ってみた実物の写真が無い。
   頭の「つくる」は流れの最初の段（立体のある玩具は #kasetsu・無い玩具は仮説の段 #kasetsu-fuda）へ行く道（刷らない）
2. 頭の後の段の順: 組み立てを立体で見る → 仮説 → たとえと、関連する事柄 → 型紙を印刷する → できたら、のこそう（本人の言葉 11-08「つくるは、仮説の前に
   「組み立てを立体で見る」を置く。」）。これまでの復元（#minna）・組み方・作っている途中で困ったら・考えを話す は頁に無い
3. 仮説の段: 見出し「仮説」→ 前提の断り（11-05）→ うつしの輪の図（本人の言葉 11-08「つくるの仮説にある図は、のこすのうつしの輪の図にする。」）→ 札。
   段の見出し（h2）は 仮説 だけ。考えを話す の口は無い（本人の言葉 11-08「つくるの「考えを話す」は無くす。」）
4. 型紙を印刷する（前の 型紙の窓。本人の言葉 11-08「型紙の窓を「型紙を印刷する」からにして、その直下に PDF を開いて印刷するボタンを置く。」）:
   刷る前は見出しの下に紙を作る「つくる」（刷る口は 1 つ）。刷った後は PDF → 型紙（紙の絵と札）→ 型紙の版の歩み（閉じた畳み）→ 口（つくる（手帖へ）・のこす）
5. できたら、のこそう の段に、もちよる のこの玩具の札（/gallery#toy-<印>）への 1 行の道「このおもちゃの作った物を もちよる で見る」。札が無い玩具には出さない
6. 作りながら見る頁の「← 玩具」は型紙の窓（#win）へ行く（前の錨 #tsukuru は外した）
"""
import os
import re
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ.pop("ANTHROPIC_API_KEY", None)

from omochae import hypotheses  # noqa: E402
from web import toy  # noqa: E402
from web.play_server import print_latest  # noqa: E402

TOYS = ("NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R")
STEPS = ["組み立てを立体で見る", "仮説", "たとえと、関連する事柄", "型紙を印刷する", "できたら、のこそう"]


def check(sid, printed):
    page = toy.toy_page(sid)
    hero = re.search(r'<section class="hero">.*?</section>', page, re.S).group(0)
    body = page[page.index("</section>", page.index('<section class="hero">')):]
    where = (sid, "刷った後" if printed else "刷る前")
    # 1
    assert "これまでの記録" not in hero and "fold-sec" not in hero, (where, "頭に これまでの記録 の畳みが残った")
    assert "genga-made" not in hero, (where, "原図の横の作ってみた実物が残った")
    assert re.search(r'<p class="road"><a class="btn" href="#kasetsu">つくる</a></p>', hero), (where, "頭の つくる が最初の段（立体）へ行かない")
    assert "/print" not in hero, (where, "頭の つくる が刷る")
    assert "くずし字を読む" in hero and 'class="label"' in hero
    # 2
    at = [body.index(s) for s in STEPS]
    assert at == sorted(at), (where, "段の順", dict(zip(STEPS, at)))
    for gone in ('id="minna"', "これまでの復元", 'id="kumikata"', "作っている途中で困ったら", 'id="ask"', 'id="hanasu"', "考えを話す"):
        assert gone not in page, (where, gone)
    # 3
    a = page.index('<section class="sec" id="kasetsu-fuda">')
    tatoe = page.index('id="tatoe"')
    fuda = page[a:tatoe]
    marks = [fuda.index(x) for x in ("<h2>仮説</h2>", 'id="premise"', 'id="wa"', 'class="plates"')]
    assert marks == sorted(marks), (where, "仮説の段の中の順", marks)
    assert fuda.count("<h2>") == 1, (where, "仮説の段に h2 が 2 つ")
    # 4
    w = page[page.index('<section class="sec" id="win">'):page.index('id="kiroku"')]
    if printed:
        assert f'href="/toy/{sid}/techo">つくる</a>' in w and f'href="/toy/{sid}/techo/kiroku">のこす</a>' in w and "PDF を開いて印刷する" in w, where
        assert f'action="/toy/{sid}/print' not in w, (where, "刷った後も刷る口が残った")
    else:
        assert re.search(rf'<form method="post" action="/toy/{sid}/print#win"[^>]*>.*?<button class="btn" data-busy>つくる</button></form>', w, re.S), (where, "刷る前の窓に紙を作る口が無い")
    if 'id="ban-ayumi"' in page:
        assert re.search(r'id="ban-ayumi"[^>]*><details class="fold-sec"><summary><h2>型紙の版の歩み</h2></summary>', w), (where, "版の歩みが窓の中の閉じた畳みでない")
        if printed:  # 段の中の順: PDF を開いて印刷する（見出しの直下・本人の言葉 11-08）→ 型紙（紙の絵と札）→ 版の歩み → 口（つくる・のこす）（本人の言葉 469）
            assert (w.index("PDF を開いて印刷する") < w.index('<figure class="sheet">') < w.index('id="ban-ayumi"')
                    < w.index(f'href="/toy/{sid}/techo">つくる</a>')), (where, "PDF → 型紙 → 版の歩み → 口 の順でない")
    # 5（もちよる の札がある時だけ。札の有る無しは もちよる の側の techo_site.toy_place が決める）
    k = page[page.index('id="kiroku"'):]
    place = toy.mochiyoru_place(sid)
    if place:
        assert f'<a href="{place}">このおもちゃの作った物を もちよる で見る</a>' in k, (where, "もちよる への道が無い")
    else:
        assert "このおもちゃの作った物を もちよる で見る" not in page, (where, "札の無い玩具に もちよる への道を出した")
    # 6
    assert 'id="tsukuru"' not in page, (where, "前の錨 #tsukuru が残った")
    return page


for sid in TOYS:
    check(sid, False)
    assert print_latest(sid, hypotheses.sheet_of(sid)["id"]) is not None, (sid, "紙を作れない")
    check(sid, True)
print("ok つくるの頁の作り直し: 頭は原図と狂歌と題・立体 → 仮説（うつしの輪）→ たとえ → 型紙を印刷する → のこそう・復元と組み方と困ったらと考えを話すは無い・窓の中で刷る・もちよるへの 1 行")
