"""玩具の頁（順路の真ん中: 記録を読む → 仮説と型紙の窓 → 作る → 記録 → 試した後の紙 → 人の説明 → AI → 次の版 → 戻る）。
要件は docs/process/site-requirements.md の 2・3・6。見た目は skin.py の骨と皮に任せ、この頁は中身だけを組む。

判断の芯（play_server の前の玩具の頁から引き継いだ線）:
- 開いたらすぐ作れる（本人の決定 11-05、#242）。型紙は正解でなく AI が考えた仮説である事を、作る節の頭に出す（本人の言葉 11-05）。
- 仮説は元の記録の順で、順位・推し・点を出さない（J-025）。大きな字は名札で順位ではない。
- 型紙と手順の紙は、刷ると PDF と一緒に PNG と SVG も書き出されている（render.write_all・to_png）。前の頁は PDF のリンクしか出さず、
  画面に絵が出なかった（本人「今は型紙が出力されていない」）。ここでは「型紙の窓」で絵を画面に出し、押すと拡大の窓（CSS の :target、JS なし）。
- 試した後の紙は、その仮説の記録が 1 件でもある時だけ出す。絵も PDF も、記録の前は URL を知っていても渡さない（J-013。門は play_server の /sheet/）。
- 記録は雛形の値で、動かない記録もそのまま並ぶ。成功・失敗・正解の言葉を使わない（philosophy.md）。仮説の文の打ち消し「正解ではありません」だけは本人の決定で出す（#258）。
- 返事の順は 紙 → 人の説明 → AI（J-013 の 11-04 の変更）。AI の釦は人の説明の後にだけ出す。
- 寸法のつまみは置かない。寸法を変えるのは「次の版を作る」（人の説明の後、1 つの寸法、床に落ちたら刷らない）だけ（本線は紙の実物）。
"""
import html
import json
import re

from omochae import hypotheses, loop, making_log, records, ways
from omochae.compose import TEMPLATES
from omochae.hypotheses import ROOT
from omochae.marks import HYPOTHESIS, PREMISE_PAGE

from . import skin, wording
from .play_server import PARAM_NAMES, esc, out_dir, printed_versions, source, sources
from .toys import way_tags

KINDS = (("", "型紙"), ("_tejun", "手順の紙"), ("_after", "試した後の紙"))


def reply_note(errors, msg):
    """返事の文（#121）。理由がいくつあっても 1 つの箱に入れ、id を重ねない。理由は読み上げの割り込み、返事はその場の知らせ。"""
    if errors:
        return f'<div role="alert"><p id="msg">{"<br>".join(esc(e) for e in errors)}</p></div>'
    return f'<div role="status"><p id="msg">{esc(msg)}</p></div>' if msg else ""


def refill(form, values):
    """通らなかった時に、書いた中身を欄に戻す（#121）。欄を作る関数ごとに引数を足さず、できた欄へ入れる。雛形ごとの欄（RECORD_EXTRA）にも同じに効く。"""
    if not values:
        return form

    def text(m):
        v = values.get(m.group(1))
        return m.group(0) if v is None else f'{m.group(0)[:-1]} value="{esc(v)}">'

    def radio(m):
        return m.group(0) + " checked" if values.get(m.group(1)) == html.unescape(m.group(2)) else m.group(0)

    def area(m):
        v = values.get(m.group(1))
        return m.group(0) if v is None else f'<textarea name="{m.group(1)}"{m.group(2)}>{esc(v)}</textarea>'

    def select(m):
        want = values.get(m.group(1))

        def option(o):
            value = o.group(1) if o.group(1) is not None else o.group(2)
            return o.group(0).replace(">", " selected>", 1) if want == html.unescape(value) else o.group(0)

        return re.sub(r'<option(?: value="([^"]*)")?>([^<]*)</option>', option, m.group(0))

    form = re.sub(r'<input type="(?:text|number)"(?: step="any")? name="([^"]+)"[^>]*>', text, form)
    form = re.sub(r'<input type="radio" name="([^"]+)" value="([^"]*)"', radio, form)
    form = re.sub(r'<textarea name="([^"]+)"([^>]*)>[^<]*</textarea>', area, form)
    return re.sub(r'<select name="([^"]+)">.*?</select>', select, form, flags=re.S)


def versions_of(sid, hid, printed_only=False):
    """刷ってある版の番号。版 2 以降は「次の版を作る」で人が採った時にできる。"""
    # printed_only=False の時は、無くても版 1 を入れる（窓の札の並びを空にしないため）。True は「本当に刷ってある版」だけ。
    got = printed_versions(sid, hid)
    return got if printed_only else sorted(set(got) | {1})


def printed_ids(sid, data, recorded=()):
    # どの版でも刷ってあれば「刷った仮説」。版 1 を決め打ちしない（報告から直した版を次の人が最初に刷るため）。
    # 頁に出す型紙はたたき台の 1 枚だけ（J-032）。ほかの仮説は作る側の控えで、札にも欄にも出さない。
    # 窓で開けるのはたたき台と、記録を残した前の紙だけ（前の記録と、それで刷った紙を読める形で残す）。
    sheet = hypotheses.sheet_of(sid)["id"]
    return [h["id"] for h in data["hypotheses"] if (h["id"] == sheet or h["id"] in recorded) and versions_of(sid, h["id"], printed_only=True)]


ZOOM_SIZES = (100, 180, 300)
# 開け閉めは CSS（:target）で足りる。Esc と絵の外で閉じる所だけ小さな JS を使う（L-11）。ここから開いた時は履歴を戻し、見ていた位置に帰す。
ZOOM_SCRIPT = """<script>(()=>{const z=document.getElementById('zoom'),a=document.querySelector('figure.sheet a');if(!z||!a)return;let mine=false;
a.addEventListener('click',()=>{mine=true});
const shut=()=>{if(location.hash!=='#zoom')return;if(mine){mine=false;history.back()}else{location.hash='win'}a.focus({preventScroll:true})};
document.addEventListener('keydown',e=>{if(e.key==='Escape')shut()});
z.addEventListener('click',e=>{if(e.target===z||e.target.classList.contains('pic'))shut()});
z.querySelector('.close').addEventListener('click',e=>{e.preventDefault();shut()});
window.addEventListener('hashchange',()=>{if(location.hash==='#zoom')z.querySelector('.close').focus({preventScroll:true})});})();</script>"""


