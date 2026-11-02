"""台帳の試験。今の repo が通る事と、根拠が消えた時に狙った検査で落ちる事を見る。"""
import json
import pathlib
import shutil
import tempfile

from omochae import ledger

assert ledger.check() == [], [f.line() for f in ledger.check()]

tmp = pathlib.Path(tempfile.mkdtemp()) / "r"
shutil.copytree(ledger.ROOT / "docs", tmp / "docs")
for f in ("README.md", "CLAUDE.md", "run.sh"):
    shutil.copy(ledger.ROOT / f, tmp / f)
for sub in ("src", "tests", "data/hypotheses"):
    shutil.copytree(ledger.ROOT / sub, tmp / sub, ignore=shutil.ignore_patterns("__pycache__"))
ledger.ROOT = tmp
assert ledger.check() == []


def floors():
    return {f.floor for f in ledger.check()}


def edit(path, fn):
    p = tmp / path
    before = p.read_text(encoding="utf-8")
    p.write_text(fn(before), encoding="utf-8")
    got = floors()
    p.write_text(before, encoding="utf-8")
    return got


# 根拠の文が消えると落ちる。ファイルが残っていても通さない
assert edit("docs/process/research/03-mechanism-dimensions.md", lambda t: t.replace("20mm 足りない", "足りる")) == {"L.claims"}
assert edit("docs/process/decisions/J005-axle-default.md", lambda t: t.replace("実物で試すまで確定しない", "確定")) == {"L.open"}
# 索引に無い記録、地図の手直し、要約の片方だけの変更
new = tmp / "docs/process/decisions/J999-x.md"
new.write_text("# x\n", encoding="utf-8")
assert floors() == {"L.index"}
new.unlink()
assert edit("docs/process/README.md", lambda t: t.replace("| 1 | [", "| 1 | [x", 1)) >= {"L.index"}
assert edit("CLAUDE.md", lambda t: t.replace("**輪**", "**循環**", 1)) == {"L.summary"}
# 台帳: 進行中なのに根拠が無い、知らない状態
def features(fn):
    return edit("docs/features.json", lambda t: json.dumps(fn(json.loads(t)), ensure_ascii=False))


assert features(lambda d: [{**d[0], "evidence": []}, *d[1:]]) == {"L.features"}
assert features(lambda d: [{**d[0], "status": "ほぼ"}, *d[1:]]) == {"L.features"}
assert edit("docs/process/how-it-was-built.md", lambda t: t + "\n[x](無い.md)\n") == {"L.links"}
