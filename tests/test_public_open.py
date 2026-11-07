"""合言葉なしで開くデモ（本人の許可 11-05「デモサイト 2 つを他の人でも見れるように公開していいよ」）。本物の API は呼ばない。

見る線: 開いた時はトンネルの名前で合言葉なしに開ける。写真と動画は受け、合言葉付きの場と同じ線で出す: 確かめる前は上げた本人の画面だけ、
人が「物だけ」と確かめた後はギャラリーにも、「人や声」は誰にも出さない（誰でも上げられる場に、確かめていない写真を皆に見せない。J-021 の
持ち寄りの線と、子どもの写真を扱わない線）。人の書いた文と記録の番号は出さない。玩具の頁と図鑑には写真を出さない。
受ける形と出す形は本人の決定（11-06「公開のデモでも写真と動画を上げられるようにしてください」「公開の場で上げた写真は、公開の場のギャラリーにも
出します」）。前は受けず、置き場に在っても出さなかった。
置き場の合計に上限を置く。合言葉付きと同時には立たない。開いていない時は、トンネルの名前を断る。
"""
import http.client
import io
import os
import tempfile
import threading
import urllib.parse

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from PIL import Image  # noqa: E402

from omochae import hypotheses, media_review, records  # noqa: E402
from web import techo_site, techo_step, wording  # noqa: E402
from web.play_server import out_dir, serve  # noqa: E402

G = "NDL-1187053-R0000005-L"
# 御来迎のたたき台は組ごと（今の組 goraigo-v14 は H-C・記録の欄 sheet_by_set）。今の組で刷れるのはたたき台の紙だけ
GS = hypotheses.sheet_of(G)["id"]
HOST = "plain-words-here.trycloudflare" + ".com"  # 作り物の名前。門がトンネルの名前の形を落とすので、字の並びを分けて書く
# 受け口は中身が読める写真だけを受ける（#187 の床）ので、本物の小さな JPEG を作る
_photo = io.BytesIO()
Image.new("RGB", (8, 8), (200, 180, 140)).save(_photo, "JPEG")
jpeg = _photo.getvalue()

try:
    serve(0, public_key="k" * 20, public_open=True)
    raise AssertionError("合言葉付きと合言葉なしが同時に立ってしまう")
except ValueError:
    pass


# 鍵のある所では開かない（誰でも費用のかかる呼び出しができてしまう）。この試験は鍵のある機械でも同じに動くよう、鍵の有無を固定する
from api import ask  # noqa: E402

ask._key_present = lambda: True
try:
    serve(0, public_open=True)
    raise AssertionError("鍵のある所で開いてしまう")
except ValueError:
    pass
ask._key_present = lambda: False


def up(**kw):
    server = serve(0, **kw)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    port = server.server_address[1]

    jar = {}  # 1 つのブラウザとして動く（記録を残した画面の鍵の cookie を持つ。説明と字を足す口は、その画面にだけ開く）

    def call(method, path, body=None, headers=None):
        c = http.client.HTTPConnection("127.0.0.1", port, timeout=20)
        sent = {"Host": HOST, **({"Cookie": "; ".join(f"{k}={v}" for k, v in jar.items())} if jar else {}), **(headers or {})}
        c.request(method, path, body=body, headers=sent)
        r = c.getresponse()
        for line in r.headers.get_all("Set-Cookie") or []:
            name, _, value = line.split(";", 1)[0].partition("=")
            jar[name.strip()] = value.strip()
        return r.status, r.read().decode("utf-8", "replace")
    call.local = f"127.0.0.1:{port}"
    call.jar = jar
    return call


