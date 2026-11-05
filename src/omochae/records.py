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
from datetime import datetime, timedelta, timezone

from . import store
from .contrib import check_pii, too_long
from .hypotheses import load, own_hypotheses
from .model import Failure

ROOT = pathlib.Path(__file__).resolve().parents[2]
OPENERS = ("紙の力", "糸", "手")
OWN = ("explanation", "interpretation", "observation")  # 記録ごとに輪の置き場へ書く物


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
    if rec.get("result") not in (*results, *old_results_for(rec["source_id"])):
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


def all_records(source_id=None):
    out = []
    for p in sorted(folder().glob("R-*.json")):
        if (withdrawn_folder() / p.name).exists():
            continue
        rec = store.read_json_or_skip(p)
        if rec is not None and (source_id is None or rec.get("source_id") == source_id):
            out.append(rec)
    return out


def used_by(rid):
    """この記録を根拠にしている物のファイル名。欄ごとに見ず番号の字で探す。根拠の欄が増えても見落とさないため。"""
    mine = {f"{kind}-{rid}.json" for kind in OWN}
    word = re.compile(rf"(?<![\w-]){rid}(?![\w-])")
    base = folder().parent
    return sorted(p.name for d in ("loop", "decisions") for p in (base / d).glob("*.json")
                  if p.name not in mine and word.search(p.read_text(encoding="utf-8", errors="replace")))


def withdraw(rid, media_only=False):
    """取り下げ。消した物の名前の一覧と Failure の一覧を返す。

    なぜ番号だけ残すか: 持ち寄りの取り下げと同じ形。番号を使い回さず、記録が別の経路で戻っても一覧に出さないため。
    根拠に使われている記録は消さない。版や提案の根拠が指す先を失うため。その時も写真と動画は media_only で消せる
    （写った顔や名札を、根拠の話のために残さない）。観察は動画から作った文なので一緒に消す。説明と解釈は人の言葉と根拠なので残す。
    """
    from . import loop

    if not re.fullmatch(r"R-[0-9]{4,}", rid):
        return [], [Failure("F8.references", rid, "記録の番号の形が違う")]
    path, mark = folder() / f"{rid}.json", withdrawn_folder() / f"{rid}.json"
    with store.locked(loop.folder()):
        # 打ち間違いの番号で「取り下げた」と答えない。印だけある番号は、途中で落ちた後の回し直しとして通す
        if not (path.exists() or mark.exists()):
            return [], [Failure("F8.references", rid, "その番号の記録は無い")]
        users = used_by(rid)
        if users and not media_only:
            return [], [Failure("F4.evidence", rid, f"{'、'.join(users)} の根拠に使われているので消さなかった。写真と動画だけなら --media-only")]
        kinds = ("observation",) if media_only else OWN
        files = [loop.folder() / f"{kind}-{rid}.json" for kind in kinds] + ([] if media_only else [path])
        media = folder() / "media" / rid
        if not media_only:
            # 印を先に置く。途中で落ちても、記録は一覧に出ない
            mark.parent.mkdir(parents=True, exist_ok=True)
            store.write_json(mark, {"id": rid, "status": "withdrawn", "withdrawn_at": datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")})
        gone = [f"media/{rid}/{p.name}" for p in sorted(media.glob("*"))] + [p.name for p in files if p.exists()]
        if media.exists():
            shutil.rmtree(media)
        for p in files:
            p.unlink(missing_ok=True)
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
    try:
        args = ap.parse_args(argv)
    except SystemExit as e:
        return 0 if e.code == 0 else 4
    try:
        if args.cmd == "summary":
            print(json.dumps(summarize(all_records(args.source)), ensure_ascii=False, indent=2))
            return 0
        if args.cmd == "withdraw":
            gone, failures = withdraw(args.id, args.media_only)
            for f in failures:
                print(f.line(), file=sys.stderr)
            if not failures:
                print(f"{args.id} の{'写真と動画' if args.media_only else '記録'}を取り下げました。消した物: {'、'.join(gone) or 'なし'}")
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
