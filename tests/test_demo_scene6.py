"""デモ動画の場面 6（demo.scene6）の床: 引いた所見が原文のまま、版の札がコードから来て、1 コマが時刻だけで決まる事を見る。

Chrome も pdftoppm も呼ばない（試験を手元の道具に依らずに回すため）。紙の絵は無地の偽物を渡す。
型紙の配置（compose）だけは本物を使う。PDF を作らず速く、朱の枠が今の部品の形から引ける事をここで確かめられるため。
"""
import inspect

from PIL import Image

from demo import scene6
from omochae.templates import slider_fan

# 本人の所見は、試行の索引の文に一字一句ある（言い換えると「作った人の言葉」でなくなる）
readme = scene6.TRIALS_README.read_text(encoding="utf-8")
assert scene6.QUOTES and all(f"「{q}」" in readme for q in scene6.QUOTES), "所見は README の原文のまま"
assert "本人の所見" in scene6.QUOTE_FROM and "11-04" in scene6.QUOTE_FROM
for hyp in scene6.SHOWN_HYPS:
    assert (scene6.OLD_DIR / scene6.OLD_PDF.format(hyp=hyp)).exists(), hyp

# 合図の表は時刻の順で、動画の長さの中
spans = list(scene6.CUES.values())
assert all(a < b for a, b in spans) and spans == sorted(spans) and spans[-1][1] <= scene6.DURATION == 10.0

# 朱の枠は今の配置の部品から引く。A には下からの切り込み、C には土台、どちらも色の境で折る
layouts, _ = scene6.current_layouts()
regions = {}
for hyp, (h, layout, failures) in layouts.items():
    assert not failures, [f.line() for f in failures]
    regions[hyp] = layout, scene6.change_regions(layout)
labels = {hyp: {lab for lab, _ in r} for hyp, (_, r) in regions.items()}
assert scene6.LABEL_GROOVE in labels["H-A"] and scene6.LABEL_COLOR in labels["H-A"], labels
for hyp, (layout, r) in regions.items():
    for lab, (x0, y0, x1, y1) in r:
        assert 0 <= x0 < x1 <= layout["page"].w and 0 <= y0 < y1 <= layout["page"].h, (hyp, lab)

# 偽の絵で 1 コマを描く
pairs = [{"hyp": hyp, "letter": layouts[hyp][0]["letter"], "old": Image.new("RGB", (210, 297), (250, 250, 250)),
          "new": Image.new("RGB", (210, 297), (245, 245, 245)), "regions": regions[hyp][1],
          "page_mm": (regions[hyp][0]["page"].w, regions[hyp][0]["page"].h)} for hyp in scene6.SHOWN_HYPS]
scene = scene6.Scene(pairs)
assert scene.duration == scene6.DURATION
for t in (0.5, 2.0, 3.8, 5.0, 7.0, 8.0, 9.0, 10.0, 11.9):
    a, b = scene.frame(t), scene.frame(t)
    assert a.size == (1920, 1080) and a.tobytes() == b.tobytes(), t
# 枠の段では朱の枠が現れる（同じ絵が続かない）
assert scene.frame(scene6.CUES["boxes_a"][0]).tobytes() != scene.frame(scene6.CUES["boxes_a"][1]).tobytes()

# 版の札はコードから来る。文字で書き込むと、組を刷り直した時に動画だけ古くなる
assert scene.new_label == slider_fan.SHEET_SET and slider_fan.SHEET_SET in scene.tag
assert slider_fan.SHEET_SET not in inspect.getsource(scene6), "SHEET_SET の値を scene6.py に書き込まない"
print("ok")
