"""小さな案内役: 北斎漫画 1 編の「提灯を高く掲げる人」を切り絵にして、いくつかの場面に重ねて歩かせる（本人の決定 11-06）。

本人の言葉: 「デモ動画に、小さな小人の案内役を足す。北斎漫画のアニメ化で。」。候補 3 人から本人が B（提灯を高く掲げる人）を選んだ。

決めた事と理由:
- 作り方はコードだけ。国立国会図書館の PDM の頁から人物を 1 人切り出し、切り絵のまま動かす（平行移動・左右の向き・歩く間の小さな上下の揺れ・
  止まって提灯を少し傾ける・溶けて現れる）。線は描き直さず、体の形も変えない。生成 AI の動画の道具は使わない（外に出る操作と課金になる）。
- 秒を足さない。今の場面に重ねるだけ（3 分の床）。新しい字も語りも足さない。クレジットの「図の手入れ」の行も今の字のまま（本人の決定 11-06:
  「あの 1 句は足さない」）。出所と改変は figures.json の v1-R0000013 に残す。
- 出る場面は 5 つ（PLANS）: 玩具の頁（前提の札）・手帖（止まったら聞く口）・持ちよる（他の人が作った物の列。窓口の決定 11-07 で足した）・表と裏の境目の札・輪の図。
  出さない場面: 始まり（職人の玩具の動画）・本人の言葉の札（引用を邪魔しない）・締めの字幕と終わりの問い（考える間に動く物を置かない）・
  語りの場面（手の映像と本人の声が入る）。
- 本物の画面を映す場面（玩具の頁・手帖）では、画面の右の紙の余白（幅 160px ほど）に立つ。画面の字や釦を隠さないため。
  輪の図では、輪の下と数の行（下の帯）の間を、少し小さく歩く。
- 切り出しは混んだ頁からなので、隣の人の線を拾わないよう、枠を絞ってから「墨のつながり」で本体だけを残す（種の点から塗り広げる）。
  頁の大きさに依らないよう、枠を決まった幅に直してから処理する。結果は時刻に依らないので、1 回だけ作って使い回す。
- 1 コマは時刻だけで決まる（frame(t) と同じ考え）。どの場面も書き出しの flip.render を通るので、そこで重ねる（場面ごとに書かない）。
"""
import functools
import json
import math
import pathlib

from PIL import Image, ImageDraw, ImageFilter, ImageOps

from demo.flip import FIGURES, H, SUMI, W, ease, fetch_image

PAGE, FIG = "v1-R0000013", "guide"
WORK_W = 616          # 切り出す前に枠をこの幅に直す（墨のつながりの太らせ方を、頁の大きさに依らない形にする）
GROW = 5              # 近い線をつなぐ太らせ方（px、WORK_W の上で）
FADE_IN = 0.4         # 溶けて現れる秒
BOB, STEP = 6, 0.5    # 歩く間の上下の揺れ（px）と、1 歩の秒

# 場面ごとの出方。keys: h（高さ px）、y（足もとの高さ）、walk（(秒, x の真ん中) の並び。間を歩く）、
# face（1 = 元の絵の向き。提灯は体の左上に掲げている。-1 = 左右を返す）、tilt（(止まって傾け始める秒, 角度)。正は左回り）
PLANS = {
    # 玩具の頁: 前提の札「型紙は正解ではなく、Claude が考えた仮説」の後、画面の右の余白へ入り、画面の方へ提灯を傾ける
    "scene3": {"h": 300, "y": H - 40, "walk": ((3.0, W + 80), (4.4, W - 82)), "face": 1, "tilt": (4.6, 4.0)},
    # 手帖（場面 8。前は作りながら見る頁を映していた）: 「こまった」で聞く画面が出る所で、右の余白に入って提灯を掲げる
    "core_make": {"h": 300, "y": H - 40, "walk": ((7.6, W + 80), (8.9, W - 82)), "face": 1, "tilt": (9.1, 4.0)},
    # 表と裏の境目「ここからは、裏のしくみ。」: 左から歩いて入り、字の左下で止まって、字の方へ提灯を傾ける
    "border": {"h": 300, "y": H - 90, "walk": ((0.3, -80), (1.8, 560)), "face": -1, "tilt": (1.9, -4.0)},
    # 持ちよる（場面 11）: 他の人が作った物の列のそばに右の余白から入り、提灯で列を照らす（窓口の決定 11-07。確かめの推し 3。おそわる相手を周囲に）
    "core_gallery": {"h": 300, "y": H - 40, "walk": ((0.8, W + 80), (2.2, W - 82)), "face": 1, "tilt": (2.4, 4.0)},
    # 輪の図: 輪の下を、4 つの輪を順に照らしながら右へ歩く（数の行の帯より上）
    # 高さ 200 だと提灯の先が輪の下の端に重なったので 180 にし、足もとを数の行（下の帯の字は H-78 から）のすぐ上に置いた（11-06 に絵で見た）
    # 11-07 の組み直しで、字幕は下の帯・数の行は上の帯になったので、上の帯と紙の列（上の端 296）の間を小さく歩く
    "core_loop": {"h": 150, "y": 290, "walk": ((2.4, 120), (12.4, 1500)), "face": -1, "tilt": (12.5, -3.0)},
}


