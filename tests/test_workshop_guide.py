"""進行者の手引き（#188）の紙の文の床。

なぜ: 場の崩れ方で一番ありそうなのは、進行者が良かれと思って仕組みを教える事（読み）。手引きの言葉はこれから本人が直すので、
直した時に評価の語と仕組みの名前が入らない事と、時間割の合計が崩れない事を機械で見る。A4 の 2 頁に収まるかは刷って見る（./run.sh はブラウザなしで動く決まり）。
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
text = (ROOT / "docs/process/workshop-guide.md").read_text(encoding="utf-8")

# 評価の語と、仕組みの名前。手順の紙には出る語でも、進行者が場で渡す物ではない。
for word in ("成功", "失敗", "正解", "蛇腹", "ジャバラ", "蝶番", "てこ"):
    assert word not in text, word

# 時間割の分を足した数と、本文の「合計」の行が合っている。
rows = re.findall(r"^\| \d [^|]+\| (\d+) 分 \| (\d+) 分 \|", text, flags=re.M)
assert len(rows) == 8, rows
five, room = sum(int(a) for a, _ in rows), sum(int(b) for _, b in rows)
assert f"5 人が {five} 分、教室が {room} 分" in text, (five, room)

# #188 のゴールの要件にある節。
for head in ("言う事・言わない事", "止まった人への 5 つの段", "よくある場面", "場の後の 15 分", "家庭で使う時の 3 行"):
    assert f"## {head}" in text, head
assert len(re.findall(r"^\d\. ", text.split("## 家庭で使う時の 3 行")[1], flags=re.M)) == 3

# 手引きが文書と同じ断りを言う（サイトの文と同じ言葉にする。文書の 3.2）。
for words in ("じょうずかどうかを見るためではありません", "声と映像は残しません", "鏡は出さなくても全部できます"):
    assert words in text, words
print("手引きの床: 通る")
