"""入口のルックブック（J-024）。本人が 5 案を見比べ、A 大判写真集と C 縦読みのジンを残した（2026-11-04）。
見開き型・冊子型・B 和綴じ帖は外した。A が入口（/）で、C は /look/zine から見る。

判断の芯: 案ごとに佇まい（表紙・見開きの構成・題の組み方）だけを変え、守る線は同じにする。
新しい絵は作らず、NDL の図の頁とその寄りだけを使う。歌は人が確かめた読みだけを引用の印つきで出す。
仮説は出さない（予想が先、F9.prediction）。どの案も最後は同じ玩具の頁（/toy/）へ入る。
"""
from omochae import hypotheses

from .play_server import ROOT, esc, page, source, sources

LOOKS = {
    "taiban": "A 大判写真集",
    "zine": "C 縦読みのジン",
}


def switch(current):
    """残した 2 案を行き来する切り替え。今いる案は太字にする。A は入口（/）と同じ頁。"""
    items = [("/", LOOKS["taiban"]), ("/look/zine", LOOKS["zine"])]
    current = "/" if current == "/look/taiban" else current
    links = "｜".join(f"<b>{esc(n)}</b>" if u == current else f'<a href="{u}">{esc(n)}</a>' for u, n in items)
    return f'<nav class="switch">{links}<span class="cap">本人が残した 2 案（J-024）</span></nav>'


def toys():
    """図の写しが手元に無い玩具も並べる。A は入口なので、写しの有無で玩具が消えると入れなくなるため。"""
    out = []
    for s in sources():
        src = source(s)
        song = [e["text"] for e in src.get("transcription", {}).get("entries", []) if not e.get("rejected_by") and e.get("checked_by")]
        out.append({"sid": s, "toy": hypotheses.load(s)["toy"], "song": song, "holding": src.get("holding", ""),
                    "pic": (ROOT / "out/sources" / f"{s}.jpg").exists(), "image_url": src.get("image_url", "")})
    return out


def _bg(sid, pos="50% 50%", size="cover"):
    # 写しが無い時は地の色だけにし、図の場所には国立国会図書館への道を別に置く（_nopic）。
    if not (ROOT / "out/sources" / f"{sid}.jpg").exists():
        return "background-color:#d9d2c3"
    return f"background-image:url(/picture/{sid});background-position:{pos};background-size:{size};background-repeat:no-repeat"


def _nopic(t):
    return "" if t["pic"] else f'<p class="cap"><a href="{esc(t["image_url"])}">図を見る（国立国会図書館）</a></p>'


QUOTE = "原文の引用。確かめた人: 本人"

# 見比べるための写しを撮る補助。?only=<節の id> で、その節だけを画面の頭に出す。
# なぜ: 縦に流れる案は、頭からしか写しを撮れず、途中の見開きを並べて比べられないため。ふだんの閲覧には効かない。
ONLY = """<script>(()=>{const id=new URLSearchParams(location.search).get('only');if(!id)return;
const st=document.createElement('style');st.textContent='section:not(#'+CSS.escape(id)+'),.switch,.ab-end,main>p{display:none!important}';document.head.appendChild(st)})();</script>"""

