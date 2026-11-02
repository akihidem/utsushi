"""持ち寄りの床の試験。本物のデータに触らないよう、置き場を使い捨てにする。"""
import base64
import io
import json
import socket
import subprocess
import sys
import os
import pathlib
import tempfile
import threading
import urllib.error
import urllib.request

tmp = tempfile.mkdtemp()
os.environ["OMOCHAE_DATA"] = tmp

from PIL import Image

from api.tools import list_contributions
from omochae import contrib
from web.contrib_server import serve

def image_b64(fmt="PNG", **kw):
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), "red").save(buf, format=fmt, **kw)
    return base64.b64encode(buf.getvalue()).decode()


PNG = image_b64()


def base(**kw):
    c = {"kind": "memory", "role": "memory", "certainty": "覚えている", "body": "筒を下げて遊んだ", "toy_name": "御来迎", "where_when": "昭和の頃",
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
# 先頭だけ PNG の偽物を、画像として読んで落とす。
fake = base64.b64encode(b"\x89PNG\r\n\x1a\nPK\x03\x04 not an image").decode()
assert floors(contrib.submit(base(kind="photo", rights={"basis": "own_work", "holder": "本人", "license": "display_only"}), fake)[1]) == {"F10.intake"}
for broken in ({"kind": []}, {"role": {}}, {"certainty": []}, {"body": "\ud800"}, {"body": "\x1b[2Jx"}, {"contact": "\ud800"}):
    assert floors(contrib.submit(base(**broken))[1]) == {"F10.intake"}, broken
assert floors(contrib.submit(base(kind="info", origin=""))[1]) == {"F10.intake"}
assert floors(contrib.submit(base(where_when=""))[1]) == {"F10.intake"}
big = base64.b64encode(b"\xff\xd8\xff" + b"0" * (contrib.MAX_IMAGE + 1)).decode()
assert floors(contrib.submit(base(kind="photo", rights={"basis": "own_work", "holder": "本人", "license": "display_only"}), big)[1]) == {"F10.intake"}
# F10.rights
assert "F10.rights" in floors(contrib.submit(base(kind="photo"), PNG)[1])
assert "F10.rights" in floors(contrib.submit(base(), PNG)[1]), "写真つきの思い出も持ち主が要る"
for holder in (123, {"a": 1}, ["x"], True, "あ" * 101):
    assert floors(contrib.submit(base(rights={"basis": "own_work", "holder": holder, "license": "display_only"}))[1]) == {"F10.rights"}
for key, value in (("basis", []), ("license", {})):
    r = {"basis": "own_work", "holder": "", "license": "display_only", key: value}
    assert floors(contrib.submit(base(rights=r))[1]) == {"F10.rights"}
cid, fs = contrib.submit(base(rights={"basis": "unknown", "holder": "", "license": "display_only"}))
assert not fs and floors(contrib.approve(cid, "確認者")) == {"F10.rights"}
# F10.review
cid, _ = contrib.submit(base())
assert floors(contrib.approve(cid, " ")) == {"F10.review"}
assert contrib.reject(cid, "確認者") == []
assert floors(contrib.approve(cid, "確認者")) == {"F10.review"}
# F10.pii
for text in ("連絡は a.b@example.com まで", "電話 03-1234-5678", "〒100-0001 のお店", "携帯09012345678", "03 - 1234 - 5678", "03.1234.5678", "(03)1234-5678",
             "０３（１２３４）５６７８", "090−1234−5678", "090–1234–5678", "+81-(0)90-1234-5678", "a＠example．com", "a@example。com", "a@exam\u200bple.com",
             "03\u200b-1234-5678", "〒1000001", "郵便番号1000001", "〒100 0001", "a at example dot com"):
    cid, _ = contrib.submit(base(body=text))
    assert floors(contrib.approve(cid, "確認者")) == {"F10.pii"}, text
cid, _ = contrib.submit(base(rights={"basis": "own_work", "holder": "x@example.com", "license": "display_only", "phone": "090-9999-8888"}, source_id="090-1111-2222"))
assert floors(contrib.approve(cid, "確認者")) == {"F10.pii"}
inbox_text = (pathlib.Path(tmp) / "contributions_inbox" / f"{cid}.json").read_text(encoding="utf-8")
assert "090-9999-8888" not in inbox_text, "rights の知らない項目を保存しない"
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


ORIGIN = {"Origin": f"http://127.0.0.1:{port}"}
assert post(base(), {"Origin": "https://evil.example"})[0] == 403
assert post(base())[0] == 403, "Origin の無い POST を断る"
assert post(base(attest={}), ORIGIN)[0] == 422


def raw_request(payload):
    with socket.create_connection(("127.0.0.1", port)) as s:
        s.sendall(payload)
        return s.recv(200).decode("latin1").split(" ")[1]


# DNS rebinding の形: Host と Origin が外の名前でそろっている
body = json.dumps(base()).encode()
assert raw_request(b"POST /api/contribute HTTP/1.1\r\nHost: evil.example:%d\r\nOrigin: http://evil.example:%d\r\nContent-Type: application/json\r\nContent-Length: %d\r\n\r\n" % (port, port, len(body)) + body) == "403"
assert raw_request(b"GET /public HTTP/1.1\r\nHost: evil.example\r\n\r\n") == "403"
deep = b"[" * 200000
assert raw_request(b"POST /api/contribute HTTP/1.1\r\nHost: 127.0.0.1:%d\r\nOrigin: http://127.0.0.1:%d\r\nContent-Type: application/json\r\nContent-Length: %d\r\n\r\n" % (port, port, len(deep)) + deep) == "400"
code, res = post(base(kind="photo", image=PNG, rights={"basis": "own_work", "holder": "山田", "license": "CC-BY-4.0"}, body="<script>x</script>"), ORIGIN)
assert code == 200
cid = res["id"]
name = f"{cid}.png"
assert get(f"/media/{name}")[0] == 404, "受付中の写真は見えない"
assert b"<script>x" not in get("/public")[1]
assert list_contributions() == []
cli = subprocess.run([sys.executable, "-m", "omochae.contrib", "approve", cid, "--reviewer", "Claude"], capture_output=True, text=True, stdin=subprocess.DEVNULL, start_new_session=True)
assert cli.returncode == 3 and "F10.review" in cli.stderr, "端末で人が打たないと公開できない"
assert list_contributions() == []
assert contrib.approve(cid, "確認者") == []
assert floors(contrib.reject(cid, "確認者")) == {"F10.review"}, "承認の後に却下で公開を残さない"
page = get("/public")[1].decode()
assert cid in page and "&lt;script&gt;" in page and "<script>x" not in page
assert "someone@example.test" not in page and get(f"/media/{name}")[0] == 200
pub = (pathlib.Path(tmp) / "contributions" / f"{cid}.json").read_text(encoding="utf-8")
assert "someone@example.test" not in pub and "attest" not in pub
assert [c["id"] for c in list_contributions()] == [cid] and list_contributions()[0]["certainty"] == "覚えている"
assert get("/media/..%2f..%2fetc%2fpasswd")[0] == 404
# 1 件の壊れた記録で全体を止めない
pub_dir = pathlib.Path(tmp) / "contributions"
(pub_dir / "C-9000.json").write_text('{"id":', encoding="utf-8")
(pub_dir / "C-9001.json").write_text('{"id":"C-9001","status":"approved","rights":{"holder":123}}', encoding="utf-8")
assert get("/public")[0] == 200 and cid in get("/public")[1].decode()
(pub_dir / "C-9000.json").unlink()
(pub_dir / "C-9001.json").unlink()
backup = (pub_dir / f"{cid}.json").read_text(encoding="utf-8")
(pathlib.Path(tmp) / "contributions_inbox" / f"{cid}.json").rename(pathlib.Path(tmp) / "moved.json")
contrib.withdraw(cid)  # 受付箱が無い機械でも効く
(pub_dir / f"{cid}.json").write_text(backup, encoding="utf-8")  # 別の経路で戻っても出さない
assert list_contributions() == [] and get(f"/media/{name}")[0] == 404 and cid not in get("/public")[1].decode()
assert not (pathlib.Path(tmp) / "contributions_inbox" / f"{cid}.private").exists()
new, _ = contrib.submit(base())
assert new != cid, "取り下げの番号を使い回さない"
# 付帯情報を公開に持ち越さない
exif = Image.Exif()
exif[0x010e] = "GPS35.7148N139.7967E_home"
gid, fs = contrib.submit(base(kind="photo", rights={"basis": "own_work", "holder": "本人", "license": "display_only"}), image_b64("JPEG", exif=exif))
assert not fs
saved = (pathlib.Path(tmp) / "contributions_media" / f"{gid}.jpg").read_bytes()
assert b"GPS35" not in saved
# 却下で他人の写真と連絡先を残さない
assert contrib.reject(gid, "確認者") == [] and not (pathlib.Path(tmp) / "contributions_media" / f"{gid}.jpg").exists()
# 「表示だけ」の投稿は Claude に渡さない
did, _ = contrib.submit(base())
assert contrib.approve(did, "確認者") == [] and did not in [c["id"] for c in list_contributions()]
# 連絡先は他の利用者から読めない
cid2, _ = contrib.submit(base())
private = pathlib.Path(tmp) / "contributions_inbox" / f"{cid2}.private"
assert private.stat().st_mode & 0o077 == 0
srv.shutdown()
