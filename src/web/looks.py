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


def _toc(ts):
    return "".join(f'<li><a href="/toy/{t["sid"]}">{i:02d}　{esc(t["toy"])}</a></li>' for i, t in enumerate(ts, 1))


QUOTE = "原文の引用。確かめた人: 本人"

# 見比べるための写しを撮る補助。?only=<節の id> で、その節だけを画面の頭に出す。
# なぜ: 縦に流れる案は、頭からしか写しを撮れず、途中の見開きを並べて比べられないため。ふだんの閲覧には効かない。
ONLY = """<script>(()=>{const id=new URLSearchParams(location.search).get('only');if(!id)return;
const st=document.createElement('style');st.textContent='section:not(#'+CSS.escape(id)+'),.switch,.tb-end,main>p{display:none!important}';document.head.appendChild(st)})();</script>"""

# ---------------------------------------------------------------- A 大判写真集
TAIBAN = """
body.taiban{background:#f4f1ea;color:#1f1b17}
.tb-cover{height:100vh;display:grid;grid-template-columns:58% 42%}
.tb-cover .img{position:relative}.tb-cover .txt{padding:6vw 5vw;display:flex;flex-direction:column;justify-content:space-between}
.tb-cover h1{font-size:clamp(64px,12vw,190px);font-weight:300;line-height:.9;margin:0;letter-spacing:-.02em}
.tb-meta{font-size:12px;letter-spacing:.35em;text-transform:uppercase}
.tb-spread{height:92vh;margin:6vh 4vw;position:relative;box-shadow:0 1px 0 #d8d0c0}
.tb-spread .gutter{position:absolute;left:50%;top:0;bottom:0;width:2px;background:linear-gradient(90deg,rgba(0,0,0,.18),transparent)}
.tb-spread .band{position:absolute;left:4%;bottom:6%;color:#fff;text-shadow:0 2px 14px rgba(0,0,0,.6)}
.tb-spread .band h2{font-size:clamp(40px,7vw,110px);font-weight:300;margin:0;letter-spacing:.1em}
.tb-item{display:grid;grid-template-columns:1fr 1fr;min-height:92vh;margin:0 4vw;background:#fff}
.tb-item .l{display:flex;align-items:center;justify-content:center}.tb-item .l div{width:46%;aspect-ratio:3/4;box-shadow:0 10px 30px rgba(0,0,0,.12)}
.tb-item .r{padding:8vw 6vw;display:flex;flex-direction:column;justify-content:flex-end;border-left:1px solid #eee}
.tb-item .no{font-size:clamp(60px,9vw,150px);font-weight:200;line-height:1;margin:0}
.tb-item .song{writing-mode:vertical-rl;font-size:18px;line-height:2;height:14em;margin:24px 0 24px auto}
.tb-end{padding:12vh 6vw;font-size:13px}
.tb-toc{list-style:none;padding:0;margin:18px 0;font-size:15px;letter-spacing:.1em}.tb-toc li{margin:6px 0}.tb-toc a{text-decoration:none;border-bottom:1px solid #1f1b17}
@media (max-width:760px){.tb-cover,.tb-item{grid-template-columns:1fr}.tb-cover .img{height:60vh}.tb-item .song{writing-mode:horizontal-tb;height:auto}}
"""


def taiban():
    ts = toys()
    first = ts[0]["sid"] if ts else ""
    body = switch("/look/taiban")
    body += (f'<section class="tb-cover"><div class="img" style="{_bg(first, "50% 62%")}"></div><div class="txt">'
             '<p class="tb-meta">Edo toy lookbook · vol.01</p><h1>うつ<br>し</h1>'
             '<div><p>江都二色（1773）に、図と歌だけが残る玩具。動きを予想して、紙と糸で作って確かめます。まず紙が返事をします。</p>'
             f'<ul class="tb-toc">{_toc(ts)}</ul><p class="tb-meta">動きを予想し · 紙と糸で確かめる</p></div></div></section>')
    for i, t in enumerate(ts, 1):
        # 1 枚の図を見開きいっぱいに敷く。綴じの影を真ん中に置いて、冊子の見開きに見せる。
        body += (f'<section id="look-{i}" class="tb-spread" style="{_bg(t["sid"], "50% 58%")}"><div class="gutter"></div>'
                 f'<div class="band"><p class="tb-meta">look {i:02d}</p><h2>{esc(t["toy"])}</h2>{_nopic(t)}</div></section>')
        song = "".join(f'<p class="song">{esc(x)}</p>' for x in t["song"])
        body += (f'<section id="item-{i}" class="tb-item"><div class="l"><div style="{_bg(t["sid"], "50% 72%", "300%")}"></div></div>'
                 f'<div class="r"><p class="no">{i:02d}</p><p class="tb-meta">{esc(t["toy"])}</p>{song}<p class="cap">{QUOTE} · {esc(t["holding"])}</p>'
                 f'<a class="open" href="/toy/{t["sid"]}">予想を書いてひらく →</a></div></section>')
    body += '<p class="tb-end">図は国立国会図書館デジタルコレクションの頁（米山堂・1931 年の複製）。この冊子のための新しい絵は作っていない。</p>'
    return page("うつし · 大判写真集", body + ONLY, TAIBAN, "taiban")


# ---------------------------------------------------------------- C 縦読みのジン
ZINE = """
body.zine{background:#111;color:#eee6d6}
body.zine a{color:#f0c27a}.zine .switch a{color:#f0c27a}
.zn-cover{height:100vh;position:relative;overflow:hidden}
.zn-cover .strip{position:absolute;left:0;right:0;top:22%;height:46%;filter:saturate(.9)}
.zn-cover h1{position:absolute;left:4vw;bottom:5vh;font-size:clamp(72px,17vw,260px);line-height:1.1;margin:0;font-weight:200;letter-spacing:-.04em;mix-blend-mode:difference;color:#fff}
.zn-cover .meta{position:absolute;right:4vw;top:6vh;color:#cfc4ad;font-size:12px;letter-spacing:.35em;text-transform:uppercase}
.zn-toy{display:grid;grid-template-columns:1fr 1fr}
.zn-toy .pin{position:sticky;top:0;height:100vh}
.zn-toy .flow > div{min-height:100vh;padding:12vh 6vw;box-sizing:border-box;display:flex;flex-direction:column;justify-content:center}
.zn-toy .big{font-size:clamp(80px,14vw,220px);font-weight:200;line-height:.9;margin:0}
.zn-toy h2{font-size:clamp(32px,5vw,72px);font-weight:300;margin:.2em 0}
.zn-toy .song{font-size:clamp(18px,2vw,26px);line-height:1.9}
.zn-toy .cap{color:#a99f8d}
.zn-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.zn-grid div{aspect-ratio:1}
@media (max-width:760px){.zn-toy{grid-template-columns:1fr}.zn-toy .pin{position:relative;height:70vh}}
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
