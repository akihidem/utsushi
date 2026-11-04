"""場面 6: 作った人の言葉で、次の版が変わる（本人の所見 → 雛形の直し T-0001 → v7 と今の紙の差 → 工作の手帖）。

使い方: python -m demo.scene6 --out <repo の外の場所>/scene6.mp4 [--sheet 要のコマの一覧.jpg] [--cache DIR]
exit: 0 = 書き出せた / 4 = 型紙が刷れない・pdftoppm か google-chrome か ffmpeg が無い（このリポの検査の決まりに合わせる）。

決めた事と理由:
- 本人の所見は docs/process/trials/README.md の文をそのまま引く（言い換えると「作った人の言葉」でなくなる）。
  床で、引いた文が README に一字一句ある事を見る。
- 台帳の直し T-0001 は、git の外の data/loop を読まずに、README と sheets/README の文から書く。
  撮る機械に data/loop が無くても同じ絵になるようにするため。
- 古い紙は作り直さない。11-04 の試行に渡した v7 の PDF（docs/process/trials/sheets/goraigo-v7、git にある）を
  そのまま映す。今の生成器で v7 は刷れないので、刷れない版を作った振りをしない。v8・v9 は紙を出さず、変えた事の字だけにする。
- 今の紙は repo の生成器（compose → render.write_all）で撮る時に刷る。版の札は slider_fan.SHEET_SET から読む
  （字で書くと、刷り直した時に動画だけ古くなる）。差の朱の枠も、同じ配置（layout）の部品の形から引く。
- 扇の開き方・動き方は描かない（F9）。型紙は平らなまま映し、矢印も付けない。
- 仮説 A と C を並べるのは、本人の所見がこの 2 つについてだったから。順位ではない（J-025）。
- 工作の手帖は src/web/techo.py の data() と頁の型から、cache の中に頁を書き出し、headless の Chrome で撮る。
  techo.main() は out/techo/index.html に固定で書くので使わない（撮るための細工を足した頁を repo の out に残さない）。
  撮るのは「よくある言葉」と「仕組みの質問を断る」の 2 つの答えだけ。どちらも AI を呼ばず、仕組みの説明を含まない。
  頁の外の字（Google Fonts）は外し、網につながずに毎回同じ絵にする。
- 顔と声は入れない（J-022）。手帖の読み上げは撮る前に切る。
- frame(t) は時刻だけから 1 コマを描く純関数（flip.py と同じ）。合図は CUES の 1 か所だけを読む。
"""
import argparse
import json
import pathlib
import re
import shutil
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

from demo.flip import H, PAPER, ROOT, SERIF_BOLD, SHU, SUMI, W, contact_sheet, ease, fade, render, text
from omochae.templates.slider_fan import SHEET_SET

DURATION = 30.0

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

# 台帳のつながり（README の「台帳での形」の段から）。
CHAIN = ("記録 R-0001・R-0002", "本人の説明", "雛形の直し T-0001", "goraigo-v8（本人が採った）")
# 版ごとに変えた事（sheets/README の表から縮めた）。( 版, 文, 床で sheets/README に有る事を見る語 )
CHANGES = (
    ("v8", "仮説 C にも内筒の土台（2 土台）を足した", "2 土台"),
    ("v8", "仮説 A の溝は、くり抜かずに下の端から切り込む", "下の端からはさみで切り込む"),
    ("v8", "扇の真ん中に足と糊代、台に貼る印", "扇の真ん中の 1 枚に足と糊代"),
    ("v9", "見える面は折り線を刷らず、色の境で折る（観察者の意見から本人が決めた）", "絵の色の境で折る"),
    ("v10", "手順の紙の問いを 4 つの着目に。型紙の部品は v9 と同じ", "型紙の部品は v9 と同じ"),
)
# 紙の差の朱の札。部品の形から枠を引く（下の change_regions）。
LABEL_GROOVE, LABEL_BASE, LABEL_COLOR = "下からの切り込み", "土台", "色の境で折る"
SHOWN_HYPS = ("H-A", "H-C")

# 手帖で撮る 2 つの質問。左はよくある言葉（型紙の説明から答える）、右は仕組みの質問（答えない）。
ASKS = (("谷折りって？", "よくある言葉は、型紙の説明から"), ("どう動くの？", "仕組みの質問は、答えない"))
TECHO_LABEL = "手順だけ答える・仕組みは答えない"
PHONE_PX = (430, 932)   # 撮る窓の大きさ（CSS の px）。手元の iPhone に近い縦長
PHONE_SCALE = 2

CAPTION = ("作った人の言葉で、次の版が変わる。", "作りながら聞ける。")

