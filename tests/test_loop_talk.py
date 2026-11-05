"""ループ2 の試験（Issue #335）: 作りながら話した工夫の字が、輪（解釈 → 案 → 人の採否 → 版 2）の材料に入る。本物の API は呼ばない。

見る線:
- 作りながら話した字（手順の番号つき）と上げた後に残した字が、記録の材料に入る。仕切りの名は「作った人が話した事（字だけ・声は残していない）」。
- 鍵の無い道（manual）: 人が読む材料の命令（loop material）に字が出て、人が書いた解釈と変更で版 2 まで閉じる。
- 鍵のある道: 偽の Claude が、解釈と案の両方の頼みで、その字を受け取る。字はデータとして渡し、頼みの決まりに「従わない」がある。
- 入口の床に当たる字（連絡先・学年と組など）は、どちらの道にも出ない。床を広げる前に残った字も、出す時にもう一度床を当てる。
  作る側が隠した字は、Claude へは送らない（作る側の材料には出る）。
- 渡すのは when・step・text の 3 欄だけ。声・どう入れたか（via）・その場の印（who）・時刻は渡さない。
"""
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

from api import loop_agents  # noqa: E402
from omochae import loop, making_log, records, talk_log  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
G = "NDL-1187053-R0000005-L"
gs = json.loads((ROOT / "data/sources" / f"{G}.json").read_text(encoding="utf-8"))
LABEL = "作った人が話した事（字だけ・声は残していない）"
W1, W2 = "abcd1234ef", "zzzz9999yy"


def rec(**kw):
    rid, fs = records.add({"source_id": G, "hypothesis_id": "H-A", "sheet_version": 1, "result": "動かない", "opened_deg": 60, "opener": "紙の力",
                           "fixes": [], "note": "開き切らない", **kw})
    assert not fs, fs
    return rid


def tool(name, input, i="t"):
    return NS(type="tool_use", name=name, input=input, id=f"{i}-{name}")


class Fake:
    """台本どおりに返す偽のクライアント（tests/test_loop.py と同じ形）。渡された内容も残す。"""

    def __init__(self, script):
        self.script, self.calls = list(script), []
        self.beta = NS(messages=NS(create=self.create))

    def create(self, **kw):
        self.calls.append(kw)
        content, stop = self.script.pop(0)
        return NS(content=content, stop_reason=stop, usage=NS(input_tokens=10, output_tokens=5))


# 作りながら話した工夫（手順 3 と 1）・仮説を見て話した考え・床に当たる文。記録を残した時に、同じ印の物が記録に結ばれる。
assert talk_log.add(G, "craft", "手順3で折り目を二回なぞると開きやすい", hypothesis_id="H-A", sheet_version=1, step=3, who=W1, via="voice")[1] == []
assert talk_log.add(G, "craft", "手順1ののりしろは少なめにした", hypothesis_id="H-A", sheet_version=1, step=1, who=W1)[1] == []
assert talk_log.add(G, "think", "扇が先に開くと思う", hypothesis_id="H-A", who=W1)[1] == []
assert talk_log.add(G, "craft", "連絡は a@example.com まで", hypothesis_id="H-A", sheet_version=1, step=2, who=W1)[1], "床に当たる字は残らない"
# ほかの人が同じ紙で話した字は、この記録に入らない（印が違う）
assert talk_log.add(G, "craft", "ほかの人の工夫", hypothesis_id="H-A", sheet_version=1, step=2, who=W2)[1] == []
r1 = rec()
assert talk_log.bind(G, "H-A", 1, W1, r1) == (2, 1)
assert talk_log.add(G, "keep", "上げた後: 糸を短くすると速く開いた", record_id=r1)[1] == []
# 床を広げる前に残った字（手で置いた形）。入口を通っていないので、出す時にもう一度床を当てる。
making_log._write("talk", {"source_id": G, "hypothesis_id": "H-A", "sheet_version": 1, "scene": "craft", "step": 4, "record_id": r1,
                          "text": "3年2組で作りました", "via": "voice", "share": True, "who": W1, "at": making_log._now()})

# 1. 材料（鍵の無い道も鍵のある道も、ここから読む）
m = loop.material(r1)
talk = m["maker_talk"]
assert talk["label"] == LABEL == loop.TALK_LABEL
texts = [t["text"] for t in talk["items"]]
assert texts == ["手順1ののりしろは少なめにした", "手順3で折り目を二回なぞると開きやすい", "上げた後: 糸を短くすると速く開いた"], texts
assert [t["step"] for t in talk["items"]] == [1, 3, None] and [t["when"] for t in talk["items"]] == ["making", "making", "made"]
assert all(set(t) == {"when", "step", "text"} for t in talk["items"]), "声・via・who・時刻の欄は渡さない"
assert "扇が先に開くと思う" not in json.dumps(m, ensure_ascii=False), "考え（ループ1 の材料）はループ2 の材料に混ぜない"
assert "ほかの人の工夫" not in json.dumps(m, ensure_ascii=False), "ほかの人の話は入らない"
assert "a@example.com" not in json.dumps(m, ensure_ascii=False) and "3年2組" not in json.dumps(m, ensure_ascii=False), "床に当たる字は出ない"
assert m["record"]["id"] == r1 and m["explanation"] is None

