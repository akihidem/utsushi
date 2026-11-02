"""輪の後半: 記録の解釈 → 次の手の提案 → 人の採否 → 版 2・順位・新しい仮説。

判断の芯: Claude は案までで、確定は人の操作だけ。人が確定していない解釈は根拠に使えない（F9）。
人の説明と次の思いつきを先に受ける。作っている人のアイディアより先に AI の原因と次の手が出ると、作る意味を奪うため（J-013）。
変更には記録 ID が要り（F4）、式のある変更は向きを数え直す（F7）。
API の鍵が無くても、人が解釈と変更を書けば同じ道で輪が閉じる（manual）。
"""
import argparse
import json
import os
import pathlib
import re
import sys
from datetime import datetime, timedelta, timezone

from .compose import compose
from .contrib import _human_confirm, check_pii, public_list
from .metrics import ALLOWED, values
from .model import Failure

ROOT = pathlib.Path(__file__).resolve().parents[2]


def base():
    return pathlib.Path(os.environ.get("OMOCHAE_DATA", ROOT / "data"))


def folder():
    d = base() / "loop"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _now():
    return datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")


def _read(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _write(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def record(rid):
    if not re.fullmatch(r"R-[0-9]{4,}", rid):
        raise ValueError(f"記録 ID の形が違う: {rid}")
    rec = _read(base() / "records" / f"{rid}.json")
    if rec is None:
        raise ValueError(f"記録が無い: {rid}")
    return rec


def interp_path(rid):
    return folder() / f"interpretation-{rid}.json"


def interpretation(rid):
    return _read(interp_path(rid))


def confirmed(rid):
    i = interpretation(rid)
    return bool(i and i.get("status") == "confirmed")


def explanation(rid):
    return _read(folder() / f"explanation-{rid}.json")


def save_explanation(rid, by, text, next_idea):
    """人の説明と次の思いつき。「わからない」でも書けばよく、中身は評価しない。"""
    record(rid)
    if not by or not by.strip():
        return [Failure("F9.human", rid, "説明した人の名前が無い")]
    if not (text or "").strip() or not (next_idea or "").strip():
        return [Failure("F9.human", rid, "説明と次の思いつきの両方が要る（わからない、と書いてもよい）")]
    failures = [Failure("F3.result", rid, f.message) for f in check_pii({"body": f"{text} {next_idea}"})]
    if failures:
        return failures
    _write(folder() / f"explanation-{rid}.json", {"record_id": rid, "text": text.strip(), "next_idea": next_idea.strip(), "by": by.strip(), "at": _now()})
    return []


def save_interpretation_draft(rid, content, trace=None):
    record(rid)
    _write(interp_path(rid), {"record_id": rid, "status": "pending_human", "content": content, "drafted_by": "claude", "trace": trace})


def confirm_interpretation(rid, by, content=None):
    """人の確定（H6）。案が無くても、人が書いた解釈で確定できる。"""
    record(rid)
    if not by or not by.strip():
        return [Failure("F9.human", rid, "確定した人の名前が無い")]
    current = interpretation(rid) or {"record_id": rid, "drafted_by": "human"}
    if content is None and "content" not in current:
        return [Failure("F9.human", rid, "解釈の案が無く、人の解釈も無い")]
    if content is not None:
        current["content"] = content
        current["edited_by_human"] = current.get("drafted_by") == "claude"
    current.update(status="confirmed", confirmed_by=by.strip(), confirmed_at=_now())
    _write(interp_path(rid), current)
    return []


def confirmed_records(source_id, known=None):
    """前例として引ける記録。人が解釈を確定した物だけ。"""
    out = []
    d = base() / "records"
    for p in sorted(d.glob("R-*.json")):
        rec = json.loads(p.read_text(encoding="utf-8"))
        if rec.get("source_id") == source_id and confirmed(rec["id"]):
            out.append({**rec, "interpretation": interpretation(rec["id"])["content"]})
    return out


def known_ids():
    ids = {p.stem for p in (base() / "records").glob("R-*.json")}
    ids |= {p.stem for p in (ROOT / "data/known_examples").glob("*.json")}
    ids |= {c["id"] for c in public_list()}
    return ids


def _template(source_id):
    from .hypotheses import load

    return load(source_id).get("template", "slider_fan")


def _hypothesis(source_id, hid):
    from .hypotheses import load, own_hypotheses

    for h in load(source_id)["hypotheses"] + own_hypotheses(source_id):
        if h["id"] == hid:
            return h
    return None


def version_params(source_id, hid, version):
    """版の寸法。版 1 は仮説の寸法で、版 2 以降は採った変更を重ねる。"""
    h = _hypothesis(source_id, hid)
    if h is None:
        raise ValueError(f"仮説が無い: {hid}")
    params = dict(h.get("params") or {})
    if version == 1:
        return params, None
    v = _read(folder() / f"version-{source_id}-{hid}-{version}.json")
    if v is None:
        return None, None
    return v["params"], v


def latest_version(source_id, hid):
    nums = [int(p.stem.rsplit("-", 1)[1]) for p in folder().glob(f"version-{source_id}-{hid}-*.json")]
    return max(nums, default=1)


def check_proposal(p, source):
    """提案の検査。Claude にも人の手書きにも同じ床を当てる。"""
    out = []
    sid = source["source_id"]
    template = _template(sid)
    records = p.get("record_ids") or []
    if not records:
        out.append(Failure("F4.evidence", "record_ids", "根拠の記録 ID が無い"))
    for rid in records:
        if not (base() / "records" / f"{rid}.json").exists():
            out.append(Failure("F8.references", rid, "その記録は実在しない"))
        elif not confirmed(rid):
            out.append(Failure("F9.human", rid, "解釈を人が確定していない記録は根拠にできない"))
    ids = known_ids()
    for ref in p.get("references", []):
        if ref not in ids:
            out.append(Failure("F8.references", ref, "その前例は実在しない"))
    hid = p.get("hypothesis_id")
    changes = p.get("changes") or []
    if changes:
        h = _hypothesis(sid, hid)
        if h is None:
            out.append(Failure("F8.references", str(hid), "その仮説は実在しない"))
        else:
            current, _ = version_params(sid, hid, latest_version(sid, hid))
            merged = dict(current)
            before = values(template, current)
            for c in changes:
                if c.get("param") not in ALLOWED[template]:
                    out.append(Failure("F7.revision", str(c.get("param")), "変えてよい寸法の外"))
                    continue
                if not c.get("why", "").strip():
                    out.append(Failure("F4.evidence", c["param"], "変える理由が無い"))
                merged[c["param"]] = c.get("to")
            if not any(c.get("to") != {**TEMPLATES_DEFAULT(template), **current}.get(c.get("param")) for c in changes):
                out.append(Failure("F7.revision", "changes", "前の版と寸法が変わっていない"))
            if not out:
                _, _, floors = compose(template, merged, source)
                out += floors
            if not out:
                after = values(template, merged)
                for c in changes:
                    metric, direction = c.get("metric"), c.get("direction")
                    c["formula_check"] = "no_formula"
                    if metric:
                        if metric not in after:
                            out.append(Failure("F7.revision", c["param"], f"式 {metric} は無い"))
                        elif (direction == "increase" and after[metric] <= before[metric]) or (direction == "decrease" and after[metric] >= before[metric]):
                            c["formula_check"] = "reverse"
                            out.append(Failure("F7.revision", c["param"], f"{metric} は {before[metric]:.2f} → {after[metric]:.2f} で、{direction} の向きと逆"))
                        else:
                            c["formula_check"] = "ok"
                    c["from"] = {**TEMPLATES_DEFAULT(template), **current}.get(c["param"])
    for r in p.get("ranking", []):
        if _hypothesis(sid, r.get("hypothesis_id")) is None:
            out.append(Failure("F8.references", str(r.get("hypothesis_id")), "順位を変える仮説が実在しない"))
    return out


def TEMPLATES_DEFAULT(template):
    from .compose import TEMPLATES

    return TEMPLATES[template].DEFAULTS


def save_proposal(proposal, source, drafted_by):
    failures = check_proposal(proposal, source)
    if failures:
        return None, failures
    nums = [int(p.stem.split("-")[1]) for p in folder().glob("proposal-*.json")]
    pid = f"P-{max(nums, default=0) + 1:04d}"
    _write(folder() / f"proposal-{pid[2:]}.json", {**proposal, "id": pid, "source_id": source["source_id"], "status": "pending_human", "drafted_by": drafted_by, "drafted_at": _now()})
    return pid, []


def adopt(pid, by, accept_params=(), accept_ranking=False, accept_new=False, source=None):
    """人の採否（H7）。採った物だけが版・順位・仮説の一覧に入る。"""
    path = folder() / f"proposal-{pid[2:]}.json"
    p = _read(path)
    if p is None:
        raise ValueError(f"提案が無い: {pid}")
    if not by or not by.strip():
        return None, [Failure("F9.human", pid, "採否を決めた人の名前が無い")]
    if p["status"] != "pending_human":
        return None, [Failure("F9.human", pid, f"状態 {p['status']} の提案は採れない")]
    # 提案の後に前提が変わっていないか、採る時にも同じ床を当てる。
    sid = p["source_id"]
    source = source or json.loads((ROOT / "data/sources" / f"{sid}.json").read_text(encoding="utf-8"))
    chosen = [c for c in p.get("changes", []) if c["param"] in accept_params]
    failures = check_proposal({**p, "changes": chosen}, source)
    if failures:
        return None, failures
    made = {}
    if chosen:
        hid = p["hypothesis_id"]
        current, _ = version_params(sid, hid, latest_version(sid, hid))
        version = latest_version(sid, hid) + 1
        params = {**current, **{c["param"]: c["to"] for c in chosen}}
        _write(folder() / f"version-{sid}-{hid}-{version}.json", {"source_id": sid, "hypothesis_id": hid, "version": version, "params": params, "changes": chosen, "record_ids": p["record_ids"], "proposal": pid, "adopted_by": by.strip(), "adopted_at": _now()})
        made["version"] = version
    if accept_ranking and p.get("ranking"):
        _write(folder() / f"ranking-{sid}.json", {"ranking": p["ranking"], "record_ids": p["record_ids"], "proposal": pid, "adopted_by": by.strip(), "adopted_at": _now()})
        made["ranking"] = True
    if accept_new and p.get("new_hypothesis"):
        extras_path = folder() / f"extra-hypotheses-{sid}.json"
        extras = _read(extras_path) or []
        new = {**p["new_hypothesis"], "id": f"H-N{len(extras) + 1}", "status": "untested", "rank": None, "evidence": p["new_hypothesis"].get("evidence", []) + [{"kind": "record", "where": rid, "what": "試した記録", "certainty": "記録"} for rid in p["record_ids"]], "proposal": pid, "adopted_by": by.strip()}
        extras.append(new)
        _write(extras_path, extras)
        made["new_hypothesis"] = new["id"]
    p.update(status="decided", decided_by=by.strip(), decided_at=_now(), accepted=made, accepted_params=list(accept_params))
    _write(path, p)
    return made, []


def overlay(data):
    """人が採った順位と新しい仮説を、一覧に重ねる。元の仮説の記録は書き換えない。"""
    sid = data["source_id"]
    extras = _read(folder() / f"extra-hypotheses-{sid}.json") or []
    data["hypotheses"] = data["hypotheses"] + extras
    rank = _read(folder() / f"ranking-{sid}.json")
    if rank:
        order = {r["hypothesis_id"]: r["rank_after"] for r in rank["ranking"]}
        for h in data["hypotheses"]:
            if h["id"] in order:
                h["rank"] = order[h["id"]]
    return data


def main(argv=None):
    ap = argparse.ArgumentParser(prog="omochae.loop")
    ap.add_argument("--source", default="NDL-1187053-R0000005-L")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("explain", help="人の説明と次の思いつきを残す。Claude の案より先に要る")
    s.add_argument("record")
    s.add_argument("--by", required=True)
    s.add_argument("--text", required=True)
    s.add_argument("--next-idea", required=True)
    s = sub.add_parser("interpret", help="人の説明の後に、Claude に解釈の案を作らせる")
    s.add_argument("record")
    s = sub.add_parser("confirm", help="解釈を人が確定する。--text で書き直せる")
    s.add_argument("record")
    s.add_argument("--by", required=True)
    s.add_argument("--text")
    s = sub.add_parser("propose", help="次の手の提案を作る。--change があれば人の手書き")
    s.add_argument("record")
    s.add_argument("--hypothesis")
    s.add_argument("--change", action="append", default=[], help="寸法=値")
    s.add_argument("--why", default="")
    s = sub.add_parser("show")
    s.add_argument("proposal")
    s = sub.add_parser("adopt", help="提案を人が採る")
    s.add_argument("proposal")
    s.add_argument("--by", required=True)
    s.add_argument("--param", action="append", default=[])
    s.add_argument("--ranking", action="store_true")
    s.add_argument("--new", action="store_true")
    try:
        args = ap.parse_args(argv)
    except SystemExit as e:
        return 0 if e.code == 0 else 4
    try:
        source = json.loads((ROOT / "data/sources" / f"{args.source}.json").read_text(encoding="utf-8"))
        failures = []
        if args.cmd == "interpret":
            from api.loop_agents import draft_interpretation

            _, failures = draft_interpretation(args.record)
            if not failures:
                print(json.dumps(interpretation(args.record)["content"], ensure_ascii=False, indent=2))
                print(f"案です。確かめて confirm {args.record} --by 名前 で確定します")
        elif args.cmd == "explain":
            if not _human_confirm(args.record, "説明"):
                failures = [Failure("F9.human", args.record, "端末での人の確認が無い")]
            else:
                failures = save_explanation(args.record, args.by, args.text, args.next_idea)
        elif args.cmd == "confirm":
            if not _human_confirm(args.record, "解釈の確定"):
                failures = [Failure("F9.human", args.record, "端末での人の確認が無い")]
            else:
                failures = confirm_interpretation(args.record, args.by, {"human_text": args.text} if args.text else None)
        elif args.cmd == "propose":
            if args.change:
                changes = []
                for c in args.change:
                    k, v = c.split("=", 1)
                    changes.append({"param": k, "to": float(v), "why": args.why})
                pid, failures = save_proposal({"record_ids": [args.record], "hypothesis_id": args.hypothesis or record(args.record)["hypothesis_id"], "changes": changes}, source, "human")
            else:
                from api.loop_agents import draft_proposal

                pid, failures = draft_proposal(args.record, source)
            if not failures:
                print(f"{pid} を作りました。show で見て adopt で採ります")
        elif args.cmd == "show":
            print(json.dumps(_read(folder() / f"proposal-{args.proposal[2:]}.json"), ensure_ascii=False, indent=2))
        else:
            if not _human_confirm(args.proposal, "採用"):
                failures = [Failure("F9.human", args.proposal, "端末での人の確認が無い")]
            else:
                made, failures = adopt(args.proposal, args.by, args.param, args.ranking, args.new, source)
                if not failures:
                    print(json.dumps(made, ensure_ascii=False))
    except ImportError as e:
        print(f"検査できない: {e}", file=sys.stderr)
        return 4
    except Exception as e:  # 鍵が無い時も含む。値は出さない
        print(f"検査できない: {type(e).__name__}: {str(e)[:200]}", file=sys.stderr)
        return 4
    for f in failures:
        print(f.line(), file=sys.stderr)
    return 3 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
