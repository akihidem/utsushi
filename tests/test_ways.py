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
from web import genre, toy, toys  # noqa: E402

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
    assert marks_of(TORA, hid)["period"] is False, hid  # 油粘土は江戸の頃に無かったので、当時の材料に数えない（#311）

# 2. 紙と道具のほかの材料の語を、書き方が違っても拾う。当時の材料は一覧に当たる物だけで、知らない物にも今の物にも付けない（#311）
# 語と素材の 2 つの表は、エンジン（paper-to-toy の tests/test_ways.py）にも同じ物を置く。片方を変える時は両方を変える
WORD_PERIOD = (("竹串", True), ("竹ひご", True), ("楊枝", True), ("つまようじ", True), ("割り箸", True), ("木綿の糸", True), ("たこ糸", True), ("細い紐", True), ("鈴", True), ("玉", True),
               ("油粘土", False), ("粘土", False), ("セロハンテープ", False), ("ビーズ", False), ("輪ゴム", False), ("割ピン", False), ("厚紙", False), ("ストロー", False))
MATERIAL_PERIOD = (("竹串（長さ 180mm）", True, []), ("木綿の糸（200mm）", True, []), ("竹串 1 本とテープ", False, ["テープ"]), ("油粘土 3g", False, ["油粘土"]),
                   ("油粘土の玉（直径 8mm）かビーズ", False, ["ビーズ", "油粘土"]), ("針金", False, []))
tpl = TEMPLATES["slider_fan"]
keep = tpl.bom, tpl.materials
for word, period in WORD_PERIOD:
    tpl.bom, tpl.materials = (lambda p: [{"name": "x", "material": "紙"}]), (lambda p, w=word: ["のり、はさみ、定規", f"{w} 1 本"])
    d = ways.details("slider_fan", {})
    assert d["one_sheet"] is False and d["period"] is period, (word, d)
# 部品表の素材でも同じ。当時の物と今の物が混ざれば付けない。どちらの一覧にも無い物は、今の物とも言わずに付けない
for material, period, modern in MATERIAL_PERIOD:
    tpl.bom, tpl.materials = (lambda p, m=material: [{"name": "x", "material": m}]), (lambda p: ["のり、はさみ、定規"])
    d = ways.details("slider_fan", {})
    assert d["one_sheet"] is False and d["period"] is period and d["modern_substitutes"] == modern, (material, d)
tpl.bom, tpl.materials = keep
# 道具だけなら紙一枚を外さない。紙だけなら当時の材料でもある
tpl.bom, tpl.materials = (lambda p: [{"name": "x", "material": "紙（厚さ 0.15mm 前後）"}]), (lambda p: ["のり、はさみ、定規", "紙を 1 枚"])
d = ways.details("slider_fan", {})
assert d["one_sheet"] is True and d["period"] is True, d
tpl.bom, tpl.materials = keep

# 3. 折るだけ: 部品が 1 つで、外形が長方形、中の切り込みも穴も糊代も無く、折り線が 1 本以上ある（#311）。
# 落ちる例にはどれも折り線を持たせて、落ちる理由を 1 つにする
RECT, FOLD = [(0, 0), (180, 0), (180, 260), (0, 260)], ((90, 0), (90, 260))
sheet = Part(1, "sheet", "紙", RECT, valley=[FOLD])
assert ways.fold_only([sheet]) is True
assert ways.fold_only([Part(1, "sheet", "紙", RECT, mountain=[FOLD])]) is True  # 山折りだけでも折り線がある
assert ways.fold_only([Part(1, "sheet", "紙", RECT, valley=[FOLD], cuts=[(10, 10, 5, 5)])]) is False
assert ways.fold_only([Part(1, "sheet", "紙", RECT, valley=[FOLD], holes=[(10, 10, 1)])]) is False
assert ways.fold_only([Part(1, "sheet", "紙", RECT, valley=[FOLD], glue=[[(0, 0), (10, 0), (10, 260), (0, 260)]])]) is False  # 糊代付きの長方形
assert ways.fold_only([Part(1, "sheet", "紙", RECT)]) is False  # 折り線の無い長方形
assert ways.fold_only([sheet, sheet]) is False
assert ways.fold_only([Part(1, "sheet", "紙", [(0, 0), (180, 0), (180, 100), (90, 130), (180, 260), (0, 260)], valley=[FOLD])]) is False

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
# 御来迎の H-C は、次の組（goraigo-v14）で割り箸をセロハンテープで内筒に留める形になり、テープは今の物で代えた材料なので
# 「当時の材料」が外れて 1 つ減った（前は割り箸の柄を差す形で当時の材料。紙一枚の数は変わらない）
assert counts == {"one_sheet": 70, "fold_only": 0, "period": 73}, counts
assert not [r for r in table if r["period"] and r["modern_substitutes"]]  # 今の物で代えたのに当時の材料、は読み違い
assert [r["hypothesis_id"] for r in table if r["source_id"] == GORAIGO and r["one_sheet"]] == ["H-E"]  # 必須 2 種で紙一枚は御来迎の H-E だけ

