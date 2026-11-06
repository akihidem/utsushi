"""場面 4: 江戸の仕組みの絵（北斎漫画 三編の遠近の線・八編の糸車）から、型紙の線と刷った紙へ。

使い方: python -m demo.scene4 --out <repo の外の場所>/scene4.mp4 [--sheet 要のコマの一覧.jpg] [--cache DIR] [--tests "53/53"]
exit: 0 = 書き出せた / 4 = 画像が取れない・型紙が刷れない・ffmpeg か pdftoppm が無い（このリポの検査の決まりに合わせる）。

決めた事と理由:
- 北斎の絵は描き直さず、所蔵の画像を切り出すだけ（場面 1 と同じ）。切り出しの枠は scene4_sources.json に置く。
- 型紙は動画のために描き直さず、repo の生成器（compose → render.write_all → pdftoppm）で撮る時に刷る。
  動画の紙と、家で刷る紙が同じ物である事が、この場面の言いたい事だから。折り線の動きも同じ配置（layout）から引く。
- 扇の開き方・動き方は見せない（紙で確かめる前に答えを見せない。J-013）。型紙は平らな紙のまま映し、矢印も動きも付けない。
- 刷って映すのは型紙だけ。手順の紙は刷らず、映さない（本人の決まり「刷るのは型紙だけ」11-06 の当てはめ。窓口の決定 11-07）。
  家で刷る紙が型紙だけになったので、動画だけが手順の紙を見せると「家で刷る紙と同じ物」の筋が崩れる。
  題と隅の札の字は、本人の確かめが来るまで今のまま（字の直しは別の段）。
- 見せる紙はたたき台の 1 組だけ（型紙は玩具に 1 枚。本人の決定 11-05 17:26、J-032）。組を並べる段とその字は外した。
  字は書き換えず、足してもいない（#332）。順位を付けない（J-025）。
- 組の版（SHEET_SET）は slider_fan.py から読む。文字で書き込むと、組を刷り直した時に動画だけ古くなる。
  試験の本数は撮る日の ./run.sh で数えて --tests で渡す。渡さない時は数を出さない（古い数を出さないため）。
- frame(t) は時刻だけから 1 コマを描く純関数（flip.py と同じ）。合図は CUES の 1 か所だけを読む。
"""
import argparse
import json
import math
import pathlib
import shutil
import subprocess
import sys

from PIL import Image, ImageDraw

from demo.flip import FPS, H, PAPER, ROOT, SHU, SUMI, W, contact_sheet, ease, fade, fetch_image, ink_layer, render, text
from omochae.templates.slider_fan import SHEET_SET

SOURCES = pathlib.Path(__file__).with_name("scene4_sources.json")
DURATION = 30.0
TESTS_DEFAULT = "試験 ./run.sh（撮る日に数える）"
WHITE = (255, 255, 255)

# 合図の表。絵の動きも字幕もここだけを読む。曲を付ける時は拍に合わせてこの時刻を直す。
CUES = {
    "persp_in": (0.0, 1.5),      # 三編の遠近の線が現れる
    "wheel_in": (5.5, 7.0),      # 三編が消え、八編の糸車が現れる
    "edo_aside": (11.5, 12.7),   # 糸車が右へ退いて薄くなり、左に白い紙が置かれる
    "cuts": (12.7, 14.7),        # 型紙の切る線（墨）を引く
    "folds": (14.7, 17.7),       # 型紙の折る線（朱）を引く
    "printed": (17.7, 19.2),     # 刷った PDF が線の下に現れる。糸車は消える
    "folds_out": (19.4, 20.6),   # 朱の折り線が退き、題が刷った紙の題に替わる（前は手順の紙が右に現れた）
    "labels": (20.6, 21.6),      # 刷った組の版と試験の札
    "closing": (25.6, 27.4),     # 締めの字幕（30 秒まで止めて読ませる）
}

