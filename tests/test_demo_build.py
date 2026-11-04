"""demo.build の床: 台本の順・試験の数の読み方・場面ごとの引数を見る（書き出しはしない。遅いので）。"""
import importlib.util

from demo import build

# 台本の 7 場面がこの順で、重ならない
assert build.SCENES == ["flip", "scene2", "scene3", "scene4", "scene5", "scene6", "scene7"]
# 試験の数は RESULT.md の行から読む。読めない時は None（古い数を出さない）
assert build.count_tests("実行した場面 57 本、期待どおり 57 本、未実装の床 0 本。") == (57, 57)
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
