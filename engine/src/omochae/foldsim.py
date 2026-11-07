"""型紙の折りのある部品を、Origami Simulator（Ghassaei ほか、origamisimulator.org）が読める SVG に書き出す。

元の repo（utsushi）の foldsim から、部品を SVG にする所（part_svg）と色の約束をそのまま写した。入口だけを変えた:
元は仮説の記録から寸法を読んだが、この repo には仮説が無いので、型紙と同じ雛形と寸法（--template と --params、
または場面の JSON）から部品を作る。
判断の芯:
- 書き出す前に型紙と同じ検査（描く前の検査）を通す。落ちる寸法の部品を「折れる形」として渡さないため。落ちれば 3
- Origami Simulator の色の約束: 外形（切る線）は黒、山折りは赤、谷折りは青。紙の厚みと摩擦は模擬しないので、実物と動きは違う
- 色の境で折る部品（hide_folds）も、折り線のデータは持っているので書き出す（型紙に線を刷らないだけ）
終了: 0 = 書き出した（折りの無い形は、書く物が無いまま 0）/ 3 = 検査に落ちた / 4 = 書き出せない。
"""
import argparse
import math
import pathlib
import re
import shutil
import sys

from .__main__ import Parser, load_source, scenario_from_args
from .compose import TEMPLATES, compose
from .model import ToolMissing, check_name
from .tools import work_dir

COLORS = {"outline": "#000000", "mountain": "#ff0000", "valley": "#0000ff"}
# 丸い切り抜きを近づける多角形の辺の数。半径 15mm でも辺の中ほどのずれは 0.05mm 未満で、紙の切り口の幅より小さい
ROUND_SEGMENTS = 48


def part_svg(part):
    """1 つの部品を SVG の文字列にする。座標は mm のまま。外形・中を切り抜く穴（cuts の矩形と round_cuts の丸）・山折り・谷折りを書く。軸の穴と糊代は折りに関わらないので書かない。"""
    xs = [x for x, _ in part.outline]
    ys = [y for _, y in part.outline]
    x0, y0 = min(xs), min(ys)
    w, h = max(xs) - x0, max(ys) - y0
    lines = []
    pts = part.outline + part.outline[:1]
    for (a, b), (c, d) in zip(pts, pts[1:]):
        lines.append((a, b, c, d, COLORS["outline"]))
    # 中を切り抜く穴（cuts の矩形）も黒の外形の線で書く。Origami Simulator は黒を「外形と中の穴」と読む（2026-11-04 に
    # origamisimulator.org の説明で確かめた。緑は細い切れ目なので穴には使わない）。書かないと、穴の無い紙として折れて形も硬さも違う。
    for x, y, cw, ch in part.cuts:
        corners = [(x, y), (x + cw, y), (x + cw, y + ch), (x, y + ch), (x, y)]
        for (a, b), (c, d) in zip(corners, corners[1:]):
            lines.append((a, b, c, d, COLORS["outline"]))
    # 丸い切り抜きは、ROUND_SEGMENTS 本の辺の多角形にして黒で書く（Origami Simulator は線だけを読むので、円を線で近づける）
    for cx, cy, r in part.round_cuts:
        ring = [(cx + r * math.cos(2 * math.pi * i / ROUND_SEGMENTS), cy + r * math.sin(2 * math.pi * i / ROUND_SEGMENTS)) for i in range(ROUND_SEGMENTS + 1)]
        for (a, b), (c, d) in zip(ring, ring[1:]):
            lines.append((a, b, c, d, COLORS["outline"]))
    for kind in ("mountain", "valley"):
        for (a, b), (c, d) in getattr(part, kind):
            lines.append((a, b, c, d, COLORS[kind]))
    body = "".join(f'<line x1="{a - x0:.3f}" y1="{b - y0:.3f}" x2="{c - x0:.3f}" y2="{d - y0:.3f}" stroke="{col}" stroke-width="0.3"/>'
                   for a, b, c, d, col in lines)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.3f}mm" height="{h:.3f}mm" viewBox="0 0 {w:.3f} {h:.3f}">'
            f"{body}</svg>\n")


def _old_outputs(out, head):
    """前の回に同じ頭で書いた SVG。名前は <頭>_<部品の key>_foldsim.svg で、key は英小文字だけ（試験で見る）。
    glob の模様にすると、--name の [ や * が模様として読まれ、別の頭の SVG まで当たった（レビューの指摘）ので、名前を正規表現で比べる。
    """
    if not out.exists():
        return []
    pat = re.compile(re.escape(head) + r"_[a-z]+_foldsim\.svg")
    return [f for f in out.iterdir() if f.is_file() and pat.fullmatch(f.name)]


def known_parts(template_id):
    """雛形が作りうる部品の key の組。雛形の既定の寸法で、刷る形（FORM）の値ごとに部品を作って合わせる。"""
    tpl = TEMPLATES[template_id]
    return {q.key for form in tpl.FORMS for q in tpl.parts({**tpl.DEFAULTS, tpl.FORM: form})}


