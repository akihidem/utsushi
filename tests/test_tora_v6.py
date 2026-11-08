"""虎の今の組 tora-v7（#115）。型紙エンジン paper-to-toy の v7（#138）の雛形を写した _tora_v6 で刷る。v5 と v6 は刷らずに飛ばした（ファイルと試験の名は v6 の写しの時のまま）。

前の組（tora-v3・tora-v4）の紙と指紋は変えない（tests/test_floor_pin.py。tora-v4 の作りは tests/test_next_sheets.py が前と同じに見る）。
寸法は記録の H-A の組ごとの寸法（エンジンの見本 examples/tora_v6.json と同じ。tests/test_by_set.py）。

見る線:
- 組の名前と控えの組の並び。組の番号が 6 から作りを写しに替え、v4 に置くと前の作りに戻る（関数ごとに替わる）
- エンジンと違う所は 2 つだけ: 手順 4 の「線のとおり山折り」（窓口が本人の委任で選んだ字）と、紙の行の 4 つの名前（#295）
- たたき台の紙（首の形・脚 4 本・角を落とした胴・両面の頭）が検査に通り、頁の凡例は次の組の字と位置の印の行
- 前の組の作りでは v6・v7 からの寸法（脚・角・顔の数・重りの穴のずれ・軸と前の壁の間・当たりの検査）を落とす（刷る紙に効かない寸法を通さない）
- 丸い切り抜きの床（部品の外・折り線にかかる・印にかかる）。3D の組み立ては型紙エンジンの JSON で描く
"""
import json

from omochae import assembly, assembly_json, hypotheses, marks
from omochae.compose import FOLD_WORDS, TEMPLATES, compose
from omochae.floors import check_art, check_holes
from omochae.templates import _tora_v6
from omochae.templates._paper import paper_name

TORA = "NDL-1187053-R0000014-R"
TIGER = TEMPLATES["pivot_counterweight"]
MARK_LEGEND = "位置の印（切らない・折らない）"
source = json.loads((hypotheses.ROOT / "data/sources" / f"{TORA}.json").read_text(encoding="utf-8"))
h = hypotheses.sheet_of(TORA)
p = {**TIGER.DEFAULTS, **h["params"]}


class at_set:
    """雛形の組を置き換えて組む（控えの組を刷る道と同じ）。"""

    def __init__(self, name):
        self.name = name

    def __enter__(self):
        self.keep, TIGER.SHEET_SET = TIGER.SHEET_SET, self.name

    def __exit__(self, *_):
        TIGER.SHEET_SET = self.keep


def words(layout):
    return [t.text for t in layout["texts"] if t.text]


# 1. 組の名前と並び。御来迎も今の組 goraigo-v14 に上げたので、凍結の組の印の表は空（前の組の紙は、呼ぶ側が前の印の文を渡す）
# 今の組は tora-v8（v7 と同じ部品で、テープを使わない版・本人の決め 11-08。v6 は当たり 2 つを v7 で直したので、刷らずに飛ばした。窓口の決定 2026-11-07）。試験の名は v6 の写しの時のまま
assert (TIGER.SHEET_SET, TIGER.set_no(), TIGER.FROZEN_SET, TIGER.KEPT_SETS) == ("tora-v8", 8, "tora-v3", ("tora-v3", "tora-v4", "tora-v7"))
assert marks.FROZEN_SETS == {}, marks.FROZEN_SETS
assert h["id"] == "H-A" and {k: p[k] for k in ("leg_height", "body_round", "head_sides")} == {"leg_height": 10, "body_round": 8, "head_sides": 2}

# 2. 組の番号が 6 から写しの関数に替わり、v4 に置くと前の作りに戻る。DEFAULTS と RANGES は写しと同じ（どちらで引いても同じ寸法）
assert TIGER.DEFAULTS == _tora_v6.DEFAULTS and TIGER.RANGES == _tora_v6.RANGES
assert TIGER.steps(p) == _tora_v6.steps(p) and TIGER.materials(p) == _tora_v6.materials(p) and TIGER.check_physics(p) == []
neck = {**TIGER.DEFAULTS, "mount": "neck"}
with at_set("tora-v4"):
    old_steps, old_parts = TIGER.steps(neck), {q.key for q in TIGER.parts(neck)}
assert old_steps != _tora_v6.steps(neck) and "1 胴の前の壁の四角い穴を切る（カッターは大人がする）" in old_steps
assert old_parts == {"body", "head", "strip", "tail", "drop"}

