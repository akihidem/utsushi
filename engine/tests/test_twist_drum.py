"""でんでん太鼓の床（F5.drum）の式の要所を数点で確かめる。糸の長さの窓と帯の長さは言葉で決めると間違えやすいので、ここで数える。"""
import math

from omochae.compose import TEMPLATES
from omochae.templates import twist_drum as t

P = dict(t.DEFAULTS)
assert TEMPLATES["twist_drum"] is t, "templates/ に置けば登録される"
assert t.check_physics(P) == [] and not t.check_range(P)

# 帯の長さ ＝ 円周（厚みの真ん中）＋ 継ぎ目の糊代。刷る帯の外形の長さも同じ値
band = next(q for q in t.parts(P) if q.key == "band")
c = 2 * math.pi * (P["radius"] - P["paper_thickness"] / 2)
assert abs(band.width - (c + P["seam_glue"])) < 1e-9 and abs(t.band_length(P) - band.width) < 1e-9
# 歯の間隔を全部足すと円周になる（歯が円周を余さず覆う）
n, pitch, inset = t.tab_teeth(P)
assert abs(n * pitch - c) < 1e-9 and pitch - 2 * inset > 1

# 糸の窓: 下限ちょうどの糸は、面の中心から半径の半分の所を打つ
low, high = t.cord_window(P)
assert abs(t.strike_offset({**P, "cord_length": low}) - t.STRIKE_ZONE * P["radius"]) < 1e-9
# 既定の寸法では、上限は柄に絡む側（√2·R − 玉の半径）で決まる
assert abs(high - (math.sqrt(2) * P["radius"] - P["stick_d"] / 2 - P["bead_d"] / 2)) < 1e-9
# 窓の内は通り、外は F5.drum の糸で落ちる
assert t.check_physics({**P, "cord_length": (low + high) / 2}) == []
for bad in (low - 0.5, high + 0.5):
    fs = t.check_physics({**P, "cord_length": bad})
    assert [(f.floor, f.where) for f in fs] == [("F5.drum", "糸")], fs
# 玉が大きいほど絡みやすい（上限が下がる）
assert t.cord_window({**P, "bead_d": 12})[1] < high
# 奥行きの半分に届かない糸は面に届かない
assert t.strike_offset({**P, "cord_length": P["depth"] / 2}) is None

# 柄の穴は帯の幅の真ん中。縁までの余白が足りないと落ちる
fs = t.check_physics({**P, "depth": 10, "stick_d": 5})
assert any(f.where == "柄の穴" and "帯の縁" in f.message for f in fs), fs
# 柄の穴は継ぎ目の糊代に重ならない（小さい鼓に広い糊代）
fs = t.check_physics({**P, "radius": 15, "seam_glue": 12, "depth": 10, "cord_length": 12})
assert any("継ぎ目" in f.message for f in fs), fs
# 穴は帯の中、柄の穴どうしは円周の半分（向かい合う）、糸の穴は柄から 90°
pos = t.hole_positions(P)
assert abs((pos["stick"][1] - pos["stick"][0]) - c / 2) < 1e-9 and abs((pos["cord"][0] - pos["stick"][0]) - c / 4) < 1e-9

# 竹串の長さが足りないと落ちる
fs = t.check_physics({**P, "handle_length": 130})
assert any(f.where == "柄" for f in fs), fs

# 鳥の面だけ幣の房があり、部品表にも載る
assert "streamer" in {q.key for q in t.parts({**P, "face": "tori"})}
assert "streamer" not in {q.key for q in t.parts(P)}
assert {r["key"] for r in t.bom({**P, "face": "tori"})} >= {"streamer", "stick", "cord", "bead"}

# ---- 諫鼓（face=kanko）----
K = {**P, "face": "kanko"}
assert t.check_physics(K) == [], t.check_physics(K)
# 帯の長さは諫鼓の半径から出し、柱の四角い穴は帯の幅の真ん中・継ぎ目の向かいにある
kb = next(q for q in t.parts(K) if q.key == "band")
kc = 2 * math.pi * (K["k_radius"] - K["paper_thickness"] / 2)
assert abs(kb.width - (kc + K["seam_glue"])) < 1e-9 and kb.holes == [] and len(kb.cuts) == 1
x, y, w, h = kb.cuts[0]
assert abs(x + w / 2 - kc / 2) < 1e-9 and abs(y + h / 2 - (K["tab"] + K["k_length"] / 2)) < 1e-9
# 窓: 下限ちょうどで、玉の表が面に触れる（軸から玉の中心まで face_gap − 玉の半径）
low, high, dz = t.kanko_window(K)
assert abs(t.wheel_anchor(K) + low - (K["face_gap"] - K["bead_d"] / 2)) < 1e-9 and dz == 0
# 上限ちょうどで、打つ点のずれが STRIKE_ZONE·R になる
rho, g = t.wheel_anchor(K) + high, K["face_gap"] - K["bead_d"] / 2
assert abs(math.sqrt(rho * rho - g * g) - t.STRIKE_ZONE * K["k_radius"]) < 1e-9
# 花車が鼓の中心の高さからずれるほど窓が狭まり、kR を越えると無くなる
assert t.kanko_window({**K, "peg_height": K["peg_height"] + 5})[1] < high
assert t.kanko_window({**K, "peg_height": 20})[1] is None
for bad in (low - 0.5, high + 0.5):
    fs = t.check_physics({**K, "k_cord": bad})
    assert [(f.floor, f.where) for f in fs] == [("F5.drum", "糸")], fs
