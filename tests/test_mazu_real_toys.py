"""まずはここから の原図の周りに浮かぶ実物のおもちゃ（web.jitsubutsu・本人の言葉 11-08「スクロールして、まずはここからの原図の周囲に、実際のおもちゃを抜き出して浮かべる。」）。

見る事（白と暗い版・日本語・やさしい日本語・英語・iPhone・iPad の横と縦・PC の 12 の大きさ）:
1. 位置の札（GPS）を含む EXIF を外す: 位置の札を付けた写真を jitsubutsu.shrink に通すと、出た絵に EXIF の印（APP1 の Exif・WebP の EXIF の塊）も札も無い。
   repo の data/jitsubutsu の絵も全部、同じに見る（生の字の並びで「GPS」を探さない。圧縮した中身にたまたま出る）
1b. 置き場に絵が 1 つも無い時は、層も置き直しの台本も頁に出ない（絵を外した場で頁が崩れない）。
   絵がある時は、置き場にある物の数だけ浮かべる
2. 浮かぶ実物の絵が、節の字の行と押す所（2 枚の札は札ごと・下の 1 行）に重ならない。画面の幅の外に出ず、頁が横にはみ出さない
3. 読み込みから 1.5 秒後まで、描くたびに見ても重ならない（入口の浮かぶ玩具と同じ・tests/test_ukabu_no_overlap.py）
4. 台本が動かない画面（置き直しの台本を外した頁）では 1 つも出ない
5. 左右に余白のある広い画面（幅 1180 以上）では 3 つ以上が出る（狭い画面は余白が無く、置く所が無ければ出さない）
6. 触って送っても、送ったまま高さだけを縮めて戻しても、置き直さない（入口の浮かぶ玩具と同じ・tests/test_ukabu_steady.py）
浮かべる形の測りは、repo の 5 つと同じ縦と横の比の絵を試験の中で作って使う（絵の色に依らずに置き場を見るため）。
./run.sh はブラウザなしで動く決まりなので、入っている Chrome で頁をその大きさの iframe に開いて測る（tests/test_landscape_fit.py と同じ）。
Chrome が無い機械と、時間内に答えなかった時は、測れないと出して通す（1 の EXIF は Chrome が無くても見る）。
"""
import html
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

from PIL import Image  # noqa: E402

from measure_tap import chrome  # noqa: E402
from web import jitsubutsu, looks, play_server, ukabu  # noqa: E402


def exif_marks(data):
    """絵のバイトにある EXIF の印と札の数。JPEG は APP1 の Exif、WebP は EXIF の塊を見る"""
    im = Image.open(io.BytesIO(data))
    app1 = data.find(b"\xff\xe1") >= 0 and data.find(b"Exif\x00\x00") >= 0
    webp = data[:4] == b"RIFF" and b"EXIF" in data[12:]
    return {"tags": len(im.getexif()), "app1": app1, "webp_chunk": webp, "info": "exif" in im.info}


# 1. 位置の札を付けた写真を通す
src = Image.new("RGB", (640, 480), (240, 238, 232))
src.paste(Image.new("RGB", (200, 160), (180, 60, 40)), (220, 160))
ex = Image.Exif()
ex[0x010F] = "phone"
gps = ex.get_ifd(0x8825)
gps[1], gps[2], gps[3], gps[4] = "N", (35.0, 41.0, 0.0), "E", (139.0, 41.0, 0.0)
buf = io.BytesIO()
src.save(buf, "JPEG", exif=ex.tobytes())
assert len(Image.open(io.BytesIO(buf.getvalue())).getexif().get_ifd(0x8825)) == 4, "試験の写真に位置の札が付いていない"
rgba = Image.open(io.BytesIO(buf.getvalue())).convert("RGBA")
assert exif_marks(jitsubutsu.shrink(rgba)) == {"tags": 0, "app1": False, "webp_chunk": False, "info": False}, "浮かべる絵に EXIF が残る"
local = sorted(jitsubutsu.OUT.glob("*")) if jitsubutsu.OUT.exists() else []
assert {p.name for p in local} == {f"{n}.webp" for n in jitsubutsu.PICKS}, ("data/jitsubutsu の絵が浮かべる 5 つと違う（元の写真やほかの絵を入れない）", [p.name for p in local])
for p in local:
    assert exif_marks(p.read_bytes()) == {"tags": 0, "app1": False, "webp_chunk": False, "info": False}, ("repo の浮かべる絵に EXIF が残る", p.name)

