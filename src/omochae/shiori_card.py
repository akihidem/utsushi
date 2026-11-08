"""しおりの紙（表と裏を 1 頁の同じ面に並べる）を描く決定的な生成器（本人の答え 11-08「しおりは型紙の PDF に一緒に刷る。」・「しおりは同じ面に刷る。」）。
設計は grove の state/shiori-in-sheet-20261108.md の 2.1 版（別の目の確かめ 2 回）と、前のしおりの設計（state/techo-card-20261108/README.md の 2″・2‴・3）。

判断の芯:
- **表だけを刷る**（本人の答え 11-08「表だけに印刷にしたい」・押す順の絵は表に移す (ア)）。A4 縦の頁のまん中に 50×150mm の 1 枚。
  外の線は実線（切る）と角の印、上に紐を通す穴の印。表に原画・押す順の 9 つの絵と朱の ①②③・鍵の字の 2 行・題字と玩具の名・QR。裏の頁と裏の字は無い。
  前の「同じ面に並べて折る」形の頁の頭の断りと切り方の 1 行は、折らなくなったので外した（新しい字は足さない・本人の答え）。
  しおりの写真 1 枚に QR と押す順の両方が写る（本人が表だけを選んだ）。開いて見えるのは、そのしおりに結ばれた記録だけ（安全の事項 1・11 への対応）。
- **QR は道だけ**（<決まった番地>/s/<印>）。印の 22 字は字で刷らない（字を読む道具で拾われないように・別の目の気づき）。
  QR は墨を地に寄せた茶（前の見本 B の色）・四角の点・誤りの直しは M。点は形（path）で描き、絵にしない（どの大きさで刷っても角が立つ）。
- 描くのはこの機械の中だけ（Claude は SVG と PDF を描かない・CLAUDE.md）。SVG を作り、頁ごとに cairosvg で PDF にし、pypdf で合わせる（render と同じ道）。
- **型紙の頁は書き直さない**（merge）。置いてある型紙の PDF の頁を、そのまま前に置き、しおりの 1 頁を後ろに足すだけ。
- **PDF の中に手元の道や機械の名を残さない**: 合わせた PDF の情報は題だけにし、作った道具の名（Producer）も入れない。
- 原画（国立国会図書館の PDM の絵）は git の外（out/sources）なので、無い所では絵の枠だけを描いて刷る（hypotheses と同じ扱い）。
  絵は小さくしてから埋める（PDF を重くしない・写真の付帯情報は描き直しで落ちる）。
- 字は設計の 6 節の一覧のまま（どれも本人の確かめ待ち）。替える時はこの上の定数だけを替える。
"""
import base64
import io
import pathlib

import cairosvg
import pypdf
import segno
from PIL import Image

from .textfit import FAMILY

ROOT = pathlib.Path(__file__).resolve().parents[2]
PAGE_W, PAGE_H = 210.0, 297.0          # A4 縦（mm）
CARD_W, CARD_H = 50.0, 150.0           # しおりの大きさ（前の設計の 3 節）
CARD_X, CARD_Y = (PAGE_W - CARD_W) / 2, 40.0  # しおりの左上（頁のまん中）
QR_MM = 22.0                           # QR の一辺（前の設計の 4 節の見本 B）
QR_COLOR = "#544230"                   # 墨を地に寄せた茶
VERMILION = "#c8381e"                  # 順の印の朱

TITLE = "うつし"
# 鍵の字（本人の答え 11-08「しおりに鍵の字を足してください。」・前に本人の確かめ待ちだった字そのまま）。表だけにした後、鍵である事と、なくした時に
# どうするかの字が 1 枚に無くなったため（別の目の #740 の気づき）。句点で 2 行に分けて、9 つの絵の下・題字と QR の上に置く
KEY_LINE = ("このしおりは手帖の鍵です。", "なくしたら、進め役に言ってください。")
MARKS = ("①", "②", "③")
PICTURES = 9


def _esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _picture(path, px):
    """絵を小さくして JPEG の data URI にする。無ければ None（枠だけを描く）。"""
    if not path or not pathlib.Path(path).exists():
        return None
    im = Image.open(path).convert("RGB")
    im.thumbnail((px, px * 2))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=80)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def _image(uri, x, y, w, h):
    if uri:
        return f'<image x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" preserveAspectRatio="xMidYMid meet" href="{uri}"/>'
    # 原画が無い所では枠だけ（刷った後に何の絵か分からなくなるが、鍵としては順の印の位置だけで足りる）
    return f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" fill="none" stroke="#999" stroke-width="0.2"/>'


