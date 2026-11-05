"""デモ動画の最初の場面（demo.opening）の床: 問いの字が本人の字のままである事、動画が無い間は印が出る事、置けば入る事、決まりに合わない動画は止める事を見る。

動画は作らない（試験を ffmpeg につながずに回すため）。動画を割った絵の代わりに、色の絵を渡す。
"""
import pathlib
import tempfile

from PIL import Image

from demo import flip, opening

# 問いの字は本人の字のまま（本人の指示 11-05 20:07）
assert opening.QUESTION == "こんなおもちゃを知っていますか？"
assert opening.PLACEHOLDER == "（ここに職人のおもちゃの動画が入ります）"
assert opening.DURATION == 12.0
spans = list(opening.CUES.values())
assert all(a < b for a, b in spans) and spans == sorted(spans) and spans[-1][1] <= opening.DURATION

# 動画の置き場は git に入らない所（画像と動画は repo に入れない）。無い間は印の出る形
assert opening.VIDEO.relative_to(opening.ROOT).parts[0] == "out"
assert opening.has_video("/無い/道.mp4") is False

# 無い間: 白い地に問いと印。作り物で埋めない（白と字の色の間の色だけ）
blank = opening.Opening()
for t in (0.0, 1.0, 5.0, 11.9):
    a, b = blank.frame(t), blank.frame(t)
    assert a.size == (flip.W, flip.H) and a.tobytes() == b.tobytes(), t
assert blank.frame(5.0).getpixel((0, 0)) == opening.WHITE and blank.ground == opening.WHITE
colors = blank.frame(5.0).getcolors(flip.W * flip.H)
assert all(abs(c[0] - c[1]) < 12 and abs(c[1] - c[2]) < 12 for _, c in colors), "白と墨のほかの色を足している"
# 問いの字の後に印が現れる
assert blank.frame(0.7).tobytes() != blank.frame(5.0).tobytes()

# 置くと入る: 時刻で絵が替わり、問いの字は上の余白に残る。枠の外は白
with tempfile.TemporaryDirectory() as tmp:
    frames = []
    for i in range(3):
        p = pathlib.Path(tmp) / f"{i:05d}.jpg"
        Image.new("RGB", (opening.VIDEO_BOX[2] - opening.VIDEO_BOX[0], opening.VIDEO_BOX[3] - opening.VIDEO_BOX[1]), (10 + i * 100, 80, 80)).save(p)
        frames.append(p)
    filled = opening.Opening(frames)
    assert filled.frame(2.5).tobytes() == filled.frame(2.5).tobytes()
    mid = ((opening.VIDEO_BOX[0] + opening.VIDEO_BOX[2]) // 2, (opening.VIDEO_BOX[1] + opening.VIDEO_BOX[3]) // 2)
    assert filled.frame(2.5).getpixel(mid) != opening.WHITE
    assert filled.frame(2.5).getpixel((5, 5)) == opening.WHITE
    assert filled.frame(0.0).getpixel(mid) == opening.WHITE, "動画は溶けて現れる"
    assert filled.frame(2.5).crop((0, 0, flip.W, opening.VIDEO_BOX[1])).getcolors(flip.W * 200) is not None
    # 絵の数より後の時刻は、最後の絵のまま
    assert filled.frame(11.9).tobytes() == filled.frame(5.0).tobytes()

# 決まりに合わない動画は理由を言って止める（崩れた絵を黙って出さない）
ok = lambda path: (1920, 1080, 12.5)
assert opening.video_problem("x", ok) is None
assert opening.video_problem("x", lambda p: (1080, 1920, 20.0)) and "16:9" in opening.video_problem("x", lambda p: (1080, 1920, 20.0))
assert "幅" in opening.video_problem("x", lambda p: (640, 360, 20.0))
assert "短い" in opening.video_problem("x", lambda p: (1920, 1080, 5.0))
assert "読めない" in opening.video_problem("x", lambda p: (0, 0, 0.0))
print("ok")
