"""首振りの振り子の式。紙の曲がりと摩擦は入れず、向きと桁を見るための計算。

なぜ式にするか: 直す向きを言葉で決めると間違えやすいので、変える前に数える。
座標は軸を原点、前を x の正、下を z の正にする。質量は g、長さは mm。
"""
import math

G = 9800.0  # mm/s²


def paper_mass(area_mm2, gsm):
    return area_mm2 * 1e-6 * gsm


def center(points):
    """points は (質量, x, z)。重心の x・z と全質量を返す。"""
    total = sum(m for m, _, _ in points)
    return sum(m * x for m, x, _ in points) / total, sum(m * z for m, _, z in points) / total, total


def rest_tilt_deg(points):
    """重心が軸の真下に来るまで傾く角度。頭が上がるか下がるかの見当。"""
    x, z, _ = center(points)
    return math.degrees(math.atan2(x, z))


def period_s(points):
    """小さく揺れる時の周期。重心が軸より上か真上なら揺れないので None。"""
    x, z, total = center(points)
    d = math.hypot(x, z)
    if z <= 0 or d == 0:
        return None
    inertia = sum(m * (px * px + pz * pz) for m, px, pz in points)
    return 2 * math.pi * math.sqrt(inertia / (total * G * d))
