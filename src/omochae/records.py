"""試した記録の入口。成績でなく観察の記録で、人が入れた物だけを残す（philosophy.md）。

判断の芯: 何が起きたかは人が決める値で、写真から判定しない。「動かない」は失敗でなく自然の返事。「わからない」を「動いた」に数えない。値は雛形が持つ（虎は揺れた／揺れない）。
札を直しても、前の札で残った記録の中身は書き換えない（読み手が読めるように、雛形の OLD_RESULTS が今の札との対応を持つ。#146）。
直した点は 3 欄が揃った物だけを残す。次の版や次に試す物の提案の根拠になるので、あいまいな記録を混ぜないため。
"""
import argparse
import json
import os
import pathlib
import re
import shutil
import sys
import unicodedata
from datetime import datetime, timedelta, timezone

from . import store
from .contrib import check_pii, too_long
from .hypotheses import load, own_hypotheses
from .model import Failure

ROOT = pathlib.Path(__file__).resolve().parents[2]
OPENERS = ("紙の力", "糸", "手")
OWN = ("explanation", "interpretation", "observation", "video")  # 記録ごとに輪の置き場へ書く物
# 動画の受け口（web/video_up.py）から来た記録の印。上げた人に「頁に出さない」と約束した物で、紙も人が確かめていないので、all_records は既定で外す。
UPLOADED = "video-up"
UNSURE = "わからない"


def folder():
    return pathlib.Path(os.environ.get("OMOCHAE_DATA", ROOT / "data")) / "records"


def withdrawn_folder():
    return folder() / "withdrawn"


def results_for(source_id):
    from .compose import TEMPLATES

    return TEMPLATES[load(source_id).get("template", "slider_fan")].RESULTS


def old_results_for(source_id):
    """前の札の言葉 → 今の札の言葉。新しく選ばせる札でなく、前の札で残った記録を読むための受け口（#146）。"""
    from .compose import TEMPLATES

    return getattr(TEMPLATES[load(source_id).get("template", "slider_fan")], "OLD_RESULTS", {})


def known_hypothesis(source_id, hypothesis_id):
    return any(h["id"] == hypothesis_id for h in load(source_id)["hypotheses"]) or any(h["id"] == hypothesis_id for h in own_hypotheses(source_id))


