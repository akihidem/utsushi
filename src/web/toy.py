"""玩具の頁（順路の真ん中: 記録を読む → 仮説と型紙の窓 → 作る → 組み方 → 記録 → 人の説明 → AI → 次の版 → 戻る）。
刷るのは型紙だけ（本人の決まり 11-06「文章のプリントは廃止」）。前は記録の後に試した後の紙を開いた。
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

from omochae import hypotheses, loop, records, ways
from omochae.compose import TEMPLATES
from omochae.marks import HYPOTHESIS, PREMISE_PAGE

from . import naoru, skin, wording
from .play_server import PARAM_NAMES, esc, out_dir, printed_versions, source
from .toys import way_tags

# 窓で見て刷る紙は型紙だけ（本人の決まり 11-06「文章のプリントは廃止。組み立て用のページだけでいい」・6 点の 1）。
# 前は手順の紙と試した後の紙も札にあった。組み方は頁の「組み方」の節、試した事の欄と予想の欄は紙から外した（6 点の 2）。
# 書き出し（PDF・PNG・SVG）は残す: 作りながら見る頁が手順の紙の PNG を使い、「刷った」は PDF の有無で読むため（設計メモ版 3）。
KINDS = (("", "型紙"),)


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
    """型紙の窓（要件の S-01〜S-05）。紙の種類と版を字の札で選び、絵（PNG）を出す。押すと拡大の窓（#zoom）。
    Returns (頭, 紙, 口)。頭 は PDF を開いて印刷する の釦と刷り方の行、紙 は紙の絵と札と版の札、口 は つくる（手帖へ）・のこす と行。
    刷った紙が無ければ ("", "", "")。
    3 つに分けるのは、段の中を 見出し「型紙を印刷する」→ PDF を開いて印刷する → 型紙 → 版の歩み → 口 の順にするため（本人の言葉 11-08「型紙の窓を
    「型紙を印刷する」からにして、その直下に PDF を開いて印刷するボタンを置く。」・前の言葉「…型紙、型紙の歩み、型紙の窓、の順がいい。」）。
    呼び手（toy_page）が見出しの下に頭を、紙と口の間に版の歩みを入れる"""
    card = hypotheses.sheet_of(sid)
    ids = printed_ids(sid, data, recorded)
    # 紙を作るのは頭の「つくる」だけ（刷る口を 1 つに。本人のサイト体験レビュー 11-07 の 3）。前は、まだ紙の無い札を窓の中で押して紙を作る釦にしていた（#127）。
    # 前の札や記録の後の知らせのリンク（kind=tejun・after）で来ても、型紙を出す（文章の紙は刷らなくなった。本人の決まり 11-06）
    kind = ""
    if not ids:
        return "", "", ""
    see = see if see in ids else (card["id"] if card["id"] in ids else ids[0])
    vs = versions_of(sid, see, printed_only=True)  # 刷ってある版だけ（版 1 を決め打ちすると、無い紙の絵とリンクが出る）
    v = v if v in vs else vs[-1]
    # たたき台の紙が前の題で刷った物（paper_current）の時は、窓に出さない。出すと「PDF を開いて印刷する」が前の題（版 1 など）の紙を開き、
    # 頁の版の札（版 7）と食い違う（11-08 に見つかった）。紙を刷る「つくる」（make_go）が今の題で刷り直す。前の記録の紙（たたき台でない仮説）は、
    # その記録で刷った紙として読むので、照らさずに出す
    if see == card["id"] and not paper_current(sid, see, v):
        return "", ""
    h = next(x for x in data["hypotheses"] if x["id"] == see)
    name = f"{see}_v{v}{kind}"
    q = lambda hid, k, vv: f"/toy/{sid}?see={hid}&kind={k.lstrip('_') or 'sheet'}&v={vv}#win"
    # 窓の中の「仮説」「型紙」の切り替えの札は外した（本人の言葉 11-08「型紙の窓のところにある仮説・型紙のボタンは要らない。」）。札は 1 つずつしか無く
    # （たたき台の仮説 1 つ・紙の種類は型紙だけ）、押しても何も替わらなかった。どの仮説の紙かは札の見出し（side の h3「仮説の型紙」）の字で分かる。
    # 前の記録の紙を見ている時（see が たたき台でない）の戻り道は、頭の「つくる」と版の札（vers）が持つ
    # 版の呼び方は組の番号（窓口の決定 11-07: 版の数は組の番号で統一。組の中の直しがある時だけ「（直し N）」）。hypotheses.label_of
    ban = lambda n: esc(hypotheses.label_of(hypotheses.current_set(data), n))
    vers = "".join(f"<b>{ban(n)}</b>" if n == v else f'<a href="{q(see, kind, n)}">{ban(n)}</a>' for n in vs)
    cap = ""
    if v > 1:
        _, adopted = loop.version_params(sid, see, v)
        if adopted:
            from .kaizen import _param_name  # 呼び名の無い寸法は、内部の名前を出さない

            ch = "、".join(f"{_param_name(sid, c['param'])} {c['from']}→{c['to']}" for c in adopted.get("changes", []))
            # 合言葉なしで開いた場には、記録の番号（内部の番号）を出さない（J-028）。
            basis = f'{esc(wording.BASED_ON.format("、".join(wording.record_no(r) for r in adopted.get("record_ids", []))))}。' if photos else ""
            cap = f'<p class="meta">{ban(v)}: {basis}変えた所: {esc(ch)}</p>'
    # 版の記録があって紙が無い版は札に出ないので、刷り直す釦を添える（#158）。
    cap += "".join(f'<form method="post" action="/toy/{sid}/reprint#win" class="inline"><input type="hidden" name="hypothesis" value="{esc(see)}"><input type="hidden" name="version" value="{n}"><button class="quiet" data-busy>{ban(n)} の紙を作り直す</button></form>'
                   for n in loop.adopted_versions(sid, see) if n not in vs)
    png = f"/sheet/{sid}/{name}.png"
    pdf = f"/sheet/{sid}/{name}.pdf"
    # 窓の絵は軽い PNG、拡大は目盛りと字がにじまない SVG（S-01）。SVG の無い古い紙は PNG に戻る。
    big = f"/sheet/{sid}/{name}.svg" if (out_dir(sid) / f"{name}.svg").exists() else png
    sizes = "".join(f'<input type="radio" name="zoom-size" id="zs{n}"{" checked" if n == 180 else ""}>' for n in ZOOM_SIZES)
    labels = "".join(f'<label for="zs{n}">{n}%</label>' for n in ZOOM_SIZES)
    fig = (f'<figure class="sheet"><a href="#zoom" aria-label="拡大して見る"><img src="{png}" alt="{esc(data["toy"])} {esc(hypotheses.SHOWN)}の{esc(dict(KINDS)[kind])}"></a></figure>'
           f'<div class="zoom" id="zoom">{sizes}<div class="bar" role="group" aria-label="大きさ">{labels}</div><a class="close" href="#win">閉じる</a><div class="pic"><img src="{big}" alt="" loading="lazy"></div></div>'
           + ZOOM_SCRIPT)
    side = (f'<div class="side"><h3>{esc(hypotheses.shown_name(h))}の{esc(dict(KINDS)[kind])}</h3>'
            f'<div class="v">{vers}</div>{cap}</div>')
    # PDF は別のタブで開く（インラインの印は play_server の /sheet/ が付ける）。同じタブで開くと窓から離れ、機器によっては落とすだけになる。
    # 段の見出し「型紙を印刷する」の直下に置く（本人の言葉 11-08）。刷り方の行（print_help・100% の行）は釦の字の続きなので一緒に
    top = (f'<div class="print-top"><p><a class="btn" href="{pdf}" target="_blank" rel="noopener">PDF を開いて印刷する</a></p>{print_help()}'
           '<p class="meta">100% で刷り、紙の物差しが 10cm か確かめます。A4 の紙 1 枚。</p></div>')
    acts = ('<div class="side">'
            # 刷った後に次へ進む口（段 0）。印刷 → つくる（手帖）の順に置く。作る口は手帖（research/36 の本人の決定）
            f'<p class="road"><a class="btn" href="/toy/{sid}/techo">つくる</a></p>'
            # つくる のすぐ下に大きな「のこす」（本人の答え 11-08: のこすへの道は案 B「印刷 → つくる の直後に大きな のこす」。本人の言葉 476「…つくるから
            # のこすの誘導が全体的に弱いので、のこすに行かない可能性が高い。」）。行き先は記録の頁（今の「つくったものを教えてください。」と同じ所）。
            # 枠だけの釦（.quiet）にして、作る口の つくる と見分ける。釦の字は道しるべの駅の名「のこす」（新しい字ではない）。
            # 本人の字（naoru.ROUTE_ASK）は のこす の釦のすぐ上（作りながら見る頁の のこす の札と同じ順: 札の中の上の段に本人の字・その下に のこす。
            # 統括の決め 11-08（479）。#657 では釦の下にあり、別の目の確かめの止め 1 で直した）
            # 道の字（ROUTE_MAKING）を空にした時は、前と同じく本人の字も出さない（3 つの行は 1 つの組。字を外す時の形・test_nokosu_route）
            + (f'<p class="meta nokosu-route">{esc(naoru.ROUTE_ASK)}</p>' if naoru.ROUTE_MAKING and naoru.ROUTE_ASK else "") +
            f'<p class="nokosu-go"><a class="btn quiet" href="/toy/{sid}/techo/kiroku">のこす</a></p>'
            # のこすへの道 1（本人の言葉 11-07 夜「つくる＝つくるところをのこせます」）の 1 行と、意義の 1 行（のこす の画面と同じ字・naoru.purpose）を
            # のこす の釦の下に置く
            + ("".join(f'<p class="meta nokosu-route">{esc(t)}</p>' for t in (naoru.ROUTE_MAKING, naoru.purpose()) if t) if naoru.ROUTE_MAKING else "") +
            f'<p class="meta"><a href="/sheet/{sid}/{name}.svg" target="_blank" rel="noopener">線の絵（SVG）</a>・絵を押すと大きく見られます。</p>'
            f'<p class="meta">{esc(HYPOTHESIS)}</p></div>')
    # 口は紙の 2 列（紙の絵 | 札）の下に 1 列で出す（.win の中に置き、札の CSS（.win .side）をそのまま効かせる）
    return (top, f'<div class="win">{fig}{side}</div>', f'<div class="win win-acts">{acts}</div>')


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


# 試した記録を残す口は、のこす（手帖の最後と記録の頁）へ寄せた（本人の答え 11-07 夕の Q3「試した記録を残すは寄せる — のこすへ」）。
# 前は玩具の頁に記録の欄（record_form・13 の欄）があったが外した。玩具の頁には、記録の頁への道を 1 本だけ置く（KIROKU_TO_NOKOSU）。
# 受け口 /toy/<印>/record は残す（作る側の道具 plain_words と、前からの道で送る物のため）。字は本人の言葉（11-07 夕、設計の担当を通して）
KIROKU_TO_NOKOSU = "つくったものを教えてください。"
# のこそう の段の、もちよる のこの玩具の所への 1 行（設計の問い 7 の推しの字・本人の答え 11-08「推しのとおり。」）。推しの字の「玩具」は、本人の 11-06 の字の決め
# 「玩具の頁の下の本文の玩具をおもちゃに」に合わせて「おもちゃ」にした（統括の決め 11-08・推しの字を作る時の照らし漏れ）
MOCHIYORU_GO = "このおもちゃの作った物を もちよる で見る"

# 作った物の並びの節（#minna）の見出しと、記録が無い時の 1 文（夕方のサイトのレビュー 11-07 の 6「これまでの復元として属人化しない」）。
# 前は「他の人が作った物と、自分の記録」「作ったら、最初の記録を残す人になります」で、並びを人ごとの物（他の人・自分）として読ませた。
# 並びは、失われた玩具の動きを紙で確かめ直してきた記録の積み重ねなので、誰の物かでなく「これまでの復元」と呼ぶ。置き場と並びは変えない。
# 字は本人の言葉（11-07）「4 つとも案のとおり」で決まった（直す時はここだけ。設計の担当と合わせた案）
MINNA_HEAD = "これまでの復元"
MINNA_EMPTY = "まだありません。作って残すと、ここに並びます。"
# 並びの頭の 1 文。前の「自分の説明」は、見る人に人ごとの物と読ませるので「作った人の説明」にした（同じレビューの 6。並びの順の言い方は変えない）
MINNA_ORDER = "記録の順。上下はありません。紙の返事 → 作った人の説明 → AI の返事、の順で開きます。"


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
    "F5.fan_leg": "この値だと、扇の足が短くて台に貼れません。",
    "F5.figure_base": "この値だと、像の足が台より広くて貼れません。",
    "F5.hole": "この値だと、穴が紙の外に出ます。",
}
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

    target = loop.next_target(r["source_id"], r["hypothesis_id"], r.get("sheet_set"))
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
    # 誰が採ったかの欄は、採る人が自分で打つ（#138）。説明の値で埋めると、別の人が作った時に記録が事実と違う。入れておくと、次に開いた別の人に前の人の値が見える。
    # 整数だけの寸法を選んだ時は step=1 にして、ブラウザの標準の吹き出しで断る（新しい字を足さない）。欄は 1 つで寸法は選ぶ物なので、JS で切り替える。JS が無ければ小数も通り、next_reasons が断る。
    # min と max は付けない: 幅の外は今ある字で断る。書いた値を欄に戻した時は value が step の起点になるので、起点が 0 に戻るように外す（値は残る）。
    whole = whole_params(template)
    step = ('<script>(()=>{const f=document.currentScript.previousElementSibling,s=f.elements.param,t=f.elements.to,w=' + json.dumps(whole) + ';'
            'const set=()=>{t.step=w.includes(s.value)?"1":"any"};t.value=t.value;t.removeAttribute("value");s.addEventListener("change",set);set()})()</script>') if whole else ""
    return (f'<details><summary>次の版を作る（寸法を 1 つ変える）</summary><form method="post" action="/record/{esc(r["id"])}/next#next-{esc(r["id"])}">{hidden}'
            f'<label>何が起きたと読むか（解釈）<textarea name="interpretation" required>{esc(told)}</textarea></label>'
            f'<label>変える寸法<select name="param">{opts}</select></label><p class="meta">かっこの中は変えてよい幅です。紙に組める値は、この幅より狭い事があります。</p>'
            '<label>新しい値<input type="number" step="any" name="to" inputmode="decimal" required></label>'
            '<label>変える理由<input type="text" name="why" required></label><label>採った人<input type="text" name="by" autocomplete="off" required></label>'
            f'<button data-busy>次の版の紙を作る</button></form>{step}</details>')


def own_papers(sid, hid, ver):
    """前に書かれた自分の仮説で刷った紙へのリンク。札を外したので（J-032 の点 2）、記録の札から開く。字は札と窓にあった物のまま。"""
    links = [f'<a href="/sheet/{sid}/{esc(hid)}_v{esc(ver)}{kind}.pdf" target="_blank" rel="noopener">{label}</a>'
             # 刷るのは型紙だけ（本人の決まり 11-06・6 点の 1）。前は型紙なしの紙と手順の紙も並べた
             for kind, label in (("", "型紙"),) if (out_dir(sid) / f"{hid}_v{ver}{kind}.pdf").exists()]
    return f'<p>{"・".join(links)}</p>' if links else ""


def foot_links():
    """頁の足の道。前と次の玩具への道と「おもちゃの一覧」は外した（本人の答え 11-08「つくるの頁の一番下の前と次のおもちゃと一覧への道は外す」。
    最初の言葉は「ほかのおもちゃ、のリンク要らない」）。作った物と入口への道は答えに無いので残す。"""
    # ギャラリーの呼び名は、職人の言葉と寄せられた声の節を序の頁（よむ）へ移した後の題「作った物」にそろえる（のこす と もちよる を分ける直し #519。
    # 本人のサイト体験レビュー 11-07 の 6）。字は #519 の頁の題のまま（新しい字は足さない）
    return '<p class="links"><a href="/gallery">作った物</a><a href="/">入口へ</a></p>'


def evidence_item(e):
    """根拠の 1 行。置き場の道（data/…）は作る側の控えなので、読む人の頁に出さない（記録の中の道は照合に使うので消さない）。
    出所が文の後ろの注と同じ字になる時は、出所を重ねない（読む人の字にすると「（作る側の考え）（作る側の考え）」と並ぶため）。"""
    what, where = (re.sub(r"（data/[^）]*）", "", str(e[k])) for k in ("what", "where"))
    what, shown = wording.plain(what), wording.plain(where)
    where = "" if where.startswith("data/") or what.endswith(f"（{shown}）") else f"（{esc(shown)}）"
    return f'<li>〔{esc(e["certainty"])}〕{esc(what)}{where}</li>'


# 段 0（UX の見直し、本人の決定 11-06。research/36）: 道しるべの言葉は えらぶ・つくる・のこす・もちよる。玩具の頁は流れの順
# （原画と歌・題・つくる → 型紙 → 窓で印刷 → 手帖で作る → 記録 → 他の人が作った物）に並べ、読み物と作る側の節は今の見出しのまま畳む。
# 畳んでも節の中身と字は変えない（新しい字は足さない）。見出しを畳みの見出しにするので、開けば前と同じに読める。
FOLD_STYLE = ("<style>.fold-sec>summary{display:flex;align-items:baseline;gap:0}.fold-sec>summary>h2,.fold-sec>summary>h3{display:inline;margin:0}"
              ".road{margin:18px 0 6px}.road .btn{min-height:64px;min-width:10em;font-size:20px;letter-spacing:.4em}"
              # 型紙の窓の のこす の釦は つくる と同じ大きさ（案 B「大きな のこす」）。字の下の行と離しすぎない
              ".win.win-acts{grid-template-columns:minmax(0,1fr);margin-top:12px}.nokosu-go{margin:10px 0 6px}.nokosu-go .btn{min-height:64px;min-width:10em;font-size:20px;letter-spacing:.4em;margin-top:0;box-sizing:border-box;display:inline-flex;align-items:center;justify-content:center}"
              # 狭い幅（1 列）の頭の並び: 原画 → 歌 → 題 → つくる → 原画の出所の字 → 書誌と道 → これまでの記録。原画と歌は頭のまま畳まない（#450 の形）。
              # 原画の部品の中の順（絵・歌・出所）は変えず、題と「つくる」を出所の字の前へ差し込む。幅 390×844 で、前は「つくる」が 873px（最初の画面の外）だった。
              # 広い幅は 2 列（原画 | 題と釦）のままで、ここは効かない
              # 広い幅の頭の 2 列は前の 1 : 1.2 のまま（11-08 に題の塊と狂歌の縦の段を原画の側へ入れた時は 1.9 : 1 にしたが、縦の段を前の形に戻したので外した）
              "@media (max-width:820px){.hero{row-gap:10px;padding-top:20px}.hero>.genga-head,.hero>div{display:contents}.hero>*>*{order:6}"
              # 歌は原画の部品の中で名の無い div に包まれている（genga.head）ので、絵の次の div を歌の段として扱う。試作の玩具の断りは釦の後ろ
              # 原画の部品は、絵と道の段（.genga-main）と歌の段（.genga-uta）。狭い幅は #595 の前の並び（本人の言葉 11-08「縦書きは失敗なので前の形に戻す」）:
              # 絵と 図を見る → 歌（横書き）→ 題 → つくる → 名の下の 1 行 → 作品の札（題の塊）→ くずし字を読む → これまでの記録。
              # 歌を絵のすぐ後に置くのは、前の決め（11-06「狂歌は必ず原画と一緒に見れるように」）
              ".hero>.genga-head>.genga-main{order:1}.hero>.genga-head>.genga-uta{order:2}.hero h1{order:3}"
              ".hero .road{order:4;margin:4px 0}.hero h1+.meta{order:5}}</style>")

# 畳んだ節へ道（#kaizen など）で着いた時は、その畳みを開く。閉じた見出しだけに着くと、行き先の中身が見えないため（別の目の確かめ 11-06、#472 の輪の図の道）。
# 着いた所が畳みの中か、畳みを持つ節なら開く。JS が無い時は、見出しに着き、押せば開く（今の畳みのまま）
FOLD_SCRIPT = ("<script>(()=>{const open=()=>{const id=decodeURIComponent(location.hash.slice(1));if(!id)return;const t=document.getElementById(id);if(!t)return;"
               "const d=t.matches('details')?t:t.querySelector(':scope>details.fold-sec')||t.closest('details');"
               "for(let e=d;e;e=e.parentElement&&e.parentElement.closest('details'))e.open=true};open();addEventListener('hashchange',open)})()</script>")


def fold(section, tag="h2", opened=False):
    """節（<section …><h2>見出し</h2>…</section>）を、見出しを畳みの見出しにした形にする。見出しが無い節はそのまま返す。
    opened は初めから開く時（送って通らなかった記録の欄など。書いた字を隠さないため、#300 と同じ線）。"""
    i = section.find(f"<{tag}")
    j = section.find(f"</{tag}>", i)
    k = section.rfind("</section>")
    if i < 0 or j < 0 or k < j:
        return section
    j += len(f"</{tag}>")
    return section[:i] + f'<details class="fold-sec"{" open" if opened else ""}><summary>{section[i:j]}</summary>' + section[j:k] + "</details>" + section[k:]


