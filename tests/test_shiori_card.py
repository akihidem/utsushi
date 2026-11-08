"""しおりの紙の生成器（omochae.shiori_card・本人の答え 11-08「しおりは型紙の PDF に一緒に刷る。」・設計 2.1 版の 1・6・7.2 節）。

なぜ: しおりは手帖の鍵なので、刷った紙の形が鍵の守りそのもの。表と裏が 1 頁の同じ面に並ぶ形（本人の答え 11-08「しおりは同じ面に刷る。」）で、
QR の行き先が決まった番地と印だけか・印の字を刷っていないか・順の印が裏の半分だけにあるか・型紙の頁を書き直していないか・PDF の情報に手元の道が
無いかを、刷った PDF から確かめる。
見る事:
1 1 頁（A4 縦）。表の半分（帯の左）の QR は「決まった番地/s/<印>」（300dpi で描いて、点の並びが segno の符号と同じ。読む道具があれば読んだ字も同じ）
2 印の 22 字は字で刷らない。①②③ は裏の半分（帯の右）だけ。題字と玩具の名は表の半分。頁の頭の断りと帯の下の切り方
3 原画がある所では表に 1 枚・裏に 9 枚の絵が入り、無い所では枠だけで刷れる
4 merge は型紙の頁の中身を替えず、後ろに 1 頁を足すだけ
5 PDF の情報は題だけ（手元の道・機械の名・作った道具の名が無い）
6 決まった番地が無い・順の形が違う時は刷らない
終了: 0 = 通る / 1 = 落ちる（assert）/ 4 = 刷った PDF を読む道具か字が無い（確かめられない）
"""
import io
import os
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile

if not (shutil.which("pdftoppm") and shutil.which("pdftotext")):
    print("検査できない: pdftoppm か pdftotext が無い", file=sys.stderr)
    sys.exit(4)

import cairosvg  # noqa: E402
import pypdf  # noqa: E402
import segno  # noqa: E402
from PIL import Image  # noqa: E402

from omochae import shiori_card as sc  # noqa: E402
from omochae.model import ToolMissing  # noqa: E402

G = "NDL-1187053-R0000005-L"
# 試しの印は回すたびに作る（本物と同じ shiori.make の作り方・22 字）。決まった字の印を repo に置かない（鍵らしい字を残さない）
TOKEN = secrets.token_urlsafe(16)
BASE = "https://utsushi.konoba.workers.dev"
URL = f"{BASE}/s/{TOKEN}"
ORDER = (2, 7, 4)
IDS = tuple(f"P{i}" for i in range(9))
tmp = tempfile.mkdtemp()
src = os.path.join(tmp, "sources")
os.makedirs(src)
for name in (G, *IDS):
    Image.new("RGB", (120, 200), (200, 180, 150)).save(os.path.join(src, f"{name}.jpg"))

try:
    pdf = sc.pages(G, TOKEN, ORDER, 3, 1794120000, BASE, name="御来迎", sources=src, ids=IDS)
except ToolMissing as e:
    print(f"検査できない: {e}", file=sys.stderr)
    sys.exit(4)
path = os.path.join(tmp, "card.pdf")
open(path, "wb").write(pdf)
r = pypdf.PdfReader(io.BytesIO(pdf))

# ---- 1 1 頁・A4 縦・QR
assert len(r.pages) == 1, len(r.pages)
for p in r.pages:
    w, h = float(p.mediabox.width), float(p.mediabox.height)
    assert abs(w - 595.28) < 1 and abs(h - 841.89) < 1, (w, h)
subprocess.run(["pdftoppm", "-r", "300", "-f", "1", "-l", "1", "-png", "-singlefile", path, os.path.join(tmp, "front")], check=True)
front = Image.open(os.path.join(tmp, "front.png")).convert("L")
matrix = segno.make(URL, error="m", micro=False).matrix
n = len(matrix)
x0, y0 = sc.STRIP_X + sc.CARD_W - 4 - sc.QR_MM, sc.STRIP_Y + sc.CARD_H - 4 - sc.QR_MM
assert x0 + sc.QR_MM <= sc.FOLD_X, "QR は表の半分（折る線の左）"
mm = 300 / 25.4
drawn = [[front.getpixel((int((x0 + (c + 0.5) * sc.QR_MM / n) * mm), int((y0 + (rr + 0.5) * sc.QR_MM / n) * mm))) < 128 for c in range(n)] for rr in range(n)]
assert drawn == [[bool(v) for v in row] for row in matrix], "表の半分の QR の点の並びが、決まった番地/s/<印> の符号と違う"
decoded = None
try:
    import cv2  # 入っている機械だけ（requirements には入れない）

    decoded = cv2.QRCodeDetector().detectAndDecode(cv2.imread(os.path.join(tmp, "front.png")))[0]
