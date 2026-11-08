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
  ③ しおりごとの外れの合計 20 回でしおりを止め、進め役への知らせを 1 つ残す（別々の相手から少しずつ当て切るのを止める・本人 11-08「外れ 20 回で止める。」）
  相手は秘密の値と組にしたハッシュで持ち、番地そのものは持たない。
- 決まった番地が無い時は、しおりを作らない（立てるたびに替わる一時のトンネルの番地を刷ると、後で開かなくなるため）。
- 名前・学校・連絡先は持たない。記録を取り下げると、しおりの並びからもその番号を消す（drop_record）。
- **開いた画面の印**（開く道の設計 7.3・別の目の止め S2・統括の決め 11-08）: 押した順が当たった時に、開いた画面だけが持つでたらめの印を作り、
  台帳にはそのハッシュと時刻だけを持つ。画面の cookie は「しおりの印.開いた画面の印」で、しおりの印（QR に入っている）だけでは開かない。
  持ち主が開いている 20 分の間に、QR の写真だけを持つ人が cookie を手で作って入れる事ができないように。1 つのしおりに開いた画面は 1 つだけ
  （開き直すと前の画面の印は効かなくなる）。「とじる」・使えなくする・止めるで、開いた画面の印もすぐ消える。照らしは compare_digest。
- さわらない 20 分で切れる。最後に使った時刻（last_used）の書き直しは 1 分に 1 回まで（門の頼みのたびに台帳を書かないため）。
- 押した順が数でない・形が違う時は、落とさずに外れとして数える（#611 の別の目の気づき (2)）。
- 作る道具（QR の絵と紙）は別の PR。ここは番地が決まる前から作れる台帳と、開いた画面の印まで（統括の段取り 11-08）。
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
# ③ しおりごとの外れの合計で止めて知らせる。本人 11-08「外れ 20 回で止める。」（前は 50。別の目の見込み: 9 つから 3 つの順は 504 通りで、
# 止まる前に QR だけの人が当てる見込みは、50 回なら多めに見て約 10%、20 回なら約 4%）。数を替える時はここだけ
TOTAL_FAILS = 20
IDLE = 1200                       # さわらない 20 分で切れる（共用の iPad の次の人へ渡らないように）
TOUCH_EVERY = 60                  # 最後に使った時刻を書き直すのは 1 分に 1 回まで
PICTURES = 9                      # しおりに刷る玩具の小さな絵の数（どの絵かは紙の版の PR で決める）
ORDER = 3                         # 押す数
TOKEN = re.compile(r"[A-Za-z0-9_-]{22}")
SCREEN = re.compile(r"([A-Za-z0-9_-]{22})\.([A-Za-z0-9_-]{22})")  # 画面の cookie の値: しおりの印.開いた画面の印
# 替わる番地（立てるたびに名前が替わる一時のトンネル）。しおりに刷らない。手元の名前（点の無い名）と数の番地も刷らない（下の base_url の形で断る）
CHANGING = ("trycloudflare.com",)


class NoBase(RuntimeError):
    """決まった番地が設定されていない（しおりを作らない）。"""


def base_url():
    """決まった番地。無い・https でない・替わる番地の時は None（しおりを作らない）。"""
    b = os.environ.get(BASE_ENV, "").strip().rstrip("/")
    if (not re.fullmatch(r"https://[a-z0-9-]+(?:\.[a-z0-9-]+)+(?::\d+)?", b) or re.fullmatch(r"https://[\d.]+(?::\d+)?", b)
            or any(c in b for c in CHANGING)):
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


def _order(order):
    """押した順を 3 つの絵の番号（0〜8・重ならない）に読む。読めない時は None（外れとして数える）。"""
    if not isinstance(order, (list, tuple)) or len(order) != ORDER:
        return None
    try:
        out = tuple(int(str(i).strip()) for i in order)
    except ValueError:
        return None
    return out if all(0 <= i < PICTURES for i in out) and len(set(out)) == ORDER else None


def _screen_hash(screen):
    return hashlib.sha256(("screen:" + screen).encode()).hexdigest()


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
             "tries": [], "fails": 0, "peer_fails": {}, "revoked": False, "stopped": False, "screen": None}
    with store.locked(folder()):
        store.write_json(folder() / _name(token), entry, exclusive=True)
    return {"token": token, "order": order, "url": f"{base}/s/{token}"}


