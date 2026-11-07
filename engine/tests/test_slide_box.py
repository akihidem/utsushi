"""猫と鼠の箱の床（F5.slide）の式の要所を数点で確かめる。隙間の層の数と行程は言葉で決めると間違えやすいので、ここで数える。"""
from omochae.compose import TEMPLATES
from omochae.templates import slide_box as t

P = dict(t.DEFAULTS)
S = {**P, "form": "sleeve"}
assert TEMPLATES["slide_box"] is t, "templates/ に置けば登録される"
for q in (P, S):
    assert t.check_physics(q) == [] and not t.check_range(q), t.check_physics(q)

# 隙間 ＝ 隙間の見込み − 厚み × 層。lid の左右は 2 層、sleeve の上下は継ぎ目の糊代を足して 3 層
th = P["paper_thickness"]
assert abs(t.clearances(P)["左右"][0] - (P["slide_gap"] - 2 * th)) < 1e-9
c, layers = t.clearances(S)["上下"]
assert layers == 3 and abs(c - (S["slide_gap"] - 3 * th)) < 1e-9
# 刷る外箱の面の幅・高さも同じ式から出る（型紙と床が同じ値を使う）
sl = next(q for q in t.parts(S) if q.key == "sleeve")
assert abs(sl.height - (2 * t.board_width(S) + 2 * t.sleeve_height(S) + S["glue"])) < 1e-9
lid = next(q for q in t.parts(P) if q.key == "lid")
assert abs(lid.height - (t.board_width(P) + 2 * P["skirt"])) < 1e-9

# 隙間の窓の外は F5.slide の道の隙間で落ちる（狭い・広い・厚い紙）
for bad in ({"slide_gap": 0.5}, {"slide_gap": 2.5}, {"paper_thickness": 0.5}):
    fs = t.check_physics({**P, **bad})
    assert fs and all(f.floor == "F5.slide" and f.where.startswith("道の隙間") for f in fs), (bad, fs)
# 同じ隙間の見込みでも、層の多い sleeve の上下は先に狭くなる
assert t.check_physics({**P, "slide_gap": 0.7}) == []
assert [f.where for f in t.check_physics({**S, "slide_gap": 0.7})] == ["道の隙間（上下）"]

# 行程: 鼠の像の後ろの端 ＋ 余りまで動けば通り、足りなければ落ちる
need = P["mouse_at"] + P["mouse_w"] + t.SHOW_MARGIN
at = need + t.STOP_AT + 2 * th  # 動く長さがちょうど要る長さになる仕切りの位置
assert abs(t.travel({**P, "partition_at": at}) - need) < 1e-9
assert t.check_physics({**P, "partition_at": at}) == []
assert [f.where for f in t.check_physics({**P, "partition_at": at - 0.5})] == ["行程"]
# 動きすぎ（箱の半分を超える）も行程で落ちる
assert any(f.where == "行程" and "半分" in f.message for f in t.check_physics({**P, "partition_at": 70}))

# 止め: lid の舌は仕切りに掛かり、鼠の上を通る。sleeve の縁は仕切りに掛かり、低い前の壁と鼠の上を通る
assert any(f.where == "止め" for f in t.check_physics({**P, "mouse_h": P["box_h"] - P["stop_depth"]}))
assert any(f.where == "止め" and "抜ける" in f.message for f in t.check_physics({**S, "stop_depth": 2}))
assert any(f.where == "前の壁" for f in t.check_physics({**S, "front_h": 22}))
# 糊代: 箱の前の角の糊代で狭まった所を、止めが擦らずに通る幅
room = t.stop_side_room(P)
assert abs(room - (P["box_w"] - 3 * th - P["stop_w"]) / 2) < 1e-9
assert [f.where for f in t.check_physics({**P, "stop_w": 29})] == ["糊代"]

# 形ごとの部品: lid だけ止めがあり、sleeve は外箱。部品表と key が揃う
for q in (P, S):
    keys = {x.key for x in t.parts(q)}
    assert keys <= {r["key"] for r in t.bom(q)}, keys
assert "stop" in {x.key for x in t.parts(P)} and "stop" not in {x.key for x in t.parts(S)}
assert "sleeve" in {x.key for x in t.parts(S)} and "lid" not in {x.key for x in t.parts(S)}
# 床の式が頼る貼る位置（止め・仕切り・鼠）は、型紙に印を刷り、組み方の文でも言う。印が無いと、式の行程どおりに貼れない
box = next(x for x in t.parts(P) if x.key == "box")
xs = {round(a["pts"][0][0], 6) for a in box.art if a["kind"] == "line"}
assert {P["box_h"] + P["partition_at"], P["box_h"] + P["mouse_at"]} <= xs, xs
k, B = P["skirt"], t.board_width(P)
ticks = [a for a in lid.art if a["kind"] == "line" and all(abs(x - t.STOP_AT) < 1e-9 for x, _ in a["pts"])]
# 蓋の表（板）と左右の袴の 3 か所。袴の印は、蓋を裏返して止めを貼る時に見える
assert {(min(y for _, y in a["pts"]) < k) + 2 * (min(y for _, y in a["pts"]) > k + B) for a in ticks} == {0, 1, 2}, ticks
text = " ".join(t.steps(P))
assert f"{P['partition_at']:g}mm" in text and f"{P['mouse_at']:g}mm" in text and f"{t.STOP_AT}mm" in text and "袴の印" in text
# 出典: 2 つの形は同じ玩具なので、どちらもコマ 25 右
assert t.SOURCES == {"lid": t.SOURCE, "sleeve": t.SOURCE}

# 外箱の縁の本当の深さは、切る端から折り線まで（stop_depth − LIP_INSET）。掛かりの式もその深さで見る
lip_fold = next(a for a, b in sl.mountain if a[0] == b[0])[0]  # 縁の折り線（縦の 1 本）
assert abs((lip_fold - min(x for x, _ in sl.outline)) - t.lip_depth(S)) < 1e-9 and abs(t.lip_depth(S) - (S["stop_depth"] - t.LIP_INSET)) < 1e-9
# 名目の深さなら掛かる（2.3 − 0.55 = 1.75）が、本当の深さでは 1.25 で掛からない寸法
assert any(f.where == "止め" and "抜ける" in f.message for f in t.check_physics({**S, "stop_depth": 2.3}))

# 組み上がりの絵は、渡した枠の中に収まる（動いた中箱を枠の左の外に描いていた）
for q in (P, S):
    left, top, width, height = 10, 20, 80, 40  # 絵の枠
    for sh in t.diagram(left, top, width, height, q):
        xs = [sh["x"], sh["x"] + sh["w"]] if sh["kind"] == "rect" else [sh["x1"], sh["x2"]]
        assert left - 1e-9 <= min(xs) and max(xs) <= left + width + 1e-9, (q["form"], sh)

# 部品の外形は左上を原点にする（低い前の壁の中箱で、左の端が 0 でなかった）
for q in (P, S, {**S, "front_h": 5}):
    for part in t.parts(q):
        assert abs(min(x for x, _ in part.outline)) < 1e-9 and abs(min(y for _, y in part.outline)) < 1e-9, (q["form"], part.key)
print("ok")
