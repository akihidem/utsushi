"""作業の頁の「聞く」の声を、このサーバの中で字にする常駐の作り手（本人 11-08 539「音声を文字にして認識して、クロードが考えて答えを
音声で出すようにする。…記録はここでは取らず、質問のための経路と割り切る。」）。

判断の芯:
- 道具は上げた動画の声と同じ（omochae.asr_worker・OMOCHAE_ASR_PYTHON・手元のモデルだけ・外へ送らない）。ただ voice_text.transcribe は使わない。
  字を *.transcript.json に書く形で（539 の「記録はここでは取らず」に合わない）、時間切れも長い動画のための 4 時間だから
- 作り手は 1 本だけ常駐させ（asr_worker --serve）、型の読み込みを 1 回にする。人が答えを待つ口なので、1 回ごとに読み込む形
  （4 秒ほどの 1 文に 14 秒）は採らない。1 本なので、頼みは 1 つずつ（同時に来たら待ち、待ちきれなければ混んでいる扱い）
- 声は標準入力で渡し、字は標準出力の 1 行で受ける。どちらもファイルにしない。作り手が管から読めない形の時だけメモリの上の箱に置き、
  作り手がすぐ消す（asr_worker._decode）。時間切れで作り手を止めた時は、その箱が残りうるので、作り直す前に掃除する（sweep）
- 字は、話す口と同じ入口の床（talk_log.blocked・連絡先と名乗りと学校の名の形）を区切りごとに通し、当たった区切りは伏せる（voice_text と同じ）
- 失敗は種類だけを返す（字にできない・時間切れ・道具が無い）。字も声も、例外の文と記録に入れない
"""
import json
import os
import pathlib
import re
import select
import shutil
import subprocess
import threading
import time

from . import talk_log, voice_text

TIMEOUT = 30  # 秒。1 つの声を字にするのを待つ長さ（設計の 2 版の止め 4）。越えたら作り手を止めて作り直す
START_TIMEOUT = 240  # 秒。型の読み込みを待つ長さ（large-v3-turbo を CPU で読む）
IDLE = 20 * 60  # 秒。最後に使ってからこれだけ過ぎたら作り手を止める（型はメモリを 1GB ほど使うので、使わない間は持たない）
MODEL_ENV = "OMOCHAE_ASK_ASR_MODEL"  # この口だけ小さい型に替える口（遅い時のため・設計の 2 版）。無ければ動画の声と同じ型
# 箱の名の頭は asr_worker.BOX_PREFIX と同じ字（あちらを import しない: 読むだけで HF_HUB_OFFLINE をこのサーバの環境に置くため。同じかは試験が見る）
BOX_PREFIX = "utsushi-ask-"
BOX = re.compile(re.escape(BOX_PREFIX) + r"(\d+)-")


class Missing(Exception):
    """字にする道具が使えない（OMOCHAE_ASR_PYTHON が無い・型が無い・作り手が立たない）。"""


class Failed(Exception):
    """1 つの声を字にできなかった。kind は form・decode・timeout・busy・broken のどれか（字は入れない）。"""

    def __init__(self, kind):
        super().__init__(kind)
        self.kind = kind


def sweep(root="/dev/shm"):
    """止まった作り手の箱を消す。名に作り手の番号があり、その番号のプロセスがもう無い箱だけ（動いている別のサーバの作り手の箱は残す）。"""
    root = pathlib.Path(root)
    if not root.is_dir():
        return 0
    n = 0
    for box in root.glob(BOX_PREFIX + "*"):
        m = BOX.match(box.name)
        if not m or not box.is_dir() or box.stat().st_uid != os.getuid():
            continue
        try:
            os.kill(int(m.group(1)), 0)
            continue  # 動いている
        except ProcessLookupError:
            pass
        except PermissionError:
            continue
        shutil.rmtree(box, ignore_errors=True)
        n += 1
    return n


def _masked(segments):
    """区切りの字をつなぐ。入口の床に当たった区切りは伏せる（何に当たったかの呼び名だけを残す）。"""
    out = []
    for seg in segments:
        text = str(seg.get("text", "")).strip()
        if not text:
            continue
        hit = talk_log.blocked(text)
        out.append(voice_text.HIDDEN.format(hit) if hit else text)
    return "".join(out)


