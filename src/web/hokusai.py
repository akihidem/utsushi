"""サイトの『北斎漫画』の節（本人の決定 2026-11-05、#262: 案 1・2・3 を全部入れる。18 人は動く形でよい）。

- 案 1（白の展示）: 序の頁に 6 編の槍の型の頁を額に入れ、押すと 18 人が順に重なる。押さなければ動かない。
- 案 2（黒のジン）: 縦読みの章の頭に同じ人物を大きく置き、下へ送ると 1 人ずつ入れ替わる。
- 案 3（どちらのサイトにも）: 序の頁の短い節に 8 編の糸車と 3 編の遠近の線。

判断の芯:
- 筋は動画と同じ「絵は動きを止めて残した。どう動いたかは紙で作って確かめる」。
- 玩具の頁と一覧には置かない。『江都二色』の玩具の図と取り違えないため。絵のそばに必ず札を出す。
- 年は摺りの 1878 だけを出す。初めの刊年は人が確かめていない（data/hokusai/README.md）。
- 動きは見る人の操作だけで起こす。頁を開いただけでは動かさない。prefers-reduced-motion では自動で送らず、1 回の操作で 1 人ずつ進める。
- 絵が無い時（取り込めなかった時）は壊れた絵を出さず、国立国会図書館への道を出す。
"""
import html

from omochae import hokusai as hk

# 本人が採った文（11-05、#318）。一字も変えない。
LEAD = "絵は、動いているとちゅうを止めてかいています。どう動いたかは、紙で作ってたしかめます。"
MECH_LEAD = "江戸の人は、糸車のしくみも、平らな紙に奥ゆきを見せる線のかき方も、絵で残しました。うつしの型紙は、その絵から線をおこして、紙で作ってたしかめます。"


def esc(s):
    return html.escape(str(s))


def credit(rec):
    return f'{rec["short"] if "short" in rec else "北斎漫画 六編"}（1878 年の摺り）・葛飾北斎 画・{rec["attribution"]}（PDM）。{rec["modification_note"]}'


def link(rec):
    return f'https://dl.ndl.go.jp/{rec["persistent_id"].replace("info:ndljp/", "")}'


def src(name):
    return f"/hokusai/{name}.jpg"


def _missing(rec):
    return f'<p class="meta"><a href="{esc(link(rec))}" rel="noopener">{esc(rec.get("short", "北斎漫画 六編"))}を見る（国立国会図書館）</a></p>'


def _stack(ids):
    """足もとを揃えて重ねる。絵の線は変えない（動画の場面 1 と同じ揃え方）。"""
    return "".join(f'<img src="{src(f"{hk.FLIP_PAGE}-{i}")}" alt="" loading="lazy">' for i in ids)


FLIP_STYLE = """
.hk{display:grid;grid-template-columns:minmax(0,1.3fr) minmax(0,1fr);gap:28px;align-items:end;margin:18px 0}
.hk figure{margin:0}
.hk .page{width:100%;display:block;border:1px solid var(--frame);background:#efe8d8}
.hk .stack{position:relative;aspect-ratio:3/4;background:#efe8d8;border:1px solid var(--frame);overflow:hidden}
.hk .stack img{position:absolute;left:50%;bottom:6%;transform:translateX(-50%);height:84%;opacity:0;mix-blend-mode:multiply}
.hk .stack img.on{opacity:1}.hk .stack img.was{opacity:.12}
@media (max-width:760px){.hk{grid-template-columns:1fr}}
"""
# 押すと順に重なる。頁を開いただけでは動かない。動きを減らす設定の人は、1 回押すと 1 人進む。
FLIP_SCRIPT = """<script>(()=>{const s=document.getElementById('hk-stack'),b=document.getElementById('hk-play');if(!s||!b)return;
const f=[...s.querySelectorAll('img')];let i=0,t=0;const show=n=>{f.forEach((x,k)=>{x.className=k===n?'on':k<n?'was':''})};show(0);
const still=matchMedia('(prefers-reduced-motion: reduce)').matches;
b.addEventListener('click',()=>{if(still){i=(i+1)%f.length;show(i);return}clearInterval(t);i=0;show(0);t=setInterval(()=>{i++;if(i>=f.length){clearInterval(t);return}show(i)},170)})})()</script>"""


