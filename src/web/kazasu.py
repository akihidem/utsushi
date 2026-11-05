"""かざして選ぶ（U-44、Issue #118）。本人の案（2026-11-05 朝、窓口を通して届いた）:
「インカメラで見せながら一緒に作る。動かない絵が自分と iPhone の画面の間にあるように映り、どれが良いか選ぶ。実際は紙で作る。
作業で止まったらそのままどうすればいいか聞ける」。

何をする頁か: 文字で予想を書く代わりに、内カメラの自分の映像の上に原図（動かない絵）を重ねて見せ、「どこが動くと思うか」を
候補の絵のタップで選ぶ。選んだ事が予想として残り、仮説と型紙が開く。作るのは紙。
文字で予想を書く今の道（/toy/<sid> の「先に、予想を書く」）は変えない。

判断の芯:
- **映像は端末の外へ出さない。** 子どもの顔や部屋が映る物を、送らず・録らず・残さない（決まり「子どもの写真・声は扱わない」（J-021・仕様書 I2）の線）。
  だから画素を写し取る・画像にする・録る・網へ送る code を置かない。サーバへ行くのは、押した候補の印（フォームの送信）だけ。
  試験（tests/test_kazasu.py）で、頁にその種の JS が無い事を固定する。
- カメラは押した時だけ動かす。頁を開いただけで許可を求めない（何のためか読んでから決められるように）。使わなくても同じ候補で選べる。
- **選ぶ物は「動く所の候補の絵」。** 原図の上に、動きそうな場所を枠で示した絵を 2〜3 枚出す。札の字は部品の呼び名だけ（扇の所・頭 など）。
  仮説の名前・字（A・B）・動かし方の文・根拠は出さない（F9.prediction: 予想の前は仮説の中身を出さない、の線を保つ。Issue #118）。
  今朝の試作は動かし方の文を札にしていて、この線を緩めていた。候補の絵に替えて、線を元に戻した。
- 候補は手で決めた箱（仮説の記録の move_candidates）。新しい絵は作らず、同じ写し（/picture/<sid>）の上に CSS の枠を重ねる。
  候補を置いたのは必須の 2 種だけ。候補の無い玩具（試作の 81 種）では、重ねた絵と「自分の言葉で書く」への道だけを出す
  （動かし方の文の札は出さない。広げるのは、仮説の記録に動く場所の欄を足してから。Issue #118 の「広げる順」）。
- 重ねた絵は指で動かせる（1 本の指で位置、2 本の指か下のつまみで大きさ）。自分の顔や手に合わせて置けるように。
  pointer の出来事と CSS の transform だけで作り、画素には触らない。
- 選んだ候補を当たりのように扱わない。選んだ後の文は「予想を残しました。紙で確かめます」だけ。並びは記録の並びで、大きさも色も同じ（J-025）。
- 見えた時に起こす仕掛けは置かない。動きは映像の切り替えの薄い移り変わりだけで、prefers-reduced-motion で止める。
- 全画面なので頭の帯は付けず、皮（白の展示・黒のジン）の変数だけを使う。高さは 100svh（スマホの URL の帯に隠れない。research/19）。
"""
import functools
import json

from omochae import hypotheses
from omochae.hypotheses import ROOT

from . import skin
from .play_server import esc, source

SENT = "予想を残しました。紙で確かめます"
PRIVACY = "映像はこの端末の中だけで、送りも残しもしません。"

