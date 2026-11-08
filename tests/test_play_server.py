"""使い手の画面の試験。手元の偽のブラウザで送り、輪の前半の線（開いたらすぐ作れる・順位なし・試した後の紙は記録の後）を見る。本物の API は呼ばない。"""
import os
import re
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from omochae import hypotheses, records  # noqa: E402
from omochae.marks import without_premise  # noqa: E402
from web.play_server import out_dir, serve  # noqa: E402

G = "NDL-1187053-R0000005-L"
# 御来迎のたたき台は組ごと（今の組 goraigo-v14 は H-C・記録の欄 sheet_by_set）。今の組で刷れるのはたたき台の紙だけ
GS = hypotheses.sheet_of(G)["id"]
server = serve(0)
port = server.server_address[1]
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{port}"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


# 1 つのブラウザとして動く（記録を残した画面の鍵の cookie を持つ。説明と字を足す口は、その画面にだけ開く）
opener = urllib.request.build_opener(NoRedirect, urllib.request.HTTPCookieProcessor())


def get(path):
    try:
        r = opener.open(base + path)
        return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def post(path, data, origin=base, ctype="application/x-www-form-urlencoded"):
    req = urllib.request.Request(base + path, data=urllib.parse.urlencode(data).encode(), method="POST", headers={"Content-Type": ctype, "Origin": origin})
    try:
        r = opener.open(req)
        return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def where(path, data):
    """送った後の戻り先を見る。(rc, Location) を返す。"""
    req = urllib.request.Request(base + path, data=urllib.parse.urlencode(data).encode(), method="POST", headers={"Content-Type": "application/x-www-form-urlencoded", "Origin": base})
    try:
        return opener.open(req).status, ""
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Location", "")


code, body = get("/")
body = body.decode()
# 入口はこのサイトの皮の入口（既定は白の展示）。玩具の一覧から入れる。大判（A）と外した 3 案は出さない（本人の決定 11-05 朝: 日本画かジン、皮ごとに 1 サイト）
assert code == 200 and "御来迎" in body and f"/toy/{G}" in body and "大判写真集" not in body
assert get("/book")[0] == 404 and get("/look/watoji")[0] == 404 and get("/look/taiban")[0] == 404
assert "冊子型" not in body and "和綴じ帖" not in body
# この皮の入口は /look/<皮> でも開く。別の皮はこのサイトには無い（切り替えは置かない）
assert get("/look/tenji")[0] == 200 and get("/look/zine")[0] == 404 and "?look=" not in body
# 残した 2 案。どれも仮説を出さず、玩具の頁へ入る。採らなかった歌の読みも出さない（黒のジンは入口の関数で見る。サーバの形は test_two_sites）
from web import looks  # noqa: E402
for name, look in (("tenji", get("/look/tenji")[1].decode()), ("zine", looks.zine())):
    assert "御来迎" in look and "/toy/" in look and "仮説 A" not in look and "怠らし" not in look, name
    # 歌の原文を出す所には引用の印。白の入口は えらぶ になり歌を出さない（本人のサイト体験レビュー 11-07 の 4。歌は玩具の頁の頭）
    assert "原文の引用" in look or name == "tenji", "引用の印を残す"
    # スマホで表紙の下が URL の帯に隠れないよう、画面の高さは svh（research/19）
    assert "100svh" in look and "whileInView" not in look and "IntersectionObserver" not in look, name
