"""届いた手の映像と本人の声を、差し込む口の置き場（out/demo/slots/）へ名前ちょうどで入れる命令（本人の決定 11-06 の受け取りの手順）。

使い方: python -m demo.take_in <届いた所（Drive の 20261106-demo-hands など）> [--pick 名前=ファイル[,ファイル…]]… [--dry-run]
exit: 0 = 入れた（届いていない物は待ちのまま名前を言う）/ 3 = 届いた物が決まりに合わない（名指しする。入れない）/ 4 = 道具が無い・読めない

決めた事と理由:
- 置き場は名前ちょうど（手 A〜E は .mp4、声 A1〜A6 は .m4a）しか読まない（demo.script の SLOTS）。撮り直し（A4-2.m4a）や分けて撮った物
  （D-1.mp4・D-2.mp4）は、名前ちょうどの物が無い時だけ候補として名前を言い、どれを使うかは人が --pick で決める（良い方を選ぶのは人）。
  --pick にファイルを , で並べると、その順につないで 1 本にする（分けて撮った D を 1 本にするため）。
- 写す時に、撮影の情報（位置・機種・時刻）を外す（-map_metadata -1）。手の映像は音も外す（顔と声を入れない。J-022）。
  iPhone の .MOV（HEVC）も、場面が読める H.264 の .mp4 に作り直す。声は .m4a（AAC）のまま作り直す。元の届いた物は触らない。
- 入れる前に確かめる: 手の映像は決まり（横 16:9・幅 1280 以上・使う秒以上。demo.words.hands_problem）、声は場面の秒に入るか
  （黙りを切り、1.08 倍まで速めて入るか。demo.build.place_voices）。合わない物は名指しして 3 で止め、置き場に入れない（崩れた物を黙って使わない）。
- 置き場は git の外（out/）。届いた所の一覧も、撮影の情報も repo に書かない。
"""
import argparse
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

from demo import build, words
from demo.script import HANDS_EXT, SCENES, SLOT_DIR, SLOTS, VOICE_EXT, load_scene

ROOT = pathlib.Path(__file__).resolve().parents[2]
VIDEO_IN = (".mp4", ".mov", ".m4v")
STILL_IN = (".jpg", ".jpeg", ".png")
STILL_EXT = ".jpg"
AUDIO_IN = (".m4a", ".mp3", ".wav", ".aac")


def expected():
    """入れる物の名前と種類: {名前: "hands" | "voice"}。"""
    out = {}
    for kinds in SLOTS.values():
        for n, _ in kinds.get("hands", ()):
            out[n] = "hands"
        for n in kinds.get("voice", ()):
            out[n] = "voice"
        for n, _ in kinds.get("open", ()):
            out[n] = "open"
        for n in kinds.get("still", ()):
            out[n] = "still"
    return out


def candidates(folder, name, kind):
    """届いた所の中の、その名前に当たる物。名前ちょうどの物と、撮り直し・分けて撮った物（名前-数字）を分けて返す。"""
    exts = AUDIO_IN if kind == "voice" else STILL_IN if kind == "still" else VIDEO_IN
    files = [p for p in sorted(pathlib.Path(folder).iterdir()) if p.is_file() and p.suffix.lower() in exts]
    exact = [p for p in files if p.stem == name]
    more = [p for p in files if re.fullmatch(rf"{re.escape(name)}-\d+", p.stem)]
    return exact, more


