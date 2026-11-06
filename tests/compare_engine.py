"""エンジンの共通の場面を、この repo と paper-to-toy の両方で回して結果を比べる（#164）。

なぜ要るか: `src/omochae/` は両方の repo にあり、正は paper-to-toy（#164）。片側だけに直しが入ると、
同じ名前の検査が別の意味になる。相手の repo が無い所でも ./run.sh を回せるように、./run.sh には入れず、取り込む時に手で回す。

比べる物: 場面の入力（雛形・出典・寸法・差し込み）、終わりの値、FAIL の行。行の数は寸法で動くので除いて比べる。
使い方: `PYTHONPATH=src .venv/bin/python tests/compare_engine.py <paper-to-toy の置き場>`。
exit code: 0 = 同じ / 3 = 違う所がある（場面を名指しする）/ 4 = 比べられない。
"""
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCENARIOS = "tests/frozen/scenarios"
# 入力を比べる欄。期待の欄（expect）は持ち方が repo で違ってよい。比べるのは実際に回した結果なので
INPUT = ("template", "source_id", "params", "inject", "title")
# FAIL の行までは比べない場面と理由。終わりの値と床の名前は比べる。
# neg_text_overlap: こちらは題の次に「刷った組」の字を置く（U-31）ので文字の位置がずれ、重なる組み合わせが変わる。字を外すと行まで同じになる事を確かめた。
FLOORS_ONLY = {"neg_text_overlap.json"}


def shapes(stderr):
    """FAIL の行から数を除いて並べる。寸法を調整すると動く数でなく、どの検査がどこで落ちたかを比べる。"""
    return sorted(re.sub(r"-?\d+(?:\.\d+)?", "#", line) for line in stderr.splitlines() if line.startswith("FAIL "))


def run(repo, scenario, out):
    env = {**os.environ, "PYTHONPATH": "src"}
    env.pop("PYTHONOPTIMIZE", None)
    r = subprocess.run([sys.executable, "-m", "omochae", "--scenario", f"{SCENARIOS}/{scenario}", "--out", str(out)],
                       cwd=repo, env=env, capture_output=True, text=True, timeout=300)
    return r.returncode, shapes(r.stderr)


def _floors_only(result):
    rc, lines = result
    return rc, sorted({line.split()[1] for line in lines})


def compare(here, there):
    """違う所の文の一覧と、比べた場面の数を返す。"""
    ours = {p.name for p in (here / SCENARIOS).glob("*.json")}
    theirs = {p.name for p in (there / SCENARIOS).glob("*.json")}
    diffs = []
    with tempfile.TemporaryDirectory() as tmp:
        for name in sorted(ours & theirs):
            a = json.loads((here / SCENARIOS / name).read_text(encoding="utf-8"))
            b = json.loads((there / SCENARIOS / name).read_text(encoding="utf-8"))
            changed = [k for k in INPUT if a.get(k) != b.get(k)]
            if changed:
                diffs.append(f"{name}: 場面の入力が違う（{'・'.join(changed)}）")
            ra = run(here, name, pathlib.Path(tmp) / "a" / name)
            rb = run(there, name, pathlib.Path(tmp) / "b" / name)
            if name in FLOORS_ONLY:
                ra, rb = _floors_only(ra), _floors_only(rb)
            if ra != rb:
                diffs.append(f"{name}: 結果が違う\n  こちら rc={ra[0]} {ra[1]}\n  あちら rc={rb[0]} {rb[1]}")
    return diffs, len(ours & theirs)


def main(argv):
    if len(argv) != 2:
        print("使い方: compare_engine.py <paper-to-toy の置き場>", file=sys.stderr)
        return 4
    there = pathlib.Path(argv[1]).resolve()
    if not (there / "src/omochae/floors.py").exists() or not (there / SCENARIOS).is_dir():
        print(f"検査できない: エンジンの repo でない: {there.name}", file=sys.stderr)
        return 4
    diffs, count = compare(ROOT, there)
    for line in diffs:
        print(line)
    print(f"共通の場面 {count} 本、違う所 {len(diffs)} 件。")
    return 3 if diffs else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