# 印刷で止まった時の案内（#297）。頁の字は本人が確かめるので、表が空の間は何も出さない。玩具にも仮説にもよらない文だけを置く。
# 文は本人が採った文（11-05）。一字も変えない。実機の確かめはまだ（iPhone・iPad・パソコンの印刷の画面、コンビニの印刷機）
PRINT_HELP_SUMMARY = "印刷できない時は"
PRINT_HELP = (  # （見出し, 文）の組
    ("大きさを 100% にするには", "印刷の画面で、倍率を 100% にします。「用紙に合わせる」を外すと、大きさがそのままになります。画面の言葉は、機械によってちがいます。"),
    ("物差しが 10cm でない時は", "倍率が 100% になっているか、もう一度見ます。直したら、印刷し直します。それでも 10cm にならない時は、そのまま作ってもだいじょうぶです。"),
    ("プリンタが無い時は", "学校の先生や家の人に、印刷をたのみましょう。コンビニの印刷機で印刷できる事もあります。その時も倍率を 100% にします。"),
)


def print_help():
    """PDF の釦の下の案内。details なので JS なしで開き、閉じていれば窓の見た目を変えない。"""
    if not PRINT_HELP:
        return ""
    items = "".join(f"<p><b>{esc(head)}</b><br>{esc(text)}</p>" for head, text in PRINT_HELP)
    return f'<details class="print-help"><summary>{esc(PRINT_HELP_SUMMARY)}</summary>{items}</details>'


def window(sid, data, see, kind, v, recorded, photos=True):
    """型紙の窓（要件の S-01〜S-05）。紙の種類と版を字の札で選び、絵（PNG）を出す。押すと拡大の窓（#zoom）。"""
    card = hypotheses.sheet_of(sid)
    ids = printed_ids(sid, data, recorded)
    # まだ紙の無い札は、窓の中で押して紙を作る釦にする（#127）。
    make = lambda x: (f'<form method="post" action="/toy/{sid}/print#win" class="inline"><input type="hidden" name="hypothesis" value="{esc(x["id"])}"><input type="hidden" name="at" value="win">'
                      f'<button data-busy>仮説 {esc(hypotheses.letter(x))}</button></form>')
    # 紙を作らずに記録を残した人が札から来た時（#320）は、試した後の紙だけがある案も窓に出す。刷った案には数えない。
    # 必須 2 種のたたき台でない案（前の試行の記録）は刷れないので、これが無いと記録の窓に別の案の紙が出る。
    only_after = (kind == "_after" and see in recorded and any(x["id"] == see for x in data["hypotheses"])
                  and (out_dir(sid) / f"{see}_v{v}_after.png").exists())
    if not ids and not only_after:
        return f'<div class="tabs">{make(card)}</div><p class="meta">仮説の札を押すと、紙を作ってここに出します。</p>'
    see = see if see in ids or only_after else (card["id"] if card["id"] in ids else ids[0])
    vs = versions_of(sid, see, printed_only=True)  # 刷ってある版だけ（版 1 を決め打ちすると、無い紙の絵とリンクが出る）
    if only_after and v not in vs:
        vs = sorted([*vs, v])
    v = v if v in vs else vs[-1]
    kind = kind if kind in ("", "_tejun", "_after") else ""
    if kind == "_after" and see not in recorded:
        kind = ""
    h = next(x for x in data["hypotheses"] if x["id"] == see)
    name = f"{see}_v{v}{kind}"
    q = lambda hid, k, vv: f"/toy/{sid}?see={hid}&kind={k.lstrip('_') or 'sheet'}&v={vv}#win"
    # たたき台の札だけ。前の記録の紙を見ている時は、ここから戻る。
    hyps = (make(card) if card["id"] not in ids else
            f'<a href="{q(card["id"], "", versions_of(sid, card["id"], printed_only=True)[-1])}" aria-current="{"true" if card["id"] == see else "false"}">仮説 {esc(hypotheses.letter(card))}</a>')
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
            from .kaizen import _param_name  # 呼び名の無い寸法は、内部の名前を出さない

            ch = "、".join(f"{_param_name(sid, c['param'])} {c['from']}→{c['to']}" for c in adopted.get("changes", []))
            # 合言葉なしで開いた場には、記録の番号（内部の番号）を出さない（J-028）。
            basis = f'{esc(wording.BASED_ON.format("、".join(wording.record_no(r) for r in adopted.get("record_ids", []))))}。' if photos else ""
            cap = f'<p class="meta">版 {v}: {basis}変えた所: {esc(ch)}</p>'
    # 版の記録があって紙が無い版は札に出ないので、刷り直す釦を添える（#158）。
    cap += "".join(f'<form method="post" action="/toy/{sid}/reprint#win" class="inline"><input type="hidden" name="hypothesis" value="{esc(see)}"><input type="hidden" name="version" value="{n}"><button class="quiet" data-busy>版 {n} の紙を作り直す</button></form>'
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
            f'<p><a class="btn" href="{pdf}" target="_blank" rel="noopener">PDF を開いて印刷する</a></p>{print_help()}'
            '<p class="meta">100% で刷り、紙の物差しが 10cm か確かめます。A4 の紙 1 枚。</p>'
            f'<p class="meta"><a href="/sheet/{sid}/{name}.svg" target="_blank" rel="noopener">線の絵（SVG）</a>・絵を押すと大きく見られます。</p>'
            f'<p class="meta">{esc(HYPOTHESIS)}</p></div>')
    # 押せない札の理由は title だけだとスマホで読めないので、字で出す（#127）。
    why = "仮説の点線の札は、押すと紙を作ってここに出します。" if card["id"] not in ids else ""
    why += "試した後の紙は、記録を残すと開きます。" if see not in recorded else ""
    why = f'<p class="meta">{why}</p>' if why else ""
    return f'<div class="tabs">{hyps}</div><div class="tabs">{kinds}</div>{why}<div class="win">{fig}{side}</div>'


