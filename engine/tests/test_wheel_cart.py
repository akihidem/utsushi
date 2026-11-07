"""雛形 wheel_cart の床 F5.wheel の式の要所を、境目の数点で確かめる。言葉で書いた条件は向きを間違えやすいので、ここで数える。"""
from omochae.floors import check_bom
from omochae.templates import wheel_cart as w

RAT = {**w.DEFAULTS, "ride": "rat"}
STICK = {**w.DEFAULTS, "ride": "stick"}


def msgs(p):
    out = w.check_physics(p)
    assert all(f.floor == "F5.wheel" for f in out), out
    return [f.where + ":" + f.message for f in out]


# 既定の寸法はどちらの形も通り、刷る部品は全部部品表に載る
for p in (RAT, STICK):
    assert msgs(p) == [], msgs(p)
    assert check_bom(w.bom(p), w.parts(p)) == []

# 1. 床: 半径 - 軸の高さ が MIN_GROUND ちょうどなら通り、それより小さければ落ちる（両方の形）
for p in (RAT, STICK):
    a = p["axle_height"]
    assert not any("床を擦る" in m for m in msgs({**p, "wheel_r": a + w.MIN_GROUND}))
    assert any("床を擦る" in m for m in msgs({**p, "wheel_r": a + w.MIN_GROUND - 0.5}))

# 2. 側面: 鼠車のすき間、前後の車輪どうし。春駒の二股の内の幅は、車輪の厚み（重ねた枚数で増える）で決まる
assert any("側面" in m for m in msgs({**RAT, "wheel_gap": w.MIN_SIDE_GAP - 0.5}))
assert not msgs({**RAT, "wheel_gap": w.MIN_SIDE_GAP})
# 胴 70mm・前後 12mm の時、軸の間は 46mm。半径 22 で車輪 2 つ 44mm + 1.5mm が入らない
assert any("前と後ろの軸の間" in m for m in msgs({**RAT, "wheel_r": 22.5}))
assert w.wheel_thickness({**STICK, "wheel_layers": 4}) > w.wheel_thickness(STICK)
thin = {**STICK, "fork_inner": 4, "stick_t": 3}
assert not any("内の幅" in m for m in msgs({**thin, "wheel_layers": 1}))  # 0.15 + 3 <= 4
assert any("内の幅" in m for m in msgs({**thin, "wheel_layers": 4}))  # 1.35 + 3 > 4
# 車輪の上の端が割り箸の先に当たる: 腕 34 - 差し込み 4 - 軸 7 - 半径 = すき間
assert any("割り箸の先" in m for m in msgs({**STICK, "wheel_r": 22}))
assert not any("割り箸の先" in m for m in msgs({**STICK, "wheel_r": 21.5}))

# 3. 穴の余裕（軸の高さ・前後の位置・胴の上の縁・二股の腕の幅）
assert any("軸の穴" == m.split(":")[0] for m in msgs({**RAT, "axle_height": 3, "wheel_r": 6}))
assert any("前の壁" in m for m in msgs({**RAT, "inset_front": 3}))
assert any("上の縁" in m for m in msgs({**RAT, "body_height": 20, "axle_height": 17, "wheel_r": 20}))
assert any("腕の縁" in m for m in msgs({**STICK, "fork_width": 7, "stick_t": 3}))

# 4. 重心: 対称なら真ん中。車輪の重さ（芯の厚紙）が重心を軸へ引くので、片側へ寄せた軸で倒れる・倒れないが分かれる
assert abs(w.cart_com_x(RAT) - RAT["body_length"] / 2) < 1e-9
tip = {**RAT, "body_length": 80, "inset_front": 45, "inset_rear": 10, "wheel_r": 10, "rider_at": 0.25}
assert any("倒れる" in m for m in msgs(tip))
# 同じ寸法で車輪の芯を増やすと、重い車輪が重心を前の軸の内へ引き、倒れなくなる
assert w.cart_com_x({**tip, "wheel_layers": 6}) > w.cart_com_x(tip)
assert not any("倒れる" in m for m in msgs({**tip, "wheel_layers": 6}))
# 人形を前へ寄せると重心も前へ動く（向きの確かめ）
assert w.cart_com_x({**RAT, "rider_at": 0.2}) < w.cart_com_x(RAT)
# 春駒は手で持つので重心は見ない
assert not any("重心" in m for m in msgs(STICK))

