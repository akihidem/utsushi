"""話した事の記録（一周の声の部分。本人の決定 2026-11-05、Issue #279）。

本人の描く一周: 1 作る前に、AI の仮説を見ながら自分の考えを話す。2 作りながら、工夫などを話す。3 できた物を上げた後に、工夫した点や考えを残す。
決まり（同じ日）: 声そのものは残さない。個人の情報は入口で落とす。

設計の芯:
- ここに届くのは字だけ。声を字にするのは画面の側（web/hanasu.py）で、受け口は字のフォームしか受けない。声・映像・写真はこの置き場に入らない。
- 置き場は工作の様子と同じ（making_log.folder()。git の外）で、出来事の種類を 1 つ足す（talk-…）。時刻とファイルの名前の決まり（分まで）も同じ物を使う。
  同じ字を 2 か所に持たない: 3 の字も試した記録には写さず、記録の番号で結ぶ。
- 残す欄は FIELDS だけ（tests/test_hanasu.py が鍵の一致を見る）。IP・ブラウザの名・cookie・名前・声は残さない。
- 入口の床（blocked）: 連絡先の形（持ち寄り・記録・聞く口と同じ contrib.check_pii）に、名乗りの形・学年と組の形・学校の名前の形を足す。
  なぜ足すか: 話す時は書く時より名乗りやすい（「○○と申します」「3 年 2 組の…」）。当たった文は残さず、落とした事だけを数える（dropped）。
  床の限り: 名前そのものは形で見分けられない（「田中です」「田中といいます」は落とせない。「谷折りといいます」と同じ形のため）。
  ひらがなだけの学校の名前（「さくら小学校で作った」）と、学年だけの言い方（「中 3」）も落とせない。
  だから画面は、字を本人が見てから残す形にし、名前を言わないお願いを出す。
  狭く保つ: 広げるほど、工作の話（「この部品の名前は分からない」「小学校の時に作った」「当時小学校で作った」）を落とす。
- 記録の「工夫した所（直した所）」に、話した字がそのまま入る（本人の設計）: 作りながら話した工夫（2）と、仮説を見て話した考え（1）は、
  その作りの記録を残した時に、その記録に結ぶ（bind）。上げた後に残した字（3）は、初めからその記録に結ぶ。記録の側から読む口は kufu。
  字を記録のファイルに写さないのは、記録は 1 回書いたら書き換えない作り（説明・解釈・観察も、記録の番号で結ぶ別のファイル）に合わせるため。
  今ある「直した点」（records の fixes。部品・変えた事・結果の 3 欄）は、そのまま別に残る: 話した字は 3 欄に分けられないので、混ぜない。
- 見せる範囲（本人の決定 11-05）: 記録に結んだ字は、記録の感想などと同じに、ほかの人の頁に文で出す（talks と kufu の shared_only が、
  学ぶ人の頁とギャラリーのための読み方）。名前は機械で落とせないので、入れないお願いの文で頼む（画面の断り。web/hanasu.py）。
  記録に結ぶ前の字（考えと工夫）は、学ぶ人の頁に出さない（出す札が無い。作る側の頁だけ）。
  出す時に、入口の床をもう一度当てる（床を広げる前に残した字や、手で置いた字のため）。
  作る側が読んで名前などに気づいた時は、その記録の字を、消さずに隠せる（set_share。記録ごと消すのは records.withdraw）。
- 読む口は 3 つ: texts（輪と束が読む。渡してよい物だけを、印を外した欄で返す）・kufu（記録の札が読む。その記録に結んだ字）・
  talks（作る側の頁と集計が読む。出来事そのまま）。
- 記録を取り下げたら、結んだ字も消す（drop_for_record。records.withdraw が呼ぶ）。
- 字を残す事がこの口の用事なので、残せなかった時は理由を返す（making_log.add_ask は黙って捨てるが、ここは本人に知らせる）。例外は外へ出さない。
"""
import json
import re
import unicodedata

from . import making_log, records, store
from .contrib import check_pii
from .model import Failure

