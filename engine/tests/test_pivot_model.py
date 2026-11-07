"""振り子の式の向きを数点で確かめる。言葉で書いた直す向きは間違えやすいので、ここで数える。"""
from omochae.pivot_model import center, period_s, rest_tilt_deg
from omochae.templates.pivot_counterweight import DEFAULTS, check_physics, mass_points

base = [(0.1, 20, 0), (3.0, 0, 20)]
far = [(0.1, 20, 0), (3.0, 0, 40)]
assert period_s(far) > period_s(base), "重りが軸から遠いほど周期が長い"
heavy = [(0.1, 20, 0), (6.0, 0, 20)]
assert abs(period_s(heavy) - period_s(base)) < 0.01, "重りの量は周期をほぼ変えない"
assert period_s([(3.0, 0, -5)]) is None, "軸より上では揺れない"
assert rest_tilt_deg([(0.1, 20, 0), (3.0, 0, 20)]) < 2
# 紙の頭は重りより桁で軽いので、後ろの腕の重りで釣り合わせると大きく傾く
seesaw = dict(DEFAULTS, weight_behind=28, weight_below_axle=5, weight_g=1.0)
assert any("傾く" in f.message for f in check_physics(seesaw))
assert mass_points(DEFAULTS)[0][0] < 0.2 and not check_physics(DEFAULTS)
print(round(period_s(mass_points(DEFAULTS)), 2))

# EP-0011（作成動画の札から採った案。2026-11-06）: 首の形の 5 重りの腕に下の穴（重りの位置）を足し、腕は試してから貼る順にした。
# - 下の穴は、軸の穴から weight_below_axle 下（釣り合いの式の重りの位置）。粘土を付ける高さを点の線（位置の印）で示す（EP-0016 で丸から替えた）
# - 糸で玉を下げる形は、玉（粘土 weight_g の球）の下が胴の底から 3mm 以上離れる寸法の時だけ、組み方の文と部品表に出す。
#   釣り合いの式は変えない: 糸で下げた玉の重さは、糸を通した穴にかかる（玉の所ではない）。糸の長さは、玉が底に当たるかだけに効く
# - 組み方の文: 腕は帯に仮に留め、頭の傾きを見て位置を決めてから貼る（手順の数と番号は変えない）
import math

from omochae.__main__ import load_source
from omochae.compose import compose
from omochae.floors import check_art
from omochae.templates import pivot_counterweight as pc
neck = dict(DEFAULTS, mount="neck")
# 下の穴の境（LOWER_HOLE_MIN）の前後も見る。重りが後ろへずれない（weight_behind 0）と、浅い重りでも検査を通る（見直しの指摘: 前の組は -20 の次が 5 だった）
seen = hangable = 0
for wba in (pc.RANGES["weight_below_axle"][0], 0.5, 1, 2, 3, 3.6, 4, 5, 12, 20, DEFAULTS["weight_below_axle"], 40, pc.RANGES["weight_below_axle"][1]):
    for wg in (pc.RANGES["weight_g"][0], 1.0, DEFAULTS["weight_g"], pc.RANGES["weight_g"][1]):
        for ax, wb in ((30, 1), (DEFAULTS["axle_height"], DEFAULTS["weight_behind"]), (50, 1), (DEFAULTS["axle_height"], 0)):
            q = dict(neck, weight_below_axle=wba, weight_g=wg, axle_height=ax, weight_behind=wb)
            if pc.check_range(q) or check_physics(q):
                continue  # 検査で落ちる寸法は刷らない
            seen += 1
            drop = next(x for x in pc.parts(q) if x.key == "drop")
            st, mat = pc.steps(q), pc.materials(q)
            # 検査に通る寸法では、粘土の玉は軸の竹串から離れ（玉の真ん中は軸の下 半径 + AXLE_CLEAR 以上）、下の穴はいつもある
            assert wba >= pc.clay_r(wg) + pc.AXLE_CLEAR and wba >= pc.LOWER_HOLE_MIN, q
            assert wba + pc.clay_r(wg) <= ax - 3 + 1e-9, q  # 玉の下が底から 3mm 以上
            (ax_x, ax_y, _), (hx, hy, hr) = drop.holes[0], drop.holes[1]
            assert hx == ax_x and abs((hy - ax_y) - wba) < 1e-9, (q, drop.holes)  # 軸の穴の真下、weight_below_axle の所
            # 粘土の高さの点の線は、穴の左右の 2 本で、穴の高さにあり、穴にかからない（check_art）
            marks = [a for a in drop.art if a["kind"] == "mark" and a.get("mark") == "weight"]
            assert len(marks) == 2 and all(y == hy for a in marks for _, y in a["pts"]), (q, marks)
            assert check_art([drop]) == [], (q, [f.line() for f in check_art([drop])])
            assert mass_points(q)[-1] == (wg, -q["weight_behind"], wba), "釣り合いの式の重りの位置は変えない"
            L = pc.hang_thread_mm(q)
            if L is None:
                assert not any("糸" in s for s in st) and not any("糸" in m for m in mat), (q, st, mat)
            else:
                hangable += 1
                r = pc.clay_r(wg)
                assert wba + L + 2 * r <= q["axle_height"] - 3 + 1e-9, (q, L, r)  # 下げた玉の下が底から 3mm 以上
                # L は穴から玉の上までの長さ（糸そのものの長さではない）と、文に書く
                # 長さの幅（下限 HANG_MIN と上限）を書く。上限だけだと、結ぶ間の無い短さでも文に合ってしまう
                assert L >= pc.HANG_MIN and any("糸" in s and f"玉の上は穴から {pc.HANG_MIN}〜{L}mm" in s for s in st), (q, st)
                assert any(f"玉の上は穴から {pc.HANG_MIN}〜{L}mm" in m for m in mat), (q, mat)
            assert any("下の穴（点の線）の所に粘土" in s and "仮に留め" in s for s in st), st
            assert any("頭の傾きを見て" in s and "貼る" in s for s in st), st
