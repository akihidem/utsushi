"""組み立てを立体で見る頁（#331）。本人の感想「紙を実際に山折り・谷折りしているように」「実際の手順に沿って、見え方や動きを再現する」。

手順ごとの途中の形が紙の動きのとおりに並ぶ事、折り線の角から作った形と組み立ての形が同じ事、頁が外の部品を読まない事を見る。
"""
import json
import math
import os
import re
import tempfile

os.environ.setdefault("OMOCHAE_DATA", tempfile.mkdtemp())

from omochae import assembly, hypotheses, instructions
from omochae.compose import TEMPLATES
from omochae.templates import slider_fan
from web import kumitate

G = "NDL-1187053-R0000005-L"
P = {**slider_fan.DEFAULTS, **hypotheses.sheet_of(G).get("params", {})}
bench = assembly.assemble(G)
frames = bench.frames
words = instructions.steps(P, "slider_fan")


def step(n):
    return frames[n - 1]["poses"]


# 折り線の角から作った形が、どの途中の形でも組み立ての形と同じ（頁は同じ計算で途中を描く）
for frame in frames[:-1]:
    for pose in frame["poses"]:
        for key, st in pose["state"].items():
            sheet = bench.sheets[key]
            made = {sheet.root: st["place"]}

            def of(i):
                if i not in made:
                    point, axis = sheet.hinge(i)
                    made[i] = assembly.mul(of(sheet.tree[i][0]), assembly.rotate_axis(point, axis, st["turns"][i]))
                return made[i]

            for i in range(len(sheet.panels)):
                m = of(i)
                if st["nudge"].get(i):
                    m = assembly.mul(m, assembly.translate(0, 0, st["nudge"][i]))
                got = pose["panels"][f"{key}:{i}"]
                assert all(abs(m[r][c] - got[r][c]) < 1e-6 for r in range(4) for c in range(4)), (frame["step"], key, i)

# 折り線でつながった面は、どの途中の形でも離れない
for frame in frames[:-1]:
    for pose in frame["poses"]:
        for key, sheet in bench.sheets.items():
            for child, (parent, k) in sheet.tree.items():
                a, b = pose["panels"][f"{key}:{child}"], pose["panels"][f"{key}:{parent}"]
                if a is None:
                    continue
                for point in sheet.lines[k][0]:
                    assert math.dist(assembly.apply(a, point), assembly.apply(b, point)) < 0.7, (frame["step"], key, child)

# 手順 1: 刷った紙が机にあり、定規が外から刷った物差しに来る
rx, ry = bench.paper["ruler"]
page = bench.paper["page"]
first, rest = step(1)
assert first["paper"] and rest["paper"] and first["ruler"][0] > page.w / 2 - 1
assert abs(rest["ruler"][0] + assembly.RULER_ZERO - (rx - page.w / 2)) < 1e-6, "定規の 0 が刷った物差しの 0 に合っていない"
# 部品は刷った紙の上の位置から始まる
tube_part = next(q for q in bench.paper["parts"] if q.key == "tube")
assert abs(first["state"]["tube"]["place"][0][3] - (tube_part.x - page.w / 2)) < 1e-6

# 手順 2: 外筒だけを切る。はさみは切る線を一周し、切った後に紙を離れる。折らない
two = step(2)
cuts = [q for q in two if q.get("cut")]
assert len(cuts) == 1 and cuts[0]["cut"][0] == cuts[0]["cut"][-1], "はさみが一周していない"
assert len(cuts[0]["cut"]) == len(tube_part.outline) + 1
assert two[0]["scrap"] and not two[-1]["scrap"], "溝の切り落とす所が残っている"
assert not two[-1]["paper"] and set(two[-1]["state"]) == {"tube"}
assert not any(two[-1]["state"]["tube"]["turns"].values()), "切っただけで折れている"

# 手順 3: 平らな所から折る
three = step(3)
assert not any(three[0]["state"]["tube"]["turns"].values()) and all(three[-1]["state"]["tube"]["turns"].values())

# 手順 4: 残りの 4 部品を 1 つずつ切り、穴を竹串の先であける
four = step(4)
cut_parts = [q for q in four if q.get("cut")]
assert len(cut_parts) == 4
assert sum("poke" in q["extras"] for q in four) == 3 and "poke" not in four[-1]["extras"]

