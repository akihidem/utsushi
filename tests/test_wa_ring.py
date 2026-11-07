"""型紙がよくなっていく輪の図（web.wa）の床。本人の言葉 11-06「サイトにその仕組みがわかりやすくあるといいよね」。

見る事:
1. 輪の字は、頁に既にある字から取った物（新しい言い方を増やさない）。順は 案 → 作る → 工夫を記録に書く → 次の型紙をよくする
2. 玩具の頁の「すぐ作る」の札のすぐ後に 1 つだけ出る（白の展示と黒のジン、必須 2 種と試作）。真ん中から頁の下の「型紙の改善の輪」へ飛べる
3. 真ん中の数は今の型紙の版だけ（組の番号。紙の題に刷る数と同じ。11-07 に寸法の刻みから替えた）。報告や動いた数は出さない（J-025）
4. 図の札は図の中に収まる（幅 390 の画面で左右の札の端が切れたのを直した）。読み上げの title に輪の順が 1 文で入る
"""
import os
import re
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ.pop("ANTHROPIC_API_KEY", None)

from omochae.marks import PREMISE_PAGE  # noqa: E402
from web import kaizen, toy, wa  # noqa: E402

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
        assert 'href="#kaizen"' in page[at:page.index("</figure>", at)] and 'id="kaizen"' in page, "真ん中から改善の輪の節へ飛べる"

# 3. 真ん中の数は今の型紙の版だけ。型紙の版は組の番号（紙の題に刷る数と同じ。本人の言葉 11-07・窓口の決定 カード 084426）で、
#    寸法の刻み（kaizen の版・ループ 2）は真ん中に出さない（作る側の版の歩みの頁に残す）
from omochae import hypotheses  # noqa: E402
for sid in (G, T, PLAIN):
    n = hypotheses.set_number(hypotheses.load(sid))
    assert wa.set_version(sid) == n and hypotheses.current_set(hypotheses.load(sid)).endswith(f"-v{n}"), sid
    page = toy.toy_page(sid, "tenji")
    fig_at = page.index('id="wa"')
    assert f'<text class="wa-v" x="{wa.CX}" y="{wa.CY + 22}" text-anchor="middle">版 {n}</text>' in page[fig_at:page.index("</figure>", fig_at)], sid
    # 型紙の札の脇にも同じ数を「型紙の版」の字で 1 つ。「エンジンの版」とは言い分ける（エンジンの版はここに出さない）
    assert page.count(f'<span class="lb ban">型紙の版 {n}</span>') == 1 and "エンジンの版" not in page, sid
assert wa.current_version(G, None) == 1
keep = kaizen.versions
kaizen.versions = lambda sid, hid: [{"version": 2}, {"version": 3}]
try:
    assert wa.current_version(G, None) == 3, "寸法の刻みは前のまま数える（作る側の頁が使う）"
    n = wa.set_version(G)
    assert f"版 {n}</text>" in toy.toy_page(G, "tenji") and ">版 3</text>" not in toy.toy_page(G, "tenji"), "真ん中は寸法の刻みでなく型紙の版"
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
    want = f"{data['toy']} 型紙 仮説 {hypotheses.letter(h)} 版 {hypotheses.set_number(data)}"
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
shown = re.findall(r"<text[^>]*>([^<]*)</text>", fig)
assert shown == [s for label in wa.STEPS for s in wa.LINES.get(label, (label,))] + [wa.NOW, "版 1"], shown
assert not re.search(r"[0-9]", "".join(shown).replace("版 1", "")), "版のほかに数を出さない"

# 4. 札は図の中に収まる。読み上げの title に輪の順
for x, y in wa.SPOTS:
    assert 0 <= x - wa.BOX_W / 2 and x + wa.BOX_W / 2 <= wa.W and 0 <= y - wa.BOX_H / 2 and y + wa.BOX_H / 2 <= wa.H, (x, y)
title = re.search(r"<title[^>]*>([^<]*)</title>", fig).group(1)
assert title == " → ".join((*wa.STEPS, wa.STEPS[0])) and 'role="img"' in fig
print("ok 輪の図は札のすぐ後に 1 つ出て、字は頁の字のまま、真ん中は今の型紙の版")