# 合図の表。絵の動きも字幕もここだけを読む。曲を付ける時は拍に合わせてこの時刻を直す。
CUES = {
    "quote1": (0.0, 0.8),        # 1 つ目の所見
    "quote2": (2.4, 3.2),        # 2 つ目の所見
    "quotes_out": (6.4, 7.0),
    "chain": (7.0, 7.8),         # 台帳のつながりと、版ごとに変えた事
    "chain_out": (11.0, 11.5),
    "pair_a": (11.5, 12.2),      # 仮説 A の紙: v7 と今
    "boxes_a": (12.6, 13.6),     # 差の朱の枠
    "pair_a_out": (16.0, 16.5),
    "pair_c": (16.5, 17.2),      # 仮説 C の紙: v7 と今
    "boxes_c": (17.6, 18.6),
    "pair_c_out": (21.0, 21.5),
    "techo": (21.5, 22.3),       # 工作の手帖の 2 つの画面
    "techo_label": (22.8, 23.6),
    "closing": (26.6, 28.0),     # 締めの字幕（30 秒まで止めて読ませる）
}

# 置き場（px）。紙は高さ 720px。左に v7、右に今の紙、間の帯に朱の札を置く。
SHEET_H, SHEET_Y = 720, 210
OLD_X, NEW_X = 120, 940
PHONE_H = 780
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


def techo_html(question):
    """手帖の頁に、撮るための細工を足した HTML。中身は techo.data() と頁の型から作る（手帖と同じ物を撮る）。

    細工は 3 つだけ: 外の字の読み込みを外す（網につながず毎回同じ絵）、読み上げを切る（声を入れない、J-022）、
    質問を入れて送る（頁の中の同じ答え方を通す。答えを手で書き込まない）。
    """
    from web import techo

    page = (ROOT / "src/web/techo_page.html").read_text(encoding="utf-8")
    page = page.replace("/*TECHO_DATA*/null", json.dumps(techo.data(), ensure_ascii=False))
    page = re.sub(r'<link [^>]*fonts\.(googleapis|gstatic)\.com[^>]*>\n?', "", page)
    script = ("<script>window.addEventListener('load',()=>{document.getElementById('speak').checked=false;"
              f"document.getElementById('q').value={json.dumps(question, ensure_ascii=False)};"
              "document.getElementById('ask-form').requestSubmit();});</script>")
    return page + script


def capture_techo(cache):
    chrome = shutil.which("google-chrome") or shutil.which("chromium")
    if not chrome:
        print("検査できない: google-chrome が無い", file=sys.stderr)
        return None
    d = cache / "techo"
    d.mkdir(parents=True, exist_ok=True)
    shots = []
    for i, (q, _) in enumerate(ASKS):
        html, png = d / f"ask{i}.html", d / f"ask{i}.png"
        html.write_text(techo_html(q), encoding="utf-8")
        png.unlink(missing_ok=True)
        subprocess.run([chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--user-data-dir={d / 'profile'}",
                        f"--force-device-scale-factor={PHONE_SCALE}", f"--window-size={PHONE_PX[0]},{PHONE_PX[1]}",
                        "--virtual-time-budget=3000", f"--screenshot={png}", html.resolve().as_uri()],
                       capture_output=True, timeout=120)
        if not png.exists():
            print(f"検査できない: 手帖の画面が撮れない（{q}）", file=sys.stderr)
            return None
        shots.append(Image.open(png).convert("RGB"))
    return shots


# ---- 描く ----

def _scaled(img, h):
    return img.resize((max(1, round(img.width * h / img.height)), round(h)), Image.LANCZOS)


def _blend_in(img, layer, xy, a):
    """layer を a の濃さで紙の上に置く（前のコマに依らず、今の img の上だけで混ぜる）。"""
    x, y = xy
    region = img.crop((x, y, x + layer.width, y + layer.height))
    img.paste(Image.blend(region, layer, a), (x, y))


def _phone(shot, h):
    """スマホの枠。墨の縁と角の丸みだけ（機種の形は描かない）。"""
    inner = _scaled(shot, h - 36)
    w = inner.width + 36
    frame = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(frame)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=46, fill=SUMI + (255,))
    mask = Image.new("L", inner.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, inner.width - 1, inner.height - 1), radius=30, fill=255)
    frame.paste(inner, (18, 18), mask)
    return frame.convert("RGB"), frame.getchannel("A")


