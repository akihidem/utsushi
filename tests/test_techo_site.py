"""入口のサイトの中の手帖（本人の方向転換 11-04）。仮説の名前と動き方を出さない・手順だけ答える・上げた物は記録に添い撮影情報を外す。"""
import io
import json
import os
import re
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from PIL import Image  # noqa: E402

from omochae import hypotheses  # noqa: E402
from web.play_server import serve  # noqa: E402
from web.techo_site import MAX_MEDIA, media_dir, strip_jpeg_meta  # noqa: E402

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
assert code == 200 and "先に予想を書く" not in body.decode(), "予想の段は無い（#242）"
assert req(f"/toy/{G}/print", {"hypothesis": "H-A"})[0] in (200, 303)
code, body = req(f"/toy/{G}/techo")
page = body.decode()
assert code == 200 and "手帖" in page and 'value="H-A"' in page and 'id="mic"' in page
for h in hypotheses.load(G)["hypotheses"]:
    assert h["how_it_moves"] not in page and h["name"] not in page, "仮説の名前と動き方は出さない"
# 聞く: 字で打った後に押す釦が欄と同じ form にある。Enter だけだと、声の使えない機器で送り方が画面から分からない（#140）
form = page.split('<form id="ask-form">', 1)[1].split("</form>", 1)[0]
assert 'id="q"' in form and '<button type="submit" class="go">聞く</button>' in form
assert form.index('id="q"') < form.index("<button"), "打つ → 送る の順でキーボードが進む"
assert '<div class="answer" id="answer" aria-live="polite"></div>' in page and "ここに答えが出ます" in page, "答えの出る場所が空の時も分かる"
# 聞く: 仕組みは答えない、よくある言葉は刷った説明から、刷っていない紙は断る
j = json.loads(req(f"/toy/{G}/ask-json", {"hypothesis": "H-A", "question": "どういう仕組みで動くの？"})[1])
assert "試して確かめる所" in j["text"]
j = json.loads(req(f"/toy/{G}/ask-json", {"hypothesis": "H-A", "question": "谷折りって？"})[1])
assert "手前にへこむ" in j["text"]
assert req(f"/toy/{G}/ask-json", {"hypothesis": "H-B", "question": "谷折りって？"})[0] == 422
# 上げる: 数と大きさの決まりを押す前に読める。写真を選ぶまで、釦の字は写真なしで起きる事を言う（#144）
form = page.split('<form id="up-form"', 1)[1].split("</form>", 1)[0]
assert "3 つまで・1 つ 20MB まで" in form and 'data-max-n="3"' in form and f'data-max-bytes="{MAX_MEDIA}"' in form
assert 'id="picked"' in form and 'id="thumbs"' in form
assert '<button class="go">記録だけ残す</button>' in form and "大人の手元だけ・顔なし・声なし" in form
# 上げる: 記録を作り、その R-番号に写真を添える。撮影情報（APP1）を外し、型と大きさと出所を見る
code, body = req(f"/toy/{G}/record-json", {"hypothesis": "H-A", "result": "わからない"})
rid = json.loads(body)["id"]
photo = io.BytesIO()
Image.new("RGB", (8, 8), (200, 180, 140)).save(photo, "JPEG")
jpeg = photo.getvalue()[:2] + b"\xff\xe1\x00\x08EXIF!!" + photo.getvalue()[2:]
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
# 頁の名前は帯・<title>・h1 で同じ。h1 は 1 つで、節は h2。頁の頭から節へ 1 回で行ける（#139）
name = "上げた物と職人の言葉"
assert f"<b>{name}</b>" in g and f"<title>{name}<" in g, g[:300]  # 帯の今いる所は b で出る
assert re.findall(r"<h1[^>]*>(.*?)</h1>", g) == [name]
for sec, label in (("ageta", "上げた物"), ("yose", "寄せられた声"), ("shokunin", "職人の言葉")):
    assert f'<a href="#{sec}">{label}</a>' in g and f'id="{sec}"' in g and f'<h2 class="mark">{label}</h2>' in g, sec
# 見本は札と断りの一文で見分ける。縞の地と、皮によって白く浮く固定の色は使わない（#139）
assert "repeating-linear-gradient" not in g and "#f4efe3" not in g and "#7a3b1d" not in g
assert '<span class="sample">見本</span>' in g and "is-sample" in g
# 上げた後は頁の中で一覧を入れ替える（#143）。同じ道へ location.href しても読み込まれず、「…」のまま残って、もう一度押すと記録が 2 件になっていた
from web.techo_site import SCRIPT  # noqa: E402
up = SCRIPT[SCRIPT.index("getElementById('up-form')"):]
assert "location.href" not in up, "同じ道へは飛ばさない"
assert "if (go.disabled) return" in up and "go.disabled = true" in up and "form.reset()" in up and "上げました" in up
assert up.index("form.reset()") < up.index("/media"), "記録ができたら先に欄を空にする（写真で止まっても、押し直しで記録を増やさない）"
# 入れ替える元は頁の #mine。今の記録と写真が、新しい順の頭に在る
r3 = json.loads(req(f"/toy/{G}/record-json", {"hypothesis": "H-A", "result": "動いた", "note": "x"})[1])["id"]
mine = req(f"/toy/{G}/techo")[1].decode().split('<div id="mine">')[1]
assert mine.index(r3) < mine.index(r2), "新しい記録が頭に来ない"
server.shutdown()
print("ok")
