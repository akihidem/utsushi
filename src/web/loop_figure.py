"""説明の頁（このサイトについて）の学びの輪の図: 二つの輪を、手書きの風合いで重ねる（窓口の決め 155253・UX の担当が作る）。

もと: 本人の言葉（ワークショップの設計の考え）「経験学習の輪はワークショップではファシリテーターと一周だけ回るが、うつし があるとその後も一人で回り続ける。
記録が次の導入になり、ファシリテーターの役割は型紙と記録の形の中に残る」と、本人が採った文（11-07「案 1 の字でよい」・下の ADOPTED）。

判断の芯:
- 二つの輪の読み: 一つは ワークショップ（進め役といっしょに一周）、もう一つは うつし（その後も一人で回り続ける）。二つが重なる所で一周目が受け渡される。
  回り続ける輪の上に 作って → 確かめて → ふり返って → 次を考える、輪の下で のこした記録 → 次に作る時の入り口 と戻る。真ん中に 型紙と記録の形（進め役の役目が残る所）
- 図の字は ADOPTED の言葉だけ（切り出した言葉が ADOPTED の中にそのままある事を試験が見る）。新しい言い方を図で足さない
- 画像のファイルは作らない（repo の画像は NDL と東京学芸大学の PDM の物だけの決まり）。型紙の図と同じく、その場で SVG を描く。手書きの風合いは、線を少し揺らし、
  二度なぞる形で出す（揺れは決まった種で作るので、開くたびに同じ絵）
- 字は SVG の text の要素に 1 つずつ置く（英語の頁の訳の表が字を替えられるように）。読み上げには ADOPTED の全文を渡す
- 形は 2 つの案（a: 二つの輪を横に重ねる／b: 大きい輪の上に小さい一周目を重ねる）。既定は b（UX の担当の推し）。どちらにするかは本人の確かめで、svg() の既定を替えるだけ
"""
import math
import random

from .skin import esc

ADOPTED = ("作って、確かめて、ふり返って、次を考える。この経験から学ぶ輪（経験学習の輪）は、ワークショップでは、進め役（ファシリテーター）といっしょに一周だけ回ります。"
           "うつしがあると、その後も一人で回り続けられます。のこした記録が、次に作る時の入り口になります。進め役の役目は、型紙と記録の形の中に残っています。")
WORDS = {"ws": "ワークショップ", "fac1": "進め役（ファシリテーター）と", "fac2": "いっしょに一周", "ut": "うつし", "alone": "一人で回り続けられます",
         "make": "作って", "check": "確かめて", "look": "ふり返って", "next": "次を考える", "rec": "のこした記録", "door": "次に作る時の入り口",
         "form": "型紙と記録の形"}
INK, SHU, MUTE = "#2b2722", "#b04030", "#6f665a"


def _ring(cx, cy, r, seed, start=0.0, sweep=2 * math.pi * 0.9, wob=1.1, n=64):
    """揺れた円弧の点（手で描いた輪のように、半径と向きを少しずつ揺らす）。"""
    rnd = random.Random(seed)
    drift = 0.0
    pts = []
    for i in range(n + 1):
        t = start + sweep * i / n
        drift += rnd.uniform(-0.12, 0.12)
        rr = r + wob * math.sin(i * 0.7 + seed) + drift * 0.4  # 揺れは小さく（大きいと渦に見え、輪に読めなかった。11-07 の 1 枚目）
        pts.append((cx + rr * math.cos(t), cy + rr * math.sin(t)))
    return pts


def _path(pts):
    d = f"M{pts[0][0]:.1f} {pts[0][1]:.1f}"
    for (x0, y0), (x1, y1) in zip(pts[1:-1:2], pts[2::2]):
        d += f" Q{x0:.1f} {y0:.1f} {x1:.1f} {y1:.1f}"
    return d


def _stroke(pts, color, w, seed, twice=True):
    """二度なぞった線（二度目は少しずらす）。"""
    out = f'<path d="{_path(pts)}" fill="none" stroke="{color}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"/>'
    if twice:
        rnd = random.Random(seed + 99)
        dx, dy = rnd.uniform(-1.2, 1.2), rnd.uniform(-1.2, 1.2)
        out += (f'<path d="{_path([(x + dx, y + dy) for x, y in pts])}" fill="none" stroke="{color}" stroke-width="{w * 0.55:.2f}" '
                f'stroke-linecap="round" opacity=".55"/>')
    return out


