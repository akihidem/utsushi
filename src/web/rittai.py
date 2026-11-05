"""できあがりの形を立体で見る試し（本人の決定 2026-11-05、#331）。

本人の決定: スマホの前のカメラで顔の動きを追い、できあがりの形の絵が一緒に動いて立体に見える形を、頁で小さく試す。
ねらいは、平らな紙から立体の形を思い浮かべる助け（試しで最初の一歩で手が止まった所への手当て）。

判断の芯:
- カメラの映像はこの機械の中だけで使う。送る code も残す code も書かない（tests/test_rittai.py が文字列を見る）。音は取らない。映像は画面に出さない。
  顔と声を残さない線（J-022）に合わせるため。カメラは押した時だけ動かす。
- 依存を足さない。顔の向きを推定する既製の部品は外の網から大きなファイルを読むので、学校の網で止まる見込みがある。
  試しなので、映像を小さく縮めて肌の色の画素の重心を見るだけにした。動き始めの位置からのずれしか使わないので、絵を動かす分には足りる見込み。
  本物の顔と本物のスマホでは確かめていない（作る側の機械にカメラが無い）。
- 絵は雛形の寸法から CSS の立体で組む。紙の型紙とは別のだいたいの形なので、頁にそう書く。紙の指紋には触らない。
- カメラが使えない時も指で動かせる。動かすのは見る人だけで、開いただけでは動かない（北斎漫画の節と同じ）。
"""
import math

from omochae import hypotheses
from omochae.compose import TEMPLATES

from . import skin
from .skin import esc

G = "NDL-1187053-R0000005-L"
MODELS = {G}
SCALE = 3  # 1mm を何 px で描くか。スマホの幅に扇（半径 48mm）が収まる大きさ
LEAD = "できあがりの形です。顔を動かすと、形も一緒に動いて、立体に見えます。"
START = "カメラで動かす"
STOP = "カメラを止める"
NOTE_CAMERA = "カメラの映像は、この機械の中だけで使います。どこにも送りません。残しません。顔は画面に出しません。"
NOTE_FINGER = "カメラを使わない時は、指で絵を動かせます。"
NOTE_SHAPE = "これは、形を思い浮かべるための、だいたいの絵です。作る時は型紙と手順の紙を見てください。"
NO_CAMERA = "この機械では、カメラを使えませんでした。指で絵を動かせます。"
LOST = "顔が見つかりません。カメラの前に顔を入れてください。"

STYLE = """
.rt-stage{position:relative;margin:18px auto 0;width:min(100%,420px);height:580px;perspective:900px;touch-action:none;cursor:grab;overflow:hidden;border:1px solid var(--frame);background:var(--paper)}
.rt-scene{position:absolute;left:50%;bottom:58px;width:0;height:0;transform-style:preserve-3d;transform:rotateX(var(--rx,-8deg)) rotateY(var(--ry,-24deg))}
.rt-scene *{transform-style:preserve-3d}
.rt-face{position:absolute;box-sizing:border-box;border:2px solid var(--fg);background:var(--soft);backface-visibility:visible}
.rt-face.alt{background:var(--paper)}
.rt-slot{position:absolute;left:50%;top:18%;bottom:6%;width:2px;margin-left:-1px;background:var(--fg)}
.rt-knob{position:absolute;box-sizing:border-box;border:2px solid var(--fg);background:var(--accent)}
.rt-pleat{position:absolute;overflow:visible}
.rt-pleat polygon{stroke:var(--fg);stroke-width:1.5;stroke-linejoin:round}
.rt-pleat.a polygon{fill:var(--paper)}
.rt-pleat.b polygon{fill:var(--soft)}
.rt-figure{position:absolute;box-sizing:border-box;background:var(--accent);border:2px solid var(--fg);border-radius:48% 48% 8% 8%}
.rt-acts{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-top:6px}
.rt-acts [hidden]{display:none}
#rt-video{position:absolute;width:1px;height:1px;opacity:0;pointer-events:none}
#rt-canvas{display:none}
"""

