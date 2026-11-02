"""振り子の式の向きを数点で確かめる。言葉で書いた直す向きは間違えやすいので、ここで数える。"""
from omochae.pivot_model import center, period_s, rest_tilt_deg
from omochae.templates.pivot_counterweight import DEFAULTS, check_physics, mass_points

base = [(0.1, 20, 0), (3.0, 0, 20)]
far = [(0.1, 20, 0), (3.0, 0, 40)]
assert period_s(far) > period_s(base), "重りが軸から遠いほど周期が長い"
heavy = [(0.1, 20, 0), (6.0, 0, 20)]
assert abs(period_s(heavy) - period_s(base)) < 0.01, "重りの量は周期をほぼ変えない"
assert period_s([(3.0, 0, -5)]) is None, "軸より上では揺れない"
assert rest_tilt_deg([(0.1, 20, 0), (3.0, 0, 20)]) < 2
# 紙の頭は重りより桁で軽いので、後ろの腕の重りで釣り合わせると大きく傾く
seesaw = dict(DEFAULTS, weight_behind=28, weight_below_axle=5, weight_g=1.0)
assert any("傾く" in f.message for f in check_physics(seesaw))
assert mass_points(DEFAULTS)[0][0] < 0.2 and not check_physics(DEFAULTS)
print(round(period_s(mass_points(DEFAULTS)), 2))
