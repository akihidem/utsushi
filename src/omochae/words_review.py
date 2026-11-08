"""公開の場の、作った人の感想と工夫の行の、出す前の人の確かめ（窓口の決め A・11-08。本人 11-08「…できたおもちゃはギャラリーの形で並べる。感想も見れるように」）。

前は、合言葉なしで開いた場のギャラリーの札に、人の書いた文（感想と工夫の行）を出さなかった。文の中の名前は機械で落とせないため（J-028）。
窓口の決め A で、人が確かめた後なら公開の場にも出す形にした。写真と動画の確かめ（media_review）と同じ考えで、字の分をここに持つ。

判断の芯:
- 確かめるのは人だけ。機械は名前や学校を見分けない。命令は端末で人が番号を打った時だけ進む（contrib._human_confirm。media_review と同じ）。
- 結果は記録の写真の置き場（records/media/<記録>/words.json）に持つ。記録は 1 回書いたら書き換えない作りなので、記録のファイルには書かない。
  写真だけの取り下げ（media_only）でも置き場ごと消えるので、字の確かめも外れる（出さない方へ倒れる。取り下げた人の字を、確かめ直さずに出さない）。
- **確かめた時の字の指紋（sha256）を持つ。** 確かめた後に字が替わった時（話した字の取り下げ --talk-only で空になった時など）は、指紋が合わず、
  確かめていない扱いに戻る。確かめた物と違う字を、確かめた印のまま出さないため。
- 既定は出さない。確かめの記録が無い時も、読めない時も、指紋が合わない時も出さない。
- 出す時に、連絡先の形の床（contrib.check_pii）をもう一度当てる。床が後で強くなった時に、前に確かめた字でも当たる物は出さない。
- 合言葉付きの場は、今までどおり確かめずに出す（その場の人だけが見る頁なので）。ここは公開の場の札だけが使う。

exit code: 0 = 通る / 3 = 確かめにならない・取り消せない / 4 = 呼び方の誤り・検査できない。
"""
import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone

from . import contrib, records, store
from .model import Failure

RECORD_ID = re.compile(r"R-\d{4,}")


def _path(rid):
    return records.folder() / "media" / rid / "words.json"


def _record(rid):
    """記録。無い・取り下げた・読めない時は None。"""
    if not (isinstance(rid, str) and RECORD_ID.fullmatch(rid)) or (records.withdrawn_folder() / f"{rid}.json").exists():
        return None
    return store.read_json_or_skip(records.folder() / f"{rid}.json")


DETAIL_KEYS = ("first_moved", "stuck", "what_if")  # 記録の欄（answers）のうち、札の畳み「のこした記録」に出す物


def details_of(rec):
    """札の畳み「のこした記録」に出す人の字: 最初に動いた所・引っかかった所・変えると違いが出そうな所・思いついた事・メモ（made_item が出す物と同じ欄）。
    前は玩具の頁の記録の札にだけ出ていた。本人の言葉 11-08 477「復元の記録などはすべてもちよるに統合する。」で、もちよるの札に移した（統括の決め）。
    どれも空なら空の辞書（words_of に足さない）。"""
    ans = rec.get("answers") if isinstance(rec.get("answers"), dict) else {}
    d = {k: str(ans.get(k) or "") for k in DETAIL_KEYS}
    d["ideas"] = [str(x) for x in rec.get("ideas") or [] if str(x).strip()]
    d["note"] = str(rec.get("note") or "")
    return d if any(v.strip() if isinstance(v, str) else v for v in d.values()) else {}


def words_of(rec):
    """札に出す人の字: 感想と工夫の行と、畳み「のこした記録」の欄（made_item が出す物と同じ欄）。確かめる人に見せる字と、指紋の元はこれ。
    畳みの欄は、ある時だけ details の鍵で足す。欄の無い記録の字の形と指紋は前と同じなので、前に確かめた記録の確かめは外れない。
    欄のある記録は、欄の字を確かめた人が見ていないので、指紋が替わって確かめを待つ物に戻る（確かめていない字を、確かめた印のまま出さない）。"""
    fixes = [{k: str(f.get(k, "")) for k in ("part", "change", "outcome")} for f in rec.get("fixes", []) if isinstance(f, dict)]
    w = {"impression": str(rec.get("impression") or ""), "fixes": fixes}
    details = details_of(rec)
    if details:
        w["details"] = details
    return w


