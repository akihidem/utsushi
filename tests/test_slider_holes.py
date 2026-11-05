"""糸と軸の穴が紙の中にある事（レビュー指摘、F5.hole）。

なぜ: 開く糸の穴は扇の要から THREAD_RADIUS（35mm）の所に開ける。折りの高さは 20mm まで許すので、低い扇では穴が紙の外になる
像の穴は足元から pivot_above_rim の高さで、像より高いと紙の上に出る。どちらも刷っても作れない型紙になる。
"""
from omochae.floors import check_holes
from omochae.templates.slider_fan import DEFAULTS, parts

base = {**DEFAULTS, "hub": "axle"}
assert not check_holes(parts(base))
low = {**base, "fold_height": 30, "push_amount": 69}
fs = check_holes(parts(low))
assert fs and any(f.where == "蛇腹の扇" and f.floor == "F5.hole" for f in fs), [f.line() for f in fs]
tall = {**base, "pivot_above_rim": 36, "figure_h": 30, "push_amount": 90, "tube_height": 110}
fs = check_holes(parts(tall))
assert fs and any(f.where == "像" and f.floor == "F5.hole" for f in fs), [f.line() for f in fs]
# 台に載せる形（rim）は糸の穴を開けないので、低い扇でも落とさない
assert not check_holes(parts({**DEFAULTS, "hub": "rim", "fold_height": 20}))
print("ok")