def record():
    return json.loads(FIGURES.read_text(encoding="utf-8"))["pages"][PAGE]


def page_url(rec=None):
    return f'{(rec or record())["iiif"]}/full/full/0/default.jpg'


def cut(page, fig):
    """頁（灰色）から人物を切り出し、墨色の RGBA の切り絵にする。fig は figures.json の 1 人分（box_pct・seeds）。"""
    x, y, w, h = fig["box_pct"]
    box = (round(x / 100 * page.width), round(y / 100 * page.height), round((x + w) / 100 * page.width), round((y + h) / 100 * page.height))
    crop = page.crop(box)
    crop = crop.resize((WORK_W, max(1, round(crop.height * WORK_W / crop.width))), Image.LANCZOS)
    g = ImageOps.autocontrast(crop, cutoff=1).point(lambda v: 255 if v > 190 else v)
    ink = ImageOps.invert(g).point(lambda v: 255 if v > 70 else 0)
    mark = ink.filter(ImageFilter.MaxFilter(GROW))
    for fx, fy in fig["seeds"]:
        sx, sy = round(fx * mark.width), round(fy * mark.height)
        for r in range(40):  # 種の近くで墨のある所を探して、そこから塗る
            hit = next(((sx + dx, sy + dy) for dx in range(-r, r + 1) for dy in range(-r, r + 1)
                        if 0 <= sx + dx < mark.width and 0 <= sy + dy < mark.height and mark.getpixel((sx + dx, sy + dy)) == 255), None)
            if hit:
                ImageDraw.floodfill(mark, hit, 128)
                break
    keep = mark.point(lambda v: 255 if v == 128 else 0)
    alpha = Image.composite(ImageOps.invert(g), Image.new("L", g.size, 0), keep)
    bb = alpha.point(lambda v: 255 if v > 40 else 0).getbbox()
    layer = Image.new("RGBA", g.size, SUMI + (0,))
    layer.putalpha(alpha)
    return layer.crop(bb) if bb else layer


_CUT = {}


def figure(cache):
    """案内役の切り絵（1 回だけ作る）。頁の写しが無ければ取り寄せる（取れなければ OSError。黙って飛ばさない）。"""
    key = str(cache)
    if key not in _CUT:
        rec = record()
        path = pathlib.Path(cache) / f"{PAGE}.jpg"
        path.parent.mkdir(parents=True, exist_ok=True)
        fetch_image(page_url(rec), path)
        fig = next(f for f in rec["figures"] if f["id"] == FIG)
        with Image.open(path) as im:
            _CUT[key] = cut(im.convert("L"), fig)
    return _CUT[key]


@functools.lru_cache(maxsize=16)
def _sized(key, h, face):
    im = _CUT[key]
    im = im.resize((max(1, round(im.width * h / im.height)), h), Image.LANCZOS)
    return ImageOps.mirror(im) if face < 0 else im


def state(name, t):
    """場面 name の時刻 t の (x の真ん中, 足もとの y, 傾き, 濃さ)。出ない時は None。"""
    plan = PLANS.get(name)
    if plan is None:
        return None
    (t0, x0), (t1, x1) = plan["walk"]
    if t < t0:
        return None
    u = ease((t - t0) / (t1 - t0)) if t1 > t0 else 1.0
    x = x0 + (x1 - x0) * u
    walking = t0 <= t < t1
    lift = -BOB * abs(math.sin(math.pi * (t - t0) / STEP)) if walking else 0.0
    ts, deg = plan["tilt"]
    tilt = deg * ease((t - ts) / 0.6) if t >= ts else 0.0
    return x, plan["y"] + lift, tilt, ease((t - t0) / FADE_IN)


def overlay(img, name, t, cache):
    """場面の 1 コマに案内役を重ねる。出ない場面・時刻では img をそのまま返す。"""
    s = state(name, t)
    if s is None:
        return img
    x, y, tilt, v = s
    plan = PLANS[name]
    figure(cache)
    im = _sized(str(cache), plan["h"], plan["face"])
    if tilt:
        # 足もとの真ん中を軸に傾ける（提灯を掲げる腕ごと、体を少し傾ける）。回すと絵が広がるので、広げた分を足もとに合わせて置く
        pad = Image.new("RGBA", (im.width * 3, im.height * 2), SUMI + (0,))
        pad.paste(im, (im.width, 0), im)
        im = pad.rotate(tilt, resample=Image.BICUBIC, center=(pad.width / 2, im.height))
        ox, oy = pad.width / 2, im.height / 2
    else:
        ox, oy = im.width / 2, im.height
    if v < 1:
        im = im.copy()
        im.putalpha(im.getchannel("A").point(lambda a: round(a * v)))
    out = img.copy()
    out.paste(im, (round(x - ox), round(y - oy)), im)
    return out


class Guided:
    """場面に案内役を重ねる包み。frame(t) と duration・ground を元の場面から引き継ぐ。"""

    def __init__(self, scene, name, cache):
        self.scene, self.name, self.cache = scene, name, cache
        # duration・ground などは __getattr__ で元の場面から読む（元に無い物は無いままにして、呼ぶ側の既定に任せる）

    def frame(self, t):
        return overlay(self.scene.frame(t), self.name, t, self.cache)

    def __getattr__(self, k):
        return getattr(self.scene, k)