# 5. ぶりぶり（mallet）: 軸は頭の芯を通るので、床は頭の角（外接円の半径）で見る
MALLET = {**w.DEFAULTS, "ride": "mallet"}
assert msgs(MALLET) == [], msgs(MALLET)
assert check_bom(w.bom(MALLET), w.parts(MALLET)) == []
assert not any("床を擦る" in m for m in msgs({**MALLET, "head_r": 10}))  # 12 - 10 = 2 ちょうど
assert any("床を擦る" in m for m in msgs({**MALLET, "head_r": 10.5}))
side, apo = w.octagon(MALLET)
assert abs(side - 2 * 9 * 0.38268) < 1e-3 and apo < MALLET["head_r"]
assert any("蓋のすき間" in m for m in msgs({**MALLET, "wheel_gap": 1}))
# 柄の先と軸: 内接円 8.3 - 差し込み - 竹串の半径 1.5 が 1.5 を割ると落ちる
assert not any("軸が回らない" in m for m in msgs({**MALLET, "handle_in": 5}))
assert any("軸が回らない" in m for m in msgs({**MALLET, "handle_in": 6}))
assert any("頭の面" in m for m in msgs({**MALLET, "stick_t": 5}))  # 面の幅 6.9 に 5 + 2 が入らない
# 範囲（head_r 6 以上）では内接円が 5.5mm 以上で穴の余裕は足りる。式の向きは範囲の外の値で確かめる（check_physics は範囲を見ない）
assert any("蓋の縁" in m for m in msgs({**MALLET, "head_r": 4, "wheel_r": 8, "stick_t": 3, "handle_in": 0}))

# 6. 床の式が頼る組み立ての位置は、型紙か組み方の文に出す（式だけが知る位置にしない）
# 6a. 春駒: 割り箸を差し込む深さ stick_in を、二股の腕に印として刷り、組み方の文にも書く
stick_p = {**STICK, "stick_in": 6}
fork = next(q for q in w.parts(stick_p) if q.key == "fork")
A, fi = stick_p["fork_arm"], stick_p["fork_inner"]
marks = [it for it in fork.art if it.get("mark") == "stop"]
ys = sorted(round(y, 6) for it in marks for _, y in it["pts"])
assert ys == [A - 6, A - 6, A + fi + 6, A + fi + 6], ys
assert any("6mm" in s and "割り箸" in s for s in w.steps(stick_p)), w.steps(stick_p)
# 6b. 鼠車: 人形を貼る位置 rider_at を、胴の上の面に印として刷り、組み方の文にも書く
rat_p = {**RAT, "rider_at": 0.4}
body = next(q for q in w.parts(rat_p) if q.key == "body")
H, L, g, W = rat_p["body_height"], rat_p["body_length"], rat_p["glue"], rat_p["body_width"]
mark = [it for it in body.art if it.get("mark") == "rider"]
assert len(mark) == 1, "人形の位置の印が無い"
xs = [x for x, _ in mark[0]["pts"]]
assert abs((min(xs) + max(xs)) / 2 - (H + 0.4 * L)) < 1e-6 and all(g <= y <= g + W for _, y in mark[0]["pts"])
assert any(f"{0.4 * L:g}mm" in s and "人形" in s for s in w.steps(rat_p)), w.steps(rat_p)
# 6c. ぶりぶり: 柄を差し込む深さ handle_in を組み方の文で、印の付け方まで言う（柄は刷る部品でないので鉛筆の印）
assert any(f"{MALLET['handle_in']}mm" in s and "印" in s for s in w.steps(MALLET)), w.steps(MALLET)
# 6d. 春駒の見取り図: 二股の腕は軸から上へ A - a、下へ a。床の線を越えない
shapes = w.diagram(0, 0, 60, 80, STICK)
floor = [s for s in shapes if s["kind"] == "line" and s["y1"] == s["y2"]][-1]["y1"]
arm = shapes[1]
assert arm["y"] + arm["h"] <= floor + 1e-9, (arm, floor)

# 7a. 春駒とぶりぶりは紙の中の四角い穴を切るので、用意する物にカッターを、組み方に「カッターは大人がする」を書く（虎の首の形と同じ言葉）
for p in (STICK, MALLET):
    assert any("カッター" in m for m in w.materials(p)), w.materials(p)
    assert any("四角い穴" in s and "カッターは大人がする" in s for s in w.steps(p)), w.steps(p)
assert not any("カッター" in m for m in w.materials(RAT))  # 鼠車に中の穴は無い
# 7b. 柄の差し込みが 0mm では貼れずに抜ける。範囲の下限で落とす
assert [f.floor for f in w.check_range({**MALLET, "handle_in": 0})] == ["F5.range"]
assert w.check_range({**MALLET, "handle_in": w.RANGES["handle_in"][0]}) == [] and w.RANGES["handle_in"][0] >= 2
# 7c. 枚数は整数だけ。2.0 のような小数の形も落とす（「4.0 枚」と刷らないため）
assert [f.floor for f in w.check_range({**RAT, "wheel_layers": 2.0})] == ["F5.range"]
assert w.check_range({**RAT, "wheel_layers": 2}) == []

