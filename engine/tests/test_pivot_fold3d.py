"""虎の胴と脚を 3D の中で折って組む確かめ（制作者の決定 2026-11-06「御来迎 v12 と虎 v5 に、3D の確かめを試験として足す」）。

凍結の基準の 3D の床（3D.close など）は御来迎のつまみの形だけを見るので、虎は試験で見る。omochae.fold3d.fold で、刷る部品の外形と
折り線から面を組み、次を見る:
- 胴: 糊代 5 枚が、それぞれ貼る相手の面に寝て（面から 0.6mm 以内）、その面に 95% 以上重なる。相手は、端の壁の上の糊代 2 枚が
  1 枚目の側面、下の糊代 2 枚が 2 枚目の側面、上の面の糊代が帯の最後の面（角を落とした胴は 2 つ目の角の面、箱は 2 枚目の側面）。
  刷った面（色の面）は、どの面も箱の外を向く。
  角を落とした胴（body_round）は、角の面の 2 本ずつの折り線と、上の面の糊代の折り線を 45° 折る（断面は八角に近い形）。
- 脚: 横の糊代が角筒の 1 面目の内に寝て重なり、4 面とも刷った面が外を向く。上の 2 つの糊代は角筒の内へ 90° 山折りし、刷った面
  （斜線）が上（胴の底に貼る側）を向く。
面は硬い板、折り線は蝶番と見て、紙の厚み・たわみ・摩擦は入れない（fold3d と同じ）。通っても、紙で組める保証ではない。
端の壁の糊代の根元の角を落とす前の形は、糊代と側面が 1 枚の面になり、折って組めなかった。
"""
import json
import math
import pathlib

from shapely.geometry import Polygon

from omochae.fold3d import _glue_faces, fold
from omochae.templates import pivot_counterweight as pc

ROOT = pathlib.Path(__file__).resolve().parents[1]
v5 = dict(pc.DEFAULTS, **json.loads((ROOT / "examples/tora_v5.json").read_text(encoding="utf-8"))["params"])


def sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def unit(a):
    n = math.sqrt(dot(a, a))
    return tuple(x / n for x in a)


def body_angles(body, p):
    """角を落とした胴の折り線の角。胴の帯の横の折り線（上から順に 糊代|上・上|角・角|側・側|底・底|側・側|角）のうち、角の面に
    かかる 4 本を 45°。角を落とさない箱は、どれも 90°（None）。"""
    if not p["body_round"]:
        return None
    H, L = p["body_height"], p["body_length"]
    rows = sorted((ln for ln in body.mountain if ln[0][1] == ln[1][1] and ln[0][0] == H and ln[1][0] == H + L), key=lambda ln: ln[0][1])
    assert len(rows) == 6, rows
    return {rows[i]: 45 for i in (0, 1, 2, 5)}


def lies_on(g, faces, skip):
    """糊代の面 g が寝て（面から 0.6mm 以内）、95% 以上重なる面。無ければ None。"""
    pts = [g.at(pt) for pt in g.poly.exterior.coords[:-1]]
    for f in faces:
        if f is g or f in skip:
            continue
        flat = [f.flat(q) for q in pts]
        if all(abs(z) <= 0.6 for _, z in flat):
            proj = Polygon([xy for xy, _ in flat])
            if proj.is_valid and proj.intersection(f.poly).area >= 0.95 * g.poly.area:
                return f
    return None


def outward(faces):
    """刷った面が、面の集まりの真ん中から外を向かない面の数。"""
    mids = [f.at(f.poly.centroid.coords[0]) for f in faces]
    c = tuple(sum(m[k] for m in mids) / len(mids) for k in range(3))
    return sum(1 for f, m in zip(faces, mids) if dot(f.normal, sub(m, c)) <= 1e-9)


def check_body(p):
    body = next(x for x in pc.parts(p) if x.key == "body")
    faces = fold(body, angles=body_angles(body, p))
    glue = _glue_faces(body, faces)
    assert len(glue) == 5, (p["mount"], len(glue))
    # 帯の面を、頁の上の真ん中の y で見分ける（上・角・1 枚目の側面・底・2 枚目の側面・角の順に y が増える）
    H, L, W, g, c = p["body_height"], p["body_length"], p["body_width"], p["glue"], p["body_round"]
    d = c / math.sqrt(2)
    ch1 = g + (W - 2 * d) + c
    b0, b1 = ch1 + (H - d), ch1 + (H - d) + W
    ch2 = b1 + (H - d)
    strip = lambda f: H < f.poly.centroid.x < H + L
    side1 = next(f for f in faces if strip(f) and ch1 < f.poly.centroid.y < b0)
    side2 = next(f for f in faces if strip(f) and b1 < f.poly.centroid.y < ch2)
    last = next(f for f in faces if strip(f) and f.poly.centroid.y > ch2) if c else side2
    for gl in glue:
        y = gl.poly.centroid.y
        want = last if y < g else (side1 if y < b0 else side2)  # 上の面の糊代は y が 0〜g、壁の上の糊代は b0 の上、下の糊代は b1 の下
        got = lies_on(gl, faces, glue)
        assert got is want, (p["mount"], c, round(y, 1), got is None)
    walls = [f for f in faces if f not in glue]
    assert outward(walls) == 0, outward(walls)
    return len(walls)


