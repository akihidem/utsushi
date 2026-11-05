"""改善の輪を、玩具ごとに 1 枚のたたき台の形にする（本人の決定 11-05、J-032、#332）。本物の API は呼ばない。

ここの「1 枚」は玩具ごとの型紙の数で、作り方の印の one_sheet（紙一枚。紙だけで作れる事）とは別の物。

見る事（本人の方針「最新版が、次の人の型紙になる。古い版は消さない」と、採った新しい仮説の形）:
1. 話した字つきの記録から版 2 がたたき台に付き、次の人は版 2 を刷る。前の版の紙と記録は読める。記録は試した版の番号を持つ
2. 形の違う案を採ると、作る側の控えに入る。札に出ず、頁から刷れない。必須 2 種は命令からも刷らない。試作の玩具は命令から刷れる（道は閉じない）
3. 寸法の差だけの案を採ると、たたき台の次の版になる。控えは増えない。案の字は採った案の記録に残る
4. 寸法の差だけでも紙に乗らない案と、差の無い案は、作る側の控えに入る
5. 次の版はたたき台にだけ足す。ほかの仮説と自分の仮説の寸法の案は断る（版の記録だけ残り、紙が刷れない形を作らない）
6. たたき台は、案を採っても替わらない
7. 案を作る Claude に、たたき台の番号を渡す。ほかの仮説の記録で寸法の案を出すと、直させる
"""
import contextlib
import io
import json
import os
import pathlib
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request
from types import SimpleNamespace as NS

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(os.environ["OMOCHAE_DATA"], "api-usage.jsonl")

from api import loop_agents  # noqa: E402
from omochae import hypotheses, loop, records, talk_log, ways  # noqa: E402
from omochae.compose import TEMPLATES  # noqa: E402
from web.play_server import out_dir, serve  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
G = "NDL-1187053-R0000005-L"
TRIAL = "NDL-1187053-R0000004-L-4"  # 形（form）の違う仮説を持つ試作の玩具
WHO = "abcd1234ef"
RESULTS = TEMPLATES["slider_fan"].RESULTS
server = serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a):
        return None


def source(sid):
    return json.loads((ROOT / "data/sources" / f"{sid}.json").read_text(encoding="utf-8"))


def get(path):
    try:
        return urllib.request.urlopen(base + path, timeout=180).read().decode()
    except urllib.error.HTTPError as e:
        return e.read().decode()


def post(path, form):
    req = urllib.request.Request(base + path, urllib.parse.urlencode(form).encode(), {"Origin": base, "Content-Type": "application/x-www-form-urlencoded"})
    try:
        return urllib.request.build_opener(NoRedirect).open(req, timeout=180).status
    except urllib.error.HTTPError as e:
        return e.code


def window(page):
    return page.split('id="win"', 1)[1].split("</section>", 1)[0]


def params_of(sid, hid):
    return next(h for h in hypotheses.load(sid)["hypotheses"] if h["id"] == hid)["params"]


def confirmed(sid, hid):
    rid, failures = records.add({"source_id": sid, "hypothesis_id": hid, "sheet_version": 1, "result": records.results_for(sid)[1], "fixes": [], "note": "試した"})
    assert not failures, failures
    assert loop.confirm_interpretation(rid, "作る側", {"human_text": "読み"}) == []
    return rid


def new_case(name, params, **more):
    return {"name": name, "how_it_moves": f"{name}の動かし方", "evidence": [], "against": ["未確認"], "to_measure": "動くか", "params": params, **more}


def propose(sid, rid, hid, **more):
    pid, failures = loop.save_proposal({"record_ids": [rid], "hypothesis_id": hid, "next_to_try": {"why": "確かめる", "what_to_measure": "動くか"}, "references": [], **more}, source(sid), "human")
    assert not failures, [f.line() for f in failures]
    return pid


def extras(sid):
    return [h["id"] for h in hypotheses.load(sid)["hypotheses"] if h["id"].startswith("H-N")]


