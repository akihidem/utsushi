"""型紙の生成の入口: 寸法 → 配置 → 描く前の検査 → SVG/PDF → 刷った後の検査 → PNG。

終了: 0 = 通る / 3 = 落ちる / 4 = 検査できない。1 と 2 は使わない（検査の結果と道具の故障を読み分けるため）。
"""
import argparse
import json
import pathlib
import shutil
import sys

# 読み込みは main の囲いより前に走るので、ここで落ちるとトレースバックの 1 になる（#25）。omochae.foldsim もここを通る。
try:
    from .compose import TEMPLATES, compose
    from .marks import check_image_count, check_pdf
    from .model import ToolMissing, check_name
    from .tools import work_dir
except Exception as e:
    print(f"検査できない: {type(e).__name__}: {e}", file=sys.stderr)
    sys.exit(4)

ROOT = pathlib.Path(__file__).resolve().parents[2]


class Parser(argparse.ArgumentParser):
    def error(self, message):
        print(f"omochae: {message}", file=sys.stderr)
        sys.exit(4)


def _named(stem, ext):
    """出力の名前の後ろに拡張子を足す。with_suffix は最後の点から後ろを置き換えるので、tiger_v1.5 が tiger_v1 の紙を指してしまう（#28）。"""
    return stem.with_name(stem.name + ext)


def _drop(stem):
    for old in (_named(stem, x) for x in (".svg", ".pdf", ".png")):
        old.unlink(missing_ok=True)


def load_source(source_id):
    """data/sources の出典の記録を読む。型紙の書き出し（omochae.foldsim）と同じ物を使う。"""
    src = ROOT / "data/sources" / f"{check_name(source_id, 'source_id')}.json"
    if not src.exists():
        # 出典の記録を作る道具（元の repo の omochae.ingest）はこの repo に無いので、置き場だけを言う。
        # 機械の絶対のパスは出さない（受付の画面などへ、そのまま返る文なので）。
        raise ToolMissing(f"出典の記録が無い: {source_id}（data/sources に出典の記録の JSON を置く）")
    return json.loads(src.read_text(encoding="utf-8"))


def scenario_from_args(args):
    """--scenario か、--template・--source・--params から場面を作る。型紙の書き出し（omochae.foldsim）も同じ入口を使う。"""
    if args.scenario:
        return json.loads(pathlib.Path(args.scenario).read_text(encoding="utf-8"))
    # 寸法を直に渡す入口。刷る形を決める寸法（雛形の FORM）は必ず書かせる（どの形を刷ったかを、呼んだ側の JSON に残すため）。
    # 玩具の型紙の 1 枚（たたき台）がどの形かは omochae.sheets が持つ（制作者の決定 2026-11-05「玩具 1 つに型紙 1 枚」）。
    if args.template not in TEMPLATES:
        raise ToolMissing(f"知らない雛形: {args.template}（{'・'.join(TEMPLATES)} のどれか）")
    tpl = TEMPLATES[args.template]
    params = json.loads(pathlib.Path(args.params).read_text(encoding="utf-8")) if args.params else {}
    if tpl.FORM not in params:
        raise ToolMissing(f"寸法の JSON に {tpl.FORM} が要る（雛形 {args.template} の刷る形。{tpl.FORM} の値は README の「雛形」の表）")
    # 刷る形ごとに出典が違う雛形（SOURCES）は、形から既定の出典を選ぶ。1 つの SOURCE に決め打ちすると、別の形の絵に別の玩具の出典を刷った。
    default = getattr(tpl, "SOURCES", {}).get(params[tpl.FORM], tpl.SOURCE)
    return {"template": args.template, "source_id": args.source or default, "params": params, "inject": {}}


