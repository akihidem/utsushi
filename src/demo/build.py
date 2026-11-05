"""デモ動画を 1 つの命令で作り直す（撮る日の本番の入口）。

使い方: python -m demo.build --out <repo の外の場所> [--music 曲のクレジット] [--photos p01,p02] [--partial]
        [--offline] [--run 前の置き場 [--only scene2,scene4]]
前の日: python -m demo.prepare で道具を確かめ、絵を全部取り寄せる。撮る日は --offline で網を切って書き出せる。
流れ: ./run.sh で試験を数える → 台本の順に場面を書き出す → demo.assemble でつなぎ 3 分の床を見る → 記録（build.json）を残す。
exit: 0 = 全部できて 3 分以内 / 3 = 試験が落ちた・3 分を超えた / 4 = 道具が無い・場面が無い・書き出せない（--partial なら無い場面を飛ばす）。

決めた事と理由:
- 試験の本数は撮るたびに ./run.sh から数える。画面に古い数を出さないため（台本の「出す数は repo の記録と合わせる」）。
  試験が 1 本でも外れたら書き出さない。外れた状態の数を動画に刷り込まないため。
- 場面の順と引数はここだけに書く。場面を足す・入れ替える時に、つなぐ順と書き出しの引数が食い違わないため。
- 要る道具は、試験（約 5 分）を回す前に全部を名前で言う。撮る日に場面の途中で初めて分かるのを避けるため。
- 途中で落ちたら、--run で同じ置き場を指して作り直す。--only で場面を絞ると、ほかの場面の動画はそのまま使い、
  つなぎ直す。試験の数は、前の記録が今の commit で手元の変更なしなら引き継ぐ（5 分の試験を回し直さない）。
  残す場面の動画に刷った物（試験の数・曲・写真）と今の値が違う時は、古い数を出さないよう 4 で止めて場面を名指しする。
- 記録に commit の SHA と各場面の長さを残す。出した動画がどのコードから出たかを後で辿れるようにする（エビデンスゲート）。
  場面ごとにも commit を持つ。--only で残した場面は、前の commit のコードから出た物なので。
"""
import argparse
import contextlib
import importlib
import json
import pathlib
import re
import subprocess
import sys
import time

from demo import assemble, prepare

ROOT = pathlib.Path(__file__).resolve().parents[2]
# 台本の順（docs/demo/plan.md の 4）。名前は src/demo の中のモジュール。
SCENES = ["flip", "scene2", "scene3", "scene4", "scene5", "scene6", "scene7"]
# 動画に効く物。場面 5・6 は docs/process/trials の記録を読むので、そこの手の変更も印に数える。
DIRTY_PATHS = ["src", "data/hypotheses", "data/sources", "tests", "docs/process/trials"]


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