class Listener:
    """常駐の作り手を 1 本持ち、声を 1 つずつ字にする。作り手は最初に頼まれた時か、start() で立てる。"""

    def __init__(self, python=None, model=None, timeout=TIMEOUT, start_timeout=START_TIMEOUT, cmd=None, idle=IDLE):
        self.python = python if python is not None else os.environ.get("OMOCHAE_ASR_PYTHON")
        self.model = model or os.environ.get(MODEL_ENV) or os.environ.get("OMOCHAE_ASR_MODEL", voice_text.ASR_MODEL)
        self.timeout, self.start_timeout, self.idle = timeout, start_timeout, idle
        self._cmd = cmd  # 試験のための口（偽の作り手を立てる）
        self._proc = None
        self._lock = threading.Lock()
        self._last = time.monotonic()
        self._warming = False
        self._watch = None

    def available(self):
        return bool(self._cmd or self.python)

    def _spawn(self):
        sweep()
        cmd = self._cmd or [self.python, "-I", str(voice_text.ASR_WORKER), "--serve", self.model]
        try:
            # 作り手の stderr はサーバの stderr（失敗の記録）へそのまま。作り手は字を stderr に出さない（asr_worker.serve）
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, env={**os.environ, "HF_HUB_OFFLINE": "1"})
        except OSError as e:
            raise Missing(type(e).__name__) from None
        try:
            line = self._line(proc, time.monotonic() + self.start_timeout)
            if json.loads(line).get("ready") is not True:
                raise ValueError
        except (TimeoutError, EOFError, ValueError):
            self._kill(proc)
            raise Missing("作り手が立たない") from None
        self._proc = proc
        self._last = time.monotonic()
        if self._watch is None or not self._watch.is_alive():
            self._watch = threading.Thread(target=self._idle_stop, daemon=True)
            self._watch.start()

    def _idle_stop(self):
        """使われない間が IDLE を過ぎたら作り手を止める。止めた後は、次に頼まれた時か頁を開いた時に立て直す。"""
        while True:
            time.sleep(min(60, max(1, self.idle / 4)))
            with self._lock:
                if self._proc is None:
                    return
                if time.monotonic() - self._last >= self.idle:
                    self._kill(self._proc)
                    self._proc = None
                    sweep()
                    return

    def warm(self):
        """作り手を裏で立て始める（作業の頁を開いた時に呼ぶ）。道具が無い・もう立っている・立てている途中なら何もしない。待たない。"""
        if not self.available() or self._warming or (self._proc is not None and self._proc.poll() is None):
            return
        self._warming = True

        def run():
            try:
                self.start()
            except Missing:
                pass  # 聞いた時に、同じ断り（道具が無い）を返す
            finally:
                self._warming = False

        threading.Thread(target=run, daemon=True).start()

    def start(self):
        """作り手を先に立てる（サーバを立てた時に裏で呼ぶ。最初に聞いた人が型の読み込みを待たないため）。立たなければ Missing。"""
        with self._lock:
            if self._proc is None or self._proc.poll() is not None:
                self._spawn()

    @staticmethod
    def _line(proc, deadline):
        buf = b""
        fd = proc.stdout.fileno()
        while not buf.endswith(b"\n"):
            left = deadline - time.monotonic()
            if left <= 0:
                raise TimeoutError
            ready, _, _ = select.select([fd], [], [], left)
            if not ready:
                raise TimeoutError
            chunk = os.read(fd, 65536)
            if not chunk:
                raise EOFError
            buf += chunk
        return buf.decode("utf-8")

    @staticmethod
    def _kill(proc):
        try:
            proc.kill()
            proc.wait(timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            pass

    def stop(self):
        with self._lock:
            if self._proc is not None:
                self._kill(self._proc)
                self._proc = None
                sweep()

    def text(self, data, form):
        """声（webm か mp4 の中身）を字にする。Returns 伏せた後の字（声が無ければ空の字）。字にできなければ Failed、道具が無ければ Missing。"""
        if not self.available():
            raise Missing("OMOCHAE_ASR_PYTHON が無い")
        tag = {"webm": b"webm", "mp4": b"mp4 "}.get(form)
        if tag is None:
            raise Failed("form")
        if not self._lock.acquire(timeout=self.timeout):
            raise Failed("busy")
        try:
            if self._proc is None or self._proc.poll() is not None:
                self._spawn()
            proc = self._proc
            try:
                proc.stdin.write(len(data).to_bytes(4, "big") + tag + data)
                proc.stdin.flush()
                reply = json.loads(self._line(proc, time.monotonic() + self.timeout))
            except (TimeoutError, EOFError, BrokenPipeError, OSError, ValueError) as e:
                # 止まった・壊れた作り手は捨てる。次に頼まれた時に立て直す（箱の残りは _spawn の sweep が消す）
                self._kill(proc)
                self._proc = None
                sweep()
                raise Failed("timeout" if isinstance(e, TimeoutError) else "broken") from None
        finally:
            self._last = time.monotonic()
            self._lock.release()
        if "error" in reply:
            raise Failed(str(reply["error"]) if reply["error"] in ("form", "decode") else "broken")
        return _masked(reply.get("segments") or [])
