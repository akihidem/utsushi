"""紙の棒と人形の仕掛け（F5.link）の床の式の要所を数点で確かめる。角や長さは言葉で決めると間違えやすいので、ここで数える。"""
import math

from shapely.geometry import Point, box

from omochae.compose import TEMPLATES
from omochae.floors import check_bom
from omochae.templates import lever_link as t

P = dict(t.DEFAULTS)
assert TEMPLATES["lever_link"] is t, "templates/ に置けば登録される"
# どの形も既定の寸法で床を通り、部品表に刷る部品が全部載る
for k in t.KINDS:
    q = {**P, "kind": k}
    assert not t.check_range(q) and t.check_physics(q) == [], (k, t.check_physics(q))
    assert check_bom(t.bom(q), t.parts(q)) == [], k
    assert t.SOURCES[k].startswith("NDL-1187053-R") and t.SOURCES[k].endswith("-lever_link")

# 押す形: 膝を接線の向きに押すと、角は asin(押す量 / 腕)
sumo = t.motion(P)
assert abs(sumo["input_angle"] - math.degrees(math.asin(P["travel"] / P["drive_arm"]))) < 0.15, sumo
# 腕より長く押すと死点を越える（どの角でも届かない）
assert t.push_angle((0, 0), (0, 30), (-1, 0), 31, 1) is None
fs = t.check_physics({**P, "travel": 32, "slot_len": 40})
assert [f.floor for f in fs] == ["F5.link"] and "死点" in fs[0].message, fs
# 振れが 15° に届かない押す量で落ちる（asin(s/30) < 15° は s < 7.76）
assert t.check_physics({**P, "travel": 7.9}) == []
fs = t.check_physics({**P, "travel": 7.6})
assert [f.where for f in fs] == ["B の足"], fs

# 溝: ピンの中心が動ける長さ ＝ 溝の長さ − 穴の直径。これが押し合う量より短いと落ちる
r = t.pin_r(P)
edge = P["travel"] + 2 * r
assert t.check_physics({**P, "slot_len": edge + 0.01}) == []
assert [f.where for f in t.check_physics({**P, "slot_len": edge - 0.01})] == ["溝"]

# ピンの穴の余白: 棒の幅の半分 − 穴の半径 ≧ 3。幅 10 は 3.3、幅 9.3 で 2.95 になり落ちる
m = {(n, w): v for n, w, v in t.pin_margins(t.assembly(P)[0]) if n == "細い棒"}
assert abs(min(m.values()) - (P["bar_w"] / 2 - r)) < 1e-6, m
assert any(f.where == "長い棒" for f in t.check_physics({**P, "bar_w": 9.3}))
# 同じ部品の 2 つの穴の間も紙の端と同じに見る（水車の腕が短いと、軸と手の穴の間が裂ける）
fs = t.check_physics({**P, "kind": "karakuri", "crank": 6})
assert any(f.where == "水車と手" for f in fs), fs

# 止まる物: 回す部品が割ピンの頭に当たる角。真下に 40mm 垂れた棒を回すと、真横 30mm の頭（半径 4）には 90° より前で当たる
bar = box(-3, 0, 3, 40)
hit = t.swing_hit(bar, (0, 0), 1, 120, [Point(-30, 0).buffer(t.HEAD_R)])
assert hit is not None and 60 < hit < 90, hit
assert t.swing_hit(bar, (0, 0), -1, 60, [Point(-30, 0).buffer(t.HEAD_R)]) is None  # 逆に回せば当たらない
# 梯子の板は、押すと下の端が机に当たり、そこで止まる（既定の寸法でも、押した角より机に当たる角が小さい）
big = t.motion({**P, "kind": "hashigo"})
assert big["hit_angle"] is not None and big["usable"] == big["hit_angle"] < big["input_angle"], big

# 引く形: 糸は膝が腰と穴を結ぶ線に乗るまでしか縮まない。そこで止まる角は、腰から膝と腰から穴の間の角
yk = t.motion({**P, "kind": "yakko", "travel": 25})  # 糸の縮む上限（約 21mm）を越えて引く
H, G = (30.0, 60.0), (76.0, 90.0)
assert yk["string_limited"] and abs(yk["input_angle"] - math.degrees(math.atan2(G[0] - H[0], G[1] - H[1]))) < 0.2, yk

