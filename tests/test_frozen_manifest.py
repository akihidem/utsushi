"""凍結した場面と基準を、照合の表（tests/frozen/manifest.json）で機械が守る（#165）。

なぜ: 床の入口は、その時にあるファイルを回すだけだった。場面や試験を 1 つ消すと合計が黙って減り、全部通った。
場面を 1 字変えても、変えた事は手の記録にしか残らなかった。
"""
import contextlib
import io
import json
import pathlib
import shutil
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
import run_floors  # noqa: E402

assert run_floors.check_manifest(ROOT) == [], "今の tree は表と合っている"
table = json.loads((ROOT / run_floors.MANIFEST).read_text(encoding="utf-8"))
assert len(table["scenarios"]) >= 30 and "test_floor_pin" in table["tests"] and "test_frozen_manifest" in table["tests"]


def copy():
    """凍結の置き場と、在るはずの試験の名前だけを写した小さな tree。本物の tree は触らない。"""
    root = pathlib.Path(tempfile.mkdtemp())
    shutil.copytree(ROOT / "tests/frozen", root / "tests/frozen")
    for t in table["tests"]:
        (root / "tests" / f"{t}.py").write_text("", encoding="utf-8")
    assert run_floors.check_manifest(root) == [], "写した直後は合っている"
    return root


def runs(root):
    """床の入口をその tree で回し、(rc, stderr) を返す。表と合わない時は、場面を 1 つも回さずに止まる。"""
    keep, err = run_floors.ROOT, io.StringIO()
    run_floors.ROOT = root
    try:
        with contextlib.redirect_stderr(err):
            return run_floors.main(), err.getvalue()
    finally:
        run_floors.ROOT = keep


SC = "tests/frozen/scenarios/neg_overlap.json"
cases = []
# 1. 場面を 1 つ消す
root = copy()
(root / SC).unlink()
cases.append((root, f"消えた: {SC}"))
# 2. 場面を 1 字変える（期待の rc を 3 から 0 に。落ちるべき紙を通る事にする変更）
root = copy()
text = (root / SC).read_text(encoding="utf-8")
assert '"rc": 3' in text
(root / SC).write_text(text.replace('"rc": 3', '"rc": 0'), encoding="utf-8")
cases.append((root, f"変わった: {SC}"))
# 3. 表に無い場面を足す
root = copy()
shutil.copy(root / SC, root / "tests/frozen/scenarios/neg_added.json")
cases.append((root, "表に無い: tests/frozen/scenarios/neg_added.json"))
# 4. 基準の文を変える
root = copy()
with (root / "tests/frozen/criteria.md").open("a", encoding="utf-8") as f:
    f.write("足した 1 行\n")
cases.append((root, "変わった: tests/frozen/criteria.md"))
# 5. 在るはずの試験を消す
root = copy()
(root / "tests/test_floor_pin.py").unlink()
cases.append((root, "消えた: tests/test_floor_pin.py"))
# 6. 表そのものを消す（表を消して見張りを外せない）
root = copy()
(root / run_floors.MANIFEST).unlink()
cases.append((root, f"{run_floors.MANIFEST} が読めない"))
for root, want in cases:
    wrong = run_floors.check_manifest(root)
    assert len(wrong) == 1 and wrong[0].startswith(want), (want, wrong)
    rc, err = runs(root)
    assert rc == 4 and want in err and not (root / "out/RESULT.md").exists(), (want, rc, err)

# 試験を足すだけなら落ちない（並んで動く線が、表でぶつからないため）。表を書き直すと、足した試験も在るはずの物になる。
root = copy()
(root / "tests/test_new_lane.py").write_text("", encoding="utf-8")
assert run_floors.check_manifest(root) == []
with contextlib.redirect_stdout(io.StringIO()):
    run_floors.write_manifest(root)
assert "test_new_lane" in json.loads((root / run_floors.MANIFEST).read_text(encoding="utf-8"))["tests"]
# 改行の形だけが違う写しは、変わったと読まない。
root = copy()
(root / SC).write_bytes((root / SC).read_bytes().replace(b"\n", b"\r\n"))
assert run_floors.check_manifest(root) == []
print(f"ok 場面 {len(table['scenarios'])} 本と基準の文、在るはずの試験 {len(table['tests'])} 本。崩し方 {len(cases)} 通りを名指しで止めた")
