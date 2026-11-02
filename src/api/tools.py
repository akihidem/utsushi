"""Claude に渡す道具。どれも決定的で、repo の外へ書かず、決まった資料だけを読む。"""
import json
import pathlib
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
SIDE_RANGE = {"L": (0.0, 50.0), "R": (50.0, 100.0)}


class ToolInputError(ValueError):
    """道具の入力が決まりの外。理由を Claude に返して直させる。"""


def zoom_url(source, x, y, w, h, width=1000):
    """対象の頁の中の領域だけを IIIF で切り出す URL を作る。x・y・w・h は見開き全体に対する %。

    なぜ頁の中に限るか: 隣の頁の別の玩具を根拠に混ぜないため。Web を自由に見せず、権利を確かめた資料だけを読ませる。
    """
    lo, hi = SIDE_RANGE[source["side"]]
    if not (lo <= x and x + w <= hi and 0 <= y and y + h <= 100 and w > 0 and h > 0):
        raise ToolInputError(f"領域 x={x} y={y} w={w} h={h} が頁の範囲 x={lo}〜{hi}・y=0〜100 の外")
    if not 200 <= width <= 1600:
        raise ToolInputError(f"幅 {width} は 200〜1600 の外")
    base = source["image_url"].split("/pct:")[0]
    return f"{base}/pct:{x},{y},{w},{h}/{width},/0/default.jpg"


def zoom_source(source_id, x, y, w, h, width=1000):
    """切り出した絵を out/zoom に置いてパスを返す。同じ領域は取り直さない（NDL に負担をかけず、再現もできる）。"""
    path = ROOT / "data/sources" / f"{source_id}.json"
    if not path.exists():
        raise ToolInputError(f"出典の記録が無い: {source_id}")
    source = json.loads(path.read_text(encoding="utf-8"))
    url = zoom_url(source, x, y, w, h, width)
    out = ROOT / "out/zoom" / f"{source_id}_{x}_{y}_{w}_{h}_{width}.jpg"
    if not out.exists():
        out.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(url, timeout=60) as r:
            out.write_bytes(r.read())
    return out


def list_contributions(source_id=None):
    """公開済みの持ち寄りを前例として返す。確かさの種類を付けたまま渡し、事実として扱わせない。"""
    from omochae.contrib import public_list

    keep = ("id", "kind", "role", "certainty", "body", "origin", "where_when", "toy_name", "source_id")
    return [{k: c[k] for k in keep if k in c} for c in public_list(source_id)]
