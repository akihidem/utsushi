"""ループ1（Issue #335）: 話した考えから作った紙（OWN-n）と、話した字が刷られた手順の紙は、作った本人の画面からしか開かない。合言葉なしの場では開かない（J-028 の線）。

見る線:
- その場限りの印（who）を確かめて頼んだ人にだけ、紙の鍵を cookie で渡す。URL に載せないので、URL を渡されても開かない。
- 鍵の無い人・別の案の鍵の人には、絵も PDF も SVG も手順の紙も開かない（在るかどうかも言わない）。頼んだ後の頁も、採る釦も同じ。
- 同じ印の人が押し直すと、鍵を受け取り直せる。書いて立てた仮説の紙は今までどおり。
- 合言葉なしの場: 書いた物も含めて OWN-n の紙は開かない。紙を作る節も受け口も閉じる。
- 共用の機械（次の人が同じブラウザに座る）: 鍵は期限の中だけ効く（頼んだ・作る側が書いた・採った時の一番新しい物から 2 時間）。期限はサーバが見る。
  記録を残すと、その案は閉じる（交代の区切り。1 人の作業は 2 時間より短いので、期限だけでは次の人に間に合わない）。同じタブの印でも受け取り直せない。
  試した後の紙は話した字が刷られないので、記録があれば誰にも開く（tests/test_loop1_next.py）。
"""
import json
import os
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

DATA = tempfile.mkdtemp()
os.environ["OMOCHAE_DATA"] = DATA
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(DATA, "api-usage.jsonl")  # 本物の台帳に書かない（#151）

from api import words  # noqa: E402
from omochae import hypotheses, loop, making_log, talk_log  # noqa: E402
from web import think_sheet  # noqa: E402
from web.play_server import out_dir, serve  # noqa: E402

G = "NDL-1187053-R0000005-L"
WHO, OTHER = "abcdefgh12", "zyxwvuts98"
SAID, SAID2 = "割り箸の柄で押したら大きく開くと思う", "柄を長くしたい"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


opener = urllib.request.build_opener(NoRedirect)


def start(**kw):
    server = serve(0, **kw)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


def send(base, path, data=None, cookie=""):
    headers = {"Content-Type": "application/x-www-form-urlencoded", "Origin": base}
    if cookie:
        headers["Cookie"] = cookie
    req = urllib.request.Request(base + path, data=urllib.parse.urlencode(data).encode() if data is not None else None, method="POST" if data is not None else "GET", headers=headers)
    try:
        r = opener.open(req)
        return r.status, r.read(), r.headers
    except urllib.error.HTTPError as e:
        return e.code, e.read(), e.headers


def ask(base, who, text):
    """考えを残して頼む。頁と同じ口から話す（考えにはたたき台の印が付く。hanasu.think_section）。Returns (Location, cookie の「名=値」)。"""
    code, _, _ = send(base, f"/toy/{G}/talk", {"scene": "think", "hypothesis": hypotheses.sheet_of(G)["id"], "text": text, "who": who})
    assert code == 303, code
    code, _, h = send(base, f"/toy/{G}/think-sheet", {"who": who})
    assert code == 303, code
    return h["Location"], h["Set-Cookie"].split(";")[0]


server, base = start()
loc, key = ask(base, WHO, SAID)
token = urllib.parse.parse_qs(urllib.parse.urlsplit(loc).query)["at"][0][len("think-"):]
attrs = send(base, f"/toy/{G}/think-sheet", {"who": WHO})[2]["Set-Cookie"]
assert "HttpOnly" in attrs and "SameSite=Lax" in attrs and "Max-Age" not in attrs, attrs  # 画面の JS から読まない。ブラウザを閉じれば消える
assert "Path=/;" in attrs or attrs.endswith("Path=/"), attrs
assert key.split("=", 1)[1] == token and token not in key.split("=", 1)[0], "鍵の名前に値を入れない"

# 頼んだ後の頁は、鍵のある人だけに字を見せる（URL だけでは開かない）
path = loc.split("#")[0]
w = words.by_token(G, token)
assert not words.fill_think(w["id"], words.think_result(w["base_params"], {"push_part": "stick", "pusher_height": 84}), "作る側")[1]
assert SAID in send(base, path, cookie=key)[1].decode(), "本人には見える"
for c in ("", "utsushi_own_W-9999=nothing"):
    assert SAID not in send(base, path, cookie=c)[1].decode(), "URL を渡されても、話した字は見えない"

