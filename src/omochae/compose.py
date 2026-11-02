"""寸法から頁の配置を作る。描画はしない（検査だけを速く回せるようにするため。道具 check_params もここを使う）。"""
from .floors import check_art, check_bom, check_layout
from .marks import mark_lines
from .model import TextBox
from .page import PAGES
from .templates import slider_fan
from .textfit import text_width, wrap

TEMPLATES = {slider_fan.ID: slider_fan}
TITLE_SIZE, BODY_SIZE, LABEL_SIZE = 5.0, 3.0, 2.8
LINE = 1.25  # 行送りの倍率。CJK の字面より少し広く取る
GAP = 4.0


def _block(texts, lines, x, y, size, width):
    """文字を折り返して置き、次の y を返す。部品の置き場をこの下から始めるために y を返す。"""
    for raw in lines:
        for line in wrap(raw, size, width):
            texts.append(TextBox(x, y, text_width(line, size), size * LINE, line, size))
            y += size * LINE
    return y


def compose(template_id, params, source, page_name="A4", version=1, title=None, inject=None):
    """Returns (merged params, layout dict, failures)。寸法の範囲か物理で落ちたら配置は作らない所までで返す。"""
    tpl, inject = TEMPLATES[template_id], inject or {}
    p = {**tpl.DEFAULTS, **params}
    failures = tpl.check_range(p)
    if failures:  # 範囲の外の値で先を計算すると、別の検査が連鎖して狙いが読めなくなる。
        return p, None, failures
    failures += tpl.check_physics(p)
    rows = tpl.bom(p)
    # 負の対照のためだけ。寸法の入力からは部品表を壊せない。
    for r in rows:
        if r["key"] == inject.get("bom_blank_material"):
            r["material"] = ""
        if r["key"] == inject.get("bom_drop_original"):
            r["original_guess"] = ""
    failures += check_bom(rows)
    page = PAGES[page_name]
    texts = []
    title = title or f"{source['toy']} 型紙（{tpl.TITLES[p['push_part']]}）版 {version}"
    y = _block(texts, [title], page.x0, page.y0, TITLE_SIZE, page.x1 - page.x0)
    y = _block(texts, mark_lines(source, inject.get("omit_marks")), page.x0, y + 1, BODY_SIZE, page.x1 - page.x0)
    # 見出しが増えれば部品の置き場も下がる。固定の y にすると行が増えた時に重なる。
    # fixed_parts_top は検査が重なりを見つける事を確かめる負の対照のためだけにあり、寸法の入力からは渡せない。
    top = inject.get("fixed_parts_top", y + GAP)
    parts = tpl.parts(p)
    by_key = {q.key: q for q in parts}
    fan = by_key["fan"]
    fan.x, fan.y = page.x1 - fan.width, top
    left_y = top
    for key in ("tube", "pusher"):
        if key in by_key:
            q = by_key[key]
            q.x, q.y = page.x0, left_y
            left_y += q.height + GAP
    base, fig = by_key["base"], by_key["figure"]
    base.x, base.y = page.x0, left_y
    fig.x, fig.y = page.x0 + base.width + GAP * 2, left_y
    left_y += max(base.height, fig.height) + GAP
    shift = inject.get("art_shift")
    if shift:  # 負の対照のためだけ。
        item = by_key[shift["part"]].art[0]
        item["pts"] = [(x + shift["dx"], y) for x, y in item["pts"]]
    move = inject.get("move_part")
    if move:  # 負の対照のためだけ。
        by_key[move["name"]].x, by_key[move["name"]].y = move["x"], move["y"]
    for q in parts:
        texts.append(TextBox(q.x + q.label_xy[0], q.y + q.label_xy[1], text_width(q.label, LABEL_SIZE),
                             LABEL_SIZE * LINE, q.label, LABEL_SIZE, owner=q.key))
    width = fan.x - page.x0 - GAP
    y = _block(texts, ["用意する物"] + [f"・{m}" for m in tpl.materials(p)], page.x0, left_y, BODY_SIZE, width)
    legend_y = y + 1
    legend = [("切る", None), ("谷折り", "2,1"), ("山折り", "3,1,0.6,1"), ("糊代", "hatch")]
    samples, x = [], page.x0
    for name, dash in legend:
        samples.append((x, legend_y + BODY_SIZE * 0.6, dash))
        texts.append(TextBox(x + 9, legend_y, text_width(name, BODY_SIZE), BODY_SIZE * LINE, name, BODY_SIZE))
        x += 9 + text_width(name, BODY_SIZE) + 3
    ruler_y = legend_y + BODY_SIZE * LINE + 2
    # 物差しは 100mm。刷りの倍率を人が確かめる唯一の手がかりなので、印字域に収まらなければ検査で落とす。
    texts.append(TextBox(page.x0, ruler_y, 100, 3, None))
    note_y = ruler_y + 4
    _block(texts, ["10cm の物差し。100% で刷る（用紙に合わせない）"], page.x0, note_y, BODY_SIZE, width)
    failures += check_layout(page, parts, texts)
    failures += check_art(parts)
    # paste_image は負の対照のためだけ。図を貼った PDF を、刷った後の検査が見つけられるか確かめる。
    return p, {"page": page, "parts": parts, "texts": texts, "samples": samples, "ruler": (page.x0, ruler_y), "paste_image": bool(inject.get("paste_image"))}, failures


def check_params(template_id, params, source, page_name="A4"):
    """道具 check_params の実体。PDF を作らず、描く前の検査の結果だけを返す。"""
    _, _, failures = compose(template_id, params, source, page_name)
    return {"passed": not failures, "errors": [f.line() for f in failures]}