assert get("/look/none")[0] == 404
# 開いたら仮説と刷る口がすぐ見える（本人の決定 11-05、#242）
body = get(f"/toy/{G}")[1].decode()
# 刷る口は頭の「つくる」1 つ（本人のサイト体験レビュー 11-07 の 3）。札の字は今のたたき台の字で見る（#511）
# 札の字は印なしの「仮説「…」」（本人の言葉 11-08「つくる、のところ仮説Cとか仮説Aとかはなしで仮説、と表記する」）
assert hypotheses.shown_name(hypotheses.sheet_of(G)) in body and "どう動くと思いますか" not in body and f'action="/toy/{G}/print#win"' in body
# 採らなかった歌の読みは出さない。出すのは採った読み「怠らじ」（本人の決め 11-08「御来迎の歌の読みは「怠らじ」」。前は 11-04 の決め U-01 で本人の表記「怠けらじ」）
assert "怠らじ朝な夕なに" in body and "怠らし" not in body and "怠けらじ" not in body
# 別のサイトから・別の形で送らせない
assert post(f"/toy/{G}/print", {"hypothesis": GS}, origin="http://evil.example")[0] == 403
assert post(f"/toy/{G}/print", {"hypothesis": GS}, ctype="text/plain")[0] == 403
# 札を主にする。仮説を書く欄は出さない（本人の決定 11-05 18:08、J-032 の点 2）。札は仮説の節（#kasetsu-fuda）にある
# （本人の言葉 11-08 の並びで、立体の節 #kasetsu の前へ移った。前は立体の節の後の型紙の窓の中）
assert re.search(r"id=\"kasetsu-fuda\".*class=\"plates\"", body, re.S) and "自分の仮説を立てる" not in body
# 順位を出さない。並びは元の記録の順
assert "rank" not in body and "順位" not in body
assert body.count('<div class="plate">') == 1 and not re.search(r"仮説 [A-Z]", re.sub(r"<script.*?</script>", "", body, flags=re.S)), "札はたたき台の 1 枚だけ（J-032）・印は出さない"
# 刷る。試した後の紙は記録の前は出さず、URL を知っていても渡さない
assert post(f"/toy/{G}/print", {"hypothesis": GS})[0] == 303
body = get(f"/toy/{G}")[1].decode()
# 型紙は画面の窓に出る（本人の指示 11-05「型紙はクリックすると表示される形に」）。PDF は窓の押し釦。試した後の紙はどちらも出ない
# 刷るのは型紙だけ（本人の決まり 11-06）。手順の紙の札は出ない。窓の「仮説」「型紙」の切り替えの札（see=…&kind=sheet の字のリンク）は外した
# （本人の言葉 11-08「型紙の窓のところにある仮説・型紙のボタンは要らない。」）ので、窓に紙の絵が出る事で見る
assert f'<img src="/sheet/{G}/{GS}_v1.png"' in body and '<div class="tabs">' not in body and "kind=tejun" not in body and "kind=after" not in body and "_tejun.pdf" not in body
assert f"{GS}_v1.pdf" in body and f"{GS}_v1_after.pdf" not in body
code, pdf = get(f"/sheet/{G}/{GS}_v1.pdf")
assert code == 200 and pdf[:4] == b"%PDF"
assert get(f"/sheet/{G}/{GS}_v1_after.pdf")[0] == 403
# 作っている最中の手順の質問（本人の決定 11-04）: 刷った紙についてだけ、聞かれた時に答える。仕組みは答えない
code, body = post(f"/toy/{G}/ask", {"hypothesis": GS, "question": "谷折りって何？"})
assert code == 200 and "手前にへこむ" in body
code, body = post(f"/toy/{G}/ask", {"hypothesis": GS, "question": "どういう仕組みで動くの？"})
assert code == 200 and "試して確かめる所" in body
assert post(f"/toy/{G}/ask", {"hypothesis": "H-B", "question": "谷折りって何？"})[0] == 422, "刷っていない紙には答えない"
assert get(f"/sheet/{G}/../../etc/passwd")[0] == 404
assert post(f"/toy/{G}/print", {"hypothesis": "H-Z"})[0] == 422
# 記録: 決まりの外の値は落とし、動かない記録もそのまま残す
assert post(f"/toy/{G}/record", {"hypothesis": GS, "result": "成功"})[0] == 422
assert post(f"/toy/{G}/record", {"hypothesis": GS, "result": "動かない", "opened_deg": "abc"})[0] == 422
code, at = where(f"/toy/{G}/record", {"hypothesis": GS, "result": "動かない", "opened_deg": "40", "opener": "紙の力", "stuck": "3 枚目の折り目"})
# 今残した記録の札に着く（#121。つくるの頁から記録の札を外した 11-08 から、戻り先は手帖の記録の頁。#657 では並びの頭 #mine だったが、
# その札の錨 #R-… へ向けた・統括の割り振り 11-08）
rid_now = records.all_records(G)[-1]["id"]
assert code == 303 and at.endswith(f"#{rid_now}") and f"/toy/{G}/techo/kiroku" in at and "fresh=1" in at, at
body = get(f"/toy/{G}/techo/kiroku")[1].decode()
# 試した後の紙は 11-06 から刷らないので頁に道を出さない。前に配った道は記録の後に開く
assert f"{GS}_v1_after.pdf" not in body and get(f"/sheet/{G}/{GS}_v1_after.pdf")[0] == 200
# 手帖の記録の札の 1 行に、紙・結果・開いた角度（前はつくるの頁の記録の札の題「仮説の紙・動かない・40°」。紙の名は仮説の表記の直しで替わるので形で見る）
assert re.search(r"[^　<]+の紙　動かない・40°", body), "手帖の記録の札に結果と開いた角度が無い"
# 仮説の文の「正解ではありません」は本人の決定で刷る（#258）。打ち消しの文だけを外し、ほかの「正解」は今までどおり落とす
for word in ("成功", "失敗", "正解"):
    assert word not in without_premise(body), word
# 人の説明は、説明と次の思いつきの両方が要る
assert post("/record/R-0001/explain", {"text": "折りが固い", "next_idea": "", "by": "本人"})[0] == 422
assert post("/record/R-0001/explain", {"text": "折りが固い", "next_idea": "強くしごく", "by": "本人"})[0] == 303
# 説明の字は手帖の記録の頁の記録の札に出る（つくるの頁から記録の札を外した 11-08）。つくるの頁には出さない
assert "次の思いつき: 強くしごく" in get(f"/toy/{G}/techo/kiroku")[1].decode() and "強くしごく" not in get(f"/toy/{G}")[1].decode()
# 自分の仮説には型紙なしの紙を返す（本人の決定）。書く欄と刷る口は頁から外した（J-032 の点 2。tests/test_own_form_gone.py）ので、前に刷った紙の形で開く
assert post(f"/toy/{G}/own", {"name": "筒を回す", "how": "ひねると紐が巻かれる", "evidence": "筒の線"})[0] == 404
assert not hypotheses.save_own(G, "筒を回す", "ひねると紐が巻かれる", "筒の線")[1]
assert hypotheses.print_own(G, "OWN-1", str(out_dir(G) / "OWN-1_v1")) == 0
code, pdf = get(f"/sheet/{G}/OWN-1_v1_free.pdf")
assert code == 200 and pdf[:4] == b"%PDF"
# 手元の名前以外の Host は受けない
req = urllib.request.Request(base + "/", headers={"Host": "evil.example"})
try:
    opener.open(req)
    raise AssertionError("403 のはず")
except urllib.error.HTTPError as e:
    assert e.code == 403
server.shutdown()
print("ok")