class Scene:
    def __init__(self, pairs, shots):
        self.duration = DURATION
        self.new_label = SHEET_SET
        self.tag = f"{OLD_SET} → {SHEET_SET}・T-0001"
        self.pairs = []
        for p in pairs:
            pw, ph = p["page_mm"]
            k = SHEET_H / ph   # mm → px。今の紙の絵と朱の枠を同じ倍率で置き、枠が紙の部品に重なるようにする
            size = (round(pw * k), SHEET_H)
            self.pairs.append({**p, "k": k, "old": p["old"].resize(size, Image.LANCZOS),
                               "new": p["new"].resize(size, Image.LANCZOS)})
        self.phones = [_phone(s, PHONE_H) for s in shots]

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

    def _chain(self, img, draw, t):
        u = span(t, "chain", "chain_out")
        if u <= 0:
            return
        text(draw, (80, 60), "台帳の直し T-0001", 54, fade(SUMI, u), True)
        text(draw, (80, 132), "言葉が記録につながり、人が採った直しだけが次の版になる", 32, fade(SUMI, u))
        x, y = 120, 250
        for i, s in enumerate(CHAIN):
            # 箱の幅は字の実際の幅から（英数字が混じると字数では測れず、右端からはみ出した）
            w = 50 + round(draw.textlength(s, font=ImageFont.truetype(SERIF_BOLD, 30)))
            color = SHU if s.startswith("雛形の直し") else SUMI
            draw.rectangle((x, y, x + w, y + 90), outline=fade(color, u), width=3)
            text(draw, (x + w // 2, y + 45), s, 30, fade(color, u), True, "mm")
            x += w
            if i < len(CHAIN) - 1:
                text(draw, (x + 30, y + 45), "→", 40, fade(SUMI, u), anchor="mm")
                x += 60
        for i, (ver, s, _) in enumerate(CHANGES):
            yy = 430 + i * 78
            text(draw, (160, yy), ver, 36, fade(SHU, u), True)
            text(draw, (290, yy), s, 36, fade(SUMI, u))

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

    def _techo(self, img, draw, t):
        u = phase(t, "techo") * (1 - phase(t, "closing"))
        if u <= 0:
            return
        x = 200
        y = (H - PHONE_H) // 2 + 10
        for (rgb, alpha), (q, note) in zip(self.phones, ASKS):
            region = img.crop((x, y, x + rgb.width, y + rgb.height))
            mask = alpha.point(lambda v: round(v * u))
            region.paste(rgb, (0, 0), mask)
            img.paste(region, (x, y))
            text(draw, (x + rgb.width // 2, y + PHONE_H + 14), note, 26, fade(SUMI, u), anchor="ma")
            x += rgb.width + 90
        v = phase(t, "techo_label") * u
        text(draw, (x + 40, 330), "工作の手帖", 58, fade(SUMI, u), True)
        text(draw, (x + 40, 420), "作りながら、スマホで聞く", 34, fade(SUMI, u))
        first, _, second = TECHO_LABEL.partition("・")
        text(draw, (x + 40, 520), first + "・", 46, fade(SHU, v), True)
        text(draw, (x + 40, 584), second, 46, fade(SHU, v), True)
        text(draw, (x + 40, 680), "仕組みは、紙で試して確かめる所だから", 30, fade(SUMI, v))

    def frame(self, t):
        """時刻 t（秒）の 1 コマ。前のコマに依らない。"""
        img = Image.new("RGB", (W, H), PAPER)
        draw = ImageDraw.Draw(img)
        self._quotes(img, draw, t)
        self._chain(img, draw, t)
        for p, cues in zip(self.pairs, (("pair_a", "boxes_a", "pair_a_out"), ("pair_c", "boxes_c", "pair_c_out"))):
            self._pair(img, draw, t, p, *cues)
        self._techo(img, draw, t)
        # 札（右上）: 版の移りと台帳の ID。台帳の段からずっと出す。
        lab = phase(t, "chain") * (1 - phase(t, "closing"))
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
        if t < CUES["chain_out"][1]:
            return "出所: docs/process/trials/README.md（本人の所見・台帳の形）・trials/sheets/README.md（版ごとに変えた事）"
        if t < CUES["pair_c_out"][1]:
            return (f"左: git に残した {OLD_SET} の PDF（docs/process/trials/sheets）　右: 今の生成器（slider_fan）が刷った PDF。"
                    "朱の枠は変えた所")
        return "工作の手帖: src/web/techo.py の頁を手元のブラウザで撮った。2 つの答えは頁の中の決まりで出た物（AI は呼んでいない）"


SHEET_TIMES = (1.5, 5.0, 9.5, 12.3, 14.5, 17.4, 19.5, 22.5, 24.5, 26.0, 27.5, 29.5)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True, help="mp4 の置き場（repo の外）")
    ap.add_argument("--sheet", help="要のコマの一覧の画像")
    ap.add_argument("--cache", default=str(ROOT / "out/demo/cache"))
    a = ap.parse_args(argv)
    cache = pathlib.Path(a.cache) / "scene6"
    try:
        pairs = build_sheets(cache)
        shots = capture_techo(cache) if pairs else None
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        print(f"検査できない: 素材が作れない（{e}）", file=sys.stderr)
        return 4
    if not pairs or not shots:
        return 4
    scene = Scene(pairs, shots)
    if a.sheet:
        contact_sheet(scene, a.sheet, SHEET_TIMES)
    return render(scene, pathlib.Path(a.out))


if __name__ == "__main__":
    sys.exit(main())
