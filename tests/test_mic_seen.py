"""録る釦「声を録る」が、幅の狭い画面で本当に見える事を測る（本人の答え 11-08「(A) 声を録る釦を置いて残す。新しい字 3 つもよい。」）。

なぜ測るか: 字を見る試験は全部通るのに、幅 1100 以下で釦が消えた事がある（前の「話す」の釦）。釦に hidden 属性が付いていて、指で触る機器の床
（skin.TAP_FLOOR の [hidden]{display:none!important}）が、話す口の CSS の出し分けに勝ったため。釦が見えるかは、字の組み合わせでなく、画面の結果を
見ないと分からない。前は「話す」の釦（ブラウザの音声認識）を測っていた。11-08 に音声認識を外し（本人「クロードの音声認識をはずして、ユーザーの
端末の音声入力に頼るのでいいのではないか。」）、録る釦を置いたので、同じ測りを録る釦に替えた（凍結の表の名なので消さずに中身を替えた。理由は
commit と docs/claude-usage.md）。測るのは、置き所の 2 つ（作りながら見る頁の工夫の口・のこすの頁の工夫の欄）で釦が見えて 44px 以上ある事と、
字の欄の下の 1 行が見える事と、記録の札の足す口に録る釦が見えない事。「音声認識を起こさない」は tests/test_no_speech_recognition.py が全部の頁で見る。

./run.sh はブラウザなしで動く決まりで、ブラウザを操る道具も入れない決まり（tests/measure_tap.py と同じ）。入っている Chrome を headless で開き、
幅を決めた iframe の中で測る。Chrome が無い機械と、時間内に答えなかった時は、測れないと出して通す（混んだ機械で、ほかの枝の取り込みを止めないため）。
落ちるのは、測れて、結果が違う時だけ。マイクは使わない（釦は押さない）。
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

from measure_tap import chrome  # noqa: E402
from omochae import records  # noqa: E402
from web import play_server  # noqa: E402

G = "NDL-1187053-R0000005-L"
from omochae import hypotheses  # noqa: E402
# 御来迎のたたき台は組ごと（今の組 goraigo-v14 は H-C・記録の欄 sheet_by_set）。今の組で刷れるのはたたき台の紙だけ
GS = hypotheses.sheet_of(G)["id"]
# 置き所: 作りながら見る頁の工夫の口と、のこすの頁（手帖の記録の頁の上の記入の節）の工夫の欄。のこすの頁の下の記録の札の足す口には録る釦が無い
MAKE, NOKOSU = f"/toy/{G}/tsukuru?h={GS}", f"/toy/{G}/techo/kiroku"
# （幅, 頁）。幅 390 は iPhone、820 は iPad。どちらも指で触る機器の床が効く幅
TOY = f"/toy/{G}"
# 玩具の頁は話す口の無い頁（考えを話す の口を外した・本人の言葉 11-08「つくるの「考えを話す」は無くす。」・#709）: 録る釦が無い事を測る。
# 字の欄の下の 1 行は、型紙を印刷する の中の「Claude に話して型紙を作り直す」口（#714・#722・#think）の中にだけある（話す口ではなく、同じ部品の 1 行）
CASES = [(w, page) for w in (390, 820) for page in (MAKE, NOKOSU, TOY)]
# 頁の終わりに足す。録る釦の大きさと、欄の下の 1 行が見えるかと、足す口の録る釦の数を親へ送る。番号はサーバが書く
MEASURE = """<script>setTimeout(()=>{const seen=e=>!!e&&getComputedStyle(e).display!=='none'&&e.getBoundingClientRect().width>0;
const m=document.querySelector('.hanasu-rec'),r=m?m.getBoundingClientRect():{width:0,height:0},kb=[...document.querySelectorAll('.hanasu-kb')].find(e=>!e.closest('#think')),kt=document.querySelector('#think .hanasu-kb');
const keep=[...document.querySelectorAll('[data-scene=keep] .hanasu-rec')].filter(seen).length,keeps=document.querySelectorAll('[data-scene=keep]').length;
parent.postMessage(JSON.stringify({key:__CASE__,w:innerWidth,rec:[Math.round(r.width),Math.round(r.height)],shown:seen(m),label:m?m.innerText.trim():'',kb:seen(kb),kt:seen(kt),keep,keeps,sx:document.documentElement.scrollWidth}),'*')},800)</script>"""
WRAP = """<!doctype html><body>%s<pre id="measured"></pre><script>
addEventListener('message',e=>{document.getElementById('measured').textContent+=e.data+'\\n'})</script>"""

send, get = play_server.Handler._send, play_server.Handler.do_GET


def wrapped(self, code, body, ctype="text/html; charset=utf-8", headers=()):
    m = re.search(r"[?&]case=(\d+)", self.path)
    if m and isinstance(body, str) and ctype.startswith("text/html"):
        # 測る script は頁の終わりに足す（見本は置かない: 釦は押さないので、マイクも録りの口も使わない）
        body = body + MEASURE.replace("__CASE__", m.group(1))
    return send(self, code, body, ctype, headers)


def do_get(self):
    if self.path == "/__wrap":
        # 親と頁の origin をそろえる（別の origin だと iframe が別のプロセスになり、測る前に DOM が書き出される。measure_tap と同じ）
        frames = "".join(f'<iframe src="{html_escape(page + ("&" if "?" in page else "?") + f"case={i}")}" width="{w}" height="844" style="border:0"></iframe>'
                         for i, (w, page) in enumerate(CASES))
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
for path, data in ((f"/toy/{G}/print", {"hypothesis": GS}), (f"/toy/{G}/record", {"hypothesis": GS, "result": "動いた"})):
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
for i, (width, page) in enumerate(CASES):
    rec = got[i]
    assert rec["w"] == width, (page, width, rec)
    assert rec["sx"] <= width, ("横にはみ出す", page, width, rec)
    if page == TOY:
        assert not rec["shown"] and not rec["kb"], ("話す口の無い玩具の頁に録る釦か、作り直しの口の外に 1 行がある", width, rec)
        assert rec["kt"], ("作り直しの口の字の欄の下の 1 行が見えない", width, rec)
        continue
    # 指で押せる大きさで見える（手がふさがっていても押せる。のこすの頁の決まりは 44px・話す口の決まりは 56px）
    assert rec["shown"] and rec["rec"][0] >= 44 and rec["rec"][1] >= 44 and rec["label"] == "声を録る", ("録る釦が見えない", page, width, rec)
    assert rec["kb"], ("字の欄の下の 1 行が見えない", page, width, rec)
    if page == NOKOSU:
        assert rec["keeps"] >= 1 and rec["keep"] == 0, ("記録の札の足す口に録る釦が見える（置かない決め・設計の 2 版の止め 1）", width, rec)
print(f"ok 録る釦: 幅 390 と 820 の {len(CASES)} 件で、作りながら見る頁と のこすの頁は 声を録る が見えて 44px 以上・欄の下の 1 行が見える・足す口には無い・玩具の頁には無い")
