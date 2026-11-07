"""場面「エンジンの仕組み」（demo.engine・案）の床。本人の言葉（11-07）「paper to toy の一つの具体例であるとか、エンジンの仕組みとかは
デモとサイトで説明した方がいい」。

見る事:
1. 1 コマは時刻だけで決まる。段の図は字幕のかたまりに合わせて 1 本ずつ現れ、最後のかたまりで具体例の札が出る
2. 字幕は 1 秒 5 字以下・1 かたまり 2 秒以上（words.cues_of と同じ作り）。場面の秒は読む秒そのもの（字を縮めて秒に合わせない）
3. 描く字の全部に英語がある（demo.english）。箱の字は箱の中に入る
4. 材料の「書かなかった事」の線: 3D の段の題に、3D で組んで確かめる 2 つの玩具を書く。人が採る箱がある
5. 台本は今のまま（ENGINE_SCENE が False・19 場面・178.9 秒）。入れ替えた時の秒は数えて出す（入れるかと秒の出所は窓口の決め）
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from PIL import ImageFont  # noqa: E402

from demo import engine, english, script, words  # noqa: E402
from demo.flip import SERIF  # noqa: E402

# 1. 時刻だけで決まる。段は 1 本ずつ
scene = engine.Engine()
for t in (0.2, 3.0, 9.0, 15.0, engine.DURATION - 0.1):
    assert scene.frame(t).tobytes() == scene.frame(t).tobytes(), t
assert engine.ROW_AT == tuple(sorted(engine.ROW_AT)) and engine.ROW_AT[1] == engine.CUES["c1"][0] and engine.ROW_AT[2] == engine.CUES["c2"][0]
row = lambda k: (0, engine.ROW_Y[k] + engine.BOX_DY, words.W, engine.ROW_Y[k] + engine.BOX_DY + engine.BOX_H)  # noqa: E731
early = scene.frame(engine.ROW_AT[1] - 0.05)
assert len(set(early.crop(row(1)).getdata())) == 1, "3D の段は 2 つ目のかたまりまで出ない"
late = scene.frame(engine.DURATION - 0.1)
assert all(len(set(late.crop(row(k)).getdata())) > 1 for k in range(3)), "最後には 3 段とも出ている"
# 現れた後は動かさない（字のそばに動く物を置かない線）
a, b = scene.frame(engine.CUES["c3"][0] + 1.0), scene.frame(engine.DURATION - 0.2)
assert a.crop((0, 0, words.W, engine.EXAMPLE_Y + 60)).tobytes() == b.crop((0, 0, words.W, engine.EXAMPLE_Y + 60)).tobytes()

# 2. 読む秒
starts = [engine.CUES[f"c{i}"][0] for i in range(len(engine.CHUNKS))] + [engine.DURATION]
for i, lines in enumerate(engine.CHUNKS):
    span = starts[i + 1] - starts[i]
    assert span >= words.MIN_CHUNK - 1e-9 and words.reading_chars("".join(lines)) / span <= words.RATE + 1e-6, lines
    assert "".join(lines)[-1] in "、。", lines
assert engine.DURATION == 21.6, engine.DURATION  # 案の 12 秒には入らない（4 かたまりを読む秒）

# 3. 英語
for s in engine.drawn():
    assert s in english.EN, s
for _, boxes in engine.ROWS:
    for label, _ in boxes:
        assert ImageFont.truetype(SERIF, engine._fit(label, engine.BOX_SIZE)).getlength(label) <= engine.BOX_W - 24, label
for lines in engine.CHUNKS:
    span = chunk = words.chunk_seconds(lines)
    assert len(english.en("".join(lines))) / span <= 15 + 1e-9, (lines, chunk)

# 4. 書かなかった事の線
assert "御来迎" in engine.ROWS[1][0] and "首振り虎" in engine.ROWS[1][0], "3D で組んで確かめるのは 2 つの玩具だけ"
assert any(label == "人が採る" for label, _ in engine.ROWS[2][1]), "直しの案を採るのは人"
assert not any(w in "".join(engine.drawn()) for w in ("DNA", "公開", "だれでも")), "まだ作っていない物を言わない"

# 5. 台本は今のまま。入れ替えた時の秒は数えて出す
assert script.ENGINE_SCENE is False and "engine" not in script.SCENES and len(script.SCENES) == 19
now = round(sum(script.load_scene(n).DURATION for n in script.SCENES), 2)
assert now == 178.9, now
swapped = script.scenes(engine=True)
assert swapped[script.SCENES.index("talk_claude")] == "engine" and "talk_claude" not in swapped
total = round(sum(script.load_scene(n).DURATION for n in swapped), 2)
print(f"ok エンジンの場面 {engine.DURATION} 秒。台本 {now} 秒、入れ替えると {total} 秒（179.5 秒の床まで {round(total - 179.5, 1)} 秒多い）")
