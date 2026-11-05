"""紙の見出し（本人の決定 11-05、#302 の案 A）。先に書かないと始められないように読める字を、本人が採った字に替える。

見る線:
- 試作の全部の案で、手順の紙と試した後の紙の見出しが、本人が採った字（一字も変えない。決定の文を文字列で見る）。前の字と「予想」の字が無い
- 変わるのは見出しの字だけ。前の字で組んだ紙と比べて、ほかの字・枠・線・位置が同じ（問いと枠が残る。仮説の文と札の順が変わらない。配置が動かない）
- 必須 2 種の前の組は前の字のまま（凍結の床。指紋そのものは tests/test_floor_pin.py が見る）。次の組（goraigo-v11・tora-v4）は採った字
- 例外は組の名前で持つ。雛形の前の組（FROZEN_SET）と食い違うと、この試験が名指しして落ちる

なぜ確かめを関数に分けて全部回すか: 直す前に落ちる所を 1 回の出力でそろえて見るため。本物の API は呼ばない。紙は組むだけで刷らない。
"""
import json

from omochae import hypotheses, instructions
from omochae.compose import TEMPLATES
from omochae.hypotheses import ROOT
from omochae.instructions import compose_after, compose_sheet

ADOPTED_BEFORE = "思った事（書かなくても作れます）"
ADOPTED_NEXT = "次はこれを変えて試す"
OLD_BEFORE = "作る前に"
OLD_NEXT = "次はこれを変えて試す（予想を書いてから）"


def words(layout):
    return [t.text for t in layout["texts"] if t.text]


def kept(layout, head):
    """見出しの箱を除いた、字・枠・線・位置の全部。見出しの箱は、位置と高さだけを別に返す（字の幅は字で変わる）。"""
    boxes = [(round(t.x, 3), round(t.y, 3), round(t.w, 3), round(t.h, 3), t.text, t.size) for t in layout["texts"] if t.text != head]
    found = [(round(t.x, 3), round(t.y, 3), round(t.h, 3)) for t in layout["texts"] if t.text == head]
    assert len(found) == 1, f"見出し「{head}」が {len(found)} 個"
    return boxes, layout["shapes"], found[0]


def with_old_heads(sheet_set, make):
    """同じ紙を前の字で組む（例外の表に一時だけ足す）。変わるのが見出しだけかを比べるため。"""
    table = instructions.FROZEN_HEADS
    table[sheet_set] = (OLD_BEFORE, OLD_NEXT)
    try:
        return make()
    finally:
        del table[sheet_set]


TRIAL, REQUIRED = [], []
for path in sorted((ROOT / "data/hypotheses").glob("*.json")):
    sid = path.stem
    data = hypotheses.load(sid)
    source = json.loads((ROOT / "data/sources" / f"{sid}.json").read_text(encoding="utf-8"))
    (REQUIRED if hypotheses.stage(sid) == "必須" else TRIAL).append((sid, data, source))
assert len(REQUIRED) == 2 and len(TRIAL) >= 80, (len(REQUIRED), len(TRIAL))


def plans(toys):
    for sid, data, source in toys:
        for h in data["hypotheses"]:
            if h.get("params") is not None:
                yield sid, source, h, h.get("template") or data.get("template", "slider_fan")


def trial_sheets_have_the_adopted_heads():
    n = 0
    for sid, source, h, tid in plans(TRIAL):
        layout, failures = compose_sheet(tid, h["params"], source, h["name"], h["how_it_moves"])
        assert not failures, (sid, h["id"], [f.line() for f in failures])
        got = words(layout)
        assert ADOPTED_BEFORE in got, (sid, h["id"], "手順の紙に採った見出しが無い")
        assert OLD_BEFORE not in got, (sid, h["id"], "手順の紙に前の見出しが残っている")
        # 前の字で組む比べは同じコードを通るので、両方に足された字は見えない。見出しのすぐ後が問いである事は、ここで直に見る。
        question = TEMPLATES[tid].measures({**TEMPLATES[tid].DEFAULTS, **h["params"]})["predict"]
        assert question.startswith(got[got.index(ADOPTED_BEFORE) + 1]), (sid, h["id"], "見出しのすぐ後が問いでない")
        n += 1
    assert n >= 160, n


def trial_after_sheets_have_the_adopted_head():
    for sid, data, source in TRIAL:
        sheet_set = TEMPLATES[data.get("template", "slider_fan")].SHEET_SET
        layout, failures = compose_after(source, data["toy"], data["after_try"], sheet_set=sheet_set)
        assert not failures, (sid, [f.line() for f in failures])
        got = words(layout)
        assert ADOPTED_NEXT in got, (sid, "試した後の紙に採った見出しが無い")
        assert not [w for w in got if "予想" in w], (sid, "試した後の紙に予想の字が残っている", [w for w in got if "予想" in w])
        assert data["after_try"]["contrasts"][0]["change"].startswith(got[got.index(ADOPTED_NEXT) + 1]), (sid, "見出しのすぐ後が変える条件でない")


