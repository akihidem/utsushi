"""玩具の頁（つくる）の頭の字の箱が、どの大きさでも重ならない（本人の言葉 11-08「iPadで横表示で見たら文字が重なってる。…いろんな大きさで見ても崩れないようにして。」）。

本人が見たのは虎の頁の iPad の横で、広い幅で絵の右に縦書きにした歌（#614 の #595 の前の形）が、題と本文の上へはみ出していた（日本語・やさしい日本語・英語の
どれでも）。歌の列の高さを決まった値にし、はみ出す時は頁の台本が歌を絵の下の横書きに替える（genga.FIT_SCRIPT・.genga-flat）。

見る事:
1. 83 の玩具の頁ぜんぶを、日本語・やさしい日本語・英語で、iPad の横（1024×768・1180×820・1366×1024）と縦（768×1024・820×1180）・PC（1440×900）・
   iPhone（390×844）の大きさで開き、頭の字の箱（縦か横の歌・題・つくる・作品の札・くずし字を読む・図を見る・絵）が互いに重ならない
2. 頁の横の幅が画面の幅を越えない（横にはみ出さない）
3. 歌の列の高さは決まった値（height）。はみ出す時の替え（.genga-flat）がある
4. 替えの台本が働く: 縦書きの歌を題の上へずらした形（Safari の見積もりの違いで本人が見た形をまねる）と、歌の列を細くした形（列が細く見積もられ、
   字の行が左の絵の上へ出る形・別の目の検品 11-08 の止め）で開くと、頁の台本が横書きに替えて重なりが消える。歌の字は行ごとの箱で測る
6. 台本の動かない画面でも重ならない: 頭は横書き（.genga-flat）で出て、台本が測って入ると分かった時だけ縦書きにする
5. 替えの台本の中に「<」が無く、英語とやさしい日本語の頁で、台本の後ろの頭の字（題・作品の札・くずし字を読む）も替わる

./run.sh はブラウザなしで動く決まりで、ブラウザを操る道具も入れない（tests/test_landscape_fit.py と同じ）。入っている Chrome で頁をその大きさの iframe に
開いて測る。Chrome が無い機械と、時間内に答えなかった時は、測れないと出して通す。iPad の Safari そのものでは測れない（この機械に WebKit の部品が無い）ので、
Safari の縦書きの幅の見積もりの違いは、頁の台本（.genga-flat）が実の箱を測って替える形で守る。
"""
import html
import json
import os
import re
import subprocess
import tempfile
import threading

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ.pop("ANTHROPIC_API_KEY", None)

from measure_tap import chrome  # noqa: E402
from web import genga, i18n, play_server, toy  # noqa: E402
from web.play_server import sources  # noqa: E402

# 3. 形
css = genga.STYLE
wide = css[:css.index("@media (max-width:820px)")]
assert ".genga-head .genga-songs{writing-mode:vertical-rl;height:min(70vh,620px)" in wide, "歌の列の高さが決まった値でない"
assert ".genga-head.genga-flat .genga-songs{writing-mode:horizontal-tb;height:auto" in wide and "genga-flat" in genga.FIT_SCRIPT
# 狭い幅の横書きの歌は高さを決めない（広い幅の決まった高さを残すと、横書きの歌の下に大きな空きができ、つくる が下へ押される）
narrow = css[css.index("@media (max-width:820px)"):]
assert ".genga-head .genga-songs{writing-mode:horizontal-tb;max-height:none;height:auto" in narrow, "狭い幅の歌に高さが残った"
# 6. 台本の動かない画面でも重ならない: 歌のある頭は横書き（.genga-flat）で出る。台本が外す（測って縦書きが入る時だけ）
assert 'class="genga genga-head genga-flat"' in genga.head("NDL-1187053-R0000014-R", play_server.source("NDL-1187053-R0000014-R")), "頭が横書きで出ない"
assert "h.classList.remove('genga-flat')" in genga.FIT_SCRIPT and ".genga-pic" in genga.FIT_SCRIPT, "台本が絵との重なりを見ない"
# 5. i18n.to_en は HTML を <[^>]*> で区切る。台本の中に「<」があると札と読み違え、</script> を飲み込んでその後の字を替えなくなる
assert "<" not in genga.FIT_SCRIPT[len("<script>"):-len("</script>")], "替えの台本の中に < がある"

# 原画の写し（out/）は git の外。無い時だけ、同じ形の絵の包み（縦横つき）を返す（test_landscape_fit と同じ）。字の箱の並びは絵の大きさで決まるため
_real_pic = genga._pic


