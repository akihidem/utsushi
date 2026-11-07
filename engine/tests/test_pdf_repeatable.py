"""同じ入力から同じ PDF ができる試験（#37）。

なぜ場面（tests/frozen）でなく試験にするか: 場面は 1 回ずつ刷って床を見るだけで、2 回刷った紙を比べる形を持たない。
別のプロセス・別の時間帯・秒の違う時刻で刷って比べないと、作った時刻の差が見えない。必須 2 種で見る。
必須 2 種の紙は、玩具のたたき台で刷る場面（御来迎 examples/goraigo_v14.json（omochae.sheets の REQUIRED）・首振り虎 pos_tiger_neck）。虎は制作者の決定（2026-11-05）で
たたき台が neck（元の repo の H-A）になったので、hang の場面から替えた（hang の場面は凍結の正の場面として残る）。
御来迎は制作者の決定（2026-11-06）でたたき台が rise（内筒を下から押し上げる形）になったので、pos_tab から替えた。rise には凍結の場面が
無いので、次の組の寸法の見本の場面で刷る（pos_tab は凍結の正の場面として残る）。
"""
import hashlib
import os
import pathlib
import subprocess
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
ENV = {**os.environ, "PYTHONPATH": str(ROOT / "src")}


def printed(scenario, d, name, tz):
    out = pathlib.Path(d) / name
    r = subprocess.run([sys.executable, "-m", "omochae", "--scenario", scenario, "--out", str(out)],
                       cwd=ROOT, env={**ENV, "TZ": tz}, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return out.with_suffix(".pdf").read_bytes()


# 必須 2 種の場面は omochae.sheets の表（REQUIRED）から読む。どの玩具のどの形かは tests/test_sheets.py の 3 が見る
sys.path.insert(0, str(ROOT / "src"))
from omochae.sheets import REQUIRED  # noqa: E402
# 時間帯と秒を変えて同じなら、作った機械の時計は PDF に入っていない
with tempfile.TemporaryDirectory() as d:
    for scenario in REQUIRED.values():
        name = pathlib.Path(scenario).stem
        first = printed(scenario, d, f"{name}_a", "Asia/Tokyo")
        time.sleep(1.1)  # 時刻の欄は秒まで。同じ秒に刷ると、時刻が入っていても同じになる
        second = printed(scenario, d, f"{name}_b", "UTC")
        assert hashlib.sha256(first).hexdigest() == hashlib.sha256(second).hexdigest(), f"{scenario}: 2 回刷った PDF が違う"
print("ok")
