"""型紙の版の歩み（本人の希望 2026-11-06）。裏側の改善ループの頁の 1 つ。

本人の言葉: 新しく作られた版の型紙について「その前の履歴・どこが良くなったか・どういう知見で良くなったか・共通化している知見」が見れるといい。
「その改善が、どこの改善ループで走った物か（ループ1〜4のどれか）も見れるといい」。

判断の芯:
- 別の台帳を作らない。版の表と共通の知見は docs/process/trials/sheets/README.md、寸法の版は omochae.loop を読むだけ。
  どのループかと、記録についた字は kaizen_versions が決める（記録から決める。手で足した欄は使わない）。
- 頁に出す答えは repo の中の data だけで決まる。エンジンの版は別の repo の台帳で、読めない時は「読めません」と出す。
- 良くなったかは機械が決めない（本人の決まり）。「どこを良くしたか」は作る側が変えた所で、効いたと言う物ではない。頁の頭に書く。
- 表に行の無い雛形の直し（T-番号）を黙って消さない。根拠の記録の玩具の札に出し、玩具が分からない物は「雛形の分からない直し」に出す。
  雛形の直しは同じ型の全部に効くが、札は根拠の玩具に置く（同じ直しを 38 回並べない）。
- 作る側の頁。学ぶ人の頁から道を置かず、合言葉なしで開いたデモでは出さない（J-028。/loop の下なので play_server が止める）。
- 順位を付けない。型の並びは雛形の表の順で、数の多い順にしない（J-025）。
"""
import pathlib
import re

from omochae import hypotheses
from omochae.compose import TEMPLATES

from . import kaizen_versions as kv
from . import skin
from .kaizen import TABLE_STYLE, _param_name, versions
from .play_server import esc, sources

ROOT = pathlib.Path(__file__).resolve().parents[2]
LEDGER = ROOT / "docs/process/trials/sheets/README.md"
TITLE = "型紙の版の歩み"
LOOPS = (("1", "考えを話す → 紙が生まれる"), ("2", "作りながらの工夫 → 型紙が直る"), ("3", "エンジンごと直す → 同じ型の紙が全部直る"), ("4", "上げて残す → ギャラリーと次の版の材料"))
SET_NAME = re.compile(r"[a-z_-]+-v\d+")
WORK_NOTE = re.compile(r"（[^（）]*(?:カード|hack-|sub-|lane/)[^（）]*）")  # 作業の番号と線の名は頁に出さない
# 本人が決めた字（11-06、読めない字の一覧の作る側の頁の分）。版の表の文書は作業の記録なので書き換えず、頁に出す時だけ替える。一字も変えない。
SHOWN = (("本人の決定（11-05、#163）: 床 F5.fan_height を直したので、H-E を 14 折り・高さ 36mm にした。", "本人の決定（11-05）: 扇の高さの決まりを直したので、仮説 E を 14 折り・高さ 36mm にしました。"),
         ("床の直し（#163）から。試行からではない", "決まりの直しから。試行からではありません"),
         ("学習プリントの線の U-25 の案 1〜4 と research/22 の候補 1・4", "学習プリントの案と、調べた候補から"),
         ("拡大した図の粗さと裏写り（v4 から v5、J-007）", "拡大した図の粗さと裏写り（v4 から v5）"),
         ("組み立ての確かめと 11-04 の写真（J-033）。", "組み立ての確かめと 11-04 の写真。"),
         ("型紙エンジンに入った（paper-to-toy #91・739167b）", "型紙エンジンに入りました"),
         ("型紙エンジンの御来迎と虎に入った（paper-to-toy f6a40ed、main は #96 の e189dc6）", "型紙エンジンの御来迎と虎に入りました"))
# 仮説の番号は「仮説 A」と出す。日本語の字の後の空白は詰める（「の H-E」→「の仮説 E」、「型紙が H-C」→「型紙が仮説 C」）
HYPOTHESIS_NO = re.compile(r"(?:(?<=[^\x00-\x7f]) )?(?<![A-Za-z0-9])H-([A-Z])(?![A-Za-z0-9])")
ENGINE_ONLY = "型紙エンジンには入りました。刷った紙にはまだ入っていません"  # 型紙エンジンに入って、サイトの紙にはまだの知見
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
    text = WORK_NOTE.sub("", text).replace("**", "").replace("`", "").strip()
    for before, after in SHOWN:
        text = text.replace(before, after)
    return HYPOTHESIS_NO.sub(r"仮説 \1", text)


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


def _names(row):
    return [n.strip() for n in row["版"].split("・")]


def _tag(verdict):
    return f'<span class="lp">{esc(kv.tag(verdict))}</span>'


