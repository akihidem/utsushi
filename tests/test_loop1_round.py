"""ループ1（Issue #335）: 本人の描く一周の順に、頁と同じ口を通して進む。部品ごとの試験が通っても、順に進むと工夫が記録に結ばれない形を、ここで押さえる。

順: たたき台を刷る → 考えを話す → この紙にする（OWN-n）→ 作りながら見る → 工夫を話す → 聞く → 記録を残す → 取り下げる。
見る線:
- 作りながら見る頁は、作った本人の画面からは、その人の紙（OWN-n）を開く。手順の文も、手順の紙の絵も、その紙の物。ほかの人には今のまま。
- 札・工夫・問い・記録は、作った本人の画面からだけ OWN-n に付く。
- 工夫も考えも、その紙の記録に結ばれ、札と輪の材料（maker_talk）に入る。束で 1 つの群になる。
- 手帖からでも同じ。型紙なしの紙でも同じ。
- 取り下げると、工夫の字も考えの字も消える。
"""
import json
import os
import pathlib
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

DATA = tempfile.mkdtemp()
os.environ["OMOCHAE_DATA"] = DATA
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(DATA, "api-usage.jsonl")  # 本物の台帳に書かない（#151）

from api import words  # noqa: E402
from omochae import engine_bundle, hypotheses, loop, records, talk_log  # noqa: E402
from web import hanasu  # noqa: E402
from web.play_server import serve  # noqa: E402

G = "NDL-1187053-R0000005-L"
server = serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


opener = urllib.request.build_opener(NoRedirect)


def send(path, data=None, cookie=""):
    headers = {"Content-Type": "application/x-www-form-urlencoded", "Origin": base}
    if cookie:
        headers["Cookie"] = cookie
    req = urllib.request.Request(base + path, data=urllib.parse.urlencode(data).encode() if data is not None else None, method="POST" if data is not None else "GET", headers=headers)
    try:
        r = opener.open(req)
    except urllib.error.HTTPError as e:  # 飛び先を追わないので、303 もここへ来る
        r = e
    return getattr(r, "code", r.status), r.read(), r.headers


def page(path, cookie=""):
    code, body, _ = send(path, cookie=cookie)
    return code, body.decode()


def everywhere(text):
    return [str(p.relative_to(DATA)) for p in pathlib.Path(DATA).rglob("*.json") if text in p.read_text(encoding="utf-8")]


def made(who, text, changed=None, not_fit=None):
    """話す → 頼む → 作る側が書く → この紙にする。頁と同じ口を通す。Returns (OWN の番号, 鍵)。"""
    assert send(f"/toy/{G}/talk", {"scene": "think", "hypothesis": hypotheses.sheet_of(G)["id"], "text": text, "who": who})[0] == 303
    code, _, h = send(f"/toy/{G}/think-sheet", {"who": who})
    assert code == 303, code
    key = h["Set-Cookie"].split(";")[0]
    token = key.split("=", 1)[1]
    w = words.by_token(G, token)
    assert not words.fill_think(w["id"], words.think_result(w["base_params"], changed, not_fit), "作る側")[1]
    assert send(f"/toy/{G}/think-ok", {"t": token}, cookie=key)[0] == 303
    return words.by_token(G, token)["own_id"], key


SHEET = hypotheses.sheet_of(G)["id"]
THINK, CRAFT = "割り箸の柄で押したら大きく開くと思う", "柄の先に紙を巻くと滑らない"
WHO, OTHER = "roundwho01", "roundwho02"

# たたき台を刷る
assert send(f"/toy/{G}/print", {"hypothesis": SHEET})[0] == 303
oid, key = made(WHO, THINK, {"push_part": "stick", "pusher_height": 84})

# ── 作りながら見る: 本人には、その人の紙が開く ──
code, body = page(f"/toy/{G}/tsukuru", cookie=key)
assert code == 200 and f'data-hid="{oid}"' in body, "紙の印が無ければ、本人の紙を開く"
assert f"{oid}_v1_tejun.png" in body and THINK not in body, "手順の紙の絵はその紙の物。話した字は頁に出さない"
assert page(f"/toy/{G}/tsukuru?h={oid}", cookie=key)[1].count(f'data-hid="{oid}"') == 1
assert send(f"/sheet/{G}/{oid}_v1_tejun.png", cookie=key)[0] == 200
total = body.count("<li")
assert total >= 2, "その紙の手順の文が出る"
# ほかの人には今のまま
assert 'data-hid="H-A"' in page(f"/toy/{G}/tsukuru")[1], "鍵の無い人には、たたき台の頁"
assert f'data-hid="{oid}"' not in page(f"/toy/{G}/tsukuru?h={oid}")[1], "番号を知っていても開かない"
# ほかの人の札・工夫・問い・記録は、その紙に付かない
assert send(f"/toy/{G}/step", {"hypothesis": oid, "event": "next", "step": 1, "who": OTHER})[0] == 422
assert send(f"/toy/{G}/talk", {"scene": "craft", "hypothesis": oid, "sheet_version": 1, "step": 1, "text": "ほかの人の工夫", "who": OTHER})[0] == 422
assert everywhere("ほかの人の工夫") == [], "ほかの人の字を残さない"
assert send(f"/toy/{G}/ask-json", {"hypothesis": oid, "question": "谷折りって？", "who": OTHER})[0] == 422
assert send(f"/toy/{G}/ask", {"hypothesis": oid, "question": "谷折りって？", "who": OTHER})[0] == 422
assert send(f"/toy/{G}/record-json", {"hypothesis": oid, "result": "わからない", "who": OTHER})[0] == 422
assert send(f"/toy/{G}/record", {"hypothesis": oid, "result": "わからない", "who": OTHER})[0] == 422
assert send(f"/toy/{G}/print-own", {"id": oid})[0] == 422, "ほかの人は刷り直せない"
assert records.all_records(G) == [], "ほかの人の記録を残さない"

