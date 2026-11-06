"""必須 2 種の次の組（goraigo-v11・tora-v4、#115）。前の組の紙と指紋は変えない（tests/test_floor_pin.py が見る）。

なぜ次の組か: 本人の答え（11-05）は、御来迎の外筒を「色がついている所が外を向くよう折った」。手順の「谷折り」のとおりに折ると、
色の面が内に入る。虎の胴も同じ形で、絵は箱の 6 面とも刷った面の側にある。本人の指示は「次の版で直し、今の版の紙と指紋は変えない」。

見る線:
- 外筒と胴の折り線は、刷った面から見て山折り。前の組は谷折りのまま
- 手順の文の違いは、1 語と、本人が決めた文だけ（内筒・土台・最後の動きの手順。一字も変えない）。手順の紙の絵の見出しと矢じりも同じ向きにする
- 次の組にまとめた直しが入る: 紙の見出し（#302）、本人が採ったやさしい言葉の印の文（#318）、用意する物の竹串とカッター（#294、本人の確認 11-06）
- 紙の字（#295）は本人の確認待ちなので、次の組にも入れない
- 文と条件はエンジン（paper-to-toy の e189dc6）と同じ
- 紙の差は見込んだ所だけ。ほかの字・線・位置は前の組と同じ
"""
import json

from shapely.geometry import LineString, box

from omochae import instructions, marks
from omochae.compose import LABEL_SIZE, LINE, TEMPLATES, compose
from omochae.floors import check_art
from omochae.hypotheses import ROOT
from omochae.instructions import compose_after, compose_sheet, compose_teacher
from omochae.textfit import text_width

GORAIGO, TORA = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"
FAN, TIGER = TEMPLATES["slider_fan"], TEMPLATES["pivot_counterweight"]
TUBE_OLD, TUBE_NEW = "1 外筒を色の境で谷折りし、糊代で貼って角筒にする", "1 外筒を色の境で山折りし、糊代で貼って角筒にする"
# 新しい文は本人の決定（11-06）。一字も変えない
INNER_OLD, INNER_NEW = "2 内筒も同じように角筒にする", "2 内筒は破線で谷折りし、糊代で貼って角筒にする"
BASE_OLD, BASE_NEW = "2 土台も同じように角筒にし、割り箸の先を下から差し込んで貼る", "2 土台は破線で谷折りし、糊代で貼って角筒にし、割り箸の先を下から差し込んで貼る"
PUSH = "竹串の端を溝に沿って上に押し上げると、4 扇が 1 外筒の口から出て、蛇腹が開く"
# 「線のとおり」は、窓口が本人の委任（2026-11-06）でカード 002247 の推しを選んだ字。山折りの線は凡例では一点鎖線なので「破線で」と合わない
BODY_OLD, BODY_NEW = "1 胴を破線で谷折りし、糊代で貼って箱にする。上の面は後で閉じる", "1 胴を線のとおり山折りし、糊代で貼って箱にする。上の面は後で閉じる"
# 凡例の字（同じ委任で選んだ推し）。型紙の凡例と手順の紙の矢じりの見本を、刷った面から見た 1 通りの言い方にそろえる
FOLD_NEW = ("谷折り（刷った面が内がわになる）", "山折り（刷った面が外がわになる）")
LEGEND_OLD, ARROW_OLD = ("谷折り（手前にへこむ）", "山折り（手前に出る）"), ("谷折り（手前へ）", "山折り（向こうへ）")
PICTURE_OLD, PICTURE_NEW = "まず筒を 1 つ作る（色の境で谷折り）", "まず筒を 1 つ作る（色の境で山折り）"
# 作成動画の札から採った案（EP-0011・EP-0012。作る側が採り、型紙エンジンの issue/tora-v4 d1e5ba1・issue/goraigo-v11 50afc27 と同じ字にした。虎は本人のレビューから採った案 EP-0016 も同じ形で入れた。
# 本人の方針 11-06 で事前の人の確かめは無く、刷った紙を本人が見る）。手順の数と番号は変わらない
ARM_OLD = ("5 重りの腕の穴にも竹串を通し、下の端に粘土を付ける。腕は 3 首の帯に貼る", "頭の傾きを見て、腕を貼る位置を決める")
ARM_NEW = ("5 重りの腕の上の穴にも竹串を通す。下の穴（点の線）の所に粘土を付ける。腕は 3 首の帯に添えて、テープで仮に留める（まだ貼らない）",
           "頭の傾きを見て腕の位置を決めてから、腕を 3 首の帯に貼る")
