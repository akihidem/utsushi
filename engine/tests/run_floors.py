"""tests/frozen の場面を全部回し、out/RESULT.md に表を出す。

なぜ狙いの検査の名前まで比べるか: exit 3 だけ見ると、別の理由で落ちた負の対照も成功に見えてしまう。

回す前に、凍結した場面と基準を照合の表（tests/frozen/manifest.json）と照らす（#26）。
なぜ照らすか: 場面も試験も、その時にあるファイルを回すだけなので、1 つ消すと合計が黙って減って全部通る。
期待の値は場面の中にあるので、場面を書き換えると期待も一緒に変わる。合わない時は rc 4（検査できない）でファイルを名指しする。
凍結を変える時は、理由を commit に書き、`.venv/bin/python tests/run_floors.py --write-manifest` で表も同じ commit で直す
（表の差分に、何を変えたかが出る）。
"""
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
PY = str(ROOT / ".venv/bin/python")
NOT_YET = []
MANIFEST = "tests/frozen/manifest.json"


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
    print(f"{MANIFEST} を書いた（凍結を変えたなら、理由を commit に）")
    return 0


def fail_shapes(stderr):
    """FAIL の行から数を除いた形を、並べて返す。数は寸法を調整すると動くので、比べるのは「どの検査が落ちたか」だけにする。"""
    return sorted(floor + " " + re.sub(r"-?\d+(?:\.\d+)?", "#", rest) for floor, rest in re.findall(r"^FAIL (\S+) (.+)$", stderr, re.M))


def scenario_ok(expect, rc, stderr):
    """(通ったか, 落ちた床) を返す。床の ID だけを見ると、1 つの ID に多くの検査が入っているので、狙った検査を消しても通る（#27）。
    落ちる場面は FAIL の行が 1 つか、期待の lines に全部の行の形が書いてある事を求める。"""
    got = sorted(set(re.findall(r"^FAIL (\S+)", stderr, re.M)))
    shapes = fail_shapes(stderr)
    want = expect.get("lines")
    same = len(shapes) <= 1 if want is None else shapes == sorted(want)
    return rc == expect["rc"] and got == expect["floors"] and same, got


def load_scenarios():
    """場面を全部読み、(場面と期待の組, 読めない物の文) を返す。壊れた物があれば 1 つも回さない（結果の表を半端に残さない）。"""
    found, wrong = [], []
    for sc in sorted((ROOT / "tests/frozen/scenarios").glob("*.json")):
        try:
            expect = json.loads(sc.read_text(encoding="utf-8"))["expect"]
            lines = expect.get("lines")
            if not (lines is None or isinstance(lines, list) and all(isinstance(x, str) for x in lines)):
                raise TypeError("lines は文の並び")
            found.append((sc, {"rc": expect["rc"], "floors": sorted(expect["floors"]), **({} if lines is None else {"lines": lines})}))
        except (OSError, ValueError, KeyError, TypeError) as e:
            wrong.append(f"{sc.relative_to(ROOT)}（{type(e).__name__}: {e}）")
    return found, wrong


def child_env(environ):
    """子へ渡す環境。試験は素の assert で検査するので、assert を消す設定（PYTHONOPTIMIZE）を渡さない。
    呼ぶ側の環境に残っていると、落ちるはずの試験が黙って通る（#36）。子は -O も付けずに起こす。"""
    return {**{k: v for k, v in environ.items() if k != "PYTHONOPTIMIZE"}, "PYTHONPATH": str(ROOT / "src")}


def child_timeout(environ):
    """子 1 本の時間切れ（秒）。雛形の試験は 1 本で数十秒かかり、ほかの作業で混むと延びるので、広めに取る（#29）。"""
    raw = environ.get("OMOCHAE_CHILD_TIMEOUT", "900")
    try:
        value = float(raw)
    except ValueError:
        value = 0.0
    if not 0 < value < float("inf"):  # 読めない値を、黙って時間切れ無しにしない
        raise ValueError(f"OMOCHAE_CHILD_TIMEOUT の値が読めない: {raw[:40]!r}")
    return value


def run_child(cmd, env, limit):
    """子を回す。返らない子は打ち切り、検査できない（4）の結果にして、残りの子へ進む。Returns (結果, 打ち切ったか)。"""
    try:
        return subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True, timeout=limit), False
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(cmd, 4, "", f"検査できない: {limit:g} 秒で返らない"), True


