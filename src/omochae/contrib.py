"""持ち寄りの投稿の受付・確認・公開。設計は docs/process/research/09。

判断の芯: 公開の記録は人の確認を通った物だけで、連絡先と写真は公開の記録に入れない。
受付箱は git に入れない。確認の前の他人のデータを push で外へ出さないため。
"""
import argparse
import base64
import json
import os
import pathlib
import re
import sys
from datetime import datetime, timedelta, timezone

from .model import Failure

ROOT = pathlib.Path(__file__).resolve().parents[2]
KINDS = {"photo", "info", "memory", "knowhow"}
ROLES = {"craftsperson", "shop", "scholar", "memory", "other"}
CERTAINTY = {"見た", "持っている", "聞いた", "覚えている", "作っている", "推測"}
RIGHTS = {"own_work", "permission", "public_domain", "unknown"}
LICENSES = {"CC-BY-4.0", "display_only"}
ATTESTS = ("agrees_terms", "adult_or_guardian", "no_identifiable_people")
MAX_BODY = 2000
MAX_IMAGE = 5 * 1024 * 1024
# 公開の文に個人の連絡先が紛れる事故を防ぐ。人の確認の補助で、これだけで安全とは言わない。
PII = {
    "メールアドレス": re.compile(r"[\w.+-]+\s*(?:@|＠)\s*[\w-]+(?:\.[\w-]+)+"),
    "電話番号": re.compile(r"(?<![\d-])(?:\+?81[-\s]?|0)\d{1,4}[-\s‐－ー]?\d{1,4}[-\s‐－ー]?\d{3,4}(?!\d)"),
    "郵便番号": re.compile(r"(?:〒\s*)?(?<!\d)\d{3}[-‐－ー]\d{4}(?!\d)"),
}
PUBLIC_TEXT_FIELDS = ("body", "display_name", "origin", "where_when", "toy_name")


def dirs():
    """試験で本物のデータに触らないよう、置き場を環境変数で替えられる。"""
    base = pathlib.Path(os.environ.get("OMOCHAE_DATA", ROOT / "data"))
    return {"inbox": base / "contributions_inbox", "public": base / "contributions", "media": base / "contributions_media"}


def check_intake(c):
    out = []
    def bad(where, msg):
        out.append(Failure("F10.intake", where, msg))
    if c.get("kind") not in KINDS:
        bad("kind", f"種類 {c.get('kind')} は決まりの外")
    if c.get("role") not in ROLES:
        bad("role", f"立場 {c.get('role')} は決まりの外")
    if c.get("certainty") not in CERTAINTY:
        bad("certainty", "確かさの種類が無い")
    body = c.get("body")
    if not isinstance(body, str) or not body.strip():
        bad("body", "本文が空")
    elif len(body) > MAX_BODY:
        bad("body", f"本文が {MAX_BODY} 字を超える")
    for key in ("display_name", "origin", "where_when", "toy_name", "source_id", "contact"):
        if not isinstance(c.get(key, ""), str) or len(c.get(key, "")) > 300:
            bad(key, "文字列でないか、長すぎる")
    attest = c.get("attest") if isinstance(c.get("attest"), dict) else {}
    for a in ATTESTS:
        if attest.get(a) is not True:
            bad(a, "同意が無い")
    out += check_rights(c, intake=True)
    return out


def check_rights(c, intake=False):
    out = []
    r = c.get("rights") if isinstance(c.get("rights"), dict) else {}
    has_photo = c.get("kind") == "photo" or bool(c.get("media"))
    if r.get("basis") not in RIGHTS:
        out.append(Failure("F10.rights", "basis", "権利の根拠が無い"))
    if r.get("license") not in LICENSES:
        out.append(Failure("F10.rights", "license", "公開の条件が無い"))
    if has_photo and not str(r.get("holder", "")).strip():
        out.append(Failure("F10.rights", "holder", "写真の権利の持ち主が無い"))
    # 受付では預かって人が問い合わせられるようにし、公開だけを止める。
    if not intake and r.get("basis") == "unknown":
        out.append(Failure("F10.rights", "basis", "権利の根拠が不明なので公開できない"))
    return out


def check_pii(c):
    out = []
    for field in PUBLIC_TEXT_FIELDS:
        text = str(c.get(field, ""))
        for name, pat in PII.items():
            if pat.search(text):
                out.append(Failure("F10.pii", field, f"公開する文に{name}の形がある"))
    return out


def _sniff(raw):
    if raw.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if raw.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    return None


def _next_id(d):
    # 公開済み・却下・取り下げの番号も使い回さないよう、両方の置き場を数える。
    nums = [int(p.stem.split(".")[0][2:]) for folder in (d["inbox"], d["public"]) for p in folder.glob("C-*.json")]
    return f"C-{max(nums, default=0) + 1:04d}"


def _now():
    return datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")