# 花車が面に近すぎる・軸が台から出る・壁が低くて棒の穴が取れない
assert any(f.where == "花車" for f in t.check_physics({**K, "wheel_r": 16, "face_gap": 17, "k_cord": 3}))
assert any(f.where == "軸" for f in t.check_physics({**K, "base_length": 60}))
assert any(f.where == "棒の穴" for f in t.check_physics({**K, "base_height": 10}))
# 諫鼓の部品と部品表（紙でない物も）が合う
assert {q.key for q in t.parts(K)} == {"front", "back", "band", "post", "base", "wheel", "rodtab", "gauge", "bearing"}
assert {r["key"] for r in t.bom(K)} >= {"peg", "rod", "pull", "cord", "bead"}
from omochae.floors import check_bom
assert check_bom(t.bom(K), t.parts(K)) == []

# ---- レビューの指摘（2026-11-04）を押さえる行 ----
import re
# 1. 玉は点でない。玉の表が面に触れる時、中心は面の外に玉の半径だけ出る。糸は帯の縁で曲がる（38）ので、
#    下限 ＝ 奥行きの半分 ＋ √((R/2)² + 玉の半径²)。既定の寸法で 9 + √(13² + 4²) ≒ 22.6mm
low, _ = t.cord_window(P)
assert abs(low - (P["depth"] / 2 + math.hypot(P["radius"] / 2, P["bead_d"] / 2))) < 1e-9, low
assert t.check_physics({**P, "cord_length": 17}) != [], "玉の半径を入れると 17mm では面の真ん中に届かない"
#    諫鼓は玉が軸の側から面へ近づくので、軸から面までの距離から玉の半径を引く（向きが逆で、引くのが正しい）
assert abs(t.wheel_anchor(K) + t.kanko_window(K)[0] - (K["face_gap"] - K["bead_d"] / 2)) < 1e-9
# 2. 鳥の面: 幣の房の上の帯（STREAMER_TOP）を、胴の上に出た竹串に巻いて貼れるだけ、串を上へ出す
tori = {**P, "face": "tori"}
out_mm = [float(m) for s in t.steps(tori) for m in re.findall(r"上へ (\d+(?:\.\d+)?)mm 出します", s)]
assert out_mm and out_mm[0] >= t.STREAMER_TOP, (out_mm, t.STREAMER_TOP)
#    串を長く出す分も、竹串の長さの床で数える
need = P["handle_length"] + 2 * P["radius"] + out_mm[0]
#    境は先を落とした竹串（SKEWER_USABLE）で見る。SKEWER_LEN で見ると 119mm を 102mm の限りと比べる事になり、境を押さえない
fit = math.floor(t.SKEWER_USABLE - 2 * P["radius"] - out_mm[0])
assert any(f.where == "柄" for f in t.check_physics({**tori, "handle_length": fit + 1}))
assert not any(f.where == "柄" for f in t.check_physics({**tori, "handle_length": fit}))
# 3. 柄に絡まない条件は厳密に L + 玉の半径 < √2·R。等しい糸（柄にちょうど届く）は落とす
edge = math.sqrt(2) * P["radius"] - P["stick_d"] / 2 - P["bead_d"] / 2
assert any(f.where == "糸" for f in t.check_physics({**P, "cord_length": edge})), "柄にちょうど届く糸を通した"
# 4. 刷る形ごとの出典。既定の SOURCE は菊の面
assert t.SOURCES == {"kiku": t.SOURCE, "tori": "NDL-1187053-R0000029-L-twist_drum", "kanko": "NDL-1187053-R0000010-R-twist_drum"}
# ---- 2 回目のレビューの指摘（2026-11-04）を押さえる行 ----
def nums(text, pat):
    return [float(m) for m in re.findall(pat, text)]
# 5. 花車の高さは、式と見取り図と同じく台の上の面から測る。組み方の文の数・物差しの紙・軸の竹串の長さが同じ基準で合う
st = " ".join(t.steps(K))
assert nums(st, r"台の上の面から (\d+(?:\.\d+)?)mm") == [K["peg_height"]], st
top = nums(st, r"軸の上のはしからは (\d+(?:\.\d+)?)mm 下")[0]
cut = nums(next(r for r in t.bom(K) if r["key"] == "peg")["material"], r"長さ (\d+(?:\.\d+)?)mm")[0]
assert cut == K["base_height"] + K["peg_height"] + top, (cut, top)
assert {q.key: q for q in t.parts(K)}["gauge"].height == K["peg_height"]
# 6. 柄の竹串を切る長さ ＝ 柄 ＋ 胴の直径 ＋ 胴の上。組み方の文と部品表が同じ値で、巻き紙は柄より 2mm 短い
for face in ("kiku", "tori"):
    p = {**P, "face": face}
    c = P["handle_length"] + 2 * P["radius"] + t.top_out(p)
    assert nums(" ".join(t.steps(p)), r"竹ぐしを (\d+(?:\.\d+)?)mm に切ります") == [c], face
    assert f"{c:g}mm に切る" in next(r for r in t.bom(p) if r["key"] == "stick")["material"]
    assert t.wrap_size(p)[1] == P["handle_length"] - 2
