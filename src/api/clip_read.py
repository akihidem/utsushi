"""カメラの区切りの中身を字にする段（声とカメラの区切りの設計 3 版の 5 節・本人 11-08 330「カメラ映像、音声はサーバーに送られて解析して
型紙とエンジンの改善に使う。文字、メタ情報化されて削除される。」・412「解析につかう」・415「カメラの映像は、押した時の短い区切りだけ。」）。

音の無い区切りは、字にしてから消すだけでは付帯情報しか残らない。区切りから 3 コマを取り、上げた動画の観察（api.observe）と同じ係
（見えた事・見えなかった事だけ・成否や上手下手は書かない）に、手順と釦の付帯情報を添えて見せる。答えは「案」で、人が確かめるまで根拠にしない。

判断の芯:
- **きっかけは人の操作の 1 回だけ**（常駐しない・CLAUDE.md）。合言葉付きの場は「承認」で区切りが届いた時（受け口が 1 回だけ呼ぶ）。
  公開の場（合言葉なし）は学ぶ人の操作では読まない（J-028）。進め役が media_review の命令の道で「写っている人なし」を確かめた時だけ読む
  （自分で押す「大人の手元だけ」の印は確かめの代わりにしない・別の目の (6)）。
- **人の言葉が先（J-013）**: のこすの記入の「工夫・感想」を人の説明と数える（統括の決め 11-08・欄は足さない）。感想と工夫の行は
  words_review.has_words と同じ見方で見て、のこすの工夫の字（記録に結んだ話した字の craft）もここで数える。どちらも空なら読まない。
- **費用**: budget.check（日割り・累計・1 回の上限）を必ず通す。最悪の見込みは observe と同じ 1 枚 1,600 トークン（縦の画面のコマで
  越えないため・統括の決め）。学ぶ人の質問と読みを食わないよう、区切りの読みだけの 1 日の回数の止め（CLIP_DAILY）を置き、台帳の role で数える。
- **読めない時は消さずに理由を控える**（voice_text.clip_wait）。72 時間を過ぎたら声の担当の掃除（sweep_clips）が読まずに消し、理由を印に残す。
- **床**: 答えに人が写っている（手の外の体・顔）と出たら、字を残さず区切りごと消す（voice_text.clip_drop）。成否や点の言葉が入った答えは出さない。
- 鍵が無い（本物の API を呼ばない場）では読まずに待つ（J-023）。
"""
import base64
import json
import os
import threading
import time

from omochae import loop, records, store, talk_log, voice_text, words_review
from omochae.marks import without_premise

from . import budget, config, observe

ROLE = "clip"  # 台帳の役の名。区切りの読みの 1 日の回数を数える
# 観察の字に、人の体や顔を言う語が入っていたら残さない（person の欄の見張りと重ねる床・別の目の止め 1）。
# 「顔」は虎の顔のような玩具の顔でも当たるが、消す側へ倒す（人の写った物を案として残すより、読み直さずに消す方を採る）
PERSON_WORDS = ("顔", "人物", "人の体", "人が写", "子ども", "子供", "髪")
READING_STALE = 600  # 読みの印が 10 分を過ぎたら、前の読みが落ちた物と見る（印が残って二度と読めなくならないように）
CLIP_DAILY = 40  # 区切りの読みだけの 1 日の回数の止め（推し・本人の答え待ち。替える時はここだけ）
SYSTEM = (observe.SYSTEM + "\n今回のコマは、作っている人が「ここで止まった」を押した後の 10 秒の動画から取った物です。"
          "手と紙がどうなっているか（どの部品をどう持ち、どこが折れず・貼れずに止まっているか）を見えたとおりに書きます。"
          "手の外の体や顔が写っているかどうかだけを、person に true か false で書きます。")


def _path(rid):
    return loop.folder() / f"clip-observation-{rid}.json"


def _meta_path(rid):
    return loop.folder() / f"clip-meta-{rid}.json"


def observations(rid):
    """その記録の区切りの読み（案）の並び。"""
    return (store.read_json_or_skip(_path(rid)) or {}).get("clips", [])


def save_meta(rid, name, step=None, button=None):
    """区切りの付帯情報（どの手順・どの釦）。受け口が受けた時に控え、読む時に係へ添える。字の中身は持たない。
    読んで書き直す形なので錠の中で（同時に 2 つ届いても、片方の控えが欠けないように・別の目の気づき）。"""
    with store.locked(loop.folder()):
        p = _meta_path(rid)
        meta = store.read_json_or_skip(p) or {}
        meta[name] = {"step": step, "button": button}
        store.write_json(p, meta)


def count_today():
    """今日、区切りを読んだ回数（台帳の role で数える。別の帳面を作らない）。"""
    path = budget._path()
    if not path.exists():
        return 0
    today = budget._today()
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
               and (row := json.loads(line)).get("role") == ROLE and row.get("day") == today)


def told_first(rid):
    """人の言葉が先か: 記録の感想か工夫の行（words_review.has_words）か、記録に結んだ工夫の話した字（のこすの記入の工夫）がある。"""
    rec = store.read_json_or_skip(records.folder() / f"{rid}.json")
    if not rec:
        return False
    if words_review.has_words(rec):
        return True
    return any(t["when"] == "making" and t["text"].strip() for t in talk_log.kufu(rec["source_id"], rid))