# 置き場（px）。型紙は左に高さ 780px。上の題の 2 行と、下の出所の札の間に収める（場面 1 の試し見で決めた余白）。
SHEET_BOX = (120, 200, 780)        # x, y, 高さ
PERSP_H, PERSP_Y, PERSP_GAP = 600, 220, 40
WHEEL_H, WHEEL_ASIDE_H = 760, 560
SHEET_DPI = 150                    # 780px に縮めて字が潰れない程度。動画のためだけで、刷る紙には関わらない


def phase(t, cue):
    a, b = CUES[cue]
    return ease((t - a) / (b - a))


# ---- 素材を集める（網と生成器に触るのはここだけ。Scene は渡された絵だけを描く） ----

def load_records():
    return json.loads(SOURCES.read_text(encoding="utf-8"))


def fetch_page(cache, page_id, rec):
    """頁の画像を IIIF から取る（cache に残す）。取れない時は None。"""
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / f"{page_id}.jpg"
    try:
        fetch_image(f'{rec["iiif"]}/full/full/0/default.jpg', path)  # 確かめてから置く
    except OSError as e:
        print(f"検査できない: 頁の画像が取れない（{page_id}: {e}）", file=sys.stderr)
        return None
    return Image.open(path).convert("L")


def crop_pct(img, box_pct):
    x, y, w, h = box_pct
    return img.crop((round(x / 100 * img.width), round(y / 100 * img.height),
                     round((x + w) / 100 * img.width), round((y + h) / 100 * img.height)))


def edo_crops(pages, recs):
    """{"v3-R0000022/left": 灰色の絵, ...}。頁の画像の大きさが変わっても、割合なので同じ所が切れる。"""
    return {f"{pid}/{c['id']}": crop_pct(pages[pid], c["box_pct"])
            for pid, rec in recs["pages"].items() for c in rec["crops"]}


def hypothesis_sheets(recs):
    """並べた仮説ごとに (記号, 寸法, 型紙の題)。題は hypotheses.print_sheet の版 1 と同じ作り。場面 6 もこの形を借りる。

    print_sheet をそのまま呼ばないのは、折り線を引くための配置（layout）が要るから。配置と PDF を同じ compose の 1 回から作れば、
    動画の朱の線と刷った紙の線が必ず重なる。
    """
    from omochae.hypotheses import letter, load
    from omochae.loop import version_params

    data = load(recs["template"]["source_id"])
    out = []
    for h in data["hypotheses"]:
        params, _ = version_params(recs["template"]["source_id"], h["id"], 1)
        name = f"仮説 {letter(h)}「{h['name']}」"
        out.append({"id": h["id"], "letter": letter(h), "params": params,
                    "title": f"{data['toy']} 型紙 {name}版 1"})
    return out


def source_record(recs):
    return json.loads((ROOT / "data/sources" / f'{recs["template"]["source_id"]}.json').read_text(encoding="utf-8"))


def template_layout(hs, source):
    """型紙の配置。検査に落ちた配置は映さない（落ちた紙を「家で刷れる紙」と言えないため）。"""
    from omochae.compose import compose
    _, layout, failures = compose("slider_fan", hs["params"], source, title=hs["title"])
    return layout, failures


def template_segments(layout):
    """型紙の線を (種類, (x1, y1), (x2, y2)) の mm で返す。種類は cut / valley / mountain。

    色の境で折る部品（hide_folds）は紙に折り線を刷らないが、折る所であるのは同じなので、朱の線では見せる。
    """
    segs = []
    for q in layout["parts"]:
        pts = [(q.x + x, q.y + y) for x, y in q.outline]
        segs += [("cut", pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts))]
        for x, y, w, h in q.cuts:
            c = [(q.x + x, q.y + y), (q.x + x + w, q.y + y), (q.x + x + w, q.y + y + h), (q.x + x, q.y + y + h)]
            segs += [("cut", c[i], c[(i + 1) % 4]) for i in range(4)]
    folds = []
    for q in layout["parts"]:
        for kind, lines in (("valley", q.valley), ("mountain", q.mountain)):
            folds += [(kind, (q.x + x1, q.y + y1), (q.x + x2, q.y + y2)) for (x1, y1), (x2, y2) in lines]
    # 折る線は上から下へ順に引く。部品の順だと、扇の 28 本の後に筒の線が飛んで出て、目が追えない。
    folds.sort(key=lambda s: (round(min(s[1][1], s[2][1]), 1), min(s[1][0], s[2][0])))
    return segs + folds


