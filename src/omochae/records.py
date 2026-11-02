"""試した記録（再現例）の入口。人が入れた物だけを記録にする。

判断の芯: 成否は人が決める 3 値で、写真から判定しない。「わからない」を「動いた」に数えない。
直した点は 3 欄が揃った物だけを残す。次の版や順位を変える根拠になるので、あいまいな記録を混ぜないため。
"""
import argparse
import json
import os
import pathlib
import re
import sys
from datetime import datetime, timedelta, timezone

from .contrib import check_pii
from .hypotheses import load, own_hypotheses
from .model import Failure

ROOT = pathlib.Path(__file__).resolve().parents[2]
RESULTS = ("動いた", "動かない", "わからない")
OPENERS = ("紙の力", "糸", "手")


def folder():
    return pathlib.Path(os.environ.get("OMOCHAE_DATA", ROOT / "data")) / "records"


def known_hypothesis(source_id, hypothesis_id):
    return any(h["id"] == hypothesis_id for h in load(source_id)["hypotheses"]) or any(h["id"] == hypothesis_id for h in own_hypotheses(source_id))


def check(rec):
    out = []
    if rec.get("result") not in RESULTS:
        out.append(Failure("F3.result", "result", f"結果は {'／'.join(RESULTS)} のどれか"))
    if not known_hypothesis(rec["source_id"], rec.get("hypothesis_id")):
        out.append(Failure("F8.references", "hypothesis_id", f"仮説 {rec.get('hypothesis_id')} は実在しない"))
    deg = rec.get("opened_deg")
    if deg is not None and not (isinstance(deg, (int, float)) and not isinstance(deg, bool) and 0 <= deg <= 360):
        out.append(Failure("F3.result", "opened_deg", "開いた角度は 0〜360"))
    if rec.get("opener") is not None and rec["opener"] not in OPENERS:
        out.append(Failure("F3.result", "opener", f"開いた力は {'／'.join(OPENERS)} のどれか"))
    for i, fix in enumerate(rec.get("fixes", []), 1):
        if not all(str(fix.get(k, "")).strip() for k in ("part", "change", "outcome")):
            out.append(Failure("F3.result", f"fixes[{i}]", "直した点は部品名・変えた事・結果の 3 欄が要る"))
    # 記録は公開の repo に入り得るので、連絡先の形を残さない。
    for f in check_pii({"body": rec.get("note", "") + " " + " ".join(str(v) for fix in rec.get("fixes", []) for v in fix.values())}):
        out.append(Failure("F3.result", "note", f.message))
    return out


def add(rec):
    failures = check(rec)
    if failures:
        return None, failures
    d = folder()
    d.mkdir(parents=True, exist_ok=True)
    nums = [int(m.group(1)) for p in d.glob("R-*.json") if (m := re.fullmatch(r"R-(\d{4,})\.json", p.name))]
    while True:
        rid = f"R-{max(nums, default=0) + 1:04d}"
        out = {**rec, "id": rid, "by": "human", "recorded_at": datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")}
        try:
            with open(d / f"{rid}.json", "x", encoding="utf-8") as f:
                json.dump(out, f, ensure_ascii=False, indent=2)
                f.write("\n")
            return rid, []
        except FileExistsError:
            nums.append(int(rid[2:]))


def all_records(source_id=None):
    out = []
    for p in sorted(folder().glob("R-*.json")):
        rec = json.loads(p.read_text(encoding="utf-8"))
        if source_id is None or rec.get("source_id") == source_id:
            out.append(rec)
    return out


def summarize(records):
    """仮説ごとの集計。3 値を別々に数え、合算しない（F3）。順位は付けない。順位を変えるのは人の確認（H7）。"""
    table = {}
    for r in records:
        row = table.setdefault(r["hypothesis_id"], {x: 0 for x in RESULTS} | {"record_ids": []})
        row[r["result"]] += 1
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
    a.add_argument("--result", required=True, help="動いた／動かない／わからない")
    a.add_argument("--opened-deg", type=float)
    a.add_argument("--opener", help="紙の力／糸／手")
    a.add_argument("--predicted-deg", type=float)
    a.add_argument("--version", type=int, default=1)
    a.add_argument("--fix", action="append", default=[], help="部品,変えた事,結果")
    a.add_argument("--note", default="")
    sub.add_parser("summary")
    try:
        args = ap.parse_args(argv)
    except SystemExit as e:
        return 0 if e.code == 0 else 4
    try:
        if args.cmd == "summary":
            print(json.dumps(summarize(all_records(args.source)), ensure_ascii=False, indent=2))
            return 0
        rec = {"source_id": args.source, "hypothesis_id": args.hypothesis, "sheet_version": args.version, "result": args.result, "opened_deg": args.opened_deg, "opener": args.opener,
               "predicted_deg": args.predicted_deg, "fixes": [parse_fix(x) for x in args.fix], "note": args.note}
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
