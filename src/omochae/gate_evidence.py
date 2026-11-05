"""関門の証拠のファイルを書き出す命令と、頭の検査（#171）。

なぜ要るか: 証拠のファイルの多くは出力だけで、どの命令をどの commit で回したかが後から引けなかった。手で書くと、抜けるか、
個人のパスが混じって push の門で止まる。頭に命令と commit を書き、手元のパスを除いて残す。

    python -m omochae.gate_evidence write red-xxx -- .venv/bin/python tests/test_xxx.py
    python -m omochae.gate_evidence check

なぜ ./run.sh に入れないか: 並行の枝が頭の無い証拠を足したまま main に入ると、main の試験が落ちて全部の枝が止まる。
並行が落ち着いたら入れる。古い証拠で命令が残っていない物は「残っていない」と書く（推測で埋めない）。
exit code: 0 = 書けた・頭がそろっている / 3 = 書かない（名前・上書き・呼び方）・頭の無い物がある / 4 = 命令を回せない。
"""
import pathlib
import re
import shlex
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "docs/process/gate-evidence"
NAME = re.compile(r"[a-z0-9][a-z0-9-]*")
HEAD_COMMAND = re.compile(r"# 命令: .+")
# 不明は git の外の写し（zip で配った物など）で回した時。番号が無い事を、無いと書いてあればよい
HEAD_COMMIT = re.compile(r"# commit: ([0-9a-f]{7,40}\b|不明)")
TIMEOUT = 900  # 秒。./run.sh が混んだ機械で 13 分ほどかかるので、それより長く取る


def _commit():
    r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else "不明（git の外）"


def _scrub(text):
    """手元のパスを除く。push の門が個人のパスとして止めるのと、証拠の読み手に要らないため。"""
    return text.replace(str(ROOT) + "/", "").replace(str(ROOT), ".").replace(str(pathlib.Path.home()), "~")


def write(name, command, timeout=TIMEOUT):
    """命令を回し、頭をつけて残す。命令が落ちても 0 を返す（Red は落ちるのが正しい）。"""
    if not NAME.fullmatch(name):
        print(f"書かない: 名前は小文字・数字・ハイフンだけ: {name!r}", file=sys.stderr)
        return 3
    path = EVIDENCE / f"{name}.txt"
    if path.exists():
        print(f"書かない: もうある（失敗した版も残す決まりなので上書きしない）: {path.name}", file=sys.stderr)
        return 3
    try:
        r = subprocess.run(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        print(f"検査できない: 命令を回せない: {type(e).__name__}", file=sys.stderr)
        return 4
    body = f"# 命令: {shlex.join(command)}\n# commit: {_commit()}（回した時の HEAD）\n{r.stdout.rstrip()}\nrc={r.returncode}\n"
    path.write_text(_scrub(body), encoding="utf-8")
    print(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path)
    return 0


def missing():
    """頭に命令と commit の番号が無い証拠のファイルの名前。"""
    out = []
    for path in sorted(EVIDENCE.iterdir()):
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[:2]
        if not (len(lines) == 2 and HEAD_COMMAND.fullmatch(lines[0]) and HEAD_COMMIT.match(lines[1])):
            out.append(path.name)
    return out


def main(argv):
    if argv[:1] == ["check"] and len(argv) == 1:
        lack = missing()
        for name in lack:
            print(f"FAIL 頭が無い: {name}")
        return 3 if lack else 0
    if argv[:1] == ["write"] and len(argv) >= 4 and argv[2] == "--":
        return write(argv[1], argv[3:])
    print("使い方: python -m omochae.gate_evidence write <名前> -- <命令...> / check", file=sys.stderr)
    return 3


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
