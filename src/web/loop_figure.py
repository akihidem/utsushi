"""説明の頁（このサイトについて）と のこす の頁の輪の図。11-08 から 1 本の輪（うつしの輪）。字は型紙の窓の輪の図（web/wa.py）と同じ言い方。

組み直し（11-08）:
- 本人の決め「この案で組み直す」・本人の言葉「構造単純でいきたい」: 輪は 1 本・駅は 4 つ（統括の案 grove の state/one-loop-20261108.md）
- 本人の言葉「なおす、わかりにくい」と「…と図がわかりにくい」「型紙の窓のこれまでの説明のほうがわかりやすい」: 駅の字は前の 作る・のこす・直す・刷る を
  やめ、型紙の窓の輪の図の字（wa.STEPS・2 行の分け方 wa.LINES・真ん中の wa.NOW）をそのまま読む。同じ輪の字が頁ごとに違わないよう、ここでは字を持たない
- 図の字は減らす。駅の説明の行と、図の下の「学ぶ人から見ると」の行は外した（学ぶ人の側の言い方は、図のすぐ上の本人が採った文 ADOPTED が持つ）。
  誰がするかは字の札でなく、駅の外の小さな絵（人の形と Claude の印）で見せる。ためしの案と次の型紙は Claude、切って組むと記録に書くは人。
  次の型紙をよくする所は、Claude が案を出し人が採る（CLAUDE.md の輪）ので、Claude と人の 2 つを並べる
- 正直に言う所: 次の型紙は今、作った人の記録を Claude に渡して作っている（作品の中の Claude API がひとりでに回してはいない）。図の下の 1 行で言う
- 前の二つの輪の図（a・b の 2 形）と、それを下絵にした生成の絵は使わない（生成の絵の道は、置き場の確かめた絵を返すだけで、頁からは呼ばない）

前の形（11-07）: 二つの輪を、手書きの風合いで重ねる（窓口の決め 155253・UX の担当が作る）。

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
- 本人の言葉（11-07 夕）「qwen2.1 でもっと綺麗な絵を」: 絵は Qwen Image 2.1（SageMaker・ComfyUI 経由）で描き直す。生成の字は崩れるので、絵には字を描かせず、
  この部品の線の絵（字を外した物）を下絵として渡し、同じ並びの絵にした。字は今のまま SVG で絵の上に重ねる（並びが下絵と同じなので、字の置き場も同じ）。
  生成した絵は repo に入れない（repo の画像の決まり）。公開の場のデータの置き場（OMOCHAE_DATA/loop_figure/loop-<形>.jpg）に、横の checked.json の
  確かめた印（checked_by）と一緒に置いた時だけ使い、/about/loop-figure/loop-<形>.jpg で返す。無い時（repo だけを clone した審査の場・確かめる前）は線の絵のまま
"""
import json
import os
import pathlib
import math
import random

from omochae.hypotheses import ROOT

from . import wa
from .skin import esc

# 輪の節の文（本人の答え 11-08「字 1 と絵 A。」）。本人の言葉「…と図がわかりにくい」「型紙の窓のこれまでの説明のほうがわかりやすい」で、
# 前の文（11-07 に採った「作って、確かめて、ふり返って、次を考える。この経験から学ぶ輪（経験学習の輪）は…進め役の役目は、型紙と記録の形の中に
# 残っています。」）を、型紙の窓の輪の図の言い方（ためしの案（仮説）→ 切って、折って、組む → どう工夫したかを記録に書く → 次の型紙をよくする）で
# 言い直した案 1。「経験学習の輪」「ファシリテーター」は内輪の言葉なので外した（決めの記録 352）。名前は前のまま ADOPTED（本人が採った文）
ADOPTED = ("型紙は、AI が考えた ためしの案（仮説）です。切って、折って、組んで、どう工夫したかを記録に書くと、その記録をもとに次の型紙をよくします。"
           "ワークショップでは進め役の人といっしょに 1 回、うつしがあれば そのあとも ひとりで、この輪をまわせます。")
