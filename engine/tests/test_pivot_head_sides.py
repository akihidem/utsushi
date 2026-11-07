"""虎 v6 の両面の頭（制作者の指示 2026-11-06「顔は、両側に貼れるように首から立体的にするか、両側から見た物を用意して。」の後の方）。

2 頭を、今の顔と、頭の上で折り返した鏡写しの顔の 1 つの部品にする（寸法 head_sides 2・pivot_counterweight._head_part）。次を見る:
1. 既定（head_sides 1）の頭は今のまま（外形・地の輪郭線・札）。凍結の場面の紙を変えないため（刷り比べは別に見る）。
2. 両面の頭の形: 外形は頭の上の平らな線（山折り）で上下の鏡写し。絵は前と後ろの半分に同じ数で、後ろは前の鏡写し。
   札は前の半分だけ。絵は折り線をまたがず、部品の外に出ない（F5.image_box）。
3. 3D: 山折りの線で 180° 折ると、後ろの半分は前の半分にぴったり重なり、口も同じ所に来る（反対の側からも、口が前を向いた顔が見える）。
   180° では谷と山の向きが見分けられないので、170° でも折り、どちらの半分も相手の裏の側に来る（刷った面の顔が両側の外を向く）事を見る。
4. 組み方の文: 手順の数と番号は変えず、頭を貼る 1 行だけが替わる。
5. 寸法: head_sides は選ぶ値の 1 か 2（spec() に mount と同じく選ぶ値で出す。1.5・3・0・True は落とす）。吊る形の両面の頭は
   落とす（頭の裏に粘土を貼るため）。
6. 揺れの式: 両面の頭は頭の紙が 2 倍。見本 examples/tora_v6.json は v5 の見本に head_sides 2 を足しただけで、検査を全部通る。
7. 首の帯: 両面の頭の 2 枚の間に挟むので、頭の真ん中の高さに帯の幅と上下の貼り代 1mm ずつが入らない寸法は落とす（見直しの指摘:
   頭の高さ 15・帯の幅 20 が通っていた）。頭の真ん中の高さは、刷る部品の前の半分の外形で測った高さと同じ。境の両側を見る。
面は硬い板、折り線は蝶番と見る（fold3d と同じ）。帯を挟んだ厚みと糊は入れない。通っても、紙で組める保証ではない。
"""
import json
import pathlib
from decimal import Decimal

from shapely import affinity
from shapely.geometry import Polygon

from omochae.__main__ import load_source
from omochae.compose import compose
from omochae.floors import check_art
from omochae.fold3d import fold
from omochae.templates import pivot_counterweight as pc

ROOT = pathlib.Path(__file__).resolve().parents[1]
ex = {n: json.loads((ROOT / f"examples/{n}.json").read_text(encoding="utf-8")) for n in ("tora_v5", "tora_v6")}
v5, v6 = (dict(pc.DEFAULTS, **ex[n]["params"]) for n in ("tora_v5", "tora_v6"))
head = lambda q: next(x for x in pc.parts(q) if x.key == "head")

# 1. 既定の頭は今のまま
one = head(dict(pc.DEFAULTS, mount="neck"))
w, h = pc.DEFAULTS["head_w"], pc.DEFAULTS["head_h"]
sx, sy = w / (245 - 40), h / (445 - 232)
assert one.outline == [((x - 40) * sx, (y - 232) * sy) for x, y in pc._HEAD] and not one.mountain and not one.valley
assert one.art[0].get("stroke") == pc.STRIPE and one.label == "2 頭" and one.label_xy == (w * 0.5, h * 0.6)

