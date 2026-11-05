"""demo.build の床: 台本の順・試験の数の読み方・場面ごとの引数を見る（書き出しはしない。遅いので）。"""
import importlib.util

from demo import build

# 台本の 7 場面がこの順で、重ならない
assert build.SCENES == ["flip", "scene2", "scene3", "scene4", "scene5", "scene6", "scene7"]
# 試験の数は RESULT.md の行から読む。読めない時は None（古い数を出さない）
assert build.count_tests("実行した 57 本（場面 30 本、試験 27 本）、期待どおり 57 本、未実装の床 0 本。") == (57, 57)
assert build.count_tests("何も無い") is None
# 引数: 試験の数は場面 4 にだけ、曲は場面 7 にだけ、写真は場面 5 にだけ
assert build.scene_args("scene4", (57, 57), None, None) == ["--tests", "57/57"]
assert build.scene_args("scene4", None, None, None) == []
assert build.scene_args("scene7", None, "曲 X", None) == ["--music", "曲 X"]
assert build.scene_args("scene7", None, None, None) == []
assert build.scene_args("scene5", None, None, "p01") == ["--photos", "p01"]
assert build.scene_args("flip", (1, 1), "曲", "p01") == []
# 今ある場面のモジュールは、どれも main を持つ（build が同じ形で呼ぶ）
for name in build.SCENES:
    if importlib.util.find_spec(f"demo.{name}"):
        assert callable(importlib.import_module(f"demo.{name}").main), name
print("ok")

# main の exit code: 試験が落ちたら 3、検査できない（run.sh が 4）なら 4、場面が無い・場面が例外で止まったら 4。
# 書き出しは重いので、試験と場面を差し替えて分かれ道だけを通す。
import pathlib
import sys
import tempfile
import types

real_run, real_import = build.run_tests, build.importlib.import_module
real_missing = build.prepare.missing_tools
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
    build.assemble.assemble = lambda made, out, audio=None: 0
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
with tempfile.TemporaryDirectory() as tmp:
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        assert build.main(["--out", tmp, "--skip-tests", "--only", "scene2"]) == 4
    assert "--run" in err.getvalue()
    run = pathlib.Path(tmp) / "20261107-100000"
    run.mkdir()
    for n in build.SCENES:
        if n not in ("scene2", "scene6"):
            (run / f"{n}.mp4").write_bytes(b"old-" + n.encode())
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        assert build.main(["--out", tmp, "--skip-tests", "--run", str(run), "--only", "scene2"]) == 4
    assert "scene6" in err.getvalue(), err.getvalue()  # 前の置き場に無い場面は、作り直さずに黙ってつながない
    (run / "scene6.mp4").write_bytes(b"old-scene6")
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
    build.assemble.assemble = lambda made, out, audio=None: made_for_assemble.append([p.name for p in made]) or 0
    build.assemble.duration = lambda p: 1.0
    assert build.main(["--out", tmp, "--run", str(run), "--only", "scene2,scene4"]) == 0
    assert sorted(seen) == ["scene2", "scene4"], seen  # 言った場面だけを作り直す
    assert (run / "scene2.mp4").read_bytes() == b"new-scene2" and (run / "flip.mp4").read_bytes() == b"old-flip"
    assert made_for_assemble == [[f"{n}.mp4" for n in build.SCENES]], made_for_assemble  # つなぐのは全場面を台本の順で
    # 試験の数は前の記録から引き継ぐ（5 分の試験を回し直さない）。曲と写真も言わなければ前のまま
    assert ran == [] and seen["scene4"][-2:] == ["--tests", "61/61"], (ran, seen["scene4"])
    assert not any("--photos" in v for k, v in seen.items() if k != "scene5")
    rec = json.loads((run / "build.json").read_text(encoding="utf-8"))
    assert rec["tests"] == [61, 61] and rec["music"] == "曲 Y" and rec["photos"] == "p01" and rec["rebuilt"] == ["scene2", "scene4"], rec
    # 記録は場面ごとに、その動画を作った commit を持つ（残した場面を今の commit と言わない。動画のコードを辿るため）
    by_name = {r["name"]: r for r in rec["scenes"]}
    assert by_name["flip"]["commit"] == "old111" and by_name["flip"]["dirty"] is True, by_name["flip"]
    assert by_name["scene2"]["commit"] == "abc123" and by_name["scene2"]["dirty"] is False, by_name["scene2"]
    assert by_name["scene5"]["commit"] == "abc123", by_name["scene5"]  # 場面ごとの控えが無い古い記録は、全体の commit を使う
    # 手元の変更があれば、前の試験の数は引き継がず回し直す
    build.is_dirty = lambda: True
    build.run_tests = lambda: ran.append("tests") or (0, (61, 61))
    assert build.main(["--out", tmp, "--run", str(run), "--only", "scene2"]) == 0
    assert ran == ["tests"], ran
    ran.clear()
    # 残す場面の動画に刷った物と食い違う時は、古い数や曲を出さないよう、作り直す場面を名指しして 4
    seen.clear()
    build.run_tests = lambda: ran.append("tests") or (0, (62, 62))
    for extra, scene in (([], "scene4"), (["--music", "曲 Z"], "scene7"), (["--photos", "p02"], "scene5")):
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
build.run_tests, build.importlib.import_module, build.prepare.missing_tools = real_run, real_import, real_missing
print("ok demo day")
