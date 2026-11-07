"""弩・弓と毛玉の床（F5.launch）の式の要所を数点で確かめる。ためる力と玉の重さは安全を分ける量なので、言葉でなく数で見る。"""
from omochae.compose import TEMPLATES
from omochae.templates import launcher as t

P = dict(t.DEFAULTS)
B = {**P, "form": "bow"}
assert TEMPLATES["launcher"] is t, "templates/ に置けば登録される"
for p in (P, B):
    assert t.check_physics(p) == [] and not t.check_range(p), t.check_physics(p)

# k は作る物の寸法から: 梁 2 本・k₁ = 3·E_HIGH·I/L³。弩の引きは引き金の座の奥まで（draw + notch_depth = 29mm）で、既定は 64N/m・27mm ほど
k1 = 3 * t.E_HIGH * (P["arm_w"] * (t.LAYERS * P["paper_t"]) ** 3 / 12) / P["arm_len"] ** 3 * 1000
x_eff = (P["draw"] + P["notch_depth"]) / 1000
assert abs(t.spring_k(P) - 2 * k1) < 1e-9 and abs(t.energy_mj(P) - 0.5 * 2 * k1 * x_eff ** 2 * 1000) < 1e-9
# 引きを倍にすると 4 倍、紙の厚さを倍にすると 8 倍（厚さの 3 乗）
assert abs(t.energy_mj({**P, "draw": 2 * P["draw"] + P["notch_depth"]}) / t.energy_mj(P) - 4) < 1e-9 and abs(t.spring_k({**P, "paper_t": 0.4}) / t.spring_k(P) - 8) < 1e-9
# 上限ちょうどの手前は通り、越えれば F5.launch のばねで落ちる（引く長さで探す: x = √(2E/k)）
x_cap = (2 * t.ENERGY_CAP_MJ / 1000 / t.spring_k(P)) ** 0.5 * 1000 - P["notch_depth"]
assert t.check_physics({**P, "draw": x_cap - 1e-6}) == []
fs = t.check_physics({**P, "draw": x_cap + 0.5})
assert [(f.floor, f.where) for f in fs] == [("F5.launch", "ばね")], fs
# 弓の形も同じ式で、持つ所の帯の外の片側を梁にする
assert abs(t.spring_k(B) - 2 * k1 * (P["arm_len"] / ((B["bow_span"] - t.GRIP_W) / 2)) ** 3) < 1e-9
assert any(f.where == "ばね" for f in t.check_physics({**B, "paper_t": 0.35}))
# 止めの条件の下がり: 重りの力 ÷ k₁。下がりが読めないほど硬い腕は落とす
assert abs(t.tip_sag_min(P) - t.COIN_G / 1000 * 9.8 / k1 * 1000) < 1e-9
assert any("確かめられない" in f.message for f in t.check_physics({**P, "arm_len": 30, "draw": 10}))

# 玉の重さ ＝ 紙の面積 × 面密度。60mm 四方・150g/m² は 0.54g
assert abs(t.projectile_mass(P) - 60 * 60 * 150e-6) < 1e-12
assert any(f.where == "玉" and "重さ" in f.message for f in t.check_physics({**P, "ball_paper": 100, "paper_gsm": 120, "ball_d": 18}))
# 毛玉は芯の玉の紙と房の帯を足した重さ。厚い紙では 1g を越える
assert abs(t.projectile_mass(B) - (60 * 60 + t.POM_LEN * t.POM_BASE + t.POM_TEETH * t.TOOTH * B["fringe_len"]) * 150e-6) < 1e-12
assert any(f.where == "玉" and "重さ" in f.message for f in t.check_physics({**B, "paper_gsm": 200}))

