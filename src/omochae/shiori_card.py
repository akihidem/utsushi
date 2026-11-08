"""しおりの紙（表と裏を 1 頁の同じ面に並べる）を描く決定的な生成器（本人の答え 11-08「しおりは型紙の PDF に一緒に刷る。」・「しおりは同じ面に刷る。」）。
設計は grove の state/shiori-in-sheet-20261108.md の 2.1 版（別の目の確かめ 2 回）と、前のしおりの設計（state/techo-card-20261108/README.md の 2″・2‴・3）。

判断の芯:
- **表と裏は 1 頁の同じ面に並べる**（本人の答え 11-08「しおりは同じ面に刷る。」・設計の 1 節の (b′)）。A4 縦の頁のまん中に 100×150mm の帯を
  1 本置き、左半分が表、右半分が裏（どちらも上向き）。外の線は実線（切る）、まん中の縦の線は点線（折る）。刷っていない面どうしを合わせて
  折って貼ると、表と裏が外を向く（縦の線を軸に裏返すと、裏の字は上向きのまま）。片面刷りで済む。穴の印は両方の半分のまん中の上にあり、
  折ると重なる。切る前の紙の写真 1 枚に QR（表）と順の ①②③（裏）が両方写るので（別の目の止め 1・本人が同じ面を選んだ）、頁の頭に
  写真に写さない断りを置く（字は本人の確かめ待ち）。
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
import datetime
import io
import pathlib
import zoneinfo

import cairosvg
import pypdf
import segno
from PIL import Image

from .textfit import FAMILY

ROOT = pathlib.Path(__file__).resolve().parents[2]
PAGE_W, PAGE_H = 210.0, 297.0          # A4 縦（mm）
CARD_W, CARD_H = 50.0, 150.0           # しおりの大きさ（前の設計の 3 節）
STRIP_X, STRIP_Y = (PAGE_W - 2 * CARD_W) / 2, 40.0  # 帯（表と裏の 2 枚ぶん・100×150mm）の左上。まん中の線が頁のまん中
FOLD_X = STRIP_X + CARD_W               # 折る線（点線）。左が表、右が裏
QR_MM = 22.0                           # QR の一辺（前の設計の 4 節の見本 B）
QR_COLOR = "#544230"                   # 墨を地に寄せた茶
VERMILION = "#c8381e"                  # 順の印の朱
TZ = zoneinfo.ZoneInfo("Asia/Tokyo")

TITLE = "うつし"
# 裏の字（設計の 6 節の 3〜5・本人の確かめ待ち）
BACK_LINES = ("この裏は、人に見せないでください。写真にうつさないでください。",
              "このしおりは手帖の鍵です。なくしたら、進め役に言ってください。",
              "いちばん新しく刷ったしおりだけが使えます。")
PAGE_HEAD = "刷ったら、すぐ切って折ってください。この頁を写真にうつさないでください。"  # 頁の頭（6 節の 7′・同じ面の形に合わせた字・本人の確かめ待ち）
CUT_LINE = "外の線で切り、まん中の点線で折って、のりではり合わせます。"  # 帯の下（6 節の 7・同じ面の形に合わせた字・本人の確かめ待ち）
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


def _wrap(s, per):
    """per 字ごとに折る。行の頭に句読点が来る時は前の行に送る（簡単な禁則）。"""
    out = []
    for i in range(0, len(s), per):
        part = s[i:i + per]
        while part and part[0] in "。、）」" and out:
            out[-1] += part[0]
            part = part[1:]
        if part:
            out.append(part)
    return out


def _frame():
    """帯の外の切る線（実線）と、まん中の折る線（点線）と、角の印と、2 つの穴の印（折ると重なる）。"""
    x, y, w, h = STRIP_X, STRIP_Y, 2 * CARD_W, CARD_H
    corners = ""
    for cx, cy, dx, dy in ((x, y, -1, -1), (x + w, y, 1, -1), (x, y + h, -1, 1), (x + w, y + h, 1, 1)):
        corners += (f'<line x1="{cx + dx * 1.5:.2f}" y1="{cy:.2f}" x2="{cx + dx * 5:.2f}" y2="{cy:.2f}" stroke="#222" stroke-width="0.25"/>'
                    f'<line x1="{cx:.2f}" y1="{cy + dy * 1.5:.2f}" x2="{cx:.2f}" y2="{cy + dy * 5:.2f}" stroke="#222" stroke-width="0.25"/>')
    holes = "".join(f'<circle cx="{hx:.2f}" cy="{y + 8:.2f}" r="2.5" fill="none" stroke="#666" stroke-width="0.25"/>' for hx in (x + CARD_W / 2, FOLD_X + CARD_W / 2))
    return (f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" fill="none" stroke="#222" stroke-width="0.3"/>' + corners + holes +
            f'<line x1="{FOLD_X:.2f}" y1="{y:.2f}" x2="{FOLD_X:.2f}" y2="{y + h:.2f}" stroke="#666" stroke-width="0.25" stroke-dasharray="1.5 1.2"/>' +
            _text(CUT_LINE, PAGE_W / 2, y + h + 12, 3.5))


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


def front_body(sid, name, url, sources):
    """表（帯の左半分）: 原画・題字と玩具の名（縦書き）・右下に QR。"""
    x, y = STRIP_X, STRIP_Y
    pic = _picture(pathlib.Path(sources) / f"{sid}.jpg", 360)
    return (_image(pic, x + 4, y + 14, CARD_W - 8, 84) +
            _vertical(TITLE, x + 8, y + 108, 6) + _vertical(name, x + 15.5, y + 108, 4.5) +
            _qr(url, x + CARD_W - 4 - QR_MM, y + CARD_H - 4 - QR_MM))


def back_body(sid, name, order, version, made_at, sources, ids):
    """裏（帯の右半分）: 9 つの絵（並びは開く頁と同じ）・3 つに朱の ①②③・裏の字・玩具の名と型紙の版と刷った日。"""
    x, y = FOLD_X, STRIP_Y
    cell, gap = 14.0, 2.0
    gx = x + (CARD_W - (3 * cell + 2 * gap)) / 2
    grid = ""
    for i, pid in enumerate(ids):
        cx, cy = gx + (i % 3) * (cell + gap), y + 16 + (i // 3) * (cell + gap)
        grid += _image(_picture(pathlib.Path(sources) / f"{pid}.jpg", 110), cx, cy, cell, cell)
        if i in order:
            # 順の印は絵の左上に朱で（白い丸を下に敷いて、絵の色に埋もれないように）
            grid += (f'<circle cx="{cx + 2.6:.2f}" cy="{cy + 2.6:.2f}" r="2.6" fill="white"/>' +
                     _text(MARKS[order.index(i)], cx + 2.6, cy + 4.1, 4.4, fill=VERMILION))
    lines = ""
    ly = y + 16 + 3 * cell + 2 * gap + 9
    for s in BACK_LINES:
        for part in _wrap(s, 13):
            lines += _text(part, x + 3, ly, 3.2, anchor="start")
            ly += 4.4
        ly += 2.0
    day = datetime.datetime.fromtimestamp(made_at, TZ)
    foot = (_text(f"{name} 型紙の版 {version}", x + CARD_W / 2, y + CARD_H - 11, 3.2) +
            _text(f"{day.year}年{day.month}月{day.day}日", x + CARD_W / 2, y + CARD_H - 6, 3.2))
    return grid + lines + foot


def page_svg(sid, name, url, order, version, made_at, sources, ids):
    """しおりの 1 頁: 頁の頭の断り・帯（表と裏）・帯の下の切り方。"""
    head = _text(PAGE_HEAD, PAGE_W / 2, STRIP_Y - 14, 3.5)
    return _svg(head + _frame() + front_body(sid, name, url, sources) + back_body(sid, name, order, version, made_at, sources, ids))


def _info(writer, title):
    # 合わせた PDF の情報は題だけ（手元の道・機械の名・作った道具の名を入れない）
    writer.metadata = {"/Title": title}


def pages(sid, token, order, version, made_at, base, name=None, sources=None, ids=None):
    """しおりの 1 頁（表と裏を同じ面に並べる）の PDF（bytes）。order は 9 つの絵の番号 0〜8 から 3 つの順（omochae.shiori.make の order）。
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
    svg = page_svg(sid, name, url, order, version, made_at, sources, ids)
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
