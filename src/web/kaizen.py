"""改善の輪（本人の方針、2026-11-05 朝）: 「作ったものの感想と動きを報告してもらったら、サイト側もループを回し、型紙の改善をする。
そうすることでより良いおもちゃの型紙を提供できる」。

判断の芯:
- 輪は、報告（記録＋感想）→ 人の説明 → 読み → 寸法を 1 つ変えて次の版 → 次に作る人はその版を刷る、の順。既にある台帳（omochae.loop）を
  画面で見える形にするだけで、別の台帳を作らない。版は data/loop の version-*.json、根拠は記録の ID。
- 「次の版を待つ報告」を数えて出す。説明の無い報告は、先に説明を待つ（J-013: 人の説明が AI より先）。
- 成績に見える数（何件動いた、など）は、玩具の頁の節と一覧 /loop には出さない（J-025）。出すのは「報告の数」「版の数」「変えた寸法」だけ。
- 玩具ごとの作る側の頁 /loop/<印>（toy_page）だけは、工作の様子の集計を出す（本人の決定 11-05 朝「工作の様子を蓄積して、サービス全体の改善をする」）:
  聞かれた事・止まった所・最初に動いた所・感想・版ごとの動きの札の数。版や案内を直す材料で、玩具や仮説の上下ではない事を頁の頭に書く。
  仮説は字（A・B）だけで指し、名前と動かし方は出さない（予想の前でも開ける頁なので、F9.prediction の線を守る）。
  出すのは Issue #119（U-45）の 6 つ（止まった段・動きの結果・感想の言葉・聞く口の質問・完成の様子・サイトの流れ）で、数と幅だけ。
  多い順に仮説や玩具を並べる・点・％の成績、のような上下を付ける形は作らない。人は、その場限りの無作為の印で数える。
- /loop は作る側（サイト側）が輪を回すための一覧。学ぶ人の頁からは道を置かない（集計は学ぶ人の画面に出さない線。道を知っている作る側が開く）。
  合言葉なしで開いたデモでは出さない（J-028）。学ぶ人の頁の節には、版と根拠だけを出し、採った人の名前は出さない（自由な文で、名前を書かない線に沿う）。
- 受け持ち（本人の決定 11-05、カード 20261105-090458 の (b)）: 雛形そのものを直すための報告の入口と道具（報告の形・検査・集計）は
  エンジン（paper-to-toy）の側。ここが持つのは、学ぶ人の記録と感想、仮説ごとの版（寸法を 1 つ変えた次の版）、その表示まで。
  だから、報告から案を機械で出す道具はここに置かない。
"""
import pathlib

from omochae import hypotheses, loop, making_log, records

from . import skin
from .play_server import PARAM_NAMES, esc, sources


def versions(sid, hid):
    """版 2 以降の記録（採った変更・根拠の記録・採った人）。版 1 は仮説の寸法そのもの。"""
    out = []
    for v in range(2, loop.latest_version(sid, hid) + 1):
        _, rec = loop.version_params(sid, hid, v)
        if rec:
            out.append(rec)
    return out


def _param_name(sid, k):
    tpl = TEMPLATES_NAMES(sid)
    return PARAM_NAMES.get(k, tpl.get(k, k))


def TEMPLATES_NAMES(sid):
    from omochae.compose import TEMPLATES

    return getattr(TEMPLATES[hypotheses.load(sid).get("template", "slider_fan")], "PARAM_NAMES", {})


def pending(sid, recs):
    """まだ版に使っていない報告。(説明があって次の版に進める物, 説明を待つ物)。"""
    used = {rid for h in hypotheses.load(sid)["hypotheses"] for v in versions(sid, h["id"]) for rid in v.get("record_ids", [])}
    ready, waiting = [], []
    for r in recs:
        if r["id"] in used:
            continue
        (ready if loop.explanation(r["id"]) else waiting).append(r)
    return ready, waiting