# 御来迎の作成動画の案（EP-0012: 開く糸・溝の矢印・足の帯）は、本人のレビュー（11-06「糸なしでやります」）で取り下げ、エンジンも外した（fae4887）。
# 代わりに、筒を外すと扇が開く形（lift・EP-0017）を次の組の別の形として足した。今の仮説（H-A〜H-E）の形は変わらない
SKEWER = "のり、はさみ、定規、竹串（穴あけ）"
CUTTER = "のり、はさみ、定規、セロハンテープ、カッター"  # 虎の首の形は腕をテープで仮に留める（EP-0011）


class old_set:
    """前の組の紙を組む（雛形は SHEET_SET で組を見分ける）。"""

    def __init__(self, tpl):
        self.tpl = tpl

    def __enter__(self):
        self.keep = self.tpl.SHEET_SET
        self.tpl.SHEET_SET = self.tpl.FROZEN_SET

    def __exit__(self, *_):
        self.tpl.SHEET_SET = self.keep


def load(sid):
    return (json.loads((ROOT / "data/hypotheses" / f"{sid}.json").read_text(encoding="utf-8")),
            json.loads((ROOT / "data/sources" / f"{sid}.json").read_text(encoding="utf-8")))


def plans(sid, tpl):
    data, _ = load(sid)
    return [(h["id"], {**tpl.DEFAULTS, **h["params"]}) for h in data["hypotheses"]]


def part(tpl, p, key):
    return next(q for q in tpl.parts(p) if q.key == key)


def words(layout):
    return [t.text for t in layout["texts"] if t.text]


# 1. 組の名前。前の組の名前は控えを刷る道として残す
assert (FAN.SHEET_SET, FAN.FROZEN_SET) == ("goraigo-v11", "goraigo-v10"), FAN.SHEET_SET
assert (TIGER.SHEET_SET, TIGER.FROZEN_SET) == ("tora-v4", "tora-v3"), TIGER.SHEET_SET

# 2. 折り線: 外筒と扇の台（御来迎）と胴（虎）が山折りになり、線の位置は前の組と同じ。ほかの部品は変わらない
# 扇の台は、真ん中の面（扇の足を貼る印のある面）を上にして蓋をする。谷折りだと印が下を向く（3D の組み立てで見つかった。11-04 の写真 p09 は印が上）
for sid, tpl, keys in ((GORAIGO, FAN, {"tube": 4, "base": 4}), (TORA, TIGER, {"body": 10})):
    for hid, p in plans(sid, tpl):
        with old_set(tpl):
            old = {q.key: (q.valley, q.mountain) for q in tpl.parts(p)}
        new = {q.key: (q.valley, q.mountain) for q in tpl.parts(p)}
        for key, count in keys.items():
            assert len(new[key][1]) == count and not new[key][0], (sid, hid, key, "山折りでない", len(new[key][1]), len(new[key][0]))
            assert len(old[key][0]) == count and not old[key][1], (sid, hid, key, "前の組が変わった")
            assert new[key][1] == old[key][0], (sid, hid, key, "線の位置が動いた")
        assert {k: v for k, v in new.items() if k not in keys} == {k: v for k, v in old.items() if k not in keys}, (sid, hid, "ほかの部品の折り線が変わった")

# 3. 手順の文: 違いは 1 語と、本人が決めた文だけ。つまみの形は最後に 1 つ増える（前の手順の番号はずれない）
for sid, tpl, want in ((GORAIGO, FAN, (TUBE_OLD, TUBE_NEW)), (TORA, TIGER, (BODY_OLD, BODY_NEW))):
    for hid, p in plans(sid, tpl):
        new = tpl.steps(p)
        with old_set(tpl):
            old = tpl.steps(p)
        expect = [want]
        if sid == TORA and p["mount"] == "neck":
            expect += list(zip(ARM_OLD, ARM_NEW))
        if sid == GORAIGO and p["push_part"] in ("tab", "tube"):
            expect.append((INNER_OLD, INNER_NEW))
        if sid == GORAIGO and p["push_part"] == "stick":
            expect.append((BASE_OLD, BASE_NEW))
        added = [PUSH] if sid == GORAIGO and p["push_part"] == "tab" else []
        assert new[len(old):] == added, (sid, hid, "増えた手順が見込みと違う", new[len(old):])
        assert sorted((a, b) for a, b in zip(old, new) if a != b) == sorted(expect), (sid, hid, [(a, b) for a, b in zip(old, new) if a != b])

