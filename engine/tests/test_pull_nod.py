"""引いて振れて戻る族（pull_nod）の床 F5.pull_nod の式の要所を数点で確かめる。

なぜ数えるか: 戻る向き・振れる角度・穴の余白は、直す向きを言葉で決めると間違えやすい。場面の rc だけでは、
どの式の項が効いて落ちたかが見えないので、項ごとに境目の両側を置く。
"""
import math

from shapely import affinity

from omochae.floors import check_bom
from omochae.templates import pull_nod as pn

bow = {**pn.DEFAULTS, "kind": "bow"}
jaw = {**pn.DEFAULTS, "kind": "jaw"}
peck = {**pn.DEFAULTS, "kind": "peck"}


def floors(p):
    return [f for f in pn.check_physics(p) if f.floor == "F5.pull_nod"]


# 既定はどちらの形も通り、部品表と部品が合う
for p in (bow, jaw, peck):
    assert pn.check_range(p) == [] and pn.check_physics(p) == [], (p["kind"], pn.check_physics(p))
    assert check_bom(pn.bom(p), pn.parts(p)) == [], p["kind"]

# 1. 戻る力: 尾の粘土が重いほど戻るモーメントが増え、軽いと体の紙に負けて負になる
m1, fr = pn.return_moment(bow)
m2, _ = pn.return_moment({**bow, "weight_g": 4.0})
assert m2 > m1 > pn.SAFETY * fr
m0, _ = pn.return_moment({**bow, "weight_g": 0.2})
assert m0 < 0 and any("戻らない" in f.message for f in floors({**bow, "weight_g": 0.2}))
# 体を前に長くすると紙の重心が前へ出て、戻るモーメントが減る（向きの確かめ）
assert pn.return_moment({**bow, "torso_len": 70})[0] < m1
# 顎は前（口が開く向き）が戻る向き。粘土を顎の先に付けるので正
assert pn.return_moment(jaw)[0] > 0
# 摩擦の境目: 戻るモーメントが摩擦の SAFETY 倍をちょうど超えない粘土の量で落ちる
card, x_card, _ = pn.lever(bow)[0][0]
arm = bow["tail_len"] - pn.CLAY_IN
w_edge = (-card * x_card + pn.SAFETY * pn.MU * card * pn.AXLE_R) / (arm - pn.SAFETY * pn.MU * pn.AXLE_R)
assert floors({**bow, "weight_g": round(w_edge - 0.01, 3)}) and not floors({**bow, "weight_g": round(w_edge + 0.05, 3)})

# 2. 振れる角度: bow は体の四角を回して臼に当たる角度。頭の前の下の角を手で回し、その角度で臼の上の面に届き、1 刻み前では届かない事を見る
def corner(p, deg):
    t = math.radians(deg)
    T, h = p["torso_len"], p["torso_w"] / 2
    return T * math.cos(t) - h * math.sin(t), p["post_height"] - T * math.sin(t) - h * math.cos(t)
sb = pn.swing_deg(bow)
f_, z_ = corner(bow, sb)
r_ = bow["mortar_round"] / (2 * math.pi)
assert z_ <= bow["stop_height"] + 1e-9 < corner(bow, sb - pn.SWEEP_STEP)[1] and abs(f_ - pn.mortar_ahead(bow)) < r_, (sb, f_, z_)
assert pn.swing_deg({**bow, "stop_height": 36}) < pn.MIN_SWING and floors({**bow, "stop_height": 36})
assert pn.swing_deg({**bow, "stop_height": 45}) == 0.0  # 臼が軸より高いと振れない
# jaw はこぶまでの隙間と舌の長さ。隙間が狭いと口が少ししか開かない
# 角度の式そのものは 5a で確かめる
assert {f.where for f in floors({**jaw, "stop_gap": 2})} == {"こぶ"}

# 3. 穴の縁の余白: 柱の幅の半分 − 穴の半径 が HOLE_MARGIN を割ると落ちる。境目の両側
assert not floors({**bow, "post_width": 2 * (pn.HOLE_MARGIN + pn.AXLE_R)})
assert floors({**bow, "post_width": 2 * (pn.HOLE_MARGIN + pn.AXLE_R) - 0.2})
# 舌が短いと、軸の穴と糸の穴の間が狭くなって落ちる（隣の穴までの余白も見る）
assert any(f.where == "下顎" for f in floors({**jaw, "tab_len": 8}))
# 糸の腕は舌の長さから穴の置き場を引いた物で、引く力の見込みは腕が長いほど小さい
assert pn.jaw_string_arm(jaw) == jaw["tab_len"] - (pn.HOLE_MARGIN + pn.STRING_R + 0.5)
assert pn.pull_gf({**bow, "string_arm": 30}) < pn.pull_gf(bow)

