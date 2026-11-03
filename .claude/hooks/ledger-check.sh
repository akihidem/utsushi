#!/bin/bash
# 台帳や記録を手で直した直後に、台帳の検査（根拠の文の照合、索引、要約の一致）を回す。
# なぜフックか: 直した後に検査を回し忘れると、push の前の ./run.sh まで食い違いが見つからない。毎回走らせ、落ちたら Claude に返して直させる。
# 落ちた時は exit 2（Claude Code が stderr を Claude に返す）。対象の外の編集と、検査できない時は止めない。
root="$(cd "$(dirname "$0")/../.." && pwd)"
path="$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_input", {}).get("file_path", ""))' 2>/dev/null)"
case "$path" in
  "$root"/docs/*|"$root"/data/*|"$root"/README.md|"$root"/CLAUDE.md) ;;
  *) exit 0 ;;
esac
[ -x "$root/.venv/bin/python" ] || exit 0
out="$(cd "$root" && PYTHONPATH=src .venv/bin/python -m omochae.ledger check 2>&1)"
rc=$?
if [ "$rc" -eq 3 ]; then
  echo "台帳の検査が落ちた。直すか、記録から描く物なら python -m omochae.ledger render を回す:" >&2
  echo "$out" >&2
  exit 2
fi
exit 0
