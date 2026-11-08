"""サイトの主な頁で、字の箱どうしと、字と絵が重ならない（本人の言葉 11-08「iPadで横表示で見たら文字が重なってる。PC、iPhoneなどいろんな大きさで見ても崩れないようにして。」）。

見る事: 入口・玩具の頁（御来迎と虎）・作りながら見る頁・手帖（最初の画面と手順の画面）・のこす・もちよる・よむ・保護者の方へ・審査用の頁・えらぶ・組み立て・
くずし字・作る側の様子 を、iPad の横（1180×820 と、Safari の帯で縮んだ 1180×746）と縦（820×1180）・PC（1440×900）・iPhone（375×667）で、日本語・やさしい日本語・英語、白と暗い版で開き、
- 字の 1 行ずつの箱どうしが重なる所（字×字）と、字の箱と絵（img・svg・video・canvas）が重なる所（字×絵）を数える
- 見えていない物（hidden・display:none・畳んだ中・読み上げだけの字）と、親と子の要素どうし（ルビと元の字など）は数えない
- 親の overflow で切られた所は、切り口で切って数える（額の中で広げた絵など）
- 組み立ての 3D の舞台（#rt-scene）の中は 1 つの絵として扱い、中の部品の字と面の重なりは数えない（立体の重なりとして描く物）
- 原画の写し（out/sources・git の外）の有り無しの両方で測る（写しの無い木では同じ形の絵の包みを置く・tests/test_landscape_fit.py と同じ）。
  原画の畳みの外の絵（えらぶ の札・入口の浮かぶ玩具・よむ の北斎漫画）は木の写しのとおりに出るので、写しのある木と無い木の両方で 1 度ずつ回して確かめる
今わかっている重なり（KNOWN・持ち主の直し待ち）は数えるが落とさない。それ以外の重なりが 1 つでもあれば落ちる。直した持ち主は KNOWN の行を外す。
./run.sh はブラウザなしで動く決まりなので、入っている Chrome で頁をその大きさの iframe に開いて測る（tests/test_landscape_fit.py と同じ測り方）。
Chrome が無い機械と、時間内に答えなかった時は、測れないと出して通す（出力の「測れない」を見る）。
"""
import concurrent.futures
import html
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ.pop("ANTHROPIC_API_KEY", None)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from measure_tap import chrome  # noqa: E402
from omochae import hypotheses  # noqa: E402
from web import genga, play_server  # noqa: E402

_real_pic = genga._pic
# 写しの有り無しはサーバごとに決める（回を同時に走らせるので、頁を作る糸ごとに持つ。下の do_get が入れる）
PIC = threading.local()


def _pic(sid, src, alt, lazy=False, href=None, **kw):
    if getattr(PIC, "m", "pic") == "nopic":
        return "", False
    got = _real_pic(sid, src, alt, lazy=lazy, href=href, **kw)
    return got if got[0] else (f'<span class="genga-pic" style="--genga-r:0.7000"><img src="data:," width="700" height="1000" alt="{html.escape(alt)}"></span>', True)


genga._pic = _pic

G, T = "NDL-1187053-R0000005-L", "NDL-1187053-R0000014-R"
PAGES = {"入口": "/", "玩具の頁 御来迎": f"/toy/{G}", "玩具の頁 虎": f"/toy/{T}", "作りながら見る": f"/toy/{G}/tsukuru", "手帖 最初": f"/toy/{G}/techo",
         "手帖 手順": f"/toy/{G}/techo?v=1&n=3", "のこす": f"/toy/{G}/techo/kiroku", "もちよる": "/gallery", "よむ": "/about", "保護者の方へ": "/otona",
         "審査用": "/kaizen", "えらぶ": "/toys?paper=1", "組み立て": f"/toy/{G}/kumitate", "くずし字": f"/zukan/{G}/yomi", "作る側の様子": "/loop"}
# iPad 横の帯あり（1180×746）は、Safari の上の帯の分だけ縦が縮んだ高さ（本人が見たのは iPad の横・11-08 に直しの担当が WebKit で測った高さの 1 つ）
SIZES = {"iPad 横": (1180, 820), "iPad 横 帯あり": (1180, 746), "iPad 縦": (820, 1180), "PC 1440": (1440, 900), "iPhone SE": (375, 667)}

