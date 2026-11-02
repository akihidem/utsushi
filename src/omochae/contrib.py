"""持ち寄りの投稿の受付・確認・公開。設計は docs/process/research/09。

判断の芯: 公開の記録は人の確認を通った物だけで、連絡先と写真は公開の記録に入れない。
受付箱は git に入れない。確認の前の他人のデータを push で外へ出さないため。
"""
import argparse
import base64
import io
import json
import os
import pathlib
import re
import sys
import tempfile
import unicodedata
from datetime import datetime, timedelta, timezone

from PIL import Image, UnidentifiedImageError

from .model import Failure

ROOT = pathlib.Path(__file__).resolve().parents[2]
KINDS = {"photo", "info", "memory", "knowhow"}
ROLES = {"craftsperson", "shop", "scholar", "memory", "other"}
CERTAINTY = {"見た", "持っている", "聞いた", "覚えている", "作っている", "推測"}
RIGHTS = {"own_work", "permission", "public_domain", "unknown"}
LICENSES = {"CC-BY-4.0", "display_only"}
ATTESTS = ("agrees_terms", "adult_or_guardian", "no_identifiable_people")
MAX_BODY = 2000
MAX_FIELD = 300
MAX_HOLDER = 100
MAX_IMAGE = 5 * 1024 * 1024
MAX_PIXELS = 40_000_000
# 受付の総量の上限。手元の機械のディスクを投稿で埋めさせないため。
MAX_INBOX = 2000
TEXT_FIELDS = ("display_name", "origin", "where_when", "toy_name", "source_id", "contact")
PUBLIC_FIELDS = ("id", "status", "received_at", "kind", "role", "certainty", "body", "display_name", "origin", "where_when", "toy_name", "source_id", "rights", "media")
ID_NAME = re.compile(r"^C-(\d{4,})\.json$")
# 公開の文に個人の連絡先が紛れる事故を減らす。人の確認の補助で、これだけで安全とは言わない。
EMAIL = re.compile(r"[\w.+-]+\s*@\s*[\w-]+(?:\s*\.\s*[\w-]+)+|\b\w+\s+at\s+\w+\s+dot\s+\w+", re.I)
PHONE_RUN = re.compile(r"\+?[\d][\d\s().\-‐‑‒–—―−ー]{7,}\d")
POSTAL = re.compile(r"(?:〒|郵便番号)\s*\d{3}[\s\-‐‑‒–—―−ー]?\d{4}|(?<!\d)\d{3}[\-‐‑‒–—―−ー]\d{4}(?!\d)")
PUBLIC_TEXT_FIELDS = ("body", "display_name", "origin", "where_when", "toy_name", "source_id")
# 状態の移り方を 1 か所で決める。承認の後の却下は認めない（公開を下げるのは取り下げだけにして、消し忘れを無くす）。
TRANSITIONS = {"received": {"approved", "rejected", "withdrawn"}, "approved": {"withdrawn"}, "rejected": {"withdrawn"}, "withdrawn": set()}


def dirs():
    """試験で本物のデータに触らないよう、置き場を環境変数で替えられる。"""
    base = pathlib.Path(os.environ.get("OMOCHAE_DATA", ROOT / "data"))
    return {"inbox": base / "contributions_inbox", "public": base / "contributions", "media": base / "contributions_media", "withdrawn": base / "contributions_withdrawn"}


def _ensure_dirs():
    for name, folder in dirs().items():
        folder.mkdir(parents=True, exist_ok=True)
        if name in ("inbox", "media"):
            os.chmod(folder, 0o700)  # 連絡先と確認前の写真を、同じ機械の他の利用者から守る


def _write_atomic(path, data, exclusive=False):
    """途中の状態を読ませないよう、一時ファイルに書いてから確定する。exclusive は同じ番号を上書きしない。"""
    payload = data if isinstance(data, bytes) else data.encode("utf-8")
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(payload)
        os.chmod(tmp, 0o600)
        if exclusive:
            os.link(tmp, path)
        else:
            os.replace(tmp, path)
            tmp = None
    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)


def _dump(rec):
    return json.dumps(rec, ensure_ascii=False, indent=2) + "\n"


def _bad_text(s):
    """保存も表示もできない文字を見つける。端末の制御文字は確認する人の画面を乱すので受け付けない。"""
    try:
        s.encode("utf-8")
    except UnicodeEncodeError:
        return True
    return any(unicodedata.category(ch) == "Cc" and ch not in "\n\t" for ch in s)


