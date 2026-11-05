"""寸法から頁の配置を作る。描画はしない（検査だけを速く回せるようにするため。道具 check_params もここを使う）。"""
from .floors import check_art, check_bom, check_holes, check_layout
from .marks import mark_lines
from .model import TextBox
from .page import PAGES
import importlib
import pkgutil

from . import templates as _templates
from .templates import pivot_counterweight, slider_fan
from .textfit import text_width, wrap

def _discover():
    """templates/ に置いた雛形を全部載せる（本人「なるべく並列ですべて作ろう」、11-04）。並列の線が、この表を手で書き足して
    ぶつからないため。必須の 2 種を先頭に置き、残りは名前の順（並びを決まった物にして、頁と試験の出力が揺れないため）。"""
    found = {slider_fan.ID: slider_fan, pivot_counterweight.ID: pivot_counterweight}
    for m in sorted(pkgutil.iter_modules(_templates.__path__), key=lambda m: m.name):
        if m.name.startswith("_"):
            continue
        mod = importlib.import_module(f"{_templates.__name__}.{m.name}")
        found.setdefault(mod.ID, mod)
    return found


TEMPLATES = _discover()
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


def set_label(texts, label, page, y_after_title):
    """組の版を題の行の右端に小さく置く（U-31）。題と重なるなら題の下に行を足し、次の y を返す。"""
    w = text_width(label, LABEL_SIZE)
    first = next(t for t in reversed(texts) if t.size == TITLE_SIZE)
    if first.y == page.y0 and first.x + first.w + 4 <= page.x1 - w:
        texts.append(TextBox(page.x1 - w, page.y0 + TITLE_SIZE * LINE - LABEL_SIZE * LINE, w, LABEL_SIZE * LINE, label, LABEL_SIZE))
        return y_after_title
    return _block(texts, [label], page.x0, y_after_title, LABEL_SIZE, page.x1 - page.x0)


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
    failures += check_bom(rows, tpl.parts(p))
    page = PAGES[page_name]
    texts = []
    title = title or f"{source['toy']} 型紙（{tpl.title(p)}）版 {version}"
    y = _block(texts, [title], page.x0, page.y0, TITLE_SIZE, page.x1 - page.x0)
    # 題の「版」は仮説の版。どの組の紙かを、照らし合わせ用に小さく刷る（U-31）。
    # 題の行の右端に置く。行を足すと縦に長い型紙（内筒が長い形）が頁に収まらなくなるため。題が長くて入らない時だけ行を足す。
    y = set_label(texts, f"刷った組 {tpl.SHEET_SET}", page, y)
    y = _block(texts, mark_lines(source, inject.get("omit_marks")), page.x0, y + 1, BODY_SIZE, page.x1 - page.x0)
    # 見出しが増えれば部品の置き場も下がる。固定の y にすると行が増えた時に重なる。
    # fixed_parts_top は検査が重なりを見つける事を確かめる負の対照のためだけにあり、寸法の入力からは渡せない。
    top = inject.get("fixed_parts_top", y + GAP)
    parts = tpl.parts(p)
    by_key = {q.key: q for q in parts}
    left_y, width, text_x = tpl.place(by_key, page, top, GAP)
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
    y = _block(texts, ["用意する物"] + [f"・{m}" for m in tpl.materials(p)], text_x, left_y, BODY_SIZE, width)
    legend_y = y + 1
    # 谷と山の意味を添える（v8）。試行のつぶやき「谷折り、山折りがわからない」（11-04）。線の種類だけでは折る向きが伝わらなかった。
    legend = [("切る", None), ("谷折り（手前にへこむ）", "2,1"), ("山折り（手前に出る）", "3,1,0.6,1"), ("糊代", "hatch")]
    samples, x = [], text_x
    for name, dash in legend:
        step = 9 + text_width(name, BODY_SIZE) + 3
        # 説明を足した凡例は、列の幅が狭い型紙（虎）では 1 行に入らない。入らない分は次の行へ送る。
        if x > text_x and x + step - 3 > text_x + width:
            x, legend_y = text_x, legend_y + BODY_SIZE * LINE + 0.5
        samples.append((x, legend_y + BODY_SIZE * 0.6, dash))
        texts.append(TextBox(x + 9, legend_y, text_width(name, BODY_SIZE), BODY_SIZE * LINE, name, BODY_SIZE))
        x += step
    ruler_y = legend_y + BODY_SIZE * LINE + 2
    # 物差しは 100mm。刷りの倍率を人が確かめる唯一の手がかりなので、印字域に収まらなければ検査で落とす。
    texts.append(TextBox(text_x, ruler_y, 100, 3, None))
    note_y = ruler_y + 4
    _block(texts, ["10cm の物差し。100% で刷る（用紙に合わせない）"], text_x, note_y, BODY_SIZE, width)
    failures += check_layout(page, parts, texts)
    failures += check_art(parts)
    failures += check_holes(parts)
    # paste_image は負の対照のためだけ。図を貼った PDF を、刷った後の検査が見つけられるか確かめる。
    return p, {"page": page, "parts": parts, "texts": texts, "samples": samples, "ruler": (text_x, ruler_y), "paste_image": bool(inject.get("paste_image"))}, failures


def check_params(template_id, params, source, page_name="A4"):
    """道具 check_params の実体。PDF を作らず、描く前の検査の結果だけを返す。"""
    _, _, failures = compose(template_id, params, source, page_name)
    return {"passed": not failures, "errors": [f.line() for f in failures]}
