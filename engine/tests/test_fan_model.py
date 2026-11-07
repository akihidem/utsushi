"""扇の幾何の検査。式の向きを数点で確かめる（向きの間違いは検査を素通りするので）。"""
from omochae.fan_model import clearance_limit_deg, opening_bound_deg, shortest_free_thread, theta_at, thread_length

assert clearance_limit_deg(30, 0) == 180
assert clearance_limit_deg(30, 10) < clearance_limit_deg(30, 21) < clearance_limit_deg(30, 40)
assert clearance_limit_deg(20, 21) > clearance_limit_deg(30, 21)
assert abs(opening_bound_deg(28, 8.5, 48) - 284.1) < 0.2
L = thread_length(30, 21, 48, 142)
assert theta_at(-48, 30, 48, L) == 0
assert abs(theta_at(21, 30, 48, L) - 142) < 0.2
assert theta_at(0, 30, 48, L) is None, "短い糸は行程の途中で突っ張る"
free = shortest_free_thread(30, 48, -48, 21)
angles = [theta_at(z, 30, 48, free) for z in range(-48, 22, 3)]
assert None not in angles and angles == sorted(angles)
