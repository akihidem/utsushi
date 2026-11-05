"""骨と皮（本人の指示 2026-11-05: 小さな直しの積み重ねを止め、A′ 白の展示と C 黒のジンをそれぞれ一気通貫に）。要件は docs/process/site-requirements.md。

判断の芯:
- 順路は 1 つ、皮は 2 つ。皮は CSS の変数の表（SKINS）だけで、頁の骨（shell・nav）と部品の CSS（BASE）は共通。皮ごとに頁を書かない。
  なぜ: 今まで頁ごとに見た目の塊を持ち（入口 3 系統・玩具の頁・手帖・図鑑）、入口から玩具の頁へ入った所で世界が変わっていた（要件の 0）。
- 皮はサイトごとに 1 つ（本人の決定 11-05 朝「日本画かジンで行く。それぞれのデザインのサイトを 2 つ作る」）。サーバを立てる時に
  --look で決め（play_server.serve の look）、頁の中に切り替えは置かない。cookie も ?look= も使わない。DEFAULT は --look を省いた時の皮。
  大判（A）は外した（同じ決定「他のデザインは要らない」）。
- 動きは入口の扇の札だけ。内側の頁は静か（research/19・24 の線のまま）。見えた時に起こす仕掛け（IntersectionObserver）は置かない。
- 図は国立国会図書館の頁の写しだけ。新しい絵は作らない。小さな字も 4.5:1 を割らない（research/24）。
- 成績・順位に見える物（点・票・数の回る表示・祝いの演出）は部品に入れない（J-025、philosophy.md）。
"""
import html

DEFAULT = "tenji"

# 皮の表。値は looks.py の A′（TENJI）と C（ZINE）から写した（色相を変えない）。mute は白地・黒地のどちらでも 4.5:1 以上。
SKINS = {
    "tenji": {"name": "白の展示", "bg": "#fcfcfa", "fg": "#2b2722", "mute": "#6f665a", "accent": "#6b4f2a", "rule": "#ebe8e2",
              "paper": "#fffefc", "frame": "#d8cdb6", "shadow": "rgba(70,55,35,.35)", "selbg": "#e6e1d6", "selfg": "#1f1b17",
              "field": "#fffefc", "onaccent": "#fcfcfa", "soft": "#f3f1ec"},
    "zine": {"name": "黒のジン", "bg": "#0b0a09", "fg": "#e9e1cf", "mute": "#a0957f", "accent": "#c9a96a", "rule": "#2a251e",
             "paper": "#141210", "frame": "#6e5a35", "shadow": "rgba(0,0,0,.7)", "selbg": "rgba(201,169,106,.35)", "selfg": "#f5eedf",
             "field": "#171411", "onaccent": "#0b0a09", "soft": "#15120f"},
}

# 頭の帯の道。順路の順（序 → おもちゃ → 上げた物 → 図鑑）。入口は「うつし」。
NAV = (("/", "うつし"), ("/about", "序"), ("/toys", "おもちゃ"), ("/gallery", "上げた物と職人の言葉"), ("/zukan", "図鑑"))


# その場限りの無作為の印（U-45 の「人の数え方」、J-027）。タブごとの sessionStorage に英数字 10 桁を 1 つ持ち、頁の POST のフォームに添える。
# cookie にしない・名前にしない・日をまたいで同じ人と分からない。持てない画面では添えない（頁は JS なしでも動く。人の数が「—」になるだけ）。
WHO_SCRIPT = ("<script>(()=>{try{let w=sessionStorage.getItem('utsushi-who')||'';if(!/^[a-z0-9]{10}$/.test(w)){"
              "const a=crypto.getRandomValues(new Uint8Array(10));w=[...a].map(x=>'abcdefghijklmnopqrstuvwxyz0123456789'[x%36]).join('');sessionStorage.setItem('utsushi-who',w)}"
              "document.querySelectorAll('form[method=post]').forEach(f=>{if(f.elements.who)return;const i=document.createElement('input');i.type='hidden';i.name='who';i.value=w;f.appendChild(i)})}catch(e){}})()</script>")


def esc(s):
    return html.escape(str(s if s is not None else ""), quote=True)