# 4. 手順の紙の絵: 見出しと矢じりも同じ向き。矢じりの見本（谷 1・山 1）のほかに、筒の矢じりが 1 つある
_, source = load(GORAIGO)
data, _ = load(GORAIGO)
h = next(x for x in data["hypotheses"] if x["id"] == data["sheet"])


def heads(layout):
    fills = [s["fill"] for s in layout["shapes"] if s["kind"] == "poly"]
    return fills.count(instructions.VALLEY_HEAD), fills.count(instructions.MOUNTAIN_HEAD)


sheet, failures = compose_sheet("slider_fan", h["params"], source, h["name"], h["how_it_moves"])
assert not failures, [f.line() for f in failures]
assert PICTURE_NEW in words(sheet) and PICTURE_OLD not in words(sheet) and f"3. {TUBE_NEW}" in words(sheet)
assert heads(sheet) == (1, 2), ("筒の矢じりが山でない", heads(sheet))
with old_set(FAN):
    before, failures = compose_sheet("slider_fan", h["params"], source, h["name"], h["how_it_moves"])
assert not failures and PICTURE_OLD in words(before) and PICTURE_NEW not in words(before) and heads(before) == (2, 1), heads(before)

# 5. 見出し: 次の組は本人が採った字（#302）。前の組は前の字のまま
for sid, tpl in ((GORAIGO, FAN), (TORA, TIGER)):
    data, source = load(sid)
    h = next(x for x in data["hypotheses"] if x["id"] == data["sheet"])
    tid = h.get("template") or data.get("template", "slider_fan")
    now = words(compose_sheet(tid, h["params"], source, h["name"], h["how_it_moves"])[0])
    after = words(compose_after(source, data["toy"], data["after_try"], sheet_set=tpl.SHEET_SET)[0])
    assert instructions.BEFORE_HEAD in now and "作る前に" not in now, sid
    assert instructions.NEXT_HEAD in after and not [w for w in after if "予想" in w], sid
    with old_set(tpl):
        then = words(compose_sheet(tid, h["params"], source, h["name"], h["how_it_moves"])[0])
    then_after = words(compose_after(source, data["toy"], data["after_try"], sheet_set=tpl.FROZEN_SET)[0])
    assert "作る前に" in then and instructions.BEFORE_HEAD not in then, sid
    assert "次はこれを変えて試す（予想を書いてから）" in then_after, sid
    # 組の札は、紙ごとに今の組の名前
    label = f"刷った組 {tpl.SHEET_SET}"
    assert label in now and label in after, sid
    assert label in words(compose_teacher(source, data["toy"], sheet_set=tpl.SHEET_SET)[0]), sid
    assert label in words(compose(tid, h["params"], source)[1]), sid

# 印の文: 次の組は本人が採ったやさしい言葉の文。前の組の文（呼ぶ側が渡す）は出ない
for sid in (GORAIGO, TORA):
    data, source = load(sid)
    h = next(x for x in data["hypotheses"] if x["id"] == data["sheet"])
    tid = h.get("template") or data.get("template", "slider_fan")
    for layout in (compose(tid, h["params"], source)[1], compose_sheet(tid, h["params"], source, h["name"], h["how_it_moves"])[0],
                   compose_after(source, data["toy"], data["after_try"])[0]):
        flat = "".join("".join(words(layout)).split())
        assert "".join(marks.HYPOTHESIS.split()) in flat and "".join(marks.HYPOTHESIS_FROZEN.split()) not in flat, sid

