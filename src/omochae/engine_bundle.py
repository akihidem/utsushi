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
- 話した事（Issue #307。話す口 talk_log の記録）も束に入れる: 作る前の考え・作りながらの工夫（手順の番号つき）・できた後の話。
  文の種類の名は、話す口の場面の名（think・craft・keep）と同じ。声は置き場にも束にも無い（話す口が字だけを残す）。
  記録に結んだ話は、その記録と同じ群に数える（直す前の組の紙の話を、今の組に数えない）。記録の番号があるのに記録が無い話は入れない
  （取り下げた人の言葉を、束で外へ出さない側に倒す）。記録に結んだ後に作る側が隠した字も入れない（名前は形で落とせないので、
  作る側が読んで気づいた時に隠す。その字を、束からエンジンの側の下書きへ流さない）。見せる印・声から入れたかの印・その場限りの印の値は入れない。
  見せてよいと選んだ話だけに絞らないのは、束を読むのが作る側だけで、git の外に置く物だから（エンジンの側の Issue の下書きは、
  作った人の言葉を「Issue に写さない手元の材料」に分けて置く）。出す時に、話す口の入口の床（連絡先・名乗り・学校の形）をもう一度当てる。
- 束の上の段に、群に出てくる雛形の「今の刷った組」を書く（current_sets。Issue #309）。エンジンの repo の雛形は組の名を持たないので、
  前の組の紙の記録から起きた案（もう直っている事がある）を、読む人が見分けられない。ここは今の組を並べるだけで、前の組の記録を
  束から外しはしない（直っていない困り事まで消え、直す前と後を並べて読めなくなる）。
- 動画の札（試行の動画の入口 trial_video。Issue #335）も束に入れる。札は事前の人の確かめなしで渡す（本人の方針 11-06「こういう確認は不用です。
  版管理してるから。できた型紙をみて、どうするか後で指示出せると思います」）。人が外した札と、意味を付けていない機械の候補（MACHINE）は入れない。
  サイトに人の言葉や写真を載せる時の人の確かめは、外に出る所なので、今までどおり残る（ここは束の門だけ）。自分のやり方の動画や、
  手順の困り事に当たらない物は、人が確かめる段で外れる。止まった段の数と文にし、人の工夫の札は作りながらの工夫に写す。案内・聞く口・サイトの札は
  エンジンの案にしない。受け口の記録（all_records の既定で外れる記録）も、札があれば群に数える。動きの札は、上げた人が結果を選んだ記録だけ数える。
  なぜエンジンの報告の形で渡さないか: 報告は「動いたか」と「仕上がりの点」が要り、聞いていない値を作る事になるため。
  人の数は数えない: 1 人が何本上げるか分からず、札の読み手は作った本人でないため（エンジンの側は、印の無い札は 3 回からの線で見る）。
  作る前の型紙のレビューの動画（video_kind が review）は作っていないので、札を種類 review の文にして、止まった段・工夫・報告の数に入れない。
  映っている紙が受付で選ばれた玩具の紙と違う時は、人が札の置き場に engine_sheet（エンジンの雛形の id と形の名）を書き、その紙の群に数える。
  レビューの 1 本目が、エンジンの repo の雛形の紙を読んでいた。元の玩具の群に数えると、別の紙の声になる。
  **入れない物**: 動画・コマ・字の全文（話した人の名前が混じり得る）・上げた人の文（note。人が読んで札に書いた分だけが流れる）・読んだ人と確かめた人の名前・札の秒。
- 群は「雛形の id × 刷った組 × 紙」（Issue #334）。紙は、玩具の番号と仮説の記号（版 2 からは版も）をつないだ名。同じ雛形・同じ組でも、紙が違えば組み方の
  手順の数と番号が違うので、足すと「別の紙の別の段で止まった 2 人」が「同じ手順で止まった 2 人」になる。エンジンの側は、手順ごとの数と文だけを紙で分け、
  動きの札・報告の数・工夫の言葉は雛形と組で足す。紙の名に人を辿れる物は入らない。玩具ごとに型紙が 1 枚になった後も、同じ雛形を使う別の玩具が混ざらない。
