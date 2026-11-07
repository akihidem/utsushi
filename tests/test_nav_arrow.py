"""頭の帯の駅の間に、流れの印（skin.ROAD_ARROW）を置く（夕方のレビュー 11-07 の 11）。

なぜ: 帯は駅の名が並ぶだけで、えらぶ の後に つくる、つくる の後に のこす、と進む事が読めなかった。駅の名と並びは本人の決定（11-06）なので
替えず、駅と駅の間に印を置くだけにする。印は読み上げない飾り（aria-hidden）で、押す所でもない。道の外（よむ・English）の前には置かない。
帯の段を増やさない事（幅 320 と 390 で 1 段）は、tests/test_nav_fit.py と同じ見積もりで見る。
"""
import re

from web import skin

G = "NDL-1187053-R0000005-L"
PATHS = {"/": "/", "/toys": "/toys", f"/toy/{G}": "", f"/toy/{G}/techo/kiroku": "", "/gallery": "/gallery", "/about": "/about"}
for path, current in PATHS.items():
    nav = skin.nav(skin.DEFAULT, current, path)
    # 先に並び: 駅の間にだけ印がある（印の字は下で見る。前の形では印が無く、ここで落ちる）
    seq = [a or b or ("ARROW" if c else "") for a, b, c in re.findall(r'<a [^>]*>([^<]+)</a>|<span class="nav-step"[^>]*>([^<]+)</span>|(<span class="nav-arrow")', nav)]
    assert seq == ["うつし", "えらぶ", "ARROW", "つくる", "ARROW", "のこす", "ARROW", "もちよる", "よむ", "やさしい", "English"], (path, seq)  # やさしい は 11-07 夜
    ARROW = f'<span class="nav-arrow" aria-hidden="true">{skin.ROAD_ARROW}</span>'
    assert nav.count(ARROW) == len(skin.ROAD) - 1, (path, "印は読み上げない飾りで、駅の間にだけ")
    assert not re.search(r"<a [^>]*>[^<]*" + re.escape(skin.ROAD_ARROW), nav), (path, "印はリンクの中に入れない")
# 英語の頁の帯は替えない（範囲の外）
assert skin.ROAD_ARROW not in skin.nav(skin.DEFAULT, "", "/en", lang="en")

# 帯の段を増やさない: 幅 320 と 390 で、うつし の後の項目が 1 段に収まる（見積もりは test_nav_fit と同じ形）
FONT_PX = 14
rule = re.search(r"@media \(max-width:480px\)\{\.nav\{([^}]*)\}", skin.NAV_STYLE).group(1)
gap = int(re.search(r"(?:^|;)gap:(\d+)px", rule).group(1))
spacing = float(re.search(r"letter-spacing:([\d.]+)(?:em)?", rule).group(1))
pull = int(re.search(r"@media \(max-width:480px\)\{[^@]*\.nav \.nav-arrow\{margin:0 -(\d+)px\}", skin.NAV_STYLE).group(1))
labels = [*sum(([n, skin.ROAD_ARROW] for n in skin.ROAD), [])[:-1], skin.YOMU[1]]
width = gap * (len(labels) - 1) + sum(FONT_PX * ((0.5 if ch.isascii() else 1) + spacing) for label in labels for ch in label) - 2 * pull * (len(skin.ROAD) - 1)
for screen in (320, 390):
    assert width <= screen * 0.9, (screen, "帯が 1 段に収まらない", width)

# 英語の帯（全頁の英語・#538）: 駅の名は訳の表から読む（訳が替わっても見積もりが付いてくる）。ラテン文字は手元の Chrome の実測
# （14px で 1 字 7.8〜9.3px）から 0.6 字に見る（test_nav_fit の 0.5 字より厚め）。幅 480 以下の英語の頁の横の隙間は html[lang=en] .nav の column-gap（段の間は替えない）
import json  # noqa: E402

from omochae.hypotheses import ROOT  # noqa: E402

words = json.loads((ROOT / "data/i18n/en.json").read_text(encoding="utf-8"))["strings"]
en_labels = [*sum(([words[n], skin.ROAD_ARROW] for n in skin.ROAD), [])[:-1], words[skin.YOMU[1]]]
m = re.search(r"@media \(max-width:480px\)\{[^@]*html\[lang=en\] \.nav\{column-gap:(\d+)px\}", skin.NAV_STYLE)
en_gap = int(m.group(1)) if m else gap  # 決まりが無ければ日本語と同じ隙間（下の確かめで落ちる）
en_width = en_gap * (len(en_labels) - 1) + sum(FONT_PX * ((0.6 if ch.isascii() else 1) + spacing) for label in en_labels for ch in label) - 2 * pull * (len(skin.ROAD) - 1)
assert en_gap < gap, "英語の帯だけ、狭い幅の横の隙間を詰める（日本語の帯は替えない）。詰めないと幅 320 の余りが 6px しかなかった（手元の Chrome）"
for screen in (320, 390):
    assert en_width <= screen * 0.9, (screen, "英語の帯が 1 段に収まらない", en_labels, en_width)
print("ok: 頭の帯の駅の間に流れの印がある（読み上げず・押さず・段を増やさない）")