# 6. 用意する物: 穴があって竹串の行が無い形に竹串（穴あけ）、胴に切り抜きのある虎の形にカッター。たたき台の御来迎 A は竹串の行があるので変わらない。紙の字（#295）は入れない
for sid, tpl, adds in ((GORAIGO, FAN, lambda hid, p: SKEWER if hid in ("H-B", "H-C", "H-D") else None), (TORA, TIGER, lambda hid, p: CUTTER if p["mount"] == "neck" else None)):
    for hid, p in plans(sid, tpl):
        got = tpl.materials(p)
        with old_set(tpl):
            was = tpl.materials(p)
        add = adds(hid, p)
        assert "のり、はさみ、定規" in was, (sid, hid, "前の組の道具の行が変わった", was)
        want = [add if m == "のり、はさみ、定規" and add else m for m in was]
        if sid == TORA and p["mount"] == "neck":
            # 竹串と粘土の置き所・丸い印は穴・4 尾だけ色がある理由を字で書く（EP-0016）。既定の寸法では糸で下げる形は出ない
            want = [f"{m}（胴の 2 つの穴・3 首の帯の穴・5 腕の上の穴に通す。胴の上の面の点の線の下を通る）" if m.startswith("竹串") else m for m in want]
            want = [f"油粘土 {p['weight_g']:g}g（5 腕の下の穴の、点の線の所に付ける）" if m.startswith("油粘土") else m for m in want]
            want.append("丸い印は穴（竹串の先であける）。4 尾は外に見えるので色を刷り、3 首の帯と 5 腕は胴の中に入るので白")
        assert got == want, (sid, hid, got, want)

# 用意する物の条件はエンジンと同じ結果（部品に穴があって竹串の行が無い・胴に切り抜きがある）。雛形は部品を組まずに形の値で決めるので、部品と照らす
for push in ("tab", "tube", "stick"):
    for hub in ("axle", "rim"):
        p = {**FAN.DEFAULTS, "push_part": push, "hub": hub}
        want = any(q.holes for q in FAN.parts(p)) and not any("竹串" in r["material"] for r in FAN.bom(p))
        assert ("竹串（穴あけ）" in FAN.materials(p)[1]) == want, (push, hub)
for mount in ("neck", "hang"):
    p = {**TIGER.DEFAULTS, "mount": mount}
    assert ("カッター" in TIGER.materials(p)[1]) == any(q.cuts for q in TIGER.parts(p)), mount

# 虎の胴の札の字に縞がかからない（首の形と吊る形。字は変えず、札の位置を動かす）。前の組は紙を変えないので、かかったまま
def label_hits_stripe(tpl, p):
    body = part(tpl, p, "body")
    x, y = body.label_xy
    label = box(x, y, x + text_width(body.label, LABEL_SIZE), y + LABEL_SIZE * LINE)
    return any(a["kind"] == "line" and LineString(a["pts"]).buffer(a.get("sw", 0) / 2).intersects(label) for a in body.art)


for mount in ("neck", "hang"):
    p = {**TIGER.DEFAULTS, "mount": mount}
    assert not label_hits_stripe(TIGER, p), (mount, "札の字に縞がかかる")
    with old_set(TIGER):
        assert label_hits_stripe(TIGER, p), (mount, "前の組の札の位置が変わった（または当たりの見方が空振り）")
    assert part(TIGER, p, "body").label == "1 胴", mount

