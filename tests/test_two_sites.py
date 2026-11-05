"""皮ごとに 1 サイト（本人の決定 11-05 朝「日本画かジンで行く。それぞれのデザインのサイトを 2 つ作る」）。本物の API は呼ばない。

なぜ: 1 つのサイトの中で見た目を切り替える形（cookie・?look=）をやめた。白の展示のサーバと黒のジンのサーバを別に立て、
どちらも入口から玩具の頁へ入れ、皮が全部の頁で同じで、相手の皮の入口は無く、切り替えのリンクも無い事を見る。大判（A）は無い。
"""
import os
import tempfile
import threading
import urllib.error
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from web.play_server import serve  # noqa: E402

G = "NDL-1187053-R0000005-L"


def up(look):
    server = serve(0, look=look)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"

    def get(path):
        try:
            r = urllib.request.urlopen(base + path)
            return r.status, r.read().decode()
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode()
    return get


try:
    serve(0, look="taiban")
    raise AssertionError("無い皮で立ってしまう")
except ValueError:
    pass

# 入口の皮は <body> の印で見分ける。<title> に作る側の案の名前は出さない（#125）
for look, other, title in (("tenji", "zine", '<body class="tenji"'), ("zine", "tenji", '<body class="zine"')):
    get = up(look)
    code, home = get("/")
    assert code == 200 and title in home and f"/toy/{G}" in home and "大判写真集" not in home, look
    assert get(f"/look/{look}")[0] == 200 and get(f"/look/{other}")[0] == 404 and get("/look/taiban")[0] == 404, look
    # 内側の頁は全部この皮。?look= を付けても変わらず、切り替えのリンクも無い
    for path in ("/about", "/toys", "/gallery", "/zukan", f"/toy/{G}", f"/toys?look={other}"):
        code, body = get(path)
        assert code == 200 and f'class="skin-{look}' in body and f'skin-{other}' not in body and "?look=" not in body, (look, path)

# 記録は 2 サイトで共有（本人の決定 11-05 朝、カード 083822 の判断 1）: 白の展示で残した自分の仮説が、黒のジンの同じ玩具の図鑑で見える

tenji, zine = up("tenji"), up("zine")
assert "先に、予想を書く" not in zine(f"/toy/{G}")[1]
from omochae import hypotheses  # noqa: E402

assert hypotheses.save_own(G, "白の展示で書いた仮説", "下から押す", "筒の下の線")[1] == []
assert "白の展示で書いた仮説" in zine(f"/zukan/{G}")[1] and "白の展示で書いた仮説" in tenji(f"/zukan/{G}")[1]
print("ok: 皮ごとに 1 サイト、記録は共有")
