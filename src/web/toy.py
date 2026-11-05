"""玩具の頁（順路の真ん中: 記録を読む → 予想 → 仮説と型紙の窓 → 作る → 記録 → 試した後の紙 → 人の説明 → AI → 次の版 → 戻る）。
要件は docs/process/site-requirements.md の 2・3・6。見た目は skin.py の骨と皮に任せ、この頁は中身だけを組む。

判断の芯（play_server の前の玩具の頁から引き継いだ線）:
- 予想か自分の仮説の前は、仮説の名前も型紙も出さない（F9.prediction）。
- 仮説は元の記録の順で、順位・推し・点を出さない（J-025）。大きな字は名札で順位ではない。
- 型紙と手順の紙は、刷ると PDF と一緒に PNG と SVG も書き出されている（render.write_all・to_png）。前の頁は PDF のリンクしか出さず、
  画面に絵が出なかった（本人「今は型紙が出力されていない」）。ここでは「型紙の窓」で絵を画面に出し、押すと拡大の窓（CSS の :target、JS なし）。
- 試した後の紙は、その仮説の記録が 1 件でもある時だけ出す。絵も PDF も、記録の前は URL を知っていても渡さない（J-013。門は play_server の /sheet/）。
- 記録は雛形の値で、動かない記録もそのまま並ぶ。成功・失敗・正解の言葉を使わない（philosophy.md）。仮説の文の打ち消し「正解ではありません」だけは本人の決定で出す（#258）。
- 返事の順は 紙 → 人の説明 → AI（J-013 の 11-04 の変更）。AI の釦は人の説明の後にだけ出す。
- 寸法のつまみは置かない。寸法を変えるのは「次の版を作る」（人の説明の後、1 つの寸法、床に落ちたら刷らない）だけ（本線は紙の実物）。
"""
import json
import re

from omochae import hypotheses, loop, making_log, records, ways
from omochae.compose import TEMPLATES
from omochae.hypotheses import ROOT
from omochae.marks import HYPOTHESIS

from . import skin
from .play_server import PARAM_NAMES, esc, out_dir, printed_versions, source, sources
from .toys import way_tags

KINDS = (("", "型紙"), ("_tejun", "手順の紙"), ("_after", "試した後の紙"))


def versions_of(sid, hid, printed_only=False):
    """刷ってある版の番号。版 2 以降は「次の版を作る」で人が採った時にできる。"""
    # printed_only=False の時は、無くても版 1 を入れる（窓の札の並びを空にしないため）。True は「本当に刷ってある版」だけ。
    got = printed_versions(sid, hid)
    return got if printed_only else sorted(set(got) | {1})


def sheet_links(sid, hid, recorded):
    """刷った紙への字のリンク。押すと画面の窓（#win）にその紙の絵が出る。
    なぜ窓へ向けるか: 本人の指示（11-05、デモを見て）「型紙はクリックすると表示されるように」。前は PDF へ直に飛び、機器によっては
    ダウンロードだけになって画面に紙が出なかった。PDF は窓の「PDF を開いて刷る」から（別のタブ、インライン）。試した後の紙は記録の後だけ。"""
    links = []
    for v in versions_of(sid, hid):
        tag = "" if v == 1 else f"版 {v} の"
        for suffix, label in KINDS:
            if (out_dir(sid) / f"{hid}_v{v}{suffix}.pdf").exists() and (suffix != "_after" or recorded):
                links.append(f'<a href="/toy/{sid}?see={hid}&kind={suffix.lstrip("_") or "sheet"}&v={v}#win">{tag}{label}</a>')
    return "・".join(links)


def printed_ids(sid, data):
    # どの版でも刷ってあれば「刷った仮説」。版 1 を決め打ちしない（報告から直した版を次の人が最初に刷るため）。
    return [h["id"] for h in data["hypotheses"] if versions_of(sid, h["id"], printed_only=True)]


def latest_printed(sid, data):
    """窓に最初に出す仮説: 一番新しく刷った物。"""
    cands = [(p.stat().st_mtime, p.name.split("_v")[0]) for p in out_dir(sid).glob("H-*_v*.pdf")] if out_dir(sid).exists() else []
    return max(cands)[1] if cands else None


ZOOM_SIZES = (100, 180, 300)
# 開け閉めは CSS（:target）で足りる。Esc と絵の外で閉じる所だけ小さな JS を使う（L-11）。ここから開いた時は履歴を戻し、見ていた位置に帰す。
ZOOM_SCRIPT = """<script>(()=>{const z=document.getElementById('zoom'),a=document.querySelector('figure.sheet a');if(!z||!a)return;let mine=false;
a.addEventListener('click',()=>{mine=true});
const shut=()=>{if(location.hash!=='#zoom')return;if(mine){mine=false;history.back()}else{location.hash='win'}a.focus({preventScroll:true})};
document.addEventListener('keydown',e=>{if(e.key==='Escape')shut()});
z.addEventListener('click',e=>{if(e.target===z||e.target.classList.contains('pic'))shut()});
z.querySelector('.close').addEventListener('click',e=>{e.preventDefault();shut()});
window.addEventListener('hashchange',()=>{if(location.hash==='#zoom')z.querySelector('.close').focus({preventScroll:true})});})();</script>"""


