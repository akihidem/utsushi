"""横置きの画面でも、手帖の手順の字が原画の釦と閉じる印の下に隠れず、作りながら見る頁の「次の手順へ」が最初の画面に入る。

なぜ: 11-07 の工作の前のまっさらな確かめで、幅 860 以上の横置き（1024×768 の iPad 横〜1920）だと、手帖の手順の字が右の列の頭に来て、
絶対配置の原画の釦（top 12・right 88）と閉じる印（top 12・right 12）の下に隠れた（御来迎と虎のほぼ全部の手）。作りながら見る頁は
1024×768 で「次の手順へ」が最初の画面の 11px 下にあった。縦置きの幅（390・768）では起きない。
./run.sh はブラウザなしで動く決まりで、ブラウザを操る道具も入れない（tests/test_voice_pause.py と同じ）。入っている Chrome で頁を
その大きさの iframe に開き、頁の中で手順を順に送って測る。Chrome が無い機械と、時間内に答えなかった時は、測れないと出して通す。
落ちるのは、測れて、字と釦が重なるか、押す所が最初の画面の外にある時だけ。
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

import html  # noqa: E402

from measure_tap import chrome  # noqa: E402
from web import genga, play_server  # noqa: E402

# 原画の写しは git の外（out/）にあり、まっさらな clone には無い。無いと原画の釦も作る時の畳みも出ず、重なりを見ない試験になる。
# そこで写しが無い時だけ、同じ形の絵の包み（頁の全体の絵が有る形）を返す。釦と畳みは本物の部品（techo_step._genga・genga.fold）が組む。
_real_pic = genga._pic


def _pic(sid, src, alt, lazy=False, href=None):
    got = _real_pic(sid, src, alt, lazy=lazy, href=href)
    return got if got[0] else (f'<span class="genga-pic" style="--genga-r:0.7000"><img src="data:," width="700" height="1000" alt="{html.escape(alt)}"></span>', True)


genga._pic = _pic

# 頁の名は URL の walk= に入るので ASCII にする（日本語は %XX に符号化され、見分けの正規表現に当たらなかった）
TOYS = {"goraigo": "NDL-1187053-R0000005-L", "tora": "NDL-1187053-R0000014-R"}
# 縦置きの幅も入れる（直しで縦置きを崩さない事も見る）。横置きは iPad 横・机の幅・大きい画面
TECHO_SIZES = [(390, 844), (768, 576), (1024, 768), (1180, 820), (1440, 900), (1920, 1080)]
# 作りながら見る頁は横置き（机の端に立てたタブレット）の大きさで見る。縦置きの 390×844 は、虎で「次の手順へ」が 15px 下に出る
# （手順の紙の絵が縦に長く、高さの上限 52svh まで使うため）。これは今回の直しの外で、別に知らせた
TSUKURU_SIZES = [(1024, 768), (1180, 820), (1440, 900)]

# 手帖: はじめるの後、手順を 1 つずつ送り、今の手順の字の行の矩形が、原画の釦・閉じる印・マイクと重なるか、
# 押す所（もどる・つぎ・こまった）の下の端が画面の外に出るかを測る。
TECHO_WALK = """<script>addEventListener('load',async()=>{
const wait=(ms=60)=>new Promise(r=>setTimeout(r,ms)),$=(id)=>document.getElementById(id),te=$('te'),total=+te.dataset.total,out=[];
const seen=(e)=>e&&!e.hidden&&getComputedStyle(e).display!=='none'&&e.getBoundingClientRect().width>0;
$('start').click();await wait();
for(let n=1;n<=total;n++){
 const li=document.querySelector('#steps li.on'),rg=document.createRange();rg.selectNodeContents(li);const rects=[...rg.getClientRects()].filter(a=>a.width>0);
 const hit=(id)=>{const e=$(id);if(!seen(e))return false;const b=e.getBoundingClientRect();return rects.some(a=>!(a.right<=b.left||b.right<=a.left||a.bottom<=b.top||b.bottom<=a.top))};
 const keys=[...document.querySelectorAll('.keys a,.keys button')].filter(seen);
 out.push({n,text:rects.length,thumb:hit('genga-thumb'),close:hit('close'),mic:hit('mic'),below:keys.some(k=>k.getBoundingClientRect().bottom>innerHeight+1)});
 if(n<total){$('next').click();await wait()}
}
parent.postMessage(JSON.stringify({page:'__PAGE__',w:innerWidth,h:innerHeight,thumb:seen($('genga-thumb')),out}),'*');
})</script>"""
# 作りながら見る: 開いた最初の画面で、一番大きい札「次の手順へ」の下の端が画面の中にあるか。
TSUKURU_WALK = """<script>addEventListener('load',async()=>{
await new Promise(r=>setTimeout(r,60));
const b=document.querySelector('#tiles button[value=next]').getBoundingClientRect();
parent.postMessage(JSON.stringify({page:'__PAGE__',w:innerWidth,h:innerHeight,bottom:b.bottom,height:b.height}),'*');
})</script>"""
WRAP = """<!doctype html><body>%s<pre id="measured"></pre><script>
addEventListener('message',e=>{document.getElementById('measured').textContent+=e.data+'\\n'})</script>"""

pages = {}
for name, sid in TOYS.items():
    for w, h in TECHO_SIZES:
        pages[f"techo-{name}-{w}x{h}"] = (f"/toy/{sid}/techo?v=1&n=1&walk=techo-{name}-{w}x{h}", w, h, TECHO_WALK)
    for w, h in TSUKURU_SIZES:
        pages[f"tsukuru-{name}-{w}x{h}"] = (f"/toy/{sid}/tsukuru?h=H-A&walk=tsukuru-{name}-{w}x{h}", w, h, TSUKURU_WALK)

send, get = play_server.Handler._send, play_server.Handler.do_GET


def wrapped(self, code, body, ctype="text/html; charset=utf-8", headers=()):
    m = re.search(r"[?&]walk=([\w-]+)", self.path)
    if m and m.group(1) in pages and isinstance(body, str) and ctype.startswith("text/html"):
        body += pages[m.group(1)][3].replace("__PAGE__", m.group(1))
    return send(self, code, body, ctype, headers)


def do_get(self):
    if self.path == "/__wrap":
        frames = "".join(f'<iframe src="{path.replace("&", "&amp;")}" width="{w}" height="{h}" style="border:0;display:block"></iframe>'
                         for path, w, h, _ in pages.values())
        return send(self, 200, WRAP % frames)
    return get(self)


exe = chrome()
if not exe:
    print("測れない: Chrome が無い")
    raise SystemExit(0)
play_server.Handler._send, play_server.Handler.do_GET = wrapped, do_get
server = play_server.serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"
for sid in TOYS.values():
    urllib.request.urlopen(urllib.request.Request(f"{base}/toy/{sid}/print", data=urllib.parse.urlencode({"hypothesis": "H-A"}).encode(),
                                                  headers={"Origin": base}), timeout=180)
try:
    with tempfile.TemporaryDirectory() as profile:
        out = subprocess.run([exe, "--headless=new", "--no-sandbox", "--disable-gpu", f"--user-data-dir={profile}", "--window-size=2000,1200",
                              "--virtual-time-budget=30000", "--dump-dom", f"{base}/__wrap"], capture_output=True, text=True, timeout=240).stdout
except subprocess.TimeoutExpired:
    out = ""
server.shutdown()
found = re.search(r'<pre id="measured">(.*?)</pre>', out, re.S)
got = {}
for line in (found.group(1).replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">") if found else "").splitlines():
    if line.strip():
        rec = json.loads(line)
        got[rec["page"]] = rec
if set(got) != set(pages):
    print(f"測れない: Chrome が {len(got)}/{len(pages)} 頁しか答えなかった（混んだ機械では起きる）: 無い {sorted(set(pages) - set(got))}")
    raise SystemExit(0)

bad = []
for page, rec in sorted(got.items()):
    _, w, h, _ = pages[page]
    # iframe の大きさが頁の画面の大きさになっている事（横置きの CSS が効く大きさで測れている事）
    assert (rec["w"], rec["h"]) == (w, h), (page, rec["w"], rec["h"])
    if page.startswith("techo-"):
        # 原画の釦がある玩具で測っている事（無いと、重なりを見ない試験になる）
        assert rec["thumb"], (page, "原画の釦が出ていない")
        assert rec["out"] and all(s["text"] for s in rec["out"]), (page, "手順の字が測れない")
        for s in rec["out"]:
            hits = [k for k in ("thumb", "close", "mic") if s[k]]
            if hits:
                bad.append(f"{page} 手順 {s['n']}: 字が {'・'.join(hits)} と重なる")
            if s["below"]:
                bad.append(f"{page} 手順 {s['n']}: 押す所が最初の画面の外")
    elif rec["height"] <= 0 or rec["bottom"] > h:
        bad.append(f"{page}: 「次の手順へ」の下の端 {rec['bottom']:.0f} が画面の高さ {h} の外")
for page, rec in sorted(got.items()):
    if page.startswith("tsukuru-"):
        print(f"{page}: 「次の手順へ」の下の端 {rec['bottom']:.0f} / 画面の高さ {rec['h']}")
assert not bad, "\n".join(bad)
print(f"ok 横置きと縦置き: 手帖 {len(TOYS) * len(TECHO_SIZES)} 通りで手順の字が原画の釦・閉じる印・マイクと重ならず、"
      f"作りながら見る {len(TOYS) * len(TSUKURU_SIZES)} 通りで「次の手順へ」が最初の画面に入る")