MAX_TEXT = 400
EMPTY = "話した事が空"
# 場面。1 考え（仮説を見て）・2 工夫（作りながら）・3 できた物（上げた後）。
SCENES = ("think", "craft", "keep")
# 工夫の場面（作りながら・上げた後）。1 の考えも記録に結ぶが、工夫ではないので、札では「考え」と分けて出す。
KUFU_SCENES = ("craft", "keep")
# エンジンへ渡す束で使う、場面の呼び名（Issue #275 で、型紙エンジンの報告の欄と合わせた名）。
WHEN = {"think": "idea", "craft": "making", "keep": "made"}
# どう入れたか。声を字にしたか、字で書いたか。声の口がどれくらい使われるかを見るためで、人を見分ける物ではない。
VIAS = ("voice", "text")
# 残す欄はこれだけ。欄を足す時は、誰が話したかを辿れる物でない事を確かめてからここに足す。
FIELDS = ("source_id", "hypothesis_id", "sheet_version", "template", "sheet_set", "scene", "step", "record_id", "text", "via", "share", "who", "at")

# 輪と束が読む口（texts）が返す欄。その場限りの印・見せる印・声か字かは入れない（輪や束や外の API へ運ばせないため）。
TEXT_KEYS = ("source_id", "hypothesis_id", "sheet_version", "template", "sheet_set", "scene", "step", "record_id", "text", "at")

# 名乗りと学校の形。NFKC でそろえた後の字に当てる。どれも短い範囲しか見ない（長い文で遅くならないように）。
NAME_SHAPES = (
    ("名乗り", re.compile(
        r"(?:私|わたし|わたくし|僕|ぼく|俺|おれ|うち|自分)の(?:名前|なまえ|氏名)は"
        # 「この部品の名前は…」を拾わないよう、前が「の」の時と、後ろが問いや「分からない」の時は見ない。
        r"|(?<!の)(?:名前|なまえ|氏名|本名)は(?!何|なに|なん|分か|わか|知ら|しら)[^、。\s]{1,12}?(?:です|だよ|といいます|と言います|と申します)"
        r"|(?:と|って)(?:申します|もうします)"
        r"|(?:私|わたし|わたくし|僕|ぼく|俺|おれ)は[^、。\s]{1,10}?(?:と|って)(?:いい|言い)ます"
        # 「○○小学校の田中です」の形（学校の名前がひらがなでも当たる）。「小学校の時です」「小学校の図工です」は名乗りではない。
        r"|(?:小学校|中学校|高等学校|高校)の(?!時|頃|ころ|とき|図工|授業|工作|宿題|先生|教科書|思い出)[^、。\s]{1,10}?(?:です|だよ|といいます|と言います|と申します)")),
    ("学年と組", re.compile(r"[0-9一二三四五六]\s*年\s*[0-9一二三四五六七八九十A-Za-z]{1,2}\s*組")),
)
# 学校の名前の形: 前が漢字か片仮名の続きの時だけ（「私は小学校の時に」「近くの中学校で」は学校の名前ではない）。1 字の名前（東小学校・南中学校）も当てる。
SCHOOL = re.compile(r"([一-龥ァ-ヶー]{1,8})(?:小学校|中学校|高等学校|高校)")
# 学校の前に来ても、名前ではない言葉（声から字にした文は、助詞が抜けやすい。「当時小学校で作った」「私立中学校の文化祭で見た」）。
NOT_SCHOOL_NAMES = frozenset(("昔", "当時", "以前", "地元", "近所", "私", "僕", "俺", "今", "元", "同", "各", "某",
                              "国立", "公立", "私立", "都立", "道立", "府立", "県立", "市立", "区立", "町立", "村立"))


def blocked(text):
    """入口の床。残さない形があれば、その呼び名（連絡先・名乗り・学年と組・学校の名前）を返す。無ければ空。"""
    if check_pii({"body": text}):
        return "連絡先"
    flat = unicodedata.normalize("NFKC", text)
    hit = next((name for name, shape in NAME_SHAPES if shape.search(flat)), "")
    if not hit and any(m.group(1) not in NOT_SCHOOL_NAMES for m in SCHOOL.finditer(flat)):
        hit = "学校の名前"
    return hit


def _record_of(source_id, record_id):
    return next((r for r in records.all_records(source_id) if r["id"] == record_id), None)


