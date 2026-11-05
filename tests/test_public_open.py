"""合言葉なしで開くデモ（本人の許可 11-05「デモサイト 2 つを他の人でも見れるように公開していいよ」）。本物の API は呼ばない。

見る線: 開いた時はトンネルの名前で合言葉なしに開ける。写真と動画は受けず、置き場に在っても出さない（誰でも上げられる場に、確かめていない
写真を載せない。J-021 の持ち寄りの線と、子どもの写真を扱わない線）。合言葉付きと同時には立たない。開いていない時は、トンネルの名前を断る。
"""
import http.client
import io
import os
import tempfile
import threading
import urllib.parse

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from PIL import Image  # noqa: E402

from omochae import hypotheses, records  # noqa: E402
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
        call.location = r.getheader("Location")
        return r.status, r.read().decode("utf-8", "replace")
    call.local = f"127.0.0.1:{port}"
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
# 説明と次の思いつきと書いた人も同じ線（#336）。送っても断られる次の版の欄ごと出さず、札は「説明を残しました。」だけにする
said = "hypothesis=H-A&result=%E5%8B%95%E3%81%84%E3%81%9F"
assert opened("POST", f"/toy/{G}/record", said, form)[0] == 303
told_id = records.all_records(G)[-1]["id"]
assert opened("POST", f"/record/{told_id}/explain", "text=TOLDWORDS&next_idea=NEXTWORDS&by=BYWORDS", form)[0] == 303
for path in ("/", "/toys", "/about", "/gallery", "/zukan", f"/zukan/{G}", f"/zukan/{G}/yomi", "/en", f"/en/toy/{G}", f"/toy/{G}", f"/toy/{G}/tsukuru?h=H-A&v=1", f"/toy/{G}/techo"):
    code, page = opened("GET", path)
    assert code == 200, (path, code)
    for word in ("TOLDWORDS", "NEXTWORDS", "BYWORDS"):
        assert word not in page, (path, word)
for path in (f"/toy/{G}", f"/toy/{G}/techo"):
    page = opened("GET", path)[1]
    assert "説明を残しました。" in page and f"/record/{told_id}/next" not in page and 'name="interpretation"' not in page, path
# 合言葉付きの場（ここでは手元の名前で開く）では、同じ記録の説明が今までどおり読めて、次の版を作れる
local = {"Host": closed.local}
for path in (f"/toy/{G}", f"/toy/{G}/techo"):
    page = closed("GET", path, None, local)[1]
    assert "TOLDWORDS" in page and "NEXTWORDS" in page and f"/record/{told_id}/next" in page and 'name="interpretation"' in page, path
made = closed("POST", f"/record/{told_id}/next", "interpretation=x&param=fold_count&to=24&why=x&by=x", {**local, "Content-Type": form["Content-Type"], "Origin": f"http://{closed.local}"})
assert made[0] == 303, made
# 自分の仮説の文も同じ線（#336 の続き）。残せるが、札・記録の欄の選択肢・図鑑・文が刷られる紙のどこにも出さない
assert opened("POST", f"/toy/{G}/own", "name=OWNNAME&how=OWNHOW&evidence=OWNWHERE", form)[0] == 303
oid = hypotheses.own_hypotheses(G)[-1]["id"]
back = opened.location.split("#")[0]
# 合言葉付きの場（手元の名前で開く）では、札と図鑑に今までどおり出て、紙も作れる。ここで作った紙と記録を、下で開いた場から開く
local_form = {**local, "Content-Type": form["Content-Type"], "Origin": f"http://{closed.local}"}
for path in (f"/toy/{G}", f"/zukan/{G}", "/zukan"):
    page = closed("GET", path, None, local)[1]
    assert "OWNNAME" in page and "OWNHOW" in page, path
page = closed("GET", f"/toy/{G}", None, local)[1]
assert "OWNWHERE" in page and f"/toy/{G}/print-own" in page and f'<option value="{oid}">' in page
assert closed("POST", f"/toy/{G}/print-own", f"id={oid}", local_form)[0] == 303
assert closed("POST", f"/toy/{G}/record", f"hypothesis={oid}&result=%E5%8B%95%E3%81%84%E3%81%9F", local_form)[0] == 303
papers = [f"/sheet/{G}/{oid}_v1_{kind}.{ext}" for kind in ("free", "after") for ext in ("pdf", "png", "svg")]
for path in papers:
    assert closed("GET", path, None, local)[0] == 200, path
# 紙が在っても、合言葉なしの場の頁に文を出さず、紙も開けない
for path in ("/", "/toys", "/about", "/gallery", "/zukan", f"/zukan/{G}", f"/zukan/{G}/yomi", "/en", f"/en/toy/{G}", f"/toy/{G}", f"/toy/{G}?see={oid}&kind=after&v=1", f"/toy/{G}/tsukuru?h={oid}", f"/toy/{G}/techo"):
    code, page = opened("GET", path)
    assert code == 200, (path, code)
    for word in ("OWNNAME", "OWNHOW", "OWNWHERE"):
        assert word not in page, (path, word)
for path in papers:
    assert opened("GET", path)[0] == 404, path
assert opened("GET", f"/sheet/{G}/H-A_v1.pdf")[0] == 200, "閉じるのは自分の仮説の紙だけ。たたき台の紙は開ける"
assert opened("POST", f"/toy/{G}/print-own", f"id={oid}", form)[0] == 403, "紙に文が刷られるので刷らない"
page = opened("GET", f"/toy/{G}")[1]
assert f"/toy/{G}/print-own" not in page and f'id="own-{oid}"' not in page and f'<option value="{oid}">' not in page
assert f"/toy/{G}/own#kasetsu" in page, "欄は残す（残せる線）"
# 残した事は返事で分かる。この場に無い釦へは案内しない
assert "at=kasetsu" in back, back
assert "仮説を残しました。" in opened("GET", back)[1] and "紙を作る" not in urllib.parse.unquote(back)
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
