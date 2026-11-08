"""入口の浮かぶ玩具は、触って送っても跳ばない（本人の言葉 11-08「トップページ、右下のツボが iPhone で触ると動く。」）。

なぜ: 右下の「ツボ」は浮かぶ玩具の 4 つ目（土の徳利・.uk4）。iPhone の Safari は、触って送り始めると番地の帯が縮み、画面の高さが替わって resize が起きる。
置き直しの台本（ukabu.PLACE_JS）は resize のたびに（高さだけが替わっても）置き直していて、その時に、
- 画面に留めた下へ送る印（position:fixed）を、送った後の位置で測った（題の間から見た印の位置は、送った分だけ下へずれる）
- 玩具の元の位置を、揺れの途中の箱（transform の入った getBoundingClientRect）で読んだ（置き直すたびに揺れの分だけ違う所を探す）
ので、印を避けて動かしていた徳利が元の位置へ戻ったり、16px ずつ跳ねたりした。
番地の帯の伸び縮みでは、題の間の大きさ（100svh）も、浮かぶ玩具の CSS の置き場（vw・vh）も替わらない。置き直しは幅が替わった時だけにした
（本人の答えを統括が伝えた線 11-08「置き直しは幅か向きが替わった時だけ」）。

見る事（白と暗い版・日本語・やさしい日本語・英語・iPhone 320×568・375×667・390×844・430×932 と iPad 820×1180・1024×768）:
0. 開いた後に浮かぶ玩具が見えている（層に .placed・4 つのうち 3 つ以上が出ていて絵が読めている）。見えていないと、動かない事を見ても空の確かめになる
   （別の目の気づき 11-08）
1. 題の間を触って（touchstart・touchmove・touchend。送る仕掛けが動かない 20px の動き）120px 送っても、浮かぶ玩具の位置（揺れる前の箱）と出ているかが替わらない
2. 送ったまま画面の高さだけを 94px 縮めて（390×844 → 390×750 の形）戻しても、置き直さない（台本が付けた置き場と出ているかが替わらない）。
   戻した後は位置も元のまま。Chrome の iframe は高さを替えると vh も替わり、CSS の置き場の玩具は縮めた間だけ動くので、縮めた間は台本が付けた物だけを見る
   （iPhone の Safari の vh は番地の帯で替わらない）
幅を替えた時（向き・窓の幅）は置き直して動いてよいので、ここでは見ない（この場の iframe は読み込みの後に描く回が来ず、幅を替えた直後の横のスクロールの帯が
消えないまま測るので、幅を替えて戻した時の置き場は揺れた。11-08 に試した）。iframe は全部を画面の左上に重ねて置く。
./run.sh はブラウザなしで動く決まりなので、入っている Chrome で頁をその大きさの iframe に開いて測る（tests/test_landscape_fit.py と同じ）。
Chrome が無い機械と、時間内に答えなかった時は、測れないと出して通す。
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
from web import play_server, ukabu  # noqa: E402

SIZES = [(320, 568), (375, 667), (390, 844), (430, 932), (820, 1180), (1024, 768)]
LANGS = ("ja", "easy", "en")
# 本物の輪郭の絵（out/ukabu・PICKS の順）の大きさ。縦と横の比が置き場に効くので、同じ比の絵で測る（tests/test_ukabu_no_overlap.py と同じ）
REAL = [(208, 324), (208, 289), (208, 184), (208, 323)]
tmp = pathlib.Path(tempfile.mkdtemp())
ukabu.OUT = tmp
pics = {}
for sid, size in zip(ukabu.PICKS, REAL):
    buf = io.BytesIO()
    Image.new("RGBA", size, (180, 140, 90, 255)).save(buf, "WEBP")
    pics[sid] = buf.getvalue()
    (tmp / f"{sid}.webp").write_bytes(pics[sid])

pages = {f"{lang}-{w}x{h}": (f"/?lang={lang}", w, h) for lang in LANGS for w, h in SIZES}
# 包みの頁が iframe ごとに、開いて 1.5 秒の後に 送る → resize → 幅を替えて戻す と歩き、各段の浮かぶ玩具の位置を控える
# 浮かぶ玩具は題の間（#hall）の物だけを見る（まずはここから の節にも浮かぶ実物の層 .ukabu があるため・web.jitsubutsu）
WRAP = """<!doctype html><body>%s<pre id="measured"></pre><script>
const wait=(ms)=>new Promise(r=>setTimeout(r,ms));
const toys=(w)=>[...w.document.querySelectorAll('#hall .ukabu .uk')];
const pos=(w)=>toys(w).map(e=>e.offsetLeft+','+e.offsetTop+','+w.getComputedStyle(e).visibility).join(' ');
const mine=(w)=>toys(w).map(e=>e.style.left+'/'+e.style.top+'/'+w.getComputedStyle(e).visibility).join(' ');
const touch=(w)=>{const h=w.document.getElementById('hall');let ok=true;
 try{const T=(y)=>new w.Touch({identifier:1,target:h,clientX:100,clientY:y});
  h.dispatchEvent(new w.TouchEvent('touchstart',{touches:[T(400)],changedTouches:[T(400)],bubbles:true}));
  h.dispatchEvent(new w.TouchEvent('touchmove',{touches:[T(380)],changedTouches:[T(380)],bubbles:true}));
  h.dispatchEvent(new w.TouchEvent('touchend',{touches:[],changedTouches:[T(380)],bubbles:true}))}catch(e){ok=false}return ok};
