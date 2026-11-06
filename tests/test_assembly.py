"""手順どおりの 3D 組み立て（本人の考え 2026-11-05、#331）。

面が硬いまま折れている事（蝶番と剛体）、段と文の 1 対 1、形の検査が合う形を通して合わない形を落とす事を見る。
"""
import contextlib
import copy
import io
import json
import math
import os
import tempfile

os.environ.setdefault("OMOCHAE_DATA", tempfile.mkdtemp())

from shapely.geometry import Polygon

from omochae import assembly, hypotheses, instructions
from omochae.model import Part
from omochae.templates import slider_fan

G = "NDL-1187053-R0000005-L"
P = {**slider_fan.DEFAULTS, **hypotheses.sheet_of(G).get("params", {})}


def build(**change):
    p = {**P, **change}
    return assembly._slider_fan(p, slider_fan.parts(p))


def lines(bench):
    return [f.line() for f in bench.failures]


def rigid(m):
    r = [m[i][:3] for i in range(3)]
    for i in range(3):
        for j in range(3):
            d = sum(r[i][k] * r[j][k] for k in range(3))
            assert abs(d - (1 if i == j else 0)) < 1e-6, m
    det = (r[0][0] * (r[1][1] * r[2][2] - r[1][2] * r[2][1]) - r[0][1] * (r[1][0] * r[2][2] - r[1][2] * r[2][0])
           + r[0][2] * (r[1][0] * r[2][1] - r[1][1] * r[2][0]))
    assert abs(det - 1) < 1e-6, "鏡に映した形になっている"


# 御来迎: 段と文が 1 対 1 で、できあがりが 1 つ続く
bench = assembly.assemble(G)
words = instructions.steps(P, "slider_fan")
# 次の組は、最後の動き（押し上げて開く）が手順 13 の文になったので、最後の段がその手順になる（前の組は字の無いできあがりの段）
assert [f["text"] for f in bench.frames] == words and len(words) == 13
assert bench.frames[-1]["step"] == len(words)

# 紙を切り分けても面積が変わらない（折り線で分けただけ）
for key, sheet in bench.sheets.items():
    whole = Polygon(sheet.part.outline).buffer(0).area
    assert abs(sum(s.area for s in sheet.panels) - whole) < 1e-3, key

# どの段でも面は硬いまま。できあがりの開いた扇も、紙の形を変えていない
for frame in bench.frames:
    for m in frame["panels"].values():
        if m is not None:
            rigid(m)

# 折り線でつながった面は、折っても離れない（開いた扇の前まで。開いた形は硬い面で表せない事を断ってある）
for frame in bench.frames[:-1]:
    for key, sheet in bench.sheets.items():
        for child, (parent, k) in sheet.tree.items():
            a, b = frame["panels"][f"{key}:{child}"], frame["panels"][f"{key}:{parent}"]
            if a is None:
                continue
            for point in sheet.lines[k][0]:
                gap = math.dist(assembly.apply(a, point), assembly.apply(b, point))
                assert gap < 0.7, (frame["step"], key, child, gap)  # 重なりの前後をずらす分だけ許す

# できあがりは絵を外に、印を上に、竹串は溝の中、扇は要から上へ開く
last = bench.frames[-1]["panels"]
tube = bench.sheets["tube"]
for k in range(4):
    i = bench.panel_at("tube", P["tube_side"] * k + P["tube_side"] / 2, 2)
    c = tube.panels[i].centroid
    world = assembly.apply(last[f"tube:{i}"], (c.x, c.y))
    assert assembly._dot(world, assembly.normal_of(last[f"tube:{i}"])) > 0, "絵のある面が内を向いている"
center = bench.panel_at("base", P["base_glue"] + P["base_side"] / 2, P["base_glue"] + P["base_side"] / 2)
assert assembly.normal_of(last[f"base:{center}"])[1] < -0.99, "台の印の面が上を向いていない"
fan = bench.sheets["fan"]
tops = [assembly.apply(last[f"fan:{i}"], (P["fold_height"], s.centroid.y))[1] for i, s in enumerate(fan.panels) if s.bounds[2] > 0]
assert len(tops) == P["fold_count"] and max(tops) <= -P["tube_height"] / 2 - P["pivot_above_rim"] + 1, "扇が要より下へ開いている"

# 閉じた時（手順 12）、扇も像も外筒の口の中に隠れる。次の組は手順 13（押し上げて開く）が後ろにあるので、番号で引く
closed = next(f for f in bench.frames if f["step"] == 12)["panels"]
for key in ("fan", "figure"):
    sheet = bench.sheets[key]
    for i, s in enumerate(sheet.panels):
        for point in s.exterior.coords:
            assert assembly.apply(closed[f"{key}:{i}"], point)[1] >= -P["tube_height"] / 2 - 1e-6, key

# 次の組（goraigo-v11）: 外筒と扇の台を山折りにしたので、言葉のとおりに折って合わない所が無い。手順 13 の段も文と並ぶ
found = lines(bench)
assert found == [], found
assert bench.frames[-1]["step"] == 13 and bench.frames[-1]["text"] == words[12], "手順 13 の段が無い"

# 線を前の組の谷折りに戻すと、合わない所が 2 つ出る（11-04 の実物の写真 p07・p09 は逆の向きで作っている。検査が言葉でなく紙の線を見ている）
parts = slider_fan.parts(P)
for q in parts:
    if q.key in ("tube", "base"):
        q.mountain, q.valley = q.valley, q.mountain
