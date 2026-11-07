"""御来迎の内筒を下から押し上げる形（push_part rise）と、次の組（goraigo-v13）の見本の寸法を確かめる。

制作者の決定（2026-11-06）「筒を外す形（lift）はやめる。下から押し上げるバージョンを作る。側面のつまみのバージョンは廃止。
内筒を付ける。」と、前の決定「糸なしでやります」による形。v13 は制作者の指示（2026-11-06）「御来迎の形の直し: ① 外筒の紫色の部分は
不用（外す）。② 内筒は半分の長さにする。③ 押し上げは、内筒の内側に割り箸を貼り付ける形にする。」と「顔は、両側に貼れるように
首から立体的にするか、両側から見た物を用意して。」（両側から見た物の方）を入れた組。選んだ事は slider_fan の RISE の注。
"""
import json
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from omochae.__main__ import load_source  # noqa: E402
from omochae.compose import compose  # noqa: E402
from omochae.templates import slider_fan as sf  # noqa: E402

SC = json.loads((ROOT / "examples/goraigo_v13.json").read_text(encoding="utf-8"))
V13 = {**sf.DEFAULTS, **SC["params"]}
SRC = load_source(SC["source_id"])
words = lambda p: " ".join(r["material"] for r in sf.bom(p)) + " ".join(sf.materials(p)) + " ".join(sf.steps(p))

# 1. 見本の寸法: 形は rise。比は実物の写真の目測（扇の半径は筒の一辺の約 1.1 倍・像の幅は一辺の約 0.4 倍・筒の長さは一辺の約 4 倍）。
#    内筒は v12 の 115 の半分（指示 ②）。ほかは v12 のまま
assert SC["template"] == "slider_fan" and V13["push_part"] == sf.RISE
A, H, L, a = V13["tube_side"], V13["tube_height"], V13["pusher_height"], V13["pusher_side"]
assert abs(V13["fold_height"] / A - 1.1) <= 0.05 and abs(V13["figure_w"] / A - 0.4) <= 0.01, (V13["fold_height"], V13["figure_w"])
assert 3.8 <= H / A <= 4.0 and L == 115 / 2, (H / A, L)
# 割り箸の見込み: よく売っている長さの短い方 200mm・外筒の下に残す 30mm・内筒に貼る 20mm 以上
assert (sf.CHOPSTICK_LEN, sf.CHOPSTICK_GRIP, sf.CHOPSTICK_GLUE) == (200, 30, 20)
assert sf.check_range(V13) == [], [f.line() for f in sf.check_range(V13)]
assert sf.check_physics(V13) == [], [f.line() for f in sf.check_physics(V13)]
assert compose("slider_fan", SC["params"], SRC)[2] == []
# 既定値は変えていない（凍結の場面のため）。既定の形は tab のまま
assert sf.DEFAULTS["push_part"] == "tab" and sf.DEFAULTS["tube_height"] == 84 and sf.DEFAULTS["fold_count"] == 28
with tempfile.TemporaryDirectory() as d:
    r = subprocess.run([sys.executable, "-m", "omochae", "--scenario", str(ROOT / "examples/goraigo_v13.json"), "--out", f"{d}/v13"],
                       cwd=ROOT, env={"PYTHONPATH": str(ROOT / "src"), "PATH": "/usr/bin:/bin"}, capture_output=True, text=True)
    assert r.returncode == 0 and pathlib.Path(f"{d}/v13.pdf").exists(), r.stderr

# 2. 部品: 1 外筒・2 内筒・3 台・4 扇・5 像・6 受け。糸・竹串・溝・つまみ・穴・筒の紫の札は無い
by = {q.key: q for q in sf.parts(V13)}
by_place = {q.key: q for q in compose("slider_fan", SC["params"], SRC)[1]["parts"]}
# 台・像・受けの段は、右の列の扇の下に置く（左の列は外筒と内筒）
assert by_place["base"].y > by_place["fan"].y + by_place["fan"].height and by_place["base"].x > by_place["tube"].x + by_place["tube"].width
assert sorted((q.number, q.key, q.label) for q in by.values()) == [
    (1, "tube", "1 外筒"), (2, "pusher", "2 内筒"), (3, "base", "3 台"), (4, "fan", "4 扇"), (5, "figure", "5"), (6, "cradle", "6 受け")]