# 1. 話した字つきの記録から版 2 がたたき台に付く。最新版が次の人の型紙で、古い版は消さない
assert post(f"/toy/{G}/print", {"hypothesis": "H-A", "who": WHO}) == 303
assert talk_log.add(G, "craft", "手順3で折り目を二回なぞると開きやすい", hypothesis_id="H-A", sheet_version=1, step=3, who=WHO)[1] == []
assert post(f"/toy/{G}/record", {"hypothesis": "H-A", "result": RESULTS[1], "who": WHO}) in (200, 303)
first = records.all_records(G)[0]["id"]
assert "二回なぞると" in loop.material_text(first), "話した字が輪の材料に入る"
assert post(f"/record/{first}/explain", {"text": "折りが固い", "next_idea": "折りを減らす", "by": "作った人"}) in (200, 303)
assert post(f"/record/{first}/next", {"interpretation": "折りが固い", "param": "fold_count", "to": "24", "why": "開きやすく", "by": "作る側"}) in (200, 303)
assert loop.adopted_versions(G, "H-A") == [2]
assert f"/sheet/{G}/H-A_v2.png" in window(get(f"/toy/{G}")), "窓の最初は一番新しい版"
assert f"/sheet/{G}/H-A_v1.png" in window(get(f"/toy/{G}?see=H-A&kind=sheet&v=1")), "前の版の紙は読める"
assert post(f"/toy/{G}/print", {"hypothesis": "H-A"}) == 303
assert (out_dir(G) / "H-A_v2.pdf").exists() and not list(out_dir(G).glob("H-A_v3*")), "次の人が刷ると一番新しい版が出て、版は増えない"
assert post(f"/toy/{G}/record", {"hypothesis": "H-A", "result": RESULTS[0]}) in (200, 303)
assert [r.get("sheet_version") for r in records.all_records(G)] == [1, 2], "記録は試した版の番号を持つ"
assert f"/sheet/{G}/H-A_v1_after.png" in window(get(f"/toy/{G}?see=H-A&kind=after&v=1")), "前の版で試した記録の紙も読める"
assert first in get(f"/toy/{G}")

# 2. 形の違う案（雛形の寸法の差で言えない案）を採ると、作る側の控えに入る。札に出さない
rid = confirmed(G, "H-A")
pid = propose(G, rid, "H-A", new_hypothesis=new_case("柄で押す", params_of(G, "H-C")))
made, failures = loop.adopt(pid, "作る側", accept_new=True)
assert not failures and made == {"new_hypothesis": "H-N1"}, (made, failures)
page = get(f"/toy/{G}")
assert 'value="H-N1"' not in page and "柄で押す" not in page, "控えは札に出さない"
assert post(f"/toy/{G}/print", {"hypothesis": "H-N1"}) == 422 and not list(out_dir(G).glob("H-N1*"))
stem = str(pathlib.Path(os.environ["OMOCHAE_DATA"]) / "by-command")
err = io.StringIO()
with contextlib.redirect_stderr(err):
    assert hypotheses.print_sheet(G, "H-N1", stem) == 3, "必須 2 種は、命令からも控えを刷らない"
assert "F9.human" in err.getvalue() and not pathlib.Path(f"{stem}.pdf").exists()
row = next(r for r in ways.table() if r["source_id"] == G and r["hypothesis_id"] == "H-N1")
assert row["sheet"] is False and row["reading_of"] == "H-A", "控えも一覧の行には残る"
assert rid in page, "案のもとの記録は読める"
# 試作の玩具は、作る側が命令から控えを刷れる（道は閉じない）。頁には出さない
trial_rid = confirmed(TRIAL, "H-A")
pid = propose(TRIAL, trial_rid, "H-A", new_hypothesis=new_case("浮かべる形", params_of(TRIAL, "H-B")))
assert loop.adopt(pid, "作る側", accept_new=True)[0] == {"new_hypothesis": "H-N1"}
assert hypotheses.print_sheet(TRIAL, "H-N1", f"{stem}-trial") == 0 and pathlib.Path(f"{stem}-trial.pdf").exists()
assert 'value="H-N1"' not in get(f"/toy/{TRIAL}") and post(f"/toy/{TRIAL}/print", {"hypothesis": "H-N1"}) == 422

