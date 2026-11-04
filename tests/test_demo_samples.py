"""デモ用の見本（本人の指示、11-04）。ギャラリーに上げた物と職人の言葉（フォームの情報提供）の見本が、作り物と分かる札付きで出る。
本物の記録の置き場には書かない。OMOCHAE_SAMPLES=0 で消える。"""
import os
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from omochae import records  # noqa: E402
from web import demo_samples, techo_site  # noqa: E402
from web.play_server import sources  # noqa: E402

html = techo_site.gallery_page(sources())
# 寄せられた声の見本（VOICES）も同じ札で出る（11-05、デモの想定の内容）。
assert html.count('class="item is-sample"') == len(demo_samples.UPLOADS) + len(demo_samples.CONTRIBUTIONS) + len(demo_samples.VOICES), "見本が全部出る"
assert demo_samples.NOTE in html, "作り物である事の一文"
# どの見本の枠にも札がある（本物と取り違えない）
for chunk in html.split('class="item is-sample"')[1:]:
    assert chunk.split("</div>")[0].count('<span class="sample">見本</span>') == 1, chunk[:80]
assert "まだ上げた物はありません" in html, "本物が無い事は見本があっても隠さない"
assert "（準備中）" not in html, "職人の言葉の 3 枠に見本が入る"
assert all("架空" in c["who"] for c in demo_samples.CONTRIBUTIONS + demo_samples.VOICES), "人の名前は架空と書く"
for sid in sources():
    assert records.all_records(sid) == [], "見本を記録の置き場に書かない"

os.environ["OMOCHAE_SAMPLES"] = "0"
off = techo_site.gallery_page(sources())
assert "is-sample" not in off and off.count("（準備中）") == 3, "本番では見本を消せる"
print("ok")