assert all(not q.holes and not q.cuts for q in by.values()), [(q.key, q.holes, q.cuts) for q in by.values() if q.holes or q.cuts]
# 札は外した（指示 ①）: 外筒の絵は白木の帯と地と角の 2 本線だけ（tests/test_slider_fan_colors.py が全部の形で見る）
assert {a.get("fill") for a in by["tube"].art if a["kind"] == "poly"} == {sf.WOOD, sf.WOOD_ALT, sf.WOOD_TOP, sf.WOOD_BOTTOM}
# 外形は 4 つの角と糊代の 2 つの角の 6 点（つまみの形は溝の切り込みで 4 点増える）
assert len(by["tube"].outline) == 6 and by["tube"].hide_folds and len(by["tube"].mountain) == 4 and not by["tube"].valley
assert len(by["pusher"].valley) == 4 and not by["pusher"].mountain and by["pusher"].height == L  # 内筒は破線の谷折り
# 割り箸を貼る位置の印: 刷った面（谷折りで筒の内）の 1 面目の真ん中に、割り箸の太さの点の線の長方形。台の糊代の下から内筒の下の手前まで
marks = [m for m in by["pusher"].art if m["kind"] == "mark"]
assert len(marks) == 1 and marks[0].get("closed"), by["pusher"].art
xs, ys = [x for x, _ in marks[0]["pts"]], [y for _, y in marks[0]["pts"]]
assert abs(min(xs) - (a / 2 - sf.CHOPSTICK_W / 2)) < 1e-9 and abs(max(xs) - (a / 2 + sf.CHOPSTICK_W / 2)) < 1e-9 and max(xs) < a
assert abs(min(ys) - (V13["base_glue"] + sf.CHOPSTICK_GAP)) < 1e-9 and L - 1 < max(ys) < L
assert len(by["base"].mountain) == 4 and not by["base"].valley  # 台は印の面を上にして糊代を下へ折る
n, w, h = int(V13["fold_count"]), V13["fold_width"], V13["fold_height"]
assert by["fan"].outline == [(0, 0), (h, 0), (h, n * w), (0, n * w)] and not by["fan"].glue  # 足の無い長方形
c = by["cradle"]
assert len(c.valley) == 2 and len(c.glue) == 3 and abs(c.width - sf.cradle_width(V13)) < 1e-9
assert abs(c.height - (2 * sf.CRADLE_FLAP + sf.cradle_depth(V13))) < 1e-9
# 像は両側から見た物（頭の上で折り返した鏡写し）: 頭の上の山折り 1 本・糊代は前の半分の足だけ・顔の絵が 2 つ
fig, fw, fh = by["figure"], V13["figure_w"], V13["figure_h"]
yf = fh * sf.FIGURE_OUTLINE[1][1]
assert len(fig.mountain) == 1 and not fig.valley and len(fig.glue) == 1, (fig.mountain, fig.glue)
(fx0, fy0), (fx1, fy1) = fig.mountain[0]
assert abs(fy0 - fy1) < 1e-9 and abs(fy0 - (fh - yf)) < 1e-9 and abs(fx1 - fx0) >= 2, fig.mountain  # 折り線は頭の上の平らな辺（幅 2mm 以上）
assert abs(fig.height - (2 * (fh - yf) + 5)) < 1e-6, fig.height  # 2 つの半分と足の糊代
assert sum(1 for item in fig.art if item.get("fill") == sf.FACE) == 2  # 顔は前と後ろの両方
assert fig.label_xy[1] > fh - yf  # 札「5」は前の半分（折り線より下）
# 後ろの半分は前の半分の鏡写し: 前の輪郭（足の線と足の糊代を除く。糊代は前の半分にだけある）を折り線で返した点が、全部、部品の輪郭にある
front = [(x, y) for x, y in fig.outline if fy0 + 1e-9 < y < 2 * (fh - yf) - 1e-9]
assert len(front) > 20
assert all(any(abs(x - qx) < 1e-6 and abs(2 * fy0 - y - qy) < 1e-6 for qx, qy in fig.outline) for x, y in front)
assert sorted((r["number"], r["key"]) for r in sf.bom(V13)) == [(1, "tube"), (2, "pusher"), (3, "base"), (4, "fan"), (5, "figure"), (6, "cradle"), (7, "stick")]
text = words(V13)
assert not any(k in text for k in ("糸", "竹串", "溝", "つまみ", "穴を")), text
mats = sf.materials(V13)
assert any(m.startswith("割り箸 1 本") and "200mm" in m for m in mats) and "セロハンテープ" in mats[1], mats
assert not any("受け" in m for m in mats), mats  # 6 受けは紙の部品で、1 枚目の紙の行に入る

