"""試作の玩具も選べる所に並ぶ（本人の指示「なるべく並列ですべて作ろう」、11-04）。必須の 2 種は入口の主役のまま。

前は図鑑の一覧に試作の玩具を小さな札で並べる試験だった。図鑑の頁は外した（本人の言葉 11-08「図鑑のページ要らない」）ので、
試作の玩具は入口（えらぶ）の棚に並ぶ事を見る（凍結の表にあるファイルなので、ファイルは残して中身を替えた）。
"""
import os
import re
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from omochae import hypotheses  # noqa: E402
from web import looks  # noqa: E402
from web.looks import toys  # noqa: E402
from web.play_server import SID, sources  # noqa: E402

FAKE = "NDL-1187053-R0000013-L-3"
assert re.fullmatch(SID, FAKE), "1 頁の 2 個目からの印を受ける"
required = [s for s in sources() if hypotheses.stage(s) == "必須"]
rest = [s for s in sources() if hypotheses.stage(s) != "必須"]
assert {t["sid"] for t in toys()} == set(required), "入口の主役は必須だけ"
page = looks.tenji()
for sid in rest[:12] + [FAKE]:
    if sid in rest:
        assert f'href="/toy/{sid}"' in page, (sid, "試作の玩具が入口の棚に無い")
assert 'href="/zukan"' not in page and not re.search(r'href="/zukan/NDL-[^"/]*"', page), "図鑑の頁への道が残った"
print("ok")
