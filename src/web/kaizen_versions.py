"""新しく作られた版の型紙の歩み（作る側の頁 /loop と /loop/<印> の節）。

本人の希望（2026-11-06）: 「新しく作られた版の型紙について、その前の履歴・どこが良くなったか・どういう知見で良くなったか・共通化している知見が、
裏側の改善ループの頁で見れるといい」「その改善が、どこの改善ループで走った物か（ループ1〜4のどれか）も見れるといい」。

判断の芯:
- 別の台帳を作らない（J-026）。読むのは今ある記録だけ: 型紙の版の表（docs/process/trials/sheets/README.md。人が書いた履歴）・雛形の直し（T-番号）・
  寸法の版（version-*）・記録と人の説明と話した工夫・エンジンの版の台帳（別の repo の data/engine。無ければその旨を出す）。
- 良くなったかは機械が決めない（本人の決まり 11-05）。見出しは本人の言葉のままで、中身は人が書いた「変えた事」。数は /loop/<印> の「2 動きの結果」で人が読む。
- 知見は人が書いた物だけを写す（人の説明・次の思いつき・変更の理由・人が確かめた読み・話した工夫・採る人の 1 行・表の記録の題）。機械が要約した文を作らない。
- どのループで走ったかは、判定でなく通った道で決める（本人の 4 つのループ、11-05 17:57）:
  - ループ 3: エンジンの版と雛形の直し（型紙を作る側を直した物）。材料の記録が通ったループも並べる。
  - 寸法の版は根拠の記録で決める。話した考えから作った紙（OWN-n）の記録はループ 1 も付く。作りながらの話がある記録と、話の無い記録はループ 2。
    上げた後に残した話や、上げる口から来た記録はループ 4。
  - 作る前のレビューは作っていないので、4 つのどれにも数えず、材料の名で出す。
  - 記録に結ばれていない直し（試す前の設計・本人の決定だけの直し）は「ループの外」と出す。ループに入れて見せない。
- 作る側の頁の中だけ（/loop は合言葉なしの場に出ない。J-028）。採った人の名前とカードの番号は出さない。成績に見える数は出さない（J-025）。
"""
import json
import os
import pathlib
import re
import subprocess

from api import words
from omochae import hypotheses, loop, records, store, talk_log
from omochae.compose import TEMPLATES
from omochae.hypotheses import ROOT

from . import kaizen
from .play_server import esc, sources

# 本人の 4 つのループの短い呼び名（omochae.cycle の頭と同じ）。
LOOPS = {1: "考えを話す → 紙が生まれる", 2: "作りながらの工夫 → 型紙の直し", 3: "エンジンごとの改善", 4: "上げて残す → ギャラリーと輪"}
TABLE = ROOT / "docs/process/trials/sheets/README.md"
SET_NAME = re.compile(r"([a-z_-]+?)-v\d+")
COMMITS = re.compile(r"[0-9a-f]{7,40}(・[0-9a-f]{7,40})*")
LINK = re.compile(r"\[([^\]]+)\]\(([^)#]+)[^)]*\)")
WORK_NOTE = re.compile(r"（[^（）]*(?:カード|hack-|sub-|lane/)[^（）]*）")  # 作業の番号と線の名は頁に出さない
# 案の数のうち、頁に出す物。動きの札の数（moved・not_moved）は出さない（J-025）。
NUMBER_JA = {"stuck_people": "止まった人", "stuck_taps": "止まったの札", "quit_people": "その段でやめた人", "craft_talks": "話した工夫", "craft_people": "工夫を話した人",
             "fixes": "直した点", "ideas": "思いつき", "keeps": "できた後の話", "reviews": "レビューの指摘", "templates": "雛形", "texts": "文"}
MAKING_NUMBERS = ("stuck_people", "stuck_taps", "quit_people", "craft_talks", "craft_people", "fixes", "ideas", "not_moved")
STYLE = (".ver{border-top:1px solid var(--rule);padding:14px 0}.ver h3{margin:0 0 6px}.ver h4{margin:14px 0 4px}.ver details{margin:6px 0}"
         ".ver ol,.ver ul{margin:4px 0;padding-left:20px}.ver ol>li{margin:0 0 10px}"
         ".lp{display:inline-block;font-size:12px;font-weight:normal;padding:1px 8px;border:1px solid var(--rule);border-radius:10px;color:var(--mute)}")


def _prefix(name):
    m = SET_NAME.match(name or "")
    return m.group(1) if m else ""


