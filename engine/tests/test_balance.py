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

# EP-0002（作る前のレビューの指摘から採った案。2026-11-06）: 弥次郎兵衛の紙で、体の左右の袖の長さがずれていた（図をそのまま写した）。
# 重りに耐える強さのため、真ん中の軸にも竹串を貼る線が欲しいという声もあった。
# - 体の外形の左右の端（袖の先）は、支点（V の先）の真上の線から同じ距離
# - 体（裏）の刷った面に、真ん中の軸の竹串を置く縦の赤い線を刷る。線は支点の真上の線に乗り、竹串の太さを含めて体の内にあり、
#   腕の竹串（差し込みの奥の端から肩まで）と重ならない（重なると、表と裏の紙が平らに合わない）
# - 重心の式に、真ん中の竹串の重さを入れる（長さ × 1mm あたりの重さを、線の真ん中に置く）
# - 用意する物と組み方の文が、真ん中の軸の竹串の長さと置き方を言う
from shapely.geometry import LineString
seen = 0
for bw in (t.RANGES["body_w"][0], Y["body_w"], t.RANGES["body_w"][1]):
    for bh in (t.RANGES["body_h"][0], Y["body_h"], t.RANGES["body_h"][1]):
        q = {**Y, "body_w": bw, "body_h": bh}
        if t.check_range(q) or t.check_physics(q):
            continue  # 検査で落ちる寸法は刷らない
        seen += 1
        body = Polygon([t._rel(q, v) for v in t._YAKKO])
        xs = [x for x, _ in body.exterior.coords]
        assert abs(min(xs) + max(xs)) < 0.01, (q, "袖の左右の長さが違う", min(xs), max(xs))
        lo, hi = t.center_stick(q)
        assert abs(lo[0]) < 1e-9 and abs(hi[0]) < 1e-9, (lo, hi)
        stick = LineString([lo, hi])
        assert body.buffer(-t.SKEWER_R).contains(stick), (q, "真ん中の竹串が体の外に出る")
        for inner, sh, _ in t.arm_geometry(q):
            assert stick.distance(LineString([inner, sh])) > 2 * t.SKEWER_R, (q, "真ん中の竹串が腕の竹串に重なる")
        back = next(x for x in t.parts(q) if x.key == "back")
        tx, ty = t._yk(q, [t._TIP])[0]
        mid = [a for a in back.art if a.get("role") == "center"]
        assert len(mid) == 1 and mid[0]["pts"][0] == (lo[0] + tx, lo[1] + ty) and mid[0]["pts"][-1] == (hi[0] + tx, hi[1] + ty), mid
        Lc = abs(hi[1] - lo[1])
        assert any(abs(m - t.SKEWER_G_PER_MM * Lc) < 1e-12 and x == 0 and abs(z - (lo[1] + hi[1]) / 2) < 1e-9 for m, x, z in t.yajirobe_points(q)), "重心の式に真ん中の竹串が無い"
assert seen >= 3, seen
lo, hi = t.center_stick(Y)
Lc = abs(hi[1] - lo[1])
st = t.steps(Y)
assert any(f"{Lc:.0f}mm" in x and "真ん中の軸" in x for x in st), st
assert any("縦の赤い線" in x for x in st), st
assert any("真ん中の軸" in m and f"{Lc:.0f}mm" in m for m in t.materials(Y)), t.materials(Y)
_, layout, fails = compose("balance", Y, load_source(t.SOURCE))
assert not fails, [f.line() for f in fails]
print("ok 弥次郎兵衛の袖と真ん中の軸")

# EP-0001（作る前のレビューの指摘から採った案。2026-11-06）: 起き上がり小法師の紙で、粘土を詰める高さの線（濃い実線）を切る線と
# 取り違えて切った人がいた（「直線なんて切ると判断して切った」）。2 番が底の部品だと分からず、帯の下の側をどうするか分からなかった。
# - 粘土を詰める高さの線は、位置の印（赤茶の点の線。凡例に「切らない・折らない」）で刷る。切る線と同じ濃い実線では刷らない
# - 札は「1 胴」「2 底」（どちらが底かを紙で分かるように。上下の字は、切れの細い寸法で札が切れに収まらないので入れない）
# - 赤道の折り線は山折り。お椀は刷った面を外にし、帯を内へ折って円錐の底の内に差し込む（谷折りの破線では、帯が外へ開く向きだった）
# - 組み方の文: 帯は刷った面を外にして輪にする・粘土は点の線まで詰める・帯は赤道の山折りの線で内へ折る
from omochae.__main__ import load_source
from omochae.compose import LABEL_SIZE, LINE, compose
from omochae.floors import check_art
from omochae.textfit import text_width
from shapely.geometry import Polygon, box
seen = 0
for R in (t.RANGES["base_r"][0], O["base_r"], t.RANGES["base_r"][1]):
    for n in (t.RANGES["gores"][0], O["gores"], t.RANGES["gores"][1]):
        q = {**O, "base_r": R, "gores": n}
        if t.check_range(q) or t.check_physics(q):
            continue  # 検査で落ちる寸法は刷らない
        seen += 1
        shell, dome = (next(x for x in t.parts(q) if x.key == k) for k in ("shell", "dome"))
        marks = [a for a in dome.art if a.get("role") == "clay"]
        assert marks and all(a["kind"] == "mark" and a.get("mark") == "clay" for a in marks), (q, [a["kind"] for a in marks])
        assert not any(a["kind"] == "line" and a.get("stroke") == t.INK and len(a["pts"]) == 2 and a["pts"][0][1] == a["pts"][1][1] for a in dome.art), "濃い実線の横線が残る"
        assert dome.mountain == [((0, q["band"]), (2 * math.pi * R, q["band"]))] and not dome.valley, (dome.mountain, dome.valley)
        assert check_art([dome]) == [], (q, [f.line() for f in check_art([dome])])
        for part, want in ((shell, "1 胴"), (dome, "2 底")):
            assert part.label == want, part.label
            lx, ly = part.label_xy
            tag = box(lx, ly, lx + text_width(part.label, LABEL_SIZE), ly + LABEL_SIZE * LINE)
            assert Polygon(part.outline).contains(tag), (q, part.key, "札が部品の外に出る")