def window(sid, data, see, kind, v, recorded):
    """型紙の窓（要件の S-01〜S-05）。仮説と紙の種類と版を字の札で選び、絵（PNG）を出す。押すと拡大の窓（#zoom）。"""
    ids = printed_ids(sid, data)
    if not ids:
        return '<p class="meta">仮説の札の「型紙と手順の紙を刷る」を押すと、ここに紙の絵が出ます。</p>'
    see = see if see in ids else (latest_printed(sid, data) or ids[0])
    vs = versions_of(sid, see, printed_only=True)  # 刷ってある版だけ（版 1 を決め打ちすると、無い紙の絵とリンクが出る）
    v = v if v in vs else vs[-1]
    kind = kind if kind in ("", "_tejun", "_after") else ""
    if kind == "_after" and see not in recorded:
        kind = ""
    h = next(x for x in data["hypotheses"] if x["id"] == see)
    name = f"{see}_v{v}{kind}"
    q = lambda hid, k, vv: f"/toy/{sid}?see={hid}&kind={k.lstrip('_') or 'sheet'}&v={vv}#win"
    # 仮説の札（元の順）。順位ではない。
    hyps = "".join((f'<span>仮説 {esc(hypotheses.letter(x))}</span>' if x["id"] not in ids else
                    f'<a href="{q(x["id"], "", versions_of(sid, x["id"], printed_only=True)[-1])}" aria-current="{"true" if x["id"] == see else "false"}">仮説 {esc(hypotheses.letter(x))}</a>')
                   for x in data["hypotheses"])
    kinds = ""
    for suffix, label in KINDS:
        if suffix == "_after" and see not in recorded:
            # 記録の前は名前も出さない（絵も PDF も渡さない線を、字の上でも守る）。
            kinds += '<span title="記録を残すと開きます">試した後の紙（記録の後）</span>'
        elif (out_dir(sid) / f"{see}_v{v}{suffix}.png").exists():
            kinds += f'<a href="{q(see, suffix, v)}" aria-current="{"true" if suffix == kind else "false"}">{label}</a>'
    vers = "".join(f"<b>版 {n}</b>" if n == v else f'<a href="{q(see, kind, n)}">版 {n}</a>' for n in vs)
    cap = ""
    if v > 1:
        _, adopted = loop.version_params(sid, see, v)
        if adopted:
            ch = "、".join(f"{PARAM_NAMES.get(c['param'], c['param'])} {c['from']}→{c['to']}" for c in adopted.get("changes", []))
            cap = f'<p class="meta">版 {v}: 根拠 {esc("、".join(adopted.get("record_ids", [])))}。変えた所: {esc(ch)}</p>'
    # 版の記録があって紙が無い版は札に出ないので、刷り直す釦を添える（#158）。
    cap += "".join(f'<form method="post" action="/toy/{sid}/reprint" class="inline"><input type="hidden" name="hypothesis" value="{esc(see)}"><input type="hidden" name="version" value="{n}"><button class="quiet">版 {n} の紙を刷り直す</button></form>'
                   for n in loop.adopted_versions(sid, see) if n not in vs)
    png = f"/sheet/{sid}/{name}.png"
    pdf = f"/sheet/{sid}/{name}.pdf"
    # 窓の絵は軽い PNG、拡大は目盛りと字がにじまない SVG（S-01）。SVG の無い古い紙は PNG に戻る。
    big = f"/sheet/{sid}/{name}.svg" if (out_dir(sid) / f"{name}.svg").exists() else png
    sizes = "".join(f'<input type="radio" name="zoom-size" id="zs{n}"{" checked" if n == 180 else ""}>' for n in ZOOM_SIZES)
    labels = "".join(f'<label for="zs{n}">{n}%</label>' for n in ZOOM_SIZES)
    fig = (f'<figure class="sheet"><a href="#zoom" aria-label="拡大して見る"><img src="{png}" alt="{esc(data["toy"])} 仮説 {esc(hypotheses.letter(h))} の{esc(dict(KINDS)[kind])}"></a></figure>'
           f'<div class="zoom" id="zoom">{sizes}<div class="bar" role="group" aria-label="大きさ">{labels}</div><a class="close" href="#win">閉じる</a><div class="pic"><img src="{big}" alt="" loading="lazy"></div></div>'
           + ZOOM_SCRIPT)
    side = (f'<div class="side"><h3>仮説 {esc(hypotheses.letter(h))}「{esc(h["name"])}」の{esc(dict(KINDS)[kind])}</h3>'
            f'<div class="v">{vers}</div>{cap}'
            # PDF は別のタブで開く（インラインの印は play_server の /sheet/ が付ける）。同じタブで開くと窓から離れ、機器によっては落とすだけになる。
            f'<p><a class="btn" href="{pdf}" target="_blank" rel="noopener">PDF を開いて刷る</a></p>'
            '<p class="meta">100% で刷り、紙の物差しが 10cm か確かめます。A4 の紙 1 枚。</p>'
            f'<p class="meta"><a href="/sheet/{sid}/{name}.svg" target="_blank" rel="noopener">線の絵（SVG）</a>・絵を押すと大きく見られます。</p>'
            f'<p class="meta">{esc(HYPOTHESIS)}</p></div>')
    return f'<div class="tabs">{hyps}</div><div class="tabs">{kinds}</div><div class="win">{fig}{side}</div>'


