"""虎 v7（examples/tora_v7.json）の当たりの直し。制作者の決定（2026-11-07）「虎 v6 の当たり2つ（粘土の玉が前の壁・頭の角が腕）は、
v7 で今直してください。撮影は v6 のまま。」と、その後の制作者の言葉「エンジンは3D組み立て検品を自分でする」・決める側の決定
（±10° の揺れで当たらない直しをそのまま進める）による。

3D の JSON をサイトの試験で描いて、v6 の寸法で 2 つの当たり（粘土の玉が前の壁へ約 1.4mm・頭の後ろの端が前の壁の 4mm 内で腕と重なる）が
見つかった。見直しで、揺れると当たる事も分かった（v7 の初めの寸法で、粘土の玉は頭が約 3° 上がると、5 重りの腕は約 5° 上がると前の壁に当たる。
腕は v6 から）。静かな時は重心が軸の真下に来るので、下の穴を後ろへ刷っても玉は軸の下へ戻る。なので軸を前の壁から離して（axle_back）直す。次を見る:
1. v7 は v6 から 5 つだけ（首の帯 14 → 23mm・粘土の下の穴を軸の 2.5mm 後ろ・軸を前の壁の 9mm 後ろ・式の粘土のずれ 0・当たりの検査 1）。
   検査を全部通り、型紙も刷れる。
2. 当たりの検査（F5.pivot）: 頭が静かな時の傾きから ±10° 揺れる間、粘土の玉・5 重りの腕・頭が前の壁から、首の帯が穴の縁から 0.5mm 以上離れる。
   - v6 の寸法に検査だけを入れると 4 行で落ちる（式の粘土のずれ・玉・腕・頭）。
   - 境の両側: 軸 8mm（玉と腕が落ちる）と 9mm、首の帯 22mm（頭が落ちる。静かな時の傾きだけなら通る＝揺れで落ちる）と 23mm。
   - 揺れの角は静かな時の傾きのまわり。水平のまわりで見ると、下の穴を後ろへ刷るだけの寸法が通ってしまう（実物は静かな時に頭が上を向き、玉が戻る）。
   - 揺れる間の一番前・一番後ろの式（_sweep_x）は、細かく回した値と同じ。
   - 首の帯は、揺れの両端のうち水平から遠い方で見る（穴 14mm は、水平から ±10° の一般の検査は通るが、ここで落ちる）。
   - 既定（fit_check 0）では検査しない。v7 の寸法（clay_back・axle_back）を既定から変えると、fit_check 0 でも見る。fit_check は選ぶ値。
     吊る形には clay_back・axle_back・fit_check を使えない（落とす）。
3. 刷る物: 胴の軸の穴・竹串の線・首の後ろの黒い斑は、軸を離した 3mm だけ後ろ（ほかの胴の形は同じ）。縞は黒い斑と重ならず、
   軸と同じだけ動く（小数の 0.5mm でも）。腕は幅 10.5mm（後ろへだけ広げる）、
   上の穴は前の端から 4mm、下の穴は 2.5mm 後ろ、粘土の線、札。広い腕は帯の下に置く。v6 の腕は前の所。
4. 組み方の文: v7 だけ、腕の向き（下の穴が後ろの尾の側）を言う。用意する物は v6 と同じ。揺れの式の粘土は軸の 2.5mm 後ろ（刷る穴と同じ）。
   吊る形の式に clay_back は効かない。
5. 3D（omochae.assembly3d）: できあがりと、できあがりの動きのどの姿でも、粘土の玉・腕・頭が前の壁から 0.5mm 以上離れる。さらに、
   できあがりの形を軸のまわりに、静かな時の傾きから ±10° まで 0.5° ずつ回しても同じ（型紙の式と別に、3D の面の形で確かめる）。
   首の帯が前の壁の面を通る所も、穴の縁から型紙の式と同じだけ離れる。
   同じ確かめで、v6 の 3D は当たる（確かめが空でない事の負の対照）。
"""
import json
import math
import pathlib
import random