# カメラの映像はここで小さく縮めて読むだけ。外へ出す口を持たない。
SCRIPT = """
<script>(()=>{
const scene=document.getElementById('rt-scene'),stage=document.getElementById('rt-stage'),go=document.getElementById('rt-go'),stop=document.getElementById('rt-stop'),note=document.getElementById('rt-note'),video=document.getElementById('rt-video'),canvas=document.getElementById('rt-canvas');
const YAW=30,PITCH=16,REACH=0.2,SKIN_MIN=0.015;
let rx=-8,ry=-24,stream=null,base=null,seen=0,sx=0,sy=0,timer=0;
const put=()=>{scene.style.setProperty('--rx',rx.toFixed(2)+'deg');scene.style.setProperty('--ry',ry.toFixed(2)+'deg');stage.dataset.rx=rx.toFixed(2);stage.dataset.ry=ry.toFixed(2)};
const clamp=(v,a)=>Math.max(-a,Math.min(a,v));
put();
// 指で動かす
let drag=null;
stage.addEventListener('pointerdown',e=>{drag=[e.clientX,e.clientY,rx,ry];stage.setPointerCapture(e.pointerId)});
stage.addEventListener('pointermove',e=>{if(!drag)return;ry=clamp(drag[3]+(e.clientX-drag[0])*.4,60);rx=clamp(drag[2]-(e.clientY-drag[1])*.25,35);put()});
stage.addEventListener('pointerup',()=>{drag=null});
stage.addEventListener('pointercancel',()=>{drag=null});
// 肌の色の画素の重心。Returns [x,y,割合]（0〜1）
const ctx=canvas.getContext('2d',{willReadFrequently:true});
const centroid=()=>{const w=canvas.width,h=canvas.height;ctx.drawImage(video,0,0,w,h);const d=ctx.getImageData(0,0,w,h).data;let n=0,ax=0,ay=0;
for(let y=0,i=0;y<h;y++)for(let x=0;x<w;x++,i+=4){const r=d[i],g=d[i+1],b=d[i+2],l=.299*r+.587*g+.114*b,cb=128-.169*r-.331*g+.5*b,cr=128+.5*r-.419*g-.081*b;
if(l>45&&cr>135&&cr<182&&cb>80&&cb<135){n++;ax+=x;ay+=y}}
return n?[ax/n/w,ay/n/h,n/(w*h)]:[0,0,0]};
const tick=()=>{if(!stream)return;if(video.readyState>=2){const [x,y,f]=centroid();
if(f<SKIN_MIN){note.textContent=note.dataset.lost}else{note.textContent='';
if(seen<10){sx+=x;sy+=y;seen++;if(seen===10)base=[sx/10,sy/10]}
else{// 前のカメラの絵は左右が鏡。見る人が自分の右へ動くと、絵の x は小さくなる。動いた側の面が見える向きへ回す。
const tx=clamp((x-base[0])/REACH,1),ty=clamp((y-base[1])/REACH,1);ry+=(-24+tx*YAW-ry)*.25;rx+=(-8+ty*PITCH-rx)*.25;put()}}}
timer=setTimeout(tick,66)};
const end=()=>{clearTimeout(timer);if(stream){stream.getTracks().forEach(t=>t.stop());stream=null}video.srcObject=null;base=null;seen=0;sx=0;sy=0;stop.hidden=true;go.hidden=false};
if(!navigator.mediaDevices||!navigator.mediaDevices.getUserMedia){go.hidden=true;note.textContent=note.dataset.none}
go.addEventListener('click',async()=>{try{stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:'user',width:{ideal:320},height:{ideal:240}},audio:false});
video.srcObject=stream;await video.play();go.hidden=true;stop.hidden=false;note.textContent='';tick()}catch(e){end();note.textContent=note.dataset.none}});
stop.addEventListener('click',()=>{end();note.textContent=''});
addEventListener('pagehide',end);
document.addEventListener('visibilitychange',()=>{if(document.hidden)end()});
})();</script>
"""


def _face(w, h, transform, cls="", inner=""):
    return f'<div class="rt-face {cls}" style="left:{-w / 2:.1f}px;bottom:0;width:{w:.1f}px;height:{h:.1f}px;transform:{transform}">{inner}</div>'


def _fan(p):
    """蛇腹の扇。要（かなめ）から半円に開く。山と谷を交互に傾けて、折った紙に見せる。"""
    r, count = p["fold_height"] * SCALE, int(p["fold_count"])
    hub = (p["tube_height"] + p["pivot_above_rim"]) * SCALE
    step = 180 / count
    half = r * math.tan(math.radians(step / 2))
    out = ""
    for i in range(count):
        angle = -90 + step * (i + .5)
        tilt = 28 if i % 2 else -28
        cls = "a" if i % 2 else "b"
        out += (f'<svg class="rt-pleat {cls}" viewBox="0 0 {2 * half:.1f} {r:.1f}" width="{2 * half:.1f}" height="{r:.1f}" '
                f'style="left:{-half:.1f}px;bottom:{hub:.1f}px;transform-origin:50% 100%;transform:rotateZ({angle:.2f}deg) rotateY({tilt}deg)">'
                f'<polygon points="{half:.1f},{r:.1f} 0,0 {2 * half:.1f},0"/></svg>')
    return out


