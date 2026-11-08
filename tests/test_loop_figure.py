"""説明の頁と のこす の頁の輪の図（loop_figure）の試験。11-08 から 1 本の輪（うつしの輪）。字は型紙の窓の輪の図（wa.py）と同じ言い方
（本人の決め「この案で組み直す」・本人の言葉「構造単純でいきたい」「型紙の窓のこれまでの説明のほうがわかりやすい」）。

見る事:
1. 本人が採った学びの輪の文（ADOPTED）は一字も替えない（頁に残す）
2. 図は 1 本の輪。4 つの駅は型紙の窓の輪の図の字と同じ物・同じ順（wa.STEPS）で、時計回り（上 → 右 → 下 → 左）に置かれる。
   前の駅の名（作る・のこす・直す・刷る）と、駅の説明の行・図の下の「学ぶ人から見ると」の行は図に出さない（字を減らす）
3. 誰がするかは駅の外の小さな絵: ためしの案は Claude、切って組むと記録に書くは人、次の型紙をよくするは Claude と人（Claude が案を出し人が採る）
4. 図の字（駅の字・誰の絵の下の名・真ん中の 2 行）は text の要素に出る（英語の頁の訳の表が字を替えられる形）
5. 読み上げは輪の順の 1 文。図の下に、次の型紙をよくするのは今、記録を Claude に渡して回している事の 1 行（正直に言う所）
6. 開くたびに同じ絵。画像のファイルと外の物を読まない（前の二つの輪を下絵にした生成の絵は、置き場にあっても使わない）
7. 図の字と下の 1 行は全部、英語の頁の訳の表にある
8. 生成の絵の道（/about/loop-figure/…）は、置き場の確かめた絵を返すだけの前のまま（頁からは呼ばない）
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

# 11-08 から本人の答え「字 1 と絵 A。」の字（前は 11-07 に採った「作って、確かめて、…型紙と記録の形の中に残っています。」）
ADOPTED = ("型紙は、AI が考えた ためしの案（仮説）です。切って、折って、組んで、どう工夫したかを記録に書くと、その記録をもとに次の型紙をよくします。"
           "ワークショップでは進め役の人といっしょに 1 回、うつしがあれば そのあとも ひとりで、この輪をまわせます。")
assert f.ADOPTED == ADOPTED, "本人が採った文は一字も替えない"
from web import wa  # noqa: E402

# 2. 駅は型紙の窓の輪の図と同じ字・同じ順。前の駅の名と、説明の行・学ぶ人の行は出さない
s = f.drawn()
assert s == f.drawn() and s.count('role="img"') == 1, "開くたびに同じ絵"
assert tuple(st[0] for st in f.STATIONS) == wa.STEPS == ("ためしの案（仮説）", "切って、折って、組む", "どう工夫したかを記録に書く", "次の型紙をよくする")
texts = re.findall(r"<text[^>]*>([^<]*)</text>", s)
pieces = [t for n, _ in f.STATIONS for t in wa.LINES.get(n, (n,))]
names = [w for _, who in f.STATIONS for w in who]
want = pieces + names + [wa.NOW, f.CENTER]
assert sorted(texts) == sorted(want), texts
for old in ("作る", "のこす", "直す", "刷る", "学ぶ人から見ると", "紙で作って試す", "手帖に写真・声・字", "記録から型紙を直す", "新しい版の型紙", "人が版を決める"):
    assert old not in texts, ("前の駅の名と説明の行は図に出さない", old)
pos = {}
for m in re.finditer(r'<text x="([\d.]+)" y="([\d.]+)"[^>]*font-size="20"[^>]*>([^<]*)</text>', s):
    pos.setdefault(m.group(3), (float(m.group(1)), float(m.group(2))))
first = [wa.LINES.get(n, (n,))[0] for n, _ in f.STATIONS]
(ax, ay), (bx, by), (cx, cy), (dx, dy) = (pos[t] for t in first)
assert ay < by < cy and bx > ax > dx and abs(ax - cx) < 1 and abs(by - dy) < 1, ("時計回りの置き方", pos)
assert s.count('rx="10"') == 4, "駅は 4 つの札"
# 3. 誰がするかの絵: 人の形（頭の丸）と Claude の印（画面の四角）の数と、駅ごとの名
assert [w for _, w in f.STATIONS] == [("Claude",), ("人",), ("人",), ("Claude", "人")]
assert s.count("<circle") == 3 and s.count('rx="5"') == 2, "人の形が 3 つ・Claude の印が 2 つ"
assert texts.count("人") == 3 and texts.count("Claude") == 2
# 4・5. 読み上げと正直に言う 1 行
assert f'aria-label="{f.RING_LABEL}"' in s and f.RING_LABEL.startswith(f.NAME) and all(n in f.RING_LABEL for n in wa.STEPS)
h = f.svg()
assert h.count("<svg") == 1 and f"<figcaption" in h and f.HONEST in h and h.index("</svg>") < h.index(f.HONEST)
assert wa.STEPS[3] in f.HONEST and "Claude" in f.HONEST, "正直な 1 行は、図の駅の字で言う"
# 6. 画像と外の物を読まない
assert not re.search(r"<image|href=|src=|url\(", h), "画像や外の物を読まない"
# ---- 8 生成の絵（本人の言葉 11-07「qwen2.1 でもっと綺麗な絵を」）: 置き場に確かめた印のある絵がある時だけ、絵の上に同じ字を重ねる。無い・確かめていない時は線の絵。道は確かめた物だけ
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

# ---- 7 英語の頁: 図の字は全部、訳の表にある（全頁の英語 #538・表に無い字は test_en_all が止める。読み上げの全文は説明の頁の文と同じ字で、その表の行は説明の頁の担当が持つ）
from web import i18n  # noqa: E402
for word in want + [f.HONEST, f.RING_LABEL]:
    # 日本語の字だけ（Claude のような英字の字は、英語の頁でもそのまま出るので表に要らない）
    assert not i18n.CJK.search(word) or i18n.lookup(word), ("図の字の英語が訳の表に無い", word)
print("ok 輪の図: 1 本の輪（うつしの輪）・駅は型紙の窓の字で時計回り・誰がするかの絵・前の駅の名を出さない・正直に言う 1 行・同じ絵・画像を読まない・生成の絵の道は前のまま・英語の表")
