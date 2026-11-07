"""紙の鳴り物の床（F5.sound）の式の要所を数点で確かめる。扇の弧と周・閉管の高さ・舌の振動数は言葉で決めると間違えやすいので、ここで数える。"""
import math

from shapely.geometry import Polygon

from omochae.compose import TEMPLATES
from omochae.floors import check_bom
from omochae.templates import whistle as w

assert TEMPLATES["whistle"] is w, "templates/ に置けば登録される"
H, T, R = ({**w.DEFAULTS, "kind": k} for k in w.KINDS)
for p in (H, T, R):
    assert w.check_physics(p) == [] and not w.check_range(p), p["kind"]
    # 型紙に刷る部品は全部部品表に載り、絵の面は自分で交わらない（交わると検査の面積が狂う）
    assert check_bom(w.bom(p), w.parts(p)) == [], p["kind"]
    for q in w.parts(p):
        for a in q.art:
            if a["kind"] == "poly":
                assert Polygon(a["pts"]).is_valid, (p["kind"], q.key)

# ラッパ: 刷った扇の外の弧の長さ ＝ 口の円周 π·D。糊代の帯は弧の端から辺に平行に glue の幅
horn = next(q for q in w.parts(H) if q.key == "horn")
arc = w.horn_outer_arc(horn)
assert abs(arc - math.pi * H["horn_mouth_d"]) / (math.pi * H["horn_mouth_d"]) < 1e-3, arc
(gx0, gy0), (gx1, gy1) = horn.glue[0][0], horn.glue[0][1]
assert abs(math.dist((gx0, gy0), (gx1, gy1)) - H["glue"]) < 1e-9
# 扇の角度は 2π·sin(半頂角)。小さい口の弧も、枠の円盤の周に合う
a, s0, s1, th = w.horn_cone(H)
assert abs(th - 2 * math.pi * math.sin(math.radians(a))) < 1e-12
assert abs(s0 * th - math.pi * 2 * w.reed_disc_r(H)) < 1e-9
# 口を開きすぎる（短いラッパ）と落ちる
fs = w.check_physics({**H, "horn_mouth_d": 80, "horn_length": 22})
assert [(f.floor, f.where) for f in fs] == [("F5.sound", "ラッパ")], fs

# 舌: 片持ちの梁の式。長さを 2 倍にすると 1/4、厚みを 2 倍にすると 2 倍
f0 = w.reed_hz(H)
assert abs(w.reed_hz({**H, "reed_length": 2 * H["reed_length"]}) - f0 / 4) < 1e-9
assert abs(w.reed_hz({**H, "reed_thickness": 2 * H["reed_thickness"]}) - 2 * f0) < 1e-9
assert 400 < f0 < 500, f0  # 既定は 454Hz 前後（E 3GPa・ρ 750 の見込み）
fs = w.check_physics({**H, "reed_length": 9, "reed_thickness": 0.03})
assert [f.where for f in fs] == ["舌"] and "Hz" in fs[0].message, fs
# 幅広の舌（板のように揺れる）と、管に収まらない窓は落ちる
assert any("幅の" in f.message for f in w.check_physics({**H, "reed_length": 6, "reed_width": 5}))
assert any("管の内" in f.message for f in w.check_physics({**H, "pipe_d": 8}))
# 刷る舌の長さ ＝ 根元 ＋ 自由長。窓は折ると重なる（橋の折り線について左右対称）
tongue = next(q for q in w.parts(H) if q.key == "tongue")
assert abs(tongue.width - (w.reed_root(H) + H["reed_length"])) < 1e-9
reed = next(q for q in w.parts(H) if q.key == "reed")
(xf, _), _ = reed.valley[0]
(x0, y0, cw, ch), (x1, y1, _, _) = reed.cuts
assert abs((x0 + cw / 2) + (x1 + cw / 2) - 2 * xf) < 1e-9 and y0 == y1

# 筒の笛: 閉管 c/4(L+0.3d)。既定の 150mm・径 16mm・栓 8mm で 584Hz 前後
f = w.tube_hz(T)
assert abs(f - 343 / (4 * (0.142 + 0.3 * 0.016))) < 1e-9 and 580 < f < 590, f
fs = w.check_physics({**T, "tube_length": 60})
assert [(f.floor, f.where) for f in fs] == [("F5.sound", "筒")], fs
fs = w.check_physics({**T, "notch_width": 14})
assert [(f.floor, f.where) for f in fs] == [("F5.sound", "歌口")], fs
assert w.check_physics({**T, "notch_depth": 1}) != []  # 浅すぎる切り欠き（径の 0.1 未満）
# 切り欠きは口（左の端）の、継ぎ目の反対（周の半分）に刷る
tube = next(q for q in w.parts(T) if q.key == "tube")
circ = w.wrap_circ(T["tube_d"], T["paper_thickness"])
xs = sorted({y for x, y in tube.outline if x == T["notch_depth"]})
assert abs(sum(xs) / 2 - circ / 2) < 1e-9 and abs(xs[1] - xs[0] - T["notch_width"]) < 1e-9
# 閉管の長さを決める粘土の栓は、詰める深さの印を竹筒に刷り、組み方の文でも言う（印が無いと詰める量で高さがずれる）
marks = [a for a in tube.art if a.get("stroke") == w.MARK]
assert [a["pts"][0][0] for a in marks] == [T["tube_length"] - T["plug_depth"]], marks
assert any("印" in s and f"{T['plug_depth']:g}mm" in s for s in w.steps(T))
# 舌の根元を挟む長さも、舌に刷った線（窓の端に合わせる）と組み方の文で言う
assert [a["pts"][0][0] for a in tongue.art if a.get("stroke") == w.MARK] == [w.reed_root(H)]
assert any("線を窓の端" in s for s in w.steps(H))
# 面は別の部品
assert {"tube", "mask", "handle"} == {q.key for q in w.parts(T)}

# 鈴: 四面体の内接球。立方体を半分にした形の一般の式と、正四面体（a = h·√2 の時）の内接球 a/(2√6) が合う
r = w.bell_inradius(R)
a = w.wrap_circ(R["bell_d"], R["paper_thickness"]) / 2
h = R["bell_height"] - 2 * w.BELL_SEAL
assert abs(r - a * h / (4 * math.sqrt(a * a / 4 + h * h))) < 1e-12
reg = {**R, "bell_height": a / math.sqrt(2) + 2 * w.BELL_SEAL}
assert abs(w.bell_inradius(reg) - a / (2 * math.sqrt(6))) < 1e-9
fs = w.check_physics({**R, "bead_d": 10})
assert [(f.floor, f.where) for f in fs] == [("F5.sound", "鈴")], fs
assert w.check_physics({**R, "bead_d": 8}) == []

# 刷る形ごとの出典の記録がある
import pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
for sid in w.SOURCES.values():
    assert (ROOT / "data/sources" / f"{sid}.json").exists(), sid
print("ok")
