"""版の歩みの決め方の部品: その版がどのループで走ったかと、どういう知見かを、記録から読む。頁は ayumi.py が持つ。

本人の希望（2026-11-06）: 「その改善が、どこの改善ループで走った物か（ループ1〜4のどれか）も見れるといい」。
統括の決め（11-06）: 答えは記録から決める。手で足した欄は使わない。審査の人は utsushi だけを clone するので、答えは repo の中の data だけで決まる。

判断の芯:
- どのループかは、判定でなく通った道で決める（本人の 4 つのループ、11-05 17:57）:
  - ループ 3: 雛形の直し（T-番号）と、案から刻んだエンジンの版（型紙を作る側を直した物）。材料の記録が通ったループも並べる。
  - 寸法の版は根拠の記録で決める。話した考えから作った紙（OWN-n）の記録はループ 1 も付く。作りながらの話がある記録と、話の無い記録はループ 2。
    上げた後に残した話や、上げる口から来た記録はループ 4。
  - 作る前のレビューは作っていないので、4 つのどれにも数えず、材料の名で出す。
  - 記録に結ばれていない直し（試す前の設計・見学者の意見・決定だけの直し）は「ループの外」。ループに入れて見せない。
- repo に入っている記録（11-04 の試行の分）は、置き場（OMOCHAE_DATA）が別の場でも読む。読まないと、同じ版の答えが場によって変わる。
  置き場の同じ番号は別の記録なので、repo の直しの根拠は repo から読み、置き場の話した字を混ぜない。
- エンジンの台帳は別の repo にある。在れば読み、無くても止めない。答え（v8 がループ 3 など）は台帳に頼らない。
  隣の木は作業の途中の枝のことがあるので、main の中身を git から読み、読めなければ木の中のファイルを読む。
- 知見は人が書いた字だけを写す（人の説明・次の思いつき・止まった所・人の工夫・人が確かめた読み・話した工夫）。機械が要約した文を作らない。
  その記録の字だけで、ほかの記録の字を混ぜない。案のままの読みと作る側が隠した字は読まない。床より前の記録や手で置いた記録もあるので、
  出す時にも入口の床（talk_log.blocked）を当てる。採った人と説明した人の名前は返さない。動きの札の数も返さない（J-025）。
"""
import json
import os
import pathlib
import re
import subprocess

from api import words
from omochae import loop, records, store, talk_log
from omochae.hypotheses import ROOT

OUTSIDE = "ループの外"
REVIEW_NAME = "作る前のレビュー"
RECORD_ID = re.compile(r"R-[0-9]{4,}")
# 案の数のうち、作る時の記録から来た数と、上げた後の話の数（engine_loop の numbers の欄）。
MAKING_NUMBERS = ("stuck_people", "stuck_taps", "quit_people", "craft_talks", "craft_people", "fixes", "ideas", "not_moved")
MADE_NUMBERS = ("keeps",)


def _repo_json(*parts):
    """repo に入っている記録を読む。置き場（OMOCHAE_DATA）を見ない。無い・読めない時は None。"""
    return store.read_json_or_skip(ROOT.joinpath("data", *parts))


def template_changes():
    """雛形の直しの記録。置き場の分に、repo の分を足す。番号は置き場ごとに振るので、番号と組の名の両方が同じ時だけ同じ物と見る。
    repo の分には in_repo の印を付ける（根拠の記録も repo から読むため）。"""
    seen = {(t.get("id"), t.get("sheet_set")): t for t in loop.template_changes()}
    for path in sorted((ROOT / "data/loop").glob("template-change-*.json")):
        t = store.read_json_or_skip(path)
        if t:
            seen.setdefault((t.get("id"), t.get("sheet_set")), {**t, "in_repo": True})
    return list(seen.values())