- 手で置いた記録の形が決まりの外でも、束ごと止めない（Issue #313）。型の外の欄は読み飛ばし、その記録のほかの欄と数は数える。
  1 件の崩れた記録のために、全部の記録の束が出なくなる方が困るため。
終了: 0 = できた / 4 = できない（書く先が決まりの外・呼び方の誤り）。1 と 2 は使わない。
"""
import argparse
import itertools
import json
import pathlib
import re
import sys
from datetime import datetime, timedelta, timezone

from . import loop, making_log, records, talk_log, trial_video
from .contrib import check_pii
from .hypotheses import ROOT

# 束の形。エンジンの omochae.engine_loop（paper-to-toy の #63）と同じ一覧で、片方を変える時は両方を変える（tests/test_engine_bundle.py が鍵の一致を見る）。
SCHEMA = "omochae.making-bundle/1"
FROM = "utsushi"
TOP_KEYS = ("schema", "exported_at", "from", "dropped_pii", "current_sets", "groups")
GROUP_KEYS = ("template", "sheet_set", "paper", "reports", "results", "moved_word", "not_moved_word", "stuck_steps", "quit_steps", "craft_steps",
              "minutes", "measures", "record_ids", "texts")
TEXT_KEYS = ("kind", "step", "text", "count")
# 文の種類: 止まった所・直した点（工夫）・思いつき（工夫）・感想・聞く口の質問・試した記録への人の説明。
# 話した事の 3 つは、話す口の場面の名のまま: think 作る前の考え・craft 作りながらの工夫・keep できた後の話。
# review は作る前の型紙のレビューの指摘（動画の札から）。作っていないので、止まった段・工夫・報告の数と混ぜない。
TEXT_KINDS = ("stuck", "fix", "idea", "impression", "question", "explain", "think", "craft", "keep", "review")
REVIEW = "review"  # 受け口の記録の video_kind の値（作る前の型紙のレビューの動画。作った時の動画には、この欄が無い）
REVIEW_OUTSIDE = ("answer", "site")
SERVICE_MARKS = ("guide", "answer", "site")  # 動画の札のうち、案内・聞く口・サイトの困り事。型紙の外なので、エンジンの案の材料にしない
MAX_TEXT = 300  # エンジンの入口の、文 1 つの上限。長い感想は頭だけを入れる（全文は記録の番号から人が読む）
MAX_TEXTS = 2000  # エンジンの入口の、群 1 つの文の上限。超えると束ごと断られる
MAX_STEP = 40
NAME = re.compile(r"[A-Za-z0-9_.-]{1,80}")  # 雛形の id と刷った組の形（エンジンの入口と同じ）
MEASURE = re.compile(r"[a-z_]{1,30}")
RECORD_ID = re.compile(r"R-[0-9]{4,8}")  # 記録の番号の形（エンジンの入口と同じ）。形の外の番号は束に入れない（自由な文をこの欄で運ばせない）
# 札の文の中の動画の秒（「1234.5 秒」「1234.5〜1240.0 秒」「3925・3945 秒」「291 秒から」）。束には時刻を入れないので、文からも外す。
# 残すと、数の多い所を連絡先の形と見るエンジンの入口の床に当たり、文ごと落ちる（11-06 に作る時の動画の札が 8 件とも落ちた）。秒の書き方だけを外す。
# 秒のすぐ後の「から・にも・に・は」も一緒に外す。秒だけを外すと「4849.8 秒は頭が下で、4850.0 秒に上へ移り」が「は頭が下で、に上へ移り」になり、
# エンジンの側で読む人に文の意味が届かない（11-06 の束で見つけた）。「で」「の」は外さない（「3 秒で回る」の様に、秒の後の文の芯になる事がある）。
SECONDS = re.compile(r"(?:[0-9]+(?:\.[0-9]+)?\s*[〜・]\s*)*[0-9]+(?:\.[0-9]+)?\s*秒(?:から|にも|に|は)?\s*")
# 機械が拾った札の案（動きの少ない区間など）の読み手の印。意味を付けていない候補なので、確かめなしでは束に入れない。
MACHINE = "機械"
JST = timezone(timedelta(hours=9))
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


def _when(text):
    """時刻を時刻として読む。読めない時は None。文字のまま比べると、秒の有無や時差の書き方が違う時刻で、黙って誤る。"""
    try:
        t = datetime.fromisoformat(str(text))
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=JST)


def _without_seconds(text):
    """札の文から、動画の秒の書き方を外す。外して空になった括弧も外す。字でない欄はそのまま返す（say が読み飛ばす）。"""
    return re.sub(r"（\s*）", "", SECONDS.sub("", text)) if isinstance(text, str) else text


def _sheet_set_of(rec):
    """その記録の紙の刷った組。記録が持てばそれ。無ければ、記録の時刻までに刷った型紙の確定の記録のうち、一番新しい物。
    どちらも無ければ空（不明）。今の雛形の組は使わない（直した後の組に、直す前の記録を数えないため）。
    時刻の読めない記録と確定は、使わない側に倒す（不明の群に分ける）。確定の並びの順でなく、時刻で一番新しい物を選ぶ。"""
    if _name(rec.get("sheet_set")):
        return rec["sheet_set"]
    at = _when(rec.get("recorded_at"))
    best = None
    for conf in loop.sheet_confirmations(rec.get("source_id")) if at else []:
        if isinstance(conf, dict) and conf.get("hypothesis_id") == rec.get("hypothesis_id") and conf.get("version") == rec.get("sheet_version", 1):
            confirmations = conf.get("confirmations")
            for c in confirmations if isinstance(confirmations, list) else []:
                when, name = (_when(c.get("at")), _name(c.get("sheet_set"))) if isinstance(c, dict) else (None, "")
                if when and name and when <= at and (best is None or when >= best[0]):
                    best = (when, name)
    return best[1] if best else ""


def _paper(rec):
    """どの紙かの名。玩具の番号と仮説の記号をつなぐ。版 2 からは版も足す（版で手順が変わる事がある）。分からない時は空（紙で分けない）。"""
    source, hypothesis, version = rec.get("source_id"), rec.get("hypothesis_id"), rec.get("sheet_version")
    if not (isinstance(source, str) and isinstance(hypothesis, str) and source and hypothesis):
        return ""
    name = f"{source}.{hypothesis}" + (f".v{version}" if isinstance(version, int) and not isinstance(version, bool) and version > 1 else "")
    return _name(name)


def _group(groups, template, sheet_set, paper=""):
    key = (_name(template), _name(sheet_set), _name(paper))
    if key not in groups:
        groups[key] = {"template": key[0], "sheet_set": key[1], "paper": key[2], "reports": 0, "results": {}, "moved_word": "", "not_moved_word": "",
                       "stuck": {}, "craft": {}, "reached": {}, "finished": set(), "minutes": [], "measures": {}, "record_ids": [], "texts": {}}
    return groups[key]


def _cap_texts(texts):
    """群 1 つの文を上限までにする。超えた時は種類ごとに順に取る（並びのまま切ると、後ろの種類が丸ごと消える）。並びは元のまま返す。
    全部を見たい時は、記録の番号から人が読む。超えなければ何も変えない。"""
    if len(texts) <= MAX_TEXTS:
        return texts
    by_kind = {}
    for i, t in enumerate(texts):
        by_kind.setdefault(t["kind"], []).append(i)
    turns = [i for row in itertools.zip_longest(*by_kind.values()) for i in row if i is not None]
    kept = set(turns[:MAX_TEXTS])
    print(f"文が多い群があるので、{len(texts) - MAX_TEXTS} 件を束に入れなかった", file=sys.stderr)
    return [t for i, t in enumerate(texts) if i in kept]


def _count_result(g, rec, tpl):
    """動きの札を数える。札の言葉は雛形が持つ物だけ（自由な文を札の欄で運ばせない）。先頭が動いた側。動かない側は、「わからない」を除いた最後の札。
    「わからない」はどちらにも数えない。
    前の札の記録は今の札に読み替える（#146）。エンジンは moved_word と not_moved_word で数を引くので、前の札のままだと数から落ちる。
    手で置かれた記録の札は字とは限らないので、辞書を直に引かない。"""
    if tpl is None:
        return
    word, old = rec.get("result"), getattr(tpl, "OLD_RESULTS", {})
    word = old[word] if word in tuple(old) else word
    # 動画の受け口の記録の「わからない」は、動いたかを聞いていない時の置き字で、見た事の札ではない。上げた人が選んだ札は数える。
    # 前は、札に「わからない」の無い雛形（虎）だけがこれで外れていた。どの雛形も「わからない」を持つ形（#146）では、ここで分ける。
    asked = not (rec.get("via") == records.UPLOADED and word == UNSURE)
    if asked and word in tpl.RESULTS:
        g["results"][word] = g["results"].get(word, 0) + 1
    sure = [w for w in tpl.RESULTS if w != UNSURE]
    g["moved_word"], g["not_moved_word"] = sure[0], (sure[-1] if len(sure) > 1 else "")


def _span(values):
    """数の幅 [最小, 最大, 件数]。無ければ None。平均は出さない（少ない件数の平均は、確かな値のように見える）。"""
    return [min(values), max(values), len(values)] if values else None


def build(origin=FROM):
    """束を作って返す（dict）。書かない。"""
    from .compose import TEMPLATES

    groups, dropped = {}, 0

    def say(g, kind, text, step=None, floor=None):
        """文を 1 つ足す。床に当たれば入れず、落とした数だけ数える。同じ文（同じ種類・同じ段）は回数にまとめる。入れたら真。
        床は、上限で切る前の全文に当てる（切った端に番号の半分が残る形を作らない）。既定は連絡先の形。話した事は、話す口の床。"""
        nonlocal dropped
        if not isinstance(text, str):  # 文字でない欄（手で置いた記録の list など）は、文として読まない
            return False
        full = " ".join(text.split())
        if not full:
            return False
        if floor(full) if floor else check_pii({"body": full}):
            dropped += 1
            return False
        text = _clean(full)
        step = step if isinstance(step, int) and not isinstance(step, bool) and 1 <= step <= MAX_STEP else None
        g["texts"][(kind, step, text)] = g["texts"].get((kind, step, text), 0) + 1
        return True

    # 試した記録: 動きの札・測った値・止まった所・直した点・思いつき・感想と、人の説明。
    group_of = {}  # 記録の番号 → その記録の群の鍵（記録に結んだ話を、同じ群に数えるため）
    for r in records.all_records():
        if not isinstance(r, dict):  # 辞書でない物（手で置いたファイル）は、記録として数えない
            continue
        template = making_log._engine(r.get("source_id"), r.get("hypothesis_id"))[0]
        g = _group(groups, template, _sheet_set_of(r), _paper(r))
        g["reports"] += 1
        rid = r.get("id") if isinstance(r.get("id"), str) and RECORD_ID.fullmatch(r["id"]) else None
        if rid:
            group_of[rid] = (g["template"], g["sheet_set"], g["paper"])
            g["record_ids"].append(rid)
        _count_result(g, r, TEMPLATES.get(template))
        for k, v in r.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool) and k != "sheet_version" and MEASURE.fullmatch(k):
                (g["minutes"] if k == "minutes_to_try" else g["measures"].setdefault(k, [])).append(v)
        # 欄は、決まった型の時だけ読む（answers は辞書・ideas と fixes は list・文は文字）。文字の欄を list として読むと、1 字ずつの文になる。
        answers = r.get("answers") if isinstance(r.get("answers"), dict) else {}
        say(g, "stuck", answers.get("stuck"))
        say(g, "idea", answers.get("what_if"))
        for idea in r.get("ideas") if isinstance(r.get("ideas"), list) else []:
            say(g, "idea", idea)
        say(g, "impression", r.get("impression"))
        for f in r.get("fixes") if isinstance(r.get("fixes"), list) else []:
            if isinstance(f, dict) and all(isinstance(f.get(k), str) and f[k].strip() for k in ("part", "change", "outcome")):
                say(g, "fix", f'{f["part"]} / {f["change"]} / {f["outcome"]}')
        told = (loop.explanation(rid) if rid else None) or {}  # 人が書いた説明だけ（Claude の読みは入れない）
        told = told if isinstance(told, dict) else {}
        say(g, "explain", told.get("text"))
        say(g, "idea", told.get("next_idea"))

    # 手順の進み: 止まったの札と、途中でやめた段。人は、その場限りの印で数えるだけで、印の値は束に入れない。
    for e in making_log.steps():
        if not isinstance(e, dict):
            continue
        step = e.get("step")
        if not (isinstance(step, int) and not isinstance(step, bool) and 1 <= step <= MAX_STEP):
            continue
        g = _group(groups, e.get("template"), e.get("sheet_set"), _paper(e))
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
        if not isinstance(a, dict):
            continue
        g = _group(groups, a.get("template"), a.get("sheet_set"), _paper(a))
        if a.get("dropped"):
            dropped += 1
            continue
        say(g, "question", a.get("question"), a.get("step"))

    # 話した事（話す口の記録）。入口の床で落ちた物は文が残っていないので、落とした数にだけ足す。
    dropped += sum(talk_log.dropped().values())
    for t in talk_log.talks():
        if not isinstance(t, dict):
            continue
        scene = t.get("scene")
        if scene not in talk_log.SCENES:
            continue
        if t.get("record_id"):
            if t["record_id"] not in group_of:
                continue  # 記録が無い（取り下げた・消えた）。その人の言葉を束に入れない
            if t.get("share") is not True:
                continue  # 記録に結んだ後に、作る側が隠した字（読んで名前などに気づいた時に隠す）。束にも入れない
            g = _group(groups, *group_of[t["record_id"]])
        else:
            g = _group(groups, t.get("template"), t.get("sheet_set"), _paper(t))
        step = t.get("step") if scene == "craft" else None
        step = step if isinstance(step, int) and not isinstance(step, bool) and 1 <= step <= MAX_STEP else None
        if say(g, scene, t.get("text"), step, floor=talk_log.blocked) and step:
            # 手順ごとの、束に入った工夫の数と人の数。人は、その場限りの印で数えるだけで、印の値は束に入れない。
            slot = g["craft"].setdefault(step, {"talks": 0, "who": set()})
            slot["talks"] += 1
            who = making_log.clean_who(t.get("who"))
            if who:
                slot["who"].add(who)

    # 動画の札。事前の確かめなしで渡す（本人の方針 11-06）。人が外した札と、機械の候補は入れない。札の文は作る側の読みなので、話した事と同じ入口の床を当てる。
    uploads = {r["id"]: r for r in records.all_records(uploads=True) if r.get("via") == records.UPLOADED}
    for d in trial_video.all_for():
        rid = d.get("record_id")
        if not isinstance(rid, str):  # 札の置き場は人が手で触るファイル。形の外でも束ごと止めない
            continue
        marks = d.get("marks") if isinstance(d.get("marks"), list) else []
        marks = [m for m in marks if isinstance(m, dict) and not m.get("rejected_by") and not str(m.get("read_by") or "").startswith(MACHINE)]
        if not marks:
            continue
        if rid in group_of:  # 手で結んだ記録は、上の試した記録で数えてある。2 重に数えない
            g = _group(groups, *group_of[rid])
        elif rid in uploads and RECORD_ID.fullmatch(rid):
            r = uploads[rid]
            template = making_log._engine(r.get("source_id"), r.get("hypothesis_id"))[0]
            sheet = d.get("engine_sheet") if isinstance(d.get("engine_sheet"), dict) else {}
            if _name(sheet.get("template")) and _name(sheet.get("paper")):
                # 映っている紙が、受付で選ばれた玩具の紙と違う時に、人が決めて札の置き場に書いた紙。エンジンの雛形の id と形の名で、刷った組は持たない
                g = _group(groups, sheet["template"], "", sheet["paper"])
            else:
                g = _group(groups, template, _sheet_set_of(r), _paper(r))
            if r.get("video_kind") != REVIEW:  # 作る前のレビューは作っていないので、報告の数と動きの札に入れない
                g["reports"] += 1
                _count_result(g, r, TEMPLATES.get(template))  # 上げた人が結果を選んだ記録だけ、札に数える。選んでいなければ「わからない」で、どちらにも数えない
            g["record_ids"].append(rid)
        else:
            continue  # 記録が無い（取り下げた・消えた）
        for m in marks:
            step = m.get("step") if isinstance(m.get("step"), int) and not isinstance(m.get("step"), bool) and 1 <= m["step"] <= MAX_STEP else None
            if uploads.get(rid, {}).get("video_kind") == REVIEW:
                # レビューで読んでいるのは紙なので、案内の札（題や組み方の文の読みにくさ）も紙への指摘。聞く口とサイトの話は紙の外
                if m.get("kind") not in REVIEW_OUTSIDE:
                    say(g, REVIEW, _without_seconds(m.get("note")), step, floor=talk_log.blocked)
                continue
            if m.get("kind") in SERVICE_MARKS:
                continue
            craft = m.get("kind") == trial_video.KUFU
            if say(g, "craft" if craft else "stuck", _without_seconds(m.get("note")), step, floor=talk_log.blocked) and step:
                if craft:
                    g["craft"].setdefault(step, {"talks": 0, "who": set()})["talks"] += 1
                else:
                    g["stuck"].setdefault(step, {"taps": 0, "who": set()})["taps"] += 1

    out = []
    for key in sorted(groups):
        g = groups[key]
        quit_steps = {}
        for who_key, n in g["reached"].items():
            if who_key not in g["finished"]:
                quit_steps[n] = quit_steps.get(n, 0) + 1
        out.append({"template": g["template"], "sheet_set": g["sheet_set"], "paper": g["paper"], "reports": g["reports"], "results": g["results"],
                    "moved_word": g["moved_word"], "not_moved_word": g["not_moved_word"],
                    "stuck_steps": {str(n): {"taps": s["taps"], "people": len(s["who"])} for n, s in sorted(g["stuck"].items())},
                    "quit_steps": {str(n): k for n, k in sorted(quit_steps.items())},
                    "craft_steps": {str(n): {"talks": c["talks"], "people": len(c["who"])} for n, c in sorted(g["craft"].items())},
                    "minutes": _span(g["minutes"]), "measures": {k: _span(v) for k, v in sorted(g["measures"].items())},
                    "record_ids": g["record_ids"],
                    "texts": _cap_texts([{"kind": kind, "step": step, "text": text, "count": n}
                              for (kind, step, text), n in sorted(g["texts"].items(), key=lambda kv: (TEXT_KINDS.index(kv[0][0]), kv[0][1] or 0, kv[0][2]))])})
    # 雛形の id が分からない群（記録が壊れている等）は入れない。エンジンの入口が、束ごと断るため。
    out = [g for g in out if g["template"]]
    # 今の刷った組は、群に出てくる雛形の分だけ（記録の無い雛形の名を束に並べない）。組の名を持たない雛形と、形の外の名は入れない。
    current = {}
    for g in out:
        name = _name(getattr(TEMPLATES.get(g["template"]), "SHEET_SET", None))
        if name:
            current[g["template"]] = name
    now = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="minutes")  # 分まで（秒を持たない）
    return {"schema": SCHEMA, "exported_at": now, "from": origin, "dropped_pii": dropped, "current_sets": current, "groups": out}


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
    # エンジンは同じ出し元の束を新しい 1 つだけ数える（束はその時までの全部なので）。置き場（OMOCHAE_DATA）が違う束は、出し元の名を分けないと片方が消える
    ex.add_argument("--from", dest="origin", default=FROM, help="束の出し元の名（英数字と . - _）。置き場が違う束は名を分ける")
    try:
        args = ap.parse_args(argv)
    except SystemExit as e:
        return 0 if e.code == 0 else 4  # 呼び方の誤りは 4（argparse の既定の 2 は使わない）。--help は 0
    try:
        path = out_path(args.out)
        if not NAME.fullmatch(args.origin):
            raise ValueError("束の出し元の名は、英数字と . - _ で 80 字まで")
        bundle = build(args.origin)
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