from shapely.geometry import Polygon

from omochae.__main__ import load_source
from omochae.assembly3d import build
from omochae.compose import compose
from omochae.templates import pivot_counterweight as pc

ROOT = pathlib.Path(__file__).resolve().parents[1]
ex = {n: json.loads((ROOT / f"examples/{n}.json").read_text(encoding="utf-8")) for n in ("tora_v6", "tora_v7")}
v6, v7 = (dict(pc.DEFAULTS, **ex[n]["params"]) for n in ("tora_v6", "tora_v7"))
src = load_source(ex["tora_v7"]["source_id"])
lines = lambda q: [f.line() for f in pc.check_physics(q)]
tags = lambda q: [x.split("] ")[0].split("[")[1] for x in lines(q)]  # 落ちた行の [所]
r = pc.clay_r(v7["weight_g"])
T = math.radians(pc.MIN_SWING)

# 1. v6 から 5 つだけ。検査を通り、刷れる
assert ex["tora_v7"]["params"] == dict(ex["tora_v6"]["params"], neck_length=23, clay_back=2.5, axle_back=9, weight_behind=0, fit_check=1)
assert pc.check_range(v7) == [] and lines(v7) == [] and not compose("pivot_counterweight", v7, src)[2]
gaps = pc.fit_gaps(v7)
assert min(gaps) >= pc.FIT_CLEAR + 0.4, gaps  # 一番狭い所でも、残す空き 0.5mm の上に 0.4mm 以上（玉 1.0・腕 1.4・頭 1.0・首 2.1）

# 2. 当たりの検査
assert lines(v6) == []  # v6 は検査しない（撮影中の紙のまま刷れる）
fit6 = lines(dict(v6, fit_check=1))
assert tags(dict(v6, fit_check=1)) == ["重り", "重り", "腕", "頭"], fit6
assert "揺れの式の粘土（軸の 1mm 後ろ）が、刷る下の穴（軸の 0mm 後ろ）と違う" in fit6[0], fit6
assert f"±{pc.MIN_SWING}° 揺れる間に、粘土の玉（半径 {r:.1f}mm）が前の壁に当たる" in fit6[1], fit6
assert "5 重りの腕の前の端が前の壁に当たる" in fit6[2] and "頭の後ろの端が前の壁に当たる" in fit6[3], fit6
assert tags(dict(v7, axle_back=8)) == ["重り", "腕"] and tags(dict(v7, axle_back=9)) == []
assert tags(dict(v7, neck_length=22)) == ["頭"] and tags(dict(v7, neck_length=23)) == []
assert tags(dict(v7, weight_behind=1)) == ["重り"] and "軸の 3.5mm 後ろ" in lines(dict(v7, weight_behind=1))[0]
# 首の帯と穴の縁: 水平から ±10° の一般の検査は通る穴 14mm が、静かな時の傾きのまわりの揺れ（片方の端は約 11.2°）では空きが 0.5mm に足りない
assert pc.strip_need(v7, math.radians(pc.MIN_SWING)) <= 14 / 2 and tags(dict(v7, opening=14)) == ["首"], lines(dict(v7, opening=14))
# v7 の寸法を使えば fit_check 0 でも見る。既定と v6 は見ない
assert pc.fit_on(v7) and pc.fit_on(dict(v6, clay_back=1)) and pc.fit_on(dict(v6, axle_back=7)) and not pc.fit_on(v6) and not pc.fit_on(dict(pc.DEFAULTS))
assert tags(dict(v7, fit_check=0, axle_back=8)) == ["重り", "腕"]
# 首の帯 22mm は、静かな時の傾きだけで見れば通る（揺れる角を 0 にして見る）。落ちるのは揺れるから
keep = pc.MIN_SWING
pc.MIN_SWING = 0
try:
    assert pc.fit_gaps(dict(v7, neck_length=22))[2] >= pc.FIT_CLEAR, pc.fit_gaps(dict(v7, neck_length=22))  # 静かな時は 0.9mm 空く
