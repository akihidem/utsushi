"""札が字でない手置きの記録があっても、頁と集計が落ちない（#146）。

なぜ要るか: 記録は検査を通らずに手で置かれる事がある。札の欄が list や dict だと辞書の鍵にできず、改善の頁が 500 になった。
札の欄が無いと KeyError で、玩具の頁と手帖と図鑑まで開かなくなる。1 件の置き間違いで、その玩具の頁が全部読めなくなる。
字でない札は数えず、頁にも出さない。engine_bundle の読み方と同じ線（自由な値を札の欄で運ばせない）。
"""
import json
import os
import tempfile
import threading
import urllib.request

DATA = tempfile.mkdtemp()
os.environ["OMOCHAE_DATA"] = DATA
os.environ["OMOCHAE_USAGE_LEDGER"] = os.path.join(DATA, "usage.jsonl")

from omochae import engine_bundle, gallery, hypotheses, making_log, records  # noqa: E402
from web.play_server import serve  # noqa: E402

G = "NDL-1187053-R0000005-L"
MARK = "手置きの目印"
ODD = {"R-9001": [MARK], "R-9002": {MARK: 1}, "R-9003": None, "R-9004": 5, "R-9005": True}
folder = records.folder()
folder.mkdir(parents=True, exist_ok=True)


def place(rid, **more):
    rec = {"id": rid, "source_id": G, "hypothesis_id": "H-A", "sheet_version": 1, **more}
    (folder / f"{rid}.json").write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")


# 字の札は数え方を見分けるために 3 件（同じ札を 2 件、動かない側を 1 件）
place("R-9000", result="動いた")
place("R-9007", result="動いた")
place("R-9008", result="動かない")
for rid, value in ODD.items():
    place(rid, result=value, impression="手で置いた感想", tried_on="2026-11-05")  # 感想があると、作った物の頁にも出る
place("R-9006", impression="手で置いた感想", tried_on="2026-11-05")  # 札の欄が無い

# 1. 集計: 字の札だけを数える
sm = making_log.summary(G)
assert sm["results_by_version"]["H-A"][1] == {"動いた": 2, "動かない": 1}, sm["results_by_version"]
assert sm["completion"]["moved"] == 2, sm["completion"]
row = records.summarize(records.all_records(G))["H-A"]
assert row["動いた"] == 2 and row["動かない"] == 1 and len(row["record_ids"]) == 9, row  # 記録そのものは落とさない
assert not set(map(type, row)) - {str}, row

# 2. 頁: どの頁も開き、字でない札の中身を出さない
server = serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"
for path in (f"/loop/{G}", "/loop", f"/toy/{G}", f"/toy/{G}/techo", f"/zukan/{G}", "/gallery"):
    with urllib.request.urlopen(base + path) as r:
        assert r.status == 200, path
        body = r.read().decode()
    assert MARK not in body, path
    for shown in ("・None", "・5", "・True", "　None　", "　5　", "　True　"):
        assert shown not in body, (path, shown)

# 3. 公開の展示の札も同じ
data = hypotheses.load(G)
for rec in records.all_records(G):
    card = gallery.card(rec, data)
    assert MARK not in card and '<span class="res">None' not in card, rec["id"]

# 4. エンジンへ渡す束も同じ記録で落ちない
assert engine_bundle.build() is not None
print("ok")