def sample_records(data):
    """その玩具の見本の記録（デモ用の作り物。札つき）。本物の記録の後ろに置き、混ぜない。"""
    from . import demo_samples

    return demo_samples.uploads_for(data["toy"])


def analogy_section(data):
    """たとえと、関連する事柄（本人の頼み 11-05「扇を開くのような、身近な物へのたとえと関連する事柄を全部の玩具に」）。
    文は作る側の言葉なので印を付け、答えではない事を書く（J-016 の線）。仕組みの手がかりになるので予想の後にだけ出す（F9.prediction）。
    欄の形は data/hypotheses の `analogy`（like・related・written_by）。試験は tests/test_analogy.py。"""
    a = data.get("analogy")
    if not a:
        return ""
    rel = "".join(f"<li>{esc(x)}</li>" for x in a.get("related", []))
    return (f'<section class="sec" id="tatoe"><h2>たとえと、関連する事柄</h2>'
            f'<p class="meta"><span class="lb">作る側のたとえ</span>{esc(a.get("written_by", ""))}。たとえは仕組みを考える手がかりで、答えではありません。</p>'
            f'<article class="card"><h3>身近な物でいうと</h3><p>{esc(a["like"])}</p></article>'
            f'<article class="card"><h3>関連する事柄</h3><ul>{rel}</ul></article></section>')


def ask_form(sid, data, asked=None):
    """作っている最中の手順の質問の口（本人の決定 11-04、src/api/ask.py）。刷った紙がある仮説だけを選べる。聞かれた時だけ答える。"""
    printed = [h for h in data["hypotheses"] if versions_of(sid, h["id"], printed_only=True)]
    if not printed:
        return ""
    opts = "".join(f'<option value="{esc(h["id"])}">仮説 {esc(hypotheses.letter(h))} の紙</option>' for h in printed)
    shown = ""
    if asked:
        q, a = asked
        shown = f'<div id="ask-answer" class="notice"><p class="meta">聞いた事: {esc(q)}</p><p>{esc(a)}</p></div>'
    return (f'<form method="post" action="/toy/{sid}/ask" id="ask" class="card"><h3>作っている途中で困ったら</h3>'
            '<p class="meta">切る・折る・貼る・組む順の疑問に答えます（例: 谷折りって？）。どう動くか・仕組みは、試して確かめる所なので答えません。</p>'
            f'<label>どの紙か<select name="hypothesis">{opts}</select></label><label>聞きたい事<input type="text" name="question" required maxlength="300"></label>'
            # 断り（本人の決定 11-05「工作の様子を蓄積してサービス全体の改善に回す。個人の情報は落とす」）: 質問の文を残すので、残す事と、
            # 名前を書かないでほしい事を、聞く口のすぐ下に出す。床が落とせるのは連絡先の形だけで、名前は機械では落とせないため。
            f'<button>聞く</button><p class="meta">{esc(making_log.ASK_NOTICE)}{esc(making_log.ASK_NAME_TEXT)}</p>{shown}</form>')


