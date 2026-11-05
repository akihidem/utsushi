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
import unicodedata
from datetime import datetime, timedelta, timezone

from PIL import Image, ImageOps, UnidentifiedImageError

from . import store
from .model import Failure

ROOT = pathlib.Path(__file__).resolve().parents[2]
# 頁に出す札。手元の画面とギャラリーで同じ語にするため、受付の決まりと一緒に持つ。
KIND_LABEL = {"photo": "写真", "info": "情報", "memory": "思い出", "knowhow": "作り方の知見"}
# 職人・玩具店・実際に遊んだ人を同じ入口で受ける（本人の決定 11-05、#285）。思い出のある人と遊んだ人を分けるのは、昔の思い出と今遊んだ話が混ざらないようにするため。
ROLE_LABEL = {"craftsperson": "職人", "shop": "玩具店・お店", "played": "遊んだ人", "scholar": "調べている人", "memory": "思い出を持つ人", "other": "その他"}
KINDS = set(KIND_LABEL)
ROLES = set(ROLE_LABEL)
CERTAINTY = {"見た", "持っている", "聞いた", "覚えている", "作っている", "売っている", "遊んだ", "推測"}
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
# 文の中の「@」や「at」を拾いすぎないよう、英数字の形に絞る。
# 頭は英数字の並びの始まりからだけ読む（#161）。途中から読み直すと文の長さの 2 乗で遅くなるが、並びは @ の手前まで続くので拾う物は変わらない。
LOCAL = r"(?<![A-Za-z0-9._+-])[A-Za-z0-9._+-]+"
EMAIL = re.compile(LOCAL + r"\s*@\s*[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*"
                   r"|" + LOCAL + r"\s*(?:\[at\]|\(at\)|アット)\s*[A-Za-z0-9-]+\.[A-Za-z]{2,}"
                   r"|" + LOCAL + r"\s+at\s+[A-Za-z0-9-]+(?:\s*\.\s*(?:com|jp|net|org|co\.jp)\b|\s+dot\s+[A-Za-z]{2,})", re.I)
PHONE_RUN = re.compile(r"\+?\d[\d\s().\-/・~〜‐‑‒–—―−ー]*\d")
POSTAL = re.compile(r"(?:〒|郵便番号)\s*\d{3}[\s\-‐‑‒–—―−ー]?\d{4}|(?<!\d)\d{3}[\-‐‑‒–—―−ー]\d{4}(?!\d)")
PUBLIC_TEXT_FIELDS = ("body", "display_name", "origin", "where_when", "toy_name", "source_id")
# 状態の移り方を 1 か所で決める。承認の後の却下は認めない（公開を下げるのは取り下げだけにして、消し忘れを無くす）。
# 取り下げはどの状態からでもでき、受付の記録ごと消すので、ここには書かない。
TRANSITIONS = {"received": {"approved", "rejected"}, "approved": set(), "rejected": set()}


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
    """持ち寄りの置き場は連絡先を持つので、同じ機械の他の利用者から読めない形で書く。"""
    store.write_atomic(path, data, exclusive=exclusive, mode=0o600)


def _dump(rec):
    return json.dumps(rec, ensure_ascii=False, indent=2) + "\n"


def _bad_text(s):
    """保存も表示もできない文字を見つける。端末の制御文字は確認する人の画面を乱すので受け付けない。"""
    try:
        s.encode("utf-8")
    except UnicodeEncodeError:
        return True
    # 文字の向きを変える制御文字は、確認する人に見える文と保存される文を違わせられるので断る。
    return any((unicodedata.category(ch) == "Cc" and ch not in "\n\t") or 0x202A <= ord(ch) <= 0x202E or 0x2066 <= ord(ch) <= 0x2069 or ord(ch) in (0x200E, 0x200F, 0x061C) for ch in s)


def _normalize(text):
    """全角や見えない文字で検査をすり抜けないよう、そろえてから調べる。"""
    text = unicodedata.normalize("NFKC", text)
    # 異体字セレクタも見えない文字なので一緒に消す。
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Cf" and not 0xFE00 <= ord(ch) <= 0xFE0F)
    return text.replace("(0)", "")


