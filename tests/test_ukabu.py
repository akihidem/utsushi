"""入口の最初の画面に浮かぶ玩具（web.ukabu。本人の決め 11-07 夜「これをうつしの一番最初の余白に浮かばせる」）。

見る線:
1. 輪郭の絵（out/ukabu の生成物）が無い場（まっさらな clone）では、入口に何も置かない
2. 絵がある時: 4 つまで・題の間（#hall）の中・玩具の頁への a（キーボードで押せる）・名は玩具の名（新しい字を足さない）
3. 動き: とてもゆっくり（1 往復 16 秒以上）・動きを減らす設定で止める・題の字の上で押す所を取らない
4. 切り抜きの縁の直し（fringe）: 墨の線の外の紙の地は透け、線の内側の白い面（紙の地と同じ色）は残る
"""
import io
import os
import pathlib
import re
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from PIL import Image, ImageDraw  # noqa: E402

from omochae import hypotheses  # noqa: E402
from web import looks, ukabu  # noqa: E402

tmp = pathlib.Path(tempfile.mkdtemp())
ukabu.OUT, ukabu.SRC = tmp / "ukabu", tmp / "sources"

# 1. 絵が無い場
assert ukabu.block(set(ukabu.PICKS)) == "" and 'class="ukabu"' not in looks.tenji()

# 2. 絵がある時
ukabu.OUT.mkdir(parents=True)
for s in ukabu.PICKS:
    Image.new("RGBA", (40, 60), (200, 150, 90, 255)).save(ukabu.OUT / f"{s}.png")
page = looks.tenji()
hall = re.search(r'<section class="tj-hall" id="hall">.*?</section>', page, re.S).group(0)
links = re.findall(r'<a class="uk uk\d" href="/toy/([^"]+)"><img src="/ukabu/([^"]+)\.png" alt="([^"]+)"', hall)
assert 3 <= len(links) <= 5 and len(links) == len(ukabu.PICKS), links
for sid, img, alt in links:
    assert sid == img and alt == hypotheses.load(sid)["toy"], (sid, alt)
assert page.count('class="uk uk') == len(links), "題の間の外にも置いた"
assert '<p class="en">Lost toys of Edo · 1773</p><h1>うつし</h1>' in hall, "題の間の字を替えた"

# 3. 動き
css = "".join(re.findall(r"<style>(.*?)</style>", page, re.S))
secs = [float(x) for x in re.findall(r"\.uk\d?\{[^}]*animation-duration:(\d+(?:\.\d+)?)s", css)]
assert secs and min(secs) >= 16, secs
assert re.search(r"@media \(prefers-reduced-motion:reduce\)\{\.uk\{animation:none\}\}", css), "動きを減らす設定で止まらない"
assert ".ukabu{position:absolute;inset:0;pointer-events:none" in css and ".uk{position:absolute;display:block;width:104px;line-height:0;border:0;pointer-events:auto" in css
assert ".uk:focus-visible{" in css, "キーボードで押した印が無い"

# 4. 縁の直し: 紙の地の上に、墨の輪と、輪の内側の白い面（紙の地と同じ色）。機械の輪郭は輪の外に紙の地の帯を残す
paper = (214, 204, 182)
im = Image.new("RGB", (800, 600), paper)
d = ImageDraw.Draw(im)
d.ellipse((200, 120, 600, 480), fill=paper, outline=(40, 32, 25), width=12)  # 白い面は紙の地と同じ色
d.ellipse((330, 250, 470, 350), fill=(190, 80, 40))  # 中の色の所
ukabu.SRC.mkdir(parents=True)
sid = ukabu.PICKS[0]
im.save(ukabu.SRC / f"{sid}.jpg", quality=95)
before = Image.open(io.BytesIO(ukabu.cut(sid, clean=False)[0]))
after = Image.open(io.BytesIO(ukabu.cut(sid, clean=True)[0]))
def alpha_at(img, x, y):  # 元の絵の座標を、切り詰めた絵の座標へ（どちらも輪の外接の箱で切っている）
    return img.getchannel("A").getpixel((round(x * img.width / 400), round(y * img.height / 360)))
inside = alpha_at(after, 200, 180)  # 輪の真ん中より少し上の白い面
assert inside > 200, ("線の内側の白い面が透けた", inside)
assert alpha_at(after, 120, 180) > 200, "中の色の所が透けた"
import numpy as np  # noqa: E402
ring_out_before = int((np.asarray(before.getchannel("A")) > 128).sum())
ring_out_after = int((np.asarray(after.getchannel("A")) > 128).sum())
assert ring_out_after < ring_out_before, ("縁の紙の地が減らない", ring_out_before, ring_out_after)
print("ok 浮かぶ玩具: 絵が無い場は置かない・題の間に 4 つ・名は玩具の名・とてもゆっくり・動きを減らす設定で止まる・縁の紙の地を外し白い面は残す")
