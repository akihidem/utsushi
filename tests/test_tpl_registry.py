"""雛形の受け口を 1 か所にまとめる（本人「なるべく並列ですべて作ろう」、11-04）。templates/ に 1 本の .py を置けば、共有のファイルを直さずに
型紙・記録・次の版・台帳の式が通る。並列の線が共有のファイルでぶつからないための契約で、契約は docs/process/template-contract.md。"""
import pathlib

from omochae.compose import TEMPLATES
from omochae.metrics import ALLOWED, METRICS

here = pathlib.Path(__file__).resolve().parent.parent / "src/omochae/templates"
files = {p.stem for p in here.glob("*.py") if not p.stem.startswith("_")}
assert {t.__name__.rsplit(".", 1)[1] for t in TEMPLATES.values()} == files, "templates/ の全部が受け口に載る（手で書き足さない）"
assert list(TEMPLATES)[:2] == ["slider_fan", "pivot_counterweight"], "必須の 2 種が先頭のまま"

REQUIRED = ("ID", "SHEET_SET", "DEFAULTS", "RANGES", "HYP_KEY", "RESULTS", "title", "spec", "check_range", "check_physics",
            "parts", "place", "bom", "materials", "steps", "measures", "diagram")
for tid, tpl in TEMPLATES.items():
    missing = [a for a in REQUIRED if not hasattr(tpl, a)]
    assert not missing, (tid, missing)
    assert tpl.HYP_KEY in tpl.DEFAULTS, (tid, "仮説を分ける寸法（HYP_KEY）に既定の値がある")
    assert tid in METRICS and tid in ALLOWED and ALLOWED[tid], (tid, "台帳の式と変えてよい寸法が要る（F7）")
    assert ALLOWED[tid] <= set(tpl.RANGES), (tid, "変えてよい寸法は範囲の検査がある物だけ")
print("ok")
