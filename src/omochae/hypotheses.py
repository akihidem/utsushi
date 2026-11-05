"""玩具ごとの仮説の記録と、型紙を刷る入口。

判断の芯（J-032、本人の決定 11-05）: 型紙は説を羅列せず、玩具 1 つに 1 枚のたたき台にする。たたき台は記録の欄 "sheet" が指し、
読む所は sheet_of の 1 つ。選ぶのは「最初に作る紙」を決める事だけで、正しさの判定でも順位でもない（J-025）。
ほかの仮説は作る側の控えとして記録に残す（試した記録 R-0001・R-0002 と型紙の直し T-0001 が仮説の番号で結ばれているため）。
前の芯（J-002）は「仕組みを 1 つに決めて既定にしない。仮説を並べる」だった。J-032 で置き換えた。
前は予想が無いと一覧も型紙も出さなかった（F9.prediction）。本人の決定（11-05、#242）「予想の段を無くして、すぐ作る形にする」で門を外した。
型紙は正解でなく AI が考えた仮説（本人の言葉、11-05）。答えに読まれない事は、門でなく札と紙の印で守る。
仮説を自分で立てたい人の道も持つ（J-008）。自分の仮説を書けば記録に残り、寸法を付ければ型紙にでき、比べるのは本人が選ぶ時だけ。
"""
import argparse
import base64
import json
import os
import pathlib
import sys
from datetime import datetime, timedelta, timezone

from . import store
from .model import Failure, ToolMissing

ROOT = pathlib.Path(__file__).resolve().parents[2]


def load(source_id):
    path = ROOT / "data/hypotheses" / f"{source_id}.json"
    if not path.exists():
        raise ToolMissing(f"仮説の記録が無い: {source_id}")
    from .loop import overlay

    # 人が採った新しい仮説だけを重ねる（F9）。元の記録は書き換えない。順位は持たない（J-025）。
    return overlay(json.loads(path.read_text(encoding="utf-8")))


def _pred_dir():
    return pathlib.Path(os.environ.get("OMOCHAE_DATA", ROOT / "data")) / "decisions"


def files_of(folder, kind, source_id):
    """置き場の `{kind}-{玩具の ID}-….json` のうち、中の source_id がその玩具の物だけを名前の順で返す。

    なぜ名前だけで数えないか: 1 コマに複数の玩具が入り、ID の末尾に枝番（…-L-3）が付いた。名前の前方一致だと、
    枝番つきの玩具の記録が、枝番なしの玩具（…-L）の記録として数えられる。試作の玩具に書いた記録で、御来迎の門が開いた（#147）。
    自分の仮説・型紙の確定が同じ形だったので、ここ 1 つにまとめた。
    読めない記録は数えず、どのファイルかを stderr に出す。書きかけの 1 つで門を開けないためと、頁を止めないため。
    """
    out = []
    for path in sorted(folder.glob(f"{kind}-{source_id}-*.json")):
        rec = store.read_json_or_skip(path)
        if rec is not None and rec.get("source_id") == source_id:
            out.append(path)
    return out


def own_paths(source_id):
    return sorted(files_of(_pred_dir(), "own", source_id), key=lambda p: int(p.stem.rsplit("-", 1)[1]))


def own_hypotheses(source_id):
    return [json.loads(p.read_text(encoding="utf-8")) for p in own_paths(source_id)]


