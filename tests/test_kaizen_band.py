"""入口の まずはここから の節の頭に、審査用の頁「良くするための一周 ♻︎」（/kaizen）への帯がある（本人の言葉 11-08「「良くするための一周」がサイトで目立っていません。
ここは審査者に見せたい所です。審査の人が入口から来て、掘らずに一周の仕組みが目に入るように、目立たせてください。」・統括の決め 11-08 の案 A）。

見る事（白と暗い版・日本語・やさしい日本語・英語・幅 320×568・390×844・1180×820・1440×900。全部の大きさは後で広げる）:
1. 帯は #mazu の中の見出しより前にあり、/kaizen へ行く。字は本人の OK 済みの題（kaizen_judge.TITLE）。英語は訳の表の字、やさしい日本語はルビの外の字が題と同じ
2. 下へ送る印と同じ #mazu で開いた時に、帯が画面の中にある（最初の 1 回の送りで目に入る）
3. 帯は見出し・2 枚の札・下の 1 行に重ならない。画面の幅の外に出ず、頁が横にはみ出さない
4. 押せる高さが 44px 以上
./run.sh はブラウザなしで動く決まりなので、入っている Chrome で頁をその大きさの iframe に開いて測る（tests/test_landscape_fit.py と同じ）。
Chrome が無い機械と、時間内に答えなかった時は、測れないと出して通す。
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
from web import i18n, kaizen_judge, looks, play_server  # noqa: E402

# 1 の前半は Chrome なしで見る: 帯は見出しより前・/kaizen・字は題そのもの
page = looks.tenji()
band = re.search(r'<a class="tj-kaizen" href="([^"]*)">([^<]*)</a>', page)
assert band and band.group(1) == "/kaizen" and band.group(2) == kaizen_judge.TITLE, "まずはここから の節に /kaizen への帯が無い（か字が題と違う）"
assert page.index('id="mazu"') < band.start() < page.index("<h2>", page.index('id="mazu"')), "帯は まずはここから の見出しより前に置く"
EN = i18n.table()[kaizen_judge.TITLE]
WANT = {"ja": kaizen_judge.TITLE, "easy": kaizen_judge.TITLE, "en": EN}

SIZES = [(320, 568), (390, 844), (1180, 820), (1440, 900)]
LANGS = ("ja", "easy", "en")
MEASURE = """<script>addEventListener('load',()=>{setTimeout(()=>{
const R=(e)=>{const b=e.getBoundingClientRect();return {l:b.left,t:b.top,r:b.right,b:b.bottom,h:b.height}},meet=(a,b)=>Math.min(a.r,b.r)-Math.max(a.l,b.l)>1&&Math.min(a.b,b.b)-Math.max(a.t,b.t)>1;
const sec=document.getElementById('mazu'),a=sec.querySelector('a.tj-kaizen'),out={page:'__PAGE__',w:innerWidth,h:innerHeight,ok:!!a};
if(a){let base='';const tw=document.createTreeWalker(a,NodeFilter.SHOW_TEXT);let t;while(t=tw.nextNode())if(!t.parentElement.closest('rt'))base+=t.textContent;
 const b=R(a),others=[...sec.querySelectorAll('h2,.row,.meta')].map(R);
 Object.assign(out,{href:a.getAttribute('href'),base:base.trim(),box:b,before:!!(a.compareDocumentPosition(sec.querySelector('h2'))&Node.DOCUMENT_POSITION_FOLLOWING),
  hit:others.filter(o=>meet(b,o)).length,cw:document.documentElement.clientWidth,sx:document.documentElement.scrollWidth})}
parent.postMessage(JSON.stringify(out),'*')},800)})</script>"""
WRAP = """<!doctype html><body>%s<pre id="measured"></pre><script>
addEventListener('message',e=>{document.getElementById('measured').textContent+=e.data+'\\n'})</script>"""
pages = {f"{lang}-{w}x{h}": (f"/?lang={lang}&walk={lang}-{w}x{h}#mazu", w, h) for lang in LANGS for w, h in SIZES}
send, get = play_server.Handler._send, play_server.Handler.do_GET


def wrapped(self, code, body, ctype="text/html; charset=utf-8", headers=()):
    m = re.search(r"[?&]walk=([\w-]+)", self.path)
    if m and m.group(1) in pages and isinstance(body, str) and ctype.startswith("text/html"):
        body += MEASURE.replace("__PAGE__", m.group(1))
    return send(self, code, body, ctype, headers)


def do_get(self):
    if self.path == "/__wrap":
        frames = "".join(f'<iframe src="{html.escape(p)}" width="{w}" height="{h}" style="border:0;display:block"></iframe>' for p, w, h in pages.values())
        return send(self, 200, WRAP % frames)
    return get(self)


def measure(look):
    server = play_server.serve(0, look=look)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as profile:
            out = subprocess.run([exe, "--headless=new", "--no-sandbox", "--disable-gpu", f"--user-data-dir={profile}", "--window-size=2000,1200",
                                  "--virtual-time-budget=20000", "--dump-dom", f"{base}/__wrap"], capture_output=True, text=True, timeout=240).stdout
    except subprocess.TimeoutExpired:
        out = ""
    server.shutdown()
    found = re.search(r'<pre id="measured">(.*?)</pre>', out, re.S)
    got = {}
    for line in html.unescape(found.group(1) if found else "").splitlines():
        if line.strip():
            rec = json.loads(line)
            got[rec["page"]] = rec
    return got if set(got) == set(pages) else None


exe = chrome()
if not exe:
    print("ok 帯は見出しの前・/kaizen・字は題そのもの。測れない: Chrome が無い")
    raise SystemExit(0)
play_server.Handler._send, play_server.Handler.do_GET = wrapped, do_get
for look in ("tenji", "zine"):
    got = measure(look)
    if got is None:
        print(f"測れない: Chrome が {look} の頁に答えきらなかった（混んだ機械では起きる）")
        raise SystemExit(0)
    for name, rec in got.items():
        lang, size = name.split("-")
        w, h = (int(x) for x in size.split("x"))
        where = (look, name)
        assert (rec["w"], rec["h"]) == (w, h) and rec["ok"], (where, "帯が無い", rec)
        assert rec["href"] == "/kaizen" and rec["before"], (where, "帯の行き先か置き場が違う", rec["href"], rec["before"])
        assert rec["base"] == WANT[lang], (where, "帯の字が題と違う（新しい字は足さない）", rec["base"])
        b = rec["box"]
        assert b["t"] >= -1 and b["b"] <= h + 1, (where, "#mazu に着いた時に帯が画面の外", b)
        assert b["l"] >= -1 and b["r"] <= rec["cw"] + 1 and rec["sx"] <= rec["cw"], (where, "帯が画面の幅の外か、頁が横にはみ出す", b, rec["sx"], rec["cw"])
        assert rec["hit"] == 0, (where, "帯が見出し・札・下の 1 行に重なる", rec["hit"])
        assert b["h"] >= 44, (where, "帯の押せる高さが 44px より低い", b["h"])
print(f"ok 良くするための一周 ♻︎ の帯: 白と暗い版・3 つの言葉・幅 {'・'.join(str(w) for w, _ in SIZES)} で、#mazu に着くと画面の中・重ならない・はみ出さない・押せる高さ 44px 以上")
