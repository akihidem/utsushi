"""雛形の族によらない描く前の検査（印字域・重なり・文字）。"""
from shapely.geometry import Polygon, box

from .model import Failure


def part_poly(p):
    return Polygon([(p.x + x, p.y + y) for x, y in p.outline])


def text_poly(t):
    return box(t.x, t.y, t.x + t.w, t.y + t.h)


# 接するだけの境界を重なりと数えないための許し。計算の丸めで偽の失敗を出さない。
EPS = 1e-6


def check_layout(page, parts, texts):
    out = []
    area = box(page.x0, page.y0, page.x1, page.y1)
    polys = {p.key: part_poly(p) for p in parts}
    for p in parts:
        if not area.buffer(EPS).contains(polys[p.key]):
            out.append(Failure("F5.print_area", p.name, f"印字域の外に出ている {tuple(round(v, 1) for v in polys[p.key].bounds)}"))
    for t in texts:
        if not area.buffer(EPS).contains(text_poly(t)):
            out.append(Failure("F5.print_area", t.text or "物差し", "文字が印字域の外に出ている"))
    for i, a in enumerate(parts):
        for b in parts[i + 1:]:
            if polys[a.key].intersection(polys[b.key]).area > EPS:
                out.append(Failure("F5.overlap", f"{a.name}/{b.name}", "部品が重なっている"))
    for i, a in enumerate(texts):
        ta = text_poly(a)
        for b in texts[i + 1:]:
            if ta.intersection(text_poly(b)).area > EPS:
                out.append(Failure("F5.text_overlap", a.text or "物差し", f"文字が「{b.text or '物差し'}」と重なっている"))
        if a.owner:
            # 部品のラベルは自分の部品の中に収まっていれば枠をまたがない。他の部品との重なりは F5.overlap が見る。
            if not polys[a.owner].buffer(EPS).contains(ta):
                out.append(Failure("F5.text_overlap", a.text, "ラベルが部品の枠をまたいでいる"))
        else:
            for p in parts:
                if ta.intersection(polys[p.key]).area > EPS:
                    out.append(Failure("F5.text_overlap", a.text or "物差し", f"文字が部品「{p.name}」と重なっている"))
    return out


def check_bom(rows):
    """素材が空の部品と、置き換えの根拠が無い部品を落とす。「不明」は正直な答えなので通す。"""
    out = []
    for r in rows:
        if not str(r.get("material", "")).strip():
            out.append(Failure("F2.bom", r["name"], "素材の欄が空"))
        if r.get("substituted") and not (str(r.get("original_guess", "")).strip() and str(r.get("reason", "")).strip()):
            out.append(Failure("F2.bom", r["name"], "置き換えた部品に元の素材（推定）か理由が無い"))
    return out
