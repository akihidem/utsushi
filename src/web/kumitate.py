"""手順どおりに組み立てる様子を立体で見る頁（本人の決定 2026-11-05、#331）。

本人の言葉: 「型紙のときにAIイメージ図をやはり3Dで」「手順をAIが3Dで組み立てて、その過程を手順書にする」
「実際の手順に沿って、見え方や動きを再現する必要があります」。
形は omochae.assembly が雛形の部品と手順の文から作る。完成図を別に描かない。見え方は刷った紙のとおりにする（render の描き方と同じ）。

判断の芯:
- 外の部品を読まない。CSS の立体だけで動かす（学校の網で止まらない）。
- 開いただけで動かし始めない。手順を送るのも回すのも見る人（認知負荷を減らす。静かに）。
- 折る所は、面を折り線のまわりに本当に回して描く。面と面は途中でも離れない。行列どうしの補間は面が離れるので使わない。
  形は Python が決め、頁は角の途中を計算するだけにする。
- 組み立ての最後に、つまみを上へ動かして扇が開く所まで見せる（本人の追加 11-06）。前の線「閉じた形と開いた形だけ」を本人が変えた。
"""
import functools
import json
import math
import re

from shapely.geometry import LineString, Point, Polygon

from omochae import assembly, hypotheses, render
from omochae.model import ToolMissing

from . import skin
from .skin import esc

SCALE = 4.0  # 1mm を何 px で描くか（要素の大きさ。見た目の大きさは場面の縮尺で決める。小さいと立体の時に絵が粗くなる）
STAGE_W, STAGE_H = 340, 480  # 図を収める大きさ（px）
LEAD = "手順どおりに組み立てます。指で回して見られます。"
NOTE_SHAPE = "これは、形を思い浮かべるための、だいたいの絵です。作る時は型紙と手順の紙を見てください。"
PREV, NEXT = "前へ", "次へ"
RESTART = "はじめから組み立てる"
DONE = "できあがり"
LABEL = "組み立てを立体で見る"

STYLE = """
.rt-stage{--rt-table:#ece6d8;position:relative;margin:18px auto 0;width:min(100%,420px);height:520px;perspective:1100px;touch-action:pan-y;cursor:grab;overflow:hidden;border:1px solid var(--frame);background:var(--rt-table)}
@supports (color:color-mix(in srgb,red,blue)){.rt-stage{--rt-table:color-mix(in srgb,var(--paper) 86%,#8a7a5c)}}
.rt-scene{position:absolute;left:50%;top:50%;width:0;height:0;transform-style:preserve-3d}
.rt-p{position:absolute;left:0;top:0;transform-origin:0 0;backface-visibility:hidden;-webkit-backface-visibility:hidden;transition:opacity .4s ease;overflow:visible}
.rt-rod{position:absolute;left:0;top:0;transform-origin:0 0;transition:opacity .4s ease;opacity:0}
.rt-axle{height:8px;margin-top:-4px;background:#8a6a3a}
.rt-thread{height:2.4px;margin-top:-1.2px;background:#7a2f2a}
.rt-paper,.rt-ruler,.rt-sci{position:absolute;left:0;top:0;transform-origin:0 0;transition:opacity .4s ease;opacity:0}
.rt-hole{fill:var(--rt-table)}
.rt-scrap,.rt-plug{transition:opacity .4s ease}
.rt-acts{display:flex;gap:10px;align-items:center;margin-top:10px}
.rt-acts [disabled]{opacity:.4}
.rt-acts [hidden]{display:none}
#rt-count{font-size:14px;color:var(--mute);margin-left:auto}
#rt-text{min-height:3.4em;margin:10px 0 0;line-height:1.8}
"""


def _css(m):
    """行列を CSS の matrix3d の 16 個にする（列の順）。平行移動は px にする。"""
    return [round(m[r][c] * (SCALE if r < 3 and c == 3 else 1), 3) for c in range(4) for r in range(4)]


def _path(shape, x0, y0, flip=None):
    """面の形の path。面の中の穴（前の壁の四角）も線にする。"""
    rings = [shape.exterior, *shape.interiors]
    return " ".join("M" + " L".join(f"{(flip - x if flip is not None else x - x0):.2f} {y - y0:.2f}" for x, y in ring.coords) + "Z" for ring in rings)


