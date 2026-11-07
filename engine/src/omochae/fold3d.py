"""型紙の部品を 3D の中で折って組み、刷る部品の形が組み方と合うかを確かめる（最小の 1 本: 御来迎 つまみの形）。

制作者の考え（2026-11-05「手順をAIが3Dで組み立てて、その過程を手順書にする」）の最初の 1 本。制作者の決定で、提出の前は御来迎 つまみの形だけを見る:
- 3D.close: 外筒を、型紙の折り線で 90° ずつ折ると角筒に閉じ、糊代が帯の反対の端の面（1 面目）に重なる。内筒も同じく見る
  （竹串の線の前提なので）。糊代 1 つが 1 面である事、折り線が面を分けていない・長さ 0・つながらない面・自分と交わる外形も、
  同じ床で落とす（式と絵のずれそのものなので）
- 3D.face: 見える面の部品（折り線を刷らず色の境で折る外筒）の刷った面（色の面）が、閉じた筒の外を向く。制作者の答え（2026-11-06
  「色がついている所が外を向くよう折った」）で足した。隠れる部品（破線を刷る内筒）は、向きが組み立てに効かないので見ない
- 3D.fan: 押し上げて扇が口から出て開く所（最後の手順の後半）。台と扇は折らずに置き、静かな時に扇が隠れる・押し上げると要が口より上に出る・
  開いた扇形が横の面の口の縁に当たらない、を見る（制作者の追加 2026-11-06）
- 3D.skewer: 折った内筒が外筒の中に入り、内筒の 2 つの穴が向かい合い（高さも横もずれない）、穴を通す竹串が水平で、
  内筒を外筒に入れて静かな時から押し上げ切るまで、外筒の溝の中を通る
判断の芯:
- 寸法の式（check_physics・slot_span）でなく、刷る部品（外形・折り線・糊代・穴・溝の切り込み）から形を組む。式と絵がずれた時に見つけるため
- 面は硬い板、折り線は蝶番と見る。紙の厚み・たわみ・摩擦は入れないので、通っても紙で動く保証ではない
- 入口は python -m omochae.fold3d だけで、型紙の検査（compose）には繋がない。3D.close・3D.face・3D.skewer・3D.fan は凍結の基準
  （tests/frozen/criteria.md）の床（2026-11-05 と 11-06 の制作者の決定で足した。試験は tests/test_fold3d.py）
前提と限り:
- 谷と山の向き（どちらの面が筒の外を向くか）は、見える面の部品だけを 3D.face で見る。3D.close は向きを見ない（谷を全部山に替えても、
  鏡に映した角筒として閉じる）
- 外筒は折り線を刷らず、絵の色の境で折る（hide_folds）。ここで折るのは型紙の折り線のデータで、色の境がその上にある事は見ない
  （型紙の絵は、折り線と同じ位置から面ごとに塗っている）
- 内筒は外筒の真ん中に、穴のある 2 面目・4 面目を外筒の 2 面目（溝のある面）・4 面目に向けて入れる（外筒は山折り・内筒は谷折りで
  鏡の向きに折れるので、1 面目と 3 面目は入れ替わって向かい合う）。すき間の分だけ横にずれる遊びは見ない
- 竹串の太さは、溝の式（slot_span）と同じ knob_width と見る。刷った穴の丸（半径 1.2mm）は竹串の先であける所の印で、竹串の太さではない
- 行程は、内筒の上の端が口より押し上げる量だけ下にある時（静かな時）から、口に届く時（押し上げ切る）まで。
  押し上げる量は寸法から、筒の高さは折った形から取る
- 竹串の長さと端の位置は見ない（竹串は刷る部品でなく、型紙に長さが無い）。見るのは、竹串の線が溝を通るかだけ
終了: 0 = 確かめて通った / 3 = 落ちた / 4 = 確かめられない（まだ組めない形・読めない）。

内筒を下から押し上げる形（rise）の外筒と内筒は check_rise で確かめる。制作者の決定（2026-11-06）「御来迎 v12 と虎 v5 に、3D の確かめを
試験として足す。」による（試験 tests/test_goraigo_rise_3d.py）。入口 python -m omochae.fold3d も rise を組む（rise は型紙の 1 枚なので、
入口で「確かめられない」と言わないため。見直しの指摘）。つまみの形の確かめと凍結の基準の床は変えない（3D.fit・3D.stroke は凍結の基準に無い）。
"""
import math
import sys
from dataclasses import dataclass

# 読み込みの囲い（壊れた雛形で 4 にする所）を先に通す。
from .__main__ import Parser, load_source, scenario_from_args
from .compose import TEMPLATES, compose
from .model import Failure, ToolMissing
from .ops3d import ops as assembly_ops

# ここだけが使う shapely の部分も、読めなければ 4 にする。読み込みは main の囲いより前に走るので、
# 囲わないとトレースバックの 1 になる（__main__ の囲いと同じ考え。レビューの指摘）。
try:
    from shapely.geometry import LineString, MultiPoint, Point, Polygon
    from shapely.ops import nearest_points, split
except Exception as e:
    print(f"確かめられない: {type(e).__name__}: {e}", file=sys.stderr)
    sys.exit(4)

# 折る手の誤差の見込み（実物で未確認）。継ぎ目のずれ・糊代の浮き・2 つの穴の高さの差をこれで見る。
TOL = 0.5
# 竹串が溝の縁に触れるだけ（余り 0）は通す。溝の上の端は、押し上げ切った時の竹串の上の端そのもの（slot_span）なので、
# 押し上げ切った所の余りは作りとして 0 になる。浮動小数の誤差だけを見逃す幅。
EPS = 1e-6
# 糊代が相手の面に重なる割合の下限。角を落とした糊代は面の中に収まるので、ほぼ全部が重なる。
GLUE_COVER = 0.95
FOLD_DEG = 90  # 角筒は 4 面なので、折り線ごとに 90°
OUTER, INNER, FAN = "tube", "pusher", "fan"
# 扇が開く面は、外筒の開く糸の穴のある 2 つの面（向かい合う面）に垂直な向き（扇の両端をその 2 つの面へ糸でつなぐので）を、
# 型紙のデータから読む。今の型紙では 2・4 面目に穴があり、1 面目に平行（雛形の注「扇は 1 面目に平行に開く」と同じ）。
# 穴が無い時だけ、この面に平行と置き、その事を所見で言う。この向きは制作者が実物どおりと確かめた（2026-11-06）
FAN_PLANE_PANEL = 1


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _mul(a, k):
    return (a[0] * k, a[1] * k, a[2] * k)


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _unit(a):
    return _mul(a, 1 / math.sqrt(_dot(a, a)))


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