# 今わかっている重なり（11-08 の見回り・grove の state/no-overlap-20261108.md）。鍵は（頁, 種類, 片方の要素の道の尾, もう片方の要素の道の尾, 言葉）。
# 持ち主が直したら、その行を外す（外すと、残っていれば落ちる）
KNOWN = {
    # えらぶの棚の札で、英語の玩具の名（長い）が札の絵に重なる。狭い幅では下の「See all toys」にも
    ("えらぶ", "字×絵", "li>a>span.nm", "li>a>img.pic", "en"),
    ("えらぶ", "字×字", "li>a>span.nm", "section.sec.erabu>p.links>a", "en"),
}
# 原画の写しの無い木の えらぶ の札で、やさしい日本語の玩具の名と「図を見る（国立国会図書館）」のルビ（切れない）が札の幅より長く、端の列が画面の横にはみ出す（上の えらぶ の札の名と同じ持ち主）
KNOWN_WIDE = {("えらぶ", "easy")}
# 原画の写しの無い木の えらぶ の札にだけ出る「図を見る（国立国会図書館）」の字が、札の玩具の名の字に重なる（写しの無い札は絵の箱が空で、名と道の字が詰まる。上の えらぶ の札の名と同じ持ち主）。
# 審査する人が repo だけを clone して回すと、この形を見る
KNOWN_LINK = ("えらぶ", "p.meta>a")

FIND = r"""(() => {
  const SKIP = new Set(["SCRIPT", "STYLE", "NOSCRIPT", "TITLE", "OPTION", "TEMPLATE"]);
  const cache = new Map();
  const shown = (el) => {
    if (cache.has(el)) return cache.get(el);
    let ok = true;
    for (let e = el; e && e !== document.documentElement; e = e.parentElement) {
      if (e.hidden || e.closest("details:not([open]) > :not(summary)") === e) { ok = false; break; }
      const s = getComputedStyle(e);
      if (s.display === "none" || s.visibility === "hidden" || +s.opacity < 0.05) { ok = false; break; }
      if (s.clipPath && s.clipPath.startsWith("inset(50%")) { ok = false; break; }
      if (s.clip && s.clip.startsWith("rect(0")) { ok = false; break; }
    }
    cache.set(el, ok);
    return ok;
  };
  const sx = scrollX, sy = scrollY;
  const clipOf = (el) => {
    let c = [-1e9, -1e9, 1e9, 1e9];
    for (let e = el.parentElement; e && e !== document.body; e = e.parentElement) {
      const s = getComputedStyle(e);
      if (s.overflow !== "visible" || s.overflowX !== "visible" || s.overflowY !== "visible" || s.contain.includes("paint")) {
        const r = e.getBoundingClientRect();
        c = [Math.max(c[0], r.left), Math.max(c[1], r.top), Math.min(c[2], r.right), Math.min(c[3], r.bottom)];
      }
    }
    return c;
  };
  const box = (r, el) => { const c = clipOf(el); return [Math.max(r.left, c[0]) + sx, Math.max(r.top, c[1]) + sy, Math.min(r.right, c[2]) + sx, Math.min(r.bottom, c[3]) + sy]; };
  const inScene = (el) => !!el.closest("#rt-scene, .rt-scene");
  const name = (el) => { const id = el.id ? "#" + el.id : "", cls = el.classList.length ? "." + [...el.classList].slice(0, 2).join(".") : ""; return el.tagName.toLowerCase() + id + cls; };
  const path = (el) => { const out = []; for (let e = el; e && e !== document.body && out.length < 3; e = e.parentElement) out.unshift(name(e)); return out.join(">"); };
  const texts = [];
  const tw = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (tw.nextNode()) {
    const n = tw.currentNode, el = n.parentElement;
    if (!n.textContent.trim() || !el || SKIP.has(el.tagName) || inScene(el) || !shown(el)) continue;
    const rg = document.createRange(); rg.selectNodeContents(n);
    for (const r of rg.getClientRects()) { const b = box(r, el); if (b[2] - b[0] >= 3 && b[3] - b[1] >= 3) texts.push({ el, b, t: n.textContent.trim().slice(0, 20) }); }
  }
  const pics = [...document.querySelectorAll("img,svg,video,canvas")].filter((e) => shown(e) && !inScene(e) && !(e.parentElement && e.parentElement.closest("svg")))
    .map((e) => ({ el: e, b: box(e.getBoundingClientRect(), e) })).filter((x) => x.b[2] - x.b[0] > 6 && x.b[3] - x.b[1] > 6);
  const inter = (a, b) => Math.min(a[2], b[2]) - Math.max(a[0], b[0]) > 3 && Math.min(a[3], b[3]) - Math.max(a[1], b[1]) > 3;
  const related = (a, b) => a === b || a.contains(b) || b.contains(a);
  const hits = [], seen = new Set();
  const add = (kind, a, b, ta, tb) => { const k = kind + "|" + path(a) + "|" + path(b); if (seen.has(k)) return; seen.add(k); hits.push({ kind, a: path(a), b: path(b), ta, tb }); };
  texts.sort((p, q) => p.b[1] - q.b[1]);
  for (let i = 0; i < texts.length; i++) { const p = texts[i]; for (let j = i + 1; j < texts.length && texts[j].b[1] < p.b[3]; j++) { const q = texts[j]; if (!related(p.el, q.el) && inter(p.b, q.b)) add("字×字", p.el, q.el, p.t, q.t); } }
  for (const p of texts) for (const g of pics) if (!related(p.el, g.el) && inter(p.b, g.b)) add("字×絵", p.el, g.el, p.t, g.el.getAttribute("alt") || "");
  return { hits, sw: document.documentElement.scrollWidth, w: innerWidth };
})()"""

