"""見比べる紙の試験。記録は使い捨ての置き場に書き、本物のデータに触らない。"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

tmp = tempfile.mkdtemp()
os.environ["OMOCHAE_DATA"] = tmp

from omochae.discriminate import compare_table, pick_pair
from omochae.hypotheses import load

FAN, TIGER = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"


def floors(fs):
    return {f.floor for f in fs}


# 計算の値は research/08 と同じ式。H-A〜H-D は同じ扇、H-E だけ帯が短く中心が口にある
rows, fs = compare_table(load(FAN))
assert not fs and len(rows) == 10
by = {(r["a"], r["b"]): r for r in rows}
assert round(by[("H-A", "H-E")]["limit_a"]) == 284 and round(by[("H-A", "H-E")]["limit_b"]) == 178
# 角度で分かれると言えるのは H-E を含む 4 組だけ。残りを見分けられると書かない
assert {k for k, r in by.items() if r["by_angle"]} == {("H-A", "H-E"), ("H-B", "H-E"), ("H-C", "H-E"), ("H-D", "H-E")}
# 虎は見分ける設計をしない（本人の判断）
assert floors(compare_table(load(TIGER))[1]) == {"F11.compare"}
# 負の場面: 同じ仮説どうし、無い仮説
assert floors(pick_pair(load(FAN), "H-A", "H-A")[2]) == {"F11.compare"}
assert floors(pick_pair(load(FAN), "H-A", "H-Z")[2]) == {"F8.references"}


def run(*args):
    return subprocess.run([sys.executable, "-m", "omochae.hypotheses", "--source", args[0], *args[1:]], capture_output=True, text=True)


out = pathlib.Path(tmp) / "cmp"
r = run(FAN, "print-compare", "H-A", "H-E", "--out", str(out))
assert r.returncode == 0, r.stderr
text = subprocess.run(["pdftotext", "-layout", r.stdout.strip(), "-"], capture_output=True, text=True).stdout
assert "昔の作り方の証明にはなりません" in text
# 答えを先に言わない。計算の上限も勝ち負けの語も刷らない
for word in ("284", "178", "正解", "成功", "失敗", "合格", "勝"):
    assert word not in text, word
assert "2 つの型紙" in text
# 型紙が同じ組は 1 個で比べる。2 個作れと刷らない
r = run(FAN, "print-compare", "H-C", "H-D", "--out", str(out))
assert r.returncode == 0, r.stderr
text = subprocess.run(["pdftotext", "-layout", r.stdout.strip(), "-"], capture_output=True, text=True).stdout
assert "型紙は 1 つ" in text and "2 つの型紙" not in text
assert run(TIGER, "print-compare", "H-A", "H-B", "--out", str(out)).returncode == 3
assert run(TIGER, "compare").returncode == 3
lines = run(FAN, "compare")
assert lines.returncode == 0 and "作り手用" in lines.stdout
print("ok")
