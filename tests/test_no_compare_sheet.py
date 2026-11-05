"""見比べる紙は外した（本人の決定 11-05「見比べる紙は外す」。#332 の点 2、J-032）の試験。

見る事:
1. 見比べる紙を刷る命令と、作り手用の表の命令が無い
2. 紙を組む関数とモジュールが無い
3. 凍結の基準に、外した床が生きた床として残っていない。外した理由は基準と凍結の変更の記録に残る
4. 前に渡した compare-v1・compare-v2 の PDF は履歴として残る
"""
import importlib.util
import pathlib
import subprocess
import sys

from omochae import hypotheses, instructions

ROOT = pathlib.Path(__file__).resolve().parents[1]
G = "NDL-1187053-R0000005-L"


def run(*args):
    return subprocess.run([sys.executable, "-m", "omochae.hypotheses", "--source", G, *args], capture_output=True, text=True)


# 1. 命令が無い。argparse が断るので、ほかの落ち方と分けるために文も見る
for args in (("print-compare", "H-A", "H-E"), ("compare",)):
    r = run(*args)
    assert r.returncode != 0 and "invalid choice" in r.stderr, args
assert run("list").returncode == 0, "負の対照: 残した命令は通る"

# 2. 作りが無い
assert importlib.util.find_spec("omochae.discriminate") is None
assert not hasattr(hypotheses, "print_compare") and not hasattr(instructions, "compose_compare")
assert not (ROOT / "tests/test_discriminate.py").exists()

# 3. 基準の見出しと、外した理由
criteria = (ROOT / "tests/frozen/criteria.md").read_text(encoding="utf-8")
assert "### F11.compare を外した" in criteria
assert not any(line.startswith("| F11") for line in criteria.splitlines()), "基準の表に生きた床として残さない"
usage = (ROOT / "docs/claude-usage.md").read_text(encoding="utf-8")
assert "F11.compare を外した" in usage

# 4. 履歴
for name in ("compare-v1/compare_A_E.pdf", "compare-v2/compare_C_D.pdf"):
    assert (ROOT / "docs/process/trials/sheets" / name).exists(), name
print("ok 見比べる紙を刷る道は無く、外した理由と前の PDF は残る")
