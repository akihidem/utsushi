"""試作: 窓口でここまで話してきた議論（本人の言葉）を持ち込んだ、入口と玩具の頁ひとつの別案（11-07）。

本人の言葉（11-07）:「昨日の話を持ち込んだサイトデザイン、デモ動画も作ってみる？（試作として）」。本人の訂正で「昨日の話」は録音ではなく、
窓口とのここまでの議論（本人の言葉）。窓口の作り方: 言葉は記録からそのまま抜く・本線は触らず差し替えできる層として作る・入口と玩具の頁ひとつの別案・
完成した形で 1 回見せる。

判断の芯:
- 層: 頁は /tameshi（入口の別案）と /tameshi/toy/<印>（玩具の頁の別案）だけ。play_server は環境の OMOCHAE_TAMESHI=1 の時だけ道を開く。
  本線の頁（入口・えらぶ・玩具の頁）は 1 字も変えない。外すときは道ごと閉じればよい。
- 字: 頁に出す文は本人の言葉（WORDS）と、今の頁に在る字（えらぶ・つくる・カメラに重ねる・こまった・型紙の版 など）だけ。
  本人の言葉は言い換えず、文の単位で抜く（作る側への指示の文「これを最初に伝える必要がある。」などは出さない）。引用の印は 「」 と
  序の頁と同じ「作った人の言葉」。感想（参加者の言葉）は使わない（本人の訂正）。
- 形（本人の言葉から）:
  - 入口: 最初の画面は根幹の 1 文だけ（「サイトの根幹は…型紙生成システム。」。同じ節の「これを最初に伝える必要がある」）。
    次に絵が並ぶ（「サイト、絵が並び、タップすると絵から3Dイメージが立ち上がる。…基本構造はシンプルがいい。」）。
    絵を押すと、その場で絵が奥へ倒れ、3D が下から立ち上がる。横に送ると、ほかの人が作った物、端に「つくる」。
    ガウシアンスプラッティングの 3D はまだ無いので描かない（作っていない物を作ったように見せない）。写真と見本の札だけ。
  - 玩具の頁: 原画 → 型紙 → 3D の順（「原画→型紙→3D という順番で、3D で見れる作成手順が…」）。3D の作成手順は今の組み立ての絵（kumitate）、
    重ねる口は今の「カメラに重ねる」の頁へ。版の並び（型紙の版 10 → 14 など）は、刷った紙の絵が手元（out/tameshi/ban）に在る時だけ出す。
  - 見た目: 「基本は、余白、間を大切にした日本画の展示空間。」白い地、大きな余白、字は少なく。
  - 案内役: 「ガイドは北斎漫画から出てきた人。」「作業中に聞いて答えてくれるのは彼。」デモの案内役 B の切り絵（out/tameshi/guide.png）を
    右下に立たせ、押すと聞く口（玩具の頁の #ask）へ。絵が手元に無ければ出さない。
- 版の数は組から読む（hypotheses.set_number）。今の main の組は御来迎 v10・虎 v4 なので、エンジンの v14・v7 の写しが入るまでは 10・4 と出る。
  版の並びの絵は刷った紙そのもの（Drive の版ごとの PDF の 1 頁目を out/tameshi/ban に写した物。git に入れない）。
"""
import json
import re

from omochae import hypotheses
from omochae.hypotheses import ROOT

from . import skin
from .skin import esc

