"""goraigo-v8 の直し（11-04 の試行を受けた本人の決定）が型紙に入っている事を見る。

本人の答え（カード 103912・104321）: H-C にも内筒の土台、H-A の溝は下から切り込む、ジャバラは糊代と貼る位置の印まで決める、
生徒の声からの候補は全部（谷・山の説明、筒を先に作る順）。
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
# 口の台に載せる形（H-E）は扇の端を台に貼るので、足を足さない
assert min(x for x, _ in by_key(rim)["fan"].outline) == 0 and not by_key(rim)["base"].art

# 4. 最初に筒を 1 つ作る順
for p in (tab, stick, rim):
    st = steps(p)
    assert st[1].startswith("まず 1 外筒だけ") and "角筒にする" in st[2]
print("ok")

# 5. v9: 見える面（外筒と扇）は折り線を刷らず、絵の色の境で折る（本人の決定 d、11-04）。隠れる部品は線を残す
for p in (tab, stick, rim):
    k = by_key(p)
    assert k["tube"].hide_folds and k["fan"].hide_folds
    assert not k["base"].hide_folds and ("pusher" not in k or not k["pusher"].hide_folds)
    fan = k["fan"]
    fills = [a["fill"] for a in fan.art[: int(p["fold_count"])]]
    assert all(a != b for a, b in zip(fills, fills[1:])), "隣の板は色が違う（色の境が折り目）"
    tube_grounds = [a["fill"] for a in k["tube"].art if a["kind"] == "poly" and a["pts"][0][1] == 4.5]
    assert len(set(tube_grounds)) == 2, "外筒は 1 面おきに地の色を変える"
assert any("色の境" in s for s in steps(tab))
print("ok v9")
