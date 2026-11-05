"""家の網に開く切り替え（本人の決定 11-04、U-36）。既定は手元だけで、--lan の時だけ網の中の番地を受ける。外の名前は断る。"""
import os
import tempfile
import threading
import urllib.error
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from web.play_server import bind_host, serve  # noqa: E402

local = serve(0)
assert local.server_address[0] == "127.0.0.1" and local.lan_hosts == ()
local.server_close()

# 試験の間は手元の口で待つ。--lan が全部の網に開く事は、口の決め方で見る（機械の網に口を開かない）
assert bind_host(True) == "0.0.0.0"
lan = serve(0, lan=True, bind="127.0.0.1")
port = lan.server_address[1]
assert lan.server_address[0] == "127.0.0.1"
threading.Thread(target=lan.serve_forever, daemon=True).start()


def get(host):
    r = urllib.request.Request(f"http://127.0.0.1:{port}/", headers={"Host": host})
    try:
        return urllib.request.urlopen(r).status
    except urllib.error.HTTPError as e:
        return e.code


assert get(f"127.0.0.1:{port}") == 200
assert get(f"evil.example:{port}") == 403, "外の名前は断る（DNS rebinding）"
for h in lan.lan_hosts:
    assert get(f"{h}:{port}") == 200, h
assert all(h.endswith(".local") or h.split(".")[0] in ("10", "172", "192") for h in lan.lan_hosts), "私的な番地と .local だけ"
lan.shutdown()
print("ok")
