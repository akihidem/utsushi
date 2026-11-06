"""写真を、この画面が残した記録に足す（1 回の作りが 2 つの記録に割れる所の直し）。番号では足さない。写真の受け口も同じ鍵で照らす。

前の形: 作りながら見るの「できた」の後は玩具の頁の記録の欄に着き、そこに写真の口が無い。記録の後に手帖で写真を上げると、別の記録になった。
直した形: 手帖が「写真あり」の合図を送ると、この画面が玩具の頁の記録の欄で残した記録（記録の鍵 records.mine）で、同じ玩具の、写真の無い物に足す。
新しい記録は作らない。頁から番号は受けない（番号は札に出る連番なので、別の人が送れる）。写真の受け口も、番号だけでは受けない。
足さない時: 欄に新しい中身（字・別の見た事）がある時（足すと、書いた事が残らない）。別の紙や版を選んでいる時。手帖で残した記録（写真の口のある所で「記録だけ」を選んだ物。
机の端の 1 台を順に使う場で、次の人の写真が前の人の記録に付かないように）。頁の動きは tests/test_photo_attach_walk.py が Chrome で歩いて見る。
"""
import io
import json
import os
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ.pop("ANTHROPIC_API_KEY", None)

from PIL import Image  # noqa: E402

from api import ask  # noqa: E402
from omochae import records  # noqa: E402
from web import play_server, techo_site  # noqa: E402
from web.play_server import REC_COOKIE, serve  # noqa: E402

ask._key_present = lambda: False  # 合言葉なしの場は鍵のある所で立たない。鍵のある機械でも同じに動かす

G, T = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"
from omochae import hypotheses  # noqa: E402
# 御来迎のたたき台は組ごと（今の組 goraigo-v14 は H-C・記録の欄 sheet_by_set）。今の組で刷れるのはたたき台の紙だけ
GS = hypotheses.sheet_of(G)["id"]
server = serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"
opener = urllib.request.build_opener(type("NoRedirect", (urllib.request.HTTPRedirectHandler,), {"redirect_request": lambda *a, **k: None}))
_photo = io.BytesIO()
Image.new("RGB", (8, 8), (200, 180, 140)).save(_photo, "JPEG")
JPEG = _photo.getvalue()
FAKE = f"{REC_COOKIE}=xxxxxxxxxxxxxxxxxxxxxxxx"


def send(path, data=None, cookie="", ctype="application/x-www-form-urlencoded"):
    body = urllib.parse.urlencode(data).encode() if isinstance(data, dict) else data
    headers = {"Origin": base} | ({"Content-Type": ctype} if body is not None else {}) | ({"Cookie": cookie} if cookie else {})
    req = urllib.request.Request(base + path, data=body, headers=headers, method="POST" if body is not None else "GET")
    try:
        r = opener.open(req, timeout=120)
        return r.status, r.read().decode("utf-8", "replace"), r.headers.get_all("Set-Cookie") or []
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace"), e.headers.get_all("Set-Cookie") or []


def key_of(cookies):
    """返事が渡した記録の鍵を、次の送信に付ける形で返す（無ければ空）。"""
    for c in cookies:
        name, _, rest = c.partition("=")
        if name == REC_COOKIE and rest.split(";")[0]:
            return f"{REC_COOKIE}={rest.split(';')[0]}"
    return ""


def attach(sid, cookie="", **more):
    """手帖の「写真あり」の合図。返すのは (状態, 返事, 渡された鍵)。"""
    code, body, cookies = send(f"/toy/{sid}/record-json", {"attach": "1", "hypothesis": hypotheses.sheet_of(sid)["id"]} | more, cookie=cookie)
    return code, json.loads(body), key_of(cookies)


def toy_record(sid, result, cookie=""):
    """玩具の頁の記録の欄で残す（写真の口が無い所）。返すのは (記録の番号, 残した画面に渡った鍵)。"""
    code, _, cookies = send(f"/toy/{sid}/record", {"hypothesis": hypotheses.sheet_of(sid)["id"], "result": result}, cookie=cookie)
    assert code == 303 and key_of(cookies), (code, cookies)
    return records.all_records(sid)[-1]["id"], key_of(cookies)


def photo(rid, cookie=""):
    return send(f"/record/{rid}/media", JPEG, cookie=cookie, ctype="image/jpeg")[0]


count = lambda sid: len(records.all_records(sid))
for sid in (G, T):
    assert send(f"/toy/{sid}/print", {"hypothesis": hypotheses.sheet_of(sid)["id"]})[0] in (200, 303)
first, mine = toy_record(G, "動いた")
assert first == "R-0001" and count(G) == 1

# ---- 足す: 新しい記録を作らず、この画面の記録の番号が返る。見た事は求めない。鍵は作り直さない（期限の数え方が続く）
assert attach(G, mine) == (200, {"id": first, "attached": True}, "")
# 同じ紙の同じ見た事を選び直した時も、同じ作りの事なので足す（手帖の欄は見た事が先に並ぶ）
assert attach(G, mine, result="動いた")[1] == {"id": first, "attached": True}
assert count(G) == 1, "合図だけでは記録は増えない"

