"""学ぶ人に同じ値を 2 度打たせず、書いた値を頁に出さない（#138）。

なぜ: 説明で「書いた人」を打ち、次の版の欄で「採った人」をもう一度打っていた。
人の確認の記録の床（F9.human）は通したまま、値は説明の時に 1 回だけ書き、次の版はそれを引き継ぐ。
欄に入れて見せる形にしないのは、次に開いた別の人に見えるため（学ぶ人の頁に、採った人の名前を出さない線）。
"""
import json
import os
import pathlib
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

DATA = tempfile.mkdtemp()
os.environ["OMOCHAE_DATA"] = DATA
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(DATA, "api-usage.jsonl")

from omochae import loop  # noqa: E402
from web.play_server import serve  # noqa: E402

G = "NDL-1187053-R0000005-L"
server = serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"


def get(path):
    return urllib.request.urlopen(base + path).read().decode()


def post(path, data):
    r = urllib.request.Request(base + path, data=urllib.parse.urlencode(data).encode(), headers={"Origin": base})
    try:
        x = urllib.request.urlopen(r)
        return x.status, x.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def next_box(page):
    return page.split('action="/record/R-0001/next#next-R-0001"', 1)[1].split("</form>", 1)[0]


def adopted_by(version):
    return json.loads((loop.folder() / f"version-{G}-H-A-{version}.json").read_text(encoding="utf-8"))["adopted_by"]


WHO = "3 班の目印"  # 頁に出ない事を見るので、ほかの字と重ならない値にする
assert post(f"/toy/{G}/print", {"hypothesis": "H-A"})[0] == 200
assert post(f"/toy/{G}/record", {"hypothesis": "H-A", "result": "動いた"})[0] == 200
assert post("/record/R-0001/explain", {"text": "折りが固くて戻る", "next_idea": "厚さを変える", "by": WHO})[0] == 200

# 玩具の頁と手帖の両方で、次の版の欄に打つ欄が無く、説明で書いた値も頁に出ない
for where, page in (("玩具の頁", get(f"/toy/{G}")), ("手帖", get(f"/toy/{G}/techo"))):
    box = next_box(page)
    assert 'name="interpretation"' in box, where
    assert 'name="by"' not in box and "採った人" not in box, f"{where}: 次の版でもう一度打たせない"
    assert WHO not in page, f"{where}: 書いた値を次に開く別の人に見せない"

# 欄が無くても、説明の値が人の確認の記録に残る（F9.human の床を通る）
form = {"interpretation": "折りが固い", "param": "fold_count", "to": "26", "why": "開きを見る"}
assert post("/record/R-0001/next", form)[0] == 200 and loop.latest_version(G, "H-A") == 2
assert loop.interpretation("R-0001")["confirmed_by"] == WHO and adopted_by(2) == WHO
conf = {(c["hypothesis_id"], c["version"]): c["confirmations"] for c in loop.sheet_confirmations(G)}
assert conf[("H-A", 2)][-1]["by"] == WHO, conf

# 床は残っている: 空で送られると通らず、何も増えない（欄があった古い頁から送られた時）
code, page = post("/record/R-0001/next", {**form, "to": "24", "by": " "})
assert code == 422 and "確定した人の名前が無い" in page and loop.latest_version(G, "H-A") == 2
# 古い頁の欄から送られた値は、書いたとおりに受ける
assert post("/record/R-0001/next", {**form, "to": "24", "by": "4 班"})[0] == 200
assert loop.latest_version(G, "H-A") == 3 and adopted_by(3) == "4 班"
print("ok: 次の版は説明の値を引き継ぎ、頁に出さない")
