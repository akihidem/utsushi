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
4. 仕組みの節（見出しは「型紙が直るフィードバックループ」）に、SVG の絵の図が 1 つ（説明の字に輪の順）と、図の下に 5 行の字（図だけに頼らない。段の名つき）
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
# 11-08 から、3 つの項目は本人が書き直した字（standing-decisions の「README の頭の 3 つを本人が書き直した」の行）を一字も替えずに置く。
# どう直るかの最後の文は、本人の答え 11-08「(A) でよい。」で「それぞれ版 14・版 7 まで重ねました。」（前の字は打ち間違いに見えたので窓口が確かめた）
SUMMARY = (
    "- **何か**: 制約の多い学校や博物館でワークショップを開く人のために開発した、支援の道具です。紙とはさみとのりだけで作れる型紙を生成し、年齢や背景にとらわれずに伝えたい事を伝えられます。",
    # 題材は本人が欄 3 で採り（387）、README でも「この字でよい」（449）と言った字のまま。絵本の名は後ろに別の文で足す
    "- **題材**: 江戸時代のおもちゃ再現。江戸時代に出版された絵本には、おもちゃの絵と音だけが残っていて、動きは一見わかりません。それを紙でよみがえらせます。失われた玩具の復活と伝統工芸継承のプロジェクトです。絵本は『江都二色』（1773）です。",
    # 「直る」を、フィードバックループの言葉で何が何を直すのかが分かる形に（本人の言葉 11-08「「直る」の所は、フィードバックループなどの言葉を使って
    # 分かりやすくして。ハッカソンの審査員が読みやすい形に。」）。本人が決めた字「…ワークショップのフィードバックで直りました。」は替えない
    "- **どう直るか（フィードバックループ）**: 作る人が、作る途中や完成形を文字・音声・動画でのこします。その記録を作る側の Claude Code が読んで新しい案を考え、Claude が作ったエンジンが 3D で組んで確かめ、人が採った案が型紙の次の版になります。今回のデモで体験してもらう 2 案は、4 日間のワークショップを開催し、そのフィードバックで改善が進み、それぞれ版 14・版 7 まで重ねました。",
)
# 核の言葉は、頭の要約のすぐ下（統括の照らし 11-08: 伝えたい核を要約の近くに）。字は本人の今の言葉 11-08「システムが良くなるところをクロードが担って
# くれるから、人間は人間同士の関わりや工作に熱中できる。」（クロードの書き方だけ Claude に）。前の引用「AIが良くなるのは副次的…」は、本人の言葉 11-08
# 「この引用がよくわからない。AIによって良くなることは副次的なもの、の言い間違い。それと、これを言うと、作ったシステムの素晴らしさを矮小化している。」で外した
# （昔の記録 philosophy.md・research/34 はその時の言葉の記録なので替えないが、README からは引かない）
CORE = "「システムが良くなるところを Claude が担ってくれるから、人間は人間同士の関わりや工作に熱中できる。」（制作者の言葉 11-08）"
OLD_CORE = "AIが良くなるのは副次的"
# 売りの 1 行（本人の言葉 11-08「型紙改善、その型紙生成エンジンの改善のループが回るのが今回のシステムの売りです。README・提出文・デモはこの売りで書いて
# ください。」）。本人の 3 つの項目の字は替えず、その後に置く
URI = "- **売り（2 つのループ）**: 型紙を直すループと、型紙を作るエンジンを直すループの 2 つが回ります。エンジンの直しは、全部の玩具の型紙に効きます。"
SITE = "- サイト: https://utsushi.konoba.workers.dev"
ORDER = ("## 試す", "## 何の課題か・誰のためか", "## 仕組み: 型紙とエンジンが直る 2 つのフィードバックループ", "## Claude の使い方", "## 確かめた事と、まだの事", "## 作る気持ち",
         "## repo の地図と動かし方", "## 型紙を作るエンジン（paper to toy）", "## 決まりと出典")


def at(line):
    assert lines.count(line) == 1, (line[:60], lines.count(line))
    return lines.index(line)


