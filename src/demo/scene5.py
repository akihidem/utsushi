"""場面 5: 11-04 の試行。刷った型紙を紙で作った事を、確かめ済みの写真と短い字幕で見せる。

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
- 字幕の言葉は docs/process/trials/README.md が言う事だけを言う（床で照らす）。data/records と data/loop は git に入らないので読まない。
- 結果は正直に「わからない」と出す。記録 R-0001（仮説 A）と R-0002（仮説 C）のどちらも、
  動画と写真がどちらの仮説の紙か分からないため「わからない」と本人が答えた。
- 本人の決定（11-05）「哲学よりの動画にして」で、記録の番号の札を外して短くした。数より、作っている手を見せるため。
- 本人の方針（11-05 20:10）「認知負荷を減らす」「癒し系」で、試した人と案の札・本人の所見の列・隅の札を外し、写真を 3 枚に絞ってゆっくり溶かす。
  試した人と写真の断りはクレジットへ寄せた（demo.scene7）。
- 扇の開き方を図に描かない（F9）。矢印・動きの線も描かない。学びの効果も言わない。声は入れない（J-022）。
- frame(t) は時刻だけから 1 コマを描く純関数（場面 1 と同じ）。曲を付ける時は CUES を拍に合わせて直す。
"""
import argparse
import pathlib
import sys

from PIL import Image, ImageDraw, ImageOps

from demo.flip import H, PAPER, ROOT, SUMI, W, contact_sheet, ease, fade, render, text

DURATION = 5.0  # 2 つ目の字幕を消した（本人の決定 11-06）。浮いた 3 秒は始まりの場面へ戻した
TRIALS = ROOT / "docs/process/trials/README.md"
PHOTO_DIR = ROOT / "docs/process/trials/photos/20261104"
REVIEW = PHOTO_DIR / "review.md"

# U-24 の確かめ表で「本人の判断」が載せてよいとなった写真（11-05 に本人が 9 枚とも公開してよいと決めた）。
# 床（tests/test_demo_scene5.py）が表を読んでこの値と照らす。表が埋まったら両方をそろえる。
PHOTOS = ("p01", "p02", "p03", "p04", "p05", "p06", "p07", "p08", "p09")
# 「本人の判断」の欄がこの言葉で始まる時だけ載せてよいと読む。「外す」「ぼかす」などは通さない。
# 言葉を広く取ると、条件つきの判断（「ぼかせば載せてよい」）を素通しにしてしまうため、先頭で見る。
ACCEPT = ("載せる", "載せてよい", "公開してよい")  # 欄が丸ごとこのどれかの時だけ通す。「可」「OK」は但し書きと混ざりやすいので外した

# 合図の表。絵の動きも字幕もここだけを読む。曲を付ける時は CUES を拍に合わせて直す。
CUES = {
    "title_in": (0.0, 1.0),     # 写真が現れる
    "photo1": (1.6, 2.6),       # 次の写真へ溶ける
    "line0": (2.0, 2.5),        # 字幕の前半
    "photo2": (3.0, 3.8),       # 動いた紙の写真へ溶ける。5 秒まで止めて見せる
}
SHEET_TIMES = (0.6, 1.5, 2.2, 3.0, 3.6, 4.2, 4.9)
# 切る → 組む → 動いた、の順に 3 枚。多く見せると速いカットになるので減らした。縦の写真でそろえ、溶ける時に形が崩れないようにする。確かめ表で通った物だけ（resolve_photos）。
SHOWN = ("p05", "p02", "p07")
# 台本（plan.md の 4）の字幕。1 かたまりずつ出す。
# 本人の決定（11-06）: 2 つ目の字幕「どの仮説の紙かは記録で「わからない」」は消す。型紙 1 枚の形では案がいくつもあるように聞こえ、読む負担にもなるため
CAPTION = ("紙で作って、動いた。",)
FRAME_BOX = (360, 56, 1560, 856)   # 写真の枠。下に字幕の余白

def phase(t, cue):
    # flip.phase は flip.CUES を読むので、この場面の CUES で同じ事をする（flip.py は変えない）
    a, b = CUES[cue]
    return ease((t - a) / (b - a))


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


class Scene5:
    duration = DURATION

    def __init__(self, photos=()):
        # 写真は名の一覧ではなく、開いた画像で持つ。空の一覧なら 1 つも開かない（床で見る）
        self.photos = []
        self.sheets = []   # 枠の大きさの紙に写真を置いた物。縦と横の写真の間でも溶かせるようにする
        fw, fh = FRAME_BOX[2] - FRAME_BOX[0], FRAME_BOX[3] - FRAME_BOX[1]
        for p in photos:
            with Image.open(p) as im:
                ph = ImageOps.contain(ImageOps.exif_transpose(im).convert("RGB"), (fw, fh))
            self.photos.append(ph)
            sheet = Image.new("RGB", (fw, fh), PAPER)
            sheet.paste(ph, ((fw - ph.width) // 2, (fh - ph.height) // 2))
            self.sheets.append(sheet)

    def sheet_at(self, t):
        """時刻 t の写真。替わり目はゆっくり溶かす。写真が無い時は None。"""
        if not self.sheets:
            return None
        cues = ("photo1", "photo2")[:len(self.sheets) - 1]
        out = self.sheets[0]
        for i, cue in enumerate(cues):
            v = phase(t, cue)
            if v > 0:
                out = Image.blend(out, self.sheets[i + 1], v)
        return out

    def frame(self, t):
        """時刻 t（秒）の 1 コマ。前のコマに依らない。"""
        img = Image.new("RGB", (W, H), PAPER)
        sheet = self.sheet_at(t)
        if sheet is not None:
            a_in = phase(t, "title_in")
            if a_in < 1:
                sheet = Image.blend(Image.new("RGB", sheet.size, PAPER), sheet, a_in)
            img.paste(sheet, FRAME_BOX[:2])
        draw = ImageDraw.Draw(img)
        # 字幕は 1 かたまり。現れたら場面の終わり（溶け）まで止めて読ませる。
        v0 = ease((t - CUES["line0"][0]) / 0.5)
        if v0 > 0:
            text(draw, (W // 2, 900), CAPTION[0], 52, fade(SUMI, v0), False, "ma")
        return img


def resolve_photos(arg):
    """--photos の名を写真の道に直す。確かめ表で通っていない名や無い写真があれば None（使わずに止める）。"""
    names = SHOWN if arg is None else tuple(n.strip() for n in arg.split(",") if n.strip())
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
    ap.add_argument("--photos", help="使う写真（例 p01,p09）。確かめ表で通った物だけ。省くと SHOWN")
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
