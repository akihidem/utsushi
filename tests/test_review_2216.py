"""本人のサイトの見直し（11-07 22:16）の 3 点:「のこす、手帖、のフォントが違う。」「もちよる、でなくのこす、というボタンにする。」
「もちよる、の上下はありません、は要らない。」

見る事: のこす（手帖の記録の頁）と手帖（作る頁）の書体が他の頁と同じ明朝／のこす の頁の次へ進む釦の字が のこす（行き先は前のまま）／
もちよる の頁（作った物）に「上下はありません」が無い（作例の節の頭の字も）。英語の頁で日本語が残らない事は test_en_all が見る。
"""
import os
import sys
import tempfile
import threading
import urllib.request
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from web import techo_site, techo_step  # noqa: E402
from web.play_server import serve  # noqa: E402

G = "NDL-1187053-R0000005-L"
assert "Noto Sans" not in techo_site.STYLE and "sans-serif" not in techo_site.STYLE.split("body.techo{")[1].split("}")[0], "のこす の頁の書体"
assert "Noto Sans" not in techo_step.STYLE.split("body{")[1].split("}")[0], "手帖の頁の書体"
assert "上下はありません" not in techo_site.SAKUREI_LEAD

srv = serve(0, look="tenji")
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{srv.server_address[1]}"
try:
    def get(path):
        with urllib.request.urlopen(base + path, timeout=120) as r:
            return r.read().decode("utf-8")

    kiroku = get(f"/toy/{G}/techo/kiroku")
    assert '<a class="go" href="/gallery#ageta">のこす</a>' in kiroku and '<a class="go" href="/gallery#ageta">もちよる</a>' not in kiroku, "のこす の釦"
    gallery = get("/gallery")
    assert "上下はありません" not in gallery, "もちよる の頁に「上下はありません」を出さない"
    for path in (f"/toy/{G}/techo", f"/toy/{G}/techo/kiroku"):
        page = get(path)
        assert "Noto Sans JP" not in page.split("</style>")[-2] if "</style>" in page else True, path
finally:
    srv.shutdown()
    srv.server_close()
print("ok 本人の見直し 22:16 の 3 点（書体・のこす の釦・上下はありません）")