# ---- 足さない: 欄に新しい中身がある時。足すと、書いた事が残らない。頁は今までどおり新しい記録を作る
for label, more in (("別の見た事", {"result": "動かない"}), ("ひとこと", {"note": "扇が引っかかった"}), ("工夫した所", {"result": "動いた", "fix_part": "扇"}),
                    ("感想", {"impression": "楽しかった"}), ("見た事と字", {"result": "動いた", "note": "二度目"})):
    assert attach(G, mine, **more)[1] == {"attached": False}, label
# 別の版の紙への返事は、別の作り（版は画面が言う。ここでは受け口の読みを差し替えて、版 2 と言われた形にする）
keep_version = play_server.sheet_version_of
play_server.sheet_version_of = lambda sid, hid, form: 2
try:
    assert attach(G, mine, result="動いた")[1] == {"attached": False}, "別の版"
    assert attach(G, mine)[1] == {"attached": False}, "見た事を選んでいなくても、選んだ紙の版が違えば足さない"
    assert attach(G, mine, hypothesis="")[1] == {"id": first, "attached": True}, "紙が来ない時（頁で最初から選ばれているまま）は、紙と版を見ない"
finally:
    play_server.sheet_version_of = keep_version
# 別の紙を選んだ時は、見た事を選んでいなくても足さない（別の紙の作りの写真を、前の紙の記録に付けない）
assert attach(G, mine, hypothesis="H-Z")[1] == {"attached": False}
assert attach(G, mine, hypothesis="")[1] == {"id": first, "attached": True}
assert attach(G, mine, hypothesis="", result="動いた")[1] == {"attached": False}, "見た事だけで紙の無い送りには足さない"

# ---- 番号は受けない: 鍵の無い画面と、でたらめの鍵の画面からは、番号を添えても足せない。記録も増えない
for other in ("", FAKE):
    assert attach(G, other, record=first, id=first)[1] == {"attached": False}, other
assert attach(T, mine)[1] == {"attached": False}, "別の玩具の手帖からは足さない"
assert count(G) == 1 and count(T) == 0

# ---- 写真の受け口も同じ鍵で照らす: 番号を知っていても、記録を残した画面でなければ送れない
assert photo(first) == 403 and photo(first, FAKE) == 403 and techo_site.media_of(first) == []
assert photo(first, mine) == 201 and techo_site.media_of(first) == ["m1.jpg"]
assert photo("R-9999", mine) == 403, "無い記録にも置かない（在るか無いかも答えない）"
# 写真のある記録には、もう足さない（次に上げる時は、今までどおり見た事を選んで新しい記録になる）。写真の続きは同じ鍵で送れる
assert attach(G, mine)[1] == {"attached": False}
assert photo(first, mine) == 201 and techo_site.media_of(first) == ["m1.jpg", "m2.jpg"]

# ---- 今までの道は変わらない: 手帖で見た事を選んで残すと新しい記録ができ、その画面の鍵で写真を送れる
code, body, cookies = send(f"/toy/{G}/record-json", {"hypothesis": GS, "result": "動かない"}, cookie=mine)
second, second_key = json.loads(body)["id"], key_of(cookies)
assert code == 201 and second == "R-0002" and second_key and second_key != mine, (code, body)
# 手帖で残した記録には足さない（写真の口のある所で「記録だけ」を選んだ物。次の人の写真が前の人の記録に付かないように）
assert attach(G, second_key)[1] == {"attached": False} and attach(G, second_key, result="動かない")[1] == {"attached": False}
assert photo(second, second_key) == 201
# 次の記録を残した画面は、前の記録には送れない（記録を残すのが交代の区切り。机の端の 1 台を順に使う場）
assert photo(first, second_key) == 403

# ---- 期限（records.OWNER_MINUTES）を過ぎると、足さない・送れない
late_rid, late = toy_record(T, "揺れた")
keep = records.OWNER_MINUTES
records.OWNER_MINUTES = -1
try:
    assert attach(T, late)[1] == {"attached": False} and photo(late_rid, late) == 403
finally:
    records.OWNER_MINUTES = keep
assert attach(T, late)[1] == {"id": late_rid, "attached": True}

# ---- 合言葉なしで開く場は、写真を受けないので足す先も答えない
opened = serve(0, public_open=True)
threading.Thread(target=opened.serve_forever, daemon=True).start()
keep_base, base = base, f"http://127.0.0.1:{opened.server_address[1]}"
try:
    assert attach(T, late)[1] == {"attached": False}
finally:
    base = keep_base
    opened.shutdown()
server.shutdown()
print("ok 写真を足す: この画面が玩具の頁で残した記録にだけ足し、番号では足さない。新しい中身は新しい記録に。写真の受け口も鍵で照らす")