def _text(s, x, y, size, anchor="middle", fill="#222"):
    return f'<text x="{x:.2f}" y="{y:.2f}" font-family="{FAMILY}" font-size="{size:.2f}" text-anchor="{anchor}" fill="{fill}">{_esc(s)}</text>'


def _vertical(s, x, y, size):
    """縦書き（1 字ずつ下へ）。cairosvg の縦書きの指定に頼らず、どの表示でも同じ形にする。"""
    return "".join(_text(ch, x, y + i * size * 1.1, size) for i, ch in enumerate(s))


NAME_SIZE = 4.5      # 玩具の名の字の大きさ（mm・入る名はこのまま）
NAME_TOP = 116.0     # 縦書きの名の 1 字目の行の位置（しおりの上の端から mm）
NAME_ROOM = CARD_H - 3.0 - NAME_TOP  # 最後の字の下の端までに使える長さ（しおりの下の切る線の 3mm 手前まで）


NAME_MIN = 2.5       # 縮める時の下限（mm・統括の決め 11-08）


def _fit(name):
    """字の数から、最後の字の下の端がしおりの下の切る線の 3mm 手前に収まる大きさ（_vertical の 1 字の送り 1.1 と字の下の出 0.15）。"""
    return NAME_ROOM / ((max(len(name), 1) - 1) * 1.1 + 0.15)


def name_fit(name):
    """縦書きの玩具の名の（刷る字, 字の大きさ）。統括の決め 11-08（別の目の #742 の確かめ: 長い名がしおりの下の切る線を越えて、切ると欠けた）:
    - 入る名は NAME_SIZE のまま、字も替えない（御来迎・虎など）
    - 入らない名は、字の数で縮めて入れる（NAME_MIN まで）
    - NAME_MIN でも越える名は、終わりの括弧の組（「（…）」）を 1 つずつ外して入れる（括弧の中を刷らない・前の括弧の読みはなるべく残す）"""
    text = name
    while _fit(text) < NAME_MIN:
        i = text.rfind("（")
        if i < 0 or not text.endswith("）"):
            break
        text = text[:i].rstrip()
    return text, max(NAME_MIN, min(NAME_SIZE, _fit(text)))


def _frame():
    """切る線（実線）と角の印と、穴の印（紐を通す丸）。"""
    x, y, w, h = CARD_X, CARD_Y, CARD_W, CARD_H
    corners = ""
    for cx, cy, dx, dy in ((x, y, -1, -1), (x + w, y, 1, -1), (x, y + h, -1, 1), (x + w, y + h, 1, 1)):
        corners += (f'<line x1="{cx + dx * 1.5:.2f}" y1="{cy:.2f}" x2="{cx + dx * 5:.2f}" y2="{cy:.2f}" stroke="#222" stroke-width="0.25"/>'
                    f'<line x1="{cx:.2f}" y1="{cy + dy * 1.5:.2f}" x2="{cx:.2f}" y2="{cy + dy * 5:.2f}" stroke="#222" stroke-width="0.25"/>')
    return (f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" fill="none" stroke="#222" stroke-width="0.3"/>' + corners +
            f'<circle cx="{x + w / 2:.2f}" cy="{y + 8:.2f}" r="2.5" fill="none" stroke="#666" stroke-width="0.25"/>')


def _qr(url, x, y):
    """QR を形で描く（点は四角・余白は描かず、しおりの地を余白にする。周りの 4 点ぶんの空きは置き場で取る）。"""
    qr = segno.make(url, error="m", micro=False)
    m = qr.matrix
    n = len(m)
    u = QR_MM / n
    d = "".join(f"M{x + c * u:.3f} {y + r * u:.3f}h{u:.3f}v{u:.3f}h{-u:.3f}z" for r, row in enumerate(m) for c, v in enumerate(row) if v)
    return f'<path d="{d}" fill="{QR_COLOR}"/>'


def _svg(body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{PAGE_W}mm" height="{PAGE_H}mm" viewBox="0 0 {PAGE_W} {PAGE_H}">'
            f'<rect width="{PAGE_W}" height="{PAGE_H}" fill="white"/>{body}</svg>')