def _normalize(text):
    """全角や見えない文字で検査をすり抜けないよう、そろえてから調べる。"""
    text = unicodedata.normalize("NFKC", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Cf")
    return text.replace("。", ".").replace("(0)", "")


def _looks_like_phone(text):
    for m in PHONE_RUN.finditer(text):
        digits = re.sub(r"\D", "", m.group())
        if digits.startswith("81"):
            digits = "0" + digits[2:]
        if digits.startswith("0") and 10 <= len(digits) <= 11:
            return True
    return False


def check_intake(c):
    out = []

    def bad(where, msg):
        out.append(Failure("F10.intake", where, msg))

    def enum(key, allowed, label):
        v = c.get(key)
        if not isinstance(v, str) or v not in allowed:
            bad(key, f"{label}が決まりの外か、無い")

    enum("kind", KINDS, "種類")
    enum("role", ROLES, "立場")
    enum("certainty", CERTAINTY, "確かさの種類")
    body = c.get("body")
    if not isinstance(body, str) or not body.strip():
        bad("body", "本文が空")
    elif len(body) > MAX_BODY:
        bad("body", f"本文が {MAX_BODY} 字を超える")
    elif _bad_text(body):
        bad("body", "使えない文字がある")
    for key in TEXT_FIELDS:
        v = c.get(key, "")
        if not isinstance(v, str) or len(v) > MAX_FIELD or _bad_text(v):
            bad(key, "文字列でないか、長すぎるか、使えない文字がある")
    if c.get("kind") == "info" and not str(c.get("origin", "")).strip():
        bad("origin", "情報には出所が要る")
    if c.get("kind") == "memory" and not str(c.get("where_when", "")).strip():
        bad("where_when", "思い出には、いつ頃・どこでが要る（おおよそでよい）")
    attest = c.get("attest") if isinstance(c.get("attest"), dict) else {}
    for a in ATTESTS:
        if attest.get(a) is not True:
            bad(a, "同意が無い")
    out += check_rights(c, intake=True)
    return out


def check_rights(c, intake=False):
    out = []
    r = c.get("rights") if isinstance(c.get("rights"), dict) else {}
    # 画像が付いていれば種類によらず写真として扱う。後で永久に公開できない投稿を受け付けないため。
    has_photo = c.get("kind") == "photo" or bool(c.get("media")) or bool(c.get("_has_image"))
    basis, license_, holder = r.get("basis"), r.get("license"), r.get("holder", "")
    if not isinstance(basis, str) or basis not in RIGHTS:
        out.append(Failure("F10.rights", "basis", "権利の根拠が無い"))
    if not isinstance(license_, str) or license_ not in LICENSES:
        out.append(Failure("F10.rights", "license", "公開の条件が無い"))
    if not isinstance(holder, str) or len(holder) > MAX_HOLDER or _bad_text(holder):
        out.append(Failure("F10.rights", "holder", "権利の持ち主が文字列でないか、長すぎる"))
    elif has_photo and not holder.strip():
        out.append(Failure("F10.rights", "holder", "写真の権利の持ち主が無い"))
    # 受付では預かって人が問い合わせられるようにし、公開だけを止める。
    if not intake and basis == "unknown":
        out.append(Failure("F10.rights", "basis", "権利の根拠が不明なので公開できない"))
    return out


def check_pii(c):
    out = []
    holder = c.get("rights", {}).get("holder", "") if isinstance(c.get("rights"), dict) else ""
    for field, raw in [(f, c.get(f, "")) for f in PUBLIC_TEXT_FIELDS] + [("rights.holder", holder)]:
        text = _normalize(str(raw))
        for name, hit in (("メールアドレス", EMAIL.search(text)), ("電話番号", _looks_like_phone(text)), ("郵便番号", POSTAL.search(text))):
            if hit:
                out.append(Failure("F10.pii", field, f"公開する文に{name}の形がある"))
    return out


def _clean_image(raw):
    """画像として本当に読めるかを確かめ、描き直す。位置情報などの付帯情報を公開に持ち越さないため。返り値は (bytes, 拡張子)。"""
    Image.MAX_IMAGE_PIXELS = MAX_PIXELS
    try:
        with Image.open(io.BytesIO(raw)) as im:
            if im.format not in ("JPEG", "PNG"):
                return None, None
            im.load()
            fmt = im.format
            mode = "RGB" if fmt == "JPEG" or im.mode not in ("RGB", "RGBA") else im.mode
            clean = Image.new(mode, im.size)
            clean.paste(im.convert(mode))
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, SyntaxError):
        return None, None
    buf = io.BytesIO()
    clean.save(buf, format=fmt, quality=90)
    return buf.getvalue(), ".jpg" if fmt == "JPEG" else ".png"


def _all_ids(d):
    nums = []
    for folder in (d["inbox"], d["public"], d["withdrawn"]):
        for p in folder.glob("C-*.json"):
            m = ID_NAME.match(p.name)
            if m:
                nums.append(int(m.group(1)))
    return nums


def _now():
    return datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")


