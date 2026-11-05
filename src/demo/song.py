"""Suno の曲を受ける口: 音のファイルから拍を測り、場面の合図をその拍へ合わせる表を作る。

使い方: 本番は python -m demo.build --out <置き場> --song 曲.mp3 --music "クレジットの文" --rights "権利の文"
       拍だけを見るなら python -m demo.song 曲.mp3 （測った値を出すだけで、何も書かない）
exit: 0 = 測れた / 3 = 拍が読めない曲（揺れが大きい・短すぎる）/ 4 = ファイルが読めない・ffmpeg が無い。

決めた事と理由:
- 本人の決定（11-05）: 曲は本人が Suno で作って渡し、その曲の拍に場面の合図を合わせ直す。ここでは Suno を呼ばない。
- 拍は渡された音の実物から測る。曲の BPM を人が書き写すと、曲を差し替えた時に黙ってずれるため。
- 新しい依存を入れない（GPL を避ける決まりと、まっさらな clone で動かすため）。ffmpeg で読み、numpy だけで測る。
  音の立ち上がりの強さ → 自己相関で拍の長さ → 動的計画法で拍の位置（Ellis 2007 の考え方。コードは写していない）。
- 場面の境目は小節の頭へ、中の合図は一番近い拍へ寄せる。合図の時刻は動画の字と絵の動きが読む唯一の表なので、
  ここを動かせば絵と字が一緒に動く（frame(t) が CUES だけを読む作り）。
- 寄せる幅に上限を置く。遠くの拍へ大きく動かすと、字を読む間が崩れるため。寄せられない合図はそのまま残し、数を記録に出す。
- 拍が読めない曲で黙って書き出さない（3）。音ハメが効かないまま「合わせた」と言わないため。
"""
import json
import math
import shutil
import subprocess
import sys

import numpy as np

from demo.script import SCENES, load_scene

SR = 22050
HOP = 512
BPM_RANGE = (60.0, 180.0)
PRIOR_BPM = 110.0          # 拍の長さの候補が倍・半分で並ぶ時の寄せ先。歩く速さの近くを取る
MIN_SECONDS = 10.0
MIN_CLARITY = 1.3          # 拍の位置の立ち上がりが、全体の平均の何倍あれば拍が読めたと言うか
MAX_CUE_SHIFT = 0.45       # 合図を動かす上限（秒）
MAX_BAR_SHIFT = 1.5        # 場面の境目を小節の頭へ動かす上限（秒）。超える時は一番近い拍へ


class SongError(Exception):
    """exit の値を持つ。3 = 拍が読めない / 4 = 読めない。"""

    def __init__(self, code, why):
        super().__init__(why)
        self.code = code


def read_audio(path):
    if not shutil.which("ffmpeg"):
        raise SongError(4, "ffmpeg が無い")
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"], capture_output=True)
    if r.returncode != 0 or not r.stdout:
        raise SongError(4, f"音が読めない: {path}")
    return np.frombuffer(r.stdout, dtype="<i2").astype(np.float32) / 32768


