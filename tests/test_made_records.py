"""作った記録が、その玩具の頁で見られる（本人の指摘 11-05「制作した記録とおもちゃのページが関連してない。同じページで見れると良いよね」）。

見る線: 記録の札に写真・感想・止まった所が出る。頁の頭の帯から記録の札へ飛べる。ギャラリーの札から玩具の頁の同じ記録へ行ける。
見本（デモ用の作り物）は札つきで、その玩具の分だけ出る。予想の段は無いので、開いたらすぐ見える（#242）。本物の API は呼ばない。
"""
import io
import os
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from PIL import Image  # noqa: E402

from omochae.marks import without_premise  # noqa: E402
from omochae import media_review, records  # noqa: E402
from web import demo_samples, techo_site  # noqa: E402
from web.play_server import serve  # noqa: E402

G, T = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"
from omochae import hypotheses  # noqa: E402
# 御来迎のたたき台は組ごと（今の組 goraigo-v14 は H-C・記録の欄 sheet_by_set）。今の組で刷れるのはたたき台の紙だけ
GS = hypotheses.sheet_of(G)["id"]
server = serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"
# 受け口は中身が読める写真だけを受ける（#187 の床）ので、本物の小さな JPEG を作る
_photo = io.BytesIO()
Image.new("RGB", (8, 8), (200, 180, 140)).save(_photo, "JPEG")
jpeg = _photo.getvalue()


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


# 1 つのブラウザとして動く（記録を残した画面の鍵の cookie を持つ。写真の受け口は、その画面からだけ受ける）
opener = urllib.request.build_opener(NoRedirect, urllib.request.HTTPCookieProcessor())


def get(path):
    try:
        r = opener.open(base + path)
        return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def post(path, data, ctype="application/x-www-form-urlencoded"):
    body = data if isinstance(data, bytes) else urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(base + path, data=body, method="POST", headers={"Content-Type": ctype, "Origin": base})
    try:
        return opener.open(req).status
    except urllib.error.HTTPError as e:
        return e.code


# 虎: 頭の帯に写真、他の人が作った物の札に写真と感想、見本はその玩具の分だけ
rid, failures = records.add({"source_id": T, "hypothesis_id": "H-A", "sheet_version": 1, "result": "揺れた", "impression": "首が長く揺れた", "fixes": []})
assert rid and not failures
assert techo_site.save_media(rid, "image/jpeg", jpeg)[0]
assert f'/record/{rid}/media/m1.jpg' not in get(f"/toy/{T}")[1], "人の確認の前は出さない（#314）"
assert media_review.record(rid, "m1.jpg", "object", "確認者") == []
after = get(f"/toy/{T}")[1]
hero, rest = after.split('id="kasetsu"')[0], after.split('id="minna"')[1]
assert f'href="#{rid}"' in hero and f'/record/{rid}/media/m1.jpg' in hero
# 写真は小さい写し（/small）で出し、押すと元の写真を開く（元の写真は 1 枚 3.7MB ほどで、並ぶと重い・#521 と同じ線）
assert f'id="{rid}"' in rest and f'<a href="/record/{rid}/media/m1.jpg"><img src="/record/{rid}/media/m1.jpg/small"' in rest and "感想: 首が長く揺れた" in rest
mine = [u for u in demo_samples.UPLOADS if u["toy"] == "張子の首振り虎"]
assert mine and rest.count('class="item is-sample"') == len(mine) and demo_samples.NOTE in rest
for u in demo_samples.UPLOADS:
    assert (u["note"] in rest) == (u["toy"] == "張子の首振り虎"), u["no"]
# 御来迎: 画面から記録して、止まった所の答えも札に出る
assert post(f"/toy/{G}/print", {"hypothesis": GS}) == 303
assert post(f"/toy/{G}/record", {"hypothesis": GS, "result": "動かない", "stuck": "3 枚目の折り目", "impression": "折るのは楽しかった"}) == 303
page = get(f"/toy/{G}")[1]
g_rid = sorted(r["id"] for r in records.all_records(G))[-1]
assert "引っかかった所: 3 枚目の折り目" in page and "感想: 折るのは楽しかった" in page
assert post(f"/record/{g_rid}/media", jpeg, "image/jpeg") == 201
assert media_review.record(g_rid, "m1.jpg", "object", "確認者") == []
assert f'<img src="/record/{g_rid}/media/m1.jpg/small"' in get(f"/toy/{G}")[1]  # 小さい写し（#521 と同じ線）
# 聞く口の断り（J-027: 質問の文を残すので、残す事と、名前を書かないでほしい事を聞く口のすぐ下に出す）
# 文は本人の決定（11-05、カード 20261105-092043 の 1 点目）のとおり。一字でも変わったら落ちるように、ここに決定の文を書く
DECIDED = "聞いた言葉は、名前や連絡先を除いて、案内を良くするために残します。声と映像は残しません"
ask_part = page.split('id="ask"')[1].split("</form>")[0]
assert DECIDED in ask_part and "名前は書かないでください" in ask_part
# 手帖は ③ の上げる頁なので、聞く口の断りの文は使わず、③ で上げる時の説明文を出す（本人の決定 11-05、#275 の決める点 3。採られたやさしい言葉の文）。
# 一字でも変わったら落ちるように、ここに決定の文を書く。名前を言わないでほしい事は、聞く口の下に残る
UPLOAD = "声は字にかえて、声は残しません。のせた写真と動画は、いつ・どこでとったかなどの情報を消してから残します。"
techo = get(f"/toy/{G}/techo")[1]
assert f'<p class="meta" id="up-notice">{UPLOAD}</p>' in techo and DECIDED not in techo and "名前は言わないでください" in techo
# ギャラリーの札から、玩具の頁の同じ記録へ
gal = get("/gallery")[1]
assert f'href="/toy/{G}#{g_rid}"' in gal and f'href="/toy/{T}#{rid}"' in gal
# 見本の無い玩具には見本を出さない
other = "NDL-1187053-R0000016-L"
assert "見本の記録" not in get(f"/toy/{other}")[1]
for w in ("成功", "失敗", "正解", "順位"):
    assert w not in without_premise(page), w
print("ok: 作った記録を玩具の頁で")