def record_form(sid, data, own):
    template = data.get("template", "slider_fan")
    hyps = [(h["id"], f'仮説 {hypotheses.letter(h)}「{h["name"]}」') for h in data["hypotheses"]] + [(h["id"], f'あなたの仮説「{h["name"]}」') for h in own]
    opts = "".join(f'<option value="{esc(i)}">{esc(n)}</option>' for i, n in hyps)
    # 版が 2 つ以上ある時だけ、どの版の紙かを聞く（紙の題の横に刷ってある）。報告が版を取り違えないため（play_server.sheet_version_of）。
    seen = sorted({n for h in data["hypotheses"] for n in versions_of(sid, h["id"], printed_only=True)})
    version_field = ('<label>どの版の紙か（紙の題の横に刷ってあります）<select name="sheet_version"><option value="">いちばん新しい版</option>'
                     + "".join(f'<option value="{n}">版 {n}</option>' for n in seen) + '</select></label>') if len(seen) > 1 else ""
    from .techo_site import ICONS

    results = "".join(f'<label class="tile"><input type="radio" name="result" value="{esc(r)}" required>{ICONS.get(r, ICONS["わからない"])}{esc(r)}</label>'
                      for r in TEMPLATES[template].RESULTS)
    if template == "pivot_counterweight":
        extra = '<label>動かした物<select name="power"><option value="">—</option><option>手</option><option>息</option><option>団扇</option><option>風</option></select></label>'
    elif template == "slider_fan":
        # 角度の欄は外した（本人の方針「開き具合の角度などは今回の課題ではない」、U-25）。受け口は古い記録のために残す。
        extra = '<label>開いた力<select name="opener"><option value="">—</option><option>紙の力</option><option>糸</option><option>手</option></select></label>'
    else:
        extra = getattr(TEMPLATES[template], "RECORD_EXTRA", "")
    return (f'<form method="post" action="/toy/{sid}/record" class="card" id="record"><h3>試した記録</h3><p class="meta">見た事を残します。動かなかった記録も、そのまま紙の返事です。記録はこの頁でほかの人も読むので、名前や連絡先は書かないでください。</p>'
            f'<label>どの仮説の紙か<select name="hypothesis">{opts}</select></label>{version_field}<fieldset style="border:0;padding:0;margin:14px 0 0"><legend class="meta">見た事</legend><div class="tiles">{results}</div></fieldset>{extra}'
            # 感想の欄（本人の方針 11-05「作ったものの感想と動きを報告してもらう」）。動きは上の札、感想は自由な文。空でもよい。
            '<label>作ってみてどうだったか（感想。動いた所、難しかった所、思った事）<textarea name="impression"></textarea></label>'
            '<label>最初に動いたのはどこか<input type="text" name="first_moved"></label><label>引っかかった所<input type="text" name="stuck"></label>'
            '<label>何を変えると違いが出そうか<input type="text" name="what_if"></label><label>作っている途中で思いついた事<input type="text" name="idea"></label>'
            '<label>メモ<textarea name="note"></textarea></label>'
            '<button>記録を残す</button></form>')


def _param_label(template, k):
    return PARAM_NAMES.get(k, getattr(TEMPLATES[template], "PARAM_NAMES", {}).get(k, k))


def _params_now(sid, hid, template):
    """次の版の元になる寸法（今の版の値に、雛形の既定を足した物）。loop.check_proposal が比べる元と同じ。"""
    try:
        params, _ = loop.version_params(sid, hid, loop.latest_version(sid, hid))
    except ValueError:  # 自分の仮説のように、版を持たない物
        params = None
    return {**TEMPLATES[template].DEFAULTS, **(params or {})}


def _param_option(template, k, now):
    """選ぶ項目の字。JS を使わず、今の値と変えてよい幅を項目そのものに並べる（#129）。"""
    label, value, span = _param_label(template, k), now.get(k), getattr(TEMPLATES[template], "RANGES", {}).get(k)
    if isinstance(value, (int, float)):
        label += f": 今 {value:g}"
        if span:
            label += f"（{span[0]:g}〜{span[1]:g}）"
    return f'<option value="{esc(k)}">{esc(label)}</option>'


# 床に落ちた理由を、学ぶ人の言葉にする（#129）。検査の言葉と座標は作る側の物で、次に何を入れるかの手がかりにならない。
NEXT_REASONS = {
    "F5.print_area": "この値だと、紙が A4 からはみ出します。",
    "F5.overlap": "この値だと、紙の上で部品どうしが重なります。",
    "F5.text_overlap": "この値だと、紙の上で字が重なります。",
    "F5.image_box": "この値だと、絵が部品からはみ出します。",
    "F5.fan_height": "この値だと、畳んだ扇が筒に隠れません。",
    "F5.fan_clearance": "この値だと、扇が筒の口の角に当たって開ききりません。",
    "F5.fan_length": "この値だと、扇の長さが折りの数と幅に合いません。",
    "F5.fan_thickness": "この値だと、畳んだ扇が内筒に入りません。",
    "F5.slide_clearance": "この値だと、内筒が外筒の中で動きません。",
    "F5.figure_height": "この値だと、像が扇より高くなります。",
    "F5.base_size": "この値だと、扇の台が内筒に入りません。",
    "F5.stroke": "この値だと、押し上げる動きが筒の中に収まりません。",
}


