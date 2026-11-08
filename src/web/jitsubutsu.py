"""まずはここから の原図の周りに浮かぶ、実物のおもちゃ（本人の言葉 11-08「スクロールして、まずはここからの原図の周囲に、実際のおもちゃを抜き出して浮かべる。」）。

判断の芯:
- 絵は実物のおもちゃの写真から背景を抜いた透けた WebP。本人の答え（11-08）「サイトの実装も写真も、repo に入れる形でよい。」で、抜いた絵（位置の札 0 を
  確かめた物だけ）を repo の data/jitsubutsu/<名>.webp に入れる（元の写真は入れない）。CLAUDE.md の画像の決まりに 1 行足した。
  前の答え「実物のおもちゃの写真は、サイトだけに出す。」（repo の外に置く形）は、本人が取り消した。
  置き場に絵がある玩具だけを浮かべ、1 つも無ければ何も置かない（頁は崩れない・tests/test_mazu_real_toys.py が有り無しの両方を見る）。
- 本人の答え（11-08）「作った人の名は出さない。」で、作った人の名・屋号と、作った人を言う札は、頁にもこのコードにも書かない。絵は押せない飾りで alt も空。
- 位置の札（GPS）を含む EXIF は全部外す。写真の 8 枚とも位置の札が 13〜15 個あった。shrink が画素だけを新しい絵に写して保存する 1 か所で、
  元の info も exif も渡さない（tests/test_mazu_real_toys.py が、位置の札を付けた絵を通して札 0 を見る）。
- 背景を抜くのは repo の外の道具（rembg・MIT、モデルは Apache-2.0）。repo の依存は増やさない: cut は rembg が読める時だけ動き、無ければ 4 で終わる。
  入口の浮かぶ玩具の取り方（web.ukabu.mask_of・紙の地の色からの距離）では、手・机・壁が残った（11-08 に 8 枚で試した）。
  モデルは写真ごとに出来の良い方を選ぶ（isnet-general-use は手を外せたが、兎は板と棒ごと消した。u2net は兎の板を残したが影も残した）。
  兎の影は drop_shadow で外す（灰色で彩りが無く、半ば透けた画素。胴の白と板の茶色は残る）。手のひらが残った写真（蔵と坂）は使わない（統括の決め 11-08）。
- 頁の側は入口の浮かぶ玩具（web.ukabu）と同じ決まり: 置くまで見せない・JS の無い画面では出さない・幅が替わった時だけ置き直す（触って送っても動かない）・
  押せない飾り（aria-hidden・alt は空なので新しい字は無い）。置き直しの台本は ukabu.place_js("mazu", wide=True)。
- 置き場は、節（幅 980px まで）の外の左右の余白まで使う（wide）。狭い画面では 2 枚の札が幅いっぱいで余白が無く、置く所が無い玩具は出さない
  （帯を足して置く案 a は本人の確かめ待ち）。
"""
import io
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data/jitsubutsu"
BOX = (208, 330)  # 入口の浮かぶ玩具と同じ上限（見せる幅 104px の 2 倍まで）
QUALITY = 82
# 浮かべる実物（5 種・浮かべる場所の順）。名は見立てで、図鑑のどの玩具かは本人の確かめ待ち。
# 蔵と坂（俵ころがしの見立て）は手のひらが残ったので使わない（統括の決め 11-08）
PICKS = ("shishi", "tora", "neko", "kasa", "usagi")


def drop_shadow(im):
    """背景を抜いた後に残る、机の影（灰色で彩りが無く、半ば透けた画素）を透かす。im は RGBA。"""
    import numpy as np
    from PIL import Image, ImageFilter

    a = np.asarray(im.convert("RGBA")).astype(int)
    rgb, alpha = a[..., :3], a[..., 3]
    gray = (rgb.max(2) - rgb.min(2) < 14) & (rgb.max(2) < 150) & (alpha < 235)
    alpha = np.where(gray, 0, alpha).astype("uint8")
    out = im.convert("RGBA")
    out.putalpha(Image.fromarray(alpha).filter(ImageFilter.MedianFilter(3)))
    return out


