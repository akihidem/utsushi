"""話した考えから型紙を作り直す口（web.think_sheet・api.words）の費用の止め 3 つ（設計 grove の state/tsukuru-talk-sheet-20261108.md の 2 版の 4 節・
別の目の検品の止め 2・本人の答え 11-08「1 日 30 回」）。

見る事:
1. 受け口 /toy/<印>/think-sheet と /toy/<印>/think-ok は、書き込みの数の止め（play_server.WRITE_PATHS）に入る
2. 予算の止め（BudgetStop）に当たった時は、作る側の待ちに落とさず、止めの字で断る。記録（W-番号）を作らない
3. この口が今日 Claude を呼んだ回数が 30 に達したら、Claude を呼ばず、待ちにも置かずに、今日の上限の字で断る。昨日の回は数えない
4. 画面の側（think_sheet.request）は、止めの字をそのまま本人へ返す
"""
import json
import os
import re
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(os.environ["OMOCHAE_DATA"], "api-usage.jsonl")
os.environ.pop("ANTHROPIC_API_KEY", None)

from api import budget, words  # noqa: E402
from omochae import hypotheses, loop  # noqa: E402
from web import play_server, think_sheet  # noqa: E402

G = "NDL-1187053-R0000005-L"
source = json.loads((hypotheses.ROOT / "data/sources" / f"{G}.json").read_text(encoding="utf-8"))
talk = {"text": "扇をもう少し大きく開きたい"}
title, evidence = think_sheet.labels(words.base_of(G)[0])
DAY = budget.BudgetStop.NOTES["day"]


def records():
    return sorted(loop.folder().glob("words-*.json"))


# 1
for act in ("think-sheet", "think-ok"):
    assert play_server.WRITE_PATHS.fullmatch(f"/toy/{G}/{act}"), (act, "書き込みの数の止めに入っていない")

# 2
real_run = words.agent.run


def stopped(*a, **k):
    raise budget.BudgetStop("今日の上限（試験）", "day")


words.agent.run = stopped
try:
    before = len(records())
    w, failures = words.request_think(source, talk, "talk-test-1.json", title, evidence, use_claude=True)
    assert w is None and failures and failures[0].message == DAY, ("予算の止めで止めの字が出ない", w, failures)
    assert len(records()) == before and not words.waiting(), "予算の止めで作る側の待ちに落とした"
finally:
    words.agent.run = real_run

# 3
now = loop._now()
for i in range(budget.WORDS_PER_DAY - 1):
    loop.save_numbered("words", "W", lambda wid: {"id": wid, "source_id": G, "status": "pending_human", "trace": {"model": "x"}, "asked_at": now})
# 昨日の回と、Claude を呼ばなかった回（trace が無い）は数えない
loop.save_numbered("words", "W", lambda wid: {"id": wid, "source_id": G, "status": "pending_human", "trace": {"model": "x"}, "asked_at": "2020-01-01T10:00:00+09:00"})
loop.save_numbered("words", "W", lambda wid: {"id": wid, "source_id": G, "status": "waiting_maker", "trace": None, "asked_at": now})
assert words.called_today() == budget.WORDS_PER_DAY - 1, words.called_today()
calls = []


def called(*a, **k):
    calls.append(1)
    raise RuntimeError("試験では Claude を呼ばない")


words.agent.run = called
try:
    # 29 回目までは呼ぶ（呼べなかった回は前のとおり待ちに落ちる）
    w, failures = words.request_think(source, talk, "talk-test-2.json", title, evidence, use_claude=True)
    assert calls == [1] and w and not failures and w["trace"] == {"fell_back": "RuntimeError"}, (calls, failures)
    assert words.called_today() == budget.WORDS_PER_DAY
    # 30 回に達した後は呼ばず、待ちにも置かない
    before = len(records())
    w, failures = words.request_think(source, talk, "talk-test-3.json", title, evidence, use_claude=True)
    assert calls == [1] and w is None and failures and failures[0].message == DAY, ("回数の止めが効かない", calls, failures)
    assert len(records()) == before, "回数の止めで記録を作った"
    # 鍵の無い道（use_claude=False・作る側の待ち）は回数に関わらず今のまま
    w, failures = words.request_think(source, talk, "talk-test-4.json", title, evidence, use_claude=False)
    assert w and not failures and w["status"] == "waiting_maker", failures
finally:
    words.agent.run = real_run

# 4
keep = words.latest_think, words.asked_for, words.think_fresh, words.request_think
words.latest_think = lambda sid, who: (talk, "talk-test-5.json")
words.asked_for = lambda name: None
words.think_fresh = lambda t: True
words.request_think = lambda *a, **k: (None, [words.Failure("F9.budget", G, DAY)])
try:
    assert think_sheet.request(G, "who", claude=True) == (None, DAY), "画面に止めの字を返さない"
finally:
    words.latest_think, words.asked_for, words.think_fresh, words.request_think = keep
assert budget.WORDS_PER_DAY == 30, "本人の答えの 1 日 30 回"
print("ok 作り直しの口の費用の止め: 受け口は書き込みの数の止め・予算の止めは待ちに落とさず止めの字・1 日 30 回で呼ばずに断る・画面は止めの字")
