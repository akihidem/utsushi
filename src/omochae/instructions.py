"""手順の紙。型紙と同じ検査（印字域・文字の重なり・印）を通す。

判断の芯: 答えを先に言わない。計算の開く角度の上限は刷らない（作る前の予想と、測った数を比べるのが目的なので）。
結果は雛形ごとの値で、同じ大きさの欄で、既定の選択を置かない。
"""
from .compose import GAP, LINE, TEMPLATES, TITLE_SIZE, _block
from .floors import check_layout
from .marks import mark_lines
from .model import Failure, TextBox
from .page import PAGES
from .textfit import text_width

# 型紙より字を大きく、欄を広くする。手で書き込む紙で、子どもも使うため。
BODY_SIZE, HEAD_SIZE = 3.6, 4.4
ANSWER_GAP, FIX_ROW = 9.0, 10.0
DIAGRAM_W, DIAGRAM_H = 42.0, 62.0
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
    y = _block(texts, ["見た事（1 つに丸）"], page.x0, y, HEAD_SIZE, width)
    x = page.x0
    # 欄を同じ大きさにする。「わからない」を小さくすると、選ぶのをためらわせるため。
    for r in tpl.RESULTS:
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


COMPARE_LIMIT = "どちらかがよく動いても、昔の作り方の証明にはなりません。紙で言えるのは、この紙がどう動くかまでです。"


def compose_compare(source, toy, ha, hb, labels, page_name="A4"):
    """2 つの仮説を見比べる紙（J-019）。計算の上限も、どちらが正しいかの欄も置かない。

    判断の芯: 問うのは「どこが違ったか」で、勝ち負けを決めない（記録は観察で成績にしない。philosophy.md）。
    """
    page = PAGES[page_name]
    width = page.x1 - page.x0
    texts, shapes = [], []
    y = _block(texts, [f"見比べる紙 {toy} 仮説 {labels[0]} と 仮説 {labels[1]}"], page.x0, page.y0, TITLE_SIZE, width)
    y = _block(texts, mark_lines(source), page.x0, y + 1, BODY_SIZE, width)
    # 型紙が同じ仮説の組（御来迎の C と D）は動かし方だけが違う。2 個作らせると、作りの差が動かし方の差に混ざる。
    same = (ha.get("template"), ha.get("params")) == (hb.get("template"), hb.get("params"))
    head = "型紙は 1 つ。1 個を作り、同じ物を 2 通りの動かし方で試す" if same else "2 つの型紙を同じ紙で刷って作り、同じ手で試す"
    y = _block(texts, [head], page.x0, y + GAP, HEAD_SIZE, width)
    for label, h in zip(labels, (ha, hb)):
        y = _block(texts, [f"{label}: {h['name']}", h["how_it_moves"], f"見る物: {h['to_measure']}"], page.x0, y + 1, BODY_SIZE, width)
    y = _block(texts, ["作る前に: どちらがどう違うと思いますか"], page.x0, y + GAP, HEAD_SIZE, width)
    y += ANSWER_GAP
    shapes.append({"kind": "line", "x1": page.x0, "y1": y - 1.5, "x2": page.x1, "y2": y - 1.5})
    y = _block(texts, ["測る（紙の力だけ。3 回）"], page.x0, y + GAP, HEAD_SIZE, width)
    for label in labels:
        x = page.x0
        for n in (1, 2, 3):
            head = f"{label} {n} 回目（度）"
            lw = text_width(head, BODY_SIZE)
            texts.append(TextBox(x, y, lw, BODY_SIZE * LINE, head, BODY_SIZE))
            shapes.append({"kind": "rect", "x": x + lw + 1.5, "y": y, "w": 22, "h": BODY_SIZE * LINE})
            texts.append(TextBox(x + lw + 1.5, y, 22, BODY_SIZE * LINE, None))
            x += lw + 28
        y += BODY_SIZE * LINE + 2
    y = _block(texts, ["見て考える"], page.x0, y + GAP, HEAD_SIZE, width)
    for q in ("2 つでどこが違いましたか", "違いが出なかった所はどこですか", "もう 1 つ見比べるなら、何を変えますか"):
        texts.append(TextBox(page.x0, y, text_width(q, BODY_SIZE), BODY_SIZE * LINE, q, BODY_SIZE))
        y += BODY_SIZE * LINE + ANSWER_GAP
        shapes.append({"kind": "line", "x1": page.x0, "y1": y - 1.5, "x2": page.x1, "y2": y - 1.5})
    y = _block(texts, [COMPARE_LIMIT], page.x0, y + 1, BODY_SIZE, width)
    ruler_y = y + 2
    texts.append(TextBox(page.x0, ruler_y, 100, 3, None))
    _block(texts, ["10cm の物差し。100% で刷る（用紙に合わせない）"], page.x0, ruler_y + 4, BODY_SIZE, width)
    failures = check_layout(page, [], texts)
    return {"page": page, "parts": [], "texts": texts, "samples": [], "ruler": (page.x0, ruler_y), "shapes": shapes}, failures


def compose_after(source, title, after, page_name="A4"):
    """試した後の紙。対比を先に見せ、説明は折って閉じた札にする（J-013）。

    判断の芯: 説明を渡さず、次に変える条件を先に渡す。ただし誤った結論のまま終わらないよう、説明は手元に置いて自分で開ける。
    札は谷折りで白い帯の上に重ねて隠す。端末でなく紙で閉じるので、子どもに AI も鍵も要らない。
    """
    page = PAGES[page_name]
    width = page.x1 - page.x0
    texts, shapes = [], []
    y = _block(texts, [f"試した後の紙 {title}"], page.x0, page.y0, TITLE_SIZE, width)
    y = _block(texts, mark_lines(source), page.x0, y + 1, BODY_SIZE, width)
    y = _block(texts, ["渡す人へ: 下の札を点線で谷折りし、端をテープで止めてから、試した後に渡す"], page.x0, y + 1, BODY_SIZE, width)
    y = _block(texts, ["次はこれを変えて試す（予想を書いてから）"], page.x0, y + GAP, HEAD_SIZE, width)
    for c in after["contrasts"]:
        y = _block(texts, [c["change"], f"見る物: {c['watch']}"], page.x0, y + 1, BODY_SIZE, width)
        y += ANSWER_GAP
        shapes.append({"kind": "line", "x1": page.x0, "y1": y - 1.5, "x2": page.x1, "y2": y - 1.5})
    # 次の条件でも測るので物差しを刷る。折り上げる帯より上に置く。
    ruler_y = y + 1
    texts.append(TextBox(page.x0, ruler_y, 100, 3, None))
    y = ruler_y + 4
    trial = []
    height = _block(trial, ["札: 自分で開いた時だけ読む", *after["card"]], page.x0, 0, BODY_SIZE, width)
    fold = page.y1 - height - 1
    failures = []
    # 札を折り上げた先に文字があると隠れ方が崩れるので、重なる帯を空けられない時は刷らない。
    if fold - height - 1 < y:
        failures.append(Failure("F5.fold", title, "札を折って隠す帯が取れない"))
    shapes.append({"kind": "line", "x1": page.x0, "y1": fold, "x2": page.x1, "y2": fold, "dash": "1.5,1.5"})
    _block(texts, ["札: 自分で開いた時だけ読む", *after["card"]], page.x0, fold + 1, BODY_SIZE, width)
    failures += check_layout(page, [], texts)
    return {"page": page, "parts": [], "texts": texts, "samples": [], "ruler": (page.x0, ruler_y), "shapes": shapes}, failures