# 3. 題と組み方: 作る順（切る → 部品ごとに折る → 貼る → 組む → 押し上げる）で、1 つの段に 1 つの動き。割り箸は内筒を筒にする前に貼る
assert sf.title(V13) == "内筒を下から押し上げる"
st = sf.steps(V13)
assert len(st) == 18 and st[0].startswith("刷った物差し") and st[1].startswith("部品を全部、実線で切る"), st
order = [next(i for i, x in enumerate(st) if x.startswith(head)) for head in
         ("1 外筒を、色の境で", "1 外筒の糊代を", "2 内筒を、破線で", "割り箸を、2 内筒の", "2 内筒の糊代を", "3 台の 4 つの糊代を", "3 台を、印のある",
          "4 扇を色の境で", "6 受けを、2 本の", "6 受けの底の面の裏を", "畳んだ 4 扇の下の端を", "5 像を、頭の上の", "5 像の足の糊代を",
          "4 扇を手で畳み", "1 外筒を片手で持ち", "割り箸をゆっくり引き下げる")]
assert order == sorted(order), order
assert "まだ貼らない" in st[4] and "セロハンテープ" in st[5] and "割り箸は筒の内に入る" in st[6], st[4:7]
assert "裏どうし" in st[13] and "両方に顔が出る" in st[13], st[13]
assert "片手で持ち" in st[-2] and "もう片方の手で割り箸を" in st[-2] and "ゆっくり押し上げる" in st[-2] and "開く" in st[-2], st[-2]
assert "ゆっくり引き下げる" in st[-1] and "筒に入る" in st[-1] and "外筒と割り箸を一緒に持つ" in st[-1], st[-1]
assert any("2 内筒の上の口に差し込み" in x and "内の面に貼る" in x for x in st) and any("6 受け" in x for x in st)

# 4. 3D の入口（python -m omochae.fold3d）は rise も組む: 見本の寸法は通り（0）、既定の寸法に形だけ rise を入れると型紙の検査で落ちる（3）。
#    中身の確かめは tests/test_goraigo_rise_3d.py
env3 = {"PYTHONPATH": str(ROOT / "src"), "PATH": "/usr/bin:/bin"}
r = subprocess.run([sys.executable, "-m", "omochae.fold3d", "--scenario", str(ROOT / "examples/goraigo_v13.json")], cwd=ROOT, env=env3, capture_output=True, text=True)
assert r.returncode == 0 and "閉じる 1 外筒" in r.stdout and "押し上げる 2 内筒" in r.stdout, (r.returncode, r.stdout, r.stderr)
with tempfile.TemporaryDirectory() as d:
    (pathlib.Path(d) / "rise.json").write_text(json.dumps({"push_part": "rise"}), encoding="utf-8")
    r = subprocess.run([sys.executable, "-m", "omochae.fold3d", "--template", "slider_fan", "--params", str(pathlib.Path(d) / "rise.json")],
                       cwd=ROOT, env=env3, capture_output=True, text=True)
assert r.returncode == 3 and "F5.stroke" in r.stderr, (r.returncode, r.stderr)

# 5. この形に効かない床は出ない（ほかの形の負の場面の寸法を v13 に足しても、足・穴・溝の床は出ない）
rise_floors = {"F5.fan_height", "F5.figure_height", "F5.stroke", "F5.slide_clearance", "F5.base_size", "F5.fan_thickness",
               "F5.figure_base", "F5.fan_clearance", "F5.fan_length", "F5.range"}
