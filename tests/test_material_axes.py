"""紙一枚の印と当時の材料の印（#255）を試験で見る。本人の言葉（2026-11-05）:
「一枚の紙から作る選択肢もある」「竹とか糸は江戸時代にもあったし使ったらよく再現できるということ」。

見る事: 印は雛形の材料の一覧から出る。2 つは別の軸で、順位の語が無い。絞り込みで紙一枚の玩具だけが並ぶ。
"""
import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from omochae import hypotheses  # noqa: E402
from omochae.compose import TEMPLATES  # noqa: E402
from web import toy, toys  # noqa: E402

G, T = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"
gd, td = hypotheses.load(G), hypotheses.load(T)
hyp = lambda d, i: next(h for h in d["hypotheses"] if h["id"] == i)
assert hypotheses.material_marks(G, hyp(gd, "H-E"), gd) == {"paper_only": True, "period": []}
assert hypotheses.material_marks(G, hyp(gd, "H-A"), gd) == {"paper_only": False, "period": ["竹", "糸"]}
assert hypotheses.material_marks(G, hyp(gd, "H-B"), gd) == {"paper_only": False, "period": ["糸"]}
assert hypotheses.material_marks(T, hyp(td, "H-A"), td) == {"paper_only": False, "period": ["竹"]}

# どの玩具でも材料の一覧から出せる。紙だけと当時の材料が同時に立つ仮説は無い（軸の中身が食い違っていない）
seen = {"paper": 0, "period": 0}
for sid in toys.sources():
    data = hypotheses.load(sid)
    for h in data["hypotheses"]:
        m = hypotheses.material_marks(sid, h, data)
        assert not (m["paper_only"] and m["period"]), (sid, h["id"], m)
        seen["paper"] += m["paper_only"]
        seen["period"] += bool(m["period"])
        if m["paper_only"]:
            tpl = TEMPLATES[h.get("template") or data.get("template", "slider_fan")]
            text = " ".join(str(x) for x in tpl.materials({**tpl.DEFAULTS, **h["params"]}))
            for w in ("竹", "糸", "粘土", "割り箸", "楊枝", "ビーズ"):
                assert w not in text, (sid, h["id"], w)
assert seen["paper"] and seen["period"], seen

page = toy.toy_page(G)
assert toy.AXIS_NOTE in page and "<span class=\"lb\">紙だけ</span>" in page and "<span class=\"lb\">当時の材料</span>" in page
for w in ("初心者", "かんたん", "おすすめ", "上級", "順位"):
    assert w not in toy.AXIS_NOTE and w not in toy.material_labels(G, hyp(gd, "H-E"), gd) and w not in toy.material_labels(G, hyp(gd, "H-A"), gd), w

# 絞り込み
listed = toys.page("tenji", "/toys", paper=True)
papers = toys.paper_only_sids(toys.sources())
assert G in papers and T not in papers and 0 < len(papers) < len(toys.sources())
assert f'href="/toy/{G}"' in listed and f'href="/toy/{T}"' not in listed and "全部の玩具を見る" in listed
assert "紙 1 枚で作れる玩具だけを見る" in toys.page("tenji")
print("ok")