# 手順 6: 竹串は外から穴を通って入る
six = step(6)
assert six[0]["extras"]["axle"][0][0] > six[-1]["extras"]["axle"][0][0], "竹串が外から入っていない"

# 手順 7: 台は内筒の上で平らなまま来て、糊代を折ってから下りる
seven = step(7)
assert not any(seven[0]["state"]["base"]["turns"].values()) and all(seven[1]["state"]["base"]["turns"].values())
assert seven[1]["state"]["base"]["place"][1][3] < seven[-1]["state"]["base"]["place"][1][3], "台が上から下りていない"

# 手順 8: 平らな帯を、端から順に畳む。順は片方の端から真ん中へ、次に反対の端から
eight = step(8)
assert not any(eight[0]["state"]["fan"]["turns"].values())
order = next(q for q in eight if q.get("order"))["order"]["fan"]
fan = bench.sheets["fan"]
seq = sorted(order, key=order.get)
ys = [fan.panels[i].bounds[1] for i in seq]
assert len(seq) == P["fold_count"] - 1 and ys[0] == 0 and ys[:P["fold_count"] // 2] == sorted(ys[:P["fold_count"] // 2]), ys[:4]

# 手順 8 の終わり: 真ん中の板は正面を向き、ほかの板が前後に重なる。厚みは紙の厚さの数のとおり
closed_fan = eight[-1]["panels"]
mid = fan.at(20, (P["fold_count"] // 2 + 0.5) * P["fold_width"])
assert assembly.normal_of(closed_fan[f"fan:{mid}"])[2] > 0.999, "真ん中の板が正面を向いていない"
pts = [assembly.apply(closed_fan[f"fan:{i}"], p) for i, s in enumerate(fan.panels) if s.bounds[2] > 0 for p in s.exterior.coords if p[0] >= 0]
deep = max(p[2] for p in pts) - min(p[2] for p in pts)
assert deep < P["paper_thickness"] * P["fold_count"] + 1, deep

nine = step(9)
assert "row" not in nine[0]["extras"] and "thread" not in nine[0]["extras"], "糸が先に通っている"
assert math.dist(*nine[1]["extras"]["row"][:2]) < 1 and math.dist(*nine[2]["extras"]["row"][:2]) > 2, "糸が穴の列を通っていない"
assert math.dist(*nine[3]["extras"]["thread"][:2]) < 1 and math.dist(*nine[-1]["extras"]["thread"][:2]) > 8, "糸が像の穴へ行っていない"

# 手順 10・11: 足を折ってから、上から下ろす
ten = step(10)
assert ten[0]["state"]["fan"]["place"][1][3] < ten[-1]["state"]["fan"]["place"][1][3]
eleven = step(11)
assert eleven[0]["state"]["figure"]["place"][1][3] < eleven[-1]["state"]["figure"]["place"][1][3]

# 手順 12: 内筒は外筒の下から入り、竹串は溝の下の端から入る
twelve = step(12)
below, inside = twelve[0], twelve[-1]
assert below["state"]["pusher"]["place"][1][3] > inside["state"]["pusher"]["place"][1][3], "下から入っていない"
assert below["extras"]["axle"][0][1] > P["tube_height"] / 2, "竹串が溝の下の端より下から始まっていない"

# 台に貼った後の扇の向き（型紙のとおり）: 真ん中の板は正面を向き、足の糊代は台の印の中、像は扇の前
ten_end = step(10)[-1]["panels"]
assert assembly.normal_of(ten_end[f"fan:{mid}"])[2] > 0.999, "台に貼った後の真ん中の板が正面を向いていない"
tab = next(i for i, s in enumerate(fan.panels) if s.bounds[2] < 0)
base = bench.sheets["base"]
c = P["base_glue"] + P["base_side"] / 2
middle = bench.panel_at("base", c, c)
mark = base.part.art[0]["pts"]
seen = [assembly.apply(ten_end[f"fan:{tab}"], p) for p in fan.panels[tab].exterior.coords]
onto = [assembly.apply(ten_end[f"base:{middle}"], p) for p in mark]
assert min(p[0] for p in onto) - 0.1 <= min(p[0] for p in seen) and max(p[0] for p in seen) <= max(p[0] for p in onto) + 0.1, "足の糊代の幅が印に入っていない"
assert min(p[2] for p in onto) - 0.1 <= min(p[2] for p in seen) and max(p[2] for p in seen) <= max(p[2] for p in onto) + 0.1, "足の糊代の奥行きが印に入っていない"

# 手順 12 の次: 上へ動かして扇が開く（本人の追加 11-06）。途中の計算の始めは手順 12 の畳んだ形、終わりは開いた形
assert len(frames[-1]["poses"]) == 1 and "fan" not in frames[-1]["state"]
last_pose = frames[-1]["poses"][0]
o = last_pose["open"]
closed_12 = step(12)[-1]["panels"]
start_pose = assembly.fan_pose(o, 0.0)
for i in o["strips"]:
    c0 = [assembly.apply(start_pose[i], p) for p in fan.panels[i].exterior.coords]
    c1 = [assembly.apply(closed_12[f"fan:{i}"], p) for p in fan.panels[i].exterior.coords]
    gap = max(math.dist(a, b) for a, b in zip(c0, c1))
    assert gap < 0.2, (i, gap)
end_pose = assembly.fan_pose(o, 1.0)
for i in o["strips"]:
    assert end_pose[i] == last_pose["panels"][f"fan:{i}"], i
# 開いた扇は正面を向く: 真ん中の板は正面で、板の先は外筒の 1 面目に平行な面に広がる（奥行きより幅がずっと広い）
assert assembly.normal_of(end_pose[o["mid"]])[2] > 0.999
tips = [assembly.apply(end_pose[i], (P["fold_height"], fan.panels[i].centroid.y)) for i in o["strips"]]
assert max(p[0] for p in tips) - min(p[0] for p in tips) > 10 * (max(p[2] for p in tips) - min(p[2] for p in tips)), "扇が正面に開いていない"
face = bench.panel_at("tube", 4, 40)
assert assembly.normal_of(last_pose["panels"][f"tube:{face}"])[2] > 0.999, "1 面目が正面にない"
# 上がるほど広がり、途中で閉じない
spans = []
for r in range(0, 11):
    made = assembly.fan_pose(o, r / 10)
    tips = [assembly.apply(made[i], (P["fold_height"], fan.panels[i].centroid.y)) for i in o["strips"]]
    spans.append(max(p[0] for p in tips) - min(p[0] for p in tips))
assert spans == sorted(spans) and spans[-1] > 2 * P["fold_height"] * 0.9, spans
assert kumitate.page(G).count('id="rt-stage"') == 1

# 頁へ渡す形
data = kumitate.frames_of(bench)
assert [f["t"] for f in data[:-1]] == words and data[-1]["t"] == ""
assert "p" in data[-1]["q"][0] and all("p" not in q for f in data[:-1] for q in f["q"])
assert all(q.get("dur", 1) > 0 for f in data for q in f["q"])
for f in data:
    for q in f["q"]:
        for name, rod in q["r"].items():
            assert len(rod["s"]) == 3 and len(rod["e"]) == 3, name

# 頁: 開いただけで動かさない。外の部品を読まない。刷った紙と定規とはさみがある
html = kumitate.page(G)
body = re.sub(r'xmlns(:\w+)?="[^"]*"', "", html)
assert not re.search(r'https?://', body), re.search(r'https?://[^"\' )]*', body)
assert "<img" not in html and "fetch(" not in html and "import(" not in html
for mark in ('id="rt-paper"', 'id="rt-ruler"', 'id="rt-sci"', 'class="rt-scrap"', 'data-r="poke"', 'data-r="row"', 'data-r="thread"', 'data-r="axle"'):
    assert mark in html, mark
assert html.count('class="rt-p"') == 2 * sum(len(s.panels) for s in bench.sheets.values())
assert "words();rest(last(L));" in html, "開いた時はできあがりの形で止まっている"
assert "prefers-reduced-motion" in html, "動きを減らす設定を見ていない"
assert "openShape" in html and "B.open" in html, "扇が開く動きが無い"
# どこまで開くかは紙で確かめる物なので、頁の字で角度を言わない（本人の答え 11-06）
visible = re.sub(r"<script>.*?</script>|<style>.*?</style>", "", html, flags=re.S)
visible = re.sub(r"<[^>]+>", " ", visible)
assert not re.search(r"\d+\s*(°|度)", visible), re.search(r".{20}\d+\s*(°|度).{10}", visible)
# 刷った紙の字は型紙のとおり
assert "10cm の物差し" in html
# 紙の折り線の見え方: 色の境で折る部品は線を刷らない。台と内筒は破線がある
assert bench.sheets["tube"].part.hide_folds and not bench.sheets["base"].part.hide_folds
assert 'stroke-dasharray="2,1"' in html

# 組み立ての書き方が無い玩具には道を出さない
assert kumitate.available(G) and 'id="kumitate"' in kumitate.block(G)
assert not kumitate.available("NDL-1187053-R0000009-R") and kumitate.block("NDL-1187053-R0000009-R") == ""
assert not kumitate.available("無い玩具")

# 型紙の頁に初めから出る（本人の決定 11-06）。書き方が無い玩具の頁には出ない
from web import toy  # noqa: E402

made_page = toy.toy_page(G)
assert made_page.count('id="kumitate"') == 1 and made_page.count('id="rt-stage"') == 1
assert made_page.index('id="kumitate"') > made_page.index('id="kasetsu"'), "すぐ作る節の中に無い"
assert 'id="kumitate"' not in toy.toy_page("NDL-1187053-R0000009-R")

# 虎: 手順と段が 1 対 1。胴は箱に折れ、絵は外、頭は前の壁の外、軸は帯の穴を通る
T = "NDL-1187053-R0000014-R"
tora = assembly.assemble(T)
tora_p = {**TEMPLATES["pivot_counterweight"].DEFAULTS, **(hypotheses.sheet_of(T).get("params") or {})}
tora_words = instructions.steps(tora_p, "pivot_counterweight")
assert [f["text"] for f in tora.frames[:-1]] == tora_words and tora.frames[-1]["text"] == ""
assert kumitate.available(T) and 'id="rt-knife"' in kumitate.block(T)
for frame in tora.frames:
    for pose in frame["poses"]:
        for key, sheet in tora.sheets.items():
            for child, (parent, k) in sheet.tree.items():
                a, b = pose["panels"][f"{key}:{child}"], pose["panels"][f"{key}:{parent}"]
                if a is None:
                    continue
                for point in sheet.lines[k][0]:
                    assert math.dist(assembly.apply(a, point), assembly.apply(b, point)) < 0.7, (frame["step"], key, child)
found = [f.line() for f in tora.failures]
assert any("手順 4" in x and "糊代の根元 4 か所" in x for x in found), found
assert any("手順 4" in x and "絵のある面が箱の内側に入る" in x for x in found), found
assert len(found) == 2, found
done = tora.frames[-1]["panels"]
H_, W_, L_ = tora_p["body_height"], tora_p["body_width"], tora_p["body_length"]
pts = [assembly.apply(m, p) for pid, m in done.items() if pid.startswith("body:") for p in tora.sheets["body"].panels[int(pid.split(":")[1])].exterior.coords]
assert abs(max(p[0] for p in pts) - min(p[0] for p in pts) - L_) < 0.8 and abs(max(p[2] for p in pts) - min(p[2] for p in pts) - W_) < 0.8, "胴が箱になっていない"
assert abs(max(p[1] for p in pts) - min(p[1] for p in pts) - H_) < 0.8
head_pts = [assembly.apply(done["head:0"], p) for p in tora.sheets["head"].panels[0].exterior.coords]
assert max(p[0] for p in head_pts) < -L_ / 2, "頭が前の壁の外に出ていない"
# 前の壁の穴は、切るまで塞がっている
assert tora.frames[1]["poses"][-1]["plug"] and not tora.frames[2]["poses"][-1]["plug"]
# できあがりの頭は揺れて、元の位置で止まる
final = tora.frames[-1]["poses"]
assert len(final) >= 5 and final[0]["state"]["head"]["place"] == final[-1]["state"]["head"]["place"]
print("ok")