def _raster(pdf, dpi):
    stem = pdf.with_suffix("")
    subprocess.run(["pdftoppm", "-png", "-r", str(dpi), "-singlefile", str(pdf), str(stem) + f"_{dpi}"],
                   check=True, capture_output=True)
    return Image.open(str(stem) + f"_{dpi}.png").convert("RGB")


def build_template(cache, recs):
    """型紙を刷って、映す絵にする。刷った後の検査（印の読み直し・貼った絵が無い事）も通す。手順の紙は刷らない。"""
    from omochae.marks import check_image_count, check_pdf
    from omochae.render import write_all

    if not shutil.which("pdftoppm"):
        print("検査できない: pdftoppm が無い", file=sys.stderr)
        return None
    source = source_record(recs)
    outdir = cache / "templates"
    hs = hypothesis_sheets(recs)
    example = next(h for h in hs if h["id"] == recs["template"]["example_hypothesis"])
    layout, failures = template_layout(example, source)
    if not failures:
        pdf = write_all(layout, outdir / f"{example['id']}")
        failures = check_pdf(pdf, source) + check_image_count(pdf)
    if failures:
        for f in failures:
            print(f.line(), file=sys.stderr)
        print(f"検査できない: 型紙 {example['id']} が検査に落ちた", file=sys.stderr)
        return None
    out = {"sheet": _raster(pdf, SHEET_DPI), "segs": template_segments(layout), "page_mm": (layout["page"].w, layout["page"].h), "pdf": pdf}
    out["example_letter"] = example["letter"]
    return out


# ---- 描く ----

def _scaled(img, h):
    return img.resize((max(1, round(img.width * h / img.height)), round(h)), Image.LANCZOS)


def _with_alpha(layer, a):
    out = layer.copy()
    out.putalpha(out.getchannel("A").point(lambda v: round(v * a)))
    return out


def _dashed(draw, p, q, pattern, fill, width):
    """PIL に破線が無いので、模様の長さを足しながら引く。模様は谷と山で変え、刷った紙の凡例と同じ読み方にする。"""
    (x1, y1), (x2, y2) = p, q
    length = math.hypot(x2 - x1, y2 - y1)
    if length == 0:
        return
    ux, uy = (x2 - x1) / length, (y2 - y1) / length
    s, i = 0.0, 0
    while s < length:
        e = min(length, s + pattern[i % len(pattern)])
        if i % 2 == 0:
            draw.line((x1 + ux * s, y1 + uy * s, x1 + ux * e, y1 + uy * e), fill=fill, width=width)
        s, i = e, i + 1


DASH = {"valley": (12, 6), "mountain": (16, 5, 4, 5)}