def save_own(source_id, name, how, evidence, params=None):
    """人が立てた仮説を残す。根拠を求めるのは、絵のどこから考えたかが後で比べる材料になるため。"""
    failures = [Failure("F9.own", field, f"{label}が空") for field, label, value in (("name", "仮説の名前", name), ("how", "動かし方", how), ("evidence", "図のどこを見たか", evidence)) if not value or not value.strip()]
    if params is not None and not isinstance(params, dict):
        failures.append(Failure("F9.own", "params", "寸法は JSON の物で渡す"))
    if failures:
        return None, failures
    folder = _pred_dir()
    folder.mkdir(parents=True, exist_ok=True)
    with store.locked(folder):
        n = max((int(p.stem.rsplit("-", 1)[1]) for p in own_paths(source_id)), default=0) + 1
        rec = {"id": f"OWN-{n}", "source_id": source_id, "name": name.strip(), "how_it_moves": how.strip(), "evidence": evidence.strip(), "params": params, "by": "human",
               "written_at": datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds"), "status": "untested"}
        store.write_json(folder / f"own-{source_id}-{n}.json", rec)
    return rec, []


def sheet_of(source_id):
    """玩具のたたき台の仮説を返す。ほかの所（頁・輪・デモ）がたたき台を知る時は、ここだけを読む。

    なぜ欄で持つか: 記録の先頭（H-A）と決めて並びで読むと、並びを変えただけでたたき台が変わる。欄にすれば、
    本人が別の仮説に替える時も 1 か所で済む（御来迎は H-A と H-C で迷いがあった。#332 の点 1）。
    """
    data = load(source_id)
    match = [h for h in data["hypotheses"] if h["id"] == data.get("sheet")]
    if not match:
        raise ToolMissing(f"たたき台の紙の欄が無いか、指す仮説が無い: {source_id}")
    return match[0]


def stage(source_id):
    """玩具の段。必須の 2 種は印が無く "必須"。全部を作る線で足した玩具は記録に "試作" と書き、入口の主役には出さない
    （凍結の床は必須の 2 種の完成で、試作が床を崩さないため。本人の指示 11-04）。"""
    return load(source_id).get("stage", "必須")


def letter(h):
    return h["id"].split("-")[1]


def list_lines(data, own=()):
    lines = [f"{data['toy']}"]
    for h in own:
        lines += [f"あなたの仮説 {h['id']} {h['name']}（{h['status']}）", f"  動かし方: {h['how_it_moves']}", f"  根拠: {h['evidence']}"]
    lines += [data["note"], ""]
    for h in data["hypotheses"]:
        lines.append(f"{h['id']} {h['name']}（{h['status']}）")
        lines.append(f"  動かし方: {h['how_it_moves']}")
        lines += [f"  根拠〔{e['certainty']}〕: {e['what']}（{e['where']}）" for e in h["evidence"]]
        lines += [f"  弱い所: {x}" for x in h["against"]]
        lines.append(f"  試して測る事: {h['to_measure']}")
    return lines


def _print_instructions(params, source_id, title, how, out, version, template="slider_fan", mark=None):
    """型紙と対の手順の紙を刷る。型紙と同じ印の検査を通す。"""
    from .instructions import compose_sheet
    from .marks import check_image_count, check_pdf
    from .render import to_png, write_all

    source = json.loads((ROOT / "data/sources" / f"{source_id}.json").read_text(encoding="utf-8"))
    if mark:
        source["hypothesis_mark"] = mark
    # 完成のイメージとして原図を手順の紙に試しに載せる（本人の決定、11-04、goraigo-v8）。型紙には貼らない（J-007 のまま）。
    # 原図の写しは git の外（out/sources、ingest が取る）なので、無い所では載せずに刷る。
    pic = ROOT / "out/sources" / f"{source_id}.jpg"
    picture = pic if template == "slider_fan" and pic.exists() else None
    layout, failures = compose_sheet(template, params, source, f"{title} 版 {version}", how, picture=picture)
    if not failures:
        stem = pathlib.Path(f"{out}_tejun")
        pdf = write_all(layout, stem)
        failures = check_pdf(pdf, source) + check_image_count(pdf, expected=len(layout.get("images", [])))
        if not failures:
            to_png(pdf, stem)
            print(pdf)
            return _print_after(source, title, out)
    for f in failures:
        print(f.line(), file=sys.stderr)
    return 3


def _print_after(source, title, out):
    """試した後の紙を刷る。手順の紙と分けるのは、試す前に渡さないため（J-013）。"""
    from .instructions import compose_after
    from .marks import check_image_count, check_pdf
    from .render import to_png, write_all

    from .compose import TEMPLATES

    data = load(source["source_id"])
    sheet_set = TEMPLATES[data.get("template", "slider_fan")].SHEET_SET
    layout, failures = compose_after(source, title, data["after_try"], sheet_set=sheet_set)
    if not failures:
        stem = pathlib.Path(f"{out}_after")
        pdf = write_all(layout, stem)
        failures = check_pdf(pdf, source) + check_image_count(pdf)
        if not failures:
            to_png(pdf, stem)
            print(pdf)
            return 0
    for f in failures:
        print(f.line(), file=sys.stderr)
    return 3


def print_free(source_id, title, how, evidence, out, mark=None):
    """型紙に乗らない仮説に、型紙なしの紙を刷る（本人の決定）。寸法は出さないので F9.own の線は変えない。"""
    from .compose import TEMPLATES
    from .instructions import compose_free
    from .marks import check_image_count, check_pdf
    from .render import to_png, write_all

    source = json.loads((ROOT / "data/sources" / f"{source_id}.json").read_text(encoding="utf-8"))
    if mark:
        source["hypothesis_mark"] = mark
    results = TEMPLATES[load(source_id).get("template", "slider_fan")].RESULTS
    layout, failures = compose_free(source, title, how, evidence, results)
    if not failures:
        stem = pathlib.Path(f"{out}_free")
        pdf = write_all(layout, stem)
        failures = check_pdf(pdf, source) + check_image_count(pdf)
        if not failures:
            to_png(pdf, stem)
            # 落ちたのではないので FAIL の行にしない。型紙にしなかった事（F9.own）は知らせる。
            print(f"F9.own: {title} は今の雛形に乗らないので型紙にはせず、型紙なしの紙を刷った", file=sys.stderr)
            print(pdf)
            return 0
    for f in failures:
        print(f.line(), file=sys.stderr)
    return 3


def print_teacher(source_id, out):
    """先生の見る紙を刷る（U-25 の案 4）。仮説に依らない 1 枚。

    先生は授業の前に刷っておくため。紙に答えも仮説も載らない。
    """
    from .compose import TEMPLATES
    from .instructions import compose_teacher
    from .marks import check_image_count, check_pdf
    from .render import to_png, write_all

    data = load(source_id)
    source = json.loads((ROOT / "data/sources" / f"{source_id}.json").read_text(encoding="utf-8"))
    layout, failures = compose_teacher(source, data["toy"], sheet_set=TEMPLATES[data.get("template", "slider_fan")].SHEET_SET)
    if not failures:
        stem = pathlib.Path(out)
        pdf = write_all(layout, stem)
        failures = check_pdf(pdf, source) + check_image_count(pdf)
        if not failures:
            to_png(pdf, stem)
            print(pdf)
            return 0
    for f in failures:
        print(f.line(), file=sys.stderr)
    return 3


def print_sheet(source_id, hypothesis_id, out, version=1, pending=None):
    """pending は、まだ記録していない版の中身。刷れると分かってから版の記録を書くために渡す（#158）。"""
    from .__main__ import generate
    from .loop import version_params

    data = load(source_id)
    match = [h for h in data["hypotheses"] if h["id"] == hypothesis_id]
    if not match:
        raise ToolMissing(f"その仮説は無い: {hypothesis_id}")
    h = match[0]
    # 必須 2 種の今の組（goraigo-v10・tora-v3）は、たたき台の 1 枚（と対の手順の紙）だけを刷る（本人の決定 11-05 の点 3、J-032）。
    # 人が輪や生成で採って重ねた新しい仮説（H-N…）も作る側の控えなので、同じく刷らない。
    # 試作の玩具は、作る側がこの口から控えを刷れる（道は閉じない）。頁からは刷らない（web の /print の口が断る）。
    if data.get("stage", "必須") == "必須" and hypothesis_id != data.get("sheet"):
        print(Failure("F9.human", f"{source_id} {hypothesis_id}", f"必須 2 種の今の組は、たたき台（{data.get('sheet')}）の紙だけを刷る").line(), file=sys.stderr)
        return 3
    params, adopted = (pending["params"], pending) if pending else version_params(source_id, hypothesis_id, version)
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
        evidence = "、".join(f"{e['what']}（{e['where']}）" for e in h.get("evidence", []))
        return print_free(source_id, f"仮説 {letter(h)}「{h['name']}」", h["how_it_moves"], evidence, out)
    rc = generate(template, params, source_id, out, title=title, version=version)
    if rc:
        return rc
    return _print_instructions(params, source_id, f"仮説 {letter(h)}「{h['name']}」", how, out, version, template)


def print_after(source_id, hypothesis_id, out):
    """試した後の紙だけを刷る（#320）。場で配られた紙で作って記録を残した人に渡すため。
    型紙と手順の紙は刷らない: 版の PDF があれば刷った案と読まれ、窓の最初の案や記録の欄の既定が、開いただけの案へ移る。題と印は型紙の組を刷る時と同じ。"""
    from .marks import OWN_HYPOTHESIS

    source = json.loads((ROOT / "data/sources" / f"{source_id}.json").read_text(encoding="utf-8"))
    match = [h for h in load(source_id)["hypotheses"] if h["id"] == hypothesis_id]
    if match:
        return _print_after(source, f"仮説 {letter(match[0])}「{match[0]['name']}」", out)
    own = [h for h in own_hypotheses(source_id) if h["id"] == hypothesis_id]
    if not own:
        raise ToolMissing(f"その仮説は無い: {hypothesis_id}")
    source["hypothesis_mark"] = OWN_HYPOTHESIS  # 人が立てた仮説を「AI が考えた」と刷らない
    return _print_after(source, f"自分の仮説「{own[0]['name']}」", out)


def print_own(source_id, own_id, out, version=1):
    from .__main__ import generate
    from .marks import OWN_HYPOTHESIS  # 人が立てた仮説を「AI が考えた」と刷らない

    match = [h for h in own_hypotheses(source_id) if h["id"] == own_id]
    if not match:
        raise ToolMissing(f"その仮説は無い: {own_id}")
    h = match[0]
    params = h["params"]
    # 雛形に無い機構を作れるふりをしない。仮説は記録として残っている。
    template = data_template = load(source_id).get("template", "slider_fan")
    from .compose import TEMPLATES

    # 仮説を分ける寸法の名前は雛形が持つ（HYP_KEY）。試作の雛形の自分の仮説でも同じ検査にするため。
    key = TEMPLATES[data_template].HYP_KEY
    if not params or key not in params:
        return print_free(source_id, f"自分の仮説「{h['name']}」", h["how_it_moves"], h["evidence"], out, mark=OWN_HYPOTHESIS)
    data = load(source_id)
    rc = generate(template, params, source_id, out, title=f"{data['toy']} 型紙 自分の仮説「{h['name']}」版 {version}", version=version, mark=OWN_HYPOTHESIS)
    if rc:
        return rc
    return _print_instructions(params, source_id, f"自分の仮説「{h['name']}」", h["how_it_moves"], out, version, template, mark=OWN_HYPOTHESIS)


def picture(source_id):
    source = json.loads((ROOT / "data/sources" / f"{source_id}.json").read_text(encoding="utf-8"))
    return f"{source['toy']} の図（出典 ID {source_id}・{source['holding']}）: {source['image_url']}"


def _preview(role, call):
    """本物を呼ばずに、送るはずの中身を書き出す（--dry-run）。

    なぜ: 本物の試験は本人の承認が要る。承認の前に、何をどの指示で送り、1 回でいくらまで使いうるかを見せるため。
    返り値は (書き出したパス, failures)。呼ぶ前に止まる時は failures だけを返す。
    """
    from api import agent, budget, config

    from .loop import _write, folder

    try:
        _, failures = call(agent.PreviewClient())
        return None, failures
    except agent.Preview as p:
        request = agent.elide_images(p.request)
    path = folder() / f"preview-{role}.json"
    _write(path, request)
    turns = config.MAX_TOOL_CALLS + config.MAX_RETRIES + 3
    print(f"下見を書きました: {path}")
    print(f"モデル {request['model']}・思考の深さ {request['output_config']['effort']}・道具 {len(request['tools'])} 個・呼ぶ回数の上限 {turns} 回")
    print(f"1 回の生成の費用の上限 ${budget.PER_RUN_CAP:.0f}（超える前に止める）。今日の上限 ${budget.daily_cap()}")
    print("本物は呼んでいません")
    return path, []


def _words_command(args):
    from .contrib import _human_confirm
    from .loop import _read, folder

    if args.cmd == "show-words":
        print(json.dumps(_read(folder() / f"words-{args.id[2:]}.json"), ensure_ascii=False, indent=2))
        return 0
    from api.words import adopt_words, draft_words

    if args.cmd == "adopt-words":
        if not _human_confirm(args.id, "採用"):
            print(Failure("F9.human", args.id, "端末での人の確認が無い").line(), file=sys.stderr)
            return 3
        rec, failures = adopt_words(args.id, args.by)
        if not failures:
            print(f"{rec['id']} を残しました。" + ("print-own で型紙にできます" if rec["params"] else "今の雛形には乗らないので、記録として残りました"))
    else:
        source = json.loads((ROOT / "data/sources" / f"{args.source}.json").read_text(encoding="utf-8"))
        if args.dry_run:
            _, failures = _preview("words", lambda client: draft_words(source, args.text, args.name, args.evidence, args.by, client=client))
            for f in failures:
                print(f.line(), file=sys.stderr)
            return 3 if failures else 0
        try:
            wid, failures = draft_words(source, args.text, args.name, args.evidence, args.by)
        except Exception as e:  # 鍵が無い・通信できない・予算の上限。値は出さない
            print(f"検査できない: Claude を呼べなかった（{type(e).__name__}: {str(e)[:160]}）。own --params で寸法を書けば同じ道で作れます", file=sys.stderr)
            return 4
        if not failures:
            print(f"{wid} を作りました。show-words で補った寸法を見て、adopt-words で採ります")
    for f in failures:
        print(f.line(), file=sys.stderr)
    return 3 if failures else 0


def _generated_command(args):
    from .contrib import _human_confirm
    from .loop import _read, folder

    if args.cmd == "import-draft":
        from api.generate import import_draft

        source = json.loads((ROOT / "data/sources" / f"{args.source}.json").read_text(encoding="utf-8"))
        gid, failures = import_draft(source, json.loads(pathlib.Path(args.file).read_text(encoding="utf-8")), args.by)
        if not failures:
            print(f"{gid} を受け付けました。show-generated で見て adopt-generated で採ります")
        for f in failures:
            print(f.line(), file=sys.stderr)
        return 3 if failures else 0
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
        if args.dry_run:
            # 下見では図を NDL から取りに行かない。手元に取ってあればその大きさを、無ければ空で示す。
            cached = ROOT / "out/sources" / f"{args.source}.jpg"
            image = base64.b64encode(cached.read_bytes()).decode() if cached.exists() else ""
            _, failures = _preview("generate", lambda client: generate(source, client=client, image=image, zoom=not args.no_zoom))
            for f in failures:
                print(f.line(), file=sys.stderr)
            return 3 if failures else 0
        try:
            gid, failures = generate(source, zoom=not args.no_zoom)
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
    sub.add_parser("picture")
    sub.add_parser("list")
    pt = sub.add_parser("print-teacher", help="先生の見る紙を刷る。4 つの着目ごとに見た事を書く。点は付けない")
    pt.add_argument("--out")
    sg0 = sub.add_parser("generate", help="裏の制作の道具。Claude が仮説と寸法の案を作る")
    sg0.add_argument("--dry-run", action="store_true", help="本物を呼ばず、送る中身を書き出す")
    sg0.add_argument("--no-zoom", action="store_true", help="拡大の道具を渡さない（U-12 の比べのためだけ）")
    im = sub.add_parser("import-draft", help="Claude Code の Skill で作った案を、人が採る前の受付に入れる")
    im.add_argument("file")
    im.add_argument("--by", required=True, help="案を作ったセッション")
    sg = sub.add_parser("show-generated")
    sg.add_argument("id")
    ag = sub.add_parser("adopt-generated", help="案を人が採る")
    ag.add_argument("id")
    ag.add_argument("--by", required=True)
    ag.add_argument("--accept", required=True, help="採る案の番号。1,2 のように")
    w = sub.add_parser("words", help="大人が打った言葉の仮説を、Claude が雛形の寸法に写す。正しさは評価しない")
    w.add_argument("text")
    w.add_argument("--name", required=True)
    w.add_argument("--evidence", required=True, help="図のどこを見たか")
    w.add_argument("--by", required=True, help="打った大人")
    w.add_argument("--dry-run", action="store_true", help="本物を呼ばず、送る中身を書き出す")
    sub.add_parser("show-words").add_argument("id")
    aw = sub.add_parser("adopt-words", help="写した寸法を人が見て採る")
    aw.add_argument("id")
    aw.add_argument("--by", required=True)
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
        if args.cmd in ("generate", "show-generated", "adopt-generated", "import-draft"):
            return _generated_command(args)
        if args.cmd in ("words", "show-words", "adopt-words"):
            return _words_command(args)
        if args.cmd == "picture":
            print(picture(args.source))
            return 0
        if args.cmd == "print-teacher":
            return print_teacher(args.source, args.out or f"out/templates/teacher_{args.source}")
        if args.cmd == "print-own":
            return print_own(args.source, args.id, args.out or f"out/templates/{args.id}_v1")
        if args.cmd == "own":
            rec, failures = save_own(args.source, args.name, args.how, args.evidence, json.loads(args.params) if args.params else None)
            if not failures:
                print(f"{rec['id']} を残しました。print-own で型紙にして試せます。用意された仮説と比べたくなったら list です")
                return 0
            for f in failures:
                print(f.line(), file=sys.stderr)
            return 3
        if args.cmd == "list":
            # 順位も他の人の集計も見せない。次の人にとって記録から作られた答えになるため（J-013）。
            # 作り手が版を直す時は records summary と loop で見る。
            print("\n".join(list_lines(load(args.source), own_hypotheses(args.source))))
            return 0
        return print_sheet(args.source, args.hypothesis, args.out or f"out/templates/{args.hypothesis}_v{args.version}", args.version)
    except (ToolMissing, OSError, ValueError, KeyError) as e:
        print(f"検査できない: {e}", file=sys.stderr)
        return 4


if __name__ == "__main__":
    sys.exit(main())
