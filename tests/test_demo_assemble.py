"""demo.assemble の床: 大きさの違う場面をつなげ、3 分を超えたら 3 で止まる事を見る。

場面は ffmpeg の色の板で作る（網も実の動画も使わない）。長さの床を見るために長い場面も要るが、
3 分を越える物を作ると遅いので、床の値（LIMIT）を小さくして同じ道を通す。
"""
import pathlib
import subprocess
import tempfile

from demo import assemble


def board(path, seconds, size):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"color=c=white:s={size}:r=25:d={seconds}",
                    "-pix_fmt", "yuv420p", str(path)], check=True)


with tempfile.TemporaryDirectory() as tmp:
    t = pathlib.Path(tmp)
    board(t / "a.mp4", 1, "1920x1080")
    board(t / "b.mp4", 1, "1280x720")  # 画面の録画のように大きさも fps も違う場面
    assert assemble.main(["--out", str(t / "ok.mp4"), str(t / "a.mp4"), str(t / "b.mp4")]) == 0
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=width,height,r_frame_rate", "-of", "csv=p=0",
                            str(t / "ok.mp4")], capture_output=True, text=True).stdout.strip()
    assert probe == "1920,1080,30/1", probe
    assert 1.9 < assemble.duration(t / "ok.mp4") < 2.1
    # 曲を重ねる: 映像より短い音は無音で足し、長さは映像に合わせる（曲が動画を伸ばさない）
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=0.5",
                    str(t / "s.m4a")], check=True)
    assert assemble.main(["--out", str(t / "music.mp4"), "--audio", str(t / "s.m4a"), str(t / "a.mp4"), str(t / "b.mp4")]) == 0
    kinds = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "csv=p=0",
                            str(t / "music.mp4")], capture_output=True, text=True).stdout.split()
    assert sorted(kinds) == ["audio", "video"], kinds
    assert 1.9 < assemble.duration(t / "music.mp4") < 2.2
    # 曲の小節へ寄せる時: 場面ごとの長さを渡すと、余れば最後のコマで止め、足りなければ切る。音は言った所から消える
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=6",
                    str(t / "long.m4a")], check=True)
    assert assemble.assemble([t / "a.mp4", t / "b.mp4"], t / "fit.mp4", t / "long.m4a", seconds=[1.5, 0.5], audio_start=1.0, fade_at=0.0) == 0
    assert 1.9 < assemble.duration(t / "fit.mp4") < 2.2
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(t / "fit.mp4"), "-ac", "1", "-ar", "8000", "-f", "s16le", "-"], capture_output=True).stdout
    assert len(raw) > 8000 and max(abs(int.from_bytes(raw[i:i + 2], "little", signed=True)) for i in range(len(raw) - 400, len(raw) - 2, 2)) < 2000, "音が消えていない"
    assemble.LIMIT = 1.5
    assert assemble.main(["--out", str(t / "long.mp4"), str(t / "a.mp4"), str(t / "b.mp4")]) == 3
    assert assemble.main(["--out", str(t / "x.mp4"), str(t / "missing.mp4")]) == 4
print("ok")