def add(source_id, scene, text, hypothesis_id=None, sheet_version=None, step=None, record_id=None, via="text", who=""):
    """話した事 1 件を残す。Returns (書いたファイルの path か None, Failure の一覧)。
    見せる印（share）は、ここでは受けない: 記録に結んだ字は、ほかの人の頁に出す決まり（本人の決定 11-05）。上げた後に残す字（keep）は、
    初めから記録に結ぶので、初めから出す。考えと工夫は、記録に結んだ時に出す（bind）。

    3（keep）は試した記録に結ぶ: 仮説と版は記録の値を使う（画面の値を信じない）。2（craft）は刷った紙の仮説が要る。1（think）は仮説を選ばなくてよい。
    床に落ちた文は残さず、落とした事だけを書く（path は None、Failure は F10.pii）。
    """
    try:
        text = " ".join(str(text or "").split())[:MAX_TEXT]
        if scene not in SCENES:
            return None, [Failure("F3.result", "scene", "場面は 考え・工夫・できた物 のどれか")]
        if not text:
            return None, [Failure("F3.result", "text", EMPTY)]
        if scene == "keep":
            rec = _record_of(source_id, record_id)
            if rec is None:
                return None, [Failure("F8.references", "record_id", f"記録 {record_id} は無い")]
            hypothesis_id, sheet_version = rec["hypothesis_id"], rec.get("sheet_version", 1)
        else:
            record_id = None
            if hypothesis_id and not records.known_hypothesis(source_id, hypothesis_id):
                return None, [Failure("F8.references", "hypothesis_id", f"仮説 {hypothesis_id} は実在しない")]
            if scene == "craft" and not hypothesis_id:
                return None, [Failure("F8.references", "hypothesis_id", "どの紙を作っているかが要る")]
        template, sheet_set = making_log._engine(source_id, hypothesis_id)
        out = {"source_id": source_id, "hypothesis_id": hypothesis_id or None, "sheet_version": sheet_version, "template": template, "sheet_set": sheet_set,
               "scene": scene, "step": making_log._step_no(step) if scene == "craft" else None, "record_id": record_id, "text": text,
               "via": via if via in VIAS else "text", "share": scene == "keep", "who": making_log.clean_who(who), "at": making_log._now()}
        shape = blocked(text)
        if shape:
            # 文は残さない。見せてよいの印も落とす（残す文が無い）。どの床で落ちたかは、床が効いているかを見るために残す。
            out.update(text="", share=False, dropped="pii" if shape == "連絡先" else "name")
            making_log._write("talk", out)
            return None, [Failure("F10.pii", "text", f"{shape}の形がある")]
        return making_log._write("talk", out), []
    except Exception as e:
        return None, [Failure("F3.result", "text", f"残せなかった（{type(e).__name__}）")]


def _all(source_id=None):
    return making_log._read("talk", source_id)


def talks(source_id=None, scene=None, record_id=None, shared_only=False):
    """残した話（分の順）。床で落とした物は入れない。取り下げた記録に結んだ物は drop_for_record が消しているので、ここでは見ない。
    shared_only は学ぶ人の頁とギャラリーのための読み方: 記録に結ばれ、作る側が隠していず、入口の床に当たらない物だけ。"""
    return [t for t in _all(source_id) if not t.get("dropped") and (scene is None or t.get("scene") == scene)
            and (record_id is None or t.get("record_id") == record_id)
            and (not shared_only or (t.get("record_id") and t.get("share") is True and not blocked(t.get("text", ""))))]


def texts(source_id=None, scene=None, hypothesis_id=None, sheet_version=None, record_id=None, who=None):
    """輪と束が読む口: 玩具・紙（仮説と版）・場面・記録で絞って、話した字を返す。Returns [{TEXT_KEYS の欄}…]（分の順）。
    本人の描く 4 つのループ（Issue #335）は、どれもここを読む: 考え（think）から紙・工夫（craft）から型紙の直し・束・上げた後の話（keep）。
    返すのは、輪や束へ渡してよい物だけ: 床で落とした物・作る側が隠した物（記録に結んだ後に share を外した物）・入口の床にもう一度当たる物は入れない。
    記録に結ぶ前の字（考え・工夫）も入る（考えから紙を作る時は、記録がまだ無い）。
    絞り方: どの引数も、渡した時だけ絞る（同じ値の物だけ）。考えは仮説を選ばずに話した物があり、その hypothesis_id は None。
    who はその場限りの印で、絞るためだけに受ける（その画面で話した字だけを読む時）。返す欄には入れない。"""
    who = making_log.clean_who(who) if who is not None else None
    out = []
    for t in _all(source_id):
        if t.get("dropped") or (t.get("record_id") and t.get("share") is not True) or blocked(t.get("text", "")):
            continue
        if ((scene is not None and t.get("scene") != scene) or (hypothesis_id is not None and t.get("hypothesis_id") != hypothesis_id)
                or (sheet_version is not None and t.get("sheet_version") != sheet_version) or (record_id is not None and t.get("record_id") != record_id)
                or (who is not None and (not who or t.get("who") != who))):
            continue
        out.append({k: t.get(k) for k in TEXT_KEYS})
    return out


