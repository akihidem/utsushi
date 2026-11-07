"""記録の組ごとの欄（たたき台 sheet_by_set・寸法 params_by_set・出さない字 hide_by_set）と、雛形の控えの組の並び（compose.kept_sets）（#115）。

なぜ要るか: 必須 2 種の次の組（御来迎 goraigo-v14・虎 tora-v6）は、たたき台・寸法・出す字が前の組と違う。前の組の紙は変えない決まりなので、
記録の 1 つの欄を書き換えず、組ごとの欄に足す。2 つの組を 2 本の PR で別に足すので、読み口を先に 1 本で入れる（統括の決め 11-06）。
欄を書いた本物の記録は、御来迎の goraigo-v14 の分（たたき台 H-C・H-C の寸法は型紙エンジンの見本 examples/goraigo_v14.json・
糸の前提の共通の字 5 つを出さない）と、虎の H-A の tora-v7 の寸法（型紙エンジンの見本 examples/tora_v7.json）だけ。
前の組の紙が変わらない事は tests/test_floor_pin.py の指紋で見る。

見る線:
- 組ごとの欄を持たない記録は、load が前と同じ物を返す（人が採った仮説を重ねるだけ）。御来迎は今の組の分だけが替わり、
  虎は H-A の寸法だけが今の組の分に替わる
- 欄を書いた記録は、雛形の今の組の分だけが効く。前の組に置くと記録の sheet・params・字のまま
- 出さない字は外すだけで、字を変えず、元の記録も書き換えない。字で持つので、元の字を直すと外れなくなる（黙って別の字は消えない）
- 控えの組の並びは古い順で、前の字で刷る最初の組（FROZEN_SET）を含み、今の組を含まない
"""
import copy
import json
import os
import pathlib
import tempfile

tmp = tempfile.mkdtemp()
os.environ["OMOCHAE_DATA"] = tmp  # 人が採った仮説（data/loop）を機械ごとに混ぜない

from omochae import hypotheses
from omochae.compose import TEMPLATES, kept_sets
from omochae.loop import overlay

ROOT = pathlib.Path(__file__).resolve().parents[1]
TIGER, FAN = TEMPLATES["pivot_counterweight"], TEMPLATES["slider_fan"]
FIELDS = ("sheet_by_set", "params_by_set", "hide_by_set")

# 1. 組ごとの欄を持たない記録は、load が前と同じ（人が採った仮説を重ねるだけ）。たたき台は記録の sheet のまま。
# 欄を書いたのは御来迎の goraigo-v14 の分と、虎の H-A の tora-v7 の寸法だけ。load は、御来迎のたたき台・H-C の寸法・出さない字の 3 つと、
# 虎の H-A の寸法だけを替える（虎のたたき台・字・ほかの仮説は記録のまま）
GORAIGO = "NDL-1187053-R0000005-L"
V14 = {"push_part": "rise", "tube_side": 26, "tube_height": 130, "pusher_side": 24.5, "pusher_height": 57.5, "push_amount": 60,
       "base_side": 24.0, "fold_count": 44, "fold_width": 4, "fold_height": 57.2, "figure_w": 10.4, "figure_h": 27.7}
TORA = "NDL-1187053-R0000014-R"
V7 = {"mount": "neck", "axle_height": 32, "head_w": 36, "weight_below_axle": 20, "leg_height": 10, "body_round": 8, "head_sides": 2,
      "neck_length": 23, "clay_back": 2.5, "axle_back": 9, "weight_behind": 0, "fit_check": 1}
for path in sorted((ROOT / "data/hypotheses").glob("*.json")):
    raw = json.loads(path.read_text(encoding="utf-8"))
    got = hypotheses.load(raw["source_id"])
    want = overlay(copy.deepcopy(raw))
    if raw["source_id"] == GORAIGO:
        assert raw["sheet"] == "H-A" and raw["sheet_by_set"] == {"goraigo-v14": "H-C"} and hypotheses.sheet_id(got) == "H-C"
        assert [h["id"] for h in raw["hypotheses"] if "params_by_set" in h] == ["H-C"], "御来迎の寸法の欄は H-C だけ"
        assert sorted(raw["hide_by_set"]) == ["goraigo-v14"]
        for h in want["hypotheses"]:
            if h["id"] == "H-C":
                h["params"] = V14
        want = hypotheses.without_hidden(want, "goraigo-v14")
    elif raw["source_id"] == TORA:
        assert hypotheses.sheet_id(got) == raw.get("sheet") and not any(k in raw for k in FIELDS), path.name
        assert [h["id"] for h in raw["hypotheses"] if "params_by_set" in h] == ["H-A"], "虎の欄は H-A だけ"
        assert raw["hypotheses"][0]["params_by_set"] == {"tora-v7": V7}, "型紙エンジンの見本 examples/tora_v7.json と同じ寸法"
        want["hypotheses"][0]["params"] = V7
    else:
        assert not any(k in raw for k in FIELDS) and not any("params_by_set" in h for h in raw["hypotheses"]), (path.name, "欄を書いたのは御来迎と虎だけ")
        assert hypotheses.sheet_id(got) == raw.get("sheet"), path.name
    assert got == want, (path.name, "組ごとの欄で load が変わった所が、今の組の分のほかにある")

