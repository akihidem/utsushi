"""組み立ての 3D の釦の隣に、押すと動く事の手引きの 1 行がある（夕方のレビュー 11-07 の 10）。

なぜ: 組み立ての 3D は、開いただけでは動かし始めない（web/kumitate.py の判断の芯）。釦を押さないと組み立て方が分からない、と
レビューで言われた。動かし方の決まりは替えず、釦のすぐ後に手引きの 1 行を添える。手引きは、開いた時に見える釦（RESTART）と始めた後の釦（NEXT）の字を含み、
釦の字を替えた時に手引きだけ古くならない。3D の無い玩具には手引きも出さない。
"""
import re

from omochae import hypotheses
from web import kumitate, play_server

shown = [s for s in sorted(play_server.sources()) if kumitate.available(s)]
assert shown, "3D のある玩具が 1 つも無い"
# 先に振る舞い: 3D の釦の並びのすぐ後に、手引きの行がある（前の形では釦の並びの後がすぐ形の断りで、ここで落ちる）
for sid in shown:
    assert re.search(r'<div class="rt-acts">.*?</div><p class="meta rt-hint">[^<]+</p>', kumitate.block(sid), re.S), (sid, "釦の並びのすぐ後に手引きの行が無い")
assert kumitate.RESTART in kumitate.HINT and kumitate.NEXT in kumitate.HINT, "手引きは、開いた時に見える釦（はじめから組み立てる）と、始めた後の釦（次へ）を名指しする"
for sid in shown:
    html = kumitate.block(sid)  # 組み立ての 3D（玩具の頁の頭と組み立ての頁が使う）。組み方の節（section）は平らな図で、舞台を持たない
    acts = html.index('<div class="rt-acts">')
    hint = html.index(f'<p class="meta rt-hint">{kumitate.esc(kumitate.HINT)}</p>')
    note = html.index(kumitate.esc(kumitate.NOTE_SHAPE))
    assert acts < hint < note, (sid, "手引きは釦の並びのすぐ後、形の断りの前")
    assert html.count(kumitate.esc(kumitate.HINT)) == 1, sid
    assert not re.search(r'id="rt-next"[^>]*autoplay|data-autoplay', html), (sid, "開いただけで動かし始めない決まりは替えない")
# 3D の無い玩具には手引きを出さない
plain = [s for s in sorted(play_server.sources()) if not kumitate.available(s) and hypotheses.load(s).get("hypotheses")][:5]
for sid in plain:
    assert kumitate.esc(kumitate.HINT) not in kumitate.block(sid) + kumitate.section(sid), sid
print("ok: 組み立ての 3D の釦の隣に、押すと動く事の手引きがある")
