"""見た事の札を、どの玩具でも同じ形にする（#146）。

見る線: どの雛形も「動きの言葉・その打ち消し・わからない」の 3 つで、度合いの言葉が無い。度合いは出来ばえの段に
読める（記録は観察で、成績にしない線）。前の札の対応が合っている。全部の玩具の手順の紙が、札を足しても検査を通る。
読む所そのものは tests/test_result_readers.py、紙の指紋は tests/test_floor_pin.py が見る。
"""
import json
import os
import pathlib
import tempfile

DATA = tempfile.mkdtemp()
os.environ["OMOCHAE_DATA"] = DATA

from omochae import engine_bundle, hypotheses, making_log, records, trial_video  # noqa: E402
from omochae.compose import TEMPLATES  # noqa: E402
from omochae.instructions import compose_sheet  # noqa: E402
from web import techo_step, toy  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
UNSURE = "わからない"
DEGREE = ("少し", "よく", "とても", "かなり", "まあまあ", "あまり", "ちょっと", "だいぶ", "すごく")
SOURCES = {}  # 雛形ごとに、その雛形の玩具を全部
for p in sorted((ROOT / "data/hypotheses").glob("*.json")):
    SOURCES.setdefault(json.loads(p.read_text(encoding="utf-8")).get("template", "slider_fan"), []).append(p.stem)
TORA = "NDL-1187053-R0000014-R"


def add(sid, word):
    rid, fails = records.add({"source_id": sid, "hypothesis_id": hypotheses.load(sid)["hypotheses"][0]["id"], "sheet_version": 1, "result": word, "fixes": []})
    assert fails == [], (sid, word, [f.line() for f in fails])
    return rid


def boxes(tid, sid, h):
    """手順の紙の丸の欄の札。欄は幅 30 の枠で、札はその枠の中の字。"""
    source = json.loads((ROOT / "data/sources" / f"{sid}.json").read_text(encoding="utf-8"))
    tpl = TEMPLATES[tid]
    # 御来迎の今の組（goraigo-v14）は 11-06 から手順の紙を刷らず、内筒を下から押し上げる形の手順の紙は A4 に収まらない。
    # 札の欄は手順の紙を控えた前の組（goraigo-v10）で見る（tests/test_floor_pin.py の STEP_SHEET_SETS と同じ線）
    now = tpl.SHEET_SET
    if tid == "slider_fan":
        tpl.SHEET_SET = tpl.FROZEN_SET
        h = next(x for x in hypotheses.load(sid)["hypotheses"] if x["id"] == h["id"])
    try:
        layout, fails = compose_sheet(tid, h["params"], source, h["name"], h["how_it_moves"])
    finally:
        tpl.SHEET_SET = now
    assert not fails, (sid, h["id"], [f.line() for f in fails])
    frames = [s for s in layout["shapes"] if s["kind"] == "rect" and s["w"] == 30]
    return [t.text for f in frames for t in layout["texts"] if t.text and abs(t.x - f["x"] - 2) < 0.01 and abs(t.y - f["y"] - 0.5) < 0.01]


# 1. 札の形: 3 つで、最後が「わからない」、2 番目が打ち消し、度合いの言葉が無い
for tid, tpl in TEMPLATES.items():
    assert len(tpl.RESULTS) == 3 and tpl.RESULTS[2] == UNSURE, (tid, tpl.RESULTS)
    assert tpl.RESULTS[1].endswith("ない"), (tid, tpl.RESULTS)
    assert not [w for w in tpl.RESULTS for d in DEGREE if d in w], (tid, tpl.RESULTS)

# 2. 前の札は今の札に対応する。「わからない」に読み替えると、見た事が消える
for tid, tpl in TEMPLATES.items():
    old = getattr(tpl, "OLD_RESULTS", {})
    assert not set(old) & set(tpl.RESULTS), (tid, old)
    assert set(old.values()) <= set(tpl.RESULTS) - {UNSURE}, (tid, old)
assert TEMPLATES["string_pull"].OLD_RESULTS == {"よく動いた": "動いた", "少し動いた": "動いた"}
assert TEMPLATES["stick_prop"].OLD_RESULTS == {"少し遊べた": "遊べた"}
assert TEMPLATES["stand_figure"].OLD_RESULTS == {"倒れた": "立たない"}

# 3. 画面: 記録の欄と手帖の両方に今の札が全部あり、前の札は選べない。札の作りは雛形ごとなので、玩具は 1 つずつ見る
for tid, sids in SOURCES.items():
    tpl, sid = TEMPLATES[tid], sids[0]
    data = hypotheses.load(sid)
    # 手帖は 1 手 1 画面に作り直され（#87）、札は記録の欄の radio でなく、手帖の段の釦（value に札の字）になった
    # 結果の札は手帖の のこす にある（玩具の頁の記録の欄は、本人の答え 11-07 夕の Q3 で のこす へ寄せた）
    for page, mark in ((techo_step.page(sid, [h["id"] for h in data["hypotheses"]]), 'class="tile" value="{}"'),):
        for w in tpl.RESULTS:
            assert mark.format(w) in page, (sid, w)
        for w in getattr(tpl, "OLD_RESULTS", {}):
            assert mark.format(w) not in page, (sid, w)

