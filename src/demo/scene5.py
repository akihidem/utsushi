"""場面 5: 11-04 の試行。本人の教え子の卒業生 5 人（全員成人）が刷った型紙を紙で作った事を、記録の文と（確かめ済みなら）写真で見せる。

使い方: python -m demo.scene5 --out <repo の外の場所>/scene5.mp4 [--sheet 要のコマの一覧.jpg] [--photos p01,p09]
exit: 0 = 書き出せた / 4 = ffmpeg が無い・写真が確かめ表で通っていない・写真が無い（このリポの検査の決まりに合わせる）。

決めた事と理由:
- 写真は U-24 の確かめ表（docs/process/trials/photos/20261104/review.md）の「本人の判断」で
  載せてよいとされた物だけを使う。repo に写真が在っても、被験者の同意と写りを本人が確かめるまでは
  動画に出さない（動画は repo より広く出回るため）。表の欄が載せてよいでない写真は 1 枚も開かない。
- --photos で撮る日に選び直せるが、確かめ表で通っていない写真は渡されても使わずに止める（exit 4）。
  表を直せばコードを直さずに撮れるようにし、表を飛ばす道は作らない。
- 写真は切らずに枠へ収める（ImageOps.contain）。切ると写りの確かめと違う絵になる。顔のある写真は表に無い。
  動画（goraigo-motion.mp4）は使わない。表では公開してよいとなったが、この場面は写真だけで組んである。
- 画面の数と言葉は docs/process/trials/README.md の文をそのまま写す（床で照らす）。
  data/records と data/loop は git に入らないので読まない。README が言う事だけを言う。
- 結果は正直に「わからない」と出す。記録 R-0001（仮説 A）と R-0002（仮説 C）のどちらも、
  動画と写真がどちらの仮説の紙か分からないため「わからない」と本人が答えた。
- 本人の決定（11-05）「哲学よりの動画にして」で、記録の番号の札を外して短くした。数より、作っている手を見せるため。
- 扇の開き方を図に描かない（F9）。矢印・動きの線も描かない。学びの効果も言わない。声は入れない（J-022）。
- frame(t) は時刻だけから 1 コマを描く純関数（場面 1 と同じ）。曲を付ける時は CUES を拍に合わせて直す。
"""
import argparse
import pathlib
import sys

from PIL import Image, ImageDraw, ImageFont, ImageOps

from demo.flip import H, PAPER, ROOT, SERIF, SERIF_BOLD, SHU, SUMI, W, contact_sheet, ease, fade, render, text

DURATION = 22.0
TRIALS = ROOT / "docs/process/trials/README.md"
PHOTO_DIR = ROOT / "docs/process/trials/photos/20261104"
REVIEW = PHOTO_DIR / "review.md"

# U-24 の確かめ表で「本人の判断」が載せてよいとなった写真（11-05 に本人が 9 枚とも公開してよいと決めた）。
# 床（tests/test_demo_scene5.py）が表を読んでこの値と照らす。表が埋まったら両方をそろえる。
PHOTOS = ("p01", "p02", "p03", "p04", "p05", "p06", "p07", "p08", "p09")
# 「本人の判断」の欄がこの言葉で始まる時だけ載せてよいと読む。「外す」「ぼかす」などは通さない。
# 言葉を広く取ると、条件つきの判断（「ぼかせば載せてよい」）を素通しにしてしまうため、先頭で見る。
ACCEPT = ("載せる", "載せてよい", "公開してよい")  # 欄が丸ごとこのどれかの時だけ通す。「可」「OK」は但し書きと混ざりやすいので外した

# 合図の表。絵の動きも字幕もここだけを読む。曲を付ける時は拍に合わせてこの時刻を直す。
CUES = {
    "title_in": (0.0, 1.2),     # 題と写真の枠が現れる
    "facts": (1.5, 2.7),        # 試した人と案の札
    "facts_out": (6.6, 7.2),
    "notes": (7.4, 8.4),        # 本人の所見（原文のまま）
    "notes_out": (13.6, 14.2),
    "closing": (14.4, 15.8),    # 締めの字幕。22 秒まで止めて読ませる
}
SHEET_TIMES = (0.6, 3.0, 6.0, 8.6, 11.0, 13.0, 15.0, 18.0, 21.5)

