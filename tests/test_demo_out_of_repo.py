"""デモ動画の作りを utsushi の repo から外した事の見張り（本人の言葉 11-08「この動画の作成はギットハブに入ってる？入れなくていいと思うと前に指摘したけど」）。

見る事:
- 動画を作る物（src/demo/・docs/demo/・動画の場面の試験・docs/process/demo-notes.md）が repo に無い。作りは repo の外（grove の手元）で続ける
- コードと試験に、動画の作りを読む所（from demo / src/demo / docs/demo）が残っていない。過程の記録（docs/process の古い帳面など）の言及は移す前の物として残る
- サイトの北斎漫画が読む絵の出所と権利の記録は、字を替えずに data/hokusai/ へ移り、サイトはそこを読む（前は src/demo/ の物を読んでいた）
- 公開デモのサイトの物（run-demo.sh・web.demo_check・web.demo_samples・サイトの道を回す試験）は残る
"""
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

gone = ["src/demo", "docs/demo", "docs/process/demo-notes.md"] + [
    f"tests/test_demo_{n}.py" for n in ("assemble", "build", "flip", "prepare", "scene2", "scene3", "scene4", "scene5", "scene6", "scene7")]
left = [p for p in gone if (ROOT / p).exists()]
assert not left, ("repo に残っている動画の作り", left)

kept = ["run-demo.sh", "src/web/demo_check.py", "src/web/demo_samples.py", "tests/test_run_demo.py", "tests/test_demo_samples.py",
        "tests/test_demo_walk.py", "tests/test_demo_walk_all.py", "docs/process/decisions/J028-open-demo.md"]
missing = [p for p in kept if not (ROOT / p).exists()]
assert not missing, ("公開デモのサイトの物が消えた", missing)

# コードと試験と README・architecture に、動画の作りを読む所が無い（この試験の字は除く）
out = subprocess.run(["git", "grep", "-n", "-E", r"(from|import) demo\b|python -m demo\.|src/demo|docs/demo", "--", "src", "tests", "run.sh", "run-demo.sh",
                      "README.md", "docs/architecture.md", ":!tests/test_demo_out_of_repo.py"], cwd=ROOT, capture_output=True, text=True).stdout
assert not out.strip(), ("動画の作りを読む所が残っている", out[:600])

# 北斎漫画の絵の出所と権利の記録は data/hokusai/ にあり、サイトはそこを読む
for name in ("figures.json", "scene4_sources.json"):
    assert (ROOT / "data/hokusai" / name).is_file(), name
    json.loads((ROOT / "data/hokusai" / name).read_text(encoding="utf-8"))
assert (ROOT / "data/hokusai/README.md").is_file()
src = (ROOT / "src/omochae/hokusai.py").read_text(encoding="utf-8")
assert "data/hokusai/figures.json" in src and "data/hokusai/scene4_sources.json" in src and "src/demo" not in src
from omochae import hokusai  # noqa: E402

assert re.search(r"def \w+", src) and hokusai is not None
print("ok デモ動画の作りは repo の外・北斎漫画の記録は data/hokusai・公開デモのサイトの物は残る")
