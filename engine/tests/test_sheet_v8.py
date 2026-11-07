"""v8 の直しが御来迎の型紙に入っている事を見る。

柄の形にも内筒の土台がある・つまみの溝は下から切り込む（くり抜かない）・蛇腹は糊代と貼る位置の印まで型紙で決める・
最初に筒を 1 つ作る順にする。どれも紙で組んで試した時に作りにくかった所を直した物。
"""
from omochae.templates.slider_fan import DEFAULTS, LEG_GLUE, leg_length, materials, parts, steps

tab = {**DEFAULTS, "push_part": "tab", "hub": "axle", "pusher_height": 15}
stick = {**DEFAULTS, "push_part": "stick", "hub": "axle", "pusher_height": 84}
rim = {**DEFAULTS, "push_part": "tube", "hub": "rim", "push_amount": 36, "pusher_height": 84, "fold_count": 18, "fold_width": 8}


def by_key(p):
    return {q.key: q for q in parts(p)}


# 1. 柄で押す形にも土台（短い内筒）がある
s = by_key(stick)
assert "pusher" in s and s["pusher"].name == "土台" and s["pusher"].height == stick["stage_height"]
assert any("土台" in x and "割り箸" in x for x in steps(stick))

# 2. 溝は下の端まで開いた切り込みで、中を切り抜く矩形は無い。カッターを要らない
t = by_key(tab)
assert t["tube"].cuts == [], "くり抜く溝を残さない"
assert len(t["tube"].outline) == 10, "外筒の輪郭に切り込みの 4 点が入る"
assert not any("カッター" in m for m in materials(tab))
assert any("下の端からはさみ" in x for x in steps(tab))

# 3. 軸で開く形の扇には、真ん中の足と糊代があり、台に貼る位置の印がある
for p in (tab, stick):
    f, b = by_key(p)["fan"], by_key(p)["base"]
    assert min(x for x, _ in f.outline) == -leg_length(p) and len(f.glue) == 1
    assert abs(min(x for x, _ in f.glue[0]) + leg_length(p)) < 1e-9 and max(x for x, _ in f.glue[0]) == -leg_length(p) + LEG_GLUE
    assert b.art, "台に足を貼る位置の印"
    assert any("足の糊代を 3 台の印に貼る" in x for x in steps(p))
# 口の台に載せる形（hub=rim）は扇の端を台に貼るので、足を足さない
assert min(x for x, _ in by_key(rim)["fan"].outline) == 0 and not by_key(rim)["base"].art

# 4. 最初に筒を 1 つ作る順
for p in (tab, stick, rim):
    st = steps(p)
    assert st[1].startswith("まず 1 外筒だけ") and "角筒にする" in st[2]
print("ok")

# 5. v9: 見える面（外筒と扇）は折り線を刷らず、絵の色の境で折る。隠れる部品は線を残す
for p in (tab, stick, rim):
    k = by_key(p)
    assert k["tube"].hide_folds and k["fan"].hide_folds
    assert not k["base"].hide_folds and ("pusher" not in k or not k["pusher"].hide_folds)
    fan = k["fan"]
    fills = [a["fill"] for a in fan.art[: int(p["fold_count"])]]
    assert all(a != b for a, b in zip(fills, fills[1:])), "隣の板は色が違う（色の境が折り目）"
    tube_grounds = [a["fill"] for a in k["tube"].art if a["kind"] == "poly" and a["pts"][0][1] == 4.5]
    assert len(set(tube_grounds)) == 2, "外筒は 1 面おきに地の色を変える"
    # 外筒は色の面を外にして角筒にするので、刷った面から見て山折り（制作者の答え 2026-11-06「色がついている所が外を向くよう折った」）。
    # 谷折り（刷った面がへこむ向き）だと色が内に入る。線は刷らないので、型紙の PDF は変わらない
    assert len(k["tube"].mountain) == 4 and not k["tube"].valley, (len(k["tube"].mountain), len(k["tube"].valley))