# 画面の数は README の文をそのまま写す。床が 1 つずつ README に在るかを見る。
FACTS = (
    ("試した人", "全員が本人の教え子の卒業生（成人）"),
    ("作り方", "1 人が 2 案ずつ作った"),
    ("試した案", "御来迎の仮説 A・仮説 C と張子の虎"),
)
# 本人の所見は README の表の「本人の所見」から、言葉を変えずに引く（誰の言葉かを毎回添える）。
NOTES = (
    "仮説Aは、くり抜く側面の穴を切るのが大変で、下から切り取ることになった",
    "ジャバラの固定に苦慮していた",
    "どちらの仮説も、内側の筒の土台があると良い",
)
# 台本（plan.md の 4 の 5 の行）の字幕をそのまま 2 行に割る。
CAPTION = ("紙で作って、動いた。", "どの仮説の紙かは記録で「わからない」")
EMPTY_LABEL = ("写真は公開前の確かめの後に入る（U-24）",)
SOURCE_NOTE = "記録 docs/process/trials/README.md（11-04）　顔と声は入れない"

FRAME_BOX = (80, 200, 860, 820)   # 写真の枠。左に置き、右の列（RIGHT_X から）に札と所見
RIGHT_X, RIGHT_W = 940, 900


def phase(t, cue):
    # flip.phase は flip.CUES を読むので、この場面の CUES で同じ事をする（flip.py は変えない）
    a, b = CUES[cue]
    return ease((t - a) / (b - a))


def shown(t, cue):
    """札の組が現れて消えるまでの濃さ。組ごとに入れ替えるので、同じ列に 2 組が重ならない。"""
    out = cue + "_out"
    return phase(t, cue) * (1 - phase(t, out)) if out in CUES else phase(t, cue)


def review_table(path=REVIEW):
    """確かめ表を読み、{ファイル名: 本人の判断} を返す。表の形が変わったら空を返し、写真を通さない側へ倒す。"""
    rows = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 5 and cells[0].split("（")[0].strip().endswith((".jpg", ".mp4")):
            rows[cells[0].split("（")[0].strip()] = cells[4]
    return rows


def allowed_photos(path=REVIEW):
    """確かめ表で載せてよいとなった写真の名（p01 など）。動画は場面に使わないので外す。"""
    return tuple(sorted(name[:-4] for name, judge in review_table(path).items()
                        if name.endswith(".jpg") and judge in ACCEPT))


def wrap(s, size, width, bold=False):
    """字の幅を測って折り返す。日本語は空白で切れないので、1 字ずつ足して幅を越えたら改行する。"""
    font = ImageFont.truetype(SERIF_BOLD if bold else SERIF, size)
    lines, cur = [], ""
    for ch in s:
        if cur and font.getlength(cur + ch) > width:
            lines.append(cur)
            cur = ""
        cur += ch
    return lines + [cur] if cur else lines


