"""輪の図 2 つ（型紙の窓の web.wa と、学びの輪の web.loop_figure）で、英語の字どうしが重ならない（統括の割り振り 11-08・
重なりの見回り grove の state/no-overlap-20261108.md の 1 と 2）。

なぜ: 英語は日本語より長く、札の幅（日本語の字の数で決まる）と真ん中の丸に入らず、字どうしが重なった（8 つの大きさ全部）。
英語の頁（html lang="en"）の時だけ、図の字の大きさを CSS で替えた（日本語の図は替えない）。

見る事（字の幅は紙の型紙と同じ字の測り omochae.textfit で出す。この機械の字が無い時は 4 だけ見る）:
1. 型紙の窓の図: 英語の札の字が札（幅 132）に、真ん中の 2 行が丸（直径 88）に収まる
2. 学びの輪の図: 英語の札の字が札に、誰がするかの名が札の右の端より内に、真ん中の「Current template」が左右の札の間に、
   真ん中の小さな 1 行が図の幅に収まり、下げた先が左右の札の下・下の札の上
3. 日本語の字の大きさと置き場は前のまま（英語の時だけの決まりは html[lang=en] の中だけ）
4. 英語の頁で、英語の時だけの決まりが図と一緒に頁に入る
"""
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
from web import i18n, loop_figure, wa  # noqa: E402

PAD = 4  # 札の縁から字までのゆとり（片側）


def en(text):
    """訳の表の英語（英字だけの字はそのまま）。"""
    return text if not i18n.CJK.search(text) else i18n.lookup(text)


def size_of(style, sel, default):
    """英語の時の字の大きさ。英語の時だけの決まりが無い時（直す前の作り）は、日本語の字の大きさのまま英語が出る"""
    m = re.search(re.escape(sel) + r"\{font-size:([\d.]+)px", style)
    return float(m.group(1)) if m else default


try:
    textfit._font()
    have_font = True
except ToolMissing:
    have_font = False