assert any("色の境" in s for s in steps(tab))
# 組み方の文も 1 語だけ（谷折り → 山折り）替えた。それより大きく文を変える時は制作者の確認を取る
assert "1 外筒を色の境で山折りし、糊代で貼って角筒にする" in steps(tab), steps(tab)
# 内筒は隠れる部品で破線を谷折りで刷るので、手順 2 は制作者の決定（2026-11-06）の文。「同じように」だと山折りと読めて、刷った破線と食い違った
assert "2 内筒は破線で谷折りし、糊代で貼って角筒にする" in steps(tab) and not any("同じように角筒にする" in s for s in steps(tab)), steps(tab)
# 用意する物の道具（制作者の確認 2026-11-06）: 穴があるのに竹串の行が無い形（内筒を下から押す・柄）は、穴をあける竹串を書く。
# つまみの形は竹串の行がもう有る。穴の無い形（内筒を下から押す・口の台）には書かない
for form, want in (("tab", "のり、はさみ、定規"), ("tube", "のり、はさみ、定規、竹串（穴あけ）"), ("stick", "のり、はさみ、定規、竹串（穴あけ）")):
    assert materials({**DEFAULTS, "push_part": form})[1] == want, (form, materials({**DEFAULTS, "push_part": form}))
assert materials({**DEFAULTS, "push_part": "tube", "hub": "rim"})[1] == "のり、はさみ、定規"
# 道具は部品を組まずに形の値で決める。部品から決めた答え（穴があり、竹串の行が無い）と、全部の押し方 × 中心の置き方で同じ事を見る
from omochae.templates.slider_fan import bom
for form in ("tab", "tube", "stick"):
    for hub in ("axle", "rim"):
        q = {**DEFAULTS, "push_part": form, "hub": hub}
        by_parts = any(x.holes for x in parts(q)) and not any("竹串" in r["material"] for r in bom(q))
        assert materials(q)[1].endswith("、竹串（穴あけ）") == by_parts, (form, hub, materials(q)[1])
# 柄の形の手順 2 も、手順 2 と同じ型の文（制作者の確認 2026-11-06）。「同じように」だと、山折りの外筒と同じと読めた
stick_steps = steps({**DEFAULTS, "push_part": "stick"})
assert "2 土台は破線で谷折りし、糊代で貼って角筒にし、割り箸の先を下から差し込んで貼る" in stick_steps, stick_steps
print("ok v9")

