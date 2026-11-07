"""手帖の鍵の「しおり」の台帳（本人の決め 11-08: 手帖の鍵は「しおり」・「しおりに書いてある絵を押す」・しおりそのものが鍵の形で
「この形でよい」・QR の行き先は「決まった番地を用意する」・QR の見た目は「A 朱の落款枠に朱」）。設計は UX の担当の
grove の state/techo-card-20261108/README.md の 2″・2‴・6（別の目の検品 3 回）。

判断の芯:
- QR は道だけ（<決まった番地>/s/<印>）。印は 22 字のでたらめ（128 ビット）。台帳は印そのものを持たず、印のハッシュで探す。
- 押す順（しおりに刷った 9 つの絵から 3 つ・しおりごとにでたらめ・裏に朱の順の印）は台帳に持たず、サーバの秘密の値・印・順の
  HMAC だけを持つ。置き場だけが漏れても、印も秘密の値も無いので順をたどれない。
- しおりそのものが鍵（拾った人は開ける・本人の決め）。QR だけを見た人の当て続けは、3 つの止めで抑える:
  ① 同じしおりに 10 分で 5 回まで（時間の止め・しおりごと。止めの間は数えない）
  ② 同じ相手の外れの合計 10 回で、そのしおりを使えなくする（相手ごとに数えるので、別々の相手が外しても使えなくはならない）
  ③ しおりごとの外れの合計 50 回でしおりを止め、進め役への知らせを 1 つ残す（別々の相手から少しずつ当て切るのを止める）
  相手は秘密の値と組にしたハッシュで持ち、番地そのものは持たない。
- 決まった番地が無い時は、しおりを作らない（立てるたびに替わる一時のトンネルの番地を刷ると、後で開かなくなるため）。
- 名前・学校・連絡先は持たない。記録を取り下げると、しおりの並びからもその番号を消す（drop_record）。
- 開いた画面の cookie・「とじる」・さわらない 20 分で切れる形は、開く道（web の側）が受け持つ。ここは last_used と fresh だけを持つ。
- 作る道具（QR の絵と紙）は別の PR。ここは番地が決まる前から作れる台帳だけ（統括の段取り 11-08）。
"""
import hashlib
import hmac
import json
import os
import re
import secrets
import time

from . import loop, store

BASE_ENV = "OMOCHAE_SHIORI_BASE"  # 決まった番地（https の頭・末の / なし）。設定の値で渡し、コードに書かない
WINDOW, WINDOW_TRIES = 600, 5     # ① 同じしおりに 10 分で 5 回まで
PEER_FAILS = 10                   # ② 同じ相手の外れの合計で使えなくする
TOTAL_FAILS = 50                  # ③ しおりごとの外れの合計で止めて知らせる
IDLE = 1200                       # さわらない 20 分で切れる（共用の iPad の次の人へ渡らないように）
PICTURES = 9                      # しおりに刷る玩具の小さな絵の数（どの絵かは紙の版の PR で決める）
ORDER = 3                         # 押す数
TOKEN = re.compile(r"[A-Za-z0-9_-]{22}")
# 替わる番地（立てるたびに名前が替わる一時のトンネル）。しおりに刷らない
CHANGING = ("trycloudflare.com", "localhost", "127.0.0.1")


class NoBase(RuntimeError):
    """決まった番地が設定されていない（しおりを作らない）。"""


def base_url():
    """決まった番地。無い・https でない・替わる番地の時は None（しおりを作らない）。"""
    b = os.environ.get(BASE_ENV, "").strip().rstrip("/")
    if not re.fullmatch(r"https://[a-z0-9.-]+(?::\d+)?", b) or any(c in b for c in CHANGING):
        return None
    return b


def folder():
    d = loop.base() / "shiori"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _secret():
    """サーバの秘密の値（git の外の置き場・持ち主だけが読める）。無ければ 1 度だけ作る。"""
    p = folder() / ".secret"
    if not p.exists():
        try:
            store.write_atomic(p, secrets.token_bytes(32), exclusive=True, mode=0o600)
        except FileExistsError:
            pass
    return p.read_bytes()


def _name(token):
    return hashlib.sha256(token.encode()).hexdigest() + ".json"


def _seal(token, order):
    return hmac.new(_secret(), (token + ":" + ",".join(str(int(i)) for i in order)).encode(), hashlib.sha256).hexdigest()


def _peer(peer):
    return hmac.new(_secret(), ("peer:" + str(peer)).encode(), hashlib.sha256).hexdigest()[:24]


def _path(token):
    return folder() / _name(token) if isinstance(token, str) and TOKEN.fullmatch(token) else None


def _load(token):
    p = _path(token)
    return (p, store.read_json_or_skip(p)) if p else (None, None)


