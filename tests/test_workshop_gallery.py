"""ワークショップの試行の写真の置き場（本人の見直し 11-07 夜の ②「これまでの復元にワークショップの写真がない。」と ⑦「ワークショップで作られたもの、は
他の人が作ったものなのでそちらにも掲載して」・web.workshop）。本人の言葉 11-08「つくるは読む情報が多すぎて整理する必要を感じる。復元の記録などは
すべてもちよるに統合する。」で、玩具の頁の「これまでの復元」（#minna）は外し、写真は もちよる（/gallery）に出す。

見る事: 表（data/workshop_photos.json）のどの玩具の頁にも #minna とワークショップの写真が無い。/gallery の 並べた写真・できたおもちゃ・様子 の
どれかに表の写真が 1 回ずつ出て（#ageta には出さない）、単体の写真の玩具の札に玩具の頁への道がある。合言葉なしの公開の場でも同じに出る（本人の直の指示）。
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
from web import workshop  # noqa: E402

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
        # 本人の言葉 11-08「…復元の記録などはすべてもちよるに統合する。」: 玩具の頁には これまでの復元 もワークショップの写真も無い
        for sid in sorted(toys) + [none]:
            page = get(base, f"/toy/{sid}")
            assert 'id="minna"' not in page and not re.findall(IMG, page), (sid, kw, re.findall(IMG, page))
        # もちよるの頁では、ワークショップの写真は「ワークショップの様子」と「ワークショップでできたおもちゃ」の節に出る（本人の言葉 11-08）。
        # 前は「他の人が作った物」（#ageta）の中の玩具ごとの札だったので、そこには出さない。表の写真は、2 つの節のどちらかに 1 回ずつ出る
        g = get(base, "/gallery")
        ageta = part(g, 'id="ageta"', "</section>")
        both = part(g, 'id="narabe"', "</figure>") + part(g, 'id="dekita"', "</section>") + part(g, 'id="yousu"', "</section>")
        assert not re.findall(IMG, ageta), (kw, re.findall(IMG, ageta))
        assert all(re.findall(IMG, both).count(r["file"]) == 1 for r in rows), (kw, re.findall(IMG, both))
        for sid in {r["toy"] for r in rows if workshop.kind_of(r["file"]) == "single"}:
            assert f'<a href="/toy/{sid}">' in part(g, 'id="dekita"', "</section>"), (sid, kw)
    finally:
        srv.shutdown()
        srv.server_close()
print(f"ok ワークショップの写真: 玩具の頁（玩具 {len(toys) + 1}）には無く、もちよるの様子とできたおもちゃに表の {len(rows)} 枚が 1 回ずつ・公開の場も同じ")
