"""場面 1 の試作: 北斎漫画の槍の型の 18 人を切り出し、足もとを揃えて順に重ねる（パラパラ）。

使い方: python -m demo.flip --out <repo の外の場所>/scene1.mp4 [--sheet 要のコマの一覧.jpg]
exit: 0 = 書き出せた / 4 = 画像が取れない・ffmpeg が無い（このリポの検査の決まりに合わせる）。

決めた事と理由:
- 絵は描き直さず、所蔵の画像をそのまま切り出す。線を描き直すと北斎の線でなくなり、
  「江戸の絵が動く」の芯が消える。改変（切り出して重ねた）は画面の隅に必ず出す。
- frame(t) は時刻だけから 1 コマを描く純関数にする（前のコマの状態を持たない）。
  試し見の 1 コマと本番の書き出しが同じ絵になり、曲を付ける時は拍の時刻を CUES に入れるだけで済む。
- 18 の絵は 1 人の人物の連続した動きではなく、槍の型の別々の姿。字幕では「動いた」と言わず「順に重ねた」と言う。
"""
import argparse
import json
import pathlib
import shutil
import subprocess
import sys
import urllib.request

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = pathlib.Path(__file__).resolve().parents[2]
FIGURES = pathlib.Path(__file__).with_name("figures.json")
PAGE = "v6-R0000020"
W, H, FPS = 1920, 1080, 30
PAPER = (239, 230, 210)   # 生成りの紙。白より、刷った和紙に見える
SUMI = (43, 38, 34)       # 墨
SHU = (190, 60, 40)       # 朱。枠と数字だけに使う（色を増やすと版画の絵とぶつかる）


def _font(pattern):
    """字の場所は機械ごとに違うので、fc-match で引く（パスを書き込まない）。明朝は江戸の版本の字に近い。
    fc-match は字が無くても別の字（DejaVu など）を黙って返し、日本語が豆腐の字のまま書き出せてしまう。
    家族の名が Noto Serif CJK でない時は空にし、render が 4 で止める。"""
    try:
        out = subprocess.run(["fc-match", "-f", "%{family}|%{file}", pattern], capture_output=True, text=True).stdout
    except OSError:
        return ""  # fc-match 自体が無い。読み込みで落とさず、demo.build の道具の確かめが名前で 4 を返す
    family, _, path = out.partition("|")
    return path.strip() if "Noto Serif CJK" in family else ""


SERIF = _font("Noto Serif CJK JP")
SERIF_BOLD = _font("Noto Serif CJK JP:bold")

# 合図の表。絵の動きも字幕もここだけを読む。曲を付ける時は拍に合わせてこの時刻を直す。
CUES = {
    "page_in": (0.0, 1.5),     # 頁が現れる
    "boxes": (2.0, 5.6),       # 18 人に 1 人ずつ枠が付く
    "page_aside": (5.8, 6.8),  # 頁が左へ退き、薄くなる
    "flip": (6.8, 12.8),       # 右で 18 人を順に重ねる
    "closing": (12.8, 14.0),   # 締めの字幕。動画の初めと終わりに出す字なので、出きった後に止めて読ませる
}
FLIP_FPS = 6                   # 1 秒に 6 枚。速いと型の姿が読めず、遅いと動いて見えない（試し見で決めた）
DURATION = 16.0
# 初めと終わりの字幕（本人の決定 11-05）。終わりの札（demo.words）もここから読み、字と置き場を食い違わせない。
CLOSING = ("絵は動きを止めて残した。", "どう動いたかは、紙で作って確かめる。")


def fetch_image(url, path):
    """画像を取り寄せて path に置く。中身を確かめてから置き、壊れた写しは消して取り直す。
    壊れた写しを残すと、以後ずっと開けずに止まり続けるため。取れない時は例外（OSError など）。"""
    if path.exists():
        try:
            with Image.open(path) as im:
                im.verify()
            return path
        except Exception:
            path.unlink()
    data = urllib.request.urlopen(url, timeout=60).read()
    tmp = path.with_suffix(path.suffix + ".part")
    tmp.write_bytes(data)
    try:
        with Image.open(tmp) as im:
            im.verify()
    except Exception:
        tmp.unlink()
        raise OSError(f"画像として読めない: {url}")
    tmp.replace(path)
    return path


