"""予想の段を無くして、開いたらすぐ作る形（本人の決定 2026-11-05、#242）を試験で見る。

本人の言葉: 「予想の段を無くして、すぐ作る形にする」「他の人の作ったものギャラリーは作る」。

見る事:
- 予想を書かずに、玩具の頁に仮説の札と刷る口が出て、刷れる。手帖と作りながら見る頁も開く。
- 画面に予想の入力と「あなたの予想」が無い。予想の口は閉じている。
- 型紙は正解でなく AI が考えた仮説である事が、作る節の頭に出る。
- 他の人が作った物が、玩具の頁とギャラリーの両方で見られる。写真の無い記録も言葉で並ぶ。順位の語は無い。
- 工夫の欄が記録に残り、札とギャラリーと工作の様子に出る（本人の言葉 11-05「工夫で乗り切る過程」）。
- #208 の形（誰かの文が別の人の画面に「あなたの予想」と出る）が起きようがない。
- 合言葉なしで開いた場では、ギャラリーにも写真と人の書いた文を出さない（J-028）。
"""
import json
import os
import pathlib
import sys
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
tmp = tempfile.TemporaryDirectory()
os.environ["OMOCHAE_DATA"] = f"{tmp.name}/data"
os.environ["OMOCHAE_SAMPLES"] = "0"
os.chdir(tmp.name)

from omochae import hypotheses, making_log, media_review, records  # noqa: E402
from web.play_server import serve  # noqa: E402
from web import techo_site, toy  # noqa: E402
# ワークショップの試行の写真（web.workshop・repo に在る）は、ここが見る「本物の記録が無い時」の形を変えるので、この試験では表を空にする
# （写真が出る形は tests/test_workshop_gallery.py が見る。本人の見直し 11-07 夜の ②⑦）
from web import workshop as _workshop  # noqa: E402

_workshop.TABLE = _workshop.TABLE.with_name("no-such-workshop-photos.json")
# もちよるの頁のワークショップの様子と、できたおもちゃの節（本人の言葉 11-08）も、写真の分けの表と感想の札を外して、本物の無い形を作る
# （2 つの節が出る形は tests/test_mochiyoru_workshop.py が見る）
_workshop.KINDS = _workshop.KINDS.with_name("no-such-workshop-photo-kinds.json")
from web import demo_samples as _samples  # noqa: E402
_samples.workshop_for = lambda sid, toy: ""

G = "NDL-1187053-R0000005-L"
# 御来迎のたたき台の仮説（次の組は H-C の柄を下から押し上げる形・前の組は H-A。本人の決定 2026-11-06。hypotheses.sheet_id）
GS = hypotheses.sheet_of(G)["id"]
server = serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def get(path):
    return urllib.request.urlopen(base + path, timeout=30).read().decode("utf-8")


def post(path, form):
    req = urllib.request.Request(base + path, data=urllib.parse.urlencode(form).encode(), headers={"Origin": base, "Content-Type": "application/x-www-form-urlencoded"})
    try:
        return urllib.request.build_opener(NoRedirect).open(req, timeout=120).status
    except urllib.error.HTTPError as e:
        return e.code


page = get(f"/toy/{G}")
# すぐ作れる
# 「すぐ作る」の見出しは外し、説明の文は型紙の窓の頭へ移した（本人のサイト体験レビュー 11-07 の 3。作る節が 2 つに見えた）。錨は残る
assert 'id="kasetsu"' in page and "<h2>すぐ作る</h2>" not in page and "型紙を刷ります。切って、折って、組みます。" in page.split('id="win"', 1)[1]
# 札はたたき台の 1 枚だけ（本人の決定 11-05、J-032）
sheet = hypotheses.sheet_of(G)
assert f'value="{sheet["id"]}"' in page and sheet["name"] in page
assert not [h["id"] for h in hypotheses.load(G)["hypotheses"] if h["id"] != sheet["id"] and f'value="{h["id"]}"' in page]
# 刷る口は頭の「つくる」1 つ（本人のサイト体験レビュー 11-07 の 3。前は札の「型紙を見る」も刷る口だった）
assert f'action="/toy/{G}/print#win"' in page and f'action="/toy/{G}/print#kasetsu"' not in page
# 予想の段が無い
assert "/predict" not in page and "あなたの予想" not in page and "先に、予想を書く" not in page and "kazasu" not in page
assert post(f"/toy/{G}/predict", {"text": "x"}) == 404
assert post(f"/toy/{G}/predict-choice", {"choice": "x"}) == 404
try:
    get(f"/toy/{G}/kazasu")
    raise AssertionError("かざして選ぶ頁は外した")
