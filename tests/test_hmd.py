"""作業しながら見る頁の試作（web.hmd）の試験。本物の API と声は使わない。

見る事:
1. 組み立ての 3D（kumitate）を中に持ち、送る釦・鍵・声の言葉が kumitate の釦につながっている
2. 声は「はじめる」の後だけ聞き、字を外へ送らない（頁の JS に送る道が無い）。声が使えない時の文がある
3. 組み立ての書き方が無い玩具は出さない
"""
import json
import os
import re
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from web import hmd, kumitate  # noqa: E402

G, T = hmd.TOYS
for sid in (G, T):
    assert hmd.available(sid), sid
    page = hmd.page(sid)
    assert 'id="rt-stage"' in page and 'id="rt-next"' in page and 'id="rt-prev"' in page, "kumitate の 3D と釦がある"
    for w in (hmd.NEXT, hmd.PREV, hmd.AGAIN, hmd.LISTEN, hmd.NO_VOICE, hmd.HOW):
        assert w in page or json.dumps(w, ensure_ascii=False)[1:-1] in page, w
    words = json.loads(re.search(r'<script type="application/json" id="hmd-words">(.*?)</script>', page, flags=re.S).group(1))
    kinds = {k for k, _ in words["words"]}
    assert kinds == {"next", "prev", "again", "top", "stop"}
    pat = dict(words["words"])
    for said, k in (("つぎ", "next"), ("次", "next"), ("もどる", "prev"), ("もう一回", "again"), ("もう一度", "again"), ("最初から", "top"), ("止めて", "stop")):
        assert re.search(pat[k], said), (said, k)
    assert not re.search(pat["next"], "もどる") and not re.search(pat["prev"], "つぎ")
    # 声は押した後だけ。字を外へ送らない（fetch・XHR・送信の道が無い）
    script = page.split(hmd.SCRIPT[:20], 1)[1]
    assert "rec.start()" in script and "listen.addEventListener('click'" in script
    assert not re.search(r"fetch\(|XMLHttpRequest|sendBeacon|<form", hmd.SCRIPT), "字を外へ送らない"
    assert "visibilitychange" in hmd.SCRIPT, "頁を隠したら聞くのを止める"
    assert "if(done())next.click();" in hmd.SCRIPT, "開いたら手順 1 から始める"
    assert "rec.onresult=e=>{if(!on)return;" in hmd.SCRIPT, "止めた後に届いた字では送らない"
    # 鍵で送れる（足の踏み板・指輪の送りは PageDown・PageUp）
    for key in ("ArrowRight", "ArrowLeft", "PageDown", "PageUp"):
        assert key in hmd.SCRIPT, key

assert not hmd.available("NDL-1187053-R0000004-L"), "組み立ての書き方が無い玩具は出さない"
index = hmd.index()
assert all(f'href="/hmd/{sid}"' in index for sid in (G, T))
assert kumitate.DONE
print("ok 作業しながら見る試作の頁は、組み立ての 3D と声とボタンと鍵で送れる")
