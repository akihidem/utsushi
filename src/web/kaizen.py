"""改善の輪（本人の方針、2026-11-05 朝）: 「作ったものの感想と動きを報告してもらったら、サイト側もループを回し、型紙の改善をする。
そうすることでより良いおもちゃの型紙を提供できる」。

判断の芯:
- 輪は、報告（記録＋感想）→ 人の説明 → 読み → 寸法を 1 つ変えて次の版 → 次に作る人はその版を刷る、の順。既にある台帳（omochae.loop）を
  画面で見える形にするだけで、別の台帳を作らない。版は data/loop の version-*.json、根拠は記録の ID。
- 「次の版を待つ報告」を数えて出す。説明の無い報告は、先に説明を待つ（J-013: 人の説明が AI より先）。
- 成績に見える数（何件動いた、など）は出さない（J-025）。出すのは「報告の数」「版の数」「変えた寸法」だけ。
- /loop は作る側（サイト側）が輪を回すための一覧。学ぶ人の順路（頭の帯）には入れず、玩具の頁の節と序から行く。
- 受け持ち（本人の決定 11-05、カード 20261105-090458 の (b)）: 雛形そのものを直すための報告の入口と道具（報告の形・検査・集計）は
  エンジン（paper-to-toy）の側。ここが持つのは、学ぶ人の記録と感想、仮説ごとの版（寸法を 1 つ変えた次の版）、その表示まで。
  だから、報告から案を機械で出す道具はここに置かない。
"""
from omochae import hypotheses, loop, records

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
                     + f'。採った人: {esc(v.get("adopted_by", ""))}'
                     + f'。<a href="/toy/{sid}?see={esc(h["id"])}&kind=sheet&v={v["version"]}#win">この版の型紙</a></li>')
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
            f'{lines}{todo}<p class="meta"><a href="/loop">全部の玩具の改善の輪</a></p></section>')


def page(look=skin.DEFAULT, path="/loop"):
    """サイト側が輪を回すための一覧。報告のある玩具から順に、版と次の版を待つ報告を数えて出す。"""
    items, n_rep = [], 0
    for sid in sources():
        recs = records.all_records(sid)
        if not recs:
            continue
        data = hypotheses.load(sid)
        n_rep += len(recs)
        vers = sum(len(versions(sid, h["id"])) for h in data["hypotheses"])
        ready, waiting = pending(sid, recs)
        items.append((len(ready), sid, data["toy"], len(recs), vers, len(waiting)))
    items.sort(key=lambda x: (-x[0], -x[3]))
    rows = "".join(f'<tr><td><a href="/toy/{esc(sid)}#kaizen">{esc(toy)}</a></td><td>{n}</td><td>{v}</td><td>{r}</td><td>{w}</td></tr>'
                   for r, sid, toy, n, v, w in items)
    table = (f'<table><thead><tr><th>玩具</th><th>報告</th><th>報告から直した版</th><th>次の版を待つ報告</th><th>説明を待つ報告</th></tr></thead><tbody>{rows}</tbody></table>'
             if items else '<p class="meta">報告はまだありません。</p>')
    body = (f'<section class="hero"><div><h1>改善の輪</h1><p class="lead">作った人の報告を、型紙の改善に回す所。報告のある玩具 {len(items)} 種、報告 {n_rep} 件。</p>'
            '<p class="meta">輪: 報告（動きと感想）→ 人の説明 → 読み → 寸法を 1 つ変えて次の版 → 次に作る人はその版を刷る。並びは待っている報告の多い順で、玩具の上下ではありません。</p></div></section>'
            f'<section class="sec">{table}</section>')
    return skin.shell("改善の輪", body, look, "", path, "table{border-collapse:collapse;width:100%}th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--rule)}th{font-weight:normal;color:var(--mute);font-size:13px}")
