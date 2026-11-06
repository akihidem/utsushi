"""話す口（一周の声の部分、Issue #279）。本人の決定 11-05「声そのものは残さない」「個人の情報は入口で落とす」。本物の API は呼ばない。

見る線:
- 3 つの場面（1 考え・2 工夫・3 できた物）で、字が残る。JS が無くても残せる。残る欄は決めた物だけで、声・IP・ブラウザの名・cookie が無い。時刻は分まで。
- 作りながら話した工夫と、仮説を見て話した考えは、記録を残した時に、その記録に入る（同じ画面の物だけ。ほかの人の話は入らない）。
- 入口の床: 連絡先の形・名乗りの形・学年と組の形・学校の名前の形の文は残らない（落とした数だけ残る）。工作の話は落とさない。
- 頁は、マイクを開く code・録る code・声を送る code を持たない。受け口は字のフォームだけを受け、音のファイルは断る。聞いた字は、残すを押すまで送らない。
- 話す釦は既定で隠れていて、音声認識の口がある画面でだけ出る。端末の中だけで字にできる画面ではその形で聞き、できない画面ではブラウザの既定の口で聞いて
  断りを出す（本人の決定 11-05: iPhone・iPad でも話す釦を出す。切り替えは OMOCHAE_VOICE）。
- 記録に入った工夫の字は、記録の感想と同じに、手帖の記録の札に文で出る（本人の決定 11-05。選び肢は置かない）。記録に入る前の字は出ない。
  合言葉なしで開いた場では、文は出ない（J-028）。作る側は、気づいた時に記録の字を隠せる。
- 利用者向けの文は、本人が採ったやさしい言葉の文のまま（Issue #318）。一字でも変わったら落ちるように、ここに決定の文を書く。
- 作る側の頁に、話した事が場面ごとと記録ごとに並ぶ。記録を取り下げると、結んだ字も消える。
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
REC_KEY = "a" * 24  # この画面が記録を残した時の鍵。上げた後に足す口は、その画面にだけ開く（records.mine）


def get(path, at=None):
    try:
        r = opener.open(urllib.request.Request((at or base) + path, headers={"Cookie": f"utsushi_rec={REC_KEY}"}))
        return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def send(path, body, ctype="application/x-www-form-urlencoded", origin=None, at=None):
    # 送る側がブラウザの名と cookie を付けても、記録に入らない事を見るために付ける
    at = at or base
    req = urllib.request.Request(at + path, data=body, method="POST",
                                 headers={"Content-Type": ctype, "Origin": origin or at, "User-Agent": "TestBrowser/1.0", "Cookie": f"name=someone; utsushi_rec={REC_KEY}"})
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
assert '<section class="sec" id="hanasu"><div role="status"><p id="msg">残しました。型紙や説明をよくするのに使います。</p></div>' in landed, landed[landed.index('id="hanasu"'):][:300]
# 通らなかった時も、同じ節の頭に理由が出る
code, page, _ = post(f"/toy/{G}/talk", {"scene": "think", "text": "電話は 090-1234-5678 です"})
assert code == 422 and f'<section class="sec" id="hanasu"><div role="alert"><p id="msg">{hanasu.BLOCKED}</p></div>' in page and "連絡先の形" not in page
code, j = talk(scene="think", hypothesis="H-ZZ", text="無い仮説")
assert code == 422 and j["kept"] is False, j
# 同じ画面で、別の仮説について話した考えと、仮説を選ばずに話した考え（頁に選ぶ欄は無いが、前に残した字と、JS の無い送り方の分。記録の形は受ける）
THINK_OTHER, THINK_FREE = "糸を引くと、下から開くのかもしれない", "どの案か分からないけど、紙が固そう"
assert talk(scene="think", hypothesis="H-B", text=THINK_OTHER, who=W)[0] == 200 and talk(scene="think", text=THINK_FREE, who=W)[0] == 200

# ---- 2 工夫: 刷った紙と手順の番号に結ぶ。手順の数の外の番号には結ばない（字は残す）。刷っていない紙は断る
CRAFT, CRAFT_QUIET = "糊代を先に折り癖を付けたら、貼りやすかった", "扇の端を少し切った"
CRAFT_OTHER, CRAFT_NOWHO, CRAFT_NOJS = "別の机で、筒を太く巻いた", "定規で折り目を押さえた", "折り目に爪で筋を付けた"
code, j = talk(scene="craft", hypothesis="H-A", sheet_version="1", step="2", text=CRAFT, who=W, via="voice")
assert code == 200 and j["kept"] is True and j["note"] == hanasu.KEPT, j
code, j = talk(scene="craft", hypothesis="H-A", sheet_version="1", step="99", text=CRAFT_QUIET, who=W)
assert code == 200 and j["kept"] is True, j
assert talk(scene="craft", hypothesis="H-A", sheet_version="1", step="1", text=CRAFT_OTHER, who=W2)[0] == 200
# 形の外の印は残さない。印が無いと記録に入れられない
code, j = talk(scene="craft", hypothesis="H-A", sheet_version="1", step="3", text=CRAFT_NOWHO, who="Tanaka Taro!")
assert code == 200 and j["kept"] is True and j["note"] == hanasu.KEPT, j
code, j = talk(scene="craft", hypothesis="H-B", sheet_version="1", step="1", text="刷っていない紙")
assert code == 422 and j["kept"] is False, j
# JS が無い時は、戻る道の付いた頁で答える（戻り先は場面から作る）
code, page, _ = post(f"/toy/{G}/talk", {"scene": "craft", "hypothesis": "H-A", "sheet_version": "1", "step": "3", "text": CRAFT_NOJS})
assert code == 200 and "残しました" in page and f'href="/toy/{G}/tsukuru?h=H-A&amp;v=1&amp;n=3"' in page, page[-600:]

# ---- 記録を残す: 同じ画面で話した工夫（同じ紙の物）と考え（同じ仮説か、仮説を選ばなかった物）が、その記録に入る
assert talk_log.talks(G, shared_only=True) == [], "記録に入る前の字は、学ぶ人の頁が読む口に出ない"
code, body, _ = post(f"/toy/{G}/record-json", {"hypothesis": "H-A", "result": "動いた", "note": "", "who": W})
assert code == 201 and json.loads(body) == {"id": "R-0001", "kufu": 2, "kangae": 2}, body
RID = "R-0001"
ku = talk_log.kufu(G, RID)
# 並びは、考え → 作りながら（手順の順）。同じ分の中の順は決まらないので、考えは集まりで見る。記録に入った字は、ほかの人の頁に出す印が付く
assert {(k["when"], k["step"], k["text"]) for k in ku[:2]} == {("idea", None, THINK), ("idea", None, THINK_FREE)}, ku
assert [(k["when"], k["step"], k["text"]) for k in ku[2:]] == [("making", 2, CRAFT), ("making", None, CRAFT_QUIET)] and all(k["share"] for k in ku), ku
# 同じ画面で次の記録を残しても、前の記録に入った字は動かない（別の仮説の考えは、この紙の記録に入らない）。印の無い画面の記録には、何も入らない
code, body, _ = post(f"/toy/{G}/record-json", {"hypothesis": "H-A", "result": "動いた", "who": W})
assert code == 201 and json.loads(body) == {"id": "R-0002"}, body
code, body, _ = post(f"/toy/{G}/record-json", {"hypothesis": "H-A", "result": "動かない"})
assert code == 201 and json.loads(body) == {"id": "R-0003"}, body
assert talk_log.kufu(G, "R-0002") == [] and talk_log.kufu(G, "R-0003") == [] and talk_log.kufu(G, RID) == ku
# 玩具の頁の記録の欄（JS が無くても送れるフォーム）から残した時も、同じに入る。別の机の工夫は、その机の記録に入る
assert post(f"/toy/{G}/record", {"hypothesis": "H-A", "result": "動いた", "who": W2})[0] == 303
assert talk_log.kufu(G, "R-0004") == [{"when": "making", "step": 1, "text": CRAFT_OTHER, "share": True}], talk_log.kufu(G, "R-0004")
# 記録の欄に書いた直した点（部品・変えた事・結果）を持つ記録。話した字とは別に残り、記録の札では同じ節に並ぶ
rid5, failures = records.add({"source_id": G, "hypothesis_id": "H-A", "sheet_version": 1, "result": "動いた",
                              "fixes": [{"part": "外筒", "change": "太く巻いた", "outcome": "内筒が入りやすくなった"}]})
assert rid5 == "R-0005" and not failures and talk_log.kufu(G, rid5) == []

# ---- 3 できた物: 試した記録に結ぶ。記録に入るので、ほかの人の頁にも出る（選び肢は無い。送っても受けない）
KEEP_A, KEEP_B = "内筒が固かったので、角を丸く切った", "扇の根元を糸で留めたら、開いたままになった"
records.claim(RID, REC_KEY)  # 受け口の形を見る。別の人が断られる事は tests/test_record_owner.py が見る
records.claim("R-0002", REC_KEY)
code, j = talk(scene="keep", record=RID, text=KEEP_A, share="0")
assert code == 200 and j["kept"] is True and j["note"] == hanasu.KEPT, j
# JS が無い時は、戻る道の付いた頁で答える。戻る道の字は、玩具の頁の入口と同じ字
code, page, _ = post(f"/toy/{G}/talk", {"scene": "keep", "record": "R-0002", "text": "JS の無い画面で足した字"})
assert code == 200 and hanasu.KEPT in page and f'href="/toy/{G}/techo#mine">手帖をひらく（作りながら聞く・上げる）</a>' in page, page[-500:]
assert talk_log.kufu(G, "R-0002")[0]["text"] == "JS の無い画面で足した字"
for p in files():  # この先の数を変えないよう、見本を片づける
    if json.loads(p.read_text(encoding="utf-8")).get("text") == "JS の無い画面で足した字":
        p.unlink()
assert talk(scene="keep", record=RID, text=KEEP_B, via="voice")[0] == 200
code, j = talk(scene="keep", record="R-9999", text="無い記録")
assert code == 403 and j["why"] == hanasu.REFUSED, j
# 前にあった、記録ごとの合図の受け口は無い（選び肢と、既定で出さない形はやめた。本人の決定 11-05）
n = len(files())
assert post(f"/toy/{G}/talk", {"signing": "1", "record": RID})[0] == 422 and len(files()) == n
assert all(k["share"] for k in talk_log.kufu(G, RID)) and len(talk_log.kufu(G, RID)) == 6

# ---- 床に落ちた文は残らない。理由が返り、落とした事だけが残る。空の文と、決まりの外の場面は何も残さない
n = len(files())
code, j = talk(scene="think", text="電話は 090-1234-5678 です。扇が開くと思う")
assert code == 422 and j["kept"] is False and j["why"] == hanasu.BLOCKED, j
code, j = talk(scene="keep", record=RID, text="緑町小学校の田中と申します")
assert code == 422 and j["why"] == hanasu.BLOCKED and "の形がある" not in j["why"], j  # 作る人向けの理由の言葉は、そのまま出さない
assert len(files()) == n + 2
code, j = talk(scene="think", text="   ")
assert code == 422 and j["why"] == hanasu.NOHEARD, j
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
                                         "scene": "think", "step": None, "record_id": RID, "text": THINK, "via": "voice", "share": True, "who": "abcdefghij", "at": ""}
assert by_text[THINK]["sheet_set"], "刷った組が空（エンジンの束と結べない）"
assert by_text["糸で引く所が気になる"]["hypothesis_id"] is None and by_text["糸で引く所が気になる"]["via"] == "text"
assert by_text[CRAFT] | {"at": "", "sheet_set": ""} == {"source_id": G, "hypothesis_id": "H-A", "sheet_version": 1, "template": "slider_fan", "sheet_set": "", "scene": "craft",
                                                       "step": 2, "record_id": RID, "text": CRAFT, "via": "voice", "share": True, "who": W, "at": ""}
assert by_text[CRAFT_QUIET]["step"] is None and by_text[CRAFT_QUIET]["record_id"] == RID and by_text[CRAFT_QUIET]["share"] is True
assert by_text[CRAFT_OTHER]["record_id"] == "R-0004" and by_text[CRAFT_OTHER]["who"] == W2 and by_text[CRAFT_OTHER]["share"] is True
# 形の外の印は残さない。印の無い工夫は、どの記録にも入らない
assert by_text[CRAFT_NOWHO]["who"] == "" and by_text[CRAFT_NOWHO]["step"] == 3 and by_text[CRAFT_NOWHO]["record_id"] is None and by_text[CRAFT_NOJS]["record_id"] is None
# 考え: 同じ仮説の物と、仮説を選ばなかった物は記録に入る。別の仮説の物と、印の無い物は入らない
assert by_text[THINK_FREE]["record_id"] == RID and by_text[THINK_FREE]["hypothesis_id"] is None and by_text[THINK_FREE]["share"] is True
assert by_text[THINK_OTHER]["record_id"] is None and by_text[THINK_OTHER]["share"] is False and by_text["糸で引く所が気になる"]["record_id"] is None
assert by_text[CRAFT_NOWHO]["share"] is False, "記録に入っていない字には、出す印が付かない"
assert by_text[KEEP_A]["record_id"] == RID and by_text[KEEP_A]["share"] is True and by_text[KEEP_A]["hypothesis_id"] == "H-A"
assert by_text[KEEP_B]["share"] is True and by_text[KEEP_B]["via"] == "voice"
assert talk_log.dropped(G) == {"pii": 2, "name": 1}
# 聞く口の質問の置き場には混ざらない（集計の数を変えない）
assert making_log.asks(G) == [] and making_log.summary(G)["asks"] == []

# ---- 読む口: 学ぶ人の頁とギャラリーは、記録に入った字を読める（記録に入る前の字は読めない）
OPEN = {THINK, THINK_FREE, CRAFT, CRAFT_QUIET, KEEP_A, KEEP_B}
assert {t["text"] for t in talk_log.talks(G, record_id=RID, shared_only=True)} == OPEN
assert {t["text"] for t in talk_log.talks(G, shared_only=True)} == OPEN | {CRAFT_OTHER}
assert {t["text"] for t in talk_log.talks(G, scene="keep")} == {KEEP_A, KEEP_B}
# 記録に結んだ字の並び: 考え → 作りながら話した物（手順の順）→ 上げた後に残した物。同じ分の中の順は決まらないので、集まりで見る
ku = talk_log.kufu(G, RID)
assert [k["when"] for k in ku] == ["idea", "idea", "making", "making", "made", "made"] and [(k["step"], k["text"]) for k in ku[2:4]] == [(2, CRAFT), (None, CRAFT_QUIET)], ku
assert {k["text"] for k in ku[:2]} == {THINK, THINK_FREE} and {k["text"] for k in ku[4:]} == {KEEP_A, KEEP_B}
assert talk_log.kufu(G, RID, shared_only=True) == ku and [k["text"] for k in talk_log.kufu(G, "R-0004", shared_only=True)] == [CRAFT_OTHER]
assert talk_log.WHEN == {"think": "idea", "craft": "making", "keep": "made"}  # 型紙エンジンの報告の欄と合わせた名（#275）
# ---- 輪と束が読む口（talk_log.texts）: 玩具・紙・場面・記録で絞って字を返す。印・見せる印・声か字かは返さない。記録に結ぶ前の字も入る
every = talk_log.texts(G)
assert all(tuple(t) == talk_log.TEXT_KEYS for t in every) and not {"who", "share", "via"} & set(talk_log.TEXT_KEYS)
assert {t["text"] for t in every} == OPEN | {CRAFT_OTHER, "糸で引く所が気になる", THINK_OTHER, CRAFT_NOWHO, CRAFT_NOJS}, sorted(t["text"] for t in every)
assert talk_log.texts() == every and talk_log.texts("NDL-1187053-R0000014-R") == []
assert {t["text"] for t in talk_log.texts(G, scene="think")} == {THINK, "糸で引く所が気になる", THINK_OTHER, THINK_FREE}
assert {t["text"] for t in talk_log.texts(G, scene="think", hypothesis_id="H-B")} == {THINK_OTHER}
assert {(t["step"], t["text"]) for t in talk_log.texts(G, scene="craft", hypothesis_id="H-A", sheet_version=1)} == {(2, CRAFT), (None, CRAFT_QUIET), (1, CRAFT_OTHER), (3, CRAFT_NOWHO), (3, CRAFT_NOJS)}
assert talk_log.texts(G, scene="craft", sheet_version=2) == [] and {t["text"] for t in talk_log.texts(G, record_id=RID)} == OPEN
assert {t["text"] for t in talk_log.texts(G, scene="keep")} == {KEEP_A, KEEP_B} and {t["record_id"] for t in talk_log.texts(G, scene="keep")} == {RID}
# その画面で話した字だけ（その場限りの印で絞る。形の外の印では何も返さない）
assert {t["text"] for t in talk_log.texts(G, scene="think", who=W)} == {THINK, THINK_OTHER, THINK_FREE} and {t["text"] for t in talk_log.texts(G, who=W2)} == {CRAFT_OTHER}
assert talk_log.texts(G, who="") == [] and talk_log.texts(G, who="Tanaka Taro!") == []
one = next(t for t in every if t["text"] == CRAFT)
assert one == {"source_id": G, "hypothesis_id": "H-A", "sheet_version": 1, "template": "slider_fan", "sheet_set": one["sheet_set"], "scene": "craft", "step": 2,
               "record_id": RID, "text": CRAFT, "at": one["at"]} and one["sheet_set"] and re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d\+09:00", one["at"])
sm = talk_log.summary(G)
assert {t["text"] for t in sm["think"]} == {THINK, "糸で引く所が気になる", THINK_OTHER, THINK_FREE}
assert sm["craft"]["H-A"][1][1] == [CRAFT_OTHER] and sm["craft"]["H-A"][1][2] == [CRAFT] and set(sm["craft"]["H-A"][1][3]) == {CRAFT_NOWHO, CRAFT_NOJS}, sm["craft"]
assert list(sm["craft"]["H-A"][1]) == [1, 2, 3, None] and sm["craft"]["H-A"][1][None] == [CRAFT_QUIET], sm["craft"]
assert [(r["record_id"], r["hypothesis_id"], r["sheet_version"], len(r["kufu"])) for r in sm["records"]] == [(RID, "H-A", 1, 6), ("R-0004", "H-A", 1, 1)], sm["records"]
assert sm["via"] == {"voice": 3, "text": 8} and sm["dropped"] == {"pii": 2, "name": 1}, sm

# ---- 頁: 3 つの場面に口がある。話す釦は既定で隠れている
MIC = '<button type="button" class="hanasu-mic" aria-pressed="false">話す</button>'
code, toy = get(f"/toy/{G}")
assert code == 200 and 'id="hanasu"' in toy and f'action="/toy/{G}/talk#hanasu"' in toy and 'name="scene" value="think"' in toy and MIC in toy
assert hanasu.NOTICE in toy and toy.count("<script>(()=>{\nconst REC=") == 1
code, tsu = get(f"/toy/{G}/tsukuru?h=H-A&n=2")
assert code == 200 and 'name="scene" value="craft"' in tsu and 'name="step" value="2"' in tsu and 'name="sheet_version" value="1"' in tsu and MIC in tsu
code, techo = get(f"/toy/{G}/techo")
assert code == 200 and f'name="record" value="{RID}"' in techo and MIC in techo
# 釦に hidden 属性を付けない。指で触る機器の床（skin.TAP_FLOOR の [hidden]{display:none!important}）が CSS の出し分けに勝って、幅 1100 以下で釦が消えた。
# 画面の結果は tests/test_mic_seen.py が測る（Chrome が無い機械では測れないので、原因の形をここでも字で見る）
assert re.search(r'<button[^>]*class="hanasu-mic"[^>]*\bhidden\b', toy + tsu + techo) is None and ".hanasu-local .hanasu .hanasu-mic,.hanasu-browser .hanasu .hanasu-mic{display:block}" in hanasu.STYLE
# ほかの人に見せるかの選び肢は、どの頁にも置かない（記録に入った字は、記録の感想と同じに出す。本人の決定 11-05）
for page in (toy, tsu, techo):
    assert 'name="share"' not in page and 'name="sign"' not in page and "hanasu-sign" not in page and 'type="checkbox" name' not in page.split('id="mine"')[-1]
assert techo.count("<script>(()=>{\nconst REC=") == 1, "手帖には部品が何個あっても、動きは 1 回だけ置く"
assert techo.index(f'name="record" value="{RID}"') < techo.index("</div></section>") and techo.rindex("const REC=") > techo.rindex('id="mine"')

# ---- 見せる範囲: 記録に入った工夫の字は、手帖の記録の札に文で出る。記録に入っていない字と、考えは、学ぶ人の頁に出ない
code, gallery = get("/gallery")
for page in (toy, tsu, techo, gallery):
    for text in ("糸で引く所が気になる", THINK_OTHER, CRAFT_NOWHO, CRAFT_NOJS, THINK, THINK_FREE):
        assert text not in page, text
# 作りながら見る頁には出さない。玩具の頁と上げた物の頁には、記録の札に出る（本人の決定 11-05 の 2b「全部見せる」、#315。tests/test_talk_in_gallery.py）
for text in OPEN | {CRAFT_OTHER}:
    assert text not in tsu, text
for text in (OPEN - {THINK, THINK_FREE}) | {CRAFT_OTHER}:
    assert text in toy and text in gallery, text
# 手帖の記録の札の「工夫した所（直した所）」: 作りながら話した物（手順の番号つき）→ 上げた後に残した物。選び肢は無い
card = techo[techo.index(f"{RID}　"):techo.index('<div class="hanasu" data-hanasu', techo.index(f"{RID}　"))]
assert '<p class="hanasu-kufu-head">工夫した所（直した所）</p>' in card and f'data-kufu="{RID}"' in card, card
for line in (f"<li>手順 2: {CRAFT}</li>", f"<li>{CRAFT_QUIET}</li>", f"<li>{KEEP_A}</li>", f"<li>{KEEP_B}</li>"):
    assert line in card, line
assert card.index(CRAFT) < card.index(CRAFT_QUIET) < min(card.index(KEEP_A), card.index(KEEP_B)) and "<form" not in card and "件（" not in card
# ほかの机の記録にも、その机の工夫が出る。何も入っていない記録には、節を出さない。記録の欄の直した点は、同じ節に文で出る
assert f'data-kufu="R-0004"><p class="hanasu-kufu-head">工夫した所（直した所）</p><ul><li>手順 1: {CRAFT_OTHER}</li></ul></div>' in techo
assert techo.count('class="hanasu-kufu"') == 3 and "<ul><li>外筒 / 太く巻いた / 内筒が入りやすくなった</li></ul></div>" in techo

# ---- 作る側の頁: 場面ごとに並ぶ。落とした文は無く、数だけ。順位と点の形が無い
code, loop_page = get(f"/loop/{G}")
assert code == 200 and "7 話した事" in loop_page
for text in (THINK, THINK_OTHER, THINK_FREE, CRAFT, KEEP_A, KEEP_B):
    assert text in loop_page, text
for text in (CRAFT_QUIET, CRAFT_OTHER, CRAFT_NOWHO, CRAFT_NOJS):
    assert text in loop_page, text
assert "仮説 A の紙・版 1・手順 2" in loop_page and "連絡先の形 2 件・名乗りや学校の形 1 件" in loop_page
# 記録ごとの「工夫した所（直した所）」: 作りながら話した物（手順の番号）と、上げた後の物。見せてよいの印は、選んだ物にだけ
assert f"<h4>{RID}（仮説 A の紙・版 1）</h4>" in loop_page and "<h4>R-0004（仮説 A の紙・版 1）</h4>" in loop_page and "<h4>R-0002" not in loop_page
assert f"<li>考え: {THINK}</li>" in loop_page and f"<li>手順 2: {CRAFT}</li>" in loop_page and f"<li>作りながら: {CRAFT_QUIET}</li>" in loop_page
assert f"<li>上げた後: {KEEP_A}</li>" in loop_page and f"<li>手順 1: {CRAFT_OTHER}</li>" in loop_page and "［隠している］</li>" not in loop_page
assert "声から字にした物 3 件・字で書いた物 8 件" in loop_page
part = loop_page[loop_page.index("7 話した事"):]
for word in ("090-1234", "緑町", "田中", "位", "点数", "％", "ランキング"):
    assert word not in part, word

# ---- 頁の code: マイクを開く・録る・声を送る物が無い。声を字にする指定は「端末の中だけ」
for word in ("getUserMedia", "MediaRecorder", "AudioContext", "createMediaStreamSource", "captureStream", "audio:true", "audio: true", "srcObject",
             "toBlob", "toDataURL", "FileReader", "Blob(", "WebSocket", "sendBeacon", "XMLHttpRequest", "EventSource", "RTCPeerConnection"):
    assert word not in hanasu.SCRIPT and word not in hanasu.STYLE, word
assert "processLocally:true" in hanasu.SCRIPT and "r.processLocally=true" in hanasu.SCRIPT and "REC.available({langs:[LANG],processLocally:true})" in hanasu.SCRIPT
# 端末の中で字にする時は話し続けられる形。ブラウザの既定の口は、1 回話すごとに止まる形で聞き、途中の字も出す（機種によって同じ字が重なるのを避ける）
assert "r.lang=LANG;r.continuous=onDevice;r.interimResults=!onDevice;if(onDevice)r.processLocally=true;" in hanasu.SCRIPT
# 送る所は 1 つで、字のフォームの形だけ。聞き取った所（onresult）からは送らない
assert hanasu.SCRIPT.count("fetch(") == 1 and "fetch(form.action,{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'}" in hanasu.SCRIPT
onresult = hanasu.SCRIPT[hanasu.SCRIPT.index("r.onresult"):hanasu.SCRIPT.index(" r.onerror")]
assert "fetch" not in onresult and "submit" not in onresult and "box.value" in onresult
# 聞き取った所は、欄に字を足して知らせるだけ。字の並びごと固定する（ここに、送る・押す・残すを足すと落ちる。「残すを押すまで送らない」が設計の要）
assert onresult == "r.onresult=(ev)=>{\n  // 読み上げの間に入った字は、端末が自分の答えを聞いた物なので入れない。\n  if(window.speechSynthesis&&speechSynthesis.speaking)return;\n  // 聞き始めた時の欄の字の後ろに、この回に聞いた字を置き直す（途中の字が来るたびに足すと、同じ字が重なる）。\n  let said='',n=ev.results.length;for(let i=0;i<n;i++)said+=ev.results[i][0].transcript;said=said.trim();\n  // 欄の長さで切る（script が入れた字には maxlength が効かない。見せた字と残る字を同じにする）。\n  if(said){box.value=((base?base+' ':'')+said).slice(0,box.maxLength);root.dataset.via='voice';note(root,ev.results[n-1].isFinal?M.heard:M.listening)}};\n", onresult
# 止まった後に「聞いています」を残さない。終わりの字が来ない機種でも、途中の字があれば読んで残せると知らせる
assert "if(n.textContent===M.listening)n.textContent=box.value.trim()!==base?M.heard:''" in hanasu.SCRIPT
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

# ---- 切り替え（OMOCHAE_VOICE）: 既定は browser（本人の決定 11-05: iPhone・iPad でも話す釦を出す）。決まりの外の値は既定に戻す
assert hanasu.mode() == "browser" and 'data-voice="browser"' in toy and "const want='browser';" in toy
for value, want in (("local", "local"), ("off", "off"), ("everything", "browser"), ("", "browser")):
    os.environ["OMOCHAE_VOICE"] = value
    assert hanasu.mode() == want and f"const want='{want}';" in hanasu.assets(), value
    assert f'data-voice="{want}"' in get(f"/toy/{G}")[1], value
os.environ.pop("OMOCHAE_VOICE")

# ---- 利用者向けの文: 本人が採ったやさしい言葉の文（11-05、Issue #318）。一字でも変わったら落ちるように、ここに決定の文を書く
ADOPTED = {
    "NOTICE": "残るのは字だけです。声は録音しません。このサイトは声を受け取りません。残す前に、字を読んで直せます。名前・学校の名前・住所・電話番号・メールは書かないでください。残した字は、AI（Claude）が型紙をよくする案を考えるのにも使います。",
    "HOW_LOCAL": "「話す」を押すと、声はこの機械（タブレットやパソコン）の中で字になります。",
    "HOW_BROWSER": "「話す」を押すと、ブラウザ（ネットを見るアプリ）が声を字にします。そのとき、声がブラウザの会社に送られることがあります。このサイトは声を受け取りません。",
    "HOW_NONE": "この機械では、声を機械の中だけで字にできません。だから「話す」のボタンを出していません。キーボードのマイクのマークを押すと、話した事が字で入ります（声がどう使われるかは、機械の設定によってちがいます）。",
    "KEPT": "残しました。型紙や説明をよくするのに使います。",
    "BLOCKED": "名前や学校の名前のような言葉が入っていたので、残しませんでした。その言葉を消して、もう一度「残す」を押してください。",
    "FAILED": "残せませんでした。インターネットにつながっているか見て、もう一度押してください。",
    "NOHEARD": "聞き取れませんでした。もう一度押すか、字で書いてください。",
    "UPLOAD_NOTICE": "声は字にかえて、声は残しません。のせた写真と動画は、いつ・どこでとったかなどの情報を消してから残します。",
}
for name, text in ADOPTED.items():
    assert getattr(hanasu, name) == text, name
# 本人が採った字（一字も変えない）。話す口の断りの後に置く。断りは定数 1 か所で、話す口のある頁の全部に同じ物が出る
AI_USE = "残した字は、AI（Claude）が型紙をよくする案を考えるのにも使います。"
assert hanasu.NOTICE.endswith("書かないでください。" + AI_USE)
for page in (toy, tsu, techo):
    assert page.count(AI_USE) == page.count('<div class="hanasu" data-hanasu') >= 1, "話す口ごとに 1 回"
    assert hanasu.NOTICE in page
# 断りと、話す釦の説明 3 つは、3 つの頁の口に出る
for page in (toy, tsu, techo):
    for name in ("NOTICE", "HOW_LOCAL", "HOW_BROWSER", "HOW_NONE"):
        assert ADOPTED[name] in page, name
# 場面の見出しと例・選ぶ欄・頁の頭の一文
assert '<p class="hanasu-head">考えを話す</p>' in toy and 'placeholder="『こう動くと思う』『ここが気になる』など"' in toy
assert '<p class="hanasu-head">工夫を話す</p>' in tsu and 'placeholder="『ここをこうしたら、うまくいった』など"' in tsu
assert '<p class="hanasu-head">工夫した所や、思った事を足す</p>' in techo
# 考えは、頁に出ているたたき台に結ぶ。仮説を選ぶ欄を置かない（型紙は玩具ごとに 1 枚。J-032）
think_form = toy[toy.index('id="hanasu"'):toy.index("</form>", toy.index('id="hanasu"'))]
assert '<input type="hidden" name="hypothesis" value="H-A">' in think_form and "<select" not in think_form and "どの案（仮説）" not in toy
assert '<p class="lead">仮説は、AI が考えたためしの案です。見て思った事を、話すか書いて残してください。合っているかどうかは見ません。思ったとおりに話してください。</p>' in toy
# 釦は「話す」「止める」「残す」のまま。声を聞いている時などの知らせ
assert ">話す</button>" in toy and '<button class="hanasu-go">残す</button>' in toy and "mic.textContent=on?'止める':'話す'" in hanasu.SCRIPT
for said in ("聞いています。話した事が、欄に字で出ます。", "字にしました。読んで、よければ「残す」を押してください。",
             "残せませんでした。インターネットにつながっているか見て、もう一度押してください。", "この機械では字にできませんでした。字で書いてください。",
             "聞き取れませんでした。もう一度押すか、字で書いてください。", "声を字にするしくみを、この機械に入れています（はじめの 1 回だけ）…"):
    assert f"'{said}'" in hanasu.SCRIPT, said
# ③ で上げる時の説明文は、手帖（③ の上げる頁）の上げる節に出る。聞く口の断りの文は、この頁では使わない
assert f'<p class="meta" id="up-notice">{ADOPTED["UPLOAD_NOTICE"]}</p>' in techo and making_log.ASK_NOTICE not in techo and making_log.ASK_NOTICE in toy
# 端末の中で字にできないと分かった時の知らせは、採られた断りの文（次に押すと声が外へ送られる事がある、と押す前に言う）
assert f"tobrowser:'{ADOPTED['HOW_BROWSER']}'" in hanasu.SCRIPT and "__" not in hanasu.SCRIPT.replace("__VOICE__", "")
# 本人の確認が済んでいない文を足していない（入れる時は、確認の後に、この一覧と一緒に直す）。節の名だけは本人の言葉のまま
assert hanasu.KUFU_HEAD == "工夫した所（直した所）" and f'<p class="hanasu-kufu-head">{hanasu.KUFU_HEAD}</p>' in techo
for word in ("に入ります", "ほかの人にも見せます", "ほかの人には見せません", "に入りました", "残しています", "公開のデモでは、文を出しません", "頁を開き直して",
             "この端末の中では", "もう一度押すと止まる）\" hidden", "この頁で残した言葉", "どの仮説についてか", "工夫した所、考えた事"):
    assert word not in toy + tsu + techo + hanasu.SCRIPT, word
# 前の文が残っていない
# 「どこにも送りません」は、ブラウザの音声認識で聞く画面では本当でない（声がブラウザの会社に送られる事がある）。本人が決め直した文（11-05）に、この言い方は無い
for old in ("残すのは字だけです", "話す釦を押すと", "型紙と案内を直す材料にします", "ほかの人に見せてよい", "作る側だけが読みます", "どこにも送りません", "録音しないし"):
    assert old not in toy + tsu + techo + hanasu.SCRIPT, old

# ---- 合言葉なしで開いた場: 字は残せるが、人の言葉は頁に出さない（J-028。件数だけ）
open_server = serve(0, public_open=True)
threading.Thread(target=open_server.serve_forever, daemon=True).start()
open_base = f"http://127.0.0.1:{open_server.server_address[1]}"
code, open_techo = get(f"/toy/{G}/techo", at=open_base)
assert code == 200 and not any(text in open_techo for text in OPEN | {CRAFT_OTHER}) and f'name="record" value="{RID}"' in open_techo
assert 'class="hanasu-kufu"' not in open_techo and "太く巻いた" not in open_techo
code, body, _ = post(f"/toy/{G}/talk", {"json": "1", "scene": "think", "text": "開いた場でも残せる"}, at=open_base)
assert code == 200 and json.loads(body)["kept"] is True
assert get(f"/loop/{G}", at=open_base)[0] == 404

# ---- 作る側の道具（talk_log.set_share）: 名前などに気づいた時に、その記録の字を、消さずに学ぶ人の頁から隠せる。戻せる
assert talk_log.set_share(G, RID, False) == (6, []) and talk_log.set_share(G, RID, False) == (0, [])
assert talk_log.kufu(G, RID, shared_only=True) == [] and len(talk_log.kufu(G, RID)) == 6 and {t["text"] for t in talk_log.talks(G, shared_only=True)} == {CRAFT_OTHER}
assert talk_log.texts(G, record_id=RID) == [] and not OPEN & {t["text"] for t in talk_log.texts(G)}, "作る側が隠した字は、輪と束が読む口にも出ない"
hidden = get(f"/toy/{G}/techo")[1]
assert not any(text in hidden for text in OPEN) and f'data-kufu="{RID}"' not in hidden and CRAFT_OTHER in hidden
assert f"<li>手順 2: {CRAFT}［隠している］</li>" in get(f"/loop/{G}")[1]
n, failures = talk_log.set_share(G, "R-0002", False)
assert n == 0 and failures and failures[0].where == "record_id"  # 話した字の無い記録
assert talk_log.set_share("NDL-1187053-R0000014-R", RID, True)[0] == 0 and talk_log.kufu(G, RID, shared_only=True) == [], "別の玩具の名では変えられない"
assert talk_log.set_share(G, RID, True) == (6, []) and f"<li>手順 2: {CRAFT}</li>" in get(f"/toy/{G}/techo")[1]

# ---- 記録を取り下げると、結んだ字も消える。ほかの場面の字は残る
before = len(talk_log.talks(G))
gone, failures = records.withdraw(RID)
assert not failures and sum(1 for g in gone if g.startswith("making/talk-")) == 7, gone  # 考え 2 件・作りながら 2 件・上げた後 2 件・床で落とした物
assert talk_log.talks(G, record_id=RID) == [] and talk_log.talks(G, scene="keep") == [] and talk_log.kufu(G, RID) == []
left = {t["text"] for t in talk_log.talks(G)}
assert len(talk_log.talks(G)) == before - 6 and {THINK_OTHER, CRAFT_OTHER, CRAFT_NOWHO} <= left and not {THINK, THINK_FREE, CRAFT, CRAFT_QUIET} & left
after = get(f"/loop/{G}")[1]
assert KEEP_B not in after and CRAFT not in after and CRAFT_OTHER in after

# ---- 記録に結ぶ条件: 同じ玩具・同じ印の物だけ。工夫は同じ紙（仮説と版）、考えは同じ仮説か、仮説を選ばなかった物。条件を 1 つ外した物は入らない
W3, TORA = "uvwxyzabcd", "NDL-1187053-R0000014-R"
for hid, ver, who, text in (("H-B", 1, W3, "別の仮説の紙の工夫"), ("H-A", 2, W3, "別の版の紙の工夫"), ("H-A", 1, "qrstuvwxyz", "別の画面の工夫"), ("H-A", 1, W3, "同じ紙の工夫")):
    path, failures = talk_log.add(G, "craft", text, hypothesis_id=hid, sheet_version=ver, step=1, who=who)
    assert path and not failures, failures
for hid, who, text in (("H-B", W3, "別の仮説の考え"), (None, W3, "仮説を選ばない考え"), (None, "qrstuvwxyz", "別の画面の考え")):
    path, failures = talk_log.add(G, "think", text, hypothesis_id=hid, who=who)
    assert path and not failures, failures
assert talk_log.bind(TORA, "H-A", 1, W3, "R-0002") == (0, 0), "別の玩具の記録には入らない"
assert talk_log.bind(G, "H-A", 1, "", "R-0002") == (0, 0) and talk_log.bind(G, "H-A", 1, "Tanaka Taro!", "R-0002") == (0, 0), "印が無いと入らない"
assert talk_log.bind(G, "H-A", 1, W3, "R-0002") == (1, 1) and [k["text"] for k in talk_log.kufu(G, "R-0002")] == ["仮説を選ばない考え", "同じ紙の工夫"]
assert talk_log.bind(G, "H-A", 1, W3, "R-0003") == (0, 0), "1 回入った字は、次の記録に動かない"
assert talk_log.bind(G, "H-B", 1, W3, "R-0003") == (1, 1) and [k["text"] for k in talk_log.kufu(G, "R-0003")] == ["別の仮説の考え", "別の仮説の紙の工夫"]
assert talk_log.bind(G, "H-A", 2, W3, "R-0003") == (1, 0) and {k["text"] for k in talk_log.kufu(G, "R-0003")} == {"別の仮説の考え", "別の仮説の紙の工夫", "別の版の紙の工夫"}
assert {"別の画面の工夫", "別の画面の考え"} <= {t["text"] for t in talk_log.talks(G) if not t["record_id"]}

# ---- 出す時に、入口の床をもう一度当てる: 手で置いた字や、床を広げる前に残した字に連絡先の形があれば、学ぶ人の頁が読む口に出さない
assert len(talk_log.kufu(G, "R-0003", shared_only=True)) == 3
some = next(p for p in files() if json.loads(p.read_text(encoding="utf-8")).get("record_id") == "R-0003")
placed = some.with_name("talk-20261105-0000-deadbeef.json")
placed.write_text(json.dumps(json.loads(some.read_text(encoding="utf-8")) | {"scene": "craft", "text": "電話は 090-1111-2222 です"}, ensure_ascii=False), encoding="utf-8")
assert len(talk_log.kufu(G, "R-0003")) == 4 and len(talk_log.kufu(G, "R-0003", shared_only=True)) == 3 and len(talk_log.texts(G, record_id="R-0003")) == 3
assert "090-1111" not in "".join(t["text"] for t in talk_log.talks(G, shared_only=True)) and "090-1111" not in get(f"/toy/{G}/techo")[1]
placed.unlink()

server.shutdown()
open_server.shutdown()
print("OK 話す口: 3 つの場面で字だけが残り、話した工夫と考えが記録に入り、入口の床・見せる範囲・採られた文・声を持たない code を確かめた")
