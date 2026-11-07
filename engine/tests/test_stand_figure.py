"""立てる姿の床（F5.stand）の式の要所と、姿と出典の組を確かめる。

なぜ組を試験で見るか: 雛形は、どの出典（--source）が選ばれたかを知らない。姿の値と出典の記録は場面が組にして渡すので、
組を間違えると、印は正しく刷られても絵と出典が食い違う。下の PAIRS は雛形の FIGURES とは別に手で書いた表で、両方が合う事を見る。
"""
import itertools
import json
import math
import pathlib
import re

from shapely.geometry import Polygon

from omochae.compose import TEMPLATES, compose
from omochae.floors import check_bom
from omochae.templates import stand_figure as t

ROOT = pathlib.Path(__file__).resolve().parents[1]
P = t.filled(dict(t.DEFAULTS))
assert TEMPLATES["stand_figure"] is t, "templates/ に置けば登録される"
assert t.check_physics(P) == [] and not t.check_range(P)

# 姿と出典（コマ・頁）の組。調べの推定の名の順（担当の一覧の優先の順）。
PAIRS = {
    "inu": (16, "L"), "uma": (17, "L"), "mimizuku": (27, "L"), "kamibina": (12, "L"), "hagoita": (23, "L"),
    "tako_ji": (24, "L"), "tako_oni": (24, "L"),
    "tsuchi_usagi": (13, "L"), "tsuchi_kame": (13, "L"), "tsuchi_hato": (13, "L"),
    "shitadashi": (8, "R"), "kubi": (17, "R"), "fukumen": (11, "L"), "mino": (10, "L"), "suwari": (26, "L"),
    "kukurizaru": (30, "L"), "fushimi": (27, "R"), "miya": (9, "R"), "chigibako": (11, "R"),
    "tokkuri": (15, "L"), "suribachi": (21, "L"), "binkake": (26, "R"), "chagama": (30, "R"),
    "tawara": (22, "R"), "hamayumi": (15, "R"), "yamaneko": (18, "R"), "hebi": (20, "L"), "nobori": (31, "R"),
    "sakana": (12, "R"), "mochibana": (21, "R"), "torisao": (5, "L"), "torisao_hoso": (28, "L"), "kidachi": (5, "R"),
    "fumei_tama": (13, "R"), "fumei_tsutsu": (19, "R"),
}
assert set(PAIRS) == set(t.FIGURES) == set(t.FORMS), sorted(set(PAIRS) ^ set(t.FIGURES))
for fig, (canvas, side) in PAIRS.items():
    sid = f"NDL-1187053-R{canvas:07d}-{side}-stand_figure"
    assert t.FIGURES[fig]["source"] == sid, fig
    src = json.loads((ROOT / "data/sources" / f"{sid}.json").read_text(encoding="utf-8"))
    assert (src["source_id"], src["canvas"], src["side"]) == (sid, canvas, side), fig
    assert src["image_url"].endswith(f"R{canvas:07d}/{src['crop_region']}/1600,/0/default.jpg"), fig
    assert src["crop_status"] == "unverified"
# 既定の姿（犬張子）と既定の出典は組
assert t.SOURCE == t.FIGURES[t.DEFAULTS["figure"]]["source"]
# 不明の 2 つは、名を作らず「不明（〜の形）」と書く
assert all(t.FIGURES[f]["title"].startswith("不明（") and t.FIGURES[f]["title"].endswith("形）") for f in ("fumei_tama", "fumei_tsutsu"))

# 場面の組: この雛形の場面は全部、姿と出典が PAIRS の組。姿ごとに正の場面が 1 本ある
scen = {}
for f in sorted((ROOT / "tests/frozen/scenarios").glob("stand_figure_*.json")):
    sc = json.loads(f.read_text(encoding="utf-8"))
    assert sc["template"] == "stand_figure", f.name
    fig = sc["params"]["figure"]
    if "F1.source" in sc["expect"]["floors"]:
        # 組の誤りを落とす負の場面だけは、わざと組でない。組でない事を確かめる
        assert sc["source_id"] != t.FIGURES[fig]["source"], f.name
        continue
    assert sc["source_id"] == t.FIGURES[fig]["source"], f"{f.name}: 姿 {fig} と出典 {sc['source_id']} が組でない"
    if sc["expect"]["rc"] == 0:
        scen[fig] = sc
assert set(scen) == set(t.FIGURES), sorted(set(t.FIGURES) - set(scen))

# 姿ごと: 外形は 1 つの多角形、勧める立て方と寸法で床に落ちず、配置まで通る。部品は部品表に載り、key は英小文字だけ
for fig, f in t.FIGURES.items():
    for stand in t.STANDS:
        p = {**P, "figure": fig, "stand": stand, **f.get("suggest", {})}
        g = t.geometry(p)
        assert g["body"].geom_type == "Polygon" and g["body"].is_valid and g["contacts"], fig
        assert abs(g["H"] - f["height"]) < 1e-6 and abs(g["body"].bounds[3] - g["H"]) < 1e-6, fig
        assert check_bom(t.bom(p), t.parts(p)) == [], (fig, stand)
        assert all(re.fullmatch(r"[a-z]+", q.key) for q in t.parts(p)), fig
    # 場面の寸法は、compose と同じく DEFAULTS に重ねて、その姿の勧めで埋める（P は犬張子の勧めで埋まっているので、重ねない）
    p = t.filled({**t.DEFAULTS, **scen[fig]["params"]})
    assert p["stand"] == f["stand"] and t.check_physics(p) == [], (fig, t.check_physics(p))
    _, layout, fails = compose("stand_figure", scen[fig]["params"], json.loads((ROOT / "data/sources" / f"{f['source']}.json").read_text(encoding="utf-8")))
    assert fails == [], (fig, [x.line() for x in fails])

# 裏の姿は表の左右を返した物（背中合わせに貼ると縁がそろう）
front, back = t.parts(P)[:2]
W = t.geometry(P)["W"]
assert Polygon(back.outline).symmetric_difference(Polygon([(W - x, y) for x, y in front.outline])).area < 1e-6
assert [q.key for q in t.parts({**P, "back": 0})] == ["front", "tab"] and [q.key for q in t.parts(P)] == ["front", "back", "tab"]

