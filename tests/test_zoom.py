"""絵を拡大する道具の範囲の検査。通信はしない（検査の結果が NDL の状態に左右されないように）。"""
import sys

from api.tools import ToolInputError, zoom_url

L = {"side": "L", "image_url": "https://example.test/iiif/R0000005/pct:0,0,50,100/1600,/0/default.jpg"}
R = {"side": "R", "image_url": "https://example.test/iiif/R0000014/pct:50,0,50,100/1600,/0/default.jpg"}


def rejected(*a, **k):
    try:
        zoom_url(*a, **k)
    except ToolInputError:
        return True
    return False


assert zoom_url(L, 7, 72, 27, 18) == "https://example.test/iiif/R0000005/pct:7,72,27,18/1000,/0/default.jpg"
assert zoom_url(R, 50, 0, 50, 100, 1600).startswith("https://example.test/iiif/R0000014/pct:50,0,50,100/1600,")
assert rejected(L, 40, 0, 20, 10), "左の頁から右の頁へはみ出す"
assert rejected(R, 40, 0, 20, 10), "右の頁から左の頁へはみ出す"
assert rejected(L, 0, 95, 10, 10), "下へはみ出す"
assert rejected(L, 0, 0, 0, 10), "幅 0"
assert rejected(L, 0, 0, 10, 10, width=5000), "大きすぎる画像"
sys.exit(0)
