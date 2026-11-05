"""上げた写真と動画の、出す前の人の確認（本人の決定 11-05、#314）。

本人の決定: 物だけが写った写真と動画は、ギャラリーで公開する。人や声が入る物は、字だけにする（映像と声は頁に出さない）。出す前に、人の確認を入れる。

判断の芯:
- 確かめるのは人だけ。機械は顔も声も見分けない。持ち寄りの公開と同じく、命令は端末で人が番号を打った時だけ進む（contrib._human_confirm）。
- 結果は写真の置き場（records/media/<記録>/review.json）に持つ。記録は 1 回書いたら書き換えない作りなので、記録のファイルには書かない。
  記録の取り下げで、写真と一緒に消える。
- 既定は出さない。確認の記録が無い時も、読めない時も出さない。
- 確認の前の物は、上げた本人の画面にだけ出す（受け取りを確かめるため）。別の人の手帖と絵の道には出さない。
  who は sessionStorage にあって絵と動画の GET に載らないので、上げた時に画面へ鍵を渡し、写真ごとに控える（owners.json。話した考えの紙の鍵と同じ作り）。
  1 台の機械を順に使う場のために、期限があり（OWNER_HOURS）、次の記録を残すと閉じる（鍵の cookie は web/play_server が消す）。
- 合言葉なしで開いた場（J-028）は写真の道そのものが閉じているので、ここでは見ない。

exit code: 0 = 通る / 3 = 確認にならない・取り消せない / 4 = 呼び方の誤り・検査できない。
"""
import argparse
import hmac
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import contrib, records, store
from .model import Failure

SHOWS = ("object", "people")  # object: 物だけが写っている / people: 人や声が入る
RECORD_ID = re.compile(r"R-\d{4,}")
MEDIA_NAME = re.compile(r"m\d+\.(?:jpg|png|mp4|mov)")
VIDEO_TIMEOUT = 120  # 秒。音の流れを落とすだけで、符号化し直さない
OWNER_HOURS = 2  # 上げた本人の画面に確認の前の物を出す長さ。話した考えの紙の鍵（api.words.KEY_HOURS）と同じ


def _folder(rid):
    return records.folder() / "media" / rid


def _load(rid):
    """確認の記録。無い時も読めない時も空にする（出さない方へ倒す）。"""
    return store.read_json_or_skip(_folder(rid) / "review.json") or {} if RECORD_ID.fullmatch(rid) else {}


def _shows(rid, name):
    entry = _load(rid).get(name)
    return entry.get("shows") if isinstance(entry, dict) else None


def public(rid, files):
    """ギャラリーと玩具の頁に出してよい物。物だけと人が確かめた物だけ。"""
    return [f for f in files if _shows(rid, f) == "object"]


def visible(rid, files):
    """AI の口で扱ってよい物。人や声が入ると確かめた物を除く。頁と絵の道は、見る画面で分ける shown_to を使う。"""
    return [f for f in files if _shows(rid, f) != "people"]


def claim(rid, name, key):
    """上げた画面の鍵を、写真ごとに控える。別の人が同じ記録へ上げても、前の人の写真を開けないように。"""
    path = _folder(rid) / "owners.json"
    owners = store.read_json_or_skip(path) or {}
    store.write_json(path, {**owners, name: {"key": key, "at": datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")}})


def _mine(rid, name, key):
    """その鍵の画面が上げた物で、期限の中か。控えが読めない時は出さない方へ倒す。"""
    entry = (store.read_json_or_skip(_folder(rid) / "owners.json") or {}).get(name) if key and RECORD_ID.fullmatch(rid) else None
    if not isinstance(entry, dict) or not isinstance(entry.get("key"), str) or not hmac.compare_digest(entry["key"].encode(), key.encode()):
        return False
    try:
        at = datetime.fromisoformat(entry["at"])
        return datetime.now(at.tzinfo) - at <= timedelta(hours=OWNER_HOURS)
    except (KeyError, TypeError, ValueError):
        return False


def shown_to(rid, files, key=None):
    """その画面に出してよい物。物だけと人が確かめた物と、確認の前で上げた本人の画面の物。人や声が入ると確かめた物は本人にも出さない。"""
    return [f for f in files if _shows(rid, f) == "object" or (_shows(rid, f) != "people" and _mine(rid, f, key))]


def waiting():
    """確認を待つ物。[(記録の番号, ファイル)]。置き場の順で、順位ではない。"""
    root = records.folder() / "media"
    out = []
    for d in sorted(root.glob("R-*")) if root.exists() else []:
        done = _load(d.name)
        out += [(d.name, p.name) for p in sorted(d.glob("m*.*")) if p.name not in done]
    return out


def _drop_audio(path):
    """前から置いてある動画の音を落とす。Returns 失敗の文か None。絵は符号化し直さない。取り込みの時に落とすのは techo_site.clean_video。"""
    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        return "音を確かめる ffmpeg か ffprobe が無い"
    try:
        probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", str(path)],
                               capture_output=True, text=True, timeout=VIDEO_TIMEOUT)
        if probe.returncode != 0:
            return "動画を読めない"
        if not probe.stdout.strip():
            return None
        with tempfile.TemporaryDirectory() as tmp:
            dst = Path(tmp) / path.name
            r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "mov", "-i", str(path), "-map", "0:V", "-an", "-c", "copy", "-f", path.suffix[1:], str(dst)],
                               capture_output=True, timeout=VIDEO_TIMEOUT)
            if r.returncode != 0 or not dst.exists():
                return "音を落とせない"
            store.write_atomic(path, dst.read_bytes())
    except (OSError, subprocess.TimeoutExpired) as e:
        return f"音を落とせない（{type(e).__name__}）"
    return None


