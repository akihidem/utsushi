"""デモの一周（本人の指示、11-04「パソコン、iPad、iPhoneからできるように」）。選ぶ → 型紙 → 作る → 質問 → 上げる → フィードバック → 次の版 を、
家の網に開いたサーバ（--lan）へ、網の中の番地の Host で通す（iPad・iPhone から開いた時と同じ形）。鍵は使わない（質問は決まった言葉への答えだけ）。
作る（紙を切って組む）は手の仕事なので、刷った紙が開ける所までを確かめる。"""
import io
import re
import json
import os
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from PIL import Image  # noqa: E402

from api import ask  # noqa: E402
from omochae import media_review  # noqa: E402

ask._key_present = lambda: False  # 鍵が置かれた機械でも、この試験は鍵なしの道だけを通す

from web.play_server import serve  # noqa: E402

server = serve(0, lan=True, bind="127.0.0.1")  # 番地の許しは --lan のまま、試験の間は手元の口で待つ
port = server.server_address[1]
threading.Thread(target=server.serve_forever, daemon=True).start()
host = f"{(server.lan_hosts or ('127.0.0.1',))[0]}:{port}"
SID = "NDL-1187053-R0000005-L"


def call(path, form=None, body=None, ctype=None):
    data = urllib.parse.urlencode(form).encode() if form is not None else body
    headers = {"Host": host}
    if data is not None:
        headers |= {"Origin": f"http://{host}", "Content-Type": ctype or "application/x-www-form-urlencoded"}
    r = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data, headers=headers)
    try:
        with urllib.request.urlopen(r) as res:
            return res.status, res.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


# 選ぶ
code, top = call("/")
assert code == 200 and f"/toy/{SID}".encode() in top
# 予想の段は無い（#242）。開いたらすぐ手帖が開く
assert call(f"/toy/{SID}/techo")[0] == 200
# 型紙
assert call(f"/toy/{SID}/print", {"hypothesis": "H-A"})[0] in (200, 303)
code, pdf = call(f"/sheet/{SID}/H-A_v1.pdf")
assert code == 200 and pdf[:4] == b"%PDF", "刷った紙が開ける（作るのはこの紙で）"
assert call(f"/sheet/{SID}/H-A_v1_after.pdf")[0] == 403, "試した後の紙は記録の前は渡さない"
# 手帖と質問（鍵なし: 決まった言葉への答え）
assert call(f"/toy/{SID}/techo")[0] == 200
code, ans = call(f"/toy/{SID}/ask-json", {"hypothesis": "H-A", "question": "谷折りって？"})
got = json.loads(ans)
assert code == 200 and got["from"] == "glossary" and got["text"], got
# 語が入っていても作り方を聞く問いには、語の説明だけを返さない（#287）
code, ans = call(f"/toy/{SID}/ask-json", {"hypothesis": "H-A", "question": "蛇腹が固定できない。どうしたらいい？"})
got = json.loads(ans)
assert code == 200 and got["from"] == "no_key" and got["text"] != ask.GLOSSARY["蛇腹"], got
# 上げる（記録 → 写真）
code, rec = call(f"/toy/{SID}/record-json", {"hypothesis": "H-A", "result": "動いた", "note": "筒を先に丸めた"})
rid = json.loads(rec)["id"]
buf = io.BytesIO()
Image.new("RGB", (64, 48), (200, 180, 140)).save(buf, "JPEG")
code, name = call(f"/record/{rid}/media", body=buf.getvalue(), ctype="image/jpeg")
assert code == 201, name
# フィードバック（人の説明が先）
assert call(f"/record/{rid}/explain", {"by": "本人", "text": "筒が支えになった", "next_idea": "折りを増やす", "back": "techo"})[0] in (200, 303)
code, techo = call(f"/toy/{SID}/techo/kiroku")
assert "次の版".encode() in techo, "説明の後に次の版の口が出る"
# 次の版
form = {"interpretation": "折りが多く、筒の口に当たって開き切らない", "param": "fold_count", "why": "口に当たらないように", "by": "本人", "back": "techo"}
code, out = call(f"/record/{rid}/next", form | {"to": "29"})
assert code == 422 and "筒の口の角に当たって" in out.decode(), "床に落ちる値は刷らず、理由を見せる"
code, out = call(f"/record/{rid}/next", form | {"to": "26"})
assert code in (200, 303), re.findall(r'<p id="msg">(.*?)<', out.decode()) or out.decode()[-600:]
assert call(f"/sheet/{SID}/H-A_v2.pdf")[1][:4] == b"%PDF", "次の版の紙が開ける"
# ギャラリー（見本も並ぶ）
assert f"/record/{rid}/media/" not in call("/gallery")[1].decode(), "人の確認の前は出さない（#314）"
assert media_review.record(rid, media_review.waiting()[0][1], "object", "確認者") == []
gallery = call("/gallery")[1].decode()
assert f"/record/{rid}/media/" in gallery and "見本" in gallery, "上げた写真と見本が並ぶ"
server.shutdown()
print("ok")