BASE = """
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--fg);font-family:"Noto Serif CJK JP","Noto Serif JP","Hiragino Mincho ProN","Yu Mincho",serif;
 font-feature-settings:"palt" 1;line-height:1.8;font-size:16px}
::selection{background:var(--selbg);color:var(--selfg)}
a{color:var(--accent);text-decoration:none;border-bottom:1px solid color-mix(in srgb,var(--accent) 40%,transparent)}
a:hover{border-bottom-color:var(--accent)}
:focus-visible{outline:2px solid var(--accent);outline-offset:3px}
h1,h2,h3{font-weight:400;margin:0}
h1{font-size:clamp(28px,3.4vw,44px);letter-spacing:.3em}
h2{font-size:clamp(20px,2.2vw,28px);letter-spacing:.2em;margin:0 0 .6em}
h3{font-size:17px;letter-spacing:.12em}
img,video{max-width:100%}
main{max-width:1180px;margin:0 auto;padding:0 5vw 96px}
.wrap{max-width:1180px;margin:0 auto;padding:0 5vw}
.meta{font-size:12px;color:var(--mute);letter-spacing:.08em;line-height:1.9}
.lb{display:inline-block;font-size:11px;letter-spacing:.2em;color:var(--mute);border:1px solid var(--frame);padding:0 8px;margin-right:8px;vertical-align:middle}
.lead{font-size:15px;line-height:2.1;letter-spacing:.06em;max-width:40em}
.nav{display:flex;gap:18px;flex-wrap:wrap;align-items:baseline;padding:16px 5vw;font-size:12px;letter-spacing:.2em;color:var(--mute);border-bottom:1px solid var(--rule)}
.nav a{color:var(--accent);border:0}.nav b{font-weight:400;color:var(--fg)}.nav .brand{font-size:15px;letter-spacing:.45em;color:var(--fg)}

.sec{padding:56px 0;border-top:1px solid var(--rule)}
.sec:first-child{border-top:0}
.hero{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.2fr);gap:5vw;align-items:start;padding:48px 0 56px}
.frame{margin:0;background:var(--paper);border:1px solid var(--frame);padding:3%;box-shadow:0 1px 0 var(--rule),0 40px 60px -30px var(--shadow)}
.frame img{width:100%;display:block}
.frame .pic{width:100%;aspect-ratio:1600/2656;background-position:85% 50%;background-size:112% 112%;background-repeat:no-repeat;background-color:var(--soft)}
.frame figcaption{font-size:11px;color:var(--mute);letter-spacing:.15em;margin-top:10px}
.songs{writing-mode:vertical-rl;height:min(44vh,360px);margin:0 0 14px auto;font-size:clamp(16px,1.6vw,21px);line-height:2.3;letter-spacing:.14em}
.songs p{margin:0 .3em}
.label{font-size:12px;line-height:2;letter-spacing:.06em;color:var(--mute);border-left:1px solid var(--frame);padding-left:14px;max-width:24em;margin:18px 0}
.label b{display:block;font-weight:400;font-size:17px;letter-spacing:.22em;color:var(--fg)}
.links{display:flex;gap:18px;flex-wrap:wrap;font-size:13px;letter-spacing:.12em}
label{display:block;margin-top:14px;font-size:14px;letter-spacing:.06em}
input[type=text],textarea,select{display:block;width:100%;margin-top:6px;padding:10px 12px;font:inherit;font-size:16px;color:var(--fg);background:var(--field);
 border:1px solid var(--frame);border-radius:0}
textarea{min-height:110px}
button,.btn{display:inline-block;margin-top:16px;padding:12px 26px;font:inherit;font-size:14px;letter-spacing:.2em;color:var(--onaccent);background:var(--accent);
 border:0;border-radius:0;cursor:pointer;text-decoration:none}
.btn.quiet,button.quiet{background:transparent;color:var(--accent);border:1px solid var(--accent)}
form.inline{display:inline}
.notice,#msg{border-left:2px solid var(--accent);padding:4px 14px;margin:14px 0;font-size:14px;letter-spacing:.04em}
article.card,.card{background:var(--paper);border:1px solid var(--frame);padding:20px 22px;margin:16px 0;box-shadow:0 18px 30px -24px var(--shadow)}
.plates{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:20px}
.plate{background:var(--paper);border:1px solid var(--frame);padding:18px 20px;box-shadow:0 18px 30px -24px var(--shadow);display:flex;flex-direction:column}
.plate .letter{font-size:44px;line-height:1;color:var(--accent);letter-spacing:0}
.plate h3{margin:8px 0}.plate p{font-size:14px;line-height:1.9;margin:6px 0}.plate ul{padding-left:1.2em;font-size:13px;color:var(--mute);margin:6px 0}
.plate .thumb{display:block;margin:12px 0 4px;border:1px solid var(--frame);background:#fff}
.plate .thumb img{display:block;width:100%}
/* 札の足。頁の足 .foot と同じ名前だと、頁の足の余白と字の大きさが掛かり釦が 2 行に折れた（#124） */
.plate .acts{margin-top:auto}.plate .acts form button{padding:12px 14px;white-space:nowrap}
.win{display:grid;grid-template-columns:minmax(0,1.1fr) minmax(0,1fr);gap:4vw;align-items:start}
.tabs{display:flex;gap:10px;flex-wrap:wrap;font-size:13px;letter-spacing:.12em;margin:0 0 12px}
.tabs a,.tabs span{border:1px solid var(--frame);padding:4px 12px}
.tabs a[aria-current=true]{background:var(--accent);color:var(--onaccent);border-color:var(--accent)}
.tabs span{color:var(--mute);border-style:dashed}
.win .sheet{margin:0;background:#fff;border:1px solid var(--frame);box-shadow:0 30px 50px -30px var(--shadow)}
.win .sheet a{display:block;border:0}.win .sheet img{display:block;width:100%}
.win .side{font-size:14px;line-height:2}
.win .side .v{display:flex;gap:10px;flex-wrap:wrap;font-size:13px;letter-spacing:.12em;margin:8px 0}
.win .side .v a,.win .side .v b{border:1px solid var(--frame);padding:2px 10px;font-weight:400}
.win .side .v b{background:var(--accent);color:var(--onaccent);border-color:var(--accent)}
.zoom{display:none;position:fixed;inset:0;z-index:50;background:var(--bg);overflow:auto;padding:4vh 4vw}
.zoom:target{display:block}
.zoom img{display:block;width:180%;max-width:none;margin:0 auto;background:#fff;border:1px solid var(--frame)}
.zoom .close{position:fixed;top:12px;right:16px;font-size:13px;letter-spacing:.2em;background:var(--accent);color:var(--onaccent);padding:8px 14px;border:0}
.tiles{display:flex;gap:12px;flex-wrap:wrap;margin-top:8px}
.tile{display:grid;justify-items:center;gap:6px;border:1px solid var(--frame);background:var(--paper);color:var(--fg);font-size:14px;padding:10px 16px;cursor:pointer;min-width:84px;position:relative;margin:0}
.tile:has(input:checked){border-color:var(--accent);box-shadow:0 0 0 1px var(--accent) inset}
.tile input{position:absolute;opacity:0;pointer-events:none}
.tile svg{width:40px;height:40px;stroke:var(--fg);fill:none;stroke-width:3;stroke-linecap:round;stroke-linejoin:round}
.item{border-top:1px solid var(--rule);padding:14px 0;display:grid;gap:6px}
.item img,.item video{height:120px;max-width:100%;border:1px solid var(--frame)}
.row{display:flex;gap:12px;flex-wrap:wrap;align-items:center}
.shots{display:flex;gap:10px;flex-wrap:wrap;margin:8px 0}.shots img,.shots video{height:150px;max-width:100%;border:1px solid var(--frame);background:#fff}
.strip{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}.strip a{border:0}.strip img,.strip video{height:72px;border:1px solid var(--frame);background:#fff}
.toys{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:18px 14px}
.toys a{display:block;border:0;color:var(--fg)}
.toys .pic{aspect-ratio:3/4;background:var(--soft) center/300% no-repeat;border:1px solid var(--frame);box-shadow:0 14px 22px -18px var(--shadow)}
.toys .nm{font-size:13px;letter-spacing:.08em;line-height:1.6;margin-top:8px}
.toys .big{grid-column:span 2;grid-row:span 2}.toys .big .pic{aspect-ratio:1600/2656;background-size:112% 112%;background-position:85% 50%}
@media (max-width:680px){.toys .big{grid-column:auto;grid-row:auto}}
.sample{display:inline-block;background:var(--accent);color:var(--onaccent);font-size:11px;letter-spacing:.2em;padding:1px 8px;margin-right:6px}
.is-sample{border-top:1px dashed var(--frame)}.is-sample svg{height:110px;width:auto;border:1px dashed var(--frame)}.samples{margin-top:18px}
.foot{padding:48px 5vw 40px;font-size:11px;color:var(--mute);letter-spacing:.1em;text-align:center;border-top:1px solid var(--rule)}
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
@media (max-width:820px){.hero,.win{grid-template-columns:1fr}.songs{writing-mode:horizontal-tb;height:auto;margin:0 0 14px}.nav{gap:12px;padding:12px 16px}
 main,.wrap{padding-left:16px;padding-right:16px}.toys{grid-template-columns:repeat(auto-fill,minmax(120px,1fr))}.zoom img{width:220%}}
@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
"""


