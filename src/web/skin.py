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

# 頭の帯の道。順路の順（序 → おもちゃ → 作った物 → 図鑑）。入口は「うつし」。
# 帯の項目。先頭の「うつし」（入口への道）は nav() が brand として出すので、ここには置かない
NAV = (("/about", "序"), ("/toys", "おもちゃ"), ("/gallery", "作った物と職人の言葉"), ("/zukan", "図鑑"), ("/en", "English"))
# 英語の頁の帯（J-030 の段 1）。全部の頁を訳さないので、道は入口と日本語の頁へだけ。
NAV_EN = (("/en", "utsushi"), ("/en#toys", "Toys"), ("/", "日本語"))


# その場限りの無作為の印（U-45 の「人の数え方」、J-027）。タブごとの sessionStorage に英数字 10 桁を 1 つ持ち、頁の POST のフォームに添える。
# cookie にしない・名前にしない・日をまたいで同じ人と分からない。持てない画面では添えない（頁は JS なしでも動く。人の数が「—」になるだけ）。
# 記録を残したら、印を作り直す（1 回の作りに 1 つの印。同じタブを次の人が使っても、前の人の字が混ざらないように。Issue #279 の続き）。
# 頁を移る時は戻る先の合図（fresh）で、手帖のように頁を移らない時は utsushiNewWho で。合図は住所から消す（読み直しで、また作り直さないように）。
WHO_SCRIPT = ("<script>(()=>{try{const make=()=>{const a=crypto.getRandomValues(new Uint8Array(10)),n=[...a].map(x=>'abcdefghijklmnopqrstuvwxyz0123456789'[x%36]).join('');sessionStorage.setItem('utsushi-who',n);return n};"
              "let w=sessionStorage.getItem('utsushi-who')||'';const u=new URL(location.href);"
              "if(u.searchParams.has('fresh')){w=make();u.searchParams.delete('fresh');history.replaceState(null,'',u)}else if(!/^[a-z0-9]{10}$/.test(w))w=make();"
              "window.utsushiNewWho=()=>{w=make();document.querySelectorAll('input[name=who]').forEach(i=>{i.value=w})};"
              "document.querySelectorAll('form[method=post]').forEach(f=>{if(f.elements.who)return;const i=document.createElement('input');i.type='hidden';i.name='who';i.value=w;f.appendChild(i)})}catch(e){}})()</script>")

# 紙を作る釦（#301）。作るのに数秒かかり、その間に釦が変わらないと、もう一度押す人が出て送信が 2 回出る。
# 押した時に輪を回し、頁の紙を作る釦を全部押せなくする（別の札を押しても、前の送信の返事が捨てられるだけなので）。輪は見えない人に届かないので aria-busy も付ける。
# submit で見るので、欄が足りずに送られない時は変わらない。JS が無ければ普通に送るだけで、形も変わらない。
# 押した釦の字は本人の決定（11-05）。頁の lang で選ぶので、文はここの 1 か所だけ。元の字を覚えて、戻す時に戻す。
# 押せないまま残らないように戻す: 戻る操作で頁がそのまま戻った時（pageshow）と、網が止まって返事が来ない時（時間切れ）。
# 時間切れの 30 秒は、手元で一番長い案の 4.1 秒に、教室の網の遅れを見込んだ値。戻せば押し直せる。釦ごとに長くする時は data-busy-for（秒）。
BUSY_SCRIPT = ("<script>(()=>{let t;const word=document.documentElement.lang==='en'?'Making…':'作っています…',all=()=>document.querySelectorAll('button[data-busy]');"
               "const back=()=>{clearTimeout(t);all().forEach(b=>{if(b.dataset.was){b.textContent=b.dataset.was;delete b.dataset.was}b.dataset.busy='';b.removeAttribute('aria-busy');b.disabled=false})};"
               "document.addEventListener('submit',e=>{const b=e.target.querySelector('button[data-busy]');if(!b||e.defaultPrevented)return;"
               "all().forEach(x=>{x.disabled=true});b.dataset.was=b.textContent;b.textContent=word;b.dataset.busy='on';b.setAttribute('aria-busy','true');t=setTimeout(back,(+b.dataset.busyFor||30)*1000)});"
               "addEventListener('pageshow',back)})()</script>")


def esc(s):
    return html.escape(str(s if s is not None else ""), quote=True)