# 本人の言葉（言い換えなし。元は grove の state/standing-decisions.md の本人の言葉の節。窓口の議論から抜いた words.md と同じ字）
WORDS = {
    # 本人の指示（11-07 未明）。2 つ目の文「これを最初に伝える必要がある。」は作る側への指示なので出さない
    "konkan": "サイトの根幹は、ユーザーによりその場で自己改善する進化するウェブページ、型紙生成システム。",
    # 本人の言葉・核の体験（11-07 未明）
    "taiken": "ユーザーには、絵が立体のおもちゃとなって自分の手のひらで遊べるようになることを体験してもらいたい。",
    # 本人の言葉・教育の原形（11-07 未明）
    "genkei": "教育の原形、まねぶ、自らあそぶ、トライアンドエラー、つくってこわす、おそわる、教師は人間いがいに自分も含めた自然、周囲",
    # 本人の言葉・版を見せる（11-07 朝）の 1 文目
    "ban": "ワークショップ2回や型紙の試作を繰り返し、型紙のが改善されたことは面白いと思う。",
    # 本人の指示・作業ページの前提（11-07 未明）
    "junban": "原画→型紙→3D という順番で、3D で見れる作成手順が空間に表示されるのを見ながら作っていく。",
}
WHO = "作った人の言葉"  # 序の頁（about.py）の見出しと同じ字
GO = "えらぶ"          # 入口の道しるべ（looks.ROAD_GO）と同じ字
MAKE = "つくる"        # 道しるべの字
KASANE = "カメラに重ねる"  # 手帖からの道の字（本人の決定 11-07）
KOMATTA = "こまった"    # 手帖の聞く口の字
BAN = "型紙の版 {n}"    # 窓口の決定（カード 084426）: 型紙の版とエンジンの版を言い分ける
ENGINE = "エンジンの版 {n}"
STEPS = ("原画", "型紙", "3D")  # 本人の言葉「原画→型紙→3D」の 3 語

GUIDE = ROOT / "out/tameshi/guide.png"
BAN_DIR = ROOT / "out/tameshi/ban"

STYLE = """
.ts{--ma:clamp(48px,12vh,140px)}
.ts-hall{min-height:100vh;min-height:100svh;display:grid;align-content:center;justify-items:center;gap:5vh;padding:0 8vw;text-align:center}
.ts-hall h1{font-size:clamp(28px,4vw,44px);letter-spacing:.6em;font-weight:400;margin:0 0 0 .6em}
.ts-word{margin:0;font-size:clamp(17px,2.1vw,24px);line-height:2.2;letter-spacing:.12em;max-width:22em}
.ts-who{font-size:12px;letter-spacing:.3em;color:var(--mute);margin:10px 0 3vh}
.ts-hall .ts-who{margin:-3vh 0 0}
.ts-go{font-size:15px;letter-spacing:.5em;padding:12px 26px;border:1px solid var(--frame);color:var(--fg);text-decoration:none}
.ts-narabi{padding:var(--ma) 24px;max-width:1280px;margin:0 auto}
.ts-grid{columns:7 96px;column-gap:16px;list-style:none;margin:0;padding:0}
.ts-grid li{break-inside:avoid;margin:0 0 16px}
.ts-grid button{all:unset;display:block;width:100%;cursor:pointer}
.ts-grid img{display:block;width:100%;height:auto;border:1px solid var(--frame);background:var(--soft)}
.ts-grid .nm{display:block;font-size:12px;letter-spacing:.08em;margin-top:6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.ts-tate{padding:var(--ma) 8vw;display:grid;justify-items:center;gap:2vh}
.ts-tate .ts-word{writing-mode:vertical-rl;max-height:70vh;line-height:2.4}
.ts-up{position:fixed;inset:0;background:var(--bg);z-index:40;display:grid;grid-template-rows:auto 1fr}
.ts-up[hidden]{display:none}
.ts-up .bar{display:flex;justify-content:space-between;align-items:center;padding:12px 20px}
.ts-up .bar button{font:inherit;background:none;border:0;color:var(--fg);font-size:22px;min-width:44px;min-height:44px;cursor:pointer}
.ts-slides{display:flex;overflow-x:auto;scroll-snap-type:x mandatory;height:100%;-webkit-overflow-scrolling:touch}
.ts-slide{flex:0 0 100%;scroll-snap-align:center;overflow-y:auto;padding:2vh 6vw 10vh;box-sizing:border-box}
.ts-rise{perspective:1200px;display:grid;justify-items:center;gap:3vh}
.ts-rise .pic{max-width:min(420px,80vw);max-height:46vh;border:1px solid var(--frame);transform-origin:50% 100%;transition:transform 1.2s cubic-bezier(.22,.61,.36,1),opacity 1.2s}
.ts-rise .solid{width:min(560px,92vw);transform-origin:50% 100%;transform:rotateX(78deg);opacity:0;transition:transform 1.4s cubic-bezier(.22,.61,.36,1) .5s,opacity 1s .5s}
.ts-up.is-up .ts-rise .pic{transform:rotateX(58deg) scale(.82);opacity:.55}
.ts-up.is-up .ts-rise .solid{transform:none;opacity:1}
.ts-ban{font-size:12px;letter-spacing:.2em;color:var(--accent)}
.ts-hint{font-size:12px;letter-spacing:.2em;color:var(--mute);text-align:center}
.ts-made{display:grid;gap:3vh;justify-items:center}
.ts-made img,.ts-made video{max-width:min(520px,88vw);max-height:60vh;border:1px solid var(--frame)}
.ts-end{display:grid;place-items:center;height:70vh}
.ts-guide{position:fixed;right:6px;bottom:0;z-index:45;opacity:.9}
.ts-guide img{display:block;height:clamp(96px,14vh,150px);width:auto}
.ts-step{padding:var(--ma) 6vw;border-top:1px solid var(--rule);max-width:1100px;margin:0 auto}
.ts-step .no{font-size:12px;letter-spacing:.5em;color:var(--mute);margin:0 0 3vh}
.ts-step .sheet{max-width:min(520px,90vw);border:1px solid var(--frame);display:block}
.ts-banrow{display:flex;gap:16px;overflow-x:auto;padding:2vh 0;scroll-snap-type:x proximity}
.ts-banrow figure{margin:0;flex:0 0 auto;scroll-snap-align:start;text-align:center}
.ts-banrow img{height:min(46vh,360px);width:auto;border:1px solid var(--frame);background:#fff}
.ts-banrow figure{max-width:260px}
.ts-banrow figcaption{font-size:12px;letter-spacing:.2em;color:var(--accent);margin-top:8px;display:grid;gap:4px;text-align:left}
.ts-banrow figcaption .eng{color:var(--mute);letter-spacing:.1em}
.ts-banrow figcaption .line{color:var(--fg);letter-spacing:.04em;line-height:1.7;white-space:normal}
.ts-banrow figcaption .date{color:var(--mute);letter-spacing:.1em}
.ts-story{max-width:34em;line-height:2}
@media (prefers-reduced-motion:reduce){.ts-rise .pic,.ts-rise .solid{transition:none}}
"""

