"""入口のルックブック（J-024）。本人が 5 案を見比べ、A 大判写真集と C 縦読みのジンを残した（2026-11-04）。
見開き型・冊子型・B 和綴じ帖は外した。その後 A も外した（本人の決定 2026-11-05 朝）。
今の入口は A′ 白の展示と C 黒のジンの 2 つで、サイトごとに 1 つを / に出す（--look）。

判断の芯: 案ごとに佇まい（表紙・見開きの構成・題の組み方）だけを変え、守る線は同じにする。
新しい絵は作らず、NDL の図の頁とその寄りだけを使う。歌は人が確かめた読みだけを引用の印つきで出す。
入口には仮説を出さない（絵を先に見せるため）。どの案も最後は同じ玩具の頁（/toy/）へ入る。
"""
from omochae import hypotheses

from . import skin, wording
from .play_server import ROOT, esc, page, source, sources

# 残した 2 つの入口。大判（A）と外した 3 案は出さない（本人の決定 11-05 朝「日本画かジンで行くから、他のデザインは要らない」）。
LOOKS = {
    "tenji": "A′ 日本画展の展示",
    "zine": "C 縦読みのジン",
}


# 表紙の題の下（白の展示は副題のすぐ下）に、説明の頁（序の頁 /about を「このサイトについて」の頁にする）への道を 1 つ。
# 本人のサイトレビュー 11-07 午後の 1「…サイトの目的や AI でやっていることや仕組みについて説明するページを作ってそのリンクを添えた方が良いかも？
# そうするなら、トップページの『このサイトは、まだ育っている途中です。型紙をよくしていくのは、作ってみるあなたです。』もいらなそう」と、
# 窓口の決め 132926 の ③④（UX の担当の設計 state/site-review-123-20261107.md）。前はここに表紙の 2 行（本人の決定 11-06）があったので外した。
# 小さな字の道にし、大きいボタンにしない（入口の大きいボタンは「えらぶ」1 つの決まり）。題の縦書きの流れを崩さないよう、横書きで小さく置く（前の 2 行と同じ場所）。
ABOUT = "このサイトについて"


def about_link():
    return f'<p class="about-go"><a href="/about">{esc(ABOUT)}</a></p>'


def switch(look):
    """入口の頭の帯。内側の頁と同じ帯を使う（入口から入った所で帯が変わらないように。要件 2）。"""
    return skin.nav(look, "/", "/")


def toys():
    """図の写しが手元に無い玩具も並べる。入口なので、写しの有無で玩具が消えると入れなくなるため。
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


# 額に入れる図は、複写の台の黒い縁が額の中に見えないよう、枠と同じ比のまま少し大きく敷く。
FRAMED = "112% 112%"


def framed_pos(sid):
    """綴じの影は頁の綴じ側に出る。左頁（L）は左、右頁（R）は右に濃いので、反対側へ寄せて影を落とす。"""
    return "15% 50%" if source(sid).get("side") == "R" else "85% 50%"


def _nopic(t):
    return "" if t["pic"] else f'<p class="cap"><a href="{esc(t["image_url"])}">図を見る（国立国会図書館）</a></p>'


QUOTE = f"原文の引用。確かめた人: {wording.MAKER}"

# 見比べるための写しを撮る補助。?only=<節の id> で、その節だけを画面の頭に出す。
# なぜ: 縦に流れる案は、頭からしか写しを撮れず、途中の見開きを並べて比べられないため。ふだんの閲覧には効かない。
ONLY = """<script>(()=>{const id=new URLSearchParams(location.search).get('only');if(!id)return;
const st=document.createElement('style');st.textContent='section:not(#'+CSS.escape(id)+'),.nav,.ab-end,main>p{display:none!important}';document.head.appendChild(st)})();</script>"""

# ---------------------------------------------------------------- 全部の玩具の一覧（A′ と C の両方の入口で使う）
# A 大判写真集の作りはここにあったが、本人の決定（2026-11-05 朝）で外した。参照のルックブックの観察は research/19、経過は J-024 に残る。
def all_toys(prefix):
    """全部の玩具の一覧（本人の指示 11-05「88 種のおもちゃから 1 個選ぶ」。要件 L-02: 入口から試作の玩具にも入れる）。
    必須の 2 種を大きく、試作の 81 種を小さな札で並べる。試作の写し（out/sources）は棚卸しの箱で切り出した物なので、全体が入る形で敷く
    （必須の 2 種は頁の半分の写しなので、額の敷き方 FRAMED で寄せる）。写しが無い玩具は名前だけにし、国立国会図書館への道を添える。
    仮説の名前と動き方は一覧に出さない（絵を先に見せるため）。名前は作る側の見立てで確かめ待ち（U-01）。動きは付けない。"""
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
        big = ' class="big"' if main else ""
        items.append(f'<li{big}><a href="/toy/{esc(sid)}">{pic}<span class="nm">{esc(data["toy"])}</span></a>{more}</li>')
    n = len(items)
    return (f'<section class="{prefix}-all" id="all-toys" aria-label="全部の玩具"><p class="chapter">おもちゃ</p>'
            f'<h2>{n} のおもちゃから、1 つ選ぶ</h2>'
            '<p class="cap">どれも図と歌だけが残った玩具。選ぶと、すぐ型紙を刷って作れる。型紙は正解ではなく、AI が考えた仮説。'
            '先頭の 2 つのほかは全部を型紙にする途中の試作で、名前は作る側の見立てで、まだ確かめていません。</p>'
            f'<ul class="grid">{"".join(items)}</ul></section>')


# 2 つの入口の画面いっぱいの高さは svh（スマホで URL の帯の裏に隠れないため）。
ZINE = """
body.zine{background:#0b0a09;color:#e9e1cf;font-family:"Noto Serif CJK JP","Noto Serif JP","Hiragino Mincho ProN","Yu Mincho",serif;
 font-feature-settings:"palt" 1}
