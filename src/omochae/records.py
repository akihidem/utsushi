"""試した記録の入口。成績でなく観察の記録で、人が入れた物だけを残す（philosophy.md）。

判断の芯: 何が起きたかは人が決める値で、写真から判定しない。「動かない」は失敗でなく自然の返事。「わからない」を「動いた」に数えない。値は雛形が持つ（虎は揺れた／揺れない／わからない）。
札を直しても、前の札で残った記録の中身は書き換えない（読み手が読めるように、雛形の OLD_RESULTS が今の札との対応を持つ。#146）。
直した点は 3 欄が揃った物だけを残す。次の版や次に試す物の提案の根拠になるので、あいまいな記録を混ぜないため。
"""
import argparse
import hmac
import json
import os
import pathlib
import re
import shutil
import sys
import unicodedata
from datetime import date, datetime, timedelta, timezone

from . import store
from .contrib import check_pii, too_long
from .hypotheses import load, own_hypotheses
from .model import Failure

ROOT = pathlib.Path(__file__).resolve().parents[2]
OPENERS = ("紙の力", "糸", "手")
OWN = ("explanation", "interpretation", "observation", "video", "owner")  # 記録ごとに輪の置き場へ書く物
# 記録を残した画面が、その記録に説明と字を足せる長さ（分）。サーバの時刻で数える。過ぎたら作る側の端末から足す（loop explain）。
OWNER_MINUTES = 15
# 動画の受け口（web/video_up.py）から来た記録の印。上げた人に「頁に出さない」と約束した物で、紙も人が確かめていないので、all_records は既定で外す。
UPLOADED = "video-up"
# ワークショップの作例の受け口（web.sakurei）の記録。本人の言葉（11-07）「サイトにワークショップで作られたおもちゃを掲載したい。写真データはこれから上げる」。
# 写真から作った記録で、学ぶ人の観察と説明が無い。動画の受け口と同じく all_records の既定から外す（エンジンへ渡す束・輪の数・審査用の頁・
# ギャラリーの「他の人が作った物」に、観察の無い作例を混ぜない。作例はギャラリーの作例の節だけが読む）
WORKSHOP = "workshop"
# 作例の記録の番号は R-1001 から数える（学ぶ人の記録は R-0001 から）。repo に載せた 11-04 の試行の記録 R-0001・R-0002 を審査用の頁が
# 「記録 R-0001」として見せるので、公開デモの置き場の作例が同じ番号の札にならないように、番号の帯を分ける（統括の確かめ 11-07）。
# 頭の字を替える（W- など）形にしないのは、写真の道（/record/R-…/media）と試験が R- の形で決め打ちしているため
WORKSHOP_FROM = 1000  # ふつうの記録はここまで（R-1000 まで）。越える時は add が断る（作例の帯と重ねない）
# ワークショップの報告の顔の写真（本人の言葉 11-07「4 日間のワークショップで作ったおもちゃたち」）の印。玩具が 1 つに決まらない写真なので、
# 玩具の印の代わりにこの印を持つ作例の記録にする（写真の道と人の確かめは作例と同じ）。作例の札には出さず、報告の段の頭にだけ出す（web.sakurei.faces）
WORKSHOP_ALL = "workshop-all"
UNSURE = "わからない"
FIX_BLANK = "書かれていない"  # 工夫の 3 欄のうち、欠けた欄に入れる字（web.play_server.fixes_of）
# 取り下げの説明文（本人の決定、Issue #335）。本人が確かめた字を、一字も変えずに出す（tests/test_withdraw_notice.py が文字列で見る）。
# 消せるのはこのサイトの中だけで、書き出した束やエンジンに渡した字には届かないので、そう言う。文を変える時は、ここだけを変える。
# 持ち寄りの所には置かない。持ち寄りは書き出す束に入らないので、文の後半が事実と合わない。
WITHDRAW_NOTICE = "取り下げると、このサイトの中からは消えます。前にエンジンへ渡した分は残ります"


def folder():
    return pathlib.Path(os.environ.get("OMOCHAE_DATA", ROOT / "data")) / "records"


def withdrawn_folder():
    return folder() / "withdrawn"


def results_for(source_id):
    from .compose import TEMPLATES

    return TEMPLATES[load(source_id).get("template", "slider_fan")].RESULTS


def result_word(rec):
    """記録の札の字。手で置かれた記録の札は字とは限らず、欄が無い事もある（#146）。字でない札は数えず、頁にも出さない。"""
    word = rec.get("result")
    return word if isinstance(word, str) else ""


def old_results_for(source_id):
    """前の札の言葉 → 今の札の言葉。新しく選ばせる札でなく、前の札で残った記録を読むための受け口（#146）。"""
    from .compose import TEMPLATES

    return getattr(TEMPLATES[load(source_id).get("template", "slider_fan")], "OLD_RESULTS", {})