def sample_records(data):
    """その玩具の見本の記録（デモ用の作り物。札つき）。本物の記録の後ろに置き、混ぜない。"""
    from . import demo_samples

    return demo_samples.uploads_for(data["toy"])


def analogy_section(data):
    """たとえと、関連する事柄（本人の頼み 11-05「扇を開くのような、身近な物へのたとえと関連する事柄を全部の玩具に」）。
    文は作る側の言葉なので印を付け、答えではない事を書く（J-016 の線）。
    欄の形は data/hypotheses の `analogy`（like・related・written_by）。試験は tests/test_analogy.py。"""
    a = data.get("analogy")
    if not a:
        return ""
    rel = "".join(f"<li>{esc(x)}</li>" for x in a.get("related", []))
    return (f'<section class="sec" id="tatoe"><h2>たとえと、関連する事柄</h2>'
            f'<p class="meta"><span class="lb">作る側のたとえ</span>{esc(wording.plain(a.get("written_by", "")))}。たとえは仕組みを考える手がかりで、答えではありません。</p>'
            f'<article class="card"><h3>身近な物でいうと</h3><p>{esc(a["like"])}</p></article>'
            f'<article class="card"><h3>関連する事柄</h3><ul>{rel}</ul></article></section>')


def ask_form(sid, data, asked=None, note="", filled=None):
    """作っている最中の手順の質問の口（本人の決定 11-04、src/api/ask.py）。刷った紙がある仮説だけを選べる。聞かれた時だけ答える。"""
    card = hypotheses.sheet_of(sid)
    if not versions_of(sid, card["id"], printed_only=True):
        return ""
    shown = ""
    if asked:
        q, a = asked
        shown = f'<div id="ask-answer" class="notice"><p class="meta">聞いた事: {esc(q)}</p><p>{esc(a)}</p></div>'
    return refill(f'<form method="post" action="/toy/{sid}/ask#ask" id="ask" class="card">{note}<h3>作っている途中で困ったら</h3>'
            '<p class="meta">切る・折る・貼る・組む順の疑問に答えます（例: 谷折りって？）。どう動くか・仕組みは、試して確かめる所なので答えません。</p>'
            f'<input type="hidden" name="hypothesis" value="{esc(card["id"])}"><label>聞きたい事<input type="text" name="question" required maxlength="300"></label>'
            # 断り（本人の決定 11-05「工作の様子を蓄積してサービス全体の改善に回す。個人の情報は落とす」）: 質問の文を残すので、残す事と、
            # 名前を書かないでほしい事を、聞く口のすぐ下に出す。床が落とせるのは連絡先の形だけで、名前は機械では落とせないため。
            f'<button>聞く</button><p class="meta">{esc(making_log.ASK_NOTICE)}{esc(making_log.ASK_NAME_TEXT)}</p>{shown}</form>', filled)


# 記録の欄の畳みの見出し（#300）。本人が採った文（11-05）を一字も変えずに入れる。空にすると畳まずに並ぶ。
RECORD_MORE = "もっと書く（あれば）"


