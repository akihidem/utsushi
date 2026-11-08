"""サイト全体の資源の上限（安全の事項 4 への対応・11-08）。

本人の条件: サイトの機能は維持し、見た目と挙動は変えず、安全の事項だけ直す。なので、どの上限も、ふつうの使い方（ワークショップの
1 つの場で数人〜十数人が同時に写真や動画を上げる・頁を開く）では届かない大きさにし、溢れた時だけ断る。断りの字は前からの字のまま
（写真と動画の口は本文を空にして返し、手帖が前からの「写真か動画を上げられませんでした」を出す）。

判断の芯:
- 写真と動画の変換（techo_site.save_media の写し直し・声とカメラの区切り）は CPU と一時の置き場を使うので、全体で同時に回す数を
  MEDIA_SLOTS に絞り、空きを待てる数（MEDIA_WAIT）と待つ長さ（MEDIA_WAIT_S）にも上限を置く（Gate）。待てる数を越えたら 503。
  本文（1 つ 20MB まで）は口に入ってから読むので、同時に持つ本文も (MEDIA_SLOTS + MEDIA_WAIT) × 20MB までになる
- 置き場の合計の照らしは、書き終わる前の分（同時に受けている途中の本文）を予約して数える（Reserve）。前は「今の合計＋今回の長さ」だけで、
  同時に送られた分が数え合わず、送られた数 × 20MB まで上限を越えうった
- 同時に処理する要求の数を、全体で HTTP_MAX に絞る（LimitedServer）。越えた要求は、読まずに 503 で閉じる。ふつうの量（頁と絵の読み込みで
  1 人あたり数本）では届かない
- 本番の HTTP サーバとプロキシでの接続数・本文の大きさ・締切の制御、CPU・メモリ・一時領域の制限は、この直しの外（PR の本文の「まだの所」）
"""
import threading
from http.server import ThreadingHTTPServer

MEDIA_SLOTS = 2       # 写真と動画の変換を、全体で同時に回す数
MEDIA_WAIT = 4        # 空きを待てる数（それより多く来たら断る）
MEDIA_WAIT_S = 60.0   # 待つ長さの上限（秒）。越えたら断る
HTTP_MAX = 64         # 同時に処理する要求の数（全体）
VOICE_QUEUE_MAX = 32  # 字にする前の声の待ち行列の長さ（omochae.voice_text の作業列）
BUSY_503 = b"HTTP/1.1 503 Service Unavailable\r\nContent-Length: 0\r\nRetry-After: 30\r\nConnection: close\r\n\r\n"


class Gate:
    """同時に回す数（slots）と、空きを待てる数（wait_max）と、待つ長さ（wait_s）の上限つきの入口。"""

    def __init__(self, slots=MEDIA_SLOTS, wait_max=MEDIA_WAIT, wait_s=MEDIA_WAIT_S):
        self._sem = threading.BoundedSemaphore(slots)
        self._lock = threading.Lock()
        self.waiting, self.wait_max, self.wait_s = 0, wait_max, wait_s

    def enter(self):
        """入れたら True（後で leave を 1 回呼ぶ）。待てる数を越えたか、待つ長さを越えたら False。"""
        if self._sem.acquire(blocking=False):
            return True
        with self._lock:
            if self.waiting >= self.wait_max:
                return False
            self.waiting += 1
        try:
            return self._sem.acquire(timeout=self.wait_s)
        finally:
            with self._lock:
                self.waiting -= 1

    def leave(self):
        self._sem.release()


class Reserve:
    """置き場の合計の予約。受けた時に長さを足し、書き終えたら（失敗でも）外す。"""

    def __init__(self):
        self._lock = threading.Lock()
        self.reserved = 0

    def take(self, used, length, total):
        """今の合計 used に、予約中の分と今回の length を足して total を越えなければ予約して True。"""
        with self._lock:
            if used + self.reserved + length > total:
                return False
            self.reserved += length
            return True

    def give(self, length):
        with self._lock:
            self.reserved = max(0, self.reserved - length)


class LimitedServer(ThreadingHTTPServer):
    """同時に処理する要求の数に上限のある ThreadingHTTPServer。越えた要求は読まずに 503 で閉じる。"""

    http_max = HTTP_MAX

    def server_activate(self):
        self._slots = threading.BoundedSemaphore(self.http_max)
        super().server_activate()

    def process_request(self, request, client_address):
        if not self._slots.acquire(blocking=False):
            try:
                request.sendall(BUSY_503)
            except OSError:
                pass
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self._slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._slots.release()