# ---------------------------------------------------------------- A 大判写真集（参照のルックブックの再現）
# 本人の指示（2026-11-04）: 参照の X の投稿のルックブックの再現を、A の実装の基準にする。
# 参照は、白いリングバインダーを真上から撮った見開きを縦に並べる形（research/19 に観察を書いた）。
# 写したのは組み方だけ: 綴じ金具とバインダーの縁、見開きの型（全面の写真と白地の小物、平置きと番号の一覧、
# 見開きをまたぐ 1 枚、文字の頁と色見本の列、余白の多い奥付）、細かい字の小さな文字組み。参照の写真と文は使わない。
# 図は国立国会図書館の頁とその寄りだけ（新しい絵は作らない）。仮説は出さない（予想が先、F9.prediction）。
# 画面いっぱいの高さは svh（スマホで URL の帯の裏に隠れないため）。動きは足さない（何度も開く入口のため）。
TAIBAN = """
body.taiban{background:#f2f2f0;color:#161616}
.taiban .switch{font-family:"Helvetica Neue",Arial,sans-serif}
.ab-slide{min-height:100vh;min-height:100svh;display:flex;align-items:center;justify-content:center;padding:3svh 0;box-sizing:border-box}
.board{position:relative;width:min(1180px,92vw,calc(86vh * 1.56));width:min(1180px,92vw,calc(86svh * 1.56));aspect-ratio:1.56;
 background:#fbfbfa;border:1px solid #dedede;border-radius:3px;padding:.9%;box-sizing:border-box;
 box-shadow:0 1px 0 #fff inset,0 28px 40px -22px rgba(0,0,0,.30),0 6px 12px -6px rgba(0,0,0,.12)}
.spread{display:grid;grid-template-columns:1fr 1fr;height:100%}
.page{position:relative;overflow:hidden;background:#fff}
.page.l{box-shadow:inset -22px 0 24px -22px rgba(0,0,0,.22)}.page.r{box-shadow:inset 22px 0 24px -22px rgba(0,0,0,.22)}
.page .fill{position:absolute;inset:0}
.rings{position:absolute;left:50%;top:6%;bottom:6%;display:flex;flex-direction:column;justify-content:space-between;pointer-events:none}
.rings::before{content:"";position:absolute;left:-3px;top:-2%;bottom:-2%;width:6px;border-radius:3px;background:linear-gradient(90deg,#8e9297,#eef0f2 45%,#9a9ea3)}
.rings i{display:block;width:clamp(26px,3.6vw,46px);height:clamp(10px,1.4vw,18px);margin-left:calc(clamp(26px,3.6vw,46px) / -2);border-radius:50%;
 border:clamp(2px,.25vw,3px) solid #a8acb1;border-top-color:#f1f2f4;border-bottom-color:#73777c;box-shadow:0 2px 3px rgba(0,0,0,.28)}
.t{position:absolute;font-family:"Helvetica Neue",Arial,"Hiragino Sans","Noto Sans JP",sans-serif;font-size:clamp(8px,.78vw,11px);line-height:1.5;letter-spacing:.05em;color:#161616;margin:0}
.t.up{text-transform:uppercase;letter-spacing:.08em}
.t.v{writing-mode:vertical-rl;letter-spacing:.2em}
.t a{color:#161616;text-decoration:none;border-bottom:1px solid #161616}
.t ol{list-style:none;padding:0;margin:0}.t ol li{display:grid;grid-template-columns:2.2em 1fr;margin:0 0 .35em}
.t b{font-weight:500}
.cut{position:absolute;filter:drop-shadow(0 8px 10px rgba(0,0,0,.18))}
.box{position:absolute;background:#f0f0ee}
/* 平置き: 1 つ目を上の段いっぱいに、残りを 2 列で。各部分は枠に収まる最大の大きさで、縦横比を崩さない（コンテナの単位で計る）。 */
.lay{position:absolute;left:5%;top:6%;bottom:6%;width:62%;display:grid;grid-template-columns:1fr 1fr;grid-template-rows:40% 1fr 1fr;gap:4%}
.cell{container-type:size;display:flex;align-items:center;justify-content:center;min-height:0}.cell.big{grid-column:1/-1}
.pc{width:min(92cqw,calc(92cqh * var(--r)));filter:drop-shadow(0 8px 10px rgba(0,0,0,.18))}
.sw{position:absolute;display:grid;grid-template-columns:repeat(4,1fr);gap:3%}.sw div{aspect-ratio:3/4;background-color:#f0f0ee}
.ab-end{font-family:"Helvetica Neue",Arial,sans-serif;font-size:11px;color:#777;text-align:center;padding:2svh 6vw 6svh}
@media (max-width:760px){
 .board{width:92vw;aspect-ratio:auto}.spread{grid-template-columns:1fr}.page{aspect-ratio:.78}.rings{display:none}
 .page.l,.page.r{box-shadow:none}.page.l{border-bottom:1px solid #e6e6e6}.t{font-size:10px}}
"""


