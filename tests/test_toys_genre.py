"""おもちゃの一覧（/toys）をジャンルで分ける試験（本人の依頼 11-06「「鑑賞するおもちゃ」「動くおもちゃ」のようにジャンル分けしたい」、
docs/process/research/36-road-and-audience.md の「決まった事」のジャンル 2 段）。

なぜ: 83 の玩具に手でジャンルを付けると、玩具が増えた時に抜ける。雛形（動き方の族）から表で引く事、表で合わない玩具だけを例外に置く事、
大きい側の字を 1 か所で差し替えられる事、玩具が 0 の見出しを出さない事を、手で見なくても固定する。"""
import json
import os
import re
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from omochae import hypotheses  # noqa: E402
from omochae.compose import TEMPLATES  # noqa: E402
from omochae.hypotheses import ROOT  # noqa: E402
from web import genre, skin, toys  # noqa: E402

NINE = ["かざる", "もって あそぶ", "うかべる", "あげる", "ひく おす", "まわす", "ならす", "ゆれる", "ころがす"]
KITES = ["NDL-1187053-R0000024-L", "NDL-1187053-R0000024-L-2", "NDL-1187053-R0000024-L-3"]

# 1. 表: どの雛形にも中の 9 つのどれかがある（雛形を足して表を足し忘れると、ここで落ちる）
assert set(genre.MIDDLE) == set(TEMPLATES), sorted(set(TEMPLATES) ^ set(genre.MIDDLE))
assert set(genre.MIDDLE.values()) <= set(NINE) and set(genre.TOY.values()) <= set(NINE)
# 中の 9 つは、大きい側のどれか 1 つにだけ入る。並びは決まった事の並びのまま
assert [m for _, mids in genre.BIG for m in mids] == NINE, genre.BIG
assert [b for b, _ in genre.BIG] == ["かざる", "あそぶ", "うごく"], "大きい側の字は本人の決定（11-06）の 3 つ"

# 2. 玩具: 83 のどれも中の 9 つに入る。例外は台帳の動きの言葉が 1 つに決まっている凧の 3 本だけ
sids = toys.sources()
inv = {t["id"]: t for t in json.loads((ROOT / "data/inventory/edo-nishiki.json").read_text(encoding="utf-8"))["toys"]}
assert sorted(genre.TOY) == sorted(KITES)
for sid in KITES:
    assert genre.middle(sid) == "あげる" and "揚げる" in inv[sid]["moves_guess"], sid
for sid in sids:
    want = genre.TOY.get(sid) or genre.MIDDLE[hypotheses.load(sid).get("template", "slider_fan")]
    assert genre.middle(sid) == want in NINE, sid
# 台帳の言葉が「か」で分かれる物は、決まるまで雛形の表のまま（例: 浮き物の雀は かざる）
assert genre.middle("NDL-1187053-R0000013-L") == "かざる"

# 3. 束ね: 玩具は 1 度ずつ、並びは記録の印の順のまま。0 の中と 0 の大きい側は入れない
grouped = genre.groups(sids)
flat = [s for _, mids in grouped for _, ss in mids for s in ss]
assert sorted(flat) == sorted(sids) and len(flat) == len(sids)
for _, mids in grouped:
    for m, ss in mids:
        assert ss and ss == sorted(ss, key=sids.index), m
uka = [s for s in sids if genre.middle(s) == "うかべる"]
assert ("うかべる" in [m for _, mids in grouped for m, _ in mids]) == bool(uka)

# 4. 頁: 必須 2 種を先頭に置いたまま、その下を大きい側 → 中の見出しで分ける
rest = [s for s in sids if hypotheses.stage(s) != "必須"]
for name in skin.SKINS:
    html = toys.page(name)
    h2 = re.findall(r"<h2[^>]*>([^<]+)</h2>", html)
    assert h2 == [b for b, _ in genre.groups(rest)], (name, h2)
    h3 = re.findall(r"<h3[^>]*>([^<]+)</h3>", html)
    assert h3 == [m for b, mids in genre.groups(rest) for m, _ in mids if m != b], (name, h3)
    assert ("うかべる" in html) == bool([s for s in rest if genre.middle(s) == "うかべる"]), "0 の見出しを出した"
    # 必須 2 種は見出しより前、ほかはそれぞれの中の見出しの後で、次の見出しより前
    first = html.index("<h2")
    for sid in sids:
        at = html.index(f'href="/toy/{sid}"')
        assert (at < first) == (hypotheses.stage(sid) == "必須"), sid
    heads = [(m.start(), m.group(2)) for m in re.finditer(r"<(h2|h3)[^>]*>([^<]+)</\1>", html)]
    for sid in rest:
        at = html.index(f'href="/toy/{sid}"')
        # 中の見出しは、大きい側と同じ字の時だけ省く（かざる の下の かざる）。どちらでも、すぐ前の見出しの字が中の字になる
        word = [w for pos, w in heads if pos < at][-1]
        assert word == genre.middle(sid), (sid, word)
    # 頁の上でも、見出しの中の並びは記録の印の順のまま（名前や数で並べ替えない）
    order = [s for _, mids in genre.groups(rest) for _, ss in mids for s in ss]
    at = [html.index(f'href="/toy/{s}"') for s in order]
    assert at == sorted(at), (name, "見出しの中の並びを変えた")
    # 足す字はジャンルの字だけ。順位・数の印は付けない（J-025）
    for w in ("位", "人気", "おすすめ"):
        assert w not in re.sub(r"<[^>]+>", "", html[first:]), w

# 5. 紙 1 枚の絞り込みも同じ形で分かれ、0 の見出しは出ない
paper = toys.page("tenji", "/toys", paper=True)
papers = toys.paper_only_sids(sids)
assert re.findall(r"<h2[^>]*>([^<]+)</h2>", paper) == [b for b, _ in genre.groups(papers)]

# 6. 大きい側と中の入れ先は BIG の 1 か所で差し替えられる（字は本人の決定 11-06 の 3 つ。中の入れ先は本人の答え待ち）
keep = genre.BIG
try:
    genre.BIG = (("見て たのしむ", ("かざる",)), ("うごかす", tuple(NINE[1:])))
    html = toys.page("tenji")
    assert re.findall(r"<h2[^>]*>([^<]+)</h2>", html) == ["見て たのしむ", "うごかす"]
    assert "<h3" in html and ">かざる</h3>" in html, "大きい側と字が違えば中の見出しを出す"
finally:
    genre.BIG = keep
# 中が大きい側のどれにも入っていなければ、黙って玩具を落とさずに止める
try:
    genre.BIG = (("かざる", ("かざる",)),)
    genre.groups(sids)
    raise AssertionError("入れ先の無い中を黙って落とした")
except ValueError as e:
    assert "もって あそぶ" in str(e)
finally:
    genre.BIG = keep
print("ok")
