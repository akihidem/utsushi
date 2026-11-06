"""輪の後半: 記録の解釈 → 次の手の提案 → 人の採否 → 版 2・新しい仮説。

順位は持たない（本人の決定、J-025）。記録で順位が動くと、動いた事を正しさとして扱う成績の形になるため。
記録は「次に試す物」の提案の材料にだけ使う。

判断の芯: Claude は案までで、確定は人の操作だけ。人が確定していない解釈は根拠に使えない（F9）。
人の説明と次の思いつきを先に受ける。作っている人のアイディアより先に AI の原因と次の手が出ると、作る意味を奪うため（J-013）。
変更には記録 ID が要り（F4）、式のある変更は向きを数え直す（F7）。
API の鍵が無くても、人が解釈と変更を書けば同じ道で輪が閉じる（manual）。
作りながら話した工夫の字（talk_log）も、記録・人の説明と並べて材料に入れる（ループ2、Issue #335）。鍵の有無で同じ材料（material）を読む。
"""
import argparse
import functools
import json
import os
import pathlib
import re
import sys
import tempfile
from datetime import datetime, timedelta, timezone

from . import store
from .compose import compose
from .contrib import _human_confirm, check_pii, public_list, too_long
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
    """必ず要る 1 件を読む。無ければ None。壊れていれば、飛ばさずに、どのファイルかを言って止める。一覧の読みは store.read_json_or_skip。"""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError as e:
        raise ValueError(f"読めない記録: {path.name}（{type(e).__name__}）") from e


def _write(path, obj):
    store.write_json(path, obj)


def exclusive(fn):
    """読んで足して書く処理を、輪の置き場の排他の中で動かす。同時に押した 2 台が上書きや番号の重なりを起こさないため。"""
    @functools.wraps(fn)
    def run(*a, **k):
        with store.locked(folder()):
            return fn(*a, **k)
    return run


@exclusive
def save_numbered(kind, letter, make):
    """次の番号を取って `{kind}-{番号}.json` に書く。make は ID を受けて中身を返す。"""
    nums = [int(p.stem.rsplit("-", 1)[1]) for p in folder().glob(f"{kind}-*.json")]
    n = max(nums, default=0) + 1
    rid = f"{letter}-{n:04d}"
    _write(folder() / f"{kind}-{n:04d}.json", make(rid))
    return rid


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
    return store.read_json_or_skip(interp_path(rid))


def confirmed(rid):
    i = interpretation(rid)
    return bool(i and i.get("status") == "confirmed")


def explanation(rid):
    return store.read_json_or_skip(folder() / f"explanation-{rid}.json")


def explained(rid):
    """人の説明の字があるか。取り下げ（records.withdraw の --talk-only）で字が空になった説明は、説明があった印として次の版の床を通るが、
    Claude を呼ぶ前の「人の説明が先」（J-013）は満たさない。その人の字が無いまま、記録だけを Claude に読ませないため。"""
    return bool(((explanation(rid) or {}).get("text") or "").strip())


# ループ2 の材料の仕切りの名（Issue #335）。人の説明（explanation）と混ぜずに、別の札で渡す。
# 「声は残していない」まで書くのは、読む人（作る側と Claude）が、字の後ろに録った声があると思わないため。
TALK_LABEL = "作った人が話した事（字だけ・声は残していない）"
# 渡す欄はこの 3 つだけ。どう入れたか（via）・その場の印（who）・時刻は、誰がいつ話したかを辿る手がかりにしかならず、案の材料に要らない。
TALK_FIELDS = ("when", "step", "text")
# 渡す話した字の上限（字数）。1 件は 400 字まで（talk_log.MAX_TEXT）だが件数に上限が無く、300 件で頼みが 13 万字になった。
# ふつうの作りで話す量（手順ごとに数件）より十分大きくする。超えた分は数だけ渡す。
TALK_MAX_CHARS = 6000


