"""雛形 string_pull の試験。線の全部の玩具の全部の仮説の版 1 が、本物の道（hypotheses.print_sheet）で刷れる事と、床が落とす事を見る。

一時の置き場を使うのは、本物の記録（data/decisions）と刷った紙の置き場を汚さないため。
"""
import contextlib
import io
import json
import os
import pathlib
import tempfile

tmp = tempfile.mkdtemp()
os.environ["OMOCHAE_DATA"] = tmp

from omochae import hypotheses
from omochae.compose import TEMPLATES, compose
from omochae.metrics import ALLOWED, METRICS, values
from omochae.templates import string_pull as T

ROOT = pathlib.Path(__file__).resolve().parents[1]
inv = json.loads((ROOT / "data/inventory/edo-nishiki.json").read_text(encoding="utf-8"))["toys"]
lane = [t["id"] for t in inv if t.get("lane") == "string"]
# 作らないと決めた件と理由。返事にも同じ理由を書く。
LEFT_OUT = {
    "NDL-1187053-R0000029-L-2": "竿の先の糸に毛の玉が下がるだけで、糸や棒で動く所（軸・腕）が図に無い。太鼓の柄と一組かも割れていて（棚卸しの注記）、型紙にすると見立てを事実として刷る事になる",
}
assert len(lane) == 13, lane
assert set(LEFT_OUT) <= set(lane)

floors = lambda fs: {f.floor for f in fs}
src = lambda sid: json.loads((ROOT / "data/sources" / f"{sid}.json").read_text(encoding="utf-8"))

assert TEMPLATES[T.ID] is T and T.ID in METRICS and ALLOWED[T.ID] <= set(T.RANGES)

printed = 0
for sid in lane:
    rec_path = ROOT / "data/hypotheses" / f"{sid}.json"
    if sid in LEFT_OUT:
        assert not rec_path.exists(), (sid, "作らないと決めた件に記録を置かない")
        continue
    data = json.loads(rec_path.read_text(encoding="utf-8"))
    assert data["template"] == T.ID and data["stage"] == "試作", sid
    assert data["written_by"] == "Claude Code のセッションが案を書いた。人の確認はまだ"
    hs = data["hypotheses"]
    assert 2 <= len(hs) <= 3, sid
    keys = [h["params"][T.HYP_KEY] for h in hs]
    assert len(set(keys)) == len(keys), (sid, "仮説は HYP_KEY の値で分ける")
    assert all(e["certainty"] in ("観察", "推測") for h in hs for e in h["evidence"]), sid
    # 翻刻は人が写す欄（U-01）。棚卸しの見立ての名前から読みを起こさない。
    assert src(sid)["transcription"]["entries"] == [], sid
    for h in hs:
        out = pathlib.Path(tmp) / "sheets" / f"{sid}_{h['id']}"
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            rc = hypotheses.print_sheet(sid, h["id"], str(out), version=1)
        assert rc == 0, (sid, h["id"], err.getvalue())
        # 刷るのは型紙だけ（窓口の決定 推し A・11-06）。手順の紙と試した後の紙は刷る時に組まない（組む仕組みは凍結の床の控えが見る）
        assert pathlib.Path(f"{out}.pdf").exists() and not any(pathlib.Path(f"{out}{s}.pdf").exists() for s in ("_tejun", "_after")), (sid, h["id"])
        values(T.ID, h["params"])  # 台帳の式が全部の仮説で数を返す
        printed += 1
assert printed == 24, printed


def fails(params, where=None):
    p = {**T.DEFAULTS, **params}
    fs = T.check_range(p) or T.check_physics(p)
    return [f for f in fs if where is None or where in f.where + f.message]


rice = json.loads((ROOT / "data/hypotheses/NDL-1187053-R0000006-L.json").read_text(encoding="utf-8"))["hypotheses"][0]["params"]
assert not fails(rice)
# 糸の穴が腕木の左の端に近すぎる（のぼり猿の最初の寸法がこれで落ちた）
assert fails({**rice, "pivot_at": 14, "pull_arm": 12}, "糸の穴")
# 腕が短すぎる・引く量が腕の 2 倍を超える・少ししか回らない
assert fails({**rice, "pull_arm": 4, "stroke": 3}, "短い")
assert fails({**rice, "stroke": 30}, "裏返る")
assert fails({**rice, "stroke": 2}, "見えない")
# 軸を腕木の重心に置くと、離しても戻らない（揺れる形は揺れない）
center = round(T.Polygon(T.mover_outline({**T.DEFAULTS, **rice})).centroid.x)
assert fails({**rice, "pivot_at": center}, "戻らない")
assert fails({**rice, "rig": "sway", "pivot_at": center}, "揺れない")
assert not fails({**rice, "rig": "push", "pivot_at": center}), "押す形は重さで戻らなくてよい"
# 軸の穴が台紙の縁に近い・糸の通し穴が台紙の外
assert fails({**rice, "pivot_x": 97}, "台紙の軸の穴")
assert fails({**rice, "guide_drop": 70}, "通し穴")

owl = json.loads((ROOT / "data/hypotheses/NDL-1187053-R0000024-L-3.json").read_text(encoding="utf-8"))["hypotheses"]
tail, bow = owl[0]["params"], owl[1]["params"]
assert not fails(tail) and not fails(bow)
# 糸目が帆の外（木菟の頭の先は細いので、上の端に寄せると外へ出る）
assert fails({**tail, "bridle_top": 3}, "上の糸目")
assert fails({**tail, "bridle_bottom": 139}, "下の糸目")
# 結び目が帆の重心より下・上の糸目より上
assert fails({**tail, "tow_at": 100}, "結び目")
assert fails({**tail, "tow_at": 10}, "結び目")
assert fails({**tail, "tail_len": 200}, "尾")
assert fails({**bow, "bow_depth": 1}, "反り") and fails({**bow, "bow_depth": 40}, "反り")
# 横骨が頭の先の細い所を渡る
assert fails({**tail, "spar_y": 6}, "横骨")
# 絵と動かし方の組み合わせ・知らない値は範囲で落とす
assert floors(fails({**tail, "rig": "pull"})) == {"F5.range"}
assert floors(fails({**rice, "shape": "kappa"})) == {"F5.range"}
assert floors(fails({**rice, "stroke": 0})) == {"F5.range"}

# 床に落ちる値は本物の道でも刷らない（compose が F5.lever を返し、配置の検査の前に名前で分かる）
_, _, fs = compose(T.ID, {**rice, "pull_arm": 4, "stroke": 3}, src("NDL-1187053-R0000006-L"))
assert "F5.lever" in floors(fs)
print("ok", printed)
