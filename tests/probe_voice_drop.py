"""動画の専用の口の声を「字にしたら消す」形の確かめを、条件ごとに分けて回す。手で回す道具で、./run.sh の試験ではない。

なぜ別に置くか: tests/test_video_up.py は 1 本の流れなので、変える前のコードでは最初の条件で止まり、ほかの条件の失敗が見えない。
ここでは条件ごとに置き場を作り直し、前のコード（PYTHONPATH で古い src を指す）でも今のコードでも、全部の条件の成否を並べて出す。
HTTP と ffmpeg を通さず、受付と記録と声のファイルを直に置いて、video_up の関数を呼ぶ（流れの全部は test_video_up.py が見る）。

見る条件（窓口の決定 11-06 夜「声の消す合図は字にしたら」「道具が無い時は口を立てない」）:
  1 字にできたら、その場で声が消え、字は残り、受付に消した印が付く
  2 字を書いた後・声を消した後・印の前に止まっても、次に字にする時に、字を残したまま印を付け直す
  3 字にする道具が無い・確かめに落ちる時は、声を残す口が立たない
  4 字ができる前の drop-voice は断り、声を残す（--force の時だけ消す）
  5 案の根拠になった記録を取り下げても（記録の番号は残す道）、声と字が消える
使い方: PYTHONPATH=<src> .venv/bin/python tests/probe_voice_drop.py
終了: 0 = 全部通る / 3 = 落ちた条件がある（名指しする）/ 4 = 確かめられない
"""
import json
import os
import pathlib
import sys
import tempfile
import traceback

KEY = "probe-key-0123456789abcdef"
SID = "NDL-1187053-R0000005-L"  # 御来迎
WORKER = """import json, pathlib, sys
if sys.argv[1] == "--check":
    sys.exit(MODE)
assert sys.argv[1].endswith("voice.mka")
json.dump({"model": sys.argv[2], "language": "ja", "segments": [{"start": 0.0, "end": 1.0, "text": "作り物の字"}]}, sys.stdout, ensure_ascii=False)
"""


def setup(tmp, mode=0):
    """新しい置き場と、作り物の字にする道具（mode は --check の終わりの値）。"""
    os.environ["OMOCHAE_DATA"] = str(tmp)
    worker = tmp / "fake_asr.py"
    worker.write_text(WORKER.replace("MODE", str(mode)), encoding="utf-8")
    from web import video_up

    video_up.ASR_WORKER = worker
    os.environ["OMOCHAE_ASR_PYTHON"] = sys.executable
    return video_up


def slip_with_voice(video_up, sid_n, text=None):
    """受け取りの済んだレビューの受付と、声の写しを置く。Returns (受付番号, 記録の番号, 声のファイル)。"""
    from omochae import hypotheses, records, trial_video as tv

    rid, fails = tv.new_record(SID, hypotheses.sheet_of(SID)["id"], records.UNSURE, note="", via=records.UPLOADED)
    assert rid and not fails, fails
    voice = tv._base(rid) / "voice" / "voice.mka"
    voice.parent.mkdir(parents=True, exist_ok=True)
    voice.write_bytes(b"voice")
    slip = {"id": f"U-{sid_n:04d}", "token": "t" * 32, "state": "done", "record": rid, "source_id": SID, "kind": "review", "keep_voice": True, "voice": True}
    if text:
        slip["text"] = text
    video_up._save(slip)
    return slip["id"], rid, voice


def read_slip(video_up, slip_id):
    return json.loads((video_up.folder() / f"{slip_id}.json").read_text(encoding="utf-8"))


def c1(tmp):
    video_up = setup(tmp)
    slip_id, rid, voice = slip_with_voice(video_up, 1)
    assert video_up.transcribe(slip_id) is True, "字にできた"
    assert video_up._text_path(rid).exists(), "字は残る"
    assert not voice.exists(), "字にしたら声が消える"
    assert read_slip(video_up, slip_id).get("voice_dropped"), "受付に消した印"


def c2(tmp):
    video_up = setup(tmp)
    slip_id, rid, voice = slip_with_voice(video_up, 1, text="failed")
    video_up._text_path(rid).write_text(json.dumps({"segments": [{"start": 0, "end": 1, "text": "前に書いた字"}]}, ensure_ascii=False), encoding="utf-8")
    voice.unlink()
    assert video_up.transcribe(slip_id) is True, "止まった後でも字ができた事にする"
    s = read_slip(video_up, slip_id)
    assert s.get("text") == "done" and s.get("voice_dropped"), s
    assert "前に書いた字" in video_up._text_path(rid).read_text(encoding="utf-8"), "残っていた字を消さない"


def c3(tmp):
    video_up = setup(tmp)
    del os.environ["OMOCHAE_ASR_PYTHON"]
    for kind in video_up.KINDS:
        try:
            server = video_up.serve(0, KEY, worker=False, kind=kind)
        except ValueError:
            continue
        server.server_close()
        raise AssertionError(f"道具が無いのに {kind} の口が立った")
    video_up = setup(tmp, mode=4)
    try:
        server = video_up.serve(0, KEY, worker=False)
    except ValueError:
        return
    server.server_close()
    raise AssertionError("道具の確かめに落ちたのに口が立った")


def c4(tmp):
    video_up = setup(tmp)
    slip_id, rid, voice = slip_with_voice(video_up, 1, text="no-tool")
    assert video_up.drop_voice(slip_id), "字の前は断る"
    assert voice.exists(), "断った時は声を残す"
    assert video_up.drop_voice(slip_id, force=True) == [] and not voice.exists(), "--force の時だけ消す"


def c5(tmp):
    video_up = setup(tmp)
    from omochae import loop, records

    slip_id, rid, voice = slip_with_voice(video_up, 1, text="no-tool")
    video_up._text_path(rid).write_text(json.dumps({"segments": []}), encoding="utf-8")
    # 根拠の見分けは番号の字で探す（records._used_paths）。案のファイルに番号があれば根拠になる
    (loop.folder() / "fix-probe.json").write_text(json.dumps({"evidence": [rid]}), encoding="utf-8")
    assert records.used_by(rid), "根拠になっている"
    assert video_up.withdraw(slip_id) == []
    assert (records.folder() / f"{rid}.json").exists(), "根拠の指す先は残す"
    assert not voice.exists() and not video_up._text_path(rid).exists(), "声と字は消す"


def main():
    try:
        import web.video_up  # noqa: F401
    except ImportError as e:
        print(f"確かめられない: {e}", file=sys.stderr)
        return 4
    failed = []
    for name, case in (("1 字にしたら声が消える", c1), ("2 止まった後も印を付け直す", c2), ("3 道具が無いと口が立たない", c3),
                       ("4 字の前の drop-voice を断る", c4), ("5 根拠の記録の取り下げで声と字が消える", c5)):
        with tempfile.TemporaryDirectory() as d:
            try:
                case(pathlib.Path(d))
                print(f"PASS {name}")
            except Exception as e:  # 条件ごとに分けて、次の条件も回す
                failed.append(name)
                where = traceback.extract_tb(e.__traceback__)[-1]
                print(f"FAIL {name}: {type(e).__name__}: {e}（{pathlib.Path(where.filename).name}:{where.lineno}）")
    print(f"{5 - len(failed)}/5 通る")
    return 3 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