class Scene:
    def __init__(self, edo, tpl, recs, tests=None):
        self.recs = recs
        self.duration = DURATION
        self.set_label = f"刷った組 {SHEET_SET}"
        self.tests_label = f"試験 {tests}（./run.sh）" if tests else TESTS_DEFAULT
        self.example = tpl.get("example_letter", "A")
        # 三編: 和本は右の頁から読むが、画面では頁の並びのまま左右に置く（見開きの姿を崩さない）。
        self.persp = [ink_layer(edo[f"v3-R0000022/{k}"], PERSP_H / edo[f"v3-R0000022/{k}"].height) for k in ("left", "right")]
        self.wheel = ink_layer(edo["v8-R0000011/wheel"], WHEEL_H / edo["v8-R0000011/wheel"].height)
        sx, sy, sh = SHEET_BOX
        pw, ph = tpl["page_mm"]
        self.k = sh / ph                       # mm → px。刷った紙の絵と線を同じ倍率で置き、線が紙の線に重なるようにする
        self.sheet_rect = (sx, sy, sx + round(pw * self.k), sy + sh)
        self.sheet = tpl["sheet"].resize((self.sheet_rect[2] - sx, sh), Image.LANCZOS)
        self.segs = [(kind, (sx + a[0] * self.k, sy + a[1] * self.k), (sx + b[0] * self.k, sy + b[1] * self.k))
                     for kind, a, b in tpl["segs"]]

    def _lines(self, img, t):
        """型紙の線を、合図の進みに合わせて長さの割合で引く（前のコマに依らない）。"""
        a_cut, a_fold = phase(t, "cuts"), phase(t, "folds")
        printed, gone = phase(t, "printed"), phase(t, "folds_out")
        if a_cut == 0:
            return
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        for kinds, u, alpha, color in ((("cut",), a_cut, 1 - printed, SUMI),
                                       (("valley", "mountain"), a_fold, 1 - gone, SHU)):
            segs = [s for s in self.segs if s[0] in kinds]
            lens = [math.hypot(b[0] - a[0], b[1] - a[1]) for _, a, b in segs]
            budget = u * sum(lens)
            fill = color + (round(255 * alpha),)
            for (kind, a, b), n in zip(segs, lens):
                if budget <= 0 or alpha <= 0:
                    break
                r = min(1.0, budget / n) if n else 1.0
                budget -= n
                end = (a[0] + (b[0] - a[0]) * r, a[1] + (b[1] - a[1]) * r)
                if kind == "cut":
                    d.line((a, end), fill=fill, width=2)
                else:
                    _dashed(d, a, end, DASH[kind], fill, 3)
        img.paste(layer, (0, 0), layer)

    def frame(self, t):
        """時刻 t（秒）の 1 コマ。前のコマに依らない。"""
        img = Image.new("RGB", (W, H), PAPER)
        draw = ImageDraw.Draw(img)
        a_in, a_wheel = phase(t, "persp_in"), phase(t, "wheel_in")
        aside, printed = phase(t, "edo_aside"), phase(t, "printed")
        # 三編の遠近の線: 真ん中に左右の頁を並べ、糸車と入れ替わる。
        a3 = a_in * (1 - a_wheel)
        if a3 > 0:
            total = sum(p.width for p in self.persp) + PERSP_GAP
            x = (W - total) // 2
            for lay, note in zip(self.persp, ("奥へ集まる線", "三ツワリの法")):
                img.paste(_with_alpha(lay, a3), (x, PERSP_Y), _with_alpha(lay, a3))
                text(draw, (x + lay.width // 2, PERSP_Y + PERSP_H + 24), note, 30, fade(SHU, a3), anchor="ma")
                x += lay.width + PERSP_GAP
        # 八編の糸車: 真ん中に現れ、型紙の段で右へ退いて薄くなり、刷った紙が出たら消える。
        a8 = a_wheel * (1 - printed)
        if a8 > 0:
            h = WHEEL_H + (WHEEL_ASIDE_H - WHEEL_H) * aside
            lay = _with_alpha(_scaled(self.wheel, h), a8 * (1 - 0.55 * aside))
            cx = W / 2 + (1450 - W / 2) * aside
            y = round(200 + 60 * aside)
            img.paste(lay, (round(cx - lay.width / 2), y), lay)
            if aside > 0:
                text(draw, (round(cx), y + lay.height + 20), "江戸の線（八編 糸車）", 28, fade(SUMI, 0.7 * a8 * aside), anchor="ma")
        # 型紙: 白い紙 → 切る線 → 折る線 → 刷った PDF。紙は平らなまま（F9）。
        if aside > 0:
            x0, y0, x1, y1 = self.sheet_rect
            region = Image.new("RGB", (x1 - x0, y1 - y0), fade(WHITE, aside))
            if printed > 0:
                region = Image.blend(region, self.sheet, printed)
            img.paste(region, (x0, y0))
            draw.rectangle((x0 - 1, y0 - 1, x1, y1), outline=fade(SUMI, 0.35 * aside), width=1)
        self._lines(img, t)
        a_lab = phase(t, "labels")
        if a_lab > 0:
            text(draw, (W - 80, 64), self.set_label, 40, fade(SHU, a_lab), True, "ra")
            text(draw, (W - 80, 126), self.tests_label, 30, fade(SUMI, a_lab), anchor="ra")
        # 題（左上）: 映している物が変わる所で入れ替える。
        if t < CUES["wheel_in"][0] + 0.75:
            head = ("北斎漫画 三編", "平らな紙に、奥行きを線で描いた", a_in * (1 - ease((t - CUES["wheel_in"][0]) / 0.75)))
        elif t < CUES["edo_aside"][0] + 0.6:
            head = ("北斎漫画 八編", "糸車の仕組みを、図で残した", min(ease((t - CUES["wheel_in"][0] - 0.75) / 0.75),
                                                                   1 - ease((t - CUES["edo_aside"][0]) / 0.6)))
        elif t < CUES["folds_out"][0]:
            head = ("型紙の線", "切る線（墨）と折る線（朱）。生成器が寸法から描く",
                    min(ease((t - CUES["edo_aside"][0] - 0.6) / 0.6), 1 - ease((t - CUES["folds_out"][0] + 0.4) / 0.4)))
        else:
            # 題と隅の札の字は、本人の確かめが来るまで今のまま（手順の紙はもう映さないが、字の直しは本人の確かめの後の別の段）
            head = ("刷った PDF と手順の紙", f"例: 仮説 {self.example} の組。",
                    ease((t - CUES["folds_out"][0]) / 0.6))
        if head[2] > 0:
            text(draw, (80, 60), head[0], 54, fade(SUMI, head[2]), True)
            text(draw, (80, 132), head[1], 32, fade(SUMI, head[2]))
        c = phase(t, "closing")
        if c > 0:
            veil = Image.new("RGBA", (W, H), PAPER + (round(235 * c),))
            img.paste(veil, (0, 0), veil)
            draw = ImageDraw.Draw(img)
            text(draw, (W // 2, 485), "江戸の絵も、仕組みを図で残した。", 58, fade(SUMI, c), True, "ma")
        text(draw, (80, H - 50), self.credit(t), 22, fade(SUMI, 0.7))
        return img

    def credit(self, t):
        """隅の札は、いま映している物の出所に合わせる。北斎の絵が見えている間は必ずその頁の札を出す。"""
        if t < sum(CUES["wheel_in"]) / 2:
            rec = self.recs["pages"]["v3-R0000022"]
        elif t < CUES["printed"][1]:
            rec = self.recs["pages"]["v8-R0000011"]
        else:
            return "型紙と手順の紙: utsushi の生成器が寸法から刷った PDF（slider_fan）。原図の写しは貼っていない"
        return f'図 {rec["short"]}（{rec["publication"]}）国立国会図書館（PDM）　{rec["modification_note"]}'


SHEET_TIMES = (1.2, 4.0, 7.5, 10.5, 12.5, 14.0, 16.5, 18.6, 20.4, 22.6, 24.5, 28.5)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True, help="mp4 の置き場（repo の外）")
    ap.add_argument("--sheet", help="要のコマの一覧の画像")
    ap.add_argument("--cache", default=str(ROOT / "out/demo/cache"))
    ap.add_argument("--tests", help="撮る日の ./run.sh の数（例: 53/53）。無ければ数を出さない")
    a = ap.parse_args(argv)
    cache = pathlib.Path(a.cache)
    recs = load_records()
    pages = {pid: fetch_page(cache, pid, rec) for pid, rec in recs["pages"].items()}
    if any(p is None for p in pages.values()):
        return 4
    try:
        tpl = build_template(cache / "scene4", recs)
    except (OSError, subprocess.CalledProcessError) as e:
        print(f"検査できない: 型紙が刷れない（{e}）", file=sys.stderr)
        return 4
    if tpl is None:
        return 4
    scene = Scene(edo_crops(pages, recs), tpl, recs, a.tests)
    if a.sheet:
        contact_sheet(scene, a.sheet, SHEET_TIMES)
    return render(scene, pathlib.Path(a.out))


if __name__ == "__main__":
    sys.exit(main())