closed, opened = up(), up(public_open=True)
# 開いていないサーバは、トンネルの名前を断る
assert closed("GET", "/")[0] == 403
# 開いたサーバは、合言葉なしで入口から玩具の頁まで開く
# えらぶ は入口そのもの（本人のサイト体験レビュー 11-07 の 4）なので、/toys は入口へ送る（302）
assert opened("GET", "/")[0] == 200 and opened("GET", "/toys")[0] == 302 and opened("GET", f"/toy/{G}")[0] == 200
form = {"Content-Type": "application/x-www-form-urlencoded", "Origin": f"https://{HOST}"}
assert opened("POST", f"/toy/{G}/print", f"hypothesis={GS}", form)[0] == 303
assert opened("POST", f"/toy/{G}/record", f"hypothesis={GS}&result=%E5%8B%95%E3%81%84%E3%81%9F", form)[0] == 303
rid = records.all_records(G)[-1]["id"]
# 写真と動画は受ける（本人の決定 11-06。前はここで 403 を見ていた）。手帖の口を開け、合言葉付きの場と同じ数の字と約束の印を出す
up_media = {"Content-Type": "image/jpeg", "Origin": f"https://{HOST}"}
code, body = opened("POST", f"/record/{rid}/media", jpeg, up_media)
assert code == 201 and body == "m1.jpg", (code, body)
techo = opened("GET", f"/toy/{G}/techo")[1]
assert 'id="files" disabled' not in techo and "公開のデモでは、写真と動画は上げられません" not in techo
assert 'id="picked"' in techo and 'id="thumbs"' in techo and "3 つまで" in techo and "大人の手元だけ・顔なし・声なし" in techo
# 上げた本人の画面には出す（受け取りを確かめられるように。手帖の記録の頁と絵の道）
assert opened("GET", f"/record/{rid}/media/m1.jpg")[0] == 200
assert f"/record/{rid}/media/m1.jpg" in opened("GET", f"/toy/{G}/techo/kiroku")[1]
# 確かめる前は、本人の画面でも、玩具の頁・ギャラリー・図鑑には出さない（ギャラリーは物だけと確かめた物だけ。#242・#314）
for path in (f"/toy/{G}", "/gallery"):
    assert f"/record/{rid}/media/" not in opened("GET", path)[1], path
port = int(opened.local.split(":")[1])


def stranger(method, path, body=None, headers=None):
    """別の画面（cookie を持たないブラウザ）。同じ開いた場へ送る。"""
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=20)
    c.request(method, path, body=body, headers={"Host": HOST, **(headers or {})})
    r = c.getresponse()
    return r.status, r.read().decode("utf-8", "replace")


# 確かめる前は、別の画面に、絵の道も頁の道も出さない（確かめずに皆に見える道を作らない）
assert stranger("GET", f"/record/{rid}/media/m1.jpg")[0] == 404
for path in (f"/toy/{G}", "/gallery", f"/toy/{G}/techo/kiroku"):
    assert f"/record/{rid}/media/" not in stranger("GET", path)[1], path
# 人が「物だけ」と確かめた後は、開いた場のギャラリーにも出る（合言葉付きの場と同じ線）。札に記録の番号は出さない（J-028）。玩具の頁と図鑑は出さないまま
assert media_review.record(rid, "m1.jpg", "object", "試験の人") == []
assert stranger("GET", f"/record/{rid}/media/m1.jpg")[0] == 200
gallery = stranger("GET", "/gallery")[1]
assert f"/record/{rid}/media/m1.jpg" in gallery and wording.record_no(rid) not in gallery
assert f"#{rid}" not in gallery and f'href="/toy/{G}"' in gallery, "札の玩具の名の道にも記録の番号を入れない（玩具の頁の頭へ行く）"
# 入口（/）も同じ（作ってみた実物の写真は、開いた場では入口と玩具の頁に置かない。web.made・本人のサイト体験レビュー 11-07 の 2 の作りの時の線）
for path in ("/", f"/toy/{G}"):
    assert f"/record/{rid}/media/" not in stranger("GET", path)[1], path
