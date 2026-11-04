"""おもちゃの一覧（/toys）と、入口の全部の玩具の節の試験（本人の指示 11-05、要件 L-02）。
なぜ: 入口と一覧から全部の玩具に入れる事、仮説の名前と採らなかった読みを出さない事、順位や成績の言葉が無い事を、手で見なくても固定する。"""
import os
import re
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

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
        assert w not in html, (name, w)
    for sid in sids:
        for h in hypotheses.load(sid)["hypotheses"]:
            assert h["name"] not in html and h["how_it_moves"] not in html, (sid, h["id"])
    assert f'class="skin-{name}' in html and "IntersectionObserver" not in html
    assert "試作" in html and "確かめていません" in html
    # 必須の 2 種は大きく、先頭に
    assert html.index('class="big"') < html.index("試作 · コマ")

for f in (looks.tenji, looks.zine):
    html = f()
    found = set(re.findall(r'href="/toy/(NDL-[^"]+)"', html))
    assert len(found) >= 80 and found == set(sids), (f.__name__, len(found))
    assert "/toys" in html and "/about" in html and "/gallery" in html
    assert "仮説 A" not in html and "怠らし" not in html and "IntersectionObserver" not in html
    assert 'id="all-toys"' in html and "確かめていません" in html
print("ok")