# 絵を押すと、その場の札を開き、絵を奥へ倒して 3D を立ち上げる。中身は /tameshi/up/<印> から読む（83 の 3D を最初に全部刷らないため）。
# 読んだ中身の <script> は innerHTML では動かないので、作り直して動かす（組み立ての絵の台本）。見えた時に起こす仕掛けは使わない（押した時だけ）。
JS = """<script>(()=>{const up=document.getElementById('ts-up'),box=document.getElementById('ts-slides'),close=document.getElementById('ts-close');
if(!up)return;
const open=async sid=>{box.innerHTML='';up.hidden=false;up.classList.remove('is-up');document.body.style.overflow='hidden';
const r=await fetch('/tameshi/up/'+encodeURIComponent(sid));box.innerHTML=await r.text();
box.querySelectorAll('script').forEach(s=>{const n=document.createElement('script');n.textContent=s.textContent;s.replaceWith(n)});
box.scrollLeft=0;requestAnimationFrame(()=>requestAnimationFrame(()=>up.classList.add('is-up')))};
document.querySelectorAll('.ts-grid button[data-sid]').forEach(b=>b.addEventListener('click',()=>open(b.dataset.sid)));
const shut=()=>{up.hidden=true;box.innerHTML='';document.body.style.overflow=''};
close.addEventListener('click',shut);document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!up.hidden)shut()})})();</script>"""


def enabled():
    import os

    return os.environ.get("OMOCHAE_TAMESHI") == "1"


def _quote(key, cls="ts-word"):
    return f'<blockquote class="{cls}">「{esc(WORDS[key])}」</blockquote><p class="ts-who">{esc(WHO)}</p>'


def _guide(sid=None):
    if not GUIDE.exists():
        return ""
    href = f"/toy/{esc(sid)}#ask" if sid else "/toys"
    return f'<a class="ts-guide" href="{href}" aria-label="{esc(KOMATTA)}"><img src="/tameshi/guide.png" alt=""></a>'


def _ban(sid):
    return esc(BAN.format(n=hypotheses.set_number(hypotheses.load(sid))))