def _plain(text):
    """表の字を頁の字にする。リンクは字だけにし、作業の番号と線の名を外す。"""
    return WORK_NOTE.sub("", LINK.sub(r"\1", text)).replace("`", "").strip()


def _title_of(target):
    """表の「記録」の先の文書の題。人が書いた題で、どういう知見かの見出しになる。読めなければ空。"""
    try:
        return (TABLE.parent / target).read_text(encoding="utf-8").split("\n", 1)[0].lstrip("# ").strip()
    except OSError:
        return ""


def _ref(label, target):
    """表の「記録」の 1 つ。題の頭の番号が呼び名と重なる時は外す（J-020: J-020 今夜の… と並べない）。"""
    title = re.sub(rf"^{re.escape(label.rsplit('/', 1)[-1])}\s*", "", _title_of(target))
    return f"記録 {label}: {title}" if title else f"記録 {label}"


def table_rows():
    """型紙の版の表の行。読めない時は空（頁を止めない）。組み合わせの行（goraigo-v10・tora-v3）は names に両方が入る。"""
    try:
        lines = TABLE.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    rows = []
    for line in lines:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not line.startswith("| ") or len(cells) != 5 or not SET_NAME.match(cells[0]):
            continue
        parts = cells[0].split("・")
        refs = [_ref(label, target) for label, target in LINK.findall(cells[4])] or [f"記録 {_plain(cells[4])}"]
        rows.append({"names": parts if all(SET_NAME.fullmatch(p) for p in parts) else [cells[0]], "commit": cells[1] if COMMITS.fullmatch(cells[1]) else "",
                     "changed": _plain(cells[2]), "found": _plain(cells[3]), "refs": refs})
    return rows


def _engine_json(name, kind=dict):
    """エンジンの repo の data/engine の中の JSON。無い・読めない時は None。場所は omochae.cycle と同じ決め方（環境の値が先で、無ければ隣の repo）。
    隣の repo は作業の途中の枝のことがあるので、main の中身を git から読む（読めなければ、木の中のファイル）。"""
    place = os.environ.get("OMOCHAE_ENGINE_REPO")
    if place:
        return store.read_json_or_skip(pathlib.Path(place) / "data/engine" / name, kind)
    repo = ROOT.parent / "paper-to-toy"
    try:
        shown = subprocess.run(["git", "-C", str(repo), "show", f"refs/remotes/origin/main:data/engine/{name}"], capture_output=True, timeout=5)
        obj = json.loads(shown.stdout) if shown.returncode == 0 else None
        if isinstance(obj, kind):
            return obj
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    return store.read_json_or_skip(repo / "data/engine" / name, kind)


def _context():
    """1 回の表示で 1 度だけ読む物。玩具ごとに読むと、一覧で同じファイルを 83 回読む。"""
    return {"rows": table_rows(), "changes": loop.template_changes(), "ledger": _engine_json("versions.json"), "seeds": _engine_json("shared-findings.json", list)}


def record_loops(rid):
    """記録が通ったループ。Returns (番号の list, 作る前のレビューか)。読めない記録は何も付けない。"""
    try:
        rec = loop.record(rid)
    except ValueError:
        return [], False
    if rec.get("video_kind") == "review":
        return [], True
    said = [t["when"] for t in talk_log.kufu(rec.get("source_id"), rid)]
    made = rec.get("via") == records.UPLOADED or talk_log.WHEN["keep"] in said
    out = {1} if rec.get("hypothesis_id") in words.spoken_own_ids(rec.get("source_id")) else set()
    if talk_log.WHEN["craft"] in said or not made:
        out.add(2)
    if made:
        out.add(4)
    return sorted(out), False


def _loops_of(record_ids):
    hits = [record_loops(rid) for rid in record_ids]
    return sorted({n for loops, _ in hits for n in loops}), any(review for _, review in hits)


def _reading(rid):
    """人が確かめた読み。人が書いた字か、Claude の案を人が確かめた物。案のままの読みは出さない。"""
    if not loop.confirmed(rid):
        return []
    c = loop.interpretation(rid).get("content")
    if isinstance(c, dict):
        return [str(x) for x in c.get("observed", [])] + [str(x.get("text", "")) for x in c.get("causes", []) if isinstance(x, dict)]
    return [str(c)] if c else []