def record_form(sid, data, mine=(), open_more=False):
    """mine は、この画面が話した考えから作った本人の案（自分の仮説の記録の形）。"""
    template = data.get("template", "slider_fan")
    card = hypotheses.sheet_of(sid)
    hyps = [(card["id"], f'仮説 {hypotheses.letter(card)}「{card["name"]}」')] + [(h["id"], f'あなたの仮説「{h["name"]}」') for h in mine]
    # 話した考えから作った本人の案は、選んだ形で出す。作った紙の記録として残すため（たたき台の記録に取り違えない）。
    opts = "".join(f'<option value="{esc(i)}"{" selected" if i != card["id"] else ""}>{esc(n)}</option>' for i, n in hyps)
    # 紙はたたき台の 1 枚なので選ぶ欄を出さない。話した本人の案がある時だけ、その紙の記録を残せるように欄を出す。書いて立てた仮説は並べない（J-032 の点 2）。
    which = f'<label>どの仮説の紙か<select name="hypothesis">{opts}</select></label>' if mine else f'<input type="hidden" name="hypothesis" value="{esc(card["id"])}">'
    # 版が 2 つ以上ある時だけ、どの版の紙かを聞く（紙の題の横に刷ってある）。報告が版を取り違えないため（play_server.sheet_version_of）。
    seen = versions_of(sid, card["id"], printed_only=True)
    version_field = ('<label>どの版の紙か（紙の題の横に刷ってあります）<select name="sheet_version"><option value="">いちばん新しい版</option>'
                     + "".join(f'<option value="{n}">版 {n}</option>' for n in seen) + '</select></label>') if len(seen) > 1 else ""
    from .techo_site import result_icon

    results = "".join(f'<label class="tile"><input type="radio" name="result" value="{esc(r)}" required>{result_icon(r, TEMPLATES[template].RESULTS)}{esc(r)}</label>'
                      for r in TEMPLATES[template].RESULTS)
    if template == "pivot_counterweight":
        extra = '<label>動かした物<select name="power"><option value="">—</option><option>手</option><option>息</option><option>団扇</option><option>風</option></select></label>'
    elif template == "slider_fan":
        # 角度の欄は外した（本人の方針「開き具合の角度などは今回の課題ではない」、U-25）。受け口は古い記録のために残す。
        extra = '<label>開いた力<select name="opener"><option value="">—</option><option>紙の力</option><option>糸</option><option>手</option></select></label>'
    else:
        extra = getattr(TEMPLATES[template], "RECORD_EXTRA", "")
    more = (f'{extra}<label>最初に動いたのはどこか<input type="text" name="first_moved"></label><label>引っかかった所<input type="text" name="stuck"></label>'
            '<label>何を変えると違いが出そうか<input type="text" name="what_if"></label><label>作っている途中で思いついた事<input type="text" name="idea"></label>'
            '<label>メモ<textarea name="note"></textarea></label>')
    if RECORD_MORE:
        # 残りは畳む（#300）。作る前の人に「全部書くのか」と読ませないため。素の details なので JS なしで開け、閉じたままでも送られる。
        # 選ぶ欄（話した本人の案がある時のどの紙か・版が 2 つ以上の時のどの版か）は畳まない: 見えないまま送ると、記録と試した後の紙が別の案になる。
        # 必須の欄も入れない: 閉じた欄が空だと、ブラウザは知らせる先を出せず送れなくなる。
        more = f'<details{" open" if open_more else ""} style="margin:14px 0 0"><summary>{esc(RECORD_MORE)}</summary>{more}</details>'
    return (f'<form method="post" action="/toy/{sid}/record#kiroku" class="card" id="record"><h3>試した記録</h3><p class="meta">見た事を残します。動かなかった記録も、そのまま紙の返事です。記録はこの頁でほかの人も読むので、名前や連絡先は書かないでください。</p>'
            f'{which}{version_field}<fieldset style="border:0;padding:0;margin:14px 0 0"><legend class="meta">見た事</legend><div class="tiles">{results}</div></fieldset>'
            # 感想の欄（本人の方針 11-05「作ったものの感想と動きを報告してもらう」）。動きは上の札、感想は自由な文。空でもよい。
            '<label>作ってみてどうだったか（感想。動いた所、難しかった所、思った事）<textarea name="impression"></textarea></label>'
            # 人の工夫（本人の言葉 11-05）。「型紙は不完全でうまく動かないけどそれを人間が工夫で乗り切る過程をAIにフィードバックして型紙が改善される」の、輪の材料の欄。一部だけ書いても記録は落とさない（play_server.fixes_of）。
            '<fieldset style="border:0;padding:0;margin:14px 0 0"><legend class="meta">うまくいかなかった所と、どう工夫したか（あれば）</legend><label>どの部品か<input type="text" name="fix_part"></label><label>どう工夫したか<input type="text" name="fix_change"></label><label>どうなったか<input type="text" name="fix_outcome"></label></fieldset>'
            f'{more}<button>記録を残す</button></form>')


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
# 文面を本人に確認してもらっている床（#164）。確認が済むまで検査の文を画面に出さず、下の「近い値を試す」の 1 行だけにする。文は確認の後に上の表へ足す。
NEXT_REASONS_WAITING = {"F5.fan_leg", "F5.figure_base", "F5.hole"}


def next_reasons(failures, sid, hid, param, to=None):
    """「次の版を作る」が通らなかった時に出す文。理由のあとに、今の値と次の一手を 1 行足す。"""
    template = hypotheses.load(sid).get("template", "slider_fan")
    now = _params_now(sid, hid, template)
    label, value = _param_label(template, param), now.get(param)
    value = f"{value:g}" if isinstance(value, (int, float)) else ""
    span = getattr(TEMPLATES[template], "RANGES", {}).get(param)
    out, on_paper = [], False
    for f in failures:
        if f.floor == "F5.range" and f.where == param and span:
            # 幅の中なのに範囲の床に落ちるのは、整数の決まり。欄は整数だけを受ける（whole_params）ので、ここへ来るのは JS が無い時か直に送った時。
            # 幅を言うと 31.4 に「6〜40 の間で」と的外れになり、床の文は作る側の字なので、今の値と次の一手だけを言う。
            if isinstance(to, (int, float)) and span[0] <= to <= span[1]:
                on_paper = True
                continue
            text = f"{label}は {span[0]:g}〜{span[1]:g} の間で書いてください" + (f"（今 {value}）。" if value else "。")
        elif f.floor in NEXT_REASONS_WAITING:
            on_paper = True
            continue
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


def whole_params(template):
    """整数だけを受ける寸法（折りの数など）。雛形の範囲の検査に聞く: 幅の中の整数でない値で落ちる寸法。表を別に持つと検査とずれるため。"""
    from omochae.metrics import ALLOWED

    tpl = TEMPLATES[template]
    return [k for k in sorted(ALLOWED[template]) if tpl.check_range({**tpl.DEFAULTS, k: tpl.RANGES[k][0] + (tpl.RANGES[k][1] - tpl.RANGES[k][0]) * 0.6317})]


