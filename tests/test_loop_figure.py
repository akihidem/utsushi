"""説明の頁の学びの輪の図（二つの輪を手書きの風合いで重ねる・窓口の決め 155253）の試験。

見る事:
1. 図の字は、本人が採った文（案 1・11-07「案 1 の字でよい」）の言葉だけ（どの字も ADOPTED の中にそのままある）
2. 2 つの形（a・b）のどちらも、どの字も 1 回ずつ text の要素に出る（英語の頁の訳の表が字を替えられる形）
3. 読み上げには ADOPTED の全文
4. 開くたびに同じ絵（揺れは決まった種）。既定は b（UX の担当の推し・本人の確かめ待ち）
5. 画像のファイルを読まない（その場で描く SVG）。外の部品も読まない
6. 図の字は全部、英語の頁の訳の表にある
"""
import re

from web import loop_figure as f

ADOPTED = ("作って、確かめて、ふり返って、次を考える。この経験から学ぶ輪（経験学習の輪）は、ワークショップでは、進め役（ファシリテーター）といっしょに一周だけ回ります。"
           "うつしがあると、その後も一人で回り続けられます。のこした記録が、次に作る時の入り口になります。進め役の役目は、型紙と記録の形の中に残っています。")
assert f.ADOPTED == ADOPTED, "本人が採った文は一字も替えない"
for key, word in f.WORDS.items():
    assert word in ADOPTED, ("図の字は採った文の言葉だけ", key, word)
for v in ("a", "b"):
    s = f.svg(v)
    texts = re.findall(r"<text[^>]*>([^<]*)</text>", s)
    assert sorted(texts) == sorted(f.WORDS.values()), (v, texts)
    assert f'aria-label="{ADOPTED}"' in s and 'role="img"' in s
    assert s == f.svg(v), "開くたびに同じ絵"
    assert not re.search(r"<image|href=|src=|url\(", s), "画像や外の物を読まない"
assert f.svg() == f.svg("b"), "既定は b"
assert f.svg("a") != f.svg("b")
# ---- 6 英語の頁: 図の字は全部、訳の表にある（全頁の英語 #538・表に無い字は test_en_all が止める。読み上げの全文は説明の頁の文と同じ字で、その表の行は説明の頁の担当が持つ）
from web import i18n  # noqa: E402
for word in f.WORDS.values():
    assert i18n.lookup(word), ("図の字の英語が訳の表に無い", word)
print("ok 学びの輪の図: 採った文の言葉だけで、a と b の 2 つの形。読み上げは全文・同じ絵・画像を読まない・図の字は全部英語の表にある")