def _art(part, x0, y0):
    out = ""
    for item in part.art:
        pts = " ".join(f"{x - x0:.2f},{y - y0:.2f}" for x, y in item["pts"])
        if item["kind"] == "poly":
            stroke = f' stroke="{item["stroke"]}" stroke-width="{item.get("sw", .3)}"' if item.get("stroke") else ""
            out += f'<polygon points="{pts}" fill="{item["fill"]}"{stroke}/>'
        elif item["kind"] == "mark":
            # 位置の印（次の組の虎の腕の丸・御来迎の溝の矢印）。刷る紙と同じ色と点で描く（render.MARK_*）
            tag = "polygon" if item.get("closed") else "polyline"
            out += (f'<{tag} points="{pts}" fill="none" stroke="{render.MARK_COLOR}" stroke-width="{render.MARK_SW}" stroke-dasharray="{render.MARK_DASH}"'
                    ' stroke-linecap="round"/>')
        else:
            out += f'<polyline points="{pts}" fill="none" stroke="{item["stroke"]}" stroke-width="{item.get("sw", .3)}"/>'
    return out


def _hatch(glue, x0, y0):
    """糊代の斜線。刷った紙と同じ間隔（render._hatch）。"""
    poly = Polygon(glue)
    a, b, c, d = poly.bounds
    span = max(c - a, d - b)
    out, v = "", a - span
    while v < c:
        seg = poly.intersection(LineString([(v, d), (v + span, d - span)]))
        for g in getattr(seg, "geoms", [seg]):
            if not g.is_empty and g.geom_type == "LineString":
                (p, q), (r, s) = g.coords[0], g.coords[-1]
                out += f'<line x1="{p - x0:.2f}" y1="{q - y0:.2f}" x2="{r - x0:.2f}" y2="{s - y0:.2f}" stroke="#888" stroke-width=".12"/>'
        v += 1.6
    return out


def _marks(part, x0, y0, near):
    """紙に刷ってある線と印。糊代の斜線・折り線（色の境で折る部品は刷らない）・穴・番号。"""
    out = "".join(_hatch(g, x0, y0) for g in part.glue)
    if not part.hide_folds:
        for lines, dash in ((part.valley, render.VALLEY), (part.mountain, render.MOUNTAIN)):
            for (x1, y1), (x2, y2) in lines:
                out += f'<line x1="{x1 - x0:.2f}" y1="{y1 - y0:.2f}" x2="{x2 - x0:.2f}" y2="{y2 - y0:.2f}" stroke="#222" stroke-width=".18" stroke-dasharray="{dash}"/>'
    out += "".join(f'<circle cx="{x - x0:.2f}" cy="{y - y0:.2f}" r="{r:.2f}" fill="#fffdf8" stroke="#55492c" stroke-width=".2"/>'
                   for x, y, r in part.holes if near.contains(Point(x, y)))
    lx, ly = part.label_xy
    if part.label and near.contains(Point(lx, ly)):
        out += f'<text x="{lx - x0:.2f}" y="{ly - y0 + 2.6:.2f}" font-size="2.8" fill="#3a2c12">{esc(part.label)}</text>'
    return out


def _panel_html(key, i, sheet):
    """面 1 枚の表と裏。表は紙の絵と線と番号と穴を面の形で切り抜く。裏は無地。"""
    part = sheet.part
    s = sheet.panels[i]
    x0, y0, x1, y1 = s.bounds
    w, h = x1 - x0, y1 - y0
    pid = f"{key}-{i}"
    shape = _path(s, x0, y0)
    box = f'width="{w * SCALE:.1f}" height="{h * SCALE:.1f}" viewBox="0 0 {w:.2f} {h:.2f}"'
    data = f'class="rt-p" data-p="{key}:{i}" data-x="{x0:.3f}" data-y="{y0:.3f}"'
    shade = '<path class="rt-s" d="{}" fill-rule="evenodd" fill="#2b2110" fill-opacity="0"/>'
    near = s.buffer(1e-3)
    front_plug, back_plug = "", ""
    for cx, cy, cw, ch in part.cuts:  # 中を切る四角は、切るまで面についている
        if near.contains(Point(cx + cw / 2, cy + ch / 2).buffer(1e-3)) or s.distance(Point(cx, cy)) < 1e-3:
            ground = next((item["fill"] for item in part.art if item["kind"] == "poly" and Polygon(item["pts"]).contains(Point(cx + cw / 2, cy + ch / 2))), "#fffdf8")
            front_plug += f'<rect class="rt-plug" x="{cx - x0:.2f}" y="{cy - y0:.2f}" width="{cw}" height="{ch}" fill="{ground}" stroke="#222" stroke-width=".25"/>'
            back_plug += f'<rect class="rt-plug" x="{x1 - cx - cw:.2f}" y="{cy - y0:.2f}" width="{cw}" height="{ch}" fill="#f3ecdc"/>'
    front = (f'<svg {data} {box}><defs><clipPath id="c{pid}"><path d="{shape}" clip-rule="evenodd"/></clipPath></defs>'
             f'<path d="{shape}" fill-rule="evenodd" fill="#fffdf8" stroke="#55492c" stroke-width=".3"/>'
             f'<g clip-path="url(#c{pid})">{_art(part, x0, y0)}{_marks(part, x0, y0, near)}</g>{front_plug}{shade.format(shape)}</svg>')
    mirror = _path(s, x0, y0, flip=x1)
    back = (f'<svg {data} data-back="{w:.3f}" {box}><path d="{mirror}" fill-rule="evenodd" fill="#f3ecdc" stroke="#55492c" stroke-width=".3"/>'
            f'{back_plug}{shade.format(mirror)}</svg>')
    return front + back