def make(records=(), now=None):
    """しおりを 1 つ作る。{"token", "order", "url"}（order は 9 つの絵の番号 0〜8 から 3 つの順）。決まった番地が無ければ NoBase。
    token と order は作った時にだけ返し、台帳には残さない（紙に刷るのはこの時だけ）。"""
    base = base_url()
    if not base:
        raise NoBase("決まった番地が無いので、しおりを作りません（設定 " + BASE_ENV + "）")
    now = time.time() if now is None else now
    token = secrets.token_urlsafe(16)  # 22 字・128 ビット
    rng = secrets.SystemRandom()
    order = tuple(rng.sample(range(PICTURES), ORDER))
    entry = {"seal": _seal(token, order), "records": [str(r) for r in records], "made_at": now, "last_used": None,
             "tries": [], "fails": 0, "peer_fails": {}, "revoked": False, "stopped": False}
    with store.locked(folder()):
        store.write_json(folder() / _name(token), entry, exclusive=True)
    return {"token": token, "order": order, "url": f"{base}/s/{token}"}


def check(token, order, peer, now=None):
    """押した順を照らす。返す字: ok / wrong / busy（時間の止め）/ revoked（使えなくした）/ stopped（外れの合計で止めた）/ unknown。"""
    now = time.time() if now is None else now
    with store.locked(folder()):
        p, e = _load(token)
        if not e:
            return "unknown"
        if e.get("revoked"):
            return "revoked"
        if e.get("stopped"):
            return "stopped"
        e["tries"] = [t for t in e.get("tries", []) if now - t < WINDOW]
        if len(e["tries"]) >= WINDOW_TRIES:
            store.write_json(p, e)
            return "busy"
        e["tries"].append(now)
        ok = isinstance(order, (list, tuple)) and len(order) == ORDER and hmac.compare_digest(e["seal"], _seal(token, order))
        if ok:
            e["last_used"] = now
            store.write_json(p, e)
            return "ok"
        e["fails"] = e.get("fails", 0) + 1
        who = _peer(peer)
        e.setdefault("peer_fails", {})[who] = e["peer_fails"].get(who, 0) + 1
        if e["peer_fails"][who] >= PEER_FAILS:
            e["revoked"], e["revoked_why"] = True, "同じ相手の外れの合計"
        if e["fails"] >= TOTAL_FAILS and not e.get("stopped"):
            e["stopped"] = True
            _notice({"at": now, "what": "しおりを止めた（外れの合計）", "records": e.get("records", [])})
        store.write_json(p, e)
        return "wrong"


def _notice(item):
    """進め役への知らせ（1 行 1 件）。しおりの印は書かない（記録の番号で探す）。"""
    with open(folder() / "notices.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")


def fresh(token, now=None):
    """開いた後、さわらない 20 分の内か。開いていない・使えなくした・止めた時は False。"""
    now = time.time() if now is None else now
    _, e = _load(token)
    return bool(e and not e.get("revoked") and not e.get("stopped") and e.get("last_used") and now - e["last_used"] < IDLE)


def touch(token, now=None):
    """開いた画面を使った（20 分を数え直す）。開いていない時は何もしない。"""
    now = time.time() if now is None else now
    with store.locked(folder()):
        p, e = _load(token)
        if e and fresh(token, now):
            e["last_used"] = now
            store.write_json(p, e)


def records_of(token):
    """そのしおりの記録の番号の並び（使えなくした・止めた時は空）。"""
    _, e = _load(token)
    return list(e.get("records", [])) if e and not e.get("revoked") and not e.get("stopped") else []


def add_record(token, rid):
    """続きの記録をしおりに足す（開いた画面から・開いていない時は足さない）。"""
    with store.locked(folder()):
        p, e = _load(token)
        if not (e and fresh(token)):
            return False
        if str(rid) not in e["records"]:
            e["records"].append(str(rid))
            store.write_json(p, e)
        return True


def _entries():
    for p in sorted(folder().glob("*.json")):
        e = store.read_json_or_skip(p)
        if e is not None:
            yield p, e


def drop_record(rid):
    """記録を取り下げた時に、どのしおりの並びからもその番号を消す。消した数を返す。"""
    n = 0
    with store.locked(folder()):
        for p, e in _entries():
            if str(rid) in e.get("records", []):
                e["records"] = [r for r in e["records"] if r != str(rid)]
                store.write_json(p, e)
                n += 1
    return n


def revoke_by_record(rid):
    """進め役の道: 記録の番号から、その記録を持つしおりを使えなくする（刷り損じ・余り・落とした時）。使えなくした数を返す。"""
    n = 0
    with store.locked(folder()):
        for p, e in _entries():
            if str(rid) in e.get("records", []) and not e.get("revoked"):
                e["revoked"], e["revoked_why"] = True, "進め役"
                store.write_json(p, e)
                n += 1
    return n


def revoke(token):
    """しおりの印から使えなくする（刷り損じをその場で使えなくする時）。使えなくしたら True。"""
    with store.locked(folder()):
        p, e = _load(token)
        if not e or e.get("revoked"):
            return False
        e["revoked"], e["revoked_why"] = True, "進め役"
        store.write_json(p, e)
        return True
