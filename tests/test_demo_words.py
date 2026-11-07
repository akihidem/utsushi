"""言葉の札（demo.words）の床: 本人の言葉が記録と一字も違わない事、語りが全文のまま読点で分かれている事、1 秒 5 字以下である事、字が幅に収まる事、1 コマが時刻だけで決まる事を見る。

本人の決定（11-05）「哲学よりの動画にして」で、動画の軸を本人の言葉にした。言葉を動画で変えてしまうと、
本人が言っていない文を本人の言葉として出す事になるので、記録の引用の行と全文で照らす（部分一致にしない）。
本人の方針（11-05 20:10）「たくさん見る審査員の認知負荷を減らす方針が1番最初。癒し系で。」で、1 度に 1 かたまりだけを、ゆっくり出す。
"""
import pathlib
import tempfile

from PIL import Image

from demo import flip, script, words

rec_lines = words.record_lines()
assert len(rec_lines) > 5, "記録の引用の行が読めていない"
# 字の札と語りは一般的な言い方（本人の言葉 11-07「デモ動画は、僕の言葉の引用ではなく、一般的な言い方にしたい」・窓口の決め (1) A・(3)）。
# 前は哲学の記録と語りの全文に一字も違わない事を見ていた。今は、本人の言葉の印を付けない事と、一人称で本人を語らない事を見る
assert words.MARKED == (), "本人の言葉の印を付ける札は無い"
for name, chunks in {**words.CARDS, **words.TALKS}.items():
    assert all(s.strip() == s and s for lines in chunks for s in lines), name
    assert not any(w in words.flat(chunks) for w in ("僕", "ぼく", "私たち")), (name, "一人称で語らない")
# 職人の 1 文は本人の言葉（11-07 の (2) の決着）の字のまま
assert "職人も少なくなり、子供が簡単に手に入り遊べるおもちゃではなくなった。知らない大人がほとんどだ。" in words.flat(words.TALKS["talk_lost"])


# 語りの文を 1 字でも変えると落ちる。文の途中で終わるのも落ちる
assert not words.in_narration((("そこに喜びが、ある。",),)) and not words.in_narration((("そこに喜びが",),))
# 一字でも違えば落ちる。短く切った文も落ちる（切った文を本人の言葉と書かない）
lines = ("AIが良くなるのは副次的なもので、", "みんなが手で実際に作ること", "その楽しさに気づくことが最初。")  # 前の札の字（記録の引用の 1 行）
assert words.in_record(lines), "道具は前の札の字で記録と照らせる"
assert not words.in_record((lines[0].replace("副次的", "二次的"), *lines[1:]))
assert not words.in_record(lines[1:]), "切った文を通した"
assert not words.in_record(("手を動かす楽しさを忘れた人のために作っている。",))

# 語りは一般的な言い方（11-07）。前は本人の語りの全文（opening-narration.txt）と 1 字も違わない事を見ていた。
# 今は、かたまりの切れ目が読点か文の終わりで、かたまりが順に続いている事だけを見る
for name, chunks in words.TALKS.items():
    at = 0
    text_of = words.flat(chunks)
    for lines in chunks:
        piece = "".join(lines)
        assert piece[-1] in "、。", (name, piece)
        assert text_of.index(piece, at) == at, (name, piece)
        at += len(piece)
        assert all(s.strip() == s and s for s in lines), name

# 1 度に 1 かたまり、1 秒 5 字以下。足りない時は速めずに文を減らす
for name in words.ALL:
    cues = words.cues_of(name)
    assert list(cues.values()) == sorted(cues.values()), name
    assert words.seconds_of(name) * 10 == round(words.seconds_of(name) * 10), name
    starts = [cues[f"c{i}"][0] for i in range(len(words.chunks_of(name)))] + [words.seconds_of(name)]
    for i, lines in enumerate(words.chunks_of(name)):
        assert words.reading_chars("".join(lines)) / (starts[i + 1] - starts[i]) <= words.RATE + 1e-6, (name, lines)

# 問いは本人の決定（11-05）の文。言葉の記録の引用ではないので、本人の言葉の札と分ける
assert words.ASK == "あなたなら、何を作りますか。" and words.ASK not in rec_lines
assert all(v >= 0 for v in words.fits().values()), words.fits()