# 図の中の部分の場所（図の幅と高さに対する割合: 左, 上, 右, 下）。作る側が図を見て決めた。名前は図に見える物の名で、
# 仕組みの名ではない（仮説を出さないため）。参照の平置きの「品物を切り抜いて散らす」を、同じ図の寄りで写すために要る。
PARTS = {
    "NDL-1187053-R0000005-L": {"focus": 62, "parts": [("扇", (0.25, 0.47, 0.66, 0.67)), ("扇の中の像", (0.38, 0.57, 0.53, 0.69)),
                                                       ("筒", (0.37, 0.65, 0.55, 0.87)), ("竿の先の鳥", (0.62, 0.44, 0.92, 0.56)), ("下に置かれた物", (0.17, 0.78, 0.63, 0.90))]},
    "NDL-1187053-R0000014-R": {"focus": 83, "parts": [("虎の頭", (0.05, 0.69, 0.26, 0.81)), ("虎", (0.05, 0.64, 0.63, 0.88)),
                                                       ("隣の像の頭", (0.27, 0.52, 0.47, 0.63)), ("隣の像", (0.27, 0.52, 0.72, 0.77))]},
}
FALLBACK = {"focus": 55, "parts": [(f"図の細部 {k}", r) for k, r in enumerate(((0.1, 0.2, 0.5, 0.45), (0.5, 0.2, 0.9, 0.45), (0.1, 0.5, 0.5, 0.75), (0.5, 0.5, 0.9, 0.75)), 1)]}
W_PX, H_PX = 1600, 2656  # NDL の写しの大きさ（2 枚とも同じ）。部分の箱の縦横比に使う


def _crop(sid, rect):
    """図の 1 部分だけを、その部分の縦横比の箱に収める。箱は幅だけ決めれば高さが決まる。"""
    x0, y0, x1, y1 = rect
    w, h = x1 - x0, y1 - y0
    if not (ROOT / "out/sources" / f"{sid}.jpg").exists():
        return f"aspect-ratio:{w * W_PX:.0f}/{h * H_PX:.0f};background-color:#d9d2c3"
    px = x0 / (1 - w) * 100 if w < 1 else 0
    py = y0 / (1 - h) * 100 if h < 1 else 0
    return (f"aspect-ratio:{w * W_PX:.0f}/{h * H_PX:.0f};background-image:url(/picture/{sid});background-repeat:no-repeat;"
            f"background-size:{100 / w:.1f}% {100 / h:.1f}%;background-position:{px:.1f}% {py:.1f}%")


def _page(cls, inner):
    return f'<div class="page {cls}">{inner}</div>'


def _spread(sid_attr, left, right):
    rings = "<div class=\"rings\">" + "<i></i>" * 6 + "</div>"
    return f'<section id="{sid_attr}" class="ab-slide"><div class="board"><div class="spread">{left}{right}</div>{rings}</div></section>'