def _claim(rid, name):
    """同じ区切りを 2 回読まない印（受け口の読みと進め役の approve が重なった時・別の目の気づき）。印を取れたら True。
    印は別のプロセスとも取り合うファイル（O_EXCL）。読みが落ちて残った古い印（10 分過ぎ）は取り直す。"""
    p = loop.folder() / f"clip-reading-{rid}-{name}"
    try:
        if p.exists() and time.time() - p.stat().st_mtime > READING_STALE:
            p.unlink(missing_ok=True)
        os.close(os.open(p, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600))
        return True
    except FileExistsError:
        return False


def _release(rid, name):
    (loop.folder() / f"clip-reading-{rid}-{name}").unlink(missing_ok=True)


def read(rid, name, client):
    """1 つの区切りを読む。Returns (結果 or None, 読まなかった理由)。読めなかった時は理由を控え、区切りは残す（72 時間で掃除）。"""
    if name not in voice_text.clips_waiting(rid):
        return None, "区切りが無い"
    if not _claim(rid, name):
        return None, "読んでいる途中"
    try:
        return _read(rid, name, client)
    finally:
        _release(rid, name)


def _read(rid, name, client):
    """read の中身（印を取った後）。印を取る間に別の読みが済ませていたら読まない。"""
    if name not in voice_text.clips_waiting(rid):
        return None, "区切りが無い"

    def wait(why):
        voice_text.clip_wait(rid, name, why)
        return None, why

    if not told_first(rid):
        return wait("説明待ち")
    from . import ask

    if not ask._key_present():
        return wait("鍵が無い")
    if count_today() >= CLIP_DAILY:
        return wait("今日の上限")
    imgs = observe.frames(voice_text.voice_dir(rid) / name)
    if not imgs:
        return wait("コマが取れない")
    meta = (store.read_json_or_skip(_meta_path(rid)) or {}).get(name, {})
    about = ("手順 " + str(meta["step"]) + " で押した区切り。" if meta.get("step") else "")
    content = [{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": base64.b64encode(b).decode()}} for b in imgs]
    content.append({"type": "text", "text": about + "この 3 コマで見えた事を、決まった形の JSON だけで返してください: "
                                                  "{\"observed\": [...], \"unclear\": [...], \"person\": true か false}"})
    try:
        budget.check(0.0, budget.worst_case(config.MODELS["observe"], 3 * 1600 + 400, config.ASK_MAX_TOKENS))
    except budget.BudgetStop as e:
        return wait(e.note)
    r = client.messages.create(model=config.MODELS["observe"], max_tokens=config.ASK_MAX_TOKENS, system=SYSTEM,
                               messages=[{"role": "user", "content": content}], thinking={"type": "adaptive"}, output_config={"effort": config.EFFORT["observe"]})
    usage = getattr(r, "usage", None)
    budget.add(ROLE, config.MODELS["observe"], getattr(usage, "input_tokens", 0) or 0, getattr(usage, "output_tokens", 0) or 0)
    text = "".join(getattr(b, "text", "") for b in r.content if getattr(b, "type", "") == "text").strip()
    try:
        result = json.loads(text[text.index("{"): text.rindex("}") + 1])
    except ValueError:
        return wait("答えの形が読めない")
    # 床: 人が写っていないと答えが言い切った時（person が真偽の値の false）だけ残す。欄が無い・字の "true"・true は、
    # 字を残さず区切りごと消す（設計 5 節・別の目の止め 1: 答えの形しだいで床が効かなかった）
    if result.get("person") is not False:
        voice_text.clip_drop(rid, name, "人が写っていた" if result.get("person") is True else "人の見分けの答えが無い")
        return None, "人が写っていた" if result.get("person") is True else "人の見分けの答えが無い"
    if not isinstance(result.get("observed"), list) or not isinstance(result.get("unclear"), list):
        return wait("答えの形が違う")
    if any(w in " ".join(map(str, result["observed"] + result["unclear"])) for w in PERSON_WORDS):
        voice_text.clip_drop(rid, name, "観察の字に人の体や顔の語")
        return None, "観察の字に人の体や顔の語"
    if any(w in without_premise(" ".join(map(str, result["observed"] + result["unclear"]))) for w in observe.BANNED):
        return wait("成否や点の言葉が入っていた")
    p = _path(rid)
    doc = store.read_json_or_skip(p) or {"record_id": rid, "clips": []}
    doc["clips"].append({"clip": name, "step": meta.get("step"), "button": meta.get("button"), "observed": result["observed"],
                         "unclear": result["unclear"], "by": "claude", "label": "案（Claude の補助・人が確かめるまで根拠にしない）", "at": loop._now()})
    loop._write(p, doc)
    voice_text.clip_done(rid, name)
    return result, ""


def read_later(rid, name, client_factory):
    """受け口から 1 回だけ呼ぶ: 区切りの読みを別の糸で走らせ、受け口の返事を待たせない（読みは 1 回の API の呼び出しで、数十秒かかりうる）。
    常駐しない（この 1 つを読んだら終わる）。試験では client_factory に偽の係を渡し、返る糸を join して待つ。"""
    def run():
        from . import ask

        try:
            # 鍵が無い場では係を作らない（作る時に鍵を読みに行って落ちるため）。read が「鍵が無い」と控える
            read(rid, name, client_factory() if ask._key_present() else None)
        except Exception as e:  # 読みが落ちても受け口は答え済み。理由を控えて 72 時間の掃除に任せる
            voice_text.clip_wait(rid, name, f"読めなかった（{type(e).__name__}）")

    t = threading.Thread(target=run, daemon=True)
    t.start()
    return t