def maker_talk(rid):
    """記録に結んだ、作りながら話した工夫と上げた後に残した字（Issue #335 のループ2）。Returns {"label", "items": [{when, step, text}…], "omitted": 上限で入れなかった字の数}。

    判断の芯:
    - どの字か: その記録に結ばれた字だけ（talk_log.kufu）。結ぶのは記録を残した時の talk_log.bind で、同じ玩具・同じ紙（仮説と版）・
      同じその場の印の物に限る。ここで印や紙を数え直して広げない（印なしで拾うと、ほかの人の話がこの記録の材料に入る）。
    - 場面は工夫（craft）と上げた後（keep）だけ。仮説を見て話した考え（think）はループ1（words の口で紙を生む側）の材料なので混ぜない。
    - 読み方: talk_log.kufu(出典, 記録, shared_only=True)。学ぶ人の頁と同じ字で、作る側が隠した字（set_share）と、入口の床にもう一度当たる字
      （床を広げる前に残った字や、手で置いた字）が外れる。床をここで当て直さない（shared_only の中にある）。
      これより強い絞りは足さない（2b で字は全部見せる決定。本人の指示 11-05 17:55）。
    - 鍵の有無で読む字を変えない。人の道（material の命令）にも隠した字を出さない: 人が読んで書く解釈と案を通って、隠した字が輪に入るため。
      作る側が隠した字を読むのは作る側の頁（hanasu.maker_section の「［隠している］」）。
    - 字の数に上限がある（TALK_MAX_CHARS）。手順の順の前から入れ、超えた分は数だけ返す。切れた 1 件を途中で切らない（字の意味が変わるため）。
    - 字を写した別のファイルは作らない。記録を取り下げると字も消える（talk_log.drop_for_record）ので、写しがあると消し残る。
    """
    from . import talk_log  # 使う時に読む（hypotheses の読み方と同じ。輪の置き場を読むだけの命令で、話す口の部品まで先に読まない）

    rec = record(rid)
    said = [t for t in talk_log.kufu(rec["source_id"], rid, shared_only=True) if t["when"] != talk_log.WHEN["think"]]
    items, used = [], 0
    for t in said:
        used += len(t["text"])
        if used > TALK_MAX_CHARS:
            break
        items.append({k: t[k] for k in TALK_FIELDS})
    return {"label": TALK_LABEL, "items": items, "omitted": len(said) - len(items)}


def material(rid):
    """輪の解釈と案の材料（記録・人の説明・作った人が話した事）。鍵のある道（api/loop_agents）も鍵の無い道（material の命令）も、ここから読む。
    同じ材料を両方の道に渡すのは、鍵の有無で、人が見る物と Claude が見る物が食い違わないため。"""
    return {"record": record(rid), "explanation": explanation(rid), "maker_talk": maker_talk(rid)}


def next_target(source_id, hid, sheet_set=None):
    """次の版を足す仮説。自分の紙（OWN-n）の記録から作る次の版は、たたき台へ向ける（根拠は OWN-n の記録のまま）。
    なぜ: 型紙は玩具ごとに 1 枚（J-032）で、最新版が次の人の型紙になる。OWN-n に版を足しても紙は刷られず、次の人にも届かない。ループ1 を通った人の工夫がループ2（型紙の改善）に届くように。
    型紙なしの紙（寸法の無い案）の記録は向く先が無いので、そのまま返す。組の報告に数えない記録で、たたき台の寸法を変えられる形は筋が通らないため。欄も節の数も出ず、受け口と床が断る。
    画面の欄・節の数・端末の propose・Claude の道は、ここ 1 か所を読む。
    sheet_set は記録の紙の組。その組の紙の押し方（雛形の HYP_KEY）が今のたたき台の形と違う記録は、向く先が無い（None）。
    なぜ: 組を上げてたたき台の形が変わると、同じ仮説の id の前の紙（御来迎の R-0002 は goraigo-v7 の柄を差す形の H-C）からの観察で、
    今の形（goraigo-v14 の割り箸で押し上げる H-C）の版を作ってしまう。窓口が本人の委任で決めた案 A（2026-11-06）: 形の違う記録には
    次の版の欄を出さず、待つ報告にも数えない。組を持たない記録と、同じ形の組の記録は今までどおり"""
    from .hypotheses import sheet_of

    if not str(hid).startswith("OWN-") or not (_hypothesis(source_id, hid) or {}).get("params"):
        if sheet_set and not _same_form(source_id, hid, sheet_set):
            return None
        return hid
    return sheet_of(source_id)["id"]


def _same_form(source_id, hid, sheet_set):
    """記録の組の紙（sheet_set の寸法）の押し方が、今のたたき台の紙の押し方と同じか。押し方の名の無い雛形は同じと見る。"""
    from .compose import TEMPLATES
    from .hypotheses import ROOT, load, params_for, sheet_of

    tpl = TEMPLATES[load(source_id).get("template", "slider_fan")]
    # 組の寸法は記録を直に読む（load は今の組の寸法を params に重ねるので、前の組の紙の寸法が読めない）。人が採った仮説は記録に無いので load の物
    path = ROOT / "data/hypotheses" / f"{source_id}.json"
    raw = json.loads(path.read_text(encoding="utf-8"))["hypotheses"] if path.exists() else []
    key, h = getattr(tpl, "HYP_KEY", None), next((x for x in raw if x["id"] == hid), None) or _hypothesis(source_id, hid)
    if not key or not h:
        return True
    then = {**tpl.DEFAULTS, **(params_for(h, sheet_set) or {})}
    now = {**tpl.DEFAULTS, **(sheet_of(source_id).get("params") or {})}
    return then.get(key) == now.get(key)


