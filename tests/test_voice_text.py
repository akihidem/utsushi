"""上げた動画の声を、この機械の中で字にしてから消す（omochae.voice_text・本人の言葉 11-08「全部残していいことにしたい。」）。本物の字にする道具は使わない（作り物）。

見る事:
1. 手帖に上げた動画: 頁に出す動画は音が無く、声だけが非公開で写る（撮影情報なし・箱 0700・ファイル 0600）。頁へ返す道（media_of）は声を拾わない
2. 字にする前に声が消えない。道具が無い時は声が残る（掃除が 72 時間で消す）
3. 字にした後は声が残らない。字は区切りごとに名乗り・連絡先・学校の名の床を通し、当たった区切りを伏せる
4. 字の在る声は 2 度字にしない。動画の専用の口の名（voice.mka・transcript.json）と手帖の名（m<n>.mka）が混ざっても同じ
5. 72 時間を過ぎた字の無い声は、字にする道具の無い機械でも消え、字にできずに消した印が残る。72 時間の前は残る
6. 道具の無いサーバ（keep_voice=False）は声を写さない。公開の場の大きさの合計（media_bytes）に声も入る
7. 取り下げで声と字が消える。字を書く前に取り下げられたら字を書かない
8. サーバ: 道具がある時だけ声を写し、作業列が字にする。道具が無くても、立てた時に掃除が回る
9. 頁・束・AI に見せる口に字が出ない。声と字の道は開かない
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
import threading
import time
import urllib.error
import urllib.request

tmp = pathlib.Path(tempfile.mkdtemp())
os.environ["OMOCHAE_DATA"] = str(tmp / "data")
os.environ["OMOCHAE_SAMPLES"] = "0"
os.environ.pop("OMOCHAE_ASR_PYTHON", None)
if not shutil.which("ffmpeg"):
    print("検査できない: ffmpeg が無い", file=sys.stderr)
    sys.exit(4)

from omochae import engine_bundle, records, voice_text  # noqa: E402
from web import play_server, techo_site  # noqa: E402

G = "NDL-1187053-R0000005-L"
PLACE = "+35.6000+139.7000"
NAMED = "山田小学校の田中です"
PHONE = "電話は 090-1234-5678 です"
PLAIN = "筒の内側に割り箸を貼ると押し上げやすい"
# 作り物の字にする道具: --check は通り、字にした回数を数える。字には名乗りと連絡先の区切りを入れる（伏せる床を見るため）
calls = tmp / "calls.txt"
fake = tmp / "fake_asr.py"
fake.write_text(f"""import json, pathlib, sys
if sys.argv[1] == "--check":
    sys.exit(0)
assert sys.argv[1].endswith(".mka")
with open({str(calls)!r}, "a") as f:
    f.write(sys.argv[1] + "\\n")
