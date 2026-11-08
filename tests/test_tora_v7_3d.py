"""虎の今の組 tora-v7 の作り方の 3D（型紙エンジンの JSON を data/kumitate/tora-v7.json に写した物。決定 2026-11-07。v6 は刷らずに飛ばした）。

エンジンの試験（作った形のずれ・刷った面が外ほか）と別の目で、サイトの側から次を見る:
1. 写した JSON: 形の名・出所の commit・寸法がたたき台の紙と同じ・部品の形がサイトの紙と同じ・紙の上の置き場が同じ・机の面の行列
2. 段と文: 手順の文 12 と 1 対 1 で、最後にできあがりの動き。サイトが place と turns から組んだ面の行列が、JSON の面の行列と同じ
3. できあがりの形: 胴の色の面が外・糊代が相手の面に寝る・首の帯が前の壁の丸い穴を通る・
   竹串が胴の 2 つの穴を通る・粘土の玉が胴の中・脚の色の面が外で上の糊代が胴の底を向く・両面の頭の顔が両側の外・尾が上の面から上へ立つ・
   揺れる間（できあがりの動きと ±10°）も、重りの腕と粘土の玉が前の壁に、帯と頭が丸い穴の縁に、0.5mm 以上の空きで当たらない・
   どの段の形でも部品が机の面より下へ出ない
4. サイトが決める見せ方: はさみは紙の上の部品を 1 つずつ一周・カッターは首の丸い穴を一周して切れ端が落ちる・重なる面のずらし
5. 頁: 机の面の層・丸い切れ端・5 重りの腕の札の 4 行・止まった形の口（still）と作業の頁の口（scene）・分解して見せる形（split）
6. 崩す: 丸い穴の置き場が紙と違う JSON は使わない
面は硬い板と見る（エンジンと同じ）。通っても、紙で組める保証ではない。
"""
import copy
import json
import math
import os
import pathlib
import re
import tempfile

os.environ.setdefault("OMOCHAE_DATA", tempfile.mkdtemp())

from shapely.geometry import Polygon

from omochae import assembly, assembly_json, hypotheses, instructions
from omochae.assembly_json import Shown, rows_of
from omochae.compose import TEMPLATES
from omochae.templates import pivot_counterweight
from web import kumitate

T = "NDL-1187053-R0000014-R"
TIGER = TEMPLATES["pivot_counterweight"]
p = {**TIGER.DEFAULTS, **hypotheses.sheet_of(T)["params"]}
words = instructions.steps(p, "pivot_counterweight")
doc = assembly_json.load("tora-v8")
apply, sub, dot, normal_of = assembly.apply, assembly._sub, assembly._dot, assembly.normal_of

# 1. 写した JSON
# 今の組は tora-v8（v7 と同じ部品で、重りの腕を指で押さえて鉛筆で印を付ける版・11-08）。JSON は v7 の物の組の名と寸法だけを替えた写し
assert TIGER.SHEET_SET == "tora-v8" and doc["format"] == assembly_json.FORMAT and doc["toy"] == "tora-v8"
assert re.fullmatch(r"[0-9a-f]{7,40}", doc["engine"]["commit"]) and "examples/tora_v7.json" in doc["engine"]["command"]
assert all(assembly._same(p.get(k), v) for k, v in doc["params"].items()), {k: (p.get(k), v) for k, v in doc["params"].items()}
bench = assembly.assemble(T)
assert isinstance(bench, Shown) and bench.failures == [], [f.line() for f in bench.failures]
parts = bench.paper["parts"]
assert assembly_json.part_gaps(doc, parts) == [], assembly_json.part_gaps(doc, parts)
at = doc["paper"]["at"]  # エンジンは小数 4 桁に丸めて書く
assert {q.key for q in parts} == set(at) and all(math.dist((q.x, q.y), at[q.key]) < 1e-3 for q in parts), at
page = bench.paper["page"]
assert [doc["paper"]["w"], doc["paper"]["h"]] == [page.w, page.h]
# 机の面の行列は、紙の座標の真ん中を 0 にした机の座標 → 世界。段 1 の部品の面は、どれも机の面の上（机の座標で高さ 0）にある
table = bench.table
assert max(abs(a - b) for a, b in zip(assembly_json.cols_of(table), assembly_json.cols_of(assembly.mul(rows_of(doc["paper"]["place"]), assembly.translate(page.w / 2, page.h / 2))))) < 1e-6
flat = assembly._invert_rigid(table)
first = bench.frames[0]["poses"][0]["panels"]
assert all(abs(apply(flat, apply(m, q))[2]) < 1e-6 for pid, m in first.items() if m is not None
           for q in bench.sheets[pid.split(":")[0]].panels[int(pid.split(":")[1])].exterior.coords), "段 1 の部品が机の面に無い"

