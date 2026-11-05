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
  床の限り: 名前そのものは形で見分けられない（「田中です」は落とせない）。だから画面は、字を本人が見てから残す形にし、名前を言わないお願いを出す。
  狭く保つ: 広げるほど、工作の話（「この部品の名前は分からない」「小学校の時に作った」）を落とす。
- 記録の「工夫した所（直した所）」に、話した字がそのまま入る（本人の設計）: 作りながら話した工夫（2）は、その作りの記録を残した時に、
  その記録に結ぶ（bind）。上げた後に残した字（3）は、初めからその記録に結ぶ。記録の側から読む口は kufu。
  字を記録のファイルに写さないのは、記録は 1 回書いたら書き換えない作り（説明・解釈・観察も、記録の番号で結ぶ別のファイル）に合わせるため。
  今ある「直した点」（records の fixes。部品・変えた事・結果の 3 欄）は、そのまま別に残る: 話した字は 3 欄に分けられないので、混ぜない。
- 見せる範囲: 1 の字は作る側の頁だけ。2 と 3 の字は、本人が「ほかの人に見せてよい」を選び（share）、記録に結ばれた物だけを、
  学ぶ人の頁が読める（talks と kufu の shared_only）。既定は見せない。
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
# 記録の「工夫した所（直した所）」に入る場面。1 の考えは仮説に結ぶ物で、記録には入れない。
KUFU_SCENES = ("craft", "keep")
# エンジンへ渡す束で使う、場面の呼び名（Issue #275 で、型紙エンジンの報告の欄と合わせた名）。
WHEN = {"think": "idea", "craft": "making", "keep": "made"}
# どう入れたか。声を字にしたか、字で書いたか。声の口がどれくらい使われるかを見るためで、人を見分ける物ではない。
VIAS = ("voice", "text")
# 残す欄はこれだけ。欄を足す時は、誰が話したかを辿れる物でない事を確かめてからここに足す。
FIELDS = ("source_id", "hypothesis_id", "sheet_version", "template", "sheet_set", "scene", "step", "record_id", "text", "via", "share", "who", "at")

# 名乗りと学校の形。NFKC でそろえた後の字に当てる。どれも短い範囲しか見ない（長い文で遅くならないように）。
NAME_SHAPES = (
    ("名乗り", re.compile(
        r"(?:私|わたし|わたくし|僕|ぼく|俺|おれ|うち|自分)の(?:名前|なまえ|氏名)は"
        # 「この部品の名前は…」を拾わないよう、前が「の」の時と、後ろが問いや「分からない」の時は見ない。
        r"|(?<!の)(?:名前|なまえ|氏名|本名)は(?!何|なに|なん|分か|わか|知ら|しら)[^、。\s]{1,12}?(?:です|だよ|といいます|と言います|と申します)"
        r"|(?:と|って)(?:申します|もうします)"
        r"|(?:私|わたし|わたくし|僕|ぼく|俺|おれ)は[^、。\s]{1,10}?(?:と|って)(?:いい|言い)ます")),
    ("学年と組", re.compile(r"[0-9一二三四五六]\s*年\s*[0-9一二三四五六七八九十A-Za-z]{1,2}\s*組")),
    # 前が漢字か片仮名の続きの時だけ（「私は小学校の時に」「近くの中学校で」は学校の名前ではない）。
    ("学校の名前", re.compile(r"[一-龥ァ-ヶー]{2,8}(?:小学校|中学校|高等学校|高校)")),
)


def blocked(text):
    """入口の床。残さない形があれば、その呼び名（連絡先・名乗り・学年と組・学校の名前）を返す。無ければ空。"""
    if check_pii({"body": text}):
        return "連絡先"
    flat = unicodedata.normalize("NFKC", text)
    return next((name for name, shape in NAME_SHAPES if shape.search(flat)), "")


def _record_of(source_id, record_id):
    return next((r for r in records.all_records(source_id) if r["id"] == record_id), None)


