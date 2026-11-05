"""工作の様子の記録（本人の決定 2026-11-05 朝）: 「子供の工作の様子を蓄積して、サービス全体の改善をするようにする。
個人の情報は落とす決まりはそのまま」。型紙だけでなく、案内・聞く口の答え・サイトの流れを直す材料にする。

設計の芯:
- ここが新しく残すのは、聞く口（作っている途中の質問）の質問の文だけ。止まった所・動きの札・感想は、既にある試した記録
  （omochae.records）にあるので写さず、集計（summary）の時に読んで合わせる。同じ物を 2 か所に持つと、片方だけ直って食い違うため。
- 残す欄は決めた 6 つだけ: source_id・hypothesis_id・sheet_version・question・answered_from・asked_at。
  **残さない物**: IP・ブラウザの名・cookie・名前・声・映像・写真・答えの文。誰が聞いたかを辿れる物は、作る様子の改善に要らない。
  時刻は分まで（秒まで持つと、ほかの記録と突き合わせて人を絞れる）。
- 連絡先の形（メールアドレス・電話番号・郵便番号。持ち寄りと記録と同じ床 contrib.check_pii）がある質問は、文を残さない。
  落とした事だけを dropped: "pii" で残す（どれくらい落ちているかが分からないと、床が効いているかも分からない）。
  名前は形では見分けられないので、機械では落とせない。だから頁で名前を聞かず、作る側が読む時に気づいたら消す（床の限り）。
- 書けなくても例外を外へ出さない。聞く口の答えを、記録の都合で止めないため。
- 集計は作る側が読む物で、学ぶ人の画面には出さない（J-025: 順位と成績を見せない）。出す所は kaizen の作る側の頁だけ。
- 手順の進み（add_step）: 机の端に置いた端末の「作りながら見る」頁（web/tsukuru.py、観察 A）の札を押した事だけを残す。
  残す欄は 6 つ: source_id・hypothesis_id・sheet_version・step（手順の番号）・event（start・next・back・stuck・done）・at（分まで）。
  映像・写真・声はここに入らない（頁の鏡は端末の中だけ）。どの手順で止まるかを数えて、手順の紙と案内を直す材料にする（research/29 の 1）。
"""
import json
import os
import pathlib
import re
import secrets
from collections import Counter
from datetime import datetime, timedelta, timezone

from . import records
from .contrib import check_pii
from .hypotheses import ROOT

MAX_QUESTION = 200
# 残す欄はこれだけ。欄を足す時は、誰が聞いたかを辿れる物でない事を確かめてからここに足す（tests/test_making_log.py が鍵の一致を見る）。
FIELDS = ("source_id", "hypothesis_id", "sheet_version", "question", "answered_from", "asked_at")
# 手順の進みの欄と、受ける出来事。欄を足す時の考えは FIELDS と同じ（誰が押したかを辿れる物を足さない）。
STEP_FIELDS = ("source_id", "hypothesis_id", "sheet_version", "step", "event", "at")
EVENTS = ("start", "next", "back", "stuck", "done")


def folder():
    return pathlib.Path(os.environ.get("OMOCHAE_DATA", ROOT / "data")) / "making"


def add_ask(source_id, hypothesis_id, sheet_version, question, answered_from):
    """聞く口の質問 1 件を残す。返り値は書いたファイルの path（残さなかった時と書けなかった時は None）。"""
    try:
        text = " ".join(str(question or "").split())[:MAX_QUESTION]
        if not text:
            return None  # 何も聞いていない送信は、様子の記録にならない
        now = datetime.now(timezone(timedelta(hours=9)))
        rec = {"source_id": source_id, "hypothesis_id": hypothesis_id, "sheet_version": sheet_version, "question": text,
               "answered_from": str(answered_from or ""), "asked_at": now.isoformat(timespec="minutes")}
        if check_pii({"body": text}):
            # 連絡先の形がある文は残さない。落とした事だけを数えられるようにする。
            rec.update(question="", dropped="pii")
        d = folder()
        d.mkdir(parents=True, exist_ok=True)
        # ファイルの名前の時刻も分まで（中の asked_at と同じ理由。名前にだけ秒を残すと、そこから突き合わせられる）。
        # 乱数は、同じ分の質問がぶつからないためだけの物（人の印ではない）。
        path = d / f"ask-{now.strftime('%Y%m%d-%H%M')}-{secrets.token_hex(4)}.json"
        with open(path, "x", encoding="utf-8") as f:
            json.dump(rec, f, ensure_ascii=False, indent=2)
            f.write("\n")
        return path
    except Exception:
        return None


