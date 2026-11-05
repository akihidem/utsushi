"""くずし字を読む頁（docs/features.json の f14、調べと決め事は docs/process/research/25-kuzushi-reading.md）。

判断の芯:
- 読みの練習なので、先に自分の読みを書き、その後で人が確かめた読みを開く。玩具の予想の段を外した（#242）後も、この順は残す（本人の言葉は玩具の予想の段の話で、読みの練習には触れていない）。
  GET の頁には確かめた読みを出さない。書いた読みを POST で受けた応答の中でだけ開く。
- 書いた読みは保存しない。応答の頁に映すだけで、記録の置き場（OMOCHAE_DATA）にもログにも書かない。
  くずし字を読む事は試しの記録（records）と違い、紙の輪の中の段ではない。残す形は本人が決めていない（research/25）。
- 比べるが採点しない（J-025、philosophy.md）。点・○×・「合っていた」の言葉を出さない。違って読めた字に印を付け、
  二つの読みを横に並べるだけ。どちらの字が元の本に近いかも言わない（確かめた読みも、割れた中から人が決めた物のため）。
- 人が採らなかった読み（rejected_by）は、この頁のどこにも出さない。図鑑（J-016、tests/test_zukan.py）と同じ線で、
  割れた事は「どの複写の読みを誰が採ったか」だけで書き、採らなかった字の並びを出さない。
  checked_scope は割れた二つの語をそのまま書いているので、画面には出さない。
- 文には図鑑と同じ 3 つの印（F6.label）を付け、labels.check に通してから描く。書いた人の読みは「観察」の印にする
  （その人が絵から読んだ事で、試していない考え＝仮説とは違う。この印の当て方は本人に確かめていない、research/25）。
- 活字の読み（printed_text）は「原文の引用」にしない。活字の文は作る側が複写から読んだ物で、本人が確かめたのは割れた語と表記だけのため。
  「観察」として、誰が読んだかを添えて出す。
"""
import difflib
import html
import json

from omochae import labels
from omochae.hypotheses import ROOT

from . import wording, zukan
from .skin import TAP_FLOOR, page_title

QUOTE, HYPO, OBS = labels.LABELS
MAX_READING = 200  # 歌 1 首は 31 字ほど。長い貼り付けで頁を膨らませないための上限

# 歌の書かれた所の枠。out/sources/<sid>.jpg（NDL の IIIF の頁の切り出し、1600×2656）に対する % で x, y, 幅, 高さ。
# 作る側が画像を見て、歌の行とふりがなが全部入り、玩具の絵がなるべく入らない所を選んだ（決め方と確かめ方は research/25）。
SONG_BOX = {
    "NDL-1187053-R0000005-L": (15, 25, 77, 27),
    "NDL-1187053-R0000014-R": (10, 29, 70, 34),
}

STYLE = zukan.STYLE + """
.zukan .crop{position:relative;overflow:hidden;width:100%;background:#fffefc;border:1px solid #d8cdb6;box-shadow:0 40px 60px -30px rgba(70,55,35,.35)}
.zukan .crop img{position:absolute;display:block;max-width:none}
.zukan .yomi{display:grid;grid-template-columns:minmax(0,1.4fr) minmax(0,1fr);gap:5vw;padding:6vh 0;border-top:1px solid #ebe8e2;align-items:start}
.zukan textarea{width:100%;box-sizing:border-box;min-height:6em;font:inherit;font-size:18px;line-height:1.9;padding:10px;border:1px solid #d8cdb6;background:#fffefc;color:inherit}
.zukan button{font:inherit;font-size:14px;letter-spacing:.2em;padding:8px 22px;margin-top:12px;border:1px solid #6b4f2a;background:#fffefc;color:#6b4f2a;cursor:pointer}
.zukan .pair{font-size:clamp(18px,1.8vw,22px);letter-spacing:.12em;line-height:2.2;word-break:break-all}
.zukan mark.d{background:none;color:inherit;border-bottom:2px solid #b06a3b;padding:0 1px}
@media (max-width:760px){.zukan .yomi{grid-template-columns:1fr}}
"""