def taiban():
    ts = toys()
    first = ts[0]["sid"] if ts else ""
    body = switch("/look/taiban")
    toc = "".join(f'<li><span>{i}</span><a href="/toy/{t["sid"]}">{esc(t["toy"])}</a></li>' for i, t in enumerate(ts, 1))
    # 1 枚目: 左に全面の図、右は白地に小さな文と、灰色の箱に置いた細部 1 つ（参照の 1 枚目の見開きの型）。入口なので一覧を置く。
    body += _spread(
        "look-0",
        _page("l", f'<div class="fill" style="{_bg(first, "56% 62%", "132% auto")}"></div>'),
        _page("r", '<p class="t up" style="left:9%;top:7%">うつし · Edo toy lookbook vol.01</p>'
                   '<p class="t up" style="right:9%;top:7%">江都二色 1773</p>'
                   '<p class="t" style="left:9%;top:14%;width:36%">江戸の絵本『江都二色』に、図と歌だけが残る玩具。</p>'
                   '<p class="t" style="left:52%;top:14%;width:38%">動きを予想して、紙と糸で作って確かめます。まず紙が返事をします。</p>'
                   f'<div class="t" style="left:9%;top:30%;width:40%"><ol>{toc}</ol></div>'
                   f'<div class="box" style="left:9%;right:9%;top:46%;bottom:13%"><div class="cut" style="left:31%;top:12%;width:38%;{_crop(first, (PARTS.get(first) or FALLBACK)["parts"][0][1])}"></div></div>'
                   '<p class="t up" style="left:9%;bottom:6%">失われた玩具の動きを、紙で実験して確かめる道具</p><p class="t up" style="right:9%;bottom:6%">utsushi</p>'))
    for i, t in enumerate(ts, 1):
        s, name = t["sid"], esc(t["toy"])
        song = "".join(f"<span>{esc(x)}</span>" for x in t["song"])
        # 平置きの見開き: 左は小さな写真と縦の一行と 2 段の文、右は寄りを切り抜きのように散らし、番号の一覧を添える。
        info = PARTS.get(s, FALLBACK)
        # 部分ごとに縦横比が違うので、高さを決めて並べ、幅は比に任せる。1 つ目を大きく置くのは参照の平置きの主役の置き方。
        cuts = "".join(f'<div class="cell{" big" if k == 0 else ""}"><div class="pc" style="--r:{(r[2] - r[0]) * W_PX / ((r[3] - r[1]) * H_PX):.3f};{_crop(s, r)}"></div></div>'
                       for k, (_, r) in enumerate(info["parts"]))
        lst = "".join(f"<li><span>{k}</span>{esc(n)}</li>" for k, (n, _) in enumerate(info["parts"], 1))
        body += _spread(
            f"look-{i}",
            _page("l", f'<p class="t up" style="left:18%;top:7%">look {i:02d}<br>{name}</p>'
                       f'<div class="cut" style="left:30%;top:24%;width:36%;height:38%;{_bg(s, "56% 50%", "132% auto")}"></div>'
                       '<p class="t v" style="left:9%;top:42%">どこが動くと思いますか</p>'
                       f'<p class="t" style="left:18%;bottom:12%;width:30%">{song}</p>'
                       f'<p class="t" style="left:54%;bottom:12%;width:30%">原文の引用。確かめた人: 本人。{esc(t["holding"])}{_nopic(t)}</p>'),
            _page("r", f'<div class="fill" style="background:#eef0f2"></div><div class="lay">{cuts}</div>'
                       f'<div class="t" style="right:5%;top:40%;width:26%"><ol>{lst}</ol></div>'
                       f'<p class="t" style="right:5%;top:66%;width:26%">図に見える物の名。仕組みの名ではありません。</p>'
                       f'<p class="t" style="right:5%;top:76%;width:26%"><a href="/toy/{s}">予想を書いてひらく →</a></p>'))
        # 見開きをまたぐ 1 枚: 1 枚の図を左右の頁に半分ずつ敷き、左上に小さな文。
        body += _spread(
            f"wide-{i}",
            _page("l", f'<div class="fill" style="{_bg(s, f"17% {(PARTS.get(s) or FALLBACK)['focus']}%", "230% auto")}"></div><p class="t up" style="left:7%;top:7%;width:46%;background:rgba(255,255,255,.78);padding:6px 8px">{name}<br>{esc(t["holding"])}</p>'),
            _page("r", f'<div class="fill" style="{_bg(s, f"91% {(PARTS.get(s) or FALLBACK)['focus']}%", "230% auto")}"></div><p class="t up" style="right:7%;top:7%">utsushi</p>'))
        # 文字の頁と全面の図: 左は文と、下に寄りを色見本のように 4 つ並べる。右は図を頁いっぱいに。
        sw = "".join(f'<div style="{_bg(s, f"{(r[0] + r[2]) * 50:.0f}% {(r[1] + r[3]) * 50:.0f}%", "420%")}"></div>' for _, r in PARTS.get(s, FALLBACK)["parts"][:4])
        body += _spread(
            f"item-{i}",
            _page("l", f'<p class="t up" style="left:9%;top:7%">{name}<br>a few small choices</p>'
                       '<p class="t" style="left:52%;top:7%;width:38%">図を見て、先に予想を書いてから作ります。紙で作って、動くかを確かめます。動かなかった記録も、そのまま紙の返事です。</p>'
                       f'<p class="t" style="left:52%;top:30%"><a href="/toy/{s}">予想を書いてひらく →</a></p>'
                       f'<div class="sw" style="left:9%;right:9%;bottom:8%">{sw}</div>'),
            _page("r", f'<div class="fill" style="{_bg(s, "56% 50%", "132% auto")}"></div>'))
    # 奥付: 左は白地に寄り 1 つと縦の一行、右は右下に寄せた少ない文（参照の最後の見開きの型）。
    body += _spread(
        "colophon",
        _page("l", f'<p class="t up" style="left:9%;top:7%">keep playing</p><p class="t up" style="right:9%;top:7%">うつし</p>'
                   f'<div class="cut" style="left:50%;top:24%;height:46%;transform:translateX(-50%);{_crop(first, (PARTS.get(first) or FALLBACK)["parts"][0][1])}"></div>'
                   '<p class="t v" style="left:6%;bottom:12%">おもちゃで遊び続ける</p><p class="t up" style="left:9%;bottom:6%">utsushi</p>'),
        _page("r", '<p class="t" style="right:9%;bottom:16%;width:62%;text-align:right">図は国立国会図書館デジタルコレクションの頁（米山堂・1931 年の複製）。この冊子のための新しい絵は作っていない。</p>'
                   '<p class="t up" style="right:9%;bottom:6%">vol.01</p>'))
    body += '<p class="ab-end">組み方は本人が挙げたルックブックの再現（J-024）。写真と文は参照の物を使っていない。</p>'
    return page("うつし · 大判写真集", body + ONLY, TAIBAN, "taiban")