assert seen >= 10 and hangable >= 1, (seen, hangable)
# 重い玉の下が底に当たる寸法（見直しの指摘の例）は、玉の下の端で落とす。玉の真ん中だけ見ると通っていた
low = dict(neck, axle_height=30, weight_below_axle=15, weight_g=15, weight_behind=0)
assert any("粘土の玉の下が底に当たる" in f.message for f in check_physics(low)), [f.line() for f in check_physics(low)]
# 検査に通る首の形の寸法では、粘土の玉の下が底から 3mm 以上離れる（上の組で見た通る組の全部）
# 玉が軸にかかり、底にも当たる寸法（見直しの指摘の例）は、玉の決まりの行を 1 つだけ出す
both = dict(neck, axle_height=15, weight_below_axle=5, weight_g=15, weight_behind=0)
ball_lines = [f for f in check_physics(both) if "粘土の玉" in f.message]
assert len(ball_lines) == 1 and "軸の竹串にかかる" in ball_lines[0].message, [f.line() for f in check_physics(both)]
# 浅い重りに重い玉（見直しの指摘の例）は、玉が軸の竹串にかかるので検査で落とす
shallow = dict(neck, weight_below_axle=1, weight_g=15, weight_behind=0)
assert any("軸の竹串にかかる" in f.message for f in check_physics(shallow)), [f.line() for f in check_physics(shallow)]
# 下の穴の無い寸法（検査では落ちる）でも、組み方の文は無い穴を言わず、粘土の位置を上の穴からの深さで言う
nohole = dict(neck, weight_below_axle=2, weight_g=0.2, weight_behind=0)
assert len(next(x for x in pc.parts(nohole) if x.key == "drop").holes) == 1
assert not any("下の穴" in s for s in pc.steps(nohole)) and any("上の穴の 2mm 下" in s for s in pc.steps(nohole)), pc.steps(nohole)
# 腕を仮に留めるテープは、用意する物に書く（首の形）
assert any("セロハンテープ" in m for m in pc.materials(neck)), pc.materials(neck)
_, layout, fails = compose("pivot_counterweight", neck, load_source(pc.SOURCE))
assert not fails, [f.line() for f in fails]
assert any("位置の印" in x.text for x in layout["texts"]), "凡例に位置の印の行が無い"
print("ok 重りの腕の下の穴と試してから貼る順")