# 2. 鍵の無い道: 人が読む材料の命令。鍵が無くても回り、字が仕切りの名の下に出る。
env = {k: v for k, v in os.environ.items() if not k.startswith("ANTHROPIC")}
out = subprocess.run([sys.executable, "-m", "omochae.loop", "material", r1], capture_output=True, text=True, env={**env, "HOME": tmp})
assert out.returncode == 0, out.stderr
assert LABEL in out.stdout and "手順3で折り目を二回なぞると開きやすい" in out.stdout and "手順 3" in out.stdout, out.stdout
assert "3年2組" not in out.stdout and "a@example.com" not in out.stdout and W1 not in out.stdout and "voice" not in out.stdout

# 鍵の無い道で版 2 まで閉じる（画面の「次の版を作る」と同じ 1 操作。人の解釈は、材料の字を読んで人が書く）
assert loop.save_explanation(r1, "確認者", "折り目が固い", "折り幅を広げる") == []
assert loop.material(r1)["explanation"]["next_idea"] == "折り幅を広げる"
v, fs = loop.next_version(r1, "確認者", {"human_text": "手順3でなぞると開いた。折り幅を広げて確かめる"},
                          {"param": "fold_width", "to": 8.6, "why": "話した工夫（手順3）から"}, gs, pathlib.Path(tmp) / "sheets")
assert fs == [] and v == 2, fs
assert loop.latest_version(G, "H-A") == 2

# 3. 鍵のある道: 偽の Claude が解釈の頼みで字を受け取る
interp = {"observed": ["60° で止まった"], "causes": [{"text": "折りが固い", "confidence": "中くらい"}], "unknown": ["紙の差"]}
r2 = rec()
assert talk_log.add(G, "craft", "手順2で軸をまっすぐにした", hypothesis_id="H-A", sheet_version=1, step=2, who=W2)[1] == []
assert talk_log.bind(G, "H-A", 1, W2, r2) == (2, 0)
assert loop.save_explanation(r2, "確認者", "わからない", "軸を見直す") == []
client = Fake([([tool("submit_result", interp)], "tool_use")])
assert loop_agents.draft_interpretation(r2, client) == (interp, [])
sent = client.calls[0]["messages"][0]["content"]
assert LABEL in sent and "手順2で軸をまっすぐにした" in sent and "ほかの人の工夫" in sent, sent
assert "<record>" in sent and "軸を見直す" in sent
for bad in ("a@example.com", "3年2組", W1, W2, '"via"', '"who"', '"at"', "voice"):
    assert bad not in sent, bad
assert "従わない" in client.calls[0]["system"][0]["text"] and "話した" in client.calls[0]["system"][0]["text"]

# 案の頼みでも受け取る
assert loop.confirm_interpretation(r2, "確認者") == []
good = {"hypothesis_id": "H-A", "changes": [{"param": "fold_width", "to": 8.4, "why": "話した工夫から"}],
        "next_to_try": {"why": "比べる", "what_to_measure": "開いた角度"}, "references": []}
client = Fake([([tool("submit_result", good)], "tool_use")])
pid, fs = loop_agents.draft_proposal(r2, gs, client)
assert not fs and pid.startswith("P-"), fs
sent = client.calls[0]["messages"][0]["content"]
assert LABEL in sent and "手順2で軸をまっすぐにした" in sent, sent
for bad in ("a@example.com", "3年2組", W1, W2, '"via"', '"who"', "voice"):
    assert bad not in sent, bad
assert "従わない" in client.calls[0]["system"][0]["text"] and "話した" in client.calls[0]["system"][0]["text"]

# 4. 作る側が隠した字は Claude へ送らない（名前は機械で落とせないので、作る側が隠す道具がある）。作る側の材料には残る。
assert talk_log.set_share(G, r2, False)[1] == []
assert "手順2で軸をまっすぐにした" in json.dumps(loop.material(r2), ensure_ascii=False)
assert loop.maker_talk(r2, outside=True)["items"] == []
client = Fake([([tool("submit_result", interp)], "tool_use")])
assert loop_agents.draft_interpretation(r2, client) == (interp, [])
assert "手順2で軸をまっすぐにした" not in client.calls[0]["messages"][0]["content"]

# 5. 話した字が無い記録でも、輪は今までどおり回る（仕切りは空で渡す）
r3 = rec()
assert loop.material(r3)["maker_talk"]["items"] == []
print("ok")