# 脚の三角: 付け根（姿の上、下の縁から s・後ろへ LEAN_DEG 傾く）と脚の先（床の上、奥行き c）の距離は脚の長さ、付け根の角は開きの角
e = t.easel(P)
lean = math.radians(t.LEAN_DEG)
hinge = (e["s"] * math.sin(lean), e["s"] * math.cos(lean))
foot = (e["c"], 0.0)
assert abs(math.dist(hinge, foot) - P["tab_length"]) < 1e-9
v1, v2 = (-hinge[0], -hinge[1]), (foot[0] - hinge[0], foot[1] - hinge[1])
ang = math.degrees(math.acos((v1[0] * v2[0] + v1[1] * v2[1]) / (math.hypot(*v1) * math.hypot(*v2))))
assert abs(ang - P["tab_angle"]) < 1e-9
g = t.geometry(P)
m = t.margin(g)
# 余白は背が高いほど広い（同じ傾きで重心が大きく動く）
assert t.margin(t.geometry({**P, "scale": 1.4})) > m
# 開きの角が狭いと足の形が浅い（脚が同じ長さでも倒れる）
assert t.easel({**P, "tab_angle": 15})["c"] < e["c"]

# 脚は 1 本の帯を三角に閉じた物。刷る帯は上から、閉じる糊代・つなぎ・脚・背に貼る面。折り線 3 本は山折りで、谷折りは無い
# （凡例の谷折りは刷った面がへこむ。色の面を外にして折り、糊代の斜線が貼る相手を向くのは山折り）
tab = next(q for q in t.parts(P) if q.key == "tab")
k = min(t.CLOSE_GLUE, P["tab_glue"])
ys = sorted(a[1] for a, _ in tab.mountain)
assert tab.valley == [] and len(ys) == 3
assert abs(ys[0] - k) < 1e-9 and abs((ys[1] - ys[0]) - e["r"]) < 1e-9 and abs((ys[2] - ys[1]) - P["tab_length"]) < 1e-9
assert abs((tab.height - ys[2]) - P["tab_glue"]) < 1e-9
spans = sorted((min(y for _, y in gl), max(y for _, y in gl)) for gl in tab.glue)
assert len(spans) == 2 and max(abs(a - b) for a, b in zip(spans[0] + spans[1], (0, k, ys[2], tab.height))) < 1e-9, spans
# 閉じる糊代は貼る面より短い（組み方の文が「短い糊代」「長い糊代の面」で見分けさせる）。貼る面の下限もそれより長い
assert k < P["tab_glue"] and t.RANGES["tab_glue"][0] > t.CLOSE_GLUE


# 机に着く姿勢を、式（余弦定理の重ね）でなく、三角を姿の背に貼ったまま姿を傾けていく二分で別に解く（式を式で確かめないため）。
# 付け根は姿に沿って s、貼る面の下の端は s − w。脚の先は「付け根から L・下の端から r」の 2 つの円の交わりのうち、後ろの側
def settle(s, w, L, r):
    along = (L * L - r * r + w * w) / (2 * w)  # 付け根から、貼る面に沿って下へ
    off = math.sqrt(L * L - along * along)  # 貼る面から後ろへ
    def tip(a):
        return ((s - along) * math.sin(a) + off * math.cos(a), (s - along) * math.cos(a) - off * math.sin(a))
    lo, hi = -math.pi / 2 + 1e-6, math.pi / 2 - 1e-6
    for _ in range(80):  # 傾けるほど脚の先は下がる。机（高さ 0）に着く傾きを探す
        a = (lo + hi) / 2
        lo, hi = (a, hi) if tip(a)[1] > 0 else (lo, a)
    return math.degrees(lo), tip(lo)[0]


# 寸法どおりの形（ずれ 0）は、寸法の開きの角・奥行き・傾きに戻る
x0 = t.easel_at(P)
assert max(abs(x0["angle"] - P["tab_angle"]), abs(x0["c"] - e["c"]), abs(x0["lean"] - t.LEAN_DEG)) < 1e-9, x0
# 手のずれの端の組み合わせ（折り目 3 本と閉じる位置が ±FOLD_TOL、貼る高さが ±GLUE_TOL）は 32 個で、先頭は寸法どおり。
# どの組み合わせでも、式の傾きと奥行きは、別に解いた姿勢と合う
assert len(t._SLIPS) == 33 and t._SLIPS[0] == ((0.0, 0.0, 0.0, 0.0), 0.0)
for (e1, e2, e3, e4), up in t._SLIPS:
    x = t.easel_at(P, (e1, e2, e3, e4), up)
    want = settle(e["s"] + up, P["tab_glue"] - e3 + e4, P["tab_length"] + e3 - e2, e["r"] + e2 - e1)
    assert abs(x["lean"] - want[0]) < 1e-6 and abs(x["c"] - want[1]) < 1e-6, ((e1, e2, e3, e4), up, x, want)
# 効き方の向き: 低く貼る・脚が長く折れると姿が立ち、高く貼る・つなぎが長く折れると姿が寝る
assert t.easel_at(P, up=-t.GLUE_TOL)["lean"] < x0["lean"] < t.easel_at(P, up=t.GLUE_TOL)["lean"]
assert t.easel_at(P, (0, -t.FOLD_TOL, t.FOLD_TOL, 0))["lean"] < x0["lean"]  # 脚だけ 2·FOLD_TOL 長い（つなぎと貼る面が FOLD_TOL ずつ短い）
assert t.easel_at(P, (-t.FOLD_TOL, t.FOLD_TOL, t.FOLD_TOL, 0))["lean"] > x0["lean"]  # つなぎだけ 2·FOLD_TOL 長い（貼る面が FOLD_TOL 短い）
# 3 辺で三角が閉じない長さは None（つなぎの上の折り目を大きくずらして、つなぎを 貼る面 + 脚 より長くする）
assert t.easel_at(P, (-(P["tab_glue"] + P["tab_length"]), 0, 0, 0)) is None
# 重心の奥行きは、姿（表と裏の 2 枚）と脚の帯（1 枚）を面積で重み付けした物。別に解いた姿勢（settle）から、付け根・貼る面の下の端・
# 脚の先の点を置き、帯の 4 つの面の真ん中の奥行きを点の座標から出して比べる。寸法どおりの形だけでなく、ずれた 32 の形でも合う
low = (e["h"] * math.sin(lean), e["h"] * math.cos(lean))
assert abs(math.dist(foot, low) - e["r"]) < 1e-9
def com_by_points(q, s_, w_, L_, r_):
    a, c_ = settle(s_, w_, L_, r_)
    a = math.radians(a)
    B, D, C = (s_ * math.sin(a), s_ * math.cos(a)), ((s_ - w_) * math.sin(a), (s_ - w_) * math.cos(a)), (c_, 0.0)
    kk = min(t.CLOSE_GLUE, q["tab_glue"])
    faces = [(w_, (B[0] + D[0]) / 2), (L_, (B[0] + C[0]) / 2), (r_, (C[0] + D[0]) / 2), (kk, D[0] + kk / 2 * math.sin(a))]
    gq = t.geometry(q)
    fig_w, strip_w = gq["body"].area * t.layers(q), q["tab_width"] * sum(n for n, _ in faces)
    return (fig_w * gq["zc"] * math.sin(a) + q["tab_width"] * sum(n * x for n, x in faces)) / (fig_w + strip_w)
