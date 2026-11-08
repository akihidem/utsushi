"""入口の題の間: 英語の頁だけ、題・副題・英字が横書きで、題字「うつし」の下に読み（looks.YOMI）があり、左右の真ん中にそろう（本人の言葉 11-08）。

本人の言葉: 「トップページ、英語版は余白維持で横書きにしてください。うつし、のひらがなの下に utushi と読みをいれる。」（綴りの答え「utsushi。」）、
続けて「英語は英語モードの時のみ横書きで、他はかえない。iPhoneで見ると英語モードの左右のバランスがズレてる。Utsushiはすこし大きめのほうがいい。」
見る事（白と暗い版の入口・日本語・やさしい日本語・英語の頁・幅 320×568・375×667・390×844・430×932・1440×900）:
1. 日本語とやさしい日本語の頁は #644 の前の形: 読みを出さない・題は縦書き（広い画面では副題と英字も縦書き）
2. 英語の頁: 題・副題・英字が横書き。副題は 3 行で 1 つの句。読みの字は looks.YOMI で、ひらがなの真下にあり、副題の字より 1.25 倍以上大きい
3. 英語の頁の左右の真ん中: 真ん中に寄せる字（題のひらがな・読み。1 列に積む幅では英字と副題の行も）の、字の見える所の左右の余白の差が 4px 以内
   （字の間は最後の字の後にも付くので、右の端から字の間を除いて測る。画面の幅はスクロールの帯を除いた幅）
4. 英字の 1 行・題・副題・このサイトについて が互いに重ならない。題の間の字が画面の幅の外に出ず、頁が横にはみ出さない。幅 390×844 と 1440×900 で このサイトについて が最初の画面の中
./run.sh はブラウザなしで動く決まりなので、入っている Chrome で頁をその大きさの iframe に開いて測る（tests/test_landscape_fit.py と同じ）。
Chrome が無い機械と、時間内に答えなかった時は、測れないと出して通す。
"""
import json
import os
import re
import subprocess
import tempfile
import threading

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ.pop("ANTHROPIC_API_KEY", None)

import html  # noqa: E402

from measure_tap import chrome  # noqa: E402
from web import looks, play_server  # noqa: E402

SIZES = [(320, 568), (375, 667), (390, 844), (430, 932), (1440, 900)]
LANGS = ("ja", "easy", "en")
MEASURE = """<script>addEventListener('load',()=>{setTimeout(()=>{
const q=(s)=>document.querySelector(s),box=(e)=>{if(!e)return null;const r=e.getBoundingClientRect();return {l:r.left,t:r.top,r:r.right,b:r.bottom,w:r.width,h:r.height}};
const hall=q('#hall'),kana=q('#hall h1 .kana'),yomi=q('#hall h1 .yomi');
const about=[...hall.querySelectorAll('a')].find(a=>(a.getAttribute('href')||'').startsWith('/about'));
const wm=(e)=>e?getComputedStyle(e).writingMode:null;
const cw=document.documentElement.clientWidth,lines=(e)=>{const out=[];if(!e)return out;const tw=document.createTreeWalker(e,NodeFilter.SHOW_TEXT);let n;
 while(n=tw.nextNode()){if(!n.textContent.trim())continue;const ls=parseFloat(getComputedStyle(n.parentElement).letterSpacing)||0,r=document.createRange();r.selectNodeContents(n);
 for(const b of r.getClientRects())if(b.width>0)out.push([b.left,cw-(b.right-ls)])}return out};
parent.postMessage(JSON.stringify({page:'__PAGE__',w:innerWidth,h:innerHeight,lang:document.documentElement.lang,sx:document.documentElement.scrollWidth,
 kana:box(kana),yomi:box(yomi),h1:box(q('#hall h1')),sub:box(q('#hall .sub')),en:box(q('#hall .en')),about:box(about),
 sub_text:q('#hall .sub')?q('#hall .sub').innerText:null,yomi_text:yomi?yomi.textContent:null,yomi_px:yomi?parseFloat(getComputedStyle(yomi).fontSize):0,sub_px:parseFloat(getComputedStyle(q('#hall .sub')).fontSize),yomi_shown:!!yomi&&getComputedStyle(yomi).display!=='none',bal:{kana:lines(kana),yomi:lines(yomi),en:lines(q('#hall .en')),sub:lines(q('#hall .sub'))},
 wm:{h1:wm(q('#hall h1')),sub:wm(q('#hall .sub')),en:wm(q('#hall .en'))}}),'*')},500)})</script>"""
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
    return get(self)