WORDS = {"ws": "ワークショップ", "fac1": "進め役（ファシリテーター）と", "fac2": "いっしょに一周", "ut": "うつし", "alone": "一人で回り続けられます",
         "make": "作って", "check": "確かめて", "look": "ふり返って", "next": "次を考える", "rec": "のこした記録", "door": "次に作る時の入り口",
         "form": "型紙と記録の形"}
# 1 本の輪の駅（11-08）。字は型紙の窓の輪の図と同じ物を読む（wa.STEPS）。駅ごとに誰がするか（駅の外の小さな絵）。時計回りに 上 → 右 → 下 → 左
WHO = (("Claude",), ("人",), ("人",), ("Claude", "人"))
STATIONS = tuple(zip(wa.STEPS, WHO))
NAME = "うつしの輪"
CENTER = "1 周で 1 つ版が上がる"
# 図の下の正直な 1 行。本人の言葉（11-08・決めの記録 521）「文書がおかしい。次の型紙をよくするのは今、記録を Claude に渡して回しています。
# その事実に合う文に直してください。」で、前の字「次の型紙をよくするのは今、記録を Claude に渡して回しています。」を替えた。
# 字は 2 案（A と、B「次の型紙は今、作った人の記録を Claude に渡して、よくしています。」）から、本人の答え「(A) でよい。」の A
HONEST = "今は、作った人の記録を Claude に渡して、次の型紙の案を作っています。どの版にするかは人が決めます。"
RING_LABEL = NAME + ": " + " → ".join(f"{n}（{'と'.join(w)}）" for n, w in STATIONS) + " → " + STATIONS[0][0]
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


def _img_dir():
    return pathlib.Path(os.environ.get("OMOCHAE_DATA", ROOT / "data")) / "loop_figure"


def image_ok(name):
    """生成した絵を出してよいか: 名の形（loop-a.jpg か loop-b.jpg）・確かめた印・置き場の中のふつうのファイル。"""
    if name not in ("loop-a.jpg", "loop-b.jpg"):
        return False
    box = _img_dir()
    try:
        checked = json.loads((box / "checked.json").read_text(encoding="utf-8"))
        real = (box / name).resolve(strict=True)
    except (OSError, ValueError):
        return False
    row = checked.get(name) if isinstance(checked, dict) else None
    return bool(isinstance(row, dict) and row.get("checked_by")) and real.parent == box.resolve() and real.is_file()


def image_bytes(name):
    """/about/loop-figure/<名> の中身。出さない物は None（呼ぶ側が 404）。"""
    if not image_ok(name):
        return None
    try:
        return (_img_dir() / name).read_bytes()
    except OSError:
        return None


def _labels(variant):
    """字だけ（線の絵と同じ置き場）。生成した絵の上に重ねる時に使う。"""
    if variant == "a":
        return (_t("ws", 100, 50, 14, MUTE, weight="bold") + _t("fac1", 100, 70, 11, MUTE) + _t("fac2", 100, 86, 11, MUTE)
                + _t("ut", 300, 36, 16, INK, weight="bold") + _t("alone", 300, 54, 11, INK)
                + _t("make", 178, 148) + _t("check", 318, 96) + _t("look", 356, 282, anchor="end") + _t("next", 226, 302)
                + _t("form", 238, 184, 12, SHU) + _t("rec", 262, 336, 12, SHU) + _t("door", 112, 336, 12, SHU)), 345
    return (_t("ws", 90, 30, 13, MUTE, weight="bold") + _t("fac1", 90, 46, 10, MUTE) + _t("fac2", 90, 60, 10, MUTE)
            + _t("ut", 292, 36, 16, INK, weight="bold") + _t("alone", 292, 54, 11, INK)
            + _t("make", 40, 212) + _t("check", 322, 122) + _t("look", 352, 272, anchor="end") + _t("next", 186, 318)
            + _t("form", 186, 190, 12, SHU) + _t("rec", 252, 348, 12, SHU) + _t("door", 110, 348, 12, SHU)), 356


