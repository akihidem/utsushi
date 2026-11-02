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
QUESTIONS = ("最初に動いたのはどこですか", "引っかかった所はどこですか", "何を変えると違いが出そうですか", "作っている途中で思いついた事は何ですか")


def steps(p, template="slider_fan"):
    return TEMPLATES[template].steps(p)


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
    shapes += tpl.diagram(diagram_x, top, DIAGRAM_W, DIAGRAM_H, p)
    texts.append(TextBox(diagram_x, top, DIAGRAM_W, DIAGRAM_H, None))
    _block(texts, ["閉じた時の中の様子（破線は筒の中）"], diagram_x, top + DIAGRAM_H + 1, 2.8, DIAGRAM_W)
    y = _block(texts, ["組み方"], page.x0, top, HEAD_SIZE, left_w)
    y = _block(texts, [f"{i}. {s}" for i, s in enumerate(tpl.steps(p), 1)], page.x0, y, BODY_SIZE, left_w)
    y = _block(texts, ["遊び方", how_it_moves, "力を入れすぎず、手でゆっくり動かす"], page.x0, y + 1, BODY_SIZE, left_w)
    y = max(y, top + DIAGRAM_H + 8) + 2

    def field(label, x, y0, w=30.0):
        lw = text_width(label, BODY_SIZE)
        texts.append(TextBox(x, y0, lw, BODY_SIZE * LINE, label, BODY_SIZE))
        shapes.append({"kind": "rect", "x": x + lw + 1.5, "y": y0, "w": w, "h": BODY_SIZE * LINE})
        texts.append(TextBox(x + lw + 1.5, y0, w, BODY_SIZE * LINE, None))
        return x + lw + w + 5

    m = tpl.measures(p)
    y = _block(texts, ["作る前に"], page.x0, y, HEAD_SIZE, width)
    field(m["predict"], page.x0, y, 30)
    y += BODY_SIZE * LINE + 3
    y = _block(texts, ["測る"], page.x0, y, HEAD_SIZE, width)
    for row in m["rows"]:
        x = page.x0
        for label, w in row:
            x = field(label, x, y, w)
        y += BODY_SIZE * LINE + 2
    # 紙が返事をするまでの速さを測る。「すぐ返ってくる」を主張にするなら、作る時間の実測が要るため（J-013）。
    field("作り始めて最初に動かすまで（分）", page.x0, y, 20)
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
