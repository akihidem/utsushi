"""輪の図の英語の並べ方の部品（型紙の窓の web.wa と、学びの輪の web.loop_figure が使う）。

統括の決め（11-08）: 英語の図の字は、幅 390 の画面に出た大きさで 10px 以上（誰がするかの名と真ん中の小さな 1 行は 9px 以上）。
作りは (a)「英語用の並べ方を別に持つ・日本語の図は替えない・試験に実の大きさの下限を足す」。前の直し（#680）は英語の時だけ字を小さくして
重なりを消したが、幅 390 で名が約 6px になり読めなかった（別の目の測り）。

判断の芯:
- 日本語の図はそのまま。英語の図は別の SVG で並べ、頁の言葉（html の lang）で片方だけを見せる（TOGGLE）。字の訳を頁の出口で替える
  仕組み（web.i18n）は、1 つの字の箱を 1 つの英語に替えるだけで、英語の長さに合わせて折れないため
- 英語の図の字は、訳の表の英語を描く時に引いて、札の幅で折る。日本語の 1 つの段が 2 行に分かれている物（「次の型紙を」「よくする」）は、
  英語をつないでから折り直す。新しい英語の字は作らない（訳の表に無い字は日本語のまま出る。表に足すのは英語の全頁の試験が止める）
- 字の幅は紙の型紙と同じ字の測り（omochae.textfit）。この機械に字が無い時は 1 字を字の大きさの 0.55 とみる（英字の平均より少し広い）
- 字の大きさは、幅 390 の画面での図の幅（FIG_390）と viewBox の幅から決める。図は頁の幅に合わせて縮むので、viewBox の中の字の大きさ ×
  （図の幅 ÷ viewBox の幅）が画面に出る大きさ
"""
import math

from omochae import textfit
from omochae.model import ToolMissing

from . import i18n

# 言葉ごとに片方の図だけを見せる。英語の図は英語の頁（html lang="en"）でだけ出す。やさしい日本語の頁は日本語の図（lang は ja のまま）
# 図の部品の見た目の決まり（.wa svg{display:block} など）より強くするため、figure の中の svg に絞る（同じ強さだと後に書いた方が勝ち、頁の CSS の
# 並びで日本語の頁にも英語の図が出うる）
TOGGLE = ("figure svg.ja-fig{display:block}figure svg.en-fig{display:none}"
          "html[lang=en] figure svg.en-fig{display:block}html[lang=en] figure svg.ja-fig{display:none}")
# 幅 390 の画面での図の幅（px）。11-08 に頭なしの Chromium で測った（型紙の窓は玩具の頁、学びの輪は のこす の頁が狭い方・よむ は 348）
FIG_390 = {"wa": 358, "loop": 311}
MIN_TEXT, MIN_SMALL = 10, 9  # 画面に出る大きさの下限（統括の決め 11-08）


def en(text):
    """訳の表の英語。英字だけの字はそのまま。表に無い時は日本語のまま（頁の英語の全頁の試験が、表に無い字を止める）。"""
    if not i18n.CJK.search(text):
        return text
    got = i18n.lookup(text)
    return got if got and got != i18n.KEEP else text


def phrase(lines):
    """日本語の 1 つの段（2 行に分けた物も）を、英語の 1 つの句にする。"""
    return " ".join(en(t) for t in lines)


def width(s, size):
    try:
        return textfit.text_width(s, size)
    except ToolMissing:
        return len(s) * size * 0.55


def wrap(text, size, max_w):
    """語の切れ目で折る。1 語が幅を超える時は、その語だけで 1 行にする（はみ出しは試験が見つける）。"""
    lines, cur = [], ""
    for word in text.split():
        cand = f"{cur} {word}" if cur else word
        if cur and width(cand, size) > max_w:
            lines.append(cur)
            cur = word
        else:
            cur = cand
    if cur:
        lines.append(cur)
    return lines


def fit(lines, size, max_w):
    """日本語の段の分け方の英語（訳の表は行ごと）が全部の行で幅に入るなら、その分け方のまま（訳の表の切れ目は意味の切れ目）。
    入らない行があれば、つないで語の切れ目で折り直す（「Make the next template」は札に入らない）。"""
    own = [en(t) for t in lines]
    return own if all(width(t, size) <= max_w for t in own) else wrap(" ".join(own), size, max_w)


def user_size(px, fig, view_w):
    """画面に px で出したい時の、viewBox の中の字の大きさ（幅 390 の画面での図の幅から）。"""
    return px * view_w / FIG_390[fig]


def floor_size(px, fig, view_w):
    """画面に px 以上で出る、viewBox の中の字の大きさ（0.1 の位へ切り上げ。切り捨てると画面で下限をわずかに割る）。"""
    return math.ceil(user_size(px, fig, view_w) * 10) / 10
