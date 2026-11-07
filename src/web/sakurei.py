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
- 写真がまとめて 1 つの folder に上がる時（本人の言葉 11-07「全部一緒にしてしまったので日毎にはしない。ここに上げていく」）は、仕分けの段
  （sort → toy → place）を通す。日は撮影の日時から 4 回のどれかに振る（撮影の情報を落とす前に読み、日だけを残す。時刻と位置は残さない）。
  4 回の日でない物と日時の無い物は「不明」。玩具は写っている物を人（か取り込む担当）が見て決め、分からない物は「不明」のまま人の確かめへ
  残す（勝手に決めない）。日と玩具の両方が決まった物だけを作例の記録に入れる。動画（一周の動画など）は写真と分けて名を挙げるだけで、触らない。

使い方（端末で）:
  1. iPhone の写真（HEIC）は、先に JPEG にする。pillow-heif のある python で回す（pillow-heif の中の x265 は GPL なので、repo の依存に
     入れない。この段は Pillow と pillow-heif と標準の部品だけで動く）:
       <pillow-heif のある python> -m web.sakurei jpeg <写真...> --out <置き場の外の一時の所>
  2. 取り込む（repo の python で）:
       python -m web.sakurei add --toy <玩具の印> --day YYYY-MM-DD [--set <刷った型紙の組、例 goraigo-v10>] <写真...>
  3. 人が確かめる: python -m omochae.media_review list / approve <記録> <名> --shows object --reviewer <名>
  4. 一覧: python -m web.sakurei list
  まとめて上がった folder の仕分け（上の 1・2 の代わり）:
  a. 日を読み、撮影の情報の無い JPEG にして仕分けの置き場（OMOCHAE_DATA の sakurei_hold）へ。動画は名を挙げるだけ（pillow-heif のある python で）:
       <pillow-heif のある python> -m web.sakurei sort <folder>
  b. 写っている物を見て玩具を決める（分からない物は不明のまま。日が不明の物は人が --day で決めてよい）:
       python -m web.sakurei toy <指紋か元の名...> --toy <玩具の印か 不明> [--day YYYY-MM-DD] [--set <組>]
  c. 日と玩具の両方が決まった物を作例の記録に入れる: python -m web.sakurei place
  d. 残っている物（不明・人の確かめ待ち）: python -m web.sakurei hold
  別の置き場（審査の場など）へ同じ取り込みを回す時は、a に --like <前の置き場の sakurei_hold/hold.json> を付け、b を飛ばして c を回す。