finally:
    pc.MIN_SWING = keep
# 揺れの角は静かな時の傾きのまわり。下の穴を軸の 5.5mm 後ろに刷るだけ（軸は 6mm のまま）だと、水平のまわりの ±10° では玉が通るが、
# 静かな時に頭が約 8° 上を向くので、そのまわりで見ると当たる
moved = dict(v6, clay_back=5.5, weight_behind=0, fit_check=1)
t0, t1 = pc.swing_range(moved)
assert math.degrees((t0 + t1) / 2) > 8, math.degrees((t0 + t1) / 2)
level = pc._sweep_x(5.5, moved["weight_below_axle"], -T, T)[0] - r + pc.NECK_BACK
assert level >= pc.FIT_CLEAR and "重り" in tags(moved), (level, lines(moved))
# 一番前・一番後ろの式は、細かく回した値と同じ（端の角と、間で点が軸の真前・真後ろに来る角）
rng = random.Random(7)
for _ in range(500):
    x, y = rng.uniform(-40, 40), rng.uniform(-40, 40)
    a0 = rng.uniform(-0.6, 0.6)
    a1 = a0 + rng.uniform(0, 0.6)
    vals = [x * math.cos(a0 + (a1 - a0) * k / 400) - y * math.sin(a0 + (a1 - a0) * k / 400) for k in range(401)]
    lo, hi = pc._sweep_x(x, y, a0, a1)
    assert abs(lo - min(vals)) < 1e-4 and abs(hi - max(vals)) < 1e-4, (x, y, a0, a1, lo, min(vals), hi, max(vals))
assert pc.spec()["fit_check"] == pc.FIT_CHECKS == (0, 1) and "fit_check" not in pc.RANGES
for bad in (2, 0.5, True, "1"):
    assert [f.where for f in pc.check_range(dict(v7, fit_check=bad))] == ["fit_check"], bad
assert pc.DEFAULTS["clay_back"] == 0 and pc.DEFAULTS["fit_check"] == 0 and pc.DEFAULTS["axle_back"] == pc.NECK_BACK
hang = dict(pc.DEFAULTS, mount="hang", axle_height=pc.DEFAULTS["body_height"] - pc.HOLE_MARGIN)
assert lines(hang) == []
assert tags(dict(hang, clay_back=2.5)) == ["重り"] and tags(dict(hang, axle_back=9)) == ["軸"] and tags(dict(hang, fit_check=1)) == ["当たり"]

# 3. 刷る物
by = lambda q: {x.key: x for x in pc.parts(q)}
b7, b9 = by(dict(v7, axle_back=6))["body"], by(v7)["body"]
assert [h[0] - g[0] for h, g in zip(b9.holes, b7.holes)] == [3, 3] and [h[1:] for h in b9.holes] == [g[1:] for g in b7.holes]
assert b9.outline == b7.outline and b9.glue == b7.glue and b9.mountain == b7.mountain
axle = lambda b: next(a for a in b.art if a["kind"] == "mark" and a.get("mark") == "axle")["pts"]
assert [p[0] - q[0] for p, q in zip(axle(b9), axle(b7))] == [3, 3]
spot = lambda b: min(x for a in b.art if a["kind"] == "poly" and a.get("fill") == pc.INK for x, _ in a["pts"])  # 首の後ろの黒い斑
assert abs(spot(b9) - spot(b7) - 3) < 1e-9
for b in (b9, b7, by(dict(pc.DEFAULTS))["body"]):  # 縞は黒い斑に重ならない（見直しの指摘: 斑だけが動き、上の面の縞と重なった）
    ink = [Polygon(a["pts"]) for a in b.art if a["kind"] == "poly" and a.get("fill") == pc.INK]
    stripes = [Polygon(a["pts"]) for a in b.art if a["kind"] == "poly" and a.get("fill") == pc.STRIPE]
    assert ink and stripes and not any(s.intersects(k) for s in stripes for k in ink)
