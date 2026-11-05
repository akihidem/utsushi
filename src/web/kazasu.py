"""かざして選ぶ（試作）。本人の案（2026-11-05 朝、窓口を通して届いた）:
「インカメラで見せながら一緒に作る。動かない絵が自分と iPhone の画面の間にあるように映り、どれが良いか選ぶ。実際は紙で作る。
作業で止まったらそのままどうすればいいか聞ける」。

何をする頁か: 文字で予想を書く代わりに、内カメラの自分の映像の上に原図（動かない絵）を重ねて見せ、「どう動くと思うか」を札のタップで選ぶ。
選んだ事が予想として残り、仮説と型紙が開く。作るのは紙で、止まった時に聞く口（手帖）は選んだ後の頁から開ける。
本人が見て決めるための試作で、文字で予想を書く今の道（/toy/<sid> の「先に、予想を書く」）は変えない。

判断の芯:
- **映像は端末の外へ出さない。** 子どもの顔や部屋が映る物を、送らず・録らず・残さない（CLAUDE.md「子どもの写真と声は扱わない」の線）。
  だから canvas に写す・画像にする・録る・網へ送る code を置かない。サーバへ行くのは、押した札の印（フォームの送信）だけ。
  試験（tests/test_kazasu.py）で、頁にその種の JS が無い事を固定する。
- カメラは押した時だけ動かす。頁を開いただけで許可を求めない（何のためか読んでから決められるように）。使わなくても同じ札で選べる。
- 札に出すのは仮説の「動かし方」の文だけ。仮説の名前・字（A・B）・根拠・並びの上下は出さない。名前と根拠は答えの形に見えやすく、
  字は「A が先＝一番」と読まれやすいため（J-025）。並びは記録の並びのままで、毎回同じ。
  ※ 今までの線（F9.prediction: 予想の前は仮説の中身を出さない）からは、動かし方の文を先に見せる分だけ緩む。「選ぶ事が予想」という
    本人の案の芯なので試作ではこうするが、採るかどうかは本人が決める（返事と窓口に書く）。
- 選んだ札を当たりのように扱わない。選んだ後の文は「予想を残しました。紙で確かめます」だけ。
- 見えた時に起こす仕掛け（IntersectionObserver）は置かない。動きは映像の切り替えの薄い移り変わりだけで、prefers-reduced-motion で止める。
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
.fig{position:relative;z-index:1;flex:1 1 auto;min-height:38svh;display:grid;place-items:center;padding:4px 0}
.pic{width:60vw;max-width:420px;max-height:46svh;background:center/contain no-repeat}
/* 紙の地（黄みの強い色）は、色を薄めてから明るさと差を上げて白へ寄せる。色を薄めないと、掛け合わせた時に黄色い面として残る（写しで比べて決めた）。
   線が痩せすぎない所で止め、縁は薄く消して四角い紙の端を見せない。 */
.live .pic{mix-blend-mode:multiply;filter:saturate(.45) contrast(1.8) brightness(1.32);
 -webkit-mask-image:radial-gradient(ellipse at center,#000 58%,transparent 100%);mask-image:radial-gradient(ellipse at center,#000 58%,transparent 100%)}
.nopic{position:relative;z-index:1;flex:1 1 auto;min-height:20svh;display:grid;place-items:center;text-align:center;font-size:13px;color:var(--mute);padding:0 16px}
.panel{position:relative;z-index:2;background:color-mix(in srgb,var(--bg) 86%,transparent);padding:12px 16px 18px;max-height:56svh;overflow:auto;border-top:1px solid var(--rule)}
.q{margin:0 0 8px;font-size:15px}
.state{margin:0 0 10px;font-size:12px;color:var(--mute)}
.state button{font:inherit;font-size:12px;color:var(--accent);background:transparent;border:1px solid var(--accent);padding:6px 12px;margin-right:8px;cursor:pointer}
.choices{display:grid;gap:8px;margin:0}
/* 札は指で押しやすい高さ（44px 以上）。並びは記録の並びで、大きさも色も同じ（上下を付けない）。 */
.choices button,.choices .other{display:block;width:100%;min-height:48px;text-align:left;font:inherit;font-size:15px;line-height:1.5;color:var(--fg);background:var(--paper);
 border:1px solid var(--frame);padding:10px 14px;cursor:pointer;text-decoration:none}
.choices button:hover,.choices button:focus-visible,.choices .other:hover{border-color:var(--accent);outline:none;box-shadow:0 0 0 1px var(--accent) inset}
.choices .other{color:var(--mute)}
.note{margin:10px 0 0;font-size:12px;color:var(--mute)}
#msg{margin:0 0 8px;font-size:13px;color:var(--accent)}
@media (prefers-reduced-motion:reduce){#cam{transition:none}}
"""

