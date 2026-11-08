"""押した時だけ録る声とカメラの短い区切りを受けて、字にしてから消す server 側（omochae.voice_text の t・k の名と掃除）。
本人の言葉 11-08「声も送って解析に使う形にする。カメラの映像は、押した時の短い区切りだけ。」・窓口の決め「声とカメラそれぞれ 5 つまで」・
本人の決め 72 時間（345）と「全部残していいことにしたい。」（349）。受け口と録る頁は別の枝（web.play_server）で、ここは境目の関数を見る。
本物の字にする道具は使わない（作り物）。設計は grove の state/voice-clip-names-design-20261108.md。

見る事:
1. 声の区切り（put_voice_clip）: webm と mp4 の声が voice/t<n>.mka に写り（0600・箱 0700）、元の形のファイルは残らず、撮影の情報も残らない。
   頭のバイトが違う・2MB を越える・声の流れが無い・知らない ext・記録が無い・名の形の違う rid は断る。6 つ目は、字にした後も消した後も断る
2. カメラの区切り（put_cam_clip）: voice/k<n>.<webm|mp4> に、絵の流れだけが撮影の情報なしで置かれる。5MB を越える・頭のバイトが違う・
   読めない物・6 つ目（読み終えた後も）は断る
3. pending が t を拾い、字にしたら音が消える（t<n>.transcript.json）。k は字にする道具に入らない
4. clips_waiting・clip_wait（最後の理由で上書き）・clip_done（k と控えが消え、読み終えた印が残る）・clip_drop（人が写っている時に今すぐ消し、
   印に why・at）。名の形の違う name・空の理由は断る
5. sweep_clips: 72 時間の前は残る・過ぎた k は読まずに消え、印に why・at と最後の理由 wait。読み終えた物には触らない
6. 公開の場の大きさの合計（media_bytes）に t と k が入り、控えの json は入らない
7. 取り下げで t・k・字・印が全部消える
8. サーバ（Worker）は立てた時に、sweep と並べて sweep_clips も回す。video_up の掃除も同じ
9. 頁へ返す道（media_of）と束に t・k が出ない
終了: 0 = 通る / 1 = 落ちる（assert）/ 4 = ffmpeg が無い（確かめられない）
"""
import json
import os
import pathlib
import shutil
import stat
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

from omochae import engine_bundle, records, voice_text  # noqa: E402
from web import techo_site, video_up  # noqa: E402

G = "NDL-1187053-R0000005-L"
PLACE = "+35.6000+139.7000"
PLAIN = "筒の内側に割り箸を貼ると押し上げやすい"
# 作り物の字にする道具（test_voice_text と同じ形）。.mka だけを受け、字にした回数を数える
calls = tmp / "calls.txt"
fake = tmp / "fake_asr.py"
fake.write_text(f"""import json, sys
if sys.argv[1] == "--check":
    sys.exit(0)
assert sys.argv[1].endswith(".mka")
with open({str(calls)!r}, "a") as f:
    f.write(sys.argv[1] + "\\n")
json.dump({{"model": sys.argv[2], "language": "ja", "segments": [{{"start": 0.0, "end": 1.0, "text": {PLAIN!r}}}]}}, sys.stdout, ensure_ascii=False)
""", encoding="utf-8")
voice_text.ASR_WORKER = fake


def clip(ext, audio=True, video=False, seconds=1):
    """作り物の区切り。撮影の情報（題と位置）を入れて、写した後に残らない事を見る。"""
    out = tmp / f"c{time.time_ns()}.{ext}"
    ins, codecs = [], []
    if video:
        ins += ["-f", "lavfi", "-i", f"testsrc=size=64x48:rate=5:duration={seconds}"]
        codecs += ["-c:v", "libvpx"] if ext == "webm" else ["-c:v", "libx264", "-pix_fmt", "yuv420p"]
    if audio:
        ins += ["-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}"]
        codecs += ["-c:a", "libopus"] if ext == "webm" else ["-c:a", "aac"]
    meta = ["-metadata", "title=secret-place", "-metadata", f"location={PLACE}"]
    if ext == "mp4":
        meta += ["-metadata", f"com.apple.quicktime.location.ISO6709={PLACE}+010.000/", "-movflags", "use_metadata_tags"]
    subprocess.run(["ffmpeg", "-v", "error", "-y", *ins, *codecs, *meta, "-f", ext, str(out)], check=True, capture_output=True, timeout=120)
    data = out.read_bytes()
    assert PLACE.encode() in data and b"secret-place" in data, "作り物に撮影の情報が入っていない"
    return data


def streams(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(path)], capture_output=True, text=True, check=True)
    return [s["codec_type"] for s in json.loads(r.stdout)["streams"]]


def new_record():
    rid, fails = records.add({"source_id": G, "hypothesis_id": "H-A", "sheet_version": 1, "result": "動いた"})
    assert rid and not fails, fails
    return rid


def clean(path):
    data = pathlib.Path(path).read_bytes()
    return PLACE.encode() not in data and b"secret-place" not in data


