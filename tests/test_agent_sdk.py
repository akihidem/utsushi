"""本物の SDK を通した輪の試験。通信は手元の偽の送り先で受け、本物の API は呼ばない。

なぜ: 偽の client の試験だけでは、SDK が引数を受けるか、送る形が資料どおりかが分からない。
本物の試験（本人の承認が要る）の 1 回目を、引数の間違いで無駄にしないため。
"""
import json
import os
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(tempfile.mkdtemp(), "api-usage.jsonl")  # 本物の台帳に書かない（#151）

import anthropic
import httpx2

from api import agent, budget

sent = []
# 1 回目は道具を使い、2 回目に結果を出す。キャッシュの数も返し、費用に足されるかを見る
replies = [
    {"content": [{"type": "tool_use", "id": "t1", "name": "echo", "input": {"x": 1}}], "stop_reason": "tool_use",
     "usage": {"input_tokens": 100, "output_tokens": 10, "cache_creation_input_tokens": 1000, "cache_read_input_tokens": 0}},
    {"content": [{"type": "tool_use", "id": "t2", "name": "submit_result", "input": {"answer": "ok"}}], "stop_reason": "tool_use",
     "usage": {"input_tokens": 50, "output_tokens": 10, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 1000}},
]


def handler(request):
    sent.append({"headers": dict(request.headers), "body": json.loads(request.content)})
    r = replies.pop(0)
    return httpx2.Response(200, json={"id": "msg", "type": "message", "role": "assistant", "model": "claude-opus-5-5", "stop_sequence": None, **r})


client = anthropic.Anthropic(api_key="dummy", http_client=httpx2.Client(transport=httpx2.MockTransport(handler)))
tools = [{"name": "echo", "description": "返す", "input_schema": {"type": "object", "properties": {"x": {"type": "integer"}}}}]
schema = {"type": "object", "properties": {"answer": {"type": "string"}}, "required": ["answer"]}
result, trace = agent.run("generate", "指示", "問い", tools, schema, lambda name, inp: json.dumps(inp), client=client)
assert result == {"answer": "ok"} and trace.tool_calls == ["echo"]
first = sent[0]
assert "server-side-fallback-2026-07-01" in first["headers"]["anthropic-beta"]
body = first["body"]
assert body["model"] == "claude-opus-5-5" and body["fallbacks"] == "default" and body["thinking"] == {"type": "adaptive"}
# キャッシュ: 変わらない指示の終わりに目印、伸びる会話は自動の目印
assert body["system"][-1]["cache_control"] == {"type": "ephemeral"} and body["cache_control"] == {"type": "ephemeral"}
assert sent[1]["body"]["system"] == body["system"], "指示が往復で変わるとキャッシュが効かない"
# 入力の数はキャッシュの分も足す。費用は書き込み 1.25 倍、読み出し 0.05 倍で数える
assert trace.input_tokens == 100 + 1000 + 50 + 1000
rows = [json.loads(line) for line in budget._path().read_text(encoding="utf-8").splitlines()]
assert [r["cache_write"] for r in rows] == [1000, 0] and [r["cache_read"] for r in rows] == [0, 1000]
assert abs(budget.cost("claude-opus-5-5", 0, 0, 1_000_000, 1_000_000) - (4 * 1.25 + 4 * 0.05)) < 1e-9
assert abs(budget.cost("claude-opus-5-5", 1_000_000, 1_000_000) - 24) < 1e-9, "キャッシュの無い数え方は前と同じ"

# 下見: 呼ばずに止まり、送る中身を返す。画像は大きさだけにする
try:
    agent.run("words", "指示", [{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": "QUJD"}}], tools, schema, lambda n, i: "", client=agent.PreviewClient())
    raise AssertionError("下見は止まるはず")
except agent.Preview as stop:
    request = stop.request
    shown = agent.elide_images(request)
assert shown["messages"][0]["content"][0]["source"]["data"] == "<base64 4 文字を省いた>"
assert request["messages"][0]["content"][0]["source"]["data"] == "QUJD", "元の要求は書き換えない"
assert len(rows) == len(budget._path().read_text(encoding="utf-8").splitlines()), "下見は費用を記録しない"
print("ok")
