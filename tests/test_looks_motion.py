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

# 扇の札（扇の間）と扇をひらくノブは外した（本人の言葉 11-07「扇の間要らない」）。札も釦もノブも台本も刷らない
assert 'class="fan-card' not in html and 'id="tj-fan"' not in html and "扇の間" not in html
assert 'id="ogi-range"' not in html and "扇をひらく" not in html and "fan-prev" not in html
# 扉の次は全部の玩具の一覧（間に扇の 1 室を挟まない）
door, room = html.index('class="tj-door"'), html.index('<section class="tj-all" id="all-toys"')
assert door < room and html[html.index("</section>", door) + len("</section>"):room].strip() == "", "扉と一覧の間に 1 室も無い"
# 動きを減らす設定では動かさない（せり上がりは no-preference の中だけ）。スクロール連動の CSS だけで、効く閲覧器だけ
assert "@supports (animation-timeline: view())" in html and "prefers-reduced-motion:no-preference" in html
assert "animation-timeline:view()" in html
# 見える状態から始める（中身を隠さない）
kf = re.findall(r"@keyframes tj-rise[^{]*\{(.*?)\}\}", html, re.S)
assert kf and all("opacity" not in k for k in kf)
assert "IntersectionObserver" not in html and "whileInView" not in html
# 仮説や仕組みの名を出さない
assert "仮説 A" not in html and "H-A" not in html
# 前からの線
assert "原文の引用" in html and "100svh" in html
# research/24 の小さな直し
assert "body.tenji{background:#fcfcfa" in html and "body.tenji ::selection" in html
assert "overflow-wrap:break-word" in html
assert "::selection" in looks.ZINE  # 大判（A）は外した（本人の決定 11-05 朝）
assert "minmax(0,1fr) minmax(0,1fr)" in looks.ZINE
print("ok")