# 1. 声の区切り
rid = new_record()
vd = voice_text.voice_dir(rid)
for n, ext in ((1, "webm"), (2, "mp4")):
    name, why = voice_text.put_voice_clip(rid, clip(ext), ext)
    assert name == f"t{n}.mka", (ext, why)
    t = vd / name
    assert streams(t) == ["audio"] and clean(t), (ext, "声だけを、撮影の情報なしで写す")
    assert stat.S_IMODE(t.stat().st_mode) == 0o600 and stat.S_IMODE(vd.stat().st_mode) == 0o700, "作る側だけが読める"
assert sorted(p.name for p in vd.iterdir()) == ["t1.mka", "t2.mka"], "元の webm・mp4 は置かない"
for data, ext, word in ((b"\x00" * 64, "webm", "頭のバイト"), (clip("mp4"), "webm", "頭のバイト"), (clip("webm"), "mp4", "頭のバイト"),
                        (clip("webm")[:4] + b"\x00" * (voice_text.VOICE_CLIP_BYTES + 1), "webm", "2MB"), (clip("webm", audio=False, video=True), "webm", "声"),
                        (clip("webm"), "ogg", "形")):
    name, why = voice_text.put_voice_clip(rid, data, ext)
    assert name is None and why, (ext, word, "断る")
assert voice_text.put_voice_clip("R-9999", clip("webm"), "webm")[0] is None, "記録が無い所には置かない"
assert voice_text.put_voice_clip("../R-0001", clip("webm"), "webm")[0] is None, "名の形の違う記録の番号は受けない"
assert sorted(p.name for p in vd.iterdir()) == ["t1.mka", "t2.mka"], "断った物は何も残さない"

# 3. pending が t を拾い、字にしたら音が消える。k は入らない
assert [p.name for p in voice_text.pending()] == ["t1.mka", "t2.mka"]
os.environ["OMOCHAE_ASR_PYTHON"] = sys.executable
t1 = vd / "t1.mka"
assert voice_text.transcribe(t1, still=lambda: voice_text.still_wanted(t1)) == "done"
assert not t1.exists() and voice_text.text_of(t1).name == "t1.transcript.json" and PLAIN in voice_text.text_of(t1).read_text(encoding="utf-8")
os.environ.pop("OMOCHAE_ASR_PYTHON")
# 6 つ目は、字にした後も消した後も断る（番号は字と印が持ち続ける）
for n in (3, 4, 5):
    assert voice_text.put_voice_clip(rid, clip("webm"), "webm")[0] == f"t{n}.mka"
(vd / "t2.mka").unlink()
voice_text.dropped_of(vd / "t2.mka").write_text("{}", encoding="utf-8")
name, why = voice_text.put_voice_clip(rid, clip("webm"), "webm")
assert name is None and "5" in why, ("6 つ目は受けない", why)

# 2. カメラの区切り
cam = new_record()
cd = voice_text.voice_dir(cam)
for n, ext in ((1, "webm"), (2, "mp4")):
    name, why = voice_text.put_cam_clip(cam, clip(ext, audio=True, video=True), ext)
    assert name == f"k{n}.{ext}", (ext, why)
    k = cd / name
    assert streams(k) == ["video"] and clean(k), (ext, "絵の流れだけを、撮影の情報なしで置く（音も落とす）")
    assert stat.S_IMODE(k.stat().st_mode) == 0o600
for data, ext in ((b"\x00" * 64, "mp4"), (clip("webm", video=True), "mp4"), (clip("webm", video=True)[:4] + b"\x00" * (voice_text.CAM_CLIP_BYTES + 1), "webm"),
                  (clip("webm", video=True)[:4] + b"\x00" * 200, "webm"), (clip("mp4", video=True), "mov")):
    assert voice_text.put_cam_clip(cam, data, ext)[0] is None, (ext, "断る")
assert voice_text.pending() == [vd / "t3.mka", vd / "t4.mka", vd / "t5.mka"], "k は字にする道具に入らない"

# 4. 待ち・理由の控え・読み終え
assert voice_text.clips_waiting(cam) == ["k1.webm", "k2.mp4"]
assert voice_text.clip_wait(cam, "k1.webm", "今日の上限") and voice_text.clip_wait(cam, "k1.webm", "人の確かめ待ち")
assert json.loads((cd / "k1.wait.json").read_text(encoding="utf-8"))["why"] == "人の確かめ待ち", "最後の理由で上書き"
assert voice_text.clip_done(cam, "k2.mp4") and not (cd / "k2.mp4").exists() and (cd / "k2.done.json").exists(), "読み終えたら消し、印を残す"
assert voice_text.clips_waiting(cam) == ["k1.webm"]
for bad in ("../k1.webm", "k1.mka", "t1.mka", "k1", "k1.webm/x"):
    assert not voice_text.clip_wait(cam, bad, "今日の上限") and not voice_text.clip_done(cam, bad), bad
assert not voice_text.clip_done(cam, "k9.webm"), "無い物は読み終えにしない"
for n in (3, 4, 5):
    assert voice_text.put_cam_clip(cam, clip("webm", audio=False, video=True), "webm")[0] == f"k{n}.webm"
