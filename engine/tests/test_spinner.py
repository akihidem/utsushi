"""雛形 spinner の床（F5.spin）の式の要所を、数点で確かめる。向きを言葉で決めると間違えやすいので、ここで数える。"""
import math

from omochae.floors import check_bom, check_holes
from omochae.templates import spinner as s


def P(**kw):
    return {**s.DEFAULTS, **kw}


def floors(**kw):
    return [f.where for f in s.check_physics(P(**kw))]


# 既定の寸法は、どの形でも床を通り、部品は全部部品表に載り、穴は紙の中にある
for k in s.KINDS:
    p = P(kind=k)
    assert s.check_physics(p) == [], (k, s.check_physics(p))
    assert check_bom(s.bom(p), s.parts(p)) == [], k
    assert check_holes(s.parts(p)) == [], k

# 風車: 羽の傾きは穴の隙間 / 2 か所の間。隙間が広いか間が短いほど羽が柄に寄る
assert abs(s.wobble_deg(P(hole_d=3.6, axle_d=3.0, bearing=10)) - math.degrees(math.atan(0.06))) < 1e-9
assert s.need_spacer(P(bearing=4)) > s.need_spacer(P(bearing=20))
assert "羽" in floors(spacer=4) and floors(spacer=9) == []
# 四角の羽はねじった分だけ後ろへ出るので、同じ間でも当たる
assert s.need_spacer(P(kind="square")) - s.need_spacer(P(kind="pinwheel", square=s.wheel_radius(P(kind="square")) * math.sqrt(2))) > 10
# 穴と軸の隙間が無いと回らない。穴の余白が無いと裂ける
assert "軸の穴" in floors(hole_d=3.1)
assert "中心の穴" in floors(uncut=5) and "中心の穴" not in floors(uncut=6)
# 角の穴は両側の辺まで穴の縁から HOLE_MARGIN 取れる所に置く（風車の角の尖りは 45°）
vanes = s.parts(P())[0]
a = s.tip_hole_dist(P())
x, y, r = vanes.holes[1]  # 右上の角 (S, 0) の穴
assert abs(y - r - s.HOLE_MARGIN) < 1e-9 and abs(math.hypot(s.DEFAULTS["square"] - x, y) - a) < 1e-9
assert abs(a * s.SIN_HALF - r - s.HOLE_MARGIN) < 1e-9
# 羽が手に当たる
assert "柄" in floors(square=180, stick_length=180)
# 四角の羽: 隣の羽が重なる・腕が短い
# 隣の羽が重なるかは、刷る菱形どうしの実際の間で見る（対角線の幅で見ると、間が 3.85mm 空く vane_radius 46 まで落とした）。
# 羽の一辺 24 では、菱形の間が VANE_GAP の 2mm になる境は vane_radius ≒ 43.6
assert floors(kind="square", vane_radius=46) == [] and floors(kind="square", vane_radius=44) == []
assert "羽" in floors(kind="square", vane_radius=43)
assert "羽" in floors(kind="square", vane_radius=38, hub_r=10, spoke_w=3)  # 菱形が重なる（負の場面 neg3）
assert "腕" in floors(kind="square", hub_r=25, spoke_w=10)

# 独楽: 1 枚では軽く、軸の重さで重心が上がって倒れやすい。重ねると通る
w1, l1 = s.top_omega_min(P(kind="top", layers=1))
w3, l3 = s.top_omega_min(P(kind="top", layers=3))
assert w1 > s.OMEGA_HAND * s.SLEEP_RATIO >= w3 and l1 > l3
assert "独楽" in floors(kind="top", layers=1)
# 軸の重さを 0 にした時は、円盤だけの式 4·sqrt(g·l·(R²/4 + l²)) / R² に戻る（式の向きの確かめ）
p = P(kind="top")
old = s.WOOD_DENSITY
s.WOOD_DENSITY = 0.0
w0, l0 = s.top_omega_min(p)
s.WOOD_DENSITY = old
R = p["disc_r"]
h = p["layers"] * s.thickness(p)
assert abs(w0 - 2 * math.sqrt(s.G * l0 * (R * R / 4 + h * h / 12 + l0 * l0)) / (R * R / 2)) < 1e-9
# 下の軸が長いほど倒れやすい。円盤が大きいほど倒れにくい
assert s.top_omega_min(P(kind="top", tip=20))[0] > s.top_omega_min(P(kind="top", tip=8))[0]
assert s.top_omega_min(P(kind="top", disc_r=40))[0] < s.top_omega_min(P(kind="top", disc_r=20))[0]
assert "独楽" in floors(kind="top", tip=25)
# 下の軸が短いと、少し傾いただけで縁が床に付く
assert "下の軸" in floors(kind="top", tip=3)
# 軸が重心を通る: 刷った円盤の重心と穴の中心の距離を数える
assert s.disc_com_offset(P(kind="top")) < 1e-6
assert abs(s.disc_com_offset(P(kind="top", hole_offset=2)) - 2) < 0.05
assert "円盤" in floors(kind="top", hole_offset=2) and floors(kind="top", hole_offset=0.4) == []
# 部品表に重ねる枚数を書く。刷る円盤も同じ枚数
p = P(kind="top", layers=4)
assert len(s.parts(p)) == 4 and all("4 枚重ねる" in r["name"] for r in s.bom(p) if r["key"].startswith("disc"))

