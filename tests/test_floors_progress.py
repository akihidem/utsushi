"""./run.sh の進み。端末で見ている人に、1 本ずつ本数と名前を出す。

全部で 8〜9 分かかるのに最後の 1 行のほかに何も出ないので、止まったのと見分けがつかなかった。
管やファイルには出さない: 合体の道は失敗の時に出力の末尾 15 行だけを見せるので、進みの行が NG の行を押し流す。
別のプロセスで、一時の根（試験 2 本だけの repo の形）に向けて main を回す（test_floors_hygiene.py と同じ形）。
"""
import os
import pathlib
import pty
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
DRIVER = """
import pathlib, sys
sys.path.insert(0, sys.argv[1])
import run_floors as rf
rf.ROOT = pathlib.Path(sys.argv[2])
rf.PY = sys.executable
rf.MANIFEST = "tests/frozen/manifest.json"
rf.write_manifest(rf.ROOT)
sys.exit(rf.main())
"""
root = pathlib.Path(BASE.name) / "root"
(root / "tests/frozen/scenarios").mkdir(parents=True)
(root / "tests/frozen/criteria.md").write_text("基準\n", encoding="utf-8")
(root / "tests/test_aa.py").write_text("print('ok')\n", encoding="utf-8")
(root / "tests/test_bb.py").write_text("assert False, '落ちる見本'\n", encoding="utf-8")
env = {k: v for k, v in os.environ.items() if k != "PYTHONOPTIMIZE"}
cmd = [sys.executable, "-c", DRIVER, str(ROOT / "tests"), str(root)]
LAST = "実行した 2 本（場面 0 本、試験 2 本）、期待どおり 1 本、未実装の床 0 本。"

# 1. 端末なら、本数と名前が順に出る。最後の行の形は変わらない
master, slave = pty.openpty()
proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=slave, text=True)
os.close(slave)
seen = b""
while True:
    try:
        chunk = os.read(master, 4096)
    except OSError:  # 子が閉じると Linux では EIO
        break
    if not chunk:
        break
    seen += chunk
os.close(master)
out = proc.communicate(timeout=60)[0]
lines = seen.decode("utf-8").replace("\r\n", "\n").splitlines()
assert proc.returncode == 3, proc.returncode
assert [ln for ln in lines if re.fullmatch(r"\d+/\d+ \S+", ln)] == ["1/2 test_aa", "2/2 test_bb"], lines
assert any(ln.startswith("NG test_bb") for ln in lines), lines
assert out.strip().splitlines()[-1] == LAST, out

# 2. 管なら進みを出さない。NG の行と最後の行だけ
r = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=60)
assert r.returncode == 3, r.returncode
assert r.stdout.strip().splitlines()[-1] == LAST, r.stdout
assert not re.findall(r"^\d+/\d+ ", r.stderr, re.M), r.stderr
assert "NG test_bb" in r.stderr, r.stderr
print("ok ./run.sh は端末にだけ、1 本ずつ本数と名前を出す")
