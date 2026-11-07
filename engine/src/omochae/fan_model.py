"""扇の開きの幾何。紙の硬さや摩擦は扱わず、「形として開けるか」だけを見る。

なぜ式にするか: 検査で緑でも扇が筒にぶつかる形を出さないため。実際に開くかは実物で確かめる。
座標は筒の口の中心を原点、上を z の正にする。角度は真上から測る。
"""
import math


def opening_bound_deg(fold_count, fold_width, fold_height):
    """開いた外周が帯の長さに等しいと置いた、開く角度の上限。折り目で紙が立つので実際はこれより小さい。"""
    return math.degrees(fold_count * fold_width / fold_height)


def clearance_limit_deg(tube_side, pivot_above_rim):
    """扇が筒の口の角にぶつからずに開ける全角度。中心が口の高さにあれば真横までの 180°。"""
    if pivot_above_rim <= 0:
        return 180.0
    return 2 * (180 - math.degrees(math.atan2(tube_side / 2, pivot_above_rim)))


def tip(theta_deg, z, radius):
    t = math.radians(theta_deg)
    return radius * math.sin(t), z + radius * math.cos(t)


def thread_length(tube_side, pivot_above_rim, radius, half_angle_deg):
    """最も上げた時に、扇の端の先と筒の口の縁を結ぶ糸の長さ。"""
    x, y = tip(half_angle_deg, pivot_above_rim, radius)
    return math.hypot(x - tube_side / 2, y)


def theta_at(z, tube_side, radius, length):
    """中心の高さ z の時に、糸に引かれて扇の端が開く角度。糸が緩んでいる間は閉じたまま（0°）。

    None は、どの角度でも糸が届かない事を表す。実物なら糸か紙が突っ張って、そこから上がらない。
    """
    for i in range(0, 1801):
        theta = i / 10
        x, y = tip(theta, z, radius)
        if math.hypot(x - tube_side / 2, y) <= length:
            return theta
    return None


def shortest_free_thread(tube_side, radius, z_start, z_end):
    """行程の途中で突っ張らない最短の糸の長さ。扇の先は中心から半径の円の上しか動けないので、円と縁の最短距離が下限。"""
    worst, z = 0.0, z_start
    while z <= z_end:
        worst = max(worst, abs(math.hypot(tube_side / 2, z) - radius))
        z += 0.5
    return worst
