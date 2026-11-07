"""ワークショップで作られたおもちゃ（作例）の受け口。

本人の言葉（11-07）「サイトにワークショップで作られたおもちゃを掲載したい。写真データはこれから上げる」。中心は 11-04 と 11-06 のワークショップ
（本人）で、写真は全部使ってよい（本人の決め 11-07）。ワークショップは 11 月 4・5・6・7 日の 4 回（本人の言葉 11-07。WORKSHOP_DAYS）。

判断の芯:
- 作例は、記録（records）と写真（記録の写真の置き場）として入れる。記録には via="workshop" と作った日（made_on）を持たせ、
  records.all_records の既定から外す（動画の受け口と同じ形。観察の無い作例を、束・輪の数・審査用の頁・「他の人が作った物」に混ぜない）。
  写真の置き場が学ぶ人の写真と同じなので、出す前の人の確かめ（omochae.media_review）を、そのまま通る。
- 出すのは、人が「物だけ」と確かめた写真だけ（media_review.public）。既定は出さない。
- 撮影の情報（位置など）は、取り込む時に落とす（web.techo_site.save_media）。HEIC は JPEG に描き直すので、情報は残らない。
- 写真の元は repo に入れない（置き場はサーバの記録の置き場。OMOCHAE_DATA）。作った人の名と感想は持たない。
- どの玩具の作例か・ワークショップの日・刷った型紙の組（分かる日だけ）は、取り込む人が渡す（写真からは分からない）。

使い方（端末で）:
  1. iPhone の写真（HEIC）は、先に JPEG にする。pillow-heif のある python で回す（pillow-heif の中の x265 は GPL なので、repo の依存に
     入れない。この段は Pillow と pillow-heif と標準の部品だけで動く）:
       <pillow-heif のある python> -m web.sakurei jpeg <写真...> --out <置き場の外の一時の所>
  2. 取り込む（repo の python で）:
       python -m web.sakurei add --toy <玩具の印> --day YYYY-MM-DD [--set <刷った型紙の組、例 goraigo-v10>] <写真...>
  3. 人が確かめる: python -m omochae.media_review list / approve <記録> <名> --shows object --reviewer <名>
  4. 一覧: python -m web.sakurei list

exit code: 0 = 通る / 3 = 受けない物がある（知らない玩具・読めない日・写真として読めない）/ 4 = 呼び方の誤り・検査できない（HEIC を読む部品が無いなど）。
"""
import argparse
import hashlib
import io
import pathlib
import re
import sys
from datetime import date

# ワークショップの日（本人の言葉 11-07「ワークショップ 4 回は 11 月 4・5・6・7 日でよい。回数の数え方と改善の歴史の表はこの 4 回でそろえてください」）。
# 作例はこの日のどれかで受ける（回数を数える所と同じ 4 回にそろえる）。ワークショップが増えたら、ここに足す
WORKSHOP_DAYS = ("2026-11-04", "2026-11-05", "2026-11-06", "2026-11-07")
LONG = 2400  # px。HEIC を描き直す時の長い辺の上限。頁は小さい写しで出すので、置き場を埋めない大きさにする
QUALITY = 88
HEIC_BRANDS = (b"heic", b"heix", b"heim", b"heis", b"mif1", b"msf1", b"hevc", b"hevx")
SET_NAME = re.compile(r"[a-z_]+-v\d+")


def is_heic(data):
    """HEIC・HEIF か（中身の印で見る。拡張子に頼らない）。"""
    return data[4:8] == b"ftyp" and data[8:12] in HEIC_BRANDS