def _arrow(pts, color, w):
    """線の終わりに、手で描いた矢の頭。"""
    (x0, y0), (x1, y1) = pts[-3], pts[-1]
    a = math.atan2(y1 - y0, x1 - x0)
    h = 9
    l = (x1 - h * math.cos(a - 0.45), y1 - h * math.sin(a - 0.45))
    r = (x1 - h * math.cos(a + 0.45), y1 - h * math.sin(a + 0.45))
    return (f'<path d="M{l[0]:.1f} {l[1]:.1f} L{x1:.1f} {y1:.1f} L{r[0]:.1f} {r[1]:.1f}" fill="none" stroke="{color}" '
            f'stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"/>')


def _t(key, x, y, size=13, color=INK, anchor="middle", weight="normal"):
    return (f'<text x="{x:.0f}" y="{y:.0f}" font-size="{size}" fill="{color}" text-anchor="{anchor}" font-weight="{weight}">'
            f'{esc(WORDS[key])}</text>')


def _path_pts(*pts, n=6):
    """折れ線を、手で描いたように少し揺らした点の並びにする。"""
    rnd = random.Random(len(pts) * 7 + int(pts[0][0]))
    out = []
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        for k in range(n):
            t = k / n
            out.append((x0 + (x1 - x0) * t + rnd.uniform(-0.8, 0.8), y0 + (y1 - y0) * t + rnd.uniform(-0.8, 0.8)))
    out.append(pts[-1])
    return out


def svg(variant="b"):
    """図の SVG（頁の幅に合わせて縮む）。variant は "a"（二つの輪を横に重ねる）か "b"（大きい輪の左上に一周目を重ねる）。
    どちらも、回り続ける輪の上に 作って → 確かめて → ふり返って → 次を考える（時計回り）、下に 次を考える → のこした記録 → 次に作る時の入り口 → 作って の戻り。"""
    if variant == "a":
        h = 345
        small = _ring(100, 170, 58, 3, start=-2.2)
        big = _ring(226, 178, 104, 7, start=-0.9)
        big2 = _ring(226, 178, 112, 11, start=-0.5, sweep=2 * math.pi * 0.62, wob=0.8)
        back = _path_pts((256, 318), (96, 318), (66, 292), (70, 252), (112, 214))
        body = (_stroke(small, MUTE, 2.2, 3) + _arrow(small, MUTE, 2.0)
                + _stroke(big, INK, 2.6, 7) + _arrow(big, INK, 2.4) + _stroke(big2, INK, 1.2, 11, twice=False)
                + _stroke(back, SHU, 2.2, 5) + _arrow(back, SHU, 2.0)
                + _t("ws", 100, 50, 14, MUTE, weight="bold") + _t("fac1", 100, 70, 11, MUTE) + _t("fac2", 100, 86, 11, MUTE)
                + _t("ut", 300, 36, 16, INK, weight="bold") + _t("alone", 300, 54, 11, INK)
                + _t("make", 178, 148) + _t("check", 318, 96) + _t("look", 356, 282, anchor="end") + _t("next", 226, 302)
                + _t("form", 238, 184, 12, SHU)
                + _t("rec", 262, 336, 12, SHU) + _t("door", 112, 336, 12, SHU))
    else:
        h = 356
        big = _ring(186, 184, 112, 21, start=-1.3)
        big2 = _ring(186, 184, 120, 25, start=-0.9, sweep=2 * math.pi * 0.6, wob=0.8)
        first = _ring(90, 118, 42, 17, start=-2.4)
        back = _path_pts((246, 330), (70, 330), (40, 296), (40, 232))
        body = (_stroke(big, INK, 2.6, 21) + _arrow(big, INK, 2.4) + _stroke(big2, INK, 1.2, 25, twice=False)
                + _stroke(first, MUTE, 2.2, 17) + _arrow(first, MUTE, 2.0)
                + _t("ws", 90, 30, 13, MUTE, weight="bold") + _t("fac1", 90, 46, 10, MUTE) + _t("fac2", 90, 60, 10, MUTE)
                + _t("ut", 292, 36, 16, INK, weight="bold") + _t("alone", 292, 54, 11, INK)
                + _t("make", 40, 212) + _t("check", 322, 122) + _t("look", 352, 272, anchor="end") + _t("next", 186, 318)
                + _t("form", 186, 190, 12, SHU)
                + _stroke(back, SHU, 2.2, 23) + _arrow(back, SHU, 2.0)
                + _t("rec", 252, 348, 12, SHU) + _t("door", 110, 348, 12, SHU))
    return (f'<svg class="loop-fig" viewBox="0 0 360 {h}" role="img" aria-label="{esc(ADOPTED)}" '
            f'style="width:100%;max-width:420px;height:auto;display:block;font-family:inherit">{body}</svg>')
