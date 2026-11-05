"""職人・玩具店・実際に遊んだ人の話を、ギャラリーと持ち寄りの同じ入口で集める（本人の決定 11-05、#285）。
入口は「寄せられた声」の節に置く。確認した物だけを札つきで出し、連絡先を出さず、順位を付けず、合言葉なしで開いた場には本物の文を出さない（J-021・J-025・J-028）。"""
import os
import re
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from omochae import contrib  # noqa: E402
from omochae.form_import import FORM_URL  # noqa: E402
from web import demo_samples, techo_site  # noqa: E402


def submit(role, certainty, body, kind="knowhow", **kw):
    c = {"kind": kind, "role": role, "certainty": certainty, "body": body, "toy_name": "虎", "display_name": "紙の人", "contact": "someone@example.test",
         "rights": {"basis": "own_work", "holder": "", "license": "display_only"},
         "attest": {"agrees_terms": True, "adult_or_guardian": True, "no_identifiable_people": True}}
    c.update(kw)
    cid, fails = contrib.submit(c)
    assert cid and not fails, fails
    return cid


def section(html, sid):
    m = re.search(rf'<section[^>]*id="{sid}".*?</section>', html, re.S)
    assert m, sid
    return m.group(0)


def yose(**kw):
    return section(techo_site.gallery_page([], **kw), "yose")


def shokunin(**kw):
    return section(techo_site.gallery_page([], **kw), "shokunin")


# 入口: 3 者の名とフォームへのリンクが「寄せられた声」の節にあり、頁の頭から飛べる。開いた場でも入口は閉じない（確認を通るまで載らないため）。
for kw in ({}, {"photos": False}):
    entry = yose(**kw)
    assert "職人さん、おもちゃ屋さん、実際に遊んだ人の話を集めています。" in entry and FORM_URL in entry, kw
    assert 'href="#yoseru"' in techo_site.gallery_page([], **kw) and 'id="yoseru"' in entry, kw

# 確認の前は出ない
played = submit("played", "遊んだ", "縁側で回して遊んだ", kind="memory", where_when="昭和の頃")
shop = submit("shop", "売っている", "店の棚の下段に並べている", kind="info", origin="店で見た事", display_name="")
craft = submit("craftsperson", "作っている", "糊しろは内側へ折る")
page = techo_site.gallery_page([])
assert not any(b in page for b in ("縁側で回して", "棚の下段に", "糊しろは内側へ折る")), "受付中の投稿は出さない"

# 確認すると札つきで出る。職人の話は「職人の言葉」へ、ほかは「寄せられた声」へ。
for cid in (played, shop, craft):
    assert contrib.approve(cid, "確認者") == []
said, crafted = yose(), shokunin()
assert "縁側で回して遊んだ" in said and "店の棚の下段に並べている" in said and "糊しろは内側へ折る" not in said
assert "糊しろは内側へ折る" in crafted and "縁側で回して" not in crafted
for words in (["遊んだ人", "思い出", "どうして知っているか: 遊んだ", "昭和の頃", "送った人: 紙の人"], ["おもちゃ屋さん・お店", "情報", "どうして知っているか: 売っている", "どこで知ったか: 店で見た事", "送った人: 名前なし"]):
    assert all(w in said for w in words), words
assert all(w in crafted for w in ("職人", "作り方の知見", "どうして知っているか: 作っている"))
assert "someone@example.test" not in techo_site.gallery_page([]), "連絡先は出さない"

# 記録の順に並べ、順位の形を出さない（J-025）
assert said.index("縁側で回して") < said.index("店の棚の下段")
for section_html in (said, crafted):
    assert not re.search(r"順位|ランキング|人気|点数|\d+ 位|いいね", section_html), "順位の形を出さない"

# 本文は字として出す
tag = submit("played", "遊んだ", "<script>x</script>", kind="memory", where_when="昭和の頃")
assert contrib.approve(tag, "確認者") == []
assert "<script>x" not in yose() and "&lt;script&gt;x" in yose()
contrib.withdraw(tag)
assert "&lt;script&gt;x" not in yose(), "取り下げた物は出さない"

# 合言葉なしで開いた場は、本物の文を出さない（J-028。公開の範囲は本人の決定待ち）
closed = techo_site.gallery_page([], photos=False)
assert not any(b in closed for b in ("縁側で回して", "棚の下段に", "糊しろは内側へ折る")), "開いた場に本物の文を出さない"
assert "公開のデモでは、人が書いた文と写真は出しません" in section(closed, "yose")

# 見本: 玩具店と遊んだ人も、札と架空の一文つきで出る。本物は見本より前に置き、見本を切ると見本だけ消える。
assert any("おもちゃ屋さん" in v["who"] for v in demo_samples.VOICES) and any("遊んだ人" in v["who"] for v in demo_samples.VOICES)
assert all("架空" in v["who"] for v in demo_samples.VOICES)
assert said.index("店の棚の下段") < said.index('class="item is-sample"'), "本物は見本の前"
assert demo_samples.VOICES[-1]["title"] in said and demo_samples.NOTE in said
os.environ["OMOCHAE_SAMPLES"] = "0"
off = yose()
assert "is-sample" not in off and "縁側で回して" in off, "見本を切っても本物は残る"
assert "まだ寄せられた声はありません" not in off, "本物があるのに無いと書かない"
assert "まだ寄せられた声はありません" not in yose(photos=False), "開いた場は、無いのか出していないのかを取り違えない"
for cid in (played, shop, craft):
    contrib.withdraw(cid)
assert "まだ寄せられた声はありません" in yose(), "本物も見本も無い時は無いと書く"
print("ok")
