"""作り方の 3D の JSON（omochae.assembly3d。窓口の決定 2026-11-07 カード 020154「…(a)、エンジンが JSON で出す形…」）を確かめる。

サイトの組み立ての頁はこの JSON を読んで描く（形の決めは ~/work/hackathon-grove/state/3d-json/FORMAT-v1.md）。次を見る:
1. 段と手順の文が 1 対 1（数も文も同じ）。どの POSE も、隠した物のほかの部品を全部持ち、面の数が部品の面の数と同じ。
2. 面ごとの行列（panels）と、根の置き場（place）＋面のつながり（tree）＋向きの付いた角（turns）から作った形が同じ
   （サイトは折る途中を turns で動かし、panels で確かめる。サイトの確かめは 0.7mm 以内）。
3. 虎 v6 のできあがり（最後の段の最後の POSE）:
   - 胴は閉じた箱で、底は脚の高さだけ上。どの面も刷った面が外を向く。糊代 5 枚は貼る相手の面に寝る（0.6mm 以内・95% 以上重なる）。
   - 脚の角筒の上の口は、胴の底の四角（位置の印）と同じ所で、脚の下の端は机（y = 0）。尾の糊代は上の面の後ろの四角に重なり、尾は上に立つ。
   - 竹串は胴の 2 つの穴を通り、前の壁の丸い穴の真ん中は竹串と同じ高さ。帯の穴は竹串の上。頭は両面で、帯の先が頭の真ん中。
   - 粘土の玉は 5 重りの腕の下の穴の所。
4. できあがりの動き（finale）: 頭が静かな時の傾き（刷る物の重さの所で見た傾き）のまわりに ±MIN_SWING の中で揺れて、静かな時の傾きで止まる
   （型紙の当たりの検査が見る角と同じ。前は水平のまわりに 12° まで揺らし、段の終わりの水平で止めていた）。
5. 入口: 書き出せる（終わりの値 0。虎 v7）。3D の組み立て検品（omochae.check3d）に落ちる形（虎 v6）は 3 で、JSON を書かない
   （検品の決めは tests/test_check3d.py）。組み立ての書き方が無い形（御来迎のつまみの形）は 4。
6. 紙の行列（paper.place）: 紙の座標を机の面（y = 0）へ写し、刷った面は上。段 1 の部品の置き場は、紙の行列と刷った所（paper.at）から出した物と同じ。
7. 手の種類（act）と動く部品（moving）がどの POSE にもある。中身の分解（structure）: inside・exploded（できあがりから離した 1 枚）・cutaway（見る人の方の面）。
8. 御来迎 v14（内筒を下から押し上げる）: 18 段。静かな時は内筒が外筒の中（隙間 0.75mm）、台の上の面は外筒の底から 70mm、扇と像は口の下。
   押し上げると台の上の面が口の高さで、扇は開く角の見込み（約 176°）の半円に開く（custom）。割り箸は開いた時も外筒の下へ 77mm 出る。
   外筒の刷った面は外、内筒の刷った面は内、台の刷った面は上、像は両側に顔。
   扇の開く所（custom）: 開き始め（と畳み終わり）は折りの形の畳んだ束と同じ（飛ばない）。開き切ると隣の板の上の端の角が合い、
   刷った面は見る人の方。途中も、どの板の上の端の真ん中も要から扇の高さの所（弧の上）にある。（見直しの指摘: 前は束と開きがつながらず、
   開き切っても板の間の折り線が合っていなかった）
9. 動く物: 消えた棒と、出た部品も動く物に入る（取り外す手・出す手を空の moving に読み違えない）。
紙は折り線で分けた硬い面（fold3d と同じ）。紙の厚み・糊・たわみは入れない。
"""
import json
import math
import os
import pathlib
import subprocess
import sys
import tempfile

from shapely.geometry import Polygon

from omochae.assembly3d import build
from omochae.templates import pivot_counterweight as pc

ROOT = pathlib.Path(__file__).resolve().parents[1]
data = build(ROOT / "examples/tora_v6.json", commit="test")
v6 = dict(pc.DEFAULTS, **json.loads((ROOT / "examples/tora_v6.json").read_text(encoding="utf-8"))["params"])
parts = {q["key"]: q for q in data["parts"]}
TOL = 0.01  # 行列は 5 桁に丸めて出すので、世界の点は 0.01mm まで（サイトの確かめは 0.7mm）


