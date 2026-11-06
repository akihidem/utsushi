"""雛形の族によらない描く前の検査（印字域・重なり・文字）。"""
from shapely.geometry import LineString, Point, Polygon, box

from .model import Failure


def part_poly(p):
    return Polygon([(p.x + x, p.y + y) for x, y in p.outline])


def text_poly(t):
    return box(t.x, t.y, t.x + t.w, t.y + t.h)


# 接するだけの境界を重なりと数えないための許し。計算の丸めで偽の失敗を出さない。
EPS = 1e-6
# SVG の stroke-miterlimit の既定。描画（render.py）は結合の形を指定しないので、刷られる角はこの限りまで尖る。
SVG_MITER = 4
MARK_SW = 0.35  # render.MARK_SW と同じ。floors は描く所に頼らない（検査だけを速く回すため）ので値を写す（型紙エンジンと同じ形）


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


def check_bom(rows, parts=()):
    """素材が空の部品と、置き換えの根拠が無い部品と、部品表に載っていない部品を落とす。「不明」は正直な答えなので通す。"""
    out = []
    listed = {}
    for r in rows:
        # 番号が重なると、どちらの行がどの部品か決まらない。
        if r["number"] in listed:
            out.append(Failure("F2.bom", r["name"], f"部品表の番号 {r['number']} が重なっている"))
        listed.setdefault(r["number"], r)
    for q in parts:
        # 型紙に刷る部品は番号と key で部品表と結ぶ。番号だけだと、同じ番号の別の行でも通ってしまう。
        r = listed.get(q.number)
        if r is None:
            out.append(Failure("F2.bom", q.name, f"部品 {q.number} が部品表に無い"))
        elif r["key"] != q.key:
            out.append(Failure("F2.bom", q.name, f"部品 {q.number} の部品表の行が別の物（{r['name']}）"))
    for r in rows:
        if not str(r.get("material", "")).strip():
            out.append(Failure("F2.bom", r["name"], "素材の欄が空"))
        if r.get("substituted") and not (str(r.get("original_guess", "")).strip() and str(r.get("reason", "")).strip()):
            out.append(Failure("F2.bom", r["name"], "置き換えた部品に元の素材（推定）か理由が無い"))
    return out


def check_art(parts):
    """描き直しの絵が部品の中にあり、折り線と糊代をまたがない事を見る。またぐと折った時に絵が割れる。"""
    out = []
    for p in parts:
        poly = part_poly(p)
        for item in p.art:
            pts = [(p.x + x, p.y + y) for x, y in item["pts"]]
            mark = item["kind"] == "mark"
            if mark and item.get("closed"):
                pts = pts + pts[:1]  # 閉じた印は戻る辺も刷る。開いた線で見ると、戻る辺が部品の外を通っても通る
            # 位置の印は、描く所が決めた太さ（render.MARK_SW）で刷る（型紙エンジンと同じ見方）
            sw = MARK_SW if mark else (item.get("sw", 0) if item.get("stroke") else 0)
            if item["kind"] == "poly":
                geom = Polygon(pts).buffer(-0.01)
                # 輪郭線つきの面は、線の太さの半分だけ外へ広がって刷られる。
                ink = Polygon(pts).buffer(sw / 2, join_style=2, mitre_limit=SVG_MITER) if sw else geom
            else:
                geom = LineString(pts)
                # 線は刷られる太さの帯で見る。中心線だけだと、太い線が糊代や折り線にはみ出しても通った。
                # 端は SVG の既定（butt）と同じく平らに、角は SVG の既定（miter・限り 4）と同じく尖らせる。丸く見ると角の先を見逃す。
                ink = geom.buffer(sw / 2, cap_style=2, join_style=2, mitre_limit=SVG_MITER)
                if mark:  # 印は丸い端で刷る（render の stroke-linecap="round"）。平らな端で見ると、端の半円が折り線にかかっても通る
                    ink = geom.buffer(sw / 2, cap_style=1, join_style=1)
                    # 印が穴や中の切り込みにかかると、切った時に消える
                    for hx, hy, r in p.holes:
                        if ink.intersects(Point(p.x + hx, p.y + hy).buffer(r)):
                            out.append(Failure("F5.image_box", p.name, "位置の印が穴にかかり、切ると消える"))
                    for x0, y0, w, h in p.cuts:
                        if ink.intersects(box(p.x + x0, p.y + y0, p.x + x0 + w, p.y + y0 + h)):
                            out.append(Failure("F5.image_box", p.name, "位置の印が中の切り込みにかかり、切ると消える"))
            # 部品の外かは、面なら塗りで見る。輪郭線が切る線の上に乗る絵（虎の頭）は、外へ出た半分を切り落とすので困らない。
            # 折り線と糊代は、切り落とされないので輪郭線の太さまで見る。
            inside = geom if item["kind"] == "poly" else ink
            if not poly.buffer(0.05).contains(inside):
                out.append(Failure("F5.image_box", p.name, "絵が部品の外に出ている"))
            for (x1, y1), (x2, y2) in p.valley + p.mountain:
                if ink.intersects(LineString([(p.x + x1, p.y + y1), (p.x + x2, p.y + y2)])):
                    out.append(Failure("F5.image_box", p.name, "絵が折り線をまたいでいる"))
            for g in p.glue:
                # 線も太さの帯（ink）にしたので、面積で見られる（中心線の面積は 0 で、線が糊代を横切っても通っていた）。
                if ink.intersection(Polygon([(p.x + x, p.y + y) for x, y in g])).area > EPS:
                    out.append(Failure("F5.image_box", p.name, "絵が糊代にかかっている"))
    return out


def check_holes(parts):
    """穴が部品の輪郭の中にある事を見る。雛形の式が穴を寸法から置くので、寸法によっては穴が紙の外に出る。"""
    out = []
    for p in parts:
        poly = Polygon(p.outline)
        for x, y, r in p.holes:
            if not poly.buffer(EPS).contains(Point(x, y).buffer(r)):
                out.append(Failure("F5.hole", p.name, f"穴 ({x:.1f}, {y:.1f}) が部品の外に出ている"))
    return out
