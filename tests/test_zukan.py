"""図鑑の頁を外した形（本人の言葉 11-08「図鑑のページ要らない」・本人の決め 11-08「本の頁は残す」）と、文の印の床（J-016）。

見る線:
1. 図鑑の目次（/zukan）と玩具ごとの図鑑の頁（/zukan/<印>）は無い（断りの 404）
2. 図鑑の本の頁（/zukan/hon/<n>）と、くずし字を読む（/zukan/<印>/yomi・道の名はそのまま）は残る
3. 図鑑の頁への道は、どの頁にも無い（玩具の頁・序の頁・くずし字を読む の頁の帯と玩具の名）。本の頁の入口は序の頁に、本人の決めの字「本でよむ」で
4. 文の印の床（zukan.guard）は残る: 印の無い文・飾りの印・裏付けの無い引用を描かずに止める（くずし字を読む の頁が使う）

前は図鑑の頁そのものの試験（印の無い文を出さない・採らなかった読みを出さない）だった。その線は、くずし字を読む の頁（test_kuzushi）と、
文の印の床（下の 4）で見る。
"""
import os
import re
import tempfile
import threading
import urllib.error
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from omochae import labels  # noqa: E402
from web import about as about_mod  # noqa: E402
from web import zukan, zukan_hon  # noqa: E402
from web.play_server import serve  # noqa: E402

G, T = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"
server = serve(0)
base = f"http://127.0.0.1:{server.server_address[1]}"
threading.Thread(target=server.serve_forever, daemon=True).start()


def get(path):
    try:
        r = urllib.request.urlopen(base + path)
        return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


try:
    # 1
    for path in ("/zukan", f"/zukan/{G}", f"/zukan/{T}"):
        assert get(path)[0] == 404, path
    # 2
    first = zukan_hon.frames()[0]
    assert get(f"/zukan/hon/{first}")[0] == 200, "本の頁が無い"
    assert get(f"/zukan/{G}/yomi")[0] == 200, "くずし字を読む が無い"
    # 3
    for path in ("/", "/about", f"/toy/{G}", f"/toy/{T}", f"/zukan/{G}/yomi", f"/zukan/hon/{first}", "/gallery"):
        body = get(path)[1]
        assert not re.search(r'href="/zukan(?:/NDL-[^"/]*)?"', body), (path, "図鑑の頁への道が残った")
    about = get("/about")[1]
    assert f'<a href="/zukan/hon/{first}">本でよむ</a>' in about and about_mod.BOOK_GO == "本でよむ", "序の頁に本の頁の入口が無い（字は本人の決め「本でよむ」）"
    yomi = get(f"/zukan/{G}/yomi")[1]
    assert f'<a href="/toy/{G}">' in yomi, "くずし字を読む の玩具の名から玩具の頁へ行かない"
finally:
    server.shutdown()

# 4
for bad in ([{"text": "印の無い文"}], [{"text": "飾り", "label": "演出"}], [{"text": "裏付けの無い引用", "label": labels.QUOTE}]):
    try:
        zukan.guard(bad)
        raise AssertionError(bad)
    except zukan.Unlabeled:
        pass
z = zukan.lines_for(G)
assert not labels.check(z["quotes"] + z["observations"] + z["hypotheses"])
print("ok 図鑑の頁は無い・本の頁とくずし字を読む は残る・図鑑への道は無い・文の印の床は残る")