def material_text(rid):
    """鍵の無い道で、人（作る側）が解釈と変更を書く前に読む材料の文。人の説明と、話した字を、別の仕切りで出す。"""
    m = material(rid)
    rec, told, talk = m["record"], m["explanation"], m["maker_talk"]
    lines = [f"記録 {rid}（{rec['source_id']} の {rec['hypothesis_id']} 版 {rec.get('sheet_version', 1)}）: {rec.get('result', '')}"
             + (f" ／ {rec['note']}" if rec.get("note") else "")]
    lines += ["", "人の説明と次の思いつき:"]
    lines += [f"  説明: {told['text']}", f"  次の思いつき: {told['next_idea']}"] if told else ["  （まだ無い。先に explain で残す）"]
    lines += ["", f"{talk['label']}:"]
    for t in talk["items"]:
        where = f"手順 {t['step']}" if t["step"] else ("上げた後" if t["when"] == "made" else "作りながら")
        lines.append(f"  {where}: {t['text']}")
    if talk["omitted"]:
        lines.append(f"  （ほかに {talk['omitted']} 件。字の数の上限で入れていない。読むのは作る側の頁）")
    from . import talk_log

    # 隠した字は出さず、数だけ知らせる。全部隠した記録を「字は無い」と読ませないため。
    hidden = sum(1 for t in talk_log.kufu(rec["source_id"], rid) if not t["share"] and t["when"] != talk_log.WHEN["think"])
    if hidden:
        lines.append(f"  （作る側が隠した字が {hidden} 件ある。ここには出さない。読むのは作る側の頁）")
    elif not talk["items"]:
        lines.append("  （この記録に結んだ字は無い）")
    target = next_target(rec["source_id"], rec["hypothesis_id"], rec.get("sheet_set"))
    if target is None:
        lines += ["", "この記録の紙は今のたたき台と押し方が違うので、次の版には使わない"]
    elif target != rec["hypothesis_id"]:
        lines += ["", f"次の版は {target} に足します（根拠はこの記録）"]
    lines += ["", f"読んだら、confirm {rid} --by 名前 --text 解釈 と propose {rid} --change 寸法=値 --why 理由 で書きます"]
    return "\n".join(lines)


def save_explanation(rid, by, text, next_idea):
    """人の説明と次の思いつき。「わからない」でも書けばよく、中身は評価しない。
    書いた人は書かなくてもよい（本人の決定 11-06。手帖の「名前や連絡先は書かないでください」と合わせる）。空の時は空のまま残す。"""
    record(rid)
    if not (text or "").strip() or not (next_idea or "").strip():
        return [Failure("F9.human", rid, "説明と次の思いつきの両方が要る（わからない、と書いてもよい）")]
    long = too_long([("説明", text), ("次の思いつき", next_idea)])
    if long:
        return [Failure("F3.result", rid, message) for _, message in long]
    failures = [Failure("F3.result", rid, f.message) for f in check_pii({"body": f"{text} {next_idea}"})]
    if failures:
        return failures
    _write(folder() / f"explanation-{rid}.json", {"record_id": rid, "text": text.strip(), "next_idea": next_idea.strip(), "by": (by or "").strip(), "at": _now()})
    return []


def save_interpretation_draft(rid, content, trace=None):
    record(rid)
    _write(interp_path(rid), {"record_id": rid, "status": "pending_human", "content": content, "drafted_by": "claude", "trace": trace})


def check_confirm(rid, by, content=None):
    """人の確定の床。書く前に見られるよう、確定そのものと分ける（#158）。"""
    record(rid)
    if not by or not by.strip():
        return [Failure("F9.human", rid, "確定した人の名前が無い")]
    if content is None and "content" not in (interpretation(rid) or {}):
        return [Failure("F9.human", rid, "解釈の案が無く、人の解釈も無い")]
    return []