# 3. エンジンと違う所は 2 つ: 手順 4 の字と、紙の行の 4 つの名前（寸法と重さの計算は paper_gsm のまま）
steps = TIGER.steps(p)
assert steps[3] == "1 胴を線のとおり山折りし、糊代で貼って箱にする。上の面は後で閉じる" and not any("破線で山折り" in s for s in steps), steps[3]
assert TIGER.materials(p)[0] == "画用紙くらいの厚さの紙を 1 枚" and paper_name(p["paper_gsm"]) == "画用紙くらいの厚さの紙"
assert all(r["material"] == paper_name(p["paper_gsm"]) for r in TIGER.bom(p) if r["key"] not in ("axle", "weight"))
assert TIGER.materials({**p, "paper_gsm": 80})[0] == "コピー用紙くらいの厚さの紙を 1 枚"
assert not any("g/m²" in str(m) or "見込み" in str(m) for m in TIGER.materials(p))

# 4. たたき台の紙: 首の形・脚 4 本（6〜9）・角を落とした胴・両面の頭・丸い首の穴。検査に通り、凡例は次の組の字と位置の印の行
by = {q.key: q for q in TIGER.parts(p)}
assert [by[k].label for k in ("body", "head", "strip", "tail", "drop", "leg1", "leg2", "leg3", "leg4")] == ["1 胴", "2 頭", "3 首の帯", "4 尾", "5 重りの腕", "6 脚", "7 脚", "8 脚", "9 脚"]
assert len(by["body"].round_cuts) == 1 and not by["body"].cuts and len(by["head"].mountain) == 1, (by["body"].round_cuts, by["head"].mountain)
_, layout, failures = compose("pivot_counterweight", h["params"], source)
assert layout is not None and not failures, [f.line() for f in failures]
got = words(layout)
assert all(w in got for w in FOLD_WORDS) and MARK_LEGEND in got and "刷った組 tora-v8" in got, got
# 手順は 12 段（脚を貼る段を、上の面を閉じる前に足した。エンジンと同じ）
assert len(steps) == 12 and steps[9].startswith("6〜9 脚を") and steps[11].startswith("4 尾の糊代を山折りし"), steps

# 5. 前の組の作りは v6・v7 からの寸法を読まないので、既定のほかの値を落とす。今の組では通る。顔の数は整数（エンジンの床）
for k, v in (("leg_height", 10), ("body_round", 8), ("head_sides", 2)):
    with at_set("tora-v4"):
        assert [f.where for f in TIGER.check_range({"mount": "neck", k: v})] == [k], k
        assert TIGER.check_range({"mount": "neck", k: TIGER.NEXT_DEFAULTS[k]}) == [], k
    assert TIGER.check_range({"mount": "neck", k: v}) == [], k
assert [f.where for f in TIGER.check_range({"mount": "neck", "head_sides": 1.5})] == ["head_sides"]
assert any("頭を両面" in f.message for f in TIGER.check_physics({**TIGER.DEFAULTS, "mount": "hang", "axle_height": 50, "head_sides": 2}))

# 6. 丸い切り抜きの床: 部品の外に出る・折り線か糊代にかかる・位置の印にかかる。どれも落ち、たたき台の紙は通る
body = by["body"]
assert check_holes([body]) == [] and check_art([body]) == []
x, y, r = body.round_cuts[0]
body.round_cuts = [(-1.0, y, r)]
assert [f.line() for f in check_holes([body])] and "外に出ている" in check_holes([body])[0].message
fold_x = body.mountain[0][0][0]  # 上の面の端の山折りの線（x = 胴の高さ）
body.round_cuts = [(fold_x, y, r)]
assert any("折り線か糊代にかかる" in f.message for f in check_holes([body])), [f.line() for f in check_holes([body])]
axle = next(a for a in body.art if a.get("mark") == "axle")
mx, my = axle["pts"][0]
body.round_cuts = [(mx, my + 1, 2.0)]
assert any("位置の印が中の切り込みにかかり" in f.message for f in check_art([body])), [f.line() for f in check_art([body])]

# 7. 3D の組み立ては、型紙エンジンが出した今の組の JSON（data/kumitate/tora-v8.json）で描く（assembly_json。形の確かめは test_tora_v7_3d）。
#    控えの組 tora-v4 では、前と同じにサイトが自分で組む
got = assembly.assemble(TORA)
assert isinstance(got, assembly_json.Shown) and got.failures == [], got and [f.line() for f in got.failures]
with at_set("tora-v4"):
    old = assembly.assemble(TORA)
    assert old is not None and not isinstance(old, assembly_json.Shown)

print("ok 虎の今の組 tora-v8。組の替わり・エンジンと違う 2 つ・たたき台の紙・前の組の寸法の床・丸い切り抜きの床・3D はエンジンの JSON")
