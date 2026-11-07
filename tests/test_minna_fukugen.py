"""玩具の頁の作った物の並び（#minna）を、人ごとの呼び方でなく「これまでの復元」と呼ぶ（夕方のサイトのレビュー 11-07 の 6
「他の人が作ったものと自分の記録 → これまでの復元として属人化しない」。設計の担当の仕分けで、決まりとぶつからない字の替え）。

見る事:
1. 玩具の頁の節の見出しは「これまでの復元」。前の見出し「他の人が作った物と、自分の記録」は、どの玩具の頁にも残らない
   （頁の頭の「これまでの記録」の畳みの 1 文はこの直しの外。見るのはこの節の中）
2. 記録が無い時の 1 文と、記録がある時の並びの頭の 1 文に、人を主にした字（「最初の記録を残す人」「自分の説明」）が残らない
3. 置き場と並びは変えない: 節の錨 #minna は 1 つで、ギャラリーへの道も残る。ギャラリーの見出しは今のまま（この直しの外）
"""
import os
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from omochae import hypotheses  # noqa: E402
from web import toy  # noqa: E402

G, T = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"
OLD = ("他の人が作った物と、自分の記録", "最初の記録を残す人", "自分の説明")

# 1・3. 必須の 2 種と、ほかの玩具 1 つの頁
other = next(p.stem for p in (hypotheses.ROOT / "data/hypotheses").glob("*.json") if p.stem not in (G, T))
for sid in (G, T, other):
    page = toy.toy_page(sid)
    assert page.count('id="minna"') == 1 and f'<section class="sec" id="minna"><h2>{toy.MINNA_HEAD}</h2>' in page, sid
    minna = page[page.index('id="minna"'):]
    minna = minna[:minna.index("</section>")]
    # 見るのはこの節の中（頁の頭の「これまでの記録」の 1 文は、この直しの外。レビューの 6 が指したのはこの節）
    assert OLD[0] not in page and not [w for w in OLD if w in minna], (sid, [w for w in OLD if w in minna])
    assert 'href="/gallery"' in minna, "ギャラリーへの道は残す"

# 2. 記録が無い時と、記録がある時の 1 文（記録は使い手と同じ道で残す: 刷ってから記録の口へ送る）
assert toy.MINNA_EMPTY in toy.toy_page(other), "記録の無い玩具では、記録が無い時の 1 文"
import threading  # noqa: E402
import urllib.parse  # noqa: E402
import urllib.request  # noqa: E402

from web.play_server import serve  # noqa: E402

server = serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"
GS = hypotheses.sheet_of(G)["id"]


def post(path, data):
    r = urllib.request.Request(base + path, data=urllib.parse.urlencode(data).encode(), headers={"Origin": base})
    return urllib.request.urlopen(r).status


assert post(f"/toy/{G}/print", {"hypothesis": GS}) in (200, 303)
assert post(f"/toy/{G}/record", {"hypothesis": GS, "result": "動いた"}) in (200, 303)
page = urllib.request.urlopen(f"{base}/toy/{G}").read().decode()
server.shutdown()
minna = page[page.index('id="minna"'):]
minna = minna[:minna.index("</section>")]
assert toy.MINNA_ORDER in minna and toy.MINNA_EMPTY not in minna, "記録がある時は並びの頭の 1 文"
assert not [w for w in OLD if w in minna] and "作った人の説明" in toy.MINNA_ORDER
assert not [w for w in OLD for s in (toy.MINNA_HEAD, toy.MINNA_EMPTY, toy.MINNA_ORDER) if w in s]
assert not [w for w in ("他の人", "自分") if w in toy.MINNA_HEAD], "見出しは人ごとの呼び方をしない"

print("ok 作った物の並びの見出しと 2 つの文を「これまでの復元」の形に（置き場とギャラリーは今のまま）")