@exclusive
def confirm_interpretation(rid, by, content=None):
    """人の確定（H6）。案が無くても、人が書いた解釈で確定できる。"""
    failures = check_confirm(rid, by, content)
    if failures:
        return failures
    current = interpretation(rid) or {"record_id": rid, "drafted_by": "human"}
    if content is not None:
        current["content"] = content
        current["edited_by_human"] = current.get("drafted_by") == "claude"
    current.update(status="confirmed", confirmed_by=by.strip(), confirmed_at=_now())
    _write(interp_path(rid), current)
    return []


def confirmed_records(source_id, known=None):
    """前例として引ける記録。人が解釈を確定した物だけ。動画の受け口の記録は外す（AI の道具に、上げた人の文を渡さない）。"""
    from .records import UPLOADED

    out = []
    d = base() / "records"
    for p in sorted(d.glob("R-*.json")):
        if (d / "withdrawn" / p.name).exists():
            continue
        rec = store.read_json_or_skip(p)
        if rec is not None and rec.get("source_id") == source_id and rec.get("via") != UPLOADED and confirmed(rec["id"]):
            out.append({**rec, "interpretation": interpretation(rec["id"])["content"]})
    return out


def known_ids():
    ids = {p.stem for p in (base() / "records").glob("R-*.json") if not (base() / "records/withdrawn" / p.name).exists()}
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
    v = store.read_json_or_skip(folder() / f"version-{source_id}-{hid}-{version}.json")
    if v is None:
        return None, None
    return v["params"], v


def adopted_versions(source_id, hid):
    """人が採った版の番号（版 1 は入らない）。"""
    # 読めない版は数えない。数えると、一番新しい版の寸法が取れず、頁と次の版が止まる。
    return sorted(int(p.stem.rsplit("-", 1)[1]) for p in folder().glob(f"version-{source_id}-{hid}-*.json") if store.read_json_or_skip(p) is not None)


def latest_version(source_id, hid):
    return max(adopted_versions(source_id, hid), default=1)


def check_proposal(p, source, will_confirm=(), need_why=True):
    """提案の検査。Claude にも人の手書きにも同じ床を当てる。will_confirm は、通った時に同じ操作で確定する記録（#158）。
    need_why は変更ごとの理由を求めるか。採った新しい案を版にする時だけ外す（案の字は版の記録の new_case に残す。_new_as_changes）。"""
    from .hypotheses import sheet_of

    out = []
    sid = source["source_id"]
    template = _template(sid)
    records = p.get("record_ids") or []
    if not records:
        out.append(Failure("F4.evidence", "record_ids", "根拠の記録 ID が無い"))
    for rid in records:
        if not (base() / "records" / f"{rid}.json").exists():
            out.append(Failure("F8.references", rid, "その記録は実在しない"))
        elif record(rid).get("source_id") != sid:
            # 別の玩具の記録は根拠にしない。仮説 ID（H-A など）は玩具ごとに振るので、偶然そろうと別の玩具の試行で寸法が変わる（レビュー指摘）。
            out.append(Failure("F8.references", rid, f"出典 {record(rid).get('source_id')} の記録で、提案の出典 {sid} と違う"))
        elif not confirmed(rid) and rid not in will_confirm:
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
        elif hid != sheet_of(sid)["id"]:
            # 型紙は玩具ごとに 1 枚で、最新版が次の人の型紙（J-032）。ほかの仮説に版を足しても次の人に届かず、必須 2 種では紙も刷れない。
            out.append(Failure("F7.revision", str(hid), f"次の版はたたき台（{sheet_of(sid)['id']}）にだけ足す"))
        else:
            current, _ = version_params(sid, hid, latest_version(sid, hid))
            merged = dict(current)
            before = values(template, current)
            ok = allowed(template, {**TEMPLATES_DEFAULT(template), **current})
            for c in changes:
                if c.get("param") not in ok:
                    out.append(Failure("F7.revision", str(c.get("param")), "変えてよい寸法の外"))
                    continue
                if need_why and not c.get("why", "").strip():
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
    # 順位は扱わない（J-025）。古い形の提案や手書きで混ざっても、黙って捨てず落として知らせる。
    if p.get("ranking"):
        out.append(Failure("F4.evidence", "ranking", "仮説の順位は扱わない。記録は次に試す物の提案に使う（J-025）"))
    nxt = p.get("next_to_try") or {}
    if nxt.get("hypothesis_id") and _hypothesis(sid, nxt["hypothesis_id"]) is None:
        out.append(Failure("F8.references", str(nxt["hypothesis_id"]), "次に試す仮説が実在しない"))
    return out