# 4. peck（藁苞の鶏）: 傾く角度は、輪郭の頂点が苞の上の面に届く角度の最小。腹が低い（leg_h が小さい）ほど浅い
sw = [pn.bird_swing({**peck, "leg_h": h}, "cock") for h in (1, 2, 4, 10)]
assert sw == sorted(sw) and sw[0] < pn.MIN_SWING <= sw[1], sw
assert [f.where for f in floors({**peck, "leg_h": 1})] == ["奥の鶏", "手前の鶏"]  # 手前の鶏は腹の高さも縮めた相似の形なので、同じく浅い
# 尾の先が苞の上の面にあり（静かな時の後ろの止め）、粘土は軸より後ろ＝戻る向き
b = pn.bird(peck, "cock")
assert abs(max(y for x, y in b["body"].exterior.coords) - b["H"]) < 1e-9 and b["clay"][0] > b["pivot"][0]
assert pn.bird_moment(peck, "cock")[0] > pn.bird_moment({**peck, "weight_g": 1.0}, "cock")[0] > 0
# 胸の糸の穴を前へ出しすぎると、斜めの胸の縁に近づいて落ちる
assert {f.where for f in floors({**peck, "peck_arm": 12})} == {"奥の鶏", "手前の鶏"}
# 苞が浅いと脚の帯が底に当たる
assert [f.where for f in floors({**peck, "straw_h": 14, "axle_depth": 8})] == ["藁苞"]
# 溝は傾く分だけ前へ長い。2 羽の溝は重ならない
sh_, sc_ = pn.slot(peck, "hen"), pn.slot(peck, "cock")
assert sh_["len"] > pn.TAB_W + 2 and abs(sh_["y"] - sc_["y"]) == peck["bird_gap"]

# 5. レビューの指摘（2026-11-04）を押さえる
# 5a. 顎の止め: 舌の端の上の角は軸のまわりを回るので、上がる高さは sin で頭打ちになる。こぶが舌の届く高さより上なら、止めに当たらない
assert floors({**jaw, "stop_gap": 20}), "舌が届かない高さのこぶを通した"
assert [f.where for f in floors({**jaw, "stop_gap": 20})] == ["こぶ"] and "届かない" in floors({**jaw, "stop_gap": 20})[0].message
h2 = jaw["jaw_h"] / 2
rho, phi = math.hypot(jaw["tab_len"], h2), math.atan2(h2, jaw["tab_len"])
assert abs(pn.swing_deg(jaw) - math.degrees(math.asin((h2 + jaw["stop_gap"]) / rho) - phi)) < 1e-9
# 5b. こぶは 3 面と、三角の柱を閉じる糊代の 4 つ。最後の面を頭に貼る面にすると、柱が閉じない
bump = next(q for q in pn.parts(jaw) if q.key == "bump")
assert len(bump.valley) == 3 and len(bump.glue) == 1 and bump.glue[0][0][0] >= 3 * 8, (bump.valley, bump.glue)
# 5c. 串の抜け止めの粘土は、重り（式の weight_g）と別の行。同じ粘土から取ると、顎に付く量が式より減る
for p in (bow, jaw, peck):
    keys = [r["key"] for r in pn.bom(p)]
    assert "stopclay" in keys, (p["kind"], keys)
    weight = next(r for r in pn.bom(p) if r["key"] == "weight")
    assert f"{p['weight_g']:g}g" in weight["material"]
    assert any("抜け止め" in m for m in pn.materials(p))
# 5d. 形ごとの出典
assert pn.SOURCES == {"bow": pn.SOURCE, "jaw": "NDL-1187053-R0000030-L-pull_nod", "peck": "NDL-1187053-R0000016-R-pull_nod"}

# 6. 2 回目のレビューの指摘（2026-11-04）を押さえる
# 6a. 傾いた後の戻るモーメントは、質量の点ごとに軸のまわりで 2 次元に回して測る（x cosθ − z sinθ）。軸より上の粘土は、前へ傾くと腕が縮み、
#     負になりうる。鶏の粘土と紙の重心は軸より上にあるので、cos だけの近似では倒れる寸法を通した
#     式を写して比べると同じ間違いを 2 回書くだけなので、shapely で点そのものを軸のまわりに回し、回った後の x から腕を取って比べる
#     （鶏は前＝左へ傾く。後ろを正の x・上を正の z に取ると、反時計回りに回すと上の点が前＝負の x へ出て、前の点は下がる）
from shapely.geometry import Point as _P
for which in ("cock", "hen"):
    pts = pn.bird_points(peck, which)
    sw_w = pn.bird_swing(peck, which)
    rotated = sum(m * affinity.rotate(_P(x, z), sw_w, origin=(0, 0)).x for m, x, z in pts)
    assert abs(rotated - pn.moment_at(pts, sw_w)) < 1e-9
    # 途中の角度でも最小が振り切りより大きくない事は、1° ごとに回して確かめる
    worst = min(sum(m * affinity.rotate(_P(x, z), a, origin=(0, 0)).x for m, x, z in pts) for a in range(0, int(sw_w) + 1))
    assert pn.min_moment(pts, sw_w) <= worst + 1e-9
    assert pn.min_moment(pts, sw_w) > pn.SAFETY * pn.bird_moment(peck, which)[1], which  # 既定は振り切るまで戻る
