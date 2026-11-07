"""色の絵がある部品を型紙の折り線で 3D の中で折り、色の面（刷った面）が外を向く事を、部品ごとに見る。

制作者の決定（2026-11-06「今のうちに4つ直す」）で、谷折りだけで閉じて色の面が内に入っていた 4 つの雛形の部品を、御来迎の外筒と
虎の胴と同じく山折りに直した時に足した。谷折りは凡例どおり刷った面がへこむ向きなので、色の面が筒や箱の内に入っていた。
部品ごとに見る事:
- 折り線が全部山折りで、谷折りが無い（本数も前と同じ）
- 3D の中で折って閉じた形で、色のある面（糊代でない面）の全部の刷った面が、形の真ん中から外を向く（omochae.fold3d.fold で折る）
- 同じ線を谷折りに戻した版（直す前の版）は、同じ見方で全部の面が内を向いて落ちる（負の対照。見方が向きを見分けている事）
- 組み方の文は 1 語だけ（谷折り → 山折り）替えた。御来迎の外筒の手順 1 と同じ形で、制作者が採った形
3D で折らない部品は、折り線のデータで見る（虎の胴の直しと同じ見方）:
- 頭の蓋: 八角の斜めの辺で折る。fold3d.fold は頁の上で面を分ける時の浮動小数の誤差で、斜めの折り線の面を分けられない
  （2026-11-06 に確かめた）。fold3d は凍結の床の道具なので、ここでは直さない
- 人形: 折り線は耳の付け根の 1 本だけで、閉じた形が無い。1 本の折り線では、3D で見る事が「刷った面の裏へ折る（山折り）」その物になる
鼠の胴は、端の壁の糊代 4 枚の根元が隣の側面とつながったまま刷られている（外形が糊代と側面の間を通らない。虎の胴の直す前と
同じ外形）ので、fold3d.fold は胴を面に分けられない。色の無い糊代を除いた 6 面の箱で見る（根元の直しは虎の答えと一緒にする）。
"""
import copy

from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

from omochae import fold3d
from omochae.templates import launcher, popup_jar, pull_nod, wheel_cart

EPS = 1e-6


def part(mod, params, key):
    return next(q for q in mod.parts({**mod.DEFAULTS, **params}) if q.key == key)


def inward(q, deg):
    """部品を折り線ごとに deg° 折り、色のある面（糊代でない面）のうち刷った面が形の真ん中の側を向く面の数と、見た面の数。

    真ん中は、折った後の全部の面（糊代も）の真ん中の平均。筒と箱は閉じるので、その内の点になる。
    角柱の n 面は 360/n° ずつ折ると閉じる（四角は 90°、六角は 60°、八角は 45°）。
    """
    faces = fold3d.fold(q, deg)
    glue = fold3d._glue_faces(q, faces)
    mids = [f.at(f.poly.centroid.coords[0]) for f in faces]
    c = tuple(sum(m[i] for m in mids) / len(mids) for i in range(3))
    sides = [(f, m) for f, m in zip(faces, mids) if f not in glue]
    return sum(1 for f, m in sides if fold3d._dot(f.normal, fold3d._sub(m, c)) <= EPS), len(sides)


def without_glue(q):
    """糊代を除いた部品。糊代の付け根の折り線（除いた後の外形の上に乗る線）も除く。"""
    out = copy.deepcopy(q)
    body = Polygon(q.outline).difference(unary_union([Polygon(g) for g in q.glue]))
    assert body.geom_type == "Polygon", (q.key, body.geom_type)
    inner = lambda ls: [ln for ln in ls if body.contains(Point((ln[0][0] + ln[1][0]) / 2, (ln[0][1] + ln[1][1]) / 2))]
    out.outline, out.valley, out.mountain, out.glue = list(body.exterior.coords)[:-1], inner(q.valley), inner(q.mountain), []
    return out


def as_valley(q):
    """同じ線を谷折りに戻した版（直す前の版）。"""
    out = copy.deepcopy(q)
    out.valley, out.mountain = out.valley + out.mountain, []
    return out