def head_sha():
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def is_dirty():
    # 手元の変更が commit されていない時は印を残す。commit の SHA だけでは、出した動画のコードを辿れないため。
    # commit していない新しいファイルも、DIRTY_PATHS の下なら動画に効くので数える。
    return bool(subprocess.run(["git", "status", "--porcelain", "--", *DIRTY_PATHS],
                               cwd=ROOT, capture_output=True, text=True).stdout.strip())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True, help="置き場（repo の外）。中に <日時>/ を作る")
    ap.add_argument("--music", help="曲のクレジットの文（場面 7 に出す）")
    ap.add_argument("--audio", help="曲のファイル。動画の長さで切り、短ければ無音で足す")
    ap.add_argument("--photos")
    ap.add_argument("--partial", action="store_true", help="無い場面を飛ばす（作りかけの確かめ用。本番では使わない）")
    ap.add_argument("--skip-tests", action="store_true", help="試験を回さない（数は出さない。確かめ用）")
    ap.add_argument("--offline", action="store_true", help="網を切って書き出す。先に demo.prepare で絵を置いておく")
    ap.add_argument("--run", help="前の置き場（<日時>/）。同じ場所に作り直す")
    ap.add_argument("--only", help="作り直す場面（scene2,scene4 のように。--run と一緒に）。ほかの場面の動画はそのまま使う")
    a = ap.parse_args(argv)

    only = [n for n in (a.only or "").split(",") if n] or list(SCENES)
    unknown = [n for n in only if n not in SCENES]
    if unknown:
        print(f"検査できない: 知らない場面 {'、'.join(unknown)}（{'、'.join(SCENES)}）", file=sys.stderr)
        return 4
    if a.only and not a.run:
        print("検査できない: --only は --run（前の置き場）と一緒に使う", file=sys.stderr)
        return 4
    miss = prepare.missing_tools()
    if miss:
        print(f"検査できない: 足りない物: {'、'.join(miss)}（README の「デモ動画を作る」）", file=sys.stderr)
        return 4
    if a.offline:
        wrong = prepare.verify(prepare.DEFAULT_CACHE, prepare.DEFAULT_SOURCES)
        if wrong:
            print("検査できない: 網を切れない（絵が控えと合わない）… " + "、".join(wrong), file=sys.stderr)
            return 4
    run, prev = None, {}
    if a.run:
        run = pathlib.Path(a.run)
        if not run.is_dir():
            print(f"検査できない: 前の置き場が無い: {run}", file=sys.stderr)
            return 4
        absent = [n for n in SCENES if n not in only and not (run / f"{n}.mp4").exists()]
        if absent:
            print(f"検査できない: 前の置き場に動画が無い場面: {'、'.join(absent)}（--only に足して作り直す）", file=sys.stderr)
            return 4
        try:
            prev = json.loads((run / "build.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            prev = {}
    music = a.music if a.music is not None else prev.get("music")
    photos = a.photos if a.photos is not None else prev.get("photos")
    sha, dirty = head_sha(), is_dirty()

    tests = None
    if not a.skip_tests:
        carried = prev.get("tests")
        if carried and prev.get("commit") == sha and not prev.get("dirty") and not dirty and carried[0] == carried[1]:
            tests = tuple(carried)  # 同じ commit で手元の変更なし。前に通した数をそのまま使う
        else:
            rc, tests = run_tests()
            if rc == 4 or (rc == 0 and tests is None):
                print(f"検査できない: 試験を回せない・数が読めない（rc {rc}）", file=sys.stderr)
                return 4
            if rc != 0 or tests[0] != tests[1]:
                print(f"FAIL D.tests 試験が通らない（rc {rc}、{tests}）。書き出さない", file=sys.stderr)
                return 3
    # 残す場面に刷った物と今の値が違えば、作り直すまで動画に古い物が残る。--skip-tests は数を見ない（確かめ用）。
    stale = [n for n in SCENES if n not in only
             and scene_args(n, prev.get("tests"), prev.get("music"), prev.get("photos"))
             != scene_args(n, tests if tests else prev.get("tests"), music, photos)]
    if stale:
        print(f"検査できない: 残す場面に刷った物と今の値が違う: {'、'.join(stale)}（--only に足して作り直す）", file=sys.stderr)
        return 4
    if run is None:
        run = pathlib.Path(a.out) / time.strftime("%Y%m%d-%H%M%S")
        run.mkdir(parents=True, exist_ok=True)
    made, skipped = [], []
    for name in SCENES:
        if name not in only:
            made.append(run / f"{name}.mp4")  # 前の動画をそのまま使う（上で在る事を確かめた）
            continue
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
            with prepare.offline() if a.offline else contextlib.nullcontext():
                rc = mod.main(["--out", str(out), "--sheet", str(run / f"{name}-sheet.jpg"),
                               *scene_args(name, tests, music, photos)])
        except Exception as e:
            print(f"検査できない: 場面 {name} が途中で止まった（{type(e).__name__}: {e}）", file=sys.stderr)
            return 4
        if rc != 0:
            print(f"検査できない: 場面 {name} が書き出せない（rc {rc}）", file=sys.stderr)
            return 4
        made.append(out)
    if music and not a.audio:
        print("注意: --music（クレジット）が有るのに --audio（曲のファイル）が無い。音の無い動画になる", file=sys.stderr)
    rc = assemble.assemble(made, run / "demo.mp4", a.audio)
    before = {r.get("name"): r for r in prev.get("scenes", [])}

    def made_by(name):
        """その場面の動画を作った commit。今作った場面は今の commit、残した場面は前の記録の物。"""
        if name in only:
            return {"commit": sha, "dirty": dirty}
        old = before.get(name, {})
        return {"commit": old.get("commit", prev.get("commit")), "dirty": old.get("dirty", prev.get("dirty"))}

    record = {"commit": sha, "dirty": dirty, "tests": tests, "music": music, "photos": photos, "skipped": skipped,
              "rebuilt": only if a.only else [], "offline": a.offline,
              "scenes": [{"name": p.stem, "seconds": assemble.duration(p), **made_by(p.stem)} for p in made],
              "total_seconds": assemble.duration(run / "demo.mp4"), "assemble_rc": rc}
    (run / "build.json").write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"置き場 {run}")
    if rc != 0:
        return rc
    # 場面が欠けた動画は、--partial で最後まで作っても通ったとは言わない（4）。
    return 4 if skipped else 0


if __name__ == "__main__":
    sys.exit(main())
