"""図鑑の一覧に試作の玩具を小さな札で並べる（本人の指示「なるべく並列ですべて作ろう」、11-04）。必須の 2 種は今までどおり大きく、入口の主役も 2 種のまま。"""
import os
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from omochae import hypotheses  # noqa: E402
from web import zukan  # noqa: E402
from web.looks import toys  # noqa: E402
from web.play_server import SID, sources  # noqa: E402
import re  # noqa: E402

FAKE = "NDL-1187053-R0000013-L-3"
assert re.fullmatch(SID, FAKE), "1 頁の 2 個目からの印を受ける"
real_load, real_stage = hypotheses.load, hypotheses.stage
hypotheses.load = lambda s: {"toy": "月の兎（見立て）", "stage": "試作", "hypotheses": []} if s == FAKE else real_load(s)
hypotheses.stage = lambda s: "試作" if s == FAKE else real_stage(s)

required = [s for s in sources() if real_stage(s) == "必須"]
html = zukan.index_page(required + [FAKE])
assert html.count('class="toy"') == 2, "必須の 2 種は大きいまま"
assert "ほかの玩具" in html and "月の兎（見立て）" in html and "試作" in html and "本の 13 コマ目" in html
assert "まだ確かめていません" in html, "名前が見立てである事を添える"
assert "ほかの玩具" not in zukan.index_page(required), "試作が無い時は出さない"
assert {t["sid"] for t in toys()} == set(required), "入口の主役は必須だけ"
print("ok")
