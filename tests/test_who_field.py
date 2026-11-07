"""次の版の欄は採る人が自分で打ち、前の人の値を欄にも頁にも出さない（#138）。

なぜ: 別の人が次の版を作る事がある。説明の値で埋めると、採った人と確定した人の記録が事実と違いうる（J-026 の「採るのは人」、F9.human）。
前の値を欄に入れておくと、次に開いた別の人に見える。空の欄で足りる。同じ機器でブラウザが前の人の値を候補に出さないよう、autocomplete も切る。
"""
import json
import os
import re
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

DATA = tempfile.mkdtemp()
os.environ["OMOCHAE_DATA"] = DATA
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(DATA, "api-usage.jsonl")

from omochae import hypotheses  # noqa: E402
from omochae import loop  # noqa: E402
from web.play_server import serve  # noqa: E402

G = "NDL-1187053-R0000005-L"
# 御来迎のたたき台は組ごと（今の組 goraigo-v14 は H-C・記録の欄 sheet_by_set）。今の組で刷れるのはたたき台の紙だけ
GS = hypotheses.sheet_of(G)["id"]
server = serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"


class Browser:
    """1 つのブラウザ。記録を残した画面の鍵（cookie）を持つ。
    なぜ分けるか: 説明の欄は記録を残した画面にだけ出る（records.mine）。前の人の値が「次に開いた別の人」に見えないかは、
    鍵を持たない別のブラウザで見るのが事実に近い。"""

    def __init__(self):
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())

    def get(self, path):
        with self.op.open(base + path) as x:
            return x.read().decode()

    def post(self, path, data):
        r = urllib.request.Request(base + path, data=urllib.parse.urlencode(data).encode(), headers={"Origin": base})
        try:
            with self.op.open(r) as x:
                return x.status, x.read().decode()
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode()


maker, other = Browser(), Browser()
post = maker.post


def box(page, rid, act):
    return page.split(f'action="/record/{rid}/{act}#', 1)[1].split("</form>", 1)[0]


def who_field(form):
    found = re.search(r'<input [^>]*name="by"[^>]*>', form)
    assert found, "打つ欄が要る"
    return found.group(0)


def adopted_by(version):
    return json.loads((loop.folder() / f"version-{G}-{GS}-{version}.json").read_text(encoding="utf-8"))["adopted_by"]


# 頁に出ない事を見るので、ほかの字と重ならない値にする
WHO, ADOPTER = "3 班の目印", "4 班の目印"
assert post(f"/toy/{G}/print", {"hypothesis": GS})[0] == 200  # 刷れるのは今の組のたたき台だけ
assert post(f"/toy/{G}/record", {"hypothesis": GS, "result": "動いた"})[0] == 200
# 手帖の説明と次の版の欄は、作り直した手帖では記録の頁にある（#87）
pages = lambda b=maker: (("玩具の頁", b.get(f"/toy/{G}")), ("手帖の記録の頁", b.get(f"/toy/{G}/techo/kiroku")))

assert post("/record/R-0001/explain", {"text": "折りが固くて戻る", "next_idea": "厚さを変える", "by": WHO})[0] == 200

# 次の版の欄に、採る人が打つ空の欄がある。説明で書いた値は、次に開いた別の人の欄にも頁にも出ない
for where, page in pages(other):
    field = who_field(box(page, "R-0001", "next"))
    assert "value=" not in field and "required" in field and 'autocomplete="off"' in field, (where, field)
    assert WHO not in page, f"{where}: 前の人の値を、次に開いた別の人に見せない"

# 欄が空なら、床が止める。説明の値で埋めない
form = {"interpretation": "折りが固い", "param": "fold_count", "to": "45", "why": "開きを見る"}  # v14 の寸法（折り 44）で通る値
for sent in (form, {**form, "by": ""}, {**form, "by": " "}):
    code, page = post("/record/R-0001/next", sent)
    assert code == 422 and "確定した人の名前が無い" in page and WHO not in page, (code, sent)
    assert loop.latest_version(G, GS) == 1, "説明の値で埋めて次の版を作らない"
assert (loop.interpretation("R-0001") or {}).get("status") != "confirmed", "床で止まった時は、確定の記録も残さない"

# 記録には、説明を書いた人でなく、次の版の欄で打った人が残る（別の人が作っても事実のとおり）
assert post("/record/R-0001/next", {**form, "by": ADOPTER})[0] == 200 and loop.latest_version(G, GS) == 2
assert loop.interpretation("R-0001")["confirmed_by"] == ADOPTER and adopted_by(2) == ADOPTER
conf = {(c["hypothesis_id"], c["version"]): c["confirmations"] for c in loop.sheet_confirmations(G)}
assert conf[(GS, 2)][-1]["by"] == ADOPTER, conf

# 通らなかった時に打った値が戻るのは、送った本人への返事だけ。次に開く人の頁には出ない
code, page = post("/record/R-0001/next", {**form, "to": "abc", "by": ADOPTER})
assert code == 422 and f'value="{ADOPTER}"' in page, code
for where, page in pages(other):
    field = who_field(box(page, "R-0001", "next"))
    assert "value=" not in field and ADOPTER not in page and WHO not in page, where

# 説明の欄にも、前の人の値を候補に出さない印がある（説明の欄は、記録を残した画面にだけ出る）
assert post(f"/toy/{G}/record", {"hypothesis": GS, "result": "動いた"})[0] == 200
for where, page in pages(maker):
    assert 'autocomplete="off"' in who_field(box(page, "R-0002", "explain")), where
print("ok: 次の版の欄は採る人が打ち、前の人の値を出さない")
