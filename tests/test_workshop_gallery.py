"""ワークショップの試行の写真が、玩具の頁の「これまでの復元」（#minna）と、作った物の頁（/gallery）の「他の人が作った物」（#ageta）にも出る
（本人の見直し 11-07 夜の ②「これまでの復元にワークショップの写真がない。」と ⑦「ワークショップで作られたもの、は他の人が作ったものなので
そちらにも掲載して」・web.workshop）。

見る事: 表（data/workshop_photos.json）の玩具の頁の #minna に、その玩具の写真だけが表の順で出て、「まだありません」は出ない。
写真の無い玩具の #minna は前のまま。/gallery の #ageta に表の写真が全部出て、玩具ごとの札に玩具の頁への道がある。
合言葉なしの公開の場でも同じに出る（本人の直の指示）。感想の字（人の書いた文）は足さない。
"""
import json
import os
import pathlib
import re
import sys
import tempfile
import threading
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from web.play_server import serve, sources  # noqa: E402
from web.toy import MINNA_EMPTY  # noqa: E402

rows = json.loads((ROOT / "data/workshop_photos.json").read_text(encoding="utf-8"))["photos"]
toys = {r["toy"] for r in rows}
none = next(s for s in sources() if s not in toys)
IMG = r'<img src="/workshop/(\d{8}/p\d{2}\.jpg)/small"'


def get(base, path):
    with urllib.request.urlopen(base + path, timeout=120) as r:
        return r.read().decode()


def part(html, start, end):
    i = html.find(start)
    assert i >= 0, start
    j = html.find(end, i)
    return html[i: j if j > 0 else len(html)]


for kw in ({}, {"public_open": True}):
    srv = serve(0, look="tenji", **kw)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    try:
        for sid in sorted(toys):
            minna = part(get(base, f"/toy/{sid}"), 'id="minna"', "</section>")
            want = [r["file"] for r in rows if r["toy"] == sid]
            assert re.findall(IMG, minna) == want, (sid, kw, re.findall(IMG, minna), want)
            assert MINNA_EMPTY not in minna, (sid, kw)
        minna = part(get(base, f"/toy/{none}"), 'id="minna"', "</section>")
        assert not re.findall(IMG, minna), none
        ageta = part(get(base, "/gallery"), 'id="ageta"', "</section>")
        assert sorted(re.findall(IMG, ageta)) == sorted(r["file"] for r in rows), (kw, re.findall(IMG, ageta))
        for sid in toys:
            assert f'<a href="/toy/{sid}">' in ageta, (sid, kw)
    finally:
        srv.shutdown()
        srv.server_close()
print(f"ok ワークショップの写真: これまでの復元（玩具 {len(toys)}）と他の人が作った物（{len(rows)} 枚）・公開の場も同じ")
