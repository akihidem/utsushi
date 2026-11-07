"""審査用の頁（/kaizen）のワークショップの節（本人の言葉 11-07 昼）の試験。回の一覧と写真は試験の中で作る（本物の写真は使わない）。

見る事:
1. 回の一覧が無い間は節を出さない（回数を作り話にしない）
2. 一覧があれば、題の下に「ワークショップ N 回」（N は一覧の数）と、回ごとの札を日付の順に。札に刷った型紙の版（「型紙の版 vN」の言い方）・直った所・下の一周への道
3. 出す写真は、人が確かめた印があり、種類が「物だけ」の物だけ（前からの本人の決め「人や声が入る物は、字だけにする」）。確かめていない物・人が入る物・名の危ない物・無い物・置き場の外を指す印（symlink）は出さない。回の番号が整数でない行は外す
4. 写真の道は、出してよい物だけ 200 の JPEG で、撮影の情報が無い。ほかは 404（置き場の外を指す名も）
5. 頭の敷き詰めは 12 枚まで。幅 390 で 3 列、間 16px（えらぶ の敷き詰めと同じ間）
6. 合言葉なしの場でも同じ
"""
import io
import json
import os
import pathlib
import tempfile
import threading
import urllib.error
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ.pop("ANTHROPIC_API_KEY", None)

from PIL import Image  # noqa: E402

from web import kaizen_judge as k, kaizen_ws as ws  # noqa: E402
from web.play_server import serve  # noqa: E402

base = pathlib.Path(os.environ["OMOCHAE_DATA"]) / "kaizen-ws"
lst = pathlib.Path(tempfile.mkdtemp()) / "workshops.json"
ws.LIST = lst


def get(srv, path):
    try:
        r = urllib.request.urlopen(f"http://127.0.0.1:{srv.server_address[1]}{path}", timeout=120)
        return r.status, r.headers.get("Content-Type", ""), r.read()
    except urllib.error.HTTPError as e:
        return e.code, "", b""


# ---- 1 一覧が無い間は出さない
assert ws.section(str) == "" and 'id="ws"' not in k.page(), "一覧が無ければ節を出さない"

# 一覧と写真（試験の中で作る）
lst.write_text(json.dumps({"workshops": [
    {"n": 2, "date": "2026-11-06", "name": "2 回目", "printed": [["御来迎", "goraigo-v10"], ["虎", "tora-v3"]], "line": "感想から次の版の案", "loop": "engine"},
    {"n": 1, "date": "2026-11-04", "name": "1 回目", "printed": [["御来迎", "goraigo-v7"]], "line": "溝をはさみで切る形に", "loop": "site"},
    {"n": 3, "date": "2026-11-07", "name": "3 回目"},
    {"n": 4, "date": "2026-11-07", "name": "4 回目"},
    {"date": "2026-11-08", "name": "番号の無い行"}, {"n": "5", "name": "番号が字の行"}, {"n": True, "name": "番号が真偽の行"}, "行でない物"]}, ensure_ascii=False), encoding="utf-8")
assert [w["n"] for w in ws.workshops()] == [1, 2, 3, 4], "回の番号が整数でない行は外す（頁ごと止めない）"
rows = []
for n in (1, 2, 3, 4):
    (base / str(n)).mkdir(parents=True, exist_ok=True)
for i in range(16):  # 物だけ・確かめた写真を 16 枚（敷き詰めの上限 12 を越える数）
    n = 1 + i % 4
    ex = Image.Exif(); ex[0x010F] = "made-up-camera"  # 撮影の情報（作り直しで落ちる事を見る）
    Image.new("RGB", (1600, 1200), (200, 120 + i, 40)).save(base / str(n) / f"o{i}.jpg", exif=ex)
    rows.append({"ws": n, "name": f"o{i}.jpg", "shows": "object", "checked_by": "確かめた人", "at": "2026-11-07T12:00+09:00"})
