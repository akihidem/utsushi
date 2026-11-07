"""デモ動画の場面 3（demo.scene3）の床: 合図の表、1 コマが時刻だけで決まる事、字幕に順位の言葉が無い事、
決定と逆の字幕を出さない事を見る。

画面は撮らない（試験を網と Chrome につながずに回すため）。撮った画面の代わりに、測った枠の所に
色の四角を置いた偽の画面で描く。F9（動き方を描かない）は機械で全部は見られないので、ここでは見ない。
"""
from PIL import Image, ImageDraw

from demo import scene3
from demo.flip import H, W
from omochae.marks import without_premise

# 合図の表は時刻の順で、動画の長さの中
spans = list(scene3.CUES.values())
assert all(a < b for a, b in spans) and spans == sorted(spans) and spans[-1][1] <= scene3.DURATION
assert scene3.Scene3.duration == scene3.DURATION == 11.0

# 順位や推しに見える言葉を字幕に出さない（J-025）
captions = scene3.CAPTIONS
for word in ("1位", "１位", "2位", "上位", "おすすめ", "オススメ", "推し", "一番", "ベスト", "正解", "ランキング", "点"):
    assert not any(word in without_premise(c) for c in captions), word
# 予想の段は外した（本人の決定 11-05、#242）。字幕が予想を先に求めない。前提は本人の言葉の形で出す
assert not any("先に予想" in c or "予想が先" in c for c in captions)
assert "正解ではなく" in scene3.TITLE_PREMISE and "Claude が考えた仮説" in scene3.TITLE_PREMISE
# 型紙は玩具に 1 つ（本人の決定 11-05 17:26）。「並べる」「案を選ぶ」を字幕に出さない。「開いたら、すぐ作る。」は残す（ですます調にした。11-07 昼）
assert scene3.CLOSING == ("開いたら、すぐ作れます。",)
assert not any("並べる" in c or "案を選" in c or "並ぶ" in c for c in captions)

# 偽の画面: 測った枠の所に四角を置く（前提の札・仮説の札）
premise = [210, 1100, 1000, 70]
rects = {"premise": [premise], "plate": [[210, 1216, 640, 392]]}
dpr = 2
shot = Image.new("RGB", (1600 * dpr, 3400 * dpr), (252, 252, 250))
d = ImageDraw.Draw(shot)
for p in rects["plate"] + rects["premise"]:
    d.rectangle([v * dpr for v in (p[0], p[1], p[0] + p[2], p[1] + p[3])], fill=(255, 253, 247), outline=(122, 59, 29))
scene = scene3.Scene3(shot, rects, dpr=dpr)

for t in (0.5, 2.0, 4.0, 6.0, 7.0, 8.2, 10.0, 10.9):
    a, b = scene.frame(t), scene.frame(t)
    assert a.size == (W, H) and a.tobytes() == b.tobytes(), t

# 頁の札はたたき台の 1 枚だけ（J-032）。記録の仮説の数のまま 5 枚に戻ったら、頁が変わったので止まる
assert scene3.plates_ok(1) and not scene3.plates_ok(0) and not scene3.plates_ok(2) and not scene3.plates_ok(5)
# 寄った先に、前提の札と型紙の札の全部が切れずに入る（札は 1 枚なので、途中で切ると何の札か分からない）
cam, view_h = scene.cam_premise, scene.cam_premise[2] * scene.aspect
plate = rects["plate"][0]
assert cam[1] - view_h / 2 <= premise[1] and plate[1] + plate[3] <= cam[1] + view_h / 2, cam
assert cam[0] - cam[2] / 2 <= premise[0] and premise[0] + premise[2] <= cam[0] + cam[2] / 2, cam
# 寄りが効いている（途中で絵が変わる）。頭は字を置かない（絵で分かる）。上の帯に字は 1 かたまりだけ
assert scene.frame(1.5).tobytes() != scene.frame(5.0).tobytes() != scene.frame(10.0).tobytes()
# 字は下の真ん中の帯（11-07 の組み直し）。頁の頭の間は帯に字を置かず、前提の札の所で 1 かたまり出る
from demo import words as _words  # noqa: E402
band = (0, _words.H - _words.BAND_BOTTOM - 200, W, _words.H - _words.BAND_BOTTOM)
assert scene.frame(1.5).crop(band).tobytes() == scene.frame(1.6).crop(band).tobytes(), "頁の頭の間は字を置かない（帯の所が動かない）"
assert scene.frame(1.5).crop(band).tobytes() != scene.frame(5.0).crop(band).tobytes(), "前提の 1 かたまりが帯に出る"
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