def submit(data, image_b64=None):
    """受付。返り値は (ID, failures)。失敗なら何も保存しない。"""
    checked = dict(data)
    if image_b64:
        checked["_has_image"] = True
    failures = check_intake(checked)
    raw = ext = None
    if image_b64:
        try:
            decoded = base64.b64decode(image_b64, validate=True)
        except Exception:
            decoded = None
            failures.append(Failure("F10.intake", "image", "画像を読めない"))
        if decoded is not None:
            if len(decoded) > MAX_IMAGE:
                failures.append(Failure("F10.intake", "image", "画像が 5MB を超える"))
            else:
                raw, ext = _clean_image(decoded)
                if raw is None:
                    failures.append(Failure("F10.intake", "image", "JPEG か PNG の画像だけを受け付ける"))
    elif data.get("kind") == "photo":
        failures.append(Failure("F10.intake", "image", "写真の投稿に画像が無い"))
    if failures:
        return None, failures
    d = dirs()
    _ensure_dirs()
    if sum(1 for _ in d["inbox"].glob("C-*.json")) >= MAX_INBOX:
        return None, [Failure("F10.intake", "inbox", "受付箱がいっぱい")]
    # 知らない項目を保存しない。公開の記録に紛れ込む道を入口で断つ。
    allowed = {"kind", "role", "certainty", "body", "display_name", "origin", "where_when", "toy_name", "source_id", "attest"}
    rec = {k: data[k] for k in allowed if k in data}
    r = data["rights"]
    rec["rights"] = {"basis": r["basis"], "holder": r.get("holder", ""), "license": r["license"]}
    rec.update(status="received", received_at=_now(), media=[])
    while True:
        cid = f"C-{max(_all_ids(d), default=0) + 1:04d}"
        rec["id"] = cid
        if raw:
            rec["media"] = [f"{cid}{ext}"]
        try:
            _write_atomic(d["inbox"] / f"{cid}.json", _dump(rec), exclusive=True)
            break
        except FileExistsError:
            continue
    if raw:
        _write_atomic(d["media"] / f"{cid}{ext}", raw)
    if data.get("contact"):
        _write_atomic(d["inbox"] / f"{cid}.private", json.dumps({"contact": data["contact"]}, ensure_ascii=False))
    return cid, []


def _check_id(cid):
    if not re.fullmatch(r"C-\d{4,}", cid):
        raise ValueError(f"ID の形が違う: {cid}")


def _load(cid):
    _check_id(cid)
    path = dirs()["inbox"] / f"{cid}.json"
    return path, json.loads(path.read_text(encoding="utf-8"))


def public_record(rec):
    """公開の記録は許可した項目だけで作る。除外の一覧にすると、新しい項目が黙って漏れるため。"""
    out = {k: rec[k] for k in PUBLIC_FIELDS if k in rec}
    r = rec.get("rights", {})
    out["rights"] = {k: r.get(k, "") for k in ("basis", "holder", "license")}
    return out


def approve(cid, reviewer, note=""):
    """人の確認。公開の記録を書く。人が画面で確かめる入口は CLI の approve だけ（F9 と同じ線）。"""
    path, rec = _load(cid)
    failures = []
    if not isinstance(reviewer, str) or not reviewer.strip():
        failures.append(Failure("F10.review", cid, "確認した人の名前が無い"))
    if "approved" not in TRANSITIONS.get(rec.get("status"), set()):
        failures.append(Failure("F10.review", cid, f"状態 {rec.get('status')} からは公開できない"))
    if (dirs()["withdrawn"] / f"{cid}.json").exists():
        failures.append(Failure("F10.review", cid, "取り下げられた番号は公開できない"))
    failures += check_rights(rec) + check_pii(rec)
    if failures:
        return failures
    _ensure_dirs()
    at = _now()
    public = public_record({**rec, "status": "approved"})
    public["reviewed_at"] = at
    # 先に公開の記録を書く。途中で失敗しても、もう一度 approve すれば同じ結果に行き着く。
    _write_atomic(dirs()["public"] / f"{cid}.json", _dump(public))
    rec.update(status="approved", review={"by": reviewer.strip(), "at": at, "note": note})
    _write_atomic(path, _dump(rec))
    return []


def reject(cid, reviewer, note=""):
    """却下。公開しないと決めた他人のデータを持ち続けないよう、写真と連絡先を消す。"""
    path, rec = _load(cid)
    if not isinstance(reviewer, str) or not reviewer.strip():
        return [Failure("F10.review", cid, "確認した人の名前が無い")]
    if "rejected" not in TRANSITIONS.get(rec.get("status"), set()):
        return [Failure("F10.review", cid, f"状態 {rec.get('status')} からは却下できない。公開済みなら取り下げる")]
    d = dirs()
    for name in rec.get("media", []):
        (d["media"] / name).unlink(missing_ok=True)
    (d["inbox"] / f"{cid}.private").unlink(missing_ok=True)
    rec.update(status="rejected", media=[], review={"by": reviewer.strip(), "at": _now(), "note": note})
    _write_atomic(path, _dump(rec))
    return []