def TEMPLATES_DEFAULT(template):
    from .compose import TEMPLATES

    return TEMPLATES[template].DEFAULTS


def _trial_values(lo, hi, now):
    """1 つの寸法で試す値を、今の値から近い順に返す。通る値はたいてい今の値の近くにあるので、近くを細かく、遠くは粗く見る
    （全部の玩具の版 1 と動かした後の版で、400 値の総当たりと同じ答えになった）。整数の寸法のために、近くの整数と幅の両端も入れる。"""
    span = hi - lo
    near = [now + sign * span * step for step in (0.00125, 0.0025, 0.005, 0.01, 0.02, 0.05) for sign in (1, -1)]
    whole = [round(now) + d for d in (-3, -2, -1, 1, 2, 3)]
    far = [lo + span * i / 20 for i in range(21)]
    values = {round(v, 4) for v in near + whole + far + [round(v) for v in far] if lo <= v <= hi and v != now}
    # 画面の口（play_server の次の版）と同じに、整数で言える値は整数で渡す。
    return [int(v) if float(v).is_integer() else v for v in sorted(values, key=lambda v: (abs(v - now), v))]


def allowed(template, params):
    """次の版で変えてよい寸法。表（metrics.ALLOWED）から、その形に効かない寸法（雛形の unused_params）を外す。"""
    from .compose import TEMPLATES

    unused = getattr(TEMPLATES[template], "unused_params", lambda p: set())(params)
    return ALLOWED[template] - unused


@functools.lru_cache(maxsize=256)
def _movable(sid, current_json):
    """今の寸法（json の字）で、1 つ変えて通る値がある寸法と、その値の 1 つ。寸法が同じなら答えも同じなので、1 度だけ検査する。
    範囲と物理の床だけで決める。配置まで組むと、棒の玩具では 1 回 0.85 秒かかり、頁の最初の表示が 9 秒止まった。物理で通った値が配置で落ちる寸法は、
    全部の玩具の版 1 と動かした後の版で見て無かった。もし出ても、断りの文が理由を言うので、欄が止まる事はない。"""
    from .compose import TEMPLATES

    template = _template(sid)
    tpl, now = TEMPLATES[template], {**TEMPLATES[template].DEFAULTS, **json.loads(current_json)}
    found = {}
    for k in sorted(allowed(template, now)):
        for v in _trial_values(*tpl.RANGES[k], now[k]):
            trial = {**now, k: v}
            if not (tpl.check_range(trial) or tpl.check_physics(trial)):
                found[k] = v
                break
    return found


def movable_params(sid, hid):
    """次の版の欄（寸法を 1 つ変える形）に出す寸法を、通る値の 1 つと一緒に返す。今の版の寸法で決める。
    なぜ固定の表にしないか: 動かせない寸法は型の拘束で決まり、ほかの寸法を変えると通る幅が開く。例えば御来迎の押し上げる量は、扇を隠す床と内筒を収める床に
    挟まれて今の寸法だと 69 ちょうどしか通らないが、扇を低くすると動かせる。Claude の案は寸法を同時に変えられるので、この絞りは掛けない（ALLOWED のまま）。"""
    current, _ = version_params(sid, hid, latest_version(sid, hid))
    return _movable(sid, json.dumps(current, ensure_ascii=False, sort_keys=True))


def save_proposal(proposal, source, drafted_by):
    from .hypotheses import sheet_of

    failures = check_proposal(proposal, source)
    if failures:
        return None, failures
    sid = source["source_id"]
    # 案を作った時のたたき台の版を持つ。採る時に、この版からの差だけを今の版に重ねるため（_new_as_changes）。
    based = proposal.get("based_on_version") or latest_version(sid, sheet_of(sid)["id"])
    return save_numbered("proposal", "P", lambda pid: {**proposal, "based_on_version": based, "id": pid, "source_id": sid, "status": "pending_human", "drafted_by": drafted_by, "drafted_at": _now()}), []


def _next_params(sid, hid, changes):
    """次の版の番号と寸法。"""
    current, _ = version_params(sid, hid, latest_version(sid, hid))
    return latest_version(sid, hid) + 1, {**current, **{c["param"]: c["to"] for c in changes}}


def _write_version(p, pid, by, hid, changes, new_case=None):
    """採った変更を次の版の記録にして、版の番号を返す。new_case は版にした案の字で、頁には出さない（変更の理由の欄は頁の輪の節に出る）。"""
    sid = p["source_id"]
    version, params = _next_params(sid, hid, changes)
    _write(folder() / f"version-{sid}-{hid}-{version}.json", {"source_id": sid, "hypothesis_id": hid, "version": version, "params": params, "changes": changes, "record_ids": p["record_ids"], "proposal": pid, "adopted_by": by.strip(), "adopted_at": _now(), **({"new_case": new_case} if new_case else {})})
    return version


