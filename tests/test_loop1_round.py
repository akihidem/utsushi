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
import re
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
from omochae.compose import TEMPLATES  # noqa: E402
from api import ask  # noqa: E402
from web import hanasu, think_sheet, tsukuru  # noqa: E402
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
# 紙を採る前に、たたき台を見ながら話した工夫と考え（同じ印）。案の紙の記録に一緒に結ばれる。ほかの印の字は結ばれない
EARLY_CRAFT, EARLY_THINK, THEIRS = "たたき台の筒を先に切った", "筒はもっと細くていいかも", "ほかの人の考えです"
assert send(f"/toy/{G}/talk", {"scene": "craft", "hypothesis": SHEET, "sheet_version": 1, "step": 1, "text": EARLY_CRAFT, "who": WHO})[0] == 200
assert send(f"/toy/{G}/talk", {"scene": "think", "hypothesis": SHEET, "text": EARLY_THINK, "who": WHO})[0] == 303
assert send(f"/toy/{G}/talk", {"scene": "think", "hypothesis": SHEET, "text": THEIRS, "who": OTHER})[0] == 303
oid, key = made(WHO, THINK, {"push_part": "stick", "pusher_height": 84})
# 刷った組は、紙を確定する時に残す（紙に刷った組。記録の時の組ではない）
confirmed = [c for c in loop.sheet_confirmations(G) if c["hypothesis_id"] == oid]
assert confirmed and confirmed[0]["version"] == 1 and confirmed[0]["confirmations"][0]["sheet_set"] == TEMPLATES["slider_fan"].SHEET_SET, confirmed

# 節から作りながら見る頁へ行ける。字は玩具の頁の入口と同じ（新しい文を足さない）
assert think_sheet.MAKE == "作りながら見る（机の端に置く・試作）" and think_sheet.MAKE in page(f"/toy/{G}")[1]
done = page(f"/toy/{G}?at=think-{key.split('=', 1)[1]}", cookie=key)[1]
assert f'/toy/{G}/tsukuru?h={oid}"' in done and think_sheet.MAKE in done, "節に、その紙の作りながら見る頁への道"

# ── 作りながら見る: 本人には、その人の紙が開く ──
code, body = page(f"/toy/{G}/tsukuru", cookie=key)
assert code == 200 and f'data-hid="{oid}"' in body, "紙の印が無ければ、本人の紙を開く"
assert f"{oid}_v1_tejun.png" in body and THINK not in body, "手順の紙の絵はその紙の物。話した字は頁に出さない"
title = re.search(r'<p class="top">.*?<span>(.*?)</span>', body, re.S).group(1)
assert hypotheses.own_hypotheses(G)[-1]["name"] in title and oid not in title, "頁の頭は案の名前で呼ぶ。番号は出さない"
assert f"組み方の絵（{hypotheses.own_hypotheses(G)[-1]['name']} の紙" in body and f"組み方の絵（{oid.split('-')[1]} の紙" not in body, "絵の説明も名前で呼ぶ"
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
assert send(f"/toy/{G}/print-own", {"id": oid})[0] == 404, "刷り直す口は閉じた（J-032 の点 2）"
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
assert {x["text"] for x in told} == {THINK, EARLY_THINK, CRAFT, EARLY_CRAFT}, "紙を採る前にたたき台に付いた同じ印の字も結ばれる。ほかの印の字は結ばれない"
assert {x["text"] for x in loop.maker_talk(rid)["items"]} == {CRAFT, EARLY_CRAFT}, "輪の材料に工夫が入る（考えはループ1 の材料なので入れない）"
body = page(f"/toy/{G}/techo/kiroku")[1]  # 記録の札は手帖の記録の頁（#87）
assert CRAFT in body and hanasu.KUFU_HEAD in body and THINK not in body, "手帖の記録の札の「工夫した所」に出る。考えは出さない"
groups = engine_bundle.build()["groups"]
# 束の群は紙ごと（Issue 334）。自分の紙の記録は、その紙の群で、たたき台の刷った組に入る（組が外れない）
mine = [g for g in groups if rid in g["record_ids"]]
assert len(mine) == 1 and mine[0]["reports"] == 1 and mine[0]["sheet_set"] == TEMPLATES["slider_fan"].SHEET_SET, "束で群が分かれず、紙の組に入る"
assert {CRAFT, EARLY_CRAFT} <= {t["text"] for g in groups for t in g["texts"]}, "束に工夫の字が入る"
# 記録の後は閉じる。作りながら見る頁も、工夫も
assert f'data-hid="{oid}"' not in page(f"/toy/{G}/tsukuru?h={oid}", cookie=key)[1]
assert send(f"/toy/{G}/talk", {"scene": "craft", "hypothesis": oid, "sheet_version": 1, "step": 1, "text": "記録の後の工夫", "who": WHO}, cookie=key)[0] == 422

# ── 取り下げ: 工夫の字も考えの字も消える ──
assert records.withdraw(rid)[1] == []
for gone in (CRAFT, THINK, EARLY_CRAFT, EARLY_THINK):
    assert everywhere(gone) == [], (gone, everywhere(gone))
assert everywhere(THEIRS), "ほかの人の字は消さない"
assert oid not in {x["id"] for x in hypotheses.own_hypotheses(G)}
assert not [c for c in loop.sheet_confirmations(G) if c["hypothesis_id"] == oid], "消えた紙の確定の記録を残さない"

# ── 手帖から: 本人の紙を選んで記録する ──
T2, C2 = "筒を細くしたら速く開くと思う", "内筒に蝋を塗ると滑る"
W2 = "roundwho03"
o2, k2 = made(W2, T2, {"push_part": "stick", "pusher_height": 84})
body = page(f"/toy/{G}/techo", cookie=k2)[1]
assert f'data-hid="{o2}"' in body, "手帖は本人の紙を作る（紙を選ばせない。#87）"
assert o2 not in page(f"/toy/{G}/techo")[1], "ほかの人の手帖には出ない"
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
assert tsukuru.step_texts(G, o3) == [] and f"{o3}_v1_free.png" in body and body.count("<li") == 1, "型紙なしの紙に雛形の手順を出さない"
step_one = TEMPLATES["slider_fan"].steps(TEMPLATES["slider_fan"].DEFAULTS)[0]
context, _ = ask.sheet_context(G, o3)
assert step_one not in context and "組み方" in context, "聞く口にも、無い手順を渡さない"
assert step_one in ask.sheet_context(G, SHEET)[0], "ほかの紙には手順を渡す（試験の見本が効いている事を見る）"
assert send(f"/toy/{G}/record", {"hypothesis": o3, "sheet_version": 1, "result": "動いた", "who": W3}, cookie=k3)[0] == 303
r3 = next(r["id"] for r in records.all_records(G) if r["hypothesis_id"] == o3)
assert {x["text"] for x in talk_log.kufu(G, r3)} == {T3, C3}
server.shutdown()
print("ok")
