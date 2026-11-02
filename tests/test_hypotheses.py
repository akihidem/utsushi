"""仮説を並べる入口の試験。既定の 1 案に戻らない事と、予想が先に要る事を見る。"""
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
assert all(h["rank"] is None and h["status"] == "untested" for h in hs), "記録の無い順位を付けない"
assert "default" not in json.dumps(data) and not any("既定" in json.dumps(h, ensure_ascii=False) for h in hs)
for h in hs:
    assert h["evidence"] and h["against"] and h["to_measure"], h["id"]
    _, _, failures = compose("slider_fan", h["params"], source)
    assert not failures, (h["id"], [f.line() for f in failures])


def cli(*args):
    return subprocess.run([sys.executable, "-m", "omochae.hypotheses", *args], capture_output=True, text=True)


r = cli("list")
assert r.returncode == 3 and "F9.prediction" in r.stderr and "H-A" not in r.stdout, "予想の前に仮説を見せない"
assert cli("print", "H-A", "--out", f"{tmp}/x").returncode == 3 and not pathlib.Path(f"{tmp}/x.pdf").exists()
assert cli("predict", "  ").returncode == 3
assert cli("predict", "筒を押すと上の飾りが開く。動力は手").returncode == 0
r = cli("list")
assert r.returncode == 0 and "筒を押すと上の飾りが開く" in r.stdout
assert r.stdout.index("筒を押すと") < r.stdout.index("H-A"), "予想を仮説より先に置く"
assert all(h["id"] in r.stdout for h in hs)
assert cli("print", "H-Z").returncode == 4
r = cli("print", "H-D", "--out", f"{tmp}/d")
assert r.returncode == 0, r.stderr
text = subprocess.run(["pdftotext", f"{tmp}/d.pdf", "-"], capture_output=True, text=True).stdout
assert "仮説D" in "".join(text.split()) and "答えではありません" in "".join(text.split())
