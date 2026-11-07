"""型紙の版が変わる場面の試作（demo.core_loop_ban）に映す、御来迎の版ごとの紙の絵を置き場（out/demo/ban/）へ入れる命令。

使い方: python -m demo.ban_take_in <刷った紙の置き場（共有の Drive の案件の頭）> [--dry-run]
exit: 0 = 入れた / 3 = 紙が見つからない・2 枚以上当たる（名指しする。入れない）/ 4 = 道具が無い・置き場が読めない

決めた事と理由:
- 映すのは御来迎の v10 → v14 の 5 枚だけ（窓口の決定 11-07。場面 15 は御来迎の版の並びだけで、虎は入れない）。
  どの版の紙かは、刷った紙の置き場の名前で決まる（版ごとに 1 枚。v11 は 2 つの形を刷ったうちの「つまみの形」で、版の歩みの本線の形）。
- 置き場の中の名前は、刷った時の頭の印（commit の短い印）を書かずに、版と種類だけで当てる（印は版が同じなら替わってもよい物で、
  repo に置く値ではない）。当たる紙が 0 枚か 2 枚以上なら、名指しして 3 で止める（違う紙を黙って映さない）。
- 紙の 1 頁目を pdftoppm で絵にし、まわりの白い余白を切る。切る枠は 5 枚の描いてある所を全部含む 1 つの枠にして、5 枚とも同じ枠で切る
  （1 枚ずつ切ると、描いてある所の少ない版の紙だけが小さく見え、並べた時に紙の大きさが変わったように見えた。11-07 に v13 で見た）。
  絵は git の外（out/）に置く。
"""
import argparse
import pathlib
import shutil
import subprocess
import sys
import tempfile

from PIL import Image, ImageChops

from demo.flip import ROOT

BAN_DIR = ROOT / "out/demo/ban"
# (置き場の名前, 刷った紙の置き場の中の当て方)。当て方は glob で、頭の印の所を * にした。
SOURCES = (
    ("goraigo-v10", "20261106-022348-workshop-print/必須_goraigo_H-A_v10.pdf"),
    ("goraigo-v11", "20261106-kaizen-print/刷る（型紙だけ）/御来迎_v11_つまみの形_型紙.pdf"),
    ("goraigo-v12", "20261106-print-now/古い刷り（使わない）/御来迎_v12_完成版*.pdf"),
    ("goraigo-v13", "20261106-print-now/古い刷り（使わない）/御来迎_v13_完成版*.pdf"),
    ("goraigo-v14", "20261106-print-now/御来迎_v14_完成版*.pdf"),
)
DPI = 150
WHITE_CUT = 245   # これより明るい所を余白とみなす（紙の地の白と、刷った時の薄い影を分ける値）
PAD = 12          # 切った後に残す余白（px）。線が絵の端に付かないように


def find(folder, pattern):
    """当て方に当たる紙。glob は [ と ] を字として扱わないので、当て方にそれを書かない。"""
    return sorted(pathlib.Path(folder).glob(pattern))


def drawn_box(img):
    """描いてある所の枠（白い余白の内側）。何も描かれていない頁は None。"""
    gray = img.convert("L").point(lambda v: 255 if v > WHITE_CUT else 0)
    return ImageChops.invert(gray).getbbox()


def union(boxes):
    boxes = [b for b in boxes if b]
    if not boxes:
        return None
    return (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))


def cut(img, box):
    if not box:
        return img
    l, t, r, b = box
    return img.crop((max(0, l - PAD), max(0, t - PAD), min(img.width, r + PAD), min(img.height, b + PAD)))


def page_image(pdf, tmp):
    """紙の 1 頁目の絵。できなければ (None, 理由の文)。"""
    stem = pathlib.Path(tmp) / pdf.stem.replace(" ", "_")
    r = subprocess.run(["pdftoppm", "-f", "1", "-l", "1", "-r", str(DPI), "-png", str(pdf), str(stem)], capture_output=True, text=True)
    pngs = sorted(pathlib.Path(tmp).glob(stem.name + "*.png"))
    if r.returncode != 0 or not pngs:
        return None, (r.stderr.strip()[:200] or "絵にできない")
    with Image.open(pngs[0]) as im:
        return im.convert("RGB"), None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("folder", help="刷った紙の置き場の頭（中に 20261106-print-now などが並ぶ所）")
    ap.add_argument("--dry-run", action="store_true", help="当たる紙を確かめるだけで、絵を作らない")
    a = ap.parse_args(argv)
    folder = pathlib.Path(a.folder)
    if not folder.is_dir():
        print(f"検査できない: 置き場が無い: {folder}", file=sys.stderr)
        return 4
    if not shutil.which("pdftoppm"):
        print("検査できない: pdftoppm が無い", file=sys.stderr)
        return 4
    found, bad = {}, []
    for name, pattern in SOURCES:
        hits = find(folder, pattern)
        if len(hits) != 1:
            bad.append(f"{name}: 当たる紙が {len(hits)} 枚（{pattern}）")
            continue
        found[name] = hits[0]
    if bad:
        for line in bad:
            print(f"FAIL D.ban {line}", file=sys.stderr)
        print("置き場には入れていない（紙を 1 枚ずつに決めてから、もう一度）", file=sys.stderr)
        return 3
    if a.dry_run:
        for name, pdf in found.items():
            print(f"当たる: {name} ← {pdf.name}")
        return 0
    BAN_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        pages = {}
        for name, pdf in found.items():
            img, err = page_image(pdf, tmp)
            if err:
                print(f"FAIL D.ban {name}: {err}", file=sys.stderr)
                return 3
            pages[name] = img
        sizes = {im.size for im in pages.values()}
        box = union(drawn_box(im) for im in pages.values()) if len(sizes) == 1 else None
        for name, img in pages.items():
            # 紙の大きさが違う時（A4 でない版が混じった時）は、同じ枠で切れないので切らずに置く
            cut(img, box).save(BAN_DIR / f"{name}.png")
            print(f"入れた: {name}.png ← {found[name].name}")
    print(f"置き場 {BAN_DIR}（{len(found)} 枚）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