# 頭の帯の CSS。入口の頁も同じ物を使う（骨を 1 つにする、要件 2）。今いる所は色だけにしない（字の色と下の罫）
# スマホの幅は字間を外し隙間を詰める。項目の字を長くすると、1 つだけ次の段に落ちるため（#303、tests/test_nav_fit.py）
NAV_STYLE = """.nav{display:flex;gap:18px;flex-wrap:wrap;align-items:baseline;padding:16px 5vw;font-size:12px;letter-spacing:.2em;color:var(--mute);border-bottom:1px solid var(--rule)}
/* 頭の帯と足は骨の物なので、頁の本文の書体（手帖のゴシックなど）を受け継がない（#126） */
.nav,.foot{font-family:"Noto Serif CJK JP","Noto Serif JP","Hiragino Mincho ProN","Yu Mincho",serif}
.nav a{color:var(--accent);border:0}.nav .brand{font-size:15px;letter-spacing:.45em;color:var(--fg)}
.nav a[aria-current=page]{color:var(--fg);border-bottom:1px solid var(--fg)}
@media (max-width:480px){.nav{gap:8px;letter-spacing:0}.nav .brand{flex:none;white-space:nowrap;margin-right:100%}}
"""
# 押す所の床（W-03、#137）。現場は iPhone と iPad なので、指で押し間違えない高さを取る。机の幅の静かな見た目は変えない。
# スマホの幅だけにすると iPad の幅で小さいまま残るので、触る機器（pointer:coarse）と 1100px までに効かせる。
# 文の中のリンクは入れない。行が崩れるので。字の大きさの床（12px）は、幅に関わらず CSS の指定そのもので守る。
# summary は inline-flex にするとブラウザの開け閉めの印が消え、ただの字に見えて畳んだ欄に気づけないので、印を字で足す（#300）。
# ▶ は iPhone で絵文字になる事があるので、絵文字にならない ▸ と ▾ にする。
# button に display を付けると、ブラウザ既定の [hidden]{display:none} に勝ち、隠した釦が出たままになる（#321）。頁ごとに止めると見落としが残るので、
# 原因のここで止める。.fan-ctl button は [hidden] より強いので !important が要る。
# 字の欄と選ぶ欄を持つ label は block に戻す（#290）。inline-flex のままだと名前の横に細く並ぶ。BASE が全幅にする組と同じ物だけに当て、札（radio）・写真の札（file）・つまみ（range）には当てない。
# label:not(.sr) と頭をそろえるのは、label:has(>textarea) だと詳細度で負けて効かないため。
# 高さを上げた字のリンクの下線は text-decoration で字に付ける。border-bottom のままだと箱の底に付き、字から 10〜16px 離れて、図鑑の一覧では隣の行の線に見える。
# 当てるのは字の線を持つリンクだけ。.nav の今いる頁の印・.tabs の枠・.grid の絵の札（図鑑の .more は字だけの一覧）・.toys の中・.btn の釦・作りながら見る頁の頭は線の形が別なので当てない。
# body .links a は図鑑の .zukan a に勝つ詳細度にするため（図鑑の頁では床より後に .zukan a が来る）。
# :where(.top) a は手帖とギャラリーの頭の字のリンク。詳細度を下げて、線なしの作りながら見る頁の .top a に勝たせる。ここは全部の頁に載るので .techo の名前を書かない（手帖の皮を外へ漏らさない決まり、#126）。
# 一括の text-decoration は Safari が太さと色を読まないので、1 つずつ書く。色は頁ごとの変数に頼らず、リンクの字の色から作る（開いた頁の見た目の組は --accent を持たない）。
TAP_FLOOR = """@media (max-width:1100px),(pointer:coarse){
.nav{font-size:14px;row-gap:0}
.nav a,.links a,.notice-back a,.tabs a,.tabs span,.top a,.tj-exit a,.fan-ctl button,summary,.grid li>a,h2>a,li>small>a,li>.meta>a,.cap>a:only-child,.meta>a:only-child,.item p>a:only-child,.zn-toy p>a:only-child,.jump a,td>a,.meta li>a,button,select,label:not(.sr){display:inline-flex;align-items:center;min-height:44px;box-sizing:border-box}
label:not(.sr):has(>input[type=text]),label:not(.sr):has(>input[type=number]),label:not(.sr):has(>textarea),label:not(.sr):has(>select),label:not(.sr)>select{display:block}
input[type=range]{height:44px}
summary{list-style:none}
summary::-webkit-details-marker{display:none}
summary::before{content:"▸";margin-right:.5em}
details[open]>summary::before{content:"▾"}
[hidden]{display:none!important}
.meta>a:only-child:not(.toys a),.meta li>a,.more .grid li>a,body .links a:not(.btn),.jump a,td>a,.cap>a:only-child,.item p>a:only-child,.zn-toy p>a:only-child,.notice-back a,:where(.top) a,body .tj-exit a{border-bottom:0;text-decoration-line:underline;text-decoration-thickness:1px;text-decoration-color:color-mix(in srgb,currentColor var(--line,40%),transparent);text-underline-offset:3px}
a:hover{--line:100%}
}
"""
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
.premise{font-size:14px;line-height:1.9;letter-spacing:.06em;margin:10px 0;padding:8px 12px;border-left:3px solid var(--frame)}
.lb{display:inline-block;font-size:12px;letter-spacing:.2em;color:var(--mute);border:1px solid var(--frame);padding:0 8px;margin-right:8px;vertical-align:middle}
.lead{font-size:15px;line-height:2.1;letter-spacing:.06em;max-width:40em}