def printed_set(sid, hid, version):
    """その版を刷った組（型紙の確定の台帳 loop.confirm_sheet に、刷る度に残る）。台帳に無ければ None。"""
    for rec in loop.sheet_confirmations(sid):
        if rec.get("hypothesis_id") == hid and rec.get("version") == version and rec.get("confirmations"):
            return rec["confirmations"][-1].get("sheet_set")
    return None


def paper_current(sid, hid, version):
    """刷ってある紙が、今の題で刷った物か（紙の SVG の頭の字が、今刷れば付く題 hypotheses.sheet_title と同じか）。
    紙の置き場の名前（<仮説>_v<版>）は仮説と版の数だけで決まるので、紙の題の決まり（版は組の番号・仮説の印を出さない。11-07〜11-08）が替わっても、
    前に刷った紙が同じ名前で残る。刷った組の台帳（printed_set）は組だけを見るので、組が同じまま題の決まりが替わった紙を拾えなかった
    （11-08: 公開のサイトの虎の頁の PDF が「…仮説 A「…」版 1」で、頁の版は「版 7」だった）。
    照らせない紙（型紙なしの紙・SVG の無い古い紙・版の記録の無い仮説）は今の紙と読む: 刷り直しの口が出続け、紙を出せなくなるのを避けるため。
    字は字の節をつなげ、空白を外して照らす（長い題が 2 行に分かれても同じに読む）"""
    data = hypotheses.load(sid)
    h = next((x for x in data["hypotheses"] if x["id"] == hid), None)
    svg = out_dir(sid) / f"{hid}_v{version}.svg"
    if h is None or h.get("template_id", "") is None or not svg.exists():
        return True
    params, adopted = loop.version_params(sid, hid, version)
    if params is None:
        return True
    shown = re.sub(r"\s", "", html.unescape(re.sub(r"<[^>]+>", "", svg.read_text(encoding="utf-8", errors="replace"))))
    return re.sub(r"\s", "", hypotheses.sheet_title(data, h, version, adopted)) in shown


