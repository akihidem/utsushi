"""場面 7: 槍の型の人物を薄く並べ、締めの字幕を出し、クレジットへ溶かす。

使い方: python -m demo.scene7 --out <repo の外の場所>/scene7.mp4 [--sheet 要のコマの一覧.jpg] [--cache DIR] [--music 曲の札]
exit: 0 = 書き出せた / 4 = 画像が取れない・ffmpeg が無い（このリポの検査の決まりに合わせる）。

決めた事と理由:
- 紙の地・墨・朱・字・切り出しは場面 1（demo.flip）の物をそのまま使う。最初と最後の場面が同じ紙に見えると、
  「絵は止めて残した → 紙で確かめる」の筋が 1 本につながる。
- 本人の方針（11-05 20:10）「たくさん見る審査員の認知負荷を減らす方針が1番最初。癒し系で。」で、刷った型紙とその札を外した。
  札が無いと 1 つの仮説を推して見える紙なので（J-025）、札ごと外した。作りながら見る頁（core_make）で今の手順の紙は映る。
- 各場面の隅の札（図の出所・改変・撮った画面・作り物の断り）はここのクレジットへ寄せた。どの場面でも読まれない字を減らすため。
- まだ動かしていない事の断りもクレジットに置く（本人の決定 11-06 で採った。docs/demo/plan.md の 4）。場面ごとに言わないため。
- 扇が開く所・動く所は映さない（紙で確かめる前に答えを見せない。J-013）。
- 顔と声は入れない（J-022）。北斎の人物は版画の線で、人の顔の写真ではない。
- frame(t) は時刻だけから 1 コマを描く純関数（場面 1 と同じ）。曲を付ける時は CUES の時刻を拍に合わせて直すだけで済む。
"""
import argparse
import pathlib
import sys

from PIL import Image, ImageDraw, ImageFont

from demo.flip import H, PAPER, ROOT, SERIF, SHU, SUMI, W, Scene, contact_sheet, ease, ink_layer, load_page, render, text

# 締めの字幕。文面は本人の採否待ち（plan.md の 6 の 2）なので、変える時はここ 1 か所だけを直す。
CAPTION = "紙で動いても、昔の作り方の証明にはならない"

# クレジット（plan.md の 4 の行をそのまま）。役と名を分けて持ち、画面では役を右寄せ・名を左寄せで揃える。
# 各場面の隅にあった札もここへ寄せた（本人の方針 11-05）。「これから作る所」は本人の決定 11-06 で採った。
CREDITS = (
    ("図", "国立国会図書館（PDM）『北斎漫画』『江都二色』"),
    ("図の手入れ", "切り出し、重ね、墨一色。線は描き直していない"),
    ("『江都二色』", "安永二年（1773）の本を、1931 年に米山堂が複製した本"),
    ("画面", "手元で動かして撮った。（例）と見本は動画のための作り物"),
    ("写真", "11-04 の試行。確かめ表で通った物。顔と声は入れない"),
    ("型紙と検査", "utsushi のエンジン（paper-to-toy）"),
    ("仮説の案・手順の質問・作る過程・動画のコード", "Claude（Claude Code）"),
    ("試した人", "成人 5 人（11-04）"),
    ("説明と判断", "本人"),
    ("これから作る所", "図の点線の所と、本物の Claude API の返事"),
)
# repo の名。README に URL が書かれていないので、URL は作らずに名だけを出す。
REPO_NAME = "utsushi"
# 合図の表。絵の動きも字幕もここだけを読む。
CUES = {
    "figs_in": (0.0, 2.0),     # 人物が 1 人ずつ薄く並ぶ
    "caption": (0.6, 1.2),     # 締めの字幕
    "caption_out": (4.8, 5.3),  # 字幕と人物が紙の地へ溶ける
    "credits": (5.4, 5.9),     # 消えてからクレジットが現れる（字を重ねない）
}
DURATION = 9.0
SHEET_TIMES = (0.6, 1.4, 2.4, 3.6, 4.6, 5.1, 5.6, 7.5, 8.8)

