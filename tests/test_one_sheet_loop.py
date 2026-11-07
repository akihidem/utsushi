"""改善の輪を、玩具ごとに 1 枚のたたき台の形にする（本人の決定 11-05、J-032、#332）。本物の API は呼ばない。

ここの「1 枚」は玩具ごとの型紙の数で、作り方の印の one_sheet（紙一枚。紙だけで作れる事）とは別の物。

見る事（本人の方針「最新版が、次の人の型紙になる。古い版は消さない」と、採った新しい仮説の形）:
1. 話した字つきの記録から版 2 がたたき台に付き、次の人は版 2 を刷る。前の版の紙と記録は読める。記録は試した版の番号を持つ
2. 形の違う案を採ると、作る側の控えに入る。札に出ず、頁から刷れない。必須 2 種は命令からも刷らない。試作の玩具は命令から刷れる（道は閉じない）
3. 寸法の差だけの案を採ると、たたき台の次の版になる。控えは増えない。差は案を作った時の版から見て、今の版に重ねるので、前の版の直しは戻らない。
   案の字（Claude の字）は版の記録の別の欄に置き、頁に出さない
4. 寸法の差だけでも紙に乗らない案と、差の無い案は、作る側の控えに入る
5. 次の版はたたき台にだけ足す。ほかの仮説と自分の仮説の寸法の案は断る（版の記録だけ残り、紙が刷れない形を作らない）
6. たたき台は、案を採っても替わらない
7. 案を作る Claude に、たたき台の番号と今の版の寸法を渡す。ほかの仮説の記録で寸法の案を出すと、直させる
8. 全部の玩具で、版 1 の時に全部の寸法を書いた案は前の版の直しを戻さない。寸法の無い控えや字の寸法の控えがあっても、一覧と頁は開く
9. 渡された材料を読んで写す Claude でも、前の版の直しは戻らない（文に従うかに頼らない）。案を作っている途中で版が増えても、途中の直しは戻らない
"""
import contextlib
import io
import json
import os
import pathlib
import subprocess
import sys
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
from omochae.metrics import ALLOWED  # noqa: E402
from web.play_server import out_dir, serve  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
G = "NDL-1187053-R0000005-L"
# この試験は、たたき台に版を重ねる作り（話した字つきの記録 → 版 2・形の違う案は控え・寸法の差の案は次の版）を、前の組（goraigo-v10）の
# つまみの形の寸法で見る（値はその寸法で選んである）。今の組（goraigo-v14）の版の重ね方は tests/test_next_version_atomic.py ほかが見る
TEMPLATES["slider_fan"].SHEET_SET = TEMPLATES["slider_fan"].FROZEN_SET
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


# 1 つのブラウザとして動く（記録を残した画面の鍵の cookie を持つ。説明と字を足す口は、その画面にだけ開く）
JAR = urllib.request.HTTPCookieProcessor()
urllib.request.install_opener(urllib.request.build_opener(JAR))


def get(path):
    try:
        return urllib.request.urlopen(base + path, timeout=180).read().decode()
    except urllib.error.HTTPError as e:
        return e.read().decode()


def status_of(path):
    """道が開くかの番号だけ（中身は読まない）。"""
    try:
        return urllib.request.urlopen(base + path, timeout=180).status
    except urllib.error.HTTPError as e:
        return e.code


def post(path, form):
    req = urllib.request.Request(base + path, urllib.parse.urlencode(form).encode(), {"Origin": base, "Content-Type": "application/x-www-form-urlencoded"})
    try:
        return urllib.request.build_opener(NoRedirect, JAR).open(req, timeout=180).status
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
# 試した後の紙は 11-06 から刷らない（本人の決まり）。前の版で試した記録の紙は、残した /sheet の道で読める（窓には出さない）
assert "_after" not in window(get(f"/toy/{G}?see=H-A&kind=after&v=1")), "窓は型紙だけ"
assert status_of(f"/sheet/{G}/H-A_v1_after.pdf") == 200, "前の版で試した記録の紙も読める"
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

