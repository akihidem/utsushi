"""届いたら差し込む物（手だけの映像・本人の声の語り）と、語りの間だけ曲を下げる決まりの床。

本人の決定（11-06）: 手だけを撮って語りの場面の後ろに敷く。語りは本人が自分の声で読む。どちらもまだ届いていない。
見る事: 置き場の名前が撮る物の一覧・語りを読む 1 枚と同じ／届いていない間は今の映す物のまま、記録に「待ち」と残す／
届いた手の映像は字の左を紙で薄くして敷く／声は場面の時刻に置き、場面の秒に入らない時は名指しして止める（速めない）／
声の間だけ曲を下げる。本物の手と声はまだ無いので、作り物の絵と音で見る。
"""
import math
import pathlib
import shutil
import subprocess
import tempfile

from PIL import Image

from demo import assemble, build, flip, script, words

# 1. 置き場の名前は、撮る物の一覧（手 A〜E）と語りを読む 1 枚（声 A1〜A6）のまま。どの場面も台本にある
hands = [n for kinds in script.SLOTS.values() for n, _ in kinds.get("hands", ())]
voices = [n for kinds in script.SLOTS.values() for n in kinds.get("voice", ())]
# 13 の手は D・E に加えて、作った物の手のひら（F）と、原画（H）→ 型紙（I）の 2 枚（窓口の決定 11-07。13 の 16 秒は変えない）
assert hands == ["A", "B", "C", "D", "E", "F", "H", "I"] and voices == ["A1", "A2", "A3", "A4", "A5", "A6"]
assert sum(s for _, s in script.SLOTS["talk_physics"]["hands"]) == script.load_scene("talk_physics").DURATION
assert set(script.SLOTS) <= set(script.SCENES)
# 声は語りの場面だけ。文の数は札の文の数と同じ（1 文 1 ファイル）
for name, kinds in script.SLOTS.items():
    assert name.startswith("talk_") or name == "scene2", name
    assert len(kinds.get("voice", ())) == len(words.sentences_of(words.TALKS[name])), name
    # 手の映像の秒の和は場面の秒に入る（手は場面の頭から敷く）
    assert sum(s for _, s in kinds.get("hands", ())) <= script.load_scene(name).DURATION + 1e-9, name
# 置き場は git の外
assert script.SLOT_DIR.split("/")[0] == "out"

# 2. 届いていない間: 記録は全部「待ち」で、今の映す物のまま（手を敷く札の絵は、手を渡さない札と同じ）
with tempfile.TemporaryDirectory() as tmp:
    rec = build.slot_record(tmp)
    assert all(v == "待ち" for kinds in rec.values() for got in kinds.values() for v in got.values()), rec
    assert len(build.waiting(rec)) == len(hands) + len(voices)
    # 1 つ届くと、その分だけ sha256 が残り、待ちから外れる
    slot = pathlib.Path(tmp) / script.SLOT_DIR
    slot.mkdir(parents=True)
    (slot / "A1.m4a").write_bytes(b"voice")
    rec = build.slot_record(tmp)
    assert rec["talk_toys"]["voice"]["A1"]["sha256"] == build.file_sha(slot / "A1.m4a")
    assert "声 A1（talk_toys）" not in build.waiting(rec) and "声 A2（talk_toys）" in build.waiting(rec)
plain = words.ChunkCard("talk_physics", words.cues_of("talk_physics"))
empty = words.ChunkCard("talk_physics", words.cues_of("talk_physics"), hands=[([], 0.0, 5.0)])
assert plain.frame(2.0).tobytes() == empty.frame(2.0).tobytes() and empty.cx == plain.cx

