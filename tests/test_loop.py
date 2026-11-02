"""輪の後半の試験。Claude の応答は記録した形の偽物で、本物の API は呼ばない。"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile
from types import SimpleNamespace as NS

tmp = tempfile.mkdtemp()
os.environ["OMOCHAE_DATA"] = tmp

from api import agent, config, loop_agents
from omochae import hypotheses, loop, records

ROOT = pathlib.Path(__file__).resolve().parents[1]
G, T = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"
gs = json.loads((ROOT / "data/sources" / f"{G}.json").read_text(encoding="utf-8"))
ts = json.loads((ROOT / "data/sources" / f"{T}.json").read_text(encoding="utf-8"))


def rec(source=G, hyp="H-A", **kw):
    rid, fs = records.add({"source_id": source, "hypothesis_id": hyp, "sheet_version": 1, "result": "動かない", "opened_deg": 60, "opener": "紙の力", "fixes": [], "note": "開き切らない", **kw})
    assert not fs, fs
    return rid


def floors(fs):
    return {f.floor for f in fs}


def tool(name, input, i="t"):
    return NS(type="tool_use", name=name, input=input, id=f"{i}-{name}")


class Fake:
    """台本どおりに返す偽のクライアント。渡された内容も残す。"""

    def __init__(self, script):
        self.script, self.calls = list(script), []
        self.beta = NS(messages=NS(create=self.create))

    def create(self, **kw):
        self.calls.append(kw)
        content, stop = self.script.pop(0)
        return NS(content=content, stop_reason=stop, usage=NS(input_tokens=10, output_tokens=5))


interp = {"observed": ["60° で止まった"], "causes": [{"text": "折りが固い", "confidence": "中くらい"}], "unknown": ["紙の差"]}
# H6: 確定なしには進めない
r1 = rec()
never = Fake([])
assert floors(loop_agents.draft_interpretation(r1, never)[1]) == {"F9.human"} and never.calls == [], "人の説明の前に Claude を呼ばない"
assert floors(loop.save_explanation(r1, "確認者", "折りが固そう", " ")) == {"F9.human"}, "次の思いつきも人が先"
assert floors(loop.save_explanation(r1, "確認者", "連絡先 a@example.com", "折りを減らす")) == {"F3.result"}
assert loop.save_explanation(r1, "確認者", "わからない", "折りを減らす") == []
client = Fake([([tool("submit_result", interp)], "tool_use")])
assert loop_agents.draft_interpretation(r1, client) == (interp, [])
assert "折りを減らす" in client.calls[0]["messages"][0]["content"]
assert loop.interpretation(r1)["status"] == "pending_human"
assert client.calls[0]["model"] == config.MODELS["interpret"] and "tool_choice" not in client.calls[0], "Opus 5.5 は強制の tool_choice が 400"
assert "<record>" in client.calls[0]["messages"][0]["content"]
assert loop.confirmed_records(G) == [], "確定していない記録を前例にしない"
never = Fake([])
pid, fs = loop_agents.draft_proposal(r1, gs, never)
assert floors(fs) == {"F9.human"} and never.calls == [], "確定の前に Claude を呼ばない"
assert floors(loop.save_proposal({"record_ids": [r1], "hypothesis_id": "H-A", "changes": [{"param": "fold_width", "to": 9, "why": "x"}]}, gs, "human")[1]) == {"F9.human"}
assert floors(loop.confirm_interpretation(r1, " ")) == {"F9.human"}
assert loop.confirm_interpretation(r1, "確認者") == []
assert [x["id"] for x in loop.confirmed_records(G)] == [r1]
# F4・F8・F7
assert floors(loop.save_proposal({"record_ids": [], "hypothesis_id": "H-A", "changes": []}, gs, "human")[1]) == {"F4.evidence"}
assert floors(loop.save_proposal({"record_ids": ["R-9999"], "hypothesis_id": "H-A"}, gs, "human")[1]) == {"F8.references"}
assert floors(loop.save_proposal({"record_ids": [r1], "references": ["KE-無い"]}, gs, "human")[1]) == {"F8.references"}
assert floors(loop.save_proposal({"record_ids": [r1], "hypothesis_id": "H-A", "changes": [{"param": "tube_glue", "to": 9, "why": "x"}]}, gs, "human")[1]) == {"F7.revision"}, "変えてよい寸法の外"
assert floors(loop.save_proposal({"record_ids": [r1], "hypothesis_id": "H-A", "changes": [{"param": "fold_width", "to": 8.5, "why": "x"}]}, gs, "human")[1]) == {"F7.revision"}, "版 1 と同じ"
assert floors(loop.save_proposal({"record_ids": [r1], "hypothesis_id": "H-A", "changes": [{"param": "fold_width", "to": 9, "why": " "}]}, gs, "human")[1]) == {"F4.evidence"}
assert floors(loop.save_proposal({"record_ids": [r1], "hypothesis_id": "H-A", "changes": [{"param": "fold_width", "to": 8, "why": "短くする", "metric": "opening_bound_deg", "direction": "increase"}]}, gs, "human")[1]) == {"F7.revision"}, "式と逆向き"
assert floors(loop.save_proposal({"record_ids": [r1], "ranking": [{"hypothesis_id": "H-Z", "rank_after": 1, "why": "x"}]}, gs, "human")[1]) == {"F8.references"}
# 虎: 周期の向き（重りを軸に近づけると短い）
tr = rec(T, "H-A", opener=None, opened_deg=None, ten_swings_sec=4.1)
assert loop.confirm_interpretation(tr, "確認者", {"human_text": "ゆっくりで見えにくい"}) == []
assert floors(loop.save_proposal({"record_ids": [tr], "hypothesis_id": "H-A", "changes": [{"param": "weight_below_axle", "to": 36, "why": "x", "metric": "period_s", "direction": "decrease"}]}, ts, "human")[1]) == {"F7.revision"}
tp, fs = loop.save_proposal({"record_ids": [tr], "hypothesis_id": "H-A", "changes": [{"param": "weight_below_axle", "to": 18, "why": "速くする", "metric": "period_s", "direction": "decrease"}]}, ts, "human")
assert not fs
# エージェント: 前例を引き、床で直し、案を出す。落ちた案は直させる
bad = {"hypothesis_id": "H-A", "changes": [{"param": "fold_width", "to": 8, "why": "長さを詰める", "metric": "opening_bound_deg", "direction": "increase"}], "next_to_try": {"why": "a", "what_to_measure": "b"}, "references": [r1]}
# 9mm は検査（紙の外・口の角に当たる）で落ちるので、通る 8.6mm の案にする。
good = {"hypothesis_id": "H-A", "changes": [{"param": "fold_width", "to": 8.6, "why": f"{r1} の 60° から長くする", "metric": "opening_bound_deg", "direction": "increase"}],
        "ranking": [{"hypothesis_id": "H-D", "rank_after": 1, "why": "下げる形を先に見分ける"}], "new_hypothesis": {"name": "糸で先に開く", "how_it_moves": "糸を引く", "params": {"push_part": "stick", "hub": "axle", "pusher_height": 84}, "against": ["未確認"], "to_measure": "角度", "evidence": []},
        "next_to_try": {"hypothesis_id": "H-D", "why": "比べる", "what_to_measure": "開いた角度と筒を下げた距離の比"}, "references": [r1]}
client = Fake([([tool("list_records", {"source_id": G}, "a"), tool("get_known_examples", {"source_id": G}, "a")], "tool_use"),
               ([tool("check_params", {"template_id": "slider_fan", "source_id": G, "params": {"fold_width": 9}}, "b")], "tool_use"),
               ([tool("submit_result", bad, "c")], "tool_use"),
               ([tool("submit_result", good, "d")], "tool_use")])
pid, fs = loop_agents.draft_proposal(r1, gs, client)
assert not fs, fs
sent = json.dumps(client.calls[1]["messages"][2]["content"], ensure_ascii=False, default=str)
assert r1 in sent, "確定した記録が前例として引かれる"
# messages は同じリストを使い回すので、全体から探す。
assert "逆" in json.dumps(client.calls[3]["messages"], ensure_ascii=False, default=str), "落ちた理由を読ませる"
saved = loop._read(loop.folder() / f"proposal-{pid[2:]}.json")
assert saved["status"] == "pending_human" and saved["trace"]["tool_calls"] == ["list_records", "get_known_examples", "check_params"] and saved["changes"][0]["formula_check"] == "ok"
# 採るまで何も変わらない（F9）
assert loop.latest_version(G, "H-A") == 1 and all(h["rank"] is None for h in hypotheses.load(G)["hypotheses"])
assert floors(loop.adopt(pid, " ", ["fold_width"])[1]) == {"F9.human"}
made, fs = loop.adopt(pid, "確認者", ["fold_width"], True, True)
assert not fs and made == {"version": 2, "ranking": True, "new_hypothesis": "H-N1"}
assert floors(loop.adopt(pid, "確認者", ["fold_width"])[1]) == {"F9.human"}, "同じ提案を 2 度採らない"
data = hypotheses.load(G)
shown = "\n".join(hypotheses.list_lines(data, "予想"))
assert "順位" not in shown and "動いた " not in shown, "順位と集計は学ぶ人の画面に出さない"
assert next(h for h in data["hypotheses"] if h["id"] == "H-D")["rank"] == 1 and any(h["id"] == "H-N1" and any(e["where"] == r1 for e in h["evidence"]) for h in data["hypotheses"])
# 版 2 の紙: 根拠の記録が刷られる
assert hypotheses.save_prediction(G, "試験")[1] == []
assert hypotheses.print_sheet(G, "H-A", f"{tmp}/v2", version=2) == 0
flat = "".join(subprocess.run(["pdftotext", f"{tmp}/v2.pdf", "-"], capture_output=True, text=True).stdout.split())
assert "版2" in flat and r1 in flat
flat = "".join(subprocess.run(["pdftotext", f"{tmp}/v2_tejun.pdf", "-"], capture_output=True, text=True).stdout.split())
assert "fold_width" in flat or "折り幅" in flat
assert hypotheses.print_sheet(G, "H-A", f"{tmp}/v3", version=3) == 3, "採っていない版は刷らない"
assert hypotheses.print_sheet(G, "H-N1", f"{tmp}/n1") == 0, "採った新しい仮説を刷れる"
# 上限
many = [([tool("list_records", {"source_id": G}, f"m{i}")], "tool_use") for i in range(config.MAX_TOOL_CALLS + 2)] + [([tool("submit_result", interp, "z")], "tool_use")]
client = Fake(many)
_, trace = agent.run("interpret", "s", "u", loop_agents._tools(), loop_agents.INTERPRET_SCHEMA, loop_agents.execute, client=client)
assert len(trace.tool_calls) == config.MAX_TOOL_CALLS, "道具は 8 回まで"
assert "is_error" in json.dumps(client.calls[-1]["messages"], default=str)
client = Fake([([tool("submit_result", {}, f"r{i}")], "tool_use") for i in range(5)])
try:
    agent.run("interpret", "s", "u", [], loop_agents.INTERPRET_SCHEMA, loop_agents.execute, validate=lambda r: ["だめ"], client=client)
    raise AssertionError("止まるはず")
except agent.AgentStopped:
    assert len(client.calls) == config.MAX_RETRIES + 1, "やり直しは 2 回まで"
for stop in ("refusal", "max_tokens"):
    try:
        agent.run("interpret", "s", "u", [], {}, loop_agents.execute, client=Fake([([], stop)]))
        raise AssertionError(stop)
    except agent.AgentStopped:
        pass
# CLI: 端末で人が打たないと確定しない。鍵が無ければ exit 4 で、値を出さない
r3 = rec()
out = subprocess.run([sys.executable, "-m", "omochae.loop", "confirm", r3, "--by", "Claude", "--text", "x"], capture_output=True, text=True, stdin=subprocess.DEVNULL, start_new_session=True)
assert out.returncode == 3 and "F9.human" in out.stderr and not loop.confirmed(r3)
env = {k: v for k, v in os.environ.items() if not k.startswith("ANTHROPIC")}
out = subprocess.run([sys.executable, "-m", "omochae.loop", "interpret", r3], capture_output=True, text=True, env={**env, "HOME": tmp})
assert out.returncode == 3 and "F9.human" in out.stderr, "説明が無ければ鍵の前に止まる"
assert loop.save_explanation(r3, "確認者", "わからない", "もう一度折る") == []
out = subprocess.run([sys.executable, "-m", "omochae.loop", "interpret", r3], capture_output=True, text=True, env={**env, "HOME": tmp})
assert out.returncode == 4 and "検査できない" in out.stderr
# 人の手書きの変更でも整数の寸法が通る。半端な折り数は落とす
hand, fs = loop.save_proposal({"record_ids": [r1], "hypothesis_id": "H-B", "changes": [{"param": "fold_count", "to": 26.0, "why": "折りを減らす"}]}, gs, "human")
assert not fs and hand
assert floors(loop.save_proposal({"record_ids": [r1], "hypothesis_id": "H-B", "changes": [{"param": "fold_count", "to": 26.5, "why": "x"}]}, gs, "human")[1]) == {"F5.range"}
