"""虎の立体の脚と、角を落とした胴（制作者の追加の指示 2026-11-06「虎の足と胴体を立体的にして、さらにリアリティを追求する」）。

既定（leg_height 0・body_round 0）は今までの箱で、脚の部品も印も無い。次の組の見本 examples/tora_v5.json が両方を使う。
"""
import json
import math
import pathlib

from omochae.__main__ import load_source
from omochae.compose import compose
from omochae.floors import check_art
from omochae.templates import pivot_counterweight as pc

ROOT = pathlib.Path(__file__).resolve().parents[1]
v5 = json.loads((ROOT / "examples/tora_v5.json").read_text(encoding="utf-8"))
q5 = dict(pc.DEFAULTS, **v5["params"])
neck = dict(pc.DEFAULTS, mount="neck")
assert q5["leg_height"] > 0 and q5["body_round"] > 0, q5

# 1. 既定は脚なし・箱: 脚の部品・脚の印・角の面の折り線が無く、側面に描いた脚がある（写真の直し F の繋ぎ）
ps = {x.key: x for x in pc.parts(neck)}
assert not any(k.startswith("leg") for k in ps) and not any(a.get("mark") == "leg" for a in ps["body"].art)
assert len(ps["body"].mountain) == 10
assert len([a for a in ps["body"].art if a["kind"] == "poly" and a.get("fill") == pc.WHITE and a.get("stroke") == pc.STRIPE]) == 4
assert [r["number"] for r in pc.bom(neck) if r["key"] in ("axle", "weight")] == [7, 8]

# 2. 脚 4 本: 番号 6〜9・名は脚。白い角筒（山折り 4 本）と、内へ折る上の糊代 2 つ（山折り 2 本）、横の糊代。刷った面は外
ps = {x.key: x for x in pc.parts(q5)}
legs = [ps[f"leg{i}"] for i in range(1, 5)]
a, t, h = pc.LEG_SIDE, pc.LEG_TAB, q5["leg_height"]
for i, leg in enumerate(legs):
    assert leg.number == 6 + i and leg.label == f"{6 + i} 脚", (leg.number, leg.label)
    assert len(leg.mountain) == 6 and not leg.valley and len(leg.glue) == 3, leg.key
    assert abs(leg.width - (4 * a + pc.LEG_GLUE)) < 1e-9 and abs(leg.height - (t + h)) < 1e-9, (leg.width, leg.height)
    assert sum(1 for m in leg.mountain if m[0][1] == t and m[1][1] == t) == 2  # 上の糊代の折り線は上の端（胴の底に付く側）
    assert 2 * pc.LEG_TAB <= a  # 向かい合う面から内へ折る 2 つの糊代は重ならない
assert check_art(legs) == [], [f.line() for f in check_art(legs)]
# 部品表: 脚は 6〜9、刷らない竹串と粘土は 10・11（刷る部品の番号と部品表の行は 1 対 1）
rows = {r["key"]: r["number"] for r in pc.bom(q5)}
assert [rows[f"leg{i}"] for i in range(1, 5)] == [6, 7, 8, 9] and rows["axle"] == 10 and rows["weight"] == 11, rows

# 3. 胴の底の四角（位置の印）4 つ: 脚の上の面の大きさ（糊代は角筒の内に入る）。底の面（x が H〜H＋L、y が b0〜b1）の内にあり、
#    前の 2 つは前の壁の側（x が H に近い）
body = ps["body"]
L, W, H, g, c = q5["body_length"], q5["body_width"], q5["body_height"], q5["glue"], q5["body_round"]
d = c / math.sqrt(2)
b0 = g + (W - 2 * d) + c + (H - d)
b1 = b0 + W
marks = [m for m in body.art if m.get("mark") == "leg"]
assert len(marks) == 4 and all(m.get("closed") for m in marks)
for m in marks:
    xs, ys = [x for x, _ in m["pts"]], [y for _, y in m["pts"]]
    assert H < min(xs) and max(xs) < H + L and b0 < min(ys) and max(ys) < b1, m["pts"]
    assert abs(max(xs) - min(xs) - a) < 1e-9 and abs(max(ys) - min(ys) - a) < 1e-9, m["pts"]
assert sorted(sum(x for x, _ in m["pts"]) / 4 < H + L / 2 for m in marks) == [False, False, True, True]
# 立体の脚がある時は、側面に脚を描かない（下の白い帯だけ）
assert not [x for x in body.art if x["kind"] == "poly" and x.get("fill") == pc.WHITE and x.get("stroke") == pc.STRIPE]

# 4. 角を落とした胴: 角の面の折り線 2 本が増え（12 本）、前と後ろの壁の上の角が切れている。軸の穴は側面の縦の所
assert len(body.mountain) == 12, len(body.mountain)
assert (0, b0 + d) in body.outline and (0, b1 - d) in body.outline and (2 * H + L, b0 + d) in body.outline, "壁の上の角を切っていない"
ax = q5["axle_height"]
ch1 = g + (W - 2 * d) + c
ch2 = b1 + (H - d)
assert [y for _, y, _ in body.holes] == [ch1 + (H - d) - ax, ch2 - ((H - d) - ax)], body.holes
assert all(ch1 < y < b0 or b1 < y < ch2 for _, y, _ in body.holes)  # 側面の縦の所（角の面ではない）

