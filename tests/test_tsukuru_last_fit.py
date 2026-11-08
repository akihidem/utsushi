"""作りながら見る頁の最後の手順の「のこす」の札が、狭い画面と英語の頁でも最初の画面に入り、札の中の本人の字が 2 行を越えない。

なぜ: #643 で最後の手順の一番大きい札を「のこす」にし、札の外の上に本人の字（naoru.ROUTE_ASK）を置いたら、字の 2 行（52px）の分だけ、
375×667 の御来迎（689px）と英語の 390×844（御来迎 879・虎 857）で札が画面の下へ出た（別の目の確かめ 11-08）。test_landscape_fit は、
手順の紙の絵が下限まで縮んだ手順を外へ出てよい事にしているので、ここを拾えなかった。本人の字を札の中の上の段に入れた（統括の決め 11-08）ので、
その形を測って守る。
./run.sh はブラウザなしで動く決まりなので、入っている Chrome で頁をその大きさの iframe に開いて測る（tests/test_landscape_fit.py と同じ測り方）。
Chrome が無い機械と、時間内に答えなかった時は、測れないと出して通す。
見る事（御来迎と虎・日本語と英語）:
- 日本語は 375×667 と 390×844、英語は 390×844 で、のこす の札の下の端が画面の高さの中
- 札の中の本人の字（.ask）は 2 行まで・札の名（.nm）の字が一番大きい・札の中で字が札の外へ出ない
- 320×568（と英語の 375×667）は #643 の前（「全部できた」の札）から画面の外だったので、数だけを出す
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import urllib.parse
import urllib.request

os.environ["OMOCHAE_DATA"] = tempfile.mkdtemp()
os.environ.pop("ANTHROPIC_API_KEY", None)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from measure_tap import chrome  # noqa: E402
from omochae import hypotheses  # noqa: E402
from web import play_server, tsukuru  # noqa: E402

TOYS = {"goraigo": "NDL-1187053-R0000005-L", "tora": "NDL-1187053-R0000014-R"}
SIZES = ((320, 568), (375, 667), (390, 844))
# 守る大きさ: 日本語は 375×667 と 390×844、英語は 390×844（統括の決め 11-08）。英語の 375×667 と 320×568 は、英語の手順の字が長く、
# 手順の紙の絵が下限まで縮んでも入らない（#643 の前から）ので、数だけを出す
MUST = {"ja": {(375, 667), (390, 844)}, "en": {(390, 844)}}
WRAP = """<!doctype html><meta charset="utf-8"><body>__FRAMES__<pre id="measured"></pre><script>
addEventListener('load',()=>setTimeout(()=>{const out=[];for(const f of document.querySelectorAll('iframe')){const d=f.contentDocument,w=f.contentWindow;
const b=d.querySelector('#tiles [value=done]'),a=b&&b.querySelector('.ask'),nm=b&&b.querySelector('.nm');const r=b.getBoundingClientRect(),ra=a.getBoundingClientRect(),rn=nm.getBoundingClientRect();
const lh=parseFloat(w.getComputedStyle(a).lineHeight);
out.push({key:f.dataset.key,w:w.innerWidth,h:w.innerHeight,bottom:Math.round(r.bottom),hidden:b.hidden,lines:Math.round(ra.height/lh),
askPx:parseFloat(w.getComputedStyle(a).fontSize),nmPx:parseFloat(w.getComputedStyle(nm).fontSize),inside:ra.top>=r.top-1&&rn.bottom<=r.bottom+1&&ra.right<=r.right+1&&ra.left>=r.left-1})}
document.getElementById('measured').textContent=JSON.stringify(out)},1200))</script>"""

exe = chrome()
if not exe:
    print("測れない: Chrome が無い")
    raise SystemExit(0)
send, get = play_server.Handler._send, play_server.Handler.do_GET
frames = {}


def do_get(self):
    if self.path.startswith("/__fit"):
        lang = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query).get("lang", [""])[0]
        q = f"&amp;lang={lang}" if lang else ""
        html = "".join(f'<iframe data-key="{name}-{w}x{h}" src="/toy/{sid}/tsukuru?h={hid}&amp;n={n}{q}" width="{w}" height="{h}" style="border:0;display:block"></iframe>'
                       for name, (sid, hid, n) in frames.items() for w, h in SIZES)
        return send(self, 200, WRAP.replace("__FRAMES__", html))
    return get(self)


play_server.Handler.do_GET = do_get
server = play_server.serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"
for name, sid in TOYS.items():
    hid = hypotheses.sheet_of(sid)["id"]
    urllib.request.urlopen(urllib.request.Request(f"{base}/toy/{sid}/print", data=urllib.parse.urlencode({"hypothesis": hid}).encode(),
                                                  headers={"Origin": base}), timeout=180).read()
    frames[name] = (sid, hid, tsukuru.count(sid, hid))


def measure(lang):
    # 言葉の切り替えは cookie なので、日本語と英語を別の回にする（同じ回に混ぜると、後の頁が先の頁の言葉で開く）
    with tempfile.TemporaryDirectory() as profile:
        try:
            out = subprocess.run([exe, "--headless=new", "--no-sandbox", "--disable-gpu", f"--user-data-dir={profile}", "--window-size=1600,1200",
                                  "--virtual-time-budget=20000", "--dump-dom", f"{base}/__fit?lang={lang}"], capture_output=True, text=True, timeout=200).stdout
        except subprocess.TimeoutExpired:
            return None
    found = re.search(r'<pre id="measured">(.*?)</pre>', out, re.S)
    return json.loads(found.group(1).replace("&quot;", '"')) if found and found.group(1).strip() else None


got = {}
for lang in ("ja", "en"):
    rec = measure(lang) or measure(lang)
    if rec is None:
        server.shutdown()
        print(f"測れない: Chrome が答えなかった（{lang}）")
        raise SystemExit(0)
    got[lang] = rec
server.shutdown()

small = []
for lang, recs in got.items():
    assert len(recs) == len(TOYS) * len(SIZES), (lang, len(recs))
    for f in recs:
        w, h = f["w"], f["h"]
        assert not f["hidden"], (lang, f)
        assert f["lines"] <= 2, (lang, "札の中の本人の字が 2 行を越える", f)
        assert f["nmPx"] > f["askPx"], (lang, "札の名 のこす が一番大きく読めない", f)
        assert f["inside"], (lang, "札の中の字が札の外へ出る", f)
        if (w, h) in MUST[lang]:
            assert f["bottom"] <= h, (lang, "のこす の札が最初の画面の外", f)
        else:
            small.append(f"{lang} {f['key']} 札の下の端 {f['bottom']}/{h}")
print("ok 作りながら見る頁の最後の手順の のこす の札: 日本語 375×667・390×844 と英語 390×844 で最初の画面の中・本人の字は札の中で 2 行まで（日本語と英語）。"
      "前から外の大きさ（数だけ）: " + "・".join(small))
