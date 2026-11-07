"""虎の 5 重りの腕の札（制作者の決定 2026-11-06「部品の名前は案3: 型紙を「5 重りの腕」にそろえる。」）。

腕は幅 8mm で、「5 重りの腕」は 1 行に入らない。腕を広げると前の壁に当たるので幅は変えず、「5 重」の下に「り」「の」「腕」を
「重」の列にそろえて縦に並べる（pivot_counterweight._drop_label）。次を見る:
1. 札の行送りの値は、描く所（compose.LINE）と同じ（値を写しているので、違うと刷る字と置き場の計算がずれる）。
2. 既定（粘土は軸の 28mm 下）と v5・v6 の見本（20mm 下）: 札は「5 重りの腕」で 4 行。どの行も腕の枠の内で、軸の穴の下から
   粘土の高さの点の線の上まで（下の穴の半径と 1mm の空き）に入り、行どうしが重ならず、下の 3 字は「重」の列にそろう。型紙の検査も通る。
3. 4 行が入らない寸法（粘土が軸に近い・下の穴が無い）は、前と同じ「5 腕」の 1 行。境は粘土が軸の約 17.2mm 下。
   「5 腕」の 1 行は、下の穴と点の線に重ならない所に置く（粘土が軸に近いと、その下へ）。
4. 用意する物の文は、どの寸法でも「5 重りの腕」と呼ぶ（「5 腕」の字は刷らない）。
"""
import json
import pathlib

from omochae.__main__ import load_source
from omochae.compose import LABEL_SIZE, LINE, compose
from omochae.templates import pivot_counterweight as pc
from omochae.textfit import text_width

ROOT = pathlib.Path(__file__).resolve().parents[1]
neck = dict(pc.DEFAULTS, mount="neck")
examples = {n: dict(pc.DEFAULTS, **json.loads((ROOT / f"examples/{n}.json").read_text(encoding="utf-8"))["params"]) for n in ("tora_v5", "tora_v6")}
drop = lambda q: next(x for x in pc.parts(q) if x.key == "drop")

# 1. 写した値は描く所と同じ
assert pc.LABEL_LINE == LINE and pc.LABEL_SIZE == LABEL_SIZE, (pc.LABEL_LINE, LINE)

# 2. 縦に並べる札
for name, q in (("既定", neck), ("v5", examples["tora_v5"]), ("v6", examples["tora_v6"])):
    d = drop(q)
    assert d.label == "5 重りの腕" and [t for t, _, _ in d.label_lines] == ["5 重", "り", "の", "腕"], (name, d.label, d.label_lines)
    h = LABEL_SIZE * LINE
    boxes = [(x, y, x + text_width(t, LABEL_SIZE), y + h) for t, x, y in d.label_lines]
    wy = 4 + q["weight_below_axle"]
    xs = [x for x, _ in d.outline]
    length = max(y for _, y in d.outline)
    for x0, y0, x1, y1 in boxes:
        assert 0 <= x0 and x1 <= max(xs) and 0 <= y0 and y1 <= length, (name, (x0, y0, x1, y1))  # 腕の枠の内
        assert y0 >= 4 + 1.0 and y1 <= wy - (pc.THREAD_R + 1.0), (name, y0, y1, wy)  # 軸の穴の下、粘土の線の上
    assert all(b[1] >= a[3] - 1e-9 for a, b in zip(boxes, boxes[1:])), (name, boxes)  # 行どうしが重ならない
    col = boxes[0][0] + text_width("5 ", LABEL_SIZE)
    assert all(abs(b[0] - col) < 1e-9 for b in boxes[1:]), (name, boxes)  # 下の 3 字は「重」の列
    marks = [a for a in d.art if a["kind"] == "mark" and a.get("mark") == "weight"]
    assert marks and all(y == wy for a in marks for _, y in a["pts"]), (name, marks)
    _, layout, fails = compose("pivot_counterweight", q, load_source(pc.SOURCE))
    assert not fails, (name, [f.line() for f in fails])
    placed = next(x for x in layout["parts"] if x.key == "drop")  # 紙の上に置いた腕（pc.parts の腕は置く前で x・y が 0）
    drawn = sorted((t.text, round(t.x - placed.x, 6), round(t.y - placed.y, 6)) for t in layout["texts"] if t.owner == "drop")
    assert drawn == sorted((t, round(x, 6), round(y, 6)) for t, x, y in d.label_lines), (name, drawn)  # 刷る札は 4 行のまま

# 3. 入らない寸法は「5 腕」の 1 行。境は約 17.2mm
for wb, want in ((17.3, "5 重りの腕"), (17.1, "5 腕"), (10, "5 腕"), (pc.LOWER_HOLE_MIN - 0.5, "5 腕")):
    d = drop(dict(neck, weight_below_axle=wb))
    assert d.label == want and len(d.label_lines) == (4 if want == "5 重りの腕" else 1), (wb, d.label, d.label_lines)
    if want == "5 腕":
        assert [t for t, _, _ in d.label_lines] == ["5 腕"], d.label_lines
# 「5 腕」の 1 行は、下の穴と点の線（穴の半径と 1mm の空きの帯）に重ならず、軸の穴の下で腕の枠の内（見直しの指摘: 前は所が
# 決まっていて、粘土が軸の約 9mm より上だと重なった）。下の穴がある浅い寸法を 0.07mm ずつ全部見る
h = LABEL_SIZE * LINE
for i in range(400):
    wb = round(pc.LOWER_HOLE_MIN + i * 0.07, 3)
    if wb >= 17.2:
        break
    d = drop(dict(neck, weight_below_axle=wb))
    (_, _, y), = d.label_lines
    wy, band = 4 + wb, pc.THREAD_R + 1.0
    assert y + h <= wy - band + 1e-6 or y >= wy + band - 1e-6, (wb, y)
    assert y >= 4 + 1.0 and y + h <= max(yy for _, yy in d.outline), (wb, y)
fallback = dict(neck, weight_below_axle=12)
assert pc.check_physics(fallback) == [], [f.line() for f in pc.check_physics(fallback)]
_, layout, fails = compose("pivot_counterweight", fallback, load_source(pc.SOURCE))
assert not fails and [t.text for t in layout["texts"] if t.owner == "drop"] == ["5 腕"], [f.line() for f in fails]
# 軽い粘土で軸に近い寸法（見直しの指摘の範囲）も、型紙の検査を通り、札は下の穴の下に来る
shallow = dict(neck, weight_g=0.9, weight_below_axle=7)  # 0.5g だと静かな時に傾きすぎる（F5.pivot）ので、通る軽さで
assert pc.check_physics(shallow) == [], [f.line() for f in pc.check_physics(shallow)]
_, layout, fails = compose("pivot_counterweight", shallow, load_source(pc.SOURCE))
assert not fails, [f.line() for f in fails]
(_, _, y), = drop(shallow).label_lines
assert y >= 4 + 7 + pc.THREAD_R + 1.0 - 1e-9, y

# 4. 用意する物の文は、どの寸法でも「5 重りの腕」
for q in (neck, examples["tora_v6"], fallback, dict(neck, weight_below_axle=pc.LOWER_HOLE_MIN - 0.5)):
    text = "".join(pc.materials(q))
    assert "5 重りの腕" in text and "5 腕" not in text, text
print("ok 虎の 5 重りの腕の札（縦に 4 行・入らない寸法は 5 腕・用意する物の名）")
