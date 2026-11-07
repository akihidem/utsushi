"""選ぶのは 2 回目から（本人の言葉 11-08「83 のおもちゃから、1 つ選ぶ、で実際に選ぶのは 2 回目以降にしたい」・本人の決め「A＋Cでよい」）。

見る事:
1. 入口（白）は 題の間 → まずはここから の 2 枚 → 畳み（details#erabu・閉じた形）の順。畳みの札の字は FOLD の形で、数は棚の分け
   （genre.groups）から数えた物（全部・うごく・かざる。固定の字にしない）。札の数の和は全部の数
2. 畳みの中に、前からの見出し（N のおもちゃから、1 つ選ぶ）と棚の敷き詰めと「紙 1 枚で…」の道。並びの写しは data-src のまま（台本が
   畳みを開いた時だけ読む）。錨は前からの #all-toys と、開いた形で着く #erabu
3. 台本: 畳みを開いた時（toggle）か、道が #erabu・#all-toys の時に開いて読む。印を残さない（localStorage・sessionStorage・cookie を使わない）
4. 題の間（縦の組み・浮かぶ玩具）は替えない（前からの試験 test_hall_tate・test_ukabu が見る）
5. のこすの後の道（C）: 手帖の記録の頁に返事の文が出た時だけ、/#erabu への道「次は、{全部} のおもちゃから えらぶ」。返事の無い時は出さない。
   道しるべの釦（class road）にはせず、その下のふつうの道（のこすの後の道しるべは 1 つ・test_ux_stage0）
"""
import os
import re
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from web import genre, looks, techo_site  # noqa: E402
from web.play_server import sources  # noqa: E402

ALL = list(sources())
n, shelves = looks.erabu_counts(ALL)
assert n == len(ALL) and n == sum(k for _, k in shelves) and [b for b, _ in shelves] == [b for b, _ in genre.groups(ALL)]
label = looks.FOLD.format(n=n, shelves="・".join(f"{b} {k}" for b, k in shelves))
assert looks.fold_label(ALL) == label and str(n) in label

# ---- 1・2 入口の並びと畳み
h = looks.tenji()
at = [h.index('id="hall"'), h.index(looks.MAZU), h.index('<details class="tj-fold" id="erabu">')]
assert at == sorted(at), "題の間 → まずはここから → 畳み"
fold = h[h.index('<details class="tj-fold" id="erabu">'):h.index("</details>", h.index('id="erabu"'))]
assert "<details class=\"tj-fold\" id=\"erabu\" open" not in h, "初めは閉じた形"
assert f"<summary>{label}</summary>" in fold, "札の字は数を棚から数えた形"
assert f"{n} のおもちゃから、1 つ選ぶ" in fold and "tj-narabi" in fold and "紙 1 枚で作れるおもちゃだけを見る" in fold
# 原画の写し（out/sources）の無い木（まっさらな clone）では札に絵が無いので、絵がある時だけ data-src を見る
assert ' src="/picture/' not in fold, "並びの写しは開くまで読まない（src にしない）"
assert "/picture/" not in fold or ' data-src="/picture/' in fold
assert 'id="all-toys"' in h

# ---- 3 台本
js = looks.ERABU_JS
assert "addEventListener('toggle'" in js and "location.hash==='#erabu'" in js and "location.hash==='#all-toys'" in js
assert not re.search(r"localStorage|sessionStorage|document\.cookie", js), "印を残さない"

# ---- 5 のこすの後の道
G = "NDL-1187053-R0000005-L"
said = techo_site.records_page(G, msg="残しました")
quiet = techo_site.records_page(G)
go = f'<p class="links next-erabu"><a href="/#erabu">{techo_site.NEXT_ERABU.format(n=n)}</a></p>'
assert said.count(go) == 1 and go not in quiet, "返事の文が出た時だけ"
assert said.index('<p class="road"><a class="go" href="/gallery#ageta">') < said.index(go), "道しるべの釦（字は本人の決めで のこす）の下（道しるべの釦は増やさない）"
assert said.count('<p class="road">') == 1
print("ok 選ぶのは 2 回目から: 入口は 2 枚の下で 83 を畳み（数は棚から）・開いた時だけ写しを読む・印を残さない・のこすの後に 2 回目の道")