def flip_section():
    """案 1。白の展示の序の頁。"""
    rec = hk.pages()[hk.FLIP_PAGE]
    ids = hk.figure_ids()
    if not (hk.has(hk.FLIP_PAGE) and all(hk.has(f"{hk.FLIP_PAGE}-{i}") for i in ids)):
        return f'<section class="sec" id="hokusai"><h2>絵は動きを止めて残した</h2><p class="lead">{esc(LEAD)}</p>{_missing(rec)}</section>'
    return (f'<style>{FLIP_STYLE}</style><section class="sec" id="hokusai"><h2>絵は動きを止めて残した</h2><p class="lead">{esc(LEAD)}</p>'
            f'<div class="hk"><figure><img class="page" src="{src(hk.FLIP_PAGE)}" alt="北斎漫画 六編の槍の型の頁" loading="lazy"></figure>'
            f'<figure><div class="stack" id="hk-stack">{_stack(ids)}</div><p><button type="button" class="quiet" id="hk-play">{len(ids)} 人を順に重ねる</button></p></figure></div>'
            f'<p class="meta">{esc(credit(rec))}</p></section>{FLIP_SCRIPT}')


# 幅 760px 以下は 1 列で、絵の箱（前は高さ 56svh に固定）と字を縦に積む。英語の字は長く、幅 375×667 で字が 507px になり、積んだ高さが
# 留まる箱（100svh）を超えた。中寄せのままはみ出すので、絵が節の上の端より 115px 上へ出て前の節の出典の字に重なり、字の終わりは画面の下に切れていた
# （11-08 の見回り・tests/test_no_overlap.py）。絵の箱の行を minmax(0,56svh) にし、字が長い時は絵の箱の方が縮む（字は切らない）。
# 見出しと出典の行の高さも狭い幅だけ詰め、絵に残る高さを増やす（幅 375 の英語で絵の箱 117px → 143px）
# 見出しにルビのある時（やさしい日本語）は 1.9 に戻す。1.45 では、幅 375 で 2 行目のルビ（「のこ」）が 1 行目の字に重なった（#696 でルビの KNOWN を外した後の試験）。
# 幅 336px 以下の英語は、字だけで留まる箱（100svh）を超え（320×568 で 530px）、絵の箱が 2px につぶれて、留まった時に字の 10 行が画面の下へ出た
# （#687 の別の目の測り）。そこだけ留めずに流す（動きを減らす設定の形と同じ）。絵の箱は前の 56svh に戻し、下へ送ると 1 人ずつ替わる動きはそのまま
SCROLL_STYLE = """
.zn-hk{position:relative;height:420vh;border-top:1px solid #1f1b16}
.zn-hk .pin{position:sticky;top:0;height:100svh;display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:5vw;align-items:center;padding:0 7vw}
.zn-hk .stack{position:relative;height:78svh;background:#efe8d8;border:1px solid #6e5a35;outline:6px solid #141210;outline-offset:-7px;overflow:hidden}
.zn-hk .stack img{position:absolute;left:50%;bottom:5%;transform:translateX(-50%);height:86%;opacity:0;mix-blend-mode:multiply}
.zn-hk .stack img.on{opacity:1}
.zn-hk .chapter{font-size:12px;letter-spacing:.5em;color:#c9a96a;margin:0 0 12px}
.zn-hk h2{font-size:clamp(24px,2.6vw,36px);font-weight:300;letter-spacing:.25em;margin:0 0 18px}
.zn-hk .cap{font-size:12px;letter-spacing:.08em;line-height:1.9;color:#9a8e76}
@media (max-width:760px){.zn-hk .pin{grid-template-columns:1fr;grid-template-rows:minmax(0,56svh) auto;align-content:center;padding:12px 7vw}
 .zn-hk .stack{height:auto;align-self:stretch}.zn-hk h2{line-height:1.45;margin:0 0 12px}.zn-hk h2:has(ruby){line-height:1.9}.zn-hk .cap{line-height:1.7}}
@media (max-width:336px){html[lang=en] .zn-hk{height:auto}html[lang=en] .zn-hk .pin{position:static;height:auto;grid-template-rows:auto;padding:8vh 7vw}
 html[lang=en] .zn-hk .stack{height:56svh}}
@media (prefers-reduced-motion:reduce){.zn-hk{height:auto}.zn-hk .pin{position:static;height:auto;padding:12vh 7vw}}
"""
# 下へ送ると 1 人ずつ入れ替わる。送った量で決めるので、止まれば止まる。動きを減らす設定の人には最初の 1 人だけを出す。
SCROLL_SCRIPT = """<script>(()=>{const w=document.getElementById('zn-hokusai');if(!w)return;const f=[...w.querySelectorAll('.stack img')];
const show=n=>f.forEach((x,k)=>x.classList.toggle('on',k===n));show(0);if(matchMedia('(prefers-reduced-motion: reduce)').matches)return;
let q=false;const go=()=>{q=false;const r=w.getBoundingClientRect(),d=r.height-innerHeight;const u=d>0?Math.min(1,Math.max(0,-r.top/d)):0;show(Math.min(f.length-1,Math.floor(u*f.length)))};
addEventListener('scroll',()=>{if(!q){q=true;requestAnimationFrame(go)}},{passive:true});go()})()</script>"""


