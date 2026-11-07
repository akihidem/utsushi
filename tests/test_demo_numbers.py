"""デモの公的調査の数の床（本人の決定 11-06: 使う数は 3 つ・置き場は A「秒は増やさず、裏の部の場面に小さく 1 行ずつ重ねる」）。

見る事: 数は原典で確かめた値のまま・出所の 1 行が付く／裏の部の場面だけに 1 つずつ・秒を足さない／読める秒（1 秒 5 字）と幅に入る／
本人の言葉の印のある札では上の帯（印のすぐ下に数を置くと、数まで本人の言葉に見えるため）／場面の頭で現れた後は動かない。
"""
from PIL import Image, ImageFont

from demo import core, flip, script, words

# 数と出所（原典の値。grove の state/survey-research-20261106 の 01・02）
lines = {k: v[0] for k, v in words.STATS.items()}
assert "59.6％" in lines["talk_physics"] and "31.5％" in lines["talk_physics"] and "小学 4 年生" in lines["talk_physics"]
assert "27％" in lines["core_loop"] and "58％" in lines["core_loop"] and "中学 2 年生" in lines["core_loop"]
assert "13.5％" in lines["word_ai"] and "ハンドクラフト・DIY・模型制作" in lines["word_ai"] and "15.0" not in lines["word_ai"]
assert all(src.startswith("出典: ") and ("2024" in src or "2026" in src) for _, src in words.STATS.values())
assert words.STATS["talk_physics"][1] == words.STATS["core_loop"][1] == words.TIMSS
# 言い切れない事は言わない
for line, src in words.STATS.values():
    assert not any(w in line for w in ("効果", "上がる", "担い手", "減", "復活", "取り戻")), line

# 裏の部の場面だけに 1 つずつ。秒は足さない（全体は本人の決定 11-07 の 179.3 秒）
assert set(words.STATS) <= set(script.BACK) and len(words.STATS) == 3
assert round(sum(script.load_scene(n).DURATION for n in script.SCENES), 1) == 179.3

# 読める秒と幅
f = ImageFont.truetype(flip.SERIF, words.STAT_SIZE)
g = ImageFont.truetype(flip.SERIF, words.SRC_SIZE)
for name, (line, src) in words.STATS.items():
    d = core.SECONDS["core_loop"] if name == "core_loop" else words.seconds_of(name)
    assert words.reading_chars(line) / words.RATE <= d - words.STAT_IN[1], name
    assert f.getlength(line) <= flip.W - 160 and g.getlength(src) <= flip.W - 160, name
    assert words.STAT_SIZE >= 30 and words.SRC_SIZE >= 22, "読める大きさの下限"

# 置き場（11-07 の組み直し）: 字幕を下の帯に出す場面は、数の行を上の帯へ（帯と重ねない）。全画面の題の札（word_ai）は下の帯
assert words.stat_band("talk_physics") == "top" and words.stat_band("core_loop") == "top" and words.stat_band("word_ai") == "bottom"
FROM_TOP = flip.H - 130
assert all(b1 <= FROM_TOP for b0, b1 in [words.BANDS["top"][2:]]), "上の帯は印より上"


def ink(img, band):
    _, _, b0, b1 = words.BANDS[band]
    return img.convert("L").crop((0, b0, flip.W, b1)).getextrema()[0] < 200


cards = {n: words.ChunkCard(n, words.cues_of(n)) for n in ("talk_physics", "word_ai")}
cards["core_loop"] = core.LoopCard(core.CUES_ALL["core_loop"])
for name, card in cards.items():
    band = words.stat_band(name)
    assert not ink(card.frame(0.0), band), (name, "頭ではまだ出ない")
    assert ink(card.frame(5.0), band), (name, "場面の中で出る")
    a = card.frame(5.0).crop((0, words.BANDS[band][2], flip.W, words.BANDS[band][3]))
    b = card.frame(card.duration - 0.2).crop((0, words.BANDS[band][2], flip.W, words.BANDS[band][3]))
    assert a.tobytes() == b.tobytes(), (name, "現れた後は動かさない")
# 表の部の札には出さない
for name in ("talk_toys", "talk_lost", "word_touch"):
    c = words.ChunkCard(name, words.cues_of(name))
    assert not ink(c.frame(5.0), "top") and name not in words.STATS
# 手の映像を敷く札では、帯に紙の色を掛けて読めるようにする
frames = []
import pathlib  # noqa: E402
import tempfile  # noqa: E402
with tempfile.TemporaryDirectory() as tmp:
    for i in range(2):
        p = pathlib.Path(tmp) / f"{i:05d}.jpg"
        Image.new("RGB", (flip.W, flip.H), (40, 60, 50)).save(p)
        frames.append(p)
    hand = words.ChunkCard("talk_physics", words.cues_of("talk_physics"), hands=[(frames, 0.0, 8.0)])
    px = hand.frame(5.0).getpixel((flip.W - 40, 20))
    assert all(abs(px[k] - flip.PAPER[k]) < 40 for k in range(3)), ("帯は紙の色", px)
print("ok 公的調査の数は裏の部の 3 場面に 1 行ずつ、原典の値と出所のまま、秒を足さずに重なる")