def _record(rid, in_repo=False):
    if not (isinstance(rid, str) and RECORD_ID.fullmatch(rid)):
        return None
    if in_repo:
        return _repo_json("records", f"{rid}.json")
    try:
        return loop.record(rid)
    except ValueError:
        return None


def record_loops(rid, in_repo=False):
    """記録が通ったループ。Returns (番号の list, 作る前のレビューか)。読めない記録は何も付けない。"""
    rec = _record(rid, in_repo)
    if rec is None:
        return [], False
    if rec.get("video_kind") == "review":
        return [], True
    said = [] if in_repo else [t["when"] for t in talk_log.kufu(rec.get("source_id"), rid)]
    made = rec.get("via") == records.UPLOADED or talk_log.WHEN["keep"] in said
    out = {1} if not in_repo and rec.get("hypothesis_id") in words.spoken_own_ids(rec.get("source_id")) else set()
    if talk_log.WHEN["craft"] in said or not made:
        out.add(2)
    if made:
        out.add(4)
    return sorted(out), False


def _reading(interpretation):
    """人が確かめた読み。人が書いた字か、Claude の案を人が確かめた物。案のままの読みは出さない。"""
    if not interpretation or interpretation.get("status") != "confirmed":
        return []
    c = interpretation.get("content")
    if isinstance(c, dict):
        return [str(x) for x in c.get("observed", [])] + [str(x.get("text", "")) for x in c.get("causes", []) if isinstance(x, dict)]
    return [str(c)] if c else []


def _said(text):
    """頁に出してよい字か。"""
    return isinstance(text, str) and bool(text.strip()) and not talk_log.blocked(text)


def record_words(rid, in_repo=False):
    """記録について人が書いた・話した字。頁にそのまま並べる形で返す。"""
    rec = _record(rid, in_repo)
    if rec is None:
        return []
    told = (_repo_json("loop", f"explanation-{rid}.json") if in_repo else loop.explanation(rid)) or {}
    out = []
    if _said(told.get("text")):
        out.append(f"人の説明 {rid}: {told['text']}" + (f" 次の思いつき: {told['next_idea']}" if _said(told.get("next_idea")) else ""))
    answers = rec.get("answers") if isinstance(rec.get("answers"), dict) else {}
    if _said(answers.get("stuck")):
        out.append(f"止まった所 {rid}: {answers['stuck']}")
    for f in rec.get("fixes") if isinstance(rec.get("fixes"), list) else []:
        fix = " / ".join(str(f.get(k, "")) for k in ("part", "change", "outcome")) if isinstance(f, dict) else ""
        if _said(fix):
            out.append(f"人の工夫 {rid}: {fix}")
    out += [f"読み {rid}: {x}" for x in _reading(_repo_json("loop", f"interpretation-{rid}.json") if in_repo else loop.interpretation(rid)) if _said(x)]
    if not in_repo:  # 話した字は git に入れないので、repo の記録には無い。床は maker_talk の中で当たる
        for t in loop.maker_talk(rid)["items"]:
            where = f"手順 {t['step']} で話した工夫" if t["step"] else ("上げた後の話" if t["when"] == talk_log.WHEN["keep"] else "作りながら話した工夫")
            out.append(f"{where} {rid}: {t['text']}")
    return out


def change_words(changes):
    """雛形の直しの根拠の記録の字。"""
    return [x for t in changes for rid in t.get("record_ids", []) for x in record_words(rid, t.get("in_repo", False))]


def change_toys(change):
    """雛形の直しの根拠の記録の玩具。組の名が雛形に当たらなくても、根拠の記録から引く。読めなければ空。"""
    recs = (_record(rid, change.get("in_repo", False)) for rid in change.get("record_ids", []))
    return sorted({r["source_id"] for r in recs if r and r.get("source_id")})


def _verdict(loops=(), material=(), review=False):
    return {"loops": sorted(set(loops)), "material": sorted(set(material)), "review": bool(review)}