def _model(p):
    """筒・つまみ・扇・像。寸法は雛形の値。"""
    side, tall = p["tube_side"] * SCALE, p["tube_height"] * SCALE
    half = side / 2
    faces = (_face(side, tall, f"translateZ({half:.1f}px)", inner='<span class="rt-slot"></span>')
             + _face(side, tall, f"rotateY(90deg) translateZ({half:.1f}px)", "alt")
             + _face(side, tall, f"rotateY(180deg) translateZ({half:.1f}px)")
             + _face(side, tall, f"rotateY(-90deg) translateZ({half:.1f}px)", "alt"))
    knob_w, knob_h = p["knob_width"] * SCALE, 18
    knob = (f'<div class="rt-knob" style="left:{-knob_w / 2:.1f}px;bottom:{tall * .55:.1f}px;width:{knob_w:.1f}px;height:{knob_h}px;'
            f'transform:translateZ({half + 10:.1f}px)"></div>')
    fig_w, fig_h = p["figure_w"] * SCALE, p["figure_h"] * SCALE
    hub = (p["tube_height"] + p["pivot_above_rim"]) * SCALE
    figure = (f'<div class="rt-figure" style="left:{-fig_w / 2:.1f}px;bottom:{hub:.1f}px;width:{fig_w:.1f}px;height:{fig_h:.1f}px;'
              f'transform:translateZ(14px)"></div>')
    # 芯: 筒の口から要まで、押し上げた内筒が見える。無いと扇が筒から浮いて見える。
    core_side, core_tall = p["pusher_side"] * SCALE, hub - tall + 4
    core_half = core_side / 2
    core = "".join(f'<div class="rt-face{" alt" if i % 2 else ""}" style="left:{-core_side / 2:.1f}px;bottom:{tall - 2:.1f}px;width:{core_side:.1f}px;height:{core_tall:.1f}px;'
                   f'transform:rotateY({i * 90}deg) translateZ({core_half:.1f}px)"></div>' for i in range(4))
    return faces + knob + core + _fan(p) + figure


def params(sid):
    """出す 1 枚の寸法。今は元の並びの先頭（型紙を 1 つにする決定 #328 の既定と同じ）。"""
    data = hypotheses.load(sid)
    h = data["hypotheses"][0]
    tpl = TEMPLATES[h.get("template") or data.get("template", "slider_fan")]
    return data, {**tpl.DEFAULTS, **(h.get("params") or {})}


def link(sid):
    """玩具の頁に置く道。試しの玩具にだけ出す。"""
    return f'<p class="links"><a href="/toy/{esc(sid)}/rittai">できあがりの形を立体で見る</a></p>' if sid in MODELS else ""


def page(sid, look=skin.DEFAULT, path=None):
    data, p = params(sid)
    body = (f'<section class="sec"><h1>{esc(data["toy"])}: 立体で見る</h1><p class="lead">{esc(LEAD)}</p>'
            f'<div class="rt-stage" id="rt-stage" role="img" aria-label="できあがりの形の絵。指かカメラで向きを変えられます。"><div class="rt-scene" id="rt-scene">{_model(p)}</div></div>'
            f'<div class="rt-acts"><button type="button" id="rt-go">{esc(START)}</button><button type="button" class="quiet" id="rt-stop" hidden>{esc(STOP)}</button></div>'
            f'<p class="meta" id="rt-note" aria-live="polite" data-none="{esc(NO_CAMERA)}" data-lost="{esc(LOST)}"></p>'
            f'<p class="meta">{esc(NOTE_CAMERA)}{esc(NOTE_FINGER)}</p><p class="meta">{esc(NOTE_SHAPE)}</p>'
            f'<p class="links"><a href="/toy/{esc(sid)}">{esc(data["toy"])}の頁へもどる</a></p>'
            '<video id="rt-video" muted playsinline aria-hidden="true"></video><canvas id="rt-canvas" width="64" height="48"></canvas>'
            f'</section>{SCRIPT}')
    return skin.shell(f'{data["toy"]}: 立体で見る', body, look, path=path or f"/toy/{sid}/rittai", extra_style=STYLE)
