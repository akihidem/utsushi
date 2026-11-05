"""Suno の曲を受ける口（demo.song）の床: 合成のクリック音の拍を実物の音から測れる事と、合図の寄せ方を見る。

本物の Suno は呼ばない。音は試験の中で作り、ffmpeg で読み直して測る（本番と同じ道を通すため）。
"""
import pathlib
import subprocess
import tempfile
import wave

import numpy as np

from demo import song
from demo.script import SCENES, load_scene


def click_track(path, bpm, seconds, sr=44100, first=0.5, swing=0.0):
    """拍ごとに短いクリック。4 拍ごとを強くする（小節の頭）。"""
    x = np.zeros(int(sr * seconds))
    gap, t, k = 60 / bpm, first, 0
    times = []
    while t < seconds - 0.1:
        at = t + (swing if k % 2 else 0.0)
        n = int(sr * 0.02)
        i = int(at * sr)
        x[i:i + n] += (1.0 if k % 4 == 0 else 0.45) * np.sin(2 * np.pi * 1800 * np.arange(n) / sr) * np.exp(-np.arange(n) / sr / 0.004)
        times.append(at)
        t += gap
        k += 1
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())
    return times


with tempfile.TemporaryDirectory() as tmp:
    tmp = pathlib.Path(tmp)
    for bpm in (90, 120, 150):
        p = tmp / f"c{bpm}.wav"
        truth = click_track(p, bpm, 30)
        m = song.measure(p)
        assert abs(m["bpm"] - bpm) / bpm < 0.02, (bpm, m["bpm"])
        # 測った拍は、本当のクリックから 30 ミリ秒以内（窓の刻みの分だけのずれを許す）
        worst = max(min(abs(b - c) for c in truth) for b in m["beats"])
        assert worst < 0.03, (bpm, worst)
        assert len(m["beats"]) >= len(truth) - 2, (len(m["beats"]), len(truth))
        # 小節の頭は強いクリックに乗る
        strong = truth[::4]
        assert max(min(abs(b - c) for c in strong) for b in m["bars"]) < 0.03, bpm
    # mp3 でも読める（Suno の曲は mp3 で来る見込み）。ffmpeg で読むので形を問わない
    mp3 = tmp / "c.mp3"
    if subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(tmp / "c120.wav"), str(mp3)], capture_output=True).returncode == 0:
        assert abs(song.measure(mp3)["bpm"] - 120) < 2.4

    # 拍が読めない音は 3、読めないファイルは 4。黙って合わせた振りをしない
    silent = tmp / "s.wav"
    with wave.open(str(silent), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(44100)
        w.writeframes(b"\0\0" * 44100 * 15)
    short = tmp / "short.wav"
    click_track(short, 120, 4)
    noise = tmp / "n.wav"
    with wave.open(str(noise), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(44100)
        w.writeframes((np.random.default_rng(1).normal(0, 0.2, 44100 * 15).clip(-1, 1) * 32767).astype("<i2").tobytes())
    for bad, code in ((silent, 3), (short, 3), (noise, 3), (tmp / "無い.mp3", 4)):
        try:
            song.measure(bad)
        except song.SongError as e:
            assert e.code == code, (bad, e.code)
        else:
            raise AssertionError(f"通ってしまった: {bad}")
    assert song.main([str(tmp / "無い.mp3")]) == 4
    assert song.main([str(tmp / "c120.wav")]) == 0

# 寄せ方: 全部の場面の合図を、100 BPM の拍へ
gap = 0.6
beats = [round(0.1 + gap * i, 4) for i in range(320)]
bars = beats[::4]
seconds = {n: load_scene(n).DURATION for n in SCENES}
cues = {n: dict(load_scene(n).CUES) for n in SCENES}
before = {n: dict(c) for n, c in cues.items()}
table = song.align(seconds, cues, beats, bars)
assert cues == before, "入力を変えない"
starts, t = {}, 0.0
for n in SCENES:
    starts[n] = t
    t += table["seconds"][n]
assert abs(t - sum(seconds.values())) < 3 * song.MAX_BAR_SHIFT and t <= 180
# 場面の境目は小節の頭（最初を除く）
for n in SCENES[1:]:
    assert min(abs(starts[n] - b) for b in bars) < 1e-3, n
# 問いの札の長さは変えない（考える間を削らない）
assert table["seconds"]["ask"] == seconds["ask"]
# どの合図も拍の上に乗る。場面の頭の合図は 0 のまま。順は崩れない
for n in SCENES:
    order = [a for a, _ in table["cues"][n].values()]
    assert order == sorted(order), n
    for cue, (a, b) in table["cues"][n].items():
        assert b > a, (n, cue)
        if a > 0:
            assert min(abs(starts[n] + a - x) for x in beats) < 1e-3 or table["left"] > 0, (n, cue)
assert table["moved"] > 40 and table["left"] == 0, (table["moved"], table["left"])
# 寄せる幅の上限を超えない（字を読む間を崩さない）
for n in SCENES:
    for cue, (a, _) in table["cues"][n].items():
        if a > 0:
            assert abs(a - cues[n][cue][0]) <= song.MAX_CUE_SHIFT + song.MAX_BAR_SHIFT + 0.01, (n, cue)

# 合わせた時刻は場面の表へ入り、札の絵が読む（words は同じ dict を返す）。戻して他の試験に響かせない
song.apply_cues({"cues": {"ask": {"in": (0.0, 2.0)}}})
assert load_scene("ask").CUES["in"] == (0.0, 2.0)
song.apply_cues({"cues": {"ask": before["ask"]}})
print("ok")