def _new_as_changes(sid, hid, new, based_on):
    """採った新しい案が、たたき台の寸法の差で言えるなら、次の版の変更にして返す。言えなければ空（J-032）。

    なぜ版にするか: 型紙は玩具ごとに 1 枚で、最新版が次の人の型紙（本人の方針 11-05）。別の仮説として控えに入れると、次の人に届かない。
    差は案を作った時の版（based_on）から見て、今の版に重ねる。案は全部の寸法を書くので、今の版と比べると、案が言っていない前の版の直しまで戻してしまう。
    案を作った後に今の版で変わった寸法に触る案は、後の直しを黙って上書きしないよう、版にしない。雛形の違う案は、寸法を重ねる版の形に乗らない。
    今の版と差が無い案は読みだけが違う案で、版にならない。変えてよい寸法の外（形の違い）と紙に乗らない差は、呼ぶ側の check_proposal が落とす。
    理由の欄は空にする: 頁の輪の節に出る欄で、案の字は Claude の字なので頁に出さない（new_case に残す）。
    """
    template = _template(sid)
    defaults = TEMPLATES_DEFAULT(template)
    then, _ = version_params(sid, hid, based_on)
    params = new.get("params")
    if new.get("template", new.get("template_id", template)) != template or then is None or not isinstance(params, dict):
        return []
    current, _ = version_params(sid, hid, latest_version(sid, hid))
    then, now = {**defaults, **then}, {**defaults, **current}
    said = {k: v for k, v in params.items() if then.get(k) != v}
    if any(now.get(k) != then.get(k) and now.get(k) != v for k, v in said.items()):
        return []
    return [{"param": k, "to": v, "why": ""} for k, v in sorted(said.items()) if now.get(k) != v]


@exclusive
def adopt(pid, by, accept_params=(), accept_new=False, source=None):
    """人の採否（H7）。採った物だけが版と作る側の控えに入る。次に試す物の提案は、採っても並びを変えない。
    新しい案（accept_new）は道を閉じず、札にも出さない（J-032）: 寸法の差で言える案はたたき台の次の版にし、言えない案と紙に乗らない案は
    作る側の控え（extra-hypotheses）に残す。人が採った案を捨てないため。たたき台は替えない（替えるのは本人が決めた時に記録の欄 sheet を直す）。"""
    from .hypotheses import sheet_of

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
    # 渡された出典が提案の出典と違えば使わない。命令の --source の既定は御来迎なので、虎の提案を --source なしで採ると
    # 御来迎の雛形で虎の寸法を検査していた（レビュー指摘［中］）。提案に書いた出典が正。
    if not source or source.get("source_id") != sid:
        source = json.loads((ROOT / "data/sources" / f"{sid}.json").read_text(encoding="utf-8"))
    chosen = [c for c in p.get("changes", []) if c["param"] in accept_params]
    failures = check_proposal({**p, "changes": chosen}, source)
    if failures:
        return None, failures
    made = {}
    if chosen:
        made["version"] = _write_version(p, pid, by, p["hypothesis_id"], chosen)
    sheet = sheet_of(sid)["id"]
    # 番号を持たない前の形の案は版 1 の時の案（前は Claude に版 1 の寸法だけを渡していた）。
    as_version = _new_as_changes(sid, sheet, p["new_hypothesis"], p.get("based_on_version", 1)) if accept_new and p.get("new_hypothesis") else []
    # 紙に乗らない差は版にしない（版の記録だけ残り、紙が刷れない形を作らない）。この時は下の控えに入る。
    if as_version and not check_proposal({"record_ids": p["record_ids"], "hypothesis_id": sheet, "changes": as_version}, source, need_why=False):
        new_case = {k: p["new_hypothesis"][k] for k in ("name", "how_it_moves")}
        made["version"] = made["new_hypothesis_as_version"] = _write_version(p, pid, by, sheet, as_version, new_case)
    elif accept_new and p.get("new_hypothesis"):
        extras_path = folder() / f"extra-hypotheses-{sid}.json"
        extras = _read(extras_path) or []
        new = {**p["new_hypothesis"], "id": f"H-N{len(extras) + 1}", "status": "untested", "evidence": p["new_hypothesis"].get("evidence", []) + [{"kind": "record", "where": rid, "what": "試した記録", "certainty": "記録"} for rid in p["record_ids"]], "proposal": pid, "adopted_by": by.strip()}
        extras.append(new)
        _write(extras_path, extras)
        made["new_hypothesis"] = new["id"]
    p.update(status="decided", decided_by=by.strip(), decided_at=_now(), accepted=made, accepted_params=list(accept_params))
    _write(path, p)
    return made, []