# カメラは押した時にだけ求める。映像は <video> に流すだけで、画素を取り出さない（canvas・録画・送信の code を置かない）。
# ?cam=1 を付けて開いた時は、開いた時に求める（確かめの写しを撮るための口。許可の窓はいつもどおり出る）。
# 頁を離れる時はカメラを止める（灯りが点いたままにしない）。
SCRIPT = """<script>(()=>{const v=document.getElementById('cam'),b=document.getElementById('on'),s=document.getElementById('state');
const off='カメラは使わずに選べます。';
if(!navigator.mediaDevices||!navigator.mediaDevices.getUserMedia){s.textContent='この機器ではカメラを使えません。'+off;return}
const start=async()=>{try{const st=await navigator.mediaDevices.getUserMedia({video:{facingMode:'user'},audio:false});
v.srcObject=st;document.body.classList.add('live');s.textContent='%s'}catch(e){s.textContent='カメラを使えませんでした。'+off}};
b.addEventListener('click',start);
if(new URLSearchParams(location.search).get('cam')==='1')start();
addEventListener('pagehide',()=>{const st=v.srcObject;if(st)st.getTracks().forEach(t=>t.stop())});
})()</script>""" % PRIVACY


@functools.lru_cache(maxsize=1)
def _inventory():
    path = ROOT / "data/inventory/edo-nishiki.json"
    return {t["id"]: t for t in json.loads(path.read_text(encoding="utf-8"))["toys"]} if path.exists() else {}


def _pct(region):
    return [float(v) for v in region[4:].split(",")]


def _fit(sid, src):
    """絵の敷き方。写しが半頁の玩具（必須の 2 種）は、頁の周りの黒い地と歌の字まで入っているので、棚卸しの箱（玩具の所）だけを見せる。
    なぜ: 映像に掛け合わせると、黒い地は黒い枠としてそのまま残り、自分の顔が隠れる。切り出しの写し（試作の玩具）はそのまま収める。
    箱は見開きに対する百分率なので、半頁の写しの中の位置に直してから、背景の大きさと位置で切り出す（画像は作り直さない）。"""
    toy = _inventory().get(sid)
    sx, sy, sw, sh = _pct(src.get("crop_region", "pct:0,0,100,100"))
    if not toy or (sw, sh) != (50.0, 100.0):
        return "aspect-ratio:1/1;background-size:contain"
    x, y, w, h = _pct(toy["region"])
    fx, fy, fw, fh = (x - sx) / sw, (y - sy) / sh, w / sw, h / sh
    if not (0 <= fx and fx + fw <= 1 and 0 <= fy and fy + fh <= 1) or fw >= 1 or fh >= 1:
        return "aspect-ratio:1/1;background-size:contain"
    # 見開きの写しは横 1600 に対して縦 1328 の比（research/26）。箱の縦横比を枠の比にする。
    ratio = (w * 1600) / (h * 1328)
    return (f"aspect-ratio:{ratio:.3f};background-size:{100 / fw:.1f}% {100 / fh:.1f}%;"
            f"background-position:{100 * fx / (1 - fw):.1f}% {100 * fy / (1 - fh):.1f}%")


def cards(data):
    """札の一覧: (送る仮説の印, 札の文, 同じ文の仮説の印の一覧)。
    - 札の文は動かし方の文。文の中に仮説の印（H-C など）が出る一文は落とす（「型紙は H-C と同じ」のような作る側の注で、字を出さない線に触れるため）。
    - 動かし方の文が同じ仮説（作りは違うが、する事は同じ）は 1 枚にまとめる。同じ文の札が 2 枚あっても選び分けられないため。
      送る印は並びの最初の仮説で、同じ文だった仮説は記録に残す（choose の same_action）。"""
    import re

    out, seen = [], {}
    for h in data["hypotheses"]:
        text = "。".join(x for x in h["how_it_moves"].split("。") if x.strip() and not re.search(r"H-[A-Z0-9]", x)).strip() or h["how_it_moves"]
        if text in seen:
            out[seen[text]][2].append(h["id"])
            continue
        seen[text] = len(out)
        out.append((h["id"], text, [h["id"]]))
    return out


