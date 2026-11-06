"""demo.build の床: 台本の順・試験の数の読み方・場面ごとの引数を見る（書き出しはしない。遅いので）。"""
import importlib.util

import tempfile

from demo import build, script as _script

# 手と声の置き場は、手元の本物の置き場（out/demo/slots）でなく空の置き場を見る（届いた物があると、試験の偽の秒で声が入らず落ちた）
_EMPTY_SLOTS = tempfile.mkdtemp()
build.SLOT_DIR = _script.SLOT_DIR = _EMPTY_SLOTS

# 台本の場面がこの順で、重ならない。最後は問いの札（本人の指示 11-05）
# 前半は表、境目の札の後が裏（本人の決定 11-06、カード 125217）。語りの後ろの 2 文は文の順のまま後半の頭へ
assert build.SCENES == ["opening", "talk_toys", "talk_lost", "scene2", "flip", "word_touch", "scene3", "core_make", "core_keep", "scene5", "core_gallery",
                        "border", "talk_physics", "talk_claude", "core_loop", "word_ai", "scene7", "close", "ask"]
# 外した場面は本人が戻すかを決める。コードは残すので、読み込める
from demo import script  # noqa: E402
assert set(script.LEFT_OUT) == {"core_map", "core_voice", "scene6", "bridge"} and not set(script.LEFT_OUT) & set(build.SCENES)
assert build.SCENES.index("border") == len(script.FRONT) and script.FRONT[-1] == "core_gallery"
for name in script.LEFT_OUT:
    assert callable(script.load_scene(name).main), name
# 全体は 179.5 秒以内
assert sum(script.load_scene(n).DURATION for n in build.SCENES) <= 179.5
# 試験の数は RESULT.md の行から読む。読めない時は None（古い数を出さない）
assert build.count_tests("実行した 57 本（場面 30 本、試験 27 本）、期待どおり 57 本、未実装の床 0 本。") == (57, 57)
assert build.count_tests("何も無い") is None
# 引数: 曲は場面 7 にだけ、写真は場面 5 にだけ。試験の数は画面に出さない（本人の決定 11-05「哲学よりの動画にして」）
assert build.scene_args("scene7", None, "曲 X", None) == [], "曲の字を場面 7 に渡さない（本人の決定 11-06: 曲のクレジットは動画の中に入れない）"
assert build.scene_args("scene7", None, None, None) == []
assert build.scene_args("scene5", None, None, "p01") == ["--photos", "p01"]
assert build.scene_args("flip", (1, 1), "曲", "p01") == []
# 今ある場面のモジュールは、どれも main を持つ（build が同じ形で呼ぶ）
for name in build.SCENES:
    assert callable(build.load_scene(name).main), name
print("ok")

# main の exit code: 試験が落ちたら 3、検査できない（run.sh が 4）なら 4、場面が無い・場面が例外で止まったら 4。
# 書き出しは重いので、試験と場面を差し替えて分かれ道だけを通す。
import pathlib
import sys
import tempfile
import types

real_run, real_import = build.run_tests, build.importlib.import_module
real_missing = build.prepare.missing_tools
real_beat = build.make_beat
build.make_beat = lambda run, made, sha, dirty: ({"kind": "仮の拍", "commit": sha, "dirty": dirty}, None)  # 分かれ道だけを通す。音の作りは下で別に見る
build.prepare.missing_tools = lambda *a, **k: []  # この機械の道具に依らず分かれ道だけを通す（道具の確かめは下で別に見る）
with tempfile.TemporaryDirectory() as tmp:
    build.run_tests = lambda: (3, (10, 9))
    assert build.main(["--out", tmp]) == 3
    build.run_tests = lambda: (4, None)
    assert build.main(["--out", tmp]) == 4, "検査できない時は 4（落ちたの 3 と分ける）"

    def boom(argv):
        raise RuntimeError("chrome が止まった")

    def fake_import(name):
        if name.endswith("scene3"):
            raise ImportError(name)
        return types.SimpleNamespace(main=boom if name.endswith("scene2") else (lambda argv: 0))

    build.importlib.import_module = fake_import
    build.assemble.assemble = lambda made, out, audio=None, **k: 0
    build.assemble.duration = lambda p: 1.0
    # 場面が例外で止まっても、トレースバックの 1 でなく 4 で返す
    assert build.main(["--out", tmp, "--skip-tests"]) == 4
    build.importlib.import_module = lambda name: (_ for _ in ()).throw(ImportError(name)) if name.endswith("scene3") \
        else types.SimpleNamespace(main=lambda argv: 0)
    # 場面が欠けたら、--partial でも 4（作りかけの確かめは最後まで作るが、通ったとは言わない）
    assert build.main(["--out", tmp, "--skip-tests"]) == 4
    assert build.main(["--out", tmp, "--skip-tests", "--partial"]) == 4
