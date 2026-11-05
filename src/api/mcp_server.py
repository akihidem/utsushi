"""作り手の工房の道具を、Claude Code から MCP で呼べるようにする（.mcp.json の utsushi）。

なぜ MCP か: 裏の制作を Claude Code のセッションで回す時（.claude/skills/backstage）、寸法の検査と図の拡大は
API の輪（src/api/loop_agents.py）と同じ決定的な道具を使わせたい。道具の実装を 2 つ持たず、同じ execute を出す。
なぜ SDK を使わず手で書くか: 使う要求は初期化・一覧・呼び出しの 3 つだけで、依存を増やさずに済むため。
標準入出力で 1 行 1 つの JSON-RPC を受ける。repo の外へは書かない。
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from api.generate import check_result  # noqa: E402
from api.loop_agents import _tools, execute  # noqa: E402
from api.tools import check_source_id  # noqa: E402

PROTOCOL = "2025-06-18"
CHECK_DRAFT = {"name": "check_draft", "description": "仮説の案の全体（submit する形）を、受付と同じ決定的な床にかける。通れば空の一覧。",
               "input_schema": {"type": "object", "properties": {"source_id": {"type": "string"}, "draft": {"type": "object"}}, "required": ["source_id", "draft"]}}


def tools():
    return [{"name": t["name"], "description": t["description"], "inputSchema": t["input_schema"]} for t in _tools() + [CHECK_DRAFT]]


def call(name, args):
    if name == "check_draft":
        check_source_id(args["source_id"])
        source = json.loads((pathlib.Path(__file__).resolve().parents[2] / "data/sources" / f"{args['source_id']}.json").read_text(encoding="utf-8"))
        return [{"type": "text", "text": json.dumps([f.line() for f in check_result(args["draft"], source)], ensure_ascii=False)}]
    out = execute(name, args)
    if isinstance(out, list):  # 画像は MCP の形に直す
        return [{"type": "image", "data": b["source"]["data"], "mimeType": b["source"]["media_type"]} for b in out]
    return [{"type": "text", "text": out}]


def handle(msg):
    method, mid = msg.get("method"), msg.get("id")
    if mid is None:
        return None  # 通知には返さない
    if method == "initialize":
        result = {"protocolVersion": msg.get("params", {}).get("protocolVersion", PROTOCOL), "capabilities": {"tools": {}}, "serverInfo": {"name": "utsushi", "version": "1"}}
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": tools()}
    elif method == "tools/call":
        p = msg.get("params", {})
        try:
            result = {"content": call(p.get("name"), p.get("arguments") or {}), "isError": False}
        except Exception as e:  # 道具の失敗は Claude に返して直させる。サーバは落とさない
            result = {"content": [{"type": "text", "text": f"{type(e).__name__}: {e}"}], "isError": True}
    else:
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"知らない要求: {method}"}}
    return {"jsonrpc": "2.0", "id": mid, "result": result}


def main():
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            reply = handle(json.loads(line))
        except json.JSONDecodeError:
            reply = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "JSON として読めない"}}
        if reply is not None:
            sys.stdout.write(json.dumps(reply, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