def to_jpeg(data):
    """写真（HEIC・JPEG・PNG）を、向きを画素へ移し、色を sRGB にした、撮影の情報の無い JPEG にする。Returns 中身 or None（読めない）。

    HEIC は pillow-heif がある時だけ読める（無ければ None）。描き直すので、EXIF（位置を含む）も色の情報も付かない。色は Display P3 の
    ICC が付いて来るので sRGB へ移す（移せない時は画素のまま）。"""
    from PIL import Image, ImageCms, ImageOps

    try:
        import pillow_heif

        pillow_heif.register_heif_opener()
    except ImportError:
        if is_heic(data):
            return None
    try:
        with Image.open(io.BytesIO(data)) as raw:
            im = ImageOps.exif_transpose(raw)
            icc = im.info.get("icc_profile")
            im = im.convert("RGB")
            if icc:
                try:
                    im = ImageCms.profileToProfile(im, ImageCms.ImageCmsProfile(io.BytesIO(icc)), ImageCms.createProfile("sRGB"), outputMode="RGB")
                except (ImageCms.PyCMSError, OSError, ValueError):
                    pass
            if max(im.size) > LONG:
                im.thumbnail((LONG, LONG))
            buf = io.BytesIO()
            im.save(buf, "JPEG", quality=QUALITY)
            return buf.getvalue()
    except (OSError, ValueError, Image.DecompressionBombError):
        return None


def _kind(data):
    """取り込める写真の型（content type）。HEIC は jpeg の段で JPEG にしてから取り込む。"""
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    return None


def fingerprint(data):
    """元の写真の指紋（同じ写真を 2 度取り込まないため）。写真そのものは持たない。"""
    return hashlib.sha256(data).hexdigest()[:16]


def workshop_records():
    from omochae import records

    return [r for r in records.all_records(workshop=True) if r.get("via") == records.WORKSHOP]


def examples():
    """頁に出してよい作例（人が「物だけ」と確かめた写真がある物）。作った日・玩具の並びの順・記録の番号の順。Returns
    [{"day", "sid", "rid", "photos", "set"}]。順位は付けない（記録の順）。合言葉付きの場と合言葉なしの場で同じ物（ギャラリーと同じく、確かめた物だけ）。"""
    from omochae import media_review

    from . import techo_site

    out = []
    for r in workshop_records():
        shown = media_review.public(r["id"], techo_site.media_of(r["id"]))
        if shown:
            out.append({"day": r["made_on"], "sid": r["source_id"], "rid": r["id"], "photos": shown, "set": r.get("sheet_set")})
    return sorted(out, key=lambda e: (e["day"], e["rid"]))


def days():
    """作例を出している日の月日 4 桁の集まり（例 {"1104", "1106"}）。審査用の頁が、作例の節の日の見出し（/gallery#sakurei-MMDD）へ道を張る時に、
    出す物がある日だけに張るため（行き止まりを作らない）。"""
    return {e["day"][5:7] + e["day"][8:10] for e in examples()}


def add(paths, sid, day, sheet_set=None, hypothesis_id=None):
    """写真を作例として取り込む。Returns ([(記録の番号, 名, 元のファイル)], [(元のファイル, 理由)], 検査できない理由 or None)。
    1 枚に 1 つの記録（できた物 1 つに 1 枚の札）。"""
    from omochae import hypotheses, records
    from omochae.model import ToolMissing

    from . import techo_site

    try:
        data_ = hypotheses.load(sid)
    except (KeyError, OSError, ValueError, ToolMissing):
        return [], [("", f"知らない玩具: {sid}")], None
    try:
        made = date.fromisoformat(day)
    except (TypeError, ValueError):
        return [], [("", f"日は YYYY-MM-DD: {day}")], None
    # 日は 1 回の取り込みごとに先に見る（写真ごとの断りより前に）。ワークショップの 4 回の日のどれか
    if made.isoformat() not in WORKSHOP_DAYS:
        return [], [("", f"作った日がワークショップの日（{'・'.join(d[5:] for d in WORKSHOP_DAYS)}）でない: {day}")], None
    if sheet_set is not None and not SET_NAME.fullmatch(sheet_set):
        return [], [("", f"型紙の組は「名前-v番号」の形: {sheet_set}")], None
    hid = hypothesis_id or hypotheses.sheet_of(sid)["id"]
    if hid not in {h["id"] for h in data_["hypotheses"]}:
        return [], [("", f"知らない仮説: {hid}")], None
    seen = {r.get("workshop_from") for r in workshop_records()}
    done, refused = [], []
    for path in paths:
        p = pathlib.Path(path)
        try:
            raw = p.read_bytes()
        except OSError as e:
            return done, refused, f"読めない: {p.name}: {e}"
        mark = fingerprint(raw)
        if mark in seen:
            refused.append((p.name, "同じ写真をもう取り込んである"))
            continue
        data = raw
        if is_heic(raw):
            data = to_jpeg(raw)
            if data is None:
                return done, refused, f"HEIC を読めない（jpeg の段を、pillow-heif のある python で先に回す）: {p.name}"
        kind = _kind(data)
        if kind is None:
            refused.append((p.name, "写真（JPEG・PNG・HEIC）として読めない"))
            continue
        rec = {"source_id": sid, "hypothesis_id": hid, "result": records.UNSURE, "via": records.WORKSHOP, "made_on": made.isoformat(),
               "workshop_from": mark, **({"sheet_set": sheet_set} if sheet_set else {})}
        rid, failures = records.add(rec)
        if failures:
            refused.append((p.name, "; ".join(f.message for f in failures)))
            continue
        name, why = techo_site.save_media(rid, kind, data)
        if not name:
            # 写真を置けなかった記録は残さない（写真の無い作例の札を作らない）
            records.withdraw(rid)
            refused.append((p.name, why))
            continue
        seen.add(mark)
        done.append((rid, name, p.name))
    return done, refused, None