build.run_tests, build.importlib.import_module = real_run, real_import
print("ok main")

# 撮る日の入口（#168）。道具が無ければ、試験（約 5 分）を回す前に名前で言って 4。
import contextlib
import json
import io
import urllib.request

ran = []
build.run_tests = lambda: ran.append("tests") or (0, (10, 10))
build.prepare.missing_tools = lambda *a, **k: ["ffmpeg", "字 Noto Serif CJK JP"]
with tempfile.TemporaryDirectory() as tmp:
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        assert build.main(["--out", tmp]) == 4
    assert "ffmpeg" in err.getvalue() and "Noto Serif CJK JP" in err.getvalue(), err.getvalue()
    assert ran == [], "道具が無いのに試験を回した"
build.prepare.missing_tools = lambda *a, **k: []

# 動画に効く物の印は、場面 5・6 が読む試行の記録の変更も見る
assert "docs/process/trials" in build.DIRTY_PATHS and "src" in build.DIRTY_PATHS

# 場面ごとの作り直し: --only は --run（前の置き場）と一緒に。無い場面の動画があれば名指しして 4
# 冒頭の動画（out/demo/opening/toys.mp4、git の外）は作業ツリーごとに有ったり無かったりする。有る作業ツリーで回すと、
# 前の記録の「印あり」と食い違って opening を作り直せと止まり、この試験の見る事（場面ごとの作り直し）と関わりなく落ちた（11-06）。
# なので作り直しの試験の間は、冒頭の動画が無い形に固定する。冒頭の動画が有る時の扱いは、下の shows_placeholder の所で別に見る。
real_has = build.opening.has_video
no_video = lambda path=None: False  # noqa: E731
build.opening.has_video = no_video
with tempfile.TemporaryDirectory() as tmp:
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        assert build.main(["--out", tmp, "--skip-tests", "--only", "scene2"]) == 4
    assert "--run" in err.getvalue()
    run = pathlib.Path(tmp) / "20261107-100000"
    run.mkdir()
    for n in build.SCENES:
        if n not in ("scene2", "core_keep"):
            (run / f"{n}.mp4").write_bytes(b"old-" + n.encode())
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        assert build.main(["--out", tmp, "--skip-tests", "--run", str(run), "--only", "scene2"]) == 4
    assert "core_keep" in err.getvalue(), err.getvalue()  # 前の置き場に無い場面は、作り直さずに黙ってつながない
    (run / "core_keep.mp4").write_bytes(b"old-core_keep")
    real_sha, real_dirty = build.head_sha, build.is_dirty
    build.head_sha, build.is_dirty = (lambda: "abc123"), (lambda: False)
    (run / "build.json").write_text(json.dumps({
        "commit": "abc123", "dirty": False, "tests": [61, 61], "music": "曲 Y", "photos": "p01",
        "scenes": [{"name": "flip", "seconds": 1.0, "commit": "old111", "dirty": True}]}), encoding="utf-8")

    seen = {}

    def fake_import(name):
        n = name.split(".")[-1]
        def main(argv):
            seen[n] = argv
            pathlib.Path(argv[argv.index("--out") + 1]).write_bytes(b"new-" + n.encode())
            return 0
        return types.SimpleNamespace(main=main)

    made_for_assemble = []
    build.importlib.import_module = fake_import
    build.assemble.assemble = lambda made, out, audio=None, **k: made_for_assemble.append([p.name for p in made]) or 0
    build.assemble.duration = lambda p: 1.0
    assert build.main(["--out", tmp, "--run", str(run), "--only", "scene2,scene5"]) == 0
    assert sorted(seen) == ["scene2", "scene5"], seen  # 言った場面だけを作り直す
    assert (run / "scene2.mp4").read_bytes() == b"new-scene2" and (run / "flip.mp4").read_bytes() == b"old-flip"
    assert made_for_assemble == [[f"{n}.mp4" for n in build.SCENES]], made_for_assemble  # つなぐのは全場面を台本の順で
    # 試験の数は前の記録から引き継ぐ（5 分の試験を回し直さない）。写真も言わなければ前のまま
    assert ran == [], ran
    assert not any("--photos" in v for k, v in seen.items() if k != "scene5")
    rec = json.loads((run / "build.json").read_text(encoding="utf-8"))
    # 曲の文は前の記録から引き継がない。曲を付けない作り直しは仮の拍と記録する（音と記録を食い違わせない。本人の決定 11-06 で場面 7 に刷らなくなった）
    assert rec["tests"] == [61, 61] and rec["music"] == build.PROVISIONAL_CREDIT and rec["photos"] == "p01" and rec["rebuilt"] == ["scene2", "scene5"], rec
    # 記録は場面ごとに、その動画を作った commit を持つ（残した場面を今の commit と言わない。動画のコードを辿るため）
    by_name = {r["name"]: r for r in rec["scenes"]}
    assert by_name["flip"]["commit"] == "old111" and by_name["flip"]["dirty"] is True, by_name["flip"]
    assert by_name["scene2"]["commit"] == "abc123" and by_name["scene2"]["dirty"] is False, by_name["scene2"]
    assert by_name["core_keep"]["commit"] == "abc123", by_name["core_keep"]  # 場面ごとの控えが無い古い記録は、全体の commit を使う
    # 職人の動画が無い間は、印が残っている事と外へ出せない事が記録に残る。opening を作り直さない間は前の記録のまま
    assert rec["placeholder"] is True and any("印" in w for w in rec["not_for_release"]), rec
    assert build.shows_placeholder(["opening"], {}, {}) is True  # 冒頭の動画が無い形に固定してある
    build.opening.has_video = lambda path=None: True
    assert build.shows_placeholder(["opening"], {}, {}) is False and build.shows_placeholder(["flip"], {}, {"placeholder": True}) is True
    assert build.shows_placeholder(["flip"], {"opening": "撮った.mp4"}, {"placeholder": True}) is False
    assert not any("印" in w for w in build.release_blockers(False)) and any("印" in w for w in build.release_blockers(True))
    assert set(script.BEFORE_RELEASE) <= set(build.release_blockers(False))
    build.opening.has_video = no_video  # この後の作り直しも、冒頭の動画が無い形で見る（下の注）
    # 音を作った commit が記録に残る（#268）
    assert rec["audio"]["kind"] == "仮の拍" and rec["audio"]["commit"] == "abc123" and rec["audio"]["dirty"] is False, rec["audio"]
    # 手元の変更があれば、前の試験の数は引き継がず回し直す
    build.is_dirty = lambda: True
    build.run_tests = lambda: ran.append("tests") or (0, (61, 61))
    assert build.main(["--out", tmp, "--run", str(run), "--only", "scene2"]) == 0
    assert ran == ["tests"], ran
    ran.clear()
    # 残す場面の動画に刷った物と食い違う時は、古い数や曲を出さないよう、作り直す場面を名指しして 4
    seen.clear()
    build.run_tests = lambda: ran.append("tests") or (0, (62, 62))
    for extra, scene in ((["--photos", "p02"], "scene5"),):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            assert build.main(["--out", tmp, "--run", str(run), "--only", "scene2", *extra]) == 4, extra
        assert scene in err.getvalue(), err.getvalue()
        assert seen == {}, "止める時は 1 場面も作り直さない"
        build.run_tests = lambda: ran.append("tests") or (0, (61, 61))
    ran.clear()
    build.head_sha, build.is_dirty = real_sha, real_dirty
    # 知らない場面の名前は 4
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        assert build.main(["--out", tmp, "--skip-tests", "--run", str(run), "--only", "scene9"]) == 4
    assert "scene9" in err.getvalue()

