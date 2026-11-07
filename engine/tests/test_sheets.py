"""玩具 1 つに型紙 1 枚（omochae.sheets・制作者の決定 2026-11-05）を確かめる。"""
import json
import pathlib
import sys
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from omochae import sheets, ways  # noqa: E402
from omochae.compose import TEMPLATES  # noqa: E402

# 1. 表の形: 雛形と形は在る物だけ。別の読みが指す型紙の形は、同じ出典の型紙（別の読みを別の読みに向けない）
for tid, m in sheets.READINGS.items():
    assert tid in TEMPLATES, tid
    forms = {str(f) for f in TEMPLATES[tid].FORMS}
    for alt, sheet in m.items():
        assert alt in forms and sheet in forms and alt != sheet, (tid, alt, sheet)
        assert sheets.is_sheet(tid, sheet), (tid, sheet)
        assert sheets.source_of(tid, alt) == sheets.source_of(tid, sheet), (tid, alt, sheet)

# 2. 玩具（雛形と出典の組）ごとに、型紙はちょうど 1 枚。描かれた物が違う形（stand_figure の凧・土人形）は別の玩具なので、
#    同じ出典に型紙が幾つかある。その組は、型紙になる形の集まりまで名指しで許す（組ごと許すと、その出典に誤って足した形で
#    型紙が増えても見えなかった）
DIFFERENT_TOYS = {("stand_figure", sheets.source_of("stand_figure", "tako_ji")): {"tako_ji", "tako_oni"},
                  ("stand_figure", sheets.source_of("stand_figure", "tsuchi_usagi")): {"tsuchi_usagi", "tsuchi_kame", "tsuchi_hato"}}
groups = defaultdict(list)
for tid, tpl in TEMPLATES.items():
    for f in tpl.FORMS:
        groups[(tid, sheets.source_of(tid, f))].append(str(f))
for key, forms in groups.items():
    got = {f for f in forms if sheets.is_sheet(key[0], f)}
    if key in DIFFERENT_TOYS:
        assert got == DIFFERENT_TOYS[key], (key, sorted(got))
    else:
        assert len(got) == 1, (key, forms)
assert set(DIFFERENT_TOYS) <= set(groups)  # 名指しした組が、雛形の変更で消えていない

# 3. 制作者の決定のたたき台（御来迎は内筒を下から押し上げる形 rise（2026-11-06）、首振り虎は元の repo の H-A）。必須 2 種の紙は、
#    そのたたき台で刷る場面。御来迎の rise には凍結の場面が無い（凍結の置き場は足さない）ので examples/goraigo_v14.json で刷る。
#    pos_tab（既定の tab）は別の読みの場面
assert sheets.is_sheet("slider_fan", "rise") and sheets.is_sheet("pivot_counterweight", "neck")
assert not any(sheets.is_sheet("slider_fan", f) for f in ("tab", "tube", "stick", "lift"))
assert not sheets.is_sheet("pivot_counterweight", "hang")
# 必須 2 種の場面は sheets.REQUIRED の 1 つの表。場面ごとに、その玩具の場面で、形がその玩具の型紙の 1 枚である事を見る
# （上の 2 行で、御来迎の型紙は rise、虎は neck と決まっているので、場面が別の形や別の玩具に書き替わると落ちる）
assert set(sheets.REQUIRED) == {"slider_fan", "pivot_counterweight"}
for tid, rel in sheets.REQUIRED.items():
    sc = json.loads((ROOT / rel).read_text(encoding="utf-8"))
    tpl = TEMPLATES[sc["template"]]
    form = sc["params"].get(tpl.FORM, tpl.DEFAULTS[tpl.FORM])
    assert sc["template"] == tid and sheets.is_sheet(tid, form), (rel, sc["template"], form)

# 4. 一覧（サイトが使う）: 行は全部の形のまま。sheet と reading_of と source_id が付き、sheet の行は玩具ごとに 1 つ
table = ways.table()
assert len(table) == sum(len(t.FORMS) for t in TEMPLATES.values())
assert all({"sheet", "reading_of", "source_id"} <= set(r) for r in table)
assert {(r["template"], r["form"]) for r in table if not r["sheet"]} == {(t, a) for t, m in sheets.READINGS.items() for a in m}
assert all((r["reading_of"] is None) == r["sheet"] for r in table)
print("ok")
