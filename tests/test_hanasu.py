"""話す口（一周の声の部分、Issue #279）。本人の決定 11-05「声そのものは残さない」「個人の情報は入口で落とす」。本物の API は呼ばない。

見る線:
- 3 つの場面（1 考え・2 工夫・3 できた物）で、字が残る。JS が無くても残せる。残る欄は決めた物だけで、声・IP・ブラウザの名・cookie が無い。時刻は分まで。
- 作りながら話した工夫は、記録を残した時に、その記録の「工夫した所（直した所）」に入る（同じ画面・同じ紙の物だけ。ほかの人の工夫は入らない）。
- 入口の床: 連絡先の形・名乗りの形・学年と組の形・学校の名前の形の文は残らない（落とした数だけ残る）。工作の話は落とさない。
- 頁は、マイクを開く code・録る code・声を送る code を持たない。受け口は字のフォームだけを受け、音のファイルは断る。
- 話す釦は既定で隠れていて、端末の中で字にできると分かった時だけ出る形になっている（切り替えは OMOCHAE_VOICE）。
- 1 の字は学ぶ人の頁に出ない。2 と 3 の字は、見せてよいと選び、記録に入った物だけが記録の札に出る（ほかは件数だけ）。合言葉なしで開いた場では、文は出ない。
- 作る側の頁に、話した事が場面ごとに並ぶ。記録を取り下げると、結んだ字も消える。
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
os.environ.pop("OMOCHAE_VOICE", None)

from omochae import making_log, records, talk_log  # noqa: E402
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


def get(path, at=None):
    try:
        r = opener.open((at or base) + path)
        return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def send(path, body, ctype="application/x-www-form-urlencoded", origin=None, at=None):
    # 送る側がブラウザの名と cookie を付けても、記録に入らない事を見るために付ける
    at = at or base
    req = urllib.request.Request(at + path, data=body, method="POST",
                                 headers={"Content-Type": ctype, "Origin": origin or at, "User-Agent": "TestBrowser/1.0", "Cookie": "name=someone"})
    try:
        r = opener.open(req)
        return r.status, r.read().decode(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(), dict(e.headers)
    except (urllib.error.URLError, ConnectionError):
        # 大きすぎる本体は、サーバが読まずに断って線を切る。送り終える前に切れると、返事の番号が読めない事がある（断られた事は同じ）。
        return None, "", {}


def post(path, data, **kw):
    return send(path, urllib.parse.urlencode(data).encode(), **kw)


def talk(**data):
    code, body, _ = post(f"/toy/{G}/talk", {"json": "1", **data})
    return code, json.loads(body)


making = pathlib.Path(DATA) / "making"
files = lambda: sorted(making.glob("talk-*.json")) if making.exists() else []

# ---- 入口の床（形だけを見る。工作の話は落とさない）
for text in ("谷を先に折ったら、筒に入りやすかった", "この部品の名前は分からないけど、三角の所を先に折った", "名前は何ですか", "これは蛇腹といいます",
             "私は小学校の時に同じ物を作った", "近くの中学校で見た", "2年前に組み立てた物と同じ", "扇の高さを 36 にした",
             # 声から字にした文は助詞が抜けやすい。学校の前の言葉が名前でない時は落とさない
             "当時小学校で作った", "昔小学校で作った", "私小学校の時に作った", "私立中学校の文化祭で見た", "市立小学校の体育館で見た",
             "作ったのは小学校の時です", "小学校の図工です", "谷折りと言います"):
    assert talk_log.blocked(text) == "", (text, talk_log.blocked(text))
for text, shape in (("電話は 090-1234-5678 です", "連絡先"), ("a@example.com に送って", "連絡先"), ("〒100-0001 に住んでいます", "連絡先"),
                    ("田中と申します。扇を先に折りました", "名乗り"), ("私の名前は田中です", "名乗り"), ("名前は田中です", "名乗り"), ("僕は田中といいます", "名乗り"),
                    ("3年2組の机で作った", "学年と組"), ("三年二組です", "学年と組"), ("３年２組で作った", "学年と組"), ("緑町小学校で作った", "学校の名前"),
                    # 1 字の名前の学校・片仮名の名前・名前でない言葉の後ろに名前が続く形・「○○学校の△△です」の名乗り（学校の名前がひらがなでも）
                    ("東小学校で作った", "学校の名前"), ("南中学校で作った", "学校の名前"), ("ヒバリ高校の文化祭", "学校の名前"), ("昔東小学校で作った", "学校の名前"),
                    ("緑町私立中学校で見た", "学校の名前"), ("東小学校の田中です", "名乗り"), ("さくら小学校の山田です", "名乗り")):
    assert talk_log.blocked(text) == shape, (text, talk_log.blocked(text))
# 床の限り（形では落とせない物。落とせない事を、ここで分かる形に残す。だから画面は、字を本人が見てから残す）
for text in ("田中です", "田中といいます", "さくら小学校で作った", "中3です"):
    assert talk_log.blocked(text) == "", (text, talk_log.blocked(text))

# ---- 頁の準備（予想を書いて、紙を刷る。予想の口の返事は見ない: 予想の段が無い作りでも、この先が同じに通るように）
post(f"/toy/{G}/predict", {"text": "筒を持つと扇が開くと思う"})
assert post(f"/toy/{G}/print", {"hypothesis": "H-A"})[0] == 303
assert not files()
# その場限りの印（画面が持つ乱数）。W は作って記録まで残す画面、W2 は同じ紙を別の机で作る画面
W, W2 = "abcdefghij", "klmnopqrst"

# ---- 1 考え: 仮説を選んでも、選ばなくても残る。JS が無い時は玩具の頁へ戻る
THINK = "筒を押すと、扇が上から開くと思う"
code, j = talk(scene="think", hypothesis="H-A", text=THINK, via="voice", who=W)
assert code == 200 and j["kept"] is True and "残しました" in j["note"], j
code, _, head = post(f"/toy/{G}/talk", {"scene": "think", "text": "糸で引く所が気になる"})
assert code == 303 and head["Location"].startswith(f"/toy/{G}?msg=") and head["Location"].endswith("&at=hanasu#hanasu"), head
# 着いた節の頭に、返事の文が出る（JS が無い時。送った後の返事を、着いた場所で読む形）
landed = get(head["Location"].split("#")[0])[1]
assert '<section class="sec" id="hanasu"><div role="status"><p id="msg">残しました。型紙と案内を直す材料にします。</p></div>' in landed, landed[landed.index('id="hanasu"'):][:300]
# 通らなかった時も、同じ節の頭に理由が出る
code, page, _ = post(f"/toy/{G}/talk", {"scene": "think", "text": "電話は 090-1234-5678 です"})
assert code == 422 and '<section class="sec" id="hanasu"><div role="alert"><p id="msg">連絡先の形があるので、残しませんでした。その所を消すと残せます。</p></div>' in page
code, j = talk(scene="think", hypothesis="H-ZZ", text="無い仮説")
assert code == 422 and j["kept"] is False, j

# ---- 2 工夫: 刷った紙と手順の番号に結ぶ。手順の数の外の番号には結ばない（字は残す）。刷っていない紙は断る
CRAFT, CRAFT_QUIET = "糊代を先に折り癖を付けたら、貼りやすかった", "扇の端を少し切った"
CRAFT_OTHER, CRAFT_NOWHO, CRAFT_NOJS = "別の机で、筒を太く巻いた", "定規で折り目を押さえた", "折り目に爪で筋を付けた"
code, j = talk(scene="craft", hypothesis="H-A", sheet_version="1", step="2", text=CRAFT, who=W, share="1", via="voice")
assert code == 200 and j["kept"] is True and j["note"] == hanasu.KEPT_CRAFT and "「工夫した所（直した所）」に入ります" in j["note"], j
code, j = talk(scene="craft", hypothesis="H-A", sheet_version="1", step="99", text=CRAFT_QUIET, who=W)
assert code == 200 and j["kept"] is True, j
assert talk(scene="craft", hypothesis="H-A", sheet_version="1", step="1", text=CRAFT_OTHER, who=W2)[0] == 200
# 形の外の印は残さない。印が無いと記録に入れられないので、入ると約束する文も出さない
code, j = talk(scene="craft", hypothesis="H-A", sheet_version="1", step="3", text=CRAFT_NOWHO, who="Tanaka Taro!")
assert code == 200 and j["kept"] is True and j["note"] == hanasu.KEPT, j
code, j = talk(scene="craft", hypothesis="H-B", sheet_version="1", step="1", text="刷っていない紙")
assert code == 422 and j["kept"] is False, j
# JS が無い時は、戻る道の付いた頁で答える（戻り先は場面から作る）
code, page, _ = post(f"/toy/{G}/talk", {"scene": "craft", "hypothesis": "H-A", "sheet_version": "1", "step": "3", "text": CRAFT_NOJS})
assert code == 200 and "残しました" in page and f'href="/toy/{G}/tsukuru?h=H-A&amp;v=1&amp;n=3"' in page, page[-600:]

# ---- 記録を残す: 同じ画面で、同じ紙について話した工夫が、その記録の「工夫した所（直した所）」に入る
assert talk_log.talks(G, shared_only=True) == [], "記録に入る前の工夫は、見せてよいと選んでいても、学ぶ人の頁が読む口に出ない"
code, body, _ = post(f"/toy/{G}/record-json", {"hypothesis": "H-A", "result": "動いた", "note": "", "who": W})
assert code == 201 and json.loads(body) == {"id": "R-0001", "kufu": 2}, body
RID = "R-0001"
ku = talk_log.kufu(G, RID)
assert ku == [{"when": "making", "step": 2, "text": CRAFT, "share": True}, {"when": "making", "step": None, "text": CRAFT_QUIET, "share": False}], ku
# 同じ画面で次の記録を残しても、前の記録に入った工夫は動かない。印の無い画面の記録には、何も入らない
code, body, _ = post(f"/toy/{G}/record-json", {"hypothesis": "H-A", "result": "動いた", "who": W})
assert code == 201 and json.loads(body) == {"id": "R-0002"}, body
code, body, _ = post(f"/toy/{G}/record-json", {"hypothesis": "H-A", "result": "動かない"})
assert code == 201 and json.loads(body) == {"id": "R-0003"}, body
assert talk_log.kufu(G, "R-0002") == [] and talk_log.kufu(G, "R-0003") == [] and talk_log.kufu(G, RID) == ku
# 玩具の頁の記録の欄（JS が無くても送れるフォーム）から残した時も、同じに入る。別の机の工夫は、その机の記録に入る
assert post(f"/toy/{G}/record", {"hypothesis": "H-A", "result": "動いた", "who": W2})[0] == 303
assert talk_log.kufu(G, "R-0004") == [{"when": "making", "step": 1, "text": CRAFT_OTHER, "share": False}], talk_log.kufu(G, "R-0004")
# 記録の欄に書いた直した点（部品・変えた事・結果）を持つ記録。話した字とは別に残り、記録の札では同じ節に並ぶ
rid5, failures = records.add({"source_id": G, "hypothesis_id": "H-A", "sheet_version": 1, "result": "動いた",
                              "fixes": [{"part": "外筒", "change": "太く巻いた", "outcome": "内筒が入りやすくなった"}]})
assert rid5 == "R-0005" and not failures and talk_log.kufu(G, rid5) == []

# ---- 3 できた物: 試した記録に結ぶ。見せてよいかは本人が選ぶ（既定は見せない）
KEEP_OPEN, KEEP_CLOSED = "扇の根元を糸で留めたら、開いたままになった", "内筒が固かったので、角を丸く切った"
code, j = talk(scene="keep", record=RID, text=KEEP_OPEN, share="1", via="voice")
assert code == 200 and j["kept"] is True and "ほかの人にも見せます" in j["note"], j
code, j = talk(scene="keep", record=RID, text=KEEP_CLOSED)
assert code == 200 and "ほかの人には見せません" in j["note"], j
code, j = talk(scene="keep", record="R-9999", text="無い記録")
assert code == 422 and "記録が見つかりません" in j["why"], j

# ---- 床に落ちた文は残らない。理由が返り、落とした事だけが残る。空の文と、決まりの外の場面は何も残さない
n = len(files())
code, j = talk(scene="think", text="電話は 090-1234-5678 です。扇が開くと思う")
assert code == 422 and j["kept"] is False and "連絡先の形がある" in j["why"] and "消すと残せます" in j["why"], j
code, j = talk(scene="keep", record=RID, text="緑町小学校の田中と申します", share="1")
assert code == 422 and "名乗りの形がある" in j["why"], j
assert len(files()) == n + 2
code, j = talk(scene="think", text="   ")
assert code == 422 and "話すか書いてください" in j["why"], j
assert talk(scene="sing", text="歌った")[0] == 422
assert len(files()) == n + 2

# ---- 受け口は字のフォームだけ。音のファイル・大きすぎる本体・別の出所は断り、何も残さない
n = len(files())
assert send(f"/toy/{G}/talk", b"RIFF....WEBM" * 100, ctype="audio/webm")[0] == 403
assert send(f"/toy/{G}/talk", b"x" * 100, ctype="multipart/form-data; boundary=x")[0] == 403
assert post(f"/toy/{G}/talk", {"scene": "think", "text": "長" * 70000})[0] in (403, None)
assert post(f"/toy/{G}/talk", {"scene": "think", "text": "別の出所"}, origin="http://evil.example")[0] == 403
assert len(files()) == n

# ---- 残った出来事: 欄は決めた物だけ。時刻とファイルの名前は分まで。送った側の名・cookie・番地は無い
seen = []
for p in files():
    raw = p.read_text(encoding="utf-8")
    rec = json.loads(raw)
    assert set(rec) - {"dropped"} == set(talk_log.FIELDS), (p.name, sorted(rec))
    assert re.fullmatch(r"talk-\d{8}-\d{4}-[0-9a-f]{8}\.json", p.name), p.name
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d\+09:00", rec["at"]), rec["at"]
    for word in ("TestBrowser", "someone", "127.0.0.1", "Tanaka", "090-1234", "緑町", "田中"):
        assert word not in raw, (p.name, word)
    assert rec["via"] in talk_log.VIAS and rec["scene"] in talk_log.SCENES and isinstance(rec["share"], bool)
    if rec.get("dropped"):
        assert rec["text"] == "" and rec["share"] is False and rec["dropped"] in ("pii", "name"), rec
    seen.append(rec)
by_text = {r["text"]: r for r in seen if r["text"]}
assert by_text[THINK] | {"at": ""} == {"source_id": G, "hypothesis_id": "H-A", "sheet_version": 1, "template": "slider_fan", "sheet_set": by_text[THINK]["sheet_set"],
                                         "scene": "think", "step": None, "record_id": None, "text": THINK, "via": "voice", "share": False, "who": "abcdefghij", "at": ""}
assert by_text[THINK]["sheet_set"], "刷った組が空（エンジンの束と結べない）"
assert by_text["糸で引く所が気になる"]["hypothesis_id"] is None and by_text["糸で引く所が気になる"]["via"] == "text"
assert by_text[CRAFT] | {"at": "", "sheet_set": ""} == {"source_id": G, "hypothesis_id": "H-A", "sheet_version": 1, "template": "slider_fan", "sheet_set": "", "scene": "craft",
                                                       "step": 2, "record_id": RID, "text": CRAFT, "via": "voice", "share": True, "who": W, "at": ""}
assert by_text[CRAFT_QUIET]["step"] is None and by_text[CRAFT_QUIET]["record_id"] == RID and by_text[CRAFT_QUIET]["share"] is False
assert by_text[CRAFT_OTHER]["record_id"] == "R-0004" and by_text[CRAFT_OTHER]["who"] == W2
# 形の外の印は残さない。印の無い工夫は、どの記録にも入らない
assert by_text[CRAFT_NOWHO]["who"] == "" and by_text[CRAFT_NOWHO]["step"] == 3 and by_text[CRAFT_NOWHO]["record_id"] is None and by_text[CRAFT_NOJS]["record_id"] is None
assert by_text[THINK]["record_id"] is None, "考えは仮説に結ぶ物で、記録には入れない"
assert by_text[KEEP_OPEN]["record_id"] == RID and by_text[KEEP_OPEN]["share"] is True and by_text[KEEP_OPEN]["hypothesis_id"] == "H-A"
assert by_text[KEEP_CLOSED]["share"] is False
assert talk_log.dropped(G) == {"pii": 2, "name": 1}
# 聞く口の質問の置き場には混ざらない（集計の数を変えない）
assert making_log.asks(G) == [] and making_log.summary(G)["asks"] == []

# ---- 読む口: 学ぶ人の頁とギャラリーは、記録に入った 2 と 3 の字のうち、見せてよいと選んだ物だけを読める
assert {t["text"] for t in talk_log.talks(G, record_id=RID, shared_only=True)} == {CRAFT, KEEP_OPEN}
assert {t["text"] for t in talk_log.talks(G, shared_only=True)} == {CRAFT, KEEP_OPEN}
assert {t["text"] for t in talk_log.talks(G, scene="keep")} == {KEEP_OPEN, KEEP_CLOSED}
# 記録の「工夫した所（直した所）」: 作りながら話した物（手順の順）の後に、上げた後に残した物。同じ分の中の順は決まらないので、後ろは集まりで見る
ku = talk_log.kufu(G, RID)
assert [(k["when"], k["step"], k["text"]) for k in ku[:2]] == [("making", 2, CRAFT), ("making", None, CRAFT_QUIET)], ku
assert {(k["when"], k["text"], k["share"]) for k in ku[2:]} == {("made", KEEP_OPEN, True), ("made", KEEP_CLOSED, False)} and len(ku) == 4, ku
assert {k["text"] for k in talk_log.kufu(G, RID, shared_only=True)} == {CRAFT, KEEP_OPEN}
assert talk_log.WHEN == {"think": "idea", "craft": "making", "keep": "made"}  # エンジンへ渡す束と合わせた名（#275）
sm = talk_log.summary(G)
assert {t["text"] for t in sm["think"]} == {THINK, "糸で引く所が気になる"}
assert sm["craft"]["H-A"][1][1] == [CRAFT_OTHER] and sm["craft"]["H-A"][1][2] == [CRAFT] and set(sm["craft"]["H-A"][1][3]) == {CRAFT_NOWHO, CRAFT_NOJS}, sm["craft"]
assert list(sm["craft"]["H-A"][1]) == [1, 2, 3, None] and sm["craft"]["H-A"][1][None] == [CRAFT_QUIET], sm["craft"]
assert [(r["record_id"], r["hypothesis_id"], r["sheet_version"], len(r["kufu"])) for r in sm["records"]] == [(RID, "H-A", 1, 4), ("R-0004", "H-A", 1, 1)], sm["records"]
assert sm["via"] == {"voice": 3, "text": 6} and sm["dropped"] == {"pii": 2, "name": 1}, sm

# ---- 頁: 3 つの場面に口がある。話す釦は既定で隠れている
MIC = '<button type="button" class="hanasu-mic" aria-pressed="false" aria-label="話す（もう一度押すと止まる）" hidden>話す</button>'
code, toy = get(f"/toy/{G}")
assert code == 200 and 'id="hanasu"' in toy and f'action="/toy/{G}/talk#hanasu"' in toy and 'name="scene" value="think"' in toy and MIC in toy
assert hanasu.NOTICE in toy and toy.count("<script>(()=>{\nconst REC=") == 1
code, tsu = get(f"/toy/{G}/tsukuru?h=H-A&n=2")
assert code == 200 and 'name="scene" value="craft"' in tsu and 'name="step" value="2"' in tsu and 'name="sheet_version" value="1"' in tsu and MIC in tsu
# 見せてよいかを選ぶ欄は、記録に入る場面（工夫・できた物）にだけ出す。既定は選んでいない
assert 'name="share" value="1"> 記録に入った時に、ほかの人に見せてよい' in tsu and 'name="share"' not in toy and "checked" not in tsu[tsu.index('name="share"'):][:40]
code, techo = get(f"/toy/{G}/techo")
assert code == 200 and f'name="record" value="{RID}"' in techo and 'name="share" value="1"' in techo and MIC in techo
assert techo.count("<script>(()=>{\nconst REC=") == 1, "手帖には部品が何個あっても、動きは 1 回だけ置く"
assert techo.index(f'name="record" value="{RID}"') < techo.index("</div></section>") and techo.rindex("const REC=") > techo.rindex('id="mine"')

# ---- 見せる範囲: 1 の字と、記録に入っていない工夫と、見せてよいと選んでいない字は、学ぶ人の頁に出ない
code, gallery = get("/gallery")
for page in (toy, tsu, techo, gallery):
    for text in (THINK, "糸で引く所が気になる", CRAFT_QUIET, CRAFT_OTHER, CRAFT_NOWHO, CRAFT_NOJS, KEEP_CLOSED):
        assert text not in page, text
# 手帖の記録の札に「工夫した所（直した所）」が出る: 見せてよいと選んだ物は文で（作りながらの物は手順の番号つき）、ほかは件数だけ
card = techo[techo.index(f"{RID}　"):techo.index(f'name="record" value="{RID}"')]
assert '<p class="hanasu-kufu-head">工夫した所（直した所）</p>' in card and f"<li>手順 2: {CRAFT}</li>" in card and f"<li>{KEEP_OPEN}</li>" in card, card
assert "ほかに 2 件（作る側だけが読みます）" in card and card.index(CRAFT) < card.index(KEEP_OPEN)
# 見せてよい物が無い記録は件数だけ。何も入っていない記録には、節を出さない。記録の欄の直した点は、同じ節に文で出る
assert techo.count('class="hanasu-kufu"') == 3 and '<p class="meta">1 件（作る側だけが読みます）</p>' in techo
assert "<ul><li>外筒 / 太く巻いた / 内筒が入りやすくなった</li></ul></div>" in techo
for page in (toy, tsu, gallery):
    assert CRAFT not in page and KEEP_OPEN not in page
# 記録を残した時に、入った数を手帖が知らせる
assert "j.kufu ?" in techo and "この記録の「工夫した所（直した所）」に入りました" in techo

# ---- 作る側の頁: 場面ごとに並ぶ。落とした文は無く、数だけ。順位と点の形が無い
code, loop_page = get(f"/loop/{G}")
assert code == 200 and "7 話した事" in loop_page
for text in (THINK, CRAFT, KEEP_OPEN, KEEP_CLOSED):
    assert text in loop_page, text
for text in (CRAFT_QUIET, CRAFT_OTHER, CRAFT_NOWHO, CRAFT_NOJS):
    assert text in loop_page, text
assert "仮説 A の紙・版 1・手順 2" in loop_page and "連絡先の形 2 件・名乗りや学校の形 1 件" in loop_page
# 記録ごとの「工夫した所（直した所）」: 作りながら話した物（手順の番号）と、上げた後の物。見せてよいの印は、選んだ物にだけ
assert f"<h4>{RID}（仮説 A の紙・版 1）</h4>" in loop_page and "<h4>R-0004（仮説 A の紙・版 1）</h4>" in loop_page and "<h4>R-0002" not in loop_page
assert f"<li>手順 2: {CRAFT}［見せてよい］</li>" in loop_page and f"<li>作りながら: {CRAFT_QUIET}</li>" in loop_page and f"<li>手順 1: {CRAFT_OTHER}</li>" in loop_page
assert f"<li>上げた後: {KEEP_OPEN}［見せてよい］</li>" in loop_page and f"<li>上げた後: {KEEP_CLOSED}</li>" in loop_page
assert "声から字にした物 3 件・字で書いた物 6 件" in loop_page
part = loop_page[loop_page.index("7 話した事"):]
for word in ("090-1234", "緑町", "田中", "位", "点数", "％", "ランキング"):
    assert word not in part, word

# ---- 頁の code: マイクを開く・録る・声を送る物が無い。声を字にする指定は「端末の中だけ」
for word in ("getUserMedia", "MediaRecorder", "AudioContext", "createMediaStreamSource", "captureStream", "audio:true", "audio: true", "srcObject",
             "toBlob", "toDataURL", "FileReader", "Blob(", "WebSocket", "sendBeacon", "XMLHttpRequest", "EventSource", "RTCPeerConnection"):
    assert word not in hanasu.SCRIPT and word not in hanasu.STYLE, word
assert "processLocally:true" in hanasu.SCRIPT and "r.processLocally=true" in hanasu.SCRIPT and "REC.available({langs:[LANG],processLocally:true})" in hanasu.SCRIPT
# 送る所は 1 つで、字のフォームの形だけ。聞き取った所（onresult）からは送らない
assert hanasu.SCRIPT.count("fetch(") == 1 and "fetch(form.action,{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'}" in hanasu.SCRIPT
onresult = hanasu.SCRIPT[hanasu.SCRIPT.index("r.onresult"):hanasu.SCRIPT.index(" r.onerror")]
assert "fetch" not in onresult and "submit" not in onresult and "box.value" in onresult
# 聞き取った所は、欄に字を足して知らせるだけ。字の並びごと固定する（ここに、送る・押す・残すを足すと落ちる。「残すを押すまで送らない」が設計の要）
assert onresult == "r.onresult=(ev)=>{\n  // 読み上げの間に入った字は、端末が自分の答えを聞いた物なので入れない。\n  if(window.speechSynthesis&&speechSynthesis.speaking)return;\n  for(let i=ev.resultIndex;i<ev.results.length;i++){if(!ev.results[i].isFinal)continue;const t=ev.results[i][0].transcript.trim();\n   if(t){box.value=(box.value?box.value+' ':'')+t;root.dataset.via='voice';note(root,M.heard)}}};\n", onresult
# 送る所は、残すを押した時の所だけ。残す釦を code から押す所・フォームを code から送る所が無い（押すのは、聞く口の声を止める 1 か所だけ）
SUBMIT = hanasu.SCRIPT.index("document.addEventListener('submit'")
assert hanasu.SCRIPT.index("fetch(") > SUBMIT and hanasu.SCRIPT.count(".hanasu-go") == 1 and hanasu.SCRIPT.index(".hanasu-go") > SUBMIT
assert hanasu.SCRIPT.count(".click()") == 1 and "if(ask)ask.click()" in hanasu.SCRIPT
for word in ("requestSubmit", "dispatchEvent", ".submit()"):
    assert word not in hanasu.SCRIPT, word
# 既定の音声認識（声を外の認識のサービスへ送る事がある）は、切り替えが browser の時にしか使わない
assert "if(how==='browser'){listen(root,false);return}" in hanasu.SCRIPT and hanasu.SCRIPT.count("listen(root,false)") == 1
assert "let how=want==='off'?'none':feat?'local':(want==='browser'&&REC)?'browser':'none'" in hanasu.SCRIPT
assert "if(want==='browser'&&REC){how='browser';mark();note(root,M.tobrowser);return}" in hanasu.SCRIPT and hanasu.SCRIPT.count("how='browser'") == 1
# 使えるかをブラウザに聞くのは、人が釦を押した時だけ（頁を開いた時に聞くと、頁ごと落ちる画面があった）
assert "local()" not in hanasu.SCRIPT[:hanasu.SCRIPT.index("document.addEventListener('click'")] and hanasu.SCRIPT.count("await local()") == 1
# 端末の中で字にできるかは、口の形で見分ける（前置きの付いた名前しか無い版でも同じに動く）。聞く時の指定は、端末の中の時だけ付ける
assert "const REC=window.SpeechRecognition||window.webkitSpeechRecognition," in hanasu.SCRIPT
assert "const feat=!!(REC&&typeof REC.available==='function'&&'processLocally' in REC.prototype);" in hanasu.SCRIPT and "if(onDevice)r.processLocally=true" in hanasu.SCRIPT
# 釦は CSS でも既定で隠れ、端末の中で字にできると分かった印が付いた時だけ出る
assert ".hanasu .hanasu-mic{display:none" in hanasu.STYLE and ".hanasu-local .hanasu .hanasu-mic,.hanasu-browser .hanasu .hanasu-mic{display:block}" in hanasu.STYLE

# ---- 切り替え（OMOCHAE_VOICE）: 既定は local。決まりの外の値は local に戻す
assert hanasu.mode() == "local" and 'data-voice="local"' in toy and "const want='local';" in toy
for value, want in (("browser", "browser"), ("off", "off"), ("everything", "local"), ("", "local")):
    os.environ["OMOCHAE_VOICE"] = value
    assert hanasu.mode() == want and f"const want='{want}';" in hanasu.assets(), value
    assert f'data-voice="{want}"' in get(f"/toy/{G}")[1], value
os.environ.pop("OMOCHAE_VOICE")
assert hanasu.HOW_BROWSER in toy and "送られる事があります" in hanasu.HOW_BROWSER and "この端末の中で字になります" in hanasu.HOW_LOCAL

# ---- 合言葉なしで開いた場: 字は残せるが、人の言葉（見せてよいの字も）は頁に出さない
open_server = serve(0, public_open=True)
threading.Thread(target=open_server.serve_forever, daemon=True).start()
open_base = f"http://127.0.0.1:{open_server.server_address[1]}"
code, open_techo = get(f"/toy/{G}/techo", at=open_base)
assert code == 200 and KEEP_OPEN not in open_techo and CRAFT not in open_techo and f'name="record" value="{RID}"' in open_techo
assert '<p class="meta">4 件（公開のデモでは、文を出しません）</p>' in open_techo and "太く巻いた" not in open_techo and "作る側だけが読みます）</p>" not in open_techo
code, body, _ = post(f"/toy/{G}/talk", {"json": "1", "scene": "think", "text": "開いた場でも残せる"}, at=open_base)
assert code == 200 and json.loads(body)["kept"] is True
assert get(f"/loop/{G}", at=open_base)[0] == 404

# ---- 記録を取り下げると、結んだ字も消える。ほかの場面の字は残る
before = len(talk_log.talks(G))
gone, failures = records.withdraw(RID)
assert not failures and sum(1 for g in gone if g.startswith("making/talk-")) == 5, gone  # 作りながらの 2 件・上げた後の 2 件・床で落とした物
assert talk_log.talks(G, record_id=RID) == [] and talk_log.talks(G, scene="keep") == [] and talk_log.kufu(G, RID) == []
left = {t["text"] for t in talk_log.talks(G)}
assert len(talk_log.talks(G)) == before - 4 and {THINK, CRAFT_OTHER, CRAFT_NOWHO} <= left and not {CRAFT, CRAFT_QUIET} & left
after = get(f"/loop/{G}")[1]
assert KEEP_OPEN not in after and CRAFT not in after and CRAFT_OTHER in after

# ---- 記録に結ぶ条件: 同じ玩具・同じ紙（仮説と版）・同じ印の物だけ。条件を 1 つ外した物は入らない
W3, TORA = "uvwxyzabcd", "NDL-1187053-R0000014-R"
for hid, ver, who, text in (("H-B", 1, W3, "別の仮説の紙の工夫"), ("H-A", 2, W3, "別の版の紙の工夫"), ("H-A", 1, "qrstuvwxyz", "別の画面の工夫"), ("H-A", 1, W3, "同じ紙の工夫")):
    path, failures = talk_log.add(G, "craft", text, hypothesis_id=hid, sheet_version=ver, step=1, who=who)
    assert path and not failures, failures
assert talk_log.bind(TORA, "H-A", 1, W3, "R-0002") == 0, "別の玩具の記録には入らない"
assert talk_log.bind(G, "H-A", 1, "", "R-0002") == 0 and talk_log.bind(G, "H-A", 1, "Tanaka Taro!", "R-0002") == 0, "印が無いと入らない"
assert talk_log.bind(G, "H-A", 1, W3, "R-0002") == 1 and [k["text"] for k in talk_log.kufu(G, "R-0002")] == ["同じ紙の工夫"]
assert talk_log.bind(G, "H-A", 1, W3, "R-0003") == 0, "1 回入った工夫は、次の記録に動かない"
assert talk_log.bind(G, "H-B", 1, W3, "R-0003") == 1 and [k["text"] for k in talk_log.kufu(G, "R-0003")] == ["別の仮説の紙の工夫"]
assert talk_log.bind(G, "H-A", 2, W3, "R-0003") == 1 and {k["text"] for k in talk_log.kufu(G, "R-0003")} == {"別の仮説の紙の工夫", "別の版の紙の工夫"}
assert "別の画面の工夫" in {t["text"] for t in talk_log.talks(G, scene="craft") if not t["record_id"]}

server.shutdown()
open_server.shutdown()
print("OK 話す口: 3 つの場面で字だけが残り、作りながら話した工夫が記録に入り、入口の床・見せる範囲・取り下げ・声を持たない code を確かめた")
