"""幅 390 の画面で、押す所の高さと字の大きさ（#137）、字の欄の幅（#290）を実測する。手で回す道具で、./run.sh の試験ではない。

なぜ試験にしないか: ./run.sh はブラウザなしで動く決まり。ブラウザを操る道具（playwright など）も入れない決まりなので、
入っている Chrome を headless で開き、頁に測る script を差し込んで、結果を DOM から読む。

    PYTHONPATH=src .venv/bin/python tests/measure_tap.py [幅]
exit code: 0 = 床を満たす / 3 = 満たさない所がある / 4 = Chrome が無いなどで測れない。
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.parse
import urllib.request

os.environ.setdefault("OMOCHAE_DATA", tempfile.mkdtemp())

from omochae import loop, records  # noqa: E402
from web import play_server  # noqa: E402

MIN_TAP, MIN_FONT = 44, 12
G = "NDL-1187053-R0000005-L"
# kazasu と tsukuru の頁は入れていない。#242 の枝で形が変わるので、床はそこで入れる
PAGES = ["/", "/about", "/toys", f"/toy/{G}", "/zukan", f"/zukan/{G}", f"/zukan/{G}/yomi", "/gallery", "/loop", f"/loop/{G}", "/no-such-page"]
# 文の中のリンクは床の外（本文の要件）。親に字があって、自分が inline の物
# load を待たない。図の読み込みが遅い頁で、時間切れの前に測れなくなる。押す所の高さと字の大きさは図に頼らない
MEASURE = """<script>setTimeout(()=>{
document.querySelectorAll('details').forEach(d=>{d.open=true}); // 畳んだ欄（次の版など）の中も測る
const vis=e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return r.width>0&&r.height>0&&s.visibility!=='hidden'&&s.display!=='none'};
const name=e=>e.tagName.toLowerCase()+(e.className&&e.className.baseVal===undefined&&e.className?'.'+String(e.className).trim().split(/\\s+/)[0]:'')+' '+(e.innerText||e.value||e.type||'').trim().replace(/\\s+/g,' ').slice(0,14);
const inSentence=e=>{if(e.tagName!=='A'||getComputedStyle(e).display!=='inline')return false;return [...e.parentElement.childNodes].some(n=>n.nodeType===3&&n.textContent.trim())};
// label の中の入力は、外の label が押す所なので label を測る。読み上げ用に隠した label（1px 四方に畳んだ物、画面の外へ出した物）は押す所でない
const hiddenLabel=e=>{if(e.tagName!=='LABEL')return false;const r=e.getBoundingClientRect();return r.height<=2||r.right<=0};
const tap=[...document.querySelectorAll('a,button,input,select,summary,label,textarea')].filter(e=>e.type!=='hidden'&&vis(e)&&!inSentence(e)&&!(e.tagName==='INPUT'&&e.closest('label'))&&!hiddenLabel(e));
const low=tap.map(e=>[name(e),Math.round(e.getBoundingClientRect().height)]).filter(x=>x[1]<%d);
const small={};for(const e of document.querySelectorAll('body *')){if(!vis(e)||![...e.childNodes].some(n=>n.nodeType===3&&n.textContent.trim()))continue;const f=parseFloat(getComputedStyle(e).fontSize);if(f<%d){const k=(e.className&&e.className.baseVal===undefined&&e.className?'.'+String(e.className).trim().split(/\\s+/)[0]:e.tagName.toLowerCase())+' '+f;small[k]=(small[k]||0)+1}}
// 帯の段ごとの項目の数。1 つだけ次の行に落ちていないかを見る（#125）
// 縦の中心が近い物を同じ段と数える。top で数えると、今いる項目の下の罫の分だけずれて、同じ段を別の段と数えた
const rows=[];for(const a of document.querySelectorAll('.nav a')){if(!vis(a))continue;const r=a.getBoundingClientRect(),c=(r.top+r.bottom)/2,hit=rows.find(x=>Math.abs(x.c-c)<14);if(hit)hit.n++;else rows.push({c,n:1})}
// 字の欄と選ぶ欄は、名前の下で箱の幅いっぱいに出す（#290）。箱は label の親の、枠と余白を除いた幅
const wide=[...document.querySelectorAll('label:not(.sr)>input[type=text],label:not(.sr)>textarea,label:not(.sr)>select')].filter(vis);
const narrow=wide.filter(f=>{const l=f.parentElement,p=l.parentElement,s=getComputedStyle(p),box=p.clientWidth-parseFloat(s.paddingLeft)-parseFloat(s.paddingRight),r=f.getBoundingClientRect(),n=[...l.childNodes].find(x=>x.nodeType===3&&x.textContent.trim());if(r.width<box-1)return true;if(!n)return false;const t=document.createRange();t.selectNodeContents(n);return r.top<t.getBoundingClientRect().bottom-1}).map(f=>name(f.parentElement));
parent.postMessage(JSON.stringify({w:innerWidth,tap:tap.length,low,small,sx:document.documentElement.scrollWidth,nav:rows.map(x=>x.n),wide:wide.length,narrow}),'*');
},800)</script>""" % (MIN_TAP, MIN_FONT)
# Chrome の新しい headless は窓の幅が 500 より狭くならない。CSS の幅の判定は iframe の幅で働くので、幅を決めた iframe に入れて測り、結果を親へ渡す
WRAP = """<!doctype html><body><iframe src="%s" width="%d" height="844" style="border:0"></iframe><script>
addEventListener('message',e=>{const p=document.createElement('pre');p.id='measured';p.textContent=e.data;document.body.append(p)})</script>"""


def inject(cls):
    """頁の終わりに測る script を足し、測る頁を入れる親の頁を同じサーバから出す。

    親と頁の origin が違うと、iframe が別のプロセスになり、--virtual-time-budget の計測の外になって、測る前に DOM が書き出された。
    """
    send, get = cls._send, cls.do_GET

    def wrapped(self, code, body, ctype="text/html; charset=utf-8", headers=()):
        if isinstance(body, str) and ctype.startswith("text/html"):
            body = body + MEASURE
        return send(self, code, body, ctype, headers)

    def do_get(self):
        if self.path.startswith("/__wrap?"):
            qs = urllib.parse.parse_qs(self.path.partition("?")[2])
            return send(self, 200, WRAP % (qs["u"][0], int(qs["w"][0])))
        return get(self)
    cls._send, cls.do_GET = wrapped, do_get


def chrome():
    for name in ("google-chrome", "chromium", "chromium-browser"):
        if shutil.which(name):
            return shutil.which(name)
    return None


def measure(exe, base, path, width):
    url = f"{base}/__wrap?w={width}&u={urllib.parse.quote(path, safe='')}"
    with tempfile.TemporaryDirectory() as profile:
        r = subprocess.run([exe, "--headless=new", "--no-sandbox", "--disable-gpu", f"--user-data-dir={profile}", "--window-size=800,900",
                            "--virtual-time-budget=6000", "--dump-dom", url], capture_output=True, text=True, timeout=120)
    m = re.search(r'<pre id="measured">(.*?)</pre>', r.stdout, re.S)
    if not m:
        return None
    return json.loads(m.group(1).replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">"))


def main():
    width = int(sys.argv[1]) if len(sys.argv) > 1 else 390
    exe = chrome()
    if not exe:
        print("検査できない: Chrome が無い", file=sys.stderr)
        return 4
    inject(play_server.Handler)
    # 頁の予想の段と手帖は、置き場の記録で形が変わる（#242 で予想の段が外れるまで）。1 回だけ作り、皮ごとのサーバで同じ記録を見る
    records.add({"source_id": G, "hypothesis_id": "H-A", "sheet_version": 1, "result": "動いた"})
    pages = PAGES + [f"/toy/{G}/techo", f"/toy/{G}/tsukuru"]
    printed, bad = False, 0
    for look in ("tenji", "zine"):
        # 皮はサーバごとに 1 つ（本人の決定 11-05）。?look= は効かない
        server = play_server.serve(0, look=look)
        base = f"http://127.0.0.1:{server.server_address[1]}"
        threading.Thread(target=server.serve_forever, daemon=True).start()
        if not printed:
            data = urllib.parse.urlencode({"hypothesis": "H-A"}).encode()
            urllib.request.urlopen(urllib.request.Request(f"{base}/toy/{G}/print", data=data, headers={"Origin": base}), timeout=120)
            # 説明まで残した記録に「次の版」の欄が出る（#290）
            rid, _ = records.add({"source_id": G, "hypothesis_id": "H-A", "sheet_version": 1, "result": "動いた"})
            assert loop.save_explanation(rid, "測る道具", "途中で止まった", "軸を長くする") == []
            printed = True
        for path in pages:
            got = measure(exe, base, path, width)
            if got is None:
                print(f"測れない: {look} {path}", file=sys.stderr)
                return 4
            if got["w"] > width:
                print(f"検査できない: 窓の幅が {got['w']} で {width} にならない", file=sys.stderr)
                return 4
            kinds = sorted({re.sub(r" .*", "", x[0]) for x in got["low"]})
            print(f"{look:6} {path[:28]:28} 押す所 {got['tap']:3}・{MIN_TAP} 未満 {len(got['low']):3} {kinds[:5]}  小さい字 {sum(got['small'].values()):3} {list(got['small'])[:4]}  横幅 {got['sx']}  帯の段 {got['nav']}  字の欄 {got['wide']}・細い {len(got['narrow'])} {got['narrow'][:2]}")
            bad += len(got["low"]) + sum(got["small"].values()) + len(got["narrow"])
            bad += sum(1 for i, n in enumerate(got["nav"]) if i and n == 1)  # 2 段目より後に 1 つだけ落ちた項目
        server.shutdown()
    print(f"満たさない所 {bad}")
    return 3 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
