"""記録の入口と手順の紙の試験。"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

tmp = tempfile.mkdtemp()
os.environ["OMOCHAE_DATA"] = tmp

from omochae.instructions import QUESTIONS, compose_after, compose_sheet, steps
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
# 手順の紙: 仮説ごとに検査を通り、答えを先に言わない。11-06 から刷る時に手順の紙を組まないので、手順の紙を控えた前の組（goraigo-v10）で見る
# （今の組 goraigo-v14 の内筒を下から押し上げる形の手順の紙は A4 に収まらず、組み方は頁が持つ。tests/test_floor_pin.py の STEP_SHEET_SETS）
from omochae.templates import slider_fan as _fan  # noqa: E402
_now, _fan.SHEET_SET = _fan.SHEET_SET, _fan.FROZEN_SET
for h in load(SID)["hypotheses"]:
    layout, failures = compose_sheet("slider_fan", h["params"], source, h["name"], h["how_it_moves"])
    assert not failures, (h["id"], [f.line() for f in failures])
    text = "".join(t.text or "" for t in layout["texts"])
    for bad in ("よね", "はず", "284", "220"):
        assert bad not in text, (h["id"], bad)
    sizes = {s["w"] for s in layout["shapes"] if s["kind"] == "rect" and s["w"] == 30}
    assert sizes == {30}, "3 値の欄は同じ大きさ"
    assert all(q in text for q in QUESTIONS)
_fan.SHEET_SET = _now
tab = next(h for h in load(SID)["hypotheses"] if h["id"] == "H-A")
stick = next(h for h in load(SID)["hypotheses"] if h["id"] == "H-C")
from omochae.templates.slider_fan import DEFAULTS
assert any("溝" in s for s in steps({**DEFAULTS, **tab["params"]}))
assert not any("溝" in s for s in steps({**DEFAULTS, **stick["params"]})), "溝の無い形に溝の手順を出さない"
# 刷るのは型紙だけ（窓口の決定 推し A・11-06）。型紙に印が入り、手順の紙は組まない
from omochae.hypotheses import sheet_of as _sheet_of  # noqa: E402
r = subprocess.run([sys.executable, "-m", "omochae.hypotheses", "print", _sheet_of(SID)["id"], "--out", f"{tmp}/a"], capture_output=True, text=True)
assert r.returncode == 0, r.stderr
flat = "".join(subprocess.run(["pdftotext", f"{tmp}/a.pdf", "-"], capture_output=True, text=True).stdout.split())
assert SID in flat and "国立国会図書館デジタルコレクション" in flat and not pathlib.Path(f"{tmp}/a_tejun.pdf").exists()
# 虎: 手順と仮説
TSID = "NDL-1187053-R0000014-R"
tsource = json.loads((pathlib.Path(__file__).resolve().parents[1] / "data/sources" / f"{TSID}.json").read_text(encoding="utf-8"))
for h in load(TSID)["hypotheses"]:
    layout, failures = compose_sheet("pivot_counterweight", h["params"], tsource, h["name"], h["how_it_moves"])
    assert not failures, (h["id"], [f.line() for f in failures])
# 虎の今の組で刷れるのは、たたき台の H-A だけ（本人の決定 11-05、J-032）。記録の床は仮説の番号に依らないので、下の H-C の記録はそのまま見る。
r = subprocess.run([sys.executable, "-m", "omochae.hypotheses", "--source", TSID, "print", "H-A", "--out", f"{tmp}/t"], capture_output=True, text=True)
assert r.returncode == 0, r.stderr
flat = "".join(subprocess.run(["pdftotext", f"{tmp}/t.pdf", "-"], capture_output=True, text=True).stdout.split())
assert TSID in flat and "張子の首振り虎" in flat
assert add(base(source_id=TSID, hypothesis_id="H-C", power="団扇", ten_swings_sec=4.2, result="揺れた"))[1] == []
assert floors(add(base(source_id=TSID, hypothesis_id="H-C", power="念力"))[1]) == {"F3.result"}
# 虎の物差しは頭が揺れるかどうか（research/15）
assert {f.floor for f in records.check({"source_id": "NDL-1187053-R0000014-R", "hypothesis_id": "H-A", "result": "わからない"})} == {"F3.result"}, "虎は 2 値"
assert records.check({"source_id": "NDL-1187053-R0000014-R", "hypothesis_id": "H-A", "result": "揺れない"}) == []
# 記録は成績でなく観察（philosophy.md）。紙の文で成績に読ませない
for tid, src, sid in (("slider_fan", source, "NDL-1187053-R0000005-L"), ("pivot_counterweight", tsource, TSID)):
    h = load(sid)["hypotheses"][0]
    layout, _ = compose_sheet(tid, h["params"], src, h["name"], h["how_it_moves"])
    after, _ = compose_after(src, h["name"], load(sid)["after_try"])
    words = " ".join(x.text or "" for x in layout["texts"] + after["texts"])
    # 仮説の文の「正解ではありません」は本人の決定で刷る（#258）。打ち消しの文だけを外し、ほかの「正解」は今までどおり落とす
    assert not any(w in words.replace("正解ではありません", "") for w in ("成功", "失敗", "正解", "合格")), "学ぶ人の紙に成績の語を刷らない"
    assert "おもちゃとして動きましたか" in words  # 見た事の見出しを、本人の着目 1 の問いにした（U-25）