def card_svg(sid, name, url, order, sources, ids):
    """しおりの 1 頁（表だけ）: 原画・押す順の 9 つの絵（並びは開く頁と同じ）と 3 つに朱の ①②③・題字と玩具の名（縦書き）・右下に QR。"""
    x, y = CARD_X, CARD_Y
    pic = _picture(pathlib.Path(sources) / f"{sid}.jpg", 360)
    body = _image(pic, x + 4, y + 14, CARD_W - 8, 40)
    cell, gap = 13.0, 2.0
    gx = x + (CARD_W - (3 * cell + 2 * gap)) / 2
    for i, pid in enumerate(ids):
        cx, cy = gx + (i % 3) * (cell + gap), y + 58 + (i // 3) * (cell + gap)
        body += _image(_picture(pathlib.Path(sources) / f"{pid}.jpg", 110), cx, cy, cell, cell)
        if i in order:
            # 順の印は絵の左上に朱で（白い丸を下に敷いて、絵の色に埋もれないように）
            body += (f'<circle cx="{cx + 2.6:.2f}" cy="{cy + 2.6:.2f}" r="2.6" fill="white"/>' +
                     _text(MARKS[order.index(i)], cx + 2.6, cy + 4.1, 4.4, fill=VERMILION))
    # 9 つの絵（下の端 y+101）と題字（y+116 から）の間に鍵の字の 2 行（1 行 18 字まで・2.2mm で しおりの幅 42mm の内）
    body += "".join(_text(line, x + CARD_W / 2, y + 105.2 + i * 3.4, 2.2) for i, line in enumerate(KEY_LINE))
    # 題字と玩具の名は鍵の字の 2 行の下から（縦書きの 1 字目の上の端が 2 行目に重ならないよう 4mm 下げた）
    shown, size = name_fit(name)
    body += (_vertical(TITLE, x + 8, y + NAME_TOP, 6) + _vertical(shown, x + 15.5, y + NAME_TOP, size) +
             _qr(url, x + CARD_W - 4 - QR_MM, y + CARD_H - 4 - QR_MM))
    return _svg(_frame() + body)


def _info(writer, title):
    # 合わせた PDF の情報は題だけ（手元の道・機械の名・作った道具の名を入れない）
    writer.metadata = {"/Title": title}


def pages(sid, token, order, version, made_at, base, name=None, sources=None, ids=None):
    """しおりの 1 頁（表だけ）の PDF（bytes）。order は 9 つの絵の番号 0〜8 から 3 つの順（omochae.shiori.make の order）。
    base は決まった番地（shiori.base_url）。無い時は刷らない（替わる番地の QR を刷ると、後で開かなくなるため）。"""
    if not base:
        raise ValueError("決まった番地が無いので、しおりを刷らない")
    order = tuple(order)
    if len(order) != 3 or len(set(order)) != 3 or not all(0 <= i < PICTURES for i in order):
        raise ValueError("順は 0〜8 から 3 つ")
    if name is None:
        from . import hypotheses
        name = hypotheses.load(sid)["toy"]
    if ids is None:
        from web.shiori_open import PICTURE_IDS as ids  # 開く頁と同じ並び（1 か所の値）
    sources = sources or ROOT / "out/sources"
    url = f"{base.rstrip('/')}/s/{token}"
    writer = pypdf.PdfWriter()
    svg = card_svg(sid, name, url, order, sources, ids)  # version と made_at は、裏の字（版と刷った日）を外したので使わない（呼ぶ側の形は替えない）
    writer.append(pypdf.PdfReader(io.BytesIO(cairosvg.svg2pdf(bytestring=svg.encode("utf-8")))))
    # cairosvg は絵をそのままの画素で埋めるので（1MB ほど）、しおりの頁の絵だけを JPEG に詰め直す（型紙の頁は触らない）
    for page in writer.pages:
        for img in page.images:
            img.replace(img.image.convert("RGB"), quality=80)
    _info(writer, "うつし しおり")
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def merge(sheet_pdf_path, card_pdf_bytes):
    """置いてある型紙の PDF の後ろに、しおりの 1 頁を足した PDF（bytes）。型紙の頁は書き直さない（頁をそのまま写す）。"""
    writer = pypdf.PdfWriter()
    writer.append(pypdf.PdfReader(str(sheet_pdf_path)))
    writer.append(pypdf.PdfReader(io.BytesIO(card_pdf_bytes)))
    _info(writer, "うつし")
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()
