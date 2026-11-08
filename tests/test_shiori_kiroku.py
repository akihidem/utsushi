"""しおりだけの画面の 手帖の記録の頁（/toy/<玩具>/techo/kiroku）の字（安全の事項 1・11 しおりの範囲を本人に関係するデータに閉じる・統括の決め 11-08）。

なぜ: しおりで開いただけの画面（合言葉の cookie が無い）にも、手帖の記録の頁で、ほかの人の記録の工夫の行と説明の字と記録の番号が、合言葉の画面と同じに出ていた。
しおりだけの画面では、そのしおりに結ばれた記録（本人の物）は今のまま、ほかの人の記録は公開の場の記録の頁と同じ形（番号・人の書いた字・説明を出さない）にする。
合言葉の画面と、合言葉の設定が無い手元の場は替えない。
見る事:
1 しおりだけの画面: 自分のしおりに結ばれた記録の工夫の行と説明は出る。ほかの人の記録の工夫の行・説明・記録の番号は出ない
2 合言葉の画面（しおりと両方の時も）と手元の場: ほかの人の記録の工夫の行・説明・記録の番号が、今のまま出る
終了: 0 = 通る / 1 = 落ちる（assert）
"""
import http.client
import os
import tempfile
import threading
import urllib.parse

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(os.environ["OMOCHAE_DATA"], "api-usage.jsonl")
os.environ["OMOCHAE_SHIORI_BASE"] = "https://example.org"

from omochae import hypotheses, loop, records, shiori  # noqa: E402
from web import play_server, shiori_open, wording  # noqa: E402

G = "NDL-1187053-R0000005-L"
H = hypotheses.sheet_of(G)["id"]
KEY = "k" * 24
gated, local = play_server.serve(0, public_key=KEY), play_server.serve(0)
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


def rec(tag):
    rid = records.add({"source_id": G, "hypothesis_id": H, "sheet_version": 1, "result": records.results_for(G)[0], "impression": f"{tag}の感想",
                       "fixes": [{"part": f"{tag}の部品", "change": f"{tag}の替えた事", "outcome": f"{tag}の結果"}]})[0]
    assert loop.save_explanation(rid, "試し", f"{tag}の説明の字", "軸を長くする") == [], rid
    return rid


K = f"utsushi_k={KEY}"
assert call(GP, f"/toy/{G}/print", "POST", {"hypothesis": H}, cookie=K)[0] in (200, 303)
r_other, r_mine = rec("ほかの人"), rec("自分")
s = shiori.make(records=[r_mine])
code, cookies, _ = call(GP, f"/s/{s['token']}", "POST", {"order": ",".join(str(i) for i in s["order"])})
assert code == 303, code
A = [c.split(";", 1)[0] for c in cookies if c.startswith(shiori_open.COOKIE + "=")][0]
PAGE = f"/toy/{G}/techo/kiroku"

# ---- 1 しおりだけの画面
code, _, page = call(GP, PAGE, cookie=A)
assert code == 200, code
assert "自分の部品" in page and "自分の説明の字" in page, "自分のしおりに結ばれた記録の字が出ない"
for word in ("ほかの人の部品", "ほかの人の替えた事", "ほかの人の説明の字", wording.record_no(r_other)):
    assert word not in page, ("しおりだけの画面に、ほかの人の記録の字か番号が出た", word)

# ---- 2 合言葉の画面・両方の画面・手元の場（今のまま）
for port, cookie in ((GP, K), (GP, f"{K}; {A}"), (LP, None)):
    code, _, page = call(port, PAGE, cookie=cookie)
    assert code == 200, (port, code)
    for word in ("ほかの人の部品", "ほかの人の説明の字", wording.record_no(r_other), "自分の部品", wording.record_no(r_mine)):
        assert word in page, ("合言葉の画面か手元の場の字が替わった", port, word)
gated.shutdown()
local.shutdown()
print("ok: しおりだけの画面の 手帖の記録の頁は、自分のしおりの記録だけ字を出し、ほかの人の記録は公開の場と同じ形・合言葉の画面と手元の場は今のまま")