def _tile(sid):
    from . import toys

    data = hypotheses.load(sid)
    path = ROOT / "out/sources" / f"{sid}.jpg"
    if path.exists():
        w, h = toys._size(str(path), path.stat().st_mtime)
        pic = f'<img src="/picture/{esc(sid)}/small" width="{w}" height="{h}" style="aspect-ratio:{w}/{h}" loading="lazy" decoding="async" alt="">'
    else:
        pic = '<img alt="" style="aspect-ratio:3/4">'
    return f'<li><button type="button" data-sid="{esc(sid)}" aria-label="{esc(data["toy"])}">{pic}<span class="nm">{esc(data["toy"])}</span></button></li>'


def entrance(look=skin.DEFAULT, path="/tameshi"):
    """入口の別案。根幹の 1 文 → 絵が並ぶ → 教育の原形の言葉（縦書き）。絵を押すと、その場で 3D が立ち上がる。"""
    from . import toys

    sids, main = toys.counts()
    order = main + [s for s in sids if s not in main]
    body = (f'<div class="ts"><section class="ts-hall"><p class="en">Lost toys of Edo · 1773</p><h1>うつし</h1>{_quote("konkan")}'
            f'<a class="ts-go" href="#narabi">{esc(GO)}</a></section>'
            f'<section class="ts-narabi" id="narabi"><ul class="ts-grid">{"".join(_tile(s) for s in order)}</ul></section>'
            f'<section class="ts-tate">{_quote("genkei")}</section></div>'
            f'<div class="ts-up" id="ts-up" hidden role="dialog" aria-modal="true"><div class="bar"><span></span>'
            f'<button type="button" id="ts-close" aria-label="とじる">×</button></div><div class="ts-slides" id="ts-slides"></div></div>'
            + _guide() + JS)
    return skin.shell("うつし · 試作", body, look, path=path, extra_style=STYLE)


def _made(sid):
    """横に送った先: ほかの人が作った物。人が確かめた写真と動画（ギャラリーと同じ道）を、無ければ見本の札（見本の印つき）を並べる。"""
    from . import techo_site
    from omochae import records

    out = []
    for r in records.all_records(sid):
        for m in techo_site.media_of(r["id"]):
            if not m.get("checked"):
                continue
            tag = "video" if m.get("kind") == "video" else "img"
            src = f'/media/{esc(r["id"])}/{esc(m["name"])}'
            out.append(f'<video src="{src}" controls playsinline muted></video>' if tag == "video" else f'<img src="{src}" alt="" loading="lazy">')
    return out


def up(sid):
    """絵を押した時の札の中身（横に送る並び）。1 枚目: 絵が倒れて 3D が立ち上がる。2 枚目から: ほかの人が作った物。端: つくる。"""
    from . import kumitate

    data = hypotheses.load(sid)
    solid = kumitate.block(sid, heading=False)
    if not solid:
        solid = kumitate.section(sid, level=None)
    path = ROOT / "out/sources" / f"{sid}.jpg"
    pic = f'<img class="pic" src="/picture/{esc(sid)}" alt="">' if path.exists() else ""
    slides = [f'<div class="ts-slide"><div class="ts-rise">{pic}<div class="solid">{solid}</div><p class="ts-ban">{_ban(sid)}</p></div></div>']
    made = _made(sid)
    if made:
        slides.append(f'<div class="ts-slide"><div class="ts-made">{"".join(made)}</div></div>')
    slides.append(f'<div class="ts-slide ts-end"><a class="ts-go" href="/tameshi/toy/{esc(sid)}">{esc(MAKE)}</a></div>')
    return "".join(slides) + _guide(sid).replace('class="ts-guide"', 'class="ts-guide" style="z-index:50"')


def _history_doc():
    """エンジンが出す改善の歴史の表（grove の state/history/kaizen-history.json を out/tameshi に写した物。git に入れない）。無ければ空。
    版ごとの 1 行・日付・エンジンの版は表の字のまま出す（窓口の決定: 頁で版ごとの字を別に書かない）。"""
    path = ROOT / "out/tameshi/kaizen-history.json"
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except (OSError, ValueError):
        return {}


def _history(toy):
    """その玩具の型紙の版ごとの行（型紙の版 → 行）。"""
    for t in _history_doc().get("toys", []):
        if t.get("toy") == toy:
            return {v["sheet_version"]: v for v in t.get("versions", []) if isinstance(v.get("sheet_version"), int)}
    return {}