def M(c):
    """列優先の 16 個 → 行の並びの 4×4。"""
    return [[c[col * 4 + row] for col in range(4)] for row in range(4)]


def mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def ap(m, p):
    x, y = p[0], p[1]
    return tuple(m[i][0] * x + m[i][1] * y + m[i][3] for i in range(3))


def hinge(p1, p2, deg):
    """部品の座標の、点 p1 を通り p1→p2 の向きの線のまわりに deg 回す 4×4（右ねじで正。サイトの頁の hinge と同じ）。"""
    ux, uy = p2[0] - p1[0], p2[1] - p1[1]
    n = math.hypot(ux, uy)
    x, y = ux / n, uy / n
    a = math.radians(deg)
    c, s, t = math.cos(a), math.sin(a), 1 - math.cos(a)
    R = [[t * x * x + c, t * x * y, s * y], [t * x * y, t * y * y + c, -s * x], [-s * y, s * x, c]]
    px, py = p1
    tr = [px - (R[0][0] * px + R[0][1] * py), py - (R[1][0] * px + R[1][1] * py), -(R[2][0] * px + R[2][1] * py)]
    return [R[0] + [tr[0]], R[1] + [tr[1]], R[2] + [tr[2]], [0.0, 0.0, 0.0, 1.0]]


def normal(m):
    return (m[0][2], m[1][2], m[2][2])


# 1. 段と文
assert data["format"] == "omochae-assembly-3d/1" and data["toy"] == "tora-v6" and data["engine"]["commit"] == "test"
assert [s["text"] for s in data["steps"]] == pc.steps(v6) and [s["n"] for s in data["steps"]] == list(range(1, len(pc.steps(v6)) + 1))
for s in data["steps"]:
    assert s["poses"], s["n"]
    for pose in s["poses"]:
        assert set(pose["parts"]) | set(pose["hidden"]) == set(parts), (s["n"], sorted(pose["parts"]))
        for key, st in pose["parts"].items():
            assert len(st["panels"]) == len(parts[key]["panels"]), (s["n"], key)

# 2. panels と place＋tree＋turns が同じ形
worst = 0.0
for pose in [q for s in data["steps"] for q in s["poses"]] + data["finale"]["poses"]:
    for key, st in pose["parts"].items():
        tree = parts[key]["tree"]
        mats = {str(tree["root"]): M(st["place"])}

        def of(i):
            if i not in mats:
                row = tree["rows"][i]
                h = row["hinge"]
                mats[i] = mul(of(str(row["parent"])), hinge(h[0], h[1], st["turns"][i]))
            return mats[i]
        for pan in parts[key]["panels"]:
            i = str(pan["id"])
            a, b = of(i), M(st["panels"][i])
            worst = max(worst, max(math.dist(ap(a, pt), ap(b, pt)) for pt in pan["poly"]))
assert worst < 0.01, worst