# EP-0017（制作者のレビューから採った案。2026-11-06）: 御来迎の次の版（goraigo-v11）は、筒を外す形（push_part lift）を足す。
# 今の組 goraigo-v10 の形（つまみ・内筒・柄）は変えない（凍結の場面の刷った紙は前と 1 バイトも違わない。run.sh の刷り比べで見る）。
# - 扇は糸を一切使わない（制作者「糸なしでやります」）。どの部品にも穴が無く、部品表・用意する物・組み方に糸と竹串が無い
# - 4 扇は足（出っぱり）が無い長方形。2 受け（U の字。底と左右の面が糊代）で、扇の下の端と両端の板を束ねる
# - 内筒・竹串・溝は無い（制作者「この形で開くなら、内筒を下から押す仕組みも竹串も要らない」）。3D の確かめ（fold3d）は、
#   つまみの形だけを組むので、この形は「確かめられない」（4）
# - 床は、筒がかぶさる事と受けが台に乗る事だけを見る。行程・内筒の遊び・足・筒の口の角・穴の床は、この形には出ない
import subprocess
import sys
from omochae.__main__ import load_source
from omochae.compose import compose
from omochae.templates import slider_fan as sf
lift = {**DEFAULTS, "push_part": "lift"}
assert sf.check_range(lift) == [] and sf.check_physics(lift) == [], [f.line() for f in sf.check_physics(lift)]
lp = by_key(lift)
assert set(lp) == {"tube", "base", "fan", "cradle", "figure"}, set(lp)
assert all(not q.holes and not q.cuts for q in lp.values()), [(q.key, q.holes, q.cuts) for q in lp.values()]
words = " ".join(r["material"] for r in sf.bom(lift)) + " ".join(materials(lift)) + " ".join(steps(lift))
assert "糸" not in words and "竹串" not in words, words
assert len(lp["fan"].outline) == 4 and not lp["fan"].glue, lp["fan"].outline  # 足（出っぱり）の無い長方形
c = lp["cradle"]
assert c.label == "2 受け" and len(c.valley) == 2 and len(c.glue) == 3 and abs(c.width - sf.cradle_width(lift)) < 1e-9, (c.label, c.valley, c.glue)
assert abs(c.height - (2 * sf.CRADLE_FLAP + sf.cradle_depth(lift))) < 1e-9
assert lp["base"].mountain and not lp["base"].valley, "筒を外す形の台は、印のある上の面を上にして糊代を下へ折る（山折り）"
assert by_key({**DEFAULTS, "push_part": "tab"})["base"].valley, "今の形の台の折りは変えない"
assert sf.title(lift) == "筒を外すと扇が開く" and steps(lift)[-1].endswith("筒を上へ外すと、扇が開く"), steps(lift)
_, layout, fails = compose("slider_fan", lift, load_source(sf.SOURCE))
assert not fails, [f.line() for f in fails]
# 3D の確かめはつまみの形だけ。この形は 4（確かめられない）で、トレースバックにならない
r = subprocess.run([sys.executable, "-m", "omochae.fold3d", "--template", "slider_fan", "--params", '{"push_part": "lift"}'], capture_output=True, text=True)
assert r.returncode == 4 and "Traceback" not in r.stderr, (r.returncode, r.stderr[-300:])
# 今の形の負の場面の寸法でも、この形に効かない床（行程・内筒の遊び・足・筒の口の角・穴）は出ない
lift_floors = {"F5.fan_height", "F5.fan_thickness", "F5.base_size", "F5.figure_height", "F5.figure_base", "F5.fan_length", "F5.range"}
for extra in ({"pusher_height": 50}, {"pusher_side": 29}, {"pivot_above_rim": 0, "fold_count": 6, "fold_width": 5, "fold_height": 40},
              {"hub": "rim", "push_amount": 36, "pusher_height": 40, "fold_height": 36}, {"fold_height": 50}, {"base_side": 27},
              {"paper_thickness": 1.2}, {"figure_h": 55}, {"figure_w": 30, "base_side": 10}):
    got = {f.floor for f in sf.check_physics({**lift, **extra}) + sf.check_range({**lift, **extra})}
    assert got <= lift_floors, (extra, got)
# 筒がかぶさらない寸法は落とす（台の高さ＋扇の高さが筒の高さ − 2 を超える）
short = {**lift, "fold_height": 60, "tube_height": 50, "base_glue": 10}  # 範囲の内: 台 10 + 扇 60 > 筒 50 − 2
# 受けの底の紙の厚さも高さに入れる（境で、紙の厚さの分だけ足りない組を落とす。見直しの指摘）
edge = {**lift, "tube_height": 70, "base_glue": 10, "fold_height": 58, "paper_thickness": 1.5}  # 10 + 1.5 + 58 = 69.5 > 68
assert any(f.floor == "F5.fan_height" for f in sf.check_physics(edge)), [f.line() for f in sf.check_physics(edge)]
# 像の幅も筒の内に入る（見直しの指摘の例: 筒 20・台 15・像の幅 30 は、足の糊代 12 で台には乗るが、筒をかぶせられない）
wide = {**lift, "tube_side": 20, "base_side": 15, "figure_w": 30}
assert any(f.floor == "F5.figure_base" and "筒をかぶせられない" in f.message for f in sf.check_physics(wide)), [f.line() for f in sf.check_physics(wide)]
assert not sf.check_range(short) and any(f.floor == "F5.fan_height" for f in sf.check_physics(short)), "筒がかぶさらない寸法を通した"
print("ok 御来迎の筒を外す形（糸なし・受け）")
