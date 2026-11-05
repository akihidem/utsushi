"""仮説を並べる入口の試験。既定の 1 案に戻らない事と、予想なしで並ぶ事（#242）を見る。"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

tmp = tempfile.mkdtemp()
os.environ["OMOCHAE_DATA"] = tmp

from omochae.compose import compose
from omochae.hypotheses import load

SID = "NDL-1187053-R0000005-L"
source = json.loads((pathlib.Path(__file__).resolve().parents[1] / "data/sources" / f"{SID}.json").read_text(encoding="utf-8"))
data = load(SID)
hs = data["hypotheses"]
assert len(hs) >= 2, "1 つに断定しない"
assert all("rank" not in h and h["status"] == "untested" for h in hs), "順位を持たない（J-025）"
assert "default" not in json.dumps(data) and not any("既定" in json.dumps(h, ensure_ascii=False) for h in hs)
for h in hs:
    assert h["evidence"] and h["against"] and h["to_measure"], h["id"]
    _, _, failures = compose("slider_fan", h["params"], source)
    assert not failures, (h["id"], [f.line() for f in failures])


def cli(*args):
    return subprocess.run([sys.executable, "-m", "omochae.hypotheses", *args], capture_output=True, text=True)


assert "dl.ndl.go.jp" in cli("picture").stdout and "H-A" not in cli("picture").stdout, "図は仮説の前に見られる"
r = cli("list")
assert r.returncode == 0, "予想の段は無い。開いたらすぐ並ぶ（#242）"
assert cli("predict", "x").returncode != 0, "予想の口は外した"
assert all(h["id"] in r.stdout for h in hs)
assert cli("print", "H-Z").returncode == 4
# 御来迎の今の組で刷れるのは、たたき台の H-A だけ（本人の決定 11-05、J-032）。ほかの仮説は F9.human で断る（tests/test_one_sheet.py）。
assert cli("print", "H-D", "--out", f"{tmp}/d").returncode == 3
r = cli("print", "H-A", "--out", f"{tmp}/d")
assert r.returncode == 0, r.stderr
text = subprocess.run(["pdftotext", f"{tmp}/d.pdf", "-"], capture_output=True, text=True).stdout
assert "仮説A" in "".join(text.split()) and "正しい答えではありません" in "".join(text.split())  # 必須 2 種の今の組もやさしい言葉の文（#318。前の組は凍結の床）

# 自分の仮説から入る道（J-008）。別の置き場で始める
os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
tmp2 = os.environ["OMOCHAE_DATA"]
r = cli("own", "筒を回すと開く")
assert r.returncode == 3 and "F9.own" in r.stderr, "動かし方と根拠が要る"
r = cli("own", "筒を回すと開く", "--how", "筒をねじる", "--evidence", "筒の 2 本線がねじれて見える")
assert r.returncode == 0 and "OWN-1" in r.stdout
r = cli("print-own", "OWN-1", "--out", f"{tmp2}/none")
# 雛形に無い機構を作れるふりをしない。型紙は刷らず、型紙なしの紙を返す（本人の決定）
assert r.returncode == 0 and "F9.own" in r.stderr and not pathlib.Path(f"{tmp2}/none.pdf").exists() and pathlib.Path(f"{tmp2}/none_free.pdf").exists(), r.stderr
free = subprocess.run(["pdftotext", "-layout", f"{tmp2}/none_free.pdf", "-"], capture_output=True, text=True).stdout
assert "型紙なしの紙" in free and "身の回りの紙と紐" in free and "おもちゃとして動きましたか" in free
# 仮説の文の「正解ではありません」は本人の決定で刷る（#258）。打ち消しの文だけを外し、ほかの「正解」は今までどおり落とす
for word in ("正解", "成功", "失敗"):
    assert word not in free.replace("正解ではありません", ""), word
assert cli("own", "壊れた寸法", "--how", "押す", "--evidence", "図", "--params", json.dumps({"push_part": "tab", "tube_side": 500})).returncode == 0
r = cli("print-own", "OWN-2", "--out", f"{tmp2}/bad")
assert r.returncode == 3 and "F5.range" in r.stderr, "自分の仮説も同じ検査を通す"
assert cli("own", "つまみを斜めに", "--how", "溝のつまみを上げる", "--evidence", "寝かせた筒の棒", "--params", json.dumps({"push_part": "tab", "hub": "axle", "pusher_height": 15})).returncode == 0
r = cli("print-own", "OWN-3", "--out", f"{tmp2}/mine")
assert r.returncode == 0, r.stderr
flat = "".join(subprocess.run(["pdftotext", f"{tmp2}/mine.pdf", "-"], capture_output=True, text=True).stdout.split())
assert "自分の仮説" in flat and "仮説D" not in flat
r = cli("list")
assert r.returncode == 0 and r.stdout.index("OWN-1") < r.stdout.index("H-A"), "比べる時は自分の仮説を先に置く"