for (e1, e2, e3, e4), up in t._SLIPS:
    want = com_by_points(P, e["s"] + up, P["tab_glue"] - e3 + e4, P["tab_length"] + e3 - e2, e["r"] + e2 - e1)
    assert abs(t.easel_at(P, (e1, e2, e3, e4), up)["com"] - want) < 1e-6, ((e1, e2, e3, e4), up)
# 帯は姿の後ろにあるので、重心は姿だけの時より後ろ。表だけ（back 0）だと姿が軽く、もっと後ろへ寄る
assert g["zc"] * math.sin(lean) < x0["com"] < t.easel_at({**P, "back": 0})["com"]

# 寸法そのものが悪い時は、ずれの話をせずに落とす（開きが狭く、寸法どおりでも後ろへ倒れる）
fs = t.check_physics({**P, "tab_angle": 15})
assert [(f.floor, f.where) for f in fs] == [("F5.stand", "脚")] and "後ろへ倒れる" in fs[0].message and "ずれた時" not in fs[0].message, fs
# 寸法どおりなら立つが、手のずれで倒れる脚は落とす。木菟に短めの脚（36mm）は、ずれた時に後ろへ倒れる
M = t.filled({**t.DEFAULTS, "figure": "mimizuku"})
short = {**M, "tab_length": 36, "tab_glue": 33}
x = t.easel_at(short)
assert x["com"] >= t.margin(t.geometry(M)) and x["c"] - x["com"] >= t.margin(t.geometry(M)), x
fs = t.check_physics(short)
assert [(f.floor, f.where) for f in fs] == [("F5.stand", "脚")] and "後ろへ倒れる" in fs[0].message and "ずれた時" in fs[0].message, fs
# 貼る面が短いと、同じずれで姿の傾きが大きく変わり、前へ倒れる側に入る（12mm は落ち、16mm は通る）
lean_span = lambda q: max(x["lean"] for x in (t.easel_at(q, f, u) for f, u in t._SLIPS)) - min(x["lean"] for x in (t.easel_at(q, f, u) for f, u in t._SLIPS))
assert lean_span({**M, "tab_glue": 12}) > lean_span({**M, "tab_glue": 16}) > lean_span(M)
fs = t.check_physics({**M, "tab_glue": 12})
assert [(f.floor, f.where) for f in fs] == [("F5.stand", "脚")] and "前へ倒れる" in fs[0].message and "ずれた時" in fs[0].message, fs
assert t.check_physics({**M, "tab_glue": 16}) == [] and t.check_physics(M) == []
# 前の既定の寸法（脚 40mm・開き 30°・貼る面 13mm）は、今の傾き 20° では足の奥行きが浅く、ずれた時に後ろへ倒れる側で落ちる
fs = t.check_physics({**P, "tab_length": 40, "tab_glue": 13, "tab_angle": 30})
assert [(f.floor, f.where) for f in fs] == [("F5.stand", "脚")] and "後ろへ倒れる" in fs[0].message and "ずれた時" in fs[0].message, fs
# 貼る面が姿の背に収まらない: 犬の背より上まで届く長い脚、腹の下（脚の間の空き）へ出る長い貼る面。
# 貼る高さのずれ ±GLUE_TOL を含めて見るので、ちょうど収まる長さより GLUE_TOL 短い長さまでしか通らない
fs = t.check_physics({**P, "tab_length": 70})
assert any("背に収まらない" in f.message for f in fs), fs
assert any("背に収まらない" in f.message for f in t.check_physics({**P, "tab_glue": 23}))
assert t.check_physics({**P, "tab_glue": 21}) == []
# 下の縁が細い物は、脚では横へ倒れる（羽子板の柄）
fs = t.check_physics({**P, "figure": "hagoita", "tab_length": 90, "tab_glue": 10})
assert any("横へ倒れる" in f.message for f in fs), fs

# 溝: 隙間 = 溝の幅 − 紙の厚み × 重ねた枚数。狭いと差せない、広いと傾きが MAX_WOBBLE を越える
# 台の形は覆面の人形（勧めの値）で見る。犬張子は重心が腹の下（足の無い所）にあり、台では舌が重心の下に来ないので脚で立てる
B = t.filled({**t.DEFAULTS, "figure": "fukumen"})
assert B["stand"] == "base" and t.check_physics(B) == []
assert any("ねじれる" in f.message for f in t.check_physics(t.filled({**P, "stand": "base", "slot_length": 12})))
# 舌が 2 つの足にまたがると、足の間が舌と胴で囲まれて紙で埋まる。黙って埋めず「またぐ」で落とす。部品は落ちた寸法でも返る（check_bom が呼ぶ）
fs = t.check_physics(t.filled({**P, "stand": "base", "slot_length": 30}))
assert any(f.where == "舌" and "またがり" in f.message for f in fs), fs
front_web = next(q for q in t.parts(t.filled({**P, "stand": "base", "slot_length": 30})) if q.key == "front")
assert Polygon(front_web.outline).is_valid and not Polygon(front_web.outline).interiors
th, tp = 2 * B["paper_thickness"], B["paper_thickness"]
# 差せるかは狭く切れた側で見る: 隙間が MIN_CLEAR（毛羽 0.1mm ＋ 狭い側のずれ 2·CUT_TOL）に足りないと差せない
assert abs(t.MIN_CLEAR - (0.1 + 2 * t.CUT_TOL)) < 1e-9
assert t.wobble_deg({**B, "slot_width": th + t.MIN_CLEAR - 0.01}) is None
# 溝は手で帯を切り取れる幅（1mm 以上）で、隙間の下限は切るずれを含む。組み方は「帯を切り取る」と言う
assert t.RANGES["slot_width"][0] >= 1.0 and t.MIN_CLEAR >= 0.4
assert any("帯" in s and "切り取る" in s and "1 本の切れ目にしない" in s for s in t.steps(B))
# 表だけ（back 0）なら紙 1 枚なので、2 枚では差せない溝にも入る
narrow = th + t.MIN_CLEAR - 0.1
assert t.wobble_deg({**B, "slot_width": narrow}) is None and t.wobble_deg({**B, "back": 0, "slot_width": narrow}) is not None