def _ban_row(sid):
    """版の並び。今の組の名前（goraigo-v10 なら goraigo）の版ごとの紙の絵が手元に在る時だけ、版の順に並べる。"""
    name = re.sub(r"-v\d+$", "", hypotheses.current_set(hypotheses.load(sid)))
    found = sorted(((int(m.group(1)), p) for p in BAN_DIR.glob(f"{name}-v*.png") if (m := re.fullmatch(rf"{re.escape(name)}-v(\d+)", p.stem))))
    if len(found) < 2:
        return ""
    from PIL import Image

    def img(p):
        # 縦横を書いて、読み込む前から額の幅を決める（無いと幅 0 の細い枠が並んだ。11-07 に幅 390 で見た）
        with Image.open(p) as im:
            w, h = im.size
        return f'<img src="/tameshi/ban/{esc(p.name)}" width="{w}" height="{h}" style="aspect-ratio:{w}/{h}" alt="">'
    hist = _history(hypotheses.load(sid)["toy"])
    story = esc(_history_doc().get("story", ""))

    def cap(n):
        v = hist.get(n)
        if not v:
            return f"<figcaption>{esc(BAN.format(n=n))}</figcaption>"
        eng = f'<span class="eng">{esc(ENGINE.format(n=v["engine_version"]))}</span>' if isinstance(v.get("engine_version"), int) else ""
        return (f'<figcaption>{esc(BAN.format(n=n))}{eng}<span class="line">{esc(v.get("line", ""))}</span>'
                f'<span class="date">{esc(v.get("date", ""))}</span></figcaption>')
    figs = "".join(f'<figure>{img(p)}{cap(n)}</figure>' for n, p in found)
    lead = f'<p class="lead ts-story">{story}</p>' if story else ""
    return f'<section class="ts-step">{_quote("ban")}{lead}<div class="ts-banrow">{figs}</div></section>'


def toy_page(sid, look=skin.DEFAULT, path=None):
    """玩具の頁の別案。原画 → 型紙 → 3D の順。版の並びと、案内役（押すと聞く口へ）。"""
    from . import genga, kumitate
    from .play_server import out_dir, printed_versions

    data = hypotheses.load(sid)
    src = json.loads((ROOT / "data/sources" / f"{sid}.json").read_text(encoding="utf-8"))
    h = hypotheses.sheet_of(sid)
    got = printed_versions(sid, h["id"]) if callable(printed_versions) else []
    png = next((f"/sheet/{sid}/{h['id']}_v{v}.png" for v in reversed(got or []) if (out_dir(sid) / f"{h['id']}_v{v}.png").exists()), "")
    if not png:
        # まだ刷っていない場では、今の組の版の紙の絵（版の並びと同じ置き場）を見せる。刷ると、刷った紙の絵に替わる
        cur = hypotheses.current_set(data)
        png = f"/tameshi/ban/{cur}.png" if (BAN_DIR / f"{cur}.png").exists() else ""
    sheet = f'<img class="sheet" src="{esc(png)}" alt="">' if png else ""
    solid = kumitate.block(sid, heading=False) or kumitate.section(sid, level=None)
    body = (f'<div class="ts"><section class="ts-step"><p class="no">{esc(STEPS[0])}</p>{genga.head(sid, src)}<h1>{esc(data["toy"])}</h1>'
            f'<p><a class="ts-go" href="#kata">{esc(MAKE)}</a></p></section>'
            f'<section class="ts-step" id="kata"><p class="no">{esc(STEPS[1])}</p><p class="ts-ban">{_ban(sid)}</p>{sheet}'
            f'<form method="post" action="/toy/{esc(sid)}/print#kasetsu"><input type="hidden" name="hypothesis" value="{esc(h["id"])}">'
            f'<button class="quiet" data-busy>型紙を見る</button></form></section>'
            f'<section class="ts-step"><p class="no">{esc(STEPS[2])}</p>{_quote("junban")}{solid}'
            f'<p><a class="btn quiet" href="/toy/{esc(sid)}/kasane">{esc(KASANE)}</a></p></section>'
            + _ban_row(sid) +
            f'<section class="ts-step">{_quote("taiken")}<p><a href="/tameshi">うつし</a></p></section></div>' + _guide(sid))
    return skin.shell(f"{data['toy']} · 試作", body, look, path=path or f"/tameshi/toy/{sid}", extra_style=STYLE)
