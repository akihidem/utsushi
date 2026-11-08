"""UX の見直しの段 0（本人の決定 11-06、docs/process/research/36-road-and-audience.md）。道をつなぐ・たたむ・並べ替える。

見る事:
1. 字は道しるべの言葉（えらぶ・つくる・のこす・もちよる）と今ある字だけ。足した押す所の字は「えらぶ」「つくる」「もちよる」、畳みの見出しは今の見出しと「見本」
2. 入口（白の展示・黒のジン）の最初の節に「えらぶ」が 1 つ（行き先は絵で選ぶ頁）
3. 玩具の頁の題のすぐ後に「つくる」が 1 つ。紙が無い時はたたき台の紙を作る（型紙を見ると同じ口）、紙がある時は窓の紙へ行く
4. 窓で紙ができた後は「PDF を開いて印刷する」→「つくる」（手帖へ）の順
5. 手帖の記録の頁で、返事の文のすぐ下に「もちよる」（ギャラリーの他の人が作った物へ）
6. 玩具の頁は流れの順（本人の言葉 11-08 の並び: これまでの復元 → 仮説 → 立体 → たとえ → 型紙）。これまでの記録は見出しのまま畳む。改善の輪の節は無い
7. 本物の記録がある時だけ、見本を「見本」の畳みに入れる（玩具の頁とギャラリー）。原画と歌は頭のまま
8. 狭い幅の Chrome で、玩具の頁の「つくる」が横にはみ出さず、1 回 下へ送ると見える（11-08 の本人の言葉で原図を横幅いっぱいにしたので、最初の画面には入らない。必須 2 種、白と黒）。headless の Chrome は窓の幅を 500 より狭くできないので、
   窓を 390×844 で頼んだ時の実の大きさ（500×701 ほど）で測る。幅 390×844・375×667 は実際のブラウザ（Chromium）で手で測った（関門の帳面）

./run.sh はブラウザなしで動く決まり。入っている Chrome で頁を開いて測る。Chrome が無い・答えない時は、測れないと出して通す。
"""
import json
import os
import re
import subprocess
import tempfile
import threading
import urllib.parse
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ.pop("ANTHROPIC_API_KEY", None)

from measure_tap import chrome  # noqa: E402
from omochae import hypotheses, records  # noqa: E402
from web import looks, play_server, techo_site, toy  # noqa: E402
# ワークショップの試行の写真（web.workshop・repo に在る）は、ここが見る「本物の記録が無い時」の形を変えるので、この試験では表を空にする
# （写真が出る形は tests/test_workshop_gallery.py が見る。本人の見直し 11-07 夜の ②⑦）
from web import workshop as _workshop  # noqa: E402

_workshop.TABLE = _workshop.TABLE.with_name("no-such-workshop-photos.json")
# もちよるの頁のワークショップの様子と、できたおもちゃの節（本人の言葉 11-08）も、写真の分けの表と感想の札を外して、本物の無い形を作る
# （2 つの節が出る形は tests/test_mochiyoru_workshop.py が見る）
_workshop.KINDS = _workshop.KINDS.with_name("no-such-workshop-photo-kinds.json")
from web import demo_samples as _samples  # noqa: E402
_samples.workshop_for = lambda sid, toy: ""

G, T = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"
# 御来迎のたたき台は組ごと（今の組 goraigo-v14 は H-C・記録の欄 sheet_by_set）。今の組で刷れるのはたたき台の紙だけ
GS = hypotheses.sheet_of(G)["id"]
ROAD = ("えらぶ", "つくる", "のこす", "もちよる")  # 本人の決定 11-06（research/36）。一字も変えない


def roads(page):
    """道しるべの押す所（class="road" の中の釦とリンク）の字。"""
    return [re.sub(r"<[^>]+>", "", m).strip() for m in re.findall(r'class="road"[^>]*>(?:<input[^>]*>)*<(?:a|button)[^>]*>(.*?)</(?:a|button)>', page)]


