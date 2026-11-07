"""型紙の版の歩みの額の並び（本人の指示 11-07「過去の型紙が改善していって、提出の時の今の型紙になっている所が分かるようにしたい。
御来迎と虎のそれぞれで、版の歩みが今の版に行き着くまで見える形にしてください。」。設計 0.7 節の置き場 ①）。

部品と、玩具の頁の置き場を見る:
1. 御来迎と虎のそれぞれで、古い版から順に額が並び、最後が提出の時の今の版（サイトが今刷る組）。今の版の額だけに「いまの型紙」の印
2. 額の下は「型紙の版 N」・エンジンの版の字・表の 1 行・日付の 4 つだけで、表の字のまま。きっかけと PR は出さない
3. 額と額の間に → の印（読み上げには出さない）。開いた時に右の端（今の版）へ送る script がある
4. 表の最初の版が版 1 でない時は「この前にも版があります」。見出しの下の数の 1 行は表から描く
5. 絵は置いてある版と repo の中から作れる版（改善の輪より前の版は刷った PDF・今の版は今の雛形・間の版は engine/ の見本の組の JSON が
   ある版だけ）を img にし、作れない間の版は
   「この版の絵は残っていない」の字（本人の見直し 11-07 22:16「過去の版が表示されていない。」。壊れた絵を出さない）。作った絵は小さい写し。サーバの道は組の名の形だけを受ける
6. 表に無い玩具・今の組の行が表に無い玩具は節を出さない（今の版と言えない並びを出さない）
7. 玩具の頁では、型紙の窓の節のすぐ後（2 画面目の頭）に 1 つだけ置き、たとえはその後。表に無い玩具の頁には出ない
"""
import os
import pathlib
import re
import tempfile
import threading
import urllib.error
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from omochae import kaizen_history as kh  # noqa: E402
from omochae.compose import TEMPLATES  # noqa: E402
from web import ban_ayumi, play_server, wa  # noqa: E402

G, T = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"
FAN, TIGER = TEMPLATES["slider_fan"], TEMPLATES["pivot_counterweight"]
data = kh.load()
tmp = pathlib.Path(tempfile.mkdtemp())
keep_pictures, kh.PICTURES = kh.PICTURES, tmp / "out-history"


def frames(html):
    return re.findall(r"<li( class=\"now\" aria-current=\"true\")?>(.*?)</li>", html, re.S)


