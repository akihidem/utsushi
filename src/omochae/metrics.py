"""寸法の変更の向きを式で確かめる（F7）。Claude の見込みを信じず、雛形の側で数え直す。"""
from .compose import TEMPLATES
from .fan_model import clearance_limit_deg, opening_bound_deg
from .pivot_model import period_s, rest_tilt_deg


def _slider(p):
    if p.get("push_part") == "rise":
        # 内筒を下から押し上げる形（御来迎の次の組のたたき台）: 扇の下の端（要）は台の上の受けの底の紙の上にあり、台の縁と口の角に当たる
        # （slider_fan._check_rise と同じ見方）。内筒の遊びは外筒と内筒の差
        t = p["paper_thickness"]
        return {"opening_bound_deg": opening_bound_deg(p["fold_count"], p["fold_width"], p["fold_height"]),
                "clearance_limit_deg": min(clearance_limit_deg(p["tube_side"], t), clearance_limit_deg(p["base_side"], t)),
                "fold_thickness_mm": p["fold_count"] * t,
                "slide_gap_mm": p["tube_side"] - p["pusher_side"]}
    d = p["pivot_above_rim"] if p["hub"] == "axle" else 0
    return {
        "opening_bound_deg": opening_bound_deg(p["fold_count"], p["fold_width"], p["fold_height"]),
        "clearance_limit_deg": clearance_limit_deg(p["tube_side"], d),
        "fold_thickness_mm": p["fold_count"] * p["paper_thickness"],
        "slide_gap_mm": p["tube_side"] - p["pusher_side"],
    }


def _pivot(p):
    from .templates.pivot_counterweight import mass_points

    pts = mass_points(p)
    return {"period_s": period_s(pts) or 0.0, "rest_tilt_deg": abs(rest_tilt_deg(pts))}


METRICS = {"slider_fan": _slider, "pivot_counterweight": _pivot}
# 変えてよい寸法を雛形ごとに絞る。全部を開けると、仮説の違いと寸法の違いが混ざるため。
ALLOWED = {
    "slider_fan": {"fold_count", "fold_width", "fold_height", "tube_side", "pusher_side", "push_amount", "pivot_above_rim", "paper_thickness"},
    "pivot_counterweight": {"weight_g", "weight_below_axle", "weight_behind", "ear_length", "neck_length", "opening", "head_w", "head_h", "paper_gsm"},
}


def values(template, params):
    return METRICS[template]({**TEMPLATES[template].DEFAULTS, **params})
# 新しい雛形は、自分の式（metrics）と変えてよい寸法（ALLOWED）を雛形の中に持つ。この表を線ごとに書き足してぶつからないため。
for _id, _tpl in TEMPLATES.items():
    if _id not in METRICS and hasattr(_tpl, "metrics"):
        METRICS[_id] = _tpl.metrics
    if _id not in ALLOWED and hasattr(_tpl, "ALLOWED"):
        ALLOWED[_id] = set(_tpl.ALLOWED)
