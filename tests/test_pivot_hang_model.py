"""吊る形（hang）: 式が使う寸法と、刷る部品・手順が同じ物を指す事（レビュー指摘）。

- 軸の高さ: 刷る耳の穴は胴の上の縁から HOLE_MARGIN 下にある。axle_height が別の値なら式と実物がずれる
- 軸から頭の上の端まで: 帯の穴から帯の下の端までの長さから、頭と重ねる糊代を引いた長さ。手順に重ねる長さを刷る
- 重り: 式は軸の下 weight_below_axle に置く。手順に頭の上の端からの位置を刷り、頭の外なら貼れないので落とす
"""
from omochae.templates.pivot_counterweight import DEFAULTS, HOLE_MARGIN, axle_to_head_top, check_physics, parts, steps

hang = {**DEFAULTS, "mount": "hang", "axle_height": 50, "weight_below_axle": 28}
assert not check_physics(hang), [f.line() for f in check_physics(hang)]

# 軸の高さ: 刷る穴の高さ（胴の下の縁からの高さ）と式の値が合う
H = hang["body_height"]
body = next(q for q in parts(hang) if q.key == "body")
ys = sorted(y for _, y, _ in body.holes)
top1 = hang["glue"] + hang["body_width"]
assert H - (ys[0] - top1) == H - HOLE_MARGIN == hang["axle_height"]
off = {**hang, "axle_height": 40}
assert any(f.floor == "F5.pivot" and "耳の穴" in f.message for f in check_physics(off)), "式の軸の高さが刷る穴と違えば落とす"

# 軸から頭の上の端まで: 帯の穴 → 帯の下の端 − 重ねる長さ
strip = next(q for q in parts(hang) if q.key == "strip")
hole_y = strip.holes[0][1]
length = max(y for _, y in strip.outline)
text = " ".join(steps(hang))
import re

m = re.search(r"(\d+)mm 重ねて", text)
assert m, text
assert length - hole_y - int(m.group(1)) == axle_to_head_top(hang)

# 重り: 手順に頭の上の端からの距離を刷り、頭の外なら落とす
assert f"頭の上の端から {hang['weight_below_axle'] - axle_to_head_top(hang):g}mm" in text, text
below = {**hang, "weight_below_axle": 45}
assert any(f.floor == "F5.pivot" and "頭" in f.where + f.message and "貼れない" in f.message for f in check_physics(below)), [f.line() for f in check_physics(below)]
print("ok")
