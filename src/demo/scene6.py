"""場面 6: 作った人の言葉で、次の版が変わる（本人の所見 → v7 と今の紙の差）。

使い方: python -m demo.scene6 --out <repo の外の場所>/scene6.mp4 [--sheet 要のコマの一覧.jpg] [--cache DIR]
exit: 0 = 書き出せた / 4 = 型紙が刷れない・pdftoppm か ffmpeg が無い（このリポの検査の決まりに合わせる）。

決めた事と理由:
- 本人の所見は docs/process/trials/README.md の文をそのまま引く（言い換えると「作った人の言葉」でなくなる）。
  床で、引いた文が README に一字一句ある事を見る。
- 本人の決定（11-05）「哲学よりの動画にして」で、台帳のつながりと工作の手帖の画面を外した。機能の説明と数を減らし、紙の差だけを見せるため。
- 古い紙は作り直さない。11-04 の試行に渡した v7 の PDF（docs/process/trials/sheets/goraigo-v7、git にある）を
  そのまま映す。今の生成器で v7 は刷れないので、刷れない版を作った振りをしない。v8・v9 は紙を出さず、変えた事の字だけにする。
- 今の紙は repo の生成器（compose → render.write_all）で撮る時に刷る。版の札は slider_fan.SHEET_SET から読む
  （字で書くと、刷り直した時に動画だけ古くなる）。差の朱の枠も、同じ配置（layout）の部品の形から引く。
- 扇の開き方・動き方は描かない（F9）。型紙は平らなまま映し、矢印も付けない。
- 仮説 A と C を並べるのは、本人の所見がこの 2 つについてだったから。順位ではない（J-025）。
- 顔と声は入れない（J-022）。
- frame(t) は時刻だけから 1 コマを描く純関数（flip.py と同じ）。合図は CUES の 1 か所だけを読む。
"""
import argparse
import pathlib
import shutil
import subprocess
import sys

from PIL import Image, ImageDraw

from demo.flip import H, PAPER, ROOT, SHU, SUMI, W, contact_sheet, ease, fade, render, text
from omochae.templates.slider_fan import SHEET_SET

DURATION = 21.0

# 本人の所見（docs/process/trials/README.md の表の文を一字一句そのまま。床で照らす）
QUOTES = (
    "仮説Aは、くり抜く側面の穴を切るのが大変で、下から切り取ることになった",
    "仮説Aにある土台が仮説Cにもあると、作りやすい",
)
QUOTE_FROM = "本人の所見（11-04）"
TRIALS_README = ROOT / "docs/process/trials/README.md"
SHEETS_README = ROOT / "docs/process/trials/sheets/README.md"

# 11-04 の試行に渡した紙。git にある PDF をそのまま映す（作り直さない）。
OLD_DIR = ROOT / "docs/process/trials/sheets/goraigo-v7"
OLD_SET = OLD_DIR.name
OLD_PDF = "goraigo_{hyp}_v7.pdf"

# 紙の差の朱の札。部品の形から枠を引く（下の change_regions）。
LABEL_GROOVE, LABEL_BASE, LABEL_COLOR = "下からの切り込み", "土台", "色の境で折る"
SHOWN_HYPS = ("H-A", "H-C")

CAPTION = ("作った人の言葉で、", "次の版が変わる。")

# 合図の表。絵の動きも字幕もここだけを読む。曲を付ける時は拍に合わせてこの時刻を直す。
CUES = {
    "quote1": (0.0, 0.8),        # 1 つ目の所見
    "quote2": (2.0, 2.8),        # 2 つ目の所見
    "quotes_out": (5.6, 6.2),
    "pair_a": (6.2, 6.9),        # 仮説 A の紙: v7 と今
    "boxes_a": (7.2, 8.2),       # 差の朱の枠
    "pair_a_out": (10.4, 10.9),
    "pair_c": (10.9, 11.6),      # 仮説 C の紙: v7 と今
    "boxes_c": (11.9, 12.9),
    "pair_c_out": (15.1, 15.6),
    "closing": (15.8, 17.2),     # 締めの字幕（21 秒まで止めて読ませる）
}

