"""エンジンへ渡す束（Issue #278・#275 の段取り 5）。サイトに残っている作る過程の記録を、型紙エンジン（paper-to-toy）が読める
JSON 1 つに束ねる。本人の言葉（2026-11-05）: 作る過程の記録を「フィードバックとして型紙を改善するほか、型紙を生成するエンジンごと改善する」。

判断の芯:
- ここは読むだけ。記録の形・頁・型紙には触らない。束ねる単位は「雛形の id × 刷った組」: エンジンの側は、型紙 1 枚でなく、
  雛形から刷る全部の紙に効く直し（雛形・部品・生成の決まり）を見るため。玩具と仮説ごとの集計は making_log.summary が持つ。
- 束から案を起こすのも、採るのも、ここではしない（web/kaizen.py の頭の受け持ちのとおり、エンジンの側の omochae.engine_loop）。
  効いたかの判定もしない（本人の決まり: 機械は断定せず、数を並べて人が読む）。だから束に入れるのは件数と幅と文だけで、
  割合・平均・順位を入れない。
- 個人の情報は入口で落とす（本人の決まり）。記録と質問は残す時に連絡先の形の床を通っているが、床より前の記録や、手で置いた
  記録もあり得るので、出す時にもう一度、同じ床（contrib.check_pii）を当てる。当たった文は入れず、落とした数だけを入れる。
  束の欄は決めた物だけ（下の TOP_KEYS・GROUP_KEYS・TEXT_KEYS。エンジンの入口が同じ一覧で確かめ、外の欄は束ごと断る）。
  **入れない物**: 名前・連絡先・その場限りの印の値（人の数だけを入れる）・IP・写真・動画・声・分より細かい時刻・採った人の名前。
  名前は形では見分けられない。だから束は git の外に書き、エンジンの側でも人が読んでから使う。
- 試した記録の刷った組は、記録が持つ値か、刷った時の型紙の確定の記録から引く。分からない時は空（不明）の群に分ける。
  今の組に数えると、直す前の紙の記録が、直した後の紙の数に混ざる。
- メモ（note）は束に入れない。記録を入れた人の覚え書きで、作った人の言葉とは限らないため。
- 束の上の段に、群に出てくる雛形の「今の刷った組」を書く（current_sets。Issue #309）。エンジンの repo の雛形は組の名を持たないので、
  前の組の紙の記録から起きた案（もう直っている事がある）を、読む人が見分けられない。ここは今の組を並べるだけで、前の組の記録を
  束から外しはしない（直っていない困り事まで消え、直す前と後を並べて読めなくなる）。
終了: 0 = できた / 4 = できない（書く先が決まりの外など）。
"""
import argparse
import json
import pathlib
import re
import sys
from datetime import datetime, timedelta, timezone

from . import loop, making_log, records
from .contrib import check_pii
from .hypotheses import ROOT

# 束の形。エンジンの omochae.engine_loop（paper-to-toy の #63）と同じ一覧で、片方を変える時は両方を変える（tests/test_engine_bundle.py が鍵の一致を見る）。
SCHEMA = "omochae.making-bundle/1"
FROM = "utsushi"
TOP_KEYS = ("schema", "exported_at", "from", "dropped_pii", "current_sets", "groups")
GROUP_KEYS = ("template", "sheet_set", "reports", "results", "moved_word", "not_moved_word", "stuck_steps", "quit_steps",
              "minutes", "measures", "record_ids", "texts")
TEXT_KEYS = ("kind", "step", "text", "count")
# 文の種類: 止まった所・直した点（工夫）・思いつき（工夫）・感想・聞く口の質問・試した記録への人の説明。
TEXT_KINDS = ("stuck", "fix", "idea", "impression", "question", "explain")
MAX_TEXT = 300  # エンジンの入口の、文 1 つの上限。長い感想は頭だけを入れる（全文は記録の番号から人が読む）
MAX_STEP = 40
NAME = re.compile(r"[A-Za-z0-9_.-]{1,80}")  # 雛形の id と刷った組の形（エンジンの入口と同じ）
MEASURE = re.compile(r"[a-z_]{1,30}")
UNSURE = "わからない"  # 動いた側にも動かない側にも数えない札（records の頭の決まり）


def _clean(text):
    """文を 1 行にして、上限で切る。空なら None。"""
    text = " ".join(str(text or "").split())
    if not text:
        return None
    return text if len(text) <= MAX_TEXT else text[:MAX_TEXT - 1] + "…"


