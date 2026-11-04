"""再現ギャラリー（J-022 の 3）。記録の順に同じ形で並べ、順位と「再現できた」を書かず、仮説の動き方を載せない。"""
import os
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from omochae import gallery, loop, records  # noqa: E402
from omochae.hypotheses import load  # noqa: E402

G = "NDL-1187053-R0000005-L"
assert "試した記録はまだ無い" in gallery.build()
r1, _ = records.add({"source_id": G, "hypothesis_id": "H-C", "sheet_version": 1, "result": "動いた"})
r2, _ = records.add({"source_id": G, "hypothesis_id": "H-A", "sheet_version": 1, "result": "動かない", "tried_on": "2026-11-04"})
loop.save_explanation(r2, "本人", "折りが固い", "強くしごく")
page = gallery.build()
assert page.index(r1) < page.index(r2), "記録の順"
assert "動かない" in page and "折りが固い" in page and "p01.jpg" in page
for word in ("再現できた", "順位", "1 位", "成功", "失敗"):
    assert word not in page, word
for h in load(G)["hypotheses"]:
    assert h["how_it_moves"] not in page, "仮説の動き方を載せない"
print("ok")