# 2. 段と文。サイトが組んだ面の行列と JSON の面の行列が同じ（頁は place と turns から折る途中を描くので）
assert [f["text"] for f in bench.frames] == words + [""] and len(words) == 12
for st in doc["steps"] + [doc["finale"]]:
    for got in st["poses"]:
        for key, mine in got["parts"].items():
            plate = bench.sheets[key]
            built = assembly_json._place_of(plate, {k: v for k, v in mine.items() if k != "panels"}, assembly_json._turns(plate, mine))
            for i, m in mine["panels"].items():
                gap = max(abs(a - b) for a, b in zip(assembly_json.cols_of(built[int(i)]), m))
                assert gap < 1e-3, (st.get("n"), key, i, gap)

# 3. できあがりの形（最後の段の最後の形。貼って重なる面のずらしを入れない JSON の行列で見る）
end = doc["steps"][-1]["poses"][-1]
M = {key: {int(i): rows_of(m) for i, m in mine["panels"].items()} for key, mine in end["parts"].items()}


def pts(key, i, m=None):
    return [apply(m or M[key][i], q) for q in bench.sheets[key].panels[i].exterior.coords]


def middle(key):
    allp = [q for i in M[key] for q in pts(key, i)]
    return tuple((min(x[k] for x in allp) + max(x[k] for x in allp)) / 2 for k in range(3))


def glue_of(key):
    return assembly_json._glue_panels(bench.sheets[key])


def outward(key, panels):
    """刷った面が部品の真ん中から外を向かない面。"""
    c = middle(key)
    return [i for i in panels if dot(sub(apply(M[key][i], tuple(bench.sheets[key].panels[i].centroid.coords[0])), c), normal_of(M[key][i])) <= 1e-9]


def lies_on(key, i, others):
    """糊代の面 i が、どれかの面に寝る（面から 0.6mm 以内で、相手の面に 9 割以上重なる）。Returns 相手の面（部品, 番号）か None。"""
    for okey, j in others:
        if (okey, j) == (key, i):
            continue
        inv = assembly._invert_rigid(M[okey][j])
        local = [apply(inv, q) for q in pts(key, i)]
        if all(abs(z) <= 0.6 for _, _, z in local):
            flat_ = Polygon([(x, y) for x, y, _ in local]).buffer(0)
            if flat_.intersection(bench.sheets[okey].panels[j]).area >= 0.9 * flat_.area:
                return okey, j
    return None


body = bench.sheets["body"]
glue = glue_of("body")
assert len(glue) == 5 and outward("body", [i for i in M["body"] if i not in glue]) == []
for i in glue:
    assert lies_on("body", i, [("body", j) for j in M["body"] if j not in glue]), ("body", i)

# 首の帯と頭が、前の壁の丸い穴を縁に当たらずに通る。帯と頭の面が壁の面を横切る点が、どれも穴の内（静かな時と、揺れる間のどの形でも）
hx, hy, hr = body.part.round_cuts[0]
wall = next(i for i, s in enumerate(body.panels) if Polygon(s.exterior).contains(Polygon(assembly.round_ring(hx, hy, hr)).centroid))