# 7. 棒の切り欠きは刷る留め具に置き換え、結ぶ所を棒の北の端からの長さで決める（押し込んだ時に軸の真横）
assert "切り欠き" not in st
assert nums(st, r"棒の北のはしから (\d+(?:\.\d+)?)mm") == [t.rodtab_pos(K)] and t.rodtab_pos(K) == t.rod_north_out(K) + t.peg_pos(K) - t.TAB_W / 2
tab = {q.key: q for q in t.parts(K)}["rodtab"]
assert abs(tab.width - (t.rod_perimeter(K) + 2 * t.TAB_FLAG)) < 1e-9 and len(tab.holes) == 2
#    引ける長さで軸が 1 回も回らない寸法は落とす
assert t.pull_turns(K) >= 1 and any(f.where == "棒" for f in t.check_physics({**K, "base_length": 70}))
# ---- 3 回目のレビューの指摘（2026-11-04）を押さえる行 ----
# 8. 諫鼓で、糸が玉の半径より短いと玉が花車に重なる（窓の式だけでは通っていた寸法）
#    （台は 80mm にする。既定の 90mm のままだと、軸が北へ寄った分だけ引ける長さと棒が伸び、棒が竹串に収まらない床も一緒に落ちる）
bad = {**K, "k_radius": 24, "face_gap": 10, "wheel_r": 8, "bead_d": 14, "k_cord": 3, "base_length": 80}
assert [f.where for f in t.check_physics(bad)] == ["糸"], [f.line() for f in t.check_physics(bad)]
# 9. 引き切っても棒の北の端が北の壁の穴に HOLE_MARGIN 残る。回る数はこの引ける長さで数える
#    （北に出す長さが引ける長さ＋余白か、は式そのものなので見ない。代わりに、棒が竹串の長さに収まるかを見る）
assert t.rod_length(K) <= t.SKEWER_USABLE
#    回る数は、棒の動いた長さをそのまま軸の周りで割った数より少ない（解けるのは旗の穴が軸から遠ざかった分。式は 31 で見る）
assert 0 < t.pull_turns(K) < t.pull_travel(K) / (math.pi * K["stick_d"])
assert nums(" ".join(t.steps(K)), r"北の壁から (\d+(?:\.\d+)?)mm 出します") == [round(t.rod_north_out(K))]
# 10. 柄の太さの分、絡む長さは短い（柄の表まで √2·R − 柄の半径）
assert any(f.where == "糸" for f in t.check_physics({**P, "cord_length": math.sqrt(2) * P["radius"] - P["bead_d"] / 2 - P["stick_d"] / 2 + 0.5}))
# 11. 諫鼓の窓は両端を含む。花車の高さのずれが kR ちょうどでも、下限＝上限の 1 点の糸は通る
edge = {**K, "peg_height": 47}
lo, hi, dz = t.kanko_window(edge)
assert dz == t.STRIKE_ZONE * K["k_radius"] and hi is not None and abs(hi - lo) < 1e-9
assert t.check_physics({**edge, "k_cord": lo}) == []
# ---- 4 回目のレビューの指摘（2026-11-05）を押さえる行 ----
# 12. 引く棒が竹串（SKEWER_LEN）より長くなる寸法は落とす（台が長いと、北に出す分も伸びる）
bad = {**K, "base_length": 100, "face_gap": 14, "k_cord": 5.8}
assert [f.where for f in t.check_physics(bad)] == ["棒"], [f.line() for f in t.check_physics(bad)]
# 13. 端数の出る寸法でも、刷る 3 つの数（北に出す長さ・留め具の位置・棒の長さ）は 1 つの丸めた値から出て食い違わない。
#     北に出す長さは切り上げるので、引き切っても余白が残る
odd = {**K, "base_length": 79.6, "k_length": 43}
st = " ".join(t.steps(odd))
north = nums(st, r"北の壁から (\d+(?:\.\d+)?)mm 出します")[0]
tabp = nums(st, r"棒の北のはしから (\d+(?:\.\d+)?)mm")[0]
rod = nums(next(r for r in t.bom(odd) if r["key"] == "rod")["material"], r"長さ (\d+(?:\.\d+)?)mm")[0]
assert north == int(north) and north - t.pull_travel(odd) >= t.HOLE_MARGIN
assert abs(tabp - (north + t.peg_pos(odd) - t.TAB_W / 2)) < 1e-9 and abs(rod - (north + odd["base_length"] + t.ROD_GRIP)) < 1e-9
# 14. 玉が花弁の先にちょうど触れる糸も落とす（柄に絡む側と同じ厳しさ）
eq = {**K, "k_cord": K["bead_d"] / 2 + (K["wheel_r"] - t.wheel_anchor(K))}
assert any("花車に重なる" in f.message for f in t.check_physics(eq))
# ---- 5 回目のレビューの指摘（2026-11-05）を押さえる行 ----
# 15. 刷る位置は留め具の北の縁。押し込んだ時に旗の穴（留め具の真ん中）が軸の真横に来る。
#     旗は南の壁の棒の穴の上の縁より高く出るので、引くと壁に当たって止まる（止め具になる）。引き切っても棒の北の端は北の穴に残る
st = " ".join(t.steps(K))
x = nums(st, r"留め具の北のふちは、棒の北のはしから (\d+(?:\.\d+)?)mm の所")[0]
north = nums(st, r"北の壁から (\d+(?:\.\d+)?)mm 出します")[0]
assert abs((x - north + t.TAB_W / 2) - t.peg_pos(K)) < 1e-9, "旗の穴（留め具の真ん中）が軸の真横に来ない"
#     旗の先は、棒が穴の底に乗った時（引く時の普通の状態）でも、穴の上の縁より HOLE_MARGIN 以上高く出て壁に掛かる（flag_tip_z は浮いた時なので使わない）
rest_tip = t.HOLE_MARGIN + 2 * K["stick_d"] + K["paper_thickness"] + t.TAB_FLAG
assert rest_tip - t.rod_cut_top(K) >= t.HOLE_MARGIN, "旗が穴の上の縁より十分に出ない"
assert abs(t.pull_travel(K) - (K["base_length"] - (x - north + t.TAB_W))) < 1e-9, "刷った位置から数えた引ける長さが pull_travel と違う"
assert north - t.pull_travel(K) >= t.HOLE_MARGIN
# 16. 棒が穴の上の縁まで浮いても、旗の先（帯の厚み込み）が天井の下の面（天井の紙の厚みを引く）から 0.5mm 空く
assert t.ceiling_z(K) - t.flag_tip_z(K) >= 0.5
for bh in (13, 14):
    assert [f.where for f in t.check_physics({**K, "base_height": bh})] == ["留め具"], bh