.sec{padding:56px 0;border-top:1px solid var(--rule)}
.sec:first-child{border-top:0}
.hero{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.2fr);gap:5vw;align-items:start;padding:48px 0 56px}
.frame{margin:0;background:var(--paper);border:1px solid var(--frame);padding:3%;box-shadow:0 1px 0 var(--rule),0 40px 60px -30px var(--shadow)}
.frame img{width:100%;display:block}
.frame .pic{width:100%;aspect-ratio:1600/2656;background-position:85% 50%;background-size:112% 112%;background-repeat:no-repeat;background-color:var(--soft)}
.frame figcaption{font-size:12px;color:var(--mute);letter-spacing:.15em;margin-top:10px}
.songs{writing-mode:vertical-rl;height:min(44vh,360px);margin:0 0 14px auto;font-size:clamp(16px,1.6vw,21px);line-height:2.3;letter-spacing:.14em}
.songs p{margin:0 .3em}
.hero .songs{float:right;margin:0 0 14px 24px}
.label{font-size:12px;line-height:2;letter-spacing:.06em;color:var(--mute);border-left:1px solid var(--frame);padding-left:14px;max-width:24em;margin:18px 0}
.label b{display:block;font-weight:400;font-size:17px;letter-spacing:.22em;color:var(--fg)}
.links{display:flex;gap:18px;flex-wrap:wrap;font-size:13px;letter-spacing:.12em}
label{display:block;margin-top:14px;font-size:14px;letter-spacing:.06em}
input[type=text],input[type=number],textarea,select{display:block;width:100%;margin-top:6px;padding:10px 12px;font:inherit;font-size:16px;color:var(--fg);background:var(--field);
 border:1px solid var(--frame);border-radius:0}
textarea{min-height:110px}
button,.btn{display:inline-block;margin-top:16px;padding:12px 26px;font:inherit;font-size:14px;letter-spacing:.2em;color:var(--onaccent);background:var(--accent);
 border:0;border-radius:0;cursor:pointer;text-decoration:none}