# ---- 1・2 入口
for name, make in looks.PAGES.items():
    page = make()
    first = re.search(r'<section class="(?:zn-cover|tj-hall)".*?</section>', page, re.S).group(0)
    if name in ("tenji", "zine"):  # 暗い版（zine）の入口も白と同じ作り（本人の決め 11-08「もう1つ立てる」）
        # 白の入口は えらぶ そのもの（本人のサイト体験レビュー 11-07 の 4・5）。えらぶ の釦は無く（押させない）、題の間のすぐ次に
        # 「まずはここから」の 2 枚（御来迎・張子の首振り虎）が、その玩具の頁への口として並ぶ
        body = page.split("</style>")[-1]
        assert 'class="road-go"' not in body, (name, "えらぶ の釦は無い")
        mazu = re.search(r'<section class="tj-mazu".*?</section>', body, re.S).group(0)
        assert "<h2>まずはここから</h2>" in mazu and body.index("</section>", body.index('class="tj-hall"')) < body.index('class="tj-mazu"')
        main = [s for s in looks.sources() if looks.hypotheses.stage(s) == "必須"]
        assert re.findall(r'class="tj-mazu-card" href="/toy/([^"]+)"', mazu) == main, (name, "まずはここから は必須の 2 種")
        continue
    assert first.count('class="road-go"') == 1 and '<a class="road-go" href="/">えらぶ</a>' in first, (name, "入口の最初の節に「えらぶ」が 1 つ")
    assert page.count('class="road-go"') == 1, (name, "入口の次へ進む釦は 1 つだけ")

# ---- 3・6・7 玩具の頁（紙の前）
# 頭の「つくる」は仮説の段の頭へ行く道（本人の言葉 11-08 477「原図をみて、狂歌を読んで、仮説、たとえ、3D をみたあとに型紙の印刷にすすむ。」・答え 481-2
# 「推しのとおり。」）。紙を作る口は型紙の窓の中の「つくる」1 つ（段 6）。前の段 0 は頭の「つくる」が紙を作って窓へ行った（本人の決定 11-05・#242
# 「開いたらすぐ作れる」）が、本人の新しい答えで替わった。道しるべは 頭（→ 仮説）と 窓（刷る）の 2 つで、この順
before = toy.toy_page(G)
assert roads(before) == ["つくる", "つくる"], ("紙の前の頁の道しるべは 頭と型紙の窓の「つくる」2 つ", roads(before))
hero = before[before.index('<section class="hero">'):before.index("</section>", before.index('<section class="hero">'))]
assert hero.index("<h1>") < hero.index(">つくる<") < hero.index('class="links"'), "題のすぐ後に「つくる」"
assert '<p class="road"><a class="btn" href="#kasetsu-fuda">つくる</a></p>' in hero and "/print" not in hero, "頭の「つくる」は仮説の段へ（刷らない）"
win_part = before[before.index('id="win"'):before.index('id="kiroku"')]
go = re.search(r'<form method="post" action="/toy/[^"]+/print#win" class="road">.*?</form>', win_part, re.S).group(0)
assert f'name="hypothesis" value="{hypotheses.sheet_of(G)["id"]}"' in go, "紙が無い時は型紙の窓でたたき台の紙を作る"
# 頭の畳み「これまでの記録」は消した（本人の言葉 11-08「つくるは、これまでの記録は消す。」・477「復元の記録などはすべてもちよるに統合する。」）
assert "これまでの記録" not in hero and "fold-sec" not in hero, "頭に これまでの記録 の畳みが残った"
# 頁の足の「型紙の改善の輪」の節は外した（本人の答え 11-07 夕の Q5。作る側の様子の頁へ移した）
assert 'id="kaizen"' not in before, "改善の輪の節は玩具の頁に無い"
if 'id="tatoe"' in before:
    # たとえは仮説の後・立体の前に、畳まずに出す（本人の言葉 11-08 477「…仮説、たとえ、3D をみたあとに型紙の印刷にすすむ。」）
    assert before.index('id="kasetsu-fuda"') < before.index('id="tatoe"') < before.index('id="kasetsu"') < before.index('id="win"') and '<section class="sec" id="tatoe"><h2>' in before, "たとえは仮説の後で開いて出す"
# 流れの順は本人の言葉 11-08 477（仮説 → たとえ → 立体 → 型紙の窓 → のこそう）。これまでの復元・困ったら（#tsukuru）・組み方は頁に無い
assert before.index('id="kasetsu-fuda"') < before.index('id="kasetsu"') < before.index('id="win"') < before.index('id="kiroku"'), "流れの順"
assert not [x for x in ('id="minna"', 'id="tsukuru"', 'id="kumikata"') if x in before], "外した節が残った"
assert '<details class="fold-sec samples-fold">' not in before, "本物の記録が無い時は、見本を畳まない"
assert toy.FOLD_SCRIPT in before and "hashchange" in toy.FOLD_SCRIPT, "畳んだ節へ道で着いた時は開く（#ban-ayumi など）"
assert "genga-head" in hero, "原画と歌は頭のまま（畳まない）"

# ---- 3・4 紙を作った後
server = play_server.serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"


def post(path, data, opener=urllib.request.build_opener()):
    q = urllib.request.Request(base + path, data=urllib.parse.urlencode(data).encode(), headers={"Origin": base})
    with opener.open(q, timeout=120) as r:
        return r.status, r.read().decode("utf-8", "replace"), r.geturl()