svg = loop_figure.drawn()
EN_STYLE = getattr(loop_figure, "EN_STYLE", "")
texts = re.findall(r'<text (?:class="(lf-[swnc])" )?x="([\d.]+)" y="([\d.]+)"[^>]*>([^<]*)</text>', svg)
if have_font:
    # 1. 型紙の窓の図
    fs_t, fs_now, fs_v = (size_of(wa.STYLE, f"html[lang=en] .wa .{c}", d) for c, d in (("wa-t", 14), ("wa-now", 12), ("wa-v", 26)))
    for step in wa.STEPS:
        for line in wa.LINES.get(step, (step,)):
            w = textfit.text_width(en(line), fs_t)
            assert w <= wa.BOX_W - 2 * PAD, ("型紙の窓の札に入らない", en(line), round(w, 1))
    # 真ん中の 2 行は、字の置かれる高さでの丸の幅（弦）に収まり、左右の札にも届かない。dy は丸の真ん中から字の真ん中までの縦の差
    # （「Current template」は y = CY-8 の字の下の線で、字の真ん中は約 CY-12。「Version N」は y = CY+22 で、字の真ん中は約 CY+16）
    import math
    gap = (wa.SPOTS[1][0] - wa.BOX_W / 2) - (wa.SPOTS[3][0] + wa.BOX_W / 2)
    for word, fs, dy in ((en(wa.NOW), fs_now, 12), (en(wa.VERSION.format(n=14)).replace("{0}", "14"), fs_v, 16)):
        w = textfit.text_width(word, fs)
        chord = 2 * math.sqrt(44 ** 2 - dy ** 2)
        assert w <= chord - 2 and w <= gap - 2 * PAD, ("型紙の窓の真ん中の丸に入らない", word, round(w, 1), round(chord, 1))
    # 2. 学びの輪の図
    st = EN_STYLE
    fs_s, fs_w, fs_n, fs_c = (size_of(st, f"html[lang=en] .loop-ring .{c}", d) for c, d in (("lf-s", 20), ("lf-w", 15), ("lf-n", 20), ("lf-c", 13)))
    m = re.search(r"\.lf-c\{[^}]*translateY\(([\d.]+)px\)", st)
    drop = float(m.group(1)) if m else 0.0
    rects = [tuple(float(v) for v in m) for m in re.findall(r'<rect x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)" rx="10"', svg)]
    assert len(rects) == 4

    def rect_at(x, y):
        return next(r for r in rects if r[0] <= x <= r[0] + r[2] and r[1] <= y <= r[1] + r[3])

    W = float(re.search(r'viewBox="0 0 ([\d.]+) ', svg).group(1))
    for cls, x, y, word in texts:
        x, y, word = float(x), float(y), en(word)
        if not cls:  # 直す前の作り（印が無い）: 札の字・名・真ん中を、字の言葉で見分ける
            cls = "lf-w" if word in ("Person", "Claude") else "lf-n" if word == en(wa.NOW) else "lf-c" if word == en(loop_figure.CENTER) else "lf-s"
        if cls == "lf-s":
            r = rect_at(x, y)
            w = textfit.text_width(word, fs_s)
            assert w <= r[2] - 2 * PAD, ("学びの輪の札に入らない", word, round(w, 1), r[2])
        elif cls == "lf-w":  # 名は絵の右から左寄せで書く（x は字の左の端）
            r = rect_at(x, y)
            # 名の置き場は日本語の字の幅で決まっているので、英語の名は札の右の端の近くまで伸びる。端から 2 以上内（字の大きさの 2 割ほど）
            assert x + textfit.text_width(word, fs_w) <= r[0] + r[2] - 2, ("誰がするかの名が札からはみ出す", word)
        elif cls == "lf-n":
            left = max(r[0] + r[2] for r in rects if r[0] + r[2] < x)
            right = min(r[0] for r in rects if r[0] > x)
            assert textfit.text_width(word, fs_n) <= (right - left) - 2 * PAD, ("真ん中の字が左右の札に届く", word)
        else:  # lf-c: 下げた先が左右の札の下・下の札の上。横は図の幅に収まる
            sides = [r for r in rects if r[1] < y < r[1] + r[3] + 40 and abs((r[0] + r[2] / 2) - W / 2) > 50]
            bottom = max(rects, key=lambda r: r[1])
            assert all(y + drop - fs_c > r[1] + r[3] for r in sides) and y + drop < bottom[1], ("真ん中の小さな 1 行の置き場", y + drop)
            assert textfit.text_width(word, fs_c) <= W - 2 * PAD, ("真ん中の小さな 1 行が図に入らない", word)

# 3. 日本語の図の字の大きさは前のまま。英語の決まりは html[lang=en] の中だけ
assert ".wa .wa-t{fill:var(--fg);font-size:14px" in wa.STYLE and "font-size:12px" in wa.STYLE and ".wa .wa-v{fill:var(--accent);font-size:26px}" in wa.STYLE
assert all(rule.startswith("html[lang=en] ") for rule in re.findall(r"[^{}]+\{[^}]*\}", loop_figure.EN_STYLE)), loop_figure.EN_STYLE
assert (loop_figure.STEP_FS, loop_figure.WHO_FS) == (20, 15) and f'font-size="{loop_figure.STEP_FS}"' in svg
assert all(c for c, *_ in texts) and len(texts) == len(re.findall(r"<text ", svg)), "学びの輪の図の字は、どれも英語の時の決まりの印（class）を持つ"

# 4. 英語の頁に、英語の時だけの決まりが図と一緒に入る
page = i18n.page_en(f'<html lang="ja"><body>{loop_figure.svg()}<style>{wa.STYLE}</style>{wa.ring(14)}</body></html>')
assert '<html lang="en"' in page and "html[lang=en] .loop-ring .lf-s" in page and "html[lang=en] .wa .wa-t" in page
note = "" if have_font else "。この機械に字が無いので、字の幅は見ていない"
print(f"ok 輪の図 2 つの英語の字が札と丸と札の間に収まり、日本語の図は前のまま{note}")