# 7. 紙の差は見込んだ所だけ（たたき台の型紙と手順の紙）。位置・線・絵は前の組と同じ。御来迎の手順の紙は手順が 1 つ増えるので、下の物は 1 行分ずれる
for sid, tpl, changed in ((GORAIGO, FAN, {TUBE_OLD, TUBE_NEW, INNER_OLD, INNER_NEW, PICTURE_OLD, PICTURE_NEW}), (TORA, TIGER, {BODY_OLD, BODY_NEW})):
    data, source = load(sid)
    source = {**source, "hypothesis_mark": marks.HYPOTHESIS_FROZEN}  # 印の文は行の数が違うので、同じ文で比べる（文は上の節で見た）
    h = next(x for x in data["hypotheses"] if x["id"] == data["sheet"])
    tid = h.get("template") or data.get("template", "slider_fan")

    q_now = {**tpl.DEFAULTS, **h["params"]}
    with old_set(tpl):
        mats = tpl.materials(q_now)
    mats += tpl.materials(q_now)

    def boxes(layout):
        """組の札・印の文・見出し・見込んだ文を除いた、字の箱の全部。"""
        out = []
        for t in layout["texts"]:
            if not t.text or t.text.startswith(("刷った組", "仮説", "作る前に", "思った事", "・のり", "1 胴", "・たこ糸", "・竹串", "・油粘土", "・丸い印")):
                continue
            if any(t.text in m for m in mats):  # 用意する物の行の折り返し（字は 6 で見た）
                continue
            # 次の組で増えた物（位置の印の凡例・虎の札の名。EP-0011・EP-0016）は 10 で見る
            if t.text in ("位置の印（切らない・折らない）", "2", "3", "4", "5", "2 頭", "3 首の帯", "3 帯", "4 尾", "5 腕"):
                continue
            if t.text in FOLD_NEW + LEGEND_OLD + ARROW_OLD + ("切る", "糊代"):  # 凡例の字は位置も変わる（字が長く、行を送る）。字は 9 で見る
                continue
            out.append((round(t.x, 3), round(t.y, 3), t.text if not any(c in t.text for c in changed) else "(見込んだ文)"))
        return out

    new_sheet = compose_sheet(tid, h["params"], source, h["name"], h["how_it_moves"])[0]
    new_pattern = compose(tid, h["params"], source)[1]
    with old_set(tpl):
        old_sheet = compose_sheet(tid, h["params"], source, h["name"], h["how_it_moves"])[0]
        old_pattern = compose(tid, h["params"], source)[1]
    # 手順の紙: 組み方の文（「組み方」から「遊び方」の前まで）は、折り返しの行が増えるので行の並びでは比べず、組み方の文そのものと比べる。
    # ほかの字は字も字の順も同じ（縦の位置は、組み方の行が増える分ずれるので比べない）
    def outside_steps(layout):
        rows = [(round(t.x, 3), t.text) for t in layout["texts"] if t.text]
        i = next(k for k, r in enumerate(rows) if r[1] == "組み方")
        j = next(k for k, r in enumerate(rows) if r[1] == "遊び方")
        return [r for r in rows[:i + 1] + rows[j:] if not r[1].startswith(("刷った組", "仮説", "作る前に", "思った事")) and r[1] not in FOLD_NEW + ARROW_OLD + (PICTURE_OLD, PICTURE_NEW)]  # 絵の見出しと矢じりの見本の字は 4 と 9 で見た
    assert outside_steps(new_sheet) == outside_steps(old_sheet), (sid, "手順の紙の字の差が見込みと違う")
    rows = [t.text for t in new_sheet["texts"] if t.text]
    printed = "".join(rows[rows.index("組み方") + 1:rows.index("遊び方")])
    assert printed == "".join(f"{i}. {w}" for i, w in enumerate(tpl.steps({**tpl.DEFAULTS, **h["params"]}), 1)), (sid, "組み方の文が手順と違う")
    if tpl is FAN:
        assert [t.text for t in new_sheet["texts"] if t.text and t.text.startswith("13.")] == [f"13. {PUSH}"], "手順 13 が刷られていない"
    # 凡例が長くなり（御来迎は 2 行）、位置の印の行が増えるので、下の物差しの説明は縦にずれる。字と横の位置は同じ
    strip = lambda rows: [(x, text) for x, _, text in rows]
    assert strip(boxes(new_pattern)) == strip(boxes(old_pattern)), (sid, "型紙の字の差が見込みと違う")
    # 部品は動かない。次の組で変わるのは、虎の 5 腕（下の穴と点の線が増える）と胴の絵（10 で見る）だけ
    # 虎の胴の 2 枚目の側面の絵は y だけ裏返す（EP-0016）ので、胴の絵は 10 で見る
    seen = lambda layout: [(q.key, q.x, q.y, q.outline, q.glue, q.holes, [a for a in q.art if a["kind"] != "mark"] if not (tpl is TIGER and q.key == "body") else None)
                           for q in layout["parts"] if q.key != "band"]
    old_seen = seen(old_pattern)
    new_seen = [(k, x, y, o, g, (hs[:1] if k == "drop" else hs), a) for k, x, y, o, g, hs, a in seen(new_pattern)]
    assert new_seen == old_seen, (sid, "部品が動いた")
    # 線や絵の種類と大きさ。矢じりの塗りと縦の位置のほかは同じ（虎は位置まで同じ）。「直した点」の表は頁の残りの分だけ行を引くので、御来迎は行の数を比べない
    # 組み方の文が伸びて行が増える（御来迎は手順 13 と帯・開く糸、虎は重りの腕の文）ので、両方とも縦の位置と「直した点」の行の数は比べない
    drop = {"fill", "y", "y1", "y2", "pts"}
    fill = lambda shapes: [{k: v for k, v in s.items() if k not in drop} for s in shapes]
    new_lines, old_lines = fill(new_sheet["shapes"]), fill(old_sheet["shapes"])
    assert len(old_lines) - len(new_lines) <= 3, (sid, "手順の紙の線が減りすぎた", len(old_lines), len(new_lines))
    old_lines = old_lines[:len(new_lines)]
    assert new_lines == old_lines, (sid, "手順の紙の線や絵の形が変わった")

