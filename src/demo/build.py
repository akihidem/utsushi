"""デモ動画を 1 つの命令で作り直す（撮る日の本番の入口）。

使い方: python -m demo.build --out <repo の外の場所> [--photos p01,p02] [--partial] [--offline] [--run 前の置き場 [--only scene2,flip]]
曲が来たら: python -m demo.build --out <置き場> --song 曲.mp3 --music "クレジットの文" --rights "権利の文" [--song-start 秒]
前の日: python -m demo.prepare で道具を確かめ、絵を全部取り寄せる。撮る日は --offline で網を切って書き出せる。
流れ: ./run.sh で試験を確かめる → （曲の拍を測って合図を寄せる）→ 台本の順に場面を書き出す → 音を付けて demo.assemble でつなぎ 3 分の床を見る → 記録（build.json）を残す。
exit: 0 = 全部できて 3 分以内 / 3 = 試験が落ちた・3 分を超えた / 4 = 道具が無い・場面が無い・書き出せない（--partial なら無い場面を飛ばす）。

決めた事と理由:
- 試験は撮るたびに ./run.sh で確かめる。試験が 1 本でも外れたら書き出さない。外れた状態の動画を出さないため。
  本人の決定（11-05）「哲学よりの動画にして」で試験の数を画面に出すのはやめたが、書き出しの条件には残す。
- 場面の順は demo.script、引数はここだけに書く。場面を足す・入れ替える時に、つなぐ順と書き出しの引数が食い違わないため。
- 曲は 1 本の命令で付ける。--song を渡すと、音の実物から拍を測り、合図を寄せて全場面を書き出し、音を重ねる。
  クレジットと権利の文が無い曲は受けない（曲の出所を動画と記録に残すため。本人の決定で曲は本人が Suno で作って渡す）。
  --song が無い間は、コードで作った仮の拍を付ける（demo.beat）。クレジットにも仮と出す。Suno の曲に見せないため。
- 音を作った commit を build.json と beats.json に残す（#268）。動画と同じく、音のコードも後から辿るため。
- 要る道具は、試験（約 5 分）を回す前に全部を名前で言う。撮る日に場面の途中で初めて分かるのを避けるため。
- 途中で落ちたら、--run で同じ置き場を指して作り直す。--only で場面を絞ると、ほかの場面の動画はそのまま使い、
  つなぎ直す。試験の数は、前の記録が今の commit で手元の変更なしなら引き継ぐ（5 分の試験を回し直さない）。
  残す場面の動画に刷った物（試験の数・曲・写真）と今の値が違う時は、古い数を出さないよう 4 で止めて場面を名指しする。
- 記録に commit の SHA と各場面の長さを残す。出した動画がどのコードから出たかを後で辿れるようにする（エビデンスゲート）。
  場面ごとにも commit を持つ。--only で残した場面は、前の commit のコードから出た物なので。
"""
import argparse
import contextlib
import hashlib
import importlib  # noqa: F401  試験が場面の読み込みを差し替える口（demo.script と同じ物）
import json
import pathlib
import re
import subprocess
import sys
import time

from demo import assemble, beat, prepare, song
from demo.script import SCENES, load_scene

ROOT = pathlib.Path(__file__).resolve().parents[2]
# 動画に効く物。場面 5・6 は docs/process/trials の記録を読み、言葉の札は哲学の記録を読むので、そこの手の変更も印に数える。
DIRTY_PATHS = ["src", "data/hypotheses", "data/sources", "tests", "docs/process/trials", "docs/process/philosophy.md"]
# 曲が来るまでのクレジット。Suno の曲に見せないため、仮と書く。
PROVISIONAL_CREDIT = "仮の拍（コードで作った音。Suno の曲待ち）"


def count_tests(result_text):
    """out/RESULT.md の「実行した N 本（場面と試験の内訳）、期待どおり M 本」を読む。読めない時は None。"""
    m = re.search(r"実行した (\d+) 本（[^）]*）、期待どおり (\d+) 本", result_text)
    return (int(m.group(1)), int(m.group(2))) if m else None


def scene_args(name, tests, music, photos):
    """場面ごとに足す引数。どの場面がどの引数を取るかは、各場面の CLI に合わせる。"""
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


