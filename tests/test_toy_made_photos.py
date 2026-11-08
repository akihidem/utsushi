"""玩具の頁の「これまでの復元」に、その玩具の作例の写真（本人が上げたワークショップの作った物の写真）を出す（本人の言葉 11-08「つくる、虎のこれまでの復元の写真が少ない。」）。
前は試行の写真の表（data/workshop_photos.json）だけを読み、作例は作った物の頁の作例の節にしか出なかった。本物の写真は使わない（作り物の色の写真）。

見る事:
1. 作例のある 12 種の玩具（今の公開デモの置き場で作例があった物）すべてで、人が「物だけ」と確かめた作例の写真が、玩具の頁のこれまでの復元に出る
2. 事例の写真（型紙で改善したおもちゃ 3 バージョン・改善ループの例・参加者の工夫）も、その玩具の頁に出る
3. 人が入る写真・確かめる前の写真・ワークショップ全体の写真（玩具が 1 つに決まらない）は出ない。ほかの玩具の頁にも出ない
4. 小さい写しで出し、字は前からある alt「作った物の写真」だけ（新しい字を足さない）。試行の写真の後ろに並ぶ
"""
import io
import os
import re
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from PIL import Image  # noqa: E402

from omochae import media_review, records  # noqa: E402
from web import sakurei, toy  # noqa: E402

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
    page = toy.toy_page(sid)
    return page.split('id="minna"', 1)[1].split("</section>", 1)[0]


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

# 1. 12 種すべてで出る
for sid, (rid, name) in made.items():
    sec = minna(sid)
    assert url(rid, name) in sec, (sid, "作例の写真がこれまでの復元に出ない")
    others = [made[o] for o in TWELVE if o != sid]
    assert not any(url(r, n) in sec for r, n in others), (sid, "ほかの玩具の作例が出た")
# 2. 事例の写真も、その玩具の頁に出る
tora = minna(T)
assert url(vr, vn) in tora, "虎の 3 バージョンの写真が出ない"
assert url(vr, vn) not in minna(G)
# 3. 人が入る写真・確かめる前・全体の写真は出ない
assert pr not in tora and wr not in tora and ar not in tora and ar not in minna(G), "出してはいけない写真が出た"
# 4. 小さい写し・字は alt だけ・試行の写真の後ろ
assert f'/record/{made[T][0]}/media/{made[T][1]}"' not in tora, "元の写真の道を並べた"
strip = re.search(r'<div class="strip workshop">(.*?)</div>', tora, re.S).group(1)
assert strip.count("<img") == 3 and set(re.findall(r'alt="([^"]*)"', strip)) == {"作った物の写真"}, "虎は試行の 1 枚と作例の 2 枚（札 1・事例 1）"
assert strip.index("/workshop/") < strip.index("/record/"), "試行の写真の後ろに並ぶ"
print("ok 玩具の頁のこれまでの復元に作例の写真: 12 種・事例も・人が入る物と全体の写真は出ない・小さい写し")