# 先の太さ: どちらの形も丸めた玉の直径。毛玉の房の長さは数えない（当たるとつぶれる）。15mm より細いと落ちる
assert t.nose_d(B) == B["ball_d"] and t.nose_d({**B, "fringe_len": 25}) == B["ball_d"]
assert any("先の太さ" in f.message for f in t.check_physics({**B, "ball_d": 14.9}))
assert not any("先の太さ" in f.message for f in t.check_physics({**B, "ball_d": 15}))

# 弩の玉は、筒より 1〜4mm 細く、紙の辺の 0.3 倍まで。物差しの穴は通らない側が 15mm 以上
small, big = t.gauge_holes(P)
assert small >= t.MIN_NOSE and big == P["stock_w"] - 1 and small < P["ball_d"] < big
assert any("物差しの穴" in f.message for f in t.check_physics({**P, "ball_d": 15}))  # 筒（太さ 20mm）に対して細すぎる
assert any("まとまらない" in f.message for f in t.check_physics({**P, "ball_paper": 50}))

# 穴と縁: 腕の幅の半分から穴の半径を引いた残りが 3mm 未満で落ちる
assert any(f.where == "腕" for f in t.check_physics({**P, "arm_w": 7}))
assert any(f.where == "弓" for f in t.check_physics({**B, "arm_w": 7}))
# 引き金の切れ込みの奥の残り・浅すぎる切れ込み・台の後ろの端までの余り
assert any("奥に" in f.message for f in t.check_physics({**P, "trigger_w": 6}))
assert any("座の前の縁" in f.message for f in t.check_physics({**P, "notch_depth": 3}))
assert any("浅く" in f.message for f in t.check_physics({**P, "notch_depth": 1}))
assert any("後ろの端" in f.message for f in t.check_physics({**P, "stock_length": 70, "draw": 50}))
# 弦の溝と糊代の間
assert any(f.where == "弦の溝" for f in t.check_physics({**P, "glue": 8}))

# 刷る部品の穴・切れ込みの位置が式と合う: 腕の穴は 4 枚の面の真ん中、引き金の切れ込みは筒の真ん中の高さ
arm = next(q for q in t.parts(P) if q.key == "arma")
assert [y for _, y, _ in arm.holes] == [k * P["arm_w"] + P["arm_w"] / 2 for k in range(t.LAYERS)]
trig = next(q for q in t.parts(P) if q.key == "trigger")
# 5 回目で鉤に改めた: 座は弦の高さ（GRIP + 筒の半分）、入口はその POCKET_H 下、前の縁は肩の内側（x = SHOULDER）
sh, yp = t.SHOULDER, t.GRIP + P["stock_w"] / 2
assert (sh, yp + t.POCKET_H + 1) in trig.outline and (sh + P["notch_depth"], yp - 1) in trig.outline and t.seat_xy(P) == (sh + P["notch_depth"] - t.POCKET_W / 2, yp)

# 形ごとの部品と部品表が合い、飛ばす物は紙だけ（竹串・楊枝・豆を部品表に載せない）
for p in (P, B):
    keys = {q.key for q in t.parts(p)}
    rows = t.bom(p)
    assert keys <= {r["key"] for r in rows}
    assert not any(w in r["material"] for r in rows for w in ("竹串", "楊枝", "豆"))
    assert any(t.SAFETY in s for s in t.steps(p))
