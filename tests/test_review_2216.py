"""本人のサイトの見直し（11-07 22:16）の 3 点:「のこす、手帖、のフォントが違う。」「もちよる、でなくのこす、というボタンにする。」
「もちよる、の上下はありません、は要らない。」

見る事: のこす（手帖の記録の頁）と手帖（作る頁）の書体が他の頁と同じ明朝／のこす の頁の次へ進む釦の字が のこす（行き先は前のまま）／
もちよる の頁（作った物）に「上下はありません」が無い（作例の節の頭の字も）。英語の頁で日本語が残らない事は test_en_all が見る。
"""
import os
import sys
import tempfile
import re
import threading
import urllib.request
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from omochae import hypotheses  # noqa: E402
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

    # のこすの流れ（本人 11-08 402・405）の後: 記録の頁の道しるべは記入の節の「のこす」の釦 1 つで、「もちよる」の釦は無い。承認の後は /gallery#ageta に着く
    # （本人の見直し 22:16「もちよる、でなくのこす、というボタンにする。」を新しい のこす の釦で満たす。記入の節は紙を刷った後に出る）
    import urllib.parse
    urllib.request.urlopen(urllib.request.Request(base + f"/toy/{G}/print", data=urllib.parse.urlencode({"hypothesis": hypotheses.sheet_of(G)["id"]}).encode(),
                                                  headers={"Origin": base, "Content-Type": "application/x-www-form-urlencoded"}), timeout=120).read()
    kiroku = get(f"/toy/{G}/techo/kiroku")
    assert kiroku.count('<p class="road">') == 1 and '<p class="road"><button type="submit" class="go" id="nk-keep">のこす</button></p>' in kiroku, "のこす の釦が 1 つ"
    # 帯の駅の「もちよる」（頭の帯のリンク）は残る。見るのは道しるべの釦（class go）に「もちよる」が無い事
    assert not re.search(r'class="go"[^>]*>もちよる<', kiroku) and 'href="/gallery#ageta">のこす' not in kiroku, "もちよる の釦は無い"
    assert "/gallery?msg=" in kiroku and "#ageta" in kiroku, "承認の後は /gallery#ageta に着く"
    gallery = get("/gallery")
    assert "上下はありません" not in gallery, "もちよる の頁に「上下はありません」を出さない"
    for path in (f"/toy/{G}/techo", f"/toy/{G}/techo/kiroku"):
        page = get(path)
        assert "Noto Sans JP" not in page.split("</style>")[-2] if "</style>" in page else True, path
finally:
    srv.shutdown()
    srv.server_close()
print("ok 本人の見直し 22:16 の 3 点（書体・のこす の釦・上下はありません）")