def record_words(rid):
    """記録から、人が書いた・話した字を並べる。隠した字は出さない（loop.maker_talk）。"""
    try:
        m = loop.material(rid)
    except ValueError:
        return []
    told = m["explanation"] or {}
    out = [f"人の説明（{rid}）: {told['text']}"] if told.get("text") else []
    out += [f"次の思いつき（{rid}）: {told['next_idea']}"] if told.get("next_idea") else []
    out += [f"読み（{rid}）: {x}" for x in _reading(rid)]
    for t in m["maker_talk"]["items"]:
        where = f"手順 {t['step']} で話した工夫" if t["step"] else ("上げた後の話" if t["when"] == talk_log.WHEN["keep"] else "作りながら話した工夫")
        out.append(f"{where}（{rid}）: {t['text']}")
    return out


def _words_of(record_ids):
    return [x for rid in record_ids for x in record_words(rid)]


def _set_entry(name, row, changes):
    """組（雛形の版）の 1 行。雛形の直しの記録があれば、その中身と根拠を使う。無ければ、表の字だけで、ループの外。"""
    record_ids = [rid for t in changes for rid in t.get("record_ids", [])]
    material, review = _loops_of(record_ids)
    row = row or {"commit": "", "changed": "", "found": "", "refs": []}
    return {"id": f"set:{name}", "name": name, "at": changes[-1].get("at", "") if changes else "", "loops": [3] if changes else [], "material": material, "review": review,
            "changed": [c for t in changes for c in t.get("changes", [])] or ([row["changed"]] if row["changed"] else []), "found": row["found"],
            "learned": _words_of(record_ids) + row["refs"], "commit": next((t["commit"] for t in changes if t.get("commit")), row["commit"]), "link": ""}


def _set_entries(template, ctx):
    """Returns (表の順の行, 表に無い組の雛形の直し)。表の行に日付は無いので、表の順のまま先に置く。"""
    prefix = _prefix(TEMPLATES[template].SHEET_SET)
    changes = {}
    for t in ctx["changes"]:
        changes.setdefault(t.get("sheet_set", ""), []).append(t)
    rows = []
    for row in ctx["rows"]:
        for name in row["names"]:
            if _prefix(name) != prefix:
                continue
            if SET_NAME.fullmatch(name):
                rows.append(_set_entry(name, row, changes.pop(name, [])))
            elif rows:  # 版の名前を変えない例外の行（goraigo-v10 の H-E）。新しい版ではないので、その版の中身に足す
                rows[-1]["changed"].append(f"{name}: {row['changed']}")
                rows[-1]["found"] = "／".join(x for x in (rows[-1]["found"], f"{name}: {row['found']}" if row["found"] else "") if x)
    return rows, [_set_entry(name, None, ts) for name, ts in changes.items() if _prefix(name) == prefix]


def _version_entries(sid, data):
    """寸法の版（版 2 から）。必ず根拠の記録があるので、読めない時はループ 2 と見る。"""
    out = []
    for h in data["hypotheses"]:
        for v in kaizen.versions(sid, h["id"]):
            changes, record_ids = v.get("changes", []), v.get("record_ids", [])
            loops, review = _loops_of(record_ids)
            arrow = lambda c: f'{kaizen._param_name(sid, c["param"])} {c["from"]}→{c["to"]}' if c.get("from") not in (None, "") else f'{kaizen._param_name(sid, c["param"])} → {c["to"]}'
            out.append({"id": f"ver:{sid}:{h['id']}:{v['version']}", "name": f"仮説 {hypotheses.letter(h)} 版 {v['version']}", "at": v.get("adopted_at", ""),
                        "loops": loops or ([] if review else [2]), "material": [], "review": review, "changed": [arrow(c) for c in changes], "found": "",
                        "learned": [f"変更の理由: {c['why']}" for c in changes if c.get("why")] + _words_of(record_ids), "commit": "",
                        "link": f"/toy/{sid}?see={h['id']}&kind=sheet&v={v['version']}#win"})
    return out


def _source_is(source, tid, sid):
    """エンジンの出典（NDL-…-L-spinner）が、この玩具か。エンジンは雛形の id を後ろに足し、サイトは同じ頁の玩具に -2 のように足す。"""
    base = source.removesuffix(f"-{tid}")
    return sid == base or sid.startswith(f"{base}-")


def _hit(v, sid, template):
    """エンジンの版が、この玩具に当たるか。Returns (当たるか, 組の名)。版の鍵は 雛形の id か 雛形の id.形。出典が台帳にあれば出典で、無ければ雛形で見る。"""
    sets, found = v.get("sheet_sets") or {}, v.get("sources") or {}
    for key, name in sets.items():
        tid = key.partition(".")[0]
        if any(_source_is(s, tid, sid) for s in found[key]) if found.get(key) else tid == template:
            return True, name
    return not sets and any(p.get("target", {}).get("kind") == "template" and p["target"].get("name") == template for p in v.get("proposals", [])), ""