def _print_into(sheet_dir, stem, printer):
    """紙を一時の場所で刷り、全部できた時だけ置き場へ移す（#158）。途中で落ちても、半端な紙を正しい名前で残さない。
    読みに来た人にも書きかけを渡さない（#301）。"""
    sheet_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=sheet_dir, prefix=".tmp-") as tmp:
        rc = printer(f"{tmp}/{stem}")
        if rc:
            return rc
        # PDF があれば刷ってあると読むので、絵の後に置く。版の PDF（web/toy.py の versions_of）は一番最後。
        for p in sorted(pathlib.Path(tmp).iterdir(), key=lambda p: (p.suffix == ".pdf", p.name == f"{stem}.pdf")):
            p.replace(sheet_dir / p.name)
    return 0


def print_version(sid, hid, version, sheet_dir, pending=None):
    """版の紙の組を刷る。"""
    from . import hypotheses

    return _print_into(sheet_dir, f"{hid}_v{version}", lambda out: hypotheses.print_sheet(sid, hid, out, version, pending=pending))


def print_after(sid, hid, version, sheet_dir):
    """その版の試した後の紙だけを刷る（#320、hypotheses.print_after）。"""
    from . import hypotheses

    return _print_into(sheet_dir, f"{hid}_v{version}", lambda out: hypotheses.print_after(sid, hid, out))


def print_own(sid, oid, sheet_dir):
    """自分の仮説の紙を刷る。"""
    from . import hypotheses

    return _print_into(sheet_dir, f"{oid}_v1", lambda out: hypotheses.print_own(sid, oid, out))


@exclusive
def next_version(rid, by, content, change, source, sheet_dir):
    """画面の「次の版を作る」の 1 操作: 解釈の確定 → 変更の案 → 人の採用 → 刷る → 型紙の確定（#158）。

    途中で落ちると前の分だけが残り、確定した解釈が根拠に使え、版の記録だけが残ると同じ値で送り直せなくなる。
    そこで、書く前に床を全部見て、刷るのも先に済ませ、通った時だけ書く。紙を先に置くのは、版の記録があって紙が無い形を作らないため。
    消して戻す形は、消し残しの形が増えるので採らない。排他の中で刷るので、その数秒は同じ置き場の書き込みが待つ。
    """
    from .compose import TEMPLATES

    failures = check_confirm(rid, by, content)
    if failures:
        return None, failures
    rec = record(rid)
    sid, hid = rec["source_id"], next_target(rec["source_id"], rec["hypothesis_id"], rec.get("sheet_set"))
    proposal = {"record_ids": [rid], "hypothesis_id": hid, "changes": [change]}
    failures = check_proposal(proposal, source, will_confirm=[rid])
    if failures:
        return None, failures
    version, params = _next_params(sid, hid, proposal["changes"])
    if print_version(sid, hid, version, sheet_dir, pending={"params": params, "changes": proposal["changes"], "record_ids": [rid]}):
        return None, [Failure("F7.revision", f"{hid} 版 {version}", f"版 {version} の紙を作れませんでした（検査に落ちた）")]
    confirm_interpretation(rid, by, content)
    pid, failures = save_proposal(proposal, source, "human")
    if failures:
        return None, failures
    made, failures = adopt(pid, by, accept_params=[change.get("param")], source=source)
    if failures:
        return None, failures
    confirm_sheet(sid, hid, made["version"], by, TEMPLATES[_template(sid)].SHEET_SET)
    return made["version"], []


