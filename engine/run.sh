#!/bin/bash
# run.sh — 凍結した場面を全部回す入口。結果は out/RESULT.md。0 = 期待どおり / 3 = 外れがある / 4 = 検査できない。
cd "$(dirname "$0")" || exit 4
[ -x .venv/bin/python ] || { echo "検査できない: .venv が無い（./init.sh を先に）" >&2; exit 4; }
exec .venv/bin/python tests/run_floors.py
