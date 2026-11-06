"""対応する一番古い Python（3.11）で開けない書き方を入れない（#311）。

README と init.sh は 3.11 以上を対応とする。手元の .venv は新しい版なので、3.11 だけで落ちる書き方は、ほかの試験を素通りする。
3.12 から f 文字列の式の中に、逆斜線・外と同じ引用符・改行・注釈を書けるようになった。3.11 では構文の誤りで、一覧と玩具の頁が開かない。

2 段で見る:
- 手元に 3.11 の解釈系があれば、それで全部のファイルを compile し、頁の部品を import する。実物なので一番確か。
  足しには行かない（init.sh が Python を黙って足さないのと同じ）。
- 無い機械でも落ちるよう、今の解釈系の字句の切り出しで同じ形を探す。ast では見分けられない（新しい版の文法で読むので、
  feature_version を渡しても通る）。字句の読みが実物と合う事は、見本の表を 3.11 にも読ませて確かめる。
"""
import io
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import tokenize

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

ROOT = pathlib.Path(__file__).resolve().parents[1]
# .venv-asr は声を字にする道具の環境（requirements-asr.txt の作り方で repo の根に作る）。他人の部品で、3.11 で読む対象でない
SKIP = {".venv", ".venv-asr", "out", "__pycache__"}
# （文, 3.11 で読めるか）
SAMPLES = [
    ("x = f'{\"\\n\".join(y)}'\n", False),  # 式の中の逆斜線
    ("x = f'''{\"\\n\".join(y)}'''\n", False),  # 三つの引用符でも逆斜線は読めない
    ("x = f'{d['a']}'\n", False),  # 外と同じ引用符
    ("x = f\"{'\"'}\"\n", False),  # 中の文字列に外の引用符が入る
    ("x = f'{f'{y}'}'\n", False),  # 入れ子の f 文字列が外と同じ引用符
    ("x = f'{\n y}'\n", False),  # 一つの引用符の式の中の改行
    ("x = f'''{\n y # 注\n}'''\n", False),  # 式の中の注釈
    ("x = f'{d[\"a\"]}'\n", True),
    ("x = f'''{d['a']}'''\n", True),  # 三つの引用符なら、一つの引用符は読める
    ("x = f'''{\n y}'''\n", True),  # 三つの引用符なら、改行も読める
    ("x = f'\\n{y}'\n", True),  # 式の外の逆斜線は前から書ける
    ("x = rf'\\d{y}'\n", True),
    ("x = f'{y!r:>{w}}'\n", True),
    ("x = f'{f\"{y}\"}'\n", True),
    ("x = '\\n' + \"'\"\n", True),  # f 文字列でない
]
# 3.11 の解釈系の中で回す。第三者の部品は入っていないので空の札で代える（見たいのは、こちらのコードが 3.11 で読めるか）
CHECK_311 = r"""
import importlib.abc, importlib.machinery, json, pathlib, sys, types
root, samples, skip = pathlib.Path(sys.argv[1]), json.loads(sys.argv[2]), set(json.loads(sys.argv[3]))
assert sys.version_info[:2] == (3, 11), sys.version
bad = []
for path in sorted(root.rglob("*.py")):
    name = path.relative_to(root)
    if skip & set(name.parts):
        continue
    try:
        compile(path.read_text(encoding="utf-8"), str(name), "exec")
    except SyntaxError as e:
        bad.append(f"{name}:{e.lineno}: {e.msg}")
for source, readable in samples:
    try:
        compile(source, "見本", "exec")
        got = True
    except SyntaxError:
        got = False
    if got is not readable:
        bad.append(f"見本の読みが字句の検査と違う: {source!r}")
if bad:
    sys.exit("\n".join(bad))

class Blank(types.ModuleType):
    __path__ = []
    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return type(name, (), {"__init__": lambda self, *a, **k: None})

class Third(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    NAMES = {"anthropic", "cairosvg", "drawsvg", "fontTools", "jsonschema", "PIL", "shapely"}
    def find_spec(self, name, path=None, target=None):
        return importlib.machinery.ModuleSpec(name, self) if name.partition(".")[0] in self.NAMES else None
    def create_module(self, spec):
        return Blank(spec.name)
    def exec_module(self, module):
        pass

sys.meta_path.insert(0, Third())
sys.path.insert(0, str(root / "src"))
import web.toys, web.toy
"""


def newer_forms(source):
    """3.11 で読めない f 文字列の行の番号。3.12 からの字句の切り出し（f 文字列を細かく切る）で見る。"""
    lines, outer = [], []  # outer は開いている f 文字列の引用符（外から順）。3.11 は外の引用符までを 1 つの文字列として読む
    for t in tokenize.generate_tokens(io.StringIO(source).readline):
        if t.type == tokenize.FSTRING_START:
            if outer and outer[0] in t.string:
                lines.append(t.start[0])
            outer.append(t.string.lstrip("rRfF"))
        elif t.type == tokenize.FSTRING_END:
            outer.pop()
        elif outer and not (t.type == tokenize.FSTRING_MIDDLE and len(outer) == 1):  # 外の f 文字列の字の部分は式でない
            if "\\" in t.string or outer[0] in t.string or t.type == tokenize.COMMENT or (t.type == tokenize.NL and len(outer[0]) == 1):
                lines.append(t.start[0])
    return sorted(set(lines))


def real_311():
    """手元の 3.11 の解釈系。無ければ None。"""
    if sys.version_info[:2] == (3, 11):
        return sys.executable
    found = shutil.which("python3.11")
    if found or not shutil.which("uv"):
        return found
    try:
        r = subprocess.run(["uv", "python", "find", "3.11", "--no-python-downloads"], capture_output=True, text=True, cwd=tempfile.gettempdir(), timeout=120)
    except subprocess.TimeoutExpired:
        return None
    return r.stdout.strip() if r.returncode == 0 else None


problems = []
if sys.version_info >= (3, 12):
    wrong = [source for source, readable in SAMPLES if bool(newer_forms(source)) is readable]
    assert not wrong, f"字句の検査の読みが見本と違う: {wrong}"
    files = [p for p in sorted(ROOT.rglob("*.py")) if not SKIP & set(p.relative_to(ROOT).parts)]
    assert any(p.name == "toys.py" for p in files) and len(files) > 100, "見る物が足りない"
    problems += [f"{p.relative_to(ROOT)}:{n}: 3.11 で読めない f 文字列" for p in files for n in newer_forms(p.read_text(encoding="utf-8"))]
python = real_311()
if python:
    r = subprocess.run([python, "-I", "-B", "-c", CHECK_311, str(ROOT), json.dumps(SAMPLES), json.dumps(sorted(SKIP))], capture_output=True, text=True)
    if r.returncode:
        problems.append(f"3.11 の解釈系で rc {r.returncode}:\n{r.stderr.strip()[-3000:]}")
assert not problems, "\n".join(problems)
print("ok（3.11 の解釈系でも見た）" if python else "ok（3.11 の解釈系が無いので、字句で見た）")