# 四節: Grashof の境目。最短 + 最長 ≦ 残りの和で、最短が水車の腕
k = {**P, "kind": "karakuri"}
km = t.motion(k)
limit = km["d"] + P["drive_arm"] - km["b"]  # 水車の腕の上限
assert t.grashof(limit - 0.01, km["b"], P["drive_arm"], km["d"]) and not t.grashof(limit + 0.01, km["b"], P["drive_arm"], km["d"])
assert not t.grashof(5, 3, 10, 10)  # 最短が水車の腕でなければ 1 周回せない
fs = t.check_physics({**k, "crank": 30})
# 腕 30 の水車は机もこする（4 回目の見直しで机を止める物にした）。ここでは Grashof で落ちる事を見る
assert any(f.where == "四節" and "Grashof" in f.message for f in fs), fs
# 1 周回る時、犬の振れはおよそ 2·asin(水車の腕 / 犬の腕)（連桿が長いので）
assert abs(km["swing"] - 2 * math.degrees(math.asin(P["crank"] / P["drive_arm"]))) < 3, km

# 板の噛み: D·cos α − t·sin α = d。厚さが無ければ acos(d/D)
assert abs(t.lock_angle(3.2, 3, 0) - math.degrees(math.acos(3 / 3.2))) < 1e-6
a = t.lock_angle(3.2, 3, 0.15)
assert abs(3.2 * math.cos(math.radians(a)) - 0.15 * math.sin(math.radians(a)) - 3) < 1e-6 and a < math.degrees(math.acos(3 / 3.2))
assert t.lock_angle(3.0, 3, 0.15) == 0.0
sv = {**P, "kind": "saru_take"}
assert [f.where for f in t.check_physics({**sv, "hole_d": 3.0})] == ["板の穴"]
assert "緩く" in t.check_physics({**sv, "hole_d": 4.0})[0].message

# 絵の札: 動く量の半分ずつ上下しても、窓の縁を 2mm 以上覆う。窓と札の余りは 15mm なので 26mm までは覆い、27mm で端が見える
eb = {**P, "kind": "ebako", "slot_len": 40}
assert t.check_physics({**eb, "travel": 26}) == []
assert any("窓から見える" in f.message for f in t.check_physics({**eb, "travel": 27}))

# 登る形は板に谷折りの耳があり、折りの書き出しの対象になる
assert all(q.valley for q in t.parts(sv) if q.key.endswith("bar"))

# 床が見る量（押す・引く量、粘土の置き場）は、紙に印を刷り、組み方の文で印を言う。印が無いと、作る人は床が見た量で動かせない
for k in ("sumo", "hashigo", "ebako"):
    q = {**P, "kind": k, "travel": 16}
    go = t.reach(q) if k != "ebako" else 16  # 止まる所で届く量が travel より小さければ、その量を刷る（下の 2 回目の見直し 1）
    ticks = [it for pt in t.parts(q) for it in pt.art if it.get("mark") == "travel"]
    assert len(ticks) == 2 and abs(math.dist(ticks[0]["at"], ticks[1]["at"]) - go) < 1e-6, (k, ticks)
    assert any("印" in s and f"{go:.0f}mm" in s for s in t.steps(q)), k
for k in ("saru_take", "saru_sao"):
    q = {**P, "kind": k}
    clay = [it for pt in t.parts(q) for it in pt.art if it.get("mark") == "clay"]
    assert len(clay) == 1 and any("粘土" in s and "印" in s for s in t.steps(q)), k
assert any("印" in s and f"{t.reach({**P, 'kind': 'yakko'}):.0f}mm" in s for s in t.steps({**P, "kind": "yakko"}))

# 2 回目の見直し 1: 止まる物や張り切る糸で入力が travel まで届かない時、届く量だけを印と文に刷る（刷った量を押せない紙にしない）
yk = {**P, "kind": "yakko", "travel": 23}
ry = t.motion(yk)
assert ry["reach"] < yk["travel"] - 1, ry  # 糸は約 21mm までしか縮まない（3 回目の見直しで穴を横木の先へ移した後）
assert not any(f"{yk['travel']:g}mm" in s for s in t.steps(yk)) and any(f"{ry['reach']:.0f}mm" in s for s in t.steps(yk)), t.steps(yk)
hs = {**P, "kind": "hashigo"}
rh = t.motion(hs)
assert rh["reach"] < P["travel"] - 1, rh  # 机に当たる所までしか押せない
ticks = [it for pt in t.parts(hs) for it in pt.art if it.get("mark") == "travel"]
assert abs(math.dist(ticks[0]["at"], ticks[1]["at"]) - rh["reach"]) < 1e-6 and not any(f"{P['travel']:g}mm" in s for s in t.steps(hs))
# 届く量が小さすぎて振れが足りなければ、今までどおり落ちる
assert t.motion({**P, "kind": "sumo"})["reach"] == P["travel"]