# 置き場（px）。紙は高さ 720px。左に v7、右に今の紙、間の帯に朱の札を置く。
SHEET_H, SHEET_Y = 720, 210
OLD_X, NEW_X = 120, 940
SHEET_DPI = 150


def phase(t, cue):
    a, b = CUES[cue]
    return ease((t - a) / (b - a))


def span(t, cin, cout):
    return phase(t, cin) * (1 - phase(t, cout))


# ---- 素材を集める（生成器とブラウザに触るのはここだけ。Scene は渡された絵だけを描く） ----

def _raster(pdf, dpi, stem):
    subprocess.run(["pdftoppm", "-png", "-r", str(dpi), "-singlefile", str(pdf), str(stem)], check=True, capture_output=True)
    return Image.open(str(stem) + ".png").convert("RGB")


def current_layouts():
    """今の生成器の型紙の配置を、並べる仮説ごとに返す。場面 4 と同じ作り（版 1 の寸法、同じ題）にする。"""
    from demo import scene4

    recs = scene4.load_records()
    source = scene4.source_record(recs)
    out = {}
    for h in scene4.hypothesis_sheets(recs):
        if h["id"] in SHOWN_HYPS:
            layout, failures = scene4.template_layout(h, source)
            out[h["id"]] = (h, layout, failures)
    return out, source


def _part_box(q):
    xs = [q.x + x for x, _ in q.outline]
    ys = [q.y + y for _, y in q.outline]
    return (min(xs), min(ys), max(xs), max(ys))


def change_regions(layout):
    """v7 から変えた所の枠（mm）を、今の配置の部品の形から引く。[(札, (x0, y0, x1, y1)), ...]

    - 下からの切り込み: 外筒の外形の、外枠の上に無い頂点（下の端から入る溝の奥）から、外筒の下の端まで
    - 土台: 名前が「土台」の部品（仮説 C に足した）
    - 色の境で折る: 折り線を刷らない部品（hide_folds、外筒と扇）
    数字で書かず形から引くのは、寸法を直した時に枠だけが古い所を指すのを防ぐため。
    """
    out = []
    for q in layout["parts"]:
        x0, y0, x1, y1 = _part_box(q)
        if q.hide_folds:
            out.append((LABEL_COLOR, (x0, y0, x1, y1)))
        if q.name == "土台":
            out.append((LABEL_BASE, (x0, y0, x1, y1)))
        if q.key == "tube":
            inner = [(q.x + x, q.y + y) for x, y in q.outline if x0 < q.x + x < x1 and y0 < q.y + y < y1]
            if inner:
                out.append((LABEL_GROOVE, (min(p[0] for p in inner) - 3, min(p[1] for p in inner) - 3,
                                           max(p[0] for p in inner) + 3, y1 + 2)))
    return out


def build_sheets(cache):
    """仮説 A・C の紙を、v7（git にある PDF）と今（生成器で刷る）の 2 枚ずつ。刷った後の検査も通す。"""
    from omochae.marks import check_image_count, check_pdf
    from omochae.render import write_all

    if not shutil.which("pdftoppm"):
        print("検査できない: pdftoppm が無い", file=sys.stderr)
        return None
    layouts, source = current_layouts()
    outdir = cache / "templates"
    pairs = []
    for hyp in SHOWN_HYPS:
        h, layout, failures = layouts[hyp]
        if not failures:
            pdf = write_all(layout, outdir / hyp)
            failures = check_pdf(pdf, source) + check_image_count(pdf)
        if failures:
            for f in failures:
                print(f.line(), file=sys.stderr)
            print(f"検査できない: 型紙 {hyp} が検査に落ちた", file=sys.stderr)
            return None
        old_pdf = OLD_DIR / OLD_PDF.format(hyp=hyp)
        if not old_pdf.exists():
            print(f"検査できない: v7 の紙が無い（{old_pdf}）", file=sys.stderr)
            return None
        pairs.append({"hyp": hyp, "letter": h["letter"],
                      "old": _raster(old_pdf, SHEET_DPI, outdir / f"{hyp}_old"),
                      "new": _raster(pdf, SHEET_DPI, outdir / f"{hyp}_new"),
                      "regions": change_regions(layout), "page_mm": (layout["page"].w, layout["page"].h)})
    return pairs


