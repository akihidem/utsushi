"""J-030 に引く本人の言葉（11-05）を、頭の字まで同じ字で残す試験。

頭の 1 字が記録によって割れていた（回送の文と J-030 が濁り、哲学の記録が澄み）。本人が 11-06 に「せっかく」と決めた。
引用は J-030 と哲学の記録の 2 か所にあり、`python -m omochae.ledger check` は引用の字を見ないので、片方だけ変わっても誰も気づかない。
だから 2 か所の行を字で見るのに加え、docs と README のどこで引いても、言葉の残りの前が決めた頭の字である事を見る。
落ちた時の文に言葉の残りを書かないのは、関門の証拠や帳面へ写った時に、この見張りの字として数えられないようにするため。
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
HEAD = "せっかく"
WORDS = HEAD + "江戸時代のおもちゃを作れるようにするから、このおもちゃの存在を知って欲しい。いろんな国の人に知って欲しい。"
REST = WORDS[len(HEAD):]

j030 = (ROOT / "docs/process/decisions/J030-reach-abroad.md").read_text(encoding="utf-8").splitlines()
assert j030.count(f"- **本人の言葉**: 「{WORDS}」") == 1, "J-030 の本人の言葉の行"
philosophy = (ROOT / "docs/process/philosophy.md").read_text(encoding="utf-8").splitlines()
assert philosophy.count(f"> {WORDS}") == 1, "哲学の記録の引用の行"

# 言葉の残りだけを探すのは、頭の字がどう変わっても（濁る・抜ける・別の字になる）同じ 1 つの照らしで拾うため。
for path in sorted([ROOT / "README.md", ROOT / "CLAUDE.md", *(ROOT / "docs").rglob("*.md")]):
    text = path.read_text(encoding="utf-8")
    assert text.count(REST) == text.count(WORDS), f"頭の字が違う引用: {path.relative_to(ROOT)}"
print("ok J-030 の本人の言葉は、頭の字まで哲学の記録と同じ")
