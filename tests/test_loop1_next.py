"""ループ1（Issue #335）の続き: 自分の紙（OWN-n）の記録から作る次の版は、たたき台へ向ける。根拠は OWN-n の記録のまま。

なぜ: 型紙は玩具ごとに 1 枚（J-032）。ループ1 を通った人の工夫が、ループ2（型紙の改善）に届くように。OWN-n に版を足しても紙は刷られず、次の人の型紙にもならない。
見る線:
- 画面の欄・端末の propose・Claude の道の既定が、そろってたたき台へ向く。OWN-n へ版を足す案は床で断る。
- 版の根拠は OWN-n の記録のまま（紙に番号が刷られ、取り下げは根拠を守って断る）。版が足されると、次の人の元の寸法になる。
- 試した後の紙は話した字が刷られないので、記録があれば別の人にも開く（ほかの紙は開かない）。合言葉なしの場では開かない。
- 改善の輪の節と作る側の数（kaizen.pending）も、同じ向く先で数える。札に欄が出る記録と、節に出る記録を食い違わせない。
- 型紙なしの紙は刷った組を残さない（紙の組の報告に数えない）。次の版の欄も出さない（組の報告に数えない記録で、たたき台の寸法を変えられる形は筋が通らないため）。
- たたき台が未刷の場でも、手帖で本人の紙を選べる。
"""
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request
from types import SimpleNamespace as NS

DATA = tempfile.mkdtemp()
os.environ["OMOCHAE_DATA"] = DATA
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(DATA, "api-usage.jsonl")  # 本物の台帳に書かない（#151）

from api import loop_agents, words  # noqa: E402
from omochae import engine_bundle, hypotheses, loop, records, talk_log  # noqa: E402
from omochae.compose import TEMPLATES, compose  # noqa: E402
from web import kaizen  # noqa: E402
from web.play_server import out_dir, serve  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
G = "NDL-1187053-R0000005-L"
SOURCE = json.loads((ROOT / "data/sources" / f"{G}.json").read_text(encoding="utf-8"))
SHEET = hypotheses.sheet_of(G)["id"]
SET = TEMPLATES["slider_fan"].SHEET_SET
server = serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


opener = urllib.request.build_opener(NoRedirect)


def send(path, data=None, cookie="", to=None):
    to = to or base
    headers = {"Content-Type": "application/x-www-form-urlencoded", "Origin": to}
    if cookie:
        headers["Cookie"] = cookie
    req = urllib.request.Request(to + path, data=urllib.parse.urlencode(data).encode() if data is not None else None, method="POST" if data is not None else "GET", headers=headers)
    try:
        r = opener.open(req)
    except urllib.error.HTTPError as e:  # 飛び先を追わないので、303 もここへ来る
        r = e
    return getattr(r, "code", r.status), r.read(), r.headers


def flat_pdf(path):
    return "".join(subprocess.run(["pdftotext", str(path), "-"], capture_output=True, text=True).stdout.split())


def made(who, text, changed=None, not_fit=None):
    """話す → 頼む → 作る側が書く → この紙にする。Returns (OWN の番号, 鍵)。"""
    assert send(f"/toy/{G}/talk", {"scene": "think", "hypothesis": SHEET, "text": text, "who": who})[0] == 303
    code, _, h = send(f"/toy/{G}/think-sheet", {"who": who})
    assert code == 303, code
    key = h["Set-Cookie"].split(";")[0]
    token = key.split("=", 1)[1]
    w = words.by_token(G, token)
    assert not words.fill_think(w["id"], words.think_result(w["base_params"], changed, not_fit), "作る側")[1]
    assert send(f"/toy/{G}/think-ok", {"t": token}, cookie=key)[0] == 303
    return words.by_token(G, token)["own_id"], key