def section(sid, data, recs):
    """玩具の頁の節「型紙の改善の輪」。記録の後に置く。"""
    rows = ""
    for h in data["hypotheses"]:
        for v in versions(sid, h["id"]):
            ch = "、".join(f'{esc(_param_name(sid, c["param"]))} {esc(c.get("from", ""))}→{esc(c["to"])}' if c.get("from") not in (None, "") else f'{esc(_param_name(sid, c["param"]))} → {esc(c["to"])}' for c in v.get("changes", []))
            why = "、".join(esc(c.get("why", "")) for c in v.get("changes", []) if c.get("why"))
            rows += (f'<li><b>仮説 {esc(hypotheses.letter(h))} 版 {v["version"]}</b>: {ch}'
                     + (f'（{why}）' if why else "") + f'。根拠: {"・".join(f"<a href=#{esc(r)}>{esc(r)}</a>" for r in v.get("record_ids", []))}'
                     + f'。<a href="/toy/{sid}?see={esc(h["id"])}&kind=sheet&v={v["version"]}#win">この版の型紙</a></li>')
    # 雛形の直し（T-）も、この玩具の記録を根拠にした物を出す。寸法の版だけだと、形や組み方の直しが見えない。
    mine = {r["id"] for r in recs}
    for t in loop.template_changes():
        if mine & set(t.get("record_ids", [])):
            rows += (f'<li><b>雛形の直し {esc(t.get("id", ""))}（{esc(t.get("sheet_set", ""))}）</b>: {esc("、".join(t.get("changes", [])))}。'
                     f'根拠: {"・".join(f"<a href=#{esc(r)}>{esc(r)}</a>" for r in t.get("record_ids", []))}</li>')
    ready, waiting = pending(sid, recs)
    lines = f'<ul>{rows}</ul>' if rows else '<p class="meta">報告から直した版はまだありません。最初の報告が最初の版を変えます。</p>'
    todo = ""
    if ready:
        todo += f'<p>次の版を待つ報告 {len(ready)} 件: ' + "・".join(f'<a href="#{esc(r["id"])}">{esc(r["id"])}</a>' for r in ready) + '（記録の「次の版を作る」から、寸法を 1 つ変えて刷ります）</p>'
    if waiting:
        todo += f'<p class="meta">説明を待つ報告 {len(waiting)} 件: ' + "・".join(f'<a href="#{esc(r["id"])}">{esc(r["id"])}</a>' for r in waiting) + '（人の説明が先。説明が付くと次の版に進めます）</p>'
    if not recs:
        todo = '<p class="meta">報告はまだありません。作って、記録と感想を残すと、ここから型紙が変わっていきます。</p>'
    return (f'<section class="sec" id="kaizen"><h2>型紙の改善の輪</h2>'
            '<p class="meta">作った人の報告（動きと感想）→ 人の説明 → 読み → 寸法を 1 つ変えて次の版 → 次に作る人はその版を刷る。版は答えではなく、報告をもとに直した翻案です。ここで変えるのはこの仮説の寸法で、型紙の作りそのもの（雛形）の直しは型紙エンジンの側が受け持ちます。</p>'
            f'{lines}{todo}</section>')


