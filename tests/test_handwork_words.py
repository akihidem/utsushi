"""本人の言葉を、字を変えずに哲学の記録に残す試験。

本人の言葉は引用の 1 行で持ち、見出しのすぐ下に置く。見出しは本人の言葉の要約でなく、引用の上に置く目印。
この字はサイトや紙に出す文ではなく、記録（文面の採否は同じ節の決まりのとおり本人の確認が要る）。
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
HEAD = "### 手仕事の継承: 子どもが主役になり、AI と技術と物語を継ぐ（11-05 夜）"
WORDS = "職人がもうほぼおらず、文献もほぼない、ナレッジがまとまっていない、というような手仕事をどう復活させるか、継承するか。その未来の担い手にある子供たちが主役となりAIと技術物語継承をする。"

lines = (ROOT / "docs/process/philosophy.md").read_text(encoding="utf-8").splitlines()
assert lines.count(HEAD) == 1, HEAD
assert lines.count(f"> {WORDS}") == 1, WORDS
next_line = next(ln for ln in lines[lines.index(HEAD) + 1:] if ln.strip())
assert next_line == f"> {WORDS}", next_line
print("ok 本人の言葉は字を変えずに見出しのすぐ下にある")
