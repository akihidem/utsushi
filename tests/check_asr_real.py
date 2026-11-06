"""本物の字にする道具で、動画の専用の口の声を 1 本字にし、字にしたら声が消える所まで通す。手で回す道具で、./run.sh の試験ではない。

なぜ試験にしないか: 道具とモデルは重く（数 GB）、requirements.txt に入れない決まり（requirements-asr.txt に分けた）。./run.sh の試験に入れると、
道具の無い機械で全部の試験が「確かめられない」になる。tests/test_video_up.py は作り物の道具で流れを見るので、本物の道（ffmpeg の管で読む・
ネットへ行かない指定で手元のモデルを読む）はここで見る。
声は作り物（espeak-ng の日本語の声で、かなの文を読ませる。漢字は読めず、字の精度は人の声より悪い）。本物の人の声は使わない。

使い方: OMOCHAE_ASR_PYTHON=.venv-asr/bin/python PYTHONPATH=src .venv/bin/python tests/check_asr_real.py
終了: 0 = 通る / 3 = 落ちる（どこで）/ 4 = 確かめられない（道具・モデル・espeak-ng が無い）
限界: ネットへ出ていない事は、道具の指定（HF_HUB_OFFLINE・local_files_only）までしか見ていない。網を切った箱はこの機械では作れなかった。
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

SID = "NDL-1187053-R0000005-L"  # 御来迎
SAY = "かたがみの さんまいめの おりせんが うすくて みえません"
# 字の当たりの見方: かなを片かなにそろえて、どれか 1 つが入っていればよい（機械の声は崩れるので、全部の一致は求めない）
EXPECT = ("カタガミ", "サンマイ", "オリセン", "ミエマセン", "見えません")


def katakana(text):
    return "".join(chr(ord(c) + 0x60) if "ぁ" <= c <= "ゖ" else c for c in text)


def main():
    if not os.environ.get("OMOCHAE_ASR_PYTHON"):
        print("確かめられない: OMOCHAE_ASR_PYTHON が無い（requirements-asr.txt の道具の python を指す）", file=sys.stderr)
        return 4
    if not (shutil.which("espeak-ng") and shutil.which("ffmpeg")):
        print("確かめられない: espeak-ng か ffmpeg が無い（作り物の声を作れない）", file=sys.stderr)
        return 4
    tmp = pathlib.Path(tempfile.mkdtemp())
    os.environ["OMOCHAE_DATA"] = str(tmp)
    from omochae import hypotheses, records, trial_video as tv
    from web import video_up

    why = video_up.tool_missing()
    if why:
        print(f"確かめられない: 道具の確かめに落ちた（{why}）", file=sys.stderr)
        return 4
    # 声の写しと同じ形（音だけの mka・AAC）にする。受け口は元の動画の音をそのまま写すので、スマホの動画に多い AAC にした
    wav = tmp / "say.wav"
    subprocess.run(["espeak-ng", "-v", "ja", "-s", "140", "-w", str(wav), SAY], check=True, capture_output=True, timeout=60)
    rid, fails = tv.new_record(SID, hypotheses.sheet_of(SID)["id"], records.UNSURE, note="", via=records.UPLOADED)
    if not rid:
        print(f"落ちた: 記録を作れない {fails}")
        return 3
    voice = tv._base(rid) / "voice" / "voice.mka"
    voice.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(wav), "-c:a", "aac", str(voice)], check=True, capture_output=True, timeout=60)
    video_up._save({"id": "U-0001", "token": "t" * 32, "state": "done", "record": rid, "source_id": SID, "kind": "review", "keep_voice": True, "voice": True})
    start = time.time()
    done = video_up.transcribe("U-0001")
    took = time.time() - start
    slip = json.loads((video_up.folder() / "U-0001.json").read_text(encoding="utf-8"))
    text_path = video_up._text_path(rid)
    data = json.loads(text_path.read_text(encoding="utf-8")) if text_path.exists() else {}
    heard = "".join(s.get("text", "") for s in data.get("segments", []))
    print(f"字にした: {done}・{took:.0f} 秒・モデル {data.get('model')}・言語 {data.get('language')}")
    print(f"読ませた文: {SAY}")
    print(f"字: {heard}")
    bad = []
    if not done or slip.get("text") != "done":
        bad.append(f"字にできていない（受付の字の様子 {slip.get('text')}）")
    if not heard.strip():
        bad.append("字が空")
    elif not any(e in katakana(heard) for e in EXPECT):
        bad.append(f"読ませた文の言葉が字に 1 つも無い（{', '.join(EXPECT)}）")
    if voice.exists():
        bad.append("字にした後も声が残っている")
    if not slip.get("voice_dropped"):
        bad.append("受付に消した印が無い")
    for b in bad:
        print(f"落ちた: {b}")
    print("通った" if not bad else f"{len(bad)} か所で落ちた")
    shutil.rmtree(tmp, ignore_errors=True)
    return 3 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
