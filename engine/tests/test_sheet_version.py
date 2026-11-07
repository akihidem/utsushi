"""型紙の題に刷る版の番号（決める側の決定 2026-11-07「紙の題の版も見本に番号を持たせる形で」。虎 v7 は版 7、撮影中の v6 は変えない、
御来迎 v14 は版 14 で刷り直す）を確かめる。

なぜ: 見本から版の番号を渡しておらず、どの版の紙の題も「版 1」だった。サイトで型紙の版（v7 など）を出しても、紙と食い違った。
次を見る:
1. 題の版は --version が先、無ければ場面の version、どちらも無ければ 1。
2. 見本の虎 v7 は 7、御来迎 v14 は 14 を持つ。撮影中の虎 v6 は持たない（刷った紙の題は前の「版 1」のまま）。
3. 入口で刷った紙（PDF の字）の題に、その版が出る（虎 v7 は「版 7」、御来迎 v14 は「版 14」、虎 v6 は「版 1」、--version 3 は「版 3」）。
4. 版は 1 以上の整数に限る。場面の version が null・字・0・負の数・小数・真偽の値なら、刷らずに 4（呼び方の誤り）。
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile
from types import SimpleNamespace

from omochae.__main__ import sheet_version

ROOT = pathlib.Path(__file__).resolve().parents[1]
ex = lambda n: json.loads((ROOT / f"examples/{n}.json").read_text(encoding="utf-8"))

# 1. 版の番号の決め方
assert sheet_version(SimpleNamespace(version=None), {"version": 7}) == 7
assert sheet_version(SimpleNamespace(version=3), {"version": 7}) == 3
assert sheet_version(SimpleNamespace(version=None), {}) == 1
# 1 以上の整数のほかは呼び方の誤り（見直しの指摘: null・字・負の数がそのまま刷られた）
from omochae.model import ToolMissing  # noqa: E402
for bad in (None, "7", 0, -2, 7.0, True):
    for args, sc in ((SimpleNamespace(version=None), {"version": bad}), (SimpleNamespace(version=bad), {})):
        if args.version is None and "version" not in sc:
            continue  # --version も場面の version も無い時は 1（上で見た）
        try:
            sheet_version(args, sc)
        except ToolMissing:
            continue
        raise AssertionError((bad, args, sc))

# 2. 見本の版
assert ex("tora_v7")["version"] == 7 and ex("goraigo_v14")["version"] == 14
assert "version" not in ex("tora_v6")  # 撮影中の v6 は変えない

# 3. 刷った紙の題
env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
with tempfile.TemporaryDirectory() as tmp:
    for name, extra, want in (("tora_v7", [], "版 7"), ("goraigo_v14", [], "版 14"), ("tora_v6", [], "版 1"), ("tora_v7", ["--version", "3"], "版 3")):
        out = pathlib.Path(tmp) / f"{name}_{want.split()[1]}"
        r = subprocess.run([sys.executable, "-m", "omochae", "--scenario", str(ROOT / f"examples/{name}.json"), "--out", str(out), *extra],
                           cwd=ROOT, env=env, capture_output=True, text=True, timeout=300)
        assert r.returncode == 0, (name, r.stderr[-300:])
        text = subprocess.run(["pdftotext", str(out.with_suffix(".pdf")), "-"], capture_output=True, text=True, check=True).stdout
        title = next(line for line in text.splitlines() if "型紙" in line)
        assert title.rstrip().endswith(want), (name, extra, title)
    bad = pathlib.Path(tmp) / "bad.json"
    bad.write_text(json.dumps(dict(ex("tora_v7"), version=None)), encoding="utf-8")
    r = subprocess.run([sys.executable, "-m", "omochae", "--scenario", str(bad), "--out", str(pathlib.Path(tmp) / "bad")],
                       cwd=ROOT, env=env, capture_output=True, text=True, timeout=300)
    assert r.returncode == 4 and "版" in r.stderr and not (pathlib.Path(tmp) / "bad.pdf").exists(), (r.returncode, r.stderr[-300:])
print("ok 型紙の題の版（虎 v7 は版 7・御来迎 v14 は版 14・撮影中の虎 v6 は版 1 のまま・1 以上の整数のほかは 4）")
