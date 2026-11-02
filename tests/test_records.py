"""記録の入口と手順の紙の試験。"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

tmp = tempfile.mkdtemp()
os.environ["OMOCHAE_DATA"] = tmp

from omochae.instructions import QUESTIONS, compose_sheet, steps
from omochae.hypotheses import load
from omochae import records
from omochae.records import add, summarize

SID = "NDL-1187053-R0000005-L"
source = json.loads((pathlib.Path(__file__).resolve().parents[1] / "data/sources" / f"{SID}.json").read_text(encoding="utf-8"))


def base(**kw):
    return {"source_id": SID, "hypothesis_id": "H-A", "sheet_version": 1, "result": "動いた", "opened_deg": 120, "opener": "紙の力", "fixes": [], "note": "", **kw}


def floors(fs):
    return {f.floor for f in fs}


# F3: 3 値だけ。既定は無い
assert floors(add(base(result=None))[1]) == {"F3.result"}
assert floors(add(base(result="たぶん動いた"))[1]) == {"F3.result"}
assert floors(add(base(opened_deg=400))[1]) == {"F3.result"}
assert floors(add(base(opener="風"))[1]) == {"F3.result"}
assert floors(add(base(fixes=[{"part": "外筒", "change": "", "outcome": "変わらず"}]))[1]) == {"F3.result"}
assert floors(add(base(note="連絡は 03-1234-5678"))[1]) == {"F3.result"}
# F8: 無い仮説を根拠にしない
assert floors(add(base(hypothesis_id="H-Z"))[1]) == {"F8.references"}
r1, fs = add(base())
assert not fs and r1 == "R-0001"
r2, _ = add(base(result="わからない", opened_deg=None))
r3, _ = add(base(result="動かない", hypothesis_id="H-D", fixes=[{"part": "蛇腹の扇", "change": "折り幅を広げた", "outcome": "変わらず"}]))
s = summarize([json.loads((pathlib.Path(tmp) / "records" / f"{i}.json").read_text(encoding="utf-8")) for i in (r1, r2, r3)])
assert s["H-A"]["動いた"] == 1 and s["H-A"]["わからない"] == 1, "わからないを動いたに数えない"
assert s["H-D"]["動かない"] == 1 and "rank" not in s["H-A"]
rec = json.loads((pathlib.Path(tmp) / "records" / f"{r1}.json").read_text(encoding="utf-8"))
assert rec["by"] == "human"
# CLI は結果を必須にする
cli = subprocess.run([sys.executable, "-m", "omochae.records", "add", "--hypothesis", "H-A"], capture_output=True, text=True)
assert cli.returncode == 4, "結果の無い記録を作らない"
cli = subprocess.run([sys.executable, "-m", "omochae.records", "add", "--hypothesis", "H-A", "--result", "わからない", "--fix", "外筒,紙を替えた,変わらず"], capture_output=True, text=True)
assert cli.returncode == 0 and "R-0004" in cli.stdout
# 手順の紙: 仮説ごとに検査を通り、答えを先に言わない
for h in load(SID)["hypotheses"]:
    layout, failures = compose_sheet("slider_fan", h["params"], source, h["name"], h["how_it_moves"])
    assert not failures, (h["id"], [f.line() for f in failures])
    text = "".join(t.text or "" for t in layout["texts"])
    for bad in ("よね", "はず", "284", "220"):
        assert bad not in text, (h["id"], bad)
    sizes = {s["w"] for s in layout["shapes"] if s["kind"] == "rect" and s["w"] == 30}
    assert sizes == {30}, "3 値の欄は同じ大きさ"
    assert all(q in text for q in QUESTIONS)
tab = next(h for h in load(SID)["hypotheses"] if h["id"] == "H-A")
stick = next(h for h in load(SID)["hypotheses"] if h["id"] == "H-C")
from omochae.templates.slider_fan import DEFAULTS
assert any("溝" in s for s in steps({**DEFAULTS, **tab["params"]}))
assert not any("溝" in s for s in steps({**DEFAULTS, **stick["params"]})), "溝の無い形に溝の手順を出さない"
# 型紙と一緒に手順の紙が刷られ、印が入っている
assert subprocess.run([sys.executable, "-m", "omochae.hypotheses", "predict", "試験の予想"], capture_output=True).returncode == 0
r = subprocess.run([sys.executable, "-m", "omochae.hypotheses", "print", "H-A", "--out", f"{tmp}/a"], capture_output=True, text=True)
assert r.returncode == 0, r.stderr
flat = "".join(subprocess.run(["pdftotext", f"{tmp}/a_tejun.pdf", "-"], capture_output=True, text=True).stdout.split())
assert "手順の紙" in flat and SID in flat and "国立国会図書館デジタルコレクション" in flat and "わからない" in flat
# 虎: 手順と仮説
TSID = "NDL-1187053-R0000014-R"
tsource = json.loads((pathlib.Path(__file__).resolve().parents[1] / "data/sources" / f"{TSID}.json").read_text(encoding="utf-8"))
for h in load(TSID)["hypotheses"]:
    layout, failures = compose_sheet("pivot_counterweight", h["params"], tsource, h["name"], h["how_it_moves"])
    assert not failures, (h["id"], [f.line() for f in failures])
assert subprocess.run([sys.executable, "-m", "omochae.hypotheses", "--source", TSID, "predict", "頭が揺れる"], capture_output=True).returncode == 0
r = subprocess.run([sys.executable, "-m", "omochae.hypotheses", "--source", TSID, "print", "H-C", "--out", f"{tmp}/t"], capture_output=True, text=True)
assert r.returncode == 0, r.stderr
flat = "".join(subprocess.run(["pdftotext", f"{tmp}/t.pdf", "-"], capture_output=True, text=True).stdout.split())
assert TSID in flat and "張子の首振り虎" in flat
assert add(base(source_id=TSID, hypothesis_id="H-C", power="団扇", ten_swings_sec=4.2, result="揺れた"))[1] == []
assert floors(add(base(source_id=TSID, hypothesis_id="H-C", power="念力"))[1]) == {"F3.result"}
# 虎の物差しは頭が揺れるかどうか（research/15）
assert {f.floor for f in records.check({"source_id": "NDL-1187053-R0000014-R", "hypothesis_id": "H-A", "result": "わからない"})} == {"F3.result"}, "虎は 2 値"
assert records.check({"source_id": "NDL-1187053-R0000014-R", "hypothesis_id": "H-A", "result": "揺れない"}) == []
