"""サイトの AI の名前の書き方（本人の決定 11-06）。

本人の決定: サイトの AI は Claude と分かる書き方にする。子どもが触る画面は「AI」のまま、断り（声・字・写真をどう使うかの説明）には
「（Claude）」を添える。英語の頁は「AI (Claude)」。釦や見出しの「AI」は変えない。

なぜ文の一覧でなく形で見るか: 断りはこれからも足される。「AI が人の字を読む・渡す・送る・使う・返事をする」と言う文に名前が無ければ落とす形にすると、
足した時に気づける。「AI が考えた仮説」や「AI の返事は使えません」は断りではないので落とさない。

見る事:
1. 学ぶ人の頁の字と、頁を作る作りの字に、名前の無い断りの形が無い
2. 採った文が /about と持ち寄りの入口にある
3. 札と状態の「AI」は変えていない（対照）
"""
import html
import os
import pathlib
import re
import tempfile
import threading
import urllib.parse
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(os.environ["OMOCHAE_DATA"], "api-usage.jsonl")

from web.play_server import serve  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
G = "NDL-1187053-R0000005-L"
from omochae import hypotheses  # noqa: E402
# 御来迎のたたき台は組ごと（今の組 goraigo-v14 は H-C・記録の欄 sheet_by_set）。今の組で刷れるのはたたき台の紙だけ
GS = hypotheses.sheet_of(G)["id"]
# 「AI」の後に（Claude）が無く、同じ文の近くに人の字の使い方の動詞が続く形。「AI の Claude」も名前が分かるので通す（持ち寄りの入口の前からの字）
NAMELESS_JA = re.compile(r"AI(?!（Claude）| の Claude)[^。\n]{0,16}?(?:渡|送|読|使[いう]|からも返事)")
NAMELESS_EN = re.compile(r"\bAI\b(?! \(Claude\))[^.\n]{0,24}?\b(?:reads?|sends?|sent|uses?|used|given)\b")

# 本人が採った字のため外す 1 文（保護者の方へ、ファシリテーターの方への頁の 5 節。research/36 の「採られた文」、本人の決定 11-06）。
# 39 行は本人が訂正を入れた形で採った物で、記録の注に「前に採られた行の「AI」は変えていない」とある。この行の「AI」もその形のまま。
# 形の見張りは緩めず、この字と一字も違わない文だけを外す。字が変われば外れず、見張りに戻る。記録の注と文が無くなっても落とす
ADOPTED_AS_AI = "記録と、作った人の説明の後で、AI が読みと次の案を出します。採るかどうかは、人が決めます。"
_r36 = (ROOT / "docs/process/research/36-road-and-audience.md").read_text(encoding="utf-8")
assert "前に採られた行の「AI」は変えていない。" in _r36, "外す根拠の注が research/36 から消えた。外すのをやめて本人に確かめ直す"
assert f"\n- {ADOPTED_AS_AI}\n" in _r36.split("## 採られた文: 保護者の方へ、ファシリテーターの方へ", 1)[1].split("この文と作りの対応:", 1)[0], "外す文が採られた文に無い。外すのをやめる"


def unexempt(text):
    """採られた字のまま外す 1 文を除く。ほかの字は見張りにかける。"""
    return text.replace(ADOPTED_AS_AI, "")


# 見張りそのものの確かめ
assert NAMELESS_JA.search("聞いた言葉は AI に送ります") and NAMELESS_JA.search("AI からも返事をもらえます") and NAMELESS_JA.search("AI が字を読みます")
assert not NAMELESS_JA.search("AI（Claude）からも返事をもらえます") and not NAMELESS_JA.search("残した字は、AI（Claude）が読みます") and not NAMELESS_JA.search("参考として AI の Claude にも渡します")
assert not NAMELESS_JA.search("AI が考えた仮説です") and not NAMELESS_JA.search("AI の返事は、この場では使えません") and not NAMELESS_JA.search("今は AI に聞けません")
assert NAMELESS_EN.search("The AI reads your words") and not NAMELESS_EN.search("The AI (Claude) reads your words") and not NAMELESS_EN.search("It is a guess made by an AI.")
# 外すのは見張りに当たる文だけ（当たらなくなったら外す要が無い）。外した後の同じ形の別の文は、まだ落ちる
assert NAMELESS_JA.search(ADOPTED_AS_AI) and not NAMELESS_JA.search(unexempt(ADOPTED_AS_AI)) and NAMELESS_JA.search(unexempt("記録の後で、AI が読みと次の案を出します。"))

server = serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"


def get(path):
    return urllib.request.urlopen(base + path, timeout=120).read().decode("utf-8", "replace")


def visible(page):
    """頁の字。作りの字の見張りと別に、組み合わさった後の文を見る。"""
    page = re.sub(r"<style.*?</style>", " ", page, flags=re.S)
    return html.unescape(re.sub(r"<[^>]+>", " ", page))


req = urllib.request.Request(base + f"/toy/{G}/print", urllib.parse.urlencode({"hypothesis": GS}).encode(), {"Origin": base})
assert urllib.request.urlopen(req, timeout=120).status == 200

# 1. 頁の字に、名前の無い断りの形が無い
PAGES = ["/", "/toys", "/about", "/otona", "/gallery", f"/zukan/{G}/yomi", f"/toy/{G}", f"/toy/{G}/techo", f"/toy/{G}/tsukuru", "/en", f"/en/toy/{G}"]
for path in PAGES:
    text = unexempt(visible(get(path)))
    assert not NAMELESS_JA.findall(text), (path, NAMELESS_JA.findall(text))
    assert not NAMELESS_EN.findall(text), (path, NAMELESS_EN.findall(text))

# 作りの字: 鍵がある時や送った後にだけ出る文も見る。持ち寄りの入口（contrib_server）の断りもここで見る。コメントの行は頁に出ないので除く
for path in sorted((ROOT / "src/web").glob("*.py")) + [ROOT / "src/omochae/making_log.py", ROOT / "src/omochae/talk_log.py", ROOT / "src/api/ask.py"]:
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.lstrip().startswith("#"):
            continue
        assert not NAMELESS_JA.search(unexempt(line)), (path.name, n, line.strip()[:80])
        assert not NAMELESS_EN.search(line), (path.name, n, line.strip()[:80])

# 2. 採った文
assert "自分の考えを書いた後で、AI（Claude）からも返事をもらえます。" in visible(get("/about"))
assert "この場所での表示だけ（AI（Claude）には渡しません）" in (ROOT / "src/web/contrib_server.py").read_text(encoding="utf-8")

# 3. 札と状態の字は「AI」のまま（子どもが触る画面。本人の決定）
toy = visible(get(f"/toy/{G}"))
assert "AI が「こうかな？」と考えた、ためしの案（仮説）です" in toy and "AI（Claude）が「こうかな" not in toy
assert "仮説は、AI が考えたためしの案です" in toy
# えらぶ の頭の断りの段は序の頁（よむ）へ移した（窓口の決定 11-07 の ②）。見張りも行き先へ移す
assert "型紙は正解ではなく、AI が考えた仮説です" in visible(get("/about"))
assert "It is a guess made by an AI." in visible(get(f"/en/toy/{G}"))

print("ok: 断りの AI には名前を添え、札と状態の AI は変えていない")