# 2 つの高さで挟む前提を、展開図と舌の形から確かめる
from shapely.geometry import LineString
net = t.base_net(B)
assert len(net.cuts) == 2 and Polygon(net.outline).is_valid
# 箱の折り線は全部山折り（色の面が外。糊代の斜線が壁の内を向く）。組み方も山折りと言う
assert net.valley == [] and len(net.mountain) == 12
assert all(Polygon(net.outline).buffer(1e-6).contains(LineString([a, b])) for a, b in net.mountain)
assert any("部品 3 台の箱を一点鎖線で山折り" in s and "色の面が外" in s for s in t.steps(B)) and not any("谷折り" in s for s in t.steps(B) + t.steps(P))
Hb, D, g0 = B["base_height"], B["base_depth"], B["base_glue"]
Y2, Y3 = g0 + D, g0 + D + Hb
(tx, ty, tw_, th_), (bx, by, bw, bh_) = sorted(net.cuts, key=lambda c: c[1])
# 閉じると、上の面（後ろの壁の上の縁 Y2 で倒す）の奥行きは Y2 − y、底の面（後ろの壁の下の縁 Y3 から）の奥行きは y − Y3。上下の溝がそろう
assert abs((Y2 - (ty + th_ / 2)) - ((by + bh_ / 2) - Y3)) < 1e-9 and abs(tx - bx) < 1e-9 and (tw_, th_) == (bw, bh_)

# 舌の先が底の溝を抜けて机に届く事を、刷る外形から見る: 刷った舌は 箱の高さ + TONGUE_EXTRA で tongue() と同じ長さ。
# TONGUE_EXTRA > BOX_TOL なので、箱が BOX_TOL 高く折れても先が机に着き、姿の下の縁は上の面から浮く（縁が面に乗ると先が浮いて、上の溝 1 つの形になる）。
# この関係は寸法に依らないので check_physics には無く、ここで定数として見る
front = next(q for q in t.parts(B) if q.key == "front")
H = t.geometry(B)["H"]
reach = max(y for _, y in front.outline) - H  # 刷った舌の、姿の下の縁から下の長さ
assert abs(reach - (Hb + t.TONGUE_EXTRA)) < 1e-9 and abs(t.tongue(B)[2] - reach) < 1e-9, reach
assert t.TONGUE_EXTRA > t.BOX_TOL and reach > Hb + t.BOX_TOL
# 傾きの上限を、紙の厚み th の板が 2 枚の紙の溝（広く切れた幅 sw + 2·CUT_TOL。真ん中の高さ tp/2 と Hb − BOX_TOL − tp/2）を通る形から
# 数で解き、式（wobble_deg）と比べる。式を式で確かめないため
def max_tilt(z1, z2, sw, thick):
    lo, hi = 0.0, math.pi / 2 - 1e-6
    for _ in range(60):  # 板の両の面が、2 つの溝の縁の内に収まる一番大きい傾き
        a = (lo + hi) / 2
        span = thick / math.cos(a) + (z2 - z1) * math.tan(a)
        lo, hi = (a, hi) if span <= sw else (lo, a)
    return math.degrees(lo)
sw = B["slot_width"]
assert abs(max_tilt(tp / 2, Hb - t.BOX_TOL - tp / 2, sw + 2 * t.CUT_TOL, th) - t.wobble_deg(B)) < 0.1, (max_tilt(tp / 2, Hb - t.BOX_TOL - tp / 2, sw + 2 * t.CUT_TOL, th), t.wobble_deg(B))
# 上の溝 1 つだけ（紙 1 枚の厚みの間で挟む）では、ほぼ倒れる。底の溝が要る理由
assert max_tilt(0, tp, sw, th) > 45
# 緩い溝の境: 広く切れた側と低く折れた箱で MAX_WOBBLE を越える幅で落ち、少し狭い幅で通る
loose = th + (Hb - t.BOX_TOL - tp) * math.tan(math.radians(t.MAX_WOBBLE)) - 2 * t.CUT_TOL + 0.05
assert any("ぐらつく" in f.message for f in t.check_physics({**B, "slot_width": loose}))
assert t.check_physics({**B, "slot_width": loose - 0.1}) == []
# 切るずれ・折るずれを見ない時の上限の少し内（前の式なら通る幅）でも、今の式では落ちる
gap_ok = (Hb - tp) * math.tan(math.radians(t.MAX_WOBBLE)) - 0.05
assert any("ぐらつく" in f.message for f in t.check_physics({**B, "slot_width": th + gap_ok}))
# 姿だけを変えた既定（勧めの値）は、どの台の姿も、溝が広く切れて箱が低く折れた側で通る（compose の試験で 35 とも通る）
for fig, f in t.FIGURES.items():
    if f["stand"] == "base":
        assert t.wobble_deg(t.filled({**t.DEFAULTS, "figure": fig})) <= t.MAX_WOBBLE, fig
