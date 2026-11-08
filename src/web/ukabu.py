"""入口に浮かぶ玩具（本人の言葉 11-07 夜「試作」: 輪郭で切り取った玩具がぷかぷか浮かぶ案。押すと頁へ飛ぶ形は、本人の言葉「リンクにはせず揺れる」で外した）。

本人の決め（11-07 夜）で採った。切り抜きは本人の OK「この4つと縁でよい」（11-07 夜）。判断の芯:
- 絵は原画の切り抜き（out/sources/<印>.jpg。国立国会図書館の PDM の頁の写し）から、紙の地の色を外して玩具の輪郭だけを残した透けた PNG を作る。
  作った絵は生成物なので repo に入れず out/ukabu/ に置く。輪郭は機械で取った物で、人は確かめていない（玩具の線の外の字や汚れが残ることがある）。
- 取り方: 縮めた絵で、紙の地の色（縁の色の中ほど）から離れた画素と濃い線を「絵」とし、太らせて細らせる（隙間を埋める）→ 縁から届く地を外す
  （中の穴を埋める）→ いちばん大きい塊だけ残す（歌の字を外す）→ 元の大きさへ戻して縁をぼかす。numpy と Pillow だけで作る（repo の依存を増やさない）。
- 頁の側（looks の入口）は、絵がある玩具だけを 4 つ、揺れるだけの飾りとして（本人の言葉「リンクにはせず揺れる」）、入口の最初の画面（題の間）の余白にゆっくり浮かべる（本人の決め 11-07 夜「これをうつしの一番最初の
  余白に浮かばせる」・窓口の条件: 数は少なく・動きはとてもゆっくり・静けさと間を壊さない）。
- 切り抜きは人の目で直してから（本人の決め 11-07 夜）。機械の輪郭の縁に残る紙の地を fringe で外し、直す前と後を並べた絵（compare）で本人が見て決める。
"""
import io
import pathlib
import sys
from collections import deque

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "out/sources"
OUT = ROOT / "out/ukabu"
SMALL = 420  # 輪郭を取る時の幅（px）。塊を数える手間を小さくするため
BOX = (208, 330)  # 浮かべる絵の大きさの上限（px）。見せる幅 104px（狭い幅は 56px）の 2 倍まで。前の高さ 360 の PNG は 4 枚で約 415KB を最初の画面で読んだ
# （入口の絵は 100KB 以下の線・統括 11-07）。透けを持てる WebP で保存して、4 枚を合わせて 150KB より下にする
QUALITY = 82


def mask_of(im):
    """玩具の輪郭の白黒（L・255 が玩具）。im は RGB。"""
    import numpy as np
    from PIL import Image, ImageFilter

    w, h = im.size
    s = im.resize((SMALL, max(1, round(h * SMALL / w))), Image.LANCZOS)
    a = np.asarray(s, dtype=np.int16)
    edge = np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]])
    paper = np.median(edge, axis=0)
    dist = np.sqrt(((a - paper) ** 2).sum(axis=2))
    dark = a.mean(axis=2) < paper.mean() - 55
    ink = (dist > 38) | dark
    m = Image.fromarray((ink * 255).astype("uint8"))
    # 隙間を埋める（墨の線の切れ目を閉じる）。前の 7・5 は犬張子の後ろ脚の線の切れ目から地が入り、白い胴が透けた（11-07 夜に暗い地で見た）
    m = m.filter(ImageFilter.MaxFilter(13)).filter(ImageFilter.MinFilter(11))
    b = np.asarray(m) > 127
    H, W = b.shape
    # 縁から届く地を外す（中の穴を埋める）
    seen = np.zeros_like(b)
    q = deque((y, x) for y in range(H) for x in (0, W - 1) if not b[y, x])
    q.extend((y, x) for x in range(W) for y in (0, H - 1) if not b[y, x])
    for y, x in q:
        seen[y, x] = True
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < H and 0 <= nx < W and not b[ny, nx] and not seen[ny, nx]:
                seen[ny, nx] = True
                q.append((ny, nx))
    solid = ~seen
    # いちばん大きい塊だけ（歌の字や汚れを外す）
    lab = np.zeros(solid.shape, dtype=np.int32)
    best, best_n, n = 0, 0, 0
    for y0 in range(H):
        for x0 in range(W):
            if solid[y0, x0] and not lab[y0, x0]:
                n += 1
                lab[y0, x0] = n
                q, cnt = deque([(y0, x0)]), 0
                while q:
                    y, x = q.popleft()
                    cnt += 1
                    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < H and 0 <= nx < W and solid[ny, nx] and not lab[ny, nx]:
                            lab[ny, nx] = n
                            q.append((ny, nx))
                if cnt > best_n:
                    best, best_n = n, cnt
    keep = Image.fromarray(((lab == best) * 255).astype("uint8"))
    return keep.resize((w, h), Image.LANCZOS).filter(ImageFilter.GaussianBlur(2.5)), best_n / (H * W)


