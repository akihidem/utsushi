"""用意する物と部品表の、紙の書き方の決まり（制作者の指示 2026-11-05 18:35「ルールで徹底して」）。

紙の書き方は次の 4 つだけ。どれも家や店にある紙と結びつく名前で、g/m² や mm の厚さ・「見込み」の語は使わない。
- コピー用紙くらいの厚さの紙
- 画用紙くらいの厚さの紙
- 画用紙より厚い紙
- 空き箱の厚紙
判断の芯:
- 寸法と質量の計算は、今までどおり雛形の paper_gsm・paper_thickness の数で行い、字だけをこの名前にする。
- 境は、コピー用紙（およそ 64〜80g/m²・0.09mm 前後）と画用紙（およそ 130〜190g/m²・0.15〜0.2mm 前後）の間と、
  画用紙の上で切った読み。重さがあれば重さで、無ければ厚さで選ぶ。どの名前で作れるかは実物でまだ試していない。
- 字をここ 1 か所に置くのは、雛形ごとに別々に書いて 7 通りに散った（そろえる決まりも試験も無かった）ため。
  決まりに合わない書き方は tests/test_paper_words.py が落とす。
"""
import re

COPY = "コピー用紙くらいの厚さの紙"
DRAWING = "画用紙くらいの厚さの紙"
THICK = "画用紙より厚い紙"
BOARD = "空き箱の厚紙"
NAMES = (COPY, DRAWING, THICK, BOARD)

# 紙の行で使ってはいけない書き方（作る人の家の紙と結びつかない・作る側の言葉）
BANNED = re.compile(r"g/m²|見込み|厚さ\s*[0-9.]+\s*mm|厚めの紙|薄い紙|^紙（|^厚紙|菓子箱")


def paper_name(gsm=None, thickness=None):
    """紙の重さ（g/m²）か厚さ（mm）から、4 つの名前のどれかを返す。重さがあれば重さを使う。"""
    if gsm is not None:
        return COPY if gsm < 110 else DRAWING if gsm < 220 else THICK
    if thickness is None:
        raise ValueError("紙の重さか厚さが要る")
    if thickness >= 0.5:
        return BOARD
    return COPY if thickness < 0.12 else DRAWING if thickness < 0.25 else THICK
