"""場面や引数の値で、決めた置き場の外を読み書きできない事を見る（#30）。

なぜ形で見るか: 受付やサイトが、人から受けた値を場面に入れてエンジンに渡す形になると、外のファイルを読ませる穴になる。
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
PY = sys.executable
ENV = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
GOOD_SOURCE = "NDL-1187053-R0000005-L"
TAB = {"push_part": "tab"}


def run(mod, *args):
    return subprocess.run([PY, "-m", mod, *args], cwd=ROOT, env=ENV, capture_output=True, text=True)


def scenario(d, source_id):
    f = pathlib.Path(d) / "sc.json"
    f.write_text(json.dumps({"template": "slider_fan", "source_id": source_id, "params": TAB, "inject": {}}), encoding="utf-8")
    return str(f)


with tempfile.TemporaryDirectory() as d:
    d = pathlib.Path(d)
    # 1. 置き場の外の JSON を、出典として読めない。中身の玩具の名前が紙に出ない事まで見る
    (d / "outside").mkdir()
    real = json.loads((ROOT / f"data/sources/{GOOD_SOURCE}.json").read_text(encoding="utf-8"))
    (d / "outside/evil.json").write_text(json.dumps({**real, "source_id": "evil"}), encoding="utf-8")
    climb = os.path.relpath(d / "outside/evil", ROOT / "data/sources")
    for bad in (climb, "../sources/" + GOOD_SOURCE, "a/b", "a\\b", str(d / "outside/evil"), "a.b", "", "x" * 81, GOOD_SOURCE + "\n", 3, None, ["a"]):
        for mod, more in (("omochae", ["--out", str(d / "o")]), ("omochae.foldsim", ["--out", str(d / "fs")])):
            r = run(mod, "--scenario", scenario(d, bad), *more)
            assert r.returncode == 4 and "Traceback" not in r.stderr, (mod, bad, r.returncode, r.stderr)
    assert not list(d.glob("o.*")) and not (d / "fs").exists(), "断った値で何か書いた"
    # 2. 形は合うが出典が無い時も 4。文に機械の絶対のパスを出さない
    r = run("omochae", "--scenario", scenario(d, "NDL-no-such"), "--out", str(d / "o"))
    assert r.returncode == 4 and "NDL-no-such" in r.stderr and "data/sources" in r.stderr, r.stderr
    assert str(ROOT) not in r.stderr, r.stderr
    # 3. --name で外へ書けない。置き場の外にも中にも何も増えない
    sc = scenario(d, GOOD_SOURCE)
    out = d / "deep/er/fs"
    out.mkdir(parents=True)
    (out / "slider_fan_fan_foldsim.svg").write_text("前の回", encoding="utf-8")
    before = sorted(p for p in d.rglob("*"))
    for bad in ("../../x", "..", "a/b", "a\\b", str(d / "x"), "a.b", "[ab]", "x" * 81):
        r = run("omochae.foldsim", "--scenario", sc, "--out", str(out), "--name", bad)
        assert r.returncode == 4 and "--name" in r.stderr and "Traceback" not in r.stderr, (bad, r.returncode, r.stderr)
        assert sorted(p for p in d.rglob("*")) == before, bad
    assert (out / "slider_fan_fan_foldsim.svg").read_text(encoding="utf-8") == "前の回"
    # 4. 決まった形の名前と、今ある出典は全部通る（形の検査で今の物を断らない）
    r = run("omochae.foldsim", "--scenario", sc, "--out", str(out), "--name", "Tiger_v-2")
    assert r.returncode == 0 and (out / "Tiger_v-2_fan_foldsim.svg").exists(), r.stderr
    sys.path.insert(0, str(ROOT / "src"))
    from omochae.__main__ import load_source
    for f in sorted((ROOT / "data/sources").glob("*.json")):
        assert load_source(f.stem)["source_id"], f.stem
print("ok")