def fringe(im, m):
    """縁に残る紙の地を外した透け（L）。機械の輪郭は、太らせて細らせた分だけ、玩具の線の外に紙の地の帯が残る（11-07 夜に絵で見た）。
    外から、紙の地の色に近い画素だけを伝って中へ入り、届いた所を透かす。玩具の墨の線で止まるので、線の内側の白い胴（犬張子など）は消えない
    （前の色だけで透かす形は、白い胴の縁まで透けた）。伝うのは輪郭の内側 10px ほどの帯の中だけ（線の切れ目から中へ入り込まない）。"""
    import numpy as np
    from PIL import Image, ImageFilter

    w, h = im.size
    S = 800
    sh = max(1, round(h * S / w))
    a = np.asarray(im.resize((S, sh), Image.LANCZOS), dtype=np.int16)
    edge = np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]])
    paper = np.median(edge, axis=0)
    dist = np.sqrt(((a - paper) ** 2).sum(axis=2))
    passable = (dist < 34) & (a.mean(axis=2) > paper.mean() - 40)
    small = m.resize((S, sh), Image.LANCZOS)
    inside = np.asarray(small) >= 128
    band = inside & (np.asarray(small.filter(ImageFilter.MinFilter(11))) < 128)
    gone = np.zeros(inside.shape, dtype=bool)
    q = deque()
    H, W = inside.shape
    ys, xs = np.nonzero(band & passable)
    for y, x in zip(ys.tolist(), xs.tolist()):
        # 外（透けた所）に接する帯の画素から始める
        if any(0 <= y + dy < H and 0 <= x + dx < W and not inside[y + dy, x + dx] for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            gone[y, x] = True
            q.append((y, x))
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < H and 0 <= nx < W and band[ny, nx] and passable[ny, nx] and not gone[ny, nx]:
                gone[ny, nx] = True
                q.append((ny, nx))
    cut_off = Image.fromarray((gone * 255).astype("uint8")).resize((w, h), Image.LANCZOS).filter(ImageFilter.GaussianBlur(1.5))
    alpha = np.asarray(m, dtype=np.float32) * (1 - np.asarray(cut_off, dtype=np.float32) / 255)
    return Image.fromarray(alpha.astype("uint8")).filter(ImageFilter.GaussianBlur(0.8))


def cut(sid, clean=True):
    """その玩具の輪郭の透けた WebP（バイト）と、絵の中で玩具が占める割合。切り抜きが無ければ (None, 0)。
    clean=False は直す前の機械の輪郭（直す前と後を並べる絵のため）。"""
    from PIL import Image

    src = SRC / f"{sid}.jpg"
    if not src.exists():
        return None, 0
    with Image.open(src) as im:
        im = im.convert("RGB")
        m, share = mask_of(im)
        if clean:
            m = fringe(im, m)
        im.putalpha(m)
        box = m.point(lambda v: 255 if v > 24 else 0).getbbox()
        if box:
            im = im.crop(box)
        im.thumbnail(BOX)
        buf = io.BytesIO()
        im.save(buf, "WEBP", quality=QUALITY, method=6)
        return buf.getvalue(), share


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] != "cut":
        print("python -m web.ukabu cut <印…>", file=sys.stderr)
        return 4
    OUT.mkdir(parents=True, exist_ok=True)
    for sid in argv[1:]:
        data, share = cut(sid)
        if data is None:
            print(f"切り抜きが無い: {sid}", file=sys.stderr)
            continue
        (OUT / f"{sid}.webp").write_bytes(data)
        print(sid, f"{share:.2f}", len(data))
    return 0


