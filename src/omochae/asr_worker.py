"""声のファイルを、この機械の中だけで字にする（本人の指示 11-05、J-029）。faster-whisper の入った python から、単独で呼ぶ。

なぜ別のプロセスか: 道具は repo の requirements に入れない（重く、./run.sh に要らない）。無い機械では呼ぶ側が「字にできていない」と残して進む。
ネットへ行かない指定で、手元のモデルだけを読む。声を外へ送らない。

使い方: <faster-whisper の入った python> -I asr_worker.py <声のファイル> <モデル>
       <faster-whisper の入った python> -I asr_worker.py --check <モデル>   道具とモデルが手元にあるかだけを見る（終わり 0 = ある / 4 = 無い）
出力: {"model": …, "language": …, "segments": [{"start": 秒, "end": 秒, "text": 字}, …]} の JSON。
道具の作り方は repo の根の requirements-asr.txt に書いた（版を固めた物）。
"""
import json
import os
import shutil
import subprocess
import sys

os.environ["HF_HUB_OFFLINE"] = "1"
RATE = 16000


def inside(segments, seconds):
    """音の長さの内の字だけを残す。音の無い終わりに、道具が話していない字を作る事があった（本物の 1 本目。110 秒の音に、118〜126 秒の「ご視聴ありがとうございました」）。"""
    return [s for s in segments if s["start"] < seconds]


def read_voice(path):
    import numpy

    """声を ffmpeg の管でメモリへ読む。ファイルを増やさない。faster-whisper の読み手は環境の部品の版で動かない事がある（手元の 1 つの環境で落ちた）。"""
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-protocol_whitelist", "file", "-i", path, "-vn", "-ac", "1", "-ar", str(RATE), "-f", "s16le", "-"], capture_output=True, check=True).stdout
    return numpy.frombuffer(raw, dtype=numpy.int16).astype(numpy.float32) / 32768.0


def check(name):
    """道具とモデルが手元にあるか。動画の専用の口は、立てる前にこれを呼び、落ちたら立たない（窓口の決定 11-06 夜）。
    重いモデルは読み込まず、手元の置き場にある事だけを見る（口を立てるたびに数 GB を読まないため）。Returns 終わりの値。"""
    if not shutil.which("ffmpeg"):
        print("字にする道具が無い: ffmpeg", file=sys.stderr)
        return 4
    try:
        import numpy  # noqa: F401
        from faster_whisper.utils import download_model

        download_model(name, local_files_only=True)
    except Exception as e:  # 入っていない・版が違う・モデルが手元に無い、のどれでも立てない
        print(f"字にする道具かモデルが手元に無い（{type(e).__name__}）", file=sys.stderr)
        return 4
    return 0


def main(path, name):
    from faster_whisper import WhisperModel

    os.nice(10)  # ほかの作業を止めない
    voice = read_voice(path)
    model = WhisperModel(name, device="cpu", compute_type="int8", cpu_threads=6, local_files_only=True)
    # 前の字に引きずられると、同じ字を繰り返す（同じ 1 本目の「以上です」）
    segments, info = model.transcribe(voice, language="ja", vad_filter=True, beam_size=1, condition_on_previous_text=False)
    out = [{"start": round(s.start, 1), "end": round(s.end, 1), "text": s.text.strip()} for s in segments]
    json.dump({"model": name, "language": info.language, "segments": inside(out, len(voice) / RATE)}, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    if sys.argv[1] == "--check":
        sys.exit(check(sys.argv[2]))
    main(sys.argv[1], sys.argv[2])
