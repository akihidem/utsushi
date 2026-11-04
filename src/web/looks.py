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
    "tenji": "A′ 日本画展の展示",
    "zine": "C 縦読みのジン",
}


def switch(current):
    """残した 2 案を行き来する切り替え。今いる案は太字にする。A は入口（/）と同じ頁。"""
    items = [("/", LOOKS["taiban"]), ("/look/tenji", LOOKS["tenji"]), ("/look/zine", LOOKS["zine"])]
    current = "/" if current == "/look/taiban" else current
    links = "｜".join(f"<b>{esc(n)}</b>" if u == current else f'<a href="{u}">{esc(n)}</a>' for u, n in items)
    # 上げた物のギャラリーと職人の言葉（本人の設計、11-04）。入口からいつでも行けるよう、切り替えの並びに置く。
    links += '｜<a href="/gallery">上げた物と職人の言葉</a>'
    return f'<nav class="switch">{links}<span class="cap">A と A′ は本人が見比べて決める（11-04）</span></nav>'


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


# 額に入れる図は、複写の台の黒い縁が額の中に見えないよう、枠と同じ比のまま少し大きく敷く（A の全面の図と同じ考え）。
FRAMED = "112% 112%"


def framed_pos(sid):
    """綴じの影は頁の綴じ側に出る。左頁（L）は左、右頁（R）は右に濃いので、反対側へ寄せて影を落とす。"""
    return "15% 50%" if source(sid).get("side") == "R" else "85% 50%"


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


# ---------------------------------------------------------------- C 縦読みのジン（黒地）
# 本人の答え（2026-11-04）: C は黒地のジンのまま性格を保つ（U-23）。さらに「本の形式もわるくないけど、黒の背景に高級感ある方が
# もっと良くなる」。デザイナーの感想「もっと美術品みたく、歴史的価値のあるように見せたサイトの方が良い」も受けた。
# 磨きの向き: 図を額装した美術品として見せる。深い黒の地に、図だけに光を当て、細い金の線の額とマット、明朝の細い字、
# 美術館の作品の札（題・作・画・年・所蔵）を添える。札の中身は出典の記録（NDL の書誌）だけから刷り、足さない。
# 動きは入れない（research/19 の判断のまま。何度も開く入口なので）。
ZINE = """
body.zine{background:#0b0a09;color:#e9e1cf;font-family:"Noto Serif CJK JP","Noto Serif JP","Hiragino Mincho ProN","Yu Mincho",serif;
 font-feature-settings:"palt" 1}
body.zine a{color:#c9a96a;text-decoration:none;border-bottom:1px solid rgba(201,169,106,.45)}
.zine .switch{position:relative;z-index:2;font-size:12px;letter-spacing:.2em;padding:14px 4vw;color:#7d7463}
.zine .switch a{color:#c9a96a}.zine .switch b{color:#e9e1cf;font-weight:400}
.zine .switch .cap{color:#5f584c}
.zn-cover{min-height:100vh;min-height:100svh;position:relative;display:grid;grid-template-columns:1fr minmax(0,44vh) 1fr;align-items:center;
 background:radial-gradient(ellipse 46% 62% at 50% 46%,#1d1914 0%,#0b0a09 72%)}
.zn-cover .frame{grid-column:2;aspect-ratio:1600/2656;padding:18px;background:#141210;border:1px solid #6e5a35;
 box-shadow:0 0 0 6px #0b0a09,0 0 0 7px #3a3122,0 30px 80px rgba(0,0,0,.7)}
.zn-cover .frame div{width:100%;height:100%}
.zn-cover h1{grid-column:3;justify-self:start;margin:0 0 0 6vw;writing-mode:vertical-rl;font-weight:300;
 font-size:clamp(40px,6.5vw,92px);letter-spacing:.5em;color:#efe6d2}
.zn-cover .meta{grid-column:1;justify-self:end;margin-right:6vw;writing-mode:vertical-rl;color:#9a8e76;font-size:13px;letter-spacing:.45em}
.zn-label{border-top:1px solid #6e5a35;padding-top:14px;margin-top:22px;font-size:13px;line-height:2;color:#b9ae97;letter-spacing:.08em}
.zn-label b{display:block;font-weight:400;font-size:clamp(20px,2.2vw,28px);color:#efe6d2;letter-spacing:.2em}
.zn-toy{display:grid;grid-template-columns:1fr 1fr;border-top:1px solid #1f1b16}
.zn-toy .pin{position:sticky;top:0;height:100vh;height:100svh;display:flex;align-items:center;justify-content:center;
 background:radial-gradient(ellipse 60% 70% at 50% 48%,#1c1813 0%,#0b0a09 75%)}
.zn-toy .pin .frame{height:78%;aspect-ratio:1600/2656;padding:14px;background:#141210;border:1px solid #6e5a35;box-shadow:0 26px 70px rgba(0,0,0,.75)}
.zn-toy .pin .frame div{width:100%;height:100%}
.zn-toy .flow > div{min-height:100vh;min-height:100svh;padding:14vh 7vw;box-sizing:border-box;display:flex;flex-direction:column;justify-content:center}
.zn-toy .big{font-size:clamp(14px,1.2vw,16px);letter-spacing:.5em;color:#c9a96a;margin:0 0 18px;font-variant-numeric:tabular-nums lining-nums}
.zn-toy h2{font-size:clamp(40px,5.5vw,84px);font-weight:300;margin:0;letter-spacing:.25em}
.zn-toy .songs{writing-mode:vertical-rl;height:min(60vh,520px);margin:0 auto 24px}
.zn-toy .song{font-size:clamp(18px,1.9vw,24px);line-height:2.2;letter-spacing:.12em;margin:0 .4em}
.zn-toy .cap{color:#8c826e;font-size:12px;letter-spacing:.15em;line-height:1.9}
.zn-grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}
.zn-grid div{aspect-ratio:1;border:1px solid #3a3122;outline:8px solid #141210;outline-offset:-9px}
.zn-end{padding:14vh 7vw;border-top:1px solid #1f1b16;text-align:center}
@media (max-width:760px){.zn-cover{grid-template-columns:1fr;grid-template-rows:auto auto auto;padding:8vh 8vw;gap:24px}
 .zn-cover .frame,.zn-cover h1,.zn-cover .meta{grid-column:1;justify-self:center;margin:0}
 .zn-cover h1,.zn-cover .meta{writing-mode:horizontal-tb}.zn-cover .frame{width:70vw}
 .zn-toy{grid-template-columns:1fr}.zn-toy .pin{position:relative;height:72vh;height:72svh}
 .zn-toy .songs{writing-mode:horizontal-tb;height:auto}}
"""