def change_verdict(changes):
    """組の答え。雛形の直しの記録があればループ 3 で、根拠の記録が通ったループが材料。無ければ記録に結ばれていないので、ループの外。"""
    hits = [record_loops(rid, t.get("in_repo", False)) for t in changes for rid in t.get("record_ids", [])]
    return _verdict([3] if changes else [], [n for loops, _ in hits for n in loops], any(review for _, review in hits))


def set_verdict(names):
    """組の名（複数でもよい）の答え。"""
    return change_verdict([t for t in template_changes() if t.get("sheet_set") in names])


def version_verdict(version):
    """寸法の版の答え。根拠の記録で決める。根拠が読めない時はループ 2 と見る（版は記録からしか作れない）。"""
    hits = [record_loops(rid) for rid in version.get("record_ids", [])]
    loops, review = [n for ns, _ in hits for n in ns], any(r for _, r in hits)
    return _verdict(loops or ([] if review else [2]), (), review)


def _proposals(version):
    return [p for p in version.get("proposals", []) if isinstance(p, dict)]


def _number_loops(numbers):
    return ([2] if any(numbers.get(k) for k in MAKING_NUMBERS) else []) + ([4] if any(numbers.get(k) for k in MADE_NUMBERS) else [])


def engine_verdict(version):
    """エンジンの版の答え。案から刻んだ版はループ 3 で、案の数から材料を読む。案の無い版は、輪を足す前の形なのでループの外。"""
    numbers = [p.get("numbers", {}) for p in _proposals(version)]
    return _verdict([3] if version.get("proposals") else [], [n for x in numbers for n in _number_loops(x)], any(x.get("reviews") for x in numbers))


def tag(verdict):
    """答えの字。"""
    joined = lambda ns: "・".join(str(n) for n in ns)
    notes = ([f"材料はループ {joined(verdict['material'])}"] if verdict["material"] else []) + ([f"材料は{REVIEW_NAME}"] if verdict["review"] else [])
    return (f"ループ {joined(verdict['loops'])}" if verdict["loops"] else OUTSIDE) + (f"（{'・'.join(notes)}）" if notes else "")


def engine_ledger():
    """エンジンの版の台帳。無い・読めない時は None。場所は omochae.cycle と同じ決め方（環境の値が先で、無ければ隣の repo）。"""
    place = os.environ.get("OMOCHAE_ENGINE_REPO")
    if place:
        return store.read_json_or_skip(pathlib.Path(place) / "data/engine/versions.json")
    repo = ROOT.parent / "paper-to-toy"
    try:
        shown = subprocess.run(["git", "-C", str(repo), "show", "refs/remotes/origin/main:data/engine/versions.json"], capture_output=True, timeout=5)
        obj = json.loads(shown.stdout) if shown.returncode == 0 else None
        if isinstance(obj, dict):
            return obj
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    return store.read_json_or_skip(repo / "data/engine/versions.json")


def engine_findings(version):
    """採る人が書いた知見の 1 行（adopt --finding）。"""
    return [f"{p['finding']}（案 {p.get('id', '')}）" for p in _proposals(version) if _said(p.get("finding"))]


def engine_shared(ledger):
    """版に入った、部品と生成の決まりの案。雛形をまたぐ直しなので、共通の知見に並ぶ。まだ版に入っていない案（next）は読まない。"""
    out = []
    for v in (ledger or {}).get("versions", []):
        for p in _proposals(v):
            kind, name = p.get("target", {}).get("kind"), p.get("target", {}).get("name", "")
            if kind in ("part", "rule"):
                numbers = p.get("numbers", {})
                out.append({"finding": p["finding"] if _said(p.get("finding")) else p.get("title", ""), "where": name, "all": kind == "part",
                            "from": f"エンジンの版 {v.get('version', '')}・案 {p.get('id', '')}", "verdict": _verdict([3], _number_loops(numbers), numbers.get("reviews"))})
    return out
