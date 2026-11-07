"""場面 2: 『江都二色』の御来迎の図を、場面 1 と同じ紙の地に置き、図に寄りながら本人の語りを 1 かたまりずつ添える。

使い方: python -m demo.scene2 --out <repo の外の場所>/scene2.mp4 [--sheet 要のコマの一覧.jpg] [--cache DIR]
exit: 0 = 書き出せた / 4 = 画像が取れない・ffmpeg が無い（このリポの検査の決まりに合わせる）。

決めた事と理由:
- 玩具の動き方は一切見せない（F9）。矢印・部品の動き・仕組みの線・部品の上の「?」を描かない。
  動くのは「目」（寄り）と字の出入りだけで、図の中の部品どうしは最後まで同じ形のまま。
- 寄りは頁全体を 1 枚の絵として拡大するだけにする。部品ごとに切り出して動かすと、
  それだけで「ここが動く」の暗示になる。
- 色の複写だが、場面 1 と同じく墨一色（ink_layer）にする。場面をまたいで紙の地と墨の色が
  変わると別の動画に見える。
- 本人の指示（11-05）で、題・歌・締めの字幕は本人の語りに置き換えた。語りの字は demo.words の 1 か所にあり、全文と照らす。
- 本人の方針（11-05 20:10）「認知負荷を減らす」で、隅の札は外し、出所と改変はクレジットへ寄せた（demo.scene7）。
  クレジットでは「1773 年の本」とだけ書かない。映るのは 1931 年に米山堂が複製した本なので、元の年と複製の年を両方書く。
"""
import argparse
import json
import pathlib
import sys

from PIL import Image, ImageDraw, ImageChops, ImageFilter, ImageOps

from demo.flip import H, PAPER, SUMI, W, contact_sheet, ease, fetch_image, ink_layer, render
from demo.words import TALKS, band, chunk_alpha, cues_of, seconds_of

ROOT = pathlib.Path(__file__).resolve().parents[2]
SOURCES = pathlib.Path(__file__).with_name("scene2_sources.json")
DURATION = seconds_of("scene2")

# 合図の表。絵の動きも字幕もここだけを読む。曲を付ける時は拍に合わせてこの時刻を直す。
CUES = dict(sorted({
    "page_in": (0.0, 1.4),    # 頁が紙の地に現れる
    "push": (0.6, 6.0),       # 図へゆっくり寄る（目が動くだけ。図の中は動かない）
    **cues_of("scene2"),      # 語りのかたまりが現れる時刻
}.items(), key=lambda kv: kv[1]))
HOLD = (CUES["push"][1], DURATION)  # 図が止まっている間。床はここで図の画素が変わらない事を見る
PAPER_CUT = 175   # これより明るい灰は紙とみなして白に飛ばす
FIG_RIGHT = 1080  # 寄った図の右の端。語りはこれより右に置き、床が図の領域だけを比べられるようにする
TEXT_X, TEXT_SIZE = 1500, 46  # 語りの真ん中と字の大きさ


def phase(t, cue):
    # flip.phase は flip.CUES を読むので、この場面の CUES で同じ事をする（flip.py は変えない）
    a, b = CUES[cue]
    return ease((t - a) / (b - a))


def load_record():
    rec = json.loads(SOURCES.read_text(encoding="utf-8"))
    src = json.loads((ROOT / rec["source_record"]).read_text(encoding="utf-8"))
    return rec, src


def load_page(cache, rec):
    """見開きの画像を IIIF から取る（cache に残す）。取れない時は None。"""
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / "1187053-R0000005-2400.jpg"
    try:
        fetch_image(rec["image_url"], path)  # 確かめてから置く（壊れた写しを残さない）
    except OSError as e:
        print(f"検査できない: 頁の画像が取れない（{e}）", file=sys.stderr)
        return None
    return Image.open(path).convert("L")


def pct_box(size, pct):
    x, y, w, h = pct
    return (round(x / 100 * size[0]), round(y / 100 * size[1]),
            round((x + w) / 100 * size[0]), round((y + h) / 100 * size[1]))


