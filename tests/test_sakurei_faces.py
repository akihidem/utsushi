"""ワークショップの報告の顔の写真（web.sakurei.faces。本人の言葉 11-07「4 日間のワークショップで作ったおもちゃたち」）と、記録の番号の帯の端。

見る線:
1. 報告の顔の写真は、玩具の印の代わりに records.WORKSHOP_ALL を持つ作例の記録として入る（仮説なし・札は「わからない」）
2. 人が「物だけ」と確かめた物だけが faces() に小さい写しの道で並ぶ。作例の札（examples）と作例を出す日（days）には入らない
3. 事例の写真（種類 versions・loop・kufu）は玩具の札に入らず、確かめた物だけが cases と versions に並ぶ
4. ふつうの記録が R-1000 に届いたら add が断る（作例の帯 R-1001〜 と重ねない）
"""
import io
import json
import os
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from PIL import Image  # noqa: E402

from omochae import media_review, records  # noqa: E402
from web import sakurei, techo_site  # noqa: E402

G = "NDL-1187053-R0000005-L"
tmp = tempfile.mkdtemp()


def photo(name, color):
    path = os.path.join(tmp, name)
    buf = io.BytesIO()
    Image.new("RGB", (60, 40), color).save(buf, "JPEG")
    with open(path, "wb") as f:
        f.write(buf.getvalue())
    return path


assert sakurei.faces() == []
(a, an, _), (b, bn, _) = sakurei.add([photo("all-1.jpg", (9, 9, 9)), photo("all-2.jpg", (99, 9, 9))], records.WORKSHOP_ALL, "2026-11-07")[0]
(g, gn, _), = sakurei.add([photo("g.jpg", (9, 99, 9))], G, "2026-11-06")[0]
rec = next(r for r in sakurei.workshop_records() if r["id"] == a)
assert rec["source_id"] == records.WORKSHOP_ALL and rec["hypothesis_id"] is None and rec["result"] == records.UNSURE
assert records.check({**rec, "result": "動いた"}), "報告の顔の写真に動きの札を許した"
assert sakurei.toy_name(records.WORKSHOP_ALL) is None
assert sakurei.faces() == [], "人の確かめの前に出た"
for rid, name in ((a, an), (b, bn), (g, gn)):
    assert media_review.record(rid, name, "object", "確認者") == []
assert sakurei.faces() == [f"/record/{a}/media/{an}/small", f"/record/{b}/media/{bn}/small"], sakurei.faces()
assert [e["rid"] for e in sakurei.examples()] == [g], "報告の顔の写真が作例の札に入った"
assert sakurei.days() == {"1106"}, "報告の顔の写真の日が作例の日に入った"
assert media_review.revoke(b, bn) == [] and sakurei.faces() == [f"/record/{a}/media/{an}/small"], "確かめを取り消した写真が残った"
assert sakurei.set_toy(["x"], records.WORKSHOP_ALL)[1] == [("x", "仕分けの置き場に無い（取り込み済みか、名か指紋の誤り）")], "WORKSHOP_ALL を玩具として書けない"

# 事例の写真（本人の言葉で届いた物）: 種類の付いた写真は玩具の札に入らず、cases と versions で引く
T = "NDL-1187053-R0000014-R"
(v1, v1n, _), = sakurei.add([photo("g3.jpg", (1, 2, 200))], G, "2026-11-07", kind="versions")[0]
(v2, v2n, _), = sakurei.add([photo("t3.jpg", (200, 2, 1))], T, "2026-11-07", kind="versions")[0]
(k1, k1n, _), = sakurei.add([photo("kufu.jpg", (50, 50, 1))], "NDL-1187053-R0000025-R", "2026-11-07")[0]
assert sakurei.add([photo("bad.jpg", (3, 3, 3))], G, "2026-11-07", kind="other")[1], "知らない種類を受けた"
assert sakurei.versions() == {} and sakurei.cases("versions") == [], "人の確かめの前に出た"
for rid, name in ((v1, v1n), (v2, v2n), (k1, k1n)):
    assert media_review.record(rid, name, "object", "確認者") == []
assert sakurei.versions() == {G: f"/record/{v1}/media/{v1n}/small", T: f"/record/{v2}/media/{v2n}/small"}, sakurei.versions()
assert k1 in [e["rid"] for e in sakurei.examples()], "種類の無い作例が札に無い"
assert sakurei.set_kind(k1, "kufu") is None and sakurei.cases("kufu") == [{"sid": "NDL-1187053-R0000025-R", "rid": k1, "url": f"/record/{k1}/media/{k1n}/small"}]
assert [e["rid"] for e in sakurei.examples()] == [g], "事例の写真が玩具の札に入った"
assert sakurei.set_kind(k1, "nai") and sakurei.set_kind("R-0099", "kufu"), "知らない種類か作例でない記録に書いた"

# ふつうの記録の帯の端
d = records.folder()
(d / "R-1000.json").write_text(json.dumps({"id": "R-1000"}), encoding="utf-8")
got, fails = records.add({"source_id": G, "hypothesis_id": "H-A", "sheet_version": 1, "result": records.results_for(G)[0]})
assert got is None and fails and "R-1000" in fails[0].message, (got, fails)
(d / "R-1000.json").unlink()
got, fails = records.add({"source_id": G, "hypothesis_id": "H-A", "sheet_version": 1, "result": records.results_for(G)[0]})
assert fails == [] and got == "R-0001", (got, fails)
print("ok 報告の顔の写真と事例の写真: 確かめた物だけ faces・cases・versions に並ぶ・玩具の札と日に入らない・ふつうの記録は R-1000 で断る")