except urllib.error.HTTPError as e:
    assert e.code == 404
assert not hasattr(hypotheses, "need_prediction") and not hasattr(hypotheses, "save_prediction")
# 前提の明示。頭の札が仮説の札より前にある
assert 'id="premise"' in page and "ためしの案（仮説）" in page and "正しい答えではありません" in page
assert page.index('id="premise"') < page.index('class="plates"')
# 仮説を書く欄は外した（本人の決定 11-05 18:08、J-032 の点 2）。考えは話す節で話す
assert f"/toy/{G}/own" not in page and f"/toy/{G}/talk" in page
# 手帖は予想なしで開く
assert "手帖" in get(f"/toy/{G}/techo")
# 刷れて、作りながら見る頁が開く
assert post(f"/toy/{G}/print", {"hypothesis": GS}) == 303
assert GS in get(f"/toy/{G}/tsukuru") or "作りながら" in get(f"/toy/{G}/tsukuru")
# 他の人の作った物。写真が無くても言葉で並ぶ
assert toy.MINNA_HEAD in get(f"/toy/{G}")  # 玩具の頁の見出しは「これまでの復元」（夕方のレビュー 11-07 の 6。ギャラリーの見出しは今のまま）
assert post(f"/toy/{G}/record", {"hypothesis": GS, "result": "動かない", "impression": "扇が引っかかった", "fix_part": "扇", "fix_change": "折り目を深くした", "fix_outcome": "少し開いた"}) == 303
page = get(f"/toy/{G}")
assert "工夫: 扇 / 折り目を深くした / 少し開いた" in page and "扇が引っかかった" in page
assert 'id="minna"' in page and 'id="kaizen"' not in page  # 輪の節は玩具の頁に無い（本人の答え 11-07 夕の Q5 で、玩具の頁の足の「型紙の改善の輪」は外し、作る側の様子の頁 /loop/<印> へ移した）
gallery = get("/gallery")
assert "他の人が作った物" in gallery and "扇が引っかかった" in gallery and "折り目を深くした" in gallery
for word in ("順位", "1 位", "人気", "ランキング", "予想"):
    assert word not in gallery, word
# 工作の様子にも工夫が届く（輪の材料）
fixes = making_log.summary(G, hypotheses.load(G).get("template", "slider_fan"))["fixes"] if making_log.summary.__code__.co_argcount == 2 else making_log.summary(G)["fixes"]
assert any(f["change"] == "折り目を深くした" for f in fixes)
# 「あれば」の欄なので、一部だけ書いても記録ごと落とさない（落とすと書いた全部が消える）。欠けは欠けと分かる形で残す
assert post(f"/toy/{G}/record", {"hypothesis": GS, "result": "動かない", "impression": "途中まで", "fix_change": "直した"}) == 303
partial = records.all_records(G)[-1]
assert partial["impression"] == "途中まで" and partial["fixes"] == [{"part": "書かれていない", "change": "直した", "outcome": "書かれていない"}]
# 言葉の無い記録は、ギャラリーに札だけで並ばない
rid = records.all_records(G)[-1]["id"]
assert post(f"/toy/{G}/record", {"hypothesis": GS, "result": "動いた"}) == 303
quiet = records.all_records(G)[-1]["id"]
assert rid != quiet and quiet not in get("/gallery")
# 写真を出さない場では、ギャラリーに画像の道が無い
d = techo_site.media_dir(rid)
d.mkdir(parents=True, exist_ok=True)
(d / "m1.jpg").write_bytes(b"\xff\xd8\xff")
assert f"/record/{rid}/media/" not in techo_site.gallery_page([G], photos=True), "人の確認の前は出さない（#314）"
assert media_review.record(rid, "m1.jpg", "object", "確認者") == []
assert f"/record/{rid}/media/" in techo_site.gallery_page([G], photos=True)
closed = techo_site.gallery_page([G], photos=False)
# 写真も人の書いた文も出さない（文の中の名前は機械で落とせない。J-028）
assert f"/record/{rid}/media/" not in closed and "扇が引っかかった" not in closed and "公開のデモでは" in closed
# ひとこと（note）はギャラリーに出さない
assert post(f"/toy/{G}/record", {"hypothesis": GS, "result": "動いた", "impression": "見える文", "note": "ないしょのメモ"}) == 303
shown = get("/gallery")
assert "見える文" in shown and "ないしょのメモ" not in shown
print("ok")
