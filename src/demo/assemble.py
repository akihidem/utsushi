"""場面の動画を台本の順につなぎ、3 分の床を見る。

使い方: python -m demo.assemble --out <repo の外>/demo.mp4 scene1.mp4 scene2.mp4 ...
exit: 0 = つないで 3 分以内 / 3 = 3 分を超えた（つないだ物は残す。どれだけ超えたかを出す）/ 4 = ffmpeg が無い・場面が読めない。

決めた事と理由:
- 長さの床をここに置く。提出の要項が 3 分までで、場面を足すたびに手で足し算すると漏れるため。
- つなぐ時に作り直す（再エンコード）。画面の録画とコードの場面は大きさや fps が違う事があり、
  そのままの連結（-c copy）だと途中で崩れる。どの場面も 1920x1080・30fps にそろえる。
- 本人の声の語り（本人の決定 11-06「語りは本人が自分の声で読む」）は voices で 1 文ずつ重ねる。場面の動画の音は今までどおり使わない。
- 語りの声が鳴る間だけ、曲（仮の拍も）を DUCK_DB まで下げる（ダッキング）。声を曲に埋もれさせないため。
  下げる所の前後 DUCK_RAMP 秒で、なだらかに下げて戻す（急に変えると、曲が切れたように聞こえる）。声の大きさは変えない。
  値は一般的な目安（語りの下の曲を 10〜15dB 下げる）から取った見込みで、本物の曲と本人の声ではまだ聞いていない。
"""
import argparse
import pathlib
import shutil
import subprocess
import sys

LIMIT = 180.0
W, H, FPS = 1920, 1080, 30
DUCK_DB, DUCK_RAMP = -12.0, 0.4     # 語りの間の曲の下げ幅（dB）と、下げて戻す秒


def duck_gain(windows, db=DUCK_DB, ramp=DUCK_RAMP):
    """曲の音の大きさの式（ffmpeg の volume の eval=frame の式）。windows: 声が鳴る (始め, 終わり) の並び。無ければ None。"""
    if not windows:
        return None
    low = 10 ** (db / 20)
    terms = [f"(1-{1 - low:.4f}*clip(min((t-{a - ramp:.3f})/{ramp},({b + ramp:.3f}-t)/{ramp}),0,1))" for a, b in windows]
    return "*".join(terms)


def duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return None


def assemble(scenes, out, audio=None, seconds=None, audio_start=0.0, fade_at=None, voices=(), duck=(), sfx=()):
    """seconds: 場面ごとの長さ（曲の小節に合わせる時）。余れば最後のコマで止め、足りなければ切る。どの場面も最後は止めて読む間なので。
    audio_start: 曲のどこから使うか。fade_at: 動画の何秒から音を 2 秒で消すか（問いの札の前で消すため）。
    voices: 本人の声の語り [(ファイル, 動画の何秒から)]。duck: 曲を下げる (始め, 終わり) の並び（語りの声が鳴る間）。
    sfx: 効果音 [(ファイル, 動画の何秒から, 大きさ dB)]。声と同じく、その時刻まで遅らせて重ねる（曲は下げない）。"""
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
        fit = ""
        if seconds:
            fit = f",tpad=stop_mode=clone:stop_duration={max(0.0, seconds[i] - lens[i]):.3f},trim=duration={seconds[i]:.3f},setpts=PTS-STARTPTS"
        parts.append(f"[{i}:v]scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,"
                     f"fps={FPS},setsar=1{fit}[v{i}]")
    chain = "".join(f"[v{i}]" for i in range(len(scenes)))
    fil = ";".join(parts) + f";{chain}concat=n={len(scenes)}:v=1:a=0[v]"
    sound = []
    n_in = len(scenes)
    if audio:
        args += ["-i", str(audio)]
        cut = f"atrim=start={audio_start:.3f},asetpts=PTS-STARTPTS," if audio_start else ""
        gone = f",afade=t=out:st={fade_at:.3f}:d=2" if fade_at is not None else ""
        gain = duck_gain(duck)
        down = f",volume='{gain}':eval=frame" if gain else ""
        fil += f";[{n_in}:a]{cut}apad{down}{gone}[m]"
        n_in += 1
    mixed = ["[m]"] if audio else []
    for i, (path, at) in enumerate(voices):
        # 声は 1 文ずつ、その場面の時刻まで遅らせて重ねる。大きさは変えない（下げるのは曲の方だけ）。
        args += ["-i", str(path)]
        ms = round(at * 1000)
        fil += f";[{n_in}:a]aresample=48000,adelay={ms}:all=1,apad[s{i}]"
        mixed.append(f"[s{i}]")
        n_in += 1
    for i, (path, at, gain) in enumerate(sfx):
        args += ["-i", str(path)]
        fil += f";[{n_in}:a]aresample=48000,volume={gain:.1f}dB,adelay={round(at * 1000)}:all=1,apad[x{i}]"
        mixed.append(f"[x{i}]")
        n_in += 1
    if mixed:
        # 混ぜる時に大きさを割らない（normalize=0）。割ると、声が入るたびに曲の大きさが変わる。
        fil += f";{''.join(mixed)}amix=inputs={len(mixed)}:normalize=0[a]" if len(mixed) > 1 else f";{mixed[0]}anull[a]"
        sound = ["-map", "[a]", "-c:a", "aac", "-b:a", "192k", "-t", f"{sum(seconds or lens):.3f}"]
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args, "-filter_complex", fil, "-map", "[v]", *sound,
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", str(out)], capture_output=True, text=True)
    if r.returncode != 0:
        print(f"検査できない: つなげない（{r.stderr.strip()[:200]}）", file=sys.stderr)
        return 4
    total = duration(out) or sum(seconds or lens)
    for s, d in zip(scenes, seconds or lens):
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