# ---------------------------------------------------------------- C 縦読みのジン
ZINE = """
body.zine{background:#111;color:#eee6d6}
body.zine a{color:#f0c27a}.zine .switch a{color:#f0c27a}
.zn-cover{height:100vh;height:100svh;position:relative;overflow:hidden}
.zn-cover .strip{position:absolute;left:0;right:0;top:22%;height:46%;filter:saturate(.9)}
.zn-cover h1{position:absolute;left:4vw;bottom:5vh;font-size:clamp(72px,17vw,260px);line-height:1.1;margin:0;font-weight:200;letter-spacing:-.04em;mix-blend-mode:difference;color:#fff}
.zn-cover .meta{position:absolute;right:4vw;top:6vh;color:#cfc4ad;font-size:12px;letter-spacing:.35em;text-transform:uppercase}
.zn-toy{display:grid;grid-template-columns:1fr 1fr}
.zn-toy .pin{position:sticky;top:0;height:100vh;height:100svh}
.zn-toy .flow > div{min-height:100vh;min-height:100svh;padding:12vh 6vw;box-sizing:border-box;display:flex;flex-direction:column;justify-content:center}
.zn-toy .big{font-size:clamp(80px,14vw,220px);font-weight:200;line-height:.9;margin:0;font-variant-numeric:tabular-nums lining-nums}
.zn-toy h2{font-size:clamp(32px,5vw,72px);font-weight:300;margin:.2em 0}
.zn-toy .song{font-size:clamp(18px,2vw,26px);line-height:1.9}
.zn-toy .cap{color:#a99f8d}
.zn-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.zn-grid div{aspect-ratio:1}
@media (max-width:760px){.zn-toy{grid-template-columns:1fr}.zn-toy .pin{position:relative;height:70vh;height:70svh}}
"""


def zine():
    ts = toys()
    first = ts[0]["sid"] if ts else ""
    body = switch("/look/zine")
    body += (f'<section class="zn-cover"><div class="strip" style="{_bg(first, "50% 60%")}"></div>'
             '<p class="meta">Edo toy lookbook · vol.01 · 1773</p><h1>うつし</h1></section>')
    for i, t in enumerate(ts, 1):
        song = "".join(f'<p class="song">{esc(x)}</p>' for x in t["song"])
        tiles = "".join(f'<div style="{_bg(t["sid"], p, "300%")}"></div>' for p in ("30% 30%", "72% 40%", "35% 75%", "70% 82%"))
        # 図は左に留めたまま、右で名・歌・細部・入口が流れる。図から目を離さずに読む形。
        body += (f'<section id="look-{i}" class="zn-toy"><div class="pin" style="{_bg(t["sid"], "50% 50%", "contain")};background-color:#1a1714"></div><div class="flow">'
                 f'<div><p class="big">{i:02d}</p><h2>{esc(t["toy"])}</h2>{_nopic(t)}</div>'
                 f'<div id="song-{i}">{song}<p class="cap">{QUOTE} · {esc(t["holding"])}</p></div>'
                 f'<div><div class="zn-grid">{tiles}</div><p class="cap">図の細部</p></div>'
                 f'<div><p class="song">どこが動くと思いますか。</p><p><a href="/toy/{t["sid"]}">予想を書いてひらく →</a></p></div></div></section>')
    body += '<p class="cap" style="padding:10vh 6vw">図は国立国会図書館デジタルコレクションの頁（米山堂・1931 年の複製）。新しい絵は作っていない。</p>'
    return page("うつし · 縦読みのジン", body + ONLY, ZINE, "zine")


PAGES = {"taiban": taiban, "zine": zine}
