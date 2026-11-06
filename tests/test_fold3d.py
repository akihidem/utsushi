"""型紙エンジンの 3D の折り方の写し（omochae.fold3d）の試験。

なぜ: 本人の指示（11-07）「サイトの作り方の3Dは古い型のものだから、新しいのにしないと。」で、組み立ての頁の立体を今の組で作り直す。
その前に、別の作りで同じ刷る部品を折る確かめ（エンジンの fold3d）をこの repo で動かし、次を固める:
1. 写しが今の main の部品で動く（御来迎の前の組 goraigo-v10 の外筒と内筒が角筒に閉じる）
2. 前の組は古い型である（外筒も内筒も谷折りで、刷った面＝色の面が筒の内を向く。今の組は色の面を外にする山折り）
3. サイトの組み立て（assembly.Sheet）で 90° ずつ折った形と、この折り方の形が同じ（面の真ん中どうしの距離で比べる）
4. 確かめが向きを見分ける（山折りに替えた外筒は外を向く）・崩れた部品を黙って通さない（FoldError）
"""
import dataclasses
import json
import os
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from omochae import assembly, fold3d, hypotheses  # noqa: E402
from omochae.compose import TEMPLATES, compose  # noqa: E402
from omochae.hypotheses import ROOT  # noqa: E402

G = "NDL-1187053-R0000005-L"  # 御来迎
tpl = TEMPLATES["slider_fan"]
assert tpl.SHEET_SET == "goraigo-v10", tpl.SHEET_SET  # main の今の組。v14 が入ったら、この試験は前の組を控えに置いて見る
h = hypotheses.sheet_of(G)
p = {**tpl.DEFAULTS, **(h.get("params") or {})}
source = json.loads((ROOT / "data/sources" / f"{G}.json").read_text(encoding="utf-8"))
parts = {q.key: q for q in compose("slider_fan", p, source)[1]["parts"]}


def site_points(part, deg):
    """サイトの組み立て（assembly.Sheet）で、折り線を全部 deg° 折った時の面ごとの真ん中の 3D の点と、頁の上の点。"""
    s = assembly.Sheet(part)
    m = s.matrices({k: deg for k in range(len(s.lines))})
    return [((c.x, c.y), assembly.apply(m[i], (c.x, c.y, 0.0))) for i, c in ((i, s.panels[i].centroid) for i in range(len(s.panels)))]


def matched(site, eng):
    """サイトの面の並びに合わせて、この折り方の面を頁の上の真ん中の点で引き当てる（どちらも同じ折り線で分けた面）。"""
    out = []
    for (x, y), _ in site:
        j = min(range(len(eng)), key=lambda k: (eng[k][0][0] - x) ** 2 + (eng[k][0][1] - y) ** 2)
        assert (eng[j][0][0] - x) ** 2 + (eng[j][0][1] - y) ** 2 < 1e-6, "面の分け方が 2 つの作りで違う"
        out.append(eng[j][1])
    return out


for key in ("tube", "pusher"):
    q = parts[key]
    faces = fold3d.fold(q)
    # 1. 角筒に閉じる（継ぎ目が合い、糊代が帯の反対の端の面に重なる）
    note, fail = fold3d._close(q, faces)
    assert fail is None and note.startswith("閉じる"), (key, fail)
    # 2. 前の組は古い型: 谷折りで、色の面が 4 面とも筒の内を向く
    note, fail = fold3d._face(q, faces)
    assert note is None and fail.floor == "3D.face" and "4 面のうち 4 面" in fail.message, (key, note, fail)
    # 3. サイトの組み立てで 90° ずつ折った形と同じ。45° で止めた形は違うと言う（比べる口が形の違いを見分ける）
    site = site_points(q, 90.0)
    assert fold3d.shape_gap([pt for _, pt in site], matched(site, fold3d.centroids(faces))) < 1e-6, key
    half = site_points(q, 45.0)
    assert fold3d.shape_gap([pt for _, pt in half], matched(half, fold3d.centroids(faces))) > fold3d.TOL, key

# 4. 向きを見分ける: 外筒の谷折りを山折りに替えると、閉じたまま色の面が外を向く（今の組の外筒の形）
outer = parts["tube"]
mountain = dataclasses.replace(outer, valley=[], mountain=list(outer.valley))
faces = fold3d.fold(mountain)
assert fold3d._close(mountain, faces)[1] is None
note, fail = fold3d._face(mountain, faces)
assert fail is None and "4 面とも筒の外を向く" in note, fail
# 崩れた部品を黙って通さない: 外形の縁まで届かない折り線
(a, b), rest = outer.valley[0], outer.valley[1:]
short = dataclasses.replace(outer, valley=[(a, ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2))] + list(rest))
try:
    fold3d.fold(short)
    raise AssertionError("縁まで届かない折り線を黙って通した")
except fold3d.FoldError as e:
    assert "縁まで届いていない" in str(e), e
# 比べる口は、数の違う点の並びを比べない
try:
    fold3d.shape_gap([(0, 0, 0)], [])
    raise AssertionError("数の違う並びを比べた")
except ValueError:
    pass
print("ok")