def recorded(who, oid, key, craft=None):
    """工夫を話して記録を残し、説明を足す。Returns 記録の番号。"""
    if craft:
        assert send(f"/toy/{G}/talk", {"scene": "craft", "hypothesis": oid, "sheet_version": 1, "step": 1, "text": craft, "who": who}, cookie=key)[0] == 200
    code, _, sent = send(f"/toy/{G}/record", {"hypothesis": oid, "sheet_version": 1, "result": "動いた", "who": who}, cookie=key)
    assert code == 303
    rid = next(r["id"] for r in records.all_records(G) if r["hypothesis_id"] == oid)
    own = next(c.split(";")[0] for c in sent.get_all("Set-Cookie") if c.startswith("utsushi_rec="))  # 説明は記録を残した画面からだけ
    assert send(f"/record/{rid}/explain", {"by": "試した人", "text": "柄で押すと大きく開いた", "next_idea": "折りを増やす"}, cookie=own)[0] == 303
    return rid


def one_change():
    """たたき台の今の版から、紙に組める形で寸法を 1 つ変える。"""
    now, _ = loop.version_params(G, SHEET, loop.latest_version(G, SHEET))
    current = {**TEMPLATES["slider_fan"].DEFAULTS, **now}
    # その形に効く寸法だけ（loop.allowed）を、小さくする方から試す。たたき台が内筒を下から押し上げる形（H-B）だと床が少なく、折りを増やす案が先に通り、
    # 後で柄の形の案（STICK）に替えると筒の口の角の床で落ちた（cycle._one_change と同じ理由）
    for param in sorted(loop.allowed("slider_fan", current)):
        value = current.get(param)
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            continue
        step = 1 if isinstance(value, int) else 0.5
        for to in (value - step, value + step):
            if not compose("slider_fan", {**now, param: to}, SOURCE)[2]:
                return param, to
    raise AssertionError("組める変更が無い")


STICK = {"push_amount": 62}

# ── たたき台を誰も刷っていない場でも、手帖で本人の紙を選べる ──
oid0, key0 = made("nextwho000", "刷る前に話した考え", STICK)
body = send(f"/toy/{G}/techo", cookie=key0)[1].decode()
# 手帖は紙を選ばせず、本人の紙があればそれを作る（1 手 1 画面、#87）
assert f'data-hid="{oid0}"' in body, "本人の紙を作る"
assert oid0 not in send(f"/toy/{G}/techo")[1].decode(), "ほかの人には出ない"
assert ">紙を作る<" in send(f"/toy/{G}/techo")[1].decode(), "紙の無い人には、紙を作る道"

assert send(f"/toy/{G}/print", {"hypothesis": SHEET})[0] == 303
assert loop.latest_version(G, SHEET) == 1