json.dump({{"model": sys.argv[2], "language": "ja", "segments": [{{"start": 0.0, "end": 1.0, "text": {PLAIN!r}}}, {{"start": 1.0, "end": 2.0, "text": {NAMED!r}}}, {{"start": 2.0, "end": 3.0, "text": {PHONE!r}}}]}}, sys.stdout, ensure_ascii=False)
""", encoding="utf-8")
voice_text.ASR_WORKER = fake


def n_calls():
    return len(calls.read_text().splitlines()) if calls.exists() else 0


def video(audio=True):
    out = tmp / f"v{time.time_ns()}.mp4"
    sound = ["-f", "lavfi", "-i", "sine=frequency=440:duration=2", "-c:a", "aac"] if audio else []
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=64x48:rate=5:duration=2", *sound, "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-metadata", "title=secret-place", "-metadata", f"com.apple.quicktime.location.ISO6709={PLACE}+010.000/", "-movflags", "use_metadata_tags", str(out)],
                   check=True, capture_output=True, timeout=120)
    data = out.read_bytes()
    assert PLACE.encode() in data, "作り物に撮影の情報が入っていない"
    return data


def streams(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(path)], capture_output=True, text=True, check=True)
    return [s["codec_type"] for s in json.loads(r.stdout)["streams"]]


def new_record():
    rid, fails = records.add({"source_id": G, "hypothesis_id": "H-A", "sheet_version": 1, "result": "動いた"})
    assert rid and not fails, fails
    return rid


# 1. 頁に出す動画は音が無く、声だけが非公開で写る
rid = new_record()
data = video()
name, why = techo_site.save_media(rid, "video/mp4", data, keep_voice=True)
assert name == "m1.mp4", why
voice = voice_text.voice_dir(rid) / "m1.mka"
assert streams(techo_site.media_dir(rid) / name) == ["video"], "頁に出す動画に音を残さない"
assert voice.exists() and streams(voice) == ["audio"], "声だけを写す"
assert stat.S_IMODE(voice.stat().st_mode) == 0o600 and stat.S_IMODE(voice.parent.stat().st_mode) == 0o700, "本人だけが読める"
assert PLACE.encode() not in voice.read_bytes() and b"secret-place" not in voice.read_bytes(), "声の写しにも撮影情報を残さない"
assert techo_site.media_of(rid) == ["m1.mp4"], "頁へ返す道は声を拾わない"
assert voice_text.pending() == [voice]

# 2. 字にする前に消えない。道具が無い時は残る
assert voice.exists(), "字にする前に声が消えない"
assert voice_text.transcribe(voice) == "no-tool" and voice.exists(), "道具が無い時は声が残る（掃除が 72 時間で消す）"

# 3. 字にした後は残らない。名乗りと連絡先の区切りは伏せる
os.environ["OMOCHAE_ASR_PYTHON"] = sys.executable
assert voice_text.transcribe(voice, still=lambda: voice_text.still_wanted(voice)) == "done"
text = voice_text.text_of(voice)
assert text.name == "m1.transcript.json" and not voice.exists(), "字にしたら声を消す"
assert stat.S_IMODE(text.stat().st_mode) == 0o600
got = json.loads(text.read_text(encoding="utf-8"))
said = [s["text"] for s in got["segments"]]
assert said[0] == PLAIN and got["hidden"] == 2 and said[1] == voice_text.HIDDEN.format("名乗り") and said[2] == voice_text.HIDDEN.format("連絡先"), said
assert NAMED not in text.read_text(encoding="utf-8") and "090-1234-5678" not in text.read_text(encoding="utf-8"), "伏せた字を残さない"

# 4. 字の在る声は 2 度字にしない。2 つの名が混ざっても同じ
before = n_calls()
shutil.copyfile(tmp / "fake_asr.py", voice)  # 止まって残った声の形（字は在る）
assert voice_text.transcribe(voice) == "done" and n_calls() == before and not voice.exists(), "字の在る声は 2 度字にしない（残った声だけ消す）"
up = voice_text.voice_dir(rid) / "voice.mka"  # 動画の専用の口の名
up.write_bytes(b"voice")
assert voice_text.text_of(up).name == "transcript.json" and up in voice_text.pending()
assert voice_text.transcribe(up) == "done" and not up.exists() and voice_text.text_of(up).exists() and n_calls() == before + 1
assert voice_text.pending() == [], "字の在る声は待ちに出ない"

# 5. 72 時間を過ぎた字の無い声は、道具の無い機械でも消え、印が残る
os.environ.pop("OMOCHAE_ASR_PYTHON")
old_rid, young_rid = new_record(), new_record()
old = voice_text.voice_dir(old_rid) / "m1.mka"
young = voice_text.voice_dir(young_rid) / "m1.mka"
for v in (old, young):
    v.parent.mkdir(parents=True, exist_ok=True)
    v.write_bytes(b"voice")
past = time.time() - voice_text.LIMIT - 60
os.utime(old, (past, past))
assert voice_text.sweep() == [old] and not old.exists() and young.exists(), "72 時間を過ぎた物だけ消す"
mark = json.loads(voice_text.dropped_of(old).read_text(encoding="utf-8"))
assert "字にできずに消した" in mark["why"], mark
assert voice_text.sweep(now=time.time() + voice_text.LIMIT + 120) == [young] and not young.exists(), "時刻を進めると、次の物も消える"

# 6. 道具の無いサーバは声を写さない。公開の場の大きさの合計に声も入る
rid2 = new_record()
name2, _ = techo_site.save_media(rid2, "video/mp4", video(), keep_voice=False)
assert name2 == "m1.mp4" and not voice_text.voice_dir(rid2).exists(), "道具が無い時は受ける時に落とす"
size_before = techo_site.media_bytes()
extra = voice_text.voice_dir(rid2) / "m1.mka"
extra.parent.mkdir(parents=True, exist_ok=True)
extra.write_bytes(b"x" * 1000)
assert techo_site.media_bytes() == size_before + 1000, "声も公開の場の合計に数える"
quiet, _ = techo_site.save_media(rid2, "video/mp4", video(audio=False), keep_voice=True)
assert quiet == "m2.mp4" and not (voice_text.voice_dir(rid2) / "m2.mka").exists(), "音の無い動画は、写す声が無い（動画は受け取る）"

# 7. 取り下げで声と字が消える。字を書く前に取り下げられたら字を書かない
os.environ["OMOCHAE_ASR_PYTHON"] = sys.executable
rid3 = new_record()
techo_site.save_media(rid3, "video/mp4", video(), keep_voice=True)
v3 = voice_text.voice_dir(rid3) / "m1.mka"
assert voice_text.transcribe(v3, still=lambda: False) == "gone" and not voice_text.text_of(v3).exists(), "取り下げた後は字を書かない"
assert records.withdraw(rid3)[1] == [] and not techo_site.media_dir(rid3).exists(), "取り下げで声と字の箱ごと消える"
assert records.withdraw(rid)[1] == [] and not voice_text.voice_dir(rid).exists(), "字のある記録も、取り下げで字が消える"

# 8. サーバ: 道具がある時だけ声を写し、作業列が字にする。道具が無くても、立てた時に掃除が回る
srv = play_server.serve(0)
assert srv.voice_tool is True and srv.voice_jobs.is_alive()
rid4 = new_record()
techo_site.save_media(rid4, "video/mp4", video(), keep_voice=srv.voice_tool)
v4 = voice_text.voice_dir(rid4) / "m1.mka"
srv.voice_jobs.jobs.put(v4)
# 作業列は字を書いてから声を消すので、字が書けた所でなく、声が消えた所まで待つ（混んだ機械で、間を見て落ちないように・上限 60 秒）
for _ in range(1200):
    if voice_text.text_of(v4).exists() and not v4.exists():
        break
    time.sleep(0.05)
assert voice_text.text_of(v4).exists() and not v4.exists(), "作業列が字にして声を消す"
srv.server_close()
os.environ.pop("OMOCHAE_ASR_PYTHON")
stale_rid = new_record()
stale = voice_text.voice_dir(stale_rid) / "m1.mka"
stale.parent.mkdir(parents=True, exist_ok=True)
stale.write_bytes(b"voice")
os.utime(stale, (past, past))
srv2 = play_server.serve(0)
assert srv2.voice_tool is False
# 掃除は音を消してから印を書くので、音が消えた所でなく、印が書けた所まで待つ（前は音が消えた所で待ちをやめ、機械が混んでいる時に
# 印を書く前の間を見て落ちた。#666 の ./run.sh・負荷の平均 36〜40 の時）。待ちの上限も、混んだ機械に合わせて 60 秒にした
for _ in range(1200):
    if not stale.exists() and voice_text.dropped_of(stale).exists():
        break
    time.sleep(0.05)
assert not stale.exists() and voice_text.dropped_of(stale).exists(), "道具が無いサーバでも、立てた時に 72 時間の掃除が回る"

# 9. 頁・束・AI に見せる口に字が出ない。声と字の道は開かない
threading.Thread(target=srv2.serve_forever, daemon=True).start()
port = srv2.server_address[1]


def get(path):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=60) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""


assert PLAIN in voice_text.text_of(v4).read_text(encoding="utf-8")
for path in (f"/toy/{G}", "/gallery", f"/toy/{G}/techo", "/about"):
    code, body = get(path)
    # 「transcript」だけでは探さない（話す口の JavaScript が、ブラウザの音声認識の transcript を読むため）。字のファイルの名で探す
    assert code == 200 and PLAIN not in body and "m1.transcript.json" not in body and "m1.mka" not in body, path
for path in (f"/record/{rid4}/media/voice/m1.transcript.json", f"/record/{rid4}/media/voice/m1.mka", f"/record/{rid4}/media/m1.transcript.json"):
    assert get(path)[0] == 404, path
srv2.shutdown()
assert PLAIN not in json.dumps(engine_bundle.build(), ensure_ascii=False), "束に字が入らない"
assert techo_site.media_of(rid4) == ["m1.mp4"], "AI に見せる口（api.observe）が読む動画の一覧に声と字が入らない（play_server が media_of から選ぶ）"
print("ok 上げた動画の声: 字にする前は残り・字にしたら消え・伏せる床・2 度字にしない・72 時間の掃除・取り下げ・頁と束に出ない")
