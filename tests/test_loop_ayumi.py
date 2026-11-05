"""型紙の版の歩み（本人の希望 11-06）。前の履歴・どこを良くしたか・どの知見から・共通の知見・どのループかが、裏側の改善ループの頁で見える事を見る。"""
import json
import os
import pathlib
import tempfile

data_dir = tempfile.mkdtemp()
os.environ["OMOCHAE_DATA"] = data_dir

from omochae import hypotheses, loop
from web import ayumi, kaizen

G, T = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"

# 台帳の表: 全部の行にループと知見がある
rows = ayumi.sheet_rows()
assert len(rows) >= 15 and all(r["ループ"] in ("前", "1", "2", "3", "4", "なし") and r["知見"] for r in rows), rows[0]
# 新しい版が上。前の履歴まで並ぶ
go = [r["版"] for r in ayumi.rows_for("goraigo")]
assert go[0].startswith("goraigo-v10") and go[-1] == "goraigo-v1" and "goraigo-v8" in go, go
assert [r["版"] for r in ayumi.rows_for("tora")] == ["goraigo-v10・tora-v3", "tora-v2", "tora-v1"]
assert not ayumi.rows_for("stand_figure")

# 頁: 履歴・良くした所・知見・ループ・共通の知見
page = ayumi.page()
for word in ("どこを良くしたか", "どの知見から", "その後に分かった事", "共通にしている知見", "ループ 1", "ループ 2", "ループ 3", "ループ 4", "ループの前", "エンジンの版"):
    assert word in page, word
assert "くり抜く側面の穴を切るのが大変" in page and "見た目のクオリティが低く見える" in page
assert 'id="goraigo-v9"' in page and f'id="{G}"' in page and f'id="{T}"' in page
assert "本当に良くなったかは機械では決めません" in page, "判定しない事を頭に書く"
for bad in ("点", "％", "順位", "ランキング"):
    assert f">{bad}<" not in page

# 組の直しの根拠: T-0001 の記録についた人の説明が、v8 の知見に出る
v8 = next(r for r in rows if r["版"] == "goraigo-v8")
item = ayumi._set_item(v8)
assert "人の説明 R-0001" in item and "人の説明 R-0002" in item
# ほかの版には出ない
assert "人の説明" not in ayumi._set_item(next(r for r in rows if r["版"] == "goraigo-v9"))

# 共通の知見: 入っている型は雛形のコードから数える。全部の型・一部の型・これからが分かれる
shared = ayumi.shared_block()
assert "全部の型" in shared and "虎の型" in shared and "まだ紙に入っていません" in shared
assert ayumi._has("hide_folds", "slider_fan") and not ayumi._has("hide_folds", "pivot_counterweight")
assert not ayumi._has("no_cuts", "pivot_counterweight") and ayumi._has("no_cuts", "slider_fan")
try:
    ayumi._has("知らない", "slider_fan")
    raise AssertionError("知らない見分け方を通した")
except ValueError:
    pass
# 型の並びは表の順で、数の多い順にしない（J-025）
assert list(ayumi.KINDS)[:2] == ["slider_fan", "pivot_counterweight"]

# 寸法の版: 記録から直した版が、知見とループと一緒に並ぶ。上げた後の字があるとループ 4 も数える
folder = pathlib.Path(data_dir) / "loop"
folder.mkdir(parents=True, exist_ok=True)
hid = hypotheses.sheet_of(T)["id"]
base = hypotheses.sheet_of(T).get("params") or {}
(folder / f"version-{T}-{hid}-2.json").write_text(json.dumps({"source_id": T, "hypothesis_id": hid, "version": 2, "params": {**base, "weight_g": 4.0},
    "changes": [{"param": "weight_g", "from": 3.0, "to": 4.0, "why": "頭が戻らなかったので重りを増やす"}], "record_ids": ["R-9999"], "adopted_by": "人", "proposal": "P-0001"}, ensure_ascii=False), encoding="utf-8")
got = kaizen.versions(T, hid)
assert got and got[0]["version"] == 2, got
block = ayumi.toy_block(T, hypotheses.load(T))
assert "仮説 A 版 2" in block and "頭が戻らなかったので重りを増やす" in block and "ループ 2" in block
assert block.index("仮説 A 版 2") < block.index("goraigo-v10・tora-v3"), "新しい版が上"
real = loop.maker_talk
loop.maker_talk = lambda rid: {"items": [{"when": "made", "step": None, "text": "上げた後の話"}]}
assert ayumi.loop_of(got[0]) == "2・4"
loop.maker_talk = lambda rid: {"items": [{"when": "making", "step": 3, "text": "作りながらの話"}]}
assert ayumi.loop_of(got[0]) == "2"
loop.maker_talk = real
assert ayumi.loop_of({"record_ids": ["無い記録"]}) == "2", "読めない記録で落ちない"

# エンジンの版: 読めない時は読めないと言う。案から刻んだ版はループ 3
old = os.environ.get("OMOCHAE_ENGINE_REPO")
os.environ["OMOCHAE_ENGINE_REPO"] = tempfile.mkdtemp()
assert ayumi.engine_versions() is None and "読めません" in ayumi.engine_block() and "読めません" in ayumi.loop_summary([G])["3"]
root = pathlib.Path(os.environ["OMOCHAE_ENGINE_REPO"]) / "data/engine"
root.mkdir(parents=True)
(root / "versions.json").write_text(json.dumps({"versions": [{"version": 1, "at": "2026-11-05", "proposals": [], "sheet_sets": {}, "note": "輪を足す前からの形"},
    {"version": 2, "at": "2026-11-06", "proposals": ["EP-1"], "sheet_sets": {"spinner": "spin-v2"}, "note": "風車の折り目を足した"}]}, ensure_ascii=False), encoding="utf-8")
block = ayumi.engine_block()
assert block.index("エンジンの版 2") < block.index("エンジンの版 1") and "ループ 3" in block and "ループの前" in block and "spin-v2" in block
assert "1 版" in ayumi.loop_summary([G])["3"]
if old is None:
    del os.environ["OMOCHAE_ENGINE_REPO"]
else:
    os.environ["OMOCHAE_ENGINE_REPO"] = old

# 表の形が崩れたら黙って飛ばさない
keep = ayumi.LEDGER
broken = pathlib.Path(tempfile.mkdtemp()) / "x.md"
broken.write_text("| 版 | ループ |\n|---|---|\n| a | b | c |\n", encoding="utf-8")
ayumi.LEDGER = broken
try:
    ayumi.sheet_rows()
    raise AssertionError("欄の数が合わない表を通した")
except ValueError:
    pass
ayumi.LEDGER = keep

# 道: 一覧と工作の様子から行ける。合言葉なしで開いたデモでは出さない
assert "/loop/ayumi" in kaizen.page() and f"/loop/ayumi#{G}" in kaizen.toy_page(G)
from http.client import HTTPConnection  # noqa: E402
import threading  # noqa: E402

from web import play_server  # noqa: E402

for public, want in ((False, 200), (True, 404)):
    srv = play_server.serve(0, public_open=public)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    con = HTTPConnection("127.0.0.1", srv.server_address[1], timeout=30)
    con.request("GET", "/loop/ayumi")
    got_status = con.getresponse().status
    srv.shutdown()
    assert got_status == want, (public, got_status)
print("ok")
