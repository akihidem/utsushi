"""見た事の札を読む所（#146）。札の言葉を直しても、前の札で残った記録が読める。「?」の絵は「わからない」だけ。

札の言葉は雛形が持つ。言葉を直すと、前の札で残った記録は検査で断られ、集計で落ち、エンジンへ渡す束の数から消える。
言葉そのものは本人が決めるので、ここでは見ない。試験の中だけの前の札を雛形に持たせて、読む所を見る。
"""
import json
import os
import pathlib
import re
import tempfile

DATA = tempfile.mkdtemp()
os.environ["OMOCHAE_DATA"] = DATA

from omochae import engine_bundle, hypotheses, making_log, records  # noqa: E402
from omochae.compose import TEMPLATES  # noqa: E402
from web import techo_site, techo_step, toy  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
UNSURE = "わからない"
SOURCES = {}  # 雛形ごとに、その雛形の玩具
for p in sorted((ROOT / "data/hypotheses").glob("*.json")):
    SOURCES.setdefault(json.loads(p.read_text(encoding="utf-8")).get("template", "slider_fan"), []).append(p.stem)
assert set(SOURCES) == set(TEMPLATES), "どの雛形にも玩具がある（無い雛形は画面で確かめられない）"


def tiles_of(page):
    return dict(re.findall(r'(?:name="result"|class="tile") value="([^"]+)"[^>]*>(<svg.*?</svg>)', page))


# 1. 札の絵: 「?」の絵は「わからない」だけ。動きの言葉まで分からない札に見せない。動く側と動かない側は別の絵
for tid, sids in SOURCES.items():
    tpl, sid = TEMPLATES[tid], sids[0]
    data = hypotheses.load(sid)
    sure = [w for w in tpl.RESULTS if w != UNSURE]
    # 結果の札は手帖の のこす にある（玩具の頁の記録の欄は、本人の答え 11-07 夕の Q3 で のこす へ寄せた）
    for page in (techo_step.page(sid, [h["id"] for h in data["hypotheses"]]),):
        tiles = tiles_of(page)
        assert list(tiles) == list(tpl.RESULTS), (sid, tiles)
        assert [w for w, svg in tiles.items() if svg == techo_site.ICONS[UNSURE]] == [w for w in tpl.RESULTS if w == UNSURE], (sid, tiles)
        assert tiles[sure[0]] != tiles[sure[-1]], (sid, tiles)

# 2. 前の札を雛形に持たせる。今の札のどれに当たるかだけを持つ
TID = "wheel_cart"
tpl, SID = TEMPLATES[TID], SOURCES[TID][0]
HYP = hypotheses.load(SID)["hypotheses"][0]["id"]
SURE = [w for w in tpl.RESULTS if w != UNSURE]
MOVED, STILL = SURE[0], SURE[-1]
OLD_MOVED, OLD_STILL = "前の札の動いた", "前の札の動かない"
assert records.old_results_for(SID) == {}, "前の札を持たない雛形は、空"
tpl.OLD_RESULTS = {OLD_MOVED: MOVED, OLD_STILL: STILL}
assert records.old_results_for(SID) == tpl.OLD_RESULTS


def add(word):
    rid, fails = records.add({"source_id": SID, "hypothesis_id": HYP, "sheet_version": 1, "result": word, "fixes": []})
    assert fails == [], (word, [f.line() for f in fails])
    return rid


rid_old = add(OLD_MOVED)
add(OLD_STILL)
add(MOVED)

# 3. 検査: 前の札は受け、札に無い言葉は断る。断りの文には今の札だけを出す。字でない物が来ても、断るだけで落ちない
rec = json.loads((pathlib.Path(DATA) / "records" / f"{rid_old}.json").read_text(encoding="utf-8"))
assert rec["result"] == OLD_MOVED, "記録の中身を今の言葉に書き換えない"
fails = records.check({"source_id": SID, "hypothesis_id": HYP, "result": "たぶん動いた"})
assert {f.floor for f in fails} == {"F3.result"} and "／".join(tpl.RESULTS) in fails[0].line() and "前の札" not in fails[0].line(), [f.line() for f in fails]
assert {f.floor for f in records.check({"source_id": SID, "hypothesis_id": HYP, "result": [MOVED]})} == {"F3.result"}

# 4. 仮説ごとの集計: 前の札で落ちない。書いた言葉のまま別に数え、合算しない（F3）
table = records.summarize(records.all_records(SID))[HYP]
assert table[OLD_MOVED] == 1 and table[OLD_STILL] == 1 and table[MOVED] == 1 and table[STILL] == 0, table

# 5. 改善の頁の数: 前の札も今の札に読み替えて、動いた側に数える
done = making_log.summary(SID)["completion"]
assert done["moved_word"] == MOVED and done["moved"] == 2, done

# 6. エンジンへ渡す束: エンジンは今の札の言葉で数を引くので、今の札に読み替えて渡す。読み替えないと数から落ちる
group = next(g for g in engine_bundle.build()["groups"] if g["template"] == TID)
assert group["results"] == {MOVED: 2, STILL: 1}, group
assert (group["moved_word"], group["not_moved_word"]) == (MOVED, STILL), group

# 7. 手で置かれた記録の札が字でなくても、束は作れる。札の数には入れない（束は入口の床を通っていない記録も読む）
hand = {"id": "R-0098", "source_id": SID, "hypothesis_id": HYP, "sheet_version": 1, "result": [MOVED], "fixes": []}
(pathlib.Path(DATA) / "records" / "R-0098.json").write_text(json.dumps(hand, ensure_ascii=False), encoding="utf-8")
group = next(g for g in engine_bundle.build()["groups"] if g["template"] == TID)
assert group["results"] == {MOVED: 2, STILL: 1} and group["reports"] == 4, group
(pathlib.Path(DATA) / "records" / "R-0098.json").unlink()

# 8. 頁: 前の札は選べない。記録の一覧には書いた言葉のまま出る
data = hypotheses.load(SID)
page = techo_site.records_page(SID)  # 記録の札は手帖の記録の頁にある（#87）。結果の札は作る頁と玩具の頁
assert OLD_MOVED not in tiles_of(techo_step.page(SID, [h["id"] for h in data["hypotheses"]]))
assert rid_old in page and OLD_MOVED in page

print("ok")
