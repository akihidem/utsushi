"""場面 7 の試作: 槍の型の 18 人と、刷った御来迎の型紙を並べ、締めの字幕とクレジットを出す。

使い方: python -m demo.scene7 --out <repo の外の場所>/scene7.mp4 [--sheet 要のコマの一覧.jpg] [--cache DIR] [--music 曲の札]
exit: 0 = 書き出せた / 4 = 画像が取れない・型紙が刷れない・ffmpeg が無い（このリポの検査の決まりに合わせる）。

決めた事と理由:
- 紙の地・墨・朱・字・切り出しは場面 1（demo.flip）の物をそのまま使う。最初と最後の場面が同じ紙に見えると、
  「絵は止めて残した → 紙で確かめる」の筋が 1 本につながる。
- 型紙は書き出す時に、このリポの生成器（omochae の generate）で刷る。画像を repo に置かず、
  動画の紙が今のエンジンの出す紙と食い違わないようにする。
- 扇が開く所・動く所は映さない（紙で確かめる前に答えを見せない。J-013）。型紙は止まった 1 枚だけを置き、どの仮説が当たりとも言わない（J-025）。
  紙の札は「一例」と書き、刷った組の版だけを出す。順位や点数に見える数は出さない。
- 顔と声は入れない（J-022）。北斎の人物は版画の線で、人の顔の写真ではない。
- frame(t) は時刻だけから 1 コマを描く純関数（場面 1 と同じ）。曲を付ける時は CUES の時刻を拍に合わせて直すだけで済む。
"""
import argparse
import pathlib
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

from demo.flip import (FPS, H, PAPER, ROOT, SERIF, SERIF_BOLD, SHU, SUMI, W, Scene, contact_sheet, ease,
                       ink_layer, load_page, render, text)

# 締めの字幕。文面は本人の採否待ち（plan.md の 6 の 2）なので、変える時はここ 1 か所だけを直す。
CAPTION = "紙で動いても、昔の作り方の証明にはならない"

# クレジット（plan.md の 4 の行をそのまま）。役と名を分けて持ち、画面では役を右寄せ・名を左寄せで揃える。
CREDITS = (
    ("図", "国立国会図書館（PDM）『北斎漫画』『江都二色』"),
    ("型紙と検査", "utsushi のエンジン（paper-to-toy）"),
    ("仮説の案・手順の質問・作る過程・動画のコード", "Claude（Claude Code）"),
    ("試した人", "成人 5 人（11-04）"),
    ("説明と判断", "本人"),
)
# repo の名。README に URL が書かれていないので、URL は作らずに名だけを出す。
REPO_NAME = "utsushi"
# 場面 1 の改変の文は「順に重ねた」なので、この場面では並べ方に合わせた文を自分で持つ。
MODIFICATION = "改変: 頁から人物を 1 人ずつ切り出して並べた。絵の線は描き直していない"

# 合図の表。絵の動きも字幕もここだけを読む。
CUES = {
    "figs_in": (0.0, 3.0),     # 18 人が 1 人ずつ並ぶ
    "sheet_in": (1.5, 3.5),    # 刷った型紙が右に現れる
    "caption": (4.0, 5.2),     # 締めの字幕
    "credits": (7.4, 8.4),     # 紙を覆ってクレジット
}
DURATION = 12.0
SHEET_TIMES = (0.6, 1.8, 3.6, 4.6, 6.0, 7.8, 8.6, 10.0, 11.8)

# 並べ方: 左の枠に 6 列 3 段。和本の読む順に合わせ、1 人目を右上に置いて右から左へ並べる。
GRID_COLS, GRID_ROWS = 6, 3
GRID_BOX = (80, 150, 1080, 870)   # 左・上・右・下。下に札、右に型紙の余白を残す
FIG_TALL = 200                    # 一番背の高い人を 200px に。全員を同じ倍率にし、体の大きさの差を消さない
SHEET_LABEL_PX = 28  # 型紙の下の札の字の大きさ
SHEET_BOX = (1180, 120, 1840, 850)  # 型紙を置く枠（A4 の縦長が入る高さ）。下に札の 2 行を置き、940 からの字幕の帯に重ねない


def credit_lines(music=None):
    """画面に出すクレジットの行。曲は本人が決めた時だけ足す（無ければ書かない、plan.md の 4）。"""
    return CREDITS + ((("曲", music),) if music else ())