def _name(value):
    """雛形の id・刷った組を、形だけ確かめて返す。形の外は空（不明）にする（自由な文をこの欄で運ばせない）。"""
    return value if isinstance(value, str) and NAME.fullmatch(value) else ""


def _sheet_set_of(rec):
    """その記録の紙の刷った組。記録が持てばそれ。無ければ、記録の時刻までに刷った型紙の確定の記録のうち、一番新しい物。
    どちらも無ければ空（不明）。今の雛形の組は使わない（直した後の組に、直す前の記録を数えないため）。"""
    if _name(rec.get("sheet_set")):
        return rec["sheet_set"]
    at = str(rec.get("recorded_at") or "")
    found = ""
    for conf in loop.sheet_confirmations(rec.get("source_id")):
        if conf and conf.get("hypothesis_id") == rec.get("hypothesis_id") and conf.get("version") == rec.get("sheet_version", 1):
            for c in conf.get("confirmations", []):
                if str(c.get("at") or "") <= at:
                    found = _name(c.get("sheet_set")) or found
    return found


def _group(groups, template, sheet_set):
    key = (_name(template), _name(sheet_set))
    if key not in groups:
        groups[key] = {"template": key[0], "sheet_set": key[1], "reports": 0, "results": {}, "moved_word": "", "not_moved_word": "",
                       "stuck": {}, "reached": {}, "finished": set(), "minutes": [], "measures": {}, "record_ids": [], "texts": {}}
    return groups[key]


def _span(values):
    """数の幅 [最小, 最大, 件数]。無ければ None。平均は出さない（少ない件数の平均は、確かな値のように見える）。"""
    return [min(values), max(values), len(values)] if values else None


