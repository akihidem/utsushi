"""デモ動画の場面 4（demo.scene4）の床: 出所の記録がそろい、1 コマが時刻だけで決まり、組の版の札がコードから来る事を見る。
刷って映すのは型紙だけで、手順の紙を刷らず映さない事も見る（本人の決まり「刷るのは型紙だけ」11-06・窓口の決定 11-07）。

画像は取りに行かない（試験を網につながずに回すため）。北斎の頁の代わりに黒い四角の絵を、刷った紙の代わりに無地の絵を渡す。
型紙の配置（compose）だけは本物を使う。PDF を作らず速く、折り線が配置から引ける事をここで確かめられるため。
"""
import inspect

from PIL import Image, ImageDraw

# デモの場面 4 は撮った時の組（goraigo-v10）の紙を映す。デモは撮り直さない（本人の決定 11-06 夜）ので、場面を読み込む前に雛形を前の組に置く
from omochae.templates import slider_fan  # noqa: E402
slider_fan.SHEET_SET = slider_fan.FROZEN_SET
from demo import scene4  # noqa: E402
from omochae import hypotheses  # noqa: E402

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
# 手順の紙を組む部品・置き場・合図を持たない（家で刷る紙が型紙だけになり、動画だけが手順の紙を見せると筋が崩れる）
assert not any(hasattr(scene4, n) for n in ("tejun_layout", "tejun_view_mm", "TEJUN_BOX")), "手順の紙を刷って映す部品が残っている"
assert not any("tejun" in k for k in scene4.CUES), scene4.CUES
# 場面 6 が借りる形（current_layouts が id・letter・params・title を読む）。手順の紙の題と動かし方は持たない
assert all(set(h) == {"id", "letter", "params", "title"} for h in hs), [sorted(h) for h in hs]

# 偽の絵: 北斎の切り出しの代わりに黒い四角、刷った紙の代わりに無地
edo = {}
for pid, rec in recs["pages"].items():
    for c in rec["crops"]:
        g = Image.new("L", (400, 300) if pid.startswith("v3") else (300, 420), 255)
        ImageDraw.Draw(g).rectangle((40, 40, 200, 200), fill=0)
        edo[f"{pid}/{c['id']}"] = g
tpl = {"sheet": Image.new("RGB", (420, 594), (250, 250, 250)),
       "segs": segs, "page_mm": (layout["page"].w, layout["page"].h), "example_letter": example["letter"]}
scene = scene4.Scene(edo, tpl, recs)
assert scene.duration == scene4.DURATION
for t in (0.5, 6.0, 13.5, 16.0, 18.5, 21.0, 23.0, 28.0):
    a, b = scene.frame(t), scene.frame(t)
    assert a.size == (scene4.W, scene4.H) and a.tobytes() == b.tobytes(), t
# 折る線の段では、線が引かれていく（同じ絵が続かない）
f0 = scene4.CUES["folds"][0] + 0.5
assert scene.frame(f0).tobytes() != scene.frame(f0 + 1.0).tobytes()

# 見せる紙はたたき台の 1 組だけ（型紙は玩具に 1 枚。J-032）。組を並べる段と「仮説ごと」の字を出さない。字は書き換えず外した
assert recs["template"]["example_hypothesis"] == hypotheses.sheet_of(recs["template"]["source_id"])["id"]
assert "sets" not in scene4.CUES and not hasattr(scene, "thumbs")
source_text = inspect.getsource(scene4)
assert not any(s in source_text for s in ("仮説ごとに 1 組", "型紙は、仮説ごとに", "どの仮説も同じ形"))
assert all(s in source_text for s in ("江戸の絵も、仕組みを図で残した。", " の組。"))
assert "手順の紙（組み方まで。中の様子の図は伏せた）" not in source_text and "compose_sheet" not in source_text, "手順の紙の絵と札を出さない"
# 型紙は、刷った紙が出るまでは左の置き場、折り線が退いた後は画面の真ん中（本人の決定 11-07）
sw = scene.sheet_rect[2] - scene.sheet_rect[0]
assert scene.sheet_x(15.0) == scene4.SHEET_BOX[0] and scene.sheet_x(scene4.CUES["folds_out"][0]) == scene4.SHEET_BOX[0]
assert scene.sheet_x(25.0) == (scene4.W - sw) // 2, scene.sheet_x(25.0)
# 真ん中へ寄った後、型紙の左右は紙の地のまま（手順の紙も組の列も映らない）。上の題と札の行、下の出所の札の行は除く
for t in (21.0, 23.5, 25.0):
    f, x = scene.frame(t), scene.sheet_x(t)
    for side in ((0, 200, x - 40, scene4.H - 80), (x + sw + 40, 200, scene4.W, scene4.H - 80)):
        assert len(f.crop(side).getcolors()) == 1, (t, side, f.crop(side).getcolors()[:3])
# 題と隅の札の字（本人の決定 11-07「推しでよい」）。前の字から「と手順の紙」を外しただけ
assert '"刷った PDF"' in source_text and "刷った PDF と手順の紙" not in source_text and "型紙と手順の紙:" not in source_text
assert scene.credit(25.0).startswith("型紙: utsushi の生成器が寸法から刷った PDF"), scene.credit(25.0)
# 組の版の札はコードから来る。文字で書き込むと、組を刷り直した時に動画だけ古くなる
assert scene.set_label == f"刷った組 {slider_fan.SHEET_SET}"
assert slider_fan.SHEET_SET not in inspect.getsource(scene4), "SHEET_SET の値を scene4.py に書き込まない"
# 試験の数は渡された時だけ出す。渡さない時は数の無い札
assert scene.tests_label == scene4.TESTS_DEFAULT and not any(ch.isdigit() for ch in scene4.TESTS_DEFAULT)
assert "53/53" in scene4.Scene(edo, tpl, recs, tests="53/53").tests_label
print("ok")
