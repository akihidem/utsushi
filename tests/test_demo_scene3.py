"""デモ動画の場面 3（demo.scene3）の床: 合図の表、1 コマが時刻だけで決まる事、仮説の数の札が記録から来る事、
字幕に順位の言葉が無い事を見る。

画面は撮らない（試験を網と Chrome につながずに回すため）。撮った画面の代わりに、測った枠の所に
色の四角を置いた偽の画面で描く。F9（動き方を描かない）は機械で全部は見られないので、ここでは見ない。
"""
import json

from PIL import Image, ImageDraw

from demo import scene3
from demo.flip import H, W
from omochae.marks import without_premise

# 合図の表は時刻の順で、動画の長さの中
spans = list(scene3.CUES.values())
assert all(a < b for a, b in spans) and spans == sorted(spans) and spans[-1][1] <= scene3.DURATION
assert scene3.Scene3.duration == scene3.DURATION == 13.0

# 仮説の数と玩具の名は記録から。札の文に数を書き込んでいない
data = json.loads((scene3.ROOT / "data/hypotheses" / f"{scene3.SID}.json").read_text(encoding="utf-8"))
n = len(data["hypotheses"])
assert scene3.hypothesis_count() == n
assert scene3.label() == f'仮説 {n}（{data["toy"]}）', scene3.label()
assert "{n}" in scene3.LABEL and not any(ch.isdigit() for ch in scene3.LABEL.replace("{n}", ""))

# 順位や推しに見える言葉を字幕に出さない（J-025）。並びに触れる時は「順位ではない」と言う
captions = scene3.CAPTIONS + (scene3.label(),)
for word in ("1位", "１位", "2位", "上位", "おすすめ", "オススメ", "推し", "一番", "ベスト", "正解", "ランキング", "点"):
    assert not any(word in without_premise(c) for c in captions), word
assert "順位ではない" in scene3.SUB_LIST
assert all(c.count("順位") == c.count("順位ではない") for c in captions)
# 予想の段は外した（本人の決定 11-05、#242）。字幕が予想を先に求めない。前提は本人の言葉の形で出す
assert not any("先に予想" in c or "予想が先" in c for c in captions)
assert "正解ではなく" in scene3.TITLE_PREMISE and "AI が考えた仮説" in scene3.TITLE_PREMISE
# 画面の釦は「型紙を見る」（刷るのは型紙の窓の印刷の所だけ。#305）。字幕を今の画面に合わせる
assert "型紙を見る" in scene3.TITLE_LIST and "刷る" not in scene3.TITLE_LIST
# 新しく書く字幕に「案を選ぶ」を入れない（本人の決定 11-05 17:26: 型紙はおもちゃ一個につき一個）
assert "案を選" not in scene3.TITLE_LIST

# 偽の画面: 測った枠の所に四角を置く（前提の札・仮説の札）
premise = [210, 1100, 1000, 70]
plates = [[210 + 300 * i, 1300, 280, 671] for i in range(4)] + [[210, 2001, 280, 486]]
rects = {"premise": [premise], "plate": plates[:n]}
dpr = 2
shot = Image.new("RGB", (1600 * dpr, 3400 * dpr), (252, 252, 250))
d = ImageDraw.Draw(shot)
for p in rects["plate"] + rects["premise"]:
    d.rectangle([v * dpr for v in (p[0], p[1], p[0] + p[2], p[1] + p[3])], fill=(255, 253, 247), outline=(122, 59, 29))
scene = scene3.Scene3(shot, rects, dpr=dpr)
assert len(scene.plates) == n and f"仮説の {n} 枚" in scene.mod_note

for t in (0.5, 2.0, 4.0, 6.0, 7.0, 8.2, 10.0, 11.0, 12.9):
    a, b = scene.frame(t), scene.frame(t)
    assert a.size == (W, H) and a.tobytes() == b.tobytes(), t

# 寄りが効いている（途中で絵が変わる）
assert scene.frame(1.5).tobytes() != scene.frame(4.0).tobytes() != scene.frame(9.0).tobytes()
# 仮説の札は同じ倍率で同じ高さの所から並び、記号の順（左から右）のまま
xs = [x for x, _, _ in scene.plates]
assert xs == sorted(xs) and len({y for _, y, _ in scene.plates}) == 1
scale = {round(p.width / q[2], 3) for (_, _, p), q in zip(scene.plates, plates)}
assert max(scale) - min(scale) < 0.01, scale
# 札は動画の幅の中
assert min(xs) >= 0 and max(x + p.width for x, _, p in scene.plates) <= W
# 撮った枠の外は、撮った頁の地の色で埋める（継ぎ目を見せない。皮の色が変わっても追いつくよう、色を書き込まない）
for bg in ((252, 252, 250), (30, 30, 30)):
    plain = Image.new("RGB", (1600 * dpr, 1000 * dpr), bg)
    assert scene3.page_color(plain) == bg
    assert scene3.Scene3(plain, rects, dpr=dpr).view(plain, (800, 900, 3200)).getpixel((0, 0)) == bg
print("ok")

# 撮る高さ: 頁の作りが変わって長くなっても、使う枠（前提の札・仮説の札）と寄りの余白が撮った画面に入る。
# 11-05 に頁を作り直した後、高さを決め打ちにしていたので札 D・E の下が黒く欠けた（3400px に対して札の下端 3505px）。
grown = {"premise": [[290, 1129, 1020, 133]], "plate": [[290, 2303, 326, 627], [290, 2951, 326, 553]]}
assert not scene3.shot_fits(grown, 3400), "札の下端が画面の外"
need = scene3.need_height(grown, 3400)
assert need >= 2951 + 553 + scene3.SHOT_MARGIN and scene3.shot_fits(grown, need)
# 短い頁は、決めた高さより低くしない（寄りの絵の大きさを変えない）
assert scene3.need_height({"premise": [[0, 100, 10, 10]], "plate": []}, 1400) == 1400
print("ok shot height")
