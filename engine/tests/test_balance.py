"""釣り合いの床（F5.balance）の式の要所を数点で確かめる。重心の向き（上か下か）は言葉で決めると間違えやすいので、ここで数える。"""
import math

from shapely.geometry import Polygon

from omochae.compose import TEMPLATES
from omochae.pivot_model import center, rest_tilt_deg
from omochae.templates import balance as t

Y = {**t.DEFAULTS, "kind": "yajirobe"}
O = {**t.DEFAULTS, "kind": "okiagari"}
assert TEMPLATES["balance"] is t, "templates/ に置けば登録される"
for p in (Y, O):
    assert t.check_physics(p) == [] and not t.check_range(p), t.check_physics(p)

# --- 弥次郎兵衛
# 既定の腕では、重心は支点（V の先）の下にある。紙の体（表裏 2 枚）は玉 1 つより軽い
_, z, total = center(t.yajirobe_points(Y))
assert z > t.MIN_DROP and t.yajirobe_points(Y)[0][0] < Y["ball_g"]
# 腕を下へ向けるほど重心が下がる
zs = [center(t.yajirobe_points({**Y, "arm_angle": a}))[1] for a in (20, 40, 60, 80)]
assert zs == sorted(zs), zs
# 腕を水平近くに上げると重心が支点の上に来て、F5.balance の重心で落ちる
fs = t.check_physics({**Y, "arm_angle": 15, "arm_length": 60})
assert [(f.floor, f.where) for f in fs] == [("F5.balance", "重心")], fs
# 玉が重いほど、左右の差（CLAY_TOL）での傾きは小さい（同じ差が全体の重さに対して小さくなる）
tilt = lambda p: abs(rest_tilt_deg(t.yajirobe_points(p, t.CLAY_TOL)))
assert tilt({**Y, "ball_g": 6}) < tilt(Y) < tilt({**Y, "ball_g": 1})
# 軽い玉で浅い腕だと、左右の差で傾きすぎる
fs = t.check_physics({**Y, "ball_g": 0.5, "arm_angle": 40})
assert any(f.where == "玉" and "傾く" in f.message for f in fs), fs
# 粘土の玉の大きさ: 体積 = 重さ / 密度
assert abs(4 / 3 * math.pi * t.ball_r(3) ** 3 * t.CLAY_DENSITY - 3) < 1e-9
# 支点の先の厚み: 表裏 2 枚 + 当て紙。2 枚の当て紙では薄く落ち、6 枚なら通る
assert abs(t.tip_thickness(Y) - 8 * Y["paper_thickness"]) < 1e-12
fs = t.check_physics({**Y, "tip_layers": 2})
assert [(f.floor, f.where) for f in fs] == [("F5.balance", "支点")], fs
# 当て紙は蛇腹: 枚数 − 1 本の折り線が、谷と山で交互
tip = next(q for q in t.parts(Y) if q.key == "tip")
assert len(tip.valley) + len(tip.mountain) == Y["tip_layers"] - 1 and abs(len(tip.valley) - len(tip.mountain)) <= 1
# 差し込みが長すぎると、竹串の奥が体の外に出るか左右で交わる
fs = t.check_physics({**Y, "arm_angle": 45, "arm_insert": 40})
assert any(f.where.endswith("腕") for f in fs), fs
# 台が低いと玉が机に当たる
assert any(f.where == "台" for f in t.check_physics({**Y, "stand_h": 80}))
# 裏は刷った面を内にして表の刷っていない面と貼るので、外形は表と同じ向き（鏡にしない）
front, back = (q for q in t.parts(Y) if q.key in ("front", "back"))
assert back.outline == front.outline

# --- 起き上がり小法師
# 粘土の欠けの体積は重さと合い、重心は欠けの中（底から欠けの高さの間）
h, zc = t.clay_cap(O)
R = O["base_r"]
assert abs(math.pi * h * h * (3 * R - h) / 3 * t.CLAY_DENSITY - O["bottom_g"]) < 1e-6 and 0 < zc < h
# 半球を満たすと、重心は底から 5R/8（中身の詰まった半球の重心）
full = {**O, "bottom_g": 2 / 3 * math.pi * R ** 3 * t.CLAY_DENSITY}
assert abs(t.clay_cap(full)[1] - 5 * R / 8) < 1e-6
# 底の粘土を増やすほど重心が下がる（紙が軽い間）
assert t.com_height({**O, "bottom_g": 6}) < t.com_height(O) < t.com_height({**O, "bottom_g": 1})
# 円錐が高く粘土が少ないと、重心が丸みの中心に近づき、F5.balance の重心で落ちる
fs = t.check_physics({**O, "cone_h": 100, "bottom_g": 1})
assert [(f.floor, f.where) for f in fs] == [("F5.balance", "重心")], fs
assert t.com_height({**O, "cone_h": 100, "bottom_g": 1}) > R * (1 - t.MIN_MARGIN)
# 粘土が多すぎると底の半分に収まらない
assert any(f.where == "粘土" for f in t.check_physics({**O, "bottom_g": 30, "base_r": 15}))
# 円錐を開いた扇の弧 ＝ 底の円周。低い円錐は半円を超えて落ちる
th, _ = t.cone_angles(O)
assert abs(th * t.slant(O) - 2 * math.pi * R) < 1e-9
assert any(f.where == "円錐" for f in t.check_physics({**O, "cone_h": 20}))
# 切れの幅は赤道で円周 / 切れの数、極で 0
assert abs(2 * t.gore_half_width(O, 0) * O["gores"] - 2 * math.pi * R) < 1e-9 and abs(t.gore_half_width(O, math.pi * R / 2)) < 1e-9

