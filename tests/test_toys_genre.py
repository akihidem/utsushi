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
# 中の 9 つは、大きい側のどれか 1 つにだけ入る。どこへ入れるかは本人の答え待ちなので、入れ先と並びは固めない
placed = [m for _, mids in genre.BIG for m in mids]
assert sorted(placed) == sorted(NINE) and len(placed) == len(NINE), genre.BIG
assert [b for b, _ in genre.BIG] == ["かざる", "あそぶ", "うごく"], "大きい側の字は本人の決定（11-06）の 3 つ"

# 2. 玩具: 83 のどれも中の 9 つに入る。決まった例外（凧の 3 本が あげる）だけを固め、ほかの例外と答え待ちは形だけを見る
#    （本人の答えで玩具が PENDING から TOY へ移っても、この試験は直さずに通る。下の 6 で、答えの例の表でも同じ確かめを回す）
sids = toys.sources()
rest = [s for s in sids if hypotheses.stage(s) != "必須"]
inv = {t["id"]: t for t in json.loads((ROOT / "data/inventory/edo-nishiki.json").read_text(encoding="utf-8"))["toys"]}
for sid in KITES:
    assert genre.TOY.get(sid) == "あげる" and genre.middle(sid) == "あげる" and "揚げる" in inv[sid]["moves_guess"], sid


def check_tables():
    """例外と答え待ちの表は在る玩具だけを指し、同じ玩具を両方に置かない。答え待ちの玩具は雛形の表のままで、別の読みは今の中と違う
    （同じなら待つ事が無い）。どの玩具も、例外が無ければ雛形の表の中になる。"""
    assert set(genre.TOY) <= set(sids) and set(genre.PENDING) <= set(sids) and not set(genre.TOY) & set(genre.PENDING)
    for sid in sids:
        tpl = genre.MIDDLE[hypotheses.load(sid).get("template", "slider_fan")]
        assert genre.middle(sid) == (genre.TOY.get(sid) or tpl) in NINE, sid
        if sid in genre.PENDING:
            assert genre.middle(sid) == tpl and genre.PENDING[sid] in NINE and genre.PENDING[sid] != tpl, sid


def check_page(html, rest):
    """頁: 必須 2 種を先頭に置いたまま、その下を大きい側 → 中の見出しで分ける。見出しの省き方は頁と同じ決まりで数える
    （中の字が大きい側と同じで、その大きい側の最初の中の時だけ省く）。"""
    grouped = genre.groups(rest)
    assert re.findall(r"<h2[^>]*>([^<]+)</h2>", html) == [b for b, _ in grouped]
    assert re.findall(r"<h3[^>]*>([^<]+)</h3>", html) == [m for b, mids in grouped for i, (m, _) in enumerate(mids) if not (i == 0 and m == b)]
    shown = {m for _, mids in grouped for m, _ in mids}
    for m in NINE:
        assert (f">{m}</h2>" in html or f">{m}</h3>" in html) == (m in shown), ("0 の見出しを出した" if m not in shown else "見出しが無い", m)
    # 必須 2 種は見出しより前、ほかはそれぞれの中の見出しの後で、次の見出しより前（すぐ前の見出しの字が中の字になる）
    first = html.index("<h2")
    for sid in sids:
        assert (html.index(f'href="/toy/{sid}"') < first) == (hypotheses.stage(sid) == "必須"), sid
    heads = [(m.start(), m.group(2)) for m in re.finditer(r"<(h2|h3)[^>]*>([^<]+)</\1>", html)]
    for sid in rest:
        at = html.index(f'href="/toy/{sid}"')
        assert [w for pos, w in heads if pos < at][-1] == genre.middle(sid), sid
    # 頁の上でも、見出しの中の並びは記録の印の順のまま（名前や数で並べ替えない）
    at = [html.index(f'href="/toy/{s}"') for _, mids in grouped for _, ss in mids for s in ss]
    assert at == sorted(at), "見出しの中の並びを変えた"
    # 足す字はジャンルの字だけ。順位・数の印は付けない（J-025）
    for w in ("位", "人気", "おすすめ"):
        assert w not in re.sub(r"<[^>]+>", "", html[first:]), w


check_tables()

# 3. 束ね: 玩具は 1 度ずつ、並びは記録の印の順のまま。0 の中と 0 の大きい側は入れない
grouped = genre.groups(sids)
flat = [s for _, mids in grouped for _, ss in mids for s in ss]
assert sorted(flat) == sorted(sids) and len(flat) == len(sids)
for _, mids in grouped:
    for m, ss in mids:
        assert ss and ss == sorted(ss, key=sids.index), m

# 4. 頁（白の展示と黒のジンの両方）
for name in skin.SKINS:
    check_page(toys.page(name), rest)

# 5. 紙 1 枚の絞り込みも同じ形で分かれ、0 の見出しは出ない
paper = toys.page("tenji", "/toys", paper=True)
papers = toys.paper_only_sids(sids)
assert re.findall(r"<h2[^>]*>([^<]+)</h2>", paper) == [b for b, _ in genre.groups(papers)]

# 6. 大きい側と中の入れ先は BIG の 1 か所で差し替えられる（字は本人の決定 11-06 の 3 つ。中の入れ先は本人の答え待ち）
keep, keep_toy = genre.BIG, dict(genre.TOY)
try:
    genre.BIG = (("見て たのしむ", ("かざる",)), ("うごかす", tuple(NINE[1:])))
    html = toys.page("tenji")
    assert re.findall(r"<h2[^>]*>([^<]+)</h2>", html) == ["見て たのしむ", "うごかす"]
    assert "<h3" in html and ">かざる</h3>" in html, "大きい側と字が違えば中の見出しを出す"
finally:
    genre.BIG = keep
# 答えの例（本人の答えの入れ方どおり、表だけを変える）。どれも試験を直さずに、上と同じ表と頁の確かめが通る
#   a. 浮き物を かざる の側に入れ、雀を PENDING から TOY へ移して うかべる にする
#   b. 大きい側と同じ字の中が後ろに来る（かざる の下に ゆれる → かざる）。中の見出しを出して、前の中の札と分ける
answers = [
    ((("かざる", ("かざる", "うかべる")), ("あそぶ", ("もって あそぶ", "あげる")), keep[2]), {"NDL-1187053-R0000013-L": "うかべる"}),
    ((("かざる", ("ゆれる", "かざる")), ("あそぶ", ("もって あそぶ", "うかべる", "あげる")), ("うごく", ("ひく おす", "まわす", "ならす", "ころがす"))), {}),
]
keep_pending = dict(genre.PENDING)
for big, moved in answers:
    try:
        genre.BIG, genre.TOY = big, {**keep_toy, **moved}
        genre.PENDING = {k: v for k, v in keep_pending.items() if k not in moved}
        check_tables()
        check_page(toys.page("tenji"), rest)
    finally:
        genre.BIG, genre.TOY, genre.PENDING = keep, keep_toy, keep_pending
# 中が大きい側のどれにも入っていない時と、2 つの大きい側に入った時は、黙って玩具を落とす・2 度出す代わりに止める
try:
    genre.BIG = (("かざる", ("かざる",)),)
    genre.groups(sids)
    raise AssertionError("入れ先の無い中を黙って落とした")
except ValueError as e:
    assert "もって あそぶ" in str(e)
finally:
    genre.BIG = keep
try:
    genre.BIG = keep + (("もう 1 つ", ("かざる",)),)
    genre.groups(sids)
    raise AssertionError("2 つの大きい側に入った中を黙って 2 度出した")
except ValueError as e:
    assert "かざる" in str(e)
finally:
    genre.BIG = keep
print("ok")
