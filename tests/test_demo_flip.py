"""デモ動画の場面 1（demo.flip）の床: 出所の記録がそろい、1 コマが時刻だけで決まる事を見る。

画像は取りに行かない（試験を網につながずに回すため）。頁の代わりに、黒い四角を置いた紙で描く。
"""
import json
import pathlib

from PIL import Image, ImageDraw

from demo import flip

rec_all = json.loads(flip.FIGURES.read_text(encoding="utf-8"))
rec = rec_all["pages"][flip.PAGE]

# 出所: PDM と所蔵と改変の文が無ければ、動画の隅の札が書けない
for k in ("persistent_id", "iiif", "rights", "rights_basis", "attribution", "modification_note", "title", "publication"):
    assert rec.get(k), k
assert rec["rights"] == "PDM" and "国立国会図書館" in rec["attribution"]
assert rec["iiif"].startswith("https://dl.ndl.go.jp/api/iiif/")
# 枠は頁の中に収まり、名前が重ならない
ids = [f["id"] for f in rec["figures"]]
assert len(ids) == len(set(ids)) == 18
for f in rec["figures"]:
    x, y, w, h = f["box_pct"]
    assert 0 <= x and 0 <= y and w > 0 and h > 0 and x + w <= 100 and y + h <= 100, f

# 合図の表は時刻の順で、動画の長さの中
spans = list(flip.CUES.values())
assert all(a < b for a, b in spans) and spans == sorted(spans) and spans[-1][1] <= flip.DURATION
# 締めの字幕は現れた後に止めて読ませる（動画の初めと終わりに出す字幕なので。出きると同時に場面が替わると読めない）
assert flip.DURATION - flip.CUES["closing"][1] >= 2.0

# 偽の頁: 枠ごとに黒い四角（人物の代わり）
page = Image.new("L", (1400, 1200), 255)
d = ImageDraw.Draw(page)
for f in rec["figures"]:
    x, y, w, h = f["box_pct"]
    d.rectangle((x * 14 + 10, y * 12 + 10, (x + w) * 14 - 10, (y + h) * 12 - 10), fill=0)
scene = flip.Scene(page, rec)
assert len(scene.order) == 18 and scene.order[0].startswith("R"), "和本の順で、右の頁から"
for t in (0.5, 4.0, 8.0, 14.0):
    a, b = scene.frame(t), scene.frame(t)
    assert a.size == (flip.W, flip.H) and a.tobytes() == b.tobytes(), t
# 重ねる段では、人物が入れ替わる（同じ絵が続かない）
f0 = flip.CUES["flip"][0] + 0.5
assert scene.frame(f0).tobytes() != scene.frame(f0 + 1 / flip.FLIP_FPS).tobytes()
# 字: 無い字の名を引くと、別の字を黙って使わずに空を返す（render が 4 で止める）
assert flip._font("No Such Font Zz") == ""
assert flip.SERIF and flip.SERIF_BOLD
print("ok")