# 縞は軸と同じだけ動く（小数でも。見直しの指摘: 整数に丸めると、軸を 0.1mm 動かして縞が 1mm 動いた）
# （後ろの壁の縞は軸と関わらないので、軸の所を使う上の面・側面・角の面の絵で見る）
xs = lambda art: sorted(min(x for x, _ in a["pts"]) for a in art if a["kind"] == "poly" and a.get("fill") in (pc.STRIPE, pc.INK))
for draw in (lambda b: pc._top_art(0, 0, 64, 20, b), lambda b: pc._side_art(0, 0, 64, 30, False, True, b), lambda b: pc._bevel_art(0, 0, 64, 5, b)):
    s60, s65 = xs(draw(6)), xs(draw(6.5))
    assert s60 and len(s60) == len(s65) and all(abs(b - a - 0.5) < 1e-9 for a, b in zip(s60, s65)), (s60, s65)
drop6, drop7 = by(v6)["drop"], by(v7)["drop"]
assert drop6.width == pc.DROP_W and abs(drop7.width - (pc.DROP_W + 2.5)) < 1e-9 and drop7.outline == pc.drop_outline(v7)
assert drop7.holes[0] == (4, 4, 1.0) and abs(drop7.holes[1][0] - 6.5) < 1e-9 and abs(drop7.holes[1][1] - (4 + v7["weight_below_axle"])) < 1e-9
marks = [a for a in drop7.art if a["kind"] == "mark" and a.get("mark") == "weight"]
assert len(marks) == 2 and marks[0]["pts"][0][0] == 0.6 and abs(marks[1]["pts"][1][0] - (drop7.width - 0.6)) < 1e-9
assert drop7.label == "5 重りの腕" and [t for t, _, _ in drop7.label_lines] == ["5 重", "り", "の", "腕"]
_, lay7, _ = compose("pivot_counterweight", v7, src)
by7 = {q.key: q for q in lay7["parts"]}
assert by7["drop"].x == by7["strip"].x and by7["drop"].y >= by7["strip"].y + by7["strip"].height  # 帯の下
_, lay6, _ = compose("pivot_counterweight", v6, load_source(ex["tora_v6"]["source_id"]))
by6 = {q.key: q for q in lay6["parts"]}
assert by6["drop"].y == by6["strip"].y and by6["drop"].x > by6["strip"].x  # v6 は前の所（帯の右の列）

# 4. 組み方の文・用意する物・揺れの式
s6, s7 = pc.steps(v6), pc.steps(v7)
diff = [(a, b) for a, b in zip(s6, s7) if a != b]
assert len(s6) == len(s7) and len(diff) == 1 and "（下の穴が後ろの尾の側に来る向きで）" in diff[0][1] and "向き" not in diff[0][0], diff
assert pc.materials(v6) == pc.materials(v7)
assert abs(pc.mass_points(v7)[2][1] + 2.5) < 1e-12  # 刷る下の穴と同じ所
assert pc.mass_points(dict(hang, clay_back=3))[2][1] == -hang["weight_behind"]  # 吊る形の式に clay_back は効かない


