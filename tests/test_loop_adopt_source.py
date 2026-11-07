"""採る時の再検査は、提案に書かれた出典で行う（レビュー指摘［中］）。命令の --source の既定に引きずられない。

なぜ: 命令の --source の既定は御来迎。虎の提案を --source なしで採ると、御来迎の雛形で虎の寸法を検査してしまう。
"""
import json
import os
import pathlib
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
from omochae import loop, records

ROOT = pathlib.Path(__file__).resolve().parents[1]
G, T = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"
gs = json.loads((ROOT / "data/sources" / f"{G}.json").read_text(encoding="utf-8"))
ts = json.loads((ROOT / "data/sources" / f"{T}.json").read_text(encoding="utf-8"))
# 変える値は、虎の今の組（tora-v6）の重りの深さ 20 と違い、床に通る 18（前の組の寸法の時は 20 だった）
tr, fs = records.add({"source_id": T, "hypothesis_id": "H-A", "sheet_version": 1, "result": "揺れた", "fixes": [], "note": "揺れた"})
assert not fs, fs
assert loop.save_explanation(tr, "確認者", "わからない", "重りを下げる") == []
assert loop.confirm_interpretation(tr, "確認者", {"human_text": "揺れた"}) == []
pid, fs = loop.save_proposal({"record_ids": [tr], "hypothesis_id": "H-A", "changes": [{"param": "weight_below_axle", "to": 18, "why": "速くする"}]}, ts, "human")
assert not fs, [f.line() for f in fs]
# 命令の main と同じく、--source の既定（御来迎）を渡して採る
made, fs = loop.adopt(pid, "確認者", ["weight_below_axle"], False, gs)
assert not fs, [f.line() for f in fs]
assert made == {"version": 2}, made
print("ok")
