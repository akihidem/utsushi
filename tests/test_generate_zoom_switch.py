"""U-12 の比べ（拡大の道具あり・なし）のための切り替え。zoom=False なら道具の一覧に zoom_picture を入れない。本物は呼ばない。"""
import os
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

import json  # noqa: E402

from api.agent import Preview, PreviewClient  # noqa: E402
from api.generate import generate  # noqa: E402
from omochae import hypotheses  # noqa: E402

G = "NDL-1187053-R0000005-L"
src = json.loads(open(f"data/sources/{G}.json", encoding="utf-8").read())


def sent_tools(**kw):
    try:
        generate(src, client=PreviewClient(), image="", **kw)
    except Preview as p:
        return [t["name"] for t in p.request["tools"]]
    raise AssertionError("下見で止まらなかった")


assert "zoom_picture" in sent_tools(), "既定は今までどおり拡大の道具あり"
assert "zoom_picture" not in sent_tools(zoom=False), "zoom=False なら拡大の道具を渡さない"
print("ok")