def svg(variant=None):
    """説明の頁と のこす の頁に置く 1 本の輪の図（11-08 の組み直し）。下に正直に言う 1 行を添える。variant は前の 2 形の名残で、使わない。"""
    return (f'<figure class="loop-fig" style="margin:12px auto;max-width:460px">{drawn()}'
            f'<figcaption class="meta" style="text-align:center">{esc(HONEST)}</figcaption></figure>')


def _person(x, y):
    """人の形の小さな絵（頭の丸と肩の線）と、右に「人」。x, y は絵の真ん中。返すのは (SVG, 横の幅)。"""
    return (f'<circle cx="{x:.1f}" cy="{y - 5:.1f}" r="5" fill="none" stroke="{INK}" stroke-width="2"/>'
            f'<path d="M{x - 9:.1f} {y + 10:.1f} Q{x:.1f} {y - 3:.1f} {x + 9:.1f} {y + 10:.1f}" fill="none" stroke="{INK}" stroke-width="2" stroke-linecap="round"/>'
            f'<text x="{x + 14:.1f}" y="{y + 6:.1f}" font-size="{WHO_FS}" fill="{MUTE}">人</text>'), 14 + WHO_FS


def _claude(x, y):
    """Claude の印の小さな絵（画面の四角と、中の 4 つの光の先）と、右に「Claude」。会社の標章は描かない。返すのは (SVG, 横の幅)。"""
    star = " ".join(f"{x + dx:.1f},{y + dy:.1f}" for dx, dy in ((0, -6), (1.8, -1.8), (6, 0), (1.8, 1.8), (0, 6), (-1.8, 1.8), (-6, 0), (-1.8, -1.8)))
    return (f'<rect x="{x - 10:.1f}" y="{y - 9:.1f}" width="20" height="18" rx="5" fill="none" stroke="{SHU}" stroke-width="2"/>'
            f'<polygon points="{star}" fill="{SHU}"/>'
            f'<text x="{x + 14:.1f}" y="{y + 6:.1f}" font-size="{WHO_FS}" fill="{SHU}">Claude</text>'), 14 + WHO_FS * 3.4


def _sheet(x, y):
    """真ん中の型紙の小さな絵（紙の角を折った四角と、点線の折り線）。"""
    return (f'<path d="M{x - 15:.1f} {y - 20:.1f} H{x + 7:.1f} L{x + 15:.1f} {y - 12:.1f} V{y + 20:.1f} H{x - 15:.1f} Z" fill="var(--paper,#fbf8f2)" stroke="{INK}" stroke-width="1.6"/>'
            f'<path d="M{x - 9:.1f} {y:.1f} H{x + 9:.1f}" stroke="{SHU}" stroke-width="1.4" stroke-dasharray="3 3"/>')


def _bend(p0, c, p1, seed, n=18):
    """2 つの札の間の曲がった矢の線（2 次の曲線を、手で描いたように少し揺らした点の並び）。"""
    rnd = random.Random(seed)
    pts = []
    for i in range(n + 1):
        t = i / n
        x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * c[0] + t * t * p1[0]
        y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * c[1] + t * t * p1[1]
        j = 0 if i in (0, n) else 0.5
        pts.append((x + rnd.uniform(-j, j), y + rnd.uniform(-j, j)))
    return pts


# 図の字の大きさ（viewBox の中の px）。幅 390 の画面では図が約 320px に縮むので、駅の字 20 は約 13px・誰の名 15 は約 10px で出る
# （前の 15 では約 8px で読めなかった。11-08 に 390 の幅で撮って見た）
STEP_FS, WHO_FS = 20, 15


