"""場面 flip: 北斎漫画の槍の型の人物を切り出し、足もとを揃えてゆっくり重ね、字幕「絵は動きを止めて残した。…」を出す。

使い方: python -m demo.flip --out <repo の外の場所>/scene1.mp4 [--sheet 要のコマの一覧.jpg]
exit: 0 = 書き出せた / 4 = 画像が取れない・ffmpeg が無い（このリポの検査の決まりに合わせる）。

決めた事と理由:
- 絵は描き直さず、所蔵の画像をそのまま切り出す。線を描き直すと北斎の線でなくなり、
  「江戸の絵が動く」の芯が消える。改変（切り出して重ねた）は画面の隅に必ず出す。
- frame(t) は時刻だけから 1 コマを描く純関数にする（前のコマの状態を持たない）。
  試し見の 1 コマと本番の書き出しが同じ絵になり、曲を付ける時は拍の時刻を CUES に入れるだけで済む。
- 18 の絵は 1 人の人物の連続した動きではなく、槍の型の別々の姿。字幕では「動いた」と言わない。
- 本人の方針（11-05 20:10）「たくさん見る審査員の認知負荷を減らす方針が1番最初。癒し系で。」で、頁・枠・数・題・隅の札を外し、速い重ねをやめた。
  出所と改変の説明はクレジットへ寄せた（demo.scene7）。字幕は 1 かたまりずつ、1 秒 5 字以下で出す。
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
    "page_in": (0.0, 0.8),     # 人物が紙の地に現れる
    "line0": (0.3, 0.8),       # 字幕の前半
    "flip": (0.6, 2.6),        # 人物をゆっくり溶かして重ねる。割り切れる長さにして、止まった時に次の姿を薄く残さない
    "line1": (2.7, 3.2),       # 字幕の後半。人物は止まったまま
}
FLIP_FPS = 2                   # 1 秒に 2 枚。前の 6 枚は癒し系の方針に対して速いので落とした。溶かして替えるのでカクつかない
FADE = 0.6                     # 場面の頭と終わりを紙の地へ溶かす秒（faded）
FIG_X, FIG_BASE, TEXT_X = 420, 860, 1270   # 人物の真ん中・足もと、字幕の真ん中
DURATION = 6.6
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


BG_INK = 0.26                 # 背景の絵の濃さ（真ん中の北斎漫画より目立たせない）
SIDE = ((300, 0.55), (600, 0.62), (1320, 0.62), (1620, 0.55))   # 真ん中の両脇に並べる人物の (真ん中の x, 大きさ)
SIDE_IN = 0.5                 # 両脇の人物が 1 人ずつ現れる間（秒）


def load_backgrounds(cache):
    """背景の絵（figures.json の backgrounds）を IIIF から取り、枠で切った RGBA の層の並びにする。取れない絵は飛ばす（場面は止めない）。
    墨の絵（ink=sumi）は墨色の切り絵、色の絵（ink=color）は色のまま。濃さは frame で掛ける"""
    recs = json.loads(FIGURES.read_text(encoding="utf-8")).get("backgrounds", {})
    cache = pathlib.Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    out = []
    for key, rec in recs.items():
        if key.startswith("_"):
            continue
        path = cache / f"bg-{key}.jpg"
        try:
            fetch_image(f'{rec["iiif"]}/full/1600,/0/default.jpg', path)
        except OSError as e:
            print(f"背景の絵が取れない（{key}・{e}）。この絵は敷かずに書き出す", file=sys.stderr)
            continue
        with Image.open(path) as im:
            x, y, w, h = rec["box_pct"]
            box = (round(x / 100 * im.width), round(y / 100 * im.height), round((x + w) / 100 * im.width), round((y + h) / 100 * im.height))
            crop = im.convert("RGB").crop(box)
        if rec.get("ink") == "sumi":
            lay = ink_layer(crop.convert("L"), 1.0)
        else:
            lay = crop.convert("RGBA")
        out.append((key, lay))
    return out


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


def draw_closing(draw, line, cx, cy, size, a):
    """締めの字幕の 1 かたまりを描く。動画の初めと終わりで同じ字にする。"""
    from demo.english import text_en  # 英語字幕（日本語の下に 1 組で。demo.english。ここで読むのは english が flip を読むため）

    text_en(draw, (cx, cy - size // 2), line, size, fade(SUMI, a), False, "ma")


class Scene:
    def __init__(self, page, rec, backgrounds=()):
        """backgrounds は load_backgrounds の層（場面 flip だけが渡す。締めの場面 7 は前のまま人物だけ）。"""
        self.rec = rec
        self.backgrounds = list(backgrounds)
        self.figs = cut_figures(page, rec)
        # 読む順: 和本なので右の頁から、上の段の右から左へ。
        order = sorted(self.figs, key=lambda f: (f[0][0] != "R", f[0][1], -ord(f[0][2])))
        self.order = [f[0] for f in order]
        tall = max(g.height for _, g in self.figs)
        self.fig_layers = {fid: ink_layer(g, 640 / tall) for fid, g in self.figs}
        # 背景を敷く形（11-07）では、北斎漫画を真ん中に置き、両脇にほかの型の人物を並べて賑やかにする（本人のデモの直し 7）。
        # 両脇の人物は、真ん中で重ねる 4 人（flip の秒の間に替わる）とは別の人物から取る
        self.cx = W // 2 if self.backgrounds else FIG_X
        rest = self.order[4:] or self.order
        self.side = [(x, ink_layer(dict(self.figs)[rest[k * len(rest) // len(SIDE)]], 640 / tall * sc)) for k, (x, sc) in enumerate(SIDE)] if self.backgrounds else []

    def _figure(self, img, i, v):
        """i 番目の人物を、足もとを同じ線に揃えて v の濃さで置く。"""
        lay = self.fig_layers[self.order[i % len(self.order)]]
        l2 = lay.copy()
        l2.putalpha(l2.getchannel("A").point(lambda x: round(x * v)))
        img.paste(l2, (self.cx - lay.width // 2, FIG_BASE - lay.height), l2)

    def frame(self, t):
        """時刻 t（秒）の 1 コマ。前のコマに依らない。"""
        img = Image.new("RGB", (W, H), PAPER)
        a_in = phase(t, "page_in")
        # 背景: 江戸の浮世絵・舞台絵を薄く（場面の頭で現れて、その後は動かさない）。1 枚目は真ん中に大きく、2 枚目は右上に小さく
        for k, (key, lay) in enumerate(self.backgrounds):
            scale = (H * 0.92 / lay.height) if k == 0 else (W * 0.34 / lay.width)
            l2 = lay.resize((max(1, round(lay.width * scale)), max(1, round(lay.height * scale))), Image.LANCZOS)
            l2.putalpha(l2.getchannel("A").point(lambda x, v=BG_INK * a_in: round(x * v)))
            xy = ((W - l2.width) // 2, (H - l2.height) // 2) if k == 0 else (W - l2.width - 60, 60)
            img.paste(l2, xy, l2)
        # 両脇の人物: 1 人ずつ現れて、その後は動かさない（動いたとは言わない。18 の絵は別々の姿）
        for k, (x, lay) in enumerate(self.side):
            v = ease((t - (CUES["page_in"][0] + 0.3 + k * SIDE_IN)) / 0.6) * 0.8
            if v > 0:
                l2 = lay.copy()
                l2.putalpha(l2.getchannel("A").point(lambda a, v=v: round(a * v)))
                img.paste(l2, (x - lay.width // 2, FIG_BASE - lay.height), l2)
        draw = ImageDraw.Draw(img)
        # 重ねる: 型の姿をゆっくり溶かして替える。止まった所からが字幕の後半（絵は動きを止めて残した）。
        f0, f1 = CUES["flip"]
        u = max(0.0, min(t, f1) - f0) * FLIP_FPS
        n, w = int(u), ease(u - int(u))
        if a_in > 0:
            self._figure(img, n, a_in * (1 - w))
            if w > 0:
                self._figure(img, n + 1, a_in * w)
        # 字幕: 1 かたまりずつ。替わる時は溶かす（1 度に 1 かたまりだけ）。
        c0, c1 = CUES["line0"][0], CUES["line1"][0]
        v0 = ease((t - c0) / 0.5) * (1 - ease((t - (c1 - 0.5)) / 0.5))
        v1 = ease((t - c1) / 0.5)
        # 下の真ん中の字幕の帯（ファイナリストから借りた点 1・2。前は人物の右に大きく）
        from demo.words import band

        if v0 > 0:
            img = band(img, (CLOSING[0],), v0)
        if v1 > 0:
            img = band(img, (CLOSING[1],), v1)
        return img


def faded(scene, t):
    """書き出す 1 コマ。場面の頭と終わりを紙の地へ溶かす。速いカットをやめるため（本人の方針 11-05「癒し系」）。
    どの場面もここを通るので、場面ごとに溶けを書かない。頭は場面の地（ground）から、終わりは次の場面の紙の地へ。"""
    img = scene.frame(t)
    d = getattr(scene, "duration", DURATION)
    head, tail = ease(t / FADE), ease((d - 1 / FPS - t) / FADE)
    k = min(head, tail)
    if k >= 1:
        return img
    ground = getattr(scene, "ground", PAPER) if head < tail else PAPER
    return Image.blend(Image.new("RGB", img.size, ground), img, k)


def guided(scene, name):
    """案内役の出る場面なら、案内役を重ねた場面にする（本人の決定 11-06。demo.guide）。どの場面も書き出しはここを通るので、場面ごとに書かない。
    場面の名前は書き出す道の名（demo.build は <置き場>/<場面>.mp4 と <場面>-sheet.jpg に書く）。"""
    from demo import guide

    from demo import later

    if isinstance(scene, later.Later):  # もう包んである（書き出しとコマの一覧の両方がここを通る）
        return scene
    if name in guide.PLANS and not isinstance(scene, guide.Guided):
        scene = guide.Guided(scene, name, ROOT / "out/demo/cache")
    # 後入れの札（本人の指示 11-07）。語りの声と本物の Claude の返事の所に、後入れと分かる札を重ねる（demo.later）
    return later.Later(scene, name)


def render(scene, out):
    """どの場面も frame(t) と duration を持てば、この 1 つで書き出せる（場面ごとに書き出しを作らない）。"""
    if not shutil.which("ffmpeg"):
        print("検査できない: ffmpeg が無い", file=sys.stderr)
        return 4
    if not (SERIF and SERIF_BOLD):
        print("検査できない: 字（Noto Serif CJK）が無い。別の字で書き出すと日本語が読めない", file=sys.stderr)
        return 4
    out.parent.mkdir(parents=True, exist_ok=True)
    scene = guided(scene, out.stem)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", str(out)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(round(getattr(scene, "duration", DURATION) * FPS)):
        p.stdin.write(faded(scene, i / FPS).tobytes())
    p.stdin.close()
    return 0 if p.wait() == 0 else 4


def contact_sheet(scene, path, times=(0.3, 0.9, 1.6, 2.3, 2.9, 3.4, 4.2, 5.4, 6.5)):
    """要のコマを並べた一覧。動画を開かずに検品できる（エビデンスの 1 つ）。"""
    scene = guided(scene, pathlib.Path(path).stem.removesuffix("-sheet"))
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
    scene = Scene(page, rec, load_backgrounds(pathlib.Path(a.cache)))
    if a.sheet:
        contact_sheet(scene, a.sheet)
    return render(scene, pathlib.Path(a.out))


if __name__ == "__main__":
    sys.exit(main())
