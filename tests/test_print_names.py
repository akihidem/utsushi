"""刷る命令の既定の出す名前に玩具を入れる。

御来迎と虎はどちらも H-A なので、前は同じ out/templates/H-A_v1.pdf に書き、後から刷った玩具の紙が前の紙を黙って消していた。
見る事:
1. 2 つの玩具の H-A を既定の名前で刷ると、紙が別々に残る（型紙・手順の紙・試した後の紙）
2. 自分の案（どの玩具でも OWN-1 から数える）も別々に残る
3. --out を渡した時は、その名前のまま
"""
import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
G, T = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"
tmp = pathlib.Path(tempfile.mkdtemp())
here = tmp / "here"
here.mkdir()
env = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "OMOCHAE_DATA": str(tmp / "data"), "OMOCHAE_USAGE_LEDGER": str(tmp / "usage.jsonl")}


def cli(*args):
    return subprocess.run([sys.executable, "-m", "omochae.hypotheses", *args], cwd=here, env=env, capture_output=True, text=True)


def words(pdf):
    return subprocess.run(["pdftotext", str(pdf), "-"], capture_output=True, text=True).stdout


def made():
    return sorted(p.name for p in (here / "out/templates").glob("*.pdf"))


# 1. 同じ H-A でも、玩具ごとに別の紙が残る
for sid in (G, T):
    r = cli("--source", sid, "print", "H-A")
    assert r.returncode == 0, r.stderr
assert len(made()) == 6, made()
for sid, toy in ((G, "御来迎"), (T, "張子の首振り虎")):
    assert toy in words(here / "out/templates" / f"{sid}_H-A_v1.pdf"), (toy, "後から刷った玩具の紙で上書きされていない")
for end in ("", "_tejun", "_after"):
    first, second = (words(here / "out/templates" / f"{sid}_H-A_v1{end}.pdf") for sid in (G, T))
    assert first != second, (end, "玩具ごとに別の紙")
# --source を付けない時は御来迎の名前
before = made()
assert cli("print", "H-A").returncode == 0 and made() == before

# 2. 自分の案も別々に残る
for sid in (G, T):
    assert cli("--source", sid, "own", "自分の案", "--how", "引くと開く", "--evidence", "図の折り目").returncode == 0
    r = cli("--source", sid, "print-own", "OWN-1")
    assert r.returncode == 0, r.stderr
assert (here / "out/templates" / f"{G}_OWN-1_v1_free.pdf").exists() and (here / "out/templates" / f"{T}_OWN-1_v1_free.pdf").exists(), made()

# 3. --out はそのまま
r = cli("print", "H-A", "--out", "mine/x")
assert r.returncode == 0 and (here / "mine/x.pdf").exists(), r.stderr
print("ok 既定の名前に玩具が入り、同じ H-A の紙が別々に残る")
