"""できあがりの形を立体で見る試し（本人の決定 11-05、#331）。カメラの映像を外へ出さない事を文字列で固定する。
本物の顔と本物のスマホの確かめは、作る側の機械ではできない（カメラが無い）。ここでは頁の作りだけを見る。"""
import os
import re
import tempfile
import threading
import urllib.error
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from omochae.compose import TEMPLATES  # noqa: E402
from web import rittai  # noqa: E402
from web.play_server import serve  # noqa: E402

G = rittai.G
srv = serve(0)
port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()


def get(path):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}") as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


# 御来迎の頁から開ける。ほかの玩具には道も頁も無い
code, page = get(f"/toy/{G}/rittai")
assert code == 200 and rittai.LEAD in page and rittai.NOTE_CAMERA in page and rittai.NOTE_FINGER in page and rittai.NOTE_SHAPE in page
assert f'href="/toy/{G}/rittai"' in get(f"/toy/{G}")[1]
other = "NDL-1187053-R0000014-R"
assert f'/toy/{other}/rittai' not in get(f"/toy/{other}")[1] and get(f"/toy/{other}/rittai")[0] == 404

# カメラの映像を送る口と残す口が無い。音は取らない。映像は画面に出さない
for word in ("fetch(", "XMLHttpRequest", "sendBeacon", "WebSocket", "RTCPeerConnection", "MediaRecorder", "toDataURL", "toBlob", "localStorage", "indexedDB", "<form"):
    assert word not in page, word
assert "audio:false" in page and "audio:true" not in page
assert 'muted playsinline aria-hidden="true"' in page and "#rt-video{position:absolute;width:1px;height:1px;opacity:0" in page
assert "#rt-canvas{display:none}" in page, "読み取りの canvas も出さない（消すと顔の絵が 64×48 で出る）"
# カメラは押した時だけ動かす
assert page.index("go.addEventListener('click'") < page.index("getUserMedia({video")
assert page.count("getUserMedia({video") == 1
# 指で動かせる。止める口がある。頁を離れたら止める
assert "pointermove" in page and 'id="rt-stop"' in page and "addEventListener('pagehide',end)" in page and "getTracks().forEach(t=>t.stop())" in page

# 絵は雛形の寸法から組む。寸法が変われば絵も変わる。外の部品を読まない
_, p = rittai.params(G)
assert p["tube_side"] == TEMPLATES["slider_fan"].DEFAULTS["tube_side"]
assert page.count('class="rt-face') == 8 and page.count('class="rt-pleat') == int(p["fold_count"])
assert f'width:{p["tube_side"] * rittai.SCALE:.1f}px' in page
assert "bigger" not in rittai._model({**p, "tube_side": p["tube_side"] + 5}) and rittai._model({**p, "tube_side": p["tube_side"] + 5}) != rittai._model(p)
assert not re.search(r'<script[^>]+src=|<link[^>]+href="http|https?://(?!www\.w3\.org)[^"\' ]*\.(?:js|wasm|task)', page), "外の部品を読まない"

# 合言葉なしで開いた場でも、映像を受ける口が無いので同じに開ける
opened = serve(0, public_open=True)
threading.Thread(target=opened.serve_forever, daemon=True).start()
with urllib.request.urlopen(f"http://127.0.0.1:{opened.server_address[1]}/toy/{G}/rittai") as r:
    assert r.status == 200
opened.shutdown()
srv.shutdown()
print("ok")