def check(token, order, peer, now=None, screen=None):
    """押した順を照らす。返す字: ok / wrong / busy（時間の止め）/ revoked（使えなくした）/ stopped（外れの合計で止めた）/ unknown。
    screen は開いた画面の印（呼ぶ側が secrets で作る 22 字）。当たった時だけ、そのハッシュを台帳に置き、前の画面の印を替える。"""
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
        read = _order(order)
        ok = read is not None and hmac.compare_digest(e["seal"], _seal(token, read))
        if ok:
            e["last_used"] = now
            e["screen"] = _screen_hash(screen) if isinstance(screen, str) and TOKEN.fullmatch(screen) else None
            store.write_json(p, e)
            return "ok"
        e["fails"] = e.get("fails", 0) + 1
        who = _peer(peer)
        e.setdefault("peer_fails", {})[who] = e["peer_fails"].get(who, 0) + 1
        if e["peer_fails"][who] >= PEER_FAILS:
            e["revoked"], e["revoked_why"], e["screen"] = True, "同じ相手の外れの合計", None
        if e["fails"] >= TOTAL_FAILS and not e.get("stopped"):
            e["stopped"], e["screen"] = True, None
            _notice({"at": now, "what": "しおりを止めた（外れの合計）", "records": e.get("records", [])})
        store.write_json(p, e)
        return "wrong"


def status(token):
    """しおりの今の形（数えない・書かない）: open（押せる）/ revoked / stopped / unknown。開く道が、絵の頁を出すか断るかを決めるのに使う。"""
    _, e = _load(token)
    if not e:
        return "unknown"
    return "revoked" if e.get("revoked") else "stopped" if e.get("stopped") else "open"


def token_of(cookie):
    """画面の cookie の値から、しおりの印を取る（形だけを見る。開いているかは fresh で見る）。"""
    m = SCREEN.fullmatch(cookie) if isinstance(cookie, str) else None
    return m.group(1) if m else None


def _notice(item):
    """進め役への知らせ（1 行 1 件）。しおりの印は書かない（記録の番号で探す）。"""
    with open(folder() / "notices.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")


def _opened(cookie, now):
    """画面の cookie の値（しおりの印.開いた画面の印）を照らす。Returns (path, entry, しおりの印) か (None, None, None)。
    しおりの印だけ・形の違う値・使えなくした・止めた・開いた画面の印が違う（開き直した・とじた）・20 分を過ぎた時は通さない。"""
    m = SCREEN.fullmatch(cookie) if isinstance(cookie, str) else None
    if not m:
        return None, None, None
    p, e = _load(m.group(1))
    if not (e and not e.get("revoked") and not e.get("stopped") and isinstance(e.get("screen"), str)
            and hmac.compare_digest(e["screen"], _screen_hash(m.group(2))) and e.get("last_used") and now - e["last_used"] < IDLE):
        return None, None, None
    return p, e, m.group(1)


def fresh(cookie, now=None):
    """その画面が開いていて、さわらない 20 分の内か。"""
    return _opened(cookie, time.time() if now is None else now)[1] is not None


def touch(cookie, now=None):
    """開いた画面を使った（20 分を数え直す）。書き直すのは前の書き直しから 1 分を過ぎた時だけ。開いていない時は何もしない。"""
    now = time.time() if now is None else now
    with store.locked(folder()):
        p, e, _ = _opened(cookie, now)
        if e and now - e["last_used"] >= TOUCH_EVERY:
            e["last_used"] = now
            store.write_json(p, e)


def close(cookie):
    """とじる: 開いた画面の印を台帳から消す（cookie を消すだけだと、その前に値を写した人の印が 20 分の切れまで生きるため・止め S2）。
    閉じたら True。開いていない画面でも落とさない（False）。"""
    m = SCREEN.fullmatch(cookie) if isinstance(cookie, str) else None
    if not m:
        return False
    with store.locked(folder()):
        p, e = _load(m.group(1))
        if not (e and isinstance(e.get("screen"), str) and hmac.compare_digest(e["screen"], _screen_hash(m.group(2)))):
            return False
        e["screen"] = None
        store.write_json(p, e)
        return True


def records_of(cookie, now=None):
    """開いた画面の、そのしおりの記録の番号の並び（開いていない時は空）。"""
    e = _opened(cookie, time.time() if now is None else now)[1]
    return list(e.get("records", [])) if e else []


def add_record(cookie, rid, now=None):
    """続きの記録をしおりに足す（開いた画面から・開いていない時は足さない）。"""
    now = time.time() if now is None else now
    with store.locked(folder()):
        p, e, _ = _opened(cookie, now)
        if not e:
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
                e["revoked"], e["revoked_why"], e["screen"] = True, "進め役", None
                store.write_json(p, e)
                n += 1
    return n


def revoke(token):
    """しおりの印から使えなくする（刷り損じをその場で使えなくする時）。使えなくしたら True。"""
    with store.locked(folder()):
        p, e = _load(token)
        if not e or e.get("revoked"):
            return False
        e["revoked"], e["revoked_why"], e["screen"] = True, "進め役", None
        store.write_json(p, e)
        return True