# 2 回目の見直し 2: 斜めの棒の両端の穴が、組んだ姿で水車の手の穴と犬の尾の穴に重なる
pcs, mk = t.assembly({**P, "kind": "karakuri"})
by = {pc["part"].key: pc for pc in pcs}
rod_holes = [t.to_asm(by["rod"], (x, y)) for x, y, _ in by["rod"]["part"].holes]
dog_tail = t.to_asm(by["dog"], by["dog"]["part"].holes[1][:2])
wheel_hand = t.to_asm(by["wheel"], by["wheel"]["part"].holes[1][:2])
assert math.dist(rod_holes[0], wheel_hand) < 1e-6 and math.dist(rod_holes[1], dog_tail) < 1e-6, (rod_holes, dog_tail, wheel_hand)

# 2 回目の見直し 3: 相撲の B は棒の溝の 1 本のピンだけでは回って滑るので、蹴る間は B の立つ足を持つ（床はそれを前提に腰を固定の軸と見る）
sm = {**P, "kind": "sumo"}
assert any(it.get("mark") == "hold" for q in t.parts(sm) if q.key == "wrestlerb" for it in q.art)
assert any("B の立つ足" in s and "持つ" in s for s in t.steps(sm)), t.steps(sm)

# 3 回目の見直し 1: 連桿の幅が、1 周の間に前の面の割ピンの頭（軸 A を含む）に当たらない。既定の寸法で 1 周回る
kk = {**P, "kind": "karakuri"}
assert t.motion(kk)["link_hit"] is None and t.check_physics(kk) == []
# 軸 A に割ピンの頭を出すと、連桿は 1 周のどこかで必ず頭に当たる（連桿から見て A は手のピンのまわりを半径 crank で 1 周するため）
assert t.link_hit(kk, with_axle_head=True) is not None

# 3 回目の見直し 2: 登る板の胴の側の穴が、組み図で人形の穴に重なる
for k in ("saru_take", "saru_sao"):
    pcs, _ = t.assembly({**P, "kind": k})
    fig_holes = [t.to_asm(pcs[0], h[:2]) for h in pcs[0]["part"].holes]
    for bar in pcs[1:]:
        pin = t.to_asm(bar, bar["part"].holes[1][:2])
        assert min(math.dist(pin, h) for h in fig_holes) < 1e-6, (k, pin, fig_holes)

# 3 回目の見直し 3: 届く量が travel の 0.8 倍より小さければ F5.link（届かない）で落ちる。0.8 倍以上なら縮めた量を文に書いて通す
fs = t.check_physics({**P, "kind": "hashigo", "travel": 30})
assert [f.floor for f in fs] == ["F5.link"] and "届かない" in fs[0].message, fs
for k in ("hashigo", "yakko"):
    q = {**P, "kind": k}
    assert t.check_physics(q) == [] and t.reach(q) >= 0.8 * P["travel"], (k, t.reach(q))

# 4 回目の見直し 1: 相撲の細い棒は膝と一緒に動き、腰 H の割ピンの頭に乗り上げうる。棒もすべての頭と比べ、当たれば落とす
for da, tr in ((10, 7), (12, 8), (15, 12)):
    fs = t.check_physics({**P, "drive_arm": da, "travel": tr})
    assert any(f.where == "細い棒" and "頭" in f.message for f in fs), (da, tr, fs)
assert t.motion(P)["rider_hit"] is None

# 4 回目の見直し 2: 持つ所の印に、動く部品（足・細い棒）が動く間ずっと重ならない
fs = t.check_physics({**P, "drive_arm": 45})
assert any("持つ所" in f.message for f in fs), fs
assert t.motion(P)["hold_hit"] is None

# 4 回目の見直し 3: からくり台の水車と連桿は机（箱の下の縁）より下へ出ない
assert t.check_physics({**P, "kind": "karakuri"}) == []
fs = t.check_physics({**P, "kind": "karakuri", "crank": 16})
assert any("机" in f.message for f in fs), fs

