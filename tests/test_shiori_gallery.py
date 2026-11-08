"""しおりだけの画面の もちよる（/gallery）の字（安全の事項 11 しおりの範囲を本人に関係するデータに閉じる・統括の決め 11-08）。

なぜ: しおりで開いただけの画面（合言葉の cookie が無い）にも、もちよる の他の人の札の感想の字が、人の確かめの前でも出ていた（合言葉の画面と同じ扱い）。
しおりだけの画面の もちよる だけを、公開の場と同じ線（人が確かめた字だけ・記録の番号を出さない）にする。合言葉の画面・手元の場・公開の場は一字も替えない。
見る事:
1 しおりだけの画面: 確かめた記録の字は出る・確かめていない他の人の記録の字は出ない・他の人の記録の番号は出ない。
  そのしおりに結ばれた記録（本人の物）の字は、確かめる前でも前のとおり出る（番号は出さない・別の目の #734 の止め）
2 合言葉の画面（しおりと両方の時も）と、合言葉の設定が無い手元の場: もちよる の中身は、前と同じ作り（gallery_page の既定）と一字も同じ。確かめていない字も出る
3 公開の場: 確かめた字だけ（前のまま）
終了: 0 = 通る / 1 = 落ちる（assert）
"""
import http.client
import os
import re
import tempfile
import threading
import urllib.parse

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(os.environ["OMOCHAE_DATA"], "api-usage.jsonl")
os.environ["OMOCHAE_SHIORI_BASE"] = "https://example.org"

from omochae import hypotheses, records, shiori, words_review  # noqa: E402
from web import play_server, shiori_open, techo_site, wording  # noqa: E402

G = "NDL-1187053-R0000005-L"
H = hypotheses.sheet_of(G)["id"]
KEY = "k" * 24
gated, local, public = play_server.serve(0, public_key=KEY), play_server.serve(0), play_server.serve(0, public_open=True)
for s in (gated, local, public):
    threading.Thread(target=s.serve_forever, daemon=True).start()
GP, LP, PP = (s.server_address[1] for s in (gated, local, public))


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


def rec(words):
    return records.add({"source_id": G, "hypothesis_id": H, "sheet_version": 1, "result": records.results_for(G)[0], "impression": words})[0]


raw_words, ok_words, mine_words = "まだ確かめていない感想の字", "人が確かめた感想の字", "自分のしおりの確かめていない字"
r_raw, r_ok, r_mine = rec(raw_words), rec(ok_words), rec(mine_words)
assert words_review.record(r_ok, "進め役") == [] and words_review.checked(r_ok) and not words_review.checked(r_raw)
s = shiori.make(records=[r_mine])
code, cookies, _ = call(GP, f"/s/{s['token']}", "POST", {"order": ",".join(str(i) for i in s["order"])})
assert code == 303, code
A = [c.split(";", 1)[0] for c in cookies if c.startswith(shiori_open.COOKIE + "=")][0]
K = f"utsushi_k={KEY}"
inner = lambda page: page[page.index('<div class="gallery">'):page.index("</main>")]

# ---- 1 しおりだけの画面
code, _, page = call(GP, "/gallery", cookie=A)
assert code == 200 and ok_words in page and raw_words not in page, ("しおりだけの画面に、確かめていない他の人の字が出た", code)
assert wording.record_no(r_ok) not in page and wording.record_no(r_raw) not in page, "しおりだけの画面に、他の人の記録の番号が出た"
assert mine_words in page and wording.record_no(r_mine) not in page, "自分のしおりに結ばれた記録の字が出ない（か、番号が出た）"

# ---- 2 合言葉の画面・両方の画面・手元の場: 前と同じ作り（gallery_page の既定）と一字も同じ
before = techo_site.gallery_page(play_server.sources(), public=False, rec_key=None)
for port, cookie in ((GP, K), (GP, f"{K}; {A}"), (LP, None)):
    code, _, page = call(port, "/gallery", cookie=cookie)
    assert code == 200 and raw_words in page and ok_words in page and mine_words in page, ("合言葉の画面か手元の場の字が替わった", port)
    assert inner(page) == inner(f"{before}</main>"), ("合言葉の画面か手元の場の もちよる の中身が前の作りと違う", port)

# ---- 3 公開の場（前のまま: 確かめた字だけ）
code, _, page = call(PP, "/gallery")
assert code == 200 and ok_words in page and raw_words not in page and mine_words not in page
for srv in (gated, local, public):
    srv.shutdown()
print("ok: しおりだけの画面の もちよる は確かめた字だけ・番号なし・合言葉の画面と手元の場は前の作りと一字も同じ・公開の場は前のまま")