def next_form(r, back=""):
    """次の版を作る口（本人の問いの (7)、11-04）。人の説明が先にある記録にだけ出す（J-013）。
    人が解釈を書いて確定し、変える寸法を 1 つ選んで採ると、台帳の床（F4・F7・F8・F9）を通った時だけ次の版を刷る。
    次の版はたたき台の記録からだけ（J-032）。ほかの仮説の記録に欄を出しても、版は刷れないか、札に出ない紙が増えるだけなので空を返す。
    自分の紙（OWN-n）の記録は、たたき台へ向けて欄を出す（loop.next_target。今の値もたたき台の物）。"""
    from omochae.metrics import ALLOWED

    target = loop.next_target(r["source_id"], r["hypothesis_id"])
    if target != hypotheses.sheet_of(r["source_id"])["id"]:
        return ""
    template = hypotheses.load(r["source_id"]).get("template", "slider_fan")
    now = _params_now(r["source_id"], target, template)
    # 1 つ変えるだけでは通らない寸法は出さない。選んでも必ず断られる項目になるため（loop.movable_params）。
    movable = loop.movable_params(r["source_id"], target)
    opts = "".join(_param_option(template, k, now) for k in sorted(ALLOWED[template]) if k in movable)
    if not opts:
        return ""
    # 解釈はすぐ上の説明とほぼ同じ問いなので、説明を初めから入れておく（#129）。そのまま採っても、書き直してもよい。
    told = (loop.explanation(r["id"]) or {}).get("text", "")
    hidden = f'<input type="hidden" name="back" value="{esc(back)}">' if back else ""
    # 整数だけの寸法を選んだ時は step=1 にして、ブラウザの標準の吹き出しで断る（新しい字を足さない）。欄は 1 つで寸法は選ぶ物なので、JS で切り替える。JS が無ければ小数も通り、next_reasons が断る。
    # min と max は付けない: 幅の外は今ある字で断る。書いた値を欄に戻した時は value が step の起点になるので、起点が 0 に戻るように外す（値は残る）。
    whole = whole_params(template)
    step = ('<script>(()=>{const f=document.currentScript.previousElementSibling,s=f.elements.param,t=f.elements.to,w=' + json.dumps(whole) + ';'
            'const set=()=>{t.step=w.includes(s.value)?"1":"any"};t.value=t.value;t.removeAttribute("value");s.addEventListener("change",set);set()})()</script>') if whole else ""
    return (f'<details><summary>次の版を作る（寸法を 1 つ変える）</summary><form method="post" action="/record/{esc(r["id"])}/next#next-{esc(r["id"])}">{hidden}'
            f'<label>何が起きたと読むか（解釈）<textarea name="interpretation" required>{esc(told)}</textarea></label>'
            f'<label>変える寸法<select name="param">{opts}</select></label><p class="meta">かっこの中は変えてよい幅です。紙に組める値は、この幅より狭い事があります。</p>'
            '<label>新しい値<input type="number" step="any" name="to" inputmode="decimal" required></label>'
            '<label>変える理由<input type="text" name="why" required></label><label>採った人<input type="text" name="by" required></label>'
            f'<button data-busy>次の版の紙を作る</button></form>{step}</details>')


def ai_block(r, up_key=None, photos=True):
    """人の説明の後に出す AI の返事（J-013 の順の最後）。読みと観察は案で、採点しない。鍵が無い時は play_server がその旨を返す。
    photos=False は合言葉なしで開いた場で、読みと観察の文を出さない（記録の文から作った字なので。J-028）。"""
    from . import techo_site

    rid = esc(r["id"])
    out = ""
    i = loop.interpretation(r["id"]) if photos else None
    if i and isinstance(i.get("content"), dict):
        c = i["content"]
        lines = "".join(f"<li>{esc(x)}</li>" for x in c.get("observed", []))
        lines += "".join(f'<li>{esc(x.get("text", ""))}（確からしさ: {esc(x.get("confidence", ""))}）</li>' for x in c.get("causes", []) if isinstance(x, dict))
        lines += "".join(f"<li>分からない事: {esc(x)}</li>" for x in c.get("unknown", []))
        out += f'<div class="item"><p class="meta">Claude の読み（案）</p><ul>{lines}</ul></div>'
    o = techo_site.seen_observation(r["id"], up_key) if photos else None
    if o:
        lines = "".join(f"<li>{esc(x)}</li>" for x in o.get("observed", [])) + "".join(f"<li>見えなかった事: {esc(x)}</li>" for x in o.get("unclear", []))
        out += f'<div class="item"><p class="meta">観察（Claude の補助）</p><ul>{lines}</ul></div>'
    can_ask, can_watch, why = techo_site.ai_offer(r["id"], up_key)
    buttons = (f'<form method="post" action="/record/{rid}/ai-interpret#{rid}" class="inline"><button class="quiet">Claude に聞く（何が起きたか）</button></form>' if can_ask else "") + (
               f'<form method="post" action="/record/{rid}/ai-observe#{rid}" class="inline"><button class="quiet">動画を見てもらう</button></form>' if can_watch else "")
    return out + (f'<div class="row">{buttons}</div>' if buttons else "") + (f'<p class="meta">{why}</p>' if why else "")


def own_papers(sid, hid, ver):
    """前に書かれた自分の仮説で刷った紙へのリンク。札を外したので（J-032 の点 2）、記録の札から開く。字は札と窓にあった物のまま。"""
    links = [f'<a href="/sheet/{sid}/{esc(hid)}_v{esc(ver)}{kind}.pdf" target="_blank" rel="noopener">{label}</a>'
             for kind, label in (("_free", "型紙なしの紙"), ("", "型紙"), ("_tejun", "手順の紙")) if (out_dir(sid) / f"{hid}_v{ver}{kind}.pdf").exists()]
    return f'<p>{"・".join(links)}</p>' if links else ""