def check(rec):
    out = []
    results = results_for(rec["source_id"])
    # 前の札も受ける。札を直す前に開いた頁から送られても、記録を断らないため。断りの文には今の札だけを出す。
    # 受け口は動いたかを聞かない（動画だけが届く）。雛形の札に「わからない」が無くても、決めつけずにこの字で受ける。束はこの字を数えない
    if rec.get("result") not in (*results, *old_results_for(rec["source_id"])) and not (rec.get("via") == UPLOADED and rec.get("result") == UNSURE):
        out.append(Failure("F3.result", "result", f"結果は {'／'.join(results)} のどれか"))
    if not known_hypothesis(rec["source_id"], rec.get("hypothesis_id")):
        out.append(Failure("F8.references", "hypothesis_id", f"仮説 {rec.get('hypothesis_id')} は実在しない"))
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
    while True:
        rid = f"R-{max(nums, default=0) + 1:04d}"
        out = {**rec, "id": rid, "by": "human", "recorded_at": datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")}
        try:
            store.write_json(d / f"{rid}.json", out, exclusive=True)
            return rid, []
        except FileExistsError:
            nums.append(int(rid[2:]))


def all_records(source_id=None, uploads=False):
    """記録の一覧。uploads は動画の受け口の記録も含める形で、版の輪の表（trial_video.effect）だけが使う。
    なぜここで外すか: 読む所は学ぶ人の頁・ギャラリー・束など多く、1 つずつ外すと、新しく読む所が足された時に約束が崩れる。
    この関数を通らない所（loop.confirmed_records とサイトの /record の口）は、それぞれで外す。"""
    out = []
    for p in sorted(folder().glob("R-*.json")):
        if (withdrawn_folder() / p.name).exists():
            continue
        rec = store.read_json_or_skip(p)
        if rec is not None and (source_id is None or rec.get("source_id") == source_id) and (uploads or rec.get("via") != UPLOADED):
            out.append(rec)
    return out


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


# 話した字の引用と読む長さ。これより長い字は、この長さの一部が写っていれば引用と読む（Claude は長い字の一部を引く）。短いと、よくある言い回しの文まで消す。
# これより短い字は、全部が写っている時に引用と読む。1 字は読まない（どの文にも当たる）。言い換えは機械で見分けられないので、消せない。
QUOTE_CHARS = 8
# 文でない欄。番号と名前と寸法の字なので、話した字と重なっても消さない。
NOT_TEXT = frozenset(("id", "source_id", "hypothesis_id", "record_id", "record_ids", "references", "param", "params", "from_words", "proposal", "status", "kind"))


def _flat(text):
    """引用を比べる形。声から字にした文は、字の幅と空白が揺れるので、そろえる。"""
    return "".join(unicodedata.normalize("NFKC", str(text)).split())


def _quotes(text, spoken):
    """text に、話した字（_flat した物の一覧）の引用があるか。"""
    flat = _flat(text)
    for s in spoken:
        if len(s) <= QUOTE_CHARS:
            if len(s) > 1 and s in flat:
                return True
        elif any(s[i:i + QUOTE_CHARS] in flat for i in range(len(s) - QUOTE_CHARS + 1)):
            return True
    return False


def _without_quotes(value, spoken):
    """引用を含む文を文ごと消す。一覧の中の文と、文を text に持つ札は、札ごと外す。ほかの欄の文は空にする（欄の形と、並ぶ寸法・番号は残す）。"""
    if isinstance(value, str):
        return "" if _quotes(value, spoken) else value
    if isinstance(value, dict):
        return {k: v if k in NOT_TEXT else _without_quotes(v, spoken) for k, v in value.items()}
    if isinstance(value, list):
        out = []
        for x in value:
            y = _without_quotes(x, spoken)
            if (isinstance(x, str) and x and not y) or (isinstance(x, dict) and x.get("text") and not y.get("text")):
                continue
            out.append(y)
        return out
    return value


def _scrub_quotes(rid, spoken):
    """この記録を根拠にした解釈・案・版・控えの文から、話した字の引用を消す。引用が残ると取り下げにならないため。番号・寸法・版・案の数は残す。消した物の名前を返す。"""
    from . import loop

    gone = []
    if not spoken:
        return gone
    for p in [*_used_paths(rid), loop.interp_path(rid)]:
        before = store.read_json_or_skip(p, (dict, list))
        if before is None:
            continue
        after = _without_quotes(before, spoken)
        if after != before:
            store.write_json(p, after)
            gone.append(f"{p.name} の引用")
    return gone


def _scrub_spoken(rid):
    """話した字だけを消す（--talk-only）。根拠に使われた記録でも、その人の言葉は消せるように（本人の決定の線。写真と動画の --media-only と同じ形）。
    記録の番号と寸法の根拠は残し、版の根拠は数として読める。案は残す（試した記録が指す先で、札に出さない印でもあるため）が、字の写し（words の記録と OWN-n の動かし方）と、
    字が刷られた紙（手順の紙・型紙なしの紙）は消す。話した字の無い型紙と試した後の紙は残す。別の記録がその案を使っていても消す（字は本人の物で、寸法の根拠は残るため）。
    解釈と案と版の文の引用も消す（_scrub_quotes）。言い換えは機械で見分けられないので消せない。"""
    from . import hypotheses, loop, making_log

    talks = _talk_files()
    made = list(_spoken_of(rid, talks))
    # 消す字を先に集めて、引用から消す。字を先に消すと、途中で落ちた後の回し直しで引用を見つけられない。
    own_ids = {w.get("own_id") for _, w in made if w.get("own_id")}
    said = [t.get("text") for t in talks.values() if t.get("record_id") == rid or (t.get("hypothesis_id") in own_ids and not t.get("record_id"))]
    said += [t.get("text") for _, w in made if (t := talks.get(w["from_talk"])) and t.get("record_id") in (None, rid)]
    said += [w.get("how_it_moves") for _, w in made]
    spoken = sorted({_flat(x) for x in said if x})
    gone = _scrub_quotes(rid, spoken)
    for p, w in made:
        sid, oid, stem = w.get("source_id"), w.get("own_id"), w["from_talk"]
        # 先に写しを消す。途中で落ちても、回し直しで残りを見つけられる。作る側か Claude の理由の欄（not_fit・filled_in の why）の引用も同じ（寸法と名前は残す）。
        scrubbed = {**w, "how_it_moves": "", "result": _without_quotes(w.get("result"), spoken)}
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
    return gone


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
    話した字（考え・工夫・上げた後）は talk_only で消せる（_scrub_spoken）。写真だけ消したい時に字まで消さないよう、media_only とは分ける。両方を渡せば両方消える。
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
            return [], [Failure("F4.evidence", rid, f"{'、'.join(users)} の根拠に使われているので消さなかった。写真と動画だけなら --media-only、話した字だけなら --talk-only")]
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
            shutil.rmtree(media)
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
        row[r["result"]] = row.get(r["result"], 0) + 1  # 前の札の記録は、その言葉のまま別に数える
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
    a.add_argument("--result", required=True, help="御来迎は動いた／動かない／わからない、虎は揺れた／揺れない")
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
    w.add_argument("--talk-only", action="store_true", help="記録は残し、話した字（考え・工夫・上げた後）と、字が刷られた紙だけを消す。根拠に使われた記録でも消せる")
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
                what = "と".join(n for n, on in (("写真と動画", args.media_only), ("話した字", args.talk_only)) if on) or "記録"
                print(f"{args.id} の{what}を取り下げました。消した物: {'、'.join(gone) or 'なし'}")
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
