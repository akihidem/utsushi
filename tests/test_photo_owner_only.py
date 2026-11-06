"""人の確認の前の写真と動画は、上げた本人の画面にだけ出す。別の人の手帖にも、絵の道にも出さない（#314 の線の続き）。

who は sessionStorage にあって、絵と動画の GET に載らない。なので上げた時に画面へ鍵を渡し、写真ごとに控える（話した考えの紙の鍵と同じ作り）。
見る事:
1. 上げた本人の手帖に出て、絵が開く。別の人の手帖には出ず、絵の道も 404。別の人の札の字はそのまま
2. 別の人は、番号を知っていても同じ記録へ上げられない（記録の鍵）。写真の鍵が違う画面には、同じ記録の写真でも見えない（鍵は写真ごと）
3. 人の確認で「物だけ」になれば誰にでも出る。「人や声」は本人にも出ない
4. 次の記録を残すと区切りになる（同じ機械の次の人に、前の人の写真を出さない）。期限を過ぎても閉じる
5. 取り下げで鍵の控えも消える
7. 合言葉なしの場の取り下げ（窓口の決定 11-06 夜・案 A）: 上げた画面にだけ「取り下げる」が出て、押すと写真と動画が置き場ごと消え、ギャラリーからも消える。
   別の画面・鍵の無い画面・期限を過ぎた画面には釦を出さず、送っても断る。合言葉付きの場は進行者に番号を伝える形のまま（釦を出さない）
6. 合言葉なしの場でも受け、合言葉付きの場と同じ線で出す（確かめる前は上げた本人の画面だけ・物だけの後は誰にでも・人や声は誰にも）。
   本人の決定 11-06「公開のデモでも写真と動画を上げられるようにしてください」「公開の場で上げた写真は、公開の場のギャラリーにも出します」。前は受けず、出さず、鍵も渡さなかった
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
        st, data = self.call("GET", f"/toy/{G}/techo/kiroku")
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

# 2. 別の人は、番号を知っていても同じ記録へ上げられない（記録を残した画面の鍵で照らす。tests/test_photo_attach.py）。
# 写真の鍵は写真ごと: 記録の鍵が同じで写真の鍵が違う画面（同じ機械で写真の鍵だけ変わった形）には、前の写真は見えない
assert b.call("POST", f"/record/{rid}/media", JPEG, "image/jpeg")[0] == 403 and not b.cookie, "受けず、鍵も渡さない"
b.cookie = {"utsushi_rec": a.cookie["utsushi_rec"]}
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
    assert e.image(late, n) == 404 and e.call("GET", f"/toy/{G}/techo/kiroku")[0] == 200, ("読めない控えは出さない方へ倒す", bad)
assert media_review.shown_to(late, [n]) == [] and media_review.shown_to(late, [n], "") == [], "鍵なしは確認の後の物だけ"

g = Screen()
g.cookie = {"utsushi_up": "é"}
assert g.image(rid, other) == 404 and g.call("GET", f"/toy/{G}/techo/kiroku")[0] == 200, "形の外の鍵でも落ちない"

# 5. 取り下げで鍵の控えも消える
f = Screen()
gone_rid = f.record()
f.photo(gone_rid)
assert records.withdraw(gone_rid, media_only=True)[1] == []
assert not (pathlib.Path(os.environ["OMOCHAE_DATA"]) / "records" / "media" / gone_rid).exists(), "写真の置き場ごと消える"

# 6. 合言葉なしの場（本人の決定 11-06「公開のデモでも写真と動画を上げられるようにしてください」）
p = Screen(opened)
assert p.call("POST", f"/record/{rid}/media", JPEG, "image/jpeg")[0] == 403 and not p.cookie, "別の人の記録へは上げられず、鍵も渡さない"
assert p.image(rid, name) == 200, "物だけと確かめた後の写真は、開いた場でも誰にでも出す（合言葉付きの場と同じ）"
q = Screen(opened)
mine_rid = q.record()
mine_name = q.photo(mine_rid)  # 自分の記録へは上げられる
assert q.image(mine_rid, mine_name) == 200 and f"/record/{mine_rid}/media/{mine_name}" in q.techo(), "上げた本人の手帖と絵の道に出る"
r = Screen(opened)
assert r.image(mine_rid, mine_name) == 404 and f"/record/{mine_rid}/media/" not in r.techo(), "確かめる前は、別の画面には出さない"
assert media_review.record(mine_rid, mine_name, "object", "試験の人") == []
assert r.image(mine_rid, mine_name) == 200 and f"/record/{mine_rid}/media/{mine_name}" in r.techo(), "物だけと確かめた後は、別の画面にも出る"
voice_rid = q.record()
voice_name = q.photo(voice_rid)
assert media_review.record(voice_rid, voice_name, "people", "試験の人") == []
assert q.image(voice_rid, voice_name) == 404 and r.image(voice_rid, voice_name) == 404, "人や声が入ると確かめた物は、上げた本人にも出さない"
# 絵の道（/media/m…）だけを見る。上げた画面には、見えない物も消せるよう「取り下げる」の道（/media/withdraw）が出る（7）
assert f"/record/{voice_rid}/media/m" not in q.techo() and f"/record/{voice_rid}/media/" not in r.techo()

# 7. 合言葉なしの場の取り下げ
w = Screen(opened)
w_rid = w.record()
w_name = w.photo(w_rid)
w_src = f"/record/{w_rid}/media/{w_name}"
drop = f'action="/record/{w_rid}/media/withdraw"'
assert media_review.record(w_rid, w_name, "object", "試験の人") == []  # ギャラリーに出ている物も、上げた画面からなら消せる
assert w_src in Screen(opened).call("GET", "/gallery")[1].decode(), "対照: 消す前はギャラリーに出ている"
assert drop in w.techo() and "取り下げる</button>" in w.techo(), "上げた画面には釦を出す"
o = Screen(opened)
assert drop not in o.techo(), "別の画面には出さない"
assert o.form(f"/record/{w_rid}/media/withdraw")[0] == 403 and w.image(w_rid, w_name) == 200, "別の画面からは消せない"
nokey = Screen(opened)
nokey.cookie = {"utsushi_rec": w.cookie["utsushi_rec"]}  # 記録の鍵だけを持つ画面（写真の鍵が無い）
assert drop not in nokey.techo() and nokey.form(f"/record/{w_rid}/media/withdraw")[0] == 403, "写真の鍵の無い画面には出さず、消せない"
st, _ = w.form(f"/record/{w_rid}/media/withdraw")
assert st == 303, st
assert not (pathlib.Path(os.environ["OMOCHAE_DATA"]) / "records" / "media" / w_rid).exists(), "置き場ごと消える（確かめの控えも残らない）"
assert w.image(w_rid, w_name) == 404 and w_src not in Screen(opened).call("GET", "/gallery")[1].decode() and drop not in w.techo(), "ギャラリーからも消え、釦も消える"
assert records.all_records(G) and any(r["id"] == w_rid for r in records.all_records(G)), "消えるのは写真と動画だけで、記録は残る"
again = w.photo(w_rid)
assert again == "m1.jpg" and w.image(w_rid, again) == 200 and again and Screen(opened).image(w_rid, again) == 404, "上げ直した物は、前の確かめを引き継がない（確かめの前に戻る）"
# 期限を過ぎた写真の鍵では、釦を出さず、消せない
late_owners = pathlib.Path(os.environ["OMOCHAE_DATA"]) / "records" / "media" / w_rid / "owners.json"
kept_owners = json.loads(late_owners.read_text(encoding="utf-8"))
late_owners.write_text(json.dumps({k: {**v, "at": old} for k, v in kept_owners.items()}), encoding="utf-8")
assert drop not in w.techo() and w.form(f"/record/{w_rid}/media/withdraw")[0] == 403, "期限を過ぎたら消す口も閉じる"
# 次の記録を残すと、前の記録の釦は消え、消せない（保護者の頁の「押せるのは、上げてから2時間の間と、次の記録を残すまでです。」の裏付け。
# 記録を残すと写真の鍵が外れる作り、_up_close。同じ機械の次の人に、前の人の写真を消させないため）
n = Screen(opened)
n_rid = n.record()
n.photo(n_rid)
n_drop = f'action="/record/{n_rid}/media/withdraw"'
assert n_drop in n.techo(), "対照: 次の記録の前は出る"
n.record()
assert "utsushi_up" not in n.cookie and n_drop not in n.techo(), "次の記録を残すと、前の記録の釦は消える"
assert n.form(f"/record/{n_rid}/media/withdraw")[0] == 403 and n.image(n_rid, "m1.jpg") == 404, "次の記録の後は消せない（写真は置き場に残る）"
assert (pathlib.Path(os.environ["OMOCHAE_DATA"]) / "records" / "media" / n_rid / "m1.jpg").exists()
# 合言葉付きの場は、進行者に記録の番号を伝える形のまま（釦を出さず、受けない）
c = Screen()
c_rid = c.record()
c.photo(c_rid)
assert f'action="/record/{c_rid}/media/withdraw"' not in c.techo() and c.form(f"/record/{c_rid}/media/withdraw")[0] == 403, "合言葉付きの場には出さない"

print("ok: 確認の前の写真は、上げた本人の画面にだけ出す。合言葉なしの場では、上げた画面から取り下げられる")
