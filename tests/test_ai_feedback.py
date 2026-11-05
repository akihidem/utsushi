"""手帖の AI の返事（J-013 の順の最後）と動画の観察の補助（J-022）。人の説明が先、成否の言葉を出さない、鍵が無ければ呼ばない。本物は呼ばない。"""
import os
import subprocess
import tempfile
from types import SimpleNamespace

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(tempfile.mkdtemp(), "api-usage.jsonl")  # 本物の台帳に書かない（#151）

from api import ask, observe  # noqa: E402
from omochae import loop, records  # noqa: E402

ask._key_present = lambda: False  # 試験の機械に鍵が置かれていても、本物の API を呼ばせない

G = "NDL-1187053-R0000005-L"
rid, _ = records.add({"source_id": G, "hypothesis_id": "H-A", "sheet_version": 1, "result": "動いた"})
video = os.path.join(tempfile.mkdtemp(), "v.mp4")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=duration=2:size=160x120:rate=10", "-pix_fmt", "yuv420p", video], check=True)
assert len(observe.frames(video)) == 3


class Fake:
    def __init__(self, text):
        self.text, self.sent = text, None
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **req):
        self.sent = req
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=self.text)], usage=SimpleNamespace(input_tokens=10, output_tokens=5))


ok = Fake('{"observed": ["扇が筒の口から上へ出た"], "unclear": ["糸が張ったか"]}')
assert observe.observe(rid, video, ok) == (None, "人の説明が先")
assert ok.sent is None, "人の説明の前は呼ばない"
assert not loop.save_explanation(rid, "本人", "開いた", "速く押す")
res, why = observe.observe(rid, video, ok)
assert not why and res["observed"] == ["扇が筒の口から上へ出た"]
assert sum(1 for b in ok.sent["messages"][0]["content"] if b["type"] == "image") == 3
assert observe.observation(rid)["label"] == "観察（Claude の補助）"
bad = Fake('{"observed": ["成功です"], "unclear": []}')
assert observe.observe(rid, video, bad)[0] is None, "成否の言葉は出さない"

# 画面: 説明の後に AI の口が出て、鍵が無い時は呼ばずに知らせる
import threading  # noqa: E402
import urllib.error  # noqa: E402
import urllib.parse  # noqa: E402
import urllib.request  # noqa: E402

from omochae import hypotheses  # noqa: E402
from web.play_server import serve  # noqa: E402

server = serve(0)
base = f"http://127.0.0.1:{server.server_address[1]}"
threading.Thread(target=server.serve_forever, daemon=True).start()


def post(path, data):
    r = urllib.request.Request(base + path, data=urllib.parse.urlencode(data).encode(), headers={"Content-Type": "application/x-www-form-urlencoded", "Origin": base})
    op = urllib.request.build_opener(type("N", (urllib.request.HTTPRedirectHandler,), {"redirect_request": lambda *a, **k: None}))
    try:
        x = op.open(r)
        return x.status, x.headers.get("Location", "")
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Location", "")


post(f"/toy/{G}/print", {"hypothesis": "H-A"})
page = urllib.request.urlopen(base + f"/toy/{G}/techo").read().decode()
assert "Claude に聞く（何が起きたか）" in page and "観察（Claude の補助）" in page
code, loc = post(f"/record/{rid}/ai-interpret", {"back": "techo"})
assert code == 303 and "techo" in loc and urllib.parse.quote("鍵が置かれると") in loc
r2, _ = records.add({"source_id": G, "hypothesis_id": "H-A", "sheet_version": 1, "result": "わからない"})
assert post(f"/record/{r2}/ai-observe", {"back": "techo"})[0] == 422, "人の説明の前は呼ばない"
server.shutdown()
print("ok")
