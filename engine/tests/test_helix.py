"""雛形 helix（DNA の二重らせんの紙の模型・試作。制作者の指示 2026-11-07「何個かつくってみてよ。」）を確かめる。

1. 形の比が B 形 DNA の値: 1 回り 10.5 塩基対（1 段のねじれ 360/10.5°）、1 段の高さ ÷ 直径 = 0.34 / 2.0、2 本の腕の間は 140°（小さい溝）と 220°（大きい溝）。
2. 右巻き: 板 i を上から見て左回りに i × ねじれ回し、1 段ずつ上げた時の、腕の先（背骨を貼る所）の点の並びが右巻きのらせん。
   背骨の帯の印の間の長さは、その隣どうしの点の間の長さと同じ（帯を印のとおりに貼ると、ねじれと高さが決まる）。
3. 紙の作り: 板の穴は竹串より太い。間の筒は竹串に巻ける長さで、外の太さが板の穴より太い（板が筒に乗る）。筒の長さは 1 段から板の厚さを引いた物。
4. 2 本の背骨は逆向き: 背骨 1 の印は下の板から、背骨 2 の印は上の板から番号が並ぶ。両端に 5' と 3'。
5. 型紙: 既定の寸法で検査を全部通る。竹串が短いと、範囲の床で落ちる。刷る印は、所蔵の代わりに文献の文（出典の記録の reference）。
6. 組み方の文: 9 段で、巻く向き（上から見て左回り）と、2 本が逆向きな事を言う。
紙で組んで確かめていない。らせんの比を見る模型で、原子の形や動きそのものではない。
"""
import json
import math
import pathlib

from omochae.__main__ import load_source
from omochae.compose import LABEL_SIZE, LINE, compose
from omochae.marks import mark_lines
from omochae.templates import helix as hx

ROOT = pathlib.Path(__file__).resolve().parents[1]
P = dict(hx.DEFAULTS)

# 部品の key は英小文字だけ（tests/test_foldsim.py と同じ決まり）
import re  # noqa: E402

assert all(re.fullmatch(r"[a-z]+", q.key) for q in hx.parts(P))

# 1. 形の比
assert abs(hx.TWIST - 360 / 10.5) < 1e-12 and abs(hx.rise(P) / (2 * P["radius"]) - 0.34 / 2.0) < 1e-12
assert hx.MINOR_DEG == 140.0 and abs((hx.ARM_A_DEG - hx.ARM_B_DEG) - hx.MINOR_DEG) < 1e-9  # 腕の間は 140°（反対の側は 220°）
assert hx.LABEL_SIZE == LABEL_SIZE and hx.LABEL_LINE == LINE

# 2. 右巻きと、背骨の印の間の長さ
R, h, n = P["radius"], hx.rise(P), P["n_bp"]


def attach(i, side_deg):
    """板 i の腕の先（背骨を貼る所）の 3D の点。上から見て左回りに i × ねじれ回し、i 段上げる（z が上）。"""
    a = math.radians(side_deg + i * hx.TWIST)
    return (R * math.cos(a), R * math.sin(a), i * h)


pts = [attach(i, 0.0) for i in range(n)]
for a, b in zip(pts, pts[1:]):
    assert abs(math.dist(a, b) - hx.segment(P)) < 1e-9
# 右巻き: 隣どうしの向きの外積の z が正（上へ進む時に左回り）
for a, b, c in zip(pts, pts[1:], pts[2:]):
    u = [b[k] - a[k] for k in range(3)]
    v = [c[k] - b[k] for k in range(3)]
    cz = u[0] * v[1] - u[1] * v[0]
    assert cz > 0, cz
parts = {q.key: q for q in hx.parts(P)}
for k in (1, 2):
    s = parts[f"back{chr(96 + k)}"]
    ys = sorted(y for a in s.art if a["kind"] == "mark" for _, y in a["pts"][:1])
    assert len(ys) == n and all(abs((b - a) - hx.segment(P)) < 1e-3 for a, b in zip(ys, ys[1:])), ys
    assert abs(s.height - ((n - 1) * hx.segment(P) + 2 * hx.STRAND_END)) < 1e-3

