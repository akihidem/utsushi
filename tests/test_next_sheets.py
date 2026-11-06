"""必須 2 種のうち虎の次の組（tora-v4、#115）。前の組 tora-v3 の紙と指紋は変えない（tests/test_floor_pin.py が見る）。御来迎は今の組 goraigo-v10 のまま
（次の組は本人の決定 11-06 で形を見直す。下から押し上げる形と内筒）。
虎の今の組は tora-v6 に上げた（tests/test_tora_v6.py）。tora-v4 は控えの組として刷れるので、この試験は雛形の組を tora-v4 に置いて、
tora-v3 との違いを前と同じに見る（v6 に上げても v4 の作りが変わらない事も見る）。

なぜ次の組か: 本人の答え（11-05）は、色の面を外にして折った。手順の「谷折り」のとおりに折ると、虎の胴は色の面が箱の内に入る。
本人の指示は「次の版で直し、今の版の紙と指紋は変えない」。次の組には、本人のレビューと作成動画の札から採った案も入る（型紙エンジン
paper-to-toy の PR #106 1f4f0b1 と同じ形と字。手順 4 の「線のとおり」と凡例の字だけは窓口が本人の委任で選んだ字）。

見る線:
- 胴の折り線は刷った面から見て山折り。前の組は谷折りのまま。ほかの部品の折り線は変わらない
- 手順の文の違いは、手順 4（線のとおり山折り）と、重りの腕の手順 8・9（EP-0011）だけ。手順の数と番号は変わらない
- 札の名（2 頭・3 首の帯・4 尾・5 腕）・胴の上の面の竹串の点の線・5 腕の粘土の高さの点の線・2 枚目の側面は y だけ裏返す（EP-0016）
- 用意する物: 道具にセロハンテープとカッター、竹串と粘土の置き所・丸い印は穴・4 尾だけ色の理由
- 凡例は刷った面から見た言い方。位置の印のある紙は「位置の印（切らない・折らない）」も。御来迎の紙と前の組の紙は前の字
- 粘土の玉の大きさの床: 軸の竹串にかかる浅い重りと、玉の下が底に当たる深い重りを落とす（先の 1 つだけを言う）
"""
import json

from shapely.geometry import LineString, box

from omochae import marks
from omochae.compose import LABEL_SIZE, LINE, TEMPLATES, compose
from omochae.floors import check_art
from omochae.hypotheses import ROOT
from omochae.instructions import compose_after, compose_sheet
from omochae.textfit import text_width

GORAIGO, TORA = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"
FAN, TIGER = TEMPLATES["slider_fan"], TEMPLATES["pivot_counterweight"]
BODY_OLD, BODY_NEW = "1 胴を破線で谷折りし、糊代で貼って箱にする。上の面は後で閉じる", "1 胴を線のとおり山折りし、糊代で貼って箱にする。上の面は後で閉じる"
ARM_OLD = ("5 重りの腕の穴にも竹串を通し、下の端に粘土を付ける。腕は 3 首の帯に貼る", "頭の傾きを見て、腕を貼る位置を決める")
ARM_NEW = ("5 重りの腕の上の穴にも竹串を通す。下の穴（点の線）の所に粘土を付ける。腕は 3 首の帯に添えて、テープで仮に留める（まだ貼らない）",
           "頭の傾きを見て腕の位置を決めてから、腕を 3 首の帯に貼る")
FOLD_NEW = ("谷折り（刷った面が内がわになる）", "山折り（刷った面が外がわになる）")
LEGEND_OLD = ("谷折り（手前にへこむ）", "山折り（手前に出る）")
MARK_LEGEND = "位置の印（切らない・折らない）"
TOOLS_NECK = "のり、はさみ、定規、セロハンテープ、カッター"


class old_set:
    """前の組の紙を組む（雛形は SHEET_SET で組を見分ける）。"""

    def __enter__(self):
        self.keep = TIGER.SHEET_SET
        TIGER.SHEET_SET = TIGER.FROZEN_SET

    def __exit__(self, *_):
        TIGER.SHEET_SET = self.keep


