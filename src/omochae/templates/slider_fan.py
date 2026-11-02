"""雛形 slider_fan: 角筒の中で動く台に蛇腹の扇と像を載せ、押し上げると開く。

押し方は仮説の違いなので 3 つ描き分ける（docs/process/decisions/J002）。寸法の初期値の根拠は research/03。
どの値も実物では未確認。Claude が変えてよいのは RANGES にある名前の値だけで、座標には触れない。
"""
from ..model import Failure, Part

ID = "slider_fan"
DEFAULTS = {
    "push_part": "tab",
    "tube_side": 30, "tube_height": 75, "tube_glue": 8,
    "pusher_side": 26, "pusher_height": 40, "pusher_glue": 8,
    "push_amount": 29,
    "fold_height": 46, "fold_width": 10, "fold_count": 22,
    "base_side": 26, "base_glue": 6,
    "figure_w": 14, "figure_h": 36,
    "knob_width": 4,
    # 0.15mm はふつうの厚めの紙の見込み。実物の紙を測ったら置き換える。
    "paper_thickness": 0.15,
}
RANGES = {
    "tube_side": (20, 50), "tube_height": (50, 110), "tube_glue": (5, 12),
    "pusher_side": (15, 48), "pusher_height": (20, 110), "pusher_glue": (5, 12),
    "push_amount": (10, 60),
    "fold_height": (20, 60), "fold_width": (5, 15), "fold_count": (6, 40),
    "base_side": (10, 48), "base_glue": (4, 10),
    "figure_w": (8, 30), "figure_h": (15, 60),
    "knob_width": (2, 8),
    # 上限を広く取るのは、厚さの検査が範囲の検査より先に落ちないようにするため。
    "paper_thickness": (0.05, 1.5),
    "fan_length": (50, 300),
}
PUSH_PARTS = ("tab", "tube", "stick")
# 溝が筒の端に近いと紙が裂けやすい。実物で確かめるまでの安全側の見込み。
SLOT_MARGIN = 5


def spec():
    """Claude に渡す道具 get_template_spec の中身。"""
    return {"template_id": ID, "defaults": DEFAULTS, "ranges": RANGES, "push_part": PUSH_PARTS}


def check_range(p):
    out = []
    for k, v in p.items():
        if k == "push_part":
            if v not in PUSH_PARTS:
                out.append(Failure("F5.range", k, f"{v} は {PUSH_PARTS} のどれでもない"))
        elif k not in RANGES:
            out.append(Failure("F5.range", k, "知らない寸法の名前"))
        elif not isinstance(v, (int, float)) or isinstance(v, bool) or not RANGES[k][0] <= v <= RANGES[k][1]:
            out.append(Failure("F5.range", k, f"{v} は範囲 {RANGES[k]} の外"))
    return out


def slot_span(p):
    """溝の範囲を筒の底からの高さで返す。つまみは内筒の高さの中ほどに通す。"""
    rest_bottom = p["tube_height"] - p["push_amount"] - p["pusher_height"]
    low = rest_bottom + p["pusher_height"] / 2 - p["knob_width"] / 2
    return low, low + p["push_amount"] + p["knob_width"]


def check_physics(p):
    out = []
    H, s, h = p["tube_height"], p["push_amount"], p["fold_height"]
    A, a, L = p["tube_side"], p["pusher_side"], p["pusher_height"]
    length = p["fold_count"] * p["fold_width"]
    if "fan_length" in p and abs(p["fan_length"] - length) > 1e-6:
        out.append(Failure("F5.fan_length", "蛇腹の扇", f"折り数×折り幅={length} と扇の長さ {p['fan_length']} が違う"))
    if h > H - s:
        out.append(Failure("F5.fan_height", "蛇腹の扇", f"畳んだ高さ {h} が筒の空き {H - s} を超える"))
    thick = p["fold_count"] * p["paper_thickness"]
    if thick > a - 2:
        out.append(Failure("F5.fan_thickness", "蛇腹の扇", f"畳んだ厚さ {thick:.1f} が内筒の一辺−2={a - 2} を超える"))
    if not a < A - 1:
        out.append(Failure("F5.slide_clearance", "内筒", f"内筒 {a} は外筒 {A} − 1 より小さくない"))
    if p["figure_h"] > h + 6:
        out.append(Failure("F5.figure_height", "像", f"像の高さ {p['figure_h']} が折りの高さ＋6={h + 6} を超える"))
    if p["base_side"] > a:
        out.append(Failure("F5.base_size", "扇の台", f"扇の台 {p['base_side']} が内筒 {a} を超える"))
    if p["push_part"] == "tab":
        if L > H - s:
            out.append(Failure("F5.stroke", "内筒", f"内筒の長さ {L} が静止時の筒の空き {H - s} に収まらない"))
        low, high = slot_span(p)
        if low < SLOT_MARGIN or H - high < SLOT_MARGIN:
            out.append(Failure("F5.stroke", "溝", f"溝が筒の端から {SLOT_MARGIN}mm 離れない（底から {low:.1f}〜{high:.1f}）"))
    elif L < H:
        # research/03: L < H だと指が筒の外にある間に押し切れない。
        out.append(Failure("F5.stroke", "押す部品", f"長さ {L} が筒の高さ {H} より短く、押し切れない"))
    return out


