"""デモ動画の場面 3（demo.scene3）の床: 合図の表、1 コマが時刻だけで決まる事、仮説の数の札が記録から来る事、
字幕に順位の言葉が無い事を見る。

画面は撮らない（試験を網と Chrome につながずに回すため）。撮った画面の代わりに、測った枠の所に
色の四角を置いた偽の画面で描く。F9（動き方を描かない）は機械で全部は見られないので、ここでは見ない。
"""
import json

from PIL import Image, ImageDraw

from demo import scene3
from demo.flip import H, W

# 合図の表は時刻の順で、動画の長さの中
spans = list(scene3.CUES.values())
assert all(a < b for a, b in spans) and spans == sorted(spans) and spans[-1][1] <= scene3.DURATION
assert scene3.Scene3.duration == scene3.DURATION == 25.0

# 仮説の数と玩具の名は記録から。札の文に数を書き込んでいない
data = json.loads((scene3.ROOT / "data/hypotheses" / f"{scene3.SID}.json").read_text(encoding="utf-8"))
n = len(data["hypotheses"])
assert scene3.hypothesis_count() == n
assert scene3.label() == f'仮説 {n}（{data["toy"]}）・予想が先', scene3.label()
assert "{n}" in scene3.LABEL and not any(ch.isdigit() for ch in scene3.LABEL.replace("{n}", ""))

# 順位や推しに見える言葉を字幕に出さない（J-025）。並びに触れる時は「順位ではない」と言う
captions = scene3.CAPTIONS + (scene3.label(),)
for word in ("1位", "１位", "2位", "上位", "おすすめ", "オススメ", "推し", "一番", "ベスト", "正解", "ランキング", "点"):
    assert not any(word in c for c in captions), word
assert "順位ではない" in scene3.SUB_LIST
assert all(c.count("順位") == c.count("順位ではない") for c in captions)
# 予想の文は例である事を文の頭で示し、画面にも例と出す
assert scene3.EXAMPLE.startswith("（例）") and "実在の人の予想ではない" in scene3.SUB_PRED

# 偽の画面: 測った枠の所に四角を置く（入力欄・予想・仮説の札）
ta = [210, 1070, 640, 120]
plates = [[210 + 300 * i, 2010, 280, 671] for i in range(4)] + [[210, 2701, 280, 486]]
rects = {"before": {"textarea": [ta], "article": [], "plate": []},
         "after": {"textarea": [[210, 1238, 640, 120]], "article": [[210, 1043, 670, 154]], "plate": plates[:n]}}
dpr = 2
before = Image.new("RGB", (1600 * dpr, 1400 * dpr), scene3.SCREEN_BG)
ImageDraw.Draw(before).rectangle([v * dpr for v in (ta[0], ta[1], ta[0] + ta[2], ta[1] + ta[3])], fill=(255, 253, 247), outline=(138, 122, 98))
after = Image.new("RGB", (1600 * dpr, 3400 * dpr), scene3.SCREEN_BG)
d = ImageDraw.Draw(after)
for p in rects["after"]["plate"] + rects["after"]["article"]:
    d.rectangle([v * dpr for v in (p[0], p[1], p[0] + p[2], p[1] + p[3])], fill=(255, 253, 247), outline=(122, 59, 29))
scene = scene3.Scene3(before, after, rects, dpr=dpr)
assert len(scene.plates) == n and f"仮説の {n} 枚" in scene.mod_note

for t in (0.5, 3.0, 6.0, 9.2, 11.0, 13.0, 16.0, 21.0, 24.9):
    a, b = scene.frame(t), scene.frame(t)
    assert a.size == (W, H) and a.tobytes() == b.tobytes(), t

# 打ち込みが効いている（途中で絵が変わる）
assert scene.frame(5.0).tobytes() != scene.frame(7.0).tobytes()
# 仮説の札は同じ倍率で同じ高さの所から並び、記号の順（左から右）のまま
xs = [x for x, _, _ in scene.plates]
assert xs == sorted(xs) and len({y for _, y, _ in scene.plates}) == 1
scale = {round(p.width / q[2], 3) for (_, _, p), q in zip(scene.plates, plates)}
assert max(scale) - min(scale) < 0.01, scale
# 札は動画の幅の中
assert min(xs) >= 0 and max(x + p.width for x, _, p in scene.plates) <= W
print("ok")