def file_sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def make_beat(run, made, sha, dirty):
    """仮の拍を作り、(記録に残す物, 音のファイル) を返す。場面の長さは書き出した動画の実物から読む。"""
    table = beat.make(run, {p.stem: assemble.duration(p) for p in made}, sha, dirty)
    path = pathlib.Path(run) / "beat.wav"
    return {"kind": "仮の拍", "file": path.name, "sha256": file_sha(path), "commit": sha, "dirty": dirty, "stop": table["stop"]}, path


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True, help="置き場（repo の外）。中に <日時>/ を作る")
    ap.add_argument("--song", help="曲のファイル。実物から拍を測り、合図を寄せて音を重ねる。動画の長さで切り、短ければ無音で足す")
    ap.add_argument("--song-start", type=float, default=0.0, help="曲のどこ（秒）から使うか。前奏を飛ばす時")
    ap.add_argument("--music", help="曲のクレジットの文（場面 7 に出す。--song の時は必ず）")
    ap.add_argument("--rights", help="曲の権利の文（作った人・道具・使ってよい範囲。build.json と beats.json に残す。--song の時は必ず）")
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
    if a.song and not (a.music and a.rights):
        print("検査できない: 曲には --music（クレジット）と --rights（権利）が要る", file=sys.stderr)
        return 4
    if a.song and a.only:
        print("検査できない: 曲を付ける時は全部の場面を作り直す（合図が動くので）。--only を外す", file=sys.stderr)
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
    if a.only and (prev.get("audio") or {}).get("kind") == "song":
        print("検査できない: 曲を付けた置き場は 1 場面だけ作り直せない（合図が曲に合わせてあるので）。--song で全部を作り直す", file=sys.stderr)
        return 4
    measured = None
    if a.song:  # 試験（約 5 分）を回す前に、曲が読めるかを確かめる
        try:
            measured = song.measure(a.song)
        except song.SongError as e:
            print(f"{'FAIL D.song' if e.code == 3 else '検査できない:'} {e}", file=sys.stderr)
            return e.code
    music = a.music if a.music is not None else prev.get("music") or PROVISIONAL_CREDIT
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
    fit = None
    if measured:
        # 合図を曲の拍へ寄せる。場面の表を書き換えるので、以後の書き出しの絵と字が曲に乗る。
        beats = [round(b - a.song_start, 4) for b in measured["beats"] if b >= a.song_start]
        bars = [round(b - a.song_start, 4) for b in measured["bars"] if b >= a.song_start]
        fit = song.align({n: load_scene(n).DURATION for n in SCENES}, {n: dict(load_scene(n).CUES) for n in SCENES}, beats, bars)
        song.apply_cues(fit)
    made, skipped = [], []
    for name in SCENES:
        if name not in only:
            made.append(run / f"{name}.mp4")  # 前の動画をそのまま使う（上で在る事を確かめた）
            continue
        try:
            mod = load_scene(name)
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
    if measured:
        # 問いの札の 1 秒前から音を消し、札の間は無音にする（考える間を音で埋めない。仮の拍と同じ線）。
        order = [p.stem for p in made]
        lengths = [fit["seconds"][n] for n in order]
        fade_at = max(0.0, sum(lengths[:order.index("ask")]) - 1.0) if "ask" in order else None
        audio = {"kind": "song", "file": pathlib.Path(a.song).name, "sha256": file_sha(a.song), "credit": music, "rights": a.rights,
                 "bpm": measured["bpm"], "start": a.song_start, "commit": sha, "dirty": dirty, "moved": fit["moved"], "left": fit["left"]}
        (run / "beats.json").write_text(song.table_json(measured, fit, **{k: audio[k] for k in ("sha256", "credit", "rights", "start", "commit", "dirty")}), encoding="utf-8")
        rc = assemble.assemble(made, run / "demo.mp4", a.song, seconds=lengths, audio_start=a.song_start, fade_at=fade_at)
    else:
        try:
            audio, sound = make_beat(run, made, sha, dirty)
        except (OSError, ValueError, KeyError) as e:
            print(f"検査できない: 仮の拍が作れない（{e}）", file=sys.stderr)
            return 4
        rc = assemble.assemble(made, run / "demo.mp4", sound)
    before = {r.get("name"): r for r in prev.get("scenes", [])}

    def made_by(name):
        """その場面の動画を作った commit。今作った場面は今の commit、残した場面は前の記録の物。"""
        if name in only:
            return {"commit": sha, "dirty": dirty}
        old = before.get(name, {})
        return {"commit": old.get("commit", prev.get("commit")), "dirty": old.get("dirty", prev.get("dirty"))}

    record = {"commit": sha, "dirty": dirty, "tests": tests, "music": music, "audio": audio, "photos": photos, "skipped": skipped,
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