body.zine a{color:#c9a96a;text-decoration:none;border-bottom:1px solid rgba(201,169,106,.45)}
/* 細い字も 4.5:1 を割らないよう明るさだけ上げ、色相は保つ（research/24 の 2）。選んだ時は黒地に金の薄い面（同 5）。 */
body.zine ::selection{background:rgba(201,169,106,.35);color:#f5eedf}
.zn-cover{min-height:100vh;min-height:100svh;position:relative;display:grid;grid-template-columns:1fr minmax(0,44vh) 1fr;align-items:center;
 background:radial-gradient(ellipse 46% 62% at 50% 46%,#1d1914 0%,#0b0a09 72%)}
.zn-cover .frame{grid-column:2;aspect-ratio:1600/2656;padding:18px;background:#141210;border:1px solid #6e5a35;
 box-shadow:0 0 0 6px #0b0a09,0 0 0 7px #3a3122,0 30px 80px rgba(0,0,0,.7)}
.zn-cover .frame div{width:100%;height:100%}
.zn-cover h1{grid-column:3;justify-self:start;margin:0 0 0 6vw;writing-mode:vertical-rl;font-weight:300;
 font-size:clamp(40px,6.5vw,92px);letter-spacing:.5em;color:#efe6d2}
/* 次へ進む釦（段 0）は、題と組にして 1 つだけ。広い幅は右の欄で縦書きの題の下、狭い幅は題のすぐ後（額より先）に置く。
   額の下の段に置くと、表紙が画面の高さいっぱいなので、幅 1440×900 でも 846px（最初の画面の外）だった。押せる大きさ（64px）を守り、金の細い枠で黒地の性格を崩さない */
.zn-title{grid-column:3;justify-self:start;margin:0 0 0 6vw;display:flex;flex-direction:column;align-items:flex-start;gap:28px}.zn-title h1{margin:0}
.zn-title .road{margin:0}
body.zine a.road-go{display:inline-flex;align-items:center;justify-content:center;min-height:64px;min-width:10em;padding:0 32px;box-sizing:border-box;border:1px solid #c9a96a;border-radius:2px;color:#efe6d2;font-size:20px;letter-spacing:.5em}
.zn-cover .meta{grid-column:1;justify-self:end;margin-right:6vw;writing-mode:vertical-rl;color:#9a8e76;font-size:13px;letter-spacing:.45em}
.zn-cover .about-go{grid-column:1/-1;justify-self:center;margin:0 0 6vh;font-size:13px;line-height:2.1;letter-spacing:.12em;color:#b9ae97;text-align:center}.zn-cover .about-go a{color:inherit;text-underline-offset:.3em}
@media (max-width:1100px),(pointer:coarse){body .about-go a{display:inline-flex;align-items:center;min-height:44px;border-bottom:0;text-decoration-line:underline;text-decoration-thickness:1px;text-decoration-color:color-mix(in srgb,currentColor 40%,transparent);text-underline-offset:.35em}}  /* 触る画面の押す所の床（skin.TAP_FLOOR と同じ 44px）。字の下の線は箱の下の端でなく字のすぐ下に（線は字の線で引く） */
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
.zn-all .lb{display:inline-block;font-size:12px;letter-spacing:.2em;color:#c9a96a;border:1px solid #6e5a35;padding:0 8px;margin:0 6px}
.zn-all .grid{list-style:none;padding:0;margin:4vh 0 0;display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:26px 18px}
.zn-all li.big{grid-column:span 2;grid-row:span 2}
.zn-all a{border:0;color:#e9e1cf}
.zn-all .pic{aspect-ratio:3/4;background:#141210 center/cover no-repeat;border:1px solid #6e5a35;outline:6px solid #141210;outline-offset:-7px;box-shadow:0 20px 40px rgba(0,0,0,.6)}
.zn-all .big .pic{aspect-ratio:1600/2656}
.zn-all .nopic{display:grid;place-items:center;font-size:12px;color:#9a8e76;letter-spacing:.15em}
.zn-all .nm{display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;overflow:hidden;font-size:13px;letter-spacing:.08em;line-height:1.6;margin-top:10px}
.zn-all .nm small,.zn-all li > small{display:block;font-size:12px;letter-spacing:.15em;color:#9a8e76}
.zn-all li > small a{color:#c9a96a;border-bottom:1px solid rgba(201,169,106,.45)}
@media (max-width:760px){.zn-cover{grid-template-columns:1fr;grid-template-rows:auto auto auto auto;padding:8vh 8vw;gap:24px}
 .zn-cover .about-go{grid-column:1;margin:0;order:1}  /* 狭い幅は 題と えらぶ → 説明の頁への道 → 額 の順（道も額より先） */
 .zn-cover .frame,.zn-cover h1,.zn-cover .meta{grid-column:1;justify-self:center;margin:0}
 .zn-title{grid-column:1;justify-self:center;margin:0;align-items:center;gap:18px;order:1}.zn-cover .frame{order:2}
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
    body = switch("zine")
    body += (f'<section class="zn-cover"><p class="meta">{esc(DOOR_LINE)}</p>'
             f'<div class="frame"><div style="{_bg(first, framed_pos(first), FRAMED)}"></div></div><div class="zn-title"><h1>うつし</h1>{ROAD_GO}</div>{about_link()}</section>')
    # 北斎漫画（本人の決定 11-05 の案 2）。縦読みの章の頭に置く: 玩具の章より先に「絵は動きを止めて残した」の筋を見せるため。
    from .hokusai import scroll_section

    body += scroll_section()
    for i, t in enumerate(ts, 1):
        src = source(t["sid"])
        song = "".join(f'<p class="song">{esc(x)}</p>' for x in t["song"])
        tiles = "".join(f'<div style="{_bg(t["sid"], p, "300%")}"></div>' for p in ("30% 30%", "72% 40%", "35% 75%", "70% 82%"))
        # 図は左に額装して留めたまま、右で札・歌・細部・入口が流れる。図から目を離さずに読む形。
        body += (f'<section id="look-{i}" class="zn-toy"><div class="pin"><div class="frame"><div style="{_bg(t["sid"], framed_pos(t["sid"]), FRAMED)}"></div></div></div><div class="flow">'
                 f'<div><p class="big">No. {i:02d}</p><h2>{esc(t["toy"])}</h2>{_label(t, src)}{_nopic(t)}</div>'
                 f'<div id="song-{i}"><div class="songs">{song}</div><p class="cap">{QUOTE} · {esc(t["holding"])}</p></div>'
                 f'<div><div class="zn-grid">{tiles}</div><p class="cap">図の細部</p></div>'
                 f'<div><p class="h2" style="font-size:clamp(22px,2.4vw,30px);letter-spacing:.2em;font-weight:300">紙で作って、確かめる。</p><p><a href="/toy/{t["sid"]}">型紙をひらく</a></p></div></div></section>')
    # 全部の玩具の一覧は、額装した 2 種の後、奥付の前（本人の指示 11-05）。黒地のジンの性格は保つ（U-23）。
    body += all_toys("zn")
    body += '<p class="cap zn-end">図は国立国会図書館デジタルコレクションの頁（米山堂・1931 年の複製）。新しい絵は作っていない。</p>'
    return page("うつし", body + ONLY, ZINE + skin.entrance_style("zine"), "zine")


# ---------------------------------------------------------------- A′ 日本画展の展示（白の壁）
# 本人の言葉（2026-11-04）: 「白の背景で高級感出してもいいよ。美術館の展示みたく」「日本画の展覧会の展示みたいな。山種美術館の展示環境みたいな」。
# 広告代理店の見学者の感想（本人が伝えた）: 「もっと美術品みたく、歴史的価値のあるように見せたサイトの方が良い」。
# A をバインダーの再現のまま磨くか展示の形に作り替えるかを聞いたら、本人は「まだ決めず、どっちも作る」と答えた。だから A はそのまま残し、
# 展示の形を A′ として並べる。順路: 入口の題のパネル → 章ごとに 1 点を白い壁に掛け、作品の札と解説 → 細部 → 出口（玩具の頁へ）。
# 札の中身は出典の記録の値だけ。解説の文は今ある決定の文（README の一言、歌の引用）だけで、作る側の言葉を足さない。
# 動き: 本人の頼み（2026-11-04「この動き、デモサイトでやってみる？」）で、A′ だけに扇の札・スクロールのせり上がり・扇をひらくノブを足した
# （research/19 の「動きを足さない」を本人の明示の頼みで変えた。J-024）。C は動かさないまま。
# 扇の札（扇の間）と扇をひらくノブは 11-07 に外した（本人の言葉「扇の間要らない」。J-024 の追記）。残る動きはせり上がりだけ。
# 入口の最初の画面の次へ進む釦（UX の見直しの段 0、本人の決定 11-06。research/36 の「道しるべの言葉は えらぶ・つくる・のこす・もちよる」）。
# 入口の最初の画面で押せる物は頭の帯だけで、最初の玩具は 1197px 下だった（幅 390、research/36 の数）。字は道しるべの 1 語だけで、新しい字は足さない。
# 行き先は絵で選ぶ頁（/toys）。入口の中の一覧は額装した 2 種の後にあり遠いので、近い方へ向ける
ROAD_GO = '<p class="road"><a class="road-go" href="/toys">えらぶ</a></p>'
# 黒のジンの表紙の 1 行（字は変えない）。白に統一した後は、白の扉の額の下に出す（本人の決定 11-06）。
DOOR_LINE = "江都二色　安永二年　うしなわれた玩具"

TENJI = """
body.tenji{background:#fcfcfa;color:#2b2722;font-family:"Noto Serif CJK JP","Noto Serif JP","Hiragino Mincho ProN","Yu Mincho",serif;font-feature-settings:"palt" 1}
/* 地は本人の言葉「白の背景」へ戻した（research/24 の 1）。前のクリーム #f6f3ec は作る側の手癖で、生成物の定番の見た目に寄っていた。
   小さな字の灰は色相を保って明るさだけ下げ、白地で 4.5:1 を割らないようにした（同 2）。 */
body.tenji ::selection{background:#e6e1d6;color:#1f1b17}
body.tenji a{color:#6b4f2a;text-decoration:none;border-bottom:1px solid rgba(107,79,42,.35)}
.tj-hall{min-height:100vh;min-height:100svh;display:grid;grid-template-columns:1fr auto 1fr;align-items:center;padding:0 5vw;box-sizing:border-box}
.tj-hall h1{grid-column:2;writing-mode:vertical-rl;font-weight:400;font-size:clamp(44px,6vw,86px);letter-spacing:.6em;margin:0;color:#1f1b17}
.tj-hall .sub{grid-column:3;justify-self:start;writing-mode:vertical-rl;margin-left:5vw;font-size:clamp(14px,1.3vw,17px);letter-spacing:.5em;line-height:2.4;color:#5d554a}
.tj-hall .en{grid-column:1;justify-self:end;margin-right:5vw;font-size:12px;letter-spacing:.35em;color:#7a7164;text-transform:uppercase;writing-mode:vertical-rl}
/* 次へ進む釦（段 0）は題の 3 列の下の段に 1 つだけ。白の壁の展示に合わせ、塗らずに細い枠で示す */
/* 字の並びは 題 → 釦 → 副題。幅の狭い画面（1 列に積む）では、副題まで積むと釦が最初の画面の外に出る（幅 390 で 1015px）ので、題のすぐ後に置く。
   広い画面は 3 列の縦書きの下の段（2 行目）に置く */
.tj-hall .road{grid-column:1/-1;grid-row:2;justify-self:center;margin:0}
body.tenji a.road-go{display:inline-flex;align-items:center;justify-content:center;min-height:64px;min-width:10em;padding:0 32px;box-sizing:border-box;border:1px solid #6b4f2a;border-radius:2px;color:#1f1b17;font-size:20px;letter-spacing:.5em}
/* 扉: 題の間の次の 1 室に、黒の表紙にあった最初の玩具の額と 1 行を掛ける（本人の決定 11-07「前の白の案の間」は B＝入口の絵の前の間。
   最初の画面は題と「えらぶ」と副題だけにして、題のまわりの空きを残す） */
.tj-door{min-height:100vh;min-height:100svh;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:28px;padding:10vh 5vw;box-sizing:border-box;border-top:1px solid #ebe8e2}
.tj-door .tj-work{width:min(100%,46vh)}.tj-door .tj-work div{width:100%;height:100%}
.tj-door .meta{margin:0;font-size:13px;letter-spacing:.45em;color:#7a7164}
.tj-hall .about-go{grid-column:1/-1;justify-self:center;margin:0 0 6vh;font-size:clamp(13px,1.1vw,15px);line-height:2.1;letter-spacing:.12em;color:#5d554a;text-align:center}.tj-hall .about-go a{color:inherit;text-underline-offset:.3em}
@media (max-width:1100px),(pointer:coarse){body .about-go a{display:inline-flex;align-items:center;min-height:44px;border-bottom:0;text-decoration-line:underline;text-decoration-thickness:1px;text-decoration-color:color-mix(in srgb,currentColor 40%,transparent);text-underline-offset:.35em}}  /* 触る画面の押す所の床（skin.TAP_FLOOR と同じ 44px）。字の下の線は箱の下の端でなく字のすぐ下に（線は字の線で引く） */
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
.tj-detail figcaption{font-size:12px;letter-spacing:.2em;color:#7a7164;margin-top:10px}
.tj-exit{padding:14vh 5vw 18vh;text-align:center;border-top:1px solid #ebe8e2}
.tj-exit p{font-size:clamp(20px,2.2vw,28px);letter-spacing:.3em;font-weight:400}
.tj-note{font-size:12px;color:#7a7164;letter-spacing:.1em;padding:0 5vw 8vh;text-align:center}
/* 全部の玩具の一覧（本人の指示 11-05）。白い壁に小さな額を並べる展示の一室。動きは無い（せり上がりの外）。 */
.tj-all{padding:10vh 5vw;border-top:1px solid #ebe8e2}
.tj-all .chapter{font-size:12px;letter-spacing:.5em;color:#7a7164;margin:0 0 12px}
.tj-all h2{font-size:clamp(22px,2.4vw,34px);font-weight:400;letter-spacing:.22em;margin:0 0 14px}
.tj-all .cap{font-size:13px;line-height:2;letter-spacing:.06em;color:#4a4339;max-width:46em}
.tj-all .lb{display:inline-block;font-size:12px;letter-spacing:.2em;color:#7a7164;border:1px solid #d8cdb6;padding:0 8px;margin:0 6px}
.tj-all .grid{list-style:none;padding:0;margin:4vh 0 0;display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:24px 16px}
.tj-all li.big{grid-column:span 2;grid-row:span 2}
.tj-all a{border:0;color:#2b2722}
.tj-all .pic{aspect-ratio:3/4;background:#fffefc center/cover no-repeat;border:1px solid #d8cdb6;box-shadow:0 14px 22px -18px rgba(70,55,35,.4)}
.tj-all .big .pic{aspect-ratio:1600/2656}
.tj-all .nopic{display:grid;place-items:center;font-size:12px;color:#7a7164;letter-spacing:.15em}
.tj-all .nm{display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;overflow:hidden;font-size:12px;letter-spacing:.08em;line-height:1.6;margin-top:8px}
.tj-all .nm small,.tj-all li > small{display:block;font-size:12px;letter-spacing:.15em;color:#7a7164}
.tj-all li > small a{color:#6b4f2a;border-bottom:1px solid rgba(107,79,42,.35)}

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

@media (max-width:820px){.tj-room{grid-template-columns:minmax(0,1fr);gap:6vh}.tj-work{width:72vw}.tj-songs{writing-mode:horizontal-tb;height:auto}
 .tj-detail{grid-template-columns:minmax(0,1fr) minmax(0,1fr)}.tj-hall{grid-template-columns:1fr;justify-items:center;gap:4vh;padding:10vh 5vw}
 .tj-hall h1,.tj-hall .sub,.tj-hall .en{grid-column:1;margin:0;justify-self:center}.tj-hall .road{grid-column:1;grid-row:auto}
 /* 1 列に積む時は、英字の小さな 1 行だけ横書きにする（縦書きのままだと 246px を取り、375×667 で釦が最初の画面の外に出た）。題と副題は縦書きのまま */
 .tj-hall .en{writing-mode:horizontal-tb}
 .tj-all .grid{grid-template-columns:repeat(auto-fill,minmax(105px,1fr))}}
@media (max-width:680px){.tj-all li.big{grid-column:auto;grid-row:auto}}
"""
KANJI = "一二三四五六七八九十"
DETAIL_POS = ("30% 30%", "72% 40%", "35% 75%", "70% 82%")

# 入口を えらぶ にする（本人のサイト体験レビュー 11-07 の 4・5・1。UX の設計 state の review-fixes の A）。
# 本人の言葉（窓口の要点）: 「入口と選ぶは分けない。最初の頁そのものを選ぶにする（江戸二色の話だけ書いて、押させるのでなく最初から選べる形）」
# 「選ぶでは『まずはここから』で御来迎と張子の首振り虎の 2 つを前に出し、どちらかを選んで作る誘導に。他も選べるが控えめに」
# 「83 のおもちゃが言葉だけ並んでいるのが嫌。絵で見える形に」。
# 前は 題の間（題・えらぶ の釦・副題）→ 扉の額 → 全部の玩具の一覧 → 章ごとの部屋（歌・部分・型紙をひらく）の順で、選ぶには えらぶ を押して /toys へ行った。
# 今は 題（題・副題・表紙の 2 行）→ 2 つの大きな札 → 83 の原画の敷き詰め（小さく）。えらぶ の釦は外し（押させない）、/toys は / へ送る（play_server）。
# 章ごとの部屋（歌・部分）は外した: 歌は玩具の頁の頭（原画と歌）に在り、入口に同じ物を 2 度置かないため。
MAZU = "まずはここから"  # 2 つの大きな札の見出し（本人の言葉そのもの。本人の「反映してください。レビューの要点の通りで」と窓口の決め 11-07）


def _mazu(ts, photos=True):
    """「まずはここから」の 2 枚（必須の 2 種）。札そのものが玩具の頁（つくる）への口。額の敷き方は前の章の部屋と同じ（FRAMED）。"""
    # 絵は中くらいの写し（/picture/<印>/mid）を img で、先に読む（fetchpriority="high"）。元の写しは最初の画面で読まない（toys.SIZES の注）。
    # 前は背景の絵（CSS）にしていたが、遅い回線（下り 1.6Mbps・往復 150ms、トンネル越し）で、下の並びの小さい写しと取り合って 2 枚が届くのに
    # 5.7 秒かかった（11-07 に Chromium で測った）。背景の絵は読む順が後ろになるため、img にして先に読ませる。
    # 額の敷き方（FRAMED の 112% と綴じの反対側）は、枠の中で 1.12 倍に広げて寄せる形で同じに見せる
    def pic(t):
        sid = t["sid"]
        if not (ROOT / "out/sources" / f"{sid}.jpg").exists():
            return f'<span class="pic" style="{_bg(sid)}" role="img" aria-label="{esc(t["toy"])}の図"></span>'
        x = framed_pos(sid).split()[0]
        from . import toys as toys_page

        # 下敷きはごく小さな絵を頁に書いた物（toys.tiny_picture）。字と一緒に届き、中くらいの写しが届くと上に重なる
        under = f"background:#d9d2c3 url({toys_page.tiny_picture(sid)}) {x} 50%/{FRAMED} no-repeat"  # 額の敷き方と同じ大きさ（黒い縁を出さない）
        return (f'<span class="pic" style="{under}"><img src="/picture/{esc(sid)}/mid" alt="{esc(t["toy"])}の図" fetchpriority="high" decoding="async" '
                f'style="object-position:{x} 50%;transform-origin:{x} 50%"></span>')
    from . import made

    def photo(t):
        # 作ってみた実物の写真（本人のサイト体験レビュー 11-07 の 2）。人が確かめた写真がある時だけ、額の右下に小さく重ねる。
        # 写真が無い時は何も置かない（玩具の頁の頭と同じ。窓口の決め 125731・(b)）
        url = made.photo(t["sid"]) if photos else None
        return f'<span class="tj-made"><img src="{esc(url)}" alt="{esc(made.PHOTO)}の写真" decoding="async"></span>' if url else ""
    cards = "".join(f'<a class="tj-mazu-card" href="/toy/{esc(t["sid"])}"><span class="tj-work">{pic(t)}{photo(t)}</span>'
                    f'<span class="nm">{esc(t["toy"])}</span></a>' for t in ts)
    head = f"<h2>{esc(MAZU)}</h2>" if MAZU else ""
    # 黒の表紙にだけあった 1 行（額の絵の下の「江都二色　安永二年　うしなわれた玩具」。本人の決定 11-06「黒案にだけある要素は白案に入れて」）は、
    # 前は白の扉の額の下に出していた。扉は外したので、同じ額の敷き方の 2 枚の下に置く（『江都二色』の話の 1 行でもある）
    return f'<section class="tj-mazu" id="mazu">{head}<div class="row">{cards}</div><p class="meta">{esc(DOOR_LINE)}</p></section>'


def _erabu(sids):
    """ほかの玩具の原画の敷き詰め（えらぶ の #508 の札と並び・ジャンルの棚）。控えめに小さく並べる。見出しは えらぶ の頭と同じ採られた字。"""
    from . import genre
    from . import toys as toys_page

    shelves = "".join(f'<h3>{esc(big)}</h3><ul class="tj-narabi">{"".join(toys_page.card(s) for _, ss in mids for s in ss)}</ul>'
                      for big, mids in genre.groups(sids))
    # 並びの小さい写しは、まずはここから の 2 枚が届いてから読む（data-src を src に替える台本 ERABU_JS）。遅い回線（下り 1.6Mbps・往復 150ms・
    # トンネル越し）で、2 枚と並びの 20 枚ほどを一度に読むと、2 枚が届くのに 5.6 秒かかった（11-07 に Chromium で測った。本人の答え 11-07 の (a)）。
    # 台本が動かない機器では、並びは名前の札だけになる（並びの絵は 2 枚より後でよい物なので、そこは止めない）
    shelves = shelves.replace(' src="/picture/', ' data-src="/picture/')
    n = len(sids) + len([s for s in sources() if hypotheses.stage(s) == "必須"])
    return (f'<section class="tj-erabu" id="all-toys"><h2>{n} のおもちゃから、1 つ選ぶ</h2>{shelves}'
            '<p class="links"><a href="/toys?paper=1">紙 1 枚で作れるおもちゃだけを見る</a></p></section>')


def tenji(photos=True):
    """白の入口（えらぶ）。photos=False は合言葉なしで開いた場: 記録の写真を置かない（玩具の頁と同じ前の決まり。test_public_open）。"""
    ts = toys()
    body = switch("tenji")
    # 題の間: 題と副題と表紙の 2 行だけ（えらぶ の釦は外した。押させずに、すぐ下から選べる）。画面いっぱいの高さにはせず、
    # 幅 390 の最初の画面に 2 つの大きな札の頭が入るようにする（「最初から選べる形」）
    body += ('<section class="tj-hall" id="hall"><p class="en">Lost toys of Edo · 1773</p><h1>うつし</h1>'
             '<p class="sub">江都二色より<br>うしなわれた玩具の動きを<br>紙で実験して確かめる</p>' + about_link() + '</section>')
    main = [t for t in ts if hypotheses.stage(t["sid"]) == "必須"]
    body += _mazu(main, photos)
    body += _erabu([s for s in sources() if hypotheses.stage(s) != "必須"])
    body += '<p class="tj-note">図は国立国会図書館デジタルコレクションの頁（米山堂・1931 年の複製）。新しい絵は作っていない。</p>'
    return page("うつし", body + ONLY + ERABU_JS, TENJI + ERABU + skin.entrance_style("tenji"), "tenji")


# 並びの小さい写しを読み始める台本。まずはここから の 2 枚が届くか（失敗も含む）、2.5 秒たった方の早い時に、並びの data-src を src にする。
# 見えた時に起こす仕掛けは使わない（入口の決まり。research/19）。
ERABU_JS = """<script>(()=>{let go=false;const run=()=>{if(go)return;go=true;document.querySelectorAll('.tj-narabi img[data-src]').forEach(i=>{i.src=i.dataset.src;i.removeAttribute('data-src')})};
const big=[...document.querySelectorAll('.tj-mazu-card .pic img')];let left=big.filter(i=>!i.complete).length;if(!left){run();return}
big.forEach(i=>{if(!i.complete){const f=()=>{if(--left<=0)run()};i.addEventListener('load',f,{once:true});i.addEventListener('error',f,{once:true})}});setTimeout(run,2500)})();</script>"""


# 入口の えらぶ の形（白の展示）。札の中身は toys.card（#508 の小さい写し・縦横つき）なので、その札が要る CSS をここに置く（入口は skin.BASE を読まない）。
# 「控えめに」: ほかの玩具は 1 列 72px 以上・9 列まで（えらぶ の頁の 96px・7 列より小さく）。2 つの大きな札は横に並べ、幅 390 で 1 枚 160px ほど。
ERABU = """
/* 題の間は横書きで短く（前の B の間の縦書きは、幅 390 で 2 つの札が 1 画面目の外に出た。11-07 に測った: 札の頭が 855px）。
   字は前の題の間の字のまま（英字・題・副題・表紙の 2 行） */
#hall.tj-hall{min-height:auto;display:block;text-align:center;padding:5vh 5vw 3vh}
#hall.tj-hall .en,#hall.tj-hall h1,#hall.tj-hall .sub{writing-mode:horizontal-tb;margin:0 auto}
#hall.tj-hall .en{margin-bottom:2vh}
#hall.tj-hall h1{font-size:clamp(30px,4.4vw,56px);letter-spacing:.5em;margin-left:.5em}
#hall.tj-hall .sub{margin-top:2.4vh;line-height:2;letter-spacing:.2em}
#hall.tj-hall .about-go{margin:2.4vh 0 0;font-size:13px}
.tj-mazu{padding:2vh 5vw 8vh;max-width:980px;margin:0 auto}
.tj-mazu h2{font-size:clamp(18px,2vw,24px);font-weight:400;letter-spacing:.3em;text-align:center;margin:0 0 3vh}
.tj-mazu .meta{text-align:center;font-size:13px;letter-spacing:.3em;color:#5d554a;margin:4vh 0 0}
.tj-mazu .row{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:clamp(16px,4vw,56px)}
body .tj-mazu-card{display:block;color:inherit;text-decoration:none;border:0}
.tj-mazu-card .tj-work{display:block;width:100%;margin:0;position:relative}
.tj-made{position:absolute;right:-6px;bottom:-10px;width:42%;line-height:0;background:#fffefc;padding:4px;box-shadow:0 10px 18px -10px rgba(70,55,35,.5);border:1px solid #d8cdb6}
.tj-made img{display:block;width:100%;height:auto}
.tj-mazu-card .pic{display:block;aspect-ratio:1600/2656;border:1px solid #d8cdb6;box-shadow:0 18px 30px -22px rgba(70,55,35,.5);overflow:hidden;background:#d9d2c3}
.tj-mazu-card .pic img{display:block;width:100%;height:100%;object-fit:cover;transform:scale(1.12)}
.tj-mazu-card .nm{display:block;text-align:center;font-size:clamp(14px,1.6vw,18px);letter-spacing:.3em;margin-top:14px;min-height:44px;line-height:44px}
.tj-erabu{padding:8vh 24px;max-width:1180px;margin:0 auto;border-top:1px solid #ebe8e2}
.tj-erabu h2{font-size:clamp(15px,1.6vw,19px);font-weight:400;letter-spacing:.2em;margin:0 0 4vh}
.tj-erabu h3{font-size:14px;font-weight:400;letter-spacing:.4em;color:#5d554a;margin:5vh 0 14px}
.tj-narabi{list-style:none;padding:0;margin:0;columns:9 72px;column-gap:12px}
.tj-narabi li{break-inside:avoid;margin:0 0 12px}
body .tj-narabi a{display:block;color:inherit;text-decoration:none;border:0}
.tj-narabi .pic{display:block;width:100%;height:auto;border:1px solid #d8cdb6;background:#f3f1ec;box-sizing:border-box}
.tj-narabi .nopic{aspect-ratio:3/4}
.tj-narabi .nm{display:block;font-size:12px;letter-spacing:.06em;margin-top:5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tj-narabi .ways{display:none}
.tj-erabu .links{margin-top:6vh;font-size:13px}
"""


PAGES = {"tenji": tenji, "zine": zine}
