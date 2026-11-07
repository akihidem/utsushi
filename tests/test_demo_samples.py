"""デモ用の見本（本人の指示、11-04）。ギャラリーに上げた物と職人の言葉（フォームの情報提供）の見本が、作り物と分かる札付きで出る。
本物の記録の置き場には書かない。OMOCHAE_SAMPLES=0 で消える。"""
import os
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from omochae import records  # noqa: E402
from web import demo_samples, techo_site  # noqa: E402
from web.play_server import sources  # noqa: E402
# ワークショップの試行の写真（web.workshop・repo に在る）は、ここが見る「本物の記録が無い時」の形を変えるので、この試験では表を空にする
# （写真が出る形は tests/test_workshop_gallery.py が見る。本人の見直し 11-07 夜の ②⑦）
from web import workshop as _workshop  # noqa: E402

_workshop.TABLE = _workshop.TABLE.with_name("no-such-workshop-photos.json")

# 上げた物の見本はギャラリーに、職人の言葉と寄せられた声の見本は序の頁の節（voices_sections）に出る
# （職人の言葉と寄せる話の入口を序の頁へ移した。本人のサイト体験レビュー 11-07 の言葉 6、直しの設計の D）
gallery, voices = techo_site.gallery_page(sources()), techo_site.voices_sections()
assert gallery.count('class="item is-sample"') == len(demo_samples.UPLOADS), "上げた物の見本がギャラリーに出る"
assert voices.count('class="item is-sample"') == len(demo_samples.CONTRIBUTIONS) + len(demo_samples.VOICES), "職人の言葉と寄せられた声の見本が序の頁の節に出る"
html = gallery + voices
# 寄せられた声の見本（VOICES）も同じ札で出る（11-05、デモの想定の内容）。
assert html.count('class="item is-sample"') == len(demo_samples.UPLOADS) + len(demo_samples.CONTRIBUTIONS) + len(demo_samples.VOICES), "見本が全部出る"
assert demo_samples.NOTE in html, "作り物である事の一文"
# どの見本の枠にも札がある（本物と取り違えない）
for chunk in html.split('class="item is-sample"')[1:]:
    assert chunk.split("</div>")[0].count('<span class="sample">見本</span>') == 1, chunk[:80]
assert "まだ作った物の記録はありません" in html, "本物が無い事は見本があっても隠さない"
assert "（準備中）" not in html, "職人の言葉の 3 枠に見本が入る"
assert all("架空" in c["who"] for c in demo_samples.CONTRIBUTIONS + demo_samples.VOICES), "人の名前は架空と書く"
for sid in sources():
    assert records.all_records(sid) == [], "見本を記録の置き場に書かない"

os.environ["OMOCHAE_SAMPLES"] = "0"
off = techo_site.gallery_page(sources()) + techo_site.voices_sections()
assert "is-sample" not in off and off.count("（準備中）") == 3, "本番では見本を消せる"
print("ok")