def paper_html(layout):
    """刷った紙。部品のほか（題・用意する物・凡例・物差し）を刷った紙のとおりに描き、部品の所は切り抜いた穴にする。部品はこの上に別に置く。"""
    page = layout["page"]
    svg = re.sub(r"^<\?xml.*?\?>\s*", "", render.to_svg({**layout, "parts": []}), flags=re.S)
    holes, scrap = "", ""
    for q in layout["parts"]:
        pts = " ".join(f"{q.x + x:.2f},{q.y + y:.2f}" for x, y in q.outline)
        holes += f'<polygon class="rt-hole" points="{pts}"/>'
        # 溝の切り落とす所は、切るまで紙についている
        if q.key == "tube":
            xs = sorted({x for x, y in q.outline if y == q.height})
            if len(xs) >= 4:
                y0 = min(y for x, y in q.outline if xs[1] <= x <= xs[2] and 0 < y < q.height)
                box = [(xs[1], y0), (xs[2], y0), (xs[2], q.height), (xs[1], q.height)]
                area = " ".join(f"{q.x + x:.2f},{q.y + y:.2f}" for x, y in box)
                inside = _art_at(q)
                scrap = (f'<g class="rt-scrap"><defs><clipPath id="rt-slot"><polygon points="{area}"/></clipPath></defs>'
                         f'<polygon points="{area}" fill="#fffdf8"/><g clip-path="url(#rt-slot)">{inside}</g></g>')
    head, _, rest = svg.partition(">")
    head = re.sub(r'\s(width|height)="[^"]*"', "", head)
    size = f' width="{page.w * SCALE:.0f}" height="{page.h * SCALE:.0f}" class="rt-paper" id="rt-paper" style="transform:translate3d({-page.w / 2 * SCALE:.1f}px,{-page.h / 2 * SCALE:.1f}px,-2px)"'
    return head + size + ">" + rest.replace("</svg>", holes + scrap + "</svg>")


def _art_at(q):
    """部品の絵を、紙の上の位置で描く。"""
    return _art(q, -q.x, -q.y)


def ruler_html():
    """定規。0 の目盛りは左の端から assembly.RULER_ZERO の所。"""
    z = assembly.RULER_ZERO
    ticks = ""
    for i in range(0, 101):
        tall = 5.5 if i % 10 == 0 else 3.8 if i % 5 == 0 else 2.4
        ticks += f'<line x1="{z + i}" y1="0" x2="{z + i}" y2="{tall}" stroke="#3a2c12" stroke-width="{.2 if i % 10 == 0 else .12}"/>'
    nums = "".join(f'<text x="{z + i}" y="9.5" font-size="3" text-anchor="middle" fill="#3a2c12">{i // 10}</text>' for i in range(0, 101, 10))
    return (f'<svg class="rt-ruler" id="rt-ruler" width="{108 * SCALE:.0f}" height="{15 * SCALE:.0f}" viewBox="0 0 108 15">'
            f'<rect width="108" height="15" rx=".6" fill="#efe3c4" fill-opacity=".94" stroke="#8a7a5c" stroke-width=".25"/>{ticks}{nums}</svg>')


SCISSORS = ('<svg class="rt-sci" id="rt-sci" width="{w:.0f}" height="{h:.0f}" viewBox="-30 -14 46 28">'
            '<g fill="none" stroke="#7a2f2a" stroke-width="2"><circle cx="-23" cy="-7" r="5"/><circle cx="-23" cy="7" r="5"/></g>'
            '<g stroke="#55565a" stroke-width="1.8" stroke-linecap="round"><line x1="-18.5" y1="-5" x2="14" y2="3.4"/><line x1="-18.5" y1="5" x2="14" y2="-3.4"/></g></svg>')


KNIFE = ('<svg class="rt-sci" id="rt-knife" width="{w:.0f}" height="{h:.0f}" viewBox="-30 -14 46 28">'
         '<polygon points="0,0 -9,-2.2 -9,1.2" fill="#9a9ca0" stroke="#55565a" stroke-width=".3"/><rect x="-30" y="-3" width="21" height="4.6" rx="1" fill="#7a2f2a"/></svg>')


