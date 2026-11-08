"""よむ の北斎漫画の留まる節（下へ送ると 1 人ずつ入れ替わる絵）が、狭い画面で崩れない（本人の言葉 11-08「PC、iPhoneなどいろんな大きさで見ても崩れないようにして。」）。

なぜ: 狭い幅は 1 列で絵の箱と字を縦に積み、留まる箱（100svh）に入れる。英語の字は長く、前は絵が節の上の端より上へ出て前の節の字に重なった（#687 で直した）。
直した後も、幅 320×568 の英語は字だけで箱を超え、絵の箱が 2px につぶれ、留まった時に字が画面の下へ出た（#687 の別の目の測り）。tests/test_no_overlap.py は
幅 320 を測らず、画面の外へ出た字も数えないので、ここで見る。
見る事（白の皮・日本語とやさしい日本語と英語・幅 320×568・375×667・390×844）:
- 留まる時（position:sticky）: 絵の箱の上の端が節の上の端より下・字の終わりが留まる箱の下の端より上・絵の箱の高さ 100px 以上
- 留めずに流す時（幅 336px 以下の英語）: 絵の箱の高さ 100px 以上で、絵の箱と字が節の中
絵は偽の頁の画像で切り出す（tests/test_site_hokusai.py と同じ。原画の写しも網も使わない）。
./run.sh はブラウザなしで動く決まりなので、入っている Chrome で頁をその大きさの iframe に開いて測る（tests/test_landscape_fit.py と同じ測り方）。
Chrome が無い機械と、時間内に答えなかった時は、測れないと出して通す（出力の「測れない」を見る）。
"""
import html
import json
import os
import pathlib
import re
import signal
import subprocess
import sys
import tempfile
import threading

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
tmp = tempfile.TemporaryDirectory()
os.environ["OMOCHAE_DATA"] = f"{tmp.name}/data"

from PIL import Image  # noqa: E402

from measure_tap import chrome  # noqa: E402
from omochae import hokusai as hk  # noqa: E402
from web import play_server  # noqa: E402

hk.DIR = pathlib.Path(tmp.name) / "hokusai"
hk.DIR.mkdir(parents=True)
for name in hk.pages():
    Image.new("RGB", (1000, 800), (200, 180, 140)).save(hk.path_of(name), "JPEG")
assert hk.fetch() == []

SIZES = ((320, 568), (375, 667), (390, 844))
MIN_STACK = 100  # 絵の箱の高さの下限（px）。1 人の絵が何の形か分かる高さ（幅 375 の英語で 164px・320 の やさしい日本語 で 128px）
FIND = r"""(() => {
  const w = document.getElementById('zn-hokusai'); if (!w) return {none: true};
  const pin = w.querySelector('.pin'), st = w.querySelector('.stack'), tx = pin.children[1], R = (e) => e.getBoundingClientRect();
  return {sticky: getComputedStyle(pin).position === 'sticky', top: R(st).top - R(w).top, stackH: R(st).height,
          textBottom: R(tx).bottom - R(pin).bottom, inside: R(tx).bottom <= R(w).bottom + 1 && R(st).top >= R(w).top - 1};
})()"""
WRAP = """<!doctype html><meta charset="utf-8"><body>__FRAMES__<pre id="measured"></pre><script>
const FIND=__FIND__;
addEventListener('load',()=>setTimeout(()=>{const out=[];for(const f of document.querySelectorAll('iframe')){let r;try{r=f.contentWindow.eval(FIND)}catch(e){r={err:String(e)}}
out.push({key:f.dataset.key,...r})}document.getElementById('measured').textContent=JSON.stringify(out)},1200))</script>"""

exe = chrome()
if not exe:
    print("測れない: Chrome が無い")
    raise SystemExit(0)
send, get = play_server.Handler._send, play_server.Handler.do_GET


def do_get(self):
    if self.path.startswith("/__pin"):
        lang = self.path.rsplit("=", 1)[1]
        frames = "".join(f'<iframe data-key="{w}x{h}" src="/about?lang={lang}" width="{w}" height="{h}" style="border:0;display:block"></iframe>' for w, h in SIZES)
        return send(self, 200, WRAP.replace("__FRAMES__", frames).replace("__FIND__", json.dumps(FIND)))
    return get(self)


play_server.Handler.do_GET = do_get
server = play_server.serve(0, look="tenji")
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"


def measure(lang):
    # 言葉の切り替えは cookie なので、言葉ごとに別の回（別の profile）にする。時間切れの時は Chrome の組ごと止める（子が profile に書き続けると後始末が落ちる）
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as profile:
        proc = subprocess.Popen([exe, "--headless=new", "--no-sandbox", "--disable-gpu", f"--user-data-dir={profile}", "--window-size=1200,1000",
                                 "--virtual-time-budget=20000", "--dump-dom", f"{base}/__pin?lang={lang}"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                text=True, start_new_session=True)
        try:
            out, _ = proc.communicate(timeout=120)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.communicate()
            return None
    found = re.search(r'<pre id="measured">(.*?)</pre>', out, re.S)
    return json.loads(html.unescape(found.group(1))) if found and found.group(1).strip() else None


bad, seen, unmeasured = [], [], []
for lang in ("ja", "easy", "en"):
    rec = measure(lang) or measure(lang)
    if rec is None:
        unmeasured.append(lang)
        continue
    for r in rec:
        assert "err" not in r and not r.get("none"), (lang, r)
        where = f"{lang}・{r['key']}"
        seen.append(f"{where} {'留まる' if r['sticky'] else '流す'} 絵 {r['stackH']:.0f}px")
        if r["stackH"] < MIN_STACK:
            bad.append(f"{where}: 絵の箱が {r['stackH']:.0f}px（{MIN_STACK}px より低い）")
        if r["sticky"] and r["top"] < -1:
            bad.append(f"{where}: 留まった時に絵の箱が節の上の端より {-r['top']:.0f}px 上へ出る（前の節の字に重なる）")
        if r["sticky"] and r["textBottom"] > 1:
            bad.append(f"{where}: 留まった時に字の終わりが画面の下へ {r['textBottom']:.0f}px 出る")
        if not r["sticky"] and not r["inside"]:
            bad.append(f"{where}: 流す形で絵の箱か字が節の外へ出る")
server.shutdown()
if len(unmeasured) == 3:
    print("測れない: Chrome が答えなかった（全部の言葉）")
    raise SystemExit(0)
assert not bad, "北斎漫画の留まる節が狭い画面で崩れる:\n" + "\n".join(bad)
print(f"ok 北斎漫画の留まる節: {len(seen)} 通り（{'・'.join(seen)}）で、絵の箱 {MIN_STACK}px 以上・前の節に出ない・字が画面の下へ出ない"
      + (f"。測れない言葉: {'・'.join(unmeasured)}" if unmeasured else ""))