# ── 画面: OWN-n の記録からの次の版は、たたき台へ向く ──
THINK, CRAFT = "割り箸の柄で押したら大きく開くと思う", "柄の先に紙を巻くと滑らない"
oid, key = made("nextwho001", THINK, STICK)
rid = recorded("nextwho001", oid, key, CRAFT)
page = send(f"/toy/{G}")[1].decode()
assert f'action="/record/{rid}/next' in page, "OWN-n の記録にも、次の版の欄が出る"
# 改善の輪の節と作る側の数も、同じ記録を数える（説明のある報告は次の版を待ち、説明の無い報告は説明を待つ）
ids = lambda rs: [r["id"] for r in rs]
ready, waiting = kaizen.pending(G, records.all_records(G))
assert rid in ids(ready) and rid not in ids(waiting), (ids(ready), ids(waiting))
# 輪の節は作る側の様子の頁（本人の答え 11-07 夕の Q5 で玩具の頁から移した）。待つ報告から玩具の頁の札へ行ける
assert f'次の版を待つ報告 1 件: <a href="/toy/{G}#{rid}">記録の番号 {rid}</a>' in send(f"/loop/{G}")[1].decode(), "節に出る"
assert send(f"/toy/{G}/record", {"hypothesis": oid0, "sheet_version": 1, "result": "動いた", "who": "nextwho000"}, cookie=key0)[0] == 303
rid0 = next(r["id"] for r in records.all_records(G) if r["hypothesis_id"] == oid0)
assert rid0 in ids(kaizen.pending(G, records.all_records(G))[1]), "説明の無い OWN-n の記録は、説明を待つ"
assert f'説明を待つ報告 1 件: <a href="/toy/{G}#{rid0}">記録の番号 {rid0}</a>' in send(f"/loop/{G}")[1].decode()  # 輪の節は作る側の様子の頁（本人の答え Q5）
assert send("/loop")[0] == 200
base_params = loop.version_params(G, SHEET, 1)[0]
param, to = one_change()
code, _, h = send(f"/record/{rid}/next", {"interpretation": "柄で押すと大きく開いた", "param": param, "to": to, "why": "試した記録から", "by": "採った人"})
assert code == 303 and f"see={SHEET}" in h["Location"], (code, h.get("Location"))
assert loop.latest_version(G, SHEET) == 2, "たたき台に版が足される"
assert not list(loop.folder().glob(f"version-{G}-OWN-*.json")), "OWN-n には版を足さない"
v2 = json.loads((loop.folder() / f"version-{G}-{SHEET}-2.json").read_text(encoding="utf-8"))
assert v2["hypothesis_id"] == SHEET and v2["record_ids"] == [rid] and v2["params"][param] == to, "根拠は OWN-n の記録のまま"
assert v2["params"]["push_part"] == base_params["push_part"], "その人の案の寸法は混ぜない（たたき台の版に、選んだ 1 つだけを足す）"
paper = out_dir(G) / f"{SHEET}_v2.pdf"
# 版の呼び方は組の番号（窓口の決定 11-07・#513 の (a)）。組の中の直しの版 2 は「版 <組の番号>（直し 2）」
ban2 = "".join(hypotheses.label_of(hypotheses.current_set(hypotheses.load(G)), 2).split())  # flat_pdf は空白を落とす
assert paper.exists() and rid in flat_pdf(paper) and ban2 in flat_pdf(paper), "版 2 の紙が刷られ、根拠の記録が載る"
assert any(c["hypothesis_id"] == SHEET and c["version"] == 2 for c in loop.sheet_confirmations(G)), "型紙の確定も残る"
assert words.base_of(G)[1][param] == to, "最新版が次の人の型紙の元になる"
assert rid not in ids(kaizen.pending(G, records.all_records(G))[0]), "版に使った報告は、もう待たない"
assert send(f"/toy/{G}")[0] == 200 and send(f"/toy/{G}/techo")[0] == 200, "版の根拠が OWN-n の記録でも、頁が開く"
assert records.withdraw(rid)[1][0].floor == "F4.evidence", "根拠に使われている記録は消さない（今までの決まりのまま）"
assert talk_log.talks(G, record_id=rid), "断った時は何も消さない"
# 通らない値の時は、たたき台の寸法で理由を返し、何も残さない
assert send(f"/record/{rid}/next", {"interpretation": "x", "param": "nope", "to": 1, "why": "x", "by": "採った人"})[0] == 422
assert loop.latest_version(G, SHEET) == 2

# ── 端末の propose の既定も、たたき台へ向く ──
oid2, key2 = made("nextwho002", "軸を上にしたい", STICK)
rid2 = recorded("nextwho002", oid2, key2)
env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
cli = lambda *a: subprocess.run([sys.executable, "-m", "omochae.loop", *a], capture_output=True, text=True, env=env, stdin=subprocess.DEVNULL)
assert f"{SHEET}" in cli("material", rid2).stdout.split("読んだら")[0], "材料の文に、次の版の向く先"
assert loop.confirm_interpretation(rid2, "確認者", {"human_text": "軸を上にしたら開きが変わった"}) == []  # 端末の confirm は人の確認を端末で取るので、子の命令からは通らない
param2, to2 = one_change()
r = cli("propose", rid2, "--change", f"{param2}={to2}", "--why", "試した記録から")
assert r.returncode == 0, r.stdout + r.stderr
pid = re.search(r"P-\d+", r.stdout).group(0)
made_p = json.loads((loop.folder() / f"proposal-{pid[2:]}.json").read_text(encoding="utf-8"))
assert made_p["hypothesis_id"] == SHEET and made_p["record_ids"] == [rid2], made_p
# OWN-n へ版を足す案は、どの道からでも床で断る
r = cli("propose", rid2, "--hypothesis", oid2, "--change", f"{param2}={to2}", "--why", "x")
assert r.returncode == 3, r.stdout + r.stderr
fs = loop.check_proposal({"record_ids": [rid2], "hypothesis_id": oid2, "changes": [{"param": param2, "to": to2, "why": "x"}]}, SOURCE)
assert any(f.floor == "F7.revision" and "たたき台" in f.message for f in fs), fs