def next_reasons(failures, sid, hid, param):
    """「次の版を作る」が通らなかった時に出す文。理由のあとに、今の値と次の一手を 1 行足す。"""
    template = hypotheses.load(sid).get("template", "slider_fan")
    now = _params_now(sid, hid, template)
    label, value = _param_label(template, param), now.get(param)
    value = f"{value:g}" if isinstance(value, (int, float)) else ""
    span = getattr(TEMPLATES[template], "RANGES", {}).get(param)
    out, on_paper = [], False
    for f in failures:
        if f.floor == "F5.range" and f.where == param and span:
            text = f"{label}は {span[0]:g}〜{span[1]:g} の間で書いてください" + (f"（今 {value}）。" if value else "。")
        elif f.floor.startswith("F5."):
            # ほかの雛形の床は文がそれぞれ読めるので、座標の組だけを外す。
            text, on_paper = NEXT_REASONS.get(f.floor) or re.sub(r"\s*\([-\d., ]+\)", "", f.message), True
        else:
            text = f.message
        if text not in out:
            out.append(text)
    if on_paper and value:
        out.append(f"{label}は今 {value} です。近い値を試すか、別の寸法を変えてください。")
    return out


def next_form(r, back=""):
    """次の版を作る口（本人の問いの (7)、11-04）。人の説明が先にある記録にだけ出す（J-013）。
    人が解釈を書いて確定し、変える寸法を 1 つ選んで採ると、台帳の床（F4・F7・F8・F9）を通った時だけ次の版を刷る。"""
    from omochae.metrics import ALLOWED

    template = hypotheses.load(r["source_id"]).get("template", "slider_fan")
    now = _params_now(r["source_id"], r["hypothesis_id"], template)
    opts = "".join(_param_option(template, k, now) for k in sorted(ALLOWED[template]))
    # 解釈はすぐ上の説明とほぼ同じ問いなので、説明を初めから入れておく（#129）。そのまま採っても、書き直してもよい。
    told = (loop.explanation(r["id"]) or {}).get("text", "")
    hidden = f'<input type="hidden" name="back" value="{esc(back)}">' if back else ""
    return (f'<details><summary>次の版を作る（寸法を 1 つ変える）</summary><form method="post" action="/record/{esc(r["id"])}/next">{hidden}'
            f'<label>何が起きたと読むか（解釈）<textarea name="interpretation" required>{esc(told)}</textarea></label>'
            f'<label>変える寸法<select name="param">{opts}</select></label><p class="meta">かっこの中は変えてよい幅です。紙に組める値は、この幅より狭い事があります。</p>'
            '<label>新しい値<input type="text" name="to" inputmode="decimal" required></label>'
            '<label>変える理由<input type="text" name="why" required></label><label>採った人<input type="text" name="by" required></label>'
            '<button>次の版を刷る</button></form></details>')


def ai_block(r):
    """人の説明の後に出す AI の返事（J-013 の順の最後）。読みと観察は案で、採点しない。鍵が無い時は play_server がその旨を返す。"""
    from api import observe

    rid = esc(r["id"])
    out = ""
    i = loop.interpretation(r["id"])
    if i and isinstance(i.get("content"), dict):
        c = i["content"]
        lines = "".join(f"<li>{esc(x)}</li>" for x in c.get("observed", []))
        lines += "".join(f'<li>{esc(x.get("text", ""))}（確からしさ: {esc(x.get("confidence", ""))}）</li>' for x in c.get("causes", []) if isinstance(x, dict))
        lines += "".join(f"<li>分からない事: {esc(x)}</li>" for x in c.get("unknown", []))
        out += f'<div class="item"><p class="meta">Claude の読み（案）</p><ul>{lines}</ul></div>'
    o = observe.observation(r["id"])
    if o:
        lines = "".join(f"<li>{esc(x)}</li>" for x in o.get("observed", [])) + "".join(f"<li>見えなかった事: {esc(x)}</li>" for x in o.get("unclear", []))
        out += f'<div class="item"><p class="meta">観察（Claude の補助）</p><ul>{lines}</ul></div>'
    from . import techo_site

    can_ask, can_watch, why = techo_site.ai_offer(r["id"])
    buttons = (f'<form method="post" action="/record/{rid}/ai-interpret" class="inline"><button class="quiet">Claude に聞く（何が起きたか）</button></form>' if can_ask else "") + (
               f'<form method="post" action="/record/{rid}/ai-observe" class="inline"><button class="quiet">動画を見てもらう</button></form>' if can_watch else "")
    return out + (f'<div class="row">{buttons}</div>' if buttons else "") + (f'<p class="meta">{why}</p>' if why else "")


