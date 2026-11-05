"""作った記録が、その玩具の頁で見られる（本人の指摘 11-05「制作した記録とおもちゃのページが関連してない。同じページで見れると良いよね」）。

見る線: 記録の札に写真・感想・止まった所が出る。頁の頭の帯から記録の札へ飛べる。ギャラリーの札から玩具の頁の同じ記録へ行ける。
見本（デモ用の作り物）は札つきで、その玩具の分だけ出る。予想の前は写真も感想も見本も出さない（予想が先、F9）。本物の API は呼ばない。
"""
import os
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from omochae import records  # noqa: E402
from web import demo_samples, techo_site  # noqa: E402
from web.play_server import serve  # noqa: E402

G, T = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"
server = serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"
jpeg = b"\xff\xd8" + b"\xff\xdb\x00\x03\x00" + b"\xff\xda\x00\x02DATA" + b"\xff\xd9"


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


def post(path, data, ctype="application/x-www-form-urlencoded"):
    body = data if isinstance(data, bytes) else urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(base + path, data=body, method="POST", headers={"Content-Type": ctype, "Origin": base})
    try:
        return opener.open(req).status
    except urllib.error.HTTPError as e:
        return e.code


# 予想の前（虎）: 記録と写真が在っても、頁には在る事だけを出す
rid, failures = records.add({"source_id": T, "hypothesis_id": "H-A", "sheet_version": 1, "result": "揺れた", "impression": "首が長く揺れた", "fixes": []})
assert rid and not failures
assert techo_site.save_media(rid, "image/jpeg", jpeg)[0]
before = get(f"/toy/{T}")[1]
assert "作った記録が 1 件あります" in before and "予想を書くとこの頁で見られます" in before
assert f"/record/{rid}/media/" not in before and "首が長く揺れた" not in before and "見本の記録" not in before
# 予想の後: 頭の帯に写真、記録の札に写真と感想、見本はその玩具の分だけ
assert post(f"/toy/{T}/predict", {"text": "頭が揺れると思う"}) == 303
after = get(f"/toy/{T}")[1]
hero, rest = after.split('id="yosou"')[0], after.split('id="kiroku"')[1]
assert f'href="#{rid}"' in hero and f'/record/{rid}/media/m1.jpg' in hero
assert f'id="{rid}"' in rest and f'<img src="/record/{rid}/media/m1.jpg"' in rest and "感想: 首が長く揺れた" in rest
mine = [u for u in demo_samples.UPLOADS if u["toy"] == "張子の首振り虎"]
assert mine and rest.count('class="item is-sample"') == len(mine) and demo_samples.NOTE in rest
for u in demo_samples.UPLOADS:
    assert (u["note"] in rest) == (u["toy"] == "張子の首振り虎"), u["no"]
# 御来迎: 画面から記録して、止まった所の答えも札に出る
assert post(f"/toy/{G}/predict", {"text": "扇が開くと思う"}) == 303 and post(f"/toy/{G}/print", {"hypothesis": "H-A"}) == 303
assert post(f"/toy/{G}/record", {"hypothesis": "H-A", "result": "動かない", "stuck": "3 枚目の折り目", "impression": "折るのは楽しかった"}) == 303
page = get(f"/toy/{G}")[1]
g_rid = sorted(r["id"] for r in records.all_records(G))[-1]
assert "引っかかった所: 3 枚目の折り目" in page and "感想: 折るのは楽しかった" in page
assert post(f"/record/{g_rid}/media", jpeg, "image/jpeg") == 201
assert f'<img src="/record/{g_rid}/media/m1.jpg"' in get(f"/toy/{G}")[1]
# 聞く口の断り（J-027: 質問の文を残すので、残す事と、名前を書かないでほしい事を聞く口のすぐ下に出す）
assert "聞いた言葉は、名前や連絡先を除いて" in page and "名前は書かないでください" in page.split('id="ask"')[1].split("</form>")[0]
techo = get(f"/toy/{G}/techo")[1]
assert "声と映像は残しません" in techo and "名前は言わないでください" in techo
# ギャラリーの札から、玩具の頁の同じ記録へ
gal = get("/gallery")[1]
assert f'href="/toy/{G}#{g_rid}"' in gal and f'href="/toy/{T}#{rid}"' in gal
# 見本の無い玩具には見本を出さない
other = "NDL-1187053-R0000016-L"
assert post(f"/toy/{other}/predict", {"text": "立つと思う"}) == 303 and "見本の記録" not in get(f"/toy/{other}")[1]
for w in ("成功", "失敗", "正解", "順位"):
    assert w not in page, w
print("ok: 作った記録を玩具の頁で")
