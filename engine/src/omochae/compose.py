"""寸法から頁の配置を作る。描画はしない（検査だけを速く回せるようにするため。道具 check_params もここを使う）。"""
import importlib
import pkgutil

from .floors import check_art, check_bom, check_holes, check_layout
from .marks import mark_lines
from .model import Failure, TextBox, ToolMissing
from .page import PAGES
from .textfit import text_width, wrap


def _discover():
    """templates/ の下で ID を持つ module を全部、雛形として登録する。
    手で並べた辞書にすると、雛形を並行して足す担当がみな同じ行を書き換え、合流のたびにぶつかる。置けば登録される形にして、
    雛形の担当が共有のファイルに触らずに済むようにする。名前の順に読むので、登録の順は毎回同じ。ID が重なれば黙って上書きせずに落とす。
    """
    from . import templates
    found = {}
    for info in sorted(pkgutil.iter_modules(templates.__path__), key=lambda i: i.name):
        # 1 つ壊れていると、関係の無い雛形の場面も止まる。どの雛形かを言う（#25）。
        try:
            mod = importlib.import_module(f"{templates.__name__}.{info.name}")
        except Exception as e:
            raise ToolMissing(f"雛形 {info.name} が読めない（{type(e).__name__}: {e}）") from e
        if not hasattr(mod, "ID"):
            continue
        if mod.ID in found:
            raise ToolMissing(f"雛形の ID が重なる: {mod.ID}（{found[mod.ID].__name__} と {mod.__name__}）")
        found[mod.ID] = mod
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


def compose(template_id, params, source, page_name="A4", version=1, title=None, inject=None):
    """Returns (merged params, layout dict, failures)。寸法の範囲か物理で落ちたら配置は作らない所までで返す。"""
    tpl, inject = TEMPLATES[template_id], inject or {}
    p = {**tpl.DEFAULTS, **params}
    failures = tpl.check_range(p)
    if failures:  # 範囲の外の値で先を計算すると、別の検査が連鎖して狙いが読めなくなる。
        return p, None, failures
    failures += tpl.check_physics(p)
    # 刷る形ごとに出典が違う雛形では、形と合わない出典の印を刷らない（絵と出典が別の玩具になる）。形の値が SOURCES に無ければ見ない。
    want = getattr(tpl, "SOURCES", {}).get(p.get(tpl.FORM))
    if want and source.get("source_id") != want:
        failures.append(Failure("F1.source", "出典", f"{tpl.FORM} {p[tpl.FORM]} の出典は {want} だが、{source.get('source_id')} が渡された"))
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
        # 札は 1 行（label を label_xy に）か、label_lines の行ごと。行ごとの札も、部品の枠の内に収まるかを F5.text_overlap が見る
        for text, dx, dy in q.label_lines or [(q.label, *q.label_xy)]:
            texts.append(TextBox(q.x + dx, q.y + dy, text_width(text, LABEL_SIZE), LABEL_SIZE * LINE, text, LABEL_SIZE, owner=q.key))
    y = _block(texts, ["用意する物"] + [f"・{m}" for m in tpl.materials(p)], text_x, left_y, BODY_SIZE, width)
    legend_y = y + 1
    # 谷と山の意味を添える（v8）。紙で組んで試した時、線の種類だけでは折る向きが伝わらなかったため。
    legend = [("切る", None), ("谷折り（手前にへこむ）", "2,1"), ("山折り（手前に出る）", "3,1,0.6,1"), ("糊代", "hatch")]
    # 位置の印を使う型紙だけ、凡例に足す。使わない型紙（御来迎のつまみの形など）の配置は今までどおりにする。
    if any(item["kind"] == "mark" for q in parts for item in q.art):
        legend.append(("位置の印（切らない・折らない）", "mark"))
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
