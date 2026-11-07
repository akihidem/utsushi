"""README に書いた命令を、書いたとおりに打って動くかを見る。

なぜ要るか: README の命令の字は、どの試験も見ていなかった。まっさらな環境で上から順に打つと、python の名前が無い機械で
止まる字と、PYTHONPATH の抜けが見つかった（#92）。コードと README を別の人が直すので、字が古くなっても誰も気づかない。

何を見るか（repo の複製の上で打つ。本物の out・local・版の台帳を汚さない）:
1. 囲みの中の命令を、README の順に、字のまま bash で打つ。.venv/bin/python だけを今の解釈系に置き換える。
   rc は 0（断るのが正しい行だけ RC に書く）。新しい行を README に足すと、そのまま見る物が増える
2. 手で打つ形の命令は .venv/bin/python で始める。python の名前が無い機械でも打てるように
3. 検査だけを回す Python の塊の出力が、README の例と同じ
4. 命令に出てくる入口は、誤った呼び方で 4（README の「1 と 2 は使わない」）
5. README の手順で repo が汚れない。書き換わるのは、release が刻む版の台帳だけ

打たない行: 道具を入れる行（機械を変える）・./init.sh と ./run.sh（この試験は run.sh の中で回る）・intake serve（止まらないので --help だけ）。
"""
import ast
import json
import os
import pathlib
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text(encoding="utf-8")
PY = ".venv/bin/python"
SETUP = ("sudo ", "pipx ", "export ")
SELF = ("./init.sh", "./run.sh")
FORMS = (f"{PY} ", f"PYTHONPATH=src {PY} ")
# 人が決める字の置き換え。<ID> は形の合った、受付箱に無い番号。
PLACEHOLDER = {"<人>": "試す人", "<番号>": "abc1234", "<組の名>": "goraigo-test", "<ID>": "B-00000000-000000-00000000"}
# <案の番号> は、README の束を受けた時に起きる最初の案の番号。案の番号は台帳（git の中）の番号の次から振るので、台帳から数える
# （台帳に採った案がある間は EP-0001 にならない。決まった番号を README に書くと、台帳が育つたびに例が外れる）。
_LEDGER = json.loads((ROOT / "data/engine/versions.json").read_text(encoding="utf-8"))
_TAKEN = [int(p["id"][3:]) for v in _LEDGER["versions"] for p in v.get("proposals", [])] + [int(p["id"][3:]) for p in _LEDGER.get("next", [])]
PLACEHOLDER["<案の番号>"] = f"EP-{max(_TAKEN, default=0) + 1:04d}"
# 受け入れは端末で人が ID を打つ。端末の無いこの試験では、断るのが正しい。
RC = {"omochae.intake review accept": 3}
WRITES = ("out/fan_tab.svg", "out/fan_tab.pdf", "out/fan_tab.png", "out/tiger.pdf",
          *(f"out/foldsim/slider_fan_{part}_foldsim.svg" for part in ("tube", "pusher", "base", "fan")))
LIMIT = 120  # 1 つの命令の時間切れ（秒）。試験 1 本の上限（./run.sh の 300 秒）の内に、止まった命令を名指しする


