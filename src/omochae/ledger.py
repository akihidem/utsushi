"""台帳の検査と描画。AI の読み手が機械で引く物を、正しい状態に保つ。

判断の芯（J-015）: 主張と索引の正本は JSON に置き、Markdown は JSON から描く。手で二重に持つと食い違うため。
根拠は「パスが在る」だけでは足りないので、根拠の文そのものが在る事まで見る。ファイルだけ残って中身が変わった時に気づくため。
"""
import argparse
import json
import pathlib
import re
import sys

from .model import Failure

ROOT = pathlib.Path(__file__).resolve().parents[2]
PROCESS = pathlib.Path("docs/process")
FEATURE_STATUS = {"todo", "doing", "done", "blocked", "dropped"}
# 主張の確かさの種類。「未確認」と「立場」を別に持つ。測っていない物を測った物と同じ列に並べないため。
CLAIM_KINDS = {"計算": "式で出した。実物では未確認", "測定": "ファイルや記録を測った", "自動試験": "試験が通る", "偽の応答の試験": "Claude の応答は偽物", "文献": "批評役が読んだ範囲で、書き手は読み直していない", "未確認": "まだ試していない", "立場": "作品の立場で、確かめる物ではない"}
SUMMARY = re.compile(r"<!-- summary:start -->.*?<!-- summary:end -->", re.S)
MAP = re.compile(r"<!-- map:start -->.*?<!-- map:end -->", re.S)
LINK = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")
COUNTS = re.compile(r"<!-- counts:start -->.*?<!-- counts:end -->", re.S)
# 試験の総数は並列の線が足すたびに変わるので、最初に読まれる文書には書かず `./run.sh` の最後の行を指す。書くと次の 1 本で古くなり、数をそろえる 1 行で枝どうしがぶつかる（#165 の表が数でなく名前で持つのと同じ理由）。
RUN_TOTAL = re.compile(r"場面(?:と試験)?\s*\d+\s*本|\d+\s*本が期待どおり")
ENTRY_DOCS = ("README.md", "CLAUDE.md", "docs/architecture.md", "docs/claude-usage.md", "docs/process/spec.md")


def _json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def render_map(index):
    rows = ["<!-- map:start -->", "| 順 | 記録 | 一言 | 状態 |", "|---|---|---|---|"]
    for i, e in enumerate(index, 1):
        rows.append(f"| {i} | [{e['id']}]({e['path']}) | {e['hook']} | {e['status']} |")
    return "\n".join(rows + ["<!-- map:end -->"])


