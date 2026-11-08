"""序の頁（よむ）と README の「うつしと paper to toy」の節（本人の言葉 11-07「このサービスは学校の理科教育や研究活動や博物館などの教育分野で
使われることを想定して始めたけど、公開してみんなが使えるようなサービスになるといいなと思ってきた。paper to toy の一つの具体例であるとか、
エンジンの仕組みとかはデモとサイトで説明した方がいい」→ 窓口: 概要・サイト・デモの説明に反映する）。字は案で、本人の確かめ待ち。

見る事:
1. 序の頁の節は「なぜ」の節の後、断りの段（えらぶ から移した段）と寄せられた声の前に 1 回（版の歩みの表は、この節のすぐ後に別の担当が足す置き場）
2. 節の見える所は README のエンジンの節と同じ短い字（具体例の本文・位置づけの 1 文目・engine/README.md への道。本人の答え 11-08「推しのとおり。」）。
   具体例の括弧の中・仕組みの 5 文（順のまま）・段の図 3 本・図の言葉の言い分けは、畳み（エンジンの流れ）の中に、定数の字のまま出る
3. 頁に「制作者」「提出物」を出さない（序の頁の言い方は「このサイトを作った人」の決め、窓口 11-07）。図の言葉に版の番号を書かない（古くなるため）。
   作る側の言葉（「雛形」「型紙エンジン」）を頁に出さない事は tests/test_reader_words.py が見る
4. README は、エンジンの話を短い 1 節（型紙を作るエンジン）にまとめて engine/README.md へつなぐ（11-08 の書き直し）。前は頭の後の最初の節に同じ字を置いていた: 見出し・具体例の 1 文
   （paper to toy は型紙エンジンの repo へのリンク）・5 文（README の中は「AI」を「Claude」と書く本人の決定 11-06）・段の図 3 本・図の言葉。位置づけは README の言葉で、教育分野（学校の理科・研究・博物館）と、
   作った物そのものがみんなが使えるサービスである事を書く（本人の直し 11-07）
5. 仕組みの 3 文目は、ぶつかりそうな所を人が見るために書き残す事まで言う（窓口の決め 11-07。3D 検品は近い板を所見として残す作りなので、言い切らない）
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

# 2. 字が定数のまま。見える所は README と同じ短い字（具体例の本文・位置づけの 1 文目・engine/README.md への道）で、仕組みの 5 文と段の図は
# 畳みの中（本人の答え 11-08「推しのとおり。」。本人の言葉 11-07「エンジンの仕組みとかはデモとサイトで説明した方がいい」で、仕組みは外さず畳む）
sec = page[yomu:nxt]
fold = sec[sec.index('<details class="flows">'):]
shown = sec[:sec.index('<details class="flows">')]
assert f"<h2>{about.ENGINE_HEAD}</h2>" in shown and about.EXAMPLE_MAIN in shown and about.POSITION_FIRST in shown, "具体例の本文と位置づけの 1 文目"
assert shown.index(about.EXAMPLE_MAIN) < shown.index(about.POSITION_FIRST), "README の節と同じ順（具体例 → 位置づけ）"
assert f'<a href="{about.ENGINE_README}">{about.ENGINE_MORE}</a>' in shown and about.ENGINE_README.endswith("/engine/README.md"), "engine/README.md への道"
assert about.ENGINE_MORE in (ROOT / "README.md").read_text(encoding="utf-8").replace("[engine/README.md](engine/README.md)", "engine/README.md"), "道の文は README の節の字"
assert (ROOT / "engine/README.md").exists()
# 位置づけの 2 文目と 3 文目は頁に出さない（同じ頁の大前提の 1 段目と、思いの核の後の 2 文が同じ事を言う）。具体例の括弧の中は畳みの頭
assert about.POSITION not in sec and about.POSITION.split("。")[1] not in sec and about.EXAMPLE not in sec
assert about.EXAMPLE_NOTE in fold and "<li>" not in shown, "仕組みの 5 文と段の図は畳みの中だけ"
idx = [fold.index(f"<li>{t}</li>") for t in about.ENGINE_STEPS]
assert len(about.ENGINE_STEPS) == 5 and idx == sorted(idx), "仕組みの 5 文が順のまま"
assert len(about.FLOWS) == 3, "段の図 3 本は畳み"
for name, items in about.FLOWS:
    assert name in sec and all(f"<li>{x}</li>" in sec for x in items), name
assert about.FLOW_NOTE in sec

# 3. 言い方と版の番号
assert "制作者" not in sec and "提出物" not in sec, "序の頁は「このサイトを作った人」の言い方"
assert not re.search(r"v\d|版 \d", about.FLOW_NOTE), "図の言葉に版の番号を書かない"

# 4. README は、エンジンの話を短い 1 節にまとめて engine/README.md へつなぐ（本人の言葉 11-08「うつしのリードミー、エンジンが合流してぐちゃぐちゃに
# なってしまっているから…優勝できる形にしよう」）。前の「うつしと paper to toy」の節（序の頁と同じ字）は README から外し、序の頁にだけ残す。
# 位置づけの言い方（本人の直し 11-07「これからというよりは、みんなが使えるサービスとして作った」）は、エンジンの節の 1 文に残す
readme = (ROOT / "README.md").read_text(encoding="utf-8")
ENGINE = "## 型紙を作るエンジン（paper to toy）"
assert f"\n## {about.ENGINE_HEAD}\n" not in readme and readme.count(f"\n{ENGINE}\n") == 1, "README のエンジンの節は短い 1 つ"
head = readme[readme.index(f"\n{ENGINE}\n"):readme.index("\n## ", readme.index(f"\n{ENGINE}\n") + 3)]
assert "[paper to toy](https://github.com/akihidem/paper-to-toy)" in head and "[engine/README.md](engine/README.md)" in head, "エンジンの repo と engine/README.md へつなぐ"
# 位置づけの 1 文目の見張りは 1 つにした（前は「みんなが使えるサービスとして作りました」が README にある事・序の頁の定数にある事・
# 序の頁の 1 文目と README が同じ字である事を、3 か所で重ねて見ていた）。ここは、これからの思いの言い方が戻っていない事だけを見る
assert not [w for w in ("したいと考えて", "していきたい") for t in (head, about.POSITION) if w in t], "位置づけは作った物の言い方（これからの思いにしない）"
# README の中は「AI」でなく「Claude」と書く（本人の決定 11-06、tests/test_readme_head.py）。序の頁は前からの言い方（AI）のまま
assert not re.search(r"(?<![A-Za-z])AI(?![A-Za-z])", re.sub(r"「[^」]*」", "", head)), "README の中は Claude と書く"
# 序の頁と README の字の照らし（別の目の指摘 11-08 で戻した見張り）: 大前提の 3 段・エンジンの節の具体例の 1 文・位置づけの 1 文目は、序の頁の定数と同じ字
assert all(readme.count(x) >= 1 for x in about.PREMISE), "大前提の 3 段が序の頁と違う"
# README は具体例の 1 文の本文だけ（括弧の中のエンジンの細かい事は engine/README.md へ・README にエンジンの細かい事を混ぜない書き直し 11-08）
assert about.EXAMPLE.split("（")[0] + "。" in head, "具体例の 1 文が序の頁と違う"
# 位置づけの 1 文目は、序の頁と README で同じ「うつしは、みんなが使えるサービスとして作りました。」（本人の直し 11-07）
assert about.POSITION.split("。")[0] + "。" == "うつしは、みんなが使えるサービスとして作りました。" and about.POSITION.split("。")[0] + "。" in head, "位置づけの 1 文目が序の頁と違う"
# 位置づけの 3 文目: 見方は作った人の物・体験はだれにでも（本人の構成の押さえ 11-07、窓口の決めの案 2）。序の頁の字のまま
assert about.POSITION.split("。")[1] + "。" == "学校の理科の授業や研究、博物館など、教育の場で使う事を考えて始めた物です。", "2 文目を替えない"
assert about.POSITION.endswith("もとにある見方は作った人だけの物ですが、紙で作って確かめる体験そのものは、だれにでもしてほしい事です。"), "見方と体験の言い分け"
# 5. 3 文目は言い切らない
assert "（ぶつかりそうな所は、人が見るために書き残します）" in about.ENGINE_STEPS[2], about.ENGINE_STEPS[2]

print("ok うつしと paper to toy（序の頁の置き場・位置づけ・具体例・仕組みの 5 文・段の図・README のエンジンの短い節と大前提が序の頁と同じ字）")