# 採る釦も、鍵のある人だけ
assert send(base, f"/toy/{G}/think-ok", {"t": token})[0] == 422, "印を知っていても、鍵が無いと採れない"
assert hypotheses.own_hypotheses(G) == [] and not out_dir(G).exists()
assert send(base, f"/toy/{G}/think-ok", {"t": token}, cookie=key)[0] == 303
oid = words.by_token(G, token)["own_id"]
names = sorted(p.name for p in out_dir(G).glob(f"{oid}_v*"))
# 刷るのは型紙だけ（窓口の決定 2026-11-07 カード 012120。#493 と同じ形）。手順の紙と試した後の紙は組まない
assert {f"{oid}_v1.pdf", f"{oid}_v1.png"} <= set(names) and not [n for n in names if "_tejun" in n or "_after" in n], names

# 紙は、作った本人にだけ開く
_, other_key = ask(base, OTHER, SAID2)
for name in names:
    if name.endswith((".pdf", ".png", ".svg")) and "_after" not in name:
        code, body, _ = send(base, f"/sheet/{G}/{name}", cookie=key)
        assert code == 200 and body, (name, code)
        for c in ("", other_key, "utsushi_own_W-0001=nothing"):
            code, body, _ = send(base, f"/sheet/{G}/{name}", cookie=c)
            assert code == 404 and SAID.encode() not in body, (name, c, code)
        assert send(base, f"/sheet/{G}/{name}?t={token}")[0] == 404, "URL に印を付けても開かない"
# 本人の頁のリンクと絵が開く（鍵で）
page = send(base, path, cookie=key)[1].decode()
assert f"/sheet/{G}/{oid}_v1.pdf" in page and f"/sheet/{G}/{oid}_v1.png" in page
assert SAID not in send(base, f"/toy/{G}", cookie=other_key)[1].decode(), "ほかの人の頁に出ない"

# 同じ印の人が押し直すと、鍵を受け取り直せる（ブラウザを閉じた後でも、同じ画面の印があれば）
code, _, h = send(base, f"/toy/{G}/think-sheet", {"who": WHO})
assert code == 303 and h["Set-Cookie"].split(";")[0] == key
code, _, h = send(base, f"/toy/{G}/think-sheet", {"who": "nobody0001"})
assert code == 422 and not h.get("Set-Cookie"), "ほかの印には渡さない"

# 書いて立てた仮説の紙は今までどおり（鍵なしで開く）
typed, _ = hypotheses.save_own(G, "書いた案", "書いて立てた動かし方", "右の図")
assert hypotheses.print_own(G, typed["id"], str(hypotheses.play_dir(G) / f'{typed["id"]}_v1')) == 0
assert send(base, f"/sheet/{G}/{typed['id']}_v1_free.pdf")[0] == 200


# ── 共用の機械: 鍵の期限 ──
def token_of(location):
    return urllib.parse.parse_qs(urllib.parse.urlsplit(location).query)["at"][0][len("think-"):]


def filled(token):
    w = words.by_token(G, token)
    assert not words.fill_think(w["id"], words.think_result(w["base_params"], {"push_part": "stick", "pusher_height": 84}), "作る側")[1]


def adopted(who, text):
    """頼んで、作る側が書き、本人が採る。Returns (印, 鍵, OWN の番号, 頼んだ後の頁の道)。"""
    location, k = ask(base, who, text)
    t = token_of(location)
    filled(t)
    assert send(base, f"/toy/{G}/think-ok", {"t": t}, cookie=k)[0] == 303
    return t, k, words.by_token(G, t)["own_id"], location.split("#")[0]


def age(t, minutes=None, broken=False):
    """その案の時刻を、今から minutes 分前にする。"""
    w = words.by_token(G, t)
    when = "こわれた" if broken else (datetime.now(timezone(timedelta(hours=9))) - timedelta(minutes=minutes)).isoformat(timespec="seconds")
    times = {k: when for k in ("asked_at", "filled_at", "decided_at") if k in w}
    (loop.folder() / f"words-{w['id'][2:]}.json").write_text(json.dumps({**w, **times}, ensure_ascii=False), encoding="utf-8")


