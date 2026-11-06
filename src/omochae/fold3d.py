"""型紙の部品を 3D の中で折り、角筒に閉じるか・刷った面（色の面）が外を向くかを確かめる（型紙エンジンの写し）。

写した元: 型紙エンジン paper-to-toy の main 957fcc2 の src/omochae/fold3d.py。面を折る芯（fold）と、閉じる確かめ（_close、
床の名 3D.close）・外を向く確かめ（_face、3D.face）・筒の軸と断面だけを、行を変えずに写した（README の決まり「型紙を作る仕組みと
検査を直す時は、先に paper-to-toy を直して、それからこの repo に取り込む」）。

なぜ写すか: 本人の指示（11-07）「サイトの作り方の3Dは古い型のものだから、新しいのにしないと。」で、組み立ての頁の立体
（omochae.assembly と web.kumitate）を今の組（虎 v6・御来迎 v14）で作り直す。サイトの組み立ては頁に描くために自分の折り方
（assembly.Sheet）を持つ。エンジンのこの折り方は、同じ刷る部品を別の作りで折るので、サイトの組み立てが閉じた形・色の面の向きを
取り違えていないかを、別の目で確かめられる。頁を描く元にはしない（座標の取り方が違う 2 つを頁で混ぜると、ずれが出やすい）。

写していない物: つまみの形の組み方（check と ops3d。手順の文を 3D の操作から作る）・内筒を下から押し上げる形の組み方（check_rise）・
入口（python -m omochae.fold3d）。check_rise は、上げる形（rise）の部品が main に入った後（御来迎 v14 の 3D の PR）で写す。
この repo で足した物は末の shape_gap と centroids だけ（サイトの組み立ての形と、この折り方の形を比べる口）。
面は硬い板、折り線は蝶番と見る。紙の厚み・たわみ・摩擦は入らないので、通っても紙で組める保証ではない（エンジンと同じ）。
"""
import math
from dataclasses import dataclass

from shapely.geometry import LineString, MultiPoint, Point, Polygon
from shapely.ops import split

from .model import Failure

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


# --- ここから、この repo で足した口（エンジンには無い）---
# サイトの組み立て（assembly.Sheet の行列）と、この折り方（fold の面）を比べる。2 つは座標の取り方が違う
# （この折り方は頁の y を上向きに取り直す。サイトは部品の座標のまま）。面の真ん中どうしの距離は、回す・動かす・鏡に映すで
# 変わらないので、距離の表どうしを比べれば、座標の取り方に寄らずに同じ形かを言える。


def centroids(faces):
    """折った面ごとの、頁の上の真ん中の点（2D）と、折った後の 3D の点。Returns [(2D の点, 3D の点)]。"""
    return [(f.poly.centroid.coords[0], f.at(f.poly.centroid.coords[0])) for f in faces]


def shape_gap(a, b):
    """同じ数の 3D の点の並び a と b の、点どうしの距離の差の一番大きい物（mm）。並びの i 番目どうしが同じ面を指す事。"""
    if len(a) != len(b):
        raise ValueError(f"点の数が違う（{len(a)} と {len(b)}）")
    return max((abs(math.dist(a[i], a[j]) - math.dist(b[i], b[j])) for i in range(len(a)) for j in range(i + 1, len(a))), default=0.0)
