"""改善の歴史の表の写しと読み口（本人の言葉 11-07「どう改善が進むかは山場なのでデモにも載せたいところ。サイトにも記載したい」。設計 0.7 節）。

見る事:
1. 写しは表のまま（機械のパスの欄 strip と、ワークショップの欄 workshops・workshops_source を外す。窓口の決め 11-07 案 A。版の行の sheet_pdf も外す）。repo に個人のパスが入らない。出す形は写す口と同じ（indent 1・ensure_ascii なし・末尾に改行）
2. 版の歩みは、サイトが今刷る組（雛形の SHEET_SET）までを古い順に並べ、今の組の行だけが now。前の組に雛形を置くとそこで止まり、
   表に無い組に上げた時は、どの行も今の版と言わない
3. エンジンの今の版は、サイトが今刷る組が結ぶ版の大きい方（表の最新ではない）。エンジンの版を刻んでいない版（御来迎 v13）は数えない
4. 紙の絵は sheets/ の下の名だけを引き、置いていない時は None。決まりの外の名（.. を含む）は開かない
5. 写す口は表を同じ形で書き、表と同じ所の sheets/ の絵を out/history/sheets に置く
6. README の数の欄の型紙の版とエンジンの版は、表と雛形から描いた字と同じ
"""
import json
import pathlib
import re
import tempfile

from omochae import kaizen_history as kh
from omochae import ledger
from omochae.compose import TEMPLATES

FAN, TIGER = TEMPLATES["slider_fan"], TEMPLATES["pivot_counterweight"]


class sets:
    """雛形の今の組を置き替える（前の組を刷る道と同じ渡し方）。"""

    def __init__(self, fan=None, tiger=None):
        self.want = {FAN: fan, TIGER: tiger}

    def __enter__(self):
        self.keep = {t: t.SHEET_SET for t in self.want}
        for t, s in self.want.items():
            if s:
                t.SHEET_SET = s

    def __exit__(self, *_):
        for t, s in self.keep.items():
            t.SHEET_SET = s


# 1. 写しは表のまま、外す 3 つの欄だけを外す
text = kh.PATH.read_text(encoding="utf-8")
data = kh.load()
assert not set(kh.DROP) & set(data) and {"toys", "engine_versions", "terms"} <= set(data), sorted(data)
assert kh.DROP == ("strip", "workshops", "workshops_source"), "感想の中身のまとめに読める欄を repo に入れない（窓口の決め 11-07）"
assert not re.search(r"/home/|~/|/Users/", text), "repo に個人のパスを入れない"
assert not any(set(kh.ROW_DROP) & set(r) for t in data["toys"] for r in t["versions"]), "版の行の Drive の置き場（sheet_pdf）を入れない"
assert text == json.dumps(data, ensure_ascii=False, indent=1) + "\n", "出す形が写す口と違う（#518 の写しとそろえる）"

# 2. 版の歩みは今刷る組まで、古い順。今の組の行だけが now
for tpl in (FAN, TIGER):
    rows = kh.versions(tpl.__name__.rsplit(".", 1)[1])
    assert [kh.set_no(r["set"]) for r in rows] == sorted(kh.set_no(r["set"]) for r in rows) and len(rows) >= 2, rows
    assert [r["now"] for r in rows] == [False] * (len(rows) - 1) + [True] and rows[-1]["set"] == tpl.SHEET_SET, [(r["set"], r["now"]) for r in rows]
    assert all(r["line"] and r["engine_version_text"] and r["sheet_image"] for r in rows), "額の下の字と絵の名は表の行にある"
# 表は 11-07 11:42 の版から、改善の輪より前の版（虎 v1・v2、御来迎 v1〜v9。サイトの repo の記録から）も持つ
assert [r["set"] for r in kh.versions("pivot_counterweight")] == [f"tora-v{n}" for n in range(1, 8)]
assert [r["set"] for r in kh.versions("slider_fan")] == [f"goraigo-v{n}" for n in range(1, 15)]
with sets(fan=FAN.FROZEN_SET, tiger=TIGER.FROZEN_SET):
    assert [(r["set"], r["now"]) for r in kh.versions("pivot_counterweight")] == [("tora-v1", False), ("tora-v2", False), ("tora-v3", True)]
    assert [r["set"] for r in kh.versions("slider_fan")][-1] == "goraigo-v10" and len(kh.versions("slider_fan")) == 10
with sets(tiger="tora-v99"):
    assert not any(r["now"] for r in kh.versions("pivot_counterweight")), "表に無い組を今の版と言わない"
assert kh.versions("no_such_template") == []

