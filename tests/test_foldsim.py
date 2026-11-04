"""Origami Simulator への書き出し（research/22 の候補 5）。山は赤・谷は青・外形は黒で、折り線の数が部品と合う。"""
import tempfile

from omochae.foldsim import export
from omochae.templates.slider_fan import DEFAULTS, parts

out = export("NDL-1187053-R0000005-L", "H-A", tempfile.mkdtemp())
names = sorted(f.name for f in out)
assert names == ["H-A_fan_foldsim.svg", "H-A_tube_foldsim.svg"], names
fan = next(q for q in parts({**DEFAULTS, "push_part": "tab", "hub": "axle", "pusher_height": 15}) if q.key == "fan")
svg = next(f for f in out if "fan" in f.name).read_text(encoding="utf-8")
assert svg.count("#ff0000") == len(fan.mountain) and svg.count("#0000ff") == len(fan.valley)
assert svg.count("#000000") == len(fan.outline)
print("ok")
