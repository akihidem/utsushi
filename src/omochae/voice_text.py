"""上げた動画の声を、この機械の中で字にしてから消す（本人の言葉 11-08「全部残していいことにしたい。」・本人の言葉 11-07「音声は文字化してから落とさないと価値が減る」）。

決まり: 字にしたら元の音は消す。字にできなければ 72 時間で消す（本人の決め 11-08）。字は作る側だけが読み、頁・束・AI に見せる口には出さない（決定 B）。
手帖の上げ口（web.techo_site・web.play_server）と動画の専用の口（web.video_up）が同じ置き場を使うので、ここに字にする所と掃除をまとめる。

判断の芯:
- 置き場は記録の写真と動画の箱の下の voice/（箱 0700・ファイル 0600・git の外）。頁へ返す道（techo_site.media_of）は箱の直下の m*.* だけを拾うので、
  voice/ は頁にも AI に見せる口（api.observe）にも出ない。取り下げ（records.withdraw）は箱ごと消すので、音も字も消える。
- 名は 2 つある。手帖は 1 本ずつ m<n>.mka（動画 m<n>.<ext> と同じ番号）、動画の専用の口は記録に 1 本の voice.mka（#388 から）。字は
  m<n>.transcript.json と transcript.json。どちらも同じ関数で扱い、字の在る音は 2 度字にしない。
- 字は残す前に、話す口と同じ入口の床（talk_log.blocked・連絡先と名乗りと学校の名の形）を区切りごとに通し、当たった区切りの字は伏せる
  （字にした事と、伏せた数だけを残す）。声から字にした文には、名前や学校の名が入りうるため。
- 順は 字を書く → 音を消す。間で止まっても、字の無いまま音が消える事は無い。書く前と書いた後に「まだ要るか」を聞き、取り下げと重なっても
  字を残さない（#492 と同じ守り）。
- 72 時間の掃除は、字にする道具の無い機械でも回す。道具が無いと字にし直せないので、掃除を道具に結ぶと音が残り続けるため。
- 字にするのは手元のモデルだけ（omochae.asr_worker・ネットへ行かない指定・requirements-asr.txt）。外のサービスへは送らない。
"""
import json
import os
import pathlib
import queue
import subprocess
import sys
import threading
import time

from . import records, store

LIMIT = 72 * 3600  # 秒。字にできなかった音を置く長さの上限（本人の決め 11-08）
ASR_WORKER = pathlib.Path(__file__).resolve().parent / "asr_worker.py"
ASR_MODEL = "mobiuslabsgmbh/faster-whisper-large-v3-turbo"  # 環境変数 OMOCHAE_ASR_MODEL で替えられる
CHECK_TIMEOUT = 120  # 秒。道具の確かめは読み込みだけ
COPY_TIMEOUT = 600  # 秒。20MB の動画の音を写すのに足りる長さ
HIDDEN = "［伏せた（{0}）］"


def voice_dir(rid):
    return records.folder() / "media" / rid / "voice"


def text_of(voice):
    """音のファイルに対する字のファイル。voice.mka → transcript.json（動画の専用の口の名）、m1.mka → m1.transcript.json。"""
    voice = pathlib.Path(voice)
    return voice.with_name("transcript.json" if voice.stem == "voice" else f"{voice.stem}.transcript.json")


def dropped_of(voice):
    """字にできずに消した印のファイル。"""
    voice = pathlib.Path(voice)
    return voice.with_name(f"{voice.stem}.dropped.json")


def tool_missing():
    """字にする道具が使えるか。Returns 使えない理由（使えれば空の字）。確かめは字にするのと同じ道（同じ python・同じ asr_worker）で回す。"""
    python = os.environ.get("OMOCHAE_ASR_PYTHON")
    if not python:
        return "OMOCHAE_ASR_PYTHON が無い"
    try:
        r = subprocess.run([python, "-I", str(ASR_WORKER), "--check", os.environ.get("OMOCHAE_ASR_MODEL", ASR_MODEL)], capture_output=True, text=True, timeout=CHECK_TIMEOUT)
    except (OSError, subprocess.SubprocessError) as e:
        return f"確かめを回せない（{type(e).__name__}）"
    if r.returncode == 0:
        return ""
    return (r.stderr.strip().splitlines() or [f"確かめに落ちた（rc={r.returncode}）"])[-1][:200]


def copy_voice(src, dst, size, demuxer="mov"):
    """動画の音の流れだけを、撮影情報を外して dst に写す。Returns 写したか（音の無い動画・写せない形は False で、動画の受け取りは止めない）。
    読み手を決め打つ（-f mov）・読むのは置いたファイルだけ（-protocol_whitelist file）・大きさの上限（-fs）は、絵を写す所（techo_site.clean_video）と同じ線。"""
    dst = pathlib.Path(dst)
    probe = subprocess.run(["ffprobe", "-v", "error", "-protocol_whitelist", "file", "-f", demuxer, "-select_streams", "a:0", "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(src)],
                           capture_output=True, text=True, timeout=CHECK_TIMEOUT)
    if probe.returncode != 0 or "audio" not in probe.stdout:
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.parent.chmod(0o700)
    try:
        r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-protocol_whitelist", "file", "-f", demuxer, "-i", str(src), "-map", "0:a:0", "-c", "copy", "-vn", "-sn", "-dn",
                            "-map_metadata", "-1", "-map_chapters", "-1", "-fflags", "+bitexact", "-fs", str(size), "-f", "matroska", str(dst)], capture_output=True, timeout=COPY_TIMEOUT)
    except (OSError, subprocess.TimeoutExpired):
        dst.unlink(missing_ok=True)
        return False
    if r.returncode != 0 or not dst.exists():
        dst.unlink(missing_ok=True)
        return False
    dst.chmod(0o600)
    return True