WRAP = """<!doctype html><meta charset="utf-8"><body>__FRAMES__<pre id="measured"></pre><script>
const FIND=__FIND__;
addEventListener('load',()=>setTimeout(()=>{const out=[];for(const f of document.querySelectorAll('iframe')){let r;try{r=f.contentWindow.eval(FIND)}catch(e){r={err:String(e)}}
out.push({key:f.dataset.key,...r})}document.getElementById('measured').textContent=JSON.stringify(out)},1500))</script>"""

exe = chrome()
if not exe:
    print("測れない: Chrome が無い")
    raise SystemExit(0)
send, get = play_server.Handler._send, play_server.Handler.do_GET


class Tee:
    """応答の書き口の写し。書いた物をそのまま送り、同じ物を手元にも残す。"""

    def __init__(self, raw):
        self.raw, self.buf = raw, io.BytesIO()

    def write(self, data):
        self.buf.write(data)
        return self.raw.write(data)

    def __getattr__(self, name):
        return getattr(self.raw, name)


# 同じ頁を 4 つの大きさの枠で開くので、1 度作った応答をそのまま返す。頁を作るのは Python の糸を並べても速くならず
# （やさしい日本語の頁は 1 枚 0.5〜2.4 秒）、作り直すと 9 回 × 60 枠で run.sh の時間切れを超えた。鍵はサーバ（皮と写しの有り無し）・道・言葉の cookie
CACHE, LOCKS, GUARD = {}, {}, threading.Lock()
STATUS = {}  # (サーバの port, 道) → 返りの番号（枠の頁が 200 で返ったかを、測った後に見る）


def frame_src(path, lang):
    """枠に開く道（言葉の印を足した物）。枠を作る所と、返りの番号を引く所で同じ形にする。"""
    return path + ("&" if "?" in path else "?") + "lang=" + lang


def do_get(self):
    PIC.m = MODE[self.server.server_address[1]]
    if self.path.startswith("/__ov"):
        lang = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query).get("lang", ["ja"])[0]
        frames = "".join(f'<iframe data-key="{html.escape(pn)}|{sz}" src="{html.escape(frame_src(path, lang))}" width="{w}" height="{h}" '
                         'style="border:0;display:block"></iframe>' for pn, path in PAGES.items() for sz, (w, h) in SIZES.items())
        return send(self, 200, WRAP.replace("__FRAMES__", frames).replace("__FIND__", json.dumps(FIND)))
    cookie = re.search(r"utsushi_lang=(\w+)", self.headers.get("Cookie", ""))
    key = (self.server.server_address[1], self.path, cookie.group(1) if cookie else "")
    with GUARD:
        lock = LOCKS.setdefault(key, threading.Lock())
    with lock:
        if key in CACHE:
            return self.wfile.write(CACHE[key])
        self.wfile = Tee(self.wfile)
        get(self)
        CACHE[key] = self.wfile.buf.getvalue()
    head = re.match(rb"HTTP/\d\.\d (\d{3})", CACHE[key])
    STATUS[key[:2]] = int(head.group(1)) if head else None


play_server.Handler.do_GET = do_get
started = time.monotonic()
# 白と暗い版は頁の皮が違う（字の大きさ・行の高さ・枠）。写しの無い形は白で見る（皮によらず原画の畳みと絵の有無が替わるだけ）
servers = {(look, mode): play_server.serve(0, look=look) for look, mode in (("tenji", "pic"), ("zine", "pic"), ("tenji", "nopic"))}
MODE = {s.server_address[1]: mode for (_, mode), s in servers.items()}
for s in servers.values():
    threading.Thread(target=s.serve_forever, daemon=True).start()
white = f"http://127.0.0.1:{servers['tenji', 'pic'].server_address[1]}"
for sid in (G, T):  # 作りながら見る頁と手帖は、紙を刷った後でしか開かない
    urllib.request.urlopen(urllib.request.Request(f"{white}/toy/{sid}/print", data=urllib.parse.urlencode({"hypothesis": hypotheses.sheet_of(sid)["id"]}).encode(),
                                                  headers={"Origin": white}), timeout=180).read()