def outside_toy(source_id):
    """サイトの玩具の一覧（data/hypotheses の 83）に無く、棚卸し（data/inventory/edo-nishiki.json）にだけある玩具の名。無ければ None。
    作例だけが使う（窓口の決め 11-07 144403: 猫と鼠の箱は作った物の頁の作例の節にだけ出し、玩具の頁は作らない・83 に足さない）。
    仮説も雛形も無いので、作例の記録は仮説を持たず、動きの札は「わからない」だけ。"""
    if not isinstance(source_id, str) or (ROOT / "data/hypotheses" / f"{source_id}.json").exists():
        return None
    try:
        toys = json.loads((ROOT / "data/inventory/edo-nishiki.json").read_text(encoding="utf-8"))["toys"]
    except (OSError, ValueError, KeyError):
        return None
    return next((t.get("name_guess") for t in toys if t.get("id") == source_id), None)


def known_hypothesis(source_id, hypothesis_id):
    return any(h["id"] == hypothesis_id for h in load(source_id)["hypotheses"]) or any(h["id"] == hypothesis_id for h in own_hypotheses(source_id))


def check(rec):
    out = []
    if rec.get("via") == WORKSHOP and (rec.get("source_id") == WORKSHOP_ALL or outside_toy(rec.get("source_id"))):
        # 83 の外の玩具の作例（outside_toy）と、報告の顔の写真（WORKSHOP_ALL）。雛形の札も仮説も無いので、札は「わからない」だけ、仮説は持たない
        if rec.get("result") != UNSURE:
            out.append(Failure("F3.result", "result", f"83 の外の玩具の作例の結果は {UNSURE}"))
        if rec.get("hypothesis_id") is not None:
            out.append(Failure("F8.references", "hypothesis_id", "83 の外の玩具の作例は仮説を持たない"))
    else:
        results = results_for(rec["source_id"])
        # 前の札も受ける。札を直す前に開いた頁から送られても、記録を断らないため。断りの文には今の札だけを出す。
        # 受け口は動いたかを聞かない（動画だけが届く）。雛形の札に「わからない」が無くても、決めつけずにこの字で受ける。束はこの字を数えない
        # 作例の受け口も「わからない」で受ける（写真から動いたかは分からない）
        if rec.get("result") not in (*results, *old_results_for(rec["source_id"])) and not (rec.get("via") in (UPLOADED, WORKSHOP) and rec.get("result") == UNSURE):
            out.append(Failure("F3.result", "result", f"結果は {'／'.join(results)} のどれか"))
        if not known_hypothesis(rec["source_id"], rec.get("hypothesis_id")):
            out.append(Failure("F8.references", "hypothesis_id", f"仮説 {rec.get('hypothesis_id')} は実在しない"))
    if rec.get("via") == WORKSHOP:
        # 作例の札は作った日（ワークショップの日）で並べるので、日が無い・読めない作例は受けない
        try:
            made = date.fromisoformat(rec.get("made_on") or "")
        except (TypeError, ValueError):
            made = None
        if made is None or not date(2026, 1, 1) <= made <= date.today() + timedelta(days=1):
            out.append(Failure("F3.result", "made_on", "作った日は YYYY-MM-DD（ワークショップの日）"))
    deg = rec.get("opened_deg")
    if deg is not None and not (isinstance(deg, (int, float)) and not isinstance(deg, bool) and 0 <= deg <= 360):
        out.append(Failure("F3.result", "opened_deg", "開いた角度は 0〜360"))
    if rec.get("opener") is not None and rec["opener"] not in OPENERS:
        out.append(Failure("F3.result", "opener", f"開いた力は {'／'.join(OPENERS)} のどれか"))
    sec = rec.get("ten_swings_sec")
    if sec is not None and not (isinstance(sec, (int, float)) and not isinstance(sec, bool) and 0 < sec <= 600):
        out.append(Failure("F3.result", "ten_swings_sec", "10 往復の秒は 0〜600"))
    if rec.get("power") is not None and rec["power"] not in ("手", "息", "団扇", "風"):
        out.append(Failure("F3.result", "power", "動かした物は 手／息／団扇／風 のどれか"))
    minutes = rec.get("minutes_to_try")
    if minutes is not None and not (isinstance(minutes, (int, float)) and not isinstance(minutes, bool) and 0 < minutes <= 600):
        out.append(Failure("F3.result", "minutes_to_try", "最初に動かすまでの分は 0〜600"))
    for i, fix in enumerate(rec.get("fixes", []), 1):
        if not all(str(fix.get(k, "")).strip() for k in ("part", "change", "outcome")):
            out.append(Failure("F3.result", f"fixes[{i}]", "直した点は部品名・変えた事・結果の 3 欄が要る"))
    # 感想（impression）も文の欄（本人の方針 11-05「感想と動きの報告」）。長さの床と連絡先の床を同じに当てる。
    fields = [("note", rec.get("note", "")), ("impression", rec.get("impression", "")), *(("answers", v) for v in rec.get("answers", {}).values()),
              *(("ideas", v) for v in rec.get("ideas", [])), *(("fixes", str(v)) for fix in rec.get("fixes", []) for v in fix.values())]
    long = too_long(fields)
    if long:
        return out + [Failure("F3.result", where, message) for where, message in long]
    # 記録は公開の repo に入り得るので、連絡先の形を残さない。
    for f in check_pii({"body": " ".join(text for _, text in fields)}):
        out.append(Failure("F3.result", "note", f.message))
    return out