def mask(data):
    """字の区切りごとに入口の床を通し、当たった区切りの字を伏せる。Returns (字, 伏せた数)。"""
    from . import talk_log

    hidden = 0
    for seg in data.get("segments", []):
        hit = talk_log.blocked(seg.get("text", ""))
        if hit:
            seg["text"] = HIDDEN.format(hit)
            hidden += 1
    return data, hidden


def transcribe(voice, still=lambda: True):
    """1 本の音を字にし、字を書けたら音を消す。still は「まだ要るか」（取り下げられていないか）を返す関数。
    Returns "done"（字がある）・"no-tool"（道具が無い。音は残り、掃除が 72 時間で消す）・"failed"（字にできない。同じ）・"gone"（もう要らない）。"""
    voice = pathlib.Path(voice)
    text = text_of(voice)
    if text.exists():
        voice.unlink(missing_ok=True)  # 字の在る音は 2 度字にしない。止まって残った音だけを消す
        return "done"
    if not voice.exists():
        return "gone"
    python = os.environ.get("OMOCHAE_ASR_PYTHON")
    if not python:
        return "no-tool"
    try:
        r = subprocess.run([python, "-I", str(ASR_WORKER), str(voice), os.environ.get("OMOCHAE_ASR_MODEL", ASR_MODEL)], capture_output=True, text=True, timeout=4 * 3600)
        data = json.loads(r.stdout) if r.returncode == 0 else None
    except (OSError, subprocess.SubprocessError, ValueError) as e:
        print(f"{voice.parent.parent.name}: 字にできない（{type(e).__name__}）", file=sys.stderr)
        data = None
    if not isinstance(data, dict):
        return "failed"
    if not still():
        return "gone"
    data, hidden = mask(data)
    data["hidden"] = hidden
    try:
        store.write_json(text, data)
        text.chmod(0o600)
    except FileNotFoundError:
        # 書く直前に取り下げが置き場を消した。消えた置き場を作り直して字を残さない
        return "gone"
    voice.unlink(missing_ok=True)
    if not still():
        text.unlink(missing_ok=True)
        return "gone"
    return "done"


def pending():
    """字にする前の音（字の無い音）。両方の名を拾う。"""
    root = records.folder() / "media"
    if not root.exists():
        return []
    return sorted(v for v in root.glob("R-*/voice/*.mka") if (v.stem == "voice" or v.stem.startswith("m")) and not text_of(v).exists())


def sweep(now=None):
    """72 時間を過ぎた字の無い音を消し、字にできずに消した事を残す。道具の有無に関わらず回す。Returns 消した音の一覧。"""
    now = time.time() if now is None else now
    gone = []
    for v in pending():
        try:
            age = now - v.stat().st_mtime
        except FileNotFoundError:
            continue
        if age <= LIMIT:
            continue
        v.unlink(missing_ok=True)
        mark = dropped_of(v)
        store.write_json(mark, {"why": "字にできずに消した（72 時間）", "at": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(now))})
        mark.chmod(0o600)
        gone.append(v)
    return gone


def still_wanted(voice):
    """その音の記録が、まだ取り下げられていないか（記録の json と、写真と動画の箱が在るか）。"""
    voice = pathlib.Path(voice)
    return (records.folder() / f"{voice.parent.parent.name}.json").exists() and voice.parent.is_dir()


class Worker(threading.Thread):
    """1 本ずつ順に字にする作業列と、1 時間ごとの掃除。同時に字にすると、長い字にする間に機械のほかの作業を止めるため 1 本ずつ。
    字にする道具が無い時（tool=False）も、掃除だけは回す。立てた時に、前に止まって残った字の無い音を回し直す。"""

    def __init__(self, tool, every=3600):
        super().__init__(daemon=True)
        self.tool, self.every = tool, every
        self.jobs = queue.Queue()

    def run(self):
        sweep()
        if self.tool:
            for v in pending():
                self.jobs.put(v)
        while True:
            try:
                v = self.jobs.get(timeout=self.every)
            except queue.Empty:
                sweep()
                continue
            try:
                if self.tool:
                    transcribe(v, still=lambda v=v: still_wanted(v))
            except Exception as e:  # 1 本の失敗で後の音を止めない。字の無い音は掃除が 72 時間で消す
                print(f"{pathlib.Path(v).parent.parent.name}: 字にする所で止まった（{type(e).__name__}）", file=sys.stderr)


def main(argv=None):
    """作る側が字を読む入口（頁は無い）。list: 字のある記録・字にする前の音・字にできずに消した数。Returns 終わりの値（0 / 4 = 呼び方の誤り）。"""
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] != ["list"]:
        print("使い方: python -m omochae.voice_text list", file=sys.stderr)
        return 4
    root = records.folder() / "media"
    for t in sorted(root.glob("R-*/voice/*transcript.json")) if root.exists() else []:
        print(f"字\t{t.parent.parent.name}\t{t}")
    for v in pending():
        print(f"字にする前\t{v.parent.parent.name}\t{v.name}")
    dropped = len(list(root.glob("R-*/voice/*.dropped.json"))) if root.exists() else 0
    print(f"字にできずに消した\t{dropped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
