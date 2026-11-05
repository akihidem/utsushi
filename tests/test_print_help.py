"""型紙の窓の PDF の釦のすぐ下に、印刷で止まった時の案内を 1 つ置く（#297）。

なぜ: 窓の説明は「100% で刷り」だけで、設定の場所も、10cm でない時も、プリンタが無い時も画面に無かった。序の頁に置くと、止まった時に見つからない。
details なので JS なしで開く。文は玩具にも仮説にもよらない（型紙は玩具ごとに 1 枚にする決定 #332 で、仮説ごとの案内は要らなくなる）。
文の表が空の時は何も出さない。文面を本人が確かめるまで、仕組みだけを main に入れられるようにするため。
"""
import os
import re
import tempfile
import threading
import urllib.parse
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(os.environ["OMOCHAE_DATA"], "api-usage.jsonl")

from web import toy  # noqa: E402
from web.play_server import serve  # noqa: E402

G = "NDL-1187053-R0000005-L"
WORDS_SUMMARY, WORDS = toy.PRINT_HELP_SUMMARY, toy.PRINT_HELP
SAMPLE = (("見出し<1>", "文の 1"), ("見出し 2", "文の 2"), ("見出し 3", "文の 3"))


def help_part(page):
    found = re.findall(r'<details class="meta print-help">.*?</details>', page, re.S)
    assert len(found) <= 1, ("案内は 1 つ", len(found))
    return found[0] if found else ""


printed = False
for look in ("tenji", "zine"):
    server = serve(0, look=look)
    base = f"http://127.0.0.1:{server.server_address[1]}"
    threading.Thread(target=server.serve_forever, daemon=True).start()
    if not printed:
        for hid in ("H-A", "H-B"):
            data = urllib.parse.urlencode({"hypothesis": hid}).encode()
            urllib.request.urlopen(urllib.request.Request(f"{base}/toy/{G}/print", data=data, headers={"Origin": base}), timeout=120)
        printed = True
    get = lambda q: urllib.request.urlopen(f"{base}/toy/{G}{q}", timeout=60).read().decode()  # noqa: E731

    # 文の表が空なら、窓に何も足さない
    toy.PRINT_HELP_SUMMARY, toy.PRINT_HELP = "", ()
    assert help_part(get("?see=H-A&kind=sheet&v=1")) == "", ("空の時は出さない", look)

    toy.PRINT_HELP_SUMMARY, toy.PRINT_HELP = "止まった時", SAMPLE
    page = get("?see=H-A&kind=sheet&v=1")
    part = help_part(page)
    assert part, ("案内が無い", look)
    # 押す前は閉じていて、1 回押せば全部読める。JS に頼らない
    assert "<summary>止まった時</summary>" in part and "<script" not in part and " on" not in part.split(">")[0]
    for head, text in SAMPLE[1:]:
        assert head in part and text in part, (head, look)
    assert "見出し&lt;1&gt;" in part, ("字を逃がす", look)
    # PDF の釦のすぐ後ろ。遠くに置くと止まった時に見つからない
    assert page.index("PDF を開いて印刷する") < page.index('class="meta print-help"') < page.index("100% で刷り"), ("置き場", look)
    # どの紙でも同じ文
    assert help_part(get("?see=H-A&kind=tejun&v=1")) == part, ("手順の紙", look)
    assert help_part(get("?see=H-B&kind=sheet&v=1")) == part, ("ほかの紙", look)
    server.shutdown()

# 文の案（文面は本人の確認待ち）。案内は 3 つで、やさしい言葉（#317 の「刷る」は「印刷する」）
assert WORDS_SUMMARY == "印刷できない時は", WORDS_SUMMARY
assert [head for head, _ in WORDS] == ["大きさを 100% にするには", "物差しが 10cm でない時は", "プリンタが無い時は"], WORDS
for _, text in WORDS:
    assert "刷" not in text.replace("印刷", "") and text.endswith("。"), text
print("ok")