assert any(f.where == "留め具" for f in t.check_physics({**K, "base_height": 14, "paper_thickness": 0.5}))
#     旗が軸の側へ倒れても、寸法の範囲のどの端でも旗の先が、軸に巻いた糸の表（軸の半径＋糸の太さ）から ROD_GAP 離れる。東の壁の側へ倒れて当たる狭い台は落とす
assert min(t.rod_off({**K, "stick_d": sd, "paper_thickness": pt}) - sd / 2 - t.WIND_D - (t.TAB_FLAG + pt)
           for sd in t.RANGES["stick_d"] for pt in t.RANGES["paper_thickness"]) >= t.ROD_GAP - 1e-9
assert [f.where for f in t.check_physics({**K, "base_width": 34})] == ["留め具"]
# 17. 竹串のとがった先を切り落とす手順（道具・大人がする）が、どの形にもある。切り落とした分、使える長さは短い
for p in (P, {**P, "face": "tori"}, K):
    st = " ".join(t.steps(p))
    assert "とがった先" in st and "切り落とします" in st and "大人がします" in st and "ニッパー" in st, p["face"]
    assert any("ニッパー" in m for m in t.materials(p))
assert t.SKEWER_USABLE == t.SKEWER_LEN - 2 * t.SKEWER_POINT and t.stick_cut(P) <= t.SKEWER_USABLE
# 18. 柱の足の印は、黒い閉じた四角（切る線に見える）でなく、茶色のかぎの印
marks = [a for a in {q.key: q for q in t.parts(K)}["base"].art if a["kind"] == "line"]
assert len(marks) == 4 and all(a["stroke"] == t.BAND and len(a["pts"]) == 3 for a in marks)
# 19. 諫鼓の用意する物にカッターとテープ、組み方に棒を切って束ねる手順がある（長さは部品表と同じ式）
m = " ".join(t.materials(K))
assert "カッター" in m and "テープ" in m
assert nums(" ".join(t.steps(K)), r"竹ぐし 2 本を (\d+(?:\.\d+)?)mm に切り") == [t.rod_length(K)]
# ---- 最終差分の独立レビュー（2026-11-05）の指摘を押さえる行 ----
# 20. 留め具は刷った面を内にして（真ん中の糊の印を棒に当てて）巻く。両端を棒の真上で立てると、2 枚の旗は刷った面どうしが向き合い、端の糊の印が相手に当たる（折りの種類は 33）。
#     旗の穴は糊の印の中にあるので、巻く糸を 2 枚の穴に通して結んでから貼り合わせる（貼ってからでは穴が糊でふさがる）
sk = t.steps(K)
wrap = next(i for i, s in enumerate(sk) if "16 棒の留め具を棒に巻いて" in s)
tie = next(i for i, s in enumerate(sk) if "穴に通して結びます" in s)
assert "印刷した面を内にして" in sk[wrap] and "のりの印を棒に当て" in sk[wrap] and wrap < tie and "結んでから" in sk[tie] and "はり合わせて、旗" in sk[tie]
assert not any("はり合わせて、旗" in s for s in sk[:tie])
# 21. 先を落とす手順は、諫鼓では 3 本まとめて 1 回（同じ文を 2 度刷らない）。でんでん太鼓では、帯の穴を先であけてから落とす
assert sum("とがった先" in s for s in sk) == 1 and "3 本" in next(s for s in sk if "とがった先" in s)
for p in (P, {**P, "face": "tori"}):
    sp = t.steps(p)
    assert next(i for i, s in enumerate(sp) if "竹ぐしの先で" in s) < next(i for i, s in enumerate(sp) if "とがった先" in s)
# 22. 諫鼓の用意する物で、カッターの行は 1 つ（穴と竹串の両方に使う）
assert sum("カッター" in m for m in t.materials(K)) == 1
# ---- 6 回目のレビューの指摘（2026-11-05）を押さえる行 ----
# 23. 留め具の帯の真ん中（棒に当たる所）に糊の印があり、組み方に「棒に糊で貼る」がある（輪が棒の上を滑らない）
from shapely.geometry import Polygon, box
q = {p.key: p for p in t.parts(K)}["rodtab"]
ring = box(t.TAB_FLAG, 0, q.width - t.TAB_FLAG, t.TAB_W)
#     （番号の箱の分だけ印を空けるので、1 枚で 9 割でなく、合わせて 8.5 割以上）
assert sum(Polygon(g).intersection(ring).area for g in q.glue) > ring.area * 0.85
assert "棒に巻いてはります" in sk[wrap]
# 24. 旗の穴から旗の先・折り目・帯の縁まで HOLE_MARGIN 以上
for hx, hy, r in q.holes:
    fold = min(abs(hx - t.TAB_FLAG), abs(hx - (q.width - t.TAB_FLAG)))
    assert min(hx, q.width - hx, hy, t.TAB_W - hy, fold) - r >= t.HOLE_MARGIN - 1e-9, (hx, hy)
# 25. 穴をあける手順は大人がし、小さい穴（旗・花車の糸の穴、でんでん太鼓の菱形）はまち針で刺す
for p in (P, K):
    poke = [s for s in t.steps(p) if "あけます" in s and "穴" in s]
    assert poke and all("大人" in s for s in poke), poke
