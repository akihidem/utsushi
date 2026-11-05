"""声のファイルを、この機械の中だけで字にする（本人の指示 11-05、J-029）。faster-whisper の入った python から、単独で呼ぶ。

なぜ別のプロセスか: 道具は repo の requirements に入れない（重く、./run.sh に要らない）。無い機械では呼ぶ側が「字にできていない」と残して進む。
ネットへ行かない指定で、手元のモデルだけを読む。声を外へ送らない。

使い方: <faster-whisper の入った python> -I asr_worker.py <声のファイル> <モデル>
出力: {"model": …, "language": …, "segments": [{"start": 秒, "end": 秒, "text": 字}, …]} の JSON。
"""
import json
import os
import subprocess
import sys

os.environ["HF_HUB_OFFLINE"] = "1"
os.nice(10)  # ほかの作業を止めない

import numpy  # noqa: E402
from faster_whisper import WhisperModel  # noqa: E402


def read_voice(path):
    """声を ffmpeg の管でメモリへ読む。ファイルを増やさない。faster-whisper の読み手は環境の部品の版で動かない事がある（手元の 1 つの環境で落ちた）。"""
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-protocol_whitelist", "file", "-i", path, "-vn", "-ac", "1", "-ar", "16000", "-f", "s16le", "-"], capture_output=True, check=True).stdout
    return numpy.frombuffer(raw, dtype=numpy.int16).astype(numpy.float32) / 32768.0


def main(path, name):
    model = WhisperModel(name, device="cpu", compute_type="int8", cpu_threads=6, local_files_only=True)
    segments, info = model.transcribe(read_voice(path), language="ja", vad_filter=True, beam_size=1)
    out = [{"start": round(s.start, 1), "end": round(s.end, 1), "text": s.text.strip()} for s in segments]
    json.dump({"model": name, "language": info.language, "segments": out}, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