def save_template_change(record_ids, sheet_set, commit, changes, by, decided_in=""):
    """雛形の直し（本人の決定 U-32、11-04）。寸法の数値では表せない直し（部品の形・組み方の順など）を、台帳でつなぐ記録。

    寸法の版（version-*.json）は数値を変える形しか持てず、11-04 の試行から出た v8 の直し（溝の形、扇の足、土台、組み方の順）が
    乗らなかった。そこで「記録 → 人の説明 → 次の版 → 人が採る」の次の版の所に、この種類を置く。
    床: 根拠の記録が実在する（F8）。どの記録にも人の説明が先にある（F9.human、J-013）。採った人・刷った組・commit・直した中身が要る。
    数値の向きの検査（F7）は当てない。式の無い直しなので、印として kind を template_change にする。
    """
    out = []
    if not record_ids:
        out.append(Failure("F4.evidence", "record_ids", "根拠の記録 ID が要る"))
    for rid in record_ids:
        try:
            record(rid)
        except ValueError as e:
            out.append(Failure("F8.references", rid, str(e)))
            continue
        if explanation(rid) is None:
            out.append(Failure("F9.human", rid, "人の説明が先に要る"))
    if not by or not by.strip():
        out.append(Failure("F9.human", "by", "採った人の名前が無い"))
    for name, v in (("sheet_set", sheet_set), ("commit", commit)):
        if not (v or "").strip():
            out.append(Failure("F7.revision", name, f"{name} が無い"))
    if not changes or not all(str(c).strip() for c in changes):
        out.append(Failure("F7.revision", "changes", "直した中身が要る"))
    if out:
        return None, out
    return save_numbered("template-change", "T", lambda tid: {"id": tid, "kind": "template_change", "record_ids": list(record_ids), "sheet_set": sheet_set.strip(),
                                                              "commit": commit.strip(), "changes": list(changes), "adopted_by": by.strip(), "decided_in": decided_in, "at": _now()}), []


@exclusive
def confirm_sheet(source_id, hid, version, by, sheet_set):
    """型紙の確定（f09）: 人が刷ると決めた仮説と版を、刷った組と一緒に台帳に残す。F9.human の「確定の記録は未実装」を埋める。
    刷る操作そのものが人の選び（仮説を選んで刷る）なので、その時に 1 件ずつ足す。中身は評価しない。"""
    if not (by or "").strip():
        return [Failure("F9.human", f"{hid} 版 {version}", "確定した人が無い")]
    path = folder() / f"sheet-confirm-{source_id}-{hid}-v{version}.json"
    rec = _read(path) or {"source_id": source_id, "hypothesis_id": hid, "version": version, "confirmations": []}
    rec["confirmations"].append({"by": by.strip(), "sheet_set": sheet_set, "at": _now()})
    _write(path, rec)
    return []


def sheet_confirmations(source_id):
    from .hypotheses import files_of  # 名前の前方一致でほかの玩具の確定を拾わない（#147）

    return [_read(p) for p in files_of(folder(), "sheet-confirm", source_id)]


def template_changes():
    return [t for p in sorted(folder().glob("template-change-*.json")) if (t := store.read_json_or_skip(p)) is not None]


def overlay(data):
    """人が採った新しい仮説を、一覧に重ねる。元の仮説の記録は書き換えない。

    前に採った順位の記録（ranking-*.json）が手元に残っていても重ねない。順位は持たない（J-025）。
    """
    sid = data["source_id"]
    extras = store.read_json_or_skip(folder() / f"extra-hypotheses-{sid}.json", list) or []
    data["hypotheses"] = data["hypotheses"] + extras
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
    s = sub.add_parser("material", help="鍵の無い道で、解釈と変更を書く前に読む材料（記録・人の説明・作った人が話した事）")
    s.add_argument("record")
    s = sub.add_parser("show")
    s.add_argument("proposal")
    s = sub.add_parser("adopt", help="提案を人が採る")
    s.add_argument("proposal")
    s.add_argument("--by", required=True)
    s.add_argument("--param", action="append", default=[])
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
                pid, failures = save_proposal({"record_ids": [args.record], "hypothesis_id": args.hypothesis or next_target(source["source_id"], record(args.record)["hypothesis_id"], record(args.record).get("sheet_set")), "changes": changes}, source, "human")
            else:
                from api.loop_agents import draft_proposal

                pid, failures = draft_proposal(args.record, source)
            if not failures:
                print(f"{pid} を作りました。show で見て adopt で採ります")
        elif args.cmd == "material":
            # 読むだけで何も書かない。字を写したファイルを作らないのは maker_talk の芯と同じ（取り下げで消し残さない）。
            print(material_text(args.record))
        elif args.cmd == "show":
            print(json.dumps(_read(folder() / f"proposal-{args.proposal[2:]}.json"), ensure_ascii=False, indent=2))
        else:
            if not _human_confirm(args.proposal, "採用"):
                failures = [Failure("F9.human", args.proposal, "端末での人の確認が無い")]
            else:
                made, failures = adopt(args.proposal, args.by, args.param, args.new, source)
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