def nav(skin, current="", path="/"):
    """頭の帯。順路の道だけ。皮の切り替えは置かない（皮ごとに 1 サイト。skin と path は呼び手の形を保つために残す）。"""
    items = "".join(f'<b>{esc(n)}</b>' if p == current else f'<a href="{p}">{esc(n)}</a>' for p, n in NAV)
    return f'<nav class="nav"><a class="brand" href="/">うつし</a>{items}</nav>'


def shell(title, body, skin=DEFAULT, current="", path="/", extra_style="", body_class="", head="", foot=""):
    """頁の骨。皮の変数を :root に置き、頭の帯と足を付ける。中身（body）は皮を知らずに書けるようにする。"""
    s = SKINS.get(skin, SKINS[DEFAULT])
    root = ";".join(f"--{k}:{v}" for k, v in s.items() if k != "name")
    foot = foot or '<p class="foot">図は国立国会図書館デジタルコレクションの頁（米山堂・1931 年の複製、パブリック・ドメイン）。紙で動いても、昔の作り方の証明にはなりません。</p>'
    return (f'<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{esc(title)}</title><style>:root{{{root}}}{BASE}{extra_style}</style>{head}'
            f'<body class="skin-{esc(skin)}{" " + esc(body_class) if body_class else ""}">{nav(skin, current, path)}<main>{body}</main>{foot}{WHO_SCRIPT}</body></html>')


