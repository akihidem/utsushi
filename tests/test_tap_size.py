"""スマホと iPad で押し間違えない床（#137）。押す所の高さ 44px 以上、字は 12px 以上。ブラウザなしで、配る頁の CSS を見る。

なぜ CSS を見るか: ./run.sh はブラウザなしで動く決まり。本当の高さは tests/measure_tap.py が手元の Chrome で測る（手で回す）。
ここは、床の CSS がどの頁にも届いている事と、小さい字の指定が戻っていない事を見る。
"""
import os
import re
import tempfile
import threading
import urllib.parse
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from omochae import hypotheses, records  # noqa: E402
from web import skin  # noqa: E402
from web.play_server import serve  # noqa: E402

MIN_FONT = 12
G = "NDL-1187053-R0000005-L"
server = serve(0)
base = f"http://127.0.0.1:{server.server_address[1]}"
threading.Thread(target=server.serve_forever, daemon=True).start()
hypotheses.save_prediction(G, "押すと開く")
urllib.request.urlopen(urllib.request.Request(f"{base}/toy/{G}/print", data=b"hypothesis=H-A", headers={"Origin": base}), timeout=120)
records.add({"source_id": G, "hypothesis_id": "H-A", "sheet_version": 1, "result": "動いた"})
PAGES = ["/", "/about", "/toys", f"/toy/{G}", f"/toy/{G}/techo", "/zukan", f"/zukan/{G}", f"/zukan/{G}/yomi", "/gallery"]

# 床は机の幅の見た目を変えない。スマホと iPad の幅か、指で触る機器の時だけ効く
assert "(max-width:1100px)" in skin.TAP_FLOOR and "(pointer:coarse)" in skin.TAP_FLOOR, skin.TAP_FLOOR[:80]
assert "min-height:44px" in skin.TAP_FLOOR
for selector in (".nav a", ".tabs a", ".links a", "summary", "button", "select", "label"):
    assert selector in skin.TAP_FLOOR, selector

for look in ("tenji", "zine"):
    for path in PAGES:
        page = urllib.request.urlopen(f"{base}{path}?look={look}", timeout=60).read().decode()
        where = (look, path)
        assert skin.TAP_FLOOR in page, ("床の CSS が届いていない", where)
        small = [float(x) for x in re.findall(r"font-size:\s*([\d.]+)px", page) if float(x) < MIN_FONT]
        assert not small, ("小さい字の指定", where, sorted(set(small)))
        ems = re.findall(r"font-size:\s*(0?\.\d+)r?em", page)
        assert all(float(x) >= .75 for x in ems), ("小さい字の指定（em）", where, ems)
server.shutdown()

# 皮なしの形（画面からは通らず、頁を直に作る時の形）にも床が届く
from web import kuzushi, zukan  # noqa: E402

for maker in (zukan._page, kuzushi._page):
    assert skin.TAP_FLOOR in maker("題", "<p>本文</p>"), maker.__module__
print("ok")
