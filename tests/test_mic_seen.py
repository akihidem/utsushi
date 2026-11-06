"""話す釦が、幅の狭い画面で本当に見える事を測る（本人の決定 11-05: iPhone・iPad でも話す釦を出す）。

なぜ測るか: 字を見る試験は全部通るのに、幅 1100 以下で釦が消えた。釦に hidden 属性が付いていて、指で触る機器の床（skin.TAP_FLOOR の
[hidden]{display:none!important}）が、話す口の CSS の出し分けに勝ったため。釦が見えるかは、字の組み合わせでなく、画面の結果を見ないと分からない。

./run.sh はブラウザなしで動く決まりで、ブラウザを操る道具も入れない決まり（tests/measure_tap.py と同じ）。入っている Chrome を headless で開き、
幅を決めた iframe の中で測る。Chrome が無い機械と、時間内に答えなかった時は、測れないと出して通す（混んだ機械で、ほかの枝の取り込みを止めないため）。
落ちるのは、測れて、結果が違う時だけ。音声認識の口は見本に差し替える（Chrome の版で結果が変わらないように。マイクは使わない）。
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
os.environ.pop("OMOCHAE_VOICE", None)

from measure_tap import chrome  # noqa: E402
from omochae import records  # noqa: E402
from web import play_server  # noqa: E402

G = "NDL-1187053-R0000005-L"
# 画面の形: iPhone に近い形（前置きの付いた名前だけ）・端末の中で字にできる形・音声認識の口が無い形
SHAPES = {
    "safari": "class S{start(){}stop(){}};window.SpeechRecognition=undefined;window.webkitSpeechRecognition=S;",
    "local": "class S{static async available(){return 'available'}start(){}stop(){}};S.prototype.processLocally=false;window.SpeechRecognition=S;window.webkitSpeechRecognition=S;",
    "none": "window.SpeechRecognition=undefined;window.webkitSpeechRecognition=undefined;",
}
# 話す釦は手帖の記録の頁の札にある（作る頁のマイクは 1 つで、はじめるの後に出る。#87。tests/test_techo_step.py が見る）
TOY, MAKE, TECHO = f"/toy/{G}", f"/toy/{G}/tsukuru?h=H-A", f"/toy/{G}/techo/kiroku"
# （幅, 頁, 形, 釦が見えるはずか）。幅 390 は iPhone、820 は iPad。どちらも指で触る機器の床が効く幅
CASES = [(w, page, "safari", True) for w in (390, 820) for page in (TOY, MAKE, TECHO)] + [(390, MAKE, "local", True), (390, MAKE, "none", False)]
# 頁の終わりに足す。釦の大きさと、断りの何が出ているかを親へ送る。番号はサーバが書く（作りながら見る頁は住所の後ろを書き換えるので、住所から読めない）
MEASURE = """<script>setTimeout(()=>{const m=document.querySelector('.hanasu-mic'),r=m?m.getBoundingClientRect():{width:0,height:0},
how=[...document.querySelectorAll('.hanasu-how')].filter(e=>e.getBoundingClientRect().width>0).map(e=>e.className);
parent.postMessage(JSON.stringify({key:__CASE__,w:innerWidth,mic:[Math.round(r.width),Math.round(r.height)],shown:!!m&&getComputedStyle(m).display!=='none',how,sx:document.documentElement.scrollWidth}),'*')},800)</script>"""
WRAP = """<!doctype html><body>%s<pre id="measured"></pre><script>
addEventListener('message',e=>{document.getElementById('measured').textContent+=e.data+'\\n'})</script>"""

send, get = play_server.Handler._send, play_server.Handler.do_GET


def wrapped(self, code, body, ctype="text/html; charset=utf-8", headers=()):
    m = re.search(r"[?&]case=(\d+)", self.path)
    if m and isinstance(body, str) and ctype.startswith("text/html"):
        # 見本は頁の script より先に置く（<head> の無い頁があるので <html> の直後）。測る script は頁の終わりに足す
        stub = f"<script>{SHAPES[CASES[int(m.group(1))][2]]}</script>"
        body = re.sub(r"<html[^>]*>", lambda h: h.group(0) + stub, body, count=1) + MEASURE.replace("__CASE__", m.group(1))
    return send(self, code, body, ctype, headers)


def do_get(self):
    if self.path == "/__wrap":
        # 親と頁の origin をそろえる（別の origin だと iframe が別のプロセスになり、測る前に DOM が書き出される。measure_tap と同じ）
        frames = "".join(f'<iframe src="{html_escape(page + ("&" if "?" in page else "?") + f"case={i}")}" width="{w}" height="844" style="border:0"></iframe>'
                         for i, (w, page, _, _) in enumerate(CASES))
        return send(self, 200, WRAP % frames)
    return get(self)


def html_escape(s):
    return s.replace("&", "&amp;")


exe = chrome()
if not exe:
    print("測れない: Chrome が無い（釦に hidden が付いていない事は tests/test_hanasu.py が字で見る）")
    raise SystemExit(0)
play_server.Handler._send, play_server.Handler.do_GET = wrapped, do_get
server = play_server.serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"
for path, data in ((f"/toy/{G}/print", {"hypothesis": "H-A"}), (f"/toy/{G}/record", {"hypothesis": "H-A", "result": "動いた"})):
    urllib.request.urlopen(urllib.request.Request(base + path, data=urllib.parse.urlencode(data).encode(), headers={"Origin": base}), timeout=120)
# 手帖の話す口は記録を残した画面にだけ開く。測る Chrome を、その画面として扱う
records.claim(records.all_records(G)[-1]["id"], "a" * 24)
play_server.Handler._rec_key = lambda self: "a" * 24
try:
    with tempfile.TemporaryDirectory() as profile:
        out = subprocess.run([exe, "--headless=new", "--no-sandbox", "--disable-gpu", f"--user-data-dir={profile}", "--window-size=1400,900",
                              "--virtual-time-budget=8000", "--dump-dom", f"{base}/__wrap"], capture_output=True, text=True, timeout=120).stdout
except subprocess.TimeoutExpired:
    out = ""
found = re.search(r'<pre id="measured">(.*?)</pre>', out, re.S)
got = {}
for line in (found.group(1).replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">") if found else "").splitlines():
    if line.strip():
        rec = json.loads(line)
        got[int(rec["key"])] = rec
server.shutdown()
if len(got) < len(CASES):
    print(f"測れない: Chrome が {len(CASES)} 件のうち {len(got)} 件しか答えなかった（混んだ機械では起きる）")
    raise SystemExit(0)
for i, (width, page, shape, want) in enumerate(CASES):
    rec = got[i]
    assert rec["w"] == width, (page, width, rec)
    assert rec["sx"] <= width, ("横にはみ出す", page, width, rec)
    if want:
        # 指で押せる大きさで見える（手がふさがっていても押せる。話す口の決まりは 56px）
        assert rec["shown"] and rec["mic"][0] >= 44 and rec["mic"][1] >= 44, ("話す釦が見えない", page, width, shape, rec)
        kind = {"safari": "is-browser", "local": "is-local"}[shape]
        assert any(kind in c for c in rec["how"]), ("断りが釦と合わない", page, width, shape, rec)
    else:
        assert not rec["shown"] and any("is-none" in c for c in rec["how"]), ("口が無い画面に釦が出た", page, width, shape, rec)
print(f"ok 話す釦: 幅 390 と 820 の {len(CASES)} 件で、見える物は見え、口の無い画面には出ない")
