"""外の命令を時間切れつきで呼ぶ所と、回ごとの一時の置き場（#29）。

なぜ 1 か所か: poppler や fontconfig が返らないと、命令も関門も止めるまで固まる。呼ぶ所ごとに書くと、足した所で付け忘れる。
切れた時は ToolMissing（exit 4・検査できない）にする。紙を見ていないので、落ちた（3）とは言わない。
"""
import math
import os
import pathlib
import re
import shutil
import subprocess
import tempfile
import time

from .model import ToolMissing

DEFAULT_TIMEOUT = 120.0  # 秒。ふだんは 1 秒もかからない。ほかの作業で混んだ機械でも、正常な命令を切らない長さにする
STALE_SECONDS = 3600  # 作った回の分からない置き場を、古いと読むまでの秒


def tool_timeout():
    raw = os.environ.get("OMOCHAE_TOOL_TIMEOUT")
    if raw is None:
        return DEFAULT_TIMEOUT
    try:
        value = float(raw)
    except ValueError:
        value = math.nan
    if not (value > 0 and math.isfinite(value)):  # 読めない値を、黙って時間切れ無しにしない
        raise ToolMissing(f"OMOCHAE_TOOL_TIMEOUT の値が読めない: {raw[:40]!r}")
    return value


def run_tool(cmd, fail, **kwargs):
    """外の命令を呼ぶ。無い・落ちた時は「fail: 理由」、返らない時は命令の名前と秒数を言って ToolMissing。"""
    limit = tool_timeout()
    try:
        return subprocess.run(cmd, capture_output=True, check=True, timeout=limit, **kwargs)
    except subprocess.TimeoutExpired:
        raise ToolMissing(f"{cmd[0]} が {limit:g} 秒で返らない")
    except (OSError, subprocess.CalledProcessError) as e:
        raise ToolMissing(f"{fail}: {e}")


def _alive(pid):
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, OverflowError):
        return False
    except PermissionError:
        return True
    return True


def _sweep(parent, prefix):
    """止められた回の置き場を片づける。後始末の finally は、外から止められた時は走らないので、次の回が見る。

    同じ所へ別の回が同時に書く事があるので、動いている回の物は消さない。名前に主の pid を入れて、生きているかで見る。
    pid の無い古い形は主が分からないので、時刻で見る。
    """
    pattern = re.compile(rf"{re.escape(prefix)}(\d+)-")
    now = time.time()
    for path in parent.glob(f"{prefix}*"):
        if path.is_symlink() or not path.is_dir():
            continue
        owner = pattern.match(path.name)
        try:
            stale = not _alive(int(owner.group(1))) if owner else now - path.stat().st_mtime > STALE_SECONDS
        except OSError:
            continue
        if stale:
            shutil.rmtree(path, ignore_errors=True)


def work_dir(parent, prefix):
    """この回だけの一時の置き場を parent の中に作る。消すのは呼ぶ側（finally）。"""
    parent = pathlib.Path(parent)
    _sweep(parent, prefix)
    return pathlib.Path(tempfile.mkdtemp(prefix=f"{prefix}{os.getpid()}-", dir=parent))