def _px(p):
    return [round(x * SCALE, 2) for x in p]


def trees_of(bench):
    """面のつながり。面 → [親の面, 折り線の点 x, y, 線の向き x, y, 根からの枚数]。長さは px。"""
    out = {}
    for key, sheet in bench.sheets.items():
        rows = {}
        for i in sheet.tree:
            (x, y, _), (ax, ay, _) = sheet.hinge(i)
            rows[i] = [sheet.tree[i][0], round(x * SCALE, 3), round(y * SCALE, 3), round(ax, 4), round(ay, 4), sheet.depth(i)]
        out[key] = {"root": sheet.root, "rows": rows}
    return out


def _fit(pts, view):
    """向きの通りに見た時に舞台へ収まる縮尺と中心。"""
    lo = [min(p[k] for p in pts) for k in range(3)]
    hi = [max(p[k] for p in pts) for k in range(3)]
    center = [(a + b) / 2 for a, b in zip(lo, hi)]
    rx, ry = math.radians(view.get("rx", -10)), math.radians(view.get("ry", -20))
    far_x = far_y = 1.0
    for p in pts:
        x, y, z = (p[k] - center[k] for k in range(3))
        x, z = x * math.cos(ry) + z * math.sin(ry), -x * math.sin(ry) + z * math.cos(ry)
        y = y * math.cos(rx) - z * math.sin(rx)
        far_x, far_y = max(far_x, abs(x)), max(far_y, abs(y))
    return center, min(STAGE_W / 2 / far_x, STAGE_H / 2 / far_y, 4.0) * 0.92 / SCALE


def _pose(bench, pose, whole):
    """途中の形 1 つを、頁へ渡す形にする。whole は面を直に置いた形（できあがり）で、行列をそのまま渡す。"""
    pts, panels = [], {}
    focus = pose.get("focus")
    for pid, m in pose["panels"].items():
        if m is None:
            continue
        key, i = pid.split(":")
        panels[pid] = _css(m)
        if not focus or key in focus:
            pts += [assembly.apply(m, p) for p in bench.sheets[key].panels[int(i)].exterior.coords]
    if not focus:
        for s, e, _ in pose["extras"].values():
            pts += [s, e]
        if pose["paper"] and bench.paper:
            w, h = bench.paper["page"].w / 2, bench.paper["page"].h / 2
            pts += [(-w, -h, 0), (w, -h, 0), (w, h, 0), (-w, h, 0)]
    center, zoom = _fit(pts, pose["view"])
    out = {"rx": pose["view"].get("rx", -10), "ry": pose["view"].get("ry", -20), "c": [round(c * SCALE, 1) for c in center], "z": round(zoom, 3),
           "r": {name: {"s": _px(s), "e": _px(e)} for name, (s, e, owner) in pose["extras"].items() if f"{owner}:0" in panels},
           "s": {key: {"m": _css(st["place"]), "a": {str(i): round(d, 3) for i, d in st["turns"].items()}, "n": {str(i): round(d * SCALE, 3) for i, d in st["nudge"].items()}}
                 for key, st in pose["state"].items()},
           "paper": 1 if pose["paper"] else 0, "scrap": 1 if pose["scrap"] else 0, "plug": 1 if pose["plug"] else 0}
    for name in ("dur", "cam", "knife"):
        if pose.get(name) is not None:
            out[name] = pose[name]
    if pose.get("ruler"):
        out["ruler"] = _px(pose["ruler"])
    if pose.get("cut"):
        out["cut"] = [_px(p) for p in pose["cut"]]
    if pose.get("order"):
        out["o"] = pose["order"]
    if pose.get("open"):
        o = pose["open"]
        out["open"] = {"h0": _px(o["hub0"]), "h1": _px(o["hub1"]), "rim": o["rim"] * SCALE, "mouth": o["mouth"] * SCALE, "half": o["spread"] / 2, "each": o["each"], "closed": o["closed"], "tilt": o["tilt"],
                       "pitch": o["pitch"] * SCALE, "w": o["w"] * SCALE, "hx": o["hole_x"] * SCALE, "fx": o["fold_x"] * SCALE, "m": o["m"], "k": {str(i): k for i, k in o["strips"].items()}, "tab": o["tab"], "mid": o["mid"]}
    if whole:
        out["p"] = panels
    return out


def frames_of(bench):
    """手順ごとの形の並び。"""
    return [{"t": f["text"], "q": [_pose(bench, pose, i == len(bench.frames) - 1) for pose in f["poses"]]} for i, f in enumerate(bench.frames)]


