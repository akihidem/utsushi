"""手順の紙。型紙と同じ検査（印字域・文字の重なり・印）を通す。

判断の芯: 答えを先に言わない。計算の開く角度の上限は刷らない（作る前の予想と、測った数を比べるのが目的なので）。
結果の 3 値は同じ大きさの欄で、既定の選択を置かない。
"""
from .compose import GAP, LINE, TEMPLATES, TITLE_SIZE, _block
from .floors import check_layout
from .marks import mark_lines
from .model import TextBox
from .page import PAGES
from .textfit import text_width

# 型紙より字を大きく、欄を広くする。手で書き込む紙で、子どもも使うため。
BODY_SIZE, HEAD_SIZE = 3.6, 4.4
ANSWER_GAP, FIX_ROW = 9.0, 10.0
DIAGRAM_W, DIAGRAM_H = 42.0, 62.0
RESULTS = ("動いた", "動かない", "わからない")
QUESTIONS = ("最初に動いたのはどこですか", "引っかかった所はどこですか", "何を変えると違いが出そうですか")


def steps(p):
    """組み方。部品番号は型紙と同じ。押し方と中心の置き方で変わる所だけを分ける。"""
    out = ["刷った物差しに定規を当て、10cm か確かめる", "部品を実線で切る。穴は竹串の先であける"]
    if p["push_part"] == "tab":
        out.append("1 外筒の溝をカッターで切る（大人がする）")
    out.append("1 外筒を破線で谷折りし、糊代で貼って角筒にする")
    if p["push_part"] in ("tab", "tube"):
        out.append("2 内筒も同じように角筒にする")
    if p["push_part"] == "tab":
        out.append("竹串を 2 内筒の 2 つの穴に通す")
    if p["push_part"] == "stick":
        out.append("3 台を割り箸の先に貼る")
    else:
        out.append("3 台で 2 内筒の上に蓋をする")
    out.append("4 扇を破線で谷折り、一点鎖線で山折りにして蛇腹に畳む")
    if p["hub"] == "axle":
        out.append("糸を 5 像の穴と 4 扇の中心側の穴の列に通し、ゆるく結ぶ")
        out.append("5 像の足を 3 台に貼る")
    else:
        out.append("4 扇の端を 3 台に貼り、5 像の足も台に貼る")
    if p["push_part"] == "tab":
        out.append("内筒を 1 外筒に入れ、竹串の端を溝から出す")
    else:
        out.append("押す部品を 1 外筒に下から入れる")
    return out


def _diagram(x, y, p):
    """組み上がりの断面の見取り図。寸法の図ではなく、部品の並びを見せるだけの絵。"""
    w, h = DIAGRAM_W, DIAGRAM_H
    s = (h - 8) / (p["tube_height"] + p["fold_height"])
    cx, base = x + w / 2, y + h - 4
    tw = p["tube_side"] * s
    th = p["tube_height"] * s
    shapes = [{"kind": "rect", "x": cx - tw / 2, "y": base - th, "w": tw, "h": th}]
    inner = p["pusher_side"] * s
    rest_top = base - (p["tube_height"] - p["push_amount"]) * s
    length = p["pusher_height"] * s
    if p["push_part"] == "stick":
        shapes.append({"kind": "rect", "x": cx - 0.6, "y": rest_top, "w": 1.2, "h": length, "dash": "1,0.6"})
    else:
        shapes.append({"kind": "rect", "x": cx - inner / 2, "y": rest_top, "w": inner, "h": length, "dash": "1,0.6"})
    if p["push_part"] == "tab":
        shapes.append({"kind": "line", "x1": cx - tw / 2 - 5, "y1": rest_top + length / 2, "x2": cx, "y2": rest_top + length / 2})
    shapes.append({"kind": "rect", "x": cx - 1.2, "y": rest_top - p["fold_height"] * s, "w": 2.4, "h": p["fold_height"] * s, "dash": "1,0.6"})
    return shapes


