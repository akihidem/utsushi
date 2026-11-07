"""説明の頁の学びの輪の図（二つの輪を手書きの風合いで重ねる・窓口の決め 155253）の試験。

見る事:
1. 図の字は、本人が採った文（案 1・11-07「案 1 の字でよい」）の言葉だけ（どの字も ADOPTED の中にそのままある）
2. 2 つの形（a・b）のどちらも、どの字も 1 回ずつ text の要素に出る（英語の頁の訳の表が字を替えられる形）
3. 読み上げには ADOPTED の全文
4. 開くたびに同じ絵（揺れは決まった種）。既定は b（UX の担当の推し・本人の確かめ待ち）
5. 線の絵（drawn）は画像のファイルを読まない（その場で描く SVG）。外の部品も読まない。生成の絵を使う時の読み方は 7
6. 図の字は全部、英語の頁の訳の表にある
7. 生成の絵（Qwen Image 2.1・本人の言葉 11-07）は、置き場に確かめた印のある絵がある時だけ、絵の上に同じ字を重ねて使う。無い時は線の絵。絵の道は確かめた物だけ
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
for key, word in f.WORDS.items():
    assert word in ADOPTED, ("図の字は採った文の言葉だけ", key, word)
for v in ("a", "b"):
    s = f.drawn(v)
    assert f.svg(v) == s, "生成の絵が無い時は線の絵"
    texts = re.findall(r"<text[^>]*>([^<]*)</text>", s)
    assert sorted(texts) == sorted(f.WORDS.values()), (v, texts)
    assert f'aria-label="{ADOPTED}"' in s and 'role="img"' in s
    assert s == f.drawn(v), "開くたびに同じ絵"
    assert not re.search(r"<image|href=|src=|url\(", s), "画像や外の物を読まない"
assert f.svg() == f.svg("b"), "既定は b"
assert f.svg("a") != f.svg("b")
# ---- 7 生成の絵（本人の言葉 11-07「qwen2.1 でもっと綺麗な絵を」）: 置き場に確かめた印のある絵がある時だけ、絵の上に同じ字を重ねる。無い・確かめていない時は線の絵。道は確かめた物だけ
from PIL import Image  # noqa: E402

from web.play_server import serve  # noqa: E402

box = pathlib.Path(os.environ["OMOCHAE_DATA"]) / "loop_figure"
box.mkdir(parents=True)
Image.new("RGB", (900, 900), (250, 246, 236)).save(box / "loop-b.jpg")
assert "<img" not in f.svg("b"), "checked.json が無い間は線の絵"
(box / "checked.json").write_text(json.dumps({"loop-b.jpg": {"checked_by": ""}}), encoding="utf-8")
assert "<img" not in f.svg("b"), "確かめた印が空なら線の絵"
(box / "checked.json").write_text(json.dumps({"loop-b.jpg": {"checked_by": "確かめた人"}}), encoding="utf-8")
h = f.svg("b")
assert h.count('<img src="/about/loop-figure/loop-b.jpg"') == 1 and "<path" not in h, "絵の上に字だけ（線は描かない）"
assert sorted(re.findall(r"<text[^>]*>([^<]*)</text>", h)) == sorted(f.WORDS.values()) and f'aria-label="{ADOPTED}"' in h
assert "<img" not in f.svg("a"), "a の絵は無いので a は線の絵"
outside = pathlib.Path(tempfile.mkdtemp()) / "x.jpg"; outside.write_bytes(b"x")
(box / "loop-a.jpg").symlink_to(outside)
(box / "checked.json").write_text(json.dumps({"loop-b.jpg": {"checked_by": "確かめた人"}, "loop-a.jpg": {"checked_by": "x"}}), encoding="utf-8")
assert "<img" not in f.svg("a"), "置き場の外を指す印は使わない"
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
for bad in ("loop-a.jpg", "loop-c.jpg", "checked.json", "..%2Fx.jpg", "x.jpg"):
    assert get(f"/about/loop-figure/{bad}")[0] == 404, bad
srv.shutdown()

# ---- 6 英語の頁: 図の字は全部、訳の表にある（全頁の英語 #538・表に無い字は test_en_all が止める。読み上げの全文は説明の頁の文と同じ字で、その表の行は説明の頁の担当が持つ）
from web import i18n  # noqa: E402
for word in f.WORDS.values():
    assert i18n.lookup(word), ("図の字の英語が訳の表に無い", word)
print("ok 学びの輪の図: 採った文の言葉だけで、a と b の 2 つの形。読み上げは全文・同じ絵・画像を読まない・図の字は全部英語の表にある")