def _rel(path):
    return pathlib.Path(path).relative_to(ROOT).as_posix()


def scenario_command(sc):
    """結果の表に書く命令。repo の頭でそのまま打てる形にする（落ちた行を手で回し直すため）。"""
    return f"PYTHONPATH=src .venv/bin/python -m omochae --scenario {_rel(sc)} --out out/scenarios/{sc.stem}"


def test_command(test):
    return f"PYTHONPATH=src .venv/bin/python {_rel(test)}"


def result_lines(rows, scenario_count):
    """結果の表の行。合計の行は今までの形のまま残し、場面と試験の内訳を別の行に足す。"""
    lines = ["# 床の実行結果", "", "| 段 | 命令 | rc | 期待 | 落ちた検査 | 期待の検査 | 判定 |", "|---|---|---|---|---|---|---|"]
    lines += [f"| {n} | `{cmd}` | {rc} | {erc} | {g} | {e} | {v} |" for n, cmd, rc, erc, g, e, v in rows]
    lines += [f"| {f} | — | — | — | — | — | 未実装 |" for f in NOT_YET]
    good = [r[-1] == "OK" for r in rows]
    lines += ["", f"実行した場面 {len(rows)} 本、期待どおり {sum(good)} 本、未実装の床 {len(NOT_YET)} 本。",
              f"内訳: 凍結の場面 {scenario_count} 本（期待どおり {sum(good[:scenario_count])} 本）、"
              f"試験 {len(rows) - scenario_count} 本（期待どおり {sum(good[scenario_count:])} 本）。"]
    return lines


def main():
    wrong = check_manifest(ROOT)
    if wrong:
        for line in wrong:
            print(f"検査できない: 凍結の表と合わない … {line}", file=sys.stderr)
        print("凍結を変えたなら、理由を commit に書き、.venv/bin/python tests/run_floors.py --write-manifest で表も同じ commit で直す", file=sys.stderr)
        return 4
    for tool in ("pdftotext", "pdftoppm", "pdfimages", "fc-match"):
        if not shutil.which(tool):
            print(f"検査できない: {tool} が無い", file=sys.stderr)
            return 4
    scenarios, wrong = load_scenarios()
    if wrong:
        for line in wrong:
            print(f"検査できない: 場面が読めない … {line}", file=sys.stderr)
        return 4
    env = child_env(os.environ)
    limit = child_timeout(os.environ)
    rows, bad, broken = [], 0, 0
    for sc, expect in scenarios:
        out = ROOT / "out/scenarios" / sc.stem
        cmd = [PY, "-m", "omochae", "--scenario", str(sc), "--out", str(out)]
        r, _ = run_child(cmd, env, limit)
        ok, got = scenario_ok(expect, r.returncode, r.stderr)
        broken += r.returncode == 4
        bad += not ok
        rows.append((sc.stem, scenario_command(sc), r.returncode, expect["rc"], ",".join(got) or "—", ",".join(expect["floors"]) or "—", "OK" if ok else "NG"))
        if not ok:
            print(f"NG {sc.stem}: rc={r.returncode} {r.stderr.strip()[:500]}", file=sys.stderr)
            print(f"   今の FAIL の行の形（期待の lines に書く形）: {json.dumps(fail_shapes(r.stderr), ensure_ascii=False)}", file=sys.stderr)
    for test in sorted((ROOT / "tests").glob("test_*.py")):
        unit, hung = run_child([PY, str(test)], env, limit)
        bad += unit.returncode != 0
        broken += hung
        rows.append((test.stem, test_command(test), unit.returncode, 0, "—", "—", "OK" if unit.returncode == 0 else "NG"))
        if unit.returncode:
            print(f"NG {test.stem}: {unit.stderr.strip()[:500]}", file=sys.stderr)
    lines = result_lines(rows, len(scenarios))
    (ROOT / "out").mkdir(exist_ok=True)
    (ROOT / "out/RESULT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[-2:]))
    return 4 if broken and bad == broken else (3 if bad else 0)


if __name__ == "__main__":
    try:
        sys.exit(write_manifest(ROOT) if sys.argv[1:] == ["--write-manifest"] else main())
    except Exception as e:  # 思わぬ失敗は「通った」にも「落ちた」にも数えない（.venv が無い・結果の表が書けない など）。
        print(f"検査できない: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(4)