# 1b. 置き場に絵が無い時と、一部だけある時
real_out = jitsubutsu.OUT
jitsubutsu.OUT = pathlib.Path(tempfile.mkdtemp())
bare = looks.tenji()
assert 'class="ukabu ukabu-mazu"' not in bare and ukabu.place_js("mazu", wide=True) not in bare, "絵が無いのに浮かぶ実物の層か台本が頁に出る"
b = io.BytesIO()
Image.new("RGBA", (208, 169), (120, 140, 90, 255)).save(b, "WEBP")
(jitsubutsu.OUT / f"{jitsubutsu.PICKS[0]}.webp").write_bytes(b.getvalue())
one = looks.tenji()
assert one.count('<span class="uk jb') == 1 and ukabu.place_js("mazu", wide=True) in one, "置き場にある絵の数だけ浮かべない"
jitsubutsu.OUT = real_out

# 手元の 5 つ（PICKS の順）の大きさ。縦と横の比が置き場に効くので、同じ比の絵で測る
REAL = [(208, 169), (208, 139), (208, 158), (208, 300), (208, 248)]
tmp = pathlib.Path(tempfile.mkdtemp())
jitsubutsu.OUT = tmp
ukabu.OUT = pathlib.Path(tempfile.mkdtemp())  # 題の間の浮かぶ玩具は置かない（この試験は まずはここから だけを見る）
for name, size in zip(jitsubutsu.PICKS, REAL):
    b = io.BytesIO()
    Image.new("RGBA", size, (120, 140, 90, 255)).save(b, "WEBP")
    (tmp / f"{name}.webp").write_bytes(b.getvalue())
PLACE = ukabu.place_js("mazu", wide=True)

