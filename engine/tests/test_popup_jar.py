"""飛び出し人形の壺（popup_jar）の床の式の要所を、境目の寸法で確かめる。

なぜ境目で見るか: 床の式は「≦」と「<」の取り違えや、高さを測る原点の取り違えで、隣の寸法が通ったり落ちたりする。
式の前提（高さは箱の底から・案内は箱の高さ・摩擦の見込み MU）は雛形の docstring にある。
"""
import math

from shapely.geometry import Polygon

from omochae.floors import check_bom
from omochae.templates import popup_jar as pj


def floors(**kw):
    return sorted({f.floor for f in pj.check_physics({**pj.DEFAULTS, **kw})})


# 既定の寸法は、どちらの壺の形でも床を通る（刷る形を替えるだけで作れる）
for jar in pj.FORMS:
    assert floors(jar=jar) == [], jar
    p = {**pj.DEFAULTS, "jar": jar}
    assert check_bom(pj.bom(p), pj.parts(p)) == []
    for q in pj.parts(p):
        assert Polygon(q.outline).is_valid, (jar, q.key)

# 1. 隠れる: 静かな時の人形の上の端 = 箱の高さ + 足 + 人形の高さ ≦ 口の高さ − HIDE_MARGIN（等号は通る）
d = pj.DEFAULTS
edge = d["jar_height"] - pj.FOOT_TAB - pj.HIDE_MARGIN  # 箱の高さは両辺から消える
assert floors(figure_h=edge) == []
assert floors(figure_h=edge + 0.5) == ["F5.popup"]

# 2. 口から出る: 体の下の端 + 押す量 ≧ 口の高さ。押す量の最小は 壺の高さ − 足の高さ
need = d["jar_height"] - pj.FOOT_TAB
assert floors(push_amount=need) == []
assert floors(push_amount=need - 1) == ["F5.popup"]
# 帯の長さは、押し切った時に帯の下の端が箱の底とそろう長さ
assert pj.strip_length(d) == d["box_height"] + pj.FOOT_TAB + d["push_amount"]

# 3. 傾き: 案内（箱の高さ）が短いほど、壺の口での横ずれが大きい。横ずれ = 遊び ÷ 2 ＋ 壺の高さ × 遊び ÷ 箱の高さ
dx, dy = pj.sway(d, d["jar_height"])
assert abs(dx - (pj.SLIDE_GAP / 2 + d["jar_height"] * pj.SLIDE_GAP / d["box_height"])) < 1e-9
gap = pj.HOLE_DEPTH - 2 * d["paper_thickness"]
assert abs(dy - (gap / 2 + d["jar_height"] * gap / d["box_height"])) < 1e-9
assert pj.sway({**d, "box_height": 10}, 60)[0] > pj.sway(d, 60)[0]
assert floors(box_height=10) == ["F5.popup"]
# 袖の幅の境目: 半分の幅 + 横ずれ + 余り ≦ 内の半分 − 紙の厚さ
room = d["jar_width"] / 2 - d["paper_thickness"]
fw_edge = 2 * (room - dx - pj.FIT_MARGIN)
assert floors(figure_w=math.floor(fw_edge * 10) / 10) == []
assert floors(figure_w=fw_edge + 0.2) == ["F5.popup"]

# 4. 引っかかり（引き出しの決まり）: 帯の幅の半分 ≦ 箱の高さ ÷ (2μ)。μ=0.5 なら 帯の幅 ≦ 2 × 箱の高さ
#    傾きと足の床と分けて見るため、壺を低く広く・人形を細くして余りを取った寸法で試す
easy = dict(jar_height=40, push_amount=40, figure_h=20, figure_w=16, strip_width=20, jar_width=60, box_side=70)
assert pj.check_physics({**d, **easy, "box_height": 10}) == []
low = [f.message for f in pj.check_physics({**d, **easy, "box_height": 9})]
assert any("引っかかる" in m for m in low), low

# 5. 壺が箱に乗る: 6 面の壺は角から角（2 × W/√3）で見る。4 面は W。どちらも外の寸法なので紙 2 枚分を足す
assert abs(pj.footprint({**d, "jar": "hex"}) - (2 * d["jar_width"] / math.sqrt(3) + 2 * d["paper_thickness"])) < 1e-9
assert abs(pj.footprint({**d, "jar": "square"}) - (d["jar_width"] + 2 * d["paper_thickness"])) < 1e-9
assert floors(jar="hex", box_side=44) == ["F5.jar_seat"]
assert floors(jar="square", box_side=44) == []

