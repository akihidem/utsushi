"""雛形の決まりを、全部の雛形について見る（#35）。新しい雛形を足した時、足りない物を名指しして落ちる。

登録は templates/ に置くだけなので、持つべき名前が欠けていても、その雛形を刷るまで誰も気づかない。
持つべき名前は compose・__main__・foldsim が読む物。場面は凍結の正（rc 0）と負（rc 3）が各 1 つ以上要る。
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
VALUES = ("ID", "FORM", "FORMS", "SOURCE", "DEFAULTS")
FUNCTIONS = ("check_range", "check_physics", "bom", "parts", "place", "materials", "title")


def problems(tpl, scenarios, sources):
    """1 つの雛形の足りない物を、文の並びで返す。scenarios は {(雛形, rc): 本数}、sources は出典の名前の組。"""
    name = getattr(tpl, "ID", tpl.__name__)
    out = [f"{name}: {key} が無い" for key in VALUES + FUNCTIONS if not hasattr(tpl, key)]
    out += [f"{name}: {key} が関数でない" for key in FUNCTIONS if hasattr(tpl, key) and not callable(getattr(tpl, key))]
    if not out:  # 名前がそろってから中身を見る（無い名前を読んで、別の例外で落ちないように）
        if tpl.FORM not in tpl.DEFAULTS:
            out.append(f"{name}: FORM の {tpl.FORM} が DEFAULTS に無い")
        by_form = getattr(tpl, "SOURCES", {})
        out += [f"{name}: SOURCES の {form} が FORMS に無い" for form in by_form if form not in tpl.FORMS]
        for form in tpl.FORMS:
            source = by_form.get(form, tpl.SOURCE)
            if source not in sources:
                out.append(f"{name}: 形 {form} の出典 {source} が data/sources に無い")
    for rc, label in ((0, "正"), (3, "負")):
        if not scenarios.get((name, rc)):
            out.append(f"{name}: 凍結の{label}の場面が無い（tests/frozen/scenarios に expect の rc が {rc} の物を足す）")
    return out


def check_all():
    from omochae.compose import TEMPLATES
    scenarios = {}
    for f in (ROOT / "tests/frozen/scenarios").glob("*.json"):
        d = json.loads(f.read_text(encoding="utf-8"))
        key = (d["template"], d["expect"]["rc"])
        scenarios[key] = scenarios.get(key, 0) + 1
    sources = {f.stem for f in (ROOT / "data/sources").glob("*.json")}
    return [line for tpl in TEMPLATES.values() for line in problems(tpl, scenarios, sources)]


found = check_all()
if found:
    sys.exit("\n".join(found))
if sys.argv[1:] == ["--only-contract"]:
    sys.exit(0)

# 今ある雛形を写した小さな tree に、足りない雛形を置いて、上の確かめが名指しして落ちる事を見る
SEED = "whistle"


def tree(base, edit, scenario=True):
    """whistle を写して ID を変えた雛形 zz_new を置き、この試験をその tree で回す。edit は雛形の文を変える関数。"""
    root = pathlib.Path(tempfile.mkdtemp(dir=base))
    shutil.copytree(ROOT / "src", root / "src", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(ROOT / "data/sources", root / "data/sources")
    shutil.copytree(ROOT / "tests/frozen", root / "tests/frozen")
    shutil.copy(pathlib.Path(__file__), root / "tests/test_template_contract.py")
    text = (ROOT / f"src/omochae/templates/{SEED}.py").read_text(encoding="utf-8")
    assert f'ID = "{SEED}"' in text
    (root / "src/omochae/templates/zz_new.py").write_text(edit(text.replace(f'ID = "{SEED}"', 'ID = "zz_new"')), encoding="utf-8")
    if scenario:
        one = json.loads(next((ROOT / "tests/frozen/scenarios").glob(f"{SEED}_neg*.json")).read_text(encoding="utf-8"))
        for rc in (0, 3):
            f = root / f"tests/frozen/scenarios/zz_new_{rc}.json"
            f.write_text(json.dumps({**one, "template": "zz_new", "expect": {"rc": rc, "floors": []}}), encoding="utf-8")
    env = {**os.environ, "PYTHONPATH": str(root / "src")}
    return subprocess.run([sys.executable, str(root / "tests/test_template_contract.py"), "--only-contract"], env=env, capture_output=True, text=True)


with tempfile.TemporaryDirectory() as base:
    same = lambda text: text
    # 足りない物が無ければ通る（下の落ち方が、写し方のせいでない事を見る）
    r = tree(base, same)
    assert r.returncode == 0, r.stderr
    # 名前を 1 つ欠くと、雛形と欠けた名前を言って落ちる
    for key in ("materials", "parts", "check_range"):
        r = tree(base, lambda text: text.replace(f"def {key}(", f"def {key}_gone("))
        assert r.returncode != 0 and f"zz_new: {key} が無い" in r.stderr, (key, r.returncode, r.stderr)
    # 値の名前も同じ
    r = tree(base, lambda text: text + "\ndel SOURCE\n")
    assert r.returncode != 0 and "zz_new: SOURCE が無い" in r.stderr, (r.returncode, r.stderr)
    # 場面が無いと落ちる（正と負の両方を言う）
    r = tree(base, same, scenario=False)
    assert r.returncode != 0 and "zz_new: 凍結の正の場面が無い" in r.stderr and "zz_new: 凍結の負の場面が無い" in r.stderr, r.stderr
    # 形の出典が無いと落ちる
    r = tree(base, lambda text: text + '\nSOURCE = "NDL-no-such"\nSOURCES = {}\n')
    assert r.returncode != 0 and "出典 NDL-no-such が data/sources に無い" in r.stderr, (r.returncode, r.stderr)
print("ok")