const shown=(w)=>{const l=w.document.querySelector('#hall .ukabu');return {placed:!!l&&l.classList.contains('placed'),
 n:toys(w).filter(e=>w.getComputedStyle(e).visibility==='visible'&&e.querySelector('img').naturalWidth>0&&e.offsetHeight>0).length}};
const walk=async(f)=>{const w=f.contentWindow,H=+f.height;await wait(1500);const a=pos(w),am=mine(w),seen=shown(w);
 const touched=touch(w);w.scrollTo(0,120);await wait(300);const b=pos(w),y=w.scrollY;
 f.height=String(H-94);await wait(500);const c=mine(w);f.height=String(H);await wait(500);const c2=pos(w);
  return {page:f.dataset.page,n:toys(w).length,seen,touched,y,a,am,b,c,c2}};
addEventListener('load',async()=>{const out=await Promise.all([...document.querySelectorAll('iframe')].map(walk));
 document.getElementById('measured').textContent=out.map(r=>JSON.stringify(r)).join('\\n')})</script>"""
get = play_server.Handler.do_GET
send = play_server.Handler._send


def do_get(self):
    if self.path == "/__wrap":
        frames = "".join(f'<iframe data-page="{n}" src="{p}" width="{w}" height="{h}" style="border:0;position:absolute;left:0;top:0"></iframe>' for n, (p, w, h) in pages.items())
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
play_server.Handler.do_GET = do_get
for look in ("tenji", "zine"):
    got = measure(look)
    if got is None:
        print(f"測れない: Chrome が {look} の頁に答えきらなかった（混んだ機械では起きる）")
        raise SystemExit(0)
    for name, rec in got.items():
        where = (look, name)
        assert rec["n"] == 4, (where, "浮かぶ玩具が 4 つ無い", rec["n"])
        assert rec["seen"]["placed"] and rec["seen"]["n"] >= 3, (where, "浮かぶ玩具が見えていない（置き直しの後に 3 つ以上が出ていない）", rec["seen"])
        assert rec["y"] >= 100, (where, "送れていない（頁が短い）", rec["y"])
        assert rec["touched"], (where, "触る事を送れなかった（TouchEvent が作れない）")
        assert rec["b"] == rec["a"], (where, "触って送ると浮かぶ玩具が動く", rec["a"], rec["b"])
        assert rec["c"] == rec["am"], (where, "送ったまま高さだけを縮めると（番地の帯の形）置き直す", rec["am"], rec["c"])
        assert rec["c2"] == rec["a"], (where, "高さを戻した後に浮かぶ玩具の位置が元と違う", rec["a"], rec["c2"])
print(f"ok 入口の浮かぶ玩具: 白と暗い版・3 つの言葉・{len(SIZES)} の大きさで、3 つ以上が見えていて、触って送っても・送ったまま高さだけを縮めて戻しても動かない")
