"""demo.prepare の床: 撮る日の前の日の下ごしらえ（道具の確かめ・絵の取り寄せ・控え・網を切った書き出し）を見る。

網には出ない。取り寄せは差し替えた関数で、絵は小さな画像で代える。
"""
import contextlib
import http.client
import io
import json
import pathlib
import tempfile
import urllib.request

from PIL import Image

from demo import flip, prepare, scene2, scene3, scene4

# 道具: 足りない物を名前で返す。全部あれば空
assert prepare.missing_tools(which=lambda n: "/x/" + n, fonts="Noto Serif CJK JP") == []
miss = prepare.missing_tools(which=lambda n: None, fonts="DejaVu Sans")
for name in ("ffmpeg", "ffprobe", "pdftoppm", "google-chrome か chromium", "字 Noto Serif CJK JP"):
    assert name in miss, (name, miss)
# chromium だけあれば chrome の分は足りる（場面 3・6 が両方を探す）
only_chromium = prepare.missing_tools(which=lambda n: "/x/" + n if n != "google-chrome" else None, fonts="Noto Serif CJK JP")
assert only_chromium == [], only_chromium

with tempfile.TemporaryDirectory() as tmp:
    tmp = pathlib.Path(tmp)
    cache, sources = tmp / "cache", tmp / "sources"

    # 取り寄せる絵: 場面 1・2・4 の頁（cache）と、場面 3 の図（out/sources）。場面が読むのと同じ置き場の名前
    want = prepare.wanted(cache, sources)
    paths = {w["path"] for w in want}
    assert cache / f"{flip.PAGE}.jpg" in paths
    assert cache / "1187053-R0000005-2400.jpg" in paths
    for pid in scene4.load_records()["pages"]:
        assert cache / f"{pid}.jpg" in paths, pid
    assert sources / f"{scene3.SID}.jpg" in paths
    # 6 枚目は案内役の頁（北斎漫画 1 編 R0000013。本人の決定 11-06 で足した）
    assert len(want) == len(paths) == 6 and all(w["url"].startswith("https://") for w in want)

    def image_bytes(color):
        buf = io.BytesIO()
        Image.new("RGB", (8, 8), color).save(buf, "JPEG")
        return buf.getvalue()

    def good_fetch(url, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(image_bytes((len(url) % 255, 0, 0)))
        return path

    # 取り寄せて控えを残す。控えには大きさとハッシュが入る
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        assert prepare.fetch_all(cache, sources, good_fetch) == 0, err.getvalue()
    manifest = json.loads((cache / "manifest.json").read_text(encoding="utf-8"))
    assert sorted(manifest["files"]) == sorted(w["label"] for w in want)
    assert all(v["bytes"] > 0 and len(v["sha256"]) == 64 for v in manifest["files"].values())
    # 控えと合っている間は、網なしの確かめが通る
    assert prepare.verify(cache, sources) == []

    # 1 枚消えたら名指しする。変わった物も名指しする
    victim = cache / f"{flip.PAGE}.jpg"
    victim.unlink()
    assert any(flip.PAGE in line and "無い" in line for line in prepare.verify(cache, sources))
    good_fetch("https://changed.example/", victim)
    got = prepare.verify(cache, sources)
    assert any(flip.PAGE in line for line in got) and all("無い" not in line for line in got), got

    # 取れない絵は、取れなかった URL を名指しして 4。控えは書き直さない
    before = (cache / "manifest.json").read_text(encoding="utf-8")

    def bad_fetch(url, path):
        raise OSError("接続できない")

    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        assert prepare.fetch_all(cache, sources, bad_fetch, force=True) == 4
    assert "接続できない" in err.getvalue() and "https://" in err.getvalue()
    assert (cache / "manifest.json").read_text(encoding="utf-8") == before

    # 通信の途中で切れた時（OSError でない例外）も、トレースバックの 1 でなく名指しで 4
    def cut_fetch(url, path):
        raise http.client.IncompleteRead(b"")

    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        assert prepare.fetch_all(cache, sources, cut_fetch) == 4
    assert "https://" in err.getvalue()

    # 控えが無い置き場は、網なしの確かめが 4 で言う
    empty = tmp / "empty"
    assert any("控え" in line for line in prepare.verify(empty, sources))

# 網を切る: 外への取り寄せは止まって理由を言い、手元の口（場面 3 の画面）は通す
calls = []
real = urllib.request.urlopen
urllib.request.urlopen = lambda url, *a, **k: calls.append(url) or "ok"
try:
    with prepare.offline():
        try:
            urllib.request.urlopen("https://dl.ndl.go.jp/x.jpg", timeout=1)
        except OSError as e:
            assert "網を切っている" in str(e) and "dl.ndl.go.jp" in str(e)
        else:
            raise AssertionError("網を切っているのに外へ出た")
        assert urllib.request.urlopen("http://127.0.0.1:8123/", timeout=1) == "ok"
        assert urllib.request.urlopen("http://localhost:8123/", timeout=1) == "ok"
    assert calls == ["http://127.0.0.1:8123/", "http://localhost:8123/"], calls
    assert urllib.request.urlopen("https://dl.ndl.go.jp/y.jpg") == "ok", "切った網は戻る"
finally:
    urllib.request.urlopen = real

# 写しがあれば、網を切っていても場面が頁を読める（取り寄せ済みの写しだけで書き出せる、の足場）
with tempfile.TemporaryDirectory() as tmp:
    cache = pathlib.Path(tmp)
    Image.new("L", (40, 30), 200).save(cache / f"{flip.PAGE}.jpg")
    Image.new("L", (40, 30), 200).save(cache / "1187053-R0000005-2400.jpg")
    with prepare.offline():
        page, _ = flip.load_page(cache)
        assert page is not None and page.size == (40, 30)
        rec, _src = scene2.load_record()
        assert scene2.load_page(cache, rec) is not None

# fc-match 自体が無い機械でも、場面を読み込んだだけで落ちない（トレースバックの 1 でなく、道具の確かめが名前で 4 を返す）
import subprocess

real_run = subprocess.run


def no_fc_match(*a, **k):
    raise FileNotFoundError(2, "No such file or directory", "fc-match")


subprocess.run = no_fc_match
try:
    assert flip._font("Noto Serif CJK JP") == ""
finally:
    subprocess.run = real_run

# 場面が 1 つ読めなくても、入口の読み込みでは落ちない（demo.build が「場面が無い」と 4 で言い、--partial で飛ばす道を残す）。
# 別のプロセスで見るのは、この試験がもう場面を読み込んでいるため。
import os
import sys

code = """
import json, pathlib, sys, tempfile
sys.modules['demo.scene3'] = None
from demo import build, prepare
d = pathlib.Path(tempfile.mkdtemp())
(d / prepare.MANIFEST).write_text(json.dumps({"files": {}}), encoding="utf-8")
wrong = prepare.verify(d, d)
assert any("読み込めない" in line for line in wrong), wrong
assert prepare.fetch_all(d, d, lambda u, p: p) == 4
print("ok-import")
"""
r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=dict(os.environ))
assert r.returncode == 0 and "ok-import" in r.stdout, r.stdout + r.stderr
print("ok")
