"""入口の最初の画面（題の間）から「まずはここから」の 2 つへ送る仕掛け（本人の言葉 11-08「サイト、。新しい絵は作っていない。はトル。
トップページスクロールしてもらう仕掛けを。うつしの文字や周囲のひろい領域タップしてもスライドしても下にスクロールしおもちゃを選ばせる、
切り抜きした4つのおもちゃをタップしてもスクロールして2つのおもちゃを選ばせる。」・web.looks の DOWN・DOWN_JS）。

見る事（白と暗い版の両方）:
- 注記の「新しい絵は作っていない。」が頁（白・暗い版・黒の zine）と訳の表（英語・やさしい日本語）に無く、新しい鍵がある
- 題の間に下へ送る印 a.tj-down（href="#mazu"・見える字が無い・読み上げは今ある見出しの字「まずはここから」）。まずはここから に tabindex="-1"
- 送る台本: 題の間の click と touchend（上へのスライド）で送る・a や button などの押せる所は除き a.tj-down は送る・
  動きを減らす設定で smooth と auto を分ける・送った後に まずはここから へ focus・見えた時に起こす仕掛けは使わない
- 浮かぶ玩具は前のまま（リンクにしない・pointer-events:none。押すと題の間の click になる）
動き（押す・滑らせる・Enter で送る所）は、頁を開いて人が確かめた（帳面の節）。この試験は作りの線を見る。
"""
import json
import os
import pathlib
import re
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from web import looks, ukabu  # noqa: E402

OLD = "新しい絵は作っていない"
K_NEW = "図は国立国会図書館デジタルコレクションの頁（米山堂・{0} 年の複製）。"
for name, page in (("白", looks.tenji()), ("暗い版", looks.yoru())):
    assert OLD not in page, (name, "注記に 新しい絵は作っていない が残る")
    hall = page[page.index('<section class="tj-hall" id="hall">'): page.index("</section>", page.index('id="hall"'))]
    m = re.search(r'<a class="tj-down" href="#mazu" aria-label="([^"]*)">(.*?)</a>', hall, re.S)
    assert m, (name, "題の間に下へ送る印が無い")
    assert m.group(1) == looks.MAZU, (name, "読み上げは今ある見出しの字", m.group(1))
    assert not re.sub(r"<[^>]+>", "", m.group(2)).strip(), (name, "印に見える字を足さない（字を足すなら本人の確かめ）")
    assert '<section class="tj-mazu" id="mazu" tabindex="-1">' in page, (name, "まずはここから に focus を置けない")
    assert ".tj-hall>a.tj-down{position:absolute" in page and "width:48px;height:48px" in page, (name, "印の置き場と押せる大きさ")
    assert ".tj-hall>a.tj-down.on{position:fixed}" in page and ".tj-hall>a.tj-down.off{opacity:0;pointer-events:none}" in page, (name, "最初の画面に留め、送ったら消す")
    js = page[page.index("const h=document.getElementById('hall')"):]
    for want in ("addEventListener('click'", "closest('a,button,summary,input,label,select,textarea')", "classList.contains('tj-down')",
                 "touchstart", "touchend", "d>=30", "prefers-reduced-motion: reduce", "behavior:r?'auto':'smooth'", "scrollIntoView",
                 "m.focus({preventScroll:true})", "getSelection()", "classList.add('on')", "toggle('off',scrollY>40)"):
        assert want in js, (name, "送る台本に無い", want)
    assert "IntersectionObserver" not in page, (name, "見えた時に起こす仕掛けは使わない（research/19）")
    if '<div class="ukabu"' in page:  # 輪郭の絵が無い木（手元の out/ が空）では浮かぶ玩具を置かない（web.ukabu.block）
        block = page[page.index('<div class="ukabu"'):page.index('<a class="tj-down"')]
        assert "<a " not in block and 'aria-hidden="true"' in block, (name, "浮かぶ玩具はリンクにしない（本人の決め 11-07）")
    assert ".ukabu{" in ukabu.UKABU and "pointer-events:none" in ukabu.UKABU, "浮かぶ玩具は押すと下の題の間に当たる"
assert OLD not in looks.zine(), "黒の zine の注記にも残る"

en = json.loads((ROOT / "data/i18n/en.json").read_text(encoding="utf-8"))["strings"]
easy = json.loads((ROOT / "data/i18n/yasashii.d/1.json").read_text(encoding="utf-8"))["strings"]
for table, label in ((en, "英語"), (easy, "やさしい日本語")):
    assert K_NEW in table, (label, "新しい注記の鍵が無い")
    assert not any(OLD in k for k in table), (label, "前の注記の鍵が残る")
assert "new pictures" not in en[K_NEW] and "あたら" not in easy[K_NEW]
print("ok 入口の題の間から まずはここから へ送る: 印（字なし・まずはここから）・click と上へのスライド・動きを減らす設定・focus・注記の字（白と暗い版）")
