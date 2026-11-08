"""名前の心（本人の言葉 11-08「「写し」は伝統芸術では、単なる模倣ではなく、過去の大家や名品との対話を通じて、作品の精神やエッセンスを解釈・再創造すること
（茶の湯・日本画・陶磁器・漆芸・能・歌舞伎・和歌の本歌取り）。名前の心として、サイトや README に生かしてほしい。」）。

見る事:
1. 序の頁（よむ）に「名前の心」の節が 1 つあり、頁の頭（大前提の札）の後・作った人の言葉の前に、about.NAME の 3 文が順に出る
2. README の頭の後（「試す」の前）に「## 名前に込めた思い」の節が 1 つあり（README の見出しは本人の訂正 11-08「GitHub（README）では、「名前の心」ではなくて「名前に込めた思い」。」。序の頁の見出しは「名前の心」のまま）、序の頁と同じ 3 文
3. 3 文目はこの作品に当てはめた文（江戸の絵本の絵と歌と向き合い、動きを紙で解釈し直す）
4. 字は英語の表とやさしい日本語の表にあり、やさしい日本語は全ての漢字にルビ
"""
import os
import pathlib
import re
import tempfile

os.environ.setdefault("OMOCHAE_DATA", tempfile.mkdtemp())
ROOT = pathlib.Path(__file__).resolve().parents[1]

from web import about, i18n  # noqa: E402

page = about.page("tenji")
assert page.count('id="namae"') == 1 and f"<h2>{about.NAME_HEAD}</h2>" in page
at = page.index('id="namae"')
assert page.index('class="lead daizen"') < at < page.index('id="kotoba"'), "頁の頭の後・作った人の言葉の前"
idx = [page.index(f'<p class="lead">{t}</p>', at) for t in about.NAME]
assert len(about.NAME) == 3 and idx == sorted(idx), "3 文が順に"
assert "江戸の絵本" in about.NAME[2] and "紙で解釈し直します" in about.NAME[2], "この作品に当てはめた 1 文"

readme = (ROOT / "README.md").read_text(encoding="utf-8")
assert readme.count("\n## 名前に込めた思い\n") == 1 and readme.index("\n## 名前に込めた思い\n") < readme.index("\n## 試す\n"), "README の頭の後・試すの前"
sec = readme[readme.index("\n## 名前に込めた思い\n"):readme.index("\n## 試す\n")]
assert "".join(about.NAME) in sec, "README も序の頁と同じ字"
assert "\n## 名前の心\n" not in readme, "README の見出しは「名前に込めた思い」（本人の訂正 11-08）"

en, easy = i18n.table("en"), i18n.table("easy")
for t in (about.NAME_HEAD, *about.NAME):
    k = i18n.key_of(t)[0]
    assert k in en and k in easy, k[:30]
    assert not re.findall(r"[一-龥々]", i18n.RUBY.sub("", easy[k])), ("ルビの無い漢字", k[:30])
print("ok 名前の心（序の頁と README の同じ字 3 文・英語とやさしい日本語）")
