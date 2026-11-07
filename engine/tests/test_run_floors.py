"""run_floors の床: 呼ぶ側の環境に関わらず試験が落ちるべき時に落ち、結果の表の命令がそのまま回せる（#36）。

なぜ要るか: 試験は素の assert を並べているので、PYTHONOPTIMIZE があると assert が消えて黙って通る。
結果の表の「命令」も、試験の行は実在しない命令になっていて、落ちた行を手で回し直せなかった。
"""
import os
import pathlib
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import run_floors  # noqa: E402

ROOT = run_floors.ROOT
PY = sys.executable

# 子へ渡す環境から PYTHONOPTIMIZE を外し、ほかはそのまま渡す。場所は src に向ける
env = run_floors.child_env({"PYTHONOPTIMIZE": "1", "KEEP": "x", "PYTHONPATH": "ほかの場所"})
assert "PYTHONOPTIMIZE" not in env and env["KEEP"] == "x" and env["PYTHONPATH"] == str(ROOT / "src"), env

# 実際に assert が効く事を見る。負の対照: 外さないと同じ物が黙って通る（これを防ぐ試験だと確かめる）
with tempfile.TemporaryDirectory() as tmp:
    broken = pathlib.Path(tmp) / "broken.py"
    broken.write_text("assert False, '落ちるべき'\n", encoding="utf-8")
    base = {**os.environ, "PYTHONOPTIMIZE": "1"}
    assert subprocess.run([PY, str(broken)], env=base, capture_output=True).returncode == 0, "負の対照"
    assert subprocess.run([PY, str(broken)], env=run_floors.child_env(base), capture_output=True).returncode == 1

# 結果の表: どの行の命令も、そのまま回せる。場面の命令は --out まで含み、試験の命令はそのファイルを指す
scenarios = sorted((ROOT / "tests/frozen/scenarios").glob("*.json"))
tests = sorted((ROOT / "tests").glob("test_*.py"))
assert scenarios and tests
neg = next(s for s in scenarios if s.stem == "neg_base_size")
small = next(t for t in tests if t.stem == "test_fan_model")
for path, command, want in ((neg, run_floors.scenario_command(neg), 3), (small, run_floors.test_command(small), 0)):
    assert path.relative_to(ROOT).as_posix() in command, command
    r = subprocess.run(command, shell=True, cwd=ROOT, capture_output=True, text=True,
                       env={k: v for k, v in os.environ.items() if k != "PYTHONPATH"})
    assert r.returncode == want, (command, r.returncode, r.stderr[-300:])
assert "--scenario test_" not in run_floors.test_command(small)

# 表の行と数: 場面と試験を別に数える。今までの行（合計）は残す（読む物があるので形を変えない）
rows = [("pos_a", "cmd-a", 0, 0, "—", "—", "OK"), ("neg_b", "cmd-b", 3, 3, "F1", "F1", "OK"),
        ("test_c", "cmd-c", 0, 0, "—", "—", "OK"), ("test_d", "cmd-d", 1, 0, "—", "—", "NG")]
text = "\n".join(run_floors.result_lines(rows, scenario_count=2))
assert "| pos_a | `cmd-a` | 0 | 0 |" in text and "| test_d | `cmd-d` | 1 | 0 |" in text, text
assert "実行した場面 4 本、期待どおり 3 本、未実装の床 0 本。" in text, text
assert "内訳: 凍結の場面 2 本（期待どおり 2 本）、試験 2 本（期待どおり 1 本）。" in text, text
print("ok run_floors")
