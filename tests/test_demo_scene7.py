"""デモ動画の場面 7（demo.scene7）の床: 合図の順、1 コマが時刻だけで決まる事、クレジットの行を見る。

頁の画像は取りに行かない（網につながずに回すため）。頁の代わりに黒い四角を置いた紙を使う。
型紙はこのリポの生成器で手元で刷る（1〜2 秒で済み、動画と同じ道を通るので試す価値がある）。
"""
import json
import pathlib
import tempfile

from PIL import Image, ImageDraw

from demo import flip, scene7

rec = json.loads(flip.FIGURES.read_text(encoding="utf-8"))["pages"][flip.PAGE]

# 合図の表は時刻の順で、場面の長さの中
spans = list(scene7.CUES.values())
assert all(a < b for a, b in spans) and spans == sorted(spans) and spans[-1][1] <= scene7.DURATION
assert all(0 <= t <= scene7.DURATION for t in scene7.SHEET_TIMES)

# クレジット: 図の出所・Claude・本人が要る。曲は渡した時だけ書く（plan.md の 4）
joined = " ".join(r + " " + n for r, n in scene7.CREDITS)
assert "国立国会図書館（PDM）" in joined and "Claude" in joined and "本人" in joined
assert not any("曲" == r for r, _ in scene7.credit_lines())
assert scene7.credit_lines(None) == scene7.CREDITS and scene7.credit_lines("") == scene7.CREDITS
assert scene7.credit_lines("試しの曲")[-1] == ("曲", "試しの曲")
assert scene7.REPO_NAME == "utsushi" and "http" not in scene7.REPO_NAME  # URL は作らない
assert scene7.CAPTION == "紙で動いても、昔の作り方の証明にはならない"

# 偽の頁: 枠ごとに黒い四角（人物の代わり）
page = Image.new("L", (1400, 1200), 255)
d = ImageDraw.Draw(page)
for f in rec["figures"]:
    x, y, w, h = f["box_pct"]
    d.rectangle((x * 14 + 10, y * 12 + 10, (x + w) * 14 - 10, (y + h) * 12 - 10), fill=0)

with tempfile.TemporaryDirectory() as tmp:
    template = scene7.make_template(pathlib.Path(tmp))
    assert template is not None, "型紙が刷れない"
    assert template.height > template.width, "A4 の縦長"

scene = scene7.Scene7(page, rec, template)
assert len(scene.order) == 18 and scene.duration == scene7.DURATION
for t in (0.5, 2.0, 4.0, 6.0, 9.0, 11.0, 15.0, 19.9):
    a, b = scene.frame(t), scene.frame(t)
    assert a.size == (flip.W, flip.H) and a.tobytes() == b.tobytes(), t
# 並ぶ段の途中と並び終えた後で絵が違う（1 人ずつ現れる）
assert scene.frame(0.5).tobytes() != scene.frame(4.0).tobytes()
# 曲を渡した時だけ、クレジットの画面が変わる
with_music = scene7.Scene7(page, rec, template, "試しの曲")
assert with_music.frame(15.0).tobytes() != scene.frame(15.0).tobytes()
assert with_music.frame(4.0).tobytes() == scene.frame(4.0).tobytes()

# 型紙の下の札は、どの行も動画の幅の中に収まる（組の名が長くなっても右の端で切れない。11-05 に v10 の「0」が切れた）
from PIL import ImageFont
lines = scene.sheet_label_lines()
assert any("順位ではない" in s for s in lines) and any(scene.sheet_set in s for s in lines)
font = ImageFont.truetype(flip.SERIF, scene7.SHEET_LABEL_PX)
cx = (scene7.SHEET_BOX[0] + scene7.SHEET_BOX[2]) // 2
for s in lines:
    half = font.getlength(s) / 2
    assert cx - half >= 0 and cx + half <= flip.W - 40, (s, cx + half)
# 札の 2 行目の下端は、締めの字幕の帯（y 940 から）より上
assert scene7.SHEET_BOX[3] + 12 + (len(lines) - 1) * (scene7.SHEET_LABEL_PX + 6) + scene7.SHEET_LABEL_PX + 6 <= 940
print("ok label")
# 全部の検査の後に出す（途中で出すと、後の検査が落ちても成功に見えるため。独立のレビューの指摘、11-05）
print("ok")

# 型紙の下の札は、どの行も動画の幅の中に収まる（組の名が長くなっても右の端で切れない。11-05 に v10 の「0」が切れた）
from PIL import ImageFont
lines = scene.sheet_label_lines()
assert any("順位ではない" in s for s in lines) and any(scene.sheet_set in s for s in lines)
font = ImageFont.truetype(flip.SERIF, scene7.SHEET_LABEL_PX)
cx = (scene7.SHEET_BOX[0] + scene7.SHEET_BOX[2]) // 2
for s in lines:
    half = font.getlength(s) / 2
    assert cx - half >= 0 and cx + half <= flip.W - 40, (s, cx + half)
# 札の 2 行目の下端は、締めの字幕の帯（y 940 から）より上
assert scene7.SHEET_BOX[3] + 12 + (len(lines) - 1) * (scene7.SHEET_LABEL_PX + 6) + scene7.SHEET_LABEL_PX + 6 <= 940
print("ok label")