# 溝の長さの下限（RANGES）は、舌の幅（溝 − 2·SLOT_END）から両側の余白 MIN_MARGIN を引いても窓が残る長さ。
# 短いと、重心が舌の真ん中にぴたり来る姿しか横の検査を通らない。下限の溝でも、重心が真ん中に来る姿（覆面の人形）は通る
assert t.RANGES["slot_length"][0] - 2 * t.SLOT_END - 2 * t.MIN_MARGIN > 0
assert t.check_physics({**B, "slot_length": t.RANGES["slot_length"][0]}) == [], t.check_physics({**B, "slot_length": t.RANGES["slot_length"][0]})
# 倒れるかは、軸（舌の先・机の上）から測る。低い亀でも、高い箱で奥行きが浅いと落ちる（姿の下の縁から測ると通っていた）
K = t.filled({**P, "figure": "tsuchi_kame", "stand": "base", "base_depth": 15, "base_height": 30, "slot_width": 2.9})
assert any(f.where == "台" for f in t.check_physics(K)), t.check_physics(K)
# 横: 姿の下の縁は浮くので、横に支えるのは舌の幅だけ。重心が余白 MIN_MARGIN を持って舌の幅に入らないとねじれる
# 犬張子を台に: 舌は前の足の下までしか寄れず、重心（腹の下）が舌の幅の外
S = t.filled({**P, "stand": "base", "slot_length": 12})
xs, ws, _ = t.tongue(S)
assert not (xs - ws / 2 + t.MIN_MARGIN <= t.geometry(S)["cx"] <= xs + ws / 2 - t.MIN_MARGIN)
assert t.check_physics(t.filled({**t.DEFAULTS, "figure": "shitadashi"})) == []
# 余白の境: 重心がちょうど舌の端にある（余白 0）と落ちる。千木箱の既定では、重心は舌の幅の内に余白を持つ
C = t.filled({**t.DEFAULTS, "figure": "chigibako"})
xc, wc, _ = t.tongue(C)
assert xc - wc / 2 + t.MIN_MARGIN <= t.geometry(C)["cx"] <= xc + wc / 2 - t.MIN_MARGIN
# 舌は姿の下の縁と半分以上つながる。羽子板の柄（約 8.5mm）に既定の長い溝の舌は折れ、短い溝なら通る
assert any(f.where == "舌" for f in t.check_physics({**B, "figure": "hagoita", "slot_length": 30}))
assert t.check_physics(t.filled({**t.DEFAULTS, "figure": "hagoita"})) == []
# 溝は箱の縁から SLOT_EDGE 内に収まる
assert any("縁まで" in f.message for f in t.check_physics({**B, "slot_length": B["base_length"] - 2 * t.SLOT_EDGE + 1}))
# 台が小さいと、重心が台の縁に近く倒れる
assert any(f.where == "台" for f in t.check_physics({**B, "base_depth": 15, "base_length": 30, "slot_length": 20, "scale": 1.5}))
# 脚の横の位置（重心の真後ろ）を組み方で言う（裏の印が無い時）
assert any(f"左の端から {t.geometry(P)['cx']:.0f}mm" in s for s in t.steps({**P, "back": 0}))

# 範囲: back は整数の 0 か 1（true/false・1.0 はほかの寸法と同じく型で落とす）、姿と立て方は一覧の値だけ
assert [f.floor for f in t.check_range({**P, "back": 0.5})] == ["F5.range"]
assert all([f.where for f in t.check_range({**P, "back": b})] == ["back"] for b in (True, False, 1.0, 0.0, 2))
assert t.check_range({**P, "back": 0}) == [] and t.check_range({**P, "back": 1}) == []
assert [f.floor for f in t.check_range({**P, "stand": "hang"})] == ["F5.range"]
# 知らない姿は、埋まらなかった既定（stand の None）を重ねて落とさず、姿の名の誤り 1 つだけで落とす（埋める前の DEFAULTS で見る）
assert [f.where for f in t.check_range({**t.DEFAULTS, "figure": "no_such"})] == ["figure"]
# 台の糊代は壁の高さ − 1mm まで（高いと展開図で隣の糊代と重なる）。溝の傾きが通る高さ 12（紙 0.25mm で隙間を詰める）で、糊代だけを変えて見る
G = {**B, "base_height": 12, "paper_thickness": 0.25}
assert any(f.where == "台" and "収まらない" in f.message for f in t.check_physics({**G, "base_glue": 12}))
assert t.check_physics({**G, "base_glue": 11}) == [], t.check_physics({**G, "base_glue": 11})
# 狭い脚（RANGES の下限 6mm）では札を番号だけにし、札が脚からはみ出して別の検査で落ちない
narrow_src = json.loads((ROOT / "data/sources" / f"{t.SOURCE}.json").read_text(encoding="utf-8"))
_, _, fs = compose("stand_figure", {"figure": "inu", "tab_width": t.RANGES["tab_width"][0]}, narrow_src)
assert fs == [], [x.line() for x in fs]
assert next(q.label for q in t.parts({**P, "tab_width": 6}) if q.key == "tab") == "3"
assert next(q.label for q in t.parts(P) if q.key == "tab") == "3 脚"
# 形から出典を選ぶ表（SOURCES）は FIGURES の組と同じ。合わない出典は compose が F1.source で落とす
assert t.SOURCES == {k: f["source"] for k, f in t.FIGURES.items()}
_, _, fs = compose("stand_figure", {"figure": "uma", "stand": "easel"}, json.loads((ROOT / "data/sources" / f"{t.SOURCE}.json").read_text(encoding="utf-8")))
assert [f.floor for f in fs] == ["F1.source"], fs

# 脚の開きは三角の辺で決まるので、開きの物差し（前の部品 4）は刷らない。組み方の文は脚の先の来る所（c）を言い、手で広げさせない
assert all(q.number <= 3 for q in t.parts(P)) and [r["key"] for r in t.bom(P)] == ["front", "back", "tab"]
assert any(f"約 {e['c']:.0f}mm 後ろ" in s and "手で広げない" in s for s in t.steps(P))
# 裏の姿の四角い印は、貼る面の置き場（上の辺が付け根 s、下の辺が h）。裏は左右を返してあるので、横の真ん中は W − 重心の x
# （返し忘れると、犬張子では数 mm ずれる）
mark = next(q for q in t.parts(P) if q.key == "back").art[-1]
HP, WP, cxP = t.geometry(P)["H"], t.geometry(P)["W"], t.geometry(P)["cx"]
assert mark["kind"] == "mark" and abs(min(y for _, y in mark["pts"]) - (HP - e["s"])) < 1e-6 and abs(max(y for _, y in mark["pts"]) - (HP - e["h"])) < 1e-6
mx = [x for x, _ in mark["pts"]]
assert abs((min(mx) + max(mx)) / 2 - (WP - cxP)) < 1e-6 and abs(max(mx) - min(mx) - P["tab_width"]) < 1e-6 and abs(WP - 2 * cxP) > 1
# 裏の印が無い時（back 0）は、貼る高さを 0.1mm まで数で言う（1mm に丸めると、小さい姿では丸めの分で傾きが変わる）
assert any(f"机に着く縁から {e['h']:.1f}〜{e['s']:.1f}mm の高さ" in s for s in t.steps({**P, "back": 0}))
# 裏の印は切る線と紛れない位置の印で刷り、凡例に行が出る。裏の姿が無い時は印も無く、線を引く鉛筆を用意する物に言う
assert not any(a["kind"] == "line" and a.get("stroke") == t.INK and len(a["pts"]) >= 5 for a in next(q for q in t.parts(P) if q.key == "back").art)
assert not any(a["kind"] == "mark" for q in t.parts({**P, "back": 0}) for a in q.art)
# 印の色と同じ地の姿でも見えるように、印のすぐ下に薄い地を敷く
for fig in ("inu", "uma", "tawara"):
    art_back = next(q for q in t.parts(t.filled({**t.DEFAULTS, "figure": fig, "stand": "easel"})) if q.key == "back").art
    assert art_back[-1]["kind"] == "mark" and art_back[-2]["kind"] == "poly" and art_back[-2]["fill"] == t.PAPER, fig
    ground_x, mark_x = [x for x, _ in art_back[-2]["pts"]], [x for x, _ in art_back[-1]["pts"]]
    assert abs(min(ground_x) - min(mark_x)) < 1e-6 and abs(max(ground_x) - max(mark_x)) < 1e-6, fig  # 地は印と同じ所（裏は左右を返してある）
