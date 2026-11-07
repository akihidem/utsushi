"""やさしい日本語で、SVG の <text>・<tspan> の中にルビ（<ruby>）を入れない（別の目の知らせ 11-07 夜: 学びの輪の図の字にルビが入ると、
ブラウザが SVG の外へ追い出し、図の字が図の下に縦に並んだ。のこす の頁で撮って確かめた）。

見る事: SVG の text・tspan の中の字は、要素を入れない形（ルビの印を外した字。読みを 漢字（よみ） で添えると図の札がはみ出した）。
全部の頁を ?lang=easy で回し、どの <svg> の中にも <ruby> が無い。
"""
import os
import pathlib
import re
import sys
import tempfile
import threading
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from web import i18n  # noqa: E402
from web.play_server import serve, sources  # noqa: E402

SVG = re.compile(r"<svg\b.*?</svg>", re.S)

out = i18n.page_easy('<html lang="ja"><main><svg viewBox="0 0 10 10"><text x="1" y="1">御来迎</text>'
                     '<text><tspan>御来迎</tspan></text></svg><p>御来迎</p></main></html>')
svg = SVG.search(out).group(0)
assert "<ruby>" not in svg, svg
# 字は消さず、ルビの印を外した字にする（読みを 漢字（よみ） で添えると図の札がはみ出したため。読みは図のすぐ上の文が持つ）
assert '<text x="1" y="1">御来迎</text>' in svg and "<tspan>御来迎</tspan>" in svg, svg
assert "<p><ruby>御来迎<rt>ごらいごう</rt></ruby></p>" in out, "SVG の外の字の節には前と同じくルビ"

srv = serve(0, look="tenji")
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{srv.server_address[1]}"
try:
    i18n.prime(base, sources())
    bad = []
    for path in i18n.routes(sources()):
        req = urllib.request.Request(base + path, headers={"Cookie": "utsushi_lang=easy"})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                body, ctype = r.read().decode("utf-8", "replace"), r.headers.get("Content-Type", "")
        except urllib.error.HTTPError as e:
            body, ctype = e.read().decode("utf-8", "replace"), e.headers.get("Content-Type", "")
        if ctype.startswith("text/html") and any("<ruby>" in s for s in SVG.findall(body)):
            bad.append(path)
    assert not bad, bad[:8]
finally:
    srv.shutdown()
    srv.server_close()
print("ok やさしい日本語: SVG の text・tspan の中にルビを入れない")