assert any("旗の穴" in s and "花車の小さい穴" in s and "まち針" in s for s in t.steps(K))
# ---- 7 回目のレビューの指摘（2026-11-05）を押さえる行 ----
# 26. 留め具の番号は糊の印の上に刷らず（印に番号の箱の分の空きがある）、部品の中で、穴にもかからない
from omochae.compose import LABEL_SIZE, LINE, text_width
lx, ly = q.label_xy
lab = box(lx, ly, lx + text_width(q.label, LABEL_SIZE), ly + LABEL_SIZE * LINE)
assert all(Polygon(g).intersection(lab).area < 1e-9 for g in q.glue) and lab.within(box(0, 0, q.width, t.TAB_W))
from shapely.geometry import Point
assert all(not lab.intersects(Point(hx, hy).buffer(r)) for hx, hy, r in q.holes)
# 27. 刷る棒の穴の上の縁は、北の壁も南の壁も検査と同じ rod_cut_top（床から）
base = {p.key: p for p in t.parts(K)}["base"]
(nx, ny, nw, nh), (sx, sy, sw, sh) = base.cuts
H, L = K["base_height"], K["base_length"]
assert abs(ny + nh - t.rod_cut_top(K)) < 1e-9 and abs((2 * H + L - sy) - t.rod_cut_top(K)) < 1e-9 and nh == sh == t.rod_cut(K)[1]
# 28. 棒の穴の検査（上の余白・東の壁の端）が落ちる時は、留め具の 2 つの検査（天井・東の壁）も範囲のどの端でも一緒に落ちる（棒の穴は単独では落ちない）
for sd in t.RANGES["stick_d"]:
    for pt in t.RANGES["paper_thickness"]:
        for bh in t.RANGES["base_height"]:
            for bw in t.RANGES["base_width"]:
                c = {**K, "stick_d": sd, "paper_thickness": pt, "base_height": bh, "base_width": bw}
                cw, ch = t.rod_cut(c)
                old = bh - t.rod_cut_top(c) < t.HOLE_MARGIN or bw / 2 + t.rod_off(c) + cw / 2 > bw - t.HOLE_MARGIN
                assert not old or any(f.where == "留め具" for f in t.check_physics(c)), c
# ---- 8 回目（2026-11-05・動きと組み上がりの読み直し）を押さえる行 ----
# 29. でんでん太鼓の糸は、帯を丸める前に帯の裏で結んで留める（面を貼った後は胴の中に手が入らず、1 つの小さい穴に外から糸を留められない）。
#     玉は後で付け、付ける所で糸の長さを決める
for p in (P, {**P, "face": "tori"}):
    sp = t.steps(p)
    knot = next(i for i, s in enumerate(sp) if "裏で 2 回結んで" in s)
    roll = next(i for i, s in enumerate(sp) if "3 胴の帯を" in s and "丸め" in s and "のりしろ" in s)
    faces = next(i for i, s in enumerate(sp) if "表の面" in s and "はります" in s)
    bead = next(i for i, s in enumerate(sp) if "玉を付けます" in s)
    assert knot < roll < faces < bead and sp[knot].startswith("丸める前に"), (knot, roll, faces, bead)
    assert nums(sp[bead], r"玉の中心まで (\d+(?:\.\d+)?)mm") == [p["cord_length"]]
    assert not any("穴に結" in s for s in sp)
#     切る糸は、結ぶ分と直す分の余りを足した長さ（部品表と用意する物が同じ数）
assert f"{P['cord_length'] + t.CORD_SPARE:g}mm に切る" in next(r for r in t.bom(P) if r["key"] == "cord")["material"] and t.CORD_SPARE >= 30
# 30. 刷る直しの幅（tune_range）は両端とも検査を通り、窓の外へ丸まらない。既定の糸はその内にあり、組み方の最後にその数を刷る
for p, key in ((P, "cord_length"), ({**P, "face": "tori"}, "cord_length"), (K, "k_cord")):
    lo, hi = t.tune_range(p)
    assert lo < hi and t.check_physics({**p, key: lo}) == [] and t.check_physics({**p, key: hi}) == [], (lo, hi)
    assert lo <= p[key] <= hi and f"{lo:g}〜{hi:g}mm の間" in t.steps(p)[-1]
    assert t.check_physics({**p, key: lo - 0.5}) != [] and t.check_physics({**p, key: hi + 0.5}) != [], "幅を窓より広く刷っている"
#     窓が無い寸法（検査で落ちる）でも組み方の文は作れ、数は刷らない
for p in ({**K, "peg_height": 20}, {**P, "radius": 15, "depth": 30, "bead_d": 14}):
    assert t.tune_range(p) is None and t.check_physics(p) != [] and "mm の間" not in t.steps(p)[-1]
# 31. 諫鼓の軸の回る数は、旗の穴が軸から遠ざかった分で数える（棒の動いた長さではない。真横から引き始めるので、始めは糸がほとんど引かれない）。
#     雛形の式とは別の道すじで数える: 糸が軸（原点・半径 r）に接して点 p へ張る形を、接点の座標から出す。y は北を正（棒は東、引く向きは南）


def tangent_unwind(r, p0, p1, north):
    """north=True は接点が軸の北の側（糸は軸の上を時計回りに来て、接点で離れて東の棒へ向かう）。Returns 軸から解ける糸の長さ。"""
    def touch(p):
        d, th = math.hypot(*p), math.atan2(p[1], p[0])
        ang = th + math.acos(r / d) if north else th - math.acos(r / d)
        q = (r * math.cos(ang), r * math.sin(ang))
        assert abs(q[0] * (p[0] - q[0]) + q[1] * (p[1] - q[1])) < 1e-9, "接点で、半径と糸が直角でない"
        assert (q[1] > 0) == north or abs(q[1]) < r * 0.3
        return ang, math.hypot(p[0] - q[0], p[1] - q[1])
    (a0, f0), (a1, f1) = touch(p0), touch(p1)
    cw = a0 - a1  # 接点が時計回りに動いた角度。北を回る糸は、接点が時計回りに動くと軸に巻き付く分が増え、その分も軸から解ける
    return (f1 - f0) + r * (cw if north else -cw)


