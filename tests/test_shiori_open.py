"""しおりの開く道（/s/<印>・web.shiori_open）の試験。設計は grove の state/techo-card-20261108/README.md の 7 節と統括の決め（11-08）。

見る事:
1. 合言葉の門の外に出るのは GET と POST /s/<22 字> だけ（? の付いた物・頭の // も同じ道）。形の違う道・%・末の /・/s/close・
   ほかの頁は門の中。HEAD と OPTIONS は 501 で頁を出さない
2. 当たる前の頁に、記録の番号と門の中への道を出さない
3. 止めは cookie の前に効く: 違う順・数でない順は 422（落ちない）・10 分に 5 回で正しい順も 429・外の Origin は 403 で数えない
4. 当たると 303 と、開いた画面の cookie（HttpOnly・SameSite=Lax・合言葉付きの場は Secure・Max-Age なし）。合言葉の cookie は渡さない
5. その cookie で門の中の頁が開く。しおりの印だけの値では開かない。20 分さわらないと門も閉じる
6. とじると、写した値でも開かない。別の画面で開き直すと前の画面は開かない。使えなくすると、すぐ開かない
7. 公開の場（合言葉なし）は /s/<印> を断り、照らさず数えない
8. 開いた画面で残した記録は、そのしおりの並びに入る
"""
import http.client
import json
import os
import re
import tempfile
import threading
import types
import urllib.parse

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(os.environ["OMOCHAE_DATA"], "api-usage.jsonl")
os.environ["OMOCHAE_SHIORI_BASE"] = "https://example.org"

from omochae import hypotheses, shiori  # noqa: E402
from web import play_server, shiori_open  # noqa: E402

clock = [1_000_000.0]
shiori.time = types.SimpleNamespace(time=lambda: clock[0])  # 台帳の時刻だけを進める（20 分・10 分の止め）

KEY = "k" * 24
gated = play_server.serve(0, public_key=KEY)
opened = play_server.serve(0, public_open=True)
for s in (gated, opened):
    threading.Thread(target=s.serve_forever, daemon=True).start()
GP, OP = gated.server_address[1], opened.server_address[1]


def call(port, path, method="GET", form=None, cookie=None, origin=None):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
    headers = {"Host": f"127.0.0.1:{port}"}
    if cookie:
        headers["Cookie"] = cookie
    body = None
    if form is not None:
        body = urllib.parse.urlencode(form).encode()
        headers |= {"Content-Type": "application/x-www-form-urlencoded", "Origin": origin or f"http://127.0.0.1:{port}"}
    c.request(method, path, body=body, headers=headers)
    r = c.getresponse()
    out = (r.status, r.getheader("Location"), r.headers.get_all("Set-Cookie") or [], r.read().decode("utf-8", "replace"))
    c.close()
    return out


GATE = "合言葉が要ります"
s = shiori.make(records=[], now=clock[0])
T, ORDER = s["token"], ",".join(str(i) for i in s["order"])
wrong = ",".join(str(i) for i in [i for i in range(9) if i not in s["order"]][:3])
G = "NDL-1187053-R0000005-L"

# 1 門の外は 2 つの道だけ
code, _, cookies, page = call(GP, f"/s/{T}")
assert code == 200 and GATE not in page and shiori_open.LEAD in page, (code, page[:200])
assert call(GP, f"/s/{T}?a=1")[0] == 200
# 頭の // は http.server が / 1 つにそろえてから門と道が見る（同じ絵の頁になり、門の中の別の頁へは抜けない）
code, _, _, body = call(GP, f"//s/{T}")
assert code == 200 and shiori_open.LEAD in body and GATE not in body
for path in (f"/s/{T[:21]}", f"/s/{T}/", f"/s/{T}/x", f"//s/{T}/x", f"/s/{T[:21]}%41", f"/toy/{G}", f"/picture/{G}/small"):
    code, _, _, body = call(GP, path)
    assert code == 403 and GATE in body, (path, code)
code, _, _, body = call(GP, "/s/close", "POST", {})
assert code == 403 and GATE in body, "とじるは門の中"
for method in ("HEAD", "OPTIONS"):
    code, _, _, body = call(GP, f"/s/{T}", method)
    assert code == 501 and shiori_open.LEAD not in body, (method, code)

# 2 当たる前の頁: 記録の番号・門の中への道・帯が無い
assert not re.search(r"R-\d{4}", page) and not re.search(r'href="/', page), re.findall(r'href="[^"]*"', page)
assert f'action="/s/{T}"' in page and page.count("<button") >= 9

# 3 止めは cookie の前に効く
code, _, cookies, body = call(GP, f"/s/{T}", "POST", {"order": wrong})
assert code == 422 and shiori_open.WRONG in body and not cookies
code, _, cookies, body = call(GP, f"/s/{T}", "POST", {"order": "a,b,c"})
assert code == 422 and not cookies, "数でない順は落ちずに外れ"
code, _, cookies, refused = call(GP, f"/s/{T}", "POST", {"order": ORDER}, origin="https://example.com")
assert code == 403 and not cookies, "外の Origin は断る"
assert '<nav class="nav"' not in refused and "href=" not in refused.split("<body", 1)[-1], "外の Origin の断りの頁も、当たる前の頁と同じ帯なし・道なし"
code, _, cookies, refused = call(GP, f"/s/{T}?x=1", "POST", {"order": ORDER}, origin="https://example.com")
assert code == 403 and not cookies and '<nav class="nav"' not in refused, "問い付きの道でも、外の Origin の断りは帯なし（門の外の見分けと同じく ? より前で見る）"
entry = lambda tok: json.loads((shiori.folder() / shiori._name(tok)).read_text(encoding="utf-8"))
assert entry(T)["fails"] == 2, "外の Origin の頼みは数えない"
for _ in range(3):
    assert call(GP, f"/s/{T}", "POST", {"o1": "0", "o2": "0", "o3": "0"})[0] == 422  # 台本の無い画面の 3 つの選び（重なる順は外れ）