# 6. 帯の穴と人形の足は、人形の輪郭が壺の真ん中に来るように、同じだけ右へずれる（体の中心が輪郭の中ほどより右にあるため）
p = {**d, "jar": "square"}
box = next(q for q in pj.parts(p) if q.key == "box")
fig = next(q for q in pj.parts(p) if q.key == "figure")
hole_cx = box.cuts[0][0] + box.cuts[0][2] / 2
assert abs(hole_cx - (d["box_height"] + d["box_side"] / 2 + pj.strip_offset(p))) < 1e-9
assert box.cuts[0][0] == box.cuts[1][0]  # 上と底の穴は同じ位置（2 点で案内する）
xs = [x for x, _ in fig.outline]
assert min(xs) == 0 and abs(max(xs) - d["figure_w"]) < 1e-9  # 輪郭の幅は figure_w（輪郭を壺の真ん中に置く式の前提）
foot_x = [x for x, y in fig.outline if y == d["figure_h"] + pj.FOOT_TAB]
assert abs(sum(foot_x) / 2 - pj.FIG_AXIS * d["figure_w"]) < 1e-9
# 足は穴より片側 STOP_LIP 広く、静かな時に箱の上で止まる
assert max(foot_x) - min(foot_x) == d["strip_width"] + pj.SLIDE_GAP + 2 * pj.STOP_LIP

# 7. 床の式が頼る貼る位置は、型紙の印と組み方の文で示す（貼る位置がずれると、隠れる・出る高さの式が実物と合わない）
#    帯の上の端から FOOT_TAB の所に、足の下の端を合わせる線を前の半分に刷る
strip = next(q for q in pj.parts(p) if q.key == "strip")
marks = [a for a in strip.art if a["kind"] == "line" and all(abs(y - pj.FOOT_TAB) < 1e-9 for _, y in a["pts"])]
assert marks and all(x <= d["strip_width"] for a in marks for x, _ in a["pts"]), strip.art
text = "".join(pj.steps(p))
assert "印の線" in text and "上の端にそろえ" in text, text
# 壺は上の面の印に、箱は「2 箱」の字の壁を前に（穴が右へずれているので、前後を取り違えると人形が壺の真ん中に来ない）
assert "印に合わせて" in text and "「2 箱」の字のある壁を前" in text, text
# 出典は形によらず 22 コマ左の 1 つ（形は同じ玩具の作り分け）
assert set(pj.SOURCES) == set(pj.FORMS) and set(pj.SOURCES.values()) == {pj.SOURCE}

# 8. 見直しの指摘（中・低）を押さえる
def msgs(**kw):
    return [f.message for f in pj.check_physics({**pj.DEFAULTS, **kw})]

# 8a. 足の収まりは静かな時だけでなく、押し上げる途中（傾きが一番大きい壺の口の高さ）でも見る。足は人形より広くなりうる
#     人形は細く（袖は収まる）、帯は広く（足は 27mm）、糊代は短く（静かな時は収まる）した寸法で、途中で足が壁に擦れる
wide_foot = dict(jar="square", figure_w=16, strip_width=20, jar_tab=3)
assert any("押し上げる途中" in m for m in msgs(**wide_foot)), msgs(**wide_foot)
assert floors(**wide_foot) == ["F5.popup"]
# 8b. 横ずれは、傾きの分に、上の穴の中で帯が丸ごと横へ寄る分（遊びの半分）を足す
assert abs(pj.sway(d, 0)[0] - pj.SLIDE_GAP / 2) < 1e-9
assert abs(pj.sway(d, 60)[0] - (pj.SLIDE_GAP / 2 + 60 * pj.SLIDE_GAP / d["box_height"])) < 1e-9
# 8c. 厚みの向きの遊びが 0（3mm の帯が 3mm の穴）や負は落とす。最小の遊び MIN_DEPTH_GAP を要る
assert any("厚みの向きの遊び" in m for m in msgs(paper_thickness=1.5)), msgs(paper_thickness=1.5)
edge_t = (pj.HOLE_DEPTH - pj.MIN_DEPTH_GAP) / 2
assert not any("厚みの向きの遊び" in m for m in msgs(paper_thickness=edge_t))
assert any("厚みの向きの遊び" in m for m in msgs(paper_thickness=edge_t + 0.01))
# 8d. jar_width は型紙の折り線の間（展開図の 1 面の幅はこの値から出す）。内の幅は紙 2 枚分狭く、外の差し渡しは 2 枚分広い
t = 0.5
assert pj.face_width({**d, "jar": "square", "paper_thickness": t}) == d["jar_width"]
assert abs(pj.inner_half({**d, "paper_thickness": t}) - (d["jar_width"] / 2 - t)) < 1e-9
assert abs(pj.footprint({**d, "jar": "square", "paper_thickness": t}) - (d["jar_width"] + 2 * t)) < 1e-9
assert abs(pj.footprint({**d, "jar": "hex", "paper_thickness": t}) - (2 * d["jar_width"] / math.sqrt(3) + 2 * t)) < 1e-9
# 8e. 決して当たらない検査（足は帯よりいつも 7mm 広い）は持たない
import inspect
assert "帯が足より広い" not in inspect.getsource(pj)

print("ok")