# 1. 頭
assert lines[0] == "# utsushi", lines[0]
head = [ln for ln in lines[1:at("## 試す")] if ln.strip()]
# ループの中の人（本人の言葉 11-08「そしてちゃんとグラウンディングで人間が入ってる。ループの中に人間が入っている事も売りに書いてください。」
# 「型紙をためしてもらうグラウンディングと、全体の改善案をみる管理人のグラウンディング。この 2 つを書いてください。」）
GROUND = "- **ループの中に人がいる（2 つのグラウンディング）**: ① 型紙を試す作り手が、紙で作って現実の世界で確かめます。② 全体の改善案を見る管理人が、どの案を採るかと、エンジンをどう直すかを決めます。"
assert head == [ONE_LINE, *SUMMARY, URI, GROUND, CORE], head
assert lines.count(CORE) == 1, "核の言葉は頭の 1 行（畳みの 30 秒の要約の核の項目は CLAUDE.md と同じ字なので、同じ引用がもう 1 か所ある）"
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
how = text[text.index("## 仕組み: 型紙とエンジンが直る 2 つのフィードバックループ\n"):text.index("## Claude の使い方\n")]
# 図は SVG の絵（docs/img/feedback-loop.svg）。前の mermaid の塊は、GitHub の携帯のアプリなどで描かれず字のまま出た（本人の言葉 11-08「flowchart LRが
# そのまま字で表示されてる。図として出るように直してください。」）。絵の説明の字（alt）に輪の順を書き、AI にも読めるようにする。図は 1 度だけ出す
IMG = re.search(r"!\[(2 つのフィードバックループ: [^\]]+)\]\((docs/img/feedback-loop\.svg)\)", how)
assert IMG and how.count("![") == 1 and "```mermaid" not in text, "図は SVG の絵 1 つ（mermaid の塊を残さない）"
assert all(w in IMG.group(1) for w in ("のこす", "作る側の Claude Code", "Claude が作ったエンジン", "3D", "人が採る", "新しい版を刷る")), IMG.group(1)
svg = (ROOT / IMG.group(2)).read_text(encoding="utf-8")
assert svg.startswith("<svg ") and "<title" in svg and "<image" not in svg and "<script" not in svg, "字を絵の中に持つ SVG（外の絵や script を読まない）"
assert all(w in svg for w in ("作る側の Claude Code が", "Claude が作ったエンジンが", "人が決める", "新しい版の型紙を刷る", "フィードバック")), "絵の中の字"
# 2 つのループ（型紙の版が上がる輪と、エンジンの版が上がる輪）が絵と説明の字の両方に見える（本人の言葉 11-08「…エンジンも改善される説明にしてください」「…ループが回るのが売り」）
assert "① 型紙の版が上がる輪" in svg and "② エンジンの版が上がる輪" in svg and "エンジンを直す" in svg, "絵の 2 つの輪"
assert svg.count(">作り手</text>") == 2 and svg.count(">管理人</text>") == 2, "絵の人の印（作り手が 2・管理人が 2）"
assert "作り手" in IMG.group(1) and "管理人" in IMG.group(1) and "グラウンディング" in how, "説明の字と節の字にも 2 つのグラウンディング"
assert "① 型紙の版が上がる輪" in IMG.group(1) and "② エンジンの版が上がる輪" in IMG.group(1), "説明の字の 2 つの輪"
# エンジンも直る事の例は、版の記録（data/history/kaizen-history.json）にある事だけ
eng = how[how.index("### エンジンも直る（版の記録にある例）"):]
hist = (ROOT / "data/history/kaizen-history.json").read_text(encoding="utf-8")
assert "色がついている所が外を向くよう折った" in eng and "色がついている所が外を向くよう折った" in hist, "例 1 の元の字が版の記録にある"
assert "虎の版 6 の当たり" in eng and "虎 v6 の当たりが見つかる" in hist, "例 2 の元の字が版の記録にある"
after = how[how.index(IMG.group(0)) + len(IMG.group(0)):]
steps = re.findall(r"(?m)^(\d)\. ", after)
assert steps == ["1", "2", "3", "4", "5"], ("図の下に 5 行の字", steps)
# 新しい案を考えたのは作る側の Claude Code（サイトの中の次の案の口は、まだ本物の鍵で呼んでいない。下の表と食い違わない。統括の照らし 11-08 の止め）
assert "作る側の Claude Code が" in how and "サイトの中で次の案を作る口は、まだ本物の鍵で呼んでいません" in how, "新しい案の主語"
assert how.count("フィードバックループ") >= 2 and "ループが 1 周します" in how, "見出しと字でフィードバックループの言葉を使い、何が何を直すかを言う"
steps_names = re.findall(r"(?m)^\d\. ([^:\n]+): ", how)
assert steps_names == ["作る", "のこす（フィードバック）", "案を考える", "3D で確かめる", "採って刷る"], steps_names
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
assert "「AI は鏡。" in text, "本人の言葉の引用は残す"
assert OLD_CORE not in text, "前の核の引用（本人が言い間違いと言った字）を README から引かない"
print(f"ok README の組み直しの形（頭と 3 行の要約・節 {len(ORDER)} つの並び・投稿ビデオの項なし・仕組みの図と 5 行・表は 3 列まで・要約 {items} 項目は畳み）")