def page(look=skin.DEFAULT, path="/loop"):
    """サイト側が輪を回すための一覧。報告のある玩具から順に、版と次の版を待つ報告を数えて出す。"""
    items, n_rep = [], 0
    asked = {}
    for a in making_log.asks():
        asked[a.get("source_id")] = asked.get(a.get("source_id"), 0) + 1
    # 記録は 1 回で読んで玩具ごとに分ける（玩具ごとに読むと、1 回の表示で全部の記録のファイルを 83 回読む）。
    by_toy = {}
    for r in records.all_records():
        by_toy.setdefault(r.get("source_id"), []).append(r)
    for sid in sources():
        recs = by_toy.get(sid, [])
        # 報告が無くても、聞かれた事がある玩具は載せる: 質問だけあって報告が無いのは「作りかけて止まった」かもしれない様子で、案内を直す材料になる。
        if not recs and not asked.get(sid):
            continue
        data = hypotheses.load(sid)
        n_rep += len(recs)
        vers = sum(len(versions(sid, h["id"])) for h in data["hypotheses"])
        ready, waiting = pending(sid, recs)
        items.append((len(ready), sid, data["toy"], len(recs), vers, len(waiting), asked.get(sid, 0)))
    # 並びは本の順のまま。待っている報告の多い順にすると、玩具に上下を付ける形になる（J-025）。
    rows = "".join(f'<tr><td><a href="/toy/{esc(sid)}#kaizen">{esc(toy)}</a>　<a href="/loop/{esc(sid)}">様子</a></td><td>{n}</td><td>{v}</td><td>{r}</td><td>{w}</td><td>{q}</td></tr>'
                   for r, sid, toy, n, v, w, q in items)
    table = (f'<table><thead><tr><th>玩具</th><th>報告</th><th>報告から直した版</th><th>次の版を待つ報告</th><th>説明を待つ報告</th><th>聞かれた事</th></tr></thead><tbody>{rows}</tbody></table>'
             if items else '<p class="meta">報告はまだありません。</p>')
    body = (f'<section class="hero"><div><h1>改善の輪</h1><p class="lead">作った人の報告を、型紙の改善に回す所。報告か質問のある玩具 {len(items)} 種、報告 {n_rep} 件。</p>'
            '<p class="meta">輪: 報告（動きと感想）→ 人の説明 → 読み → 寸法を 1 つ変えて次の版 → 次に作る人はその版を刷る。並びは本の順です。</p></div></section>'
            f'<section class="sec">{table}</section>')
    return skin.shell("改善の輪", body, look, "", path, TABLE_STYLE)


TABLE_STYLE = "table{border-collapse:collapse;width:100%}th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--rule)}th{font-weight:normal;color:var(--mute);font-size:13px}"


# 測った値の欄の、頁での呼び方。表に無い欄は、欄の名前のまま出す（雛形ごとに測る物が違うので、ここで全部は決めない）。
MEASURE_NAMES = {"opened_deg": "開いた角度（度）", "ten_swings_sec": "10 往復の秒"}
STAGE_NAMES = {"predict": "予想を書いた", "print": "型紙を刷った", "make": "作りながら見る頁を開いた", "record": "記録を残した"}


def _span(sp, unit=""):
    """幅 [最小, 最大, 件数] を「20〜40 分（3 件）」の形にする。平均や割合にはしない（少ない件数で、確かな値のように見えるため）。"""
    lo, hi, n = sp
    return (f"{lo:g}" if lo == hi else f"{lo:g}〜{hi:g}") + f"{unit}（{n} 件）"


def _clock(sec):
    sec = int(sec)
    return f"{sec // 60:02d}:{sec % 60:02d}"


def _by(label="確かめた人"):
    return f'<label style="display:inline-block;margin:0 8px 0 0;font-size:12px">{label}<input type="text" name="by" required style="width:9em"></label>'