# つなぎの文は本人が決めた字のまま。本人の言葉の印を付けない
BRIDGE1 = "むかしの子どもも、今の子どもも、もらったおもちゃより、それを包んでいた紙やリボンのひもで遊んでしまうことがあります。"
assert words.flat(words.BRIDGE) == BRIDGE1 and "bridge" not in words.CARDS and BRIDGE1 not in rec_lines
assert words.flat(words.BRIDGE2) == "作ったものを持ちよると、Claude もそれを見て、次の型紙を少しずつよくしていきます。"
assert words.NOW_LINE == "いま作っているところです"
assert not {"bridge", "close", "core_loop"} & set(words.MARKED)
# 境目の札の字は本人の決定（11-06、カード 125217）のまま。本人の言葉の記録の引用ではないので、言葉の札の印を付けない。3 秒に入る
assert words.flat(words.BORDER) == "ここからは、裏のしくみ。" and words.ALL["border"] == words.BORDER
assert "border" not in words.MARKED and words.seconds_of("border") == 3.0
assert words.MARKED == (), "一般的な言い方にした（11-07）ので、本人の言葉の印を付ける札は無い"

# 終わりの字幕は初めと同じ字（本人の決定 11-05）。字幕 → 問いの順で終わる
assert script.SCENES[-2:] == ["close", "ask"]
assert flip.CLOSING == ("絵は動きを止めて残した。", "どう動いたかは、紙で作って確かめる。")
assert words.flat(words.ALL["close"]) == "".join(flip.CLOSING)

# 1 コマは時刻だけで決まる。1 度に 1 かたまりだけ（字は前が消えてから次が現れる）
pic = Image.new("RGBA", (300, 600), flip.SUMI + (255,))
for name in [*words.CARDS, "talk_toys", "talk_lost", "talk_physics", "talk_claude", "bridge", "close", "border"]:
    card = words.ChunkCard(name, words.cues_of(name), pic if name in words.PICTURED else None)
    for t in (0.0, 0.8, 3.0, card.duration - 0.1):
        a, b = card.frame(t), card.frame(t)
        assert a.size == (flip.W, flip.H) and a.tobytes() == b.tobytes(), (name, t)
    n = len(card.chunks)
    for t in [x / 4 for x in range(int(card.duration * 4))]:
        showing = sum(1 for i in range(n) if words.chunk_alpha(card.cues, n, i, t) > 0)
        assert showing <= 1, (name, t)
    # 字のそばに動く物を置かない（図が溶ける札のほかは、かたまりの間で絵が変わらない）
    if name not in words.PICTURED:
        mid = (card.cues["c0"][0] + card.cues["c1"][0]) / 2 if n > 1 else card.duration / 2
        assert card.frame(mid).tobytes() == card.frame(mid + 0.05).tobytes(), name
# 図の札: 失われる話の間に図が薄くなる（今の決定の形。見せ方の議論が決まるまで変えない）
lost = words.ChunkCard("talk_lost", words.cues_of("talk_lost"), pic)
# 図は真ん中に置く（11-07 の組み直し: 字は下の帯なので、図を右へ寄せない）
box = (words.W // 2 - 100, 300, words.W // 2 + 100, 700)
assert lost.frame(0.0).crop(box).getextrema()[0][0] < lost.frame(lost.duration - 0.1).crop(box).getextrema()[0][0]

# 問いの札は止まっている（考える間に動く物を置かない）
ask = words.AskCard(words.cues_of("ask"))
assert ask.frame(3.0).tobytes() == ask.frame(ask.duration - 0.1).tobytes()
assert ask.frame(0.0).tobytes() != ask.frame(3.0).tobytes()

# 記録を読む道も試す: 別のファイルの字と照らせる
with tempfile.TemporaryDirectory() as tmp:
    p = pathlib.Path(tmp) / "p.md"
    p.write_text("> 別の言葉\n", encoding="utf-8")
    assert words.in_record(("別の", "言葉"), p) and not words.in_record(lines, p)

# 継承を軸にする（本人の決定 11-05）: 札にも場面の字にも「復活」「取り戻」を出さない
for name, chunks in words.ALL.items():
    assert not words.says_restored(chunks), name
assert words.says_restored((("昔の作り方を", "取り戻した"),)) and words.says_restored((("おもちゃを復活させる",),))
for py in pathlib.Path(flip.__file__).parent.glob("*.py"):
    if py.name != "words.py":
        text = py.read_text(encoding="utf-8")
        assert not any(w in text for w in words.NOT_SAID), py.name
print("ok")