class Scene5:
    duration = DURATION

    def __init__(self, photos=()):
        # 写真は名の一覧ではなく、開いた画像で持つ。空の一覧なら 1 つも開かない（床で見る）。
        self.photos = []
        fw, fh = FRAME_BOX[2] - FRAME_BOX[0] - 24, FRAME_BOX[3] - FRAME_BOX[1] - 24
        for p in photos:
            with Image.open(p) as im:
                self.photos.append(ImageOps.contain(ImageOps.exif_transpose(im).convert("RGB"), (fw, fh)))

    def photo_at(self, t):
        """写真は枠の出ている間に同じ長さずつ順に替える。時刻だけで決まる。"""
        a, b = CUES["title_in"][1], CUES["closing"][0]
        if not self.photos:
            return None
        i = min(len(self.photos) - 1, max(0, int((t - a) / (b - a) * len(self.photos))))
        return self.photos[i]

    def frame(self, t):
        """時刻 t（秒）の 1 コマ。前のコマに依らない。"""
        img = Image.new("RGB", (W, H), PAPER)
        draw = ImageDraw.Draw(img)
        a_in = phase(t, "title_in")
        text(draw, (80, 70), "11-04 の試行", 54, fade(SUMI, a_in), True)
        text(draw, (80, 140), "刷った御来迎の型紙を、紙で作った", 34, fade(SUMI, a_in))
        # 写真の枠: 写真が無い時は、空の枠と「確かめの後に入る」の札だけ。何かを描いて写真の代わりにしない。
        x0, y0, x1, y1 = FRAME_BOX
        draw.rectangle(FRAME_BOX, outline=fade(SUMI, 0.5 * a_in), width=2)
        ph = self.photo_at(t)
        if ph is not None:
            img.paste(ph, ((x0 + x1 - ph.width) // 2, (y0 + y1 - ph.height) // 2))
            text(draw, (x0, y1 + 16), "写真: 11-04 の試行（U-24 の確かめ済み）", 22, fade(SUMI, 0.7 * a_in))
        else:
            # 点線の内枠で「ここは空けてある」と分かるようにする（実線だけだと何かの図に見える）
            for x in range(x0 + 24, x1 - 24, 24):
                draw.line((x, y0 + 24, x + 12, y0 + 24), fill=fade(SUMI, 0.35 * a_in), width=2)
                draw.line((x, y1 - 24, x + 12, y1 - 24), fill=fade(SUMI, 0.35 * a_in), width=2)
            for y in range(y0 + 24, y1 - 24, 24):
                draw.line((x0 + 24, y, x0 + 24, y + 12), fill=fade(SUMI, 0.35 * a_in), width=2)
                draw.line((x1 - 24, y, x1 - 24, y + 12), fill=fade(SUMI, 0.35 * a_in), width=2)
            for i, line in enumerate(wrap(EMPTY_LABEL[0], 34, x1 - x0 - 120)):
                text(draw, ((x0 + x1) // 2, (y0 + y1) // 2 - 24 + 50 * i), line, 34, fade(SUMI, 0.75 * a_in), anchor="ma")
        # 右の列は 2 組を順に入れ替える: 試した人と案 → 本人の所見
        a = shown(t, "facts")
        if a > 0:
            y = 230
            for label, value in FACTS:
                text(draw, (RIGHT_X, y), label, 30, fade(SHU, a), True)
                for line in wrap(value, 48, RIGHT_W):
                    text(draw, (RIGHT_X, y + 44), line, 48, fade(SUMI, a), True)
                    y += 62
                y += 90
        a = shown(t, "notes")
        if a > 0:
            text(draw, (RIGHT_X, 230), "本人の所見（原文のまま）", 30, fade(SHU, a), True)
            y = 300
            for note in NOTES:
                for j, line in enumerate(wrap(f"「{note}」", 38, RIGHT_W)):
                    text(draw, (RIGHT_X + (0 if j == 0 else 20), y), line, 38, fade(SUMI, a))
                    y += 56
                y += 40
        # 締め: 紙を薄く掛け、字幕だけを読ませる。
        c = phase(t, "closing")
        if c > 0:
            veil = Image.new("RGBA", (W, H), PAPER + (round(235 * c),))
            img.paste(veil, (0, 0), veil)
            draw = ImageDraw.Draw(img)
            text(draw, (W // 2, 440), CAPTION[0], 58, fade(SUMI, c), True, "ma")
            text(draw, (W // 2, 530), CAPTION[1], 58, fade(SUMI, c), True, "ma")
        text(draw, (80, H - 50), SOURCE_NOTE, 22, fade(SUMI, 0.7))
        return img


def resolve_photos(arg):
    """--photos の名を写真の道に直す。確かめ表で通っていない名や無い写真があれば None（使わずに止める）。"""
    names = PHOTOS if arg is None else tuple(n.strip() for n in arg.split(",") if n.strip())
    ok = set(allowed_photos())
    bad = [n for n in names if n not in ok]
    if bad:
        print(f"検査できない: U-24 の確かめ表で載せてよいとなっていない写真 {','.join(bad)}", file=sys.stderr)
        return None
    paths = [PHOTO_DIR / f"{n}.jpg" for n in names]
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        print(f"検査できない: 写真が無い {','.join(missing)}", file=sys.stderr)
        return None
    return paths


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True, help="mp4 の置き場（repo の外）")
    ap.add_argument("--sheet", help="要のコマの一覧の画像")
    ap.add_argument("--photos", help="使う写真（例 p01,p09）。確かめ表で通った物だけ。省くと PHOTOS")
    a = ap.parse_args(argv)
    photos = resolve_photos(a.photos)
    if photos is None:
        return 4
    scene = Scene5(photos)
    if a.sheet:
        contact_sheet(scene, a.sheet, times=SHEET_TIMES)
    return render(scene, pathlib.Path(a.out))


if __name__ == "__main__":
    sys.exit(main())