# 8. 版 2 の紙: 遊び方の文が伸びても、頁に入る。書く欄の間を詰めるだけで、字と枠は残る（次の組は印の文が 2 行で手順も増えたので、数 mm 溢れて版 2 を刷れなくなった）
data, source = load(GORAIGO)
h = next(x for x in data["hypotheses"] if x["id"] == data["sheet"])
LONG = "。前の版から変えた所: fold_width 9→8.6、fold_count 22→24、pusher_height 15→18、push_amount 66→60"
wide, failures = compose_sheet("slider_fan", h["params"], source, h["name"], h["how_it_moves"])
assert not failures
narrow, failures = compose_sheet("slider_fan", h["params"], source, f"{h['name']} 版 2・根拠 R-0009、R-0010", h["how_it_moves"] + LONG)
assert not failures, [f.line() for f in failures]
for q in instructions.QUESTIONS:
    assert q in words(narrow), q
assert any(s.get("tag") == "predict_box" and s["h"] == instructions.PREDICT_H for s in narrow["shapes"]), "書く枠の大きさが変わった"
assert any(t.text == "直した点（部品・変えた事・結果）" for t in narrow["texts"]) and sum(1 for s in narrow["shapes"] if s["kind"] == "rect" and s.get("h") == instructions.FIX_ROW) == 3, "直した点の表が無い"
# 入る紙は詰めない（前の組の指紋と、今の組の 1 版の紙の字の間は今までどおり）
question_y = [t.y for t in wide["texts"] if t.text in instructions.QUESTIONS]
assert round(question_y[1] - question_y[0], 3) == round(question_y[2] - question_y[1], 3) and question_y[1] - question_y[0] > instructions.ANSWER_GAP, question_y

# 9. 凡例: 次の組は型紙の凡例と手順の紙の矢じりの見本が同じ字。前の組（凍結の床）と、FROZEN_SET を持たないほかの雛形は前の字のまま。
# 字が長くなっても、全部の案の型紙と手順の紙が頁に収まる（検査の失敗が無い）
for sid, tpl in ((GORAIGO, FAN), (TORA, TIGER)):
    data, source = load(sid)
    tid = data.get("template", "slider_fan")
    for h in data["hypotheses"]:
        t = h.get("template") or tid
        pattern = compose(t, h["params"], source)
        assert not pattern[2], (sid, h["id"], [f.line() for f in pattern[2]])
        assert all(w in words(pattern[1]) for w in FOLD_NEW) and not any(w in words(pattern[1]) for w in LEGEND_OLD), (sid, h["id"], "型紙の凡例")
        with old_set(tpl):
            assert all(w in words(compose(t, h["params"], source)[1]) for w in LEGEND_OLD), (sid, h["id"], "前の組の凡例が変わった")
    h = next(x for x in data["hypotheses"] if x["id"] == data["sheet"])
    sheet, failures = compose_sheet(tid, h["params"], source, h["name"], h["how_it_moves"])
    assert not failures, (sid, [f.line() for f in failures])
    if tpl is FAN:  # 矢じりの見本は御来迎の手順の紙だけにある
        assert all(w in words(sheet) for w in FOLD_NEW) and not any(w in words(sheet) for w in ARROW_OLD), "手順の紙の矢じりの見本"
        with old_set(tpl):
            assert all(w in words(compose_sheet(tid, h["params"], source, h["name"], h["how_it_moves"])[0]) for w in ARROW_OLD), "前の組の矢じりの見本が変わった"
other = TEMPLATES["wheel_cart"]
assert not hasattr(other, "FROZEN_SET")
wsrc = {**load(GORAIGO)[1], "toy": "試し"}
assert all(w in words(compose("wheel_cart", dict(other.DEFAULTS), wsrc)[1]) for w in LEGEND_OLD), "ほかの雛形の凡例が変わった"

