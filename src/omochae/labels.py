"""図鑑の文の印（F6.label）。決定は docs/process/decisions/J016-zukan-labels.md。

判断の芯: 読み手が「昔の本にある言葉」「試していない考え」「誰かが見た事」を取り違えないよう、文ごとに種類を持たせる。
文言は検査しない（本人の判断）。だから印の付け間違いはこの床では見つからず、見るのは印の有無と、引用の裏付けだけ。
"""
import argparse
import json
import pathlib
import sys

from .model import Failure

ROOT = pathlib.Path(__file__).resolve().parents[2]
QUOTE = "原文の引用"
# 飾りの文の印をあえて持たない。今週は作らないので、作れば印が無くて落ちる形にする。
LABELS = (QUOTE, "仮説", "観察")


def _filled(value):
    return isinstance(value, str) and bool(value.strip())


def _quote_ok(line):
    """引用は翻刻か、人が確かめた文だけ。

    Claude が複写から読んだだけの文は通さない。同じ歌でも複写 A と B で読みが割れた実例があり（data/sources）、
    読んだ者自身の確認も数えない。翻刻の書名を書いても、機械の読みが挟まれば人の確認が要る。
    """
    if _filled(line.get("checked_by")) and line["checked_by"] != line.get("read_by"):
        return True
    return _filled(line.get("transcribed_in")) and not line.get("read_by")


def check(lines):
    out = []
    for i, line in enumerate(lines):
        where = f"lines[{i}]"
        if not _filled(line.get("text")):
            out.append(Failure("F6.label", where, "文が空"))
        if line.get("label") not in LABELS:
            out.append(Failure("F6.label", where, f"印は {'／'.join(LABELS)} のどれか"))
        elif line["label"] == QUOTE and not _quote_ok(line):
            out.append(Failure("F6.label", where, "原文の引用は、翻刻か人が確かめた文だけ"))
    return out


def source_lines(source):
    """出典の読みを引用の候補として並べる。図鑑の画面はまだ無いので、今この床にかけられる実データはここだけ。

    人が採らなかった読み（rejected_by）は候補に入れない。割れた読みの片方を人が選んだ後も、もう片方は記録として出典に残すが、
    引用として出す物ではないため。
    """
    entries = source.get("transcription", {}).get("entries", [])
    return [{**entry, "label": QUOTE} for entry in entries if not entry.get("rejected_by")]


def main(argv=None):
    ap = argparse.ArgumentParser(description="図鑑の文の印を見る。0=通る 3=落ちる 4=検査できない")
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", help="文の一覧の JSON")
    group.add_argument("--source", help="出典 ID。その読みを引用として見る")
    try:
        args = ap.parse_args(argv)
    except SystemExit as e:
        return 0 if e.code == 0 else 4
    try:
        if args.file:
            lines = json.loads(pathlib.Path(args.file).read_text(encoding="utf-8"))
        else:
            lines = source_lines(json.loads((ROOT / "data/sources" / f"{args.source}.json").read_text(encoding="utf-8")))
        failures = check(lines)
    except (OSError, ValueError, AttributeError, TypeError) as e:
        print(f"検査できない: {type(e).__name__}: {e}", file=sys.stderr)
        return 4
    for f in failures:
        print(f.line(), file=sys.stderr)
    return 3 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
