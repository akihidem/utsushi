"""内筒を下から押す形（tube）で、押し上げる量が外筒の高さを超えない事（レビュー指摘、F5.stroke に足す）。

なぜ: 静止時の内筒の上の端は、外筒の底から 高さ − 押し上げる量 の所。量が高さを超えると、上の端（扇の台）が外筒の下へ出て、扇が筒に入らない。
"""
from omochae.templates.slider_fan import DEFAULTS, check_physics

p = {**DEFAULTS, "push_part": "tube", "hub": "axle", "tube_height": 50, "push_amount": 90, "pusher_height": 50}
fs = [f for f in check_physics(p) if f.floor == "F5.stroke"]
assert fs and any("押し上げる量" in f.message for f in fs), [f.line() for f in check_physics(p)]
ok = {**DEFAULTS, "push_part": "tube", "hub": "axle", "pusher_height": 84}
assert not check_physics(ok), [f.line() for f in check_physics(ok)]
print("ok")
