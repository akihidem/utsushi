"""場面 2: 『江都二色』の御来迎の図を、場面 1 と同じ紙の地に置き、図に寄って歌を添える。

使い方: python -m demo.scene2 --out <repo の外の場所>/scene2.mp4 [--sheet 要のコマの一覧.jpg] [--cache DIR]
exit: 0 = 書き出せた / 4 = 画像が取れない・ffmpeg が無い（このリポの検査の決まりに合わせる）。

決めた事と理由:
- 玩具の動き方は一切見せない（F9）。矢印・部品の動き・仕組みの線・部品の上の「?」を描かない。
  動くのは「目」（寄り）と字の出入りだけで、図の中の部品どうしは最後まで同じ形のまま。
  この場面の芯は「動き方は書かれていない」なので、少しでも動きを描けば字幕と食い違う。
- 寄りは頁全体を 1 枚の絵として拡大するだけにする。部品ごとに切り出して動かすと、
  それだけで「ここが動く」の暗示になる。
- 色の複写だが、場面 1 と同じく墨一色（ink_layer）にする。場面をまたいで紙の地と墨の色が
  変わると別の動画に見える。色を捨てる事は改変として隅の札に書く。
- 歌は scene2_sources.json に写さず、data/sources の記録から本人が確かめた読みを毎回読む。
  読みが直された時に、動画の字と記録が食い違わないようにするため。
- 隅の札は「1773 年の本」と書かない。映るのは 1931 年に米山堂が複製した本なので、
  元の年と複製の年を両方書く（所蔵の記録の holding に合わせる）。
"""
import argparse
import json
import pathlib
import sys

from PIL import Image, ImageDraw, ImageChops, ImageFilter, ImageOps

from demo.flip import FPS, H, PAPER, SHU, SUMI, W, contact_sheet, ease, fade, fetch_image, ink_layer, render, text

ROOT = pathlib.Path(__file__).resolve().parents[2]
SOURCES = pathlib.Path(__file__).with_name("scene2_sources.json")
DURATION = 20.0

# 合図の表。絵の動きも字幕もここだけを読む。曲を付ける時は拍に合わせてこの時刻を直す。
CUES = {
    "page_in": (0.0, 1.8),    # 頁が紙の地に現れる
    "title_out": (2.6, 3.4),  # 題の 2 行が消える（寄った頁と重ならないように）
    "push": (3.0, 8.0),       # 図へゆっくり寄る（目が動くだけ。図の中は動かない）
    "song": (8.4, 9.8),       # 歌が右に現れる
    "closing": (14.5, 16.0),  # 締めの字幕。20 秒まで止めて読ませる
}
SONG_OUT = (13.6, 14.4)  # 歌は締めの字幕より先に消す（重ねると両方読めない。試し見で直した）
HOLD = (CUES["push"][1], CUES["closing"][0])  # 図が止まっている間。床はここで図の画素が変わらない事を見る
PAPER_CUT = 175   # これより明るい灰は紙とみなして白に飛ばす
FIG_RIGHT = 1080  # 寄った図の右の端。歌はこれより右に置き、床が図の領域だけを比べられるようにする


def phase(t, cue):
    # flip.phase は flip.CUES を読むので、この場面の CUES で同じ事をする（flip.py は変えない）
    a, b = CUES[cue]
    return ease((t - a) / (b - a))


def load_record():
    rec = json.loads(SOURCES.read_text(encoding="utf-8"))
    src = json.loads((ROOT / rec["source_record"]).read_text(encoding="utf-8"))
    return rec, src


def checked_song(src):
    """本人が確かめ、退けられていない読みだけを使う。無ければ歌を出さない（Claude だけの読みは画面に出さない）。"""
    tr = src.get("transcription", {})
    if tr.get("status") != "human_checked":
        return None
    for e in tr.get("entries", []):
        if e.get("checked_by") and not e.get("rejected_by"):
            return e
    return None


def song_lines(s):
    """上の句と下の句に分ける。「朝な」で割れなければ真ん中で割る（読みが直されても画面が崩れない）。"""
    i = s.find("朝な")
    if i <= 0:
        i = len(s) // 2
    return s[:i].strip(), s[i:].strip()


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