def render_claims(claims):
    lines = ["# 主張と根拠", "", "`claims.json` から `python -m omochae.ledger render` で描いた表。手で直さない。根拠の文が今もファイルに在る事は `./run.sh` が確かめる。", "", "## 確かさの種類", "", "| 種類 | 意味 |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in CLAIM_KINDS.items()]
    lines += ["", "## 主張", "", "| ID | 主張 | 確かさ | 根拠 |", "|---|---|---|---|"]
    for c in claims:
        links = "、".join(f"[{pathlib.Path(e['path']).name}]({_rel(e['path'])})" for e in c["evidence"])
        lines.append(f"| {c['id']} | {c['claim']} | {c['kind']} | {links} |")
    return "\n".join(lines) + "\n"


def render_counts():
    """玩具・雛形・凍結の場面の数を tree から数える。手で書くと、増やした時に文だけ古く残るため。"""
    toys = len(list((ROOT / "data/hypotheses").glob("*.json")))
    templates = [p for p in (ROOT / "src/omochae/templates").glob("*.py") if not p.name.startswith("_")]
    scenarios = list((ROOT / "tests/frozen/scenarios").glob("*.json"))
    negative = [p for p in scenarios if p.name.startswith("neg_")]
    return "\n".join([
        "<!-- counts:start -->",
        f"- 玩具: {toys} 件（`data/hypotheses` のファイルの数。必須の 2 種を含む）",
        f"- 雛形: {len(templates)} 本（`src/omochae/templates`。必須の 2 本を含む）",
        f"- 凍結の場面: {len(scenarios)} 本（`tests/frozen/scenarios`。うち {len(negative)} 本は落ちるべき紙を入れる負の場面）",
        "<!-- counts:end -->",
    ])


def _unlisted_modules():
    """`src/` のモジュールで、architecture.md にも features.json にも名前が出ない物を返す。雛形は置くだけで読まれるので、architecture.md の文に名前が出れば足りる。"""
    arch = (ROOT / "docs/architecture.md").read_text(encoding="utf-8")
    known = arch + (ROOT / "docs/features.json").read_text(encoding="utf-8")
    missing = []
    for p in sorted((ROOT / "src").rglob("*.py")):
        rel = p.relative_to(ROOT).as_posix()
        if p.name == "__init__.py" or rel in known or f"`{p.name}`" in known:
            continue
        if p.parent.name == "templates" and f"`{p.stem}`" in arch:
            continue
        missing.append(rel)
    return missing


def _rel(path):
    return pathlib.PurePosixPath(*[".."] * len(PROCESS.parts), path).as_posix() if not path.startswith(str(PROCESS) + "/") else path[len(str(PROCESS)) + 1:]


def check():
    out = []
    seen = set()
    for f in _json("docs/features.json"):
        where = f.get("id", "?")
        if where in seen:
            out.append(Failure("L.features", where, "id が重なっている"))
        seen.add(where)
        if f.get("status") not in FEATURE_STATUS:
            out.append(Failure("L.features", where, f"状態 {f.get('status')} は使えない"))
        if f.get("status") in ("doing", "done") and not f.get("evidence"):
            out.append(Failure("L.features", where, "進行中か完了の機能には根拠のパスが要る"))
        out += [Failure("L.features", where, f"根拠が無い: {p}") for p in f.get("evidence", []) if not (ROOT / p).exists()]
    index = _json(PROCESS / "index.json")
    listed = {e["path"] for e in index}
    for sub in ("research", "decisions"):
        for p in sorted((ROOT / PROCESS / sub).glob("*.md")):
            rel = f"{sub}/{p.name}"
            if rel not in listed:
                out.append(Failure("L.index", rel, "索引に載っていない"))
    for e in index:
        if not (ROOT / PROCESS / e["path"]).exists():
            out.append(Failure("L.index", e["path"], "索引の先が無い"))
        if not e.get("hook", "").strip() or len(e["hook"]) > 60:
            out.append(Failure("L.index", e["path"], "一言は 1〜60 字"))
    readme = (ROOT / PROCESS / "README.md").read_text(encoding="utf-8")
    found = MAP.search(readme)
    if not found or found.group(0) != render_map(index):
        out.append(Failure("L.index", "docs/process/README.md", "地図が index.json と違う。render を回す"))
    claims = _json(PROCESS / "claims.json")
    for c in claims:
        if c.get("kind") not in CLAIM_KINDS:
            out.append(Failure("L.claims", c["id"], f"確かさの種類 {c.get('kind')} は使えない"))
        if not c.get("evidence"):
            out.append(Failure("L.claims", c["id"], "根拠が無い"))
        for e in c.get("evidence", []):
            path = ROOT / e["path"]
            if not path.exists():
                out.append(Failure("L.claims", c["id"], f"根拠のファイルが無い: {e['path']}"))
            elif e["quote"] not in path.read_text(encoding="utf-8"):
                out.append(Failure("L.claims", c["id"], f"根拠の文が {e['path']} に無い: {e['quote']}"))
    for o in _json(PROCESS / "open.json"):
        e = o["evidence"]
        path = ROOT / e["path"]
        if not path.exists() or e["quote"] not in path.read_text(encoding="utf-8"):
            out.append(Failure("L.open", o["id"], f"判断待ちの根拠の文が無い: {e['path']}"))
    if (ROOT / PROCESS / "claims.md").read_text(encoding="utf-8") != render_claims(claims):
        out.append(Failure("L.claims", "docs/process/claims.md", "表が claims.json と違う。render を回す"))
    # 要約は 2 か所に置くので、片方だけ古くならないように同じ文かを見る。
    blocks = [SUMMARY.search((ROOT / f).read_text(encoding="utf-8")) for f in ("README.md", "CLAUDE.md")]
    if not all(blocks) or blocks[0].group(0) != blocks[1].group(0):
        out.append(Failure("L.summary", "README.md・CLAUDE.md", "30 秒の要約が無いか、2 か所で違う"))
    for f in sorted((ROOT / PROCESS).rglob("*.md")):
        for target in LINK.findall(f.read_text(encoding="utf-8")):
            if not target.startswith("http") and not (f.parent / target).exists():
                out.append(Failure("L.links", str(f.relative_to(ROOT)), f"リンク先が無い: {target}"))
    found = COUNTS.search((ROOT / "README.md").read_text(encoding="utf-8"))
    if not found or found.group(0) != render_counts():
        out.append(Failure("L.counts", "README.md", "玩具・雛形・凍結の場面の数が tree と違う。render を回す"))
    for f in ENTRY_DOCS:
        for hit in RUN_TOTAL.findall(COUNTS.sub("", (ROOT / f).read_text(encoding="utf-8"))):
            out.append(Failure("L.counts", f, f"試験の総数は書かず `./run.sh` の最後の行を指す: {hit}"))
    out += [Failure("L.modules", m, "architecture.md にも features.json にも出ていない") for m in _unlisted_modules()]
    return out


def render():
    index = _json(PROCESS / "index.json")
    p = ROOT / PROCESS / "README.md"
    p.write_text(MAP.sub(lambda _: render_map(index), p.read_text(encoding="utf-8")), encoding="utf-8")
    (ROOT / PROCESS / "claims.md").write_text(render_claims(_json(PROCESS / "claims.json")), encoding="utf-8")
    readme = ROOT / "README.md"
    readme.write_text(COUNTS.sub(lambda _: render_counts(), readme.read_text(encoding="utf-8")), encoding="utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="omochae.ledger")
    ap.add_argument("cmd", choices=("check", "render"))
    try:
        args = ap.parse_args(argv)
    except SystemExit as e:
        return 0 if e.code == 0 else 4
    try:
        if args.cmd == "render":
            render()
        failures = check()
    except (OSError, ValueError, KeyError) as e:
        print(f"検査できない: {type(e).__name__}: {e}", file=sys.stderr)
        return 4
    for f in failures:
        print(f.line(), file=sys.stderr)
    return 3 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