# 3. 寸法の差だけの案を採ると、たたき台の次の版になる。控えは増えない
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
assert [c["from"] for c in version["changes"] if c["param"] == "fold_count"] == [24]
# 案の字は版の記録の別の欄に置く。変更の理由の欄は頁の「型紙の改善の輪」に出るので、案の字も、本人の確認の外の字も入れない
assert all(c["why"] == "" for c in version["changes"]), version["changes"]
assert version["new_case"] == {"name": "折りをさらに減らす", "how_it_moves": "折りをさらに減らすの動かし方"}
assert loop._read(loop.folder() / f"proposal-{pid[2:]}.json")["new_hypothesis"]["name"] == "折りをさらに減らす", "案の字は採った案の記録に残る"
page = get(f"/toy/{G}")
assert "折りをさらに減らす" not in page and "採った案" not in page, "案の字を頁に出さない"
assert "24→22" in get(f"/loop/{G}").split('id="kaizen"', 1)[1], "変えた寸法は作る側の頁の輪の節に出す"  # （本人の答え 11-07 夕の Q5 で、玩具の頁の足の「型紙の改善の輪」は外し、作る側の様子の頁 /loop/<印> へ移した）
assert post(f"/toy/{G}/print", {"hypothesis": "H-A"}) == 303 and (out_dir(G) / "H-A_v3.pdf").exists(), "次の人はその版を刷る"
# 寸法の案（changes）と一緒に採ると、順に版を重ねる
pid = propose(G, rid, "H-A", changes=[{"param": "fold_count", "to": 21, "why": "少し減らす"}], new_hypothesis=new_case("低くする", {"fold_height": 42}))
made, failures = loop.adopt(pid, "作る側", ["fold_count"], True)
assert not failures and made == {"version": 5, "new_hypothesis_as_version": 5}, (made, failures)
assert loop.version_params(G, "H-A", 5)[0]["fold_count"] == 21 and loop.version_params(G, "H-A", 5)[0]["fold_height"] == 42
# 今の版を見て作った案なら、版 1 の値へ戻す案も、はっきり書いた差なので次の版になる
first = {**TEMPLATES["slider_fan"].DEFAULTS, **params_of(G, "H-A")}
assert first["fold_height"] != 42
pid = propose(G, rid, "H-A", new_hypothesis=new_case("扇の高さを元に戻す", {"fold_height": first["fold_height"]}))
made, failures = loop.adopt(pid, "作る側", accept_new=True)
assert not failures and made == {"version": 6, "new_hypothesis_as_version": 6}, (made, failures)
assert [c["from"] for c in loop.version_params(G, "H-A", 6)[1]["changes"]] == [42]
# 版 1 の時に全部の寸法を書いた案を採っても、前の版の直しは戻らない。案を作った時の版からの差だけを、今の版に重ねる
now, _ = loop.version_params(G, "H-A", 6)
pid = propose(G, rid, "H-A", based_on_version=1, new_hypothesis=new_case("幅を少し広げる", {**first, "fold_width": 9}))
made, failures = loop.adopt(pid, "作る側", accept_new=True)
assert not failures and made == {"version": 7, "new_hypothesis_as_version": 7}, (made, failures)
params, version = loop.version_params(G, "H-A", 7)
assert params == {**now, "fold_width": 9} and [c["param"] for c in version["changes"]] == ["fold_width"], (params, version["changes"])
# 版の番号を持たない前の形の案は、版 1 の時の案と読む（前は Claude に版 1 の寸法だけを渡していた）
pid = propose(G, rid, "H-A", new_hypothesis=new_case("前の形の案", {**first, "paper_thickness": 0.2}))
path = loop.folder() / f"proposal-{pid[2:]}.json"
saved = loop._read(path)
assert saved["based_on_version"] == 7, "案を作った時の版を持つ"
del saved["based_on_version"]
loop._write(path, saved)
made, failures = loop.adopt(pid, "作る側", accept_new=True)
assert not failures and made == {"version": 8, "new_hypothesis_as_version": 8}, (made, failures)
params, version = loop.version_params(G, "H-A", 8)
assert params == {**now, "fold_width": 9, "paper_thickness": 0.2} and [c["param"] for c in version["changes"]] == ["paper_thickness"]
# 案の差のうち、今の版ともう同じ値の物は変更に混ぜない
pid = propose(G, rid, "H-A", based_on_version=1, new_hypothesis=new_case("一部はもう直っている", {**first, "fold_count": params["fold_count"], "fold_height": 46}))
made, failures = loop.adopt(pid, "作る側", accept_new=True)
assert not failures and made == {"version": 9, "new_hypothesis_as_version": 9}, (made, failures)
assert [c["param"] for c in loop.version_params(G, "H-A", 9)[1]["changes"]] == ["fold_height"]