# 8. 中の四角い穴も切る線と同じ実線で刷るので、最初の「部品を切る」行で穴を除き、カッターの行を折る行より前に置く
for p in (STICK, MALLET):
    st = w.steps(p)
    cut = next(i for i, x in enumerate(st) if "実線で切る" in x)
    assert "中の四角い穴はまだ切らない" in st[cut], st[cut]
    knife = next(i for i, x in enumerate(st) if "カッターは大人がする" in x)
    # 折る行は谷折りか山折り（ぶりぶりの頭と蓋は、色の面を外にする山折りに直した。制作者の決定 2026-11-06）
    fold = next(i for i, x in enumerate(st) if "谷折り" in x or "山折り" in x)
    assert cut < knife < fold, (cut, knife, fold)
assert "中の四角い穴" not in w.steps(RAT)[1]  # 鼠車に中の穴は無い

# 9. 位置の印（鼠車の人形を貼る所・春駒の割り箸を止める所）は、エンジンの位置の印（kind "mark"）で刷る。
# 雛形が色と線を決めて濃い実線で描くと、「部品を実線で切る」の行で切る線と取り違え、四角を穴として切り抜くか、腕を切り離しうる。
# 破線にすると谷折りと取り違える。色と線の形は描く所（render）が 1 つに決め、凡例に意味が出る
from omochae import render
from omochae.__main__ import load_source
from omochae.compose import compose
for p, key, tag in ((RAT, "body", "rider"), (STICK, "fork", "stop")):
    q = next(x for x in w.parts(p) if x.key == key)
    items = [it for it in q.art if it.get("mark") == tag]
    assert items, (tag, "位置の印が無い")
    assert all(it["kind"] == "mark" and "stroke" not in it and "sw" not in it for it in items), (tag, items)
    _, lay, fl = compose("wheel_cart", p, load_source(w.SOURCES[p["ride"]]))
    assert fl == [], [f.line() for f in fl]
    assert any(t.text and "位置の印（切らない・折らない）" in t.text for t in lay["texts"]), (tag, "凡例に位置の印が無い")
    svg = render.to_svg(lay)
    assert svg.count(f'stroke-dasharray="{render.MARK_DASH}"') == len(items) + 1, tag  # 印の数 ＋ 凡例の見本 1 本
# 春駒の二股には、印のほかに線の絵を置かない（腕を横切る実線が残ると切られる）
assert not [it for it in next(x for x in w.parts(STICK) if x.key == "fork").art if it["kind"] == "line"]
# 印を刷らない形（ぶりぶりは柄に鉛筆で印を付ける。春駒で差し込みが 0 に近い時は折り目が印）の凡例には出さない
for p in (MALLET, {**STICK, "stick_in": 0.5}):
    _, lay, fl = compose("wheel_cart", p, load_source(w.SOURCES[p["ride"]]))
    assert fl == [], [f.line() for f in fl]
    assert not any(t.text and "位置の印" in t.text for t in lay["texts"]), p["ride"]
# 組み方の文は、印を刷った見た目（赤茶の点の線）で言う。刷らない時は折り目で止めると言う
assert any("人形" in s and "赤茶の点の線" in s and "四角い印" in s for s in w.steps(RAT)), w.steps(RAT)
assert any("割り箸の先" in s and "赤茶の点の線" in s and "切らない" in s for s in w.steps(STICK)), w.steps(STICK)
st0 = w.steps({**STICK, "stick_in": 0.5})
assert any("割り箸の先" in s and "折り目（破線）で止めて貼る" in s for s in st0) and not any("赤茶" in s for s in st0), st0
# 春駒の文で、二股の折り目を「頭の折り目」と言わない（頭は馬の頭の部品の名）
assert not any("頭の折り目" in s for q in (STICK, {**STICK, "stick_in": 0.5}) for s in w.steps(q))
# 鼠車の印は閉じた四角（3 辺だけの コ の字にしない）で、人形の耳の大きさ（幅は人形の 0.6 倍・奥行き 7mm）
rider = next(it for it in next(x for x in w.parts(RAT) if x.key == "body").art if it.get("mark") == "rider")
assert rider["closed"] is True and len(rider["pts"]) == 4, rider
rx, ry = [x for x, _ in rider["pts"]], [y for _, y in rider["pts"]]
assert abs(max(rx) - min(rx) - RAT["figure_w"] * 0.6) < 1e-9 and abs(max(ry) - min(ry) - 7) < 1e-9, rider
# 印を刷る下限は、型紙（_fork）と組み方の文で同じ。下限のすぐ上では印を 2 本刷って文も印と言い、下限ちょうどでは刷らずに折り目と言う
for d, n in ((w.STOP_MARK_MIN, 0), (w.STOP_MARK_MIN + 0.1, 2)):
    q = {**STICK, "stick_in": d}
    stops = [it for it in next(x for x in w.parts(q) if x.key == "fork").art if it.get("mark") == "stop"]
    assert len(stops) == n, (d, len(stops))
    assert any("赤茶の点の線" in s for s in w.steps(q)) == bool(n), (d, w.steps(q))
print("ok")
