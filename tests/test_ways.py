"""作り方の印（omochae.ways、#261）。本人の決定: 「紙一枚」と「折るだけ」を別の印で持ち、「当時の材料」は再現の良さの別の軸。どれも上下の印ではない。"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from omochae import hypotheses, ways  # noqa: E402
from omochae.compose import TEMPLATES  # noqa: E402
from omochae.model import Part  # noqa: E402
from web import toy, toys  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
GORAIGO, TORA = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"


def hyp(sid, hid):
    return next(h for h in hypotheses.load(sid)["hypotheses"] if h["id"] == hid)


def marks_of(sid, hid):
    data = hypotheses.load(sid)
    h = hyp(sid, hid)
    return ways.marks(h.get("template", data.get("template", "slider_fan")), h["params"])


# 1. 印は宣言でなく、部品表と用意する物から出す（宣言だと、部品を変えた時に印と食い違う）
for hid in ("H-A", "H-B", "H-C"):
    assert marks_of(TORA, hid)["one_sheet"] is False, hid  # 虎は竹串と粘土が要る
    assert marks_of(TORA, hid)["period"] is True, hid  # 竹と粘土は当時の材料（engine と同じ見立て）

# 2. 紙と道具のほかの材料の語を、書き方が違っても拾う
tpl = TEMPLATES["slider_fan"]
keep = tpl.bom, tpl.materials
for word, modern in (("竹ひご", False), ("楊枝", False), ("つまようじ", False), ("木綿の糸", False), ("細い紐", False), ("油粘土", False), ("割り箸", False), ("セロハンテープ", True), ("ビーズ", True)):
    tpl.bom, tpl.materials = (lambda p: [{"name": "x", "material": "紙"}]), (lambda p, w=word: ["のり、はさみ、定規", f"{w} 1 本"])
    d = ways.details("slider_fan", {})
    assert d["one_sheet"] is False and d["period"] is not modern, (word, d)
tpl.bom, tpl.materials = keep
# 道具だけなら紙一枚を外さない
tpl.bom, tpl.materials = (lambda p: [{"name": "x", "material": "紙（厚さ 0.15mm 前後）"}]), (lambda p: ["のり、はさみ、定規", "紙を 1 枚"])
assert ways.details("slider_fan", {})["one_sheet"] is True
tpl.bom, tpl.materials = keep

# 3. 折るだけ: 部品が 1 つで、外形が長方形、中の切り込みも穴も無い（切らずに折る）
sheet = Part(1, "sheet", "紙", [(0, 0), (180, 0), (180, 260), (0, 260)], valley=[((90, 0), (90, 260))])
assert ways.fold_only([sheet]) is True
assert ways.fold_only([Part(1, "sheet", "紙", [(0, 0), (180, 0), (180, 260), (0, 260)], cuts=[(10, 10, 5, 5)])]) is False
assert ways.fold_only([Part(1, "sheet", "紙", [(0, 0), (180, 0), (180, 260), (0, 260)], holes=[(10, 10, 1)])]) is False
assert ways.fold_only([sheet, sheet]) is False
assert ways.fold_only([Part(1, "sheet", "紙", [(0, 0), (180, 0), (180, 100), (90, 130), (180, 260), (0, 260)])]) is False

# 4. 全部の仮説に、2 つの印と材料の軸が付く
table = ways.table()
want = {(p.stem, h["id"]) for p in (ROOT / "data/hypotheses").glob("*.json") for h in hypotheses.load(p.stem)["hypotheses"]}
assert {(r["source_id"], r["hypothesis_id"]) for r in table} == want and len(want) > 100
assert all(set(r) >= {"one_sheet", "fold_only", "period", "other_materials", "modern_substitutes"} for r in table)
assert all(r["period"] for r in table if r["one_sheet"])  # 紙だけなら当時の材料でもある
assert all(r["one_sheet"] == (not r["other_materials"]) for r in table)
assert all(not r["fold_only"] or r["one_sheet"] for r in table)  # 折るだけなのに紙のほかの材料が要る、は読み違い
# 判定が読めるよう、数を固定する。雛形や仮説を足して変わったら、増えた分の材料を見てここを直す
counts = {k: sum(r[k] for r in table) for k in ("one_sheet", "fold_only", "period")}
assert counts == {"one_sheet": 70, "fold_only": 0, "period": 77}, counts
assert [r["hypothesis_id"] for r in table if r["source_id"] == GORAIGO and r["one_sheet"]] == ["H-E"]  # 必須 2 種で紙一枚は御来迎の H-E だけ

# 5. 頁に札で出る。順位の形にしない。仮説の並びは元の記録のまま
data = hypotheses.load(TORA)
# 予想の段は #266 で外したので、予想を置かずに開いた頁にそのまま札が出る
page = toy.toy_page(TORA)
assert '<span class="lb">当時の材料</span>' in page and '<span class="lb">紙一枚</span>' not in page
assert "どの印も上下を表しません" in page
for w in ("順位", "おすすめ", "初心者", "点数", "★"):
    assert w not in page, w
at = [page.index(f"仮説 {hypotheses.letter(h)}「") for h in data["hypotheses"]]
assert at == sorted(at), "仮説の並びを変えた"
# 一覧は玩具ごと。どれかの仮説に付く印を、並びを変えずに出す
listing = toys.page("tenji")
assert listing.count('class="ways"') >= 1 and "どの印も上下を表しません" in listing
assert ways.toy_labels(TORA) == ["当時の材料"]
at = [listing.index(f'href="/toy/{sid}"') for sid in sorted(toys.sources(), key=lambda s: hypotheses.stage(s) != "必須")]
assert at == sorted(at), "印で一覧の並びを変えた"

# 6. 入口: JSON で出す。間違った呼び方は 4
r = subprocess.run([sys.executable, "-m", "omochae.ways", "--json"], capture_output=True, text=True)
assert r.returncode == 0 and json.loads(r.stdout) == json.loads(json.dumps(table, ensure_ascii=False)), r.stderr
assert subprocess.run([sys.executable, "-m", "omochae.ways", "--nope"], capture_output=True).returncode == 4
print("ok")
