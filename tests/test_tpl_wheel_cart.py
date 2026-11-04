"""雛形 wheel_cart（鼠車・俵）の線の完成の定義を確かめる。全部の玩具の全部の仮説の版 1 が本物の道で刷れ、床に落ちる値は落ちる。

本物の道（hypotheses.print_sheet）を通すのは、compose だけ通っても手順の紙や試した後の紙で落ちる事があるため。
"""
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
from omochae.templates import wheel_cart as wc

ROOT = pathlib.Path(__file__).resolve().parents[1]
TOYS = ("NDL-1187053-R0000019-L", "NDL-1187053-R0000022-R-5")
inv = json.loads((ROOT / "data/inventory/edo-nishiki.json").read_text(encoding="utf-8"))["toys"]
lane = {t["id"] for t in inv if t["lane"] == "cart"}
# 樋の板は竹筒（L-2）の部品と見て外した（雛形の冒頭）。外した物が増えたり減ったりしたら、ここで気づく。
assert lane - set(TOYS) == {"NDL-1187053-R0000004-L-3"}, lane

out = pathlib.Path(tempfile.mkdtemp())
count = 0
for sid in TOYS:
    data = hypotheses.load(sid)
    assert data["template"] == wc.ID and data["stage"] == "試作"
    assert 2 <= len(data["hypotheses"]) <= 3
    keys = [h["params"][wc.HYP_KEY] for h in data["hypotheses"]]
    assert len(set(keys)) == len(keys), (sid, "仮説は HYP_KEY の値で分ける")
    for h in data["hypotheses"]:
        with contextlib.redirect_stdout(io.StringIO()):
            rc = hypotheses.print_sheet(sid, h["id"], str(out / f"{sid}_{h['id']}"))
        assert rc == 0, (sid, h["id"], rc)
        assert (out / f"{sid}_{h['id']}.pdf").exists() and (out / f"{sid}_{h['id']}_tejun.pdf").exists()
        count += 1
assert count == 4

source = json.loads((ROOT / "data/sources/NDL-1187053-R0000019-L.json").read_text(encoding="utf-8"))


def floors(params):
    _, _, f = compose(wc.ID, params, source)
    return {(x.floor, x.where) for x in f}


cart = {"drive": "pull", "body": "cart"}
# 車が小さいと台の縁が床をこする
assert ("F5.wheel", "車") in floors({**cart, "wheel_d": 14})
# 前後の車が擦れ合う
assert ("F5.wheel", "車") in floors({**cart, "deck_length": 50, "axle_in": 10, "wheel_d": 34})
# 穴が縁の下端に近すぎて裂ける
assert ("F5.axle", "軸の穴") in floors({**cart, "axle_drop": 10, "skirt": 12, "wheel_d": 30})
# 穴が軸にきつすぎて回らない・広すぎて首を振る
assert ("F5.axle", "軸の穴") in floors({**cart, "axle_hole": 1.5})
assert ("F5.axle", "軸の穴") in floors({**cart, "axle_hole": 3.0})
# 俵: 短すぎる、坂の縁が低い
assert ("F5.roll", "俵") in floors({"drive": "slope", "body": "bale", "bale_length": 24, "bale_d": 30})
assert ("F5.roll", "坂") in floors({"drive": "slope", "body": "bale", "rail": 5})
# 範囲の外と、知らない遊び方
assert ("F5.range", "drive") in floors({"drive": "fly", "body": "cart"})
assert ("F5.range", "wheel_d") in floors({**cart, "wheel_d": 80})
# 既定の形は床を通る（落ちる値だけが落ちる事の対照）
assert not floors(cart) and not floors({"drive": "slope", "body": "bale"})

# 台帳の式（F7）: 車を大きくすると床との隙間が増える
assert values(wc.ID, {**cart, "wheel_d": 30})["ground_clear_mm"] > values(wc.ID, cart)["ground_clear_mm"]
print("ok", count)