# 3. エンジンの今の版は、今刷る組が結ぶ版の大きい方
now = kh.engine_now()
assert now["engine_version"] == 7 and now["line"] == next(e["line"] for e in data["engine_versions"] if e["engine_version"] == 7)
with sets(tiger="tora-v4"):
    assert kh.engine_now()["engine_version"] == 6, "虎 v4（版 2）と御来迎 v14（版 6）なら 6。表の最新の 7 ではない"
with sets(fan="goraigo-v13", tiger=TIGER.FROZEN_SET):
    v13 = next(r for r in kh.versions("slider_fan") if r["now"])
    assert v13["engine_version"] is None and "刻んでいない" in v13["engine_version_text"], v13
    assert kh.engine_now() is None, "刻んでいない版（御来迎 v13）と台帳と結ばない版（虎 v3）だけなら、エンジンの今の版は無い"

# 4. 紙の絵は sheets/ の下の名だけ
tmp = pathlib.Path(tempfile.mkdtemp())
keep_pictures, kh.PICTURES = kh.PICTURES, tmp / "out-history"
try:
    (kh.PICTURES / "sheets").mkdir(parents=True)
    (kh.PICTURES / "sheets/tora-v7.png").write_bytes(b"png")
    (tmp / "secret.png").write_bytes(b"x")
    assert kh.picture({"sheet_image": "sheets/tora-v7.png"}) == kh.PICTURES / "sheets/tora-v7.png"
    assert kh.picture({"sheet_image": "sheets/tora-v6.png"}) is None, "置いていない絵は None"
    assert kh.picture({"sheet_image": "../secret.png"}) is None and kh.picture({"sheet_image": "sheets/../../secret.png"}) is None
    assert kh.picture({}) is None
finally:
    kh.PICTURES = keep_pictures

# 5. 写す口: 外す欄を外して同じ形で書き、絵を置く
src = tmp / "grove"
(src / "sheets").mkdir(parents=True)
table = {"title": "t", "strip": "~/somewhere/strip.png", "workshops": [{"line": "感想から"}], "workshops_source": "答え", "toys": [{"toy": "虎", "template": "pivot_counterweight", "versions": [
    {"set": "tora-v3", "sheet_image": "sheets/tora-v3.png", "sheet_pdf": "Drive x/a.pdf"}, {"set": "tora-v4", "sheet_image": "../tora-v4.png"}]}], "engine_versions": []}
(src / "kaizen-history.json").write_text(json.dumps(table, ensure_ascii=False), encoding="utf-8")
(src / "sheets/tora-v3.png").write_bytes(b"png3")
(src / "tora-v4.png").write_bytes(b"png4")
keep = kh.PATH, kh.PICTURES
kh.PATH, kh.PICTURES = tmp / "data/history/kaizen-history.json", tmp / "out/history"
try:
    assert kh.main(["copy", str(src / "kaizen-history.json")]) == 0
    written = kh.PATH.read_text(encoding="utf-8")
    want = {k: v for k, v in table.items() if k not in kh.DROP}
    want["toys"] = [{**t, "versions": [{k: v for k, v in r.items() if k != "sheet_pdf"} for r in t["versions"]]} for t in want["toys"]]
    assert written == json.dumps(want, ensure_ascii=False, indent=1) + "\n"
    assert "workshops" not in written and "strip" not in written and "sheet_pdf" not in written
    assert (kh.PICTURES / "sheets/tora-v3.png").read_bytes() == b"png3" and not (tmp / "out/tora-v4.png").exists(), "決まりの外の名の絵は置かない"
    assert kh.main(["copy"]) == 4 and kh.main(["copy", str(tmp / "none.json")]) == 4, "使い方の誤りと読めない表は 4"
finally:
    kh.PATH, kh.PICTURES = keep

# 6. README の数の欄
readme = (ledger.ROOT / "README.md").read_text(encoding="utf-8")
counts = ledger.render_counts()
assert counts in readme, "README の数の欄が表と雛形から描いた物と違う（python -m omochae.ledger render）"
# エンジンの版の注は「全部の玩具の型紙に効く」と書かない（3D の確かめは御来迎と虎だけ・エンジンの版 3〜7 は 1 つの玩具の組だけで、言い過ぎ。照らしの止め 11-08・#671）
assert "全部の玩具の型紙に効く" not in counts and "そのエンジンが作る型紙のどれにも使われる" in counts, counts
assert "- 型紙の版: 張子の首振り虎 7・御来迎 14（" in counts and "- エンジンの版: 7（" in counts, counts

print("ok 改善の歴史の表の写しと読み口（今刷る組まで・エンジンの今の版・絵の名の決まり・写す口・README の数）")