def _looks_like_phone(text):
    """電話番号の形（0 始まり 10〜11 桁、塊は 3 つまで、先頭は 2 桁以上）を探す。

    前後の別の数字に引きずられないよう塊の窓で見るが、寸法や日付の並びを拾わないよう窓を絞る。国番号 81 の塊は別に数える。
    """
    for m in PHONE_RUN.finditer(text):
        groups = re.findall(r"\d+", m.group())
        for i, first in enumerate(groups):
            if first == "81":
                digits = "0" + "".join(groups[i + 1 : i + 4]).lstrip("0")
                if 10 <= len(digits) <= 11:
                    return True
            for j in range(i + 1, min(i + 3, len(groups)) + 1):
                digits = "".join(groups[i:j])
                if len(first) >= 2 and digits.startswith("0") and 10 <= len(digits) <= 11:
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


def too_long(fields):
    """長さの上限を越えた欄を、断る文にして返す。検査の前に見て、貼り付けの長い文を検査へ回さない（#161）。fields は (欄, 文) の並び。"""
    return [(where, f"{where} が {MAX_BODY} 字を超える") for where, text in fields if len(text or "") > MAX_BODY]


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
    try:
        # MPO はスマホの JPEG に多く、Pillow は JPEG の読み手から MPO として返す。下で JPEG として描き直す。
        with Image.open(io.BytesIO(raw), formats=("JPEG", "PNG")) as im:
            if im.size[0] * im.size[1] > MAX_PIXELS:  # Pillow の上限は警告の倍まで通るので、読む前に自分で比べる
                return None, None
            fmt = "PNG" if im.format == "PNG" else "JPEG"
            im.load()
            # 付帯情報を消すと向きも消えるので、先に向きを画素へ反映する。
            im = ImageOps.exif_transpose(im)
            if im.mode.startswith("I"):  # 16bit をそのまま 8bit にすると真っ白になる
                im = im.point(lambda v: v / 256).convert("L")
            mode = "RGB" if fmt == "JPEG" or im.mode not in ("RGB", "RGBA", "LA", "P") else "RGBA"
            source = im.convert(mode)
            clean = Image.new(mode, source.size)
            clean.paste(source)
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


def _received_count(d):
    """確認待ちの数。読めないファイルや、取り下げと同時に消えたファイルで受付全体を止めない。"""
    count = 0
    for p in d["inbox"].glob("C-*.json"):
        try:
            count += '"status": "received"' in p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
    return count


def submit(data, image_b64=None):
    """受付。返り値は (ID, failures)。失敗なら何も保存しない。"""
    checked = dict(data)
    if isinstance(checked.get("body"), str):
        checked["body"] = checked["body"].replace("\r\n", "\n")  # ブラウザの改行を、使えない文字として断らない
    if image_b64:
        checked["_has_image"] = True
    failures = check_intake(checked)
    # 公開の時でなく受付の時に知らせる。形の検査は誤検知が必ず残るので、断り切らず、投稿者が確かめれば受け付けて確認者に印を渡す。
    pii = check_pii(checked)
    if not data.get("pii_confirmed"):
        failures += pii
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
    elif data.get("kind") == "photo" and not data.get("form_files"):
        # フォームの添付（ドライブのリンク）は、本人が確かめて手元へ移すまでファイルが無い。リンクがあれば受け付けて預かる（f17、11-04）。
        failures.append(Failure("F10.intake", "image", "写真の投稿に画像が無い"))
    if failures:
        return None, failures
    d = dirs()
    _ensure_dirs()
    if _received_count(d) >= MAX_INBOX:
        return None, [Failure("F10.intake", "inbox", "受付箱がいっぱい")]
    # 知らない項目を保存しない。公開の記録に紛れ込む道を入口で断つ。
    allowed = {"kind", "role", "certainty", "body", "display_name", "origin", "where_when", "toy_name", "source_id"}
    rec = {k: checked[k] for k in allowed if k in checked}
    rec["attest"] = {a: True for a in ATTESTS}
    r = data["rights"]
    rec["rights"] = {"basis": r["basis"], "holder": r.get("holder", ""), "license": r["license"]}
    rec.update(status="received", received_at=_now(), media=[], pii_flag=bool(pii))
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
    try:
        if raw:
            _write_atomic(d["media"] / f"{cid}{ext}", raw)
        private = {k: data[k] for k in ("contact", "form_files") if data.get(k)}
        if private:
            # 連絡先とフォームの添付のリンクは、公開の記録に入らない預かりの所に置く（本人が確かめて手元へ移す）。
            _write_atomic(d["inbox"] / f"{cid}.private", json.dumps(private, ensure_ascii=False))
    except OSError:
        # 写真の無い記録を承認できる形で残さない。投稿者には失敗として返る。
        (d["inbox"] / f"{cid}.json").unlink(missing_ok=True)
        (d["media"] / f"{cid}{ext}").unlink(missing_ok=True)
        raise
    return cid, []


