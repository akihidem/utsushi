"""提案の根拠の記録は、提案の出典と同じ玩具の物だけ（レビュー指摘、F8.references）。

なぜ: 別の玩具の記録でも、仮説 ID（H-A など）が偶然そろえば寸法の変更の根拠として通ってしまう。
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
tr, fs = records.add({"source_id": T, "hypothesis_id": "H-A", "sheet_version": 1, "result": "揺れた", "fixes": [], "note": "揺れた"})
assert not fs, fs
assert loop.save_explanation(tr, "確認者", "わからない", "重りを減らす") == []
assert loop.confirm_interpretation(tr, "確認者", {"human_text": "揺れた"}) == []
_, fs = loop.save_proposal({"record_ids": [tr], "hypothesis_id": "H-A", "changes": [{"param": "fold_width", "to": 8, "why": "x"}]}, gs, "human")
assert {f.floor for f in fs} == {"F8.references"}, [f.line() for f in fs]
assert any("出典" in f.message for f in fs), [f.line() for f in fs]
print("ok")