def opened(k, oid, kind=""):
    return send(base, f"/sheet/{G}/{oid}_v1{kind}.pdf", cookie=k)[0]


TEXT = "柄を太くすると押しやすいと思う"
t1, k1, o1, p1 = adopted("expiry0001", TEXT)
age(t1, 119)
assert opened(k1, o1) == 200 and TEXT in send(base, p1, cookie=k1)[1].decode(), "期限の中は開く"
age(t1, 121)
assert opened(k1, o1) == 404 and opened(k1, o1, "_tejun") == 404, "期限を過ぎると、鍵があっても開かない"
assert TEXT not in send(base, p1, cookie=k1)[1].decode(), "期限を過ぎると、話した字も見えない"
code, _, h = send(base, f"/toy/{G}/think-sheet", {"who": "expiry0001"})
assert code == 422 and not h.get("Set-Cookie"), "同じ印で押し直しても、期限を過ぎた鍵は渡さない（同じタブの次の人）"
age(t1, broken=True)
assert opened(k1, o1) == 404, "時刻が読めない時は閉じる側に倒す"
# 採る前の案も、期限を過ぎると採れない
loc2, k2 = ask(base, "expiry0002", "筒を細くしたい")
t2 = token_of(loc2)
filled(t2)
age(t2, 121)
assert send(base, f"/toy/{G}/think-ok", {"t": t2}, cookie=k2)[0] == 422 and words.by_token(G, t2)["status"] == "pending_human"
# 作る側が後から書くと、そこから 2 時間は開く（待っていた人が受け取れる）
loc3, k3 = ask(base, "expiry0003", "折りを増やしたい")
t3 = token_of(loc3)
age(t3, 180)
assert send(base, f"/toy/{G}/think-sheet", {"who": "expiry0003"})[0] == 422, "待ちの間も期限は同じ"
filled(t3)
code, _, h = send(base, f"/toy/{G}/think-sheet", {"who": "expiry0003"})
assert code == 303 and h["Set-Cookie"].split(";")[0] == k3
assert "折りを増やしたい" in send(base, loc3.split("#")[0], cookie=k3)[1].decode()
# 頼まないまま古くなった考えは、頼めない（同じタブの次の人が、前の人の字で頼まない）
talk_log.add(G, "think", "古い考え", who="expiry0004")
_, stem = words.latest_think(G, "expiry0004")
talk_path = making_log.folder() / f"{stem}.json"
talk_path.write_text(json.dumps({**json.loads(talk_path.read_text(encoding="utf-8")), "at": "2026-11-05T08:00+09:00"}, ensure_ascii=False), encoding="utf-8")
assert send(base, f"/toy/{G}/think-sheet", {"who": "expiry0004"})[0] == 422 and "古い考え" not in str([w["how_it_moves"] for w in words.waiting()])

# ── 共用の機械: 記録を残すと、その案は閉じる（交代の区切り） ──
for route, want, who, text in (("record", 303, "handover01", "下から押したい"), ("record-json", 201, "handover02", "上から押したい")):
    t, k, used, p = adopted(who, text)
    # 自分の紙も型紙だけ（窓口の決定 2026-11-07 カード 012120）。手順の紙は組まないので開く物が無い
    assert opened(k, used) == 200 and opened(k, used, "_tejun") == 404
    # 記録の form: 本人にだけ、その案の選び肢が出て、選ばれている（作った紙の記録として残すため）。ほかの人の案は並べない（型紙は玩具ごとに 1 枚。J-032）
    label = f'<option value="{used}" selected>'
    assert label in send(base, f"/toy/{G}", cookie=k)[1].decode(), f"{route}: 本人の form に自分の案"
    assert f'value="{used}"' not in send(base, f"/toy/{G}")[1].decode(), f"{route}: ほかの人の form に出さない"
    assert send(base, f"/toy/{G}/{route}", {"hypothesis": used, "result": "わからない", "who": who})[0] == 422, f"{route}: 鍵の無い人の記録は受けない"
    assert send(base, f"/toy/{G}/{route}", {"hypothesis": used, "result": "わからない", "who": who}, cookie=k)[0] == want, route
    assert opened(k, used) == 404 and opened(k, used, "_tejun") == 404, f"{route}: 記録を残すと、紙も手順の紙も閉じる"
    assert text not in send(base, p, cookie=k)[1].decode(), f"{route}: 話した字も見えない"
    assert opened(k, used, "_after") == 200, f"{route}: 試した後の紙は、記録の後に本人が使う（話した字は刷られない）"
    assert opened("", used, "_after") == 200, f"{route}: 記録があれば別の人にも開く（話した字が無い紙。tests/test_loop1_next.py）"
    code, _, h = send(base, f"/toy/{G}/think-sheet", {"who": who})
    assert code == 422 and not h.get("Set-Cookie"), f"{route}: 同じタブの次の人が押しても、前の人の案へ戻らない"
    assert f'value="{used}"' not in send(base, f"/toy/{G}", cookie=k)[1].decode(), f"{route}: 閉じた案は form にも出さない"
