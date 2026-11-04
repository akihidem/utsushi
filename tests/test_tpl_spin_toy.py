"""雛形 spin_toy（線 spin: 風車・独楽・手車）の試験。線の契約（docs/process/template-contract.md）の完成の定義を確かめる。

1. 線の全部の玩具の全部の仮説の版 1 が、本物の道（hypotheses.print_sheet）で床を通って刷れる
2. 回らない・倒れる・釣り合わない形は床（check_physics）で落ちる。落ちる床の名前まで見る
置き場は一時の物にする。予想や版の記録が data/ に残ると、ほかの試験の前提が変わるため。
"""
import contextlib
import io
import json
import os
import pathlib
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from omochae import hypotheses  # noqa: E402  置き場の環境を先に決めてから読む
from omochae.compose import compose  # noqa: E402
from omochae.templates import spin_toy as T  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
inv = json.loads((ROOT / "data/inventory/edo-nishiki.json").read_text(encoding="utf-8"))
lane = [t["id"] for t in inv["toys"] if t.get("lane") == "spin"]
assert len(lane) == 6, lane

out_dir = pathlib.Path(tempfile.mkdtemp())
printed = 0
for sid in lane:
    data = hypotheses.load(sid)
    assert data["template"] == T.ID and data["stage"] == "試作", sid
    assert 2 <= len(data["hypotheses"]) <= 3, sid
    # 仮説は回し方（HYP_KEY）で分ける。同じ回し方の仮説が 2 つあると、紙で見分けられない。
    drives = [{**T.DEFAULTS, **h["params"]}[T.HYP_KEY] for h in data["hypotheses"]]
    assert len(set(drives)) == len(drives), (sid, drives)
    src = json.loads((ROOT / "data/sources" / f"{sid}.json").read_text(encoding="utf-8"))
    assert src["transcription"]["entries"] == [], "翻刻は人が写す欄で、線では空のまま（U-01）"
    for h in data["hypotheses"]:
        assert {e["certainty"] for e in h["evidence"]} <= {"観察", "推測", "計算", "二次資料"}, (sid, h["id"])
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            rc = hypotheses.print_sheet(sid, h["id"], str(out_dir / f"{sid}_{h['id']}"), version=1)
        assert rc == 0, (sid, h["id"], err.getvalue())
        assert (out_dir / f"{sid}_{h['id']}.pdf").exists() and (out_dir / f"{sid}_{h['id']}_tejun.pdf").exists()
        printed += 1
assert printed == 12, printed

src = json.loads((ROOT / "data/sources" / f"{lane[0]}.json").read_text(encoding="utf-8"))


def floors(params):
    _, _, f = compose(T.ID, params, src)
    return {(x.floor, x.where) for x in f}


# 床に落ちる値。どれも 1 つだけ変えて、狙いの床の名前で落ちる事を見る（別の理由で落ちたのを成功と数えない）。
assert floors({"blade_count": 10, "blade": 20, "arm_w": 3}) == {("F5.spin", "羽")}, "羽が多く大きいと、ひねった羽どうしが当たる"
assert floors({"blade_count": 12}) >= {("F5.spin", "羽の柄")}, "柄が多いと中心で重なる"
assert floors({"blade_angle": 60}) == {("F5.spin", "羽のひねり")}, "ひねりが深すぎると風を受け流す"
assert floors({"drive": "cup", "blade_angle": 60}) == set(), "受け皿に折る形はひねりを使わない"
assert floors({"shape": "cone", "look": "tetsudo", "drive": "twist", "cone_pieces": 1}) == {("F5.balance", "胴")}, "胴を 1 枚で巻くと糊代が片側に寄る"
assert T.balance_offset({**T.DEFAULTS, "shape": "cone", "cone_pieces": 2}) == 0
assert floors({"shape": "disc", "look": "koma", "drive": "palm", "axis_len": 40}) == {("F5.spin", "芯")}, "芯が短いと両手でもむ長さが無い"
assert floors({"shape": "disc", "look": "koma", "drive": "twist", "axis_len": 120}) == {("F5.spin", "芯")}, "芯が径に比べて長すぎると倒れる"
assert floors({"shape": "disc", "look": "koma", "drive": "twist", "axis_below": 20}) == {("F5.spin", "芯の先")}
assert floors({"shape": "yoyo", "look": "teguruma", "drive": "yoyo", "string_len": 1500, "hub_w": 2, "disc_d": 25}) == {("F5.spin", "紐")}, "芯の溝に巻けない長さの紐"
assert floors({"shape": "pinwheel", "look": "kanko", "wheels": 2, "hub_r": 5, "arm_len": 14, "arm_w": 3, "blade": 11, "drive": "beat", "striker_len": 30}) == {("F5.spin", "打ち木")}, "打ち木が深くかかると引っかかる"
assert floors({"shape": "disc", "drive": "pitch"}) == {("F5.range", "drive")}, "形に合わない回し方"
assert floors({"blade_count": 7.5}) == {("F5.range", "blade_count")}

# 台帳の式（F7）は形によらず同じ名前を返す。版の前後を同じ物差しで比べるため。
keys = {tuple(sorted(T.metrics({**T.DEFAULTS, **h["params"]}))) for sid in lane for h in hypotheses.load(sid)["hypotheses"]}
assert len(keys) == 1, keys
print("ok", printed)
