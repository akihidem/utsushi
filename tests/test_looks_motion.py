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
# 入口は えらぶ（本人のサイト体験レビュー 11-07 の 4・5）: 題の間 → まずはここから の 2 枚 → ほかの原画の並び。間に扉や扇の 1 室を挟まない
body = html.split("</style>")[-1]
hall, mazu, erabu = body.index('class="tj-hall"'), body.index('<section class="tj-mazu"'), body.index('<section class="tj-erabu"')
assert hall < mazu < erabu and 'class="tj-door"' not in body and 'class="road-go"' not in body, "えらぶ の釦（押させる口）は無い"
for gap in ((body.index("</section>", hall), mazu), (body.index("</section>", mazu), erabu)):
    assert body[gap[0] + len("</section>"):gap[1]].strip() == "", "間に 1 室も無い"
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
# 歌の原文は、出す所に引用の印を付ける。入口は えらぶ になり、歌は玩具の頁の頭（原画と歌）だけに出す（入口に同じ物を 2 度置かない）
songs = [x for t in ts for x in t["song"]]
assert not any(x in body for x in songs) or "原文の引用" in html
assert "100svh" in html
# research/24 の小さな直し
assert "body.tenji{background:#fcfcfa" in html and "body.tenji ::selection" in html
assert "overflow-wrap:break-word" in html
assert "::selection" in looks.ZINE  # 大判（A）は外した（本人の決定 11-05 朝）
assert "minmax(0,1fr) minmax(0,1fr)" in looks.ZINE
print("ok")