def page_layer(spread, rec):
    """見開きから左の頁を切り出し、墨の層にする。語りの札（demo.words）の図も同じ層を使う。"""
    page = spread.crop(pct_box(spread.size, rec["page_pct"]))
    # 裏写り（裏の頁の絵が透けた薄い線）と黄ばんだ紙を先に白へ飛ばす。flip.clean の閾値 190 は
    # 北斎漫画の白い紙で決めた値で、この複写の紙と裏写りが灰色のまま残ったため（試し見で 175 に決めた）。
    page = ImageOps.autocontrast(page, cutoff=1).point(lambda v: 255 if v > PAPER_CUT else v)
    # 墨の層は元の大きさのまま持ち、毎コマ 1 回の affine で拡大縮小する（縮めた層を拡大すると線がぼける）
    layer = ink_layer(page, 1)
    # 頁の端は影で灰色になり、四角い縁が見えてしまう。端の 60px を紙へぼかして、紙の地に溶かす。
    edge = Image.new("L", layer.size, 0)
    ImageDraw.Draw(edge).rectangle((60, 60, layer.width - 61, layer.height - 61), fill=255)
    edge = edge.filter(ImageFilter.GaussianBlur(25))
    layer.putalpha(ImageChops.multiply(layer.getchannel("A"), edge))
    return layer


class Scene2:
    duration = DURATION

    def __init__(self, spread, rec):
        self.rec = rec
        self.chunks = TALKS["scene2"]
        self.layer = page_layer(spread, rec)
        pw, ph = self.layer.size
        # 寄る前: 頁全体を高さ 800px で、左に寄せて置く。右は語りの場所として空けておく。
        s0 = 800 / ph
        self.start = (s0, (FIG_RIGHT + 60 - pw * s0) / 2, (H - ph * s0) / 2)
        # 寄った後: 図の枠を高さ 880px にし、左半分（右の端 FIG_RIGHT まで）の真ん中に置く。
        fx0, fy0, fx1, fy1 = pct_box((pw, ph), rec["figure_pct"])
        s1 = min(880 / (fy1 - fy0), (FIG_RIGHT - 120) / (fx1 - fx0))
        cx, cy = (FIG_RIGHT + 60) / 2, (H - 40) / 2
        self.end = (s1, cx - (fx0 + fx1) / 2 * s1, cy - (fy0 + fy1) / 2 * s1)

    def page_at(self, t):
        """頁の層を、時刻 t の寄りの位置で画面の大きさに描く。寄りは倍率を対数で補い、一定の速さに見せる。"""
        u = phase(t, "push")
        (s0, x0, y0), (s1, x1, y1) = self.start, self.end
        s = s0 * (s1 / s0) ** u
        # 画面上の点 = 頁の点 * s + 位置。位置は倍率に合わせ、図の中心が真っすぐ寄るように補う
        k = (s - s0) / (s1 - s0) if s1 != s0 else u
        x, y = x0 + (x1 - x0) * k, y0 + (y1 - y0) * k
        return self.layer.transform((W, H), Image.AFFINE, (1 / s, 0, -x / s, 0, 1 / s, -y / s),
                                    resample=Image.BICUBIC, fillcolor=SUMI + (0,))

    def frame(self, t):
        """時刻 t（秒）の 1 コマ。前のコマに依らない。"""
        img = Image.new("RGB", (W, H), PAPER)
        a_in = phase(t, "page_in")
        if a_in > 0:
            pg = self.page_at(t)
            if a_in < 1:
                pg.putalpha(pg.getchannel("A").point(lambda v: round(v * a_in)))
            img.paste(pg, (0, 0), pg)
        draw = ImageDraw.Draw(img)
        # 語り: 下の真ん中の字幕の帯に 1 かたまりずつ（ファイナリストから借りた点 1・2。前は図の右に大きく。本人の言葉の印は外した）
        for i, lines in enumerate(self.chunks):
            v = chunk_alpha(CUES, len(self.chunks), i, t)
            if v > 0:
                img = band(img, lines, v)
        return img


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True, help="mp4 の置き場（repo の外）")
    ap.add_argument("--sheet", help="要のコマの一覧の画像")
    ap.add_argument("--cache", default=str(ROOT / "out/demo/cache"))
    a = ap.parse_args(argv)
    rec, _ = load_record()
    spread = load_page(pathlib.Path(a.cache), rec)
    if spread is None:
        return 4
    scene = Scene2(spread, rec)
    if a.sheet:
        contact_sheet(scene, a.sheet, times=tuple(round(DURATION * k, 2) for k in (0.05, 0.14, 0.22, 0.32, 0.5, 0.66, 0.75, 0.88, 0.98)))
    return render(scene, pathlib.Path(a.out))


if __name__ == "__main__":
    sys.exit(main())