# 写真の札にも、人の書いた文は出さない（文の中の名前は機械で落とせない。J-028）
assert opened("POST", f"/toy/{G}/record", f"hypothesis={GS}&result=%E5%8B%95%E3%81%84%E3%81%9F&impression=PHOTOWORDS", form)[0] == 303
worded = records.all_records(G)[-1]["id"]
assert opened("POST", f"/record/{worded}/media", jpeg, up_media)[0] == 201 and media_review.record(worded, "m1.jpg", "object", "試験の人") == []
gallery = stranger("GET", "/gallery")[1]
assert f"/record/{worded}/media/m1.jpg" in gallery and "PHOTOWORDS" not in gallery
# のこした後に着くギャラリーの「今残した 1 つ」（#480）は、開いた場では記録を残した同じ画面にも出さない。札に記録の番号と感想の字が出るため（J-028）。
# 閉じ方は 2 つ（呼ぶ側が鍵を渡さない・gallery_page が public で鍵を見ない）なので、頁と gallery_page の両方で見る
mine_view = opened("GET", "/gallery?msg=x")[1]
assert 'id="own"' not in mine_view and "PHOTOWORDS" not in mine_view and wording.record_no(worded) not in mine_view, "同じ画面にも今残した 1 つを出さない"
rec_key = opened.jar["utsushi_rec"]
assert records.mine(worded, rec_key), "対照: この鍵は今残した記録の物"
assert 'id="own"' in techo_site.gallery_page([G], rec_key=rec_key), "対照: 合言葉付きの場の形なら今残した 1 つが出る"
assert 'id="own"' not in techo_site.gallery_page([G], public=True, rec_key=rec_key), "gallery_page も開いた場では鍵を見ない"
# 「人や声」と確かめた物は、上げた本人にも、ギャラリーにも出さない
assert opened("POST", f"/toy/{G}/record", f"hypothesis={GS}&result=%E5%8B%95%E3%81%84%E3%81%9F", form)[0] == 303
voiced = records.all_records(G)[-1]["id"]
assert opened("POST", f"/record/{voiced}/media", jpeg, up_media)[0] == 201 and media_review.record(voiced, "m1.jpg", "people", "試験の人") == []
assert opened("GET", f"/record/{voiced}/media/m1.jpg")[0] == 404 and stranger("GET", f"/record/{voiced}/media/m1.jpg")[0] == 404
# 絵の道（/media/m…）を見る。上げた画面の手帖の記録の頁には、見えない物も消せるよう「取り下げる」の道（/media/withdraw）が出る
for page in (opened("GET", "/gallery")[1], stranger("GET", "/gallery")[1], opened("GET", f"/toy/{G}/techo/kiroku")[1]):
    assert f"/record/{voiced}/media/m" not in page
# 別の画面は、番号を知っていても同じ記録へ上げられない（記録の鍵と同じ出所の確かめは、開いた場でもそのまま）
assert stranger("POST", f"/record/{rid}/media", jpeg, up_media)[0] == 403
assert stranger("POST", f"/record/{rid}/media", jpeg, {**up_media, "Origin": "https://evil.example"})[0] == 403
# 1 つの記録に 3 つまで（今の数のまま）。次の記録を残すと前の記録の鍵は外れるので、新しい記録で見る
assert opened("POST", f"/toy/{G}/record", f"hypothesis={GS}&result=%E5%8B%95%E3%81%84%E3%81%9F", form)[0] == 303
three = records.all_records(G)[-1]["id"]
assert [opened("POST", f"/record/{three}/media", jpeg, up_media)[0] for _ in range(3)] == [201, 201, 201]
code, body = opened("POST", f"/record/{three}/media", jpeg, up_media)
assert code == 422 and "3 つまで" in body, (code, body)
# 置き場の合計の上限: 越える時は 507 で、本文は空（手帖は今ある字「写真か動画を上げられませんでした」を出す）。置き場に足さない
assert opened("POST", f"/toy/{G}/record", f"hypothesis={GS}&result=%E5%8B%95%E3%81%84%E3%81%9F", form)[0] == 303
full_id = records.all_records(G)[-1]["id"]
total, techo_site.PUBLIC_MEDIA_TOTAL = techo_site.PUBLIC_MEDIA_TOTAL, techo_site.media_bytes() + len(jpeg) - 1
try:
    assert opened("POST", f"/record/{full_id}/media", jpeg, up_media) == (507, ""), "合計の上限"
    assert techo_site.media_of(full_id) == []
