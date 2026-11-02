"""仮説を見比べる試作（案 B、J-019）。型紙を、2 つの仮説を並べて試す実験装置として使う。

判断の芯: 見分けられると言えるのは、式で差が出る組だけ。差が出ない組を「見分ける試作」と呼ぶと実験を偽るので、
作り手の表にはそう書く。学ぶ人の紙には計算の値も見分けられるかも刷らない（答えを先に言わない。J-013）。
紙で分かるのはこの紙の動きまでで、昔の職人の作り方の証明にはならない。だから紙にそれを刷る。
"""
from itertools import combinations

from .compose import TEMPLATES
from .fan_model import clearance_limit_deg, opening_bound_deg
from .model import Failure

# 家庭で手で測る時の読みと紙のばらつきの見込み。実物の試行が 0 件なので実測ではない。
ANGLE_MARGIN = 30.0


def opening_limit_deg(p):
    """形として開ける上限。帯の長さと筒の口の角の小さい方（検査の F5.fan_clearance と同じ式）。"""
    pivot = p["pivot_above_rim"] if p["hub"] == "axle" else 0
    return min(opening_bound_deg(p["fold_count"], p["fold_width"], p["fold_height"]), clearance_limit_deg(p["tube_side"], pivot))


def _template(data):
    return data.get("template", "slider_fan")


def compare_table(data):
    """作り手用の表。虎は頭が揺れるかが物差しで、本人の判断で見分ける設計をしないので Failure を返す。"""
    if _template(data) != "slider_fan":
        return [], [Failure("F11.compare", data["source_id"], "この雛形は見分ける物差しを持たない（本人の判断。research/15）")]
    defaults = TEMPLATES["slider_fan"].DEFAULTS
    limits = {h["id"]: opening_limit_deg({**defaults, **h["params"]}) for h in data["hypotheses"]}
    rows = []
    for a, b in combinations(limits, 2):
        gap = abs(limits[a] - limits[b])
        rows.append({"a": a, "b": b, "limit_a": limits[a], "limit_b": limits[b], "by_angle": gap >= ANGLE_MARGIN})
    return rows, []


def table_lines(rows):
    lines = ["作り手用。学ぶ人に見せない。上限は形の計算で、実物は未確認"]
    for r in rows:
        low, high = sorted((r["limit_a"], r["limit_b"]))
        verdict = f"角度で分かれうる。{low:.0f}° を超えて開けば下の上限の紙では説明できない。超えなければ何も言えない" if r["by_angle"] else "角度では分かれない。動かし方で見る"
        lines.append(f"{r['a']} {r['limit_a']:.0f}° / {r['b']} {r['limit_b']:.0f}°: {verdict}")
    return lines


def pick_pair(data, a, b):
    """Returns (ha, hb, failures)。同じ仮説どうしや無い仮説は、見比べにならないので落とす。"""
    by_id = {h["id"]: h for h in data["hypotheses"]}
    missing = [x for x in (a, b) if x not in by_id]
    if missing:
        return None, None, [Failure("F8.references", "compare", f"仮説 {'、'.join(missing)} は実在しない")]
    if a == b:
        return None, None, [Failure("F11.compare", "compare", "同じ仮説どうしは見比べにならない")]
    _, failures = compare_table(data)
    return by_id[a], by_id[b], failures