def add_step(source_id, hypothesis_id, sheet_version, step, event):
    """手順の進み 1 件を残す。返り値は書いたファイルの path（決まりの外と、書けなかった時は None）。
    残すのは札を押した事だけ（何番の手順で、進んだ・戻った・止まった・できた）。人の印は持たない。時刻は分まで（add_ask と同じ理由）。"""
    try:
        if event not in EVENTS or isinstance(step, bool) or not isinstance(step, int) or step < 1:
            return None
        now = datetime.now(timezone(timedelta(hours=9)))
        rec = {"source_id": source_id, "hypothesis_id": hypothesis_id, "sheet_version": sheet_version, "step": step, "event": event,
               "at": now.isoformat(timespec="minutes")}
        d = folder()
        d.mkdir(parents=True, exist_ok=True)
        path = d / f"step-{now.strftime('%Y%m%d-%H%M')}-{secrets.token_hex(4)}.json"
        with open(path, "x", encoding="utf-8") as f:
            json.dump(rec, f, ensure_ascii=False, indent=2)
            f.write("\n")
        return path
    except Exception:
        return None


def steps(source_id=None):
    """残した手順の進みを返す（分の順。同じ分の中の順は決まらない）。読めないファイルは飛ばす。"""
    out = []
    d = folder()
    if not d.exists():
        return out
    for p in sorted(d.glob("step-*.json")):
        try:
            rec = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if source_id is None or rec.get("source_id") == source_id:
            out.append(rec)
    return out


def asks(source_id=None):
    """残した質問を、聞かれた分の順で返す（同じ分の中の順は決まらない。秒を持たないため）。source_id を渡せばその玩具の分だけ。読めないファイルは飛ばす。"""
    out = []
    d = folder()
    if not d.exists():
        return out
    for p in sorted(d.glob("ask-*.json")):
        try:
            rec = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if source_id is None or rec.get("source_id") == source_id:
            out.append(rec)
    return out


def _same(q):
    """同じ質問とみなす鍵。空白と句読点と記号を落として比べるだけ（言い回しの違いまでは寄せない。寄せると、違う困り事を 1 つに数える）。"""
    return re.sub(r"[\s、。，．,.!?！？・「」『』（）()\-ー〜~]", "", q)


def summary(source_id):
    """作る側が読む集計。学ぶ人の画面には出さない。
    asks は (質問, 回数) の多い順（同じ回数は文の順。聞かれた順は分までしか持たないので、並びを時刻に頼らない）。
    同じ質問の書き方が割れた時に見せる文は、一番多い書き方（同じ数なら文の順で先の物）。止まった所などは試した記録の答えと感想から、書かれた言葉のまま。"""
    counts, variants = Counter(), {}
    dropped = 0
    for a in asks(source_id):
        if a.get("dropped"):
            dropped += 1
            continue
        key = _same(a.get("question", ""))
        if not key:
            continue
        counts[key] += 1
        variants.setdefault(key, Counter())[a["question"]] += 1
    shown = {k: sorted(v.items(), key=lambda kv: (-kv[1], kv[0]))[0][0] for k, v in variants.items()}
    recs = records.all_records(source_id)
    by_version = {}
    for r in recs:
        slot = by_version.setdefault(r["hypothesis_id"], {}).setdefault(r.get("sheet_version", 1), {})
        slot[r["result"]] = slot.get(r["result"], 0) + 1

    def words(key):
        return [r["answers"][key] for r in recs if (r.get("answers") or {}).get(key, "").strip()]

    # 止まった手順は番号ごとに数える（番号の小さい順。多い順にすると、手順の並びが読めなくなる）。できたは回数だけ。
    stuck_steps = Counter(e["step"] for e in steps(source_id) if e.get("event") == "stuck")
    done = sum(1 for e in steps(source_id) if e.get("event") == "done")
    return {"stuck_steps": dict(sorted(stuck_steps.items())), "steps_done": done,
            "asks": sorted(((shown[k], n) for k, n in counts.items()), key=lambda qn: (-qn[1], qn[0])),
            "asks_dropped": dropped,
            "stuck": words("stuck"), "first_moved": words("first_moved"), "what_if": words("what_if"),
            "impressions": [r["impression"] for r in recs if (r.get("impression") or "").strip()],
            "results_by_version": by_version, "reports": len(recs)}