# 10. 作成動画の札から採った案（EP-0011・EP-0012）。型紙エンジンと同じ形
# 虎: 首の形の 5 腕に、軸の穴から weight_below_axle 下の穴と、それを囲む点の丸（位置の印）。糸で下げる形は、玉の下が底から 3mm 以上離れる寸法の時だけ
p = {**TIGER.DEFAULTS, "mount": "neck"}
arm = part(TIGER, p, "drop")
assert [h[:2] for h in arm.holes] == [(4, 4), (4, 4 + p["weight_below_axle"])], arm.holes
# 粘土の高さの点の線は、穴の左右の 2 本で、穴の高さにある（EP-0016 で丸から替えた。丸は「赤い斑点」に見えた）
assert [a["kind"] for a in arm.art] == ["mark", "mark"] and all(y == arm.holes[1][1] for a in arm.art for _, y in a["pts"]), arm.art
assert TIGER.hang_thread_mm(p) is None, "既定の寸法（玉 約 15mm）で糸で下げる形が出た"
assert not any("糸で下げる" in w for w in TIGER.steps(p) + TIGER.materials(p))
deep = {**p, "axle_height": 60, "body_height": 66, "weight_below_axle": 28}  # 玉の下が底から離れる寸法
L = TIGER.hang_thread_mm(deep)
assert L is not None and L >= TIGER.HANG_MIN and f"玉の上は穴から {TIGER.HANG_MIN}〜{L}mm" in TIGER.steps(deep)[7] and "たこ糸" in TIGER.materials(deep)[3], (L, TIGER.steps(deep)[7])
with old_set(TIGER):
    assert len(part(TIGER, p, "drop").holes) == 1 and not part(TIGER, p, "drop").art and TIGER.hang_thread_mm(deep) is None
# EP-0016: 胴の 2 枚目の側面は y だけ裏返し、2 枚とも虎の鼻先が軸の穴の側（前の端）に来る。前の組は 180° 回したまま（頭が後ろの端）
nose = min(range(len(TIGER._BODY)), key=lambda i: TIGER._BODY[i][0])
for mount in ("neck", "hang"):
    q = {**TIGER.DEFAULTS, "mount": mount, **({"axle_height": 50} if mount == "hang" else {})}
    for now in (True, False):
        def sides():
            body = part(TIGER, q, "body")
            return body, [a["pts"][nose][0] for a in body.art if a["kind"] == "poly" and a.get("fill") == TIGER.TIGER and a.get("stroke") == TIGER.STRIPE]
        if now:
            body, noses = sides()
        else:
            with old_set(TIGER):
                body, noses = sides()
        H, L = q["body_height"], q["body_length"]
        front = [abs(n - H) < abs(n - (H + L)) for n in noses]
        assert len(noses) == 2 and (front == [True, True] if now else front == [True, False]), (mount, now, noses)
    assert not compose("pivot_counterweight", q, load(TORA)[1])[2], mount
# 2〜5 番の名（前の組は番号だけ）、胴の上の面の軸の竹串の点の線（2 つの軸の穴と同じ x）、用意する物の置き所の字
assert {x.key: x.label for x in TIGER.parts(p)} == {"body": "1 胴", "head": "2 頭", "strip": "3 首の帯", "tail": "4 尾", "drop": "5 腕"}
with old_set(TIGER):
    assert {x.key: x.label for x in TIGER.parts(p)} == {"body": "1 胴", "head": "2", "strip": "3", "tail": "4", "drop": "5"}
    assert not [a for a in part(TIGER, p, "body").art if a["kind"] == "mark"]
