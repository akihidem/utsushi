"""入口のルックブック（J-024）。本人が 5 案を見比べ、A 大判写真集と C 縦読みのジンを残した（2026-11-04）。
見開き型・冊子型・B 和綴じ帖は外した。A が入口（/）で、C は /look/zine から見る。

判断の芯: 案ごとに佇まい（表紙・見開きの構成・題の組み方）だけを変え、守る線は同じにする。
新しい絵は作らず、NDL の図の頁とその寄りだけを使う。歌は人が確かめた読みだけを引用の印つきで出す。
仮説は出さない（予想が先、F9.prediction）。どの案も最後は同じ玩具の頁（/toy/）へ入る。
"""
from omochae import hypotheses

from .play_server import ROOT, esc, page, source, sources

# 残した 2 つの入口。大判（A）と外した 3 案は出さない（本人の決定 11-05 朝「日本画かジンで行くから、他のデザインは要らない」）。
LOOKS = {
    "tenji": "A′ 日本画展の展示",
    "zine": "C 縦読みのジン",
}


def switch(current):
    """入口の頭の帯。順路の道（序・おもちゃ・上げた物と職人の言葉・図鑑）だけ。
    皮の切り替えは置かない: 皮ごとに 1 サイト（本人の決定 11-05 朝）。current は呼び手の形を保つために残す。"""
    links = '<a href="/about">序</a>｜<a href="/toys">おもちゃ</a>｜<a href="/gallery">上げた物と職人の言葉</a>｜<a href="/zukan">図鑑（ほかの玩具も）</a>'
    return f'<nav class="switch">{links}</nav>'


def toys():
    """図の写しが手元に無い玩具も並べる。A は入口なので、写しの有無で玩具が消えると入れなくなるため。
    入口の主役は必須の 2 種だけ。試作の玩具は図鑑から入る（hypotheses.stage）。"""
    out = []
    for s in (s for s in sources() if hypotheses.stage(s) == "必須"):
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
def all_toys(prefix):
    """全部の玩具の一覧（本人の指示 11-05「88 種のおもちゃから 1 個選ぶ」。要件 L-02: 入口から試作の玩具にも入れる）。
    必須の 2 種を大きく、試作の 81 種を小さな札で並べる。試作の写し（out/sources）は棚卸しの箱で切り出した物なので、全体が入る形で敷く
    （必須の 2 種は頁の半分の写しなので、額の敷き方 FRAMED で寄せる）。写しが無い玩具は名前だけにし、国立国会図書館への道を添える。
    仮説の名前と動き方は出さない（予想が先、F9.prediction）。名前は作る側の見立てで確かめ待ち（U-01）。動きは付けない。"""
    items = []
    # 必須の 2 種を先頭に（入口の主役のまま）、試作はコマの順。順位ではなく、記録の並び。
    sids = sorted(sources(), key=lambda s: (hypotheses.stage(s) != "必須", s))
    for sid in sids:
        data = hypotheses.load(sid)
        src = source(sid)
        main = hypotheses.stage(sid) == "必須"
        has = (ROOT / "out/sources" / f"{sid}.jpg").exists()
        if has:
            pic = f'<div class="pic" style="{_bg(sid, framed_pos(sid), FRAMED) if main else _bg(sid, "50% 50%", "contain")}" role="img" aria-label="{esc(data["toy"])}の図"></div>'
        else:
            pic = '<div class="pic nopic">図は手元に無い</div>'
        more = "" if has else f'<small><a href="{esc(src.get("image_url", ""))}">図を見る（国立国会図書館）</a></small>'
        items.append(f'<li{" class=\"big\"" if main else ""}><a href="/toy/{esc(sid)}">{pic}<span class="nm">{esc(data["toy"])}</span></a>{more}</li>')
    n = len(items)
    return (f'<section class="{prefix}-all" id="all-toys" aria-label="全部の玩具"><p class="chapter">おもちゃ</p>'
            f'<h2>{n} の玩具から、1 つ選ぶ</h2>'
            '<p class="cap">どれも図と歌だけが残った玩具。選んで、先に予想を書くと、仮説と型紙が出る。'
            '先頭の 2 つのほかは全部を型紙にする途中の試作で、名前は作る側の見立てで、まだ確かめていません。</p>'
            f'<ul class="grid">{"".join(items)}</ul></section>')


