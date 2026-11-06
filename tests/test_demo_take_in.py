"""届いた手の映像と声を、差し込む口の置き場へ入れる命令（demo.take_in）の床。

見る事: 名前ちょうどの物を入れる／撮り直しと分けて撮った物は候補として名前を言い、--pick で選ぶ（, で並べるとつなぐ）／
撮影の情報と手の映像の音を外す／決まりに合わない物は名指しして 3 で止め、置き場に入れない／--dry-run は置き場に触らない。
本物の置き場（repo の out/）には書かない（ROOT を一時の所に向ける）。作り物の映像と音で見る。
"""
import contextlib
import io
import pathlib
import shutil
import subprocess
import tempfile

from demo import take_in
from demo.script import SLOT_DIR

if shutil.which("ffmpeg"):
    def video(path, seconds, size="1920x1080"):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc=size={size}:rate=30:duration={seconds}",
                        "-f", "lavfi", "-i", f"sine=f=440:d={seconds}", "-shortest", "-metadata", "creation_time=2026-11-06T10:00:00Z",
                        "-metadata", "location=+35.0000+139.0000/", str(path)], check=True)

    def voice(path, seconds):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono:d=1", "-f", "lavfi",
                        "-i", f"sine=f=330:d={seconds}:sample_rate=48000", "-filter_complex", "[0][1]concat=n=2:v=0:a=1",
                        "-metadata", "creation_time=2026-11-06T10:00:00Z", "-c:a", "aac", str(path)], check=True)

    def tags(path):
        return subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format_tags:stream=codec_type", "-of", "compact", str(path)],
                              capture_output=True, text=True).stdout

    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        got, root = tmp / "got", tmp / "repo"
        got.mkdir()
        video(got / "A.mp4", 7)
        video(got / "D-1.mov", 3)
        video(got / "D-2.mov", 3)
        video(got / "B.mp4", 7, size="1080x1920")   # 縦で撮った物（決まりに合わない）
        voice(got / "A1.m4a", 3)
        voice(got / "A4-2.m4a", 5)                   # 撮り直しだけがある（選ぶ物）
        real_root = take_in.ROOT
        take_in.ROOT = root
        try:
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = take_in.main([str(got), "--dry-run"])
            assert rc == 3 and "手 B" in err.getvalue() and ("16:9" in err.getvalue() or "幅" in err.getvalue()), err.getvalue()
            assert "D（候補: D-1.mov・D-2.mov" in out.getvalue() and "A4（候補: A4-2.m4a" in out.getvalue(), out.getvalue()
            assert not (root / SLOT_DIR).exists(), "合わない物がある時は置き場に入れない"
            (got / "B.mp4").unlink()
            out = io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
                rc = take_in.main([str(got), "--pick", "D=D-1.mov,D-2.mov", "--pick", "A4=A4-2.m4a"])
            assert rc == 0, out.getvalue()
            slot = root / SLOT_DIR
            assert sorted(p.name for p in slot.iterdir()) == ["A.mp4", "A1.m4a", "A4.m4a", "D.mp4"], sorted(slot.iterdir())
            assert "まだ届いていない" in out.getvalue() and "C" in out.getvalue()
            d = tags(slot / "D.mp4")
            assert "audio" not in d and "creation_time" not in d and "location" not in d, d
            assert 5.9 < float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(slot / "D.mp4")],
                                              capture_output=True, text=True).stdout) < 6.2, "D-1 と D-2 をつないで 1 本に"
            assert "creation_time" not in tags(slot / "A1.m4a")
            assert (got / "D-1.mov").exists(), "届いた物は触らない"
            # 名前の分からない --pick は 4
            with contextlib.redirect_stderr(io.StringIO()):
                assert take_in.main([str(got), "--pick", "Z=A.mp4"]) == 4
        finally:
            take_in.ROOT = real_root
print("ok 届いた物は名前ちょうどで、撮影の情報と音を外して入り、合わない物は名指しして止まる")