# 本人の札・工夫・問いは、その紙に付く
assert send(f"/toy/{G}/step", {"hypothesis": oid, "event": "next", "step": 1, "sheet_version": 1, "who": WHO}, cookie=key)[0] == 303
assert send(f"/toy/{G}/talk", {"scene": "craft", "hypothesis": oid, "sheet_version": 1, "step": 2, "text": CRAFT, "who": WHO}, cookie=key)[0] == 200
said = [t for t in talk_log.talks(G, scene="craft") if t["text"] == CRAFT]
assert said and said[0]["hypothesis_id"] == oid and said[0]["step"] == 2, said
code, body, _ = send(f"/toy/{G}/ask-json", {"hypothesis": oid, "question": "糊代はどこ？", "who": WHO}, cookie=key)
assert code == 200 and json.loads(body)["from"] in ("no_key", "glossary"), body  # 紙の中身から答える道で落ちない（鍵が無いので no_key）
assert send(f"/toy/{G}/ask", {"hypothesis": oid, "question": "糊代はどこ？", "who": WHO}, cookie=key)[0] == 200

# ── 記録: 工夫も考えも、その紙の記録に結ばれる ──
assert f'<option value="{oid}" selected>' in page(f"/toy/{G}", cookie=key)[1], "記録の欄は本人の紙を選んでいる"
code, _, h = send(f"/toy/{G}/record", {"hypothesis": oid, "sheet_version": 1, "result": "動いた", "who": WHO}, cookie=key)
assert code == 303, code
rid = next(r["id"] for r in records.all_records(G) if r["hypothesis_id"] == oid)
told = talk_log.kufu(G, rid)
assert {x["when"] for x in told} == {"idea", "making"} and any(x["text"] == CRAFT and x["step"] == 2 for x in told) and any(x["text"] == THINK for x in told), told
assert [x["text"] for x in loop.maker_talk(rid)["items"]] == [CRAFT], "輪の材料に工夫が入る（考えはループ1 の材料なので入れない）"
body = page(f"/toy/{G}/techo")[1]
assert CRAFT in body and hanasu.KUFU_HEAD in body and THINK not in body, "手帖の記録の札の「工夫した所」に出る。考えは出さない"
groups = engine_bundle.build()["groups"]
assert len(groups) == 1 and groups[0]["reports"] == 1, "束で群が分かれない"
# 記録の後は閉じる。作りながら見る頁も、工夫も
assert f'data-hid="{oid}"' not in page(f"/toy/{G}/tsukuru?h={oid}", cookie=key)[1]
assert send(f"/toy/{G}/talk", {"scene": "craft", "hypothesis": oid, "sheet_version": 1, "step": 1, "text": "記録の後の工夫", "who": WHO}, cookie=key)[0] == 422

# ── 取り下げ: 工夫の字も考えの字も消える ──
assert records.withdraw(rid)[1] == []
assert everywhere(CRAFT) == [] and everywhere(THINK) == [], (everywhere(CRAFT), everywhere(THINK))
assert oid not in {x["id"] for x in hypotheses.own_hypotheses(G)}

# ── 手帖から: 本人の紙を選んで記録する ──
T2, C2 = "筒を細くしたら速く開くと思う", "内筒に蝋を塗ると滑る"
W2 = "roundwho03"
o2, k2 = made(W2, T2, {"push_part": "stick", "pusher_height": 84})
body = page(f"/toy/{G}/techo", cookie=k2)[1]
assert f'name="hypothesis" value="{o2}"' in body and body.index(f'value="{o2}"') < body.index(f'value="{SHEET}"'), "手帖の札に本人の紙が先に出る"
assert f'value="{o2}"' not in page(f"/toy/{G}/techo")[1], "ほかの人の手帖には出ない"
assert send(f"/toy/{G}/talk", {"scene": "craft", "hypothesis": o2, "sheet_version": 1, "step": 1, "text": C2, "who": W2}, cookie=k2)[0] == 200
code, body, _ = send(f"/toy/{G}/record-json", {"hypothesis": o2, "sheet_version": 1, "result": "動いた", "who": W2}, cookie=k2)
assert code == 201 and json.loads(body)["kufu"] == 1 and json.loads(body)["kangae"] == 1, body
assert f'data-hid="{o2}"' not in page(f"/toy/{G}/tsukuru?h={o2}", cookie=k2)[1], "手帖の記録でも閉じる"

# ── 型紙なしの紙でも同じ ──
T3, C3 = "水を入れた重さで開くのかも", "紙コップで試した"
W3 = "roundwho04"
o3, k3 = made(W3, T3, not_fit=["水の重さで動く機構は雛形に無い"])
code, body = page(f"/toy/{G}/tsukuru", cookie=k3)
assert code == 200 and f'data-hid="{o3}"' in body and f"{o3}_v1_free.png" in body, "作りながら見る頁に、型紙なしの紙の絵"
assert send(f"/toy/{G}/talk", {"scene": "craft", "hypothesis": o3, "sheet_version": 1, "text": C3, "who": W3}, cookie=k3)[0] == 200
assert send(f"/toy/{G}/ask-json", {"hypothesis": o3, "question": "糊代はどこ？", "who": W3}, cookie=k3)[0] == 200
assert send(f"/toy/{G}/record", {"hypothesis": o3, "sheet_version": 1, "result": "動いた", "who": W3}, cookie=k3)[0] == 303
r3 = next(r["id"] for r in records.all_records(G) if r["hypothesis_id"] == o3)
assert {x["text"] for x in talk_log.kufu(G, r3)} == {T3, C3}
server.shutdown()
print("ok")