def _pic(sid, src, alt, lazy=False, href=None, **kw):
    got = _real_pic(sid, src, alt, lazy=lazy, href=href, **kw)
    if got[0]:
        return got
    tag, link = ("a", f' href="{html.escape(href)}"') if href else ("span", "")
    return (f'<{tag} class="genga-pic"{link} style="--genga-r:0.7000"><img src="data:," width="700" height="1000" alt="{html.escape(alt)}"></{tag}>', True)


genga._pic = _pic

SIZES = ((1024, 768), (1180, 820), (1366, 1024), (768, 1024), (820, 1180), (1440, 900), (390, 844))
LANGS = ("ja", "easy", "en")
SIDS = list(sources())
BOXES = (".hero .genga-songs", ".hero h1", ".hero .road", ".hero .label", ".hero .links", ".hero .genga-cap", ".hero .genga-pic")
# 歌は要素の箱でなく字の行ごとの箱（Range）で測る: 列が細く見積もられると、字の行は要素の箱の外（左の絵の上）へ出る
MEASURE = """<script>addEventListener('load',()=>setTimeout(()=>{const B=__BOXES__,out=[];
for(const s of B){const e=document.querySelector(s);if(!e)continue;let rs=[e.getBoundingClientRect()];
if(s.indexOf('genga-songs')>=0){const g=document.createRange();g.selectNodeContents(e);rs=[...g.getClientRects()]}
for(const r of rs)if(r.width>1&&r.height>1)out.push([s,r.left,r.top,r.right,r.bottom])}
parent.postMessage(JSON.stringify({page:'__PAGE__',w:innerWidth,sw:document.documentElement.scrollWidth,flat:!!document.querySelector('.genga-flat'),boxes:out}),'*')},300))</script>"""
WRAP = """<!doctype html><body>%s<pre id="measured"></pre><script>
addEventListener('message',e=>{document.getElementById('measured').textContent+=e.data+'\\n'})</script>"""

send, get = play_server.Handler._send, play_server.Handler.do_GET
# 束（1 つの言葉と 1 つの大きさの 83 頁）ごとの頁。束は別々の Chrome で同時に回す（全部を 1 つずつ回すと 7 分ほどかかり、./run.sh の 1 本の時間を越えた）
batches = {f"{lang}-{w}x{h}": {f"{lang}-{w}x{h}-{i}": (f"/toy/{sid}?lang={lang}&fit={lang}-{w}x{h}-{i}", w, h) for i, sid in enumerate(SIDS)}
           for lang in LANGS for w, h in SIZES}
pages = {k: v for b in batches.values() for k, v in b.items()}

# 4. 本人が iPad の横で見た形（縦書きの歌が題と本文の上にかかる）は、この機械の Chrome と WebKit では出なかった。歌を右へずらしてその形を作り、
# 頁の台本が実の箱を測って横書きに替える事を見る。ずらしは縦書きの間だけ効く（横書きに替わったら外れる）。虎の頁（本人が見た頁）を iPad の横の 3 つの大きさで
TIGER = "NDL-1187053-R0000014-R"
STRESS = {"stress": "<style>.genga-head:not(.genga-flat) .genga-songs{transform:translateX(360px)}</style>",
          # 列を細くする形: 縦書きの列の幅を 20px に決めると、字の行は列の左へ出て、頭の列の中に留まったまま絵に重なる
          "narrow": "<style>.genga-head:not(.genga-flat) .genga-songs{width:20px!important;min-width:0!important}</style>"}
batches.update({f"{kind}-{lang}": {f"{kind}-{lang}-{w}x{h}": (f"/toy/{TIGER}?lang={lang}&fit={kind}-{lang}-{w}x{h}", w, h) for w, h in SIZES[:3]}
                for kind in STRESS for lang in LANGS})
pages = {k: v for b in batches.values() for k, v in b.items()}

# 5. 英語とやさしい日本語の頁で、替えの台本の後ろにある頭の字も替わる（台本が i18n の区切りを狂わせると、ここから後ろが日本語のまま残る）
ja_page = toy.toy_page(TIGER)
for conv, want in ((i18n.page_en, "Read the cursive script"), (i18n.page_easy, "<ruby>")):
    got_page = conv(ja_page)
    at = got_page.index("addEventListener('resize',fit)")
    rest = got_page[at:got_page.index("</section>", at)]
    assert "くずし字を読む" not in rest and want in rest, (conv.__name__, "替えの台本の後ろの頭の字が替わらない", rest[:200])


# 頁の中身は大きさで替わらない（替わるのは CSS の効き方だけ）ので、玩具と言葉ごとに 1 回だけ作り、7 つの大きさで使い回す（作る時間が試験の大半だった）
made = {}
made_lock = threading.Lock()


