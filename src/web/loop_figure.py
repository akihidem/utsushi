"""説明の頁（このサイトについて）と のこす の頁の輪の図。11-08 から 1 本の輪（うつしの輪）: 作る → のこす → 直す → 刷る。

組み直し（11-08・本人の決め「この案で組み直す」・本人の言葉「構造単純でいきたい」・統括の案 grove の state/one-loop-20261108.md）:
- 輪は 1 本・駅は 4 つ。駅ごとに誰がするかの印（作る・のこす は人、直す は Claude、刷る は人が版を決める）。真ん中に輪の名「うつしの輪」
- 学ぶ人の経験学習の輪（本人が採った文 ADOPTED）は、同じ輪を人の側から見た物として、図の下の 1 行に収める（ADOPTED の文は頁にそのまま残す）
- 正直に言う所: 直す は今、作る側が記録を Claude に渡して回している（作品の中の Claude API がひとりでに回してはいない）。図の下の 1 行で言う
- 前の二つの輪の図（a・b の 2 形）と、それを下絵にした生成の絵は使わない（生成の絵の道は、置き場の確かめた絵を返すだけで、頁からは呼ばない）
- 新しい字（駅・誰の印・駅の説明・真ん中・下の 2 行）は本人の確かめ待ち

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

from .skin import esc

ADOPTED = ("作って、確かめて、ふり返って、次を考える。この経験から学ぶ輪（経験学習の輪）は、ワークショップでは、進め役（ファシリテーター）といっしょに一周だけ回ります。"
           "うつしがあると、その後も一人で回り続けられます。のこした記録が、次に作る時の入り口になります。進め役の役目は、型紙と記録の形の中に残っています。")
WORDS = {"ws": "ワークショップ", "fac1": "進め役（ファシリテーター）と", "fac2": "いっしょに一周", "ut": "うつし", "alone": "一人で回り続けられます",
         "make": "作って", "check": "確かめて", "look": "ふり返って", "next": "次を考える", "rec": "のこした記録", "door": "次に作る時の入り口",
         "form": "型紙と記録の形"}
# 1 本の輪の字（11-08 の組み直し・本人の確かめ待ち）。駅は時計回りに 作る（上）→ のこす（右）→ 直す（下）→ 刷る（左）
STATIONS = (("make1", "作る", "人", "紙で作って試す"), ("keep1", "のこす", "人", "手帖に写真・声・字"),
            ("fix1", "直す", "Claude", "記録から型紙を直す"), ("print1", "刷る", "人が版を決める", "新しい版の型紙"))
NAME = "うつしの輪"
CENTER = "1 周で 1 つ版が上がる"
LEARNER = "学ぶ人から見ると: 作って、確かめて、ふり返って、次を考える"
HONEST = "直すは今、記録を Claude に渡して回しています。"
RING_LABEL = NAME + ": " + " → ".join(f"{n}（{w}）" for _, n, w, _ in STATIONS) + " → " + STATIONS[0][1]
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


def drawn(variant=None):
    """1 本の輪の SVG（頁の幅に合わせて縮む）。4 つの駅を時計回りに置き、駅の間を手書きの風合いの弧と矢でつなぐ。字は text の要素に 1 つずつ。"""
    W, H, CX, CY, R = 540, 470, 270, 228, 120
    ang = (-90, 0, 90, 180)
    body = ""
    for i in range(4):
        a0, sw = math.radians(ang[i] + 24), math.radians(90 - 48)
        # 短い弧は揺れが目立つので、揺れを小さくし、なぞりは 1 度にする（11-08 に絵で見た。前の値では波打って矢に見えにくかった）
        arc = _ring(CX, CY, R, 31 + i, start=a0, sweep=sw, wob=0.25, n=24)
        body += _stroke(arc, SHU, 2.6, 31 + i, twice=False) + _arrow(arc, SHU, 2.4)
    for (key, name, who, what), d in zip(STATIONS, ang):
        x, y = CX + R * math.cos(math.radians(d)), CY + R * math.sin(math.radians(d))
        body += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="31" fill="var(--paper,#fbf8f2)" stroke="{INK}" stroke-width="2"/>'
        body += f'<text x="{x:.1f}" y="{y + 6:.1f}" text-anchor="middle" font-size="19" font-weight="bold" fill="{INK}">{esc(name)}</text>'
        if d == -90:
            tx, ty, anchor = x, y - 62, "middle"
        elif d == 90:
            tx, ty, anchor = x, y + 52, "middle"
        elif d == 0:
            tx, ty, anchor = x + 42, y - 4, "start"
        else:
            tx, ty, anchor = x - 42, y - 4, "end"
        body += f'<text x="{tx:.1f}" y="{ty:.1f}" text-anchor="{anchor}" font-size="13" fill="{SHU if who == "Claude" else MUTE}">{esc(who)}</text>'
        body += f'<text x="{tx:.1f}" y="{ty + 15:.1f}" text-anchor="{anchor}" font-size="11" fill="{MUTE}">{esc(what)}</text>'
    body += f'<text x="{CX}" y="{CY - 6}" text-anchor="middle" font-size="16" fill="{INK}">{esc(NAME)}</text>'
    body += f'<text x="{CX}" y="{CY + 14}" text-anchor="middle" font-size="11" fill="{MUTE}">{esc(CENTER)}</text>'
    body += f'<text x="{CX}" y="{H - 14}" text-anchor="middle" font-size="11" fill="{MUTE}">{esc(LEARNER)}</text>'
    return (f'<svg class="loop-ring" viewBox="0 0 {W} {H}" role="img" aria-label="{esc(RING_LABEL)}" '
            f'style="width:100%;height:auto;display:block;font-family:inherit">{body}</svg>')
