"""デモ動画の場面 5（demo.scene5）の床: 写真は U-24 の確かめ表で通った物だけ、数と言葉は試行の記録のまま、を見る。

網につながず、写真も開かずに回す（写真の入る道は手元で作った偽の写真で見る）。
扇の開き方を描かない決まり（F9）と順位を付けない決まり（J-025）は機械で全部は見られない。
ここでは記録の 2 枚の札が同じ言葉で並ぶ事だけを見る。
"""
import pathlib
import re
import tempfile

from PIL import Image

from demo import flip, scene5

readme = scene5.TRIALS.read_text(encoding="utf-8")

# 合図の表は時刻の順で、場面の長さの中
spans = list(scene5.CUES.values())
assert all(a < b for a, b in spans) and spans == sorted(spans) and spans[-1][1] <= scene5.DURATION
assert scene5.DURATION == 5.0 and scene5.Scene5.duration == scene5.DURATION
assert scene5.CAPTION == ("紙で作って、動いた。",), "2 つ目の字幕は消した（本人の決定 11-06）"
assert all(0 <= t <= scene5.DURATION for t in scene5.SHEET_TIMES)

# 既定の写真は確かめ表と一致する。表を自前でも読み、scene5 の読み方と食い違わない事も見る
rows = {}
for line in scene5.REVIEW.read_text(encoding="utf-8").splitlines():
    m = re.match(r"\|\s*(p\d\d)\.jpg\s*\|(.*)\|\s*$", line)
    if m:
        rows[m.group(1)] = m.group(2).split("|")[-1].strip()
assert len(rows) == 9, rows  # p01〜p09 が表に在る（表の形が変わったら気づく）
mine = tuple(sorted(n for n, judge in rows.items() if judge in scene5.ACCEPT))
assert scene5.PHOTOS == mine == scene5.allowed_photos(), (scene5.PHOTOS, mine)
# 条件つきや外す判断は通さない
with tempfile.TemporaryDirectory() as tmp:
    fake = pathlib.Path(tmp) / "review.md"
    fake.write_text("| p01.jpg | a | 無し | b | 載せる |\n| p02.jpg | a | 無し | b | 外す |\n"
                    "| p03.jpg | a | 無し | b | ぼかせば載せてよい |\n| p04.jpg | a | 無し | b |  |\n"
                    "| p05.jpg | a | 無し | b | 載せる（画面をぼかしてから） |\n| p06.jpg | a | 無し | b | OK、ただし顔は外す |\n"
                    "| p07.jpg | a | 無し | b | 可能なら外す |\n"
                    "| goraigo-motion.mp4（5 秒） | a | 無し | b | 載せる |\n", encoding="utf-8")
    # 判断の欄が「載せる」などと丸ごと一致する時だけ通す。条件や但し書きが付いた判断は人が決め直す
    assert scene5.allowed_photos(fake) == ("p01",), scene5.allowed_photos(fake)
# 確かめ表で通っていない写真は --photos で渡しても止まる
if "p06" not in scene5.allowed_photos():
    assert scene5.resolve_photos("p06") is None
assert scene5.resolve_photos("") == []

# 字幕の言葉は README が言う事だけ。「わからない」の字幕は本人の決定（11-06）で消した（型紙 1 枚の形では案がいくつもあるように聞こえるため）。
# 記録の答えは README に残っている
assert "わからない" in readme and "動画と写真がどちらの仮説か分からないため" in readme and "本人の答え" in readme
assert not any("わからない" in c for c in scene5.CAPTION)
# 1 かたまり、1 秒 5 字以下（本人の方針 11-05）。現れてから場面の終わりまで読める
assert scene5.DURATION - scene5.CUES["line0"][0] >= len(scene5.CAPTION[0]) / 5
# 既定の写真は確かめ表で通った物だけ。多く見せない
assert set(scene5.SHOWN) <= set(scene5.PHOTOS) and len(scene5.SHOWN) <= 3

# 写真の許可が空なら、写真のファイルを 1 つも開かない
opened = []
real_open = Image.open


def spy(fp, *a, **k):
    opened.append(str(fp))
    return real_open(fp, *a, **k)


Image.open = spy
try:
    scene = scene5.Scene5(scene5.resolve_photos("") or ())
    for t in (0.5, 2.2, 3.0, 3.6, 4.4, 4.9):
        a, b = scene.frame(t), scene.frame(t)
        assert a.size == (flip.W, flip.H) and a.tobytes() == b.tobytes(), t
finally:
    Image.open = real_open
assert not any("photos" in p for p in opened), opened
# 字幕が現れる（1 かたまり。現れる前と後で絵が変わる）
assert scene.frame(1.0).tobytes() != scene.frame(3.0).tobytes()

# 写真が渡された時だけ枠の中が変わる（偽の写真で。repo の写真は開かない）
with tempfile.TemporaryDirectory() as tmp:
    p = pathlib.Path(tmp) / "fake.jpg"
    Image.new("RGB", (400, 300), (20, 120, 60)).save(p)
    with_photo = scene5.Scene5([p])
    region = scene5.FRAME_BOX
    assert with_photo.frame(3.0).crop(region).tobytes() != scene.frame(3.0).crop(region).tobytes()
    # 縦と横の写真の間でも溶かせる（枠の大きさの紙に置いてから混ぜる）
    q = pathlib.Path(tmp) / "fake2.jpg"
    Image.new("RGB", (300, 400), (120, 20, 60)).save(q)
    two = scene5.Scene5([p, q])
    assert two.frame(1.0).crop(region).tobytes() != two.frame(5.0).crop(region).tobytes()
    # 切らずに収める: 縦横の比が元のまま
    ph = with_photo.photos[0]
    assert abs(ph.width / ph.height - 400 / 300) < 0.01
print("ok")