def export(template_id, params, source, out_dir, name=None, parts=None, title=None, inject=None):
    """雛形と寸法から部品を作り、検査を通ったら、折りのある部品を 1 つずつ SVG にする。Returns (書いたファイル, 検査の失敗)。

    parts は書き出す部品の key の組（None なら折りのある部品を全部）。知らない key は、検査より先に ValueError（何も消さない）。
    name はファイル名の頭（既定は雛形の名前）。title と inject は場面の物で、python -m omochae と同じ検査にするために compose へ渡す。
    前の回の同じ頭の SVG は、検査に落ちた時も書き出した時も残さない（部品を減らした回と混ざらないように）。
    書き出しは仮の置き場で作り、全部書けてから、新しい物を先に正しい名前へ移し、その後で今回に無い前の物を消す
    （前の物を先に消すと、移す途中で止まった時に前の物を失った）。限り: 移すのは 1 つずつなので、途中で止まると新旧が混ざりうる。
    """
    if name is not None:
        check_name(name, "--name")  # 前の SVG を消す所より先に見る
    if parts is not None:
        # 知らない key は、検査（compose）より先に落とす。雛形の部品の key は、今の寸法でなく雛形の既定の寸法と刷る形ごとに数える
        # （今の寸法で部品を作ると、範囲の外や型の違う寸法で作れず key を確かめられないまま先へ進み、前の SVG を消した）。
        keys = known_parts(template_id)
        if not set(parts) <= keys:
            raise ValueError(f"知らない部品: {'・'.join(sorted(set(parts) - keys))}（この雛形の部品は {'・'.join(sorted(keys))}）")
    _, layout, failures = compose(template_id, params, source, title=title, inject=inject or {})
    if parts is not None and layout:
        # 雛形の部品でも、今の形に無い部品（吊る形の drop など）は書けない。何も書かずに前の SVG を消さないよう、ここで落とす。
        here = {q.key for q in layout["parts"]}
        if not set(parts) <= here:
            raise ValueError(f"この形に無い部品: {'・'.join(sorted(set(parts) - here))}（この形の部品は {'・'.join(sorted(here))}）")
    out = pathlib.Path(out_dir)
    head = name or template_id
    if failures:
        for f in _old_outputs(out, head):
            f.unlink()
        return [], failures
    out.mkdir(parents=True, exist_ok=True)
    work = work_dir(out, ".foldsim-")
    try:
        made = []
        # 検査を通った配置の部品を使う（型紙に刷る物と同じ部品）。部品の座標は部品の左上が原点なので、頁の上の置き場は関わらない。
        for q in layout["parts"]:
            if (parts is None or q.key in parts) and (q.valley or q.mountain):
                f = work / f"{head}_{q.key}_foldsim.svg"
                f.write_text(part_svg(q), encoding="utf-8")
                made.append(f)
        old = _old_outputs(out, head)
        written = [f.replace(out / f.name) for f in made]
        for f in old:
            if f.name not in {w.name for w in written}:
                f.unlink()
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return written, []


def main(argv=None):
    ap = Parser(prog="omochae.foldsim", description="型紙の折りのある部品を、Origami Simulator が読める SVG（外形 黒・山折り 赤・谷折り 青）に書き出す。"
                                                  "書き出す前に型紙と同じ検査を通す。終了: 0 書き出した / 3 検査に落ちた / 4 書き出せない")
    ap.add_argument("--scenario", help="場面の JSON（python -m omochae と同じ形）。渡すと --template・--source・--params は使わない")
    ap.add_argument("--template", default="slider_fan", help="雛形（" + "・".join(sorted(TEMPLATES)) + "。既定 slider_fan）")
    ap.add_argument("--source", help="data/sources/ の出典の記録の名前（既定は雛形ごと）")
    ap.add_argument("--params", help="寸法の JSON。雛形の刷る形の寸法（slider_fan は push_part、pivot_counterweight は mount）が要る")
    ap.add_argument("--parts", help="書き出す部品の key をカンマで（例 fan,tube）。既定は折りのある部品を全部")
    ap.add_argument("--out", default="out/foldsim", help="書き出す所（既定 out/foldsim）")
    ap.add_argument("--name", help="ファイル名の頭（既定は雛形の名前）。<頭>_<部品>_foldsim.svg")
    args = ap.parse_args(argv)
    try:
        sc = scenario_from_args(args)
        if sc["template"] not in TEMPLATES:
            raise ToolMissing(f"知らない雛形: {sc['template']}")
        parts = set(args.parts.split(",")) if args.parts else None
        written, failures = export(sc["template"], sc["params"], load_source(sc["source_id"]), args.out, args.name, parts,
                                   sc.get("title"), sc.get("inject"))
    except (ToolMissing, ValueError) as e:
        print(f"書き出せない: {e}", file=sys.stderr)
        return 4
    except Exception as e:  # 想定外は「書き出した」にも「落ちた」にも数えない。
        print(f"書き出せない: {type(e).__name__}: {e}", file=sys.stderr)
        return 4
    if failures:
        for f in failures:
            print(f.line(), file=sys.stderr)
        return 3
    if not written:
        # --parts を書かずに書く物が無いのは、折りの無い形（風車・独楽など）で、誤りではない。前の回の SVG は export が消してある。
        if parts is None:
            print("折りのある部品が無い", file=sys.stderr)
            return 0
        print("書き出せない: 折りのある部品が無い（--parts を確かめる）", file=sys.stderr)
        return 4
    for f in written:
        print(f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