assert seen >= 3, seen
_, layout, fails = compose("balance", O, load_source(t.SOURCES["okiagari"]))
assert not fails, [f.line() for f in fails]
assert any("位置の印" in x.text for x in layout["texts"]), "凡例に位置の印の行が無い"
st = t.steps(O)
assert any("刷った面を外にして" in x and "輪" in x for x in st), st
assert any("点の線" in x and "粘土" in x for x in st), st
assert any("赤道の山折りの線" in x and "内へ折り" in x for x in st) and not any("赤道の破線" in x for x in st), st
# EP-0001 に足した声（曲線の胴に直線の 2 番を貼るのが難しい）: 帯の上の縁に、切れの半分ごとのくし形の切り込みを入れ、
# 切り込みは赤道の折り線の手前で止める。帯の糊代は切り込みを除いた形（斜線が切り込みを隠さない）。組み方の文が切り込みを言う
# 継ぎ目の糊代にも、帯の頭の g mm にある切り込みと同じ所に切り込みを入れる（重ねた時に切り込みを塞がない。検品の指摘の組
# 半径 15・切れ 12・糊代 10 も見る）
# 切れの数は範囲の全部、糊代の長さは 1mm 刻みで見る（2 回目の検品の指摘の組 半径 15・切れ 7・糊代 7 を含む）
checked_seam = 0
for R in (t.RANGES["base_r"][0], O["base_r"], t.RANGES["base_r"][1]):
    for n in range(t.RANGES["gores"][0], t.RANGES["gores"][1] + 1):
        for b in (t.RANGES["band"][0], O["band"], t.RANGES["band"][1]):
          for g in range(t.RANGES["seam_glue"][0], t.RANGES["seam_glue"][1] + 1):
            q = {**O, "base_r": R, "gores": n, "band": b, "seam_glue": g}
            if t.check_range(q) or t.check_physics(q):
                continue
            dome = next(x for x in t.parts(q) if x.key == "dome")
            w = 2 * math.pi * R / n
            under = [j * w / 2 for j in range(1, 2 * n) if j * w / 2 - t.SLIT_W / 2 < g]  # 糊代が少しでも重なる帯の頭の切り込み
            C = 2 * math.pi * R
            tips = [pt for pt in dome.outline if abs(pt[1] - (b - t.SLIT_KEEP)) < 1e-9 and pt[0] < C - 1e-9]
            assert len(tips) == 2 * n - 1, (q, len(tips))  # 帯の切り込み（糊代の側は下で面積で見る）
            # 輪にすると、糊代（C〜C+g）は帯の頭（0〜g）に重なる。帯の切り込みの V を糊代の側へ写し、糊代の紙が V を塞がない
            # （重なる面積がほぼ 0）事を見る。頂点の数だけを見ると、V の半分を塞ぐ形でも通った（3 回目の検品の指摘）
            tab = Polygon(dome.outline).intersection(box(C, 0, C + g, b))
            for xs in under:
                v = Polygon([(C + xs - t.SLIT_W / 2, 0), (C + xs, b - t.SLIT_KEEP), (C + xs + t.SLIT_W / 2, 0)])
                assert tab.intersection(v).area < 1e-6, (q, xs, tab.intersection(v).area)
            checked_seam += bool(under)
            assert Polygon(dome.outline).is_valid and all(Polygon(dome.outline).buffer(1e-6).contains(Polygon(gl)) for gl in dome.glue), q
            assert check_art([dome]) == [], (q, [f.line() for f in check_art([dome])])
assert checked_seam >= 1, checked_seam
assert any("切り込み" in x and "重ねて" in x for x in t.steps(O)), t.steps(O)
print("ok 起き上がり小法師の印と向き")