def load(sid):
    return (json.loads((ROOT / "data/hypotheses" / f"{sid}.json").read_text(encoding="utf-8")),
            json.loads((ROOT / "data/sources" / f"{sid}.json").read_text(encoding="utf-8")))


def plans():
    data, _ = load(TORA)
    return [(h["id"], {**TIGER.DEFAULTS, **h["params"]}) for h in data["hypotheses"]]


def part(p, key):
    return next(q for q in TIGER.parts(p) if q.key == key)


def words(layout):
    return [t.text for t in layout["texts"] if t.text]


# 1. 組の名前。前の組の名前は控えを刷る道として残す。御来迎は今の組のまま（前の組を持たない）。
# 虎の今の組は tora-v6 で、tora-v4 は控えの組。ここからは雛形の組を tora-v4 に置く（控えの組を刷る道と同じ）
assert (TIGER.SHEET_SET, TIGER.FROZEN_SET, TIGER.KEPT_SETS) == ("tora-v6", "tora-v3", ("tora-v3", "tora-v4")), TIGER.SHEET_SET
TIGER.SHEET_SET = "tora-v4"
assert FAN.SHEET_SET == "goraigo-v10" and not hasattr(FAN, "FROZEN_SET"), FAN.SHEET_SET
assert marks.FROZEN_SETS == {GORAIGO: "goraigo-v10"}, marks.FROZEN_SETS

# 2. 折り線: 胴が山折りになり、線の位置は前の組と同じ。ほかの部品の折り線は変わらない
for hid, p in plans():
    with old_set():
        old = {q.key: (q.valley, q.mountain) for q in TIGER.parts(p)}
    new = {q.key: (q.valley, q.mountain) for q in TIGER.parts(p)}
    assert len(new["body"][1]) == 10 and not new["body"][0] and new["body"][1] == old["body"][0] and not old["body"][1], (hid, "胴")
    assert {k: v for k, v in new.items() if k != "body"} == {k: v for k, v in old.items() if k != "body"}, (hid, "ほかの部品の折り線が変わった")

# 3. 手順の文: 違いは手順 4 と、首の形の手順 8・9 だけ。手順の数は変わらない
for hid, p in plans():
    new = TIGER.steps(p)
    with old_set():
        old = TIGER.steps(p)
    expect = [(BODY_OLD, BODY_NEW)] + (list(zip(ARM_OLD, ARM_NEW)) if p["mount"] == "neck" else [])
    assert len(new) == len(old), (hid, "手順の数が変わった")
    assert sorted((a, b) for a, b in zip(old, new) if a != b) == sorted(expect), (hid, [(a, b) for a, b in zip(old, new) if a != b])

# 4. 見出しと印の文: 次の組は本人が採った字（#302・#318）。前の組は前の字のまま。御来迎は前の字のまま
for sid in (GORAIGO, TORA):
    data, source = load(sid)
    h = next(x for x in data["hypotheses"] if x["id"] == data["sheet"])
    tid = h.get("template") or data.get("template", "slider_fan")
    now = "".join("".join(words(compose_sheet(tid, h["params"], source, h["name"], h["how_it_moves"])[0])).split())
    raised = sid == TORA
    assert ("思った事" in now) == raised and ("作る前に" in now) != raised, sid
    assert ("".join(marks.HYPOTHESIS.split()) in now) == raised and ("".join(marks.HYPOTHESIS_FROZEN.split()) in now) != raised, sid
    assert f"刷った組 {TEMPLATES[tid].SHEET_SET}" in words(compose(tid, h["params"], source)[1]), sid

