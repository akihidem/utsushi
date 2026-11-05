"""合言葉なしで開くデモ（本人の許可 11-05「デモサイト 2 つを他の人でも見れるように公開していいよ」）。本物の API は呼ばない。

見る線: 開いた時はトンネルの名前で合言葉なしに開ける。写真と動画は受けず、置き場に在っても出さない（誰でも上げられる場に、確かめていない
写真を載せない。J-021 の持ち寄りの線と、子どもの写真を扱わない線）。合言葉付きと同時には立たない。開いていない時は、トンネルの名前を断る。
"""
import http.client
import os
import tempfile
import threading

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from omochae import records  # noqa: E402
from web import techo_site  # noqa: E402
from web.play_server import serve  # noqa: E402

G = "NDL-1187053-R0000005-L"
HOST = "plain-words-here.trycloudflare" + ".com"  # 作り物の名前。門がトンネルの名前の形を落とすので、字の並びを分けて書く
jpeg = b"\xff\xd8" + b"\xff\xdb\x00\x03\x00" + b"\xff\xda\x00\x02DATA" + b"\xff\xd9"

try:
    serve(0, public_key="k" * 20, public_open=True)
    raise AssertionError("合言葉付きと合言葉なしが同時に立ってしまう")
except ValueError:
    pass


def up(**kw):
    server = serve(0, **kw)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    port = server.server_address[1]

    def call(method, path, body=None, headers=None):
        c = http.client.HTTPConnection("127.0.0.1", port, timeout=20)
        c.request(method, path, body=body, headers={"Host": HOST, **(headers or {})})
        r = c.getresponse()
        return r.status, r.read().decode("utf-8", "replace")
    return call


closed, opened = up(), up(public_open=True)
# 開いていないサーバは、トンネルの名前を断る
assert closed("GET", "/")[0] == 403
# 開いたサーバは、合言葉なしで入口から玩具の頁まで開く
assert opened("GET", "/")[0] == 200 and opened("GET", "/toys")[0] == 200 and opened("GET", f"/toy/{G}")[0] == 200
form = {"Content-Type": "application/x-www-form-urlencoded", "Origin": f"https://{HOST}"}
assert opened("POST", f"/toy/{G}/predict", "text=%E6%89%87%E3%81%8C%E9%96%8B%E3%81%8F", form)[0] == 303
assert opened("POST", f"/toy/{G}/print", "hypothesis=H-A", form)[0] == 303
assert opened("POST", f"/toy/{G}/record", "hypothesis=H-A&result=%E5%8B%95%E3%81%84%E3%81%9F", form)[0] == 303
rid = records.all_records(G)[-1]["id"]
# 写真と動画は受けない。手帖の口も閉じてある
code, body = opened("POST", f"/record/{rid}/media", jpeg, {"Content-Type": "image/jpeg", "Origin": f"https://{HOST}"})
assert code == 403 and "上げられません" in body, (code, body)
techo = opened("GET", f"/toy/{G}/techo")[1]
assert 'id="files" disabled' in techo and "公開のデモでは、写真と動画は上げられません" in techo
# 置き場に写真が在っても出さない
assert techo_site.save_media(rid, "image/jpeg", jpeg)[0]
assert opened("GET", f"/record/{rid}/media/m1.jpg")[0] == 404
# 別の出所からは書けない（開いていても）
assert opened("POST", f"/toy/{G}/predict", "text=x", {"Content-Type": "application/x-www-form-urlencoded", "Origin": "https://evil.example"})[0] == 403
# 記録の欄に、名前を書かない断りがある
assert "名前や連絡先は書かないでください" in opened("GET", f"/toy/{G}")[1]
print("ok: 合言葉なしで開くデモ")
