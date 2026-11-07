"""ワークショップの報告の顔の写真（web.sakurei.faces。本人の言葉 11-07「4 日間のワークショップで作ったおもちゃたち」）と、記録の番号の帯の端。

見る線:
1. 報告の顔の写真は、玩具の印の代わりに records.WORKSHOP_ALL を持つ作例の記録として入る（仮説なし・札は「わからない」）
2. 人が「物だけ」と確かめた物だけが faces() に小さい写しの道で並ぶ。作例の札（examples）と作例を出す日（days）には入らない
3. ふつうの記録が R-1000 に届いたら add が断る（作例の帯 R-1001〜 と重ねない）
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

# ふつうの記録の帯の端
d = records.folder()
(d / "R-1000.json").write_text(json.dumps({"id": "R-1000"}), encoding="utf-8")
got, fails = records.add({"source_id": G, "hypothesis_id": "H-A", "sheet_version": 1, "result": records.results_for(G)[0]})
assert got is None and fails and "R-1000" in fails[0].message, (got, fails)
(d / "R-1000.json").unlink()
got, fails = records.add({"source_id": G, "hypothesis_id": "H-A", "sheet_version": 1, "result": records.results_for(G)[0]})
assert fails == [] and got == "R-0001", (got, fails)
print("ok 報告の顔の写真: 全部の玩具の印で入る・確かめた物だけ faces に並ぶ・作例の札と日に入らない・ふつうの記録は R-1000 で断る")