class Scene2:
    duration = DURATION

    def __init__(self, spread, rec, src):
        self.rec = rec
        self.song = checked_song(src)
        page = spread.crop(pct_box(spread.size, rec["page_pct"]))
        # 裏写り（裏の頁の絵が透けた薄い線）と黄ばんだ紙を先に白へ飛ばす。flip.clean の閾値 190 は
        # 北斎漫画の白い紙で決めた値で、この複写の紙と裏写りが灰色のまま残ったため（試し見で 175 に決めた）。
        page = ImageOps.autocontrast(page, cutoff=1).point(lambda v: 255 if v > PAPER_CUT else v)
        # 墨の層は元の大きさのまま持ち、毎コマ 1 回の affine で拡大縮小する（縮めた層を拡大すると線がぼける）
        self.layer = ink_layer(page, 1)
        # 頁の端は影で灰色になり、四角い縁が見えてしまう。端の 60px を紙へぼかして、紙の地に溶かす。
        edge = Image.new("L", self.layer.size, 0)
        ImageDraw.Draw(edge).rectangle((60, 60, self.layer.width - 61, self.layer.height - 61), fill=255)
        edge = edge.filter(ImageFilter.GaussianBlur(25))
        self.layer.putalpha(ImageChops.multiply(self.layer.getchannel("A"), edge))
        pw, ph = self.layer.size
        # 寄る前: 頁全体を高さ 800px で真ん中に。上に題、下に札の余白を残す（場面 1 と同じ考え）。
        s0 = 800 / ph
        self.start = (s0, (W - pw * s0) / 2, (H - ph * s0) / 2 + 30)
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
        # 題: 頁が現れる間だけ。寄り始めたら消す。
        a_t = a_in * (1 - phase(t, "title_out"))
        if a_t > 0:
            text(draw, (80, 70), "江都二色", 54, fade(SUMI, a_t), True)
            text(draw, (80, 140), "安永二年（1773）の絵本。玩具の図と歌が並ぶ", 34, fade(SUMI, a_t))
        # 歌: 図の右に。本人が確かめた読みが無ければ出さない。
        a, b = SONG_OUT
        a_s = phase(t, "song") * (1 - ease((t - a) / (b - a)))
        if self.song and a_s > 0:
            x = FIG_RIGHT + 60
            text(draw, (x, 300), "歌", 40, fade(SHU, a_s), True)
            kami, shimo = song_lines(self.song["text"])
            text(draw, (x, 380), kami, 50, fade(SUMI, a_s), True)
            text(draw, (x + 100, 460), shimo, 50, fade(SUMI, a_s), True)
            # 「本人」は画面の外の人には通じないので、人が確かめた事だけを書く。
            # 頁にほかの文が無いとは言わない（人が確かめていない）。それは締めの字幕に任せる。
            text(draw, (x, 580), f'読み: 手元の複写の頁 {self.song["page"]} による（人が確かめた）', 26, fade(SUMI, 0.7 * a_s))
        # 締め: 紙を薄く掛け、図はうっすら残す（止まった絵のまま）。
        c = phase(t, "closing")
        if c > 0:
            veil = Image.new("RGBA", (W, H), PAPER + (round(225 * c),))
            img.paste(veil, (0, 0), veil)
            draw = ImageDraw.Draw(img)
            text(draw, (W // 2, 440), "図と歌だけが残った玩具。", 58, fade(SUMI, c), True, "ma")
            text(draw, (W // 2, 530), "動き方は書かれていない。", 58, fade(SUMI, c), True, "ma")
        # 隅の札: 元の年と複製の年を両方。場面 1 と同じ大きさ。1 行では画面の幅を越えるので 2 行に分ける。
        text(draw, (80, H - 82), self.rec["credit"], 22, fade(SUMI, 0.7))
        text(draw, (80, H - 50), self.rec["modification_note"], 22, fade(SUMI, 0.7))
        return img


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True, help="mp4 の置き場（repo の外）")
    ap.add_argument("--sheet", help="要のコマの一覧の画像")
    ap.add_argument("--cache", default=str(ROOT / "out/demo/cache"))
    a = ap.parse_args(argv)
    rec, src = load_record()
    spread = load_page(pathlib.Path(a.cache), rec)
    if spread is None:
        return 4
    scene = Scene2(spread, rec, src)
    if a.sheet:
        contact_sheet(scene, a.sheet, times=(0.9, 2.2, 4.5, 6.5, 8.0, 9.2, 12.0, 15.2, 19.0))
    return render(scene, pathlib.Path(a.out))


if __name__ == "__main__":
    sys.exit(main())
