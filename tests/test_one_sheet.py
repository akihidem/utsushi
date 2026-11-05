"""型紙は玩具ごとに 1 枚のたたき台（本人の決定 11-05、J-032、#332）の試験。

見る事:
1. どの玩具の記録にも、たたき台の紙を指す欄 "sheet" が 1 つあり、型紙にできる仮説を指す。必須 2 種はどちらも H-A
2. hypotheses.sheet_of が、その欄の仮説を返す（ほかの所はここから読む）
3. 必須 2 種の今の組（goraigo-v10・tora-v3）は、たたき台の仮説だけを刷る。ほかの仮説は F9.human で断り、紙を残さない
4. 前の記録（R-0001 御来迎 H-A・R-0002 同 H-C・型紙の直し T-0001）が切れずに読める。仮説を消さずに欄を足したため
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

tmp = tempfile.mkdtemp()
os.environ["OMOCHAE_DATA"] = tmp  # 人が採った新しい仮説（data/loop）を混ぜず、記録の素のままを見る

from omochae import hypotheses  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
G, T = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"

# 1. 欄が全部の玩具にあり、型紙にできる仮説を指す
files = sorted((ROOT / "data/hypotheses").glob("*.json"))
assert len(files) >= 83, len(files)
for path in files:
    data = json.loads(path.read_text(encoding="utf-8"))
    ids = [h["id"] for h in data["hypotheses"]]
    assert data.get("sheet") in ids, (path.name, data.get("sheet"), ids)
    h = next(h for h in data["hypotheses"] if h["id"] == data["sheet"])
    assert h.get("params"), (path.name, "たたき台は寸法を持つ（刷れる紙）")
    assert len(ids) == len(set(ids)), path.name
for sid in (G, T):
    assert json.loads((ROOT / "data/hypotheses" / f"{sid}.json").read_text(encoding="utf-8"))["sheet"] == "H-A", sid

# 2. sheet_of は記録の欄の仮説を返す。順位の欄は持たない（J-025）
for sid in (G, T):
    h = hypotheses.sheet_of(sid)
    assert h["id"] == "H-A" and "rank" not in h, (sid, h["id"])
assert "つまみ" in hypotheses.sheet_of(G)["name"] or "つまみ" in hypotheses.sheet_of(G)["how_it_moves"], "御来迎のたたき台はつまみの形（本人の決定）"
assert "首" in hypotheses.sheet_of(T)["name"], "虎のたたき台は首を通す形で、吊る形でない（本人の決定）"
# ほかの仮説は消していない（記録が仮説の番号で結ばれている）
assert {h["id"] for h in hypotheses.load(G)["hypotheses"]} >= {"H-A", "H-B", "H-C", "H-D", "H-E"}
assert {h["id"] for h in hypotheses.load(T)["hypotheses"]} >= {"H-A", "H-B", "H-C"}


def cli(*args):
    return subprocess.run([sys.executable, "-m", "omochae.hypotheses", *args], capture_output=True, text=True)


# 3. 必須 2 種は、たたき台だけを刷る
for sid, other in ((G, "H-C"), (G, "H-E"), (T, "H-B")):
    stem = f"{tmp}/{sid}_{other}"
    r = cli("--source", sid, "print", other, "--out", stem)
    assert r.returncode == 3 and "F9.human" in r.stderr and "たたき台" in r.stderr, (sid, other, r.returncode, r.stderr)
    assert not list(pathlib.Path(tmp).glob(f"{sid}_{other}*")), "断った紙を残さない"
for sid in (G, T):
    stem = f"{tmp}/{sid}_sheet"
    r = cli("--source", sid, "print", "H-A", "--out", stem)
    assert r.returncode == 0, r.stderr
    for suffix in ("", "_tejun", "_after"):
        assert pathlib.Path(f"{stem}{suffix}.pdf").exists(), (sid, suffix, "型紙と対の手順の紙と試した後の紙")
# 試作の玩具は今の作りのまま（この決定の作りの変更は必須 2 種の今の組から。ほかの玩具の頁と輪は次の直しで）
trial = next(p.stem for p in files if json.loads(p.read_text(encoding="utf-8")).get("stage") == "試作"
             and len(json.loads(p.read_text(encoding="utf-8"))["hypotheses"]) > 1)
assert hypotheses.stage(trial) == "試作"

# 4. 前の記録が切れずに読める
records = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in (ROOT / "data/records").glob("R-*.json")}
for rid, hid in (("R-0001", "H-A"), ("R-0002", "H-C")):
    rec = records[rid]
    assert rec["source_id"] == G and rec["hypothesis_id"] == hid, rid
    assert any(h["id"] == hid for h in hypotheses.load(G)["hypotheses"]), (rid, "記録が指す仮説が読める")
change = json.loads((ROOT / "data/loop/template-change-0001.json").read_text(encoding="utf-8"))
assert change["id"] == "T-0001" and set(change["record_ids"]) <= set(records), "型紙の直しの根拠の記録が読める"
print("ok 型紙は玩具ごとに 1 枚のたたき台。必須 2 種は H-A だけを刷り、前の記録は読める")
