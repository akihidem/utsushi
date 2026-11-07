"""吊る形（hang）: 式が使う寸法と、刷る部品・組み方の文が同じ物を指す事。

- 軸の高さ: 刷る耳の穴は胴の上の縁から HOLE_MARGIN 下にある。axle_height が別の値なら式と実物がずれる
- 軸から頭の上の端まで: 帯の穴から帯の下の端までの長さから、頭と重ねる糊代を引いた長さ。組み方の文に重ねる長さを書く
- 重り: 式は軸の下 weight_below_axle に置く。組み方の文に頭の上の端からの位置を書き、頭の外なら貼れないので落とす
"""
from omochae.templates.pivot_counterweight import DEFAULTS, HOLE_MARGIN, axle_to_head_top, check_physics, parts, steps

hang = {**DEFAULTS, "mount": "hang", "axle_height": 50, "weight_below_axle": 28}
assert not check_physics(hang), [f.line() for f in check_physics(hang)]

# 軸の高さ: 刷る穴の高さ（胴の下の縁からの高さ）と式の値が合う
H = hang["body_height"]
body = next(q for q in parts(hang) if q.key == "body")
ys = sorted(y for _, y, _ in body.holes)
top1 = hang["glue"] + hang["body_width"]
assert H - (ys[0] - top1) == H - HOLE_MARGIN == hang["axle_height"]
off = {**hang, "axle_height": 40}
assert any(f.floor == "F5.pivot" and "耳の穴" in f.message for f in check_physics(off)), "式の軸の高さが刷る穴と違えば落とす"

# 軸から頭の上の端まで: 帯の穴 → 帯の下の端 − 重ねる長さ
strip = next(q for q in parts(hang) if q.key == "strip")
hole_y = strip.holes[0][1]
length = max(y for _, y in strip.outline)
text = " ".join(steps(hang))
import re

m = re.search(r"(\d+)mm 重ねて", text)
assert m, text
assert length - hole_y - int(m.group(1)) == axle_to_head_top(hang)

# 重り: 組み方の文に頭の上の端からの距離を書き、頭の外なら落とす
assert f"頭の上の端から {hang['weight_below_axle'] - axle_to_head_top(hang):g}mm" in text, text
below = {**hang, "weight_below_axle": 45}
assert any(f.floor == "F5.pivot" and "頭" in f.where + f.message and "貼れない" in f.message for f in check_physics(below)), [f.line() for f in check_physics(below)]
print("ok")

# 胴は色の面（虎の地・縞・横の絵）を外にして箱にするので、10 本とも刷った面から見て山折り（首の形・吊る形とも）。
# 谷折り（刷った面がへこむ向き）だと色が箱の内に入る。御来迎の外筒への制作者の答え（2026-11-06）と同じ線で直した。組み方の文は 1 語だけ替えた
for form in ({**DEFAULTS, "mount": "neck"}, hang):
    b = next(q for q in parts(form) if q.key == "body")
    assert len(b.mountain) == 10 and not b.valley, (form["mount"], len(b.mountain), len(b.valley))
    assert "1 胴を破線で山折りし、糊代で貼って箱にする。上の面は後で閉じる" in steps(form), steps(form)
print("ok 胴の折る向き")
# 用意する物の道具（制作者の確認 2026-11-06）: 首の形は前の壁の丸い穴を切るので、カッターを書く。吊る形には書かない
from omochae.templates.pivot_counterweight import materials
# 首の形は、重りの腕をテープで仮に留めて試してから貼るので、セロハンテープも書く（EP-0011、2026-11-06）
assert materials({**DEFAULTS, "mount": "neck"})[1] == "のり、はさみ、定規、セロハンテープ、カッター", materials({**DEFAULTS, "mount": "neck"})
assert materials(hang)[1] == "のり、はさみ、定規", materials(hang)
# カッターは部品を組まずに形の値で決める。部品から決めた答え（胴に中を切り抜く所がある）と、首の形・吊る形で同じ事を見る
for form in ({**DEFAULTS, "mount": "neck"}, hang):
    assert materials(form)[1].endswith("、カッター") == any(x.cuts or x.round_cuts for x in parts(form)), form["mount"]
print("ok 用意する物")
