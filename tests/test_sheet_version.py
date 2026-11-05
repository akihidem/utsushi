"""版 2 以降を試した記録が、その版として残る（#149）。

見る線: 版を言わなければ刷ってある一番新しい版。言えばその版。刷っていない版の番号は記録に残らず、刷ってある一番新しい版に
読み替わる（頁の選ぶ欄は全部の仮説の版を合わせて出すので、断ると作った人の記録が失われる。test_kaizen と同じ線）。
玩具の頁と手帖の 2 つの口で同じ。手帖の「試した後の紙」は、その記録の版の紙を指す。
"""
import os
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from omochae import hypotheses, records  # noqa: E402
from web import techo_site  # noqa: E402
from web.play_server import out_dir, serve  # noqa: E402

G = "NDL-1187053-R0000005-L"
server = serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


opener = urllib.request.build_opener(NoRedirect)


def post(path, **data):
    req = urllib.request.Request(base + path, data=urllib.parse.urlencode(data).encode(), method="POST", headers={"Origin": base})
    try:
        r = opener.open(req)
        return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def printed(v):
    out_dir(G).mkdir(parents=True, exist_ok=True)
    (out_dir(G) / f"H-A_v{v}.pdf").write_bytes(b"%PDF-1.4\n")


def versions():
    return [r["sheet_version"] for r in records.all_records(G)]


def on_page(**form):
    return post(f"/toy/{G}/record", hypothesis="H-A", result="動かない", **form)[0]


def on_techo(**form):
    return post(f"/toy/{G}/record-json", hypothesis="H-A", result="動かない", **form)[0]


assert hypotheses.save_prediction(G, "筒を押すと開く")[1] == []
printed(1)
for send in (on_page, on_techo):
    before = versions()
    assert send() in (201, 303) and versions() == before + [1]
    assert send(sheet_version="2") in (201, 303) and versions() == before + [1, 1], "版 2 はまだ刷っていない"

printed(2)
for send in (on_page, on_techo):
    before = versions()
    assert send() in (201, 303) and versions() == before + [2], "言わなければ一番新しい版"
    assert send(sheet_version="") in (201, 303) and versions() == before + [2, 2]
    assert send(sheet_version="1") in (201, 303) and versions() == before + [2, 2, 1], "古い版を試した記録は古い版のまま"
    for bad in ("99", "0", "-1", "abc"):
        assert send(sheet_version=bad) in (201, 303) and versions()[-1] == 2, bad
assert set(versions()) == {1, 2}, "刷っていない版の番号が記録に残った"

# 手帖の「試した後の紙」は、その記録の版の紙を指す
for v in (1, 2):
    rec = next(r for r in records.all_records(G) if r["sheet_version"] == v)
    assert f"H-A_v{v}_after.pdf" in techo_site.feedback(G, rec), v
# 頁は版が 2 つ以上ある時だけ聞く
assert 'name="sheet_version"' in urllib.request.urlopen(base + f"/toy/{G}").read().decode()
print("ok")
