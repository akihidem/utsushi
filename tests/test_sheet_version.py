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
# 御来迎のたたき台は組ごと（今の組 goraigo-v14 は H-C・記録の欄 sheet_by_set）。今の組で刷れるのはたたき台の紙だけ
GS = hypotheses.sheet_of(G)["id"]
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
    (out_dir(G) / f"{GS}_v{v}.pdf").write_bytes(b"%PDF-1.4\n")


def versions():
    return [r["sheet_version"] for r in records.all_records(G)]


def on_page(**form):
    return post(f"/toy/{G}/record", hypothesis=GS, result="動かない", **form)[0]


def on_techo(**form):
    return post(f"/toy/{G}/record-json", hypothesis=GS, result="動かない", **form)[0]


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

# 手帖の記録の札には、試した後の紙への道を出さない（11-06 から刷らない）。紙の道はその記録の版の紙を開く
for v in (1, 2):
    rec = next(r for r in records.all_records(G) if r["sheet_version"] == v)
    assert "_after.pdf" not in techo_site.feedback(G, rec), v
    assert urllib.request.urlopen(base + f"/sheet/{G}/{GS}_v{v}_after.pdf").status == 200, v
# 玩具の頁には、版を聞く記録の欄が無い（本人の答え 11-07 夕の Q3 で のこす へ寄せた）。手帖は開いた時の版を持って送る（data-v。上の手帖の口で見た）
toy_html = urllib.request.urlopen(base + f"/toy/{G}").read().decode()
assert 'name="sheet_version"' not in toy_html and 'id="record"' not in toy_html
print("ok")