# 5. 頁に札で出る。順位の形にしない。仮説の並びは元の記録のまま
data = hypotheses.load(TORA)
# 予想の段は #266 で外したので、予想を置かずに開いた頁にそのまま札が出る
page = toy.toy_page(GORAIGO)
# 札の印はたたき台の分（J-032）。御来迎の次の組（goraigo-v14）のたたき台 H-C は、割り箸をセロハンテープで留める（テープは今の物で代えた材料）ので、
# 「紙一枚」も「当時の材料」も付かない（前の組の H-A は竹串と糸で「当時の材料」だった）。本人の決定 19:44 で、たたき台が紙一枚でなくてよい
assert 'class="ways"' not in page
page = toy.toy_page(TORA)
assert 'class="ways"' not in page  # 虎は竹串と油粘土が要るので、どの印も付かない。札の無い頁も開く
assert "どれがえらい、ということはありません" in page
for w in ("順位", "おすすめ", "初心者", "点数", "★"):
    assert w not in page, w
assert f'仮説 {hypotheses.letter(hypotheses.sheet_of(TORA))}「' in page and "仮説 B「" not in page, "札はたたき台の 1 枚だけ（J-032）"
# 一覧は玩具ごと。たたき台に付く印を、並びを変えずに出す（J-032。本人の決定 19:44 で、必須 2 種に紙一枚が付かなくてよい）
listing = toys.page("tenji")
assert listing.count('class="ways"') >= 1 and "どれがえらい、ということはありません" in listing
assert ways.toy_labels(TORA) == [] and ways.toy_labels(GORAIGO) == []
# 並びは、必須 2 種 → ジャンルの見出しごと（genre.groups の順。本人の依頼 11-06）で、見出しの中は記録の順。印ではこの並びを変えない
rest = [s for s in toys.sources() if hypotheses.stage(s) != "必須"]
order = [s for s in toys.sources() if hypotheses.stage(s) == "必須"] + [s for _, mids in genre.groups(rest) for _, ss in mids for s in ss]
at = [listing.index(f'href="/toy/{sid}"') for sid in order]
assert at == sorted(at), "印で一覧の並びを変えた"

# 6. 入口: JSON で出す。間違った呼び方は 4
r = subprocess.run([sys.executable, "-m", "omochae.ways", "--json"], capture_output=True, text=True)
assert r.returncode == 0 and json.loads(r.stdout) == json.loads(json.dumps(table, ensure_ascii=False)), r.stderr
assert subprocess.run([sys.executable, "-m", "omochae.ways", "--nope"], capture_output=True).returncode == 4

# 7. 名前はエンジン（paper-to-toy の omochae.ways）と同じ。片方を変える時は両方の試験を変える
ENGINE_MARKS = {"one_sheet": "紙一枚", "fold_only": "折るだけ", "period": "当時の材料"}
ENGINE_KEYS = {*ENGINE_MARKS, "other_materials", "modern_substitutes"}
assert dict(ways.LABELS) == ENGINE_MARKS and set(ways.of_hypothesis(data, hyp(TORA, "H-A"))) == ENGINE_KEYS
print("ok")