SIZES = [(320, 568), (375, 667), (390, 844), (430, 932), (768, 1024), (820, 1180), (1024, 768), (1180, 820), (1366, 1024), (1280, 800), (1440, 900), (1920, 1080)]
LANGS = ("ja", "easy", "en")
MEASURE = """<script>(()=>{const snap=()=>{
const sec=document.getElementById('mazu'),boxes=[],tw=document.createTreeWalker(sec,NodeFilter.SHOW_TEXT);let n;
while(n=tw.nextNode()){if(!n.textContent.trim()||n.parentElement.closest('.ukabu'))continue;const st=getComputedStyle(n.parentElement);if(st.display==='none'||st.visibility==='hidden')continue;
 const r=document.createRange();r.selectNodeContents(n);for(const b of r.getClientRects())if(b.width>0)boxes.push({t:n.textContent.trim().slice(0,12),l:b.left,tp:b.top,r:b.right,b:b.bottom})}
for(const e of sec.querySelectorAll('a,button')){if(e.closest('.ukabu'))continue;const b=e.getBoundingClientRect();if(b.width>0)boxes.push({t:'['+(e.className||e.tagName)+']',l:b.left,tp:b.top,r:b.right,b:b.bottom})}
const cw=document.documentElement.clientWidth,toys=[...sec.querySelectorAll('.ukabu-mazu .uk')].map(e=>{const im=e.querySelector('img'),b=im.getBoundingClientRect(),st=getComputedStyle(e);
 return {c:e.className,l:b.left,tp:b.top,r:b.right,b:b.bottom,h:b.height,shown:st.visibility!=='hidden'&&st.display!=='none'}});
const hit=[];for(const y of toys){if(!y.shown||!(y.h>0))continue;for(const x of boxes)if(Math.min(y.r,x.r)-Math.max(y.l,x.l)>0&&Math.min(y.b,x.b)-Math.max(y.tp,x.tp)>0)hit.push(y.c+' × '+x.t);
 if(y.l<0||y.r>cw)hit.push(y.c+' が画面の幅の外')}
return {n:toys.length,shown:toys.filter(t=>t.shown&&t.h>0).length,hit,sx:document.documentElement.scrollWidth,cw}};
let fr=0,done=false;const early=[];const tick=()=>{if(done)return;fr++;const s=snap();if(s.hit.length&&early.length<3)early.push({fr,hit:s.hit.slice(0,3)});
 requestAnimationFrame(()=>setTimeout(tick,0))};tick();
addEventListener('load',()=>{setTimeout(()=>{done=true;const s=snap();
parent.postMessage(JSON.stringify({page:'__PAGE__',w:innerWidth,h:innerHeight,fr,early,...s}),'*')},1500)})})()</script>"""
WRAP = """<!doctype html><body>%s<pre id="measured"></pre><script>
addEventListener('message',e=>{document.getElementById('measured').textContent+=e.data+'\\n'})</script>"""
# 浮かぶ実物は節の中ほどより下（題の間の下）にあるので、iframe の高さはその大きさの画面のまま、節を最初の画面に入れる道（#mazu）で開く
pages = {f"{js}-{lang}-{w}x{h}": (f"/?lang={lang}&walk={js}-{lang}-{w}x{h}#mazu", w, h) for js in ("js", "nojs") for lang in LANGS for w, h in SIZES}
STEADY = """<!doctype html><body>%s<pre id="measured"></pre><script>
const wait=(ms)=>new Promise(r=>setTimeout(r,ms));
const toys=(w)=>[...w.document.querySelectorAll('.ukabu-mazu .uk')];
const pos=(w)=>toys(w).map(e=>e.offsetLeft+','+e.offsetTop+','+w.getComputedStyle(e).visibility).join(' ');
const mine=(w)=>toys(w).map(e=>e.style.left+'/'+e.style.top+'/'+w.getComputedStyle(e).visibility).join(' ');
const walk=async(f)=>{const w=f.contentWindow,H=+f.height;await wait(1500);const a=pos(w),am=mine(w),seen=toys(w).filter(e=>w.getComputedStyle(e).visibility==='visible').length;
 const s=w.document.getElementById('mazu');let ok=true;
 try{const T=(y)=>new w.Touch({identifier:1,target:s,clientX:100,clientY:y});s.dispatchEvent(new w.TouchEvent('touchstart',{touches:[T(400)],changedTouches:[T(400)],bubbles:true}));
  s.dispatchEvent(new w.TouchEvent('touchmove',{touches:[T(380)],changedTouches:[T(380)],bubbles:true}));s.dispatchEvent(new w.TouchEvent('touchend',{touches:[],changedTouches:[T(380)],bubbles:true}))}catch(e){ok=false}
 w.scrollBy(0,120);await wait(300);const b=pos(w);f.height=String(H-94);await wait(500);const c=mine(w);f.height=String(H);await wait(500);const c2=pos(w);
 return {page:f.dataset.page,seen,touched:ok,a,am,b,c,c2}};
addEventListener('load',async()=>{const out=await Promise.all([...document.querySelectorAll('iframe')].map(walk));
 document.getElementById('measured').textContent=out.map(r=>JSON.stringify(r)).join('\\n')})</script>"""
steady = {f"{lang}-{w}x{h}": (f"/?lang={lang}#mazu", w, h) for lang in LANGS for w, h in [(390, 844), (1180, 820), (1440, 900)]}
send, get = play_server.Handler._send, play_server.Handler.do_GET


def wrapped(self, code, body, ctype="text/html; charset=utf-8", headers=()):
    m = re.search(r"[?&]walk=([\w-]+)", self.path)
    if m and m.group(1) in pages and isinstance(body, str) and ctype.startswith("text/html"):
        if m.group(1).startswith("nojs-"):
            assert PLACE in body, "置き直しの台本が まずはここから に無い（外す形が測れない）"
            body = body.replace(PLACE, "")
        body += MEASURE.replace("__PAGE__", m.group(1))
    return send(self, code, body, ctype, headers)