STYLE = """
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--fg);font-family:"Noto Serif CJK JP","Noto Serif JP","Hiragino Mincho ProN","Yu Mincho",serif;line-height:1.7;font-size:16px}
a{color:var(--accent)}
.stage{position:relative;min-height:100svh;display:flex;flex-direction:column;overflow:hidden}
/* 映像は鏡のように左右を返す（自分の動きと同じ向きに見えるように）。カメラを使うまでは出さない。 */
#cam{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;transform:scaleX(-1);opacity:0;transition:opacity .4s}
.live #cam{opacity:1}
.top{position:relative;z-index:2;display:flex;justify-content:space-between;gap:12px;margin:0;padding:12px 16px;font-size:13px;letter-spacing:.08em}
.top a,.top span{background:color-mix(in srgb,var(--bg) 78%,transparent);padding:4px 10px;text-decoration:none}
/* 絵は画面の幅の 6 割ほど、中央やや上。カメラが動いている時は、紙の地を白へ寄せてから掛け合わせ（multiply）、線と色だけを映像の上に残す。
   白×映像＝映像なので、紙の地が抜けて、絵が自分と画面の間に浮いて見える。カメラが無い時は掛け合わせず、地の色の上にそのまま出す。 */
/* z-index を付けない: 付けると .fig が重なりの文脈を作り、中の .pic の掛け合わせ（mix-blend-mode）が映像まで届かず、白い面が顔を覆う（検品で再現）。
   並びは頁の順（#cam の後）で手前に出る。 */
.fig{position:relative;flex:1 1 auto;min-height:36svh;display:grid;place-items:center;padding:4px 0}
/* 指で動かす: 位置と大きさは CSS の変数で持ち、transform だけで動かす（画素には触らない）。touch-action:none は、絵を引く指で頁が巻かれないため。 */
.pic{width:60vw;max-width:420px;max-height:44svh;background:center/contain no-repeat;transform:translate(var(--tx,0px),var(--ty,0px)) scale(var(--sc,1));
 touch-action:none;cursor:grab;-webkit-user-select:none;user-select:none}
.pic:active{cursor:grabbing}
.pic:focus-visible{outline:2px solid var(--accent);outline-offset:4px}
/* 紙の地（黄みの強い色）は、色を薄めてから明るさと差を上げて白へ寄せる。色を薄めないと、掛け合わせた時に黄色い面として残る（写しで比べて決めた）。
   線が痩せすぎない所で止め、縁は薄く消して四角い紙の端を見せない。 */
.live .pic{mix-blend-mode:multiply;filter:saturate(.45) contrast(1.8) brightness(1.32);
 -webkit-mask-image:radial-gradient(ellipse at center,#000 58%,transparent 100%);mask-image:radial-gradient(ellipse at center,#000 58%,transparent 100%)}
.nopic{position:relative;z-index:1;flex:1 1 auto;min-height:20svh;display:grid;place-items:center;text-align:center;font-size:13px;color:var(--mute);padding:0 16px}
.panel{position:relative;z-index:2;background:color-mix(in srgb,var(--bg) 86%,transparent);padding:12px 16px 18px;max-height:58svh;overflow:auto;border-top:1px solid var(--rule)}
.q{margin:0 0 8px;font-size:15px}
.state{margin:0 0 8px;font-size:12px;color:var(--mute)}
.state button,.tools button{font:inherit;font-size:12px;color:var(--accent);background:transparent;border:1px solid var(--accent);padding:6px 12px;margin-right:8px;cursor:pointer}
.tools{display:flex;gap:10px;align-items:center;margin:0 0 10px;font-size:12px;color:var(--mute)}
.tools label{display:flex;gap:8px;align-items:center;flex:1 1 auto}
.tools input[type=range]{flex:1 1 auto;min-width:80px;accent-color:var(--accent)}
.tools button{margin-right:0}
/* 候補の絵は横に並べる。並びは記録の並びで、大きさも色も同じ（上下を付けない）。押しやすい大きさ（幅の 1/3、高さは 44px より十分大きい）。 */
.cands{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin:0}
.cand{display:block;width:100%;padding:6px;font:inherit;color:var(--fg);background:var(--paper);border:1px solid var(--frame);cursor:pointer;text-align:center}
.cand:hover,.cand:focus-visible{border-color:var(--accent);outline:none;box-shadow:0 0 0 1px var(--accent) inset}
.cand .thumb{position:relative;display:block;width:100%;background-repeat:no-repeat;background-color:#fff}
/* 動きそうな場所の印。枠だけで、矢印や動きの絵は描かない（どう動くかは見せない）。白い縁は、紙の色の上でも枠が読めるように。 */
.cand .mark{position:absolute;border:3px solid var(--accent);border-radius:8px;box-shadow:0 0 0 2px #fff}
.cand .lb{display:block;margin-top:6px;font-size:14px;line-height:1.4}
.other{display:block;margin:8px 0 0;min-height:44px;padding:10px 14px;font-size:14px;color:var(--mute);background:var(--paper);border:1px solid var(--frame);text-decoration:none}
.other:hover{border-color:var(--accent)}
.note{margin:10px 0 0;font-size:12px;color:var(--mute)}
#msg{margin:0 0 8px;font-size:13px;color:var(--accent)}
@media (prefers-reduced-motion:reduce){#cam{transition:none}}
"""

