"""どの頁でも同じ頭の帯が出て、今いる所が分かる。<title> の形がそろう（#125、要件 2「骨を 1 つにする」）。

なぜ要るか: 帯に「うつし」が 2 つ並び、今いる所の印は字の色だけで、入口だけ別の帯だった。入口から内側へ入ると、帯の項目と順が変わった。
<title> は頁ごとに形が違い、入口は作る側の案の名前（日本画展の展示・縦読みのジン）を出していた。
"""
import os
import re
import tempfile
import threading
import urllib.error
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from omochae import hypotheses, records  # noqa: E402
from web.play_server import serve  # noqa: E402

G = "NDL-1187053-R0000005-L"
# 予想の段は #266 で外したので、予想を置かずに全部の頁が開く
records.add({"source_id": G, "hypothesis_id": "H-A", "sheet_version": 1, "result": "動いた"})
# 頁と、帯で印の付く項目（None は印なし。順路の外の頁）。kazasu と tsukuru は別の枝（#242）で形が変わるので入れない
PAGES = {"/": "うつし", "/about": "序", "/toys": "おもちゃ", f"/toy/{G}": "おもちゃ", f"/toy/{G}/techo": "おもちゃ", "/gallery": "作った物と職人の言葉",
         "/zukan": "図鑑", f"/zukan/{G}": "図鑑", f"/zukan/{G}/yomi": "図鑑", "/loop": None, f"/loop/{G}": None}
ITEMS = ["うつし", "序", "おもちゃ", "作った物と職人の言葉", "図鑑", "English"]
printed = False
for look in ("tenji", "zine"):
    server = serve(0, look=look)
    base = f"http://127.0.0.1:{server.server_address[1]}"
    threading.Thread(target=server.serve_forever, daemon=True).start()
    if not printed:
        urllib.request.urlopen(urllib.request.Request(f"{base}/toy/{G}/print", data=b"hypothesis=H-A", headers={"Origin": base}), timeout=120)
        printed = True
    for path, here in PAGES.items():
        where = (look, path)
        page = urllib.request.urlopen(base + path, timeout=60).read().decode()
        # 別の帯が残っていない
        assert 'class="switch"' not in page, ("入口だけ別の帯", where)
        navs = re.findall(r'<nav class="nav">(.*?)</nav>', page, re.S)
        assert len(navs) == 1, ("帯は 1 つ", where, len(navs))
        # 項目と順が全部の頁で同じ。「うつし」は 1 つ
        names = re.findall(r"<a [^>]*>([^<]+)</a>", navs[0])
        assert names == ITEMS, ("帯の項目と順", where, names)
        # 今いる所は色以外でも分かる（aria-current と、下の罫）
        current = re.findall(r'<a [^>]*aria-current="page"[^>]*>([^<]+)</a>', navs[0])
        assert current == ([here] if here else []), ("今いる所の印", where, current)
        assert re.search(r"\.nav a\[aria-current=page\]\{[^}]*border-bottom:1px solid", page), ("印に罫が無い", where)
        # <title> は「頁の名前 · うつし」。入口は「うつし」。作る側の案の名前を出さない
        title = re.search(r"<title>([^<]*)</title>", page).group(1)
        if path == "/":
            assert title == "うつし", ("入口の題", where, title)
        else:
            assert re.fullmatch(r"(?!うつし · ).+ · うつし", title), ("題の形", where, title)
        assert not re.search("日本画展|縦読みのジン|展示案", title), ("案の名前", where, title)
        # スマホの幅で「図鑑」だけ次の行に落ちないよう、brand を 1 段目に置く。本当の段は tests/measure_tap.py が測る
        assert ".nav .brand{flex:none;white-space:nowrap;margin-right:100%}" in page, ("帯の段", where)
        # 床は帯の CSS より後ろ（前だと帯の字の大きさが戻る。入口で見つけた）
        assert page.rindex("min-height:44px") > page.rindex(".nav{display:flex"), ("床の順", where)
        assert ".zukan .nav{" not in page, ("図鑑の CSS が帯に掛かる", where)
        # 入口の頁でも、帯のリンクに下線を付けない（入口の a の指定が帯に掛かっていた。目で見て見つけた）
        if path == "/":
            assert "body .nav a:not([aria-current=page]){border-bottom:0" in page, ("入口の帯の下線", where)
        # 図鑑の頁でも、帯のリンクに下線を付けない（.zukan a が帯に掛かっていた）
        if "/zukan" in path:
            assert ".zukan .nav a:not([aria-current])" in page, ("図鑑の帯の下線", where)
    # 断りの頁の帯にも印は付かない（どこにもいないので）
    try:
        urllib.request.urlopen(f"{base}/no-such-page", timeout=60)
        raise AssertionError("404 のはず")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        assert e.code == 404 and 'aria-current="page"' not in re.search(r'<nav class="nav">(.*?)</nav>', body, re.S).group(1), e.code
    server.shutdown()
print("ok")
