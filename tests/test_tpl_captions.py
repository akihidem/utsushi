"""手順の紙の図の説明と結果の欄の見出しを、雛形ごとに持つ（全部の玩具の線の報告、11-05）。
御来迎の筒の言葉（破線は筒の中）を、車・凧・人形の紙に刷らない。必須の 2 種の紙は今までどおり。"""
import json

from omochae import hypotheses
from omochae.compose import TEMPLATES
from omochae.hypotheses import ROOT
from omochae.instructions import RESULT_HEAD, compose_sheet
from web.play_server import sources

OLD = "閉じた時の中の様子（破線は筒の中）"
first = {}
for sid in sources():
    d = hypotheses.load(sid)
    first.setdefault(d.get("template", "slider_fan"), (sid, d["hypotheses"][0]))
for tid, (sid, h) in sorted(first.items()):
    tpl = TEMPLATES[tid]
    src = json.loads((ROOT / "data/sources" / f"{sid}.json").read_text(encoding="utf-8"))
    layout, failures = compose_sheet(tid, h["params"], src, "x", h["how_it_moves"])
    assert not failures, (tid, [f.message for f in failures])
    words = "".join(t.text or "" for t in layout["texts"])  # 折り返した行もつないで探す
    if tid in ("slider_fan", "pivot_counterweight"):
        assert OLD in words and RESULT_HEAD in words, (tid, "必須の 2 種は今までどおり")
        continue
    assert OLD not in words, (tid, "筒の言葉を刷らない")
    assert tpl.DIAGRAM_CAPTION in [t.text for t in layout["texts"]], (tid, "図の説明は 1 行に収める（折れると読みにくい）")
    assert getattr(tpl, "RESULT_HEAD", RESULT_HEAD) in words, tid
print("ok", len(first))
