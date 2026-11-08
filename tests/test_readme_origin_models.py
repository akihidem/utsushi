"""README の「エンジンの原点にある模型（試作して開発中）」の節（本人の言葉 11-07「作ってみる。試作して開発中と書く」と訂正「外の2は間違いで
原点にあるやつ」。エンジンの README の #147 と同じ言い方）。

見る事（README の書き直し 11-08 で、節は README から engine/README.md へ移した。今の見方）:
1. 節は README に無く、engine/README.md の同じ見出しの節にある。README は engine/README.md へつなぐ
2. engine/README.md の節の字: 「開発中」と「原点にある」があり、2 つの模型の名がある
3. README の中で原点にある模型を言う文に、「できる」「できます」「作れる」「動く」と書かない（試作はまだ紙で組んでいない）
4. 試作の名（振り子の波・二重らせん）を、30 秒の要約と「できること」の節に出さない（うつしの題材の江戸の玩具と混ぜない）
（前の 4 つ目の engine/ の置き場の見張りは、節が README にあった時の物なので外した。今の節はエンジンの README の字で、エンジンの repo が持つ）
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
# 試作をできた物として書かない（別の目の指摘 11-08 で戻した見張り）。節は engine/README.md へ移したので、README の中で原点にある模型を言う文を見る
for sent in re.split(r"(?<=。)", readme):
    if "原点" in sent or "振り子" in sent or "二重らせん" in sent:
        for w in ("できる", "できます", "作れる", "動く"):
            assert w not in sent, ("試作をできた物として書かない", w, sent.strip()[:60])
summary = section("## 30 秒の要約")
can = section(next(h for h in heads if h.startswith("## できること")))
for w in ("振り子", "二重らせん"):
    assert w not in summary and w not in can, ("江戸の玩具の話と混ぜない", w)
print("ok README のエンジンの原点にある模型（節は engine/README.md・開発中と原点・README の文にできると書かない・要約とできることに混ぜない）")
