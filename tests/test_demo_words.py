"""言葉の札（demo.words）の床: 本人の言葉が記録と一字も違わない事、字が幅に収まる事、1 コマが時刻だけで決まる事を見る。

本人の決定（11-05）「哲学よりの動画にして」で、動画の軸を本人の言葉にした。言葉を動画で変えてしまうと、
本人が言っていない文を本人の言葉として出す事になるので、記録の引用の行と全文で照らす（部分一致にしない）。
"""
import pathlib
import tempfile

from PIL import Image, ImageDraw

from demo import flip, script, words

rec_lines = words.record_lines()
assert len(rec_lines) > 5, "記録の引用の行が読めていない"
for name, (lines, seconds, step) in words.CARDS.items():
    assert words.in_record(lines), f"{name} の字が記録と違う"
    assert all(s.strip() == s and s for s in lines), name
    assert script.load_scene(name).DURATION == seconds
    spans = list(words.cues_of(name).values())
    assert spans == sorted(spans) and spans[-1][1] < seconds - 3, f"{name} は最後の行の後に読む間を置く"

# 最初の言葉の札は本人の言葉（11-05 夕、芯の順番）の全文。字は足さず引かず、行の切れ目だけで分ける
TOUCH = "AIが良くなるのは副次的なもので、みんなが手で実際に作ることその楽しさに気づくことが最初。"
assert "".join(words.CARDS["word_touch"][0]) == TOUCH and TOUCH in rec_lines
# 優先の順が変わったので、前の札は台本に出さない（記録の言葉は消さない）
for gone in ("word_make", "word_fix", "word_who"):
    assert gone not in words.CARDS and gone not in script.SCENES, gone

# 一字でも違えば落ちる。短く切った文も落ちる（切った文を本人の言葉と書かない）
lines = words.CARDS["word_touch"][0]
assert not words.in_record((lines[0].replace("副次的", "二次的"), *lines[1:]))
assert not words.in_record(lines[1:]), "切った文を通した"
assert not words.in_record(("手を動かす楽しさを忘れた人のために作っている。",))

# つなぎ 1 は本人が決めた字のまま（本人の決定 11-05）。図と歌の場面の次、本人の言葉の札の前。本人の言葉の札にはしない
BRIDGE1 = "むかしの子どもも、今の子どもも、もらったおもちゃより、それを包んでいた紙やリボンのひもで遊んでしまうことがあります。"
assert "".join(words.BRIDGE) == BRIDGE1
assert "bridge" not in words.CARDS and BRIDGE1 not in rec_lines
at = script.SCENES.index("bridge")
assert script.SCENES[at - 1] == "scene2" and script.SCENES[at + 1] == "word_touch"
assert script.load_scene("bridge").DURATION == words.BRIDGE_SECONDS >= len(BRIDGE1) / 5, "1 秒に 5 字で読む間"
bridge = words.BridgeCard(words.cues_of("bridge"))
assert bridge.frame(0.0).tobytes() != bridge.frame(3.0).tobytes() != bridge.frame(bridge.duration - 0.05).tobytes(), "行は順に現れる"
assert bridge.frame(bridge.duration - 2.0).tobytes() == bridge.frame(bridge.duration - 0.05).tobytes(), "出きった後は止まって読ませる"

# 終わりの字幕は初めと同じ字（本人の決定 11-05）。字幕 → 問いの順で終わる。言葉の記録の引用ではないので、言葉の札と分ける
assert script.SCENES[-2:] == ["close", "ask"]
assert flip.CLOSING == ("絵は動きを止めて残した。", "どう動いたかは、紙で作って確かめる。")
assert "close" not in words.CARDS and script.load_scene("close").DURATION == words.CLOSE_SECONDS
closing = words.CloseCard(words.cues_of("close"))
assert closing.frame(0.0).tobytes() != closing.frame(3.0).tobytes()
assert closing.frame(3.0).tobytes() == closing.frame(closing.duration - 0.05).tobytes(), "字幕の札は止まって読ませる"

# 問いの文は本人の決定（11-05）。言葉の記録の引用ではないので、本人の言葉の札と分ける
assert words.ASK == "あなたなら、何を作りますか。" and words.ASK not in rec_lines
assert all(v >= 0 for v in words.fits().values()), words.fits()

# 台本の順: 問いの札が最後
assert script.SCENES[-1] == "ask" and all(n in script.SCENES for n in words.CARDS)

# 偽の頁: 枠ごとに黒い四角（人物の代わり）。網につながない
import json
rec = json.loads(flip.FIGURES.read_text(encoding="utf-8"))["pages"][flip.PAGE]
page = Image.new("L", (1400, 1200), 255)
d = ImageDraw.Draw(page)
for f in rec["figures"]:
    x, y, w, h = f["box_pct"]
    d.rectangle((x * 14 + 10, y * 12 + 10, (x + w) * 14 - 10, (y + h) * 12 - 10), fill=0)

for name in words.CARDS:
    cues = words.cues_of(name)
    card = words.Card(name, cues, page, rec)
    for t in (0.0, 0.8, 3.0, card.duration - 0.1):
        a, b = card.frame(t), card.frame(t)
        assert a.size == (flip.W, flip.H) and a.tobytes() == b.tobytes(), (name, t)
    # 行は順に現れる。字の出る所だけを見る（隅の人物は別に動く）
    box = (words.LEFT, 0, flip.W - 450, flip.H - 120)
    assert card.frame(0.1).crop(box).tobytes() != card.frame(card.duration - 0.1).crop(box).tobytes(), name
    # 隅の人物は動く（絵は動きを止めて残した、の筋を字の間も続ける）
    corner = (words.FIG_X - 200, words.FIG_BASE - words.FIG_TALL, words.FIG_X + 200, words.FIG_BASE)
    assert card.frame(card.duration - 2.0).crop(corner).tobytes() != card.frame(card.duration - 1.0).crop(corner).tobytes(), name

# 問いの札は止まっている（考える間に動く物を置かない）
ask = words.AskCard(words.cues_of("ask"))
assert ask.frame(3.0).tobytes() == ask.frame(ask.duration - 0.1).tobytes()
assert ask.frame(0.0).tobytes() != ask.frame(3.0).tobytes()

# 段の印は 3 つ。右上に収まる。本人の言葉の印は付けない（窓口が整理した文なので）
from PIL import ImageFont
assert [m for m, _ in words.STEPS] == ["①", "②", "③"]
for mark, s in words.STEPS:
    assert ImageFont.truetype(flip.SERIF_BOLD, 32).getlength(f"{mark} {s}") <= 800, s
    assert s not in rec_lines

# 記録を読む道も試す: 別のファイルの字と照らせる
with tempfile.TemporaryDirectory() as tmp:
    p = pathlib.Path(tmp) / "p.md"
    p.write_text("> 別の言葉\n", encoding="utf-8")
    assert words.in_record(("別の", "言葉"), p) and not words.in_record(lines, p)
print("ok")