def frame(sid, caption="", pos=None):
    """額に入れた図。写しが無い時は地の色だけ（図の場所には国立国会図書館への道を別に置く）。looks._bg と同じ敷き方。"""
    from omochae.hypotheses import ROOT

    if (ROOT / "out/sources" / f"{sid}.jpg").exists():
        from .looks import framed_pos

        style = f"background-image:url(/picture/{esc(sid)});background-position:{pos or framed_pos(sid)}"
    else:
        style = ""
    cap = f"<figcaption>{esc(caption)}</figcaption>" if caption else ""
    return f'<figure class="frame"><div class="pic" style="{style}" role="img" aria-label="図"></div>{cap}</figure>'


def artwork_label(toy, src):
    """美術館の作品の札。中身は出典の記録（NDL の書誌）の値だけで、作る側の言葉を足さない（looks._label と同じ線）。"""
    who = esc(src.get("creator_as_cataloged", "").replace("||", "・"))
    when = esc((src.get("original_publication") or {}).get("value", ""))
    rights = "パブリック・ドメイン（PDM）" if src.get("rights") == "PDM" else esc(src.get("rights", ""))
    return f'<p class="label"><b>{esc(toy)}</b>『{esc(src.get("title", ""))}』より<br>{who}<br>{when}<br>{esc(src.get("holding", ""))}<br>{rights}</p>'


def notice(title, reason, skin=DEFAULT, links=(("/", "入口へ"), ("/toys", "おもちゃの一覧へ")), bare=False):
    """断りの頁（404・403・500）。何が起きたかと戻り方を、皮の地で 1 つの形で出す。bare は帯も足も出さない形で、合言葉の門のように中身を見せない所に使う（#136）。"""
    back = "".join(f'<a href="{esc(p)}">{esc(n)}</a>' for p, n in links)
    back = f'<p class="notice-back">{back}</p>' if back else ""
    page = shell(title, f'<section class="sec notice"><h1>{esc(title)}</h1><p>{esc(reason)}</p>{back}</section>', skin,
                 extra_style=".notice-back a{margin-right:1.2em}", foot=" " if bare else "")
    # 骨は shell のまま使い、帯だけ抜く。foot は空だと既定の足が付くので、bare では空白を渡す
    return page.replace(nav(skin), "", 1) if bare else page