# 次の人が同じタブで話せば、その人の案を作れる。前の人の案は閉じたまま
loc4, k4 = ask(base, "handover01", "次の人の考え")
t4 = token_of(loc4)
assert words.by_token(G, t4)["how_it_moves"] == "次の人の考え" and k4 != k
# 別の紙の記録でも、考えが結ばれれば閉じる（その人の作りの区切り）
t5, k5, o5, p5 = adopted("handover03", "別の紙を試した")
assert send(base, f"/toy/{G}/record", {"hypothesis": "H-A", "result": "わからない", "who": "handover03"})[0] == 303
assert opened(k5, o5) == 404
# 頼まないまま記録に結ばれた考えからも、頼めない。その前の結ばれていない考えへも戻らない（同じタブの次の人が、前の人の字で頼まない）
talk_log.add(G, "think", "別の仮説を見た前の考え", hypothesis_id="H-C", who="handover04")
talk_log.add(G, "think", "記録に結ばれる考え", who="handover04")
assert send(base, f"/toy/{G}/record", {"hypothesis": "H-A", "result": "わからない", "who": "handover04"})[0] == 303
code, _, h = send(base, f"/toy/{G}/think-sheet", {"who": "handover04"})
assert code == 422 and not h.get("Set-Cookie"), "結ばれた考えから頼めない"
assert not {"記録に結ばれる考え", "別の仮説を見た前の考え"} & {w["how_it_moves"] for w in words.waiting()}, "案を作らない"
# 対照: 合言葉の場では、この鍵でこの案が開く（下の断りが、閉じた案を見ているだけにならないように）
assert f'data-hid="{oid}"' in send(base, f"/toy/{G}/tsukuru?h={oid}", cookie=key)[1].decode() and f'data-hid="{oid}"' in send(base, f"/toy/{G}/techo", cookie=key)[1].decode()
server.shutdown()

# ── 合言葉なしの場 ──
server, base = start(public_open=True)
for name in (f"{oid}_v1.pdf", f"{oid}_v1.png", f"{oid}_v1_tejun.pdf", f"{typed['id']}_v1_free.pdf"):
    assert send(base, f"/sheet/{G}/{name}", cookie=key)[0] == 404, name
assert send(base, f"/sheet/{G}/H-A_v1.pdf")[0] in (200, 404), "元の仮説の道は変えない"
assert f'data-hid="{oid}"' not in send(base, f"/toy/{G}/tsukuru?h={oid}", cookie=key)[1].decode(), "鍵があっても、作りながら見る頁に本人の紙を開かない"
assert oid not in send(base, f"/toy/{G}/techo", cookie=key)[1].decode(), "手帖にも出さない"
code, body, _ = send(base, f"/toy/{G}")
assert code == 200 and think_sheet.GO not in body.decode() and f"{typed['id']}_v1_free.pdf" not in body.decode(), "開かない紙の入口を出さない"
talk_log.add(G, "think", "公開の場で話した考え", who="pubwho0001")
before = len(words.waiting())
assert send(base, f"/toy/{G}/think-sheet", {"who": "pubwho0001"})[0] == 403
assert send(base, f"/toy/{G}/think-ok", {"t": token}, cookie=key)[0] == 403
assert len(words.waiting()) == before, "合言葉なしの場では案を作らない"
assert SAID not in send(base, path, cookie=key)[1].decode(), "鍵があっても字を出さない"
server.shutdown()
print("ok")
