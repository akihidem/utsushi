"""デモ動画の場面 6（demo.scene6）の床: 引いた所見が原文のまま、版の札がコードから来て、1 コマが時刻だけで決まる事を見る。

Chrome も pdftoppm も呼ばない（試験を手元の道具に依らずに回すため）。手帖の画面と紙の絵は無地の偽物を渡す。
型紙の配置（compose）だけは本物を使う。PDF を作らず速く、朱の枠が今の部品の形から引ける事をここで確かめられるため。
"""
import inspect

from PIL import Image

from demo import scene6
from omochae import hypotheses
from omochae.templates import slider_fan

# 本人の所見は、試行の索引の文に一字一句ある（言い換えると「作った人の言葉」でなくなる）
readme = scene6.TRIALS_README.read_text(encoding="utf-8")
assert scene6.QUOTES and all(f"「{q}」" in readme for q in scene6.QUOTES), "所見は README の原文のまま"
assert "本人の所見" in scene6.QUOTE_FROM and "11-04" in scene6.QUOTE_FROM
assert all(r in readme for r in ("R-0001", "R-0002", "goraigo-v8"))
# T-0001 の ID は試行の索引に無く、決めた事の表（U-32）にある。R-0001・R-0002 と goraigo-v8 につながる行で照らす
decided = (scene6.ROOT / "docs/process/decided-and-open.md").read_text(encoding="utf-8")
assert any(all(k in line for k in ("R-0001", "T-0001", "goraigo-v8")) for line in decided.splitlines())
# 版ごとに変えた事は、型紙の版の表に根拠の語がある
sheets_readme = scene6.SHEETS_README.read_text(encoding="utf-8")
for ver, _, key in scene6.CHANGES:
    assert f"goraigo-{ver}" in sheets_readme and key in sheets_readme, (ver, key)

# 型紙は玩具に 1 枚（J-032）。紙を並べて見せるのは、たたき台の 1 組だけ
assert scene6.SHOWN_HYPS == (hypotheses.sheet_of(scene6.SID)["id"],) == ("H-A",)
# 所見と版の字は 11-04 の試行の事実なので残す（字は書き換えない）
assert any("仮説 C にも内筒の土台" in s for _, s, _ in scene6.CHANGES)
# 古い紙は git にある PDF を使う（作り直さない）
for hyp in scene6.SHOWN_HYPS:
    assert (scene6.OLD_DIR / scene6.OLD_PDF.format(hyp=hyp)).exists(), hyp

# 合図の表は時刻の順で、動画の長さの中
spans = list(scene6.CUES.values())
assert all(a < b for a, b in spans) and spans == sorted(spans) and spans[-1][1] <= scene6.DURATION == 25.0

# 朱の枠は今の配置の部品から引く。A には下からの切り込みと、色の境で折る所
# 撮った時の組（goraigo-v10）の紙で見る。デモは撮り直さない（本人の決定 11-06 夜）。生成器は今の組の紙を刷るので、v14 の後に撮り直すなら直す要がある
from omochae.templates import slider_fan as _fan  # noqa: E402
_now, _fan.SHEET_SET = _fan.SHEET_SET, _fan.FROZEN_SET
try:
    layouts, _ = scene6.current_layouts()
finally:
    _fan.SHEET_SET = _now
regions = {}
for hyp, (h, layout, failures) in layouts.items():
    assert not failures, [f.line() for f in failures]
    regions[hyp] = layout, scene6.change_regions(layout)
labels = {hyp: {lab for lab, _ in r} for hyp, (_, r) in regions.items()}
assert scene6.LABEL_GROOVE in labels["H-A"] and scene6.LABEL_COLOR in labels["H-A"], labels
for hyp, (layout, r) in regions.items():
    for lab, (x0, y0, x1, y1) in r:
        assert 0 <= x0 < x1 <= layout["page"].w and 0 <= y0 < y1 <= layout["page"].h, (hyp, lab)

# 手帖を撮る頁: 外の字を読まず、読み上げを切り、仕組みの質問は頁の中の決まりで断られる語を含む
from api import ask  # noqa: E402

html = scene6.techo_html(scene6.ASKS[1][0])
assert "fonts.googleapis.com" not in html and "'speak').checked=false" in html
assert any(w in scene6.ASKS[1][0] for w in ask.MECHANISM_WORDS)
assert any(w in scene6.ASKS[0][0] for w in ask.GLOSSARY) and not any(w in scene6.ASKS[0][0] for w in ask.MECHANISM_WORDS)

# 偽の絵で 1 コマを描く
pairs = [{"hyp": hyp, "letter": layouts[hyp][0]["letter"], "old": Image.new("RGB", (210, 297), (250, 250, 250)),
          "new": Image.new("RGB", (210, 297), (245, 245, 245)), "regions": regions[hyp][1],
          "page_mm": (regions[hyp][0]["page"].w, regions[hyp][0]["page"].h)} for hyp in scene6.SHOWN_HYPS]
shots = [Image.new("RGB", (860, 1864), (240, 236, 228)) for _ in scene6.ASKS]
scene = scene6.Scene(pairs, shots)
assert scene.duration == scene6.DURATION
for t in (0.5, 4.0, 9.0, 12.5, 14.5, 18.0, 20.0, 23.0, 24.9):
    a, b = scene.frame(t), scene.frame(t)
    assert a.size == (1920, 1080) and a.tobytes() == b.tobytes(), t
# 枠の段では朱の枠が現れる（同じ絵が続かない）
assert scene.frame(scene6.CUES["boxes_a"][0]).tobytes() != scene.frame(scene6.CUES["boxes_a"][1]).tobytes()

# 版の札はコードから来る。文字で書き込むと、組を刷り直した時に動画だけ古くなる
assert scene.new_label == slider_fan.SHEET_SET and slider_fan.SHEET_SET in scene.tag and "T-0001" in scene.tag
assert slider_fan.SHEET_SET not in inspect.getsource(scene6), "SHEET_SET の値を scene6.py に書き込まない"
print("ok")
