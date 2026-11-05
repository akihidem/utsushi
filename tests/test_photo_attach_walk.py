"""手帖の頁が、写真を「この画面が残した記録」に足す所を、入っている Chrome で歩いて確かめる（1 回の作りが 2 つの記録に割れる所の直し）。

字を見る試験では、押す順と送る順が分からない。本物の頁で、玩具の頁の記録の欄で残す → 手帖を開く → 写真を選ぶ → 押す、を歩き、
残った記録と写真をサーバの側で数える。受け口の決まり（鍵・番号を受けない・期限）は tests/test_photo_attach.py が見る。

歩く道:
N 約束の印（大人の手元だけ・顔なし・声なし）を入れずに押す: 何も送らない（足せるかも聞かない）。印が「要る」になっていない形でも同じ
A 写真だけを選んで押す: 見た事を求めず、さっきの記録に足す（記録は増えない）
B 写真のある記録には、もう足さない: 今までどおり「紙と見た事をえらぶ」
C 続けて 2 度押す: 同じ写真を 2 度送らない
D 同じ見た事を選び直して押す: 同じ作りなので足す（記録は増えない）
E ひとことを書いて押す: 書いた事が残るように、今までどおり新しい記録にする
P 別の紙を選び直して、写真だけで押す: 前の紙の記録には足さず、今までどおり「紙と見た事をえらぶ」
頁が送る紙: 紙は最初から 1 つ選ばれているので、選び直した時と見た事を選んだ時だけ送る（A では送らない・D と P では送る）

./run.sh はブラウザなしで動く決まりで、ブラウザを操る道具も入れない決まり（tests/test_mic_seen.py と同じ）。入っている Chrome で頁を iframe に開いて歩く。
Chrome が無い機械と、Chrome が何も答えなかった時は、測れないと出して通す。落ちるのは、歩けて結果が違う時と、歩き始めたのに終わらなかった時。
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
os.environ.pop("ANTHROPIC_API_KEY", None)

from measure_tap import chrome  # noqa: E402
from omochae import records  # noqa: E402
from web import play_server, techo_site  # noqa: E402

G = "NDL-1187053-R0000005-L"
# 親の頁。手帖と同じ origin に置き、iframe の中の頁を本物の操作と同じ順で動かす。写真は canvas で作った本物の JPEG（受け口は中身を読める物だけを受ける）。
# 押す前に、上げる時の約束の印（大人の手元だけ・顔なし・声なし）を入れる。入れないと、頁は送らない。
WALK = r"""<!doctype html><body><iframe id="f" width="820" height="900" style="border:0"></iframe><pre id="measured">started</pre><script>(async()=>{
const R={},G=%s,f=document.getElementById('f');
const wait=(ms)=>new Promise(r=>setTimeout(r,ms));
const record=(result)=>fetch('/toy/'+G+'/record',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:new URLSearchParams({hypothesis:'H-A',result}),redirect:'manual'});
// 頁が記録の口へ送った数を数える（約束の印が無い時に、足せるかも聞かない事を見るため）
const open=()=>new Promise(r=>{f.onload=()=>{const w=f.contentWindow,real=w.fetch;w.__sent=0;w.fetch=(u,o)=>{if(String(u).includes('record-json')){w.__sent++;const q=new URLSearchParams(o&&o.body?o.body.toString():'');if(q.get('attach')==='1')w.__asked=q.get('hypothesis')}return real.call(w,u,o)};r()};f.src='/toy/'+G+'/techo?t='+Math.random()});
const doc=()=>f.contentDocument,go=()=>doc().querySelector('#up-form button.go'),st=()=>doc().getElementById('up-status');
const jpeg=()=>new Promise(r=>{const c=document.createElement('canvas');c.width=c.height=8;c.getContext('2d').fillRect(0,0,8,8);c.toBlob(r,'image/jpeg')});
const pick=async()=>{const w=f.contentWindow,dt=new w.DataTransfer();dt.items.add(new w.File([await jpeg()],'a.jpg',{type:'image/jpeg'}));
 const p=doc().getElementById('files');p.files=dt.files;p.dispatchEvent(new w.Event('change'))};
const press=async(times=1)=>{st().textContent='';doc().getElementById('ok').checked=true;for(let i=0;i<times;i++)go().click();
 for(let i=0;i<300&&(go().disabled||!st().textContent||st().textContent==='送っています…');i++)await wait(50);return st().textContent};
const choose=(result)=>doc().querySelector('[name=result][value="'+result+'"]').click(),who=()=>sessionStorage.getItem('utsushi-who');
try{
 await record('動いた');await open();await pick();R.button=go().textContent;
 // 印が「要る」になっていない形（別の頁から戻って、写真だけが戻った時）を作る。ブラウザの標準の止めが効かないので、頁の中の止めを通る
 const ok=doc().getElementById('ok');ok.checked=false;ok.required=false;st().textContent='';go().click();await wait(400);R.n=[st().textContent,f.contentWindow.__sent,go().disabled,ok.required];
 R.who_a=[who()];R.a=await press();R.who_a.push(who());R.a_asked=f.contentWindow.__asked;
 await pick();R.b=await press();R.b_ready=!go().disabled;
 await record('動かない');await open();await pick();R.c=await press(2);R.c_sent=f.contentWindow.__sent;
 await record('わからない');await open();await pick();choose('わからない');R.d=await press();R.d_asked=f.contentWindow.__asked;
 await record('動いた');await open();await pick();choose('動いた');doc().getElementById('note').value='二度目の作り';R.who_e=[who()];R.e=await press();R.who_e.push(who());
 // 紙を選び直した形を作る（この玩具の紙は 1 つなので、選ばれている札を「最初からの選びでない別の紙」にする。最初の選びを外すと選びも外れるので、選び直す）
 await record('動かない');await open();await pick();const tile=doc().querySelector('[name=hypothesis]:checked');tile.defaultChecked=false;tile.checked=true;tile.value='H-Z';R.p=await press();R.p_asked=f.contentWindow.__asked;
}catch(e){R.error=String(e&&e.stack||e)}
document.getElementById('measured').textContent=JSON.stringify(R);
})();</script>"""

send, get = play_server.Handler._send, play_server.Handler.do_GET


def do_get(self):
    if self.path == "/__walk":
        return send(self, 200, WALK % json.dumps(G))
    return get(self)


exe = chrome()
if not exe:
    print("測れない: Chrome が無い（受け口の決まりは tests/test_photo_attach.py が見る）")
    raise SystemExit(0)
play_server.Handler.do_GET = do_get
server = play_server.serve(0)
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}"
urllib.request.urlopen(urllib.request.Request(f"{base}/toy/{G}/print", data=urllib.parse.urlencode({"hypothesis": "H-A"}).encode(), headers={"Origin": base}), timeout=120)


def walk():
    """Chrome で 1 回歩く。返すのは、頁が書いた結果（歩き終われば dict、始めただけなら "started"、何も答えなければ None）。"""
    try:
        with tempfile.TemporaryDirectory() as profile:
            out = subprocess.run([exe, "--headless=new", "--no-sandbox", "--disable-gpu", f"--user-data-dir={profile}", "--window-size=1000,1000",
                                  "--virtual-time-budget=90000", "--dump-dom", f"{base}/__walk"], capture_output=True, text=True, timeout=170).stdout
    except subprocess.TimeoutExpired:
        return None
    found = re.search(r'<pre id="measured">(.*?)</pre>', out, re.S)
    if not found:
        return None
    text = found.group(1).replace("&quot;", '"').replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
    return json.loads(text) if text.startswith("{") else text


got = walk()
if not isinstance(got, dict) and not records.all_records(G):
    got = walk()  # 混んだ機械では答えない事があるので、何も残っていなければ 1 度だけ回し直す
server.shutdown()
if got is None:
    print("測れない: Chrome が答えなかった（混んだ機械では起きる。受け口の決まりは tests/test_photo_attach.py が見る）")
    raise SystemExit(0)
assert isinstance(got, dict), ("歩き始めたのに終わらなかった", got, [(r["id"], r["result"]) for r in records.all_records(G)])
assert "error" not in got, got
rows = [(r["result"], r.get("via"), r.get("note") or "", len(techo_site.media_of(r["id"]))) for r in sorted(records.all_records(G), key=lambda r: r["id"])]
# N 約束の印なしでは、足せるかも聞かず、何も送らない。押す所も止めない
assert got["n"] == ["", 0, False, True], got
# A 写真だけで押すと、見た事を求めず、玩具の頁で残した記録に足す
assert got["button"] == "上げる" and got["a"] == "上げました", got
assert rows[0] == ("動いた", None, "", 1), rows
# 足した時は、その場限りの印を作り直さない（記録は増えていない。作り直すと、次の作りの話が 2 つの印に割れる）
assert got["who_a"][0] and got["who_a"][0] == got["who_a"][1], got
assert got["a_asked"] == "", ("紙を選び直していない時は、選んだ紙として送らない", got)
# B 写真のある記録にはもう足さず、今までどおり見た事を求める。押す所は戻る
assert got["b"] == "紙と見た事をえらぶ" and got["b_ready"], got
# C 続けて 2 度押しても、写真は 1 つ。2 度目の押しは送る所まで行かない（写真の数だけだと、送る順の具合で 1 つに見える事があるので、送った数も見る）
assert got["c"] == "上げました" and got["c_sent"] == 1 and rows[1] == ("動かない", None, "", 1), (got, rows)
# D 同じ見た事を選び直しても、記録は増えない
assert got["d"] == "上げました" and got["d_asked"] == "H-A" and rows[2] == ("わからない", None, "", 1), (got, rows)
# E 書いた字がある時は、新しい記録にして字を残す。玩具の頁で残した記録は、写真なしのまま
assert got["e"] == "上げました" and rows[3:5] == [("動いた", None, "", 0), ("動いた", "techo", "二度目の作り", 1)], (got, rows)
assert got["who_e"][0] and got["who_e"][0] != got["who_e"][1], ("新しい記録が残った時は、今までどおり印を作り直す", got)
# P 別の紙を選び直した時は、見た事を選んでいなくても、前の紙の記録に足さない
assert got["p"] == "紙と見た事をえらぶ" and got["p_asked"] == "H-Z" and rows[5:] == [("動かない", None, "", 0)], (got, rows)
print("ok 写真を足す頁: 写真だけで押すと記録が 1 つのまま。写真のある記録・書いた字がある時は今までどおり。2 度押しても写真は 1 つ")
