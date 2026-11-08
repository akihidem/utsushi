"""玩具の頁の「見本の記録」を、ワークショップのデータの記録に替える（本人の言葉 11-08「見本の記録をワークショップのデータで作成して欲しい。」
「2つのデモ案はもちろん他のおもちゃも。」）。本物の API は呼ばない。

見る事:
1. 感想の「作ったおもちゃ」を玩具の印に結ぶ表は、結べる 10 件だけ。迷う 5 件と、サイトに無い 2 件は入れない（本人の答え待ち）
2. 結んだ感想と話された言葉は、もちよる（/gallery）の「みんながつくったおもちゃ」のその玩具の札の「感想を見る」に、序の頁と同じ札・同じ字で出る
   （2 つのデモ案も、ほかの玩具も）。見本の札と作り物は出ない。玩具の頁には出ない（本人の言葉 11-08「つくるは読む情報が多すぎて整理する必要を感じる。
   復元の記録などはすべてもちよるに統合する。」で、玩具の頁の「これまでの復元」は もちよる へ移した）
3. 結べない・迷う感想は玩具の頁にも もちよる の玩具の札にも出ず、序の頁の寄せられた声には全部出る
4. 作った物の頁（ギャラリー）に、見本の畳みと作り物が出ない
"""
import html
import os
import re
import tempfile
import threading
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from omochae import hypotheses  # noqa: E402
from web import demo_samples  # noqa: E402
from web.play_server import serve, sources  # noqa: E402

G, TORA, NOBORI, KOMA = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R", "NDL-1187053-R0000020-R-3", "NDL-1187053-R0000026-L-3"
OPEN = {"円型コマ", "独楽 型紙(円盤に串を通す)", "車屏風", "でんでん太鼓", "ぶりぶり", "ぴいぴい", "しからくり台"}

# 1. 結ぶ表
names = [v["toy"] for v in demo_samples.VOICES]
assert set(demo_samples.VOICE_TOYS) <= set(names), "表の鍵は感想の答えの名"
assert sum(n in demo_samples.VOICE_TOYS for n in names) == 10, "結べる 10 件"
assert not (OPEN & set(demo_samples.VOICE_TOYS)) and OPEN <= set(names), "迷う 5 件とサイトに無い 2 件は入れない"
assert set(demo_samples.VOICE_TOYS.values()) <= set(sources()), "結ぶ先はサイトの玩具の印"

srv = serve(0)
threading.Thread(target=srv.serve_forever, daemon=True).start()


def get(path):
    with urllib.request.urlopen(f"http://127.0.0.1:{srv.server_address[1]}{path}", timeout=60) as r:
        return r.read().decode("utf-8")


GALLERY = None


def minna(sid):
    """その玩具の、もちよる の「みんながつくったおもちゃ」の札（玩具の名の道 /toy/<印> を持つ figure）。札が無い玩具は空。
    本人の言葉 11-08「…復元の記録などはすべてもちよるに統合する。」で、前の置き場（玩具の頁の これまでの復元）から移った先。
    同じ時に、玩具の頁にはその玩具の感想と話された言葉の札が 1 つも無い事を見る"""
    global GALLERY
    toy_page = get(f"/toy/{sid}")
    assert 'id="minna"' not in toy_page and esc(demo_samples.VOICES_WHO) not in toy_page and esc(demo_samples.SPOKEN_WHO) not in toy_page, (sid, "玩具の頁に感想の札が残った")
    assert esc(demo_samples.CRAFT_WHO) not in toy_page, (sid, "玩具の頁に職人の言葉の札が残った")
    GALLERY = GALLERY or get("/gallery")
    for m in re.finditer(r'<figure class="workshop">(.*?)</figure>', GALLERY, re.S):
        if f'<a href="/toy/{sid}">' in m.group(1):
            return m.group(1)
    return ""


def esc(t):
    return html.escape(t, quote=True)