def records_list(sid, recs, photos=True, at="", note="", filled=(None, {}), up_key=None, rec_key=None):
    """記録の札を並べる。rec_key は、この画面が記録を残した時に渡した鍵。説明の欄はその記録にだけ出す（records.mine）。"""
    from api.words import spoken_own_ids

    from . import zukan

    data = hypotheses.load(sid)
    spoken = spoken_own_ids(sid)
    out = "<p class='meta'>記録の順。上下はありません。紙の返事 → 自分の説明 → AI の返事、の順で開きます。</p>" if recs else ""
    for r in reversed(recs):
        told = loop.explanation(r["id"])
        deg = f'・{r["opened_deg"]:g}°' if r.get("opened_deg") is not None else ""
        # 試した後の紙も字のリンクは窓へ（画面に出す）。PDF は添え。
        hid, ver = esc(r["hypothesis_id"]), r.get("sheet_version", 1)
        pdf = f'/sheet/{sid}/{hid}_v{ver}_after.pdf'
        after = (f'<p><a href="/toy/{sid}?see={hid}&kind=after&v={ver}#win">試した後の紙</a>（先に開いて、次に変える条件を読む。'
                 f'<a href="{pdf}" target="_blank" rel="noopener">PDF</a>）</p>')
        # 自分の仮説は窓に出ない（窓へ向けると、ほかの案の紙が出る）ので、字のリンクも PDF へ向ける（#320）。
        if not any(h["id"] == r["hypothesis_id"] for h in data["hypotheses"]):
            # 合言葉なしの場では OWN-n の紙を開かない（think_sheet.opens）。行き止まりになるので、札に紙への道を出さない。
            after = f'<p><a href="{pdf}" target="_blank" rel="noopener">試した後の紙</a>（先に開いて、次に変える条件を読む）</p>' if photos else ""
            # 話した案の刷った紙は、作った本人の画面からだけ開く。これも道を出さない。
            if photos and r["hypothesis_id"] not in spoken:
                after = own_papers(sid, r["hypothesis_id"], ver) + after
        if told:
            nid = f'next-{r["id"]}'
            nxt = next_form(r)
            if at == nid:
                # 通らなかった時は、畳んだ欄を開いて、その上に理由を出す。手帖から来た印も保つ。
                nxt = refill(next_form(r, filled[1].get("back", "")), filled[1]).replace("<details>", "<details open>", 1)
            # 紙の返事 → 自分の説明 → AI → 次の版 の順を、罫で見分ける（#130）。
            tail = (f'<div class="step"><p>説明: {esc(told["text"])}</p><p>次の思いつき: {esc(told["next_idea"])}</p></div>'
                    f'<div class="step">{ai_block(r, up_key)}</div>' + (f'<div class="step" id="{esc(nid)}">{note if at == nid else ""}{nxt}</div>' if nxt else ""))
        else:
            # 人の説明が先。Claude の釦はこの後の段で出す。
            tail = "" if not records.mine(r["id"], rec_key) else refill(f'<form method="post" action="/record/{esc(r["id"])}/explain#{esc(r["id"])}"><label>何が起きたと思いますか（わからない、でもよい）<textarea name="text" required></textarea></label>'
                    '<label>次に試したい事<input type="text" name="next_idea" required></label><label>書いた人<input type="text" name="by" required></label><button>説明を残す</button></form>', filled[1] if filled[0] == "explain" and at == r["id"] else {})
        here = note if at == r["id"] else ""
        # 感想（本人の方針 11-05「感想と動きの報告」）。動きの欄の次に、作った人の言葉として出す。
        feel = f'<p>感想: {esc(r["impression"])}</p>' if r.get("impression") else ""
        # 作った物の写真と動画、止まった所の答えも同じ札に出す（本人の指摘 11-05: 制作した記録を玩具の頁で見る）。
        ans = r.get("answers") or {}
        # 書いた欄だけを読める字で出す。書いていない欄の名前は並べない（#130）。
        written = [("最初に動いた所", ans.get("first_moved")), ("引っかかった所", ans.get("stuck")), ("変えると違いが出そうな所", ans.get("what_if")),
                   ("思いついた事", "、".join(str(x) for x in r.get("ideas") or [])), ("メモ", wording.record_note(r.get("note")))]
        feel += "".join(f"<p>{label}: {esc(text)}</p>" for label, text in written if text)
        # 人の工夫（本人の言葉 11-05「それを人間が工夫で乗り切る過程をAIにフィードバックして型紙が改善される」）。輪の材料そのものなので札の上の方に出す。
        feel = "".join(f'<p>工夫: {esc(f.get("part", ""))} / {esc(f.get("change", ""))} / {esc(f.get("outcome", ""))}</p>' for f in r.get("fixes", []) if isinstance(f, dict)) + feel
        feel = media_html(r["id"], photos=photos) + feel
        if not photos:
            # 合言葉なしで開いた場: 人の書いた文を別の人に見せない（文の中の名前は機械で落とせない。J-028）。札と紙への道と欄だけ残す。
            feel = ""
            if told:
                # 次の版の欄も出さない: 解釈の欄に説明が初めから入る上に、この場では送っても断られる（#336）。
                tail = '<p class="meta">説明を残しました。</p>' + ai_block(r, up_key, photos=False)
        out += f'<article class="card" id="{esc(r["id"])}">{here}<h3>{esc(zukan.record_title(r, data))}{esc(deg)}</h3><p class="meta">{esc(zukan.record_date(r))}・版 {esc(ver)}{"・" + esc(wording.record_no(r["id"])) if photos else ""}</p>{feel}{after}{tail}</article>'
    return out


def observations(sid, data, link=True, photos=True):
    """記録を読む（順路の 2 段目）。文には印を付ける（J-016 の線。zukan と同じ作り）。"""
    from . import zukan

    lines = zukan.observation_lines(sid, data, photos)
    if not lines:
        return '<p class="meta"><span class="lb">観察</span>試した記録はまだありません。最初の記録を残す人になります。</p>'
    # 行から同じ頁の記録の札（写真・感想・説明）へ飛べる。
    text = lambda x: f'<a href="#{esc(x["record_id"])}">{esc(x["text"])}</a>' if link and x.get("record_id") else esc(x["text"])
    return "<ul class='meta' style='list-style:none;padding:0'>" + "".join(f'<li><span class="lb">{esc(x["label"])}</span>{text(x)}</li>' for x in lines) + "</ul>"


def media_html(rid, cls="shots", photos=True):
    """記録に添えた写真と動画（手帖の「上げる」で添えた物）。ギャラリーと同じ道（/record/<記録>/media/）から出す。
    photos=False は合言葉なしで開いた場。受け口が画像を出さないので、壊れた絵にしないよう枠ごと出さない（J-028）。"""
    from omochae import media_review

    from .techo_site import media_of

    # 物だけと人が確かめた物だけを出す（本人の決定 11-05、#314）。この頁は他の人にも見えるので、ギャラリーと同じ線にする。
    files = media_review.public(rid, media_of(rid)) if photos else []
    if not files:
        return ""
    pics = "".join((f'<video src="/record/{esc(rid)}/media/{esc(f)}" controls muted playsinline preload="metadata"></video>' if f.endswith(("mp4", "mov"))
                    else f'<img src="/record/{esc(rid)}/media/{esc(f)}" alt="作った物の写真" loading="lazy">') for f in files)
    return f'<div class="{cls}">{pics}</div>'


