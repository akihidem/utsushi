#!/bin/bash
# init.sh — 環境を作る。足りない物は名指しして exit 4（検査できない）にする。
# なぜ apt を自動で入れないか: 使い手の機械の系を黙って変えないため。無い物を言うだけにする。
set -u
cd "$(dirname "$0")"
# 固定した依存（shapely など）が 3.11 以上を求める。先に見ないと、uv の解決の失敗の長い文でしか分からない。
MIN_PY=3.11
missing=()
for c in uv pdftotext pdftoppm fc-match ffmpeg ffprobe; do command -v "$c" >/dev/null || missing+=("$c"); done
if [ ${#missing[@]} -eq 0 ] && ! fc-list | grep -q "Noto Serif CJK JP"; then missing+=("字 Noto Serif CJK JP"); fi
if [ ${#missing[@]} -gt 0 ]; then echo "init: 足りない物: ${missing[*]}" >&2; exit 4; fi
# --no-python-downloads: 使い手の機械に黙って Python を足さない（apt を入れないのと同じ理由）。
if [ ! -d .venv ]; then
  uv venv -q --python ">=$MIN_PY" --no-python-downloads .venv || { echo "init: 足りない物: Python $MIN_PY 以上" >&2; exit 4; }
fi
have=$(.venv/bin/python -c 'import sys; print("%d.%d" % sys.version_info[:2])') || have="動かない"
if [ "$have" = "動かない" ] || [ "$(printf '%s\n' "$MIN_PY" "$have" | sort -V | head -n 1)" != "$MIN_PY" ]; then
  echo "init: 足りない物: Python $MIN_PY 以上（.venv は $have）。.venv を消して、やり直す" >&2; exit 4
fi
uv pip install -q --python .venv/bin/python -r requirements.txt || exit 4
echo "init: 環境ができた"