# 4 回目の見直し 4: 組み方の文は穴を大きさ（小さい穴）でなく、印か置き場で言う
for k in t.KINDS:
    assert not any("小さい穴" in s for s in t.steps({**P, "kind": k})), k
assert all(any(it.get("mark") == "pole" for it in q.art) for q in t.parts({**P, "kind": "saru_take"}) if q.key.endswith("bar"))

# 4 回目の見直し 5: 噛む角の窓（3〜25°）が、穴の大きさで ±HOLE_TOL の広さを持つ。薄い紙の板では窓が狭く落ちる
lo_d, hi_d = t.hole_window(P["pole_d"], P["plate_t"])
assert lo_d + t.HOLE_TOL <= P["hole_d"] <= hi_d - t.HOLE_TOL, (lo_d, hi_d)
assert abs(t.lock_angle(lo_d, P["pole_d"], P["plate_t"]) - t.MIN_LOCK) < 1e-6 and abs(t.lock_angle(hi_d, P["pole_d"], P["plate_t"]) - t.MAX_LOCK) < 1e-6
fs = t.check_physics({**P, "kind": "saru_take", "plate_t": 0.5, "hole_d": 3.15})
assert any("許し" in f.message for f in fs), fs

# 4 回目の見直し 6: 竿の人形は 1 本のピンで吊るので、板を傾ける腕はピンまでの drive_arm で、粘土の置き場では変わらない。印はピンの真下
ss = {**P, "kind": "saru_sao"}
fig = t.parts(ss)[0]
clay = next(it for it in fig.art if it.get("mark") == "clay")
assert abs(clay["at"][0] - fig.holes[0][0]) < 1e-6 and clay["at"][1] > fig.holes[0][1]

# 4 回目の見直し 7: からくり台の水車の軸は、pin_d によらず 3mm の竹串
for d in (2, 5):
    row = next(r for r in t.bom({**P, "kind": "karakuri", "pin_d": d}) if r["key"] == "axle")
    assert "3mm" in row["material"], row

# 4 回目の見直し 8: 梯子の押す量の印は、範囲のどの押す量でも板の下の側に収まる（印の後ろの端 ≦ 板の端）
for tr in range(2, 41, 2):
    q = {**P, "kind": "hashigo", "travel": tr}
    slat = next(x for x in t.parts(q) if x.key == "slat")
    ticks = [it for it in slat.art if it.get("mark") == "travel"]
    assert max(it["at"][0] for it in ticks) + 0.4 <= slat.width - 0.3, (tr, ticks)

# 5 回目の見直し 1: 持つ所は指先の大きさ（半径 FINGER_R の円）で見て、その大きさで刷る。棒が 1mm だけ印を避ける寸法も落ちる
for da, w in ((40, 10), (38, 15)):
    fs = t.check_physics({**P, "drive_arm": da, "bar_w": w})
    assert any(f.where == "持つ所" for f in fs), (da, w, fs)
assert t.check_physics(P) == []
# 刷った持つ所の印は、床が見る指先の円と同じ所（組み図で、円の内にあり、円と部品の刷れる内側（切る線から 0.7mm 内）の重なりを覆う）
from shapely.geometry import Polygon as _Poly
pcs, mm = t.assembly(P)
bpc = next(pc for pc in pcs if pc["part"].key == "wrestlerb")
hold = next(it for it in bpc["part"].art if it.get("mark") == "hold")
printed = _Poly([t.to_asm(bpc, v) for v in hold["pts"]])
zone = mm["holds"][0]
assert zone.buffer(1e-6).contains(printed) and printed.area > 0.99 * zone.intersection(t.asm_poly(bpc).buffer(-0.7)).area

# 5 回目の見直し 2: 梯子のつまみは 3mm の竹串なので、その穴は pin_d によらない
for d in (2, 5):
    slat = next(q for q in t.parts({**P, "kind": "hashigo", "pin_d": d}) if q.key == "slat")
    assert abs(slat.holes[0][2] - (t.AXLE_D / 2 + 0.2)) < 1e-9, slat.holes
assert "3mm" in next(r for r in t.bom({**P, "kind": "hashigo"}) if r["key"] == "peg")["material"]