assert not any("輪ゴム" in r["material"] for p in (P, B) for r in t.bom(p))  # ばねは刷った紙だけ
# 出典は形ごと（弩はコマ 8 左、弓と毛玉はコマ 29 左）。既定の出典は既定の形の物
assert getattr(t, "SOURCES", {}) == {"crossbow": "NDL-1187053-R0000008-L-launcher", "bow": "NDL-1187053-R0000029-L-launcher"} and t.SOURCE == t.SOURCES[P["form"]]
# 引く長さ x がためる力の上限を決めるので、引ける所の限りを紙に刷り、組み方の文で言う
# 弩: 弦の溝は腕の根元から x + 1mm で終わり（溝の端が止め）、引き金の切れ込みはその x の所
st = next(q for q in t.parts(P) if q.key == "stock")
assert all(c[2] == P["draw"] + 1 for c in st.cuts if c[3] == t.SLIT) and any("溝の端" in s and f"{t.trigger_x(P):g}mm" in s for s in t.steps(P))
# 弓: 引き止めの帯に、弓から x の所の線を刷る。部品表にも載り、組み方の文がその線までと言う
stop = next((q for q in t.parts(B) if q.key == "drawstop"), None)
assert stop is not None and any(it["kind"] == "line" and all(abs(y - (t.STOP_BASE + B["draw"])) < 1e-9 for _, y in it["pts"]) for it in stop.art)
assert "drawstop" in {r["key"] for r in t.bom(B)} and any("引き止めの帯" in s and "線" in s for s in t.steps(B))
# 0.08J は確かめていない目安として書くだけで、決まり（規格）の値として書かない
assert "目安" in t.__doc__ and "安全の決まり" not in t.__doc__
# 2 回目の指摘の行: 弓のばねは刷った紙だけ（輪ゴムを使わない）、弩は引ける所が 1 つで止めの条件で確かめる、
# 物差しの穴と床の範囲が合う、弓の真ん中の穴をあける、弦の糸が部品表にある、貼り重ねの 3 つの面を全部貼る、弩で引く長さを変えさせない
from shapely.geometry import Polygon
from shapely.ops import unary_union
CHECKS = {
 "H1 弓の k は作った物から": lambda: (not any("輪ゴム" in r["material"] for r in t.bom(B)) and "spring_k" not in t.DEFAULTS
     and abs(t.spring_k(B) - 2 * 3 * t.E_HIGH * (P["arm_w"] * (t.LAYERS * P["paper_t"]) ** 3 / 12) / ((B["bow_span"] - t.GRIP_W) / 2) ** 3 * 1000) < 1e-9  # 4 回目で梁を持つ所の外に改めた
     and t.energy_mj({**B, "paper_t": 0.3}) > t.energy_mj(B)),
 "H2 弩の引きは 1 つで、測って止める": lambda: (not any("引く長さを減らす" in s for s in t.steps(P))
     and any("使わない" in s and f"{t.sag_print(P)}mm" in s for s in t.steps(P))
     and any("使わない" in s and f"{t.sag_print(B)}mm" in s for s in t.steps(B))),
 "M 物差しの穴と閉じた範囲": lambda: (lambda s, b: any(f.where == "玉" for f in t.check_physics({**P, "ball_d": s}))
     and any(f.where == "玉" for f in t.check_physics({**P, "ball_d": b})) and not any("物差しの穴" in f.message for f in t.check_physics({**P, "ball_d": s + t.GAUGE_TOL})))(*t.gauge_holes(P)),
 # 4 回目で弓の真ん中の毛玉の穴をやめた（持つ所の帯の上から巻いて結ぶ）。刷る穴（両端）をあける文があるかを見る
 "M 弓の穴をあける文": lambda: any("両端の穴" in s and "あけ" in s for s in t.steps(B)) and len(next(q for q in t.parts(B) if q.key == "stave").holes) == 2 * t.LAYERS,
 "M 弓の弦の糸が部品表に": lambda: any(r["key"] == "string" and "糸" in r["material"] for r in t.bom(B)),
 "M 貼り重ねの 3 つの面": lambda: (lambda a: abs(unary_union([Polygon(g) for g in a.glue]).area - a.width * a.height) < 1e-6)(next(q for q in t.parts(P) if q.key == "arma"))
     and any("裏" in s and "貼" in s for s in t.steps(P)),
 "L 弩で引く長さを変えさせない": lambda: not any("引く長さを変えて" in s for s in t.steps(P)) and "変える" not in t.measures(P)["predict"],
}
for name, check in CHECKS.items():
    assert check(), name