# 網を切った書き出し: --offline の間、場面が外へ取りに行くと止まって、場面の名前と URL を言う
with tempfile.TemporaryDirectory() as tmp:
    real_urlopen = urllib.request.urlopen

    def reach_out(argv):
        urllib.request.urlopen("https://dl.ndl.go.jp/api/iiif/x.jpg", timeout=1)
        return 0

    build.importlib.import_module = lambda name: types.SimpleNamespace(main=reach_out)
    # 絵が控えと合わない間は、網を切って書き出さずに名指しして 4
    real_verify = build.prepare.verify
    build.prepare.verify = lambda *a, **k: ["写しが無い: cache/v6-R0000020.jpg"]
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        assert build.main(["--out", tmp, "--skip-tests", "--offline"]) == 4
    assert "v6-R0000020" in err.getvalue() and "網を切れない" in err.getvalue(), err.getvalue()
    build.prepare.verify = lambda *a, **k: []
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        assert build.main(["--out", tmp, "--skip-tests", "--offline"]) == 4
    assert "網を切っている" in err.getvalue() and "dl.ndl.go.jp" in err.getvalue(), err.getvalue()
    assert urllib.request.urlopen is real_urlopen, "網を切る間だけ。終わったら戻す"
build.prepare.verify = real_verify
print("ok demo day")

