"""要る物が足りない機械で、床の入口が「落ちた（3）」でなく「検査できない（4）」と名前を言って止まる事を見る（#160）。

小さな tree に床の入口を写し、偽の道具だけを置いた PATH で回す。本物の場面は回らない。
道具の確かめが消えても、偽の python で場面がすぐ終わるので、この試験が自分を呼び直す事は無い。
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
import run_floors  # noqa: E402

FOUND = "#!/bin/sh\necho :file=/fonts/NotoSerifCJK-Regular.ttc\n"
NO_FONT = "#!/bin/sh\necho :file=/fonts/DejaVuSans.ttf\n"
BASE = tempfile.TemporaryDirectory()  # 写しは終わる時にまとめて消す


def stub(path, body="#!/bin/sh\nexit 0\n"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)


def tree(venv=True):
    root = pathlib.Path(tempfile.mkdtemp(dir=BASE.name))
    shutil.copytree(ROOT / "tests/frozen", root / "tests/frozen")
    for t in json.loads((ROOT / run_floors.MANIFEST).read_text(encoding="utf-8"))["tests"]:
        (root / "tests" / f"{t}.py").write_text("", encoding="utf-8")
    shutil.copy(ROOT / "tests/run_floors.py", root / "tests/run_floors.py")
    if venv:
        stub(root / ".venv/bin/python")
    return root


def runs(root, without=(), fc_match=FOUND):
    bin_dir = root / "bin"
    for tool in run_floors.TOOLS:
        if tool not in without:
            stub(bin_dir / tool, fc_match if tool == "fc-match" else "#!/bin/sh\nexit 0\n")
    bin_dir.mkdir(exist_ok=True)
    env = {**os.environ, "PATH": str(bin_dir)}
    return subprocess.run([sys.executable, str(root / "tests/run_floors.py")], env=env, capture_output=True, text=True)


# 道具を 1 つずつ外す。外した物の名前が出て 4。結果の表は書かない（回していないので）
assert "ffmpeg" in run_floors.TOOLS and "ffprobe" in run_floors.TOOLS
for tool in run_floors.TOOLS:
    root = tree()
    r = runs(root, without=(tool,))
    assert r.returncode == 4 and f"検査できない: {tool} が無い" in r.stderr, (tool, r.returncode, r.stderr)
    assert not (root / "out/RESULT.md").exists(), tool
# 2 つ足りない時は、両方の名前を 1 回で言う
r = runs(tree(), without=("ffmpeg", "pdftotext"))
assert r.returncode == 4 and "ffmpeg が無い" in r.stderr and "pdftotext が無い" in r.stderr, r.stderr
# .venv が無い時に床の入口を直に呼んでも、トレースバックの 1 でなく 4
r = runs(tree(venv=False))
assert r.returncode == 4 and ".venv が無い" in r.stderr and "Traceback" not in r.stderr, (r.returncode, r.stderr)
# 字が無い時も 4
r = runs(tree(), fc_match=NO_FONT)
assert r.returncode == 4 and f"字 {run_floors.FONT} が無い" in r.stderr, (r.returncode, r.stderr)
# 全部そろっていれば確かめを越えて回る（この確かめがいつも 4 を返すのでは、上の 4 に意味が無い）
root = tree()
r = runs(root)
assert "検査できない" not in r.stderr and (root / "out/RESULT.md").exists(), (r.returncode, r.stderr)

# README・init.sh・床の入口の一覧が同じ。uv は環境を作る時だけ使うので、README と init.sh にだけ在る
readme = next(l for l in (ROOT / "README.md").read_text(encoding="utf-8").splitlines() if l.startswith("要る物:"))
init = (ROOT / "init.sh").read_text(encoding="utf-8")
loop = next(l for l in init.splitlines() if l.startswith("for c in "))
assert loop.split(";")[0].split()[3:] == ["uv", *run_floors.TOOLS], loop
for tool in run_floors.TOOLS:
    assert f"`{tool}`" in readme, tool
assert "uv" in readme and run_floors.FONT in readme and run_floors.FONT in init
assert "sudo apt install" in readme and "ffmpeg" in readme.split("sudo apt install")[1]
print(f"ok 道具 {len(run_floors.TOOLS)} 個と .venv と字を、足りない時は 4 で名指しする")