# 5 回目の見直し 3: からくり台は机に立てて箱を押さえる手順があり、水車と机の間に TABLE_CLEAR の余りを持つ
st = t.steps({**P, "kind": "karakuri"})
assert any("机に立て" in x and "押さえ" in x for x in st), st
assert any("机" in f.message for f in t.check_physics({**P, "kind": "karakuri", "crank": 12}))

# 5 回目の見直し 4: 用意する物に、登る板を貼る厚紙が載る。紙の書き方の決まり（omochae.paper_words・制作者の指示 2026-11-05）で
# 厚さの mm は書かず「空き箱の厚紙」の名前で言う。板の厚さの範囲（plate_t）の下の端でも、その名前に当たる事を見る
from omochae.paper_words import BOARD, paper_name  # noqa: E402
m = t.materials({**P, "kind": "saru_take"})
assert any(x.startswith(BOARD) for x in m), m
assert paper_name(thickness=t.RANGES["plate_t"][0]) == BOARD and paper_name(thickness=t.FRAME_CARD_T) == BOARD

# 5 回目の見直し 5: 竹串や厚紙を刃物で切る形は、道具・「大人がする」・ささくれと尖りの始末を言う
for k in ("karakuri", "hashigo", "saru_take", "saru_sao", "yakko"):
    q = {**P, "kind": k}
    assert any("ニッパー" in x or "カッター" in x for x in t.materials(q)), k
    assert any("大人がする" in x for x in t.steps(q)) and any("ささくれ" in x or "尖り" in x for x in t.steps(q)), k

# 5 回目の見直し 6: 噛む角は、厚紙と貼った紙を足した厚さで見る。厚紙の耳は筋を付けて折る
q = {**P, "kind": "saru_take"}
teff = P["plate_t"] + P["paper_thickness"]
assert abs(t.motion(q)["lock"] - t.lock_angle(P["hole_d"], P["pole_d"], teff)) < 1e-9
assert any("筋" in x for x in t.steps(q))
assert [f.floor for f in t.check_range({**q, "plate_t": 1.6})] == ["F5.range"]  # 2mm の厚紙は耳が折れないので受けない

# 5 回目の見直し 7: 床が使わない load_arm は持たない（粘土の置き場は、どちらの形でも板の傾きを変えない）
assert "load_arm" not in t.motion({**P, "kind": "saru_take"}) and "load_arm" not in t.motion({**P, "kind": "saru_sao"})

# 6 回目の見直し 1: 7 回目の見直しで、切り抜きと穴を分けた（下の 7 回目の見直し 3）

# 6 回目の見直し 2: からくり台の枠は厚紙に貼る（紙 1 枚だと回すうちに曲がり、O と A の間が保てない）
kq = {**P, "kind": "karakuri"}
assert "厚紙" in next(r for r in t.bom(kq) if r["key"] == "frame")["material"]
assert any("厚紙" in m for m in t.materials(kq)) and any("厚紙" in x and "枠" in x for x in t.steps(kq))

# 6 回目の見直し 3: 梯子のつまみは前へだけ出す。後ろへ出すと、押した角に届く前に台に乗り上げる（床の幾何で確かめる）
hq = {**P, "kind": "hashigo"}
back = t.knob_back_hit(hq)
assert back is not None and back < t.motion(hq)["usable"], back
assert any("台の前" in x and "前へだけ" in x for x in t.steps(hq)), t.steps(hq)

# 6 回目の見直し 4: plate_t は厚紙の厚さ（0.5mm 以上）しか受けない
assert [f.floor for f in t.check_range({**P, "kind": "saru_take", "plate_t": 0.4})] == ["F5.range"]
assert t.check_range({**P, "kind": "saru_take", "plate_t": 0.5}) == []

# 7 回目の見直し 1: 厚紙に貼る形は、厚紙に貼る手順がはさみで切る手順より前にあり、手順に番号が順に振られる
for k in ("karakuri", "saru_take", "saru_sao"):
    st = t.steps({**P, "kind": k})
    glue = next(i for i, x in enumerate(st) if "厚紙に貼" in x)
    cut = next(i for i, x in enumerate(st) if "はさみで切る" in x)
    assert glue < cut, (k, st)
    assert all(x.startswith(f"手順 {i + 1}: ") for i, x in enumerate(st)), st