# 1. 胴: 首の形・吊る形（既定の箱）と、次の組の見本（角を落とした胴）。糊代の幅の範囲の両端でも組める
assert check_body(dict(pc.DEFAULTS, mount="neck")) == 6  # 上・側・底・側・前の壁・後ろの壁
assert check_body(dict(pc.DEFAULTS, mount="hang", axle_height=pc.DEFAULTS["body_height"] - pc.HOLE_MARGIN)) == 6
for gl in pc.RANGES["glue"]:
    check_body(dict(pc.DEFAULTS, mount="neck", glue=gl))
assert check_body(v5) == 8  # 角の面 2 つが増える

# 2. 脚: 角筒が閉じ、色の面が外、上の糊代は上を向く（次の組の見本の脚 4 本）
legs = [x for x in pc.parts(v5) if x.key.startswith("leg")]
assert len(legs) == 4
a, t, h = pc.LEG_SIDE, pc.LEG_TAB, v5["leg_height"]
for leg in legs:
    faces = fold(leg)
    glue = _glue_faces(leg, faces)
    side = [g for g in glue if g.poly.bounds[0] >= 4 * a - 1e-9]  # 横の糊代（x が 4a より右）
    tabs = [g for g in glue if g not in side]
    assert len(side) == 1 and len(tabs) == 2, (len(side), len(tabs))
    tube = [f for f in faces if f not in glue]
    f0 = next(f for f in tube if f.poly.contains(Polygon([(a / 2 - 0.1, t + h / 2 - 0.1), (a / 2 + 0.1, t + h / 2 - 0.1), (a / 2 + 0.1, t + h / 2 + 0.1)]).centroid))
    assert len(tube) == 4 and lies_on(side[0], tube, []) is f0, leg.key  # 横の糊代は、角筒の 1 面目（x が 0〜a）の内に貼る
    assert outward(tube) == 0, leg.key
    up = unit(sub(f0.at((a / 2, t)), f0.at((a / 2, t + h))))  # 脚の下の端から上の端（胴の底の側）への向き
    assert all(dot(g.normal, up) > 0.99 for g in tabs), [dot(g.normal, up) for g in tabs]

# 3. ① 糊代の根元: 胴の糊代の多角形の辺は、どれも外形か折り線に乗る（隣の側面と、切る線も折り線も無い縁でつながらない）。
#    首の形・吊る形・角を落とした胴、糊代の幅の範囲の両端で見る（落とす前は、端の壁の糊代 4 枚が糊代の幅だけ側面とつながっていた）
from shapely.geometry import LineString

for q in (dict(pc.DEFAULTS, mount="neck"), dict(pc.DEFAULTS, mount="hang", axle_height=pc.DEFAULTS["body_height"] - pc.HOLE_MARGIN), v5,
          dict(pc.DEFAULTS, mount="neck", glue=pc.RANGES["glue"][0]), dict(pc.DEFAULTS, mount="neck", glue=pc.RANGES["glue"][1])):
    body = next(x for x in pc.parts(q) if x.key == "body")
    edge = Polygon(body.outline).boundary
    folds = [LineString(ln) for ln in body.mountain + body.valley]
    for gl in body.glue:
        for a_, b_ in zip(gl, gl[1:] + gl[:1]):
            seg = LineString([a_, b_])
            on = edge.buffer(1e-6).contains(seg) or any(f.buffer(1e-6).contains(seg) for f in folds)
            assert on, (q["mount"], q["glue"], a_, b_)

# 4. ② 札「1 胴」: 後ろの壁の床の側の白い帯の内にあり、縞・黒い斑・位置の印にかからない（胴の高さと幅の範囲の下限・角を落とした胴でも）
from omochae.textfit import text_width

for q in (dict(pc.DEFAULTS, mount="neck"), v5, dict(pc.DEFAULTS, mount="neck", body_height=pc.RANGES["body_height"][0], axle_height=20,
                                                       body_width=pc.RANGES["body_width"][0], strip_width=10)):
    body = next(x for x in pc.parts(q) if x.key == "body")
    H, L, W, g, c = q["body_height"], q["body_length"], q["body_width"], q["glue"], q["body_round"]
    d = c / math.sqrt(2)
    b0 = g + (W - 2 * d) + c + (H - d)
    x0, y0 = body.label_xy
    box = Polygon([(x0, y0), (x0 + text_width(body.label, pc.LABEL_SIZE), y0), (x0 + text_width(body.label, pc.LABEL_SIZE), y0 + 1.3 * pc.LABEL_SIZE),
                   (x0, y0 + 1.3 * pc.LABEL_SIZE)])
    band = Polygon([(H + L + 0.2, b0 + 0.2), (H + L + 0.2 + pc.FOOT_BAND * (H - 0.4), b0 + 0.2), (H + L + 0.2 + pc.FOOT_BAND * (H - 0.4), b0 + W - 0.2),
                    (H + L + 0.2, b0 + W - 0.2)])
    assert band.contains(box), (q["body_height"], q["body_width"], box.bounds, band.bounds)
    marks_or_ink = [a_ for a_ in body.art if a_["kind"] == "mark" or a_.get("fill") in (pc.STRIPE, pc.INK)]
    for a_ in marks_or_ink:
        shape = Polygon(a_["pts"]) if a_["kind"] == "poly" else LineString(a_["pts"]).buffer(0.3)
        assert not shape.intersects(box), (q["body_height"], a_.get("mark") or a_.get("fill"))
print("ok 虎の胴と脚を 3D で折って組む・糊代の根元・胴の札")
