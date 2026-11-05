"""スマホの幅 390 で、頭の帯の項目が 1 段に収まる（#303）。帯の字を替えても段を増やさない。ブラウザなしで、字の数と CSS から幅を見積もる。

なぜ見積もりか: ./run.sh はブラウザなしで動く決まり。本当の段は tests/measure_tap.py が手元の Chrome で測る（手で回す）。
日本語は 1 字を字の大きさ 1 つ分に数える。かなを詰める分（palt）は引かないので、実際より少し広く見積もる。
ラテン文字の 0.5 字分は English の実測（14px で 46px ほど）から取った。
"""
import re

from web import skin

WIDTH = 390
FONT_PX = 14  # TAP_FLOOR の .nav の字の大きさ（スマホの幅はこちらが効く）


def narrow_rule():
    """幅 480 以下の .nav の指定から、隙間と字間（em）を読む。"""
    rule = re.search(r"@media \(max-width:480px\)\{\.nav\{([^}]*)\}", skin.NAV_STYLE).group(1)
    gap = int(re.search(r"(?:^|;)gap:(\d+)px", rule).group(1))
    spacing = re.search(r"letter-spacing:([\d.]+)(?:em)?", rule)
    return gap, float(spacing.group(1))


def row_width(labels, gap, spacing):
    width = gap * (len(labels) - 1)
    for label in labels:
        for ch in label:
            width += FONT_PX * ((0.5 if ch.isascii() else 1) + spacing)
    return width


def room():
    # 帯の左右の余白は .nav の padding（5vw ずつ）
    assert "padding:16px 5vw" in skin.NAV_STYLE
    return WIDTH * 0.9


# 帯の字の大きさは、スマホの幅で FONT_PX のまま
assert f".nav{{font-size:{FONT_PX}px" in skin.TAP_FLOOR
gap, spacing = narrow_rule()
labels = [name for _, name in skin.NAV]
# 「うつし」は margin-right:100% で 1 段目に置くので、残りの項目だけで 1 段に収める
assert ".nav .brand{flex:none;white-space:nowrap;margin-right:100%}" in skin.NAV_STYLE
assert row_width(labels, gap, spacing) <= room(), ("帯が 390 で 1 段に収まらない", labels, row_width(labels, gap, spacing), room())
# 見積もりが効いている事: 長い字は落とす
assert row_width(["うつしとは", "作る（おもちゃを選ぶ）", "作った物と職人の言葉", "図鑑（読む）", "English"], gap, spacing) > room()
print("ok")
