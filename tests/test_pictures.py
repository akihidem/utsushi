"""全部の玩具に図（原図の切り出し）の出典がある。通信はしない。

なぜ: 本人の指示（11-05）「図がないおもちゃは図を入れて」。写し（out/sources）は git の外なので、まっさらな clone には無い。
頁が図を出せるかは、仮説を置いた玩具の全部に出典の記録があり、その記録に NDL の切り出しの URL と箱がある事で決まる。
ここではその線と、写しを取る道具（ingest.fetch_images）が 1 枚の失敗で残りを捨てない事を見る。
箱が玩具を正しく囲むかは機械では見られない（作る側が全コマの写しに箱を描いて目で確かめた。research/26。人の確認はまだ）。
"""
import json
import pathlib
import re
import tempfile

from omochae import ingest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PCT = re.compile(r"^pct:(\d+(?:\.\d+)?),(\d+(?:\.\d+)?),(\d+(?:\.\d+)?),(\d+(?:\.\d+)?)$")

inventory = {t["id"]: t for t in json.loads((ROOT / "data/inventory/edo-nishiki.json").read_text(encoding="utf-8"))["toys"]}
sids = sorted(p.stem for p in (ROOT / "data/hypotheses").glob("NDL-*.json"))
assert sids, "仮説の記録が無い"

for sid in sids:
    rec_path = ROOT / "data/sources" / f"{sid}.json"
    assert rec_path.exists(), (sid, "出典の記録が無い")
    rec = json.loads(rec_path.read_text(encoding="utf-8"))
    m = PCT.match(rec["crop_region"])
    assert m, (sid, rec["crop_region"])
    x, y, w, h = (float(v) for v in m.groups())
    # 箱は見開きの中にあり、空でない
    assert 0 <= x < 100 and 0 <= y < 100 and w > 0 and h > 0 and x + w <= 100 and y + h <= 100, (sid, rec["crop_region"])
    # 写しの URL は NDL の IIIF で、箱と同じ切り出し（頁の図は常に出典の記録の箱と同じ所を見せる）
    assert rec["image_url"] == f"https://dl.ndl.go.jp/api/iiif/1187053/R{rec['canvas']:07d}/{rec['crop_region']}/1600,/0/default.jpg", (sid, rec["image_url"])
    # 箱の出所は棚卸し（必須の 2 種は半頁の箱で、ingest.TARGETS が持つ）
    expect = ingest.TARGETS[sid]["region"] if sid in ingest.TARGETS else inventory[sid]["region"]
    assert rec["crop_region"] == expect, (sid, rec["crop_region"], expect)
    assert rec["rights"] == "PDM", sid

# 写しを取る対象は、仮説を置いた玩具の全部
assert set(ingest.image_targets()) == set(sids)

# 1 枚取れなくても残りを取り、取れなかった分だけを返す。2 回目は足りない分だけを取る
root = pathlib.Path(tempfile.mkdtemp())
calls = []


def fake_get(url):
    calls.append(url)
    if url.endswith("/b.jpg"):
        raise OSError("timeout")
    return b"jpg"


ingest.ROOT, ingest._get = root, fake_get
targets = {k: f"https://x/{k}.jpg" for k in ("a", "b", "c")}
assert ingest.fetch_images(targets) == ["b"]
assert (root / "out/sources/a.jpg").exists() and (root / "out/sources/c.jpg").exists() and not (root / "out/sources/b.jpg").exists()
ingest._get = lambda url: b"jpg"
calls.clear()
assert ingest.fetch_images(targets) == []
assert (root / "out/sources/b.jpg").exists()
assert ingest.fetch_images(targets) == []  # 全部そろっていれば通信しない
print("ok: 全部の玩具に図の出典がある", len(sids))