# 3 回目の指摘の行: 毛玉の先は芯の玉で見る、止めの下がりは切り上げて刷る（どの寸法でも刷った値 ≧ 式の値）、
# 弓の毛玉の穴は引き止めの帯の糊代から外す、弩の腕の穴をあける文、弓は両端を測る、穴あけの竹串を用意する物に、房の長さが合う
import itertools, re
from shapely.geometry import Point
def printed_sags(p):
    return [float(x) for s in t.steps(p) if "止めの条件" in s for x in re.findall(r"([\d.]+)mm 以上下がらなければ", s)]
def sag_ok():
    for f, al, aw, pt in itertools.product(("crossbow", "bow"), (30, 50, 70), (8, 9, 12), (0.1, 0.12, 0.2, 0.3)):
        p = {**P, "form": f, "arm_len": al, "arm_w": aw, "paper_t": pt}
        got = printed_sags(p)
        if not got or min(got) < t.tip_sag_min(p):
            return False
    return True
def hole_clear():
    sv = next(q for q in t.parts(B) if q.key == "stave")
    L = B["bow_span"]
    glue = Polygon([(L / 2 - t.STOP_W / 2, 0), (L / 2 + t.STOP_W / 2, 0), (L / 2 + t.STOP_W / 2, sv.height), (L / 2 - t.STOP_W / 2, sv.height)])
    return all(not glue.intersects(Point(x, y).buffer(r)) for x, y, r in sv.holes)
CHECKS3 = {
 "H 毛玉の先は芯で見る": lambda: t.nose_d(B) == B["ball_d"] and any(f.where == "玉" for f in t.check_physics({**B, "ball_d": 12})) and t.check_physics({**B, "fringe_len": 6}) == [],
 "H 止めの下がりは切り上げて刷る": sag_ok,
 "M 弓の真ん中の穴と引き止めの糊代": hole_clear,
 "M 弩の腕の穴をあける文": lambda: any("腕の先の穴" in s and "あけ" in s for s in t.steps(P)),
 "M 弓は両側を測る": lambda: any("止めの条件" in s and "両端" in s and "どちらか" in s for s in t.steps(B)),
 "L 穴あけの竹串が用意する物に": lambda: all(any("竹串" in m and "片づけ" in m for m in t.materials(p)) for p in (P, B)),
 "L 房の長さが合う": lambda: (lambda q: abs(q.width - t.POM_LEN) < 1e-9 and abs(t.projectile_mass({**B, "ball_paper": 1e-9}) - Polygon(q.outline).area * B["paper_gsm"] * 1e-6) < 1e-6)(next(q for q in t.parts(B) if q.key == "pompom")),
}
for name, check in CHECKS3.items():
    assert check(), name
# 4 回目の指摘の行: 弓は持つ所を刷り梁はその外、弩は引いてから玉を入れる、竹串は大人があけて片づけ筒の中で弦に掛からない、
# 固く丸めた玉を落とす、弓の向けと構えと糸の長さの上限、腕は根元の折り線で押さえる、δ と x の余裕を書く
def idx(steps, *words):
    return next(i for i, s in enumerate(steps) if all(w in s for w in words))
