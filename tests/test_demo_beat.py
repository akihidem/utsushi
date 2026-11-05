"""デモ動画の仮の拍（demo.beat）の床: どの合図も拍の上に乗る事、問いの後は鳴らない事、同じ入力で同じ音になる事を見る。

動画は作らない（数秒で済ませ、音の作りだけを見るため）。耳で聞く確かめの代わりにはならない。音の良し悪しは人が聞いて決める。
"""
import tempfile
import pathlib
import wave

import numpy as np

from demo import beat
from demo.build import SCENES

seconds = {n: __import__(f"demo.{n}", fromlist=["DURATION"]).DURATION for n in SCENES}
points, total = beat.anchors(seconds)
assert total == sum(seconds.values()) and total <= 180, total
times = [p["t"] for p in points]
assert times == sorted(times) and all(b - a >= beat.MIN_GAP for a, b in zip(times, times[1:]))

# どの合図も拍の上に乗る。間の拍の幅は、基の拍から大きく外れない（半拍より短い間だけは束ねた分として許す）
beats = beat.beat_map(times)
assert all(t in beats for t in times)
widths = np.diff(beats)
assert (widths <= beat.BEAT * 1.5).all(), widths.max()

mix, table = beat.compose(seconds)
assert table["note"].startswith("仮の拍") and "Suno の曲ではない" in table["note"], "Suno の曲に見せない"
assert abs(np.max(np.abs(mix)) - beat.TOP) < 1e-6, "割れないように頭を揃える"
assert mix.shape[0] == int(beat.SR * total) + 1
assert table["stop"] == next(p["t"] for p in points if (p["scene"], p["cue"]) == beat.END)
# 問いの札の後は、最後に鳴らした音の余韻の後、無音になる（考える間を音で埋めない）
tail = mix[int(beat.SR * (table["stop"] + 2.0)):]
assert np.max(np.abs(tail)) < 1e-3, np.max(np.abs(tail))
# 問いの前は鳴っている
assert np.sqrt(np.mean(mix[:int(beat.SR * 15)] ** 2)) > 0.01
# 1 枚ごとの刻みの数は絵の側の数と同じ
assert len(table["ticks"]) == sum(c for _, _, c in beat.RUNS)
# 同じ入力なら同じ音（動画と同じく、作り直しても同じ物が出る）
again, _ = beat.compose(seconds)
assert again.tobytes() == mix.tobytes()

with tempfile.TemporaryDirectory() as tmp:
    path = pathlib.Path(tmp) / "b.wav"
    beat.write_wav(mix, path)
    with wave.open(str(path)) as w:
        assert w.getframerate() == beat.SR and w.getnchannels() == 1 and w.getnframes() == mix.shape[0]
print("ok")
