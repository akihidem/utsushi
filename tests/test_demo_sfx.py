"""効果音（script.SFX・build.place_sfx。統括の頼み 11-07: 手の映像の切る・折る所の音ハメ）の床。

見る事: 効果音は台本の場面の中に収まる／場面の頭からの秒を動画の秒に直す／曲の拍があれば一番近い拍へ半拍までしか寄せない／
置き場に無い音は飛ばして名前を返す（無くても書き出せる）／置き場は git の外。
"""
import pathlib
import tempfile

from demo import build, script, song

assert script.SFX_DIR.split("/")[0] == "out", "置き場は git の外"
for scene, off, name, gain in script.SFX:
    assert scene in script.SCENES and 0 <= off < script.load_scene(scene).DURATION, (scene, off)
    assert name and gain <= 0, (name, gain)

order = list(script.SCENES)
lengths = [script.load_scene(n).DURATION for n in order]
starts = dict(zip(order, [sum(lengths[:i]) for i in range(len(order))]))
with tempfile.TemporaryDirectory() as root:
    d = pathlib.Path(root) / script.SFX_DIR
    d.mkdir(parents=True)
    names = sorted({n for _, _, n, _ in script.SFX})
    for n in names[:-1]:
        (d / f"{n}.wav").write_bytes(b"x")
    placed, missing = build.place_sfx(order, lengths, root=root)
    assert missing == [n for _, _, n, _ in script.SFX if n == names[-1]], missing
    want = [(scene, off) for scene, off, n, _ in script.SFX if n != names[-1]]
    assert [round(at, 3) for _, at, _ in placed] == [round(starts[s] + o, 3) for s, o in want], placed
    # 曲の拍へ寄せる: 近い拍（半拍以内）へは寄り、遠い拍へは寄らない
    first = starts[want[0][0]] + want[0][1]
    near_beats = [first + 0.25]
    got, _ = build.place_sfx(order, lengths, beats=near_beats, root=root)
    assert abs(got[0][1] - (first + 0.25)) < 1e-6
    far, _ = build.place_sfx(order, lengths, beats=[first + song.BEAT_ONLY_SHIFT + 0.2], root=root)
    assert abs(far[0][1] - first) < 1e-6
print("ok 効果音は場面の中に収まり、動画の秒に直され、拍へは半拍まで寄り、無い音は名前を返して飛ばす")