def _item(title, tag, rows, anchor=""):
    body = "".join(f"<dt>{esc(k)}</dt><dd>{v}</dd>" for k, v in rows if v)
    return f'<article class="ay"{f" id={chr(34)}{esc(anchor)}{chr(34)}" if anchor else ""}><h3>{esc(title)}{_tag(tag)}</h3><dl>{body}</dl></article>'


def _lines(items):
    return "".join(f"<br>{esc(x)}" for x in items)


def _set_item(row, prefix=""):
    """版の表の 1 行の札。id は、その玩具の版の名（組み合わせの行は 2 つの玩具に出るので、id が重ならないように）。"""
    names = _names(row)
    changes = [t for t in kv.template_changes() if t.get("sheet_set") in names]
    know = esc(row["知見"]) + _lines(kv.change_words(changes))
    return _item(row["版"], kv.change_verdict(changes), (("どこを良くしたか", esc(row["前の版から変えた事と理由"])), ("どの知見から", know),
                                                       ("その後に分かった事", esc(row["分かった問題、捨てた理由"]))), next((n for n in names if SET_NAME.fullmatch(n) and n.startswith(prefix)), ""))


def _version_item(sid, hid, head, v):
    ch = "、".join(f'{esc(_param_name(sid, c["param"]))} {esc(c.get("from", ""))}→{esc(c["to"])}' if c.get("from") not in (None, "") else f'{esc(_param_name(sid, c["param"]))} → {esc(c["to"])}' for c in v.get("changes", []))
    why = "、".join(esc(c["why"]) for c in v.get("changes", []) if c.get("why"))
    said = [x for rid in v.get("record_ids", []) for x in kv.record_words(rid)]
    know = why + _lines(said) if why else _lines(said).removeprefix("<br>")
    # 仮説の印（A・C）は札の題に出さない（本人の答え 11-08「そろえる。」（つくるの外も印なし））。head は呼び名（hypotheses.version_head。版がある仮説が 2 つ以上の玩具では名を添える）
    return _item(f"{head} 版 {v['version']}", kv.version_verdict(v), (("どこを良くしたか", ch), ("どの知見から", know), ("記録", esc("・".join(v.get("record_ids", []))))))


def _loose_changes():
    """表に行の無い雛形の直し。"""
    listed = {n for r in sheet_rows() for n in _names(r)}
    return [t for t in kv.template_changes() if t.get("sheet_set") not in listed]


def _change_item(t):
    """表に行の無い雛形の直しの札。"""
    return _item(str(t.get("sheet_set", "")), kv.change_verdict([t]), (("どこを良くしたか", esc("、".join(str(c) for c in t.get("changes", [])))), ("どの知見から", _lines(kv.change_words([t])).removeprefix("<br>")),
                                                                     ("記録", "" if t.get("in_repo") else esc("・".join(str(r) for r in t.get("record_ids", []))))))


def toy_block(sid, data):
    """玩具 1 つの版の歩み。新しい版が上（日付のある版を日の新しい順に、その後に版の表の行）。書く事が無ければ空。"""
    # 同じ玩具で版がある仮説が 2 つ以上の時は、札の題に仮説の名を添えて見分ける（仮説「…」 版 N）。印（A・C）は使わない。1 つの時は「仮説 版 N」。
    # 統括の割り振り 11-08（別の目の気づき: 印を外した後、2 つの仮説の版が同じ「仮説 版 2」で並ぶと見分けられない）
    many = sum(1 for h in data["hypotheses"] if versions(sid, h["id"])) > 1
    dated = [(v.get("adopted_at", ""), _version_item(sid, h["id"], hypotheses.version_head(h, many), v)) for h in data["hypotheses"] for v in versions(sid, h["id"])]
    dated += [(t.get("at", ""), _change_item(t)) for t in _loose_changes() if sid in kv.change_toys(t)]
    items = "".join(html for _, html in sorted(dated, key=lambda x: x[0], reverse=True))
    prefix = _prefix(_template(sid))
    for row in rows_for(prefix):
        items += _set_item(row, prefix)
    if not items:
        return ""
    return f'<section class="sec" id="{esc(sid)}"><h2>{esc(data["toy"])}</h2><p class="links"><a href="/toy/{esc(sid)}">玩具の頁</a><a href="/loop/{esc(sid)}">工作の様子</a></p>{items}</section>'


def unknown_block(sids):
    """根拠の記録から玩具が分からない雛形の直し。黙って消さない。無ければ空。"""
    items = "".join(_change_item(t) for t in _loose_changes() if not set(kv.change_toys(t)) & set(sids))
    return f'<section class="sec" id="unknown"><h2>雛形の分からない直し</h2>{items}</section>' if items else ""


