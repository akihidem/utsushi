"""工作の様子の蓄積（本人の決定 11-05 朝「子供の工作の様子を蓄積して、サービス全体の改善をする。個人の情報は落とす決まりはそのまま」）。
本物の API は呼ばない（鍵が無い時の、言葉の表の答えと断りで動く）。

見る線: 聞く口の質問の文だけが残る。残る欄は決めた物だけで、誰が聞いたかを辿れる物（IP・ブラウザの名・cookie・名前）と答えの文は無い。
連絡先の形がある質問は文を残さない。集計は作る側の頁（/loop/<印>）にだけ出て、学ぶ人の頁には出ない。成績の言葉は出さない（J-025）。

Issue #119（U-45）の段取り 1〜3 で足した線: 人はその場限りの無作為の印（who。英数字 8〜12 桁。形の外は落とす）で数える。出来事に雛形の id と
刷った組を残す（エンジンの報告とつなぐ）。聞いた段（step）と、頁の段の進み（刷る・作る・記録）を残す。作る側の頁に 6 つの集計
（止まった段・動きの結果・感想の言葉・聞く口の質問・完成の様子・サイトの流れ）が数と幅で出て、上下を付ける形（順位・点・％）が無い。
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

from omochae.marks import without_premise  # noqa: E402
from omochae import hypotheses, loop, making_log, records  # noqa: E402
from web import tsukuru  # noqa: E402
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
# 連絡先の形がある質問は、文を残さない（仕組みの質問にして、鍵のある機械でも本物の API を呼ばないようにする）
assert post(f"/toy/{G}/ask", {"hypothesis": "H-A", "question": "どういう仕組みで動くの？ 電話は 090-1234-5678 です"})[0] == 200
files = sorted(making.glob("ask-*.json"))
assert len(files) == 4, [f.name for f in files]
assert all(re.fullmatch(r"ask-\d{8}-\d{4}-[0-9a-f]{8}\.json", f.name) for f in files), [f.name for f in files]  # 名前の時刻も分まで
recs = [json.loads(f.read_text(encoding="utf-8")) for f in files]
for r in recs:
    # 残る欄はちょうど決めた物だけ。IP・ブラウザの名・cookie・名前・答えの文は無い
    assert set(r) - {"dropped"} == set(making_log.FIELDS), r
    assert r["source_id"] == G and r["hypothesis_id"] == "H-A" and r["sheet_version"] == 1
    # エンジンの報告とつなぐ欄（雛形の id・刷った組）。印と段を送っていない質問は、印が空で段が無い
    assert r["template"] == "slider_fan" and r["sheet_set"] and r["who"] == "" and r["step"] is None, r
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}\+09:00", r["asked_at"]), r["asked_at"]  # 分まで
    raw = json.dumps(r, ensure_ascii=False)
    for leak in ("TestBrowser", "someone", "127.0.0.1", "手前にへこむ", "090"):
        assert leak not in raw, (leak, r)
assert sorted(r["answered_from"] for r in recs) == ["glossary", "glossary", "refuse", "refuse"], [r["answered_from"] for r in recs]
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
# 前からある鍵（意味は変えない）と、Issue #119 の 6 つの集計のために足した鍵
OLD = {"asks", "asks_dropped", "stuck", "first_moved", "what_if", "impressions", "results_by_version", "reports", "stuck_steps", "steps_done"}
NEW = {"stuck_by_version", "measures", "fixes", "words", "asks_by_step", "completion", "flow"}
assert set(sm) == OLD | NEW, set(sm) ^ (OLD | NEW)
# 同じ質問（空白と句読点の違いだけ）は 1 つに数え、多い順に並ぶ
assert sm["asks"][0][1] == 2 and making_log._same(sm["asks"][0][0]) == "谷折りって何", sm["asks"][0]
assert ("どういう仕組みで動くの？", 1) in sm["asks"] and sm["asks_dropped"] == 1
assert sm == making_log.summary(G), "並びが毎回同じ"
assert sm["stuck"] == ["3 枚目の折り目", "筒の口"] and sm["first_moved"] == ["内筒"] and sm["what_if"] == ["折りを減らす"]
assert sm["impressions"] == ["折るのは楽しかった"] and sm["reports"] == 2
assert sm["results_by_version"] == {"H-A": {1: {"動かない": 1, "動いた": 1}}}
assert making_log.asks("NDL-1187053-R0000014-R") == [] and making_log.summary("NDL-1187053-R0000014-R")["asks"] == []
assert sm["asks_by_step"] == {"H-A": {None: sm["asks"]}}, "段を送っていない質問は、その紙の段なしにまとまる"

# ---- 段取り 2: 頁の段の進み。刷る・記録（2 件）が残る。予想の段は外した（#242）。何を書いたかは写さない
assert sorted(e["stage"] for e in making_log.stages(G)) == ["print", "record", "record"]
for f in making.glob("stage-*.json"):
    r = json.loads(f.read_text(encoding="utf-8"))
    assert set(r) == set(making_log.STAGE_FIELDS), r  # IP・機器の名前・cookie・書いた中身は無い
    assert r["source_id"] == G and r["template"] == "slider_fan" and r["who"] == ""
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}\+09:00", r["at"]) and re.fullmatch(r"stage-\d{8}-\d{4}-[0-9a-f]{8}\.json", f.name)
    raw = json.dumps(r, ensure_ascii=False)
    for leak in ("TestBrowser", "someone", "127.0.0.1", "筒を持つと", "折るのは楽しかった"):
        assert leak not in raw, (leak, r)
assert making_log.add_stage(G, "win") is None, "決まりの外の段は残さない"
assert sm["flow"] == {"print": {"events": 1, "people": 0}, "make": {"events": 0, "people": 0},
                      "record": {"events": 2, "people": 0}}

# ---- 段取り 1: その場限りの印（who）は形だけ確かめて残す。聞いた段（step）は 1 以上の数だけ
A, B = "a1b2c3d4", "Zz9Yy8Xx7Ww6"
for bad in ("", "short", "x" * 13, "has space1", "名前です名前です", "a@example.com", "abc-1234", None):
    assert making_log.clean_who(bad) == "", bad
assert making_log.clean_who(A) == A and making_log.clean_who(B) == B
assert post(f"/toy/{G}/ask-json", {"hypothesis": "H-A", "question": "山折りって何？", "step": "3", "who": A})[0] == 200
assert post(f"/toy/{G}/ask", {"hypothesis": "H-A", "question": "山折りって何", "step": "3", "who": B})[0] == 200
assert post(f"/toy/{G}/ask", {"hypothesis": "H-A", "question": "糊代って何？", "step": "abc", "who": "山田 太郎"})[0] == 200
assert post(f"/toy/{G}/ask", {"hypothesis": "H-A", "question": "蛇腹って何？", "step": "0", "who": "long@example.com"})[0] == 200
by_q = {r["question"]: r for r in making_log.asks(G)}
assert by_q["山折りって何？"]["who"] == A and by_q["山折りって何？"]["step"] == 3 and by_q["山折りって何"]["who"] == B
assert by_q["糊代って何？"]["who"] == "" and by_q["糊代って何？"]["step"] is None, "形の外の印と段は残さない"
assert by_q["蛇腹って何？"]["who"] == "" and by_q["蛇腹って何？"]["step"] is None
assert "山田" not in json.dumps(making_log.asks(G), ensure_ascii=False) and "example" not in json.dumps(making_log.asks(G), ensure_ascii=False)


def step(n, event, who=""):
    return post(f"/toy/{G}/step", {"hypothesis": "H-A", "step": str(n), "event": event, "json": "1", **({"who": who} if who else {})})


# A: 開いて、2 へ進み、2 で止まって、そのままやめた。B: 開いて、2 で止まり、3 へ進んで、最後の手順でできた（組み上がりは最後の手順だけで受ける。#321）。印の無い人も 2 で止まった
last = tsukuru.count(G, "H-A")
for n, ev, w in ((1, "start", A), (1, "next", A), (2, "stuck", A), (1, "start", B), (1, "next", B), (2, "stuck", B), (2, "next", B), (last, "done", B),
                 (2, "stuck", "")):
    assert step(n, ev, w)[0] == 200, (n, ev, w)
for f in making.glob("step-*.json"):
    r = json.loads(f.read_text(encoding="utf-8"))
    assert set(r) == set(making_log.STEP_FIELDS), r
    assert r["template"] == "slider_fan" and r["sheet_set"] and r["who"] in (A, B, "")
# 動きの結果の幅・直した点・感想の言葉・最初に動くまでの分（記録の欄から。画面に欄の無い物は、記録に直に足して見る）
r3, fails = records.add({"source_id": G, "hypothesis_id": "H-A", "sheet_version": 1, "result": "動いた", "opened_deg": 40, "minutes_to_try": 20,
                         "impression": "折り目がむずかしかった", "fixes": [{"part": "扇", "change": "折りを減らした", "outcome": "前より開いた"}]})
assert r3 and not fails, fails
r4, fails = records.add({"source_id": G, "hypothesis_id": "H-A", "sheet_version": 1, "result": "動いた", "opened_deg": 90, "minutes_to_try": 40,
                         "note": "糸の所が分からなかった", "fixes": []})
assert r4 and not fails, fails
assert not loop.save_explanation(r3, "作った人", "扇が開くのが面白かった", "折りを減らす")
sm = making_log.summary(G)
# 1 止まった段: 版ごと・段ごとの札の数と、印のある人の数
assert sm["stuck_by_version"] == {"H-A": {1: {2: {"taps": 3, "people": 2}}}} and sm["stuck_steps"] == {2: 3} and sm["steps_done"] == 1
# 2 動きの結果: 見た事の数・測った値の幅・直した点
assert sm["results_by_version"] == {"H-A": {1: {"動かない": 1, "動いた": 3}}} and sm["reports"] == 4
assert sm["measures"] == {"H-A": {1: {"opened_deg": [40, 90, 2]}}}, sm["measures"]
assert sm["fixes"] == [{"record_id": r3, "hypothesis_id": "H-A", "sheet_version": 1, "part": "扇", "change": "折りを減らした", "outcome": "前より開いた"}]
# 3 感想の言葉: 分からなかった側と面白かった側（感想・メモ・説明から）
assert sm["words"] == {"hard": ["折り目がむずかしかった", "糸の所が分からなかった"], "fun": ["折るのは楽しかった", "扇が開くのが面白かった"]}, sm["words"]
# 4 聞く口の質問: 段ごとに同じ問いを束ねる。段の番号の順で、段なしは最後
by = sm["asks_by_step"]["H-A"]
assert list(by) == [3, None]
assert len(by[3]) == 1 and by[3][0][1] == 2 and making_log._same(by[3][0][0]) == "山折りって何"
assert {making_log._same(q) for q, _ in by[None]} >= {"谷折りって何", "糊代って何", "蛇腹って何"}
# 5 完成の様子: 時間の幅、動いた記録の数、途中でやめた段（印のある人だけ。A は 2 で止まったまま）
assert sm["completion"] == {"minutes": [20, 40, 2], "moved": 3, "moved_word": "動いた", "quit_steps": {"H-A": {2: 1}}, "people": 2}, sm["completion"]
# 6 サイトの流れ: 作る頁を開いた 2 人が足される（直に足した記録は、画面を通っていないので段の進みに数えない）
assert sm["flow"] == {"print": {"events": 1, "people": 0}, "make": {"events": 2, "people": 2},
                      "record": {"events": 2, "people": 0}}, sm["flow"]
assert sm == making_log.summary(G), "並びが毎回同じ"

# ---- 段取り 3: 作る側の頁。6 つの節が数と幅で出る。仮説は字だけで、名前と動かし方は出さない
code, page = get(f"/loop/{G}")
assert code == 200 and "作る側の集計" in page and "公開しない頁" in page and "上下を付ける物ではありません" in page
for i, h in enumerate(("止まった段", "動きの結果", "感想の言葉", "聞く口の質問", "完成の様子", "サイトの流れ"), 1):
    assert f'id="k{i}"' in page and f"<h2>{i} {h}</h2>" in page, h
assert "<td>仮説 A の紙</td><td>版 1</td><td>手順 2</td><td>3 回</td><td>2 人</td>" in page and "3 枚目の折り目" in page
assert "仮説 A の紙" in page and "動かない 1、動いた 3" in page and "開いた角度（度） 40〜90（2 件）" in page
assert f"{r3}（仮説 A の紙・版 1）: 扇 / 折りを減らした / 前より開いた" in page
assert "分からなかった・むずかしかった（2 件）" in page and "面白かった・楽しかった（2 件）" in page and "折るのは楽しかった" in page
assert "<h3>仮説 A の紙・手順 3</h3>" in page and "<h3>仮説 A の紙・段なし</h3>" in page and page.index("<h3>仮説 A の紙・手順 3</h3>") < page.index("<h3>仮説 A の紙・段なし</h3>")
assert f"<td>{sm['asks'][0][0]}</td><td>2 回</td>" in page
assert "連絡先の形があったので文を残さなかった質問: 1 件" in page and "090" not in page
assert "最初に動くまでの分: 20〜40 分（2 件）" in page and "「動いた」の記録: 4 件のうち 3 件" in page and "できたの札: 1 回" in page
assert "<td>仮説 A の紙</td><td>手順 2</td><td>1 人</td>" in page, "途中でやめた段"
assert "<td>作りながら見る頁を開いた</td><td>2 回</td><td>2 人</td>" in page
assert "<td>記録を残した</td><td>2 回</td><td>—</td>" in page
for h in hypotheses.load(G)["hypotheses"]:
    assert h["name"] not in page and h["how_it_moves"] not in page, h["id"]
# 上下を付ける形の言葉と記号が無い。その場限りの印そのものは頁に出さない
main = page.split("<main>")[1].split("</main>")[0]  # 頁の字だけを見る（後ろの印の script の % は字ではない）
for w in ("成功", "失敗", "正解", "点数", "順位", "％", "%", A, B):
    assert w not in without_premise(main), w
assert "順位" not in page
assert get("/loop/NDL-0000000-R0000000-L")[0] == 404
# 一覧から行ける
assert f'href="/loop/{G}"' in get("/loop")[1]
# 学ぶ人の頁には、集計も回数も出ない
toy = get(f"/toy/{G}")[1]
for w in ("聞かれた事", "2 回", "3 回", "工作の様子", "作る側の集計", "止まった人", "件のうち", "完成の様子", "サイトの流れ", "途中でやめた", A, B):
    assert w not in toy, w
print("ok: 工作の様子")
