"""同じ記録に声とカメラの区切りが同時に 2 つ届いても、同じ番号を取って前の区切りを上書きしない（omochae.voice_text の put_voice_clip・put_cam_clip）。
#642 の確かめの気づき（11-08）「_free_slot には錠が無く、同時に 2 つ届くと同じ番号を取りうる」。空いた番号を見てから置くまでの間に、
ほかの受け取りが同じ番号を置いた形を、番号を見る所（_free_slot）が 1 度だけ古い答え（もう置かれた番号）を返す形で作る。

見る事:
1. 声の区切り: 古い答えで同じ番号に当たっても、前の t1.mka を上書きせず、次の空いた番号（t2.mka）に置く。前の音の中身は替わらない
2. カメラの区切り: 同じく k1 を上書きせず k2 に置く
3. 置き場に一時のファイルが残らない。5 つの上限は今のまま（6 つ目は断る）。途中で止まって残った一時のファイルは 72 時間で掃除が消す
終了: 0 = 通る / 1 = 落ちる（assert）/ 4 = ffmpeg が無い（確かめられない）
"""
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

tmp = pathlib.Path(tempfile.mkdtemp())
os.environ["OMOCHAE_DATA"] = str(tmp / "data")
os.environ["OMOCHAE_SAMPLES"] = "0"
os.environ.pop("OMOCHAE_ASR_PYTHON", None)
if not shutil.which("ffmpeg"):
    print("検査できない: ffmpeg が無い", file=sys.stderr)
    sys.exit(4)

from omochae import records, voice_text  # noqa: E402

G = "NDL-1187053-R0000005-L"


def clip(video=False, hz=440):
    out = tmp / f"c{time.time_ns()}.webm"
    ins = ["-f", "lavfi", "-i", "testsrc=size=64x48:rate=5:duration=1"] if video else ["-f", "lavfi", "-i", f"sine=frequency={hz}:duration=1"]
    codec = ["-c:v", "libvpx"] if video else ["-c:a", "libopus"]
    subprocess.run(["ffmpeg", "-v", "error", "-y", *ins, *codec, "-f", "webm", str(out)], check=True, capture_output=True, timeout=120)
    return out.read_bytes()


def new_record():
    rid, fails = records.add({"source_id": G, "hypothesis_id": "H-A", "sheet_version": 1, "result": "動いた"})
    assert rid and not fails, fails
    return rid


real = voice_text._free_slot


def stale_once(answer):
    """1 度目だけ古い答え（ほかの受け取りがもう置いた番号）を返し、後は本当の答えを返す。"""
    state = {"left": 1}

    def slot(rid, kind):
        if state["left"]:
            state["left"] -= 1
            return answer
        return real(rid, kind)
    return slot


# 1. 声の区切り
rid = new_record()
vd = voice_text.voice_dir(rid)
assert voice_text.put_voice_clip(rid, clip(hz=440), "webm")[0] == "t1.mka"
before = (vd / "t1.mka").read_bytes()
voice_text._free_slot = stale_once(1)
name, why = voice_text.put_voice_clip(rid, clip(hz=880), "webm")
voice_text._free_slot = real
assert name == "t2.mka", (name, why, "同じ番号に当たったら、次の空いた番号に置く")
assert (vd / "t1.mka").read_bytes() == before, "前の声の区切りを上書きしない"
# 2. カメラの区切り
assert voice_text.put_cam_clip(rid, clip(video=True), "webm")[0] == "k1.webm"
kbefore = (vd / "k1.webm").read_bytes()
voice_text._free_slot = stale_once(1)
name, why = voice_text.put_cam_clip(rid, clip(video=True), "webm")
voice_text._free_slot = real
assert name == "k2.webm", (name, why)
assert (vd / "k1.webm").read_bytes() == kbefore, "前のカメラの区切りを上書きしない"
# 3. 一時のファイルが残らない・上限は今のまま
assert sorted(p.name for p in vd.iterdir()) == ["k1.webm", "k2.webm", "t1.mka", "t2.mka"], sorted(p.name for p in vd.iterdir())
for n in (3, 4, 5):
    assert voice_text.put_voice_clip(rid, clip(), "webm")[0] == f"t{n}.mka"
assert voice_text.put_voice_clip(rid, clip(), "webm")[0] is None, "6 つ目は断る"
assert not [p for p in vd.iterdir() if p.name.startswith(".")], "一時のファイルが残らない"
# 置く途中で止まって残った一時のファイルは、72 時間を過ぎたら掃除が消す（若い物は残す）
old, young = vd / ".tmp-old.mka", vd / ".tmp-young.webm"
old.write_bytes(b"x")
young.write_bytes(b"x")
past = time.time() - voice_text.LIMIT - 60
os.utime(old, (past, past))
voice_text.sweep_clips()
assert not old.exists() and young.exists(), "古い一時のファイルだけ消す"
young.unlink()
print("ok 区切りが同時に届いても同じ番号で上書きしない: 声・カメラ・一時のファイルなし・上限は今のまま")
