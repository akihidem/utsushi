"""振り子の波（pendulum_wave。江戸の玩具ではない試作の作例）を確かめる。

制作者の指示（2026-11-07）「何個かつくってみてよ。」（物理現象などの紙のモデルの試作）による。次を見る:
1. 長さと周期: いちばん長い振り子は Γ 秒に n0 回（longest_mm に収まる、いちばん小さい整数）、次は n0 + 1 回、…。
   どの長さも、点の重りの周期の式 T = 2π√(L/g) で Γ / n になる（式は教科書の値でも見る: 1 秒の振り子は約 248.4mm）。長さは短くなる向きに並ぶ。
   玉の回る重さは入れない（糸が玉の真ん中を揺れの軸と平行に通り、玉は糸を軸に回れる。見直しの指摘）。
2. Γ 秒で全部がそろい、Γ / 2 秒では隣どうしが逆の向き（位相が π ずれる）。
3. 塔の高さは、いちばん長い振り子の玉の下が机から 5mm（から 6mm まで）離れる高さ。
4. 寸法の決まり（F5.range）: 玉が隣と当たる・穴の組の間が狭い・V が浅い・梁の端が塔に乗らない・数が整数でない、を 1 行ずつ落とす。
5. 刷る物: 梁の穴の組は振り子の真ん中から V の上の幅の半分ずつ、物差しの線は長さの所、番号の札は部品の内。糸の長さは V の 2 辺と結び代。
   型紙の検査を全部通り、組み方の文は 9 段で、最後の段に Γ 秒が入る。
6. 出典の印: 江戸の玩具でない模型は、所蔵の代わりに出典の記録の reference（ここでは物理の原理の文）を「出典: …」と刷り、刷った PDF から
   その文・改変・出典 ID・仮説を読む（所蔵の名と永続 ID は探さない。DNA の模型と同じ形）。
   史料の出典では、今までどおり所蔵の名と永続 ID も探す。
"""
import json
import math
import pathlib
import tempfile

from omochae.__main__ import generate, load_source
from omochae.compose import compose
from omochae.marks import HOLDER, check_pdf, mark_lines
from omochae.templates import pendulum_wave as pw
from omochae.textfit import text_width

ROOT = pathlib.Path(__file__).resolve().parents[1]
p = dict(pw.DEFAULTS)
src = load_source(pw.SOURCE)

# 1. 長さと周期
n = pw.swings(p)
r = pw.bob_r(p["bob_g"])
Ls = pw.lengths(p)
assert n == list(range(n[0], n[0] + p["count"])) and n[0] == pw.first_swings(p), n
point = lambda m: pw.G_MM * (p["cycle_s"] / m / (2 * math.pi)) ** 2  # 点の玉の長さ
assert point(n[0]) <= p["longest_mm"] < point(n[0] - 1), (point(n[0]), point(n[0] - 1))  # n0 は収まる中でいちばん小さい
for m, L in zip(n, Ls):
    assert abs(pw.period_of(L) - p["cycle_s"] / m) < 1e-9, (m, L)
    assert abs(point(m) - L) < 1e-9, (m, L, point(m))  # 点の重りの長さそのもの
assert abs(pw.length_for(1.0) - 248.4) < 0.05 and abs(pw.length_for(2.0) - 993.6) < 0.1  # 教科書の値（g = 9.80665 m/s²）
assert all(a > b for a, b in zip(Ls, Ls[1:])) and Ls[0] <= p["longest_mm"], Ls

# 2. Γ 秒でそろい、Γ/2 秒で隣どうしが逆の向き
phase = lambda L, t: (2 * math.pi * t / pw.period_of(L)) % (2 * math.pi)
for L in Ls:
    ph = phase(L, p["cycle_s"])
    assert min(ph, 2 * math.pi - ph) < 1e-6, ph
for a, b in zip(Ls, Ls[1:]):
    d = (phase(b, p["cycle_s"] / 2) - phase(a, p["cycle_s"] / 2)) % (2 * math.pi)
    assert abs(d - math.pi) < 1e-6, d

# 3. 塔の高さ
gap = pw.tower_height(p) - Ls[0] - r
assert pw.CLEAR <= gap < pw.CLEAR + 1, gap


# 4. 寸法の決まり
def lines(**kw):
    q = dict(p, **kw)
    return [f.line() for f in pw.check_range(q) + pw.check_physics(q)]