def submit(data, image_b64=None):
    """受付。返り値は (ID, failures)。失敗なら何も保存しない。"""
    failures = check_intake(data)
    raw = ext = None
    if image_b64:
        try:
            raw = base64.b64decode(image_b64, validate=True)
        except Exception:
            failures.append(Failure("F10.intake", "image", "画像を読めない"))
        if raw is not None:
            ext = _sniff(raw)
            if ext is None:
                failures.append(Failure("F10.intake", "image", "JPEG か PNG だけを受け付ける"))
            elif len(raw) > MAX_IMAGE:
                failures.append(Failure("F10.intake", "image", "画像が 5MB を超える"))
    elif data.get("kind") == "photo":
        failures.append(Failure("F10.intake", "image", "写真の投稿に画像が無い"))
    if failures:
        return None, failures
    d = dirs()
    for folder in d.values():
        folder.mkdir(parents=True, exist_ok=True)
    allowed = {"kind", "role", "certainty", "body", "display_name", "origin", "where_when", "toy_name", "source_id", "rights", "attest"}
    rec = {k: data[k] for k in allowed if k in data}
    while True:
        cid = _next_id(d)
        try:
            # 同時の投稿で同じ番号を上書きしないよう、作成だけを許す開き方にする。
            with open(d["inbox"] / f"{cid}.json", "x", encoding="utf-8") as f:
                rec.update(id=cid, status="received", received_at=_now(), media=[])
                if raw:
                    name = f"{cid}{ext}"
                    (d["media"] / name).write_bytes(raw)
                    rec["media"] = [name]
                json.dump(rec, f, ensure_ascii=False, indent=2)
            break
        except FileExistsError:
            continue
    if data.get("contact"):
        (d["inbox"] / f"{cid}.private").write_text(json.dumps({"contact": data["contact"]}, ensure_ascii=False), encoding="utf-8")
    return cid, []


def _load(cid):
    if not re.fullmatch(r"C-\d{4,}", cid):
        raise ValueError(f"ID の形が違う: {cid}")
    path = dirs()["inbox"] / f"{cid}.json"
    return path, json.loads(path.read_text(encoding="utf-8"))


def approve(cid, reviewer, note=""):
    """人の確認。公開の記録を書く。自動の処理から呼ばない（F9 と同じ線）。"""
    path, rec = _load(cid)
    failures = []
    if not reviewer or not reviewer.strip():
        failures.append(Failure("F10.review", cid, "確認した人の名前が無い"))
    if rec["status"] != "received":
        failures.append(Failure("F10.review", cid, f"状態 {rec['status']} からは公開できない"))
    failures += check_rights(rec) + check_pii(rec)
    if failures:
        return failures
    rec.update(status="approved", review={"by": reviewer.strip(), "at": _now(), "note": note})
    path.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
    public = {k: v for k, v in rec.items() if k not in ("attest", "review")}
    public["reviewed_at"] = rec["review"]["at"]
    (dirs()["public"] / f"{cid}.json").write_text(json.dumps(public, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return []


def reject(cid, reviewer, note=""):
    path, rec = _load(cid)
    if not reviewer or not reviewer.strip():
        return [Failure("F10.review", cid, "確認した人の名前が無い")]
    rec.update(status="rejected", review={"by": reviewer.strip(), "at": _now(), "note": note})
    path.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
    return []


def withdraw(cid):
    """取り下げ。公開の記録と写真を消し、番号だけを残す。投稿者の申し出に確実に応えるため、確認を挟まない。"""
    path, rec = _load(cid)
    d = dirs()
    (d["public"] / f"{cid}.json").unlink(missing_ok=True)
    for name in rec.get("media", []):
        (d["media"] / name).unlink(missing_ok=True)
    (d["inbox"] / f"{cid}.private").unlink(missing_ok=True)
    path.write_text(json.dumps({"id": cid, "status": "withdrawn", "withdrawn_at": _now()}, ensure_ascii=False, indent=2), encoding="utf-8")
    return []


def public_list(source_id=None):
    """公開の頁と Claude の道具の唯一の入口。確認済みの物しか返さない。"""
    out = []
    for p in sorted(dirs()["public"].glob("C-*.json")):
        rec = json.loads(p.read_text(encoding="utf-8"))
        if rec.get("status") == "approved" and (source_id is None or rec.get("source_id") == source_id):
            out.append(rec)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(prog="omochae.contrib", exit_on_error=False)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("inbox")
    for name in ("approve", "reject"):
        s = sub.add_parser(name)
        s.add_argument("id")
        s.add_argument("--reviewer", required=True)
        s.add_argument("--note", default="")
    sub.add_parser("withdraw").add_argument("id")
    try:
        args = ap.parse_args(argv)
    except (argparse.ArgumentError, SystemExit):
        return 4
    try:
        if args.cmd == "inbox":
            for p in sorted(dirs()["inbox"].glob("C-*.json")):
                rec = json.loads(p.read_text(encoding="utf-8"))
                print(rec["id"], rec["status"], rec.get("kind", ""), str(rec.get("body", ""))[:40].replace("\n", " "))
            return 0
        fn = {"approve": approve, "reject": reject}.get(args.cmd)
        failures = fn(args.id, args.reviewer, args.note) if fn else withdraw(args.id)
    except (FileNotFoundError, ValueError) as e:
        print(f"検査できない: {e}", file=sys.stderr)
        return 4
    for f in failures:
        print(f.line(), file=sys.stderr)
    return 3 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