# 曲を受ける口: クレジットと権利が無い曲は受けない。拍が読めない曲は試験を回す前に 3。場面の長さと消す所を assemble へ渡し、権利と commit を記録に残す
build.importlib.import_module = lambda name: types.SimpleNamespace(main=lambda argv: pathlib.Path(argv[argv.index("--out") + 1]).write_bytes(b"x") and 0)
build.prepare.verify = real_verify
with tempfile.TemporaryDirectory() as tmp:
    tune = pathlib.Path(tmp) / "曲.mp3"
    tune.write_bytes(b"not-really-audio")
    # 権利の文は要る（曲の出所を記録に残す）。クレジットの文（--music）は要らない（本人の決定 11-06）
    for bad in (["--song", str(tune)], ["--song", str(tune), "--music", "曲 X"],
                ["--song", str(tune), "--rights", "権利", "--only", "scene2"]):
        with contextlib.redirect_stderr(io.StringIO()):
            assert build.main(["--out", tmp, "--skip-tests", *bad]) == 4, bad
    ran.clear()
    build.run_tests = lambda: ran.append("tests") or (0, (10, 10))
    real_measure, real_align, real_apply = build.song.measure, build.song.align, build.song.apply_cues

    def unreadable(path):
        raise build.song.SongError(3, "拍がはっきりしない")

    build.song.measure = unreadable
    with contextlib.redirect_stderr(io.StringIO()):
        assert build.main(["--out", tmp, "--song", str(tune), "--music", "曲 X", "--rights", "権利"]) == 3
    assert ran == [], "曲が読めないのに試験を回した"
    with contextlib.redirect_stderr(io.StringIO()):
        assert build.main(["--out", tmp, "--song", str(tune), "--rights", "権利"]) == 3, "クレジットの文が無くても曲を受けて、拍を測る所まで進む"
    assert ran == []
    build.song.measure = lambda path: {"bpm": 100.0, "beats": [0.5, 1.1], "bars": [0.5], "seconds": 200.0, "clarity": 3.0}
    fitted = {"seconds": {n: 10.0 for n in build.SCENES}, "cues": {n: {} for n in build.SCENES}, "moved": 5, "left": 1}
    build.song.align = lambda *a: fitted
    build.song.apply_cues = lambda t: None
    build.load_scene_real = build.load_scene
    build.load_scene = lambda n: types.SimpleNamespace(DURATION=10.0, CUES={}, main=lambda argv: pathlib.Path(argv[argv.index("--out") + 1]).write_bytes(b"x") and 0)
    got = {}
    build.assemble.assemble = lambda made, out, audio=None, **k: got.update(audio=audio, **k) or 0
    tests_ok = build.main(["--out", tmp, "--skip-tests", "--song", str(tune), "--song-start", "2.0", "--music", "曲 X", "--rights", "本人が作った"])
    build.load_scene = build.load_scene_real
    assert tests_ok == 0, tests_ok
    assert got["audio"] == str(tune) and got["seconds"] == [10.0] * len(build.SCENES) and got["audio_start"] == 2.0
    assert got["fade_at"] == 10.0 * (len(build.SCENES) - 1) - 1.0, got["fade_at"]  # 問いの札の 1 秒前から消す
    run_dir = sorted(p for p in pathlib.Path(tmp).iterdir() if p.is_dir())[-1]
    rec = json.loads((run_dir / "build.json").read_text(encoding="utf-8"))
    assert rec["music"] == "曲 X" and rec["audio"]["kind"] == "song" and rec["audio"]["rights"] == "本人が作った" and rec["audio"]["sha256"]
    assert rec["audio"]["commit"] == rec["commit"]
    table = json.loads((run_dir / "beats.json").read_text(encoding="utf-8"))
    assert table["kind"] == "song" and table["commit"] == rec["commit"] and table["rights"] == "本人が作った" and table["moved"] == 5
    build.song.measure, build.song.align, build.song.apply_cues = real_measure, real_align, real_apply