def page(sid, look=skin.DEFAULT, error=""):
    """かざして選ぶ頁。予想の前でも開く（選ぶ事が予想になる）。札は仮説の動かし方の文だけ。"""
    data, src = hypotheses.load(sid), source(sid)
    s = skin.SKINS.get(look, skin.SKINS[skin.DEFAULT])
    root = ";".join(f"--{k}:{v}" for k, v in s.items() if k != "name")
    has_pic = (ROOT / "out/sources" / f"{sid}.jpg").exists()
    # 写しは git の外。無い時は絵の代わりに一文と、国立国会図書館の図への道を出す（玩具の頁と同じ扱い）。
    pic = (f'<div class="fig"><div class="pic" role="img" aria-label="{esc(data["toy"])}の図" style="background-image:url(/picture/{esc(sid)});{_fit(sid, src)}"></div></div>' if has_pic else
           f'<p class="nopic">図は手元に無い。<a href="{esc(src.get("image_url", ""))}">図を見る（国立国会図書館）</a></p>')
    # 札: 動かし方の文だけ。名前・字・根拠は出さない。並びは記録の並び。送る値は仮説の印（画面には出ない）。
    buttons = "".join(f'<button name="hypothesis" value="{esc(hid)}">{esc(text)}</button>' for hid, text, _ in cards(data))
    msg = f'<p id="msg">{esc(error)}</p>' if error else ""
    body = (f'<main class="stage"><video id="cam" autoplay playsinline muted aria-hidden="true"></video>'
            f'<p class="top"><a href="/toy/{esc(sid)}">← {esc(data["toy"])}</a><span>かざして選ぶ（試作）</span></p>'
            f'{pic}'
            f'<div class="panel">{msg}<p class="q">この絵は、どう動くと思いますか。近いと思う物を 1 つ押します。</p>'
            f'<p class="state" id="state"><button type="button" id="on">カメラを使う</button>自分の前に絵が浮かんで見えます。{PRIVACY}カメラは使わずに選べます。</p>'
            f'<form method="post" action="/toy/{esc(sid)}/predict-choice" class="choices">{buttons}'
            f'<a class="other" href="/toy/{esc(sid)}#yosou">どれでもない（自分の言葉で書く）</a></form>'
            '<p class="note">選ぶと予想として残り、仮説と型紙が開きます。作るのは紙です。作っていて止まった時に聞く口（手帖）は、選んだ後の頁から開けます。'
            '絵は国立国会図書館デジタルコレクションの頁（パブリック・ドメイン）。</p></div></main>')
    return (f'<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
            f'<title>{esc(data["toy"])} · かざして選ぶ</title><style>:root{{{root}}}{STYLE}</style>'
            f'<body class="kazasu skin-{esc(look)}">{body}{SCRIPT}</body></html>')


def choose(sid, hid):
    """押した札を予想として残す。返り値は（選んだ仮説 or None、落ちた理由の list）。
    予想の文には動かし方の文だけを入れ、仮説の印は入れない（予想は Claude への文脈にも渡るので、印で答えの形にしない）。
    どの道で残した予想か（via）と選んだ印（choice）は、予想の記録の別の欄に置く。読み手（toy.py・api/generate.py）は text だけを読むので壊れない。"""
    data = hypotheses.load(sid)
    # 受けるのは頁に出した札の印だけ（まとめられて札にならなかった仮説の印や、無い印は断る）。
    card = next((c for c in cards(data) if c[0] == hid), None)
    if card is None:
        return None, ["その札は無い"]
    h = next(x for x in data["hypotheses"] if x["id"] == hid)
    path, failures = hypotheses.save_prediction(sid, f"かざして選んだ: {card[1]}")
    if failures:
        return None, [f.message for f in failures]
    rec = json.loads(path.read_text(encoding="utf-8"))
    rec.update(via="kazasu", choice=hid)
    if len(card[2]) > 1:
        # 動かし方の文が同じ仮説をまとめた札。どの仮説を選んだとも言えないので、同じ文だった印を全部残す。
        rec["same_action"] = card[2]
    path.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return h, []
