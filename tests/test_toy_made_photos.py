"""その玩具の作例の写真（本人が上げたワークショップの作った物の写真）の置き場（本人の言葉 11-08「つくる、虎のこれまでの復元の写真が少ない。」）。
本人の言葉 11-08「つくるは読む情報が多すぎて整理する必要を感じる。復元の記録などはすべてもちよるに統合する。」で、玩具の頁の「これまでの復元」は外し、
作例の写真は もちよる（/gallery）に出す。本物の写真は使わない（作り物の色の写真）。

見る事:
1. 作例のある 12 種の玩具（今の公開デモの置き場で作例があった物）すべてで、人が「物だけ」と確かめた作例の写真が、玩具の頁に出ず、もちよる に出る
2. 事例の写真（型紙で改善したおもちゃ 3 バージョン）は玩具の頁に出ない（もちよる の玩具の札に出る事は、もちよる の玩具ごとの札の枝の
   試験 tests/test_mochiyoru_toy_place.py が見る）
3. 人が入る写真・確かめる前の写真は、玩具の頁にも もちよる にも出ない。ワークショップ全体の写真（玩具が 1 つに決まらない）は玩具の頁に出ない
4. もちよる では小さい写しで出し、元の写真の道を並べない
"""
import io
import os
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from PIL import Image  # noqa: E402

from omochae import media_review, records  # noqa: E402
from web import sakurei, techo_site, toy  # noqa: E402
from web.play_server import sources  # noqa: E402

tmp = tempfile.mkdtemp()
G, T = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"
# 11-08 に公開デモの置き場で作例があった玩具（玩具の頁のある 12 種）
TWELVE = [G, T, "NDL-1187053-R0000006-R", "NDL-1187053-R0000007-R", "NDL-1187053-R0000014-L", "NDL-1187053-R0000016-R", "NDL-1187053-R0000019-L",
          "NDL-1187053-R0000020-R", "NDL-1187053-R0000022-L", "NDL-1187053-R0000026-L", "NDL-1187053-R0000026-L-3", "NDL-1187053-R0000029-R-2"]


def photo(name, n):
    path = os.path.join(tmp, name)
    buf = io.BytesIO()
    Image.new("RGB", (64, 48), (n * 20 % 255, 80, 160)).save(buf, "JPEG")
    with open(path, "wb") as f:
        f.write(buf.getvalue())
    return path


def minna(sid):
    """その玩具の頁（前は、この頁の これまでの復元 の節を見ていた）。本人の言葉 11-08「…復元の記録などはすべてもちよるに統合する。」で節は無い"""
    page = toy.toy_page(sid)
    assert 'id="minna"' not in page and "strip workshop" not in page, (sid, "玩具の頁に これまでの復元 が残った")
    return page


def url(rid, name):
    return f'src="/record/{rid}/media/{name}/small"'


made = {}
for i, sid in enumerate(TWELVE):
    (rid, name, _), = sakurei.add([photo(f"m{i}.jpg", i)], sid, "2026-11-07")[0]
    assert media_review.record(rid, name, "object", "確認者") == []
    made[sid] = (rid, name)
# 事例（虎の 3 バージョン）・人が入る写真・確かめる前の写真・全体の写真
(vr, vn, _), = sakurei.add([photo("v.jpg", 40)], T, "2026-11-07", kind="versions")[0]
(pr, pn, _), = sakurei.add([photo("p.jpg", 41)], T, "2026-11-07")[0]
(wr, wn, _), = sakurei.add([photo("w.jpg", 42)], T, "2026-11-07")[0]
(ar, an, _), = sakurei.add([photo("a.jpg", 43)], records.WORKSHOP_ALL, "2026-11-07")[0]
for rid, name in ((vr, vn), (ar, an)):
    assert media_review.record(rid, name, "object", "確認者") == []
assert media_review.record(pr, pn, "people", "確認者") == []

gallery = techo_site.gallery_page(list(sources()))
# 1. 12 種すべてで、玩具の頁に出ず、もちよる に出る（本人の言葉 11-08「…復元の記録などはすべてもちよるに統合する。」）
for sid, (rid, name) in made.items():
    page = minna(sid)
    assert url(rid, name) not in page and not any(url(r, n) in page for r, n in made.values()), (sid, "作例の写真が玩具の頁に残った")
    assert url(rid, name) in gallery, (sid, "作例の写真が もちよる に無い")
# 2. 事例の写真（虎の 3 バージョン）は玩具の頁に出ない（もちよる の札は tests/test_mochiyoru_toy_place.py）
tora = minna(T)
assert url(vr, vn) not in tora and url(vr, vn) not in minna(G), "事例の写真が玩具の頁に残った"
# 3. 人が入る写真・確かめる前は、どちらの頁にも出ない。全体の写真は玩具の頁に出ない（もちよる では報告の顔の写真として出る・test_sakurei_gallery）
assert pr not in tora and wr not in tora and ar not in tora and ar not in minna(G), "出してはいけない写真が玩具の頁に出た"
assert url(pr, pn) not in gallery and url(wr, wn) not in gallery, "人が入る写真か確かめる前の写真が もちよる に出た"
# 4. もちよる では小さい写しで出し、元の写真の道を並べない
assert f'/record/{made[T][0]}/media/{made[T][1]}"' not in gallery, "元の写真の道を並べた"
print("ok 作例の写真: 12 種とも玩具の頁に無く もちよる にある・事例も玩具の頁に無い・人が入る物と確かめる前の物は出ない・小さい写し")