def _check_id(cid):
    # 全角の数字や桁の違う番号を別の番号として通さない。
    if not re.fullmatch(r"C-(?:[0-9]{4}|[1-9][0-9]{4,})", cid):
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


def approve(cid, reviewer, note="", pii_cleared=False):
    """人の確認。公開の記録を書く。人が画面で確かめる入口は CLI の approve だけ（F9 と同じ線）。"""
    path, rec = _load(cid)
    failures = []
    if not isinstance(reviewer, str) or not reviewer.strip():
        failures.append(Failure("F10.review", cid, "確認した人の名前が無い"))
    if "approved" not in TRANSITIONS.get(rec.get("status"), set()):
        # 却下の記録は中身を消してあるので、他の検査を重ねず、状態の理由だけを返す。
        return failures + [Failure("F10.review", cid, f"状態 {rec.get('status')} からは公開できない")]
    if (dirs()["withdrawn"] / f"{cid}.json").exists():
        failures.append(Failure("F10.review", cid, "取り下げられた番号は公開できない"))
    failures += check_rights(rec)
    # 形の検査に当たった文は、人が全文を読んで連絡先でないと判断した時だけ通す。
    if not pii_cleared:
        failures += check_pii(rec)
    for name in rec.get("media", []):
        if not (dirs()["media"] / name).exists():
            failures.append(Failure("F10.review", cid, f"写真 {name} が無い"))
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
    (d["public"] / f"{cid}.json").unlink(missing_ok=True)  # 承認の途中で失敗した物が公開に残らないように
    # 本文も残さない。公開しないと決めた他人の文を持ち続ける理由が無い。
    _write_atomic(path, _dump({"id": cid, "status": "rejected", "review": {"by": reviewer.strip(), "at": _now(), "note": note}}))
    return []


def withdraw(cid):
    """取り下げ。投稿者の申し出に確実に応えるため、確認を挟まず、受付箱が無い機械でも効かせる。

    番号だけの記録を残し、公開の一覧で照合する。公開の記録が別の経路で戻っても、再び出ないようにするため。
    """
    _check_id(cid)
    d = dirs()
    _ensure_dirs()
    # 打ち間違いの番号で「取り下げた」と答えない。
    if not ((d["inbox"] / f"{cid}.json").exists() or (d["public"] / f"{cid}.json").exists() or (d["withdrawn"] / f"{cid}.json").exists()):
        raise ValueError(f"その番号の投稿は無い: {cid}")
    _write_atomic(d["withdrawn"] / f"{cid}.json", _dump({"id": cid, "status": "withdrawn", "withdrawn_at": _now()}))
    (d["public"] / f"{cid}.json").unlink(missing_ok=True)
    for folder in (d["media"],):
        for p in folder.glob(f"{cid}.*"):
            p.unlink(missing_ok=True)
    (d["inbox"] / f"{cid}.private").unlink(missing_ok=True)
    (d["inbox"] / f"{cid}.json").unlink(missing_ok=True)
    return []


