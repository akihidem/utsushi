"""工作の様子の蓄積（本人の決定 11-05 朝「子供の工作の様子を蓄積して、サービス全体の改善をする。個人の情報は落とす決まりはそのまま」）。
本物の API は呼ばない（鍵が無い時の、言葉の表の答えと断りで動く）。

見る線: 聞く口の質問の文だけが残る。残る欄は決めた 6 つで、誰が聞いたかを辿れる物（IP・ブラウザの名・cookie・名前）と答えの文は無い。
連絡先の形がある質問は文を残さない。集計は作る側の頁（/loop/<印>）にだけ出て、学ぶ人の頁には出ない。成績の言葉は出さない（J-025）。
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

from omochae import hypotheses, making_log  # noqa: E402
from web.play_server import serve  # noqa: E402

G = "NDL-1187053-R0000005-L"
server = serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


opener = urllib.request.build_opener(NoRedirect)


def get(path):
    try:
        r = opener.open(base + path)
        return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def post(path, data):
    # 送る側がブラウザの名と cookie を付けても、記録に入らない事を見るために付ける
    req = urllib.request.Request(base + path, data=urllib.parse.urlencode(data).encode(), method="POST",
                                 headers={"Content-Type": "application/x-www-form-urlencoded", "Origin": base,
                                          "User-Agent": "TestBrowser/1.0", "Cookie": "look=tenji; name=someone"})
    try:
        r = opener.open(req)
        return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


making = pathlib.Path(DATA) / "making"
assert post(f"/toy/{G}/predict", {"text": "筒を持つと扇が開くと思う"})[0] == 303
assert post(f"/toy/{G}/print", {"hypothesis": "H-A"})[0] == 303
# 刷っていない紙への質問は断られ、残らない。空の質問も残らない
assert post(f"/toy/{G}/ask", {"hypothesis": "H-B", "question": "谷折りって何？"})[0] == 422
assert post(f"/toy/{G}/ask", {"hypothesis": "H-A", "question": "   "})[0] == 200
assert not making.exists() or not list(making.glob("ask-*.json"))
# 玩具の頁の聞く口と、手帖の聞く口。同じ質問は空白と句読点の違いを無視して 1 つに数える
assert post(f"/toy/{G}/ask", {"hypothesis": "H-A", "question": "谷折りって何？"})[0] == 200
code, body = post(f"/toy/{G}/ask-json", {"hypothesis": "H-A", "question": "谷折り って何"})
assert code == 200 and json.loads(body)["from"] == "glossary", body
# 仕組みを聞く質問は断るが、何を聞かれたかは残す（案内を直す材料）
assert post(f"/toy/{G}/ask", {"hypothesis": "H-A", "question": "どういう仕組みで動くの？"})[0] == 200
# 連絡先の形がある質問は、文を残さない（言葉の表で答えられる質問にして、鍵のある機械でも本物の API を呼ばないようにする）
assert post(f"/toy/{G}/ask", {"hypothesis": "H-A", "question": "谷折りって何？ 電話は 090-1234-5678 です"})[0] == 200
files = sorted(making.glob("ask-*.json"))
assert len(files) == 4, [f.name for f in files]
assert all(re.fullmatch(r"ask-\d{8}-\d{4}-[0-9a-f]{8}\.json", f.name) for f in files), [f.name for f in files]  # 名前の時刻も分まで
recs = [json.loads(f.read_text(encoding="utf-8")) for f in files]
for r in recs:
    # 残る欄はちょうど決めた物だけ。IP・ブラウザの名・cookie・名前・答えの文は無い
    assert set(r) - {"dropped"} == set(making_log.FIELDS), r
    assert r["source_id"] == G and r["hypothesis_id"] == "H-A" and r["sheet_version"] == 1
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}\+09:00", r["asked_at"]), r["asked_at"]  # 分まで
    raw = json.dumps(r, ensure_ascii=False)
    for leak in ("TestBrowser", "someone", "127.0.0.1", "手前にへこむ", "090"):
        assert leak not in raw, (leak, r)
assert sorted(r["answered_from"] for r in recs) == ["glossary", "glossary", "glossary", "refuse"], [r["answered_from"] for r in recs]
dropped = [r for r in recs if r.get("dropped")]
assert len(dropped) == 1 and dropped[0]["question"] == "" and dropped[0]["dropped"] == "pii"
assert all(len(r["question"]) <= making_log.MAX_QUESTION for r in recs)
# 長い質問は 200 字まで
making_log.add_ask(G, "H-A", 1, "あ" * 500, "glossary")
assert max(len(r["question"]) for r in making_log.asks(G)) == making_log.MAX_QUESTION
# 書けなくても例外を外へ出さない（聞く口の答えを止めない）
keep = making_log.folder
making_log.folder = lambda: files[0] / "x"  # ファイルの下には作れない
assert making_log.add_ask(G, "H-A", 1, "のりはどこ？", "glossary") is None
making_log.folder = keep
# 試した記録の止まった所・最初に動いた所・感想・動きの札と合わせて集計する
assert post(f"/toy/{G}/record", {"hypothesis": "H-A", "result": "動かない", "stuck": "3 枚目の折り目", "first_moved": "内筒", "what_if": "折りを減らす",
                                 "impression": "折るのは楽しかった"})[0] == 303
assert post(f"/toy/{G}/record", {"hypothesis": "H-A", "result": "動いた", "stuck": "筒の口"})[0] == 303
sm = making_log.summary(G)
# stuck_steps・steps_done は、作りながら見る頁（観察 A）の手順の進みから（tests/test_tsukuru.py が中身を見る）
assert set(sm) == {"asks", "asks_dropped", "stuck", "first_moved", "what_if", "impressions", "results_by_version", "reports", "stuck_steps", "steps_done"}
# 同じ質問（空白と句読点の違いだけ）は 1 つに数え、多い順に並ぶ
assert sm["asks"][0][1] == 2 and making_log._same(sm["asks"][0][0]) == "谷折りって何", sm["asks"][0]
assert ("どういう仕組みで動くの？", 1) in sm["asks"] and sm["asks_dropped"] == 1
assert sm == making_log.summary(G), "並びが毎回同じ"
assert sm["stuck"] == ["3 枚目の折り目", "筒の口"] and sm["first_moved"] == ["内筒"] and sm["what_if"] == ["折りを減らす"]
assert sm["impressions"] == ["折るのは楽しかった"] and sm["reports"] == 2
assert sm["results_by_version"] == {"H-A": {1: {"動かない": 1, "動いた": 1}}}
assert making_log.asks("NDL-1187053-R0000014-R") == [] and making_log.summary("NDL-1187053-R0000014-R")["asks"] == []
# 作る側の頁: 聞かれた事（回数つき）・止まった所・感想・動きの札。仮説は字だけで、名前と動かし方は出さない
code, page = get(f"/loop/{G}")
assert code == 200 and "作る側の集計" in page and "順位ではありません" in page
assert sm["asks"][0][0] in page and "2 回" in page and "3 枚目の折り目" in page and "折るのは楽しかった" in page and "仮説 A の紙" in page
assert "連絡先の形があったので文を残さなかった質問: 1 件" in page and "090" not in page
for h in hypotheses.load(G)["hypotheses"]:
    assert h["name"] not in page and h["how_it_moves"] not in page, h["id"]
for w in ("成功", "失敗", "正解", "点数"):
    assert w not in page, w
assert "順位" not in page.replace("順位ではありません", "")
assert get("/loop/NDL-0000000-R0000000-L")[0] == 404
# 一覧から行ける
assert f'href="/loop/{G}"' in get("/loop")[1]
# 学ぶ人の頁には、集計も回数も出ない
toy = get(f"/toy/{G}")[1]
for w in ("聞かれた事", "2 回", "工作の様子", "作る側の集計"):
    assert w not in toy, w
print("ok: 工作の様子")
