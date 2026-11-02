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


def run(args):
    if args.scenario:
        sc = json.loads(pathlib.Path(args.scenario).read_text(encoding="utf-8"))
    else:
        params = json.loads(pathlib.Path(args.params).read_text(encoding="utf-8")) if args.params else {}
        sc = {"template": args.template, "source_id": args.source, "params": params, "inject": {}}
    src = ROOT / "data/sources" / f"{sc['source_id']}.json"
    if not src.exists():
        raise ToolMissing(f"出典の記録が無い: {src}（python -m omochae.ingest を先に）")
    source = json.loads(src.read_text(encoding="utf-8"))
    _, layout, failures = compose(sc["template"], sc["params"], source, args.page, args.version, sc.get("title"), sc["inject"])
    if failures:
        for f in failures:
            print(f.line(), file=sys.stderr)
        return 3
    from .render import to_png, write_all  # 描く前の検査だけの時に重い読み込みをしない
    stem = pathlib.Path(args.out)
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