r, off, T = K["stick_d"] / 2, t.rod_off(K), t.pull_travel(K)
re_ = r + t.WIND_D / 2
#     多い側の見込み: 北を回る・旗は立ったまま・糸の太さ無し。少ない側の見込み: 南を回る・引き切る頃に旗が軸の側へ倒れる・糸の太さの半分
many = tangent_unwind(r, (off, 0), (off, -T), north=True)
few = tangent_unwind(re_, (off, 0), (off - t.TAB_FLAG / 2, -T), north=False)
assert abs(t.pull_unwind(K, favorable=True) - many) < 1e-9 and abs(t.pull_unwind(K) - few) < 1e-9, (many, few)
assert abs(t.pull_turns(K, favorable=True) - many / (2 * math.pi * r)) < 1e-9 and abs(t.pull_turns(K) - few / (2 * math.pi * re_)) < 1e-9
#     同じ形なら、北を回る巻き方の方が多く解ける（差は 軸に沿う分の 2 倍）。どちらも棒の動いた長さより短い
assert tangent_unwind(r, (off, 0), (off, -T), north=False) < many < T and few < T
lo_t, hi_t = t.pull_turns(K), t.pull_turns(K, favorable=True)
#     既定の台は、少ない側の見込みでも 1.3 回を越える。前の既定（台 80mm）は前の式で 1.75 回と刷っていたが、少ない側では 1 回に届かず落ちる
assert 1.3 <= lo_t < hi_t and t.pull_turns({**K, "base_length": 80}) < 1 < T / (2 * math.pi * r)
assert any(f.where == "棒" and "1 回も回らない" in f.message for f in t.check_physics({**K, "base_length": 80}))
assert t.pull_unwind({**K, "base_length": 60}) == 0.0  # 引けない寸法（軸が南の壁に近すぎる）は 0
# 32. 巻く糸は軸に結んで糊で留める（巻くだけでは滑って回らない）。結ぶ高さは旗の穴と同じ（軸の下の端は軸受けを通すので空ける）。
#     巻いておく回数は、多い側で解ける回数より 1 回以上多い。結ぶ所の長さ・部品表の糸・組み方の数が同じ式から出る
sk = t.steps(K)
flag = next(i for i, s in enumerate(sk) if "穴に通して結びます" in s)
knot = next(i for i, s in enumerate(sk) if "軸（竹ぐし 13）に結びます" in s)
wind = next(i for i, s in enumerate(sk) if "巻き取ります" in s)
assert flag < knot < wind and "のりを付けてとめ" in sk[knot]
assert nums(sk[knot], r"机から約 (\d+)mm") == [round(t.flag_hole_z(K))] and t.flag_hole_z(K) == t.HOLE_MARGIN + 2 * K["stick_d"] + K["paper_thickness"] + t.TAB_FLAG / 2
#     巻く向きは、台の中の糸を見ずに確かめられる言い方（上から見た花車の回る向き）で書く。押し込む所は棒の印で決める
assert "時計と反対回り" in sk[wind] and "鼓を奥・棒を右" in sk[wind] and "印まで押しこ" in sk[wind]
mark = next(i for i, s in enumerate(sk) if "えんぴつで印" in s)
assert mark < wind and "北の壁から" in sk[mark] and any("えんぴつ" in m for m in t.materials(K))
assert t.wind_wraps(K) == math.ceil(many / (2 * math.pi * r)) + 1
assert nums(sk[knot], r"旗の穴から (\d+(?:\.\d+)?)mm") == [t.pull_cord(K)] and nums(sk[wind], r"約 (\d+) 回") == [t.wind_wraps(K)]
#     結ぶ所までの糸は、押し込んだ時に張る分 ＋ 巻いておく回数分（糸の太さを入れた 1 周）。多い側で解けても 1 周以上残る
assert abs(t.pull_cord(K) - (math.sqrt(off * off - re_ * re_) + t.wind_wraps(K) * 2 * math.pi * re_)) <= 0.5
assert t.pull_cord(K) - math.sqrt(off * off - re_ * re_) - many >= 2 * math.pi * r
pull_mm = nums(next(q for q in t.bom(K) if q["key"] == "pull")["material"], r"（(\d+(?:\.\d+)?)mm）")[0]
assert t.pull_cord(K) + 2 * t.CORD_SPARE <= pull_mm < t.pull_cord(K) + 2 * t.CORD_SPARE + 10
assert "巻き直します" in sk[-2] and "印まで押しこみ" in sk[-2]
# 33. 折り線の種類は凡例どおり（谷折りは刷った面から見て折り目がへこむ・山折りは出る）。
#     絵を外にして向こうへ折る所（胴の歯・柱の筒・台の壁と角の糊代・軸受けの糊代）と、刷った面を棒に当てて巻く留め具の旗は山折り。
#     刷った面の側へ起こす所（柱の足）だけが谷折り。前は全部が谷折りの線だった
for p in (P, K):
    b = {q.key: q for q in t.parts(p)}["band"]
    tab_, D_ = p["tab"], t.drum_rd(p)[1]
    assert sorted(l[0][1] for l in b.mountain) == [tab_, tab_ + D_] and b.valley == []