def generate(template, params, source_id, out, page="A4", version=1, title=None, inject=None):
    """型紙を 1 枚作る共通の流れ。検査に落ちれば 3 を返す。"""
    source = load_source(source_id)
    stem = pathlib.Path(out)
    _, layout, failures = compose(template, params, source, page, version, title, inject or {})
    if failures:
        # 検査に落ちた時だけ前の回の紙を消す。前に通った紙が正しい名前で残ると、今回の物と取り違える。
        # 検査できない（例外・exit 4）時は消さない。今回は何も分かっていないので、前の結果を壊す理由が無い。
        _drop(stem)
        for f in failures:
            print(f.line(), file=sys.stderr)
        return 3
    from .render import to_png, write_all  # 描く前の検査だけの時に重い読み込みをしない
    # 描く・刷った後の検査・PNG は、その回だけの仮の置き場で作り、全部済んでから正しい名前へ移す。途中で検査できなくなった
    # （例外・exit 4）時に、前の回の紙と今回の紙が混ざって残らないようにするため（前の回の紙には触らない）。
    # 置き場は出力と同じ所に毎回別の名前で作る。決まった仮の名前だと、点のある --out や、たまたま同じ名前の別の出力と重なった。
    # 同じ所に置くのは、移す（replace）が同じ機械の中の名前の付け替えで済むようにするため。
    # 限り: 3 つの紙は 1 つずつ移すので、移す途中で止まると新旧が混ざりうる（全部を一度に替える手段が無い。移すのは名前の付け替えだけ）。
    stem.parent.mkdir(parents=True, exist_ok=True)
    work = work_dir(stem.parent, ".omochae-")
    tmp = work / "page"
    try:
        pdf = write_all(layout, tmp)
        failures = check_pdf(pdf, source) + check_image_count(pdf)
        if failures:
            rejected = _named(stem, ".rejected.pdf")
            pdf.replace(rejected)  # 印の無い紙を正しい名前で残さない。
            _drop(stem)  # 前の回の紙も正しい名前で残さない（今回の物と取り違えるため）。
            for f in failures:
                print(f.line(), file=sys.stderr)
            print(f"退けた: {rejected}", file=sys.stderr)
            return 3
        to_png(pdf, tmp)
        for x in (".svg", ".pdf", ".png"):
            tmp.with_suffix(x).replace(_named(stem, x))
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print(_named(stem, ".pdf"))
    return 0


def sheet_version(args, sc):
    """題に刷る型紙の版の番号。--version が先、無ければ場面の version（見本の型紙の版。虎 v7 は 7・御来迎 v14 は 14）、どちらも無ければ 1。
    決める側の決定（2026-11-07）「紙の題の版も見本に番号を持たせる形で」。前は見本から版を渡さず、どの版の紙の題も「版 1」だった
    （サイトで v7 と出しても紙は「版 1」）。撮影中の虎 v6 の見本には番号を持たせない（刷った紙を変えない）。
    版は 1 以上の整数に限り、ほかは呼び方の誤り（4）にする（見直しの指摘: 場面の null・字・負の数が、そのまま「版 None」などと刷られた）。
    場面の title は題の全体を置き換えるので、その時は版も title に書く（凍結の場面 pos_long_title のように、題を丸ごと試す場面のため）。"""
    v = args.version if args.version is not None else sc.get("version", 1)
    if isinstance(v, bool) or not isinstance(v, int) or v < 1:
        raise ToolMissing(f"型紙の版（version）は 1 以上の整数にする（{v!r}）")
    return v


def run(args):
    sc = scenario_from_args(args)
    version = sheet_version(args, sc)
    out = args.out or f"out/templates/{sc['template']}_v{version}"
    return generate(sc["template"], sc["params"], sc["source_id"], out, args.page, version, sc.get("title"), sc["inject"])


def main():
    ap = Parser(prog="omochae", description="寸法から型紙の SVG・PDF・PNG を作り、描く前と刷った後に検査する。終了: 0 通る / 3 落ちる / 4 検査できない")
    ap.add_argument("--scenario", help="場面の JSON（template・source_id・params・inject と、あれば version・title）。examples/ と tests/frozen/scenarios/ の形。渡すと --template・--source・--params は使わない")
    # choices で縛らない。--scenario の時は --template を使わないので、併記された値で止めない（知らない名前は run が --params の時だけ落とす）。
    ap.add_argument("--template", default="slider_fan", help="雛形（" + "・".join(sorted(TEMPLATES)) + "。既定 slider_fan）")
    ap.add_argument("--source", help="data/sources/ の出典の記録の名前（既定は雛形ごと: slider_fan は御来迎、pivot_counterweight は張子の首振り虎）")
    ap.add_argument("--params", help="寸法の JSON。雛形の刷る形の寸法（slider_fan は push_part、pivot_counterweight は mount）が要る。書かない寸法は雛形の既定値")
    ap.add_argument("--page", default="A4", choices=["A4", "B4"], help="紙の大きさ（既定 A4）")
    ap.add_argument("--version", type=int, default=None, help="題に刷る版の番号（既定は場面の version、無ければ 1）")
    ap.add_argument("--out", help="出力の名前（拡張子なし）。既定は out/templates/<雛形>_v<版>")
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
