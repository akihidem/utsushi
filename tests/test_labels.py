"""図鑑の文の印の試験。本物の歌は使わず、実データは形と数だけを見る。"""
import json
import pathlib
import subprocess
import sys
import tempfile

from omochae.labels import check, source_lines

ROOT = pathlib.Path(__file__).resolve().parents[1]


def floors(lines):
    return {f.floor for f in check(lines)}


def line(**kw):
    return {"text": "例の文", "label": "仮説", **kw}


# 正の場面: 3 分類のどれか。文言は見ない
assert not check([line(), line(label="観察"), line(label="原文の引用", checked_by="人", read_by="Claude")])
assert not check([line(label="原文の引用", transcribed_in="例の本 12 頁")])
# 負の場面: 印が無い、3 分類の外（飾りの文の印も持たない）
assert floors([{"text": "例の文"}]) == {"F6.label"}
assert floors([line(label="演出")]) == {"F6.label"}
assert floors([line(text=" ")]) == {"F6.label"}
# 負の場面: 裏付けの無い引用。Claude の読みは翻刻に数えず、読んだ者自身の確認も数えない
assert floors([line(label="原文の引用")]) == {"F6.label"}
assert floors([line(label="原文の引用", read_by="Claude", checked_by=None)]) == {"F6.label"}
assert floors([line(label="原文の引用", read_by="Claude", checked_by="Claude")]) == {"F6.label"}
assert floors([line(label="原文の引用", checked_by="  ")]) == {"F6.label"}
assert floors([line(label="原文の引用", read_by="Claude", transcribed_in="例の本 12 頁")]) == {"F6.label"}
# 文言は検査しない（本人の判断）。だから引用らしい文に仮説の印を付けても通る。この穴は J-016 に書いた
assert not check([line(text="原文の引用のように見える文")])

# 実データ: 人が確かめていない読みの数だけ落ちる。確認が入れば試験を直さず通る
sources = sorted((ROOT / "data/sources").glob("NDL-*.json"))
assert sources
for path in sources:
    source = json.loads(path.read_text(encoding="utf-8"))
    entries = source_lines(source)
    assert len(check(entries)) == sum(not e.get("checked_by") for e in entries), path.name


def run(*args):
    return subprocess.run([sys.executable, "-m", "omochae.labels", *args], capture_output=True, text=True)


with tempfile.TemporaryDirectory() as d:
    good, bad, broken = (pathlib.Path(d) / n for n in ("good.json", "bad.json", "broken.json"))
    good.write_text(json.dumps([line()]), encoding="utf-8")
    bad.write_text(json.dumps([{"text": "例の文"}]), encoding="utf-8")
    broken.write_text("{", encoding="utf-8")
    assert run("--file", str(good)).returncode == 0
    r = run("--file", str(bad))
    assert r.returncode == 3 and "FAIL F6.label" in r.stderr
    assert run("--file", str(broken)).returncode == 4
    assert run("--file", str(pathlib.Path(d) / "none.json")).returncode == 4
    # 一覧でなく 1 つの物を渡されたら、通さず検査できないとする
    good.write_text(json.dumps(line()), encoding="utf-8")
    assert run("--file", str(good)).returncode == 4
assert run().returncode == 4
assert run("--source", "NDL-none").returncode == 4
print("ok")
