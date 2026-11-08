"""話す口（一周の声の部分、Issue #279）。本人の決定 11-05「声そのものは残さない」「個人の情報は入口で落とす」。本物の API は呼ばない。

見る線:
- 3 つの場面（1 考え・2 工夫・3 できた物）で、字が残る。JS が無くても残せる。残る欄は決めた物だけで、声・IP・ブラウザの名・cookie が無い。時刻は分まで。
  1 考え の口（玩具の頁の 考えを話す）は 11-08 に頁から外した（本人の言葉 11-08「つくるの「考えを話す」は無くす。」）。受け口は前に残した字と
  前の頁から送る物のために残るので、受け口は前のまま見て、玩具の頁に口が無い事を見る。話す口の形と断りは、残った 2 工夫（作りながら見る頁）と
  3 できた物（手帖の記録の頁）の口で見る
- 作りながら話した工夫と、仮説を見て話した考えは、記録を残した時に、その記録に入る（同じ画面の物だけ。ほかの人の話は入らない）。
- 入口の床: 連絡先の形・名乗りの形・学年と組の形・学校の名前の形の文は残らない（落とした数だけ残る）。工作の話は落とさない。
- 話す口の台本は、マイクを開く code・録る code・声を送る code・声を字にする code（音声認識）を持たない。録る釦「声を録る」（録っている間は「止める」）を
  押した時に、置き場（web.clips）の voiceStart を 1 か所で呼び、もう一度押した時と「残す」の前に voiceStop を呼ぶ（本人 11-08 415「声も送って解析に使う形に
  する。」・本人の答え (A)「声を録る釦を置いて残す。」）。送るのは のこすの承認の時（web.nokosu）。受け口（/talk）は字のフォームだけを受け、音のファイルは断る。
- 録る釦は考えの口と工夫の口にあり、記録の札の足す口には無い（設計の 2 版の止め 1）。字の欄の下に「キーボードのマイクで話して入れられます。」の 1 行が
  3 つの場面の全部にある。前の「話す」の釦・音声認識・切り替え OMOCHAE_VOICE・どこで字にするかの断り（HOW_LOCAL・HOW_BROWSER・HOW_NONE）と
  NOHEARD は無い（本人 11-08「クロードの音声認識をはずして、ユーザーの端末の音声入力に頼るのでいいのではないか。」）。
  凍結の表の名の試験なので消さずに中身を替えた（理由は commit と docs/claude-usage.md）。
- 話した字は、記録に入っていても、学ぶ人の頁（手帖の記録の札も）に出ない（本人の決定 11-06、J-034。11-05 の「記録の感想と同じに出す」を変えた）。
  記録の札の「工夫した所（直した所）」には、記録の欄に書いた直した点だけが出る。合言葉なしで開いた場では、節ごと出ない（J-028）。
  作る側は、気づいた時に記録の字を輪と束から外せる。
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

from omochae import hypotheses, making_log, records, talk_log  # noqa: E402
from web import hanasu  # noqa: E402
from web.play_server import serve  # noqa: E402

G = "NDL-1187053-R0000005-L"
# 御来迎のたたき台の仮説（次の組は H-C の柄を下から押し上げる形・前の組は H-A。本人の決定 2026-11-06。hypotheses.sheet_id）
GS = hypotheses.sheet_of(G)["id"]
GL = hypotheses.SHOWN  # 頁と紙のたたき台の呼び名。11-08 から印（A・C）は出さない（本人の答え 11-08「そろえる。」・hypotheses.SHOWN）
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
assert post(f"/toy/{G}/print", {"hypothesis": GS})[0] == 303
assert not files()
# その場限りの印（画面が持つ乱数）。W は作って記録まで残す画面、W2 は同じ紙を別の机で作る画面
W, W2 = "abcdefghij", "klmnopqrst"

# ---- 1 考え: 仮説を選んでも、選ばなくても残る。JS が無い時は玩具の頁へ戻る
THINK = "筒を押すと、扇が上から開くと思う"
code, j = talk(scene="think", hypothesis=GS, text=THINK, via="voice", who=W)
assert code == 200 and j["kept"] is True and "残しました" in j["note"], j
code, _, head = post(f"/toy/{G}/talk", {"scene": "think", "text": "糸で引く所が気になる"})
assert code == 303 and head["Location"].startswith(f"/toy/{G}?msg=") and head["Location"].endswith("&at=hanasu#hanasu"), head
# 返事の文は落とさずに頁に 1 回出る（JS が無い時。送った後の返事を、着いた頁で読む形）。考えを話す の節（#hanasu）は 11-08 に外した
# （本人の言葉 11-08「つくるの「考えを話す」は無くす。」）ので、文は頁の文の受け所（toy_page の終わりの、錨 #kasetsu の頭）に出る
landed = get(head["Location"].split("#")[0])[1]
assert 'id="hanasu"' not in landed and landed.count('<div role="status"><p id="msg">残しました。型紙や説明をよくするのに使います。</p></div>') == 1, landed[:300]
# 通らなかった時も、理由が頁に 1 回出る（連絡先の形の名は出さない）
code, page, _ = post(f"/toy/{G}/talk", {"scene": "think", "text": "電話は 090-1234-5678 です"})
assert code == 422 and page.count(f'<div role="alert"><p id="msg">{hanasu.BLOCKED}</p></div>') == 1 and 'id="hanasu"' not in page and "連絡先の形" not in page
code, j = talk(scene="think", hypothesis="H-ZZ", text="無い仮説")
assert code == 422 and j["kept"] is False, j
# 同じ画面で、別の仮説について話した考えと、仮説を選ばずに話した考え（頁に選ぶ欄は無いが、前に残した字と、JS の無い送り方の分。記録の形は受ける）
THINK_OTHER, THINK_FREE = "糸を引くと、下から開くのかもしれない", "どの案か分からないけど、紙が固そう"
assert talk(scene="think", hypothesis="H-B", text=THINK_OTHER, who=W)[0] == 200 and talk(scene="think", text=THINK_FREE, who=W)[0] == 200

# ---- 2 工夫: 刷った紙と手順の番号に結ぶ。手順の数の外の番号には結ばない（字は残す）。刷っていない紙は断る
CRAFT, CRAFT_QUIET = "糊代を先に折り癖を付けたら、貼りやすかった", "扇の端を少し切った"
CRAFT_OTHER, CRAFT_NOWHO, CRAFT_NOJS = "別の机で、筒を太く巻いた", "定規で折り目を押さえた", "折り目に爪で筋を付けた"
code, j = talk(scene="craft", hypothesis=GS, sheet_version="1", step="2", text=CRAFT, who=W, via="voice")
assert code == 200 and j["kept"] is True and j["note"] == hanasu.KEPT, j
code, j = talk(scene="craft", hypothesis=GS, sheet_version="1", step="99", text=CRAFT_QUIET, who=W)
assert code == 200 and j["kept"] is True, j
assert talk(scene="craft", hypothesis=GS, sheet_version="1", step="1", text=CRAFT_OTHER, who=W2)[0] == 200
# 形の外の印は残さない。印が無いと記録に入れられない
code, j = talk(scene="craft", hypothesis=GS, sheet_version="1", step="3", text=CRAFT_NOWHO, who="Tanaka Taro!")
assert code == 200 and j["kept"] is True and j["note"] == hanasu.KEPT, j
code, j = talk(scene="craft", hypothesis="H-B", sheet_version="1", step="1", text="刷っていない紙")
assert code == 422 and j["kept"] is False, j
# JS が無い時は、戻る道の付いた頁で答える（戻り先は場面から作る）
code, page, _ = post(f"/toy/{G}/talk", {"scene": "craft", "hypothesis": GS, "sheet_version": "1", "step": "3", "text": CRAFT_NOJS})
assert code == 200 and "残しました" in page and f'href="/toy/{G}/tsukuru?h={GS}&amp;v=1&amp;n=3"' in page, page[-600:]

# ---- 記録を残す: 同じ画面で話した工夫（同じ紙の物）と考え（同じ仮説か、仮説を選ばなかった物）が、その記録に入る
assert talk_log.talks(G, shared_only=True) == [], "記録に入る前の字は、学ぶ人の頁が読む口に出ない"
code, body, _ = post(f"/toy/{G}/record-json", {"hypothesis": GS, "result": "動いた", "note": "", "who": W})
assert code == 201 and json.loads(body) == {"id": "R-0001", "kufu": 2, "kangae": 2}, body
RID = "R-0001"
ku = talk_log.kufu(G, RID)
# 並びは、考え → 作りながら（手順の順）。同じ分の中の順は決まらないので、考えは集まりで見る。記録に入った字は、ほかの人の頁に出す印が付く
assert {(k["when"], k["step"], k["text"]) for k in ku[:2]} == {("idea", None, THINK), ("idea", None, THINK_FREE)}, ku
assert [(k["when"], k["step"], k["text"]) for k in ku[2:]] == [("making", 2, CRAFT), ("making", None, CRAFT_QUIET)] and all(k["share"] for k in ku), ku
# 同じ画面で次の記録を残しても、前の記録に入った字は動かない（別の仮説の考えは、この紙の記録に入らない）。印の無い画面の記録には、何も入らない
code, body, _ = post(f"/toy/{G}/record-json", {"hypothesis": GS, "result": "動いた", "who": W})
assert code == 201 and json.loads(body) == {"id": "R-0002"}, body
code, body, _ = post(f"/toy/{G}/record-json", {"hypothesis": GS, "result": "動かない"})
assert code == 201 and json.loads(body) == {"id": "R-0003"}, body
assert talk_log.kufu(G, "R-0002") == [] and talk_log.kufu(G, "R-0003") == [] and talk_log.kufu(G, RID) == ku
# 玩具の頁の記録の欄（JS が無くても送れるフォーム）から残した時も、同じに入る。別の机の工夫は、その机の記録に入る
assert post(f"/toy/{G}/record", {"hypothesis": GS, "result": "動いた", "who": W2})[0] == 303
assert talk_log.kufu(G, "R-0004") == [{"when": "making", "step": 1, "text": CRAFT_OTHER, "share": True}], talk_log.kufu(G, "R-0004")
# 記録の欄に書いた直した点（部品・変えた事・結果）を持つ記録。話した字とは別に残り、記録の札では同じ節に並ぶ
rid5, failures = records.add({"source_id": G, "hypothesis_id": GS, "sheet_version": 1, "result": "動いた",
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
assert code == 200 and hanasu.KEPT in page and f'href="/toy/{G}/techo/kiroku#mine">手帖をひらく（作りながら聞く・上げる）</a>' in page, page[-500:]
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
# 空の字は、前は「聞き取れませんでした。…」（NOHEARD）だった。声を聞かなくなったので、受け口の断りの字（REFUSED）
assert code == 422 and j["why"] == hanasu.REFUSED and not hasattr(hanasu, "NOHEARD"), j
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
assert by_text[THINK] | {"at": ""} == {"source_id": G, "hypothesis_id": GS, "sheet_version": 1, "template": "slider_fan", "sheet_set": by_text[THINK]["sheet_set"],
                                         "scene": "think", "step": None, "record_id": RID, "text": THINK, "via": "voice", "share": True, "who": "abcdefghij", "at": ""}
assert by_text[THINK]["sheet_set"], "刷った組が空（エンジンの束と結べない）"
assert by_text["糸で引く所が気になる"]["hypothesis_id"] is None and by_text["糸で引く所が気になる"]["via"] == "text"
assert by_text[CRAFT] | {"at": "", "sheet_set": ""} == {"source_id": G, "hypothesis_id": GS, "sheet_version": 1, "template": "slider_fan", "sheet_set": "", "scene": "craft",
                                                       "step": 2, "record_id": RID, "text": CRAFT, "via": "voice", "share": True, "who": W, "at": ""}
assert by_text[CRAFT_QUIET]["step"] is None and by_text[CRAFT_QUIET]["record_id"] == RID and by_text[CRAFT_QUIET]["share"] is True
assert by_text[CRAFT_OTHER]["record_id"] == "R-0004" and by_text[CRAFT_OTHER]["who"] == W2 and by_text[CRAFT_OTHER]["share"] is True
# 形の外の印は残さない。印の無い工夫は、どの記録にも入らない
assert by_text[CRAFT_NOWHO]["who"] == "" and by_text[CRAFT_NOWHO]["step"] == 3 and by_text[CRAFT_NOWHO]["record_id"] is None and by_text[CRAFT_NOJS]["record_id"] is None
# 考え: 同じ仮説の物と、仮説を選ばなかった物は記録に入る。別の仮説の物と、印の無い物は入らない
assert by_text[THINK_FREE]["record_id"] == RID and by_text[THINK_FREE]["hypothesis_id"] is None and by_text[THINK_FREE]["share"] is True
assert by_text[THINK_OTHER]["record_id"] is None and by_text[THINK_OTHER]["share"] is False and by_text["糸で引く所が気になる"]["record_id"] is None
assert by_text[CRAFT_NOWHO]["share"] is False, "記録に入っていない字には、出す印が付かない"
assert by_text[KEEP_A]["record_id"] == RID and by_text[KEEP_A]["share"] is True and by_text[KEEP_A]["hypothesis_id"] == GS
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
assert {(t["step"], t["text"]) for t in talk_log.texts(G, scene="craft", hypothesis_id=GS, sheet_version=1)} == {(2, CRAFT), (None, CRAFT_QUIET), (1, CRAFT_OTHER), (3, CRAFT_NOWHO), (3, CRAFT_NOJS)}
assert talk_log.texts(G, scene="craft", sheet_version=2) == [] and {t["text"] for t in talk_log.texts(G, record_id=RID)} == OPEN
assert {t["text"] for t in talk_log.texts(G, scene="keep")} == {KEEP_A, KEEP_B} and {t["record_id"] for t in talk_log.texts(G, scene="keep")} == {RID}
# その画面で話した字だけ（その場限りの印で絞る。形の外の印では何も返さない）
assert {t["text"] for t in talk_log.texts(G, scene="think", who=W)} == {THINK, THINK_OTHER, THINK_FREE} and {t["text"] for t in talk_log.texts(G, who=W2)} == {CRAFT_OTHER}
assert talk_log.texts(G, who="") == [] and talk_log.texts(G, who="Tanaka Taro!") == []
one = next(t for t in every if t["text"] == CRAFT)
assert one == {"source_id": G, "hypothesis_id": GS, "sheet_version": 1, "template": "slider_fan", "sheet_set": one["sheet_set"], "scene": "craft", "step": 2,
               "record_id": RID, "text": CRAFT, "at": one["at"]} and one["sheet_set"] and re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d\+09:00", one["at"])
sm = talk_log.summary(G)
assert {t["text"] for t in sm["think"]} == {THINK, "糸で引く所が気になる", THINK_OTHER, THINK_FREE}
assert sm["craft"][GS][1][1] == [CRAFT_OTHER] and sm["craft"][GS][1][2] == [CRAFT] and set(sm["craft"][GS][1][3]) == {CRAFT_NOWHO, CRAFT_NOJS}, sm["craft"]
assert list(sm["craft"][GS][1]) == [1, 2, 3, None] and sm["craft"][GS][1][None] == [CRAFT_QUIET], sm["craft"]
assert [(r["record_id"], r["hypothesis_id"], r["sheet_version"], len(r["kufu"])) for r in sm["records"]] == [(RID, GS, 1, 6), ("R-0004", GS, 1, 1)], sm["records"]
assert sm["via"] == {"voice": 3, "text": 8} and sm["dropped"] == {"pii": 2, "name": 1}, sm

# ---- 頁: 口は作りながら見る頁の工夫の口と、記録の札の足す口。録る釦は工夫の口にあり、記録の札の足す口には無い。字の欄の下の 1 行は口ごとに。
# 玩具の頁の 考えを話す の口は外した（本人の言葉 11-08「つくるの「考えを話す」は無くす。」・#709）ので、玩具の頁に話す口・送り先・録る釦・断り・台本が無い
REC = '<button type="button" class="hanasu-rec" aria-pressed="false"><span class="rec-go">声を録る</span><span class="rec-stop">止める</span></button>'
KB = '<p class="meta hanasu-kb">キーボードのマイクで話して入れられます。</p>'
HEAD = "<script>(()=>{\nconst M={norec:"  # 話す口の台本の頭（頁に 1 回だけ置く）
code, toy = get(f"/toy/{G}")
assert code == 200 and 'id="hanasu"' not in toy and f'action="/toy/{G}/talk' not in toy and 'name="scene" value="think"' not in toy and REC not in toy and KB not in toy
assert hanasu.NOTICE not in toy and "data-hanasu" not in toy and HEAD not in toy
code, tsu = get(f"/toy/{G}/tsukuru?h={GS}&n=2")
assert code == 200 and 'name="scene" value="craft"' in tsu and 'name="step" value="2"' in tsu and 'name="sheet_version" value="1"' in tsu and REC in tsu and KB in tsu
assert hanasu.NOTICE in tsu and tsu.count(HEAD) == 1
assert f'data-hanasu data-sid="{G}" data-scene="craft"' in tsu, "録る区切りに玩具の印と場面を添える（台本が読む）"
# 手帖の記録の札は記録の頁にある（作る頁は 1 手 1 画面にして、記録の番号を出さない。本人の決定 11-05、#87）
code, techo = get(f"/toy/{G}/techo/kiroku")
assert code == 200 and f'name="record" value="{RID}"' in techo
keep_form = techo[techo.index(f'name="record" value="{RID}"'):techo.index("</form>", techo.index(f'name="record" value="{RID}"'))]
assert KB in keep_form and "hanasu-rec" not in keep_form, "記録の札の足す口は字の欄と端末のマイクだけ（録る釦を置かない・設計の 2 版の止め 1）"
keep_boxes = [b for b in techo.split('<div class="hanasu" data-hanasu')[1:] if 'data-scene="keep"' in b[:120]]
assert keep_boxes and all("hanasu-rec" not in b.split("</div>")[0] + b.split("</form>")[0] for b in keep_boxes), "どの足す口にも録る釦が無い"
assert techo.count('data-scene="keep"') == len(keep_boxes) and "hanasu-mic" not in toy + tsu + techo, "前の「話す」の釦は無い"
# 釦に hidden 属性を付けない。指で触る機器の床（skin.TAP_FLOOR の [hidden]{display:none!important}）が CSS の出し分けに勝って、幅 1100 以下で釦が消えた事がある。
# 画面の結果は tests/test_mic_seen.py が測る（Chrome が無い機械では測れないので、原因の形をここでも字で見る）
assert re.search(r'<button[^>]*class="hanasu-rec"[^>]*\bhidden\b', toy + tsu + techo) is None
assert ".hanasu-rec .rec-stop,.hanasu-rec[aria-pressed=true] .rec-go{display:none}" in hanasu.STYLE and ".hanasu-rec[aria-pressed=true] .rec-stop{display:inline}" in hanasu.STYLE, \
    "録っている間だけ「止める」の字を見せる（字は 2 つとも頁にあり、英語の頁でも訳される）"
# ほかの人に見せるかの選び肢は、どの頁にも置かない（話した字は学ぶ人の頁に出さないので、選ぶ物が無い。J-034）
for page in (toy, tsu, techo):
    assert 'name="share"' not in page and 'name="sign"' not in page and "hanasu-sign" not in page and 'type="checkbox" name' not in page.split('id="mine"')[-1]
assert techo.count(HEAD) == 1, "手帖には部品が何個あっても、動きは 1 回だけ置く"
assert techo.index(f'name="record" value="{RID}"') < techo.index("</div></section>") and techo.rindex(HEAD) > techo.rindex('id="mine"')

# ---- 見せる範囲（本人の決定 11-06、J-034）: 話した字は、記録に入っていても、学ぶ人の頁に出ない。頁に出す字は AI が整理した字だけで、
# その置き場はまだ無い。記録の札の「工夫した所（直した所）」には、記録の欄に書いた直した点だけが出る
code, gallery = get("/gallery")
for page in (toy, tsu, techo, gallery):
    for text in OPEN | {"糸で引く所が気になる", THINK_OTHER, CRAFT_OTHER, CRAFT_NOWHO, CRAFT_NOJS}:
        assert text not in page, text
# 話した字が結んである記録（RID と、ほかの机の R-0004）の札に、節を出さない。記録の欄の直した点がある記録にだけ、節が 1 つ出る
assert f'data-kufu="{RID}"' not in techo and 'data-kufu="R-0004"' not in techo and "手順 2: " not in techo
assert techo.count('class="hanasu-kufu"') == 1 and f'data-kufu="{rid5}"><p class="hanasu-kufu-head">工夫した所（直した所）</p><ul><li>外筒 / 太く巻いた / 内筒が入りやすくなった</li></ul></div>' in techo
# 字は消していない: 記録に結んだまま、輪の材料と作る側の頁が読む（下の作る側の頁の節が見る）
assert {k["text"] for k in talk_log.kufu(G, RID, shared_only=True)} == OPEN and [k["text"] for k in talk_log.kufu(G, "R-0004", shared_only=True)] == [CRAFT_OTHER]

# ---- 作る側の頁: 場面ごとに並ぶ。落とした文は無く、数だけ。順位と点の形が無い
code, loop_page = get(f"/loop/{G}")
assert code == 200 and "7 話した事" in loop_page
for text in (THINK, THINK_OTHER, THINK_FREE, CRAFT, KEEP_A, KEEP_B):
    assert text in loop_page, text
for text in (CRAFT_QUIET, CRAFT_OTHER, CRAFT_NOWHO, CRAFT_NOJS):
    assert text in loop_page, text
assert f"{GL}の紙・版 1・手順 2" in loop_page and "連絡先の形 2 件・名乗りや学校の形 1 件" in loop_page
# 記録ごとの「工夫した所（直した所）」: 作りながら話した物（手順の番号）と、上げた後の物。見せてよいの印は、選んだ物にだけ
assert f"<h4>{RID}（{GL}の紙・版 1）</h4>" in loop_page and f"<h4>R-0004（{GL}の紙・版 1）</h4>" in loop_page and "<h4>R-0002" not in loop_page
assert f"<li>考え: {THINK}</li>" in loop_page and f"<li>手順 2: {CRAFT}</li>" in loop_page and f"<li>作りながら: {CRAFT_QUIET}</li>" in loop_page
assert f"<li>上げた後: {KEEP_A}</li>" in loop_page and f"<li>手順 1: {CRAFT_OTHER}</li>" in loop_page and "［隠している］</li>" not in loop_page
# 前の「声から字にした物 n 件・字で書いた物 n 件」は外した（声を字にしなくなった）。前の記録の via は talk_log に残る（上の sm["via"]）
assert "声から字にした物" not in loop_page and "字で書いた物" not in loop_page
part = loop_page[loop_page.index("7 話した事"):]
for word in ("090-1234", "緑町", "田中", "位", "点数", "％", "ランキング"):
    assert word not in part, word

# ---- 頁の code: マイクを開く・録る・声を送る・声を字にする物が無い
for word in ("getUserMedia", "MediaRecorder", "AudioContext", "createMediaStreamSource", "captureStream", "audio:true", "audio: true", "srcObject",
             "toBlob", "toDataURL", "FileReader", "Blob(", "WebSocket", "sendBeacon", "XMLHttpRequest", "EventSource", "RTCPeerConnection",
             "SpeechRecognition", "processLocally", "speechSynthesis"):
    assert word not in hanasu.SCRIPT and word not in hanasu.STYLE, word
assert not hasattr(hanasu, "mode") and not hasattr(hanasu, "MODES") and "data-voice" not in toy + tsu + techo, "切り替え OMOCHAE_VOICE は無い"
# 声の区切り（本人 11-08 415・本人の答え (A)・web.clips）: 録るのは置き場の voiceStart で、呼ぶのは録る釦を押した所の 1 か所だけ。
# 止めるのは、もう一度押した所（止める）と「残す」の前（置き終えるのを待ってから送る）
from web import clips  # noqa: E402

S = hanasu.SCRIPT
assert S.count("utsushiClips.voiceStart(") == 1 and S.count("utsushiClips.voiceStop()") == 1 and "const stopRec=()=>window.utsushiClips?utsushiClips.voiceStop():Promise.resolve('none');" in S
click = S[S.index("document.addEventListener('click'"):S.index("document.addEventListener('submit'")]
assert "e.target.closest('.hanasu-rec')" in click and click.index("if(b.getAttribute('aria-pressed')==='true'){await stopRec();press(b,false);return}") < click.index("utsushiClips.voiceStart("), \
    "押した印がある時は止めるだけ（2 回目に押した時）"
assert click.index("await stopRec();\n if(!window.utsushiClips") < click.index("voiceStart("), "録り始める前に、ほかの口の録りを止める（録りは頁に 1 つ）"
submit = S[S.index("document.addEventListener('submit'"):]
assert submit.index("e.preventDefault();await stopRec();") < submit.index("fetch("), "「残す」の前に録りを止め、置き終えてから送る"
assert "fetch" not in click and "submit" not in click.replace("'submit'", ""), "録る釦の所からは送らない（送るのは「残す」の時だけ）"
assert hanasu.assets().count(clips.assets()) == 1, "置き場の台本は頁に 1 回"
for word in ("fetch(", "XMLHttpRequest", "sendBeacon", "WebSocket", "EventSource", "RTCPeerConnection", "document.cookie"):
    assert word not in clips.SCRIPT, ("置き場は外へ送らない", word)
# 送る所は 1 つで、字のフォームの形だけ。字は欄に打った字（via は text だけ）
assert S.count("fetch(") == 1 and "fetch(form.action,{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'}" in S and "b.set('via','text')" in S and "'voice'" not in S
# 残す釦を code から押す所・フォームを code から送る所が無い
SUBMIT = S.index("document.addEventListener('submit'")
assert S.index("fetch(") > SUBMIT and S.count(".hanasu-go") == 1 and S.index(".hanasu-go") > SUBMIT
for word in ("requestSubmit", "dispatchEvent", ".submit()", ".click()"):
    assert word not in S, word
# 録れない画面と 5 ついっぱいの時の 1 行は、置き場の前からの字（本人の OK 11-08）。新しい字は足さない
assert f"norec:'{clips.NO_VOICE}'" in S and f"full:'{clips.FULL}'" in S and "__" not in S

# ---- 利用者向けの文: 本人が採ったやさしい言葉の文（11-05、Issue #318）。一字でも変わったら落ちるように、ここに決定の文を書く
# 11-08: NOTICE の「このサイトは声を受け取りません。」と UPLOAD_NOTICE は、上げた動画の声を字にしてから消す形（omochae.voice_text）に合わせた案（本人の確かめ待ち）
ADOPTED = {
    # 11-08: 声を録って送る形（本人 415・「公開デモでも声も録る。」）に替えた案の、録る釦の名に合わせた字（音声認識を外す設計の 4 節の (A)）。本人の確かめ待ち
    "NOTICE": "残るのは字だけです。「声を録る」を押した間の声を録り、のこすで承認した時に受け取ります。声は字にしてから消します。残す前に、字を読んで直せます。名前・学校の名前・住所・電話番号・メールは書かないでください。残した字は、AI（Claude）が型紙をよくする案を考えるのにも使います。",
    # 本人の答え 11-08「新しい字 3 つもよい。」
    "KEYBOARD": "キーボードのマイクで話して入れられます。",
    "REC_START": "声を録る",
    "REC_STOP": "止める",
    "KEPT": "残しました。型紙や説明をよくするのに使います。",
    "BLOCKED": "名前・学校の名前・住所・電話番号・メールのような言葉が入っていたので、残しませんでした。その言葉を消して、もう一度「残す」を押してください。",
    "FAILED": "残せませんでした。インターネットにつながっているか見て、もう一度押してください。",
    "UPLOAD_NOTICE": "のせた写真と動画は、いつ・どこでとったかなどの情報を消してから残します。動画の声は、この機械の中で字にしてから消します。字にできない時も、3 日で消します。子どもの声は入れないでください。",
}
for name, text in ADOPTED.items():
    assert getattr(hanasu, name) == text, name
# 前の断り（どこで声を字にするか）と NOHEARD は外した（同じ意味の字を 2 つにしない・HOW_NONE の後半は KEYBOARD に寄せた）
for name in ("HOW_LOCAL", "HOW_BROWSER", "HOW_NONE", "NOHEARD"):
    assert not hasattr(hanasu, name), name
# 本人が採った字（一字も変えない）。話す口の断りの後に置く。断りは定数 1 か所で、話す口のある頁の全部に同じ物が出る
AI_USE = "残した字は、AI（Claude）が型紙をよくする案を考えるのにも使います。"
assert hanasu.NOTICE.endswith("書かないでください。" + AI_USE)
for page in (tsu, techo):
    assert page.count(AI_USE) == page.count('<div class="hanasu" data-hanasu') >= 1, "話す口ごとに 1 回"
    assert hanasu.NOTICE in page
# 断りと、字の欄の下の 1 行は、口のある 2 つの頁に出る（1 行は口ごとに 1 回）。口の無い玩具の頁には出ない（考えを話す の口を外した・#709）
for page in (tsu, techo):
    # 手帖の記録の頁の上の のこす の記入の節（web.nokosu）の工夫の欄にも同じ 1 行がある（話す口の形の div・class なし）
    assert ADOPTED["NOTICE"] in page and page.count(KB) == page.count('<div class="hanasu" data-hanasu') + page.count('<div data-hanasu data-sid=') >= 1
    for old in ("「話す」を押すと", "声を機械の中だけで字にできません", "キーボードのマイクのマーク"):
        assert old not in page, old
assert AI_USE not in toy and ADOPTED["NOTICE"] not in toy and KB not in toy, "口の無い玩具の頁に話す口の断りが残った"
# 場面の見出しと例・選ぶ欄・頁の頭の一文
# 玩具の頁の 考えを話す の口（見出し・例の字・頭の一文・考えの欄）は、口ごと外した（本人の言葉 11-08「つくるの「考えを話す」は無くす。」）。
# 前は仮説の段の中の小さな口（見出し h3・箱の見出し hanasu-head は出さない 11-06 の字の決めの 2）だった
assert "考えを話す" not in toy and 'placeholder="『こう動くと思う』『ここが気になる』など"' not in toy
assert '<p class="hanasu-head">工夫を話す</p>' in tsu and 'placeholder="『ここをこうしたら、うまくいった』など"' in tsu
assert '<p class="hanasu-head">工夫した所や、思った事を足す</p>' in techo
# 考えの口は、頁に出ているたたき台に結ぶ形だった（型紙は玩具ごとに 1 枚。J-032）。口を外した後も、仮説を選ぶ欄と頭の一文は戻っていない（#709）
assert "<select" not in toy.split('id="win"', 1)[0] and "どの案（仮説）" not in toy
assert "仮説は、AI が考えたためしの案です。見て思った事を、話すか書いて残してください。" not in toy
# 工夫の口も、頁に出ているたたき台と版に結ぶ（選ぶ欄を置かない）
craft_form = tsu[tsu.index('name="scene" value="craft"'):tsu.index("</form>", tsu.index('name="scene" value="craft"'))]
assert f'<input type="hidden" name="hypothesis" value="{GS}">' in craft_form and "<select" not in craft_form
# 釦は「声を録る」（録っている間は「止める」）と「残す」（口の残った作りながら見る頁で見る）。台本は釦の字を書き替えない（押した印だけを替え、CSS が字を選ぶ）
assert REC in tsu and '<button class="hanasu-go">残す</button>' in tsu and "textContent=on?" not in hanasu.SCRIPT
for said in ("聞いています。話した事が、欄に字で出ます。", "字にしました。読んで、よければ「残す」を押してください。", "この機械では字にできませんでした。字で書いてください。",
             "聞き取れませんでした。もう一度押すか、字で書いてください。", "声を字にするしくみを、この機械に入れています（はじめの 1 回だけ）…"):
    assert said not in hanasu.SCRIPT, ("聞く口の知らせは外した", said)
assert f"failed:'{ADOPTED['FAILED']}'" in hanasu.SCRIPT
# ③ で上げる時の説明文は、手帖（③ の上げる頁）の上げる節に出る。聞く口の断りの文は、この頁では使わない
code, techo_make = get(f"/toy/{G}/techo")  # 上げる説明は作る頁の最後の画面に出る（1 手 1 画面、#87）
assert code == 200 and f'<p class="meta" id="up-notice">{ADOPTED["UPLOAD_NOTICE"]}</p>' in techo_make and making_log.ASK_NOTICE not in techo_make + techo and making_log.ASK_NOTICE in tsu and making_log.ASK_NOTICE not in toy
# （聞く口の断りは、聞く口のある作りながら見る頁で見る。つくるの頁の聞く口は外した・設計の問い 4 の答え「推しのとおり。」）
# 本人の確認が済んでいない文を足していない（入れる時は、確認の後に、この一覧と一緒に直す）。節の名だけは本人の言葉のまま
assert hanasu.KUFU_HEAD == "工夫した所（直した所）" and f'<p class="hanasu-kufu-head">{hanasu.KUFU_HEAD}</p>' in techo
for word in ("に入ります", "ほかの人にも見せます", "ほかの人には見せません", "に入りました", "残しています", "公開のデモでは、文を出しません", "頁を開き直して",
             "この端末の中では", "もう一度押すと止まる）\" hidden", "この頁で残した言葉", "どの仮説についてか", "工夫した所、考えた事"):
    assert word not in toy + tsu + techo + techo_make + hanasu.SCRIPT, word
# 前の文が残っていない
# 「どこにも送りません」は、ブラウザの音声認識で聞く画面では本当でない（声がブラウザの会社に送られる事がある）。本人が決め直した文（11-05）に、この言い方は無い
for old in ("残すのは字だけです", "話す釦を押すと", "型紙と案内を直す材料にします", "ほかの人に見せてよい", "作る側だけが読みます", "どこにも送りません", "録音しないし"):
    assert old not in toy + tsu + techo + hanasu.SCRIPT, old

# ---- 合言葉なしで開いた場: 字は残せるが、人の言葉は頁に出さない（J-028。件数だけ）
open_server = serve(0, public_open=True)
threading.Thread(target=open_server.serve_forever, daemon=True).start()
open_base = f"http://127.0.0.1:{open_server.server_address[1]}"
code, open_techo = get(f"/toy/{G}/techo/kiroku", at=open_base)
assert code == 200 and not any(text in open_techo for text in OPEN | {CRAFT_OTHER}) and f'name="record" value="{RID}"' in open_techo
assert 'class="hanasu-kufu"' not in open_techo and "太く巻いた" not in open_techo
code, body, _ = post(f"/toy/{G}/talk", {"json": "1", "scene": "think", "text": "開いた場でも残せる"}, at=open_base)
assert code == 200 and json.loads(body)["kept"] is True
assert get(f"/loop/{G}", at=open_base)[0] == 404

# ---- 作る側の道具（talk_log.set_share）: 名前などに気づいた時に、その記録の字を、消さずに学ぶ人の頁から隠せる。戻せる
assert talk_log.set_share(G, RID, False) == (6, []) and talk_log.set_share(G, RID, False) == (0, [])
assert talk_log.kufu(G, RID, shared_only=True) == [] and len(talk_log.kufu(G, RID)) == 6 and {t["text"] for t in talk_log.talks(G, shared_only=True)} == {CRAFT_OTHER}
assert talk_log.texts(G, record_id=RID) == [] and not OPEN & {t["text"] for t in talk_log.texts(G)}, "作る側が隠した字は、輪と束が読む口にも出ない"
hidden = get(f"/toy/{G}/techo/kiroku")[1]
assert not any(text in hidden for text in OPEN | {CRAFT_OTHER}) and f'data-kufu="{RID}"' not in hidden, "隠しても隠さなくても、学ぶ人の頁には出ない"
assert f"<li>手順 2: {CRAFT}［隠している］</li>" in get(f"/loop/{G}")[1]
n, failures = talk_log.set_share(G, "R-0002", False)
assert n == 0 and failures and failures[0].where == "record_id"  # 話した字の無い記録
assert talk_log.set_share("NDL-1187053-R0000014-R", RID, True)[0] == 0 and talk_log.kufu(G, RID, shared_only=True) == [], "別の玩具の名では変えられない"
assert talk_log.set_share(G, RID, True) == (6, []) and f"<li>手順 2: {CRAFT}</li>" in get(f"/loop/{G}")[1] and CRAFT not in get(f"/toy/{G}/techo/kiroku")[1]

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
for hid, ver, who, text in (("H-B", 1, W3, "別の仮説の紙の工夫"), (GS, 2, W3, "別の版の紙の工夫"), (GS, 1, "qrstuvwxyz", "別の画面の工夫"), (GS, 1, W3, "同じ紙の工夫")):
    path, failures = talk_log.add(G, "craft", text, hypothesis_id=hid, sheet_version=ver, step=1, who=who)
    assert path and not failures, failures
for hid, who, text in (("H-B", W3, "別の仮説の考え"), (None, W3, "仮説を選ばない考え"), (None, "qrstuvwxyz", "別の画面の考え")):
    path, failures = talk_log.add(G, "think", text, hypothesis_id=hid, who=who)
    assert path and not failures, failures
assert talk_log.bind(TORA, "H-A", 1, W3, "R-0002") == (0, 0), "別の玩具の記録には入らない"
assert talk_log.bind(G, GS, 1, "", "R-0002") == (0, 0) and talk_log.bind(G, GS, 1, "Tanaka Taro!", "R-0002") == (0, 0), "印が無いと入らない"
assert talk_log.bind(G, GS, 1, W3, "R-0002") == (1, 1) and [k["text"] for k in talk_log.kufu(G, "R-0002")] == ["仮説を選ばない考え", "同じ紙の工夫"]
assert talk_log.bind(G, GS, 1, W3, "R-0003") == (0, 0), "1 回入った字は、次の記録に動かない"
assert talk_log.bind(G, "H-B", 1, W3, "R-0003") == (1, 1) and [k["text"] for k in talk_log.kufu(G, "R-0003")] == ["別の仮説の考え", "別の仮説の紙の工夫"]
assert talk_log.bind(G, GS, 2, W3, "R-0003") == (1, 0) and {k["text"] for k in talk_log.kufu(G, "R-0003")} == {"別の仮説の考え", "別の仮説の紙の工夫", "別の版の紙の工夫"}
assert {"別の画面の工夫", "別の画面の考え"} <= {t["text"] for t in talk_log.talks(G) if not t["record_id"]}

# ---- 出す時に、入口の床をもう一度当てる: 手で置いた字や、床を広げる前に残した字に連絡先の形があれば、学ぶ人の頁が読む口に出さない
assert len(talk_log.kufu(G, "R-0003", shared_only=True)) == 3
some = next(p for p in files() if json.loads(p.read_text(encoding="utf-8")).get("record_id") == "R-0003")
placed = some.with_name("talk-20261105-0000-deadbeef.json")
placed.write_text(json.dumps(json.loads(some.read_text(encoding="utf-8")) | {"scene": "craft", "text": "電話は 090-1111-2222 です"}, ensure_ascii=False), encoding="utf-8")
assert len(talk_log.kufu(G, "R-0003")) == 4 and len(talk_log.kufu(G, "R-0003", shared_only=True)) == 3 and len(talk_log.texts(G, record_id="R-0003")) == 3
assert "090-1111" not in "".join(t["text"] for t in talk_log.talks(G, shared_only=True)) and "090-1111" not in get(f"/toy/{G}/techo/kiroku")[1]
placed.unlink()

server.shutdown()
open_server.shutdown()
print("OK 話す口: 3 つの場面で字だけが残り、話した工夫と考えが記録に入り、入口の床・見せる範囲・採られた文・声を持たない code を確かめた")