def records_list(sid, recs):
    from . import zukan

    data = hypotheses.load(sid)
    out = "<h2>これまでの記録</h2><p class='meta'>記録の順。紙の返事 → 自分の説明 → AI の返事、の順で開きます。</p>" if recs else ""
    for r in reversed(recs):
        told = loop.explanation(r["id"])
        deg = f'・{r["opened_deg"]:g}°' if r.get("opened_deg") is not None else ""
        # 試した後の紙も字のリンクは窓へ（画面に出す）。PDF は添え。
        hid, ver = esc(r["hypothesis_id"]), r.get("sheet_version", 1)
        after = (f'<p><a href="/toy/{sid}?see={hid}&kind=after&v={ver}#win">試した後の紙</a>（先に開いて、次に変える条件を読む。'
                 f'<a href="/sheet/{sid}/{hid}_v{ver}_after.pdf" target="_blank" rel="noopener">PDF</a>）</p>')
        if told:
            # 紙の返事 → 自分の説明 → AI → 次の版 の順を、罫で見分ける（#130）。
            tail = (f'<div class="step"><p>説明: {esc(told["text"])}</p><p>次の思いつき: {esc(told["next_idea"])}</p></div>'
                    f'<div class="step">{ai_block(r)}</div><div class="step">{next_form(r)}</div>')
        else:
            # 人の説明が先。Claude の釦はこの後の段で出す。
            tail = (f'<form method="post" action="/record/{esc(r["id"])}/explain"><label>何が起きたと思いますか（わからない、でもよい）<textarea name="text" required></textarea></label>'
                    '<label>次に試したい事<input type="text" name="next_idea" required></label><label>書いた人<input type="text" name="by" required></label><button>説明を残す</button></form>')
        # 感想（本人の方針 11-05「感想と動きの報告」）。動きの欄の次に、作った人の言葉として出す。
        feel = f'<p>感想: {esc(r["impression"])}</p>' if r.get("impression") else ""
        # 作った物の写真と動画、止まった所の答えも同じ札に出す（本人の指摘 11-05: 制作した記録を玩具の頁で見る）。
        ans = r.get("answers") or {}
        # 書いた欄だけを読める字で出す。書いていない欄の名前は並べない（#130）。
        written = [("最初に動いた所", ans.get("first_moved")), ("引っかかった所", ans.get("stuck")), ("変えると違いが出そうな所", ans.get("what_if")),
                   ("思いついた事", "、".join(str(x) for x in r.get("ideas") or [])), ("メモ", r.get("note"))]
        feel += "".join(f"<p>{label}: {esc(text)}</p>" for label, text in written if text)
        feel = media_html(r["id"]) + feel
        out += f'<article class="card" id="{esc(r["id"])}"><h3>{esc(zukan.record_title(r, data))}{esc(deg)}</h3><p class="meta">{esc(zukan.record_date(r))}・版 {esc(ver)}・{esc(r["id"])}</p>{feel}{after}{tail}</article>'
    return out


def observations(sid, data, link=False):
    """記録を読む（順路の 2 段目）。文には印を付ける（J-016 の線。zukan と同じ作り）。"""
    from . import zukan

    lines = zukan.observation_lines(sid, data)
    if not lines:
        return '<p class="meta"><span class="lb">観察</span>試した記録はまだありません。最初の記録を残す人になります。</p>'
    # 予想の後は、行から同じ頁の記録の札（写真・感想・説明）へ飛べる。予想の前は札が頁に無いので字だけ。
    text = lambda x: f'<a href="#{esc(x["record_id"])}">{esc(x["text"])}</a>' if link and x.get("record_id") else esc(x["text"])
    return "<ul class='meta' style='list-style:none;padding:0'>" + "".join(f'<li><span class="lb">{esc(x["label"])}</span>{text(x)}</li>' for x in lines) + "</ul>"


def media_html(rid, cls="shots"):
    """記録に添えた写真と動画（手帖の「上げる」で添えた物）。ギャラリーと同じ道（/record/<記録>/media/）から出す。"""
    from .techo_site import media_of

    files = media_of(rid)
    if not files:
        return ""
    pics = "".join((f'<video src="/record/{esc(rid)}/media/{esc(f)}" controls muted playsinline preload="metadata"></video>' if f.endswith(("mp4", "mov"))
                    else f'<img src="/record/{esc(rid)}/media/{esc(f)}" alt="作った物の写真" loading="lazy">') for f in files)
    return f'<div class="{cls}">{pics}</div>'


def made_strip(sid, recs, shown):
    """玩具の頁の頭に出す「作った記録」の帯（本人の指摘 11-05「制作した記録とおもちゃのページが関連してない。同じページで見れると良い」）。
    予想の後は、写真の小さな並びから同じ頁の記録の札へ飛ぶ。予想の前は写真も感想も出さず、在る事だけを知らせる（予想が先、F9。
    作った物の写真は動かし方の手がかりになるため、仮説と同じ扱いにする）。"""
    if not recs:
        return ""
    if not shown:
        return f'<p class="meta">作った記録が {len(recs)} 件あります。写真と感想は、予想を書くとこの頁で見られます。</p>'
    from .techo_site import media_of

    thumbs = ""
    for r in reversed(recs):
        for f in media_of(r["id"])[:1]:
            tag = (f'<video src="/record/{esc(r["id"])}/media/{esc(f)}" muted playsinline preload="metadata"></video>' if f.endswith(("mp4", "mov"))
                   else f'<img src="/record/{esc(r["id"])}/media/{esc(f)}" alt="作った物の写真" loading="lazy">')
            thumbs += f'<a href="#{esc(r["id"])}" aria-label="{esc(r["id"])} の記録へ">{tag}</a>'
    return (f'<div class="strip">{thumbs}</div>' if thumbs else "") + '<p class="meta"><a href="#kiroku">作った記録を見る（写真・感想・説明）</a></p>'


