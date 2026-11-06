"""説明の欄の「書いた人」は、書かなくても送れる（本人の決定 11-06。公開の前の点検の一覧の 5）。

なぜ: 書いた人は必須で、手帖の「名前や連絡先は書かないでください」と食い違っていた。字は今のまま、欄を任意にする。
空の時は記録に空のまま残す（空の時に入れる、今ある決まった字は無い）。
「人の説明が先」の床（説明のファイルがある事）と、次の版・Claude の読みは、空の書いた人で止まらない。合言葉あり・なしの両方で見る。
"""
import json
import os
import re
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request
from types import SimpleNamespace as NS

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(os.environ["OMOCHAE_DATA"], "api-usage.jsonl")

from api import loop_agents  # noqa: E402
from omochae import gallery, hypotheses, loop, records  # noqa: E402
from omochae.compose import TEMPLATES  # noqa: E402
from web.play_server import serve  # noqa: E402

G = "NDL-1187053-R0000005-L"
SOURCE = json.loads((hypotheses.ROOT / "data/sources" / f"{G}.json").read_text(encoding="utf-8"))


class Browser:
    """1 つのブラウザ。記録を残した画面の鍵（cookie）を持つ。"""

    def __init__(self, base):
        self.base = base
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())

    def call(self, path, data=None):
        r = urllib.request.Request(self.base + path, data=urllib.parse.urlencode(data).encode() if data is not None else None, headers={"Origin": self.base})
        try:
            with self.op.open(r) as res:
                return res.status, res.read().decode()
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode()


class Fake:
    """Claude の代わり。読みの案を 1 つ返す。"""

    def __init__(self, answer):
        self.answer = answer
        self.beta = NS(messages=NS(create=self.create))

    def create(self, **kw):
        return NS(content=[NS(type="tool_use", name="submit_result", input=self.answer, id="t")], stop_reason="tool_use", usage=NS(input_tokens=10, output_tokens=5))


def by_input(page, action):
    """その送り先のフォームの、書いた人の欄の字。"""
    form = re.search(rf'<form[^>]*action="{re.escape(action)}[^"]*"[^>]*>(.*?)</form>', page, re.S)
    assert form, action
    return re.search(r'<input[^>]*name="by"[^>]*>', form.group(1)).group(0), re.search(r'<input[^>]*name="next_idea"[^>]*>', form.group(1)).group(0)


def a_change(rid):
    """この記録から作れる次の版の寸法の変え方を 1 つ探す。"""
    tpl = hypotheses.load(G).get("template", "slider_fan")
    hid = hypotheses.sheet_of(G)["id"]
    now = {**TEMPLATES[tpl].DEFAULTS, **(loop.version_params(G, hid, loop.latest_version(G, hid))[0] or {})}
    for k in sorted(loop.ALLOWED[tpl]):
        if isinstance(now.get(k), (int, float)) and not isinstance(now.get(k), bool):
            for d in (1, -1, 0.5):
                if not loop.check_proposal({"record_ids": [rid], "hypothesis_id": hid, "changes": [{"param": k, "to": float(now[k]) + d, "why": "x"}]}, SOURCE, will_confirm=[rid]):
                    return k, float(now[k]) + d
    raise AssertionError("変えられる寸法が無い")


def explain_without_name(public):
    server = serve(0, public_open=public)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    b = Browser(f"http://127.0.0.1:{server.server_address[1]}")
    assert b.call(f"/toy/{G}/print", {"hypothesis": "H-A"})[0] == 200
    st, body = b.call(f"/toy/{G}/record-json", {"hypothesis": "H-A", "result": "動いた"})
    rid = json.loads(body)["id"]
    if not public:
        # 欄: 書いた人は任意。説明と次の思いつきは今までどおり要る
        for path in (f"/toy/{G}", f"/toy/{G}/techo"):
            by, nxt = by_input(b.call(path)[1], f"/record/{rid}/explain")
            assert "required" not in by and "required" in nxt, (path, by, nxt)
    st, page = b.call(f"/record/{rid}/explain", {"text": "筒が固かった", "next_idea": "幅を変える", "by": ""})
    assert st == 200 and "説明を残しました" in page, (public, st, page[-300:])
    told = loop.explanation(rid)
    assert told and told["by"] == "" and told["text"] == "筒が固かった" and told["next_idea"] == "幅を変える", told
    server.shutdown()
    return b, rid


# 合言葉なしの場でも、書いた人なしで説明を残せる
explain_without_name(True)

# 合言葉付きの場: 説明を残し、人の説明が先の床を通って、Claude の読みと次の版まで進む
b, rid = explain_without_name(False)
assert loop.explanation(rid) is not None, "人の説明が先の床（説明のファイルがある事）"
result, failures = loop_agents.draft_interpretation(rid, client=Fake({"observed": ["筒が固くて開きが遅い"], "causes": [], "unknown": []}))
assert not failures and loop.interpretation(rid)["content"]["observed"] == ["筒が固くて開きが遅い"], failures
server = serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
b.base = f"http://127.0.0.1:{server.server_address[1]}"
k, to = a_change(rid)
st, page = b.call(f"/record/{rid}/next", {"param": k, "to": str(to), "why": "固さを減らす", "by": "採った人", "interpretation": "筒が固い"})
assert st == 200 and "紙を作りました" in page, (st, page[-300:])
server.shutdown()

# 書いた人の無い説明は、札に空の括弧を出さない
rec = next(r for r in records.all_records(G) if r["id"] == rid)
card = gallery.card(rec, hypotheses.load(G))
assert "（）" not in card and "<b>説明</b>: 筒が固かった" in card, card[:400]
print("ok: 説明の書いた人は、書かなくても送れる")
