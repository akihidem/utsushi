"""型紙の生成の入口: 寸法 → 配置 → 描く前の検査 → SVG/PDF → 刷った後の検査 → PNG。

終了: 0 = 通る / 3 = 落ちる / 4 = 検査できない。1 と 2 は使わない（検査の結果と道具の故障を読み分けるため）。
"""
import argparse
import json
import pathlib
import sys

from .compose import compose
from .marks import check_image_count, check_pdf
from .model import ToolMissing

ROOT = pathlib.Path(__file__).resolve().parents[2]


class Parser(argparse.ArgumentParser):
    def error(self, message):
        print(f"omochae: {message}", file=sys.stderr)
        sys.exit(4)


def generate(template, params, source_id, out, page="A4", version=1, title=None, inject=None):
    """型紙を 1 枚作る共通の流れ。検査に落ちれば 3 を返す。"""
    src = ROOT / "data/sources" / f"{source_id}.json"
    if not src.exists():
        raise ToolMissing(f"出典の記録が無い: {src}（python -m omochae.ingest を先に）")
    source = json.loads(src.read_text(encoding="utf-8"))
    _, layout, failures = compose(template, params, source, page, version, title, inject or {})
    if failures:
        for f in failures:
            print(f.line(), file=sys.stderr)
        return 3
    from .render import to_png, write_all  # 描く前の検査だけの時に重い読み込みをしない
    stem = pathlib.Path(out)
    pdf = write_all(layout, stem)
    failures = check_pdf(pdf, source) + check_image_count(pdf)
    if failures:
        rejected = stem.with_suffix(".rejected.pdf")
        pdf.replace(rejected)  # 印の無い紙を正しい名前で残さない。
        for f in failures:
            print(f.line(), file=sys.stderr)
        print(f"退けた: {rejected}", file=sys.stderr)
        return 3
    to_png(pdf, stem)
    print(pdf)
    return 0


def run(args):
    if args.scenario:
        sc = json.loads(pathlib.Path(args.scenario).read_text(encoding="utf-8"))
    else:
        # 使い手の入口は omochae.hypotheses。ここは寸法を直接試す開発用で、押し方を必ず指定させる（既定の答えを作らない）。
        params = json.loads(pathlib.Path(args.params).read_text(encoding="utf-8")) if args.params else {}
        if "push_part" not in params:
            raise ToolMissing("寸法の JSON に push_part が要る。仮説から刷るなら python -m omochae.hypotheses print")
        sc = {"template": args.template, "source_id": args.source, "params": params, "inject": {}}
    return generate(sc["template"], sc["params"], sc["source_id"], args.out, args.page, args.version, sc.get("title"), sc["inject"])


def main():
    ap = Parser(prog="omochae")
    ap.add_argument("--scenario")
    ap.add_argument("--template", default="slider_fan")
    ap.add_argument("--source", default="NDL-1187053-R0000005-L")
    ap.add_argument("--params")
    ap.add_argument("--page", default="A4", choices=["A4", "B4"])
    ap.add_argument("--version", type=int, default=1)
    ap.add_argument("--out", default="out/templates/slider_fan_v1")
    args = ap.parse_args()
    try:
        return run(args)
    except ToolMissing as e:
        print(f"検査できない: {e}", file=sys.stderr)
        return 4
    except Exception as e:  # 想定外は「通った」にも「落ちた」にも数えない。
        print(f"検査できない: {type(e).__name__}: {e}", file=sys.stderr)
        return 4


if __name__ == "__main__":
    sys.exit(main())