# 3. 紙の作り
plate = parts["platea"]
hole_r = plate.holes[0][2]
assert hole_r > P["skewer_d"] / 2
sp = parts["spacera"]
inner = P["skewer_d"] + 2 * hx.HOLE_CLEAR
assert abs((sp.width - hx.SPACER_GLUE) - math.pi * inner * hx.WRAPS) < 1e-3
outer = inner + 2 * hx.WRAPS * 0.15  # 紙の厚さ 0.15mm で巻いた外の太さの見込み
assert outer > 2 * hole_r, (outer, 2 * hole_r)
assert abs(sp.height - (hx.rise(P) - hx.PLATE_T)) < 1e-3
assert len([k for k in parts if k.startswith("plate")]) == n and len([k for k in parts if k.startswith("spacer")]) == n - 1
for i in range(n):  # 腕の色は塩基で、向かいは相補
    q = parts[f"plate{chr(97 + i)}"]
    b = hx.SEQUENCE[i]
    assert [a["fill"] for a in q.art] == [hx.COLORS[b], hx.COLORS[hx.PAIR[b]]] and len(q.valley) == 2 and len(q.glue) == 2

# 4. 2 本の背骨は逆向き
labels = {k: [t for t, _, _ in parts[k].label_lines] for k in ("backa", "backb")}
assert labels["backa"][:3] == [str(n + 1), "5'", "3'"] and labels["backb"][:3] == [str(n + 2), "5'", "3'"]
assert labels["backa"][3:] == [str(i) for i in range(1, n + 1)] and labels["backb"][3:] == [str(i) for i in range(n, 0, -1)]

# 5. 型紙
src = load_source(hx.SOURCE)
_, layout, fails = compose("helix", P, src)
assert not fails, [f.line() for f in fails]
lines = mark_lines(src)
assert lines[0].startswith("出典: Watson J. D., Crick F. H. C. (1953)") and not any(s.startswith("所蔵") for s in lines)
ndl = load_source("NDL-1187053-R0000007-L-balance")
assert mark_lines(ndl)[0].startswith("所蔵: 国立国会図書館デジタルコレクション")  # 古い刷り物の型紙は前のまま
# 積んだ高さは板 n 枚と筒 n − 1 本（筒は 1 段 − 板の厚さ）。前は n 段と数え、12 段が 120mm の竹串に収まるのに断った（見直しの指摘）
for q in (P, dict(P, n_bp=12), dict(P, n_bp=6, radius=18)):
    n_, h_ = int(q["n_bp"]), hx.rise(q)
    stacked = n_ * hx.PLATE_T + (n_ - 1) * (h_ - hx.PLATE_T)  # 板と筒を 1 つずつ足した高さ
    assert abs(hx.stack_height(q) - (stacked + hx.CLAY_DEPTH + hx.TOP_MARGIN)) < 1e-9, q
assert hx.check_physics(dict(P, n_bp=12, skewer_len=120)) == []  # 12 段（既定の半径）は 120mm の竹串に収まる
short = dict(P, n_bp=12, radius=28, skewer_len=120)  # 要る長さ約 125mm（半径 29 からは背骨の帯が A4 に入らず、別の床でも落ちる）
assert [f.floor for f in hx.check_physics(short)] == ["F5.range"] and "竹串" in hx.check_physics(short)[0].where
assert hx.check_physics(dict(P, n_bp=12)) == []
neg = json.loads((ROOT / "tests/frozen/scenarios/helix_neg.json").read_text(encoding="utf-8"))
assert neg["expect"] == {"rc": 3, "floors": ["F5.range"]}

# 6. 組み方の文
st = hx.steps(P)
assert len(st) == 9 and any("上から見て左回り" in s for s in st) and any("向きが逆" in s for s in st)
print(f"ok DNA の二重らせんの模型（{n} 段・1 段 {hx.rise(P):.1f}mm・印の間 {hx.segment(P):.1f}mm）")
