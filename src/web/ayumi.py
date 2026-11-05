"""型紙の版の歩み（本人の希望 2026-11-06）。裏側の改善ループの頁の 1 つ。

本人の言葉: 新しく作られた版の型紙について「その前の履歴・どこが良くなったか・どういう知見で良くなったか・共通化している知見」が見れるといい。
「その改善が、どこの改善ループで走った物か（ループ1〜4のどれか）も見れるといい」。

判断の芯:
- 別の台帳を作らない。版の表と共通の知見は docs/process/trials/sheets/README.md、寸法の版と組の直しと人の説明は omochae.loop、
  エンジンの版は paper-to-toy の data/engine/versions.json を読むだけ。
- 良くなったかは機械が決めない（本人の決まり）。「どこを良くしたか」は作る側が変えた所で、効いたと言う物ではない。頁の頭に書く。
- 版の表のループの欄は作る側の読み。寸法の版は、根拠の記録に上げた後の字があればループ 4、無ければループ 2 と数える。
- 作る側の頁。学ぶ人の頁から道を置かず、合言葉なしで開いたデモでは出さない（J-028。/loop の下なので play_server が止める）。
- 順位を付けない。型の並びは雛形の表の順で、数の多い順にしない（J-025）。
"""
import json
import os
import pathlib
import re

from omochae import hypotheses, loop, records
from omochae.compose import TEMPLATES

from . import skin
from .kaizen import TABLE_STYLE, _param_name, versions
from .play_server import esc, sources

ROOT = pathlib.Path(__file__).resolve().parents[2]
LEDGER = ROOT / "docs/process/trials/sheets/README.md"
TITLE = "型紙の版の歩み"
LOOPS = (("1", "考えを話す → 紙が生まれる"), ("2", "作りながらの工夫 → 型紙が直る"), ("3", "エンジンごと直す → 同じ型の紙が全部直る"), ("4", "上げて残す → ギャラリーと次の版の材料"))
BEFORE = "ループの前"
KINDS = {"slider_fan": "御来迎の型", "pivot_counterweight": "虎の型", "stand_figure": "立てる型", "stick_prop": "棒に付ける型", "string_pull": "糸や棒で動かす型",
         "spin_toy": "回す型", "den_den": "鳴らす型", "balance_toy": "つり合いの型", "wheel_cart": "車の型"}
STYLE = TABLE_STYLE + """
.ay{border-top:1px solid var(--rule);padding:14px 0}
.ay h3{margin:0 0 6px;font-size:17px}
.ay dl{margin:0;display:grid;grid-template-columns:minmax(6.5em,auto) 1fr;gap:4px 12px}
.ay dt{color:var(--mute);font-size:13px;padding-top:3px}
.ay dd{margin:0;min-width:0;overflow-wrap:anywhere}
.lp{display:inline-block;margin-left:8px;padding:1px 8px;border:1px solid var(--rule);font-size:13px;font-weight:normal}
@media (max-width:520px){.ay dl{grid-template-columns:1fr}.ay dt{padding-top:6px}}
"""


def _plain(cell):
    """表の字を画面の字にする。リンクは字だけ、飾りの記号は外す。"""
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", cell)
    return text.replace("**", "").replace("`", "").strip()


def _table(head):
    """台帳の表を 1 つ読む。head は見出しの行の頭。Returns [{見出し: 字}]。"""
    rows, names = [], None
    for line in LEDGER.read_text(encoding="utf-8").split("\n"):
        if names is None:
            if line.startswith(head):
                names = [c.strip() for c in line.strip().strip("|").split("|")]
            continue
        if not line.startswith("|"):
            break
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if set(cells[0]) <= {"-"}:
            continue
        if len(cells) != len(names):
            raise ValueError(f"表の欄の数が合わない: {cells[0]}")
        rows.append({n: _plain(c) for n, c in zip(names, cells)})
    if names is None:
        raise ValueError(f"表が無い: {head}")
    return rows


def sheet_rows():
    return _table("| 版 |")


def shared_rows():
    return _table("| 知見 |")


def _template(sid):
    return hypotheses.sheet_of(sid).get("template") or hypotheses.load(sid).get("template", "slider_fan")


def _prefix(template):
    return TEMPLATES[template].SHEET_SET.rsplit("-v", 1)[0]


def rows_for(prefix):
    """その組の版の行。新しい版を上に。"""
    mine = [r for r in sheet_rows() if any(n.strip().startswith(prefix + "-v") for n in r["版"].split("・"))]
    return list(reversed(mine))