# 竹串は、胴の 2 つの穴を通る（穴の真ん中から竹串の線まで、穴の半径の内）
rod = end["rods"]["skewer"]
s, e = rod["from"], rod["to"]
d = assembly._unit(sub(e, s))
holes = [apply(M["body"][next(i for i, sh in enumerate(body.panels) if sh.buffer(1e-3).contains(Polygon(assembly.round_ring(x, y, rr)).centroid))], (x, y)) for x, y, rr in body.part.holes]
for h in holes:
    v = sub(h, s)
    off = math.dist(h, tuple(a + b * dot(v, d) for a, b in zip(s, d)))
    assert off < 1.2, off

# 粘土の玉は胴の幅の内で、胴の底より上
lo = [min(q[k] for i in M["body"] for q in pts("body", i)) for k in range(3)]
hi = [max(q[k] for i in M["body"] for q in pts("body", i)) for k in range(3)]
ball, r = end["balls"]["clay"]["at"], doc["balls"]["clay"]["r"]
assert lo[2] + r <= ball[2] <= hi[2] - r and ball[1] + r < hi[1], (ball, lo, hi)

# 前の壁に当たらない（空きは床 FLOOR 以上）: 重りの腕と粘土の玉は壁の内に、首の帯は丸い穴の縁の内を通り、頭は穴の縁の内を通るか壁の外にある。
# 見る形は、できあがり・できあがりの動きのどの形・できあがりの形から竹串のまわりに ±10° を 0.5° ずつ回した形。
# v6 では、揺れると玉と腕が前の壁に当たった（エンジンの v7 の検品で見つけた。この試験の v6 の版は帯と頭が穴を通るかだけを見て、見落とした）
FLOOR = 0.5


def gaps(mats, at):
    """Returns (腕の空き, 玉の空き, 帯と頭が穴の縁から離れる最小, 頭が穴を通るか, 頭が壁の外にある離れの最小, 帯が壁を横切る数)。"""
    wm = mats["body"][wall]
    c, n = apply(wm, (hx, hy)), normal_of(wm)
    inward = lambda q: -dot(sub(q, c), n)
    arm = min(inward(q) for i, m in mats["drop"].items() for q in pts("drop", i, m))
    far, crossed = 0.0, {"strip": 0, "head": 0}
    for key in ("strip", "head"):
        for i, m in mats[key].items():
            q = pts(key, i, m)
            for a, b in zip(q, q[1:]):
                sa, sb = dot(sub(a, c), n), dot(sub(b, c), n)
                if sa * sb < 0:
                    x = tuple(u + (v - u) * sa / (sa - sb) for u, v in zip(a, b))
                    far, crossed[key] = max(far, math.dist(x, c)), crossed[key] + 1
    outside = min(-inward(q) for i, m in mats["head"].items() for q in pts("head", i, m))
    return arm, inward(at) - r, hr - far, crossed["head"] > 0, outside, crossed["strip"]


shapes = [("できあがり", M, ball)]
for k, got in enumerate(doc["finale"]["poses"]):
    shapes.append((f"できあがりの動き {k}", {key: {int(i): rows_of(m) for i, m in mine["panels"].items()} for key, mine in got["parts"].items()}, got["balls"]["clay"]["at"]))
for k in range(-20, 21):
    turn = assembly.rotate_axis(tuple(s), sub(e, s), k * 0.5)
    mats = {key: ({i: assembly.mul(turn, m) for i, m in ms.items()} if key in ("strip", "head", "drop") else ms) for key, ms in M.items()}
    shapes.append((f"{k * 0.5:+.1f}°", mats, apply(turn, ball)))
least = [math.inf] * 3
for name, mats, at in shapes:
    arm, gap, hole, through, outside, strip = gaps(mats, at)
    assert strip >= 2 and min(arm, gap, hole) >= FLOOR and (through or outside >= FLOOR), (name, arm, gap, hole, through, outside, strip)
    least = [min(a, b) for a, b in zip(least, (arm, gap, hole))]