# 4. 版にならない案は、版を作らず、作る側の控えに入る（人が採った案を捨てない）
now, _ = loop.version_params(G, "H-A", loop.latest_version(G, "H-A"))
assert now["fold_height"] == 46 and first["fold_height"] != 46
# 下の「後の直しとぶつかる」の値は紙に乗る。乗らない値だと、ぶつかる守りを外しても控えに入り、見張りにならない
assert not loop.check_proposal({"record_ids": [rid], "hypothesis_id": "H-A", "changes": [{"param": "fold_height", "to": 44, "why": "試す"}]}, source(G))
for name, params, more in (("幅を広げすぎる（紙に乗らない）", {**now, "fold_width": 15}, {}),
                           ("読みだけ違う（差が無い）", dict(now), {}),
                           ("寸法を書いていない", None, {}),
                           ("字の寸法を混ぜる", {**now, "fold_count": "多め"}, {}),
                           ("変えてよい寸法の外", {**now, "pusher_height": 20}, {}),
                           ("雛形が違う", {"fold_height": 44}, {"template": "pivot_counterweight"}),
                           # 案を作った後に今の版で変わった寸法に触る案は、後の直しを黙って上書きしない
                           ("後の直しとぶつかる", {**first, "fold_height": 44}, {"based_on_version": 1}),
                           ("もう同じ値", {**first, "fold_count": now["fold_count"]}, {"based_on_version": 1}),
                           ("読めない版の案", {**now, "fold_width": 8.5}, {"based_on_version": 99}),
                           ("寸法が字", "多め", {}),
                           ("寸法が並び", [1, 2], {}),
                           ("雛形の無い案", {"fold_height": 44}, {"template": None}),
                           ("雛形に乗らない読み", {"fold_height": 44}, {"template_id": None})):
    based = {"based_on_version": more.pop("based_on_version")} if "based_on_version" in more else {}
    pid = propose(G, rid, "H-A", new_hypothesis=new_case(name, params, **more), **based)
    number = len(extras(G)) + 1
    made, failures = loop.adopt(pid, "作る側", accept_new=True)
    assert not failures and made == {"new_hypothesis": f"H-N{number}"} and loop.latest_version(G, "H-A") == 9, (name, made, failures)

# 5. 次の版はたたき台にだけ足す。ほかの仮説と自分の仮説の寸法の案は断る
other = confirmed(G, "H-C")
proposal = {"record_ids": [other], "hypothesis_id": "H-C", "changes": [{"param": "fold_count", "to": 24, "why": "試す"}], "next_to_try": {"why": "x", "what_to_measure": "y"}, "references": []}
pid, failures = loop.save_proposal(proposal, source(G), "human")
assert pid is None and {f.floor for f in failures} == {"F7.revision"}, failures
assert loop.adopted_versions(G, "H-C") == [] and "see=H-C&kind=sheet&v=2" not in get(f"/loop/{G}").split('id="kaizen"', 1)[1]
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
now, _ = loop.version_params(G, "H-A", 9)
assert sent["sheet"] == "H-A" and sent["sheet_version"] == 9 and sent["sheet_params"] == now, "たたき台の番号と今の版の寸法を渡す"
shown = {h["id"]: h["params"] for h in sent["hypotheses"]}
assert shown["H-A"] == now and shown["H-C"] == params_of(G, "H-C"), "一覧のたたき台の寸法も今の版。ほかの仮説は記録のまま"
assert "たたき台" in client.calls[0]["system"][0]["text"] and "作る側の控え" in client.calls[0]["system"][0]["text"]
assert "F7.revision" in json.dumps(client.calls[1]["messages"], ensure_ascii=False, default=str), "落ちた理由を読ませる"

