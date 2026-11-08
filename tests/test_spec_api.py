"""仕様書（docs/process/spec.md）の本物の API の字が、11-07 に手元で本物の鍵を置いて呼んだ事実と食い違わない事。

なぜ: 仕様書は「本物の API は 0 回」「まだ確かめていない事: 本物の API」のままだったが、11-07 に聞く口・記録の読み・言葉の仮説・原画から仮説の案の
4 つを本物の鍵で呼んでいる（docs/claude-usage.md・README の Claude の使い方の表。統括の頼み 11-08「事実に直す」）。
見る事:
1. 前の字（「本物の API は 0 回」と、まだ確かめていない事の頭の「本物の API、」）が残っていない
2. まだ確かめていない事は、README の表で「まだ」の 2 つの口（記録の動画の 3 コマ・次の手の案）だけを本物の API のまだとして言う
3. claude-usage.md に 11-07 の本物の鍵の事実がある（仕様書が指す先）
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = (ROOT / "docs/process/spec.md").read_text(encoding="utf-8")
usage = (ROOT / "docs/claude-usage.md").read_text(encoding="utf-8")
readme = (ROOT / "README.md").read_text(encoding="utf-8")

assert "本物の API は 0 回" not in spec and "まだ確かめていない事: 本物の API、" not in spec, "前の字が残っている"
line = next(ln for ln in spec.splitlines() if ln.startswith("まだ確かめていない事:"))
assert "記録の動画の 3 コマを見せる口と次の手の案" in line, line[:80]
still = [ln for ln in readme.splitlines() if ln.startswith("| ") and ln.endswith("| まだ |")]
assert len(still) == 2 and any("observe.py" in r for r in still) and any("次の手の案" in r for r in still), still
assert re.search(r"本物の API は、11-07 に手元で本物の鍵を置いて", usage), "claude-usage.md の事実"
print("ok 仕様書の本物の API の字（0 回の字なし・まだは 2 つの口だけ・claude-usage の 11-07 の事実）")