def shrink(im):
    """浮かべる大きさの WebP（バイト）。画素だけを新しい絵に写し、EXIF（位置の札を含む）も元の info も渡さない。"""
    from PIL import Image

    im = im.convert("RGBA")
    box = im.getchannel("A").point(lambda v: 255 if v > 40 else 0).getbbox()
    if box:
        im = im.crop(box)
    im.thumbnail(BOX)
    clean = Image.new("RGBA", im.size)
    clean.paste(im)
    buf = io.BytesIO()
    clean.save(buf, "WEBP", quality=QUALITY, method=6)
    return buf.getvalue()


def cut(photo, model="isnet-general-use", shadow=False):
    """写真（パス）から背景を抜いて浮かべる WebP（バイト）。rembg が無ければ None。"""
    try:
        from rembg import new_session, remove
    except ImportError:
        return None
    from PIL import Image, ImageOps

    with Image.open(photo) as src:
        im = ImageOps.exif_transpose(src).convert("RGB")
    got = remove(im, session=new_session(model))
    return shrink(drop_shadow(got) if shadow else got)


def block():
    """浮かぶ実物の層（まずはここから の節の中に置く・揺れるだけの飾り）。絵がある物だけ。1 つも無ければ空。"""
    from .skin import esc

    have = [n for n in PICKS if (OUT / f"{n}.webp").exists()]
    if not have:
        return ""
    toys = "".join(f'<span class="uk jb{i}"><img src="/jitsubutsu/{esc(n)}.webp" alt="" loading="lazy" decoding="async" fetchpriority="low"></span>'
                   for i, n in enumerate(have, 1))
    return f'<div class="ukabu ukabu-mazu" aria-hidden="true">{toys}</div>'


# 浮かぶ形（入口の浮かぶ玩具の .uk の大きさと揺れを使う）。CSS の注は頁に出るので、理由はここに書く:
# - 節に position:relative を付け、節の中の字と札を層より前にする（入口の題の間と同じ組み）
# - 置き場の札の名は jb1〜jb5（入口の題の間の uk1〜uk4 と頭を分ける。tests/test_ukabu.py は class="uk uk の数で題の間の外に置かない事を見る）
# - 置く前の位置は、2 枚の札の左右の外（節の外の余白）。台本が層を画面の幅いっぱいに広げてから、字と札に重ならない近い所へ置き直す
# - 幅は 72px（1300px より広い画面は 100px）。iPad の横 1180 では札の外の余白が 92px で、字と札との間合い 12px と縁 4px を引くと 72px までしか入らない
#   （入口の浮かぶ玩具と同じ 104px では 2 つしか出なかった・11-08 に測った）
MAZU = """
.tj-mazu{position:relative}
.tj-mazu>*:not(.ukabu){position:relative;z-index:1}
.ukabu-mazu .uk{width:72px}
@media (min-width:1300px){.ukabu-mazu .uk{width:100px}}
.jb1{left:2%;top:10%;animation-duration:21s}.jb2{right:2%;top:16%;animation-duration:18s;animation-delay:-7s}
.jb3{left:4%;top:48%;animation-duration:24s;animation-delay:-3s}.jb4{right:3%;top:56%;animation-duration:19s;animation-delay:-12s}
.jb5{left:6%;top:78%;animation-duration:22s;animation-delay:-9s}
"""


def main(argv=None):
    """python -m web.jitsubutsu cut <写真> <名> [--model <名>] [--shadow]。名は PICKS の 1 つ。書き出すのは data/jitsubutsu/<名>.webp だけ。"""
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) < 3 or argv[0] != "cut" or argv[2] not in PICKS:
        print("python -m web.jitsubutsu cut <写真> <名（" + "・".join(PICKS) + "）> [--model isnet-general-use|u2net] [--shadow]", file=sys.stderr)
        return 4
    model = argv[argv.index("--model") + 1] if "--model" in argv else "isnet-general-use"
    data = cut(argv[1], model=model, shadow="--shadow" in argv)
    if data is None:
        print("背景を抜く道具（rembg）が読めない。repo の外の venv で回す", file=sys.stderr)
        return 4
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{argv[2]}.webp").write_bytes(data)
    print(argv[2], len(data))
    return 0


if __name__ == "__main__":
    sys.exit(main())