.btn.quiet,button.quiet{background:transparent;color:var(--accent);border:1px solid var(--accent)}
button[data-busy]:disabled{opacity:.7;cursor:progress}
button[data-busy=on]:disabled{opacity:1}
button[data-busy=on]::after{content:"";display:inline-block;width:.8em;height:.8em;margin-left:.5em;vertical-align:-.1em;border:2px solid currentColor;border-right-color:transparent;border-radius:50%;animation:busy-turn .9s linear infinite}
@keyframes busy-turn{to{transform:rotate(360deg)}}
@media (prefers-reduced-motion:reduce){button[data-busy=on]::after{animation:none}}
form.inline{display:inline}
.notice,#msg{border-left:2px solid var(--accent);padding:4px 14px;margin:14px 0;font-size:14px;letter-spacing:.04em}
.card .step{border-top:1px solid var(--frame);margin-top:14px;padding-top:12px}
article.card,.card{background:var(--paper);border:1px solid var(--frame);padding:20px 22px;margin:16px 0;box-shadow:0 18px 30px -24px var(--shadow)}
.plates{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:20px}
.plate{background:var(--paper);border:1px solid var(--frame);padding:18px 20px;box-shadow:0 18px 30px -24px var(--shadow);display:flex;flex-direction:column}
.plate .letter{font-size:44px;line-height:1;color:var(--accent);letter-spacing:0}
.plate h3{margin:8px 0}.plate p{font-size:14px;line-height:1.9;margin:6px 0}.plate ul{padding-left:1.2em;font-size:13px;color:var(--mute);margin:6px 0}
.plate .thumb{display:block;margin:12px 0 4px;border:1px solid var(--frame);background:#fff}
.plate .thumb img{display:block;width:100%}
.plates>.plate:only-child{grid-column:1/-1;max-width:640px}.plates>.plate:only-child .thumb{max-width:280px}
/* 札の足。頁の足 .foot と同じ名前だと、頁の足の余白と字の大きさが掛かり釦が 2 行に折れた（#124） */
.plate .acts{margin-top:auto}.plate .acts form button{padding:12px 14px;white-space:nowrap}
.win{display:grid;grid-template-columns:minmax(0,1.1fr) minmax(0,1fr);gap:4vw;align-items:start}
.tabs{display:flex;gap:10px;flex-wrap:wrap;font-size:13px;letter-spacing:.12em;margin:0 0 12px}
.tabs a,.tabs span{border:1px solid var(--frame);padding:4px 12px}
.tabs a[aria-current=true]{background:var(--accent);color:var(--onaccent);border-color:var(--accent)}
.tabs span{color:var(--mute);border-style:dashed}
.tabs button{margin:0;padding:4px 12px;font-size:inherit;letter-spacing:inherit;color:var(--accent);background:transparent;border:1px dashed var(--frame);cursor:pointer}
.win .sheet{margin:0;background:#fff;border:1px solid var(--frame);box-shadow:0 30px 50px -30px var(--shadow)}
.win .sheet a{display:block;border:0}.win .sheet img{display:block;width:100%}
.win .side{font-size:14px;line-height:2}
/* 印刷で止まった時の案内は、プリンタの前で小学生も読むので、本文と同じ字の大きさにする（#297） */
.win .side .print-help{font-size:16px;line-height:1.8}
.win .side .v{display:flex;gap:10px;flex-wrap:wrap;font-size:13px;letter-spacing:.12em;margin:8px 0}
.win .side .v a,.win .side .v b{border:1px solid var(--frame);padding:2px 10px;font-weight:400}
.win .side .v b{background:var(--accent);color:var(--onaccent);border-color:var(--accent)}
.zoom{display:none;position:fixed;inset:0;z-index:50;background:var(--bg);overflow:auto;padding:4vh 4vw}
.zoom:target{display:block}
.zoom img{display:block;width:180%;max-width:none;margin:0 auto;background:#fff;border:1px solid var(--frame)}
.zoom input{position:absolute;opacity:0;width:1px;height:1px}.zoom #zs100:checked~.pic img{width:100%}.zoom #zs300:checked~.pic img{width:300%}
.zoom .bar{position:fixed;top:12px;left:16px;z-index:1;display:flex;gap:6px}.zoom .bar label{font-size:13px;padding:8px 12px;margin:0;background:var(--paper);color:var(--fg);border:1px solid var(--frame);cursor:pointer}
.zoom #zs100:checked~.bar label[for=zs100],.zoom #zs180:checked~.bar label[for=zs180],.zoom #zs300:checked~.bar label[for=zs300]{background:var(--accent);color:var(--onaccent)}
.zoom #zs100:focus-visible~.bar label[for=zs100],.zoom #zs180:focus-visible~.bar label[for=zs180],.zoom #zs300:focus-visible~.bar label[for=zs300]{outline:2px solid var(--fg);outline-offset:2px}
.zoom .pic{margin-top:40px}
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
.ways{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0 0}.ways .lb{margin:0}
.toys .nm{display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;overflow:hidden;font-size:13px;letter-spacing:.08em;line-height:1.6;margin-top:8px}
.toys .big{grid-column:span 2;grid-row:span 2}.toys .big .pic{aspect-ratio:1600/2656;background-size:112% 112%;background-position:85% 50%}
@media (max-width:680px){.toys .big{grid-column:auto;grid-row:auto}}
.sample{display:inline-block;background:var(--accent);color:var(--onaccent);font-size:12px;letter-spacing:.2em;padding:1px 8px;margin-right:6px}
.is-sample{border-top:1px dashed var(--frame)}.is-sample svg{height:110px;width:auto;border:1px dashed var(--frame)}.samples{margin-top:18px}
.foot{padding:48px 5vw 40px;font-size:12px;color:var(--mute);letter-spacing:.1em;text-align:center;border-top:1px solid var(--rule)}
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
@media (max-width:820px){.hero,.win{grid-template-columns:1fr}.songs{writing-mode:horizontal-tb;height:auto;margin:0 0 14px}.hero .songs{float:none;margin:0 0 14px}.nav{gap:12px;padding:12px 16px}
 main,.wrap{padding-left:16px;padding-right:16px}.toys{grid-template-columns:repeat(auto-fill,minmax(120px,1fr))}}
@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
"""


def nav(skin, current="", path="/", lang="ja"):
    """頭の帯。順路の道だけ。皮の切り替えは置かない（皮ごとに 1 サイト。skin と path は呼び手の形を保つために残す）。"""
    if lang == "en":
        items = "".join(f'<a href="{p}">{esc(n)}</a>' for p, n in NAV_EN[1:])
        return f'<nav class="nav"><a class="brand" href="/en">utsushi</a>{items}</nav>'
    # 玩具の頁と手帖は道から「おもちゃ」に印を付ける。呼び手が current を渡さない頁の分
    here = current or ("/toys" if (path or "").startswith("/toy/") else "")
    mark = lambda p: ' aria-current="page"' if p == here else ""  # noqa: E731
    items = "".join(f'<a href="{p}"{mark(p)}>{esc(n)}</a>' for p, n in NAV)
    return f'<nav class="nav"><a class="brand" href="/"{mark("/")}>うつし</a>{items}</nav>'


def page_title(title):
    """<title> の形を「頁の名前 · うつし」にそろえる。頭に「うつし · 」を書いた呼び手の分も直す。入口は「うつし」だけ。"""
    name = title.removeprefix("うつし · ").removesuffix(" · うつし")
    return "うつし" if name in ("", "うつし") else f"{name} · うつし"


def entrance_style(skin):
    """入口の頁（骨は別）に、内側の頁と同じ帯の CSS を渡す。皮の変数も要る。入口だけ地を透かす（下の罫を置かない）。"""
    s = SKINS.get(skin, SKINS[DEFAULT])
    root = ";".join(f"--{k}:{v}" for k, v in s.items() if k != "name")
    # 入口の頁は body.tenji a のように a に下線を掛けるので、帯の下線だけ強い指定で外す（全部の頁で同じにする）。
    # 床は帯の CSS の後ろにもう 1 度置く。前にしかないと、帯の字の大きさが 12px に戻った
    return f":root{{{root}}}{NAV_STYLE}.nav{{border-bottom:0}}body .nav a:not([aria-current=page]){{border-bottom:0;text-decoration:none;color:var(--accent)}}{TAP_FLOOR}"


def shell(title, body, skin=DEFAULT, current="", path="/", extra_style="", body_class="", head="", foot="", lang="ja"):
    """頁の骨。皮の変数を :root に置き、頭の帯と足を付ける。中身（body）は皮を知らずに書けるようにする。"""
    s = SKINS.get(skin, SKINS[DEFAULT])
    root = ";".join(f"--{k}:{v}" for k, v in s.items() if k != "name")
    foot = foot or '<p class="foot">図は国立国会図書館デジタルコレクションの頁（米山堂・1931 年の複製、パブリック・ドメイン）。紙で動いても、昔の作り方の証明にはなりません。</p>'
    return (f'<!doctype html><html lang="{esc(lang)}"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{esc(page_title(title))}</title><style>:root{{{root}}}{BASE}{NAV_STYLE}{TAP_FLOOR}{extra_style}</style>{head}'
            f'<body class="skin-{esc(skin)}{" " + esc(body_class) if body_class else ""}">{nav(skin, current, path, lang)}<main>{body}</main>{foot}{WHO_SCRIPT}{BUSY_SCRIPT}</body></html>')


def frame(sid, caption="", pos=None):
    """額に入れた図。写しが無い時は地の色だけ（図の場所には国立国会図書館への道を別に置く）。looks._bg と同じ敷き方。"""
    from omochae.hypotheses import ROOT

    if (ROOT / "out/sources" / f"{sid}.jpg").exists():
        from .genga import size

        # 絵の比のまま敷く。前は額の比が必須 2 種の写しに固定で、ほかの玩具の切り抜きを縦横別々に伸ばしていた（59 種で 1.25 倍以上、
        # 最大 5.5 倍。原画の確かめ 11-06）。pos は呼び手の互換のために受けるが、比が合うので寄せる所は無い
        w, h = size(ROOT / "out/sources" / f"{sid}.jpg")
        style = f"background-image:url(/picture/{esc(sid)});aspect-ratio:{w}/{h};background-size:contain;background-position:center"
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
