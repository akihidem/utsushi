"""おもちゃの一覧（/toys）と、入口の全部の玩具の節の試験（本人の指示 11-05、要件 L-02）。
なぜ: 入口と一覧から全部の玩具に入れる事、仮説の名前と採らなかった読みを出さない事、順位や成績の言葉が無い事を、手で見なくても固定する。"""
import os
import re
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from omochae.marks import without_premise  # noqa: E402
from omochae import hypotheses  # noqa: E402
from omochae.hypotheses import ROOT  # noqa: E402
from web import looks, skin, toys  # noqa: E402

sids = sorted(p.stem for p in (ROOT / "data/hypotheses").glob("NDL-*.json"))
assert len(sids) >= 3

for name in skin.SKINS:
    html = toys.page(name)
    found = re.findall(r'href="/toy/(NDL-[^"]+)"', html)
    assert sorted(found) == sids, (name, len(found), len(sids))
    assert "御来迎" in html and "張子" in html
    for w in ("仮説 A", "H-A", "怠らし", "成功", "失敗", "正解", "順位"):
        assert w not in without_premise(html), (name, w)
    for sid in sids:
        for h in hypotheses.load(sid)["hypotheses"]:
            assert h["name"] not in html and h["how_it_moves"] not in html, (sid, h["id"])
    assert f'class="skin-{name}' in html and "IntersectionObserver" not in html
    assert "試作" in html and "確かめていません" in html
    # 必須の 2 種は大きく、先頭に
    assert re.findall(r'<li( class="big")?>', html)[:3] == [' class="big"', ' class="big"', ""]  # 必須の 2 種が先頭

for f in (looks.tenji, looks.zine):
    html = f()
    found = set(re.findall(r'href="/toy/(NDL-[^"]+)"', html))
    assert len(found) >= 80 and found == set(sids), (f.__name__, len(found))
    assert "/toys" in html and "/about" in html and "/gallery" in html
    assert "仮説 A" not in html and "怠らし" not in html and "IntersectionObserver" not in html
    assert 'id="all-toys"' in html and "確かめていません" in html
# 一覧の大きい札（必須 2 種）: 縦にも 2 段ぶんにして、横の小さい札の下に穴を作らない。
# 3 列以下では 2 列ぶんの札の横に穴ができるので、狭い幅では 1 列ぶんに戻して 2 枚を横に並べる（#131）
for css, rule in ((skin.BASE, ".toys .big"), (looks.ZINE, ".zn-all li.big"), (looks.TENJI, ".tj-all li.big")):
    assert rule + "{grid-column:span 2;grid-row:span 2}" in css, rule
    assert "@media (max-width:680px){" + rule + "{grid-column:auto;grid-row:auto}}" in css, rule
# 小さい札の図は全体が入る敷き方、字は名前だけ。コマの番号は選ぶ人に伝わらないので図鑑の頁に置く（#133）
for html in (toys.page("tenji"), looks.tenji(), looks.zine()):
    assert "試作 · コマ" not in html and "全部を型紙にする途中の試作" in html
    small = [m for m in re.findall(r'<li><a href="/toy/[^"]+"><div class="pic"[^>]*>', html)]
    assert not small or all("contain" in m and "cover" not in m for m in small), small[:1]
# 写しの無い clone では上の札に図が出ないので、敷き方は生成する字の側でも見る
assert 'if main else "contain"' in (ROOT / "src/web/toys.py").read_text(encoding="utf-8")
assert '_bg(sid, "50% 50%", "contain")' in (ROOT / "src/web/looks.py").read_text(encoding="utf-8")
for css, rule in ((skin.BASE, ".toys .nm"), (looks.ZINE, ".zn-all .nm"), (looks.TENJI, ".tj-all .nm")):
    assert re.search(re.escape(rule) + r"\{[^}]*-webkit-line-clamp:2", css), rule
print("ok")