# 5. 3D: できあがりと、できあがりの動きの姿で当たらない。できあがりを軸のまわりに回しても当たらない
def worst(d, q, swing=()):
    """3D の JSON の、できあがり（最後の段の最後の姿）とできあがりの動きの姿で、(玉, 腕, 頭) と前の壁の空きの一番狭い所 mm。
    swing は、できあがりの形を軸のまわりに回して足す角 rad（頭が上がる向きが正）。前の壁は胴の丸い穴のある面の x。"""
    parts = {x["key"]: x for x in d["parts"]}
    M = lambda c: [[c[col * 4 + row] for col in range(4)] for row in range(4)]
    ap = lambda m, p: tuple(m[i][0] * p[0] + m[i][1] * p[1] + m[i][3] for i in range(3))
    last = d["steps"][-1]["poses"][-1]
    front = next(x for x in parts["body"]["panels"] if x.get("inner"))
    wall = ap(M(last["parts"]["body"]["panels"][str(front["id"])]), front["poly"][0])[0]
    sx, sy = last["rods"]["skewer"]["from"][:2]
    assert abs(sx - wall - q["axle_back"]) < 0.01, (sx, wall)  # 竹串は前の壁の axle_back 後ろ
    pts = lambda pose, key: [ap(M(pose["parts"][key]["panels"][str(pn["id"])]), v) for pn in parts[key]["panels"] for v in pn["poly"]]
    turn = lambda p, a: (sx + (p[0] - sx) * math.cos(a) - (p[1] - sy) * math.sin(a), sy + (p[0] - sx) * math.sin(a) + (p[1] - sy) * math.cos(a))
    shapes = [(pts(f, "drop"), pts(f, "head"), f["balls"]["clay"]["at"]) for f in [last] + d["finale"]["poses"]]
    a0 = (pts(last, "drop"), pts(last, "head"), last["balls"]["clay"]["at"])
    shapes += [([turn(p, a) for p in a0[0]], [turn(p, a) for p in a0[1]], turn(a0[2], a)) for a in swing]
    ball = min(c[0] - pc.clay_r(q["weight_g"]) - wall for _, _, c in shapes)
    arm = min(p[0] - wall for dr, _, _ in shapes for p in dr)
    head = min(wall - p[0] for _, hd, _ in shapes for p in hd)
    return ball, arm, head


d7 = build(ROOT / "examples/tora_v7.json", commit="test")
t0, t1 = pc.swing_range(v7)
sweep = [t0 + (t1 - t0) * k / 40 for k in range(41)]  # 0.5° ずつ
got = worst(d7, v7, sweep)
assert min(got) >= pc.FIT_CLEAR - 0.01, got
assert all(abs(a - b) < 0.05 for a, b in zip(got, pc.fit_gaps(v7)[:3])), (got, pc.fit_gaps(v7))  # 型紙の式と 3D の形が同じ空きを出す


def strip_margin(d, q, swing):
    """首の帯が前の壁の面を通る所の、穴の縁までの空き mm の一番狭い所（できあがりの形を軸のまわりに swing の角だけ回した時）。"""
    parts = {x["key"]: x for x in d["parts"]}
    M = lambda c: [[c[col * 4 + row] for col in range(4)] for row in range(4)]
    ap = lambda m, p: tuple(m[i][0] * p[0] + m[i][1] * p[1] + m[i][3] for i in range(3))
    last = d["steps"][-1]["poses"][-1]
    front = next(x for x in parts["body"]["panels"] if x.get("inner"))
    wall = ap(M(last["parts"]["body"]["panels"][str(front["id"])]), front["poly"][0])[0]
    sx, sy = last["rods"]["skewer"]["from"][:2]  # 穴の真ん中は竹串の高さ
    out = q["opening"] / 2
    for a in swing:
        for pn in parts["strip"]["panels"]:
            m = M(last["parts"]["strip"]["panels"][str(pn["id"])])
            pts = [ap(m, v) for v in pn["poly"]]
            pts = [(sx + (x - sx) * math.cos(a) - (y - sy) * math.sin(a), sy + (x - sx) * math.sin(a) + (y - sy) * math.cos(a)) for x, y, _ in pts]
            for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
                if (x1 - wall) * (x2 - wall) < 0:
                    y = y1 + (y2 - y1) * (wall - x1) / (x2 - x1)
                    out = min(out, q["opening"] / 2 - abs(y - sy))
    return out