# 2. 組ごとの欄を書いた記録（代わりの記録を別の置き場に置く。repo の data は書き換えない）
now, old = TIGER.SHEET_SET, TIGER.FROZEN_SET
assert now != old
fake = {
    "source_id": "TEST-BY-SET", "toy": "試しの玩具", "template": "pivot_counterweight", "sheet": "H-A", "sheet_by_set": {now: "H-B"},
    "questions": ["残る問い", "外す問い"],
    "after_try": {"contrasts": [{"change": "残す比べる事", "watch": "見る"}, {"change": "外す比べる事", "watch": "見る"}], "card": ["残す札", "外す札"]},
    "analogy": {"text": "たとえ", "related": ["残す関わり", "外す関わり"]},
    "hide_by_set": {now: {"questions": ["外す問い"], "after_try.contrasts": ["外す比べる事"], "after_try.card": ["外す札"], "analogy.related": ["外す関わり"]}},
    "hypotheses": [
        {"id": "H-A", "name": "前のたたき台", "params": {"mount": "neck"}},
        {"id": "H-B", "name": "次のたたき台", "params": {"mount": "hang"}, "params_by_set": {now: {"mount": "neck", "axle_height": 32}}},
    ],
}
want_kept = {"questions": ["残る問い"], "after_try.contrasts": ["残す比べる事"], "after_try.card": ["残す札"], "analogy.related": ["残す関わり"]}


def texts(d):
    return {"questions": d["questions"], "after_try.contrasts": [c["change"] for c in d["after_try"]["contrasts"]],
            "after_try.card": d["after_try"]["card"], "analogy.related": d["analogy"]["related"]}


folder = pathlib.Path(tmp) / "repo"
(folder / "data/hypotheses").mkdir(parents=True)
(folder / "data/hypotheses/TEST-BY-SET.json").write_text(json.dumps(fake, ensure_ascii=False), encoding="utf-8")
keep_root = hypotheses.ROOT
hypotheses.ROOT = folder
try:
    # 2a. 今の組: たたき台は H-B、H-B の寸法は今の組の分、出さない字は外れる。H-A の寸法は記録のまま
    got = hypotheses.load("TEST-BY-SET")
    assert hypotheses.current_set(got) == now and hypotheses.sheet_id(got) == "H-B", hypotheses.sheet_id(got)
    assert hypotheses.sheet_of("TEST-BY-SET")["id"] == "H-B"
    by = {h["id"]: h["params"] for h in got["hypotheses"]}
    assert by == {"H-A": {"mount": "neck"}, "H-B": {"mount": "neck", "axle_height": 32}}, by
    assert texts(got) == want_kept, texts(got)
    assert got["analogy"]["text"] == "たとえ" and got["after_try"]["contrasts"][0]["watch"] == "見る", "外す欄のほかは変えない"
    # 2b. 前の組に置くと、記録の sheet・params・字のまま
    TIGER.SHEET_SET = old
    try:
        was = hypotheses.load("TEST-BY-SET")
        was_sheet = hypotheses.sheet_id(was), hypotheses.sheet_of("TEST-BY-SET")["id"]  # 組を省くと雛形の今の組（ここでは前の組）
    finally:
        TIGER.SHEET_SET = now
    assert was_sheet == ("H-A", "H-A"), was_sheet
    assert {h["id"]: h["params"] for h in was["hypotheses"]} == {"H-A": {"mount": "neck"}, "H-B": {"mount": "hang"}}
    assert texts(was) == texts(fake), "前の組では字を外さない"
finally:
    hypotheses.ROOT = keep_root

# 3. 組を名指しして引く（凍結の床が記録を直に読んで組ごとに組む道）。元の記録は書き換えない
before = copy.deepcopy(fake)
assert hypotheses.sheet_id(fake, old) == "H-A" and hypotheses.sheet_id(fake, now) == "H-B" and hypotheses.sheet_id(fake, "tora-v99") == "H-A"
assert hypotheses.params_for(fake["hypotheses"][1], now) == {"mount": "neck", "axle_height": 32}
assert hypotheses.params_for(fake["hypotheses"][1], old) == {"mount": "hang"} and hypotheses.params_for(fake["hypotheses"][0], now) == {"mount": "neck"}
assert texts(hypotheses.without_hidden(fake, now)) == want_kept and hypotheses.without_hidden(fake, old) is fake
assert fake == before, "出さない字を外した時に、元の記録が書き換わった"
# 字で持つので、元の字を直すと外れない（黙って別の字は消えない）
moved = {**fake, "questions": ["残る問い", "外す問い（直した）"]}
assert hypotheses.without_hidden(moved, now)["questions"] == ["残る問い", "外す問い（直した）"]

# 4. 控えの組の並び: 古い順で、前の字の組を含み、今の組を含まない。前の組の無い雛形は空
for tpl in TEMPLATES.values():
    sets = kept_sets(tpl)
    assert tpl.SHEET_SET not in sets and len(set(sets)) == len(sets), (tpl.ID, sets)
    if hasattr(tpl, "FROZEN_SET"):
        assert sets[0] == tpl.FROZEN_SET, (tpl.ID, sets)
    else:
        assert sets == (), (tpl.ID, sets)
assert kept_sets(TIGER) == ("tora-v3", "tora-v4") and kept_sets(FAN) == ("goraigo-v10",), (kept_sets(TIGER), kept_sets(FAN))
# 凍結の床の控えは、控えの組の全部と今の組の紙を持つ
pin = json.loads((ROOT / "tests/floor_pin.json").read_text(encoding="utf-8"))
for tpl in (TIGER, FAN):
    for s in kept_sets(tpl) + (tpl.SHEET_SET,):
        assert any(n.startswith(f"{s}/") for n in pin["papers"]), (s, "凍結の床の控えに、その組の紙が無い")

print("ok 組ごとの欄（たたき台・寸法・出さない字）と控えの組の並び。欄の無い記録は load が前と同じ・虎は H-A の寸法だけが v7 の分")
