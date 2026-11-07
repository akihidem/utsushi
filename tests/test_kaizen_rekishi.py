"""序の頁の「型紙とエンジンの改善の歴史」（設計 0.7 節の置き場 ③。本人の言葉 11-07「どう改善が進むかは山場なのでデモにも載せたいところ。
サイトにも記載したい」）。

見る事:
1. 序の頁の「なぜ」の後、おもちゃを選ぶ断りの段の前に、節が 1 つ（<section id="kaizen-rekishi">）。題と山場の流れは表の字
2. 玩具ごとの型紙の版は出さない（玩具の頁の版の歩みが持つ。序の頁の「仕組みの答えと仮説の名前を書かない」決まりのため。窓口の決定 11-07 案 A）
3. エンジンの版は全部（刷った型紙の組つき・PR つき）、エンジンそのものの直しも全部
4. 表の作り手の言い方「制作者」「本人」は「このサイトを作った人」に替え、作る側の言葉（表の「言葉」の欄・採った案の番号）は出さない。
   動き方の字（「押し上げ」「扇が開く」）と、表の spoiler の印のきっかけも出さない
5. 表が読めない時は節を出さず、序の頁はほかの節だけで開く
"""
import os
import re
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from omochae import kaizen_history as kh  # noqa: E402
from web import about, kaizen_rekishi  # noqa: E402
from web.wording import MAKER  # noqa: E402

data = kh.load()
html = kaizen_rekishi.section()
text = re.sub(r"<[^>]+>", " ", html)

# 1. 置き場と題
page = about.page("tenji")
at = page.index('id="kaizen-rekishi"')
assert page.count('id="kaizen-rekishi"') == 1 and page.index("<h2>なぜ</h2>") < at < page.index('href="/toys"'), "なぜ の後、選ぶ釦の前"
assert f"<h2>{data['title']}</h2>" in html and kaizen_rekishi._maker(data["story"]) in html

# 2. 玩具ごとの型紙の版は出さない（玩具の頁の版の歩みが持つ）。序の頁の決まり（仕組みの答えと仮説の名前を書かない）に当たる字も無い
assert "（型紙の版）" not in html and "<b>型紙の版" not in html
assert not [w for w in ("成功", "失敗", "正解", "仮説 A", "H-A", "つまみ", "内筒") if w in text], "序の頁の決まりの字"

# 2 の続き. エンジンの行にも御来迎の動き方の字を出さない（窓口の決め (a) で表の作り手が出し直した 2 行。見張りの決まった語の外の字なので、ここで見る）
assert "押し上げ" not in text and "扇が開く" not in text, "序の頁の改善の歴史に動き方の字"
# 本人の言葉で仕組みを含むきっかけ（表の spoiler の印）は、動き方を見せない頁に出さない（統括の決め 11-07）
spoilers = [w["text"] for t in data["toys"] for v in t["versions"] for w in v.get("why", []) if w.get("spoiler")]
assert spoilers and not [w for w in spoilers if kaizen_rekishi._maker(w) in page or w in page], "spoiler の付いたきっかけが序の頁に出た"

# 3. エンジンの版と、エンジンそのものの直し
assert len(re.findall(r"<b>エンジンの版 \d+</b>", html)) == len(data["engine_versions"]) == 7
assert all(f"/paper-to-toy/pull/{e['pr']}\">#{e['pr']}</a>" in html for e in data["engine_versions"] if e.get("pr"))
assert "刷った型紙の組: 虎 型紙の版 4・御来迎 型紙の版 11" in html, "エンジンの版 2 が刷った組"
changes = html[html.index(kaizen_rekishi.CHANGES_HEAD):]
assert all(kaizen_rekishi._maker(c["line"]) in changes for c in data["engine_changes"]) and len(data["engine_changes"]) == 9

# 4. 言い方と、出さない物
assert "制作者" not in text and "本人" not in text and MAKER in text
engine = html[html.index(f"<h3>{kaizen_rekishi.ENGINE_HEAD}</h3>"):html.index(f"<h3>{kaizen_rekishi.CHANGES_HEAD}</h3>")]
assert "EP-" not in engine, "エンジンの版に付く採った案の番号の並び（proposals）は出さない（きっかけの字の中の番号は表の字のまま）"
assert "data/engine/versions.json" not in text and data["terms"]["型紙の版"] not in text, "表の「言葉」の欄（作る側の言葉）は出さない"
assert 'class="sec kaizen-rekishi"' in html and "<table" not in html, "狭い画面でも読めるよう表の形にしない"

# 5. 表が読めない時
keep = kh.load
kh.load = lambda path=None: (_ for _ in ()).throw(OSError("無い"))
try:
    assert kaizen_rekishi.section() == ""
    assert 'id="kaizen-rekishi"' not in about.page("tenji") and "<h2>なぜ</h2>" in about.page("tenji")
finally:
    kh.load = keep

print("ok 序の頁の改善の歴史（置き場・型紙の版・エンジンの版と直し・作り手の言い方・読めない時）")
