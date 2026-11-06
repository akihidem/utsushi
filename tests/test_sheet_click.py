"""型紙を押すと画面に型紙そのものが出る（本人の指示 11-05、デモを見て「ダウンロードだけではなく、クリックで画面に出る形」）。

なぜ: 前は仮説の札の字のリンクと記録の「試した後の紙」が PDF へ直に飛び、機器によっては落とすだけで画面に紙が出なかった。
字のリンクは窓（#win）へ向け、窓は絵（PNG）を出し、押すと拡大（#zoom）。PDF は別のタブでインラインに開く。本物の API は呼ばない。
"""
import os
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from web.play_server import serve  # noqa: E402

G = "NDL-1187053-R0000005-L"
from omochae import hypotheses  # noqa: E402
# 御来迎のたたき台は組ごと（今の組 goraigo-v14 は H-C・記録の欄 sheet_by_set）。今の組で刷れるのはたたき台の紙だけ
GS = hypotheses.sheet_of(G)["id"]
server = serve(0)
port = server.server_address[1]
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{port}"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


opener = urllib.request.build_opener(NoRedirect)


def get(path):
    try:
        r = opener.open(base + path)
        return r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read(), dict(e.headers)


def post(path, data):
    req = urllib.request.Request(base + path, data=urllib.parse.urlencode(data).encode(), method="POST",
                                 headers={"Content-Type": "application/x-www-form-urlencoded", "Origin": base})
    try:
        return opener.open(req).status
    except urllib.error.HTTPError as e:
        return e.code


assert post(f"/toy/{G}/print", {"hypothesis": GS}) == 303
code, body, _ = get(f"/toy/{G}")
body = body.decode()
# 紙を選ぶ字の札は窓へ。PDF へ直に飛ぶ字のリンクは置かない（窓の押し釦だけ）
assert f'href="/toy/{G}?see={GS}&kind=sheet&v=1#win" aria-current="true">型紙</a>' in body
# 刷るのは型紙だけ（本人の決まり 11-06）。手順の紙の札は出ない
assert "kind=tejun" not in body and ">手順の紙</a>" not in body
assert body.count(f'href="/sheet/{G}/{GS}_v1.pdf"') == 1 and 'target="_blank"' in body.split(f'href="/sheet/{G}/{GS}_v1.pdf"')[1][:40]
# 窓: 絵が出て、押すと拡大の窓
# 前の札のリンク（kind=tejun）で来ても、窓は型紙を出す。手順の紙の絵の道は、作りながら見る頁のために残る
code, win, _ = get(f"/toy/{G}?see={GS}&kind=tejun&v=1")
win = win.decode()
assert f'<img src="/sheet/{G}/{GS}_v1.png"' in win and "_tejun.png" not in win and 'href="#zoom"' in win and 'id="zoom"' in win
assert get(f"/sheet/{G}/{GS}_v1_tejun.png")[0] == 200
# PDF はインラインの印付きで、ブラウザが開ける
code, pdf, headers = get(f"/sheet/{G}/{GS}_v1.pdf")
assert code == 200 and pdf[:4] == b"%PDF" and headers.get("Content-Disposition", "").startswith("inline;"), headers
# 記録の前も後も、試した後の紙の字のリンクは出ない（11-06 から刷らない）
assert "kind=after" not in body
assert post(f"/toy/{G}/record", {"hypothesis": GS, "result": "動かない", "opened_deg": "40", "opener": "紙の力", "stuck": "3 枚目"}) == 303
code, body, _ = get(f"/toy/{G}")
body = body.decode()
assert "kind=after" not in body and ">試した後の紙</a>" not in body
assert "_after.png" not in get(f"/toy/{G}?see={GS}&kind=after&v=1")[1].decode()
print("ok: 型紙はクリックで画面に出る")
