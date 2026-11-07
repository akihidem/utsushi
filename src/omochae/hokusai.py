"""サイトに出す『北斎漫画』の絵を取り込む（本人の決定 2026-11-05、#262: 案 1・2・3 を全部入れる）。

判断の芯:
- 絵の出所は権利を確かめた国立国会図書館の物だけ（PDM。data/hokusai/README.md）。記録は data/hokusai/figures.json と
  data/hokusai/scene4_sources.json を読み、文と枠を二重に持たない。前はデモ動画の作りの置き場に同じ物を置いて読んでいたが、
  動画の作りを repo の外へ移した（本人の言葉 11-08「この動画の作成はギットハブに入ってる？入れなくていいと思う」）ので、字を替えずにサイト側へ移した。
- 絵は描き直さず切り出すだけ。描き直すと北斎の線でなくなる（data/hokusai/README.md）。
- 画像は repo に入れない。取り込みの時に IIIF から取り、out/sources/hokusai に置く（out/ は git の外）。
- 取れない時に起動を止めない。頁は絵の代わりに国立国会図書館への道を出す。
"""
import json
import urllib.request

from PIL import Image

from .hypotheses import ROOT

DIR = ROOT / "out/sources/hokusai"
FLIP_PAGE = "v6-R0000020"
WHEEL_PAGE = "v8-R0000011"
LINES_PAGE = "v3-R0000022"
TIMEOUT = 60


def pages():
    """頁の記録。{頁の名: 記録}。切り出しは crops に {id, box_pct} で揃える。"""
    out = {}
    fig = json.loads((ROOT / "data/hokusai/figures.json").read_text(encoding="utf-8"))["pages"]
    for name, rec in fig.items():
        out[name] = {**rec, "crops": rec["figures"]}
    out.update(json.loads((ROOT / "data/hokusai/scene4_sources.json").read_text(encoding="utf-8"))["pages"])
    return out


def figure_ids():
    """パラパラに使う 18 人の印。並びは記録の順（動画と同じ）。"""
    return [c["id"] for c in pages()[FLIP_PAGE]["crops"]]


def names():
    """頁が出してよい絵の名前。道の許しの一覧にも使う。"""
    out = []
    for name, rec in pages().items():
        out.append(name)
        out += [f'{name}-{c["id"]}' for c in rec["crops"]]
    return out


def path_of(name):
    return DIR / f"{name}.jpg"


def has(name):
    return path_of(name).exists()


def crop(page_path, box_pct, out):
    """box_pct は頁の画像に対する割合 [左, 上, 幅, 高さ]。画像の大きさに依らない（動画と同じ記録）。"""
    with Image.open(page_path) as im:
        w, h = im.size
        x, y, bw, bh = box_pct
        box = (round(w * x / 100), round(h * y / 100), round(w * (x + bw) / 100), round(h * (y + bh) / 100))
        im.convert("RGB").crop(box).save(out, "JPEG", quality=88)


def _fetch_page(rec, out):
    data = urllib.request.urlopen(f'{rec["iiif"]}/full/full/0/default.jpg', timeout=TIMEOUT).read()
    tmp = out.with_suffix(".part")
    tmp.write_bytes(data)
    with Image.open(tmp) as im:
        im.verify()  # 壊れた写しを正しい名前で残さない。残すと以後ずっと開けないため
    tmp.replace(out)


def fetch():
    """足りない絵だけを取る。取れなかった頁の名を返す（1 枚の失敗で残りを止めない）。"""
    DIR.mkdir(parents=True, exist_ok=True)
    failed = []
    for name, rec in pages().items():
        page = path_of(name)
        try:
            if not page.exists():
                _fetch_page(rec, page)
            for c in rec["crops"]:
                piece = path_of(f'{name}-{c["id"]}')
                if not piece.exists():
                    crop(page, c["box_pct"], piece)
        except (OSError, ValueError) as e:
            print(f"北斎漫画の絵を取れない: {name}（{e}）")
            failed.append(name)
    return failed