# 形ごとの部品は部品表と合い、鍵が重ならない
assert {q.key for q in t.parts(Y)} == {"front", "back", "tip", "gauge"} and {q.key for q in t.parts(O)} == {"shell", "dome"}
assert {r["key"] for r in t.bom(Y)} >= {"arm", "ball", "stand"} and "weight" in {r["key"] for r in t.bom(O)}
# 置く位置に頼る床（腕の差し込み・玉の位置・底の粘土）は、型紙に印を刷り、組み方の文に位置を書く
from omochae.compose import compose
from omochae.__main__ import load_source
back = next(q for q in t.parts(Y) if q.key == "back")
tx, ty = t._yk(Y, [t._TIP])[0]
guides = [it for it in back.art if it.get("role") == "arm"]
assert len(guides) == 2, "裏に腕の竹串を置く線が 2 本"
for g, (inner, sh, _) in zip(guides, t.arm_geometry(Y)):
    (x0, y0), (x1, y1) = g["pts"][0], g["pts"][-1]
    assert abs(x0 - (inner[0] + tx)) < 1e-6 and abs(y0 - (inner[1] + ty)) < 1e-6  # 差し込みの奥の端
    assert math.hypot(x1 - (sh[0] + tx), y1 - (sh[1] + ty)) < 1.5  # 肩の角の手前まで
gauge = next(q for q in t.parts(Y) if q.key == "gauge")
assert abs(gauge.width - (Y["arm_insert"] + Y["arm_length"])) < 1e-9
marks = sorted(round(it["at"], 6) for it in gauge.art if "at" in it)
assert marks == [Y["arm_insert"], Y["arm_insert"] + Y["arm_length"]], marks
st = " ".join(t.steps(Y))
assert f"{Y['arm_insert']}mm" in st and f"{Y['arm_length']}mm" in st and "4 腕の物差し" in st
dome = next(q for q in t.parts(O) if q.key == "dome")
clay = [it for it in dome.art if it.get("role") == "clay"]
assert len(clay) == O["gores"], "切れごとに粘土の高さの線"
arc = R * math.acos(1 - t.clay_cap(O)[0] / R)  # 底の極から線までの、切れの上の長さ
assert all(abs(c["pts"][0][1] - (O["band"] + math.pi * R / 2 - arc)) < 1e-6 for c in clay)
assert f"{t.clay_cap(O)[0]:.0f}mm" in " ".join(t.steps(O))
# 形ごとの出典: 既定でない形に既定の形の出典を渡すと F1.source で落ちる
assert t.SOURCES == {"yajirobe": t.SOURCE, "okiagari": "NDL-1187053-R0000026-L-balance"}
_, _, fs = compose("balance", O, load_source(t.SOURCE))
assert [f.floor for f in fs] == ["F1.source"], fs
# 2 回目の見直し
# (1) 重ね方: 裏を刷った面を上に置き、竹串を載せ、表を刷った面を上にしたまま（刷っていない面を下に）重ねる。
#     どちらも上から見えるのは刷った面なので、外形は同じ向きで重なる（鏡にすると左右が逆になってずれる）。
#     表を裏返さない事を組み方の文に書く（裏返すと、刷った奴の絵が内に隠れる）。
mirrored = [(Y["body_w"] - x, y) for x, y in front.outline]
assert back.outline == front.outline and Polygon(mirrored).symmetric_difference(Polygon(back.outline)).area > 1, "奴は左右が非対称で、鏡にすると重ならない"
assert any("裏返さない" in s_ for s_ in t.steps(Y)), t.steps(Y)
# (2) 机に当たるか: 振れの途中で玉の中心は支点から d 近くまで下がる。休む時の高さだけでは見逃す
p2 = {**Y, "stand_h": 110}
arms = t.arm_geometry(p2)
assert max(b[1] for _, _, b in arms) + t.ball_r(p2["ball_g"]) < p2["stand_h"] - t.TABLE_CLEAR  # 休む時は当たらない
assert any(f.where == "台" for f in t.check_physics(p2)), t.check_physics(p2)
# (3) 肩は左右で非対称なので、台の串に当たるまでの振れは左右とも見る（右 21.9°・左 19.9° の寸法）
fs = t.check_physics({**Y, "arm_length": 61, "arm_angle": 85})
assert any(f.where == "左の玉" and "振れない" in f.message for f in fs), fs
# (4) 起き上がりの図の外形は、自分と交わらない 1 本の道（赤道の横の線を余分に引かない）
shape = t.diagram(0, 0, 50, 80, O)[0]["pts"]
assert Polygon(shape).is_valid, "図の外形が自分と交わる"
print("ok")