# 撮った動画で場面を差し替える口（声の取り込みとエンジンごとの輪は、撮れたら差し替える）。読めない物は 4
with tempfile.TemporaryDirectory() as tmp:
    clip = pathlib.Path(tmp) / "撮り足し.mp4"
    clip.write_bytes(b"clip-bytes")
    for bad in (["--clip", "無い場面=" + str(clip)], ["--clip", "core_loop=" + str(clip) + "x"]):
        with contextlib.redirect_stderr(io.StringIO()):
            assert build.main(["--out", tmp, "--skip-tests", *bad]) == 4, bad
    seen_scene = []
    build.importlib.import_module = lambda name: types.SimpleNamespace(main=lambda argv: seen_scene.append(pathlib.Path(argv[argv.index("--out") + 1]).stem) or pathlib.Path(argv[argv.index("--out") + 1]).write_bytes(b"x") and 0)
    build.assemble.assemble = lambda made, out, audio=None, **k: 0
    assert build.main(["--out", tmp, "--skip-tests", "--clip", "core_loop=" + str(clip)]) == 0
    assert "core_loop" not in seen_scene and "core_gallery" in seen_scene, seen_scene
    run_dir = sorted(p for p in pathlib.Path(tmp).iterdir() if p.is_dir())[-1]
    assert (run_dir / "core_loop.mp4").read_bytes() == b"clip-bytes"
    rec = json.loads((run_dir / "build.json").read_text(encoding="utf-8"))
    assert rec["clips"]["core_loop"]["sha256"] and rec["clips"]["core_loop"]["file"] == "撮り足し.mp4", rec["clips"]

# 曲が無い時は仮の拍を付け、記録（build.json）にだけ仮と残す。動画のクレジットには出さない（本人の決定 11-06）
assert "仮の拍" in build.PROVISIONAL_CREDIT and "Suno の曲待ち" in build.PROVISIONAL_CREDIT
from demo import scene7  # noqa: E402
assert all(build.PROVISIONAL_CREDIT not in n and "曲" not in r for r, n in scene7.credit_lines())
build.run_tests, build.importlib.import_module, build.prepare.missing_tools = real_run, real_import, real_missing
build.opening.has_video = real_has
build.make_beat = real_beat
print("ok song")