# ── Claude の道の既定も、たたき台へ向く ──
class Fake:
    def __init__(self, script):
        self.script, self.calls = list(script), []
        self.beta = NS(messages=NS(create=self.create))

    def create(self, **kw):
        self.calls.append(kw)
        return NS(content=[NS(type="tool_use", name="submit_result", input=self.script.pop(0), id="t")], stop_reason="tool_use", usage=NS(input_tokens=10, output_tokens=5))


T3, C3 = "扇をもっと開きたい", "内筒に蝋を塗ると滑る"
oid3, key3 = made("nextwho003", T3, STICK)
rid3 = recorded("nextwho003", oid3, key3, C3)
assert loop.confirm_interpretation(rid3, "確認者", {"human_text": "柄で押すと大きく開いた"}) == []
param3, to3 = one_change()
answer = {"changes": [{"param": param3, "to": to3, "why": "話した工夫から"}], "next_to_try": {"why": "比べる", "what_to_measure": "開いた角度"}, "references": []}
to_own = {**answer, "hypothesis_id": oid3}
client = Fake([to_own, answer])
pid3, fs = loop_agents.draft_proposal(rid3, SOURCE, client)
assert not fs and pid3, fs
assert len(client.calls) == 2, "OWN-n へ向けた案はやり直しになる"
sent = client.calls[0]["messages"][0]["content"]
context = json.loads(sent.split("<data>\n", 1)[1].rsplit("\n</data>", 1)[0])
assert context["sheet"] == SHEET and C3 in sent, "向く先と話した工夫を渡す"
assert context["own_paper"]["hypothesis_id"] == oid3 and context["own_paper"]["params"]["push_amount"] == 62, "試した紙の寸法を渡す"
assert T3 not in json.dumps(context["own_paper"], ensure_ascii=False), "考えの字は案の材料に入れない"
assert "own_paper" in client.calls[0]["system"][0]["text"], "決まりの文に、自分の紙の記録の読み方がある"
saved = json.loads((loop.folder() / f"proposal-{pid3[2:]}.json").read_text(encoding="utf-8"))
assert saved["hypothesis_id"] == SHEET and saved["record_ids"] == [rid3], saved

# ── 欄の「今」の値は、たたき台の今の版の物（本人の紙の値でない）。次の版はたたき台に足すので、比べる元はたたき台 ──
param6, to6 = one_change()
oid6, key6 = made("nextwho006", "寸法を変えた紙で試した", {param6: to6})
assert next(h for h in hypotheses.own_hypotheses(G) if h["id"] == oid6)["params"][param6] == to6, "本人の紙の値はたたき台と違う"
rid6 = recorded("nextwho006", oid6, key6)
form = send(f"/toy/{G}")[1].decode().split(f'action="/record/{rid6}/next', 1)[1].split("</form>", 1)[0]
now6 = {**TEMPLATES["slider_fan"].DEFAULTS, **loop.version_params(G, SHEET, loop.latest_version(G, SHEET))[0]}[param6]
assert now6 != to6 and f"今 {now6:g}" in form and f"今 {to6:g}" not in form, form[:400]

# ── 試した後の紙: 話した字が無いので、記録があれば別の人にも開く ──
# 刷るのは型紙だけ（窓口の決定 2026-11-07 カード 012120。#493 と同じ形）。試した後の紙は刷る時に組まず、前に配った道で開く時に作る（print_after）
assert send(f"/sheet/{G}/{oid}_v1_after.pdf")[0] == 200, "記録があれば別の人にも開く"
after = out_dir(G) / f"{oid}_v1_after.pdf"
assert after.exists() and "".join(THINK.split()) not in flat_pdf(after) and "".join(CRAFT.split()) not in flat_pdf(after), "試した後の紙に話した字が刷られない"
assert send(f"/sheet/{G}/{oid}_v1_after.png")[0] == 200
assert send(f"/sheet/{G}/{oid}_v1.pdf")[0] == 404 and send(f"/sheet/{G}/{oid}_v1_tejun.pdf")[0] == 404, "ほかの紙は開かない"
oid4, key4 = made("nextwho004", "記録の前の案", STICK)
assert send(f"/sheet/{G}/{oid4}_v1_after.pdf")[0] == 404, "記録の前は開かない（在るかどうかも言わない）"
public = serve(0, public_open=True)
threading.Thread(target=public.serve_forever, daemon=True).start()
pub = f"http://127.0.0.1:{public.server_address[1]}"
assert send(f"/sheet/{G}/{oid}_v1_after.pdf", to=pub)[0] == 404, "合言葉なしの場では開かない"
public.shutdown()