# 7 回目の見直し 2: からくり台の厚紙の枠は、大人がカッターを下敷きの上で定規に当てて切る
st = t.steps({**P, "kind": "karakuri"})
assert any("枠" in x and "大人" in x and "カッター" in x and "下敷き" in x and "定規" in x for x in st), st

# 7 回目の見直し 3: カッターは中を切り抜く所か厚紙がある形だけ。穴だけの形は目打ちと下敷きの行だけ
for k in t.KINDS:
    q = {**P, "kind": k}
    ps = t.parts(q)
    cutter = any(x.cuts for x in ps) or k in ("karakuri", "saru_take", "saru_sao")
    m = t.materials(q)
    assert any("カッター" in x for x in m) == cutter, (k, m)
    assert any("カッター" in x for x in t.steps(q)) == cutter, k
    assert all("大人" in x for x in t.steps(q) if "カッター" in x and "背" not in x), k  # 刃で切る手順は大人がする（筋を付けるカッターの背は除く）
    if any(x.holes for x in ps):
        assert any("目打ち" in x and "下敷き" in x and "大人" in x for x in m), (k, m)
        assert any("目打ち" in x and "大人" in x for x in t.steps(q)), k
assert not any("カッター" in x for x in t.materials({**P, "kind": "hashigo"}))  # 切り抜きの無い形

# 7 回目の見直し 4: plate_t の範囲は、使う形（登る板）だけで見る
assert t.check_range({**P, "kind": "sumo", "plate_t": 0.1}) == []
assert [f.floor for f in t.check_range({**P, "kind": "saru_take", "plate_t": 0.1})] == ["F5.range"]

# 8 回目の見直し 1: 登る形で、目打ちで丸い穴をあける手順は竹串の穴を除き、竹串の穴は小さくあけて広げる手順の番号を指す
for k in ("saru_take", "saru_sao"):
    st = t.steps({**P, "kind": k})
    awl = next(x for x in st if "目打ちであける" in x)
    widen = next(i for i, x in enumerate(st) if "少しずつ広げる" in x)
    assert f"竹串の穴は手順 {widen + 1} で" in awl, (awl, widen)

# 8 回目の見直し 2: 厚紙に貼る部品は、余白を残して粗く切り取ってから貼る
for k in ("karakuri", "saru_take", "saru_sao"):
    assert any("余白" in x and "粗く" in x and "厚紙に貼" in x for x in t.steps({**P, "kind": k})), k

# 8 回目の見直し 3: からくり台の門の口を切る手順は 1 つ
assert sum("門の口" in x and "切" in x for x in t.steps({**P, "kind": "karakuri"})) == 1

# 8 回目の見直し 4: 手順の番号（「手順 n:」）と部品の番号（「部品 n」）を分けて書く。部品の番号は型紙の部品にある
import re
for k in t.KINDS:
    q = {**P, "kind": k}
    nums = {x.number for x in t.parts(q)}
    for x in t.steps(q):
        body = x.split(": ", 1)[1]
        assert not re.match(r"[0-9]+ ", body), x  # 文の頭に裸の番号を置かない
        assert {int(n) for n in re.findall(r"部品 ([0-9]+)", body)} <= nums, x

# 9 回目の見直し 1: 厚紙に貼る部品を粗く切る余白は、型紙の上で隣の部品までの距離より小さい（余白で隣の部品を切り落とさない）
import re as _re
from omochae.__main__ import load_source
from omochae.compose import compose
from omochae.floors import part_poly
for k in ("karakuri", "saru_take", "saru_sao"):
    q = {**P, "kind": k}
    _, lay, fs = compose("lever_link", q, load_source(t.SOURCES[k]))
    assert not fs, fs
    polys = {x.key: part_poly(x) for x in lay["parts"]}
    card = [x.key for x in lay["parts"] if "厚紙" in next(r for r in t.bom(q) if r["key"] == x.key)["material"]]
    near = min(polys[a].distance(polys[b]) for a in card for b in polys if b != a)
    step = next(x for x in t.steps(q) if "粗く" in x)
    margin = float(_re.search(r"周りに ([0-9.]+)mm", step).group(1))
    assert margin < near, (k, margin, near)

# 9 回目の見直し 2: 組んだ後に竹串を切りそろえる手順は、同じ手順の中で大人がすると言う
for k in t.KINDS:
    for x in t.steps({**P, "kind": k}):
        if "切りそろえる" in x:
            assert "大人がする" in x, x
print("ok")