def mochiyoru_place(sid, photos=True):
    """もちよる のこの玩具の札への道。札が無い玩具は None で、道を出さない（別の目の確かめ 11-08 の止め 4: もちよる に何も無い玩具で頭に着くだけの道にしない）。
    札の錨と道は もちよる の側（techo_site.toy_place・#646）が持つ。photos=False（合言葉なしの場）は public=True で聞く: 公開の場の もちよる は、人が確かめた字か
    写真の札だけを出すので、道もそれに合わせる（もちよる の担当の形）"""
    from . import techo_site

    return techo_site.toy_place(sid, public=not photos)


def make_go(sid):
    """玩具の頁の最初の画面の「つくる」（段 0）。働きは型紙の札の「型紙を見る」と同じで、たたき台の紙を作って窓に出す。
    刷ってある紙が「一番新しい版（loop.latest_version）」で「今の組」の物の時だけ、作り直さずに窓の紙へ行く。
    版が上がった時（人が採った版 2 など）と組が上がった時（雛形の次の組）は、刷る口へ送って一番新しい紙を刷る。
    刷り残しの古い紙を、頁でいちばん目立つ釦が出さないため（本人の方針「最新版が次の人の型紙になる」、J-032。別の目の確かめ 11-06）。"""
    h = hypotheses.sheet_of(sid)
    last = versions_of(sid, h["id"], printed_only=True)
    now = loop.latest_version(sid, h["id"])
    this_set = TEMPLATES[hypotheses.load(sid).get("template", "slider_fan")].SHEET_SET
    # 刷ってある紙の題が今の題でない時（題の決まりが替わる前に刷った紙）も刷る口へ送る（paper_current）
    if last and last[-1] == now and printed_set(sid, h["id"], now) == this_set and paper_current(sid, h["id"], now):
        return f'<p class="road"><a class="btn" href="/toy/{sid}?see={h["id"]}&amp;kind=sheet&amp;v={last[-1]}#win">つくる</a></p>'
    return (f'<form method="post" action="/toy/{sid}/print#win" class="road"><input type="hidden" name="hypothesis" value="{esc(h["id"])}">'
            f'<input type="hidden" name="at" value="win"><button class="btn" data-busy>つくる</button></form>')


