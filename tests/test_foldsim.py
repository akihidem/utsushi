"""Origami Simulator への書き出し（research/22 の候補 5）。山は赤・谷は青・外形は黒で、折り線の数が部品と合う。

既定では折りのある部品を全部書く（レビュー指摘: 扇と外筒に固定していて、台・内筒、虎の胴・帯が出なかった）。parts で絞れる。
"""
import tempfile

from omochae import hypotheses
from omochae.foldsim import export
from omochae.templates import pivot_counterweight, slider_fan


def check(out, tpl, params, hid):
    by_key = {q.key: q for q in tpl.parts({**tpl.DEFAULTS, **params})}
    for f in out:
        key = f.name[len(hid) + 1:-len("_foldsim.svg")]
        q, svg = by_key[key], f.read_text(encoding="utf-8")
        assert svg.count("#ff0000") == len(q.mountain) and svg.count("#0000ff") == len(q.valley), key
        assert svg.count("#000000") == len(q.outline), key
    return sorted(f.name for f in out)


ha = {"push_part": "tab", "hub": "axle", "pusher_height": 15}
names = check(export("NDL-1187053-R0000005-L", "H-A", tempfile.mkdtemp()), slider_fan, ha, "H-A")
assert names == ["H-A_base_foldsim.svg", "H-A_fan_foldsim.svg", "H-A_pusher_foldsim.svg", "H-A_tube_foldsim.svg"], names
# 虎は今の組（tora-v6）の寸法で書く（記録の組ごとの寸法）。両面の頭・尾・立体の脚 4 本にも折りがある。丸い首の穴は書かない
# （この書き出しは中の切り込みを書かない。矩形の切り込みも同じ）
tora = hypotheses.sheet_of("NDL-1187053-R0000014-R")["params"]
names = check(export("NDL-1187053-R0000014-R", "H-A", tempfile.mkdtemp()), pivot_counterweight, tora, "H-A")
assert names == [f"H-A_{k}_foldsim.svg" for k in ("body", "head", "leg1", "leg2", "leg3", "leg4", "strip", "tail")], names
only = export("NDL-1187053-R0000005-L", "H-A", tempfile.mkdtemp(), parts=("fan",))
assert [f.name for f in only] == ["H-A_fan_foldsim.svg"]
print("ok")
