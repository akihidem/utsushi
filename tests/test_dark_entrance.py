"""暗い画面の版の入口（本人の決め 11-08「もう1つ立てる」・統括の頼み 11-08「入口も白と同じ作り（縦の題字・まずはここから・小さい写し）で
色だけ暗くする」）の試験。

見る事:
1. 皮 zine のサイトの入口（looks.PAGES["zine"]）は yoru で、作りは白の入口と同じ（題の間 tj-hall・縦の題字・まずはここから の 2 枚・
   全部のおもちゃの節・浮かぶ玩具の置き場）。体の字（style を除く）は白の入口と一字も同じ
2. 色だけが違う: 白の入口の地と字の色（#fcfcfa・#2b2722・#1f1b17・#fffefc・#ebe8e2）が CSS に残らない。帯の変数は皮 zine の物（--bg:#0b0a09）
3. body の印は tenji yoru（白の入口の CSS の選び body.tenji をそのまま効かせ、暗い版を yoru で見分ける）
4. 入口の絵は小さい写し（/picture/<印>/mid）で、白と同じ
"""
import os
import re
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from web import looks  # noqa: E402

assert looks.PAGES["zine"] is looks.yoru and looks.PAGES["tenji"] is looks.tenji
for photos in (True, False):
    white, dark = looks.tenji(photos), looks.yoru(photos)
    body = lambda h: re.sub(r"<style>.*?</style>", "", h, flags=re.S)  # noqa: E731
    assert body(white).replace('<body class="tenji">', "") == body(dark).replace('<body class="tenji yoru">', ""), "作りと字は白と同じ"
    for part in ('class="tj-hall"', "<h1>うつし</h1>", "まずはここから", 'id="all-toys"'):
        assert part in dark, part
    css = "".join(re.findall(r"<style>(.*?)</style>", dark, re.S)).lower()
    assert not [c for c in ("#fcfcfa", "#2b2722", "#1f1b17", "#fffefc", "#ebe8e2") if c in css], "白の地と字の色が残らない"
    assert "--bg:#0b0a09" in css and '<body class="tenji yoru">' in dark
    assert re.findall(r"/picture/[^\"')]+/mid", white) == re.findall(r"/picture/[^\"')]+/mid", dark), "入口の絵は白と同じ小さい写し"
print("ok 暗い画面の版の入口: 作りと字は白と同じで、色だけ暗い（帯は皮 zine の変数・body は tenji yoru・絵は小さい写し）")
