"""exit code の決まり（0・3・4）の外に出ない事を見る（#25）。壊れた場面と壊れた雛形で、トレースバックの 1 でなく、名前を言って 4 で止まる。

小さな tree に写して壊す。本物の場面と雛形は触らない。
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
PY = sys.executable
GOOD = {"template": "slider_fan", "source_id": "x", "params": {}, "inject": {}, "expect": {"rc": 0, "floors": []}}


def floors(scenarios):
    """場面だけを置いた tree で床の入口を回す。.venv は無いので、場面を回す所まで進めば別の理由で止まる。"""
    root = pathlib.Path(tempfile.mkdtemp(dir=BASE))
    (root / "tests/frozen/scenarios").mkdir(parents=True)
    shutil.copy(ROOT / "tests/run_floors.py", root / "tests/run_floors.py")
    for name, text in scenarios.items():
        (root / "tests/frozen/scenarios" / name).write_text(text, encoding="utf-8")
    # 照合の表は今の場面から書く。見たいのは表と合った後の読み込みと回す所（表の見張りは test_frozen_manifest が見る）。
    subprocess.run([PY, str(root / "tests/run_floors.py"), "--write-manifest"], capture_output=True, check=True)
    return root, subprocess.run([PY, str(root / "tests/run_floors.py")], capture_output=True, text=True)


def engine(broken=None):
    """エンジンを写した tree を作り、broken の雛形を足す。(root, 環境) を返す。"""
    root = pathlib.Path(tempfile.mkdtemp(dir=BASE))
    shutil.copytree(ROOT / "src", root / "src", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(ROOT / "data/sources", root / "data/sources")
    for name, text in (broken or {}).items():
        (root / "src/omochae/templates" / name).write_text(text, encoding="utf-8")
    return root, {**os.environ, "PYTHONPATH": str(root / "src")}


with tempfile.TemporaryDirectory() as BASE:
    # 1. 壊れた場面は、1 つも回さずに名指しして 4（途中まで回すと、結果の表が半端に残るため）
    for name, text in (("cut.json", '{"template": "slider_fan", "expect": {"rc"'),
                       ("no_expect.json", json.dumps({"template": "slider_fan"})),
                       ("list.json", "[]"),
                       ("no_floors.json", json.dumps({"expect": {"rc": 0}})),
                       ("floors_num.json", json.dumps({"expect": {"rc": 0, "floors": 3}}))):
        root, r = floors({"good.json": json.dumps(GOOD), name: text})
        assert r.returncode == 4 and name in r.stderr and "good.json" not in r.stderr, (name, r.returncode, r.stderr)
        assert "Traceback" not in r.stderr and not (root / "out/RESULT.md").exists(), (name, r.stderr)
    # 2. 場面が読めても、回す所で思わぬ失敗をしたら 4（.venv が無い時）。トレースバックは出さない
    root, r = floors({"good.json": json.dumps(GOOD)})
    assert r.returncode == 4 and "検査できない" in r.stderr and "Traceback" not in r.stderr, (r.returncode, r.stderr)

    # 3. 壊れた雛形があると、関係の無い雛形の場面でも、壊れた雛形の名前を言って 4
    scenario = str(ROOT / "examples/fan_tab.json")
    breaks = {"zz_syntax.py": "def (\n", "zz_raise.py": "raise ValueError('読むと落ちる')\n", "zz_import.py": "import no_such_module_here\n"}
    for name, text in breaks.items():
        root, env = engine({name: text})
        # omochae.fold3d も同じ読み込みの囲いを通る（--out を持たないが、読み込みで先に 4 になる）
        for mod in ("omochae", "omochae.foldsim", "omochae.fold3d"):
            r = subprocess.run([PY, "-m", mod, "--scenario", scenario, "--out", str(root / "o")], cwd=root, env=env, capture_output=True, text=True)
            assert r.returncode == 4 and name[:-3] in r.stderr and "Traceback" not in r.stderr, (mod, name, r.returncode, r.stderr)
    # ID が重なる雛形も同じ
    root, env = engine({"zz_dup.py": "ID = 'slider_fan'\n"})
    r = subprocess.run([PY, "-m", "omochae", "--scenario", scenario, "--out", str(root / "o")], cwd=root, env=env, capture_output=True, text=True)
    assert r.returncode == 4 and "zz_dup" in r.stderr and "Traceback" not in r.stderr, (r.returncode, r.stderr)
    # 4. 壊さなければ同じ tree で通る（上の 4 が、写し方のせいでない事を見る）
    root, env = engine()
    r = subprocess.run([PY, "-m", "omochae", "--scenario", scenario, "--out", str(root / "o")], cwd=root, env=env, capture_output=True, text=True)
    assert r.returncode == 0 and (root / "o.pdf").exists(), (r.returncode, r.stderr)
print("ok")