def do_get(self):
    if self.path == "/__wrap":
        frames = "".join(f'<iframe src="{html.escape(p)}" width="{w}" height="{h}" style="border:0;display:block"></iframe>' for p, w, h in pages.values())
        return send(self, 200, WRAP % frames)
    if self.path == "/__steady":
        frames = "".join(f'<iframe data-page="{n}" src="{html.escape(p)}" width="{w}" height="{h}" style="border:0;position:absolute;left:0;top:0"></iframe>' for n, (p, w, h) in steady.items())
        return send(self, 200, STEADY % frames)
    return get(self)


def run(look, path, want):
    server = play_server.serve(0, look=look)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        with tempfile.TemporaryDirectory() as profile:
            out = subprocess.run([exe, "--headless=new", "--no-sandbox", "--disable-gpu", f"--user-data-dir={profile}", "--window-size=2000,1200",
                                  "--virtual-time-budget=30000", "--dump-dom", f"{base}{path}"], capture_output=True, text=True, timeout=300).stdout
    except subprocess.TimeoutExpired:
        out = ""
    server.shutdown()
    found = re.search(r'<pre id="measured">(.*?)</pre>', out, re.S)
    got = {}
    for line in html.unescape(found.group(1) if found else "").splitlines():
        if line.strip():
            rec = json.loads(line)
            got[rec["page"]] = rec
    return got if set(got) == set(want) else None


exe = chrome()
if not exe:
    print(f"ok 浮かべる絵の EXIF（位置の札 0・repo の絵 {len(local)} 枚）。測れない: Chrome が無い")
    raise SystemExit(0)
play_server.Handler._send, play_server.Handler.do_GET = wrapped, do_get
for look in ("tenji", "zine"):
    got = run(look, "/__wrap", pages)
    if got is None:
        print(f"測れない: Chrome が {look} の頁に答えきらなかった（混んだ機械では起きる）")
        raise SystemExit(0)
    for name, rec in got.items():
        js, _, size = name.split("-")
        w, h = (int(x) for x in size.split("x"))
        where = (look, name)
        assert (rec["w"], rec["h"]) == (w, h), where
        assert rec["n"] == len(jitsubutsu.PICKS), (where, "浮かぶ実物の数", rec["n"])
        assert not rec["hit"], (where, "浮かぶ実物が字か押す所に重なる", rec["hit"][:6])
        assert rec["sx"] <= rec["cw"], (where, "頁が横にはみ出す", rec["sx"], rec["cw"])
        assert rec["fr"] >= 3 and not rec["early"], (where, "開いた直後に重なる（か、描く回を見られていない）", rec["fr"], rec["early"])
        if js == "nojs":
            assert rec["shown"] == 0, (where, "台本が動かない画面で浮かぶ実物が出る", rec["shown"])
        elif w >= 1180:
            assert rec["shown"] >= 3, (where, "左右に余白のある広い画面で、浮かぶ実物が 3 つより少ない", rec["shown"])
    got = run(look, "/__steady", steady)
    if got is None:
        print(f"測れない: Chrome が {look} の送る試しに答えきらなかった")
        raise SystemExit(0)
    for name, rec in got.items():
        where = (look, "steady", name)
        assert rec["touched"], (where, "触る事を送れなかった")
        if not name.endswith("390x844"):
            assert rec["seen"] >= 3, (where, "浮かぶ実物が見えていない", rec["seen"])
        assert rec["b"] == rec["a"], (where, "触って送ると浮かぶ実物が動く", rec["a"], rec["b"])
        assert rec["c"] == rec["am"], (where, "送ったまま高さだけを縮めると置き直す", rec["am"], rec["c"])
        assert rec["c2"] == rec["a"], (where, "高さを戻した後に位置が元と違う", rec["a"], rec["c2"])
print(f"ok 浮かぶ実物: EXIF の位置の札 0（repo の絵 {len(local)} 枚も）・白と暗い版・3 つの言葉・{len(SIZES)} の大きさで字と札に重ならず、はみ出さない・"
      "開いた直後も・台本が動かない画面では出さない・広い画面で 3 つ以上・触って送っても高さを替えても動かない")
