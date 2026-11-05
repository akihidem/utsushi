"""記録・輪・自分の仮説の置き場の読み書き（#153）。

書き込み: 本番のファイルに直に書くと、途中で止まった時に書きかけが残り、次に読む頁が全部止まる。一時ファイルに書いてから確定する。
読み込み: 一覧を作る時は、読めない 1 件を飛ばして、どのファイルかを stderr に出す。1 件のために全部の玩具の頁を止めない。
排他: デモは複数の機器が同じ置き場に書き、サーバが 2 つのプロセスに分かれる事もある。threading.Lock では足りないので、置き場のロックファイルを使う。
"""
import contextlib
import fcntl
import json
import os
import pathlib
import sys
import tempfile
import threading

_UMASK = os.umask(0)  # umask は読むだけの口が無い。スレッドが動く前の import の時に 1 回だけ読む。
os.umask(_UMASK)
_held = threading.local()

# 玩具の頁の ID の形。source_id をパスにつなぐ前に、画面・Claude の道具・MCP の口で同じ式で確かめる（#174）。
# 1 頁に玩具が何個もある時は、頁の印の後に -2, -3 と番号を足す（全部の玩具を作る、本人の指示 11-04）。1 個目は番号なし。
SID = r"NDL-\d+-R\d+-[LR](?:-\d+)?"


def write_atomic(path, data, exclusive=False, mode=None):
    """途中の状態を読ませないよう、一時ファイルに書いてから確定する。exclusive は同じ番号を上書きしない。mode が無ければ umask に従う。"""
    payload = data if isinstance(data, bytes) else data.encode("utf-8")
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(payload)
        os.chmod(tmp, 0o666 & ~_UMASK if mode is None else mode)
        if exclusive:
            os.link(tmp, path)
        else:
            os.replace(tmp, path)
            tmp = None
    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)


def write_json(path, obj, exclusive=False):
    write_atomic(path, json.dumps(obj, ensure_ascii=False, indent=2) + "\n", exclusive=exclusive)


def read_json_or_skip(path, kind=dict):
    """一覧のための読み。無ければ None。読めない・形が違う時も None にして、どのファイルかを stderr に出す。"""
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as e:
        print(f"読めない記録を飛ばした: {path.name}（{type(e).__name__}）", file=sys.stderr)
        return None
    if not isinstance(obj, kind):
        print(f"読めない記録を飛ばした: {path.name}（形が違う）", file=sys.stderr)
        return None
    return obj


@contextlib.contextmanager
def locked(folder):
    """置き場ごとの排他。flock は開いたファイルごとに効くので、別のスレッドとも別のプロセスとも取り合う。同じスレッドが重ねて取っても固まらない。"""
    key = str(pathlib.Path(folder).resolve())
    depth = _held.__dict__.setdefault("depth", {})
    if depth.get(key):
        depth[key] += 1
        try:
            yield
        finally:
            depth[key] -= 1
        return
    with open(pathlib.Path(folder) / ".lock", "a", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)  # 閉じると外れる
        depth[key] = 1
        try:
            yield
        finally:
            depth[key] = 0
