"""配置を SVG・PDF・PNG にする。判断を持たず、compose の結果をそのまま描くだけにしてある。"""
import io
import pathlib
import subprocess

import cairosvg
import drawsvg as dw
from PIL import Image
from shapely.geometry import LineString, Polygon

from .model import ToolMissing
from .textfit import FAMILY

STROKE = {"stroke": "black", "fill": "none"}
VALLEY, MOUNTAIN = "2,1", "3,1,0.6,1"


def _hatch(d, poly_pts, dx=0, dy=0):
    poly = Polygon(poly_pts)
    x0, y0, x1, y1 = poly.bounds
    span = (x1 - x0) + (y1 - y0)
    # 網掛けを斜線で描くのは、cairosvg の pattern の表示差に頼らず、どの PDF 表示でも同じに出すため。
    v = x0 - (y1 - y0)
    while v < x1:
        seg = poly.intersection(LineString([(v, y1), (v + span, y1 - span)]))
        for g in getattr(seg, "geoms", [seg]):
            if not g.is_empty and g.geom_type == "LineString":
                (a, b), (c, e) = g.coords[0], g.coords[-1]
                d.append(dw.Line(a + dx, b + dy, c + dx, e + dy, stroke="#888", stroke_width=0.12))
        v += 1.6


def to_svg(layout):
    page = layout["page"]
    d = dw.Drawing(page.w, page.h, origin=(0, 0))
    d.set_render_size(f"{page.w}mm", f"{page.h}mm")
    d.append(dw.Rectangle(0, 0, page.w, page.h, fill="white"))
    # 絵を先に描く。線を上に重ねないと、切る線と折る線が絵に隠れる。
    for q in layout["parts"]:
        for item in q.art:
            pts = [v for x, y in item["pts"] for v in (q.x + x, q.y + y)]
            if item["kind"] == "poly":
                kw = {"stroke": item["stroke"], "stroke_width": item["sw"]} if item.get("stroke") else {}
                d.append(dw.Lines(*pts, close=True, fill=item["fill"], **kw))
            else:
                d.append(dw.Lines(*pts, close=False, fill="none", stroke=item["stroke"], stroke_width=item["sw"]))
    # 手順の紙の完成のイメージ（原図、v8）。型紙の部品には貼らない（J-007）。
    for im in layout.get("images", []):
        d.append(dw.Image(im["x"], im["y"], im["w"], im["h"], data=im["data"], mime_type="image/jpeg"))
    if layout.get("paste_image"):
        buf = io.BytesIO()
        Image.new("RGB", (4, 4), "red").save(buf, format="PNG")
        d.append(dw.Image(0, 280, 5, 5, data=buf.getvalue(), mime_type="image/png"))
    for q in layout["parts"]:
        for g in q.glue:
            _hatch(d, g, q.x, q.y)
        pts = [v for x, y in q.outline for v in (q.x + x, q.y + y)]
        d.append(dw.Lines(*pts, close=True, stroke_width=0.25, **STROKE))
        for lines, dash in ((q.valley, VALLEY), (q.mountain, MOUNTAIN)):
            if q.hide_folds:
                break  # 色の境で折る部品は、折り線を刷らない（v9）。
            for (x1, y1), (x2, y2) in lines:
                d.append(dw.Line(q.x + x1, q.y + y1, q.x + x2, q.y + y2, stroke="black", stroke_width=0.18, stroke_dasharray=dash))
        for x, y, w, h in q.cuts:
            d.append(dw.Rectangle(q.x + x, q.y + y, w, h, stroke_width=0.25, **STROKE))
        for x, y, r in q.holes:
            d.append(dw.Circle(q.x + x, q.y + y, r, stroke_width=0.25, **STROKE))
    for s in layout.get("shapes", []):
        dash = {"stroke_dasharray": s["dash"]} if s.get("dash") else {}
        if s["kind"] == "rect":
            d.append(dw.Rectangle(s["x"], s["y"], s["w"], s["h"], stroke_width=0.25, **STROKE, **dash))
        elif s["kind"] == "poly":
            # 手順の紙の絵の塗り（筒の地の色、矢じり。U-25）。線の太さは絵ごとに渡し、無ければ縁を引かない。
            kw = {"stroke": s.get("stroke", "black"), "stroke_width": s["sw"]} if s.get("sw") else {}
            d.append(dw.Lines(*[v for pt in s["pts"] for v in pt], close=True, fill=s["fill"], **kw))
        else:
            d.append(dw.Line(s["x1"], s["y1"], s["x2"], s["y2"], stroke="black", stroke_width=0.25, **dash))
    for t in layout["texts"]:
        if t.text:
            # 基線は字の箱の下の方。字面の高さは約 0.88em。
            d.append(dw.Text(t.text, t.size, t.x, t.y + t.size * 0.95, font_family=FAMILY, fill="black"))
    for x, y, dash in layout["samples"]:
        if dash == "hatch":
            _hatch(d, [(x, y - 1.5), (x + 7, y - 1.5), (x + 7, y + 1), (x, y + 1)])
        else:
            kw = {"stroke_dasharray": dash} if dash else {}
            d.append(dw.Line(x, y, x + 7, y, stroke="black", stroke_width=0.25, **kw))
    # 測らない紙（手順・試した後・見比べる・先生の見る紙。U-25）は物差しを持たない。型紙は今までどおり必ず持つ。
    if layout.get("ruler"):
        rx, ry = layout["ruler"]
        d.append(dw.Line(rx, ry + 3, rx + 100, ry + 3, stroke="black", stroke_width=0.25))
        for i in range(11):
            d.append(dw.Line(rx + i * 10, ry + 3, rx + i * 10, ry + (0.5 if i % 5 == 0 else 1.5), stroke="black", stroke_width=0.2))
    return d.as_svg()


def write_all(layout, out_stem):
    stem = pathlib.Path(out_stem)
    stem.parent.mkdir(parents=True, exist_ok=True)
    svg = to_svg(layout)
    stem.with_suffix(".svg").write_text(svg, encoding="utf-8")
    pdf = stem.with_suffix(".pdf")
    cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=str(pdf))
    return pdf


def to_png(pdf, stem):
    try:
        subprocess.run(["pdftoppm", "-png", "-r", "110", "-singlefile", str(pdf), str(stem)], check=True, capture_output=True)
    except (OSError, subprocess.CalledProcessError) as e:
        raise ToolMissing(f"pdftoppm で画像にできない: {e}")