# 3. 寸法の差だけの案を採ると、たたき台の次の版になる。今の版からの差で見る。控えは増えない
now, _ = loop.version_params(G, "H-A", loop.latest_version(G, "H-A"))
assert now["fold_count"] == 24
pid = propose(G, rid, "H-A", new_hypothesis=new_case("折りをさらに減らす", {**now, "fold_count": 22, "fold_height": 44}))
before = extras(G)
made, failures = loop.adopt(pid, "作る側", accept_new=True)
assert not failures and made == {"version": 3, "new_hypothesis_as_version": 3}, (made, failures)
assert extras(G) == before and loop.adopted_versions(G, "H-A") == [2, 3]
params, version = loop.version_params(G, "H-A", 3)
assert params["fold_count"] == 22 and params["fold_height"] == 44 and params["push_part"] == "tab"
assert version["record_ids"] == [rid] and {c["param"] for c in version["changes"]} == {"fold_count", "fold_height"}
assert all("折りをさらに減らす" in c["why"] for c in version["changes"]) and [c["from"] for c in version["changes"] if c["param"] == "fold_count"] == [24]
assert loop._read(loop.folder() / f"proposal-{pid[2:]}.json")["new_hypothesis"]["name"] == "折りをさらに減らす", "案の字は採った案の記録に残る"
assert post(f"/toy/{G}/print", {"hypothesis": "H-A"}) == 303 and (out_dir(G) / "H-A_v3.pdf").exists(), "次の人はその版を刷る"
# 寸法の案（changes）と一緒に採ると、順に版を重ねる
pid = propose(G, rid, "H-A", changes=[{"param": "fold_count", "to": 21, "why": "少し減らす"}], new_hypothesis=new_case("低くする", {"fold_height": 42}))
made, failures = loop.adopt(pid, "作る側", ["fold_count"], True)
assert not failures and made == {"version": 5, "new_hypothesis_as_version": 5}, (made, failures)
assert loop.version_params(G, "H-A", 5)[0]["fold_count"] == 21 and loop.version_params(G, "H-A", 5)[0]["fold_height"] == 42
# 差は版 1 からでなく今の版から見る。版 1 の値へ戻す案も、今の版から見れば差があるので次の版になる
first_height = {**TEMPLATES["slider_fan"].DEFAULTS, **params_of(G, "H-A")}["fold_height"]
assert first_height != 42
pid = propose(G, rid, "H-A", new_hypothesis=new_case("扇の高さを元に戻す", {"fold_height": first_height}))
made, failures = loop.adopt(pid, "作る側", accept_new=True)
assert not failures and made == {"version": 6, "new_hypothesis_as_version": 6}, (made, failures)
assert [c["from"] for c in loop.version_params(G, "H-A", 6)[1]["changes"]] == [42]

# 4. 版にならない案は、版を作らず、作る側の控えに入る（人が採った案を捨てない）
now, _ = loop.version_params(G, "H-A", loop.latest_version(G, "H-A"))
for number, name, params, more in ((2, "幅を広げすぎる（紙に乗らない）", {**now, "fold_width": 15}, {}),
                                   (3, "読みだけ違う（差が無い）", dict(now), {}),
                                   (4, "寸法を書いていない", None, {}),
                                   (5, "字の寸法を混ぜる", {**now, "fold_count": "多め"}, {}),
                                   (6, "変えてよい寸法の外", {**now, "pusher_height": 20}, {}),
                                   (7, "雛形が違う", {"fold_height": 44}, {"template": "pivot_counterweight"})):
    pid = propose(G, rid, "H-A", new_hypothesis=new_case(name, params, **more))
    made, failures = loop.adopt(pid, "作る側", accept_new=True)
    assert not failures and made == {"new_hypothesis": f"H-N{number}"} and loop.latest_version(G, "H-A") == 6, (name, made, failures)

