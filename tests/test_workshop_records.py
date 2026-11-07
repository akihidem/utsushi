"""玩具の頁の「見本の記録」を、ワークショップのデータの記録に替える（本人の言葉 11-08「見本の記録をワークショップのデータで作成して欲しい。」
「2つのデモ案はもちろん他のおもちゃも。」）。本物の API は呼ばない。

見る事:
1. 感想の「作ったおもちゃ」を玩具の印に結ぶ表は、結べる 10 件だけ。迷う 5 件と、サイトに無い 2 件は入れない（本人の答え待ち）
2. 玩具の頁の「これまでの復元」に、結んだ感想と話された言葉が、序の頁と同じ札・同じ字で出る（2 つのデモ案も、ほかの玩具も）。見本の札と作り物は出ない
3. 結べない・迷う感想は玩具の頁に出ず、序の頁の寄せられた声には全部出る
4. 作った物の頁（ギャラリー）に、見本の畳みと作り物が出ない
"""
import html
import os
import tempfile
import threading
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from omochae import hypotheses  # noqa: E402
from web import demo_samples, techo_site  # noqa: E402
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


def minna(sid):
    page = get(f"/toy/{sid}")
    return page.split('id="minna"', 1)[1].split("</section>", 1)[0]


def esc(t):
    return html.escape(t, quote=True)


# 2. 玩具の頁: 2 つのデモ案と、ほかの玩具
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
    assert techo_site.esc("まだありません。作って残すと、ここに並びます。") not in sec, (sid, "札があるのに「まだありません」を出さない")
# 迷う感想の玩具（独楽）は、玩具の頁に感想が出ない
sec = minna(KOMA)
assert '<div class="voices-real">' not in sec and not any(esc(t) in sec for v in demo_samples.VOICES if v["toy"] in OPEN for _, t in v["fields"])

# 3. 序の頁の寄せられた声には全部出る（結べない・迷う物も）
about = get("/about")
assert all(esc(t) in about for v in demo_samples.VOICES for _, t in v["fields"]), "寄せられた声は 17 件とも序の頁に出る"

# 4. ギャラリーに見本が出ない
gallery = get("/gallery")
# 札と畳みの要素で見る（「is-sample」の語は、序の頁の職人の言葉の見本のために、全体の皮の CSS に残る）
assert '<details class="samples-fold">' not in gallery and 'class="item is-sample"' not in gallery and esc(demo_samples.NOTE) not in gallery, "上げた物の見本は外した"
assert not hasattr(demo_samples, "UPLOADS"), "作り物の 8 件を残さない"
srv.shutdown()
print("ok 玩具の頁の記録はワークショップのデータ: 結べる 10 件と話された言葉・見本なし・迷う物は序の頁だけ")
