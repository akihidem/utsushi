"""Claude Code の工房の部品の試験: MCP の道具、案の受付、台帳のフック。本物の API は呼ばない。"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
tmp = tempfile.mkdtemp()
os.environ["OMOCHAE_DATA"] = tmp
G = "NDL-1187053-R0000005-L"


def mcp(*msgs):
    lines = "".join(json.dumps(m, ensure_ascii=False) + "\n" for m in msgs)
    r = subprocess.run([sys.executable, str(ROOT / "src/api/mcp_server.py")], input=lines, capture_output=True, text=True, cwd=ROOT)
    return [json.loads(x) for x in r.stdout.splitlines()]


init = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}}
note = {"jsonrpc": "2.0", "method": "notifications/initialized"}
bad = {"push_part": "tab", "tube_side": 500}
A = {"push_part": "tab", "hub": "axle", "pusher_height": 15}
C = {"push_part": "stick", "hub": "axle", "pusher_height": 84}


def hyp(name, params):
    return {"name": name, "how_it_moves": "動かす", "physics": "折り目の力", "evidence": [{"kind": "image", "where": "筒", "what": "棒", "certainty": "観察"}], "against": ["未確認"], "to_measure": "角度", "template_id": "slider_fan", "params": params, "vs_prediction": {"same": [], "different": []}}


good = {"hypotheses": [hyp("a", A), hyp("b", C)], "references": []}
out = mcp(init, note, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
          {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "check_params", "arguments": {"template_id": "slider_fan", "source_id": G, "params": bad}}},
          {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "check_draft", "arguments": {"source_id": G, "draft": good}}},
          {"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "check_draft", "arguments": {"source_id": G, "draft": {"hypotheses": [hyp("a", bad)], "references": ["R-9999"]}}}},
          {"jsonrpc": "2.0", "id": 6, "method": "tools/call", "params": {"name": "無い道具", "arguments": {}}},
          {"jsonrpc": "2.0", "id": 7, "method": "無い要求"})
by = {m["id"]: m for m in out}
assert len(out) == 7, "通知には返さない"
# API の輪と同じ道具を出す。道具の実装を 2 つ持たない
from api.loop_agents import _tools  # noqa: E402

names = {t["name"] for t in by[2]["result"]["tools"]}
assert names == {t["name"] for t in _tools()} | {"check_draft"}
assert "F5.range" in by[3]["result"]["content"][0]["text"]
assert json.loads(by[4]["result"]["content"][0]["text"]) == []
fails = by[5]["result"]["content"][0]["text"]
assert "F5.range" in fails and "F8.references" in fails
assert by[6]["result"]["isError"] is True and by[7]["error"]["code"] == -32601

# 案の受付: 予想が先、床を通った物だけ、人が採るまで一覧に入らない
from api import generate as gen  # noqa: E402
from omochae import hypotheses  # noqa: E402

source = json.loads((ROOT / "data/sources" / f"{G}.json").read_text(encoding="utf-8"))
assert {f.floor for f in gen.import_draft(source, good, "セッション")[1]} == {"F9.prediction"}
assert hypotheses.save_prediction(G, "筒を押すと開く")[1] == []
assert {f.floor for f in gen.import_draft(source, good, " ")[1]} == {"F9.human"}
assert gen.import_draft(source, {"hypotheses": [hyp("a", bad), hyp("b", C)], "references": []}, "セッション")[1]
gid, fs = gen.import_draft(source, good, "Claude Code のセッション")
assert not fs and gid
draft = json.loads((pathlib.Path(tmp) / "loop" / f"generated-{gid[2:]}.json").read_text(encoding="utf-8"))
assert draft["status"] == "pending_human" and draft["trace"]["via"] == "claude-code-skill"
assert not [h for h in hypotheses.load(G)["hypotheses"] if h["id"].startswith("H-N")]
assert gen.adopt_generated(gid, "確認者", [1])[0] == ["H-N1"]

# 台帳のフック: 対象の外は止めない。台帳が食い違えば exit 2 で Claude に返す
hook = ROOT / ".claude/hooks/ledger-check.sh"


def run_hook(root, path, cwd=None, where=None):
    data = {"tool_input": {"file_path": str(path)}}
    if cwd:
        data["cwd"] = str(cwd)
    return subprocess.run([str(root / ".claude/hooks/ledger-check.sh")], input=json.dumps(data), capture_output=True, text=True, cwd=where)


assert run_hook(ROOT, ROOT / "docs/progress.md").returncode == 0
assert run_hook(ROOT, "/tmp/elsewhere.txt").returncode == 0
copy = pathlib.Path(tempfile.mkdtemp()) / "repo"
shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns(".git", ".venv", "out", "__pycache__"))
(copy / ".venv").symlink_to(ROOT / ".venv")
readme = copy / "README.md"
intact = readme.read_text(encoding="utf-8")
readme.write_text(intact.replace("30 秒の要約", "30 秒の要約（崩した）", 1), encoding="utf-8")
r = run_hook(copy, copy / "README.md")
assert r.returncode == 2 and "L.summary" in r.stderr, r.stderr

# 渡され方が違っても同じ判定にする: 相対のパスは Claude Code の渡す cwd から解き、.. を畳んでから比べる
elsewhere = tempfile.mkdtemp()
for path, cwd, where in (("README.md", copy, elsewhere), ("docs/../README.md", copy, elsewhere), ("../README.md", copy / "docs", elsewhere), ("README.md", None, copy)):
    r = run_hook(copy, path, cwd, where)
    assert r.returncode == 2 and "L.summary" in r.stderr, (path, r.stderr)
assert run_hook(copy, "src/web/skin.py", copy, elsewhere).returncode == 0
assert run_hook(copy, "docs/../../README.md", copy, elsewhere).returncode == 0  # repo の外の同じ名前は対象の外
# 台帳の検査そのものと凍結の場面を直した時も回す
for path in ("src/omochae/ledger.py", "tests/frozen/criteria.md"):
    r = run_hook(copy, copy / path)
    assert r.returncode == 2 and "L.summary" in r.stderr, (path, r.stderr)
readme.write_text(intact, encoding="utf-8")
assert run_hook(copy, copy / "README.md").returncode == 0

# 検査できない時は黙って通さない。exit 0 の stderr は Claude に届かないので、これも exit 2 で返す
claims = copy / "docs/process/claims.json"
kept = claims.read_text(encoding="utf-8")
claims.write_text("{壊れた", encoding="utf-8")
r = run_hook(copy, claims)
assert r.returncode == 2 and "検査できない" in r.stderr, r.stderr
claims.write_text(kept, encoding="utf-8")
broken = subprocess.run([str(copy / ".claude/hooks/ledger-check.sh")], input="{壊れた", capture_output=True, text=True)
assert broken.returncode == 2 and "検査できない" in broken.stderr, broken.stderr
(copy / ".venv").unlink()
r = run_hook(copy, copy / "README.md")
assert r.returncode == 2 and "検査できない" in r.stderr and ".venv" in r.stderr, r.stderr
assert run_hook(copy, "/tmp/elsewhere.txt").returncode == 0  # 対象の外は .venv が無くても止めない
print("ok")