kp = {q.key: q for q in t.parts(K)}
H, W, L = K["base_height"], K["base_width"], K["base_length"]
assert len(kp["base"].mountain) == 8 and kp["base"].valley == []
assert {((H, H), (H + W, H)), ((H, H + L), (H + W, H + L)), ((H, H), (H, H + L)), ((H + W, H), (H + W, H + L))} <= set(kp["base"].mountain)
PL = K["post_height"] + t.POST_INSERT
assert [l[0][0] for l in kp["post"].mountain] == [K["post_side"] * i for i in range(1, 5)] and kp["post"].valley == [((0, PL), (4 * K["post_side"], PL))]
assert [l[0][0] for l in kp["rodtab"].mountain] == [t.TAB_FLAG, kp["rodtab"].width - t.TAB_FLAG] and kp["rodtab"].valley == []
assert kp["bearing"].mountain == [((t.BEARING_LIFT, 0), (t.BEARING_LIFT, kp["bearing"].height))] and kp["bearing"].valley == []
assert any("内へ山折り" in s for s in t.steps(P)) and not any("谷折り" in s for s in t.steps(P))
assert any("11 台を山折り" in s for s in sk) and any("山折りして棒の真上に立て" in s for s in sk)
#     糊の印（斜線）は、刷った面に糊を付ける所にだけ刷る。柱の足は裏を台に貼るので印を刷らず、組み方に「裏に糊」と書く
assert len(kp["post"].glue) == 1 and any("足の裏（印刷していない側）にのり" in s for s in sk)
# 34. 軸受け: 穴は台の上の面の穴の真下（西の壁の内の面から台の幅の半分）で同じ太さ。腕の先は、範囲のどの端でも棒の穴の手前で止まる。
#     糊代は一番低い壁より低い。軸に糸を結んだ後、巻き取る前に付ける（先に付けると、台の下から軸に手が届かない）
be = kp["bearing"]
(hx, hy, hr), = be.holes
arm, to_hole = t.bearing_arm(K)
assert abs((hx - t.BEARING_LIFT) - (K["base_width"] / 2 - K["paper_thickness"])) < 1e-9 and hr == kp["base"].holes[0][2]
assert abs(hy - be.height / 2) < 1e-9 and min(hy, be.height - hy) - hr >= t.HOLE_MARGIN - 1e-9 and abs(be.width - (t.BEARING_LIFT + arm)) < 1e-9
for sd in t.RANGES["stick_d"]:
    for pt in t.RANGES["paper_thickness"]:
        c = {**K, "stick_d": sd, "paper_thickness": pt}
        a, th = t.bearing_arm(c)
        assert a - th < t.rod_off(c) - t.rod_cut(c)[0] / 2, c  # 腕の先（軸から）＜ 棒の穴の西の縁（軸から）
        #   高さ: 軸の側へ倒れた旗（棒の上の面の高さ）は腕の上の面から 2mm 以上、巻いた糸（旗の穴の高さ）は 3mm 以上、上にある
        assert t.HOLE_MARGIN + 2 * sd - (t.BEARING_LIFT + pt) >= 2 and t.flag_hole_z(c) - (t.BEARING_LIFT + pt) >= 3, c
assert t.BEARING_LIFT < t.RANGES["base_height"][0] and t.flag_hole_z(K) < t.ceiling_z(K)
#     穴をあける手順に、軸受けの穴も入っている
assert any("18 軸受けの穴" in s and "大人" in s for s in sk)
#     花車の高さの紙は、貼れたら外す（立てたままだと玉の通り道に残る）
assert any("17 は外します" in s for s in sk)
fit = next(i for i, s in enumerate(sk) if "18 軸受けののりしろ" in s)
assert knot < fit < wind and "西の壁" in sk[fit] and "山折り" in sk[fit]
assert check_bom(t.bom(K), t.parts(K)) == []
# 35. 方角（北・南・東・西）は紙に刷っていないので、最初に使う文で、台の上の印と穴から決めて言う
first = next(i for i, s in enumerate(sk) if re.search("[北南東西]", s))
assert all(w in sk[first] for w in ("北", "南", "東", "呼びます")), sk[first]
# 37. 凍結した負の場面（F5.drum）は、どれも理由が 1 つだけで落ちる（2 つ落ちる場面は、狙った検査を消しても緑のままになる）
import json
import pathlib
for f in sorted(pathlib.Path(__file__).parent.glob("frozen/scenarios/twist_drum_neg*.json")):
    sc = json.loads(f.read_text(encoding="utf-8"))
    if sc["expect"]["floors"] == ["F5.drum"]:
        fs = t.check_physics({**t.DEFAULTS, **sc["params"]})
        assert len(fs) == 1, (f.name, [x.line() for x in fs])
# ---- 9 回目（2026-11-05・動きの読み直しの続き）を押さえる行 ----
# 38. でんでん太鼓の糸は胴の中を通れない。結び目（帯の幅の真ん中）から帯の縁まで奥行きの半分を使い、縁で曲がって面の上へ出る。
#     式とは別に数える: 面に触れた玉の中心（面の中心から x、面から玉の半径だけ外）まで、縁を回る道のりが糸の長さになる x を、2 分法で探す
R_, D_, b_ = P["radius"], P["depth"], P["bead_d"] / 2


def strike_by_search(L):
    lo, hi = -R_, R_  # x が大きい（縁に近い）ほど道のりは短い
    for _ in range(80):
        mid = (lo + hi) / 2
        if D_ / 2 + math.hypot(R_ - mid, b_) > L:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


for L in (23, 27, 31):
    q = {**P, "cord_length": L}
    assert abs(t.strike_offset(q) - strike_by_search(L)) < 1e-6, L
    #   前の式（結び目を中心に糸の全長で回る）は、打つ点を面の中心の側へ寄せて出していた
    assert P["radius"] - math.sqrt(L * L - (P["depth"] / 2 + P["bead_d"] / 2) ** 2) < t.strike_offset(q)
#     手で数えた値: 既定（半径 26・奥行き 18・玉 8・糸 27）で、打つ点は 26 − √(18² − 4²) ≒ 8.45mm、下限は 9 + √(13² + 4²) ≒ 22.60mm
assert abs(t.strike_offset(P) - 8.4501) < 1e-3 and abs(t.cord_window(P)[0] - 22.6015) < 1e-3
#     前の式が通していた短い糸（18.4〜22.6mm）は、縁の近く（半径の半分より外）を打つので落ちる。既定の糸は窓の真ん中の近く
for L in (19, 22):
    fs = t.check_physics({**P, "cord_length": L})
    assert [f.where for f in fs] == ["糸"] and t.strike_offset({**P, "cord_length": L}) > t.STRIKE_ZONE * P["radius"], L