def drawn(variant=None):
    """1 本の輪の SVG（頁の幅に合わせて縮む）。4 つの駅を時計回り（上 → 右 → 下 → 左）に角の丸い札で置き、札の間を手書きの風合いの曲がった矢でつなぐ。
    誰がするかの小さな絵は札の中の上の段（札の外に置くと図の横幅が広がり、狭い画面で字が小さくなりすぎた）。字は text の要素に 1 つずつ。"""
    PAD, RH, RV = 10, 172, 140  # 真ん中から左右の札・上下の札までの長さ
    boxes = []
    for name, who in STATIONS:
        lines = wa.LINES.get(name, (name,))
        widths = [(_claude if w == "Claude" else _person)(0, 0)[1] + 16 for w in who]
        row = sum(widths) + 12 * (len(widths) - 1)
        bw = max(max(len(t) for t in lines) * STEP_FS, row) + 28
        bh = 30 + len(lines) * (STEP_FS + 6) + 12
        boxes.append((name, who, lines, bw, bh, widths))
    CX = PAD + boxes[3][3] / 2 + RH
    W = CX + RH + boxes[1][3] / 2 + PAD
    CY = PAD + boxes[0][4] / 2 + RV
    H = CY + RV + boxes[2][4] / 2 + PAD
    spots = ((CX, CY - RV), (CX + RH, CY), (CX, CY + RV), (CX - RH, CY))
    (tx, ty), (rx, ry), (bx, by), (lx, ly) = spots
    tw, rw, bw_, lw = (b[3] / 2 for b in boxes)
    th, rh, bh_, lh = (b[4] / 2 for b in boxes)
    g = 7
    body = ""
    # 矢: 上の札の右の端 → 右の札の上の端、右の札の下の端 → 下の札の右の端…と、札の端の真ん中どうしを角の側へふくらむ曲線でつなぐ（4 本で 1 周）
    for k, (p0, c, p1) in enumerate((((tx + tw + g, ty), (rx, ty), (rx, ry - rh - g)), ((rx, ry + rh + g), (rx, by), (bx + bw_ + g, by)),
                                     ((bx - bw_ - g, by), (lx, by), (lx, ly + lh + g)), ((lx, ly - lh - g), (lx, ty), (tx - tw - g, ty)))):
        pts = _bend(p0, c, p1, 41 + k)
        body += _stroke(pts, SHU, 2.6, 41 + k, twice=False) + _arrow(pts, SHU, 2.4)
    for (name, who, lines, w, h, widths), (x, y) in zip(boxes, spots):
        body += f'<rect x="{x - w / 2:.1f}" y="{y - h / 2:.1f}" width="{w:.0f}" height="{h:.0f}" rx="10" fill="var(--paper,#fbf8f2)" stroke="{INK}" stroke-width="1.8"/>'
        # 上の段: 誰がするかの絵（2 つの時は並べる）。札の真ん中にそろえる
        ix = x - (sum(widths) + 12 * (len(widths) - 1)) / 2
        for w_, wd in zip(who, widths):
            body += (_claude if w_ == "Claude" else _person)(ix + 10, y - h / 2 + 22)[0]
            ix += wd + 12
        top = y - h / 2 + 30 + STEP_FS + 4
        body += "".join(f'<text x="{x:.1f}" y="{top + i * (STEP_FS + 6):.1f}" text-anchor="middle" font-size="{STEP_FS}" fill="{INK}">{esc(t)}</text>'
                        for i, t in enumerate(lines))
    body += _sheet(CX, CY - 30)
    body += f'<text x="{CX:.1f}" y="{CY + 18:.1f}" text-anchor="middle" font-size="{STEP_FS}" fill="{INK}">{esc(wa.NOW)}</text>'
    body += f'<text x="{CX:.1f}" y="{CY + 40:.1f}" text-anchor="middle" font-size="13" fill="{MUTE}">{esc(CENTER)}</text>'
    return (f'<svg class="loop-ring" viewBox="0 0 {W:.0f} {H:.0f}" role="img" aria-label="{esc(RING_LABEL)}" '
            f'style="width:100%;height:auto;display:block;font-family:inherit">{body}</svg>')