def _label(t, src, cls="zn-label"):
    """美術館の作品の札。中身は出典の記録（NDL の書誌）の値だけで、作る側の言葉を足さない。"""
    who = esc(src.get("creator_as_cataloged", "").replace("||", "・"))
    when = esc((src.get("original_publication") or {}).get("value", ""))
    rights = "パブリック・ドメイン（PDM）" if src.get("rights") == "PDM" else esc(src.get("rights", ""))
    return (f'<p class="{cls}">『{esc(src.get("title", ""))}』より<br>{who}<br>{when}<br>'
            f'{esc(t["holding"])}<br>{rights}</p>')


def zine():
    ts = toys()
    first = ts[0]["sid"] if ts else ""
    body = switch("/look/zine")
    body += (f'<section class="zn-cover"><p class="meta">江都二色　安永二年　うしなわれた玩具</p>'
             f'<div class="frame"><div style="{_bg(first, framed_pos(first), FRAMED)}"></div></div><h1>うつし</h1></section>')
    for i, t in enumerate(ts, 1):
        src = source(t["sid"])
        song = "".join(f'<p class="song">{esc(x)}</p>' for x in t["song"])
        tiles = "".join(f'<div style="{_bg(t["sid"], p, "300%")}"></div>' for p in ("30% 30%", "72% 40%", "35% 75%", "70% 82%"))
        # 図は左に額装して留めたまま、右で札・歌・細部・入口が流れる。図から目を離さずに読む形。
        body += (f'<section id="look-{i}" class="zn-toy"><div class="pin"><div class="frame"><div style="{_bg(t["sid"], framed_pos(t["sid"]), FRAMED)}"></div></div></div><div class="flow">'
                 f'<div><p class="big">No. {i:02d}</p><h2>{esc(t["toy"])}</h2>{_label(t, src)}{_nopic(t)}</div>'
                 f'<div id="song-{i}"><div class="songs">{song}</div><p class="cap">{QUOTE} · {esc(t["holding"])}</p></div>'
                 f'<div><div class="zn-grid">{tiles}</div><p class="cap">図の細部</p></div>'
                 f'<div><p class="h2" style="font-size:clamp(22px,2.4vw,30px);letter-spacing:.2em;font-weight:300">どこが動くと思いますか。</p><p><a href="/toy/{t["sid"]}">予想を書いてひらく</a></p></div></div></section>')
    body += '<p class="cap zn-end">図は国立国会図書館デジタルコレクションの頁（米山堂・1931 年の複製）。新しい絵は作っていない。</p>'
    return page("うつし · 縦読みのジン", body + ONLY, ZINE, "zine")


