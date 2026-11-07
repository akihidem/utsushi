"""入口に浮かぶ玩具の試作（本人の言葉 11-07 夜「試作」: 輪郭で切り取った玩具がぷかぷか浮かんで、押すとその玩具の頁へ飛ぶ案）。

試作の枝だけの物（合体しない。本人が見て決める）。判断の芯:
- 絵は原画の切り抜き（out/sources/<印>.jpg。国立国会図書館の PDM の頁の写し）から、紙の地の色を外して玩具の輪郭だけを残した透けた PNG を作る。
  作った絵は生成物なので repo に入れず out/ukabu/ に置く。輪郭は機械で取った物で、人は確かめていない（玩具の線の外の字や汚れが残ることがある）。
- 取り方: 縮めた絵で、紙の地の色（縁の色の中ほど）から離れた画素と濃い線を「絵」とし、太らせて細らせる（隙間を埋める）→ 縁から届く地を外す
  （中の穴を埋める）→ いちばん大きい塊だけ残す（歌の字を外す）→ 元の大きさへ戻して縁をぼかす。numpy と Pillow だけで作る（repo の依存を増やさない）。
- 頁の側（looks の入口）は、絵がある玩具だけを 3〜5 つ、入口の下の余白にゆっくり浮かべる（窓口の条件: 数は少なく・動きはとてもゆっくり・静けさと間を壊さない）。
"""
import io
import pathlib
import sys
from collections import deque

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "out/sources"
OUT = ROOT / "out/ukabu"
SMALL = 420  # 輪郭を取る時の幅（px）。塊を数える手間を小さくするため
TALL = 360  # 浮かべる絵の高さの上限（px）


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
    m = m.filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.MinFilter(5))  # 隙間を埋める
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


def cut(sid):
    """その玩具の輪郭の透けた PNG（バイト）と、絵の中で玩具が占める割合。切り抜きが無ければ (None, 0)。"""
    from PIL import Image

    src = SRC / f"{sid}.jpg"
    if not src.exists():
        return None, 0
    with Image.open(src) as im:
        im = im.convert("RGB")
        m, share = mask_of(im)
        im.putalpha(m)
        box = m.point(lambda v: 255 if v > 24 else 0).getbbox()
        if box:
            im = im.crop(box)
        im.thumbnail((TALL * 2, TALL))
        buf = io.BytesIO()
        im.save(buf, "PNG", optimize=True)
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
        (OUT / f"{sid}.png").write_bytes(data)
        print(sid, f"{share:.2f}", len(data))
    return 0


if __name__ == "__main__":
    sys.exit(main())


# 浮かべる玩具（3〜5 つ・窓口の条件）。輪郭が玩具の線で閉じて、切り抜きの縁に切られていない物を選んだ（11-07 夜に 6 つを切って見た:
# 亀は切り抜きの縁で甲羅が切れ、飾り馬は線の外の汚れが残ったので外した）。並びは頁の玩具の並びでなく、浮かべる場所の順
PICKS = ("NDL-1187053-R0000016-L", "NDL-1187053-R0000026-L", "NDL-1187053-R0000026-L-3", "NDL-1187053-R0000007-R")

# 浮かぶ形。CSS の注は頁に出るので、理由はここに書く:
# - 幅 1400 以上: えらぶ の棚（最大 1180px）の左右の余白に、棚の下の端から上へ間を空けて置く（棚の字と札に重ならない）
# - それより狭い（390 など）: 頁の終わりの余白に、小さく 1 列（頭の題の間と まずはここから と棚の間の余白は食わない）
# - 動きはとてもゆっくり（16〜25 秒で 1 往復・上下 12px と傾き 1.5 度）。動きを減らす設定では止める。キーボードで押せる（a に名を持たせ、押す印を見せる）
UKABU = """
.ukabu{position:relative;height:0;max-width:1440px;margin:0 auto}
.uk{position:absolute;display:block;width:104px;line-height:0;border:0;animation:uk-float 19s ease-in-out infinite}
.uk img{width:100%;height:auto;filter:drop-shadow(0 8px 10px rgba(70,55,35,.18))}
.uk:focus-visible{outline:2px solid #5d554a;outline-offset:6px;border-radius:6px}
.uk1{left:14px;bottom:1500px;animation-duration:17s}.uk2{right:14px;bottom:1100px;animation-duration:23s;animation-delay:-6s}
.uk3{left:18px;bottom:600px;animation-duration:20s;animation-delay:-11s}.uk4{right:18px;bottom:260px;animation-duration:25s;animation-delay:-3s}
@keyframes uk-float{0%,100%{transform:translateY(0) rotate(-1.5deg)}50%{transform:translateY(-12px) rotate(1.5deg)}}
@media (max-width:1399px){.ukabu{height:auto;display:flex;justify-content:center;flex-wrap:wrap;gap:16px 20px;padding:4vh 5vw 2vh}.uk{position:static;width:64px}}
@media (prefers-reduced-motion:reduce){.uk{animation:none}}
"""


def block(sids):
    """浮かぶ玩具の塊（入口の棚の後ろに置く）。輪郭の絵（out/ukabu/<印>.png）がある玩具だけ。1 つも無ければ空。"""
    from omochae import hypotheses

    from .skin import esc

    have = [s for s in PICKS if s in sids and (OUT / f"{s}.png").exists()]
    if not have:
        return ""
    links = "".join(f'<a class="uk uk{i}" href="/toy/{esc(s)}"><img src="/ukabu/{esc(s)}.png" alt="{esc(hypotheses.load(s)["toy"])}" loading="lazy" decoding="async"></a>'
                    for i, s in enumerate(have, 1))
    return f'<div class="ukabu">{links}</div>'
