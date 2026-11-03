"""API の消費の見張り。予算の決まりの上限を、呼ぶ側で機械的に守る。

実際の消費の正は Console で、これは手元の見積もり。日割りの上限と累計の停止線に当たったら、呼ぶ前に止める。
上限の値は予算の決まりの配分表と同じ。変える時は本人の承認が要る。
"""
import json
import os
import pathlib
from datetime import datetime, timedelta, timezone

ROOT = pathlib.Path(__file__).resolve().parents[2]
PRICES = {"claude-opus-5-5": (4.0, 20.0), "claude-sonnet-5-5": (2.0, 10.0), "claude-haiku-5-5": (0.10, 0.50)}
# キャッシュの書き込みと読み出しは入力の単価に掛ける。5 分の書き込みは 1.25 倍。読み出しは Opus 5.5 が 0.05 倍、他は 0.1 倍（claude-api の資料）。
CACHE_WRITE = 1.25
CACHE_READ = {"claude-opus-5-5": 0.05}
DAILY_CAP = {"11-02": 40, "11-03": 50, "11-04": 60, "11-05": 70, "11-06": 80, "11-07": 70, "11-08": 50}
STOP_TOTAL = 475.0
# 1 回の生成の上限。暴走した輪で日割りを使い切らないため。
PER_RUN_CAP = 3.0


class BudgetStop(Exception):
    pass


def _path():
    base = pathlib.Path(os.environ["OMOCHAE_DATA"]) if os.environ.get("OMOCHAE_DATA") else ROOT / "out"
    base.mkdir(parents=True, exist_ok=True)
    return base / "api-usage.jsonl"


def _today():
    return datetime.now(timezone(timedelta(hours=9))).strftime("%m-%d")


def cost(model, input_tokens, output_tokens, cache_write=0, cache_read=0):
    i, o = PRICES.get(model, PRICES["claude-opus-5-5"])
    return (input_tokens * i + cache_write * i * CACHE_WRITE + cache_read * i * CACHE_READ.get(model, 0.1) + output_tokens * o) / 1e6


def spent():
    path = _path()
    total = day = 0.0
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            total += row["usd"]
            day += row["usd"] if row["day"] == _today() else 0.0
    return day, total


def check(run_usd=0.0):
    day, total = spent()
    cap = DAILY_CAP.get(_today(), 0)
    if total >= STOP_TOTAL:
        raise BudgetStop(f"累計の見積もり ${total:.2f} が停止線 ${STOP_TOTAL:.0f} に達した。本人の承認が要る")
    if day >= cap:
        raise BudgetStop(f"今日の見積もり ${day:.2f} が日割りの上限 ${cap} に達した。本人の承認が要る")
    if run_usd >= PER_RUN_CAP:
        raise BudgetStop(f"この 1 回が ${run_usd:.2f} に達した。上限 ${PER_RUN_CAP:.0f} で止める")


def add(role, model, input_tokens, output_tokens, cache_write=0, cache_read=0):
    usd = cost(model, input_tokens, output_tokens, cache_write, cache_read)
    with open(_path(), "a", encoding="utf-8") as f:
        f.write(json.dumps({"day": _today(), "role": role, "model": model, "input": input_tokens, "output": output_tokens, "cache_write": cache_write, "cache_read": cache_read, "usd": usd}) + "\n")
    return usd