CHECKS4 = {
 "H 弓は持つ所を刷り、梁はその外": lambda: (getattr(t, "GRIP_W", None) and t.beam_len(B) == (B["bow_span"] - t.GRIP_W) / 2
     and "grip" in {q.key for q in t.parts(B)} and "grip" in {r["key"] for r in t.bom(B)}
     and any("持つ所の帯の内だけ" in s for s in t.steps(B))
     and any(f.where == "ばね" for f in t.check_physics({**B, "bow_span": 80, "paper_t": 0.12, "arm_w": 10, "draw": 34}))),
 "H 弩は引いてから玉を入れる": lambda: idx(t.steps(P), "引き金", "弦を掛ける") < idx(t.steps(P), "玉を台の前の口から入れ"),
 "M 竹串は大人があけて片づけ、筒の中で弦に掛からない": lambda: (t.skewer_clear(P) >= 2 and any(f.where == "弦の溝" and "竹串" in f.message for f in t.check_physics({**P, "stock_w": 12, "glue": 4, "ball_d": 10, "ball_paper": 40}))
     and all(any("大人" in s and "竹串" in s and "片づけ" in s for s in t.steps(p)) for p in (P, B))
     and all(any("大人" in m and "竹串" in m for m in t.materials(p)) for p in (P, B))),
 "M 固く丸めた玉を落とす": lambda: (t.bulk_density(P) <= t.DENSITY_MAX
     and any("固" in f.message for f in t.check_physics({**P, "ball_paper": 100, "paper_gsm": 100, "ball_d": 16.5}))),
 "M 弓の向けと構え・糸の長さの上限": lambda: (any("遠くの壁か床" in s for s in t.steps(B)) and any("顔から離し" in s for s in t.steps(B))
     and any(f.where == "毛玉の糸" for f in t.check_physics({**B, "tether": t.TETHER_MAX + 1})) and t.check_physics({**B, "tether": t.TETHER_MAX}) == []),
 "L 腕は根元の折り線で押さえる": lambda: any("止めの条件" in s and "根元の折り線" in s for s in t.steps(P)),
 # 7 回目で δ ≒ x/2 の見込みを δ ≒ x − slack_takeup に改めた（糸は伸びないので）。上限との書き分けがあるかを見る
 "L δ と x の余裕を書く": lambda: "δ ≒ x − slack_takeup" in t.__doc__ and "上限" in t.__doc__,
}
for name, check in CHECKS4.items():
    assert check(), name
# 5 回目の指摘の行: 引き金は前に縁のある鉤で座までの引きを力に入れる、弓の持つ所は 55mm 以上で貼り重ねて硬い、
# 弩の腕の根元の折りは確かめていないと書く、かさの密度は物差しの小さい穴で見る、弦の長さの印を刷り張って結ばない、
# 紙の玉のほかを筒に入れない、引き金に肩
from shapely.geometry import LineString
def hook_holds(p):
    """引き金の外形で、弦の座（くぼみ）の前に縁（lip）があるか: 弦の座の点から前（x が小さい向き）へ水平に出ると紙に当たる。"""
    tr = next(q for q in t.parts(p) if q.key == "trigger")
    poly = Polygon(tr.outline)
    sx, sy = t.seat_xy(p)
    if poly.contains(Point(sx, sy)):
        return False  # 座が紙の中では弦が入らない
    from shapely.geometry import LineString
    ray = LineString([(sx, sy), (-1, sy)])
    return ray.intersection(poly).length > 0
CHECKS5 = {
 "H 引き金は前に縁のある鉤で弦を受け、座までの引きを力に入れる": lambda: (hook_holds(P)
     and abs(t.draw_eff(P) - (P["draw"] + P["notch_depth"])) < 1e-9
     and any(f.where == "ばね" for f in t.check_physics({**P, "stock_w": 20, "draw": 25, "notch_depth": 9.76, "arm_w": 13.09, "paper_t": 0.2}))),
 "H 弓の持つ所は 55mm 以上で、貼り重ねて硬い": lambda: (t.GRIP_W >= 55 and t.GRIP_TURNS >= 3
     and abs(next(q for q in t.parts(B) if q.key == "grip").width - t.grip_len(B)) < 1e-9
     and any(f.where == "ばね" for f in t.check_physics({**B, "bow_span": 81.18, "paper_t": 0.08, "arm_w": 10.47, "draw": 30.24}))),
 "M 弩の腕の根元の折りは確かめていないと書く": lambda: "根元の折り" in t.__doc__ and "蝶番" in t.__doc__,
 "M かさの密度は物差しの小さい穴で見る": lambda: abs(t.bulk_density(P) - P["ball_paper"] ** 2 * P["paper_gsm"] * 1e-6 / (3.141592653589793 / 6 * ((t.gauge_holes(P)[0] + t.GAUGE_TOL) / 10) ** 3)) < 1e-9 and t.check_physics(P) == [],
 "M 弦の長さの印を刷り、張って結ばない": lambda: (t.STRING_SLACK > 0 and t.STRING_TOL >= 0  # 6 回目でずれを長い側だけにした（たるみ＞ずれ の決まりはやめた）
     and t.STRING_SLACK > 0
     and all("strlen" in {q.key for q in t.parts(p)} and any("張らない" in s and "印" in s for s in t.steps(p)) for p in (P, B))),
 "L 紙の玉のほかを筒に入れない": lambda: any("紙の玉のほか" in s and "入れない" in s for s in t.steps(P)) and "おはじき" in t.__doc__,
 "L 引き金に肩": lambda: (lambda tr: tr.width > P["trigger_w"] + 1)(next(q for q in t.parts(P) if q.key == "trigger")),
}
for name, check in CHECKS5.items():
    assert check(), name
