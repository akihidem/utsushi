"""のこした後の「この画面をとじる」で、この画面の写真の鍵と記録の鍵が消える（設計は grove の state/screen-close-20261108.md）。

なぜ: 1 台を順に使う場では、前の人の写真の鍵（確かめる前の写真を上げた画面に 2 時間見せる）と記録の鍵（今残した 1 つの札と、字を足す口）が、
次の人が記録を残すまでその画面に残り、次の人に前の人の確かめる前の写真と札が見えた（のこすの流れの設計の別の目の気づき 9）。
見る事は 4 つ: 1 とじると 2 つの鍵が消える／2 外の頁からはとじさせない（Origin）／3 とじた後は前の確かめる前の写真が見えない／
4 釦はのこした直後の返事の下だけで、道しるべの釦にしない（公開の場も同じ形で、公開の場だけの断りは置かない・本人 11-08）。
"""
import http.cookiejar
import io
import json
import os
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(os.environ["OMOCHAE_DATA"], "api-usage.jsonl")

from PIL import Image  # noqa: E402

from omochae import hypotheses  # noqa: E402
from web import play_server, techo_site  # noqa: E402


class Stay(urllib.request.HTTPRedirectHandler):
    """303 を追わない（とじた時の返事の見出しを、そのまま見るため）。"""

    def redirect_request(self, *args, **kw):
        return None


server = play_server.serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"
jar = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar), Stay)


def call(path, body=None, ctype="application/x-www-form-urlencoded", origin=None):
    r = urllib.request.Request(base + path, data=body, headers={"Origin": origin or base, "Content-Type": ctype} if body is not None else {})
    try:
        with op.open(r) as x:
            return x.status, x.headers, x.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read().decode("utf-8", "replace")


keys = lambda: {c.name for c in jar}
G = "NDL-1187053-R0000005-L"
H = hypotheses.sheet_of(G)["id"]
form = lambda d: urllib.parse.urlencode(d).encode()
assert call(f"/toy/{G}/print", form({"hypothesis": H}))[0] in (200, 303)  # 303 を追わないので、刷った後の戻り先の返事のまま
code, _, body = call(f"/toy/{G}/record-json", form({"hypothesis": H, "result": "動いた", "impression": "扇が開いた"}))
rid = json.loads(body)["id"]
buf = io.BytesIO()
Image.effect_noise((32, 24), 40).convert("RGB").save(buf, "PNG")
code, _, name = call(f"/record/{rid}/media", buf.getvalue(), "image/png")
assert code == 201 and name == "m1.png", (code, name)
assert {play_server.UP_COOKIE, play_server.REC_COOKIE} <= keys(), keys()
photo = f"/record/{rid}/media/{name}"
assert photo in call(f"/toy/{G}/techo/kiroku")[2], "とじる前は、上げた画面に確かめる前の写真が出る（今の形）"

# 2 外の頁からはとじさせない: 別のサイトの頁が、この画面の鍵を消せないように（書き込みの口と同じ Origin の照らし）
code, headers, _ = call("/close", form({}), origin="https://example.com")
assert code == 403 and not headers.get_all("Set-Cookie"), (code, headers.get_all("Set-Cookie"))
assert {play_server.UP_COOKIE, play_server.REC_COOKIE} <= keys(), "外の頁からの頼みでは、鍵は残る"

# 1 とじると 2 つの鍵が消え、ギャラリーの返事へ。その場限りの印も作り直させる（fresh）
code, headers, _ = call("/close", form({}))
assert code == 303, code
assert headers["Location"] == f"/gallery?msg={urllib.parse.quote(techo_site.CLOSED)}&fresh=1#ageta", headers["Location"]
gone = headers.get_all("Set-Cookie")
for c in (play_server.UP_COOKIE, play_server.REC_COOKIE):
    assert any(h.startswith(f"{c}=;") and "Max-Age=0" in h and "HttpOnly" in h for h in gone), (c, gone)
assert not ({play_server.UP_COOKIE, play_server.REC_COOKIE} & keys()), keys()
# 鍵の無い画面でとじても同じ返事（鍵の有り無しを外へ見せない）
assert call("/close", form({}))[0] == 303

# 3 とじた後は、前の人の確かめる前の写真も、今残した 1 つの札も見えない
assert photo not in call(f"/toy/{G}/techo/kiroku")[2], "とじた後の手帖の記録の頁に、確かめる前の写真を出さない"
assert call(photo)[0] in (403, 404), "とじた後は、確かめる前の写真そのものも開かない"
code, _, page = call(f"/gallery?msg={urllib.parse.quote(techo_site.CLOSED)}")
assert code == 200 and 'id="own"' not in page, "とじた後のギャラリーに、前の人の今残した 1 つの札を出さない"

# 4 釦はのこした直後の返事の下だけ・道しるべの釦（.go）にしない・公開の場も同じ形（本人 11-08「公開デモだけのものはいらない。なにかあれば僕が対応するので。」）
shut = f'<form method="post" action="/close" class="close-screen"><button type="submit">{techo_site.CLOSE}</button></form>'
done = techo_site.gallery_page(play_server.sources(), msg="上げました")
assert shut in done and done.index('id="msg"') < done.index(shut), "のこした直後の返事のすぐ下に、とじる釦"
assert shut not in techo_site.gallery_page(play_server.sources()), "返事の無い時（ふつうに開いた時）は出さない"
assert shut not in techo_site.gallery_page(play_server.sources(), msg=techo_site.CLOSED), "とじた後の返事には出さない"
opened = techo_site.gallery_page(play_server.sources(), public=True, msg="上げました")
assert shut in opened and "取り下げられません" not in opened and "取り下げられません" not in done, "公開の場も同じ釦だけで、公開の場だけの断りの字は出さない"
assert 'class="go"' not in techo_site.close_form(), "道しるべの釦にしない（帯の駅の道しるべは 1 つ）"
assert shut in call(f"/gallery?msg={urllib.parse.quote('上げました')}")[2], "サーバの頁にも出る"
server.shutdown()
print("ok: のこした後の「この画面をとじる」で、この画面の写真の鍵と記録の鍵が消える")
