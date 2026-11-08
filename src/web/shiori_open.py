"""しおりの開く道（/s/<印>）。設計は grove の state/techo-card-20261108/README.md の 2″・2‴・6 の 2・7（別の目の検品 4 回）。

本人の決め（11-08）: 手帖の鍵は「しおり」・「しおりに書いてある絵を押す」・しおりそのものが鍵の形で「この形でよい」。
統括の決め（11-08）: しおりの道 /s/<印> の GET と POST だけを合言葉の門の外にする。合言葉の値そのものは端末に渡さず、門は開いた画面の印
（utsushi_s）も通す（別の目の止め S1 の代わりの形）。「とじる」はサーバの側でも開いた画面の印を消す（止め S2）。

判断の芯:
- **門の外は 2 つの道だけ。** 見分けは play_server._gate の頭の PATH の fullmatch（? より前の道）。startswith にしないのは、% の入った字・
  末の /・/s/close などを門の中に残すため。絵の頁が要る物（9 つの絵・字の形）は頁の中に入れ、絵のために門の外の道を増やさない。
- **当たる前の頁には、記録の番号・並び・門の中への道を出さない。** 帯と足を外した素の頁にする（合言葉の門の断りの頁と同じ形）。
- **止めは cookie の前に効く。** 公開の場の断り（照らさず数えない）→ フォームの Origin の照らし → 書き込みの止め（WRITE_PATHS）→
  台帳の止め 3 つ（shiori.check）の後で、当たった時だけ cookie を渡す。
- **画面の cookie は「しおりの印.開いた画面の印」。** 合言葉の cookie（utsushi_k）は渡さない: 合言葉はその場の全部の頁を長く開ける値で、
  HttpOnly でも持ち主は開発の道具で読めるので、拾った人の端末に写すと ?k= のリンクにして配れてしまう（止め S1）。
  Max-Age を付けないが、ブラウザの「前回の続き」で残る事があるので、切れはサーバの側の 20 分（shiori.IDLE）に任せる。
- 9 つの絵の並び（PICTURE_IDS）は仮の 1 か所の値。どの玩具にするかは、しおりの紙の PR で本人に確かめる。刷った後は替えない
  （押す順は 0〜8 の番号で持つので、並びを替えると刷ったしおりが開かなくなる）。
"""
import base64
import functools
import io
import re

from omochae import hypotheses, records, shiori

from . import skin as skinmod
from .skin import esc

COOKIE = "utsushi_s"
PATH = re.compile(r"/s/([A-Za-z0-9_-]{22})")
CLOSE_PATH = "/s/close"
# 仮の 9 つ（紙の PR で本人に確かめる・刷った後は替えない）。形の違う玩具を混ぜ、小さい絵でも見分けやすくした
PICTURE_IDS = ("NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R", "NDL-1187053-R0000004-L", "NDL-1187053-R0000007-L", "NDL-1187053-R0000007-R",
               "NDL-1187053-R0000006-L", "NDL-1187053-R0000010-R", "NDL-1187053-R0000013-L", "NDL-1187053-R0000013-L-3")
PICTURE_PX = 96  # 頁に埋める小さい絵の幅。9 枚で数十 KB に収め、門の外の道を増やさない

TITLE = "しおり"
PUBLIC_REFUSE = "このしおりは、ワークショップの場で開きます。"
CANNOT = "このしおりは開けません。進め役に聞いてください。"
LEAD = "しおりの裏の ①②③ の順に、絵を押してください。"
WRONG = "ちがう順でした。もう一度、押してください。"
WAIT = "少し待ってから、もう一度押してください。"
NTH = ("1 つめ", "2 つめ", "3 つめ")
OPEN = "ひらく"
OPENED = "しおりの記録"
NONE_YET = "まだ記録はありません。"
GO_ON = "続きをつくる"
CLOSE = "とじる"
CLOSE_NOTE = "つかいおわったら「とじる」を押してください。"

STYLE = (".shiori-pics{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;max-width:360px}"
         ".shiori-pics button{min-height:96px;padding:4px;border:1px solid var(--frame);background:var(--field);color:var(--fg);font:inherit}"
         ".shiori-pics button[aria-pressed=true]{outline:3px solid #b5302a}"
         ".shiori-pics img{display:block;width:100%;height:auto}")


@functools.lru_cache(maxsize=None)
def _picture(sid):
    """頁に埋める小さい絵（data: の JPEG）。原画の写しが無い機械（試験など）では None で、釦は玩具の名前だけになる。"""
    from . import toys

    raw = toys.small_picture(sid, "small")
    if not raw:
        return None
    from PIL import Image

    with Image.open(io.BytesIO(raw)) as im:
        im = im.convert("RGB")
        im.thumbnail((PICTURE_PX, PICTURE_PX * 2))
        out = io.BytesIO()
        im.save(out, "JPEG", quality=70)
    return "data:image/jpeg;base64," + base64.b64encode(out.getvalue()).decode("ascii")


