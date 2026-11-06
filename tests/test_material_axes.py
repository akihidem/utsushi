"""紙一枚の印と当時の材料の印（#255）を試験で見る。本人の言葉（2026-11-05）:
「一枚の紙から作る選択肢もある」「竹とか糸は江戸時代にもあったし使ったらよく再現できるということ」。

印そのものの判定は main の ways（#261）が持ち、tests/test_ways.py が見る。ここでは #255 で足した物を見る:
札に印と断りが出て順位の語が無い事、一覧の絞り込みが札と同じ「紙一枚」の判定で並ぶ事。
（#255 の頃は hypotheses.material_marks で別に判定していた。ways と二重になり札と絞り込みが食い違いうるので外した。）
"""
import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from omochae import ways  # noqa: E402
from web import toy, toys  # noqa: E402

G, T = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"

# 札の印はたたき台の分。紙一枚で作れるたたき台を持つ玩具で見る（必須 2 種は持たない。本人の決定 11-05 19:44 で紙一枚は必須でない）
page = toy.toy_page(toys.paper_only_sids(toys.sources())[0])
assert ways.NOTE in page and "<span class=\"lb\">紙一枚</span>" in page and "<span class=\"lb\">当時の材料</span>" in page
for w in ("初心者", "かんたん", "おすすめ", "上級", "順位"):
    assert w not in ways.NOTE, w

# 絞り込みは札と同じ判定（ways の紙一枚）で並ぶ
listed = toys.page("tenji", "/toys", paper=True)
papers = toys.paper_only_sids(toys.sources())
assert papers == [s for s in toys.sources() if "紙一枚" in ways.toy_labels(s)]
assert G not in papers and T not in papers and len(papers) == 33 and len(toys.sources()) == 83
assert f'href="/toy/{G}"' not in listed and f'href="/toy/{T}"' not in listed and f'href="/toy/{papers[0]}"' in listed and "全部の玩具を見る" in listed
assert "紙 1 枚で作れるおもちゃだけを見る" in toys.page("tenji")
# 絞った一覧の断りは、並んでいる必須の玩具の数に合わせる（必須の 2 種が並ばないのに「先頭の 2 つ」は嘘になる）
assert "先頭の" not in listed and "先頭の 2 つのほかは" in toys.page("tenji")
# 寸法（params）の無い仮説は印を出さずに頁が開く（#255 の頃の判定が持っていた守りを、ways に寄せた後も保つ）
import copy  # noqa: E402
from omochae import hypotheses  # noqa: E402
_load = hypotheses.load
def _no_params(sid):
    d = copy.deepcopy(_load(sid))
    d["hypotheses"][0].pop("params", None)
    return d
hypotheses.load = _no_params
try:
    assert "仮説" in toy.toy_page(G)
finally:
    hypotheses.load = _load
print("ok")
