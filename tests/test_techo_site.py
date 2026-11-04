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
# 次の版（本人の問いの (7)）: 説明が先、数でない値は断る、床に通った時だけ版 2 を刷る
code, body = req(f"/record/{rid}/next", {"interpretation": "折りが固い", "param": "fold_count", "to": "24", "why": "開きを見る", "by": "本人"})
assert code == 422 and "先に説明を書く" in body.decode()
assert req(f"/record/{rid}/explain", {"text": "わからない", "next_idea": "折りを減らす", "by": "本人"})[0] in (200, 303)
assert req(f"/record/{rid}/next", {"interpretation": "折りが固い", "param": "fold_count", "to": "abc", "why": "x", "by": "本人"})[0] == 422
code, body = req(f"/record/{rid}/next", {"interpretation": "折りが固い", "param": "fold_count", "to": "24", "why": "開きを見る", "by": "本人"})
assert code in (200, 303), body[:300]
page = req(f"/toy/{G}")[1].decode()
# 版を言わずに開くと窓は最新の版（PDF の押し釦は版 2）。字のリンクは窓へ（本人の指示 11-05）
assert "H-A_v2.pdf" in page and "版 2 の型紙" in page and f"see=H-A&kind=sheet&v=2#win" in page
assert req(f"/sheet/{G}/H-A_v2.pdf")[1][:4] == b"%PDF"
# 型紙の確定の記録（f09）: 刷った版ごとに、誰が・どの組で確定したかが台帳に残る
from omochae import loop  # noqa: E402
conf = {(c["hypothesis_id"], c["version"]): c["confirmations"] for c in loop.sheet_confirmations(G)}
assert ("H-A", 1) in conf and conf[("H-A", 2)][-1]["by"] == "本人" and conf[("H-A", 2)][-1]["sheet_set"]
# フィードバックも手帖で（本人 11-04）: 試した後の紙・説明・次の版が手帖の記録に出て、送った後は手帖へ戻る
page = req(f"/toy/{G}/techo")[1].decode()
assert "試した後の紙" in page and "次の版を作る" in page and 'name="back" value="techo"' in page
r2 = json.loads(req(f"/toy/{G}/record-json", {"hypothesis": "H-A", "result": "動いた"})[1])["id"]
opener = urllib.request.build_opener(type("NoRedirect", (urllib.request.HTTPRedirectHandler,), {"redirect_request": lambda *a, **k: None}))
x = urllib.request.Request(base + f"/record/{r2}/explain", data=urllib.parse.urlencode({"text": "開いた", "next_idea": "速く押す", "by": "本人", "back": "techo"}).encode(),
                           headers={"Content-Type": "application/x-www-form-urlencoded", "Origin": base})
try:
    opener.open(x)
except urllib.error.HTTPError as e:
    assert e.code == 303 and "/techo" in e.headers["Location"]
# サイトのギャラリー: 上げた物と職人の言葉の枠
g = req("/gallery")[1].decode()
assert "m1.jpg" in g and "職人の言葉" in g and "紙と折りの職人" in g  # 枠の中身は見本（demo_samples）か（準備中）
assert "/gallery" in req("/look/tenji")[1].decode()
server.shutdown()
print("ok")
