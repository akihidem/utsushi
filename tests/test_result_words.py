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

from omochae import engine_bundle, hypotheses, making_log, records  # noqa: E402
from omochae.compose import TEMPLATES  # noqa: E402
from omochae.instructions import compose_sheet  # noqa: E402
from web import techo_site, toy  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
UNSURE = "わからない"
DEGREE = ("少し", "よく", "とても", "かなり", "まあまあ", "あまり", "ちょっと", "だいぶ", "すごく")
SOURCES = {}  # 雛形ごとに、その雛形の玩具を全部
for p in sorted((ROOT / "data/hypotheses").glob("*.json")):
    SOURCES.setdefault(json.loads(p.read_text(encoding="utf-8")).get("template", "slider_fan"), []).append(p.stem)
# 虎は前の本人の判断（2 値）に当たるので、次の commit で分けて変える。
THREE = [t for t in TEMPLATES if t != "pivot_counterweight"]


def add(sid, word):
    rid, fails = records.add({"source_id": sid, "hypothesis_id": hypotheses.load(sid)["hypotheses"][0]["id"], "sheet_version": 1, "result": word, "fixes": []})
    assert fails == [], (sid, word, [f.line() for f in fails])
    return rid


def boxes(tid, sid, h):
    """手順の紙の丸の欄の札。欄は幅 30 の枠で、札はその枠の中の字。"""
    source = json.loads((ROOT / "data/sources" / f"{sid}.json").read_text(encoding="utf-8"))
    layout, fails = compose_sheet(tid, h["params"], source, h["name"], h["how_it_moves"])
    assert not fails, (sid, h["id"], [f.line() for f in fails])
    frames = [s for s in layout["shapes"] if s["kind"] == "rect" and s["w"] == 30]
    return [t.text for f in frames for t in layout["texts"] if t.text and abs(t.x - f["x"] - 2) < 0.01 and abs(t.y - f["y"] - 0.5) < 0.01]


# 1. 札の形: 3 つで、最後が「わからない」、2 番目が打ち消し、度合いの言葉が無い
for tid in THREE:
    tpl = TEMPLATES[tid]
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
    for page in (toy.record_form(sid, data, []), techo_site.page(sid, [h["id"] for h in data["hypotheses"]], "")):
        for w in tpl.RESULTS:
            assert f'name="result" value="{w}"' in page, (sid, w)
        for w in getattr(tpl, "OLD_RESULTS", {}):
            assert f'name="result" value="{w}"' not in page, (sid, w)

# 4. 紙: 欄を足しても全部の玩具の全部の紙が検査を通る（欄が次の行へ送られて頁からはみ出さない）。欄は札の数だけある
for tid, sids in SOURCES.items():
    tpl = TEMPLATES[tid]
    for sid in sids:
        for h in hypotheses.load(sid)["hypotheses"]:
            assert boxes(tid, sid, h) == list(getattr(tpl, "PAPER_RESULTS", tpl.RESULTS)), (sid, h["id"])

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
for tid in THREE:
    sid = SOURCES[tid][-1]
    before = making_log.summary(sid)["completion"]["moved"]
    add(sid, UNSURE)
    assert making_log.summary(sid)["completion"]["moved"] == before, tid
    add(sid, TEMPLATES[tid].RESULTS[0])
    assert making_log.summary(sid)["completion"]["moved"] == before + 1, tid
    table = records.summarize(records.all_records(sid))[hypotheses.load(sid)["hypotheses"][0]["id"]]
    assert table[UNSURE] >= 1 and table[TEMPLATES[tid].RESULTS[1]] == 0, (tid, table)

# 7. 英語の訳: 今の札にも前の札にもある（前の札の記録も英語で読めるように）
required = json.loads((ROOT / "data/en/required.json").read_text(encoding="utf-8"))
for tid, tpl in TEMPLATES.items():
    for w in (*tpl.RESULTS, *getattr(tpl, "OLD_RESULTS", {})):
        assert w in required["results"], (tid, w)

print("ok")