# 3b. 声で選ぶ札（前の techo_step.RESULT_WORDS）は、11-08 に手帖の作る頁の音声認識と一緒に外した（本人「クロードの音声認識をはずして、
# ユーザーの端末の音声入力に頼るのでいいのではないか。」）。札は押して選ぶだけで、送る値は札の value（上の 3 の照らし）。前の札は頁に出ない
assert not hasattr(techo_step, "RESULT_WORDS")

# 3c. 動画の報告: どの雛形も、打ち消しの札（2 つ目）が「動かなかった」として渡る。3 つ目の「わからない」は渡さない（None）
for tid, tpl in TEMPLATES.items():
    assert tpl.RESULTS[1] in trial_video.NOT_MOVED and tpl.RESULTS[2] == UNSURE, (tid, tpl.RESULTS)
    assert UNSURE not in trial_video.NOT_MOVED + trial_video.PARTLY_MOVED

# 4. 紙: 欄を足しても全部の玩具の全部の紙が検査を通る（欄が次の行へ送られて頁からはみ出さない）。欄は札の数だけある
for tid, sids in SOURCES.items():
    tpl = TEMPLATES[tid]
    for sid in sids:
        for h in hypotheses.load(sid)["hypotheses"]:
            assert boxes(tid, sid, h) == list(tpl.paper_results() if hasattr(tpl, "paper_results") else tpl.RESULTS), (sid, h["id"])

# 5. 前の札の記録の数: 改善の頁とエンジンへ渡す束で、対応した今の札に数える
PULL, PROP, STAND = (SOURCES[t][0] for t in ("string_pull", "stick_prop", "stand_figure"))
add(PULL, "よく動いた")
add(PULL, "少し動いた")
add(PULL, "動かない")
add(PROP, "少し遊べた")
add(STAND, "倒れた")
sm = making_log.summary(PULL)["completion"]
assert sm["moved_word"] == "動いた" and sm["moved"] == 2, sm
groups = {g["template"]: g for g in engine_bundle.build()["groups"]}
pull = groups["string_pull"]
assert pull["results"] == {"動いた": 2, "動かない": 1} and (pull["moved_word"], pull["not_moved_word"]) == ("動いた", "動かない"), pull
assert groups["stick_prop"]["results"] == {"遊べた": 1}, groups["stick_prop"]
stand = groups["stand_figure"]
assert stand["results"] == {"立たない": 1} and stand["not_moved_word"] == "立たない", stand

# 6. 「わからない」を動いた側にも動かない側にも数えない（F3）。5 と混ざらないよう、ここで足す
for tid in TEMPLATES:
    sid = SOURCES[tid][-1]
    before = making_log.summary(sid)["completion"]["moved"]
    add(sid, UNSURE)
    assert making_log.summary(sid)["completion"]["moved"] == before, tid
    add(sid, TEMPLATES[tid].RESULTS[0])
    assert making_log.summary(sid)["completion"]["moved"] == before + 1, tid
    table = records.summarize(records.all_records(sid))[hypotheses.load(sid)["hypotheses"][0]["id"]]
    assert table[UNSURE] >= 1 and table[TEMPLATES[tid].RESULTS[1]] == 0, (tid, table)

# 7. 虎: 記録では「わからない」を選べる。手順の紙の札は刷る組で決まる（本人の決め 11-06「次の組の紙から 3 つの欄」）。
# 決めの前に紙の指紋を控えた組（TWO_BOX_SETS）は 2 つの欄のまま、それより後の組は 3 つの欄。
# 組を 1 つの値で見ない: 今の組が上がっても（tora-v6 など）、控えた組の紙は 2 つの欄のまま、今の組の紙は 3 つの欄になる事を、紙そのもので見る
pc = TEMPLATES["pivot_counterweight"]
pinned = json.loads((ROOT / "tests" / "floor_pin.json").read_text(encoding="utf-8"))["papers"]
assert pc.TWO_BOX_SETS and all(any(n.startswith(f"{s}/") for n in pinned) for s in pc.TWO_BOX_SETS), ("2 つの欄は、指紋を控えた組だけ", pc.TWO_BOX_SETS)
tora_h = hypotheses.load(TORA)["hypotheses"][0]
now_set = pc.SHEET_SET
try:
    for s, want in [*((s, pc.PAPER_RESULTS) for s in pc.TWO_BOX_SETS), ("tora-v99", pc.RESULTS)]:
        pc.SHEET_SET = s
        assert pc.paper_results() == want and boxes("pivot_counterweight", TORA, tora_h) == list(want), (s, want)
finally:
    pc.SHEET_SET = now_set
assert records.check({"source_id": TORA, "hypothesis_id": "H-A", "result": UNSURE}) == []
assert {f.floor for f in records.check({"source_id": TORA, "hypothesis_id": "H-A", "result": "たぶん揺れた"})} == {"F3.result"}

# 8. 英語の訳: 今の札にも前の札にもある（前の札の記録も英語で読めるように）
required = json.loads((ROOT / "data/en/required.json").read_text(encoding="utf-8"))
for tid, tpl in TEMPLATES.items():
    for w in (*tpl.RESULTS, *getattr(tpl, "OLD_RESULTS", {})):
        assert w in required["results"], (tid, w)

print("ok")