IDENTITY = (((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)), (0.0, 0.0, 0.0))


def _apply(T, p):
    R, t = T
    return tuple(_dot(R[i], p) + t[i] for i in range(3))


def _back(T, q):
    """_apply の逆。R は回転なので、転置で戻す。"""
    R, t = T
    d = _sub(q, t)
    return tuple(R[0][i] * d[0] + R[1][i] * d[1] + R[2][i] * d[2] for i in range(3))


def _turn(T, o, d, ang):
    """変換 T の後に、点 o を通る向き d（単位）の線のまわりに ang（ラジアン）回す変換。"""
    x, y, z = d
    c, s = math.cos(ang), math.sin(ang)
    C = 1 - c
    M = ((c + x * x * C, x * y * C - z * s, x * z * C + y * s),
         (y * x * C + z * s, c + y * y * C, y * z * C - x * s),
         (z * x * C - y * s, z * y * C + x * s, c + z * z * C))
    R, t = T
    cols = list(zip(*R))
    return (tuple(tuple(_dot(M[i], cols[j]) for j in range(3)) for i in range(3)),
            _add(tuple(_dot(M[i], _sub(t, o)) for i in range(3)), o))


def _lift(pt):
    """頁の点（mm、y は下向き）を、折る前の紙の 3D の点にする。刷った面が z の正を向き、筒の上（頁の上）が y の正。"""
    return (pt[0], -pt[1], 0.0)


@dataclass
class Face:
    """折った後の面 1 枚。poly は頁の上の平らな形、T は頁の点を 3D へ写す変換、hinge は親の面とつなぐ折り線。"""
    poly: Polygon
    T: tuple
    hinge: tuple = None
    parent: int = None

    def at(self, pt):
        return _apply(self.T, _lift(pt))

    def flat(self, q):
        """3D の点を、この面の頁の上の点と、面から浮く量にする。"""
        X, Y, Z = _back(self.T, q)
        return (X, -Y), Z

    @property
    def normal(self):
        """刷った面の向き（折る前の z の正を、今の向きへ写した物）。"""
        R, _ = self.T
        return (R[0][2], R[1][2], R[2][2])


def _long(a, b, ext=1.0):
    """折り線を両端で ext mm 伸ばす。外形の縁でちょうど終わる線は、縁に触れるだけで面を分けないことがあるため（伸ばした分は外形の外で捨てる）。"""
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = math.hypot(dx, dy)
    ux, uy = dx / n * ext, dy / n * ext
    return LineString([(a[0] - ux, a[1] - uy), (b[0] + ux, b[1] + uy)])


class FoldError(Exception):
    """型紙の折り線と外形が合わず、折れない（3D.close で落とす。確かめられない 4 にはしない。式と絵のずれそのものなので）。"""


def fold(part, deg=FOLD_DEG, angles=None):
    """部品を折り線で面に分け、外形の始めの点を持つ面を動かさずに、折り線ごとに deg° 折る。谷は刷った面の側へ、山は裏へ折る。

    angles は折り線（((x1, y1), (x2, y2))。部品の valley・mountain と同じ形）から角（°）への表で、表に無い線は deg° 折る。
    角を落とした箱（虎の胴の角の面は 45°）のように、折り線ごとに角が違う形を組むため。渡さなければ、どの線も deg°（今までと同じ）。
    Returns 面の並び（list of Face）。親の面を子より先に並べる。最初の面が動かない面（筒なら 1 面目）。
    外形が自分と交わる・長さ 0 の折り線・外形の縁まで届かない折り線・ほかの折り線と重なる折り線・面をちょうど 2 つに分けない
    折り線・折り線でつながらない面がある時は FoldError（黙って飛ばしたり、例外の 4 にしたりすると、崩れた型紙が
    「確かめられない」に紛れる）。
    """
    lines = [(ln, 1) for ln in part.valley] + [(ln, -1) for ln in part.mountain]
    outline = Polygon(part.outline)
    if not outline.is_valid:
        raise FoldError("外形が自分と交わり、面に分けられない")
    for n, ((a, b), _) in enumerate(lines, 1):
        if math.dist(a, b) <= EPS:
            raise FoldError(f"{n} 本目の折り線の長さが 0")
        # 両端が外形の縁にある事。面を分ける時は線を少し伸ばすので、縁の手前で止まる折り線も分けてしまい、見逃した（レビューの指摘）
        gap = max(outline.boundary.distance(Point(pt)) for pt in (a, b))
        if gap > EPS:
            raise FoldError(f"{n} 本目の折り線が外形の縁まで届いていない（端が {gap:.1f}mm 離れる）")
        # 同じ所の 2 本目（谷と山を重ねた矛盾も）は、面の木で黙って飛ばされ、本数だけが増えて通った（レビューの指摘）
        for m, ((c, d), _) in enumerate(lines[:n - 1], 1):
            if LineString([a, b]).intersection(LineString([c, d])).length > EPS:
                raise FoldError(f"{n} 本目の折り線が {m} 本目と重なる")
    polys = [outline]
    for (a, b), _ in lines:
        polys = [g for f in polys for g in split(f, _long(a, b)).geoms]
    # 折り線に沿って縁を持つ 2 面を、その折り線でつなぐ。縁が線に沿う長さで見る（真ん中の点で見ると、溝や穴を通る折り線で外れる）
    adj = {}
    for n, ((a, b), sign) in enumerate(lines, 1):
        seg = LineString([a, b])
        touch = [i for i, f in enumerate(polys) if f.boundary.intersection(seg).length > EPS]
        if len(touch) != 2:
            raise FoldError(f"{n} 本目の折り線が面を 2 つに分けていない（外形と合わない）")
        i, j = touch
        adj.setdefault(i, []).append((j, (a, b), sign))
        adj.setdefault(j, []).append((i, (a, b), sign))
    start = Point(part.outline[0])
    root = next(i for i, f in enumerate(polys) if f.boundary.distance(start) < EPS)
    faces, index = [Face(polys[root], IDENTITY)], {root: 0}
    for k in range(len(polys)):  # 広さ優先。faces が伸びる間だけ回る
        if k >= len(faces):
            break
        i = next(n for n, m in index.items() if m == k)
        parent = faces[k]
        for j, (a, b), sign in adj.get(i, []):
            if j in index:
                continue
            o, e = parent.at(a), parent.at(b)
            d = _unit(_sub(e, o))
            ang = math.radians(angles.get((a, b), deg) if angles else deg)
            c = polys[j].centroid.coords[0]
            c0 = parent.at(c)
            # 回す向きは、子の面の真ん中が親の刷った面の側（谷）か裏（山）へ動く方。線の向きで符号が変わるので、動きで決める
            T = _turn(parent.T, o, d, ang)
            if _dot(_sub(_apply(T, _lift(c)), c0), parent.normal) * sign < 0:
                T = _turn(parent.T, o, d, -ang)
            index[j] = len(faces)
            faces.append(Face(polys[j], T, (a, b), k))
    if len(faces) < len(polys):
        raise FoldError(f"折り線でつながらない面が {len(polys) - len(faces)} つある（外形と折り線が合わない）")
    return faces