ZINE = """
body.zine{background:#0b0a09;color:#e9e1cf;font-family:"Noto Serif CJK JP","Noto Serif JP","Hiragino Mincho ProN","Yu Mincho",serif;
 font-feature-settings:"palt" 1}
body.zine a{color:#c9a96a;text-decoration:none;border-bottom:1px solid rgba(201,169,106,.45)}
.zine .switch{position:relative;z-index:2;font-size:12px;letter-spacing:.2em;padding:14px 4vw;color:#8a806e}
.zine .switch a{color:#c9a96a}.zine .switch b{color:#e9e1cf;font-weight:400}
.zine .switch .cap{color:#827968}
/* 細い字も 4.5:1 を割らないよう明るさだけ上げ、色相は保つ（research/24 の 2）。選んだ時は黒地に金の薄い面（同 5）。 */
body.zine ::selection{background:rgba(201,169,106,.35);color:#f5eedf}
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
.zn-toy{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);border-top:1px solid #1f1b16}
.zn-toy .pin{position:sticky;top:0;height:100vh;height:100svh;display:flex;align-items:center;justify-content:center;
 background:radial-gradient(ellipse 60% 70% at 50% 48%,#1c1813 0%,#0b0a09 75%)}
.zn-toy .pin .frame{height:78%;aspect-ratio:1600/2656;padding:14px;background:#141210;border:1px solid #6e5a35;box-shadow:0 26px 70px rgba(0,0,0,.75)}
.zn-toy .pin .frame div{width:100%;height:100%}
.zn-toy .flow > div{min-height:100vh;min-height:100svh;padding:14vh 7vw;box-sizing:border-box;display:flex;flex-direction:column;justify-content:center}
.zn-toy .big{font-size:clamp(14px,1.2vw,16px);letter-spacing:.5em;color:#c9a96a;margin:0 0 18px;font-variant-numeric:tabular-nums lining-nums}
.zn-toy h2{font-size:clamp(40px,5.5vw,84px);font-weight:300;margin:0;letter-spacing:.25em;overflow-wrap:break-word;min-width:0}
.zn-toy .songs{writing-mode:vertical-rl;height:min(60vh,520px);margin:0 auto 24px}
.zn-toy .song{font-size:clamp(18px,1.9vw,24px);line-height:2.2;letter-spacing:.12em;margin:0 .4em}
.zn-toy .cap{color:#8c826e;font-size:12px;letter-spacing:.15em;line-height:1.9}
.zn-grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:18px}
.zn-grid div{aspect-ratio:1;border:1px solid #3a3122;outline:8px solid #141210;outline-offset:-9px}
.zn-end{padding:14vh 7vw;border-top:1px solid #1f1b16;text-align:center}
/* 全部の玩具の一覧（本人の指示 11-05）。黒地に、金の細い額の小さな札。動きは無い。必須の 2 種は大きな額のまま。 */
.zn-all{padding:12vh 7vw;border-top:1px solid #1f1b16}
.zn-all .chapter{font-size:12px;letter-spacing:.5em;color:#c9a96a;margin:0 0 12px}
.zn-all h2{font-size:clamp(24px,2.6vw,36px);font-weight:300;letter-spacing:.25em;margin:0 0 18px}
.zn-all .lb{display:inline-block;font-size:11px;letter-spacing:.2em;color:#c9a96a;border:1px solid #6e5a35;padding:0 8px;margin:0 6px}
.zn-all .grid{list-style:none;padding:0;margin:4vh 0 0;display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:26px 18px}
.zn-all li.big{grid-column:span 2;grid-row:span 2}
.zn-all a{border:0;color:#e9e1cf}
.zn-all .pic{aspect-ratio:3/4;background:#141210 center/cover no-repeat;border:1px solid #6e5a35;outline:6px solid #141210;outline-offset:-7px;box-shadow:0 20px 40px rgba(0,0,0,.6)}
.zn-all .big .pic{aspect-ratio:1600/2656}
.zn-all .nopic{display:grid;place-items:center;font-size:11px;color:#9a8e76;letter-spacing:.15em}
.zn-all .nm{display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;overflow:hidden;font-size:13px;letter-spacing:.08em;line-height:1.6;margin-top:10px}
.zn-all .nm small,.zn-all li > small{display:block;font-size:11px;letter-spacing:.15em;color:#9a8e76}
.zn-all li > small a{color:#c9a96a;border-bottom:1px solid rgba(201,169,106,.45)}
@media (max-width:760px){.zn-cover{grid-template-columns:1fr;grid-template-rows:auto auto auto;padding:8vh 8vw;gap:24px}
 .zn-cover .frame,.zn-cover h1,.zn-cover .meta{grid-column:1;justify-self:center;margin:0}
 .zn-cover h1,.zn-cover .meta{writing-mode:horizontal-tb}.zn-cover .frame{width:70vw}
 .zn-toy{grid-template-columns:1fr}.zn-toy .pin{position:relative;height:72vh;height:72svh}
 .zn-all .grid{grid-template-columns:repeat(auto-fill,minmax(110px,1fr))}
 .zn-toy .songs{writing-mode:horizontal-tb;height:auto}}
@media (max-width:680px){.zn-all li.big{grid-column:auto;grid-row:auto}}
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
    # 全部の玩具の一覧は、額装した 2 種の後、奥付の前（本人の指示 11-05）。黒地のジンの性格は保つ（U-23）。
    body += all_toys("zn")
    body += '<p class="cap zn-end">図は国立国会図書館デジタルコレクションの頁（米山堂・1931 年の複製）。新しい絵は作っていない。</p>'
    return page("うつし · 縦読みのジン", body + ONLY, ZINE, "zine")


# ---------------------------------------------------------------- A′ 日本画展の展示（白の壁）
# 本人の言葉（2026-11-04）: 「白の背景で高級感出してもいいよ。美術館の展示みたく」「日本画の展覧会の展示みたいな。山種美術館の展示環境みたいな」。
# 広告代理店の見学者の感想（本人が伝えた）: 「もっと美術品みたく、歴史的価値のあるように見せたサイトの方が良い」。
# A をバインダーの再現のまま磨くか展示の形に作り替えるかを聞いたら、本人は「まだ決めず、どっちも作る」と答えた。だから A はそのまま残し、
# 展示の形を A′ として並べる。順路: 入口の題のパネル → 章ごとに 1 点を白い壁に掛け、作品の札と解説 → 細部 → 出口（玩具の頁へ）。
# 札の中身は出典の記録の値だけ。解説の文は今ある決定の文（README の一言、歌の引用）だけで、作る側の言葉を足さない。
# 動き: 本人の頼み（2026-11-04「この動き、デモサイトでやってみる？」）で、A′ だけに扇の札・スクロールのせり上がり・扇をひらくノブを足した
# （research/19 の「動きを足さない」を本人の明示の頼みで変えた。J-024）。A と C は動かさないまま。
TENJI = """
body.tenji{background:#fcfcfa;color:#2b2722;font-family:"Noto Serif CJK JP","Noto Serif JP","Hiragino Mincho ProN","Yu Mincho",serif;font-feature-settings:"palt" 1}
/* 地は本人の言葉「白の背景」へ戻した（research/24 の 1）。前のクリーム #f6f3ec は作る側の手癖で、生成物の定番の見た目に寄っていた。
   小さな字の灰は色相を保って明るさだけ下げ、白地で 4.5:1 を割らないようにした（同 2）。 */
body.tenji ::selection{background:#e6e1d6;color:#1f1b17}
body.tenji a{color:#6b4f2a;text-decoration:none;border-bottom:1px solid rgba(107,79,42,.35)}
.tenji .switch{font-size:12px;letter-spacing:.2em;padding:14px 5vw;color:#7a7164}.tenji .switch .cap{color:#7c7160}
.tj-hall{min-height:100vh;min-height:100svh;display:grid;grid-template-columns:1fr auto 1fr;align-items:center;padding:0 5vw;box-sizing:border-box}
.tj-hall h1{grid-column:2;writing-mode:vertical-rl;font-weight:400;font-size:clamp(44px,6vw,86px);letter-spacing:.6em;margin:0;color:#1f1b17}
.tj-hall .sub{grid-column:3;justify-self:start;writing-mode:vertical-rl;margin-left:5vw;font-size:clamp(14px,1.3vw,17px);letter-spacing:.5em;line-height:2.4;color:#5d554a}
.tj-hall .en{grid-column:1;justify-self:end;margin-right:5vw;font-size:11px;letter-spacing:.35em;color:#7a7164;text-transform:uppercase;writing-mode:vertical-rl}
.tj-room{min-height:100vh;min-height:100svh;display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.25fr) minmax(0,1fr);gap:4vw;align-items:center;
 padding:12vh 5vw;box-sizing:border-box;border-top:1px solid #ebe8e2}
.tj-room .panel{align-self:start;padding-top:6vh;min-width:0}
.tj-room .chapter{font-size:12px;letter-spacing:.5em;color:#7a7164;margin:0 0 18px}
/* keep-all は和文の名を 1 語に保つが、空白の無い長い名は欄を越える。越える時だけ折る（research/24 の 3）。 */
.tj-room h2{font-weight:400;font-size:clamp(26px,2.8vw,42px);letter-spacing:.18em;margin:0 0 26px;word-break:keep-all;overflow-wrap:break-word;min-width:0}
.tj-room .lead{font-size:14px;line-height:2.2;letter-spacing:.08em;color:#4a4339}
.tj-work{justify-self:center;width:min(100%,46vh);aspect-ratio:1600/2656;padding:3.2%;background:#fffefc;
 border:1px solid #d8cdb6;box-shadow:0 1px 0 #e8e1d2,0 40px 60px -30px rgba(70,55,35,.35),0 2px 6px rgba(70,55,35,.08)}
.tj-work div{width:100%;height:100%}
.tj-side{align-self:end;padding-bottom:6vh}
.tj-label{font-size:12px;line-height:2;letter-spacing:.06em;color:#5d554a;border-left:1px solid #b9a982;padding-left:14px;max-width:22em}
.tj-label .no{display:block;color:#7a7164;letter-spacing:.3em}
.tj-label .ttl{display:block;font-size:18px;letter-spacing:.25em;color:#1f1b17;margin:4px 0}
.tj-songs{writing-mode:vertical-rl;height:min(46vh,420px);margin:0 0 20px auto;font-size:clamp(16px,1.6vw,21px);line-height:2.3;letter-spacing:.14em}
.tj-songs p{margin:0 .3em}
.tj-detail{padding:12vh 5vw;border-top:1px solid #ebe8e2;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:3vw;align-items:start}
.tj-detail figure{margin:0}.tj-detail figure div{aspect-ratio:3/4;background-color:#fffefc;border:1px solid #d8cdb6;box-shadow:0 20px 30px -24px rgba(70,55,35,.4)}
.tj-detail figcaption{font-size:11px;letter-spacing:.2em;color:#7a7164;margin-top:10px}
.tj-exit{padding:14vh 5vw 18vh;text-align:center;border-top:1px solid #ebe8e2}
.tj-exit p{font-size:clamp(20px,2.2vw,28px);letter-spacing:.3em;font-weight:400}
.tj-note{font-size:11px;color:#7a7164;letter-spacing:.1em;padding:0 5vw 8vh;text-align:center}
/* 全部の玩具の一覧（本人の指示 11-05）。白い壁に小さな額を並べる展示の一室。動きは無い（扇の間とせり上がりの外）。 */
.tj-all{padding:10vh 5vw;border-top:1px solid #ebe8e2}
.tj-all .chapter{font-size:12px;letter-spacing:.5em;color:#7a7164;margin:0 0 12px}
.tj-all h2{font-size:clamp(22px,2.4vw,34px);font-weight:400;letter-spacing:.22em;margin:0 0 14px}
.tj-all .cap{font-size:13px;line-height:2;letter-spacing:.06em;color:#4a4339;max-width:46em}
.tj-all .lb{display:inline-block;font-size:11px;letter-spacing:.2em;color:#7a7164;border:1px solid #d8cdb6;padding:0 8px;margin:0 6px}
.tj-all .grid{list-style:none;padding:0;margin:4vh 0 0;display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:24px 16px}
.tj-all li.big{grid-column:span 2;grid-row:span 2}
.tj-all a{border:0;color:#2b2722}
.tj-all .pic{aspect-ratio:3/4;background:#fffefc center/cover no-repeat;border:1px solid #d8cdb6;box-shadow:0 14px 22px -18px rgba(70,55,35,.4)}
.tj-all .big .pic{aspect-ratio:1600/2656}
.tj-all .nopic{display:grid;place-items:center;font-size:11px;color:#7a7164;letter-spacing:.15em}
.tj-all .nm{display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;overflow:hidden;font-size:12px;letter-spacing:.08em;line-height:1.6;margin-top:8px}
.tj-all .nm small,.tj-all li > small{display:block;font-size:11px;letter-spacing:.15em;color:#7a7164}
.tj-all li > small a{color:#6b4f2a;border-bottom:1px solid rgba(107,79,42,.35)}

/* 扇の札（本人の頼み 2026-11-04「この動き、デモサイトでやってみる？」の (1)）。図と寄りの札を、下の 1 点（要）を軸に
   開いた扇のように並べる。御来迎の図の扇と響かせるため。中央の札を大きく手前に。--k は中央からの番手で、角度だけを決める。
   JS が無くても、刷った時の --k のまま開いた扇として完成している。動きは遅い減速だけで、跳ねない（展示の静けさ）。 */
.tj-fan{border-top:1px solid #ebe8e2;padding:8vh 5vw 6vh;text-align:center;--w:clamp(120px,15vw,210px);--step:11deg}
.tj-fan .chapter{font-size:12px;letter-spacing:.5em;color:#7a7164;margin:0 0 2vh}
.fan-stage{position:relative;height:calc(var(--w) * 1.5 * 1.8 + 40px);overflow:hidden;touch-action:pan-y;outline:none}
.fan-stage:focus-visible{box-shadow:0 0 0 1px #b9a982 inset}
.fan-card{position:absolute;left:50%;bottom:calc(var(--w) * 1.5 * .55 + 20px);width:var(--w);margin-left:calc(var(--w) / -2);aspect-ratio:2/3;
 box-sizing:border-box;padding:6px 6px 26px;background:#fffefc;border:1px solid #d8cdb6;border-bottom:1px solid #d8cdb6;
 transform-origin:50% 155%;transform:rotate(calc(var(--k) * var(--step))) scale(var(--s,.92));
 box-shadow:0 18px 26px -20px rgba(70,55,35,.45);transition:transform 1.1s cubic-bezier(.22,.61,.36,1),box-shadow 1.1s ease}
.fan-card.is-c{--s:1.14;box-shadow:0 34px 44px -26px rgba(70,55,35,.55),0 2px 6px rgba(70,55,35,.1)}
.fan-pic{display:block;width:100%;height:100%}
.fan-lb{position:absolute;left:0;right:0;bottom:5px;font-size:11px;letter-spacing:.15em;color:#5d554a;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;padding:0 6px}
.fan-kaname{position:absolute;left:50%;bottom:20px;width:12px;height:12px;margin-left:-6px;border-radius:50%;background:#b9a982;box-shadow:0 0 0 3px #fcfcfa,0 0 0 4px #d8cdb6}
.fan-ctl{display:flex;gap:2em;justify-content:center;align-items:center;margin-top:2vh;font-size:13px;letter-spacing:.2em;color:#5d554a}
.fan-ctl button{font:inherit;color:#6b4f2a;background:none;border:0;border-bottom:1px solid rgba(107,79,42,.35);padding:4px 2px;cursor:pointer}
.fan-ctl button:disabled{color:#a59b8b;border-color:transparent;cursor:default}
.fan-cap{min-width:8em}

/* 「扇をひらく」（本人の頼みの (3) を静かにした物）。派手な 3D のねじれは持ち込まず、線の扇の開く角だけをノブで動かす。
   筒の中の仕組みは描かない（仮説を出さないため。予想が先、F9.prediction）。--t は骨の位置（-0.5〜0.5）、--a が開く角。 */
.tj-ogi{padding:6vh 5vw 10vh;text-align:center}
.tj-ogi svg{width:min(360px,80vw);height:auto;display:block;margin:0 auto}
.tj-ogi .pl{transform-box:view-box;transform-origin:120px 128px;transform:rotate(calc(var(--a) * var(--t)))}
.tj-ogi label{display:inline-flex;gap:1em;align-items:center;font-size:13px;letter-spacing:.2em;color:#5d554a;margin-top:2vh}
.tj-ogi input{accent-color:#8a6d3b;width:min(240px,50vw)}
.tj-ogi .cap{font-size:11px;letter-spacing:.1em;color:#7a7164;margin-top:1.2vh}

/* スクロールでせり上がる（本人の頼みの (2)）。CSS のスクロール連動だけで、見える状態から始める（opacity を 0 にしない）。
   なぜ: 速く読む人から中身を隠さないため（research/19 の「全部の節に演出を付けない」を、隠さない形で守る）。
   図と札で始まりをずらし、段差をつける。効かない閲覧器では何も起きず、止まった展示のまま。 */
@supports (animation-timeline: view()){
 @media (prefers-reduced-motion:no-preference){
  .tj-room .tj-work{animation:tj-rise-work linear both;animation-timeline:view();animation-range:entry 0% cover 38%}
  .tj-room .tj-label{animation:tj-rise linear both;animation-timeline:view();animation-range:entry 15% cover 45%}
  .tj-detail figure{animation:tj-rise linear both;animation-timeline:view();animation-range:entry 0% cover 30%}
  .tj-detail figure:nth-child(2){animation-range:entry 10% cover 36%}
  .tj-detail figure:nth-child(3){animation-range:entry 20% cover 42%}
  .tj-detail figure:nth-child(4){animation-range:entry 30% cover 48%}
 }
}
@keyframes tj-rise-work{from{transform:translateY(28px) rotate(-.8deg);box-shadow:0 1px 0 #e8e1d2,0 16px 24px -18px rgba(70,55,35,.25),0 2px 6px rgba(70,55,35,.08)}
 to{transform:none;box-shadow:0 1px 0 #e8e1d2,0 40px 60px -30px rgba(70,55,35,.35),0 2px 6px rgba(70,55,35,.08)}}
@keyframes tj-rise{from{transform:translateY(18px) rotate(.6deg)}to{transform:none}}
/* 動きを減らす設定の人には、扇は止まった扇のまま（札の入れ替えは瞬時）、せり上がりも無し。 */
@media (prefers-reduced-motion:reduce){.fan-card{transition:none}}

@media (max-width:820px){.tj-room{grid-template-columns:minmax(0,1fr);gap:6vh}.tj-work{width:72vw}.tj-songs{writing-mode:horizontal-tb;height:auto}
 .tj-detail{grid-template-columns:minmax(0,1fr) minmax(0,1fr)}.tj-hall{grid-template-columns:1fr;justify-items:center;gap:4vh;padding:10vh 5vw}
 .tj-hall h1,.tj-hall .sub,.tj-hall .en{grid-column:1;margin:0;justify-self:center}
 .tj-fan{--w:clamp(110px,30vw,150px);--step:9deg}
 .tj-all .grid{grid-template-columns:repeat(auto-fill,minmax(105px,1fr))}}
@media (max-width:680px){.tj-all li.big{grid-column:auto;grid-row:auto}}
"""
KANJI = "一二三四五六七八九十"
DETAIL_POS = ("30% 30%", "72% 40%", "35% 75%", "70% 82%")

# 扇の札を動かす小さな台本。矢印の釦・キーボードの左右・指で払う、の 3 つで中央の札を入れ替える。
# なぜ IntersectionObserver を使わないか: 見えた時に起こす仕掛けは入口に置かない決まり（research/19、試験で固定）。押した時だけ動く。
# 端の札を押した時は、玩具の頁へ飛ばずに先に中央へ回す（扇を回す手応えを先に返す）。中央の札を押せば玩具の頁へ入る。
FAN_JS = """<script>(()=>{const d=document.getElementById('tj-fan');if(!d)return;
const st=d.querySelector('.fan-stage'),cs=[...d.querySelectorAll('.fan-card')],cap=d.querySelector('.fan-cap'),
pv=d.querySelector('.fan-prev'),nx=d.querySelector('.fan-next');let c=+d.dataset.c;
function set(n){c=Math.max(0,Math.min(cs.length-1,n));cs.forEach((e,i)=>{const k=i-c;e.style.setProperty('--k',k);
e.style.zIndex=50-Math.abs(k);e.classList.toggle('is-c',k===0);e.tabIndex=k===0?0:-1});
cap.textContent=cs[c].dataset.name;pv.disabled=c===0;nx.disabled=c===cs.length-1}
pv.hidden=nx.hidden=false;pv.onclick=()=>set(c-1);nx.onclick=()=>set(c+1);
st.addEventListener('keydown',e=>{if(e.key==='ArrowLeft'){set(c-1);e.preventDefault()}else if(e.key==='ArrowRight'){set(c+1);e.preventDefault()}});
cs.forEach((e,i)=>e.addEventListener('click',ev=>{if(i!==c){ev.preventDefault();set(i)}}));
let x0=null;st.addEventListener('pointerdown',e=>{x0=e.clientX});
st.addEventListener('pointerup',e=>{if(x0===null)return;const dx=e.clientX-x0;x0=null;if(Math.abs(dx)>40)set(c+(dx<0?1:-1))});
set(c)})();
(()=>{const r=document.getElementById('ogi-range'),s=document.getElementById('ogi-svg');if(!r||!s)return;
const f=()=>s.style.setProperty('--a',r.value+'deg');r.addEventListener('input',f);f()})();</script>"""


def _fan_cards(ts):
    """扇に並べる札。玩具 1 の寄り → 玩具 1 の図 → 玩具 2 の図 → 玩具 2 の寄り、の順にし、中央に図が来るようにする。
    寄りの場所は部分の段（tj-detail）と同じ。図に見える所の写しだけで、名前は「部分」に留める（仕組みの名を出さない）。"""
    cards = []
    for j, t in enumerate(ts):
        name = esc(t["toy"])
        pic = {"href": f"/toy/{t['sid']}", "name": name, "style": _bg(t["sid"], framed_pos(t["sid"]), FRAMED)}
        details = [{"href": "", "name": f"{name} 部分 {k}", "style": _bg(t["sid"], p, "300%")} for k, p in enumerate(DETAIL_POS, 1)]
        cards += (details + [pic]) if j % 2 == 0 else ([pic] + details)
    return cards


def fan_deck(ts):
    cards = _fan_cards(ts)
    if not cards:
        return ""
    # 中央は 1 つ目の玩具の図。偶数枚でも図が真ん中に来るよう、寄りの数（4）を中央の番手にする。
    c = min(len(DETAIL_POS), len(cards) - 1)
    items = []
    for i, cd in enumerate(cards):
        k = i - c
        tag, href = ("a", f' href="{cd["href"]}"') if cd["href"] else ("div", "")
        items.append(f'<{tag} class="fan-card{" is-c" if k == 0 else ""}"{href} data-name="{cd["name"]}" style="--k:{k};z-index:{50 - abs(k)}">'
                     f'<span class="fan-pic" style="{cd["style"]}"></span><span class="fan-lb">{cd["name"]}</span></{tag}>')
    return (f'<section class="tj-fan" id="tj-fan" data-c="{c}" aria-label="扇の札"><p class="chapter">扇の間</p>'
            f'<div class="fan-stage" tabindex="0" aria-label="扇の札。左右の矢印で回す">{"".join(items)}<i class="fan-kaname"></i></div>'
            f'<div class="fan-ctl"><button type="button" class="fan-prev" hidden aria-label="左の札へ">◁ 左へ</button>'
            f'<span class="fan-cap" aria-live="polite">{cards[c]["name"]}</span>'
            f'<button type="button" class="fan-next" hidden aria-label="右の札へ">右へ ▷</button></div></section>')


def ogi_slider(n=13, start=150):
    """線で描いた扇。骨 n 本の楔を要（120,128）から立て、開く角 --a で回すだけ。御来迎の図の扇の形（閉じた → 半円）に合わせた。
    楔の幅は全開の 180° を n-1 で割った角。閉じると楔が重なって 1 本の骨になる。"""
    import math
    hw = math.radians(180 / (n - 1) / 2)
    r0, r1, cx, cy = 34, 112, 120, 128

    def pt(r, a):
        return f"{cx + r * math.sin(a):.1f},{cy - r * math.cos(a):.1f}"
    wedge = f"M{pt(r0, -hw)} L{pt(r1, -hw)} A{r1},{r1} 0 0 1 {pt(r1, hw)} L{pt(r0, hw)} A{r0},{r0} 0 0 0 {pt(r0, -hw)}Z"
    pleats = "".join(f'<g class="pl" style="--t:{i / (n - 1) - .5:.4f}"><path d="{wedge}" fill="{"#f4f0e7" if i % 2 else "#e7e0d1"}" stroke="#b9a982" stroke-width=".6"/>'
                     f'<line x1="{cx}" y1="{cy}" x2="{cx}" y2="{cy - r0}" stroke="#8a6d3b" stroke-width="1.4"/></g>' for i in range(n))
    return (f'<section class="tj-ogi" id="tj-ogi"><svg id="ogi-svg" viewBox="0 0 240 140" style="--a:{start}deg" role="img" aria-label="線で描いた扇">{pleats}'
            f'<circle cx="{cx}" cy="{cy}" r="4" fill="#8a6d3b"/></svg>'
            f'<label>扇をひらく <input id="ogi-range" type="range" min="0" max="180" value="{start}" aria-label="扇をひらく角"></label>'
            '<p class="cap">開く角だけの線の絵。どう開くかは描いていない。それを紙で確かめる。</p></section>')


def tenji():
    ts = toys()
    body = switch("/look/tenji")
    body += ('<section class="tj-hall"><p class="en">Lost toys of Edo · 1773</p><h1>うつし</h1>'
             '<p class="sub">江都二色より<br>うしなわれた玩具の動きを<br>紙で実験して確かめる</p></section>')
    # 全部の玩具の一覧は扇の間の次の一室（本人の指示 11-05）。扇の札と動きは変えない。
    body += fan_deck(ts) + ogi_slider() + all_toys("tj")
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
                       for k, p in enumerate(DETAIL_POS, 1))
        body += f'<section class="tj-detail" id="detail-{i}">{figs}</section>'
        body += (f'<section class="tj-exit"><p>どこが動くと思いますか。</p><a href="/toy/{t["sid"]}">予想を書いてひらく</a></section>')
    body += '<p class="tj-note">図は国立国会図書館デジタルコレクションの頁（米山堂・1931 年の複製）。扇の開く角を示す線の絵のほかに、新しい絵は作っていない。</p>'
    return page("うつし · 日本画展の展示", body + ONLY + FAN_JS, TENJI, "tenji")


PAGES = {"tenji": tenji, "zine": zine}
