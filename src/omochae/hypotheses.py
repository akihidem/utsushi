"""仮説を並べて見せ、使い手の予想を先に受ける入口。

判断の芯（J-002）: 仕組みを 1 つに決めて既定にしない。最初に刷る 1 枚は入口で、答えではない。
予想を書く前に AI や作者の案を見せると、予想が案に引きずられるので、予想が無いと一覧も型紙も出さない。
仮説を自分で立てたい人の道も持つ（J-008）。自分の仮説を書けば、それを型紙にでき、比べるのは本人が選ぶ時だけ。
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
    from .loop import overlay

    # 人が採った順位と新しい仮説だけを重ねる（F9）。元の記録は書き換えない。
    return overlay(json.loads(path.read_text(encoding="utf-8")))


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


def own_paths(source_id):
    return sorted(_pred_dir().glob(f"own-{source_id}-*.json"), key=lambda p: int(p.stem.rsplit("-", 1)[1]))


def own_hypotheses(source_id):
    return [json.loads(p.read_text(encoding="utf-8")) for p in own_paths(source_id)]


def save_own(source_id, name, how, evidence, params=None):
    """人が立てた仮説を残す。根拠を求めるのは、絵のどこから考えたかが後で比べる材料になるため。"""
    failures = [Failure("F9.own", field, f"{label}が空") for field, label, value in (("name", "仮説の名前", name), ("how", "動かし方", how), ("evidence", "図のどこを見たか", evidence)) if not value or not value.strip()]
    if params is not None and not isinstance(params, dict):
        failures.append(Failure("F9.own", "params", "寸法は JSON の物で渡す"))
    if failures:
        return None, failures
    n = max((int(p.stem.rsplit("-", 1)[1]) for p in own_paths(source_id)), default=0) + 1
    rec = {"id": f"OWN-{n}", "source_id": source_id, "name": name.strip(), "how_it_moves": how.strip(), "evidence": evidence.strip(), "params": params, "by": "human",
           "written_at": datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds"), "status": "untested"}
    folder = _pred_dir()
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"own-{source_id}-{n}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return rec, []


def need_prediction(source_id):
    if predictions(source_id) or own_paths(source_id):
        return []
    return [Failure("F9.prediction", source_id, "先に予想か自分の仮説を書く（python -m omochae.hypotheses predict か own）")]


def letter(h):
    return h["id"].split("-")[1]


def list_lines(data, latest, own=(), tallies=None):
    tallies = tallies or {}
    lines = [f"{data['toy']}"]
    if latest:
        lines.append(f"あなたの予想: {latest}")
    for h in own:
        lines += [f"あなたの仮説 {h['id']} {h['name']}（{h['status']}）", f"  動かし方: {h['how_it_moves']}", f"  根拠: {h['evidence']}"]
    lines += [data["note"], ""]
    for h in data["hypotheses"]:
        rank = f"人が決めた順位 {h['rank']}・" if h.get("rank") else ""
        lines.append(f"{h['id']} {h['name']}（{rank}{tallies.get(h['id'], h['status'])}）")
        lines.append(f"  動かし方: {h['how_it_moves']}")
        lines += [f"  根拠〔{e['certainty']}〕: {e['what']}（{e['where']}）" for e in h["evidence"]]
        lines += [f"  弱い所: {x}" for x in h["against"]]
        lines.append(f"  試して測る事: {h['to_measure']}")
    return lines


def _print_instructions(params, source_id, title, how, out, version, template="slider_fan"):
    """型紙と対の手順の紙を刷る。型紙と同じ印の検査を通す。"""
    from .instructions import compose_sheet
    from .marks import check_image_count, check_pdf
    from .render import to_png, write_all

    source = json.loads((ROOT / "data/sources" / f"{source_id}.json").read_text(encoding="utf-8"))
    layout, failures = compose_sheet(template, params, source, f"{title} 版 {version}", how)
    if not failures:
        stem = pathlib.Path(f"{out}_tejun")
        pdf = write_all(layout, stem)
        failures = check_pdf(pdf, source) + check_image_count(pdf)
        if not failures:
            to_png(pdf, stem)
            print(pdf)
            return 0
    for f in failures:
        print(f.line(), file=sys.stderr)
    return 3


def print_sheet(source_id, hypothesis_id, out, version=1):
    from .__main__ import generate
    from .loop import version_params

    data = load(source_id)
    match = [h for h in data["hypotheses"] if h["id"] == hypothesis_id]
    if not match:
        raise ToolMissing(f"その仮説は無い: {hypothesis_id}")
    h = match[0]
    params, adopted = version_params(source_id, hypothesis_id, version)
    if params is None:
        print(Failure("F9.human", f"{hypothesis_id} 版 {version}", "人が採っていない版は刷らない").line(), file=sys.stderr)
        return 3
    label = f"版 {version}"
    how = h["how_it_moves"]
    if adopted:
        # 紙から根拠の記録へ戻れるように刷る（F7）。
        label += "・根拠 " + "、".join(adopted["record_ids"])
        how += "。前の版から変えた所: " + "、".join(f"{c['param']} {c['from']}→{c['to']}" for c in adopted["changes"])
    title = f"{data['toy']} 型紙 仮説 {letter(h)}「{h['name']}」{label}"
    template = h.get("template") or data.get("template", "slider_fan")
    if h.get("template_id", "") is None:
        print(Failure("F9.own", hypothesis_id, "今の雛形には乗らない仮説なので型紙にできない").line(), file=sys.stderr)
        return 3
    rc = generate(template, params, source_id, out, title=title, version=version)
    if rc:
        return rc
    return _print_instructions(params, source_id, f"仮説 {letter(h)}「{h['name']}」", how, out, version, template)


def print_own(source_id, own_id, out, version=1):
    from .__main__ import generate

    match = [h for h in own_hypotheses(source_id) if h["id"] == own_id]
    if not match:
        raise ToolMissing(f"その仮説は無い: {own_id}")
    h = match[0]
    params = h["params"]
    # 雛形に無い機構を作れるふりをしない。仮説は記録として残っている。
    template = data_template = load(source_id).get("template", "slider_fan")
    key = "mount" if data_template == "pivot_counterweight" else "push_part"
    if not params or key not in params:
        print(Failure("F9.own", own_id, "今の雛形には乗らない仮説なので型紙にできない。記録としては残っている").line(), file=sys.stderr)
        return 3
    data = load(source_id)
    rc = generate(template, params, source_id, out, title=f"{data['toy']} 型紙 自分の仮説「{h['name']}」版 {version}", version=version)
    if rc:
        return rc
    return _print_instructions(params, source_id, f"自分の仮説「{h['name']}」", h["how_it_moves"], out, version, template)


def picture(source_id):
    source = json.loads((ROOT / "data/sources" / f"{source_id}.json").read_text(encoding="utf-8"))
    return f"{source['toy']} の図（出典 ID {source_id}・{source['holding']}）: {source['image_url']}"


def _generated_command(args):
    from .contrib import _human_confirm
    from .loop import _read, folder

    if args.cmd == "show-generated":
        print(json.dumps(_read(folder() / f"generated-{args.id[2:]}.json"), ensure_ascii=False, indent=2))
        return 0
    from api.generate import adopt_generated, generate

    if args.cmd == "adopt-generated":
        if not _human_confirm(args.id, "採用"):
            print(Failure("F9.human", args.id, "端末での人の確認が無い").line(), file=sys.stderr)
            return 3
        made, failures = adopt_generated(args.id, args.by, [int(x) for x in args.accept.split(",")])
        if not failures:
            print("採りました:", " ".join(made))
    else:
        source = json.loads((ROOT / "data/sources" / f"{args.source}.json").read_text(encoding="utf-8"))
        try:
            gid, failures = generate(source)
        except Exception as e:  # 鍵が無い・通信できない・予算の上限。値は出さない
            print(f"検査できない: Claude を呼べなかった（{type(e).__name__}: {str(e)[:160]}）。固定の仮説は list で見られます", file=sys.stderr)
            return 4
        if not failures:
            print(f"{gid} を作りました。show-generated で見て adopt-generated で採ります")
    for f in failures:
        print(f.line(), file=sys.stderr)
    return 3 if failures else 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="omochae.hypotheses")
    ap.add_argument("--source", default="NDL-1187053-R0000005-L")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("predict").add_argument("text")
    sub.add_parser("picture")
    sub.add_parser("list")
    sub.add_parser("generate", help="Claude がその場で仮説と寸法を作る。予想か自分の仮説が先に要る")
    sg = sub.add_parser("show-generated")
    sg.add_argument("id")
    ag = sub.add_parser("adopt-generated", help="案を人が採る")
    ag.add_argument("id")
    ag.add_argument("--by", required=True)
    ag.add_argument("--accept", required=True, help="採る案の番号。1,2 のように")
    o = sub.add_parser("own")
    o.add_argument("name")
    o.add_argument("--how", default="")
    o.add_argument("--evidence", default="")
    o.add_argument("--params", help="型紙にする時の寸法の JSON。push_part が要る")
    po = sub.add_parser("print-own")
    po.add_argument("id")
    po.add_argument("--out")
    s = sub.add_parser("print")
    s.add_argument("hypothesis")
    s.add_argument("--out")
    s.add_argument("--version", type=int, default=1)
    try:
        args = ap.parse_args(argv)
    except SystemExit as e:
        return 0 if e.code == 0 else 4
    try:
        if args.cmd in ("generate", "show-generated", "adopt-generated"):
            return _generated_command(args)
        if args.cmd == "picture":
            print(picture(args.source))
            return 0
        if args.cmd == "print-own":
            return print_own(args.source, args.id, args.out or f"out/templates/{args.id}_v1")
        if args.cmd == "own":
            rec, failures = save_own(args.source, args.name, args.how, args.evidence, json.loads(args.params) if args.params else None)
            if not failures:
                print(f"{rec['id']} を残しました。print-own で型紙にして試せます。用意された仮説と比べたくなったら list です")
                return 0
        elif args.cmd == "predict":
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
            preds = predictions(args.source)
            latest = json.loads(preds[-1].read_text(encoding="utf-8"))["text"] if preds else None
            # 記録の数は見せるが、順位は付けない。順位を変えるのは人の確認（H7）。
            from .records import all_records, summarize

            tallies = {k: f"動いた {v['動いた']}・動かない {v['動かない']}・わからない {v['わからない']}" for k, v in summarize(all_records(args.source)).items()}
            print("\n".join(list_lines(load(args.source), latest, own_hypotheses(args.source), tallies)))
            return 0
        return print_sheet(args.source, args.hypothesis, args.out or f"out/templates/{args.hypothesis}_v{args.version}", args.version)
    except (ToolMissing, OSError, ValueError, KeyError) as e:
        print(f"検査できない: {e}", file=sys.stderr)
        return 4


if __name__ == "__main__":
    sys.exit(main())