for extra in ({"pivot_above_rim": 0}, {"pivot_above_rim": 40}, {"hub": "rim"}, {"knob_width": 8}, {"stage_height": 40},
              {"fold_count": 6, "fold_width": 5, "fold_height": 40}, {"fan_length": 200}, {"paper_thickness": 1.2}):
    got = {f.floor for f in sf.check_physics({**V13, **extra}) + sf.check_range({**V13, **extra})}
    assert got <= rise_floors, (extra, got)


# 6. 落ちる寸法は、その床で落ちる（1 つの崩れに 1 つの床）
def floors(**extra):
    return [f.floor for f in sf.check_physics({**V13, **extra})]


assert floors(push_amount=30) == ["F5.fan_height"]                       # 受けの底＋扇の高さ 28.6＋2 に足りず、静かな時に扇が出る
assert floors(figure_h=30) == ["F5.figure_height"]                       # 像 30＋2 が押し上げる量 31 を超え、静かな時に像が出る
assert floors(push_amount=101) == ["F5.stroke"]                          # 押し上げる量が筒の高さを超え、静かな時に台が筒の下に出る
assert floors(push_amount=79) == ["F5.stroke"]                           # 静かな時に外筒に入る 21 が内筒の一辺 22 より短く、傾く
msg = lambda **extra: [f.message for f in sf.check_physics({**V13, **extra})][0]
assert "台が筒の下に出る" in msg(push_amount=101) and "入らず" not in msg(push_amount=101)  # 2 つは文を分ける
assert "21mm しか入らず" in msg(push_amount=79)
assert floors(push_amount=78) == []                                       # 入る長さ 22 なら通る（境）
assert floors(pusher_height=26) == ["F5.stroke"] and "割り箸を内筒に貼る長さ 19mm" in msg(pusher_height=26)  # 貼る長さ 19 が 20 に足りない
assert floors(pusher_height=27) == []                                     # 貼る長さ 20 なら通る（境）
sf.CHOPSTICK_LEN, keep = 120, sf.CHOPSTICK_LEN  # 短い割り箸の見込みなら、開いた位置で外筒の下に 30mm 残らない（範囲の寸法では 200mm で落ちない）
try:
    assert floors() == ["F5.stroke"] and "外筒の下へ 27mm しか出ず" in msg(), msg()
finally:
    sf.CHOPSTICK_LEN = keep
assert floors(pusher_side=25, base_side=24.5) == ["F5.slide_clearance"]  # 内筒が外筒の一辺−1 より小さくない
assert floors(base_side=22) == ["F5.base_size"]                          # 台が内筒と同じ大きさで、糊代の紙 2 枚が口に入らない
assert floors(base_side=20.9) == ["F5.base_size"]                        # 台が内筒より 1mm を超えて小さく、糊代が壁に届かない
assert floors(base_side=21) == [] and floors(base_side=21.7) == []       # 境（内筒−1 と、内筒−紙 2 枚）
assert floors(fold_count=24) == ["F5.fan_clearance"]                     # 24 枚 × 4mm は 192° で、ほぼ 180° に収まらない
assert floors(figure_w=25) == ["F5.figure_base"]                         # 像の幅 25 が筒の一辺−2 を超え、筒に入らない
# 右の列の段の下に文字が重ならない: 筒が短く扇が長い寸法（段が左の列の筒より下まで来る）でも、配置の検査が通る
short = {**SC["params"], "tube_height": 70, "pusher_height": 60, "push_amount": 48, "fold_count": 35, "fold_height": 45}
assert sf.check_physics({**sf.DEFAULTS, **short}) == [], [f.line() for f in sf.check_physics({**sf.DEFAULTS, **short})]
_, lay, fs = compose("slider_fan", short, SRC)
assert fs == [], [f.line() for f in fs]
pl = {q.key: q for q in lay["parts"]}
assert pl["base"].x > pl["tube"].x + pl["tube"].width and pl["figure"].y + pl["figure"].height > pl["pusher"].y + pl["pusher"].height
# 既定の寸法（つまみの形の寸法）に形だけ rise を入れると床に落ちる。rise は寸法ごと書く（見本は examples/goraigo_v13.json）
assert "F5.stroke" in [f.floor for f in sf.check_physics({**sf.DEFAULTS, "push_part": sf.RISE})]
print("ok 御来迎の内筒を下から押し上げる形（rise）と次の組の見本（v13）")