finally:
    techo_site.PUBLIC_MEDIA_TOTAL = total
assert opened("POST", f"/record/{full_id}/media", jpeg, up_media)[0] == 201, "上限の内なら受ける"
assert "写真か動画を上げられませんでした" in techo, "断りの字は今ある字（新しい字を足さない）"
# 人の書いた文は別の人に見せない（文の中の名前は機械で落とせない。J-028）
assert opened("POST", f"/toy/{G}/record", f"hypothesis={GS}&result=%E5%8B%95%E3%81%84%E3%81%9F&impression=SECRETWORDS", form)[0] == 303
assert "SECRETWORDS" not in opened("GET", f"/toy/{G}")[1] and "SECRETWORDS" not in opened("GET", "/gallery")[1]
# 説明と次の思いつきと書いた人も同じ線（#336）。送っても断られる次の版の欄ごと出さず、札は「説明を残しました。」だけにする
said = f"hypothesis={GS}&result=%E5%8B%95%E3%81%84%E3%81%9F"
assert opened("POST", f"/toy/{G}/record", said, form)[0] == 303
told_id = records.all_records(G)[-1]["id"]
assert opened("POST", f"/record/{told_id}/explain", "text=TOLDWORDS&next_idea=NEXTWORDS&by=BYWORDS", form)[0] == 303
for path in ("/", "/toys?paper=1", "/about", "/gallery", f"/zukan/{G}/yomi", "/en", f"/en/toy/{G}", f"/toy/{G}", f"/toy/{G}/tsukuru?h={GS}&v=1", f"/toy/{G}/techo", f"/toy/{G}/techo/kiroku"):
    code, page = opened("GET", path)
    assert code == 200, (path, code)
    for word in ("TOLDWORDS", "NEXTWORDS", "BYWORDS"):
        assert word not in page, (path, word)
for path in (f"/toy/{G}", f"/toy/{G}/techo/kiroku"):
    page = opened("GET", path)[1]
    assert "説明を残しました。" in page and f"/record/{told_id}/next" not in page and 'name="interpretation"' not in page, path
# 合言葉付きの場（ここでは手元の名前で開く）では、同じ記録の説明が今までどおり読めて、次の版を作れる
local = {"Host": closed.local}
for path in (f"/toy/{G}", f"/toy/{G}/techo/kiroku"):
    page = closed("GET", path, None, local)[1]
    assert "TOLDWORDS" in page and "NEXTWORDS" in page and f"/record/{told_id}/next" in page and 'name="interpretation"' in page, path
made = closed("POST", f"/record/{told_id}/next", "interpretation=x&param=fold_count&to=24&why=x&by=x", {**local, "Content-Type": form["Content-Type"], "Origin": f"http://{closed.local}"})
assert made[0] == 303, made
# 自分の仮説の文も同じ線（#336 の続き）。頁の書く口は閉じた（#332）が、置き場に在る物を、頁にも図鑑にも紙にも出さない
own, failures = hypotheses.save_own(G, "OWNNAME", "OWNHOW", "OWNWHERE")
assert not failures, failures
oid = own["id"]
assert hypotheses.print_own(G, oid, str(out_dir(G) / f"{oid}_v1")) == 0
local_form = {**local, "Content-Type": form["Content-Type"], "Origin": f"http://{closed.local}"}
assert closed("POST", f"/toy/{G}/record", f"hypothesis={oid}&result=%E5%8B%95%E3%81%84%E3%81%9F", local_form)[0] == 303
# 合言葉付きの場では、紙も開ける（前は図鑑にも今までどおり出るかを見ていた。図鑑の頁は外した・本人の言葉 11-08）
papers = [f"/sheet/{G}/{oid}_v1_{kind}.{ext}" for kind in ("free", "after") for ext in ("pdf", "png", "svg")]
for path in papers:
    assert closed("GET", path, None, local)[0] == 200, path
