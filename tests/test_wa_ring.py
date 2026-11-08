"""型紙がよくなっていく輪の図（web.wa）の床。本人の言葉 11-06「サイトにその仕組みがわかりやすくあるといいよね」。

見る事:
1. 輪の字は、頁に既にある字から取った物（新しい言い方を増やさない）。順は 案 → 作る → 工夫を記録に書く → 次の型紙をよくする
2. 玩具の頁の仮説の段の図（#wa・断りの後・札の前に 1 つだけ。白の展示と黒のジン、必須 2 種と試作）は、11-08 から のこす の頁の うつしの輪 の図
   （本人の言葉 11-08「つくるの仮説にある図は、のこすのうつしの輪の図にする。」）。駅の字「ためしの案（仮説）」が図の中にある。前の輪の図（wa.ring）は頁に出ない
3. 真ん中の数（wa.ring の図の部品の形）は今の型紙の版だけ（組の番号。紙の題に刷る数と同じ。11-07 に寸法の刻みから替えた）。報告や動いた数は出さない（J-025）。
   玩具の頁では、型紙の版は札の脇の版の札が出す
4. 図の札は図の中に収まる（幅 390 の画面で左右の札の端が切れたのを直した）。読み上げの title に輪の順が 1 文で入る
"""
import os
import re
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ.pop("ANTHROPIC_API_KEY", None)

from omochae.marks import PREMISE_PAGE  # noqa: E402
from web import kaizen, loop_figure, toy, wa  # noqa: E402

G, T, PLAIN = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R", "NDL-1187053-R0000009-L-2"

# 1. 字は頁に既にある字から
assert wa.STEPS == ("ためしの案（仮説）", "切って、折って、組む", "どう工夫したかを記録に書く", "次の型紙をよくする")
assert "ためしの案（仮説）" in PREMISE_PAGE and "どう工夫したかを記録に書" in PREMISE_PAGE and "次の型紙をよくする" in PREMISE_PAGE
for label, lines in wa.LINES.items():
    assert "".join(lines) == label, "2 行に分けるのは置き方だけで、字は変えない"

# 2. 置き場: 札のすぐ後に 1 つだけ。真ん中から改善の輪の節へ
for sid in (G, T, PLAIN):
    for look in ("tenji", "zine"):
        page = toy.toy_page(sid, look)
        # 「すぐ作る」の頭の文は、見出しを外した後、型紙の窓の頭へ移した（本人のサイト体験レビュー 11-07 の 3）。輪の図も窓の頭の札の前
        assert "切って、折って、組みます" in page, "「切って、折って、組む」は型紙の窓の頭の文の字"
        assert page.count('id="wa"') == 1, (sid, look)
        at, premise = page.index('id="wa"'), page.index('id="premise"')
        assert premise < at and page.index("</p>", premise) < at < page.index('class="plates"'), "札のすぐ後"
        # 図は のこす の頁と同じ うつしの輪（同じ部品・同じ文）。駅の字「ためしの案（仮説）」が図の中にあり（統括の割り振り 11-08）、前の輪の図（真ん中に版と
        # 説明の頁の改善の歴史への道）は無い。頁の足の「型紙の改善の輪」の節は外したまま（本人の答え 11-07 夕の Q5）
        fig = page[at:page.index("</figure>", at)]
        assert loop_figure.svg() in fig + "</figure>" and loop_figure.ADOPTED in page[at:page.index('class="plates"')], (sid, look, "うつしの輪の図でない")
        # 図の中の字（SVG の text・2 行に分けた駅の字はつなげて読む）に「ためしの案（仮説）」がある
        assert "ためしの案（仮説）" in "".join(re.findall(r"<text[^>]*>([^<]*)</text>", fig)), (sid, look, "図の中に ためしの案（仮説） が無い")
        assert 'class="wa-c"' not in page and 'class="wa-v"' not in page and 'id="kaizen"' not in page, (sid, look, "前の輪の図が残った")
        # 前の線: 真ん中の行き先は説明の頁（序の頁）の改善の歴史の錨（窓口の決め 11-07。輪の図は残し、頁の足の「型紙の改善の輪」の節は外した）（本人の答え 11-07 夕の Q5 で、玩具の頁の足の「型紙の改善の輪」は外し、作る側の様子の頁 /loop/<印> へ移した）
        # 部品の wa.ring には残る（頁には出さない）
assert f'href="{wa.HREF}"' in wa.ring(1) and wa.HREF == "/about#kaizen-rekishi", "部品の真ん中から説明の頁の改善の歴史へ飛べる"

# 3. 真ん中の数は今の型紙の版だけ。型紙の版は組の番号（紙の題に刷る数と同じ。本人の言葉 11-07・窓口の決定 カード 084426）で、
#    寸法の刻み（kaizen の版・ループ 2）は真ん中に出さない（作る側の版の歩みの頁に残す）
from omochae import hypotheses  # noqa: E402
for sid in (G, T, PLAIN):
    n = hypotheses.set_number(hypotheses.load(sid))
    assert wa.set_version(sid) == n and hypotheses.current_set(hypotheses.load(sid)).endswith(f"-v{n}"), sid
    page = toy.toy_page(sid, "tenji")
    # 部品の wa.ring の真ん中は今の型紙の版（玩具の頁には出さない。上の 2）
    assert f'<text class="wa-v" x="{wa.CX}" y="{wa.CY + 22}" text-anchor="middle">版 {n}</text>' in wa.ring(wa.set_version(sid)), sid
    # 型紙の札の脇にも同じ数を「型紙の版」の字で 1 つ。「エンジンの版」とは言い分ける（エンジンの版はここに出さない）。
    # 版の歩みの節（#ban-ayumi）の額の下には、型紙の版とエンジンの版を言い分けて出す（設計 0.7 節）ので、その節を外して見る
    outside = re.sub(r'<section[^>]*id="ban-ayumi".*?</section>', "", page, flags=re.S)
    assert page.count(f'<span class="lb ban">型紙の版 {n}</span>') == 1 and "エンジンの版" not in outside, sid