# 3. 虎 v6 のできあがり
last = data["steps"][-1]["poses"][-1]
world = {key: {str(p["id"]): M(last["parts"][key]["panels"][str(p["id"])]) for p in parts[key]["panels"]} for key in last["parts"]}
H, L, W, legh, ax = v6["body_height"], v6["body_length"], v6["body_width"], v6["leg_height"], v6["axle_height"]
body = parts["body"]
pts = [ap(world["body"][str(p["id"])], q) for p in body["panels"] for q in p["poly"]]
lo, hi = [min(q[k] for q in pts) for k in range(3)], [max(q[k] for q in pts) for k in range(3)]
assert all(abs(a - b) < TOL for a, b in zip(lo, (0.0, -legh - H, -W / 2))) and all(abs(a - b) < TOL for a, b in zip(hi, (L, -legh, W / 2))), (lo, hi)
center = ((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, 0.0)
# 面の点は 4 桁に丸めて出すので、糊代の面は重なりの広さで見分ける（99% 以上が糊代の多角形の内）
glue_panels = {p["id"] for p in body["panels"] if any(Polygon(g).intersection(Polygon(p["poly"])).area >= 0.99 * Polygon(p["poly"]).area for g in body["glue"])}
assert len(glue_panels) == 5, glue_panels
for p in body["panels"]:
    if p["id"] in glue_panels:
        continue
    m = world["body"][str(p["id"])]
    c = Polygon(p["poly"]).centroid
    w = ap(m, (c.x, c.y))
    assert sum((w[k] - center[k]) * normal(m)[k] for k in range(3)) > 0, p["id"]  # 刷った面が外


def lies_on(m_tab, tab_poly, m_face, face_poly, tol=0.6):
    """糊代の面が、相手の面に寝て（面から tol 以内）、95% 以上重なるか。"""
    inv_n, o = normal(m_face), ap(m_face, (0.0, 0.0))
    pts3 = [ap(m_tab, q) for q in tab_poly]
    if any(abs(sum((q[k] - o[k]) * inv_n[k] for k in range(3))) > tol for q in pts3):
        return False
    # 相手の面の座標へ戻す（回転の転置）
    R = [row[:3] for row in m_face[:3]]
    flat = [tuple(sum(R[k][i] * (q[k] - o[k]) for k in range(3)) for i in range(2)) for q in pts3]
    return Polygon(flat).intersection(Polygon(face_poly)).area >= 0.95 * Polygon(tab_poly).area


for gid in glue_panels:
    tab = next(p for p in body["panels"] if p["id"] == gid)
    assert any(lies_on(world["body"][str(gid)], tab["poly"], world["body"][str(p["id"])], p["poly"])
               for p in body["panels"] if p["id"] not in glue_panels), gid
# 脚: 上の口は底の四角、下の端は机
marks = [a for a in body["art"] if a["kind"] == "mark" and a.get("mark") == "leg"]
bottom = next(p for p in body["panels"] if Polygon(p["poly"]).contains(Polygon(marks[0]["pts"]).centroid))
for k, mk in zip(("leg1", "leg2", "leg3", "leg4"), marks):
    sq = [ap(world["body"][str(bottom["id"])], q) for q in mk["pts"]]
    leg = parts[k]
    top = [ap(world[k][str(leg["panels"][1]["id"])], q) for q in ((0.0, 3.0), (7.0, 3.0))]
    assert all(min(math.dist(t, s) for s in sq) < TOL for t in top), (k, top, sq)
    ys = [ap(world[k][str(p["id"])], q)[1] for p in leg["panels"] for q in p["poly"]]
    assert abs(max(ys)) < TOL and abs(min(ys) + legh) < TOL, (k, min(ys), max(ys))
# 尾: 糊代は上の面の後ろの四角、尾は上に立つ
tail = parts["tail"]
mk = next(a for a in body["art"] if a["kind"] == "mark" and a.get("mark") == "tail")
top_face = next(p for p in body["panels"] if Polygon(p["poly"]).contains(Polygon(mk["pts"]).centroid))
tab = tail["panels"][1]
assert lies_on(world["tail"][str(tab["id"])], tab["poly"], world["body"][str(top_face["id"])], mk["pts"], tol=1e-6)
tip = ap(world["tail"]["0"], (pc.TAIL_W / 2, 0.0))
assert tip[1] < -legh - H - pc.TAIL_LEN + 1, tip  # 上の面より尾の長さだけ上
# 竹串・首の穴・帯・頭・粘土
sk = last["rods"]["skewer"]
holes = [ap(world["body"][str(p["id"])], (x, y)) for x, y, _ in body["holes"] for p in body["panels"] if Polygon(p["poly"]).buffer(1e-6).contains(Polygon([(x, y), (x + 1e-3, y), (x, y + 1e-3)]))]
for h in holes:
    assert abs(h[0] - sk["from"][0]) < TOL and abs(h[1] - sk["from"][1]) < TOL, (h, sk)
front = next(p for p in body["panels"] if p.get("inner"))
ring = front["inner"][0]
hole_c = ap(world["body"][str(front["id"])], (sum(x for x, _ in ring) / len(ring), sum(y for _, y in ring) / len(ring)))
assert abs(hole_c[1] - sk["from"][1]) < 1e-3 and abs(hole_c[0]) < TOL, hole_c  # 前の壁（x = 0）の穴の真ん中は竹串の高さ
strip_hole = ap(world["strip"]["0"], (v6["strip_width"] / 2, pc.STRIP_HOLE))
assert math.dist(strip_hole[:2], tuple(sk["from"][:2])) < TOL, strip_hole
tip_x = sk["from"][0] - (v6["neck_length"] + 6)
head = parts["head"]
fy = head["tree"]["rows"]["1"]["hinge"][0][1]
mid = ap(world["head"]["0"], (v6["head_w"] / 2, 1.5 * fy))
assert abs(mid[0] - tip_x) < TOL and abs(mid[1] - sk["from"][1]) < TOL, mid
assert normal(world["head"]["0"])[2] > 0.999 and normal(world["head"]["1"])[2] < -0.999  # 両側に顔
clay = last["balls"]["clay"]["at"]
assert abs(clay[1] - (sk["from"][1] + v6["weight_below_axle"])) < TOL and abs(clay[0] - sk["from"][0]) < TOL, clay
# 4. できあがりの動き: 静かな時の傾きのまわりに ±MIN_SWING の中で揺れて、静かな時の傾きで止まる


def turned(pose):
    """段の終わりの形（水平）から、軸のまわりに回した角 rad（頭の真ん中の点の向きで読む。頭が上がる向きが正）。"""
    m = ap(M(pose["parts"]["head"]["panels"]["0"]), (v6["head_w"] / 2, 1.5 * fy))
    return math.atan2(-(m[1] - sk["from"][1]), -(m[0] - sk["from"][0]))


fin = data["finale"]["poses"]
rest = sum(pc.swing_range(v6)) / 2
assert abs(turned(last)) < 1e-4 and abs(turned(fin[-1]) - rest) < 1e-4, (turned(last), turned(fin[-1]), rest)
assert abs(math.degrees(rest) + 5.46) < 0.01, math.degrees(rest)  # v6 の刷った形（粘土は軸の真下）は、頭が約 5.5° 下がって止まる
assert len(fin) >= 3 and all(abs(turned(f) - rest) <= math.radians(pc.MIN_SWING) + 1e-4 for f in fin)
assert max(abs(turned(f) - rest) for f in fin) > math.radians(pc.MIN_SWING) - 1e-3  # 揺れの端まで見せる
# 5. 入口
env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
with tempfile.TemporaryDirectory() as d:
    out = pathlib.Path(d) / "tora-v7.json"
    r = subprocess.run([sys.executable, "-m", "omochae.assembly3d", "--scenario", str(ROOT / "examples/tora_v7.json"), "--out", str(out), "--commit", "x"],
                       cwd=ROOT, env=env, capture_output=True, text=True)
    assert r.returncode == 0 and json.loads(out.read_text(encoding="utf-8"))["toy"] == "tora-v7", r.stderr
    out6 = pathlib.Path(d) / "tora-v6.json"
    r = subprocess.run([sys.executable, "-m", "omochae.assembly3d", "--scenario", str(ROOT / "examples/tora_v6.json"), "--out", str(out6), "--commit", "x"],
                       cwd=ROOT, env=env, capture_output=True, text=True)
    assert r.returncode == 3 and not out6.exists() and "FAIL 3D.hit" in r.stderr, (r.returncode, r.stderr)  # v6 は検品に落ちる（負の対照）
    r = subprocess.run([sys.executable, "-m", "omochae.assembly3d", "--scenario", str(ROOT / "examples/fan_tab.json")], cwd=ROOT, env=env, capture_output=True, text=True)
    assert r.returncode == 4, (r.returncode, r.stderr)

# 6. 紙の行列
P = M(data["paper"]["place"])
assert all(abs(ap(P, c)[1]) < TOL for c in ((0, 0), (data["paper"]["w"], 0), (0, data["paper"]["h"]))) and normal(P)[1] < -0.999
first = data["steps"][0]["poses"][0]
for key, (x, y) in data["paper"]["at"].items():
    got = M(first["parts"][key]["place"])
    root = next(pn for pn in parts[key]["panels"] if pn["id"] == 0)
    for q in root["poly"][:3]:
        assert math.dist(ap(got, q), ap(P, (q[0] + x, q[1] + y))) < TOL, (key, q)

# 7. 手の種類・動く部品・中身の分解
ACTS = {"cut", "fold", "thread", "place", "open", "move"}


def check_acts_structure(d, pk):
    for pose in [q for st in d["steps"] for q in st["poses"]] + d["finale"]["poses"] + [d["structure"]["exploded"]]:
        assert pose["act"] in ACTS and isinstance(pose["moving"], list), (pose.get("act"), pose.get("moving"))
    st = d["structure"]
    assert set(st["exploded"]["parts"]) == set(pk), sorted(st["exploded"]["parts"])
    for key, ids in st["cutaway"].items():
        for i in ids:
            assert i in d["steps"][-1]["poses"][-1]["parts"][key]["panels"], (key, i)


check_acts_structure(data, parts)
assert data["structure"]["inside"]["strip"] == "body" and data["structure"]["cutaway"] == {"body": ["3"]}
assert [q["act"] for q in data["steps"][6]["poses"]] == ["move", "thread", "thread"]  # 帯を穴に入れて竹串を通す
assert data["steps"][6]["poses"][2]["moving"] == ["skewer"] and "clay" in data["finale"]["poses"][0]["moving"]  # 棒と粘土の玉も動く物

# 8. 御来迎 v14
from omochae.templates import slider_fan as sf  # noqa: E402

g = build(ROOT / "examples/goraigo_v14.json", commit="test")
v14 = dict(sf.DEFAULTS, **json.loads((ROOT / "examples/goraigo_v14.json").read_text(encoding="utf-8"))["params"])
gp = {q["key"]: q for q in g["parts"]}
assert [st["text"] for st in g["steps"]] == sf.steps(v14) and len(g["steps"]) == 18
check_acts_structure(g, gp)
gworst = 0.0
for pose in [q for st in g["steps"] for q in st["poses"]]:
    for key, st in pose["parts"].items():
        if st.get("custom"):
            continue
        tree = gp[key]["tree"]
        mats = {str(tree["root"]): M(st["place"])}

        def ofg(i):
            if i not in mats:
                row = tree["rows"][i]
                mats[i] = mul(ofg(str(row["parent"])), hinge(row["hinge"][0], row["hinge"][1], st["turns"][i]))
            return mats[i]
        for pan in gp[key]["panels"]:
            gworst = max(gworst, max(math.dist(ap(ofg(str(pan["id"])), q), ap(M(st["panels"][str(pan["id"])]), q)) for q in pan["poly"]))
assert gworst < 0.01, gworst


def box(pose, key):
    pts = [ap(M(pose["parts"][key]["panels"][str(pn["id"])]), q) for pn in gp[key]["panels"] for q in pn["poly"]]
    return [min(q[k] for q in pts) for k in range(3)], [max(q[k] for q in pts) for k in range(3)]


rest, opened = g["steps"][15]["poses"][-1], g["steps"][16]["poses"][-1]
A, a, Ht, s_up, Lp = v14["tube_side"], v14["pusher_side"], v14["tube_height"], v14["push_amount"], v14["pusher_height"]
(t0, t1), (p0, p1) = box(rest, "tube"), box(rest, "pusher")
assert abs((t1[0] - t0[0]) - A) < TOL and abs((p1[0] - p0[0]) - a) < TOL and abs((p0[0] - t0[0]) - (A - a) / 2) < TOL  # 内筒は外筒の真ん中
mouth, bottom = t0[1], t1[1]
assert abs((bottom - mouth) - Ht) < TOL
base_top = box(rest, "base")[0][1]
assert abs((bottom - base_top) - (Ht - s_up)) < TOL, (bottom - base_top)  # 台の上の面は外筒の底から 70mm
assert box(rest, "fan")[0][1] > mouth + 2 - TOL and box(rest, "figure")[0][1] > mouth + 2 - TOL  # 扇と像は口の下（2mm 以上）
assert abs(box(opened, "base")[0][1] - mouth) < TOL  # 押し上げると台の上の面が口の高さ
fan_lo, fan_hi = box(opened, "fan")
R = v14["fold_height"]
assert opened["parts"]["fan"].get("custom") and abs((fan_hi[0] - fan_lo[0]) / 2 - R) < 0.5 and abs((mouth - fan_lo[1]) - R) < 0.5, (fan_lo, fan_hi)
ch = opened["rods"]["chopstick"]
assert abs((ch["to"][1] - bottom) - 77.0) < 0.01, ch["to"][1] - bottom  # fold3d.check_rise と同じ 77mm
norm_of = lambda key, i: normal(M(rest["parts"][key]["panels"][str(i)]))
cen = (0.0, (mouth + bottom) / 2, 0.0)
for pn in gp["tube"]["panels"][:4]:  # 外筒の 4 面は刷った面が外
    c = Polygon(pn["poly"]).centroid
    w = ap(M(rest["parts"]["tube"]["panels"][str(pn["id"])]), (c.x, c.y))
    assert (w[0] - cen[0]) * norm_of("tube", pn["id"])[0] + (w[2] - cen[2]) * norm_of("tube", pn["id"])[2] > 0, pn["id"]
for pn in gp["pusher"]["panels"][:4]:  # 内筒の 4 面は刷った面が内
    c = Polygon(pn["poly"]).centroid
    w = ap(M(rest["parts"]["pusher"]["panels"][str(pn["id"])]), (c.x, c.y))
    assert w[0] * norm_of("pusher", pn["id"])[0] + w[2] * norm_of("pusher", pn["id"])[2] < 0, pn["id"]
assert norm_of("base", 1)[1] < -0.999 and norm_of("figure", 0)[2] > 0.999 and norm_of("figure", 1)[2] < -0.999
assert g["structure"]["inside"]["pusher"] == "tube" and g["structure"]["cutaway"] == {"tube": ["0"], "pusher": ["2"]}
fan = gp["fan"]
nf, Rf = len(fan["panels"]), max(x for x, _ in fan["outline"])
wf = max(y for _, y in fan["outline"]) / nf
s17, s18 = g["steps"][16]["poses"], g["steps"][17]["poses"]
fp = lambda pose, k: M(pose["parts"]["fan"]["panels"][str(k)])
assert not s17[0]["parts"]["fan"].get("custom") and all(q["parts"]["fan"].get("custom") for q in s17[1:] + s18[:-1])
assert max(math.dist(ap(fp(s18[-2], k), q), ap(fp(s17[0], k), q)) for k in range(nf) for q in fan["panels"][k]["poly"]) < TOL  # 畳み終わり = 束
first_open = max(math.dist(ap(fp(s17[1], k), q), ap(fp(s17[0], k), q)) for k in range(nf) for q in fan["panels"][k]["poly"])
assert 0 < first_open < 0.25 * Rf * math.radians(180), first_open  # 開き始めは束から少しだけ動く（飛ばない）
opened_f = s17[-1]
assert max(math.dist(ap(fp(opened_f, k), (Rf, (k + 1) * wf)), ap(fp(opened_f, k + 1), (Rf, (k + 1) * wf))) for k in range(nf - 1)) < 0.05
assert min(fp(opened_f, k)[2][2] for k in range(nf)) > 0.999  # 開き切ると刷った面は見る人の方
piv = ap(fp(opened_f, 0), (0.0, wf / 2))
assert max(abs(math.dist(ap(fp(q, k), (Rf, k * wf + wf / 2)), piv) - Rf) for q in s17[1:] for k in range(nf)) < TOL  # 上の端の真ん中は弧の上

# 9. 動く物: 消えた棒・出た部品
from omochae.assembly3d import Scene  # noqa: E402
from omochae.compose import compose as _compose  # noqa: E402
from omochae.__main__ import load_source as _ls  # noqa: E402

_, lay, _ = _compose("pivot_counterweight", v6, _ls(pc.SOURCE))
sc = Scene(lay)
states = {k: ({}, sc.on_paper(k)) for k in sc.parts}
sc.pose(states, rods={"skewer": {"from": [0, 0, 0], "to": [0, 0, 1]}})
gone = sc.pose(states)
assert gone["moving"] == ["skewer"] and gone["act"] == "move", (gone["moving"], gone["act"])
hid = sc.pose(states, hidden=("tail",))
shown = sc.pose(states)
assert shown["moving"] == ["tail"] and shown["act"] == "move" and hid["moving"] == ["tail"], (shown["moving"], hid["moving"])
print(f"ok 作り方の 3D の JSON（虎 v6・{len(data['steps'])} 段・形のずれ {worst:.1e}mm／御来迎 v14・{len(g['steps'])} 段・形のずれ {gworst:.1e}mm）")