# 2. もちよる の玩具の札: 2 つのデモ案と、ほかの玩具
for sid, voices, spoken in ((G, 3, 4), (TORA, 0, 2), (NOBORI, 1, 0)):
    sec = minna(sid)
    name = hypotheses.load(sid)["toy"]
    name = name if isinstance(name, str) else name["name"]
    mine_v = [v for v in demo_samples.VOICES if demo_samples.VOICE_TOYS.get(v["toy"]) == sid]
    mine_s = [s for s in demo_samples.SPOKEN if s["toy"] == name]
    assert (len(mine_v), len(mine_s)) == (voices, spoken), (sid, len(mine_v), len(mine_s))
    for v in mine_v:
        assert all(esc(t) in sec for _, t in v["fields"]), (sid, v["toy"])
    assert all(esc(s["text"]) in sec for s in mine_s), (sid, "話された言葉")
    assert sec.count('<div class="item">') == voices + spoken, (sid, "1 件 1 枚")
    if voices:
        assert esc(demo_samples.VOICES_NOTE) in sec and esc(demo_samples.VOICES_WHO) in sec
    if spoken:
        assert esc(demo_samples.SPOKEN_NOTE) in sec and esc(demo_samples.SPOKEN_WHO) in sec
    assert '<span class="sample">見本</span>' not in sec and "見本の記録" not in sec and 'class="item is-sample"' not in sec, (sid, "見本の札と作り物は出ない")
    assert esc(demo_samples.NOTE) not in sec, (sid, "作り物である事の一文は出ない（本物）")
    assert sec, (sid, "もちよる にその玩具の札が無い")
# 迷う 5 件は本人の答え（11-08）「ワークショップの感想にだけ載せて、おもちゃの頁には出さない。」で、サイトに無い 2 件は本人の答えで、
# 玩具の頁に出さない。83 種すべての玩具の札で見て、候補だった玩具は本物の頁でも見る
# 見る字は、迷う・サイトに無い感想にだけある字（「楽しかったです。」のように、結べる感想にも同じ字がある物は外す）
linked_texts = {t for v in demo_samples.VOICES if v["toy"] in demo_samples.VOICE_TOYS for _, t in v["fields"]}
open_texts = [t for v in demo_samples.VOICES if v["toy"] in OPEN for _, t in v["fields"] if t not in linked_texts]
assert len(open_texts) >= 30, len(open_texts)
for sid in sources():
    t = hypotheses.load(sid)["toy"]
    cards = demo_samples.workshop_for(sid, t if isinstance(t, str) else t["name"])
    # 札の字は 1 つずつ <span> に入るので、要素の字が丸ごと一致するかで見る（「楽しかったです」が「楽しかったです。」の一部に当たらないように）
    assert not any(f"<span>{esc(x)}</span>" in cards for x in open_texts), (sid, "迷う・サイトに無い感想を玩具の頁に出さない")
for sid in (KOMA, "NDL-1187053-R0000029-R-2", "NDL-1187053-R0000021-L-2", "NDL-1187053-R0000025-L", "NDL-1187053-R0000025-L-2",
            "NDL-1187053-R0000007-R", "NDL-1187053-R0000029-L", "NDL-1187053-R0000009-L-2"):
    sec = minna(sid)
    assert not any(f"<span>{esc(x)}</span>" in sec for x in open_texts), (sid, "候補だった玩具の頁にも出ない")

# 型紙レビューの言葉は、もちよる の玩具の札では「職人の言葉」の札で出る（本人の言葉 11-08「改善のために撮影し上た型紙レビュー10本は職人の言葉です。」）
KAZA = "NDL-1187053-R0000020-R"
sec = minna(KAZA)
rev = [s for s in demo_samples.SPOKEN if s["where"] == "review" and s["toy"] == "風車"]
assert rev and all(esc(s["text"]) in sec for s in rev) and esc(demo_samples.CRAFT_WHO) in sec, "もちよる の風車の札に、レビューの言葉が職人の言葉の札で出る"
assert sec.count(esc(demo_samples.SPOKEN_WHO)) == 0, "レビューの言葉をワークショップで話された言葉の札で出さない"

# 3. 序の頁の寄せられた声には全部出る（結べない・迷う物も）
about = get("/about")
assert all(esc(t) in about for v in demo_samples.VOICES for _, t in v["fields"]), "寄せられた声は 17 件とも序の頁に出る"

# 4. ギャラリーに見本が出ない
gallery = get("/gallery")
# 札と畳みの要素で見る（「is-sample」の語は、序の頁の職人の言葉の見本のために、全体の皮の CSS に残る）
# 職人の言葉の節（本人の言葉 11-08「職人の言葉、はもちよるに移動」・中身は見本の札のまま）は頁の足なので、その前で見る
before = gallery[:gallery.index('id="shokunin"')]
assert '<details class="samples-fold">' not in gallery and 'class="item is-sample"' not in before and esc(demo_samples.NOTE) not in gallery, "上げた物の見本は外した"
assert not hasattr(demo_samples, "UPLOADS"), "作り物の 8 件を残さない"
srv.shutdown()
print("ok ワークショップのデータの記録は もちよる の玩具の札に: 結べる 10 件と話された言葉・見本なし・玩具の頁には無い・迷う物は序の頁だけ")
