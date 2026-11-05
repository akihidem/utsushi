"""その場の仮説生成の試験。Claude の応答は記録した形の偽物で、本物の API は呼ばない。"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile
from types import SimpleNamespace as NS

tmp = tempfile.mkdtemp()
os.environ["OMOCHAE_DATA"] = tmp
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(tmp, "api-usage.jsonl")  # 本物の台帳に書かない（#151）
# 子を別の置き場で起こすので、呼ぶ側の PYTHONPATH=src が相対でも読めるように絶対へ直す（#170）
os.environ["PYTHONPATH"] = str(pathlib.Path(__file__).resolve().parents[1] / "src")

from api import budget, generate as gen
from omochae import hypotheses, instructions, loop, records

ROOT = pathlib.Path(__file__).resolve().parents[1]
G = "NDL-1187053-R0000005-L"
source = json.loads((ROOT / "data/sources" / f"{G}.json").read_text(encoding="utf-8"))


def floors(fs):
    return {f.floor for f in fs}


def tool(name, input, i):
    return NS(type="tool_use", name=name, input=input, id=f"{i}-{name}")


class Fake:
    def __init__(self, script):
        self.script, self.calls = list(script), []
        self.beta = NS(messages=NS(create=self.create))

    def create(self, **kw):
        self.calls.append(kw)
        content, stop = self.script.pop(0)
        return NS(content=content, stop_reason=stop, usage=NS(input_tokens=1000, output_tokens=100))


def hyp(name, params, template="slider_fan", evidence=None):
    return {"name": name, "how_it_moves": "動かす", "physics": "折り目の力", "evidence": evidence or [{"kind": "image", "where": "寝かせた筒", "what": "棒", "certainty": "観察"}], "against": ["未確認"], "to_measure": "角度", "template_id": template, "params": params, "vs_own": {"same": ["手で動かす"], "different": ["棒"]}}


A = {"push_part": "tab", "hub": "axle", "pusher_height": 15}
C = {"push_part": "stick", "hub": "axle", "pusher_height": 84}
good = {"hypotheses": [hyp("読み 1", A), hyp("読み 2", C), {**hyp("雛形に無い読み", None, None), "params": None}], "references": []}
# 検査に落ちた案は直させる: 範囲の外・実在しない前例
bad = {"hypotheses": [hyp("範囲の外", {"push_part": "tab", "tube_side": 500}), hyp("x", A)], "references": ["R-9999"]}
client = Fake([([tool("get_template_spec", {"template_id": "slider_fan"}, "a")], "tool_use"), ([tool("submit_result", bad, "b")], "tool_use"), ([tool("submit_result", good, "c")], "tool_use")])
gid, fs = gen.generate(source, client, image="QQ==")
assert not fs, fs
first = client.calls[0]["messages"][0]["content"]
assert first[0]["type"] == "image" and "reader_predictions" not in first[1]["text"], "図を渡す。予想の段は無いので、予想の欄は渡さない（#242）"
# 本人が採らなかった歌の読み（複写 A の「怠らし」）は渡さない。採った読みは渡す
assert "御来迎 拝むにつけて怠らし" not in first[1]["text"] and "怠けらじ" in first[1]["text"]
sent = json.dumps(client.calls[2]["messages"], ensure_ascii=False, default=str)
assert "F5.range" in sent and "F8.references" in sent, "落ちた理由を読ませる"
assert not gen.check_result({"hypotheses": [hyp("1 本", A)], "references": []}, source), "案は 1 本でよい（型紙は玩具ごとに 1 枚。J-032）"
for fail in ({"hypotheses": [], "references": []},
             {"hypotheses": [hyp("a", A), hyp("b", A), hyp("c", A), hyp("d", A)], "references": []},
             {"hypotheses": [hyp("a", A), hyp("b", {"hub": "axle"})], "references": []},
             {"hypotheses": [hyp("a", A), hyp("b", A, "無い雛形")], "references": []},
             {"hypotheses": [hyp("a", A), hyp("b", A, evidence=[{"kind": "record", "where": "R-7777", "what": "x", "certainty": "記録"}])], "references": []}):
    assert gen.check_result(fail, source), fail
# 採るまで一覧に入らない（H3）
assert not [h for h in hypotheses.load(G)["hypotheses"] if h["id"].startswith("H-N")]
assert floors(gen.adopt_generated(gid, " ", [1])[1]) == {"F9.human"}
assert floors(gen.adopt_generated(gid, "確認者", [9])[1]) == {"F9.human"}
made, fs = gen.adopt_generated(gid, "確認者", [1, 3])
assert not fs and made == ["H-N1", "H-N2"]
assert floors(gen.adopt_generated(gid, "確認者", [2])[1]) == {"F9.human"}, "2 度採らない"
# 描くのは描画器。雛形に無い読みは型紙にしない
# 採った案は作る側の控えで、必須 2 種では刷らない（J-032）。控えを刷る道は試作の玩具で見る
assert hypotheses.print_sheet(G, "H-N1", f"{tmp}/n0") == 3 and not pathlib.Path(f"{tmp}/n0.pdf").exists()
TRIAL = "NDL-1187053-R0000004-L-4"
loop._write(loop.folder() / f"extra-hypotheses-{TRIAL}.json", loop._read(loop.folder() / f"extra-hypotheses-{G}.json"))
# 見るのは控えを刷る道だけ。原図の写し（git の外の out/sources）が在る機械でも同じ結果になるよう、ここでは手順の紙に原図を載せない
real_sheet = instructions.compose_sheet
instructions.compose_sheet = lambda *a, **k: real_sheet(*a, **{**k, "picture": None})
assert hypotheses.print_sheet(TRIAL, "H-N1", f"{tmp}/n1") == 0 and pathlib.Path(f"{tmp}/n1.pdf").exists()
assert hypotheses.print_sheet(TRIAL, "H-N2", f"{tmp}/n2") == 0 and not pathlib.Path(f"{tmp}/n2.pdf").exists() and pathlib.Path(f"{tmp}/n2_free.pdf").exists()
instructions.compose_sheet = real_sheet
# 固定の仮説は受け皿として残る
assert any(h["id"] == "H-A" for h in hypotheses.load(G)["hypotheses"])
# 確定した記録が次の生成の前例になり、結果が記録で変わる
empty = json.loads(gen.execute("list_records", {"source_id": G}))
assert empty == []
rid, _ = records.add({"source_id": G, "hypothesis_id": "H-N1", "sheet_version": 1, "result": "動かない", "fixes": [], "note": "開かない"})
assert loop.confirm_interpretation(rid, "確認者", {"human_text": "折りが固い"}) == []
assert [r["id"] for r in json.loads(gen.execute("list_records", {"source_id": G}))] == [rid], "1 人目の記録が次の前例になる"
withref = {"hypotheses": [hyp("読み 3", A, evidence=[{"kind": "record", "where": rid, "what": "開かなかった", "certainty": "記録"}]), hyp("読み 4", C)], "references": [rid]}
assert gen.generate(source, Fake([([tool("submit_result", withref, "d")], "tool_use")]), image="QQ==")[1] == []
# 予算: 上限に当たると呼ばない
path = budget._path()
path.write_text(json.dumps({"day": budget._today(), "role": "x", "model": "claude-opus-5-5", "input": 0, "output": 0, "usd": 1e6}) + "\n", encoding="utf-8")
blocked = Fake([])
try:
    gen.generate(source, blocked, image="QQ==")
    raise AssertionError("止まるはず")
except budget.BudgetStop:
    assert blocked.calls == []
assert abs(budget.cost("claude-opus-5-5", 1_000_000, 1_000_000) - 24) < 1e-9
path.unlink()
# 鍵が無ければ exit 4 で固定の仮説を案内し、値を出さない
env = {k: v for k, v in os.environ.items() if not k.startswith("ANTHROPIC")}
# 図を取り寄せる前に鍵を見る。取り寄せに行くと網に出て、repo の out/sources に書き、網なしでは別の理由で 4 になる
# 手元の repo の .env に鍵が在っても本物を呼ばないよう、.env を読む所だけ差し替えて、鍵の無い機械と同じにする
NO_KEY = """
import sys, anthropic
from api import agent, generate
from omochae import hypotheses
agent.default_client = lambda role=None: anthropic.Anthropic()
def fetched(source):
    raise OSError("図を取り寄せに行った")
generate.source_image = fetched
sys.exit(hypotheses.main(["generate"]))
"""
out = subprocess.run([sys.executable, "-c", NO_KEY], capture_output=True, text=True, env={**env, "HOME": tmp}, cwd=tmp)
assert out.returncode == 4 and "固定の仮説" in out.stderr and "鍵が無い" in out.stderr, out.stderr
assert "取り寄せに行った" not in out.stderr, out.stderr

# 下見: 本物を呼ばず、送る中身を書き出す。案の記録は作らない
before = sorted(p.name for p in loop.folder().glob("generated-*.json"))
dry = subprocess.run([sys.executable, "-m", "omochae.hypotheses", "generate", "--dry-run"], capture_output=True, text=True, env={**env, "OMOCHAE_DATA": tmp})
assert dry.returncode == 0, dry.stderr
assert "本物は呼んでいません" in dry.stdout and (loop.folder() / "preview-generate.json").exists()
assert sorted(p.name for p in loop.folder().glob("generated-*.json")) == before

# 本人の決定で全部 Opus（J-017）。黙って別のモデルに変わらないように固定する
from api.config import MODELS
assert set(MODELS.values()) == {"claude-opus-5-5"}
assert out.returncode == 4
