"""入口のサイトの中の手帖（本人の方向転換 11-04）。予想が先・仮説の名前と動き方を出さない・手順だけ答える・上げた物は記録に添い撮影情報を外す。"""
import json
import os
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from omochae import hypotheses  # noqa: E402
from web.play_server import serve  # noqa: E402
from web.techo_site import media_dir, strip_jpeg_meta  # noqa: E402

G = "NDL-1187053-R0000005-L"
server = serve(0)
port = server.server_address[1]
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{port}"


def req(path, data=None, ctype="application/x-www-form-urlencoded", origin=base):
    body = urllib.parse.urlencode(data).encode() if isinstance(data, dict) else data
    r = urllib.request.Request(base + path, data=body, method="POST" if body is not None else "GET", headers={"Content-Type": ctype, "Origin": origin})
    try:
        x = urllib.request.urlopen(r)
        return x.status, x.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


code, body = req(f"/toy/{G}/techo")
assert code == 200 and "先に予想を書く" in body.decode(), "予想の前は手帖を開かない"
assert req(f"/toy/{G}/predict", {"text": "筒を押すと扇が開く"})[0] in (200, 303)
assert req(f"/toy/{G}/print", {"hypothesis": "H-A"})[0] in (200, 303)
code, body = req(f"/toy/{G}/techo")
page = body.decode()
assert code == 200 and "手帖" in page and 'value="H-A"' in page and 'id="mic"' in page
for h in hypotheses.load(G)["hypotheses"]:
    assert h["how_it_moves"] not in page and h["name"] not in page, "仮説の名前と動き方は出さない"
# 聞く: 仕組みは答えない、よくある言葉は刷った説明から、刷っていない紙は断る
j = json.loads(req(f"/toy/{G}/ask-json", {"hypothesis": "H-A", "question": "どういう仕組みで動くの？"})[1])
assert "試して確かめる所" in j["text"]
j = json.loads(req(f"/toy/{G}/ask-json", {"hypothesis": "H-A", "question": "谷折りって？"})[1])
assert "手前にへこむ" in j["text"]
assert req(f"/toy/{G}/ask-json", {"hypothesis": "H-B", "question": "谷折りって？"})[0] == 422
# 上げる: 記録を作り、その R-番号に写真を添える。撮影情報（APP1）を外し、型と大きさと出所を見る
code, body = req(f"/toy/{G}/record-json", {"hypothesis": "H-A", "result": "わからない"})
rid = json.loads(body)["id"]
jpeg = b"\xff\xd8" + b"\xff\xe1\x00\x08EXIF!!" + b"\xff\xdb\x00\x03\x00" + b"\xff\xda\x00\x02DATA" + b"\xff\xd9"
assert req(f"/record/{rid}/media", jpeg, "image/jpeg")[0] == 201
saved = (media_dir(rid) / "m1.jpg").read_bytes()
assert b"EXIF" not in saved and saved == strip_jpeg_meta(jpeg)
code, got = req(f"/record/{rid}/media/m1.jpg")
assert code == 200 and got == saved
assert req(f"/record/{rid}/media", b"x", "text/html")[0] == 422, "写真と動画の型だけ"
assert req(f"/record/{rid}/media", jpeg, "image/jpeg", origin="http://evil.example")[0] == 403
assert req("/record/R-9999/media", jpeg, "image/jpeg")[0] == 422, "記録の無い所には置かない"
assert "m1.jpg" in req(f"/toy/{G}/techo")[1].decode()
server.shutdown()
print("ok")