def main(argv=None):
    ap = argparse.ArgumentParser(prog="web.sakurei", description="ワークショップで作られたおもちゃ（作例）の写真を受ける")
    sub = ap.add_subparsers(dest="cmd", required=True)
    j = sub.add_parser("jpeg", help="HEIC などを、撮影の情報の無い sRGB の JPEG にする（pillow-heif のある python で回す）")
    j.add_argument("photos", nargs="+")
    j.add_argument("--out", required=True)
    a = sub.add_parser("add", help="写真を作例として取り込む（撮影の情報を落とし、人の確かめを待つ）")
    a.add_argument("photos", nargs="+")
    a.add_argument("--toy", required=True, help="玩具の印（NDL-…）")
    a.add_argument("--day", required=True, help="ワークショップの日 YYYY-MM-DD")
    a.add_argument("--set", dest="sheet_set", help="刷った型紙の組（例 goraigo-v10）。分からない時は書かない")
    a.add_argument("--hypothesis", help="刷った型紙の仮説（既定はたたき台）")
    sub.add_parser("list", help="取り込んだ作例と、人の確かめの状態")
    try:
        args = ap.parse_args(argv)
    except SystemExit as e:
        return 0 if e.code == 0 else 4
    if args.cmd == "jpeg":
        out = pathlib.Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        bad = 0
        for path in args.photos:
            p = pathlib.Path(path)
            try:
                data = to_jpeg(p.read_bytes())
            except OSError as e:
                print(f"検査できない: {p.name}: {e}", file=sys.stderr)
                return 4
            if data is None:
                print(f"読めない（HEIC は pillow-heif が要る）: {p.name}", file=sys.stderr)
                bad += 1
                continue
            (out / f"{p.stem}.jpg").write_bytes(data)
            print(out / f"{p.stem}.jpg")
        return 4 if bad else 0
    if args.cmd == "add":
        done, refused, cannot = add(args.photos, args.toy, args.day, args.sheet_set, args.hypothesis)
        for rid, name, src in done:
            print(rid, name, src)
        for src, why in refused:
            print(f"受けない: {src} {why}".strip(), file=sys.stderr)
        if cannot:
            print(f"検査できない: {cannot}", file=sys.stderr)
            return 4
        return 3 if refused else 0
    from omochae import media_review

    from . import techo_site

    for r in workshop_records():
        state = []
        for name in techo_site.media_of(r["id"]):
            state.append(f"{name}:{'物だけ' if media_review.public(r['id'], [name]) else ('確かめ待ち' if media_review.visible(r['id'], [name]) else '人が入る')}")
        print(r["id"], r["made_on"], r["source_id"], r.get("sheet_set") or "-", " ".join(state))
    return 0


if __name__ == "__main__":
    sys.exit(main())
