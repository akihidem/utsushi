"""声のファイルを、この機械の中だけで字にする（本人の指示 11-05、J-029）。faster-whisper の入った python から、単独で呼ぶ。

なぜ別のプロセスか: 道具は repo の requirements に入れない（重く、./run.sh に要らない）。無い機械では呼ぶ側が「字にできていない」と残して進む。
ネットへ行かない指定で、手元のモデルだけを読む。声を外へ送らない。

使い方: <faster-whisper の入った python> -I asr_worker.py <声のファイル> <モデル>
       <faster-whisper の入った python> -I asr_worker.py --check <モデル>   道具とモデルが手元にあるかだけを見る（終わり 0 = ある / 4 = 無い）
       <faster-whisper の入った python> -I asr_worker.py --serve <モデル>   常駐して、標準入力から声を 1 つずつ受ける（下の serve）
出力: {"model": …, "language": …, "segments": [{"start": 秒, "end": 秒, "text": 字}, …]} の JSON。
道具の作り方は repo の根の requirements-asr.txt に書いた（版を固めた物）。

常駐の形（--serve）は、作業の頁の「聞く」（本人 11-08 539「質問した時のその瞬間の写真を何枚か撮って、音声を文字にして認識して、
クロードが考えて答えを音声で出すようにする。…記録はここでは取らず、質問のための経路と割り切る。」）のため。
- 型を 1 回だけ読み込む。1 回ごとに読み込むと、4 秒ほどの 1 文に 14 秒かかった（声の字の 1 本目の実測）。人が答えを待つ口なので、読み込みを先に済ませる
- 声はファイルにせず標準入力で受け、字も標準出力で返すだけ（539 の「記録はここでは取らず」。ディスクに声も字も残さない）。
  ffmpeg が管から読めない形（mp4 の頭の情報が後ろにある物）の時だけ、メモリの上（/dev/shm）の 0700 の箱に 1 つ置き、字にしたらすぐ消す
- 頼みの形: 8 バイトの頭（中身の長さ 4 バイト・大きい方から＋形の名 4 字「webm」か「mp4 」）の後に中身。返事は 1 行の JSON
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


SERVE_SECONDS = 15  # 常駐の形で字にする声の長さの上限（秒）。頁は 12 秒で止めるので、少し長く取る。長い声で CPU を埋めないため
SERVE_FORMATS = {b"webm": "matroska", b"mp4 ": "mov"}  # 形の名 → ffmpeg の読み手。読み手を決め打ち、中身の形で選ばせない（voice_text の CLIP_FORMATS と同じ線）
BOX_PREFIX = "utsushi-ask-"  # 管から読めない時の箱の名の頭。後ろに作り手のプロセスの番号を付け、残った箱を呼ぶ側（omochae.asr_serve）が掃除する
DECODE_TIMEOUT = 20  # 秒。壊れた声で ffmpeg が止まらないため


def _decode(data, demuxer, box):
    """声の中身をメモリの上で読む。Returns float32 の並び（読めなければ None）。まず管から読み、だめな時だけ箱に置いて読み直し、置いた物は必ず消す。"""
    import numpy

    # 管から読むので -nostdin は付けない（標準入力が声そのもの）。読める道は pipe だけにする（中身が別のファイルや URL を指しても読みに行かない）
    cmd = ["ffmpeg", "-v", "error", "-protocol_whitelist", "pipe", "-f", demuxer, "-i", "pipe:0", "-vn", "-ac", "1", "-ar", str(RATE), "-f", "s16le", "-"]
    try:
        raw = subprocess.run(cmd, input=data, capture_output=True, timeout=DECODE_TIMEOUT).stdout
    except subprocess.TimeoutExpired:
        raw = b""
    if not raw and box:
        import tempfile

        fd, path = tempfile.mkstemp(dir=box)  # 0600
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(data)
            file_cmd = ["ffmpeg", "-v", "error", "-protocol_whitelist", "file", "-f", demuxer, "-i", path, "-vn", "-ac", "1", "-ar", str(RATE), "-f", "s16le", "-"]
            raw = subprocess.run(file_cmd, stdin=subprocess.DEVNULL, capture_output=True, timeout=DECODE_TIMEOUT).stdout
        except subprocess.TimeoutExpired:
            raw = b""
        finally:
            os.unlink(path)
    if not raw:
        return None
    return numpy.frombuffer(raw, dtype=numpy.int16).astype(numpy.float32)[:RATE * SERVE_SECONDS] / 32768.0


def _read_exact(stream, n):
    out = b""
    while len(out) < n:
        chunk = stream.read(n - len(out))
        if not chunk:
            return None
        out += chunk
    return out


def serve(name):
    """常駐して、声を 1 つずつ字にする。読み込みが済んだら {"ready": true} の 1 行を出し、頼みごとに 1 行を返す。
    返す 1 行は {"segments": […]} か {"error": 種類}。種類は form（形の名が違う）・decode（読めない）。字は返す 1 行の中だけで、ほかには出さない。
    標準入力が閉じたら（呼ぶ側のサーバが止まったら）終わる。"""
    import atexit
    import shutil as _shutil
    import tempfile

    from faster_whisper import WhisperModel

    model = WhisperModel(name, device="cpu", compute_type="int8", cpu_threads=6, local_files_only=True)
    box = None
    if os.path.isdir("/dev/shm"):  # メモリの上の置き場が無い機械では、管から読めない形を断る（ディスクに声を置かない）
        box = tempfile.mkdtemp(prefix=f"{BOX_PREFIX}{os.getpid()}-", dir="/dev/shm")  # 0700
        atexit.register(_shutil.rmtree, box, True)
    out, src = sys.stdout, sys.stdin.buffer
    out.write(json.dumps({"ready": True}) + "\n")
    out.flush()
    while True:
        head = _read_exact(src, 8)
        if head is None:
            return
        size, form = int.from_bytes(head[:4], "big"), head[4:]
        data = _read_exact(src, size)
        if data is None:
            return
        if form not in SERVE_FORMATS:
            reply = {"error": "form"}
        else:
            voice = _decode(data, SERVE_FORMATS[form], box)
            if voice is None:
                reply = {"error": "decode"}
            else:
                # 引数は main と同じ（前の字に引きずられて同じ字を繰り返さない・音の無い所の字を落とす）
                segments, _ = model.transcribe(voice, language="ja", vad_filter=True, beam_size=1, condition_on_previous_text=False)
                segs = [{"start": round(s.start, 1), "end": round(s.end, 1), "text": s.text.strip()} for s in segments]
                reply = {"segments": inside(segs, len(voice) / RATE)}
        del data
        out.write(json.dumps(reply, ensure_ascii=False) + "\n")
        out.flush()


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
    if sys.argv[1] == "--serve":
        sys.exit(serve(sys.argv[2]))
    main(sys.argv[1], sys.argv[2])
