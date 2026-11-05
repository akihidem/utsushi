"""工作の手帖（U-35）。頁の中身は repo のコードから書き出し、仮説の名前と動き方を入れない（作りながら見る頁なので短くする）。"""
import json
import re

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
# 頁も src/api/ask.py と同じ線: 語そのものを尋ねる短い問いだけを語の説明で答える。形は data から読み、頁に二重に持たない（#287）
assert re.fullmatch(d["term_question"], "蛇腹とは") and not re.fullmatch(d["term_question"], "蛇腹が固定できない。どうしたらいい？")
assert "DATA.term_question" in (techo.ROOT / "src/web/techo_page.html").read_text(encoding="utf-8")
print("ok")
