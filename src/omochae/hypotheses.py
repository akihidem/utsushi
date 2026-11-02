"""仮説を並べて見せ、使い手の予想を先に受ける入口。

判断の芯（J-002）: 仕組みを 1 つに決めて既定にしない。最初に刷る 1 枚は入口で、答えではない。
予想を書く前に AI や作者の案を見せると、予想が案に引きずられるので、予想が無いと一覧も型紙も出さない。
"""
import argparse
import json
import os
import pathlib
import sys
from datetime import datetime, timedelta, timezone

from .model import Failure, ToolMissing

ROOT = pathlib.Path(__file__).resolve().parents[2]


def load(source_id):
    path = ROOT / "data/hypotheses" / f"{source_id}.json"
    if not path.exists():
        raise ToolMissing(f"仮説の記録が無い: {source_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def _pred_dir():
    return pathlib.Path(os.environ.get("OMOCHAE_DATA", ROOT / "data")) / "decisions"


def predictions(source_id):
    return sorted(_pred_dir().glob(f"prediction-{source_id}-*.json"))


def save_prediction(source_id, text):
    """人が書いた予想を残す。個人の記録なので git には入れない。"""
    if not text or not text.strip():
        return None, [Failure("F9.prediction", source_id, "予想が空")]
    folder = _pred_dir()
    folder.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone(timedelta(hours=9)))
    path = folder / f"prediction-{source_id}-{now.strftime('%Y%m%d-%H%M%S-%f')}.json"
    path.write_text(json.dumps({"source_id": source_id, "text": text.strip(), "written_at": now.isoformat(timespec="seconds"), "by": "human"}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path, []


def need_prediction(source_id):
    return [] if predictions(source_id) else [Failure("F9.prediction", source_id, "先に予想を書く（python -m omochae.hypotheses predict）")]


def letter(h):
    return h["id"].split("-")[1]


def list_lines(data, latest):
    lines = [f"{data['toy']}", f"あなたの予想: {latest}", data["note"], ""]
    for h in data["hypotheses"]:
        lines.append(f"{h['id']} {h['name']}（{h['status']}）")
        lines.append(f"  動かし方: {h['how_it_moves']}")
        lines += [f"  根拠〔{e['certainty']}〕: {e['what']}（{e['where']}）" for e in h["evidence"]]
        lines += [f"  弱い所: {x}" for x in h["against"]]
        lines.append(f"  試して測る事: {h['to_measure']}")
    return lines


def print_sheet(source_id, hypothesis_id, out, version=1):
    from .__main__ import generate

    data = load(source_id)
    match = [h for h in data["hypotheses"] if h["id"] == hypothesis_id]
    if not match:
        raise ToolMissing(f"その仮説は無い: {hypothesis_id}")
    h = match[0]
    title = f"{data['toy']} 型紙 仮説 {letter(h)}「{h['name']}」版 {version}"
    return generate("slider_fan", h["params"], source_id, out, title=title, version=version)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="omochae.hypotheses")
    ap.add_argument("--source", default="NDL-1187053-R0000005-L")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("predict").add_argument("text")
    sub.add_parser("list")
    s = sub.add_parser("print")
    s.add_argument("hypothesis")
    s.add_argument("--out")
    try:
        args = ap.parse_args(argv)
    except SystemExit as e:
        return 0 if e.code == 0 else 4
    try:
        if args.cmd == "predict":
            _, failures = save_prediction(args.source, args.text)
        else:
            failures = need_prediction(args.source)
        if failures:
            for f in failures:
                print(f.line(), file=sys.stderr)
            return 3
        if args.cmd == "predict":
            print("予想を残しました。次に list で仮説を並べて見られます")
            return 0
        if args.cmd == "list":
            latest = json.loads(predictions(args.source)[-1].read_text(encoding="utf-8"))["text"]
            print("\n".join(list_lines(load(args.source), latest)))
            return 0
        return print_sheet(args.source, args.hypothesis, args.out or f"out/templates/{args.hypothesis}_v1")
    except (ToolMissing, OSError, ValueError, KeyError) as e:
        print(f"検査できない: {e}", file=sys.stderr)
        return 4


if __name__ == "__main__":
    sys.exit(main())