def compose_sheet(template_id, params, source, title, how_it_moves, page_name="A4", version=1):
    """Returns (layout, failures)。"""
    tpl = TEMPLATES[template_id]
    p = {**tpl.DEFAULTS, **params}
    page = PAGES[page_name]
    texts, shapes = [], []
    width = page.x1 - page.x0
    y = _block(texts, [f"手順の紙 {title}"], page.x0, page.y0, TITLE_SIZE, width)
    y = _block(texts, mark_lines(source), page.x0, y + 1, BODY_SIZE, width)
    top = y + GAP
    left_w = width - DIAGRAM_W - GAP
    diagram_x = page.x1 - DIAGRAM_W
    shapes += _diagram(diagram_x, top, p)
    texts.append(TextBox(diagram_x, top, DIAGRAM_W, DIAGRAM_H, None))
    _block(texts, ["閉じた時の中の様子（破線は筒の中）"], diagram_x, top + DIAGRAM_H + 1, 2.8, DIAGRAM_W)
    y = _block(texts, ["組み方"], page.x0, top, HEAD_SIZE, left_w)
    y = _block(texts, [f"{i}. {s}" for i, s in enumerate(steps(p), 1)], page.x0, y, BODY_SIZE, left_w)
    y = _block(texts, ["遊び方", how_it_moves, "力を入れすぎず、手でゆっくり動かす"], page.x0, y + 1, BODY_SIZE, left_w)
    y = max(y, top + DIAGRAM_H + 8) + 2

    def field(label, x, y0, w=30.0):
        lw = text_width(label, BODY_SIZE)
        texts.append(TextBox(x, y0, lw, BODY_SIZE * LINE, label, BODY_SIZE))
        shapes.append({"kind": "rect", "x": x + lw + 1.5, "y": y0, "w": w, "h": BODY_SIZE * LINE})
        texts.append(TextBox(x + lw + 1.5, y0, w, BODY_SIZE * LINE, None))
        return x + lw + w + 5

    y = _block(texts, ["作る前に"], page.x0, y, HEAD_SIZE, width)
    field("どこまで開くと思いますか（度）", page.x0, y, 30)
    y += BODY_SIZE * LINE + 3
    y = _block(texts, ["測る"], page.x0, y, HEAD_SIZE, width)
    x = field("開いた角度（度）紙の力だけ", page.x0, y, 20)
    if p["hub"] == "axle":
        field("糸あり", x, y, 20)
    y += BODY_SIZE * LINE + 2
    x = field("試した回数", page.x0, y, 15)
    field("開いた回数", x, y, 15)
    y += BODY_SIZE * LINE + 3
    y = _block(texts, ["見て考える"], page.x0, y, HEAD_SIZE, width)
    for q in QUESTIONS:
        texts.append(TextBox(page.x0, y, text_width(q, BODY_SIZE), BODY_SIZE * LINE, q, BODY_SIZE))
        y += BODY_SIZE * LINE + ANSWER_GAP
        shapes.append({"kind": "line", "x1": page.x0, "y1": y - 1.5, "x2": page.x1, "y2": y - 1.5})
    y += 1
    y = _block(texts, ["結果（1 つに丸）"], page.x0, y, HEAD_SIZE, width)
    x = page.x0
    # 3 つの欄を同じ大きさにする。「わからない」を小さくすると、選ぶのをためらわせるため。
    for r in RESULTS:
        shapes.append({"kind": "rect", "x": x, "y": y, "w": 30, "h": BODY_SIZE * LINE + 1})
        texts.append(TextBox(x + 2, y + 0.5, text_width(r, BODY_SIZE), BODY_SIZE * LINE, r, BODY_SIZE))
        x += 34
    y += BODY_SIZE * LINE + 4
    y = _block(texts, ["直した点（部品・変えた事・結果）"], page.x0, y, HEAD_SIZE, width)
    for _ in range(2):
        for col, cw in enumerate((40.0, 80.0, 70.0)):
            shapes.append({"kind": "rect", "x": page.x0 + sum((40.0, 80.0, 70.0)[:col]), "y": y, "w": cw, "h": FIX_ROW})
        texts.append(TextBox(page.x0, y, width, FIX_ROW, None))
        y += FIX_ROW
    ruler_y = y + 2
    texts.append(TextBox(page.x0, ruler_y, 100, 3, None))
    _block(texts, ["10cm の物差し。100% で刷る（用紙に合わせない）"], page.x0, ruler_y + 4, BODY_SIZE, width)
    failures = check_layout(page, [], texts)
    return {"page": page, "parts": [], "texts": texts, "samples": [], "ruler": (page.x0, ruler_y), "shapes": shapes}, failures