def add(rec):
    failures = check(rec)
    if failures:
        return None, failures
    d = folder()
    d.mkdir(parents=True, exist_ok=True)
    # 取り下げた番号も数える。使い回すと、残った根拠や控えが別の記録を指してしまう
    nums = [int(m.group(1)) for p in (*d.glob("R-*.json"), *withdrawn_folder().glob("R-*.json")) if (m := re.fullmatch(r"R-(\d{4,})\.json", p.name))]
    # 作例は作例の帯（WORKSHOP_FROM より上）、ほかは下の帯の中で数える。片方の番号が、もう片方の続きの番号を押し上げないように
    base = WORKSHOP_FROM if rec.get("via") == WORKSHOP else 0
    nums = [n for n in nums if (n > WORKSHOP_FROM) == bool(base)]
    if not base and max(nums, default=0) >= WORKSHOP_FROM:
        # ふつうの記録が作例の帯に届いた。続けると作例の番号と重なるので受けない（帯の幅を広げる時は WORKSHOP_FROM を上げる）
        return None, [Failure("F3.result", "id", f"記録の番号が R-{WORKSHOP_FROM:04d} に届いた（作例の番号の帯と重なる）")]
    while True:
        rid = f"R-{max(nums, default=base) + 1:04d}"
        out = {**rec, "id": rid, "by": "human", "recorded_at": datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")}
        try:
            store.write_json(d / f"{rid}.json", out, exclusive=True)
            return rid, []
        except FileExistsError:
            nums.append(int(rid[2:]))


def all_records(source_id=None, uploads=False, workshop=False):
    """記録の一覧。uploads は動画の受け口の記録も含める形で、版の輪の表（trial_video.effect）だけが使う。workshop は作例の受け口の記録も含める形で、
    作例の節（web.sakurei）だけが使う。
    なぜここで外すか: 読む所は学ぶ人の頁・ギャラリー・束など多く、1 つずつ外すと、新しく読む所が足された時に約束が崩れる。
    この関数を通らない所（loop.confirmed_records とサイトの /record の口）は、それぞれで外す。"""
    out = []
    for p in sorted(folder().glob("R-*.json")):
        if (withdrawn_folder() / p.name).exists():
            continue
        rec = store.read_json_or_skip(p)
        if rec is not None and (source_id is None or rec.get("source_id") == source_id) and (uploads or rec.get("via") != UPLOADED) \
                and (workshop or rec.get("via") != WORKSHOP):
            out.append(rec)
    return out


def claim(rid, key):
    """記録を残した画面の鍵を控える。別の人が前の人の記録に説明や字を足せないように、受け口で照らす（下の mine）。写真の鍵（media_review.claim）と同じ作り。
    who を使わないのは、記録が残ると作り直され（1 回の作りに 1 つの印）、記録にも残さないから。番号は連番なので証拠にならない。
    控えは記録の外（輪の置き場）に置く。記録の欄に入れると、記録を読む所（束・ギャラリー）の全部に気を付ける事になる。"""
    from . import loop

    store.write_json(loop.folder() / f"owner-{rid}.json", {"record_id": rid, "key": key, "at": datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")})


def mine(rid, key):
    """その鍵の画面が残した記録で、期限の中か。控えの無い記録（作る側の端末で残した物、前からある記録）と、読めない控えと、
    とじた画面の控え（close_key の closed）は、閉じる側に倒す。"""
    from . import loop

    entry = store.read_json_or_skip(loop.folder() / f"owner-{rid}.json") if key and re.fullmatch(r"R-[0-9]{4,}", str(rid)) else None
    if not isinstance(entry, dict) or not isinstance(entry.get("key"), str) or not hmac.compare_digest(entry["key"].encode(), key.encode("utf-8", "replace")):
        return False
    if entry.get("closed"):
        return False
    try:
        at = datetime.fromisoformat(entry["at"])
        return datetime.now(at.tzinfo) - at <= timedelta(minutes=OWNER_MINUTES)
    except (KeyError, TypeError, ValueError):
        return False


def close_key(key):
    """とじた画面の鍵を、台帳の側で失効させる（本人の指示 11-08 の安全の事項 6「「とじる」が所有者トークンを失効させない」）。
    とじる で cookie を消すだけだと、写した鍵が期限（OWNER_MINUTES）まで生きる。その鍵で控えた記録の全部に closed を書き、mine が通さないようにする
    （しおりの /s/close の shiori.close と同じ形）。鍵が空か、どこにも無い時は何もしない（鍵の有り無しを外へ見せない）。書いた数を返す。"""
    from . import loop

    if not key:
        return 0
    n = 0
    for path in sorted(loop.folder().glob("owner-R-*.json")):
        entry = store.read_json_or_skip(path)
        if isinstance(entry, dict) and isinstance(entry.get("key"), str) and not entry.get("closed") \
                and hmac.compare_digest(entry["key"].encode(), key.encode("utf-8", "replace")):
            store.write_json(path, {**entry, "closed": datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")})
            n += 1
    return n


def _used_paths(rid):
    """この記録を根拠にしている物のファイル。欄ごとに見ず番号の字で探す。根拠の欄が増えても見落とさないため。"""
    mine = {f"{kind}-{rid}.json" for kind in OWN}
    word = re.compile(rf"(?<![\w-]){rid}(?![\w-])")
    base = folder().parent
    return [p for d in ("loop", "decisions") for p in (base / d).glob("*.json")
            if p.name not in mine and word.search(p.read_text(encoding="utf-8", errors="replace"))]


def used_by(rid):
    """この記録を根拠にしている物のファイル名。"""
    return sorted(p.name for p in _used_paths(rid))


def _spoken_of(rid, talks):
    """この記録に関わる、話した考えから作った案の words の記録（ファイル、中身）。考えがこの記録に結ばれている案と、この記録が試した紙の案。
    考えは別の仮説を見て話すと紙の記録に結ばれないので、両方を見る。"""
    from . import loop

    path = folder() / f"{rid}.json"
    rec = store.read_json_or_skip(path) if path.exists() else None
    for p in sorted(loop.folder().glob("words-*.json")):
        w = store.read_json_or_skip(p)
        if not w or not w.get("from_talk"):
            continue
        tried = rec is not None and w.get("own_id") and rec.get("hypothesis_id") == w["own_id"] and rec.get("source_id") == w.get("source_id")
        if tried or talks.get(w["from_talk"], {}).get("record_id") == rid:
            yield p, w


def _talk_files():
    from . import making_log

    return {p.stem: t for p in making_log.folder().glob("talk-*.json") if (t := store.read_json_or_skip(p))} if making_log.folder().exists() else {}


def _drop_loose_talk(sid, oid, talks):
    """その紙に付いた工夫で、まだ結ばれていない字を消す。この記録に結ばれた字は drop_for_record が消す。"""
    from . import making_log

    gone = []
    for stem, t in talks.items():
        if t.get("hypothesis_id") == oid and t.get("source_id") == sid and not t.get("record_id"):
            (making_log.folder() / f"{stem}.json").unlink(missing_ok=True)
            gone.append(f"making/{stem}.json")
    return gone


# 話した字の引用と読む長さ。これより長い字は、この長さの一部が写っていれば引用と読む（文は長い字の一部を引く）。これ以下の字は、4 字以上なら語尾 1 字を落とした全部を探す
# （活用の違いを拾う。紙が破れた → 紙が破れている）。4 字未満はそのまま全部で、1 字は読まない（どの文にも当たる）。tests/test_loop1_quotes.py が手で作った例で振る舞いを固定する。
# 要約はどの比べ方でも拾えないので、Claude が書いた文は引用の有無によらず消す（_claude_keys）。人が言い換えた文は消せない。
QUOTE_CHARS = 6
DROP_TAIL_FROM = 4
# 書いた字（ひとこと・答え・工夫・手書きの説明）は、この長さを超える物だけを比べる（統括の決め）。短い答えは部品や寸法の名前になりやすく（「外筒」「折りの幅」）、
# 話した字と同じ決まりで比べると、引用でない別の人の文を消す。短い思いつきを写した文が残る方を取る（別の人の文を消す誤りの方が重い）。短い答えも記録からは空にする。
WRITTEN_CHARS = 7
# 文でない欄。番号と名前と寸法の字なので、話した字と重なっても消さない。時刻（*_at と at）も（話した字「11」が時刻に当たる）。
# 名前（*_by と by。話した字「作る人」が当たる。drafted_by を消すと Claude の文を見分けられなくなる）、呼び出しの記録（trace）、字の値の寸法（to・from）、採った物の番号と札も同じ。
NOT_TEXT = frozenset(("id", "source_id", "hypothesis_id", "record_id", "record_ids", "references", "param", "params", "from_words", "proposal", "status", "kind", "at",
                      "metric", "direction", "formula_check", "template", "template_id", "by", "trace", "to", "from", "accepted", "accepted_params", "based_on_version",
                      "version", "sheet_set", "commit", "decided_in", "certainty", "confidence", "label"))
RECORD_NO = re.compile(r"R-[0-9]{4,}")  # 記録の番号だけの字は文でない（根拠の where の欄。話した字「00」が番号に当たる）


def _not_text(key):
    return key in NOT_TEXT or key.endswith(("_at", "_by"))


def _compared(talk, written):
    """引用を探す字（_flat した物）。話した字は全部、書いた字は WRITTEN_CHARS を超える物だけ。欄が勧める決まった字は、その人の言葉ではないので外す
    （「わからない」は説明の欄が勧める字、「書かれていない」は工夫の欠けた欄に入る字。引用と読むと、人の文を消し過ぎる）。"""
    out = {_flat(x) for x in talk if x} | {f for x in written if len(f := _flat(x)) > WRITTEN_CHARS}
    return sorted(out - {UNSURE, FIX_BLANK})


def _flat(text):
    """引用を比べる形。声から字にした文は、字の幅と空白が揺れるので、そろえる。"""
    return "".join(unicodedata.normalize("NFKC", str(text)).split())


def _quotes(text, spoken):
    """text に、話した字（_flat した物の一覧）の引用があるか。"""
    flat = _flat(text)
    for s in spoken:
        if len(s) > QUOTE_CHARS:
            if any(s[i:i + QUOTE_CHARS] in flat for i in range(len(s) - QUOTE_CHARS + 1)):
                return True
        else:
            key = s[:-1] if len(s) >= DROP_TAIL_FROM else s
            if len(key) > 1 and key in flat:
                return True
    return False


def _clean(value, drop):
    """drop(文) が真の文を消す。一覧の中の文と、文を text に持つ札は、札ごと外す。ほかの欄の文は空にする（欄の形と、並ぶ寸法・番号は残す）。文でない欄には触らない。"""
    if isinstance(value, str):
        return "" if drop(value) and not RECORD_NO.fullmatch(value) else value
    if isinstance(value, dict):
        return {k: v if _not_text(k) else _clean(v, drop) for k, v in value.items()}
    if isinstance(value, list):
        out = []
        for x in value:
            y = _clean(x, drop)
            if (isinstance(x, str) and x and not y) or (isinstance(x, dict) and x.get("text") and not y.get("text")):
                continue
            out.append(y)
        return out
    return value


def _without_quotes(value, spoken):
    """引用を含む文を文ごと消す。"""
    return _clean(value, lambda text: _quotes(text, spoken))


def _blank(value):
    """Claude が書いた文を全部消す。根拠の記録の番号と、人の名前の欄は残す（_clean）。"""
    return _clean(value, lambda text: True)


def _by_claude(pid):
    """その案を Claude が書いたか。"""
    from . import loop

    p = store.read_json_or_skip(loop.folder() / f"proposal-{str(pid)[2:]}.json") if pid else None
    return bool(p and p.get("drafted_by") == "claude")


def _claude_keys(path, doc):
    """その文書で Claude が書いた文の欄。人が書き直した解釈は人の字（edited_by_human）。版は、元の案を Claude が書いた時（採った人は寸法を採っただけで、理由の文は Claude の字）。"""
    name = path.name
    if name.startswith("interpretation-"):
        return ("content",) if doc.get("drafted_by") == "claude" and not doc.get("edited_by_human") else ()
    if name.startswith("proposal-"):
        return ("changes", "next_to_try", "new_hypothesis") if doc.get("drafted_by") == "claude" else ()
    if name.startswith("version-"):
        return ("changes", "new_case") if _by_claude(doc.get("proposal")) else ()
    return ()


def _scrubbed(path, doc, rid, spoken):
    """1 つの文書から話した字を消した形。Claude が書いた文は引用の有無によらず全部（要約で残るため）、人の字は引用を含む文だけ。"""
    if isinstance(doc, list):  # 採った案の控え。札ごとに書いた人と根拠が違うので、この記録の番号を含む札だけを見る（関わりの無い札の字を消さない）
        word = re.compile(rf"(?<![\w-]){rid}(?![\w-])")
        return [_without_quotes(_blank(e) if _by_claude(e.get("proposal")) else e, spoken) if isinstance(e, dict) and word.search(json.dumps(e, ensure_ascii=False)) else e for e in doc]
    doc = {**doc, **{k: _blank(doc[k]) for k in _claude_keys(path, doc) if k in doc}}
    return _without_quotes(doc, spoken)


def _scrub_quotes(rid, spoken):
    """この記録を根拠にした解釈・案・版・控えから、話した字と書いた字を消す。引用や要約が残ると取り下げにならないため。番号・寸法・版・案の数・時刻は残す。消した物の名前を返す。"""
    from . import loop

    gone = []
    for p in [*_used_paths(rid), loop.interp_path(rid)]:
        before = store.read_json_or_skip(p, (dict, list))
        if before is None:
            continue
        after = _scrubbed(p, before, rid, spoken)
        if after != before:
            store.write_json(p, after)
            gone.append(f"{p.name} の文")
    return gone


def _written(rec, told):
    """記録に人が書いた字（ひとこと・感想・答え・思いつき・工夫）と、手書きの説明の字。手で置いた記録の形が違っても読めるように、決まった型の時だけ読む。"""
    rec, told = rec or {}, told or {}
    answers = rec.get("answers") if isinstance(rec.get("answers"), dict) else {}
    ideas = rec.get("ideas") if isinstance(rec.get("ideas"), list) else []
    fixes = rec.get("fixes") if isinstance(rec.get("fixes"), list) else []
    texts = [rec.get("note"), rec.get("impression"), *answers.values(), *ideas, *(v for f in fixes if isinstance(f, dict) for v in f.values()), told.get("text"), told.get("next_idea")]
    return [x for x in texts if isinstance(x, str) and x.strip()]


def _blank_written(rid, rec, told):
    """記録に人が書いた字と、手書きの説明の字を空にする。消した物の名前を返す。番号・結果・寸法は残す。
    説明はファイルごと残し、字と本人が打った名前だけを空にする: 「人の説明が先」の床は説明があった事だけを見るので、消しても次の案と版の道を止めない。"""
    from . import loop

    gone = []
    if rec:
        left = {**rec, **{k: v for k, v in (("note", ""), ("impression", ""), ("answers", {}), ("ideas", []), ("fixes", [])) if k in rec}}
        if left != rec:
            store.write_json(folder() / f"{rid}.json", left)
            gone.append(f"{rid}.json の文")
    if told:
        left = {**told, "text": "", "next_idea": "", "by": ""}
        if left != told:
            loop._write(loop.folder() / f"explanation-{rid}.json", left)
            gone.append(f"explanation-{rid}.json の文")
    return gone


def _scrub_spoken(rid):
    """話した字と書いた字を消す（--talk-only）。根拠に使われた記録でも、その人の言葉は消せるように（本人の決定の線。写真と動画の --media-only と同じ形）。
    記録の番号と寸法の根拠は残し、版の根拠は数として読める。案は残す（試した記録が指す先で、札に出さない印でもあるため）が、字の写し（words の記録と OWN-n の動かし方）と、
    字が刷られた紙（手順の紙・型紙なしの紙）は消す。話した字の無い型紙と試した後の紙は残す。別の記録がその案を使っていても消す（字は本人の物で、寸法の根拠は残るため）。
    Claude が書いた解釈と案の文は全部、人の字は引用を含む文を消す（_scrub_quotes）。記録に書いた字と手書きの説明の字も空にする（_blank_written。本人の決めた説明文が本当になるように）。"""
    from . import hypotheses, loop, making_log

    talks = _talk_files()
    made = list(_spoken_of(rid, talks))
    path = folder() / f"{rid}.json"
    rec, told = store.read_json_or_skip(path) if path.exists() else None, loop.explanation(rid)
    # 消す字を先に集めて、引用から消す。字を先に消すと、途中で落ちた後の回し直しで引用を見つけられない。
    own_ids = {w.get("own_id") for _, w in made if w.get("own_id")}
    said = [t.get("text") for t in talks.values() if t.get("record_id") == rid or (t.get("hypothesis_id") in own_ids and not t.get("record_id"))]
    said += [t.get("text") for _, w in made if (t := talks.get(w["from_talk"])) and t.get("record_id") in (None, rid)]
    said += [w.get("how_it_moves") for _, w in made]
    written = _written(rec, told)
    spoken = _compared(said, written)
    # 字の無い記録からは何も消さない。字があれば、比べる字が無くても Claude の文は消す（その人の字から書いた文なので）。
    gone = _scrub_quotes(rid, spoken) if [x for x in said if x] or written else []
    for p, w in made:
        sid, oid, stem = w.get("source_id"), w.get("own_id"), w["from_talk"]
        # 先に写しを消す。途中で落ちても、回し直しで残りを見つけられる。理由の欄（not_fit・filled_in の why）は、Claude が書いた結果なら全部（言い換えで残るため）、作る側が書いた結果なら引用だけ（寸法と名前は残す）。
        result = _blank(w.get("result")) if w.get("trace") and not w.get("filled_by") else _without_quotes(w.get("result"), spoken)
        scrubbed = {**w, "how_it_moves": "", "result": result}
        if scrubbed != w:
            loop._write(p, scrubbed)
            gone.append(p.name)
        if oid:
            gone += hypotheses.scrub_own(sid, oid)
            gone += _drop_loose_talk(sid, oid, talks)
        # 元の考えの字。ほかの記録に結ばれた字は、その記録の物なので残す。
        if stem in talks and talks[stem].get("record_id") in (None, rid):
            (making_log.folder() / f"{stem}.json").unlink(missing_ok=True)
            gone.append(f"making/{stem}.json")
    return gone + _blank_written(rid, rec, told)  # 最後に消す。途中で落ちても、回し直しで字を読み直して引用を見つけられる


def _drop_spoken(rid):
    """話した考えから作った案（ループ1、Issue #335）のうち、この記録に関わる物を消す。消した物の名前を返す。人の言葉を、取り下げた記録の外に残さないため。
    関わる物は _spoken_of。
    別の記録がまだその案を使っている時は残す（試した記録が指す先を失わない）。最後の記録を取り下げた時に消える。
    置き場を読むのは words の記録の形だけ（api へは依らない）。書いて立てた仮説は from_talk を持たないので触らない。"""
    from . import hypotheses, loop, making_log

    talks = _talk_files()
    gone = []
    for p, w in list(_spoken_of(rid, talks)):
        sid, oid, stem = w.get("source_id"), w.get("own_id"), w["from_talk"]
        if oid and any(r["hypothesis_id"] == oid and r["id"] != rid for r in all_records(sid)):
            continue
        if oid:
            gone += hypotheses.drop_own(sid, oid)
            for conf in sorted(loop.folder().glob(f"sheet-confirm-{sid}-{oid}-v*.json")):  # 消えた紙の確定の記録も残さない
                conf.unlink()
                gone.append(conf.name)
            gone += _drop_loose_talk(sid, oid, talks)  # 消えた紙を指す字を残さない
        # 元の考えの字。ほかの記録に結ばれた字は、その記録の物なので残す。
        if stem in talks and talks[stem].get("record_id") in (None, rid):
            (making_log.folder() / f"{stem}.json").unlink(missing_ok=True)
            gone.append(f"making/{stem}.json")
        p.unlink()  # 最後に消す。途中で落ちても、回し直しで残りを見つけられる
        gone.append(p.name)
    return gone


def withdraw(rid, media_only=False, talk_only=False):
    """取り下げ。消した物の名前の一覧と Failure の一覧を返す。

    なぜ番号だけ残すか: 持ち寄りの取り下げと同じ形。番号を使い回さず、記録が別の経路で戻っても一覧に出さないため。
    根拠に使われている記録は消さない。版や提案の根拠が指す先を失うため。その時も写真と動画は media_only で消せる
    （写った顔や名札を、根拠の話のために残さない）。観察と動画の札は動画から作った文なので一緒に消す。説明と解釈は人の言葉と根拠なので残す。
    話した字（考え・工夫・上げた後）と書いた字（ひとこと・感想・答え・思いつき・工夫・手書きの説明）は talk_only で消せる（_scrub_spoken）。写真だけ消したい時に字まで消さないよう、media_only とは分ける。両方を渡せば両方消える。
    """
    from . import loop

    if not re.fullmatch(r"R-[0-9]{4,}", rid):
        return [], [Failure("F8.references", rid, "記録の番号の形が違う")]
    path, mark = folder() / f"{rid}.json", withdrawn_folder() / f"{rid}.json"
    with store.locked(loop.folder()):
        # 打ち間違いの番号で「取り下げた」と答えない。印だけある番号は、途中で落ちた後の回し直しとして通す
        if not (path.exists() or mark.exists()):
            return [], [Failure("F8.references", rid, "その番号の記録は無い")]
        whole = not media_only and not talk_only
        users = used_by(rid)
        if users and whole:
            return [], [Failure("F4.evidence", rid, f"{'、'.join(users)} の根拠に使われているので消さなかった。写真と動画だけなら --media-only、話した字と書いた字だけなら --talk-only。{WITHDRAW_NOTICE}")]
        kinds = OWN if whole else ("observation", "video") if media_only else ()
        files = [loop.folder() / f"{kind}-{rid}.json" for kind in kinds] + ([path] if whole else [])
        media = folder() / "media" / rid
        if whole:
            # 印を先に置く。途中で落ちても、記録は一覧に出ない
            mark.parent.mkdir(parents=True, exist_ok=True)
            store.write_json(mark, {"id": rid, "status": "withdrawn", "withdrawn_at": datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")})
        gone = ([f"media/{rid}/{p.name}" for p in sorted(media.glob("*"))] if whole or media_only else []) + [p.name for p in files if p.exists()]
        if whole:
            gone += _drop_spoken(rid)  # 記録を消す前に読む（試した紙がどの案かは、記録にしか無い）
        if talk_only:
            gone += _scrub_spoken(rid)
        if media.exists() and (whole or media_only):
            from . import media_review  # 循環を避けて、ここで読む（media_review は records を読む）

            with media_review.media_lock():  # 同時の上げ・確認の書き込みと取り合わない（安全の事項 2 への対応）
                shutil.rmtree(media, ignore_errors=False)
        for p in files:
            p.unlink(missing_ok=True)
        if whole or talk_only:
            # 記録に結んだ「話した事」も消す（Issue #279）。人の言葉を、取り下げた記録の外に残さないため。
            from . import talk_log

            gone += talk_log.drop_for_record(rid)
    return gone, []


def summarize(records):
    """仮説ごとの集計。値を別々に数え、合算しない（F3）。順位は付けない（J-025）。"""
    table = {}
    for r in records:
        row = table.setdefault(r["hypothesis_id"], {x: 0 for x in results_for(r["source_id"])} | {"record_ids": []})
        word = result_word(r)
        if word:
            row[word] = row.get(word, 0) + 1  # 前の札の記録は、その言葉のまま別に数える
        row["record_ids"].append(r["id"])
    return table


def parse_fix(text):
    parts = text.split(",", 2)
    return dict(zip(("part", "change", "outcome"), [x.strip() for x in parts] + [""] * (3 - len(parts))))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="omochae.records")
    ap.add_argument("--source", default="NDL-1187053-R0000005-L")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add")
    a.add_argument("--hypothesis", required=True)
    a.add_argument("--result", required=True, help="御来迎は動いた／動かない／わからない、虎は揺れた／揺れない／わからない")
    a.add_argument("--opened-deg", type=float)
    a.add_argument("--opener", help="紙の力／糸／手")
    a.add_argument("--predicted-deg", type=float)
    a.add_argument("--version", type=int, default=1)
    a.add_argument("--ten-swings-sec", type=float)
    a.add_argument("--power", help="動かした物。手／息／団扇／風")
    a.add_argument("--fix", action="append", default=[], help="部品,変えた事,結果")
    a.add_argument("--note", default="")
    # 手順の紙の問いの答え。「動いたか」だけでなく、「すぐ返ってきたか」「作る途中で考えが湧いたか」を見る物差しのため（J-013）。
    a.add_argument("--first-moved", default="", help="最初に動いたのはどこか")
    a.add_argument("--stuck", default="", help="引っかかった所はどこか")
    a.add_argument("--what-if", default="", help="何を変えると違いが出そうか")
    a.add_argument("--idea", action="append", default=[], help="作っている途中で思いついた事")
    a.add_argument("--minutes-to-try", type=float, help="作り始めて最初に動かすまでの分")
    sub.add_parser("summary")
    w = sub.add_parser("withdraw", help="記録と、添えた写真・動画・説明・解釈・観察を消す。根拠に使われている記録は止まる")
    w.add_argument("id", help="記録の番号。R-0003 のように")
    w.add_argument("--media-only", action="store_true", help="記録は残し、写真と動画と観察だけを消す")
    w.add_argument("--talk-only", action="store_true", help=f"記録は残し、話した字（考え・工夫・上げた後）と書いた字（ひとこと・感想・工夫・手書きの説明）と、字が刷られた紙だけを消す。根拠に使われた記録でも消せる。{WITHDRAW_NOTICE}")
    try:
        args = ap.parse_args(argv)
    except SystemExit as e:
        return 0 if e.code == 0 else 4
    try:
        if args.cmd == "summary":
            print(json.dumps(summarize(all_records(args.source)), ensure_ascii=False, indent=2))
            return 0
        if args.cmd == "withdraw":
            gone, failures = withdraw(args.id, args.media_only, args.talk_only)
            for f in failures:
                print(f.line(), file=sys.stderr)
            if not failures:
                what = "と".join(n for n, on in (("写真と動画", args.media_only), ("話した字と書いた字", args.talk_only)) if on) or "記録"
                print(f"{args.id} の{what}を取り下げました。消した物: {'、'.join(gone) or 'なし'}")
                print(WITHDRAW_NOTICE)
            return 3 if failures else 0
        rec = {"source_id": args.source, "hypothesis_id": args.hypothesis, "sheet_version": args.version, "result": args.result, "opened_deg": args.opened_deg, "opener": args.opener,
               "predicted_deg": args.predicted_deg, "ten_swings_sec": args.ten_swings_sec, "power": args.power, "fixes": [parse_fix(x) for x in args.fix], "note": args.note,
               "answers": {k: v for k, v in (("first_moved", args.first_moved), ("stuck", args.stuck), ("what_if", args.what_if)) if v}, "ideas": args.idea, "minutes_to_try": args.minutes_to_try}
        rid, failures = add(rec)
    except (OSError, ValueError, KeyError) as e:
        print(f"検査できない: {type(e).__name__}: {e}", file=sys.stderr)
        return 4
    for f in failures:
        print(f.line(), file=sys.stderr)
    if failures:
        return 3
    print(f"{rid} を残しました")
    return 0


if __name__ == "__main__":
    sys.exit(main())