# 6 回目の指摘の行: たるみを取る引きを数えて動く床を持つ（結び目は長い側）、docstring の数が今のコードと合う、
# 持つ所の帯は巻くごとの太りを数える、玉は引き金の前の縁で止まると言う、糸の印の間と肩のはみ出し
import math
def takeup_ok(p):
    s = t.STRING_SLACK + t.STRING_TOL
    a = (t.string_len(p) - t.STRING_SLACK) / 2
    return abs(t.slack_takeup(p) - math.sqrt((a + s / 2) ** 2 - a * a)) < 1e-9
def grip_ok(p):
    n, pt, aw = t.GRIP_TURNS, p["paper_t"], p["arm_w"]
    need = sum(2 * (aw + t.LAYERS * pt) + 4 * (2 * i + 1) * pt for i in range(n))
    g = next(q for q in t.parts(p) if q.key == "grip")
    over = g.glue[0][1][0] - g.glue[0][0][0]
    return abs(g.width - (need + over)) < 1e-9 and over >= 6
def marks_ok(p):
    sl = next(q for q in t.parts(p) if q.key == "strlen")
    xs = sorted(it["pts"][0][0] for it in sl.art if it["kind"] == "line")
    return len(xs) == 2 and abs(xs[1] - xs[0] - t.string_len(p)) < 1e-9
def shoulders_ok(p):
    tr = next(q for q in t.parts(p) if q.key == "trigger")
    st = next(q for q in t.parts(p) if q.key == "stock")
    slot = next(c for c in st.cuts if c[3] == t.SLOT)
    # 引き金の体（肩の下）は台の切れ込みの前の端に前の縁をそろえて差す。肩は切れ込みの前と後ろの両方にはみ出す
    front = t.SHOULDER  # 体の前の縁から肩の前の端まで
    rear = (tr.width - t.SHOULDER) - slot[2]  # 体の前の縁から肩の後ろの端まで − 切れ込みの長さ
    return front > 0 and rear > 0
CHECKS6 = {
 "H たるみを取る引きを数え、動く床を持つ": lambda: (t.STRING_SLACK <= 1 and takeup_ok(P) and takeup_ok(B)
     and any(f.where == "弦" and "動かない" in f.message for f in t.check_physics({**P, "draw": 10}))
     and t.check_physics(P) == [] and t.check_physics(B) == []
     and any("長い側" in s for s in t.steps(P)) and any("長い側" in s for s in t.steps(B))),
 "M docstring の数が今のコードと合う": lambda: all(w in t.__doc__ for w in ("26.9mJ", "22.7mJ", "55mm", "3.7%", "5.6%", "座の奥")) and "E ≒ 20mJ" not in t.__doc__ and "持つ所 30mm" not in t.__doc__,
 "M 持つ所の帯は巻くごとの太りを数える": lambda: grip_ok(B) and grip_ok({**B, "paper_t": 0.3}),
 "L 玉は引き金の前の縁で止まると言う": lambda: any("引き金の前の縁で止まる" in s for s in t.steps(P)),
 "L 糸の印の間と肩のはみ出し": lambda: marks_ok(P) and marks_ok(B) and shoulders_ok(P),
}
for name, check in CHECKS6.items():
    assert check(), name
