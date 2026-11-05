"""結果の表（out/RESULT.md）の命令は、そのまま貼って回せる。場面と試験の数は別々に出る（#170）。

なぜ: 表は全部の行に `--scenario <名前>` と書いていて、試験の行では実在しない命令だった。最後の行も、場面と試験を
足した数を「場面」と呼んでいて、文書が引く数がどちらを指すのか分からなかった。
"""
import contextlib
import io
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

from demo import build

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
import run_floors  # noqa: E402

# 本物の場面（通る物と落ちる物）と、試験 2 本だけの小さな tree。本物の out/ は触らない。
root = pathlib.Path(tempfile.mkdtemp())
(root / "tests/frozen/scenarios").mkdir(parents=True)
for name in ("pos_stick", "neg_fan_length"):
    shutil.copy(ROOT / f"tests/frozen/scenarios/{name}.json", root / "tests/frozen/scenarios")
(root / "src").symlink_to(ROOT / "src")
(root / ".venv").symlink_to(ROOT / ".venv")
# 表の命令と同じ形で回っている事を、子の環境で見る。
(root / "tests/test_same_form.py").write_text("import os\nassert os.environ['PYTHONPATH'] == 'src'\n", encoding="utf-8")
(root / "tests/test_red.py").write_text("raise SystemExit(5)\n", encoding="utf-8")
with contextlib.redirect_stdout(io.StringIO()):
    run_floors.write_manifest(root)

keep = run_floors.ROOT
run_floors.ROOT = root
try:
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        rc = run_floors.main()
finally:
    run_floors.ROOT = keep
assert rc == 3, rc  # test_red が期待の外

text = (root / "out/RESULT.md").read_text(encoding="utf-8")
rows = {}
for line in text.splitlines():
    cells = [c.strip() for c in line.strip("|").split("|")]
    if len(cells) == 7 and cells[1].startswith("`"):
        rows[cells[0]] = (cells[1].strip("`"), int(cells[2]), cells[6])
assert set(rows) == {"pos_stick", "neg_fan_length", "test_same_form", "test_red"}, rows
assert rows["test_same_form"][2] == "OK" and rows["test_red"][2] == "NG", rows
assert rows["test_red"][1] == 5, rows

# 表のどの行も、repo の根で貼ると、表の rc で返る。呼ぶ側の PYTHONPATH には頼らない。
env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
for name, (cmd, want, _) in rows.items():
    pasted = subprocess.run(["bash", "-c", cmd], cwd=root, env=env, capture_output=True, text=True)
    assert pasted.returncode == want, (name, cmd, pasted.returncode, want, pasted.stderr[-300:])
    assert "--scenario" in cmd if name.startswith(("pos_", "neg_")) else f"tests/{name}.py" in cmd, cmd

# 数は場面と試験で別々。動画の場面 4 が読む合計（build.count_tests）も同じ行から読める。
last = text.strip().splitlines()[-1]
assert re.search(r"場面 2 本、試験 2 本", last), last
assert build.count_tests(last) == (4, 3), last

shutil.rmtree(root)
print("ok")