def engine_block():
    data = kv.engine_ledger()
    if data is None:
        return '<p class="meta">エンジンの版の台帳が、この機械から読めません。</p>'
    items = ""
    for v in reversed(data.get("versions", [])):
        sets = "、".join(f"{esc(k)}: {esc(x)}" for k, x in (v.get("sheet_sets") or {}).items())
        made = f'案 {len(v["proposals"])} 件から' if v.get("proposals") else ""
        items += _item(f"エンジンの版 {v['version']}", kv.engine_verdict(v), (("どこを良くしたか", esc(v.get("note", "")) or esc(made)), ("どの知見から", _lines(kv.engine_findings(v)).removeprefix("<br>")), ("刷った組", sets), ("日", esc(v.get("at", "")))))
    return items


def _spoken_count(sids):
    from api.words import spoken_own_ids

    return sum(len(spoken_own_ids(sid)) for sid in sids)


def loop_summary(sids):
    """ループごとの今の数。上下を付けない。効いたかは言わない。"""
    verdicts = [kv.version_verdict(v) for sid in sids for h in hypotheses.load(sid)["hypotheses"] for v in versions(sid, h["id"])]
    data = kv.engine_ledger()
    released = "読めません" if data is None else f"{sum(3 in kv.engine_verdict(v)['loops'] for v in data.get('versions', []))} 版"
    return {"1": f"話した考えから生まれたその人の紙 {_spoken_count(sids)} 枚（たたき台は変えません）", "2": f"直した版: 寸法の版 {sum(2 in x['loops'] for x in verdicts)}",
            "3": f"雛形の直し {len(kv.template_changes())}、案から刻んだエンジンの版: {released}", "4": f"上げた物も材料にした版 {sum(4 in x['loops'] for x in verdicts)}"}


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
        # 丸い切り抜き（虎の次の組 tora-v6 の首の穴）も中の切り込み。矩形だけを見ると、切り抜く型を「切り込みなし」と言ってしまう
        return not any(q.cuts or q.round_cuts for q in parts)
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
            inside, outside = (ENGINE_ONLY if "型紙エンジン" in r["どこから"] else "まだ紙に入っていません"), ""
        else:
            yes = [k for k in order if _has(mark, k)]
            no = [k for k in order if k not in yes]
            inside = "全部の型" if not no else "、".join(name(k) for k in yes)
            outside = "、".join(name(k) for k in no)
        rows += _item(r["知見"], kv.set_verdict(_names(r)), (("どこから", esc(r["どこから"])), ("入っている型", esc(inside)), ("まだの型", esc(outside))))
    for k in kv.engine_shared(kv.engine_ledger()):  # 版に入った部品と決まりの案。出した人の 1 行があればそれを、無ければ案の題を出す
        rows += _item(k["finding"], k["verdict"], (("どこから", esc(k["from"])), ("入っている型", esc("全部の型" if k["all"] else k["where"])), ("直した所", esc(k["where"] if k["all"] else ""))))
    return rows


def page(look=skin.DEFAULT, path="/loop/ayumi"):
    sids = sources()
    summary = loop_summary(sids)
    legend = "".join(f'<tr><td>ループ {n}</td><td>{esc(text)}</td><td>{esc(summary[n])}</td></tr>' for n, text in LOOPS)
    blocks = [toy_block(sid, hypotheses.load(sid)) for sid in sids]
    toys = "".join(blocks)
    rest = blocks.count("")
    body = (f'<section class="hero"><div><h1>{TITLE}</h1><p class="lead">新しい版の型紙について、前の版からどこを良くしたか、どの知見から直したか、どのループで直したかを並べます。新しい版が上です。</p>'
            '<p class="meta">作る側の頁です。公開しません。「どこを良くしたか」は作る側が変えた所です。本当に良くなったかは機械では決めません。紙で作って、人が読みます。どのループかは、記録に結ばれているかで決めます。</p>'
            '<p class="links"><a href="/loop">改善の輪の一覧</a></p></div></section>'
            f'<section class="sec" id="loops"><h2>4 つのループ</h2><table><thead><tr><th>ループ</th><th>何が回るか</th><th>今の数</th></tr></thead><tbody>{legend}</tbody></table>'
            f'<p class="meta">{kv.OUTSIDE}: 作った人の記録に結ばれていない直しです（試す前の設計や、見学者の意見、決定だけの直し）。</p></section>'
            f'<section class="sec" id="shared"><h2>共通にしている知見</h2><p class="meta">1 つの型紙で分かった事を、ほかの型にも入れている物です。どの型に入っているかは、雛形のコードから数えています。</p>{shared_block()}</section>'
            f'{toys}{unknown_block(sids)}'
            f'<section class="sec" id="others"><h2>ほかの {rest} 種</h2><p class="meta">まだ版 1 のままです。作った記録が来ると、ここに版が並びます。</p></section>'
            f'<section class="sec" id="engine"><h2>エンジンの版</h2><p class="meta">同じ型から刷る全部の紙に効く直しです（ループ 3）。</p>{engine_block()}</section>')
    return skin.shell(TITLE, body, look, "", path, STYLE)