low, high = t.cord_window(P)
assert abs(P["cord_length"] - (low + high) / 2) < 1
#     奥行きが深いほど、同じ糸でも面の上へ出る分が減り、打つ点が縁へ寄る。縁から先の糸が玉の半径に届かないと、玉は面の上へ出ない
assert t.strike_offset({**P, "depth": 24}) > t.strike_offset(P) and t.strike_offset({**P, "cord_length": P["depth"] / 2 + P["bead_d"] / 2}) is None
#     柄の側の上限（まっすぐの距離。厳しい側の下限）は変えていない。反対の縁の側の上限（far_limit）は、範囲のどの端でもそれより長い（今は先に効かない）
assert abs(high - (math.sqrt(2) * P["radius"] - P["stick_d"] / 2 - P["bead_d"] / 2)) < 1e-9
for R2 in t.RANGES["radius"]:
    for D2 in t.RANGES["depth"]:
        for b2 in t.RANGES["bead_d"]:
            for sd in t.RANGES["stick_d"]:
                c = {**P, "radius": R2, "depth": D2, "bead_d": b2, "stick_d": sd}
                assert t.far_limit(c) > t.tangle_limit(c), c
# 39. 手で数えた余白と上限（式が黙って変わったら落ちる）
#     回る数は式から刷る
st = " ".join(t.steps(K))
assert nums(st, r"軸が約 (\d+\.\d)〜") == [round(t.pull_turns(K), 1)] and nums(st, r"〜(\d+\.\d) 回まわり") == [round(t.pull_turns(K, favorable=True), 1)]
#     旗の余白は、既定で、天井まで 18.85 − 17.15 ＝ 1.7mm、東の壁まで 18 − 10.15 − 7.15 ＝ 0.7mm
assert round(t.ceiling_z(K) - t.flag_tip_z(K), 2) == 1.7 and round(K["base_width"] / 2 - t.rod_off(K) - (t.TAB_FLAG + K["paper_thickness"]), 2) == 0.7
#     棒を引き切っても、北の壁の穴に 3.5mm 残る
assert round(t.rod_north_out(K) - t.pull_travel(K), 2) == 3.5
#     打つ点が中心を越える糸も検査を通る（打つ向きが結び目の反対の側になる）
far = {**P, "radius": 28, "depth": 10, "bead_d": 4, "cord_length": 34}
assert t.check_physics(far) == [] and t.strike_offset(far) < 0
#     柄に絡まない上限の手前は通り、四捨五入の 31.3mm は落ちる
assert t.check_physics({**P, "cord_length": 31.2}) == [] and t.check_physics({**P, "cord_length": 31.3}) != []
# 40. 組み方の文は、前のサイトの手順の紙の左の列（144mm・字 3.6mm・「番号. 文」）で数えて、でんでん太鼓は STEP_LINES_MAX 行まで（紙に収まった行数。手順の紙は廃止したが、上限は残す）。
#     糸を留める手順と直しの幅を足した版は 22〜23 行で、紙の下へはみ出していた。諫鼓は前から収まらないので、今の行数を上限にして増やさない
from omochae.textfit import wrap


def step_lines(p):
    return sum(len(wrap(f"{i}. {s_}", t.STEP_SIZE, t.STEP_COL_W)) for i, s_ in enumerate(t.steps(p), 1))


for p in (P, {**P, "face": "tori"}, {**P, "cord_length": 23.5, "handle_length": 95.5}, {**P, "face": "tori", "cord_length": 23.5, "handle_length": 95.5}):
    assert step_lines(p) <= t.STEP_LINES_MAX, (step_lines(p), p)
assert step_lines(K) <= t.STEP_LINES_KANKO and t.STEP_LINES_MAX == 16
# 41. 引く手順は、どこまで引くか（旗が南の壁に当たるまで）を言う。鳥の面は幣の房の手順の分だけ多い
pull_i = next(i for i, s_ in enumerate(t.steps(K), 1) if "すばやく引きます" in s_)
assert "旗が南の壁に当たるまで" in t.steps(K)[pull_i - 1] and nums(t.steps(K)[pull_i - 1], r"当たるまで（(\d+(?:\.\d+)?)mm）") == [t.pull_travel(K)]
assert len(t.steps({**P, "face": "tori"})) == len(t.steps(P)) + 1
#     サイトの見取り図の言葉を持つ（持たないと、御来迎の筒の言葉が鼓の図に出る。前は手順の紙に刷った）
assert "糸" in t.DIAGRAM_CAPTION and "筒" not in t.DIAGRAM_CAPTION
# 42. 利用者に見せる文はやさしい言葉（2026-11-06 の制作者の決定で書き直した。書き方の決めは雛形の CUT_POINTS の上の注）。
#     組み方は 1 文ずつ「です・ます」で終わる（文の終わりの（…）の添え書きは除いて見る）。
#     小学校で習わない字と、紙の凡例に無い線の名は、組み方・用意する物・見取り図の言葉に戻さない
HARD = ("糊", "貼", "竹串", "菱", "一点鎖線", "破線", "実線", "敷", "挟", "絡", "垂", "滑", "込", "束", "縁", "端", "刷っ", "木綿", "粘土", "花弁")
for p in (P, {**P, "face": "tori"}, K):
    for s_ in t.steps(p):
        for sen in filter(None, s_.split("。")):
            assert re.sub(r"（[^（）]*）$", "", sen).endswith(("ます", "です", "ません")), (p["face"], sen)
    shown = " ".join(t.steps(p) + t.materials(p) + [t.DIAGRAM_CAPTION])
    assert not [w for w in HARD if w in shown], (p["face"], [w for w in HARD if w in shown])
print("ok")