# 5. 次の版はたたき台にだけ足す。ほかの仮説と自分の仮説の寸法の案は断る
other = confirmed(G, "H-C")
proposal = {"record_ids": [other], "hypothesis_id": "H-C", "changes": [{"param": "fold_count", "to": 24, "why": "試す"}], "next_to_try": {"why": "x", "what_to_measure": "y"}, "references": []}
pid, failures = loop.save_proposal(proposal, source(G), "human")
assert pid is None and {f.floor for f in failures} == {"F7.revision"}, failures
assert loop.adopted_versions(G, "H-C") == [] and "see=H-C&kind=sheet&v=2" not in get(f"/toy/{G}").split('id="kaizen"', 1)[1]
mine, _ = hypotheses.save_own(G, "自分の案", "引くと開く", "図の折り目", dict(params_of(G, "H-A")))
own_rid = confirmed(G, mine["id"])
pid, failures = loop.save_proposal({**proposal, "record_ids": [own_rid], "hypothesis_id": mine["id"]}, source(G), "human")
assert pid is None and {f.floor for f in failures} == {"F7.revision"}, failures
# ほかの仮説の記録を根拠に、たたき台の寸法を変える案は通る（R-0002「どちらの仮説も、内側の筒の土台があると良い」の形）
assert propose(G, other, "H-A", changes=[{"param": "fold_count", "to": 20, "why": "H-C の記録から"}])

# 6. たたき台は、案を採っても替わらない。替えるのは本人が決めた時に、記録の欄を直す時だけ
assert hypotheses.sheet_of(G)["id"] == "H-A" and hypotheses.sheet_of(TRIAL)["id"] == "H-A"
assert json.loads((ROOT / "data/hypotheses" / f"{G}.json").read_text(encoding="utf-8"))["sheet"] == "H-A"


# 7. 案を作る Claude に、たたき台の番号を渡す。ほかの仮説の記録で寸法の案を出すと、直させる
def tool(name, data, i):
    return NS(type="tool_use", name=name, input=data, id=f"{i}-{name}")


class Fake:
    def __init__(self, script):
        self.script, self.calls = list(script), []
        self.beta = NS(messages=NS(create=self.create))

    def create(self, **kw):
        self.calls.append(kw)
        content, stop = self.script.pop(0)
        return NS(content=content, stop_reason=stop, usage=NS(input_tokens=10, output_tokens=5))


assert loop.save_explanation(other, "作った人", "筒が足りない", "土台を足す") == []
NEXT = {"why": "確かめる", "what_to_measure": "動くか"}
client = Fake([([tool("submit_result", {"changes": [{"param": "fold_count", "to": 24, "why": "試す"}], "next_to_try": NEXT, "references": []}, "a")], "tool_use"),
               ([tool("submit_result", {"next_to_try": NEXT, "references": []}, "b")], "tool_use")])
pid, failures = loop_agents.draft_proposal(other, source(G), client)
assert not failures and len(client.calls) == 2, (failures, len(client.calls))
sent = json.loads(client.calls[0]["messages"][0]["content"].split("<data>\n", 1)[1].rsplit("\n</data>", 1)[0])
assert sent["sheet"] == "H-A", "たたき台の番号を渡す"
assert "たたき台" in client.calls[0]["system"][0]["text"] and "作る側の控え" in client.calls[0]["system"][0]["text"]
assert "F7.revision" in json.dumps(client.calls[1]["messages"], ensure_ascii=False, default=str), "落ちた理由を読ませる"

server.shutdown()
print("ok 改善の輪はたたき台の 1 枚の形で回る。採った案は次の版か作る側の控えになり、札に出ない")