# カメラは押した時にだけ求める。映像は <video> に流すだけで、画素を取り出さない（写し取る・録る・送る code を置かない）。
# ?cam=1 を付けて開いた時は、開いた時に求める（確かめの写しを撮るための口。許可の窓はいつもどおり出る）。
# 頁を離れる時はカメラを止める（灯りが点いたままにしない）。
# 絵を動かす所: 1 本の指（かマウス）で引くと位置、2 本の指でつまむと大きさ。つまみ（range）と矢印の鍵でも動く（指が使えない時の道）。
# 位置と大きさは CSS の変数に書くだけで、どこにも送らず、残さない。
SCRIPT = """<script>(()=>{const v=document.getElementById('cam'),b=document.getElementById('on'),s=document.getElementById('state');
const off='カメラは使わずに選べます。';
const pic=document.getElementById('pic'),size=document.getElementById('size'),reset=document.getElementById('reset');
if(pic){let tx=0,ty=0,sc=1,d0=0,s0=1;const pts=new Map();
const put=()=>{pic.style.setProperty('--tx',tx+'px');pic.style.setProperty('--ty',ty+'px');pic.style.setProperty('--sc',sc);if(size)size.value=Math.round(sc*100)};
const dist=()=>{const a=[...pts.values()];return Math.hypot(a[0].x-a[1].x,a[0].y-a[1].y)};
pic.addEventListener('pointerdown',e=>{pic.setPointerCapture(e.pointerId);pts.set(e.pointerId,{x:e.clientX,y:e.clientY});if(pts.size===2){d0=dist();s0=sc}});
pic.addEventListener('pointermove',e=>{const p=pts.get(e.pointerId);if(!p)return;
if(pts.size===1){tx+=e.clientX-p.x;ty+=e.clientY-p.y}
pts.set(e.pointerId,{x:e.clientX,y:e.clientY});
if(pts.size===2&&d0>0)sc=Math.min(2.4,Math.max(.5,s0*dist()/d0));
put()});
const up=e=>{pts.delete(e.pointerId);d0=0};
pic.addEventListener('pointerup',up);pic.addEventListener('pointercancel',up);
pic.addEventListener('keydown',e=>{const k={ArrowLeft:[-12,0],ArrowRight:[12,0],ArrowUp:[0,-12],ArrowDown:[0,12]}[e.key];if(k){tx+=k[0];ty+=k[1];put();e.preventDefault()}});
if(size)size.addEventListener('input',()=>{sc=size.value/100;put()});
if(reset)reset.addEventListener('click',()=>{tx=0;ty=0;sc=1;put()})}
if(!navigator.mediaDevices||!navigator.mediaDevices.getUserMedia){s.textContent='この機器ではカメラを使えません。'+off;return}
const start=async()=>{try{const st=await navigator.mediaDevices.getUserMedia({video:{facingMode:'user'},audio:false});
v.srcObject=st;document.body.classList.add('live');s.textContent='__PRIVACY__'}catch(e){s.textContent='カメラを使えませんでした。'+off}};
b.addEventListener('click',start);
if(new URLSearchParams(location.search).get('cam')==='1')start();
addEventListener('pagehide',()=>{const st=v.srcObject;if(st)st.getTracks().forEach(t=>t.stop())});
})()</script>""".replace("__PRIVACY__", PRIVACY)


@functools.lru_cache(maxsize=1)
def _inventory():
    path = ROOT / "data/inventory/edo-nishiki.json"
    return {t["id"]: t for t in json.loads(path.read_text(encoding="utf-8"))["toys"]} if path.exists() else {}


def _pct(region):
    return [float(v) for v in region[4:].split(",")]


def candidates(data):
    """動く所の候補（仮説の記録の move_candidates）。形の崩れた物は落とす（箱は写しに対する 0〜1 の割合で、左上と右下）。"""
    out = []
    for c in data.get("move_candidates") or []:
        box = c.get("box") or []
        if c.get("id") and c.get("label") and len(box) == 4 and 0 <= box[0] < box[2] <= 1 and 0 <= box[1] < box[3] <= 1:
            out.append(c)
    return out