# 5. 用意する物: 首の形は道具にセロハンテープとカッター、竹串と粘土の置き所・丸い印は穴・4 尾だけ色の理由。吊る形と前の組は前の字
for hid, p in plans():
    got = TIGER.materials(p)
    with old_set():
        was = TIGER.materials(p)
    assert was[1] == "のり、はさみ、定規", (hid, was)
    if p["mount"] == "neck":
        assert got[1] == TOOLS_NECK, (hid, got)
        assert got[2] == f"{was[2]}（胴の 2 つの穴・3 首の帯の穴・5 腕の上の穴に通す。胴の上の面の点の線の下を通る）", (hid, got[2])
        assert got[3].startswith(f"油粘土 {p['weight_g']:g}g（") and "点の線の所に付ける" in got[3], (hid, got[3])
        assert got[4] == "丸い印は穴（竹串の先であける）。4 尾は外に見えるので色を刷り、3 首の帯と 5 腕は胴の中に入るので白", (hid, got)
    else:
        assert got == was, (hid, got, was)

# 6. 札（EP-0016）: 2〜5 番に名。3 首の帯の札は真ん中の谷折りの線が字の「3」と「首」の間を通る。前の組は番号だけ。虎の胴の札の字に縞がかからない
p = {**TIGER.DEFAULTS, "mount": "neck"}
assert {q.key: q.label for q in TIGER.parts(p)} == {"body": "1 胴", "head": "2 頭", "strip": "3 首の帯", "tail": "4 尾", "drop": "5 腕"}
with old_set():
    assert {q.key: q.label for q in TIGER.parts(p)} == {"body": "1 胴", "head": "2", "strip": "3", "tail": "4", "drop": "5"}
strip = part(p, "strip")
x0 = strip.label_xy[0]
gap0, gap1 = x0 + text_width("3", LABEL_SIZE), x0 + text_width("3 ", LABEL_SIZE)
assert gap0 <= p["strip_width"] <= gap1, ("3 首の帯の札の字が折り線にかかる", x0, gap0, gap1)
assert TIGER.LABEL_SIZE == LABEL_SIZE


def label_hits_stripe(q):
    body = part(q, "body")
    x, y = body.label_xy
    label = box(x, y, x + text_width(body.label, LABEL_SIZE), y + LABEL_SIZE * LINE)
    return any(a["kind"] == "line" and LineString(a["pts"]).buffer(a.get("sw", 0) / 2).intersects(label) for a in body.art)


for mount in ("neck", "hang"):
    q = {**TIGER.DEFAULTS, "mount": mount}
    assert not label_hits_stripe(q), (mount, "札の字に縞がかかる")
    with old_set():
        assert label_hits_stripe(q), (mount, "前の組の札の位置が変わった（または当たりの見方が空振り）")

# 7. 印（EP-0011・EP-0016）: 5 腕に軸の穴から weight_below_axle 下の穴と、その高さの点の線 2 本（穴の左右）。胴の上の面に竹串の点の線。
# 糸で下げる形は、玉の下が底から 3mm 以上離れる寸法の時だけ（既定の寸法では玉 約 15mm が底に当たるので出ない）。前の組には印が無い
arm = part(p, "drop")
assert [h[:2] for h in arm.holes] == [(4, 4), (4, 4 + p["weight_below_axle"])], arm.holes
assert [a["kind"] for a in arm.art] == ["mark", "mark"] and all(y == arm.holes[1][1] for a in arm.art for _, y in a["pts"]), arm.art
body = part(p, "body")
axle = [a for a in body.art if a["kind"] == "mark" and a.get("mark") == "axle"]
assert len(axle) == 1 and all(x == body.holes[0][0] for x, _ in axle[0]["pts"]) and check_art([body]) == [], axle
assert TIGER.hang_thread_mm(p) is None and not any("糸で下げる" in w for w in TIGER.steps(p) + TIGER.materials(p))
deep = {**p, "axle_height": 60, "body_height": 66, "weight_below_axle": 28}
L = TIGER.hang_thread_mm(deep)
assert L is not None and f"玉の上は穴から {TIGER.HANG_MIN}〜{L}mm" in TIGER.steps(deep)[7], (L, TIGER.steps(deep)[7])
with old_set():
    assert len(part(p, "drop").holes) == 1 and not part(p, "drop").art and not [a for a in part(p, "body").art if a["kind"] == "mark"]

