"""デモ動画の仮の拍: 場面の合図の時刻に拍を置いた音を、コードだけで作る。

使い方: python -m demo.beat --run <demo.build の置き場>   （中の build.json の場面の長さを読み、beat.wav と beats.json を書く）
exit: 0 = 書き出せた / 4 = build.json が読めない・場面が無い（このリポの検査の決まりに合わせる）。

なぜ要るか: 本人の案は Suno の音ハメ（docs/demo/plan.md の 3）。Suno を動かすのは外に出る操作と課金で、本人の判断を待っている。
本人の頼み（11-05）「現状でデモ動画作成してみて」に今ある物で答えるため、音ハメの動きだけを先に見せる仮の音を作る。
Suno の曲に見せないよう、クレジットには「仮の拍」と書く（build の --music）。曲が来たらこの音は捨てる。

決めた事と理由:
- 拍を映像に合わせる（plan.md の案は逆で、曲の拍へ CUES を合わせる）。曲が無い今は映像の合図の方が決まっているため。
  合図と合図の間を、90 拍毎分に一番近い整数で割る。どの合図も必ず拍の上に乗り、割り切れない分は間ごとに速さをわずかに動かして吸う。
- 90 拍毎分にしたのは、場面 1 の重ねる速さ（1 秒に 6 枚）が 16 分音符とちょうど重なるため。
- 枠が 1 人ずつ付く所・重ねる所・並ぶ所は、1 枚ごとに木の音を鳴らす（RUNS）。絵の動きと音が 1 対 1 で合うのが音ハメの芯なので。
- 問いの札（場面 7 の ask）から後は鳴らさない。見ている人が考える間を、音で埋めないため。
- 同じ入力から同じ音を作る（乱数の種を固定）。動画と同じく、作り直しても同じ物が出るように。
- 声は入れない（J-022）。楽器の音だけで、外の音源を使わない（権利の確かめが要らないように）。
"""
import argparse
import importlib
import json
import pathlib
import sys
import wave

import numpy as np

from demo.build import SCENES

SR = 44100
BEAT = 60 / 90          # 1 拍の秒。16 分音符が 1/6 秒で、場面 1 の 1 秒 6 枚と重なる
MIN_GAP = 0.3           # これより近い合図は 1 つに束ねる（拍が詰まって聞き取れなくなるため）
# 陰音階（都節）に寄せた 5 音。江戸の絵に合う響きとして選んだ（試し聞きはできていないので、音の良し悪しは人が聞いて決める）。
SCALE = (146.83, 155.56, 196.00, 220.00, 233.08, 293.66, 311.13, 392.00)
MOTIF = (0, 2, 3, 2, 4, 3, 2, 1)
# 場面ごとの濃さ。話の山（場面 4・6）で少し濃くする。
LEVEL = {"flip": 0.6, "scene2": 0.4, "scene3": 0.6, "scene4": 0.85, "scene5": 0.7, "scene6": 0.85, "scene7": 0.6}
# 1 枚ごとに木の音を鳴らす所: (場面, 合図, 枚数)。枚数は絵の側の数と同じ（18 人。flip の重ねは 1 秒 6 枚 × 6 秒）。
RUNS = (("flip", "boxes", 18), ("flip", "flip", 36), ("scene7", "figs_in", 18))
STRONG = ("page_in", "persp_in", "title_in", "quote1", "figs_in", "closing", "caption")
END = ("scene7", "ask")  # ここで音を止める


def anchors(seconds):
    """場面の長さ {名: 秒} から、動画全体の時刻の合図の表を作る。近すぎる合図は前の方に束ねる。"""
    out, t0 = [], 0.0
    for name in SCENES:
        if name not in seconds:
            raise KeyError(name)
        cues = importlib.import_module(f"demo.{name}").CUES
        for cue, (a, _) in cues.items():
            out.append({"t": round(t0 + a, 4), "scene": name, "cue": cue})
        t0 += seconds[name]
    out.sort(key=lambda x: x["t"])
    kept = []
    for x in out:
        if not kept or x["t"] - kept[-1]["t"] >= MIN_GAP:
            kept.append(x)
    return kept, t0


def beat_map(points):
    """合図の時刻の並びから、拍の時刻の並びを作る。どの合図も拍の上に乗る。"""
    beats = []
    for a, b in zip(points, points[1:]):
        n = max(1, round((b - a) / BEAT))
        beats += [a + (b - a) * i / n for i in range(n)]
    return beats + points[-1:]


def _tone(n, freq, tau):
    t = np.arange(n) / SR
    return np.sin(2 * np.pi * freq * t) * np.exp(-t / tau)