def wrapped(self, code, body, ctype="text/html; charset=utf-8", headers=()):
    m = re.search(r"[?&]fit=([\w-]+)", self.path)
    if m and m.group(1) in pages and isinstance(body, str) and ctype.startswith("text/html") and code == 200:
        with made_lock:
            made[self.path.split("&fit=", 1)[0]] = body
    if m and m.group(1).split("-", 1)[0] in STRESS and isinstance(body, str):
        body = body.replace('<section class="hero">', '<section class="hero">' + STRESS[m.group(1).split("-", 1)[0]], 1)
    if m and m.group(1) in pages and isinstance(body, str) and ctype.startswith("text/html"):
        body = body.replace("</body>", MEASURE.replace("__PAGE__", m.group(1)).replace("__BOXES__", json.dumps(BOXES)) + "</body>", 1) if "</body>" in body else body + MEASURE.replace("__PAGE__", m.group(1)).replace("__BOXES__", json.dumps(BOXES))
    return send(self, code, body, ctype, headers)


def do_get(self):
    key = self.path.split("&fit=", 1)[0]
    if "&fit=" in self.path and key in made:
        return wrapped(self, 200, made[key])
    if self.path.startswith("/__fit/") and self.path[len("/__fit/"):] in batches:
        frames = "".join(f'<iframe src="{html.escape(path)}" width="{w}" height="{h}" style="border:0;display:block"></iframe>'
                         for path, w, h in batches[self.path[len("/__fit/"):]].values())
        return send(self, 200, WRAP % frames)
    return get(self)


def overlap(a, b):
    return a[1] < b[3] - 1 and b[1] < a[3] - 1 and a[2] < b[4] - 1 and b[2] < a[4] - 1


exe = chrome()
if not exe:
    print("測れない: Chrome が無い")
    raise SystemExit(0)
play_server.Handler._send, play_server.Handler.do_GET = wrapped, do_get
server = play_server.serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"
bad, short, unflat, narrow_flat = [], [], [], []


def run(key):
    """1 つの束を 1 つの Chrome で開き、頁ごとの箱を返す。"""
    with tempfile.TemporaryDirectory() as profile:
        try:
            out = subprocess.run([exe, "--headless=new", "--no-sandbox", "--disable-gpu", f"--user-data-dir={profile}", "--window-size=1600,1200",
                                  "--virtual-time-budget=20000", "--dump-dom", f"{base}/__fit/{key}"], capture_output=True, text=True, timeout=150).stdout
        except subprocess.TimeoutExpired:
            out = ""
    found = re.search(r'<pre id="measured">(.*?)</pre>', out, re.S)
    got = {}
    for line in (html.unescape(found.group(1)) if found else "").splitlines():
        if line.strip():
            rec = json.loads(line)
            got[rec["page"]] = rec
    return key, got


try:
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=4) as pool:
        for key, got in pool.map(run, batches):
            if len(got) < len(batches[key]):
                short.append((key, len(got)))
            for name, rec in got.items():
                if key.split("-", 1)[0] in STRESS:
                    sid, lang, size = TIGER, key.split("-")[1], name.rsplit("-", 1)[1]
                    # ずらす形はどの大きさでも題にかかるので、必ず横書きに替わる。列を細くする形は、大きさによっては字の行が絵まで届かず
                    # （重ならないので替えなくてよい）、重なる大きさでだけ替わる。どちらも、替えた後に重なりが残らない事は下の重なりの線が見る
                    if key.startswith("stress-") and not rec["flat"]:
                        unflat.append((key.split("-", 1)[0], lang, size))
                    if key.startswith("narrow-") and rec["flat"]:
                        narrow_flat.append((lang, size))
                else:
                    sid = SIDS[int(name.rsplit("-", 1)[1])]
                    lang, size = key.split("-", 1)
                if rec["sw"] > rec["w"] + 1:
                    bad.append((sid, lang, size, "横にはみ出す", rec["sw"]))
                boxes = rec["boxes"]
                for i in range(len(boxes)):
                    for j in range(i + 1, len(boxes)):
                        if boxes[i][0] != boxes[j][0] and overlap(boxes[i], boxes[j]):  # 歌の行どうしは数えない
                            bad.append((sid, lang, size, boxes[i][0], boxes[j][0]))
finally:
    server.shutdown()
if short and not bad:
    print(f"測れない所あり: Chrome が答えなかった束 {short[:3]}（混んだ機械では起きる）")
assert not bad, (len(bad), bad[:8])
assert not unflat, ("歌をずらした虎の頁で横書きに替わらなかった", unflat)
assert narrow_flat or len(short) > 0, "列を細くした虎の頁が、どの大きさでも横書きに替わらなかった（絵との重なりを拾っていない）"
print(f"ok 玩具の頁の頭の字の箱は重ならない: {len(SIDS)} 頁 × {len(LANGS)} 言葉 × {len(SIZES)} の大きさ（測れなかった束 {len(short)}）")
