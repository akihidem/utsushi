"""雛形 stick_prop（持ち物の玩具の線）の試験。線の全部の玩具の全部の仮説の版 1 が、本物の道（print_sheet）で刷れる事と、
組めない・持てない・動かない寸法が床に落ちる事を見る（docs/process/template-contract.md の完成の定義）。"""
import contextlib
import io
import json
import multiprocessing
import os
import pathlib
import tempfile

# 記録の置き場は一時の所にする。本物の記録（data/decisions など）を試験で汚さないため。
tmp = tempfile.mkdtemp()
os.environ["OMOCHAE_DATA"] = tmp

from omochae.__main__ import generate
from omochae.compose import compose
from omochae.hypotheses import print_sheet
from omochae.metrics import values
from omochae.templates import stick_prop as T

ROOT = pathlib.Path(__file__).resolve().parents[1]
inv = json.loads((ROOT / "data/inventory/edo-nishiki.json").read_text(encoding="utf-8"))
lane = [t for t in inv["toys"] if t.get("lane") == "prop"]
# 作らないと決めた件。理由は commit と返事に書く（刀と兜巾の後ろの飾りか結袈裟か割れていて、棒で持つ形の読みが立たない）。
LEFT_OUT = {"NDL-1187053-R0000005-R-3"}
made = [t for t in lane if t["id"] not in LEFT_OUT]
assert len(lane) == 17 and len(made) == 16, (len(lane), len(made))

def _print(job):
    sid, hid, out = job
    return print_sheet(sid, hid, out)


jobs = []
for t in made:
    sid = t["id"]
    data = json.loads((ROOT / "data/hypotheses" / f"{sid}.json").read_text(encoding="utf-8"))
    src = json.loads((ROOT / "data/sources" / f"{sid}.json").read_text(encoding="utf-8"))
    assert data["template"] == T.ID and data["stage"] == "試作" and data["toy"] == t["name_guess"], sid
    assert all(e.get("decided_by") or e.get("checked_by") for e in src["transcription"]["entries"]), "翻刻は人が写す欄で、線では空のまま（U-01）"  # 線（雛形の生成）は翻刻を書かない。入るのは人の決め（本人の決め 11-08「A にそろえる」の decided_by）か人が確かめた読みだけ
    hs = data["hypotheses"]
    assert 2 <= len(hs) <= 3 and len({h["params"][T.HYP_KEY] for h in hs}) == len(hs), (sid, "仮説は付け方で分ける")
    for h in hs:
        assert h["status"] == "untested" and h["evidence"] and h["against"] and h["to_measure"], (sid, h["id"])
        assert {e["certainty"] for e in h["evidence"]} <= {"観察", "推測", "計算", "二次資料"}, (sid, h["id"])
        assert set(values(T.ID, h["params"])) >= {"stick_in_mm", "grip_mm"}
        jobs.append((sid, h["id"], f"{tmp}/{sid}_{h['id']}"))
# 1 枚に 3 種の紙（型紙・手順・試した後）を刷るので、33 仮説を順に刷ると数分かかる。run.sh を重くしないよう、刷るのだけを並べる。
with multiprocessing.get_context("fork").Pool(4) as pool, contextlib.redirect_stdout(io.StringIO()):
    rcs = pool.map(_print, jobs)
for job, rc in zip(jobs, rcs):
    assert rc == 0, (job, rc)
    # 刷るのは型紙だけ（窓口の決定 推し A・11-06）。手順の紙と試した後の紙は刷る時に組まない（組む仕組みは凍結の床の控えが見る）
    assert pathlib.Path(f"{job[2]}.pdf").exists() and not any(pathlib.Path(f"{job[2]}{s}.pdf").exists() for s in ("_tejun", "_after")), job
printed = len(jobs)
assert not (ROOT / "data/hypotheses" / "NDL-1187053-R0000005-R-3.json").exists()
print(f"ok 刷れた {len(made)} 件 {printed} 仮説")

# 床に落ちる値。どれも 1 つの寸法だけを壊し、狙った床で落ちる事を見る。
src = json.loads((ROOT / "data/sources/NDL-1187053-R0000008-R-3.json").read_text(encoding="utf-8"))


def fails(params):
    _, _, f = compose(T.ID, params, src)
    return [x.floor + " " + x.where for x in f]


assert fails({"shape": "uchiwa_l", "hold": "glue", "size": 92}) == []
assert fails({"shape": "uchiwa_l", "hold": "nod"}) == ["F5.range hold"], "形に無い付け方は落とす"
assert fails({"shape": "uchiwa_l", "hold": "glue", "size": 30}) == ["F5.prop 竹串"], "貼る所が短いと振って抜ける"
assert fails({"shape": "uchiwa_l", "hold": "glue", "size": 92, "stick_len": 100}) == ["F5.prop 持つ所"]
assert "F5.prop 重心" in fails({"shape": "ame_tori", "hold": "nod", "size": 100, "weight_g": 0}), "重りが無いと首振りの鳥は戻らない"
assert fails({"shape": "ame_tori", "hold": "nod", "size": 100, "weight_g": 1.0}) == []
assert fails({"shape": "katana", "hold": "slide", "size": 170, "slide_gap": 0.5}) == ["F5.prop すき間"]
assert fails({"shape": "katana", "hold": "slide", "size": 170, "slide_gap": 8}) == ["F5.prop すき間"]
assert fails({"shape": "utsubo", "hold": "pocket", "size": 140, "pocket_depth": 50}) == ["F5.prop 袋"]
assert fails({"shape": "nobori", "hold": "turn", "size": 120, "loop_len": 12}) == ["F5.prop 輪の帯"]
assert fails({"shape": "harukoma", "hold": "wheel", "size": 100, "wheel_d": 15}) == ["F5.prop 車"]
assert fails({"shape": "andon", "hold": "glue", "size": 100}) == ["F5.print_area 行灯"], "A4 に入らない行灯は刷らない"
assert fails({"shape": "uchiwa_l", "hold": "glue", "size": 999})[0].startswith("F5.range"), "範囲の外は先に落とす"
# 本物の道でも落ちる（rc 3）。落ちた紙を正しい名前で残さない
bad = f"{tmp}/bad"
assert generate(T.ID, {"shape": "katana", "hold": "slide", "size": 170, "slide_gap": 0.5}, "NDL-1187053-R0000005-R", bad) == 3
assert not pathlib.Path(f"{bad}.pdf").exists()
# 刷った後の検査で落ちた紙も、正しい名前で残さない（場面 neg_marks_all と同じ形。PDF は .rejected.pdf へ移し、PNG は作らない）
bad = f"{tmp}/bad_marks"
assert generate("slider_fan", {}, "NDL-1187053-R0000005-L", bad, inject={"omit_marks": "all"}) == 3
assert not pathlib.Path(f"{bad}.pdf").exists() and not pathlib.Path(f"{bad}.png").exists() and pathlib.Path(f"{bad}.rejected.pdf").exists()
print("ok 床")
