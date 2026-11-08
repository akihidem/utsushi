"""README の組み直し（11-08）の形の試験。

本人の言葉 11-08「今読んだら、表が読みにくい、全体的に構造化できていないので分かりにくい。仕組みもわからない。ハッカソンの審査員と審査用の AI が
読んでわかりやすく優勝できるものにする。投稿ビデオの項が残っているので消す。」から、前の README の字を元にせず、本人の決めの記録（grove の
standing-decisions）から骨組みを組み直した（骨組みは統括が「書き始めてよい」11-08）。前の頭（4 列の要約の表・大前提の 3 段・説明の 3 行）は外した。
説明の 3 行の「AI」を「Claude」と書く決め（本人の決定 11-06。審査員が見る所ははっきり Claude と書く）は、そのまま見る。

見る事:
1. 頭: 題・一言（入口の副題にそろえた・窓口の決め 11-08）・3 行の要約・核の言葉。その後の最初の節が「試す」で、決まった番地（窓口 11-08 の訂正の番地）が頭の 30 行の内にある
   （提出の床が頭の 30 行を見る）
2. 節の並び: 試す → 何の課題か・誰のためか → 仕組み → Claude の使い方 → 確かめた事と、まだの事 → 作る気持ち → repo の地図と動かし方 → エンジン → 決まりと出典
3. 投稿ビデオの項を残さない（本人の言葉 11-08）。動画のリンクの見えない印も置かない（統括の決め 11-08: HTML の注は AI に読まれる内輪の印。動画を上げた時に
   統括が見える 1 行を足す）。README の HTML の注は、台帳が描く 2 組の印（要約と数）だけ
4. 仕組みの節に、GitHub で描ける図（mermaid）が 1 つと、図の下に 5 行の字（図だけに頼らない）
5. 表は 3 列まで（本人の「表が読みにくい」）。1 行 1 事実
6. Claude の使い方の節: 本物の鍵で動いた口と、まだの口（記録の動画の 3 コマ・次の手の案）を分けて書く（統括の決め 11-08「どれが動いた・どれがまだ」）
7. 30 秒の要約は畳んだ中にあり、見出しの項目の数が中身と合う（要約の字は omochae.ledger の L.summary が CLAUDE.md と照らす）
8. 審査員が読む所は「AI」でなく「Claude」と書く。本人の言葉の引用（「」の中）は変えない
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
text = (ROOT / "README.md").read_text(encoding="utf-8")
lines = text.splitlines()

ONE_LINE = "> うしなわれた玩具の動きを、紙でよみがえらせる"
# 3 行の要約（字は欄 3 v10・本人の言葉 11-08 の 386〜388・392・453・463 から。本人の確かめ待ち）
SUMMARY = (
    "- **何か**: 学校や博物館でワークショップを開く人のための、ワークショップ支援のウェブの道具です。紙とはさみとのりだけで作れる型紙で、いろいろな年齢の人に伝えたい事を伝えられます。",
    # 題材は本人が欄 3 で採り（387）、README でも「この字でよい」（449）と言った字のまま。絵本の名は後ろに別の文で足す
    "- **題材**: 江戸時代のおもちゃです。江戸時代に出版された絵本に絵と音だけが残り、動きがわからなくなった玩具を、紙でよみがえらせます。玩具復活と伝統工芸継承のプロジェクトです。絵本は『江都二色』（1773）です。",
    "- **どう直るか**: 作る人が、作る途中や完成形を文字・音声・動画でのこします。Claude はその記録をもとに新しい案を考え、Claude が作ったエンジンが 3D で組んで確かめます。"
    "今回のデモで体験してもらう 2 案は、それぞれ版 14・版 7 まで、4 日間のワークショップのフィードバックで直りました。",
)
# 核の言葉（本人の言葉 11-05「今話してるこの部分が今回のハッカソンの核になる」）は、頭の要約のすぐ下（統括の照らし 11-08: 伝えたい核を要約の近くに）
CORE = "「AIが良くなるのは副次的なもので、みんなが手で実際に作ることその楽しさに気づくことが最初。」（制作者の言葉）"
SITE = "- サイト: https://utsushi.konoba.workers.dev"
ORDER = ("## 試す", "## 何の課題か・誰のためか", "## 仕組み", "## Claude の使い方", "## 確かめた事と、まだの事", "## 作る気持ち",
         "## repo の地図と動かし方", "## 型紙を作るエンジン（paper to toy）", "## 決まりと出典")


def at(line):
    assert lines.count(line) == 1, (line[:60], lines.count(line))
    return lines.index(line)


# 1. 頭
assert lines[0] == "# utsushi", lines[0]
head = [ln for ln in lines[1:at("## 試す")] if ln.strip()]
assert head == [ONE_LINE, *SUMMARY, CORE], head
assert text.count(CORE) == 1, "核の言葉は頭の 1 か所"
assert at(SITE) < 30, "決まった番地は頭の 30 行の内"

# 2. 節の並び（## の見出しはこの 9 つと、畳みの中の 30 秒の要約だけ）
heads = [ln for ln in lines if ln.startswith("## ")]
assert [h for h in heads if h != "## 30 秒の要約"] == list(ORDER), heads

# 3. 投稿ビデオの項と見えない印
for w in ("デモ動画", "YouTube", "合成の声", "投稿ビデオ", "動画のリンク"):
    assert w not in text, ("投稿ビデオの項が残っている", w)
notes = re.findall(r"<!--(.*?)-->", text, re.S)
assert sorted(n.strip() for n in notes) == ["counts:end", "counts:start", "summary:end", "summary:start"], notes

# 4. 仕組みの図と 5 行の字
how = text[text.index("## 仕組み\n"):text.index("## Claude の使い方\n")]
assert how.count("```mermaid\n") == 1 and "flowchart" in how, "GitHub で描ける図が 1 つ"
after = how[how.index("```", how.index("```mermaid") + 3) + 3:]
steps = re.findall(r"(?m)^(\d)\. ", after)
assert steps == ["1", "2", "3", "4", "5"], ("図の下に 5 行の字", steps)
# 新しい案を考えたのは作る側の Claude Code（サイトの中の次の案の口は、まだ本物の鍵で呼んでいない。下の表と食い違わない。統括の照らし 11-08 の止め）
assert "作る側の Claude Code が" in how and "サイトの中で次の案を作る口は、まだ本物の鍵で呼んでいません" in how, "新しい案の主語"
assert "Claude が作ったエンジン" in how and "人が決め" in how, "輪の主語（本人の言葉 11-08「Claude が作ったエンジンが 3D で組んで確かめ」・どの版にするかは人が決める）"

# 5. 表は 3 列まで
for ln in lines:
    if ln.startswith("|"):
        assert ln.count("|") <= 4, ("表は 3 列まで", ln[:60])

# 6. 動いた口とまだの口
use = text[text.index("## Claude の使い方\n"):text.index("## 確かめた事と、まだの事\n")]
rows = [ln for ln in use.splitlines() if ln.startswith("| ") and not ln.startswith("| 口 ")]
assert {r.rsplit("|", 2)[1].strip() for r in rows} <= {"動いた（11-07）", "まだ"} and sum(r.endswith("| まだ |") for r in rows) == 2, rows
assert any("observe.py" in r and r.endswith("| まだ |") for r in rows), "記録の動画の 3 コマはまだ"
assert "記録の読み（字と、動画の 3 コマ）" in use

# 7. 30 秒の要約は畳みの中
fold, start, end, close = at("<details>"), at("<!-- summary:start -->"), at("<!-- summary:end -->"), at("</details>")
assert fold < start < end < close
items = sum(ln.startswith("- **") for ln in lines[start:end])
assert items > 0 and lines[fold + 1] == f"<summary>くわしい要約（{items} 項目）</summary>", lines[fold + 1]

# 8. 審査員が読む所は「AI」でなく「Claude」と書く（本人の決定 11-06）。本人の言葉の引用と、紙や画面の字の引用（「」の中）は変えない。
# 前後を英字でない所に限るのは、FAIL や MAIN のような語に当てないため。要約は CLAUDE.md と同じ字なので、ここで一緒に見た事になる
AI_WORD = re.compile(r"(?<![A-Za-z])AI(?![A-Za-z])")
left = [ln[:60] for ln in lines if AI_WORD.search(re.sub(r"「[^」]*」", "", ln))]
assert not left, ("README の中は審査員が読む所なので「Claude」と書く（本人の決定 11-06）", left)
assert "「AI は鏡。" in text and "「AIが良くなるのは副次的なもので" in text, "本人の言葉の引用は残す"
print(f"ok README の組み直しの形（頭と 3 行の要約・節 {len(ORDER)} つの並び・投稿ビデオの項なし・仕組みの図と 5 行・表は 3 列まで・要約 {items} 項目は畳み）")
