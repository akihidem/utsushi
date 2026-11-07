"""場面「エンジンの仕組み」（案）: 型紙を作るエンジン paper to toy の流れを、段の図 3 本で順に見せ、うつしがその一つの具体例である事を言う。

使い方: python -m demo.engine --out <置き場>/engine.mp4 [--sheet <置き場>/engine-sheet.jpg]
exit: 0 = 書き出せた / 4 = 書き出せない（demo.flip.render と同じ）

決めた事と理由:
- 本人の言葉（11-07・統括を通して）「このサービスは学校の理科教育や研究活動や博物館などの教育分野で使われることを想定して始めたけど、
  公開してみんなが使えるようなサービスになるといいなと思ってきた。paper to toy の一つの具体例であるとか、エンジンの仕組みとかは
  デモとサイトで説明した方がいい」。デモの担当の案（grove の state/demo-fix-owner-20261107.md の末）: 場面 14（talk_claude）と入れ替える。
- 字は材料（grove の state/engine-explain-20261107.md）の (1)(4) から作った案で、全部 本人の確かめ待ち。英語は (3) を元にした案（demo.english）。
- 材料の「書かなかった事」の線を守る: 3D で組んで確かめるのは御来迎と首振り虎だけなので、3D の段の題にその 2 つを書く。直しの案を採るのは人
  （「人が採る」の箱）。物理や DNA の紙のモデル・公開の仕組みは、まだ作っていないので描かない。
- 台本には、窓口の決め 120643 で場面 14（talk_claude）と入れ替えて入れた（demo.script の ENGINE_SCENE）。
- 字幕は下の真ん中の帯（words.band。ファイナリストから借りた点 1・2）。かたまりは words.ALL に入れず、ここで持つ（台本の字の表を
  同じ時に直している枝と取り合わないため）。合図の作り方は words.cues_of と同じ（1 秒 5 字・1 かたまり 2 秒以上・頭 0.4 秒と終わり 0.2 秒）。
- 秒: 前の 4 かたまりは読む秒で 21.6 秒になった。本人の決定（11-07・179.3 秒）の 14 秒ほどに入るよう、3 かたまりに縮めた（CHUNKS の注）。
- 図は紙の地に墨の箱と矢印だけ（新しい絵は描かない）。段は字幕のかたまりに合わせて 1 本ずつ現れ、現れた後は動かさない（字のそばに動く物を置かない線）。
  案内役 B は出さない（guide.PLANS に入れない）。
"""
import argparse
import math
import pathlib
import sys

from PIL import Image, ImageDraw

from demo.flip import H, PAPER, SHU, SUMI, W, contact_sheet, ease, fade, render
from demo.words import DISSOLVE, EPS, LEAD, TAIL, band, chunk_alpha, chunk_seconds

NAME = "engine"
# 字幕のかたまり（行の並び）。全部 案。窓口の決め 120530「小学 4 年生向け 5 文と英語 3 文は案のとおり…具体例の文は本人の直した位置づけ
# （みんなが使えるサービスとして作った・うつしは一つの具体例）に直して使う。デモの説明もこれで」の 5 文から、場面の秒（本人の決定 11-07・
# 179.3 秒の引き方で 14 秒ほど。窓口の決め 120643）に入るよう 3 かたまりに縮めた: 1 文目（エンジンが型紙を出す）・5 文目（直すと
# 型紙の版とエンジンの版が上がる。誰の報告から直すかは改善の輪の段の図が見せる）・具体例の 1 文。2・3 文目（刷る前後の確かめと 3D の組み立て）は字幕にせず、段の図（ROWS）が見せる。
# 具体例の 1 文は、窓口の決め 120530 のとおり本人の直した位置づけ（本人の言葉 11-07「これからというよりは、みんなが使えるサービスとして作った」）と
# 1 つにした。位置づけの 1 文（窓口の決め 120643）もこの文が言う（締めの場面に別に置くと、合計の秒 179.5 に入らなかった）
CHUNKS = (
    ("型紙は、paper to toy という", "エンジンが作ります。"),
    ("直すたびに、", "型紙とエンジンの版が上がります。"),
    ("うつしはその一つの具体例で、", "みんなが使えるサービスとして作りました。"),
)