def _number_loops(numbers):
    return sorted(({2} if any(numbers.get(k) for k in MAKING_NUMBERS) else set()) | ({4} if numbers.get("keeps") else set()))


def _proposal_words(p):
    nums = "・".join(f"{NUMBER_JA[k]} {v}" for k, v in p.get("numbers", {}).items() if k in NUMBER_JA)
    return ([f"{p['finding']}（案 {p['id']}）"] if p.get("finding") else []) + [f"案 {p['id']}「{p['title']}」" + (f"（{nums}）" if nums else "")]


def _engine_entries(sid, template, ctx):
    out = []
    for v in (ctx["ledger"] or {}).get("versions", []):
        hit, name = _hit(v, sid, template)
        if hit:
            ps = v.get("proposals", [])
            out.append({"id": f"eng:{v['version']}", "name": f"エンジンの版 {v['version']}" + (f"（{name}）" if name else ""), "at": v.get("at", ""), "loops": [3],
                        "material": sorted({n for p in ps for n in _number_loops(p.get("numbers", {}))}), "review": any(p.get("numbers", {}).get("reviews") for p in ps),
                        "changed": [v["note"]] if v.get("note") else [], "found": "", "learned": [x for p in ps for x in _proposal_words(p)], "commit": str(v.get("commit", ""))[:7], "link": ""})
    return out


def entries(sid, ctx=None, data=None):
    """その玩具の版の歩み（古い順）。表の行が先で、日付のある版がその後に日の順で続く。一番後ろが、新しく作られた版。"""
    ctx = ctx or _context()
    data = data or hypotheses.load(sid)
    template = data.get("template", "slider_fan")
    rows, dated = _set_entries(template, ctx)
    return rows + sorted(dated + _version_entries(sid, data) + _engine_entries(sid, template, ctx), key=lambda e: e["at"])


def shared_findings(ctx):
    """共通化している知見。エンジンの repo に人が書いた一覧（shared-findings.json）と、版に入った部品と生成の決まりの案。形の外の行は読まない。"""
    out = []
    for k in ctx["seeds"] or []:
        if isinstance(k, dict) and isinstance(k.get("finding"), str) and k["finding"].strip():
            out.append({"finding": k["finding"], "where": str(k.get("where", "")), "reach": k.get("reach", "all"), "loops": k.get("loops", []), "material": k.get("material", []),
                        "review": False, "from": str(k.get("from", "")), "commit": str(k.get("commit", ""))[:7]})
    for v in (ctx["ledger"] or {}).get("versions", []):
        for p in v.get("proposals", []):
            kind, name = p.get("target", {}).get("kind"), p.get("target", {}).get("name", "")
            if kind in ("part", "rule"):
                out.append({"finding": p.get("finding") or p["title"], "where": name, "reach": "all" if kind == "part" else [name.split(" ")[0]], "loops": [3],
                            "material": _number_loops(p.get("numbers", {})), "review": bool(p.get("numbers", {}).get("reviews")),
                            "from": f"エンジンの版 {v['version']}・案 {p['id']}", "commit": str(v.get("commit", ""))[:7]})
    return out


def tag(e):
    """どのループで走ったかの字。"""
    joined = lambda ns: "・".join(str(n) for n in ns)
    notes = ([f"材料はループ {joined(e['material'])}"] if e.get("material") else []) + (["材料は作る前のレビュー"] if e.get("review") else [])
    return (f"ループ {joined(e['loops'])}" if e.get("loops") else "ループの外") + (f"（{'・'.join(notes)}）" if notes else "")


def _tag_html(e):
    return f'<span class="lp">{esc(tag(e))}</span>'


def _items(lines, empty):
    return "<ul>" + "".join(f"<li>{esc(x)}</li>" for x in lines) + "</ul>" if lines else f'<p class="meta">{empty}</p>'


def _finding_html(k):
    reach = "全部の雛形" if k["reach"] == "all" else "雛形 " + "・".join(str(x) for x in k["reach"]) if isinstance(k["reach"], list) else ""
    where = "・".join(x for x in (k["where"], reach, k["from"], f"commit {k['commit']}" if k["commit"] else "") if x)
    return f'<li>{esc(k["finding"])} {_tag_html(k)}' + (f'<br><span class="meta">{esc(where)}</span>' if where else "") + "</li>"


def _reaches(k, template):
    return k["reach"] == "all" or (isinstance(k["reach"], list) and template in k["reach"])