# 白の展示の色（本人の決定 11-06「ページは白案で統一します。黒案にだけある要素は白案に入れてください」）。縦読みの節の形と動きは黒と同じで、色だけを白の壁に合わせる
WHITE_SCROLL_STYLE = """
.tj-hk{border-top:1px solid #ebe8e2}
.tj-hk .stack{border-color:#d8cdb6;outline-color:#fffefc}
.tj-hk .chapter{color:#6b4f2a}.tj-hk h2{font-weight:400;color:#1f1b17}.tj-hk .cap{color:#7a7164}
"""


def scroll_section(look="zine"):
    """案 2。序の頁の縦読み（前は黒の入口の章の頭。11-08 に暗い版の入口を白と同じ作りにしてから、白と暗い版の両方の序の頁）。絵が無ければ節ごと出さない。
    前は黒のジンにだけあった。本人の決定（11-06）で白の展示にも入れる（look="tenji" で白の色）。字と動きは同じ。"""
    rec = hk.pages()[hk.FLIP_PAGE]
    ids = hk.figure_ids()
    if not all(hk.has(f"{hk.FLIP_PAGE}-{i}") for i in ids):
        return ""
    white = f"<style>{WHITE_SCROLL_STYLE}</style>" if look == "tenji" else ""
    return (f'<style>{SCROLL_STYLE}</style>{white}<section class="zn-hk{" tj-hk" if look == "tenji" else ""}" id="zn-hokusai" aria-label="北斎漫画"><div class="pin"><div class="stack">{_stack(ids)}</div>'
            f'<div><p class="chapter">北斎漫画</p><h2>絵は動きを止めて残した</h2><p>{esc(LEAD)}</p><p class="cap">下へ送ると、{len(ids)} 人が 1 人ずつ入れ替わります。{esc(credit(rec))}</p></div></div></section>{SCROLL_SCRIPT}')


MECH_STYLE = """
.hk-mech{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:22px;margin:18px 0}
.hk-mech figure{margin:0}.hk-mech img{width:100%;display:block;border:1px solid var(--frame);background:#efe8d8}
.hk-mech figcaption{font-size:12px;line-height:1.8;letter-spacing:.06em;color:var(--mute);margin-top:8px}
"""


def mechanism_section():
    """案 3。糸車と遠近の線。どちらのサイトの序の頁にも置く。"""
    all_pages = hk.pages()
    out = ""
    for name in (hk.WHEEL_PAGE, hk.LINES_PAGE):
        rec = all_pages[name]
        for c in rec["crops"]:
            piece = f'{name}-{c["id"]}'
            if hk.has(piece):
                out += f'<figure><img src="{src(piece)}" alt="{esc(c["what"])}" loading="lazy"><figcaption>{esc(c["what"])}。{esc(credit(rec))}</figcaption></figure>'
            else:
                out += f'<figure><figcaption>{esc(c["what"])}</figcaption>{_missing(rec)}</figure>'
    return f'<style>{MECH_STYLE}</style><section class="sec" id="hokusai-mech"><h2>江戸の絵も仕組みを図で残した</h2><p class="lead">{esc(MECH_LEAD)}</p><div class="hk-mech">{out}</div></section>'
