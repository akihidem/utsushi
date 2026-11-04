"""A′（/look/tenji）に足した動き（本人の頼み 2026-11-04、J-024）の試験。
なぜ: 動きは JS が無くても・動きを減らす設定でも止まった展示として完成している事、見えた時に起こす仕掛けを
入れない事（research/19）、仮説を出さない事を、手で写しを見なくても崩れないよう固定する。"""
import os
import re
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from web import looks  # noqa: E402

html = looks.tenji()
ts = looks.toys()

# 扇の札: 玩具ごとに図 1 枚と寄り 4 枚。中央の札は 1 つだけで、静かな扇として刷られている
cards = re.findall(r'class="fan-card( is-c)?"', html)
assert len(cards) == 5 * len(ts) and len(ts) >= 1, len(cards)
assert sum(1 for c in cards if c) == 1, "中央は 1 枚"
assert html.count('class="fan-prev"') == 1 and html.count('class="fan-next"') == 1
assert "ArrowLeft" in html and "ArrowRight" in html and "pointerup" in html
# 図の札は玩具の頁へ入る
for t in ts:
    assert f'class="fan-card' in html and f'href="/toy/{t["sid"]}" data-name' in html
# JS が無くても開いた扇: 番手 --k は刷った時に入っている
assert re.search(r'style="--k:-\d+;z-index:\d+"', html) and 'style="--k:0;' in html
# 動きを減らす設定では動かさない。せり上がりはスクロール連動の CSS だけで、効く閲覧器だけ
assert "@media (prefers-reduced-motion:reduce){.fan-card{transition:none}}" in html
assert "@supports (animation-timeline: view())" in html and "prefers-reduced-motion:no-preference" in html
assert "animation-timeline:view()" in html
# 見える状態から始める（中身を隠さない）
kf = re.findall(r"@keyframes tj-rise[^{]*\{(.*?)\}\}", html, re.S)
assert kf and all("opacity" not in k for k in kf)
assert "IntersectionObserver" not in html and "whileInView" not in html
# 扇をひらくノブ: 開く角だけ。仮説や仕組みの名を出さない
assert 'id="ogi-range" type="range"' in html and "扇をひらく" in html
assert "仮説 A" not in html and "H-A" not in html
# 前からの線
assert "原文の引用" in html and "100svh" in html
# research/24 の小さな直し
assert "body.tenji{background:#fcfcfa" in html and "body.tenji ::selection" in html
assert "overflow-wrap:break-word" in html
assert "clamp(10px,.78vw,11px)" in looks.TAIBAN and "::selection" in looks.TAIBAN and "::selection" in looks.ZINE
assert "minmax(0,1fr) minmax(0,1fr)" in looks.ZINE
print("ok")