# EP-0016（制作者のレビューから採った案。2026-11-06）
# 1. 胴の 2 枚目の側面の絵は y だけを裏返す。2 枚の側面の虎の頭（図の鼻先＝_BODY の x の一番小さい点）が、どちらも箱の前の端
#    （軸の穴の側）に来る。前は 180° 回していて、2 枚目の頭が後ろの端に来た（前にも言われて直っていなかった所）
# 2. 2〜5 番に部品の名を刷る（札は部品の枠の内。compose の F5.text_overlap が見る）
# 3・4. 首の形では、胴の上の面に軸の竹串が横切る所の点の線、用意する物に竹串と粘土の置き所・丸い印は穴・4 尾だけ色がある理由
# 側面は縞と白い帯と白い脚（実物の写真の直し C・F）になったので、向きは脚で見る。どちらの側面も、脚（白い面に紺の線の物）は
# 床の辺の側（1 枚目は胴の底の面との境 b0、2 枚目は b1）にあり、前の脚と後ろの脚は 2 枚で同じ x（前の端 H と後ろの端 H + L の近く）
for mount in ("neck", "hang"):
    q = dict(DEFAULTS, mount=mount, **({"axle_height": 50} if mount == "hang" else {}))
    body = next(x for x in pc.parts(q) if x.key == "body")
    H, L, W, g = q["body_height"], q["body_length"], q["body_width"], q["glue"]
    top1 = g + W
    b0, b1 = top1 + H, top1 + H + W
    legs = [a for a in body.art if a["kind"] == "poly" and a.get("fill") == pc.WHITE and a.get("stroke") == pc.STRIPE]
    assert len(legs) == 4, (mount, len(legs))
    for y0, y1, foot in ((top1, b0, b0), (b1, b1 + H, b1)):
        side = [a for a in legs if all(y0 <= y <= y1 for _, y in a["pts"])]
        assert len(side) == 2, (mount, foot, len(side))
        # 脚は床の辺から脚の高さ（LEG_TOP）の内。背の辺の側には無い
        assert all(abs(y - foot) <= pc.LEG_TOP * H + 0.5 for a in side for _, y in a["pts"]), (mount, foot)
        xs = sorted(sum(x for x, _ in a["pts"]) / len(a["pts"]) for a in side)
        assert xs[0] - H < L / 4 and (H + L) - xs[1] < L / 4, (mount, xs)
    cx = sorted(round(sum(x for x, _ in a["pts"]) / len(a["pts"]), 6) for a in legs)
    assert cx[0] == cx[1] and cx[2] == cx[3], cx  # 2 枚の側面で脚の x が同じ（x は裏返さない。EP-0016）
    _, layout, fails = compose("pivot_counterweight", q, load_source(pc.SOURCE))
    assert not fails, (mount, [f.line() for f in fails])
labels = {x.key: x.label for x in pc.parts(neck)}
# 5 は「5 重りの腕」（制作者の決定 2026-11-06「部品の名前は案3: 型紙を「5 重りの腕」にそろえる。」。札の並べ方は test_pivot_arm_label.py が見る）
assert labels == {"body": "1 胴", "head": "2 頭", "strip": "3 首の帯", "tail": "4 尾", "drop": "5 重りの腕"}, labels
# 3 首の帯の札: 真ん中の谷折りの線（x = sw）が、字の「3」と「首」の間の空きを通る（字が折り線にかからない）。細い帯は「3 帯」で、
# どの帯の幅でも札が帯の枠に収まる（範囲の下限 5mm で「3 首の帯」が枠からはみ出し、配置の検査で落ちていた。見直しの指摘）
from omochae.compose import LABEL_SIZE
from omochae.textfit import text_width
# 雛形が写した札の字の大きさは、描く所（compose）と同じ（違うと、置き場の計算が刷る字の幅とずれる。見直しの指摘）
assert pc.LABEL_SIZE == LABEL_SIZE, (pc.LABEL_SIZE, LABEL_SIZE)
for sw in range(pc.RANGES["strip_width"][0], pc.RANGES["strip_width"][1] + 1):
    q = dict(neck, strip_width=sw)
    strip = next(x for x in pc.parts(q) if x.key == "strip")
    x0 = strip.label_xy[0]
    assert strip.label in ("3 首の帯", "3 帯"), (sw, strip.label)
    assert x0 + text_width("3", pc.LABEL_SIZE) < sw < x0 + text_width("3 ", pc.LABEL_SIZE), (sw, x0)  # 折り線は空きの中
    assert x0 >= 0 and x0 + text_width(strip.label, pc.LABEL_SIZE) <= 2 * sw, (sw, strip.label, x0)  # 帯の枠の内
    if not pc.check_range(q) and not check_physics(q):
        _, _, fails = compose("pivot_counterweight", q, load_source(pc.SOURCE))
        assert not fails, (sw, [f.line() for f in fails])
assert next(x for x in pc.parts(neck) if x.key == "strip").label == "3 首の帯"  # 既定の帯（10mm）は名を変えない
body = next(x for x in pc.parts(neck) if x.key == "body")
axle = [a for a in body.art if a["kind"] == "mark" and a.get("mark") == "axle"]
assert len(axle) == 1 and all(x == body.holes[0][0] for x, _ in axle[0]["pts"]), axle  # 2 つの軸の穴と同じ x
assert check_art([body]) == [], [f.line() for f in check_art([body])]
mat = pc.materials(neck)
assert any("5 重りの腕の上の穴に通す" in m and "点の線の下を通る" in m for m in mat), mat
assert any("5 重りの腕の下の穴の、点の線の所に付ける" in m for m in mat), mat
assert any("丸い印は穴" in m and "4 尾は外に見えるので色を刷り" in m for m in mat), mat
print("ok 虎の側面の向き・部品の名・竹串と粘土の印")


# 実物の写真の直し（制作者の決定 2026-11-06「実物の写真と照らした直しは、御来迎・虎とも全部入れる。次の版へ」）
# A. 首の穴は丸い切り抜きで、縁は赤。穴の真ん中は軸の高さ（前の壁は x = H が床の辺）。四角い切り込みは無い
import json
import pathlib

