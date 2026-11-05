"""API の予算の日割りは、表に無い日（期間の後）も既定の額で続く。止まった時の画面の文は、今日の上限か累計の停止線かを言う。本物の API は呼ばない。

なぜ要るか: DAILY_CAP は 11-02〜11-08 だけを持ち、表に無い日は上限 0 と読んでいた。提出の翌日（11-09）から、Claude を呼ぶ機能が
1 回目の呼び出しの前に全部止まり、画面の文からは日付が原因だと分からなかった。本人の決定（11-05）: 表に無い日は既定の日割りで続ける。
"""
import json
import os
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(tempfile.mkdtemp(), "api-usage.jsonl")  # 本物の台帳に書かない（#151）

from api import ask, budget  # noqa: E402

TABLE = {"11-02": 40, "11-03": 50, "11-04": 60, "11-05": 70, "11-06": 80, "11-07": 70, "11-08": 50}


def on(day):
    """試験を回す日で結果が変わらないよう、今日を決める。"""
    budget._today = lambda: day


def reset():
    """費用の台帳だけを空にする（置き場は変えない。画面の試験は同じ置き場の記録を使う）。"""
    budget._path().unlink(missing_ok=True)


def spend(usd, day=None):
    with open(budget._path(), "a", encoding="utf-8") as f:
        f.write(json.dumps({"day": day or budget._today(), "role": "t", "model": "claude-opus-5-5", "usd": usd}) + "\n")


def stopped(fn):
    try:
        fn()
    except budget.BudgetStop as e:
        return e
    raise AssertionError("予算で止まるはず")


# 1. 表に無い日でも、既定の上限の中なら通る（前は上限 0 で、1 回目の前に止まった）
for day in ("11-09", "12-01", "12-31"):
    reset()
    on(day)
    budget.check(0.0, 0.05)
    assert budget.daily_cap() == budget.DEFAULT_DAILY_CAP > 0, day

# 2. 表に無い日も、既定の上限で止まる（日割りを見ない形にはしない。1 日で使い切らせない）
reset()
on("11-09")
spend(budget.DEFAULT_DAILY_CAP - 1.0)
budget.check(0.0, 0.5)  # 上限の手前は通る
e_day = stopped(lambda: budget.check(0.0, 1.0))  # 次の 1 回で上限に届くなら止まる
assert e_day.kind == "day", e_day.kind

# 3. 表にある日（11-02〜11-08）の額は変わらない
assert budget.DAILY_CAP == TABLE, budget.DAILY_CAP
for day, cap in TABLE.items():
    on(day)
    assert budget.daily_cap() == cap, day

# 4. 累計の停止線は変わらず、表に無い日にも効く（今日の分は 0 で、前の日までの累計が線の直前）
assert budget.STOP_TOTAL == 475.0
reset()
on("12-01")
spend(budget.STOP_TOTAL - 0.05, day="11-05")
e_total = stopped(lambda: budget.check(0.0, 0.1))
assert e_total.kind == "total", e_total.kind

# 5. 既定の額は 1 か所にある。そこを変えると、表に無い日の上限だけが変わる
keep = budget.DEFAULT_DAILY_CAP
budget.DEFAULT_DAILY_CAP = 7
on("11-09")
assert budget.daily_cap() == 7
on("11-05")
assert budget.daily_cap() == 70
budget.DEFAULT_DAILY_CAP = keep

# 6. 止まった時の文は、今日の上限か累計の停止線かを言う。今日の上限なら、日が変われば聞けると分かる
assert "今日" in e_day.note and "累計" not in e_day.note, e_day.note
assert "累計" in e_total.note and "今日" not in e_total.note, e_total.note
e_run = stopped(lambda: (reset(), on("11-09"), budget.check(budget.PER_RUN_CAP)))
assert e_run.kind == "run" and "1 回" in e_run.note, (e_run.kind, e_run.note)
# 画面の文に、額（$）と作る側の言葉（本人の承認）を出さない。詳しい数は例外の文（記録と命令の出力）に残す
for e in (e_day, e_total, e_run):
    assert "$" not in e.note and "承認" not in e.note, e.note
    assert "$" in str(e), str(e)

# 7. 画面: 手順の質問（玩具の頁・手帖）と、手帖の Claude の返事の 3 つの口が、同じ文で理由を言う
from api import agent, loop_agents  # noqa: E402
from omochae import hypotheses, loop, records  # noqa: E402
from web.play_server import serve  # noqa: E402

G = "NDL-1187053-R0000005-L"
server = serve(0)
base = f"http://127.0.0.1:{server.server_address[1]}"
threading.Thread(target=server.serve_forever, daemon=True).start()


def post(path, data):
    r = urllib.request.Request(base + path, data=urllib.parse.urlencode(data).encode(), headers={"Content-Type": "application/x-www-form-urlencoded", "Origin": base})
    op = urllib.request.build_opener(type("N", (urllib.request.HTTPRedirectHandler,), {"redirect_request": lambda *a, **k: None}))
    try:
        x = op.open(r)
        return x.status, x.headers.get("Location", ""), x.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Location", ""), e.read().decode()


def over(*a, **k):
    """Claude を呼ぶ所の代わり。呼ぶ前の見張り（budget.check）だけを通す。"""
    budget.check(0.0, 1.0)
    raise AssertionError("予算で止まるはず")


hypotheses.save_prediction(G, "押すと開く")
assert post(f"/toy/{G}/print", {"hypothesis": "H-A"})[0] == 303
rid, _ = records.add({"source_id": G, "hypothesis_id": "H-A", "sheet_version": 1, "result": "動いた"})
assert not loop.save_explanation(rid, "本人", "開いた", "速く押す")
ask.answer = over
ask._key_present = lambda: True  # 鍵がある時の道を通す。Claude を呼ぶ所は上の代わりに替えてある
agent.default_client = lambda role=None: None
loop_agents.draft_interpretation = over
on("11-09")
for fill, word, other in ((lambda: spend(budget.DEFAULT_DAILY_CAP - 0.5), "今日の予算の上限", "累計"),
                          (lambda: spend(budget.STOP_TOTAL - 0.5, day="11-05"), "累計の停止線", "今日")):
    reset()
    fill()
    code, _, page = post(f"/toy/{G}/ask", {"hypothesis": "H-A", "question": "竹串はいつ通すの？"})
    assert code == 200 and word in page and "$" not in page.split("今は AI に聞けません", 1)[1][:80], (code, word)
    code, _, body = post(f"/toy/{G}/ask-json", {"hypothesis": "H-A", "question": "竹串はいつ通すの？"})
    got = json.loads(body)
    assert code == 200 and got["from"] == "stop" and word in got["text"] and other not in got["text"], got
    code, loc, _ = post(f"/record/{rid}/ai-interpret", {"back": "techo"})
    assert code == 303 and urllib.parse.quote(word) in loc and urllib.parse.quote(other) not in loc, loc
server.shutdown()
print("ok")
