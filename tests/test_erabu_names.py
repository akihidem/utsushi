"""えらぶの棚（/toys?paper=1 の原画の敷き詰め）の玩具の名の札が、どの大きさでも崩れない（本人の言葉 11-08「iPadで横表示で見たら文字が重なってる。PC、iPhoneなどいろんな大きさで見ても崩れないようにして。」）。

なぜ: 名の札は「絵の下に小さく 1 行」（skin.BASE の .narabi .nm）を、行の数の切り（-webkit-line-clamp:1）と overflow:hidden で作っていた。英語とやさしい日本語の
長い名は 2〜25 行に折れて、2 行目からは隠れた字のまま札の下（次の絵と下の道の所）に並び、やさしい日本語では隠れた 2 行目のルビの頭が名の下に覗いた
（11-08 に幅 390 で撮って見た）。字の重なりの見回り（grove の state/no-overlap-20261108.md の 4）は、この隠れた行を絵との重なりとして数えていた。
見る事（白と暗い版・日本語・やさしい日本語・英語・iPad の横と縦・PC・iPhone の 12 の大きさ）:
1. 名の字（ルビの外）は 1 行だけ（隠れた行が無い）
2. ルビ（rt）は札の箱の中（上も下も切れない）
3. 札の箱は、絵・ほかの札・下の道（全部の玩具を見る）に重ならない。札は自分の列（li）の幅の中
4. 札の a の title に全名がある（ルビの外の名の字と同じ）。名が … で切れる時に、全名を見る道（統括の頼み 11-08・英語は 33 のうち 24〜31 が切れる）
./run.sh はブラウザなしで動く決まりなので、入っている Chrome で頁をその大きさの iframe に開いて測る（tests/test_landscape_fit.py と同じ）。
原画の写し（out/sources・git の外）が無い木では、絵の無い札（.nopic）で同じ形を測る。Chrome が無い機械と、時間内に答えなかった時は、測れないと出して通す。
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
from web import play_server  # noqa: E402

SIZES = [(320, 568), (375, 667), (390, 844), (430, 932), (768, 1024), (820, 1180), (1024, 768), (1180, 820), (1366, 1024), (1280, 800), (1440, 900), (1920, 1080)]
LANGS = ("ja", "easy", "en")
MEASURE = """<script>addEventListener('load',()=>{setTimeout(()=>{
const R=(b)=>({l:b.left,t:b.top,r:b.right,b:b.bottom}),meet=(a,b)=>Math.min(a.r,b.r)-Math.max(a.l,b.l)>1&&Math.min(a.b,b.b)-Math.max(a.t,b.t)>1;
const sec=document.querySelector('.erabu'),bad=[];let n=0;
const pics=[...sec.querySelectorAll('.narabi .pic')].map(e=>R(e.getBoundingClientRect())),links=[...sec.querySelectorAll('p.links a')].map(e=>R(e.getBoundingClientRect()));
const nms=[...sec.querySelectorAll('.narabi .nm')],own=nms.map(e=>R(e.getBoundingClientRect()));
nms.forEach((e,i)=>{n++;const o=own[i],li=R(e.closest('li').getBoundingClientRect()),name=e.textContent.slice(0,24),tops=[];let base='';
 const tw=document.createTreeWalker(e,NodeFilter.SHOW_TEXT);let t;while(t=tw.nextNode()){if(t.parentElement.closest('rt')||!t.textContent.trim())continue;base+=t.textContent;
  const rg=document.createRange();rg.selectNodeContents(t);for(const b of rg.getClientRects())if(b.width>0)tops.push(b.top)}
 const ttl=(e.closest('a').getAttribute('title')||'').trim();if(ttl!==base.trim())bad.push(name+': 札の a の title が全名でない「'+ttl.slice(0,24)+'」');
 if(tops.length&&Math.max(...tops)-Math.min(...tops)>4)bad.push(name+': 名の字が 2 行以上（隠れた行）');
 for(const rt of e.querySelectorAll('rt')){const b=R(rt.getBoundingClientRect());if(b.r-b.l>0&&(b.t<o.t-0.5||b.b>o.b+0.5)){bad.push(name+': ルビが札の箱の外 '+Math.round(b.t)+'〜'+Math.round(b.b)+' / '+Math.round(o.t)+'〜'+Math.round(o.b));break}}
 if(pics.some(p=>meet(o,p)))bad.push(name+': 札が絵に重なる');
 if(links.some(p=>meet(o,p)))bad.push(name+': 札が下の道に重なる');
 if(own.some((p,j)=>j!==i&&meet(o,p)))bad.push(name+': 札がほかの札に重なる');
 if(o.l<li.l-0.5||o.r>li.r+0.5)bad.push(name+': 札が列の幅の外')});
parent.postMessage(JSON.stringify({page:'__PAGE__',w:innerWidth,h:innerHeight,n,bad:bad.slice(0,6),nbad:bad.length}),'*')},800)})</script>"""
WRAP = """<!doctype html><body>%s<pre id="measured"></pre><script>
addEventListener('message',e=>{document.getElementById('measured').textContent+=e.data+'\\n'})</script>"""
pages = {f"{lang}-{w}x{h}": (f"/toys?paper=1&lang={lang}&walk={lang}-{w}x{h}", w, h) for lang in LANGS for w, h in SIZES}
send, get = play_server.Handler._send, play_server.Handler.do_GET


def wrapped(self, code, body, ctype="text/html; charset=utf-8", headers=()):
    m = re.search(r"[?&]walk=([\w-]+)", self.path)
    if m and m.group(1) in pages and isinstance(body, str) and ctype.startswith("text/html"):
        body += MEASURE.replace("__PAGE__", m.group(1))
    return send(self, code, body, ctype, headers)


def do_get(self):
    if self.path == "/__wrap":
        frames = "".join(f'<iframe src="{p.replace("&", "&amp;")}" width="{w}" height="{h}" style="border:0;display:block"></iframe>' for p, w, h in pages.values())
        return send(self, 200, WRAP % frames)
    return get(self)


def measure(look):
    server = play_server.serve(0, look=look)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        with tempfile.TemporaryDirectory() as profile:
            out = subprocess.run([exe, "--headless=new", "--no-sandbox", "--disable-gpu", f"--user-data-dir={profile}", "--window-size=2000,1200",
                                  "--virtual-time-budget=30000", "--dump-dom", f"{base}/__wrap"], capture_output=True, text=True, timeout=300).stdout
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
    print("測れない: Chrome が無い")
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
        assert (rec["w"], rec["h"]) == (w, h), where
        assert rec["n"] >= 10, (where, "棚の名の札が少ない（測る頁を取り違えていないか）", rec["n"])
        assert not rec["bad"], (where, f"名の札が崩れる（{rec['nbad']} 件）", rec["bad"])
print(f"ok えらぶの棚の名の札: 白と暗い版・3 つの言葉・{len(SIZES)} の大きさで 1 行・ルビは札の中・絵と道とほかの札に重ならない・札の a の title に全名")