# 3. 届いた手の映像: 敷いた間は右に映像が出て、左は紙の色が掛かって字が読める。敷き終えた後は今の地に戻る
with tempfile.TemporaryDirectory() as tmp:
    frames = []
    for i in range(3):
        p = pathlib.Path(tmp) / f"{i:05d}.jpg"
        Image.new("RGB", (flip.W, flip.H), (40 + i * 60, 90, 60)).save(p)
        frames.append(p)
    card = words.ChunkCard("talk_physics", words.cues_of("talk_physics"), hands=[(frames, 0.0, 5.0), (frames, 5.0, 8.0)])
    assert card.cx == words.HANDS_STYLE["cx"] and card.size == words.HANDS_STYLE["size"], "手を敷く札は字を左に寄せる"
    # 見る点は高さ 300。上の帯（0〜112）は公的調査の数の行の所で、手の映像の時は紙の色を掛けるため（本人の決定 11-06・置き場 A）
    on = card.frame(2.0)
    assert on.tobytes() == card.frame(2.0).tobytes(), "1 コマは時刻だけで決まる"
    right, left = on.getpixel((1800, 300)), on.getpixel((20, 300))
    assert abs(right[0] - flip.PAPER[0]) > 60, ("右に手の映像が出る", right)
    assert all(abs(left[k] - flip.PAPER[k]) < 30 for k in range(3)), ("左は紙の色が掛かる", left)
    assert card.frame(0.0).getpixel((1800, 300)) == flip.PAPER, "紙の地から溶けて現れる"
    late = card.frame(card.duration - 0.1)
    assert late.getpixel((1800, 300)) == flip.PAPER and late.getpixel((20, 300)) == flip.PAPER, "使い切った後は今の地"
    # 図を右に置く札でも、手が届けば図の代わりに手を敷く（両方は置かない）
    pic = Image.new("RGBA", (300, 600), flip.SUMI + (255,))
    toys = words.ChunkCard("talk_toys", words.cues_of("talk_toys"), pic, hands=[(frames, 0.0, 6.0)])
    assert toys.frame(3.0).getpixel((words.PIC_X, flip.H // 2)) != flip.SUMI
# 字は手を敷く置き方でも切れない
assert all(v >= 0 for k, v in words.fits().items() if k.endswith("+hands")), words.fits()

# 4. 手の映像の決まり（横 16:9・幅 1280 以上・使う秒以上）。合わない物は理由を言う
assert words.hands_problem("x", 6.0, probe=lambda p: (1920, 1080, 20.0)) is None
assert "幅" in words.hands_problem("x", 6.0, probe=lambda p: (1080, 608, 20.0))
assert "16:9" in words.hands_problem("x", 6.0, probe=lambda p: (1920, 1440, 20.0))
assert "短い" in words.hands_problem("x", 6.0, probe=lambda p: (1920, 1080, 3.0))
assert "読めない" in words.hands_problem("x", 6.0, probe=lambda p: None)

# 5. 声の置き方: 場面の頭から順に置く。入らない時は、その場面の声を同じ倍率で 1.08 倍まで速める（統括の決め 11-06）。
#    それでも入らない時は名指しして止める
with tempfile.TemporaryDirectory() as tmp:
    slot = pathlib.Path(tmp) / script.SLOT_DIR
    slot.mkdir(parents=True)
    for n in ("A1", "A2", "A4"):
        (slot / f"{n}.m4a").write_bytes(n.encode())
    keep = assemble.duration
    lengths = {"A1": 8.0, "A2": 2.0, "A4": 22.0}
    assemble.duration = lambda p: lengths.get(pathlib.Path(p).stem)
    try:
        order = ["opening", "talk_toys", "talk_lost", "scene2"]
        secs = [8.6, 11.8, 12.2, 24.0]
        got, duck, problem = build.place_voices(order, secs, tmp)
        assert problem is None, problem
        assert [(pathlib.Path(f).stem, at, sp) for f, at, sp in got] == [("A1", 8.8, 1.0), ("A2", 17.1, 1.0), ("A4", 32.8, 1.0)], got
        assert duck == [(8.8, 19.1), (32.8, 54.8)], duck
        lengths["A4"] = 25.0  # 場面 2 の 24 秒に入らないが、1.05 倍で入る
        got, duck, problem = build.place_voices(order, secs, tmp)
        assert problem is None and math.isclose(got[-1][2], 25.0 / 23.8, abs_tol=1e-3) and duck[-1] == (32.8, 56.6), (got, duck)
        lengths["A4"] = 26.0  # 1.08 倍でも入らない
        got, duck, problem = build.place_voices(order, secs, tmp)
        assert got == [] and "A4" in problem and "scene2" in problem and "1.08" in problem, problem
    finally:
        assemble.duration = keep

# 5b. 本物の ffmpeg で、本人に頼んだ録り方の 2 つの形を見る（作り物の音）
#   形 1: 録り始めと終わりに 2 秒ずつ黙った声。黙りを切ると入る（切らないと 1.08 倍でも入らない長さ）
#   形 2: 語りを読む 1 枚の目安（1 秒 5 字）ちょうどの声に、前後 2 秒の黙り。6 文とも、今の台本の秒に入る
if shutil.which("ffmpeg"):
    def padded(path, seconds, pad=2.0):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"anullsrc=r=48000:cl=mono:d={pad}",
                        "-f", "lavfi", "-i", f"sine=f=330:d={seconds}:sample_rate=48000", "-f", "lavfi", "-i", f"anullsrc=r=48000:cl=mono:d={pad}",
                        "-filter_complex", "[0][1][2]concat=n=3:v=0:a=1", "-c:a", "aac", str(path)], check=True)

    with tempfile.TemporaryDirectory() as tmp:
        slot = pathlib.Path(tmp) / script.SLOT_DIR
        slot.mkdir(parents=True)
        padded(slot / "A3.m4a", 11.0)
        assert assemble.duration(slot / "A3.m4a") > 14.9, "黙りつきの長さは 15 秒（talk_lost の 12.2 秒に 1.08 倍でも入らない）"
        cut = build.trim_voice(slot / "A3.m4a", pathlib.Path(tmp) / "cut.wav")
        assert cut is not None and 10.9 < assemble.duration(cut) < 11.0 + 2 * build.SILENCE_KEEP + 0.15, assemble.duration(cut)
        got, duck, problem = build.place_voices(["talk_lost"], [12.2], tmp, into=pathlib.Path(tmp) / "voice")
        assert problem is None and pathlib.Path(got[0][0]).parent.name == "voice" and got[0][2] <= build.MAX_SPEED, (got, problem)
        _, _, problem = build.place_voices(["talk_lost"], [12.2], tmp)  # 黙りを切らない置き方なら止まる
        assert problem and "A3" in problem, problem

    with tempfile.TemporaryDirectory() as tmp:
        slot = pathlib.Path(tmp) / script.SLOT_DIR
        slot.mkdir(parents=True)
        target = {}
        for name, kinds in script.SLOTS.items():
            sents = words.sentences_of(words.TALKS[name])
            for v, sent in zip(kinds.get("voice", ()), sents):
                target[v] = round(words.reading_chars(sent) / words.RATE, 1)
                padded(slot / f"{v}.m4a", target[v])
        assert target == {"A1": 9.2, "A2": 1.8, "A3": 11.6, "A4": 23.4, "A5": 14.8, "A6": 3.8}, target
        lengths = [script.load_scene(n).DURATION for n in script.SCENES]
        got, duck, problem = build.place_voices(script.SCENES, lengths, tmp, into=pathlib.Path(tmp) / "voice")
        assert problem is None, problem
        assert [pathlib.Path(f).stem.split("-")[0] for f, _, _ in got] == ["A1", "A2", "A3", "A4", "A5", "A6"]
        assert all(sp <= 1.02 for _, _, sp in got), [sp for _, _, sp in got]  # 目安ちょうどなら、ほとんど速めない
        # 速めた声は、その倍率の長さになっている（高さを変えない atempo）
        for f, _, sp in got:
            if sp > 1.0:
                assert "-x" in pathlib.Path(f).name and abs(assemble.duration(f) * sp - assemble.duration(pathlib.Path(tmp) / "voice" / f"{pathlib.Path(f).stem.split('-')[0]}.wav")) < 0.1

