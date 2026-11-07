"""説明の頁と のこす の頁の輪の図（loop_figure）の試験。11-08 から 1 本の輪（うつしの輪）: 作る → のこす → 直す → 刷る
（本人の決め「この案で組み直す」・本人の言葉「構造単純でいきたい」）。

見る事:
1. 本人が採った学びの輪の文（ADOPTED）は一字も替えない（頁に残す。図の下の 1 行は、その中の言葉で学ぶ人から見た言い方）
2. 図は 1 本の輪。4 つの駅が時計回り（作る 上・のこす 右・直す 下・刷る 左）に置かれ、駅ごとに誰がするかの印（直す は Claude）
3. 図の字（駅・誰の印・駅の説明・真ん中の 2 行・下の 1 行）は、どれも 1 回ずつ text の要素に出る（英語の頁の訳の表が字を替えられる形）
4. 読み上げは輪の順の 1 文。図の下に、直す は今、記録を Claude に渡して回している事の 1 行（正直に言う所）
5. 開くたびに同じ絵。画像のファイルと外の物を読まない（前の二つの輪を下絵にした生成の絵は、置き場にあっても使わない）
6. 図の字と下の 1 行は全部、英語の頁の訳の表にある
7. 生成の絵の道（/about/loop-figure/…）は、置き場の確かめた絵を返すだけの前のまま（頁からは呼ばない）
"""
import json
import os
import pathlib
import re
import tempfile
import threading
import urllib.error
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
from web import loop_figure as f  # noqa: E402

ADOPTED = ("作って、確かめて、ふり返って、次を考える。この経験から学ぶ輪（経験学習の輪）は、ワークショップでは、進め役（ファシリテーター）といっしょに一周だけ回ります。"
           "うつしがあると、その後も一人で回り続けられます。のこした記録が、次に作る時の入り口になります。進め役の役目は、型紙と記録の形の中に残っています。")
assert f.ADOPTED == ADOPTED, "本人が採った文は一字も替えない"
# 1. 図の下の 1 行の言葉は ADOPTED の中にある
assert f.LEARNER.split(": ", 1)[1] in ADOPTED
# 2・3. 1 本の輪・4 つの駅・誰の印・字は 1 回ずつ
s = f.drawn()
assert s == f.drawn() and s.count('role="img"') == 1, "開くたびに同じ絵"
texts = re.findall(r"<text[^>]*>([^<]*)</text>", s)
want = [x for _, n, w, d in f.STATIONS for x in (n, w, d)] + [f.NAME, f.CENTER, f.LEARNER]
assert sorted(texts) == sorted(want), texts
assert [n for _, n, _, _ in f.STATIONS] == ["作る", "のこす", "直す", "刷る"] and dict((n, w) for _, n, w, _ in f.STATIONS)["直す"] == "Claude"
pos = {m.group(3): (float(m.group(1)), float(m.group(2))) for m in re.finditer(r'<text x="([\d.]+)" y="([\d.]+)"[^>]*font-size="19"[^>]*>([^<]*)</text>', s)}
(mx, my), (kx, ky), (fx, fy), (px, py) = (pos[n] for n in ("作る", "のこす", "直す", "刷る"))
assert my < ky < fy and kx > mx > px and abs(mx - fx) < 1 and abs(ky - py) < 1, ("時計回りの置き方", pos)
assert s.count("<circle") == 4, "駅は 4 つ"
# 4. 読み上げと正直に言う 1 行
assert f'aria-label="{f.RING_LABEL}"' in s and f.RING_LABEL.startswith(f.NAME)
h = f.svg()
assert h.count("<svg") == 1 and f"<figcaption" in h and f.HONEST in h and h.index("</svg>") < h.index(f.HONEST)
# 5. 画像と外の物を読まない
assert not re.search(r"<image|href=|src=|url\(", h), "画像や外の物を読まない"
# ---- 7 生成の絵（本人の言葉 11-07「qwen2.1 でもっと綺麗な絵を」）: 置き場に確かめた印のある絵がある時だけ、絵の上に同じ字を重ねる。無い・確かめていない時は線の絵。道は確かめた物だけ
from PIL import Image  # noqa: E402

from web.play_server import serve  # noqa: E402

box = pathlib.Path(os.environ["OMOCHAE_DATA"]) / "loop_figure"
box.mkdir(parents=True)
Image.new("RGB", (900, 900), (250, 246, 236)).save(box / "loop-b.jpg")
(box / "checked.json").write_text(json.dumps({"loop-b.jpg": {"checked_by": "確かめた人"}}), encoding="utf-8")
assert "<img" not in f.svg() and "<img" not in f.svg("b"), "確かめた生成の絵が置き場にあっても、頁の図は 1 本の輪の線の絵（前の二つの輪の絵は使わない）"
srv = serve(0, public_open=True)
threading.Thread(target=srv.serve_forever, daemon=True).start()


def get(path):
    try:
        r = urllib.request.urlopen(f"http://127.0.0.1:{srv.server_address[1]}{path}", timeout=60)
        return r.status, r.headers.get("Content-Type"), r.read()
    except urllib.error.HTTPError as e:
        return e.code, None, b""


code, ctype, data = get("/about/loop-figure/loop-b.jpg")
assert code == 200 and ctype == "image/jpeg" and data[:2] == b"\xff\xd8"
for bad in ("loop-c.jpg", "checked.json", "..%2Fx.jpg", "x.jpg"):
    assert get(f"/about/loop-figure/{bad}")[0] == 404, bad
srv.shutdown()

# ---- 6 英語の頁: 図の字は全部、訳の表にある（全頁の英語 #538・表に無い字は test_en_all が止める。読み上げの全文は説明の頁の文と同じ字で、その表の行は説明の頁の担当が持つ）
from web import i18n  # noqa: E402
for word in want + [f.HONEST]:
    # 日本語の字だけ（Claude のような英字の字は、英語の頁でもそのまま出るので表に要らない）
    assert not i18n.CJK.search(word) or i18n.lookup(word), ("図の字の英語が訳の表に無い", word)
print("ok 輪の図: 1 本の輪（うつしの輪）・4 つの駅が時計回り・誰の印・字は 1 回ずつ・正直に言う 1 行・同じ絵・画像を読まない・生成の絵の道は前のまま・英語の表")