exit code: 0 = 通る / 3 = 受けない物がある（知らない玩具・読めない日・写真として読めない）/ 4 = 呼び方の誤り・検査できない（HEIC を読む部品が無いなど）。
"""
import argparse
import hashlib
import io
import json
import os
import pathlib
import re
import sys
from datetime import date, datetime, timedelta, timezone

# ワークショップの日（本人の言葉 11-07「ワークショップ 4 回は 11 月 4・5・6・7 日でよい。回数の数え方と改善の歴史の表はこの 4 回でそろえてください」）。
# 作例はこの日のどれかで受ける（回数を数える所と同じ 4 回にそろえる）。ワークショップが増えたら、ここに足す
WORKSHOP_DAYS = ("2026-11-04", "2026-11-05", "2026-11-06", "2026-11-07")
LONG = 2400  # px。HEIC を描き直す時の長い辺の上限。頁は小さい写しで出すので、置き場を埋めない大きさにする
QUALITY = 88
HEIC_BRANDS = (b"heic", b"heix", b"heim", b"heis", b"mif1", b"msf1", b"hevc", b"hevx")
SET_NAME = re.compile(r"[a-z_]+-v\d+")
# 作例の写真の種類（本人の言葉で届いた事例の写真）。種類の付いた写真は玩具の札（examples）に入れず、それぞれの段が読む（cases・versions）。
# 同じ物が頁に 2 回出ないように（本人のサイト体験レビュー 11-07 の 3「同じ物が何回も出る」）
KINDS = {
    "versions": "型紙で改善したおもちゃ 3 バージョン",  # 本人の言葉 11-07。R-1019 御来迎・R-1020 虎
    "loop": "改善ループの例",  # 本人の言葉 11-07「手前から使う型紙の版が変わっている。改善ループの例として使って欲しい」
    "kufu": "参加者の工夫",  # 本人の言葉 11-07「参加者の型紙の改善例その1。…事例としてサイトに載せて」
}
ROOT = pathlib.Path(__file__).resolve().parents[2]
UNKNOWN = "不明"  # 仕分けで日か玩具が決まらない物の印（人の確かめへ残す。統括の頼み 11-07 の字のまま）
JST = timezone(timedelta(hours=9))  # ワークショップの場の時（撮影の日時の日をこの時で読む）
VIDEO_EXT = (".mov", ".mp4", ".m4v")
VIDEO_BRANDS = (b"qt  ", b"isom", b"mp41", b"mp42", b"M4V ", b"iso2", b"avc1")


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
    from omochae import media_review, records

    from . import techo_site

    out = []
    for r in workshop_records():
        if r["source_id"] == records.WORKSHOP_ALL or r.get("kind"):
            continue  # 報告の顔の写真（faces）と事例の写真（cases）は玩具の札にしない
        shown = media_review.public(r["id"], techo_site.media_of(r["id"]))
        if shown:
            out.append({"day": r["made_on"], "sid": r["source_id"], "rid": r["id"], "photos": shown, "set": r.get("sheet_set")})
    return sorted(out, key=lambda e: (e["day"], e["rid"]))


def cases(kind):
    """事例の写真（KINDS の種類）。人が「物だけ」と確かめた物だけ・記録の順。Returns [{"sid", "rid", "url"}]。"""
    from omochae import media_review

    from . import techo_site

    return [{"sid": r["source_id"], "rid": r["id"], "url": f"/record/{r['id']}/media/{name}/small"} for r in workshop_records() if r.get("kind") == kind
            for name in media_review.public(r["id"], techo_site.media_of(r["id"]))]


def versions():
    """型紙で改善したおもちゃ 3 バージョンの写真の、玩具ごとの 1 枚（同じ玩具に 2 枚あれば記録の順であとの方）。Returns {玩具の印: 道}。
    審査用の頁の「型紙で改善したおもちゃ」の段が読む（窓口の決め 11-07 152530）。"""
    return {c["sid"]: c["url"] for c in cases("versions")}


def set_kind(rid, kind):
    """取り込んだ作例の記録に事例の写真の種類を書く。Returns 断りの理由 or None。作例の記録だけ（ほかの記録は書き換えない）。"""
    from omochae import records, store

    if kind not in KINDS:
        return f"種類は {'・'.join(sorted(KINDS))} のどれか"
    path = records.folder() / f"{rid}.json"
    rec = next((r for r in workshop_records() if r["id"] == rid), None)
    if rec is None or not path.exists():
        return "作例の記録に無い"
    store.write_json(path, {**rec, "kind": kind})
    return None


def faces():
    """ワークショップの報告の顔の写真（本人の言葉 11-07「4 日間のワークショップで作ったおもちゃたち」）の小さい写しの道の並び。
    人が「物だけ」と確かめた物だけ・記録の順。作例の節の報告の段の頭と、審査用の頁のワークショップの節の頭が読む（無ければ空で、段に写真を置かない）。"""
    from omochae import media_review, records

    from . import techo_site

    return [f"/record/{r['id']}/media/{name}/small" for r in workshop_records() if r["source_id"] == records.WORKSHOP_ALL
            for name in media_review.public(r["id"], techo_site.media_of(r["id"]))]


def toy_name(sid):
    """作例の札の玩具の名。83 の玩具はその名、83 の外の玩具は棚卸しの名（records.outside_toy）。"""
    from omochae import hypotheses, records

    if sid == records.WORKSHOP_ALL:
        return None  # 報告の顔の写真は 1 つの玩具の物でないので、名を持たない（札にしない）
    return records.outside_toy(sid) or hypotheses.load(sid)["toy"]


def days():
    """作例を出している日の月日 4 桁の集まり（例 {"1104", "1106"}）。審査用の頁が、作例の節の日の見出し（/gallery#sakurei-MMDD）へ道を張る時に、
    出す物がある日だけに張るため（行き止まりを作らない）。"""
    return {e["day"][5:7] + e["day"][8:10] for e in examples()}


def add(paths, sid, day, sheet_set=None, hypothesis_id=None, kind=None):
    """写真を作例として取り込む。Returns ([(記録の番号, 名, 元のファイル)], [(元のファイル, 理由)], 検査できない理由 or None)。
    1 枚に 1 つの記録（できた物 1 つに 1 枚の札）。"""
    from omochae import hypotheses, records
    from omochae.model import ToolMissing

    from . import techo_site

    # 83 の外で棚卸しにだけある玩具（猫と鼠の箱など。作例の節にだけ出す）と、報告の顔の写真（records.WORKSHOP_ALL）は仮説を持たない
    outside = sid == records.WORKSHOP_ALL or records.outside_toy(sid)
    try:
        data_ = None if outside else hypotheses.load(sid)
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
    if kind is not None and kind not in KINDS:
        return [], [("", f"事例の写真の種類は {'・'.join(sorted(KINDS))} のどれか: {kind}")], None
    if outside:
        if hypothesis_id:
            return [], [("", f"83 の外の玩具の作例は仮説を持たない: {hypothesis_id}")], None
        hid = None
    else:
        hid = hypothesis_id or hypotheses.sheet_of(sid)["id"]
        if hid not in {h["id"] for h in data_["hypotheses"]}:
            return [], [("", f"知らない仮説: {hid}")], None
    # 同じ写真を同じ玩具に 2 度入れない（2 つの玩具が写る写真は、玩具ごとに 1 度ずつ入る）
    seen = {(r.get("workshop_from"), r.get("source_id")) for r in workshop_records()}
    done, refused = [], []
    for path in paths:
        p = pathlib.Path(path)
        try:
            raw = p.read_bytes()
        except OSError as e:
            return done, refused, f"読めない: {p.name}: {e}"
        mark = fingerprint(raw)
        if (mark, sid) in seen:
            refused.append((p.name, "同じ写真をもう取り込んである"))
            continue
        data = raw
        if is_heic(raw):
            data = to_jpeg(raw)
            if data is None:
                return done, refused, f"HEIC を読めない（jpeg の段を、pillow-heif のある python で先に回す）: {p.name}"
        ctype = _kind(data)  # 写真の型（content type）。事例の写真の種類の kind と別の物
        if ctype is None:
            refused.append((p.name, "写真（JPEG・PNG・HEIC）として読めない"))
            continue
        rec = {"source_id": sid, "hypothesis_id": hid, "result": records.UNSURE, "via": records.WORKSHOP, "made_on": made.isoformat(),
               "workshop_from": mark, **({"sheet_set": sheet_set} if sheet_set else {}), **({"kind": kind} if kind else {})}
        rid, failures = records.add(rec)
        if failures:
            refused.append((p.name, "; ".join(f.message for f in failures)))
            continue
        name, why = techo_site.save_media(rid, ctype, data)
        if not name:
            # 写真を置けなかった記録は残さない（写真の無い作例の札を作らない）
            records.withdraw(rid)
            refused.append((p.name, why))
            continue
        seen.add((mark, sid))
        done.append((rid, name, p.name))
    return done, refused, None


def is_video(data, name):
    """動画か（中身の印か拡張子で見る）。一周の動画（splat 用）は写真と分け、仕分けの段では触らない。"""
    return (data[4:8] == b"ftyp" and data[8:12] in VIDEO_BRANDS) or name.lower().endswith(VIDEO_EXT)


def shot_day(data):
    """撮影の日（Asia/Tokyo の YYYY-MM-DD）。EXIF の DateTimeOriginal（と OffsetTimeOriginal）から読む。読めなければ None。

    DateTime（0x0132）は直した時の日時になる事があるので使わない（撮った日と違う日に振らない）。時差の欄が無い時は、書いてある時のまま読む
    （カメラの時計はその場の時）。HEIC は pillow-heif がある時だけ読める（無ければ None）。"""
    from PIL import Image

    try:
        import pillow_heif

        pillow_heif.register_heif_opener()
    except ImportError:
        if is_heic(data):
            return None
    try:
        with Image.open(io.BytesIO(data)) as im:
            sub = im.getexif().get_ifd(0x8769)
            raw, off = sub.get(0x9003), sub.get(0x9011) or sub.get(0x9010)
        t = datetime.strptime(str(raw).strip("\x00 "), "%Y:%m:%d %H:%M:%S")
        m = re.fullmatch(r"([+-])(\d\d):(\d\d)", str(off or "").strip("\x00 "))
        if m:
            sign = 1 if m.group(1) == "+" else -1
            t = t.replace(tzinfo=timezone(sign * timedelta(hours=int(m.group(2)), minutes=int(m.group(3))))).astimezone(JST)
        return t.date().isoformat()
    except (OSError, ValueError, TypeError, Image.DecompressionBombError):
        return None


def workshop_day(data):
    """撮影の日が 4 回のワークショップの日なら、その日。ほかの日と、日時の無い物は不明（人が決める）。"""
    d = shot_day(data)
    return d if d in WORKSHOP_DAYS else UNKNOWN


def hold_dir():
    """仕分けの置き場（写真の元は repo に入れない: サーバの記録の置き場 OMOCHAE_DATA の下。置かない時は git の外の data/ の下）。"""
    return pathlib.Path(os.environ.get("OMOCHAE_DATA", ROOT / "data")) / "sakurei_hold"


def _hold_list():
    try:
        return json.loads((hold_dir() / "hold.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def _hold_save(items):
    d = hold_dir()
    d.mkdir(parents=True, exist_ok=True)
    tmp = d / "hold.json.tmp"
    tmp.write_text(json.dumps(items, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    tmp.replace(d / "hold.json")


def sort(folder, like=None):
    """まとめて上がった folder の直下を仕分けの置き場へ。Returns ([仕分けた元の名], [動画の名], [(写真でない名, 理由)], 検査できない理由 or None)。

    1 枚ごとに: 撮影の日を読む → 撮影の情報の無い JPEG に描き直して置く（日時・位置・機種は残さない）→ 帳面（hold.json）に
    指紋・元の名・日（4 回の日か不明）・玩具（不明）を書く。同じ元の写真は 2 度置かない（指紋で見る）。元の folder には書かない。
    like は別の置き場の帳面（hold.json）。同じ指紋の写真には、そこで人が決めた玩具・日・組を写す（審査の場を立てる時に、公開のデモと
    同じ取り込みを、決め直さずにもう一度回すため）。"""
    folder = pathlib.Path(folder)
    if not folder.is_dir():
        return [], [], [], f"folder が無い: {folder}"
    try:
        known = {it["fp"]: it for it in json.loads(pathlib.Path(like).read_text(encoding="utf-8"))} if like else {}
    except (OSError, ValueError, KeyError, TypeError) as e:
        return [], [], [], f"写す帳面を読めない: {like}: {e}"
    items = _hold_list()
    seen = {it["fp"] for it in items}
    held, videos, skipped = [], [], []
    for p in sorted(x for x in folder.iterdir() if x.is_file() and not x.name.startswith(".")):
        try:
            raw = p.read_bytes()
        except OSError as e:
            return held, videos, skipped, f"読めない: {p.name}: {e}"
        if is_video(raw, p.name):
            videos.append(p.name)
            continue
        fp = fingerprint(raw)
        if fp in seen:
            continue
        jpeg = to_jpeg(raw)
        if jpeg is None:
            if is_heic(raw):
                _hold_save(items)
                return held, videos, skipped, f"HEIC を読めない（sort は pillow-heif のある python で回す）: {p.name}"
            skipped.append((p.name, "写真（JPEG・PNG・HEIC）として読めない"))
            continue
        d = hold_dir()
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{fp}.jpg").write_bytes(jpeg)
        item = {"fp": fp, "name": p.name, "day": workshop_day(raw), "toy": UNKNOWN}
        item.update({k: known[fp][k] for k in ("day", "toy", "set", "kind") if k in known.get(fp, {})})
        items.append(item)
        seen.add(fp)
        held.append(p.name)
    _hold_save(items)
    return held, videos, skipped, None


def set_toy(keys, sid, day=None, sheet_set=None, kind=None):
    """仕分けの置き場の写真の玩具（と、人が決めた日・刷った組）を書く。keys は指紋か元の名。sid は玩具の印か不明。
    2 つ以上の玩具が写る写真は、印を「,」でつないで渡すと、それぞれの玩具の作例になる（本人の言葉 11-07「両方の玩具の作例に載せる」）。
    Returns ([書いた指紋], [(key, 理由)])。"""
    sids = [s.strip() for s in sid.split(",") if s.strip()] if sid != UNKNOWN else [UNKNOWN]
    if not sids or (len(sids) > 1 and UNKNOWN in sids) or len(set(sids)) != len(sids):
        return [], [("", f"玩具の印の並びが読めない: {sid}")]
    if sids != [UNKNOWN]:
        from omochae import hypotheses, records
        from omochae.model import ToolMissing

        for one in sids:
            try:
                one == records.WORKSHOP_ALL or records.outside_toy(one) or hypotheses.load(one)
            except (KeyError, OSError, ValueError, ToolMissing):
                return [], [("", f"知らない玩具: {one}")]
    if day is not None and day not in WORKSHOP_DAYS + (UNKNOWN,):
        return [], [("", f"日はワークショップの日（{'・'.join(d[5:] for d in WORKSHOP_DAYS)}）か不明: {day}")]
    if sheet_set is not None and not SET_NAME.fullmatch(sheet_set):
        return [], [("", f"型紙の組は「名前-v番号」の形: {sheet_set}")]
    if kind is not None and kind not in KINDS:
        return [], [("", f"事例の写真の種類は {'・'.join(sorted(KINDS))} のどれか: {kind}")]
    items = _hold_list()
    done, refused = [], []
    for key in keys:
        hit = [it for it in items if key in (it["fp"], it["name"]) and not it.get("rid")]
        if len(hit) != 1:
            refused.append((key, "元の名が 2 つ以上に当たる（指紋で選ぶ）" if hit else "仕分けの置き場に無い（取り込み済みか、名か指紋の誤り）"))
            continue
        it = hit[0]
        it["toy"] = ",".join(sids)  # 帳面は 1 つの字で持つ（--like で写す時も同じ形）
        if day is not None:
            it["day"] = day
        if sheet_set is not None:
            it["set"] = sheet_set
        if kind is not None:
            it["kind"] = kind
        done.append(it["fp"])
    _hold_save(items)
    return done, refused


def place():
    """日と玩具の両方が決まった物を作例の記録に入れる（add と同じ道: 人の確かめを待つ）。Returns ([(記録, 元の名)], [(元の名, 理由)])。
    入れた物は仕分けの置き場の写しを消し、帳面に記録の番号を書く（2 度入れない）。"""
    items = _hold_list()
    done, refused = [], []
    for it in items:
        if it.get("rid") or UNKNOWN in (it["day"], it["toy"]):
            continue
        path = hold_dir() / f"{it['fp']}.jpg"
        rids, whys = list(it.get("rids", [])), []
        # 2 つの玩具が写る写真は玩具ごとに 1 つの記録（同じ写真を両方の札に）。途中で断られても、入った分は帳面に残す（2 度入れない）
        for sid in it["toy"].split(","):
            got, why, cannot = add([path], sid, it["day"], it.get("set"), kind=it.get("kind"))
            if got:
                rids.append(got[0][0])
                done.append((got[0][0], it["name"]))
            else:
                whys.append(cannot or "; ".join(w for _, w in why))
        if rids:
            it["rids"] = rids
        if whys:
            refused.append((it["name"], "; ".join(whys)))
        else:
            it["rid"] = rids[0]
            path.unlink(missing_ok=True)
    _hold_save(items)
    return done, refused


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
    so = sub.add_parser("sort", help="まとめて上がった folder の写真を、日を読んで撮影の情報を落とし、仕分けの置き場へ（動画は名を挙げるだけ）")
    so.add_argument("folder")
    so.add_argument("--like", help="別の置き場の帳面（hold.json）。同じ写真に、そこで決めた玩具・日・組を写す")
    ty = sub.add_parser("toy", help="仕分けの置き場の写真の玩具を書く（分からない物は 不明）")
    ty.add_argument("keys", nargs="+", help="指紋か元の名")
    ty.add_argument("--toy", required=True, help=f"玩具の印（NDL-…）か {UNKNOWN}。報告の顔の写真（玩具が 1 つに決まらない写真）は workshop-all")
    ty.add_argument("--day", help=f"人が決めた日 YYYY-MM-DD か {UNKNOWN}（撮影の日時から決まらない物）")
    ty.add_argument("--set", dest="sheet_set", help="刷った型紙の組（分かる時だけ）")
    ty.add_argument("--kind", choices=sorted(KINDS), help="本人の言葉で届いた事例の写真の種類（versions・loop・kufu）")
    ki = sub.add_parser("kind", help="取り込んだ作例の記録に、事例の写真の種類を書く（仕分けの置き場で付け忘れた時）")
    ki.add_argument("rid")
    ki.add_argument("kind", choices=sorted(KINDS))
    sub.add_parser("place", help="日と玩具の両方が決まった物を作例の記録に入れる")
    sub.add_parser("hold", help="仕分けの置き場に残っている物（不明・人の確かめ待ち）")
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
    if args.cmd == "sort":
        held, videos, skipped, cannot = sort(args.folder, args.like)
        items = {it["name"]: it for it in _hold_list()}
        for name in held:
            print("仕分けた", items[name]["fp"], items[name]["day"], name)
        for name in videos:
            print("動画（触らない）", name)
        for name, why in skipped:
            print(f"受けない: {name} {why}", file=sys.stderr)
        if cannot:
            print(f"検査できない: {cannot}", file=sys.stderr)
            return 4
        return 3 if skipped else 0
    if args.cmd == "toy":
        done, refused = set_toy(args.keys, args.toy, args.day, args.sheet_set, args.kind)
        for fp in done:
            print("書いた", fp, args.toy)
        for key, why in refused:
            print(f"受けない: {key} {why}".strip(), file=sys.stderr)
        return 3 if refused else 0
    if args.cmd == "kind":
        why = set_kind(args.rid, args.kind)
        if why:
            print(f"受けない: {args.rid} {why}", file=sys.stderr)
            return 3
        print("書いた", args.rid, args.kind)
        return 0
    if args.cmd == "place":
        done, refused = place()
        for rid, name in done:
            print(rid, name)
        for name, why in refused:
            print(f"受けない: {name} {why}", file=sys.stderr)
        return 3 if refused else 0
    if args.cmd == "hold":
        for it in _hold_list():
            if not it.get("rid"):
                print(it["fp"], it["day"], it["toy"], it.get("set") or "-", it["name"])
        return 0
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
