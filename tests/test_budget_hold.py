"""安全の事項 3 への対応の試験: AI の費用の上限が、同時に呼んでも越えない。本物の API は呼ばない。

前は check（済んだ台帳だけを読む）→ 呼ぶ → add の間に、呼んでいる途中の費用を数える所が無く、日割り 0.25 で 0.20 の 4 本が同時に通って
0.80 になった。今は check が錠の中で最大の見込み額を予約し、add が実費で精算し、呼べなかった時は release で返す（api.budget の頭の注）。
見る事:
1. 同じプロセスの 4 本（スレッド）と、別のプロセスの 4 本が同時に check しても、通るのは上限の内の 1 本だけで、精算の後の額は上限を越えない
2. 精算すると予約が消え、実費が台帳に残る。呼べなかった時（API の失敗）は予約が返り、次の呼び出しが通る
3. 返し忘れた予約は HOLD_SECONDS を過ぎると数えない
4. 記録の後の次の版（next）と AI の口（ai-interpret・ai-observe）が、同じ相手からの書き込みの数の上限に入る
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from types import SimpleNamespace

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
LEDGER = pathlib.Path(tempfile.mkdtemp()) / "api-usage.jsonl"
os.environ["OMOCHAE_USAGE_LEDGER"] = str(LEDGER)
os.environ.pop("ANTHROPIC_API_KEY", None)

from api import ask, budget  # noqa: E402
from omochae import hypotheses, loop, records  # noqa: E402
from omochae.hypotheses import ROOT  # noqa: E402
from web import play_server  # noqa: E402

CAP, EACH = 0.25, 0.20
MODEL = "claude-opus-5-5"
OUT_TOKENS = round(EACH * 1e6 / budget.PRICES[MODEL][1])  # 出力だけで 0.20 になる数
assert abs(budget.cost(MODEL, 0, OUT_TOKENS) - EACH) < 1e-9
budget.daily_cap = lambda: CAP


def reset():
    # 予約の置き場は台帳の横（前の作りには無いので、名を直に作る。前の作りでも同時の 4 本を回して、越える事を見られるように）
    for p in (LEDGER, LEDGER.with_name(LEDGER.name + ".holds.json")):
        if p.exists():
            p.unlink()


# ---- 1. 同時に 4 本（スレッド）
reset()
gate = threading.Barrier(4)
got = []


def one():
    gate.wait()
    try:
        budget.check(0.0, EACH)
    except budget.BudgetStop as e:
        got.append(e.kind)
        return
    time.sleep(0.3)  # 呼んでいる途中（この間にほかの 3 本が check する）
    budget.add("ask", MODEL, 0, OUT_TOKENS)
    got.append("ok")


threads = [threading.Thread(target=one) for _ in range(4)]
for t in threads:
    t.start()
for t in threads:
    t.join()
day, _ = budget.spent()
assert sorted(got) == ["day", "day", "day", "ok"], ("上限の内の 1 本だけが通る", got)
assert day <= CAP and budget.held() == (0.0, 0.0), ("精算の後の額が上限を越えず、予約が残らない", day, budget.held())

# ---- 1. 同時に 4 本（別のプロセス。台帳の錠は flock なので、プロセスをまたいで取り合う）
reset()
RUNNER = f"""
import os, sys, time
sys.path.insert(0, {str(ROOT / 'src')!r})
os.environ["OMOCHAE_USAGE_LEDGER"] = {str(LEDGER)!r}
from api import budget
budget.daily_cap = lambda: {CAP}
start = float(sys.argv[1])
while time.time() < start:
    time.sleep(0.005)
try:
    budget.check(0.0, {EACH})
except budget.BudgetStop as e:
    print(e.kind); sys.exit(0)
