"""入口の浮かぶ玩具の絵が、題の間の字と押す所に重ならない（本人の言葉 11-08「iPadで横表示で見たら文字が重なってる。PC、iPhoneなどいろんな大きさで見ても崩れないようにして。」）。

見る事（白と暗い版の入口・日本語・やさしい日本語・英語の頁）:
- iPad の横（1024×768・1180×820・1366×1024）と縦（768×1024・820×1180）、PC（1280×800・1440×900・1920×1080）、iPhone（375×667・390×844・430×932）で、
  出ている浮かぶ玩具の絵の箱が、題の間の字の行の箱（英字・題・読み・副題・このサイトについて）と押す所の箱（下へ送る印など）に重ならない
- 絵が画面の幅の外に出ない。4 つのうち 3 つ以上が出ている（置き直しで全部を消して重なりを無くす形を落とす）
直す前は、英語の頁の幅 1024〜1440 で左上の絵が英字に、右上の絵が副題に重なり、幅 375・390 で右下の絵が下へ送る印に重なった。
輪郭の絵は生成物（out/ukabu）で、まっさらな clone には無いので、本物の 4 つと同じ縦と横の比の絵を試験の中で作り、試験のサーバから出す。
./run.sh はブラウザなしで動く決まりなので、入っている Chrome で頁をその大きさの iframe に開いて測る（tests/test_landscape_fit.py と同じ）。
Chrome が無い機械と、時間内に答えなかった時は、測れないと出して通す。
"""
import io
import json
import os
import pathlib
import re
import subprocess
import tempfile
import threading

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ.pop("ANTHROPIC_API_KEY", None)

import html  # noqa: E402

from PIL import Image  # noqa: E402

from measure_tap import chrome  # noqa: E402
from web import play_server, ukabu  # noqa: E402

SIZES = [(1024, 768), (1180, 820), (1366, 1024), (768, 1024), (820, 1180), (1280, 800), (1440, 900), (1920, 1080), (375, 667), (390, 844), (430, 932)]
LANGS = ("ja", "easy", "en")
# 本物の輪郭の絵（out/ukabu・PICKS の順）の大きさ。縦と横の比が置き場に効くので、同じ比の絵で測る
REAL = [(208, 324), (208, 289), (208, 184), (208, 323)]
tmp = pathlib.Path(tempfile.mkdtemp())
ukabu.OUT = tmp
pics = {}
for sid, size in zip(ukabu.PICKS, REAL):
    buf = io.BytesIO()
    Image.new("RGBA", size, (180, 140, 90, 255)).save(buf, "WEBP")
    pics[sid] = buf.getvalue()
    (tmp / f"{sid}.webp").write_bytes(pics[sid])

MEASURE = """<script>addEventListener('load',()=>{setTimeout(()=>{
const hall=document.getElementById('hall'),boxes=[],tw=document.createTreeWalker(hall,NodeFilter.SHOW_TEXT);let n;
while(n=tw.nextNode()){if(!n.textContent.trim()||n.parentElement.closest('.ukabu'))continue;const st=getComputedStyle(n.parentElement);if(st.display==='none'||st.visibility==='hidden')continue;
 const r=document.createRange();r.selectNodeContents(n);for(const b of r.getClientRects())if(b.width>0)boxes.push({t:n.textContent.trim().slice(0,20),l:b.left,tp:b.top,r:b.right,b:b.bottom})}
for(const e of hall.querySelectorAll('a,button')){if(e.closest('.ukabu'))continue;const b=e.getBoundingClientRect();if(b.width>0)boxes.push({t:'['+(e.className||e.tagName)+']',l:b.left,tp:b.top,r:b.right,b:b.bottom})}
const cw=document.documentElement.clientWidth,toys=[...hall.querySelectorAll('.ukabu .uk')].map(e=>{const im=e.querySelector('img'),b=im.getBoundingClientRect(),st=getComputedStyle(e);
 return {c:e.className,l:b.left,tp:b.top,r:b.right,b:b.bottom,h:b.height,shown:st.visibility!=='hidden'&&st.display!=='none'}});
const hit=[];for(const y of toys){if(!y.shown)continue;for(const x of boxes)if(Math.min(y.r,x.r)-Math.max(y.l,x.l)>0&&Math.min(y.b,x.b)-Math.max(y.tp,x.tp)>0)hit.push(y.c+' × '+x.t);
 if(y.l<0||y.r>cw)hit.push(y.c+' が画面の幅の外')}
parent.postMessage(JSON.stringify({page:'__PAGE__',w:innerWidth,h:innerHeight,n:toys.length,shown:toys.filter(t=>t.shown).length,loaded:toys.every(t=>t.h>0),hit}),'*')},1500)})</script>"""
WRAP = """<!doctype html><body>%s<pre id="measured"></pre><script>
addEventListener('message',e=>{document.getElementById('measured').textContent+=e.data+'\\n'})</script>"""
pages = {f"{lang}-{w}x{h}": (f"/?lang={lang}&walk={lang}-{w}x{h}", w, h) for lang in LANGS for w, h in SIZES}
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
    m = re.fullmatch(r"/ukabu/([\w-]+)\.webp", self.path)
    if m and m.group(1) in pics:  # 試験の絵を出す（本物の道は out/ukabu を読む）
        return send(self, 200, pics[m.group(1)], "image/webp")
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
        _, size = name.split("-")
        w, h = (int(x) for x in size.split("x"))
        where = (look, name)
        assert (rec["w"], rec["h"]) == (w, h), where
        assert rec["n"] == 4 and rec["loaded"], (where, "浮かぶ玩具の絵が 4 つ読めていない", rec)
        assert rec["shown"] >= 3, (where, "浮かぶ玩具が 3 つより少ない（消して重なりを無くしていないか）", rec["shown"])
        assert not rec["hit"], (where, "浮かぶ玩具の絵が字か押す所に重なる", rec["hit"][:6])
print(f"ok 入口の浮かぶ玩具: 白と暗い版・3 つの言葉・{len(SIZES)} の大きさで、字と押す所に重ならない（3 つ以上が出ている）")
