"""御来迎（slider_fan）の色を確かめる。どの形にも効く。

制作者の決定（2026-11-06）「実物の写真と照らした直しは、御来迎・虎とも全部入れる。次の版へ」の色の直し（案 D）。
- 筒は白木、扇は金に寄せる。v12 で足した筒の紫の枠の札は、制作者の指示（2026-11-06「① 外筒の紫色の部分は不用（外す）」）で外した。
- どの形も色の境で折る（線を刷らない）ので、隣り合う面と板が同じ色にならない事を、全部の形で見る。
- 寸法の直し（扇を細かく小さく・筒を細長く）は、次の組の形の見本の場面で入れる（この試験ではない）。
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from omochae.templates import slider_fan as sf  # noqa: E402

# 1. 色の境で折る部品（外筒・扇）は、隣り合う面と板の色が違う（同じ色だと折る所の目印が消える）。全部の形で見る
for form in sf.PUSH_PARTS:
    p = {**sf.DEFAULTS, "push_part": form, **({"pusher_height": 84} if form in ("tube", "stick") else {})}
    by = {q.key: q for q in sf.parts(p)}
    A, H = p["tube_side"], p["tube_height"]
    # 面の地の色: 各面の真ん中の高さの帯（上の帯と下の帯の間）の塗り
    def ground(i):
        cx = A * (i + 0.5)
        hits = [a["fill"] for a in by["tube"].art if a["kind"] == "poly" and a["fill"] in (sf.WOOD, sf.WOOD_ALT)
                and min(x for x, _ in a["pts"]) <= cx - 3 and max(x for x, _ in a["pts"]) >= cx - 3]
        return hits[0]
    faces = [ground(i) for i in range(4)]
    assert all(faces[i] != faces[i + 1] for i in range(3)), (form, faces)
    fills = [a["fill"] for a in by["fan"].art[:int(p["fold_count"])]]
    assert all(fills[i] != fills[i + 1] for i in range(len(fills) - 1)), form
    assert set(fills) == {sf.FAN_A, sf.FAN_B} and sf.WOOD != sf.WOOD_ALT, form

# 金と白木に寄せた色: 扇は赤と緑が青より十分に強い黄の色、筒は明るい（地の明るさ 0.75 以上。前の原図の地は 0.54 と 0.64）
rgb = lambda c: tuple(int(c[i:i + 2], 16) / 255 for i in (1, 3, 5))
for c in (sf.FAN_A, sf.FAN_B):
    r_, g_, b_ = rgb(c)
    assert r_ > 0.75 and g_ > 0.6 and b_ < g_ - 0.25, c
for c in (sf.WOOD, sf.WOOD_ALT):
    assert sum(rgb(c)) / 3 >= 0.75, c

# 2. 筒の紫の枠の札は無い（指示 ①）: どの形も、外筒の絵は上と下の帯・面の地（白木の 4 つの色が全部ある）と、角の 2 本線（線の色）だけ。
#    塗りも線も、ほかの色（紫の枠・白い札の紙）を持たない
for form in sf.PUSH_PARTS:
    p = {**sf.DEFAULTS, "push_part": form, **({"pusher_height": 84} if form in ("tube", "stick") else {})}
    tube = {q.key: q for q in sf.parts(p)}["tube"]
    fills = {a.get("fill") for a in tube.art if a["kind"] == "poly"}
    strokes = {a.get("stroke") for a in tube.art if a["kind"] == "line"}
    assert fills == {sf.WOOD, sf.WOOD_ALT, sf.WOOD_TOP, sf.WOOD_BOTTOM}, (form, fills)
    assert strokes == {sf.LINE} and sum(1 for a in tube.art if a["kind"] == "line") == 2, (form, strokes)
    assert all(a["kind"] in ("poly", "line") for a in tube.art), form

# 3. 範囲の上限: 筒の高さを 130 まで書ける形は、内筒も同じ高さまで書ける（内筒を下から押す形と柄の形は、内筒が筒より短いと落とす）
assert sf.RANGES["pusher_height"][1] >= sf.RANGES["tube_height"][1]
# 折り数は写真の 44〜52 枚を書け、上限 60 まで受ける。扇の長さを書く時も、合っている長さを範囲の検査が先に落とさない
assert sf.RANGES["fold_count"][1] == 60 and sf.RANGES["fan_length"][1] >= sf.RANGES["fold_count"][1] * sf.RANGES["fold_width"][1]
for fc in (44, 52, 60):
    assert sf.check_range({**sf.DEFAULTS, "fold_count": fc, "fan_length": fc * 8.5}) == [], fc
assert sf.check_range({**sf.DEFAULTS, "fold_count": 61})[0].floor == "F5.range"
for form in ("tube", "stick"):
    tall = {**sf.DEFAULTS, "push_part": form, "tube_height": 130, "pusher_height": 130}
    assert sf.check_range(tall) == [] and not [f for f in sf.check_physics(tall) if "押し切れない" in f.message], form
print("ok 御来迎の色（白木・金）・筒の札は無い")