# 今の版の寸法で書いた案は、今の版からの差だけが次の版になる。案を作った時の版は、Claude の返事でなく呼ぶ側が持つ
assert loop.save_explanation(rid, "作った人", "幅が広い", "幅を戻す") == []
client = Fake([([tool("submit_result", {"based_on_version": 1, "new_hypothesis": new_case("幅を戻す", {**now, "fold_width": 8.5}), "next_to_try": NEXT, "references": []}, "c")], "tool_use")])
pid, failures = loop_agents.draft_proposal(rid, source(G), client)
assert not failures, failures
assert loop._read(loop.folder() / f"proposal-{pid[2:]}.json")["based_on_version"] == 9
made, failures = loop.adopt(pid, "作る側", accept_new=True)
assert not failures and made == {"version": 10, "new_hypothesis_as_version": 10}, (made, failures)
assert [c["param"] for c in loop.version_params(G, "H-A", 10)[1]["changes"]] == ["fold_width"]

# 8. 寸法の無い控えや字の寸法の控えがあっても、一覧と頁は開く
rows = ways.table()
assert {r["hypothesis_id"] for r in rows if r["source_id"] == G} >= {"H-A", "H-N1"} and len({r["source_id"] for r in rows if r["sheet"]}) == 83
out = subprocess.run([sys.executable, "-m", "omochae.ways", "--json"], capture_output=True, text=True)
assert out.returncode == 0 and len(json.loads(out.stdout)) == len(rows), out.stderr[-300:]
for path in (f"/toy/{G}", f"/toy/{G}/techo", f"/toy/{G}/tsukuru", f"/en/toy/{G}", f"/zukan/{G}", "/toys", "/toys?paper=1", "/loop"):
    with urllib.request.urlopen(base + path, timeout=180) as r:
        assert r.status == 200, path
done = subprocess.run([sys.executable, "-m", "omochae.engine_bundle", "export", "--out", os.path.join(os.environ["OMOCHAE_DATA"], "bundle.json")], capture_output=True, text=True)
assert done.returncode == 0, done.stderr[-300:]

# 全部の玩具で: 前の版の直しがある時に、版 1 の時の案を採っても戻らない（5 雛形で実行して全部戻った形の見張り）
os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
kept = 0
for path in sorted((ROOT / "data/hypotheses").glob("*.json")):
    sid, sheet = path.stem, hypotheses.sheet_of(path.stem)
    template = hypotheses.load(sid).get("template", "slider_fan")
    whole = {**TEMPLATES[template].DEFAULTS, **sheet["params"]}
    names = [k for k in sorted(ALLOWED[template]) if type(whole.get(k)) in (int, float)]
    assert names, (sid, template)
    fixed = {**sheet["params"], names[0]: whole[names[0]] + 1}
    loop._write(loop.folder() / f"version-{sid}-{sheet['id']}-2.json", {"source_id": sid, "hypothesis_id": sheet["id"], "version": 2, "params": fixed, "changes": []})
    case = {"name": "x", "how_it_moves": "y"}
    assert loop._new_as_changes(sid, sheet["id"], {**case, "params": whole}, 1) == [], (sid, "版 1 のままの案は何も変えない")
    if len(names) > 1:
        changes = loop._new_as_changes(sid, sheet["id"], {**case, "params": {**whole, names[1]: whole[names[1]] + 1}}, 1)
        assert [c["param"] for c in changes] == [names[1]], (sid, changes)
        kept += 1
assert kept > 60, kept


