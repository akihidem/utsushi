"""デモのリンクの先が本当に開くかを見る（run-demo.sh から呼ぶ。#159）。

使い方: python -m web.demo_check <URL の頭> --key-file <合言葉のファイル> [--via <つなぐ先>]
        python -m web.demo_check --port-free <port>
exit: 0 = 開く・port が空いている / 4 = 開かない・port が使用中。理由は stderr に 1 行。

決めた事と理由:
- 合言葉付きのリンクを開いた後（303）、Cookie で頁まで開く（200）。人が踏む順と同じにする。トンネルは口だけ開いていて奥へつながらない
  時があり、別の合言葉で動いている別のサーバは 303 を返さないので、両方ともここで「開かない」と読む。
- 合言葉は引数に書かない（ps で見える。play_server と同じ）。理由の文にも出さない（端末とログに残さないため）。
- --via は試験のための口。網を使わずに、トンネルの名前を手元のサーバへ向ける。
- port の先の確かめは、サーバを立てる前に別に見る。立てた後に見ると、塞いでいる相手が答えた分を自分のサーバと取り違えるため。
"""
import argparse
import http.client
import pathlib
import socket
import sys
import urllib.error
import urllib.parse
import urllib.request

TIMEOUT = 5  # 秒。1 回の GET。やり直しは呼ぶ側（run-demo.sh）が持つ


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None  # 303 の Location と Set-Cookie を、こちらで見るため


def _get(url, host, cookie=None):
    headers = {"Host": host, "User-Agent": "utsushi-demo-check"}  # 既定の名前は、トンネルの前で断られる事がある
    if cookie:
        headers["Cookie"] = cookie
    handlers = [_NoRedirect()]
    if url.startswith("http://127.0.0.1"):
        handlers.append(urllib.request.ProxyHandler({}))  # 手元の口を、網の設定の proxy へ回さない
    try:
        with urllib.request.build_opener(*handlers).open(urllib.request.Request(url, headers=headers), timeout=TIMEOUT) as r:
            return r.status, r.headers
    except urllib.error.HTTPError as e:
        return e.code, e.headers


def opens(base, key, via=None):
    """開くなら None、開かないなら理由の文を返す。"""
    base = base.rstrip("/")
    host = urllib.parse.urlsplit(base).netloc
    target = (via or base).rstrip("/")
    try:
        code, headers = _get(f"{target}/?{urllib.parse.urlencode({'k': key})}", host)
        if code != 303 or not headers.get("Set-Cookie", "").startswith("utsushi_k="):
            return f"合言葉付きのリンクに {code} が返った（303 を待っていた）"
        code, _ = _get(f"{target}/", host, cookie=f"utsushi_k={key}")
        return None if code == 200 else f"頁を開くと {code} が返った（200 を待っていた）"
    except (OSError, http.client.HTTPException) as e:
        return f"つながらない（{type(e).__name__}）"


def port_free(port):
    with socket.socket() as s:
        s.settimeout(TIMEOUT)
        return s.connect_ex(("127.0.0.1", port)) != 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("base", nargs="?")
    ap.add_argument("--key-file")
    ap.add_argument("--via")
    ap.add_argument("--port-free", type=int)
    args = ap.parse_args(argv)
    if args.port_free is not None:
        if port_free(args.port_free):
            return 0
        print(f"port {args.port_free} は使用中です（前のデモが動いていないか見てください。別の port は DEMO_PORT で選べます）", file=sys.stderr)
        return 4
    if not args.base:
        print("URL の頭か --port-free が要る", file=sys.stderr)
        return 4
    try:
        key = pathlib.Path(args.key_file).read_text(encoding="utf-8").strip()
    except (OSError, TypeError) as e:
        print(f"合言葉のファイルが読めない（{type(e).__name__}）", file=sys.stderr)
        return 4
    why = opens(args.base, key, via=args.via)
    if why:
        print(why, file=sys.stderr)
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