# 粘土を軸の高い所（尾の付け根の上）に付ける形は、振り切った所で前へ倒れて落ちる
high = [(peck["weight_g"], 18, 27)]
assert pn.moment_at(high, 43) < 0
# bow と jaw は質量の点が軸の高さ（z = 0）にあるので、2 次元に回しても cos 倍と同じ（近似でなく厳密）
for p in (bow, jaw):
    pts, _ = pn.lever(p)
    assert all(z == 0 for _, _, z in pts)
# 6b. 手前の鶏は奥の鶏をそのまま HEN 倍にした形（腹の高さも縮める）。脚の帯は苞と穴の余白で決まるので縮めない
cb, hb = pn.bird(peck, "cock")["body"], pn.bird(peck, "hen")["body"]
assert affinity.scale(cb, pn.HEN, pn.HEN, origin=(0, 0)).symmetric_difference(hb).area < 1e-6
# 6c. bow の竹串は、U の字の柱の間（POST_GAP ＋ 柱の紙 2 枚）と、両端の抜け止めの分。柱の幅は串の向きに関わらない
import re
axle = next(r for r in pn.bom(bow) if r["key"] == "axle")
n_mm = int(re.search(r"約 (\d+)mm", axle["material"]).group(1))
assert n_mm == round(pn.POST_GAP + 2 * pn.PAPER_T + 2 * pn.STOP_END), axle["material"]
assert n_mm == next(int(re.search(r"約 (\d+)mm", r["material"]).group(1)) for r in pn.bom({**bow, "post_width": 20}) if r["key"] == "axle")
assert "stopclay" in [r["key"] for r in pn.bom(bow)] and any("抜け止め" in s for s in pn.steps(bow))

# 7. 3 回目のレビューの指摘（2026-11-05）を押さえる
# 7a. 2 羽が同じ面（bird_gap 0）だと、傾いた時にぶつかって落ちる。既定は幅の向きに離して別の面で振れ、通る
assert pn.birds_collide({**peck, "bird_gap": 0}) is not None and any("ぶつかる" in f.message for f in floors({**peck, "bird_gap": 0}))
assert pn.birds_collide(peck) is None and not floors(peck)
# 別の面にすると、苞の幅に収まらない間は落ちる
assert any("幅に収まらない" in f.message for f in floors({**peck, "bird_gap": 24}))
# 7b. bow の頭が臼を外れる（角度が大きく、頭の先が軸の近くへ引っ込む）寸法は落ちる。前の式は 78.5° で通した
miss = {**bow, "post_height": 70, "stop_height": 10, "weight_g": 3}
assert pn.swing_deg(miss) is None and any("臼を外れ" in f.message for f in floors(miss))
assert pn.bow_contact({**bow, "post_height": 56, "stop_height": 5, "torso_len": 41})[1] != "mortar"
# 7c. 鶏の粘土は質量から出した半径の玉で、玉の下が苞の上の面より上にある（尾の先より先に苞に載らない）
for which in ("cock", "hen"):
    bb = pn.bird(peck, which)
    rad = (3 * peck["weight_g"] / (4 * math.pi * pn.CLAY_RHO)) ** (1 / 3)
    assert abs(rad - 6.4) < 0.1 and bb["H"] - bb["clay"][1] - rad >= pn.CLAY_LIFT - 1e-9
    assert bb["body"].contains(_P(*bb["clay"]))  # 玉の中心は紙の上（紙に付ける）
# 7d. 顎のこぶの貼る所は、舌の角が当たる所の真上で、頭に目印を刷り、組み方の文にも同じ距離を書く
xb = pn.jaw_contact_back(jaw)
h2 = jaw["jaw_h"] / 2
assert abs(xb - math.sqrt(math.hypot(jaw["tab_len"], h2) ** 2 - (h2 + jaw["stop_gap"]) ** 2)) < 1e-9
head = next(q for q in pn.parts(jaw) if q.key == "head")
x0_, y0_, x1_, y1_ = pn.bump_box(jaw)
assert any(it["kind"] == "line" and (x0_, y0_) in it["pts"] and (x1_, y1_) in it["pts"] for it in head.art)
assert any(f"{xb:.0f}mm 後ろ" in s_ for s_ in pn.steps(jaw))
# 7e. 抜け止めの粘土は、部品表も組み方の文も串の両端の外側。peck で苞の中に付ける文は無い
for p in (bow, jaw, peck):
    assert "外側" in next(r["material"] for r in pn.bom(p) if r["key"] == "stopclay")
    assert any("抜け止め" in s_ and "外側" in s_ for s_ in pn.steps(p)), p["kind"]
