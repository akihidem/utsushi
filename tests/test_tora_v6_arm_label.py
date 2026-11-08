"""虎の 5 重りの腕の札（本人の決定 2026-11-06「部品の名前は案3: 型紙を「5 重りの腕」にそろえる。」。型紙エンジン #135 の試験の写し）。

腕は幅 8mm で、「5 重りの腕」は 1 行に入らない。腕を広げると前の壁に当たるので幅は変えず、「5 重」の下に「り」「の」「腕」を
「重」の列にそろえて縦に並べる（_tora_v6._drop_label）。サイトでは今の組 tora-v7 から。前の組 tora-v4 の紙も、本人の決定（2026-11-07
「(1): A、v4 の紙も「5 重りの腕」に替える。」）で同じ行ごとの札になった（#498 の pivot_counterweight._drop_label）。前の組 tora-v3 の紙は「5」のまま。
次を見る:
1. 札の行送りの値は、描く所（compose.LINE）と同じ（値を写しているので、違うと刷る字と置き場の計算がずれる）。
2. 既定（粘土は軸の 28mm 下）と v6 のたたき台（20mm 下）: 札は「5 重りの腕」で 4 行。どの行も腕の枠の内で、軸の穴の下から
   粘土の高さの点の線の上まで（下の穴の半径と 1mm の空き）に入り、行どうしが重ならず、下の 3 字は「重」の列にそろう。型紙の検査も通る。
3. 4 行が入らない寸法（粘土が軸に近い・下の穴が無い）は、前と同じ「5 腕」の 1 行。境は粘土が軸の約 17.2mm 下。
   「5 腕」の 1 行は、下の穴と点の線に重ならない所に置く（粘土が軸に近いと、その下へ）。
4. 用意する物の文は、どの寸法でも「5 重りの腕」と呼ぶ（「5 腕」の字は刷らない）。
5. 前の組 tora-v4 の札は「5 重りの腕」の 4 行で、用意する物の文も「5 重りの腕」と呼ぶ（#498 の作り）。凍結の組 tora-v3 の札は「5」の 1 行のまま。
"""
import json

from omochae import hypotheses
from omochae.compose import LABEL_SIZE, LINE, TEMPLATES, compose
from omochae.templates import _tora_v6 as pc
from omochae.textfit import text_width

TORA = "NDL-1187053-R0000014-R"
TIGER = TEMPLATES["pivot_counterweight"]
source = json.loads((hypotheses.ROOT / "data/sources" / f"{TORA}.json").read_text(encoding="utf-8"))
neck = dict(pc.DEFAULTS, mount="neck")
sheet = dict(pc.DEFAULTS, **hypotheses.sheet_of(TORA)["params"])
drop = lambda q: next(x for x in TIGER.parts(q) if x.key == "drop")
assert TIGER.SHEET_SET == "tora-v8"  # 今の組（v6 は刷らずに飛ばした。v8 は v7 と同じ部品でテープを使わない版）

# 1. 写した値は描く所と同じ
assert pc.LABEL_LINE == LINE and pc.LABEL_SIZE == LABEL_SIZE, (pc.LABEL_LINE, LINE)

# 2. 縦に並べる札
for name, q in (("既定", neck), ("v6 のたたき台", sheet)):
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
    _, layout, fails = compose("pivot_counterweight", q, source)
    assert not fails, (name, [f.line() for f in fails])
    placed = next(x for x in layout["parts"] if x.key == "drop")  # 紙の上に置いた腕（parts の腕は置く前で x・y が 0）
    drawn = sorted((t.text, round(t.x - placed.x, 6), round(t.y - placed.y, 6)) for t in layout["texts"] if t.owner == "drop")
    assert drawn == sorted((t, round(x, 6), round(y, 6)) for t, x, y in d.label_lines), (name, drawn)  # 刷る札は 4 行のまま

# 3. 入らない寸法は「5 腕」の 1 行。境は約 17.2mm
for wb, want in ((17.3, "5 重りの腕"), (17.1, "5 腕"), (10, "5 腕"), (pc.LOWER_HOLE_MIN - 0.5, "5 腕")):
    d = drop(dict(neck, weight_below_axle=wb))
    assert d.label == want and len(d.label_lines) == (4 if want == "5 重りの腕" else 1), (wb, d.label, d.label_lines)
    if want == "5 腕":
        assert [t for t, _, _ in d.label_lines] == ["5 腕"], d.label_lines
# 「5 腕」の 1 行は、下の穴と点の線（穴の半径と 1mm の空きの帯）に重ならず、軸の穴の下で腕の枠の内。下の穴がある浅い寸法を 0.07mm ずつ全部見る
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
assert TIGER.check_physics(fallback) == [], [f.line() for f in TIGER.check_physics(fallback)]
_, layout, fails = compose("pivot_counterweight", fallback, source)
assert not fails and [t.text for t in layout["texts"] if t.owner == "drop"] == ["5 腕"], [f.line() for f in fails]
# 軽い粘土で軸に近い寸法も、型紙の検査を通り、札は下の穴の下に来る
shallow = dict(neck, weight_g=0.9, weight_below_axle=7)  # 0.5g だと静かな時に傾きすぎる（F5.pivot）ので、通る軽さで
assert TIGER.check_physics(shallow) == [], [f.line() for f in TIGER.check_physics(shallow)]
_, layout, fails = compose("pivot_counterweight", shallow, source)
assert not fails, [f.line() for f in fails]
(_, _, y), = drop(shallow).label_lines
assert y >= 4 + 7 + pc.THREAD_R + 1.0 - 1e-9, y

# 4. 用意する物の文は、どの寸法でも「5 重りの腕」
for q in (neck, sheet, fallback, dict(neck, weight_below_axle=pc.LOWER_HOLE_MIN - 0.5)):
    text = "".join(TIGER.materials(q))
    assert "5 重りの腕" in text and "5 腕" not in text, text

# 5. 前の組 tora-v4 は、本人の決定（11-07）で「5 重りの腕」の 4 行（#498 の作り。今の組と同じ字と並び）。凍結の組 tora-v3 は「5」の 1 行のまま
# なぜ見るか: v4 の札は #498 で、v7 の札は型紙エンジンの写しで、別々の作りから刷る。字か並びが割れると、組で部品の名が違って見える
now, TIGER.SHEET_SET = TIGER.SHEET_SET, "tora-v4"
try:
    d = drop(neck)
    assert d.label == "5 重りの腕" and [t for t, _, _ in d.label_lines] == ["5 重", "り", "の", "腕"], (d.label, d.label_lines)
    assert "5 重りの腕" in "".join(TIGER.materials(neck)) and "5 腕" not in "".join(TIGER.materials(neck))
    TIGER.SHEET_SET = TIGER.FROZEN_SET
    d = drop(neck)
    assert d.label == "5" and not d.label_lines, (d.label, d.label_lines)
finally:
    TIGER.SHEET_SET = now
print("ok 虎の 5 重りの腕の札（縦に 4 行・入らない寸法は 5 腕・用意する物の名・前の組 v4 も 5 重りの腕・凍結の組 v3 は 5 のまま）")