def _made_from(source_id, hypothesis_id):
    """その案（OWN-n）を作った元の考えのファイルの名前。話した考えから作った案でなければ None。"""
    if not str(hypothesis_id).startswith("OWN-"):
        return None
    from . import loop

    for p in sorted(loop.folder().glob("words-*.json")):
        w = store.read_json_or_skip(p)
        if w and w.get("own_id") == hypothesis_id and w.get("source_id") == source_id:
            return w.get("from_talk")
    return None


def bind(source_id, hypothesis_id, sheet_version, who, record_id):
    """試した記録を残した時に、その作りの間に話した工夫（2）と考え（1）を、その記録に結ぶ。Returns (結んだ工夫の数, 結んだ考えの数)。
    どれが「その作り」か: 同じ玩具・同じその場限りの印（who）で、まだどの記録にも結んでいない物。
    工夫は、同じ紙（仮説と版）の物。考えは、同じ仮説か、仮説を選ばずに話した物（考えは作る前の話なので、版は見ない）。
    印が無い時（JS の無い画面）は結ばない: 印なしで結ぶと、ほかの人が話した事まで、この記録に入るため。
    話した考えから作った案（OWN-n）の紙の記録には、その元の考えも結ぶ。考えはたたき台を見て話した物でたたき台に付いたままなので、案の紙の記録と仮説が合わない（ループ1、#335）。
    結んだ字には、見せる印を付ける（記録に結んだ字は、記録の感想などと同じに、ほかの人の頁に出す。本人の決定 11-05）。
    書けなくても例外は外へ出さない（記録を残す口を、話した字の都合で止めない）。"""
    who = making_log.clean_who(who)
    d = making_log.folder()
    n = {"craft": 0, "think": 0}
    made_from = _made_from(source_id, hypothesis_id)
    for p in sorted(d.glob("talk-*.json")) if who and d.exists() else []:
        try:
            t = json.loads(p.read_text(encoding="utf-8"))
            if t.get("record_id") or t.get("dropped") or t.get("who") != who or t.get("source_id") != source_id:
                continue
            same_paper = t.get("hypothesis_id") == hypothesis_id and (t.get("sheet_version") or 1) == (sheet_version or 1)
            if (t.get("scene") == "craft" and same_paper) or (t.get("scene") == "think" and (t.get("hypothesis_id") in (None, hypothesis_id) or p.stem == made_from)):
                store.write_json(p, {**t, "record_id": record_id, "share": True})
                n[t["scene"]] += 1
        except (OSError, ValueError, AttributeError):
            continue
    return n["craft"], n["think"]


def kufu(source_id, record_id, shared_only=False):
    """その記録に結んだ字。仮説を見て話した考え、作りながら話した工夫（手順の番号の順。番号なしは後）、上げた後に残した物、の順。
    Returns [{"when": "idea"・"making"・"made" のどれか, "step", "text", "share"}…]。shared_only は学ぶ人の頁とギャラリーのための読み方
    （作る側が隠していず、入口の床に当たらない物だけ）。"""
    mine = talks(source_id, record_id=record_id, shared_only=shared_only)
    craft = sorted((t for t in mine if t["scene"] == "craft"), key=lambda t: (t.get("step") is None, t.get("step") or 0))
    return [{"when": WHEN[t["scene"]], "step": t.get("step"), "text": t["text"], "share": t.get("share") is True}
            for t in [t for t in mine if t["scene"] == "think"] + craft + [t for t in mine if t["scene"] == "keep"]]