# 並べ方: 6 列 3 段の枠の上下の段に置く。真ん中の段は字幕の通り道として空ける（隠すと足だけが残って見えた）。
# 和本の読む順に合わせ、1 人目を右上に置いて右から左へ並べる。
GRID_COLS, GRID_ROWS = 6, 3
GRID_BOX = (260, 120, 1660, 900)
FIG_TALL = 200                    # 一番背の高い人を 200px に。全員を同じ倍率にし、体の大きさの差を消さない
FIG_INK = 0.22                    # 字幕を先に読ませるので薄くする


def credit_lines(music=None):
    """画面に出すクレジットの行。曲は本人が決めた時だけ足す（無ければ書かない、plan.md の 4）。"""
    return CREDITS + ((("曲", music),) if music else ())


def _alpha(layer, a):
    out = layer.copy()
    out.putalpha(out.getchannel("A").point(lambda v: round(v * a)))
    return out


def _fade(color, a):
    return tuple(round(PAPER[i] + (color[i] - PAPER[i]) * a) for i in range(3))


class Scene7:
    duration = DURATION

    def __init__(self, page, rec, music=None):
        self.rec = rec
        # 切り出しと読む順は場面 1 の Scene に任せる（同じ 18 人・同じ順で出すため、並べ替えを二重に書かない）
        base = Scene(page, rec)
        self.order = base.order
        figs = dict(base.figs)
        k = FIG_TALL / max(g.height for g in figs.values())
        self.fig_layers = {fid: ink_layer(g, k) for fid, g in figs.items()}
        self.credits = credit_lines(music)

    def _grid(self, img, t, dim):
        x0, y0, x1, y1 = GRID_BOX
        cw, ch = (x1 - x0) / GRID_COLS, (y1 - y0) / GRID_ROWS
        a, b = CUES["figs_in"]
        step = (b - a) / len(self.order)
        for i, fid in enumerate(self.order):
            v = ease((t - a - i * step) / 0.6) * FIG_INK * dim
            if v <= 0:
                continue
            col, row = GRID_COLS - 1 - i % GRID_COLS, i // GRID_COLS
            if row == 1:
                continue
            lay = self.fig_layers[fid]
            cx, base = round(x0 + (col + 0.5) * cw), round(y0 + (row + 1) * ch - 18)
            l2 = _alpha(lay, v)
            img.paste(l2, (cx - lay.width // 2, base - lay.height), l2)

    def _credits(self, img, c):
        draw = ImageDraw.Draw(img)
        text(draw, (W // 2, 96), REPO_NAME, 84, _fade(SUMI, c), True, "ma")
        draw.line((W // 2 - 60, 214, W // 2 + 60, 214), fill=_fade(SHU, c), width=3)
        # 役と名の境目を、一番長い役と一番長い名の幅から決めて、全体を真ん中に置く
        size, gap = 30, 40
        f = ImageFont.truetype(SERIF, size)
        rw = max(f.getlength(r) for r, _ in self.credits)
        nw = max(f.getlength(n) for _, n in self.credits)
        mid = round((W - (rw + gap + nw)) / 2 + rw)
        y = 262
        for role, name in self.credits:
            text(draw, (mid, y), role, size, _fade(SHU, c), False, "ra")
            text(draw, (mid + gap, y), name, size, _fade(SUMI, c))
            y += 60
        return draw

    def frame(self, t):
        """時刻 t（秒）の 1 コマ。前のコマに依らない。"""
        img = Image.new("RGB", (W, H), PAPER)
        out = ease((t - CUES["caption_out"][0]) / (CUES["caption_out"][1] - CUES["caption_out"][0]))
        if out < 1:
            self._grid(img, t, 1 - out)
        draw = ImageDraw.Draw(img)
        cap = ease((t - CUES["caption"][0]) / (CUES["caption"][1] - CUES["caption"][0])) * (1 - out)
        if cap > 0:
            text(draw, (W // 2, H // 2 - 30), CAPTION, 64, _fade(SUMI, cap), False, "mm")
        c = ease((t - CUES["credits"][0]) / (CUES["credits"][1] - CUES["credits"][0]))
        if c > 0:
            self._credits(img, c)
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
    scene = Scene7(page, rec, a.music)
    if a.sheet:
        contact_sheet(scene, a.sheet, SHEET_TIMES)
    return render(scene, pathlib.Path(a.out))


if __name__ == "__main__":
    sys.exit(main())
