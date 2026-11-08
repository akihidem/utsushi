"""輪の図 2 つ（型紙の窓の web.wa と、学びの輪の web.loop_figure）で、英語の字どうしが重ならない（統括の割り振り 11-08・
重なりの見回り grove の state/no-overlap-20261108.md の 1 と 2）。

なぜ: 英語は日本語より長く、札の幅（日本語の字の数で決まる）と真ん中の丸に入らず、字どうしが重なった（8 つの大きさ全部）。
英語の図を別の SVG にし（en_fig.TOGGLE で、英語の頁でだけ見せる）、字は訳の表の英語・大きさは SVG の中の値（wa.EN_FS・loop_figure._en_boxes）で持つ。
前は英語の頁の CSS で字を小さくしたが、字の大きさの床（tests/test_tap_size.py の 12px）に当たって main が落ちた（11-08）。

見る事（字の幅は紙の型紙と同じ字の測り omochae.textfit で出す。この機械の字が無い時は 3 と 4 だけ見る）:
1. 型紙の窓の英語の図: 札の字が札（幅 132）に、真ん中の 2 行が字の高さでの丸の幅と左右の札の間に収まる
2. 学びの輪の英語の図: 札の字が札に、誰がするかの名が札の右の端より内に、真ん中の「Current template」が左右の札の間に、
   真ん中の小さな 1 行が図の幅に収まり、置き場が左右の札の下・下の札の上
3. 日本語の図は前のまま（字の大きさ・日本語の字）。英語の図の字は英語（日本語の字が残らない）
4. 図の HTML に、字の大きさの CSS（font-size の px）が無い（字の大きさの床に当たらない）。2 つの図は言葉で片方だけを見せる
5. 英語の図の字が、幅 390 の画面に出る大きさ（viewBox の中の字の大きさ × 幅 390 での図の幅 ÷ viewBox の幅）で下限以上
   （統括の決め 11-08: 字 10px・誰がするかの名と真ん中の小さな 1 行 9px）。前の直しは SVG の中の値にしただけで、画面では 5〜8px だった
"""
import math
import os
import pathlib
import re
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from omochae import textfit  # noqa: E402
from omochae.model import ToolMissing  # noqa: E402
from web import en_fig, i18n, loop_figure, wa  # noqa: E402

PAD = 4  # 札の縁から字までのゆとり（片側）
_TAG = re.compile(r'<text (?:class="([\w-]+)" )?x="([\d.]+)" y="([\d.]+)"([^>]*)>([^<]*)</text>')


class TEXT:
    """図の字の (class, x, y, 字の大きさ, 字)。字の大きさは要素の font-size（無ければ空）。"""
    @staticmethod
    def findall(svg):
        out = []
        for cls, x, y, rest, word in _TAG.findall(svg):
            m = re.search(r'font-size="([\d.]+)"', rest)
            out.append((cls, x, y, m.group(1) if m else "", word))
        return out


def svgs(html):
    """(日本語の図, 英語の図)。"""
    ja = re.search(r'<svg class="[^"]*ja-fig[^"]*".*?</svg>', html, re.S)
    en = re.search(r'<svg class="[^"]*en-fig[^"]*".*?</svg>', html, re.S)
    assert ja and en, "日本語の図と英語の図の 2 つ"
    return ja.group(0), en.group(0)


try:
    textfit._font()
    have_font = True
except ToolMissing:
    have_font = False

ring = wa.ring(14)
wa_ja, wa_en = svgs(ring)
fig = loop_figure.svg()
lf_ja, lf_en = svgs(fig)

# 4. 字の大きさの CSS が無い・言葉で片方だけを見せる
for name, html in (("型紙の窓", ring), ("学びの輪", fig)):
    small = [float(x) for x in re.findall(r"font-size:\s*([\d.]+)px", html) if float(x) < 12]
    assert not small, (name, "字の大きさの床（12px）に当たる CSS", small)
    assert "html[lang=en] figure svg.en-fig{display:block}" in html and "figure svg.en-fig{display:none}" in html, name
# 3. 日本語の図は前のまま・英語の図の字は英語
assert lf_ja == loop_figure.drawn() and 'font-size="20"' in lf_ja and (loop_figure.STEP_FS, loop_figure.WHO_FS) == (20, 15)
assert ".wa .wa-t{fill:var(--fg);font-size:14px" in wa.STYLE and ".wa .wa-v{fill:var(--accent);font-size:26px}" in wa.STYLE
for name, en in (("型紙の窓", wa_en), ("学びの輪", lf_en)):
    shown = [t[4] for t in TEXT.findall(en)]
    assert shown and not [t for t in shown if i18n.CJK.search(t)], (name, "英語の図に日本語の字が残る", shown)