def made_strip(sid, recs, photos=True):
    """玩具の頁の頭に出す「他の人が作った物」の帯（本人の指摘 11-05「制作した記録とおもちゃのページが関連してない」、本人の決定 11-05「他の人の作ったものギャラリーは作る」）。
    写真の小さな並びから、同じ頁の記録の札へ飛ぶ。photos=False は合言葉なしで開いた場で、写真は出さず札への道だけを出す（J-028）。"""
    if not recs:
        return ""
    from omochae import media_review

    from .techo_site import media_of

    thumbs = ""
    for r in reversed(recs):
        for f in (media_review.public(r["id"], media_of(r["id"]))[:1] if photos else []):
            tag = (f'<video src="/record/{esc(r["id"])}/media/{esc(f)}" muted playsinline preload="metadata"></video>' if f.endswith(("mp4", "mov"))
                   else f'<img src="/record/{esc(r["id"])}/media/{esc(f)}" alt="作った物の写真" loading="lazy">')
            thumbs += f'<a href="#{esc(r["id"])}" aria-label="{esc(wording.record_no(r["id"]))} へ">{tag}</a>'
    return (f'<div class="strip">{thumbs}</div>' if thumbs else "") + '<p class="meta"><a href="#minna">他の人が作った物を見る（写真・感想・工夫）</a></p>'


def neighbours(sid):
    ss = sources()
    i = ss.index(sid)
    prev_, next_ = ss[i - 1] if i > 0 else None, ss[i + 1] if i + 1 < len(ss) else None
    out = []
    if prev_:
        out.append(f'<a href="/toy/{prev_}">← {esc(hypotheses.load(prev_)["toy"])}</a>')
    out += ['<a href="/toys">おもちゃの一覧</a>', '<a href="/gallery">作った物と職人の言葉</a>', '<a href="/">入口へ</a>']
    if next_:
        out.append(f'<a href="/toy/{next_}">{esc(hypotheses.load(next_)["toy"])} →</a>')
    return '<p class="links">' + "".join(out) + "</p>"


def evidence_item(e):
    """根拠の 1 行。置き場の道（data/…）は作る側の控えなので、読む人の頁に出さない（記録の中の道は照合に使うので消さない）。
    出所が文の後ろの注と同じ字になる時は、出所を重ねない（読む人の字にすると「（作る側の考え）（作る側の考え）」と並ぶため）。"""
    what, where = (re.sub(r"（data/[^）]*）", "", str(e[k])) for k in ("what", "where"))
    what, shown = wording.plain(what), wording.plain(where)
    where = "" if where.startswith("data/") or what.endswith(f"（{shown}）") else f"（{esc(shown)}）"
    return f'<li>〔{esc(e["certainty"])}〕{esc(what)}{where}</li>'