found = lines(assembly._slider_fan(P, parts))
assert any("手順 3" in x and "絵のある面（4 面）が筒の内側に入る" in x for x in found), found
assert any("手順 7" in x and "印のある面が下を向く" in x for x in found), found


def tube_part(widths, kinds="valley"):
    xs = [sum(widths[:i]) for i in range(len(widths) + 1)]
    end, h = xs[-1], 84
    outline = [(0, 0), (end, 0), (end + 8, 2), (end + 8, h - 2), (end, h), (0, h)]
    folds = [((x, 0), (x, h)) for x in xs[1:]]
    return Part(1, "t", "筒", outline, **{kinds: folds})


# 閉じる: 4 面がそろえば閉じ、1 面が狭いと糊代が届かない
good = assembly.Bench([tube_part([30, 30, 30, 30])])
good.fold("t", deg=90)
assert good.closes("t", good.panel_at("t", 124, 40), good.panel_at("t", 4, 40)) and not good.failures
bad = assembly.Bench([tube_part([30, 30, 30, 25])])
bad.fold("t", deg=90)
assert not bad.closes("t", bad.panel_at("t", 119, 40), bad.panel_at("t", 4, 40))
assert "糊代が相手の面に届かない" in lines(bad)[0], lines(bad)

# 絵の向き: 同じ紙でも、谷なら内を向き、山なら外を向く
for kinds, want in (("valley", 4), ("mountain", 0)):
    t = assembly.Bench([tube_part([30, 30, 30, 30], kinds)])
    t.fold("t", deg=90)
    lo, hi = t.bounds("t")
    middle = tuple((a + b) / 2 for a, b in zip(lo, hi))
    assert len(t.faces_out("t", [t.panel_at("t", 30 * k + 15, 40) for k in range(4)], middle)) == want, kinds

# 穴: 向かい合う 2 つは通り、隣り合う面の 2 つは通らない
holed = tube_part([30, 30, 30, 30])
holed.holes = [(45, 40, 1), (105, 40, 1), (75, 40, 1)]
h = assembly.Bench([holed])
h.fold("t", deg=90)
assert h.holes_in_line("t", 0, 1) and not h.failures
assert h.holes_in_line("t", 0, 2) is None and "向かい合わない" in lines(h)[0]

# 寸法が合わなければ、どの段で何が合わないかを言う
assert any("の中に入らない" in x for x in lines(build(pusher_side=34, base_side=34))), "内筒が外筒より太い"
assert any("台の面（20mm）" in x for x in lines(build(base_side=20))), "台が内筒より小さい"
assert any("畳んだ扇が外筒の口から" in x for x in lines(build(fold_height=60))), "折りの高さが高い"

# 溝を短くすると、押し上げた時に竹串が当たる
shorter = slider_fan.parts(P)
tube_q = next(q for q in shorter if q.key == "tube")
top = min(y for x, y in tube_q.outline if 40 < x < 50 and 0 < y < P["tube_height"])
tube_q.outline = [(x, y + 30 if y == top else y) for x, y in tube_q.outline]
assert any("竹串が溝の上の端に当たる" in x for x in lines(assembly._slider_fan(P, shorter))), "溝が短い"

# 竹串が短いと溝から外へ出ない
real = assembly.knob_length
assembly.knob_length = lambda p: 5
assert any("竹串が短くて" in x for x in lines(build())), "竹串が短い"
assembly.knob_length = real

# 像の穴がずれると、糸がまっすぐ通らない
moved = slider_fan.parts(P)
fig = next(q for q in moved if q.key == "figure")
fig.holes = [(fig.holes[0][0], fig.holes[0][1] - 6, fig.holes[0][2])]
assert any("像の穴と扇の要の穴の高さが合わない" in x for x in lines(assembly._slider_fan(P, moved))), "穴がずれた"

# 段と文がずれたら落とす（図と文がずれないため）
real_steps = instructions.steps
calls = []


def shifted(p, template):
    calls.append(template)
    got = copy.copy(real_steps(p, template))
    if len(calls) > 1:
        got[3] = "違う文"
    return got


instructions.steps = shifted
assert any("1 対 1" in x for x in lines(assembly.assemble(G)))
instructions.steps = real_steps

# 組み立ての書き方が無い物は、組み立てたふりをしない
assert assembly.assemble("NDL-1187053-R0000009-R") is None, "台に立てる形はまだ"
other = next(h for h in hypotheses.load(G)["hypotheses"] if (h.get("params") or {}).get("push_part") not in (None, "tab"))
assert assembly.assemble(G, other["id"]) is None, "押し方が別の形はまだ"

# 命令: 通る 0・落ちる 3・検査できない 4・JSON は全部の段。次の組は合わない所が無いので 0、前の組（線が谷折り）は 3
out = io.StringIO()
with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
    assert assembly.main([G, "--json"]) == 0
    now = slider_fan.SHEET_SET
    slider_fan.SHEET_SET = slider_fan.FROZEN_SET
    try:
        assert assembly.main([G]) == 3
    finally:
        slider_fan.SHEET_SET = now
    assert assembly.main(["NDL-1187053-R0000009-R"]) == 4
    assert assembly.main(["無い玩具"]) == 4
assert len(json.loads(out.getvalue().splitlines()[0])) == len(words)
print("ok")