time.sleep(0.5)
budget.add("ask", {MODEL!r}, 0, {OUT_TOKENS})
print("ok")
"""
start = time.time() + 2.0
procs = [subprocess.Popen([sys.executable, "-c", RUNNER, str(start)], stdout=subprocess.PIPE, text=True) for _ in range(4)]
kinds = sorted(p.communicate(timeout=120)[0].strip() for p in procs)
day, _ = budget.spent()
assert kinds == ["day", "day", "day", "ok"], ("別のプロセスでも上限の内の 1 本だけ", kinds)
assert day <= CAP and budget.held() == (0.0, 0.0), (day, budget.held())

# ---- 2. 精算と返し（上限に当てない額で見る）
reset()
budget.daily_cap = lambda: 50.0
budget.check(0.0, EACH)
assert abs(budget.held()[0] - EACH) < 1e-9, "check で最大の見込み額を予約する"
budget.add("ask", MODEL, 0, OUT_TOKENS // 2)
assert budget.held() == (0.0, 0.0) and abs(budget.spent()[0] - EACH / 2) < 1e-9, "add は実費で精算し、予約を消す"
budget.check(0.0, EACH)
budget.release()
assert budget.held() == (0.0, 0.0), "release で予約を返す"
# API が落ちた時（手順の質問の口）: 予約が返り、次が通る
G = "NDL-1187053-R0000005-L"
HG = hypotheses.sheet_of(G)["id"]


class Broken:
    def __init__(self):
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **req):
        assert budget.held()[0] > 0, "呼んでいる間は予約がある"
        raise RuntimeError("つながらない")


reset()
try:
    ask.answer(G, HG, "竹串はいつ通すの？", client=Broken())
    raise AssertionError("落ちた呼び出しで返った")
except RuntimeError:
    pass
assert budget.held() == (0.0, 0.0) and budget.spent()[0] == 0.0, ("呼べなかった時は予約を返し、台帳に何も書かない", budget.held())

# ---- 3. 返し忘れた予約は HOLD_SECONDS を過ぎると数えない
reset()
budget.daily_cap = lambda: CAP
budget._write_holds({"old": {"usd": EACH, "day": budget._today(), "at": time.time() - budget.HOLD_SECONDS - 1},
                     "new": {"usd": 0.01, "day": budget._today(), "at": time.time()}})
assert abs(budget.held()[0] - 0.01) < 1e-9, ("古い予約は数えない", budget.held(), budget.spent(), LEDGER.exists() and LEDGER.read_text())
budget.check(0.0, EACH)  # 古い 0.20 を数えないので通る（0.01 + 0.20 < 0.25）
budget.release()
budget._write_holds({})

# ---- 4. 記録の後の次の版と AI の口も、書き込みの数の上限に入る
server = play_server.serve(0)
server.write_limit = play_server.WriteLimit(limit=2)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"
rid, _ = records.add({"source_id": G, "hypothesis_id": HG, "sheet_version": 1, "result": "動いた"})
assert not loop.save_explanation(rid, "本人", "開いた", "速く押す")


def post(path, who):
    req = urllib.request.Request(base + path, data=urllib.parse.urlencode({"back": "techo"}).encode(),
                                 headers={"Content-Type": "application/x-www-form-urlencoded", "Origin": base, "Cf-Connecting-Ip": who})
    op = urllib.request.build_opener(type("N", (urllib.request.HTTPRedirectHandler,), {"redirect_request": lambda *a, **k: None}))
    try:
        return op.open(req, timeout=60).status
    except urllib.error.HTTPError as e:
        return e.code


try:
    for i, act in enumerate(("ai-interpret", "ai-observe", "next")):
        who = f"203.0.113.{10 + i}"
        codes = [post(f"/record/{rid}/{act}", who) for _ in range(3)]
        assert codes[2] == 429 and 429 not in codes[:2], (act, "同じ相手の 3 回目は数の上限で断る", codes)
finally:
    server.shutdown()
    server.server_close()
print("ok AI の費用は呼ぶ前に最大の見込み額を予約し、同時に呼んでも上限を越えない。記録の後の次の版と AI の口も書き込みの数に入る")