# 7 回目の指摘の行: 動く床は玉の後ろ（draw）で見る（切れ込みの深さを数えない反例を含む）、たるみの引きを式を写さず
# 糸の長さの幾何から解いて合わせる、δ ≒ x − たるみの引き と書く
def half_from_holes(p):
    """刷った穴の位置から、両端の穴の間の半分 a を出す（string_len を使わない）。"""
    if p["form"] == "bow":
        xs = [x for x, _, _ in next(q for q in t.parts(p) if q.key == "stave").holes]
        return (max(xs) - min(xs)) / 2
    arm = next(q for q in t.parts(p) if q.key == "arma")
    return p["stock_w"] / 2 + (arm.holes[0][0] - t.ROOT)  # 台の外の面（腕の根元の折り線）から先の穴まで


def takeup_direct(p):
    """式を写さず、糸の長さの幾何から二分法で解く: 両端 (±a, 0) に結んだ長さ 2a + s の糸の真ん中を、ぴんと張るまで y 引く。"""
    a = half_from_holes(p)  # 8 回目: string_len を使わず、刷った穴の位置から出す
    s = t.STRING_SLACK + t.STRING_TOL
    lo, hi = 0.0, a
    for _ in range(200):
        y = (lo + hi) / 2
        if 2 * (a * a + y * y) ** 0.5 < 2 * a + s:
            lo = y
        else:
            hi = y
    return (lo + hi) / 2
CHECKS7 = {
 "H 動く床は玉の後ろ（引き金の前の縁＝draw）で見る": lambda: (
     any(f.where == "弦" for f in t.check_physics({**P, "draw": 10, "notch_depth": 8, "trigger_w": 12}))
     and "13.45mm" in t.__doc__ and "17.4mm" not in t.__doc__ and t.check_physics(P) == [] and t.check_physics(B) == []),
 "L たるみの引きを幾何で別に解いて合わせる": lambda: all(abs(t.slack_takeup(p) - takeup_direct(p)) < 1e-6 for p in (P, B, {**P, "arm_len": 30}, {**B, "bow_span": 100})),
 "L δ ≒ x − たるみの引き と書く": lambda: "δ ≒ x − slack_takeup" in t.__doc__ and "δ ≒ x/2" not in t.__doc__,
}
for name, check in CHECKS7.items():
    assert check(), name
# 8 回目の指摘の行: 弓の物差しの穴も大人がカッターで切る、玉と弦の間を式の値で刷る、弩も顔から離し腰の高さで飛ばす、
# 半分の長さ a を刷った穴から別に出す
CHECKS8 = {
 "M 弓の物差しの穴も大人がカッターで切る": lambda: any("物差しの穴" in s and "カッター" in s and "大人" in s for s in t.steps(B)) and any("カッター" in m and "大人" in m for m in t.materials(B)),
 "L 玉と弦の間を式の値で刷る": lambda: all(any(f"玉の {pp['notch_depth'] - t.POCKET_W / 2:g}mm 後ろ" in s for s in t.steps(pp)) for pp in (P, {**P, "notch_depth": 6})),
 "L 弩も顔から離し腰の高さで飛ばす": lambda: any("引き金を真上" in s and "顔から離し" in s and "腰の高さ" in s for s in t.steps(P)),
 "L 半分の長さ a を刷った穴から別に出す": lambda: all(abs(half_from_holes(p) - (t.string_len(p) - t.STRING_SLACK) / 2) < 1e-9 for p in (P, B, {**P, "arm_len": 30}, {**B, "bow_span": 100})),
}
for name, check in CHECKS8.items():
    assert check(), name