def toy_page(sid, look=skin.DEFAULT, errors=(), msg="", asked=None, see=None, kind="", v=0, path=None, photos=True, at="", filled=None, mine=(), up_key=None, rec_key=None):
    """玩具の頁。本人の決定（11-05、#242）「予想の段を無くして、すぐ作る形にする」で、開いたら仮説の札と刷る口がすぐ見える。
    答えに読まれない事は、門でなく札で守る: 「型紙は正解ではなく、AI が考えた仮説」を作る節の頭に出す（本人の言葉 11-05）。
    photos=False は合言葉なしで開いた場（写真と動画を出さない。J-028）。
    at は返事の文を入れる場所（節か札の id）。着く錨と同じ物を渡す（#121）。filled は通らなかった欄の名前と、書いた中身。"""
    data, src = hypotheses.load(sid), source(sid)
    path = path or f"/toy/{sid}"
    note = reply_note(errors, msg)
    filled = filled or (None, {})
    head = lambda name: note if at == name else ""
    fill = lambda name: filled[1] if filled[0] == name else {}
    has_pic = (ROOT / "out/sources" / f"{sid}.jpg").exists()
    nopic = "" if has_pic else f'<p class="meta"><a href="{esc(src["image_url"])}">図を見る（国立国会図書館）</a></p>'
    songs = "".join(f'<p>{esc(e["text"])}</p>' for e in src.get("transcription", {}).get("entries", []) if not e.get("rejected_by") and e.get("checked_by"))
    who = "・".join(sorted({wording.plain(e["checked_by"]) for e in src.get("transcription", {}).get("entries", []) if not e.get("rejected_by") and e.get("checked_by")}))
    stage = hypotheses.stage(sid)
    stage_note = '<p class="meta"><span class="lb">試作</span>全部の玩具を型紙にする途中の物。名前は作る側の見立てで、まだ確かめていません。</p>' if stage != "必須" else ""
    hero = (f'<section class="hero">{skin.frame(sid, src.get("holding", ""))}<div>'
            f'<h1>{esc(data["toy"])}</h1>{stage_note}'
            + (f'<div class="songs">{songs}</div><p class="meta">原文の引用。確かめた人: {esc(who)}</p>' if songs else "")
            + skin.artwork_label(data["toy"], src) + nopic
            + f'<p class="links"><a href="/zukan/{sid}">図鑑の頁</a><a href="/zukan/{sid}/yomi">くずし字を読む</a><a href="/toys">ほかのおもちゃ</a></p>'
            f'<h3 style="margin-top:24px">これまでの記録</h3>{observations(sid, data, photos=photos)}{made_strip(sid, records.all_records(sid), photos)}</div></section>')
    recs = records.all_records(sid)
    recorded = {r["hypothesis_id"] for r in recs}
    # 作る節を頭に置く。開いたらすぐ刷れる形（#242）。札はたたき台の 1 枚だけで、順位は学ぶ人の画面に出さない（J-013・J-025・J-032）。
    body = hero + (f'<section class="sec" id="kasetsu">{head("kasetsu") or ("" if at else note)}<h2>すぐ作る</h2><p class="lead">型紙と手順の紙を刷ります。切って、折って、組みます。</p>'
                   f'<p class="premise" id="premise">{esc(PREMISE_PAGE)}</p><p class="meta">{esc(ways.NOTE)}</p><div class="plates">')
    from . import kumitate  # 手順どおりに組み立てる絵。型紙の絵の上に初めから出す（本人の決定 11-06。J-033）

    body += kumitate.block(sid)
    for h in [hypotheses.sheet_of(sid)]:
        ev = "".join(evidence_item(e) for e in h["evidence"])
        last = versions_of(sid, h["id"], printed_only=True)
        # 紙の種類と版を選ぶのは窓の札の役。札の下に字のリンクを並べると、版ごとに 3 つ増える（#127）。
        thumb = (f'<a class="thumb" href="/toy/{sid}?see={h["id"]}&kind=sheet&v={last[-1]}#win" aria-label="仮説 {esc(hypotheses.letter(h))} の紙を窓で見る"><img src="/sheet/{sid}/{h["id"]}_v{last[-1]}.png" alt="" loading="lazy"></a>'
                 if last and (out_dir(sid) / f"{h['id']}_v{last[-1]}.png").exists() else "")
        body += (f'<div class="plate"><div class="letter">{esc(hypotheses.letter(h))}</div><h3>仮説 {esc(hypotheses.letter(h))}「{esc(h["name"])}」</h3><p>{esc(wording.plain(h["how_it_moves"]))}</p><ul>{ev}</ul>'
                 f'<p class="meta">試して見る事: {esc(wording.plain(h["to_measure"]))}</p>{way_tags(ways.labels(ways.of_hypothesis(data, h))) if h.get("params") is not None else ""}{thumb}<div class="acts">'
                 f'<form method="post" action="/toy/{sid}/print#kasetsu"><input type="hidden" name="hypothesis" value="{esc(h["id"])}"><button class="quiet" data-busy>型紙を見る</button></form>'
                 '</div></div>')
    # 書いて立てた仮説の札と書く欄は外した（本人の決定 11-05 18:08「仮説は書かず、話すことができる」、J-032 の点 2）。考えは下の節で話す。
    body += "</div></section>"
    # 仮説を見て、考えを話す（一周の 1、Issue #279）。仮説の節のすぐ後に置く。
    from . import hanasu

    body += hanasu.think_section(sid, data, head("hanasu"))
    from . import think_sheet  # 話した考えから、たたき台の紙を作り直す（ループ1、Issue #335）
    if photos and think_sheet.ready(sid):  # 合言葉なしの場（photos=False）と、呼び名がそろっていない玩具では節を出さない。受け口も閉じている（J-028）
        body += think_sheet.section(sid, at, head(at))
    body += analogy_section(data)
    body += f'<section class="sec" id="win">{head("win")}<h2>型紙の窓</h2><p class="meta">画面で見て、印刷する前に案を検討する所。</p>{window(sid, data, see, kind, v, recorded, photos)}</section>'
    body += (f'<section class="sec" id="tsukuru"><h2>作る</h2><p class="lead">刷った紙を切って、折って、組みます。机に置いた手帖で、声で手順を聞き、写真と動画を記録に添えられます。</p>'
             f'<p><a class="btn" href="/toy/{sid}/techo">手帖をひらく（作りながら聞く・上げる）</a>'
             # 作りながら見る（観察 A の試作。本人の案 11-05「端末を机の端に置いて…作成の様子を見れるようにする」）。刷った紙がある時だけ出す。
             + (f' <a class="btn quiet" href="/toy/{sid}/tsukuru">作りながら見る（机の端に置く・試作）</a>' if versions_of(sid, hypotheses.sheet_of(sid)["id"], printed_only=True) or mine else "")
             + f'</p>{ask_form(sid, data, asked, head("ask"), fill("ask"))}</section>')
    # 通らなかった時は畳みを開く。書いた字を隠さないため（#300）。
    body += f'<section class="sec" id="kiroku">{head("kiroku")}<h2>試した記録を残す</h2>{refill(record_form(sid, data, [h for h in hypotheses.own_hypotheses(sid) if h["id"] in mine], bool(fill("record"))), fill("record"))}</section>'
    # 他の人の作った物（本人の決定 11-05「他の人の作ったものギャラリーは作る」）。記録の札と見本を、同じ節に並べる。全部の玩具の分は /gallery。
    body += (f'<section class="sec" id="minna"><h2>他の人が作った物と、自分の記録</h2>{records_list(sid, recs, photos, at, note, filled, up_key, rec_key) or "<p class=meta>まだありません。作ったら、最初の記録を残す人になります。</p>"}'
             f'{sample_records(data)}<p class="links"><a href="/gallery">全部の玩具の、作った物を見る</a></p></section>')
    # 改善の輪（本人の方針 11-05）: 報告から直した版と、次の版を待つ報告。
    from . import kaizen

    body += kaizen.section(sid, data, recs, photos)
    # 英語の短い紹介（本人の指示 11-05「実装までやって」、J-030）。頁の足に置く: 日本語の順路を押し下げないため。
    from . import en

    body += en.band(sid)
    body += f'<section class="sec">{neighbours(sid)}</section>'
    if note and note not in body:  # 知らない印や、欄が出ていない時も、文を落とさない
        body = body.replace('id="kasetsu">', f'id="kasetsu">{note}', 1)
    return skin.shell(data["toy"], body, look, "", path)
