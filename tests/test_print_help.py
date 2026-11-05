"""型紙の窓の PDF の釦のすぐ下に、印刷で止まった時の案内を 1 つ置く（#297）。

なぜ: 窓の説明は「100% で刷り」だけで、設定の場所も、10cm でない時も、プリンタが無い時も画面に無かった。序の頁に置くと、止まった時に見つからない。
details なので JS なしで開く。文は玩具にも仮説にもよらない（型紙は玩具ごとに 1 枚にする決定 #332 で、仮説ごとの案内は要らなくなる）。
文の表が空の時は何も出さない。文面を本人が確かめるまで、仕組みだけを main に入れられるようにするため。
"""
import json
import os
import re
import tempfile
import threading
import urllib.parse
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(os.environ["OMOCHAE_DATA"], "api-usage.jsonl")

from omochae import hypotheses  # noqa: E402
from web import toy  # noqa: E402
from web.play_server import serve  # noqa: E402

G = "NDL-1187053-R0000005-L"
# ほかの玩具の紙でも同じ文か見る。型紙は玩具ごとに 1 枚（#332）で、必須 2 種の今の組はたたき台しか刷れないので、仮説でなく玩具を替える
T = next(p.stem for p in sorted((hypotheses.ROOT / "data/hypotheses").glob("*.json")) if json.loads(p.read_text(encoding="utf-8")).get("stage") == "試作")
SHEET = {sid: hypotheses.sheet_of(sid)["id"] for sid in (G, T)}
# 本人が採った文（11-05）。一字も変えずに頁へ出す。変える時は本人の確認を通す
ADOPTED_SUMMARY = "印刷できない時は"
ADOPTED = (
    ("大きさを 100% にするには", "印刷の画面で、倍率を 100% にします。「用紙に合わせる」を外すと、大きさがそのままになります。画面の言葉は、機械によってちがいます。"),
    ("物差しが 10cm でない時は", "倍率が 100% になっているか、もう一度見ます。直したら、印刷し直します。それでも 10cm にならない時は、そのまま作ってもだいじょうぶです。"),
    ("プリンタが無い時は", "学校の先生や家の人に、印刷をたのみましょう。コンビニの印刷機で印刷できる事もあります。その時も倍率を 100% にします。"),
)
WORDS = toy.PRINT_HELP_SUMMARY, toy.PRINT_HELP  # 試験が表を入れ替える前の、本物の文
SAMPLE = (("見出し<1>", "文の 1"), ("見出し 2", "文の 2"), ("見出し 3", "文の 3"))


def help_part(page):
    found = re.findall(r'<details class="[^"]*print-help">.*?</details>', page, re.S)
    assert len(found) <= 1, ("案内は 1 つ", len(found))
    return found[0] if found else ""


printed = False
for look in ("tenji", "zine"):
    server = serve(0, look=look)
    base = f"http://127.0.0.1:{server.server_address[1]}"
    threading.Thread(target=server.serve_forever, daemon=True).start()
    if not printed:
        for sid, hid in SHEET.items():
            data = urllib.parse.urlencode({"hypothesis": hid}).encode()
            urllib.request.urlopen(urllib.request.Request(f"{base}/toy/{sid}/print", data=data, headers={"Origin": base}), timeout=120)
        printed = True
    get = lambda q, sid=G: urllib.request.urlopen(f"{base}/toy/{sid}?see={SHEET[sid]}&v=1&{q}", timeout=60).read().decode()  # noqa: E731

    # 文の表が空なら、窓に何も足さない
    toy.PRINT_HELP_SUMMARY, toy.PRINT_HELP = "", ()
    assert help_part(get("kind=sheet")) == "", ("空の時は出さない", look)

    toy.PRINT_HELP_SUMMARY, toy.PRINT_HELP = "止まった時", SAMPLE
    page = get("kind=sheet")
    part = help_part(page)
    assert part, ("案内が無い", look)
    # 押す前は閉じていて、1 回押せば全部読める。JS に頼らない
    assert "<summary>止まった時</summary>" in part and "<script" not in part and " on" not in part.split(">")[0]
    for head, text in SAMPLE[1:]:
        assert head in part and text in part, (head, look)
    assert "見出し&lt;1&gt;" in part, ("字を逃がす", look)
    # プリンタの前で小学生も読む文なので、本文と同じ字の大きさにする（.meta の 12px にしない）。窓の横の欄は 14px なので、案内にだけ指定する
    assert part.startswith('<details class="print-help">'), ("小さい字の class", look, part[:60])
    body_px = re.search(r"body\{margin:0[^}]*?font-size:(\d+)px", page).group(1)
    assert f".win .side .print-help{{font-size:{body_px}px" in page, ("案内の字が本文より小さい", look, body_px)
    # PDF の釦のすぐ後ろ。遠くに置くと止まった時に見つからない
    assert page.index("PDF を開いて印刷する") < page.index('print-help">') < page.index("100% で刷り"), ("置き場", look)
    # どの紙でも同じ文
    assert help_part(get("kind=tejun")) == part, ("手順の紙", look)
    assert help_part(get("kind=sheet", T)) == part, ("ほかの玩具", look)

    # 本物の文が、採った字のまま頁に出る
    toy.PRINT_HELP_SUMMARY, toy.PRINT_HELP = WORDS
    part = help_part(get("kind=sheet"))
    assert f"<summary>{ADOPTED_SUMMARY}</summary>" in part, ("見出し", look)
    for head, text in ADOPTED:
        assert f"<b>{head}</b><br>{text}</p>" in part, (head, look)
    assert part.count("<p>") == len(ADOPTED), ("案内の数", look)
    server.shutdown()
print("ok")