def make_template(cache):
    """御来迎の型紙をこのリポの生成器で刷り、PNG の画像にする。刷れない時は None。

    凍結した場面 pos_tube の寸法を使う。試験で毎回通っている組なので、動画の紙が検査を通らない紙になる事がない。
    この寸法は仮説 B の紙と同じ（レビューの指摘）。名札が無いと 1 つの仮説だけを推して見えるので、札に仮説 B と順位でない事を書く（J-025）。
    """
    import json

    from omochae.__main__ import generate
    from omochae.model import ToolMissing

    sc = json.loads((ROOT / "tests/frozen/scenarios/pos_tube.json").read_text(encoding="utf-8"))
    stem = pathlib.Path(cache) / "scene7-template" / "goraigo"
    try:
        rc = generate(sc["template"], sc["params"], sc["source_id"], stem)
        if rc != 0:
            print(f"検査できない: 型紙が検査に落ちた（rc={rc}）", file=sys.stderr)
            return None
        # 生成器の PNG は 110dpi。動画では 760px の高さに縮めるので、線が潰れないよう 200dpi で引き直す。
        subprocess.run(["pdftoppm", "-png", "-r", "200", "-singlefile", str(stem.with_suffix(".pdf")),
                        str(stem) + "-200"], check=True, capture_output=True)
    except (ToolMissing, OSError, subprocess.CalledProcessError) as e:
        print(f"検査できない: 型紙が刷れない（{e}）", file=sys.stderr)
        return None
    return Image.open(str(stem) + "-200.png").convert("RGB")


def _alpha(layer, a):
    out = layer.copy()
    out.putalpha(out.getchannel("A").point(lambda v: round(v * a)))
    return out


def _fade(color, a):
    return tuple(round(PAPER[i] + (color[i] - PAPER[i]) * a) for i in range(3))


