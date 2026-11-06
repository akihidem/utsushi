"""人の確認の前の写真と動画は、上げた本人の画面にだけ出す。別の人の手帖にも、絵の道にも出さない（#314 の線の続き）。

who は sessionStorage にあって、絵と動画の GET に載らない。なので上げた時に画面へ鍵を渡し、写真ごとに控える（話した考えの紙の鍵と同じ作り）。
見る事:
1. 上げた本人の手帖に出て、絵が開く。別の人の手帖には出ず、絵の道も 404。別の人の札の字はそのまま
2. 別の人が同じ記録へ上げても、前の人の写真は見えない（鍵は写真ごと）
3. 人の確認で「物だけ」になれば誰にでも出る。「人や声」は本人にも出ない
4. 次の記録を残すと区切りになる（同じ機械の次の人に、前の人の写真を出さない）。期限を過ぎても閉じる
5. 取り下げで鍵の控えも消える
6. 合言葉なしの場は今のまま（受けず、出さず、鍵も渡さない）
"""
import http.client
import io
import json
import os
import pathlib
import tempfile
import threading
import urllib.parse
from datetime import datetime, timedelta, timezone

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(os.environ["OMOCHAE_DATA"], "api-usage.jsonl")

from PIL import Image  # noqa: E402

from api import ask  # noqa: E402
from omochae import media_review, records  # noqa: E402
from web.play_server import serve  # noqa: E402

ask._key_present = lambda: False  # 合言葉なしの場は鍵のある所で立たない。鍵のある機械でも同じに動かす
G = "NDL-1187053-R0000005-L"
buf = io.BytesIO()
Image.new("RGB", (16, 16), (200, 180, 140)).save(buf, "JPEG")
JPEG = buf.getvalue()


def up(**kw):
    server = serve(0, **kw)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server.server_address[1]


closed, opened = up(), up(public_open=True)


class Screen:
    """1 つのブラウザ。cookie を持ち回る。"""

    def __init__(self, port=closed):
        self.port, self.cookie, self.last = port, {}, ""

    def call(self, method, path, body=None, ctype=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=120)
        h = {"Host": f"127.0.0.1:{self.port}"}
        if self.cookie:
            h["Cookie"] = "; ".join(f"{k}={v}" for k, v in self.cookie.items())
        if body is not None:
            h.update({"Origin": f"http://127.0.0.1:{self.port}", "Content-Type": ctype})
        c.request(method, path, body, h)
        r = c.getresponse()
        data = r.read()
        c.close()
        lines = r.headers.get_all("Set-Cookie") or []  # 記録の後は記録の鍵と写真の鍵の 2 行が来る。ブラウザと同じに全部読む
        self.last = "\n".join(lines)
        for line in lines:
            name, _, value = line.split(";", 1)[0].partition("=")
            if value and "Max-Age=0" not in line:
                self.cookie[name] = value
            else:
                self.cookie.pop(name, None)
        return r.status, data

    def form(self, path, **fields):
        return self.call("POST", path, urllib.parse.urlencode(fields), "application/x-www-form-urlencoded")

    def record(self, route="record-json"):
        st, data = self.form(f"/toy/{G}/{route}", hypothesis="H-A", result="動いた", who="photowho01")
        if route == "record-json":
            assert st == 201, (st, data[:200])
            return json.loads(data)["id"]
        assert st == 303, (st, data[:200])
        return records.all_records(G)[-1]["id"]

    def photo(self, rid):
        st, data = self.call("POST", f"/record/{rid}/media", JPEG, "image/jpeg")
        assert st == 201, (st, data[:200])
        return data.decode()

    def techo(self):
        st, data = self.call("GET", f"/toy/{G}/techo")
        assert st == 200, st
        return data.decode()

    def image(self, rid, name):
        return self.call("GET", f"/record/{rid}/media/{name}")[0]


a, b = Screen(), Screen()
assert a.form(f"/toy/{G}/print", hypothesis="H-A")[0] == 303
rid = a.record()
name = a.photo(rid)
assert "HttpOnly" in a.last and "SameSite=Lax" in a.last and "Max-Age" not in a.last and "utsushi_up=" in a.last, a.last
src = f"/record/{rid}/media/{name}"