def _blend_in(img, layer, xy, a):
    """layer を a の濃さで紙の上に置く（前のコマに依らず、今の img の上だけで混ぜる）。"""
    x, y = xy
    region = img.crop((x, y, x + layer.width, y + layer.height))
    img.paste(Image.blend(region, layer, a), (x, y))


class Scene:
    def __init__(self, pairs):
        self.duration = DURATION
        self.new_label = SHEET_SET
        self.tag = f"{OLD_SET} → {SHEET_SET}"
        self.pairs = []
        for p in pairs:
            pw, ph = p["page_mm"]
            k = SHEET_H / ph   # mm → px。今の紙の絵と朱の枠を同じ倍率で置き、枠が紙の部品に重なるようにする
            size = (round(pw * k), SHEET_H)
            self.pairs.append({**p, "k": k, "old": p["old"].resize(size, Image.LANCZOS),
                               "new": p["new"].resize(size, Image.LANCZOS)})

    # 拍ごとの絵

    def _quotes(self, img, draw, t):
        a = 1 - phase(t, "quotes_out")
        for i, (q, cue) in enumerate(zip(QUOTES, ("quote1", "quote2"))):
            u = phase(t, cue) * a
            if u <= 0:
                continue
            y = 380 + i * 230
            draw.rectangle((180, y - 6, 188, y + 120), fill=fade(SHU, u))
            # 長い所見は最後の読点で 2 行に割る（1 行だと 1920px に入らない大きさで読ませたい）
            head, _, tail = q.rpartition("、")
            lines = (f"「{head}、", f"{tail}」") if tail else (f"「{q}」",)
            for j, s in enumerate(lines):
                text(draw, (220, y + j * 62), s, 48, fade(SUMI, u), True)
        if a > 0 and phase(t, "quote1") > 0:
            u = phase(t, "quote1") * a
            text(draw, (80, 60), QUOTE_FROM, 54, fade(SUMI, u), True)
            text(draw, (80, 132), "11-04 に成人 5 人が作って試した後の言葉（原文のまま）", 32, fade(SUMI, u))
            text(draw, (220, 860), "記録 R-0001（仮説 A）・R-0002（仮説 C）。見た事はどちらも「わからない」", 30,
                 fade(SUMI, 0.8 * phase(t, "quote2") * a))

    def _pair(self, img, draw, t, p, cin, cbox, cout):
        u = span(t, cin, cout)
        if u <= 0:
            return
        old, new = p["old"], p["new"]
        _blend_in(img, old, (OLD_X, SHEET_Y), u)
        _blend_in(img, new, (NEW_X, SHEET_Y), u)
        for x, im in ((OLD_X, old), (NEW_X, new)):
            draw.rectangle((x - 1, SHEET_Y - 1, x + im.width, SHEET_Y + im.height), outline=fade(SUMI, 0.35 * u))
        text(draw, (OLD_X, SHEET_Y + SHEET_H + 14), f"{OLD_SET}（11-04 の試行に渡した紙）", 28, fade(SUMI, u), True)
        text(draw, (NEW_X, SHEET_Y + SHEET_H + 14), f"{self.new_label}（今の生成器で刷った）", 28, fade(SHU, u), True)
        text(draw, (80, 60), f"仮説 {p['letter']} の紙", 54, fade(SUMI, u), True)
        text(draw, (80, 132), "同じ仮説の紙を、試行の前と今で並べた。紙は平らなまま", 32, fade(SUMI, u))
        b = phase(t, cbox) * u
        if b <= 0:
            return
        k = p["k"]
        last = {"left": -1e9, "right": -1e9}
        boxes = [(label, (NEW_X + x0 * k, SHEET_Y + y0 * k, NEW_X + x1 * k, SHEET_Y + y1 * k), (x0 + x1) / 2)
                 for label, (x0, y0, x1, y1) in p["regions"]]
        for label, box, _ in boxes:
            draw.rectangle(box, outline=fade(SHU, b), width=4)
        # 札は紙の外に出す。左の部品（外筒・土台）は 2 枚の間の帯へ、右の部品（扇）は右の余白へ。
        # 札の高さは枠の真ん中に合わせ、引き出し線を水平にする。札どうしが重なる時だけ下へずらす。
        for label, box, cx in sorted(boxes, key=lambda r: (r[1][1] + r[1][3]) / 2):
            side = "left" if cx < p["page_mm"][0] / 2 else "right"
            ly = max((box[1] + box[3]) / 2, last[side] + 70)
            last[side] = ly
            if side == "left":
                lx, anchor = NEW_X - 24, "rm"
                draw.line((lx + 8, ly, box[0], ly), fill=fade(SHU, b), width=2)
            else:
                lx, anchor = NEW_X + new.width + 30, "lm"
                draw.line((box[2], ly, lx - 8, ly), fill=fade(SHU, b), width=2)
            text(draw, (lx, ly), label, 34, fade(SHU, b), True, anchor)

    def frame(self, t):
        """時刻 t（秒）の 1 コマ。前のコマに依らない。"""
        img = Image.new("RGB", (W, H), PAPER)
        draw = ImageDraw.Draw(img)
        self._quotes(img, draw, t)
        for p, cues in zip(self.pairs, (("pair_a", "boxes_a", "pair_a_out"), ("pair_c", "boxes_c", "pair_c_out"))):
            self._pair(img, draw, t, p, *cues)
        # 札（右上）: 版の移り。紙の段からずっと出す。
        lab = phase(t, "pair_a") * (1 - phase(t, "closing"))
        if lab > 0:
            text(draw, (W - 80, 64), self.tag, 36, fade(SHU, lab), True, "ra")
        c = phase(t, "closing")
        if c > 0:
            veil = Image.new("RGBA", (W, H), PAPER + (round(235 * c),))
            img.paste(veil, (0, 0), veil)
            draw = ImageDraw.Draw(img)
            text(draw, (W // 2, 440), CAPTION[0], 58, fade(SUMI, c), True, "ma")
            text(draw, (W // 2, 530), CAPTION[1], 58, fade(SUMI, c), True, "ma")
        text(draw, (80, H - 50), self.credit(t), 22, fade(SUMI, 0.7))
        return img

    def credit(self, t):
        """隅の札は、いま映している物の出所に合わせる。"""
        if t < CUES["quotes_out"][1]:
            return "出所: docs/process/trials/README.md（本人の所見）"
        return (f"左: git に残した {OLD_SET} の PDF（docs/process/trials/sheets）　右: 今の生成器（slider_fan）が刷った PDF。"
                "朱の枠は変えた所")


SHEET_TIMES = (1.5, 4.5, 6.8, 8.6, 10.2, 11.4, 13.0, 15.0, 16.0, 18.0, 20.5)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True, help="mp4 の置き場（repo の外）")
    ap.add_argument("--sheet", help="要のコマの一覧の画像")
    ap.add_argument("--cache", default=str(ROOT / "out/demo/cache"))
    a = ap.parse_args(argv)
    cache = pathlib.Path(a.cache) / "scene6"
    try:
        pairs = build_sheets(cache)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        print(f"検査できない: 素材が作れない（{e}）", file=sys.stderr)
        return 4
    if not pairs:
        return 4
    scene = Scene(pairs)
    if a.sheet:
        contact_sheet(scene, a.sheet, SHEET_TIMES)
    return render(scene, pathlib.Path(a.out))


if __name__ == "__main__":
    sys.exit(main())