def _when(e):
    bits = ([e["at"][:10]] if e["at"] else []) + ([f"commit {e['commit']}"] if e["commit"] else [])
    return f'<p class="meta">{esc("・".join(bits))}</p>' if bits else ""


def _sheet_link(e):
    return f'<p class="meta"><a href="{esc(e["link"])}">この版の型紙</a></p>' if e["link"] else ""


def _history(older):
    """その前の履歴（新しい順）。変えた事と、人が書いた「分かった事」と知見を、そのまま並べる。"""
    if not older:
        return '<h4>その前の履歴</h4><p class="meta">この前の版の記録はありません。</p>'
    rows = "".join(f'<li><b>{esc(e["name"])}</b> {_tag_html(e)}{_when(e)}{_items(e["changed"], "変えた事の字はありません。")}'
                   + (f'<p class="meta">分かった事: {esc(e["found"])}</p>' if e["found"] else "") + (_items(e["learned"], "") if e["learned"] else "") + _sheet_link(e) + "</li>"
                   for e in reversed(older))
    return f'<details><summary>その前の履歴（{len(older)} 版）</summary><ol>{rows}</ol></details>'


def _card(sid, title, ents, findings):
    latest = ents[-1]
    return (f'<article class="ver" id="ver-{esc(sid)}"><h3>{title}: {esc(latest["name"])} {_tag_html(latest)}</h3>{_when(latest)}{_sheet_link(latest)}'
            f'{_history(ents[:-1])}'
            f'<h4>どこが良くなったか</h4><p class="meta">変えた所です。良くなったかは機械が決めず、次の記録で人が読みます（<a href="/loop/{esc(sid)}#k2">版ごとの動きの札</a>）。</p>'
            f'{_items(latest["changed"], "変えた事の字はありません。")}'
            + (f'<p class="meta">分かった事: {esc(latest["found"])}</p>' if latest["found"] else "")
            + f'<h4>どういう知見で良くなったか</h4>{_items(latest["learned"], "人が書いた知見はまだありません。")}'
            f'<h4>共通化している知見</h4>'
            + (f'<ul>{"".join(_finding_html(k) for k in findings)}</ul>' if findings else '<p class="meta">この玩具に届く、共通化した知見の記録はまだありません。</p>')
            + "</article>")


def _legend(ctx):
    missing = '<p class="meta">エンジンの台帳が手元にありません。エンジンの版と、そこで共通化した知見は出ません。</p>' if ctx["ledger"] is None else ""
    return ('<p class="meta">どのループで走ったか: ' + " ／ ".join(f"ループ {n}: {esc(text)}" for n, text in LOOPS.items())
            + " ／ ループの外: 記録に結ばれていない直し（試す前の設計や、決定だけの直し）</p>" + missing)


def section():
    """/loop の節。版の歩みのある玩具ごとに、新しく作られた版の札を出す。同じ歩みの玩具（同じ雛形）は 1 枚にまとめ、続けて共通化している知見の全部を出す。"""
    ctx = _context()
    findings = shared_findings(ctx)
    cards = {}
    for sid in sources():
        data = hypotheses.load(sid)
        ents = entries(sid, ctx, data)
        if ents:
            cards.setdefault(tuple(e["id"] for e in ents), []).append((sid, data, ents))
    html = ""
    for group in cards.values():
        sid, data, ents = group[0]
        title = f'<a href="/loop/{esc(sid)}">{esc(data["toy"])}</a>' + (f" ほか {len(group) - 1} 種" if len(group) > 1 else "")
        html += _card(sid, title, ents, [k for k in findings if _reaches(k, data.get("template", "slider_fan"))])
    return (f'<section class="sec" id="versions"><h2>新しく作られた版の型紙</h2>{_legend(ctx)}'
            + (html or '<p class="meta">版の記録はまだありません。</p>') + '</section>'
            '<section class="sec" id="shared"><h2>共通化している知見（全部）</h2>'
            + (f'<div class="ver"><ul>{"".join(_finding_html(k) for k in findings)}</ul></div>' if findings else '<p class="meta">共通化した知見の記録はまだありません。</p>')
            + '</section>')


def toy_section(sid, data):
    """/loop/<印> の節。その玩具の札。"""
    ctx = _context()
    ents = entries(sid, ctx, data)
    findings = [k for k in shared_findings(ctx) if _reaches(k, data.get("template", "slider_fan"))]
    return (f'<section class="sec" id="versions"><h2>新しく作られた版の型紙</h2>{_legend(ctx)}'
            + (_card(sid, esc(data["toy"]), ents, findings) if ents else '<p class="meta">版の記録はまだありません。</p>') + '</section>')