assert wa.current_version(G, None) == 1
keep = kaizen.versions
kaizen.versions = lambda sid, hid: [{"version": 2}, {"version": 3}]
try:
    assert wa.current_version(G, None) == 3, "寸法の刻みは前のまま数える（作る側の頁が使う）"
    n = wa.set_version(G)
    # 玩具の頁の札の脇の版の札は、寸法の刻みでなく型紙の版（前は輪の図の真ん中で見ていた。図を うつしの輪 に替えた後も、版は札が出す）
    # 版の歩みの節（#ban-ayumi）は前の組の額（型紙の版 3 など）を並べるので、仮説の札の所（#kasetsu-fuda から たとえ の前まで）で見る
    page = toy.toy_page(G, "tenji")
    fuda = page[page.index('id="kasetsu-fuda"'):page.index('id="tatoe"')]
    assert f'<span class="lb ban">型紙の版 {n}</span>' in fuda and "型紙の版 3<" not in fuda, "札の版は寸法の刻みでなく型紙の版"
finally:
    kaizen.versions = keep
# 版の呼び方は組の番号で統一（窓口の決定 11-07）。組の中で人が採った直しがある時だけ「（直し N）」
assert hypotheses.label_of("goraigo-v10") == "版 10" and hypotheses.label_of("goraigo-v10", 2) == "版 10（直し 2）"
assert hypotheses.label_of("tora-v4", 1) == "版 4" and hypotheses.label_of("spin-v1", 1) == "版 1"
# 紙の題: 今の組は組の番号、前の組（凍結の床の控え）は前の題「版 N」のまま
from omochae.compose import TEMPLATES, kept_sets  # noqa: E402
gd, td = hypotheses.load(G), hypotheses.load(T)
assert hypotheses.paper_label(gd, 1) == f"版 {hypotheses.set_number(gd)}" and hypotheses.paper_label(gd, 3) == f"版 {hypotheses.set_number(gd)}（直し 3）"
tiger = TEMPLATES[td.get("template")]
now = tiger.SHEET_SET
try:
    tiger.SHEET_SET = kept_sets(tiger)[0]
    assert hypotheses.paper_label(td, 1) == "版 1" and hypotheses.paper_label(td, 2) == "版 2", "前の組の紙は前の題のまま"
finally:
    tiger.SHEET_SET = now
assert hypotheses.paper_label(td, 1) == f"版 {hypotheses.set_number(td)}"
# 玩具の頁の 3D の机の上の紙の題（assembly._sheet_title）: 刷る紙の題から「…」の仮説の名を外した「玩具の名 型紙 仮説 A 版 N」。
# 前は雛形の呼び名の括弧（御来迎は「内筒を下から押し上げる」＝今のたたき台と違う仮説の名で、動き方の答え）が出た（J-013・11-07 夕の気づき）。
# 版は組の番号（窓口の決定 (a)）。題は前より短く、型紙エンジンの 3D の JSON と部品の配置が合うまま（test_tora_v7_3d・test_goraigo_v14_3d）
from omochae import assembly  # noqa: E402

for sid in (G, T):
    bench = assembly.assemble(sid)
    data = hypotheses.load(sid)
    h = hypotheses.sheet_of(sid)
    want = f"{data['toy']} 型紙 仮説 版 {hypotheses.set_number(data)}"  # 仮説の印は出さない（本人の言葉 11-08「つくる、のところ仮説Cとか仮説Aとかはなしで仮説、と表記する」・hypotheses.SHOWN）
    texts = [getattr(t, "text", None) or "" for t in bench.paper["texts"]]
    assert want in texts, (sid, texts[:2])
    assert not any("（" in x and "型紙" in x for x in texts) and not any(h["name"] in x for x in texts), (sid, "動き方の字（雛形の呼び名・仮説の名）を出さない")
# 組の名前に -v<数> が無い雛形は 1
keep_cs = hypotheses.current_set
hypotheses.current_set = lambda data: "plain"
try:
    assert hypotheses.set_number({}) == 1
finally:
    hypotheses.current_set = keep_cs
fig = wa.ring(1)
# 日本語の図の字（英語の頁でだけ見せる英語の図 en-fig は、tests/test_ring_en_fit が見る）
shown = re.findall(r"<text[^>]*>([^<]*)</text>", re.search(r'<svg class="ja-fig".*?</svg>', fig, re.S).group(0))
assert shown == [s for label in wa.STEPS for s in wa.LINES.get(label, (label,))] + [wa.NOW, "版 1"], shown
assert not re.search(r"[0-9]", "".join(shown).replace("版 1", "")), "版のほかに数を出さない"

# 4. 札は図の中に収まる。読み上げの title に輪の順
for x, y in wa.SPOTS:
    assert 0 <= x - wa.BOX_W / 2 and x + wa.BOX_W / 2 <= wa.W and 0 <= y - wa.BOX_H / 2 and y + wa.BOX_H / 2 <= wa.H, (x, y)
title = re.search(r"<title[^>]*>([^<]*)</title>", fig).group(1)
assert title == " → ".join((*wa.STEPS, wa.STEPS[0])) and 'role="img"' in fig
print("ok 仮説の段の図は うつしの輪（断りの後・札の前に 1 つ・ためしの案（仮説）が図の中）。部品の輪の図の字は頁の字のまま、真ん中は今の型紙の版")
