"""審査用の頁（/kaizen）のワークショップの節（本人の言葉 11-07 昼）の試験。

見る事:
1. 回の一覧が無い間は節を出さない（回数を作り話にしない）
2. 一覧があれば、題の下に「ワークショップ N 回」（N は一覧の数）と、回ごとの札を回の番号の順に。札の名は日付。刷った型紙の版（「型紙の版 vN」の言い方）・直った所・下の一周への道
3. 写真は試行の記録の写しの置き場（docs/process/trials/photos/<箱>/）から。確かめ表（review.md）の本人の判断が「公開してよい」の写真だけ。
   欄が空・外す・表に無い・無いファイル・動画・名の危ない物・箱の外を指す印（symlink）・置き場の外を指す箱は出さない
4. 写真の道は、出してよい物だけ 200 の JPEG で、撮影の情報が無い。ほかは 404
5. 頭の敷き詰めは 12 枚までで、回をまたいで順に取る（写真の多い回だけで埋まらない）。札は 9 枚を開き、残りは畳む。幅 390 で 3 列、間 16px
6. 合言葉なしの場でも同じ
7. 本物の一覧と写真: 4 回。11 月 4 日の写真 9 枚・11 月 6 日の写真 33 枚（34 枚から p28 を外す。窓口の決め 11-07）が、確かめ表のとおりに出る（本人の答え 11-07「全部使っていい」）
8. 作例（/gallery#sakurei）への道は、作例の部品が人の確かめた作例を返す時だけ節の末に 1 本（作例の節は玩具ごとで日ごとの見出しが無いため）。部品が無い・空・壊れた時は張らない
9. 報告の顔の写真（本人「4 日間のワークショップで作ったおもちゃたち」）は、作例の部品の faces() の記録の写真の道だけを節の頭に。無い・壊れた時は出さない
10. 感想の分析の 2 文（本人の答え「全部入れる」の 2）は、節の説明（LEAD）のすぐ後に 1 回ずつ。数は件で言い、割合（%・割）を書かない。回答の字（「」の引用）を入れない
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

from web import kaizen_judge as k, kaizen_ws as ws  # noqa: E402
from web.play_server import serve  # noqa: E402

REAL_LIST, REAL_PHOTOS = ws.LIST, ws.PHOTOS


def get(srv, path):
    try:
        r = urllib.request.urlopen(f"http://127.0.0.1:{srv.server_address[1]}{path}", timeout=120)
        return r.status, r.headers.get("Content-Type", ""), r.read()
    except urllib.error.HTTPError as e:
        return e.code, "", b""


# ---- 1 一覧が無い間は出さない
ws.LIST = pathlib.Path(tempfile.mkdtemp()) / "workshops.json"
assert ws.section(str) == "" and 'id="ws"' not in k.page(), "一覧が無ければ節を出さない"

# 試験の置き場（試行の写真の置き場の形）
top = pathlib.Path(tempfile.mkdtemp())
ws.PHOTOS = top / "photos"
for box in ("a", "b"):
    (ws.PHOTOS / box).mkdir(parents=True)
rows = {"a": [], "b": []}
for i in range(20):  # a に 14 枚・b に 6 枚（a だけで敷き詰めが埋まらない事を見る）
    box = "a" if i < 14 else "b"
    ex = Image.Exif(); ex[0x010F] = "made-up-camera"  # 撮影の情報（作り直しで落ちる事を見る）
    Image.new("RGB", (1600, 1200), (200, 120 + i, 40)).save(ws.PHOTOS / box / f"p{i:02d}.jpg", exif=ex)
    rows[box].append(f"| p{i:02d}.jpg | 物 | 無し | 無し | 公開してよい |")
for name, judge in (("blank.jpg", ""), ("drop.jpg", "外す"), ("later.jpg", "まだ")):
    Image.new("RGB", (100, 100)).save(ws.PHOTOS / "a" / name)
    rows["a"].append(f"| {name} | 物 | 無し | 無し | {judge} |")
Image.new("RGB", (100, 100)).save(ws.PHOTOS / "a" / "unlisted.jpg")
rows["a"].append("| gone.jpg | 物 | 無し | 無し | 公開してよい |")
(ws.PHOTOS / "a" / "clip.mp4").write_bytes(b"\0" * 10)
rows["a"].append("| clip.mp4 | 動画 | 無し | 無し | 公開してよい |")
(top / "secret.jpg").write_bytes((ws.PHOTOS / "a" / "p00.jpg").read_bytes())
(ws.PHOTOS / "a" / "link.jpg").symlink_to(top / "secret.jpg")
rows["a"].append("| link.jpg | 物 | 無し | 無し | 公開してよい |")
rows["a"].append("| ../secret.jpg | 物 | 無し | 無し | 公開してよい |")
for box in ("a", "b"):
    (ws.PHOTOS / box / "review.md").write_text("| ファイル | 写っている物 | 顔 | 気になる所 | 本人の判断 |\n|---|---|---|---|---|\n" + "\n".join(rows[box]) + "\n", encoding="utf-8")
(top / "outside").mkdir()
# 箱そのものが置き場の外を指す印（symlink）の時も出さない（外の箱に確かめ表と写真があっても）
Image.new("RGB", (100, 100)).save(top / "outside" / "p00.jpg")
(top / "outside" / "review.md").write_text("| p00.jpg | 物 | 無し | 無し | 公開してよい |\n", encoding="utf-8")
(ws.PHOTOS / "c").symlink_to(top / "outside")
ws.LIST.write_text(json.dumps({"workshops": [
    {"n": 2, "date": "11 月 6 日", "did": "いろいろ作った", "printed": [["御来迎", "goraigo-v10"], ["虎", "tora-v3"]], "line": "感想から次の版の案", "loop": "engine", "photos": "b"},
    {"n": 1, "date": "11 月 4 日", "did": "御来迎を作った", "printed": [["御来迎", "goraigo-v7"]], "line": "溝をはさみで切る形に", "loop": "site", "photos": "a"},
    {"n": 3, "date": "11 月 10 日", "did": "動画で感想", "photos": "../outside"},
    {"n": 4, "date": "11 月 11 日", "photos": "nothing"},
    {"n": 5, "date": "11 月 12 日", "photos": "c"},
    {"date": "番号の無い行"}, {"n": "5", "date": "番号が字の行"}, {"n": True, "date": "番号が真偽の行"}, "行でない物"]}, ensure_ascii=False), encoding="utf-8")

# ---- 3 出す写真
assert [w["n"] for w in ws.workshops()] == [1, 2, 3, 4, 5], "回の番号の順。番号が整数でない行は外す"
assert ws.photos(1) == [f"p{i:02d}.jpg" for i in range(14)], ws.photos(1)
assert ws.photos(2) == [f"p{i:02d}.jpg" for i in range(14, 20)]
assert ws.photos(3) == [] and ws.photos(4) == [] and ws.photos(5) == [] and ws.photos(9) == [], "置き場の外を指す箱（名・印）・無い箱・一覧に無い回は出さない"

for opened in (False, True):
    srv = serve(0, public_open=opened)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    code, _, body = get(srv, "/kaizen")
    page = body.decode()
    assert code == 200
    # ---- 2 節と札
    assert page.index('id="ws"') < page.index('id="site"'), "題の下、一周の前"
    assert "ワークショップ 5 回" in page and "回目" not in page[page.index('id="ws"'):page.index('id="site"')], "札の名は日付"
    order = [page.index(f'id="ws-{n}"') for n in (1, 2, 3, 4)]
    assert order == sorted(order), "回の番号の順（11 月 10 日が 11 月 4 日より前に来ない）"
    hist = json.loads(k.HISTORY.read_text(encoding="utf-8"))
    for toy, s in (("御来迎", "goraigo-v7"), ("御来迎", "goraigo-v10"), ("虎", "tora-v3")):
        assert f"{toy} {k._sheet(hist, s)}" in page, (toy, s)
    assert 'href="#site"' in page and 'href="#engine"' in page and "溝をはさみで切る形に" in page and "御来迎を作った" in page
    assert "番号の無い行" not in page and "番号が字の行" not in page
    # ---- 5 敷き詰めと畳み
    mosaic = page[page.index('class="ws-mosaic"'):]
    mosaic = mosaic[:mosaic.index("</div>")]
    assert mosaic.count("<img") == ws.MOSAIC == 12
    assert mosaic.count("/kaizen/photo/2/") == 6, "写真の少ない回も頭に出る（回をまたいで順に取る）"
    card1 = page[page.index('id="ws-1"'):page.index('id="ws-2"')]
    assert card1.index("<details>") > card1.index('class="ws-photos"') and card1.count("<img") == 14 and ws.MORE.format(n=14 - ws.SHOWN) in card1, "9 枚を開き、残りは畳む"
    assert ".ws-mosaic{display:grid;grid-template-columns:repeat(3,1fr);gap:16px" in page
    for bad in ("blank.jpg", "drop.jpg", "later.jpg", "unlisted.jpg", "gone.jpg", "clip.mp4", "link.jpg", "secret.jpg"):
        assert bad not in page, bad
    # ---- 4 写真の道
    code, ctype, data = get(srv, "/kaizen/photo/1/p00.jpg")
    assert code == 200 and ctype == "image/jpeg"
    im = Image.open(io.BytesIO(data))
    assert im.format == "JPEG" and im.size[0] <= ws.SMALL_W and not dict(im.getexif()), "小さい写しで、撮影の情報が無い"
    for path in ("/kaizen/photo/1/blank.jpg", "/kaizen/photo/1/drop.jpg", "/kaizen/photo/1/unlisted.jpg", "/kaizen/photo/1/gone.jpg",
                 "/kaizen/photo/1/clip.mp4", "/kaizen/photo/1/link.jpg", "/kaizen/photo/1/..%2Fsecret.jpg", "/kaizen/photo/1/%2E%2E%2Fsecret.jpg",
                 "/kaizen/photo/2/p00.jpg", "/kaizen/photo/3/p00.jpg", "/kaizen/photo/5/p00.jpg", "/kaizen/photo/9/p00.jpg", "/kaizen/photo/1/review.md"):
        assert get(srv, path)[0] == 404, path
    srv.shutdown()

# ---- 8 作例への道: 作例の部品が人の確かめた作例を返す時だけ、節の末に /gallery#sakurei へ 1 本。部品が無い・空・壊れた時は張らない（頁は止めない）
import sys  # noqa: E402
import types  # noqa: E402
ws.LIST.write_text(json.dumps({"workshops": [{"n": 1, "date": "11 月 4 日", "md": "1104"}, {"n": 2, "date": "11 月 6 日", "md": "1106"}]}, ensure_ascii=False), encoding="utf-8")
assert "/gallery#sakurei" not in ws.section(str), "作例の部品が無い間は張らない"
fake = types.ModuleType("web.sakurei"); fake.examples = lambda: []
sys.modules["web.sakurei"] = fake
import web  # noqa: E402
web.sakurei = fake
assert "/gallery#sakurei" not in ws.section(str), "作例が無ければ張らない"
fake.examples = lambda: [{"sid": "x", "url": "/record/R-1001/media/m1.jpg/small"}]
h = ws.section(str)
assert h.count('href="/gallery#sakurei"') == 1 and "sakurei-1104" not in h and ws.SAKUREI in h, "節の末に 1 本だけ（日ごとの道は無い）"
assert h.index('class="ws-row"') < h.index('href="/gallery#sakurei"'), "札の並びの後"
fake.examples = lambda: (_ for _ in ()).throw(RuntimeError("壊れた"))
assert "/gallery#sakurei" not in ws.section(str), "壊れた時は張らず、頁は止めない"
del sys.modules["web.sakurei"]; del web.sakurei

# ---- 9 報告の顔の写真: 作例の部品の faces() の道だけ。部品が無い・壊れた時は出さない
assert 'class="ws-faces"' not in ws.section(str), "作例の部品が無い間は顔を出さない"
fake2 = types.ModuleType("web.sakurei"); fake2.faces = lambda: ["/record/R-1021/media/m1.jpg/small", "/record/R-1022/media/m1.jpg/small", "javascript:x"]
sys.modules["web.sakurei"] = fake2; web.sakurei = fake2
h = ws.section(str)
assert h.count("/record/R-102") == 2 and "javascript" not in h and ws.FACES in h, "顔の写真 2 枚と本人の言葉の札（記録の写真の道だけ）"
assert h.index('class="ws-faces"') < h.index('class="lead"'), "節の頭（題のすぐ下）"
fake2.faces = lambda: (_ for _ in ()).throw(RuntimeError("壊れた"))
assert 'class="ws-faces"' not in ws.section(str), "壊れた時は出さず、頁は止めない"
del sys.modules["web.sakurei"]; del web.sakurei

# ---- 7 本物の一覧と写真
ws.LIST, ws.PHOTOS = REAL_LIST, REAL_PHOTOS
real = ws.workshops()
assert len(real) == 4 and "ワークショップ 4 回" in k.page(), "本人の答え（11-07）の 4 回"
counts = {w["date"]: len(ws.photos(w["n"])) for w in real}
assert counts == {"11 月 4 日": 9, "11 月 5 日": 0, "11 月 6 日": 33, "11 月 7 日": 0}, counts
assert "p28.jpg" not in ws.photos(3) and "/kaizen/photo/3/p28.jpg" not in k.page(), "他社の AI の画面が写る p28 は出さない（窓口の決め 11-07）"
for w in real:
    box = ws._box(w["n"])
    if box:
        judged = ws._judged(box)
        files = {p.name for p in box.iterdir() if p.suffix.lower() in ws.IMAGE}
        assert judged >= files and set(ws.photos(w["n"])) == files - set(w.get("omit", [])), ("確かめ表の全部の写真が公開してよいで、外す物の他は全部出る", w["date"])

# ---- 10 感想の分析の 2 文（本人の答え「全部入れる」の 2・統括の決め: 件で言い割合にしない）
_h = ws.section(str)
assert ws.VOICES and all(_h.count(f'<p class="lead ws-voices">{t}</p>') == 1 for t in ws.VOICES), "2 文が 1 回ずつ"
_at = [_h.index(f'<p class="lead">{ws.LEAD}</p>')] + [_h.index(t) for t in ws.VOICES]
assert _at == sorted(_at), "LEAD のすぐ後に、2 文の順で"
assert not any(re.search(r"[%％]|\d+ ?割|半分", t) for t in ws.VOICES), "割合にしない"
assert not any("「" in t for t in ws.VOICES), "回答の字を引かない"

print("ok 審査用の頁のワークショップの節: 4 回の札（日付の名）・写真は試行の記録の写しのうち確かめ表で公開してよい物だけ・写真の道はそれ以外 404")