v5 = json.loads((pathlib.Path(__file__).resolve().parents[1] / "examples/tora_v5.json").read_text(encoding="utf-8"))
q5 = dict(DEFAULTS, **v5["params"])
for q in (neck, q5):
    body = next(x for x in pc.parts(q) if x.key == "body")
    H, W, g = q["body_height"], q["body_width"], q["glue"]
    # 前の壁の幅の真ん中。胴の角を落とした形（body_round）では、上の面が 2d 細く、側面が d 低く、角の面 c が 2 つ入る
    c = q["body_round"]
    d = c / math.sqrt(2)
    cy = g + (W - 2 * d) + c + (H - d) + W / 2
    assert body.cuts == [] and body.round_cuts == [(H - q["axle_height"], cy, q["opening"] / 2)], body.round_cuts
    rims = [a for a in body.art if a["kind"] == "poly" and a.get("fill") == pc.RIM]
    assert len(rims) == 1 and all(abs(math.hypot(x - (H - q["axle_height"]), y - cy) - (q["opening"] / 2 + pc.RIM_W)) < 1e-6 for x, y in rims[0]["pts"])
hang = dict(DEFAULTS, mount="hang", axle_height=50)
assert not any(x.round_cuts or x.cuts for x in pc.parts(hang))
assert "1 胴の前の壁の丸い穴を切る（カッターは大人がする）" in pc.steps(neck)
# 丸い印が 2 種ある（竹串であける小さい穴と、切り抜く大きな丸）ので、用意する物と組み方の文で言い分ける
assert any("小さい丸い印は穴（竹串の先であける）" in m and "赤い縁の大きな丸は切り抜く" in m for m in pc.materials(neck)), pc.materials(neck)
assert "部品を実線で切る。胴の小さい穴は竹串の先であける" in pc.steps(neck) and "部品を実線で切る。胴の小さい穴は竹串の先であける" in pc.steps(hang)
assert not any("大きな丸" in m for m in pc.materials(hang)), pc.materials(hang)  # 吊る形に切り抜く丸は無い
# E. 尾は根元の糊代を山折りし、上の面の後ろの端の近くの四角（位置の印）に貼って立てる。どちらの形も同じ
for q in (neck, hang):
    ps = {x.key: x for x in pc.parts(q)}
    tail = ps["tail"]
    assert tail.mountain == [((0, pc.TAIL_LEN), (pc.TAIL_W, pc.TAIL_LEN))] and len(tail.glue) == 1 and tail.height == pc.TAIL_LEN + pc.TAIL_TAB
    marks = [a for a in ps["body"].art if a["kind"] == "mark" and a.get("mark") == "tail"]
    assert len(marks) == 1 and marks[0].get("closed"), marks
    H, L, W, g = q["body_height"], q["body_length"], q["body_width"], q["glue"]
    xs, ys = [x for x, _ in marks[0]["pts"]], [y for _, y in marks[0]["pts"]]
    # 四角は尾の糊代と同じ大きさで、上の面（y が g〜g＋W）の後ろの端（x = H＋L）の近く
    assert abs(max(xs) - min(xs) - pc.TAIL_TAB) < 1e-9 and abs(max(ys) - min(ys) - pc.TAIL_W) < 1e-9, marks
    assert H + L - pc.TAIL_BACK - pc.TAIL_TAB - 1e-9 <= min(xs) and max(xs) <= H + L and g <= min(ys) and max(ys) <= g + W, marks
    assert pc.steps(q)[-1] == "4 尾の糊代を山折りし、1 胴の上の面の後ろの点の線の四角に貼る。尾は上へ反らせる", pc.steps(q)[-1]
    assert check_art([ps["body"], tail]) == [], [f.line() for f in check_art([ps["body"], tail])]
# 次の組（tora-v5）の寸法は examples/tora_v5.json に置く（既定の寸法は凍結の場面が使うので変えない）。
# A: 軸（＝首の穴の真ん中）は前の面の高さの半ばより少し上（写真の目測で 5〜6 割）。D: 頭の長さは胴の長さの 0.55〜0.6 倍
assert v5["template"] == "pivot_counterweight" and q5["mount"] == "neck"
assert pc.check_range(q5) == [] and check_physics(q5) == [], [f.line() for f in pc.check_range(q5) + check_physics(q5)]
assert 0.5 <= q5["axle_height"] / q5["body_height"] <= 0.65 and 0.55 <= q5["head_w"] / q5["body_length"] <= 0.6, q5
_, _, fails = compose("pivot_counterweight", q5, load_source(v5["source_id"]))
assert not fails, [f.line() for f in fails]
print("ok 実物の写真の直し")