assert "鉛筆" in "".join(t.materials({**P, "back": 0})) and "鉛筆" not in "".join(t.materials(P))
assert "鉛筆" not in "".join(t.materials({**t.DEFAULTS, "figure": "hagoita", "stand": "base", "back": 0}))
assert any("部品 2 は無い" in s for s in t.steps({**P, "back": 0})) and not any("部品 2 は無い" in s for s in t.steps(P))
# 貼る面を先に背に貼り、後で三角を閉じる（閉じる糊代の折り目を、貼った面の下の端にそろえる）
st = t.steps(P)
i_glue = next(i for i, x in enumerate(st) if "長い糊代" in x and "四角い位置の印" in x and "押さえて乾かす" in x)
i_close = next(i for i, x in enumerate(st) if "三角を閉じる" in x and "折り目を端にそろえて" in x)
assert i_glue < i_close
assert "乾くまで立てない" in st[i_close] and any("定規を当てて線の真上で山折り" in x for x in st)
# 台の形: 舌が底の溝を通った事を、持ち上げて見させる（外れて箱の床で止まっても、浮きの差は紙の厚みだけで見分けられない）
st_b = t.steps(B)
assert any("箱を持ち上げて、底の溝から舌の先が出ている" in x for x in st_b)
# 箱は左右の壁の糊代を先に貼り、上の面を後で閉じる（先に閉じると残りの糊代に指が届かない）。のりは舌の先まで、付け根の角は切り過ぎない
box_step = next(x for x in st_b if "台の箱を一点鎖線" in x)
assert box_step.index("左右の壁の糊代 4 枚") < box_step.index("上の面を閉じて") < box_step.index("箱のゆがみを直して")
assert box_step.index("通し") < box_step.index("押し込まず") < box_step.index("箱のゆがみを直して")  # 舌を最初に通す所で、きつい時の事を言う
assert any("舌の先までのりを塗って" in x and "角で止める" in x for x in st_b)
assert any("角で止める" in x and "部品 2 は無い" in x for x in t.steps({**B, "back": 0}))
assert not any("舌" in x for x in t.steps(P))
# 組み方の文は、float と同じ行数まで（前のサイトの手順の紙の左の列で、「番号. 文」の形の同じ折り返しで数えた。手順の紙は廃止）
from omochae.templates.float import STEP_COL_W, STEP_LINES_MAX, STEP_SIZE
from omochae.textfit import wrap
for fig in t.FIGURES:
    for q in (t.filled({**t.DEFAULTS, "figure": fig}), t.filled({**t.DEFAULTS, "figure": fig, "back": 0})):
        n_lines = sum(len(wrap(f"{i}. {s_}", STEP_SIZE, STEP_COL_W)) for i, s_ in enumerate(t.steps(q), 1))
        assert n_lines <= STEP_LINES_MAX, (n_lines, fig, q["back"])
# 手順の番号は「手順 n:」、部品の番号は「部品 n」。表と裏は粗く切って貼ってから、実線で 2 枚いっしょに切る（縁と舌がそろう）
for q in (P, B, {**P, "back": 0}):
    st = t.steps(q)
    assert all(x.startswith(f"手順 {i + 1}: ") for i, x in enumerate(st)), st
    assert not any(re.search(r"(?<!部品 )(?<![\d.〜])\b[1-4] (表|裏|脚|台)", x) for x in st), st
assert any("粗く切り取る" in s for s in t.steps(P)) and any("2 枚いっしょに切る" in s and "舌がそろう" in s for s in t.steps(B))
assert not any("粗く" in s for s in t.steps({**P, "back": 0}))

# 姿だけを変えた入口（--params {"figure": X}）でも、その姿に勧める立て方と寸法が既定になって通る。書いた寸法は勝つ
for fig, f in t.FIGURES.items():
    src = json.loads((ROOT / "data/sources" / f"{f['source']}.json").read_text(encoding="utf-8"))
    p, _, fails = compose("stand_figure", {"figure": fig}, src)
    assert fails == [], (fig, [x.line() for x in fails])
    assert t.filled(p)["stand"] == f["stand"] and all(t.filled(p)[k] == v for k, v in f.get("suggest", {}).items()), fig
assert t.filled({**P, "figure": "hagoita", "slot_length": 30})["slot_length"] == 30
assert t.filled({**P, "figure": "hagoita", "stand": "easel"})["stand"] == "easel"
assert t.spec()["figures"]["hagoita"]["stand"] == "base" and t.spec()["figures"]["hagoita"]["slot_length"] == t.FIGURES["hagoita"]["suggest"]["slot_length"]

# 横から見た組み上がりの絵は、どの姿でも渡した枠（x 10〜50・y 20〜70）の内に収まる
for fig in t.FIGURES:
    sh = t.diagram(10, 20, 40, 50, {**t.DEFAULTS, "figure": fig})
    xs = [v for q in sh for kk, v in q.items() if kk in ("x1", "x2", "x")] + [q["x"] + q["w"] for q in sh if q["kind"] == "rect"]
    ys = [v for q in sh for kk, v in q.items() if kk in ("y1", "y2", "y")] + [q["y"] + q["h"] for q in sh if q["kind"] == "rect"]
    tiny = 1e-9  # 丸めの分
    assert min(xs) + tiny >= 10 and max(xs) - tiny <= 50 and min(ys) + tiny >= 20 and max(ys) - tiny <= 70, (fig, min(xs), max(xs), min(ys), max(ys))
# 脚の絵は 3 本の線（姿・脚・つなぎ）と机の線
assert sum(1 for q in t.diagram(10, 20, 40, 50, P) if q["kind"] == "line") == 4