assert voice_text.put_cam_clip(cam, clip("webm", audio=False, video=True), "webm")[0] is None, "6 つ目は、読み終えた後も受けない"

# 4 の続き: 人が写っている時は、読まずに今すぐ消す（clip_drop・受け口の枝の進め役の確かめと Claude の答えから呼ぶ）
dr = new_record()
dd = voice_text.voice_dir(dr)
assert voice_text.put_cam_clip(dr, clip("webm", video=True), "webm")[0] == "k1.webm" and voice_text.clip_wait(dr, "k1.webm", "人の確かめ待ち")
for bad, why in (("k1.webm", ""), ("k1.webm", "   "), ("../k1.webm", "人が写っている"), ("k1.mka", "人が写っている"), ("k2.webm", "人が写っている")):
    assert not voice_text.clip_drop(dr, bad, why), (bad, why, "断る")
assert (dd / "k1.webm").exists(), "断った時は消さない"
assert voice_text.clip_drop(dr, "k1.webm", "人が写っている") and not (dd / "k1.webm").exists() and not (dd / "k1.wait.json").exists(), "今すぐ消し、控えも消す"
mark = json.loads((dd / "k1.dropped.json").read_text(encoding="utf-8"))
assert mark["why"] == "人が写っている" and mark["at"] and stat.S_IMODE((dd / "k1.dropped.json").stat().st_mode) == 0o600, mark
assert not voice_text.clip_drop(dr, "k1.webm", "人が写っている") and voice_text.clips_waiting(dr) == [], "2 度は消さない"
assert voice_text.put_cam_clip(dr, clip("webm", video=True), "webm")[0] == "k2.webm", "消した番号は印が持ち続ける"

# 5. 72 時間の掃除
past = time.time() - voice_text.LIMIT - 60
os.utime(cd / "k1.webm", (past, past))
gone = voice_text.sweep_clips()
assert gone == [cd / "k1.webm"] and not (cd / "k1.webm").exists() and (cd / "k3.webm").exists(), "72 時間を過ぎた物だけ消す"
mark = json.loads((cd / "k1.dropped.json").read_text(encoding="utf-8"))
assert "読まずに消した" in mark["why"] and mark["at"] and mark["wait"] == "人の確かめ待ち", mark
assert not (cd / "k1.wait.json").exists(), "控えは印へ移す"
assert voice_text.sweep_clips(now=time.time() + voice_text.LIMIT + 120) == [cd / "k3.webm", cd / "k4.webm", cd / "k5.webm", dd / "k2.webm"], "時刻を進めると、ほかの記録の物も消える"
assert json.loads((cd / "k3.dropped.json").read_text(encoding="utf-8"))["wait"] is None, "理由が無い時は空"
assert (cd / "k2.done.json").exists(), "読み終えた印には触らない"

# 6. 公開の場の合計
size = techo_site.media_bytes()
k6 = new_record()
assert voice_text.put_voice_clip(k6, clip("webm"), "webm")[0] == "t1.mka" and voice_text.put_cam_clip(k6, clip("webm", video=True), "webm")[0] == "k1.webm"
kfile = voice_text.voice_dir(k6) / "k1.webm"
assert techo_site.media_bytes() - size == (voice_text.voice_dir(k6) / "t1.mka").stat().st_size + kfile.stat().st_size, "t と k を数える"
size = techo_site.media_bytes()
voice_text.clip_wait(k6, "k1.webm", "説明待ち")
assert techo_site.media_bytes() == size, "控えの json は数えない"

# 9. 頁へ返す道と束に出ない（7 の前に見る）
assert techo_site.media_of(cam) == [] and techo_site.media_of(k6) == [], "頁へ返す道は区切りを拾わない"
bundle = json.dumps(engine_bundle.build(), ensure_ascii=False)
assert PLAIN not in bundle and "k1.webm" not in bundle and "t1.transcript" not in bundle, "束に区切りと字が入らない"

# 8. サーバと video_up の掃除が sweep_clips も回す
os.utime(kfile, (past, past))
worker = voice_text.Worker(tool=False, every=3600)
worker.start()
for _ in range(200):
    if not kfile.exists():
        break
    time.sleep(0.05)
assert not kfile.exists() and (voice_text.voice_dir(k6) / "k1.dropped.json").exists(), "立てた時に区切りの掃除も回る"
k7 = new_record()
voice_text.put_cam_clip(k7, clip("webm", video=True), "webm")
k7file = voice_text.voice_dir(k7) / "k1.webm"
os.utime(k7file, (past, past))
video_up.sweep()
assert not k7file.exists(), "video_up の掃除も区切りを消す"

# 7. 取り下げで全部消える
for r in (rid, cam):
    assert records.withdraw(r)[1] == [] and not voice_text.voice_dir(r).exists(), r
print("ok 声とカメラの区切り: t は写して字にしてから消す・k は絵だけ・5 つまでの通し・大きさと頭のバイト・待ちと理由と読み終え・72 時間の掃除・合計に数える・取り下げ・頁と束に出ない")
