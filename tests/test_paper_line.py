"""用意する物の紙の行を 1 つの形にそろえる（#295）。

なぜ要るか: 紙の字が雛形ごとに 7 通りあり、g/m² と mm は家や店の紙と結びつかない。「見込み」は作る側の言葉で、
糸で動かす雛形の 18 案は「…に貼るを 1 枚」と文が崩れていた。雛形を足すたびに揺れるので、全部の案を試験で見る。
文面は本人の確認待ちの案で、下の PAPER_LINES と BOX の 4 つのほかは落とす。必須 2 種の凍結の組の字は凍結の床なので変えない。
虎は今の組 tora-v6 で 4 つの名前にしたので FROZEN から外した（前の組 tora-v3・tora-v4 は前の字のまま。5 で見る）。御来迎は次の組で外す。
"""
import json
import pathlib
import re

from omochae import ways
from omochae.compose import TEMPLATES

ROOT = pathlib.Path(__file__).resolve().parents[1]
GORAIGO, TORA = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"
FROZEN = {GORAIGO: "紙（厚さ 0.15mm 前後）を 1 枚（全部品を同じ紙に刷る）"}
TORA_OLD = "紙（厚さ 0.15mm 前後・150g/m² の見込み）を 1 枚"  # 虎の前の組（tora-v3・tora-v4）の字
PAPER_LINES = {"コピー用紙くらいの厚さの紙を 1 枚", "画用紙くらいの厚さの紙を 1 枚", "画用紙より厚い紙を 1 枚"}
BOX = "空き箱の厚紙"


def lines(tid, params):
    tpl = TEMPLATES[tid]
    return tpl.materials({**tpl.DEFAULTS, **params})


# 記録を直接読む。hypotheses.load は人が採った仮説を data/loop から重ねるので、機械ごとに数が変わる。
cases = []
for path in sorted((ROOT / "data/hypotheses").glob("*.json")):
    data = json.loads(path.read_text(encoding="utf-8"))
    cases += [(path.stem, h["id"], h.get("template") or data.get("template", "slider_fan"), h["params"]) for h in data["hypotheses"]]
assert len(cases) > 100

# 1. 必須 2 種のほかは、紙の行が案の字で、作る側の言葉と数が出ない
checked = 0
for sid, hid, tid, params in cases:
    got = lines(tid, params)
    if sid in FROZEN:
        assert got[0] == FROZEN[sid], (sid, hid, got[0])  # 凍結の床。次の組で直す
        continue
    checked += 1
    assert got[0] in PAPER_LINES, (sid, hid, got[0])
    # 2 行目より後に紙の行を足さない。厚紙の行も案の字だけ
    assert not PAPER_LINES.intersection(map(str, got[1:])) and all(m == BOX for m in map(str, got) if "厚紙" in m), (sid, hid, got)
    # 「前後」は見ない。竹ひごの長さの「25cm 前後」のように、紙の行のほかでは分かる言葉として使っている。
    assert not re.search(r"見込み|貼るを|g/m²", " ".join(map(str, got))), (sid, hid, got)

# 2. 紙の重さを変えた案でも、形を外れない（改善の輪は paper_gsm を範囲の中で変えられる）
for tid in ("balance_toy", "spin_toy", "stand_figure", "stick_prop", "string_pull", "wheel_cart"):
    assert lines(tid, {"paper_gsm": 80})[0] == "コピー用紙くらいの厚さの紙を 1 枚", tid
    assert lines(tid, {"paper_gsm": 150})[0] == "画用紙くらいの厚さの紙を 1 枚", tid
    assert lines(tid, {"paper_gsm": 250})[0] == "画用紙より厚い紙を 1 枚", tid
    # 境の値そのもの。境が動くと、同じ重さの紙の名前が黙って変わる
    assert lines(tid, {"paper_gsm": 109})[0] == "コピー用紙くらいの厚さの紙を 1 枚", tid
    assert lines(tid, {"paper_gsm": 110})[0] == "画用紙くらいの厚さの紙を 1 枚", tid
    assert lines(tid, {"paper_gsm": 219})[0] == "画用紙くらいの厚さの紙を 1 枚", tid
    assert lines(tid, {"paper_gsm": 220})[0] == "画用紙より厚い紙を 1 枚", tid

# 3. 空き箱の厚紙は、手順で使うので紙とは別の行に立てる。凧は厚紙を使わない
board = next((c for c in cases if c[2] == "string_pull" and "厚紙" in " ".join(TEMPLATES["string_pull"].steps({**TEMPLATES["string_pull"].DEFAULTS, **c[3]}))))
assert BOX in lines("string_pull", board[3]), lines("string_pull", board[3])
kite = next(c for c in cases if c[2] == "string_pull" and "厚紙" not in " ".join(TEMPLATES["string_pull"].steps({**TEMPLATES["string_pull"].DEFAULTS, **c[3]})))
assert not any("厚紙" in m for m in lines("string_pull", kite[3])), kite

# 4. 字を変えても作り方の印は変わらない。紙の名前を材料と読まず、厚紙は今の物で代えた材料のまま
d = ways.details("string_pull", board[3])
assert d["one_sheet"] is False and "厚紙" in d["modern_substitutes"], d
assert any(c[2] == "stand_figure" and ways.details(c[2], c[3])["one_sheet"] for c in cases), "紙の名前を材料と読んで、紙一枚の印が外れた"
# 5. 虎の前の組（控えの組）は前の字のまま刷る（凍結の床の指紋も tests/test_floor_pin.py が見る）
tiger = TEMPLATES["pivot_counterweight"]
now = tiger.SHEET_SET
for kept in tiger.KEPT_SETS:
    tiger.SHEET_SET = kept
    try:
        assert lines("pivot_counterweight", {"mount": "neck"})[0] == TORA_OLD, kept
    finally:
        tiger.SHEET_SET = now
print(f"ok 紙の行の形 {checked} 案")