for path in ("/", "/toys?paper=1", "/about", "/gallery", f"/zukan/{G}/yomi", "/en", f"/en/toy/{G}", f"/toy/{G}", f"/toy/{G}?see={oid}&kind=after&v=1", f"/toy/{G}/techo"):
    code, page = opened("GET", path)
    assert code == 200, (path, code)
    for word in ("OWNNAME", "OWNHOW", "OWNWHERE"):
        assert word not in page, (path, word)
for path in papers:
    assert opened("GET", path)[0] == 404, path
assert opened("GET", f"/toy/{G}/tsukuru?h={oid}")[0] == 303, "作りながら見る頁も、その紙では開かない"
# 別の出所からは書けない（開いていても）
assert opened("POST", f"/toy/{G}/record", "name=x", {"Content-Type": "application/x-www-form-urlencoded", "Origin": "https://evil.example"})[0] == 403
# 作る側の頁は出さない（聞いた言葉と感想の文が読める頁で、名前は機械では落とせない）。開いていない時は出る
assert opened("GET", "/loop")[0] == 404 and opened("GET", f"/loop/{G}")[0] == 404
# 次の版を採る口と AI の口は閉じる（誰でも型紙の版を変えられる形にしない・費用をかけさせない）
assert opened("POST", f"/record/{rid}/next", "interpretation=x&param=fold_count&to=24&why=x&by=x", form)[0] == 403
assert opened("POST", f"/record/{rid}/ai-interpret", "x=1", form)[0] == 403 and opened("POST", f"/record/{rid}/ai-observe", "x=1", form)[0] == 403
# 記録を書く所に、名前を書かない断りがある。玩具の頁の記録の欄は のこす へ寄せた（本人の答え 11-07 夕の Q3）ので、
# 記録の字を書くのは手帖の のこす の画面で、そこに話す口と同じ断り（hanasu.NOTICE。名前・学校の名前…は書かない）が出る
import html  # noqa: E402

from web import hanasu  # noqa: E402

assert "名前や連絡先は書かないでください" not in opened("GET", f"/toy/{G}")[1], "玩具の頁に記録の欄は無い"
assert html.escape(hanasu.NOTICE, quote=False) in opened("GET", f"/toy/{G}/techo")[1] or hanasu.NOTICE in opened("GET", f"/toy/{G}/techo")[1]
# 上げた直後の返事（窓口の決定 11-06 夜・案 A）: 手帖は上げた後に「上げました」をギャラリーへ渡す。合言葉なしの場では、確かめる前はギャラリーに
# 並ばない理由の 1 行を続ける。写真なしで残した時（記録を残しました）と、合言葉付きの場には出さない
assert f"return '{techo_site.UPLOADED}'" in techo_step.SCRIPT and "location.assign(`/gallery?msg=${encodeURIComponent(done)}" in techo_step.SCRIPT
uploaded = f"/gallery?msg={urllib.parse.quote(techo_site.UPLOADED)}"
assert techo_site.PUBLIC_UPLOADED == "写真は、人が確かめてから、みんなの所に出ます。" and techo_site.PUBLIC_UPLOADED in opened("GET", uploaded)[1]
assert techo_site.PUBLIC_UPLOADED not in opened("GET", f"/gallery?msg={urllib.parse.quote('記録を残しました')}")[1], "写真なしの返事には出さない"
assert techo_site.PUBLIC_UPLOADED not in closed("GET", uploaded, None, local)[1], "合言葉付きの場には出さない"
print("ok: 合言葉なしで開くデモ")
