"""管理の合言葉（安全の事項 1 の締め前の手当て・本人の頼み 11-08）。

なぜ: 共有の合言葉を知る人は、作る側の頁を読み、次の版を採る口と AI の口まで使えた。管理の合言葉の設定のファイル（OMOCHAE_ADMIN_KEY_FILE）がある時だけ、
管理の口を管理の cookie（utsushi_a）を持つ画面に限る。設定が無い時は今のまま（機能・見た目・挙動を替えない）。断りの字は前からの物。
見る事:
1 設定あり: 合言葉だけの画面は管理の面（/loop・/loop/<玩具>・/loop/ayumi）と次の版・AI の口が 403。?a= の 1 回の入口で管理の cookie に移し、URL から消す。
  管理の cookie の画面は通る。合言葉の設定の無い手元の場でも同じ
2 設定なし: 合言葉の画面と手元の場は今のまま（管理の面が 200）
終了: 0 = 通る / 1 = 落ちる（assert）
"""
import http.client
import os
import tempfile
import threading
import urllib.parse

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(os.environ["OMOCHAE_DATA"], "api-usage.jsonl")
os.environ.pop("OMOCHAE_ADMIN_KEY_FILE", None)
os.environ.pop("ANTHROPIC_API_KEY", None)

from omochae import hypotheses, records  # noqa: E402
from web import play_server  # noqa: E402

G = "NDL-1187053-R0000005-L"
H = hypotheses.sheet_of(G)["id"]
KEY, ADMIN = "k" * 24, "a" * 24


def up(**kw):
    s = play_server.serve(0, **kw)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s, s.server_address[1]


def call(port, path, method="GET", form=None, cookie=None):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=60)
    headers = {"Host": f"127.0.0.1:{port}"}
    if cookie:
        headers["Cookie"] = cookie
    body = None
    if form is not None:
        body = urllib.parse.urlencode(form).encode()
        headers |= {"Content-Type": "application/x-www-form-urlencoded", "Origin": f"http://127.0.0.1:{port}"}
    c.request(method, path, body=body, headers=headers)
    r = c.getresponse()
    return r.status, r.getheader("Location"), r.headers.get_all("Set-Cookie") or [], r.read().decode("utf-8", "replace")


ADMIN_PATHS = ("/loop", f"/loop/{G}", "/loop/ayumi")
CHANGE = ("next", "ai-interpret", "ai-observe")
K, A = f"utsushi_k={KEY}", f"utsushi_a={ADMIN}"

# ---- 2 設定なし（先に立てる。設定のファイルはサーバを立てる時に読む）
plain_g, PG = up(public_key=KEY)
plain_l, PL = up()
rid = records.add({"source_id": G, "hypothesis_id": H, "sheet_version": 1, "result": records.results_for(G)[0], "impression": "試し"})[0]
for port, cookie in ((PG, K), (PL, None)):
    for path in ADMIN_PATHS:
        assert call(port, path, cookie=cookie)[0] == 200, ("設定なしで管理の面が替わった", port, path)
    for act in CHANGE:
        assert call(port, f"/record/{rid}/{act}", "POST", {"to": "12"}, cookie=cookie)[0] != 403, ("設定なしで変える口が断られた", port, act)
assert play_server.serve.__defaults__ is not None and plain_g.admin_key is None and plain_l.admin_key is None

# ---- 1 設定あり
d = tempfile.mkdtemp()
with open(os.path.join(d, "admin.key"), "w", encoding="utf-8") as f:
    f.write(ADMIN + "\n")
os.environ["OMOCHAE_ADMIN_KEY_FILE"] = os.path.join(d, "admin.key")
adm_g, AG = up(public_key=KEY)
adm_l, AL = up()
assert adm_g.admin_key == ADMIN and adm_l.admin_key == ADMIN
for port, base in ((AG, K), (AL, None)):
    for path in ADMIN_PATHS:
        code, _, _, body = call(port, path, cookie=base)
        assert code == 403 and "受け付けられません" in body, ("合言葉だけの画面で管理の面が開いた", port, path, code)
    for act in CHANGE:
        assert call(port, f"/record/{rid}/{act}", "POST", {"to": "12"}, cookie=base)[0] == 403, ("合言葉だけの画面で変える口が通った", port, act)
    # 管理の入口: ?a= を 1 回だけ受けて cookie に移し、URL から消す
    code, where, cookies, _ = call(port, f"/loop?a={ADMIN}&x=1", cookie=base)
    assert code == 303 and where == "/loop?x=1" and any(c.startswith(f"utsushi_a={ADMIN};") and "HttpOnly" in c for c in cookies), (code, where, cookies)
    assert call(port, f"/loop?a={'b' * 24}", cookie=base)[0] == 403, "違う管理の合言葉で入れた"
    with_a = f"{base}; {A}" if base else A
    for path in ADMIN_PATHS:
        assert call(port, path, cookie=with_a)[0] == 200, ("管理の cookie で管理の面が開かない", port, path)
    for act in CHANGE:
        assert call(port, f"/record/{rid}/{act}", "POST", {"to": "12"}, cookie=with_a)[0] != 403, ("管理の cookie で変える口が断られた", port, act)
    # 管理の口の外は今のまま
    assert call(port, f"/toy/{G}", cookie=base)[0] == 200
for s in (plain_g, plain_l, adm_g, adm_l):
    s.shutdown()
print("ok: 管理の合言葉の設定がある時だけ、管理の口は管理の cookie の画面に限る・設定が無い時は今のまま")
