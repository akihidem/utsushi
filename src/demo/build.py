"""デモ動画を 1 つの命令で作り直す（撮る日の本番の入口）。

使い方: python -m demo.build --out <repo の外の場所> [--music 曲のクレジット] [--photos p01,p02] [--partial]
流れ: ./run.sh で試験を数える → 台本の順に場面を書き出す → demo.assemble でつなぎ 3 分の床を見る → 記録（build.json）を残す。
exit: 0 = 全部できて 3 分以内 / 3 = 試験が落ちた・3 分を超えた / 4 = 場面が無い・書き出せない（--partial なら無い場面を飛ばす）。

決めた事と理由:
- 試験の本数は撮るたびに ./run.sh から数える。画面に古い数を出さないため（台本の「出す数は repo の記録と合わせる」）。
  試験が 1 本でも外れたら書き出さない。外れた状態の数を動画に刷り込まないため。
- 場面の順と引数はここだけに書く。場面を足す・入れ替える時に、つなぐ順と書き出しの引数が食い違わないため。
- 記録に commit の SHA と各場面の長さを残す。出した動画がどのコードから出たかを後で辿れるようにする（エビデンスゲート）。
"""
import argparse
import importlib
import json
import pathlib
import re
import subprocess
import sys
import time

from demo import assemble

ROOT = pathlib.Path(__file__).resolve().parents[2]
# 台本の順（docs/demo/plan.md の 4）。名前は src/demo の中のモジュール。
SCENES = ["flip", "scene2", "scene3", "scene4", "scene5", "scene6", "scene7"]


def count_tests(result_text):
    """out/RESULT.md の「実行した場面 N 本、期待どおり M 本」を読む。読めない時は None。"""
    m = re.search(r"実行した場面 (\d+) 本、期待どおり (\d+) 本", result_text)
    return (int(m.group(1)), int(m.group(2))) if m else None


def scene_args(name, tests, music, photos):
    """場面ごとに足す引数。どの場面がどの引数を取るかは、各場面の CLI に合わせる。"""
    if name == "scene4" and tests:
        return ["--tests", f"{tests[1]}/{tests[0]}"]  # 場面 4 が「試験 N/N（./run.sh）」の形にする
    if name == "scene5" and photos is not None:
        return ["--photos", photos]
    if name == "scene7" and music:
        return ["--music", music]
    return []


def run_tests():
    r = subprocess.run([str(ROOT / "run.sh")], cwd=ROOT, capture_output=True, text=True)
    got = count_tests((ROOT / "out/RESULT.md").read_text(encoding="utf-8")) if (ROOT / "out/RESULT.md").exists() else None
    return r.returncode, got


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True, help="置き場（repo の外）。中に <日時>/ を作る")
    ap.add_argument("--music", help="曲のクレジットの文（場面 7 に出す）")
    ap.add_argument("--audio", help="曲のファイル。動画の長さで切り、短ければ無音で足す")
    ap.add_argument("--photos")
    ap.add_argument("--partial", action="store_true", help="無い場面を飛ばす（作りかけの確かめ用。本番では使わない）")
    ap.add_argument("--skip-tests", action="store_true", help="試験を回さない（数は出さない。確かめ用）")
    a = ap.parse_args(argv)

    tests = None
    if not a.skip_tests:
        rc, tests = run_tests()
        if rc == 4 or (rc == 0 and tests is None):
            print(f"検査できない: 試験を回せない・数が読めない（rc {rc}）", file=sys.stderr)
            return 4
        if rc != 0 or tests[0] != tests[1]:
            print(f"FAIL D.tests 試験が通らない（rc {rc}、{tests}）。書き出さない", file=sys.stderr)
            return 3
    run = pathlib.Path(a.out) / time.strftime("%Y%m%d-%H%M%S")
    run.mkdir(parents=True, exist_ok=True)
    made, skipped = [], []
    for name in SCENES:
        try:
            mod = importlib.import_module(f"demo.{name}")
        except ImportError:
            if a.partial:
                skipped.append(name)
                continue
            print(f"検査できない: 場面 {name} が無い", file=sys.stderr)
            return 4
        out = run / f"{name}.mp4"
        # 場面の中の例外（Chrome の時間切れ・ffmpeg の途中の失敗など）は、トレースバックの 1 でなく 4 で返す。
        # 1 はこのリポの検査で使わない決まりで、どの場面で止まったかも分からなくなるため。
        try:
            rc = mod.main(["--out", str(out), "--sheet", str(run / f"{name}-sheet.jpg"),
                           *scene_args(name, tests, a.music, a.photos)])
        except Exception as e:
            print(f"検査できない: 場面 {name} が途中で止まった（{type(e).__name__}: {e}）", file=sys.stderr)
            return 4
        if rc != 0:
            print(f"検査できない: 場面 {name} が書き出せない（rc {rc}）", file=sys.stderr)
            return 4
        made.append(out)
    if a.music and not a.audio:
        print("注意: --music（クレジット）が有るのに --audio（曲のファイル）が無い。音の無い動画になる", file=sys.stderr)
    rc = assemble.assemble(made, run / "demo.mp4", a.audio)
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    # 手元の変更が commit されていない時は印を残す。commit の SHA だけでは、出した動画のコードを辿れないため。
    # commit していない新しいファイルも、src/ と data/ の下なら動画に効くので数える。
    dirty = bool(subprocess.run(["git", "status", "--porcelain", "--", "src", "data/hypotheses", "data/sources", "tests"],
                                cwd=ROOT, capture_output=True, text=True).stdout.strip())
    record = {"commit": sha, "dirty": dirty, "tests": tests, "music": a.music, "photos": a.photos, "skipped": skipped,
              "scenes": [{"name": p.stem, "seconds": assemble.duration(p)} for p in made],
              "total_seconds": assemble.duration(run / "demo.mp4"), "assemble_rc": rc}
    (run / "build.json").write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"置き場 {run}")
    if rc != 0:
        return rc
    # 場面が欠けた動画は、--partial で最後まで作っても通ったとは言わない（4）。
    return 4 if skipped else 0


if __name__ == "__main__":
    sys.exit(main())
