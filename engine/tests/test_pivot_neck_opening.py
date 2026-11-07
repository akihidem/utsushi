"""首の形（neck）: 首の帯が前の壁の丸い穴を通り、MIN_SWING まで揺れても縁に当たらない事。

穴は丸い（実物の写真の直し A。前は四角）。帯は穴の真ん中の縦の列を通るので、縦に使える長さは丸でも直径のままで、式は変わらない。

なぜ: 帯の面は軸に直交するので、帯の幅は穴の中で縦に並ぶ。幅 20mm の帯は 10mm 角の穴を通れない。
軸は壁の 6mm 後ろ。θ 傾くと、壁の所で帯の中心は 6·tanθ 動き、帯の縦の幅は sw/cosθ に広がる。
"""
from omochae.templates.pivot_counterweight import DEFAULTS, check_physics


def neck_fail(**kw):
    return [f for f in check_physics({**DEFAULTS, "mount": "neck", **kw}) if f.where == "首"]


assert neck_fail(opening=10, strip_width=20), "帯が穴より広い"
assert neck_fail(opening=10, strip_width=10), "幅が同じでは揺れられない"
# 穴 10 の半分は 5。帯 8mm: 6·tan10° + 8/(2·cos10°) = 1.06 + 4.06 = 5.12 > 5 で当たる。帯 7mm: 1.06 + 3.55 = 4.61 ≦ 5 で揺れる
assert neck_fail(opening=10, strip_width=8)
assert not neck_fail(opening=10, strip_width=7)
assert not neck_fail(), "既定（穴 18・帯 10）は通る"
print("ok")
