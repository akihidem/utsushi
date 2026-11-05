"""合言葉なしで開くデモ（本人の許可 11-05「デモサイト 2 つを他の人でも見れるように公開していいよ」）。本物の API は呼ばない。

見る線: 開いた時はトンネルの名前で合言葉なしに開ける。写真と動画は受けず、置き場に在っても出さない（誰でも上げられる場に、確かめていない
写真を載せない。J-021 の持ち寄りの線と、子どもの写真を扱わない線）。合言葉付きと同時には立たない。開いていない時は、トンネルの名前を断る。
"""
import http.client
import io
import os
import tempfile
import threading

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from PIL import Image  # noqa: E402

from omochae import records  # noqa: E402
from web import techo_site  # noqa: E402
from web.play_server import serve  # noqa: E402

G = "NDL-1187053-R0000005-L"
HOST = "plain-words-here.trycloudflare" + ".com"  # 作り物の名前。門がトンネルの名前の形を落とすので、字の並びを分けて書く
# 受け口は中身が読める写真だけを受ける（#187 の床）ので、本物の小さな JPEG を作る
_photo = io.BytesIO()
Image.new("RGB", (8, 8), (200, 180, 140)).save(_photo, "JPEG")
jpeg = _photo.getvalue()

try:
    serve(0, public_key="k" * 20, public_open=True)
    raise AssertionError("合言葉付きと合言葉なしが同時に立ってしまう")
except ValueError:
    pass


# 鍵のある所では開かない（誰でも費用のかかる呼び出しができてしまう）。この試験は鍵のある機械でも同じに動くよう、鍵の有無を固定する
from api import ask  # noqa: E402

ask._key_present = lambda: True
try:
    serve(0, public_open=True)
    raise AssertionError("鍵のある所で開いてしまう")
except ValueError:
    pass
ask._key_present = lambda: False


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
assert opened("POST", f"/toy/{G}/print", "hypothesis=H-A", form)[0] == 303
assert opened("POST", f"/toy/{G}/record", "hypothesis=H-A&result=%E5%8B%95%E3%81%84%E3%81%9F", form)[0] == 303
rid = records.all_records(G)[-1]["id"]
# 写真と動画は受けない。手帖の口も閉じてある
code, body = opened("POST", f"/record/{rid}/media", jpeg, {"Content-Type": "image/jpeg", "Origin": f"https://{HOST}"})
assert code == 403 and "上げられません" in body, (code, body)
techo = opened("GET", f"/toy/{G}/techo")[1]
assert 'id="files" disabled' in techo and "公開のデモでは、写真と動画は上げられません" in techo
assert 'id="picked"' in techo and 'id="thumbs"' in techo and "3 つまで" not in techo, "閉じた口でも台本の探す欄は残し、上げられる数は言わない（#144）"
# 置き場に写真が在っても出さない
assert techo_site.save_media(rid, "image/jpeg", jpeg)[0]
assert opened("GET", f"/record/{rid}/media/m1.jpg")[0] == 404
# 頁とギャラリーにも画像の道を出さない（壊れた絵にしない。#242 のギャラリー）
assert f"/record/{rid}/media/" not in opened("GET", f"/toy/{G}")[1] and f"/record/{rid}/media/" not in opened("GET", "/gallery")[1]
assert f"/record/{rid}/media/" not in opened("GET", f"/toy/{G}/techo")[1], "手帖の自分の記録も、壊れた絵を出さない"
# 人の書いた文は別の人に見せない（文の中の名前は機械で落とせない。J-028）
assert opened("POST", f"/toy/{G}/record", "hypothesis=H-A&result=%E5%8B%95%E3%81%84%E3%81%9F&impression=SECRETWORDS", form)[0] == 303
assert "SECRETWORDS" not in opened("GET", f"/toy/{G}")[1] and "SECRETWORDS" not in opened("GET", "/gallery")[1]
# 別の出所からは書けない（開いていても）
assert opened("POST", f"/toy/{G}/own", "name=x", {"Content-Type": "application/x-www-form-urlencoded", "Origin": "https://evil.example"})[0] == 403
# 作る側の頁は出さない（聞いた言葉と感想の文が読める頁で、名前は機械では落とせない）。開いていない時は出る
assert opened("GET", "/loop")[0] == 404 and opened("GET", f"/loop/{G}")[0] == 404
# 次の版を採る口と AI の口は閉じる（誰でも型紙の版を変えられる形にしない・費用をかけさせない）
assert opened("POST", f"/record/{rid}/next", "interpretation=x&param=fold_count&to=24&why=x&by=x", form)[0] == 403
assert opened("POST", f"/record/{rid}/ai-interpret", "x=1", form)[0] == 403 and opened("POST", f"/record/{rid}/ai-observe", "x=1", form)[0] == 403
# 記録の欄に、名前を書かない断りがある
assert "名前や連絡先は書かないでください" in opened("GET", f"/toy/{G}")[1]
print("ok: 合言葉なしで開くデモ")
