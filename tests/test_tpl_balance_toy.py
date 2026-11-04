"""雛形 balance_toy（釣り合い人形・起き上がり小法師）の線の完成の定義を確かめる。全部の仮説の版 1 が本物の道で刷れ、床に落ちる値は落ちる。"""
import contextlib
import io
import json
import os
import pathlib
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()  # 人の記録（予想・版）を本物の data/ に書かない

from omochae import hypotheses
from omochae.compose import compose
from omochae.metrics import values
from omochae.pivot_model import center
from omochae.templates import balance_toy as bt

ROOT = pathlib.Path(__file__).resolve().parents[1]
TOYS = ("NDL-1187053-R0000007-L", "NDL-1187053-R0000026-L")
inv = json.loads((ROOT / "data/inventory/edo-nishiki.json").read_text(encoding="utf-8"))["toys"]
assert {t["id"] for t in inv if t["lane"] == "balance"} == set(TOYS)

out = pathlib.Path(tempfile.mkdtemp())
count = 0
for sid in TOYS:
    data = hypotheses.load(sid)
    assert data["template"] == bt.ID and data["stage"] == "試作"
    assert 2 <= len(data["hypotheses"]) <= 3
    keys = [h["params"][bt.HYP_KEY] for h in data["hypotheses"]]
    assert len(set(keys)) == len(keys), (sid, "仮説は HYP_KEY の値で分ける")
    for h in data["hypotheses"]:
        with contextlib.redirect_stdout(io.StringIO()):
            rc = hypotheses.print_sheet(sid, h["id"], str(out / f"{sid}_{h['id']}"))
        assert rc == 0, (sid, h["id"], rc)
        count += 1
assert count == 4

source = json.loads((ROOT / "data/sources/NDL-1187053-R0000007-L.json").read_text(encoding="utf-8"))


def floors(params):
    _, _, f = compose(bt.ID, params, source)
    return {(x.floor, x.where) for x in f}


# 腕を水平にすると錘が支点より上に来て、戻らない
assert ("F5.balance", "錘") in floors({"hold": "arm", "arm_deg": 0})
assert center(bt.mass_points({**bt.DEFAULTS, "arm_deg": 0}))[1] < 0
# 既定の腕の角度（図の 60°）では、重心が支点の下にある
assert center(bt.mass_points(bt.DEFAULTS))[1] > bt.MIN_DROP
# 細い着物で腕を真下近くへ伸ばすと、錘が台に当たる
assert ("F5.balance", "錘") in floors({"hold": "arm", "kimono_w": 40, "arm_len": 60, "arm_deg": 80, "stand": 44})
# 回す読み: 大きく振るには掌で回しきれない速さが要る
assert ("F5.balance", "糸") in floors({"hold": "spin", "spin_deg": 60, "thread_len": 10})
# 起き上がり: 細く高い胴は重心が丸い底の中心より上に来る
assert ("F5.balance", "底") in floors({"hold": "round", "body_h": 90, "base_r": 8})
assert ("F5.range", "hold") in floors({"hold": "hang"})
for h in bt.HOLDS:
    assert not floors({"hold": h}), h

# 台帳の式（F7）: 粘土の底を大きくすると起き上がりの余裕が増える。糸を長くすると、同じ振れに要る回し方は遅くてよい
assert values(bt.ID, {"hold": "round", "base_r": 16})["cg_margin_mm"] > values(bt.ID, {"hold": "round"})["cg_margin_mm"]
assert values(bt.ID, {"hold": "spin", "thread_len": 60})["spin_rev_s"] < values(bt.ID, {"hold": "spin"})["spin_rev_s"]
print("ok", count)