def withdraw(cid):
    """取り下げ。投稿者の申し出に確実に応えるため、確認を挟まず、受付箱が無い機械でも効かせる。

    番号だけの記録を残し、公開の一覧で照合する。公開の記録が別の経路で戻っても、再び出ないようにするため。
    """
    _check_id(cid)
    d = dirs()
    _ensure_dirs()
    _write_atomic(d["withdrawn"] / f"{cid}.json", _dump({"id": cid, "status": "withdrawn", "withdrawn_at": _now()}))
    (d["public"] / f"{cid}.json").unlink(missing_ok=True)
    for folder in (d["media"],):
        for p in folder.glob(f"{cid}.*"):
            p.unlink(missing_ok=True)
    (d["inbox"] / f"{cid}.private").unlink(missing_ok=True)
    (d["inbox"] / f"{cid}.json").unlink(missing_ok=True)
    return []


def _valid_public(rec):
    return isinstance(rec, dict) and all(isinstance(rec.get(k), str) for k in ("id", "body", "kind", "role", "certainty")) and rec["kind"] in KINDS and rec["role"] in ROLES and isinstance(rec.get("rights"), dict) and all(isinstance(rec["rights"].get(k, ""), str) for k in ("holder", "license", "basis")) and isinstance(rec.get("media", []), list)


def public_list(source_id=None):
    """公開の頁と Claude の道具の唯一の入口。確認済みで取り下げのない物だけを返す。壊れた 1 件で全体を止めない。"""
    out = []
    d = dirs()
    for p in sorted(d["public"].glob("C-*.json")):
        if (d["withdrawn"] / p.name).exists():
            continue
        try:
            rec = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            print(f"読めない公開の記録を飛ばした: {p.name}: {type(e).__name__}", file=sys.stderr)
            continue
        if not _valid_public(rec):
            print(f"形の違う公開の記録を飛ばした: {p.name}", file=sys.stderr)
            continue
        if rec.get("status") == "approved" and (source_id is None or rec.get("source_id") == source_id):
            out.append(rec)
    return out


def _show(cid):
    """確認する人に、公開される項目を全部見せる。本文の一部だけで承認させないため。"""
    _, rec = _load(cid)
    print(json.dumps(public_record(rec), ensure_ascii=False, indent=2))
    print("公開の前に写真も確かめる:", ", ".join(str(dirs()["media"] / n) for n in rec.get("media", [])) or "写真なし")


def _human_confirm(cid):
    """人が端末で番号を打った時だけ公開する。AI や自動の処理の承認を止めるための補助で、完全な保証ではない。"""
    try:
        with open("/dev/tty", "r+", encoding="utf-8") as tty:
            tty.write(f"公開される内容を確かめましたか。公開するなら {cid} と打ってください: ")
            tty.flush()
            return tty.readline().strip() == cid
    except OSError:
        return False


def main(argv=None):
    ap = argparse.ArgumentParser(prog="omochae.contrib")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("inbox")
    sub.add_parser("show").add_argument("id")
    for name in ("approve", "reject"):
        s = sub.add_parser(name)
        s.add_argument("id")
        s.add_argument("--reviewer", required=True)
        s.add_argument("--note", default="")
    sub.add_parser("withdraw").add_argument("id")
    try:
        args = ap.parse_args(argv)
    except SystemExit as e:
        return 0 if e.code == 0 else 4
    try:
        if args.cmd == "inbox":
            for p in sorted(dirs()["inbox"].glob("C-*.json")):
                try:
                    rec = json.loads(p.read_text(encoding="utf-8"))
                    print(rec["id"], rec["status"], rec.get("kind", ""), "".join(ch for ch in str(rec.get("body", ""))[:40] if ch.isprintable()))
                except (OSError, ValueError, KeyError, TypeError):
                    print(f"{p.name} 読めない記録", file=sys.stderr)
            return 0
        if args.cmd == "show":
            _show(args.id)
            return 0
        if args.cmd == "approve":
            _show(args.id)
            if not _human_confirm(args.id):
                print(Failure("F10.review", args.id, "端末での人の確認が無い").line(), file=sys.stderr)
                return 3
            failures = approve(args.id, args.reviewer, args.note)
        elif args.cmd == "reject":
            failures = reject(args.id, args.reviewer, args.note)
        else:
            failures = withdraw(args.id)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as e:
        print(f"検査できない: {type(e).__name__}: {e}", file=sys.stderr)
        return 4
    for f in failures:
        print(f.line(), file=sys.stderr)
    return 3 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
