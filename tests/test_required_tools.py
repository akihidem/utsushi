"""要る物が足りない機械で、床の入口が「落ちた（3）」でなく「検査できない（4）」と名前を言って止まる事を見る（#160）。

小さな tree に床の入口を写し、偽の道具だけを置いた PATH で回す。本物の場面は回らない。
道具の確かめが消えても、偽の python で場面がすぐ終わるので、この試験が自分を呼び直す事は無い。
"""
import importlib.metadata
import json
import os
import pathlib
import re
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

# Python の版（#227）。README・init.sh・固定した依存が同じ下限を言い、足りない時は init.sh が 4 で名指しする
MIN_PY = re.search(r"^MIN_PY=(\d+\.\d+)$", init, re.M).group(1)
assert f"Python {MIN_PY} 以上" in readme, readme


def ver(text):
    return tuple(int(x) for x in text.split("."))


pins = re.findall(r"^([\w-]+)==", (ROOT / "requirements.txt").read_text(encoding="utf-8"), re.M)
assert pins
for name in pins:
    floor = re.search(r">=\s*(\d+\.\d+)", importlib.metadata.metadata(name).get("Requires-Python") or "")
    assert not floor or ver(floor.group(1)) <= ver(MIN_PY), (name, floor.group(1), MIN_PY)


def runs_init(venv_python=None, uv_venv_rc=0, new_python="3.12"):
    """偽の道具で init.sh を回し、(rc, stderr, uv が受けた引数の行) を返す。古い Python を試験の機械に置けないので、比べ方と止まる所だけを見る。"""
    root = pathlib.Path(tempfile.mkdtemp(dir=BASE.name))
    shutil.copy(ROOT / "init.sh", root / "init.sh")
    (root / "requirements.txt").write_text("", encoding="utf-8")
    for tool in run_floors.TOOLS:
        stub(root / "bin" / tool)
    stub(root / "bin/fc-list", f"#!/bin/sh\necho '{run_floors.FONT}'\n")
    stub(root / "bin/uv", f"""#!/bin/bash
echo "$*" >> "{root}/uv.log"
if [ "$1" = venv ]; then
  [ {uv_venv_rc} -eq 0 ] || exit {uv_venv_rc}
  mkdir -p .venv/bin; printf '#!/bin/sh\\necho {new_python}\\n' > .venv/bin/python; chmod +x .venv/bin/python
fi
""")
    if venv_python:
        stub(root / ".venv/bin/python", f"#!/bin/sh\necho {venv_python}\n")
    env = {**os.environ, "PATH": f"{root}/bin:/usr/bin:/bin"}
    r = subprocess.run(["bash", str(root / "init.sh")], cwd=root, env=env, capture_output=True, text=True)
    log = root / "uv.log"
    return r.returncode, r.stderr, log.read_text(encoding="utf-8") if log.exists() else ""


# 版の合う Python が無い: 4 で版を名指しし、依存を入れに進まない
rc, err, uv = runs_init(uv_venv_rc=2)
assert rc == 4 and f"Python {MIN_PY} 以上" in err and "pip install" not in uv, (rc, err, uv)
# 版の合う Python がある: 範囲を渡し、黙って Python を落とさない形で作り、依存を入れる
rc, err, uv = runs_init()
assert rc == 0 and f">={MIN_PY}" in uv and "--no-python-downloads" in uv and "pip install" in uv, (rc, err, uv)
# 前からある .venv の版も見る（3.9 と 3.11 を字の順で比べると逆になる）
major, minor = ver(MIN_PY)
for old in (f"{major}.{minor - 1}", "3.9"):
    rc, err, uv = runs_init(venv_python=old)
    assert rc == 4 and f"Python {MIN_PY} 以上" in err and old in err and "pip install" not in uv, (old, rc, err, uv)
for good in (MIN_PY, f"{major}.{minor + 3}"):
    rc, err, uv = runs_init(venv_python=good)
    assert rc == 0 and not uv.startswith("venv"), (good, rc, err, uv)  # 前からある .venv を作り直さない
print(f"ok 道具 {len(run_floors.TOOLS)} 個と .venv と字と Python の版を、足りない時は 4 で名指しする")
