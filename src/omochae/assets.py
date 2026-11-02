"""型紙に載せる原図の切り出しを NDL から作る。結果は data/assets に commit してある。

なぜ commit するか: 図は PDM で、通信なしで clone から型紙を刷れるようにするため。作り直す時だけこれを走らせる。
領域は research と J-005 で画像を見て決めた。絵の切り抜きの点は雛形と同じ物を使う。
"""
import io
import json
import pathlib
import urllib.request

from PIL import Image, ImageDraw

from .templates.slider_fan import _RAW

ROOT = pathlib.Path(__file__).resolve().parents[2]
BASE = "https://dl.ndl.go.jp/api/iiif/1187053/R0000005"
TUBE_REGION = "pct:19.0,65.5,7.6,22.5"


def fetch(region, width):
    with urllib.request.urlopen(f"{BASE}/{region}/{width},/0/default.jpg", timeout=60) as r:
        return Image.open(io.BytesIO(r.read())).convert("RGB")


def main():
    out = ROOT / "data/assets"
    out.mkdir(exist_ok=True)
    meta = {}
    tube = fetch(TUBE_REGION, 274)
    # 絵の筒は角を手前に描かれ、面の幅が縮んで見える。平らな面に戻すため横に伸ばし、面の縦横比（30:84）にそろえる。
    for name, box in (("goraigo_tube_left.jpg", (42, 60, 130, 620)), ("goraigo_tube_right.jpg", (172, 60, 244, 620))):
        tube.crop(box).resize((300, 840), Image.LANCZOS).save(out / name, quality=88)
        meta[name] = {"source_id": "NDL-1187053-R0000005-L", "iiif_region": TUBE_REGION, "crop_px_at_width_274": box, "changes": "切り出し・横に伸ばす"}
    fig = fetch("pct:21.0,58.4,3.6,8.8", 260)
    scale = 4
    mask = Image.new("L", (fig.width * scale, fig.height * scale), 0)
    ImageDraw.Draw(mask).polygon([(x * scale, y * scale) for x, y in _RAW], fill=255)
    mask = mask.resize(fig.size, Image.LANCZOS)
    white = Image.new("RGB", fig.size, "white")
    Image.composite(fig, white, mask).crop((36, 33, 213, 505)).save(out / "goraigo_figure.png")
    meta["goraigo_figure.png"] = {"source_id": "NDL-1187053-R0000005-L", "iiif_region": "pct:21.0,58.4,3.6,8.8", "changes": "切り出し・輪郭で切り抜き・拡大"}
    # 撮影の黒い背景を入れない範囲で頁を切る。
    page_region = "pct:4.5,4.5,45,90"
    fetch(page_region, 600).save(out / "goraigo_page.jpg", quality=80)
    meta["goraigo_page.jpg"] = {"source_id": "NDL-1187053-R0000005-L", "iiif_region": page_region, "changes": "切り出し・縮小"}
    (out / "assets.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