def _cues():
    """words.cues_of と同じ作り: page は場面の頭、c0, c1… は各かたまりの現れる時刻。"""
    out, t = {"page": (0.0, LEAD)}, LEAD
    for i, lines in enumerate(CHUNKS):
        out[f"c{i}"] = (round(t, 3), round(t + DISSOLVE, 3))
        t += chunk_seconds(lines)
    return out


CUES = _cues()
DURATION = math.ceil((LEAD + sum(chunk_seconds(c) for c in CHUNKS) + TAIL) * 10 - EPS) / 10

# 段の図（材料の (2) の 3 本）。(題, [(箱の字, 箱の下の小さな字 or None)…])。全部 案
ROWS = (
    ("型紙の流れ", (("入力（寸法・出典）", None), ("部品を並べる", None), ("刷る前の検査", None), ("描く", None), ("刷った後の検査", None), ("型紙", None))),
    ("3D の流れ（御来迎・首振り虎）", (("型紙の部品", None), ("3D で折る", None), ("組み立てる", None), ("3D 組み立て検品", None), ("作り方の 3D", None))),
    ("改善の輪", (("作った人の報告・感想", None), ("直しの案", None), ("人が採る", None), ("版を刻む", "型紙の版・エンジンの版"), ("次の型紙", None))),
)
EXAMPLE = "うつし ＝ paper to toy の一つの具体例"   # 最後のかたまりで出す札（字幕ではない）。案
# 段が現れる時刻: 型紙の流れと 3D の流れは 1 つ目のかたまりの中（字幕はエンジンが型紙を作る事を言い、段が中の確かめを見せる）、
# 改善の輪は 2 つ目のかたまり（版が上がる）の頭
ROW_AT = (CUES["c0"][0] + 0.6, CUES["c0"][0] + 2.4, CUES["c1"][0])
STEP = 0.18      # 段の中で、箱が 1 つずつ現れる間（秒）
APPEAR = 0.5     # 1 つの箱が現れきる秒

# 置き場（px）。下の帯（2 行の日本語と英語でおよそ上の端 800）より上に 3 段を入れる。段の題は段の上に置く
# （前は左に置いたが、「3D の流れ（御来迎・首振り虎）」が箱に重なった。11-07 に止めの絵で見た）
TITLE_X, BOX_X0 = 100, 100
BOX_W, BOX_H, GAP = 250, 128, 44
ROW_Y = (52, 282, 512)       # 段の題の上の端。箱は BOX_DY 下から
BOX_DY = 80        # 段の題の英語の行の下（前は 58 で、英語の行が箱の上の端に重なった）
TITLE_SIZE, BOX_SIZE, SUB_SIZE = 30, 24, 18
EXAMPLE_Y, EXAMPLE_SIZE = 782, 32


def drawn():
    """この場面が描く日本語の字（英語字幕の試験が、どれにも英語がある事を見る）。"""
    out = ["".join(lines) for lines in CHUNKS] + [EXAMPLE]
    for title, boxes in ROWS:
        out.append(title)
        for label, sub in boxes:
            out.append(label)
            if sub:
                out.append(sub)
    return out


def _fit(label, size):
    """箱の中に入る大きさ（px）。長い字（作った人の報告・感想）は、箱の左右に 12px ずつ空く所まで小さくする。"""
    from PIL import ImageFont

    from demo.flip import SERIF

    while size > 18 and ImageFont.truetype(SERIF, size).getlength(label) > BOX_W - 24:
        size -= 1
    return size


def _arrow(d, x0, x1, y, color, width=3):
    d.line((x0, y, x1 - 12, y), fill=color, width=width)
    d.polygon([(x1, y), (x1 - 14, y - 7), (x1 - 14, y + 7)], fill=color)