neck3d = strip_margin(d7, v7, sweep)
assert abs(neck3d - pc.fit_gaps(v7)[3]) < 0.05 and neck3d >= pc.FIT_CLEAR, (neck3d, pc.fit_gaps(v7))
clay7, sk7 = d7["steps"][-1]["poses"][-1]["balls"]["clay"]["at"], d7["steps"][-1]["poses"][-1]["rods"]["skewer"]["from"]
assert abs(clay7[0] - (sk7[0] + 2.5)) < 0.01 and abs(clay7[1] - (sk7[1] + v7["weight_below_axle"])) < 0.01, (clay7, sk7)
d6 = build(ROOT / "examples/tora_v6.json", commit="test")
t0, t1 = pc.swing_range(v6)
bad = worst(d6, v6, [t0 + (t1 - t0) * k / 40 for k in range(41)])
assert bad[0] < 0 and bad[2] < 0, bad  # v6 の 3D は、同じ確かめで玉と頭が前の壁に入る（負の対照）
print("ok 虎 v7（揺れても当たらない: 粘土の玉 %.1f・腕 %.1f・頭 %.1f・首の帯 %.1fmm。v6 は玉 %.1f・頭 %.1fmm）" % (*got, neck3d, bad[0], bad[2]))

# 虎 v8（examples/tora_v8.json）: テープを使わない新しい版。材料の前提（2026-11-07 の設計の条件。テープは樹脂の側）と、
# 制作者の言葉（2026-11-08）「対応する。」（型紙の再設計の答えへ）による。v7 の寸法に arm_hold="finger" を足しただけで、
# 重りの腕を、テープでなく指で押さえて仮に止め、帯に鉛筆で腕の位置の印を付ける。テープは作る途中の仮留めだけなので、部品の形は v7 と同じ
import json as _json
from omochae.compose import compose as _compose
from omochae.__main__ import load_source as _load
_ex = lambda n: _json.loads((ROOT / f"examples/{n}.json").read_text(encoding="utf-8"))
t7, t8 = _ex("tora_v7"), _ex("tora_v8")
assert t8["version"] == 8 and t8["params"] == {**t7["params"], "arm_hold": "finger"}, t8
assert "arm_hold" not in t7["params"]  # デモの v7 は前のまま（既定の tape）
q7, q8 = ({**pc.DEFAULTS, **t["params"]} for t in (t7, t8))
shape = lambda p: [(q.key, q.outline, q.holes, q.cuts) for q in pc.parts(p)]
assert shape(q8) == shape(q7), "v8 の部品の形が v7 と違う"
m8, m7 = " ".join(pc.materials(q8)), " ".join(pc.materials(q7))
assert "テープ" not in m8 and "鉛筆" in m8 and "カッター" in m8, m8
assert "セロハンテープ" in m7, m7
st8 = pc.steps(q8)
assert len(st8) == len(pc.steps(q7)) and any("指で押さえて仮に止める" in s for s in st8), st8
# 鉛筆の印は、頭の傾きを見て位置を決めた後に付ける（傾きを見る前に印を付けると、位置を直した時に印が古い位置に残る。見直しの指摘）
i_hold = next(i for i, s in enumerate(st8) if "指で押さえて仮に止める" in s)
i_mark = next(i for i, s in enumerate(st8) if "鉛筆で腕の位置の印" in s)
assert i_mark == i_hold + 1 and st8[i_mark].index("傾きを見て") < st8[i_mark].index("鉛筆で") < st8[i_mark].index("貼る"), st8[i_hold:i_mark + 1]
assert "鉛筆" not in st8[i_hold], st8[i_hold]
assert pc.steps(q7)[i_mark] == "頭の傾きを見て腕の位置を決めてから、腕を 3 首の帯に貼る"  # デモの v7 の手順は前のまま
assert not any("テープ" in s for s in st8), st8
_, lay8, fails8 = _compose("pivot_counterweight", t8["params"], _load(t8["source_id"]), version=8)
assert not fails8, [f.line() for f in fails8]
assert any(t.text and t.text.endswith("版 8") for t in lay8["texts"]), "題が版 8 でない"
assert pc.check_range({**q8, "arm_hold": "clip"}) and not pc.check_range(q8)  # 仮に止める物は tape と finger だけ
assert pc.spec()["arm_hold"] == ("tape", "finger")  # 仕様の道具にも選び肢を出す（見直しの指摘）
print("ok 虎 v8（テープを使わず、指で押さえて鉛筆で印・部品は v7 と同じ）")