def video_section(sid, paper):
    """動画 → 札 → 直しの案 → 版 → 版ごとの止まり方を、1 本につなげて見せる（本人の指示 11-05「実際に型紙が改善するかを見たい」、J-029）。
    数は比べるための手がかりで、効いたとは判定しない（数件の比べなので）。映像とコマは、人が顔と声の確かめをした記録だけ出す。"""
    from omochae import trial_video as tv

    trials = tv.all_for(sid)
    fixes = tv.fixes(sid)
    eff = tv.effect(sid)
    if not trials and not any(h["rows"] for h in eff.values()):
        return '<p class="meta">動画を結んだ試行はまだありません。</p>'
    out = ""
    for d in trials:
        rid = d["record_id"]
        rec = loop.record(rid)
        out += (f'<h3 id="v-{esc(rid)}">{esc(rid)} {esc(paper(d["hypothesis_id"]))}・{esc(d.get("sheet_set", ""))} 版 {esc(d.get("sheet_version", 1))}</h3>'
                f'<p class="meta">見た事: {esc(rec.get("result", ""))}。試した日: {esc(rec.get("tried_on") or str(rec.get("recorded_at", ""))[:10])}。'
                + '</p>')
        told = loop.explanation(rid)
        # 人の説明が先（J-013）。説明の後でなければ直しの案を作れない。
        out += (f'<p>説明: {esc(told["text"])}（次に試したい事: {esc(told["next_idea"])}）</p>' if told else
                f'<form method="post" action="/record/{esc(rid)}/explain"><input type="hidden" name="back" value="loop"><label>何が起きたと思いますか（わからない、でもよい）<textarea name="text" required></textarea></label>'
                f'<label>次に試したい事<input type="text" name="next_idea" required></label>{_by("書いた人")}<button class="quiet">説明を残す</button></form>')
        for v in d["videos"]:
            spans = "、".join(f"{_clock(a)}〜{_clock(b)}" for a, b in v.get("still", [])) or "無し"
            # 顔と声の確かめは動画ごと（確かめた後に結んだ動画を、見ないまま出さない）。
            if v.get("checked_by"):
                head = f'<video src="/loop/video/{esc(rid)}/{esc(v["file"])}" controls muted playsinline preload="metadata" style="max-width:100%;max-height:360px"></video>'
                who = f'顔と声の確かめ: {esc(v["checked_by"])}。'
            else:
                head = (f'<form method="post" action="/loop/{esc(sid)}/shown"><input type="hidden" name="record" value="{esc(rid)}"><input type="hidden" name="video" value="{esc(v["file"])}">{_by()}'
                        f'<button class="quiet">{esc(v["file"])} に顔と声が入っていないと確かめた</button></form>')
                who = "顔と声の確かめ待ちなので、映像とコマは出していません。"
            out += f'{head}<p class="meta">{esc(v["file"])}（{_clock(v["duration"])}）。{who}動きの少なかった区間: {spans}（手が止まった候補で、止まったとは限りません）</p>'
        rows = ""
        for m in d["marks"]:
            state = "外した" if m.get("rejected_by") else f'確かめた人: {esc(m["confirmed_by"])}' if m.get("confirmed_by") else "案（確かめ待ち）"
            if not m.get("confirmed_by") and not m.get("rejected_by"):
                state += (f'<form method="post" action="/loop/{esc(sid)}/judge" style="margin-top:6px"><input type="hidden" name="record" value="{esc(rid)}"><input type="hidden" name="mark" value="{esc(m["id"])}">{_by()}'
                          '<button class="quiet" name="action" value="confirm">確かめた</button> <button class="quiet" name="action" value="drop">外す</button></form>')
            ok = tv.shown(rid, m["video"])
            at = f'<a href="/loop/video/{esc(rid)}/{esc(m["video"])}#t={int(m["at"])}">{_clock(m["at"])}</a>' if ok else _clock(m["at"])
            pic = f'<img src="/loop/frame/{esc(rid)}/{esc(pathlib.Path(m["video"]).stem)}-{int(m["at"]):06d}.jpg" alt="" loading="lazy" style="height:72px">' if ok else ""
            rows += (f'<tr><td>{esc(m["id"])}</td><td>{at}{pic}</td><td>{"手順 " + esc(m["step"]) if m.get("step") is not None else "—"}</td><td>{esc(tv.KINDS.get(m["kind"], m["kind"]))}</td>'
                     f'<td>{esc(m["note"])}</td><td>読んだ人: {esc(m["read_by"])}。{state}</td></tr>')
        out += ("<table><thead><tr><th>札</th><th>時刻</th><th>手順</th><th>種類</th><th>何が</th><th>読み</th></tr></thead><tbody>" + rows + "</tbody></table>"
                if rows else '<p class="meta">札はまだありません。</p>')
    rows = ""
    for f in fixes:
        to = f'{esc(f["param"])} → {esc(f["to"])}' if f.get("param") else "形や手順の文"
        state = {"pending_human": "人の採否を待っている", "rejected": f'採らない（{esc(f.get("decided_by", ""))}）'}.get(f["status"])
        if f["status"] == "adopted":
            state = f'版 {esc(f["version"])} になった（採った人: {esc(f["decided_by"])}）' if f.get("version") else f'{esc(f.get("template_change", ""))}・{esc(f.get("sheet_set", ""))} になった（採った人: {esc(f["decided_by"])}）'
        if f["status"] == "pending_human":
            # 形や手順の文の案は、雛形を直した後で採る（直した組と commit を書く。まだ直していない案を、直した事にしない）。
            more = "" if f.get("param") else ('<label style="display:inline-block;margin:0 8px 0 0;font-size:12px">直した組<input type="text" name="sheet_set" style="width:8em"></label>'
                                              '<label style="display:inline-block;margin:0 8px 0 0;font-size:12px">commit<input type="text" name="commit" style="width:6em"></label>')
            state += (f'<form method="post" action="/loop/{esc(sid)}/fix" style="margin-top:6px"><input type="hidden" name="fix" value="{esc(f["id"])}">{more}{_by("決めた人")}'
                      '<button class="quiet" name="action" value="adopt">採る</button> <button class="quiet" name="action" value="reject">採らない</button></form>')
        rows += f'<tr><td>{esc(f["id"])}</td><td>{esc(f["record_id"])} の {esc("・".join(f["mark_ids"]))}</td><td>{esc(f["text"])}</td><td>{to}</td><td>{state}</td></tr>'
    out += "<h3>直しの案</h3>" + ("<table><thead><tr><th>案</th><th>根拠の札</th><th>何をどう直すか</th><th>変える物</th><th>どうなったか</th></tr></thead><tbody>" + rows + "</tbody></table>"
                                  if rows else '<p class="meta">直しの案はまだありません。確かめた札と人の説明の後に作れます。</p>')
    out += '<h3>版ごとの止まり方</h3><p class="meta">確かめた札（動画）と「ここで止まった」の札（画面）の数を、手順ごとに並べます。数件の比べなので、効いたかは人が読みます。</p>'
    shown_any = False
    for hid, h in eff.items():
        if not h["rows"]:
            continue
        shown_any = True
        cols = h["columns"]
        head = "".join(f"<th>{esc(c[0] or '組の記録なし')} 版 {esc(c[1])}（報告 {h['reports'].get(c, 0)} 件）</th>" for c in cols)
        body = ""
        for step, cells in h["rows"].items():
            tds = ""
            for c in cols:
                x = cells.get(c)
                tds += f'<td>動画 {x["video"]}・画面 {x["tap"]}</td>' if x else "<td>—</td>"
            body += f"<tr><td>手順 {esc(step)}</td>{tds}</tr>"
        out += f'<p>{esc(paper(hid))}</p><table><thead><tr><th>手順</th>{head}</tr></thead><tbody>{body}</tbody></table>'
    if not shown_any:
        out += '<p class="meta">確かめた札も画面の札も、まだありません。</p>'
    return out


