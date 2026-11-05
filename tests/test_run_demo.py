"""run-demo.sh が、開かないリンクを案内しない（#159）。

実の cloudflared と網は使わない。トンネルは偽の命令に替え、「名前越しに開くか」は試験の口（DEMO_TUNNEL_VIA）で手元のサーバへ向ける。
repo の out/ に触らないよう、script を一時の木へ写して動かす。動いているデモの合言葉・リンク・置き場を試験が壊さないため。
port は毎回空きを取る。デモの決まった port には触らない。
"""
import os
import pathlib
import shutil
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from web import demo_check  # noqa: E402
from web.play_server import TUNNEL_HOST, serve  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
SAMPLE = "demo-abc" + TUNNEL_HOST.split("+", 1)[1].replace("\\", "")  # サーバが受ける形から作る見本の名前（実在のトンネルではない）
KEY = "k" * 24
FIRST_IMAGE = "out/sources/NDL-1187053-R0000005-L.jpg"


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def write_exec(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


def make_tree(base):
    """script の写しと、偽のトンネルの命令を置いた木を作る。図があるので取り込みの網には出ない。"""
    shutil.copy(ROOT / "run-demo.sh", base / "run-demo.sh")
    (base / "src").symlink_to(ROOT / "src")
    # pid はファイルで受ける（exec なので同じ pid のまま）。落ちる場面で、サーバとトンネルを狙って止めるため。
    write_exec(base / ".venv/bin/python",
               f'#!/bin/sh\ncase "$*" in *web.play_server*) echo $$ > server.pid;; esac\nexec "{sys.executable}" "$@"\n')
    write_exec(base / "bin/cloudflared",
               f'#!/bin/sh\ntouch tunnel-started\necho $$ > tunnel.pid\necho "https://{SAMPLE}"\nexec sleep 300\n')
    (base / FIRST_IMAGE).parent.mkdir(parents=True)
    (base / FIRST_IMAGE).touch()


def start(base, port, *args, via=None):
    env = {**os.environ, "PATH": f"{base / 'bin'}:{os.environ['PATH']}", "DEMO_PORT": str(port), "DEMO_TUNNEL_TRIES": "2"}
    env.pop("OMOCHAE_DATA", None)
    env.pop("PYTHONPATH", None)
    if via:
        env["DEMO_TUNNEL_VIA"] = via
    return subprocess.Popen(["bash", str(base / "run-demo.sh"), *args], cwd=base, env=env, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)


def finish(proc, timeout=60):
    """終わるのを待つ。時間切れは試験の失敗にする（固まったまま残さない）。"""
    try:
        return (*proc.communicate(timeout=timeout), proc.returncode)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        raise SystemExit("run-demo.sh が時間内に終わらない")


def wait_for_link(proc, base, timeout=60):
    url = base / "out/demo-url"
    end = time.time() + timeout
    while time.time() < end:
        if url.exists():
            return url.read_text(encoding="utf-8").strip()
        if proc.poll() is not None:
            raise SystemExit(f"リンクの前に終わった: rc={proc.returncode} {proc.stderr.read()[-500:]}")
        time.sleep(0.2)
    os.killpg(proc.pid, signal.SIGKILL)
    raise SystemExit("リンクが時間内に出ない")


def stop(proc):
    os.kill(proc.pid, signal.SIGTERM)
    return finish(proc)


def kill_pid_in(path):
    os.kill(int(path.read_text(encoding="utf-8")), signal.SIGKILL)


def closed(port):
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def check_cli(url, key_file):
    return subprocess.run([sys.executable, "-m", "web.demo_check", url, "--key-file", str(key_file)],
                          cwd=ROOT, env={**os.environ, "PYTHONPATH": "src"}, capture_output=True, text=True)


# 1 開くかを見る口: 合言葉が合うサーバだけを「開く」と読む
good = serve(0, public_key=KEY)
threading.Thread(target=good.serve_forever, daemon=True).start()
gp = good.server_address[1]
assert demo_check.opens(f"http://127.0.0.1:{gp}", KEY) is None, "合言葉が合えば開く"
assert demo_check.opens(f"https://{SAMPLE}", KEY, via=f"http://127.0.0.1:{gp}") is None, "トンネルの名前でも開く"
why = demo_check.opens(f"http://127.0.0.1:{gp}", "x" * 24)
assert why and "x" * 24 not in why, "合言葉が違えば開かない。理由の文に合言葉を出さない"
assert demo_check.opens(f"http://127.0.0.1:{free_port()}", KEY), "誰もいない口は開かない"
assert not demo_check.port_free(gp) and demo_check.port_free(free_port()), "使用中の port が分かる"
print("ok opens")

with tempfile.TemporaryDirectory() as tmp:
    # 2 port が塞がっている時: リンクを案内せず 4。前からあるリンク・合言葉・置き場は、動いているデモの物なので触らない
    base = pathlib.Path(tmp).resolve() / "busy"
    base.mkdir()
    make_tree(base)
    (base / "out/demo-url").write_text("https://old/?k=old\n", encoding="utf-8")
    (base / "out/demo-key").write_text(KEY + "\n", encoding="utf-8")
    (base / "out/demo-data").mkdir()
    (base / "out/demo-data/keep").touch()
    with socket.socket() as blocker:
        blocker.bind(("127.0.0.1", 0))
        blocker.listen()
        port = blocker.getsockname()[1]
        out, err, rc = finish(start(base, port, "--fresh"))
    assert "リンク" not in out, f"塞がっているのにリンクを案内した: {out}"
    assert rc == 4, (rc, err)
    assert str(port) in err and "使用中" in err, err
    assert (base / "out/demo-url").read_text(encoding="utf-8") == "https://old/?k=old\n", "動いているデモのリンクを消した"
    assert (base / "out/demo-key").read_text(encoding="utf-8").strip() == KEY, "動いているデモの合言葉を変えた"
    assert (base / "out/demo-data/keep").exists(), "動いているデモの置き場を消した"
    assert not (base / "tunnel-started").exists(), "塞がっているのにトンネルを立てた"
    print("ok busy port")

    # 3 サーバが立った直後に落ちる時（短すぎる合言葉）: 理由を出して 4。古いリンクも残さない
    base = pathlib.Path(tmp).resolve() / "dead"
    base.mkdir()
    make_tree(base)
    (base / "out/demo-url").write_text("https://old/?k=old\n", encoding="utf-8")
    (base / "out/demo-key").write_text("short\n", encoding="utf-8")
    out, err, rc = finish(start(base, free_port()))
    assert rc == 4, (rc, err)
    assert "合言葉が短すぎる" in err, err
    assert "リンク" not in out and not (base / "out/demo-url").exists(), (out, err)
    assert not (base / "tunnel-started").exists(), "サーバが立っていないのにトンネルを立てた"
    print("ok server died at start")

    # 4 トンネルの名前は出たが、名前越しに開かない時: リンクを案内せず 4
    base = pathlib.Path(tmp).resolve() / "unreachable"
    base.mkdir()
    make_tree(base)
    out, err, rc = finish(start(base, free_port(), via=f"http://127.0.0.1:{free_port()}"))
    assert rc == 4, (rc, err)
    assert "リンク" not in out and not (base / "out/demo-url").exists(), (out, err)
    assert "開けません" in err and SAMPLE in err, err
    print("ok tunnel unreachable")

    # 5 開く時: 合言葉付きのリンクを案内する。止めるとリンクは消え、サーバも止まり、終わりは 0
    base = pathlib.Path(tmp).resolve() / "open"
    base.mkdir()
    make_tree(base)
    port = free_port()
    proc = start(base, port, via=f"http://127.0.0.1:{port}")
    link = wait_for_link(proc, base)
    key = (base / "out/demo-key").read_text(encoding="utf-8").strip()
    assert link == f"https://{SAMPLE}/?k={key}", link
    (base / "out/demo-data/keep").touch()
    out, err, rc = stop(proc)
    assert rc == 0, (rc, err)
    assert "リンク" in out and key not in out and key not in err, "案内はするが、合言葉は画面に出さない"
    assert not (base / "out/demo-url").exists(), "止めた後にリンクが残った"
    assert closed(port), "止めた後もサーバが残った"
    print("ok open and stop")

    # 6 続けて立てる時は合言葉と置き場を保つ。--fresh の後は、前の合言葉で入れない
    proc = start(base, port, via=f"http://127.0.0.1:{port}")
    wait_for_link(proc, base)
    assert (base / "out/demo-key").read_text(encoding="utf-8").strip() == key, "--fresh なしで合言葉が変わった"
    assert (base / "out/demo-data/keep").exists(), "--fresh なしで置き場が消えた"
    stop(proc)
    (base / "old-key").write_text(key + "\n", encoding="utf-8")
    proc = start(base, port, "--fresh", via=f"http://127.0.0.1:{port}")
    wait_for_link(proc, base)
    new = (base / "out/demo-key").read_text(encoding="utf-8").strip()
    assert new != key, "--fresh で合言葉が変わらない"
    assert not (base / "out/demo-data/keep").exists(), "--fresh で置き場が空にならない"
    assert check_cli(f"http://127.0.0.1:{port}", base / "out/demo-key").returncode == 0, "新しい合言葉で入れない"
    old = check_cli(f"http://127.0.0.1:{port}", base / "old-key")
    assert old.returncode == 4 and key not in old.stderr, "前の合言葉で入れた"
    print("ok fresh key")

    # 7 動いている間にサーバが落ちた時: 黙って終わらず 4。リンクは消す
    kill_pid_in(base / "server.pid")
    out, err, rc = finish(proc)
    assert rc == 4 and "サーバが止まりました" in err, (rc, err)
    assert not (base / "out/demo-url").exists(), "サーバが落ちた後にリンクが残った"
    print("ok server died later")

    # 8 動いている間にトンネルが落ちた時: サーバが動いていても黙らず 4（リンクはもう開かない）
    proc = start(base, port, via=f"http://127.0.0.1:{port}")
    wait_for_link(proc, base)
    kill_pid_in(base / "tunnel.pid")
    out, err, rc = finish(proc)
    assert rc == 4 and "トンネルが止まりました" in err, (rc, err)
    assert not (base / "out/demo-url").exists(), "トンネルが落ちた後にリンクが残った"
    assert closed(port), "トンネルが落ちた後にサーバが残った"
    print("ok tunnel died later")

    logs = "".join(p.read_text(encoding="utf-8", errors="replace") for p in (base / "out").glob("demo-*.log"))
    assert new not in logs, "ログに合言葉が残った"

shutil.rmtree(os.environ["OMOCHAE_DATA"], ignore_errors=True)
print("ok")