def convert(srcs, dst, kind):
    """届いた物（1 つか、つなぐ物の並び）を、撮影の情報を外して dst に書く。手の映像は音も外して H.264 にする。"""
    dst.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        src = srcs[0]
        if len(srcs) > 1:
            listing = pathlib.Path(tmp) / "list.txt"
            listing.write_text("".join(f"file '{pathlib.Path(s).resolve()}'\n" for s in srcs), encoding="utf-8")
            src = listing
        head = ["ffmpeg", "-v", "error", "-y"] + (["-f", "concat", "-safe", "0"] if len(srcs) > 1 else []) + ["-i", str(src), "-map_metadata", "-1"]
        if kind == "still":  # 写真は撮影の情報（位置を含む）を外して JPEG に作り直す
            cmd = head + ["-frames:v", "1", "-q:v", "2", str(dst)]
        elif kind in ("hands", "open"):  # 映像は音も外す（open も手の映像と同じく、撮った時の音を入れない）
            cmd = head + ["-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-movflags", "+faststart", str(dst)]
        else:
            cmd = head + ["-vn", "-c:a", "aac", "-b:a", "192k", str(dst)]
        r = subprocess.run(cmd, capture_output=True, text=True)
    return None if r.returncode == 0 and dst.exists() else (r.stderr.strip()[:200] or "作り直せない")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("folder", help="届いた所（手の映像と声のファイルが並ぶ所）")
    ap.add_argument("--pick", action="append", default=[], metavar="名前=ファイル[,ファイル…]",
                    help="名前ちょうどの物が無い時に使う物（撮り直しから選ぶ・分けて撮った物を , で並べてつなぐ）")
    ap.add_argument("--dry-run", action="store_true", help="確かめるだけで、置き場に入れない")
    a = ap.parse_args(argv)
    folder = pathlib.Path(a.folder)
    if not folder.is_dir():
        print(f"検査できない: 届いた所が無い: {folder}", file=sys.stderr)
        return 4
    if not shutil.which("ffmpeg"):
        print("検査できない: ffmpeg が無い", file=sys.stderr)
        return 4
    want = expected()
    picks = {}
    for item in a.pick:
        name, _, files = item.partition("=")
        if name not in want or not files:
            print(f"検査できない: --pick が読めない: {item}（名前は {'・'.join(want)}）", file=sys.stderr)
            return 4
        paths = [folder / f for f in files.split(",")]
        missing = [str(p.name) for p in paths if not p.is_file()]
        if missing:
            print(f"検査できない: --pick のファイルが無い: {'・'.join(missing)}", file=sys.stderr)
            return 4
        picks[name] = paths
    slot = ROOT / SLOT_DIR
    with tempfile.TemporaryDirectory() as tmp:
        stage = pathlib.Path(tmp) / SLOT_DIR
        made, waiting, choose, bad = [], [], [], []
        for name, kind in want.items():
            exact, more = candidates(folder, name, kind)
            srcs = picks.get(name) or exact[:1]
            if not srcs:
                (choose if more else waiting).append(f"{name}" + (f"（候補: {'・'.join(p.name for p in more)}。--pick {name}=… で選ぶ）" if more else ""))
                continue
            dst = stage / f"{name}{VOICE_EXT if kind == 'voice' else STILL_EXT if kind == 'still' else HANDS_EXT}"
            err = convert(srcs, dst, kind)
            if err:
                bad.append(f"{name}: 作り直せない（{err}）")
                continue
            if kind == "hands":
                secs = next(s for kinds in SLOTS.values() for n, s in kinds.get("hands", ()) if n == name)
                problem = words.hands_problem(dst, secs)
                if problem:
                    bad.append(f"手 {name}: {problem}")
                    continue
            if kind == "open":
                secs = next(s for kinds in SLOTS.values() for n, s in kinds.get("open", ()) if n == name)
                problem = words.open_problem(dst, secs)
                if problem:
                    bad.append(f"開く映像 {name}: {problem}")
                    continue
            made.append(name)
        # 声は場面の秒に入るかを、書き出しと同じ置き方（黙りを切る・1.08 倍まで）で確かめる
        lengths = [load_scene(n).DURATION for n in SCENES]
        _, _, problem = build.place_voices(SCENES, lengths, tmp, into=pathlib.Path(tmp) / "voice")
        if problem:
            bad.append(problem)
        for line in made:
            print(f"届いた: {line}")
        for line in choose:
            print(f"選ぶ物がある: {line}")
        if waiting:
            print(f"まだ届いていない: {'・'.join(waiting)}")
        if bad:
            for line in bad:
                print(f"FAIL D.slots {line}", file=sys.stderr)
            print("置き場には入れていない（合わない物を直してから、もう一度）", file=sys.stderr)
            return 3
        if a.dry_run:
            print("確かめるだけ（--dry-run）。置き場には入れていない")
            return 0
        slot.mkdir(parents=True, exist_ok=True)
        for p in stage.iterdir():
            shutil.copyfile(p, slot / p.name)
        print(f"置き場に入れた: {slot}（{len(made)} 個）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