# 6. 曲を下げる式: 声の間は DUCK_DB、離れた所は元の大きさ、前後はなだらか
assert assemble.duck_gain([]) is None
expr = assemble.duck_gain([(9.0, 19.3), (33.0, 55.0)])
gain = lambda t: eval(expr, {"clip": lambda x, a, b: max(a, min(b, x)), "min": min, "t": t})  # noqa: E731
low = 10 ** (assemble.DUCK_DB / 20)
assert math.isclose(gain(12.0), low, abs_tol=1e-3) and math.isclose(gain(40.0), low, abs_tol=1e-3)
assert gain(0.0) == 1.0 and gain(25.0) == 1.0 and gain(60.0) == 1.0
assert low < gain(8.8) < 1.0, "下げる前になだらかに下げる"

# 7. 本物の ffmpeg で、声を重ねて曲を下げてつなげる（作り物の短い場面・音で）
if shutil.which("ffmpeg"):
    with tempfile.TemporaryDirectory() as tmp:
        t = pathlib.Path(tmp)
        for i in range(2):
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=gray:s=320x180:d=1.5:r=30", f"{t}/s{i}.mp4"], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=f=220:d=3", f"{t}/beat.wav"], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=f=660:d=0.6", "-c:a", "aac", f"{t}/A1.m4a"], check=True)
        rc = assemble.assemble([t / "s0.mp4", t / "s1.mp4"], t / "out.mp4", t / "beat.wav", voices=[(t / "A1.m4a", 1.6)], duck=[(1.6, 2.2)])
        assert rc == 0, rc
        streams = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(t / "out.mp4")],
                                 capture_output=True, text=True).stdout.split()
        assert sorted(streams) == ["audio", "video"], streams
        assert abs(assemble.duration(t / "out.mp4") - 3.0) < 0.1
print("ok 届いたら差し込む物は待ちと残り、届けば手を敷き声を置いて、声の間だけ曲を下げる")