def load_page(cache):
    """頁の画像を IIIF から取る（cache に残す）。取れない時は None。"""
    rec = json.loads(FIGURES.read_text(encoding="utf-8"))["pages"][PAGE]
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / f"{PAGE}.jpg"
    try:
        fetch_image(f'{rec["iiif"]}/full/full/0/default.jpg', path)
    except OSError as e:
        print(f"検査できない: 頁の画像が取れない（{e}）", file=sys.stderr)
        return None, rec
    return Image.open(path).convert("L"), rec


def clean(gray):
    """複写の細かい点を消し、墨の線だけを残す。閾値は 6 編の頁で試し見して決めた。"""
    g = ImageOps.autocontrast(gray, cutoff=1)
    return g.point(lambda v: 255 if v > 190 else v)


def ink_layer(gray, scale):
    """灰色の絵を、墨色の RGBA の切り絵にする（白いところは透ける）。"""
    g = clean(gray)
    if scale != 1:
        g = g.resize((max(1, round(g.width * scale)), max(1, round(g.height * scale))), Image.LANCZOS)
    alpha = ImageOps.invert(g)
    layer = Image.new("RGBA", g.size, SUMI + (0,))
    layer.putalpha(alpha)
    return layer


def cut_figures(page, rec):
    """枠の割合から人物を切り出す。足もと（墨の一番下）と横の重心を後で揃えるため、墨の外接の箱で詰める。"""
    out = []
    for f in rec["figures"]:
        x, y, w, h = f["box_pct"]
        box = (round(x / 100 * page.width), round(y / 100 * page.height),
               round((x + w) / 100 * page.width), round((y + h) / 100 * page.height))
        g = clean(page.crop(box))
        bb = ImageOps.invert(g).point(lambda v: 255 if v > 60 else 0).getbbox()
        out.append((f["id"], g.crop(bb) if bb else g))
    return out


def ease(u):
    u = min(1.0, max(0.0, u))
    return u * u * (3 - 2 * u)


def phase(t, cue):
    a, b = CUES[cue]
    return ease((t - a) / (b - a))


def text(draw, xy, s, size, fill=SUMI, bold=False, anchor="la"):
    draw.text(xy, s, font=ImageFont.truetype(SERIF_BOLD if bold else SERIF, size), fill=fill, anchor=anchor)


def fade(color, a):
    return tuple(round(PAPER[i] + (color[i] - PAPER[i]) * a) for i in range(3))


