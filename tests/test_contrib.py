"""持ち寄りの床の試験。本物のデータに触らないよう、置き場を使い捨てにする。"""
import base64
import json
import os
import pathlib
import tempfile
import threading
import urllib.error
import urllib.request

tmp = tempfile.mkdtemp()
os.environ["OMOCHAE_DATA"] = tmp

from api.tools import list_contributions
from omochae import contrib
from web.contrib_server import serve

PNG = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"0" * 32).decode()


def base(**kw):
    c = {"kind": "memory", "role": "memory", "certainty": "覚えている", "body": "筒を下げて遊んだ", "toy_name": "御来迎",
         "rights": {"basis": "own_work", "holder": "", "license": "display_only"},
         "attest": {"agrees_terms": True, "adult_or_guardian": True, "no_identifiable_people": True}, "contact": "someone@example.test"}
    c.update(kw)
    return c


def floors(fs):
    return {f.floor for f in fs}


# F10.intake
assert floors(contrib.submit(base(attest={"agrees_terms": True}))[1]) == {"F10.intake"}
assert floors(contrib.submit(base(body=" "))[1]) == {"F10.intake"}
assert floors(contrib.submit(base(kind="photo", rights={"basis": "own_work", "holder": "本人", "license": "display_only"}), base64.b64encode(b"GIF89a").decode())[1]) == {"F10.intake"}
big = base64.b64encode(b"\xff\xd8\xff" + b"0" * (contrib.MAX_IMAGE + 1)).decode()
assert floors(contrib.submit(base(kind="photo", rights={"basis": "own_work", "holder": "本人", "license": "display_only"}), big)[1]) == {"F10.intake"}
# F10.rights
assert "F10.rights" in floors(contrib.submit(base(kind="photo"), PNG)[1])
cid, fs = contrib.submit(base(rights={"basis": "unknown", "holder": "", "license": "display_only"}))
assert not fs and floors(contrib.approve(cid, "確認者")) == {"F10.rights"}
# F10.review
cid, _ = contrib.submit(base())
assert floors(contrib.approve(cid, " ")) == {"F10.review"}
assert contrib.reject(cid, "確認者") == []
assert floors(contrib.approve(cid, "確認者")) == {"F10.review"}
# F10.pii
for text in ("連絡は a.b@example.com まで", "電話 03-1234-5678", "〒100-0001 のお店", "携帯09012345678"):
    cid, _ = contrib.submit(base(body=text))
    assert floors(contrib.approve(cid, "確認者")) == {"F10.pii"}, text
cid, _ = contrib.submit(base(body="1773 年の本にある。1931 年の複製もある"))
assert contrib.approve(cid, "確認者") == [], "年の数字を電話番号と誤って止めない"
contrib.withdraw(cid)
# 正の流れと F10.public
srv = serve(0)
port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()


def get(path):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}") as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def post(obj, headers=None):
    h = {"Content-Type": "application/json", **(headers or {})}
    req = urllib.request.Request(f"http://127.0.0.1:{port}/api/contribute", json.dumps(obj).encode(), h)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


assert post(base(), {"Origin": "https://evil.example"})[0] == 403
assert post(base(attest={}))[0] == 422
code, res = post(base(kind="photo", image=PNG, rights={"basis": "own_work", "holder": "山田", "license": "CC-BY-4.0"}, body="<script>x</script>"))
assert code == 200
cid = res["id"]
name = f"{cid}.png"
assert get(f"/media/{name}")[0] == 404, "受付中の写真は見えない"
assert b"<script>x" not in get("/public")[1]
assert list_contributions() == []
assert contrib.approve(cid, "確認者") == []
page = get("/public")[1].decode()
assert cid in page and "&lt;script&gt;" in page and "<script>x" not in page
assert "someone@example.test" not in page and get(f"/media/{name}")[0] == 200
pub = (pathlib.Path(tmp) / "contributions" / f"{cid}.json").read_text(encoding="utf-8")
assert "someone@example.test" not in pub and "attest" not in pub
assert [c["id"] for c in list_contributions()] == [cid] and list_contributions()[0]["certainty"] == "覚えている"
assert get("/media/..%2f..%2fetc%2fpasswd")[0] == 404
contrib.withdraw(cid)
assert list_contributions() == [] and get(f"/media/{name}")[0] == 404 and cid not in get("/public")[1].decode()
assert not (pathlib.Path(tmp) / "contributions_inbox" / f"{cid}.private").exists()
new, _ = contrib.submit(base())
assert new != cid, "取り下げの番号を使い回さない"
srv.shutdown()