assert not any("鶏の両側" in s_ for s_ in pn.steps(peck))
# 7f. 胸の糸の穴は、傾いても溝の前の端より後ろにある
for which in ("cock", "hen"):
    sl_ = pn.slot(peck, which)
    assert pn.string_ahead(peck, which) < sl_["cx"] - sl_["x0"], which
# 7g. 台は臼の前の縁まで載る長さが要る（臼が大きいと、臼の目印が台から出た）
assert any(f.where == "台" for f in floors({**bow, "plank_length": 80, "mortar_round": 70}))

# 形ごとの部品の key は英小文字だけ、部品表の番号と合う
for p in (bow, jaw, peck):
    assert {q.number: q.key for q in pn.parts(p)} == {r["number"]: r["key"] for r in pn.bom(p) if r["number"] < 7}

print(round(pn.swing_deg(bow), 1), round(pn.swing_deg(jaw), 1), round(pn.bird_swing(peck, 'cock'), 1), round(pn.pull_gf(bow)), round(pn.pull_gf(jaw)), round(pn.pull_gf(peck)))
print("ok")

# EP-0008（作る前のレビューの指摘から採った案。2026-11-06）: 振り獅子の下顎に、顎を動かす糸を付ける所と、口が開くための重りを付ける所を
# 示してほしいという声があった。位置の印（赤茶の点の線。凡例に「切らない・折らない」）で 2 つを刷った。
# - 重り: 顎の先の点の丸。真ん中は、戻る力の式が粘土を置く所（軸から jaw_len − CLAY_IN 前・軸の高さ）と同じ。粘土は丸の裏に付ける
# - 糸: 舌の端の糸の穴を囲む点の丸（軸の穴と見分ける）
# - 印は部品の内にあり、穴・折り線・糊代にかからない（check_art）。寸法の範囲の端の組でも同じ
# - 組み方の文が、2 つの丸を言う
from shapely.geometry import Point, Polygon
from omochae.__main__ import load_source
from omochae.compose import compose
from omochae.floors import check_art
seen = 0
for jl in (pn.RANGES["jaw_len"][0], jaw["jaw_len"], pn.RANGES["jaw_len"][1]):
    for jh in (pn.RANGES["jaw_h"][0], jaw["jaw_h"], pn.RANGES["jaw_h"][1]):
        for tl in (pn.RANGES["tab_len"][0], jaw["tab_len"], pn.RANGES["tab_len"][1]):
            q = {**jaw, "jaw_len": jl, "jaw_h": jh, "tab_len": tl}
            if pn.check_range(q) or pn.check_physics(q):
                continue  # 検査で落ちる寸法は刷らない
            seen += 1
            part = next(x for x in pn.parts(q) if x.key == "jaw")
            clay = [a for a in part.art if a["kind"] == "mark" and a.get("mark") == "clay"]
            ring = [a for a in part.art if a["kind"] == "mark" and a.get("mark") == "string"]
            assert len(clay) == 1 and len(ring) == 1, (q, len(clay), len(ring))
            c = Polygon(clay[0]["pts"]).centroid
            # 戻る力の式（lever）の粘土の点: 軸から前へ d・軸の高さ。軸の穴は顎の先から jaw_len なので、顎の紙の上では x = jaw_len − d
            d = pn.lever(q)[0][1][1]
            assert math.dist((c.x, c.y), (jl - d, jh / 2)) < 0.05, (q, c, jl - d)
            hx, hy, hr = part.holes[1]  # 舌の端の糸の穴
            rc = Polygon(ring[0]["pts"]).centroid
            assert math.dist((rc.x, rc.y), (hx, hy)) < 0.05, (q, rc, (hx, hy))
            assert check_art([part]) == [], (q, [f.line() for f in check_art([part])])
assert seen >= 5, seen
_, layout, fails = compose("pull_nod", jaw, load_source(pn.SOURCES["jaw"]))
assert not fails, [f.line() for f in fails]
assert any("位置の印" in x.text for x in layout["texts"]), "凡例に位置の印の行が無い"
st = pn.steps(jaw)
assert any("点の丸" in x and "重りの粘土" in x for x in st), st
assert any("点の丸で囲んだ" in x and "糸" in x for x in st), st
print("ok 振り獅子の糸と重りの印")