SCRIPT = r"""
<script>(()=>{
const F=__FRAMES__,T=__TREES__,L=F.length-1,S=__SCALE__,LIGHT=[-.35,-.6,.72];
const $=id=>document.getElementById(id);
const scene=$('rt-scene'),stage=$('rt-stage'),prev=$('rt-prev'),next=$('rt-next'),text=$('rt-text'),count=$('rt-count'),paper=$('rt-paper'),ruler=$('rt-ruler'),sci=$('rt-sci'),knife=$('rt-knife'),scrap=paper&&paper.querySelector('.rt-scrap'),plugs=[...scene.querySelectorAll('.rt-plug')];
const els=[...scene.querySelectorAll('.rt-p')].map(e=>({e,id:e.dataset.p,key:e.dataset.p.split(':')[0],i:e.dataset.p.split(':')[1],back:e.dataset.back?+e.dataset.back:0,x:+e.dataset.x*S,y:+e.dataset.y*S,shade:e.querySelector('.rt-s')}));
const rods=[...scene.querySelectorAll('.rt-rod')];
const still=window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches;
const last=i=>F[i].q[F[i].q.length-1];
let at=L,dx=0,dy=0,run=null,cam=null;
// 行列は列の順の 16 個
const mul=(a,b)=>{const o=new Array(16);for(let c=0;c<4;c++)for(let r=0;r<4;r++)o[c*4+r]=a[r]*b[c*4]+a[4+r]*b[c*4+1]+a[8+r]*b[c*4+2]+a[12+r]*b[c*4+3];return o};
const hinge=(px,py,ax,ay,deg)=>{const n=Math.hypot(ax,ay),x=ax/n,y=ay/n,a=deg*Math.PI/180,c=Math.cos(a),s=Math.sin(a),t=1-c,r=[t*x*x+c,t*x*y,-s*y,0,t*x*y,t*y*y+c,s*x,0,s*y,-s*x,c,0,0,0,0,1];r[12]=px-(r[0]*px+r[4]*py);r[13]=py-(r[1]*px+r[5]*py);r[14]=-(r[2]*px+r[6]*py);return r};
const toQ=m=>{const a=m[0],b=m[4],c=m[8],d=m[1],e=m[5],f=m[9],g=m[2],h=m[6],i=m[10],t=a+e+i;let s;
if(t>0){s=Math.sqrt(t+1)*2;return[(h-f)/s,(c-g)/s,(d-b)/s,s/4]}
if(a>e&&a>i){s=Math.sqrt(1+a-e-i)*2;return[s/4,(b+d)/s,(c+g)/s,(h-f)/s]}
if(e>i){s=Math.sqrt(1+e-a-i)*2;return[(b+d)/s,s/4,(f+h)/s,(c-g)/s]}
s=Math.sqrt(1+i-a-e)*2;return[(c+g)/s,(f+h)/s,s/4,(d-b)/s]};
const slerp=(p,q,t)=>{let d=p[0]*q[0]+p[1]*q[1]+p[2]*q[2]+p[3]*q[3];if(d<0){q=q.map(v=>-v);d=-d}if(d>.9999)return p;const o=Math.acos(d),a=Math.sin((1-t)*o)/Math.sin(o),b=Math.sin(t*o)/Math.sin(o);return p.map((v,k)=>v*a+q[k]*b)};
const fromQ=([x,y,z,w],tx,ty,tz)=>[1-2*(y*y+z*z),2*(x*y+z*w),2*(x*z-y*w),0,2*(x*y-z*w),1-2*(x*x+z*z),2*(y*z+x*w),0,2*(x*z+y*w),2*(y*z-x*w),1-2*(x*x+y*y),0,tx,ty,tz,1];
const lerp=(a,b,t)=>a+(b-a)*t;
const ease=t=>t<0?0:t>1?1:t*t*(3-2*t);
const put=(o,m)=>{const{e,back,x,y,shade}=o;e.style.transform=`matrix3d(${m.join(',')}) translate3d(${x}px,${y}px,0)${back?` translate3d(${back*S}px,0,0) rotateY(180deg)`:''}`;
const n=(m[8]*LIGHT[0]+m[9]*LIGHT[1]+m[10]*LIGHT[2])*(back?-1:1);shade.style.fillOpacity=(.3*(1-Math.max(0,n))).toFixed(3)};
const rod=(r,s,e)=>{const v=[e[0]-s[0],e[1]-s[1],e[2]-s[2]],l=Math.hypot(...v)||1,d=v.map(c=>c/l),u=Math.abs(d[1])<.9?[0,1,0]:[1,0,0],cr=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];let z=cr(d,u);const zl=Math.hypot(...z);z=z.map(c=>c/zl);const y=cr(z,d);r.style.width=l+'px';r.style.transform=`matrix3d(${[d[0],d[1],d[2],0,y[0],y[1],y[2],0,z[0],z[1],z[2],0,s[0],s[1],s[2],1].join(',')})`};
const view=()=>{const[rx,ry,c,z]=cam,k=Math.min(1,stage.clientWidth/340)*z;scene.style.transform=`scale3d(${k},${k},${k}) rotateX(${rx+dy}deg) rotateY(${ry+dx}deg) translate3d(${-c[0]}px,${-c[1]}px,${-c[2]}px)`;stage.dataset.ry=(ry+dx).toFixed(1)};
const lay=(r,p)=>{r.style.transform=`translate3d(${p[0]}px,${p[1]}px,4px)`};
const misc=B=>{for(const p of plugs)p.style.opacity=B.plug?1:0;if(paper)paper.style.opacity=B.paper?1:0;if(scrap)scrap.style.opacity=B.scrap?1:0;ruler.style.opacity=B.ruler?1:0;if(B.ruler&&ruler.style.transform==='')lay(ruler,B.ruler)};
// 面の形。根の面から順に、親の行列へ折り線のまわりの回転を掛ける。折る順の早い線から折る
const shape=(A,B,key,p,u)=>{const a=A.s[key],b=B.s[key],rows=T[key].rows,n=p.levels.length,w=n>1?Math.max(.1,1.9/n):1,gap=n>1?(1-w)/(n-1):0,e=ease(u),q=slerp(p.q0,p.q1,e);
const base=fromQ(q,lerp(a.m[12],b.m[12],e),lerp(a.m[13],b.m[13],e),lerp(a.m[14],b.m[14],e)),out={[T[key].root]:base};
const of=i=>{if(out[i])return out[i];const r=rows[i],k=p.at[i],v=k===undefined?1:ease((u-k*gap)/w);return out[i]=mul(of(r[0]),hinge(r[1],r[2],r[3],r[4],lerp(a.a[i],b.a[i],v)))};
for(const i in rows)of(i);
for(const i in out){const d=lerp(a.n[i]||0,b.n[i]||0,e);if(d)out[i]=mul(out[i],[1,0,0,0,0,1,0,0,0,0,1,0,0,0,d,1])}
return out};
// 扇が開く所。assembly.fan_pose と同じ計算
const rotZ=d=>{const a=d*Math.PI/180,c=Math.cos(a),s=Math.sin(a);return[c,s,0,0,-s,c,0,0,0,0,1,0,0,0,0,1]};
const rotX=d=>{const a=d*Math.PI/180,c=Math.cos(a),s=Math.sin(a);return[1,0,0,0,0,c,s,0,0,-s,c,0,0,0,0,1]};
const openShape=(o,r)=>{const y=lerp(o.h0[1],o.h1[1],r),below=y-o.rim,now=below>0?Math.min(o.half,Math.atan2(o.mouth,below)*180/Math.PI):o.half,settle=Math.min(1,r/.08),t=Math.max(0,Math.min(1,now/o.half))*settle*settle*(3-2*settle),out={};
for(const i in o.k){const k=o.k[i],off=k-o.m,goal=k===o.m?0:(k%2?o.tilt:-o.tilt),lean=(off%2?o.closed:0)*(1-t)+goal*t,at=[1,0,0,0,0,1,0,0,0,0,1,0,o.h0[0],y,o.h0[2]+off*o.pitch*(1-t),1],back=[1,0,0,0,0,1,0,0,0,0,1,0,-o.hx,-(k+.5)*o.w,0,1];out[i]=mul(at,mul(rotZ(-90+off*o.each*t),mul(rotX(lean),back)))}
out[o.tab]=mul(out[o.mid],hinge(o.fx,0,0,1,90));return out};
const flatPlan=B=>{const out={};for(const key in B.s){const q=toQ(B.s[key].m);out[key]={levels:[],at:{},q0:q,q1:q}}return out};
const rest=B=>{const pl=B.p?null:flatPlan(B),made={};if(pl)for(const key in pl)made[key]=shape(B,B,key,pl[key],1);
for(const o of els){const m=B.p?B.p[o.id]:made[o.key]&&made[o.key][o.i];if(!m){o.e.style.opacity=0;continue}o.e.style.opacity=1;put(o,m)}
for(const r of rods){const a=B.r[r.dataset.r];if(!a){r.style.opacity=0;continue}r.style.opacity=1;rod(r,a.s,a.e)}
sci.style.opacity=0;knife.style.opacity=0;if(B.ruler)lay(ruler,B.ruler);misc(B);cam=[B.rx,B.ry,B.c,B.z];view()};
const words=()=>{const f=F[at];text.textContent=f.t||text.dataset.done;count.textContent=at<L?`${at+1} / ${L}`:'';prev.disabled=at===0;next.textContent=at===L?next.dataset.again:next.dataset.go;stage.dataset.at=at};
const plan=(A,B)=>{const sheets={};let most=0;for(const key in B.s){if(!A.s[key])continue;const a=A.s[key].a,b=B.s[key].a,rows=T[key].rows,ord=i=>B.o&&B.o[key]&&B.o[key][i]!==undefined?B.o[key][i]:-rows[i][5],moved=Object.keys(rows).filter(i=>Math.abs(a[i]-b[i])>.01),levels=[...new Set(moved.map(ord))].sort((x,y)=>x-y),where={};for(const i of moved)where[i]=levels.indexOf(ord(i));most=Math.max(most,levels.length);sheets[key]={levels,at:where,q0:toQ(A.s[key].m),q1:toQ(B.s[key].m)}}return{sheets,dur:B.dur||Math.min(5000,1100+(most>1?450*most:most?300:0))}};
const along=(path,t)=>{let total=0;const seg=[];for(let i=1;i<path.length;i++){const l=Math.hypot(path[i][0]-path[i-1][0],path[i][1]-path[i-1][1]);seg.push(l);total+=l}let d=t*total;for(let i=0;i<seg.length;i++){if(d<=seg[i]||i===seg.length-1){const k=seg[i]?d/seg[i]:0,a=path[i],b=path[i+1];return[lerp(a[0],b[0],k),lerp(a[1],b[1],k),Math.atan2(b[1]-a[1],b[0]-a[0])]}d-=seg[i]}};
const draw=(A,B,pl,u)=>{const made={};for(const key in pl.sheets)made[key]=shape(A,B,key,pl.sheets[key],u);
if(B.open)made.fan=openShape(B.open,ease(u));
for(const o of els){const m=made[o.key];if(m)put(o,m[o.i])}
const e=ease(u);for(const r of rods){const a=A.r[r.dataset.r],b=B.r[r.dataset.r];if(a&&b)rod(r,a.s.map((v,k)=>lerp(v,b.s[k],e)),a.e.map((v,k)=>lerp(v,b.e[k],e)))}
if(A.ruler&&B.ruler)lay(ruler,[lerp(A.ruler[0],B.ruler[0],e),lerp(A.ruler[1],B.ruler[1],e)]);
if(B.cut){const[x,y,a]=along(B.cut,u);(B.knife?knife:sci).style.transform=`translate3d(${x}px,${y}px,8px) rotate(${a}rad) translate(${-30*S}px,${-14*S}px)`}
// 見る向きは先に変える。折って小さくなる時（cam）は、形が縮んでから寄る
const c=ease(u/(B.cam||.4)),zc=B.cam&&B.z>A.z?ease((u-.5)/.5):c;cam=[lerp(A.rx,B.rx,c),lerp(A.ry,B.ry,c),A.c.map((v,k)=>lerp(v,B.c[k],zc)),lerp(A.z,B.z,zc)];view()};
const stop=()=>{if(run){cancelAnimationFrame(run.raf);run=null}};
const play=(A,seq,j)=>{const B=seq[j],pl=plan(A,B),me={raf:0};run=me;
// この形に無い部品は消し、新しく出る部品は行き先に置いてから出す
const fresh=flatPlan(B);for(const key in fresh){if(A.s[key])continue;const m=shape(B,B,key,fresh[key],1);for(const o of els)if(o.key===key)put(o,m[o.i])}
for(const o of els)o.e.style.opacity=B.s[o.key]||(B.open&&o.key==='fan')?1:0;
for(const r of rods){const b=B.r[r.dataset.r];if(!b){r.style.opacity=0;continue}r.style.opacity=1;if(!A.r[r.dataset.r])rod(r,b.s,b.e)}
if(B.ruler&&!A.ruler)lay(ruler,B.ruler);misc(B);sci.style.opacity=B.cut&&!B.knife?1:0;knife.style.opacity=B.cut&&B.knife?1:0;
const start=performance.now();
const tick=now=>{if(run!==me)return;const t=Math.min(1,(now-start)/pl.dur);draw(A,B,pl,t);if(t<1){me.raf=requestAnimationFrame(tick);return}
sci.style.opacity=0;knife.style.opacity=0;if(j+1<seq.length)play(B,seq,j+1);else{run=null;rest(B)}};
me.raf=requestAnimationFrame(tick)};
const show=i=>{const to=Math.max(0,Math.min(L,i)),from=at;stop();at=to;words();
// 前へ戻る時は動かさない。手順 12 の次は、上へ動かして扇が開く所まで動かす
if(still||to<from&&!(from===L&&to===0))return rest(last(to));
const seq=F[to].q;if(to===0){rest(seq[0]);if(seq.length>1)play(seq[0],seq,1);return}
rest(last(from));play(last(from),seq,0)};
prev.addEventListener('click',()=>show(at-1));next.addEventListener('click',()=>show(at===L?0:at+1));
let drag=null;
stage.addEventListener('pointerdown',e=>{drag=[e.clientX,e.clientY,dx,dy];stage.setPointerCapture(e.pointerId)});
stage.addEventListener('pointermove',e=>{if(!drag)return;dx=drag[2]+(e.clientX-drag[0])*.5;dy=Math.max(-70,Math.min(70,drag[3]-(e.clientY-drag[1])*.4));if(cam)view()});
const up=()=>{drag=null};stage.addEventListener('pointerup',up);stage.addEventListener('pointercancel',up);
words();rest(last(L));
})();</script>
"""