for name, row in (("p.jpg", {"shows": "people", "checked_by": "確かめた人"}), ("u.jpg", {"shows": "object"}), ("gone.jpg", {"shows": "object", "checked_by": "x"})):
    if name != "gone.jpg":
        Image.new("RGB", (100, 100)).save(base / "1" / name)
    rows.append(dict(row, ws=1, name=name))
(base / "secret.jpg").write_bytes((base / "1" / "o0.jpg").read_bytes())
rows.append({"ws": 1, "name": "../secret.jpg", "shows": "object", "checked_by": "x"})
# 箱の中の印（symlink）が置き場の外を指す時も出さない（別の目の気づき 11-07）
(base / "1" / "link.jpg").symlink_to(base / "secret.jpg")
rows.append({"ws": 1, "name": "link.jpg", "shows": "object", "checked_by": "x"})
(base / "photos.json").write_text(json.dumps({"photos": rows}, ensure_ascii=False), encoding="utf-8")

# ---- 3 出す写真
assert ws.photos(1) == ["o0.jpg", "o4.jpg", "o8.jpg", "o12.jpg"], ws.photos(1)
assert "p.jpg" not in ws.photos(1), "人が入る写真は出さない（前からの本人の決め）"

for opened in (False, True):
    srv = serve(0, public_open=opened)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    code, _, body = get(srv, "/kaizen")
    page = body.decode()
    assert code == 200
    # ---- 2 節と札
    assert page.index('id="ws"') < page.index('id="site"'), "題の下、一周の前"
    assert "ワークショップ 4 回" in page
    order = [page.index(f'id="ws-{n}"') for n in (1, 2, 3, 4)]
    assert order == sorted(order), "日付の順"
    hist = json.loads(k.HISTORY.read_text(encoding="utf-8"))
    for toy, s in (("御来迎", "goraigo-v7"), ("御来迎", "goraigo-v10"), ("虎", "tora-v3")):
        assert f"{toy} {k._sheet(hist, s)}" in page, (toy, s)
    assert 'href="#site"' in page and 'href="#engine"' in page and "溝をはさみで切る形に" in page
    # ---- 5 敷き詰め
    mosaic = page[page.index('class="ws-mosaic"'):]
    mosaic = mosaic[:mosaic.index("</div>")]
    assert mosaic.count("<img") == ws.MOSAIC == 12
    assert ".ws-mosaic{display:grid;grid-template-columns:repeat(3,1fr);gap:16px" in page
    assert "番号の無い行" not in page and "番号が字の行" not in page
    for bad in ("p.jpg", "u.jpg", "gone.jpg", "secret.jpg", "link.jpg"):
        assert bad not in page, bad
    # ---- 4 写真の道
    code, ctype, data = get(srv, "/kaizen/photo/1/o0.jpg")
    assert code == 200 and ctype == "image/jpeg"
    im = Image.open(io.BytesIO(data))
    assert im.format == "JPEG" and max(im.size) <= ws.SMALL_W * 2 and im.size[0] <= ws.SMALL_W and not dict(im.getexif()), "小さい写しで、撮影の情報が無い"
    for path in ("/kaizen/photo/1/p.jpg", "/kaizen/photo/1/u.jpg", "/kaizen/photo/1/gone.jpg", "/kaizen/photo/1/..%2Fsecret.jpg",
                 "/kaizen/photo/1/%2E%2E%2Fsecret.jpg", "/kaizen/photo/1/link.jpg", "/kaizen/photo/2/o0.jpg", "/kaizen/photo/9/o0.jpg", "/kaizen/photo/1/nothing.jpg"):
        assert get(srv, path)[0] == 404, path
    srv.shutdown()

# ---- 人が入る写真を出す決めになった時（SHOWS_OK に people を足す）だけ出る
ws.SHOWS_OK = ("object", "people")
assert "p.jpg" in ws.photos(1) and "u.jpg" not in ws.photos(1), "確かめていない物は、どの決めでも出さない"
ws.SHOWS_OK = ("object",)

print("ok 審査用の頁のワークショップの節: 一覧があれば回数と回ごとの札、写真は人が確かめた物だけの物だけ、写真の道はそれ以外 404")
