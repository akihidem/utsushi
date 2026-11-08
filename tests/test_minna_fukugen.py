"""玩具の頁の作った物の並び（#minna）を、人ごとの呼び方でなく「これまでの復元」と呼ぶ（夕方のサイトのレビュー 11-07 の 6
「他の人が作ったものと自分の記録 → これまでの復元として属人化しない」。設計の担当の仕分けで、決まりとぶつからない字の替え）。

見る事:
1. 玩具の頁に「これまでの復元」の節（#minna）と頭の「これまでの記録」の畳みが無い（本人の言葉 11-08「つくるは読む情報が多すぎて整理する必要を
   感じる。復元の記録などはすべてもちよるに統合する。」で、中身は もちよる へ移した）。前の見出し「他の人が作った物と、自分の記録」は、どの玩具の頁にも残らない
2. 字の元（MINNA_HEAD・MINNA_EMPTY・MINNA_ORDER）に、人を主にした字（「最初の記録を残す人」「自分の説明」）が残らない
3. 記録を残した後、その記録は手帖の記録の頁にあり、玩具の頁には出ない。どちらの頁にも人を主にした字が残らない。玩具の頁からギャラリー（もちよる）への道は頁の足に残る
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
    # 本人の言葉 11-08「つくるは読む情報が多すぎて整理する必要を感じる。復元の記録などはすべてもちよるに統合する。」: 節も頭の畳みも玩具の頁に無い
    assert 'id="minna"' not in page and toy.MINNA_HEAD not in page and "これまでの記録" not in page, sid
    assert toy.MINNA_EMPTY not in page and toy.MINNA_ORDER not in page and "試した記録は" not in page, sid
    assert not [w for w in OLD if w in page], (sid, [w for w in OLD if w in page])
    assert 'href="/gallery"' in page, "ギャラリー（もちよる）への道は頁の足に残す"

# 2. 字の元に人を主にした字が残らない（並びの部品は もちよる の側でも使える形のまま残る）
assert not [w for w in OLD for s in (toy.MINNA_HEAD, toy.MINNA_EMPTY, toy.MINNA_ORDER) if w in s]
assert not [w for w in ("他の人", "自分") if w in toy.MINNA_HEAD], "見出しは人ごとの呼び方をしない"
assert "作った人の説明" in toy.MINNA_ORDER

# 3. 記録を残した後（記録は使い手と同じ道で残す: 刷ってから記録の口へ送る）
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
kiroku = urllib.request.urlopen(f"{base}/toy/{G}/techo/kiroku").read().decode()
server.shutdown()
# 本人の言葉 11-08「…復元の記録などはすべてもちよるに統合する。」: 残した記録は玩具の頁に出ず、手帖の記録の頁に出る
assert "R-0001" not in page and 'id="minna"' not in page, "残した記録が玩具の頁に出た"
assert "R-0001" in kiroku, "残した記録が手帖の記録の頁に無い"
assert not [w for w in OLD if w in page or w in kiroku], [w for w in OLD if w in page or w in kiroku]

print("ok 玩具の頁に これまでの復元 と頭の記録の畳みが無い・字の元に人ごとの呼び方が無い・残した記録は手帖の記録の頁にある")