def view_box(sid, src, cands=()):
    """絵のどこを見せるか（写しに対する 0〜1 の箱）。None は写しをそのまま収める。
    写しが半頁の玩具（必須の 2 種）は、頁の周りの黒い地と歌の字まで入っているので、棚卸しの箱（玩具の所）だけを見せる。
    なぜ: 映像に掛け合わせると、黒い地は黒い枠としてそのまま残り、自分の顔が隠れる。切り出しの写し（試作の玩具）はそのまま収める。
    候補の箱が棚卸しの箱から少しはみ出す事がある（虎の尾）ので、候補の箱も全部入るように広げ、周りに少し余白を取る。"""
    toy = _inventory().get(sid)
    sx, sy, sw, sh = _pct(src.get("crop_region", "pct:0,0,100,100"))
    if not toy or (sw, sh) != (50.0, 100.0):
        return None
    x, y, w, h = _pct(toy["region"])
    boxes = [((x - sx) / sw, (y - sy) / sh, (x - sx + w) / sw, (y - sy + h) / sh)] + [tuple(c["box"]) for c in cands]
    m = 0.015
    x0, y0 = max(0.0, min(b[0] for b in boxes) - m), max(0.0, min(b[1] for b in boxes) - m)
    x1, y1 = min(1.0, max(b[2] for b in boxes) + m), min(1.0, max(b[3] for b in boxes) + m)
    if x1 - x0 >= 1 or y1 - y0 >= 1:
        return None
    return (x0, y0, x1, y1)


def view_style(src, view):
    """箱（view）だけを見せる背景の敷き方。画像は作り直さず、背景の大きさと位置で切り出す。
    縦横比は、写しが見開き（横 1600・縦 1328 の比、research/26）のどれだけを占めるかから出す（写しの画素は読まない）。"""
    if view is None:
        return "aspect-ratio:1/1;background-size:contain"
    _, _, sw, sh = _pct(src.get("crop_region", "pct:0,0,100,100"))
    fw, fh = view[2] - view[0], view[3] - view[1]
    ratio = (fw * sw * 1600) / (fh * sh * 1328)
    return (f"aspect-ratio:{ratio:.3f};background-size:{100 / fw:.1f}% {100 / fh:.1f}%;"
            f"background-position:{100 * view[0] / (1 - fw):.1f}% {100 * view[1] / (1 - fh):.1f}%")


def _mark(view, box):
    """候補の枠の置き場（見せている箱の中での百分率）。"""
    fw, fh = view[2] - view[0], view[3] - view[1]
    return (f"left:{100 * (box[0] - view[0]) / fw:.1f}%;top:{100 * (box[1] - view[1]) / fh:.1f}%;"
            f"width:{100 * (box[2] - box[0]) / fw:.1f}%;height:{100 * (box[3] - box[1]) / fh:.1f}%")


def has_picture(sid):
    """原図の写し（out/sources の jpg）が手元に在るか。写しは git の外なので、まっさらな clone では無い（その時は候補を出さず、字の予想へ案内する）。"""
    return (ROOT / "out/sources" / f"{sid}.jpg").exists()