def draw_closing(draw, a):
    """締めの字幕を描く。動画の初めと終わりで同じ字・同じ大きさ・同じ置き場にする。"""
    text(draw, (W // 2, 440), CLOSING[0], 58, fade(SUMI, a), True, "ma")
    text(draw, (W // 2, 530), CLOSING[1], 58, fade(SUMI, a), True, "ma")


class Scene:
    def __init__(self, page, rec):
        self.rec = rec
        # 頁は高さ 780px に縮めて置く。上に題の 2 行、下に出所の札を置く余白が要る。
        self.page_scale = 780 / page.height
        self.page = ink_layer(page, self.page_scale)
        self.figs = cut_figures(page, rec)
        # 読む順: 和本なので右の頁から、上の段の右から左へ。
        order = sorted(self.figs, key=lambda f: (f[0][0] != "R", f[0][1], -ord(f[0][2])))
        self.order = [f[0] for f in order]
        tall = max(g.height for _, g in self.figs)
        self.fig_layers = {fid: ink_layer(g, 640 / tall) for fid, g in self.figs}

    def frame(self, t):
        """時刻 t（秒）の 1 コマ。前のコマに依らない。"""
        img = Image.new("RGB", (W, H), PAPER)
        draw = ImageDraw.Draw(img)
        # 頁: 真ん中に現れ、裏返しの段で左へ退いて薄くなる。
        a_in, a_side = phase(t, "page_in"), phase(t, "page_aside")
        scale = 1 - 0.45 * a_side
        pg = self.page.resize((round(self.page.width * scale), round(self.page.height * scale)), Image.LANCZOS)
        px = round((W - pg.width) / 2 * (1 - a_side) + 60 * a_side)
        py = round((H - pg.height) / 2 + 50 * (1 - a_side))
        alpha = a_in * (1 - 0.6 * a_side)
        if alpha > 0:
            pg.putalpha(pg.getchannel("A").point(lambda v: round(v * alpha)))
            img.paste(pg, (px, py), pg)
        # 枠: 18 人に 1 人ずつ。頁が退くと一緒に縮む。
        a, b = CUES["boxes"]
        shown = 0 if t < a else min(len(self.order), int((t - a) / (b - a) * len(self.order)) + 1)
        figs = {f["id"]: f["box_pct"] for f in self.rec["figures"]}
        for fid in self.order[:shown]:
            x, y, w, h = figs[fid]
            kx, ky = pg.width / 100, pg.height / 100
            draw.rectangle((px + x * kx, py + y * ky, px + (x + w) * kx, py + (y + h) * ky),
                           outline=fade(SHU, 1 - 0.5 * a_side), width=3)
        if shown and t < CUES["page_aside"][1]:
            text(draw, (W - 80, 90), f"{shown} / {len(self.order)} 人", 44, SHU, True, "ra")
        # 重ねる: 足もとを同じ線に揃え、横は真ん中に。
        f0, f1 = CUES["flip"]
        if f0 <= t < CUES["closing"][0] + 0.6:
            n = min(len(self.order) - 1, int((t - f0) * FLIP_FPS) % len(self.order))
            if t >= f1:
                n = len(self.order) - 1
            lay = self.fig_layers[self.order[n]]
            cx, base = 1300, 900
            # 締めの字幕と重ならないよう、締めに入ったら消す
            fade_in = ease((t - f0) / 0.4) * (1 - ease((t - CUES["closing"][0]) / 0.6))
            l2 = lay.copy()
            l2.putalpha(l2.getchannel("A").point(lambda v: round(v * fade_in)))
            img.paste(l2, (cx - lay.width // 2, base - lay.height), l2)
            draw.line((cx - 330, base + 6, cx + 330, base + 6), fill=fade(SUMI, 0.35 * fade_in), width=2)
            text(draw, (W - 80, 90), f"{n + 1:02d} / {len(self.order)}", 44, fade(SHU, fade_in), True, "ra")
            text(draw, (cx, 960), "槍の型の 18 の絵を、足もとを揃えて順に重ねた", 34, fade(SUMI, fade_in), anchor="ma")
        # 字幕と隅の札
        if t < CUES["page_aside"][0]:
            text(draw, (80, 70), "北斎漫画 六編", 54, fade(SUMI, a_in), True)
            text(draw, (80, 140), "江戸の絵手本。動きの途中を、止めて描いた", 34, fade(SUMI, a_in))
        c = phase(t, "closing")
        if c > 0:
            veil = Image.new("RGBA", (W, H), PAPER + (round(235 * c),))
            img.paste(veil, (0, 0), veil)
            draw = ImageDraw.Draw(img)
            draw_closing(draw, c)
        text(draw, (80, H - 50), f'図 {self.rec["title"]}（{self.rec["publication"]}）国立国会図書館（PDM）'
             f'　{self.rec["modification_note"]}', 22, fade(SUMI, 0.7))
        return img


def render(scene, out):
    """どの場面も frame(t) と duration を持てば、この 1 つで書き出せる（場面ごとに書き出しを作らない）。"""
    if not shutil.which("ffmpeg"):
        print("検査できない: ffmpeg が無い", file=sys.stderr)
        return 4
    if not (SERIF and SERIF_BOLD):
        print("検査できない: 字（Noto Serif CJK）が無い。別の字で書き出すと日本語が読めない", file=sys.stderr)
        return 4
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", str(out)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(round(getattr(scene, "duration", DURATION) * FPS)):
        p.stdin.write(scene.frame(i / FPS).tobytes())
    p.stdin.close()
    return 0 if p.wait() == 0 else 4


def contact_sheet(scene, path, times=(0.8, 2.6, 4.0, 5.6, 6.3, 7.5, 9.0, 11.0, 15.5)):
    """要のコマを並べた一覧。動画を開かずに検品できる（エビデンスの 1 つ）。"""
    tw, th = W // 3, H // 3
    sheet = Image.new("RGB", (tw * 3, th * ((len(times) + 2) // 3)), "white")
    for i, t in enumerate(times):
        sheet.paste(scene.frame(t).resize((tw, th)), ((i % 3) * tw, (i // 3) * th))
        ImageDraw.Draw(sheet).text(((i % 3) * tw + 6, (i // 3) * th + 4), f"t={t}s", fill=SHU)
    sheet.save(path, quality=85)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True, help="mp4 の置き場（repo の外）")
    ap.add_argument("--sheet", help="要のコマの一覧の画像")
    ap.add_argument("--cache", default=str(ROOT / "out/demo/cache"))
    a = ap.parse_args(argv)
    page, rec = load_page(pathlib.Path(a.cache))
    if page is None:
        return 4
    scene = Scene(page, rec)
    if a.sheet:
        contact_sheet(scene, a.sheet)
    return render(scene, pathlib.Path(a.out))


if __name__ == "__main__":
    sys.exit(main())
