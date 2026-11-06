"""文字の幅をフォントから測る。

なぜ測るか: SVG の text は幅を持たないので、測らないと右にはみ出しても重なっても検査を通ってしまう。
"""
import functools
import subprocess

from fontTools.ttLib import TTCollection, TTFont

from .model import ToolMissing

FAMILY = "Noto Serif CJK JP"


@functools.lru_cache(maxsize=1)
def _font():
    try:
        path = subprocess.run(["fc-match", FAMILY, "file"], capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError) as e:
        raise ToolMissing(f"fc-match が使えない: {e}")
    path = path.strip().removeprefix(":file=")
    if "NotoSerifCJK" not in path:
        raise ToolMissing(f"字 {FAMILY} が無い（fc-match の答え: {path}）")
    if path.endswith((".ttc", ".otc")):
        fonts = TTCollection(path, lazy=True).fonts
    else:
        fonts = [TTFont(path, lazy=True)]
    for f in fonts:
        if f["name"].getDebugName(1) == FAMILY:
            return f.getBestCmap(), f["hmtx"], f["head"].unitsPerEm
    raise ToolMissing(f"{path} の中に {FAMILY} が無い")


def text_width(s, size):
    cmap, hmtx, upem = _font()
    total = 0
    for ch in s:
        glyph = cmap.get(ord(ch))
        # 字形の無い文字は全角で数える。狭く見積もると重なりを見逃すので広い側に倒す。
        total += hmtx[glyph][0] if glyph else upem
    return total * size / upem


# 縦に積む札の 1 字の箱の高さ（字の大きさの倍率）と、空白の間（字の大きさの倍率）。
# 細い部品に長い名を入れるため（虎の 5 重りの腕、本人の決定 11-07）。箱は字の大きさより少しだけ高くし、字どうしが触れない間を取る。
# 空白は 1 字ぶん空けると番号と名が離れて別の札に見えるので、3 分の 1 にした。
V_PITCH = 1.1
V_SPACE = 1 / 3


def stack(s, size):
    """縦に 1 字ずつ積む札の並び。Returns ([(dy, 字, 字の幅)], 全体の高さ)。dy は札の上の端から字の箱の上の端まで（mm）。
    字の幅は text_width で測る（凍結の床の standin が _font を置き換えるので、字幅の置き換えもここに効く）。"""
    out, y = [], 0.0
    for ch in s:
        if ch == " ":
            y += size * V_SPACE
            continue
        out.append((y, ch, text_width(ch, size)))
        y += size * V_PITCH
    return out, y


def wrap(s, size, max_width):
    """1 字ずつ送って折り返す。日本語の禁則は扱わない（型紙の短い文なので、見て困ったら足す）。"""
    lines, cur = [], ""
    for ch in s:
        if cur and text_width(cur + ch, size) > max_width:
            lines.append(cur)
            cur = ch
        else:
            cur += ch
    if cur:
        lines.append(cur)
    return lines