assert len(shapes) == 1 + len(doc["finale"]["poses"]) + 41, len(shapes)

# 脚: 角筒の色の面が外。横の糊代は角筒の面に寝て、上の 2 つの糊代は刷った面が胴の底を向く（胴の底に貼れる）
floor = next(i for i, sh in enumerate(body.panels) if abs(dot(normal_of(M["body"][i]), (0, 1, 0)) - 1) < 1e-6)  # 刷った面が下（外）を向く底
up = tuple(-x for x in normal_of(M["body"][floor]))
for key in ("leg1", "leg2", "leg3", "leg4"):
    g = glue_of(key)
    tube = [i for i in M[key] if i not in g]
    assert len(g) == 3 and len(tube) == 4 and outward(key, tube) == [], key
    side = [i for i in g if lies_on(key, i, [(key, j) for j in tube])]
    tops = [i for i in g if i not in side]
    assert len(side) == 1 and len(tops) == 2 and all(dot(normal_of(M[key][i]), up) > 0.99 for i in tops), key
    assert all(lies_on(key, i, [("body", floor)]) for i in tops), ("上の糊代が胴の底に寝ない", key)

# 両面の頭: 2 枚の刷った面が逆を向き、どちらも口が前（胴から遠い側）にある。山折りで折った（顔が両側の外）
head = bench.sheets["head"]
(child, (parent, k)), = head.tree.items()
assert dot(normal_of(M["head"][child]), normal_of(M["head"][parent])) < -0.999
turn = float(end["parts"]["head"]["turns"][str(child)])
assert head.lines[k][1] == "mountain" and (head.turn(child, {k: 90.0}) > 0) == (turn > 0), "頭を山折りで折っていない"
# 尾: 先が上の面より上（胴の上の端より上）にある
tail = bench.sheets["tail"]
tip = min(q[1] for i in M["tail"] for q in pts("tail", i))
assert tip < lo[1] - 40, (tip, lo[1])

# 机の面より下へ出ない: どの段のどの形でも、部品の面の点が机の面（刷った紙を置いた面）より 0.5mm を超えて下へ出ない。
# 型紙エンジンの 3D 組み立て検品（#139）で直った所: 前の JSON は、手順 12 の初めの形で尾が机の下へ 16mm 出ていた（尾を貼る四角の上に替えた）
under = assembly._invert_rigid(table)
low = min((apply(under, apply(rows_of(m), q))[2], st.get("n"), key)
          for st in doc["steps"] + [doc["finale"]] for got in st["poses"] for key, mine in got["parts"].items()
          for i, m in mine["panels"].items() for q in bench.sheets[key].panels[int(i)].exterior.coords)
assert low[0] >= -0.5, ("机の面より下へ出る", low)

# 4. サイトが決める見せ方
cut2 = [q for q in bench.frames[1]["poses"] if q.get("cut")]
assert len(cut2) == len(parts) and all(q["paper"] for q in cut2)  # 紙の上の部品を 1 つずつ一周する
cut3 = [q for q in bench.frames[2]["poses"] if q.get("cut")]
assert len(cut3) == 1 and cut3[0].get("knife")
q = bench.paper["parts"][0]
center = (q.x + hx - page.w / 2, q.y + hy - page.h / 2)
assert all(abs(math.dist(x, center) - hr) < 1e-6 for x in cut3[0]["cut"]), "カッターが首の丸い穴を回らない"
assert all(q["plug"] for f in bench.frames[:2] for q in f["poses"]) and cut3[0]["plug"]
assert not any(q["plug"] for f in bench.frames[3:] for q in f["poses"]) and not bench.frames[2]["poses"][-1]["plug"]
last = bench.frames[-2]["poses"][-1]["state"]
assert last["head"]["nudge"] == {0: assembly_json.LIFT_MOUNTAIN, 1: assembly_json.LIFT_MOUNTAIN}
assert last["strip"]["nudge"] == {0: assembly_json.LIFT_VALLEY, 1: assembly_json.LIFT_VALLEY}
assert all(abs(v) == assembly_json.LIFT_GLUE for v in last["body"]["nudge"].values()) and set(last["body"]["nudge"]) == glue