def wood(rng):
    """拍子木に似せた短い音。1 枚ごとの刻みに使う。"""
    n = int(SR * 0.08)
    return 0.7 * _tone(n, 1250, 0.012) + 0.3 * _tone(n, 2100, 0.008) + 0.15 * rng.standard_normal(n) * np.exp(-np.arange(n) / SR / 0.004)


def drum():
    """太鼓に似せた低い音。場面の頭と締めに使う。音の高さを落として、胴の鳴りに見せる。"""
    n = int(SR * 0.9)
    t = np.arange(n) / SR
    freq = 58 + 40 * np.exp(-t / 0.05)
    return np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-t / 0.28)


def pluck(freq, rng):
    """弦を弾いた音（Karplus-Strong）。箏や三味線の代わりで、外の音源を使わないため。"""
    n, period = int(SR * 1.2), max(2, int(SR / freq))
    buf = rng.uniform(-1, 1, period)
    out = np.zeros(n)
    for i in range(n):
        out[i] = buf[i % period]
        buf[i % period] = 0.498 * (buf[i % period] + buf[(i + 1) % period])
    return out


def _add(mix, t, sound, gain):
    i = int(round(t * SR))
    if i >= len(mix):
        return
    m = min(len(sound), len(mix) - i)
    mix[i:i + m] += gain * sound[:m]


def compose(seconds, seed=7):
    """音の配列（-1〜1 の mono）と、拍の表（beats.json の中身）を返す。同じ入力なら同じ音。"""
    points, total = anchors(seconds)
    stop = next(p["t"] for p in points if (p["scene"], p["cue"]) == END)
    times = [p["t"] for p in points if p["t"] <= stop]
    beats = [b for b in beat_map(times) if b <= stop]
    rng = np.random.default_rng(seed)
    mix = np.zeros(int(SR * total) + 1)
    plucks = {f: pluck(f, rng) for f in SCALE}
    wood_hit, drum_hit = wood(rng), drum()

    def scene_at(t):
        t0 = 0.0
        for name in SCENES:
            t0 += seconds[name]
            if t < t0:
                return name
        return SCENES[-1]

    for i, b in enumerate(beats):
        level = LEVEL[scene_at(b)]
        note = SCALE[MOTIF[i % len(MOTIF)] + (SCENES.index(scene_at(b)) % 3)]
        _add(mix, b, plucks[note], 0.32 * level)
        if i % 4 == 0:
            _add(mix, b, drum_hit, 0.35 * level)
    for p in points:
        if p["t"] > stop:
            continue
        strong = p["cue"] in STRONG or p["cue"] == END[1]
        _add(mix, p["t"], drum_hit, 0.75 if strong else 0.35)
        _add(mix, p["t"], plucks[SCALE[5]], 0.4 if strong else 0.2)
    ticks = []
    starts = {(p["scene"], p["cue"]): p["t"] for p in points}
    for scene, cue, count in RUNS:
        a, b = importlib.import_module(f"demo.{scene}").CUES[cue]
        t0 = starts.get((scene, cue))
        if t0 is None:
            continue
        for k in range(count):
            at = t0 + (b - a) * k / count
            ticks.append(round(at, 4))
            _add(mix, at, wood_hit, 0.3)
    peak = float(np.max(np.abs(mix))) or 1.0
    mix = mix / peak * 0.8  # 割れないように頭を揃える
    table = {"bpm": 90, "stop": stop, "total": round(total, 3), "anchors": [p for p in points if p["t"] <= stop],
             "beats": [round(b, 4) for b in beats], "ticks": ticks,
             "note": "仮の拍。コードで作った音で、Suno の曲ではない。曲が来たら捨てる"}
    return mix, table


def write_wav(mix, path):
    pcm = (np.clip(mix, -1, 1) * 32767).astype("<i2").tobytes()
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run", required=True, help="demo.build の置き場（<日時>/）")
    a = ap.parse_args(argv)
    run = pathlib.Path(a.run)
    try:
        rec = json.loads((run / "build.json").read_text(encoding="utf-8"))
        seconds = {s["name"]: s["seconds"] for s in rec["scenes"]}
        mix, table = compose(seconds)
    except (OSError, ValueError, KeyError) as e:
        print(f"検査できない: 場面の長さが読めない（{e}）", file=sys.stderr)
        return 4
    write_wav(mix, run / "beat.wav")
    (run / "beats.json").write_text(json.dumps(table, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{run / 'beat.wav'}  合図 {len(table['anchors'])}・拍 {len(table['beats'])}・刻み {len(table['ticks'])}・止める所 {table['stop']:.2f} 秒")
    return 0


if __name__ == "__main__":
    sys.exit(main())