def measure(look):
    """皮 look のサイト（tenji 白・zine 暗い版）を立て、全部の頁を 1 回の Chrome で測る。答えが揃わなければ None"""
    server = play_server.serve(0, look=look)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        with tempfile.TemporaryDirectory() as profile:
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


def overlap(a, b):
    return a and b and min(a["r"], b["r"]) - max(a["l"], b["l"]) > 1 and min(a["b"], b["b"]) - max(a["t"], b["t"]) > 1


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
        assert rec["lang"] == ("en" if lang == "en" else "ja"), (where, rec["lang"])
        if lang != "en":
            # 1. 日本語とやさしい日本語は #644 の前の形
            assert not rec["yomi_shown"], (where, "日本語の頁に読みが出た")
            assert rec["wm"]["h1"] == "vertical-rl", (where, rec["wm"])
            if w > 820:
                assert rec["wm"]["sub"] == "vertical-rl" and rec["wm"]["en"] == "vertical-rl", (where, rec["wm"])
        else:
            # 2. 英語は横書き・副題は 1 つの句・読みはひらがなの真下で、副題より大きい
            assert rec["wm"] == {"h1": "horizontal-tb", "sub": "horizontal-tb", "en": "horizontal-tb"}, (where, rec["wm"])
            assert [x.strip() for x in rec["sub_text"].splitlines() if x.strip()] == ["From Edo nishiki", "the lost movements of toys", "brought back to life in paper"], (where, rec["sub_text"])
            k, y = rec["kana"], rec["yomi"]
            assert rec["yomi_shown"] and rec["yomi_text"] == looks.YOMI, (where, rec["yomi_text"])
            assert rec["yomi_px"] >= 1.25 * rec["sub_px"], (where, "読みが副題とはっきり違う大きさでない", rec["yomi_px"], rec["sub_px"])
            assert y["t"] >= k["b"] - 1 and k["l"] - 2 <= (y["l"] + y["r"]) / 2 <= k["r"] + 2, (where, "読みがひらがなの下に無い", k, y)
            # 3. 左右の真ん中（1 列に積む幅は英字と副題の行も）
            for part in (("kana", "yomi") if w > 820 else ("kana", "yomi", "en", "sub")):
                for left, right in rec["bal"][part]:
                    assert abs(left - right) <= 4, (where, f"{part} の左右の余白が {left:.0f}px と {right:.0f}px", rec["bal"][part])
        # 4. 重ならない・はみ出さない
        parts = {n: rec[n] for n in ("en", "h1", "sub", "about")}
        for i, a in enumerate(parts):
            for b in list(parts)[i + 1:]:
                assert not overlap(parts[a], parts[b]), (where, f"{a} と {b} が重なる", parts[a], parts[b])
        for n, r in parts.items():
            assert r and r["l"] >= -1 and r["r"] <= w + 1, (where, f"{n} が画面の幅の外", r)
        assert rec["sx"] <= w, (where, "頁が横にはみ出す", rec["sx"])
        if (w, h) in ((390, 844), (1440, 900)):
            assert rec["about"]["b"] <= h, (where, "このサイトについて が最初の画面の外", rec["about"])
print("ok 入口の題の間: 英語の頁だけ横書きで、題字の下に大きめの読み・左右の真ん中がそろう。日本語の頁は前の形（白と暗い版・幅 320/375/390/430/1440）")
