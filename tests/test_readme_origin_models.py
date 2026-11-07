"""README の「エンジンの原点にある模型（試作して開発中）」の節（本人の言葉 11-07「作ってみる。試作して開発中と書く」と訂正「外の2は間違いで
原点にあるやつ」。エンジンの README の #147 と同じ言い方）。

見る事:
1. 節が「うつしと paper to toy」の節のすぐ後に 1 つある（エンジンの仕組みの続き。窓口へ出した推しの置き場 A）
2. 節の字: 「開発中」と「原点にある」があり、「できる」「できます」「作れる」「動く」と書かない（試作はまだ紙で組んでいない）。2 つの模型の名がある
3. 試作の名（振り子の波・二重らせん）を、30 秒の要約と「できること」の節に出さない（うつしの題材の江戸の玩具と混ぜない）
4. 節の中の engine/ の置き場は、今の repo に在るファイル（engine/ をまとめた後に「まとめる PR で直す」の古い 1 行を残さない。
   統括の確かめ 11-08「事実の直しとして今の置き場に替えてよい・意味は替えない」）
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
readme = (ROOT / "README.md").read_text(encoding="utf-8")
heads = [m.group(0) for m in re.finditer(r"(?m)^## .*$", readme)]
HEAD = "## エンジンの原点にある模型（試作して開発中）"


def section(head):
    a = readme.index(head + "\n")
    b = readme.find("\n## ", a + 3)
    return readme[a:b if b >= 0 else None]


# README の書き直し（本人の言葉 11-08「エンジンが合流してぐちゃぐちゃ…優勝できる形に」）で、この節は README から外し、エンジンの README（engine/README.md）
# の同じ見出しの節に任せる。README は短いエンジンの節から engine/README.md へつなぐ
assert HEAD not in readme and "[engine/README.md](engine/README.md)" in readme, "原点にある模型は engine/README.md へ"
eng = (ROOT / "engine/README.md").read_text(encoding="utf-8")
e = eng.index("### エンジンの原点にある模型（試作して開発中）")
sec = eng[e:eng.find("\n## ", e)]
assert "開発中" in sec and "原点にある" in sec and "振り子の波" in sec and "DNA の二重らせん" in sec, sec[:200]
summary = section("## 30 秒の要約")
can = section(next(h for h in heads if h.startswith("## できること")))
for w in ("振り子", "二重らせん"):
    assert w not in summary and w not in can, ("江戸の玩具の話と混ぜない", w)
# 4. engine/ の置き場の見張りは、節が README にあった時の物なので外した（今の節はエンジンの README の字で、エンジンの repo が持つ）
print("ok README のエンジンの原点にある模型（置き場・開発中・できると書かない・要約とできることに混ぜない・engine/ の置き場が在る）")