# 円錐の独楽: 円錐の殻の質量と慣性モーメントを足す。円錐が高いほど円盤が上がり、倒れやすい
assert s.top_omega_min(P(kind="cone", cone_h=20))[0] > s.top_omega_min(P(kind="cone", cone_h=10))[0]
mc, zc, i3c, i1c = s.top_parts_mass(P(kind="cone"))[2]
q = P(kind="cone")
assert abs(zc - (q["cone_tip"] + 2 * q["cone_h"] / 3)) < 1e-9 and abs(i3c - mc * q["cone_r"] ** 2 / 2) < 1e-9
# 扇形の角は 2πR/s。平らすぎると糊代を足して一回りを超える
a, g = s.cone_angles(q)
assert abs(a - 2 * math.pi * q["cone_r"] / math.hypot(q["cone_r"], q["cone_h"])) < 1e-9
assert "円錐" in floors(kind="cone", cone_h=5) and "円錐" not in floors(kind="cone", cone_h=10)
assert "独楽" in floors(kind="cone", cone_tip=25)
# 扇形の内の弧は、丸めると軸の太さの口になる（内の半径 × R/s ＝ 軸の半径）
cone = next(x for x in s.parts(q) if x.key == "cone")
ri = min(math.hypot(x - cone.width / 2, y - cone.width / 2) for x, y in cone.outline)
assert abs(ri * q["cone_r"] / math.hypot(q["cone_r"], q["cone_h"]) - q["axle_d"] / 2) < 0.05, ri
# 車屏風: 屏風の重さが車の張り出しを支える。車を遠く・重くすると前へ倒れる
back, front = s.screen_moment(P(kind="screen"))
assert front < back
assert "屏風" in floors(kind="screen", wheel_gap=30, layers=6)
# 車が机に当たる・車が前の面に当たる
assert "車" in floors(kind="screen", panel_h=60) and "車" in floors(kind="screen", wheel_gap=2)
# 2 つの穴は、コの字に折った時に向かい合う（同じ高さで、3 の面の折り線から同じ距離）
scr = next(x for x in s.parts(P(kind="screen")) if x.key == "screen")
(x1, y1, _), (x2, y2, _) = scr.holes
(f2, _), _ = scr.valley[0]
(f3, _), _ = scr.valley[1]
assert y1 == y2 and abs((f2 - x1) - (x2 - f3)) < 1e-9
# 穴の上に絵の塗りを置かない（紙の風車の中心の輪が塗りの円になり、穴の線が墨に埋もれて見えなかった）。どの形のどの部品でも、
# 絵の面が穴の円にかからない
from shapely.geometry import Point, Polygon
for k in s.KINDS:
    for q in s.parts(P(kind=k)):
        for x, y, r in q.holes:
            disc = Point(x, y).buffer(r, 32)
            for item in q.art:
                if item["kind"] == "poly":
                    assert Polygon(item["pts"]).intersection(disc).area < 1e-6, (k, q.key, item["fill"])
# 出典は形ごとに持つ（形と合わない出典の印を刷らない）
assert set(s.SOURCES) == set(s.KINDS) and s.SOURCES[s.DEFAULTS["kind"]] == s.SOURCE
print("ok")
