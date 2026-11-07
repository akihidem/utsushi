"""英語字幕（demo.english。本人の言葉 11-07「英語字幕を入れよう」）の床。

見る事:
1. 書き出しが描く日本語の字（字幕・札・数の行・出所・問い・印・後入れの札）の全部に英語がある。表に、どこにも描かれない字が残っていない
2. 英語は置き場の幅に入る（デモと同じ字の形の幅で測る）。数の行と出所の行は 1 行に入る
3. 英語は 1 秒 15 字以下で読める（日本語のかたまりと同じ秒で出すため）
4. 英語の無い字を描こうとすると止まる（黙って英語を落とさない）
5. 台本の順・場面の秒・合図は変わらない（英語は字の下に足すだけ）
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from demo import english, script, words  # noqa: E402
from demo.flip import SERIF, W  # noqa: E402

# 1. 全部の字に英語。表に余った字が無い
sources = english.all_sources()
missing = [(ja, where) for ja, where in sources if ja not in english.EN]
assert not missing, ("英語字幕が無い", missing)
drawn = {ja for ja, _ in sources}
stale = sorted(set(english.EN) - drawn)
assert not stale, ("表に、どこにも描かれない字がある（日本語の字を替えたら表も替える）", stale)
assert english.en_format("型紙の版 {n}", n=14) == "Pattern v14" and english.en_format("エンジンの版 {n}", n=7) == "Engine v7"

# 2. 幅に入る。かたまりは置き場の真ん中の幅で折って、どの行も幅に入る
for name, chunks in words.ALL.items():
    style = words.STYLES.get(name, {})
    size, cx = style.get("size", 72), style.get("cx", W // 2)
    f = english.font(size)
    for lines in chunks:
        for line in english.wrap(english.en("".join(lines)), size, english.room(cx)):
            assert f.getlength(line) <= english.room(cx), (name, line)
for line, src in words.STATS.values():
    assert ImageFont.truetype(SERIF, words.EN_STAT_SIZE).getlength(english.en(line)) <= W - 2 * english.MARGIN, line
    assert ImageFont.truetype(SERIF, words.SRC_SIZE).getlength(f"{src}　{english.en(src)}") <= W - 2 * english.MARGIN, src

# 3. 読める速さ（かたまりの秒で）
fast = []
for name, chunks in words.ALL.items():
    for lines in chunks:
        e = english.en("".join(lines))
        if len(e) > 15 * words.chunk_seconds(lines) + 1e-9:
            fast.append((name, e))
assert not fast, ("英語が 1 秒 15 字を超える", fast)

# 4. 英語の無い字は止まる
img = Image.new("RGB", (W, 200))
try:
    words.draw_chunk(ImageDraw.Draw(img), ("英語の無い字",), W // 2, 100, 40, 1.0)
except english.MissingEnglish:
    pass
else:
    raise AssertionError("英語の無い字を黙って描いた")

# 5. 台本は変わらない
assert script.SCENES == ["opening", "talk_toys", "talk_lost", "scene2", "flip", "word_touch", "scene3", "core_make", "scene5", "core_keep",
                         "core_gallery", "border", "talk_physics", "talk_claude", "core_loop", "word_ai", "scene7", "close", "ask"]
assert round(sum(script.load_scene(n).DURATION for n in script.SCENES), 2) == 178.9
# 秒と合図は日本語のかたまりだけで決まる（英語は秒を足さない）
import inspect  # noqa: E402
for fn in (words.seconds_of, words.cues_of, words.chunk_seconds):
    assert "english" not in inspect.getsource(fn), fn.__name__
print(f"ok 英語字幕: 字 {len(drawn)} の全部に英語があり、幅と読む速さに入る")
