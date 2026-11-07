"""御来迎の今の組 goraigo-v14 の作り方の 3D（型紙エンジンの JSON を data/kumitate/goraigo-v14.json に写した物。決定 2026-11-07）。

エンジンの試験（作った形のずれ・扇の半円・割り箸の長さほか）と別の目で、サイトの側から次を見る:
1. 写した JSON: 形の名・出所の commit・寸法がたたき台の紙と同じ・部品の形がサイトの紙と同じ・紙の上の置き場が同じ・机の面の行列
2. 段と文: 手順の文 18 と 1 対 1 で、最後にできあがりの動き。折りで表せる形では、サイトが place と turns から組んだ面の行列が、
   JSON の面の行列と同じ（扇が開く所と畳む所は、折りで表せない形なので面の行列だけで描く）
3. 組んだ形（段 16 の終わり・内筒を外筒に入れて静かな時）: 外筒の色の面が外・外筒の糊代が相手の面に寝る・内筒と扇が外筒の中・
   割り箸が外筒の下へ出る
4. 押し上げて扇が開く所（段 17）と畳む所（段 18）: 押し上げると扇が外筒の口の上に出る・開き切ると扇の幅が扇の高さの 2 倍（半円）・
   口の縁より下にある扇の所は外筒の内に収まる（口の縁に当たらない）・畳み終わりは開き始めの畳んだ束と同じ形（飛ばない）
5. サイトが決める見せ方と頁: 段 1 の定規は刷った物差しの所へ・はさみは紙の上の部品を 1 つずつ一周・机の面の層・止まった形の口（still）・
   作業の頁の口（scene）・分解して見せる形（split）・扇が開いて畳む間も頁が扇を描く（x）
6. 崩す: 部品の外形が紙と違う JSON は使わない
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
from web import kumitate

G = "NDL-1187053-R0000005-L"
FAN = TEMPLATES["slider_fan"]
p = {**FAN.DEFAULTS, **(hypotheses.sheet_of(G).get("params") or {})}
words = instructions.steps(p, "slider_fan")
doc = assembly_json.load("goraigo-v14")
apply, sub, dot, normal_of = assembly.apply, assembly._sub, assembly._dot, assembly.normal_of

# 1. 写した JSON
assert FAN.SHEET_SET == "goraigo-v14" and doc["format"] == assembly_json.FORMAT and doc["toy"] == "goraigo-v14"
assert re.fullmatch(r"[0-9a-f]{7,40}", doc["engine"]["commit"]) and "examples/goraigo_v14.json" in doc["engine"]["command"]
assert all(assembly._same(p.get(k), v) for k, v in doc["params"].items()), {k: (p.get(k), v) for k, v in doc["params"].items()}
bench = assembly.assemble(G)
assert isinstance(bench, Shown) and bench.failures == [], [f.line() for f in bench.failures]
parts = bench.paper["parts"]
assert assembly_json.part_gaps(doc, parts) == [], assembly_json.part_gaps(doc, parts)
at = doc["paper"]["at"]  # エンジンは小数 4 桁に丸めて書く
assert {q.key for q in parts} == set(at) and all(math.dist((q.x, q.y), at[q.key]) < 1e-3 for q in parts), at
page = bench.paper["page"]
assert [doc["paper"]["w"], doc["paper"]["h"]] == [page.w, page.h]
table = bench.table
want = assembly.mul(rows_of(doc["paper"]["place"]), assembly.translate(page.w / 2, page.h / 2))
assert max(abs(a - b) for a, b in zip(assembly_json.cols_of(table), assembly_json.cols_of(want))) < 1e-6
flat = assembly._invert_rigid(table)
first = bench.frames[0]["poses"][0]["panels"]
assert all(abs(apply(flat, apply(m, q))[2]) < 1e-6 for pid, m in first.items() if m is not None
           for q in bench.sheets[pid.split(":")[0]].panels[int(pid.split(":")[1])].exterior.coords), "段 1 の部品が机の面に無い"

# 2. 段と文。折りで表せる形では、サイトが組んだ面の行列と JSON の面の行列が同じ
assert [f["text"] for f in bench.frames] == words + [""] and len(words) == 18
custom = 0
for st in doc["steps"] + [doc["finale"]]:
    for got in st["poses"]:
        for key, mine in got["parts"].items():
            if mine.get("custom"):
                custom += 1
                continue
            plate = bench.sheets[key]
            built = assembly_json._place_of(plate, {k: v for k, v in mine.items() if k != "panels"}, assembly_json._turns(plate, mine))
            for i, m in mine["panels"].items():
                gap = max(abs(a - b) for a, b in zip(assembly_json.cols_of(built[int(i)]), m))
                assert gap < 1e-3, (st.get("n"), key, i, gap)
assert custom >= 20, custom  # 開く所と畳む所の 10 枚ずつ（と、できあがりの動き）


def mats(got):
    return {key: {int(i): rows_of(m) for i, m in mine["panels"].items()} for key, mine in got["parts"].items()}


def pts(M, key):
    return [apply(m, q) for i, m in M[key].items() for q in bench.sheets[key].panels[i].exterior.coords]


def box(M, key):
    allp = pts(M, key)
    return [min(q[k] for q in allp) for k in range(3)], [max(q[k] for q in allp) for k in range(3)]


# 3. 組んだ形（段 16 の終わり。内筒を外筒の下から入れて、静かな時）
rest = doc["steps"][15]["poses"][-1]
M = mats(rest)
tube = bench.sheets["tube"]
glue = assembly_json._glue_panels(tube)
walls = [i for i in M["tube"] if i not in glue]
lo, hi = box(M, "tube")
mid = tuple((a + b) / 2 for a, b in zip(lo, hi))
assert len(glue) == 1 and len(walls) == 4
assert all(dot(sub(apply(M["tube"][i], tube.panels[i].centroid.coords[0]), mid), normal_of(M["tube"][i])) > 0 for i in walls), "外筒の色の面が外を向かない"
(g,) = glue
inv = {i: assembly._invert_rigid(M["tube"][i]) for i in walls}
on = [i for i in walls if all(abs(apply(inv[i], q)[2]) <= 0.6 for q in [apply(M["tube"][g], c) for c in tube.panels[g].exterior.coords])]
assert len(on) == 1, "外筒の糊代が相手の面に寝ない"
for key in ("pusher", "fan"):
    l2, h2 = box(M, key)
    assert all(lo[k] - 1e-6 <= l2[k] and h2[k] <= hi[k] + 1e-6 for k in (0, 2)) and lo[1] - 1e-6 <= l2[1], (key, l2, h2, lo, hi)
rim, bottom = lo[1], hi[1]  # y は下が正。外筒の口（上の端）と下の端

# 4. 押し上げて扇が開く所と畳む所
up = doc["steps"][16]["poses"][0]  # 押し上げた形（まだ開く前）
U = mats(up)
fan_lo, fan_hi = box(U, "fan")
height = fan_hi[1] - fan_lo[1]
assert fan_hi[1] <= rim + 1e-6, "押し上げても扇が口の上に出ない"
rod = up["rods"]["chopstick"]
assert max(rod["from"][1], rod["to"][1]) > bottom + 10, "割り箸が外筒の下へ出ない"
opened = [got for got in doc["steps"][16]["poses"] if got["parts"]["fan"].get("custom")]
closing = [got for got in doc["steps"][17]["poses"] if got["parts"]["fan"].get("custom")]
assert len(opened) == len(closing) == 10, (len(opened), len(closing))
wide = mats(opened[-1])
w_lo, w_hi = box(wide, "fan")
assert abs((w_hi[0] - w_lo[0]) - 2 * height) < 0.5, (w_hi[0] - w_lo[0], height)  # 開き切ると半円
for got in opened + closing:
    F, T_ = mats(got), mats(got)
    t_lo, t_hi = box(T_, "tube")
    below = [q for q in pts(F, "fan") if q[1] > t_lo[1] + 1e-6]
    assert all(t_lo[0] - 1e-6 <= q[0] <= t_hi[0] + 1e-6 and t_lo[2] - 1e-6 <= q[2] <= t_hi[2] + 1e-6 for q in below), "口の縁より下の扇が外筒の外に出る"
start, end = mats(up)["fan"], mats(closing[-1])["fan"]
assert max(abs(a - b) for i in start for a, b in zip(assembly_json.cols_of(start[i]), assembly_json.cols_of(end[i]))) < 1e-3, "畳み終わりが開き始めの束と違う（飛ぶ）"

# 5. サイトが決める見せ方と頁
ruler = [q["ruler"] for q in bench.frames[0]["poses"] if q.get("ruler")]
rx0, ry0 = bench.paper["ruler"]
assert len(ruler) == 2 and math.dist(ruler[-1], (rx0 - page.w / 2 - assembly.RULER_ZERO, ry0 + 3.2 - page.h / 2)) < 1e-6
cuts = [q for q in bench.frames[1]["poses"] if q.get("cut")]
assert len(cuts) == len(parts) and all(q["paper"] for q in cuts)
# 扇が開く所と畳む所（折りで表せない形）は、頁へ渡す形の x に面の行列を持たせる（置き場と角の s を持たないので、x が無いと頁が扇を消す）。
# 頁の JS は x の面を補って置き、見える形にする
pages = kumitate.frames_of(bench)
for n in (17, 18):
    moving = [q for q in pages[n - 1]["q"] if q.get("x")]
    assert len(moving) >= 10 and all(len([k for k in q["x"] if k.startswith("fan:")]) == len(bench.sheets["fan"].panels) for q in moving), n
assert not any(q.get("x") for f in pages[:16] for q in f["q"]), "折りで表せる段に x がある"
assert "B.x&&B.x[o.id]" in kumitate.SCRIPT and "if(B.x){" in kumitate.SCRIPT
html = kumitate._block_html(G, kumitate._key(G))
assert html.count('class="rt-table"') == 2 and html.count("window.kumitateSplit=") == 1
still = kumitate.still(G)
assert "<script" not in still and still.count('<svg style="transform:matrix3d(') > 0 and 'rt-rod rt-axle" style="opacity:1' in still
scene = kumitate.scene(G)
assert len(scene["frames"]) == 19 and scene["split"] and scene["split"]["cut"] and scene["split"]["inside"]["pusher"] == "tube"

# 6. 崩す: 部品の外形が紙と違う JSON は使わない（違う紙の立体を見せない）
keep = assembly_json.DIR
try:
    assembly_json.DIR = pathlib.Path(tempfile.mkdtemp())
    bad = copy.deepcopy(doc)
    next(jp for jp in bad["parts"] if jp["key"] == "fan")["outline"][0][0] += 1
    assembly_json.path_of("goraigo-v14").write_text(json.dumps(bad, ensure_ascii=False), encoding="utf-8")
    assert assembly.assemble(G) is None
finally:
    assembly_json.DIR = keep
print("ok 御来迎 v14 の作り方の 3D（エンジンの JSON）。写しの照らし・段と文・組んだ形・開いて畳む所・見せ方と頁・崩し")
