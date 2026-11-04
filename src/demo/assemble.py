"""場面の動画を台本の順につなぎ、3 分の床を見る。

使い方: python -m demo.assemble --out <repo の外>/demo.mp4 scene1.mp4 scene2.mp4 ...
exit: 0 = つないで 3 分以内 / 3 = 3 分を超えた（つないだ物は残す。どれだけ超えたかを出す）/ 4 = ffmpeg が無い・場面が読めない。

決めた事と理由:
- 長さの床をここに置く。提出の要項が 3 分までで、場面を足すたびに手で足し算すると漏れるため。
- つなぐ時に作り直す（再エンコード）。画面の録画とコードの場面は大きさや fps が違う事があり、
  そのままの連結（-c copy）だと途中で崩れる。どの場面も 1920x1080・30fps にそろえる。
"""
import argparse
import pathlib
import shutil
import subprocess
import sys

LIMIT = 180.0
W, H, FPS = 1920, 1080, 30


def duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return None


def assemble(scenes, out, audio=None):
    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        print("検査できない: ffmpeg か ffprobe が無い", file=sys.stderr)
        return 4
    lens = []
    for s in scenes:
        d = duration(s)
        if d is None:
            print(f"検査できない: 場面が読めない {s}", file=sys.stderr)
            return 4
        lens.append(d)
    out.parent.mkdir(parents=True, exist_ok=True)
    # 大きさをそろえて映像だけを concat する。場面の音は使わない（声を入れない決まり J-022、コードの場面は音が無い）。
    # 曲は audio で 1 本だけ重ね、映像の長さ（場面の長さの和）で切る。短い曲は apad で無音を足す。
    # apad と -shortest の組は filter_complex の中だと終わらない（試験で止まった）ので、長さを -t で決める。
    args, parts = [], []
    for i, s in enumerate(scenes):
        args += ["-i", str(s)]
        parts.append(f"[{i}:v]scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,"
                     f"fps={FPS},setsar=1[v{i}]")
    chain = "".join(f"[v{i}]" for i in range(len(scenes)))
    fil = ";".join(parts) + f";{chain}concat=n={len(scenes)}:v=1:a=0[v]"
    sound = []
    if audio:
        args += ["-i", str(audio)]
        fil += f";[{len(scenes)}:a]apad[a]"
        sound = ["-map", "[a]", "-c:a", "aac", "-b:a", "192k", "-t", f"{sum(lens):.3f}"]
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args, "-filter_complex", fil, "-map", "[v]", *sound,
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", str(out)], capture_output=True, text=True)
    if r.returncode != 0:
        print(f"検査できない: つなげない（{r.stderr.strip()[:200]}）", file=sys.stderr)
        return 4
    total = duration(out) or sum(lens)
    for s, d in zip(scenes, lens):
        print(f"{d:6.2f} 秒  {pathlib.Path(s).name}")
    print(f"計 {total:.2f} 秒（床 {LIMIT:.0f} 秒）")
    if total > LIMIT + 0.05:
        print(f"FAIL D.length 床 {LIMIT:.0f} 秒を {total - LIMIT:.2f} 秒超えた", file=sys.stderr)
        return 3
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--audio", help="曲のファイル（有れば重ねる）")
    ap.add_argument("scenes", nargs="+")
    a = ap.parse_args(argv)
    return assemble([pathlib.Path(s) for s in a.scenes], pathlib.Path(a.out), a.audio)


if __name__ == "__main__":
    sys.exit(main())