# 範囲の下限の胴（長さ 40・幅 20）でも、4 つの四角は底の面の内で重ならない
small = dict(q5, body_length=40, body_width=20, body_round=0)
sb = next(x for x in pc.parts(small) if x.key == "body")
from shapely.geometry import Polygon
rects = [Polygon(m["pts"]) for m in sb.art if m.get("mark") == "leg"]
sb0 = small["glue"] + small["body_width"] + small["body_height"]
floor = Polygon([(small["body_height"], sb0), (small["body_height"] + 40, sb0), (small["body_height"] + 40, sb0 + 20), (small["body_height"], sb0 + 20)])
assert all(floor.contains(r) for r in rects) and all(r1.intersection(r2).area == 0 for i, r1 in enumerate(rects) for r2 in rects[i + 1:])

# 5. 組み方の文: 脚の段は、上の面を閉じる前。上の糊代は内へ折る。脚が無い形の手順は変わらない
st = pc.steps(q5)
i = st.index("6〜9 脚を山折りの線で角筒にして糊代で貼り、上の 2 つの糊代を内へ山折りして、1 胴の底の点の線の四角に 1 本ずつ貼る")
assert st[i + 1] == "1 胴の上の面を閉じる", st
assert len(st) == len(pc.steps(dict(q5, leg_height=0))) + 1

# 6. 床: 吊る形の胴は角を落とせない。軸の穴が角の面に来る高さ・尾の四角が入らない細い上の面は落とす。脚の分だけ頭は床から離れる
def fails(q):
    return [f.message for f in pc.check_physics(q)]
assert any("吊る形の胴は角を落とせない" in m for m in fails(dict(pc.DEFAULTS, mount="hang", axle_height=50, body_round=4)))
assert any("角の面に来る" in m for m in fails(dict(q5, axle_height=48)))
assert any("尾の糊代の四角" in m for m in fails(dict(q5, body_width=20, body_round=10, strip_width=10)))
low = dict(neck, axle_height=15, head_h=26, weight_below_axle=5, weight_behind=0)
assert any("床に近すぎる" in m for m in fails(low)) and not any("床に近すぎる" in m for m in fails(dict(low, leg_height=10)))
# 吊る形は、脚がある時も床までは胴の底で見る（保守側）。頭の裏の粘土の玉が前の脚に当たるかは、玉の大きさ・位置・傾きで変わるので、
# 胴の底より下へ頭を出さない形だけを通す。境は「頭の下の端が胴の底から 3mm」: ちょうど 3mm は通し、それより低いと落とす。
# 脚の分を足せば床に届かない寸法は「前の脚に当たらないかを確かめられない」と言い、脚が無い時や脚を足しても届く時は「床に近すぎる」
hang = dict(pc.DEFAULTS, mount="hang", axle_height=pc.DEFAULTS["body_height"] - pc.HOLE_MARGIN)
arm = pc.axle_to_head_top(hang)
edge = pc.DEFAULTS["body_height"] - pc.HOLE_MARGIN - 3 - arm  # 頭の下の端が胴の底からちょうど 3mm になる頭の高さ
floor_msgs = lambda q: [m for m in fails(q) if "床に近すぎる" in m or "前の脚に当たらないか" in m]
ok_q = dict(hang, head_h=edge, weight_below_axle=arm + 1)
bad_q = dict(hang, head_h=edge + 1, weight_below_axle=arm + 1)
assert floor_msgs(ok_q) == [] and floor_msgs(dict(ok_q, leg_height=10)) == [], (floor_msgs(ok_q), floor_msgs(dict(ok_q, leg_height=10)))
assert floor_msgs(bad_q) == ["頭の下端が床に近すぎる"], floor_msgs(bad_q)
assert len(floor_msgs(dict(bad_q, leg_height=10))) == 1 and "前の脚に当たらないかを確かめられない" in floor_msgs(dict(bad_q, leg_height=10))[0]
# 低すぎる脚は落とし、形は壊さない（横の糊代の頂点の順と指の線）
assert any("脚が低すぎ" in m for m in fails(dict(q5, leg_height=3))) and not any("脚が低すぎ" in m for m in fails(q5))
for hh in (0.5, 1, 2, 3, pc.LEG_MIN):
    lp = next(x for x in pc.parts(dict(q5, leg_height=hh)) if x.key == "leg1")
    assert Polygon(lp.outline).is_valid and check_art([lp]) == [], (hh, [f.line() for f in check_art([lp])])

# 7. 見本の紙は、範囲・物理・配置の検査を通り、A4 に入る（脚は網の空きに置く）
assert pc.check_range(q5) == [] and pc.check_physics(q5) == []
_, layout, fl = compose("pivot_counterweight", q5, load_source(v5["source_id"]))
assert not fl, [f.line() for f in fl]
print("ok 虎の立体の脚と角を落とした胴")