# 2. 両面の頭の形
two = head(v6)
assert pc.DEFAULTS["head_sides"] == 1 and v6["head_sides"] == 2
assert len(two.mountain) == 1 and not two.valley and not two.glue, (two.mountain, two.valley, two.glue)
(fx0, fy), (fx1, fy1) = two.mountain[0]
assert abs(fy - fy1) < 1e-9 and fx1 - fx0 > 5, two.mountain  # 平らな頭の上の水平な線。蝶番は 5mm より長い
outline = Polygon(two.outline)
assert outline.is_valid
front = outline.intersection(Polygon([(-1, fy), (99, fy), (99, 999), (-1, 999)]))
back = outline.intersection(Polygon([(-1, -999), (99, -999), (99, fy), (-1, fy)]))
assert affinity.scale(back, yfact=-1, origin=(0, fy)).symmetric_difference(front).area < 1e-6  # 上下の鏡写し
# 外す頭の上の尖りは、絵の点の y 232〜250（頭の高さの 18/213）。前の半分の高さは頭の高さからそれを引いた物で、部品はその 2 倍
cut = v6["head_h"] * (250 - 232) / (445 - 232)
assert abs(fy - (v6["head_h"] - cut)) < 1e-9 and abs(two.height - 2 * fy) < 1e-9, (fy, two.height, cut)
# 絵: 前の半分と後ろの半分に同じ数。後ろの半分の絵は、前の半分の絵の鏡写し
ys = lambda it: [y for _, y in it["pts"]]
fr = [it for it in two.art if min(ys(it)) >= fy - 1e-9]
bk = [it for it in two.art if max(ys(it)) <= fy + 1e-9]
assert len(fr) == len(bk) == len(two.art) // 2 == len(one.art), (len(fr), len(bk), len(two.art), len(one.art))
for a, b in zip(fr, bk):
    assert a["kind"] == b["kind"] and a.get("fill") == b.get("fill")
    assert all(abs(qa[0] - qb[0]) < 1e-9 and abs(qa[1] - (2 * fy - qb[1])) < 1e-9 for qa, qb in zip(a["pts"], b["pts"]))
# 地には輪郭線を引かない（線は折り線の上にも乗るので）。札は前の半分で、今の頭と同じ所（顔の絵に対して）
assert not two.art[0].get("stroke") and two.label == "2 頭" and two.label_xy[1] > fy
# 前の半分は、今の頭を dy（= 折り線の高さ − 外した尖りの高さ）だけ下げた物。札も同じだけ下げた所
dy = fy - cut
assert abs(two.label_xy[0] - v6["head_w"] * 0.5) < 1e-9 and abs(two.label_xy[1] - (v6["head_h"] * 0.6 + dy)) < 1e-9, two.label_xy
assert check_art([two]) == [], [f.line() for f in check_art([two])]


# 3. 3D で折る
def halves(faces):
    """折った面を、前の半分（頁の上で折り線より下）と後ろの半分に分ける。"""
    assert len(faces) == 2, len(faces)
    f, b = sorted(faces, key=lambda x: -x.poly.centroid.y)
    return f, b


def onto(src, dst, pts):
    """src の面の頁の上の点を、折った後に dst の面の頁の上の点と面から浮く量にする。"""
    return [dst.flat(src.at(p)) for p in pts]


line = two.mountain[0]
f180, b180 = halves(fold(two, angles={line: 180}))
proj = onto(b180, f180, list(b180.poly.exterior.coords)[:-1])
assert all(abs(z) < 1e-6 for _, z in proj), max(abs(z) for _, z in proj)  # 後ろの半分は前の半分と同じ面に寝る
laid = Polygon([xy for xy, _ in proj])
assert laid.intersection(f180.poly).area >= 0.99 * f180.poly.area and laid.symmetric_difference(f180.poly).area < 1e-6
mouth_f = next(Polygon(it["pts"]) for it in fr if it.get("fill") == pc.MOUTH)
mouth_b = next(it["pts"] for it in bk if it.get("fill") == pc.MOUTH)
mouth_laid = Polygon([xy for xy, _ in onto(b180, f180, mouth_b)])
assert mouth_laid.symmetric_difference(mouth_f).area < 1e-6  # 反対の側から見た口も、前の口と同じ所（顔は前を向く）
f170, b170 = halves(fold(two, angles={line: 170}))
# 山折りなので、どちらの半分も相手の裏の側（刷った面の向きの負の側）に来る。刷った面の顔が両側の外を向く
assert all(z < 0 for _, z in onto(b170, f170, [b170.poly.centroid.coords[0]])), onto(b170, f170, [b170.poly.centroid.coords[0]])
assert all(z < 0 for _, z in onto(f170, b170, [f170.poly.centroid.coords[0]])), onto(f170, b170, [f170.poly.centroid.coords[0]])

# 4. 組み方の文: 数と番号は同じで、頭を貼る 1 行だけが替わる
s5, s6 = pc.steps(v5), pc.steps(v6)
diff = [(a, b) for a, b in zip(s5, s6) if a != b]
assert len(s5) == len(s6) and diff == [("3 首の帯の前の端に 2 頭を貼る",
                                        "2 頭を頭の上の山折りの線で後ろへ折る。3 首の帯の先を、口と反対の側から 2 枚の間の真ん中まで挟み、裏どうしを貼る")], diff