def page(sid, look=skin.DEFAULT, error=""):
    """かざして選ぶ頁。予想の前でも開く（選ぶ事が予想になる）。出すのは絵と、動く所の候補（部品の呼び名）だけ。"""
    data, src = hypotheses.load(sid), source(sid)
    s = skin.SKINS.get(look, skin.SKINS[skin.DEFAULT])
    root = ";".join(f"--{k}:{v}" for k, v in s.items() if k != "name")
    has_pic = has_picture(sid)
    cands = candidates(data)
    view = view_box(sid, src, cands)
    url = f"background-image:url(/picture/{esc(sid)})"
    # 写しは git の外。無い時は絵の代わりに一文と、国立国会図書館の図への道を出す（玩具の頁と同じ扱い）。
    pic = (f'<div class="fig"><div class="pic" id="pic" tabindex="0" role="img" aria-label="{esc(data["toy"])}の図（指で動かせます）" style="{url};{view_style(src, view)}"></div></div>' if has_pic else
           f'<p class="nopic">図は手元に無い。<a href="{esc(src.get("image_url", ""))}">図を見る（国立国会図書館）</a></p>')
    tools = ('<p class="tools"><label>絵の大きさ<input type="range" id="size" min="50" max="240" value="100" aria-label="絵の大きさ"></label>'
             '<button type="button" id="reset">元の位置へ</button></p>' if has_pic else "")
    msg = f'<p id="msg">{esc(error)}</p>' if error else ""
    if cands and has_pic and view:
        # 候補の絵: 同じ写しの同じ所に、候補の箱だけを枠で示す。札の字は部品の呼び名だけ。送る値は候補の印（仮説の印ではない）。
        items = "".join(f'<button class="cand" name="choice" value="{esc(c["id"])}"><span class="thumb" style="{url};{view_style(src, view)}">'
                        f'<span class="mark" style="{_mark(view, c["box"])}"></span></span><span class="lb">{esc(c["label"])}</span></button>' for c in cands)
        ask = "この絵の、どこが動くと思いますか。近いと思う所を 1 つ押します。"
        form = (f'<form method="post" action="/toy/{esc(sid)}/predict-choice" class="cands">{items}</form>'
                f'<a class="other" href="/toy/{esc(sid)}#yosou">どれでもない（自分の言葉で書く）</a>')
        note = "選ぶと予想として残り、仮説と型紙が開きます。作るのは紙です。作っていて止まった時に聞く口（手帖）は、選んだ後の頁から開けます。"
    elif cands:
        # 写しが手元に無い時は、枠を重ねる絵が無いので、呼び名の札だけで選べるようにする（字だけでも同じ予想が残る）。
        items = "".join(f'<button class="cand" name="choice" value="{esc(c["id"])}"><span class="lb">{esc(c["label"])}</span></button>' for c in cands)
        ask = "この玩具の、どこが動くと思いますか。近いと思う所を 1 つ押します。"
        form = (f'<form method="post" action="/toy/{esc(sid)}/predict-choice" class="cands">{items}</form>'
                f'<a class="other" href="/toy/{esc(sid)}#yosou">どれでもない（自分の言葉で書く）</a>')
        note = "選ぶと予想として残り、仮説と型紙が開きます。作るのは紙です。"
    else:
        # 候補をまだ置いていない玩具（試作）。仮説の動かし方の文は札にしない（予想の前に仮説の中身を出さない）。絵を見て、自分の言葉へ。
        ask = "この絵は、どこがどう動くと思いますか。絵を自分の前に重ねて見て、自分の言葉で予想を書きます。"
        form = f'<a class="other" href="/toy/{esc(sid)}#yosou">自分の言葉で予想を書く</a>'
        note = "この玩具には、選ぶ候補の絵をまだ用意していません。予想を書くと、仮説と型紙が開きます。作るのは紙です。"
    body = (f'<main class="stage"><video id="cam" autoplay playsinline muted aria-hidden="true"></video>'
            f'<p class="top"><a href="/toy/{esc(sid)}">← {esc(data["toy"])}</a><span>かざして選ぶ</span></p>'
            f'{pic}'
            f'<div class="panel">{msg}<p class="q">{ask}</p>'
            f'<p class="state" id="state"><button type="button" id="on">カメラを使う</button>自分の前に絵が浮かんで見えます。{PRIVACY}カメラは使わずに選べます。</p>'
            f'{tools}{form}'
            f'<p class="note">{note}絵は指で動かせます（1 本の指で位置、2 本の指で大きさ）。'
            '絵は国立国会図書館デジタルコレクションの頁（パブリック・ドメイン）。</p></div></main>')
    return (f'<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
            f'<title>{esc(data["toy"])} · かざして選ぶ</title><style>:root{{{root}}}{STYLE}</style>'
            f'<body class="kazasu skin-{esc(look)}">{body}{SCRIPT}{skin.WHO_SCRIPT}</body></html>')


def choose(sid, cid):
    """押した候補を予想として残す。返り値は（選んだ候補 or None、落ちた理由の list）。
    予想の文は「ここが動くと思う: <呼び名>」。仮説の印も名前も入れない（予想は Claude への文脈にも渡るので、答えの形にしない）。
    記録の種類（kind: choice）・選んだ候補の印（choice）・どの道で残したか（via）は、予想の記録の別の欄に置く。
    読み手（toy.py の「あなたの予想」・api/generate.py）は text だけを読むので、今までの予想と同じに扱われる。"""
    data = hypotheses.load(sid)
    # 受けるのは頁に出した候補の印だけ（無い印、候補を置いていない玩具は断る）。
    cand = next((c for c in candidates(data) if c["id"] == cid), None)
    if cand is None:
        return None, ["その候補は無い"]
    path, failures = hypotheses.save_prediction(sid, f"ここが動くと思う: {cand['label']}")
    if failures:
        return None, [f.message for f in failures]
    rec = json.loads(path.read_text(encoding="utf-8"))
    rec.update(kind="choice", choice=cand["id"], via="kazasu")
    path.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return cand, []
