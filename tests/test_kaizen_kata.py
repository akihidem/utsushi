"""審査用の頁の「型紙で改善したおもちゃ」の段と、御来迎が開く動画の道（本人の言葉 11-07・窓口の決め 152530）の試験。

見る事:
1. 作例の部品（web.sakurei.versions()）が無い・空・壊れた時は段を出さない（頁は止めない）
2. 写真があれば、題の下・ワークショップの節の前に段。玩具ごとに写真と玩具の名（玩具の頁への道）。記録の写真の道でない物は出さない
3. 動画は、確かめた印（checked.json の checked_by）があり置き場の中のふつうのファイルの時だけ、御来迎の写真の隣に（押すと動く・音なし）。札は「御来迎が開く所」
4. /kaizen/video/<名>.mp4 は、出してよい物だけ 200（Range は 206）。ほかは 404（印が無い・名の形が違う・置き場の外を指す印・無い）
5. 動画の撮り方を表す字は、頁と部品のどこにも無い（本人の訂正 11-07）
6. 合言葉なしの場でも同じ
"""
import json
import os
import pathlib
import sys
import tempfile
import threading
import types
import urllib.error
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ.pop("ANTHROPIC_API_KEY", None)

import web  # noqa: E402
from web import kaizen_judge as k, kaizen_kata as kv  # noqa: E402
from web.play_server import serve  # noqa: E402

G, T = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"
box = pathlib.Path(os.environ["OMOCHAE_DATA"]) / "kaizen_video"


def get(srv, path, headers=None):
    req = urllib.request.Request(f"http://127.0.0.1:{srv.server_address[1]}{path}", headers=headers or {})
    try:
        r = urllib.request.urlopen(req, timeout=120)
        return r.status, r.headers, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers, b""


def fake(versions):
    m = types.ModuleType("web.sakurei")
    m.versions = versions
    sys.modules["web.sakurei"] = m
    web.sakurei = m


# ---- 1 出さない時
sys.modules.pop("web.sakurei", None)
if hasattr(web, "sakurei"):
    delattr(web, "sakurei")
assert kv.section() == "" and 'id="versions"' not in k.page(), "作例の部品が無い間は段を出さない"
fake(lambda: {})
assert kv.section() == "", "写真が無ければ段を出さない"
fake(lambda: (_ for _ in ()).throw(RuntimeError("壊れた")))
assert kv.section() == "" and k.page(), "壊れた時は出さず、頁は止めない"

# ---- 2 写真
fake(lambda: {G: "/record/R-1019/media/m1.jpg/small", T: "/record/R-1020/media/m1.jpg/small", "x": "javascript:alert(1)"})
h = kv.section()
assert h.count("<img") == 2 and "javascript" not in h and kv.HEAD in h
assert f'href="/toy/{G}"' in h and f'href="/toy/{T}"' in h
assert "<video" not in h, "確かめた印が無い間は動画を出さない"

# ---- 3 動画
box.mkdir(parents=True, exist_ok=True)
(box / kv.VIDEO).write_bytes(b"\x00\x00\x00\x18ftypmp42" + bytes(range(256)) * 40)
assert "<video" not in kv.section(), "checked.json が無い"
(box / "checked.json").write_text(json.dumps({kv.VIDEO: {"checked_by": ""}}), encoding="utf-8")
assert "<video" not in kv.section(), "確かめた印が空"
(box / "checked.json").write_text(json.dumps({kv.VIDEO: {"checked_by": "確かめた人"}}), encoding="utf-8")
h = kv.section()
assert h.count("<video") == 1 and "autoplay" not in h and "muted" in h and kv.OPENS in h
assert h.index("R-1019") < h.index("<video") < h.index("R-1020"), "御来迎の写真の隣"

# ---- 4 動画の道（置き場の外を指す印も見る）
outside = pathlib.Path(tempfile.mkdtemp()) / "o.mp4"
outside.write_bytes(b"x")
(box / "link.mp4").symlink_to(outside)
(box / "plain.mp4").write_bytes(b"x")
(box / "checked.json").write_text(json.dumps({kv.VIDEO: {"checked_by": "確かめた人"}, "link.mp4": {"checked_by": "x"}}), encoding="utf-8")
for opened in (False, True):
    srv = serve(0, public_open=opened)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    page = get(srv, "/kaizen")[2].decode()
    assert page.index('id="versions"') < page.index('id="site"'), "題の下・一周の前"
    if 'id="ws"' in page:
        assert page.index('id="versions"') < page.index('id="ws"'), "ワークショップの節の前"
    code, hd, data = get(srv, f"/kaizen/video/{kv.VIDEO}")
    assert code == 200 and hd.get("Content-Type") == "video/mp4" and hd.get("Accept-Ranges") == "bytes" and data == (box / kv.VIDEO).read_bytes()
    code, hd, data = get(srv, f"/kaizen/video/{kv.VIDEO}", {"Range": "bytes=0-9"})
    assert code == 206 and len(data) == 10 and hd.get("Content-Range", "").startswith("bytes 0-9/"), "iPhone の Safari の Range"
    for bad in ("plain.mp4", "link.mp4", "nothing.mp4", "..%2Fx.mp4", "checked.json", f"{kv.VIDEO[:-4]}.mov"):
        assert get(srv, f"/kaizen/video/{bad}")[0] == 404, bad
    srv.shutdown()

# ---- 5 撮り方を表す字を書かない
words = "".join(chr(c) for c in (0x9006, 0x518d, 0x751f))  # 試験の中にもその字を書かないため、字の番号で持つ
for f in (pathlib.Path(kv.__file__), pathlib.Path(__file__)):
    assert words not in f.read_text(encoding="utf-8"), f
assert words not in k.page()
sys.modules.pop("web.sakurei", None)
delattr(web, "sakurei")
print("ok 型紙で改善したおもちゃの段: 作例の部品の写真がある時だけ、御来迎の写真の隣に確かめた動画。動画の道は確かめた物だけ（Range も）")