if __name__ == "__main__":
    sys.exit(main())


# 浮かべる玩具（4 つ・数は試作のまま）。輪郭が玩具の線で閉じて、切り抜きの縁に切られず、紙の地に近い白い面が線の際に無い物を選んだ
# （11-07 夜: 試作の犬張子とでんでん太鼓は、白い胴と太鼓の面が紙の地と同じ色で、線の切れ目から透けたので、猿の人形と土の徳利に替えた。
# 亀は切り抜きの縁で甲羅が切れ、飾り馬は線の外の汚れが残った）。並びは頁の玩具の並びでなく、浮かべる場所の順
PICKS = ("NDL-1187053-R0000026-L", "NDL-1187053-R0000030-L-2", "NDL-1187053-R0000026-L-3", "NDL-1187053-R0000015-L")

# 浮かぶ形。CSS の注は頁に出るので、理由はここに書く（本人の決め 11-07 夜「これをうつしの一番最初の余白に浮かばせる」）:
# - 置き場は入口の最初の画面（題の間・縦の組み・画面いっぱい）の四隅の余白。題字・英字・副題 3 列と札の字（このサイトについて）に重ならない所
#   （幅 1440 で題の塊は真ん中の約 560〜980px・390 では真ん中の約 150〜240px の縦の帯なので、左右の端と上下の端に寄せる）
# - 数と動きは試作のまま（4 つ・16〜25 秒で 1 往復・上下 12px と傾き 1.5 度）。動きを減らす設定では止める
# - 押しても頁へ飛ばない、揺れるだけの飾り（本人の言葉 11-07 夜「リンクにはせず揺れる」）。リンクにせず、焦点に入れず、読み上げでは飛ばす
#   （aria-hidden・alt は空）。押す所も取らない（pointer-events は全部 none）。浮かぶ絵は題の間の字より後ろの層
# - 読み込みは題字より後（loading=lazy・fetchpriority=low・decoding=async）
# - 狭い幅の左下（uk3）は上からの位置で置く（下からだと、題の間が画面より少し高い 390 で画面の下の端に切れた・確かめの気づき 11-07）
UKABU = """
.tj-hall{position:relative}
.ukabu{position:absolute;inset:0;pointer-events:none;z-index:0}
.tj-hall>*:not(.ukabu){position:relative;z-index:1}
.uk{position:absolute;display:block;width:104px;line-height:0;animation:uk-float 19s ease-in-out infinite}
.uk img{width:100%;height:auto;filter:drop-shadow(0 8px 10px rgba(70,55,35,.16))}
.uk1{left:9vw;top:16vh;animation-duration:17s}.uk2{right:10vw;top:22vh;animation-duration:23s;animation-delay:-6s}
.uk3{left:14vw;bottom:14vh;animation-duration:20s;animation-delay:-11s}.uk4{right:15vw;bottom:18vh;animation-duration:25s;animation-delay:-3s}
@keyframes uk-float{0%,100%{transform:translateY(0) rotate(-1.5deg)}50%{transform:translateY(-12px) rotate(1.5deg)}}
@media (max-width:820px){.uk{width:56px}.uk1{left:3vw;top:30vh}.uk2{right:3vw;top:40vh}.uk3{left:4vw;top:64vh;bottom:auto}.uk4{right:4vw;bottom:20vh}}
@media (prefers-reduced-motion:reduce){.uk{animation:none}}
"""


