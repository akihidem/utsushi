"""tests/frozen の場面を全部回し、out/RESULT.md に表を出す。

なぜ狙いの検査の名前まで比べるか: exit 3 だけ見ると、別の理由で落ちた負の対照も成功に見えてしまう。
"""
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
PY = str(ROOT / ".venv/bin/python")
NOT_YET = ["F2.bom", "F3.result", "F4.evidence", "F5.pivot", "F6.label", "F7.revision", "F8.references", "F9.human"]


def main():
    for tool in ("pdftotext", "pdftoppm", "fc-match"):
        if not shutil.which(tool):
            print(f"検査できない: {tool} が無い", file=sys.stderr)
            return 4
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    rows, bad, broken = [], 0, 0
    for sc in sorted((ROOT / "tests/frozen/scenarios").glob("*.json")):
        expect = json.loads(sc.read_text(encoding="utf-8"))["expect"]
        out = ROOT / "out/scenarios" / sc.stem
        cmd = [PY, "-m", "omochae", "--scenario", str(sc), "--out", str(out)]
        r = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True)
        got = sorted(set(re.findall(r"^FAIL (\S+)", r.stderr, re.M)))
        ok = r.returncode == expect["rc"] and got == sorted(expect["floors"])
        broken += r.returncode == 4
        bad += not ok
        rows.append((sc.stem, r.returncode, expect["rc"], ",".join(got) or "—", ",".join(expect["floors"]) or "—", "OK" if ok else "NG"))
        if not ok:
            print(f"NG {sc.stem}: rc={r.returncode} {r.stderr.strip()[:500]}", file=sys.stderr)
    lines = ["# 床の実行結果", "", "| 段 | 命令 | rc | 期待 | 落ちた検査 | 期待の検査 | 判定 |", "|---|---|---|---|---|---|---|"]
    for n, rc, erc, g, e, v in rows:
        lines.append(f"| {n} | `python -m omochae --scenario {n}` | {rc} | {erc} | {g} | {e} | {v} |")
    lines += [f"| {f} | — | — | — | — | — | 未実装 |" for f in NOT_YET]
    lines += ["", f"実行した場面 {len(rows)} 本、期待どおり {len(rows) - bad} 本、未実装の床 {len(NOT_YET)} 本。"]
    (ROOT / "out").mkdir(exist_ok=True)
    (ROOT / "out/RESULT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(lines[-1])
    return 4 if broken and bad == broken else (3 if bad else 0)


if __name__ == "__main__":
    sys.exit(main())