def fenced(text):
    """囲みの中の命令の行を順に返す。行の全部が注釈の物は除く。"""
    out = []
    for block in re.findall(r"^```(?:bash|sh)\n(.*?)^```", text, re.S | re.M):
        out += [ln.strip() for ln in block.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    return out


def inline(text):
    """囲みの外の字の塊のうち、python を呼ぶ物。"""
    outside = re.sub(r"^```.*?^```", "", text, flags=re.S | re.M)
    return re.findall(r"`([^`\n]*\bpython\b[^`\n]*)`", outside)


def bare(text):
    """python の名前で始まる、打つ形の命令。`python -m omochae` のように入口の名前を指すだけの字は、打つ形でないので除く。"""
    spans = [s for s in [*fenced(text), *inline(text)] if s.startswith("python ")]
    return [s for s in spans if not re.fullmatch(r"python -m [\w.]+", s)]


def typed(line):
    """打つ字に直す。置き換えの字は決めた物だけ（新しい字が増えたら、ここで名指しする）。"""
    for k, v in PLACEHOLDER.items():
        line = line.replace(k, v)
    unknown = re.findall(r"<[^<>\s]+>", line.split(" # ")[0])
    assert not unknown, ("置き換えの字が決まっていない。PLACEHOLDER に足す", unknown, line)
    return line.replace(PY, shlex.quote(sys.executable))


def expected(line):
    return next((rc for key, rc in RC.items() if key in line), 0)


# 負の対照: 字を見る形が、古い字を拾う事を確かめる（拾わない検査は、通っても意味が無い）
assert bare("`python -m omochae --help`") == ["python -m omochae --help"]
assert bare("`python tests/run_floors.py --write-manifest`") == ["python tests/run_floors.py --write-manifest"]
assert bare("```bash\npython -m omochae --help\n```\n") == ["python -m omochae --help"]
assert bare("`python -m omochae.fold3d` の検査") == [] and bare(f"`PYTHONPATH=src {PY} -m omochae --help`") == []
assert fenced("```bash\n# 注釈\necho a   # 説明\n\n```\n```json\n{}\n```\n") == ["echo a   # 説明"]
try:
    typed(f"{PY} -m omochae --by <知らない>")
except AssertionError:
    pass
else:
    raise SystemExit("知らない置き換えの字を拾わなかった")
assert typed(f"{PY} -m x  # show <知らない> で見る").endswith("# show <知らない> で見る"), "注釈の中の字は見ない"
assert expected("x -m omochae.intake review accept y") == 3 and expected("x -m omochae.ways") == 0

# 2. 打つ形の字
assert not bare(README), ("python の名前で始まる命令が README にある。.venv/bin/python で始める", bare(README))
lines = fenced(README)
assert len(lines) > 20, "命令の行を読めていない"
unknown = [ln for ln in lines if not ln.startswith((*SETUP, *SELF, *FORMS, "echo "))]
assert not unknown, ("README に知らない形の命令がある", unknown)
for name in SELF:
    assert os.access(ROOT / name, os.X_OK), (name, "実行できない")
# 特別に扱う行が README から消えたら、扱いの方が古い
for key in (*RC, "omochae.intake serve"):
    assert any(key in ln for ln in lines), ("README に無い行を特別に扱っている", key)

ENV = {k: v for k, v in os.environ.items() if not k.startswith(("OMOCHAE_", "GIT_")) and k != "PYTHONPATH"}
GIT_ENV = {**ENV, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}  # 使う人の git の設定を読まない
tmp = tempfile.TemporaryDirectory()
repo = pathlib.Path(tmp.name) / "r"
shutil.copytree(ROOT, repo, ignore=shutil.ignore_patterns(".git", ".venv", "out", "local", "__pycache__", "lane-issues", "LANE-*.md"))


def shell(line):
    try:
        return subprocess.run(["bash", "-c", line], cwd=repo, env=ENV, capture_output=True, text=True, timeout=LIMIT)
    except subprocess.TimeoutExpired:
        raise SystemExit(f"検査できない: {LIMIT} 秒で終わらない命令: {line}")


git = shutil.which("git")
if git:  # README の手順で何が変わるかを、打つ前の木と比べる
    for cmd in (["init", "-q"], ["add", "-A"], ["-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", "before"]):
        subprocess.run(["git", *cmd], cwd=repo, env=GIT_ENV, check=True, capture_output=True)

# 1. 囲みの中の命令を順に打つ
ran = 0
for line in lines:
    if line.startswith((*SETUP, *SELF)):
        continue
    # 開いたまま止まらない口は、呼べる事だけを見る
    r = shell(typed(line.split(" # ")[0].rstrip() + " --help" if "omochae.intake serve" in line else line))
    assert r.returncode == expected(line), (line, r.returncode, r.stdout[-300:], r.stderr[-300:])
    assert "Traceback" not in r.stderr, (line, r.stderr[-300:])
    ran += 1
for name in WRITES:
    assert (repo / name).is_file() and (repo / name).stat().st_size > 0, (name, "README の言う物ができていない")

# 囲みの外の、打つ形の字（--help と照合の表）。名前だけの `PYTHONPATH=src .venv/bin/python` は打たない
table = repo / "tests/frozen/manifest.json"
manifest = table.read_bytes()
spans = [s for s in inline(README) if s.startswith(FORMS)]
assert any("--help" in s for s in spans) and any("--write-manifest" in s for s in spans), spans
for span in spans:
    r = shell(typed(span))
    assert r.returncode == 0, (span, r.returncode, r.stderr[-300:])
    ran += 1
# 表を書き直しても、場面と基準は変わらない。試験の名の一覧だけは、試験を足す PR で増えるので見ない（並んで動く線を止めないため）
now, was = json.loads(table.read_text(encoding="utf-8")), json.loads(manifest)
assert {k: v for k, v in now.items() if k != "tests"} == {k: v for k, v in was.items() if k != "tests"}, "照合の表を書き直すと、場面か基準が変わる"
table.write_bytes(manifest)

# 3. 検査だけを回す Python の塊
block = re.search(r"^```python\n(.*?)^```", README, re.S | re.M).group(1)
said = "\n".join(ln[2:] for ln in block.splitlines() if ln.startswith("# "))
code = "\n".join(ln for ln in block.splitlines() if not ln.startswith("# "))
r = subprocess.run([sys.executable, "-c", code], cwd=repo, env={**ENV, "PYTHONPATH": "src"}, capture_output=True, text=True, timeout=LIMIT)
assert r.returncode == 0 and ast.literal_eval(r.stdout) == ast.literal_eval(said), (r.returncode, r.stdout, r.stderr[-300:])

# 4. 命令に出てくる入口は、誤った呼び方で 4
entries = sorted(set(re.findall(r"-m (omochae(?:\.\w+)?)", "\n".join(lines))))
assert len(entries) >= 7 and "omochae.ways" in entries, entries
for mod in entries:
    r = shell(f"PYTHONPATH=src {shlex.quote(sys.executable)} -m {mod} --nope")
    assert r.returncode == 4 and "Traceback" not in r.stderr, (mod, r.returncode, r.stderr[-300:])

# 5. README の手順で repo が汚れない。書き換わるのは release が刻む版の台帳だけ
if git:
    status = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=repo, env=GIT_ENV, capture_output=True, text=True, check=True).stdout
    assert status.splitlines() == [" M data/engine/versions.json"], ("README の手順で repo が汚れた", status)

tmp.cleanup()
print(f"ok README の命令 {ran} 本を打った（入口 {len(entries)} つ）")
