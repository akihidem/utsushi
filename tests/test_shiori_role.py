"""しおりだけの画面の範囲（安全の事項 1 参加者と管理者の権限の分離・11 しおりの範囲）。

なぜ: しおりで開いた画面も合言葉の門を通るので、前は合言葉の画面と同じに、作る側の頁（工作の様子・他の人の聞いた事と感想）を読め、
他の人の記録の「次の版」を送れた。しおりの範囲を、そのしおりに結ばれた記録に閉じる。合言葉の画面と、合言葉の設定が無い手元の場は替えない。
見る事（拒否の試験: 未認証・しおりの人 A・しおりの人 B・合言葉）:
1 未認証は門で断られる（今のまま）
2 しおりの人 A・B: 管理の面（/loop・/loop/<玩具>・/loop/ayumi）は 403。次の版と AI の口（next・ai-interpret・ai-observe）は、
  自分の記録にも他の人の記録にも 403。他の人の記録への送り（説明）は 403。玩具の頁・しおりの記録の頁は開き、続きの記録は残せて自分のしおりに入る
3 合言葉の画面: 管理の面は 200、次の版と AI の口は 403 にならない（今のまま）。しおりと合言葉の両方を持つ画面は合言葉の画面
4 合言葉の設定が無い手元の場は、今のまま開く
終了: 0 = 通る / 1 = 落ちる（assert）
"""
import http.client
import json
import os
import re
import tempfile
import threading
import urllib.parse

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(os.environ["OMOCHAE_DATA"], "api-usage.jsonl")
os.environ["OMOCHAE_SHIORI_BASE"] = "https://example.org"
os.environ.pop("ANTHROPIC_API_KEY", None)

from omochae import hypotheses, records, shiori  # noqa: E402
from web import play_server, shiori_open  # noqa: E402

G = "NDL-1187053-R0000005-L"
H = hypotheses.sheet_of(G)["id"]
KEY = "k" * 24
gated = play_server.serve(0, public_key=KEY)
local = play_server.serve(0)
for s in (gated, local):
    threading.Thread(target=s.serve_forever, daemon=True).start()
GP, LP = gated.server_address[1], local.server_address[1]


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
    return r.status, r.headers.get_all("Set-Cookie") or [], r.read().decode("utf-8", "replace")


def rec():
    return records.add({"source_id": G, "hypothesis_id": H, "sheet_version": 1, "result": records.results_for(G)[0], "impression": "試し"})[0]


def opened(rid):
    """記録 1 つを結んだしおりを作り、絵の順を押して開いた画面の cookie を返す（本物の開く道を通す）。"""
    s = shiori.make(records=[rid])
    code, cookies, _ = call(GP, f"/s/{s['token']}", "POST", {"order": ",".join(str(i) for i in s["order"])})
    assert code == 303, code
    jar = [c.split(";", 1)[0] for c in cookies if c.startswith(shiori_open.COOKIE + "=")]
    assert jar, cookies
    return jar[0]


assert call(GP, f"/toy/{G}/print", "POST", {"hypothesis": H}, cookie=f"utsushi_k={KEY}")[0] in (200, 303)
ra, rb = rec(), rec()
A, B = opened(ra), opened(rb)
K = f"utsushi_k={KEY}"
ADMIN = ("/loop", f"/loop/{G}", "/loop/ayumi")
CHANGE = ("next", "ai-interpret", "ai-observe")

# ---- 1 未認証
for path in ADMIN:
    assert call(GP, path)[0] == 403, ("未認証で管理の面が開いた", path)

# ---- 2 しおりの人 A・B
for who, mine, other in ((A, ra, rb), (B, rb, ra)):
    for path in ADMIN:
        code, _, body = call(GP, path, cookie=who)
        assert code == 403 and "受け付けられません" in body, ("しおりだけの画面で管理の面が開いた", path, code)
    for rid in (mine, other):
        for act in CHANGE:
            assert call(GP, f"/record/{rid}/{act}", "POST", {"to": "12", "param": "x"}, cookie=who)[0] == 403, ("しおりだけの画面で変える口が通った", rid, act)
    assert call(GP, f"/record/{other}/explain", "POST", {"by": "x", "text": "他の人の記録", "next_idea": ""}, cookie=who)[0] == 403, "他の人の記録へ送れた"
    # 開いた画面でできる事は残る: 玩具の頁・しおりの記録の頁・続きの記録（自分のしおりに入る）
    assert call(GP, f"/toy/{G}", cookie=who)[0] == 200
    code, _, body = call(GP, f"/toy/{G}/record-json", "POST", {"hypothesis": H, "result": records.results_for(G)[0], "impression": "続き"}, cookie=who)
    assert code == 201, (code, body[:200])
    assert json.loads(body)["id"] in shiori.records_of(who.split("=", 1)[1]), "続きの記録が自分のしおりに入らない"

# ---- 3 合言葉の画面（今のまま）・両方を持つ画面は合言葉の画面
for cookie in (K, f"{K}; {A}"):
    for path in ADMIN:
        assert call(GP, path, cookie=cookie)[0] == 200, ("合言葉の画面で管理の面が開かない", path, cookie[:12])
    for act in CHANGE:
        assert call(GP, f"/record/{rb}/{act}", "POST", {"to": "12", "param": "x"}, cookie=cookie)[0] != 403, ("合言葉の画面で変える口が断られた", act)

# ---- 4 合言葉の設定が無い手元の場（今のまま）
for path in ADMIN:
    assert call(LP, path)[0] == 200, ("手元の場で管理の面が開かない", path)
gated.shutdown()
local.shutdown()
print("ok: しおりだけの画面は管理の面と変える口を開かず、他の人の記録へ送れない・合言葉の画面と手元の場は今のまま")
