"""工作の様子の記録（本人の決定 2026-11-05 朝）: 「子供の工作の様子を蓄積して、サービス全体の改善をするようにする。
個人の情報は落とす決まりはそのまま」。型紙だけでなく、案内・聞く口の答え・サイトの流れを直す材料にする。

設計の芯:
- ここが残すのは、聞く口（作っている途中の質問）の質問の文と、札や釦を押した事（手順の進み・頁の段の進み）だけ。止まった所の言葉・
  動きの札・感想は、既にある試した記録（omochae.records）にあるので写さず、集計（summary）の時に読んで合わせる。同じ物を 2 か所に
  持つと、片方だけ直って食い違うため。
- 残す欄は決めた物だけ（下の FIELDS・STEP_FIELDS・STAGE_FIELDS。試験が鍵の一致を見る）。
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
- 蓄積の器（Issue #119・U-45 の段取り 1〜3、本人の指示 11-05「凍結の例外で入れる」）で足した物:
  - **人の数え方（who）**: 画面が sessionStorage に持つ乱数（英数字 8〜12 桁）を、その場限りの印として受ける。cookie にも名前にもせず、
    サーバは形だけを確かめて残す。タブを閉じると消えるので、日をまたいで同じ人とは分からない（分からなくてよい。数えたいのは
    「同じ段で何人止まったか」で、人を追う事ではない）。形の外の値は空にする（名前や連絡先を who に入れさせないため）。
  - **エンジンとつなぐ欄（template・sheet_set）**: 型紙エンジンの報告は雛形と形で集める。玩具の印と版だけでは向こうの集計と
    突き合わせられないので、雛形の id と刷った組を出来事に残す。
  - **聞いた段（step）**: 聞く口の質問に、今どの手順かを任意で添える（同じ段の同じ問いを束ねて、先回りの答えの材料にする）。
  - **頁の段の進み（add_stage）**: 予想を書いた・刷った・作る頁を開いた・記録を残した、の 4 つだけ。どの段で先へ進まなくなるかを数える。
    残す欄は source_id・template・stage・who・at。何を書いたか（予想の文・記録の中身）はここに写さない。
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
# who はその場限りの乱数の印（下の clean_who）。IP・機器の名前・cookie・名前は、ここにも下の 2 つにも足さない。
FIELDS = ("source_id", "hypothesis_id", "sheet_version", "template", "sheet_set", "question", "answered_from", "step", "who", "asked_at")
# 手順の進みの欄と、受ける出来事。欄を足す時の考えは FIELDS と同じ（誰が押したかを辿れる物を足さない）。
STEP_FIELDS = ("source_id", "hypothesis_id", "sheet_version", "template", "sheet_set", "step", "event", "who", "at")
EVENTS = ("start", "next", "back", "stuck", "done")
# 頁の段の進み。順路の順（予想 → 型紙 → 作る → 記録）。
STAGE_FIELDS = ("source_id", "template", "stage", "who", "at")
STAGES = ("predict", "print", "make", "record")
# その場限りの印の形。英数字だけ・8〜12 桁。これ以外は残さない（自由な文を who に入れさせない）。
WHO = re.compile(r"[A-Za-z0-9]{8,12}")
# 感想と説明から拾う言葉。分からなかった側と面白かった側を分けて、たとえと説明のどこを言い換えるかの材料にする（Issue #119 の 3）。
# 言葉の一覧は少なく保つ: 広げるほど、関係の無い文を拾う。
HARD_WORDS = ("分から", "わから", "むずかし", "難し", "できな", "困っ")
FUN_WORDS = ("面白", "おもしろ", "楽し", "たのし", "うれし", "嬉し", "かわい", "すご")


# 聞く口の下に出す断りの文。本人の決定（11-05、カード 20261105-092043 の 1 点目）の文をそのまま 1 か所に置き、玩具の頁・手帖・作りながら見る頁が同じ物を出す。
# 名前は床では落とせない（落とせるのは連絡先の形だけ。J-027）ので、決定の文の後ろに、名前を書かない（声なら言わない）お願いを別の文で添える。
ASK_NOTICE = "聞いた言葉は、名前や連絡先を除いて、案内を良くするために残します。声と映像は残しません。"
ASK_NAME_TEXT = "名前は書かないでください。"
ASK_NAME_VOICE = "名前は言わないでください。"

def folder():
    return pathlib.Path(os.environ.get("OMOCHAE_DATA", ROOT / "data")) / "making"


def clean_who(who):
    """その場限りの印を、形だけ確かめて返す。形の外（空・長すぎ・記号や字の混じった物）は空にする。
    なぜ落とすか: who は画面が勝手に作る乱数のはずで、そこに名前や連絡先が入っていたら、残してはいけない物だから。"""
    who = str(who or "")
    return who if WHO.fullmatch(who) else ""


def _engine(source_id, hypothesis_id=None):
    """エンジンの報告とつなぐ欄（雛形の id・刷った組）。仮説が雛形を持てばそれ、無ければ玩具の雛形（刷る時と同じ決め方）。
    分からない時は空で返す（つなぐ欄が無いだけで、出来事は残す）。"""
    try:
        from .compose import TEMPLATES
        from .hypotheses import load

        data = load(source_id)
        template = data.get("template", "slider_fan")
        h = next((x for x in data["hypotheses"] if x["id"] == hypothesis_id), None)
        if h and h.get("template"):
            template = h["template"]
        return template, str(getattr(TEMPLATES[template], "SHEET_SET", ""))
    except Exception:
        return "", ""


def _step_no(step):
    """聞いた段・押した段の番号。1 以上の整数だけを受ける（字の数も受ける）。それ以外は None。"""
    if isinstance(step, bool):
        return None
    if isinstance(step, str) and step.strip().isdigit():
        step = int(step.strip())
    return step if isinstance(step, int) and step >= 1 else None


def _write(prefix, rec):
    """出来事 1 件を making/ に書く。ファイルの名前の時刻も分まで（中の時刻と同じ理由。名前にだけ秒を残すと、そこから突き合わせられる）。
    乱数は、同じ分の出来事がぶつからないためだけの物（人の印ではない）。"""
    now = datetime.now(timezone(timedelta(hours=9)))
    d = folder()
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{prefix}-{now.strftime('%Y%m%d-%H%M')}-{secrets.token_hex(4)}.json"
    with open(path, "x", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return path


def _now():
    return datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="minutes")


def add_ask(source_id, hypothesis_id, sheet_version, question, answered_from, step=None, who=""):
    """聞く口の質問 1 件を残す。返り値は書いたファイルの path（残さなかった時と書けなかった時は None）。
    step は今どの手順か（任意。分からなければ None）。who はその場限りの印（任意。形の外は空）。"""
    try:
        text = " ".join(str(question or "").split())[:MAX_QUESTION]
        if not text:
            return None  # 何も聞いていない送信は、様子の記録にならない
        template, sheet_set = _engine(source_id, hypothesis_id)
        rec = {"source_id": source_id, "hypothesis_id": hypothesis_id, "sheet_version": sheet_version, "template": template, "sheet_set": sheet_set,
               "question": text, "answered_from": str(answered_from or ""), "step": _step_no(step), "who": clean_who(who), "asked_at": _now()}
        if check_pii({"body": text}):
            # 連絡先の形がある文は残さない。落とした事だけを数えられるようにする。
            rec.update(question="", dropped="pii")
        return _write("ask", rec)
    except Exception:
        return None


def add_step(source_id, hypothesis_id, sheet_version, step, event, who=""):
    """手順の進み 1 件を残す。返り値は書いたファイルの path（決まりの外と、書けなかった時は None）。
    残すのは札を押した事だけ（何番の手順で、進んだ・戻った・止まった・できた）。who はその場限りの印（任意）。時刻は分まで（add_ask と同じ理由）。"""
    try:
        if event not in EVENTS or isinstance(step, bool) or not isinstance(step, int) or step < 1:
            return None
        template, sheet_set = _engine(source_id, hypothesis_id)
        rec = {"source_id": source_id, "hypothesis_id": hypothesis_id, "sheet_version": sheet_version, "template": template, "sheet_set": sheet_set,
               "step": step, "event": event, "who": clean_who(who), "at": _now()}
        return _write("step", rec)
    except Exception:
        return None


def add_stage(source_id, stage, who=""):
    """頁の段の進み 1 件を残す（予想を書いた predict・刷った print・作る頁を開いた make・記録を残した record）。
    返り値は書いたファイルの path（決まりの外と、書けなかった時は None）。何を書いたかは写さない。呼ぶ口を止めないよう、例外は外へ出さない。"""
    try:
        if stage not in STAGES:
            return None
        rec = {"source_id": source_id, "template": _engine(source_id)[0], "stage": stage, "who": clean_who(who), "at": _now()}
        return _write("stage", rec)
    except Exception:
        return None


def _read(prefix, source_id=None):
    """残した出来事を返す（分の順。同じ分の中の順は決まらない。秒を持たないため）。読めないファイルは飛ばす。"""
    out = []
    d = folder()
    if not d.exists():
        return out
    for p in sorted(d.glob(f"{prefix}-*.json")):
        try:
            rec = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if source_id is None or rec.get("source_id") == source_id:
            out.append(rec)
    return out


def steps(source_id=None):
    """残した手順の進み。"""
    return _read("step", source_id)


def asks(source_id=None):
    """残した質問。source_id を渡せばその玩具の分だけ。"""
    return _read("ask", source_id)


def stages(source_id=None):
    """残した頁の段の進み。"""
    return _read("stage", source_id)


def _same(q):
    """同じ質問とみなす鍵。空白と句読点と記号を落として比べるだけ（言い回しの違いまでは寄せない。寄せると、違う困り事を 1 つに数える）。"""
    return re.sub(r"[\s、。，．,.!?！？・「」『』（）()\-ー〜~]", "", q)


def _count_same(items):
    """同じ質問（空白と句読点の違いだけ）を 1 つに数え、(見せる文, 回数) を多い順で返す（同じ回数は文の順）。
    見せる文は一番多い書き方。聞かれた順は分までしか持たないので、並びを時刻に頼らない。"""
    counts, variants = Counter(), {}
    for q in items:
        key = _same(q)
        if not key:
            continue
        counts[key] += 1
        variants.setdefault(key, Counter())[q] += 1
    shown = {k: sorted(v.items(), key=lambda kv: (-kv[1], kv[0]))[0][0] for k, v in variants.items()}
    return sorted(((shown[k], n) for k, n in counts.items()), key=lambda qn: (-qn[1], qn[0]))


def _span(values):
    """数の幅 [最小, 最大, 件数]。無ければ None。平均は出さない（少ない件数の平均は、確かな値のように見える）。"""
    values = [v for v in values if isinstance(v, (int, float)) and not isinstance(v, bool)]
    return [min(values), max(values), len(values)] if values else None


def summary(source_id):
    """作る側が読む集計。学ぶ人の画面には出さない。数と幅だけで、上下を付ける形（多い順に仮説や玩具を並べる・点・割合の成績）は作らない。
    前からある鍵（asks・stuck・impressions・results_by_version・stuck_steps など）の意味は変えない。Issue #119 の 6 つの集計のために足した鍵:
    - stuck_by_version: {版: {段: {"taps": 札の数, "people": 印のある人の数}}}（1 止まった段）
    - measures: {仮説: {版: {欄: [最小, 最大, 件数]}}}・fixes: 直した点の一覧（2 動きの結果）
    - words: {"hard": 分からなかった側の文, "fun": 面白かった側の文}（3 感想の言葉。感想・メモ・説明・次の思いつきから）
    - asks_by_step: {段（無ければ None）: [(質問, 回数)…]}（4 聞く口の質問）
    - completion: {"minutes": 最初に動くまでの分の幅, "moved": 動いた記録の数, "moved_word": その札の言葉, "quit_steps": {段: 人の数}, "people": 印のある人の数}（5 完成の様子）
    - flow: {段: {"events": 出来事の数, "people": 印のある人の数}}（6 サイトの流れ。段は STAGES の順）"""
    from . import loop

    all_asks = asks(source_id)
    live = [a for a in all_asks if not a.get("dropped")]
    dropped = len(all_asks) - len(live)
    recs = records.all_records(source_id)
    by_version, measured = {}, {}
    for r in recs:
        v = r.get("sheet_version", 1)
        slot = by_version.setdefault(r["hypothesis_id"], {}).setdefault(v, {})
        slot[r["result"]] = slot.get(r["result"], 0) + 1
        # 測った値: 記録の上の段にある数の欄（版の番号と、完成の様子で使う分は除く）。欄の名前を決め打ちしないのは、雛形ごとに測る物が違うため。
        for k, val in r.items():
            if k not in ("sheet_version", "minutes_to_try") and isinstance(val, (int, float)) and not isinstance(val, bool):
                measured.setdefault(r["hypothesis_id"], {}).setdefault(v, {}).setdefault(k, []).append(val)
    measures = {hid: {v: {k: _span(vals) for k, vals in fields.items()} for v, fields in vs.items()} for hid, vs in measured.items()}
    fixes = [{"record_id": r["id"], "hypothesis_id": r["hypothesis_id"], "sheet_version": r.get("sheet_version", 1),
              "part": str(f.get("part", "")), "change": str(f.get("change", "")), "outcome": str(f.get("outcome", ""))}
             for r in recs for f in r.get("fixes", []) if isinstance(f, dict)]

    def words(key):
        return [r["answers"][key] for r in recs if (r.get("answers") or {}).get(key, "").strip()]

    # 感想の言葉: 感想・メモ・説明・次の思いつき。説明は人が書いた物だけ（Claude の読みは入れない。人の言葉を拾うための集計なので）。
    said = []
    for r in recs:
        told = loop.explanation(r["id"]) or {}
        said += [t.strip() for t in (r.get("impression"), r.get("note"), told.get("text"), told.get("next_idea")) if (t or "").strip()]
    word_lists = {"hard": [t for t in said if any(w in t for w in HARD_WORDS)], "fun": [t for t in said if any(w in t for w in FUN_WORDS)]}

    evs = steps(source_id)
    # 止まった手順は番号ごとに数える（番号の小さい順。多い順にすると、手順の並びが読めなくなる）。できたは回数だけ。
    stuck_steps = Counter(e["step"] for e in evs if e.get("event") == "stuck")
    done = sum(1 for e in evs if e.get("event") == "done")
    by_v = {}
    for e in evs:
        if e.get("event") != "stuck":
            continue
        slot = by_v.setdefault(e.get("sheet_version", 1), {}).setdefault(e["step"], {"taps": 0, "who": set()})
        slot["taps"] += 1
        if e.get("who"):
            slot["who"].add(e["who"])
    stuck_by_version = {v: {n: {"taps": x["taps"], "people": len(x["who"])} for n, x in sorted(ss.items())} for v, ss in sorted(by_v.items())}

    by_step = {}
    for a in live:
        by_step.setdefault(a.get("step"), []).append(a.get("question", ""))
    # 段の番号の順。段なし（None）は最後。
    asks_by_step = {k: _count_same(v) for k, v in sorted(by_step.items(), key=lambda kv: (kv[0] is None, kv[0] or 0))}

    # 途中でやめた段: 印のある人のうち、できたを押していない人が最後に居た段（進んだ先の段）。印の無い出来事は、人ごとに分けられないので入れない。
    reached, finished = {}, set()
    for e in evs:
        w = e.get("who")
        if not w:
            continue
        if e.get("event") == "done":
            finished.add(w)
        reached[w] = max(reached.get(w, 0), e["step"] + (1 if e.get("event") == "next" else 0))
    quit_steps = Counter(n for w, n in reached.items() if w not in finished)
    try:
        moved_word = records.results_for(source_id)[0]  # 雛形の RESULTS の先頭が、動いた側の言葉
    except Exception:
        moved_word = ""
    completion = {"minutes": _span([r.get("minutes_to_try") for r in recs]), "moved": sum(1 for r in recs if r["result"] == moved_word),
                  "moved_word": moved_word, "quit_steps": dict(sorted(quit_steps.items())), "people": len(reached)}

    flow = {}
    st = stages(source_id)
    for name in STAGES:
        mine = [e for e in st if e.get("stage") == name]
        flow[name] = {"events": len(mine), "people": len({e["who"] for e in mine if e.get("who")})}

    return {"stuck_steps": dict(sorted(stuck_steps.items())), "steps_done": done,
            "asks": _count_same([a.get("question", "") for a in live]),
            "asks_dropped": dropped,
            "stuck": words("stuck"), "first_moved": words("first_moved"), "what_if": words("what_if"),
            "impressions": [r["impression"] for r in recs if (r.get("impression") or "").strip()],
            "results_by_version": by_version, "reports": len(recs),
            "stuck_by_version": stuck_by_version, "measures": measures, "fixes": fixes, "words": word_lists,
            "asks_by_step": asks_by_step, "completion": completion, "flow": flow}
