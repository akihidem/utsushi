"""玩具の頁（つくる の頁）の頭の組み替え（本人の言葉 11-08「サイト、つくる、のところ。…」）。

本人の言葉: 「原文の引用確かめた人要らない。国立図書館デジタルコレクションの文言はページの一番下に。大きく見る、図を見る、は統一して国会図書館へのリンクへ。
絵の左横に縦で狂歌、その左横に御来迎 江都二色よりーの部分を置く。図鑑のページ要らない。ぐずし字を読む、のところは、現代語訳や関連する言葉の意味を書く。
ほかのおもちゃ、のリンク要らない。」

見る線:
1. 原文の引用の「確かめた人」の行が無い
2. 国立国会図書館デジタルコレクションの出典の字（所蔵・コマ・権利）は頁の一番下（頁の終わりの出典の段）にだけある。字は替えない
3. 「大きく見る」と「図を見る」は 1 つ（図を見る（国立国会図書館））で、行き先は国立国会図書館のその絵の頁（dl.ndl.go.jp/pid/…/1/<コマ>）。絵そのものも同じ所へ
4. 頭の原画の部品は、左から 題の塊（玩具の名・『江都二色』より・作者・刊年）→ 狂歌 → 絵 の順で、題の塊と狂歌は縦書き
5. 頭に「図鑑の頁」と「ほかのおもちゃ」の道が無い。「くずし字を読む」は残る
6. くずし字を読む の頁に、現代語訳と言葉の意味の置き場がある（data/kuzushi_notes/<印>.json がある時だけ出す。書くのは別の担当）
"""
import json
import os
import pathlib
import re
import tempfile

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()

from web import kuzushi, toy  # noqa: E402
from web.play_server import sources  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
G, T = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"
QUIET = "NDL-1187053-R0000013-L-5"  # 歌の読みが無い玩具（亀）

for sid in (G, T, QUIET):
    src = json.loads((ROOT / "data/sources" / f"{sid}.json").read_text(encoding="utf-8"))
    page = toy.toy_page(sid)
    head = re.search(r'<section class="hero">.*?</section>', page, re.S).group(0)
    # 1
    assert "確かめた人" not in head and "原文の引用" not in head, (sid, "原文の引用の確かめた人が残った")
    # 2: 出典の字は頁の一番下の段にだけ
    holding = src["holding"]
    assert holding not in head, (sid, "出典の字が頭に残った")
    foot = re.search(r'<section class="sec ndl-credit">(.*?)</section>', page, re.S)
    assert foot and holding in foot.group(1) and "パブリック・ドメイン（PDM）" in foot.group(1), (sid, "頁の一番下に出典の字が無い")
    tail = page[page.index('class="sec ndl-credit"'):]
    assert "<section" not in tail[1:], (sid, "出典の段の後ろに別の段がある")
    # 3: 1 つの道で国立国会図書館のその絵の頁へ
    ndl = f"https://dl.ndl.go.jp/pid/{src['persistent_id'].rsplit('/', 1)[1]}/1/{src['canvas']}"
    assert "大きく見る" not in head, (sid, "大きく見る が残った")
    assert head.count("図を見る（国立国会図書館）") == 1, (sid, head.count("図を見る（国立国会図書館）"))
    assert f'href="{ndl}"' in head and f'/picture/{sid}/page"' not in head.replace(f'src="/picture/{sid}/page"', ""), (sid, "国立国会図書館の頁への道で無い")
    # 5
    assert f'href="/zukan/{sid}"' not in head and "図鑑の頁" not in head and "ほかのおもちゃ" not in head, (sid, "図鑑の頁 か ほかのおもちゃ の道が残った")
    assert f'href="/zukan/{sid}/yomi"' in page, (sid, "くずし字を読む が無い")

# 4: 題の塊 → 狂歌 → 絵 の順・縦書き
page = toy.toy_page(G)
fig = re.search(r'<figure class="genga genga-head".*?</figure>', page, re.S).group(0)
tate = re.search(r'<div class="genga-tate">(.*?)</div></div>', fig, re.S)
assert tate, "題の塊と狂歌の縦の段が無い"
t, s_, p_ = fig.index('class="genga-title"'), fig.index('class="genga-songs"'), fig.index('class="genga-pic"')
assert t < s_ < p_, (t, s_, p_)
title = re.search(r'<div class="genga-title">(.*?)</div>', fig, re.S).group(1)
assert "御来迎" in title and "『江都二色』より" in title, title
css = "".join(re.findall(r"<style>(.*?)</style>", page, re.S))
assert re.search(r"\.genga-head \.genga-tate\{[^}]*\}", css) and ".genga-head .genga-title{writing-mode:vertical-rl" in css and ".genga-head .genga-songs{writing-mode:vertical-rl" in css

# 6: くずし字を読む の置き場
notes = ROOT / "data/kuzushi_notes" / f"{G}.json"
before = kuzushi.page(G)
had = notes.exists()
if not had:
    assert 'id="yomi-notes"' not in before, "書く物が無いのに置き場の見出しが出た"
    notes.parent.mkdir(parents=True, exist_ok=True)
    notes.write_text(json.dumps({"gendaigo": "試しの訳", "words": [{"word": "御来迎", "meaning": "試しの意味"}]}, ensure_ascii=False), encoding="utf-8")
try:
    after = kuzushi.page(G)
    sec = re.search(r'<section class="yomi-notes" id="yomi-notes">(.*?)</section>', after, re.S)
    assert sec and "現代語訳" in sec.group(1) and "言葉の意味" in sec.group(1), "現代語訳と言葉の意味の置き場が無い"
    if not had:
        assert "試しの訳" in sec.group(1) and "試しの意味" in sec.group(1)
finally:
    if not had:
        notes.unlink()
        if not any(notes.parent.iterdir()):
            notes.parent.rmdir()
print("ok 玩具の頁の頭: 確かめた人なし・出典は頁の一番下・図を見るは国立国会図書館の頁へ 1 つ・題の塊と狂歌は絵の左に縦・図鑑の頁とほかのおもちゃの道なし・くずし字の置き場")