def only_the_head_changes():
    for sid, source, h, tid in plans(TRIAL):
        make = lambda: compose_sheet(tid, h["params"], source, h["name"], h["how_it_moves"])
        new_boxes, new_shapes, new_head = kept(make()[0], ADOPTED_BEFORE)
        old_boxes, old_shapes, old_head = kept(with_old_heads(TEMPLATES[tid].SHEET_SET, make)[0], OLD_BEFORE)
        assert new_head == old_head, (sid, h["id"], "見出しの位置か行数が動いた", new_head, old_head)
        assert new_boxes == old_boxes and new_shapes == old_shapes, (sid, h["id"], "見出しのほかが変わった")
        assert any(s.get("tag") == "predict_box" for s in new_shapes), (sid, h["id"], "書く枠が無い")
    for sid, data, source in TRIAL:
        sheet_set = TEMPLATES[data.get("template", "slider_fan")].SHEET_SET
        make = lambda: compose_after(source, data["toy"], data["after_try"], sheet_set=sheet_set)
        new_boxes, new_shapes, new_head = kept(make()[0], ADOPTED_NEXT)
        old_boxes, old_shapes, old_head = kept(with_old_heads(sheet_set, make)[0], OLD_NEXT)
        assert new_head == old_head, (sid, "試した後の紙の見出しの位置か行数が動いた", new_head, old_head)
        assert new_boxes == old_boxes and new_shapes == old_shapes, (sid, "試した後の紙の見出しのほかが変わった")


def required_old_sets_keep_the_old_heads():
    for sid, source, h, tid in plans(REQUIRED):
        tpl = TEMPLATES[tid]
        now, tpl.SHEET_SET = tpl.SHEET_SET, tpl.FROZEN_SET
        try:
            got = words(compose_sheet(tid, h["params"], source, h["name"], h["how_it_moves"])[0])
        finally:
            tpl.SHEET_SET = now
        assert OLD_BEFORE in got and ADOPTED_BEFORE not in got, (sid, h["id"], "必須 2 種の前の組の手順の紙が変わった")
    for sid, data, source in REQUIRED:
        sheet_set = TEMPLATES[data.get("template", "slider_fan")].FROZEN_SET
        got = words(compose_after(source, data["toy"], data["after_try"], sheet_set=sheet_set)[0])
        assert OLD_NEXT in got and ADOPTED_NEXT not in got, (sid, "必須 2 種の前の組の試した後の紙が変わった")


def required_next_sets_have_the_adopted_heads():
    for sid, source, h, tid in plans(REQUIRED):
        got = words(compose_sheet(tid, h["params"], source, h["name"], h["how_it_moves"])[0])
        assert ADOPTED_BEFORE in got and OLD_BEFORE not in got, (sid, h["id"], "次の組の手順の紙に採った見出しが無い")
    for sid, data, source in REQUIRED:
        sheet_set = TEMPLATES[data.get("template", "slider_fan")].SHEET_SET
        got = words(compose_after(source, data["toy"], data["after_try"], sheet_set=sheet_set)[0])
        assert ADOPTED_NEXT in got and OLD_NEXT not in got, (sid, "次の組の試した後の紙に採った見出しが無い")


def exceptions_match_the_frozen_sets():
    # 例外の表は、控えを残す前の組の行だけ。今の組の行があると前の字で刷り、前の組の行が無いと指紋が変わる。
    frozen = {TEMPLATES["slider_fan"].FROZEN_SET, TEMPLATES["pivot_counterweight"].FROZEN_SET}
    assert set(instructions.FROZEN_HEADS) == frozen, ("例外の表と雛形の前の組が食い違う", sorted(instructions.FROZEN_HEADS), sorted(frozen))
    assert all(v == (OLD_BEFORE, OLD_NEXT) for v in instructions.FROZEN_HEADS.values()), "例外の字は前の字のまま"
    trial_sets = {TEMPLATES[tid].SHEET_SET for _, _, _, tid in plans(TRIAL)}
    assert not trial_sets & set(instructions.FROZEN_HEADS), "試作の玩具が必須 2 種の組を使っている"


def raising_a_set_drops_the_old_heads():
    # 負の対照: 組の名前を上げた形で組むと、前の字が外れて、採った字になる。
    tpl = TEMPLATES["slider_fan"]
    sid, source, h, tid = next(p for p in plans(REQUIRED) if p[3] == "slider_fan")
    saved = tpl.SHEET_SET
    tpl.SHEET_SET = "次の組の試し"
    try:
        got = words(compose_sheet(tid, h["params"], source, h["name"], h["how_it_moves"])[0])
    finally:
        tpl.SHEET_SET = saved
    assert ADOPTED_BEFORE in got and OLD_BEFORE not in got, "組を上げても前の字が残る"
    data = next(d for s, d, _ in REQUIRED if s == sid)
    got = words(compose_after(source, data["toy"], data["after_try"], sheet_set="次の組の試し")[0])
    assert ADOPTED_NEXT in got and OLD_NEXT not in got, "組を上げても試した後の紙に前の字が残る"


fails = []
for check in (trial_sheets_have_the_adopted_heads, trial_after_sheets_have_the_adopted_head, only_the_head_changes, required_old_sets_keep_the_old_heads,
              required_next_sets_have_the_adopted_heads, exceptions_match_the_frozen_sets, raising_a_set_drops_the_old_heads):
    try:
        check()
    except Exception as e:  # 表が無い直す前も、ほかの確かめを止めずに名前で出す
        fails.append(f"{check.__name__}: {type(e).__name__}: {e}")
assert not fails, "\n" + "\n".join(fails)
print("ok: 紙の見出し")