# ---------------------------------------------------------------- A′ 日本画展の展示（白の壁）
# 本人の言葉（2026-11-04）: 「白の背景で高級感出してもいいよ。美術館の展示みたく」「日本画の展覧会の展示みたいな。山種美術館の展示環境みたいな」。
# デザイナーの感想（本人が伝えた）: 「もっと美術品みたく、歴史的価値のあるように見せたサイトの方が良い」。
# A をバインダーの再現のまま磨くか展示の形に作り替えるかを聞いたら、本人は「まだ決めず、どっちも作る」と答えた。だから A はそのまま残し、
# 展示の形を A′ として並べる。順路: 入口の題のパネル → 章ごとに 1 点を白い壁に掛け、作品の札と解説 → 細部 → 出口（玩具の頁へ）。
# 札の中身は出典の記録の値だけ。解説の文は今ある決定の文（README の一言、歌の引用）だけで、作る側の言葉を足さない。動きは入れない。
TENJI = """
body.tenji{background:#f6f3ec;color:#2b2722;font-family:"Noto Serif CJK JP","Noto Serif JP","Hiragino Mincho ProN","Yu Mincho",serif;font-feature-settings:"palt" 1}
body.tenji a{color:#6b4f2a;text-decoration:none;border-bottom:1px solid rgba(107,79,42,.35)}
.tenji .switch{font-size:12px;letter-spacing:.2em;padding:14px 5vw;color:#8b8172}.tenji .switch .cap{color:#a59b8b}
.tj-hall{min-height:100vh;min-height:100svh;display:grid;grid-template-columns:1fr auto 1fr;align-items:center;padding:0 5vw;box-sizing:border-box}
.tj-hall h1{grid-column:2;writing-mode:vertical-rl;font-weight:400;font-size:clamp(44px,6vw,86px);letter-spacing:.6em;margin:0;color:#1f1b17}
.tj-hall .sub{grid-column:3;justify-self:start;writing-mode:vertical-rl;margin-left:5vw;font-size:clamp(14px,1.3vw,17px);letter-spacing:.5em;line-height:2.4;color:#5d554a}
.tj-hall .en{grid-column:1;justify-self:end;margin-right:5vw;font-size:11px;letter-spacing:.35em;color:#8b8172;text-transform:uppercase;writing-mode:vertical-rl}
.tj-room{min-height:100vh;min-height:100svh;display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.25fr) minmax(0,1fr);gap:4vw;align-items:center;
 padding:12vh 5vw;box-sizing:border-box;border-top:1px solid #e4ddcf}
.tj-room .panel{align-self:start;padding-top:6vh}
.tj-room .chapter{font-size:12px;letter-spacing:.5em;color:#8b8172;margin:0 0 18px}
.tj-room h2{font-weight:400;font-size:clamp(26px,2.8vw,42px);letter-spacing:.18em;margin:0 0 26px;word-break:keep-all}
.tj-room .lead{font-size:14px;line-height:2.2;letter-spacing:.08em;color:#4a4339}
.tj-work{justify-self:center;width:min(100%,46vh);aspect-ratio:1600/2656;padding:3.2%;background:#fbf9f4;
 border:1px solid #d8cdb6;box-shadow:0 1px 0 #e8e1d2,0 40px 60px -30px rgba(70,55,35,.35),0 2px 6px rgba(70,55,35,.08)}
.tj-work div{width:100%;height:100%}
.tj-side{align-self:end;padding-bottom:6vh}
.tj-label{font-size:12px;line-height:2;letter-spacing:.06em;color:#5d554a;border-left:1px solid #b9a982;padding-left:14px;max-width:22em}
.tj-label .no{display:block;color:#8b8172;letter-spacing:.3em}
.tj-label .ttl{display:block;font-size:18px;letter-spacing:.25em;color:#1f1b17;margin:4px 0}
.tj-songs{writing-mode:vertical-rl;height:min(46vh,420px);margin:0 0 20px auto;font-size:clamp(16px,1.6vw,21px);line-height:2.3;letter-spacing:.14em}
.tj-songs p{margin:0 .3em}
.tj-detail{padding:12vh 5vw;border-top:1px solid #e4ddcf;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:3vw;align-items:start}
.tj-detail figure{margin:0}.tj-detail figure div{aspect-ratio:3/4;background-color:#fbf9f4;border:1px solid #d8cdb6;box-shadow:0 20px 30px -24px rgba(70,55,35,.4)}
.tj-detail figcaption{font-size:11px;letter-spacing:.2em;color:#8b8172;margin-top:10px}
.tj-exit{padding:14vh 5vw 18vh;text-align:center;border-top:1px solid #e4ddcf}
.tj-exit p{font-size:clamp(20px,2.2vw,28px);letter-spacing:.3em;font-weight:400}
.tj-note{font-size:11px;color:#8b8172;letter-spacing:.1em;padding:0 5vw 8vh;text-align:center}
@media (max-width:820px){.tj-room{grid-template-columns:1fr;gap:6vh}.tj-work{width:72vw}.tj-songs{writing-mode:horizontal-tb;height:auto}
 .tj-detail{grid-template-columns:1fr 1fr}.tj-hall{grid-template-columns:1fr;justify-items:center;gap:4vh;padding:10vh 5vw}
 .tj-hall h1,.tj-hall .sub,.tj-hall .en{grid-column:1;margin:0;justify-self:center}}
"""
KANJI = "一二三四五六七八九十"