def esc(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def crop_html(sid, alt):
    """歌の所だけを大きく見せる。画像は 1 枚のまま CSS で切る（新しく画像を作らず、NDL へも取りに行かない）。

    枠の外は overflow で隠す。img の幅・位置は枠の幅と高さに対する % で決まるので、画面の幅が変わっても同じ所が出る。
    """
    x, y, w, h = SONG_BOX[sid]
    W, H = 1600, 2656
    ratio = f"{w * W} / {h * H}"
    return (f'<div class="crop" style="aspect-ratio:{ratio}"><img src="/picture/{esc(sid)}" alt="{esc(alt)}の歌の所" '
            f'style="width:{100 * 100 / w:.3f}%;left:{-100 * x / w:.3f}%;top:{-100 * y / h:.3f}%"></div>')


def zoom_link(src, sid):
    """NDL の IIIF で同じ所を高い解像度で開くリンク。見開きに対する % へ直して api.tools.zoom_url に渡す（頁の外へはみ出さない検査をそのまま使う）。"""
    from api.tools import ToolInputError, zoom_url

    x, y, w, h = SONG_BOX[sid]
    off = 0 if src.get("side") == "L" else 50
    try:
        return zoom_url(src, off + x / 2, y, w / 2, h, width=1600)
    except (ToolInputError, KeyError):
        return ""


def _checked(src):
    return zukan.quote_lines(src)


def split_lines(src):
    """読みが割れた事と、誰がどう決めたかを観察の文にする。採らなかった読みの字の並びは入れない（ファイル冒頭）。"""
    entries = src.get("transcription", {}).get("entries", [])
    took = [e for e in entries if e.get("checked_by") and not e.get("rejected_by")]
    left = [e for e in entries if e.get("rejected_by")]
    out = []
    if took and left:
        books = " と".join(sorted({f"本 {e.get('set')}" for e in entries if e.get("set")}))
        out.append({"text": f"作る側が読んだ本（{books}）では、この歌の一部の読みが分かれていました（作る側の記録）。", "label": OBS})
        for e in took:
            out.append({"text": f"{wording.plain(e['checked_by'])}が {e.get('checked_at') or '日付不明'} に、本 {e.get('set')}（頁 {e.get('page')}）の読みに決めました。", "label": OBS})
        out.append({"text": f"もう一方の読みは記録に残してありますが、{wording.MAKER}が選ばなかった読みなので、この頁には出しません。", "label": OBS})
    for e in took:
        if e.get("printed_text"):
            out.append({"text": f"本 {e.get('set')} の頁 {e.get('page')} の見出しに印刷された字は「{e['printed_text']}」です（作る側が本から読んだ文）。", "label": OBS})
            out.append({"text": f"上の「人が確かめた読み」とは字が違う所があります。{wording.MAKER}は 2026-11-04 に、自分で確かめた書き方で出すと決め、印刷された字の文は記録に残しました。", "label": OBS})
    return out


def _norm(s):
    return "".join(str(s).split())


def diff_marks(mine, theirs):
    """二つの読みの、違って読めた字に印を付けた HTML を返す。空白は比べない（ふりがなや行の切れ目の書き方の違いを数えないため）。

    戻り値の 3 つ目は違った所の有無だけで、数や割合は返さない（点にしないため）。
    """
    a, b = _norm(mine), _norm(theirs)
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    ha, hb, differs = [], [], False
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            ha.append(esc(a[i1:i2]))
            hb.append(esc(b[j1:j2]))
        else:
            differs = True
            if i2 > i1:
                ha.append(f'<mark class="d">{esc(a[i1:i2])}</mark>')
            if j2 > j1:
                hb.append(f'<mark class="d">{esc(b[j1:j2])}</mark>')
    return "".join(ha), "".join(hb), differs


def _li(line, inner=None):
    return f'<li><span class="lb">{esc(line["label"])}</span>{inner if inner is not None else esc(line["text"])}</li>'


NAV = '<p class="nav"><a href="/">入口</a><a href="/zukan">図鑑</a><a href="/gallery">作った物</a></p>'


def _page(title, body, look=None, path="/zukan"):
    """look があれば皮の骨に載せる（図鑑と同じ理由、11-05）。look が無い時は今までの 1 枚の頁。"""
    if look:
        from . import skin

        return skin.shell(title, body.replace(zukan.NAV, ""), look, "/zukan", path, STYLE, "zukan")
    return ('<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{esc(page_title(title))}</title><style>{STYLE}{TAP_FLOOR}</style><body class="zukan"><main>{body}</main></body></html>')


def _form(sid, mine=""):
    return (f'<form method="post" action="/zukan/{esc(sid)}/yomi">'
            f'<p class="meta">読めた字だけでかまいません。読めない字は □ のまま書いてください。書いた読みは、どこにも残しません。</p>'
            f'<textarea name="mine" maxlength="{MAX_READING}" aria-label="あなたの読み">{esc(mine)}</textarea>'
            f'<button type="submit">書いた読みと並べる</button></form>')


def page(sid, mine=None, msg="", look=None):
    """mine が None なら、書く前の頁（確かめた読みを出さない）。文字があれば、並べて見せる頁。"""
    data = json.loads((ROOT / "data/hypotheses" / f"{sid}.json").read_text(encoding="utf-8"))
    src = json.loads((ROOT / "data/sources" / f"{sid}.json").read_text(encoding="utf-8"))
    toy = data["toy"]
    has_pic = sid in SONG_BOX and (ROOT / "out/sources" / f"{sid}.jpg").exists()
    pic = crop_html(sid, toy) if has_pic else '<p class="meta">手元に絵がありません</p>'
    z = zoom_link(src, sid) if sid in SONG_BOX else ""
    pic += f'<p class="meta">{esc(src.get("holding", ""))}' + (f'　<a href="{esc(z)}">同じ所を大きく（国立国会図書館）</a>' if z else "") + "</p>"
    head = f'<h1>くずし字を読む</h1>{NAV}<p class="meta"><a href="/zukan/{esc(sid)}">{esc(toy)}</a>の絵の、歌の所です。</p>'
    note = f'<p class="meta">{esc(msg)}</p>' if msg else ""
    if mine is None:
        body = f'<section class="yomi"><div>{pic}</div><div>{note}{_form(sid)}</div></section>'
        return _page(f"うつし · くずし字を読む · {toy}", head + body, look, f"/zukan/{sid}/yomi")

    checked = _checked(src)
    reader = {"text": mine, "label": OBS}
    splits = split_lines(src)
    # 床を通してから描く（J-016）。書いた人の読みも 1 つの文として通す。
    zukan.guard([reader] + checked + splits)
    rows = []
    for q in checked:
        mh, th, differs = diff_marks(mine, q["text"])
        rows.append('<ul class="pair">' + _li(reader, "あなたの読み　" + mh) + _li(q, "人が確かめた読み　" + th) + "</ul>")
        rows.append(f'<p class="meta">確かめた人: {esc(wording.plain(q["checked_by"]))}。' +
                    ("線の付いた字は、ここが違って読めた所です。" if differs else "二つの読みは、同じ字の並びでした。") + "</p>")
    if not checked:
        rows.append('<ul class="pair">' + _li(reader) + '</ul><p class="meta">人が確かめた読みは、まだありません。</p>')
    how = f'<p class="meta">読みが分かれた事と、決めた事</p><ul>{"".join(_li(x) for x in splits)}</ul>' if splits else ""
    body = (f'<section class="yomi"><div>{pic}</div><div>{"".join(rows)}{how}'
            f'<p class="meta">もう一度書く</p>{_form(sid, mine)}</div></section>')
    return _page(f"うつし · くずし字を読む · {toy}", head + body, look, f"/zukan/{sid}/yomi")
