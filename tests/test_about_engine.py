"""序の頁（よむ）と README の「うつしと paper to toy」の節（本人の言葉 11-07「このサービスは学校の理科教育や研究活動や博物館などの教育分野で
使われることを想定して始めたけど、公開してみんなが使えるようなサービスになるといいなと思ってきた。paper to toy の一つの具体例であるとか、
エンジンの仕組みとかはデモとサイトで説明した方がいい」→ 窓口: 概要・サイト・デモの説明に反映する）。字は案で、本人の確かめ待ち。

見る事:
1. 序の頁の節は「なぜ」の節の後、断りの段（えらぶ から移した段）と寄せられた声の前に 1 回（版の歩みの表は、この節のすぐ後に別の担当が足す置き場）
2. 節に、位置づけ・具体例の 1 文・仕組みの 5 文（順のまま）・段の図 3 本（畳み）・図の言葉の言い分けが、定数の字のまま出る
3. 頁に「制作者」「提出物」を出さない（序の頁の言い方は「このサイトを作った人」の決め、窓口 11-07）。図の言葉に版の番号を書かない（古くなるため）。
   作る側の言葉（「雛形」「型紙エンジン」）を頁に出さない事は tests/test_reader_words.py が見る
4. README は、頭（本人が採った一言・言葉・説明の 3 行と畳んだ要約。tests/test_readme_head.py）の後の最初の節に同じ字を置く: 見出し・具体例の 1 文
   （paper to toy は型紙エンジンの repo へのリンク）・5 文（README の中は「AI」を「Claude」と書く本人の決定 11-06）・段の図 3 本・図の言葉。位置づけは README の言葉で、教育分野（学校の理科・研究・博物館）と、
   作った物そのものがみんなが使えるサービスである事を書く（本人の直し 11-07）
5. 仕組みの 3 文目は、ぶつかりそうな所を人が見るために書き残す事まで言う（窓口の決め 11-07。3D 検品は近い板を所見として残す作りなので、言い切らない）
6. 英語の頁（/en）にも同じ形の節（窓口の決め 11-07「英語の 3 文は英語の頁に入れる。序の頁は #527 で作る形にそろえる」）: 案内の後・玩具を選ぶ前に 1 回、
   英語の 3 文が順のまま。2 文目の 3D の所も、ぶつかりそうな所を人が見るために残す言い方
"""
import os
import re
import tempfile

os.environ.setdefault("OMOCHAE_DATA", tempfile.mkdtemp())

from web import about  # noqa: E402
from web.play_server import ROOT  # noqa: E402

page = about.page("tenji")

# 1. 置き場
at = page.index('id="engine"')
assert page.count('id="engine"') == 1
assert page.index("<h2>なぜ</h2>") < at < page.index('id="yose"'), "なぜ の後、寄せられた声の前"
yomu = page.index('<section class="sec" id="engine">')
nxt = page.index("</section>", yomu)
assert "<h2>なぜ</h2>" not in page[yomu:nxt]

# 2. 字が定数のまま
sec = page[yomu:nxt]
assert f"<h2>{about.ENGINE_HEAD}</h2>" in sec and about.POSITION in sec and about.EXAMPLE in sec, "位置づけと具体例"
idx = [sec.index(f"<li>{t}</li>") for t in about.ENGINE_STEPS]
assert len(about.ENGINE_STEPS) == 5 and idx == sorted(idx), "仕組みの 5 文が順のまま"
assert '<details class="flows">' in sec and len(about.FLOWS) == 3, "段の図 3 本は畳み"
for name, items in about.FLOWS:
    assert name in sec and all(f"<li>{x}</li>" in sec for x in items), name
assert about.FLOW_NOTE in sec

# 3. 言い方と版の番号
assert "制作者" not in sec and "提出物" not in sec, "序の頁は「このサイトを作った人」の言い方"
assert not re.search(r"v\d|版 \d", about.FLOW_NOTE), "図の言葉に版の番号を書かない"

# 4. README の頭も同じ字
readme = (ROOT / "README.md").read_text(encoding="utf-8")
# 頭の畳みの後の最初の節（頭の字は本人の決定で決まっているので、頭には足さない）
after = readme[readme.index("<!-- summary:end -->"):]
assert after.index(f"\n## {about.ENGINE_HEAD}\n") < after.index("\n## 開発の過程\n"), "頭の後、開発の過程の前の節"
first = after[after.index("</details>"):]
assert first.lstrip("</details>\n").startswith(f"## {about.ENGINE_HEAD}\n"), "頭の畳みのすぐ後の最初の節"
head = after[after.index(f"\n## {about.ENGINE_HEAD}\n"):after.index("\n## 開発の過程\n")]
plain = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", head)
assert about.EXAMPLE in plain, "具体例の 1 文"
assert "[paper to toy](https://github.com/akihidem/paper-to-toy)" in head, "paper to toy は型紙エンジンの repo へ"
# README の中は「AI」でなく「Claude」と書く（本人の決定 11-06、tests/test_readme_head.py）。序の頁は前からの言い方（AI）のまま
assert all(f"{i}. {t.replace('AI が', 'Claude が')}" in head for i, t in enumerate(about.ENGINE_STEPS, 1)), "5 文"
for name, items in about.FLOWS:
    assert f"{name}:" in head and "\n  → ".join(items) in head, name
assert about.FLOW_NOTE in head
assert "教育分野" in head and "理科" in head and "博物館" in head and "みんなが使えるサービスとして作りました" in head, "位置づけ"
# 位置づけは、作った物そのものがみんなが使えるサービスという言い方（本人の直し 11-07「これからというよりは、みんなが使えるサービスとして作った」）。
# これからの思いの言い方（「したいと考えています」「していきたい」）に戻さない
for text in (about.POSITION, head):
    assert "みんなが使えるサービスとして作りました" in text and "したいと考えて" not in text and "していきたい" not in text, text[:80]
# 5. 3 文目は言い切らない
assert "（ぶつかりそうな所は、人が見るために書き残します）" in about.ENGINE_STEPS[2], about.ENGINE_STEPS[2]

# 6. 英語の頁
from web import en  # noqa: E402

ep = en.index_page()
assert ep.count('id="engine"') == 1 and ep.index('id="engine"') < ep.index('id="toys"'), "英語の頁の節は案内の後・玩具を選ぶ前"
esec = ep[ep.index('id="engine"'):ep.index('id="toys"')]
assert f"<h2>{en.ENGINE_HEAD_EN}</h2>" in esec and len(en.ENGINE_EN) == 3
pos = [esec.index(x.replace("'", "&#x27;")) for x in en.ENGINE_EN]
assert pos == sorted(pos), "英語の 3 文が順のまま"
assert "nothing collides" not in esec and "near misses for people to review" in esec, "英語も言い切らない"
print("ok うつしと paper to toy（序の頁の置き場・位置づけ・具体例・仕組みの 5 文・段の図・README の最初の節と同じ字）")