# 大人がカッターで切る物は、用意する物の行と組み方の文で同じ（#41）。両方の文から取り出して比べるので、片方だけ変えると落ちる
from omochae.compose import compose
from omochae.__main__ import load_source


def adult_cuts(lines):
    """文の並びから「大人がカッターで切る物」の組を取り出す。部品の番号（1 台の…の 1）は外す。カッターの文が 1 つでない時は None。"""
    found = [re.search(r"([^。（]*)はカッターで大人が切る", s) for s in lines if "カッター" in s]
    if len(found) != 1 or not found[0]:
        return None
    return {re.sub(r"^\d+ ", "", x.strip()) for x in found[0].group(1).split("、")}


for pp, want in ((P, {"台の細い溝と切れ込み", "玉の物差しの穴"}), (B, {"玉の物差しの穴"})):
    assert adult_cuts(t.materials(pp)) == adult_cuts(t.steps(pp)) == want, (t.materials(pp), t.steps(pp))
    # 文の組は部品と合う。台の溝と切れ込みだけが切り抜きで、玉の物差しの穴は 2 つ（腕と弓の穴は竹串なので入らない）
    assert {q.key for q in t.parts(pp) if q.cuts} == ({"stock"} if pp is P else set())
    assert len(next(q for q in t.parts(pp) if q.key == "gauge").holes) == 2
    # 片方だけ変えると食い違いが見える（比べ方が両方を読んでいる事を見る）
    assert adult_cuts([s.replace("玉の物差しの穴は", "穴は") for s in t.materials(pp)]) != adult_cuts(t.steps(pp))
    assert adult_cuts(t.materials(pp)) != adult_cuts([s.replace("玉の物差しの穴は", "穴は") for s in t.steps(pp)])
    # カッターの注記を別の行にすると、弩の紙が印字域の下の端に届く。行の数と、のりの行にある事を保つ
    assert any(m.startswith("のり、はさみ、定規（") and "カッター" in m for m in t.materials(pp)), t.materials(pp)
# 弓は断りの 1 行（制作者の決定 2026-11-06）を足して 8 行
assert len(t.materials(P)) == 6 and len(t.materials(B)) == 8, (len(t.materials(P)), len(t.materials(B)))
# 境の寸法: 通っていた寸法は通り、その上は同じ床で落ちる（文を長くして 1 行増えると、下の 3 つが落ちる）
src = load_source(t.SOURCES["crossbow"])
floors = lambda **over: [f.floor for f in compose("launcher", {"form": "crossbow", **over}, src)[2]]
for over in ({"stock_w": 21}, {"arm_w": 10}, {"ball_paper": 62}):
    assert floors(**over) == [], (over, floors(**over))
assert "F5.print_area" in floors(stock_w=21.05) and "F5.print_area" in floors(arm_w=10.05), "印字域の検査を緩めていない"
# 弓と毛玉の断り（制作者の決定 2026-11-06: 型紙に残し、断りを書く）: 刷る紙の「用意する物」の終わりに 1 行。弩には出さない
assert t.materials(B)[-1] == t.BOW_CAVEAT, t.materials(B)[-1]
assert "持つ所と握る手に当たる見込み" in t.BOW_CAVEAT and "図に弦は描かれておらず" in t.BOW_CAVEAT
assert not any(m.startswith("断り") for m in t.materials(P)), t.materials(P)
# 刷った紙で断りは折り返さず 1 行に載り、弓の紙は検査 0 件のまま
_, layout, failures = compose("launcher", B, load_source(t.SOURCES["bow"]))
assert not failures, [f.line() for f in failures]
assert any(x.text == f"・{t.BOW_CAVEAT}" for x in layout["texts"]), "断りが 1 行で紙に載っていない"
print("ok")