class Engine:
    """エンジンの仕組みの場面。frame(t) は時刻だけで決まる（前のコマに依らない）。"""

    def __init__(self):
        self.cues, self.duration = CUES, DURATION

    def _row(self, d, k, t):
        from demo.english import text_en

        title, boxes = ROWS[k]
        start = ROW_AT[k]
        v_title = ease((t - start) / APPEAR)
        if v_title <= 0:
            return
        accent = SHU if k == 2 else SUMI
        text_en(d, (TITLE_X, ROW_Y[k]), title, TITLE_SIZE, fade(accent, v_title), True, "la")
        y = ROW_Y[k] + BOX_DY
        for i, (label, sub) in enumerate(boxes):
            v = ease((t - start - (i + 1) * STEP) / APPEAR)
            if v <= 0:
                continue
            x = BOX_X0 + i * (BOX_W + GAP)
            d.rounded_rectangle((x, y, x + BOX_W, y + BOX_H), 10, outline=fade(SUMI, 0.75 * v), width=2, fill=fade((252, 248, 238), v))
            size = _fit(label, BOX_SIZE)
            if sub:
                top = text_en(d, (x + BOX_W // 2, y + 10), label, size, fade(SUMI, v), False, "ma")
                text_en(d, (x + BOX_W // 2, top + 26), sub, SUB_SIZE, fade(SHU, 0.9 * v), False, "ma")
            else:
                text_en(d, (x + BOX_W // 2, y + 30), label, size, fade(SUMI, v), False, "ma")
            if i:
                _arrow(d, x - GAP + 6, x - 6, y + BOX_H // 2, fade(accent, 0.8 * v))
        # 改善の輪は、最後の箱（次の型紙）から最初の箱へ戻る線で輪にする
        if k == 2:
            v = ease((t - start - (len(boxes) + 1) * STEP) / APPEAR)
            if v > 0:
                x_last = BOX_X0 + (len(boxes) - 1) * (BOX_W + GAP) + BOX_W // 2
                x_first = BOX_X0 + BOX_W // 2
                yb = y + BOX_H + 26
                color = fade(SHU, 0.8 * v)
                d.line((x_last, y + BOX_H, x_last, yb), fill=color, width=3)
                d.line((x_last, yb, x_first, yb), fill=color, width=3)
                d.line((x_first, yb, x_first, y + BOX_H + 12), fill=color, width=3)
                d.polygon([(x_first, y + BOX_H + 2), (x_first - 7, y + BOX_H + 16), (x_first + 7, y + BOX_H + 16)], fill=color)

    def frame(self, t):
        from demo.english import text_en

        img = Image.new("RGB", (W, H), PAPER)
        d = ImageDraw.Draw(img)
        for k in range(len(ROWS)):
            self._row(d, k, t)
        last = len(CHUNKS) - 1
        v = ease((t - CUES[f"c{last}"][0]) / APPEAR)
        if v > 0:
            text_en(d, (W // 2, EXAMPLE_Y), EXAMPLE, EXAMPLE_SIZE, fade(SHU, v), True, "ma")
        n = len(CHUNKS)
        for i, lines in enumerate(CHUNKS):
            a = chunk_alpha(CUES, n, i, t)
            if a > 0:
                img = band(img, lines, a)
        return img


SHEET_TIMES = tuple(round(DURATION * k, 2) for k in (0.08, 0.2, 0.32, 0.45, 0.58, 0.7, 0.82, 0.9, 0.98))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True, help="mp4 の置き場（repo の外）")
    ap.add_argument("--sheet", help="要のコマの一覧の画像")
    a = ap.parse_args(argv)
    scene = Engine()
    if a.sheet:
        pathlib.Path(a.sheet).parent.mkdir(parents=True, exist_ok=True)
        contact_sheet(scene, a.sheet, times=SHEET_TIMES)
    return render(scene, pathlib.Path(a.out))


if __name__ == "__main__":
    sys.exit(main())