CROSSBOW = {"form": "crossbow"}
SQUARE, HEX = {"jar": "square"}, {"jar": "hex"}
RAT, MALLET = {"ride": "rat"}, {"ride": "mallet"}
PECK = {"kind": "peck"}
# (名, 雛形, 形, 部品の鍵, 山折りの本数, 3D の見方, 折る角, 色のある面の数)。見方は whole（部品のまま）・core（糊代を除く）・data（データだけ）
CASES = [
    ("弩の 1 台", launcher, CROSSBOW, "stock", 4, "whole", 90, 4),
    ("四角の 1 壺", popup_jar, SQUARE, "jar", 8, "whole", 90, 4),
    ("六角の 1 壺", popup_jar, HEX, "jar", 12, "whole", 60, 6),
    ("2 箱", popup_jar, SQUARE, "box", 10, "whole", 90, 6),
    ("鼠の 1 胴", wheel_cart, RAT, "body", 10, "core", 90, 6),
    ("鼠の 2 人形", wheel_cart, RAT, "rider", 1, "data", None, None),
    ("ぶりぶりの 1 頭", wheel_cart, MALLET, "drum", 8, "whole", 45, 8),
    ("ぶりぶりの 2 頭の蓋", wheel_cart, MALLET, "capa", 8, "data", None, None),
    ("ぶりぶりの 3 頭の蓋", wheel_cart, MALLET, "capb", 8, "data", None, None),
    ("1 藁苞", pull_nod, PECK, "straw", 4, "whole", 90, 4),
]
# 組み方の文。直した部品の行は 1 語だけ替えた（谷折り → 山折り）。この形の手順に、ほかに谷折りの行は無い
STEPS = [
    (launcher, CROSSBOW, ["1 台を破線で山折りして角筒にし、糊代で貼る"]),
    (popup_jar, SQUARE, ["まず 1 壺だけを実線で切る。色の境で山折りし、横の糊代で貼って 四角の筒にする",
                         "2 箱を色の境で山折りし、横の壁の糊代を前と後ろの壁の内に、後ろの壁の糊代を上の面の内に貼って箱にする"]),
    (popup_jar, HEX, ["まず 1 壺だけを実線で切る。色の境で山折りし、横の糊代で貼って 六角の筒にする"]),
    (wheel_cart, RAT, ["1 胴を破線で山折りし、糊代で貼って箱にする", "2 人形の耳を山折りし、1 胴の上の面の四角い印"]),
    (wheel_cart, MALLET, ["1 頭を破線で山折りして八角の筒にし、糊代で貼る", "2・3 頭の蓋の糊代を山折りし、頭の両端の内側に貼って蓋をする"]),
    (pull_nod, PECK, ["1 藁苞を破線で山折りし、糊代で貼って角の筒にする。両端は開けたまま"]),
]

# 部品ごとに見て、落ちた所を全部並べてから止める（1 つ目で止めると、ほかの部品の様子が見えない）
bad = []
for name, mod, form, key, n_lines, how, deg, n_faces in CASES:
    q = part(mod, form, key)
    if q.valley or len(q.mountain) != n_lines:
        bad.append(f"{name}: 折り線が山折り {n_lines} 本だけでない（谷 {len(q.valley)} 本・山 {len(q.mountain)} 本）")
    if how == "data":
        continue
    shape = without_glue(q) if how == "core" else q
    got = inward(shape, deg)
    if got != (0, n_faces):
        bad.append(f"{name}: 3D で折ると、色のある面 {got[1]} 面のうち {got[0]} 面の刷った面が内を向く（{n_faces} 面とも外のはず）")
    before = inward(as_valley(shape), deg)
    if before != (n_faces, n_faces):
        bad.append(f"{name}: 谷折りに戻した版で、内を向く面が {before[0]}/{before[1]}（全部のはず。見方が向きを見分けていない）")
for mod, form, lines in STEPS:
    st = mod.steps({**mod.DEFAULTS, **form})
    for want in lines:
        if not any(s.startswith(want) for s in st):
            bad.append(f"{mod.__name__.rsplit('.', 1)[-1]} {form}: 組み方の文「{want}」が無い")
    left = [s for s in st if "谷折り" in s]
    if left:
        bad.append(f"{mod.__name__.rsplit('.', 1)[-1]} {form}: 谷折りの行が残る: {left}")
assert not bad, "\n".join(bad)
print("ok 色の面が外")