for sid in (G, T):
    st, page, url = post(f"/toy/{sid}/print", {"hypothesis": hypotheses.sheet_of(sid)["id"], "at": "win"})
    assert st == 200 and "#win" in url or "see=" in url, (sid, url)
after = toy.toy_page(G, see=hypotheses.sheet_of(G)["id"], kind="", v=1)
hero = after[after.index('<section class="hero">'):after.index("</section>", after.index('<section class="hero">'))]
# 紙がある時も、頭の「つくる」は仮説の段へ（477・481-2）。型紙の窓は刷った紙を出し、刷る口は出さない（版が上がった時だけ make_go が刷る口を返す。下の線）
assert '<p class="road"><a class="btn" href="#kasetsu-fuda">つくる</a></p>' in hero, "頭の「つくる」は仮説の段へ"
win_after = after[after.index('id="win"'):after.index('id="kiroku"')]
assert '<figure class="sheet">' in win_after and "/print#win" not in win_after, "紙がある時は、作り直さずに窓の紙を出す"
# 刷ってある紙が一番新しい版でない時（人が採った版 2 など）と、今の組でない時（雛形の次の組）は、窓へ行かずに刷る口へ送る（古い紙を出さない）
from omochae import loop  # noqa: E402
from omochae.compose import TEMPLATES  # noqa: E402

real_latest = loop.latest_version
loop.latest_version = lambda s, h: 2
try:
    assert re.search(r'<form method="post" action="/toy/[^"]+/print#win" class="road">', toy.make_go(G)), "版が上がった時は刷る口へ"
finally:
    loop.latest_version = real_latest
tpl = TEMPLATES[hypotheses.load(G).get("template", "slider_fan")]
real_set = tpl.SHEET_SET
tpl.SHEET_SET = real_set + "-next"
try:
    assert re.search(r'<form method="post" action="/toy/[^"]+/print#win" class="road">', toy.make_go(G)), "組が上がった時は刷る口へ"
finally:
    tpl.SHEET_SET = real_set
assert '<p class="road"><a class="btn"' in toy.make_go(G), "対照: 一番新しい版で今の組の紙なら窓へ"
# 型紙の窓は次の段（できたら、のこそう・#kiroku）の頭まで。窓の中に版の歩みの節（畳み）が入るので、最初の </section> では切らない（11-08）
win = after[after.index('id="win"'):after.index('id="kiroku"')]
assert win.index("PDF を開いて印刷する") < win.index(f'<a class="btn" href="/toy/{G}/techo">つくる</a>'), "窓は 印刷 → つくる（手帖）の順"
# 作りながら見るの釦は、11-07 の工作のために残していたが、作りながら見る頁を手帖へ寄せた（窓口の決め 11-07 の 4。作る口は手帖 1 つ）
assert f'href="/toy/{G}/tsukuru"' not in after, "作りながら見るの釦は玩具の頁に出さない"
assert roads(after) == ["つくる", "つくる"], ("紙の後の道しるべ", roads(after))

# ---- 5 手帖の記録の頁
# 感想のある記録（ギャラリーは、写真か言葉の無い記録を札にしない）
rid, fs = records.add({"source_id": G, "hypothesis_id": GS, "sheet_version": 1, "result": "動いた", "impression": "扇がよく開いた"})
assert not fs, fs
kiroku = techo_site.records_page(G, msg="上げました")
mine = kiroku[kiroku.index('<div id="mine">'):]
assert mine.index('<p id="msg">上げました</p>') < mine.index('<p class="road"><a class="go" href="/gallery#ageta">のこす</a></p>') < mine.index('class="item"'), "返事の文のすぐ下に「もちよる」"
assert roads(kiroku) == ["のこす"], roads(kiroku)  # 釦の字は のこす（本人のサイトの見直し 11-07 22:16）。行き先は前のまま

# ---- 7 見本の記録（作り物）は外した（本人の言葉 11-08「見本の記録をワークショップのデータで作成して欲しい。」）。畳みも出ない
withrec = toy.toy_page(G)
gallery = techo_site.gallery_page(play_server.sources())
assert "samples-fold" not in withrec and '<details class="samples-fold">' not in gallery, "玩具の頁とギャラリーに見本の畳みを出さない"

# ---- 1 足した押す所の字は道しるべの言葉だけ
for page in (before, after, kiroku, *(f() for f in looks.PAGES.values())):
    assert all(w in ROAD for w in roads(page) + re.findall(r'class="road-go"[^>]*>([^<]*)<', page)), "道しるべの言葉のほかの字を足していない"