# 字に重ならない置き直し（本人の言葉 11-08「iPadで横表示で見たら文字が重なってる。PC、iPhoneなどいろんな大きさで見ても崩れないようにして。」）。
# CSS の置き場（UKABU の vw・vh）は画面の形で余白が替わり、英語の横書きの頁の幅 1024〜1440 で英字と副題に、幅 375・390 で下へ送る印に重なった。
# 決まった位置の表を増やすと、表に無い大きさでまた重なるので、頁が開いた後に、題の間の字の行と押す所の箱を実際に測って置き直す:
# - まず CSS の位置のまま。字・押す所と重ならなければ動かさない（今の見た目を保つ）
# - 重なる時は、題の間の中で、CSS の位置にいちばん近い重ならない所へ動かす（16px の目で探す）。揺れ（上下 12px・傾き）の分の間をとる
# - どこにも入らない時は、その玩具だけ出さない（飾りなので、字を隠すより出さない方を採る）
# - 絵が読めた時・字の形が決まった時（document.fonts）・画面の大きさが替わった時に置き直す。読み上げと押す所には今までどおり関わらない
PLACE_JS = """<script>(()=>{const hall=document.getElementById('hall'),layer=hall&&hall.querySelector('.ukabu');if(!layer)return;
const toys=[...layer.querySelectorAll('.uk')],GAP=12,SWAY=14,STEP=16;
const boxes=(H)=>{const out=[],tw=document.createTreeWalker(hall,NodeFilter.SHOW_TEXT);let n;
 while(n=tw.nextNode()){if(!n.textContent.trim()||n.parentElement.closest('.ukabu'))continue;const st=getComputedStyle(n.parentElement);if(st.display==='none'||st.visibility==='hidden')continue;
  const r=document.createRange();r.selectNodeContents(n);for(const b of r.getClientRects())if(b.width>0)out.push(b)}
 for(const e of hall.querySelectorAll('a,button'))if(!e.closest('.ukabu')){const b=e.getBoundingClientRect();if(b.width>0)out.push(b)}
 return out.map(b=>({l:b.left-H.left-GAP,t:b.top-H.top-GAP,r:b.right-H.left+GAP,b:b.bottom-H.top+GAP}))};
const hit=(a,list)=>list.some(b=>Math.min(a.r,b.r)>Math.max(a.l,b.l)&&Math.min(a.b,b.b)>Math.max(a.t,b.t));
const place=()=>{const H=hall.getBoundingClientRect(),W=hall.clientWidth,Ht=hall.clientHeight,busy=boxes(H);
 for(const e of toys){e.style.left=e.style.top=e.style.right=e.style.bottom='';e.style.visibility=''}
 for(const e of toys){const b=e.getBoundingClientRect(),w=b.width,h=b.height,x0=b.left-H.left,y0=b.top-H.top;
  const box=(x,y)=>({l:x-4,t:y-SWAY,r:x+w+4,b:y+h+SWAY});
  if(!hit(box(x0,y0),busy)&&x0>=0&&x0+w<=W){busy.push(box(x0,y0));continue}
  let best=null,bd=1e18;
  for(let y=SWAY;y+h+SWAY<=Ht;y+=STEP)for(let x=4;x+w+4<=W;x+=STEP){if(hit(box(x,y),busy))continue;const d=(x-x0)**2+(y-y0)**2;if(d<bd){bd=d;best=[x,y]}}
  if(!best){e.style.visibility='hidden';continue}
  e.style.left=best[0]+'px';e.style.top=best[1]+'px';e.style.right=e.style.bottom='auto';busy.push(box(best[0],best[1]))}};
let tm;const later=()=>{clearTimeout(tm);tm=setTimeout(place,80)};
for(const im of layer.querySelectorAll('img'))if(!im.complete)im.addEventListener('load',later);
if(document.fonts&&document.fonts.ready)document.fonts.ready.then(later);
addEventListener('resize',later);addEventListener('orientationchange',later);place()})()</script>"""


def block(sids):
    """浮かぶ玩具の塊（入口の題の間の中に置く・揺れるだけの飾り）。輪郭の絵（out/ukabu/<印>.webp）がある玩具だけ。1 つも無ければ空。
    字に重ならないよう置き直す台本（PLACE_JS）を後ろに付ける。"""
    from .skin import esc

    have = [s for s in PICKS if s in sids and (OUT / f"{s}.webp").exists()]
    if not have:
        return ""
    toys = "".join(f'<span class="uk uk{i}"><img src="/ukabu/{esc(s)}.webp" alt="" loading="lazy" decoding="async" fetchpriority="low"></span>'
                   for i, s in enumerate(have, 1))
    return f'<div class="ukabu" aria-hidden="true">{toys}</div>' + PLACE_JS