def neighbours(sid):
    ss = sources()
    i = ss.index(sid)
    prev_, next_ = ss[i - 1] if i > 0 else None, ss[i + 1] if i + 1 < len(ss) else None
    out = []
    if prev_:
        out.append(f'<a href="/toy/{prev_}">← {esc(hypotheses.load(prev_)["toy"])}</a>')
    out += ['<a href="/toys">おもちゃの一覧</a>', '<a href="/gallery">上げた物と職人の言葉</a>', '<a href="/">入口へ</a>']
    if next_:
        out.append(f'<a href="/toy/{next_}">{esc(hypotheses.load(next_)["toy"])} →</a>')
    return '<p class="links">' + "".join(out) + "</p>"


def toy_page(sid, look=skin.DEFAULT, errors=(), msg="", asked=None, see=None, kind="", v=0, path=None):
    data, src = hypotheses.load(sid), source(sid)
    path = path or f"/toy/{sid}"
    note = "".join(f'<p id="msg">{esc(e)}</p>' for e in errors) + (f'<p id="msg">{esc(msg)}</p>' if msg else "")
    has_pic = (ROOT / "out/sources" / f"{sid}.jpg").exists()
    nopic = "" if has_pic else f'<p class="meta"><a href="{esc(src["image_url"])}">図を見る（国立国会図書館）</a></p>'
    songs = "".join(f'<p>{esc(e["text"])}</p>' for e in src.get("transcription", {}).get("entries", []) if not e.get("rejected_by") and e.get("checked_by"))
    who = "・".join(sorted({e["checked_by"] for e in src.get("transcription", {}).get("entries", []) if not e.get("rejected_by") and e.get("checked_by")}))
    shown = not hypotheses.need_prediction(sid)  # 予想の後だけ、作った記録の写真と感想を頭の帯に出す
    stage = hypotheses.stage(sid)
    stage_note = '<p class="meta"><span class="lb">試作</span>全部の玩具を型紙にする途中の物。名前は作る側の見立てで、まだ確かめていません。</p>' if stage != "必須" else ""
    hero = (f'<section class="hero">{skin.frame(sid, src.get("holding", ""))}<div>'
            f'<h1>{esc(data["toy"])}</h1>{stage_note}'
            + (f'<div class="songs">{songs}</div><p class="meta">原文の引用。確かめた人: {esc(who)}</p>' if songs else "")
            + skin.artwork_label(data["toy"], src) + nopic
            + f'<p class="links"><a href="/zukan/{sid}">図鑑の頁</a><a href="/zukan/{sid}/yomi">くずし字を読む</a><a href="/toys">ほかのおもちゃ</a></p>'
            f'<h3 style="margin-top:24px">これまでの記録</h3>{observations(sid, data, link=shown)}{made_strip(sid, records.all_records(sid), shown)}</div></section>')
    preds = hypotheses.predictions(sid)
    latest = json.loads(preds[-1].read_text(encoding="utf-8"))["text"] if preds else None
    form_pred = (f'<form method="post" action="/toy/{sid}/predict" class="card"><h3>予想</h3><label>どう動くと思いますか（先に書きます）<textarea name="text" required></textarea></label>'
                 '<button>予想を残す</button></form>')
    form_own = (f'<form method="post" action="/toy/{sid}/own" class="card"><h3>自分の仮説を立てる</h3><label>名前<input type="text" name="name" required></label>'
                f'<label>動かし方<textarea name="how" required></textarea></label><label>図のどこを見たか<input type="text" name="evidence" required></label><button>仮説を残す</button></form>')
    if hypotheses.need_prediction(sid):
        # 予想の前は仮説を見せない。答えを先に見せないため（F9.prediction）。
        # かざして選ぶ（試作、本人の案 11-05）: 文字で書く代わりに、内カメラの映像に絵を重ねて札で選ぶ道。本人が見て決めるための入口を 1 つだけ置く。
        kazasu_link = f'<p><a class="btn quiet" href="/toy/{sid}/kazasu">かざして選ぶ（試作）</a></p>'
        body = hero + f'<section class="sec" id="yosou">{note}<h2>先に、予想を書く</h2><p class="lead">図を見て、どこがどう動くと思うかを書きます。書くと仮説と型紙が開きます。仮説を自分で立てる道もあります。</p>{kazasu_link}{form_pred}{form_own}</section>' + neighbours(sid)
        return skin.shell(data["toy"], body, look, "", path)
    recs = records.all_records(sid)
    recorded = {r["hypothesis_id"] for r in recs}
    own = hypotheses.own_hypotheses(sid)
    body = hero + f'<section class="sec" id="yosou">{note}<h2>予想</h2>'
    # 予想の後は札を主にし、欄は畳む（JS なし）。大きな欄が残ると、次の段の仮説が画面の下へ押される（#120）。
    body += (f'<article class="card"><h3>あなたの予想</h3><p>{esc(latest)}</p></article><details><summary>予想を書き足す</summary>{form_pred}</details>' if latest else form_pred)
    for h in own:
        # 寸法の無い自分の仮説には、型紙なしの紙（身の回りの紙と紐で作る紙）を返す。本人の決定。
        free = f'{h["id"]}_v1_free.pdf'
        link = f'<a href="/sheet/{sid}/{free}">型紙なしの紙</a>' if (out_dir(sid) / free).exists() else ""
        body += (f'<article class="card" id="own-{esc(h["id"])}"><h3>あなたの仮説 {esc(h["id"])} {esc(h["name"])}</h3><p>{esc(h["how_it_moves"])}</p><p class="meta">根拠: {esc(h["evidence"])}</p>'
                 f'<form method="post" action="/toy/{sid}/print-own"><input type="hidden" name="id" value="{esc(h["id"])}"><button class="quiet">紙を刷る</button></form><p>{link}</p></article>')
    body += f'<details><summary>自分の仮説を立てる</summary>{form_own}</details></section>'
    body += f'<section class="sec" id="kasetsu"><h2>仮説</h2><p class="meta">{esc(data["note"])}</p><p class="meta">{esc(ways.NOTE)}</p><div class="plates">'
    # 並びは記録の順位でなく、元の記録の並び。順位は学ぶ人の画面に出さない（J-013）。
    for h in data["hypotheses"]:
        ev = "".join(f'<li>〔{esc(e["certainty"])}〕{esc(e["what"])}（{esc(e["where"])}）</li>' for e in h["evidence"])
        printed = sheet_links(sid, h["id"], h["id"] in recorded)
        last = versions_of(sid, h["id"], printed_only=True)
        thumb = (f'<a class="thumb" href="/toy/{sid}?see={h["id"]}&kind=sheet&v={last[-1]}#win"><img src="/sheet/{sid}/{h["id"]}_v{last[-1]}.png" alt="" loading="lazy"></a>'
                 if last and (out_dir(sid) / f"{h['id']}_v{last[-1]}.png").exists() else "")
        body += (f'<div class="plate"><div class="letter">{esc(hypotheses.letter(h))}</div><h3>仮説 {esc(hypotheses.letter(h))}「{esc(h["name"])}」</h3><p>{esc(h["how_it_moves"])}</p><ul>{ev}</ul>'
                 f'<p class="meta">試して見る事: {esc(h["to_measure"])}</p>{way_tags(ways.labels(ways.of_hypothesis(data, h)))}{thumb}<div class="acts">'
                 f'<form method="post" action="/toy/{sid}/print"><input type="hidden" name="hypothesis" value="{esc(h["id"])}"><button class="quiet">型紙と手順の紙を刷る</button></form>'
                 f'<p class="meta">{printed}</p></div></div>')
    body += "</div></section>"
    body += analogy_section(data)
    body += f'<section class="sec" id="win"><h2>型紙の窓</h2><p class="meta">画面で見て、刷る前に案を検討する所。並びは仮説の順で、上下はありません。</p>{window(sid, data, see, kind, v, recorded)}</section>'
    body += (f'<section class="sec" id="tsukuru"><h2>作る</h2><p class="lead">刷った紙を切って、折って、組みます。机に置いた手帖で、声で手順を聞き、写真と動画を記録に添えられます。</p>'
             f'<p><a class="btn" href="/toy/{sid}/techo">手帖をひらく（作りながら聞く・上げる）</a>'
             # 作りながら見る（観察 A の試作。本人の案 11-05「端末を机の端に置いて…作成の様子を見れるようにする」）。刷った紙がある時だけ出す。
             + (f' <a class="btn quiet" href="/toy/{sid}/tsukuru">作りながら見る（机の端に置く・試作）</a>' if printed_ids(sid, data) else "")
             + f'</p>{ask_form(sid, data, asked)}</section>')
    body += f'<section class="sec" id="kiroku"><h2>記録と返事</h2>{record_form(sid, data, own)}{records_list(sid, recs)}{sample_records(data)}</section>'
    # 改善の輪（本人の方針 11-05）: 報告から直した版と、次の版を待つ報告。
    from . import kaizen

    body += kaizen.section(sid, data, recs)
    body += f'<section class="sec">{neighbours(sid)}</section>'
    return skin.shell(data["toy"], body, look, "", path)