def _repo_loop(name):
    """repo に入っている輪の記録（11-04 の試行の分）。作業中の置き場（OMOCHAE_DATA）が別でも読む。"""
    try:
        return json.loads((ROOT / "data/loop" / name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def template_changes():
    """組の直しの記録。置き場の分と repo の分を合わせる。"""
    seen = {t["id"]: t for t in loop.template_changes()}
    for path in sorted((ROOT / "data/loop").glob("template-change-*.json")):
        t = _repo_loop(path.name)
        if t:
            seen.setdefault(t["id"], t)
    return list(seen.values())


def told(record_ids):
    """根拠の記録についた人の説明。"""
    out = []
    for rid in record_ids:
        e = loop.explanation(rid) or _repo_loop(f"explanation-{rid}.json")
        if e:
            out.append(f"{rid}: {e['text']}" + (f" 次の思いつき: {e['next_idea']}" if e.get("next_idea") else ""))
    return out


def loop_of(version):
    """寸法の版のループ。根拠の記録に上げた後の字があれば 4 も数える。"""
    made = False
    for rid in version.get("record_ids", []):
        try:
            made = made or any(t["when"] == "made" for t in loop.maker_talk(rid)["items"])
        except (ValueError, KeyError, OSError):
            continue
    return "2・4" if made else "2"


def _tag(name):
    if name == "前":
        return f'<span class="lp">{BEFORE}</span>'
    if name in ("なし", ""):
        return ""
    return f'<span class="lp">ループ {esc(name)}</span>'


def _item(title, tag, rows, anchor=""):
    body = "".join(f"<dt>{esc(k)}</dt><dd>{v}</dd>" for k, v in rows if v)
    return f'<article class="ay"{f" id={chr(34)}{esc(anchor)}{chr(34)}" if anchor else ""}><h3>{esc(title)}{_tag(tag)}</h3><dl>{body}</dl></article>'


def _set_item(row):
    changes = [t for t in template_changes() if t.get("sheet_set") in [n.strip() for n in row["版"].split("・")]]
    rids = [r for t in changes for r in t.get("record_ids", [])]
    know = esc(row["知見"]) + "".join(f"<br>人の説明 {esc(x)}" for x in told(rids))
    return _item(row["版"], row["ループ"], (("どこを良くしたか", esc(row["前の版から変えた事と理由"])), ("どの知見から", know),
                                         ("その後に分かった事", esc(row["分かった問題、捨てた理由"])), ("記録", esc(row["記録"]))), row["版"].split("・")[0].split(" ")[0])


def _version_item(sid, hid, letter, v):
    ch = "、".join(f'{esc(_param_name(sid, c["param"]))} {esc(c.get("from", ""))}→{esc(c["to"])}' if c.get("from") not in (None, "") else f'{esc(_param_name(sid, c["param"]))} → {esc(c["to"])}' for c in v.get("changes", []))
    why = "、".join(esc(c["why"]) for c in v.get("changes", []) if c.get("why"))
    know = "<br>".join(x for x in [why, *(f"人の説明 {esc(t)}" for t in told(v.get("record_ids", [])))] if x)
    return _item(f"仮説 {letter} 版 {v['version']}", loop_of(v), (("どこを良くしたか", ch), ("どの知見から", know), ("記録", esc("・".join(v.get("record_ids", []))))))


def toy_block(sid, data):
    """玩具 1 つの版の歩み。新しい版が上。書く事が無ければ空。"""
    items = ""
    for h in data["hypotheses"]:
        for v in reversed(versions(sid, h["id"])):
            items += _version_item(sid, h["id"], hypotheses.letter(h), v)
    for row in rows_for(_prefix(_template(sid))):
        items += _set_item(row)
    if not items:
        return ""
    return f'<section class="sec" id="{esc(sid)}"><h2>{esc(data["toy"])}</h2><p class="links"><a href="/toy/{esc(sid)}">玩具の頁</a><a href="/loop/{esc(sid)}">工作の様子</a></p>{items}</section>'


def engine_versions():
    """エンジンの版の台帳。読めなければ None（エンジンの repo は別にある）。"""
    root = pathlib.Path(os.environ.get("OMOCHAE_ENGINE_REPO") or ROOT.parent / "paper-to-toy")
    try:
        return json.loads((root / "data/engine/versions.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def engine_block():
    data = engine_versions()
    if data is None:
        return '<p class="meta">エンジンの版の台帳が、この機械から読めません。</p>'
    items = ""
    for v in reversed(data.get("versions", [])):
        sets = "、".join(f"{esc(k)}: {esc(x)}" for k, x in (v.get("sheet_sets") or {}).items())
        made = f'案 {len(v["proposals"])} 件から' if v.get("proposals") else ""
        items += _item(f"エンジンの版 {v['version']}", "3" if v.get("proposals") else "前", (("どこを良くしたか", esc(v.get("note", "")) or esc(made)), ("刷った組", sets), ("日", esc(v.get("at", "")))))
    return items


def _spoken_count(sids):
    from api.words import spoken_own_ids

    return sum(len(spoken_own_ids(sid)) for sid in sids)


def loop_summary(sids):
    """ループごとの今の数。上下を付けない。効いたかは言わない。"""
    n_versions = n_made = 0
    for sid in sids:
        for h in hypotheses.load(sid)["hypotheses"]:
            for v in versions(sid, h["id"]):
                n_versions += 1
                n_made += loop_of(v) != "2"
    n_sets = len(template_changes())
    data = engine_versions()
    released = "読めません" if data is None else f"{sum(1 for v in data.get('versions', []) if v.get('proposals'))} 版"
    return {"1": f"話した考えから生まれたその人の紙 {_spoken_count(sids)} 枚（たたき台は変えません）", "2": f"直した版: 寸法の版 {n_versions - n_made}、組の直し {n_sets}",
            "3": f"案から刻んだエンジンの版: {released}", "4": f"上げた後の字も材料にした版 {n_made}"}


def _kinds():
    """型ごとの玩具の数。"""
    count = {}
    for sid in sources():
        count[_template(sid)] = count.get(_template(sid), 0) + 1
    return count


def _has(mark, template):
    """その型に、この知見が入っているか。雛形のコードから見る。"""
    tpl = TEMPLATES[template]
    parts = tpl.parts(tpl.DEFAULTS)
    if mark == "hide_folds":
        return any(q.hide_folds for q in parts)
    if mark == "no_cuts":
        return not any(q.cuts for q in parts)
    if mark == "redraw":
        return any(q.art for q in parts)
    if mark == "ruler_first":
        return "物差し" in tpl.steps(tpl.DEFAULTS)[0]
    if mark == "legend":  # 凡例は全部の型の紙を刷る compose が持つ
        return True
    raise ValueError(f"知らない見分け方: {mark}")


def shared_block():
    count = _kinds()
    order = [k for k in KINDS if k in count]
    name = lambda k: f"{KINDS[k]}（{count[k]} 種）"
    rows = ""
    for r in shared_rows():
        mark = r["見分け方"]
        if mark == "これから":
            inside, outside = "まだ紙に入っていません", ""
        else:
            yes = [k for k in order if _has(mark, k)]
            no = [k for k in order if k not in yes]
            inside = "全部の型" if not no else "、".join(name(k) for k in yes)
            outside = "、".join(name(k) for k in no)
        rows += _item(r["知見"], r["ループ"], (("どこから", esc(r["どこから"])), ("入っている型", esc(inside)), ("まだの型", esc(outside))))
    return rows


def page(look=skin.DEFAULT, path="/loop/ayumi"):
    sids = sources()
    summary = loop_summary(sids)
    legend = "".join(f'<tr><td>ループ {n}</td><td>{esc(text)}</td><td>{esc(summary[n])}</td></tr>' for n, text in LOOPS)
    toys = "".join(toy_block(sid, hypotheses.load(sid)) for sid in sids)
    rest = sum(1 for sid in sids if not toy_block(sid, hypotheses.load(sid)))
    body = (f'<section class="hero"><div><h1>{TITLE}</h1><p class="lead">新しい版の型紙について、前の版からどこを良くしたか、どの知見から直したか、どのループで直したかを並べます。新しい版が上です。</p>'
            '<p class="meta">作る側の頁です。公開しません。「どこを良くしたか」は作る側が変えた所です。本当に良くなったかは機械では決めません。紙で作って、人が読みます。ループの欄は作る側の読みです。</p>'
            '<p class="links"><a href="/loop">改善の輪の一覧</a></p></div></section>'
            f'<section class="sec" id="loops"><h2>4 つのループ</h2><table><thead><tr><th>ループ</th><th>何が回るか</th><th>今の数</th></tr></thead><tbody>{legend}</tbody></table>'
            f'<p class="meta">{BEFORE}: 試す前に、作る側が図と計算から直した版です。</p></section>'
            f'<section class="sec" id="shared"><h2>共通にしている知見</h2><p class="meta">1 つの型紙で分かった事を、ほかの型にも入れている物です。どの型に入っているかは、雛形のコードから数えています。</p>{shared_block()}</section>'
            f'{toys}'
            f'<section class="sec" id="others"><h2>ほかの {rest} 種</h2><p class="meta">まだ版 1 のままです。作った記録が来ると、ここに版が並びます。</p></section>'
            f'<section class="sec" id="engine"><h2>エンジンの版</h2><p class="meta">同じ型から刷る全部の紙に効く直しです（ループ 3）。</p>{engine_block()}</section>')
    return skin.shell(TITLE, body, look, "", path, STYLE)
