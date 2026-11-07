"""エンジンの 3D 組み立て検品（omochae.check3d。制作者の言葉 2026-11-07「エンジンは3D組み立て検品を自分でする（エンジンの性質として）」
「組み立ての様子も作る」、決める側の決定: 入口は 3D の JSON を出す道だけ・記録は段ごとの絵か短い動画で当たりは赤）を確かめる。次を見る:
1. 小さな場面で、当たりの決め:
   - 面が面を刺すと 3D.hit。刺す所が穴（inner）なら当たらない。折り線でつながる隣の面は刺さない。
   - ほぼ平らな 2 面（貼る・重ねる）は、両側へ 1mm 超出る時だけ刺すと見る（0.87mm は通り、1.4mm は落ちる）。
   - 同じ部品の中の 2 つ目からの交わりも、同じ落ちの面と点に足す（記録の絵で全部を赤に）。
   - 玉が紙に食い込むと 3D.hit。付く部品（attach）の面は見ない。棒は穴（holes）の所でだけ紙を通る。
   - 机に置く形（desk）で机の下へ出ると 3D.out（棒の端も）。口の下に隠れる部品（below）が口の近くへ出ると 3D.out。
   - 刷った面の向き（faces の out・in・both）が違うと 3D.face。決めた部品が姿に無い時も、3D.out・3D.face で落ちる。
   - 近い形（custom）の部品の当たりは所見（NOTE）で、落ちにしない。
2. 本物の組: 虎 v7 は落ちも所見も無い（揺れの間 41 の姿も見る）。御来迎 v14 は落ちが無く、所見は開く扇（custom）の当たりだけ。
   虎 v6 は、粘土の玉が胴（前の壁）に食い込む・竹串が穴の無い紙（前の壁の糊代）を通る・揺れると頭が前の壁に刺さる、で落ちる（負の対照）。
   虎の手順 12 の尾は、机の下へ出ない（前は尾の先を下にして机の右に立て、16mm 出ていた。この検品で見つけて直した）。
3. 入口（python -m omochae.assembly3d）: 虎 v7・御来迎 v14 は 0 で JSON を書く。虎 v6 は 3 で JSON を書かず、同じ置き場の前の JSON も
   消す（古い形を読ませない）。--record は落ちても記録（段ごとの絵の一覧 PNG・短い動画 GIF・行の TXT）を書く。
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

from omochae import check3d as c3
from omochae.assembly3d import assemble

ROOT = pathlib.Path(__file__).resolve().parents[1]


def mat(o, u, v):
    """面の座標 (x, y, 0) を o + x·u + y·v へ写す列優先の 16 個（z の列は u × v）。"""
    n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
    return [*u, 0.0, *v, 0.0, *n, 0.0, *o, 1.0]


def part(key, panels, rows=None, holes=()):
    return {"key": key, "name": key, "panels": [{"id": i, "poly": poly, **({"inner": inner} if inner else {})} for i, (poly, inner) in enumerate(panels)],
            "tree": {"root": 0, "rows": rows or {}}, "holes": [list(h) for h in holes], "round_cuts": [], "art": []}


SQ = [[0, 0], [20, 0], [20, 20], [0, 20]]
X, Y, Z = (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)


def scene(parts, states, rods=None, balls=None, radius=None):
    """1 つの姿だけの作り方の 3D（段 1 の 1 つの姿）。states は {部品: [面ごとの 16 個]}。"""
    pose = {"parts": {k: {"panels": {str(i): m for i, m in enumerate(ms)}} for k, ms in states.items()}, "hidden": [],
            "rods": rods or {}, "balls": balls or {}}
    return {"parts": parts, "steps": [{"n": 1, "poses": [pose]}], "finale": {"poses": []}, "rods": {k: {"r": 1.0} for k in (rods or {})},
            "balls": {k: {"r": r} for k, r in (radius or {}).items()}, "toy": "test", "engine": {"commit": "test"}}


floors = lambda hits: sorted((h.floor, h.where, h.note) for h in hits)
wall = mat((-10.0, -10.0, 0.0), X, Y)  # z = 0 の 20mm 角の壁（真ん中が原点）
stick = mat((-2.0, 0.0, -10.0), X, Z)  # y = 0 の面で、z が −10〜10 の板（壁を刺す）
PL = [[0, 0], [4, 0], [4, 20], [0, 20]]

# 1. 小さな場面
d = scene([part("wall", [(SQ, None)]), part("stick", [(PL, None)])], {"wall": [wall], "stick": [stick]})
assert floors(c3.inspect(d, {})) == [("3D.hit", "stickとwall", False)], c3.summary(c3.inspect(d, {}))
hole = [[[7, 7], [13, 7], [13, 13], [7, 13]]]  # 壁の真ん中の 6mm 角の穴（板は x が −2〜2 で、穴の中を通る）
d = scene([part("wall", [(SQ, hole)]), part("stick", [(PL, None)])], {"wall": [wall], "stick": [stick]})
assert c3.inspect(d, {}) == []
TAB = [[0, 0], [20, 0], [20, 4], [0, 4]]  # 壁の真ん中を横切る 20 × 4mm の帯（交わる線が壁の中に来る）
d = scene([part("wall", [(SQ, None)]), part("tab", [(TAB, None)])], {"wall": [wall], "tab": [mat((-10.0, -2.0, -0.87), (0.996, 0.0, 0.087), Y)]})
assert c3.inspect(d, {}) == []  # 5° 傾いて壁の両側へ 0.87mm ずつ出る糊代は、ほぼ平らな重なり（1mm 以下）なので刺さない
d = scene([part("wall", [(SQ, None)]), part("tab", [(TAB, None)])], {"wall": [wall], "tab": [mat((-10.0, -2.0, -1.4), (0.990, 0.0, 0.139), Y)]})
assert floors(c3.inspect(d, {})) == [("3D.hit", "tabとwall", False)]  # 8° 傾いて 1.4mm ずつ出るのは、浅い角でも刺す
fold = {"1": {"parent": 0, "hinge": [[0, 20], [20, 20]], "kind": "valley"}}
d = scene([part("box", [(SQ, None), ([[0, 20], [20, 20], [20, 40], [0, 40]], None)], rows=fold)],
          {"box": [wall, mat((-10.0, 10.0, -20.0), X, Z)]})  # 2 枚目は折り線（壁の上の端 y = 10）で 90° に立つ（座標は y が 20 から）
assert c3.inspect(d, {}) == []  # 折り線を共にする面は、辺が相手に乗るだけで刺さない
d = scene([part("wall", [(SQ, None)]), part("arm", [(PL, None)])], {"wall": [wall], "arm": [mat((-2.0, 30.0, 3.0), X, Y)]},
          balls={"clay": {"at": [0.0, 0.0, 3.0]}}, radius={"clay": 5.0})
assert floors(c3.inspect(d, {})) == [("3D.hit", "clayとwall", False)]
assert c3.inspect(d, {"attach": {"clay": "wall"}}) == []
rod = {"skewer": {"from": [0.0, 0.0, -10.0], "to": [0.0, 0.0, 10.0]}}
d = scene([part("wall", [(SQ, None)])], {"wall": [wall]}, rods=rod)
assert floors(c3.inspect(d, {})) == [("3D.hit", "skewerとwall", False)]
d = scene([part("wall", [(SQ, None)], holes=[(10, 10, 1.2)])], {"wall": [wall]}, rods=rod)
assert c3.inspect(d, {}) == []
d = scene([part("wall", [(SQ, None)])], {"wall": [mat((-10.0, -15.0, 0.0), X, Y)]})  # 下の端は y = 5（机の 5mm 下）
assert floors(c3.inspect(d, {"desk": True})) == [("3D.out", "wall", False)] and c3.inspect(d, {}) == []
d = scene([part("wall", [(SQ, None)])], {"wall": [mat((-10.0, -30.0, 0.0), X, Y)]}, rods={"stick": {"from": [15.0, -5.0, 0.0], "to": [15.0, 3.0, 0.0]}})
got = c3.inspect(d, {"desk": True})
assert floors(got) == [("3D.out", "stick", False)] and got[0].rods == ["stick"] and got[0].points == [(15.0, 3.0, 0.0)]  # 棒の端が机の 3mm 下
x0, y0, k = c3._fit(d, [d["steps"][0]["poses"][0]])
for q in ((15.0, -5.0, 0.0), (15.0, 3.0, 0.0)):  # 記録の絵は、紙の外へ出た棒の端も入れる大きさ
    p = c3._rot(q)
    assert 0 <= c3.TILE / 2 + (p[0] - x0) * k <= c3.TILE and 0 <= c3.TILE / 2 + (p[1] - y0) * k <= c3.TILE, p
d = scene([part("z", [(SQ, None), (PL, None), (PL, None)])], {"z": [wall, stick, mat((4.0, 0.0, -10.0), X, Z)]})
got = c3.inspect(d, {})
assert floors(got) == [("3D.hit", "z", False)] and {("z", 1), ("z", 2)} <= set(got[0].panels) and len(got[0].points) == 2, (c3.summary(got), got[0].panels)
# 2 つの面が互いを刺す時は、深い方の向きで言う（壁の辺が板を 10mm、板の辺が壁を 1mm 刺す）
w_ = c3.Panel("w", "w", 0, [tuple(q) for q in SQ], [], [], c3.M(wall))
b_ = c3.Panel("b", "b", 0, [(0, 0), (10, 0), (10, 9), (0, 9)], [], [], c3.M(mat((0.0, -15.0, -1.0), Y, Z)))
assert abs(c3._deepest(w_, b_, c3.EPS)[1] - 10) < 1e-9 and abs(c3._deepest(b_, w_, c3.EPS)[1] - 10) < 1e-9
# 棒が同じ姿で同じ部品の 2 つの面を穴の無い所で通っても、落ちは 1 つで、まとめの行は「ほか」を言わない
d = scene([part("box", [(SQ, None), (SQ, None)])], {"box": [wall, mat((-10.0, -10.0, 5.0), X, Y)]}, rods=rod)
got = c3.inspect(d, {})
assert floors(got) == [("3D.hit", "skewerとbox", False)] and len(got[0].panels) == 2 and "ほか" not in c3.summary(got)[0], c3.summary(got)
lid = mat((-10.0, -40.0, 0.0), X, Y)  # 口（tube の一番上）は y = −40
d = scene([part("tube", [(SQ, None)]), part("fan", [(PL, None)])], {"tube": [lid], "fan": [mat((-2.0, -41.0, 5.0), X, Y)]})
rule = {"below": {"parts": ["fan"], "of": "tube", "clear": 2.0, "pose": (1, -1)}}
assert floors(c3.inspect(d, rule)) == [("3D.out", "fan", False)]  # 扇の上の端は口の 1mm 上
d = scene([part("tube", [(SQ, None)]), part("fan", [(PL, None)])], {"tube": [lid], "fan": [mat((-2.0, -37.0, 5.0), X, Y)]})
assert c3.inspect(d, rule) == []  # 口の 3mm 下
d = scene([part("tube", [(SQ, None)]), part("fan", [(PL, None)])], {"tube": [lid]})  # 扇を入れ忘れた姿
assert floors(c3.inspect(d, rule)) == [("3D.out", "fan", False)]
cube = [mat((0, 0, 0), Y, X), mat((0, 0, 20), X, Y), mat((0, 0, 0), Z, Y), mat((20, 0, 0), Y, Z), mat((0, 0, 0), X, Z), mat((0, 20, 0), Z, X)]
d = scene([part("box", [(SQ, None)] * 6)], {"box": cube})  # 6 面とも刷った面が外を向く 20mm の箱
assert c3.inspect(d, {"faces": {"box": "out"}}) == [] and floors(c3.inspect(d, {"faces": {"box": "in"}})) == [("3D.face", "box", False)]
d["steps"][0]["poses"][0]["parts"]["box"]["panels"]["1"] = mat((0, 0, 20), Y, X)  # 上の面だけ内向き
bad = c3.inspect(d, {"faces": {"box": "out"}})
assert floors(bad) == [("3D.face", "box", False)] and bad[0].panels == [("box", 1)], c3.summary(bad)
assert floors(c3.inspect(d, {"faces": {"lid": "out"}})) == [("3D.face", "lid", False)]  # 決めた部品が姿に無い
d = scene([part("wall", [(SQ, None)]), part("stick", [(PL, None)])], {"wall": [wall], "stick": [stick]})
d["steps"][0]["poses"][0]["parts"]["stick"]["custom"] = True
got = c3.inspect(d, {})
assert floors(got) == [("3D.hit", "stickとwall", True)] and c3.summary(got)[0].startswith("NOTE"), c3.summary(got)

# 2. 本物の組
d7, r7 = assemble(ROOT / "examples/tora_v7.json", commit="test")
assert len(r7["extra"]) == 41 and c3.inspect(d7, r7) == []
g14, r14 = assemble(ROOT / "examples/goraigo_v14.json", commit="test")
h14 = c3.inspect(g14, r14)
assert h14 and all(h.note and "fan" in h.where for h in h14), c3.summary(h14)
d6, r6 = assemble(ROOT / "examples/tora_v6.json", commit="test")
h6 = c3.inspect(d6, r6)
assert {(h.floor, h.where) for h in h6} == {("3D.hit", "clayとbody"), ("3D.hit", "skewerとbody"), ("3D.hit", "bodyとhead")}, c3.summary(h6)
assert not any(h.note for h in h6)
# まとめの行は一番深い姿の文（v6 の粘土の玉は、静かな時 1.4mm・揺れると 2.9mm）
s6 = c3.summary(h6)
assert any("[clayとbody]" in s and "2.9mm 食い込む" in s and "ほか" in s for s in s6), s6
assert any(h.where == "bodyとhead" and h.pose_label.startswith(("揺れ", "できあがり")) for h in h6)  # 頭は揺れると当たる
tail = [q for q in d7["steps"][11]["poses"]]
assert all(max(p[1] for pn in c3.panels_of(d7, q) for p in pn.pts) <= c3.DESK_TOL for q in tail)  # 手順 12 の尾は机の下へ出ない

# 3. 入口
env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
with tempfile.TemporaryDirectory() as tmp:
    tmp = pathlib.Path(tmp)
    run = lambda name: subprocess.run([sys.executable, "-m", "omochae.assembly3d", "--scenario", str(ROOT / f"examples/{name}.json"),
                                       "--out", str(tmp / f"{name}.json"), "--commit", "x", "--record", str(tmp / "rec")],
                                      cwd=ROOT, env=env, capture_output=True, text=True, timeout=600)
    r = run("tora_v7")
    assert r.returncode == 0 and json.loads((tmp / "tora_v7.json").read_text(encoding="utf-8"))["toy"] == "tora-v7", r.stderr
    assert "FAIL" not in r.stderr and "NOTE" not in r.stderr
    (tmp / "tora_v6.json").write_text(json.dumps({"format": "omochae-assembly-3d/1"}), encoding="utf-8")  # 前に書いた 3D の JSON がある置き場
    r = run("tora_v6")
    assert r.returncode == 3 and not (tmp / "tora_v6.json").exists() and "前の JSON を消した" in r.stderr, r.stderr
    assert "FAIL 3D.hit [clayとbody]" in r.stderr and "JSON は書かない" in r.stderr, r.stderr
    for ext in ("png", "gif", "txt"):
        assert (tmp / "rec" / f"tora-v6-check.{ext}").stat().st_size > 0 and (tmp / "rec" / f"tora-v7-check.{ext}").stat().st_size > 0
    assert "FAIL 3D.hit [clayとbody]" in (tmp / "rec/tora-v6-check.txt").read_text(encoding="utf-8")
    from PIL import Image
    gif = Image.open(tmp / "rec/tora-v7-check.gif")
    # 動画は全部の段とできあがりの動きの姿（続けて同じ絵の姿は、GIF を書く時に 1 枚にまとまる）
    assert len(d7["steps"]) <= gif.n_frames <= sum(len(s["poses"]) for s in d7["steps"]) + len(d7["finale"]["poses"]), gif.n_frames
print("ok 3D の組み立て検品（虎 v7 は落ちも所見も無い・御来迎 v14 は開く扇の所見 %d・虎 v6 は %d の姿で落ちる）" % (len(h14), len(h6)))
