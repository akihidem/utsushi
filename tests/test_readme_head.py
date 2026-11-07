"""README の頭（本人の決定 11-05「README の頭の案（説明の 3 行を含む）を採る」）の試験。

本人の方針（11-05 20:10）「たくさん見る審査員の認知負荷を減らす方針が1番最初。癒し系で。」から作った案を、本人が採った。
説明の 3 行の「AI」は、本人の決定（11-06、AI の名前の書き方。審査員が見る所ははっきり Claude と書く）で「Claude」にした。本人の言葉の引用は変えない。
見る事:
1. 一言・本人の言葉・説明の 3 行・審査の人が 30 秒で読む 4 行が、一字も変わらず、この順で、畳んだ要約より上にある
2. 頭に見える字は、上の物と、絵だけの行・デモ動画のリンクだけの行に限る（要約を頭に戻さない）。隠れる印は 1 行で閉じる
   （閉じ忘れると、次の `-->` までの字が GitHub の描画から消える。説明の 3 行と畳みが消えるのを描画で確かめた）
3. 要約は畳んだ中にあり、見出しの項目の数が中身と合う（要約の字は omochae.ledger の L.summary が CLAUDE.md と照らす）

4 つのループの絵は本人の採否待ち、デモ動画のリンクは動画待ちで、今は見えない印だけ。入れる時は印を置き換えればよく、ここは変えなくてよい。
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
HIDDEN = re.compile(r"<!--((?!-->).)*-->")
PICTURE = re.compile(r"!\[[^\]]*\]\([!-~]+\)|\[!\[[^\]]*\]\([!-~]+\)\]\([!-~]+\)|<img\s[^<>]*>")
VIDEO = re.compile(r"(- )?デモ動画(（[^）]{0,8}）)?[:：] ?https?://[!-~]+|\[デモ動画[^\]]{0,12}\]\(https?://[!-~]+\)")
ONE_LINE = "> 失われた玩具の動きを、紙で実験して確かめる道具"
WORDS = "「AIが良くなるのは副次的なもので、みんなが手で実際に作ることその楽しさに気づくことが最初。」（本人の言葉）"
ADOPTED = (
    "江戸の絵本『江都二色』（1773）には、玩具の図と歌だけが残っています。動く仕組みは書かれていません。",
    "Claude が考えた型紙を紙に刷り、切って、折って、作って、動きを確かめます。",
    "型紙は正解ではなく、Claude が考えた仮説です。作った人の工夫から、人が直しを選んで、次の版にします。",
)
# 審査の人が 30 秒で読む 4 行（本人の言葉 11-07 夜「うつしとエンジンのreadme もハッカソンで優勝するために書き直す？審査員が読むと思う。
# yomiyasuで分かりやすくもして欲しい」）。何の作品か・誰のためか・何が動くか・どう見るかを、説明の 3 行の後に 1 行ずつ。字は本人の確かめ待ちの案。
# 頭に見える字を増やす事になるので（11-05 の方針「審査員の認知負荷を減らす」）、1 つの問いに 1 行の箇条にして、くわしい事は畳んだ要約と下の節に置く
JUDGE = (
    '- **何の作品か**: 図と歌だけが残る江戸の玩具を、紙の型紙で作って動かし、仕組みを確かめます。サイト（うつし）で玩具を選んで型紙を刷ります。型紙を作る仕組みは、エンジン（paper to toy）として別に開発し、engine/ にも入れました。',
    '- **誰のためか**: 出発は本人の教育現場の学習活動です。博物館や科学館のワークショップ、夏休みの自由研究にも使えると考えています（本人の見立て）。ワークショップは 4 回（11 月 4・5・6・7 日）開きました。',
    '- **何が動くか**: 型紙を作り、刷る前と刷った後に検査して、通った紙だけを A4 の PDF にします。御来迎と張子の首振り虎は、組み立ての手順を 3D で見られます。手帖では、作りながら写真や動画と一緒に記録を残せます。本物の Claude API は、まだ動かしていません。',
    '- **どう見るか**: 要る物は下の「動かし方」にあります。`./run-home.sh` を打つと、手元のブラウザでサイトが開きます（http://127.0.0.1:8766/）。`./run.sh` は全部の検査を回します（8〜9 分。結果は `out/RESULT.md`）。作った過程の記録は [docs/process/README.md](docs/process/README.md) から辿れます。',
)

lines = (ROOT / "README.md").read_text(encoding="utf-8").splitlines()


def at(text):
    assert lines.count(text) == 1, (text, lines.count(text))
    return lines.index(text)


assert lines[0] == "# utsushi", lines[0]

# 1. 本人が採った字が、この順で要約より上にある
fold, start, end, close = at("<details>"), at("<!-- summary:start -->"), at("<!-- summary:end -->"), at("</details>")
order = [at(ONE_LINE), at(WORDS), *map(at, ADOPTED), *map(at, JUDGE), fold, start, end, close]
assert order == sorted(order), order

# 2. 隠れる印は 1 行で閉じ、後ろに字を続けない。頭に見える字を増やさない。数えないのは、印と、絵だけの行と、動画のリンクだけの行
head = lines[1:fold]
for ln in head:
    assert not ("<!--" in ln or "-->" in ln) or HIDDEN.fullmatch(ln), ln
shown = [ln for ln in head if ln.strip() and not any(x.fullmatch(ln) for x in (HIDDEN, PICTURE, VIDEO))]
assert shown == [ONE_LINE, WORDS, *ADOPTED, *JUDGE], shown

# 3. 要約は畳んだ中にあり、見出しの数が中身と合う
items = sum(ln.startswith("- **") for ln in lines[start:end])
assert items > 0
assert lines[fold + 1] == f"<summary>くわしい要約（{items} 項目）</summary>", lines[fold + 1]

# 4. 審査員が読む所は「AI」でなく「Claude」と書く（本人の決定 11-06）。本人の言葉の引用と、紙や画面の字の引用（「」の中）は変えない。
# 英語の紹介も同じ（README は審査員が読む所）。序の頁は学ぶ人の頁で「AI」のままなので、ここでは見ない。要約は CLAUDE.md と同じ字なので、ここで一緒に見た事になる。
# 前後を英字でない所に限るのは、FAIL や MAIN のような語に当てないため。
AI_WORD = re.compile(r"(?<![A-Za-z])AI(?![A-Za-z])")
left = [ln[:60] for ln in lines if AI_WORD.search(re.sub(r"「[^」]*」", "", ln))]
assert not left, ("README の中は審査員が読む所なので「Claude」と書く（本人の決定 11-06。英語の紹介も同じ）", left)
assert all(x in "\n".join(lines) for x in ("「AI は鏡。", WORDS)), "本人の言葉の引用は残す"
print(f"ok README の頭は本人が採った字で、要約 {items} 項目は畳んである")