# 9. 渡された材料を読んで写す Claude でも、前の版の直しは戻らない。文に従うかに頼らない（本物の Claude が文に従うかは確かめられない）
class Reading:
    """渡された材料から案の寸法を写す偽の Claude。during は返す前に動かす（案を作っている途中で版が増える形）。"""

    def __init__(self, copy, during=None):
        self.copy, self.during = copy, during
        self.beta = NS(messages=NS(create=self.create))

    def create(self, **kw):
        data = json.loads(kw["messages"][0]["content"].split("<data>\n", 1)[1].rsplit("\n</data>", 1)[0])
        if self.during:
            self.during()
        done = {"new_hypothesis": new_case("写した案", self.copy(data)), "next_to_try": NEXT, "references": []}
        return NS(content=[tool("submit_result", done, "r")], stop_reason="tool_use", usage=NS(input_tokens=10, output_tokens=5))


def entry(data):
    return next(h for h in data["hypotheses"] if h["id"] == data["sheet"])["params"]


def with_defaults(sid, params):
    return {**TEMPLATES[hypotheses.load(sid).get("template", "slider_fan")].DEFAULTS, **params}


os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
# 必須 2 種と 5 雛形（別の目の確かめで、版 1 の寸法を写すと直しが戻った 7 種）
for sid in (G, "NDL-1187053-R0000014-R", "NDL-1187053-R0000007-R", "NDL-1187053-R0000004-L", TRIAL, "NDL-1187053-R0000005-L-3", "NDL-1187053-R0000014-L"):
    sheet = hypotheses.sheet_of(sid)
    template = hypotheses.load(sid).get("template", "slider_fan")
    whole = {**TEMPLATES[template].DEFAULTS, **sheet["params"]}
    name = next(k for k in sorted(ALLOWED[template]) if type(whole.get(k)) in (int, float))
    fixed = {**sheet["params"], name: whole[name] + 1}
    loop._write(loop.folder() / f"version-{sid}-{sheet['id']}-2.json", {"source_id": sid, "hypothesis_id": sheet["id"], "version": 2, "params": fixed, "changes": []})
    reader = confirmed(sid, sheet["id"])
    assert loop.save_explanation(reader, "作った人", "説明", "次") == []
    for label, copy in (("今の版の寸法", lambda d: d["sheet_params"]),
                        ("既定と今の版の寸法", lambda d, s=sid: with_defaults(s, d["sheet_params"])),
                        ("一覧のたたき台の寸法", entry),
                        ("既定と一覧のたたき台の寸法", lambda d, s=sid: with_defaults(s, entry(d)))):
        pid, failures = loop_agents.draft_proposal(reader, source(sid), Reading(copy))
        assert not failures, (sid, label, failures)
        made, failures = loop.adopt(pid, "作る側", accept_new=True)
        assert not failures and "version" not in made and loop.latest_version(sid, sheet["id"]) == 2, (sid, label, made, failures)
        assert loop.version_params(sid, sheet["id"], 2)[0][name] == whole[name] + 1, (sid, label)


# 案を作っている途中で版が増えても、案を作り始めた時の版から見るので、途中の直しは戻らない
os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
start = {**params_of(G, "H-A"), "fold_count": 24}
loop._write(loop.folder() / f"version-{G}-H-A-2.json", {"source_id": G, "hypothesis_id": "H-A", "version": 2, "params": start, "changes": []})


def bump():
    loop._write(loop.folder() / f"version-{G}-H-A-3.json", {"source_id": G, "hypothesis_id": "H-A", "version": 3, "params": {**start, "fold_height": 44}, "changes": []})


reader = confirmed(G, "H-A")
assert loop.save_explanation(reader, "作った人", "説明", "次") == []
pid, failures = loop_agents.draft_proposal(reader, source(G), Reading(lambda d: {**d["sheet_params"], "paper_thickness": 0.2}, bump))
assert not failures, failures
assert loop._read(loop.folder() / f"proposal-{pid[2:]}.json")["based_on_version"] == 2, "案を作り始めた時の版を持つ"
made, failures = loop.adopt(pid, "作る側", accept_new=True)
assert not failures and made == {"version": 4, "new_hypothesis_as_version": 4}, (made, failures)
params = loop.version_params(G, "H-A", 4)[0]
assert params["fold_count"] == 24 and params["fold_height"] == 44 and params["paper_thickness"] == 0.2, params

server.shutdown()
print("ok 改善の輪はたたき台の 1 枚の形で回る。採った案は次の版か作る側の控えになり、札に出ない")