def toy_page(sid, look=skin.DEFAULT, path=None, note=""):
    """その玩具の工作の様子（作る側の頁。公開しない）。Issue #119（U-45）の 6 つの集計を、数と幅で出す:
    1 止まった段 / 2 動きの結果 / 3 感想の言葉 / 4 聞く口の質問 / 5 完成の様子 / 6 サイトの流れ。
    なぜ別の頁か: 学ぶ人の頁（/toy/<印>）に集計を出すと、数が成績や答えのように見える（J-025）。ここは案内・答え・型紙の版を直す人が読む。
    上下を付ける形は作らない: 仮説や玩具を多い順に並べない（並びは版・手順・仮説の元の順）、点や％の成績にしない。
    仮説は字だけで指す。名前と動かし方は出さない（予想の前でも開ける頁なので）。"""
    data = hypotheses.load(sid)
    sm = making_log.summary(sid)
    letter = {h["id"]: hypotheses.letter(h) for h in data["hypotheses"]}
    paper = lambda hid: f"仮説 {letter[hid]} の紙" if hid in letter else f"自分の仮説 {hid} の紙"
    none = lambda text: f'<p class="meta">{text}</p>'

    def lines(items, empty):
        return "<ul>" + "".join(f"<li>{esc(x)}</li>" for x in items) + "</ul>" if items else none(empty)

    def table(head, rows):
        return "<table><thead><tr>" + "".join(f"<th>{h}</th>" for h in head) + f"</tr></thead><tbody>{rows}</tbody></table>"

    # 1 止まった段: 版ごと・手順ごとの「止まった」の札の数と、印のある人の数。並びは版と手順の番号の順（多い順にすると手順の並びが読めない）。
    rows = "".join(f'<tr><td>{esc(paper(h))}</td><td>版 {esc(v)}</td><td>手順 {esc(n)}</td><td>{x["taps"]} 回</td><td>{str(x["people"]) + " 人" if x["people"] else "—"}</td></tr>'
                   for h, vs in sm["stuck_by_version"].items() for v, ss in vs.items() for n, x in ss.items())
    s1 = table(("紙", "版", "手順の番号", "止まったの札", "止まった人（印のある分）"), rows) if rows else none("止まったの札はまだ押されていません。")
    s1 += (f'<h3>止まった所の言葉</h3>{lines(sm["stuck"], "書かれた物はまだありません。")}'
           f'<h3>最初に動いた所</h3>{lines(sm["first_moved"], "書かれた物はまだありません。")}'
           f'<h3>何を変えると違いが出そうか</h3>{lines(sm["what_if"], "書かれた物はまだありません。")}')

    # 2 動きの結果: 仮説と版ごとの「見た事」の数、測った値の幅、直した点。
    rows = ""
    for hid, by_v in sm["results_by_version"].items():
        for v in sorted(by_v):
            ms = sm["measures"].get(hid, {}).get(v, {})
            span = "、".join(f"{esc(MEASURE_NAMES.get(k, k))} {_span(sp)}" for k, sp in ms.items()) or "—"
            rows += f'<tr><td>{esc(paper(hid))}</td><td>版 {esc(v)}</td><td>{"、".join(f"{esc(k)} {n}" for k, n in by_v[v].items())}</td><td>{span}</td></tr>'
    s2 = table(("紙", "版", "動きの札", "測った値の幅"), rows) if rows else none("報告はまだありません。")
    fixes = [f'{f["record_id"]}（{paper(f["hypothesis_id"])}・版 {f["sheet_version"]}）: {f["part"]} / {f["change"]} / {f["outcome"]}' for f in sm["fixes"]]
    s2 += f'<h3>直した点（部品・変えた事・結果）</h3>{lines(fixes, "書かれた物はまだありません。")}'

    # 3 感想の言葉: 分からなかった側と面白かった側に分けて並べる（たとえと説明のどこを言い換えるかの材料）。
    hard, fun = sm["words"]["hard"], sm["words"]["fun"]
    s3 = (f'<h3>分からなかった・むずかしかった（{len(hard)} 件）</h3>{lines(hard, "書かれた物はまだありません。")}'
          f'<h3>面白かった・楽しかった（{len(fun)} 件）</h3>{lines(fun, "書かれた物はまだありません。")}'
          f'<h3>感想（全部、{len(sm["impressions"])} 件）</h3>{lines(sm["impressions"], "書かれた物はまだありません。")}')

    # 4 聞く口の質問: 手順の段ごとに、同じ問いを束ねる。段の分からない質問は「段なし」。
    s4 = ""
    for h, ss in sm["asks_by_step"].items():
        for step, qs in ss.items():
            name = f"{esc(paper(h))}・手順 {esc(step)}" if step is not None else f"{esc(paper(h))}・段なし"
            s4 += f"<h3>{name}</h3>" + table(("聞かれた事", "回数"), "".join(f"<tr><td>{esc(q)}</td><td>{n} 回</td></tr>" for q, n in qs))
    s4 = s4 or none("聞かれた事はまだありません。")
    if sm["asks_dropped"]:
        s4 += f'<p class="meta">連絡先の形があったので文を残さなかった質問: {sm["asks_dropped"]} 件</p>'

    # 5 完成の様子: 時間は幅、動いた記録は「何件のうち何件」。割合の％にしない。途中でやめた段は、印のある人の分だけ。
    c = sm["completion"]
    s5 = "<ul>"
    s5 += f'<li>最初に動くまでの分: {_span(c["minutes"], " 分") if c["minutes"] else "書かれた物はまだありません"}</li>'
    s5 += f'<li>「{esc(c["moved_word"])}」の記録: {sm["reports"]} 件のうち {c["moved"]} 件</li>' if sm["reports"] else "<li>報告はまだありません</li>"
    s5 += f'<li>できたの札: {sm["steps_done"]} 回</li></ul>'
    rows = "".join(f"<tr><td>{esc(paper(h))}</td><td>手順 {esc(n)}</td><td>{k} 人</td></tr>" for h, ss in c["quit_steps"].items() for n, k in ss.items())
    s5 += "<h3>途中でやめた段（できたを押していない人が、最後に居た手順）</h3>" + (
        table(("紙", "手順の番号", "人（印のある分）"), rows) if rows else none("印のある人の記録はまだありません。"))

    # 6 サイトの流れ: 順路の段（予想 → 型紙 → 作る → 記録）ごとの、先へ進んだ数。
    rows = "".join(f'<tr><td>{STAGE_NAMES[k]}</td><td>{x["events"]} 回</td><td>{str(x["people"]) + " 人" if x["people"] else "—"}</td></tr>' for k, x in sm["flow"].items())
    s6 = table(("段", "出来事の数", "人（印のある分）"), rows)

    body = (f'<section class="hero"><div><h1>{esc(data["toy"])} の工作の様子</h1>'
            '<p class="lead">作る側の集計。学ぶ人の頁には出しません。公開しない頁です。上下を付ける物ではありません。</p>'
            f'<p class="meta">聞く口の質問、手順の進み、試した記録の止まった所・感想・動きの札を、案内と答えと型紙の版を直す材料として並べます。'
            f'名前と連絡先は残していません（質問の文に連絡先の形があれば、文ごと残しません）。人は、その場限りの無作為の印で数えます（印の無い出来事は札の数だけ）。'
            f'声・映像・写真はここに入りません。報告 {sm["reports"]} 件。</p>'
            f'<p class="links"><a href="/loop">改善の輪の一覧</a><a href="/toy/{esc(sid)}#kaizen">この玩具の頁の輪</a></p></div></section>'
            + (f'<p id="msg">{esc(note)}</p>' if note else "") +
            f'<section class="sec" id="k0"><h2>動画から版まで</h2><p class="meta">作成の過程の動画 → 札 → 人の確かめ・説明 → 直しの案 → 人が採る → 版 → 版ごとの止まり方。</p>{video_section(sid, paper)}</section>'
            f'<section class="sec" id="k1"><h2>1 止まった段</h2><p class="meta">作りながら見る頁（机の端に置く・試作）の「止まった」の札を、版と手順の番号ごとに数えます（止まった手順）。映像は残していません。</p>{s1}</section>'
            f'<section class="sec" id="k2"><h2>2 動きの結果</h2><p class="meta">版を直す前と後を見比べる材料です。紙で動いても、昔の作り方の証明にはなりません。</p>{s2}</section>'
            f'<section class="sec" id="k3"><h2>3 感想の言葉</h2><p class="meta">感想・メモ・説明・次の思いつきから、言葉で拾います。拾い方は荒いので、読む時に確かめます。</p>{s3}</section>'
            f'<section class="sec" id="k4"><h2>4 聞く口の質問</h2><p class="meta">作っている途中に聞く口へ来た質問を、手順の段ごとに束ねます（同じ文だけを 1 つに数えます）。</p>{s4}</section>'
            f'<section class="sec" id="k5"><h2>5 完成の様子</h2><p class="meta">時間は幅で、動いた記録は件数で出します。</p>{s5}</section>'
            f'<section class="sec" id="k6"><h2>6 サイトの流れ</h2><p class="meta">予想 → 型紙 → 作る → 記録の、どの段まで進んだか。何を書いたかは写していません。</p>{s6}</section>')
    return skin.shell(f'{data["toy"]} の工作の様子', body, look, "", path or f"/loop/{sid}", TABLE_STYLE)