def _valid_public(rec):
    return isinstance(rec, dict) and all(isinstance(rec.get(k), str) for k in ("id", "body", "kind", "role", "certainty")) and rec["kind"] in KINDS and rec["role"] in ROLES and isinstance(rec.get("rights"), dict) and all(isinstance(rec["rights"].get(k, ""), str) for k in ("holder", "license", "basis")) and all(isinstance(n, str) for n in rec.get("media", []) if isinstance(rec.get("media", []), list)) and isinstance(rec.get("media", []), list) and all(isinstance(rec.get(k, ""), str) for k in ("display_name", "origin", "where_when", "toy_name", "source_id"))


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
    if rec.get("pii_flag"):
        print("注意: 連絡先の形に当たった文です。全文を読み、連絡先でなければ approve に --pii-checked を付けます")
    private = dirs()["inbox"] / f"{cid}.private"
    if private.exists():
        # 確認で止めた時に再投稿を頼めるように、確認する人にだけ見せる。
        print("連絡先（公開しない）:", json.loads(private.read_text(encoding="utf-8")).get("contact", ""))
    print("公開の前に写真も確かめる:", ", ".join(str(dirs()["media"] / n) for n in rec.get("media", [])) or "写真なし")


def _show_if_present(cid):
    _check_id(cid)
    if (dirs()["inbox"] / f"{cid}.json").exists():
        _show(cid)


def _human_confirm(cid, action="公開"):
    """人が端末で番号を打った時だけ進める。AI や自動の処理と、番号の打ち間違いを止めるための補助で、完全な保証ではない。"""
    try:
        # 端末は seek できないので、普通の open の読み書きの形では開けない。
        fd = os.open("/dev/tty", os.O_RDWR | os.O_NOCTTY)
        with io.TextIOWrapper(io.FileIO(fd, "r+"), encoding="utf-8") as tty:
            tty.write(f"内容を確かめましたか。{action}するなら {cid} と打ってください: ")
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
        if name == "approve":
            s.add_argument("--pii-checked", action="store_true", help="形の検査に当たった文を人が読み、連絡先でないと判断した")
    sub.add_parser("withdraw").add_argument("id")
    try:
        args = ap.parse_args(argv)
    except SystemExit as e:
        return 0 if e.code == 0 else 4
    try:
        if args.cmd == "inbox":
            unreadable = 0
            for p in sorted(dirs()["inbox"].glob("C-*.json")):
                try:
                    rec = json.loads(p.read_text(encoding="utf-8"))
                    print(rec["id"], rec["status"], rec.get("kind", ""), "".join(ch for ch in str(rec.get("body", ""))[:40] if ch.isprintable()))
                except (OSError, ValueError, KeyError, TypeError):
                    print(f"{p.name} 読めない記録", file=sys.stderr)
                    unreadable += 1
            return 4 if unreadable else 0
        if args.cmd == "show":
            _show(args.id)
            return 0
        if args.cmd == "approve":
            _show(args.id)
            if not _human_confirm(args.id):
                print(Failure("F10.review", args.id, "端末での人の確認が無い").line(), file=sys.stderr)
                return 3
            failures = approve(args.id, args.reviewer, args.note, args.pii_checked)
        elif args.cmd == "reject":
            failures = reject(args.id, args.reviewer, args.note)
        else:
            _show_if_present(args.id)
            # 消すと戻せないので、別の人の番号を打ち間違えていないか確かめる。
            if not _human_confirm(args.id, "取り下げ"):
                print(Failure("F10.review", args.id, "端末での人の確認が無い").line(), file=sys.stderr)
                return 3
            failures = withdraw(args.id)
            print(f"取り下げた: {args.id}")
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as e:
        print(f"検査できない: {type(e).__name__}: {e}", file=sys.stderr)
        return 4
    for f in failures:
        print(f.line(), file=sys.stderr)
    return 3 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