def onset_strength(x):
    """音の立ち上がりの強さの列。周波数ごとの増えた分だけを足す（減る所を数えない）。"""
    size = 1024
    n = max(0, (len(x) - size) // HOP + 1)
    if n < 2:
        return np.zeros(1)
    win = np.hanning(size)
    frames = np.stack([x[i * HOP:i * HOP + size] * win for i in range(n)])
    mag = np.log1p(np.abs(np.fft.rfft(frames, axis=1)) * 10)
    env = np.maximum(0.0, np.diff(mag, axis=0)).sum(axis=1)
    # 少しならす。クリックのような細い立ち上がりは、拍の長さがコマの刻みの整数でない時に自己相関の頂が割れ、
    # 2 拍分の頂の方が高くなって半分の BPM に読んでしまう（120 BPM のクリックで 60 と出た）。
    kernel = np.hanning(9)
    env = np.convolve(np.concatenate([[0.0], env]), kernel / kernel.sum(), mode="same")
    return env / (env.max() or 1.0)


def beat_period(env):
    """自己相関から 1 拍のコマ数を返す。倍と半分で迷う時は PRIOR_BPM の近くを取る。"""
    rate = SR / HOP
    env0 = env - env.mean()
    ac = np.fft.irfft(np.abs(np.fft.rfft(env0, 2 * len(env0))) ** 2)[:len(env0)]
    lo, hi = int(rate * 60 / BPM_RANGE[1]), min(len(ac) - 2, int(rate * 60 / BPM_RANGE[0]) + 1)
    if hi <= lo:
        raise SongError(3, "短すぎて拍の長さを測れない")
    lags = np.arange(lo, hi)
    bpm = 60 * rate / lags
    prior = np.exp(-0.5 * (np.log2(bpm / PRIOR_BPM) / 0.9) ** 2)
    i = int(np.argmax(ac[lo:hi] * prior)) + lo
    # 頂の前後 3 点でならして、コマの刻みより細かく読む
    a, b, c = ac[i - 1], ac[i], ac[i + 1]
    d = a - 2 * b + c
    return i + (0.5 * (a - c) / d if d else 0.0)


def track(env, period, tight=120.0):
    """拍の位置を動的計画法で選ぶ。立ち上がりの強さと、拍の長さの揃い方の両方を見る。"""
    n = len(env)
    score, back = env.astype(float).copy(), np.full(n, -1)
    lo, hi = max(1, round(period * 0.5)), round(period * 2)
    steps = np.arange(lo, hi + 1)
    penalty = -tight * np.log(steps / period) ** 2
    for i in range(lo, n):
        prev = i - steps
        ok = prev >= 0
        cand = score[prev[ok]] + penalty[ok]
        j = int(np.argmax(cand))
        if cand[j] > 0:
            score[i] += cand[j]
            back[i] = prev[ok][j]
    # 終わりの近くで一番良い所から辿る
    tail = max(0, n - round(period * 2))
    i = tail + int(np.argmax(score[tail:]))
    out = []
    while i >= 0:
        out.append(i)
        i = int(back[i])
    return np.array(out[::-1])


def bar_starts(beats, env):
    """4 拍ごとの頭。立ち上がりが一番強くなる並びを選ぶ（曲の小節の頭は強く入る事が多い。外れても 4 拍の刻みには乗る）。"""
    best = max(range(4), key=lambda k: float(env[beats[k::4]].sum()) if len(beats[k::4]) else -1.0)
    return beats[best::4]


def measure(path):
    """音のファイルから拍を測る。{bpm, beats, bars, seconds, clarity}。読めない時は SongError。"""
    x = read_audio(path)
    seconds = len(x) / SR
    if seconds < MIN_SECONDS:
        raise SongError(3, f"曲が短すぎる（{seconds:.1f} 秒）")
    env = onset_strength(x)
    if env.max() <= 0:
        raise SongError(3, "音の立ち上がりが無い")
    period = beat_period(env)
    frames = track(env, period)
    if len(frames) < 4:
        raise SongError(3, "拍の位置を拾えない")
    clarity = float(env[frames].mean() / (env.mean() or 1.0))
    if clarity < MIN_CLARITY:
        raise SongError(3, f"拍がはっきりしない（立ち上がりの比 {clarity:.2f}）")
    rate = SR / HOP
    to_sec = lambda f: [round((int(i) * HOP + 512) / SR, 4) for i in f]  # 窓の真ん中の時刻にする
    # 真ん中の値でなく平均を使う。拍の長さがコマの刻みの整数でない時、幅は 21 と 22 を行き来し、真ん中の値は 2% ずれる。
    mean_width = float(frames[-1] - frames[0]) / (len(frames) - 1)
    return {"bpm": round(60 * rate / mean_width, 2), "beats": to_sec(frames), "bars": to_sec(bar_starts(frames, env)),
            "seconds": round(seconds, 3), "clarity": round(clarity, 2)}


def _nearest(values, t):
    i = int(np.searchsorted(values, t))
    near = [values[j] for j in (i - 1, i) if 0 <= j < len(values)]
    return min(near, key=lambda v: abs(v - t)) if near else None


def align(seconds, cues, beats, bars):
    """場面の長さと合図を、曲の拍へ寄せた表を返す（入力は変えない）。

    seconds: {場面: 秒}。cues: {場面: {合図: (始め, 終わり)}}。場面の順は SCENES。
    返す物: {"seconds": {場面: 秒}, "cues": {場面: {合図: (始め, 終わり)}}, "moved": 動かした数, "left": 寄せられなかった数}
    """
    names = [n for n in SCENES if n in seconds]
    edges, t = [0.0], 0.0
    for n in names:
        t += seconds[n]
        edges.append(t)
    snapped = [0.0]
    for edge in edges[1:-1]:
        bar, beat = _nearest(bars, edge), _nearest(beats, edge)
        to = bar if bar is not None and abs(bar - edge) <= MAX_BAR_SHIFT else beat if beat is not None and abs(beat - edge) <= MAX_CUE_SHIFT else edge
        snapped.append(max(to, snapped[-1] + 1.0))
    snapped.append(snapped[-1] + seconds[names[-1]])  # 最後の場面（問いの札）は長さを変えない
    out, moved, left = {}, 0, 0
    for k, n in enumerate(names):
        start, length = snapped[k], snapped[k + 1] - snapped[k]
        out[n], prev = {}, 0.0
        for cue, (a, b) in cues[n].items():
            if a == 0.0:  # 場面の頭の合図は境目（小節の頭）に乗っている
                out[n][cue] = (a, b)
                continue
            near = _nearest(beats, start + a)
            if near is not None and abs(near - (start + a)) <= MAX_CUE_SHIFT:
                moved += 1
                a2 = near - start
            else:
                left += 1
                a2 = a
            a2 = max(a2, prev)  # 順を崩さない
            prev = a2
            out[n][cue] = (round(a2, 4), round(min(a2 + (b - a), max(length, a2 + 0.01)), 4))
    return {"seconds": {n: round(snapped[i + 1] - snapped[i], 4) for i, n in enumerate(names)}, "cues": out, "moved": moved, "left": left}


def apply_cues(table):
    """合わせた時刻を場面の合図の表へ書き込む。frame(t) は CUES を読むので、絵と字が一緒に動く。"""
    for name, cues in table["cues"].items():
        load_scene(name).CUES.update(cues)


def table_json(measured, table, **extra):
    return json.dumps({"kind": "song", "bpm": measured["bpm"], "clarity": measured["clarity"], "seconds": measured["seconds"],
                       "beats": measured["beats"], "bars": measured["bars"], "scene_seconds": table["seconds"], "cues": table["cues"],
                       "moved": table["moved"], "left": table["left"], **extra}, ensure_ascii=False, indent=1) + "\n"


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print(__doc__.splitlines()[2], file=sys.stderr)
        return 4
    try:
        m = measure(argv[0])
    except SongError as e:
        print(f"{'FAIL D.song' if e.code == 3 else '検査できない:'} {e}", file=sys.stderr)
        return e.code
    print(f"{m['bpm']} BPM・拍 {len(m['beats'])}・小節 {len(m['bars'])}・{m['seconds']} 秒・立ち上がりの比 {m['clarity']}")
    gap = 60 / m["bpm"]
    print(f"1 拍 {gap:.3f} 秒・はじめの拍 {m['beats'][0]} 秒" + (f"（{math.floor(m['seconds'] / gap)} 拍分の長さ）" if gap else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