def _texts(w):
    """words_of の字の全部（連絡先の形の床に当てる字）。"""
    d = w.get("details", {})
    return [w["impression"], *(v for f in w["fixes"] for v in f.values()), *(d.get(k, "") for k in DETAIL_KEYS), *d.get("ideas", []), d.get("note", "")]


def has_words(rec):
    w = words_of(rec)
    return bool(w["impression"].strip() or w["fixes"] or w.get("details"))


def digest(rec):
    """字の指紋。並びと字だけから作り、時刻や番号は入れない。"""
    return hashlib.sha256(json.dumps(words_of(rec), ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def checked(rid):
    """公開の場の札に、この記録の感想と工夫の行を出してよいか。人が確かめ、その時の字のままで、連絡先の床にも当たらない時だけ True。"""
    rec = _record(rid)
    entry = store.read_json_or_skip(_path(rid)) if rec else None
    if not (rec and isinstance(entry, dict) and entry.get("ok") is True and entry.get("digest") == digest(rec)):
        return False
    return not contrib.check_pii({"body": " ".join(_texts(words_of(rec)))})


def waiting():
    """確かめを待つ記録の番号（字があって、まだ確かめていない物・確かめた後に字が替わった物）。置き場の順で、順位ではない。"""
    return [r["id"] for r in records.all_records() if has_words(r) and not checked(r["id"])]


def record(rid, reviewer):
    """人の確かめた結果を残す。Returns 失敗の一覧。"""
    rec = _record(rid)
    if rec is None:
        return [Failure("F10.review", str(rid), "その番号の記録は無い")]
    if not has_words(rec):
        return [Failure("F10.review", rid, "確かめる字（感想と工夫の行と、のこした記録の欄）が無い")]
    if not (isinstance(reviewer, str) and reviewer.strip()):
        return [Failure("F10.review", rid, "確かめた人の名前が無い")]
    path = _path(rid)
    path.parent.mkdir(parents=True, exist_ok=True)
    store.write_json(path, {"ok": True, "reviewer": reviewer.strip(), "digest": digest(rec),
                            "at": datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="minutes")})
    return []


def revoke(rid):
    """確かめを取り消す。確かめを待つ物に戻り、公開の場の札から字が消える。Returns 失敗の一覧。"""
    if not (isinstance(rid, str) and RECORD_ID.fullmatch(rid)):
        return [Failure("F10.review", str(rid), "記録の番号の形が違う")]
    _path(rid).unlink(missing_ok=True)
    return []


def main(argv=None):
    ap = argparse.ArgumentParser(prog="omochae.words_review", description="公開の場の札に出す前に、作った人の感想と工夫の行を人が確かめる")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="確かめを待つ記録と、その字")
    a = sub.add_parser("approve", help="人が読んで、出してよいと確かめた結果を残す。端末で番号を打った時だけ進む")
    a.add_argument("id")
    a.add_argument("--reviewer", required=True)
    r = sub.add_parser("revoke", help="確かめを取り消す")
    r.add_argument("id")
    try:
        args = ap.parse_args(argv)
    except SystemExit as e:
        return 0 if e.code == 0 else 4
    try:
        if args.cmd == "list":
            for rid in waiting():
                w = words_of(_record(rid))
                print(rid, json.dumps(w, ensure_ascii=False))
            return 0
        if args.cmd == "approve":
            rec = _record(args.id)
            if rec is not None:
                print(json.dumps(words_of(rec), ensure_ascii=False))
            if rec is not None and not contrib._human_confirm(args.id, "確かめ"):
                failures = [Failure("F10.review", args.id, "端末での人の確かめが無い")]
            else:
                failures = record(args.id, args.reviewer)
        else:
            failures = revoke(args.id)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as e:
        print(f"検査できない: {type(e).__name__}: {e}", file=sys.stderr)
        return 4
    for f in failures:
        print(f.line(), file=sys.stderr)
    return 3 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
