"""最初の場面: 問い「こんなおもちゃを知っていますか？」と、白を背景に手で持った職人のおもちゃの動画。

使い方: python -m demo.opening --out <repo の外の場所>/opening.mp4 [--sheet 要のコマの一覧.jpg] [--video 動画のファイル]
exit: 0 = 書き出せた / 4 = 動画が決まりに合わない・ffmpeg が無い（このリポの検査の決まりに合わせる）。

決めた事と理由:
- 本人の指示（11-05 20:07）「デモの始まりは、『こんなおもちゃを知っていますか？』で、おもちゃを何個か職人が作ったものを白を背景に写す。小ささを見せるために手で持つ」。
- 職人のおもちゃの動画は手元に無い。作り物で埋めない（生成した絵・見本の絵・紙の型紙の写真を職人の物として使わない）。
  無い間は場所だけ空け、白い地に問いの字と、下に小さく印を出す。本人だけが見る試作の印で、この印が残っている間は外へ出せない。
  demo.build が build.json の placeholder と not_for_release に載せる。
- 動画のファイルを VIDEO の道に置けば、そこへ入る。git に入れない（out/ の下）。音は捨てる（J-022）。
  決まり（16:9・幅 1280 以上・DURATION 秒以上）に合わない時は 4 で止める。崩れた絵を黙って出さないため。
- 問いの字と動画は重ねない。上に字、下に動画を置く。白を背景に撮った動画なら、地が続いて見える。
- frame(t) は時刻だけから 1 コマを描く純関数（場面 1 と同じ）。動画は書き出しの前に 1 秒 30 枚に割り、時刻から 1 枚を選ぶ。
"""
import argparse
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw

from demo.flip import FPS, H, ROOT, SUMI, W, contact_sheet, ease, render, text

QUESTION = "こんなおもちゃを知っていますか？"
PLACEHOLDER = "（ここに職人のおもちゃの動画が入ります）"
VIDEO = ROOT / "out/demo/opening/toys.mp4"     # 職人のおもちゃの動画の置き場（git に入れない）
DURATION = 12.0
MIN_WIDTH = 1280
WHITE = (255, 255, 255)
VIDEO_BOX = (178, 180, 1742, 1060)             # 動画を置く枠。16:9 で、上に問いの字の余白
# 合図の表。絵の動きも字幕もここだけを読む。
CUES = {
    "in": (0.0, 1.2),      # 問いの字が現れる
    "video": (0.8, 2.0),   # 動画（無い間は印）が現れる
}


def has_video(path=VIDEO):
    return pathlib.Path(path).exists()


def _probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:format=duration",
                        "-of", "json", str(path)], capture_output=True, text=True)
    d = json.loads(r.stdout or "{}")
    stream = (d.get("streams") or [{}])[0]
    return stream.get("width", 0), stream.get("height", 0), float(d.get("format", {}).get("duration", 0))


def video_problem(path, probe=_probe):
    """置かれた動画が決まりに合わない時に、その理由を返す。合えば None。"""
    width, height, seconds = probe(path)
    if not width or not height:
        return f"動画が読めない: {path}"
    if abs(width / height - 16 / 9) > 0.01:
        return f"動画の縦横が 16:9 でない（{width}×{height}）"
    if width < MIN_WIDTH:
        return f"動画の幅が {MIN_WIDTH} より小さい（{width}）"
    if seconds < DURATION:
        return f"動画が {DURATION:.0f} 秒より短い（{seconds:.1f} 秒）"
    return None


def _ink(v):
    """白い地の上の墨の色（flip.fade は紙の地の色へ混ぜるので、ここでは使わない）。"""
    return tuple(round(255 + (SUMI[i] - 255) * v) for i in range(3))


class Opening:
    duration = DURATION
    ground = WHITE     # 場面の頭の溶けを、紙でなく白から始める

    def __init__(self, frames=()):
        self.frames = list(frames)    # 動画を 1 秒 30 枚に割った絵のファイルの並び。空なら印を出す

    def _p(self, t, cue):
        a, b = CUES[cue]
        return ease((t - a) / (b - a))

    def frame(self, t):
        """時刻 t（秒）の 1 コマ。前のコマに依らない。"""
        img = Image.new("RGB", (W, H), WHITE)
        draw = ImageDraw.Draw(img)
        a, v = self._p(t, "in"), self._p(t, "video")
        if not self.frames:
            if a > 0:
                text(draw, (W // 2, H // 2 - 110), QUESTION, 72, _ink(a), False, "ma")
            if v > 0:
                text(draw, (W // 2, H // 2 + 40), PLACEHOLDER, 28, _ink(0.55 * v), False, "ma")
            return img
        if a > 0:
            text(draw, (W // 2, 62), QUESTION, 60, _ink(a), False, "ma")
        if v > 0:
            x0, y0, x1, y1 = VIDEO_BOX
            with Image.open(self.frames[min(len(self.frames) - 1, int(t * FPS))]) as im:
                shot = im.convert("RGB").resize((x1 - x0, y1 - y0))
            if v < 1:
                shot = Image.blend(Image.new("RGB", shot.size, WHITE), shot, v)
            img.paste(shot, (x0, y0))
        return img


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True, help="mp4 の置き場（repo の外）")
    ap.add_argument("--sheet", help="要のコマの一覧の画像")
    ap.add_argument("--video", default=str(VIDEO), help="職人のおもちゃの動画（省くと決まった置き場）")
    a = ap.parse_args(argv)
    times = (0.4, 1.0, 1.6, 2.4, 4.0, 6.0, 8.0, 10.0, 11.8)
    video = pathlib.Path(a.video)
    if not video.exists():
        print("注意: 職人のおもちゃの動画が無いので、印を出す。この動画は外へ出せない", file=sys.stderr)
        scene = Opening()
        if a.sheet:
            contact_sheet(scene, a.sheet, times)
        return render(scene, pathlib.Path(a.out))
    if not shutil.which("ffmpeg"):
        print("検査できない: ffmpeg が無い", file=sys.stderr)
        return 4
    problem = video_problem(video)
    if problem:
        print(f"検査できない: {problem}", file=sys.stderr)
        return 4
    with tempfile.TemporaryDirectory(prefix="opening-") as tmp:
        x0, y0, x1, y1 = VIDEO_BOX
        r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-t", f"{DURATION}", "-i", str(video), "-an",
                            "-vf", f"fps={FPS},scale={x1 - x0}:{y1 - y0}", "-q:v", "2", f"{tmp}/%05d.jpg"], capture_output=True, text=True)
        frames = sorted(pathlib.Path(tmp).glob("*.jpg"))
        if r.returncode != 0 or not frames:
            print(f"検査できない: 動画を割れない（{r.stderr.strip()[:200]}）", file=sys.stderr)
            return 4
        scene = Opening(frames)
        if a.sheet:
            contact_sheet(scene, a.sheet, times)
        return render(scene, pathlib.Path(a.out))


if __name__ == "__main__":
    sys.exit(main())
