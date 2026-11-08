"""作った記録の置き場（本人の指摘 11-05「制作した記録とおもちゃのページが関連してない。同じページで見れると良いよね」）。
本人の言葉 11-08「つくるは読む情報が多すぎて整理する必要を感じる。復元の記録などはすべてもちよるに統合する。」で、記録の札は玩具の頁から外し、
もちよる（/gallery の「他の人が作った物」）と手帖の記録の頁（/toy/<印>/techo/kiroku）に出す。

見る線: 玩具の頁に記録の札と頭の写真の帯が無い。もちよる の札に写真（小さい写しで、押すと元の写真）と感想が出る（人が確かめた後だけ）。
手帖の記録の頁に写真と止まった所が出る。見本（デモ用の作り物）は出ない。聞く口の断りは、残った聞く口（作りながら見る頁）に出る。本物の API は呼ばない。
"""
import html
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
# 本人の言葉 11-08「…復元の記録などはすべてもちよるに統合する。」: 玩具の頁には記録の札も頭の写真の帯も無い
assert f'id="{rid}"' not in after and f'href="#{rid}"' not in after and f'/record/{rid}/media/m1.jpg' not in after and 'id="minna"' not in after
# もちよる の札: 写真は小さい写し（/small）で出し、押すと元の写真を開く（元の写真は 1 枚 3.7MB ほどで、並ぶと重い・#521 と同じ線）。感想も出る
gal_t = get("/gallery")[1]
assert f'<a href="/record/{rid}/media/m1.jpg"><img src="/record/{rid}/media/m1.jpg/small"' in gal_t and "<p>首が長く揺れた</p>" in gal_t
# 見本の記録（作り物）は外した（本人の言葉 11-08「見本の記録をワークショップのデータで作成して欲しい。」）。虎の話された言葉は もちよる の虎の札に出る
assert 'class="item is-sample"' not in after and demo_samples.NOTE not in after
tora = [s for s in demo_samples.SPOKEN if s["toy"] == "張子の首振り虎"]
assert tora and all(html.escape(s["text"]) in gal_t for s in tora) and not any(html.escape(s["text"]) in after for s in tora), "虎の話された言葉が もちよる に無いか、玩具の頁に残った"
# 御来迎: 画面から記録して、止まった所の答えも札に出る
assert post(f"/toy/{G}/print", {"hypothesis": GS}) == 303
assert post(f"/toy/{G}/record", {"hypothesis": GS, "result": "動かない", "stuck": "3 枚目の折り目", "impression": "折るのは楽しかった"}) == 303
page = get(f"/toy/{G}")[1]
g_rid = sorted(r["id"] for r in records.all_records(G))[-1]
assert post(f"/record/{g_rid}/media", jpeg, "image/jpeg") == 201
assert media_review.record(g_rid, "m1.jpg", "object", "確認者") == []
# 玩具の頁には出ない（本人の言葉 11-08「…復元の記録などはすべてもちよるに統合する。」）。もちよる に感想と小さい写し（#521 と同じ線）
assert "3 枚目の折り目" not in page and "折るのは楽しかった" not in page and g_rid not in get(f"/toy/{G}")[1]
gal_g = get("/gallery")[1]
assert "<p>折るのは楽しかった</p>" in gal_g and f'<img src="/record/{g_rid}/media/m1.jpg/small"' in gal_g
# 止まった所（引っかかった所）は、もちよる の記録の札の畳み「のこした記録」に出る（前は玩具の頁の記録の札だけに出ていた・#653・統括の決め 11-08 の (ア)）
kiroku = get(f"/toy/{G}/techo/kiroku")[1]
assert f'<img src="/record/{g_rid}/media/m1.jpg/small"' in kiroku, "手帖の記録の頁に写真が無い"
# 記録を残した画面の もちよる は、その記録を「今残した」札で出す（他の人が作った物 の札は出さない）。畳み「のこした記録」は 他の人が作った物 の札に付くので、
# 鍵の無い別の画面で開いて見る
with urllib.request.urlopen(f"{base}/gallery", timeout=120) as r:
    other_gal = r.read().decode()
assert "引っかかった所: 3 枚目の折り目" in other_gal, "止まった所（引っかかった所）が、玩具の頁から外れた後、どの頁にも出ない"
# 聞く口の断り（J-027: 質問の文を残すので、残す事と、名前を出さないでほしい事を聞く口のすぐ下に出す）。玩具の頁の聞く口は外したので（本人の言葉 11-08・
# 困ったら は手帖の聞く口に任せる）、残った聞く口（作りながら見る頁）で見る。文は本人の決定（11-05、カード 20261105-092043 の 1 点目）のとおり。
# 一字でも変わったら落ちるように、ここに決定の文を書く
DECIDED = "聞いた言葉は、名前や連絡先を除いて、案内を良くするために残します。声と映像は残しません"
assert 'id="ask"' not in page and "作っている途中で困ったら" not in page, "玩具の頁に聞く口が残った"
making = get(f"/toy/{G}/tsukuru?h={GS}")[1]
ask_part = making.split('id="ask-form"')[1].split("声で聞く・写真を上げる（手帖）")[0]  # 聞く口の form から、その下の断りの 1 行まで
assert DECIDED in ask_part and "名前は言わないでください" in ask_part
# 手帖は ③ の上げる頁なので、聞く口の断りの文は使わず、③ で上げる時の説明文を出す（本人の決定 11-05、#275 の決める点 3。採られたやさしい言葉の文）。
# 一字でも変わったら落ちるように、ここに決定の文を書く。名前を言わないでほしい事は、聞く口の下に残る
UPLOAD = "のせた写真と動画は、いつ・どこでとったかなどの情報を消してから残します。動画の声は、この機械の中で字にしてから消します。字にできない時も、3 日で消します。子どもの声は入れないでください。"  # 11-08: 上げた動画の声を字にしてから消す形に合わせた案（本人の確かめ待ち）
techo = get(f"/toy/{G}/techo")[1]
assert f'<p class="meta" id="up-notice">{UPLOAD}</p>' in techo and DECIDED not in techo and "名前は言わないでください" in techo
# ギャラリーの札の玩具の名から、もちよるの中のその玩具の札（錨 toy-<印>）へ。前は玩具の頁の同じ記録（#R-…）へ行ったが、本人の言葉 11-08 477
# 「復元の記録などはすべてもちよるに統合する。」で玩具の頁から記録の札が無くなるので向け直した。行き先の錨が頁にある事も見る
gal = get("/gallery")[1]
# 今残した 1 つ（own・この試験の画面の鍵が合う記録）の玩具の名は、手帖の記録の頁の自分の記録へ（記録の番号の道と同じ行き先）
for sid in (G, T):
    assert f'href="#toy-{sid}"' in gal or f'href="/toy/{sid}/techo/kiroku#mine"' in gal, (sid, "札の玩具の名の道")
    assert f'id="toy-{sid}"' in gal, (sid, "行き先の錨")
assert f'href="/toy/{G}#{g_rid}"' not in gal and f'href="/toy/{T}#{rid}"' not in gal, "無くなる玩具の頁の記録の札へ向けない"
# 見本の無い玩具には見本を出さない
other = "NDL-1187053-R0000016-L"
assert "見本の記録" not in get(f"/toy/{other}")[1]
for w in ("成功", "失敗", "正解", "順位"):
    assert w not in without_premise(page), w
print("ok: 作った記録は もちよる と手帖の記録の頁に（玩具の頁には無い）")
