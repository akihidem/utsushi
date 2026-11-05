"""API の消費の見張り。予算の決まりの上限を、呼ぶ側で機械的に守る。

実際の消費の正は Console で、これは手元の見積もり。日割りの上限と累計の停止線に当たったら、呼ぶ前に止める。
日割りは、表にある日（期間の中）は表の額、表に無い日（期間の後）は既定の額。累計の停止線は、どの日にも効く。
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
# 表に無い日（期間の後）の日割り。本人の決定（11-05）: 表に無い日は既定の日割りで続け、額は今の表の日割りと同じ額にする。
# 表は日ごとに額が違うので、表の最後の日（11-08）の額を、先の日にもそのまま使う読みにした。違う額が届いたら、ここだけ変える。
# 前は表に無い日を上限 0 と読んでいて、提出の翌日から、Claude を呼ぶ機能が 1 回目の呼び出しの前に全部止まった。
DEFAULT_DAILY_CAP = 50
STOP_TOTAL = 475.0
# 1 回の生成の上限。暴走した輪で日割りを使い切らないため。
PER_RUN_CAP = 3.0


class BudgetStop(Exception):
    """上限で止めた合図。kind は止めた線（day 今日の上限 / total 累計の停止線 / run 1 回の上限）。"""

    # 画面に出す短い文。待てば聞けるのか（今日の上限）、待っても聞けないのか（累計の停止線）が、学ぶ人に分かるようにする。
    # 額と作る側の言葉（本人の承認）は出さない。詳しい数は例外の文（命令の出力）に残す。
    NOTES = {"day": "今日の予算の上限に達しました。明日また聞けます",
             "total": "予算の累計の停止線に達しました。日が変わっても聞けません",
             "run": "この 1 回の上限に達しました"}

    def __init__(self, message, kind="day"):
        super().__init__(message)
        self.kind = kind

    @property
    def note(self):
        return self.NOTES[self.kind]


def _path():
    """台帳は記録の置き場（OMOCHAE_DATA）から切り離して 1 本にする。置き場の中にあると、同じ鍵なのに上限を置き場ごとに別々に数え、
    デモの --fresh（置き場を丸ごと消す）のたびに 0 に戻る（#151）。別の場所へ向ける OMOCHAE_USAGE_LEDGER は試験のための口。"""
    path = pathlib.Path(os.environ.get("OMOCHAE_USAGE_LEDGER") or ROOT / "out/api-usage.jsonl")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _today():
    return datetime.now(timezone(timedelta(hours=9))).strftime("%m-%d")


def daily_cap():
    """今日の日割りの上限。表にある日は表の額、表に無い日（期間の後）は既定の額。"""
    return DAILY_CAP.get(_today(), DEFAULT_DAILY_CAP)


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


# 図 1 枚の入力の数の上限の見積もり。図は画素の数で数えられ（約 1.15MP で 1600 前後）、高い解像度でも 5000 には届かない。
# base64 の文字数で数えると図 1 枚で数百万になり、余裕があっても止めてしまうので、図だけは決まった数で数える。
IMAGE_TOKENS = 5000


def estimate_tokens(*parts):
    """送る中身（指示・道具の定義・会話）の入力の数を、多めに見積もる。

    なぜ多めか: 予算の見張りは呼ぶ前の判断なので、少なく見て上限を越えるより、多く見て手前で止まる方を選ぶ。
    文字 1 つを 1 として数える。日本語はおよそ 1 文字 1 前後、英数字と JSON は 3〜4 文字で 1 なので、どちらも多めになる。
    本物の数え方（count_tokens）は API を 1 回呼ぶので、ここでは使わない。
    """
    def walk(x):
        if isinstance(x, str):
            return len(x)
        if isinstance(x, dict):
            if x.get("type") == "image":
                return IMAGE_TOKENS
            return sum(walk(k) + walk(v) for k, v in x.items())
        if isinstance(x, (list, tuple)):
            return sum(walk(v) for v in x)
        if hasattr(x, "model_dump"):  # SDK の応答の塊（前の往復の応答を会話に積んで送り直す）
            return walk(x.model_dump())
        if hasattr(x, "__dict__"):
            return walk(vars(x))
        return len(str(x))

    return sum(walk(p) for p in parts)


def worst_case(model, input_tokens, max_tokens):
    """この 1 回で使い得る最大の費用。出力は上限まで使い、入力は全部キャッシュの書き込み（入力の単価の 1.25 倍）で数える。"""
    return cost(model, 0, max_tokens, cache_write=input_tokens)


def check(run_usd=0.0, upcoming_usd=0.0):
    """呼ぶ前の見張り。upcoming_usd はこれから呼ぶ 1 回の最悪の費用（worst_case）。

    なぜ足すか: 今までの消費だけを見ると、上限の直前から 1 回分（Opus の出力の上限だけで $0.32）はみ出す（外の検品の指摘、11-04）。
    引数なしと run_usd だけの呼び方は前と同じに動く（upcoming_usd の既定が 0）。
    """
    day, total = spent()
    cap = daily_cap()
    if total + upcoming_usd >= STOP_TOTAL:
        raise BudgetStop(f"累計の見積もり ${total:.2f} と次の 1 回の最大 ${upcoming_usd:.2f} で停止線 ${STOP_TOTAL:.0f} に達する。本人の承認が要る", "total")
    if day + upcoming_usd >= cap:
        raise BudgetStop(f"今日の見積もり ${day:.2f} と次の 1 回の最大 ${upcoming_usd:.2f} で日割りの上限 ${cap} に達する。本人の承認が要る", "day")
    if run_usd + upcoming_usd >= PER_RUN_CAP:
        raise BudgetStop(f"この 1 回が ${run_usd:.2f} と次の最大 ${upcoming_usd:.2f} で上限 ${PER_RUN_CAP:.0f} に達する。そこで止める", "run")


def add(role, model, input_tokens, output_tokens, cache_write=0, cache_read=0):
    usd = cost(model, input_tokens, output_tokens, cache_write, cache_read)
    with open(_path(), "a", encoding="utf-8") as f:
        f.write(json.dumps({"day": _today(), "role": role, "model": model, "input": input_tokens, "output": output_tokens, "cache_write": cache_write, "cache_read": cache_read, "usd": usd}) + "\n")
    return usd