def toy_page(sid, look=skin.DEFAULT, errors=(), msg="", asked=None, see=None, kind="", v=0, path=None, photos=True, at="", filled=None, up_key=None, rec_key=None):
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
    songs = "".join(f'<p>{esc(e["text"])}</p>' for e in src.get("transcription", {}).get("entries", []) if not e.get("rejected_by") and e.get("checked_by"))
    who = "・".join(sorted({wording.plain(e["checked_by"]) for e in src.get("transcription", {}).get("entries", []) if not e.get("rejected_by") and e.get("checked_by")}))
    stage = hypotheses.stage(sid)
    stage_note = '<p class="meta"><span class="lb">試作</span>全部の玩具を型紙にする途中の物。名前は作る側の見立てで、まだ確かめていません。</p>' if stage != "必須" else ""
    from . import workshop  # ワークショップで作られた物の写真（本人の言葉 11-07 夜）。公開の場にも出すので photos の線を掛けない
    from . import genga  # 原画と歌（本人の指示 11-06）。頁の全体の絵と歌を 1 つの組にして頭に置く。歌はこの組の中に出す

    from . import kumitate, wa  # 立体の組み立て（本人の決定 11-06。J-033）と、型紙の版（web.wa）

    # 段 3 組み立てを立体で見る: 開いた時に 1 回動かして見せる（本人の答え 11-07 Q6）。頭の「つくる」の行き先を決めるので、頭より先に作る
    rittai_block = kumitate.block(sid, heading=False, tour=True)
    # 題のすぐ後に次へ進む釦を 1 つ（段 0）。行き先は流れの最初の段（本人の言葉 11-08「原図をみて、狂歌を読んで、仮説、たとえ、3D をみたあとに型紙の印刷にすすむ。」・
    # 設計の問い 2 の答え「推しのとおり。」）。前は頭の釦が紙を刷って型紙の窓へ行き、仮説・たとえ・3D を飛ばしていた。紙を刷る口は型紙の窓の中（make_go）。
    # 本人の言葉 11-08「つくるは、仮説の前に「組み立てを立体で見る」を置く。」で最初の段が立体になったので、行き先は立体の段（#kasetsu）。
    # 立体の無い玩具は仮説の段（#kasetsu-fuda）。481-2 の「仮説の段の頭へ」は流れの最初の段という意味で読む（統括の決め 11-08）
    first = "#kasetsu" if rittai_block else "#kasetsu-fuda"
    # 頭の畳み「これまでの記録」は消した（本人の言葉 11-08「つくるは、これまでの記録は消す。」・477「復元の記録などはすべてもちよるに統合する。」）
    hero = (f'<section class="hero">{genga.head(sid, src, photos=photos)}<div>'
            f'<h1>{esc(data["toy"])}</h1>{stage_note}<p class="road"><a class="btn" href="{first}">つくる</a></p>'
            # 作品の札は前の所（題と つくる の後）に、題の塊だけで置く。出典の字は頁の一番下の段（本人の言葉 11-08「文言はページの一番下に」・genga.ndl_credit）。
            # 11-08 に一度、題の塊を原画の部品の縦の段へ移したが、本人の言葉「縦書きは失敗なので前の形に戻す」・答え「広い画面も戻す」で戻した。
            # 図を見る（国立国会図書館）は原画の部品の 1 つの道にまとめた。図鑑の頁とほかのおもちゃの道は外した（本人の言葉「図鑑のページ要らない」
            # 「ほかのおもちゃ、のリンク要らない」）。くずし字を読む は残す
            + skin.artwork_label(data["toy"], src, credit=False)
            + f'<p class="links"><a href="/zukan/{sid}/yomi">くずし字を読む</a></p></div></section>')
    recs = records.all_records(sid)
    recorded = {r["hypothesis_id"] for r in recs}
    # 頁の本体は 原画と立体 → つくる → 型紙 の順だけにする（本人のサイト体験レビュー 11-07 の 3「作るの頁がごちゃごちゃして、同じ物が何回も出る。まとめる」）。
    # 前は「すぐ作る」の節（見出し・説明・断り・輪の図・立体・仮説の札）と「型紙の窓」の節が別にあり、作る節と型紙の置き場が 2 つに見えた。
    # 立体は頭の原画のすぐ後へ（核の体験「絵が立体のおもちゃとなって自分の手のひらで遊べる」）、断りと輪の図と仮説の札は型紙の窓の頭へ寄せる。
    # 「すぐ作る」の見出しは外し、説明の文（輪の図の「切って、折って、組む」の字の出所）は型紙の窓の頭へ移した（新しい字は足さない）。
    # 節の錨 #kasetsu は残す（紙を作れなかった時の文を受ける錨・試験の並び）。
    # 段 3 組み立てを立体で見る（中身は頭の前で作った rittai_block）。段の見出しは h2 にそろえる（字は kumitate.LABEL のまま）。
    # 節の錨 #kasetsu は残す（紙を作れなかった時の文を受ける錨・前からの道・頭の「つくる」の行き先）
    told = head("kasetsu") or ("" if at else note)
    rittai = ((f'<section class="sec" id="kasetsu">{told}' + (f'<h2>{esc(kumitate.LABEL)}</h2>{rittai_block}' if rittai_block else "") + '</section>')
              if rittai_block or told else '<div id="kasetsu"></div>')
    # 真ん中は型紙の版（組の番号。本人の言葉 11-07「バージョンをサイトで明示したい」、窓口の決定 カード 084426）。前は寸法の刻み（wa.current_version）
    ban = wa.set_version(sid, data)
    # 仮説の段の図は、のこす の頁の うつしの輪 の図（本人の言葉 11-08「つくるの仮説にある図は、のこすのうつしの輪の図にする。」・本人の答え「字 1 と絵 A。」の絵）。
    # 字は のこす の頁（techo_site.manabi_box）と同じ（輪の名・本人が採った文 ADOPTED・図と図の下の 1 行。新しい字は足さない）。段の見出し（h2）は 仮説 だけに
    # 保つので、輪の名は h3。錨 #wa は前の輪の図（wa.ring・真ん中に今の型紙の版）から引き継ぐ。型紙の版は札の脇の版の札（下の plate）が出す
    from . import loop_figure

    ring = f'<div class="manabi" id="wa"><h3>{esc(loop_figure.NAME)}</h3><p>{esc(loop_figure.ADOPTED)}</p>{loop_figure.svg()}</div>'
    plate = ""
    for h in [hypotheses.sheet_of(sid)]:
        ev = "".join(evidence_item(e) for e in h["evidence"])
        # 型紙の絵は型紙の窓の 1 か所だけに出し、刷る口は頭の「つくる」1 つにする（本人のサイト体験レビュー 11-07 の 3「同じ物が何回も出る」）。
        # 前はこの札にも紙の小さな絵と「型紙を見る」（紙を作る釦）があり、型紙が 2 か所、刷る口が 3 つ（頭・この札・窓の札）あった。札は仮説の字だけ
        # 札の脇に型紙の版（設計 0.7「型紙の札の脇に、今の版の印を 1 つ」）。字は「型紙の版」と数だけ（エンジンの版と言い分ける。カード 084426）
        plate += (f'<div class="plate"><h3>{esc(hypotheses.shown_name(h))}</h3>'
                  f'<p class="meta"><span class="lb ban">型紙の版 {ban}</span></p><p>{esc(wording.plain(h["how_it_moves"]))}</p><ul>{ev}</ul>'
                  f'<p class="meta">試して見る事: {esc(wording.plain(h["to_measure"]))}</p>{way_tags(ways.labels(ways.of_hypothesis(data, h))) if h.get("params") is not None else ""}'
                  '</div>')
    # 段 3 仮説: 見出し → 前提の断り（「型紙は正解ではなく、AI が考えた仮説」・本人の言葉 11-05。札より前）→ 輪の図（窓口の決め 162346 で残す・
    # 設計の問い 6 の答え「推しのとおり。」で仮説の段のまま）→ 仮説の札（→ 話した考えから作り直す口。考えを話す の口は 11-08 に外した）。
    # 札を作る行（上の for）は替えない（「仮説」の字の直しは別の担当が持つ）。書いて立てる欄は無い（本人の決定 11-05 18:08、J-032 の点 2）
    from . import think_sheet  # 話した考えから、たたき台の紙を作り直す（ループ 1、Issue #335）

    # 考えを話す の口は外した（本人の言葉 11-08「つくるの「考えを話す」は無くす。」・前は設計の問い 4 の答えで仮説の段の中に残していた）。
    # 話した考えから紙を作り直す口（自分の案 OWN の道・ループ 1）は残す。声とカメラの区切りの作り始めは頁の終わりの clips.toy_start
    talk = ""
    if photos and think_sheet.ready(sid):  # 合言葉なしの場（photos=False）と、呼び名がそろっていない玩具では出さない。受け口も閉じている（J-028）
        talk += think_sheet.section(sid, at, head(at))
    kasetsu = (f'<section class="sec" id="kasetsu-fuda"><h2>仮説</h2><p class="premise" id="premise">{esc(PREMISE_PAGE)}</p>{ring}<p class="meta">{esc(ways.NOTE)}</p>'
               f'<div class="plates">{plate}</div>{talk}</section>')
    # 段 6 型紙の窓（型紙の印刷）: 刷る前は窓の中に紙を作る「つくる」1 つ（make_go。刷る口は 1 つ・前は頭の釦）。刷った後は 紙・PDF・つくる（手帖へ）・のこす（案 B）。
    # 型紙の版の歩みは窓の中の閉じた畳み（設計の問い 3 の答え「推しのとおり。」。本人の指示 11-07 の版の歩みは残し、読む量を減らす）
    from . import ban_ayumi

    top, sheet, acts = window(sid, data, see, kind, v, recorded, photos)
    go = make_go(sid)
    printing = "" if sheet and "/print" not in go else go
    # 段の中の順: 見出し「型紙を印刷する」→ 刷る口（刷る前・版が上がった時）と PDF を開いて印刷する → 型紙（紙の絵と札と版の札）→ 版の歩み（閉じた畳み）→
    # 口（つくる・本人の字・のこす）
    # JS の無い画面の聞く口（作りながら見る頁の #ask-form）は、この頁へ答えを返す（play_server の ask）。聞く口の節は外したので、答えだけを窓の頭に出す。
    # 字は前の聞く口の答えの形のまま（「聞いた事: …」と答え）
    answer = (f'<div id="ask-answer" class="notice"><p class="meta">聞いた事: {esc(asked[0])}</p><p>{esc(asked[1])}</p></div>' if asked else "") + head("ask")
    # 見出しは「型紙を印刷する」（本人の言葉 11-08「型紙の窓を「型紙を印刷する」からにして、その直下に PDF を開いて印刷するボタンを置く。」）。前は「型紙の窓」。
    # 見出しの直下は、刷った後は PDF を開いて印刷する（top）、刷る前は紙を刷る「つくる」（printing）。版が上がった時は新しい紙を刷る「つくる」の後に、
    # 前の紙の PDF（前は口の中にあった物を残す）。説明の 2 行はその後ろへ下げた（字は前のまま）
    win = (f'<section class="sec" id="win">{head("win")}{answer}<h2>型紙を印刷する</h2>{printing}{top}<p class="lead">型紙を刷ります。切って、折って、組みます。</p>'
           f'<p class="meta">画面で見て、印刷する前に案を検討する所。</p>{sheet}{fold(ban_ayumi.section(sid))}{acts}</section>')
    # 錨 #tsukuru（前の 作っている途中で困ったら の節）は外した。作りながら見る頁の「← 玩具」は #win（型紙の窓）へ向け直した（tsukuru.py）。
    # 作っている途中で困ったら（聞く口）は外した: 手帖の手順の画面に「こまった」と聞く口が前からある（設計の問い 4 の答え「推しのとおり。」）。
    # 組み方の畳みは外した: 作る時は手帖が 3D と文で 1 手ずつ出す（本人の言葉 477「作成を 3D の手順の解説に従って行い」・設計の問い 5 の答え）。
    # これまでの復元（作った物の記録・ワークショップの写真と感想と話された言葉）は もちよる の玩具ごとの所へ移した（本人の言葉 477）。下の のこそう の段から 1 行で行ける
    # 段の順（本人の言葉 477 と 11-08「つくるは、仮説の前に「組み立てを立体で見る」を置く。」）: 頭（段 1 原図・段 2 狂歌）→ 段 3 立体 → 段 4 仮説 →
    # 段 5 たとえ → 段 6 型紙の窓 → 段 8 のこそう（段 7 作る は手帖）。立体の無い玩具は立体の段が抜けるだけ（錨 #kasetsu の空の div は残る）
    body = hero + rittai + kasetsu + analogy_section(data) + win
    # 段 8 のこす: 試した記録を残す口は のこす（記録の頁）へ寄せた（本人の答え 11-07 夕の Q3）。錨 #kiroku と返事の文（head）は残す: 作りながら見る頁の
    # 組み上がりの札・試した後の紙の断りの「記録の欄へ」・受け口の返事が、この錨へ戻るため。のこすへの道 2（本人の言葉 11-07 夜「できたはのこそう」）
    # を残す（設計の問い 9 の答え）。もちよる のこの玩具の所への 1 行（字は設計の問い 7 の推しの字・本人の答え「推しのとおり。」）
    done = (f'<h2>{esc(naoru.ROUTE_DONE)}</h2>' if naoru.ROUTE_DONE else "") + (f'<p class="meta">{esc(naoru.purpose())}</p>' if naoru.ROUTE_DONE and naoru.purpose() else "")
    body += (f'<section class="sec" id="kiroku">{head("kiroku")}{done}'
             f'<p class="links"><a href="/toy/{esc(sid)}/techo/kiroku">{esc(KIROKU_TO_NOKOSU)}</a></p>'
             + (f'<p class="links"><a href="{esc(place)}">{esc(MOCHIYORU_GO)}</a></p>' if (place := mochiyoru_place(sid, photos)) else "") + '</section>')
    # 頁の足の「型紙の改善の輪」の節は外した（本人の答え 11-07 夕の Q5「型紙の改善の輪は外して、説明の頁と のこす だけにする」。
    # 夕方のレビューの 8「型紙改善の輪と型紙の窓の情報が重なる」）。報告から直した版と次の版を待つ報告は、作る側の様子の頁（/loop/<印>）へ移した。
    # 学ぶ人には、版の歩み（ban_ayumi）が版の並びを、型紙の窓の小さな輪の図が輪の形を見せる。たとえは型紙の窓のすぐ後へ移した（本人の答え Q4）
    # 英語の短い紹介（本人の指示 11-05「実装までやって」、J-030）。頁の足に置く: 日本語の順路を押し下げないため。
    from . import en

    body += en.band(sid)
    body += f'<section class="sec">{foot_links()}</section>'
    # 国立国会図書館デジタルコレクションの出典の字（所蔵・コマ・権利）は頁の一番下（本人の言葉 11-08「国立図書館デジタルコレクションの文言はページの一番下に」）
    body += genga.ndl_credit(sid, src)
    # 声とカメラの区切りの置き場の台本と、頁を開いた時の作り始め（#640）。前は 考えを話す の節の中にあったので、節を外した後も頁に 1 回置く（web.clips.toy_start）
    from . import clips

    body += clips.toy_start(sid)
    if note and note not in body:  # 知らない印や、欄が出ていない時も、文を落とさない
        body = body.replace('id="kasetsu">', f'id="kasetsu">{note}', 1)
    return skin.shell(data["toy"], FOLD_STYLE + body + FOLD_SCRIPT, look, "", path)
