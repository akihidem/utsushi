"""図鑑の本の頁（/zukan/hon/<コマ>）の試験。本人の決定 11-06: 玩具の絵がある頁を、図鑑から 1 コマずつ順に。本物の網は使わない。

見る事:
1. 置く頁は棚卸しの玩具が載る 54 頁（28 コマ）。奥付（31 左）と玩具の無いコマ（1〜3・32〜35）と 4 コマ目の右は入らない
2. 取る道は玩具の頁の頭と同じ入口・同じ名前（1 枚を分け合う）
3. 1 コマの頁: 見開きの頁と玩具の所の枠。サイトの玩具は枠と名前から玩具の頁へ。無い玩具は枠だけ。確かめた歌はその頁の下
4. 図鑑から 1 回で入れて、前へ・次へで順に送れる。新しい字は「原画と歌」「大きく見る」と今ある「本の n コマ目」だけ
5. 写しの道は置く頁だけを返す。写しが無くても頁は止まらない
"""
import io
import json
import os
import pathlib
import re
import tempfile
import threading
import urllib.error
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ.pop("ANTHROPIC_API_KEY", None)

from PIL import Image  # noqa: E402

from omochae import ingest  # noqa: E402
from omochae.hypotheses import ROOT  # noqa: E402
from web import genga, genga_words, kumitate, zukan, zukan_hon  # noqa: E402
from web.play_server import serve, sources  # noqa: E402

G = "NDL-1187053-R0000005-L"

# 1. 置く頁
faces = ingest.book_faces()
assert len(faces) == 54 and zukan_hon.frames() == list(range(4, 32))
assert (31, "L") not in faces and (4, "R") not in faces and not [f for f in faces if f[0] < 4 or f[0] > 31]
site_faces = {(int(json.loads(p.read_text(encoding="utf-8"))["canvas"]), json.loads(p.read_text(encoding="utf-8"))["side"])
              for p in (ROOT / "data/sources").glob("NDL-*.json")}
assert site_faces <= set(faces) and len(set(faces) - site_faces) == 7, "サイトの 47 頁と、棚卸しにだけ玩具がある 7 頁"
assert faces.index((5, "R")) < faces.index((5, "L")), "見開きは右の面が先"

# 2. 同じ入口・同じ名前
books, pages = ingest.book_targets(), ingest.page_targets()
assert all(books[k] == v for k, v in pages.items()), "玩具の頁の頭と 1 枚を分け合う"
assert books["R0000008-L"].endswith("/R0000008/pct:0,0,50,100/1000,/0/default.jpg")

# 写しの置き場を一時の場所にする（本物の out/sources/pages には触らない）
ingest.PAGES = pathlib.Path(tempfile.mkdtemp())
for face in ((5, "L"), (5, "R"), (8, "L"), (8, "R")):
    buf = io.BytesIO()
    Image.new("RGB", (100, 166), (230, 220, 200)).save(buf, "JPEG")
    zukan_hon.face_file(*face).write_bytes(buf.getvalue())

# 3. 1 コマの頁
inv = json.loads((ROOT / "data/inventory/edo-nishiki.json").read_text(encoding="utf-8"))["toys"]
h8 = zukan_hon.page(8, "tenji")
assert h8.count('<figure class="face"') == 2 and h8.index('id="R0000008-R"') < h8.index('id="R0000008-L"'), "本の順"
on8 = [t for t in inv if t["frame"] == 8]
linked = [t for t in on8 if t["id"] in sources()]
assert h8.count('<a class="genga-box"') == len(linked) and h8.count('<span class="genga-box"') == len(on8) - len(linked)
assert all(f'href="/toy/{t["id"]}"' in h8 for t in linked)
assert not [t for t in on8 if t["side"] == "L" and t["id"] in sources()], "8 コマ目の左はサイトに玩具が無い頁"
for t in on8:
    if t["id"] not in sources():
        assert t["name_guess"] not in h8, "見立ての名前は字にしない"
h5 = zukan_hon.page(5, "tenji")
songs = [e["text"] for e in genga.songs(json.loads((ROOT / "data/sources" / f"{G}.json").read_text(encoding="utf-8")))]
assert songs and all(s in h5.split('id="R0000005-L"', 1)[1] for s in songs), "確かめた歌は、その頁の下"
assert f'<a href="/zukan/hon/R0000005-L.jpg">{genga_words.BIG}</a>' in h5

# 4. 入口と送り
# 入口は前の図鑑の目次から、序の頁（よむ）へ移した（図鑑の頁は外した・本人の言葉 11-08。本の頁は残す・本人の決め 11-08）。字は前のまま「原画と歌」
from web import about  # noqa: E402
idx = about.page("tenji")
assert f'<a href="/zukan/hon/4">{genga_words.HEAD}</a>' in idx
assert zukan_hon.PREV == kumitate.PREV and zukan_hon.NEXT == kumitate.NEXT, "送る字は組み立ての頁と同じ"
assert 'href="/zukan/hon/7">前へ' in h8 and 'href="/zukan/hon/9">次へ' in h8
first, last = zukan_hon.page(4, "tenji"), zukan_hon.page(31, "tenji")
assert ">前へ<" not in first and ">次へ<" not in last
assert "本の 8 コマ目" in h8 and zukan_hon.koma(8) == "本の 8 コマ目"
body8 = h8[h8.index('<div class="zukan-hon">'):h8.index("</main>")] if "</main>" in h8 else h8[h8.index('<div class="zukan-hon">'):]
text = re.sub(r"<(style|script)\b.*?</\1>", "", body8, flags=re.S)  # 頭の帯と足は今の字なので、本の頁の中身だけを見る
words = set(re.findall(r">([^<>]+)<", text))
known = {genga_words.HEAD, genga_words.BIG, "本の 8 コマ目", "前へ", "次へ"} | {t for t in words if t.strip() == ""}
extra = {w for w in words - known if not any(w in src for src in (json.dumps(json.loads((ROOT / "data/sources" / f"{s}.json").read_text(encoding="utf-8")), ensure_ascii=False) for s in sources()))}
extra -= set(re.findall(r">([^<>]+)<", zukan.NAV))  # 図鑑の今の帯の字
assert not extra, ("新しい字は足さない", extra)

# 5. 道
def get(server, path):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{server.server_address[1]}{path}", timeout=30) as r:
            return r.status, r.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        return e.code, ""


for public_open in (False, True):
    server = serve(0, public_open=public_open)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        assert get(server, "/zukan/hon/8")[0] == 200 and get(server, "/zukan/hon/12")[0] == 200, "写しが無くても止まらない"
        assert get(server, "/zukan/hon/R0000008-L.jpg") == (200, "image/jpeg")
        for bad in ("/zukan/hon/3", "/zukan/hon/32", "/zukan/hon/R0000031-L.jpg", "/zukan/hon/R0000004-R.jpg", "/zukan/hon/R0000012-R.jpg"):
            assert get(server, bad)[0] == 404, bad
    finally:
        server.shutdown()
        server.server_close()
print("ok 図鑑の本の頁は、玩具の絵がある 54 頁を 1 コマずつ本の順に、新しい字を足さずに出す")