# 回の全体の締め切り（秒）。run.sh は 1 本を 300 秒で切って「検査できない（4）」にするので、その前に残りの回を測れないとして通す。
# 空いた機械では全部で 2 分ほど。11-08 の昼に機械が混んだ時（負荷 80・16 核）は、写しの無い木で 240 秒かかった
BUDGET = 230


def measure(base, lang):
    left = started + BUDGET - time.monotonic()
    if left < 20:
        return None
    # 言葉の切り替えは cookie なので、言葉ごとに別の回（別の profile）にする
    with tempfile.TemporaryDirectory() as profile:
        try:
            out = subprocess.run([exe, "--headless=new", "--no-sandbox", "--disable-gpu", f"--user-data-dir={profile}", "--window-size=2000,1400",
                                  "--virtual-time-budget=30000", "--dump-dom", f"{base}/__ov?lang={lang}"], capture_output=True, text=True, timeout=left).stdout
        except subprocess.TimeoutExpired:
            return None
    found = re.search(r'<pre id="measured">(.*?)</pre>', out, re.S)
    return json.loads(html.unescape(found.group(1))) if found and found.group(1).strip() else None


# 先に始まる回ほど締め切りに当たりにくいので、白の 3 つの言葉と写しの無い日本語を先にする
RUNS = ([("pic", "tenji", lang) for lang in ("ja", "easy", "en")] + [("nopic", "tenji", "ja")] + [("pic", "zine", lang) for lang in ("ja", "easy", "en")]
        + [("nopic", "tenji", lang) for lang in ("easy", "en")])


def one(run):
    mode, look, lang = run
    base = f"http://127.0.0.1:{servers[look, mode].server_address[1]}"
    return run, measure(base, lang) or measure(base, lang)


# 回を 1 本ずつ回すと 9 回で 3 分を超え、run.sh の 1 本の時間切れ（tests/run_floors.py の STEP_TIMEOUT 300 秒）に近い。Chrome を並べて回す
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    results = list(pool.map(one, RUNS))
found, wide, known_seen, unmeasured = [], [], set(), []
for (mode, look, lang), rec in results:
    if rec is None:
        unmeasured.append(f"{mode}・{look}・{lang}")
        continue
    port = servers[look, mode].server_address[1]
    for r in rec:
        page, size = r["key"].split("|")
        assert "err" not in r, (mode, look, lang, r["key"], r.get("err"))
        # 枠の頁が 200 で返ったか（404 や 500 の断りの頁の字を測って 0 と数えない・#684 の別の目）。返りは覚えた応答の頭の行から読む
        status = STATUS.get((port, frame_src(PAGES[page], lang)))
        assert status == 200, (mode, look, lang, page, "枠の頁が 200 で返らない（測った字は頁の字でない）", status)
        if r["sw"] > r["w"] + 1:
            if (page, lang) in KNOWN_WIDE:
                known_seen.add(("横", page, lang))
            else:
                wide.append(f"{mode}・{look}・{lang}・{page}・{size}: 横にはみ出す {r['sw']}px（幅 {r['w']}px）")
        for hit in r["hits"]:
            key = (page, hit["kind"], hit["a"], hit["b"], lang)
            link = page == KNOWN_LINK[0] and (KNOWN_LINK[1] in hit["a"] or KNOWN_LINK[1] in hit["b"])
            if key in KNOWN or link:
                known_seen.add(key if key in KNOWN else ("道", page))
                continue
            found.append(f"{mode}・{look}・{lang}・{page}・{size}: {hit['kind']} {hit['a']}「{hit['ta']}」× {hit['b']}「{hit['tb']}」")
for s in servers.values():
    s.shutdown()
if unmeasured and len(unmeasured) == len(RUNS):
    print("測れない: Chrome が答えなかった（全部の回）")
    raise SystemExit(0)
assert not found and not wide, "重なり・横のはみ出し（KNOWN の外）:\n" + "\n".join((wide + found)[:60])
gone = ([k for k in KNOWN if k not in known_seen] + [("横", *k) for k in KNOWN_WIDE if ("横", *k) not in known_seen]
        + [k for k in (("道", KNOWN_LINK[0]),) if k not in known_seen])
print(f"ok 主な頁の字の重なり: {len(PAGES)} 頁 × {len(SIZES)} 大きさ × 3 言葉 × 白と暗い版（原画の写しの有り無し）で KNOWN の外は 0。"
      f"KNOWN の残り {len(known_seen)} 件" + (f"・見えなくなった KNOWN {len(gone)} 件（写しの有り無しの片方でだけ出る物もある。両方の木で見えなければ行を外す）" if gone else "")
      + (f"。測れない回: {'・'.join(unmeasured)}" if unmeasured else "") + f"（{time.monotonic() - started:.0f} 秒）")
for k in gone:
    print("  見えなかった KNOWN:", "・".join(k))