def _target(rid, name):
    """番号とファイルの形と実在を見る。Returns (ファイルの path か None, 失敗の一覧)。"""
    if not (isinstance(rid, str) and RECORD_ID.fullmatch(rid) and isinstance(name, str) and MEDIA_NAME.fullmatch(name)):
        return None, [Failure("F10.review", f"{rid}/{name}", "記録の番号かファイルの名前の形が違う")]
    path = _folder(rid) / name
    if not path.exists():
        return None, [Failure("F10.review", f"{rid}/{name}", "写真か動画が無い")]
    return path, []


def record(rid, name, shows, reviewer):
    """人の確かめた結果を残す。Returns 失敗の一覧。物だけと確かめた動画に音が残っていれば、ここで落とす。"""
    path, failures = _target(rid, name)
    if failures:
        return failures
    if shows not in SHOWS:
        return [Failure("F10.review", f"{rid}/{name}", "結果は object（物だけ）か people（人や声が入る）")]
    if not (isinstance(reviewer, str) and reviewer.strip()):
        return [Failure("F10.review", f"{rid}/{name}", "確かめた人の名前が無い")]
    if shows == "object" and path.suffix in (".mp4", ".mov"):
        why = _drop_audio(path)
        if why:
            return [Failure("F10.review", f"{rid}/{name}", why)]
    done = _load(rid)
    done[name] = {"shows": shows, "reviewer": reviewer.strip(), "at": datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="minutes")}
    store.write_json(_folder(rid) / "review.json", done)
    return []


def revoke(rid, name):
    """確認を取り消す。確認を待つ物に戻り、ギャラリーから消える。Returns 失敗の一覧。"""
    _, failures = _target(rid, name)
    if failures:
        return failures
    done = _load(rid)
    if name in done:
        del done[name]
        store.write_json(_folder(rid) / "review.json", done)
    return []


def main(argv=None):
    ap = argparse.ArgumentParser(prog="omochae.media_review", description="上げた写真と動画を、出す前に人が確かめる（#314）")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="確認を待つ物")
    a = sub.add_parser("approve", help="人が見て結果を残す。端末で番号を打った時だけ進む")
    a.add_argument("id")
    a.add_argument("name")
    a.add_argument("--shows", required=True, choices=SHOWS, help="object: 物だけが写っている / people: 人や声が入る")
    a.add_argument("--reviewer", required=True)
    r = sub.add_parser("revoke", help="確認を取り消す")
    r.add_argument("id")
    r.add_argument("name")
    try:
        args = ap.parse_args(argv)
    except SystemExit as e:
        return 0 if e.code == 0 else 4
    try:
        if args.cmd == "list":
            for rid, name in waiting():
                print(rid, name, _folder(rid) / name)
            return 0
        if args.cmd == "approve":
            path, failures = _target(args.id, args.name)
            if not failures:
                print(path)
                if not contrib._human_confirm(f"{args.id}/{args.name}", "確認"):
                    failures = [Failure("F10.review", f"{args.id}/{args.name}", "端末での人の確認が無い")]
                else:
                    failures = record(args.id, args.name, args.shows, args.reviewer)
        else:
            failures = revoke(args.id, args.name)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as e:
        print(f"検査できない: {type(e).__name__}: {e}", file=sys.stderr)
        return 4
    for f in failures:
        print(f.line(), file=sys.stderr)
    return 3 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
