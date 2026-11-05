#!/bin/bash
# 台帳や記録を手で直した直後に、台帳の検査（根拠の文の照合、索引、要約の一致）を回す。
# なぜフックか: 直した後に検査を回し忘れると、push の前の ./run.sh まで食い違いが見つからない。毎回走らせ、落ちたら Claude に返して直させる。
# 落ちた時と検査できない時は exit 2（Claude Code が stderr を Claude に返す。PostToolUse なので編集は戻らない）。
# なぜ検査できない時も 2 か: exit 0 の stderr は Claude に届かず、回らなかった事に誰も気づけない。対象の外の編集は止めない。
root="$(cd "$(dirname "$0")/../.." && pwd -P)"
cannot() { echo "検査できない: $1（この編集の後の台帳は確かめていない）" >&2; exit 2; }
# 相対のパスは Claude Code の渡す cwd から解く。.. と symlink を畳んでから比べないと、渡され方で判定が変わる
path="$(python3 -c '
import json, os, sys
d = json.load(sys.stdin)
p = d.get("tool_input", {}).get("file_path", "")
print(os.path.realpath(os.path.join(d.get("cwd") or os.getcwd(), p)) if p else "")' 2>/dev/null)" || cannot "フックの入力が読めない"
case "$path" in
  "$root"/docs/*|"$root"/data/*|"$root"/README.md|"$root"/CLAUDE.md|"$root"/tests/frozen/*|"$root"/src/omochae/ledger.py) ;;
  *) exit 0 ;;
esac
[ -x "$root/.venv/bin/python" ] || cannot ".venv が無い（./init.sh を先に）"
out="$(cd "$root" && PYTHONPATH=src .venv/bin/python -m omochae.ledger check 2>&1)"
rc=$?
[ "$rc" -eq 0 ] && exit 0
if [ "$rc" -eq 3 ]; then
  echo "台帳の検査が落ちた。直すか、記録から描く物なら python -m omochae.ledger render を回す:" >&2
  echo "$out" >&2
  exit 2
fi
echo "$out" >&2
cannot "台帳の検査が rc $rc で終わった"
