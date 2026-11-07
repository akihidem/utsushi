"""玩具の頁の「これまでの記録」に、ワークショップで作られた物の写真が、その玩具の分だけ出る（本人の言葉 11-07 夜
「おもちゃ毎のつくるにあるこれまでの記録にはワークショップで作られた写真を載せて欲しい」・web.workshop）。

見る事: 表（data/workshop_photos.json）の写真は全部置き場に在り、玩具の印は 83 の中。表の玩具の頁の「これまでの記録」に、
その玩具の写真だけが小さい写しの道で出る（ほかの玩具の写真は出ない・写真の無い玩具は並びを出さない）。小さい写しは 100KB 以下。
表の外の道は 404。合言葉なしの公開の場でも同じに出る（本人の直の指示）。人の書いた字（感想）は頁に足さない。
"""
import json
import os
import pathlib
import re
import sys
import tempfile
import threading
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from web import workshop  # noqa: E402
from web.play_server import serve, sources  # noqa: E402

rows = json.loads((ROOT / "data/workshop_photos.json").read_text(encoding="utf-8"))["photos"]
assert rows, "表が空"
for r in rows:
    assert (ROOT / "docs/process/trials/photos" / r["file"]).exists(), ("写真が無い", r["file"])
    assert r["toy"] in sources(), ("83 の外の玩具", r)
    assert r.get("why"), ("照らした理由が無い", r)
assert len({(r["file"], r["toy"]) for r in rows}) == len(rows), "同じ組が 2 回"
G, T = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"
toys = {r["toy"] for r in rows}
assert {G, T} <= toys, toys
none = next(s for s in sources() if s not in toys)


def get(base, path):
    try:
        with urllib.request.urlopen(base + path, timeout=120) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def section(html):
    m = re.search(r"<summary><h3>これまでの記録</h3></summary>(.*?)</details>", html, re.S)
    assert m, "これまでの記録の節が無い"
    return m.group(1)


for kw in ({}, {"public_open": True}):
    srv = serve(0, look="tenji", **kw)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    try:
        for sid in sorted(toys):
            st, body = get(base, f"/toy/{sid}")
            assert st == 200, (sid, st)
            sec = section(body.decode())
            want = [r["file"] for r in rows if r["toy"] == sid]
            got = re.findall(r'<img src="/workshop/(\d{8}/p\d{2}\.jpg)/small"', sec)
            assert got == want, (sid, kw, got, want)
        st, body = get(base, f"/toy/{none}")
        assert st == 200 and "strip workshop" not in body.decode(), none
        for f in {r["file"] for r in rows}:
            st, body = get(base, f"/workshop/{f}/small")
            assert st == 200 and body[:2] == b"\xff\xd8" and len(body) <= 100_000, (f, st, len(body))
        assert get(base, "/workshop/20261106/p28.jpg/small")[0] == 404  # 置き場に在っても表の外は返さない
        assert get(base, "/workshop/20261106/p99.jpg/small")[0] == 404
        assert get(base, "/workshop/../../README.md/small")[0] == 404
    finally:
        srv.shutdown()
        srv.server_close()
print(f"ok ワークショップの写真: 表 {len(rows)} 枚・玩具 {len(toys)}・その玩具の分だけ・小さい写し 100KB 以下・表の外は 404・公開の場も同じ")