def set_share(source_id, record_id, on):
    """作る側の道具: その記録に結んだ字を、ほかの人の頁から隠す（on=False）・戻す（on=True）。Returns (変えた数, Failure の一覧)。
    なぜ要るか: 名前は機械で落とせない。作る側が読んで気づいた時に、字を消さずに、学ぶ人の頁から外せるように。画面からは呼ばない。
    床で落とした出来事（文が無い）には触らない。"""
    d = making_log.folder()
    mine = []
    for p in sorted(d.glob("talk-*.json")) if d.exists() else []:
        try:
            t = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(t, dict) and t.get("record_id") == record_id and t.get("source_id") == source_id and not t.get("dropped"):
            mine.append((p, t))
    if not mine:
        return 0, [Failure("F8.references", "record_id", f"記録 {record_id} に結んだ字は無い")]
    n = 0
    for p, t in mine:
        if (t.get("share") is True) != bool(on):
            try:
                store.write_json(p, {**t, "share": bool(on)})
                n += 1
            except OSError:
                return n, [Failure("F3.result", "share", "書けなかった")]
    return n, []


def dropped(source_id=None):
    """床で落とした数。{"pii": 連絡先の形, "name": 名乗りと学校の形}。文は残っていない。"""
    out = {"pii": 0, "name": 0}
    for t in _all(source_id):
        if t.get("dropped") in out:
            out[t["dropped"]] += 1
    return out


def drop_for_record(record_id):
    """記録の取り下げと一緒に、結んだ字を消す。消したファイルの名前を返す。人の言葉を、取り下げた記録の外に残さないため。"""
    gone = []
    d = making_log.folder()
    for p in sorted(d.glob("talk-*.json")) if d.exists() else []:
        try:
            if json.loads(p.read_text(encoding="utf-8")).get("record_id") == record_id:
                p.unlink()
                gone.append(f"making/{p.name}")
        except (OSError, ValueError):
            continue
    return gone


def summary(source_id):
    """作る側が読む集計。学ぶ人の画面には出さない。場面ごとに字を並べるだけで、多い順や点の形は作らない（J-025）。
    - think: [{"hypothesis_id", "text"}…]（1 考え。仮説を選ばなかった物は None）
    - craft: {仮説: {版: {手順（無ければ None）: [字…]}}}（2 工夫。手順の番号は仮説ごとに別の文なので、仮説と版で分ける。記録に結んだ物も入る）
    - records: [{"record_id", "hypothesis_id", "sheet_version", "kufu": kufu() の形}…]（記録ごとに結んだ字。考えも入る。記録の番号の順）
    - via: {"voice": 声から字にした数, "text": 字で書いた数}・dropped: 床で落とした数"""
    live = talks(source_id)
    craft = {}
    for t in live:
        if t["scene"] == "craft":
            craft.setdefault(t.get("hypothesis_id") or "", {}).setdefault(t.get("sheet_version") or 1, {}).setdefault(t.get("step"), []).append(t["text"])
    by_step = lambda ss: dict(sorted(ss.items(), key=lambda kv: (kv[0] is None, kv[0] or 0)))  # 手順の番号の順。番号なしは最後
    tied = {}
    for t in live:
        rid = t.get("record_id")
        # 仮説と版は、工夫か上げた後の字から読む（考えは、仮説を選ばずに話した物がある）。それが無い記録だけ、考えの値を使う。
        if rid and (rid not in tied or (t["scene"] in KUFU_SCENES and tied[rid]["scene"] not in KUFU_SCENES)):
            tied[rid] = t
    return {"think": [{"hypothesis_id": t.get("hypothesis_id"), "text": t["text"]} for t in live if t["scene"] == "think"],
            "craft": {h: {v: by_step(ss) for v, ss in sorted(vs.items())} for h, vs in sorted(craft.items())},
            "records": [{"record_id": rid, "hypothesis_id": t.get("hypothesis_id"), "sheet_version": t.get("sheet_version"), "kufu": kufu(source_id, rid)}
                        for rid, t in sorted(tied.items())],
            "via": {v: sum(1 for t in live if t.get("via") == v) for v in VIAS}, "dropped": dropped(source_id)}
