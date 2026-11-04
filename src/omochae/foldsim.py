"""型紙の折りの部品を、Origami Simulator（Ghassaei ほか、origamisimulator.org）が読める SVG に書き出す。作り手用。

本人が research/22 の取り入れる候補 5 を採った（2026-11-04）。判断の芯:
- 画面の上で立体を動かす物は本線にしない（本人の言葉、philosophy.md）。だからここは書き出しだけで、画面に組み込まない
- 予想が先（F9.prediction）。学ぶ人の画面からは道を作らず、作り手が試しの後に見るための道具にする
- Origami Simulator の色の約束: 外形（切る線）は黒、山折りは赤、谷折りは青。紙の厚みと摩擦は模擬しないので、実物と動きは違う
"""
import argparse
import pathlib
import sys

from .compose import TEMPLATES

ROOT = pathlib.Path(__file__).resolve().parents[2]
COLORS = {"outline": "#000000", "mountain": "#ff0000", "valley": "#0000ff"}


def part_svg(part):
    """1 つの部品を SVG の文字列にする。座標は mm のまま。穴と糊代は折りに関わらないので書かない。"""
    xs = [x for x, _ in part.outline]
    ys = [y for _, y in part.outline]
    x0, y0 = min(xs), min(ys)
    w, h = max(xs) - x0, max(ys) - y0
    lines = []
    pts = part.outline + part.outline[:1]
    for (a, b), (c, d) in zip(pts, pts[1:]):
        lines.append((a, b, c, d, COLORS["outline"]))
    for kind in ("mountain", "valley"):
        for (a, b), (c, d) in getattr(part, kind):
            lines.append((a, b, c, d, COLORS[kind]))
    body = "".join(f'<line x1="{a - x0:.3f}" y1="{b - y0:.3f}" x2="{c - x0:.3f}" y2="{d - y0:.3f}" stroke="{col}" stroke-width="0.3"/>'
                   for a, b, c, d, col in lines)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.3f}mm" height="{h:.3f}mm" viewBox="0 0 {w:.3f} {h:.3f}">'
            f"{body}</svg>\n")


def export(source_id, hypothesis_id, out_dir, parts=None):
    """仮説の寸法で雛形の部品を作り、折りのある部品を 1 つずつ SVG にする。書いたファイルの一覧を返す。

    parts=None（既定）は折りのある部品を全部書く。前は扇と外筒に固定していて、台・内筒や虎の胴・帯が出ず、
    虎では何も書かずに正常に終わっていた（レビュー指摘）。部品の名前で絞りたい時だけ parts を渡す。
    """
    from . import hypotheses

    data = hypotheses.load(source_id)
    match = [h for h in data["hypotheses"] if h["id"] == hypothesis_id]
    if not match:
        raise ValueError(f"その仮説は無い: {hypothesis_id}")
    # 型紙にできない仮説（template_id が null）は断る。print_sheet と同じ意味にそろえる。
    # 既定の雛形へ落とすと、仮説と無関係な寸法の折りが「その仮説の折り」として残るため（レビュー指摘）。
    if match[0].get("template_id", "") is None:
        raise ValueError(f"{hypothesis_id} は型紙にできない仮説（雛形に乗らない）なので、折りも書き出さない")
    tpl = TEMPLATES[match[0].get("template") or data.get("template", "slider_fan")]
    p = {**tpl.DEFAULTS, **match[0].get("params", {})}
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for q in tpl.parts(p):
        if (parts is None or q.key in parts) and (q.valley or q.mountain):
            f = out / f"{hypothesis_id}_{q.key}_foldsim.svg"
            f.write_text(part_svg(q), encoding="utf-8")
            written.append(f)
    return written


def main(argv=None):
    ap = argparse.ArgumentParser(prog="omochae.foldsim", description="作り手用。折りのある部品を Origami Simulator の SVG に書き出す。学ぶ人には試しの前に見せない")
    ap.add_argument("hypothesis")
    ap.add_argument("--source", default="NDL-1187053-R0000005-L")
    ap.add_argument("--out", default="out/foldsim")
    ap.add_argument("--part", action="append", help="書く部品の名前（fan・tube など）。無ければ折りのある部品を全部")
    args = ap.parse_args(argv)
    try:
        written = export(args.source, args.hypothesis, args.out, parts=args.part)
    except ValueError as e:  # 無い仮説・型紙にできない仮説。検査の約束に合わせて 3（落ちる）で返す
        print(f"FAIL foldsim [{args.hypothesis}] {e}", file=sys.stderr)
        return 3
    for f in written:
        print(f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