class Scene7:
    duration = DURATION

    def __init__(self, page, rec, template, music=None):
        self.rec = rec
        # 切り出しと読む順は場面 1 の Scene に任せる（同じ 18 人・同じ順で出すため、並べ替えを二重に書かない）。
        base = Scene(page, rec)
        self.order = base.order
        figs = dict(base.figs)
        k = FIG_TALL / max(g.height for g in figs.values())
        self.fig_layers = {fid: ink_layer(g, k) for fid, g in figs.items()}
        # 型紙は白い紙のまま置く（墨の切り絵にしない）。刷った紙の色と線をそのまま見せるのが目的。
        bw, bh = SHEET_BOX[2] - SHEET_BOX[0], SHEET_BOX[3] - SHEET_BOX[1]
        s = min(bw / template.width, bh / template.height)
        self.template = template.resize((round(template.width * s), round(template.height * s)), Image.LANCZOS)
        self.credits = credit_lines(music)
        from omochae.templates.slider_fan import SHEET_SET
        self.sheet_set = SHEET_SET

    def _grid(self, img, draw, t, dim):
        x0, y0, x1, y1 = GRID_BOX
        cw, ch = (x1 - x0) / GRID_COLS, (y1 - y0) / GRID_ROWS
        a, b = CUES["figs_in"]
        step = (b - a) / len(self.order)
        for i, fid in enumerate(self.order):
            # 1 人ずつ 0.4 秒で現れる。場面 1 の枠が 1 人ずつ付く動きと同じ拍にそろえる。
            v = ease((t - a - i * step) / 0.4) * dim
            if v <= 0:
                continue
            col, row = GRID_COLS - 1 - i % GRID_COLS, i // GRID_COLS
            lay = self.fig_layers[fid]
            cx, base = round(x0 + (col + 0.5) * cw), round(y0 + (row + 1) * ch - 18)
            l2 = _alpha(lay, v)
            img.paste(l2, (cx - lay.width // 2, base - lay.height), l2)
            # 足もとの線: 場面 1 で揃えた足もとの線を、ここでも細く引く
            draw.line((cx - cw * 0.4, base + 4, cx + cw * 0.4, base + 4), fill=_fade(SUMI, 0.3 * v), width=1)
        text(draw, ((x0 + x1) // 2, y1 + 24), "北斎漫画 六編　槍の型の 18 の絵", 32, _fade(SUMI, ease((t - a) / 1.0) * dim),
             anchor="ma")

    def _sheet(self, img, draw, t, dim):
        v = ease((t - CUES["sheet_in"][0]) / (CUES["sheet_in"][1] - CUES["sheet_in"][0])) * dim
        if v <= 0:
            return
        tw, th = self.template.size
        x = SHEET_BOX[0] + (SHEET_BOX[2] - SHEET_BOX[0] - tw) // 2
        y = SHEET_BOX[1]
        # 紙の影: 刷った紙が地の上に置かれて見えるよう、少しずらした濃い地を敷く
        shadow = Image.new("RGBA", (tw, th), SUMI + (round(40 * v),))
        img.paste(shadow, (x + 8, y + 8), shadow)
        sheet = self.template.convert("RGBA")
        sheet.putalpha(round(255 * v))
        img.paste(sheet, (x, y), sheet)
        for i, s in enumerate(self.sheet_label_lines()):
            text(draw, (x + tw // 2, SHEET_BOX[3] + 12 + i * (SHEET_LABEL_PX + 6)), s, SHEET_LABEL_PX, _fade(SUMI, v), anchor="ma")

    def sheet_label_lines(self):
        """型紙の下の札。1 行では右の端で組の名が切れた（11-05）ので、何の紙かと、順位でない事・組の名を 2 行に分ける。"""
        return ("刷った型紙の一例（御来迎・仮説 B の紙）", f"順位ではない・組 {self.sheet_set}")

    def _credits(self, img, c):
        # 覆いは最後に不透明にする。下の絵が薄く透けると、クレジットの字と重なって読みにくい
        veil = Image.new("RGBA", (W, H), PAPER + (round(255 * c),))
        img.paste(veil, (0, 0), veil)
        draw = ImageDraw.Draw(img)
        text(draw, (W // 2, 230), REPO_NAME, 104, _fade(SUMI, c), True, "ma")
        draw.line((W // 2 - 60, 380, W // 2 + 60, 380), fill=_fade(SHU, c), width=3)
        # 役と名の境目を、一番長い役と一番長い名の幅から決めて、全体を真ん中に置く
        size, gap = 38, 44
        f = ImageFont.truetype(SERIF, size)
        fb = ImageFont.truetype(SERIF_BOLD, size)
        rw = max(fb.getlength(r) for r, _ in self.credits)
        nw = max(f.getlength(n) for _, n in self.credits)
        mid = round((W - (rw + gap + nw)) / 2 + rw)
        y = 450
        for role, name in self.credits:
            text(draw, (mid, y), role, size, _fade(SHU, c), True, "ra")
            text(draw, (mid + gap, y), name, size, _fade(SUMI, c))
            y += 84
        return draw

    def frame(self, t):
        """時刻 t（秒）の 1 コマ。前のコマに依らない。"""
        img = Image.new("RGB", (W, H), PAPER)
        draw = ImageDraw.Draw(img)
        cap = ease((t - CUES["caption"][0]) / (CUES["caption"][1] - CUES["caption"][0]))
        # 字幕が出たら絵と紙を少し薄くし、字幕を読む順を先にする
        dim = 1 - 0.35 * cap
        self._grid(img, draw, t, dim)
        self._sheet(img, draw, t, dim)
        if cap > 0:
            band = Image.new("RGBA", (W, 120), PAPER + (round(230 * cap),))
            img.paste(band, (0, 940), band)
            draw = ImageDraw.Draw(img)
            text(draw, (W // 2, 962), CAPTION, 54, _fade(SUMI, cap), True, "ma")
        c = ease((t - CUES["credits"][0]) / (CUES["credits"][1] - CUES["credits"][0]))
        if c > 0:
            draw = self._credits(img, c)
        # 隅の札: 出所と改変は毎コマ出す（場面 1 と同じ決まり）。字幕の帯の上に重ならないよう上の隅に置く。
        text(draw, (80, 50), f'図 {self.rec["title"]}（{self.rec["publication"]}）国立国会図書館（PDM）　{MODIFICATION}',
             22, _fade(SUMI, 0.7))
        return img


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True, help="mp4 の置き場（repo の外）")
    ap.add_argument("--sheet", help="要のコマの一覧の画像")
    ap.add_argument("--cache", default=str(ROOT / "out/demo/cache"))
    ap.add_argument("--music", help="曲のクレジットの文（本人が決めた時だけ。無ければ書かない）")
    a = ap.parse_args(argv)
    page, rec = load_page(pathlib.Path(a.cache))
    if page is None:
        return 4
    template = make_template(a.cache)
    if template is None:
        return 4
    scene = Scene7(page, rec, template, a.music)
    if a.sheet:
        contact_sheet(scene, a.sheet, SHEET_TIMES)
    return render(scene, pathlib.Path(a.out))


if __name__ == "__main__":
    sys.exit(main())