def _tube(number, key, name, side, height, glue, label):
    w = side * 4
    # 糊代の角を落とすのは、貼る時に隣の面へはみ出さないようにするため。
    outline = [(0, 0), (w, 0), (w + glue, 2), (w + glue, height - 2), (w, height), (0, height)]
    return Part(number, key, name, outline, label_xy=(1.5, 1.5), label=label,
                valley=[((side * i, 0), (side * i, height)) for i in range(1, 5)],
                glue=[[(w, 0), (w + glue, 2), (w + glue, height - 2), (w, height)]])


def parts(p):
    A, H, a, L = p["tube_side"], p["tube_height"], p["pusher_side"], p["pusher_height"]
    out = []
    tube = _tube(1, "tube", "外筒", A, H, p["tube_glue"], "1 外筒")
    if p["push_part"] == "tab":
        low, high = slot_span(p)
        # 溝は 2 面目の中央。ラベルの面と離し、糊の継ぎ目からも離す。y は頁の下向きなので高さから引く。
        tube.cuts.append((A * 1.5 - (p["knob_width"] + 1) / 2, H - high, p["knob_width"] + 1, high - low))
    out.append(tube)
    if p["push_part"] in ("tab", "tube"):
        inner = _tube(2, "pusher", "内筒", a, L, p["pusher_glue"], "2 内筒")
        if p["push_part"] == "tab":
            # 向かい合う 2 面に串を通す穴。1 面だけだと串が傾いて溝の中で引っかかりやすい。
            inner.holes += [(a * 1.5, L / 2, 1.2), (a * 3.5, L / 2, 1.2)]
        out.append(inner)
    b, g = p["base_side"], p["base_glue"]
    out.append(Part(3, "base", "扇の台", [
        (g, g), (g + 1, 0), (g + b - 1, 0), (g + b, g), (g + b + g, g + 1), (g + b + g, g + b - 1),
        (g + b, g + b), (g + b - 1, g + b + g), (g + 1, g + b + g), (g, g + b), (0, g + b - 1), (0, g + 1),
    ], label_xy=(g + 1, g + 1), label="3 台",
        valley=[((g, g), (g + b, g)), ((g + b, g), (g + b, g + b)), ((g + b, g + b), (g, g + b)), ((g, g + b), (g, g))],
        glue=[[(g, g), (g + 1, 0), (g + b - 1, 0), (g + b, g)],
              [(g + b, g), (g + b + g, g + 1), (g + b + g, g + b - 1), (g + b, g + b)],
              [(g + b, g + b), (g + b - 1, g + b + g), (g + 1, g + b + g), (g, g + b)],
              [(g, g + b), (0, g + b - 1), (0, g + 1), (g, g)]]))
    n, w, h = p["fold_count"], p["fold_width"], p["fold_height"]
    fan = Part(4, "fan", "蛇腹の扇", [(0, 0), (h, 0), (h, n * w), (0, n * w)], label_xy=(1.5, 1.5), label="4 扇")
    for i in range(1, n):
        line = ((0, i * w), (h, i * w))
        # 山と谷を交互にするのが蛇腹の形そのもの。
        (fan.valley if i % 2 else fan.mountain).append(line)
    out.append(fan)
    fw, fh = p["figure_w"], p["figure_h"]
    out.append(Part(5, "figure", "像", [(0, 0), (fw, 0), (fw, fh), (0, fh)], label_xy=(1, 1.5), label="5 像"))
    return out


def materials(p):
    """紙以外に要る物。型紙の「用意する物」はここだけから刷る（2 か所に手で書かない）。"""
    lines = [f"紙: 厚さ {p['paper_thickness']}mm 前後を 1 枚（全部品を同じ紙に刷る）", "のり、はさみ、定規"]
    if p["push_part"] == "tab":
        lines += [f"竹串 1 本（長さ約 {p['tube_side'] + 20}mm に切り、先を落とす）", "カッター（溝を切る。大人がする）"]
    if p["push_part"] == "stick":
        lines += [f"割り箸 1 本（長さ約 {p['pusher_height']}mm）"]
    return lines


TITLES = {"tab": "つまみで動かす", "tube": "内筒を下から押す", "stick": "割り箸を下から押す"}
LAYOUT = {"right_column": "fan", "left_row_last": ("base", "figure")}