# 8. 2 枚目の側面は y だけ裏返し、2 枚とも虎の鼻先が軸の穴の側（前の端）に来る。前の組は 180° 回したまま（頭が後ろの端）
nose = min(range(len(TIGER._BODY)), key=lambda i: TIGER._BODY[i][0])
for mount in ("neck", "hang"):
    q = {**TIGER.DEFAULTS, "mount": mount, **({"axle_height": 50} if mount == "hang" else {})}
    for raised in (True, False):
        if raised:
            sides = [a["pts"][nose][0] for a in part(q, "body").art if a["kind"] == "poly" and a.get("fill") == TIGER.TIGER and a.get("stroke") == TIGER.STRIPE]
        else:
            with old_set():
                sides = [a["pts"][nose][0] for a in part(q, "body").art if a["kind"] == "poly" and a.get("fill") == TIGER.TIGER and a.get("stroke") == TIGER.STRIPE]
        front = [abs(n - q["body_height"]) < abs(n - (q["body_height"] + q["body_length"])) for n in sides]
        assert front == ([True, True] if raised else [True, False]), (mount, raised, sides)

# 9. 凡例: 虎の次の組の型紙は刷った面から見た言い方と、位置の印の行。前の組と御来迎の型紙は前の字で、位置の印の行も無い。全部の案が頁に収まる
data, source = load(TORA)
for h in data["hypotheses"]:
    pattern = compose("pivot_counterweight", h["params"], source)
    assert not pattern[2], (h["id"], [f.line() for f in pattern[2]])
    got = words(pattern[1])
    assert all(w in got for w in FOLD_NEW) and not any(w in got for w in LEGEND_OLD), (h["id"], "型紙の凡例")
    with old_set():
        got = words(compose("pivot_counterweight", h["params"], source)[1])
        assert all(w in got for w in LEGEND_OLD) and MARK_LEGEND not in got, (h["id"], "前の組の凡例が変わった")
assert MARK_LEGEND in words(compose("pivot_counterweight", {"mount": "neck"}, source)[1])
gdata, gsource = load(GORAIGO)
gh = next(x for x in gdata["hypotheses"] if x["id"] == gdata["sheet"])
gwords = words(compose("slider_fan", gh["params"], gsource)[1])
assert all(w in gwords for w in LEGEND_OLD) and MARK_LEGEND not in gwords, "御来迎の凡例が変わった"

# 10. 粘土の玉の大きさの床: 軸の竹串にかかる浅い重りと、玉の下が底に当たる深い重りを落とす。両方起きる寸法では先の 1 つだけ。重りの別の落ちがあれば言わない
assert any("軸の竹串にかかる" in f.message for f in TIGER.check_physics({**p, "weight_below_axle": 5}))
assert any("玉の下が底に当たる" in f.message for f in TIGER.check_physics({**p, "weight_below_axle": 36}))
both = {**p, "axle_height": 15, "weight_below_axle": 5, "weight_g": 15, "weight_behind": 0}
ball = [f for f in TIGER.check_physics(both) if "粘土の玉" in f.message]
assert len(ball) == 1 and "軸の竹串にかかる" in ball[0].message, [f.line() for f in TIGER.check_physics(both)]
above = [f for f in TIGER.check_physics({**p, "weight_below_axle": -20}) if f.where == "重り"]
assert above and not any("粘土の玉" in f.message for f in above), [f.line() for f in above]
assert not TIGER.check_physics(p)

# 11. 試した後の紙は、組の札のほかは前の組と同じ字（見出しは 4 で見た）
after = words(compose_after(source, data["toy"], data["after_try"], sheet_set=TIGER.SHEET_SET)[0])
assert f"刷った組 {TIGER.SHEET_SET}" in after

print("ok 虎の次の組 tora-v4。折り線・手順の文・見出し・印の文・用意する物・札・印・側面の向き・凡例・粘土の玉の床（御来迎は今の組のまま）")
