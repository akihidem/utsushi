"""断りの頁（404・403・500）が、何が起きたかと戻り方を読める形で、皮の地に出る事を見る（#136）。

合言葉の門は別に見る。リンクを落とした人が最初に見る頁なので、頁の中身と玩具の名前を漏らさない。
写真と動画の口は手帖の頁の JS が文をそのまま画面に出すので、ここだけ素の文のまま残す。
"""
import os
import re
import tempfile
import threading
import urllib.error
import urllib.request

_data = tempfile.TemporaryDirectory()
os.environ["OMOCHAE_DATA"] = _data.name

from web import play_server  # noqa: E402

G = "NDL-1187053-R0000005-L"
KEY = "k" * 8 + "aikotoba" + "k" * 8
opener = urllib.request.build_opener(type("N", (urllib.request.HTTPRedirectHandler,), {"redirect_request": lambda *a, **k: None}))


def start(**kw):
    server = play_server.serve(0, **kw)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


def call(base, path, data=None, headers=None):
    req = urllib.request.Request(base + path, data=data, method="POST" if data is not None else "GET", headers=headers or {})
    try:
        r = opener.open(req, timeout=20)
        return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def page(code, body, reason, skin="tenji"):
    """皮の地・lang・題・理由が揃った頁かを見る。"""
    assert code == page.want, (code, body[:120])
    assert '<html lang="ja"' in body, body[:120]
    assert re.search(r"<title>[^<]+</title>", body), body[:200]
    assert f"skin-{skin}" in body, body[:400]
    assert reason in body, body[:400]


server, base = start()
FORM = {"Content-Type": "application/x-www-form-urlencoded", "Origin": base}

# 無い道: 白の展示と黒のジンのどちらでも、入口と一覧へ戻れる
page.want = 404
for look in ("tenji", "zine"):
    # 皮の決め方に寄らないよう、同じ要求で開いた普通の頁と同じ皮かを見る
    headers = {"Cookie": f"look={look}"}
    skin = re.search(r"skin-(\w+)", call(base, "/about", headers=headers)[1]).group(1)
    code, body = call(base, "/mada/nai", headers=headers)
    page(code, body, "見つかりません", skin)
    assert 'href="/"' in body and 'href="/toys"' in body
# 無い道への POST も同じ頁
code, body = call(base, "/mada/nai", data=b"a=1", headers=FORM)
page(code, body, "見つかりません")
assert 'href="/"' in body

# 記録の前に試した後の紙を開く: 玩具の頁の記録の欄へ戻れる
page.want = 403
assert call(base, f"/toy/{G}/predict", data=b"text=x", headers=FORM)[0] == 303
assert call(base, f"/toy/{G}/print", data=b"hypothesis=H-A", headers=FORM)[0] == 303
code, body = call(base, f"/sheet/{G}/H-A_v1_after.pdf")
page(code, body, "試した記録を残してから開きます")
assert f'href="/toy/{G}#kiroku"' in body

# 別のサイトからの送信を断る頁
code, body = call(base, f"/toy/{G}/predict", data=b"text=x", headers={**FORM, "Origin": "http://evil.example"})
page(code, body, "受け付けられない送り方です")

# 手元の名前でない Host には、同じ名前へ戻るリンクを出さない
code, body = call(base, "/", headers={"Host": "evil.example"})
page(code, body, "受け付けられません")
assert "href=" not in body and "<nav" not in body

# 中で失敗した時: GET も POST も、理由の文だけで例外の中身を出さない
page.want = 500
real_get, real_post = play_server.Handler._get, play_server.Handler._post


def boom(self):
    raise RuntimeError("中の値")


play_server.Handler._get = play_server.Handler._post = boom
try:
    code, body = call(base, "/")
    page(code, body, "うまく表示できませんでした")
    assert 'href="/"' in body and "中の値" not in body
    code, body = call(base, "/", data=b"a=1", headers=FORM)
    page(code, body, "受け付けられませんでした")
    assert 'href="/"' in body and "中の値" not in body
finally:
    play_server.Handler._get, play_server.Handler._post = real_get, real_post

# 写真と動画の口は、手帖の JS が文をそのまま出すので素の文のまま
code, body = call(base, "/record/R-0001/media", data=b"x", headers={"Content-Type": "image/jpeg", "Origin": "http://evil.example"})
assert code == 403 and "<" not in body, body[:120]
server.shutdown()

# 合言葉の門: 帯もリンクも玩具の名前も出さず、聞く先だけを言う
server, base = start(public_key=KEY)
page.want = 403
for path in ("/", f"/toy/{G}", "/mada/nai"):
    code, body = call(base, path)
    page(code, body, "合言葉付きのリンクから開いてください")
    assert "リンクを渡した人に聞いてください" in body
    assert "<nav" not in body and "href=" not in body and "class=\"foot\"" not in body, body[:400]
    for leak in ("御来迎", "張子", "江都二色", "/toy/", G):
        assert leak not in body, leak
server.shutdown()
print("ok")