def build():
    """束を作って返す（dict）。書かない。"""
    from .compose import TEMPLATES

    groups, dropped = {}, 0

    def say(g, kind, text, step=None):
        """文を 1 つ足す。連絡先の形があれば入れず、落とした数だけ数える。同じ文（同じ種類・同じ段）は回数にまとめる。"""
        nonlocal dropped
        text = _clean(text)
        if text is None:
            return
        if check_pii({"body": text}):
            dropped += 1
            return
        step = step if isinstance(step, int) and not isinstance(step, bool) and 1 <= step <= MAX_STEP else None
        g["texts"][(kind, step, text)] = g["texts"].get((kind, step, text), 0) + 1

    # 試した記録: 動きの札・測った値・止まった所・直した点・思いつき・感想と、人の説明。
    for r in records.all_records():
        template = making_log._engine(r.get("source_id"), r.get("hypothesis_id"))[0]
        g = _group(groups, template, _sheet_set_of(r))
        g["reports"] += 1
        g["record_ids"].append(r["id"])
        tpl = TEMPLATES.get(template)
        if tpl is not None:
            # 札の言葉は雛形が持つ物だけを数える（自由な文を札の欄で運ばせない）。先頭が動いた側。動かない側は、「わからない」を除いた最後の札
            # （「少し動いた」のような間の札を持つ雛形があるので、2 番目とは決めない）。「わからない」はどちらにも数えない。
            # 前の札の記録は今の札に読み替える（#146）。エンジンは moved_word と not_moved_word で数を引くので、前の札のままだと数から落ちる。
            # 手で置かれた記録の札は字とは限らないので、辞書を直に引かない。
            word, old = r.get("result"), getattr(tpl, "OLD_RESULTS", {})
            word = old[word] if word in tuple(old) else word
            if word in tpl.RESULTS:
                g["results"][word] = g["results"].get(word, 0) + 1
            sure = [w for w in tpl.RESULTS if w != UNSURE]
            g["moved_word"], g["not_moved_word"] = sure[0], (sure[-1] if len(sure) > 1 else "")
        for k, v in r.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool) and k != "sheet_version" and MEASURE.fullmatch(k):
                (g["minutes"] if k == "minutes_to_try" else g["measures"].setdefault(k, [])).append(v)
        answers = r.get("answers") or {}
        say(g, "stuck", answers.get("stuck"))
        say(g, "idea", answers.get("what_if"))
        for idea in r.get("ideas") or []:
            say(g, "idea", idea)
        say(g, "impression", r.get("impression"))
        for f in r.get("fixes") or []:
            if isinstance(f, dict) and all(str(f.get(k, "")).strip() for k in ("part", "change", "outcome")):
                say(g, "fix", f'{f["part"]} / {f["change"]} / {f["outcome"]}')
        told = loop.explanation(r["id"]) or {}  # 人が書いた説明だけ（Claude の読みは入れない）
        say(g, "explain", told.get("text"))
        say(g, "idea", told.get("next_idea"))

    # 手順の進み: 止まったの札と、途中でやめた段。人は、その場限りの印で数えるだけで、印の値は束に入れない。
    for e in making_log.steps():
        step = e.get("step")
        if not (isinstance(step, int) and not isinstance(step, bool) and 1 <= step <= MAX_STEP):
            continue
        g = _group(groups, e.get("template"), e.get("sheet_set"))
        who = making_log.clean_who(e.get("who"))
        if e.get("event") == "stuck":
            slot = g["stuck"].setdefault(step, {"taps": 0, "who": set()})
            slot["taps"] += 1
            if who:
                slot["who"].add(who)
        if who:
            key = (who, e.get("hypothesis_id", ""))  # 同じ人が別の仮説の紙を作る事がある（making_log.summary と同じ数え方）
            if e.get("event") == "done":
                g["finished"].add(key)
            g["reached"][key] = min(MAX_STEP, max(g["reached"].get(key, 0), step + (1 if e.get("event") == "next" else 0)))

    # 聞く口の質問: 手順の番号つき。残す時に連絡先の形で落ちた物は、落とした数に足す。
    for a in making_log.asks():
        g = _group(groups, a.get("template"), a.get("sheet_set"))
        if a.get("dropped"):
            dropped += 1
            continue
        say(g, "question", a.get("question"), a.get("step"))

    out = []
    for key in sorted(groups):
        g = groups[key]
        quit_steps = {}
        for who_key, n in g["reached"].items():
            if who_key not in g["finished"]:
                quit_steps[n] = quit_steps.get(n, 0) + 1
        out.append({"template": g["template"], "sheet_set": g["sheet_set"], "reports": g["reports"], "results": g["results"],
                    "moved_word": g["moved_word"], "not_moved_word": g["not_moved_word"],
                    "stuck_steps": {str(n): {"taps": s["taps"], "people": len(s["who"])} for n, s in sorted(g["stuck"].items())},
                    "quit_steps": {str(n): k for n, k in sorted(quit_steps.items())},
                    "minutes": _span(g["minutes"]), "measures": {k: _span(v) for k, v in sorted(g["measures"].items())},
                    "record_ids": g["record_ids"],
                    "texts": [{"kind": kind, "step": step, "text": text, "count": n}
                              for (kind, step, text), n in sorted(g["texts"].items(), key=lambda kv: (TEXT_KINDS.index(kv[0][0]), kv[0][1] or 0, kv[0][2]))]})
    # 雛形の id が分からない群（記録が壊れている等）は入れない。エンジンの入口が、束ごと断るため。
    out = [g for g in out if g["template"]]
    # 今の刷った組は、群に出てくる雛形の分だけ（記録の無い雛形の名を束に並べない）。組の名を持たない雛形と、形の外の名は入れない。
    current = {}
    for g in out:
        name = _name(getattr(TEMPLATES.get(g["template"]), "SHEET_SET", None))
        if name:
            current[g["template"]] = name
    now = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="minutes")  # 分まで（秒を持たない）
    return {"schema": SCHEMA, "exported_at": now, "from": FROM, "dropped_pii": dropped, "current_sets": current, "groups": out}


def out_path(out=None):
    """束を書く先。git に入らない所だけ（repo の中なら out/ の下）。決まりの外なら ValueError。"""
    now = datetime.now(timezone(timedelta(hours=9)))
    path = pathlib.Path(out) if out else ROOT / "out" / "engine-bundle" / f"bundle-{now:%Y%m%d-%H%M}.json"
    full = path.resolve()
    if full.is_relative_to(ROOT.resolve()) and not full.is_relative_to((ROOT / "out").resolve()):
        raise ValueError("束は git の外か、out/ の下に書く（作った人の文を repo に入れない）")
    return full


def main(argv=None):
    ap = argparse.ArgumentParser(prog="omochae.engine_bundle", description="作る過程の記録を、型紙エンジンへ渡す束（JSON 1 つ）にする。終了: 0 できた / 4 できない")
    sub = ap.add_subparsers(dest="cmd", required=True)
    ex = sub.add_parser("export", help="束を書く（git の外か out/ の下）")
    ex.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    try:
        path = out_path(args.out)
        bundle = build()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(bundle, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    except (OSError, ValueError) as e:
        print(f"できない: {e}", file=sys.stderr)
        return 4
    texts = sum(len(g["texts"]) for g in bundle["groups"])
    print(f"束を書いた: {path.name}（群 {len(bundle['groups'])}・文 {texts}・連絡先の形で落とした文 {bundle['dropped_pii']}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