def add(source_id, scene, text, hypothesis_id=None, sheet_version=None, step=None, record_id=None, via="text", share=False, who=""):
    """話した事 1 件を残す。Returns (書いたファイルの path か None, Failure の一覧)。

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
               "via": via if via in VIAS else "text", "share": bool(share) and scene in KUFU_SCENES, "who": making_log.clean_who(who), "at": making_log._now()}
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
    shared_only は学ぶ人の頁とギャラリーのための読み方（記録に結ばれた 2 と 3 の字のうち、本人が見せてよいと選んだ物だけ）。"""
    return [t for t in _all(source_id) if not t.get("dropped") and (scene is None or t.get("scene") == scene)
            and (record_id is None or t.get("record_id") == record_id)
            and (not shared_only or (t.get("scene") in KUFU_SCENES and t.get("record_id") and t.get("share") is True))]


def bind(source_id, hypothesis_id, sheet_version, who, record_id):
    """試した記録を残した時に、その作りの間に話した工夫（2）を、その記録に結ぶ。結んだ数を返す。
    どれが「その作り」か: 同じ玩具・同じ紙（仮説と版）・同じその場限りの印（who）で、まだどの記録にも結んでいない物。
    印が無い時（JS の無い画面）は結ばない: 印なしで結ぶと、ほかの人が話した工夫まで、この記録に入るため。
    書けなくても例外は外へ出さない（記録を残す口を、話した字の都合で止めない）。"""
    who = making_log.clean_who(who)
    d = making_log.folder()
    n = 0
    for p in sorted(d.glob("talk-*.json")) if who and d.exists() else []:
        try:
            t = json.loads(p.read_text(encoding="utf-8"))
            if (t.get("scene") == "craft" and not t.get("record_id") and not t.get("dropped") and t.get("who") == who and t.get("source_id") == source_id
                    and t.get("hypothesis_id") == hypothesis_id and (t.get("sheet_version") or 1) == (sheet_version or 1)):
                store.write_json(p, {**t, "record_id": record_id})
                n += 1
        except (OSError, ValueError, AttributeError):
            continue
    return n


def kufu(source_id, record_id, shared_only=False):
    """その記録の「工夫した所（直した所）」に入っている字。作りながら話した物（手順の番号の順。番号なしは後）、次に、上げた後に残した物。
    Returns [{"when": "making" か "made", "step", "text", "share"}…]。shared_only は学ぶ人の頁とギャラリーのための読み方。"""
    mine = talks(source_id, record_id=record_id, shared_only=shared_only)
    craft = sorted((t for t in mine if t["scene"] == "craft"), key=lambda t: (t.get("step") is None, t.get("step") or 0))
    return [{"when": WHEN[t["scene"]], "step": t.get("step"), "text": t["text"], "share": t.get("share") is True}
            for t in craft + [t for t in mine if t["scene"] == "keep"]]


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
    - records: [{"record_id", "hypothesis_id", "sheet_version", "kufu": kufu() の形}…]（記録ごとの「工夫した所（直した所）」。記録の番号の順）
    - via: {"voice": 声から字にした数, "text": 字で書いた数}・dropped: 床で落とした数"""
    live = talks(source_id)
    craft = {}
    for t in live:
        if t["scene"] == "craft":
            craft.setdefault(t.get("hypothesis_id") or "", {}).setdefault(t.get("sheet_version") or 1, {}).setdefault(t.get("step"), []).append(t["text"])
    by_step = lambda ss: dict(sorted(ss.items(), key=lambda kv: (kv[0] is None, kv[0] or 0)))  # 手順の番号の順。番号なしは最後
    tied = {}
    for t in live:
        if t["scene"] in KUFU_SCENES and t.get("record_id"):
            tied.setdefault(t["record_id"], t)
    return {"think": [{"hypothesis_id": t.get("hypothesis_id"), "text": t["text"]} for t in live if t["scene"] == "think"],
            "craft": {h: {v: by_step(ss) for v, ss in sorted(vs.items())} for h, vs in sorted(craft.items())},
            "records": [{"record_id": rid, "hypothesis_id": t.get("hypothesis_id"), "sheet_version": t.get("sheet_version"), "kufu": kufu(source_id, rid)}
                        for rid, t in sorted(tied.items())],
            "via": {v: sum(1 for t in live if t.get("via") == v) for v in VIAS}, "dropped": dropped(source_id)}
