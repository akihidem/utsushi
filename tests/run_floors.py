"""tests/frozen の場面を全部回し、out/RESULT.md に表を出す。

なぜ狙いの検査の名前まで比べるか: exit 3 だけ見ると、別の理由で落ちた負の対照も成功に見えてしまう。

回す前に、凍結した場面と基準を照合の表（tests/frozen/manifest.json）と照らす（#165）。
なぜ照らすか: 場面も試験も、その時にあるファイルを回すだけなので、1 つ消すと合計が黙って減って全部通る。
場面の中身を変えても、変えた事は手の記録にしか残らない。合わない時は rc 4（検査できない）でファイルを名指しする。
凍結を変える時は、理由を commit と docs/claude-usage.md に書き、`python tests/run_floors.py --write-manifest` で
表も同じ commit で直す（表の差分に、何を変えたかが出る）。
"""
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
PY = str(ROOT / ".venv/bin/python")
NOT_YET = []
MANIFEST = "tests/frozen/manifest.json"
# 要る物の一覧。README の「動かし方」と init.sh も同じ物を挙げる（tests/test_required_tools.py が照らす）。
# uv は環境を作る時だけ使うので、ここでは作られた .venv を見る。
TOOLS = ("pdftotext", "pdftoppm", "fc-match", "ffmpeg", "ffprobe")
FONT = "Noto Serif CJK JP"


def _sha(path):
    # 改行の形だけが違う写し（CRLF の checkout）を、変わったと読まない。
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def manifest_now(root):
    """今の tree から照合の表を作る。期待の rc と床も載せるのは、表の差分だけで期待の変更が読めるようにするため。"""
    scenarios = {}
    for sc in sorted((root / "tests/frozen/scenarios").glob("*.json")):
        try:
            expect = json.loads(sc.read_text(encoding="utf-8"))["expect"]
            scenarios[sc.name] = {"sha256": _sha(sc), "rc": expect["rc"], "floors": sorted(expect["floors"])}
        except (ValueError, KeyError, TypeError):
            scenarios[sc.name] = {"sha256": _sha(sc), "rc": None, "floors": []}  # 読めない場面は、表と合わない物として出る
    criteria = root / "tests/frozen/criteria.md"
    return {"criteria.md": _sha(criteria) if criteria.exists() else None, "scenarios": scenarios,
            "tests": sorted(p.stem for p in (root / "tests").glob("test_*.py"))}


def ledger_env(env, folder, name):
    """子に渡す環境。API の消費の台帳は記録の置き場で分かれないので、試験ごとに一時の台帳へ向け、本物に書かせない（#151）。"""
    return {**env, "OMOCHAE_USAGE_LEDGER": str(pathlib.Path(folder) / f"{name}.jsonl")}


def check_manifest(root):
    """凍結の表と今の tree の合わない所を、ファイルを名指しした文で返す。空なら合っている。

    試験は数でなく名前で持ち、在るはずの物が消えた時だけ落とす。数にすると、並んで動く線が試験を足すたびに
    同じ 1 行でぶつかり、表より前に切った枝を取り込んだ直後に main が検査できなくなるため。
    """
    path = root / MANIFEST
    try:
        table = json.loads(path.read_text(encoding="utf-8"))
        want, tests = table["scenarios"], table["tests"]
    except (OSError, ValueError, KeyError, TypeError) as e:
        return [f"{MANIFEST} が読めない（{type(e).__name__}）"]
    now, out = manifest_now(root), []
    if table.get("criteria.md") != now["criteria.md"]:
        out.append("変わった: tests/frozen/criteria.md")
    for name in sorted(set(want) | set(now["scenarios"])):
        where = f"tests/frozen/scenarios/{name}"
        if name not in now["scenarios"]:
            out.append(f"消えた: {where}")
        elif name not in want:
            out.append(f"表に無い: {where}")
        elif want[name] != now["scenarios"][name]:
            out.append(f"変わった: {where}")
    out += [f"消えた: tests/{t}.py" for t in sorted(set(tests) - set(now["tests"]))]
    return out


