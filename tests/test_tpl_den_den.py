"""雛形 den_den（音の玩具の線、11-04）: 線の全部の玩具の全部の仮説の版 1 が、本物の道（hypotheses.print_sheet）で床を通って刷れる事と、
組めない・鳴らない形が床で落ちる事を見る。刷った紙は一時の置き場に出し、本物の置き場を汚さない。"""
import io
import json
import os
import pathlib
import tempfile
from contextlib import redirect_stderr, redirect_stdout

tmp = tempfile.mkdtemp()
os.environ["OMOCHAE_DATA"] = tmp

from omochae import hypotheses  # noqa: E402
from omochae.compose import TEMPLATES, compose  # noqa: E402
from omochae.metrics import values  # noqa: E402
from omochae.templates import den_den  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
inv = json.loads((ROOT / "data/inventory/edo-nishiki.json").read_text(encoding="utf-8"))["toys"]
lane = [t["id"] for t in inv if t.get("lane") == "drum"]
made = [sid for sid in lane if (ROOT / "data/hypotheses" / f"{sid}.json").exists()]
# 作らないと決めた件。胴と皮の形に乗らない笛・琴、付属品の読みが強い物（理由は線の返事に書いた）。数が黙って減らないように名指しする。
LEFT_OUT = {"NDL-1187053-R0000009-L-3", "NDL-1187053-R0000015-L-4", "NDL-1187053-R0000024-R-2", "NDL-1187053-R0000026-R", "NDL-1187053-R0000027-L-2"}
assert set(lane) == set(made) | LEFT_OUT and not set(made) & LEFT_OUT, (lane, made)
assert len(made) == 5

# 1. 全部の玩具の全部の仮説の版 1 が刷れる
count = 0
for sid in made:
    data = hypotheses.load(sid)
    assert data["template"] == "den_den" and data["stage"] == "試作", sid
    assert data["written_by"].startswith("Claude Code のセッション"), sid
    assert 2 <= len(data["hypotheses"]) <= 3, sid
    keys = [h["params"]["play"] for h in data["hypotheses"]]
    assert len(set(keys)) == len(keys), (sid, "仮説は鳴らし方（HYP_KEY）で分ける")
    src = json.loads((ROOT / "data/sources" / f"{sid}.json").read_text(encoding="utf-8"))
    assert all(e.get("decided_by") or e.get("checked_by") for e in src["transcription"]["entries"]), (sid, "翻刻は人が確かめるか決めるまで空")  # 線（雛形の生成）は翻刻を書かない。入るのは人の決め（本人の決め 11-08「A にそろえる」の decided_by）か人が確かめた読みだけ
    for h in data["hypotheses"]:
        out = f"{tmp}/{sid}_{h['id']}"
        err = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(err):
            rc = hypotheses.print_sheet(sid, h["id"], out)
        assert rc == 0, (sid, h["id"], err.getvalue())
        # 刷るのは型紙だけ（窓口の決定 推し A・11-06）。手順の紙と試した後の紙は刷る時に組まない（組む仕組みは凍結の床の控えが見る）
        assert pathlib.Path(f"{out}.pdf").exists() and not any(pathlib.Path(f"{out}{s}.pdf").exists() for s in ("_tejun", "_after")), (sid, h["id"])
        assert all(isinstance(v, float) for v in values("den_den", h["params"]).values())
        count += 1
assert count == 10, count

# 2. 床に落ちる値は落ちる。狙いの検査の名前と、どこで落ちたかまで見る（別の理由で落ちたのを成功と見ないため）。
src = json.loads((ROOT / "data/sources" / f"{made[0]}.json").read_text(encoding="utf-8"))


def fails(params):
    _, _, f = compose("den_den", params, src)
    return {(x.floor, x.where) for x in f}


assert fails({"play": "twist"}) == set()
assert fails({"play": "twist", "thread_len": 12}) == {("F5.drum", "糸")}, "糸が短く玉が皮に届かない"
assert fails({"play": "twist", "thread_len": 80}) == {("F5.drum", "糸")}, "糸が長く玉が皮の縁を越える"
assert fails({"play": "twist", "thread_len": 16}) == {("F5.drum", "糸")}, "届いても皮の縁ぎりぎりを打つ"
assert fails({"play": "twist", "handle_len": 100}) == {("F5.drum", "柄")}, "柄が胴を通ると握る所が残らない"
assert fails({"play": "twist", "drums": 2, "head_d": 40, "handle_len": 130}) == {("F5.drum", "柄")}, "胴 2 つでは柄が足りない"
assert fails({"play": "shake", "band_w": 11, "bead_d": 9}) == {("F5.drum", "中の玉")}, "中の玉が動けない"
assert fails({"play": "tap", "band_w": 10, "handle_d": 4}) == {("F5.drum", "帯")}, "柄の穴の前後が狭く裂ける"
assert fails({"play": "twist", "form": "stand", "handle_len": 100}) == {("F5.drum", "柄")}, "台に立てた胴は回せない"
assert fails({"play": "tap", "form": "stand", "band_w": 60, "base_l": 50, "handle_len": 100}) == {("F5.drum", "台")}, "胴が台より大きいと倒れる"
assert fails({"play": "tap", "head_d": 60}) == {("F5.range", "head_d")}, "皮の径の範囲（帯が A4 に入らない）"
assert fails({"play": "tap", "drums": 1.5}) == {("F5.range", "drums")}
assert fails({"play": "blow"}) == {("F5.range", "play")}, "笛はこの雛形の鳴らし方に無い"
# 皮の径の上限は帯が A4 の印字域に入る所にした。上限と一番長い糊代の帯が、配置の床（印字域）も通る事を見る。
_, _, f = compose("den_den", {"play": "tap", "head_d": 56, "glue": 12}, src)
assert not f, [x.line() for x in f]
# 配置の床も働く: 負の対照で部品を印字域の外へ動かすと落ちる。
_, _, f = compose("den_den", {"play": "tap"}, src, inject={"move_part": {"name": "band1", "x": 60, "y": 20}})
assert "F5.print_area" in {x.floor for x in f}, [x.line() for x in f]

# 3. 式（F7）は刷る物と同じ数を見る。玉が打つ点は、糸の長さで皮の中心をまたいで動く。
p = {**den_den.DEFAULTS, "thread_len": 20}
q = {**den_den.DEFAULTS, "thread_len": 40}
assert den_den.hit_offset(p) > 0 > den_den.hit_offset(q), "短い糸は手前の縁寄り、長い糸は中心の向こうを打つ"
assert den_den.ALLOWED <= set(den_den.RANGES) and "den_den" in TEMPLATES
print("ok", count)