def _bare(body, look):
    """帯と足の無い素の頁（門の中への道を出さないため。skin.notice の bare と同じ外し方）。"""
    page = skinmod.shell(TITLE, body, look, extra_style=STYLE, foot=" ")
    return page.replace(skinmod.nav(look), "", 1)


def notice(reason, look):
    return skinmod.notice(TITLE, reason, look, links=(), bare=True)


def picture_page(token, look, msg=""):
    """当たる前の頁: 9 つの絵と、押した順を送るフォーム。記録の番号・並び・門の中への道は出さない。"""
    names = [hypotheses.load(sid)["toy"] for sid in PICTURE_IDS]
    pics = "".join(
        f'<button type="button" data-i="{i}" aria-pressed="false">'
        + (f'<img src="{_picture(sid)}" alt="{esc(name)}">' if _picture(sid) else esc(name)) + '</button>'
        for i, (sid, name) in enumerate(zip(PICTURE_IDS, names)))
    picks = "".join(f'<label>{esc(n)} <select name="o{k + 1}">' + "".join(f'<option value="{i}">{esc(name)}</option>' for i, name in enumerate(names))
                    + '</select></label> ' for k, n in enumerate(NTH))
    say = f'<p role="status" id="msg">{esc(msg)}</p>' if msg else ""
    # 押した順は台本が隠した欄に入れ、3 つ押したら送る。台本の無い画面では、3 つの選びの欄で送る（noscript）
    script = ("<script>(()=>{const f=document.getElementById('shiori-go'),o=f.elements.order,got=[];"
              "document.querySelectorAll('.shiori-pics button').forEach(b=>{b.onclick=()=>{if(got.includes(b.dataset.i))return;"
              "got.push(b.dataset.i);b.setAttribute('aria-pressed','true');if(got.length===3){o.value=got.join(',');f.submit()}}})})()</script>")
    body = (f'<section class="sec"><h1>{esc(TITLE)}</h1>{say}<p>{esc(LEAD)}</p>'
            f'<form method="post" action="/s/{esc(token)}" id="shiori-go"><input type="hidden" name="order" value="">'
            f'<div class="shiori-pics">{pics}</div>'
            f'<noscript><p>{picks}<button type="submit">{esc(OPEN)}</button></p></noscript></form></section>{script}')
    return _bare(body, look)


def opened_page(cookie, look):
    """開いた画面の頁: そのしおりの記録の並び・続きをつくる道・とじる。取り下げと「使えなくする」の口は出さない（2‴ の 3）。"""
    rows, recs = "", {x["id"]: x for x in records.all_records()}  # 取り下げた記録は all_records に出ないので、並びにも出ない
    for rid in shiori.records_of(cookie):
        r = recs.get(rid)
        if r is None:
            continue
        sid = r["source_id"]
        # 記録への道は手帖の記録の頁のその記録の札へ（#657 でつくるの頁から記録の札を外した。前の /toy/<印>#<記録> は行き先の札が無い・統括の確かめ 11-08）
        rows += (f'<li><a href="/toy/{esc(sid)}/techo/kiroku#{esc(rid)}">{esc(hypotheses.load(sid)["toy"])}</a>　{esc(records.result_word(r))}'
                 f'　<a href="/toy/{esc(sid)}/techo">{esc(GO_ON)}</a></li>')
    body = (f'<section class="sec"><h1>{esc(OPENED)}</h1><p>{esc(CLOSE_NOTE)}</p>'
            + (f'<ul>{rows}</ul>' if rows else f'<p>{esc(NONE_YET)}</p>')
            + f'<form method="post" action="{CLOSE_PATH}"><button type="submit">{esc(CLOSE)}</button></form></section>')
    return skinmod.shell(OPENED, body, look, extra_style=STYLE)


def cookie_line(value, secure):
    """画面の cookie の行。Max-Age を付けない（閉じると消える形）。値が空なら消す。合言葉の cookie は、ここでもどこでも渡さない（止め S1）。"""
    return ("Set-Cookie", f"{COOKIE}={value}; Path=/; HttpOnly; SameSite=Lax" + ("; Secure" if secure else "") + ("" if value else "; Max-Age=0"))


def order_of(form):
    """押した順。台本の欄（"3,1,5"）か、台本の無い画面の 3 つの選び（o1〜o3）。形は台帳が見る（読めない物は外れに数える）。"""
    if form.get("order", "").strip():
        return form["order"].split(",")
    picks = [form.get(f"o{k}") for k in (1, 2, 3)]
    return picks if all(p is not None for p in picks) else None
