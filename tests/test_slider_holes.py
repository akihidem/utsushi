"""糸と軸の穴が紙の中にある事（レビュー指摘、F5.holes）。

なぜ: 開く糸の穴は扇の要から THREAD_RADIUS（35mm）の所に開ける。折りの高さは 20mm まで許すので、低い扇では穴が紙の外になる。
像の穴は足元から pivot_above_rim の高さで、像より高いと紙の上に出る。どちらも刷っても作れない型紙になる。
"""
from omochae.templates.slider_fan import DEFAULTS, THREAD_RADIUS, check_physics

base = {**DEFAULTS, "hub": "axle"}
assert not [f for f in check_physics(base) if f.floor == "F5.holes"]
low = {**base, "fold_height": 30, "push_amount": 69}
fs = [f for f in check_physics(low) if f.floor == "F5.holes"]
assert fs and any(f.where == "蛇腹の扇" for f in fs), [f.line() for f in check_physics(low)]
tall = {**base, "pivot_above_rim": 36, "figure_h": 30, "push_amount": 90, "tube_height": 110}
fs = [f for f in check_physics(tall) if f.floor == "F5.holes"]
assert fs and any(f.where == "像" for f in fs), [f.line() for f in check_physics(tall)]
# 台に載せる形（rim）は糸の穴を開けないので、低い扇でも落とさない
assert not [f for f in check_physics({**DEFAULTS, "hub": "rim", "fold_height": 20}) if f.floor == "F5.holes"]
print("ok")
