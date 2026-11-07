"""検査と出力の守りの試験。全体のレビュー（2026-11-04）で見つかった穴を、1 つずつ負の場面で押さえる。

なぜ場面（tests/frozen）でなく試験にするか: 前の回の出力が残るか・部品表と部品の対応など、1 回の生成の rc と床の名前だけでは見えない物を見るため。
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
PY = sys.executable
ENV = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
SRC_ID = "NDL-1187053-R0000005-L"


def scenario(d, name, params):
    f = pathlib.Path(d) / f"{name}.json"
    f.write_text(json.dumps({"template": "slider_fan", "source_id": SRC_ID, "params": params, "inject": {}}), encoding="utf-8")
    return f


def gen(sc, out):
    return subprocess.run([PY, "-m", "omochae", "--scenario", str(sc), "--out", str(out)], cwd=ROOT, env=ENV, capture_output=True, text=True)


# 1. 描く前の検査に落ちた時、同じ名前の前の回の紙を残さない
with tempfile.TemporaryDirectory() as d:
    out = pathlib.Path(d) / "x"
    assert gen(scenario(d, "ok", {"push_part": "tab"}), out).returncode == 0
    r = gen(scenario(d, "bad", {"push_part": "tab", "fold_height": 50}), out)
    assert r.returncode == 3 and "F5.fan_height" in r.stderr, r.stderr
    left = sorted(p.name for p in pathlib.Path(d).glob("x.*"))
    assert left == [], f"落ちた後に前の紙が残った: {left}"
    # 検査できない（exit 4）だけの時は、前の回の紙を消さない
    assert gen(scenario(d, "ok", {"push_part": "tab"}), out).returncode == 0
    broken = pathlib.Path(d) / "broken.json"
    broken.write_text(json.dumps({"template": "no_such", "source_id": SRC_ID, "params": {}, "inject": {}}), encoding="utf-8")
    assert gen(broken, out).returncode == 4
    left = sorted(p.name for p in pathlib.Path(d).glob("x.*"))
    assert left == ["x.pdf", "x.png", "x.svg"], f"検査できない時に前の紙が消えた: {left}"
    # 描いた後（PNG にする所）で検査できなくなっても、前の回の紙はそのまま、仮の名前の物も残さない
    import shutil
    before = {p.name: p.read_bytes() for p in pathlib.Path(d).glob("x.*")}
    fake = pathlib.Path(d) / "bin"
    fake.mkdir()
    (fake / "pdftoppm").write_text("#!/bin/sh\nexit 1\n")
    (fake / "pdftoppm").chmod(0o755)
    r = subprocess.run([PY, "-m", "omochae", "--scenario", str(scenario(d, "stick", {"push_part": "stick", "pusher_height": 84})), "--out", str(out)],
                       cwd=ROOT, env={**ENV, "PATH": f"{fake}:{os.environ['PATH']}"}, capture_output=True, text=True)
    assert r.returncode == 4, r.stderr
    after = {p.name: p.read_bytes() for p in pathlib.Path(d).glob("x*")}
    assert after == before, f"検査できない時に紙が変わった・増えた: {sorted(after)}"

# 1b. 仮の置き場は毎回別の名前。点のある --out でも揃い、たまたま同じ名前の別の出力（x-partial）を壊さない
with tempfile.TemporaryDirectory() as d:
    assert gen(scenario(d, "ok", {"push_part": "tab"}), pathlib.Path(d) / "x.v1").returncode == 0
    assert {"x.v1.svg", "x.v1.pdf", "x.v1.png"} <= {p.name for p in pathlib.Path(d).iterdir()}
    assert gen(scenario(d, "ok", {"push_part": "tab"}), pathlib.Path(d) / "y-partial").returncode == 0
    keep = {p.name: p.read_bytes() for p in pathlib.Path(d).glob("y-partial.*")}
    assert gen(scenario(d, "stick", {"push_part": "stick", "pusher_height": 84}), pathlib.Path(d) / "y").returncode == 0
    assert {p.name: p.read_bytes() for p in pathlib.Path(d).glob("y-partial.*")} == keep
    assert not [p for p in pathlib.Path(d).iterdir() if p.name.startswith(".omochae-")], "仮の置き場が残った"

# 1c. 名前の点の後ろを切らない（#28）。切ると、別の版の名前で落ちた時に、前の版の紙を消す
with tempfile.TemporaryDirectory() as d:
    r = gen(scenario(d, "ok", {"push_part": "tab"}), pathlib.Path(d) / "tiger_v1.5")
    assert r.returncode == 0 and r.stdout.strip().endswith("tiger_v1.5.pdf"), r.stdout
    made = {"tiger_v1.5.svg", "tiger_v1.5.pdf", "tiger_v1.5.png"}
    assert made <= {p.name for p in pathlib.Path(d).iterdir()}
    r = gen(scenario(d, "bad", {"push_part": "tab", "fold_height": 50}), pathlib.Path(d) / "tiger_v1.9")
    assert r.returncode == 3 and "F5.fan_height" in r.stderr, r.stderr
    assert made <= {p.name for p in pathlib.Path(d).iterdir()}, "別の名前で落ちて、前の紙が消えた"
    # 同じ名前で落ちた時は消す（1 の決まりは、点のある名前でも同じ）
    r = gen(scenario(d, "bad", {"push_part": "tab", "fold_height": 50}), pathlib.Path(d) / "tiger_v1.5")
    assert r.returncode == 3 and not made & {p.name for p in pathlib.Path(d).iterdir()}, r.stderr

# 2. 線の絵が糊代を横切ったら落とす（面積でなく長さで見る）
sys.path.insert(0, str(ROOT / "src"))
from omochae.floors import check_art
from omochae.model import Part

glue = [[(30, 0), (40, 0), (40, 20), (30, 20)]]
over = Part(1, "t", "試し", [(0, 0), (40, 0), (40, 20), (0, 20)], glue=glue, art=[{"kind": "line", "pts": [(5, 10), (38, 10)], "stroke": "#000", "sw": 0.3}])
clear = Part(1, "t", "試し", [(0, 0), (40, 0), (40, 20), (0, 20)], glue=glue, art=[{"kind": "line", "pts": [(5, 10), (25, 10)], "stroke": "#000", "sw": 0.3}])
assert [f.floor for f in check_art([over])] == ["F5.image_box"]
assert check_art([clear]) == []
# 中心線は糊代の手前でも、刷られる太さで糊代にかかれば落とす
thick = Part(1, "t", "試し", [(0, 0), (40, 0), (40, 20), (0, 20)], glue=glue, art=[{"kind": "line", "pts": [(29.5, 2), (29.5, 18)], "stroke": "#000", "sw": 2.0}])
thin = Part(1, "t", "試し", [(0, 0), (40, 0), (40, 20), (0, 20)], glue=glue, art=[{"kind": "line", "pts": [(29.5, 2), (29.5, 18)], "stroke": "#000", "sw": 0.3}])
assert [f.floor for f in check_art([thick])] == ["F5.image_box"]
assert check_art([thin]) == []
# 輪郭線つきの面は、線の太さで糊代にかかれば落とす
framed = Part(1, "t", "試し", [(0, 0), (40, 0), (40, 20), (0, 20)], glue=glue,
              art=[{"kind": "poly", "pts": [(5, 5), (29.5, 5), (29.5, 15), (5, 15)], "fill": "#ccc", "stroke": "#000", "sw": 2.0}])
assert [f.floor for f in check_art([framed])] == ["F5.image_box"]
# 折れ曲がる線は、SVG と同じく尖った角の先まで見る（丸い角で見ると角の先が糊代にかかるのを見逃す）
bent = Part(1, "t", "試し", [(0, 0), (40, 0), (40, 20), (0, 20)], glue=glue, art=[{"kind": "line", "pts": [(10, 4), (28.0, 10), (10, 16)], "stroke": "#000", "sw": 1.5}])
assert [f.floor for f in check_art([bent])] == ["F5.image_box"]

# 3. 型紙に刷る部品は全部、部品表に載る（首の形の重りの腕）
from omochae.floors import check_bom
from omochae.templates import pivot_counterweight as pc, slider_fan as sf

for tpl, forms in ((pc, [{"mount": "neck"}, {"mount": "hang"}]), (sf, [{"push_part": x} for x in ("tab", "tube", "stick")])):
    for form in forms:
        p = {**tpl.DEFAULTS, **form}
        assert check_bom(tpl.bom(p), tpl.parts(p)) == [], (tpl.ID, form)
neck = {**pc.DEFAULTS, "mount": "neck"}
short = [r for r in pc.bom(neck) if r["number"] != 5]
assert [f.floor for f in check_bom(short, pc.parts(neck))] == ["F2.bom"]
assert any("竹串" in m for m in pc.materials(neck)) and any("油粘土" in m for m in pc.materials(neck))
other = [dict(r, key="other", name="別の物") if r["number"] == 5 else r for r in pc.bom(neck)]
assert [f.floor for f in check_bom(other, pc.parts(neck))] == ["F2.bom"]
twice = pc.bom(neck) + [dict(pc.bom(neck)[0])]
assert [f.floor for f in check_bom(twice, pc.parts(neck))] == ["F2.bom"]

# 4. 刷った後の印の検査は、所蔵・改変の注記・仮説の文をそのまま探す
from omochae.marks import check_pdf

source = json.loads((ROOT / "data/sources" / f"{SRC_ID}.json").read_text(encoding="utf-8"))
with tempfile.TemporaryDirectory() as d:
    out = pathlib.Path(d) / "m"
    assert gen(scenario(d, "ok", {"push_part": "tab"}), out).returncode == 0
    pdf = out.with_suffix(".pdf")
    assert check_pdf(pdf, source) == []
    other = {**source, "holding": source["holding"] + "（別の文）", "modification_note": "改変: 別の注記"}
    assert sorted(f.where for f in check_pdf(pdf, other)) == ["所蔵の文", "改変"]

# 4b. 刷った後の検査に落ちた紙も、名前の点の後ろを切らずに退ける（#28）
import contextlib
import io
import omochae.__main__ as entry
from omochae.model import Failure

with tempfile.TemporaryDirectory() as d, contextlib.redirect_stderr(io.StringIO()):
    out = pathlib.Path(d) / "m.v2"
    keep_check, entry.check_pdf = entry.check_pdf, lambda pdf, src: [Failure("F7.mark", "所蔵の文", "試験で落とす")]
    try:
        assert entry.generate("slider_fan", {"push_part": "tab"}, SRC_ID, out) == 3
    finally:
        entry.check_pdf = keep_check
    assert [p.name for p in pathlib.Path(d).iterdir()] == ["m.v2.rejected.pdf"]

# 5. 開く糸の長さは、筒の穴（口から THREAD_DEPTH 下）から測る
from omochae.fan_model import shortest_free_thread

p = {**sf.DEFAULTS, "push_part": "tab", "tube_side": 26, "pusher_side": 22, "base_side": 22, "pivot_above_rim": 2, "push_amount": 69, "fold_height": 38, "fold_count": 10}
tube = next(q for q in sf.parts(p) if q.key == "tube")
depth = tube.holes[0][1]
assert depth == sf.THREAD_DEPTH
z0 = p["pivot_above_rim"] + depth
assert abs(sf.thread_mm(p) - shortest_free_thread(p["tube_side"], sf.THREAD_RADIUS, z0 - p["push_amount"], z0)) < 1e-9
assert abs(sf.thread_mm(p) - 30.3) < 0.1, sf.thread_mm(p)

# 6. 色の境で折る扇でも、足の糊代の境の谷折り線だけは刷る（組み方の文が「糊代の境の破線で折り」と言うため）
import re
from omochae.compose import compose
from omochae.render import to_svg

# pivot_above_rim 2 は足の長さが糊代と同じで、足の折り線が x = 0 に来る境目
for form in ({"push_part": "tab"}, {"push_part": "stick", "pusher_height": 84}, {"push_part": "tab", "pivot_above_rim": 2, "fold_count": 6, "fold_width": 5, "fold_height": 40}):
    _, layout, failures = compose("slider_fan", form, source)
    assert not failures
    fan = next(q for q in layout["parts"] if q.key == "fan")
    assert len(fan.print_folds) == 1 and fan.print_folds[0][0][0] == fan.print_folds[0][1][0] <= 0, fan.print_folds
    dashed = re.findall(r'<path d="M([-\d.]+),([-\d.]+) L([-\d.]+),([-\d.]+)" [^>]*stroke-dasharray="2,1"', to_svg(layout))
    on_fan = [d for d in dashed if fan.x - 30 < float(d[0]) < fan.x + fan.width and fan.y <= float(d[1]) <= fan.y + fan.height]
    (x1, y1), (x2, y2) = fan.print_folds[0]
    assert [tuple(float(v) for v in d) for d in on_fan] == [(fan.x + x1, fan.y + y1, fan.x + x2, fan.y + y2)], on_fan
# 口の台の形は足が無いので、刷る折り線も無い
_, layout, _ = compose("slider_fan", {"hub": "rim", "push_amount": 36, "pusher_height": 40, "fold_count": 14, "fold_width": 8, "fold_height": 36}, source)
assert next(q for q in layout["parts"] if q.key == "fan").print_folds == []

# 7. 寸法を直に渡す入口（--params）: 雛形ごとの刷る形の寸法を求め、御来迎も虎も刷れる。出典と出力の名前は雛形ごとの既定
def params_run(d, template, params, out=None):
    f = pathlib.Path(d) / f"{template}.json"
    f.write_text(json.dumps(params), encoding="utf-8")
    cmd = [PY, "-m", "omochae", "--template", template, "--params", str(f)] + (["--out", str(out)] if out else [])
    return subprocess.run(cmd, cwd=d, env=ENV, capture_output=True, text=True)

with tempfile.TemporaryDirectory() as d:
    # 出典を書かない時は雛形の既定の出典を使う。ROOT の data/sources から読むので、cwd は repo の外でよい
    r = params_run(d, "pivot_counterweight", {"mount": "hang", "axle_height": 50})
    assert r.returncode == 0, r.stderr
    assert (pathlib.Path(d) / "out/templates/pivot_counterweight_v1.pdf").exists()
    assert params_run(d, "slider_fan", {"push_part": "stick", "pusher_height": 84}, pathlib.Path(d) / "s").returncode == 0
    r = params_run(d, "pivot_counterweight", {"axle_height": 50})
    assert r.returncode == 4 and "mount が要る" in r.stderr, r.stderr
    r = params_run(d, "slider_fan", {"fold_count": 20})
    assert r.returncode == 4 and "push_part が要る" in r.stderr, r.stderr
    assert "omochae.hypotheses" not in r.stderr  # この repo に無い道具を案内しない
    # --scenario の時は --template を使わないので、併記された知らない名前で止めない。--params の時は知らない名前を落とす
    r = subprocess.run([PY, "-m", "omochae", "--scenario", str(ROOT / "examples/fan_tab.json"), "--template", "no_such", "--out", str(pathlib.Path(d) / "sc")], cwd=d, env=ENV, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    r = params_run(d, "no_such", {"push_part": "tab"})
    assert r.returncode == 4 and "知らない雛形" in r.stderr, r.stderr
# 雛形ごとの既定の出典は雛形が持つ（雛形を足した時に出典を足し忘れると、雛形の SOURCE が無くて試験で落ちる）
from omochae.compose import TEMPLATES
for tpl in TEMPLATES.values():
    assert (ROOT / "data/sources" / f"{tpl.SOURCE}.json").exists(), tpl.ID

# 8. 虎の吊る形の組み方の文（steps が返す文。この repo の型紙には刷らない）は、頭を帯に重ねて貼る長さを言う。重ねた後の軸から頭の上までが、式の見込み（axle_to_head_top）と合う
hang = {**pc.DEFAULTS, "mount": "hang"}
assert any(f"2 頭の上の端に {pc.HEAD_OVERLAP}mm 重ねて貼る" in s for s in pc.steps(hang))
strip = next(q for q in pc.parts(hang) if q.key == "strip")
assert strip.height - strip.holes[0][1] - pc.HEAD_OVERLAP == pc.axle_to_head_top(hang)

# 9. 雛形は templates/ に置くだけで登録される（雛形を並行して足す担当が、共有の登録の行に触らずに済むように）。ID を持つ module は漏れなく載る
import pkgutil
import omochae.templates as tdir
mods = {i.name for i in pkgutil.iter_modules(tdir.__path__)}
assert {"slider_fan", "pivot_counterweight"} <= set(TEMPLATES), sorted(TEMPLATES)
assert {t.__name__.rsplit(".", 1)[1] for t in TEMPLATES.values()} == {m for m in mods if hasattr(__import__(f"omochae.templates.{m}", fromlist=["ID"]), "ID")}

# 10. 刷る形ごとに出典が違う雛形（SOURCES）では、形と合わない出典を刷らない。既定の出典も形から選ぶ（形を 1 つの SOURCE に決め打ちすると、
# 別の形の絵に別の玩具の出典を刷った。レビューの指摘）。SOURCES の無い雛形（御来迎・虎）は今までどおり SOURCE を使い、検査もしない
import types
from omochae.__main__ import load_source, scenario_from_args
from omochae.compose import compose
tiger = load_source(pc.SOURCE)
pc.SOURCES = {"neck": pc.SOURCE, "hang": "NDL-1187053-R0000005-L"}
try:
    _, _, fl = compose(pc.ID, {"mount": "hang"}, tiger)
    assert any(f.floor == "F1.source" for f in fl), [f.line() for f in fl]
    _, _, fl = compose(pc.ID, {"mount": "neck"}, tiger)
    assert not any(f.floor == "F1.source" for f in fl), [f.line() for f in fl]
    pj = ROOT / "out" / "_src_hang.json"
    pj.parent.mkdir(exist_ok=True)
    pj.write_text('{"mount": "hang"}', encoding="utf-8")
    args = types.SimpleNamespace(scenario=None, template=pc.ID, params=str(pj), source=None)
    assert scenario_from_args(args)["source_id"] == "NDL-1187053-R0000005-L"
    pj.unlink()
finally:
    del pc.SOURCES
_, _, fl = compose(pc.ID, {"mount": "hang"}, tiger)
assert not any(f.floor == "F1.source" for f in fl)

# 11. 組み立ての位置の印（貼る所・差す深さ）は、切る線（黒の実線）とも折る線（黒の破線）とも違う見た目で刷り、凡例に意味を書く。
# 雛形ごとに実線や破線で描くと、子どもが切るか折るかしてしまった（族の雛形のレビューの指摘）。印を使わない紙の凡例は今までどおり
from omochae import render
orig_parts = pc.parts
def parts_with_mark(p):
    qs = orig_parts(p)
    tail = next(q for q in qs if q.key == "tail")
    tail.art.append({"kind": "mark", "pts": [(2, 20), (6, 20)]})
    return qs
pc.parts = parts_with_mark
try:
    _, lay, fl = compose(pc.ID, {"mount": "hang", "axle_height": 50}, tiger)
    assert fl == [], [f.line() for f in fl]
    assert any(t.text and "位置の印" in t.text for t in lay["texts"])
    svg = render.to_svg(lay)
    assert render.MARK_COLOR in svg and f'stroke-dasharray="{render.MARK_DASH}"' in svg
finally:
    pc.parts = orig_parts
# 印を使わない紙（御来迎のつまみの形）の凡例は今までどおり。虎は尾を貼る四角の印（実物の写真の直し E）を、どちらの形も使う
_, lay, _ = compose(sf.ID, {"push_part": "tab"}, load_source(sf.SOURCE))
assert not any(t.text and "位置の印" in t.text for t in lay["texts"])
_, lay, _ = compose(pc.ID, {"mount": "hang", "axle_height": 50}, tiger)
assert any(t.text and "位置の印" in t.text for t in lay["texts"])
# 閉じた印は戻る辺も刷るので、検査も戻る辺まで見る。印は描く所が決めた太さと丸い端で見る。穴や中の切り込みにかかる印は、切ると消えるので落とす
from omochae.floors import check_art
def art_fail(art, key="body", mount="hang"):
    qs = pc.parts({**pc.DEFAULTS, "mount": mount}); q = next(x for x in qs if x.key == key); q.art = [art]
    return [f.message for f in check_art([q])]
assert art_fail({"kind": "mark", "pts": [(44, 42), (56, 42), (56, 84)], "closed": True}), "閉じた印の戻る辺を見ていない"
assert art_fail({"kind": "mark", "pts": [(2, 9), (6, 9)], "stroke": "#000"}, key="strip") == [], "印に書いた stroke で太さが 0 になった"
body = next(x for x in pc.parts({**pc.DEFAULTS, "mount": "neck"}) if x.key == "body")
# 首の穴は丸い切り抜き（実物の写真の直し A）。丸い切り抜きにかかる印も、切ると消えるので落とす
cx, cy, r = body.round_cuts[0]
assert art_fail({"kind": "mark", "pts": [(cx - r + 1, cy), (cx + r - 1, cy)]}, mount="neck"), "丸い切り抜きにかかる印を通した"
# 矩形の切り込みにかかる印も、前と同じく落とす（矩形の切り込みを持つ部品で見る）
rect = Part(1, "plate", "板", [(0, 0), (40, 0), (40, 40), (0, 40)], cuts=[(10, 10, 20, 20)], art=[{"kind": "mark", "pts": [(12, 20), (28, 20)]}])
assert any("切り込みにかかり" in f.message for f in check_art([rect])), "切り込みにかかる印を通した"
# 丸い切り抜き（round_cuts）が部品の外に出たら、穴と同じ床（F5.hole）で落とす。刷る時は切る線と同じ実線の円で描く
from omochae.floors import check_holes
from shapely.geometry import LineString, Point
sq = [(0, 0), (40, 0), (40, 40), (0, 40)]
assert [f.floor for f in check_holes([Part(1, "plate", "板", sq, round_cuts=[(38, 20, 5)])])] == ["F5.hole"]
assert check_holes([Part(1, "plate", "板", sq, round_cuts=[(20, 20, 5)])]) == []
# 円の弧だけがわずかにかかる寸法も落とす。円の内に入る多角形（64 頂点）の 2 つの頂点の真ん中の向きで、円から 0.003mm 内に
# 引いた折り線は、円にはかかるが内の多角形にはかからない（前の見方では通っていた）
import math as _m
_a, _d = _m.pi / 64, 4.997  # 頂点の間の真ん中の向きと、中心から線までの長さ（円の半径 5 より短く、内の多角形の 5·cos(π/64)≈4.994 より長い）
_ux, _uy = _m.cos(_a), _m.sin(_a)
_p = ((20 + _d * _ux + 8 * _uy, 20 + _d * _uy - 8 * _ux), (20 + _d * _ux - 8 * _uy, 20 + _d * _uy + 8 * _ux))
assert Point(20, 20).buffer(5, quad_segs=16).intersects(LineString(_p)) is False  # 内の多角形にはかからない（試験の前提）
assert [f.floor for f in check_holes([Part(1, "plate", "板", sq, mountain=[_p], round_cuts=[(20, 20, 5)])])] == ["F5.hole"]
# 逆に、円から 0.003mm 離れた折り線（頂点の向き）は円にかからないので通す（円を外から包む多角形で見ると、落としていた）
assert check_holes([Part(1, "plate", "板", sq, mountain=[((25.003, 0), (25.003, 40))], round_cuts=[(20, 20, 5)])]) == []
assert check_holes([Part(1, "plate", "板", sq, glue=[[(25.003, 0), (40, 0), (40, 40), (25.003, 40)]], round_cuts=[(20, 20, 5)])]) == []
# 丸い切り抜きが折り線か糊代にかかる時も落とす（外形の内でも、折る所・貼る所を切り取る）
assert [f.floor for f in check_holes([Part(1, "plate", "板", sq, mountain=[((0, 22), (40, 22))], round_cuts=[(20, 20, 5)])])] == ["F5.hole"]
assert [f.floor for f in check_holes([Part(1, "plate", "板", sq, glue=[[(0, 30), (40, 30), (40, 40), (0, 40)]], round_cuts=[(20, 27, 5)])])] == ["F5.hole"]
_, lay, _ = compose(pc.ID, {"mount": "neck"}, tiger)
neck_r = pc.DEFAULTS["opening"] / 2
assert re.search(rf'<circle [^>]*r="{neck_r:g}(\.0+)?"', render.to_svg(lay)), "丸い切り抜きを円で刷っていない"

# 作業の覚え書きは、追跡している .gitignore だけで外れる（.git/info/exclude は clone に付いてこないので、まっさらな repo で見る）
if shutil.which("git"):
    with tempfile.TemporaryDirectory() as d:
        env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
        subprocess.run(["git", "init", "-q", d], env=env, check=True)
        shutil.copy(ROOT / ".gitignore", d)
        names = ["LANE-BRIEF.md", "LANE-NOTES.md", "LANE-X.md", "lane-issues/a.md", "keep.md"]
        for n in names:
            f = pathlib.Path(d) / n
            f.parent.mkdir(exist_ok=True)
            f.write_text("x", encoding="utf-8")
        r = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=d, env=env, capture_output=True, text=True, check=True)
        shown = sorted(line[3:] for line in r.stdout.splitlines())
        assert shown == [".gitignore", "keep.md"], f"覚え書きが git status に出た: {shown}"

# 12. 型紙は正解でなく、AI が考えた仮説である事を紙に刷る（制作者の言葉・#57）。刷った PDF から読める事まで見る
import shutil as _sh
from omochae import marks as _marks
assert "AI が考えた" in _marks.HYPOTHESIS and "正解ではありません" in _marks.HYPOTHESIS, _marks.HYPOTHESIS
with tempfile.TemporaryDirectory() as d:
    r = subprocess.run([sys.executable, "-m", "omochae", "--scenario", str(ROOT / "tests/frozen/scenarios/pos_tab.json"), "--out", f"{d}/s"],
                       cwd=ROOT, capture_output=True, text=True, env={**os.environ, "PYTHONPATH": str(ROOT / "src")})
    assert r.returncode == 0, r.stderr
    text = subprocess.run(["pdftotext", f"{d}/s.pdf", "-"], capture_output=True, text=True).stdout.replace(" ", "").replace("\n", "")
    assert "AIが考えた" in text and "正解ではありません" in text, text[:400]

print("ok")