# ---- 8 幅 390 の Chrome で最初の画面に入るか
MEASURE = r"""<script>addEventListener('load',()=>setTimeout(()=>{const R={vh:innerHeight,vw:innerWidth,sx:document.documentElement.scrollWidth};
const e=document.querySelector('.road-go, .hero .road .btn, .tj-mazu-card');if(e){const b=e.getBoundingClientRect();R.go=[Math.round(b.top),Math.round(b.bottom),Math.round(b.height),e.textContent.trim()]}
const p=document.createElement('pre');p.id='measured';p.textContent=JSON.stringify(R);document.body.appendChild(p)},400))</script>"""
send = play_server.Handler._send


def wrapped(self, code, body, ctype="text/html; charset=utf-8", headers=()):
    if isinstance(body, str) and "</body>" in body and "measure=1" in self.path:
        body = body.replace("</body>", MEASURE + "</body>", 1)
    return send(self, code, body, ctype, headers)


exe = chrome()
measured = {}
if exe:
    play_server.Handler._send = wrapped
    try:
        for look in ("tenji", "zine"):
            for path in (f"/look/{look}?measure=1", f"/toy/{G}?measure=1", f"/toy/{T}?measure=1"):
                server.look = look
                with tempfile.TemporaryDirectory() as prof:
                    try:
                        out = subprocess.run([exe, "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars", f"--user-data-dir={prof}", "--window-size=390,844",
                                              "--virtual-time-budget=8000", "--dump-dom", base + path], capture_output=True, text=True, timeout=120).stdout
                    except subprocess.TimeoutExpired:
                        out = ""
                m = re.search(r'<pre id="measured">(.*?)</pre>', out, re.S)
                measured[(look, path)] = json.loads(m.group(1).replace("&quot;", '"')) if m else None
    finally:
        play_server.Handler._send = send
server.shutdown()
got = [v for v in measured.values() if v]
if not got:
    print("ok 段 0 の道しるべ: 字と順と畳みを見た。測れない: Chrome が無いか答えないので、最初の画面に入るかは見ていない")
    raise SystemExit(0)
for key, r in measured.items():
    if r is None:
        continue
    assert "go" in r, (key, "次へ進む釦が頁にある", r)
    top, bottom, height, word = r["go"]
    if key[1].startswith(("/look/tenji", "/look/zine")):  # 暗い版（zine）の入口も白と同じ作り（本人の決め 11-08「もう1つ立てる」）
        # 白の入口は えらぶ そのもの（本人のサイト体験レビュー 11-07 の 4・5）。次へ進む釦の代わりに、まずはここから の札（玩具の名前）がある。
        # 前は札が最初の画面で押せる（札の上の 64px が画面の中）事も見ていたが、本人の決め（11-07 夜）「縦の組みに戻す」で題の間が 11-06 夜の
        # 画面いっぱいの縦の組みに戻り、札は 1 回 下へ送ると見える所になった（1440 と 390 で札の頭が約 1040px）。札があって押せる大きさかだけを見る
        assert word not in ("えらぶ", "つくる") and height >= 64 and top > 0, (key, "まずはここから の札が頁にあり押せる大きさ", r)
        assert r["sx"] <= r["vw"], (key, "横にはみ出さない", r)
        continue
    assert word in ("えらぶ", "つくる") and height >= 64, (key, "押せる大きさ", r)
    # 玩具の頁の「つくる」は、前は最初の画面に入る事（bottom <= vh）を見ていた。本人の言葉（11-08）「iPhone Airだとこの表示。原図を横幅いっぱいに
    # する。縦書きは失敗なので前の形に戻す。」で、狭い幅の原図は高さの上限を外して横幅いっぱいになり、「つくる」は原図・狂歌・題の後（幅 390 で
    # 下の端が約 1170px）になった。最初の画面には入らないので、1 回 下へ送ると見える所（画面 2 つ分の中）にある事を見る。横にはみ出さない事は前のまま
    # （本人の写真では、縦書きの段が右へはみ出して切れていた）
    assert bottom <= 2 * r["vh"], (key, "1 回 下へ送ると見える（画面 2 つ分の中）", r)
    assert r["sx"] <= r["vw"], (key, "横にはみ出さない", r)
size = "×".join(str(got[0][k]) for k in ("vw", "vh"))
print(f"ok 段 0 の道しるべ: 玩具の頁の「つくる」が狭い幅（{size}）で横にはみ出さず 1 回 下へ送ると見え、紙の後は 印刷 → つくる、残した後は もちよる。{len(got)} 画面を測った")
