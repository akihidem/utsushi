"""雛形 stand_figure（figure の線）: 線の全部の玩具・全部の仮説の版 1 が、本物の道（hypotheses.print_sheet）で床を通って刷れる事と、
床に落ちる値が落ちる事を見る。契約は docs/process/template-contract.md。

なぜ並列で刷るか: 38 件・76 枚の型紙と手順の紙を 1 本ずつ刷ると数分かかり、./run.sh の待ちが延びる。刷る道は同じで、数を減らさない。
"""
import json
import multiprocessing
import os
import pathlib
import tempfile
from concurrent.futures import ProcessPoolExecutor

# 置き場は一時の所。試験の予想や版の記録を本物の data/ に残さないため。子の工程にも env で渡る。
os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from omochae import hypotheses  # noqa: E402
from omochae.compose import compose  # noqa: E402
from omochae.templates import stand_figure as T  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
INV = json.loads((ROOT / "data/inventory/edo-nishiki.json").read_text(encoding="utf-8"))
LANE = sorted(t["id"] for t in INV["toys"] if t.get("lane") == "figure")
# 作らないと決めた件と理由。棚卸しは共有のファイルなので書き換えず、ここに残して返事で統括の担当へ渡す。
LEFT_OUT = {
    "NDL-1187053-R0000005-R-4": "刀の付属品（小柄・笄）と見る。単独の玩具と言える根拠が絵に無い",
    "NDL-1187053-R0000023-L-3": "羽子板の後ろの花の枝で、季節の添え物と見る",
}
MADE = [sid for sid in LANE if sid not in LEFT_OUT]
assert set(LEFT_OUT) <= set(LANE)
for sid in LEFT_OUT:
    assert not (ROOT / "data/hypotheses" / f"{sid}.json").exists(), sid


def _one(job):
    sid, hid, out = job
    return sid, hid, hypotheses.print_sheet(sid, hid, out)


jobs = []
out = pathlib.Path(os.environ["OMOCHAE_DATA"]) / "sheets"
out.mkdir()
for sid in MADE:
    data = json.loads((ROOT / "data/hypotheses" / f"{sid}.json").read_text(encoding="utf-8"))
    assert data["template"] == T.ID and data["stage"] == "試作", sid
    assert data["written_by"] == "Claude Code のセッションが案を書いた。人の確認はまだ"
    assert 2 <= len(data["hypotheses"]) <= 3, sid
    forms = [h["params"][T.HYP_KEY] for h in data["hypotheses"]]
    assert len(set(forms)) == len(forms), (sid, "仮説は置き方（HYP_KEY）で分ける")
    for h in data["hypotheses"]:
        assert all(e["certainty"] in ("観察", "推測", "二次資料") for e in h["evidence"]), sid
        jobs.append((sid, h["id"], str(out / f"{sid}-{h['id']}")))
    # 名前は見立てのまま、翻刻は空（読みは本人が確かめる、U-01）。
    src = json.loads((ROOT / "data/sources" / f"{sid}.json").read_text(encoding="utf-8"))
    assert src["transcription"]["entries"] == [], sid

# 3.14 の既定（forkserver）は試験の本体を子で読み直すので、fork で子を起こす。本体は __main__ の守りの無い素の試験の書き方のため。
with ProcessPoolExecutor(max_workers=min(8, os.cpu_count() or 2), mp_context=multiprocessing.get_context("fork")) as ex:
    results = list(ex.map(_one, jobs))
bad = [(s, h, rc) for s, h, rc in results if rc != 0]
assert not bad, bad
# 刷るのは型紙だけ（窓口の決定 推し A・11-06）。手順の紙と試した後の紙は刷る時に組まない（組む仕組みは凍結の床の控えが見る）
for _, _, stem in jobs:
    assert pathlib.Path(f"{stem}.pdf").exists() and not any(pathlib.Path(f"{stem}{s}.pdf").exists() for s in ("_tejun", "_after")), stem
print(f"ok 刷れた {len(MADE)} 件・{len(jobs)} 仮説")

# ---- 床に落ちる値 ----
SRC = json.loads((ROOT / "data/sources" / f"{MADE[0]}.json").read_text(encoding="utf-8"))


def floors(params):
    _, _, f = compose(T.ID, params, SRC)
    return {x.floor for x in f}, [x.line() for x in f]


# 高い絵を狭い台に載せると、少し傾けただけで倒れる
got, lines = floors({"form": "base", "motif": "nobori_box", "fig_h": 120, "base_w": 40, "base_d": 20, "base_h": 40})
assert "F5.stand" in got and any("倒れる" in x for x in lines), lines
# 小さい器に重い絵を載せると、縁まで水が来る
got, lines = floors({"form": "float", "motif": "shrine", "fig_h": 88, "base_w": 96, "base_d": 20, "base_h": 6, "paper_gsm": 400})
assert "F5.float" in got and any("水が入る" in x for x in lines), lines
# 支えが長すぎると、折り目の高さが絵の背からはみ出す
got, lines = floors({"form": "easel", "motif": "rabbit", "fig_h": 40, "strut_len": 60})
assert any("支えの糊代" in x for x in lines), lines
# 台が糊代より狭い
got, lines = floors({"form": "base", "motif": "shrine", "fig_h": 88, "base_w": 40})
assert any("糊代" in x and "収まらない" in x for x in lines), lines
# 器の壁が絵より高い
got, lines = floors({"form": "box", "motif": "gourd", "fig_h": 30, "base_h": 28})
assert any("器の壁" in x for x in lines), lines
# 知らない絵・知らない置き方・範囲の外
for bad_p in ({"motif": "dragon"}, {"form": "hang"}, {"fig_h": 200}):
    got, lines = floors(bad_p)
    assert got == {"F5.range"}, (bad_p, lines)
# 床を通る既定の値は通る（落ちる値だけが落ちている事の対照）
assert floors({})[0] == set()
print("ok 床")

# ---- 折り線は色の境に置き、見える面には刷らない（本人の決定 d） ----
p = {**T.DEFAULTS, "form": "float"}
by = {q.key: q for q in T.parts(p)}
assert by["front"].hide_folds and by["back"].hide_folds and by["tray"].hide_folds
assert len(by["front"].valley) == 1 and by["front"].glue, "表の下に糊代と、その境の折り線が 1 本"
# 裏は表の鏡の絵
fw = by["front"].width
assert abs(by["back"].width - fw) < 1e-6
# 台の上の面と壁は色が違う（色の境が折り目）
fills = [a["fill"] for a in by["tray"].art if a["kind"] == "poly"]
assert fills[0] != fills[1]
# 全部の絵が A4 の表と裏の大きさに収まる見込み
for m in T.MOTIFS:
    w_u = T.MOTIFS[m][0]()[0]
    assert T.tab_width({**T.DEFAULTS, "motif": m, "fig_h": round(min(90, 86 * 100 / w_u))}) > 0
assert set(T.metrics(T.DEFAULTS)) == {"tip_deg", "draft_mm", "center_height_mm", "mass_g"}
print("ok 部品")