@functools.lru_cache(maxsize=128)
def _can(sid, params):
    try:
        return assembly.assemble(sid) is not None
    except (KeyError, ValueError, OSError, StopIteration, ToolMissing):
        return False


def available(sid):
    """組み立ての書き方がある玩具か。"""
    try:
        return _can(sid, json.dumps(hypotheses.sheet_of(sid).get("params") or {}, sort_keys=True, ensure_ascii=False))
    except (KeyError, ValueError, OSError, StopIteration, ToolMissing):
        return False


@functools.lru_cache(maxsize=8)
def _block_html(sid, params):
    """組み立ての絵と送る釦。組むのに 1 秒ほどかかるので、紙の寸法が同じ間は作り直さない。"""
    bench = assembly.assemble(sid)
    if bench is None:
        return ""
    panels = "".join(_panel_html(key, i, sheet) for key, sheet in bench.sheets.items() for i in range(len(sheet.panels)))
    dump = lambda v: json.dumps(v, ensure_ascii=False, separators=(",", ":"))
    script = SCRIPT.replace("__FRAMES__", dump(frames_of(bench))).replace("__TREES__", dump(trees_of(bench))).replace("__SCALE__", str(SCALE))
    paper = paper_html(bench.paper) if bench.paper else ""
    tools = ruler_html() + SCISSORS.format(w=46 * SCALE, h=28 * SCALE) + KNIFE.format(w=46 * SCALE, h=28 * SCALE)
    return (f'<style>{STYLE}</style><p class="lead">{esc(LEAD)}</p>'
            f'<div class="rt-stage" id="rt-stage" role="img" aria-label="組み立ての絵。指で回せます。"><div class="rt-scene" id="rt-scene">{paper}{panels}'
            f'<div class="rt-rod rt-axle" data-r="axle"></div><div class="rt-rod rt-axle" data-r="poke"></div><div class="rt-rod rt-thread" data-r="row"></div><div class="rt-rod rt-thread" data-r="thread"></div>{tools}</div></div>'
            f'<p id="rt-text" aria-live="polite" data-done="{esc(DONE)}"></p>'
            f'<div class="rt-acts"><button type="button" class="quiet" id="rt-prev">{esc(PREV)}</button>'
            f'<button type="button" id="rt-next" data-go="{esc(NEXT)}" data-again="{esc(RESTART)}"></button><span id="rt-count"></span></div>'
            f'<p class="meta">{esc(NOTE_SHAPE)}</p>{script}')


def block(sid):
    """型紙の頁に置く組み立ての節（本人の決定 11-06: 置き場所は型紙の頁）。組み立ての書き方が無い玩具は空。1 つの頁に 1 つだけ置く。"""
    if not available(sid):
        return ""
    return f'<div class="kumitate" id="kumitate"><h3>{esc(LABEL)}</h3>{_block_html(sid, json.dumps(hypotheses.sheet_of(sid).get("params") or {}, sort_keys=True, ensure_ascii=False))}</div>'


def page(sid, look=skin.DEFAULT, path=None):
    """組み立てだけの頁。開くと、まずできあがりの形を見せる。「はじめから」で刷った紙に戻り、手順を送るとまた組み上がる。"""
    toy = hypotheses.load(sid)["toy"]
    body = f'<section class="sec"><h1>{esc(toy)}: {esc(LABEL)}</h1>{block(sid)}<p class="links"><a href="/toy/{esc(sid)}">{esc(toy)}の頁へもどる</a></p></section>'
    return skin.shell(f"{toy}: {LABEL}", body, look, path=path or f"/toy/{sid}/kumitate")