body = part(TIGER, p, "body")
axle = [a for a in body.art if a["kind"] == "mark" and a.get("mark") == "axle"]
assert len(axle) == 1 and all(x == body.holes[0][0] for x, _ in axle[0]["pts"]), axle
assert check_art([body]) == [], [f.line() for f in check_art([body])]
# 粘土の玉の大きさの床: 軸の竹串にかかる浅い重りと、玉の下が底に当たる深い重りを落とす（前の組でも同じ玉なので組で分けない）
assert any("軸の竹串にかかる" in f.line() for f in TIGER.check_physics({**p, "weight_below_axle": 5}))
assert any("玉の下が底に当たる" in f.line() for f in TIGER.check_physics({**p, "weight_below_axle": 36}))
assert not TIGER.check_physics(p)
# 玉が軸にかかり、底にも当たる寸法は、玉の決まりの行を 1 つだけ出す（エンジンと同じ）。重りの別の落ちがある時は玉の行を足さない
both = {**p, "axle_height": 15, "weight_below_axle": 5, "weight_g": 15, "weight_behind": 0}
ball = [f for f in TIGER.check_physics(both) if "粘土の玉" in f.message]
assert len(ball) == 1 and "軸の竹串にかかる" in ball[0].message, [f.line() for f in TIGER.check_physics(both)]
above = [f for f in TIGER.check_physics({**p, "weight_below_axle": -20}) if f.where == "重り"]
assert above and not any("粘土の玉" in f.message for f in above), [f.line() for f in above]
# 御来迎: 今の仮説（H-A〜H-E）の形は、開く糸・溝の矢印・足の帯（取り下げた EP-0012）を持たない
data, source = load(GORAIGO)
for h in data["hypotheses"]:
    q = {**FAN.DEFAULTS, **h["params"]}
    assert "band" not in {x.key for x in FAN.parts(q)} and not [a for x in FAN.parts(q) for a in x.art if a["kind"] == "mark"], h["id"]
    assert not any("開く糸 2 本（各" in w for w in FAN.steps(q)), h["id"]
# 筒を外すと扇が開く形（lift・EP-0017。エンジン issue/goraigo-v11 5325586 と同じ）: 糸・穴・扇の足・内筒・竹串が無く、2 受け（U の字・刷った面は全部糊代）がある。
# 台は山折りで、受けの底を貼る印がある。前の組には無い形（check_range が落とす）
h = next(x for x in data["hypotheses"] if x["id"] == data["sheet"])
lift = {**FAN.DEFAULTS, **h["params"], "push_part": "lift"}
assert not FAN.check_range(lift) and not FAN.check_physics(lift), [f.line() for f in FAN.check_range(lift) + FAN.check_physics(lift)]
by = {x.key: x for x in FAN.parts(lift)}
assert set(by) == {"tube", "base", "fan", "cradle", "figure"}, set(by)
assert not any(x.holes for x in by.values()) and min(px for px, _ in by["fan"].outline) == 0, "lift に穴か扇の足がある"
c = by["cradle"]
assert c.label == "2 受け" and len(c.valley) == 2 and not c.mountain and len(c.glue) == 3, (c.label, c.valley, c.glue)
assert by["base"].mountain and not by["base"].valley and by["base"].art, "台が山折りでないか、受けを貼る印が無い"
words_lift = FAN.steps(lift)
assert len(words_lift) == 9 and words_lift[-1] == "4 扇を手で畳み、上から 1 外筒をかぶせる。筒を上へ外すと、扇が開く", words_lift
assert not any(w in "".join(words_lift + FAN.materials(lift)) for w in ("糸", "竹串", "内筒", "穴に通")), (words_lift, FAN.materials(lift))
assert FAN.materials(lift)[1] == "のり、はさみ、定規" and [r["key"] for r in FAN.bom(lift)] == ["tube", "cradle", "base", "fan", "figure"]
pat = compose("slider_fan", lift, source)
assert not pat[2], [f.line() for f in pat[2]]
fig = next(x for x in pat[1]["parts"] if x.key == "figure")
cr = next(x for x in pat[1]["parts"] if x.key == "cradle")
assert cr.x > fig.x + fig.width and cr.y == fig.y, "受けが像の右に無い"
sheet_l, fl = compose_sheet("slider_fan", lift, source, h["name"], h["how_it_moves"])
assert not fl, [f.line() for f in fl]
# 手順の紙の問いと折る順の絵も、押す部品の無い形に合わせる（「押すと」のままだと組み方と合わない）
assert "筒を外すと、どこがどう動くと思いますか（言葉か絵で）" in words(sheet_l) and not any(w.startswith("押すと") for w in words(sheet_l))
assert sum(1 for x in sheet_l["shapes"] if x.get("tag") == "order_panel") == 3
with old_set(FAN):
    assert any(f.floor == "F5.range" for f in FAN.check_range(lift)), "前の組で lift が通った"

print("ok 次の組 goraigo-v11・tora-v4。折り線・手順の文・絵の見出しと矢じり・見出し・印の文・用意する物・凡例・作成動画の案")