try:
    # 置き場には虎 v7 と御来迎 v10 だけを置く（ほかの版は、repo の中から作れる版だけが img になる事を見る）
    (kh.PICTURES / "sheets").mkdir(parents=True)
    for name in ("tora-v7", "goraigo-v10"):
        (kh.PICTURES / f"sheets/{name}.png").write_bytes(b"\x89PNG" + name.encode())

    # 1. 古い順に並び、最後が今の版。印は今の版だけ
    for sid, tpl, want in ((T, TIGER, [f"tora-v{n}" for n in range(1, 8)]), (G, FAN, [f"goraigo-v{n}" for n in range(1, 15)])):
        html = ban_ayumi.section(sid)
        rows = kh.versions(tpl.__name__.rsplit(".", 1)[1])
        assert [r["set"] for r in rows] == want and rows[-1]["set"] == tpl.SHEET_SET, [r["set"] for r in rows]
        got = frames(html)
        assert len(got) == len(rows) and [bool(now) for now, _ in got] == [False] * (len(rows) - 1) + [True], [bool(n) for n, _ in got]
        assert html.count(wa.NOW) == 1 and wa.NOW in got[-1][1], "いまの型紙の印は今の版の額だけ"
        assert 'id="ban-ayumi"' in html and f"<h2>{ban_ayumi.HEAD}</h2>" in html and "版の歩み" in html
        # 2. 額の下は 4 つだけで、表の字のまま
        for (_, body), r in zip(got, rows):
            # 表の字のまま。玩具の頁に「制作者」を出さない決め（窓口 11-07）は、表の作り手が字を直して守る（11-07 19 時台の表で 0）
            assert f"<b>型紙の版 {r['sheet_version']}</b>" in body and r["engine_version_text"] in body and r["line"] in body, r["set"]
            assert "制作者" not in body and "本人" not in body, r["set"]
            assert all(w["text"] not in body for w in r["why"]) and not re.search(r"#\d", body), ("きっかけと PR は出さない", r["set"])
        # 3. → の印は額の間に 1 つずつ（最初の額の前には無い）。読み上げには出さない
        assert html.count('class="ban-to"') == len(rows) - 1 and ban_ayumi.ARROW not in got[0][1] and 'aria-hidden="true"' in ban_ayumi.ARROW
        assert "→" not in re.sub(r"<[^>]+>", "", html), "→ は字でなく印"
        assert ban_ayumi.SCRIPT in html and "e.scrollLeft=e.scrollWidth" in ban_ayumi.SCRIPT and "resize" in ban_ayumi.SCRIPT, "開いた時と幅が替わった時は今の版の側から"
        # 4. 表は版 1 から持つので「この前にも版があります」は出ない。数の 1 行は表から
        assert rows[0]["sheet_version"] == 1 and ban_ayumi.BEFORE not in html, "版 1 から並ぶ時は、前の版のつなぎを出さない"
        assert ban_ayumi.COUNT.format(first=rows[0]["sheet_version"], last=rows[-1]["sheet_version"], n=len(rows)) in html

    tiger = ban_ayumi.section(T)
    assert "型紙の版 7" in tiger and "版 7" in tiger
    assert "<time datetime=\"2026-11-07\">11 月 7 日</time>" in tiger and "<time datetime=\"2026-11-06\">11 月 6 日</time>" in tiger
    v13 = next(body for _, body in frames(ban_ayumi.section(G)) if "型紙の版 13" in body)
    assert "刻んでいない" in v13, "エンジンの版を刻んでいない版は、表の字のまま"

    # 5. 絵は置いた版（tora-v7）と、repo の中から作れる版（虎 v1〜v3 は刷った PDF・v5・v6 は engine/ の見本）を img。作れない版（虎 v4）は字
    imgs = re.findall(r'<img class="ban-pic" src="([^"]+)"', tiger)
    assert imgs == [f"/history/sheets/tora-v{n}.png" for n in (1, 2, 3, 5, 6, 7)], imgs
    none = f'<span class="ban-pic ban-none">{ban_ayumi.NO_PICTURE}</span>'
    assert tiger.count(none) == 1 and '<span class="ban-pic" aria-hidden="true"></span>' not in tiger, "空の額でなく、残っていないと字で"
    assert [i for i, (_, body) in enumerate(frames(tiger)) if none in body] == [3], "字になるのは、組の JSON も紙も無い虎 v4 の額"
    assert not (kh.PICTURES / "sheets/tora-v1.png").exists(), "頁を返す時は絵を作らない（作れるかだけを見る）"
    goraigo = ban_ayumi.section(G)
    gimgs = re.findall(r'<img class="ban-pic" src="([^"]+)"', goraigo)
    assert gimgs == [f"/history/sheets/goraigo-v{n}.png" for n in (*range(1, 11), 13, 14)] and goraigo.count(none) == 2, gimgs
    assert ban_ayumi.COUNT.format(first=1, last=7, n=7) in tiger and ban_ayumi.COUNT.format(first=1, last=14, n=14) in ban_ayumi.section(G)
    assert ban_ayumi.picture_file("tora-v7") == kh.PICTURES / "sheets/tora-v7.png"
    assert ban_ayumi.picture_file("tora-v4") is None and ban_ayumi.picture_file("../x") is None and ban_ayumi.picture_file("tora-v7.png/..") is None
    made = ban_ayumi.picture_file("tora-v3")  # 求められた時に、刷った PDF の 1 枚目から小さい写しを作る
    assert made == kh.PICTURES / "sheets/tora-v3.png" and made.read_bytes()[:4] == b"\x89PNG"
    from PIL import Image
    assert Image.open(made).size[0] == kh.THUMB_W, Image.open(made).size
    made = ban_ayumi.picture_file("tora-v5")  # 間の版は engine/ の見本（その版の組の JSON）を engine/ のエンジンで刷る
    assert made == kh.PICTURES / "sheets/tora-v5.png" and Image.open(made).size[0] == kh.THUMB_W
    assert ban_ayumi.picture_file("tora-v4") is None, "組の JSON も紙も無い版は作らない"
    server = play_server.serve(0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    r = urllib.request.urlopen(f"{base}/history/sheets/tora-v7.png", timeout=30)
    assert r.status == 200 and r.headers["Content-Type"] == "image/png" and r.read() == b"\x89PNGtora-v7"
    for bad in ("/history/sheets/tora-v4.png", "/history/sheets/Tora-v7.png", "/history/sheets/..%2Fx.png"):
        try:
            urllib.request.urlopen(f"{base}{bad}", timeout=30)
            raise AssertionError(("出してはいけない道が開いた", bad))
        except urllib.error.HTTPError as e:
            assert e.code == 404, (bad, e.code)
    server.shutdown()

    # 6. 今の組の行が表に無い・表に無い玩具は節を出さない。前の組に雛形を置けば、その組が今の版
    keep = TIGER.SHEET_SET
    try:
        TIGER.SHEET_SET = "tora-v99"
        assert ban_ayumi.section(T) == "", "表に無い組を今の版と言わない"
        TIGER.SHEET_SET = TIGER.FROZEN_SET
        old = frames(ban_ayumi.section(T))
        assert len(old) == 3 and old[-1][0] and "型紙の版 3" in old[-1][1] and not old[0][0], old
    finally:
        TIGER.SHEET_SET = keep
    keep_load = kh.load
    cut = {**data, "toys": [{**t, "versions": [v for v in t["versions"] if not v.get("before_loop")]} for t in data["toys"]]}
    kh.load = lambda path=None: cut
    try:
        assert ban_ayumi.BEFORE in ban_ayumi.section(T), "表の最初が版 1 でない時は、前にも版がある事を書く"
    finally:
        kh.load = keep_load
    other = next(p.stem for p in (kh.ROOT / "data/hypotheses").glob("*.json") if p.stem not in (G, T))
    assert ban_ayumi.section(other) == "", other
    # 同じ雛形の別の玩具（雛形の名の欄が無い記録は御来迎の雛形と読む）でも、表の玩具の名と違えば出さない
    from omochae import hypotheses  # noqa: E402
    real = hypotheses.load
    hypotheses_load = lambda sid: {**real(G), "toy": "別の玩具"} if sid == "X" else real(sid)  # noqa: E731
    keep_load, ban_ayumi.load = ban_ayumi.load, hypotheses_load
    try:
        assert ban_ayumi.section("X") == "" and ban_ayumi.section(G), "表の玩具の名と同じ記録だけに出す"
    finally:
        ban_ayumi.load = keep_load
finally:
    kh.PICTURES = keep_pictures

# 7. 玩具の頁の置き場: 原画と立体 → つくる → 型紙の窓 のすぐ後（2 画面目の頭。設計の担当の置き場 11-07）。たとえ（本人の答え Q4 で窓の近く）はその後。
# 表に無い玩具の頁には出ない
from web import toy  # noqa: E402

for sid in (G, T):
    page = toy.toy_page(sid)
    at = page.index('id="ban-ayumi"')
    win = page.index('id="win"')
    after = [page.index(m) for m in ('id="tatoe"', 'id="hanasu"', 'id="tsukuru"') if m in page]
    assert page.count('id="ban-ayumi"') == 1 and win < at < min(after), (sid, win, at, after)
    assert page.index("</section>", win) < at, "型紙の窓の節の中でなく、その後"
    assert "版の歩み" in page and wa.NOW in page[at:]
assert 'id="ban-ayumi"' not in toy.toy_page(other), "表に無い玩具の頁には出さない"

print("ok 型紙の版の歩みの額の並び（古い順・最後が今の版・印・4 つの字・→・始めは右の端・前の版のつなぎ・絵の道・玩具の頁の置き場）")