def write_manifest(root):
    """照合の表を今の tree から書く。在るはずの試験の一覧には、今ある試験を全部載せる。"""
    path = root / MANIFEST
    before = check_manifest(root) if path.exists() else ["表が無かった"]
    path.write_text(json.dumps(manifest_now(root), ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    for line in before:
        print(f"表を直した所 … {line}")
    print(f"{MANIFEST} を書いた（凍結を変えたなら、理由を commit と docs/claude-usage.md に）")
    return 0


def missing_needs():
    """足りない物を全部、名前で返す（#160）。回してから試験が落ちると、道具の不足が「落ちた（3）」に見えるため。"""
    out = [] if os.path.exists(PY) else [".venv が無い（./init.sh を先に）"]
    out += [f"{tool} が無い" for tool in TOOLS if not shutil.which(tool)]
    if shutil.which("fc-match"):
        # 見分け方は src/omochae/textfit.py と同じ。ここは .venv の外でも動くので、あちらを読み込まない。
        found = subprocess.run(["fc-match", FONT, "file"], capture_output=True, text=True).stdout
        if "NotoSerifCJK" not in found:
            out.append(f"字 {FONT} が無い")
    return out


def main():
    wrong = check_manifest(ROOT)
    if wrong:
        for line in wrong:
            print(f"検査できない: 凍結の表と合わない … {line}", file=sys.stderr)
        print("凍結を変えたなら、理由を commit と docs/claude-usage.md に書き、python tests/run_floors.py --write-manifest で表も同じ commit で直す", file=sys.stderr)
        return 4
    needs = missing_needs()
    if needs:
        for line in needs:
            print(f"検査できない: {line}", file=sys.stderr)
        return 4
    # 試験は素の assert で検査するので、assert を消す設定（PYTHONOPTIMIZE）を子に渡さない。
    # 呼ぶ側の環境に残っていると、落ちるはずの試験が黙って通る（外の検品の指摘、11-04）。子は -O も付けずに起こす。
    env = {**{k: v for k, v in os.environ.items() if k != "PYTHONOPTIMIZE"}, "PYTHONPATH": str(ROOT / "src")}
    rows, bad, broken = [], 0, 0
    ledgers = tempfile.TemporaryDirectory()
    for sc in sorted((ROOT / "tests/frozen/scenarios").glob("*.json")):
        expect = json.loads(sc.read_text(encoding="utf-8"))["expect"]
        out = ROOT / "out/scenarios" / sc.stem
        cmd = [PY, "-m", "omochae", "--scenario", str(sc), "--out", str(out)]
        r = subprocess.run(cmd, cwd=ROOT, env=ledger_env(env, ledgers.name, sc.stem), capture_output=True, text=True)
        got = sorted(set(re.findall(r"^FAIL (\S+)", r.stderr, re.M)))
        ok = r.returncode == expect["rc"] and got == sorted(expect["floors"])
        broken += r.returncode == 4
        bad += not ok
        rows.append((sc.stem, r.returncode, expect["rc"], ",".join(got) or "—", ",".join(expect["floors"]) or "—", "OK" if ok else "NG"))
        if not ok:
            print(f"NG {sc.stem}: rc={r.returncode} {r.stderr.strip()[:500]}", file=sys.stderr)
    for test in sorted((ROOT / "tests").glob("test_*.py")):
        unit = subprocess.run([PY, str(test)], cwd=ROOT, env=ledger_env(env, ledgers.name, test.stem), capture_output=True, text=True)
        bad += unit.returncode != 0
        rows.append((test.stem, unit.returncode, 0, "—", "—", "OK" if unit.returncode == 0 else "NG"))
        if unit.returncode:
            print(f"NG {test.stem}: {unit.stderr.strip()[:500]}", file=sys.stderr)
    ledgers.cleanup()
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
    sys.exit(write_manifest(ROOT) if sys.argv[1:] == ["--write-manifest"] else main())