code, _, cookies, body = call(GP, f"/s/{T}", "POST", {"order": ORDER})
assert code == 429 and not cookies and shiori_open.WAIT in body, "10 分に 5 回で、正しい順も止まる"
clock[0] += 601

# 4 当たると 303 と開いた画面の cookie。合言葉の cookie は渡さない
code, where, cookies, _ = call(GP, f"/s/{T}", "POST", {"order": ORDER})
assert code == 303 and where == f"/s/{T}", (code, where)
assert len(cookies) == 1 and not any("utsushi_k" in c for c in cookies), cookies
line = cookies[0]
value = line.split(";", 1)[0].split("=", 1)[1]
parts = {x.strip() for x in line.split(";")[1:]}
assert parts == {"Path=/", "HttpOnly", "SameSite=Lax", "Secure"}, parts
assert value.startswith(T + ".") and len(value) == 45, value
mine = f"{shiori_open.COOKIE}={value}"

# 5 その cookie で門の中が開く・しおりの印だけでは開かない
code, _, _, body = call(GP, f"/toy/{G}", cookie=mine)
assert code == 200 and GATE not in body
code, _, _, body = call(GP, f"/s/{T}", cookie=mine)
assert code == 200 and shiori_open.OPENED in body and 'action="/s/close"' in body, "開いた画面は記録の並びととじる"
assert call(GP, f"/toy/{G}", cookie=f"{shiori_open.COOKIE}={T}")[0] == 403, "しおりの印だけの値では開かない"
assert call(GP, f"/toy/{G}", cookie=f"{shiori_open.COOKIE}={T}.{'A' * 22}")[0] == 403, "作った値では開かない"

# 8 開いた画面で残した記録は、そのしおりの並びに入る
H = hypotheses.sheet_of(G)["id"]
assert call(GP, f"/toy/{G}/print", "POST", {"hypothesis": H}, cookie=mine)[0] in (200, 303)
code, _, _, body = call(GP, f"/toy/{G}/record-json", "POST", {"hypothesis": H, "result": "動いた"}, cookie=mine)
rid = json.loads(body)["id"]
assert shiori.records_of(value) == [rid], shiori.records_of(value)
# 記録への道は手帖の記録の頁のその記録の札へ（つくるの頁から記録の札を外した 11-08・#657。前の /toy/<印>#<記録> は行き先の札が無い）
opened_body = call(GP, f"/s/{T}", cookie=mine)[3]
assert f'href="/toy/{G}/techo/kiroku#{rid}"' in opened_body and f'href="/toy/{G}#{rid}"' not in opened_body, "開いた画面の頁に、その記録への道"

# 5 の続き: 20 分さわらないと門も閉じる（触れば数え直す。1 分に 1 回）
clock[0] += 1199
assert call(GP, f"/toy/{G}", cookie=mine)[0] == 200
clock[0] += 1199
assert call(GP, f"/toy/{G}", cookie=mine)[0] == 200, "触った後は数え直す"
clock[0] += 1200
assert call(GP, f"/toy/{G}", cookie=mine)[0] == 403, "20 分さわらないと門も閉じる"

# 6 とじる・開き直す・使えなくする
clock[0] += 601
code, _, cookies, _ = call(GP, f"/s/{T}", "POST", {"order": ORDER})
first = f'{shiori_open.COOKIE}={cookies[0].split(";", 1)[0].split("=", 1)[1]}'
code, _, cookies, _ = call(GP, f"/s/{T}", "POST", {"order": ORDER})
second = f'{shiori_open.COOKIE}={cookies[0].split(";", 1)[0].split("=", 1)[1]}'
assert call(GP, f"/toy/{G}", cookie=first)[0] == 403 and call(GP, f"/toy/{G}", cookie=second)[0] == 200, "開き直すと前の画面は開かない"
code, where, cookies, _ = call(GP, "/s/close", "POST", {}, cookie=second)
assert code == 303 and any(c.startswith(f"{shiori_open.COOKIE}=;") and "Max-Age=0" in c for c in cookies), cookies
assert call(GP, f"/toy/{G}", cookie=second)[0] == 403, "とじた後は、写した値でも開かない"
code, _, cookies, _ = call(GP, f"/s/{T}", "POST", {"order": ORDER})
third = f'{shiori_open.COOKIE}={cookies[0].split(";", 1)[0].split("=", 1)[1]}'
assert call(GP, f"/toy/{G}", cookie=third)[0] == 200 and shiori.revoke(T)
assert call(GP, f"/toy/{G}", cookie=third)[0] == 403, "使えなくすると、すぐ開かない"
code, _, _, body = call(GP, f"/s/{T}")
assert code == 404 and shiori_open.CANNOT in body and not re.search(r'href="/', body)

# 7 公開の場は断り、照らさず数えない
u = shiori.make(now=clock[0])
before = entry(u["token"])["fails"]
for method, form in (("GET", None), ("POST", {"order": "0,1,2"})):
    code, _, cookies, body = call(OP, f"/s/{u['token']}", method, form)
    assert code == 403 and shiori_open.PUBLIC_REFUSE in body and not cookies, (method, code)
assert entry(u["token"])["fails"] == before and entry(u["token"])["tries"] == [], "公開の場では数えない"

gated.shutdown()
opened.shutdown()
print("ok しおりの開く道: 門の外は 2 つの道だけ・止めが cookie の前・合言葉は渡さない・20 分・とじる・開き直す・使えなくする・公開の場は断る")
