"""図鑑の頁（docs/features.json の f15、決定は docs/process/decisions/J016-zukan-labels.md）。

判断の芯:
- 図鑑に出す文は、どれも原文の引用／仮説／観察の印を持つ。印は画面にも出し、組み立てた文の一覧を
  labels.check（F6.label）に通してから描く。1 文でも落ちれば頁を描かない（印の無い文を公開しない、J-016）。
- 原文の引用は、人が確かめた歌の読みだけ（checked_by がある物）。人が採らなかった読み（rejected_by）は出さない。
  labels.source_lines は確かめていない読みも候補に残すので、ここでさらに確かめた物だけに絞る。絞らないと、
  確かめていない読みが 1 つあるだけで頁ごと描けなくなり、公開できる歌まで隠れるため。
- 仮説の名前と動かし方はいつも出す（本人の決定 11-05、#242「予想の段を無くして、すぐ作る形にする」）。
  答えに読まれない事は、仮説の印（J-016）で守る。
- 観察は人が入れた記録から作る（records.py）。結果の値をそのまま書き、成績や順位にしない（J-025）。仮説は字（A の紙）だけで指し、
  名前や動かし方を観察の文に混ぜない。記録の字は再現ギャラリー（gallery.py）が出しているのと同じ範囲。
- 文言は検査しない（本人の判断、J-016）。飾りの文は作らない。見た目は日本画展の展示（looks.py の tenji）に揃えた白い地で、文字は少なく。
"""
import html
import json
import re

from omochae import hypotheses, labels, records
from omochae.hypotheses import ROOT

from . import wording
from .skin import TAP_FLOOR, page_title

QUOTE, HYPO, OBS = labels.LABELS

# 色は皮の変数（skin.SKINS）に乗せ、変数が無い時は今までの白い展示の値に落ちる。黒のジンの皮で /zukan を開いても読めるようにするため（11-05）。
STYLE = """
body.zukan{margin:0;background:var(--bg,#fcfcfa);color:var(--fg,#2b2722);font-family:"Noto Serif CJK JP","Noto Serif JP","Hiragino Mincho ProN","Yu Mincho",serif;font-feature-settings:"palt" 1}
.zukan main{max-width:1100px;margin:0 auto;padding:10vh 5vw 14vh;box-sizing:border-box}
.zukan a{color:var(--accent,#6b4f2a);text-decoration:none;border-bottom:1px solid color-mix(in srgb,var(--accent,#6b4f2a) 40%,transparent)}
.zukan .nav a:not([aria-current]){border-bottom:0}
.zukan h1{font-weight:400;font-size:clamp(30px,4vw,48px);letter-spacing:.5em;margin:0 0 8px}
.zukan p.nav{font-size:12px;letter-spacing:.2em;color:var(--mute,#6f665a);display:flex;gap:18px;flex-wrap:wrap;margin:0 0 6vh}
.zukan .toy{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.2fr);gap:5vw;padding:8vh 0;border-top:1px solid var(--rule,#ebe8e2);align-items:start}
.zukan .toy figure{margin:0;background:var(--paper,#fffefc);border:1px solid var(--frame,#d8cdb6);padding:3%;box-shadow:0 40px 60px -30px var(--shadow,rgba(70,55,35,.35))}
.zukan .toy figure img{width:100%;display:block}
.zukan .toy h2{font-weight:400;font-size:clamp(24px,2.6vw,38px);letter-spacing:.2em;margin:0 0 20px}
.zukan .song{writing-mode:vertical-rl;height:min(40vh,360px);font-size:clamp(16px,1.5vw,20px);line-height:2.2;letter-spacing:.12em;float:right;margin:0 0 12px 24px}
.zukan ul{list-style:none;padding:0;margin:0 0 22px}
.zukan li{font-size:14px;line-height:2;letter-spacing:.04em;border-left:1px solid var(--frame,#b9a982);padding-left:12px;margin:0 0 6px}
.zukan .lb{display:inline-block;font-size:12px;letter-spacing:.2em;color:var(--mute,#6f665a);border:1px solid var(--frame,#d8cdb6);padding:0 8px;margin-right:10px}
.zukan .meta{font-size:12px;color:var(--mute,#6f665a);letter-spacing:.08em;line-height:1.9}
.zukan .links{font-size:13px;letter-spacing:.12em;display:flex;gap:16px;flex-wrap:wrap}
.zukan .more{padding:8vh 0;border-top:1px solid var(--rule,#ebe8e2)}.zukan .more h2{font-weight:400;letter-spacing:.2em}
.zukan .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:4px 18px}.zukan .grid li{margin:0}
@media (max-width:760px){.zukan .toy{grid-template-columns:1fr}.zukan .song{writing-mode:horizontal-tb;height:auto;float:none;margin:0 0 12px}}
"""


