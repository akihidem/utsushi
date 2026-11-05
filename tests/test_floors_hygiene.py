"""run_floors の床（#169）: 止まった試験で関門が固まらず、試験の一時の置き場を残さない。全部の網に口を開かない。

別のプロセスで、一時の根（試験 1 本だけの repo の形）に向けて main を回す。本物の試験を回し直さないため。
"""
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
DRIVER = """
import pathlib, sys
sys.path.insert(0, sys.argv[1])
import run_floors as rf
rf.ROOT = pathlib.Path(sys.argv[2])
rf.PY = sys.executable
rf.STEP_TIMEOUT = 2
rf.MANIFEST = "tests/frozen/manifest.json"
rf.write_manifest(rf.ROOT)
sys.exit(rf.main())
"""


def run_with(test_body, within=40):
    """試験 1 本だけの根で main を回し、(rc, 根) を返す。関門が固まったら外の時間切れで落とす。"""
    root = pathlib.Path(tempfile.mkdtemp(dir=BASE.name))
    (root / "tests/frozen/scenarios").mkdir(parents=True)
    (root / "tests/frozen/criteria.md").write_text("基準\n", encoding="utf-8")
    (root / "tests/test_one.py").write_text(test_body, encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if k != "PYTHONOPTIMIZE"}
    r = subprocess.run([sys.executable, "-c", DRIVER, str(ROOT / "tests"), str(root)], env=env, capture_output=True, text=True, timeout=within)
    return r, root


# 1. 眠るだけの試験は、決めた時間で「検査できない（4）」。孫が出力の管を持ったままでも固まらず、孫も残らない
mark = f"utsushi-floors-sleep-{os.getpid()}"
started = time.monotonic()
r, root = run_with(f"""
import subprocess, sys, time
subprocess.Popen(["bash", "-c", "exec -a {mark} sleep 60"])
time.sleep(60)
""")
assert r.returncode == 4, (r.returncode, r.stderr[-400:])
assert time.monotonic() - started < 30, "決めた時間で切れていない"
assert "時間切れ" in r.stderr and "test_one" in r.stderr, r.stderr[-400:]
result = (root / "out/RESULT.md").read_text(encoding="utf-8")
assert "| test_one |" in result and "| NG |" in result, result
left = subprocess.run(["pgrep", "-f", mark], capture_output=True, text=True).stdout.split()
assert not left, f"孫が残った: {left}"

# 2. 試験の一時の置き場は、回した後に残らない（試験を消し忘れても、走りの置き場ごと消える）
r, root = run_with("""
import pathlib, sys, tempfile
d = pathlib.Path(tempfile.mkdtemp())
(d / "x").write_text("ごみ")
print(d)
pathlib.Path(sys.argv[0]).with_name("made.txt").write_text(str(d))
""")
assert r.returncode == 0, (r.returncode, r.stderr[-400:])
made = pathlib.Path((root / "tests/made.txt").read_text())
assert not made.exists(), f"一時の置き場が残った: {made}"

# 3. 全部の網に開く形は、口の決め方だけを見る。試験の間に 0.0.0.0 で待たない（試験は手元の口で動かす）
from web.play_server import bind_host, serve  # noqa: E402

assert bind_host(False) == "127.0.0.1" and bind_host(True) == "0.0.0.0"
os.environ.setdefault("OMOCHAE_DATA", tempfile.mkdtemp(dir=BASE.name))
lan = serve(0, lan=True, bind="127.0.0.1")
try:
    assert lan.server_address[0] == "127.0.0.1" and lan.lan_hosts, "網の中の番地の許しは --lan のまま"
finally:
    lan.server_close()
# どの試験も、--lan の形を試す時は手元の口を言う（1 本ずつ名指しにすると、足した試験が漏れる）
opened = [p.name for p in (ROOT / "tests").glob("test_*.py") if p.name != pathlib.Path(__file__).name
          and re.search(r"serve\([^)\n]*lan=True(?![^)\n]*bind=)", p.read_text(encoding="utf-8"))]
assert not opened, f"試験が全部の網に口を開いている: {opened}"
print("ok floors hygiene")
