"""負の場面が、狙った検査で落ちている事を見る（#27）。

なぜ: 床の入口は落ちた床の ID の組だけを比べていた。1 つの ID に多くの検査が入っているので、狙った検査を消しても、
同じ ID の別の検査で落ちて場面は通った。落ちる場面は FAIL の行が 1 つか、期待の lines に全部の行の形を書く。
"""
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import run_floors  # noqa: E402

ROOT = run_floors.ROOT
SCENARIOS = ROOT / "tests/frozen/scenarios"

# 形: 数だけを除く。数が動いても同じ形で、検査の文が違えば別の形
one = "FAIL F5.float [重心] GM が 1.7mm で、傾いて戻らない（3mm 以上）\nFAIL F5.float [人形] 半幅 14.1mm が -2mm\nほかの行\n"
assert run_floors.fail_shapes(one) == ["F5.float [人形] 半幅 #mm が #mm", "F5.float [重心] GM が #mm で、傾いて戻らない（#mm 以上）"]
assert run_floors.fail_shapes(one.replace("1.7", "2.9")) == run_floors.fail_shapes(one)

# 比べ方
single = {"rc": 3, "floors": ["F5.float"]}
assert run_floors.scenario_ok(single, 3, "FAIL F5.float [重心] 落ちた 1\n") == (True, ["F5.float"])
assert run_floors.scenario_ok({"rc": 0, "floors": []}, 0, "")[0], "正の場面は FAIL の行が無い"
assert not run_floors.scenario_ok(single, 3, one)[0], "lines が無いのに 2 行で落ちる場面は通さない"
assert not run_floors.scenario_ok(single, 0, "")[0]
assert not run_floors.scenario_ok({"rc": 3, "floors": ["F5.other"]}, 3, "FAIL F5.float [重心] 落ちた\n")[0]
both = {**single, "lines": run_floors.fail_shapes(one)}
assert run_floors.scenario_ok(both, 3, one)[0]
assert not run_floors.scenario_ok(both, 3, one.split("\n")[0] + "\n")[0], "1 行消えたら通さない"
assert not run_floors.scenario_ok(both, 3, one + "FAIL F5.float [足した] 増えた\n")[0], "1 行増えても通さない"

# 凍結の場面の決まり: 期待の lines は、複数の FAIL で落ちる場面にだけ書く（1 行の場面は書かなくても守れる）
withlines = [p for p in SCENARIOS.glob("*.json") if "lines" in json.loads(p.read_text(encoding="utf-8"))["expect"]]
assert len(withlines) >= 16
for p in withlines:
    assert len(json.loads(p.read_text(encoding="utf-8"))["expect"]["lines"]) >= 2, p.name

# 本物の検査を 1 つ消すと、場面が落ちる。rc も床の ID も同じなので、前の比べ方では気づけなかった所
MUTANTS = [("float.py", 'out.append(Failure("F5.float", "人形", f"壁の上端', "float_neg2"),
           ("lever_link.py", 'out.append(Failure("F5.link", "水車と手", f"水車と机', "lever_link_neg4"),
           ("pivot_counterweight.py", 'out.append(Failure("F5.pivot", "頭", f"頭が胴', "neg_pivot_ear"),
           ("launcher.py", 'out.append(Failure("F5.launch", "玉", f"玉 {d:g}mm が物差しの穴', "launcher_neg2"),
           ("popup_jar.py", 'out.append(Failure("F5.popup", "人形の足", f"押し上げる', "popup_jar_neg4"),
           ("pull_nod.py", 'out.append(Failure("F5.pull_nod", "こぶ", "こぶを貼る所', "pull_nod_neg2")]


def run_in(root, name):
    sc = SCENARIOS / f"{name}.json"
    expect = json.loads(sc.read_text(encoding="utf-8"))["expect"]
    r = subprocess.run([sys.executable, "-m", "omochae", "--scenario", str(sc), "--out", str(root / "out" / name)], cwd=root,
                       env={**os.environ, "PYTHONPATH": str(root / "src")}, capture_output=True, text=True)
    return expect, r


with tempfile.TemporaryDirectory() as base:
    root = pathlib.Path(base)
    shutil.copytree(ROOT / "src", root / "src", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(ROOT / "data", root / "data")
    for file, needle, name in MUTANTS:
        expect, r = run_in(root, name)
        assert run_floors.scenario_ok(expect, r.returncode, r.stderr)[0], ("消す前は通る", name, r.stderr[-300:])
        path = root / "src/omochae/templates" / file
        keep = path.read_text(encoding="utf-8")
        assert keep.count(needle) == 1, needle
        path.write_text(keep.replace(needle, needle.replace("out.append(", "(lambda *_: None)(")), encoding="utf-8")
        expect, r = run_in(root, name)
        path.write_text(keep, encoding="utf-8")
        got = sorted(set(re.findall(r"^FAIL (\S+)", r.stderr, re.M)))
        assert r.returncode == expect["rc"] and got == expect["floors"], ("前の比べ方なら通る形", name, r.returncode, got)
        assert not run_floors.scenario_ok(expect, r.returncode, r.stderr)[0], ("検査を消したのに通った", name)
print(f"ok 期待に行を書いた場面 {len(withlines)} 本。検査を消す試し {len(MUTANTS)} か所")
