"""後入れの札（demo.later。本人の指示 11-07「本人の声の6文と、本物の Claude の返事の場面は後入れで空けておくこと」）の床。

見る事: 本物の Claude の返事の札は場面 8 の聞く段からだけ出る／語りの札は、声が無い時は「本人の声は後入れ」、仮の読み上げの印がある時は
「仮の読み上げ」、本人の声が入った（印が無い）時は出ない／札は画面の右上に重なり、字幕の所は変えない。
"""
import pathlib
import tempfile

from PIL import Image

from demo import core, flip, later, script

ask = core.CUES_ALL["core_make"]["ask"][0]
assert later.label("core_make", ask - 0.1) is None and later.label("core_make", ask) == later.LABEL_CLAUDE
assert later.label("word_ai", 1.0) is None and later.label("scene7", 1.0) is None, "声の口の無い場面には出さない"

with tempfile.TemporaryDirectory() as root:
    slot = pathlib.Path(root) / script.SLOT_DIR
    slot.mkdir(parents=True)
    assert later.label("talk_toys", 1.0, root) == later.LABEL_VOICE, "声が無い時"
    for v in script.SLOTS["talk_toys"]["voice"]:
        (slot / f"{v}{script.VOICE_EXT}").write_bytes(b"x")
    (slot / later.MARK).write_bytes(b"")
    assert later.label("talk_toys", 1.0, root) == later.LABEL_VOICE_TMP, "仮の読み上げの時"
    (slot / later.MARK).unlink()
    assert later.label("talk_toys", 1.0, root) is None, "本人の声が入った時は出ない"

base = Image.new("RGB", (flip.W, flip.H), flip.PAPER)
marked = later.overlay(base, "core_make", ask + 0.5)
diff = [y for y in range(flip.H) if any(marked.getpixel((x, y)) != flip.PAPER for x in range(0, flip.W, 4))]
assert diff and max(diff) < 120, "札は画面の上の帯にだけ重なる（字幕の所は変えない）"
assert later.overlay(base, "core_make", ask - 0.5).tobytes() == base.tobytes()
print("ok 後入れの札は本物の Claude の返事の段と、声の無い語りの場面にだけ、右上に出る")
