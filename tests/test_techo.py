"""工作の手帖（U-35）。頁の中身は repo のコードから書き出し、仮説の名前と動き方を入れない（作りながら見る頁なので短くする）。"""
import json

from omochae import hypotheses
from web import techo

d = techo.data()
blob = json.dumps(d, ensure_ascii=False)
for t in d["toys"]:
    for h in hypotheses.load(t["sid"])["hypotheses"]:
        assert h["how_it_moves"] not in blob and h["name"] not in blob, h["id"]
    assert all(s["label"].startswith("仮説 ") and s["steps"] for s in t["sheets"])
assert [s["id"] for s in d["toys"][0]["sheets"]] == ["H-A", "H-C", "H-D"], "試行で配った紙だけ"
assert "手前にへこむ" in d["glossary"]["谷折り"] and "仕組み" in d["mechanism"]
print("ok")