# 姿の大きさ（scale）だけを変えても、勧めの寸法が姿に付いて来る: 脚の長さ・貼る面・溝の長さは同じ倍率（溝は舌の検査が通る窓の内）、
# 脚の幅は小さくする時だけ、台の奥行きは大きくする時だけ。書いた値はそのまま勝ち、1 倍は元の勧めのまま
small = t.filled({**t.DEFAULTS, "figure": "mimizuku", "scale": 0.75})
assert (small["tab_length"], small["tab_glue"], small["tab_width"]) == (36.0, 33.8, 10.5), small
assert (small["base_length"], small["base_depth"]) == (t.BASE_DEFAULTS["base_length"], t.BASE_DEFAULTS["base_depth"])
big = t.filled({**t.DEFAULTS, "figure": "hagoita", "scale": 1.25})
h1 = t.figure_defaults("hagoita")
assert big["base_depth"] == h1["base_depth"] * 1.25 and big["base_length"] == h1["base_length"] and big["tab_width"] == h1["tab_width"]
assert abs(big["slot_length"] - h1["slot_length"] * 1.25) < 0.051
assert abs(t.filled({**t.DEFAULTS, "figure": "hagoita", "scale": 0.8})["slot_length"] - h1["slot_length"] * 0.8) < 0.051
assert t.filled({**t.DEFAULTS, "figure": "mimizuku", "scale": 0.75, "tab_length": 40})["tab_length"] == 40
assert t.filled({**t.DEFAULTS, "figure": "mimizuku"}) == {**t.DEFAULTS, **t.figure_defaults("mimizuku"), "figure": "mimizuku"}
assert all(lo <= v <= hi for sc in t.RANGES["scale"] for f in t.FIGURES for k, (lo, hi) in t.RANGES.items()
           if isinstance(v := t.figure_defaults(f, sc).get(k), (int, float)))
# 倍率が数でない時は、埋める所では止まらず、範囲の検査が 1 つだけ落とす
assert [f.where for f in t.check_range({**t.DEFAULTS, "scale": "big"})] == ["scale"]
# 脚で立てる姿は、0.75 倍・0.9 倍（A4）と 1.25 倍（B4。大きい姿は A4 に入らない）で、倍率だけを書いて配置まで通る。
# 倍率を掛ける前は、0.75 倍で 35 のうち 19、1.25 倍で 21 の姿が落ちた
for sc, page in ((0.75, "A4"), (0.9, "A4"), (1.25, "B4")):
    for fig, f in t.FIGURES.items():
        if f["stand"] == "easel":
            src = json.loads((ROOT / "data/sources" / f"{f['source']}.json").read_text(encoding="utf-8"))
            _, _, fails = compose("stand_figure", {"figure": fig, "scale": sc}, src, page)
            assert fails == [], (sc, fig, [x.line() for x in fails])
# 台に差す姿も、0.9 倍では全部通る（魚の体の人形は、倍率どおりの溝だと重心が舌の窓をわずかに外れるので、窓の下限まで広げる）
bad = []
for fig, f in t.FIGURES.items():
    if f["stand"] == "base":
        src = json.loads((ROOT / "data/sources" / f"{f['source']}.json").read_text(encoding="utf-8"))
        if compose("stand_figure", {"figure": fig, "scale": 0.9}, src)[2]:
            bad.append(fig)
assert bad == [], bad
# 溝の窓の式を、本物の検査と比べる: 窓の内の溝で舌の検査（つながり・またぐ・重心が舌の幅の内）は落ちない。窓の外へ出ると落ちる。
# 窓が空の姿と倍率（溝をどうしても通らない）は勧めのままで舌の検査に落ちる
tongue_fails = lambda fig, sc, sl: [f for f in t.check_physics({**t.DEFAULTS, "figure": fig, "stand": "base", "scale": sc, "slot_length": sl}) if f.where == "舌"]
for fig, f in t.FIGURES.items():
    if f["stand"] == "base":
        for sc in (0.75, 0.8, 0.85, 0.9, 0.95, 1.05, 1.1, 1.2, 1.25, 1.35, 1.5):
            lo, hi = t._slot_window(fig, sc)
            lo, hi = max(lo, t.RANGES["slot_length"][0]), min(hi, t.RANGES["slot_length"][1])
            if lo <= hi:
                assert tongue_fails(fig, sc, lo) == [] and tongue_fails(fig, sc, hi) == [], (fig, sc, lo, hi)
                assert lo <= t.figure_defaults(fig, sc)["slot_length"] <= hi, (fig, sc)
                if lo - 0.5 >= t.RANGES["slot_length"][0]:
                    assert tongue_fails(fig, sc, lo - 0.5), (fig, sc, lo)
                if hi + 0.5 <= t.RANGES["slot_length"][1]:
                    assert tongue_fails(fig, sc, hi + 0.5), (fig, sc, hi)
            else:
                assert tongue_fails(fig, sc, t.figure_defaults(fig, sc)["slot_length"]), (fig, sc, lo, hi)
# 首人形の 0.87 倍以下は足の間が狭く、細い鳥の竿の 0.75 倍は足が細く、溝をどう書いても舌の検査を通らない（README の限り）。少し大きければ通る
assert all(tongue_fails(fig, sc, sl) for fig, sc in (("kubi", 0.87), ("torisao_hoso", 0.75)) for sl in (6, 6.5, 8, 12, 20, 40, 60))
assert tongue_fails("kubi", 0.88, 6) == [] and tongue_fails("torisao_hoso", 0.76, 6) == []
# 大きくする時の台の姿: 溝を窓に収めるので、覆面の人形・破魔弓・鳥の竿・魚の体の人形は B4 の 1.25 倍で勧めのまま通る
for fig in ("fukumen", "hamayumi", "torisao", "sakana"):
    src = json.loads((ROOT / "data/sources" / f"{t.FIGURES[fig]['source']}.json").read_text(encoding="utf-8"))
    assert compose("stand_figure", {"figure": fig, "scale": 1.25}, src, "B4")[2] == [], fig
assert [f.where for f in t.check_range({**t.DEFAULTS, "scale": 0.5})] == ["scale"]

# null は「勧めを使う」の意味なのは立て方と脚・台の寸法だけ。倍率と紙の厚みの null は名前を言って落とす。文字以外の姿の名も止まらない
for bad_p in ({"figure": "inu", "paper_thickness": None}, {"figure": "inu", "scale": None}, {"figure": "fukumen", "paper_thickness": None}):
    src = json.loads((ROOT / "data/sources" / f"{t.FIGURES[bad_p['figure']]['source']}.json").read_text(encoding="utf-8"))
    assert [f.floor for f in compose("stand_figure", bad_p, src)[2]] == ["F5.range"], bad_p