except ImportError:
    if shutil.which("zbarimg"):
        decoded = subprocess.run(["zbarimg", "-q", "--raw", os.path.join(tmp, "front.png")], capture_output=True, text=True).stdout.strip()
if decoded is None:
    print("測れない: QR を読む道具（OpenCV か zbarimg）が無い（点の並びは segno の符号と同じ事を確かめた）")
else:
    assert decoded == URL, decoded

# ---- 2 印を字で刷らない・①②③ は裏の半分だけ
pt = 72 / 25.4


def half(x_mm, w_mm):
    """頁の縦の帯（x_mm から w_mm の幅・帯の上から下まで）の字。表の半分と裏の半分を分けて見る。"""
    args = ["-x", str(int(x_mm * pt)), "-y", str(int(sc.STRIP_Y * pt)), "-W", str(int(w_mm * pt)), "-H", str(int(sc.CARD_H * pt))]
    return subprocess.run(["pdftotext", *args, path, "-"], capture_output=True, text=True, check=True).stdout


whole = subprocess.run(["pdftotext", path, "-"], capture_output=True, text=True, check=True).stdout
left, right = half(sc.STRIP_X, sc.CARD_W - 0.5), half(sc.FOLD_X + 0.5, sc.CARD_W - 0.5)
assert TOKEN not in whole and TOKEN.encode() not in pdf, "印の 22 字を字で刷っている"
assert all(m in right for m in sc.MARKS) and not any(m in left for m in sc.MARKS), "順の印は裏の半分（折る線の右）だけ"
# 題字と玩具の名は縦書きの 2 列なので、字を取り出すと行ごとに混ざる。題字は 1 字ずつ見る
assert all(ch in left for ch in sc.TITLE + "御来迎"), "表の半分に題字と玩具の名"
assert sc.PAGE_HEAD in whole.replace("\n", "") and sc.CUT_LINE in whole.replace("\n", ""), "頁の頭の写さない断りと、帯の下の切り方"
# 「いちばん新しく刷ったしおりだけが使えます。」は、刷り直しで前のしおりを使えなくする所が入るまで刷らない（前に刷ったしおりも開くので事実と合わない・統括の決め 11-08）
assert "いちばん新しく刷った" not in whole.replace("\n", ""), "前のしおりも開く今の作りで、いちばん新しい物だけが使えると刷っている"
flat = right.replace("\n", "")
assert all(line in flat for line in sc.BACK_LINES) and "型紙の版 3" in flat and "2026年11月8日" in flat, "裏の字・版・刷った日（東京の日付）"

# ---- 3 絵の数
assert [len(p.images) for p in r.pages] == [10], [len(p.images) for p in r.pages]
empty = os.path.join(tmp, "none")
os.makedirs(empty)
bare = pypdf.PdfReader(io.BytesIO(sc.pages(G, TOKEN, ORDER, 3, 1794120000, BASE, name="御来迎", sources=empty, ids=IDS)))
assert len(bare.pages) == 1 and [len(p.images) for p in bare.pages] == [0], "原画が無い所では枠だけで刷る"

# ---- 4 merge は型紙の頁を書き直さない
sheet = os.path.join(tmp, "sheet.pdf")
cairosvg.svg2pdf(bytestring=b'<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 210 297"><rect x="20" y="20" width="50" height="80" fill="none" stroke="black"/></svg>', write_to=sheet)
merged = pypdf.PdfReader(io.BytesIO(sc.merge(sheet, pdf)))
orig = pypdf.PdfReader(sheet)
assert len(merged.pages) == len(orig.pages) + 1, len(merged.pages)
assert merged.pages[0].get_contents().get_data() == orig.pages[0].get_contents().get_data(), "型紙の頁の中身が替わった"

# ---- 5 PDF の情報
host = socket.gethostname()
for doc, raw in ((r, pdf), (merged, sc.merge(sheet, pdf))):
    meta = dict(doc.metadata or {})
    assert set(meta) <= {"/Title"}, meta
    assert b"/home" not in raw and host.encode() not in raw and b"/Producer" not in raw, "手元の道・機械の名・作った道具の名を入れない"

# ---- 6 刷らない時
for kw in ({"base": ""}, {"order": (1, 1, 2)}, {"order": (0, 4, 9)}, {"order": (0, 1)}):
    args = {"base": BASE, "order": ORDER, **kw}
    try:
        sc.pages(G, TOKEN, args["order"], 3, 1794120000, args["base"], name="御来迎", sources=empty, ids=IDS)
        raise AssertionError(("刷ってはいけない形で刷った", kw))
    except ValueError:
        pass
print("ok: しおりは表と裏を 1 頁の同じ面に並べる・QR は決まった番地/s/<印>・印の字を刷らず順の印は裏の半分だけ・型紙の頁は替えず・PDF の情報は題だけ")