# 5. 画面に出る大きさの下限（幅 390）。型紙の窓の真ん中の「Current template」は真ん中の小さな字（9px）、版の数と駅の字は 10px
FLOOR = {"wa-te": en_fig.MIN_TEXT, "wa-ve": en_fig.MIN_TEXT, "wa-nowe": en_fig.MIN_SMALL,
         "lf-s": en_fig.MIN_TEXT, "lf-n": en_fig.MIN_TEXT, "lf-w": en_fig.MIN_SMALL, "lf-c": en_fig.MIN_SMALL}
small = []
for name, fig, en in (("型紙の窓", "wa", wa_en), ("学びの輪", "loop", lf_en)):
    view_w = float(re.search(r'viewBox="0 0 ([\d.]+) ', en).group(1))
    for cls, _x, _y, fs, word in TEXT.findall(en):
        shown_px = float(fs) * en_fig.FIG_390[fig] / view_w
        if shown_px < FLOOR[cls] - 1e-6:
            small.append((name, cls, word, round(shown_px, 2), FLOOR[cls]))
assert not small, ("英語の図の字が幅 390 で下限より小さい", small)

if have_font:
    # 1. 型紙の窓の英語の図
    for cls, x, y, fs, word in TEXT.findall(wa_en):
        x, y, fs = float(x), float(y), float(fs)
        w = textfit.text_width(word, fs)
        if cls == "wa-te":
            assert w <= wa.BOX_W - 2 * PAD, ("型紙の窓の札に入らない", word, round(w, 1))
        else:  # 真ん中の 2 行（字の真ん中は、字の下の線から字の大きさの 4 割ほど上）
            dy = abs(y - fs * 0.4 - wa.CY)
            chord = 2 * math.sqrt(44 ** 2 - dy ** 2)
            gap = (wa.SPOTS[1][0] - wa.BOX_W / 2) - (wa.SPOTS[3][0] + wa.BOX_W / 2)
            assert w <= chord - 2 and w <= gap - 2 * PAD, ("型紙の窓の真ん中の丸に入らない", word, round(w, 1), round(chord, 1))
    # 2. 学びの輪の英語の図
    rects = [tuple(float(v) for v in m) for m in re.findall(r'<rect x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)" rx="10"', lf_en)]
    assert len(rects) == 4
    W = float(re.search(r'viewBox="0 0 ([\d.]+) ', lf_en).group(1))

    def rect_at(x, y):
        return next(r for r in rects if r[0] <= x <= r[0] + r[2] and r[1] <= y <= r[1] + r[3])

    for cls, x, y, fs, word in TEXT.findall(lf_en):
        x, y, fs = float(x), float(y), float(fs)
        w = textfit.text_width(word, fs)
        if cls == "lf-s":
            r = rect_at(x, y)
            assert w <= r[2] - 2 * PAD, ("学びの輪の札に入らない", word, round(w, 1), r[2])
        elif cls == "lf-w":  # 名は絵の右から左寄せで書く（x は字の左の端）。置き場は日本語の字の幅で決まるので、札の右の端から 2 以上内
            r = rect_at(x, y)
            assert x + w <= r[0] + r[2] - 2, ("誰がするかの名が札からはみ出す", word)
        elif cls == "lf-n":
            left = max(r[0] + r[2] for r in rects if r[0] + r[2] < x)
            right = min(r[0] for r in rects if r[0] > x)
            assert w <= (right - left) - 2 * PAD, ("真ん中の字が左右の札に届く", word)
        else:  # lf-c: 左右の札の下・下の札の上。横は図の幅に収まる
            sides = [r for r in rects if abs((r[0] + r[2] / 2) - W / 2) > 50]
            bottom = max(rects, key=lambda r: r[1])
            assert all(y - fs > r[1] + r[3] for r in sides) and y < bottom[1], ("真ん中の小さな 1 行の置き場", y)
            assert w <= W - 2 * PAD, ("真ん中の小さな 1 行が図に入らない", word)
note = "" if have_font else "。この機械に字が無いので、字の幅は見ていない"
print(f"ok 輪の図 2 つの英語の図は字が札と丸と札の間に収まり、幅 390 で字 10px・名と小さな 1 行 9px 以上で、字の大きさの CSS を持たない。日本語の図は前のまま{note}")
