"""API の消費の台帳は、記録の置き場が変わっても 1 本（#151）。

なぜ要るか: 台帳が OMOCHAE_DATA の中にあると、同じ鍵なのに日割りも累計の停止線も置き場ごとに別々に数え、
デモの --fresh（置き場を丸ごと消す）のたびに 0 に戻った。呼ぶ前に止める見張りの穴になる。
"""
import json
import os
import pathlib
import shutil
import sys
import tempfile

ledger = pathlib.Path(tempfile.mkdtemp()) / "api-usage.jsonl"
os.environ["OMOCHAE_USAGE_LEDGER"] = str(ledger)  # 本物の台帳に書かない

from api import budget  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODEL = next(iter(budget.PRICES))


def add_in(data_dir):
    os.environ["OMOCHAE_DATA"] = str(data_dir)
    return budget.add("ask", MODEL, 1000, 100)


# 置き場を変えても、同じ台帳に足される
a, b = pathlib.Path(tempfile.mkdtemp()), pathlib.Path(tempfile.mkdtemp())
one = add_in(a)
two = add_in(b)
rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
assert len(rows) == 2, rows
assert budget._path() == ledger
total_before = sum(r["usd"] for r in rows)
assert abs(total_before - (one + two)) < 1e-9
assert not (a / "api-usage.jsonl").exists() and not (b / "api-usage.jsonl").exists(), "記録の置き場に台帳を作らない"

# --fresh（置き場を丸ごと消す）の後も残る
shutil.rmtree(a)
shutil.rmtree(b)
os.environ["OMOCHAE_DATA"] = str(tempfile.mkdtemp())
assert len(ledger.read_text(encoding="utf-8").splitlines()) == 2, "置き場を消すと台帳も消えた"

# 口を設定しない時は repo の out/ の 1 本。OMOCHAE_DATA には左右されない（ここでは場所を見るだけで、書かない）
del os.environ["OMOCHAE_USAGE_LEDGER"]
assert budget._path() == ROOT / "out/api-usage.jsonl", budget._path()
del os.environ["OMOCHAE_DATA"]
assert budget._path() == ROOT / "out/api-usage.jsonl", budget._path()
os.environ["OMOCHAE_USAGE_LEDGER"] = str(ledger)

# 床の入口は、子の試験ごとに別の一時の台帳を渡す（本物に書かず、試験の間で額が混ざらない）
sys.path.insert(0, str(ROOT / "tests"))
import run_floors  # noqa: E402

base = pathlib.Path(tempfile.mkdtemp())
first, second = run_floors.ledger_env({"X": "1"}, base, "test_a"), run_floors.ledger_env({"X": "1"}, base, "test_b")
assert first["X"] == "1"
assert first["OMOCHAE_USAGE_LEDGER"] != second["OMOCHAE_USAGE_LEDGER"]
assert pathlib.Path(first["OMOCHAE_USAGE_LEDGER"]).parent == base