def tenji():
    ts = toys()
    body = switch("/look/tenji")
    body += ('<section class="tj-hall"><p class="en">Lost toys of Edo · 1773</p><h1>うつし</h1>'
             '<p class="sub">江都二色より<br>うしなわれた玩具の動きを<br>紙で実験して確かめる</p></section>')
    for i, t in enumerate(ts, 1):
        src = source(t["sid"])
        song = "".join(f"<p>{esc(x)}</p>" for x in t["song"])
        n = KANJI[i - 1] if i <= len(KANJI) else str(i)
        body += (f'<section id="look-{i}" class="tj-room"><div class="panel"><p class="chapter">第{n}章</p><h2>{esc(t["toy"])}</h2>'
                 f'<div class="tj-songs" id="song-{i}">{song}</div><p class="lead">{QUOTE}</p></div>'
                 f'<div class="tj-work"><div style="{_bg(t["sid"], framed_pos(t["sid"]), FRAMED)}"></div></div>'
                 f'<div class="tj-side"><div class="tj-label"><span class="no">No. {i:02d}</span><span class="ttl">{esc(t["toy"])}</span>'
                 f'{_label(t, src, "tj-inner")}</div>{_nopic(t)}</div></section>')
        figs = "".join(f'<figure><div style="{_bg(t["sid"], p, "300%")}"></div><figcaption>部分 {k}</figcaption></figure>'
                       for k, p in enumerate(("30% 30%", "72% 40%", "35% 75%", "70% 82%"), 1))
        body += f'<section class="tj-detail" id="detail-{i}">{figs}</section>'
        body += (f'<section class="tj-exit"><p>どこが動くと思いますか。</p><a href="/toy/{t["sid"]}">予想を書いてひらく</a></section>')
    body += '<p class="tj-note">図は国立国会図書館デジタルコレクションの頁（米山堂・1931 年の複製）。新しい絵は作っていない。</p>'
    return page("うつし · 日本画展の展示", body + ONLY, TENJI, "tenji")


PAGES = {"taiban": taiban, "tenji": tenji, "zine": zine}