assert pc.materials(v5) == pc.materials(v6) and pc.bom(v5) == pc.bom(v6)

# 5. 寸法: 1 か 2 だけ。吊る形の両面の頭は落とす
assert pc.check_range(v6) == [] and pc.check_range(dict(v6, head_sides=2.0)) == []
for bad in (1.5, 3, 0, True, "2", Decimal("1"), 1 + 0j):  # Decimal と複素数は、等しさでは 1 でも揺れの式で例外になる
    fails = pc.check_range(dict(v6, head_sides=bad))
    assert [f.where for f in fails] == ["head_sides"] and fails[0].floor == "F5.range", (bad, [f.line() for f in fails])
assert pc.spec()["head_sides"] == pc.HEAD_SIDES == (1, 2) and "head_sides" not in pc.RANGES  # 連続の範囲でなく、選ぶ値
hang = dict(pc.DEFAULTS, mount="hang", axle_height=pc.DEFAULTS["body_height"] - pc.HOLE_MARGIN)
assert pc.check_physics(hang) == [], [f.line() for f in pc.check_physics(hang)]
fails = pc.check_physics(dict(hang, head_sides=2))
assert [f.line() for f in fails] == ["FAIL F5.pivot [頭] 吊る形は頭の裏に粘土を貼るので、頭を両面（head_sides 2）にできない"], [f.line() for f in fails]

# 6. 揺れの式と見本
assert abs(pc.mass_points(v6)[0][0] - 2 * pc.mass_points(v5)[0][0]) < 1e-12 and pc.mass_points(v6)[1:] == pc.mass_points(v5)[1:]
assert ex["tora_v6"]["params"] == dict(ex["tora_v5"]["params"], head_sides=2) and ex["tora_v6"]["source_id"] == ex["tora_v5"]["source_id"]
assert pc.check_physics(v6) == [], [f.line() for f in pc.check_physics(v6)]
_, _, fails = compose("pivot_counterweight", v6, load_source(ex["tora_v6"]["source_id"]))
assert not fails, [f.line() for f in fails]
assert [x.key for x in pc.parts(v6)] == [x.key for x in pc.parts(v5)]

# 7. 首の帯が両面の頭に挟めるか
from shapely.geometry import LineString  # noqa: E402


def drawn_span(q):
    """刷る部品の前の半分（折り線より下）の、頭の幅の真ん中の縦の高さ。"""
    hd = head(q)
    y0 = hd.mountain[0][0][1]
    half = Polygon(hd.outline).intersection(Polygon([(-1, y0), (99, y0), (99, 999), (-1, 999)]))
    return half.intersection(LineString([(q["head_w"] / 2, -999), (q["head_w"] / 2, 999)])).length


for q in (v6, dict(v6, head_h=15), dict(v6, head_h=45, head_w=15)):
    assert abs(pc.head_span_mm(q) - drawn_span(q)) < 1e-6, (q["head_h"], pc.head_span_mm(q), drawn_span(q))
assert v6["strip_width"] + 2 * pc.HEAD_GLUE_MIN <= pc.head_span_mm(v6)  # 見本は挟める（帯 10・頭の真ん中 約 19.6）
bad = dict(v6, head_h=15, strip_width=20, opening=30)  # 見直しの指摘の寸法
lines = [f.line() for f in pc.check_physics(bad)]
assert lines == [f"FAIL F5.pivot [頭] 首の帯（幅 20mm）を両面の頭の 2 枚の間に挟めない（頭の真ん中の高さ {pc.head_span_mm(bad):.1f}mm に、"
                 f"帯と上下の貼り代 {pc.HEAD_GLUE_MIN}mm ずつが入らない）"], lines
assert pc.check_physics(dict(bad, head_sides=1)) == []  # 片面の頭は帯の横の面に貼るので、この決まりは無い
edge = pc.head_span_mm(dict(v6, head_h=20)) - 2 * pc.HEAD_GLUE_MIN  # 境: 帯の幅がちょうど入る所は通り、少し広いと落ちる
assert not any("挟めない" in f.message for f in pc.check_physics(dict(v6, head_h=20, strip_width=round(edge - 0.05, 2))))
assert any("挟めない" in f.message for f in pc.check_physics(dict(v6, head_h=20, strip_width=round(edge + 0.05, 2))))
print("ok 虎 v6 の両面の頭（形・3D で折る・組み方の文・寸法・見本・首の帯）")
