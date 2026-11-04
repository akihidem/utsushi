"""デモ動画の場面 4（demo.scene4）の床: 出所の記録がそろい、1 コマが時刻だけで決まり、組の版の札がコードから来る事を見る。

画像は取りに行かない（試験を網につながずに回すため）。北斎の頁の代わりに黒い四角の絵を、刷った紙の代わりに無地の絵を渡す。
型紙の配置（compose）だけは本物を使う。PDF を作らず速く、折り線が配置から引ける事をここで確かめられるため。
"""
import inspect

from PIL import Image, ImageDraw

from demo import scene4
from omochae.templates import slider_fan

recs = scene4.load_records()

# 出所: PDM と所蔵と改変の文が無ければ、動画の隅の札が書けない
for pid, rec in recs["pages"].items():
    for k in ("persistent_id", "iiif", "rights", "rights_basis", "attribution", "modification_note", "title", "short", "publication"):
        assert rec.get(k), (pid, k)
    assert rec["rights"] == "PDM" and "国立国会図書館" in rec["attribution"], pid
    assert rec["iiif"].startswith("https://dl.ndl.go.jp/api/iiif/"), pid
    assert "manifest" in rec["rights_basis"] and "PDM" in rec["rights_basis"], pid
    for c in rec["crops"]:
        x, y, w, h = c["box_pct"]
        assert 0 <= x and 0 <= y and w > 0 and h > 0 and x + w <= 100 and y + h <= 100, (pid, c)
assert set(recs["pages"]) == {"v3-R0000022", "v8-R0000011"}
assert recs["template"]["modification_note"]

# 合図の表は時刻の順で、動画の長さの中
spans = list(scene4.CUES.values())
assert all(a < b for a, b in spans) and spans == sorted(spans) and spans[-1][1] <= scene4.DURATION

# 型紙の配置（本物）から線を引く。折る線が無ければ「型紙の折り線へ」が映らない
hs = scene4.hypothesis_sheets(recs)
assert [h["letter"] for h in hs] == sorted(h["letter"] for h in hs) and len(hs) >= 2
source = scene4.source_record(recs)
example = next(h for h in hs if h["id"] == recs["template"]["example_hypothesis"])
layout, failures = scene4.template_layout(example, source)
assert not failures, [f.line() for f in failures]
segs = scene4.template_segments(layout)
kinds = {k for k, _, _ in segs}
assert {"cut", "valley"} <= kinds, kinds
# 手順の紙は「遊び方」の行より上で切る（扇の動かし方を先に見せない、F9）
tl, tf = scene4.tejun_layout(example, source)
assert not tf
crop, hide = scene4.tejun_view_mm(tl)
play = next(t for t in tl["texts"] if t.text == "遊び方")
assert crop[3] <= play.y and hide[0] > 0 and hide[3] == crop[3]

# 偽の絵: 北斎の切り出しの代わりに黒い四角、刷った紙の代わりに無地
edo = {}
for pid, rec in recs["pages"].items():
    for c in rec["crops"]:
        g = Image.new("L", (400, 300) if pid.startswith("v3") else (300, 420), 255)
        ImageDraw.Draw(g).rectangle((40, 40, 200, 200), fill=0)
        edo[f"{pid}/{c['id']}"] = g
tpl = {"sheet": Image.new("RGB", (420, 594), (250, 250, 250)), "tejun": Image.new("RGB", (600, 300), (245, 245, 245)),
       "thumbs": [(h["letter"], Image.new("RGB", (84, 119), (240, 240, 240))) for h in hs],
       "segs": segs, "page_mm": (layout["page"].w, layout["page"].h), "example_letter": example["letter"]}
scene = scene4.Scene(edo, tpl, recs)
assert scene.duration == scene4.DURATION
for t in (0.5, 6.0, 13.5, 16.0, 18.5, 21.0, 23.0, 28.0):
    a, b = scene.frame(t), scene.frame(t)
    assert a.size == (scene4.W, scene4.H) and a.tobytes() == b.tobytes(), t
# 折る線の段では、線が引かれていく（同じ絵が続かない）
f0 = scene4.CUES["folds"][0] + 0.5
assert scene.frame(f0).tobytes() != scene.frame(f0 + 1.0).tobytes()

# 組の版の札はコードから来る。文字で書き込むと、組を刷り直した時に動画だけ古くなる
assert scene.set_label == f"刷った組 {slider_fan.SHEET_SET}"
assert slider_fan.SHEET_SET not in inspect.getsource(scene4), "SHEET_SET の値を scene4.py に書き込まない"
# 試験の数は渡された時だけ出す。渡さない時は数の無い札
assert scene.tests_label == scene4.TESTS_DEFAULT and not any(ch.isdigit() for ch in scene4.TESTS_DEFAULT)
assert "53/53" in scene4.Scene(edo, tpl, recs, tests="53/53").tests_label
print("ok")