assert lines() == []
assert len(lines(spacing=14, v_span=6)) == 1 and "玉が当たる" in lines(spacing=14, v_span=6)[0]
assert len(lines(spacing=18, v_span=14)) == 1 and "裂けやすい" in lines(spacing=18, v_span=14)[0]
deep = lines(longest_mm=50, count=8, v_span=24, spacing=30)  # 短い振り子（いちばん短い 約 37mm）に広い V
assert any("V の上の幅" in s for s in deep), deep
assert lines(end=12) and "塔の上に乗らない" in lines(end=12)[0]
assert lines(count=3.5) == ["FAIL F5.range [count] 3.5 は整数でない（振り子の数）"]
assert all(s.startswith("FAIL F5.range") for s in lines(spacing=14, v_span=6) + deep + lines(end=12))

# 5. 刷る物
by = {q.key: q for q in pw.parts(p)}
beam, gauge = by["beam"], by["gauge"]
for k in range(p["count"]):
    x = p["end"] + k * p["spacing"]
    assert (x - p["v_span"] / 2, 1.5 * p["beam_side"], pw.HOLE_R) in beam.holes and (x + p["v_span"] / 2, 1.5 * p["beam_side"], pw.HOLE_R) in beam.holes
assert len(beam.holes) == 2 * p["count"]
ticks = sorted(a["pts"][0][0] for a in gauge.art if a["kind"] == "line")
assert all(abs(t - L) < 1e-9 for t, L in zip(ticks, sorted(Ls))), ticks
for q in (beam, gauge):
    xs, ys = [x for x, _ in q.outline], [y for _, y in q.outline]
    for t, x, y in q.label_lines:
        assert min(xs) <= x and x + text_width(t, pw.LABEL_SIZE) <= max(xs) and min(ys) <= y and y + pw.LABEL_SIZE * pw.LABEL_LINE <= max(ys), (q.key, t)
assert [t for t, _, _ in beam.label_lines][1:] == [str(k + 1) for k in range(p["count"])]
for k, L in enumerate(Ls):
    assert pw.thread_length(p, L) == math.ceil(2 * math.hypot(L, p["v_span"] / 2) + pw.TIE)
    assert f"{k + 1} は {pw.thread_length(p, L)}mm" in pw.materials(p)[2]
_, layout, fails = compose("pendulum_wave", p, src)
assert not fails, [f.line() for f in fails]
st = pw.steps(p)
assert len(st) == 9 and f"{p['cycle_s']:g} 秒でまた全部がそろう" in st[-1], st[-1]
# 長さの式（点の重り）の前提: 糸が玉の真ん中を、梁と同じ向き（揺れの軸と平行）に通る事を、手順の文が言う（見直しの指摘）
assert "玉の真ん中を横に通る" in st[5] and "梁と同じ向き" in st[5], st[5]
sc = json.loads((ROOT / "tests/frozen/scenarios/pendulum_wave_neg.json").read_text(encoding="utf-8"))
assert lines(**{k: v for k, v in sc["params"].items() if k != "kind"}) == lines(spacing=14, v_span=6)

# 6. 出典の印
ml = mark_lines(src)
assert ml[0].startswith("出典: 物理の原理: ") and not any(s.startswith("所蔵") for s in ml), ml
with tempfile.TemporaryDirectory() as d:
    rc = generate("pendulum_wave", p, pw.SOURCE, str(pathlib.Path(d) / "pw"))
    assert rc == 0, rc
    pdf = pathlib.Path(d) / "pw.pdf"
    assert check_pdf(pdf, src) == []
    mid = dict(src, reference=src["reference"][12:40])  # 刷った文の途中（前に「出典:」が無い所）。頭の語ごと探すので見つからない
    assert [f.where for f in check_pdf(pdf, mid)] == ["出典の文献"], check_pdf(pdf, mid)
    ndl = load_source("NDL-1187053-R0000007-L-balance")
    miss = [f.where for f in check_pdf(pdf, ndl)]
    assert "所蔵" in miss and "永続ID" in miss, miss  # 史料の出典では、今までどおり所蔵の名（HOLDER）と永続 ID を探す
    assert HOLDER not in "".join(ml)
print(f"ok 振り子の波（{p['count']} 本・{p['cycle_s']} 秒でそろう・長さ {Ls[0]:.1f}〜{Ls[-1]:.1f}mm・塔 {pw.tower_height(p)}mm）")
