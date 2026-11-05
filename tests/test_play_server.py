"""使い手の画面の試験。手元の偽のブラウザで送り、輪の前半の線（予想が先・順位なし・試した後の紙は記録の後）を見る。本物の API は呼ばない。"""
import os
import re
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from web.play_server import serve  # noqa: E402

G = "NDL-1187053-R0000005-L"
server = serve(0)
port = server.server_address[1]
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{port}"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


opener = urllib.request.build_opener(NoRedirect)


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
    assert "原文の引用" in look, "引用の印を残す"
    # スマホで表紙の下が URL の帯に隠れないよう、画面の高さは svh（research/19）
    assert "100svh" in look and "whileInView" not in look and "IntersectionObserver" not in look, name
assert get("/look/none")[0] == 404
# 予想の前は仮説を見せない
body = get(f"/toy/{G}")[1].decode()
assert "仮説 A" not in body and "どう動くと思いますか" in body
# 採らなかった歌の読みは出さない
assert "怠けらじ" in body and "怠らし" not in body
# 別のサイトから・別の形で送らせない
assert post(f"/toy/{G}/predict", {"text": "x"}, origin="http://evil.example")[0] == 403
assert post(f"/toy/{G}/predict", {"text": "x"}, ctype="text/plain")[0] == 403
assert post(f"/toy/{G}/predict", {"text": " "})[0] == 422
assert post(f"/toy/{G}/print", {"hypothesis": "H-A"})[0] == 422, "予想の前は刷らない"
assert "<details><summary>予想を書き足す" not in get(f"/toy/{G}")[1].decode(), "予想の前は欄を畳まない"
code, at = where(f"/toy/{G}/predict", {"text": "筒を押すと扇が開く"})
assert code == 303 and at.endswith("#kasetsu"), at  # 予想の次の段は仮説と型紙（要件 L-04）。試した記録の欄へは行かない
body = get(f"/toy/{G}")[1].decode()
assert "筒を押すと扇が開く" in body and "仮説 A" in body
# 予想の後は札を主にし、書き足す欄と自分の仮説の欄は畳む。仮説の節は札の後ろに続く
assert re.search(r"あなたの予想.*<details><summary>予想を書き足す.*<details><summary>自分の仮説を立てる.*id=\"kasetsu\"", body, re.S), "畳んでいない"
# 順位を出さない。並びは元の記録の順
assert "rank" not in body and "順位" not in body
assert re.search(r"仮説 A.*仮説 B.*仮説 C.*仮説 D.*仮説 E", body, re.S)
# 刷る。試した後の紙は記録の前は出さず、URL を知っていても渡さない
assert post(f"/toy/{G}/print", {"hypothesis": "H-A"})[0] == 303
body = get(f"/toy/{G}")[1].decode()
# 字のリンクは画面の窓へ（本人の指示 11-05「型紙はクリックすると表示される形に」）。PDF は窓の押し釦。試した後の紙はどちらも出ない
assert "see=H-A&kind=sheet&v=1#win" in body and "see=H-A&kind=tejun&v=1#win" in body and "kind=after" not in body
assert "H-A_v1.pdf" in body and "H-A_v1_after.pdf" not in body
code, pdf = get(f"/sheet/{G}/H-A_v1.pdf")
assert code == 200 and pdf[:4] == b"%PDF"
assert get(f"/sheet/{G}/H-A_v1_after.pdf")[0] == 403
# 作っている最中の手順の質問（本人の決定 11-04）: 刷った紙についてだけ、聞かれた時に答える。仕組みは答えない
code, body = post(f"/toy/{G}/ask", {"hypothesis": "H-A", "question": "谷折りって何？"})
assert code == 200 and "手前にへこむ" in body
code, body = post(f"/toy/{G}/ask", {"hypothesis": "H-A", "question": "どういう仕組みで動くの？"})
assert code == 200 and "試して確かめる所" in body
assert post(f"/toy/{G}/ask", {"hypothesis": "H-B", "question": "谷折りって何？"})[0] == 422, "刷っていない紙には答えない"
assert get(f"/sheet/{G}/../../etc/passwd")[0] == 404
assert post(f"/toy/{G}/print", {"hypothesis": "H-Z"})[0] == 422
# 記録: 決まりの外の値は落とし、動かない記録もそのまま残す
assert post(f"/toy/{G}/record", {"hypothesis": "H-A", "result": "成功"})[0] == 422
assert post(f"/toy/{G}/record", {"hypothesis": "H-A", "result": "動かない", "opened_deg": "abc"})[0] == 422
code, at = where(f"/toy/{G}/record", {"hypothesis": "H-A", "result": "動かない", "opened_deg": "40", "opener": "紙の力", "stuck": "3 枚目の折り目"})
assert code == 303 and re.search(r"#R-\d{4}$", at), at  # 今残した記録の札に着く（#121）
body = get(f"/toy/{G}")[1].decode()
assert "H-A_v1_after.pdf" in body and get(f"/sheet/{G}/H-A_v1_after.pdf")[0] == 200
assert "仮説 A の紙・動かない・40°" in body
# 仮説の文の「正解ではありません」は本人の決定で刷る（#258）。打ち消しの文だけを外し、ほかの「正解」は今までどおり落とす
for word in ("成功", "失敗", "正解"):
    assert word not in body.replace("正解ではありません", ""), word
# 人の説明は、説明と次の思いつきの両方が要る
assert post("/record/R-0001/explain", {"text": "折りが固い", "next_idea": "", "by": "本人"})[0] == 422
assert post("/record/R-0001/explain", {"text": "折りが固い", "next_idea": "強くしごく", "by": "本人"})[0] == 303
assert "次の思いつき: 強くしごく" in get(f"/toy/{G}")[1].decode()
# 自分の仮説には型紙なしの紙を返す（本人の決定）
code, at = where(f"/toy/{G}/own", {"name": "筒を回す", "how": "ひねると紐が巻かれる", "evidence": "筒の線"})
assert code == 303 and at.endswith("#own-OWN-1"), at  # 残した仮説の札と「紙を刷る」に着く
assert re.search(r'id="own-OWN-1".*紙を刷る', get(f"/toy/{G}")[1].decode(), re.S)
assert post(f"/toy/{G}/print-own", {"id": "OWN-9"})[0] == 422
assert post(f"/toy/{G}/print-own", {"id": "OWN-1"})[0] == 303
assert "OWN-1_v1_free.pdf" in get(f"/toy/{G}")[1].decode()
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