# 1. 上げた本人にだけ出る。別の人の札の字はそのまま
assert src in a.techo() and a.image(rid, name) == 200, "上げた本人は受け取りを確かめられる"
page = b.techo()
assert src not in page and rid in page, "別の人の手帖に出さない。札は残す"
assert b.image(rid, name) == 404, "別の人には絵の道も開かない"
assert not b.cookie, "見ただけの人に鍵を渡さない"
assert b.call("GET", f"/toy/{G}")[1].decode().count(src) == 0 and a.call("GET", f"/toy/{G}")[1].decode().count(src) == 0, "玩具の頁は確認の後だけ（今のまま）"
assert src not in a.call("GET", "/gallery")[1].decode(), "ギャラリーも確認の後だけ（今のまま）"

# 2. 別の人が同じ記録へ上げても、前の人の写真は見えない
other = b.photo(rid)
assert b.image(rid, other) == 200 and b.image(rid, name) == 404, "鍵は写真ごと"
assert a.image(rid, name) == 200 and a.image(rid, other) == 404, "前の人にも後の人の写真は見えない"
assert src in a.techo() and f"/record/{rid}/media/{other}" not in a.techo()

# 3. 人の確認の後は、確認のとおり
assert media_review.waiting() == [(rid, name), (rid, other)], "鍵の控えを確認待ちに数えない"
media_review.record(rid, name, "object", "確かめた人")
media_review.record(rid, other, "people", "確かめた人")
c = Screen()
assert c.image(rid, name) == 200 and src in c.techo(), "物だけと確かめた物は誰にでも出る"
assert b.image(rid, other) == 404 and f"/record/{rid}/media/{other}" not in b.techo(), "人や声が入る物は本人にも出ない"

# 4. 次の記録が区切りになる（どちらの口でも）。期限を過ぎても閉じる
for route in ("record-json", "record"):
    d = Screen()
    first = d.record()
    n = d.photo(first)
    assert d.image(first, n) == 200
    assert "utsushi_up" in d.cookie
    second = d.record(route)
    assert "utsushi_up=" in d.last and "Max-Age=0" in d.last, (route, d.last)
    assert d.image(first, n) == 404, (route, "同じ機械の次の人に、前の人の写真を出さない")
    assert f"/record/{first}/media/{n}" not in d.techo(), route
    n2 = d.photo(second)
    assert d.image(second, n2) == 200, (route, "次の人の写真は次の人に出る")
e = Screen()
late = e.record()
n = e.photo(late)
owners = pathlib.Path(os.environ["OMOCHAE_DATA"]) / "records" / "media" / late / "owners.json"
kept = json.loads(owners.read_text(encoding="utf-8"))
old = (datetime.now(timezone(timedelta(hours=9))) - timedelta(hours=media_review.OWNER_HOURS, minutes=1)).isoformat(timespec="seconds")
owners.write_text(json.dumps({k: {**v, "at": old} for k, v in kept.items()}), encoding="utf-8")
assert e.image(late, n) == 404 and f"/record/{late}/media/{n}" not in e.techo(), "期限を過ぎたら閉じる"
key = kept[n]["key"]
for bad in ("{壊れた", json.dumps({n: {"key": key}}), json.dumps({n: {"key": key, "at": "壊れた時刻"}}), json.dumps({n: {"key": 3, "at": old}}), json.dumps({n: "字"})):
    owners.write_text(bad, encoding="utf-8")
    assert e.image(late, n) == 404 and e.call("GET", f"/toy/{G}/techo")[0] == 200, ("読めない控えは出さない方へ倒す", bad)
assert media_review.shown_to(late, [n]) == [] and media_review.shown_to(late, [n], "") == [], "鍵なしは確認の後の物だけ"

g = Screen()
g.cookie = {"utsushi_up": "é"}
assert g.image(rid, other) == 404 and g.call("GET", f"/toy/{G}/techo")[0] == 200, "形の外の鍵でも落ちない"

# 5. 取り下げで鍵の控えも消える
f = Screen()
gone_rid = f.record()
f.photo(gone_rid)
assert records.withdraw(gone_rid, media_only=True)[1] == []
assert not (pathlib.Path(os.environ["OMOCHAE_DATA"]) / "records" / "media" / gone_rid).exists(), "写真の置き場ごと消える"

# 6. 合言葉なしの場は今のまま
p = Screen(opened)
assert p.call("POST", f"/record/{rid}/media", JPEG, "image/jpeg")[0] == 403 and not p.cookie, "受けず、鍵も渡さない"
assert p.image(rid, name) == 404 and src not in p.techo(), "確認の後の写真も出さない"
p.cookie = dict(a.cookie)
assert p.image(rid, name) == 404, "鍵があっても出さない"

print("ok: 確認の前の写真は、上げた本人の画面にだけ出す")