class Unlabeled(ValueError):
    """F6.label に落ちた文がある。頁を描かない。"""


def esc(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def _source(sid):
    return json.loads((ROOT / "data/sources" / f"{sid}.json").read_text(encoding="utf-8"))


def quote_lines(src):
    # 採らなかった読みは source_lines が外す。その上で確かめた読みだけを残す（理由はファイル冒頭）。
    return [{**e, "label": QUOTE} for e in labels.source_lines(src) if e.get("checked_by")]


def record_title(r, data):
    """記録の見出し。玩具の頁の札と図鑑の行で同じ書き方にする（#130）。字だけで仮説を指し、仮説の名前は書かない。"""
    h = next((x for x in data["hypotheses"] if x["id"] == r["hypothesis_id"]), None)
    who = f"仮説 {hypotheses.letter(h)} の紙" if h else "自分の仮説の紙"
    word = records.result_word(r)
    return f"{who}・{word}" if word else who


def record_date(r):
    """試した日を「11 月 5 日」の形にする。形の違う古い記録は、書いてあるままを出す。"""
    when = r.get("tried_on") or str(r.get("recorded_at", ""))[:10]
    m = re.fullmatch(r"\d{4}-(\d{2})-(\d{2})", when)
    return f"{int(m[1])} 月 {int(m[2])} 日" if m else when


def observation_lines(sid, data):
    """記録 1 件を観察の文 1 つにする。番号は札へ引けるように最後に残す。"""
    return [{"text": f"{record_title(r, data)}（{record_date(r)}・{wording.record_no(r['id'])}）", "label": OBS, "record_id": r["id"]} for r in records.all_records(sid)]


def hypothesis_lines(sid, data, photos=True):
    """どれも試していない考えなので、仮説の印を付ける（status も添える）。出すのはたたき台の 1 つだけ（J-032。説を羅列しない）。"""
    out = [{"text": f"仮説 {hypotheses.letter(h)} {h['name']}: {wording.plain(h['how_it_moves'])}", "label": HYPO} for h in data["hypotheses"] if h["id"] == data.get("sheet")]
    from api.words import spoken_own_ids  # 話した考えから採った案は出さない（ループ1、Issue #335。記録に結ぶ前の字は学ぶ人の頁に出さない決まり）

    spoken = spoken_own_ids(sid)
    # 合言葉なしで開いた場では、書いて立てた仮説の文も出さない: 人ごとに分かれておらず、文の中の名前は機械で落とせない（J-028、#336）。
    own = hypotheses.own_hypotheses(sid) if photos else []
    out += [{"text": f"あなたの仮説「{h['name']}」: {h['how_it_moves']}", "label": HYPO} for h in own if h["id"] not in spoken]
    return out


def lines_for(sid, photos=True):
    """その玩具の図鑑の文を、印ごとに返す。予想の段を外した（本人の決定 11-05、#242）ので、仮説はいつも出す。"""
    data, src = hypotheses.load(sid), _source(sid)
    return {"toy": data["toy"], "quotes": quote_lines(src), "observations": observation_lines(sid, data),
            "hypotheses": hypothesis_lines(sid, data, photos), "holding": src.get("holding", "")}


def guard(lines):
    """公開の前の床。落ちた文があれば描かずに止める（J-016「図鑑を作る時に、公開の前にこの床を通す」）。"""
    failures = labels.check(lines)
    if failures:
        raise Unlabeled("; ".join(f.line() for f in failures))
    return lines


def _items(lines):
    return "".join(f'<li><span class="lb">{esc(x["label"])}</span>{esc(x["text"])}</li>' for x in lines)


def toy_section(sid, link_title=False, photos=True):
    z = lines_for(sid, photos)
    guard(z["quotes"] + z["observations"] + z["hypotheses"])
    has_pic = (ROOT / "out/sources" / f"{sid}.jpg").exists()
    pic = f'<figure><img src="/picture/{esc(sid)}" alt="{esc(z["toy"])}の図"><figcaption class="meta">{esc(z["holding"])}</figcaption></figure>' if has_pic else "<div></div>"
    songs = "".join(f'<p class="song">{esc(q["text"])}</p><p class="meta"><span class="lb">{esc(q["label"])}</span>確かめた人: {esc(wording.plain(q["checked_by"]))}</p>'
                    for q in z["quotes"])
    obs = f"<ul>{_items(z['observations'])}</ul>" if z["observations"] else '<p class="meta">試した記録はまだありません</p>'
    hyp = f"<ul>{_items(z['hypotheses'])}</ul>"
    title = f'<a href="/zukan/{esc(sid)}">{esc(z["toy"])}</a>' if link_title else esc(z["toy"])
    return (f'<section class="toy" id="{esc(sid)}">{pic}<div><h2>{title}</h2>{songs}'
            f'<p class="meta">試した記録</p>{obs}<p class="meta">仮説</p>{hyp}'
            f'<p class="links"><a href="/toy/{esc(sid)}">玩具の頁</a><a href="/zukan/{esc(sid)}/yomi">くずし字を読む</a><a href="/toy/{esc(sid)}/techo">手帖</a><a href="/gallery">作った物</a></p></div></section>')


def _page(title, body, look=None, path="/zukan"):
    """look があれば皮の骨（skin.shell）に載せる（入口で選んだ皮を図鑑まで続ける、11-05 の作り直し）。
    自前の帯（NAV）は頭の帯と重なるので外す。look が無い時は今までの 1 枚の頁（試験と書き出しはこちら）。"""
    if look:
        from . import skin

        return skin.shell(title, body.replace(NAV, ""), look, "/zukan", path, STYLE, "zukan")
    return ('<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{esc(page_title(title))}</title><style>{STYLE}{TAP_FLOOR}</style><body class="zukan"><main>{body}</main></body></html>')


NAV = '<p class="nav"><a href="/">入口</a><a href="/zukan">図鑑</a><a href="/gallery">作った物</a></p>'
LEAD = '<p class="meta">文にはどれも印があります。原文の引用は人が確かめた読み、仮説は試していない考え、観察は人が残した記録です。</p>'


def index_page(sids, look=None, photos=True):
    """必須の 2 種は今までどおり 1 つずつ大きく並べる。全部を作る線で足した試作の玩具（本人の指示 11-04）は、その下に小さな札で並べる。
    100 を超える玩具を全部大きく並べると、入口から見たい物に届かないため。試作の札は名前が確かめ待ちである事も添える。"""
    main = [s for s in sids if hypotheses.stage(s) == "必須"]
    rest = [s for s in sids if hypotheses.stage(s) != "必須"]
    body = "".join(toy_section(s, link_title=True, photos=photos) for s in main)
    if rest:
        cards = "".join(f'<li><a href="/zukan/{esc(s)}">{esc(hypotheses.load(s)["toy"])}</a> <span class="meta">{esc(wording.frame(s))}</span></li>' for s in rest)
        body += (f'<section class="more" aria-label="ほかの玩具"><h2>ほかの玩具</h2><p class="meta"><span class="lb">試作</span>'
                 f'全部の玩具を型紙にする途中の {len(rest)} 種。名前は作る側の見立てで、まだ確かめていません。</p><ul class="grid">{cards}</ul></section>')
    return _page("うつし · 図鑑", f"<h1>図鑑</h1>{NAV}{LEAD}" + body, look)


def toy_zukan(sid, look=None, photos=True):
    return _page(f"うつし · 図鑑 · {hypotheses.load(sid)['toy']}", f"<h1>図鑑</h1>{NAV}{LEAD}" + toy_section(sid, photos=photos), look, f"/zukan/{sid}")