# ── 型紙なしの紙: 刷った組を残さず、紙の組の報告に数えない ──
oid5, key5 = made("nextwho005", "水の重さで開くのかも", not_fit=["水の重さで動く機構は雛形に無い"])
assert not [c for c in loop.sheet_confirmations(G) if c["hypothesis_id"] == oid5], "型紙なしは組を残さない"
rid5 = recorded("nextwho005", oid5, key5, "紙コップで試した")
# 束の群は紙ごと（Issue 334）。型紙なしの紙の記録はどの組の群にも入らず、組のある自分の紙の記録は組の群に入る
in_set = [g for g in engine_bundle.build()["groups"] if g["sheet_set"] == SET]
assert not any(rid5 in g["record_ids"] for g in in_set) and any(rid in g["record_ids"] for g in in_set), [g["record_ids"] for g in in_set]
assert send(f"/sheet/{G}/{oid5}_v1_after.pdf", cookie=key5)[0] == 200, "型紙なしの紙の記録にも、試した後の紙が開く"
# 次の版は、どの道からも作らない。節の数にも入れない（向く先が無い）
assert loop.next_target(G, oid5) == oid5 and loop.next_target(G, oid) == SHEET, "型紙なしには向く先が無い"
page = send(f"/toy/{G}")[1].decode()
assert f'action="/record/{rid5}/next' not in page and f'action="/record/{rid5}/next' not in send(f"/toy/{G}/techo/kiroku")[1].decode(), "欄を出さない"
assert not {rid5} & set(ids(kaizen.pending(G, records.all_records(G))[0]) + ids(kaizen.pending(G, records.all_records(G))[1])), "節の数に入れない"
param5, to5 = one_change()
latest = loop.latest_version(G, SHEET)
assert send(f"/record/{rid5}/next", {"interpretation": "x", "param": param5, "to": to5, "why": "x", "by": "採った人"})[0] == 422, "受け口も断る"
r = cli("propose", rid5, "--change", f"{param5}={to5}", "--why", "x")
assert r.returncode == 3, r.stdout + r.stderr
assert loop.confirm_interpretation(rid5, "確認者", {"human_text": "水で開いた"}) == []
fs = loop.check_proposal({"record_ids": [rid5], "hypothesis_id": loop.next_target(G, oid5), "changes": [{"param": param5, "to": to5, "why": "x"}]}, SOURCE)
assert fs, "Claude の道の既定でも、寸法の変更は床で断る"
# Claude がたたき台の番号を書いて寸法を変えようとしても、型紙なしの紙の記録からは断り、変更の無い案だけを受ける
keep = {"next_to_try": {"why": "比べる", "what_to_measure": "開いた角度"}, "references": []}
free_client = Fake([{**keep, "hypothesis_id": SHEET, "changes": [{"param": param5, "to": to5, "why": "話した工夫から"}]}, keep])
pid5, fs = loop_agents.draft_proposal(rid5, SOURCE, free_client)
assert not fs and len(free_client.calls) == 2, (fs, len(free_client.calls))
assert not json.loads((loop.folder() / f"proposal-{pid5[2:]}.json").read_text(encoding="utf-8")).get("changes"), "寸法の変更は残らない"
own_paper = json.loads(free_client.calls[0]["messages"][0]["content"].split("<data>\n", 1)[1].rsplit("\n</data>", 1)[0])["own_paper"]
assert own_paper["hypothesis_id"] == oid5 and not own_paper["params"], "型紙なしの紙だと分かる形で渡す"
assert loop.latest_version(G, SHEET) == latest, "たたき台の版は増えない"
server.shutdown()
print("ok")