# 5. 頁
html = kumitate._block_html(T, kumitate._key(T))
assert html.count('class="rt-table"') == 2 and html.count('<circle class="rt-plug"') == 2  # 紙と道具の層・丸い切れ端の表と裏
assert re.search(r'class="rt-plug" cx="[^"]+" cy="[^"]+" r="9.00" fill="#cc3326"', html), "切れ端の色が首の穴の赤い縁の色でない"
drop = re.findall(r'<svg class="rt-p" data-p="drop:0".*?</svg>', html, re.S)[0]
lines = [t for t, _, _ in bench.sheets["drop"].part.label_lines]
assert [t for t in re.findall(r">([^<>]+)</text>", drop)] == lines and "".join(lines).replace(" ", "") == "5重りの腕", lines
still = kumitate.still(T)
assert "<script" not in still and still.count('<svg style="transform:matrix3d(') == 2 * sum(len(s.panels) for s in bench.sheets.values())
assert 'rt-rod rt-axle" style="opacity:1' in still and f'aria-label="{kumitate.DONE}"' in still
assert 'class="rt-plug"' not in still, "切った後の止まった形に、丸い穴の切れ端が残る"
small = kumitate.still(T, 200, 240)
assert 'width:200px;height:240px' in small
scene = kumitate.scene(T)
assert set(scene) == {"frames", "trees", "scale", "table", "split", "panels", "paper"} and len(scene["frames"]) == 13 and scene["table"] == kumitate._css(table)
assert kumitate.scene("無い玩具") is None and kumitate.still("NDL-1187053-R0000009-R") == ""

# 5. 分解して見せる形（作業の頁の口 window.kumitateSplit）: できあがりと同じ形の書き方で、どの部品も持ち、
#    中に入る部品（帯・腕）と脚・尾・頭は、できあがりより胴の真ん中から離れる。内側を見る時に外す面は胴の面
split = kumitate.split_of(bench)
assert set(split) == {"X", "cut", "inside"} and set(split["X"]) >= {"p", "s", "r", "rx", "ry", "c", "z"}
assert set(split["X"]["s"]) == set(end["parts"]) | {"clay"} and split["inside"]["strip"] == "body"
assert split["cut"] and all(c.split(":")[0] in bench.sheets and int(c.split(":")[1]) < len(bench.sheets[c.split(":")[0]].panels) for c in split["cut"])
apart = {key: {int(i): rows_of(m) for i, m in mine["panels"].items()} for key, mine in doc["structure"]["exploded"]["parts"].items()}
core = middle("body")


def reach(mats, key):
    return max(math.dist(apply(m, q), core) for i, m in mats[key].items() for q in bench.sheets[key].panels[i].exterior.coords)


for key in ("strip", "drop", "head", "tail", "leg1"):
    assert reach(apart, key) > reach(M, key) + 5, key
assert html.count("window.kumitateSplit=") == 1 and kumitate.scene(T)["split"]["cut"] == split["cut"]

# 6. 崩す: 丸い穴の置き場が紙と違う JSON は使わない（違う紙の立体を見せない）
keep = assembly_json.DIR
try:
    assembly_json.DIR = pathlib.Path(tempfile.mkdtemp())
    bad = copy.deepcopy(doc)
    next(jp for jp in bad["parts"] if jp["key"] == "body")["round_cuts"][0][0] += 1
    assembly_json.path_of("tora-v8").write_text(json.dumps(bad, ensure_ascii=False), encoding="utf-8")
    assert assembly.assemble(T) is None
finally:
    assembly_json.DIR = keep
print("ok 虎 v7 の作り方の 3D（エンジンの JSON）。写しの照らし・段と文・できあがりの形・見せ方・頁・崩し")
