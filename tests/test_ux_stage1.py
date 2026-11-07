"""UX の見直しの段 1（本人の決定 11-06、docs/process/research/36-road-and-audience.md）のうち、撮影の前に入れる分。

見る事:
1. 頭の帯は道しるべ: うつし｜えらぶ つくる のこす もちよる｜よむ。前の帯の名（序・おもちゃ・作った物と職人の言葉・図鑑・English）は帯に無い
2. 今いる駅に印（aria-current）: 一覧 = えらぶ、玩具の頁と手帖の作る頁の頭 = つくる、手帖の記録の頁 = のこす、ギャラリー = もちよる、序・図鑑・保護者の頁 = よむ
3. つくる・のこす は玩具を選んだ後の駅なので、玩具の頁の中でだけ押せる（その玩具の頁・手帖の記録の頁へ）。選ぶ前は押せない段の印（字だけ）
4. 持ち寄る駅（ギャラリー）の頭に「もう 1 つ つくる」が 1 つ（えらぶへ）。次の玩具は勧めない
5. よむ（序の頁）の頭に、前は帯にあった 図鑑・English と、保護者の方へ、ファシリテーターの方へ の頁への道（今の名前のまま）
6. 英語の頁の帯は変えない（J-030 の段 1）。字は決まった言葉だけ（新しい字は足さない）
"""
import os
import re
import tempfile
import threading
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ.pop("ANTHROPIC_API_KEY", None)

from web import play_server, skin  # noqa: E402

G = "NDL-1187053-R0000005-L"
ROAD = ("えらぶ", "つくる", "のこす", "もちよる")  # 本人の決定の字（research/36）。一字も変えない

server = play_server.serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"


def get(path):
    with urllib.request.urlopen(base + path, timeout=120) as r:
        return r.read().decode("utf-8", "replace")


def nav_of(page):
    return re.search(r'<nav class="nav">(.*?)</nav>', page, re.S).group(1)


def items(nav):
    """帯の字と、押せるか・印。"""
    out = []
    for m in re.finditer(r'<a([^>]*)>([^<]+)</a>|<span class="nav-step"[^>]*>([^<]+)</span>', nav):
        if m.group(3):
            out.append((m.group(3), None, False))
        else:
            href = re.search(r'href="([^"]+)"', m.group(1)).group(1)
            out.append((m.group(2), href, 'aria-current="page"' in m.group(1)))
    return out


EXPECT = {"/toys": "えらぶ", f"/toy/{G}": "つくる", f"/toy/{G}/techo/kiroku": "のこす", "/gallery": "もちよる", "/about": "よむ", "/zukan": "よむ", "/otona": "よむ"}
for path, station in EXPECT.items():
    nav = nav_of(get(path))
    got = items(nav)
    assert [x[0] for x in got] == ["うつし", *ROAD, "よむ", "English"], (path, "帯は道しるべと、右の端の言語の切り替え", got)
    assert [x[0] for x in got if x[2]] == [station], (path, "今いる駅に印", got)
    # 行き先は今の頁の英語（?lang=en。全頁の英語・窓口の決め 130735 の案 B）
    assert '<a class="nav-lang" href="?lang=en" lang="en">English</a>' in nav, (path, "English は言語の切り替え（窓口の決定 11-06）。駅の印は付けない")
    for old in ("序", "おもちゃ", "作った物と職人の言葉", "図鑑"):
        assert f">{old}<" not in nav, (path, "前の帯の名は帯に無い", old)
    links = {x[0]: x[1] for x in got}
    if path.startswith("/toy/"):
        assert links["つくる"] == f"/toy/{G}" and links["のこす"] == f"/toy/{G}/techo/kiroku", (path, "玩具の頁の中では つくる・のこす が押せる", links)
    else:
        assert links["つくる"] is None and links["のこす"] is None, (path, "玩具を選ぶ前は つくる・のこす は押せない段の印", links)
    assert links["えらぶ"] == "/" and links["もちよる"] == "/gallery" and links["よむ"] == "/about" and links["English"] == "?lang=en", (path, links)  # 今の頁の英語へ（全頁の英語・窓口の決め 130735 の案 B）
# 入口: 帯は同じで、印は「えらぶ」（入口が えらぶ の駅。本人のサイト体験レビュー 11-07 の 4）。「うつし」には印を付けない（同じ頁に印を 2 つ置かない）
entry = items(nav_of(get("/")))
assert [x[0] for x in entry if x[2]] == ["えらぶ"], entry
# 英語の頁の帯は変えない
assert ">日本語<" in nav_of(get("/en")) and ">えらぶ<" not in nav_of(get("/en"))

# ---- 4 もう 1 つ つくる
gallery = get("/gallery")
assert gallery.count(">もう 1 つ つくる<") == 1 and '<p class="road"><a class="go" href="/">もう 1 つ つくる</a></p>' in gallery, "持ち寄る駅の頭に 1 つ"
assert gallery.index("もう 1 つ つくる") < gallery.index('id="ageta"'), "頭に置く"
# 頭の「入口へ」は外した（窓口の決め 11-07）。入口へ行く口は「もう 1 つ つくる」の 1 つ（同じ所へ行く釦の対を置かない。本人のサイト体験レビュー 11-07 の 3）
head = gallery[gallery.index('<div class="gallery">'):gallery.index('id="ageta"')]
assert head.count('href="/"') == 1, ("ギャラリーの頭で入口へ行く口は 1 つ", head.count('href="/"'))

# ---- 5 よむ（序の頁）
about = get("/about")
yomu = re.search(r'<p class="links yomu">(.*?)</p>', about).group(1)
assert [h for h in re.findall(r'href="([^"]+)"', yomu)] == ["/zukan", "/otona", "/en"], yomu
assert re.findall(r">([^<]+)</a>", yomu) == ["図鑑", "保護者の方へ、ファシリテーターの方へ", "English"], "今の名前のまま"
server.shutdown()
assert skin.ROAD == ROAD and skin.YOMU == ("/about", "よむ"), "帯の字は 1 か所（skin）に置く"
print("ok 段 1: 頭の帯は道しるべで、今いる駅に印。玩具の頁の中でだけ つくる・のこす が押せる。持ち寄る駅に もう 1 つ つくる、よむ に読み物への道")