def _glue_faces(part, faces):
    """糊代とちょうど重なる面（面の 99% が糊代で、その糊代の 99% がこの面にある）。

    面の側だけを見ると、糊代が隣の面へはみ出しても通った（レビューの指摘）。両側から見る。
    """
    gs = [Polygon(g) for g in part.glue]

    def same(f, g):
        a = f.poly.intersection(g).area
        return a >= 0.99 * f.poly.area and a >= 0.99 * g.area
    return [f for f in faces if any(same(f, g) for g in gs)]


def _seam(part, face, ends):
    """糊代の折り線の 2 つの端（3D）が、相手の面の 1 本の切る縁（折り線の上でない外形の辺）にどれだけ近いか。2 つの端の遠い方で測る。

    縁のどこかまでの距離にすると、1 面目だけが広い時に、2 つの端が上と下の縁に乗って 0 になり、閉じない筒を見逃した。
    1 本の辺に 2 つの端がそろって乗る事を見る。並んだ辺の途中の点は除いてから見る（同じ線の上で切れた辺を 1 本にするため）。
    """
    folds = [LineString(ln) for ln in part.valley + part.mountain]
    pts = [face.flat(e) for e in ends]
    coords = list(face.poly.simplify(0).exterior.coords)
    gaps = [max(math.hypot(LineString([a, b]).distance(Point(pt)), z) for pt, z in pts)
            for a, b in zip(coords, coords[1:])
            if not any(ln.distance(Point((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)) < EPS for ln in folds)]
    return min(gaps, default=math.inf)


def _far_end(faces, g):
    """折り線でつながる面の木の上で、面 g から一番遠い面（帯の反対の端）。筒の糊代の面なら、帯の始めの 1 面目。"""
    def up(k):
        out = [k]
        while faces[out[-1]].parent is not None:
            out.append(faces[out[-1]].parent)
        return out
    pg = up(g)

    def dist(k):
        pk = up(k)
        common = next(x for x in pk if x in pg)
        return pk.index(common) + pg.index(common)
    return max(range(len(faces)), key=dist)


def _kinds(part):
    """折りの種類と本数の言い方（例: 谷折り 4 本）。"""
    return "・".join(f"{name} {len(ls)} 本" for name, ls in (("谷折り", part.valley), ("山折り", part.mountain)) if ls)


def _close(part, faces):
    """糊代の面が、継ぎ目を合わせて帯の反対の端の面に重なるか。Returns (所見の文, 失敗)。どちらか片方だけ。

    相手は帯の反対の端の面に限る。どの面でもよいとすると、折り線の崩れで糊代が別の面に貼り付く形を通しうる（レビューの指摘）。
    継ぎ目を先に見る。折り線が 1 本ずれた時に、継ぎ目と糊代の重なりの 2 行が出ると、1 つの崩れが 2 つに見えるため。
    谷と山の向きは見ない（どちらの面が筒の外を向くか）。谷を全部山に替えても、鏡に映した角筒として閉じる。文には実際の本数を言う。
    """
    where = part.label
    kinds = _kinds(part)
    if not part.glue:
        return None, Failure("3D.close", where, "糊代の印が無く、角筒の継ぎ目を貼れない")
    glued = _glue_faces(part, faces)
    # 糊代 1 つに面 1 つ。余計な折り線で糊代が分かれると、片方だけを見て、もう片方を見落とす（レビューの指摘）
    if len(glued) != len(part.glue):
        return None, Failure("3D.close", where, f"糊代が折り線で区切られた 1 面とちょうど重なっておらず（糊代 {len(part.glue)} つに、重なる面 {len(glued)} つ）、折って貼れない")
    gi = next(i for i, f in enumerate(faces) if f is glued[0])
    g, k = faces[gi], _far_end(faces, gi)
    # 糊代の面の折り線。外形の始めの点が糊代の面にあると、その面が動かない面になり、折り線は子の面の側が持つ
    hinge = g.hinge or next((f.hinge for f in faces if f.parent == gi), None)
    if k == gi or hinge is None:
        return None, Failure("3D.close", where, "糊代を折って貼る相手の面が無い")
    gap = _seam(part, faces[k], [g.at(pt) for pt in hinge])
    if gap > TOL:
        return None, Failure("3D.close", where, f"型紙の折り線（{kinds}）で 90° ずつ折ると、継ぎ目が {gap:.1f}mm ずれ、角筒に閉じない")
    f = faces[k]
    mapped = [f.flat(g.at(pt)) for pt in g.poly.exterior.coords]
    lift = max(abs(z) for _, z in mapped)
    cover = Polygon([pt for pt, _ in mapped]).intersection(f.poly).area / g.poly.area
    if lift > TOL or cover < GLUE_COVER:
        return None, Failure("3D.close", where, f"糊代が貼る相手の面に重ならない（浮き {lift:.1f}mm・重なり {cover:.0%}）")
    target = "1 面目" if k == 0 else "帯の反対の端の面"
    return f"閉じる {where}: 型紙の折り線（{kinds}）を 90° ずつ折ると角筒に閉じる（継ぎ目のずれ {gap:.2f}mm・糊代は{target}に {cover:.0%} 重なる）", None


def tube_axis(faces):
    """角筒の軸の上向きの向き・断面の中心の点・その点から測った底と上の端の高さ。

    中心は折り線（蝶番）の位置の平均から取る。面の頂点の平均にすると、溝のある面の点が多いぶん溝の側へ寄る。
    """
    hinged = [f for f in faces if f.hinge]
    a, b = hinged[0].hinge
    top, bottom = (a, b) if a[1] < b[1] else (b, a)  # 頁の y の小さい方が筒の上
    up = _unit(_sub(hinged[0].at(top), hinged[0].at(bottom)))
    mids = [f.at(((f.hinge[0][0] + f.hinge[1][0]) / 2, (f.hinge[0][1] + f.hinge[1][1]) / 2)) for f in hinged]
    c = _mul(tuple(sum(m[i] for m in mids) for i in range(3)), 1 / len(mids))
    hs = [_dot(_sub(f.at(pt), c), up) for f in faces for pt in f.poly.exterior.coords]
    return up, c, min(hs), max(hs)


def _face(part, faces):
    """見える面の部品の刷った面（色の面）が、閉じた筒の外を向くか。Returns (所見の文, 失敗)。

    側の面ごとに、刷った面の向き（折る前の z の正を今の向きへ写した物）と、軸から面の真ん中への向きが同じ側かを見る。
    谷折り（凡例の、刷った面がへこむ向き）で筒にすると、色の面が内に入る。制作者の答え（2026-11-06「色がついている所が外を向くよう
    折った」）で、型紙の外筒を山折りに直した時に足した。
    """
    up, c, _, _ = tube_axis(faces)
    glue = _glue_faces(part, faces)
    sides = [f for f in faces if f not in glue]
    inward = 0
    for f in sides:
        m = _sub(f.at(f.poly.centroid.coords[0]), c)
        if _dot(f.normal, _sub(m, _mul(up, _dot(m, up)))) <= 0:
            inward += 1
    if inward:
        return None, Failure("3D.face", part.label, f"型紙の折り線（{_kinds(part)}）で折ると、色の面（刷った面）が筒の内を向く"
                                                 f"（{len(sides)} 面のうち {inward} 面）。谷折りは刷った面がへこむ向き")
    return f"外向き {part.label}: 色の面（刷った面）は {len(sides)} 面とも筒の外を向く", None


def _section(faces, up, c):
    """角筒の断面。折り線（角）の位置を、軸に垂直な面へ写した多角形（軸の中心 c が原点）。"""
    e1 = _cross(up, (0.0, 0.0, 1.0))
    e1 = _unit(e1 if _dot(e1, e1) > EPS else _cross(up, (1.0, 0.0, 0.0)))
    e2 = _cross(up, e1)
    mids = [_sub(f.at(((f.hinge[0][0] + f.hinge[1][0]) / 2, (f.hinge[0][1] + f.hinge[1][1]) / 2)), c) for f in faces if f.hinge]
    return MultiPoint([(_dot(m, e1), _dot(m, e2)) for m in mids]).convex_hull


def _op_fold(st, key):
    """筒を折って閉じる操作（fold_outer・fold_inner）。閉じた筒だけを後の操作に渡す。見える面の部品は、色の面の向きも見る。"""
    q = st["by"][key]
    try:
        faces = fold(q)
    except FoldError as e:
        return [(None, Failure("3D.close", q.label, str(e)))]
    note, fail = _close(q, faces)
    if fail:
        return [(None, fail)]
    st["folded"][key] = faces
    out = [(note, None)]
    if q.hide_folds:
        # 見える面の部品（色の境で折る）だけ、色の面の向きを見る。隠れる部品（破線を刷る内筒）の向きは組み立てに効かない。
        # 向きは竹串の形に効かない（鏡に映した筒でも穴と溝は並ぶ）ので、3D.face で落ちても後の操作は続ける
        out.append(_face(q, faces))
    return out


def _op_thread(st):
    """竹串を内筒の 2 つの穴に通す操作。内筒が閉じなければ見ない（1 つの崩れに 1 行）。"""
    if INNER not in st["folded"]:
        return []
    inner_part, inner = st["by"][INNER], st["folded"][INNER]
    holes = inner_part.holes
    if len(holes) != 2:
        return [(None, Failure("3D.skewer", "竹串", f"竹串を通す穴が 2 つでない（{len(holes)} 個）"))]
    centers, walls_of = [], []
    for x, y, _ in holes:
        f = next((f for f in inner if f.poly.contains(Point(x, y))), None)
        if f is None:
            return [(None, Failure("3D.skewer", "竹串", "竹串を通す穴が面の中に無い（折り線の上か外形の外）"))]
        centers.append(f.at((x, y)))
        walls_of.append(f)
    up_i = tube_axis(inner)[0]
    d = _sub(centers[1], centers[0])
    if math.sqrt(_dot(d, d)) <= EPS:
        # 2 つの穴が同じ所にあると竹串の向きが決まらない。先へ進むと 0 で割って 4 になった（レビューの指摘）
        return [(None, Failure("3D.skewer", "竹串", "2 つの穴が同じ所にあり、竹串の向きが決まらない"))]
    tilt = abs(_dot(d, up_i))
    if tilt > TOL:
        return [(None, Failure("3D.skewer", "竹串", f"2 つの穴の高さが {tilt:.1f}mm 違い、竹串が傾く（溝の中で引っかかる）"))]
    # 横のずれも同じく見る。高さだけがそろい、穴が向かい合わずに横へずれると、竹串が面へ斜めに交わる（レビューの指摘）。
    # 穴のある面に垂直な向きと、軸の向きのどちらでもない向きの長さ
    n1 = walls_of[0].normal
    side = math.sqrt(max(0.0, _dot(d, d) - _dot(d, n1) ** 2 - _dot(d, up_i) ** 2))
    if side > TOL:
        return [(None, Failure("3D.skewer", "竹串", f"2 つの穴が向かい合っておらず（横に {side:.1f}mm ずれ）、竹串が斜めになる（溝の中で引っかかる）"))]
    st["skewer"] = centers
    return [(f"通す 竹串: 2 つの穴は向かい合い（高さの差 {tilt:.2f}mm・横のずれ {side:.2f}mm）、竹串は水平", None)]


def _op_insert(st):
    """内筒を外筒に入れ、竹串の端を溝から出す操作。外筒・内筒が閉じ、竹串を通した後だけ見る。

    竹串が出る面は、静かな時に竹串の切り口から紙までの余りが一番大きい面（溝のある面）。前は行程の全部の余りで選んでいて、
    溝の上の端が短い時は 2 つの面が同じ値になり、面の並びの順で決まっていた。
    """
    if OUTER not in st["folded"] or INNER not in st["folded"] or "skewer" not in st:
        return []
    outer_part, outer = st["by"][OUTER], st["folded"][OUTER]
    inner_part, inner = st["by"][INNER], st["folded"][INNER]
    p, centers = st["p"], st["skewer"]
    up_o, c_o, bot_o, top_o = tube_axis(outer)
    up_i, c_i, bot_i, top_i = tube_axis(inner)
    # 折った内筒が外筒の中に入るか。寸法の式（F5.slide_clearance）でなく、折った形の断面で見る（絵の内筒が式より大きくずれた時に
    # 見つけるため。レビューの指摘）。紙の厚みを入れないので、すき間が 0 より大きいかだけを見る（厚みの分の余りは式の床が見る）
    sec_o, sec_i = _section(outer, up_o, c_o), _section(inner, up_i, c_i)
    if sec_i.within(sec_o):
        fit = sec_o.exterior.distance(sec_i)
    else:
        fit = -max(sec_o.distance(Point(pt)) for pt in sec_i.exterior.coords)
    if fit <= EPS:
        return [(None, Failure("3D.skewer", inner_part.label, f"内筒の断面が外筒の断面に収まらず（すき間 {fit:.1f}mm）、外筒に入らない"))]
    H, L, s, r = top_o - bot_o, top_i - bot_i, p["push_amount"], p["knob_width"] / 2
    rest, push = H - s - L, H - L  # 内筒の底の、外筒の底からの高さ

    def placed(q, t):
        """内筒の点を、外筒の真ん中で、内筒の底を外筒の底から t の高さに置いた所へ写す（両方とも 1 面目を動かさずに頁の向きのまま折るので、
        穴のある 2 面目・4 面目は外筒の 2 面目・4 面目に向く。外筒が山折り・内筒が谷折りだと鏡の向きになり、1 面目と 3 面目は入れ替わる）。"""
        return _add(_add(_sub(q, c_i), c_o), _mul(up_o, bot_o + t - bot_i))

    u = _unit(_sub(centers[1], centers[0]))
    glue = _glue_faces(outer_part, outer)
    best = None
    for f in (f for f in outer if f not in glue):
        n = f.normal
        if abs(_dot(u, n)) < EPS:
            continue  # 竹串と平らな面は通らない
        o = f.at(f.poly.exterior.coords[0])
        q = []
        for t in (rest, push):
            a = placed(centers[0], t)
            q.append(f.flat(_add(a, _mul(u, _dot(_sub(o, a), n) / _dot(u, n))))[0])
        hull = f.poly.convex_hull
        if not all(hull.covers(Point(pt)) for pt in q):
            continue  # 行程の端で面の外（筒の上か下）を通る面は、竹串が出る所ではない
        # 竹串が面へ斜めに交わると、面の上の切り口は楕円になり、長い方の半径は r / cos。安全側に、その半径の円で見る
        # （横のずれの床を通った後は、斜めは 1° ほどまでなので、円にした分の差は小さい）
        rf = r / abs(_dot(u, n))
        at_rest = f.poly.distance(Point(q[0])) - rf
        if best is None or at_rest > best[0]:
            best = (at_rest, f, q, rf)
    if best is None:
        return [(None, Failure("3D.skewer", "竹串", "竹串の線が、行程の間ずっと外筒の面を横切る所が無い（筒の外を通る）"))]
    at_rest, f, (q0, q1), rf = best  # rf はその面の上の竹串の切り口の半径（文に出す太さは r のまま）
    if at_rest < -EPS:
        return [(None, Failure("3D.skewer", "竹串", f"静かな時から、竹串（太さ {2 * r:g}mm）が外筒の紙に {-at_rest:.1f}mm 掛かり、溝を通らない"))]
    rest_h, push_h = (_dot(_sub(placed(centers[0], t), c_o), up_o) - bot_o for t in (rest, push))
    st["slot"] = {"face": f, "q": (q0, q1), "rf": rf, "r": r, "travel": push - rest, "h": (rest_h, push_h)}
    return [(f"入れる {inner_part.label}: 内筒は外筒の中に入る（断面のすき間 {fit:.2f}mm）。内筒を外筒の真ん中に入れると、静かな時は竹串の中心が"
             f"底から {rest_h:.1f}mm で、竹串（太さ {2 * r:g}mm）の端が溝から出る（紙までの余り {at_rest:.2f}mm）", None)]


def _op_push(st):
    """竹串の端を溝に沿って押し上げる操作。入れた後だけ見る。竹串の中心が通る線分から紙までで、行程の全部を一度に見る。"""
    if "slot" not in st:
        return []
    sl = st["slot"]
    f, (q0, q1), rf, r = sl["face"], sl["q"], sl["rf"], sl["r"]
    if f.poly.distance(LineString([q0, q1])) - rf < -EPS:
        # 動きは真っ直ぐなので、紙に当たる所は行程の途中の 1 か所。二分で探す
        lo, hi = 0.0, 1.0
        for _ in range(40):
            mid = (lo + hi) / 2
            end = (q0[0] + (q1[0] - q0[0]) * mid, q0[1] + (q1[1] - q0[1]) * mid)
            lo, hi = (mid, hi) if f.poly.distance(LineString([q0, end])) - rf >= -EPS else (lo, mid)
        short = (1 - lo) * sl["travel"]
        return [(None, Failure("3D.skewer", "竹串", f"押し上げ切る {short:.1f}mm 手前で、竹串が外筒の紙に当たり、溝を通り切らない"))]
    c_push = f.poly.distance(Point(q1)) - rf
    stop = ""
    if c_push < TOL and nearest_points(f.poly, Point(q1))[0].y < q1[1] - EPS:
        stop = "。押し上げ切ると溝の上の端に届いて止まる"
    rest_h, push_h = sl["h"]
    return [(f"押し上げる 竹串: 竹串の中心は底から {rest_h:.1f}mm から {push_h:.1f}mm まで {sl['travel']:g}mm 上がり、行程の全部で溝の中を通る"
             f"（押し上げ切った時の紙までの余り {c_push:.2f}mm{stop}）", None)] + _fan(st)


def _fan_shape(fan_part):
    """扇の部品の形から読む値。Returns (板の高さ h, 帯の長さ, 要の穴の x, 足の折り線の x) か、足が無ければ None。

    頁の x は要の側の縁（x = 0）から先の縁（x = h）へ、y は帯の長さの向き。足は真ん中の板から要の側（x < 0）へ伸び、
    足の糊代の境の折り線（x 一定）が台の上の面に乗る。寸法の式でなく描いた形から読む（式と絵のずれを見つけるため）。
    """
    legs = [a[0] for a, b in fan_part.valley + fan_part.mountain if abs(a[0] - b[0]) < EPS and a[0] < 0]
    if not legs or not fan_part.holes:
        return None
    h = max(x for x, _ in fan_part.outline)
    ys = [y for _, y in fan_part.outline]
    return h, max(ys) - min(ys), min(hx for hx, _, _ in fan_part.holes), legs[0]


def _fan(st):
    """押し上げて扇が開く所（手順 13 の後半）。台と扇は折らずに置いた形で見る。Returns [(所見の文, 失敗)]。

    台の上の面は内筒の上の端の高さ、扇は足の折り線が台の上の面に乗る高さに置く。畳んだ扇は箱（上の端の高さだけを見る）、
    開いた扇は要のまわりの扇形（半径は要の穴から先の縁まで、開く角は見込みの上限の帯の長さ÷板の高さ。雛形の F5.fan_clearance と同じ見込みで、
    実際は折り目で紙が立つので小さい。上限まで開いても当たらないかを、安全側で見る）。
    見る事: 静かな時に扇の上の端が口より下（隠れる）・押し上げ切ると要が口より上・開いた扇形が横の面の口の縁に当たらない。
    見ない事: 蛇腹の折り・開く仕組み（糸・紙のばね）・畳んだ扇の厚さが断面に収まるか（台の奥の縁に寄るので、式の床と食い違いうる）。
    """
    by, p = st["by"], st["p"]
    if FAN not in by:
        # 外筒と内筒だけを渡した呼び方。黙って通さず、扇は見ていないと言う
        return [("開く 扇: 扇の部品を渡していないので、扇は見ない", None)]
    where = by[FAN].label
    if p.get("hub") != "axle":
        # 口の台の形（hub rim）は、扇の端を台に貼る別の作り。まだ置いていないと言う（黙って通さない）
        return [(f"開く {where}: 口の台の形の扇は、まだ置いていない（要と足が無い作り）", None)]
    shape = _fan_shape(by[FAN])
    if shape is None:
        # 軸の形なのに要の穴か足の折り線が無いのは、描いた扇の崩れ。口の台の形と取り違えて通さない（レビューの指摘）
        return [(None, Failure("3D.fan", where, "軸の形の扇に、要の穴か足の糊代の境の折り線が無く、台に置けない"))]
    h, strip, hole_x, leg_x = shape
    outer_part, outer = by[OUTER], st["folded"][OUTER]
    up, c, bot, top = tube_axis(outer)
    H, s = top - bot, p["push_amount"]
    # 静かな時は内筒の上の端（＝台の上の面）が口より押し上げる量だけ下。畳んだ扇の上の端は、台の上の面から h − 足の折り線の x。
    # 口と同じ高さは隠れていない（凍結の行の「口より下」。型紙の検査に通る寸法では 2mm 以上の余りがある）
    hidden = s - (h - leg_x)
    if hidden <= EPS:
        said = f"口より {-hidden:.1f}mm 上に出る" if hidden < -EPS else "口と同じ高さに来る"
        return [(None, Failure("3D.fan", where, f"静かな時に、畳んだ扇の上の端が{said}（隠れない）"))]
    d = hole_x - leg_x  # 押し上げ切った時の、要の口からの高さ（台の上の面が口の高さに来る）
    if d <= EPS:
        return [(None, Failure("3D.fan", where, f"押し上げ切っても、要が口より上に出ない（口から {d:.1f}mm）"))]
    R, theta = h - hole_x, min(360.0, math.degrees(strip / h))
    sides = sorted((f for f in outer if f not in _glue_faces(outer_part, outer)), key=lambda f: f.poly.bounds[0])
    # 開く面: 開く糸の穴のある面が向かい合う 2 面なら、その 2 面に垂直（＝ほかの 2 面に平行）。無ければ FAN_PLANE_PANEL に平行と置く
    holed = [f for f in sides if any(f.poly.contains(Point(x, y)) for x, y, _ in outer_part.holes)]
    if holed and not (len(holed) == 2 and _dot(holed[0].normal, holed[1].normal) < -1 + EPS):
        # 穴はあるのに、向かい合う 2 面に無い（1 面だけ・3 面以上・隣の面）のは、描いた穴の崩れ。穴が無い時と取り違えて
        # 決めた向きで続けない（レビューの指摘）
        faces = "・".join(str(sides.index(f) + 1) for f in holed)
        return [(None, Failure("3D.fan", outer_part.label, f"開く糸の穴が向かい合う 2 つの面に無く（穴のある面: {faces} 面目）、扇の開く向きが決まらない"))]
    if holed:
        fan_n = _cross(up, holed[0].normal)
        plane = next(i for i, f in enumerate(sides, 1) if abs(abs(_dot(f.normal, fan_n)) - 1) < EPS)
        how = f"{plane} 面目に平行に開き（開く糸の穴のある {'・'.join(str(sides.index(f) + 1) for f in holed)} 面目に垂直な向き）"
    else:
        fan_n, plane = sides[FAN_PLANE_PANEL - 1].normal, FAN_PLANE_PANEL
        how = f"{plane} 面目に平行に開き（開く糸の穴が無いので、この向きと置いた）"
    mouth = _add(c, _mul(up, top))
    margins = []
    for f in sides:
        if abs(_dot(f.normal, fan_n)) > EPS:
            continue  # 扇の面と平行な面には、扇は当たらない（扇はその面に平行に開く）
        off = _dot(_sub(f.at(f.poly.exterior.coords[0]), mouth), f.normal)
        a = abs(off)  # 軸から横の面までの距離
        out_dir = _mul(f.normal, 1 if off > 0 else -1)
        if R <= a:
            continue  # 扇の先が横の面まで届かない
        half = math.radians(theta / 2)
        phi = math.asin(a / R)
        if half <= phi:
            continue  # 開いても横の面まで届かない角
        reach = math.sqrt(R * R - a * a)
        low = d + a / math.tan(half) if half < math.pi - phi else d - reach
        seg = [f.flat(_add(_add(mouth, _mul(out_dir, a)), _mul(up, z)))[0] for z in (low, d + reach)]
        margins.append(f.poly.distance(LineString(seg)) if low < 0 else low)
    margin = min(margins, default=None)
    if margin is not None and margin <= EPS:
        return [(None, Failure("3D.fan", where, f"開く角の見込みの上限（{theta:.0f}°）まで開くと、扇が横の面の口の縁に当たる"))]
    edge = "横の面の口の縁に当たらない" + (f"（縁までの余り {margin:.1f}mm）" if margin is not None else "（横の面まで届かない）")
    return [(f"開く {where}: 静かな時、畳んだ扇の上の端は口より {hidden:.1f}mm 下（隠れる）。押し上げ切ると、要が口より {d:.1f}mm 上に出て、"
             f"扇は {how}、開く角の見込みの上限（{theta:.0f}°。帯の長さ÷板の高さで、実際は折り目で紙が立つので小さい）まで開いても、"
             f"{edge}。台と扇は折らずに置いた形で見る（畳んだ扇は箱、開いた扇は要の"
             "まわりの扇形）。蛇腹の折りと、開く仕組み（糸・紙のばね）は見ない", None)]


# 操作の種類ごとに、3D で行う事。並びは omochae.ops3d の操作の並び（手順の文と同じ元）で決める
OPS = {"fold_outer": lambda st: _op_fold(st, OUTER), "fold_inner": lambda st: _op_fold(st, INNER),
       "thread": _op_thread, "insert": _op_insert, "push": _op_push}


def _step_numbers(p):
    """3D の操作の種類ごとの、手順の番号（雛形の組み方の何番目か）。雛形が、手順の文と操作の種類を 1 つの並びで持つ（step_ops）。

    文を突き合わせて引くと、文の小さな直しで黙って外れた（レビューの指摘）。扇などの部品も要らない。
    """
    return TEMPLATES["slider_fan"].step_ops(p)


def _tag(note, nums, *kinds):
    """所見の文の頭に、確かめた操作の手順の番号を添える（組んだ過程と手順書を、番号で結ぶため）。"""
    ns = [str(nums[k]) for k in kinds if k in nums]
    if not ns:
        return note
    head, rest = note.split(": ", 1)
    return f"{head}（手順 {'・'.join(ns)}）: {rest}"


def check(parts, p):
    """刷る部品（compose の配置の部品）と寸法から、外筒と内筒を折って組み、確かめる。Returns (所見の文の並び, 失敗の並び)。

    手順の文を作る操作の並び（omochae.ops3d）を、その順に 3D の中で行う。前の操作が落ちると、それに頼る後の操作は見ない
    （1 つの崩れに 1 行。compose と同じ考え）。所見と失敗の行には、その操作の手順の番号を添える（直す所を手順で引けるように）。
    """
    by = {q.key: q for q in parts}
    if OUTER not in by or INNER not in by:
        raise ToolMissing("外筒と内筒が無い（組めるのは、御来迎 つまみの形と、内筒を下から押し上げる形だけ）")
    nums = _step_numbers(p)
    st = {"by": by, "p": p, "folded": {}}
    notes, failures = [], []
    for kind, _ in assembly_ops(parts, p):
        for note, fail in OPS[kind](st):
            if note:
                notes.append(_tag(note, nums, kind))
            else:
                n = nums.get(kind)
                failures.append(Failure(fail.floor, fail.where, f"{fail.message}（手順 {n}）" if n else fail.message))
    return notes, failures


def _fit(outer, inner):
    """折った内筒の断面が、折った外筒の断面に収まる時のすき間 mm（負なら、はみ出す長さ）。紙の厚みは入れない。"""
    up_o, c_o, _, _ = tube_axis(outer)
    up_i, c_i, _, _ = tube_axis(inner)
    sec_o, sec_i = _section(outer, up_o, c_o), _section(inner, up_i, c_i)
    if sec_i.within(sec_o):
        return sec_o.exterior.distance(sec_i), sec_i
    return -max(sec_o.distance(Point(pt)) for pt in sec_i.exterior.coords), sec_i


def check_rise(parts, p):
    """内筒を下から押し上げる形（rise）の外筒と内筒を、刷る部品から折って組み、確かめる。Returns (所見の文の並び, 失敗の並び)。

    試験だけが呼ぶ（凍結の基準の床ではない。床の名は、つまみの形と同じ事を見る 3D.close・3D.face と、この形だけの 3D.fit・3D.stroke）。
    つまみの形の確かめ（check）と同じ部品（fold・_close・_face・tube_axis・_section）を使い、面は硬い板・折り線は蝶番と見る。
    - 3D.close: 外筒と内筒が、型紙の折り線で 90° ずつ折ると角筒に閉じ、糊代が帯の反対の端の面に重なる
    - 3D.face: 外筒（色の境で折る見える部品）の色の面が筒の外を向く。内筒は隠れる部品なので向きを見ない（3D.face と同じ決まり）
    - 3D.fit: 折った内筒の断面が外筒の断面に収まる（すき間が 0 より大きい）
    - 3D.stroke: 内筒を外筒の真ん中に入れ、台の上の面（内筒の上の端）を、静かな時（口から押し上げる量 s だけ下）から開いた位置
      （口の高さ）まで動かす。静かな時に、台の上に立つ物（受けの底の紙＋扇の高さ・像の高さ）の上の端が口より下（口と同じ高さは落とす）、
      内筒が外筒に内筒の一辺（折った断面の幅）以上入っている（静かな時が一番短い。傾かない）。割り箸（刷る部品でないので、雛形の
      見込みの長さ CHOPSTICK_LEN で置く）は台の糊代の下から下へ伸び、内筒に CHOPSTICK_GLUE 以上貼れて、開いた位置でも外筒の下へ
      CHOPSTICK_GRIP 以上残る（押し引きする所）。
      筒の高さと内筒の長さ・一辺は折った形から、押し上げる量・扇と像の高さ・紙の厚さ・台の糊代は寸法から取る（つまみの形の 3D.fan と同じ取り方）
    見ない事: 扇が開く所（受けと蛇腹の折り目のばねで開く仕組みで、蝶番ではないので、面と蝶番の 3D では組めない）・台（蓋）と受けと
    像は折らない・紙の厚み・たわみ・摩擦。
    """
    by = {q.key: q for q in parts}
    if OUTER not in by or INNER not in by:
        raise ToolMissing("外筒と内筒が無い")
    notes, failures, folded = [], [], {}
    for key in (OUTER, INNER):
        q = by[key]
        try:
            faces = fold(q)
        except FoldError as e:
            failures.append(Failure("3D.close", q.label, str(e)))
            continue
        note, fail = _close(q, faces)
        if fail:
            failures.append(fail)
            continue
        notes.append(note)
        folded[key] = faces
        if q.hide_folds:
            note, fail = _face(q, faces)
            notes.append(note) if note else failures.append(fail)
    if len(folded) < 2:
        return notes, failures  # 閉じない筒は、入れる・押し上げるを見ない（1 つの崩れに 1 行）
    fit, sec_i = _fit(folded[OUTER], folded[INNER])
    inner_label = by[INNER].label
    if fit <= EPS:
        failures.append(Failure("3D.fit", inner_label, f"内筒の断面が外筒の断面に収まらず（すき間 {fit:.1f}mm）、外筒に入らない"))
        return notes, failures
    notes.append(f"入れる {inner_label}: 内筒は外筒の中に入る（断面のすき間 {fit:.2f}mm）")
    _, _, bot_o, top_o = tube_axis(folded[OUTER])
    _, _, bot_i, top_i = tube_axis(folded[INNER])
    H, L = top_o - bot_o, top_i - bot_i
    x0, y0, x1, y1 = sec_i.bounds
    a = max(x1 - x0, y1 - y0)
    s, t, h, fh = p["push_amount"], p["paper_thickness"], p["fold_height"], p["figure_h"]
    sf = TEMPLATES["slider_fan"]
    rest = H - s  # 静かな時の、台の上の面の外筒の底からの高さ。開いた位置では H（口の高さ）
    stand = max(t + h, fh)
    inside = min(L, rest)  # 静かな時に、内筒が外筒の中に入っている長さ（下の端が外筒の下に出る時は、外筒の底から台まで）
    _, below = sf.chopstick_lengths(L, H, p["base_glue"])  # 開いた位置で、割り箸が外筒の下へ出る長さ（所見の文に言う）
    bad = []
    if rest + stand >= H - EPS:
        bad.append(f"静かな時に、台の上の物（扇 {t + h:g}・像 {fh:g}）の上の端が口から {rest + stand - H:.1f}mm 出る")
    if inside < a - EPS:
        bad.append(f"静かな時に、内筒が外筒に {inside:.1f}mm しか入らず、一辺 {a:.1f} より短い")
    # 割り箸の決まり（貼れる長さ・開いた位置で外筒の下に残る長さ）は、型紙の床と同じ式と同じ順（雛形の chopstick_problem）で、
    # 折った形の筒の高さと内筒の長さで見る（2 つに書くと判定がずれた。見直しの指摘）
    problem = sf.chopstick_problem(L, H, p["base_glue"])
    if problem:
        bad.append(problem)
    if bad:
        failures.extend(Failure("3D.stroke", inner_label, m) for m in bad)
        return notes, failures
    notes.append(f"押し上げる {inner_label}: 台の上の面は底から {rest:.1f}mm（静かな時。扇と像は口の {H - rest - stand:.1f}mm 下に隠れ、内筒は外筒に "
                 f"{inside:.1f}mm 入る）から {H:.1f}mm（開いた位置。口の高さ）まで {s:g}mm 上がる。割り箸（{sf.CHOPSTICK_LEN}mm）は、開いた位置でも"
                 f"外筒の下へ {below:.1f}mm 出る")
    return notes, failures


def run(template_id, params, source, title=None, inject=None):
    """型紙と同じ検査（compose）を通ってから、3D で組んで確かめる。Returns (所見, 失敗)。

    型紙の検査に落ちる寸法は、組む前にその失敗を返す（落ちる寸法の部品を「組める形」として確かめないため。omochae.foldsim と同じ）。
    まだ組めない形かは、型紙の検査の後で見る。先に見ると、形の値の打ち間違いも F5.range（3）でなく「まだ組めない」（4）になった（レビューの指摘）。
    """
    p, layout, failures = compose(template_id, params, source, title=title, inject=inject or {})
    if failures:
        return [], failures
    form = p.get(TEMPLATES[template_id].FORM) if template_id == "slider_fan" else None
    if form == "rise":
        return check_rise(layout["parts"], p)
    if form != "tab":
        raise ToolMissing("まだ 3D で組めない形（組めるのは、御来迎 つまみの形と、内筒を下から押し上げる形だけ）")
    return check(layout["parts"], p)


def main(argv=None):
    ap = Parser(prog="omochae.fold3d", description="型紙の部品を 3D の中で折って組み、外筒が閉じるか・溝と竹串が並ぶかを確かめる（御来迎 "
                                                 "つまみの形と、内筒を下から押し上げる形）。先に型紙と同じ検査を通す。終了: 0 通った / 3 落ちた / 4 確かめられない")
    ap.add_argument("--scenario", help="場面の JSON（python -m omochae と同じ形）。渡すと --template・--source・--params は使わない")
    ap.add_argument("--template", default="slider_fan", help="雛形（今は slider_fan だけ組める。既定 slider_fan）")
    ap.add_argument("--source", help="data/sources/ の出典の記録の名前（既定は雛形ごと）")
    ap.add_argument("--params", help="寸法の JSON。push_part（今は tab と rise を組める）が要る")
    args = ap.parse_args(argv)
    try:
        sc = scenario_from_args(args)
        if sc["template"] not in TEMPLATES:
            raise ToolMissing(f"知らない雛形: {sc['template']}")
        notes, failures = run(sc["template"], sc["params"], load_source(sc["source_id"]), sc.get("title"), sc.get("inject"))
    except (ToolMissing, ValueError) as e:
        print(f"確かめられない: {e}", file=sys.stderr)
        return 4
    except Exception as e:  # 想定外は「通った」にも「落ちた」にも数えない。
        print(f"確かめられない: {type(e).__name__}: {e}", file=sys.stderr)
        return 4
    for n in notes:
        print(n)
    if failures:
        for f in failures:
            print(f.line(), file=sys.stderr)
        return 3
    print("紙の厚み・たわみ・摩擦は入れていない。通っても、紙で動く保証ではない")
    return 0


if __name__ == "__main__":
    sys.exit(main())
