"""README の頭（本人の決定 11-05「README の頭の案（説明の 3 行を含む）を採る」）の試験。

本人の方針（11-05 20:10）「たくさん見る審査員の認知負荷を減らす方針が1番最初。癒し系で。」から作った案を、本人が採った。
見る事:
1. 一言・本人の言葉・説明の 3 行が、一字も変わらず、この順で、畳んだ要約より上にある
2. 頭に見える字は、上の物と、絵とリンクの行だけ（要約を頭に戻さない）
3. 要約は畳んだ中にあり、見出しの項目の数が中身と合う（要約の字は omochae.ledger の L.summary が CLAUDE.md と照らす）

4 つのループの絵は本人の採否待ち、デモ動画のリンクは動画待ちで、今は見えない印だけ。入れる時は印を置き換えればよく、ここは変えなくてよい。
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
ONE_LINE = "> 失われた玩具の動きを、紙で実験して確かめる道具"
WORDS = "「AIが良くなるのは副次的なもので、みんなが手で実際に作ることその楽しさに気づくことが最初。」（本人の言葉）"
ADOPTED = (
    "江戸の絵本『江都二色』（1773）には、玩具の図と歌だけが残っています。動く仕組みは書かれていません。",
    "AI が考えた型紙を紙に刷り、切って、折って、作って、動きを確かめます。",
    "型紙は正解ではなく、AI が考えた仮説です。作った人の工夫から、人が直しを選んで、次の版にします。",
)

lines = (ROOT / "README.md").read_text(encoding="utf-8").splitlines()


def at(text):
    assert lines.count(text) == 1, (text, lines.count(text))
    return lines.index(text)


assert lines[0] == "# utsushi", lines[0]

# 1. 本人が採った字が、この順で要約より上にある
fold, start, end, close = at("<details>"), at("<!-- summary:start -->"), at("<!-- summary:end -->"), at("</details>")
order = [at(ONE_LINE), at(WORDS), *map(at, ADOPTED), fold, start, end, close]
assert order == sorted(order), order

# 2. 頭に見える字を増やさない。隠れる印と、絵・リンクの行は数えない
shown = [ln for ln in lines[1:fold] if ln.strip() and not ln.startswith("<!--") and not re.search(r"!\[|https?://", ln)]
assert shown == [ONE_LINE, WORDS, *ADOPTED], shown

# 3. 要約は畳んだ中にあり、見出しの数が中身と合う
items = sum(ln.startswith("- **") for ln in lines[start:end])
assert items > 0
assert lines[fold + 1] == f"<summary>くわしい要約（{items} 項目）</summary>", lines[fold + 1]
print(f"ok README の頭は本人が採った字で、要約 {items} 項目は畳んである")
