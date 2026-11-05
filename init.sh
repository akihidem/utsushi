#!/bin/bash
# init.sh — 環境を作る。足りない物は名指しして exit 4（検査できない）にする。
# なぜ apt を自動で入れないか: 使い手の機械の系を黙って変えないため。無い物を言うだけにする。
set -u
cd "$(dirname "$0")"
missing=()
for c in uv pdftotext pdftoppm fc-match ffmpeg ffprobe; do command -v "$c" >/dev/null || missing+=("$c"); done
if [ ${#missing[@]} -eq 0 ] && ! fc-list | grep -q "Noto Serif CJK JP"; then missing+=("字 Noto Serif CJK JP"); fi
if [ ${#missing[@]} -gt 0 ]; then echo "init: 足りない物: ${missing[*]}" >&2; exit 4; fi
[ -d .venv ] || uv venv -q .venv || exit 4
uv pip install -q --python .venv/bin/python -r requirements.txt || exit 4
echo "init: 環境ができた"