assert t.check_range({"figure": "inu", "stand": None, "tab_length": None}) == []  # 勧めで埋まる
assert [f.where for f in t.check_range({**t.DEFAULTS, "figure": ["inu"]})] == ["figure"]
# 舌を足の端へ寄せると、つながる長さは下限ちょうどになる。丸めで落ちない（下の 3 つは、許しを外すと丸めだけで落ちる）
for fig, sc, sl in (("chigibako", 0.86, 25.8), ("hebi", 0.77, 7.7), ("hebi", 1.11, 11.1)):
    assert not any("つながらず" in f.message for f in t.check_physics({**t.DEFAULTS, "figure": fig, "stand": "base", "scale": sc, "slot_length": sl})), (fig, sc, sl)
# 重心が舌の窓の端にある時の文は小数 2 桁（丸めた数だと「22.7mm が 20.5〜22.7mm に無い」と読める）
assert any(re.search(r"左の端から \d+\.\d\dmm）が舌の幅の内.*\d+\.\d\d〜\d+\.\d\dmm", f.message)
           for f in t.check_physics({**t.DEFAULTS, "figure": "sakana", "stand": "base", "scale": 0.9, "slot_length": 7.2}))
# 溝が下限の時は、短くしろと言わない（言われたとおりにすると範囲の検査で落ちる）
thin = [f.message for f in t.check_physics({**t.DEFAULTS, "figure": "kubi", "stand": "base", "slot_length": 6, "scale": 0.75})]
assert any("姿を大きく" in x for x in thin) and not any("溝を短く" in x for x in thin), thin

# 姿の形の覚えは上限つき（高さは連続の値なので、上限が無いと場面を回すほど増える）
assert t._shape.cache_info().maxsize is not None
# 表のとおり stand に base を書いた値で刷れる。勧めの寸法は脚で立てる物なので、そのままだと舌が足に合わず、紙にも入らない姿があった。
# 馬だけは、足の幅と重心の位置で舌の窓が空（下限が上限を越える）で、溝をどう変えても舌では立たない。
from omochae.compose import check_params  # noqa: E402

NO_TONGUE = {"uma"}
for fig, f in t.FIGURES.items():
    src = json.loads((ROOT / "data/sources" / f"{f['source']}.json").read_text(encoding="utf-8"))
    r = check_params(t.ID, {"figure": fig, "stand": "base"}, src)
    low, high = t._slot_window(fig, 1.0)
    if fig in NO_TONGUE:
        assert low > high and not r["passed"] and all("F5.stand" in e for e in r["errors"]), (fig, low, high, r)
    else:
        assert r["passed"], ("stand: base を書くと刷れない", fig, r["errors"])
        if f["stand"] != "base":
            assert low <= t.filled({"figure": fig, "stand": "base"})["slot_length"] <= high, fig
    # 勧めの立て方を書いても書かなくても同じ（勧めの紙を変えない）。書いた値はそのまま勝つ
    assert t.filled({"figure": fig}) == {**t.filled({"figure": fig, "stand": f["stand"]})}, fig
    assert t.filled({"figure": fig, "stand": "base", "slot_length": 30})["slot_length"] == 30, fig

# 表のとおり stand に easel を書いた値で刷れる。勧めが台の姿は下の縁が細いので、既定の脚では貼る面が背に収まらないか、横へ倒れる。
# 下の 11 種は、脚の寸法をどう変えても刷れない。式の余白は勧めが脚の姿と同じ物で、緩めない。
# 貼れない: 下が細い棒で、脚の一番細い幅でも貼る面が背に収まらない。倒れる: どの脚でも足の形の内に重心が余白を持って入らない。
# 両立しない: 貼れる脚と倒れない脚はあるが、同じ脚では両方を満たさない。
NO_EASEL = {"kubi": "貼れない", "torisao": "貼れない", "torisao_hoso": "貼れない",
            "hagoita": "倒れる", "chigibako": "倒れる", "hebi": "倒れる",
            "shitadashi": "両立しない", "hamayumi": "両立しない", "mochibana": "両立しない", "kidachi": "両立しない", "fumei_tama": "両立しない"}
for fig, f in t.FIGURES.items():
    src = json.loads((ROOT / "data/sources" / f"{f['source']}.json").read_text(encoding="utf-8"))
    r = check_params(t.ID, {"figure": fig, "stand": "easel"}, src)
    if fig not in NO_EASEL:
        assert r["passed"], ("stand: easel を書くと刷れない", fig, r["errors"])
        continue
    assert not r["passed"] and all("F5.stand" in e for e in r["errors"]), (fig, r)
    base = t.filled({**t.DEFAULTS, "figure": fig, "stand": "easel"})
    stick = stand = 0
    for w, length, glue, angle in itertools.product(range(6, 31, 6), range(10, 121, 20), (10, 30, 50), range(10, 61, 10)):
        fails = t.check_physics({**base, "tab_width": w, "tab_length": length, "tab_glue": glue, "tab_angle": angle})
        sticks = not any("貼る面" in x.message for x in fails)
        stands = not any("貼る面" not in x.message for x in fails)
        assert not (sticks and stands), ("通る脚がある。NO_EASEL から外して、勧めの寸法を持たせる", fig, w, length, glue, angle)
        stick += sticks
        stand += stands
    assert (NO_EASEL[fig] != "貼れない" or stick == 0) and (NO_EASEL[fig] != "倒れる" or stand == 0), (fig, stick, stand)
# 脚の勧めは 1 倍の値で、倍率を書いた値には重ねない。覆面の幅は 1 倍だと 22mm しか通らず、0.85 倍以下へ縮めると貼る面が背に収まらないので、前は通った値が落ちる。
fukumen_src = json.loads((ROOT / "data/sources" / f"{t.FIGURES['fukumen']['source']}.json").read_text(encoding="utf-8"))
for sc in (0.75, 0.8, 0.85):
    assert check_params(t.ID, {"figure": "fukumen", "stand": "easel", "scale": sc}, fukumen_src)["passed"], ("倍率を書いた脚が落ちる", sc)
for fig, f in t.FIGURES.items():
    if "suggest_easel" in f:
        for sc in (0.75, 0.9, 1.25, 1.5):
            assert t.figure_defaults(fig, sc, "easel") == t.figure_defaults(fig, sc), ("倍率を書いた脚に勧めを重ねた", fig, sc)

print("ok")
